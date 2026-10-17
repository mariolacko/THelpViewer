"""Readable source-specific package cache and shared idle expiration."""

import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.downloader.cache import cache_metadata_path, clear_download_cache, download_cached
from thelpviewer.server.downloader import maintenance, packages
from thelpviewer.server.downloader.maintenance import DownloadCache
from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.processing import UnsafeContentError
from thelpviewer.server.settings import ServerSettings
from test_server_content import admin_session, config_for


def put(path, data=b"archive", *, age=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    timestamp = time.time() - age * 86400
    os.utime(path, (timestamp, timestamp))
    return path


@pytest.mark.parametrize("recipe,expected", [
    ({"url": "https://games.test/Prince%20of%20Persia.zip?token=ignored"}, "prince/Prince of Persia.zip"),
    ({"url": "https://games.test/download/opaque", "format": "zip"}, "prince/prince.zip"),
    ({"url": "https://games.test/download/opaque", "format": "archive"}, "prince/prince.archive"),
    ({"file": "utils.zip"}, "prince/utils.zip"),
    ({"format": "collection", "archives": [{}]}, "prince/prince.zip"),
    ({"url": "https://games.test/%2F..%2Fevil.zip"}, "prince/_.._evil.zip"),
])
def test_package_archive_names_are_readable_safe_and_have_extensions(recipe, expected):
    assert packages.package_cache_path({"id": "prince", **recipe}).as_posix() == expected


@pytest.mark.parametrize("ident", ["../escape", "/absolute", "..", "a/b", "", None])
def test_package_cache_id_cannot_escape_its_root(ident):
    with pytest.raises(ValueError):
        packages.package_cache_path({"id": ident, "url": "https://games.test/game.zip"})


def test_same_name_from_another_source_never_uses_wrong_bytes(tmp_path, monkeypatch):
    source = {"id": "game", "url": "https://one.test/game.zip"}
    alternate = {**source, "url": "https://two.test/game.zip"}
    calls = []
    def fetch(recipe, *_args, **_kwargs):
        calls.append(recipe["url"])
        return recipe["url"].encode()
    monkeypatch.setattr(packages, "fetch_source", fetch)
    first, key = packages.download_package(source, tmp_path, 1000)
    cached = tmp_path / packages.package_cache_path(source)
    metadata = cache_metadata_path(cached)
    assert json.loads(metadata.read_text())["key"] == key
    second, second_key = packages.download_package(alternate, tmp_path, 1000)
    assert first != second and key != second_key
    assert packages.download_package(alternate, tmp_path, 1000)[0] == second
    assert calls == [source["url"], alternate["url"]]
    def fail(*_args, **_kwargs):
        raise OSError("connection interrupted")
    monkeypatch.setattr(packages, "fetch_source", fail)
    with pytest.raises(OSError):
        packages.download_package(source, tmp_path, 1000)
    assert cached.read_bytes() == second
    assert json.loads(metadata.read_text())["key"] == second_key


def test_multiple_package_ids_share_one_transfer_for_the_same_source(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    calls = []
    entered, release = threading.Event(), threading.Event()
    def fetch(source, *_args, **_kwargs):
        calls.append(source["url"])
        entered.set()
        assert release.wait(2)
        return b"shared input"
    monkeypatch.setattr(packages, "fetch_source", fetch)
    sources = [{"id": ident, "url": "https://games.test/shared.zip"} for ident in ("one", "two")]
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(packages.download_package, source, tmp_path, 100) for source in sources]
        assert entered.wait(1)
        release.set()
        assert all(future.result(timeout=2)[0] == b"shared input" for future in futures)
    assert calls == ["https://games.test/shared.zip"]
    assert all((tmp_path / packages.package_cache_path(source)).read_bytes() == b"shared input" for source in sources)


def test_successful_reuse_refreshes_retention_but_failed_processing_does_not(tmp_path):
    cached = put(tmp_path / "archive.zip", age=45)
    before = cached.stat().st_mtime
    def fetch(_path):
        pytest.fail("Existing cache should be reused")
    def invalid(_path):
        raise ValueError("wrong archive")
    with pytest.raises(ValueError):
        download_cached(cached, 100, fetch, process=invalid)
    assert cached.stat().st_mtime == before
    assert download_cached(cached, 100, fetch).read_bytes() == b"archive"
    assert cached.stat().st_mtime >= time.time() - 2


@pytest.mark.parametrize("linked", ["parent", "metadata"])
def test_readable_cache_refuses_linked_storage(tmp_path, linked):
    elsewhere = tmp_path / "outside"
    elsewhere.mkdir()
    cached = tmp_path / "cache" / "game.zip"
    if linked == "parent":
        cached.parent.symlink_to(elsewhere, target_is_directory=True)
    else:
        cached.parent.mkdir()
        cache_metadata_path(cached).symlink_to(elsewhere / "identity.json")
    with pytest.raises(UnsafeContentError):
        download_cached(cached, 100, lambda _path: pytest.fail("Unsafe cache reached fetch"), identity="key")
    assert not list(elsewhere.iterdir())


def test_one_time_migration_keeps_cache_bytes_mtime_and_reuses_without_network(tmp_path, monkeypatch):
    source = {"id": "game", "url": "https://games.test/game.zip", "format": "zip"}
    old = put(tmp_path / packages.package_cache_key(source), age=10)
    timestamp = old.stat().st_mtime_ns
    unmapped = put(tmp_path / ("f" * 64), b"unmapped")
    assert packages.migrate_package_cache([source], tmp_path) == {"moved": 1, "unmapped": 1}
    target = tmp_path / "game/game.zip"
    assert not old.exists() and target.read_bytes() == b"archive"
    assert target.stat().st_mtime_ns == timestamp
    assert unmapped.read_bytes() == b"unmapped"
    assert packages.migrate_package_cache([source], tmp_path) == {"moved": 0, "unmapped": 1}
    monkeypatch.setattr(packages, "fetch_source", lambda *_args, **_kwargs: pytest.fail("Migrated cache was not reused"))
    assert packages.download_package(source, tmp_path, 100)[0] == b"archive"


def test_migration_includes_alternatives_and_collection_components(tmp_path):
    source = {"id": "tools", "format": "collection", "archives": [
        {"url": "https://one.test/a.zip"}, {"url": "https://one.test/b.zip"}],
        "alternatives": [{"url": "https://other.test/all.zip", "format": "zip"}]}
    primary = {key: value for key, value in source.items() if key != "alternatives"}
    recipes = [primary, {"id": "tools", **source["alternatives"][0]},
               *({"id": f"tools-{index}", **entry} for index, entry in enumerate(source["archives"]))]
    for recipe in recipes:
        put(tmp_path / packages.package_cache_key(recipe))
    assert packages.migrate_package_cache([source], tmp_path) == {"moved": 4, "unmapped": 0}
    assert all((tmp_path / packages.package_cache_path(recipe)).read_bytes() == b"archive" for recipe in recipes)


def test_migration_preflights_every_collision_before_removing_any_original(tmp_path):
    sources = [{"id": ident, "url": f"https://games.test/{ident}.zip"} for ident in ("one", "two")]
    old = [put(tmp_path / packages.package_cache_key(source)) for source in sources]
    collision = put(tmp_path / packages.package_cache_path(sources[1]), b"keep different cache")
    with pytest.raises(ValueError, match="conflict"):
        packages.migrate_package_cache(sources, tmp_path)
    assert all(path.read_bytes() == b"archive" for path in old)
    assert collision.read_bytes() == b"keep different cache"
    assert not (tmp_path / packages.package_cache_path(sources[0])).exists()


def test_migration_does_not_clobber_same_name_alternative_slots_or_loop_on_restart(tmp_path):
    primary = {"id": "game", "url": "https://one.test/game.zip"}
    alternate = {"id": "game", "url": "https://two.test/game.zip"}
    source = {**primary, "alternatives": [{"url": alternate["url"]}]}
    for recipe in (primary, alternate):
        put(tmp_path / packages.package_cache_key(recipe), recipe["url"].encode())
    assert packages.migrate_package_cache([source], tmp_path) == {"moved": 1, "unmapped": 1}
    cached = tmp_path / packages.package_cache_path(primary)
    assert cached.read_bytes() == primary["url"].encode()
    assert packages.migrate_package_cache([source], tmp_path) == {"moved": 0, "unmapped": 1}
    assert cached.read_bytes() == primary["url"].encode()


def test_inventory_cache_reads_the_matching_alternative_without_network(tmp_path, monkeypatch):
    source = {"id": "game", "url": "https://one.test/game.zip", "alternatives": [
        {"url": "https://two.test/game.zip", "format": "zip"}]}
    alternate = {"id": "game", **source["alternatives"][0]}
    monkeypatch.setattr(packages, "fetch_source", lambda *_args, **_kwargs: b"archive")
    packages.download_package(alternate, tmp_path, 100)
    monkeypatch.setattr(packages, "fetch_source", lambda *_args, **_kwargs: pytest.fail("Ownership recovery reached network"))
    result = packages.read_package_cache(source, tmp_path, 100, process=lambda data, recipe: (data, recipe["url"]))
    assert result == (b"archive", alternate["url"])


def test_expiration_uses_payload_age_and_removes_companion_metadata(tmp_path):
    root = tmp_path / "downloads"
    old = [put(root / kind / "nested/old.zip", age=31) for kind in ("help", "dos", "midi")]
    fresh = put(root / "dos/nested/recent.zip", age=2)
    old_metadata = put(cache_metadata_path(old[1]), b"new metadata")
    fresh_metadata = put(cache_metadata_path(fresh), b"old metadata", age=50)
    unrelated = put(root / "README.txt", age=100)
    protected = put(tmp_path / "var/sources/Manual.HLP", age=100)
    result = clear_download_cache(root, protected_paths=(protected.parent,), older_than=time.time()-30*86400)
    assert result["files"] == 4
    assert all(not path.exists() for path in [*old, old_metadata])
    assert all(path.is_file() for path in (fresh, fresh_metadata, unrelated, protected))
    assert (root / "dos/nested").is_dir() and not (root / "help/nested").exists()


def test_expiration_defers_for_active_jobs_then_applies_current_setting(tmp_path):
    config = replace(config_for(tmp_path), data_dir=tmp_path / "data")
    settings = ServerSettings(tmp_path / "settings.json")
    downloads = OnlineDownloader()
    cache = DownloadCache(config, settings, downloads)
    old = put(cache.root / "help/old.zip", age=31)
    recent = put(cache.root / "dos/recent.zip", age=10)
    try:
        downloads.begin("help", [{"id": "one", "label": "Converting"}])
        with pytest.raises(ValueError, match="Wait for downloads"):
            cache.clear(expired_only=True)
        assert old.exists()
        downloads.finish("help")
        assert cache.clear(expired_only=True)["files"] == 1 and recent.exists()
        settings.update({"download_cache_days": 7})
        assert cache.clear(expired_only=True)["files"] == 1 and not recent.exists()
    finally:
        downloads.close()


def test_server_expires_downloads_and_originals_at_startup_and_periodically(tmp_path, monkeypatch):
    config = replace(config_for(tmp_path), data_dir=tmp_path / "data")
    old = put(config.downloads_dir / "help/old.zip", age=31)
    expired = put(config.sources_dir / "Old/Manual.HLP", age=100)
    expired_licence = put(config.sources_dir / "Old/LICENCE.TXT", age=100)
    kept = put(config.sources_dir / "Current/Manual.HLP", age=.25)
    installed = put(config.state_dir / "dos/c/GAME.EXE", age=100)
    monkeypatch.setattr(maintenance, "CACHE_SWEEP_SECONDS", .01)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        assert all(not path.exists() for path in (old, expired, expired_licence))
        assert not expired.parent.exists()
        assert kept.read_bytes() == installed.read_bytes() == b"archive"
        admin_session(app, client)
        recent = put(config.downloads_dir / "midi/recent.zip", age=2)
        recent_source = put(config.sources_dir / "Other/HELP.HLP", age=2)
        assert recent.exists()
        response = client.put("/api/admin/settings", headers={"Origin": config.auth_origin},
            json={"dos_user_disk_mb": 64, "backup_count": 2, "download_cache_days": 1})
        assert response.status_code == 200
        deadline = time.monotonic() + 2
        while (recent.exists() or recent_source.exists()) and time.monotonic() < deadline:
            time.sleep(.01)
        assert not recent.exists() and not recent_source.exists()
        assert kept.is_file() and installed.is_file()


def test_help_originals_do_not_expire_during_active_processing(tmp_path):
    config = replace(config_for(tmp_path), data_dir=tmp_path / "data")
    downloads = OnlineDownloader()
    cache = DownloadCache(config, ServerSettings(tmp_path / "settings.json"), downloads)
    original = put(config.sources_dir / "Old/HELP.HLP", age=31)
    try:
        downloads.begin("help", [{"id": "one", "label": "Converting"}])
        with pytest.raises(ValueError, match="Wait for downloads"):
            cache.clear(expired_only=True)
        assert original.is_file()
        downloads.finish("help")
        assert cache.clear(expired_only=True)["files"] == 1 and not original.exists()
    finally:
        downloads.close()


def test_source_ingestion_reuse_refreshes_age_but_conflicts_do_not(tmp_path):
    from thelpviewer.server.converter.sources import copy_help_files
    source = put(tmp_path / "incoming/HELP.HLP", b"original")
    root = tmp_path / "sources"
    target = put(root / "Manual/HELP.HLP", b"original", age=45)
    assert copy_help_files([source], target.parent, root) == []
    assert target.stat().st_mtime >= time.time() - 2
    before = time.time() - 45 * 86400
    os.utime(target, (before, before))
    before = target.stat().st_mtime
    source.write_bytes(b"conflict")
    with pytest.raises(ValueError, match="Conflicting original"):
        copy_help_files([source], target.parent, root)
    assert target.stat().st_mtime == before


@pytest.mark.parametrize("fails", [False, True])
def test_only_successful_help_conversion_refreshes_input_age(tmp_path, monkeypatch, fails):
    from thelpviewer.server.converter.build import build_help_groups
    from thelpviewer.server.converter.results import ConversionError
    from thelpviewer.server.converter.writers import bundle
    config = config_for(tmp_path)
    source = put(config.sources_dir / "HelpPC 2.10/C.TXT",
        b"@C language\r\n:Reference\r\n%Help text\r\n", age=45)
    before = source.stat().st_mtime
    if fails:
        def invalid(*_args, **_kwargs):
            raise ValueError("Invalid HELP input")
        monkeypatch.setattr(bundle, "_write_document_bundle", invalid)
        with pytest.raises(ConversionError):
            build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir)
        assert source.stat().st_mtime == before
    else:
        build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir)
        assert source.stat().st_mtime >= time.time() - 2


def test_cancelling_maintenance_waits_for_inflight_filesystem_work(tmp_path, monkeypatch):
    import threading
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    config = config_for(tmp_path)
    downloads = OnlineDownloader()
    cache = DownloadCache(config, ServerSettings(tmp_path / "settings.json"), downloads)
    def clear(**_kwargs):
        started.set()
        release.wait(2)
        finished.set()
        return {"files": 0, "bytes": 0}
    monkeypatch.setattr(cache, "clear", clear)
    async def scenario():
        task = asyncio.create_task(cache.sweep())
        assert await asyncio.to_thread(started.wait, 1)
        task.cancel()
        await asyncio.sleep(.01)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert finished.is_set()
    try:
        asyncio.run(scenario())
    finally:
        release.set()
        downloads.close()
