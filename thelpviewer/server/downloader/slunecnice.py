"""Slunečnice.cz provider for Game-Cheater 9.02."""

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .catalog import product_spec, products_for_source
from .collector import copy_help_files
from .extractor import ExtractorTools, extract_file
from .http import USER_AGENT, fetch_html, download_file, parse_anchors


SOURCE_NAME = "slunecnice"
DOWNLOAD_PAGE_SUFFIX = "stahnout/"
DATABASE_FILENAMES = {
    name.upper()
    for name in product_spec("game-cheater").conversion.required_filenames
}


def find_download_url(html: str, page_url: str) -> str:
    """Find the current signed Slunečnice download URL in a download page."""
    for anchor in parse_anchors(html):
        href = urljoin(page_url, anchor.get("href", ""))
        parsed = urlparse(href)
        if parsed.path.startswith("/sw/game-cheater/stahnout/") and "md5=" in parsed.query:
            return href
    raise RuntimeError("Game-Cheater download link was not found on Slunečnice.cz")


def _download_archive(url: str, dest: Path, *, referer: str) -> Path:
    return download_file(url, dest, headers={"User-Agent": USER_AGENT,
        "Accept": "application/zip,application/octet-stream,*/*;q=0.9", "Referer": referer})


def _collect_database_files(
    work_dir: Path,
    filenames: set[str] | None = None,
) -> list[Path]:
    selected_names = DATABASE_FILENAMES if filenames is None else filenames
    by_name: dict[str, Path] = {}
    for path in sorted(work_dir.rglob("*")):
        name = path.name.upper()
        if path.is_file() and name in selected_names:
            current = by_name.get(name)
            if current is None or "GCDATA" in {part.upper() for part in path.parts}:
                by_name[name] = path
    return [by_name[name] for name in sorted(by_name)]


def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    extractor: ExtractorTools,
) -> list[Path]:
    """Download and extract the Game-Cheater database from Slunečnice.cz."""
    selected = products_for_source(SOURCE_NAME, product_keys)
    if not selected:
        return []

    collected: list[Path] = []
    for product in selected:
        query = product.sources[SOURCE_NAME]
        database_filenames = {name.upper() for name in product.conversion.required_filenames}
        if not database_filenames:
            raise RuntimeError(f"No required conversion files configured for {product.key}")
        catalog_url = query.base_url
        if not catalog_url:
            raise RuntimeError(f"No base_url configured for {product.key}/{SOURCE_NAME}")
        download_page = urljoin(catalog_url.rstrip("/") + "/", DOWNLOAD_PAGE_SUFFIX)
        print(f"\n{'=' * 60}")
        print(f"[slunecnice.cz] {product.label}")
        print(f"Page: {catalog_url}")
        print("=" * 60)

        html = fetch_html(download_page)
        download_url = find_download_url(html, download_page)
        archive_path = dl_dir / "instgc.zip"
        if dry_run:
            print(f"    [dry-run] url: {download_url}")
            print(f"    [dry-run] target: {sources_dir / 'Game-Cheater' / product.label}")
            continue

        try:
            _download_archive(download_url, archive_path, referer=download_page)
            with tempfile.TemporaryDirectory(prefix="dlgamecheater_") as tmp:
                work_dir = Path(tmp)
                if not extract_file(archive_path, work_dir, extractor):
                    print("    [error] Could not extract instgc.zip")
                    continue
                installers = [
                    path for path in work_dir.rglob("*")
                    if path.is_file() and path.name.upper() == "INSTGC.EXE"
                ]
                if not installers:
                    print("    [error] INSTGC.EXE was not found in instgc.zip")
                    continue
                installer_dir = work_dir / "installer"
                if not extract_file(installers[0], installer_dir, extractor):
                    print("    [error] Could not extract INSTGC.EXE")
                    continue
                files = _collect_database_files(installer_dir, database_filenames)
                missing = sorted(database_filenames - {path.name.upper() for path in files})
                if missing:
                    print(f"    [error] Missing database files: {', '.join(missing)}")
                    continue
                target_dir = sources_dir / "Game-Cheater" / product.label
                collected.extend(copy_help_files(files, target_dir, sources_dir))
        except Exception as exc:
            print(f"    [error] {exc}")
    return collected
