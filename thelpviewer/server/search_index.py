"""Incremental, server-side full-text index of generated UHF HELP bundles."""

from __future__ import annotations

import gzip
import json
import logging
import re
import sqlite3
import threading
import zlib
from contextlib import closing, contextmanager
from pathlib import Path

from ..public_docs import public_doc_sources
from .converter.text_screen import screen_text_lines


_TAG = re.compile(r"\[(?:/?[A-Za-z][^\]\n]*|rule)\]")
_WORD = re.compile(r"\w+", re.UNICODE)
_LOGGER = logging.getLogger(__name__)
_HELP_INDEX_REVISION = "4"


def _plain(value: object) -> str:
    return _TAG.sub("", str(value or "").replace("[[", "\ue000")).replace("\ue000", "[").strip()


def _catalog_names(helps_dir: Path) -> dict[str, str]:
    try:
        catalog = json.loads((helps_dir / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        entry["file"]: str(entry.get("name") or "")
        for entry in catalog if isinstance(entry, dict) and isinstance(entry.get("file"), str)
    } if isinstance(catalog, list) else {}


def _catalog_sources(helps_dir: Path) -> dict[str, str]:
    try:
        catalog = json.loads((helps_dir / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        entry["file"]: str(entry.get("source_file") or "")
        for entry in catalog if isinstance(entry, dict) and isinstance(entry.get("file"), str)
    } if isinstance(catalog, list) else {}


def _topic_records(bundle: dict):
    topics = bundle.get("topics", {})
    entries = topics.items() if isinstance(topics, dict) else enumerate(topics) if isinstance(topics, list) else ()
    for key, topic in entries:
        if isinstance(topic, dict):
            yield str(topic.get("id", key)), topic


def _alias_key(value: str, case_sensitive: bool = False) -> str:
    value = value.strip()
    if not case_sensitive:
        return value.lower()
    qualifier, separator, context = value.partition("!")
    return qualifier.lower() + separator + context if separator else value


def _topic_alias_rows(bundle: dict, file_path: str):
    records = list(_topic_records(bundle))
    seen: set[tuple[str, bool]] = set()
    databases = bundle.get("metadata", {}).get("quickhelp_databases", [])
    databases = databases if isinstance(databases, list) else []
    for context_id, topic in records:
        aliases = topic.get("aliases")
        if not isinstance(aliases, dict):
            continue
        case_sensitive = any(isinstance(database, dict) and database.get("case_sensitive")
                             and isinstance(database.get("first_topic_id"), int)
                             and isinstance(database.get("topic_count"), int)
                             and context_id.isdecimal()
                             and database["first_topic_id"] <= int(context_id)
                             < database["first_topic_id"] + database["topic_count"]
                             for database in databases)
        ids, strings = aliases.get("ids", []), aliases.get("strings", [])
        values = [(value, False) for value in ids] if isinstance(ids, list) else []
        values += [(value, bool(case_sensitive)) for value in strings if isinstance(value, str)] if isinstance(strings, list) else []
        lines = aliases.get("lines", {})
        for value, exact in values:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                continue
            alias = _alias_key(str(value), exact)
            # Store source aliases even when their spelling is a real UHF ID.
            # The request's topic/alias namespace determines lookup priority.
            # Duplicate aliases use the first definition in each namespace.
            if not alias or (alias, exact) in seen:
                continue
            seen.add((alias, exact))
            line = lines.get(str(value)) if isinstance(lines, dict) else None
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                line = None
            yield file_path, alias, context_id, line, int(exact)


def _topic_rows(bundle: dict, file_path: str, help_name: str):
    terms: dict[str, list[str]] = {}
    for group in bundle.get("index", []):
        if not isinstance(group, dict):
            continue
        for entry in group.get("entries", []):
            if isinstance(entry, dict) and entry.get("topic_id") is not None and not entry.get("file"):
                terms.setdefault(str(entry["topic_id"]), []).append(_plain(entry.get("label")))
    for context_id, topic in _topic_records(bundle):
        title = _plain(topic.get("title")) or f"Topic {context_id}"
        content = topic.get("content")
        lines = []
        in_code = False
        for line in content if isinstance(content, list) else []:
            if isinstance(line, str) and re.fullmatch(r"\[code(?::[A-Za-z0-9_-]+)?\]", line, re.IGNORECASE):
                in_code = True
            elif line == "[/code]":
                in_code = False
            screen_lines = screen_text_lines(bundle, line) if isinstance(line, str) and not in_code else None
            lines.extend(screen_lines if screen_lines is not None else [_plain(line)])
        lines = [line for line in lines if line]
        preview = " ".join(lines[:3])[:180]
        yield (
            file_path, help_name, context_id, title,
            json.dumps(list(dict.fromkeys(terms.get(context_id, []))), ensure_ascii=False),
            "\n".join(lines), preview,
        )


class GlobalSearchIndex:
    """One background writer for public HELP topics and Docs."""

    def __init__(self, helps_dir: Path, state_dir: Path, docs_dir: Path | None = None,
                 virtual_docs: tuple[tuple[str, Path], ...] = (), *, journal=None):
        self.helps_dir = helps_dir
        self.docs_dir = docs_dir
        self.virtual_docs = virtual_docs
        self.path = state_dir / "global-search.sqlite3"
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._pauses = 0
        self.journal = journal
        self._job_id = None
        self._worker = None
        self._stopping = False
        self._completed = 0
        self._building = False
        self._available = False
        self._failed_files: dict[tuple[str, str], tuple[str, str]] = {}
        self._pending_files: set[tuple[str, str]] = set()
        self._failed_snapshot = None
        self._status = {"state": "idle", "percent": 0, "processed": 0, "total": 0,
                        "topics": 0, "documents": 0, "file": ""}
        if journal:
            previous = journal.latest("index")
            if previous:
                self._failed_files = {
                    tuple(key.split(":", 1)): (step["fingerprint"], step["detail"].get("error", ""))
                    for key, step in journal.steps(previous["id"]).items() if step["state"] == "error"
                }

    def close(self):
        with self._lock:
            self._stopping = True
            worker = self._worker
        if worker and worker is not threading.current_thread():
            worker.join()

    def _record_job(self, state):
        if self.journal and self._job_id:
            self.journal.update(self._job_id, state, self._status, self._status.get("error", ""))

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("""CREATE TABLE IF NOT EXISTS files (
            file_path TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
            help_name TEXT NOT NULL, topic_count INTEGER NOT NULL
        )""")
        connection.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
            file_path UNINDEXED, help_name UNINDEXED, context_id UNINDEXED,
            title, index_terms, body, preview UNINDEXED,
            tokenize='unicode61 remove_diacritics 2'
        )""")
        alias_columns = [row[1] for row in connection.execute("PRAGMA table_info(topic_aliases)")]
        if alias_columns and alias_columns != ["file_path", "alias", "context_id", "line", "case_sensitive"]:
            # This is a rebuildable search cache, not account/user data.
            connection.execute("DROP TABLE topic_aliases")
            connection.execute("UPDATE files SET fingerprint = ''")
        connection.execute("""CREATE TABLE IF NOT EXISTS topic_aliases (
            file_path TEXT NOT NULL, alias TEXT NOT NULL, context_id TEXT NOT NULL,
            line INTEGER, case_sensitive INTEGER NOT NULL,
            PRIMARY KEY(file_path, alias, case_sensitive)
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS docs_files (
            doc_path TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, title TEXT NOT NULL
        )""")
        connection.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
            doc_path UNINDEXED, title, body, preview UNINDEXED,
            tokenize='unicode61 remove_diacritics 2'
        )""")
        connection.commit()
        return connection

    def _snapshot(self) -> dict[str, tuple[Path, str, str]]:
        names = _catalog_names(self.helps_dir)
        found = {}
        if not self.helps_dir.is_dir():
            return found
        for path in self.helps_dir.rglob("*.json.gz"):
            if not path.is_file():
                continue
            relative = path.relative_to(self.helps_dir).as_posix()
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue  # The source disappeared while scanning.
            name = names.get(relative) or ""
            fingerprint = f"{_HELP_INDEX_REVISION}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}:{name}"
            found[relative] = (path, fingerprint, name)
        return found

    def _docs_snapshot(self) -> dict[str, tuple[Path, str, str]]:
        if self.docs_dir is None:
            return {}
        found = {}
        seen_paths = set()
        for relative, path in public_doc_sources(self.docs_dir, self.virtual_docs).items():
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            title = Path(relative).stem.replace("_", " ")
            found[relative] = (path, f"{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}", title)
        return found

    @contextmanager
    def suspend(self):
        """Yield the disk/CPU to HELP processing, then rescan published content.

        Finish the current source transaction before handing over. Stop the
        writer at a file boundary rather than holding SQLite open while paused.
        Nested/concurrent holders resume only after the final one leaves.
        """
        with self._condition:
            self._pauses += 1
            while self._building:
                self._condition.wait()
        try:
            yield
        finally:
            with self._condition:
                self._pauses -= 1
            self.ensure_current()

    def ensure_current(self) -> None:
        with self._lock:
            if self._building or self._pauses or self._stopping:
                return
            try:
                snapshot = self._snapshot()
                docs_snapshot = self._docs_snapshot()
                with closing(self._connect()) as connection:
                    indexed = {
                        row[0]: row[1] for row in connection.execute("SELECT file_path, fingerprint FROM files")
                    }
                    indexed_docs = {
                        row[0]: row[1] for row in connection.execute("SELECT doc_path, fingerprint FROM docs_files")
                    }
                    topic_count = connection.execute("SELECT coalesce(sum(topic_count), 0) FROM files").fetchone()[0]
                    doc_count = connection.execute("SELECT count(*) FROM docs_files").fetchone()[0]
                if self._status["state"] != "error":
                    self._available = self._available or bool(indexed or indexed_docs)
                for key in list(self._failed_files):
                    kind, name = key
                    if name not in (snapshot if kind == "help" else docs_snapshot):
                        del self._failed_files[key]
                work = sorted(
                    [("help", name) for name, (_path, fingerprint, _title) in snapshot.items()
                     if indexed.get(name) != fingerprint
                     and self._failed_files.get(("help", name), (None,))[0] != fingerprint]
                    + [("help", name) for name in indexed if name not in snapshot]
                    + [("doc", name) for name, (_path, fingerprint, _title) in docs_snapshot.items()
                       if indexed_docs.get(name) != fingerprint
                       and self._failed_files.get(("doc", name), (None,))[0] != fingerprint]
                    + [("doc", name) for name in indexed_docs if name not in docs_snapshot],
                    key=lambda item: (item[1] in (snapshot if item[0] == "help" else docs_snapshot), *item),
                )
                if not work:
                    self._available = True
                    self._pending_files.clear()
                    self._status = {"state": "ready", "percent": 100, "processed": 0,
                                    "total": len(snapshot) + len(docs_snapshot), "topics": topic_count,
                                    "documents": doc_count, "file": ""}
                    self._failed_snapshot = None
                    if self.journal:
                        for job in self.journal.pending("index"):
                            self.journal.update(job["id"], "done", self._status)
                    return
                signature = tuple((kind, name,
                                   (snapshot if kind == "help" else docs_snapshot).get(name, (None, None, None))[1])
                                  for kind, name in work)
                if signature == self._failed_snapshot:
                    return
                self._building = True
                self._pending_files = {
                    (kind, name) for kind, name in work
                    if name in (snapshot if kind == "help" else docs_snapshot)
                }
                self._status = {"state": "building", "percent": 0, "processed": 0,
                                "total": len(work), "topics": topic_count,
                                "documents": doc_count, "file": ""}
                self._completed = 0
                if self.journal:
                    pending = self.journal.pending("index")
                    self._job_id = pending[0]["id"] if pending else self.journal.create("index", {})
                    self.journal.claim(self._job_id)
                    for (kind, name), (fingerprint, error) in self._failed_files.items():
                        self.journal.checkpoint(self._job_id, kind + ":" + name, state="error",
                            fingerprint=fingerprint, detail={"error": error})
                    for key, step in self.journal.steps(self._job_id).items():
                        kind, name = key.split(":", 1)
                        sources = snapshot if kind == "help" else docs_snapshot
                        if step["fingerprint"] == sources.get(name, (None, "missing", None))[1]:
                            self._completed += 1
                    self._status.update(processed=self._completed, total=self._completed + len(work),
                        percent=round(100 * self._completed / (self._completed + len(work))))
                    self._record_job("running")
            except (OSError, ValueError, sqlite3.Error) as error:
                self._building = False
                self._condition.notify_all()
                self._available = False
                self._status = {"state": "error", "percent": 0, "processed": 0,
                                "total": 0, "topics": 0, "documents": 0, "file": "", "error": str(error)}
                return
            self._worker = threading.Thread(target=self._build, args=(snapshot, docs_snapshot, work, signature),
                                             daemon=True, name="thelp-global-index")
            self._worker.start()

    @staticmethod
    def _remove_indexed_source(connection: sqlite3.Connection, kind: str, relative: str) -> None:
        if kind == "help":
            connection.execute("DELETE FROM topic_aliases WHERE file_path = ?", (relative,))
            connection.execute("DELETE FROM topics_fts WHERE file_path = ?", (relative,))
            connection.execute("DELETE FROM files WHERE file_path = ?", (relative,))
        else:
            connection.execute("DELETE FROM docs_fts WHERE doc_path = ?", (relative,))
            connection.execute("DELETE FROM docs_files WHERE doc_path = ?", (relative,))

    def _update_source(self, connection: sqlite3.Connection, kind: str, relative: str, snapshot: dict) -> None:
        if relative not in snapshot:
            with connection:
                self._remove_indexed_source(connection, kind, relative)
            return
        path, fingerprint, title = snapshot[relative]
        if kind == "help":
            with gzip.open(path, "rt", encoding="utf-8") as source:
                bundle = json.load(source)
            if (not isinstance(bundle, dict) or not isinstance(bundle.get("topics"), (dict, list))
                    or not isinstance(bundle.get("metadata", {}), dict)
                    or not isinstance(bundle.get("index", []), list)):
                raise ValueError("Invalid UHF document structure")
            help_name = title or str(bundle.get("metadata", {}).get("name") or relative)
            rows = list(_topic_rows(bundle, relative, help_name))
            with connection:
                self._remove_indexed_source(connection, kind, relative)
                connection.executemany(
                    "INSERT INTO topics_fts(file_path, help_name, context_id, title, index_terms, body, preview) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)", rows,
                )
                connection.executemany(
                    "INSERT INTO topic_aliases(file_path, alias, context_id, line, case_sensitive) VALUES (?, ?, ?, ?, ?)",
                    _topic_alias_rows(bundle, relative),
                )
                connection.execute(
                    "INSERT INTO files(file_path, fingerprint, help_name, topic_count) VALUES (?, ?, ?, ?)",
                    (relative, fingerprint, help_name, len(rows)),
                )
        else:
            body = path.read_text(encoding="utf-8", errors="replace")
            preview = " ".join(line.strip(" #>*-`\t") for line in body.splitlines() if line.strip())[:180]
            with connection:
                self._remove_indexed_source(connection, kind, relative)
                connection.execute(
                    "INSERT INTO docs_fts(doc_path, title, body, preview) VALUES (?, ?, ?, ?)",
                    (relative, title, body, preview),
                )
                connection.execute(
                    "INSERT INTO docs_files(doc_path, fingerprint, title) VALUES (?, ?, ?)",
                    (relative, fingerprint, title),
                )

    def _build(self, snapshot: dict, docs_snapshot: dict,
               work: list[tuple[str, str]], signature: tuple) -> None:
        try:
            with closing(self._connect()) as connection:
                for position, (kind, relative) in enumerate(work, 1):
                    with self._lock:
                        if self._pauses or self._stopping:
                            self._record_job("interrupted")
                            return
                    sources = snapshot if kind == "help" else docs_snapshot
                    try:
                        self._update_source(connection, kind, relative, sources)
                    except (OSError, EOFError, ValueError, TypeError, zlib.error) as error:
                        # File/format failures are isolated; database failures are
                        # still fatal rather than silently hiding a broken DB.
                        with connection:
                            self._remove_indexed_source(connection, kind, relative)
                        fingerprint = sources.get(relative, (None, "", None))[1]
                        with self._lock:
                            self._failed_files[(kind, relative)] = (fingerprint, str(error))
                        if self.journal:
                            self.journal.checkpoint(self._job_id, kind + ":" + relative, state="error",
                                fingerprint=fingerprint, detail={"error": str(error)})
                        _LOGGER.warning("Cannot index %s %s: %s", kind, relative, error)
                    else:
                        with self._lock:
                            self._failed_files.pop((kind, relative), None)
                            self._available = True
                        if self.journal:
                            self.journal.checkpoint(self._job_id, kind + ":" + relative,
                                fingerprint=sources.get(relative, (None, "missing", None))[1])
                    with self._lock:
                        self._pending_files.discard((kind, relative))
                    count = connection.execute("SELECT coalesce(sum(topic_count), 0) FROM files").fetchone()[0]
                    documents = connection.execute("SELECT count(*) FROM docs_files").fetchone()[0]
                    with self._lock:
                        total, processed = self._completed + len(work), self._completed + position
                        self._status = {"state": "building", "percent": round(processed * 100 / total),
                                        "processed": processed, "total": total, "topics": count,
                                        "documents": documents, "file": relative}
                        self._record_job("running")
            with self._lock:
                self._status = {**self._status, "state": "ready", "percent": 100, "file": ""}
                self._available = True
                self._failed_snapshot = None
                self._record_job("done")
        except (OSError, ValueError, sqlite3.Error) as error:
            with self._lock:
                self._status = {**self._status, "state": "error", "error": str(error)}
                self._available = False
                self._failed_snapshot = signature
                self._record_job("error")
        finally:
            with self._condition:
                self._building = False
                self._condition.notify_all()

    def status(self) -> dict:
        self.ensure_current()
        with self._lock:
            return {**self._status,
                    **({"state": "paused", "phase": "Waiting for HELP processing", "file": ""} if self._pauses else {}),
                    "available": self._available,
                    "warnings": [{"kind": kind, "file": name, "error": error}
                                 for (kind, name), (_fingerprint, error) in sorted(self._failed_files.items())]}

    def file_error(self, kind: str, path: str) -> str | None:
        with self._lock:
            failure = self._failed_files.get((kind, path))
            return failure[1] if failure else None

    def file_pending(self, kind: str, path: str) -> bool:
        with self._lock:
            return (kind, path) in self._pending_files

    def search(self, query: str, limit: int = 60) -> tuple[dict, list[dict]]:
        status = self.status()
        if not status["available"]:
            return status, []
        words = _WORD.findall(query.casefold())[:8]
        if not words:
            return status, []
        expression = " AND ".join(f'"{word}"*' for word in words)
        result_limit = max(1, min(60, limit))
        with closing(self._connect()) as connection:
            help_rows = connection.execute("""SELECT file_path, help_name, context_id, title,
                       index_terms, preview, bm25(topics_fts, 0, 0, 0, 12, 8, 1, 0)
                       FROM topics_fts WHERE topics_fts MATCH ?
                       ORDER BY bm25(topics_fts, 0, 0, 0, 12, 8, 1, 0) LIMIT ?""",
                (expression, result_limit),
            ).fetchall()
            doc_rows = connection.execute("""SELECT doc_path, title, preview,
                       bm25(docs_fts, 0, 12, 1, 0) FROM docs_fts WHERE docs_fts MATCH ?
                       ORDER BY bm25(docs_fts, 0, 12, 1, 0) LIMIT ?""",
                (expression, result_limit),
            ).fetchall()
        sources = _catalog_sources(self.helps_dir)
        ranked = [
            (row[6], {"kind": "help", "file": row[0], "help_name": row[1],
                      "context_hex": row[2], "title": row[3],
                      "index_terms": json.loads(row[4]) if row[4] else [],
                      "preview": row[5], "text": "", "source_file": sources.get(row[0]) or row[0]})
            for row in help_rows
        ]
        ranked.extend(
            (row[3], {"kind": "doc", "file": row[0], "help_name": "Docs",
                      "context_hex": "", "title": row[1], "index_terms": [],
                      "preview": row[2], "text": "", "source_file": row[0]})
            for row in doc_rows
        )
        ranked.sort(key=lambda item: item[0])
        return status, [result for _score, result in ranked[:result_limit]]

    def document(self, doc_path: str) -> dict[str, str] | None:
        if not self.status()["available"]:
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT title, body, preview FROM docs_fts WHERE doc_path = ? LIMIT 1",
                (doc_path,),
            ).fetchone()
        return None if row is None else {"title": row[0], "body": row[1], "preview": row[2]}

    def document_paths(self) -> list[str]:
        if not self.status()["available"]:
            return []
        with closing(self._connect()) as connection:
            return [row[0] for row in connection.execute(
                "SELECT doc_path FROM docs_fts WHERE body != '' ORDER BY doc_path"
            ).fetchall()]

    def topic(self, file_path: str, context_id: str, *, alias_only: bool = False) -> dict[str, str | int] | None:
        if not self.status()["available"]:
            return None
        with closing(self._connect()) as connection:
            row = None if alias_only else connection.execute(
                "SELECT help_name, title, body, preview, context_id, NULL FROM topics_fts "
                "WHERE file_path = ? AND context_id = ? LIMIT 1",
                (file_path, context_id),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT t.help_name, t.title, t.body, t.preview, t.context_id, a.line "
                    "FROM topic_aliases AS a JOIN topics_fts AS t "
                    "ON t.file_path = a.file_path AND t.context_id = a.context_id "
                    "WHERE a.file_path = ? AND ((a.case_sensitive = 1 AND a.alias = ?) "
                    "OR (a.case_sensitive = 0 AND a.alias = ?)) ORDER BY a.case_sensitive DESC LIMIT 1",
                    (file_path, _alias_key(context_id, True), _alias_key(context_id)),
                ).fetchone()
        return None if row is None else {
            "help_name": row[0], "title": row[1], "body": row[2], "preview": row[3], "context_id": row[4],
            **({"line": row[5]} if row[5] is not None else {}),
        }

    def sitemap_count(self) -> int:
        if not self.status()["available"]:
            return 0
        with closing(self._connect()) as connection:
            return connection.execute("SELECT count(*) FROM topics_fts WHERE body != ''").fetchone()[0]

    def file_sitemap_counts(self) -> list[tuple[str, int]]:
        if not self.status()["available"]:
            return []
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT file_path, count(*) FROM topics_fts WHERE body != '' "
                "GROUP BY file_path ORDER BY file_path"
            ).fetchall()

    def file_topic_rows(self, file_path: str, offset: int = 0,
                        limit: int | None = None) -> list[tuple[str, str, str]]:
        if not self.status()["available"]:
            return []
        query = ("SELECT context_id, title, help_name FROM topics_fts "
                 "WHERE file_path = ? AND body != '' ORDER BY context_id")
        parameters: tuple = (file_path,)
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            parameters += (limit, offset)
        with closing(self._connect()) as connection:
            return connection.execute(query, parameters).fetchall()

    def sitemap_rows(self, offset: int, limit: int) -> list[tuple[str, str]]:
        if not self.status()["available"]:
            return []
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT file_path, context_id FROM topics_fts WHERE body != '' "
                "ORDER BY file_path, context_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
