"""Publish completed DOS packages while other source preparation is still active."""

import errno
import json
from pathlib import Path
import threading
import time
import uuid

import pytest

from thelpviewer.server.dos.paths import DosError, atomic_file
from thelpviewer.server.file_storage import clone_file
from test_dos_package_recipes import zipped
from test_dos_prompt import payload, store_at


@pytest.mark.parametrize("failed", [False, True])
def test_published_package_survives_a_later_download_and_removals_wait(tmp_path, monkeypatch, failed):
    store = store_at(tmp_path)
    manifest = json.loads(store.config_path.read_text())
    manifest["sources"] = [{"id": ident, "title": ident, "url": f"https://{ident}.test/game.zip",
                            "format": "zip", "target": "GAMES/" + ident.upper()}
                           for ident in ("old", "one", "two")]
    store.config_path.write_text(json.dumps(manifest))
    entered, release = threading.Event(), threading.Event()
    calls, errors = [], []
    def fetch(source, *_args, **_kwargs):
        calls.append(source["id"])
        if source["id"] == "two":
            entered.set()
            assert release.wait(10)
            if failed:
                raise OSError("later source unavailable")
        return zipped({"GAME.EXE": source["id"].encode()})
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    store.configure(["old"])
    account = uuid.uuid4().hex
    store.save(account, payload(store, files={"GAMES/SAVE.DAT": b"private"}))
    def configure():
        try:
            store.configure(["one", "two"])
        except DosError as error:
            errors.append(str(error))
    worker = threading.Thread(target=configure)
    try:
        worker.start()
        assert entered.wait(5)
        deadline = time.monotonic() + 5
        while "one" not in store.published_packages() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert worker.is_alive(), "Second transfer must still be blocked during first publication"
        assert store.published_packages() == {"old", "one"}
        assert (store._published_disk / "GAMES/ONE/GAME.EXE").read_bytes() == b"one"
        rows = {row["id"]: row for row in store.downloads.snapshot(private=True)["items"]}
        assert rows["dos:one"]["state"] == "done"
        assert rows["dos:two"]["state"] != "done"
        release.set()
        worker.join(5)
        assert not worker.is_alive()
        assert bool(errors) is failed
        assert store.published_packages() == ({"old", "one"} if failed else {"one", "two"})
        assert store.overlay(account)[1] == {"GAMES/SAVE.DAT": b"private"}
        if failed:
            # A new store recovers the real published checkpoint, not a percentage.
            recovered = type(store)(store.root, store.config_path)
            try:
                assert recovered.published_packages() == {"old", "one"}
            finally:
                recovered.downloads.close()
    finally:
        release.set()
        worker.join(10)
        store.downloads.close()


@pytest.mark.parametrize("fallback", [False, True])
def test_staged_clone_replacement_never_changes_the_published_file(tmp_path, monkeypatch, fallback):
    source, destination = tmp_path / "live", tmp_path / "staged"
    source.write_bytes(b"published")
    if fallback:
        def unsupported(*_args):
            raise OSError(errno.EXDEV, "No cross-device links")
        monkeypatch.setattr("thelpviewer.server.file_storage.os.link", unsupported)
    clone_file(source, destination)
    assert destination.read_bytes() == b"published"
    if not fallback:
        assert source.stat().st_ino == destination.stat().st_ino
    atomic_file(destination, b"replacement")
    assert source.read_bytes() == b"published" and destination.read_bytes() == b"replacement"
