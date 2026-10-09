"""Local rebuilds replace only their exact scope and quiesce old writers."""

import base64
from dataclasses import replace
import io
import json
from pathlib import Path
import threading
import uuid
import zipfile

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.dos_prompt import DosError, DosPromptStore
from thelpviewer.server.midi_library import MidiLibrary
from test_midi_library import MIDI


def test_dos_rebuild_recreates_base_preserves_private_files_and_download_cache(tmp_path):
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [], "files": [{"path": "OLD.TXT", "text": ["original"]}]}))
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.prepare()
    assert store.state == "ready"
    account = uuid.uuid4().hex
    store.save(account, {"base_id": store.base_id, "revision": 0,
        "files": {"SAVE.DAT": base64.b64encode(b"private save").decode()},
        "deleted": ["OLD.TXT"], "directories": []})
    (store.root / "downloads").mkdir()
    cached = store.root / "downloads" / "cached-archive"
    cached.write_bytes(b"keep source cache")
    manifest.write_text(json.dumps({"sources": [], "files": [{"path": "NEW.TXT", "text": ["new configuration"]}]}))
    store.rebuild()
    store._worker.join(timeout=5)
    assert not store._worker.is_alive()
    assert store.state == "ready"
    assert "OLD.TXT" not in store.files
    assert store.files["NEW.TXT"] == b"new configuration\r\n"
    assert cached.read_bytes() == b"keep source cache"
    assert (tmp_path / store.backup / "c" / "OLD.TXT").read_bytes() == b"original\r\n"
    with zipfile.ZipFile(io.BytesIO(store.bundle(account)[0])) as archive:
        assert archive.read("drive_c/SAVE.DAT") == b"private save"
    assert store.overlay(account)[0] == 1  # Private revision/database was not reset.
    store.rebuild()
    store._worker.join(timeout=5)
    assert store.state == "ready"  # A second rebuild gets its own recoverable backup.


def test_dos_rebuild_rejects_active_preparation_and_symlink_base(tmp_path):
    manifest = tmp_path / "dos.json"
    manifest.write_text('{"sources": []}')
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.state = "building"
    with pytest.raises(DosError, match="already"):
        store.rebuild()
    store.state = "ready"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("do not move")
    store.root.mkdir()
    (store.root / "base").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic"):
        store.rebuild()
    assert (outside / "keep").read_text() == "do not move"


def test_midi_rebuild_stops_old_writer_before_archive_and_reindexes_sources(tmp_path, monkeypatch):
    manifest = tmp_path / "midi.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "game", "name": "Game", "pages": ["https://music.test/list"],
        "allowed_hosts": ["music.test"], "extract": {"mode": "anchors"}, "request_delay_seconds": 0,
    }]}))
    library = MidiLibrary(tmp_path / "midi", manifest)
    old_in_flight, release_old, new_index = threading.Event(), threading.Event(), threading.Event()
    fetched = []

    def fetch(url, hosts, limit):
        fetched.append(url)
        if url.endswith("/list"):
            name = "new.mid" if new_index.is_set() else "old.mid"
            return f'<a href="/{name}">{name}</a>'.encode()
        if url.endswith("/old.mid"):
            old_in_flight.set()
            assert release_old.wait(5), "Test did not release the old downloader"
        return MIDI

    monkeypatch.setattr(library, "_fetch", fetch)
    (library.root / "covers").mkdir()
    (library.root / "covers" / "old-cover.png").write_bytes(b"old cover")
    library.start()
    try:
        assert old_in_flight.wait(5)
        new_index.set()
        library.rebuild()
        assert library.rebuild_status()["state"] == "building"
        assert library.rebuild_status()["percent"] == 0
        assert library.catalog()["state"] == "rebuilding"
        assert (library.root / "covers" / "old-cover.png").exists()
        assert not (tmp_path / "backups").exists()  # Old writer still owns the active tree.
        with pytest.raises(ValueError, match="already"):
            library.rebuild()
    finally:
        release_old.set()
        library._worker.join(timeout=10)
    assert not library._worker.is_alive()
    status = library.rebuild_status()
    assert status["state"] == "ready" and status["percent"] == 100
    assert not (library.root / "covers" / "old-cover.png").exists()
    backup = tmp_path / status["backup"]
    assert (backup / "covers" / "old-cover.png").read_bytes() == b"old cover"
    assert list((backup / "game").glob("*old.mid"))  # Final old write went into the archived generation.
    tracks = library.catalog()["tracks"]
    assert len(tracks) == 1 and tracks[0]["file"].endswith("new.mid") and tracks[0]["available"]
    assert fetched.count("https://music.test/list") == 2


def test_rebuild_routes_require_local_mode_admin_origin_and_explicit_post(tmp_path):
    manifest = tmp_path / "empty.json"
    manifest.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
        dos_config_path=manifest, midi_sources_path=manifest, auth_origin="http://localhost:5448",
        public_base_url="", dev_auto_login=True, statistics_path=tmp_path / "var" / "statistics.sqlite3")
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.post("/api/admin/rebuild/dos", headers={"Origin": config.auth_origin}).status_code == 403
        client.get("/api/auth/session")
        assert client.get("/api/admin/rebuild/dos").json()["state"] == "idle"
        assert app.state.dos_prompt._worker is None  # GET is not a destructive/preparation trigger.
        for resource in ("dos", "midi"):
            assert client.post(f"/api/admin/rebuild/{resource}").status_code == 403
            assert client.post(f"/api/admin/rebuild/{resource}", headers={"Origin": "https://evil.test"}).status_code == 403
            assert client.post(f"/api/admin/rebuild/{resource}", headers={"Origin": config.auth_origin, "X-Forwarded-For": "127.0.0.1"}).status_code == 403
            result = client.post(f"/api/admin/rebuild/{resource}", headers={"Origin": config.auth_origin})
            assert result.status_code == 202 and result.headers["cache-control"] == "no-store"
            store = app.state.dos_prompt if resource == "dos" else app.state.midi_library
            store._worker.join(timeout=5)
            assert client.get(f"/api/admin/rebuild/{resource}").json()["state"] == "ready"
        assert client.post("/api/admin/rebuild/unknown", headers={"Origin": config.auth_origin}).status_code == 404
        accounts = app.state.accounts
        accounts.create_user("member")
        with accounts._connect() as database:
            ident = database.execute("SELECT id FROM accounts WHERE username='member'").fetchone()[0]
            token = accounts._new_session(database, ident)
        client.cookies.set("thelp_session", token)
        assert client.post("/api/admin/rebuild/dos", headers={"Origin": config.auth_origin}).status_code == 403

    production = create_app(replace(config, dev_auto_login=False))
    with TestClient(production, base_url=config.auth_origin) as client:
        for resource in ("dos", "midi"):
            assert client.get(f"/api/admin/rebuild/{resource}").status_code == 404
            assert client.post(f"/api/admin/rebuild/{resource}", headers={"Origin": config.auth_origin}).status_code == 404
