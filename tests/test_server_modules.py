"""Feature components work independently of HTTP/application construction."""

import base64
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid
import zipfile

import pytest

from thelpviewer.server.dos.media import DosMediaStore
from thelpviewer.server.dos.overlay import DosOverlayStore
from thelpviewer.server.dos.packages import DosPackageExtractor, configured_files
from thelpviewer.server.dos.paths import DosError
from thelpviewer.server.midi import catalog
from thelpviewer.server.midi.format import standard_midi
from thelpviewer.server.midi.sources import index_source
from thelpviewer.server.settings import ServerSettings


def test_private_overlay_and_media_reopen_without_shared_disk_preparation(tmp_path):
    users = tmp_path / "data/dos/users"
    settings = ServerSettings(tmp_path / "data/server-settings.json")
    overlay = DosOverlayStore(users, settings, None)
    account, other = uuid.uuid4().hex, uuid.uuid4().hex
    shared = {"GAME.EXE": b"shared", "README.TXT": b"original"}
    payload = {"revision": 0, "base_id": "base", "files": {
        "SAVE.DAT": base64.b64encode(b"private saved game").decode(),
    }, "deleted": ["README.TXT"], "directories": ["EMPTY"]}
    assert overlay.save(account, payload, "base", shared) == 1
    reopened = DosOverlayStore(users, settings, None)
    assert reopened.overlay(account) == (1, {"SAVE.DAT": b"private saved game"}, ["README.TXT"], ["EMPTY"])
    assert reopened.overlay(other) == (0, {}, [], [])
    assert reopened.disk_usage(account)["used_bytes"] == len(b"private saved game")
    assert shared == {"GAME.EXE": b"shared", "README.TXT": b"original"}
    assert not (tmp_path / "var").exists()
    digest = hashlib.sha256(b"private saved game").hexdigest()
    assert reopened.read_chunk(account, "SAVE.DAT", digest, 8, 5) == b"saved"
    with pytest.raises(DosError, match="changed"):
        reopened.read_chunk(other, "SAVE.DAT", digest, 0, 10)

    floppy = bytes(510) + b"\x55\xaa"
    media = DosMediaStore(users)
    ident = media.add_media(account, "floppy", floppy, 1024)
    assert DosMediaStore(users).media_path(account, ident).read_bytes() == floppy
    assert media.media_path(other, ident) is None
    with pytest.raises(DosError, match="quota"):
        media.add_media(account, "floppy", floppy, 511)


def test_package_extraction_and_file_recipes_need_no_store_or_network():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("DISK1/README.TXT", b"reference")
    assert DosPackageExtractor(100).extract(data.getvalue(), {
        "format": "zip", "strip_components": 1,
    }) == {"README.TXT": b"reference"}
    with pytest.raises(DosError, match="quota"):
        DosPackageExtractor(8).extract(data.getvalue(), {"format": "zip"})
    assert configured_files({"files": [
        {"path": "AUTOEXEC.BAT", "text": ["@echo off"]},
        {"path": "DATA.BIN", "base64": "AAEC"},
    ]}, 100) == {"AUTOEXEC.BAT": b"@echo off\r\n", "DATA.BIN": b"\0\1\2"}


def test_midi_source_catalog_and_covers_round_trip_without_background_workers(tmp_path):
    source = {"id": "music", "index_url": "https://music.test/list", "allowed_hosts": ["music.test"],
              "extract": {"mode": "anchors"}, "rights_note": "Source attribution"}
    requests = []

    def fetch(url, hosts, limit):
        requests.append((url, hosts, limit))
        return b'<a href="/theme.mid">Theme</a>'

    items = index_source(source, fetch)
    assert len(requests) == 1 and items[0]["url"] == "https://music.test/theme.mid"
    assert catalog.load_catalog(tmp_path) == ([], {}, {})
    catalog.save_catalog(tmp_path, items)
    cover = catalog.save_cover(tmp_path, source, "", b"\x89PNG\r\n\x1a\nimage", ".png", source["index_url"])
    loaded, covers, pages = catalog.load_catalog(tmp_path)
    assert loaded == items and covers == {("music", ""): cover} and pages == {}
    assert (tmp_path / "covers" / cover).is_file()
    catalog.sync_tracks(tmp_path, loaded, covers, lambda source_id, filename: True)
    with sqlite3.connect(tmp_path / "library.sqlite3") as database:
        assert database.execute("SELECT title,source_url,cover_filename FROM midi_tracks").fetchall() == [
            ("Theme", "https://music.test/theme.mid", cover),
        ]
    midi = b"MThd\0\0\0\6\0\0\0\1\0\x60MTrk\0\0\0\4\0\xff\x2f\0"
    assert standard_midi(midi, limit=100) == midi


def test_account_package_remains_executable_as_a_cli():
    result = subprocess.run([sys.executable, "-m", "thelpviewer.server.accounts", "--help"],
        cwd=Path(__file__).resolve().parents[1], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "create" in result.stdout and "invite" in result.stdout
