"""HTTP and HTML helpers shared by downloader providers."""

from __future__ import annotations

import html as html_module
import json
import re
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from .transport import create_opener, download_chunks, public_url


_progress = ContextVar("download_progress", default=None)


@contextmanager
def observe_downloads(callback):
    """Per-task progress, without redirecting process-wide stdout."""
    token = _progress.set(callback)
    try:
        yield
    finally:
        _progress.reset(token)


def _notify(url, received, total):
    callback = _progress.get()
    if callback:
        callback({"phase": "Downloading", "file": Path(urlparse(url).path).name,
                  "received": received, "bytes_total": total})


REQUEST_DELAY = 1.5
DOWNLOAD_DELAY = 3.0
RETRY_DELAY = 5.0
MAX_RETRY_AFTER = 300

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class AttrParser(HTMLParser):
    """Collect simple anchor metadata from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self._buf: list[str] = []
        self._cur: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._cur = {key: (value or "") for key, value in attrs}
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
    """Return all parsed ``<a>`` elements from one HTML document."""
    parser = AttrParser()
    parser.feed(html_text)
    return parser.anchors


_opener: urllib.request.OpenerDirector | None = None


def get_opener() -> urllib.request.OpenerDirector:
    """Return a cached urllib opener with cookies and browser-like headers."""
    global _opener
    if _opener is None:
        _opener = create_opener(https_only=False)
        _opener.addheaders = [
            ("User-Agent", USER_AGENT),
            ("Accept", "text/html,application/xhtml+xml,*/*;q=0.9"),
            ("Accept-Language", "en-US,en;q=0.9"),
        ]
    return _opener


def _retry_delay(headers: object, default: int) -> int:
    """Return a bounded numeric Retry-After delay."""
    try:
        value = int(getattr(headers, "get")("Retry-After", default))
    except (AttributeError, TypeError, ValueError):
        value = default
    return min(max(value, 0), MAX_RETRY_AFTER)


def fetch_html(url: str, retries: int = 3, encoding: str | None = None) -> str:
    """Fetch one HTML page with retries and optional forced text encoding."""
    public_url(url, https_only=False)
    opener = get_opener()
    for attempt in range(retries):
        try:
            with opener.open(url, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if encoding:
                    charset = encoding
                else:
                    match = re.search(r"charset=([^\s;]+)", content_type, re.I)
                    charset = match.group(1) if match else "utf-8"
                return b"".join(download_chunks(resp, 16 * 1024 * 1024)).decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = _retry_delay(exc.headers, 30)
                print(f"  [429] waiting {wait}s …")
                time.sleep(wait)
                continue
            if attempt == retries - 1:
                raise
            time.sleep(RETRY_DELAY)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(RETRY_DELAY)
    raise RuntimeError(f"fetch_html failed: {url}")


def fetch_json(url: str) -> object:
    """Fetch one JSON document."""
    public_url(url, https_only=False)
    opener = get_opener()
    with opener.open(url, timeout=20) as resp:
        return json.loads(b"".join(download_chunks(resp, 16 * 1024 * 1024)))


def fetch_polite(url: str, encoding: str | None = None) -> str:
    """Fetch one page after the shared request delay."""
    time.sleep(REQUEST_DELAY)
    return fetch_html(url, encoding=encoding)


def download_file(url: str, dest: Path, retries: int = 3) -> Path:
    """Download one file to disk, skipping already-downloaded targets."""
    public_url(url, https_only=False)
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
                with tmp.open("wb") as fh:
                    for chunk in download_chunks(resp, 512 * 1024 * 1024,
                                                 lambda received, size: _notify(url, received, size)):
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
        except urllib.error.HTTPError as exc:
            if tmp.exists():
                tmp.unlink()
            if exc.code == 429:
                wait = _retry_delay(exc.headers, 60)
                print(f"\r    [429] waiting {wait}s (attempt {attempt + 1}/{retries}) …")
                time.sleep(wait)
                continue
            if 500 <= exc.code < 600 and attempt < retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(f"Download failed: {url}: {exc}") from exc

    raise RuntimeError(f"Download failed after {retries} attempts: {url}")
