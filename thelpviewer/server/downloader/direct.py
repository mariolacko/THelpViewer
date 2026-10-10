"""Pinned archive downloads with exact source-file selection."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .catalog import products_for_source
from .extractor import ExtractorTools, collect_archive_members
from .http import download_file


SOURCE_NAME = "direct"


def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    extractor: ExtractorTools,
) -> list[Path]:
    """Download known archives and retain only their configured members."""
    collected: list[Path] = []
    failures: list[str] = []
    for product in products_for_source(SOURCE_NAME, product_keys):
        query = product.sources[SOURCE_NAME]
        print(f"\n[direct] {product.label}")
        target_label = product.collection_prefixes[0] if product.collection_prefixes else product.label
        target_dir = sources_dir / target_label
        for url in query.direct_urls:
            filename = Path(urlparse(url).path).name
            if not filename:
                failures.append(f"{product.key}: URL has no archive filename: {url}")
                continue
            print(f"  Archive: {url}")
            if dry_run:
                print(f"  [dry-run] Members: {', '.join(query.archive_members)}")
                continue
            if query.archive_members and all(
                (target_dir / Path(member).name.upper()).is_file()
                for member in query.archive_members
            ):
                print("  [skipped] All selected files already exist")
                continue
            archive_path = dl_dir / f"direct_{product.key}_{filename}"
            try:
                download_file(url, archive_path)
                collected.extend(
                    collect_archive_members(
                        archive_path,
                        query.archive_members,
                        target_label,
                        sources_dir,
                        extractor,
                    )
                )
            except Exception as exc:
                print(f"  [error] {product.label}: {exc}")
                failures.append(f"{product.key}: {exc}")
    if failures:
        raise RuntimeError("Pinned downloads failed: " + "; ".join(failures))
    return collected
