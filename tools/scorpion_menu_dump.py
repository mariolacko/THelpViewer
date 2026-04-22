#!/usr/bin/env python3
"""Dump the top-level Scorpion program menu from the `seznam` record with raw target blobs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.converter.readers.scorpion_dat import (  # noqa: E402
    _extract_program_menu_entries,
    _menu_blob_hint,
    _parse_records,
)

def _format_blob(blob: bytes) -> str:
    if not blob:
        return "<empty>"
    return " ".join(f"{value:02x}" for value in blob)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to program.dat")
    args = parser.parse_args()

    path = Path(args.path)
    records = _parse_records(path.read_bytes())
    seznam = next((record for record in records if record.name == "seznam"), None)
    if seznam is None:
        raise SystemExit("Record 'seznam' not found")

    entries = _extract_program_menu_entries(seznam)
    if not entries:
        raise SystemExit("Could not locate program menu block inside 'seznam'")
    menu_end = seznam.payload.find(b"04x")
    if menu_end < 0:
        menu_end = len(seznam.payload)

    print(f"file:   {path}")
    print("record: seznam")
    print(f"menu-range-end: {menu_end}")
    print()
    print("PROGRAM MENU ENTRIES")

    for index, entry in enumerate(entries):
        next_pos = menu_end
        if index + 1 < len(entries):
            next_pos = entries[index + 1].start
        preview = seznam.payload[entry.start:next_pos].decode("cp852", errors="replace")
        preview = preview.replace("\r", " ").replace("\n", " ")
        preview = " ".join(preview.split())
        print(f"- label: {entry.label}")
        print(f"  start: {entry.start}")
        print(f"  blob:  {_format_blob(entry.blob)}")
        if entry.hint:
            print(f"  hint:  {entry.hint}")
        raw_hint = entry.raw_hint or _menu_blob_hint(entry.blob)
        if raw_hint and raw_hint != entry.hint:
            print(f"  raw:   {raw_hint}")
        print(f"  text:  {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
