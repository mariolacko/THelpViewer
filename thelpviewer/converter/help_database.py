"""Shared lookup helpers for the canonical help-file database."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path
import zlib


DEFAULT_HELP_DATABASE_PATH = Path(__file__).resolve().parents[1] / "help-database.json"


@dataclass(frozen=True, slots=True)
class HelpDatabaseEntry:
    """One canonical help-file record keyed by CRC32."""

    crc32: int
    filenames: tuple[str, ...]
    title: str
    collection: str
    bundle_stem: str = ""
    text_encoding: str = ""
    language: str = ""
    help_contents_topic_id: int | None = None


def crc32_file(path: str | Path) -> int:
    """Return the unsigned CRC32 of one source help file."""
    source_path = Path(path)
    return zlib.crc32(source_path.read_bytes()) & 0xFFFFFFFF


def help_database_path(path: str | Path | None = None) -> Path:
    """Resolve the configured help-database JSON path."""
    if path is not None:
        return Path(path)
    configured = os.environ.get("THELP_HELP_DATABASE_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_HELP_DATABASE_PATH


@lru_cache(maxsize=4)
def _load_entries(database_path: str) -> dict[int, HelpDatabaseEntry]:
    payload_path = Path(database_path)
    if not payload_path.is_file():
        return {}
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        return {}

    entries: dict[int, HelpDatabaseEntry] = {}
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        if item.get("kind") == "separator":
            continue
        filename = item.get("filename")
        filenames = item.get("filenames")
        crc32 = item.get("crc32")
        alias_names: list[str] = []
        if isinstance(filenames, list):
            alias_names.extend(
                value.strip()
                for value in filenames
                if isinstance(value, str) and value.strip()
            )
        if not alias_names and isinstance(filename, str) and filename.strip():
            alias_names.append(filename.strip())
        if not alias_names:
            continue
        if not isinstance(crc32, str):
            continue
        try:
            crc_value = int(crc32, 16)
        except ValueError:
            continue
        title = item.get("title") if isinstance(item.get("title"), str) else ""
        collection = item.get("collection") if isinstance(item.get("collection"), str) else ""
        if not collection and isinstance(item.get("project"), str):
            collection = item.get("project")
        bundle_stem = item.get("bundle_stem") if isinstance(item.get("bundle_stem"), str) else ""
        text_encoding = item.get("text_encoding") if isinstance(item.get("text_encoding"), str) else ""
        language = item.get("language") if isinstance(item.get("language"), str) else ""
        help_contents_topic_id = item.get("help_contents_topic_id")
        if help_contents_topic_id is not None:
            try:
                help_contents_topic_id = int(help_contents_topic_id)
            except (TypeError, ValueError):
                help_contents_topic_id = None
        entries[crc_value] = HelpDatabaseEntry(
            crc32=crc_value,
            filenames=tuple(alias_names),
            title=title.strip(),
            collection=collection.strip(),
            bundle_stem=bundle_stem.strip(),
            text_encoding=text_encoding.strip(),
            language=language.strip(),
            help_contents_topic_id=help_contents_topic_id,
        )
    return entries


def load_help_database(path: str | Path | None = None) -> dict[int, HelpDatabaseEntry]:
    """Load the canonical help-file database indexed by CRC32."""
    resolved = help_database_path(path).resolve()
    return dict(_load_entries(str(resolved)))


def lookup_help_database_entry(
    source_path: str | Path,
    database: dict[int, HelpDatabaseEntry] | None = None,
) -> HelpDatabaseEntry | None:
    """Return the canonical metadata entry for one source help file."""
    path = Path(source_path)
    key = crc32_file(path)
    if database is None:
        return _load_entries(str(help_database_path().resolve())).get(key)
    return database.get(key)
