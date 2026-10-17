"""Callable HELP download orchestration; CLI and server share the providers."""

from dataclasses import dataclass, field, replace
from contextlib import closing
import importlib
from pathlib import Path
import threading

from ...help_database import crc32_file, load_help_manifest
from ...help_packages import help_package_id
from .catalog import PRODUCTS, SOURCE_RUNNERS, all_sources, products_for_source, supported_product_keys
from ..converter.selection import archive_member_selected, select_help_packages
from ..archives.core import ExtractorTools, find_lsar, find_sevenzip, find_unar
from ..processing import observe_progress
from .http import download_file
from ..converter.ingest import ingest_help
from .online import OnlineDownloader, run_processing
from .attempts import SOURCE_ERRORS, try_sources


@dataclass
class DownloadResult:
    files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def process_help_input(input_source, *, sources_dir, extractor, url, headers=None):
    """Shared transfer/validation boundary used by every HELP source provider."""
    return download_file(url, input_source.path, headers=headers,
        process=lambda staged: run_processing(
            lambda: ingest_help(replace(input_source, path=staged), sources_dir, extractor)))


def _preparation_source(row):
    """Advisory origin for lookahead; actual requests keep enforcing site limits."""
    if not row["sources"]:
        return ""
    provider = row["sources"][0]
    with select_help_packages([row["id"]] if ":" in row["id"] else None):
        products = products_for_source(provider, [row["id"].split(":", 1)[0]])
    for product in products:
        query = product.sources[provider]
        for url in (*query.direct_urls, query.api_url, query.base_url, query.raw_base_url):
            if url:
                return url
    return provider


def plan_help_downloads(product_keys, *, source_keys=None, package_ids=None):
    """One edition is one queue unit; configured providers are alternatives."""
    sources = all_sources() if source_keys is None else source_keys
    if set(product_keys) - PRODUCTS.keys() or set(sources) - SOURCE_RUNNERS.keys():
        raise ValueError("Unknown HELP product or download source")
    if package_ids is not None and any(":" not in key or key.split(":", 1)[0] not in product_keys for key in package_ids):
        raise ValueError("Unknown HELP edition product")
    rows = []
    for key in dict.fromkeys(package_ids if package_ids is not None else product_keys):
        product, _, version = key.partition(":")
        providers = []
        for source in sources:
            with select_help_packages([key] if package_ids is not None else None):
                if product in supported_product_keys(source):
                    providers.append(source)
        if package_ids is not None:
            manifest = load_help_manifest()
            exact = {source for entry in manifest.entries
                     if help_package_id(entry.product_key, entry.version or PRODUCTS[product].default_version) == key
                     for source in entry.sources}
            # Exact downloadable archives need no family/release-page crawl.
            # Keep other edition recipes and family discovery as fallbacks.
            providers.sort(key=lambda source: (source not in exact, source != "direct"))
        label = (PRODUCTS[product].menu_label or PRODUCTS[product].label) + (" " + version if version else "")
        rows.append({"id": key, "group": key, "label": label, "sources": providers, "byte_progress": False})
    return rows


def _verified_sources(package, sources_dir):
    """Only stop discovery when every registered component has a known CRC.

    Revisions of the same collection/bundle are alternatives, not additional
    required copies. Products without registered CRCs still need conversion.
    """
    manifest = load_help_manifest()
    product = manifest.product_map[package.split(":", 1)[0]]
    expected = {}
    for entry in manifest.entries:
        if help_package_id(entry.product_key, entry.version or product.default_version) != package:
            continue
        if entry.collection and entry.filenames:
            if not any(archive_member_selected(Path(entry.collection) / name, entry) for name in entry.filenames):
                continue
            component = (entry.collection, entry.bundle_stem or entry.filenames[0].casefold())
            expected.setdefault(component, []).append(entry)
    if not expected:
        return None
    for (collection, _component), entries in expected.items():
        directory = sources_dir / collection
        if not directory.is_dir() or any(path.is_symlink() for path in (directory, *directory.parents)):
            return False
        names = {name.casefold() for entry in entries for name in entry.filenames}
        checksums = {entry.crc32 for entry in entries}
        if not any(path.name.casefold() in names and path.is_file() and not path.is_symlink()
                   and crc32_file(path) in checksums for path in directory.iterdir()):
            return False
    return True


def download_products(product_keys: list[str], sources_dir: Path, downloads_dir: Path,
                      *, source_keys: list[str] | None = None, dry_run=False,
                      on_progress=None, extractor: ExtractorTools | None = None, downloads=None,
                      preserve_downloads=False, package_ids: list[str] | None = None,
                      finalize=True, on_ready=None) -> DownloadResult:
    """Download only explicit product IDs. An empty selection does nothing."""
    plan = plan_help_downloads(product_keys, source_keys=source_keys, package_ids=package_ids)
    result = DownloadResult()
    if not product_keys or package_ids == []:
        return result
    extractor = extractor or ExtractorTools(find_unar(), find_lsar(), find_sevenzip())
    if not dry_run and not extractor.available:
        raise ValueError("Archive extraction requires unar/lsar or 7zz; rebuild the Docker image")
    if not dry_run:
        downloads_dir.mkdir(parents=True, exist_ok=True)
    queue = [{"product": row["id"], "label": row["label"], "source": "",
              "state": "pending"} for row in plan]
    owns_downloader = downloads is None
    downloads = downloads or OnlineDownloader()
    try:
        downloads.begin("help", plan, replace=not preserve_downloads)
        counts = {"new_files": 0, "cached_files": 0, "bytes": 0}
        limited_sources = set()
        progress_lock = threading.Lock()
        def run_row(index, row):
            row_result = DownloadResult()
            key, source, warnings = row["id"], "", []
            attempted_inputs = []
            queue[index]["state"] = "running"
            def progress(values):
                downloads.update("help", key, state="running", phase=values.get("phase", "Downloading"),
                    received=values.get("received", 0), bytes_total=values.get("bytes_total", 0),
                    stage=values.get("stage", "prepare"), stage_percent=values.get("stage_percent"))
                with progress_lock:
                    if values.get("phase") == "Downloaded":
                        counts["new_files"] += 1
                        counts["bytes"] += values.get("downloaded_size", 0)
                    elif values.get("phase") == "Using cached archive":
                        counts["cached_files"] += 1
                    if values.get("warning"):
                        warning = f"{source}/{key}: {values['warning']}"
                        row_result.warnings.append(warning)
                        warnings.append(warning)
                        queue[index]["warning"] = True
                    snapshot = {"queue": [dict(item) for item in queue], "downloads": dict(counts)}
                if on_progress:
                    on_progress({"processed": index, "total": len(plan), "product": key,
                                 "source": source, "received": 0, "bytes_total": 0, **values,
                                 "file": values.get("file") or row["label"],
                                 **snapshot})
            verified = None if dry_run or package_ids is None else _verified_sources(key, sources_dir)
            def complete():
                return verified is True
            def process(input_source, *, url, headers=None):
                nonlocal verified
                identity = (url, input_source, headers)
                if complete() or identity in attempted_inputs:
                    return []
                # Remember failed/empty inputs too. Another query is not an
                # explicit retry, and changing a mirror still has a distinct URL.
                attempted_inputs.append(identity)
                files = process_help_input(input_source, sources_dir=sources_dir,
                    extractor=extractor, url=url, headers=headers)
                verified = None if dry_run or package_ids is None else _verified_sources(key, sources_dir)
                return files
            def attempt(provider):
                nonlocal source, verified
                if verified is True:
                    return True
                source = provider
                queue[index]["source"] = source
                progress({"phase": f"Finding sources ({source})"})
                with downloads.context("help", key), observe_progress(progress), select_help_packages(
                        [key] if package_ids is not None else None):
                    module = importlib.import_module(SOURCE_RUNNERS[source])
                    row_result.files.extend(module.run(product_keys=[key.split(":", 1)[0]],
                        dl_dir=downloads_dir, dry_run=dry_run, process=process, complete=complete))
                verified = None if dry_run or package_ids is None else _verified_sources(key, sources_dir)
                return verified
            def failed(_source, error):
                nonlocal verified
                progress({"phase": "Trying alternative source", "warning": str(error)})
                # A provider may have retained all required originals before a later
                # optional request failed. Recheck them before rejecting the edition.
                verified = None if dry_run or package_ids is None else _verified_sources(key, sources_dir)
            if verified is not True:
                try_sources(row["sources"], attempt, complete=lambda value: value is True,
                    limited_sources=limited_sources, errors=SOURCE_ERRORS + (ValueError,),
                    on_failure=failed)
            error = ""
            if not dry_run and verified is not True:
                if warnings:
                    error = "; ".join(warnings)
                elif verified is False or not row["sources"]:
                    error = f"No complete verified sources found for {row['label']}"
            # Non-CRC formats cannot be proven complete here. Keep their source
            # diagnostics in the queue, but let staged conversion decide publication.
            fatal = bool(error) and (verified is not None or package_ids is None or not row["sources"])
            if fatal:
                row_result.errors.append(error)
            queue[index]["state"] = "checked"
            progress({"phase": "Verified sources available" if verified else "Sources checked", "processed": index + 1})
            row_error = error if fatal or finalize else ""
            downloads.update("help", key, state="error" if row_error else "done" if finalize else "running", error=row_error,
                             **({} if row_error else {"percent": 100 if finalize else 35,
                                "phase": "Sources checked" if finalize else "Awaiting conversion"}))
            return row_result
        def execute(item):
            index, row = item
            with select_help_packages([row["id"]] if package_ids is not None else None):
                return run_row(index, row)
        with closing(downloads.prepare(enumerate(plan), execute,
                source=lambda item: _preparation_source(item[1]))) as pending:
            for (_index, row), future in pending:
                try:
                    completed = future.result()
                    result.files.extend(completed.files)
                    result.warnings.extend(completed.warnings)
                    result.errors.extend(completed.errors)
                except Exception as error:
                    downloads.update("help", row["id"], state="error", phase="Failed", error=str(error))
                    raise
                # Consumer cancellation after another edition's conversion
                # failed is not a download failure of this successful source.
                if on_ready and not completed.errors:
                    on_ready(row["id"])
        if finalize:
            downloads.finish("help")
        return result
    finally:
        if owns_downloader:
            downloads.close()
