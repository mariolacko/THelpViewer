"""
WinWorldPC Downloader – Borland/Turbo DOS Help Files

Scrapes WinWorldPC, downloads .7z archives (disk images), extracts help files.
Limit: 25 downloads/day per IP. Archives are cached and skipped on re-run –
if rate-limited, just run the script again tomorrow.

Usage (via unified CLI):
    python3 -m downloader --source winworld
    python3 -m downloader --source winworld --products tp tc tasm

Or directly (standalone):
    python3 downloader/winworld_downloader.py
"""

from __future__ import annotations

import re
import time
import urllib.parse
from pathlib import Path

from .common import (
    collect_help_files, copy_help_files, detect_language, download_file,
    extract_archive, extract_nested, fetch_polite, parse_anchors, process_archive,
)

import tempfile


WINWORLD_BASE = "https://winworldpc.com"

PRODUCTS: dict[str, tuple[str, str]] = {
    "tp":      ("turbo-pascal",    "Borland Turbo Pascal"),
    "tc":      ("turbo-c",         "Borland Turbo C"),
    "tasm":    ("turbo-assembler", "Borland Turbo Assembler"),
    "tbasic":  ("turbo-basic",     "Borland Turbo Basic"),
    "tprolog": ("turbo-prolog",    "Borland Turbo Prolog"),
    "bc":      ("borland-c",       "Borland C++"),
    "bp":      ("borland-pascal",  "Borland Pascal"),
    "sk":      ("sidekick",        "Borland Sidekick"),
}

SKIP_VERSION_KW = (
    "windows", "os/2", "os2", "win32", "winnt", "log in",
    "(win)", "(mac)", "macintosh", "for mac",
)
SKIP_FILE_KW = (
    "manual",
    "for cpm", "for cp/m", "for macintosh", "for mac",
    "for microsoft windows", "for windows",
    "(cd)", "(iso)", " iso", "_iso",
    "patch disk",
)


# ---------------------------------------------------------------------------
# Scraping – 3 levels
# ---------------------------------------------------------------------------

def get_version_urls(product_slug: str) -> list[tuple[str, str]]:
    url = f"{WINWORLD_BASE}/product/{product_slug}/"
    print(f"\nScraping {url} …")
    html_text = fetch_polite(url)

    versions: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a in parse_anchors(html_text):
        href = a.get("href", "")
        if not re.search(rf"/product/{re.escape(product_slug)}/[^/\s]+$", href):
            continue
        full = urllib.parse.urljoin(WINWORLD_BASE, href)
        if full in seen:
            continue
        seen.add(full)

        name = a.get("_text") or href.split("/")[-1]
        if any(x in name.lower() for x in SKIP_VERSION_KW):
            print(f"  [skipped] {name!r}")
            continue

        versions.append((name, full))
        print(f"  verzia: {name}")

    return versions


def get_file_records(version_url: str) -> list[tuple[str, str]]:
    """Returns (filename, download_page_url) for each file in the version."""
    html_text = fetch_polite(version_url)
    records: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a in parse_anchors(html_text):
        href = a.get("href", "")
        if not re.match(r"^/download/[0-9a-f\-]{36}$", href, re.I):
            continue
        full = urllib.parse.urljoin(WINWORLD_BASE, href)
        if full in seen:
            continue
        seen.add(full)
        fname = a.get("title") or href.split("/")[-1]
        records.append((fname, full))
        print(f"    file: {fname}")

    return records


def get_server_urls(download_page_url: str) -> list[tuple[str, str]]:
    """Returns all available servers from the /download/<uuid> page."""
    html_text = fetch_polite(download_page_url)
    servers: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a in parse_anchors(html_text):
        href = a.get("href", "")
        if re.match(r"^/download/[0-9a-f\-]{36}/from/[0-9a-f\-]{36}$", href, re.I):
            full = urllib.parse.urljoin(WINWORLD_BASE, href)
            if full not in seen:
                seen.add(full)
                servers.append((a.get("_text", "").strip(), full))

    return servers


# ---------------------------------------------------------------------------
# Spracovanie verzie
# ---------------------------------------------------------------------------

def process_version(
    version_name: str,
    version_url: str,
    label: str,
    dl_dir: Path,
    sources_dir: Path,
    sevenz: str | None,
    dry_run: bool,
    failed: list[str],
) -> list[Path]:
    print(f"\n  --- {version_name} ---")
    records = get_file_records(version_url)
    if not records:
        print("    No records found.")
        return []

    safe_v = re.sub(r"[^\w\s\-.]", "", version_name).strip()
    collected: list[Path] = []

    for fname, dl_page_url in records:
        fname_lower = fname.lower()

        # Filtering
        if any(x in fname_lower for x in ("manual",)):
            print(f"    [skipped] {fname} (manual)")
            continue
        if any(x in fname_lower for x in SKIP_FILE_KW):
            print(f"    [skipped] {fname}")
            continue

        lang_code  = detect_language(fname)
        lang_info  = f" [{lang_code}]" if lang_code else ""
        lang_sfx   = f" ({lang_code})" if lang_code else ""
        target_dir = sources_dir / f"{label} {safe_v}{lang_sfx}".strip()

        print(f"    Looking for servers: {fname}{lang_info} …")
        if dry_run:
            print(f"      [dry-run] {dl_page_url}")
            print(f"      [target] {target_dir.relative_to(sources_dir)}")
            continue

        servers = get_server_urls(dl_page_url)
        if not servers:
            print(f"      [error] No servers for {fname}")
            failed.append(f"{fname}: no servers")
            continue

        safe_fname   = re.sub(r"[^\w\-. ]", "_", fname).strip() or "archive"
        archive_path = dl_dir / safe_fname

        downloaded = False
        for sname, surl in servers:
            try:
                print(f"    Downloading [{sname}]: {safe_fname}")
                download_file(surl, archive_path)
                downloaded = True
                break
            except RuntimeError as exc:
                if "429" in str(exc):
                    print(f"      [429] {sname} – trying next server …")
                    continue
                print(f"    [error] {exc}")
                failed.append(f"{fname}: {exc}")
                break

        if not downloaded:
            msg = f"All servers failed for {fname}"
            print(f"    [error] {msg}")
            failed.append(msg)
            continue

        with tempfile.TemporaryDirectory(prefix="ww_") as tmp:
            tmp_path = Path(tmp)
            print(f"    Extracting …")
            if not extract_archive(archive_path, tmp_path, sevenz):
                continue
            extract_nested(tmp_path, sevenz)
            files = collect_help_files(tmp_path)
            if not files:
                print("    No help files found.")
                continue
            result = copy_help_files(files, target_dir, sources_dir)
            collected.extend(result)

    return collected


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    sevenz: str | None,
) -> list[Path]:
    all_collected: list[Path] = []
    all_failed:    list[str]  = []

    for key in product_keys:
        if key not in PRODUCTS:
            print(f"  [unknown product] {key}")
            continue

        slug, label = PRODUCTS[key]
        print(f"\n{'='*60}")
        print(f"[WinWorldPC] {label}")
        print("=" * 60)

        try:
            versions = get_version_urls(slug)
        except Exception as exc:
            print(f"  [chyba] {exc}")
            continue

        for version_name, version_url in versions:
            try:
                files = process_version(
                    version_name=version_name,
                    version_url=version_url,
                    label=label,
                    dl_dir=dl_dir,
                    sources_dir=sources_dir,
                    sevenz=sevenz,
                    dry_run=dry_run,
                    failed=all_failed,
                )
                all_collected.extend(files)
            except Exception as exc:
                print(f"  [chyba] {version_name}: {exc}")
                all_failed.append(f"{version_name}: {exc}")

    if all_failed:
        print(f"\n  {len(all_failed)} downloads failed (WinWorldPC rate limit?):")
        for f in all_failed:
            print(f"    {f}")
        print("  → Run the script again tomorrow, archives will be skipped.")

    return all_collected
