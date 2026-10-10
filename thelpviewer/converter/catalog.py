#!/usr/bin/env python3
"""Rebuild ``helps/catalog.json`` directly from existing ``*.json.gz`` bundles."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

# ``metadata.source.format`` in the bundle records the source format id
# ("thelp", "quickhelp", ...).  ``helps/catalog.json`` exposes the reader
# family used by the bundle exporter ("borland", "bw03", ...), so rebuilt
# catalogs normalize the same public value.
FORMAT_ALIASES = {
    "thelp": "borland",
    "ng": "norton-guide",
}


def _normalize_format(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower()
    if not normalized:
        return "unknown"
    return FORMAT_ALIASES.get(normalized, normalized)


def _topic_count(payload: dict[str, object]) -> int:
    topics = payload.get("topics")
    if isinstance(topics, dict):
        return len(topics)
    if isinstance(topics, list):
        return len(topics)
    return 0


def _read_file_bytes(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY)
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(fd)


def _metadata_string(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    return value.strip() if isinstance(value, str) else ""


def _catalog_source_files(metadata: dict[str, object], source_file: str) -> list[str]:
    raw_files = metadata.get("catalog_source_files")
    if isinstance(raw_files, list):
        files = [item.strip() for item in raw_files if isinstance(item, str) and item.strip()]
        if files:
            return files
    return [source_file] if source_file else []


def _catalog_entry(path: Path, helps_dir: Path) -> dict[str, object]:
    payload = json.loads(gzip.decompress(_read_file_bytes(path)).decode("utf-8"))
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    source = metadata.get("source")
    if not isinstance(source, dict):
        source = {}

    rel_path = path.relative_to(helps_dir)
    group = str(rel_path.parent).replace("\\", "/")
    source_file = source.get("filename") if isinstance(source.get("filename"), str) else ""
    name = metadata.get("name") if isinstance(metadata.get("name"), str) else ""
    if not name:
        name = path.stem
    source_files = _catalog_source_files(metadata, source_file or path.name)

    product_key = _metadata_string(metadata, "product")
    product_name = _metadata_string(metadata, "product_name")
    version = _metadata_string(metadata, "version")
    menu_name = _metadata_string(metadata, "menu_name")
    entry = {
        "group": "" if group == "." else group,
        "file": str(rel_path).replace("\\", "/"),
        "source_file": source_files[0],
        "source_files": source_files,
        "name": name,
        "format": _normalize_format(source.get("format")),
        "topics": _topic_count(payload),
    }
    if product_key:
        entry["product"] = product_key
    if product_name:
        entry["product_name"] = product_name
    if version:
        entry["version"] = version
    if menu_name and menu_name != name:
        entry["menu_name"] = menu_name
    return entry


def rebuild_catalog(helps_dir: Path, output_path: Path) -> int:
    bundles = sorted(
        path
        for path in helps_dir.rglob("*.json.gz")
        if path.is_file()
    )
    catalog = [_catalog_entry(path, helps_dir) for path in bundles]
    catalog.sort(
        key=lambda item: (
            str(item["group"]).casefold(),
            str(item["name"]).casefold(),
            str(item["file"]).casefold(),
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(catalog)


def main() -> int:
    default_helps_dir = REPO_ROOT / "helps"
    parser = argparse.ArgumentParser(
        description="Rebuild helps/catalog.json from existing .json.gz bundles.",
    )
    parser.add_argument(
        "helps_dir",
        nargs="?",
        default=str(default_helps_dir),
        help="Directory containing help bundles (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output catalog path (default: <helps_dir>/catalog.json)",
    )
    args = parser.parse_args()

    helps_dir = Path(args.helps_dir).resolve()
    output_path = Path(args.output).resolve() if args.output else helps_dir / "catalog.json"
    count = rebuild_catalog(helps_dir, output_path)
    print(f"[catalog] Rebuilt {output_path} from {count} bundles in {helps_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
