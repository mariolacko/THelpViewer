import io
from urllib.parse import parse_qs

import pytest

from thelpviewer.server.dos_sources import fetch_dos_source
from thelpviewer.downloader.transport import _HTTPSRedirect, _PublicHTTPSConnection
from urllib.request import Request
from types import SimpleNamespace


class DownloadResponse(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url
        self.headers = {"Content-Length": str(len(data))}


def test_generic_dos_html_forms_keep_fields_submit_button_and_progress(monkeypatch):
    url = "https://games.test/game"
    contents = bytes(70000)
    pages = [b'<form id="download" method="post"><input type="hidden" name="id" value="42"><button name="d">Download</button></form>',
             b'<form class="file" method="post" action="/archive"><input type="hidden" name="token" value="fresh"><button name="get">Download</button></form>',
             contents]
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return DownloadResponse(pages[len(requests) - 1], request.full_url)
    monkeypatch.setattr("thelpviewer.downloader.transport.build_opener", lambda *args: Opener())
    progress = []
    source = {"url": url, "download_forms": ["form#download", "form.file"]}
    assert fetch_dos_source(source, 100000, lambda *args: progress.append(args)) == contents
    assert requests[0].data is None
    assert parse_qs(requests[1].data.decode(), keep_blank_values=True) == {"id": ["42"], "d": [""]}
    assert requests[2].full_url == "https://games.test/archive"
    assert parse_qs(requests[2].data.decode(), keep_blank_values=True) == {"token": ["fresh"], "get": [""]}
    assert progress[-1] == (70000, 70000)


def test_download_form_cannot_downgrade_to_http(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            return DownloadResponse(b'<form method="post" action="http://games.test/archive"></form>', request.full_url)
    monkeypatch.setattr("thelpviewer.downloader.transport.build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="HTTPS"):
        fetch_dos_source({"url": "https://games.test/game", "download_forms": ["form"]}, 10000)


def test_dos_source_byte_limit_applies_to_form_downloads(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            return DownloadResponse(bytes(1001), request.full_url)
    monkeypatch.setattr("thelpviewer.downloader.transport.build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="size limit"):
        fetch_dos_source({"url": "https://games.test/game", "download_forms": ["form"]}, 1000)


def test_direct_download_and_cross_host_forms_work_without_host_configuration(monkeypatch):
    urls = []
    class Opener:
        def open(self, request, timeout):
            urls.append(request.full_url)
            data = b'<form method="post" action="https://cdn.test/archive"></form>' if len(urls) == 1 else b"archive"
            return DownloadResponse(data, request.full_url)
    monkeypatch.setattr("thelpviewer.downloader.transport.build_opener", lambda *args: Opener())
    assert fetch_dos_source({"url": "https://games.test/game", "download_forms": ["form"]}, 10000) == b"archive"
    assert urls == ["https://games.test/game", "https://cdn.test/archive"]
    urls.clear()
    assert fetch_dos_source({"url": "https://games.test/direct.zip"}, 10000).startswith(b"<form")
    handler = _HTTPSRedirect()
    assert handler.redirect_request(Request("https://games.test/game"), None, 302, "Found", {}, "https://cdn.test/archive").full_url == "https://cdn.test/archive"


@pytest.mark.parametrize("url", ["http://games.test/file", "https://localhost/file", "https://127.0.0.1/file",
                                  "https://[::1]/file", "https://192.168.1.2/file", "https://user:password@games.test/file"])
def test_dos_download_rejects_insecure_or_private_urls(url):
    with pytest.raises(ValueError):
        fetch_dos_source({"url": url}, 100)


@pytest.mark.parametrize("peer", ["127.0.0.1", "192.168.1.2", "169.254.169.254", "::1"])
def test_resolved_https_peer_cannot_be_private(peer):
    closed = []
    connection = _PublicHTTPSConnection("public-name.test")
    connection.sock = SimpleNamespace(getpeername=lambda: (peer, 443), close=lambda: closed.append(True))
    with pytest.raises(ValueError, match="private network"):
        connection._check_peer()
    assert closed and connection.sock is None
