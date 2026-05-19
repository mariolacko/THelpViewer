#!/usr/bin/env python3
"""Rebuild the canonical help-file database from the current sources tree."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.converter.exporter import (
    autodetect_display_encoding,
    detect_format_handler,
    fix_metadata_encoding,
    load_document,
)
from thelpviewer.converter.help_database import crc32_file
from thelpviewer.downloader.collector import detect_language


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_STOP_TOKENS = {
    "help",
    "file",
    "files",
    "guide",
    "guides",
    "viewer",
    "manual",
    "the",
    "and",
}
_HELP_FILE_SUFFIXES = {".hlp", ".tph", ".tch", ".tah", ".tdh", ".tfh", ".ng", ".hlx", ".hl6", ".dat"}
_NEW_ENTRIES_SEPARATOR_KIND = "separator"
_NEW_ENTRIES_NOTE = "New help files discovered during the last rebuild start below."

LANGUAGE_BY_DETECTED_CODE = {
    "CZ": "cs",
    "DE": "de",
    "FR": "fr",
    "ES": "es",
    "IT": "it",
    "NL": "nl",
    "PT": "pt",
    "PL": "pl",
    "RU": "ru",
    "SE": "sv",
    "HU": "hu",
}


def _inspect_supported_file(path: Path) -> tuple[str, str, int | None]:
    handler = detect_format_handler(path)
    if handler is None:
        if path.name.upper() == "TASM.TAH":
            return "Turbo Assembler Help", "cp437", None
        return path.stem, "", None
    document = load_document(path)
    encoding = autodetect_display_encoding(document, source_hint=str(path))
    fix_metadata_encoding(document, encoding)
    title = document.display_name.strip()
    topic_ids = {topic.context_id for topic in document.topics}
    help_contents_topic_id = document.metadata.get("help_contents_topic_id")
    if not isinstance(help_contents_topic_id, int) or help_contents_topic_id not in topic_ids:
        help_contents_topic_id = next(
            (topic.context_id for topic in document.topics if topic.is_help_contents),
            None,
        )
    if path.name.upper() == "TASM.TAH" and title.casefold() == "tasm":
        title = "Turbo Assembler Help"
    return title or path.stem, encoding, help_contents_topic_id


def _infer_language(path: Path, title: str, collection: str, text_encoding: str) -> str:
    """Infer a BCP 47 language tag from canonical metadata and source names."""
    haystack = " ".join((str(path), title, collection))
    detected = detect_language(f" {haystack} ")
    if detected:
        mapped = LANGUAGE_BY_DETECTED_CODE.get(detected.upper())
        if mapped:
            return mapped

    lowered = haystack.casefold()
    if any(token in lowered for token in ("(cz)", " czech", " česk", " cesk", " nápověd", "napoved")):
        return "cs"
    if any(token in lowered for token in ("(de)", " german", " deutsch", " hilfe")):
        return "de"
    if any(token in lowered for token in ("software 602", "text602", "calc602", "m602", "scorpion")):
        return "cs"
    if text_encoding in {"cp852", "kamenicky"}:
        return "cs"
    if any(token in lowered for token in ("microsoft", "borland", "norton", "quick", "turbo", "objectwindows")):
        return "en"
    return ""


def _is_help_file_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in _HELP_FILE_SUFFIXES or (
        len(suffix) == 4
        and suffix.startswith(".t")
        and suffix.endswith("h")
    )


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(value)
        if token.casefold() not in _STOP_TOKENS
    }


def _collection_score(collection: str, title: str) -> tuple[int, int, int, int, int]:
    collection_lower = collection.casefold()
    overlap = len(_tokens(collection) & _tokens(title))
    exact_version = 1 if re.search(r"\b\d+(?:\.\d+)+\b", collection) else 0
    generic_version = 1 if re.search(r"\b\d+\.(?:x|X)\b", collection) else 0
    current_penalty = 1 if "current" in collection_lower else 0
    return (
        overlap,
        exact_version,
        -generic_version,
        -current_penalty,
        -len(collection),
    )


def _canonical_collection(collections: list[str], title: str) -> str:
    ranked = sorted(
        collections,
        key=lambda value: (_collection_score(value, title), value.casefold()),
        reverse=True,
    )
    return ranked[0]


def _separator_entry() -> dict[str, object]:
    return {
        "kind": _NEW_ENTRIES_SEPARATOR_KIND,
        "note": _NEW_ENTRIES_NOTE,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def _normalize_entry(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None

    if item.get("kind") == _NEW_ENTRIES_SEPARATOR_KIND:
        note = item.get("note") if isinstance(item.get("note"), str) else _NEW_ENTRIES_NOTE
        normalized = {
            "kind": _NEW_ENTRIES_SEPARATOR_KIND,
            "note": note.strip() or _NEW_ENTRIES_NOTE,
        }
        generated_at = item.get("generated_at")
        if isinstance(generated_at, str) and generated_at.strip():
            normalized["generated_at"] = generated_at.strip()
        return normalized

    crc32 = item.get("crc32")
    if not isinstance(crc32, str):
        return None
    try:
        int(crc32, 16)
    except ValueError:
        return None

    raw_filenames = item.get("filenames")
    filenames: list[str] = []
    if isinstance(raw_filenames, list):
        filenames.extend(
            value.strip()
            for value in raw_filenames
            if isinstance(value, str) and value.strip()
        )
    if not filenames:
        legacy_filename = item.get("filename")
        if isinstance(legacy_filename, str) and legacy_filename.strip():
            filenames.append(legacy_filename.strip())
    if not filenames:
        return None

    title = item.get("title") if isinstance(item.get("title"), str) else ""
    collection = item.get("collection") if isinstance(item.get("collection"), str) else ""
    if not collection and isinstance(item.get("project"), str):
        collection = item.get("project")
    text_encoding = item.get("text_encoding") if isinstance(item.get("text_encoding"), str) else ""
    language = item.get("language") if isinstance(item.get("language"), str) else ""
    bundle_stem = item.get("bundle_stem") if isinstance(item.get("bundle_stem"), str) else ""
    help_contents_topic_id = item.get("help_contents_topic_id")
    if help_contents_topic_id is not None:
        try:
            help_contents_topic_id = int(help_contents_topic_id)
        except (TypeError, ValueError):
            help_contents_topic_id = None

    normalized = {
        "crc32": crc32.upper(),
        "filenames": filenames,
        "title": title,
        "collection": collection,
        "text_encoding": text_encoding,
    }
    if bundle_stem.strip():
        normalized["bundle_stem"] = bundle_stem.strip()
    if language.strip():
        normalized["language"] = language.strip()
    if help_contents_topic_id is not None:
        normalized["help_contents_topic_id"] = help_contents_topic_id
    return normalized


def _merge_filenames(existing: list[str], discovered: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for name in existing + discovered:
        folded = name.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        merged.append(name)
    return merged


def _merge_existing_entry(existing: dict[str, object], discovered: dict[str, object]) -> dict[str, object]:
    merged = dict(existing)
    merged["crc32"] = discovered["crc32"]
    merged["filenames"] = _merge_filenames(
        list(existing.get("filenames", [])) if isinstance(existing.get("filenames"), list) else [],
        list(discovered.get("filenames", [])) if isinstance(discovered.get("filenames"), list) else [],
    )
    for key in ("title", "collection", "bundle_stem", "text_encoding", "language", "help_contents_topic_id"):
        current = merged.get(key)
        if key == "help_contents_topic_id":
            if current is None and discovered.get(key) is not None:
                merged[key] = discovered[key]
            continue
        if not isinstance(current, str) or not current.strip():
            merged[key] = discovered.get(key, "")
    return merged


def _load_existing_entries(output_path: Path) -> list[dict[str, object]]:
    if not output_path.is_file():
        return []
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        return []
    normalized_entries: list[dict[str, object]] = []
    for item in raw_entries:
        normalized = _normalize_entry(item)
        if normalized is not None:
            normalized_entries.append(normalized)
    return normalized_entries


def _discover_entries(sources_dir: Path) -> dict[str, dict[str, object]]:
    grouped_paths: dict[int, list[Path]] = defaultdict(list)
    all_paths = sorted(
        path
        for path in sources_dir.rglob("*")
        if path.is_file() and _is_help_file_path(path)
    )
    for path in all_paths:
        grouped_paths[crc32_file(path)].append(path)

    discovered_entries: dict[str, dict[str, object]] = {}
    for crc32, paths in sorted(grouped_paths.items()):
        source_paths = sorted(paths, key=lambda value: str(value.relative_to(sources_dir)).casefold())
        representative = source_paths[0]
        filenames = sorted({path.name for path in source_paths}, key=str.casefold)
        canonical_filename = representative.name
        ordered_filenames = [canonical_filename] + [
            name for name in filenames if name.casefold() != canonical_filename.casefold()
        ]
        title, text_encoding, help_contents_topic_id = _inspect_supported_file(representative)
        collections = sorted(
            {
                str(path.parent.relative_to(sources_dir)).replace("\\", "/")
                for path in source_paths
            },
            key=str.casefold,
        )
        collection = _canonical_collection(collections, title)
        language = _infer_language(representative, title, collection, text_encoding)
        entry: dict[str, object] = {
            "filenames": ordered_filenames,
            "crc32": f"{crc32:08X}",
            "title": title,
            "collection": collection,
            "text_encoding": text_encoding,
        }
        if language:
            entry["language"] = language
        if help_contents_topic_id is not None:
            entry["help_contents_topic_id"] = help_contents_topic_id
        discovered_entries[f"{crc32:08X}"] = entry
    return discovered_entries


def rebuild_help_database(sources_dir: Path, output_path: Path) -> int:
    discovered_entries = _discover_entries(sources_dir)
    existing_entries = _load_existing_entries(output_path)

    merged_entries: list[dict[str, object]] = []
    seen_crc32: set[str] = set()
    for item in existing_entries:
        if item.get("kind") == _NEW_ENTRIES_SEPARATOR_KIND:
            continue
        crc32 = item.get("crc32")
        if not isinstance(crc32, str) or crc32 in seen_crc32:
            continue
        seen_crc32.add(crc32)
        discovered = discovered_entries.pop(crc32, None)
        if discovered is None:
            merged_entries.append(item)
        else:
            merged_entries.append(_merge_existing_entry(item, discovered))

    new_entries = [discovered_entries[key] for key in sorted(discovered_entries)]
    entries = list(merged_entries)
    if new_entries:
        entries.append(_separator_entry())
        entries.extend(new_entries)

    payload = {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "entries": entries,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len([item for item in entries if isinstance(item, dict) and item.get("crc32")])


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Rebuild help-database.json from current sources.")
    parser.add_argument(
        "sources_dir",
        nargs="?",
        default=str(repo_root / "sources"),
        help="Directory containing source help files (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(repo_root / "thelpviewer" / "help-database.json"),
        help="Output JSON file (default: %(default)s)",
    )
    args = parser.parse_args()
    sources_dir = Path(args.sources_dir).resolve()
    output_path = Path(args.output).resolve()
    count = rebuild_help_database(sources_dir, output_path)
    print(f"[helpdb] Rebuilt {output_path} from {count} unique help files in {sources_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
