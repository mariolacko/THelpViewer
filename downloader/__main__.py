"""
Unified Downloader – Borland/Turbo DOS Help Files
==================================================

Downloads help files from WinWorldPC, archive.org, and old-dos.ru.

Usage:
    python3 -m downloader                          # all sources, all products
    python3 -m downloader --source winworld archiveorg
    python3 -m downloader --products tp tc tasm
    python3 -m downloader --dry-run
    python3 -m downloader --source archiveorg --products tp td
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path if needed
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from downloader.common import require_7z


SOURCES = ["winworld", "archiveorg", "olddos"]

ALL_PRODUCTS = ["tp", "tc", "tasm", "td", "tbasic", "tprolog", "bc", "bp", "sk"]

SOURCE_PRODUCTS = {
    "winworld":   ["tp", "tc", "tasm", "tbasic", "tprolog", "bc", "bp", "sk"],
    "archiveorg": ["tp", "tc", "tasm", "td", "tbasic", "tprolog", "bc", "bp"],
    "olddos":     ["tp", "tc", "tasm", "td", "tbasic", "tprolog", "bc", "bp"],
}

PRODUCT_LABELS = {
    "tp":      "Borland Turbo Pascal",
    "tc":      "Borland Turbo C / C++",
    "tasm":    "Borland Turbo Assembler",
    "td":      "Borland Turbo Debugger",
    "tbasic":  "Borland Turbo Basic",
    "tprolog": "Borland Turbo Prolog",
    "bc":      "Borland C++",
    "bp":      "Borland Pascal",
    "sk":      "Borland Sidekick",
}


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)

    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        prog="python3 -m downloader",
        description="Download Borland/Turbo DOS help files from multiple sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Sources:\n"
            "  winworld   – WinWorldPC (25 downloads/day, disk images)\n"
            "  archiveorg – Archive.org (no limit, direct files)\n"
            "  olddos     – Old-dos.ru (cat=102 programming tools)\n"
            "\n"
            "Products:\n" +
            "\n".join(f"  {k:10s} – {v}" for k, v in PRODUCT_LABELS.items())
        ),
    )
    parser.add_argument(
        "--source", nargs="+", choices=SOURCES, default=SOURCES,
        metavar="SOURCE",
        help=f"Sources: {', '.join(SOURCES)} (default: all)",
    )
    parser.add_argument(
        "--products", nargs="+", choices=ALL_PRODUCTS,
        metavar="PRODUCT",
        help=f"Products: {', '.join(ALL_PRODUCTS)} (default: all for given source)",
    )
    parser.add_argument(
        "--out-dir", default=str(project_root / "sources"),
        help="Target directory for extracted help files (default: sources/)",
    )
    parser.add_argument(
        "--dl-dir", default=str(project_root / "downloads"),
        help="Directory for downloaded archives (default: downloads/)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only print what would happen, don't download.",
    )

    args   = parser.parse_args()
    sources_dir = Path(args.out_dir)
    dl_dir      = Path(args.dl_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory:   {sources_dir}")
    print(f"Download directory: {dl_dir}")
    print(f"Sources:            {', '.join(args.source)}")
    if args.products:
        print(f"Products:           {', '.join(args.products)}")
    if args.dry_run:
        print("Mode:               DRY-RUN")

    sevenz = require_7z(dry_run=args.dry_run)

    all_collected: list[Path] = []

    for source in args.source:
        products = args.products or SOURCE_PRODUCTS.get(source, ALL_PRODUCTS)
        # Filter only products supported by this source
        supported = SOURCE_PRODUCTS.get(source, ALL_PRODUCTS)
        products  = [p for p in products if p in supported]

        if source == "winworld":
            from downloader import winworld
            collected = winworld.run(
                product_keys=products,
                sources_dir=sources_dir,
                dl_dir=dl_dir,
                dry_run=args.dry_run,
                sevenz=sevenz,
            )
        elif source == "archiveorg":
            from downloader import archiveorg
            collected = archiveorg.run(
                product_keys=products,
                sources_dir=sources_dir,
                dl_dir=dl_dir,
                dry_run=args.dry_run,
                sevenz=sevenz,
            )
        elif source == "olddos":
            from downloader import olddos
            collected = olddos.run(
                product_keys=products,
                sources_dir=sources_dir,
                dl_dir=dl_dir,
                dry_run=args.dry_run,
                sevenz=sevenz,
            )
        else:
            continue

        all_collected.extend(collected)

    print(f"\n{'='*60}")
    if args.dry_run:
        print("DRY-RUN – no files were downloaded.")
    else:
        print(f"Total help files collected: {len(all_collected)}")
        for p in all_collected:
            print(f"  {p.relative_to(sources_dir)}")


if __name__ == "__main__":
    main()
