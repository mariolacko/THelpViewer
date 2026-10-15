#!/usr/bin/env python3
"""Inspect the declared pages and keyword records of compiled HLX B+ trees."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.server.converter.readers.hlx_binary import HlxBinaryParser


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("path", type=Path, help="A compiled .HLX file or directory")
    cli.add_argument("--details", action="store_true", help="Print every native keyword record")
    args = cli.parse_args()
    targets = (sorted(p for p in args.path.rglob("*") if p.suffix.lower() == ".hlx")
               if args.path.is_dir() else [args.path])
    if not targets:
        cli.error(f"No .HLX files found under {args.path}")
    print(f"{'file':<16} {'bytes':>8} {'page_size':>9} {'pages':>5} {'levels':>6} {'keywords':>8} {'references':>10}")
    failed = False
    for path in targets:
        try:
            data = path.read_bytes()
            parser = HlxBinaryParser(data)
        except (OSError, ValueError) as error:
            print(f"{path}: {error}", file=sys.stderr)
            failed = True
            continue
        header = parser.header
        print(f"{path.name:<16} {len(data):>8} {header.page_size:>9} {header.total_pages:>5} "
              f"{header.levels:>6} {header.keyword_count:>8} "
              f"{sum(record.reference_count for record in parser.records):>10}")
        if args.details:
            for record in parser.records:
                print(f"  page={record.page} offset={record.file_offset:#x} "
                      f"count={record.reference_count} kwdata={record.kwdata_offset:#x} "
                      f"key={record.label!r}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
