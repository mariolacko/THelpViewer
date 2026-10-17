"""Unified CLI for the refactored help-file downloader."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ...config import PROJECT_ROOT
from .catalog import (
    PRODUCTS,
    SOURCE_DESCRIPTIONS,
    all_products,
    all_sources,
)
from ..archives.core import ExtractionError, require_extractor_tools
from .service import download_products


def _build_parser(project_root: Path) -> argparse.ArgumentParser:
    sources = all_sources()
    products = all_products()
    parser = argparse.ArgumentParser(
        prog="python3 -m thelpviewer.server.downloader",
        description="Download DOS help files from multiple sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Sources:\n"
            + "\n".join(f"  {name:10s} – {SOURCE_DESCRIPTIONS[name]}" for name in sources)
            + "\n\nProducts:\n"
            + "\n".join(f"  {key:10s} – {PRODUCTS[key].label}" for key in products)
        ),
    )
    parser.add_argument(
        "--source",
        nargs="+",
        choices=sources,
        default=None,
        metavar="SOURCE",
        help=f"Sources: {', '.join(sources)}",
    )
    parser.add_argument(
        "--products",
        nargs="+",
        choices=products,
        metavar="PRODUCT",
        default=None,
        help=f"Logical product groups: {', '.join(products)}",
    )
    parser.add_argument(
        "selectors",
        nargs="*",
        metavar="SELECTOR",
        help="Optional positional source/product selectors, e.g. `tp olddos`.",
    )
    parser.add_argument(
        "--out-dir",
        default=os.environ.get("THELP_SOURCES_DIR", str(Path(os.environ.get("THELP_STATE_DIR", project_root / "var")) / "sources")),
        help="Target directory for extracted help files (default: var/sources/)",
    )
    parser.add_argument(
        "--dl-dir",
        default=str(Path(os.environ.get("THELP_DOWNLOADS_DIR", project_root / "var" / "downloads")) / "help"),
        help="Directory for downloaded archives/files (default: var/downloads/help/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would happen, do not download or extract.",
    )
    return parser


def _resolve_selection(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[list[str], list[str]]:
    sources = set(args.source or [])
    products = set(args.products or [])

    for token in args.selectors:
        if token in SOURCE_DESCRIPTIONS:
            sources.add(token)
            continue
        if token in PRODUCTS:
            products.add(token)
            continue
        parser.error(f"Unknown selector: {token}")

    resolved_sources = [name for name in all_sources() if name in sources] if sources else all_sources()
    resolved_products = [name for name in all_products() if name in products] if products else all_products()
    return resolved_sources, resolved_products


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)

    project_root = PROJECT_ROOT
    parser = _build_parser(project_root)
    args = parser.parse_args()
    selected_sources, selected_products = _resolve_selection(args, parser)

    sources_dir = Path(args.out_dir)
    dl_dir = Path(args.dl_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory:   {sources_dir}")
    print(f"Download directory: {dl_dir}")
    print(f"Sources:            {', '.join(selected_sources)}")
    print(f"Products:           {', '.join(selected_products)}")
    if args.dry_run:
        print("Mode:               DRY-RUN")

    try:
        extractor_tools = require_extractor_tools(dry_run=args.dry_run)
    except ExtractionError as error:
        raise SystemExit(str(error)) from error
    result = download_products(selected_products, sources_dir, dl_dir,
                              source_keys=selected_sources, dry_run=args.dry_run, extractor=extractor_tools)
    all_collected = result.files

    print(f"\n{'=' * 60}")
    if args.dry_run:
        print("DRY-RUN – no files were downloaded.")
    else:
        print(f"Total help files collected: {len(all_collected)}")
        for path in all_collected:
            print(f"  {path.relative_to(sources_dir)}")
    for warning in result.warnings:
        print("Warning: " + warning)
    if result.errors:
        raise SystemExit("Download errors: " + "; ".join(result.errors))


if __name__ == "__main__":
    main()
