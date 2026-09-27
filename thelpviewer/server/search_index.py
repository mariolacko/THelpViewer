"""Incremental, server-side full-text index of generated UHF HELP bundles."""

from __future__ import annotations

import gzip
import json
import re
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from ..public_docs import public_doc_sources


_TAG = re.compile(r"\[(?:/?[A-Za-z][^\]\n]*|rule)\]")
_WORD = re.compile(r"\w+", re.UNICODE)


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


def _topic_rows(bundle: dict, file_path: str, help_name: str):
    terms: dict[str, list[str]] = {}
    for group in bundle.get("index", []):
        if not isinstance(group, dict):
            continue
        for entry in group.get("entries", []):
            if isinstance(entry, dict) and entry.get("topic_id") is not None and not entry.get("file"):
                terms.setdefault(str(entry["topic_id"]), []).append(_plain(entry.get("label")))
    topics = bundle.get("topics", {})
    entries = topics.items() if isinstance(topics, dict) else enumerate(topics) if isinstance(topics, list) else ()
    for key, topic in entries:
        if not isinstance(topic, dict):
            continue
        context_id = str(topic.get("id", key))
        title = _plain(topic.get("title")) or f"Topic {context_id}"
        content = topic.get("content")
        lines = [_plain(line) for line in content] if isinstance(content, list) else []
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
                 virtual_docs: tuple[tuple[str, Path], ...] = ()):
        self.helps_dir = helps_dir
        self.docs_dir = docs_dir
        self.virtual_docs = virtual_docs
        self.path = state_dir / "global-search.sqlite3"
        self._lock = threading.Lock()
        self._building = False
        self._failed_snapshot = None
        self._status = {"state": "idle", "percent": 0, "processed": 0, "total": 0,
                        "topics": 0, "documents": 0, "file": ""}

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
            stat = path.stat()
            name = names.get(relative) or ""
            fingerprint = f"{stat.st_size}:{stat.st_mtime_ns}:{name}"
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
            stat = path.stat()
            title = Path(relative).stem.replace("_", " ")
            found[relative] = (path, f"{stat.st_size}:{stat.st_mtime_ns}", title)
        return found

    def ensure_current(self) -> None:
        with self._lock:
            if self._building:
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
                work = sorted(
                    [("help", name) for name, (_path, fingerprint, _title) in snapshot.items()
                     if indexed.get(name) != fingerprint]
                    + [("help", name) for name in indexed if name not in snapshot]
                    + [("doc", name) for name, (_path, fingerprint, _title) in docs_snapshot.items()
                       if indexed_docs.get(name) != fingerprint]
                    + [("doc", name) for name in indexed_docs if name not in docs_snapshot]
                )
                if not work:
                    self._status = {"state": "ready", "percent": 100, "processed": 0,
                                    "total": len(snapshot) + len(docs_snapshot), "topics": topic_count,
                                    "documents": doc_count, "file": ""}
                    self._failed_snapshot = None
                    return
                signature = tuple((kind, name,
                                   (snapshot if kind == "help" else docs_snapshot).get(name, (None, None, None))[1])
                                  for kind, name in work)
                if signature == self._failed_snapshot:
                    return
                self._building = True
                self._status = {"state": "building", "percent": 0, "processed": 0,
                                "total": len(work), "topics": topic_count,
                                "documents": doc_count, "file": ""}
            except (OSError, sqlite3.Error) as error:
                self._status = {"state": "error", "percent": 0, "processed": 0,
                                "total": 0, "topics": 0, "documents": 0, "file": "", "error": str(error)}
                return
        threading.Thread(target=self._build, args=(snapshot, docs_snapshot, work, signature), daemon=True).start()

    def _build(self, snapshot: dict, docs_snapshot: dict,
               work: list[tuple[str, str]], signature: tuple) -> None:
        try:
            with closing(self._connect()) as connection:
                for position, (kind, relative) in enumerate(work, 1):
                    if kind == "help" and relative in snapshot:
                        path, fingerprint, catalog_name = snapshot[relative]
                        with gzip.open(path, "rt", encoding="utf-8") as source:
                            bundle = json.load(source)
                        help_name = catalog_name or str(bundle.get("metadata", {}).get("name") or relative)
                        rows = list(_topic_rows(bundle, relative, help_name))
                        with connection:
                            connection.execute("DELETE FROM topics_fts WHERE file_path = ?", (relative,))
                            connection.executemany(
                                "INSERT INTO topics_fts(file_path, help_name, context_id, title, index_terms, body, preview) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?)", rows,
                            )
                            connection.execute(
                                "INSERT OR REPLACE INTO files(file_path, fingerprint, help_name, topic_count) "
                                "VALUES (?, ?, ?, ?)", (relative, fingerprint, help_name, len(rows)),
                            )
                    elif kind == "help":
                        with connection:
                            connection.execute("DELETE FROM topics_fts WHERE file_path = ?", (relative,))
                            connection.execute("DELETE FROM files WHERE file_path = ?", (relative,))
                    elif relative in docs_snapshot:
                        path, fingerprint, title = docs_snapshot[relative]
                        body = path.read_text(encoding="utf-8", errors="replace")
                        preview = " ".join(
                            line.strip(" #>*-`\t") for line in body.splitlines() if line.strip()
                        )[:180]
                        with connection:
                            connection.execute("DELETE FROM docs_fts WHERE doc_path = ?", (relative,))
                            connection.execute(
                                "INSERT INTO docs_fts(doc_path, title, body, preview) VALUES (?, ?, ?, ?)",
                                (relative, title, body, preview),
                            )
                            connection.execute(
                                "INSERT OR REPLACE INTO docs_files(doc_path, fingerprint, title) VALUES (?, ?, ?)",
                                (relative, fingerprint, title),
                            )
                    else:
                        with connection:
                            connection.execute("DELETE FROM docs_fts WHERE doc_path = ?", (relative,))
                            connection.execute("DELETE FROM docs_files WHERE doc_path = ?", (relative,))
                    count = connection.execute("SELECT coalesce(sum(topic_count), 0) FROM files").fetchone()[0]
                    documents = connection.execute("SELECT count(*) FROM docs_files").fetchone()[0]
                    with self._lock:
                        self._status = {"state": "building", "percent": round(position * 100 / len(work)),
                                        "processed": position, "total": len(work), "topics": count,
                                        "documents": documents, "file": relative}
            with self._lock:
                self._status = {**self._status, "state": "ready", "percent": 100, "file": ""}
                self._failed_snapshot = None
        except (OSError, ValueError, sqlite3.Error) as error:
            with self._lock:
                self._status = {**self._status, "state": "error", "error": str(error)}
                self._failed_snapshot = signature
        finally:
            with self._lock:
                self._building = False

    def status(self) -> dict:
        self.ensure_current()
        with self._lock:
            return dict(self._status)

    def search(self, query: str, limit: int = 60) -> tuple[dict, list[dict]]:
        status = self.status()
        if status["state"] != "ready":
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
        if self.status()["state"] != "ready":
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT title, body, preview FROM docs_fts WHERE doc_path = ? LIMIT 1",
                (doc_path,),
            ).fetchone()
        return None if row is None else {"title": row[0], "body": row[1], "preview": row[2]}

    def document_paths(self) -> list[str]:
        if self.status()["state"] != "ready":
            return []
        with closing(self._connect()) as connection:
            return [row[0] for row in connection.execute(
                "SELECT doc_path FROM docs_fts WHERE body != '' ORDER BY doc_path"
            ).fetchall()]

    def topic(self, file_path: str, context_id: str) -> dict[str, str] | None:
        if self.status()["state"] != "ready":
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT help_name, title, body, preview FROM topics_fts "
                "WHERE file_path = ? AND context_id = ? LIMIT 1",
                (file_path, context_id),
            ).fetchone()
        return None if row is None else {
            "help_name": row[0], "title": row[1], "body": row[2], "preview": row[3],
        }

    def sitemap_count(self) -> int:
        if self.status()["state"] != "ready":
            return 0
        with closing(self._connect()) as connection:
            return connection.execute("SELECT count(*) FROM topics_fts WHERE body != ''").fetchone()[0]

    def file_sitemap_counts(self) -> list[tuple[str, int]]:
        if self.status()["state"] != "ready":
            return []
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT file_path, count(*) FROM topics_fts WHERE body != '' "
                "GROUP BY file_path ORDER BY file_path"
            ).fetchall()

    def file_topic_rows(self, file_path: str, offset: int = 0,
                        limit: int | None = None) -> list[tuple[str, str, str]]:
        if self.status()["state"] != "ready":
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
        if self.status()["state"] != "ready":
            return []
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT file_path, context_id FROM topics_fts WHERE body != '' "
                "ORDER BY file_path, context_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
