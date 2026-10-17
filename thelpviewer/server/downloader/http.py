"""HTTP and HTML helpers shared by downloader providers."""

from __future__ import annotations

import html as html_module
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from .transport import create_opener, public_url, read_request
from .errors import SourceRateLimited, SourceUnavailable
from .cache import download_cached
from ..processing import report_progress


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
        _opener = create_opener(https_only=False)
        _opener.addheaders = [
            ("User-Agent", USER_AGENT),
            ("Accept", "text/html,application/xhtml+xml,*/*;q=0.9"),
            ("Accept-Language", "en-US,en;q=0.9"),
        ]
    return _opener


def fetch_html(url: str, retries: int = 3, encoding: str | None = None, *, headers=None) -> str:
    """Fetch one HTML page with retries and optional forced text encoding."""
    public_url(url, https_only=False)
    request = urllib.request.Request(url, headers=headers) if headers else url
    data, _url, response_headers = read_request(get_opener(), request, 16 * 1024 * 1024, retries=retries,
        phase="Reading source page", on_status=report_progress)
    match = re.search(r"charset=([^\s;]+)", response_headers.get("Content-Type", ""), re.I)
    return data.decode(encoding or (match.group(1) if match else "utf-8"), errors="replace")


def fetch_json(url: str) -> object:
    """Fetch one JSON document."""
    public_url(url, https_only=False)
    data, _url, _headers = read_request(get_opener(), url, 16 * 1024 * 1024, timeout=20,
        phase="Reading source index", on_status=report_progress)
    return json.loads(data)


def fetch_polite(url: str, encoding: str | None = None) -> str:
    """Fetch one page after the shared request delay."""
    time.sleep(REQUEST_DELAY)
    return fetch_html(url, encoding=encoding)


def download_file(url: str, dest: Path, retries: int = 3, *, headers=None, process=None):
    """Download one file to disk, skipping already-downloaded targets."""
    public_url(url, https_only=False)
    def cached():
        print(f"    [skipped] {dest.name} (exists)")
        report_progress("Using cached archive", dest.name)
    def fetch(staged):
        time.sleep(DOWNLOAD_DELAY)
        request = urllib.request.Request(url, headers=headers) if headers else url
        try:
            read_request(get_opener(), request, 512 * 1024 * 1024, timeout=120, retries=retries,
                retry_after=60, destination=staged,
                on_status=lambda phase: report_progress(phase, dest.name),
                on_progress=lambda received, size: report_progress("Downloading", dest.name, stage="download",
                    received=received, bytes_total=size))
        except SourceRateLimited:
            raise
        except (OSError, urllib.error.URLError) as error:
            raise SourceUnavailable(f"Download failed: {dest.name}: {error}") from error
        report_progress("Downloaded", dest.name, stage="prepare", downloaded_size=staged.stat().st_size)
    return download_cached(dest, 512 * 1024 * 1024, fetch, process=process, on_cached=cached)
