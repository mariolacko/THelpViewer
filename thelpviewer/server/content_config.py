"""Shared structural validation of manifest-defined download sources."""

import json
from pathlib import Path
from re import Pattern


def read_source_manifest(path: Path | None, label: str, id_pattern: Pattern) -> dict:
    data = json.loads(path.read_text(encoding="utf-8")) if path is not None else {"sources": []}
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ValueError(f"{label} configuration needs a sources list")
    seen = set()
    for source in data["sources"]:
        ident = source.get("id") if isinstance(source, dict) else None
        if not isinstance(ident, str) or not id_pattern.fullmatch(ident) or ident in seen:
            raise ValueError(f"{label} sources need unique valid IDs")
        seen.add(ident)
    return data
