"""Callable HELP download orchestration; CLI and server share the providers."""

from dataclasses import dataclass, field
import importlib
from pathlib import Path

from .catalog import PRODUCTS, SOURCE_RUNNERS, all_sources, products_for_source
from .extractor import ExtractorTools, find_lsar, find_sevenzip, find_unar
from .http import observe_downloads


@dataclass
class DownloadResult:
    files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def download_products(product_keys: list[str], sources_dir: Path, downloads_dir: Path,
                      *, source_keys: list[str] | None = None, dry_run=False,
                      on_progress=None, extractor: ExtractorTools | None = None) -> DownloadResult:
    """Download only explicit product IDs. An empty selection does nothing."""
    sources = all_sources() if source_keys is None else source_keys
    if set(product_keys) - PRODUCTS.keys() or set(sources) - SOURCE_RUNNERS.keys():
        raise ValueError("Unknown HELP product or download source")
    result = DownloadResult()
    if not product_keys:
        return result
    extractor = extractor or ExtractorTools(find_unar(), find_lsar(), find_sevenzip())
    if not dry_run and not extractor.available:
        raise ValueError("Archive extraction requires unar/lsar or 7zz; rebuild the Docker image")
    if not dry_run:
        downloads_dir.mkdir(parents=True, exist_ok=True)
    tasks = [(source, product.key) for source in sources
             for product in products_for_source(source) if product.key in product_keys]
    for index, (source, key) in enumerate(tasks):
        def progress(values):
            if on_progress:
                on_progress({"processed": index, "total": len(tasks), "product": key,
                             "source": source, **values})
        progress({"phase": "Finding sources", "file": PRODUCTS[key].label})
        try:
            with observe_downloads(progress):
                module = importlib.import_module(SOURCE_RUNNERS[source])
                result.files.extend(module.run(product_keys=[key], sources_dir=sources_dir,
                    dl_dir=downloads_dir, dry_run=dry_run, extractor=extractor))
        except Exception as error:
            result.warnings.append(f"{source}/{key}: {error}")
        progress({"phase": "Sources checked", "processed": index + 1, "file": PRODUCTS[key].label})
    return result
