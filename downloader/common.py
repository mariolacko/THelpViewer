"""
Shared utilities for all downloaders: HTTP, archive extraction, help file collection.
"""

from __future__ import annotations

import html as html_module
import http.cookiejar
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HELP_EXTENSIONS = {".hlp", ".tph", ".tch", ".hlx", ".hl6"}
WINHELP_MAGIC   = b"\x3f\x5f\x03\x00"

SKIP_HELP_NAMES = {
    "CALC.HLP", "TUTOR.HLP", "INSTALL.HLP", "UTILS.HLP",
    "DEMOHELP.HLP", "DEMOHELP_BP7.HLP",  # Borland TVHC demo help (FBHF magic, not THELP)
}

LANG_CODES: dict[str, str] = {
    "german":      "DE", "deutsch":    "DE",
    "french":      "FR", "français":   "FR", "francais": "FR",
    "spanish":     "ES", "español":    "ES", "espanol":  "ES",
    "italian":     "IT", "italiano":   "IT",
    "dutch":       "NL", "netherlands":"NL",
    "portuguese":  "PT",
    "czech":       "CZ",
    "polish":      "PL",
    "russian":     "RU",
    "swedish":     "SE",
    "norwegian":   "NO",
    "danish":      "DK",
    "finnish":     "FI",
    "hungarian":   "HU",
}

REQUEST_DELAY  = 1.5
DOWNLOAD_DELAY = 3.0

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

class AttrParser(HTMLParser):
    """Collects <a> tags with href, title, and text content."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self._buf: list[str] = []
        self._cur: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._cur = {k: (v or "") for k, v in attrs}
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._cur is not None:
            self._cur["_text"] = html_module.unescape("".join(self._buf)).strip()
            self.anchors.append(self._cur)
            self._cur = None

    def handle_data(self, data: str) -> None:
        if self._cur is not None:
            self._buf.append(data)


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


def fetch_html(url: str, retries: int = 3, encoding: str | None = None) -> str:
    opener = get_opener()
    for attempt in range(retries):
        try:
            with opener.open(url, timeout=30) as resp:
                ct = resp.headers.get("Content-Type", "")
                if encoding:
                    charset = encoding
                else:
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


def fetch_json(url: str) -> object:
    import json
    opener = get_opener()
    with opener.open(url, timeout=20) as resp:
        return json.loads(resp.read())


def fetch_polite(url: str, encoding: str | None = None) -> str:
    time.sleep(REQUEST_DELAY)
    return fetch_html(url, encoding=encoding)


def download_file(url: str, dest: Path, retries: int = 3) -> Path:
    """Download file. Skip if exists. Retry on 429."""
    if dest.exists():
        print(f"    [skipped] {dest.name} (exists)")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    time.sleep(DOWNLOAD_DELAY)
    opener = get_opener()

    for attempt in range(retries):
        try:
            with opener.open(url, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                with open(tmp, "wb") as fh:
                    while chunk := resp.read(65536):
                        fh.write(chunk)
                        done += len(chunk)
                        if total:
                            print(f"\r    {dest.name}: {done*100//total:3d}%"
                                  f" ({done//1024}kB/{total//1024}kB)",
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
                print(f"\r    [429] waiting {wait}s (attempt {attempt+1}/{retries}) …")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            raise RuntimeError(f"Download failed: {url}: {exc}") from exc

    raise RuntimeError(f"Download failed after {retries} attempts: {url}")


# ---------------------------------------------------------------------------
# 7z
# ---------------------------------------------------------------------------

def find_7z() -> str | None:
    for name in ("7z", "7za", "7zz", "7zr"):
        if shutil.which(name):
            return name
    return None


def require_7z(dry_run: bool = False) -> str | None:
    sevenz = find_7z()
    if sevenz:
        return sevenz
    msg = (
        "7z is not installed – cannot extract .7z archives without it.\n"
        "  macOS:  brew install sevenzip\n"
        "  Linux:  sudo apt install p7zip-full\n"
    )
    if dry_run:
        print(f"WARNING: {msg}")
        return None
    sys.exit(f"ERROR: {msg}")


def _run_7z(archive: Path, dest: Path, sevenz: str) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sevenz, "x", str(archive), f"-o{dest}", "-y", "-bd"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"    [7z error] {result.stderr[:300]}")
        return False
    return True


def extract_archive(archive: Path, dest: Path, sevenz: str | None) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(dest)
            return True
        except zipfile.BadZipFile as exc:
            print(f"    [zipfile error] {exc}")
    if sevenz:
        return _run_7z(archive, dest, sevenz)
    print(f"    [error] Cannot extract {archive.name}")
    return False


def extract_nested(work_dir: Path, sevenz: str | None, depth: int = 0) -> None:
    """
    Recursive extraction: disk image → ZIP/7z inside → help files.
    archive.7z → disk01.img → TURBO.ZIP → TURBO.TPH
    """
    if not sevenz or depth > 3:
        return

    image_exts = {".img", ".ima", ".dsk", ".iso", ".flp", ".vfd"}

    for f in sorted(work_dir.rglob("*")):
        if not (f.is_file() and f.suffix.lower() in image_exts):
            continue
        sub = f.parent / (f.stem + "_extracted")
        if sub.exists():
            continue
        print(f"    {'  '*depth}Extracting image: {f.name} …")
        if _run_7z(f, sub, sevenz):
            extract_nested(sub, sevenz, depth + 1)

    for f in sorted(work_dir.rglob("*")):
        if not (f.is_file() and f.suffix.lower() == ".zip"):
            continue
        if f.parent == work_dir:
            continue
        sub = f.parent / (f.stem + "_extracted")
        if sub.exists():
            continue
        print(f"    {'  '*depth}Extracting: {f.name} …")
        ok = False
        try:
            with zipfile.ZipFile(f) as zf:
                zf.extractall(sub)
            ok = True
        except Exception:
            if sevenz:
                ok = _run_7z(f, sub, sevenz)
        if ok:
            extract_nested(sub, sevenz, depth + 1)


# ---------------------------------------------------------------------------
# Help files
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str | None:
    t = text.lower()
    for kw, code in LANG_CODES.items():
        if re.search(r"[\[\(\s_]" + re.escape(kw) + r"[\]\)\s_\.]", t):
            return code
    return None


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
            print(f"    [skipped] {p.name} (accessory)")
            continue
        if p.suffix.lower() == ".hlp" and is_winhelp(p):
            print(f"    [skipped] {p.name} (Windows HLP)")
            continue
        found.append(p)
    return found


def copy_help_files(
    files: list[Path],
    target_dir: Path,
    sources_dir: Path,
) -> list[Path]:
    copied = []
    for src in files:
        dest = target_dir / src.name.upper()
        if dest.exists():
            print(f"    [skipped] {dest.name} (exists)")
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"    ✓ {dest.relative_to(sources_dir)}")
        copied.append(dest)
    return copied


def process_archive(
    archive: Path,
    label: str,
    lang_code: str | None,
    sources_dir: Path,
    sevenz: str | None,
) -> list[Path]:
    """Extract archive, find help files, copy to sources/."""
    import tempfile
    lang_suffix = f" ({lang_code})" if lang_code else ""
    target_dir = sources_dir / f"{label}{lang_suffix}".strip()

    with tempfile.TemporaryDirectory(prefix="dlhelp_") as tmp:
        tmp_path = Path(tmp)
        if not extract_archive(archive, tmp_path, sevenz):
            return []
        extract_nested(tmp_path, sevenz)
        files = collect_help_files(tmp_path)
        if not files:
            return []
        return copy_help_files(files, target_dir, sources_dir)
