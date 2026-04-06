#!/usr/bin/env python3
"""
WinWorldPC Downloader – Borland DOS Help Files
===============================================

Scrapes Turbo Pascal, Turbo C, and Turbo Assembler pages on WinWorldPC,
downloads archives (.7z / .zip), extracts them (including floppy disk images)
and copies help files (.HLP, .TPH, .HLX, .HL6) to the sources/ directory.

No external dependencies – only Python standard library + external 7z.

Requirements:
    7z must be available in PATH
    macOS: brew install sevenzip
    Linux: sudo apt install p7zip-full

Usage:
    python3 downloader/winworld_downloader.py
    python3 downloader/winworld_downloader.py --dry-run
    python3 downloader/winworld_downloader.py --products tp tc tasm
    python3 downloader/winworld_downloader.py --out-dir /custom/path
"""

from __future__ import annotations

import argparse
import html as html_module
import http.cookiejar
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WINWORLD_BASE = "https://winworldpc.com"

PRODUCTS = {
    # Turbo series
    "tp":     ("turbo-pascal",    "Borland Turbo Pascal"),
    "tc":     ("turbo-c",         "Borland Turbo C"),
    "tasm":   ("turbo-assembler", "Borland Turbo Assembler"),
    "tbasic": ("turbo-basic",     "Borland Turbo Basic"),
    "tprolog":("turbo-prolog",    "Borland Turbo Prolog"),
    # Borland series (successors of Turbo products)
    "bc":     ("borland-c",       "Borland C++"),
    "bp":     ("borland-pascal",  "Borland Pascal"),
    # Other Borland DOS tools with help files
    "sk":     ("sidekick",        "Borland Sidekick"),
}

HELP_EXTENSIONS = {".hlp", ".tph", ".tch", ".hlx", ".hl6"}

# WinHelp 3.x/4.x magic bytes – tieto nechceme
WINHELP_MAGIC = b"\x3f\x5f\x03\x00"

# Language keywords in filenames → ISO 639-1 codes
LANG_CODES: dict[str, str] = {
    "german":     "DE",
    "deutsch":    "DE",
    "french":     "FR",
    "français":   "FR",
    "francais":   "FR",
    "spanish":    "ES",
    "español":    "ES",
    "espanol":    "ES",
    "italian":    "IT",
    "italiano":   "IT",
    "dutch":      "NL",
    "netherlands": "NL",
    "portuguese": "PT",
    "czech":      "CZ",
    "polish":     "PL",
    "russian":    "RU",
    "swedish":    "SE",
    "norwegian":  "NO",
    "danish":     "DK",
    "finnish":    "FI",
    "hungarian":  "HU",
}

REQUEST_DELAY = 2.5   # seconds between regular HTTP requests
DOWNLOAD_DELAY = 4.0  # seconds between file downloads (WinWorldPC has daily limit)

# Help files we don't want – IDE accessories, not language help
SKIP_HELP_NAMES = {
    "CALC.HLP",    # Borland Calculator accessory
    "TUTOR.HLP",   # Tutorial (not main help)
    "INSTALL.HLP", # Installation helper
    "UTILS.HLP",   # Utilities
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# UUID pattern pre WinWorldPC
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Minimal HTML parser
# ---------------------------------------------------------------------------

class AttrParser(HTMLParser):
    """Collects <a> tags with their href and title attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self._text_buf: list[str] = []
        self._cur: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            d = {k: (v or "") for k, v in attrs}
            self._cur = d
            self._text_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._cur is not None:
            self._cur["_text"] = html_module.unescape("".join(self._text_buf)).strip()
            self.anchors.append(self._cur)
            self._cur = None

    def handle_data(self, data: str) -> None:
        if self._cur is not None:
            self._text_buf.append(data)


def parse_anchors(html_text: str) -> list[dict[str, str]]:
    p = AttrParser()
    p.feed(html_text)
    return p.anchors


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

_opener: urllib.request.OpenerDirector | None = None


def get_opener() -> urllib.request.OpenerDirector:
    global _opener
    if _opener is None:
        jar = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar),
            urllib.request.HTTPRedirectHandler(),
        )
        _opener.addheaders = [
            ("User-Agent", USER_AGENT),
            ("Accept", "text/html,application/xhtml+xml,*/*;q=0.9"),
            ("Accept-Language", "en-US,en;q=0.9"),
        ]
    return _opener


def fetch_html(url: str, retries: int = 3) -> str:
    opener = get_opener()
    for attempt in range(retries):
        try:
            with opener.open(url, timeout=30) as resp:
                ct = resp.headers.get("Content-Type", "")
                m = re.search(r"charset=([^\s;]+)", ct, re.I)
                charset = m.group(1) if m else "utf-8"
                return resp.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = int(exc.headers.get("Retry-After", 30))
                print(f"  [429] waiting {wait}s …")
                time.sleep(wait)
                continue
            if attempt == retries - 1:
                raise
            time.sleep(5)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5)
    raise RuntimeError(f"fetch_html failed: {url}")


def fetch_polite(url: str) -> str:
    time.sleep(REQUEST_DELAY)
    return fetch_html(url)


def _is_429_error(exc: Exception) -> bool:
    return "429" in str(exc) or (
        isinstance(exc, urllib.error.HTTPError) and exc.code == 429
    )


def download_file(url: str, dest: Path, retries: int = 3) -> Path:
    """Download file (skip if exists). Retry on 429."""
    if dest.exists():
        print(f"    [skipped] {dest.name}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    time.sleep(DOWNLOAD_DELAY)
    opener = get_opener()

    for attempt in range(retries):
        try:
            with opener.open(url, timeout=120) as resp:
                total_raw = resp.headers.get("Content-Length")
                total = int(total_raw) if total_raw else 0
                done = 0
                with open(tmp, "wb") as fh:
                    while chunk := resp.read(65536):
                        fh.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = done * 100 // total
                            print(f"\r    {dest.name}: {pct:3d}% ({done//1024}kB/{total//1024}kB)",
                                  end="", flush=True)
                if total:
                    print()
            tmp.rename(dest)
            return dest
        except urllib.error.HTTPError as exc:
            if tmp.exists():
                tmp.unlink()
            if exc.code == 429:
                wait = int(exc.headers.get("Retry-After", 60))
                print(f"\r    [429] WinWorldPC daily limit – waiting {wait}s before attempt {attempt+1}/{retries} …")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Download failed ({url}): HTTP {exc.code}") from exc
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            raise RuntimeError(f"Download failed ({url}): {exc}") from exc

    raise RuntimeError(f"Download failed after {retries} attempts: {url}")


# ---------------------------------------------------------------------------
# Scraping – three levels
# ---------------------------------------------------------------------------

# 1) List of versions from the product page
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
        name_lower = name.lower()
        # Exclude versions for other platforms
        skip_kw = ("windows", "os/2", "os2", "win32", "winnt", "log in",
                   "(win)", "(mac)", "macintosh", "for mac")
        if any(x in name_lower for x in skip_kw):
            print(f"  [skipped] {name!r}")
            continue

        versions.append((name, full))
        print(f"  verzia: {name}")

    return versions


# 2) List of download UUIDs + filenames from the version page
def get_file_records(version_url: str) -> list[tuple[str, str]]:
    """
    Returns list of (filename, download_page_url).
    The version page has rows like:
        <a href="/download/<uuid>" title="Filename.7z">
    """
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

        title = a.get("title", "")
        fname = title if title else href.split("/")[-1]
        records.append((fname, full))
        print(f"    file: {fname}")

    return records


# 3) All download servers from the /download/<uuid> page
def get_server_urls(download_page_url: str) -> list[tuple[str, str]]:
    """
    Returns list of (server_name, url) for all available servers.
    Links like: /download/<uuid>/from/<server-uuid>
    """
    html_text = fetch_polite(download_page_url)
    servers: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a in parse_anchors(html_text):
        href = a.get("href", "")
        if re.match(r"^/download/[0-9a-f\-]{36}/from/[0-9a-f\-]{36}$", href, re.I):
            full = urllib.parse.urljoin(WINWORLD_BASE, href)
            if full not in seen:
                seen.add(full)
                name = a.get("_text", "").strip() or href.split("/")[-1]
                servers.append((name, full))

    return servers


# ---------------------------------------------------------------------------
# Extrakcia
# ---------------------------------------------------------------------------

def detect_language(fname: str) -> str | None:
    """Returns ISO language code if a language keyword is found in the filename, else None (=English)."""
    fname_lower = fname.lower()
    for keyword, code in LANG_CODES.items():
        # Match e.g. [German], (German), _German_, "german" bounded by non-letter chars
        if re.search(r"[\[\(\_\s]" + re.escape(keyword) + r"[\]\)\_\s\.]", fname_lower):
            return code
    return None


def find_7z() -> str | None:
    for name in ("7z", "7za", "7zz", "7zr"):
        if shutil.which(name):
            return name
    return None


def require_7z(dry_run: bool) -> str | None:
    """
    Find 7z. In dry-run mode just warn; in normal mode exit the program
    if 7z is missing (can't extract archives without it).
    """
    sevenz = find_7z()
    if sevenz:
        return sevenz

    msg = (
        "7z is not installed – cannot extract .7z archives without it.\n"
        "\n"
        "  macOS:  brew install sevenzip\n"
        "  Linux:  sudo apt install p7zip-full\n"
        "           sudo dnf install p7zip p7zip-plugins\n"
    )
    if dry_run:
        print(f"UPOZORNENIE: {msg}")
        return None
    sys.exit(f"CHYBA: {msg}")


def extract_archive(archive: Path, dest: Path, sevenz: str | None) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(dest)
            return True
        except zipfile.BadZipFile as exc:
            print(f"    [zipfile chyba] {exc}")
    if sevenz:
        return _run_7z(archive, dest, sevenz)
    print(f"    [error] Cannot extract {archive.name}")
    return False


def _run_7z(archive: Path, dest: Path, sevenz: str) -> bool:
    result = subprocess.run(
        [sevenz, "x", str(archive), f"-o{dest}", "-y", "-bd"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"    [7z chyba] {result.stderr[:400]}")
        return False
    return True


def extract_nested(work_dir: Path, sevenz: str | None, depth: int = 0) -> None:
    """
    Recursive layer extraction: disk image → ZIP/7z inside → help files.

    Typical Borland archive structure from WinWorldPC:
      archive.7z  →  disk01.img  →  TURBO.ZIP   →  TURBO.TPH
                                     TVISION.ZIP  →  TVISION.TPH
                                     OWL.ZIP      →  OWL.TPH
                                     WINDOWS.ZIP  →  WINDOWS.TPH
    """
    if not sevenz or depth > 3:
        return

    image_exts = {".img", ".ima", ".dsk", ".iso", ".flp", ".vfd"}

    # 1) Obrazy diskiet
    for f in sorted(work_dir.rglob("*")):
        if not (f.is_file() and f.suffix.lower() in image_exts):
            continue
        sub = f.parent / (f.stem + "_extracted")
        if sub.exists():
            continue
        print(f"    {'  ' * depth}Extrahujem obraz: {f.name} …")
        if _run_7z(f, sub, sevenz):
            extract_nested(sub, sevenz, depth + 1)

    # 2) ZIP archives nested in subdirectories (not directly in root work_dir –
    #    that's the whole archive, not nested files)
    for f in sorted(work_dir.rglob("*")):
        if not (f.is_file() and f.suffix.lower() == ".zip"):
            continue
        if f.parent == work_dir:
            continue   # root ZIP = whole archive, don't copy
        sub = f.parent / (f.stem + "_extracted")
        if sub.exists():
            continue
        print(f"    {'  ' * depth}Extrahujem: {f.name} …")
        ok = False
        try:
            import zipfile as _zf
            with _zf.ZipFile(f) as zf:
                zf.extractall(sub)
            ok = True
        except Exception:
            ok = _run_7z(f, sub, sevenz)
        if ok:
            extract_nested(sub, sevenz, depth + 1)


def extract_disk_images(work_dir: Path, sevenz: str | None) -> None:
    """Alias for extract_nested – kept for compatibility."""
    extract_nested(work_dir, sevenz)


# ---------------------------------------------------------------------------
# Collecting help files
# ---------------------------------------------------------------------------

def is_winhelp(path: Path) -> bool:
    try:
        return path.read_bytes()[:4] == WINHELP_MAGIC
    except OSError:
        return False


def collect_help_files(work_dir: Path) -> list[Path]:
    found = []
    for p in sorted(work_dir.rglob("*")):
        if not (p.is_file() and p.suffix.lower() in HELP_EXTENSIONS):
            continue
        if p.name.upper() in SKIP_HELP_NAMES:
            print(f"    [skipped] {p.name} (accessory, not language help)")
            continue
        if p.suffix.lower() == ".hlp" and is_winhelp(p):
            print(f"    [skipped] {p.name} (Windows HLP)")
            continue
        found.append(p)
    return found


# ---------------------------------------------------------------------------
# Spracovanie jednej verzie
# ---------------------------------------------------------------------------

def process_version(
    version_name: str,
    version_url: str,
    label: str,
    dl_dir: Path,
    sources_dir: Path,
    sevenz: str | None,
    dry_run: bool,
) -> list[Path]:
    print(f"\n  --- {version_name} ---")

    records = get_file_records(version_url)
    if not records:
        print("    No download records.")
        return []

    safe_v = re.sub(r"[^\w\s\-.]", "", version_name).strip()
    target_dir = sources_dir / f"{label} {safe_v}".strip()
    collected: list[Path] = []

    for fname, dl_page_url in records:
        fname_lower = fname.lower()
        # Skip manuals and CP/M / Mac / Windows file variants
        if "manual" in fname_lower:
            print(f"    [skipped] {fname} (manual)")
            continue
        skip_file_kw = (
            # Other platforms
            "for cpm", "for cp/m", "for macintosh", "for mac",
            "for microsoft windows", "for windows",
            # CD-ROM / ISO – too large (hundreds of MB), floppy versions contain the same help files
            "(cd)", "(iso)", " iso", "_iso",
            # Patch disks – don't contain complete help files
            "patch disk",
        )
        if any(x in fname_lower for x in skip_file_kw):
            reason = "nie DOS" if any(x in fname_lower for x in ("for cpm", "for cp/m", "for macintosh", "for mac", "for microsoft windows", "for windows")) else "CD/ISO/patch"
            print(f"    [skipped] {fname} ({reason})")
            continue

        # Detect language from filename and select target directory accordingly
        lang_code = detect_language(fname)
        lang_suffix = f" ({lang_code})" if lang_code else ""
        file_target_dir = sources_dir / f"{label} {safe_v}{lang_suffix}".strip()

        lang_info = f" [{lang_code}]" if lang_code else ""
        print(f"    Looking for servers: {fname}{lang_info} …")
        if dry_run:
            print(f"      [dry-run] {dl_page_url}")
            print(f"      [target] {file_target_dir.relative_to(sources_dir)}")
            continue

        servers = get_server_urls(dl_page_url)
        if not servers:
            print(f"      [error] No servers found for {fname}")
            continue
        for sname, surl in servers:
            print(f"      server: {sname!r}")

        safe_fname = re.sub(r"[^\w\-. ]", "_", fname).strip() or "archive"
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
                    print(f"      [429] {sname} exhausted – trying next server …")
                    continue
                print(f"    [chyba] {exc}")
                break

        if not downloaded:
            print(f"    [error] All servers failed for {fname}")
            continue

        with tempfile.TemporaryDirectory(prefix="winworld_") as tmp:
            tmp_path = Path(tmp)
            print(f"    Extracting …")
            if not extract_archive(archive_path, tmp_path, sevenz):
                continue

            extract_disk_images(tmp_path, sevenz)

            files = collect_help_files(tmp_path)
            if not files:
                print("    No help files found.")
                continue

            for src in files:
                dest = file_target_dir / src.name.upper()
                if dest.exists():
                    print(f"    [skipped] {dest.name}")
                    continue
                file_target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                rel = dest.relative_to(sources_dir)
                print(f"    ✓ {rel}")
                collected.append(dest)

    return collected


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def run(product_keys: list[str], sources_dir: Path, dl_dir: Path, dry_run: bool) -> None:
    sevenz = require_7z(dry_run)

    all_collected: list[Path] = []

    for key in product_keys:
        slug, label = PRODUCTS[key]
        print(f"\n{'='*60}")
        print(f"Produkt: {label}")
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
                )
                all_collected.extend(files)
            except Exception as exc:
                print(f"  [chyba] {version_name}: {exc}")

    print(f"\n{'='*60}")
    if dry_run:
        print("DRY-RUN – no files were downloaded.")
    else:
        print(f"Total help files collected: {len(all_collected)}")
        for p in all_collected:
            print(f"  {p.relative_to(sources_dir)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    # Line-buffered output even when stdout is not a terminal (pipe, file, background task)
    sys.stdout.reconfigure(line_buffering=True)

    project_root = Path(__file__).resolve().parents[1]

    product_help = "  ".join(f"{k}={v[1]}" for k, v in PRODUCTS.items())
    parser = argparse.ArgumentParser(
        description="Download Borland/Turbo DOS help files from WinWorldPC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available products:\n  {product_help}",
    )
    parser.add_argument(
        "--products", nargs="+", choices=list(PRODUCTS), default=list(PRODUCTS),
        metavar="PRODUCT",
        help=f"Products to download (default: all). Options: {', '.join(PRODUCTS)}",
    )
    parser.add_argument(
        "--out-dir", default=str(project_root / "sources"),
        help="Target directory (default: sources/)",
    )
    parser.add_argument(
        "--dl-dir", default=str(project_root / "downloads"),
        help="Directory for archives (default: downloads/)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only print what would happen.",
    )

    args = parser.parse_args()
    sources_dir = Path(args.out_dir)
    dl_dir = Path(args.dl_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory:   {sources_dir}")
    print(f"Download directory: {dl_dir}")
    print(f"Products:           {', '.join(args.products)}")
    if args.dry_run:
        print("Mode:               DRY-RUN")

    run(product_keys=args.products, sources_dir=sources_dir, dl_dir=dl_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
