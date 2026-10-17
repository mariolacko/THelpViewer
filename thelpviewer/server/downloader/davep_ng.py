"""Dave Pearson Norton Guides mirror provider."""

from __future__ import annotations

import re
from pathlib import Path

from ..processing import UnsafeContentError, report_progress
from ..converter.ingest import HelpInput
from .catalog import products_for_source
from .http import fetch_html


SOURCE_NAME = "davep_ng"


def get_guide_names(base_url: str) -> list[str]:
    """Return all guide slugs exposed by the DaveP mirror."""
    html = fetch_html(base_url)
    guides = set()
    for match in re.finditer(r'<a href="([a-zA-Z0-9_\-]+)/index.html"', html):
        guides.add(match.group(1))
    return sorted(guides)


def run(
    product_keys: list[str],
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Download plain ``.ng`` files from the DaveP mirror."""

    selected = products_for_source(SOURCE_NAME, product_keys)
    if not selected:
        return []

    product = selected[0]
    source_query = product.sources[SOURCE_NAME]
    base_url = source_query.base_url or "https://norton-guides.davep.dev/"

    print(f"\n{'=' * 60}")
    print("[davep-ng] Norton Guides (.ng) files")
    print(f"Search: {source_query.search_text}")
    print("=" * 60)

    guides = get_guide_names(base_url)
    if not guides:
        print("  [error] No .ng files found on the mirror.")
        return []

    collected: list[Path] = []

    for guide in guides:
        if complete and complete():
            break
        url = f"{base_url}{guide}/{guide}.ng"
        temp_dest = dl_dir / f"{guide}.ng"

        print(f"  File: {guide}.ng")
        if dry_run:
            print(f"    [dry-run] {url}")
            continue
        try:
            collected.extend(process(HelpInput(temp_dest, product.label, direct=True), url=url))
        except UnsafeContentError:
            raise
        except Exception as exc:
            print(f"    [error] {exc}")
            report_progress("Source warning", warning=str(exc))

    return collected
