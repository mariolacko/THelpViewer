"""Shared DOS C drive, private file overlays and approved removable media."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import tempfile
import threading
import zipfile
import uuid
from fnmatch import fnmatch

from .downloader.extractor import ExtractorTools, extract_file, find_lsar, find_sevenzip, find_unar
from .dos_sources import fetch_dos_source
from .settings import ServerSettings
from .accounts import AccountStore
from .rebuild import archive_rebuild_directory


MAX_FILES = 4096
MAX_SOURCE_BYTES = 64 * 1024 * 1024
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ACCOUNT_RE = re.compile(r"^[a-f0-9]{32}$")


class DosError(ValueError):
    pass


def c_path(value: str) -> str:
    """Canonical DOS names, never a host path or an archive escape."""
    if not isinstance(value, str) or not value or len(value) > 260 or value.startswith(("/", "\\")):
        raise DosError("Invalid C drive path")
    parts = value.replace("\\", "/").split("/")
    for part in parts:
        if (part in ("", ".", "..") or len(part) > 64
                or not re.fullmatch(r"[a-zA-Z0-9_. !#$%&'()@^{}~-]+", part)
                or part.rstrip(" .") != part):
            raise DosError("Invalid C drive path")
    return "/".join(parts).upper()


def _atomic_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        output.write(data)
        temporary = Path(output.name)
    os.replace(temporary, path)


class DosPromptStore:
    def __init__(self, root: Path, config_path: Path | None, settings: ServerSettings | None = None,
                 accounts: AccountStore | None = None, downloads_dir: Path | None = None,
                 *, users_dir: Path | None = None, disk_dir: Path | None = None):
        self.root, self.config_path = root, config_path
        self.settings = settings or ServerSettings(root.parent / "server-settings.json")
        self.accounts = accounts
        self.config: dict = {}
        self.files: dict[str, bytes] = {}
        self.file_hashes: dict[str, str] = {}
        self.base_id = ""
        self.state = "idle"
        self.error = ""
        self.current = ""
        self.initializing = False
        self.processed = self.total = self.percent = 0
        self.phase = "Checking disk"
        self.received = 0
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self.backup = ""
        self.rebuilding = False
        self.downloads_dir = downloads_dir or root / "downloads"
        self.source_selection = None
        self.on_progress = None
        self.users_dir = users_dir or root / "users"
        self.disk_dir = disk_dir or root / "base" / "c"
        self.base_root = disk_dir or root / "base"
        self.installed_path = root / "installed.json" if disk_dir else root / "base" / "installed.json"

    def install(self, source_ids: list[str], *, on_progress=None) -> None:
        """Install explicitly selected packages; keep the shared disk and private overlays."""
        with self._lock:
            if self.state == "building" or (self._worker and self._worker.is_alive()):
                raise DosError("DOS C drive is already being prepared")
            self.state, self.error = "building", ""
            self.on_progress = on_progress
        try:
            self.prepare(install_sources=True, source_ids=source_ids)
        finally:
            self.on_progress = None

    def rebuild(self) -> None:
        """Replace only the shared base; retain downloads and every private overlay."""
        with self._lock:
            if self.state == "building" or (self._worker and self._worker.is_alive()):
                raise DosError("DOS C drive is already being prepared")
            if self.installed_path.is_symlink():
                raise DosError("DOS installation metadata must not be a symbolic link")
            self.backup = archive_rebuild_directory(self.base_root, self.root.parent / "backups", "dos-base")
            if not self.installed_path.is_relative_to(self.base_root) and self.installed_path.exists():
                if not self.backup:
                    backup = self.root.parent / "backups" / f"dos-base-{uuid.uuid4().hex}"
                    backup.mkdir(parents=True)
                    self.backup = str(backup.relative_to(self.root.parent))
                self.installed_path.rename(self.root.parent / self.backup / "installed.json")
            self.files, self.file_hashes, self.base_id = {}, {}, ""
            self.state, self.error, self.current = "idle", "", ""
            self.processed = self.total = self.percent = self.received = 0
            self.initializing = True
            self.rebuilding = True
            self.phase = "Preparing new C drive"
            self.start()

    def start(self) -> None:
        with self._lock:
            if self.state != "idle":
                return
            self.state = "building"
            self._worker = threading.Thread(target=self.prepare, name="thelp-dos-first-run", daemon=True)
            self._worker.start()

    def prepare(self, *, install_sources: bool = False, source_ids: list[str] | None = None) -> None:
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8")) if self.config_path else {"sources": []}
            if not isinstance(config, dict) or not isinstance(config.get("sources"), list):
                raise DosError("DOS configuration needs a sources list")
            if any(key in config for key in ("initial_files", "autoexec.bat", "config.sys")):
                raise DosError("Use files entries with path and text/base64 instead of initial_files/autoexec.bat/config.sys")
            self.config = config
            limit = int(config.get("max_c_bytes", MAX_SOURCE_BYTES))
            if not 1024 <= limit <= 256 * 1024 * 1024:
                raise DosError("Invalid C drive size limit")
            media_limit = int(config.get("max_media_bytes", 128 * 1024 * 1024))
            if not 512 <= media_limit <= 256 * 1024 * 1024:
                raise DosError("Invalid media size limit")
            root_files = self._configured_files(config, limit)
            self.root.mkdir(parents=True, exist_ok=True)
            base = self.disk_dir
            marker = self.installed_path
            installed = json.loads(marker.read_text()) if marker.exists() else {}
            if not isinstance(installed, dict):
                raise DosError("Invalid DOS disk installation marker")
            initializing = installed.get("_complete") is not True
            self.initializing = initializing or install_sources
            if initializing:
                base.mkdir(parents=True, exist_ok=True)
            elif not base.is_dir():
                raise DosError("The initialised C drive is missing; restore the server disk backup")
            seen = set()
            if source_ids is None and self.source_selection:
                source_ids = self.source_selection()
            sources = config["sources"] if self.initializing else []
            if source_ids is not None:
                if set(source_ids) - {source.get("id") for source in config["sources"] if isinstance(source, dict)}:
                    raise DosError("Unknown DOS package")
                sources = [source for source in sources if isinstance(source, dict) and source.get("id") in source_ids]
            self.total = sum(1 for source in sources if isinstance(source, dict)
                             and (source_ids is not None or source.get("enabled") is not False))
            self.processed = 0
            for source in sources:
                if not isinstance(source, dict):
                    raise DosError("Each software source must be an object")
                if source_ids is None and source.get("enabled") is False:
                    continue
                ident = source.get("id", "")
                digest = source.get("sha256", "")
                if not ID_RE.fullmatch(ident) or ident in seen or (digest and not re.fullmatch(r"[0-9a-f]{64}", digest)):
                    raise DosError("Software sources need unique IDs and valid optional SHA-256 hashes")
                cache_key = digest or hashlib.sha256(json.dumps(
                    {"url": source.get("url"), "download_forms": source.get("download_forms", [])}, sort_keys=True
                ).encode()).hexdigest()
                seen.add(ident)
                additions = self._configured_files(source, limit)
                target = c_path(source["target"]) + "/" if source.get("target") else ""
                additions = {name: root_files.get(target + name, contents) for name, contents in additions.items()}
                if installed.get(ident) == cache_key:
                    # Resume/explicit install may fill missing configured files,
                    # but never overwrite the administrator's existing C files.
                    for name, contents in additions.items():
                        destination = base / (target + name)
                        if not destination.exists():
                            _atomic_file(destination, contents)
                        elif not destination.is_file() or destination.read_bytes() != contents:
                            raise DosError(f"Configured software file conflicts with existing C file: {target + name}")
                    self.processed += 1
                    continue
                self.current = str(source.get("title", ident))
                self._progress("Downloading", 0)
                cached = self.downloads_dir / cache_key
                legacy_cached = self.root / "downloads" / cache_key
                if cached.is_file():
                    data = cached.read_bytes()
                elif legacy_cached.is_file():
                    data = legacy_cached.read_bytes()
                else:
                    data = fetch_dos_source(source, MAX_SOURCE_BYTES, self._download_progress)
                if digest and hashlib.sha256(data).hexdigest() != digest:
                    raise DosError(f"SHA-256 mismatch for {ident}")
                _atomic_file(cached, data)
                self._progress("Extracting", 0.75)
                incoming = self._source_files(data, source)
                incoming.update(additions)
                incoming = {name: root_files.get(target + name, contents) for name, contents in incoming.items()}
                if len(incoming) > MAX_FILES or sum(len(value) for value in incoming.values()) > limit:
                    raise DosError("Software exceeds C drive quota")
                for index, (name, contents) in enumerate(incoming.items(), 1):
                    destination = base / (target + name)
                    if destination.exists():
                        if not destination.is_file() or destination.read_bytes() != contents:
                            raise DosError(f"Initial software conflicts with existing C file: {target + name}")
                    else:
                        _atomic_file(destination, contents)
                    self._progress("Installing", 0.75 + 0.25 * index / max(1, len(incoming)))
                installed[ident] = cache_key
                _atomic_file(marker, json.dumps(installed).encode())
                self.processed += 1
            for filename, contents in root_files.items():
                destination = base / filename
                if initializing or (install_sources and not destination.exists()):
                    if destination.exists() and not destination.is_file():
                        raise DosError(f"Configured DOS file is not a regular file: {filename}")
                    _atomic_file(destination, contents)
            files = {}
            self.phase = "Checking installed files"
            if (initializing or install_sources) and config.get("software_catalog"):
                guide = list(config["software_catalog"])
                if not all(isinstance(line, str) and "\n" not in line and "\r" not in line for line in guide):
                    raise DosError("DOS software_catalog must contain individual header lines")
                for source in config["sources"]:
                    if source.get("launch") and installed.get(source.get("id")):
                        guide.extend([str(source.get("title", source["id"])), "  " + source["launch"], ""])
                _atomic_file(base / "SOFTWARE.TXT", ("\r\n".join(guide) + "\r\n").encode("cp437", errors="replace"))
            for path in base.rglob("*"):
                if path.is_symlink():
                    raise DosError("Shared C drive must not contain symbolic links")
                if path.is_file():
                    files[c_path(path.relative_to(base).as_posix())] = path.read_bytes()
            if len(files) > MAX_FILES or sum(map(len, files.values())) > limit:
                raise DosError("Shared C drive exceeds configured limits")
            hasher = hashlib.sha256()
            hashes = {}
            for name, contents in sorted(files.items()):
                digest = hashlib.sha256(contents)
                hashes[name] = digest.hexdigest()
                hasher.update(name.encode() + b"\0" + digest.digest())
            if initializing:
                installed["_complete"] = True
                _atomic_file(marker, json.dumps(installed).encode())
            with self._lock:
                self.files, self.base_id, self.state = files, hasher.hexdigest(), "ready"
                self.file_hashes = hashes
                self.percent = 100
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            self.error, self.state = str(error), "error"
        finally:
            self.current = ""
            self.rebuilding = False

    def _progress(self, phase: str, fraction: float) -> None:
        self.phase = phase
        self.percent = min(99, int(100 * (self.processed + fraction) / max(1, self.total)))
        if self.on_progress:
            self.on_progress(self.status(start=False))

    def _download_progress(self, received: int, total: int) -> None:
        self.received = received
        self._progress("Downloading", min(1, received / total) * 0.75 if total > 0 else 0)

    def _configured_files(self, config: dict, limit: int) -> dict[str, bytes]:
        entries = config.get("files", [])
        if not isinstance(entries, list) or len(entries) > MAX_FILES:
            raise DosError("DOS files must be a list of file definitions")
        files = {}
        total = 0
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) not in ({"path", "text"}, {"path", "base64"}):
                raise DosError("Each DOS file needs path and exactly one of text/base64")
            name = c_path(entry["path"])
            if name in files:
                raise DosError("Duplicate configured DOS filename")
            if "text" in entry:
                lines = entry["text"]
                if not isinstance(lines, list) or not all(isinstance(line, str) and "\n" not in line and "\r" not in line for line in lines):
                    raise DosError("DOS text files must contain lists of individual lines")
                contents = ("\r\n".join(lines) + "\r\n").encode("cp437", errors="replace")
            else:
                encoded = entry["base64"]
                if not isinstance(encoded, str) or len(encoded) > 4 * ((limit + 2) // 3):
                    raise DosError("Configured binary DOS file exceeds its quota")
                try:
                    contents = base64.b64decode(encoded, validate=True)
                except ValueError as error:
                    raise DosError("Invalid base64 in configured DOS file") from error
            total += len(contents)
            if total > limit:
                raise DosError("Configured DOS files exceed the C drive quota")
            files[name] = contents
        return files

    def _source_files(self, data: bytes, source: dict) -> dict[str, bytes]:
        patterns = source.get("members", ["*"])
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise DosError("Invalid software member selection")
        if source.get("format") == "zip":
            files = {}
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if len(archive.infolist()) > MAX_FILES:
                    raise DosError("Too many software archive entries")
                total = 0
                for entry in archive.infolist():
                    if entry.is_dir():
                        continue
                    name = c_path(entry.filename)
                    if stat.S_ISLNK(entry.external_attr >> 16):
                        raise DosError("Software archive contains a symbolic link")
                    total += entry.file_size
                    if total > int(self.config.get("max_c_bytes", MAX_SOURCE_BYTES)):
                        raise DosError("Software archive expands beyond its quota")
                    if any(fnmatch(name, pattern.upper()) for pattern in patterns):
                        if name in files:
                            raise DosError("Duplicate DOS filename in software archive")
                        files[name] = archive.read(entry)
            return files
        if source.get("format") not in ("img", "archive"):
            raise DosError("Software sources must be zip, img or archive")
        tools = ExtractorTools(find_unar(), find_lsar(), find_sevenzip())
        if not tools.available:
            raise DosError("IMG extraction needs unar/lsar or 7zz; rebuild the Docker image")
        # Reuse the downloader's image extractor; these are admin-configured,
        # hash-pinned images, never untrusted media uploaded by a player.
        with tempfile.TemporaryDirectory(prefix="thelp-dos-image-") as temporary:
            image = Path(temporary) / ("software.img" if source.get("format") == "img" else "software.archive")
            image.write_bytes(data)
            directory = Path(temporary) / "contents"
            if not extract_file(image, directory, tools):
                raise DosError("Cannot extract configured software image")
            if source.get("image_member"):
                wanted = c_path(source["image_member"])
                candidates = [path for path in directory.rglob("*") if path.is_file()
                              and c_path(path.relative_to(directory).as_posix()) == wanted]
                if len(candidates) != 1:
                    raise DosError("Configured disk image is missing from the software archive")
                contents = Path(temporary) / "disk-contents"
                if not extract_file(candidates[0], contents, tools):
                    raise DosError("Cannot extract configured inner disk image")
                directory = contents
            files = {}
            for path in directory.rglob("*"):
                if path.is_symlink():
                    raise DosError("Unsafe software image")
                if path.is_file():
                    name = c_path(path.relative_to(directory).as_posix())
                    if any(fnmatch(name, pattern.upper()) for pattern in patterns):
                        files[name] = path.read_bytes()
                    if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_SOURCE_BYTES:
                        raise DosError("Software image expands beyond its quota")
            return files

    def status(self, *, start: bool = True) -> dict:
        if start:
            self.start()
        return {"state": self.state, "current": self.current, "error": self.error,
                "initializing": self.initializing, "processed": self.processed, "total": self.total,
                "percent": self.percent, "phase": self.phase, "received": self.received,
                "backup": self.backup, "rebuilding": self.rebuilding}

    def _user_dir(self, account_id: str) -> Path:
        if not ACCOUNT_RE.fullmatch(account_id):
            raise DosError("Invalid account storage ID")
        directory = self.users_dir / account_id
        if directory.is_symlink() or directory.parent.is_symlink():
            raise DosError("Private user storage must not be a symbolic link")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _check_private_path(self, path: Path) -> None:
        parts = path.relative_to(self.users_dir).parts
        if self.users_dir.is_symlink() or any(
                self.users_dir.joinpath(*parts[:index]).is_symlink() for index in range(1, len(parts) + 1)):
            raise DosError("Private C storage must not contain symbolic links")

    def _database(self, account_id: str) -> sqlite3.Connection:
        database = sqlite3.connect(self._user_dir(account_id) / "overlay.sqlite3", timeout=15)
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
        root = self._user_dir(account_id) / "c"
        if root.is_symlink():
            raise DosError("Private C storage must not be a symbolic link")
        root.mkdir(exist_ok=True)
        pending = Path(tempfile.mkdtemp(prefix="pending-", dir=root))
        snapshot = root / str(revision)
        try:
            for name in directories:
                (pending / c_path(name)).mkdir(parents=True, exist_ok=True)
            for name, contents in files.items():
                _atomic_file(pending / c_path(name), contents)
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
            snapshot = self._user_dir(account_id) / "c" / str(revision)
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

    def save(self, account_id: str, payload: dict) -> int:
        limit = self.overlay_limit(account_id)
        if payload.get("base_id") != self.base_id:
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
            if contents != self.files.get(canonical):
                total += len(contents)
                if total > limit:
                    raise DosError("Overlay exceeds its quota")
                files[canonical] = contents
        tombstones = {c_path(name) for name in deleted}
        if not isinstance(directories, list) or len(directories) > MAX_FILES:
            raise DosError("Invalid directory list")
        folders = {c_path(name) for name in directories}
        merged = {name: data for name, data in self.files.items() if name not in tombstones}
        merged.update(files)
        if len(merged) > MAX_FILES:
            raise DosError("Too many C drive files")
        if folders.intersection(merged):
            raise DosError("A path cannot be both a file and a directory")
        for name in merged.keys() | folders:
            parts = name.split("/")
            if any("/".join(parts[:index]) in merged for index in range(1, len(parts))):
                raise DosError("A file cannot contain another path")
        if any(name not in self.files or name in files for name in tombstones):
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
            previous = self._user_dir(account_id) / "c" / str(revision - 1)
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

    def c_limit(self, account_id: str | None) -> int:
        return (sum(map(len, self.files.values())) + self.overlay_limit(account_id) if account_id
                else int(self.config.get("max_c_bytes", MAX_SOURCE_BYTES)))

    def overlay_limit(self, account_id: str | None = None) -> int:
        override = self.accounts.disk_capacity(account_id) if self.accounts and account_id else None
        return (override if override is not None else self.settings.get()["dos_user_disk_mb"]) * 1024 * 1024

    def disk_usage(self, account_id: str) -> dict:
        # Read the committed generation only; recovery copies and common C files
        # do not count towards the user's quota. Do not boot/download DOS here.
        path = self._user_dir(account_id) / "overlay.sqlite3"
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

    def bundle(self, account_id: str | None, media_id: str = "", *, lazy: bool = False, account_name: str = "") -> tuple[bytes, dict]:
        revision, overlay, deleted, directories = self.overlay(account_id)
        files = {name: data for name, data in self.files.items() if name not in deleted}
        files.update(overlay)
        remote_files = {name: {"size": len(data), "sha256": (self.file_hashes.get(name) if name not in overlay else None)
                              or hashlib.sha256(data).hexdigest(), "base": name not in overlay}
                        for name, data in files.items()} if lazy else {}
        commands = ["@echo off", "mount c drive_c"]
        media = self.media_path(account_id, media_id) if media_id and account_id else None
        if media_id and media is None:
            raise DosError("Media not found for this account")
        if media:
            kind = "floppy" if media.suffix == ".img" else "iso"
            drive = "a" if kind == "floppy" else "d"
            commands.append(f"imgmount {drive} media/{media.name} -t {kind}")
        commands += ["config -securemode", "c:", "set PATH=C:\\FREEDOS\\BIN;Z:\\", "cls",
                     "echo THelpViewer DOS Prompt - use the DOS Prompt menu for media.",
                     "if exist C:\\AUTOEXEC.BAT call C:\\AUTOEXEC.BAT",
                     "Z:\\COMMAND.COM", "echo THelpViewer DOS session ended.", "pause >nul"]
        cycles = str(self.config.get("cycles", "auto"))
        if not re.fullmatch(r"auto|max|[0-9]{1,6}", cycles):
            raise DosError("Invalid DOS cycles setting")
        memory = int(self.config.get("memory_mb", 16))
        if not 4 <= memory <= 64:
            raise DosError("Invalid DOS memory setting")
        conf = f"[dosbox]\nmemsize={memory}\n[sdl]\nautolock=false\n[cpu]\ncycles={cycles}\n[autoexec]\n" + "\n".join(commands) + "\n"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(".jsdos/", b"")
            archive.writestr(".jsdos/dosbox.conf", conf)
            if lazy:
                archive.writestr(".jsdos/disk.json", json.dumps({"base_id": self.base_id, "account": account_name, "files": remote_files}))
            archive.writestr("drive_c/", b"")
            folders = set(directories)
            for name in [*files, *directories]:
                parts = name.split("/")
                folders.update("/".join(parts[:index]) for index in range(1, len(parts)))
            # libzip in DOSBox does not synthesise missing parent directories.
            for directory in sorted(folders, key=lambda name: (name.count("/"), name)):
                archive.writestr("drive_c/" + directory + "/", b"")
            if not lazy:
                for name, contents in sorted(files.items()):
                    archive.writestr("drive_c/" + name, contents)
        metadata = {
            "base_id": self.base_id, "revision": revision,
            "files": {name: self.file_hashes.get(name) or hashlib.sha256(data).hexdigest() for name, data in self.files.items()},
            "media": media.name if media else "", "max_c_bytes": self.c_limit(account_id),
            "max_overlay_bytes": self.overlay_limit(account_id) if account_id else 0,
            "overlay_files": list(overlay), "remote_files": remote_files,
            "allow_full_disk_fallback": self.config.get("allow_full_disk_fallback") is True,
            "max_media_bytes": self.config.get("max_media_bytes", 128 * 1024 * 1024),
        }
        return buffer.getvalue(), metadata

    def read_chunk(self, account_id: str | None, name: str, digest: str, base_file: bool, offset: int, size: int) -> bytes:
        name = c_path(name)
        if offset < 0 or not 1 <= size <= 65536:
            raise DosError("Invalid DOS file chunk")
        if base_file:
            data = self.files.get(name)
            if data is None or (self.file_hashes.get(name) or hashlib.sha256(data).hexdigest()) != digest:
                raise DosError("DOS file changed; reload the disk")
            return data[offset:offset + size]
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
            path = self._user_dir(account_id) / "c" / str(revision) / name
            self._check_private_path(path)
            with path.open("rb") as handle:
                handle.seek(offset)
                data = handle.read(size)
            database.commit()
            return data
        finally:
            database.close()

    def add_media(self, account_id: str, kind: str, data: bytes) -> str:
        if kind not in ("floppy", "cd"):
            raise DosError("Only floppy and CD images may be mounted")
        if kind == "floppy":
            if len(data) % 512 or len(data) < 512 or len(data) > 16 * 1024 * 1024 or data[510:512] != b"\x55\xaa":
                raise DosError("Invalid raw floppy image")
        elif len(data) < 32774 or data[32769:32774] != b"CD001":
            raise DosError("CD media must be an ISO9660 image")
        if len(data) > int(self.config.get("max_media_bytes", 128 * 1024 * 1024)):
            raise DosError("Media exceeds its configured quota")
        directory = self._user_dir(account_id) / "media"
        directory.mkdir(exist_ok=True)
        ident = hashlib.sha256(data).hexdigest()[:32] + (".img" if kind == "floppy" else ".iso")
        if (directory / ident).is_file():
            return ident
        if len(list(directory.iterdir())) >= 8:
            raise DosError("Media library is full (8 images)")
        _atomic_file(directory / ident, data)
        return ident

    def media_path(self, account_id: str, ident: str) -> Path | None:
        if not re.fullmatch(r"[a-f0-9]{32}\.(img|iso)", ident):
            return None
        path = self._user_dir(account_id) / "media" / ident
        return path if path.is_file() and not path.is_symlink() else None
