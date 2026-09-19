from __future__ import annotations

from email.message import Message
import urllib.error

from thelpviewer.downloader import http


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
    assert http._retry_delay(headers, 30) == 30

    headers.replace_header("Retry-After", "9999")
    assert http._retry_delay(headers, 30) == http.MAX_RETRY_AFTER
