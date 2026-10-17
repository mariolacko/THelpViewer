"""Explicit cache cleanup includes HELP originals but protects installed data."""

from dataclasses import replace
from pathlib import Path
import threading

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.app import create_app
from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.downloader.cache import clear_download_cache
from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.processing import UnsafeContentError
from test_server_content import admin_session, config_for


def put(path, payload=b"cached download"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_cleanup_removes_only_raw_downloads_and_abandoned_staging(tmp_path):
    root = tmp_path / "var/downloads"
    cache = [put(root / name) for name in (
        "help/archive.zip", "help/.download-abandoned/source.zip", "dos/source.7z", "midi/source.zip")]
    protected = [put(tmp_path / name, b"keep") for name in (
        "var/sources/HELP.HLP", "data/helps/help.json.gz", "data/dos/users/user/SAVE.DAT",
        "data/accounts.sqlite3", "var/dos/c/GAME.EXE", "var/midi/tracks/track.mid",
        "var/midi/covers/cover.png", "var/backups/previous/source", "var/search/index.sqlite3")]
    unknown = put(root / "README.txt", b"unrelated")
    result = clear_download_cache(root, protected_paths=(tmp_path / "data", tmp_path / "var/sources",
                                                        tmp_path / "var/dos", tmp_path / "var/midi"))
    assert result == {"files": 4, "bytes": 4 * len(b"cached download")}
    assert not any(path.exists() for path in cache)
    assert all(list((root / kind).iterdir()) == [] for kind in ("help", "dos", "midi"))
    assert all(path.read_bytes() == b"keep" for path in protected)
    assert unknown.read_bytes() == b"unrelated"
    assert clear_download_cache(root, protected_paths=(tmp_path / "data",)) == {"files": 0, "bytes": 0}


def test_manual_cleanup_includes_all_help_inputs_and_licences(tmp_path):
    root, sources = tmp_path / "var/downloads", tmp_path / "var/sources"
    removed = [put(root / "help/source.zip"), put(root / "dos/package.zip"),
               put(root / "midi/album.zip"), put(sources / "Manual/HELP.HLP"),
               put(sources / "Manual/LICENCE.TXT"), put(sources / "empty-named/unknown.bin")]
    (sources / "empty").mkdir()
    retained = [put(tmp_path / name, b"keep") for name in (
        "data/helps/help.json.gz", "data/docs/guide.md", "data/accounts.sqlite3",
        "data/dos/users/user/SAVE.DAT", "var/dos/c/GAME.EXE", "var/midi/tracks/song.mid",
        "var/backups/help/previous.json.gz", "var/global-search.sqlite3")]
    unrelated = put(root / "README.txt", b"keep")
    result = clear_download_cache(root, sources_dir=sources, protected_paths=(
        tmp_path / "data", tmp_path / "var/dos", tmp_path / "var/midi", tmp_path / "var/backups"))
    assert result == {"files": len(removed), "bytes": len(removed) * len(b"cached download")}
    assert not any(path.exists() for path in removed)
    assert sources.is_dir() and list(sources.iterdir()) == []
    assert all(path.read_bytes() == b"keep" for path in [*retained, unrelated])
    assert clear_download_cache(root, sources_dir=sources, protected_paths=(tmp_path / "data",)) == {"files": 0, "bytes": 0}


@pytest.mark.parametrize("unsafe", ["root-link", "ancestor-link", "child-link", "fifo", "file", "overlap", "downloads", "broad"])
def test_invalid_help_input_scope_keeps_every_cache_file(tmp_path, unsafe):
    root, sources = tmp_path / "downloads", tmp_path / "sources"
    archive = put(root / "help/source.zip")
    original = put(sources / "Manual/HELP.HLP")
    protected = put(tmp_path / "data/keep.bin", b"permanent")
    if unsafe == "root-link":
        linked = tmp_path / "linked"
        linked.symlink_to(sources, target_is_directory=True)
        sources = linked
    elif unsafe == "ancestor-link":
        linked = tmp_path / "linked"
        linked.symlink_to(tmp_path, target_is_directory=True)
        sources = linked / "sources"
    elif unsafe == "child-link":
        (sources / "last-link").symlink_to(protected)
    elif unsafe == "fifo":
        import os
        os.mkfifo(sources / "pipe")
    elif unsafe == "file":
        sources = original
    elif unsafe == "overlap":
        sources = protected.parent
    elif unsafe == "downloads":
        sources = root / "help"
    elif unsafe == "broad":
        sources = Path.home()
    with pytest.raises(ValueError):
        clear_download_cache(root, sources_dir=sources, protected_paths=(protected.parent,))
    assert archive.read_bytes() == original.read_bytes() == b"cached download"
    assert protected.read_bytes() == b"permanent"


def test_help_input_expiry_uses_the_same_cutoff_as_raw_downloads(tmp_path):
    import os
    archive = put(tmp_path / "downloads/help/source.zip")
    original = put(tmp_path / "sources/HELP.HLP")
    recent = put(original.parent / "recent.HLP")
    for path in (archive, original):
        os.utime(path, (1, 1))
    result = clear_download_cache(tmp_path / "downloads", sources_dir=original.parent,
                                  protected_paths=(), older_than=2)
    assert result == {"files": 2, "bytes": 2 * len(b"cached download")}
    assert not archive.exists() and not original.exists()
    assert recent.is_file()


@pytest.mark.parametrize("link_location", ["root", "scope", "file", "ancestor"])
def test_cleanup_refuses_links_before_deleting_any_cache(tmp_path, link_location):
    root = tmp_path / "downloads"
    first = put(root / "help/keep.zip")
    outside = put(tmp_path / "outside/keep.zip", b"permanent")
    if link_location == "root":
        link = tmp_path / "linked"
        link.symlink_to(root, target_is_directory=True)
        root = link
    elif link_location == "ancestor":
        link = tmp_path / "linked"
        link.symlink_to(tmp_path / "outside", target_is_directory=True)
        root = link / "downloads"
    elif link_location == "scope":
        (root / "midi").symlink_to(outside.parent, target_is_directory=True)
    else:
        (root / "help/link.zip").symlink_to(outside)
    with pytest.raises(UnsafeContentError):
        clear_download_cache(root, protected_paths=(outside.parent,))
    assert first.read_bytes() == b"cached download" and outside.read_bytes() == b"permanent"


def test_cleanup_rejects_overlapping_installed_content_and_broad_roots(tmp_path):
    root = tmp_path / "downloads"
    archive = put(root / "help/keep.zip")
    for protected in (root, root / "dos", root / "dos/users"):
        with pytest.raises(UnsafeContentError, match="overlaps"):
            clear_download_cache(root, protected_paths=(protected,))
        assert archive.is_file()
    for broad in (Path("/"), Path.home(), Path.cwd()):
        with pytest.raises(ValueError, match="own directory"):
            clear_download_cache(broad, protected_paths=())


def test_cleanup_does_not_read_unavailable_archive_payloads(tmp_path, monkeypatch):
    root = tmp_path / "downloads"
    archive = put(root / "help/cloud-placeholder.zip")
    def unavailable(*_args, **_kwargs):
        raise OSError("Input/output error")
    monkeypatch.setattr(Path, "open", unavailable)
    assert clear_download_cache(root, protected_paths=()) == {"files": 1, "bytes": len(b"cached download")}
    assert not archive.exists()


@pytest.mark.parametrize("processing", [False, True])
def test_maintenance_rejects_active_pipeline_and_blocks_new_work_until_done(processing):
    downloads = OnlineDownloader()
    release, active = threading.Event(), threading.Event()
    submit = downloads.enqueue_processing if processing else downloads.enqueue
    future = submit(lambda: active.set() or release.wait(5))
    try:
        assert active.wait(2)
        with pytest.raises(ValueError, match="Wait for downloads"):
            with downloads.maintenance():
                pytest.fail("Maintenance ran beside an active writer")
        release.set()
        future.result(timeout=2)
        with downloads._changed:
            assert downloads._changed.wait_for(lambda: not downloads._sources, timeout=2)
        started, submitted = threading.Event(), threading.Event()
        def submit():
            started.set()
            downloads.enqueue(lambda: None).result(timeout=2)
            submitted.set()
        with downloads.maintenance():
            thread = threading.Thread(target=submit)
            thread.start()
            assert started.wait(2) and not submitted.wait(.05)
        assert submitted.wait(2)
        thread.join(timeout=2)
    finally:
        release.set()
        downloads.close()


@pytest.mark.parametrize("custom_sources", [False, True])
def test_cache_api_requires_admin_origin_and_idle_processing(tmp_path, custom_sources):
    config = replace(config_for(tmp_path), data_dir=tmp_path / "data",
                     sources_dir=tmp_path / "custom-inputs" if custom_sources else None)
    app = create_app(config)
    sources = config.sources_dir or config.state_dir / "sources"
    originals = [put(sources / name, b"manual input")
                 for name in ("Manual/HELP.HLP", "Manual/LICENCE.TXT")]
    archive = put(config.downloads_dir / "help/source.zip")
    protected = [put(path, b"published") for path in (
        config.helps_dir / "published.json.gz", config.docs_dir / "manual.md",
        config.persistent_dir / "dos/users/user/SAVE.DAT", config.state_dir / "dos/c/GAME.EXE",
        config.state_dir / "midi/tracks/track.mid", config.state_dir / "backups/help/previous.json.gz")]
    origin = {"Origin": config.auth_origin}
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.post("/api/admin/cache/clear", headers=origin).status_code == 403
        admin_session(app, client)
        admin_cookie = client.cookies.get("thelp_session")
        app.state.accounts.create_user("member")
        with app.state.accounts._connect() as database:
            account = database.execute("SELECT id FROM accounts WHERE username='member'").fetchone()[0]
            member_cookie = new_session(database, account)
        client.cookies.set("thelp_session", member_cookie)
        assert client.post("/api/admin/cache/clear", headers=origin).status_code == 403
        client.cookies.set("thelp_session", admin_cookie)
        assert client.post("/api/admin/cache/clear", headers={"Origin": "https://evil.test"}).status_code == 403
        assert client.get("/api/admin/cache/clear").status_code == 405
        app.state.downloads.begin("help", [{"id": "test", "label": "Converting HELP"}])
        response = client.post("/api/admin/cache/clear", headers=origin)
        assert response.status_code == 409 and "Wait for downloads" in response.json()["detail"]
        assert archive.is_file() and all(path.is_file() for path in originals)
        app.state.downloads.finish("help", error="Test cancelled")
        response = client.post("/api/admin/cache/clear", headers=origin)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert response.json() == {"files": 3, "bytes": len(b"cached download") + 2 * len(b"manual input")}
        assert not archive.exists()
        assert not any(path.exists() for path in originals)
        assert list(sources.iterdir()) == []
        assert all(path.read_bytes() == b"published" for path in protected)
        assert app.state.content.sources_dir == sources
        settings = client.get("/api/admin/settings").json()
        assert settings["runtime"]["sources_dir"] == str(sources)
        assert app.state.accounts.list_users(admin_cookie)
