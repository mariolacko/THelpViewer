"""Refresh Turbo Vision assets in already-generated HTML trees."""

from __future__ import annotations

import argparse
from pathlib import Path

from .writers.html import SITE_ASSET_DIR_NAME, copy_site_assets


def iter_site_roots(root: Path) -> list[Path]:
    """Return generated site directories that contain an ``assets`` directory."""
    sites: set[Path] = set()
    direct_assets = root / SITE_ASSET_DIR_NAME
    if direct_assets.is_dir():
        sites.add(root)
    for asset_dir in root.rglob(SITE_ASSET_DIR_NAME):
        if asset_dir.is_dir():
            sites.add(asset_dir.parent)
    return sorted(sites)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser used by ``python -m python.hlx2html.sync_assets``."""
    parser = argparse.ArgumentParser(
        prog="python -m python.hlx2html.sync_assets",
        description="Refresh bundled JS/CSS/font assets in generated hlx2html output trees.",
    )
    parser.add_argument(
        "output_root",
        nargs="?",
        default=str(Path(__file__).resolve().parents[2] / "python" / "hlx2html" / "generated"),
        help="Generated site directory or a tree containing multiple generated help sites.",
    )
    return parser


def main() -> None:
    """Refresh ``assets`` in one generated site or in a whole generated tree."""
    args = build_parser().parse_args()
    root = Path(args.output_root)
    sites = iter_site_roots(root)
    for site in sites:
        copy_site_assets(site)
        print(site)
    print(f"TOTAL\t{len(sites)}")


if __name__ == "__main__":
    main()
