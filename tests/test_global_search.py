"""Server-wide UHF search is incremental and never moves HELP bundles."""

from dataclasses import replace
import gzip
from importlib import import_module
import json
import time
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config


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
    monkeypatch.setattr(import_module("thelpviewer.server.public_pages"), "SITEMAP_TOPIC_PAGE_SIZE", 2)
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
