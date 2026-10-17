"""MIDI writers must stop before the shared download queue is torn down."""

from dataclasses import replace
import json
import threading
from concurrent.futures import CancelledError

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.midi.library import MidiLibrary
from test_midi_library import MIDI


def _library(tmp_path):
    manifest = tmp_path / "midi.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "game", "name": "Game", "pages": ["https://music.test/list"],
        "allowed_hosts": ["music.test"], "extract": {"mode": "anchors"}, "request_delay_seconds": 0,
    }]}))
    return MidiLibrary(tmp_path / "midi", manifest, selection_path=tmp_path / "selection.json")


@pytest.mark.parametrize("operation", ["download", "rebuild", "selection", "index"])
def test_close_waits_for_current_writer_without_starting_a_replacement(tmp_path, monkeypatch, operation):
    library = _library(tmp_path)
    entered, release, closing, closed = (threading.Event() for _ in range(4))
    calls = []

    def fetch(url, *_args):
        calls.append(url)
        if url.endswith(".mid"):
            entered.set()
            assert release.wait(5), "Test failed to release the active transfer"
            return MIDI
        return b'<a href="song.mid">Song</a>'

    monkeypatch.setattr(library, "_fetch", fetch)
    library.start()
    try:
        assert entered.wait(5)
        if operation == "rebuild": library.rebuild()
        elif operation == "selection": library.select_sources(["game"], {})
        elif operation == "index": library.index_source("game")

        def close():
            closing.set()
            library.close()
            closed.set()

        closer = threading.Thread(target=close)
        closer.start()
        assert closing.wait(5)
        assert not closed.wait(0.05)  # A transfer is still writing the active tree.
        assert not library.downloads._closed
    finally:
        release.set()
        library.close()
        if "closer" in locals():
            closer.join(timeout=5)
        library.downloads.close()
    assert closed.is_set() and not library._worker.is_alive()
    assert library._stop.is_set() and calls == ["https://music.test/list", "https://music.test/song.mid"]
    assert not (tmp_path / "backups").exists()
    assert next(library.root.rglob("*.mid")).read_bytes() == MIDI
    for action in (library.rebuild, lambda: library.select_sources([], {}), lambda: library.index_source("game")):
        with pytest.raises(ValueError, match="stopping"):
            action()
    library.start()
    library.run_once()
    assert not library.prioritize("game", "0" * 16)


def test_close_joins_urgent_playback_transfers_too(tmp_path, monkeypatch):
    library = _library(tmp_path)
    source, = library._sources()
    item = {"id": "0" * 16, "source_id": "game", "kind": "midi", "game": "Game",
            "title": "Song", "filename": "song.mid", "url": "https://music.test/song.mid"}
    library._items = [item]
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()

    def download(*_args):
        entered.set()
        assert release.wait(5)
        return False

    monkeypatch.setattr(library, "_download_item", download)
    monkeypatch.setattr(library, "_sync_tracks", lambda: None)
    closer = None
    try:
        assert library.prioritize(source["id"], item["id"])
        assert entered.wait(5)
        closer = threading.Thread(target=lambda: (library.close(), closed.set()))
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        library.close()
        if closer:
            closer.join(timeout=5)
        library.downloads.close()
    assert closed.is_set() and not library._play_tasks


def test_close_cancels_pending_midi_without_waiting_for_an_unrelated_source_transfer(tmp_path, monkeypatch):
    from thelpviewer.server.downloader.transport import read_request
    library = _library(tmp_path)
    busy, release, queued, closed = (threading.Event() for _ in range(4))
    tasks = []

    def unrelated_download():
        busy.set()
        assert release.wait(5)

    unrelated = library.downloads.enqueue(unrelated_download, source="https://music.test/other.zip")
    enqueue = library._queue_download

    def queue(*args, **kwargs):
        task = enqueue(*args, **kwargs)
        tasks.append(task)
        queued.set()
        return task

    class Opener:
        def open(self, *_args, **_kwargs):
            pytest.fail("Cancelled MIDI must not start a transfer")

    def fetch(url, *_args):
        if url.endswith(".mid"):
            return read_request(Opener(), url, 1024)[0]
        return b'<a href="song.mid">Song</a>'

    monkeypatch.setattr(library, "_queue_download", queue)
    monkeypatch.setattr(library, "_fetch", fetch)
    closer = None
    try:
        assert busy.wait(5)
        library.start()
        assert queued.wait(5)
        closer = threading.Thread(target=lambda: (library.close(), closed.set()))
        closer.start()
        assert closed.wait(2), "Shutdown waited for an unrelated source's download"
        with pytest.raises(CancelledError):
            tasks[0].result()
        assert not unrelated.done()
        assert not library.downloads._closed and not list(library.root.rglob("*.mid"))
    finally:
        release.set()
        library.close()
        if closer:
            closer.join(timeout=5)
        unrelated.result(timeout=5)
        library.downloads.close()


def test_app_lifespan_closes_midi_before_shared_queue(tmp_path, monkeypatch):
    manifest = tmp_path / "empty.json"
    manifest.write_text('{"sources": []}')
    config = replace(load_config(), sources_dir=(tmp_path / "var") / 'sources',
        downloads_dir=(tmp_path / "var") / "downloads",
        state_dir=tmp_path / "var", data_dir=tmp_path / "data",
        helps_dir=tmp_path / "helps", midi_sources_path=manifest, dos_config_path=manifest,
        statistics_path=tmp_path / "statistics.sqlite3", dev_auto_login=False)
    app = create_app(config)
    events = []
    close_midi, close_queue = app.state.midi_library.close, app.state.downloads.close

    def midi():
        assert not app.state.downloads._closed
        close_midi()
        events.append("midi")

    def queue():
        assert events == ["midi"]
        close_queue()
        events.append("queue")

    monkeypatch.setattr(app.state.midi_library, "close", midi)
    monkeypatch.setattr(app.state.downloads, "close", queue)
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
    assert events == ["midi", "queue"]


def test_midi_cancelled_after_worker_claim_does_not_enter_the_download(tmp_path, monkeypatch):
    library = _library(tmp_path)
    item = {"id": "0" * 16, "source_id": "game", "kind": "midi", "game": "Game",
            "title": "Song", "filename": "song.mid", "url": "https://music.test/song.mid"}
    library._items = [item]
    report = library.downloads._operation_status
    def claimed(state, phase, **values):
        report(state, phase, **values)
        if state == "running" and phase == "Processing":
            library._stop.set()
    monkeypatch.setattr(library.downloads, "_operation_status", claimed)
    monkeypatch.setattr(library, "_download_item", lambda *_: pytest.fail("Cancelled MIDI started downloading"))
    try:
        assert library.prioritize("game", item["id"])
        with pytest.raises(CancelledError):
            library._play_tasks[("game", item["id"])].result(timeout=5)
        assert library.downloads.snapshot()["items"][0]["state"] == "blocked"
    finally:
        library.close()
        library.downloads.close()
