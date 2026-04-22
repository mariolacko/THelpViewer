"""HTTP and HTML helpers shared by downloader providers."""

from __future__ import annotations

import html as html_module
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


REQUEST_DELAY = 1.5
DOWNLOAD_DELAY = 3.0

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
    """Fetch one HTML page with retries and optional forced text encoding."""
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
    """Fetch one JSON document."""
    opener = get_opener()
    with opener.open(url, timeout=20) as resp:
        return json.loads(resp.read())


def fetch_polite(url: str, encoding: str | None = None) -> str:
    """Fetch one page after the shared request delay."""
    time.sleep(REQUEST_DELAY)
    return fetch_html(url, encoding=encoding)


def download_file(url: str, dest: Path, retries: int = 3) -> Path:
    """Download one file to disk, skipping already-downloaded targets."""
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
        except urllib.error.HTTPError as exc:
            if tmp.exists():
                tmp.unlink()
            if exc.code == 429:
                wait = int(exc.headers.get("Retry-After", 60))
                print(f"\r    [429] waiting {wait}s (attempt {attempt + 1}/{retries}) …")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            raise RuntimeError(f"Download failed: {url}: {exc}") from exc

    raise RuntimeError(f"Download failed after {retries} attempts: {url}")
