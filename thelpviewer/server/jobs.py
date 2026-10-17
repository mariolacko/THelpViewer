"""Durable operation intent, safe checkpoints and shared processing progress.

Files remain owned and validated by HELP/DOS/MIDI/index components. A saved
percentage is diagnostic information, never evidence that an artifact is valid.
"""

from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from .file_storage import file_digest


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._owner = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._transaction() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, payload TEXT NOT NULL,
                    state TEXT NOT NULL, progress TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0,
                    created REAL NOT NULL, updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_steps (
                    job_id TEXT NOT NULL REFERENCES jobs(id), step TEXT NOT NULL,
                    state TEXT NOT NULL, fingerprint TEXT NOT NULL, detail TEXT NOT NULL,
                    PRIMARY KEY(job_id, step)
                );
                CREATE TABLE IF NOT EXISTS queue_jobs (
                    kind TEXT PRIMARY KEY, state TEXT NOT NULL, batch INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS queue_items (
                    kind TEXT NOT NULL REFERENCES queue_jobs(kind) ON DELETE CASCADE,
                    id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind, id)
                );
            """)

    @contextmanager
    def _transaction(self):
        # Short transactions, including FULL-synchronous commits. Do not enable
        # WAL on a database that an administrator may access through SMB.
        with self._lock, closing(sqlite3.connect(self.path, timeout=15)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                yield connection

    def acquire(self):
        """Only one application process may recover/execute this job journal."""
        with self._lock:
            if self._owner is not None:
                raise RuntimeError("The job journal already has a running owner")
            owner = self.path.with_suffix(".lock").open("a+b")
            try:
                if os.name == "nt":
                    import msvcrt
                    if owner.tell() == 0:
                        owner.write(b"0")
                        owner.flush()
                    owner.seek(0)
                    msvcrt.locking(owner.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                owner.close()
                raise RuntimeError("Another server is using this job journal") from None
            self._owner = owner
            try:
                with self._transaction() as connection:
                    connection.execute("UPDATE jobs SET state='interrupted', updated=? WHERE state='running'", (time.time(),))
            except BaseException:
                self.release()
                raise

    def release(self):
        with self._lock:
            if self._owner is not None:
                if os.name == "nt":
                    import msvcrt
                    self._owner.seek(0)
                    msvcrt.locking(self._owner.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._owner, fcntl.LOCK_UN)
                self._owner.close()
                self._owner = None

    def create(self, kind, payload):
        ident, now = uuid.uuid4().hex, time.time()
        with self._transaction() as connection:
            connection.execute("INSERT INTO jobs(id,kind,payload,state,created,updated) VALUES (?,?,?,'queued',?,?)",
                               (ident, kind, json.dumps(payload), now, now))
        return ident

    def claim(self, ident):
        with self._transaction() as connection:
            changed = connection.execute("""UPDATE jobs SET state='running', attempts=attempts+1, updated=?
                WHERE id=? AND state IN ('queued','interrupted')""", (time.time(), ident)).rowcount
            if not changed:
                raise ValueError("Job is already claimed or finished")

    def update(self, ident, state, progress=None, error=""):
        with self._transaction() as connection:
            connection.execute("UPDATE jobs SET state=?, progress=coalesce(?,progress), error=?, updated=? WHERE id=?",
                (state, json.dumps(progress) if progress is not None else None, error, time.time(), ident))

    def pending(self, kind):
        with self._transaction() as connection:
            rows = connection.execute("""SELECT * FROM jobs WHERE kind=?
                AND state IN ('queued','running','interrupted') ORDER BY sequence""", (kind,)).fetchall()
        return [self._job(row) for row in rows]

    def latest(self, kind):
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE kind=? ORDER BY sequence DESC LIMIT 1", (kind,)).fetchone()
        return self._job(row) if row else None

    @staticmethod
    def _job(row):
        return {**dict(row), "payload": json.loads(row["payload"]), "progress": json.loads(row["progress"])}

    def checkpoint(self, ident, step, *, state="done", fingerprint="", detail=None):
        with self._transaction() as connection:
            connection.execute("INSERT OR REPLACE INTO job_steps VALUES (?,?,?,?,?)",
                (ident, step, state, fingerprint, json.dumps(detail or {})))

    def steps(self, ident):
        with self._transaction() as connection:
            rows = connection.execute("SELECT * FROM job_steps WHERE job_id=?", (ident,)).fetchall()
        return {row["step"]: {**dict(row), "detail": json.loads(row["detail"])} for row in rows}

    def checkpoint_files(self, ident, step, root, files):
        inventory = {path.relative_to(root).as_posix(): file_digest(path) for path in files}
        self.checkpoint(ident, step, detail={"files": inventory})

    @staticmethod
    def files_valid(root, step):
        files = step["detail"].get("files", {})
        if not files:
            return False
        for name, digest in files.items():
            relative = Path(name)
            path = root / relative
            if (relative.is_absolute() or ".." in relative.parts
                    or any(parent.is_symlink() for parent in (path, *path.parents))):
                return False
            try:
                if not path.is_file() or file_digest(path) != digest:
                    return False
            except OSError:
                return False
        return True

    def load_queue(self):
        with self._transaction() as connection:
            jobs = {row["kind"]: {"state": row["state"], "batch": row["batch"], "items": {}}
                    for row in connection.execute("SELECT * FROM queue_jobs")}
            for row in connection.execute("SELECT * FROM queue_items ORDER BY rowid"):
                jobs[row["kind"]]["items"][row["id"]] = json.loads(row["payload"])
        return jobs

    def save_queue(self, kind, state, batch, items):
        with self._transaction() as connection:
            connection.execute("INSERT INTO queue_jobs VALUES (?,?,?) ON CONFLICT(kind) DO UPDATE SET state=?,batch=?",
                               (kind, state, batch, state, batch))
            connection.execute("DELETE FROM queue_items WHERE kind=?", (kind,))
            connection.executemany("INSERT INTO queue_items VALUES (?,?,?)",
                [(kind, item["id"], json.dumps(item)) for item in items])

    def save_queue_item(self, kind, item):
        with self._transaction() as connection:
            connection.execute("""INSERT INTO queue_items VALUES (?,?,?)
                ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload""", (kind, item["id"], json.dumps(item)))
