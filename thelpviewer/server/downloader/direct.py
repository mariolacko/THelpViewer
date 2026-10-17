"""Pinned archive downloads with exact source-file selection."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from ..processing import UnsafeContentError
from .errors import SourceUnavailable
from .catalog import products_for_source
from .cache import download_filename
from ..converter.ingest import HelpInput


SOURCE_NAME = "direct"


def run(
    product_keys: list[str],
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Download known archives and retain only their configured members."""
    collected: list[Path] = []
    failures: list[str] = []
    for product in products_for_source(SOURCE_NAME, product_keys):
        if complete and complete():
            break
        query = product.sources[SOURCE_NAME]
        print(f"\n[direct] {product.label}")
        target_label = product.collection_prefixes[0] if product.collection_prefixes else product.label
        for url in query.direct_urls:
            if complete and complete():
                break
            filename = Path(urlparse(url).path).name
            if not filename:
                failures.append(f"{product.key}: URL has no archive filename: {url}")
                continue
            print(f"  Archive: {url}")
            if dry_run:
                print(f"  [dry-run] Members: {', '.join(query.archive_members)}")
                continue
            archive_path = dl_dir / f"direct_{product.key}_{download_filename(filename)}"
            try:
                collected.extend(process(HelpInput(archive_path, target_label,
                    members=query.archive_members), url=url))
            except UnsafeContentError:
                raise
            except Exception as exc:
                print(f"  [error] {product.label}: {exc}")
                failures.append(f"{product.key}: {exc}")
    if failures:
        raise SourceUnavailable("Pinned downloads failed: " + "; ".join(failures))
    return collected
