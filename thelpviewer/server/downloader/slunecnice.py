"""Slunečnice.cz provider for Game-Cheater 9.02."""

from __future__ import annotations

from pathlib import Path
import json
import re
from urllib.parse import parse_qs, urljoin, urlparse

from ..processing import UnsafeContentError, report_progress
from ..converter.ingest import HelpInput
from .catalog import products_for_source
from .errors import SourceUnavailable
from .http import USER_AGENT, fetch_html, parse_anchors


SOURCE_NAME = "slunecnice"
DOWNLOAD_PAGE_SUFFIX = "stahnout/"


def find_download_url(html: str, page_url: str) -> str:
    """Find the current signed Slunečnice download URL in a download page."""
    candidates = [anchor.get("href", "") for anchor in parse_anchors(html)]
    # The partner-offer page now keeps the program's URL in a JS string rather
    # than an anchor. Decode that literal only; never execute page scripts or
    # follow the unrelated partnerUrl (antivirus advertisement).
    for literal in re.findall(r'\b(?:var|let|const)\s+softwareUrl\s*=\s*("(?:\\.|[^"\\])*")\s*;', html):
        try:
            candidates.append(json.loads(literal))
        except json.JSONDecodeError:
            continue
    page = urlparse(page_url)
    for candidate in candidates:
        href = urljoin(page_url, candidate)
        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        if (parsed.scheme == "https" and parsed.netloc == page.netloc
                and parsed.path.startswith(page.path.rstrip("/") + "/")
                and query.get("md5") and query.get("expires")):
            return href
    raise SourceUnavailable("Game-Cheater download link was not found on Slunečnice.cz")


def run(
    product_keys: list[str],
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Download and extract the Game-Cheater database from Slunečnice.cz."""
    selected = products_for_source(SOURCE_NAME, product_keys)
    if not selected:
        return []

    collected: list[Path] = []
    for product in selected:
        if complete and complete():
            break
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
            print(f"    [dry-run] target: Game-Cheater/{product.label}")
            continue

        try:
            collected.extend(process(HelpInput(archive_path, "Game-Cheater/" + product.label,
                members=tuple(sorted(database_filenames)), inner_member="INSTGC.EXE"), url=download_url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/zip,application/octet-stream,*/*;q=0.9",
                    "Referer": download_page}))
        except UnsafeContentError:
            raise
        except Exception as exc:
            print(f"    [error] {exc}")
            report_progress("Source warning", warning=str(exc))
    return collected
