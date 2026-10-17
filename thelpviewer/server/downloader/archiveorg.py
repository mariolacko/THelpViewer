"""Archive.org provider for the unified downloader."""

from __future__ import annotations

import re
import time
import urllib.parse
from pathlib import Path, PurePosixPath

from ..processing import UnsafeContentError
from .errors import SourceRateLimited
from .catalog import ProductSpec, SourceQuery, products_for_source
from ..converter.selection import version_selected
from .cache import download_filename
from ..converter.sources import HELP_EXTENSIONS, detect_language
from ..converter.ingest import HelpInput
from .http import fetch_json
from ..processing import report_progress


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
    data = fetch_json(f"{ARCHIVEORG_METADATA}/{urllib.parse.quote(identifier, safe='')}")
    item = data.get("metadata", {})
    return item if item.get("identifier") == identifier else None


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
        path = PurePosixPath(name)
        if not name or path.is_absolute() or "\\" in name or any(part in {".", ".."} for part in name.split("/")):
            continue
        ext = Path(name).suffix.lower()
        size = int(item.get("size") or 0)
        lowered = name.lower()

        if lowered.endswith("_jp2.zip") or any(token in lowered for token in ("kryoflux", ".raw", ".scp", ".ipf", ".mfm")):
            continue

        if ext in HELP_EXTENSIONS:
            direct_help.append((name, size))
            continue
        if ext in archive_exts or ext in {".iso", ".img", ".ima", ".dsk", ".flp"}:
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
    archives_iso = [(name, size) for name, size in archives if name.lower().endswith(".iso")]
    archives_img = [
        (name, size) for name, size in archives if Path(name).suffix.lower() in {".img", ".ima", ".dsk", ".flp"}
    ]
    chosen = archives_7z or archives_zip or archives_rar or archives_iso or archives_img
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
    process,
    dry_run: bool,
    failed: list[str],
    *,
    complete=None,
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
    version_suffix = f" {version}" if version and not product.label.casefold().endswith(f" {version}".casefold()) else ""
    base_label = f"{product.label}{version_suffix}".strip()
    collected: list[Path] = []

    for filename, url in to_download:
        if complete and complete():
            break
        print(f"    file: {filename}")
        if dry_run:
            print(f"      [dry-run] {url}")
            print(f"      [search]   {source_query.search_text}")
            continue

        direct = Path(filename).suffix.lower() in HELP_EXTENSIONS
        cache = dl_dir / f"ao_{identifier}" / filename if direct else dl_dir / f"ao_{identifier}_{download_filename(filename)}"
        collection = (product.collection_prefixes[0] if source_query.archive_members and product.collection_prefixes
                      else f"{base_label}{f' ({lang_code})' if lang_code and direct else ''}")
        try:
            collected.extend(process(HelpInput(cache, collection, members=source_query.archive_members,
                language=None if direct else lang_code, direct=direct, allow_partial=True), url=url))
        except (SourceRateLimited, UnsafeContentError):
            raise
        except Exception as exc:
            failed.append(f"{identifier}/{filename}: {exc}")

    return collected


def run(
    product_keys: list[str],
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Run the Archive.org provider for selected logical products."""
    all_collected: list[Path] = []
    all_failed: list[str] = []
    seen_items: set[tuple[str, str, tuple[str, ...]]] = set()

    for product in products_for_source(SOURCE_NAME, product_keys):
        if complete and complete():
            break
        source_query = product.sources[SOURCE_NAME]
        if not source_query.query and not source_query.direct_urls:
            continue

        print(f"[archive.org] {product.label}")
        print(f"  Search: {source_query.search_text}")
        collected_query = False
        def candidates():
            # A pinned item must not depend on a working advanced-search API.
            for url in source_query.direct_urls:
                if complete and complete():
                    return
                identifier = _identifier_from_direct_url(url)
                if not identifier or (product.key, identifier, source_query.archive_members) in seen_items:
                    continue
                try:
                    item = get_item(identifier)
                except (SourceRateLimited, UnsafeContentError):
                    raise
                except Exception as error:
                    all_failed.append(f"{identifier}: {error}")
                    continue
                if item:
                    yield item
            if source_query.query and not collected_query and not (complete and complete()):
                time.sleep(1.0)
                items = search_items(source_query.query)
                relevant = [item for item in items if is_relevant_item(item, source_query)]
                print(f"  Found: {len(items)}, relevant: {len(relevant)}")
                yield from relevant

        for item in candidates():
            if complete and complete():
                break
            if not (product.default_version and version_selected(product.key, product.default_version)) and not version_selected(
                    product.key, str(item.get("title", "")) + " " + item["identifier"]):
                continue
            identity = (product.key, item["identifier"], source_query.archive_members)
            if identity in seen_items:
                continue
            seen_items.add(identity)
            try:
                files = process_item(
                    item=item,
                    product=product,
                    source_query=source_query,
                    dl_dir=dl_dir,
                    process=process,
                    dry_run=dry_run,
                    failed=all_failed,
                    complete=complete,
                )
                all_collected.extend(files)
                if files or dry_run:
                    collected_query = True
            except SourceRateLimited:
                raise
            except UnsafeContentError:
                raise
            except Exception as exc:
                identifier = item.get("identifier", "?")
                print(f"  [error] {identifier}: {exc}")
                all_failed.append(f"{identifier}: {exc}")

    if all_failed:
        print(f"\n  {len(all_failed)} downloads failed:")
        for item in all_failed:
            print(f"    {item}")
            report_progress("Source warning", warning=item)

    return all_collected
