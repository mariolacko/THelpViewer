"""HELP processing has priority over the single background index writer."""

import sqlite3
import threading
import time

from fastapi.testclient import TestClient
import pytest

from test_global_search import _bundle, _ready
from test_server_content import admin_session, config_for, wait_job
from thelpviewer.server.app import create_app
from thelpviewer.server.downloader.service import DownloadResult
from thelpviewer.server.search_index import GlobalSearchIndex


def ready(index):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = index.status()
        if status["state"] == "ready":
            return status
        time.sleep(.01)
    raise AssertionError(status)


def test_pause_keeps_old_searchable_data_coalesces_changes_and_rescans_once(tmp_path, monkeypatch):
    helps, state = tmp_path / "helps", tmp_path / "var"
    first, removed = helps / "first.json.gz", helps / "removed.json.gz"
    _bundle(first, "Old", ["Old cached text"])
    _bundle(removed, "Removed", ["Retired body"])
    index = GlobalSearchIndex(helps, state)
    ready(index)
    scans, builds = [], []
    snapshot, build = index._snapshot, index._build
    def scan():
        scans.append(True)
        return snapshot()
    def rebuild(*args):
        builds.append(True)
        build(*args)
    monkeypatch.setattr(index, "_snapshot", scan)
    monkeypatch.setattr(index, "_build", rebuild)
    with index.suspend():
        for title in ("Intermediate", "Final"):
            _bundle(first, title, [title + " unique text"])
            index.ensure_current()
            assert index.status()["state"] == "paused"
        removed.unlink()
        _bundle(helps / "new.json.gz", "New", ["New article"])
        status, rows = index.search("cached")
        assert status["available"] and rows[0]["title"] == "Old"
        with index.suspend():
            index.ensure_current()
        assert index.status()["state"] == "paused"
        assert not scans and not builds
    assert ready(index)["topics"] == 2
    assert len(builds) == 1
    assert index.topic("first.json.gz", "7")["title"] == "Final"
    assert index.topic("new.json.gz", "7")["title"] == "New"
    assert index.topic("removed.json.gz", "7") is None


def test_running_writer_finishes_current_file_then_yields_until_help_finishes(tmp_path, monkeypatch):
    helps = tmp_path / "helps"
    for name in ("a", "b", "c"):
        _bundle(helps / (name + ".json.gz"), name, [name + " body"])
    index = GlobalSearchIndex(helps, tmp_path / "var")
    entered, release_source, processing, release_help = (threading.Event() for _ in range(4))
    calls = []
    update = index._update_source
    def blocked(connection, kind, name, snapshot):
        calls.append(name)
        if name == "a.json.gz":
            entered.set()
            assert release_source.wait(5)
        return update(connection, kind, name, snapshot)
    monkeypatch.setattr(index, "_update_source", blocked)
    index.ensure_current()
    assert entered.wait(5)
    def help_work():
        with index.suspend():
            processing.set()
            assert release_help.wait(5)
    worker = threading.Thread(target=help_work)
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while index.status()["state"] != "paused":
            assert time.monotonic() < deadline
            time.sleep(.01)
        assert not processing.is_set()
        release_source.set()
        assert processing.wait(5)
        assert calls == ["a.json.gz"] and not index._building
        # No SQLite writer/transaction is retained during the pause.
        with sqlite3.connect(index.path, timeout=.1) as connection:
            connection.execute("BEGIN IMMEDIATE")
            assert connection.execute("SELECT file_path FROM files").fetchall() == [("a.json.gz",)]
        _bundle(helps / "b.json.gz", "Newest b", ["Final b body"])
        (helps / "c.json.gz").unlink()
        _bundle(helps / "d.json.gz", "New d", ["Final d body"])
        index.ensure_current()
        assert calls == ["a.json.gz"]
    finally:
        release_source.set()
        release_help.set()
        worker.join(5)
    assert not worker.is_alive()
    assert ready(index)["topics"] == 3
    assert calls == ["a.json.gz", "b.json.gz", "d.json.gz"]
    assert index.topic("b.json.gz", "7")["title"] == "Newest b"


def test_first_index_is_deferred_and_restarts_without_a_request_even_after_error(tmp_path, monkeypatch):
    index = GlobalSearchIndex(tmp_path / "helps", tmp_path / "var")
    started = threading.Event()
    build = index._build
    def rebuild(*args):
        started.set()
        build(*args)
    monkeypatch.setattr(index, "_build", rebuild)
    with pytest.raises(ValueError, match="HELP failed"):
        with index.suspend():
            _bundle(index.helps_dir / "first.json.gz", "First", ["Published body"])
            assert index.status()["state"] == "paused"
            assert not index.path.exists() and not started.is_set()
            assert index.search("body")[1] == []
            raise ValueError("HELP failed")
    assert started.wait(5)
    assert ready(index)["topics"] == 1


@pytest.mark.parametrize("failure", [None, "download", "conversion"])
def test_content_api_pauses_index_through_help_work_and_recovers_on_every_exit(tmp_path, monkeypatch, failure):
    config = config_for(tmp_path)
    _bundle(config.helps_dir / "existing.json.gz", "Published", ["Old searchable body"])
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"bad help" if failure == "conversion" else b"@C\r\n:Reference\r\n%New converted body\r\n")
    config.docs_dir.mkdir()
    app = create_app(config)
    entered, release = threading.Event(), threading.Event()
    def download(*_args, on_ready, **_kwargs):
        assert app.state.global_search.status()["state"] == "paused"
        entered.set()
        assert release.wait(5)
        if failure == "download":
            raise ValueError("HELP download failed")
        on_ready("helppc:")
        return DownloadResult(files=[source])
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    with TestClient(app, base_url=config.auth_origin) as client:
        _ready(client)
        admin_session(app, client)
        try:
            response = client.post("/api/admin/content", json={"help_packages": ["helppc:"]},
                                   headers={"Origin": config.auth_origin})
            assert response.status_code == 202 and entered.wait(5), app.state.content.status()["error"]
            (config.docs_dir / "New.md").write_text("# New document during processing", encoding="utf-8")
            status = client.get("/api/search/status").json()
            assert status["state"] == "paused" and status["available"]
            assert not app.state.global_search._building
            assert client.get("/api/search/global", params={"q": "searchable"}).json()["results"]
            assert client.get("/sitemap.xml").status_code == 200
            assert client.get("/", params={"file": "existing.json.gz", "topic": "7"}).status_code == 200
            response = client.get("/", params={"doc": "New.md"})
            assert response.status_code == 503 and response.headers["retry-after"] == "60"
        finally:
            release.set()
        assert wait_job(client)["state"] == ("error" if failure else "ready")
        assert _ready(client)["documents"] == 1
        assert client.get("/", params={"doc": "New.md"}).status_code == 200
        results = client.get("/api/search/global", params={"q": "converted"}).json()["results"]
        assert bool(results) == (failure is None)


def test_dos_only_work_does_not_pause_index(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    app = create_app(config)
    calls = []
    def configure(*_args, **_kwargs):
        calls.append(True)
        assert app.state.global_search.status()["state"] == "ready"
        app.state.dos_prompt.state = "ready"
    monkeypatch.setattr(app.state.dos_prompt, "configure", configure)
    with TestClient(app, base_url=config.auth_origin) as client:
        _ready(client)
        admin_session(app, client)
        assert client.post("/api/admin/content", json={"dos_packages": ["one"]},
                           headers={"Origin": config.auth_origin}).status_code == 202
        assert wait_job(client)["state"] == "ready" and calls


def test_combined_job_releases_index_after_help_while_dos_is_still_running(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C\r\n:Reference\r\n%Concurrent converted body\r\n")
    app = create_app(config)
    entered, release = threading.Event(), threading.Event()

    def download(*_args, on_ready, **_kwargs):
        assert entered.wait(5)
        assert app.state.global_search.status()["state"] == "paused"
        on_ready("helppc:")
        return DownloadResult(files=[source])

    def configure(*_args, **_kwargs):
        entered.set()
        assert release.wait(5)
        app.state.dos_prompt.state = "ready"

    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    monkeypatch.setattr(app.state.dos_prompt, "configure", configure)
    with TestClient(app, base_url=config.auth_origin) as client:
        _ready(client)
        admin_session(app, client)
        try:
            response = client.post("/api/admin/content", json={"help_packages": ["helppc:"], "dos_packages": ["one"]},
                                   headers={"Origin": config.auth_origin})
            assert response.status_code == 202 and entered.wait(5)
            ready(app.state.global_search)
            assert not release.is_set()
            assert app.state.content.status()["state"] == "building"
            assert (config.helps_dir / "HelpPC 2.10/c.json.gz").is_file()
            assert client.get("/api/search/global", params={"q": "Concurrent"}).json()["results"]
        finally:
            release.set()
        assert wait_job(client)["state"] == "ready"


def test_failed_help_retry_also_holds_and_releases_index_pause(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C\r\n:Reference\r\n%Retry converted body\r\n")
    app = create_app(config)
    calls, entered, release = [], threading.Event(), threading.Event()
    def download(*_args, on_ready=None, **_kwargs):
        calls.append(True)
        assert app.state.global_search.status()["state"] == "paused"
        if len(calls) == 1:
            raise ValueError("First download failed")
        entered.set()
        assert release.wait(5)
        if on_ready:
            on_ready("helppc:")
        return DownloadResult(files=[source])
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    with TestClient(app, base_url=config.auth_origin) as client:
        _ready(client)
        admin_session(app, client)
        assert client.post("/api/admin/content", json={"help_packages": ["helppc:"]},
                           headers={"Origin": config.auth_origin}).status_code == 202
        assert wait_job(client)["state"] == "error"
        _ready(client)
        app.state.downloads.act("help:helppc:", "retry")
        try:
            assert entered.wait(5)
            assert client.get("/api/search/status").json()["state"] == "paused"
        finally:
            release.set()
        assert wait_job(client)["state"] == "ready"
        assert _ready(client)["topics"] == 1
        assert client.get("/api/search/global", params={"q": "converted"}).json()["results"]
