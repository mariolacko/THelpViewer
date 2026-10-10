"""Server-wide UHF search is incremental and never moves HELP bundles."""

from dataclasses import replace
import gzip
from html import unescape
from importlib import import_module
import json
import re
import threading
import time
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.search_index import GlobalSearchIndex


def _bundle(path, title, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as output:
        json.dump({
            "uhf_version": "2.0",
            "metadata": {"name": title},
            "topics": {"7": {"id": 7, "title": title, "content": content}},
            "index": [{"group": "A", "entries": [{"label": "Indexed Alpha", "topic_id": 7}]}],
        }, output)


def _ready(client):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = client.get("/api/search/status").json()
        if status["state"] == "ready":
            return status
        assert status["state"] == "building", status
        assert 0 <= status["percent"] <= 100
        time.sleep(0.02)
    raise AssertionError("global index did not finish")


def test_global_search_builds_incrementally_and_removes_missing_help(tmp_path):
    helps = tmp_path / "helps"
    first = helps / "first.json.gz"
    second = helps / "nested" / "second.json.gz"
    _bundle(first, "First topic", ["A [link:topic=8]Turbo Vision[/link] guide", "[[literal]", "<script>alert(1)</script>"])
    (helps / "catalog.json").write_text(json.dumps([
        {"file": "first.json.gz", "name": "The First HELP", "source_file": "FIRST.NG"},
    ]), encoding="utf-8")
    config = replace(load_config(), helps_dir=helps, docs_dir=tmp_path / "docs", virtual_docs=(),
                     state_dir=tmp_path / "var",
                     public_base_url="https://help.example.test",
                     google_site_verification="",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        assert 'google-site-verification' not in client.get("/").text
        status = _ready(client)
        assert status["percent"] == 100 and status["topics"] == 1
        home = client.get("/")
        assert '<main id="tv-public-fallback">' in home.text
        assert 'href="/?file=first.json.gz"' in home.text
        assert "The First HELP" in home.text
        assert 'rel="canonical" href="https://help.example.test/"' in home.text
        assert client.get("/assets/Thelp.png").headers["content-type"] == "image/png"
        assert client.get("/favicon.ico", follow_redirects=False).headers["location"] == "/assets/thelp-icon.svg"
        database = tmp_path / "var" / "global-search.sqlite3"
        assert database.is_file() and first.is_file()
        matches = client.get("/api/search/global", params={"q": "turbo"}).json()["results"]
        assert [(row["file"], row["help_name"], row["context_hex"]) for row in matches] == [
            ("first.json.gz", "The First HELP", "7"),
        ]
        assert matches[0]["source_file"] == "FIRST.NG"
        assert "Indexed Alpha" in client.get("/api/search/global", params={"q": "indexed"}).json()["results"][0]["index_terms"]
        assert client.get("/api/search/global", params={"q": '" OR *'}).status_code == 200
        page = client.get("/", params={"file": "first.json.gz", "topic": "7"})
        assert page.status_code == 200
        assert 'google-site-verification' not in page.text
        assert "Turbo Vision" in page.text
        assert "&lt;script&gt;" in page.text and "<script>" not in page.text
        assert 'data-tv-bundle-desktop' in page.text
        assert '<main id="tv-public-fallback">' in page.text
        assert "Open in THelpViewer" not in page.text
        assert 'https://help.example.test/?file=first.json.gz&amp;topic=7' in page.text
        public = client.get("/", params={"file": "first.json.gz", "topic": "7"})
        assert public.status_code == 200 and "Turbo Vision" in public.text
        assert 'href="/?file=first.json.gz"' in public.text
        overview = client.get("/", params={"file": "first.json.gz"})
        assert overview.status_code == 200
        assert "The First HELP" in overview.text
        assert 'data-tv-bundle-desktop' in overview.text
        assert 'href="/?file=first.json.gz&amp;topic=7"' in overview.text
        assert 'https://help.example.test/?file=first.json.gz' in overview.text
        assert client.get("/", params={"file": "missing.json.gz"},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/", params={"file": ""},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/", params={"file": "missing.json.gz", "topic": "7"},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/topics/first.json.gz", params={"topic": "7"},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/", params={"file": "first.json.gz", "topic": "absent"}).status_code == 404
        assert client.get("/", params={"file": "first.json.gz", "topic": "absent"},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert "Sitemap: https://help.example.test/sitemap.xml" in client.get("/robots.txt").text
        sitemap_index = client.get("/sitemap.xml")
        assert sitemap_index.status_code == 200
        assert "https://help.example.test/sitemaps/site.xml" in sitemap_index.text
        assert "sitemaps/file.xml?file=first.json.gz&amp;page=1" in sitemap_index.text
        ElementTree.fromstring(sitemap_index.text)
        site_map = client.get("/sitemaps/site.xml")
        assert site_map.status_code == 200
        assert "https://help.example.test/</loc>" in site_map.text
        ElementTree.fromstring(site_map.text)
        file_map = client.get("/sitemaps/file.xml", params={"file": "first.json.gz", "page": 1})
        assert file_map.status_code == 200
        assert "?file=first.json.gz</loc>" in file_map.text
        assert "?file=first.json.gz&amp;topic=7</loc>" in file_map.text
        ElementTree.fromstring(file_map.text)
        assert client.get("/sitemaps/file.xml", params={"file": "first.json.gz", "page": 2}).status_code == 404
        assert client.get("/sitemaps/file.xml", params={"file": "missing.json.gz"}).status_code == 404
        assert "?file=first.json.gz&amp;topic=7" in client.get("/sitemap-1.xml").text
        assert client.get("/sitemap-2.xml").status_code == 404

        _bundle(second, "Second topic", ["Another Turbo guide"])
        assert _ready(client)["topics"] == 2
        results = client.get("/api/search/global", params={"q": "turbo"}).json()["results"]
        assert {row["file"] for row in results} == {"first.json.gz", "nested/second.json.gz"}
        assert "sitemaps/file.xml?file=nested%2Fsecond.json.gz&amp;page=1" in client.get("/sitemap.xml").text

        first.unlink()
        assert _ready(client)["topics"] == 1
        results = client.get("/api/search/global", params={"q": "turbo"}).json()["results"]
        assert [row["file"] for row in results] == ["nested/second.json.gz"]
        assert "first.json.gz" not in client.get("/sitemap.xml").text
        assert client.get("/sitemaps/file.xml", params={"file": "first.json.gz"}).status_code == 404
        assert "?file=first.json.gz&amp;topic=7" not in client.get("/sitemap-1.xml").text
        assert "?file=nested%2Fsecond.json.gz&amp;topic=7" in client.get("/sitemap-1.xml").text


def test_global_search_empty_catalog_is_ready(tmp_path):
    helps = tmp_path / "helps"
    helps.mkdir()
    config = replace(load_config(), helps_dir=helps, docs_dir=tmp_path / "docs", virtual_docs=(),
                     state_dir=tmp_path / "var",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        assert client.get("/api/search/status").json()["state"] == "ready"
        assert client.get("/api/search/global", params={"q": "anything"}).json()["results"] == []


def test_public_docs_share_search_index_and_have_crawlable_pages(tmp_path):
    helps = tmp_path / "helps"
    docs = tmp_path / "docs"
    helps.mkdir()
    docs.mkdir()
    guide = docs / "Guide.md"
    guide.write_text("# Guide\n\nUnique Zebra text <script>alert(1)</script>", encoding="utf-8")
    (docs / "Private Audit.md").write_text("Hidden Zebra", encoding="utf-8")
    (docs / "Research RE Notes.md").write_text("Hidden Zebra", encoding="utf-8")
    (docs / "Audit.md").write_text("Hidden Zebra", encoding="utf-8")
    (docs / "RE.md").write_text("Hidden Zebra", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("# Welcome\n\nPublic Penguin text", encoding="utf-8")
    config = replace(load_config(), helps_dir=helps, docs_dir=docs,
                     virtual_docs=(("README.md", readme), ("Alias/README.md", readme)),
                     state_dir=tmp_path / "var", public_base_url="https://help.example.test",
                     google_site_verification='verification-"&',
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        verification = '<meta name="google-site-verification" content="verification-&quot;&amp;" />'
        assert verification in client.get("/").text
        assert _ready(client)["documents"] == 2
        results = client.get("/api/search/global", params={"q": "zebra"}).json()["results"]
        assert [(row["kind"], row["file"], row["title"]) for row in results] == [
            ("doc", "Guide.md", "Guide"),
        ]
        assert client.get("/api/search/global", params={"q": "penguin"}).json()["results"][0]["file"] == "README.md"
        assert client.get("/api/search/global", params={"q": "hidden"}).json()["results"] == []
        sitemap = client.get("/sitemap.xml")
        assert "sitemaps/docs.xml?page=1" in sitemap.text
        home = client.get("/")
        assert 'href="/?doc=Guide.md"' in home.text
        assert 'href="/?doc=README.md"' in home.text
        assert "Private Audit" not in home.text
        docs_map = client.get("/sitemaps/docs.xml")
        assert docs_map.status_code == 200
        assert "?doc=Guide.md" in docs_map.text
        assert "?doc=README.md" in docs_map.text
        assert "/documents/" not in docs_map.text
        assert "Alias" not in docs_map.text and "Audit" not in docs_map.text
        ElementTree.fromstring(docs_map.text)
        page = client.get("/", params={"doc": "Guide.md"})
        assert page.status_code == 200
        assert "Unique Zebra text" in page.text
        assert verification in page.text
        assert "&lt;script&gt;" in page.text and "<script>" not in page.text
        assert 'https://help.example.test/?doc=Guide.md' in page.text
        assert 'data-tv-bundle-desktop' in page.text
        assert '<main id="tv-public-fallback">' in page.text
        assert "Open in THelpViewer" not in page.text
        assert client.get("/documents/Guide.md", headers={"Accept": "text/html"},
                          follow_redirects=False).status_code == 404
        assert client.get("/", params={"doc": ""},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/", params={"doc": "Private Audit.md"},
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/documents/Private%20Audit.md",
                          headers={"Accept": "text/html"}, follow_redirects=False).status_code == 404
        assert client.get("/documents/Alias/README.md").status_code == 404

        guide.write_text("# Guide\n\nUpdated Otter text", encoding="utf-8")
        assert _ready(client)["documents"] == 2
        assert client.get("/api/search/global", params={"q": "otter"}).json()["results"][0]["file"] == "Guide.md"
        assert client.get("/api/search/global", params={"q": "zebra"}).json()["results"] == []
        guide.unlink()
        assert _ready(client)["documents"] == 1
        assert client.get("/", params={"doc": "Guide.md"}).status_code == 404
        assert client.get("/documents/Guide.md", follow_redirects=False).status_code == 404
        assert "Guide.md" not in client.get("/sitemaps/docs.xml").text


def test_file_sitemap_pages_keep_overview_on_first_page(tmp_path, monkeypatch):
    monkeypatch.setattr(import_module("thelpviewer.server.routes.public_pages"), "SITEMAP_TOPIC_PAGE_SIZE", 2)
    helps = tmp_path / "helps"
    helps.mkdir()
    with gzip.open(helps / "many.json.gz", "wt", encoding="utf-8") as output:
        json.dump({
            "metadata": {"name": "Many topics"},
            "topics": {
                str(number): {"id": number, "title": f"Topic {number}", "content": [f"Body {number}"]}
                for number in range(1, 4)
            },
        }, output)
    config = replace(load_config(), helps_dir=helps, docs_dir=tmp_path / "docs", virtual_docs=(),
                     state_dir=tmp_path / "var",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        _ready(client)
        index = client.get("/sitemap.xml").text
        assert "file=many.json.gz&amp;page=1" in index
        assert "file=many.json.gz&amp;page=2" in index
        first = client.get("/sitemaps/file.xml", params={"file": "many.json.gz", "page": 1}).text
        second = client.get("/sitemaps/file.xml", params={"file": "many.json.gz", "page": 2}).text
        assert first.count("<url>") == 3  # overview and two topics
        assert second.count("<url>") == 1
        assert "?file=many.json.gz</loc>" in first
        assert "?file=many.json.gz</loc>" not in second
        assert "topic=3" in second
        assert client.get("/sitemaps/file.xml", params={"file": "many.json.gz", "page": 3}).status_code == 404


def test_public_urls_redirect_encoding_variants_to_sitemap_urls(tmp_path):
    helps = tmp_path / "helps"
    docs = tmp_path / "docs"
    docs.mkdir()
    file_path = "Borland C++ 3.0/tchelp.json.gz"
    doc_path = "Formats/HELP Format.md"
    _bundle(helps / file_path, "Topic title", ["Topic body"])
    (docs / "Formats").mkdir()
    (docs / doc_path).write_text("# HELP Format\n\nDocument body", encoding="utf-8")
    midi_sources = tmp_path / "midi.json"
    midi_sources.write_text('{"sources": []}', encoding="utf-8")
    config = replace(load_config(), helps_dir=helps, docs_dir=docs, virtual_docs=(),
                     state_dir=tmp_path / "var", midi_sources_path=midi_sources,
                     public_base_url="https://help.example.test",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        _ready(client)
        topic_url = "/?" + urlencode({"file": file_path, "topic": "7"})
        overview_url = "/?" + urlencode({"file": file_path})
        doc_url = "/?" + urlencode({"doc": doc_path})
        for variant, expected in (
            (topic_url.replace("%2F", "/"), topic_url),
            (topic_url.replace("%2F", "%2f"), topic_url),
            (topic_url.replace("+", "%20"), topic_url),
            ("/?" + urlencode({"topic": "7", "file": file_path}), topic_url),
            (overview_url.replace("%2F", "/"), overview_url),
            (doc_url.replace("%2F", "/").replace("+", "%20"), doc_url),
            (topic_url.replace("%2F", "/") + "&line=2&slow=1", topic_url + "&line=2&slow=1"),
        ):
            response = client.get(variant, follow_redirects=False)
            assert response.status_code == 308, variant
            assert response.headers["location"] == expected
            page = client.get(expected, follow_redirects=False)
            assert page.status_code == 200
            canonical = unescape(re.search(r'<link rel="canonical" href="([^"]+)"', page.text)[1])
            assert canonical == config.public_base_url + expected.split("&line=")[0]

        # Do not try to repair ambiguous literal '+' or redirect missing content.
        assert client.get("/?file=Borland+C+++3.0/tchelp.json.gz&topic=7",
                          follow_redirects=False).status_code == 404
        assert client.get("/?file=missing/path.json.gz&topic=7",
                          follow_redirects=False).status_code == 404
        assert client.get(overview_url + "&topic=missing",
                          follow_redirects=False).status_code == 404

        # Every advertised canonical must return HTML directly, without a redirect.
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        maps = ElementTree.fromstring(client.get("/sitemap.xml").text)
        for location in maps.findall("s:sitemap/s:loc", namespace):
            parsed = urlsplit(location.text)
            sitemap = client.get(parsed.path + ("?" + parsed.query if parsed.query else ""))
            assert sitemap.status_code == 200
            for url in ElementTree.fromstring(sitemap.text).findall("s:url/s:loc", namespace):
                parsed = urlsplit(url.text)
                page = client.get(parsed.path + ("?" + parsed.query if parsed.query else ""),
                                  follow_redirects=False)
                assert page.status_code == 200, url.text
                canonical = unescape(re.search(r'<link rel="canonical" href="([^"]+)"', page.text)[1])
                assert canonical == url.text


def test_browser_error_page_keeps_messagebox_but_returns_real_404(tmp_path):
    helps = tmp_path / "helps"
    helps.mkdir()
    midi_sources = tmp_path / "midi.json"
    midi_sources.write_text('{"sources": []}', encoding="utf-8")
    config = replace(load_config(), helps_dir=helps, docs_dir=tmp_path / "docs", virtual_docs=(),
                     state_dir=tmp_path / "var", midi_sources_path=midi_sources,
                     google_site_verification="test-verification",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        response = client.get("/missing", headers={"Accept": "text/html"})
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")
        assert response.headers["x-robots-tag"] == "noindex"
        assert response.url.params["server_error"] == "404"
        assert response.url.params["server_path"] == "/missing"
        assert 'data-tv-bundle-desktop' in response.text
        assert 'tv-bundle-app.js' in response.text
        assert 'content="test-verification"' in response.text
        assert 'rel="canonical"' not in response.text
        assert client.get("/api/missing").json() == {"detail": "Not Found"}


def test_original_error_documentation_is_not_a_website_error(tmp_path):
    helps = tmp_path / "helps"
    helps.mkdir()
    topics = {
        "3": {"title": "There is currently no help available for",
              "content": ["", "There is currently no help available for", "this item."]},
        "591": {"title": "Could not find file 'filename'",
                "content": ["Could not find file 'filename'", "The compiler is unable to find the file",
                            "supplied on the command line."]},
        "29": {"title": "Match Not Found", "content": ["[b]Match Not Found[/b]",
               "MS-DOS Help could not find the text you specified.",
               "The cursor remains at the location where you started the search."]},
        "719": {"title": "Could not find a match for argument(s)",
                "content": ["Could not find a match for argument(s)",
                            "No C++ function could be found with parameters matching the supplied arguments."]},
        "800": {"title": "More information", "content": [
            "There is currently no help available for this item.", "Read the manual for more information."]},
        "402": {"title": "Pomoc nie je dostupná", "content": ["Pre túto položku nie je dostupná pomoc."]},
        "403": {"title": "Fichier introuvable", "content": ["Le compilateur ne trouve pas le fichier."]},
        "404": {"title": "Nicht gefunden", "content": ["Nicht gefunden"]},
        "0": {"title": "Empty topic", "content": ["", "   ", "[b][/b]"]},
    }
    with gzip.open(helps / "messages.json.gz", "wt", encoding="utf-8") as output:
        json.dump({"metadata": {"name": "Original software HELP"}, "topics": topics}, output)
    # Unknown/short messages are not classified by their wording or filename.
    _bundle(helps / "placeholder.json.gz", "No help", topics["3"]["content"])
    midi_sources = tmp_path / "midi.json"
    midi_sources.write_text('{"sources": []}', encoding="utf-8")
    config = replace(load_config(), helps_dir=helps, docs_dir=tmp_path / "docs", virtual_docs=(),
                     state_dir=tmp_path / "var", midi_sources_path=midi_sources,
                     statistics_path=tmp_path / "var" / "statistics.sqlite3")
    with TestClient(create_app(config)) as client:
        assert _ready(client)["topics"] == 10
        non_empty_topics = set(topics) - {"0"}
        for topic in non_empty_topics:
            page = client.get("/", params={"file": "messages.json.gz", "topic": topic})
            assert page.status_code == 200
            assert "x-robots-tag" not in page.headers
            assert '<h1>HELP reference:' in page.text
            assert "Original documentation from" in page.text
            assert "not a status message from this website" in page.text
            assert 'content="Reference documentation from Original software HELP:' in page.text
        placeholder = client.get("/", params={"file": "messages.json.gz", "topic": "3"})
        assert placeholder.status_code == 200
        assert "x-robots-tag" not in placeholder.headers
        assert "There is currently no help available for\nthis item." in placeholder.text
        assert 'href="/?file=messages.json.gz&amp;topic=3"' in client.get(
            "/", params={"file": "messages.json.gz"}).text
        assert client.get("/", params={"file": "placeholder.json.gz"}).status_code == 200
        assert "x-robots-tag" not in client.get("/", params={"file": "placeholder.json.gz", "topic": "7"}).headers
        assert "placeholder.json.gz" in client.get("/sitemap.xml").text
        assert client.get("/sitemaps/file.xml", params={"file": "placeholder.json.gz"}).status_code == 200
        assert client.get("/", params={"file": "messages.json.gz", "topic": "0"}).status_code == 404
        assert client.app.state.global_search.sitemap_count() == 9

        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url in ("/sitemaps/file.xml?file=messages.json.gz", "/sitemap-1.xml"):
            sitemap = ElementTree.fromstring(client.get(url).text)
            parameters = [urlsplit(location.text).query
                          for location in sitemap.findall("s:url/s:loc", namespace)]
            urls = [client.get("/?" + query).url.params for query in parameters]
            topics_in_map = {params.get("topic") for params in urls if params.get("file") == "messages.json.gz"}
            assert topics_in_map - {None} == non_empty_topics
        matches = client.get("/api/search/global", params={"q": "currently"}).json()["results"]
        assert any(row["file"] == "messages.json.gz" and row["context_hex"] == "3" for row in matches)


def _isolated_config(tmp_path):
    helps = tmp_path / "helps"
    docs = tmp_path / "docs"
    helps.mkdir()
    docs.mkdir()
    midi = tmp_path / "midi.json"
    midi.write_text('{"sources": []}', encoding="utf-8")
    return replace(load_config(), helps_dir=helps, docs_dir=docs, virtual_docs=(),
                   state_dir=tmp_path / "var", midi_sources_path=midi,
                   statistics_path=tmp_path / "var" / "statistics.sqlite3")


@pytest.mark.parametrize("damage", ["gzip", "deflate", "truncated", "json", "structure"])
def test_bad_bundle_is_isolated_and_repaired_bundle_is_retried(tmp_path, caplog, damage):
    config = _isolated_config(tmp_path)
    damaged = config.helps_dir / "a-damaged.json.gz"
    _bundle(damaged, "Old topic", ["Old unique text"])
    _bundle(config.helps_dir / "z-good.json.gz", "Healthy topic", ["Healthy zebra text"])
    (config.docs_dir / "Guide.md").write_text("# Guide\n\nHealthy zebra docs", encoding="utf-8")
    with TestClient(create_app(config)) as client:
        assert _ready(client)["topics"] == 2
        if damage == "gzip":
            damaged.write_bytes(b"Not gzip")
        elif damage == "deflate":
            damaged.write_bytes(bytes.fromhex("1f8b08000000000002ff07"))  # Invalid DEFLATE block type.
        elif damage == "truncated":
            damaged.write_bytes(gzip.compress(b'{"topics":{}}')[:15])
        else:
            with gzip.open(damaged, "wt", encoding="utf-8") as output:
                output.write("Not JSON" if damage == "json" else "[]")
        status = _ready(client)
        assert status["available"] is True and status["topics"] == 1
        assert [(warning["kind"], warning["file"]) for warning in status["warnings"]] == [
            ("help", "a-damaged.json.gz"),
        ]
        assert damaged.exists()  # Only its cached index rows were removed.
        assert "Cannot index help a-damaged.json.gz" in caplog.text
        assert client.get("/", params={"file": "z-good.json.gz", "topic": "7"}).status_code == 200
        assert client.get("/", params={"doc": "Guide.md"}).status_code == 200
        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200 and "a-damaged" not in sitemap.text
        assert "z-good" in sitemap.text
        for params in ({"file": "a-damaged.json.gz"}, {"file": "a-damaged.json.gz", "topic": "7"}):
            response = client.get("/", params=params)
            assert response.status_code == 503
            assert response.headers["retry-after"] == "60"
        assert client.get("/sitemaps/file.xml", params={"file": "a-damaged.json.gz"}).status_code == 503
        response = client.get("/api/search/global", params={"q": "zebra"})
        assert response.status_code == 200 and len(response.json()["results"]) == 2
        assert response.json()["status"]["warnings"] == status["warnings"]
        assert client.get("/api/search/global", params={"q": "unique"}).json()["results"] == []
        caplog.clear()
        for _ in range(3):
            assert client.get("/api/search/status").json()["state"] == "ready"
        assert "Cannot index" not in caplog.text  # No retry storm for unchanged bad data.
        _bundle(damaged, "Repaired topic", ["Recovered unique text"])
        status = _ready(client)
        assert status["warnings"] == [] and status["topics"] == 2
        assert client.get("/", params={"file": "a-damaged.json.gz", "topic": "7"}).status_code == 200
        assert "a-damaged" in client.get("/sitemap.xml").text
        assert client.get("/api/search/global", params={"q": "recovered"}).json()["results"]
        damaged.unlink()
        assert _ready(client)["topics"] == 1
        assert client.get("/", params={"file": "a-damaged.json.gz", "topic": "7"}).status_code == 404


def test_bad_bundle_on_first_build_does_not_prevent_later_files(tmp_path):
    config = _isolated_config(tmp_path)
    damaged = config.helps_dir / "a-first.json.gz"
    damaged.write_bytes(b"Bad gzip")
    _bundle(config.helps_dir / "z-later.json.gz", "Healthy later topic", ["Healthy body"])
    with TestClient(create_app(config)) as client:
        status = _ready(client)
        assert status["available"] and status["topics"] == 1 and len(status["warnings"]) == 1
        assert client.get("/", params={"file": "z-later.json.gz", "topic": "7"}).status_code == 200
        damaged.unlink()
        assert _ready(client)["warnings"] == []
        assert client.get("/", params={"file": "a-first.json.gz", "topic": "7"}).status_code == 404


def test_completed_topics_search_and_sitemaps_stay_available_during_update(tmp_path, monkeypatch):
    config = _isolated_config(tmp_path)
    first = config.helps_dir / "first.json.gz"
    removed = config.helps_dir / "removed.json.gz"
    _bundle(first, "Old topic", ["Old cached text"])
    _bundle(removed, "Removed topic", ["Removed text"])
    with TestClient(create_app(config)) as client:
        _ready(client)
        entered = threading.Event()
        release = threading.Event()
        original = client.app.state.global_search._update_source
        def blocked(connection, kind, name, snapshot):
            if name in ("first.json.gz", "New.md"):
                entered.set()
                assert release.wait(5)
            return original(connection, kind, name, snapshot)
        monkeypatch.setattr(client.app.state.global_search, "_update_source", blocked)
        _bundle(first, "Updated topic", ["New fresh text"])
        _bundle(config.helps_dir / "new.json.gz", "New topic", ["New pending file text"])
        (config.docs_dir / "New.md").write_text("# New pending document", encoding="utf-8")
        removed.unlink()
        client.get("/api/search/status")
        assert entered.wait(5)
        try:
            status = client.get("/api/search/status").json()
            assert status["state"] == "building" and status["available"]
            page = client.get("/", params={"file": "first.json.gz", "topic": "7"})
            assert page.status_code == 200 and "Old cached text" in page.text
            response = client.get("/api/search/global", params={"q": "cached"})
            assert response.status_code == 200 and response.json()["results"]
            assert response.json()["status"]["state"] == "building"
            assert client.get("/sitemap.xml").status_code == 200
            assert client.get("/sitemaps/file.xml", params={"file": "first.json.gz"}).status_code == 200
            assert client.get("/", params={"file": "removed.json.gz", "topic": "7"}).status_code == 404
            assert client.get("/", params={"file": "new.json.gz", "topic": "7"}).status_code == 503
            assert client.get("/sitemaps/file.xml", params={"file": "new.json.gz"}).status_code == 503
            assert client.get("/", params={"doc": "New.md"}).status_code == 503
        finally:
            release.set()
        assert _ready(client)["state"] == "ready"
        assert "New fresh text" in client.get("/", params={"file": "first.json.gz", "topic": "7"}).text
        assert client.get("/", params={"file": "new.json.gz", "topic": "7"}).status_code == 200


def test_unreadable_document_is_isolated_and_recovers(tmp_path, monkeypatch):
    config = _isolated_config(tmp_path)
    _bundle(config.helps_dir / "good.json.gz", "Healthy help", ["Healthy text"])
    guide = config.docs_dir / "Guide.md"
    guide.write_text("# Guide\n\nOriginal text", encoding="utf-8")
    with TestClient(create_app(config)) as client:
        _ready(client)
        original = type(guide).read_text
        def unreadable(path, *args, **kwargs):
            if path == guide and not path.stat().st_mode & 0o400:
                raise PermissionError("Document is temporarily unreadable")
            return original(path, *args, **kwargs)
        guide.chmod(0)
        with monkeypatch.context() as patch:
            patch.setattr(type(guide), "read_text", unreadable)
            status = _ready(client)
            assert status["warnings"][0]["kind"] == "doc"
            assert client.get("/", params={"doc": "Guide.md"}).status_code == 503
            assert client.get("/", params={"file": "good.json.gz", "topic": "7"}).status_code == 200
            assert "sitemaps/docs.xml" not in client.get("/sitemap.xml").text
        # Restoring permissions alone changes ctime and retries the same content.
        guide.chmod(0o600)
        assert _ready(client)["warnings"] == []
        assert client.get("/", params={"doc": "Guide.md"}).status_code == 200


def test_database_failure_is_not_misreported_as_a_bad_source(tmp_path, monkeypatch):
    config = _isolated_config(tmp_path)
    _bundle(config.helps_dir / "good.json.gz", "Healthy topic", ["Original text"])
    with TestClient(create_app(config)) as client:
        _ready(client)
        import sqlite3
        def broken_database(*args):
            raise sqlite3.DatabaseError("Database failure")
        monkeypatch.setattr(client.app.state.global_search, "_connect", broken_database)
        status = client.get("/api/search/status").json()
        assert status["state"] == "error" and not status["available"]
        assert status["warnings"] == []
        assert client.get("/sitemap.xml").status_code == 503


def test_first_build_is_temporarily_unavailable_until_a_source_is_committed(tmp_path, monkeypatch):
    config = _isolated_config(tmp_path)
    _bundle(config.helps_dir / "first.json.gz", "First topic", ["Real text"])
    entered = threading.Event()
    release = threading.Event()
    original = GlobalSearchIndex._update_source
    def blocked(self, connection, kind, name, snapshot):
        entered.set()
        assert release.wait(5)
        return original(self, connection, kind, name, snapshot)
    monkeypatch.setattr(GlobalSearchIndex, "_update_source", blocked)
    with TestClient(create_app(config)) as client:
        assert entered.wait(5)
        try:
            status = client.get("/api/search/status").json()
            assert status["state"] == "building" and not status["available"]
            assert client.get("/api/search/global", params={"q": "real"}).status_code == 202
            for url in ("/", "/sitemap.xml", "/?file=first.json.gz&topic=7"):
                response = client.get(url)
                assert response.status_code == 503 and response.headers["retry-after"] == "60"
            assert "tv-bundle-app.js" in client.get("/").text  # Browser UI may still start.
        finally:
            release.set()
        assert _ready(client)["available"]
        assert client.get("/", params={"file": "first.json.gz", "topic": "7"}).status_code == 200
