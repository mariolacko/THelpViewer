import io
import json
from urllib.parse import parse_qs

import pytest

from thelpviewer.config import CONFIG_DIR
from thelpviewer.server.downloader.transport import fetch_source as fetch_dos_source
from thelpviewer.server.downloader.transport import _HTTPSRedirect, _PublicHTTPSConnection
from urllib.request import Request
from types import SimpleNamespace
from urllib.error import HTTPError


def test_standard_dos_catalog_has_explicit_categories_and_opt_in_historical_tools():
    manifest = json.loads((CONFIG_DIR / "dos-prompt.json").read_text())
    categories = {item["id"] for item in manifest["categories"]}
    assert categories == {"games-platform", "games-action", "games-racing", "games-sports",
        "games-puzzle", "games-strategy", "games-rpg", "development", "editors", "filemanagers",
        "archivers", "graphics", "audio", "antivirus", "office"}
    sources = {item["id"]: item for item in manifest["sources"]}
    assert len(sources) == len(manifest["sources"])
    assert all(item["category"] in categories for item in sources.values())
    assert all(isinstance(item.get("description"), str) and item["description"]
               and isinstance(item.get("post_install"), list) for item in sources.values())
    assert all(item.get("icon") for item in manifest["categories"])
    assert categories == {item["category"] for item in sources.values()}
    assert all(item.get("language") for item in sources.values())
    assert sources["bog-quadrax"]["language"] == "sk"
    assert "volkov-commander-405-source" not in sources
    assert {item["id"] for item in sources.values() if item.get("required")} == {"utils", "volkov-commander-405"}
    assert max(len(item["title"]) for item in sources.values()) <= 32
    assert any(item["path"] == "LICENSE.TXT" and item["text"][0].startswith("Copyright")
               for item in sources["volkov-commander-405"]["files"])
    assert {"panda-vlak-201", "panda-dosman-220", "software602-t602-31", "software602-m602-20", "software602-c602"} <= sources.keys()
    assert all(sources[key]["language"] == "cs" and sources[key]["enabled"] is False
               for key in ("panda-vlak-201", "panda-dosman-220", "software602-t602-31", "software602-m602-20"))
    assert {"ia-winter-challenge", "ia-summer-challenge", "ia-lotus-ultimate-challenge",
        "ia-duke-nukum-shareware", "ia-duke-nukem-2-shareware", "ia-crystal-caves-shareware",
        "ia-bio-menace-shareware", "freedos-dos-navigator-2", "freedos-doszip", "freedos-tde",
        "freedos-biew", "freedos-grafx2", "freedos-dosmid"} <= sources.keys()
    assert sources["utils"]["format"] == "collection" and sources["utils"]["archives"]
    assert all("INSTALL" not in sources[key]["launch"] for key in sources if key.startswith("borland-turbo-"))
    new = {"borland-turbo-pascal-302", "borland-turbo-pascal-55", "borland-turbo-c-201",
           "borland-turbo-cpp-101", "thunderbyte-803", "norton-antivirus-michelangelo"}
    assert new <= sources.keys()
    assert all(sources[key]["enabled"] is False and sources[key]["license"] for key in new)
    # Complete antivirus packages retain the licence, not just scanner executables.
    assert all("members" not in sources[key] and "files" not in sources[key]
               for key in ("thunderbyte-803", "norton-antivirus-michelangelo"))


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
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
    progress = []
    source = {"url": url, "download_forms": ["form#download", "form.file"]}
    assert fetch_dos_source(source, 100000, lambda *args: progress.append(args)) == contents
    assert requests[0].data is None
    assert parse_qs(requests[1].data.decode(), keep_blank_values=True) == {"id": ["42"], "d": [""]}
    assert requests[2].full_url == "https://games.test/archive"
    assert parse_qs(requests[2].data.decode(), keep_blank_values=True) == {"token": ["fresh"], "get": [""]}
    assert progress[-1] == (70000, 70000)


def test_unicode_download_form_action_and_post_fields_use_shared_encoding(monkeypatch):
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            data = ('<form method="post" action="/archív – game.zip?q=%2B+čaj">'
                    '<input type="hidden" name="meno" value="Žofia"></form>').encode() if len(requests) == 1 else b"archive"
            return DownloadResponse(data, request.full_url)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
    source = {"url": "https://games.test/hra – page", "download_forms": ["form"]}
    assert fetch_dos_source(source, 10000) == b"archive"
    assert requests[0].full_url == "https://games.test/hra%20%E2%80%93%20page"
    assert requests[1].full_url == "https://games.test/arch%C3%ADv%20%E2%80%93%20game.zip?q=%2B+%C4%8Daj"
    assert parse_qs(requests[1].data.decode()) == {"meno": ["Žofia"]}


def test_package_rate_limit_reports_wait_and_retries_without_losing_form_fields(monkeypatch):
    calls, phases, sleeps = [], [], []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.data)
            if len(calls) == 2:
                raise HTTPError(request.full_url, 429, "rate limit", {"Retry-After": "2"}, None)
            data = b'<form method="post"><input type="hidden" name="id" value="42"></form>' if len(calls) == 1 else b"archive"
            return DownloadResponse(data, request.full_url)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
    monkeypatch.setattr("thelpviewer.server.downloader.transport.time.sleep", sleeps.append)
    source = {"id": "game", "title": "Game", "url": "https://packages.test/game", "download_forms": ["form"]}
    assert fetch_dos_source(source, 10000, on_status=phases.append) == b"archive"
    assert calls == [None, b"id=42", b"id=42"] and sleeps == [1, 1]
    assert phases == ["Downloading", "Downloading", "Rate limited (HTTP 429), retry in 2s", "Rate limited (HTTP 429), retry in 1s", "Downloading"]


def test_persistent_package_rate_limit_names_the_package_and_stops(monkeypatch):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            raise HTTPError(request.full_url, 429, "rate limit", {"Retry-After": "0"}, None)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="Norton Commander.*HTTP 429.*unchanged"):
        fetch_dos_source({"url": "https://packages.test/archive", "title": "Norton Commander"}, 1000)
    assert len(calls) == 3


def test_download_form_cannot_downgrade_to_http(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            return DownloadResponse(b'<form method="post" action="http://games.test/archive"></form>', request.full_url)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="HTTPS"):
        fetch_dos_source({"url": "https://games.test/game", "download_forms": ["form"]}, 10000)


def test_dos_source_byte_limit_applies_to_form_downloads(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            return DownloadResponse(bytes(1001), request.full_url)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="size limit"):
        fetch_dos_source({"url": "https://games.test/game", "download_forms": ["form"]}, 1000)


def test_direct_download_and_cross_host_forms_work_without_host_configuration(monkeypatch):
    urls = []
    class Opener:
        def open(self, request, timeout):
            urls.append(request.full_url)
            data = b'<form method="post" action="https://cdn.test/archive"></form>' if len(urls) == 1 else b"archive"
            return DownloadResponse(data, request.full_url)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.build_opener", lambda *args: Opener())
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
