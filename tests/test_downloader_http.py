from __future__ import annotations

from email.message import Message
from http.client import HTTPConnection
from types import SimpleNamespace
import urllib.error
from urllib.request import Request

import pytest

from thelpviewer.server.downloader import http
from thelpviewer.server.processing import observe_progress
from thelpviewer.server.downloader.transport import read_request, retry_delay, MAX_RETRY_AFTER, _HTTPSRedirect


class _Response:
    def __init__(self, payload: bytes):
        self.headers: dict[str, str] = {}
        self._chunks = iter((payload, b""))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size: int) -> bytes:
        return next(self._chunks)


class _FlakyOpener:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls = 0

    def open(self, _url: str, timeout: int):
        assert timeout == 120
        self.calls += 1
        if self.calls == 1:
            raise urllib.error.URLError("temporary outage")
        return _Response(self.payload)


@pytest.mark.parametrize(("url", "encoded"), [
    ("https://music.test/Space%20Quest%20–%20The%20Sarien%20Encounter.zip",
     "https://music.test/Space%20Quest%20%E2%80%93%20The%20Sarien%20Encounter.zip"),
    ("https://music.test/Žltá skladba 🎵.mid?q=čaj+koláč&path=%2Ftest%2f&plus=%2B#čas",
     "https://music.test/%C5%BDlt%C3%A1%20skladba%20%F0%9F%8E%B5.mid?q=%C4%8Daj+kol%C3%A1%C4%8D&path=%2Ftest%2f&plus=%2B#%C4%8Das"),
    ("http://example.test/a%20b/(c)/a%2Fb?signature=x+y%2Bz&empty=",
     "http://example.test/a%20b/(c)/a%2Fb?signature=x+y%2Bz&empty="),
    ("https://bücher.test:443/čaj", "https://xn--bcher-kva.test:443/%C4%8Daj"),
    ("https://[2606:4700:4700::1111]/čaj?", "https://[2606:4700:4700::1111]/%C4%8Daj?"),
])
@pytest.mark.parametrize("post", [False, True])
def test_shared_transport_encodes_unicode_without_changing_escaped_urls(url, encoded, post):
    body = b"id=42&name=%C4%8Daj"
    request = Request(url, data=body, headers={"Cookie": "test=42", "Content-Type": "application/x-www-form-urlencoded"}) if post else url
    calls = []
    def open_request(value, **_kwargs):
        calls.append(value)
        actual = value if isinstance(value, Request) else Request(value)
        assert actual.full_url == encoded
        # The real HTTP serializer raised UnicodeEncodeError before the fix.
        connection = HTTPConnection(actual.host)
        connection.putrequest(actual.get_method(), actual.selector)
        if post:
            assert actual is request and actual.get_method() == "POST" and actual.data == body
            assert actual.get_header("Cookie") == "test=42"
            assert actual.get_header("Content-type") == "application/x-www-form-urlencoded"
        return _Response(b"archive")
    contents, final_url, _headers = read_request(SimpleNamespace(open=open_request), request, 100)
    assert contents == b"archive" and final_url == encoded and len(calls) == 1


def test_shared_redirect_encodes_unicode_and_keeps_host_and_https_guards():
    request = Request("https://music.test/old.mid")
    handler = _HTTPSRedirect(allowed_hosts={"music.test"})
    redirect = handler.redirect_request(request, None, 302, "Found", {}, "https://music.test/Žltá%20–%20song.mid?q=%2B+čaj")
    assert redirect.full_url == "https://music.test/%C5%BDlt%C3%A1%20%E2%80%93%20song.mid?q=%2B+%C4%8Daj"
    for target in ("https://outside.test/čaj.mid", "http://music.test/čaj.mid", "https://127.0.0.1/čaj.mid"):
        with pytest.raises(ValueError):
            handler.redirect_request(request, None, 302, "Found", {}, target)
    # HTTP headers are decoded as Latin-1 by http.client; urllib recovers UTF-8 bytes.
    targets = []
    handler.parent = SimpleNamespace(open=lambda value, **_kwargs: targets.append(value.full_url) or "redirected")
    request.timeout = 30
    from io import BytesIO
    headers = Message()
    headers["Location"] = "https://music.test/čaj – song.mid".encode("utf-8").decode("latin-1")
    assert handler.http_error_302(request, BytesIO(), 302, "Found", headers) == "redirected"
    assert targets == ["https://music.test/%C4%8Daj%20%E2%80%93%20song.mid"]


@pytest.mark.parametrize("url", ["https://music.test/track\n.mid", "https://music.test/track\r.mid",
    "https://music.test/track\t.mid", "https://music.test/track\x00.mid", "https://@music.test/track.mid",
    "https://ｌｏｃａｌｈｏｓｔ/track.mid", "https://１２７.０.０.１/track.mid"])
def test_url_encoding_does_not_hide_unsafe_addresses(url):
    def unexpected(*_args, **_kwargs):
        pytest.fail("Invalid URL reached the network")
    with pytest.raises(ValueError):
        read_request(SimpleNamespace(open=unexpected), url, 100)


def test_download_file_retries_transient_network_errors(tmp_path, monkeypatch):
    opener = _FlakyOpener(b"complete payload")
    monkeypatch.setattr(http, "get_opener", lambda: opener)
    monkeypatch.setattr(http.time, "sleep", lambda _seconds: None)
    destination = tmp_path / "archive.bin"

    result = http.download_file("https://example.test/archive.bin", destination, retries=2)

    assert result == destination
    assert destination.read_bytes() == b"complete payload"
    assert opener.calls == 2
    assert not (tmp_path / "archive.bin.tmp").exists()


def test_retry_after_is_numeric_and_bounded():
    headers = Message()
    headers["Retry-After"] = "not-a-number"
    assert retry_delay(headers, 30) == 30

    headers.replace_header("Retry-After", "9999")
    assert retry_delay(headers, 30) == MAX_RETRY_AFTER


def test_download_progress_uses_archive_name_and_clears_bytes_between_phases(tmp_path, monkeypatch):
    response = _Response(b"complete payload")
    response.headers["Content-Length"] = "16"
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=lambda *args, **kwargs: response))
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    destination = tmp_path / "Borland Turbo Pascal 7.0.7z"
    events = []
    with observe_progress(events.append):
        http.download_file("https://example.test/download/mirror-id", destination)
        http.download_file("https://example.test/download/mirror-id", destination)
    assert [(event["phase"], event["file"], event["received"], event["bytes_total"]) for event in events] == [
        ("Downloading", destination.name, 0, 0),
        ("Downloading", destination.name, 16, 16),
        ("Downloaded", destination.name, 0, 0),
        ("Using cached archive", destination.name, 0, 0),
    ]


def test_rate_limit_is_reported_as_waiting_before_retry(tmp_path, monkeypatch):
    events, calls = [], []
    def open_response(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 429, "rate limit", {"Retry-After": "3"}, None)
        return _Response(b"payload")
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=open_response))
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    with observe_progress(events.append):
        http.download_file("https://example.test/download/id", tmp_path / "Help archive.zip", retries=2)
    assert [event["phase"] for event in events] == [
        "Downloading", "Rate limited (HTTP 429), retry in 3s", "Rate limited (HTTP 429), retry in 2s",
        "Rate limited (HTTP 429), retry in 1s", "Downloading", "Downloading", "Downloaded"]
    assert all(event["file"] == "Help archive.zip" for event in events)


def test_help_rate_limit_defers_site_and_redirects_but_not_other_sites_or_new_jobs(tmp_path, monkeypatch):
    from thelpviewer.server.downloader import transport

    calls, cooldowns = [], []
    def open_response(url, **_kwargs):
        calls.append(url)
        if "limited.test" in url:
            raise urllib.error.HTTPError(url, 429, "quota", {"Retry-After": "0"}, None)
        return _Response(b"archive")
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=open_response))
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    monkeypatch.setattr(transport, "defer_source", lambda url, delay: cooldowns.append((url, delay)))
    deferred = set()
    with transport.defer_limited_sources(deferred):
        with pytest.raises(transport.SourceRateLimited, match="alternative sources"):
            http.download_file("https://limited.test/download/first", tmp_path / "first.zip")
        assert calls == ["https://limited.test/download/first"] * 3
        assert deferred == {"limited.test"} and len(cooldowns) == 3
        with pytest.raises(transport.SourceRateLimited):
            http.download_file("https://mirror.limited.test/another", tmp_path / "second.zip")
        with pytest.raises(transport.SourceRateLimited):
            _HTTPSRedirect().redirect_request(Request("https://other.test/start"), None,
                302, "Found", {}, "https://limited.test/mirror")
        assert len(calls) == 3  # No network request or cooldown wait for other mirrors.
        assert http.download_file("https://other.test/archive.zip", tmp_path / "other.zip").read_bytes() == b"archive"
    assert not (tmp_path / "first.zip").exists() and not (tmp_path / "second.zip").exists()
    assert not list(tmp_path.glob("*.part"))
    # A later explicit retry has a fresh operation scope, not a permanent ban.
    with transport.defer_limited_sources(set()):
        with pytest.raises(transport.SourceRateLimited):
            http.download_file("https://limited.test/download/first", tmp_path / "first.zip", retries=1)
    assert len(calls) == 5


def test_help_transient_rate_limit_can_recover_within_bounded_attempts(tmp_path, monkeypatch):
    from thelpviewer.server.downloader.transport import defer_limited_sources

    calls = []
    def open_response(url, **_kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 429, "quota", {"Retry-After": "0"}, None)
        return _Response(b"archive")
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=open_response))
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    deferred = set()
    with defer_limited_sources(deferred):
        assert http.download_file("https://transient.test/file", tmp_path / "file").read_bytes() == b"archive"
    assert len(calls) == 2 and not deferred
