"""
Archive.org Downloader – Borland/Turbo DOS Help Files

Searches archive.org via JSON API, downloads archives, and extracts help files.
No rate limits, direct HTTPS download.

Usage:
    python3 -m downloader --source archiveorg
    python3 -m downloader --source archiveorg --products tp tc tasm
"""

from __future__ import annotations

import re
import time
import urllib.parse
from pathlib import Path

from .common import (
    DOWNLOAD_DELAY, HELP_EXTENSIONS, collect_help_files, copy_help_files,
    detect_language, download_file, extract_archive, extract_nested,
    fetch_json, fetch_polite, find_7z, is_winhelp, process_archive, require_7z,
)

import tempfile


ARCHIVEORG_SEARCH   = "https://archive.org/advancedsearch.php"
ARCHIVEORG_METADATA = "https://archive.org/metadata"
ARCHIVEORG_DOWNLOAD = "https://archive.org/download"

# Keywords for filtering irrelevant results
BORLAND_KEYWORDS = {
    "borland", "turbo pascal", "turbo c", "turbo assembler", "tasm",
    "turbo basic", "turbo prolog", "turbo debugger",
}

# Ignore these archive.org identifiers (not DOS Borland)
SKIP_IDENTIFIERS = {
    "turbo-pascal-bcd-1xdiskette",   # Atari BCD, nie Borland DOS
}

# Products: key → (search query, label for sources/)
PRODUCTS: dict[str, tuple[str, str]] = {
    "tp": (
        'creator:Borland AND (title:"Turbo Pascal" OR subject:"Turbo Pascal") AND mediatype:software',
        "Borland Turbo Pascal",
    ),
    "tc": (
        'creator:Borland AND (title:"Turbo C" OR title:"Turbo C++") AND mediatype:software',
        "Borland Turbo C",
    ),
    "tasm": (
        'creator:Borland AND (title:"Turbo Assembler" OR title:"TASM") AND mediatype:software',
        "Borland Turbo Assembler",
    ),
    "td": (
        'creator:Borland AND title:"Turbo Debugger" AND mediatype:software',
        "Borland Turbo Debugger",
    ),
    "tbasic": (
        '(creator:Borland OR creator:"Power Basic") AND (title:"Turbo Basic" OR title:"PowerBASIC") AND mediatype:software',
        "Borland Turbo Basic",
    ),
    "tprolog": (
        'creator:Borland AND title:"Turbo Prolog" AND mediatype:software',
        "Borland Turbo Prolog",
    ),
    "bc": (
        # BC++ 2.x–3.x had DOS help; 4.x+ is Windows-only. Exclude C++ Builder (Windows RAD IDE).
        'creator:Borland AND title:"Borland C++" AND mediatype:software NOT title:"Builder"',
        "Borland C++",
    ),
    "bp": (
        'creator:Borland AND title:"Borland Pascal" AND mediatype:software',
        "Borland Pascal",
    ),
    # Special – bundle containing TC + TP + TASM + TD
    "bundle": (
        'identifier:borland-turbo-c-pascal-assembler-debugger-turbo-debugger',
        "Borland Bundle",
    ),
}


# ---------------------------------------------------------------------------
# Scraping archive.org
# ---------------------------------------------------------------------------

def search_items(query: str, rows: int = 50) -> list[dict]:
    """Returns list of archive.org items for the given query."""
    params = urllib.parse.urlencode({
        "q": query,
        "fl[]": "identifier,title,subject,creator",
        "rows": rows,
        "output": "json",
        "page": 1,
    })
    url = f"{ARCHIVEORG_SEARCH}?{params}"
    data = fetch_json(url)
    docs = data.get("response", {}).get("docs", [])
    return [d for d in docs if d.get("identifier") not in SKIP_IDENTIFIERS]


def get_item_files(identifier: str) -> list[dict]:
    """Returns list of files for the given archive.org identifier."""
    url = f"{ARCHIVEORG_METADATA}/{identifier}/files"
    data = fetch_json(url)
    return data.get("result", [])


def is_relevant_item(item: dict, label: str) -> bool:
    """Returns True if item likely contains DOS Borland software (IDE/compiler)."""
    title = (item.get("title") or "").lower()
    # creator can be string or list of strings from archive.org API
    _cr = item.get("creator") or []
    if isinstance(_cr, str):
        _cr = [_cr]
    creator = " ".join(_cr).lower()
    subject_raw = item.get("subject") or []
    if isinstance(subject_raw, str):
        subject_raw = [subject_raw]
    subject = " ".join(subject_raw).lower()
    identifier = (item.get("identifier") or "").lower()
    combined = f"{title} {creator} {subject}"

    # Must have at least one keyword
    if not any(kw in combined for kw in BORLAND_KEYWORDS):
        return False

    # Must be from Borland (creator) – exclude things "written in" Turbo Pascal
    creator_is_borland = any("borland" in c.lower() for c in _cr)

    # If creator is not Borland, title must clearly reference IDE (not a game/demo)
    if not creator_is_borland:
        # Only acceptable if identifier or title contains software version
        ide_keywords = (
            "pascal 7", "pascal 6", "pascal 5", "pascal 4", "pascal 3",
            "turbo c 1", "turbo c 2", "turbo c 3",
            "turbo c++ 1", "turbo c++ 2", "turbo c++ 3",
            "assembler 1", "assembler 2", "assembler 3", "assembler 4",
            "turbo assembler", "tasm", "turbo debugger",
            "debugger 1", "debugger 2", "debugger 3",
            "turbo pascal box", "borland pascal",
        )
        if not any(kw in title or kw in identifier for kw in ide_keywords):
            return False

    # Exclude Atari, C64, Apple, Windows, PC-98 versions
    # Note: we don't exclude "kryoflux" from is_relevant_item – items may have .img
    #       disk images alongside Kryoflux dumps. Kryoflux .zip files are filtered
    #       later in pick_download_files.
    skip = (
        "atari", "c64", "commodore", "apple ii", "amiga", "cp/m", "cpm",
        "disk image dump", "flux dump",
        "for windows", "turbo c for windows", "turbo pascal for windows",
        "turbo debugger for windows", "windows-only",
        "pour windows", "für windows", "for win",
        "pc-98", "pc-9801", "pc98", "9801", "pc-9x",
    )
    if any(s in combined or s in identifier for s in skip):
        return False

    # Exclude C++ Builder (Windows RAD IDE) – no DOS help files
    if "c++ builder" in title or "cppbuilder" in identifier or "cpp-builder" in identifier:
        return False
    if "builder" in title and "borland c++" in title:
        return False

    # Exclude games and demos (files written in Turbo Pascal)
    game_kw = (
        "game", "demo", "shareware game", "go-moku", "chess", "puzzle",
        "vicki", "adventure", "arcade", "tetris", "invaders",
    )
    if any(kw in title or kw in identifier for kw in game_kw):
        return False

    return True


def pick_download_files(files: list[dict], identifier: str) -> list[tuple[str, str]]:
    """
    Selects files for download:
    1. If there are direct .hlp/.tph files → download them
    2. Otherwise download .7z / .zip archives (smallest available)
    Returns list of (fname, download_url).
    """
    archive_exts  = {".7z", ".zip"}
    direct_help   = []
    archives      = []

    for f in files:
        name = f.get("name", "")
        if not name or "/" in name:
            # Subdirectories in archive.org metadata – skip
            continue
        ext  = Path(name).suffix.lower()
        size = int(f.get("size") or 0)
        name_lower = name.lower()

        # Skip Kryoflux flux dumps and other unusable formats
        skip_names = ("kryoflux", ".raw", ".scp", ".ipf", ".mfm")
        if any(s in name_lower for s in skip_names):
            continue

        disk_exts = {".img", ".ima", ".dsk", ".flp"}

        if ext in HELP_EXTENSIONS:
            direct_help.append((name, size))
        elif ext in archive_exts and size > 0:
            archives.append((name, size))
        elif ext in disk_exts and size > 0:
            archives.append((name, size))  # treat disk images like archives

    result = []
    base = f"{ARCHIVEORG_DOWNLOAD}/{identifier}"

    if direct_help:
        for name, _ in direct_help:
            result.append((name, f"{base}/{urllib.parse.quote(name)}"))
    elif archives:
        # Prefer .7z, then .zip, then disk images; pick smallest
        sevenz_archives = [(n, s) for n, s in archives if n.lower().endswith(".7z")]
        zip_archives    = [(n, s) for n, s in archives if n.lower().endswith(".zip")]
        img_archives    = [(n, s) for n, s in archives if Path(n).suffix.lower() in {".img", ".ima", ".dsk", ".flp"}]
        chosen = sevenz_archives or zip_archives or img_archives
        chosen.sort(key=lambda x: x[1])   # smallest first
        # For disk images take max 6 (typical set = 3-6 disks)
        # For zip/7z take max 2 (some items have many variants)
        limit = 6 if chosen is img_archives else 2
        for name, _ in chosen[:limit]:
            result.append((name, f"{base}/{urllib.parse.quote(name)}"))

    return result


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _detect_version(title: str, identifier: str) -> str | None:
    """
    Extracts version number from the title or identifier of an archive.org item.
    E.g. 'Borland Turbo Pascal 6.01 (German)' → '6.01'
         'BL_TurboPascal-7'                   → '7'
    """
    combined = f"{title} {identifier}".lower()

    # Look for patterns: '6.01', '5.5', '7.1', '3.01a', ...
    m = re.search(
        r'\b(?:version\s+|v\.?\s*)?(\d+\.\d+[a-z]?)\b',
        combined,
    )
    if m:
        return m.group(1)

    # Whole numbers after product name: 'pascal 7', 'turbo-c-3', 'BL_Pascal-7'
    m = re.search(
        r'(?:pascal|turbo[- ]?c|assembler|debugger|basic|prolog|c\+\+|borland-c)[- _](\d)\b',
        combined,
    )
    if m:
        return m.group(1)

    return None


# ---------------------------------------------------------------------------
# Processing a single item
# ---------------------------------------------------------------------------

def process_item(
    item: dict,
    label: str,
    dl_dir: Path,
    sources_dir: Path,
    sevenz: str | None,
    dry_run: bool,
    failed: list[str],
) -> list[Path]:
    identifier = item["identifier"]
    title      = item.get("title", identifier)

    print(f"\n  [{identifier}]  {title}")

    files = get_item_files(identifier)
    to_download = pick_download_files(files, identifier)

    if not to_download:
        print("    No suitable files on archive.org.")
        return []

    lang_code  = detect_language(title)
    lang_info  = f" [{lang_code}]" if lang_code else ""
    lang_sfx   = f" ({lang_code})" if lang_code else ""
    ver        = _detect_version(title, identifier)
    ver_sfx    = f" {ver}" if ver else ""
    target_dir = sources_dir / f"{label}{ver_sfx}{lang_sfx}".strip()

    collected: list[Path] = []

    for fname, url in to_download:
        print(f"    file: {fname}{lang_info}")
        if dry_run:
            print(f"      [dry-run] {url}")
            print(f"      [target] {target_dir.relative_to(sources_dir)}")
            continue

        ext = Path(fname).suffix.lower()

        # Direct help files – download straight to target_dir
        if ext in HELP_EXTENSIONS:
            dest = target_dir / fname.upper()
            if dest.exists():
                print(f"    [skipped] {fname} (exists)")
                continue
            try:
                download_file(url, dest)
                # Check if it's a Windows HLP (magic bytes)
                if ext == ".hlp" and is_winhelp(dest):
                    print(f"    [skipped] {fname} (Windows HLP – not Borland THELP)")
                    dest.unlink()
                    continue
                collected.append(dest)
                print(f"    ✓ {dest.relative_to(sources_dir)}")
            except Exception as exc:
                print(f"    [error] {exc}")
                failed.append(f"{identifier}/{fname}: {exc}")
            continue

        # Archive – download and extract
        archive_path = dl_dir / f"ao_{identifier}_{fname}"
        try:
            print(f"    Downloading: {fname}")
            download_file(url, archive_path)
        except Exception as exc:
            print(f"    [chyba] {exc}")
            failed.append(f"{identifier}/{fname}: {exc}")
            continue

        result = process_archive(archive_path, f"{label}{ver_sfx}{lang_sfx}".strip(),
                                 None, sources_dir, sevenz)
        collected.extend(result)
        if not result:
            print("    No help files found.")

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

        query, label = PRODUCTS[key]
        print(f"\n{'='*60}")
        print(f"[archive.org] {label}")
        print("=" * 60)

        time.sleep(1.0)
        items = search_items(query)
        relevant = [it for it in items if is_relevant_item(it, label)]
        print(f"  Found: {len(items)}, relevant: {len(relevant)}")

        for item in relevant:
            try:
                files = process_item(
                    item=item, label=label,
                    dl_dir=dl_dir, sources_dir=sources_dir,
                    sevenz=sevenz, dry_run=dry_run,
                    failed=all_failed,
                )
                all_collected.extend(files)
            except Exception as exc:
                print(f"  [chyba] {item.get('identifier')}: {exc}")
                all_failed.append(f"{item.get('identifier')}: {exc}")

    if all_failed:
        print(f"\n  {len(all_failed)} downloads failed:")
        for f in all_failed:
            print(f"    {f}")

    return all_collected
