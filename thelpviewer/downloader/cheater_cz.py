"""Cheater.cz provider for the complete DOS Scorpions Cheater corpus."""

from __future__ import annotations

import re
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote_plus, urljoin

from .catalog import ProductSpec, products_for_source
from .collector import copy_help_files
from .extractor import ExtractorTools, expand_single_file_payloads, extract_file, extract_nested
from .http import DOWNLOAD_DELAY, REQUEST_DELAY, USER_AGENT, fetch_html, get_opener


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
    request = urllib.request.Request(url, headers=headers)
    with get_opener().open(request, timeout=30) as resp:
        return resp.read().decode(encoding, errors="replace")


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


def _download_with_referer(url: str, dest: Path, *, referer: str) -> Path:
    if dest.exists():
        print(f"    [skipped] {dest.name} (exists)")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    time.sleep(DOWNLOAD_DELAY)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,*/*;q=0.9",
            "Accept-Language": "cs,en;q=0.9",
            "Referer": referer,
        },
    )
    with get_opener().open(request, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with tmp.open("wb") as fh:
            while chunk := resp.read(65536):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    print(
                        f"\r    {dest.name}: {done * 100 // total:3d}%"
                        f" ({done // 1024}kB/{total // 1024}kB)",
                        end="",
                        flush=True,
                    )
        if total:
            print()
    tmp.rename(dest)
    return dest


def _collect_scorpion_source_files(work_dir: Path, product: ProductSpec) -> list[Path]:
    files: list[Path] = []
    for path in sorted(work_dir.rglob("*")):
        if not path.is_file():
            continue
        if product.conversion.matches(path):
            files.append(path)
    if files:
        return files

    for path in sorted(work_dir.rglob("*")):
        if not path.is_file():
            continue
        if product.conversion.matches(path, secondary=True):
            files.append(path)
    return files


def _collect_from_archive(
    archive_path: Path,
    *,
    product_label: str,
    version_label: str,
    sources_dir: Path,
    extractor: ExtractorTools,
    product: ProductSpec,
) -> list[Path]:
    target_dir = sources_dir / product_label / _safe_segment(version_label)
    with tempfile.TemporaryDirectory(prefix="dlscorpion_") as tmp:
        tmp_path = Path(tmp)
        if not extract_file(archive_path, tmp_path, extractor):
            return []
        extract_nested(tmp_path, extractor)
        expand_single_file_payloads(tmp_path, extractor)
        files = _collect_scorpion_source_files(tmp_path, product)
        if not files:
            return []
        return copy_help_files(files, target_dir, sources_dir)


def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    extractor: ExtractorTools,
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
        print(f"\n  --- {version_label} ---")
        try:
            archive_name = get_archive_name(download_key, history_url)
            download_url = get_download_url(download_key, history_url)
        except Exception as exc:
            print(f"    [error] {exc}")
            continue

        archive_filename = f"{download_key}__{_safe_segment(archive_name)}"
        archive_path = dl_dir / archive_filename

        if dry_run:
            print(f"    [dry-run] key: {download_key}")
            print(f"    [dry-run] file: {archive_name}")
            print(f"    [dry-run] url: {download_url}")
            continue

        try:
            _download_with_referer(download_url, archive_path, referer=history_url)
            files = _collect_from_archive(
                archive_path,
                product_label=product.label,
                version_label=version_label,
                sources_dir=sources_dir,
                extractor=extractor,
                product=product,
            )
            if not files:
                print("    No Scorpion source files found.")
                continue
            collected.extend(files)
        except Exception as exc:
            print(f"    [error] {exc}")

    return collected
