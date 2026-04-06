"""
Old-dos.ru Downloader – Borland/Turbo DOS Help Files

Scrapes the programming tools category on old-dos.ru (cat=102),
filters Borland/Turbo products, and downloads archives.

old-dos.ru is a Russian archive of old DOS software (CP-1251 encoding).
The site does not require login for browsing, only for searching.

Usage:
    python3 -m downloader --source olddos
    python3 -m downloader --source olddos --products tp tc tasm
"""

from __future__ import annotations

import re
import time
import urllib.parse
from pathlib import Path

from .common import (
    DOWNLOAD_DELAY, detect_language, download_file,
    fetch_html, fetch_polite, parse_anchors, process_archive, require_7z,
)

import html as html_module


OLDDOS_BASE = "https://old-dos.ru"

# Programming tool categories on old-dos.ru (2025+):
#   51 = Pascal/Delphi
#   52 = C/C++
#   50 = Assembler
#   58 = Basic/Visual Basic
#  126 = Other languages (Prolog etc.)
#  229 = Debuggers
# Old cat=102 = multimedia, doesn't work for Borland products
PROGRAMMING_CATS = [51, 52, 50, 58, 126, 229]

# Keywords for filtering Borland products
BORLAND_FILTER = {
    "turbo pascal", "turbo c", "turbo c++", "turbo assembler",
    "turbo basic", "turbo prolog", "turbo debugger",
    "borland pascal", "borland c", "borland c++",
    "tasm", "tpas",
}

# Products: key → list of search keywords in name/item
PRODUCTS: dict[str, tuple[list[str], str]] = {
    "tp":      (["turbo pascal"],            "Borland Turbo Pascal"),
    "tc":      (["turbo c", "turbo c++", "turbo cpp"], "Borland Turbo C"),
    "tasm":    (["turbo assembler", "tasm"], "Borland Turbo Assembler"),
    "td":      (["turbo debugger"],          "Borland Turbo Debugger"),
    "tbasic":  (["turbo basic"],             "Borland Turbo Basic"),
    "tprolog": (["turbo prolog"],            "Borland Turbo Prolog"),
    "bc":      (["borland c++", "borland c"],"Borland C++"),
    "bp":      (["borland pascal"],          "Borland Pascal"),
}


# ---------------------------------------------------------------------------
# Scraping old-dos.ru
# ---------------------------------------------------------------------------

def fetch_olddos(url: str) -> str:
    """Download HTML from old-dos.ru with CP-1251 encoding."""
    time.sleep(1.0)
    return fetch_html(url, encoding="cp1251")


def get_file_listing_pages(cat: int) -> list[str]:
    """
    Returns URLs of all category pages (pagination).
    old-dos.ru: cat=N&id=M where M is the page number.
    """
    base_url = f"{OLDDOS_BASE}/index.php?page=files&mode=files&do=list&cat={cat}"
    html_text = fetch_olddos(base_url)

    pages = {base_url}
    for a in parse_anchors(html_text):
        href = html_module.unescape(a.get("href", ""))
        if f"cat={cat}" in href and "do=list" in href:
            full = href if href.startswith("http") else OLDDOS_BASE + "/" + href.lstrip("/")
            pages.add(full)

    # Sort by id= parameter (pages go 1,2,3...)
    def page_num(url: str) -> int:
        m = re.search(r"[&?]id=(\d+)", url)
        return int(m.group(1)) if m else 0

    return sorted(pages, key=page_num)


def parse_file_entries(html_text: str) -> list[dict[str, str]]:
    """
    Extracts file entries from the listing page.
    old-dos.ru structure (2025+):
      <a href="index.php?page=files&mode=files&do=show&id=N">Name</a>
    Older structure (for compatibility):
      <a href="index.php?page=files&mode=files&do=showfile&id=N">Name</a>
    """
    entries = []
    seen = set()

    for a in parse_anchors(html_text):
        href = html_module.unescape(a.get("href", ""))
        # Support both URL formats
        if "do=show&id=" not in href and "do=showfile&id=" not in href:
            # Skip pagination links (do=list&cat=N&id=M) and other
            if "do=show" not in href:
                continue
        m = re.search(r"(?:do=show(?:file)?&id=|do=show&id=)(\d+)", href)
        if not m:
            # fallback: any href with mode=files and id= (not a cat page)
            if "mode=files" in href and "do=show" in href:
                m = re.search(r"[?&]id=(\d+)", href)
        if not m:
            continue
        file_id = m.group(1)
        if file_id in seen:
            continue
        seen.add(file_id)
        name = a.get("_text", "").strip()
        if not name or len(name) < 3:
            continue
        # Exclude #download anchor duplicates
        href_clean = href.split("#")[0]
        full = href_clean if href_clean.startswith("http") else OLDDOS_BASE + "/" + href_clean.lstrip("/")
        entries.append({"id": file_id, "name": name, "url": full})

    return entries


def get_download_url(file_page_url: str) -> str | None:
    """
    Extracts the download link from the file detail page.
    old-dos.ru (2025+): /dl.php?id=N
    Old format: /files/[subdir]/[name].zip or .7z
    Returns first found dl.php or direct archive link.
    """
    html_text = fetch_olddos(file_page_url)

    for a in parse_anchors(html_text):
        href = html_module.unescape(a.get("href", ""))
        # New format: dl.php?id=N
        if re.search(r"/dl\.php\?id=\d+", href, re.I):
            return href if href.startswith("http") else OLDDOS_BASE + "/" + href.lstrip("/")
        # Old format: direct archive
        if re.search(r"\.(zip|7z|rar|arj|lzh)(\?|$)", href, re.I):
            return href if href.startswith("http") else OLDDOS_BASE + "/" + href.lstrip("/")

    return None


def matches_product(name: str, keywords: list[str]) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in keywords)


def matches_any_borland(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in BORLAND_FILTER)


# ---------------------------------------------------------------------------
# Spracovanie
# ---------------------------------------------------------------------------

def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    sevenz: str | None,
) -> list[Path]:
    print(f"\n{'='*60}")
    print("[old-dos.ru] Loading programming tool categories …")
    print("=" * 60)

    # Collect entries from all relevant categories
    all_entries: list[dict[str, str]] = []
    for cat in PROGRAMMING_CATS:
        pages = get_file_listing_pages(cat)
        print(f"  cat={cat}: {len(pages)} pages")
        for page_url in pages:
            html_text = fetch_olddos(page_url)
            entries = parse_file_entries(html_text)
            all_entries.extend(entries)

    # Deduplication
    seen_ids: set[str] = set()
    unique_entries = []
    for e in all_entries:
        if e["id"] not in seen_ids:
            seen_ids.add(e["id"])
            unique_entries.append(e)

    print(f"  Total entries: {len(unique_entries)}")

    # Filter only Borland items
    borland_entries = [e for e in unique_entries if matches_any_borland(e["name"])]
    print(f"  Borland entries: {len(borland_entries)}")
    for e in borland_entries:
        print(f"    {e['name']}")

    all_collected: list[Path] = []

    for key in product_keys:
        if key not in PRODUCTS:
            print(f"  [unknown product] {key}")
            continue

        keywords, label = PRODUCTS[key]
        matching = [e for e in borland_entries if matches_product(e["name"], keywords)]

        print(f"\n  --- {label} ({len(matching)} found) ---")

        for entry in matching:
            print(f"    {entry['name']}")
            if dry_run:
                print(f"      [dry-run] {entry['url']}")
                continue

            dl_url = get_download_url(entry["url"])
            if not dl_url:
                print(f"      [error] Could not find download link")
                continue

            lang_code = detect_language(entry["name"])
            lang_info = f" [{lang_code}]" if lang_code else ""
            print(f"      Downloading{lang_info}: {dl_url.split('/')[-1]}")

            fname = urllib.parse.urlparse(dl_url).path.split("/")[-1]
            safe_fname = re.sub(r"[^\w\-. ]", "_", fname) or "archive"
            archive_path = dl_dir / f"od_{safe_fname}"

            try:
                download_file(dl_url, archive_path)
            except Exception as exc:
                print(f"      [chyba] {exc}")
                continue

            lang_sfx   = f" ({lang_code})" if lang_code else ""
            result = process_archive(
                archive_path, f"{label}{lang_sfx}".strip(),
                None, sources_dir, sevenz,
            )
            all_collected.extend(result)
            if not result:
                print("      No help files found.")

    return all_collected
