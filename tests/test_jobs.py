"""Durable intent/progress and verified recovery, including a killed process."""

from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import zipfile

from fastapi.testclient import TestClient
import pytest

from test_global_search import _bundle, _ready
from test_server_content import admin_session, config_for, wait_job
from thelpviewer.server.app import create_app
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.downloader.service import DownloadResult
from thelpviewer.server.jobs import JobStore
from thelpviewer.server.search_index import GlobalSearchIndex


def test_job_claims_durable_checkpoints_queue_actions_and_single_owner(tmp_path):
    path = tmp_path / "data/jobs.sqlite3"
    first = JobStore(path)
    first.acquire()
    ident = first.create("content", {"scope": ["help"], "values": {"help_packages": ["helppc:"]}})
    first.claim(ident)
    first.update(ident, "running", {"stage": "convert", "percent": 65})
    output = tmp_path / "output.json.gz"
    output.write_bytes(b"already validated output")
    first.checkpoint_files(ident, "help:helppc:", tmp_path, [output])
    with pytest.raises(ValueError, match="claimed"):
        first.claim(ident)
    other = JobStore(path)
    with pytest.raises(RuntimeError, match="Another server"):
        other.acquire()
    downloads = OnlineDownloader(first)
    downloads.begin("help", [{"id": "helppc:", "label": "HelpPC"}])
    downloads.update("help", "helppc:", state="running", stage="convert", stage_percent=65)
    downloads.begin("midi", [{"id": "broken", "label": "Broken album"}])
    downloads.update("midi", "broken", state="error", error="Invalid MIDI")
    downloads.finish("midi")
    downloads.act("midi:broken", "remove")
    downloads.close()
    first.release()
    other.acquire()
    try:
        job, = other.pending("content")
        assert job["id"] == ident and job["state"] == "interrupted" and job["progress"]["percent"] == 65
        step = other.steps(ident)["help:helppc:"]
        assert other.files_valid(tmp_path, step)
        output.write_bytes(b"damaged")
        assert not other.files_valid(tmp_path, step)
        output.unlink()
        assert not other.files_valid(tmp_path, step)
        restored = OnlineDownloader(other)
        rows = restored.snapshot(private=True)["items"]
        assert len(rows) == 1 and rows[0]["stage"] == "convert" and rows[0]["stage_percent"] == 65
        assert not restored.snapshot(private=True)["active"] and not rows[0]["error"]
        restored.close()
        other.claim(ident)
        assert other.latest("content")["attempts"] == 2
        other.update(ident, "error", error="Actual conversion failure")
        assert other.pending("content") == []
    finally:
        other.release()


def reference_sources(config):
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"@C language\r\n:Reference\r\n%Durable reference body\r\n")
    html = config.sources_dir / "FreeDOS HTML Help 1.1.1a/HHSTNDRD.ZIP"
    html.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(html, "w") as archive:
        archive.writestr("help/index.htm", "<title>FreeDOS</title><p>Durable FreeDOS help</p>")
    return source, html


def test_sigkill_after_first_help_publication_resumes_only_unfinished_edition(tmp_path, monkeypatch):
    # The child never exits its second download. SIGKILL prevents finally blocks
    # from flushing progress, cleaning staging trees or releasing the owner lock.
    code = r'''
import sys, time
from pathlib import Path
from fastapi.testclient import TestClient
from test_server_content import config_for
from test_jobs import reference_sources
from thelpviewer.server.app import create_app
from thelpviewer.server import content
root=Path(sys.argv[1]); config=config_for(root)
source, html=reference_sources(config)
app=create_app(config)
published=app.state.content.on_help_publish
def notify():
    published()
    (root/'published').write_text('ready')
app.state.content.on_help_publish=notify
def download(*args,on_ready,**kwargs):
    on_ready('helppc:')
    while True: time.sleep(.1)
content.download_products=download
with TestClient(app):
    app.state.content.start(help_packages=['helppc:','freedos-help:'])
    while True: time.sleep(.1)
'''
    worker = subprocess.Popen([sys.executable, "-B", "-c", code, str(tmp_path)],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
             "THELP_STATE_DIR": str(tmp_path / "var"), "THELP_DATA_DIR": "",
             "THELP_SOURCES_DIR": str(tmp_path / "sources"), "THELP_DOWNLOADS_DIR": str(tmp_path / "var/downloads"),
             "THELP_HELPS_DIR": str(tmp_path / "helps"), "THELP_DOCS_DIR": str(tmp_path / "docs"),
             "PYTHONPATH": os.pathsep.join([str(Path.cwd() / "tests"), str(Path.cwd())])},
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while not (tmp_path / "published").exists():
            assert worker.poll() is None, worker.communicate()[1].decode()
            assert time.monotonic() < deadline, "First HELP was not published while second download waited"
            time.sleep(.02)
    finally:
        worker.kill()
        worker.communicate(timeout=5)
    config = config_for(tmp_path)
    first = config.helps_dir / "HelpPC 2.10/c.json.gz"
    published_bytes = first.read_bytes()
    before = JobStore(config.persistent_dir / "jobs.sqlite3").latest("content")
    assert before["state"] == "running"
    requests = []
    def download(*_args, package_ids, on_ready, **_kwargs):
        requests.append(package_ids)
        assert package_ids == ["freedos-help:"]
        on_ready(package_ids[0])
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert wait_job(client)["state"] == "ready"
        assert app.state.content._installed_help_packages() == {"helppc:", "freedos-help:"}
        assert first.read_bytes() == published_bytes
        assert requests == [["freedos-help:"]]
        after = app.state.jobs.latest("content")
        assert after["id"] == before["id"] and after["attempts"] == 2 and after["state"] == "done"
        assert app.state.jobs.files_valid(config.helps_dir, app.state.jobs.steps(after["id"])["help:helppc:"])
        assert _ready(client)["topics"] >= 2


@pytest.mark.parametrize("lost", [False, True])
def test_recovery_rechecks_completed_artifacts_not_just_catalog_membership(tmp_path, monkeypatch, lost):
    config = config_for(tmp_path)
    reference_sources(config)
    build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir, package_ids=["helppc:"], keep_packages=["helppc:"])
    first = config.helps_dir / "HelpPC 2.10/c.json.gz"
    app = create_app(config)
    values = {"help_packages": ["helppc:"], "dos_packages": []}
    ident = app.state.jobs.create("content", {"scope": ["help"], "values": values, "configured": True})
    app.state.jobs.checkpoint_files(ident, "help:helppc:", config.helps_dir, [first])
    if lost:
        first.unlink()
    else:
        first.write_bytes(b"not a valid gzip UHF")
    calls = []
    def download(*_args, on_ready, package_ids, **_kwargs):
        calls.append(package_ids)
        on_ready("helppc:")
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert wait_job(client)["state"] == "ready"
        assert calls == [["helppc:"]]
        assert app.state.jobs.files_valid(config.helps_dir, app.state.jobs.steps(ident)["help:helppc:"])


def test_restart_recovers_the_exact_rename_gap_before_backup_migration(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    reference_sources(config)
    build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir, package_ids=["freedos-help:"], keep_packages=["freedos-help:"])
    old = {p.relative_to(config.helps_dir): p.read_bytes() for p in config.helps_dir.rglob("*.json.gz")}
    app = create_app(config)
    ident = app.state.jobs.create("content", {"scope": ["help"], "configured": True,
        "values": {"help_packages": ["helppc:", "freedos-help:"], "dos_packages": []}})
    stage = config.helps_dir.parent / ".helps-build-interrupted"
    stage.mkdir()
    (stage / "partial.json.gz").write_bytes(b"incomplete staged output")
    previous = config.helps_dir.parent / (".helps-previous-" + "a" * 32)
    app.state.jobs.checkpoint(ident, "help-publication", state="running",
        detail={"stage": stage.name, "previous": previous.name})
    config.helps_dir.rename(previous)
    def download(*_args, on_ready, **_kwargs):
        assert all((config.helps_dir / name).read_bytes() == data for name, data in old.items())
        on_ready("helppc:")
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert wait_job(client)["state"] == "ready"
        assert all((config.helps_dir / name).read_bytes() == data for name, data in old.items())
        assert app.state.content._installed_help_packages() == {"helppc:", "freedos-help:"}
        assert not stage.exists()


def test_interrupted_index_resumes_committed_files_and_persists_file_failures(tmp_path, monkeypatch):
    helps, state = tmp_path / "helps", tmp_path / "var"
    for name in ("a", "b", "c"):
        _bundle(helps / (name + ".json.gz"), name, [name + " unique reference"])
    journal = JobStore(tmp_path / "data/jobs.sqlite3")
    journal.acquire()
    index = GlobalSearchIndex(helps, state, journal=journal)
    update = index._update_source
    calls = []
    def stop_after_first(connection, kind, name, snapshot):
        calls.append(name)
        update(connection, kind, name, snapshot)
        if name == "a.json.gz":
            index._stopping = True
    monkeypatch.setattr(index, "_update_source", stop_after_first)
    index.ensure_current()
    index._worker.join(5)
    job = journal.latest("index")
    assert job["state"] == "interrupted" and job["progress"]["processed"] == 1
    with closing(sqlite3.connect(index.path)) as connection:
        assert connection.execute("SELECT file_path FROM files").fetchall() == [("a.json.gz",)]
    journal.release()
    (helps / "b.json.gz").write_bytes(b"broken gzip")
    reopened = JobStore(journal.path)
    reopened.acquire()
    try:
        resumed = GlobalSearchIndex(helps, state, journal=reopened)
        real_update = resumed._update_source
        def record(*args):
            calls.append(args[2])
            return real_update(*args)
        monkeypatch.setattr(resumed, "_update_source", record)
        resumed.ensure_current()
        resumed._worker.join(5)
        assert calls == ["a.json.gz", "b.json.gz", "c.json.gz"]
        assert resumed.status()["state"] == "ready"
        assert resumed.status()["topics"] == 2
        assert reopened.latest("index")["id"] == job["id"]
        assert reopened.latest("index")["state"] == "done"
        resumed.close()
        another = GlobalSearchIndex(helps, state, journal=reopened)
        assert another.file_error("help", "b.json.gz")
        another.ensure_current()
        assert another._worker is None  # Unchanged corrupt input is not retried on every startup.
        _bundle(helps / "b.json.gz", "Fixed", ["Repaired reference"])
        another.ensure_current()
        another._worker.join(5)
        assert another.status()["topics"] == 3
        assert not another.file_error("help", "b.json.gz")
        another.close()
    finally:
        reopened.release()


def test_terminal_content_failure_is_not_replayed_and_pending_job_protects_cache(tmp_path, monkeypatch):
    config = replace(config_for(tmp_path), data_dir=tmp_path / "data")
    app = create_app(config)
    cache = config.downloads_dir / "help/retained.zip"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"cached source")
    values = {"help_packages": ["helppc:"], "dos_packages": []}
    app.state.content._save_selection({**values, "configured": False})
    ident = app.state.jobs.create("content", {"scope": ["help"], "values": values, "configured": False})
    with pytest.raises(ValueError, match="interrupted content jobs"):
        app.state.download_cache.clear(expired_only=True)
    assert cache.read_bytes() == b"cached source"
    app.state.jobs.update(ident, "error", error="Source unavailable")
    def unexpected(*_args, **_kwargs):
        raise AssertionError("Terminal failure was retried without approval")
    monkeypatch.setattr("thelpviewer.server.content.download_products", unexpected)
    with TestClient(app):
        assert app.state.content.status()["state"] == "idle"
        assert app.state.content.choices()["selection"]["help_packages"] == []
        assert app.state.jobs.latest("content")["state"] == "error"


def test_queued_help_and_dos_resume_concurrently_with_real_installation(tmp_path, monkeypatch):
    import io
    config = config_for(tmp_path)
    reference_sources(config)
    app = create_app(config)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("GAME.EXE", b"ready to run")
    calls = []
    entered = {kind: threading.Event() for kind in ("help", "dos")}
    def help_download(*_args, on_ready, **_kwargs):
        calls.append("help")
        entered["help"].set()
        assert entered["dos"].wait(5)
        on_ready("helppc:")
        return DownloadResult()
    def dos_download(*_args, **_kwargs):
        calls.append("dos")
        entered["dos"].set()
        assert entered["help"].wait(5)
        return payload.getvalue()
    monkeypatch.setattr("thelpviewer.server.content.download_products", help_download)
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", dos_download)
    values = {"help_packages": ["helppc:"], "dos_packages": ["two"]}
    for scope in ("help", "dos"):
        app.state.jobs.create("content", {"scope": [scope], "values": values, "configured": False})
    private = config.persistent_dir / "dos/users/retained/SAVE.DAT"
    private.parent.mkdir(parents=True)
    private.write_bytes(b"private save")
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert wait_job(client)["state"] == "ready"
        assert sorted(calls) == ["dos", "help"]
        assert (app.state.dos_prompt.disk_dir / "GAMES/TWO/GAME.EXE").read_bytes() == b"ready to run"
        assert private.read_bytes() == b"private save"
        assert not app.state.jobs.pending("content")
        status = client.get("/api/downloads").json()
        assert status["content_revision"] != "missing"
        assert not status["errors"]


def test_index_failures_survive_other_successful_index_jobs(tmp_path):
    helps = tmp_path / "helps"
    helps.mkdir()
    (helps / "broken.json.gz").write_bytes(b"broken")
    journal = JobStore(tmp_path / "jobs.sqlite3")
    index = GlobalSearchIndex(helps, tmp_path / "var", journal=journal)
    index.ensure_current()
    index._worker.join(5)
    _bundle(helps / "new.json.gz", "New", ["New reference"])
    index.ensure_current()
    index._worker.join(5)
    index.close()
    reopened = GlobalSearchIndex(helps, tmp_path / "var", journal=journal)
    assert reopened.file_error("help", "broken.json.gz")
    reopened.ensure_current()
    assert reopened._worker is None and reopened.status()["topics"] == 1
    reopened.close()


def test_sigkill_during_index_transaction_rolls_back_only_uncommitted_source(tmp_path, monkeypatch):
    helps = tmp_path / "helps"
    for name in ("a", "b", "c"):
        _bundle(helps / (name + ".json.gz"), name, [name + " searchable reference"])
    code = r'''
import sys,time
from pathlib import Path
from thelpviewer.server.jobs import JobStore
from thelpviewer.server.search_index import GlobalSearchIndex
root=Path(sys.argv[1]);journal=JobStore(root/'data/jobs.sqlite3');journal.acquire()
index=GlobalSearchIndex(root/'helps',root/'var',journal=journal)
update=index._update_source
def blocked(connection,kind,name,snapshot):
    if name=='b.json.gz':
        connection.execute('BEGIN IMMEDIATE')
        connection.execute("DELETE FROM topics_fts WHERE file_path='a.json.gz'")
        (root/'uncommitted').write_text('ready')
        while True: time.sleep(.1)
    return update(connection,kind,name,snapshot)
index._update_source=blocked;index.ensure_current()
while True: time.sleep(.1)
'''
    worker = subprocess.Popen([sys.executable, "-B", "-c", code, str(tmp_path)],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "uncommitted").exists():
            assert worker.poll() is None, worker.communicate()[1].decode()
            assert time.monotonic() < deadline
            time.sleep(.02)
    finally:
        worker.kill()
        worker.communicate(timeout=5)
    journal = JobStore(tmp_path / "data/jobs.sqlite3")
    journal.acquire()
    index = GlobalSearchIndex(helps, tmp_path / "var", journal=journal)
    calls, update = [], index._update_source
    def record(connection, kind, name, snapshot):
        calls.append(name)
        update(connection, kind, name, snapshot)
    monkeypatch.setattr(index, "_update_source", record)
    try:
        index.ensure_current()
        index._worker.join(5)
        assert calls == ["b.json.gz", "c.json.gz"]
        assert index.status()["topics"] == 3
        assert index.topic("a.json.gz", "7")["body"] == "a searchable reference"
        assert journal.latest("index")["state"] == "done"
    finally:
        index.close()
        journal.release()


def test_unavailable_job_storage_fails_visibly_without_starting_or_losing_intent(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        def unavailable(*_args):
            raise sqlite3.OperationalError("job storage is read-only")
        with monkeypatch.context() as patch:
            patch.setattr(app.state.jobs, "create", unavailable)
            response = client.post("/api/admin/content", json={"help_packages": ["helppc:"]},
                                   headers={"Origin": config.auth_origin})
            assert response.status_code == 503 and "Job storage is unavailable" in response.json()["detail"]
            assert not app.state.content._jobs
        with monkeypatch.context() as patch:
            patch.setattr(app.state.jobs, "claim", unavailable)
            assert client.post("/api/admin/content", json={"help_packages": ["helppc:"]},
                               headers={"Origin": config.auth_origin}).status_code == 202
            status = wait_job(client)
            assert status["state"] == "error" and "read-only" in status["error"]
        assert app.state.jobs.pending("content")[0]["state"] == "queued"
        assert not app.state.content._installed_help_packages()
        assert not app.state.downloads.snapshot(private=True)["active"]
        assert client.post("/api/admin/content", json={"help_packages": []},
                           headers={"Origin": config.auth_origin}).status_code == 409


def test_explicit_retry_is_durable_before_its_worker_starts(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    reference_sources(config)
    first = create_app(config)
    first.state.content._save_selection({"configured": False, "help_packages": ["helppc:"], "dos_packages": []})
    first.state.downloads.begin("help", [{"id": "helppc:", "label": "HelpPC"}])
    first.state.downloads.update("help", "helppc:", state="error", error="Network unavailable")
    first.state.downloads.finish("help")
    # OnlineDownloader calls this synchronously before creating the Retry thread.
    operation = first.state.content._prepare_retry("help", "helppc:", ["helppc:"])
    assert callable(operation) and not first.state.content._jobs
    queued, = first.state.jobs.pending("content")
    first.state.downloads.close()
    calls = []
    def download(*_args, on_ready, **_kwargs):
        calls.append(True)
        on_ready("helppc:")
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert wait_job(client)["state"] == "ready"
        assert calls == [True] and app.state.content._installed_help_packages() == {"helppc:"}
        assert app.state.jobs.latest("content")["id"] == queued["id"]
