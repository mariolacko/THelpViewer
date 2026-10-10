import base64
from dataclasses import replace
import hashlib
import io
import json
import struct
import sqlite3
import uuid
import zipfile

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.dos_prompt import DosPromptStore, DosError, c_path
from thelpviewer.server.downloader.extractor import find_unar, find_sevenzip


def store_at(tmp_path):
    config = tmp_path / "dos.json"
    config.write_text('{"sources": [], "files": [{"path":"README.TXT","text":["Shared test disk"]},{"path":"GAMES/README.TXT","text":["Test games"]}]}')
    store = DosPromptStore(tmp_path / "dos", config)
    store.prepare()
    assert store.state == "ready", store.error
    return store


def payload(store, revision=0, files=None, deleted=None):
    return {"base_id": store.base_id, "revision": revision,
            "files": {name: base64.b64encode(data).decode() for name, data in (files or {}).items()},
            "deleted": deleted or [], "directories": ["EMPTY"]}


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd", "C:/file", "foo/../../escape", "foo\\..\\bar", "foo/", "bad\0name"])
def test_dos_names_cannot_escape_c(path):
    with pytest.raises(DosError):
        c_path(path)


def test_private_overlays_preserve_base_deletions_and_empty_directories(tmp_path):
    store = store_at(tmp_path)
    first, second = uuid.uuid4().hex, uuid.uuid4().hex
    original = (store.root / "base" / "c" / "README.TXT").read_bytes()
    store.save(first, payload(store, files={"SAVE.DAT": b"level 3"}, deleted=["README.TXT"]))
    user_zip, state = store.bundle(first)
    with zipfile.ZipFile(io.BytesIO(user_zip)) as archive:
        assert archive.read("drive_c/SAVE.DAT") == b"level 3"
        assert "drive_c/README.TXT" not in archive.namelist()
        assert "drive_c/EMPTY/" in archive.namelist()
        conf = archive.read(".jsdos/dosbox.conf").decode()
        assert "mount c drive_c" in conf and "config -securemode" in conf
        assert conf.index("mount c") < conf.index("config -securemode") < conf.index("echo THelpViewer")
    with zipfile.ZipFile(io.BytesIO(store.bundle(second)[0])) as archive:
        assert archive.read("drive_c/README.TXT") == original
        assert "drive_c/SAVE.DAT" not in archive.namelist()
    assert (store.root / "base" / "c" / "README.TXT").read_bytes() == original
    # Deleting a user-created file must not bring it back on the next boot.
    store.save(first, payload(store, revision=1, deleted=["README.TXT"]))
    assert store.overlay(first)[1] == {}
    with pytest.raises(DosError, match="Another DOS"):
        store.save(first, payload(store, revision=1))
    invalid = payload(store, revision=2, files={"../outside": b"no"})
    with pytest.raises(DosError):
        store.save(first, invalid)
    assert store.overlay(first)[0] == 2


def test_boot_zip_contains_all_parent_directories_before_files(tmp_path):
    store = store_at(tmp_path)
    store.files["FREEDOS/APPINFO/TEST.LSM"] = b"metadata"
    account = uuid.uuid4().hex
    data = payload(store, files={"SAVE/LEVEL1/GAME.DAT": b"saved"})
    data["directories"] = ["EMPTY/NESTED"]
    store.save(account, data)
    with zipfile.ZipFile(io.BytesIO(store.bundle(account)[0])) as archive:
        paths = archive.namelist()
        for name in paths:
            parts = name.rstrip("/").split("/")
            for index in range(1, len(parts)):
                parent = "/".join(parts[:index]) + "/"
                assert parent in paths and paths.index(parent) < paths.index(name)
        assert archive.read("drive_c/FREEDOS/APPINFO/TEST.LSM") == b"metadata"


def test_finished_base_is_not_rebuilt_or_changed_on_later_starts(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    base = store.root / "base" / "c"
    (base / "README.TXT").write_bytes(b"administrator-edited base")
    (base / "GAMES" / "README.TXT").unlink()
    store.config_path.write_text(json.dumps({"sources": [{"id": "later-added-source"}]}))
    monkeypatch.setattr("thelpviewer.server.dos_prompt.fetch_dos_source", lambda *args: pytest.fail("Completed base must not download again"))
    reloaded = DosPromptStore(store.root, store.config_path)
    reloaded.prepare()
    assert reloaded.state == "ready", reloaded.error
    assert reloaded.files["README.TXT"] == b"administrator-edited base"
    assert not (base / "GAMES" / "README.TXT").exists()
    assert json.loads((store.root / "base" / "installed.json").read_text())["_complete"] is True


def test_overlay_rejects_base_changes_collisions_and_private_quota(tmp_path):
    store = store_at(tmp_path)
    account = uuid.uuid4().hex
    invalid = {**payload(store), "base_id": "wrong"}
    with pytest.raises(DosError, match="base changed"):
        store.save(account, invalid)
    with pytest.raises(DosError, match="both a file and a directory"):
        store.save(account, payload(store, files={"EMPTY": b"file"}))
    with pytest.raises(DosError, match="cannot contain"):
        store.save(account, payload(store, files={"DATA": b"file", "DATA/OTHER": b"child"}))
    store.settings.update({"dos_user_disk_mb": 1})
    with pytest.raises(DosError, match="quota"):
        store.save(account, payload(store, files={"LARGE": bytes(1024 * 1024 + 1)}))
    assert store.overlay(account)[0] == 0


def test_overlay_files_are_regular_files_and_sqlite_holds_only_metadata(tmp_path):
    store = store_at(tmp_path)
    account = uuid.uuid4().hex
    store.save(account, payload(store, files={"SAVE/LEVEL1.DAT": b"level one"}, deleted=["README.TXT"]))
    user = store.root / "users" / account
    assert (user / "c" / "1" / "SAVE" / "LEVEL1.DAT").read_bytes() == b"level one"
    assert (user / "c" / "1" / "EMPTY").is_dir()
    assert not (user / "c" / "1" / "README.TXT").exists()
    with sqlite3.connect(user / "overlay.sqlite3") as database:
        assert not database.execute("SELECT 1 FROM sqlite_master WHERE name='files'").fetchone()
        assert database.execute("SELECT name FROM deleted").fetchall() == [("README.TXT",)]
    assert store.overlay(account)[1] == {"SAVE/LEVEL1.DAT": b"level one"}
    store.save(account, payload(store, revision=1, files={"SAVE/LEVEL2.DAT": b"level two"}))
    store.save(account, payload(store, revision=2, files={"SAVE/LEVEL3.DAT": b"level three"}))
    assert not (user / "c" / "1").exists()
    assert (user / "c" / "2" / "SAVE" / "LEVEL2.DAT").exists()
    assert store.overlay(account)[1] == {"SAVE/LEVEL3.DAT": b"level three"}


def test_legacy_sqlite_overlay_migrates_without_losing_files_or_deletions(tmp_path):
    store = store_at(tmp_path)
    account = uuid.uuid4().hex
    user = store._user_dir(account)
    with sqlite3.connect(user / "overlay.sqlite3") as database:
        database.executescript("""
            CREATE TABLE files (name TEXT PRIMARY KEY, data BLOB NOT NULL);
            CREATE TABLE state (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL);
            CREATE TABLE deleted (name TEXT PRIMARY KEY);
            CREATE TABLE directories (name TEXT PRIMARY KEY);
            INSERT INTO state VALUES (1, 7);
            INSERT INTO files VALUES ('SAVE.DAT', X'7361766564');
            INSERT INTO deleted VALUES ('README.TXT');
            INSERT INTO directories VALUES ('EMPTY');
        """)
    assert store.overlay(account) == (7, {"SAVE.DAT": b"saved"}, ["README.TXT"], ["EMPTY"])
    assert (user / "c" / "7" / "SAVE.DAT").read_bytes() == b"saved"
    assert store.overlay(account)[0] == 7


def test_failed_snapshot_does_not_replace_the_last_saved_overlay(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    account = uuid.uuid4().hex
    store.save(account, payload(store, files={"SAVE.DAT": b"old"}))
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr("thelpviewer.server.dos_prompt._atomic_file", fail)
    with pytest.raises(OSError, match="disk full"):
        store.save(account, payload(store, revision=1, files={"SAVE.DAT": b"new"}))
    assert store.overlay(account)[0:2] == (1, {"SAVE.DAT": b"old"})


def test_shared_software_does_not_consume_private_overlay_capacity(tmp_path):
    store = store_at(tmp_path)
    store.settings.update({"dos_user_disk_mb": 1})
    store.files["GAME.DAT"] = bytes(2 * 1024 * 1024)
    account = uuid.uuid4().hex
    store.save(account, payload(store, files={"SAVE.DAT": bytes(1024 * 1024)}))
    assert store.overlay(account)[0] == 1
    assert store.bundle(account)[1]["max_overlay_bytes"] == 1024 * 1024
    assert store.bundle(None)[1]["max_overlay_bytes"] == 0


def test_lazy_boot_zip_contains_metadata_not_game_contents(tmp_path):
    store = store_at(tmp_path)
    store.files["GAMES/LARGE.DAT"] = bytes(2 * 1024 * 1024)
    data, metadata = store.bundle(None, lazy=True)
    assert len(data) < 4096
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert "drive_c/GAMES/" in archive.namelist()
        assert "drive_c/GAMES/LARGE.DAT" not in archive.namelist()
        disk = json.loads(archive.read(".jsdos/disk.json"))
        assert disk["files"]["GAMES/LARGE.DAT"]["size"] == 2 * 1024 * 1024
        assert disk["files"]["GAMES/LARGE.DAT"]["base"] is True
    digest = metadata["remote_files"]["GAMES/LARGE.DAT"]["sha256"]
    assert store.read_chunk(None, "GAMES/LARGE.DAT", digest, True, 65530, 20) == bytes(20)
    with pytest.raises(DosError):
        store.read_chunk(None, "../outside", digest, True, 0, 20)
    with pytest.raises(DosError):
        store.read_chunk(None, "GAMES/LARGE.DAT", digest, True, 0, 65537)


def test_unread_private_files_are_retained_without_browser_upload(tmp_path):
    store = store_at(tmp_path)
    account = uuid.uuid4().hex
    store.save(account, payload(store, files={"SAVE.DAT": b"unchanged", "OTHER.DAT": b"remove"}))
    data = payload(store, revision=1, files={"NEW.DAT": b"new"})
    data["unchanged"] = ["SAVE.DAT"]
    store.save(account, data)
    assert store.overlay(account)[1] == {"SAVE.DAT": b"unchanged", "NEW.DAT": b"new"}
    digest = hashlib.sha256(b"unchanged").hexdigest()
    assert store.read_chunk(account, "SAVE.DAT", digest, False, 2, 3) == b"cha"
    with pytest.raises(DosError):
        store.read_chunk(uuid.uuid4().hex, "SAVE.DAT", digest, False, 0, 3)


def test_root_text_binary_and_boot_files_use_the_same_schema_and_remain_frozen(tmp_path):
    config = tmp_path / "dos.json"
    config.write_text(json.dumps({"sources": [], "files": [
        {"path": "AUTOEXEC.BAT", "text": ["@ECHO OFF", "SET TEST=1"]},
        {"path": "CONFIG.SYS", "text": ["FILES=40"]},
        {"path": "GAMES/README.TXT", "text": ["Custom games header"]},
        {"path": "BOOT/DATA.BIN", "base64": "AP8="},
    ]}))
    store = DosPromptStore(tmp_path / "dos", config)
    store.prepare()
    assert store.state == "ready", store.error
    assert store.files["AUTOEXEC.BAT"] == b"@ECHO OFF\r\nSET TEST=1\r\n"
    assert store.files["CONFIG.SYS"] == b"FILES=40\r\n"
    assert store.files["BOOT/DATA.BIN"] == b"\x00\xff"
    assert "README.TXT" not in store.files
    (store.root / "base" / "c" / "AUTOEXEC.BAT").write_bytes(b"administrator content")
    store.prepare(install_sources=True)
    assert store.files["AUTOEXEC.BAT"] == b"administrator content"
    with zipfile.ZipFile(io.BytesIO(store.bundle(None)[0])) as archive:
        commands = archive.read(".jsdos/dosbox.conf").decode()
        assert commands.index("config -securemode") < commands.index("call C:\\AUTOEXEC.BAT")


def test_default_manifest_does_not_create_an_ineffective_config_sys(tmp_path):
    from pathlib import Path

    manifest = json.loads(Path("thelpviewer/config/dos-prompt.json").read_text())
    assert "config.sys" not in manifest
    manifest["sources"] = []  # Do not download software to test initial files.
    config = tmp_path / "dos.json"
    config.write_text(json.dumps(manifest))
    store = DosPromptStore(tmp_path / "dos", config)
    store.prepare()
    assert store.state == "ready", store.error
    assert "CONFIG.SYS" not in store.files
    assert "AUTOEXEC.BAT" in store.files


def test_first_run_software_download_is_hash_checked_selected_and_resumable(tmp_path, monkeypatch):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("BIN/EDIT.EXE", b"program")
        archive.writestr("DOC/COPYING", b"licence")
        archive.writestr("UNUSED.TXT", b"unused")
    data = output.getvalue()
    config = tmp_path / "dos.json"
    config.write_text(json.dumps({"sources": [{
        "id": "editor", "url": "https://example.test/editor.zip", "sha256": hashlib.sha256(data).hexdigest(),
        "format": "zip", "target": "TOOLS", "members": ["BIN/*", "DOC/*"],
    }]}))
    fetched = []
    monkeypatch.setattr("thelpviewer.server.dos_prompt.fetch_dos_source", lambda source, *args: fetched.append(source["url"]) or data)
    store = DosPromptStore(tmp_path / "dos", config)
    store.prepare()
    assert store.state == "ready", store.error
    assert store.files["TOOLS/BIN/EDIT.EXE"] == b"program"
    assert "TOOLS/UNUSED.TXT" not in store.files
    reloaded = DosPromptStore(tmp_path / "dos", config)
    reloaded.prepare()
    assert reloaded.files == store.files and len(fetched) == 1
    assert b"licence" in reloaded.files.values()
    changed = json.loads(config.read_text())
    changed["sources"][0]["sha256"] = "0" * 64
    config.write_text(json.dumps(changed))
    invalid = DosPromptStore(tmp_path / "invalid", config)
    invalid.prepare()
    assert invalid.state == "error" and "SHA-256 mismatch" in invalid.error
    with pytest.raises(DosError):
        store._source_files(_unsafe_zip(), {"format": "zip"})


def test_source_files_override_archive_on_fresh_install_and_remain_frozen(tmp_path, monkeypatch):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("RUN.BAT", b"original archive content")
    archive_data = stream.getvalue()
    source = {"id": "game", "url": "https://games.test/game.zip", "format": "zip", "target": "GAMES/TEST",
              "sha256": hashlib.sha256(archive_data).hexdigest(), "files": [
        {"path": "RUN.BAT", "text": ["@ECHO OFF", "GAME"]},
        {"path": "DATA/RAW.BIN", "base64": base64.b64encode(bytes(range(256))).decode()},
    ]}
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [source]}))
    monkeypatch.setattr("thelpviewer.server.dos_prompt.fetch_dos_source", lambda *args: archive_data)
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.prepare()
    assert store.state == "ready", store.error
    assert store.files["GAMES/TEST/RUN.BAT"] == b"@ECHO OFF\r\nGAME\r\n"
    assert store.files["GAMES/TEST/DATA/RAW.BIN"] == bytes(range(256))
    source["files"][0]["text"] = ["new configuration"]
    manifest.write_text(json.dumps({"sources": [source]}))
    frozen = DosPromptStore(store.root, manifest)
    frozen.prepare()
    assert frozen.files == store.files
    frozen.rebuild()
    frozen._worker.join(timeout=5)
    assert frozen.state == "ready", frozen.error
    assert frozen.files["GAMES/TEST/RUN.BAT"] == b"new configuration\r\n"


@pytest.mark.parametrize("entries", [
    {}, [{"path": "../escape", "text": ["bad"]}], [{"path": "X.BIN", "base64": "bad!"}],
    [{"path": "X.TXT", "text": ["one\ntwo"]}], [{"path": "X.TXT", "text": [], "base64": ""}],
    [{"path": "a.txt", "text": []}, {"path": "A.TXT", "text": []}],
    [{"path": "X.BIN", "base64": base64.b64encode(bytes(101)).decode()}],
])
def test_source_files_validate_names_contents_and_quota(tmp_path, entries):
    store = DosPromptStore(tmp_path / "dos", None)
    with pytest.raises(DosError):
        store._configured_files({"files": entries}, 100)


def test_root_recipe_overrides_package_recipe_and_can_resume_explicit_install(tmp_path, monkeypatch):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("CONFIG.TXT", b"archive")
    data = stream.getvalue()
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"files": [{"path": "APP/CONFIG.TXT", "text": ["root override"]}],
        "sources": [{"id": "app", "url": "https://example.test/app.zip", "format": "zip", "target": "APP",
            "sha256": hashlib.sha256(data).hexdigest(), "files": [{"path": "CONFIG.TXT", "text": ["package override"]}]}]}))
    monkeypatch.setattr("thelpviewer.server.dos_prompt.fetch_dos_source", lambda *args: data)
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.prepare()
    assert store.state == "ready", store.error
    assert store.files["APP/CONFIG.TXT"] == b"root override\r\n"
    store.prepare(install_sources=True)
    assert store.state == "ready", store.error
    assert store.files["APP/CONFIG.TXT"] == b"root override\r\n"


@pytest.mark.parametrize("key", ["initial_files", "autoexec.bat", "config.sys"])
def test_obsolete_root_file_formats_have_an_explicit_migration_error(tmp_path, key):
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [], key: []}))
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.prepare()
    assert store.state == "error" and "Use files entries" in store.error
    assert not (store.root / "base").exists()


def _unsafe_zip():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../escape", b"bad")
    return output.getvalue()


def floppy_image():
    """Minimal genuine 1.44 MB FAT12 floppy with one readable text file."""
    image = bytearray(1474560)
    image[:11] = b"\xeb\x3c\x90MSDOS5.0"
    struct.pack_into("<HBHBHHBHHHII", image, 11, 512, 1, 1, 2, 224, 2880, 0xf0, 9, 18, 2, 0, 0)
    image[38] = 0x29
    image[43:62] = b"THELP TEST FAT12   "
    image[510:512] = b"\x55\xaa"
    for start in (512, 5120):
        image[start:start + 5] = b"\xf0\xff\xff\xff\x0f"
    root = 19 * 512
    image[root:root + 11] = b"APPROVEDTXT"
    image[root + 11] = 0x20
    contents = b"approved media\r\n"
    struct.pack_into("<HI", image, root + 26, 2, len(contents))
    image[33 * 512:33 * 512 + len(contents)] = contents
    return bytes(image)


def cd_image():
    """Small ISO9660 image with a valid PVD, path table and one file."""
    image = bytearray(32 * 2048)

    def both32(value):
        return struct.pack("<I", value) + struct.pack(">I", value)

    def both16(value):
        return struct.pack("<H", value) + struct.pack(">H", value)

    def record(name, extent, size, flags=0):
        length = 33 + len(name) + (0 if len(name) % 2 else 1)
        output = bytearray(length)
        output[0] = length
        output[2:10] = both32(extent)
        output[10:18] = both32(size)
        output[18:25] = bytes([126, 10, 8, 12, 0, 0, 0])
        output[25] = flags
        output[28:32] = both16(1)
        output[32] = len(name)
        output[33:33 + len(name)] = name
        return bytes(output)

    pvd = 16 * 2048
    image[pvd:pvd + 7] = b"\x01CD001\x01"
    image[pvd + 8:pvd + 40] = b"THELP".ljust(32)
    image[pvd + 40:pvd + 72] = b"THELP TEST".ljust(32)
    image[pvd + 80:pvd + 88] = both32(32)
    image[pvd + 120:pvd + 124] = both16(1)
    image[pvd + 124:pvd + 128] = both16(1)
    image[pvd + 128:pvd + 132] = both16(2048)
    image[pvd + 132:pvd + 140] = both32(10)
    struct.pack_into("<I", image, pvd + 140, 19)
    struct.pack_into(">I", image, pvd + 148, 20)
    image[pvd + 156:pvd + 190] = record(b"\0", 21, 2048, 2)
    image[pvd + 881] = 1
    image[17 * 2048:17 * 2048 + 7] = b"\xffCD001\x01"
    image[19 * 2048:19 * 2048 + 10] = b"\x01\0" + struct.pack("<IH", 21, 1) + b"\0\0"
    image[20 * 2048:20 * 2048 + 10] = b"\x01\0" + struct.pack(">IH", 21, 1) + b"\0\0"
    contents = b"approved cd\r\n"
    directory = record(b"\0", 21, 2048, 2) + record(b"\x01", 21, 2048, 2) + record(b"APPROVED.TXT;1", 22, len(contents))
    image[21 * 2048:21 * 2048 + len(directory)] = directory
    image[22 * 2048:22 * 2048 + len(contents)] = contents
    return bytes(image)


@pytest.mark.skipif(not (find_unar() or find_sevenzip()), reason="Image extractor unavailable")
def test_configured_img_source_reuses_real_disk_extractor(tmp_path):
    store = store_at(tmp_path)
    files = store._source_files(floppy_image(), {"format": "img", "members": ["APPROVED.TXT"]})
    assert files == {"APPROVED.TXT": b"approved media\r\n"}


def test_dos_api_binds_storage_and_media_to_session(tmp_path):
    dos_config = tmp_path / "dos.json"
    dos_config.write_text('{"sources": [], "files": [{"path":"README.TXT","text":["Shared test disk"]}]}')
    midi = tmp_path / "midi.json"
    midi.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
        dos_config_path=dos_config, midi_sources_path=midi, auth_origin="http://testserver",
        statistics_path=tmp_path / "var" / "statistics.sqlite3")
    app = create_app(config)
    app.state.dos_prompt.prepare()
    accounts = app.state.accounts
    accounts.create_user("one"); accounts.create_user("two")
    with accounts._connect() as database:
        first = database.execute("SELECT id FROM accounts WHERE username='one'").fetchone()[0]
        second = database.execute("SELECT id FROM accounts WHERE username='two'").fetchone()[0]
        first_token = accounts._new_session(database, first)
        second_token = accounts._new_session(database, second)
    with TestClient(app) as client:
        assert client.get("/api/dos/bundle").status_code == 200
        assert client.put("/api/dos/overlay", json={}, headers={"Origin": "http://testserver"}).status_code == 401
        client.cookies.set("thelp_session", first_token)
        session = client.get("/api/dos/session").json()
        assert session["account"] == "one"
        store = app.state.dos_prompt
        store.files["CHUNK.DAT"] = b"chunk-data-" * 10000
        digest = hashlib.sha256(store.files["CHUNK.DAT"]).hexdigest()
        query = {"name": "CHUNK.DAT", "sha256": digest, "base_id": store.base_id,
                 "account": "one", "offset": 65536, "size": 2048}
        chunk = client.get("/api/dos/file", params=query, headers={"Accept-Encoding": "gzip"})
        assert chunk.status_code == 200 and chunk.headers["Content-Encoding"] == "gzip"
        assert chunk.content == store.files["CHUNK.DAT"][65536:67584]
        assert chunk.headers["Cache-Control"] == "no-store"
        plain = client.get("/api/dos/file", params=query, headers={"Accept-Encoding": "gzip;q=0"})
        assert "Content-Encoding" not in plain.headers and plain.content == chunk.content
        for changed in ({"account": "two"}, {"base_id": "wrong"}, {"sha256": "0" * 64},
                        {"name": "../outside"}, {"size": 65537}, {"offset": -1}):
            assert client.get("/api/dos/file", params={**query, **changed}).status_code == 409
        data = {**payload(app.state.dos_prompt, files={"CONFIG.INI": b"one"}), "account": "one"}
        assert client.put("/api/dos/overlay", json=data, headers={"Origin": "https://evil.test"}).status_code == 403
        assert client.put("/api/dos/overlay", json=data, headers={"Origin": "http://testserver"}).status_code == 200
        private_query = {"name": "CONFIG.INI", "sha256": hashlib.sha256(b"one").hexdigest(),
                         "base_id": store.base_id, "account": "one", "base_file": False}
        assert client.get("/api/dos/file", params=private_query).content == b"one"
        media_headers = {"Origin": "http://testserver", "X-DOS-Account": "one"}
        result = client.post("/api/dos/media?kind=floppy", content=floppy_image(), headers=media_headers)
        assert result.status_code == 200
        ident = result.json()["id"]
        assert client.get("/api/dos/media/" + ident).status_code == 200
        assert client.post("/api/dos/media?kind=floppy", content=floppy_image(), headers=media_headers).json()["id"] == ident
        with zipfile.ZipFile(io.BytesIO(client.get("/api/dos/bundle?media=" + ident).content)) as archive:
            assert b"imgmount a media/" in archive.read(".jsdos/dosbox.conf")
        client.cookies.set("thelp_session", second_token)
        assert client.get("/api/dos/file", params={**private_query, "account": "two"}).status_code == 409
        assert client.post("/api/dos/media?kind=floppy", content=floppy_image(), headers=media_headers).status_code == 409
        assert client.get("/api/dos/media/" + ident).status_code == 404
        assert client.put("/api/dos/overlay", json=data, headers={"Origin": "http://testserver"}).status_code == 409
        with zipfile.ZipFile(io.BytesIO(client.get("/api/dos/bundle").content)) as archive:
            assert "drive_c/CONFIG.INI" not in archive.namelist()
