"""Archive.org provider for the unified downloader."""

from __future__ import annotations

import re
import time
import urllib.parse
from pathlib import Path

from .catalog import ProductSpec, SourceQuery, products_for_source
from .collector import HELP_EXTENSIONS, detect_language, is_winhelp
from .extractor import ExtractorTools, collect_from_archive
from .http import download_file, fetch_json


SOURCE_NAME = "archiveorg"
ARCHIVEORG_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVEORG_METADATA = "https://archive.org/metadata"
ARCHIVEORG_DOWNLOAD = "https://archive.org/download"

SKIP_IDENTIFIERS = {
    "turbo-pascal-bcd-1xdiskette",
}


def _identifier_from_direct_url(value: str) -> str | None:
    """Extract an Archive.org item identifier from a known item URL."""
    text = str(value or "").strip().rstrip("/")
    if not text:
        return None
    marker = "/details/"
    if marker in text:
        return text.split(marker, 1)[1].split("/", 1)[0] or None
    if "/" not in text and " " not in text:
        return text
    return None


def search_items(query: str, rows: int = 50) -> list[dict]:
    """Return Archive.org search results for one advanced-search query."""
    params = urllib.parse.urlencode(
        {
            "q": query,
            "fl[]": "identifier,title,subject,creator",
            "rows": rows,
            "output": "json",
            "page": 1,
        }
    )
    data = fetch_json(f"{ARCHIVEORG_SEARCH}?{params}")
    docs = data.get("response", {}).get("docs", [])
    return [doc for doc in docs if doc.get("identifier") not in SKIP_IDENTIFIERS]


def get_item_files(identifier: str) -> list[dict]:
    """Return metadata file entries for one Archive.org item."""
    data = fetch_json(f"{ARCHIVEORG_METADATA}/{identifier}/files")
    return data.get("result", [])


def get_item(identifier: str) -> dict | None:
    """Fetch a minimal Archive.org item record by identifier."""
    params = urllib.parse.urlencode(
        {
            "q": f"identifier:{identifier}",
            "fl[]": "identifier,title,subject,creator",
            "rows": 1,
            "output": "json",
            "page": 1,
        }
    )
    data = fetch_json(f"{ARCHIVEORG_SEARCH}?{params}")
    docs = data.get("response", {}).get("docs", [])
    return docs[0] if docs else None


def is_relevant_item(item: dict, source_query: SourceQuery) -> bool:
    """Filter Archive.org search noise for one product query."""
    keywords = tuple(kw.lower() for kw in source_query.keywords)
    title = (item.get("title") or "").lower()
    creator_raw = item.get("creator") or []
    if isinstance(creator_raw, str):
        creator_raw = [creator_raw]
    creator = " ".join(creator_raw).lower()
    subject_raw = item.get("subject") or []
    if isinstance(subject_raw, str):
        subject_raw = [subject_raw]
    subject = " ".join(subject_raw).lower()
    identifier = (item.get("identifier") or "").lower()
    combined = f"{title} {creator} {subject}"

    if keywords and not any(keyword in combined for keyword in keywords):
        return False

    skip = (
        "atari",
        "c64",
        "commodore",
        "apple ii",
        "amiga",
        "cp/m",
        "cpm",
        "disk image dump",
        "flux dump",
        "for windows",
        "turbo c for windows",
        "turbo pascal for windows",
        "turbo debugger for windows",
        "windows-only",
        "pour windows",
        "für windows",
        "for win",
        "pc-98",
        "pc-9801",
        "pc98",
        "9801",
        "pc-9x",
    )
    if any(token in combined or token in identifier for token in skip):
        return False

    if "c++ builder" in title or "cppbuilder" in identifier or "cpp-builder" in identifier:
        return False
    if "builder" in title and "borland c++" in title:
        return False

    game_keywords = (
        "game",
        "demo",
        "shareware game",
        "go-moku",
        "chess",
        "puzzle",
        "vicki",
        "adventure",
        "arcade",
        "tetris",
        "invaders",
    )
    if any(keyword in title or keyword in identifier for keyword in game_keywords):
        return False

    return True


def pick_download_files(files: list[dict], identifier: str) -> list[tuple[str, str]]:
    """Choose direct help files or the best candidate archives to download."""
    archive_exts = {".7z", ".zip", ".rar"}
    direct_help: list[tuple[str, int]] = []
    archives: list[tuple[str, int]] = []

    for item in files:
        name = item.get("name", "")
        if not name or "/" in name:
            continue
        ext = Path(name).suffix.lower()
        size = int(item.get("size") or 0)
        lowered = name.lower()

        if any(token in lowered for token in ("kryoflux", ".raw", ".scp", ".ipf", ".mfm")):
            continue

        if ext in HELP_EXTENSIONS:
            direct_help.append((name, size))
            continue
        if ext in archive_exts or ext in {".img", ".ima", ".dsk", ".flp"}:
            if size > 0:
                archives.append((name, size))

    result: list[tuple[str, str]] = []
    base = f"{ARCHIVEORG_DOWNLOAD}/{identifier}"

    if direct_help:
        for name, _size in direct_help:
            result.append((name, f"{base}/{urllib.parse.quote(name)}"))
        return result

    archives_7z = [(name, size) for name, size in archives if name.lower().endswith(".7z")]
    archives_zip = [(name, size) for name, size in archives if name.lower().endswith(".zip")]
    archives_rar = [(name, size) for name, size in archives if name.lower().endswith(".rar")]
    archives_img = [
        (name, size) for name, size in archives if Path(name).suffix.lower() in {".img", ".ima", ".dsk", ".flp"}
    ]
    chosen = archives_7z or archives_zip or archives_rar or archives_img
    chosen.sort(key=lambda item: item[1])
    limit = 6 if chosen is archives_img else 20
    for name, _size in chosen[:limit]:
        result.append((name, f"{base}/{urllib.parse.quote(name)}"))
    return result


def _detect_version(title: str, identifier: str) -> str | None:
    """Best-effort version extraction for final target directory naming."""
    combined = f"{title} {identifier}".lower()
    match = re.search(r"\b(?:version\s+|v\.?\s*)?(\d+\.\d+[a-z]?)\b", combined)
    if match:
        return match.group(1)
    match = re.search(r"(?:pascal|turbo[- ]?c|assembler|debugger|basic|prolog|c\+\+|borland-c)[- _](\d)\b", combined)
    if match:
        return match.group(1)
    return None


def process_item(
    item: dict,
    product: ProductSpec,
    source_query: SourceQuery,
    dl_dir: Path,
    sources_dir: Path,
    extractor: ExtractorTools,
    dry_run: bool,
    failed: list[str],
) -> list[Path]:
    """Download one Archive.org item and collect any help files from it."""
    identifier = item["identifier"]
    title = item.get("title", identifier)

    print(f"\n  [{identifier}] {title}")
    files = get_item_files(identifier)
    to_download = pick_download_files(files, identifier)
    if not to_download:
        print("    No suitable files on archive.org.")
        return []

    lang_code = detect_language(title)
    version = _detect_version(title, identifier)
    version_suffix = f" {version}" if version else ""
    base_label = f"{product.label}{version_suffix}".strip()
    collected: list[Path] = []

    for filename, url in to_download:
        print(f"    file: {filename}")
        if dry_run:
            print(f"      [dry-run] {url}")
            print(f"      [search]   {source_query.search_text}")
            continue

        ext = Path(filename).suffix.lower()
        if ext in HELP_EXTENSIONS:
            target_dir = sources_dir / f"{base_label}{f' ({lang_code})' if lang_code else ''}".strip()
            dest = target_dir / filename.upper()
            if dest.exists():
                print(f"    [skipped] {filename} (exists)")
                continue
            try:
                download_file(url, dest)
                if ext == ".hlp" and is_winhelp(dest):
                    print(f"    [skipped] {filename} (Windows HLP)")
                    dest.unlink(missing_ok=True)
                    continue
                collected.append(dest)
                print(f"    ✓ {dest.relative_to(sources_dir)}")
            except Exception as exc:
                print(f"    [error] {exc}")
                failed.append(f"{identifier}/{filename}: {exc}")
            continue

        archive_path = dl_dir / f"ao_{identifier}_{filename}"
        try:
            print(f"    Downloading: {filename}")
            download_file(url, archive_path)
        except Exception as exc:
            print(f"    [error] {exc}")
            failed.append(f"{identifier}/{filename}: {exc}")
            continue

        result = collect_from_archive(
            archive_path,
            base_label,
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
    """Run the Archive.org provider for selected logical products."""
    all_collected: list[Path] = []
    all_failed: list[str] = []

    for product in products_for_source(SOURCE_NAME, product_keys):
        source_query = product.sources[SOURCE_NAME]
        if not source_query.query and not source_query.direct_urls:
            continue

        print(f"[archive.org] {product.label}")
        print(f"  Search: {source_query.search_text}")
        direct_items: list[dict] = []
        for url in source_query.direct_urls:
            identifier = _identifier_from_direct_url(url)
            if not identifier:
                continue
            item = get_item(identifier)
            if item:
                direct_items.append(item)

        time.sleep(1.0)
        items = search_items(source_query.query) if source_query.query else []
        relevant = [item for item in items if is_relevant_item(item, source_query)]
        merged: dict[str, dict] = {}
        for item in [*direct_items, *relevant]:
            identifier = item.get("identifier")
            if isinstance(identifier, str) and identifier:
                merged[identifier] = item
        relevant = list(merged.values())
        print(f"  Found: {len(items)}, relevant: {len(relevant)}")

        for item in relevant:
            try:
                files = process_item(
                    item=item,
                    product=product,
                    source_query=source_query,
                    dl_dir=dl_dir,
                    sources_dir=sources_dir,
                    extractor=extractor,
                    dry_run=dry_run,
                    failed=all_failed,
                )
                all_collected.extend(files)
            except Exception as exc:
                identifier = item.get("identifier", "?")
                print(f"  [error] {identifier}: {exc}")
                all_failed.append(f"{identifier}: {exc}")

    if all_failed:
        print(f"\n  {len(all_failed)} downloads failed:")
        for item in all_failed:
            print(f"    {item}")

    return all_collected
