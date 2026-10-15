"""Administrator MIDI choices persist separately and never erase the download cache."""

from dataclasses import replace
import json
import threading

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.midi.library import MidiLibrary


MIDI = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60MTrk\x00\x00\x00\x04\x00\xff\x2f\x00"


def manifest(tmp_path):
    path = tmp_path / "midi.json"
    path.write_text(json.dumps({"sources": [
        {"id": "one", "name": "First", "pages": ["https://music.test/a", "https://music.test/b"],
         "allowed_hosts": ["music.test"], "extract": {"mode": "anchors"}, "request_delay_seconds": 0},
        {"id": "two", "name": "Second", "enabled": False, "pages": ["https://music.test/second"],
         "allowed_hosts": ["music.test"], "extract": {"mode": "anchors"}, "request_delay_seconds": 0},
    ]}))
    return path


def finish(library):
    library._worker.join(timeout=5)
    assert not library._worker.is_alive()
    assert library.rebuild_status()["state"] == "ready", library.rebuild_status()


def test_midi_choices_persist_resume_disable_and_survive_rebuild(tmp_path, monkeypatch):
    path = manifest(tmp_path)
    original = path.read_bytes()
    selected_path = tmp_path / "data" / "midi-settings.json"
    library = MidiLibrary(tmp_path / "var" / "midi", path, selection_path=selected_path)
    calls = []

    def fetch(url, hosts, limit):
        calls.append(url)
        return MIDI if url.endswith(".mid") else f'<a href="/{url.rsplit("/", 1)[-1]}.mid">Track</a>'.encode()

    monkeypatch.setattr(library, "_fetch", fetch)
    assert [{key: source[key] for key in ("id", "name", "selected")}
            for source in library.source_choices()["sources"]] == [
        {"id": "one", "name": "First", "selected": True},
        {"id": "two", "name": "Second", "selected": False},
    ]
    assert not selected_path.exists() and not calls
    library.run_once(sleep=False)
    cached = {track["file"]: library.file_path(track["source_id"], track["file"].rsplit("/", 1)[-1])
              for track in library.catalog()["tracks"]}
    assert len(cached) == 2
    library.select_sources(["two"], {})
    finish(library)
    assert {track["source_id"] for track in library.catalog()["tracks"]} == {"two"}
    assert all(file.read_bytes() == MIDI for file in cached.values())
    assert library.file_path("one-a", next(iter(cached)).rsplit("/", 1)[-1]) is None
    assert json.loads(selected_path.read_text()) == {"sources": ["two"], "albums": {}}
    resumed = MidiLibrary(library.root, path, selection_path=selected_path)
    assert [source["id"] for source in resumed._sources()] == ["two"]
    for invalid in (["unknown"], ["two", "two"]):
        with pytest.raises(ValueError):
            library.select_sources(invalid, {})
    assert json.loads(selected_path.read_text()) == {"sources": ["two"], "albums": {}}
    library.select_sources([], {})
    finish(library)
    assert library.catalog()["tracks"] == [] and library._sources() == []
    assert all(file.exists() for file in cached.values())
    before = list(calls)
    library.select_sources(["one"], {})
    finish(library)
    assert len(library.catalog()["tracks"]) == 2 and calls == before
    library.rebuild()
    finish(library)
    assert {source["id"] for source in library._sources()} == {"one-a", "one-b"}
    assert path.read_bytes() == original and json.loads(selected_path.read_text()) == {"sources": ["one"], "albums": {}}


def test_source_change_waits_for_old_writer_and_retains_its_final_file(tmp_path, monkeypatch):
    path = manifest(tmp_path)
    library = MidiLibrary(tmp_path / "midi", path, selection_path=tmp_path / "selection.json")
    downloading, release = threading.Event(), threading.Event()

    def fetch(url, hosts, limit):
        if url.endswith(".mid"):
            downloading.set()
            assert release.wait(5)
            return MIDI
        return b'<a href="/old.mid">Old</a>'

    monkeypatch.setattr(library, "_fetch", fetch)
    library.start()
    try:
        assert downloading.wait(5)
        library.select_sources([], {})
        assert library.source_choices()["status"]["state"] == "building"
        assert library.catalog()["state"] == "rebuilding"
        with pytest.raises(ValueError, match="already"):
            library.select_sources(["two"], {})
        with pytest.raises(ValueError, match="already"):
            library.rebuild()
    finally:
        release.set()
        finish(library)
    assert library.catalog()["tracks"] == []
    assert next(library.root.rglob("*.mid")).read_bytes() == MIDI


def test_midi_selection_api_requires_admin_origin_and_explicit_manifest_ids(tmp_path, monkeypatch):
    path = manifest(tmp_path)
    dos = tmp_path / "dos.json"
    dos.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", data_dir=tmp_path / "data",
        helps_dir=tmp_path / "helps", statistics_path=tmp_path / "statistics.sqlite3",
        midi_sources_path=path, dos_config_path=dos, auth_origin="https://accounts.test", dev_auto_login=False)
    monkeypatch.setattr(MidiLibrary, "_fetch", staticmethod(lambda url, hosts, limit:
        MIDI if url.endswith(".mid") else b'<a href="/song.mid">Song</a>'))
    app = create_app(config)
    accounts = app.state.accounts
    accounts.create_user("admin")
    accounts.create_user("member")
    with accounts._connect() as database:
        tokens = {name: new_session(database, ident) for name, ident
                  in database.execute("SELECT username,id FROM accounts").fetchall()}
    with TestClient(app, base_url=config.auth_origin) as client:
        finish(app.state.midi_library)
        endpoint = "/api/admin/midi-sources"
        assert client.get(endpoint).status_code == 403
        assert client.get(endpoint + "/status").status_code == 403
        assert client.post(endpoint + "/two/index", headers={"Origin": config.auth_origin}).status_code == 403
        client.cookies.set("thelp_session", tokens["member"])
        assert client.get(endpoint).status_code == 403
        assert client.get(endpoint + "/status").status_code == 403
        assert client.post(endpoint + "/two/index", headers={"Origin": config.auth_origin}).status_code == 403
        assert client.put(endpoint, json={"sources": [], "albums": {}}, headers={"Origin": config.auth_origin}).status_code == 403
        client.cookies.set("thelp_session", tokens["admin"])
        choices = client.get(endpoint)
        assert choices.status_code == 200 and choices.headers["cache-control"] == "no-store"
        assert len(choices.json()["sources"]) == 2
        status = client.get(endpoint + "/status")
        assert status.status_code == 200 and status.headers["cache-control"] == "no-store"
        for headers in ({}, {"Origin": "https://evil.test"},
                        {"Origin": config.auth_origin, "Host": "evil.test"},
                        {"Origin": config.auth_origin, "Sec-Fetch-Site": "cross-site"}):
            assert client.put(endpoint, json={"sources": [], "albums": {}}, headers=headers).status_code == 403
            assert client.post(endpoint + "/two/index", headers=headers).status_code == 403
        headers = {"Origin": config.auth_origin}
        assert client.post(endpoint + "/unknown/index", headers=headers).status_code == 409
        index = client.post(endpoint + "/two/index", headers=headers)
        assert index.status_code == 202 and index.headers["cache-control"] == "no-store"
        finish(app.state.midi_library)
        indexed = client.get(endpoint).json()["sources"][1]
        assert indexed["indexed"] and indexed["albums"] and not indexed["selected"]
        assert app.state.midi_library.catalog()["tracks"]
        assert all(track["source_id"] != "two" for track in app.state.midi_library.catalog()["tracks"])
        for body in ({"sources": ["unknown"]}, {"sources": ["one", "one"]}):
            assert client.put(endpoint, json={**body, "albums": {}}, headers=headers).status_code == 409
        for body in ({"sources": [1]}, {"sources": "one"}, {"sources": [], "url": "https://evil.test"}):
            assert client.put(endpoint, json={**body, "albums": {}}, headers=headers).status_code == 422
        assert not app.state.midi_library.selection_path.exists()
        response = client.put(endpoint, json={"sources": [], "albums": {}}, headers=headers)
        assert response.status_code == 202 and response.headers["cache-control"] == "no-store"
        finish(app.state.midi_library)
        assert client.get("/api/midi/catalog").json()["tracks"] == []
        assert config.persistent_dir / "midi-settings.json" == app.state.midi_library.selection_path
        assert client.get("/api/admin/settings").json()["dos_user_disk_mb"] == 64
        assert app.state.dos_prompt.state == "idle"


def test_album_index_does_not_enable_downloads_and_album_selection_controls_all_consumers(tmp_path, monkeypatch):
    path = manifest(tmp_path)
    data = json.loads(path.read_text())
    data["sources"][0].update(enabled=False, extract={"mode": "selectors", "item_selector": ".track",
        "link_selector": "a[href]", "game_selector": ".game", "title_selector": "a"})
    path.write_text(json.dumps(data))
    selection_path = tmp_path / "data" / "midi-settings.json"
    library = MidiLibrary(tmp_path / "var" / "midi", path, selection_path=selection_path)
    calls = []
    pages = {
        "https://music.test/a": b'<div class="track"><span class="game">Doom</span><a href="/doom1.mid">One</a></div>'
            b'<div class="track"><span class="game">Quake</span><a href="/quake.mid">Quake</a></div>',
        "https://music.test/b": b'<div class="track"><span class="game">Doom</span><a href="/doom2.mid">Two</a></div>',
    }
    def fetch(url, hosts, limit):
        calls.append(url)
        return MIDI if url.endswith(".mid") else pages[url]
    monkeypatch.setattr(library, "_fetch", fetch)
    assert library.source_choices()["sources"][0]["albums"] == [] and not calls
    library.index_source("one")
    finish(library)
    assert calls == list(pages) and not list(library.root.rglob("*.mid"))
    assert not selection_path.exists() and library.catalog()["tracks"] == []
    source = library.source_choices()["sources"][0]
    assert source["indexed"] and not source["selected"]
    assert [album["name"] for album in source["albums"]] == ["Doom", "Quake"]
    doom, quake = [album["id"] for album in source["albums"]]
    for invalid in ({"unknown": []}, {"one": ["not-an-album"]}, {"one": [doom, doom]}):
        with pytest.raises(ValueError, match="album"):
            library.select_sources(["one"], invalid)
    assert not selection_path.exists()
    library.select_sources(["one"], {"one": [doom]})
    finish(library)
    assert {track["game"] for track in library.catalog()["tracks"]} == {"Doom"}
    assert len(library.catalog()["tracks"]) == 2
    assert not any(url.endswith("/quake.mid") for url in calls)
    item = next(item for item in library._items if item["game"] == "Quake")
    assert not library.prioritize(item["source_id"], item["id"])
    library.select_sources(["one"], {"one": None})
    finish(library)
    cached = library.file_path(item["source_id"], item["filename"])
    assert cached and cached.read_bytes() == MIDI
    descriptor = next(source for source in library._sources() if source["id"] == item["source_id"])
    library._save_cover(descriptor, "Quake", bytes.fromhex("89504e470d0a1a0a") + b"image", ".png", "https://music.test/cover.png")
    cover = library._covers[(item["source_id"], "Quake")]
    assert library.cover_path(item["source_id"], cover)
    library.select_sources(["one"], {"one": [doom]})
    finish(library)
    assert library.file_path(item["source_id"], item["filename"]) is None
    assert library.cover_path(item["source_id"], cover) is None
    assert cached.is_file() and (library.root / "covers" / cover).is_file()
    resumed = MidiLibrary(library.root, path, selection_path=selection_path)
    assert {track["game"] for track in resumed.catalog()["tracks"]} == {"Doom"}
    before = calls.count("https://music.test/quake.mid")
    library.rebuild()
    finish(library)
    assert calls.count("https://music.test/quake.mid") == before
    assert json.loads(selection_path.read_text())["albums"] == {"one": [doom]}


def test_failed_album_index_does_not_mark_the_page_complete_or_change_selection(tmp_path, monkeypatch):
    path = manifest(tmp_path)
    data = json.loads(path.read_text())
    data["sources"][0]["enabled"] = False
    path.write_text(json.dumps(data))
    library = MidiLibrary(tmp_path / "midi", path, selection_path=tmp_path / "settings.json")
    calls = []
    monkeypatch.setattr(library, "_fetch", lambda url, *_args: (calls.append(url) or b"<p>No songs</p>"))
    library.index_source("two")
    library._worker.join(timeout=5)
    assert not library._worker.is_alive()
    assert calls == ["https://music.test/second"]
    assert library.rebuild_status()["state"] == "error"
    assert "No MIDI/ZIP links" in library.rebuild_status()["error"]
    assert not library.source_choices()["sources"][1]["indexed"]
    assert not library.selection_path.exists()
    monkeypatch.setattr(library, "_fetch", lambda url, *_args: (calls.append(url) or b'<a href="/song.mid">Song</a>'))
    library.index_source("two")
    finish(library)
    assert calls == ["https://music.test/second"] * 2
    assert library.source_choices()["sources"][1]["indexed"] and library.catalog()["tracks"] == []
