"""old-dos.ru provider for the unified downloader."""

from __future__ import annotations

import html as html_module
import re
import time
import urllib.parse
from pathlib import Path

from ..processing import UnsafeContentError, report_progress
from .catalog import ProductSpec, SourceQuery, products_for_source
from ..converter.selection import version_selected
from ..converter.sources import detect_language
from ..converter.ingest import HelpInput
from .http import fetch_html, parse_anchors
from .cache import download_filename


SOURCE_NAME = "olddos"
# This archive serves HTTP; its HTTPS endpoint redirects back to HTTP.
# Declare that source explicitly without allowing HTTPS downgrades elsewhere.
OLDDOS_BASE = "http://old-dos.ru"


def fetch_olddos(url: str) -> str:
    """Fetch old-dos.ru HTML using the site's CP-1251 encoding."""
    time.sleep(1.0)
    return fetch_html(url, encoding="cp1251")


def get_file_listing_pages(category_id: int) -> list[str]:
    """Return all pagination URLs for one old-dos category."""
    base_url = f"{OLDDOS_BASE}/index.php?page=files&mode=files&do=list&cat={category_id}"
    html_text = fetch_olddos(base_url)

    pages = {base_url}
    for anchor in parse_anchors(html_text):
        href = html_module.unescape(anchor.get("href", ""))
        if f"cat={category_id}" in href and "do=list" in href:
            full = href if href.startswith("http") else OLDDOS_BASE + "/" + href.lstrip("/")
            pages.add(full)

    def page_num(url: str) -> int:
        match = re.search(r"[&?]id=(\d+)", url)
        return int(match.group(1)) if match else 0

    return sorted(pages, key=page_num)


def parse_file_entries(html_text: str) -> list[dict[str, str]]:
    """Extract file-detail links from one old-dos listing page."""
    entries: list[dict[str, str]] = []
    seen: set[str] = set()

    for anchor in parse_anchors(html_text):
        href = html_module.unescape(anchor.get("href", ""))
        if "do=show&id=" not in href and "do=showfile&id=" not in href:
            if "do=show" not in href:
                continue
        match = re.search(r"(?:do=show(?:file)?&id=|do=show&id=)(\d+)", href)
        if not match and "mode=files" in href and "do=show" in href:
            match = re.search(r"[?&]id=(\d+)", href)
        if not match:
            continue

        file_id = match.group(1)
        if file_id in seen:
            continue
        seen.add(file_id)

        name = anchor.get("_text", "").strip()
        if not name or len(name) < 3:
            continue

        href_clean = href.split("#")[0]
        full = href_clean if href_clean.startswith("http") else OLDDOS_BASE + "/" + href_clean.lstrip("/")
        entries.append({"id": file_id, "name": name, "url": full})

    return entries


def get_download_url(file_page_url: str) -> str | None:
    """Extract the actual archive download URL from one old-dos detail page."""
    html_text = fetch_olddos(file_page_url)
    for anchor in parse_anchors(html_text):
        href = html_module.unescape(anchor.get("href", ""))
        if re.search(r"/dl\.php\?id=\d+", href, re.I):
            return href if href.startswith("http") else OLDDOS_BASE + "/" + href.lstrip("/")
        if re.search(r"\.(zip|7z|rar|arj|lzh)(\?|$)", href, re.I):
            return href if href.startswith("http") else OLDDOS_BASE + "/" + href.lstrip("/")
    return None


def matches_keywords(name: str, keywords: tuple[str, ...]) -> bool:
    """Return ``True`` when one old-dos item matches the configured keywords."""
    lowered = name.lower()
    return any(keyword in lowered for keyword in keywords)


def _load_category_entries(category_ids: set[int]) -> dict[int, list[dict[str, str]]]:
    entries_by_category: dict[int, list[dict[str, str]]] = {}
    for category_id in sorted(category_ids):
        pages = get_file_listing_pages(category_id)
        print(f"  cat={category_id}: {len(pages)} pages")
        entries: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        for page_url in pages:
            html_text = fetch_olddos(page_url)
            for entry in parse_file_entries(html_text):
                if entry["id"] in seen_ids:
                    continue
                seen_ids.add(entry["id"])
                entries.append(entry)
        entries_by_category[category_id] = entries
    return entries_by_category


def _entries_for_product(
    product: ProductSpec,
    source_query: SourceQuery,
    entries_by_category: dict[int, list[dict[str, str]]],
) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for category_id in source_query.category_ids:
        for entry in entries_by_category.get(category_id, []):
            if entry["id"] in seen_ids:
                continue
            if not matches_keywords(entry["name"], source_query.keywords):
                continue
            seen_ids.add(entry["id"])
            entries.append(entry)
    return entries


def run(
    product_keys: list[str],
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Run the old-dos.ru provider for selected logical products."""
    print(f"\n{'=' * 60}")
    print("[old-dos.ru] Loading configured categories …")
    print("=" * 60)

    selected_products = products_for_source(SOURCE_NAME, product_keys)
    needed_categories = {
        category_id
        for product in selected_products
        for category_id in product.sources[SOURCE_NAME].category_ids
    }
    entries_by_category = _load_category_entries(needed_categories)
    all_collected: list[Path] = []

    for product in selected_products:
        if complete and complete():
            break
        source_query = product.sources[SOURCE_NAME]
        matching = _entries_for_product(product, source_query, entries_by_category)

        print(f"\n  --- {product.label} ({len(matching)} found) ---")
        print(f"  Search: {source_query.search_text}")

        for entry in matching:
            if complete and complete():
                break
            if not version_selected(product.key, entry["name"]):
                continue
            print(f"    {entry['name']}")
            if dry_run:
                print(f"      [dry-run] {entry['url']}")
                continue

            download_url = get_download_url(entry["url"])
            if not download_url:
                print("      [error] Could not find download link")
                continue

            lang_code = detect_language(entry["name"])
            filename = urllib.parse.urlparse(download_url).path.split("/")[-1]
            # dl.php?id=... identifies different archives. Its basename alone
            # would reuse the first product's bytes for every subsequent link.
            suffix = Path(filename).suffix.lower()
            if suffix not in {".zip", ".7z", ".rar", ".arj", ".lzh", ".img", ".iso"}:
                suffix = ".archive"
            archive_path = dl_dir / ("od_" + download_filename(entry["name"] + " " + entry["id"]) + suffix)

            try:
                print(f"      Archive: {archive_path.name}")
                result = process(HelpInput(archive_path, product.label, language=lang_code,
                    members=source_query.archive_members, allow_partial=True), url=download_url)
            except UnsafeContentError:
                raise
            except Exception as exc:
                print(f"      [error] {exc}")
                report_progress("Source warning", warning=str(exc))
                continue

            all_collected.extend(result)
            if not result:
                print("      No help files found.")

    return all_collected
