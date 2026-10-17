"""Old SHA-pinned receipts migrate once, with checksum/ownership proof."""

import hashlib
import io
import json
import os
import zipfile

import pytest

from thelpviewer.server.dos.paths import DosError
from thelpviewer.server.dos.store import DosPromptStore
from thelpviewer.server.downloader.cache import cache_metadata_path
from thelpviewer.server.downloader.packages import package_cache_key, package_cache_path, read_package_cache


def installation(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("TIM/GAME.EXE", b"game")
    data = buffer.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    source = {"id": "game", "url": "https://games.test/game.zip", "format": "zip", "target": "GAMES"}
    config = {"sources": [source]}
    config_path = tmp_path / "dos.json"
    config_path.write_text(json.dumps(config))
    store = DosPromptStore(tmp_path / "var/dos", config_path, downloads_dir=tmp_path / "var/downloads/dos",
                           disk_dir=tmp_path / "var/dos/c", users_dir=tmp_path / "data/dos/users")
    store.config = config
    store.disk_dir.joinpath("GAMES/TIM").mkdir(parents=True)
    store.disk_dir.joinpath("GAMES/TIM/GAME.EXE").write_bytes(b"game")
    store.disk_dir.joinpath("ADMIN.TXT").write_bytes(b"keep")
    store.downloads_dir.mkdir(parents=True)
    old = store.downloads_dir / digest
    old.write_bytes(data)
    os.utime(old, ns=(1_000_000_000, 2_000_000_000))
    store.installed_path.write_text(json.dumps({"game": digest, "_complete": True, "obsolete": "f" * 64}))
    return store, source, old


def test_recovery_preserves_live_files_migrates_cache_and_allows_uninstall_without_archive(tmp_path, monkeypatch):
    store, source, old = installation(tmp_path)
    before = {p.relative_to(store.disk_dir): p.read_bytes() for p in store.disk_dir.rglob("*") if p.is_file()}
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source",
                        lambda *_a, **_kw: pytest.fail("Migration/reuse must not download"))
    try:
        result = store.migrate_downloads()
        assert result["recovered"] == 1 and result["unmapped"] == 0
        receipt = json.loads(store.installed_path.read_text())
        assert receipt["game"] == package_cache_key(source)
        assert receipt["obsolete"] == "f" * 64 and receipt["_complete"]
        assert receipt["_files"] == {"game": ["GAMES/TIM/GAME.EXE"]}
        target = store.downloads_dir / package_cache_path(source)
        assert not old.exists() and target.stat().st_mtime_ns == 2_000_000_000
        assert read_package_cache(source, store.downloads_dir, 1024, process=lambda data, _recipe: data) == target.read_bytes()
        assert {p.relative_to(store.disk_dir): p.read_bytes() for p in store.disk_dir.rglob("*") if p.is_file()} == before
        assert store.migrate_downloads()["recovered"] == 0
        target.unlink()
        cache_metadata_path(target).unlink()
        store.configure([])
        assert not (store.disk_dir / "GAMES/TIM/GAME.EXE").exists()
        assert (store.disk_dir / "ADMIN.TXT").read_bytes() == b"keep"
    finally:
        store.downloads.close()


@pytest.mark.parametrize("problem", ["modified", "missing", "link", "cache-conflict", "bad-checksum"])
def test_recovery_does_not_guess_or_overwrite_unverified_content(tmp_path, problem):
    store, source, old = installation(tmp_path)
    receipt = store.installed_path.read_bytes()
    game = store.disk_dir / "GAMES/TIM/GAME.EXE"
    if problem == "modified":
        game.write_bytes(b"admin change")
    elif problem == "missing":
        game.unlink()
    elif problem == "link":
        game.unlink()
        game.symlink_to(store.disk_dir / "ADMIN.TXT")
    elif problem == "cache-conflict":
        target = store.downloads_dir / package_cache_path(source)
        target.parent.mkdir(parents=True)
        target.write_bytes(b"another source")
    else:
        old.write_bytes(b"corrupt")
    try:
        if problem == "bad-checksum":
            assert store.migrate_downloads()["recovered"] == 0
        else:
            with pytest.raises(DosError):
                store.migrate_downloads()
        assert old.exists() and store.installed_path.read_bytes() == receipt
        assert (store.disk_dir / "ADMIN.TXT").read_bytes() == b"keep"
    finally:
        store.downloads.close()


def test_receipt_write_failure_keeps_old_cache_and_can_be_retried(tmp_path, monkeypatch):
    from thelpviewer.server.dos import migration
    store, source, old = installation(tmp_path)
    original_receipt = store.installed_path.read_bytes()
    original_write = migration.atomic_file
    def fail_receipt(path, data):
        if path == store.installed_path:
            raise OSError("receipt disk full")
        original_write(path, data)
    try:
        with monkeypatch.context() as patched:
            patched.setattr(migration, "atomic_file", fail_receipt)
            with pytest.raises(OSError, match="disk full"):
                store.migrate_downloads()
        assert old.exists() and store.installed_path.read_bytes() == original_receipt
        assert store.migrate_downloads()["recovered"] == 1
        assert not old.exists()
    finally:
        store.downloads.close()


def test_missing_new_configured_files_are_not_invented_as_existing_owned_files(tmp_path):
    store, source, old = installation(tmp_path)
    config = json.loads(store.config_path.read_text())
    config["sources"][0]["files"] = [{"path": "START.BAT", "text": ["GAME.EXE"]}]
    store.config_path.write_text(json.dumps(config))
    try:
        assert store.migrate_downloads()["recovered"] == 1
        assert json.loads(store.installed_path.read_text())["_files"]["game"] == ["GAMES/TIM/GAME.EXE"]
        assert not (store.disk_dir / "GAMES/START.BAT").exists()
        store.configure(["game"])
        assert (store.disk_dir / "GAMES/START.BAT").read_bytes() == b"GAME.EXE\r\n"
        assert "GAMES/START.BAT" in json.loads(store.installed_path.read_text())["_files"]["game"]
        store.configure([])
        assert not (store.disk_dir / "GAMES/START.BAT").exists()
    finally:
        store.downloads.close()
