#!/usr/bin/env python3
"""Post-process already-built UHF bundles in `helps/` and annotate index
entries that reference external topic ids with a `source_file` hint.

This helps the viewer resolve `$`-style symbolic index labels when the
original conversion could not determine the owning bundle (due to build
ordering). Run after a full `./thelp.sh build` to make index entries
self-descriptive.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Dict


def build_context_owner_map(helps_dir: Path) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for p in helps_dir.rglob("*.json.gz"):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                j = json.load(fh)
        except Exception:
            continue
        src = (j.get("metadata", {}).get("source", {}).get("filename") or p.name)
        topics = j.get("topics") or {}
        for t in topics.values():
            try:
                tid = int(t.get("id"))
            except Exception:
                continue
            if tid not in mapping:
                mapping[tid] = src
    return mapping


def annotate_index_entries(helps_dir: Path, mapping: Dict[int, str]) -> int:
    changed = 0
    for p in helps_dir.rglob("*.json.gz"):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                j = json.load(fh)
        except Exception:
            continue

        topics = j.get("topics") or {}
        modified = False
        for group in j.get("index", []):
            for entry in group.get("entries", []):
                try:
                    target = int(entry.get("topic_id"))
                except Exception:
                    continue
                # If this bundle already contains the target, skip.
                if any((int(t.get("id")) == target) for t in topics.values() if t.get("id") is not None):
                    continue
                if entry.get("source_file"):
                    continue
                owner = mapping.get(target)
                if owner:
                    entry["source_file"] = owner
                    modified = True

        if modified:
            try:
                # Write out as a single gzip-compressed JSON payload.
                payload = json.dumps(j, ensure_ascii=False, indent=2)
                with gzip.open(p, "wt", encoding="utf-8") as fh:
                    fh.write(payload)
                changed += 1
            except Exception:
                continue

    return changed


def main():
    from thelpviewer.server.config import load_config
    helps_dir = load_config().helps_dir
    if not helps_dir.exists():
        print(f"{helps_dir} directory not found")
        return
    print("Scanning bundles for topic owners...")
    mapping = build_context_owner_map(helps_dir)
    print(f"Found {len(mapping)} unique topic ids across bundles")
    print("Annotating index entries...")
    changed = annotate_index_entries(helps_dir, mapping)
    print(f"Updated {changed} bundles")


if __name__ == "__main__":
    main()
