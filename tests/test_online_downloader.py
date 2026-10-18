"""Shared queue, priority, nested pipelines, progress and access boundaries."""

from contextvars import ContextVar
from concurrent.futures import Future
import io
import threading
import time
import zipfile
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.downloader.online import OnlineDownloader, source_key
from thelpviewer.server.downloader.transport import read_request, fetch_bytes, _HTTPSRedirect
from test_server_content import config_for, admin_session


def wait_downloads(downloads):
    deadline = time.monotonic() + 5
    while downloads.snapshot(private=True)["active"] and time.monotonic() < deadline:
        time.sleep(.01)
    assert not downloads.snapshot(private=True)["active"]


def test_pipeline_prefills_required_priority_before_optional_independent_sources():
    downloads = OnlineDownloader()
    downloads.defer_source("https://required.test/tool.zip", 60)
    items = [{"id": ident, "priority": priority, "url": url} for ident, priority, url in [
        ("tool", 0, "https://required.test/tool.zip"),
        ("manager", 0, "https://required.test/manager.zip"),
        ("game", 10, "https://other.test/game.zip"),
        ("another", 10, "https://independent.test/game.zip"),
    ]]
    submitted = []
    def submit(item):
        submitted.append(item["id"])
        future = Future()
        future.set_result(item["id"])
        return future
    stream = downloads.pipeline(items, submit, ordered=True,
        source=lambda item: item["url"], priority=lambda item: item["priority"])
    try:
        item, future = next(stream)
        assert item["id"] == future.result() == "tool"
        assert submitted == ["tool", "manager", "game"]
        assert [item["id"] for item, _future in stream] == ["manager", "game", "another"]
    finally:
        stream.close()
        downloads.close()


def test_processing_is_bounded_without_holding_a_network_source_lane():
    downloads = OnlineDownloader()
    release = threading.Event()
    entered = [threading.Event() for _ in range(4)]
    def work(index):
        entered[index].set()
        assert release.wait(5)
    futures = [downloads.enqueue_processing(lambda index=index: work(index)) for index in range(4)]
    try:
        assert all(event.wait(2) for event in entered[:3]) and not entered[3].is_set()
        assert downloads.enqueue(lambda: "network", source="https://source.test/archive").result(timeout=2) == "network"
        assert downloads.enqueue_processing(lambda: "playback", priority=-10).result(timeout=2) == "playback"
        release.set()
        for future in futures:
            future.result(timeout=2)
    finally:
        release.set()
        downloads.close()


def test_closing_ordered_pipeline_drains_running_work_and_cancels_waiting_work():
    downloads = OnlineDownloader()
    release, closed = threading.Event(), threading.Event()
    entered = threading.Barrier(4)
    tasks = []
    def work():
        entered.wait(timeout=5)
        assert release.wait(5)
    # Keep processors busy so pipeline work remains cancellable in the queue.
    blockers = [downloads.enqueue_processing(work) for _ in range(3)]
    def submit(item):
        task = downloads.enqueue_processing(lambda: item)
        tasks.append(task)
        return task
    stream = downloads.pipeline(range(5), submit, ordered=True)
    try:
        entered.wait(timeout=2)
        next(stream)
        closer = threading.Thread(target=lambda: (stream.close(), closed.set()))
        closer.start()
        assert closed.wait(2), "Cancelled queued Futures must not block pipeline cleanup"
        closer.join(timeout=2)
        assert len(tasks) == 3 and all(task.cancelled() for task in tasks)
    finally:
        release.set()
        stream.close()
        for task in blockers:
            task.result(timeout=2)
        downloads.close()


def test_failed_group_retry_only_reopens_failed_units_and_preserves_other_rows():
    downloads = OnlineDownloader()
    downloads.begin("midi", [{"id": "one", "group": "album", "label": "Album"},
        {"id": "two", "group": "album", "label": "Album"},
        {"id": "other", "group": "another", "label": "Another"}])
    downloads.update("midi", "one", state="done", percent=100)
    for key in ("two", "other"):
        downloads.update("midi", key, state="error", error="offline")
    downloads.finish("midi")
    entered, release = threading.Event(), threading.Event()
    def prepare(group, failed):
        assert group == "album" and failed == ["two"]
        def retry():
            entered.set()
            assert release.wait(5)
            downloads.update("midi", "two", state="done", percent=100, error="")
        return retry
    downloads.register_retry("midi", prepare)
    assert downloads.snapshot()["items"][0]["retryable"]
    downloads.act("midi:album", "retry")
    assert entered.wait(5)
    with pytest.raises(ValueError):
        downloads.act("midi:album", "retry")
    assert downloads.snapshot()["items"][1]["error"] == "offline"
    release.set()
    wait_downloads(downloads)
    assert [row["state"] for row in downloads.snapshot()["items"]] == ["done", "error"]
    downloads.act("midi:another", "remove")
    assert [row["id"] for row in downloads.snapshot()["items"]] == ["midi:album"]
    with pytest.raises(ValueError):
        downloads.act("midi:album", "remove")  # Only failed rows can be removed.
    downloads.close()


def test_blocked_packages_can_be_retried_or_removed_after_restart(tmp_path):
    from thelpviewer.server.jobs import JobStore
    path = tmp_path / "jobs.sqlite3"
    downloads = OnlineDownloader(JobStore(path))
    downloads.begin("dos", [{"id": key, "label": key} for key in ("failed", "retry", "remove")])
    downloads.update("dos", "failed", state="error", error="offline")
    downloads.finish("dos", error="offline")
    downloads.close()
    downloads = OnlineDownloader(JobStore(path))
    def prepare(group, failed):
        assert group == "retry" and failed == ["retry"]
        return lambda: downloads.update("dos", "retry", state="done", percent=100, error="")
    downloads.register_retry("dos", prepare)
    try:
        rows = {row["id"]: row for row in downloads.snapshot(private=True)["items"]}
        assert rows["dos:retry"]["state"] == "blocked" and rows["dos:retry"]["retryable"]
        downloads.act("dos:remove", "remove")
        downloads.act("dos:retry", "retry")
        wait_downloads(downloads)
        rows = {row["id"]: row for row in downloads.snapshot(private=True)["items"]}
        assert rows["dos:retry"]["state"] == "done" and "dos:remove" not in rows
        assert rows["dos:failed"]["state"] == "error"
    finally:
        downloads.close()
    assert "remove" not in JobStore(path).load_queue()["dos"]["items"]


def test_dos_retry_continues_requested_packages_not_only_the_clicked_one(tmp_path, monkeypatch):
    import json
    from test_server_content import join_content_jobs

    config = config_for(tmp_path)
    manifest = json.loads(config.dos_config_path.read_bytes())
    manifest["sources"].append({"id": "three", "title": "Three", "url": "https://packages.test/three.zip",
                                "format": "zip", "target": "GAMES/THREE"})
    config.dos_config_path.write_text(json.dumps(manifest))
    app = create_app(config)
    content, dos, downloads = app.state.content, app.state.dos_prompt, app.state.downloads
    offline = False
    calls = []
    def fetch(source, *_args, **_kwargs):
        calls.append(source["id"])
        if offline and source["id"] == "two":
            raise OSError("offline")
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as output:
            output.writestr("GAME.EXE", source["id"].encode())
        return payload.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    try:
        dos.configure(["one"])
        offline = True
        content.start(dos_packages=["one", "two", "three"])
        join_content_jobs(content)
        assert content.status()["state"] == "error"
        assert not (dos.disk_dir / "GAMES/TWO/GAME.EXE").exists()
        # Exercise Retry even if the original failing row has been removed.
        downloads.act("dos:two", "remove")
        downloads.update("dos", "three", state="blocked", phase="Not started", error="")
        downloads.finish("dos")
        offline = False
        calls.clear()
        downloads.act("dos:three", "retry")
        wait_downloads(downloads)
        join_content_jobs(content)
        assert content.status()["state"] == "ready", content.status()
        for key in ("one", "two", "three"):
            assert (dos.disk_dir / f"GAMES/{key.upper()}/GAME.EXE").read_bytes() == key.encode()
        assert "one" not in calls and "two" in calls
        assert all(row["state"] == "done" and not row["error"]
                   for row in downloads.snapshot(private=True)["items"])
        assert set(json.loads(content.path.read_bytes())["dos_packages"]) == {"one", "two", "three"}
        retry = app.state.jobs.latest("content")
        assert retry["state"] == "done" and set(retry["payload"]["values"]["dos_packages"]) == {"one", "two", "three"}
    finally:
        downloads.close()


def test_retry_validation_and_repeated_failure_leave_a_failed_row():
    downloads = OnlineDownloader()
    downloads.begin("dos", [{"id": "one", "label": "One"}])
    downloads.update("dos", "one", state="error", error="original")
    downloads.finish("dos")
    def reject(*_args):
        raise ValueError("no longer selected")
    downloads.register_retry("dos", reject)
    with pytest.raises(ValueError, match="no longer selected"):
        downloads.act("dos:one", "retry")
    assert downloads.snapshot(private=True)["items"][0]["error"] == "original"
    downloads.register_retry("dos", lambda *_args: lambda: (_ for _ in ()).throw(ValueError("still offline")))
    downloads.act("dos:one", "retry")
    wait_downloads(downloads)
    row = downloads.snapshot(private=True)["items"][0]
    assert row["state"] == "error" and row["error"] == "still offline" and row["retryable"]
    downloads.close()


def test_stale_retry_cannot_finish_or_mark_a_replacement_job_failed():
    downloads = OnlineDownloader()
    downloads.begin("midi", [{"id": "one", "label": "One"}])
    downloads.update("midi", "one", state="error", error="offline")
    downloads.finish("midi")
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    def retry():
        entered.set()
        assert release.wait(5)
        finished.set()
        raise ValueError("old attempt")
    downloads.register_retry("midi", lambda *_args: retry)
    downloads.act("midi:one", "retry")
    assert entered.wait(5)
    downloads.begin("midi", [{"id": "one", "label": "New One"}])
    downloads.update("midi", "one", state="running", phase="New operation")
    release.set()
    assert finished.wait(5)
    deadline = time.monotonic() + 5
    while downloads.retry_in_progress("midi") and time.monotonic() < deadline:
        time.sleep(.01)
    row = downloads.snapshot()["items"][0]
    assert row["state"] == "running" and not row["error"] and downloads.snapshot()["active"]
    downloads.finish("midi")
    downloads.close()


def test_public_midi_action_accepts_configured_https_origin_behind_tls_proxy(tmp_path):
    config = config_for(tmp_path)
    app = create_app(config)
    with TestClient(app, base_url="http://testserver") as client:
        downloads = app.state.downloads
        downloads.begin("midi", [{"id": "provider:album", "label": "Album"}])
        downloads.update("midi", "provider:album", state="error", error="offline")
        downloads.finish("midi")
        response = client.post("/api/downloads/action", json={"id": "midi:provider:album", "action": "remove"},
            headers={"Origin": config.auth_origin})
        assert response.status_code == 202
        assert not downloads.snapshot()["items"]


def test_failed_download_actions_require_origin_and_private_admin_session(tmp_path):
    config = config_for(tmp_path)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        downloads = app.state.downloads
        for kind, key in (("dos", "one"), ("midi", "provider:album"), ("midi", "page")):
            downloads.begin(kind, [{"id": key, "label": key}], replace=False)
            downloads.update(kind, key, state="error", error="offline")
            downloads.finish(kind)
        headers = {"Origin": config.auth_origin}
        assert client.post("/api/downloads/action", json={"id": "dos:one", "action": "remove"}, headers=headers).status_code == 403
        assert client.post("/api/downloads/action", json={"id": "midi:page", "action": "retry"}, headers=headers).status_code == 403
        for bad in ({}, {"Origin": "https://evil.test"}, {**headers, "Sec-Fetch-Site": "cross-site"}):
            assert client.post("/api/downloads/action", json={"id": "midi:provider:album", "action": "remove"}, headers=bad).status_code == 403
        response = client.post("/api/downloads/action", json={"id": "midi:provider:album", "action": "remove"}, headers=headers)
        assert response.status_code == 202 and response.headers["cache-control"] == "no-store"
        admin_session(app, client)
        assert client.post("/api/downloads/action", json={"id": "dos:one", "action": "delete-files"}, headers=headers).status_code == 422
        assert client.post("/api/downloads/action", json={"id": "dos:one", "action": "retry", "url": "https://evil.test"}, headers=headers).status_code == 422
        assert client.post("/api/downloads/action", json={"id": "dos:one", "action": "remove"}, headers=headers).status_code == 202
        assert client.post("/api/downloads/action", json={"id": "dos:unknown", "action": "retry"}, headers=headers).status_code == 409


def test_midi_retry_downloads_only_failed_tracks_of_the_chosen_album(tmp_path, monkeypatch):
    import json
    from thelpviewer.server.midi.library import MidiLibrary
    from test_midi_library import MIDI
    path = tmp_path / "midi.json"
    path.write_text(json.dumps({"sources": [{"id": "source", "name": "Source",
        "pages": ["https://music.test/index"], "allowed_hosts": ["music.test"],
        "extract": {"mode": "anchors"}, "request_delay_seconds": 0}]}))
    selection = tmp_path / "selection.json"
    library = MidiLibrary(tmp_path / "midi", path, selection_path=selection)
    calls = []
    repaired = False
    def fetch(url, *_args):
        calls.append(url)
        if url.endswith("index"):
            return b'<a href="/good.mid">Good</a><a href="/bad.mid">Bad</a><a href="/other.mid">Other</a>'
        if "good.mid" in url or repaired:
            return MIDI
        raise ValueError("offline")
    monkeypatch.setattr(library, "_fetch", fetch)
    library.run_once(sleep=False)
    for item in library._items:
        item["game"] = "Chosen" if "other.mid" not in item["url"] else "Another"
    # The runtime queue now groups the two albums, retaining successful units.
    library.run_once(sleep=False)
    rows = library.downloads.snapshot()["items"]
    target = next(row for row in rows if "Chosen" in row["label"])
    calls.clear(); repaired = True
    library.downloads.act(target["id"], "retry")
    wait_downloads(library.downloads)
    assert calls == ["https://music.test/bad.mid"]
    assert [row["state"] for row in library.downloads.snapshot()["items"]] == ["done", "error"]
    assert library.catalog()["downloaded"] == 2
    selection.write_text('{"sources": [], "albums": {}}')
    other = next(row for row in library.downloads.snapshot()["items"] if row["state"] == "error")
    with pytest.raises(ValueError, match="no longer selected"):
        library.downloads.act(other["id"], "retry")
    assert len(calls) == 1
    library.downloads.close()


def test_dos_retry_preserves_installed_packages_and_private_data(tmp_path, monkeypatch):
    import json
    import zipfile
    from thelpviewer.server.dos.paths import DosError
    config = config_for(tmp_path)
    app = create_app(config)
    calls, fail = [], False
    def fetch(source, _limit, *_args, **_kwargs):
        calls.append(source["id"])
        if fail:
            raise ValueError("offline")
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as output:
            output.writestr("GAME.EXE", source["id"].encode())
        return payload.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    content, dos = app.state.content, app.state.dos_prompt
    content._save_selection({"configured": True, "help_packages": [], "dos_packages": ["two"]})
    dos.configure(["one"])
    fail = True
    with pytest.raises(DosError, match="offline"):
        dos.configure(["two"])  # Failed pending removal must not delete One on retry.
    private = dos.users_dir / "sentinel.dat"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_bytes(b"private saved game")
    selection = content.path.read_bytes()
    app.state.downloads.begin("dos", [{"id": "unrelated", "label": "Unrelated"}], replace=False)
    app.state.downloads.update("dos", "unrelated", state="error", error="another failure")
    app.state.downloads.finish("dos")
    calls.clear(); fail = False
    app.state.downloads.act("dos:two", "retry")
    wait_downloads(app.state.downloads)
    assert calls == ["two"]
    assert dos.files["GAMES/ONE/GAME.EXE"] == b"one" and dos.files["GAMES/TWO/GAME.EXE"] == b"two"
    assert private.read_bytes() == b"private saved game" and content.path.read_bytes() == selection
    rows = {row["id"]: row for row in app.state.downloads.snapshot(private=True)["items"]}
    assert rows["dos:two"]["state"] == "done" and "dos:unrelated" not in rows
    assert private.is_file() and dos.disk_dir.is_dir()
    assert json.loads(dos.installed_path.read_text())["_complete"]
    app.state.downloads.close()


def test_help_retry_rechecks_edition_sources_and_preserves_other_products(tmp_path, monkeypatch):
    from dataclasses import replace
    import importlib
    import zipfile
    import zlib
    from thelpviewer.help_database import HelpDatabaseEntry, load_help_manifest
    from thelpviewer.server.converter.build import build_help_groups
    from thelpviewer.server.downloader.catalog import all_sources, supported_product_keys, SOURCE_RUNNERS
    config = config_for(tmp_path)
    other = config.sources_dir / "FreeDOS HTML Help 1.1.1a" / "HHSTNDRD.ZIP"
    other.parent.mkdir(parents=True)
    with zipfile.ZipFile(other, "w") as output:
        output.writestr("help/index.htm", "<title>Contents</title><p>FreeDOS help</p>")
    build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir)
    published = {path: path.read_bytes() for path in config.helps_dir.rglob("*.json.gz")}
    app = create_app(config)
    content = app.state.content
    content._save_selection({"configured": True, "help_packages": ["helppc:"], "dos_packages": []})
    selection = content.path.read_bytes()
    provider = next(key for key in all_sources() if "helppc" in supported_product_keys(key))
    payload = b"@C language\r\n:ReferenceTopic\r\n%Reference help\r\n"
    # Register this small valid source fixture, not the CRCs of the full real corpus.
    manifest = load_help_manifest()
    entry = HelpDatabaseEntry(crc32=zlib.crc32(payload), filenames=("C.TXT",), title="HelpPC",
        collection="HelpPC 2.10", product_key="helppc")
    monkeypatch.setattr("thelpviewer.server.downloader.service.load_help_manifest", lambda:
        replace(manifest, entries=tuple(item for item in manifest.entries if item.product_key != "helppc") + (entry,)))
    calls = []
    def run(*, product_keys, **_kwargs):
        calls.extend(product_keys)
        path = config.sources_dir / "HelpPC 2.10" / "C.TXT"
        path.parent.mkdir(parents=True)
        path.write_bytes(payload)
        return [path]
    monkeypatch.setattr(importlib.import_module(SOURCE_RUNNERS[provider]), "run", run)
    downloads = app.state.downloads
    downloads.begin("help", [{"id": "helppc:", "group": "helppc:", "label": "HelpPC"},
        {"id": "other", "group": "another", "label": "Another"}])
    for key in ("helppc:", "other"):
        downloads.update("help", key, state="error", error="offline")
    downloads.finish("help")
    downloads.act("help:helppc:", "retry")
    wait_downloads(downloads)
    assert calls == ["helppc"] and content.status()["state"] == "ready", content.status()
    assert (config.helps_dir / "HelpPC 2.10/c.json.gz").is_file()
    assert all(path.read_bytes() == data for path, data in published.items())
    assert content.path.read_bytes() == selection
    assert [row["state"] for row in downloads.snapshot(private=True)["items"]] == ["done", "error"]
    downloads.close()


def test_unkeyed_pipeline_fifo_priority_and_context_without_nested_deadlock():
    downloader = OnlineDownloader()
    entered, release = threading.Event(), threading.Event()
    order, threads = [], []
    value = ContextVar("test_download_context", default="missing")
    def first():
        entered.set()
        assert release.wait(5)
        order.append("first")
    blocker = downloader.enqueue(first)
    assert entered.wait(5)
    def task(name):
        order.append(name)
        threads.append(threading.current_thread().ident)
        return downloader.call(value.get)
    value.set("HELP")
    help_task = downloader.enqueue(lambda: task("help"))
    value.set("DOS")
    dos_task = downloader.enqueue(lambda: task("dos"))
    value.set("MIDI")
    priority = downloader.enqueue(lambda: task("priority-midi"), priority=0)
    release.set()
    blocker.result(timeout=5)
    assert [priority.result(timeout=5), help_task.result(timeout=5), dos_task.result(timeout=5)] == ["MIDI", "HELP", "DOS"]
    assert order == ["first", "priority-midi", "help", "dos"] and len(threads) == 3
    downloader.close()


def test_failed_task_does_not_block_later_tasks():
    downloader = OnlineDownloader()
    failed = downloader.enqueue(lambda: (_ for _ in ()).throw(ValueError("source failed")))
    next_task = downloader.enqueue(lambda: b"next archive")
    with pytest.raises(ValueError, match="source failed"):
        failed.result(timeout=5)
    assert next_task.result(timeout=5) == b"next archive"
    downloader.close()


def test_source_queue_skips_busy_mirrors_without_starting_parallel_downloads():
    downloads = OnlineDownloader()
    entered, release, other = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def first():
        entered.set()
        assert release.wait(5)
    running = downloads.enqueue(first, source="https://archive.org/first.zip")
    assert entered.wait(5)
    waiting = [downloads.enqueue(lambda index=index: calls.append(index),
        source=f"https://ia{index}.us.archive.org/{index}.zip") for index in range(10)]
    independent = downloads.enqueue(other.set, source="https://www.breatharian.eu/program.zip")
    urgent = downloads.enqueue(lambda: calls.append("urgent"), priority=-10,
        source="https://archive.org/selected.mid")
    try:
        assert other.wait(5) and not calls and not urgent.done()
        release.set()
        running.result(5); independent.result(5); urgent.result(5)
        for task in waiting:
            task.result(5)
        assert calls[0] == "urgent" and set(calls) == {*range(10), "urgent"}
        assert source_key("https://archive.org/a") == source_key("https://ia8000.us.archive.org/b")
    finally:
        release.set()
        downloads.close()


def test_source_cooldown_does_not_block_another_source_or_disappear_after_failure():
    downloads = OnlineDownloader()
    completed = threading.Event()
    downloads.defer_source("https://archive.org/failed.zip", .15)
    task = downloads.enqueue(lambda: "retry", source="https://ia801.us.archive.org/other.zip")
    independent = downloads.enqueue(completed.set, source="https://downloads.example.net/item.zip")
    try:
        assert completed.wait(5) and not task.done()
        assert task.result(5) == "retry"
        independent.result(5)
    finally:
        downloads.close()


def test_redirected_response_bodies_share_the_destination_source_limit():
    downloads = OnlineDownloader()
    opened_twice, entered, release = threading.Event(), threading.Event(), threading.Event()
    calls, opened = [], []
    class Response(io.BytesIO):
        headers = {}
        url = "https://ia8000.us.archive.org/download/file.zip"
        def read(self, size):
            if not self.tell():
                calls.append(threading.current_thread().name)
                entered.set()
                assert release.wait(5)
            return super().read(size)
    class Opener:
        def open(self, *_args, **_kwargs):
            opened.append(True)
            if len(opened) == 2:
                opened_twice.set()
            return Response(b"archive")
    try:
        with downloads.activate():
            tasks = [downloads.enqueue(lambda url=url: read_request(Opener(), url, 100), source=url)
                for url in ("https://first.test/download", "https://second.test/download")]
        assert entered.wait(5) and opened_twice.wait(5)
        assert len(calls) == 1
        release.set()
        assert all(task.result(5)[0] == b"archive" for task in tasks)
    finally:
        release.set()
        downloads.close()


def test_regular_downloads_have_a_global_bound_of_three_distinct_sources():
    downloads = OnlineDownloader()
    release, full = threading.Event(), threading.Event()
    active = []
    lock = threading.Lock()
    def operation(index):
        with lock:
            active.append(index)
            if len(active) == 3:
                full.set()
        assert release.wait(5)
    tasks = [downloads.enqueue(lambda index=index: operation(index),
        source=f"https://source{index}.test/file.zip") for index in range(6)]
    try:
        assert full.wait(5) and len(active) == 3
        release.set()
        for task in tasks:
            task.result(5)
    finally:
        release.set()
        downloads.close()


@pytest.mark.parametrize("ordered", [False, True])
def test_preparation_looks_past_a_busy_site_without_reordering_installation(ordered):
    downloads = OnlineDownloader()
    entered, independent, release = (threading.Event() for _ in range(3))
    urls = [f"https://archive.org/{index}.zip" for index in range(10)] + ["https://other.test/file.zip"]
    results, errors = [], []

    def operation(url):
        def transfer():
            if source_key(url) == "archive.org":
                entered.set()
                assert release.wait(5)
            else:
                independent.set()
            return url
        return downloads.call(transfer, source=url)

    def consume():
        try:
            for item, future in downloads.prepare(urls, operation, ordered=ordered, source=lambda url: url):
                results.append((item, future.result(timeout=5)))
        except BaseException as error:
            errors.append(error)

    worker = threading.Thread(target=consume)
    worker.start()
    try:
        assert entered.wait(2)
        assert independent.wait(2), "A later source must start while the first site is still blocked"
        assert downloads.process(lambda: "local validation") == "local validation"
    finally:
        release.set()
        worker.join(timeout=5)
        downloads.close()
    assert not worker.is_alive() and not errors
    assert {item for item, _value in results} == set(urls)
    assert all(item == value for item, value in results)
    if ordered:
        assert [item for item, _value in results] == urls


def test_waiting_help_preparations_do_not_occupy_dos_or_http_workers():
    downloads = OnlineDownloader()
    entered, independent, release = (threading.Event() for _ in range(3))
    errors = []

    def consume(urls):
        def operation(url):
            def transfer():
                if source_key(url) == "archive.org":
                    entered.set()
                    assert release.wait(5)
                else:
                    independent.set()
                return b"archive"
            return downloads.call(transfer, source=url)
        try:
            for _item, future in downloads.prepare(urls, operation, source=lambda url: url):
                assert future.result(timeout=5) == b"archive"
        except BaseException as error:
            errors.append(error)

    help_worker = threading.Thread(target=consume, args=([f"https://archive.org/{index}" for index in range(3)],))
    dos_worker = threading.Thread(target=consume, args=(["https://packages.test/game.zip"],))
    help_worker.start()
    try:
        assert entered.wait(2)
        dos_worker.start()
        assert independent.wait(2), "Three waiting HELP drivers must not block an unrelated DOS source"
        dos_worker.join(timeout=2)
        assert not dos_worker.is_alive()
    finally:
        release.set()
        help_worker.join(timeout=5)
        if dos_worker.ident is not None:
            dos_worker.join(timeout=5)
        downloads.close()
    assert not help_worker.is_alive() and not errors


def test_urgent_playback_promotes_the_same_future_while_a_package_is_running():
    downloads = OnlineDownloader()
    entered, release = threading.Event(), threading.Event()
    context = ContextVar("urgent_test_context", default="background")
    calls = []
    def package():
        entered.set()
        assert release.wait(5)
        return "package finished"
    package_task = downloads.enqueue(package)
    assert entered.wait(5)
    def music():
        calls.append(threading.current_thread().name)
        return downloads.call(context.get)
    pending = downloads.enqueue(music, identity=("midi", "track"))
    context.set("selected song")
    selected = downloads.enqueue(lambda: pytest.fail("Duplicate transfer"), priority=-10, identity=("midi", "track"))
    try:
        assert selected is pending
        assert selected.result(timeout=5) == "selected song"
        assert not package_task.done()
        assert calls == ["thelp-urgent-downloader"]
    finally:
        release.set()
        assert package_task.result(timeout=5) == "package finished"
        downloads.close()


def test_newest_waiting_playback_goes_to_the_front_and_shutdown_cancels_it():
    downloads = OnlineDownloader()
    entered, release = threading.Event(), threading.Event()
    order = []
    def active():
        entered.set()
        assert release.wait(5)
    current = downloads.enqueue(active, priority=-10)
    assert entered.wait(5)
    old = downloads.enqueue(lambda: order.append("older"), priority=-10)
    new = downloads.enqueue(lambda: order.append("newer"), priority=-10)
    release.set()
    current.result(timeout=5); new.result(timeout=5); old.result(timeout=5)
    assert order == ["newer", "older"]
    entered.clear(); release.clear()
    current = downloads.enqueue(active, priority=-10)
    assert entered.wait(5)
    waiting = downloads.enqueue(lambda: pytest.fail("Cancelled urgent task ran"), priority=-10)
    downloads.close()
    assert waiting.cancelled()
    release.set()
    current.result(timeout=5)


def test_shutdown_cancels_waiting_work_not_the_current_transfer():
    downloader = OnlineDownloader()
    entered, release = threading.Event(), threading.Event()
    def active():
        entered.set()
        assert release.wait(5)
        return "finished current request"
    current = downloader.enqueue(active)
    assert entered.wait(5)
    pending = downloader.enqueue(lambda: "must not run")
    downloader.close()
    assert pending.cancelled()
    release.set()
    assert current.result(timeout=5) == "finished current request"


def test_preparation_failure_is_visible_even_without_an_active_file():
    downloads = OnlineDownloader()
    downloads.begin("dos", [])
    downloads.finish("dos", error="Invalid package configuration")
    status = downloads.snapshot(private=True)
    assert status["errors"] == 1 and status["items"][0]["error"] == "Invalid package configuration"
    assert not downloads.snapshot()["items"]
    downloads.close()


def test_completed_files_do_not_claim_finished_publication():
    downloads = OnlineDownloader()
    downloads.begin("dos", [{"id": "one", "label": "One"}])
    downloads.update("dos", "one", state="done", percent=100)
    assert downloads.snapshot(private=True)["percent"] == 99
    downloads.finish("dos")
    assert not downloads.snapshot(private=True)["active"]
    assert downloads.snapshot(private=True)["percent"] == 0
    downloads.close()


def test_batch_percentage_includes_every_pending_and_waiting_package():
    downloads = OnlineDownloader()
    try:
        downloads.begin("dos", [{"id": str(i), "label": f"Package {i}", "byte_progress": False}
                                for i in range(20)])
        downloads.update("dos", "0", state="running", stage="download", stage_percent=90, percent=50)
        status = downloads.snapshot(private=True)
        assert status["active"] and status["percent"] == 2  # 50 / 20, not the active phase's 90%.
        downloads.update("dos", "0", state="waiting", phase="Awaiting publication", stage="install", percent=99)
        downloads.update("dos", "1", state="running", stage="extract", stage_percent=100, percent=75)
        status = downloads.snapshot(private=True)
        assert status["percent"] == 8  # (99 + 75) / 20, with the remaining 18 still queued.
        assert len(status["items"]) == 20
        assert next(row for row in status["items"] if row["id"] == "dos:0")["state"] == "waiting"
    finally:
        downloads.close()


def test_completed_counter_resets_and_a_new_batch_excludes_history():
    downloads = OnlineDownloader()
    try:
        assert downloads.snapshot() == {"active": False, "percent": 0, "errors": 0, "items": []}
        downloads.begin("midi", [{"id": str(i), "label": f"Old song {i}"} for i in range(100)])
        for i in range(100):
            downloads.update("midi", str(i), state="done", percent=100)
        downloads.finish("midi")
        finished = downloads.snapshot()
        assert not finished["active"] and finished["percent"] == 0
        assert len(finished["items"]) == 100 and all(item["percent"] == 100 for item in finished["items"])
        downloads.begin("midi", [{"id": "new", "label": "New song"}], replace=False)
        assert downloads.snapshot()["active"] and downloads.snapshot()["percent"] == 0
        downloads.update("midi", "new", state="running", received=50, bytes_total=100)
        assert downloads.snapshot()["percent"] == 50
        downloads.update("midi", "new", state="done", percent=100)
        downloads.finish("midi")
        assert downloads.snapshot()["percent"] == 0 and len(downloads.snapshot()["items"]) == 101
        # Re-requesting a known identity also starts fresh, not at its previous 100%.
        downloads.begin("midi", [{"id": "new", "label": "New song"}], replace=False)
        assert downloads.snapshot()["percent"] == 0
        assert next(row for row in downloads.snapshot()["items"] if row["id"] == "midi:new")["state"] == "pending"
    finally:
        downloads.close()


def test_public_midi_counter_restarts_while_private_packages_continue():
    downloads = OnlineDownloader()
    try:
        downloads.begin("dos", [{"id": "package", "label": "DOS package"}])
        downloads.update("dos", "package", state="running", percent=50)
        downloads.begin("midi", [{"id": "old", "label": "Old song"}])
        downloads.update("midi", "old", state="done", percent=100)
        downloads.finish("midi")
        assert downloads.snapshot()["percent"] == 0
        assert downloads.snapshot(private=True)["percent"] == 75
        downloads.begin("midi", [{"id": "new", "label": "New song"}], replace=False)
        assert downloads.snapshot()["active"] and downloads.snapshot()["percent"] == 0
        downloads.update("midi", "new", state="running", percent=50)
        assert downloads.snapshot()["percent"] == 50
        downloads.update("dos", "package", state="done", percent=100)
        downloads.finish("dos")
        assert downloads.snapshot(private=True)["active"] and downloads.snapshot(private=True)["percent"] == 75
        downloads.update("midi", "new", state="done", percent=100)
        downloads.finish("midi")
        assert downloads.snapshot(private=True)["percent"] == 0
    finally:
        downloads.close()


def test_retry_counter_counts_only_retried_work_not_successful_history():
    downloads = OnlineDownloader()
    entered, release = threading.Event(), threading.Event()
    try:
        downloads.begin("midi", [{"id": "good", "group": "album", "label": "Album"},
                                  {"id": "failed", "group": "album", "label": "Album"}])
        downloads.update("midi", "good", state="done", percent=100)
        downloads.update("midi", "failed", state="error", error="Offline")
        downloads.finish("midi")
        assert downloads.snapshot()["percent"] == 50
        def retry():
            entered.set()
            assert release.wait(5)
            downloads.update("midi", "failed", state="done", percent=100, error="")
        downloads.register_retry("midi", lambda *_args: retry)
        downloads.act("midi:album", "retry")
        assert entered.wait(5)
        assert downloads.snapshot()["percent"] == 0 and downloads.snapshot()["active"]
        release.set()
        wait_downloads(downloads)
        assert downloads.snapshot()["percent"] == 0 and downloads.snapshot()["items"][0]["percent"] == 100
    finally:
        release.set()
        downloads.close()


def test_cached_package_processing_leaves_network_and_preparation_workers_free(tmp_path, monkeypatch):
    from thelpviewer.server.downloader.packages import download_package, package_cache_path
    downloader = OnlineDownloader()
    calls, workers = [], []
    def fetch(source, limit, progress):
        calls.append(source["url"])
        workers.append(threading.current_thread().name)
        progress(7, 7)
        return b"archive"
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    def process(data, _recipe):
        workers.append(threading.current_thread().name)
        return data.upper()
    source = {"id": "tools", "url": "https://packages.test/file.zip"}
    try:
        for _ in range(2):
            with downloader.activate():
                for _source, future in downloader.prepare([source], lambda source: download_package(source, tmp_path, 1000,
                        on_progress=lambda *_: None, process=process)):
                    result, key = future.result(timeout=5)
            assert result == b"ARCHIVE"
        assert calls == [source["url"]] and (tmp_path / package_cache_path(source)).read_bytes() == b"archive"
        assert len(workers) == 3 and workers[0].startswith("thelp-prepare")
        assert all(name.startswith("thelp-processor") for name in workers[1:])
    finally:
        downloader.close()


def test_shared_progress_groups_albums_and_hides_private_packages():
    downloads = OnlineDownloader()
    downloads.begin("dos", [{"id": "compiler", "label": "Compiler"}])
    downloads.begin("midi", [{"id": "one", "group": "doom", "label": "DOOM"},
                             {"id": "two", "group": "doom", "label": "DOOM"}])
    downloads.update("dos", "compiler", state="running", received=5, bytes_total=10)
    downloads.update("midi", "one", state="done", percent=100)
    public = downloads.snapshot()
    assert public["active"] and public["percent"] == 50
    assert len(public["items"]) == 1 and public["items"][0]["percent"] == 50
    assert public["items"][0]["total"] == 2
    assert len(downloads.snapshot(private=True)["items"]) == 2
    downloads.update("midi", "two", state="error", error="HTTP 429")
    downloads.finish("midi")
    assert not downloads.snapshot()["active"] and downloads.snapshot()["errors"] == 1
    assert downloads.snapshot()["percent"] == 50  # Failed work is not reported as 100% complete.
    downloads.close()


def test_batch_percentage_weights_packages_not_their_number_of_provider_attempts():
    downloads = OnlineDownloader()
    try:
        downloads.begin("help", [{"id": provider, "group": "pascal", "label": "Pascal"}
                                 for provider in ("winworld", "archiveorg", "olddos")])
        downloads.begin("dos", [{"id": "game", "label": "Game"}])
        for provider in ("winworld", "archiveorg", "olddos"):
            downloads.update("help", provider, state="done", percent=100)
        downloads.finish("help")
        assert downloads.snapshot(private=True)["percent"] == 50  # One of two packages, not three of four sources.
        downloads.update("dos", "game", state="running", received=50, bytes_total=100)
        assert downloads.snapshot(private=True)["percent"] == 75
        downloads.update("dos", "game", state="done", percent=100)
        downloads.finish("dos")
        assert downloads.snapshot(private=True)["percent"] == 0
    finally:
        downloads.close()


def test_help_discovery_responses_are_not_the_package_download_percentage():
    from thelpviewer.server.downloader.service import plan_help_downloads
    downloads = OnlineDownloader()
    try:
        plan = plan_help_downloads(["tp"], source_keys=["winworld"], package_ids=["tp:5.5"])
        assert plan
        downloads.begin("help", plan)
        key = plan[0]["id"]
        # Both a small discovery page and a later archive may reach their own
        # Content-Length. Neither completes this multi-request source check.
        for phase, received, total in (("Downloading", 1024, 1024),
                                       ("Rate limited (HTTP 429), retry in 30s", 0, 0),
                                       ("Downloading", 10, 100), ("Downloading", 100, 100)):
            downloads.update("help", key, state="running", phase=phase, received=received, bytes_total=total)
            status = downloads.snapshot(private=True)
            assert status["active"] and status["percent"] == status["items"][0]["percent"] == 0
        downloads.update("help", key, state="done", percent=100)
        assert downloads.snapshot(private=True)["percent"] == 99  # Owner still publishing.
        downloads.finish("help")
        assert downloads.snapshot(private=True)["percent"] == 0
        assert not downloads.snapshot()["items"]  # No private progress exposed.
    finally:
        downloads.close()


def test_explicit_installation_progress_is_not_overwritten_by_response_bytes():
    downloads = OnlineDownloader()
    try:
        downloads.begin("dos", [{"id": "game", "label": "Game", "byte_progress": False}])
        downloads.update("dos", "game", state="running", percent=45)
        downloads.update("dos", "game", received=100, bytes_total=100)
        assert downloads.snapshot(private=True)["percent"] == 45
        downloads.update("dos", "game", percent=80)
        assert downloads.snapshot(private=True)["percent"] == 80
        downloads.begin("midi", [{"id": "track", "label": "Track"}])
        downloads.update("midi", "track", state="running", received=50, bytes_total=100)
        assert downloads.snapshot()["percent"] == 50  # Single-file progress remains byte-based.
        downloads.update("midi", "track", percent=60, received=50, bytes_total=100)
        assert downloads.snapshot()["percent"] == 60  # Explicit owner progress wins.
    finally:
        downloads.close()


def test_dos_apply_does_not_requeue_installed_packages_as_new_completed_work(tmp_path, monkeypatch):
    app = create_app(config_for(tmp_path))
    def fetch(source, _limit, *_args, **_kwargs):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as output:
            output.writestr("GAME.EXE", source["id"].encode())
        return payload.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    dos = app.state.dos_prompt
    try:
        dos.configure(["one"])
        dos.configure(["one", "two"])
        snapshot = dos.downloads.snapshot(private=True)
        assert {row["id"] for row in snapshot["items"]} == {"dos:two"}
        assert snapshot["percent"] == 0 and not snapshot["active"]
        assert dos.files["GAMES/ONE/GAME.EXE"] == b"one" and dos.files["GAMES/TWO/GAME.EXE"] == b"two"
    finally:
        dos.downloads.close()


def test_rejected_source_cannot_make_a_failed_group_or_batch_show_100_percent():
    downloads = OnlineDownloader()
    try:
        downloads.begin("help", [{"id": "source", "group": "pascal", "label": "Pascal"}])
        downloads.update("help", "source", state="error", percent=100, error="Invalid archive")
        downloads.finish("help")
        snapshot = downloads.snapshot(private=True)
        assert not snapshot["active"] and snapshot["errors"] == 1
        assert snapshot["percent"] == snapshot["items"][0]["percent"] == 99
    finally:
        downloads.close()


def test_shared_transfer_is_atomic_and_preserves_previous_cache_on_failure(tmp_path):
    destination = tmp_path / "file.zip"
    destination.write_bytes(b"previous")
    response = io.BytesIO(b"truncated")
    response.headers = {"Content-Length": "100"}
    with pytest.raises(ValueError, match="incomplete"):
        read_request(SimpleNamespace(open=lambda *_args, **_kwargs: response), "https://packages.test/file.zip",
                     1000, destination=destination)
    assert destination.read_bytes() == b"previous" and not list(tmp_path.glob(".download-*"))


def test_midi_uses_common_public_peer_and_host_boundary(monkeypatch):
    def opener(**kwargs):
        assert kwargs["allowed_hosts"] == {"music.test"}
        response = io.BytesIO(b"MThd")
        response.headers = {"Content-Length": "4"}
        return SimpleNamespace(open=lambda *_args, **_kwargs: response)
    monkeypatch.setattr("thelpviewer.server.downloader.transport.create_opener", opener)
    assert fetch_bytes("https://music.test/track.mid", {"music.test"}, 100) == b"MThd"
    with pytest.raises(ValueError, match="configured"):
        fetch_bytes("https://outside.test/track.mid", {"music.test"}, 100)
    from urllib.request import Request
    with pytest.raises(ValueError, match="configured"):
        _HTTPSRedirect(allowed_hosts={"music.test"}).redirect_request(Request("https://music.test/track.mid"),
            None, 302, "Found", {}, "https://outside.test/track.mid")


def test_shared_queue_api_is_read_only_and_admin_scoped(tmp_path):
    config = config_for(tmp_path)
    app = create_app(config)
    assert app.state.downloads is app.state.dos_prompt.downloads is app.state.midi_library.downloads
    with TestClient(app, base_url=config.auth_origin) as client:
        downloads = app.state.downloads
        downloads.begin("dos", [{"id": "compiler", "label": "Compiler"}])
        downloads.begin("midi", [{"id": "song", "label": "DOOM"}])
        response = client.get("/api/downloads")
        assert response.headers["Cache-Control"] == "no-store"
        assert {row["kind"] for row in response.json()["items"]} == {"midi"}
        admin_session(app, client)
        assert {row["kind"] for row in client.get("/api/downloads").json()["items"]} == {"dos", "midi"}
        assert client.post("/api/downloads", json={"url": "https://outside.test"}).status_code == 405


@pytest.mark.parametrize("provider", ["cheater_cz", "slunecnice"])
def test_referer_providers_use_shared_queued_atomic_transfer(tmp_path, monkeypatch, provider):
    import importlib
    from thelpviewer.server.downloader import http
    module = importlib.import_module("thelpviewer.server.downloader." + provider)
    requests, threads, progress = [], [], []
    def open_response(request, **kwargs):
        requests.append(request)
        threads.append(threading.current_thread().name)
        response = io.BytesIO(b"archive")
        response.headers = {"Content-Length": "7"}
        return response
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=open_response))
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    from thelpviewer.server.downloader import service
    from thelpviewer.server.processing import observe_progress
    from functools import partial
    monkeypatch.setattr(service, "ingest_help", lambda source, *_: (
        [source.path] if source.path.read_bytes() == b"archive" else []))
    if provider == "cheater_cz":
        monkeypatch.setattr(module, "get_versions", lambda _: [("Scorpions Cheater 21", "key")])
        monkeypatch.setattr(module, "get_archive_name", lambda *_: "source.zip")
        monkeypatch.setattr(module, "get_download_url", lambda *_: "https://provider.test/source.zip")
        products = ["scorpion"]
    else:
        monkeypatch.setattr(module, "fetch_html", lambda *_: "")
        monkeypatch.setattr(module, "find_download_url", lambda *_: "https://provider.test/source.zip")
        products = ["game-cheater"]
    plans = []
    def process(source, **options):
        plans.append((source, options))
        return service.process_help_input(source, sources_dir=tmp_path / "sources",
            extractor=None, **options)
    with observe_progress(progress.append):
        module.run(products, tmp_path / "downloads", False, process)
    assert len(plans) == 1
    assert requests[0].get_header("Referer") == plans[0][1]["headers"]["Referer"]
    assert plans[0][0].path.read_bytes() == b"archive"
    assert len(threads) == 1 and threads[0].startswith("thelp-online-downloader-")
    assert progress[-1]["phase"] == "Downloaded" and progress[-1]["downloaded_size"] == 7
