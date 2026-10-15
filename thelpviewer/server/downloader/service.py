"""Callable HELP download orchestration; CLI and server share the providers."""

from dataclasses import dataclass, field
import importlib
from pathlib import Path

from .catalog import PRODUCTS, SOURCE_RUNNERS, all_sources, supported_product_keys, select_help_packages
from .extractor import ExtractorTools, find_lsar, find_sevenzip, find_unar
from .http import observe_downloads
from .online import OnlineDownloader


@dataclass
class DownloadResult:
    files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def download_products(product_keys: list[str], sources_dir: Path, downloads_dir: Path,
                      *, source_keys: list[str] | None = None, dry_run=False,
                      on_progress=None, extractor: ExtractorTools | None = None, downloads=None,
                      preserve_downloads=False, package_ids: list[str] | None = None) -> DownloadResult:
    """Download only explicit product IDs. An empty selection does nothing."""
    sources = all_sources() if source_keys is None else source_keys
    if set(product_keys) - PRODUCTS.keys() or set(sources) - SOURCE_RUNNERS.keys():
        raise ValueError("Unknown HELP product or download source")
    if package_ids is not None and any(":" not in key or key.split(":", 1)[0] not in product_keys for key in package_ids):
        raise ValueError("Unknown HELP edition product")
    result = DownloadResult()
    if not product_keys or package_ids == []:
        return result
    extractor = extractor or ExtractorTools(find_unar(), find_lsar(), find_sevenzip())
    if not dry_run and not extractor.available:
        raise ValueError("Archive extraction requires unar/lsar or 7zz; rebuild the Docker image")
    if not dry_run:
        downloads_dir.mkdir(parents=True, exist_ok=True)
    tasks = [(source, key) for source in sources
             for key in (package_ids if package_ids is not None else product_keys)
             if key.split(":", 1)[0] in supported_product_keys(source)]
    def label(key):
        product, _, version = key.partition(":")
        return (PRODUCTS[product].menu_label or PRODUCTS[product].label) + (" " + version if version else "")
    queue = [{"product": key, "label": label(key), "source": source,
              "state": "pending"} for source, key in tasks]
    downloads = downloads or OnlineDownloader()
    downloads.begin("help", [{"id": f"{source}:{key}", "group": key, "label": label(key)}
        for source, key in tasks], replace=not preserve_downloads)
    counts = {"new_files": 0, "cached_files": 0, "bytes": 0}
    for index, (source, key) in enumerate(tasks):
        queue[index]["state"] = "running"
        def progress(values):
            downloads.update("help", f"{source}:{key}", state="running", phase=values.get("phase", "Downloading"),
                received=values.get("received", 0), bytes_total=values.get("bytes_total", 0))
            if values.get("phase") == "Downloaded":
                counts["new_files"] += 1
                counts["bytes"] += values.get("downloaded_size", 0)
            elif values.get("phase") == "Using cached archive":
                counts["cached_files"] += 1
            if values.get("warning"):
                result.warnings.append(f"{source}/{key}: {values['warning']}")
                queue[index]["warning"] = True
            if on_progress:
                on_progress({"processed": index, "total": len(tasks), "product": key,
                             "source": source, "received": 0, "bytes_total": 0, **values,
                             "file": values.get("file") or label(key),
                             "queue": [dict(item) for item in queue], "downloads": dict(counts)})
        progress({"phase": "Finding sources", "file": label(key)})
        try:
            with downloads.context("help", f"{source}:{key}"), observe_downloads(progress), select_help_packages(
                    [key] if package_ids is not None else None):
                module = importlib.import_module(SOURCE_RUNNERS[source])
                result.files.extend(module.run(product_keys=[key.split(":", 1)[0]], sources_dir=sources_dir,
                    dl_dir=downloads_dir, dry_run=dry_run, extractor=extractor))
        except Exception as error:
            result.warnings.append(f"{source}/{key}: {error}")
            queue[index]["warning"] = True
        queue[index]["state"] = "checked"
        progress({"phase": "Sources checked", "processed": index + 1, "file": label(key)})
        downloads.update("help", f"{source}:{key}", state="error" if queue[index].get("warning") else "done",
            percent=100, error=result.warnings[-1] if queue[index].get("warning") else "")
    downloads.finish("help")
    return result
