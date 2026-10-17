import asyncio
import gzip

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from thelpviewer.server.app import create_app
from thelpviewer.server.compression import ResponseCompressionMiddleware, accepts_encoding
from thelpviewer.server.config import AppConfig


@pytest.mark.parametrize(("accepted", "expected"), [
    ("gzip", True), ("GZip; Q=0.5", True), ("br, gzip;q=0", False),
    ("*;q=0.5", True), ("*;q=1, gzip;q=0", False), ("gzip;q=0, *", False),
    ("gzip;q=invalid", False), ("gzip;q=nan", False), ("gzip;q=2", False),
    ("gzip;q=-1", False), ("not-gzip", False), ("", False), ("identity", False),
    ("br", False), ("gzip, gzip;q=0", False),
])
def test_encoding_negotiation(accepted, expected):
    assert accepts_encoding(accepted, "gzip") is expected


def wire_response(response, *, accepted="gzip", path="/test", method="GET", headers=(), extensions=None):
    """Capture ASGI bytes before httpx/browser automatic content decoding."""
    messages = []
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": method, "path": path, "query_string": b"",
        "headers": [(b"accept-encoding", accepted.encode()), *headers],
        "extensions": extensions or {},
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    asyncio.run(ResponseCompressionMiddleware(response)(scope, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return dict(start["headers"]), body


@pytest.mark.parametrize("accepted", ["gzip", "GZIP;q=0.5", "*;q=0.5"])
def test_shared_gzip_produces_real_compressed_bytes(accepted):
    original = b"large API response " * 10000
    headers, body = wire_response(Response(original, media_type="application/json", headers={
        "Vary": "Cookie", "ETag": '"original"',
    }), accepted=accepted)
    assert headers[b"content-encoding"] == b"gzip"
    assert headers[b"vary"] == b"Cookie, Accept-Encoding"
    assert headers[b"etag"] == b'W/"original"'
    assert int(headers[b"content-length"]) == len(body)
    assert len(body) < len(original) // 10
    assert gzip.decompress(body) == original


@pytest.mark.parametrize("accepted", ["", "identity", "br", "gzip;q=0", "*;q=1, gzip;q=0"])
def test_identity_variant_has_vary_and_original_bytes(accepted):
    original = b"response " * 300
    headers, body = wire_response(Response(original), accepted=accepted)
    assert b"content-encoding" not in headers
    assert headers[b"vary"] == b"Accept-Encoding"
    assert int(headers[b"content-length"]) == len(original)
    assert body == original


@pytest.mark.parametrize(("path", "media_type", "extra_headers", "status"), [
    ("/helps/example.json.gz", "application/json", {}, 200),
    ("/api/dos/bundle", "application/zip", {}, 200),
    ("/assets/font.sf3", "application/octet-stream", {}, 200),
    ("/assets/cover.png", "image/png", {}, 200),
    ("/events", "text/event-stream", {}, 200),
    ("/api/auth/registration-tokens", "application/json", {}, 200),
    ("/api/admin/users", "application/json", {}, 201),
    ("/cookie", "application/json", {"Set-Cookie": "secret=private"}, 200),
    ("/private", "text/plain", {"Cache-Control": "private, no-transform"}, 200),
    ("/encoded", "text/plain", {"Content-Encoding": "br"}, 200),
    ("/partial", "text/plain", {"Content-Range": "bytes 0-2047/4096"}, 206),
])
def test_compressed_and_sensitive_responses_are_not_transformed(path, media_type, extra_headers, status):
    original = b"unaltered bytes " * 300
    headers, body = wire_response(
        Response(original, status_code=status, media_type=media_type, headers=extra_headers), path=path,
    )
    assert headers.get(b"content-encoding") == (b"br" if path == "/encoded" else None)
    assert body == original


def test_small_response_and_range_request_are_not_compressed():
    headers, body = wire_response(Response(b"small"))
    assert b"content-encoding" not in headers and body == b"small"
    headers, body = wire_response(Response(b"range " * 500), headers=[(b"range", b"bytes=0-2047")])
    assert b"content-encoding" not in headers and body == b"range " * 500


def test_streaming_response_is_compressed_without_buffering_the_whole_stream():
    async def chunks():
        for _ in range(4):
            yield b"stream content " * 1000

    headers, body = wire_response(StreamingResponse(chunks(), media_type="text/plain"))
    assert headers[b"content-encoding"] == b"gzip"
    assert b"content-length" not in headers
    assert gzip.decompress(body) == b"stream content " * 4000


def test_original_headers_reach_application_and_pathsend_is_disabled_for_gzip():
    async def app(scope, receive, send):
        assert dict(scope["headers"])[b"accept-encoding"] == b"br, GZIP;q=0.5"
        assert "http.response.pathsend" not in scope["extensions"]
        assert "other-extension" in scope["extensions"]
        await Response(b"file " * 1000)(scope, receive, send)

    headers, body = wire_response(app, accepted="br, GZIP;q=0.5", extensions={
        "http.response.pathsend": {}, "other-extension": {},
    })
    assert headers[b"content-encoding"] == b"gzip"
    assert gzip.decompress(body) == b"file " * 1000


@pytest.fixture
def server(tmp_path):
    web = tmp_path / "www"
    assets = web / "assets"
    assets.mkdir(parents=True)
    helps = tmp_path / "data" / "helps"
    helps.mkdir(parents=True)
    docs = tmp_path / "docs"
    docs.mkdir()
    index = web / "index.html"
    index.write_text("<html><head></head><body>" + "THelpViewer " * 500 + "</body></html>")
    for filename in ("app.js", "style.css", "core.wasm"):
        (assets / filename).write_bytes(b"static asset " * 20000)
    (docs / "guide.md").write_text("# Guide\n\n" + "A documented feature.\n" * 500)
    (helps / "catalog.json").write_text('[{"name":"example"},' + '{"name":"another"},' * 100 + '{}]')
    (helps / "example.json.gz").write_bytes(gzip.compress(b'{"topics":[]}' * 1000))
    config = AppConfig(
        host="127.0.0.1", port=5448, web_dir=web, index_path=index, assets_dir=assets,
        helps_dir=helps, docs_dir=docs, readme_path=tmp_path / "README.md",
        changelog_path=tmp_path / "CHANGELOG.md", state_dir=tmp_path / "var", virtual_docs=(),
        sources_dir=tmp_path / "var" / "sources", downloads_dir=tmp_path / "var" / "downloads",
    )
    app = create_app(config)

    @app.get("/large-api")
    def large_api():
        return {"items": ["API JSON response"] * 1000}

    return TestClient(app)


@pytest.mark.parametrize("url", [
    "/", "/large-api", "/assets/app.js", "/assets/style.css", "/assets/core.wasm",
    "/docs/guide.md", "/helps/catalog.json",
])
def test_application_compresses_public_content_and_file_responses(server, url):
    plain = server.get(url, headers={"Accept-Encoding": "identity"})
    compressed = server.get(url, headers={"Accept-Encoding": "gzip"})
    # No lifespan/index build is started in this isolated transport fixture.
    assert compressed.status_code == plain.status_code == (503 if url == "/" else 200)
    assert compressed.content == plain.content
    assert compressed.headers["content-encoding"] == "gzip"
    assert "Accept-Encoding" in compressed.headers["vary"]
    assert int(compressed.headers.get("content-length", "0")) < len(plain.content)


def test_application_keeps_raw_uhf_and_file_range_and_conditional_responses(server):
    raw_uhf = server.get("/helps/example.json.gz", headers={"Accept-Encoding": "gzip"})
    assert raw_uhf.status_code == 200 and "content-encoding" not in raw_uhf.headers
    assert gzip.decompress(raw_uhf.content) == b'{"topics":[]}' * 1000
    url = "/assets/app.js"
    response = server.get(url, headers={"Accept-Encoding": "gzip"})
    assert response.headers["etag"].startswith("W/")
    not_modified = server.get(url, headers={
        "Accept-Encoding": "gzip", "If-None-Match": response.headers["etag"],
    })
    assert not_modified.status_code == 304 and not_modified.content == b""
    assert "Accept-Encoding" in not_modified.headers["vary"]
    assert not_modified.headers["etag"] == response.headers["etag"]
    partial = server.get(url, headers={"Accept-Encoding": "gzip", "Range": "bytes=10-39"})
    assert partial.status_code == 206
    assert "content-encoding" not in partial.headers
    assert partial.content == response.content[10:40]
    head = server.head(url, headers={"Accept-Encoding": "gzip"})
    assert head.status_code == 200 and not head.content
    assert "content-encoding" not in head.headers
    assert "Accept-Encoding" in head.headers["vary"]


@pytest.mark.parametrize("media_type", [
    "application/xml", "image/svg+xml", "audio/midi", "application/octet-stream",
])
def test_uncompressed_xml_svg_midi_and_dos_data_share_compression(media_type):
    original = b"raw data " * 1000
    headers, body = wire_response(Response(original, media_type=media_type))
    assert headers[b"content-encoding"] == b"gzip"
    assert gzip.decompress(body) == original


def test_head_without_body_retains_identity_file_length_and_cache_variant():
    headers, body = wire_response(Response(b"", headers={"Content-Length": "4096"}), method="HEAD")
    assert body == b"" and headers[b"content-length"] == b"4096"
    assert b"content-encoding" not in headers
    assert headers[b"vary"] == b"Accept-Encoding"

