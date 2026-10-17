import base64
from dataclasses import replace
import hashlib
import io
import json
import struct
import sqlite3
import threading
import uuid
import zipfile

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.dos.packages import configured_files
from thelpviewer.server.dos.config import select_dos_packages
from thelpviewer.server.dos.store import DosPromptStore
from thelpviewer.server.dos.paths import DosError, c_path
from thelpviewer.server.archives.core import UnsafeArchiveError, find_unar, find_sevenzip


def store_at(tmp_path):
    config = tmp_path / "dos.json"
    config.write_text('{"sources": [], "files": [{"path":"README.TXT","text":["Shared test disk"]},{"path":"GAMES/README.TXT","text":["Test games"]}]}')
    store = DosPromptStore(tmp_path / "dos", config)
    store.prepare()
    assert store.state == "ready", store.error
    return store


def test_package_selection_uninstalls_only_owned_files_and_preserves_private_and_shared_files(tmp_path, monkeypatch):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("GAME.EXE", b"game")
        archive.writestr("COMMON.DAT", b"shared")
    archive_data = data.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *args, **kwargs: archive_data)
    config = tmp_path / "dos.json"
    sources = [{"id": ident, "url": f"https://games.test/{ident}.zip", "target": "GAMES", "format": "zip"}
               for ident in ("one", "two")]
    config.write_text(json.dumps({"sources": sources, "files": [{"path": "AUTOEXEC.BAT", "text": ["@echo off"]}]}))
    store = DosPromptStore(tmp_path / "var" / "dos", config, users_dir=tmp_path / "data" / "dos" / "users",
                           disk_dir=tmp_path / "var" / "dos" / "c")
    store.configure(["one", "two"])
    account = uuid.uuid4().hex
    store.save(account, payload(store, files={"GAMES/SAVE.DAT": b"saved"}))
    (store.disk_dir / "ADMIN.TXT").write_bytes(b"not package-owned")
    store.configure(["two"])
    assert store.files["GAMES/GAME.EXE"] == b"game"  # Shared ownership protects the surviving package.
    assert store.overlay(account)[1] == {"GAMES/SAVE.DAT": b"saved"}
    store.configure([])
    assert "GAMES/GAME.EXE" not in store.files and "GAMES/COMMON.DAT" not in store.files
    assert store.files["ADMIN.TXT"] == b"not package-owned"
    assert store.files["AUTOEXEC.BAT"] == b"@echo off\r\n"
    assert store.overlay(account)[1] == {"GAMES/SAVE.DAT": b"saved"}
    assert (store.root.parent / store.backup / "c" / "GAMES/GAME.EXE").read_bytes() == b"game"
    assert "two" not in json.loads(store.installed_path.read_text())


def test_failed_package_publication_restores_original_disk_receipt_and_memory(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    before = dict(store.files)
    receipt = store.installed_path.read_bytes()
    original = __import__("thelpviewer.server.dos.store", fromlist=["atomic_file"]).atomic_file
    def fail_marker(path, contents):
        if path == store.root / "base" / "installed.json":
            raise OSError("metadata disk full")
        original(path, contents)
    monkeypatch.setattr("thelpviewer.server.dos.store.atomic_file", fail_marker)
    with pytest.raises(DosError, match="disk full"):
        store.configure([])
    assert store.state == "ready" and not store.configuring
    assert store.files == before
    assert store.installed_path.read_bytes() == receipt
    assert (store.disk_dir / "README.TXT").read_bytes() == before["README.TXT"]
    assert not list(store.disk_dir.parent.glob(".dos-packages-*"))


@pytest.mark.parametrize("failure", [None, "download", "publication"])
def test_dos_completion_means_published_not_staged_and_retry_reuses_cache(tmp_path, monkeypatch, failure):
    from test_server_content import config_for
    config = config_for(tmp_path)
    app = create_app(config)
    store, downloads = app.state.dos_prompt, app.state.downloads
    store.configure([])
    before, marker = dict(store.files), store.installed_path.read_bytes()
    live_marker = store.installed_path
    original = __import__("thelpviewer.server.dos.store", fromlist=["atomic_file"]).atomic_file
    fetched, seen = [], []
    def fetch(source, *_args, **_kwargs):
        fetched.append(source["id"])
        if failure == "download" and source["id"] == "two":
            raise OSError("source offline")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("GAME.EXE", source["id"].encode())
        return output.getvalue()
    def write(path, contents):
        if path == live_marker:
            rows = downloads.snapshot(private=True)["items"]
            assert rows and all(row["state"] == "waiting" and row["phase"] == "Awaiting publication" for row in rows)
            seen.append("publication")
            if failure == "publication":
                raise OSError("publication failed")
        original(path, contents)
    def progress(_status):
        choices = app.state.content.choices()
        assert not any(item["installed"] for item in choices["dos_packages"])
        assert not store.status(start=False)["initializing"]
        assert store.status(start=False)["configuring"]
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    monkeypatch.setattr("thelpviewer.server.dos.store.atomic_file", write)
    try:
        if failure:
            with pytest.raises(DosError, match="offline|publication failed"):
                store.configure(["one", "two"], on_progress=progress)
            rows = {row["id"]: row for row in downloads.snapshot(private=True)["items"]}
            assert rows["dos:one"]["state"] == "blocked" and rows["dos:one"]["retryable"]
            assert all(row["state"] != "done" for row in rows.values())
            assert store.files == before and store.installed_path.read_bytes() == marker
            assert store.published_packages() == set()
            fetched.clear()
            previous_failure, failure = failure, None
            store.configure(["one", "two"], on_progress=progress)
            assert fetched == (["two"] if previous_failure == "download" else [])
        else:
            store.configure(["one", "two"], on_progress=progress)
        assert seen
        assert store.published_packages() == {"one", "two"}
        assert all(row["state"] == "done" for row in downloads.snapshot(private=True)["items"])
    finally:
        downloads.close()


def test_shared_library_exceeds_individual_package_size_without_a_global_quota(tmp_path, monkeypatch):
    from test_server_content import config_for
    config = config_for(tmp_path)
    manifest = json.loads(config.dos_config_path.read_text())
    manifest["files"] = []
    config.dos_config_path.write_text(json.dumps(manifest))
    # Small per-package safety bound, independent of the combined library size.
    monkeypatch.setattr("thelpviewer.server.dos.store.MAX_PACKAGE_BYTES", 16)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("GAME.EXE", b"123456789")
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *_a, **_kw: output.getvalue())
    store = DosPromptStore(tmp_path / "dos", config.dos_config_path)
    try:
        store.configure(["one", "two"])
        assert sum(map(len, store.files.values())) == 18
        assert store.c_limit(None) == 18 + store.overlay_limit(None)
    finally:
        store.downloads.close()


def test_missing_published_package_file_is_uninstalled_until_cache_repairs_it(tmp_path, monkeypatch):
    from test_server_content import config_for
    config = config_for(tmp_path)
    app = create_app(config)
    store = app.state.dos_prompt
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("GAME.EXE", b"game")
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *_a, **_kw: output.getvalue())
    try:
        store.configure(["one"])
        owned = json.loads(store.installed_path.read_text())["_files"]["one"]
        (store.disk_dir / owned[0]).unlink()
        assert store.published_packages() == set()
        assert not next(item for item in app.state.content.choices()["dos_packages"] if item["id"] == "one")["installed"]
        def offline(*_args, **_kwargs):
            raise AssertionError("Repair must reuse the verified cached archive")
        monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", offline)
        store.configure(["one"])
        assert store.published_packages() == {"one"}
        assert (store.disk_dir / owned[0]).read_bytes() == b"game"
    finally:
        app.state.downloads.close()


def test_backup_cleanup_failure_does_not_roll_back_published_packages(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    before = dict(store.files)
    def cleanup(*_args):
        raise OSError("backup cleanup failed")
    monkeypatch.setattr("thelpviewer.server.dos.store.prune_backups", cleanup)
    try:
        store.configure([])
        assert store.state == "ready" and not store.configuring
        assert store.files == before and not store.error
        assert json.loads(store.installed_path.read_text())["_complete"]
        assert store.downloads.snapshot(private=True)["errors"] == 0
    finally:
        store.downloads.close()


@pytest.mark.parametrize("key", ["max_c_bytes", "max_c_files"])
def test_shared_library_quota_fields_are_not_supported(tmp_path, key):
    from thelpviewer.server.dos.config import load_dos_config
    config = tmp_path / "dos.json"
    config.write_text(json.dumps({"sources": [], key: 1024}))
    with pytest.raises(DosError, match="shared DOS library has no quota"):
        load_dos_config(config)


def test_large_shared_file_inventory_does_not_consume_private_file_quota(tmp_path):
    from thelpviewer.server.dos.paths import MAX_FILES
    store = store_at(tmp_path)
    try:
        for number in range(MAX_FILES + 1):
            (store.disk_dir / f"F{number}.DAT").touch()
        store.prepare()
        assert store.state == "ready", store.error
        assert len(store.files) > MAX_FILES
        account = uuid.uuid4().hex
        store.save(account, payload(store, files={"PRIVATE.DAT": b"saved"}))
        assert store.overlay(account)[1] == {"PRIVATE.DAT": b"saved"}
        with pytest.raises(DosError, match="file list"):
            store.save(account, payload(store, files={f"P{number}.DAT": b"" for number in range(MAX_FILES + 1)}))
    finally:
        store.downloads.close()


def test_required_packages_survive_empty_selection_initialization_and_rebuild(tmp_path, monkeypatch):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("PROGRAM.EXE", b"required program")
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *args, **kwargs: data.getvalue())
    config = tmp_path / "dos.json"
    config.write_text(json.dumps({"sources": [
        {"id": "base-tool", "required": True, "enabled": False, "url": "https://tools.test/base.zip",
         "format": "zip", "target": "TOOLS/BASE"},
        {"id": "game", "url": "https://games.test/game.zip", "format": "zip", "target": "GAMES/ONE"},
    ]}))
    store = DosPromptStore(tmp_path / "dos", config)
    store.prepare(source_ids=[])
    assert store.state == "ready", store.error
    assert store.files == {"TOOLS/BASE/PROGRAM.EXE": b"required program"}
    store.configure(["game"])
    assert "GAMES/ONE/PROGRAM.EXE" in store.files and "TOOLS/BASE/PROGRAM.EXE" in store.files
    store.configure([])
    assert store.files == {"TOOLS/BASE/PROGRAM.EXE": b"required program"}
    assert "base-tool" in json.loads(store.installed_path.read_text())
    store.source_selection = lambda: []  # Rebuild must apply the same manifest rule.
    store.rebuild()
    store._worker.join(5)
    assert store.state == "ready", store.error
    assert store.files == {"TOOLS/BASE/PROGRAM.EXE": b"required program"}


def test_required_selection_and_queue_precede_optional_manifest_entries(tmp_path, monkeypatch):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("PROGRAM.EXE", b"program")
    config = tmp_path / "dos.json"
    sources = [{"id": ident, "required": required, "url": f"https://{ident}.test/program.zip",
                "format": "zip", "target": ident.upper()}
               for ident, required in [("game", False), ("tool", True), ("another", False), ("manager", True)]]
    config.write_text(json.dumps({"sources": sources}))
    assert select_dos_packages({"sources": sources}, ["another", "game"]) == ["tool", "manager", "game", "another"]
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *args, **kwargs: output.getvalue())
    store = DosPromptStore(tmp_path / "dos", config)
    try:
        store.configure(["another", "game"])
        rows = store.downloads.snapshot(private=True)["items"]
        assert [row["id"] for row in rows] == ["dos:tool", "dos:manager", "dos:game", "dos:another"]
        assert [row["priority"] for row in rows] == [0, 0, 10, 10]
    finally:
        store.downloads.close()


@pytest.mark.parametrize("damage", ["receipt", "file", "inventory"])
def test_required_receipt_needs_owned_files_before_boot_and_preserves_existing_data(tmp_path, monkeypatch, damage):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("PROGRAM.EXE", b"required")
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [
        {"id": "tool", "required": True, "enabled": False, "url": "https://tools.test/tool.zip",
         "format": "zip", "target": "TOOLS"},
        {"id": "optional", "url": "https://games.test/game.zip", "format": "zip", "target": "GAME"},
    ], "files": [{"path": "AUTOEXEC.BAT", "text": ["@echo off"]}]}))
    fetched = []
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source",
                        lambda source, *args, **kwargs: fetched.append(source["id"]) or output.getvalue())
    store = DosPromptStore(tmp_path / "dos", manifest)
    try:
        store.configure(["optional"])
        (store.disk_dir / "AUTOEXEC.BAT").write_bytes(b"administrator boot")
        receipt = json.loads(store.installed_path.read_text())
        if damage == "receipt":
            del receipt["tool"]
        elif damage == "inventory":
            del receipt["_files"]["tool"]
        else:
            (store.disk_dir / "TOOLS/PROGRAM.EXE").unlink()
        store.installed_path.write_text(json.dumps(receipt))
        before = len(fetched)
        reloaded = DosPromptStore(store.root, manifest, downloads=store.downloads)
        reloaded.prepare()
        assert reloaded.state == "ready", reloaded.error
        assert reloaded.files["TOOLS/PROGRAM.EXE"] == b"required"
        assert reloaded.files["GAME/PROGRAM.EXE"] == b"required"
        assert reloaded.files["AUTOEXEC.BAT"] == b"administrator boot"
        assert json.loads(reloaded.installed_path.read_text())["_files"]["tool"] == ["TOOLS/PROGRAM.EXE"]
        assert len(fetched) == before  # Repair reuses the matching cached archive.
    finally:
        store.downloads.close()


@pytest.mark.parametrize("empty_receipt", [False, True])
@pytest.mark.parametrize("fail_required", [False, True])
def test_dos_api_waits_for_required_bootstrap_not_optional_saved_choices(tmp_path, monkeypatch, empty_receipt, fail_required):
    from test_server_content import config_for
    config = config_for(tmp_path)
    manifest = json.loads(config.dos_config_path.read_text())
    manifest["sources"][1]["required"] = True
    config.dos_config_path.write_text(json.dumps(manifest))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("GAME.EXE", b"mandatory program")
    entered, release = threading.Event(), threading.Event()
    fetched = []
    def fetch(source, *args, **kwargs):
        fetched.append(source["id"])
        entered.set()
        assert release.wait(5)
        if fail_required:
            raise ValueError("Required package unavailable")
        return output.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    app = create_app(config)
    store = app.state.dos_prompt
    app.state.content._save_selection({"configured": True, "help_packages": [], "dos_packages": ["one", "two"]})
    if empty_receipt:
        store.disk_dir.mkdir(parents=True)
        (store.disk_dir / "KEEP.TXT").write_bytes(b"keep")
        store.installed_path.write_text('{"_complete":true,"_files":{}}')
    with TestClient(app, base_url=config.auth_origin) as client:
        try:
            assert client.get("/api/dos/status").json()["state"] == "building"
            assert entered.wait(2)
            assert client.get("/api/dos/session").status_code == 503
            assert client.get("/api/dos/bundle").status_code == 503
            assert fetched == ["two"]
        finally:
            release.set()
            store._worker.join(5)
        assert not store._worker.is_alive()
        if fail_required:
            assert store.state == "error" and "Required package unavailable" in store.error
            assert client.get("/api/dos/session").status_code == 503
            assert client.get("/api/dos/bundle").status_code == 503
            return
        assert store.state == "ready", store.error
        assert client.get("/api/dos/session").status_code == 200
        assert store.files["GAMES/TWO/GAME.EXE"] == b"mandatory program"
        assert "GAMES/ONE/GAME.EXE" not in store.files
        if empty_receipt:
            assert store.files["KEEP.TXT"] == b"keep"


def test_package_strip_components_merges_distribution_disks_after_member_selection(tmp_path):
    store = store_at(tmp_path)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("Disk1/INSTALL.EXE", b"installer")
        archive.writestr("Disk1/README", b"original documentation")
        archive.writestr("Disk2/COMPILER.EXE", b"compiler")
        archive.writestr("UNSELECTED.TXT", b"not part of the disks")
    files = store._source_files(stream.getvalue(), {"format": "zip", "strip_components": 1,
        "members": ["Disk1/*", "Disk2/*"]})
    assert files == {"INSTALL.EXE": b"installer", "README": b"original documentation", "COMPILER.EXE": b"compiler"}


@pytest.mark.parametrize("strip", [-1, True, 1.5, "1", 17])
def test_package_strip_components_rejects_invalid_counts(tmp_path, strip):
    with pytest.raises(DosError, match="component count"):
        store_at(tmp_path)._source_files(b"", {"format": "zip", "strip_components": strip})


@pytest.mark.parametrize("names,message", [
    (["Disk1/FILE.TXT", "Disk2/file.txt"], "Duplicate DOS filename"),
    (["FILE.TXT"], "too few components"),
    (["../FILE.TXT"], "Unsafe archive member path"),
])
def test_package_strip_components_rejects_collisions_short_paths_and_traversal(tmp_path, names, message):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name in names:
            archive.writestr(name, b"data")
    with pytest.raises(UnsafeArchiveError if names[0].startswith("../") else DosError, match=message):
        store_at(tmp_path)._source_files(stream.getvalue(), {"format": "zip", "strip_components": 1})


@pytest.mark.parametrize("creator", [0, 3])
def test_dos_zip_attributes_are_not_misread_as_unix_symlinks(tmp_path, creator):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        entry = zipfile.ZipInfo("ANTI-VIR.DAT")
        entry.create_system = creator
        entry.external_attr = 0o122317 << 16
        archive.writestr(entry, b"ordinary DOS file")
    store = store_at(tmp_path)
    if creator == 3:
        with pytest.raises(UnsafeArchiveError, match="symbolic link"):
            store._source_files(stream.getvalue(), {"format": "zip"})
    else:
        assert store._source_files(stream.getvalue(), {"format": "zip"}) == {"ANTI-VIR.DAT": b"ordinary DOS file"}


def test_legacy_package_ownership_requires_cached_archive_before_uninstall(tmp_path):
    from thelpviewer.server.downloader.cache import write_cache_identity
    from thelpviewer.server.downloader.packages import package_cache_key, package_cache_path
    store = store_at(tmp_path)
    config = json.loads(store.config_path.read_text())
    config["sources"] = [{"id": "legacy", "url": "https://games.test/old.zip", "target": "GAMES/OLD", "format": "zip"}]
    store.config_path.write_text(json.dumps(config))
    source = config["sources"][0]
    receipt = {"legacy": package_cache_key(source), "_complete": True}
    store.installed_path.write_text(json.dumps(receipt))
    original = store.installed_path.read_bytes()
    with pytest.raises(DosError, match="cached archive"):
        store.configure([])
    assert store.installed_path.read_bytes() == original and store.state == "ready"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("GAME.EXE", b"game")
    cache = store.downloads_dir / package_cache_path(source)
    cache.parent.mkdir(parents=True); cache.write_bytes(stream.getvalue())
    write_cache_identity(cache, package_cache_key(source))
    game = store.disk_dir / "GAMES/OLD/GAME.EXE"
    game.parent.mkdir(); game.write_bytes(b"game")
    store.configure([])
    assert not game.exists() and cache.is_file()


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
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *args, **kwargs: pytest.fail("Completed base must not download again"))
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
    user = store.overlays.user_dir(account)
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
    monkeypatch.setattr("thelpviewer.server.dos.overlay.atomic_file", fail)
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
        "id": "editor", "required": True, "url": "https://example.test/editor.zip", "sha256": hashlib.sha256(data).hexdigest(),
        "format": "zip", "target": "TOOLS", "members": ["BIN/*", "DOC/*"],
    }]}))
    fetched = []
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda source, *args, **kwargs: fetched.append(source["url"]) or data)
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
    with pytest.raises(UnsafeArchiveError):
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
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *args, **kwargs: archive_data)
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.prepare(install_sources=True)
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
def test_source_files_validate_names_contents_and_quota(entries):
    with pytest.raises(DosError):
        configured_files({"files": entries}, 100)


def test_root_recipe_overrides_package_recipe_and_can_resume_explicit_install(tmp_path, monkeypatch):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("CONFIG.TXT", b"archive")
    data = stream.getvalue()
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"files": [{"path": "APP/CONFIG.TXT", "text": ["root override"]}],
        "sources": [{"id": "app", "url": "https://example.test/app.zip", "format": "zip", "target": "APP",
            "sha256": hashlib.sha256(data).hexdigest(), "files": [{"path": "CONFIG.TXT", "text": ["package override"]}]}]}))
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *args, **kwargs: data)
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
    config = replace(load_config(), sources_dir=(tmp_path / "var") / 'sources',
        downloads_dir=(tmp_path / "var") / "downloads",
        state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
        dos_config_path=dos_config, midi_sources_path=midi, auth_origin="http://testserver",
        statistics_path=tmp_path / "var" / "statistics.sqlite3")
    app = create_app(config)
    app.state.dos_prompt.prepare()
    accounts = app.state.accounts
    accounts.create_user("one"); accounts.create_user("two")
    with accounts._connect() as database:
        first = database.execute("SELECT id FROM accounts WHERE username='one'").fetchone()[0]
        second = database.execute("SELECT id FROM accounts WHERE username='two'").fetchone()[0]
        first_token = new_session(database, first)
        second_token = new_session(database, second)
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
