"""Revision-checked private C files, tombstones, quotas and recovery."""

import base64
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from ..accounts.store import AccountStore
from ..settings import ServerSettings
from .paths import DosError, MAX_FILES, atomic_file, c_path, user_dir


class DosOverlayStore:
    def __init__(self, users_dir: Path, settings: ServerSettings, accounts: AccountStore | None):
        self.users_dir = users_dir
        self.settings = settings
        self.accounts = accounts

    def user_dir(self, account_id: str) -> Path:
        return user_dir(self.users_dir, account_id)

    def _check_private_path(self, path: Path) -> None:
        parts = path.relative_to(self.users_dir).parts
        if self.users_dir.is_symlink() or any(
                self.users_dir.joinpath(*parts[:index]).is_symlink() for index in range(1, len(parts) + 1)):
            raise DosError("Private C storage must not contain symbolic links")

    def _database(self, account_id: str) -> sqlite3.Connection:
        database = sqlite3.connect(self.user_dir(account_id) / "overlay.sqlite3", timeout=15)
        database.executescript("""
            CREATE TABLE IF NOT EXISTS entries (name TEXT PRIMARY KEY, sha256 TEXT NOT NULL, size INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS deleted (name TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS directories (name TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL);
            INSERT OR IGNORE INTO state VALUES (1, 0);
        """)
        columns = {row[1] for row in database.execute("PRAGMA table_info(entries)")}
        for name, definition in (("sha256", "TEXT NOT NULL DEFAULT ''"), ("size", "INTEGER NOT NULL DEFAULT 0")):
            if name not in columns:
                database.execute(f"ALTER TABLE entries ADD COLUMN {name} {definition}")
        database.commit()
        return database

    def _write_snapshot(self, account_id: str, revision: int, files: dict[str, bytes], directories: list | set) -> Path:
        root = self.user_dir(account_id) / "c"
        if root.is_symlink():
            raise DosError("Private C storage must not be a symbolic link")
        root.mkdir(exist_ok=True)
        pending = Path(tempfile.mkdtemp(prefix="pending-", dir=root))
        snapshot = root / str(revision)
        try:
            for name in directories:
                (pending / c_path(name)).mkdir(parents=True, exist_ok=True)
            for name, contents in files.items():
                atomic_file(pending / c_path(name), contents)
            # This revision is not committed yet; discard only an orphan from
            # an interrupted attempt, never the SQLite-selected current disk.
            if snapshot.is_symlink():
                raise DosError("Private C snapshot must not be a symbolic link")
            if snapshot.exists():
                shutil.rmtree(snapshot)
            os.replace(pending, snapshot)
        finally:
            if pending.exists():
                shutil.rmtree(pending)
        return snapshot

    def _migrate_overlay_files(self, database: sqlite3.Connection, account_id: str, revision: int) -> None:
        if not database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='files'").fetchone():
            return
        files = dict(database.execute("SELECT name, data FROM files"))
        directories = [row[0] for row in database.execute("SELECT name FROM directories")]
        self._write_snapshot(account_id, revision, files, directories)
        database.executemany("INSERT OR REPLACE INTO entries VALUES (?, ?, ?)",
                             [(name, hashlib.sha256(data).hexdigest(), len(data)) for name, data in files.items()])
        database.execute("DROP TABLE files")

    def overlay(self, account_id: str | None) -> tuple[int, dict[str, bytes], list[str], list[str]]:
        if not account_id:
            return 0, {}, [], []
        database = self._database(account_id)
        try:
            database.execute("BEGIN IMMEDIATE")
            revision = database.execute("SELECT revision FROM state WHERE id=1").fetchone()[0]
            self._migrate_overlay_files(database, account_id, revision)
            files = {}
            snapshot = self.user_dir(account_id) / "c" / str(revision)
            for row in database.execute("SELECT name FROM entries"):
                name = c_path(row[0])
                path = snapshot / name
                self._check_private_path(path)
                try:
                    files[name] = path.read_bytes()
                except OSError as error:
                    raise DosError("Saved C files are missing; restore the user's disk backup") from error
                database.execute("UPDATE entries SET sha256=?,size=? WHERE name=? AND sha256=''",
                                 (hashlib.sha256(files[name]).hexdigest(), len(files[name]), name))
            deleted = [row[0] for row in database.execute("SELECT name FROM deleted")]
            directories = [row[0] for row in database.execute("SELECT name FROM directories")]
            database.commit()
            return revision, files, deleted, directories
        finally:
            database.close()

    def save(self, account_id: str, payload: dict, base_id: str, base_files: dict[str, bytes]) -> int:
        limit = self.overlay_limit(account_id)
        if payload.get("base_id") != base_id:
            raise DosError("C drive base changed; reload the page before saving")
        incoming, deleted = payload.get("files"), payload.get("deleted")
        unchanged = payload.get("unchanged", [])
        directories = payload.get("directories", [])
        if (not isinstance(incoming, dict) or not isinstance(deleted, list) or not isinstance(unchanged, list)
                or len(incoming) + len(deleted) + len(unchanged) > MAX_FILES):
            raise DosError("Invalid overlay file list")
        files = {}
        total = 0
        if unchanged:
            old_revision, old_files, _deleted, _directories = self.overlay(account_id)
            if old_revision != payload.get("revision"):
                raise DosError("Another DOS window saved this drive; reload the page to load its changes")
            for name in unchanged:
                canonical = c_path(name)
                if canonical not in old_files or canonical in files:
                    raise DosError("Invalid unchanged overlay file")
                files[canonical] = old_files[canonical]
                total += len(files[canonical])
            if total > limit:
                raise DosError("Overlay exceeds its quota")
        for name, encoded in incoming.items():
            canonical = c_path(name)
            if canonical in files or not isinstance(encoded, str):
                raise DosError("Duplicate or invalid overlay file")
            try:
                contents = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as error:
                raise DosError("Invalid overlay file data") from error
            if contents != base_files.get(canonical):
                total += len(contents)
                if total > limit:
                    raise DosError("Overlay exceeds its quota")
                files[canonical] = contents
        tombstones = {c_path(name) for name in deleted}
        if not isinstance(directories, list) or len(directories) > MAX_FILES:
            raise DosError("Invalid directory list")
        folders = {c_path(name) for name in directories}
        merged = {name: data for name, data in base_files.items() if name not in tombstones}
        merged.update(files)
        if len(merged) > len(base_files) + MAX_FILES:
            raise DosError("Too many C drive files")
        if folders.intersection(merged):
            raise DosError("A path cannot be both a file and a directory")
        for name in merged.keys() | folders:
            parts = name.split("/")
            if any("/".join(parts[:index]) in merged for index in range(1, len(parts))):
                raise DosError("A file cannot contain another path")
        if any(name not in base_files or name in files for name in tombstones):
            raise DosError("Invalid deleted file list")
        database = self._database(account_id)
        snapshot = None
        try:
            database.execute("BEGIN IMMEDIATE")
            revision = database.execute("SELECT revision FROM state WHERE id=1").fetchone()[0]
            if type(payload.get("revision")) is not int or payload["revision"] != revision:
                raise DosError("Another DOS window saved this drive; reload the page to load its changes")
            self._migrate_overlay_files(database, account_id, revision)
            snapshot = self._write_snapshot(account_id, revision + 1, files, folders)
            database.execute("DELETE FROM entries")
            database.execute("DELETE FROM deleted")
            database.execute("DELETE FROM directories")
            database.executemany("INSERT INTO entries VALUES (?, ?, ?)",
                                 [(name, hashlib.sha256(data).hexdigest(), len(data)) for name, data in files.items()])
            database.executemany("INSERT INTO deleted VALUES (?)", [(name,) for name in sorted(tombstones)])
            database.executemany("INSERT INTO directories VALUES (?)", [(name,) for name in sorted(folders)])
            database.execute("UPDATE state SET revision=? WHERE id=1", (revision + 1,))
            database.commit()
            snapshot = None
            # Keep the previous generation for recovery; readers and writers
            # hold the same SQLite lock until all referenced files are read.
            previous = self.user_dir(account_id) / "c" / str(revision - 1)
            if previous.is_dir() and not previous.is_symlink():
                shutil.rmtree(previous, ignore_errors=True)
            return revision + 1
        except Exception:
            database.rollback()
            if snapshot is not None:
                shutil.rmtree(snapshot, ignore_errors=True)
            raise
        finally:
            database.close()

    def overlay_limit(self, account_id: str | None = None) -> int:
        override = self.accounts.disk_capacity(account_id) if self.accounts and account_id else None
        return (override if override is not None else self.settings.get()["dos_user_disk_mb"]) * 1024 * 1024

    def disk_usage(self, account_id: str) -> dict:
        # Read the committed generation only; recovery copies and common C files
        # do not count towards the user's quota. Do not boot/download DOS here.
        path = self.user_dir(account_id) / "overlay.sqlite3"
        used = 0
        if path.exists():
            if path.is_symlink():
                raise DosError("Private C database must not be a symbolic link")
            database = self._database(account_id)
            try:
                database.execute("BEGIN IMMEDIATE")
                revision = database.execute("SELECT revision FROM state WHERE id=1").fetchone()[0]
                self._migrate_overlay_files(database, account_id, revision)
                used = database.execute("SELECT COALESCE(SUM(size),0) FROM entries").fetchone()[0]
                database.commit()
            finally:
                database.close()
        capacity = self.overlay_limit(account_id)
        return {"used_bytes": used, "capacity_bytes": capacity, "free_bytes": max(0, capacity - used)}

    def read_chunk(self, account_id: str | None, name: str, digest: str, offset: int, size: int) -> bytes:
        if not account_id:
            raise DosError("Sign in to read private C files")
        database = self._database(account_id)
        try:
            database.execute("BEGIN IMMEDIATE")
            revision = database.execute("SELECT revision FROM state WHERE id=1").fetchone()[0]
            self._migrate_overlay_files(database, account_id, revision)
            row = database.execute("SELECT sha256 FROM entries WHERE name=?", (name,)).fetchone()
            if row is None or row[0] != digest:
                raise DosError("Private DOS file changed; reload the disk")
            path = self.user_dir(account_id) / "c" / str(revision) / name
            self._check_private_path(path)
            with path.open("rb") as handle:
                handle.seek(offset)
                data = handle.read(size)
            database.commit()
            return data
        finally:
            database.close()
