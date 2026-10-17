"""Cheater.cz provider for the complete DOS Scorpions Cheater corpus."""

from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import quote_plus, urljoin

from ..processing import UnsafeContentError, report_progress
from ..converter.ingest import HelpInput
from .catalog import products_for_source
from ..converter.selection import version_selected
from .http import REQUEST_DELAY, USER_AGENT, fetch_html


SOURCE_NAME = "cheater_cz"
VERSION_ROW_RE = re.compile(
    r"<tr>\s*<td>\s*(Scorpions\s+Cheater[^<]+?)\s*</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>.*?</td>\s*<td>\s*"
    r"<a[^>]*downloadx\('([^']+)'\)",
    re.IGNORECASE | re.DOTALL,
)
DOWNLOAD_HREF_RE = re.compile(r'href="([^"]*download-file\.php\?[^"]+)"', re.IGNORECASE)


def _normalize_spaces(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _safe_segment(text: str) -> str:
    sanitized = re.sub(r"[^\w\-. ]", "_", _normalize_spaces(text)).strip()
    return sanitized or "Scorpions Cheater"


def _request_text(url: str, *, referer: str | None = None, encoding: str = "utf-8") -> str:
    time.sleep(REQUEST_DELAY)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
        "Accept-Language": "cs,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    return fetch_html(url, encoding=encoding, headers=headers)


def get_versions(history_url: str) -> list[tuple[str, str]]:
    """Return DOS version labels and download keys from the Cheater.cz history page."""
    html = fetch_html(history_url, encoding="utf-8")
    versions = [(_normalize_spaces(label), key) for label, key in VERSION_ROW_RE.findall(html)]
    unique: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    for label, key in versions:
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append((label, key))
    return unique


def get_archive_name(download_key: str, history_url: str) -> str:
    """Resolve the final archive filename for one Cheater.cz download key."""
    url = f"https://www.cheater.cz/download/get-name.php?soubor={quote_plus(download_key)}"
    name = _normalize_spaces(_request_text(url, referer=history_url, encoding="latin-1")).strip()
    if not name or name.startswith("?"):
        raise RuntimeError(f"Missing archive name for {download_key}")
    return name


def get_download_url(download_key: str, history_url: str) -> str:
    """Resolve the real file-download URL for one Cheater.cz download key."""
    url = f"https://www.cheater.cz/download/get-link.php?soubor={quote_plus(download_key)}"
    html = _request_text(url, referer=history_url, encoding="latin-1")
    match = DOWNLOAD_HREF_RE.search(html)
    if not match:
        raise RuntimeError(f"Missing download link for {download_key}")
    return urljoin(history_url, match.group(1))


def run(
    product_keys: list[str],
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Download every published DOS Scorpions Cheater release from Cheater.cz."""
    selected = products_for_source(SOURCE_NAME, product_keys)
    if not selected:
        return []

    product = selected[0]
    source_query = product.sources[SOURCE_NAME]
    history_url = source_query.base_url
    if not history_url:
        raise RuntimeError(f"No base_url configured for {product.key}/{SOURCE_NAME}")

    print(f"\n{'=' * 60}")
    print("[cheater.cz] Scorpions Cheater DOS")
    print(f"Search: {source_query.search_text}")
    print("=" * 60)

    versions = get_versions(history_url)
    if not versions:
        print("  [error] No DOS versions found on cheater.cz.")
        return []

    print(f"  Found: {len(versions)} versions")
    collected: list[Path] = []

    for version_label, download_key in versions:
        if complete and complete():
            break
        if not version_selected(product.key, version_label):
            continue
        print(f"\n  --- {version_label} ---")
        try:
            archive_name = get_archive_name(download_key, history_url)
            download_url = get_download_url(download_key, history_url)
        except UnsafeContentError:
            raise
        except Exception as exc:
            print(f"    [error] {exc}")
            report_progress("Source warning", warning=str(exc))
            continue

        archive_filename = f"{download_key}__{_safe_segment(archive_name)}"
        archive_path = dl_dir / archive_filename

        if dry_run:
            print(f"    [dry-run] key: {download_key}")
            print(f"    [dry-run] file: {archive_name}")
            print(f"    [dry-run] url: {download_url}")
            continue

        try:
            files = process(HelpInput(archive_path, product.label + "/" + _safe_segment(version_label),
                product=product), url=download_url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream,*/*;q=0.9",
                    "Accept-Language": "cs,en;q=0.9", "Referer": history_url})
            if not files:
                print("    No Scorpion source files found.")
                continue
            collected.extend(files)
        except UnsafeContentError:
            raise
        except Exception as exc:
            print(f"    [error] {exc}")
            report_progress("Source warning", warning=str(exc))

    return collected
