import io
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from thelpviewer.server.midi_library import MidiIndexParser, MidiLibrary
from thelpviewer.server.routes.midi import create_midi_router


MIDI = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60MTrk\x00\x00\x00\x04\x00\xff\x2f\x00"
PNG = bytes.fromhex("89504e470d0a1a0a") + b"test cover"


def test_default_midi_manifest_pages_preserve_source_ids(tmp_path):
    manifest = Path("thelpviewer/midi-sources.json")
    configured = json.loads(manifest.read_text(encoding="utf-8"))["sources"]
    assert all(isinstance(source["pages"], list) and source["pages"] for source in configured)
    library = MidiLibrary(tmp_path / "midi", manifest)
    sources = library._sources()
    assert [source["index_url"] for source in sources] == [
        page for source in configured if source.get("enabled") is not False for page in source["pages"]
    ]
    assert next(source for source in sources if source["index_url"].endswith("game-midi-dos-d/"))["id"] == "karlsitretro-dos-d"
    assert all("pages" not in source for source in sources)


@pytest.mark.parametrize("pages", [None, [], "https://music.example/list", [1], ["https://music.example/list", None]])
def test_midi_pages_must_be_a_nonempty_url_list(tmp_path, pages):
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "direct", "name": "Direct", "pages": pages,
        "allowed_hosts": ["music.example"], "extract": {"mode": "anchors"},
    }]}), encoding="utf-8")
    library = MidiLibrary(tmp_path / "midi", manifest)
    with pytest.raises(ValueError, match="nonempty pages list"):
        library._sources()


def test_html_extractors_use_only_json_rules():
    rows = MidiIndexParser({
        "mode": "table_rows", "group_row_class": "gameheader", "group_cell": 0,
        "author_cell": 2, "href_pattern": r"\.mid$",
    })
    rows.feed('<tr class="gameheader"><td>Doom</td></tr><tr><td><a href="e1.mid">At Doom Gate</a>'
              '<td>123 bytes<td>Bobby Prince</tr>')
    assert rows.finish() == [{
        "href": "e1.mid", "game": "Doom", "title": "At Doom Gate", "sequencer": "Bobby Prince",
    }]

    archives = MidiIndexParser({
        "mode": "download_then_heading", "download_link_text": "Download",
        "game_heading_tag": "h5", "game_prefix": "Game:", "href_pattern": r"\.zip$",
    })
    archives.feed('<a href="/midi/Doom.zip">Download</a><h5><strong>Game: Doom</strong></h5>')
    assert archives.finish()[0]["game"] == "Doom"

    anchors = MidiIndexParser({"mode": "anchors", "href_pattern": r"\.midi?$"})
    anchors.feed('<a href="one.mid">One</a><a href="two.zip">Two</a>')
    assert [item["title"] for item in anchors.finish()] == ["One"]

    selectors = MidiIndexParser({
        "mode": "selectors", "item_selector": ".track", "link_selector": "a[href]",
        "game_selector": ".game", "title_selector": ".song",
        "sequencer_selector": ".arranger", "href_pattern": r"\.mid$",
    })
    selectors.feed('<div class="track"><strong class="game">Doom</strong>'
                   '<a href="one.mid"><span class="song">E1M1</span></a>'
                   '<em class="arranger">Bobby Prince</em></div>')
    assert selectors.finish() == [{
        "href": "one.mid", "game": "Doom", "title": "E1M1", "sequencer": "Bobby Prince",
    }]


def test_configured_midi_and_zip_sources_download_resume_and_serve(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.json"
    sources = [
        {"id": "direct", "name": "Direct", "pages": ["https://music.example/list"],
         "allowed_hosts": ["music.example"], "extract": {"mode": "anchors", "href_pattern": r"\.mid$"}},
        {"id": "archive", "name": "Archive", "pages": ["https://zip.example/list"],
         "allowed_hosts": ["zip.example"], "extract": {
             "mode": "download_then_heading", "download_link_text": "Download",
             "game_heading_tag": "h5", "game_prefix": "Game:", "href_pattern": r"\.zip$",
         }, "cover": {"mode": "zip_image", "extensions": [".png"]}},
    ]
    manifest.write_text(json.dumps({"sources": sources}), encoding="utf-8")
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("Game/Title.mid", MIDI)
        archive.writestr("Game/Other.mid", MIDI)
        archive.writestr("Game/Cover.png", PNG)
        archive.writestr("Game/ignore.txt", "not a track")
    responses = {
        "https://music.example/list": b'<a href="song.mid">Song</a>',
        "https://music.example/song.mid": MIDI,
        "https://zip.example/list": b'<a href="game.zip">Download</a><h5>Game: Test Game</h5>',
        "https://zip.example/game.zip": archive_buffer.getvalue(),
    }
    calls = []

    def fetch(url, hosts, limit):
        calls.append(url)
        assert url.split("/")[2] in hosts
        assert len(responses[url]) <= limit
        return responses[url]

    library = MidiLibrary(tmp_path / "midi", manifest)
    monkeypatch.setattr(library, "_fetch", fetch)
    library.run_once(sleep=False)
    catalog = library.catalog()
    assert catalog["state"] == "ready"
    assert catalog["downloaded"] == catalog["total"] == 3
    assert len(catalog["sources"]) == 2
    assert len([track for track in catalog["tracks"] if track["cover"]]) == 2

    app = FastAPI()
    app.include_router(create_midi_router(library))
    client = TestClient(app)
    assert client.get("/api/midi/catalog").json()["downloaded"] == 3
    assert client.get(catalog["tracks"][0]["file"]).content == MIDI
    assert client.get(next(track["cover"] for track in catalog["tracks"] if track["cover"])).content == PNG
    assert client.get("/api/midi/files/direct/../library.sqlite3").status_code == 404

    with sqlite3.connect(tmp_path / "midi" / "library.sqlite3") as database:
        assert database.execute("SELECT count(*) FROM midi_index").fetchone()[0] == 2
        assert database.execute("SELECT count(*) FROM midi_covers").fetchone()[0] == 1
        assert database.execute("SELECT count(*) FROM midi_tracks").fetchone()[0] == 3
        assert database.execute("SELECT count(*) FROM midi_tracks WHERE cover_filename != ''").fetchone()[0] == 2

    reloaded = MidiLibrary(tmp_path / "midi", manifest)
    monkeypatch.setattr(reloaded, "_fetch", fetch)
    reloaded.run_once(sleep=False)
    assert reloaded.catalog()["downloaded"] == 3
    assert len(calls) == 4

    sources.append({"id": "another", "name": "Another", "pages": ["https://new.example/list"],
                    "allowed_hosts": ["new.example"],
                    "extract": {"mode": "selectors", "item_selector": ".track",
                                "game_selector": ".game", "href_pattern": r"\.mid$"}})
    manifest.write_text(json.dumps({"sources": sources}), encoding="utf-8")
    responses["https://new.example/list"] = (
        b'<div class="track"><strong class="game">New Game</strong>'
        b'<a href="new.mid">New game tune</a></div>'
    )
    responses["https://new.example/new.mid"] = MIDI
    reloaded.run_once(sleep=False)
    assert reloaded.catalog()["downloaded"] == 4
    assert reloaded.catalog()["tracks"][-1]["game"] == "New Game"
    with sqlite3.connect(tmp_path / "midi" / "library.sqlite3") as database:
        assert database.execute("SELECT count(*) FROM midi_tracks").fetchone()[0] == 4
    assert calls[-2:] == ["https://new.example/list", "https://new.example/new.mid"]


def test_pending_tracks_can_jump_ahead_of_the_background_queue(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.json"
    source = {"id": "direct", "name": "Direct", "pages": ["https://music.example/list"],
              "allowed_hosts": ["music.example"],
              "extract": {"mode": "anchors", "href_pattern": r"\.mid$"}}
    manifest.write_text(json.dumps({"sources": [source]}), encoding="utf-8")
    responses = {"https://music.example/list": (
        b'<a href="one.mid">One</a><a href="two.mid">Two</a><a href="three.mid">Three</a>'
    )}
    responses.update({f"https://music.example/{name}.mid": MIDI for name in ("one", "two", "three")})
    fetched = []

    def fetch(url, hosts, limit):
        fetched.append(url)
        return responses[url]

    library = MidiLibrary(tmp_path / "midi", manifest)
    monkeypatch.setattr(library, "_fetch", fetch)
    library._items = library._index_source(library._sources()[0])
    library._save_catalog()
    pending = library.catalog()
    assert pending["downloaded"] == 0
    assert pending["total"] == 3
    assert all(not track["available"] and not track["file"] for track in pending["tracks"])
    monkeypatch.setattr(library, "start", lambda: None)
    original_download = library._download_item

    def download(source, item):
        if item["title"] == "One":
            assert library.prioritize("direct", library._items[2]["id"])
        return original_download(source, item)

    monkeypatch.setattr(library, "_download_item", download)
    app = FastAPI()
    app.include_router(create_midi_router(library))
    client = TestClient(app)
    assert client.post("/api/midi/priority/direct/not-an-id").status_code == 404
    library.run_once(sleep=False)
    assert fetched[1:] == ["https://music.example/one.mid", "https://music.example/three.mid",
                           "https://music.example/two.mid"]
    assert library.catalog()["downloaded"] == 3
    assert client.post(f"/api/midi/priority/direct/{library._items[0]['id']}").json() == {"queued": True}


def test_pages_add_letters_without_redownloading_existing_page(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.json"
    rules = {"mode": "download_then_heading", "download_link_text": "Download",
             "game_heading_tag": "h5", "game_prefix": "Game:", "href_pattern": r"\.zip$"}
    old_source = {"id": "retro-dos-d", "name": "Retro DOS D",
                  "pages": ["https://music.example/d/"], "allowed_hosts": ["music.example"],
                  "extract": rules, "cover": {"mode": "zip_image", "extensions": [".png"]}}
    manifest.write_text(json.dumps({"sources": [old_source]}), encoding="utf-8")
    archives = {}
    for letter in ("d", "w"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(f"{letter}/Theme.mid", MIDI)
            archive.writestr(f"{letter}/Cover.png", PNG)
        archives[letter] = buffer.getvalue()
    responses = {
        "https://music.example/d/": b'<a href="d.zip">Download</a><h5>Game: Dune</h5>',
        "https://music.example/w/": b'<a href="w.zip">Download</a><h5>Game: Wolfenstein 3D</h5>',
        "https://music.example/d/d.zip": archives["d"],
        "https://music.example/w/w.zip": archives["w"],
    }
    calls = []

    def fetch(url, hosts, limit):
        calls.append(url)
        return responses[url]

    library = MidiLibrary(tmp_path / "midi", manifest)
    monkeypatch.setattr(library, "_fetch", fetch)
    library.run_once(sleep=False)
    old_track = library.catalog()["tracks"][0]
    assert old_track["source_id"] == "retro-dos-d"

    manifest.write_text(json.dumps({"sources": [{
        "id": "retro-dos", "name": "Retro DOS", "pages": [
            "https://music.example/d/", "https://music.example/w/"],
        "allowed_hosts": ["music.example"], "extract": rules,
        "cover": {"mode": "zip_image", "extensions": [".png"]},
    }]}), encoding="utf-8")
    reloaded = MidiLibrary(tmp_path / "midi", manifest)
    monkeypatch.setattr(reloaded, "_fetch", fetch)
    reloaded.run_once(sleep=False)
    catalog = reloaded.catalog()
    assert catalog["state"] == "ready"
    assert catalog["downloaded"] == catalog["total"] == 2
    assert {source["id"] for source in catalog["sources"]} == {"retro-dos-d", "retro-dos-w"}
    assert next(track for track in catalog["tracks"] if track["game"] == "Dune")["file"] == old_track["file"]
    assert next(track for track in catalog["tracks"] if track["game"] == "Wolfenstein 3D")["cover"]
    assert calls == ["https://music.example/d/", "https://music.example/d/d.zip",
                     "https://music.example/w/", "https://music.example/w/w.zip"]


def test_page_ids_come_from_urls_without_configured_letter_keys(tmp_path):
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "retro-dos", "name": "Retro DOS",
        "pages": [
            "https://music.example/game-midi-dos/",
            "https://music.example/game_midi_dos_a/",
            "https://music.example/game-midi-dos-d/",
        ],
        "allowed_hosts": ["music.example"], "extract": {"mode": "anchors"},
    }]}), encoding="utf-8")
    library = MidiLibrary(tmp_path / "midi", manifest)
    assert [source["id"] for source in library._sources()] == [
        "retro-dos-0", "retro-dos-a", "retro-dos-d",
    ]


def test_disabled_midi_source_is_not_indexed(tmp_path, monkeypatch):
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [
        {"id": "disabled", "name": "Disabled", "enabled": False,
         "pages": ["https://old.example/list"], "allowed_hosts": ["old.example"],
         "extract": {"mode": "anchors"}},
        {"id": "active", "name": "Active", "pages": ["https://new.example/list"],
         "allowed_hosts": ["new.example"], "extract": {"mode": "anchors"}},
    ]}), encoding="utf-8")
    calls = []

    def fetch(url, hosts, limit):
        calls.append(url)
        return b'<a href="song.mid">Song</a>' if url.endswith("/list") else MIDI

    library = MidiLibrary(tmp_path / "midi", manifest)
    monkeypatch.setattr(library, "_fetch", fetch)
    library.run_once(sleep=False)
    assert library.catalog()["downloaded"] == 1
    assert [source["id"] for source in library.catalog()["sources"]] == ["active"]
    assert calls == ["https://new.example/list", "https://new.example/song.mid"]

    with sqlite3.connect(tmp_path / "midi" / "library.sqlite3") as database:
        database.execute("UPDATE midi_index SET source_id = 'disabled', payload = json_set(payload, '$.source_id', 'disabled')")
    (tmp_path / "midi" / "disabled").mkdir()
    (tmp_path / "midi" / "disabled" / "song.mid").write_bytes(MIDI)
    reloaded = MidiLibrary(tmp_path / "midi", manifest)
    assert reloaded.catalog()["tracks"] == []
    assert reloaded.file_path("disabled", "song.mid") is None
    assert not reloaded.prioritize("disabled", reloaded._items[0]["id"])
