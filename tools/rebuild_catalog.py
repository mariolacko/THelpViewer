#!/usr/bin/env python3
"""Rebuild ``helps/catalog.json`` directly from existing ``*.json.gz`` bundles."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path


# ``metadata.source.format`` in the bundle records the source format id
# ("thelp", "quickhelp", ...).  ``helps/catalog.json`` historically exposes the
# reader family used by the bundle exporter ("borland", "bw03", ...), so we
# normalize here to keep rebuilt catalogs byte-for-byte compatible with the
# normal bundle build.
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


def _catalog_entry(path: Path, helps_dir: Path) -> dict[str, object]:
    payload = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
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

    return {
        "group": "" if group == "." else group,
        "file": str(rel_path).replace("\\", "/"),
        "source_file": source_file or path.name,
        "name": name,
        "format": _normalize_format(source.get("format")),
        "topics": _topic_count(payload),
    }


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
    repo_root = Path(__file__).resolve().parents[1]
    default_helps_dir = repo_root / "helps"
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
