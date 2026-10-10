"""WinWorldPC provider for the unified downloader."""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

from .catalog import products_for_source
from .collector import detect_language
from .extractor import ExtractorTools, collect_from_archive
from .http import download_file, fetch_polite, parse_anchors


SOURCE_NAME = "winworld"
WINWORLD_BASE = "https://winworldpc.com"

SKIP_VERSION_KW = (
    "windows",
    "os/2",
    "os2",
    "win32",
    "winnt",
    "log in",
    "(win)",
    "(mac)",
    "macintosh",
    "for mac",
)
SKIP_FILE_KW = (
    "manual",
    "for cpm",
    "for cp/m",
    "for macintosh",
    "for mac",
    "for microsoft windows",
    "for windows",
    "(cd)",
    "(iso)",
    " iso",
    "_iso",
    "patch disk",
)


def get_version_urls(product_slug: str) -> list[tuple[str, str]]:
    """Return visible WinWorld version pages for one product slug."""
    url = f"{WINWORLD_BASE}/product/{product_slug}/"
    print(f"\nScraping {url} …")
    html_text = fetch_polite(url)

    versions: list[tuple[str, str]] = []
    seen: set[str] = set()

    for anchor in parse_anchors(html_text):
        href = anchor.get("href", "")
        if not re.search(rf"/product/{re.escape(product_slug)}/[^/\s]+$", href):
            continue
        full = urllib.parse.urljoin(WINWORLD_BASE, href)
        if full in seen:
            continue
        seen.add(full)

        name = anchor.get("_text") or href.split("/")[-1]
        if any(token in name.lower() for token in SKIP_VERSION_KW):
            print(f"  [skipped] {name!r}")
            continue

        versions.append((name, full))
        print(f"  version: {name}")

    return versions


def get_file_records(version_url: str) -> list[tuple[str, str]]:
    """Return download-page records for one WinWorld version page."""
    html_text = fetch_polite(version_url)
    records: list[tuple[str, str]] = []
    seen: set[str] = set()

    for anchor in parse_anchors(html_text):
        href = anchor.get("href", "")
        if not re.match(r"^/download/[0-9a-f\-]{36}$", href, re.I):
            continue
        full = urllib.parse.urljoin(WINWORLD_BASE, href)
        if full in seen:
            continue
        seen.add(full)
        filename = anchor.get("title") or href.split("/")[-1]
        records.append((filename, full))
        print(f"    file: {filename}")

    return records


def get_server_urls(download_page_url: str) -> list[tuple[str, str]]:
    """Return all actual WinWorld mirror download URLs for one file page."""
    html_text = fetch_polite(download_page_url)
    servers: list[tuple[str, str]] = []
    seen: set[str] = set()

    for anchor in parse_anchors(html_text):
        href = anchor.get("href", "")
        if not re.match(r"^/download/[0-9a-f\-]{36}/from/[0-9a-f\-]{36}$", href, re.I):
            continue
        full = urllib.parse.urljoin(WINWORLD_BASE, href)
        if full in seen:
            continue
        seen.add(full)
        servers.append((anchor.get("_text", "").strip(), full))

    return servers


def process_version(
    version_name: str,
    version_url: str,
    label: str,
    dl_dir: Path,
    sources_dir: Path,
    extractor: ExtractorTools,
    dry_run: bool,
    failed: list[str],
) -> list[Path]:
    """Download one WinWorld version and collect help files from its archives."""
    print(f"\n  --- {version_name} ---")
    records = get_file_records(version_url)
    if not records:
        print("    No records found.")
        return []

    safe_version = re.sub(r"[^\w\s\-.]", "", version_name).strip()
    collected: list[Path] = []

    for filename, dl_page_url in records:
        lowered = filename.lower()
        if any(token in lowered for token in SKIP_FILE_KW):
            print(f"    [skipped] {filename}")
            continue

        lang_code = detect_language(filename)
        if dry_run:
            print(f"      [dry-run] {dl_page_url}")
            print(f"      [search]   {version_name}")
            continue

        servers = get_server_urls(dl_page_url)
        if not servers:
            print(f"      [error] No servers for {filename}")
            failed.append(f"{filename}: no servers")
            continue

        safe_filename = re.sub(r"[^\w\-. ]", "_", filename).strip() or "archive"
        archive_path = dl_dir / safe_filename
        downloaded = False

        for server_name, server_url in servers:
            try:
                print(f"    Downloading [{server_name}]: {safe_filename}")
                download_file(server_url, archive_path)
                downloaded = True
                break
            except RuntimeError as exc:
                if "429" in str(exc):
                    print(f"      [429] {server_name} – trying next server …")
                    continue
                print(f"    [error] {exc}")
                failed.append(f"{filename}: {exc}")
                break

        if not downloaded:
            msg = f"All servers failed for {filename}"
            print(f"    [error] {msg}")
            failed.append(msg)
            continue

        result = collect_from_archive(
            archive_path,
            f"{label} {safe_version}".strip(),
            sources_dir,
            extractor,
            lang_code=lang_code,
        )
        collected.extend(result)
        if not result:
            print("    No help files found.")

    return collected


def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    extractor: ExtractorTools,
) -> list[Path]:
    """Run the WinWorldPC provider for selected logical products."""
    all_collected: list[Path] = []
    all_failed: list[str] = []

    for product in products_for_source(SOURCE_NAME, product_keys):
        source_query = product.sources[SOURCE_NAME]
        if not source_query.slug:
            continue

        print(f"\n{'=' * 60}")
        print(f"[WinWorldPC] {product.label}")
        print(f"Search: {source_query.search_text}")
        print("=" * 60)

        try:
            versions = get_version_urls(source_query.slug)
        except Exception as exc:
            print(f"  [error] {exc}")
            continue

        for version_name, version_url in versions:
            try:
                files = process_version(
                    version_name=version_name,
                    version_url=version_url,
                    label=product.label,
                    dl_dir=dl_dir,
                    sources_dir=sources_dir,
                    extractor=extractor,
                    dry_run=dry_run,
                    failed=all_failed,
                )
                all_collected.extend(files)
            except Exception as exc:
                print(f"  [error] {version_name}: {exc}")
                all_failed.append(f"{version_name}: {exc}")

    if all_failed:
        print(f"\n  {len(all_failed)} downloads failed (WinWorldPC rate limit?):")
        for item in all_failed:
            print(f"    {item}")
        print("  → Run the script again tomorrow, cached archives will be reused.")

    return all_collected
