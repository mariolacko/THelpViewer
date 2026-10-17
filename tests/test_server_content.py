"""Content setup calls modules, publishes safely and never touches private disks."""

from dataclasses import replace
import gzip
import io
import json
from pathlib import Path
import time
import threading
import zipfile

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.downloader.service import DownloadResult, download_products
from thelpviewer.server.downloader.transport import download_chunks, public_url
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.content import ContentJob


def config_for(tmp_path):
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [
        {"id": "one", "title": "One", "url": "https://packages.test/one.zip", "format": "zip", "target": "GAMES/ONE"},
        {"id": "two", "title": "Two", "url": "https://packages.test/two.zip", "format": "zip", "target": "GAMES/TWO", "enabled": False},
    ], "files": [{"path": "AUTOEXEC.BAT", "text": ["@echo off"]}]}))
    midi = tmp_path / "midi.json"
    midi.write_text('{"sources": []}')
    return replace(load_config(), helps_dir=tmp_path / "helps", sources_dir=tmp_path / "sources",
        downloads_dir=tmp_path / "var" / "downloads", state_dir=tmp_path / "var",
        statistics_path=tmp_path / "var" / "statistics.sqlite3", docs_dir=tmp_path / "docs",
        virtual_docs=(), dos_config_path=manifest, midi_sources_path=midi,
        dev_auto_login=False, auth_origin="https://testserver")


def admin_session(app, client):
    app.state.accounts.create_user("administrator")
    with app.state.accounts._connect() as database:
        ident = database.execute("SELECT id FROM accounts").fetchone()[0]
        token = new_session(database, ident)
    client.cookies.set("thelp_session", token)
    return ident


def wait_job(client):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = client.get("/api/admin/content/status").json()
        if status["state"] != "building":
            return status
        assert 0 <= status["percent"] <= 100
        time.sleep(.01)
    raise AssertionError("Content job did not finish")


def join_content_jobs(content, timeout=10):
    for job in content._jobs:
        if job.worker:
            job.worker.join(timeout=timeout)
            assert not job.worker.is_alive()


@pytest.mark.parametrize("fail_last", [False, True])
def test_help_stages_overlap_and_publish_each_edition_before_later_failure(tmp_path, monkeypatch, fail_last):
    from types import SimpleNamespace
    from thelpviewer.server.downloader import service
    from thelpviewer.server.downloader.transport import read_request
    from thelpviewer.server.converter import build, selection
    from thelpviewer.server.processing import report_progress

    manifest = json.loads(Path("thelpviewer/config/help-database.json").read_text())
    product = next(product for product in manifest["products"] if product["key"] == "tp")
    product["versions"] = sorted(set(product.get("versions", [])) | {"5.0", "5.5", "6.0"})
    for query in product["sources"].values():
        query["archive_members"] = ["REFERENCE.TXT"]
    database = tmp_path / "help-database.json"
    database.write_text(json.dumps(manifest))
    monkeypatch.setenv("THELP_HELP_DATABASE_PATH", str(database))
    config = config_for(tmp_path)
    # A later error must retain both existing published content and originals.
    original = config.sources_dir / "HelpPC 2.10/C.TXT"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"@C\r\n:Original\r\n%Existing library\r\n")
    build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir)
    previous = {path.relative_to(config.helps_dir): path.read_bytes()
                for path in config.helps_dir.rglob("*") if path.is_file()}
    first_extract, second_extract, converting, third_transfer, release = (threading.Event() for _ in range(5))
    app = create_app(config)
    monkeypatch.setattr(service, "all_sources", lambda: ["direct"])
    monkeypatch.setattr(service, "supported_product_keys", lambda _: ["tp"])
    monkeypatch.setattr(service, "_verified_sources", lambda *_: None)
    monkeypatch.setattr(service, "find_sevenzip", lambda: "7zz")

    class Response(io.BytesIO):
        headers = {"Content-Length": "4"}
        def __init__(self, url):
            self.url = url
            super().__init__(b"help")
        def read(self, count):
            if self.url.endswith("6.0"):
                third_transfer.set()
                assert release.wait(5)
            return super().read(count)
    opener = SimpleNamespace(open=lambda url, **_kwargs: Response(url))

    def provider(**_kwargs):
        version, = [version for version in ("5.0", "5.5", "6.0") if selection.version_selected("tp", version)]
        if version == "5.5":
            assert first_extract.wait(5)
        elif version == "6.0":
            assert converting.wait(5)
        read_request(opener, "https://source.test/" + version, 1024)
        report_progress("Extracting archive", version, stage="extract")
        if version == "5.0":
            first_extract.set()
            assert second_extract.wait(5)
        elif version == "5.5":
            second_extract.set()
            assert release.wait(5)
        source = config.sources_dir / ("Borland Turbo Pascal " + version) / "REFERENCE.TXT"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"@Pascal\r\n:Reference\r\n%" + version.encode() + b"\r\n")
        if version == "6.0" and fail_last:
            source.write_bytes(b"invalid HELP payload")
        return [source]
    import_module = service.importlib.import_module
    monkeypatch.setattr(service.importlib, "import_module", lambda name: SimpleNamespace(run=provider)
        if name in service.SOURCE_RUNNERS.values() else import_module(name))
    export = build.export_bundle_tree
    def convert(*args, source_paths, on_progress, **kwargs):
        if source_paths[0].parent.name.endswith("5.0"):
            on_progress({"phase": "Converting", "stage": "convert", "processed": 0, "total": 1})
            converting.set()
            assert second_extract.wait(5) and third_transfer.wait(5)
            rows = {item["id"]: item for item in app.state.downloads.snapshot(private=True)["items"]}
            assert rows["help:tp:5.0"]["stage"] == "convert"
            assert rows["help:tp:5.5"]["stage"] == "extract"
            assert rows["help:tp:6.0"]["stage"] == "download"
            assert rows["help:tp:5.0"]["percent"] == 35
            assert {path.relative_to(config.helps_dir): path.read_bytes()
                    for path in config.helps_dir.rglob("*") if path.is_file()} == previous
            release.set()
        return export(*args, source_paths=source_paths, on_progress=on_progress, **kwargs)
    monkeypatch.setattr(build, "export_bundle_tree", convert)
    try:
        app.state.content.start(help_packages=["helppc:", "tp:5.0", "tp:5.5", "tp:6.0"])
        join_content_jobs(app.state.content)
        status = app.state.content.status()
        assert converting.is_set() and third_transfer.is_set()
        assert status["state"] == ("error" if fail_last else "ready"), status
        current = {path.relative_to(config.helps_dir): path.read_bytes()
                   for path in config.helps_dir.rglob("*") if path.is_file()}
        if fail_last:
            assert current[Path("HelpPC 2.10/c.json.gz")] == previous[Path("HelpPC 2.10/c.json.gz")]
            assert all((config.helps_dir / f"Borland Turbo Pascal {version}/reference.json.gz").is_file()
                       for version in ("5.0", "5.5"))
            assert not (config.helps_dir / "Borland Turbo Pascal 6.0/reference.json.gz").exists()
            rows = {row["id"]: row for row in app.state.downloads.snapshot(private=True)["items"]}
            assert rows["help:tp:6.0"]["state"] == "error", status["error"]
            for edition in ("5.0", "5.5"):
                assert rows["help:tp:" + edition]["state"] == "done"
                assert not rows["help:tp:" + edition]["error"]
            assert sum(row["state"] == "error" for row in rows.values()) == 1
        else:
            assert all((config.helps_dir / f"Borland Turbo Pascal {version}/reference.json.gz").is_file()
                       for version in ("5.0", "5.5", "6.0"))
        assert original.read_bytes() == b"@C\r\n:Original\r\n%Existing library\r\n"
        assert not list(config.helps_dir.parent.glob(".helps-build-*"))
    finally:
        release.set()
        app.state.downloads.close()


def test_global_build_progress_does_not_start_every_edition(tmp_path):
    app = create_app(config_for(tmp_path))
    editions = ["tp:5.0", "tp:5.5"]
    app.state.downloads.begin("help", [{"id": ident, "label": ident} for ident in editions])
    try:
        values = {"help_packages": editions, "dos_packages": []}
        ident = app.state.jobs.create("content", {"values": values, "scope": ["help"], "configured": True})
        job = ContentJob(ident, values, {"help"}, True)
        app.state.content._help_build_progress(job,
            {"phase": "Checking HELP selection", "processed": 1, "total": 2}, editions)
        assert all(row["state"] == "pending" for row in app.state.downloads.snapshot(private=True)["items"])
    finally:
        app.state.downloads.close()


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("registered", [True, False])
def test_help_api_fallback_requires_crc_or_successful_conversion(tmp_path, monkeypatch, valid, registered):
    import zlib
    from types import SimpleNamespace
    from urllib.error import HTTPError
    from thelpviewer.help_database import HelpDatabaseEntry, load_help_manifest
    from thelpviewer.server.downloader import archiveorg, http, service, transport, winworld

    config = config_for(tmp_path)
    old = config.sources_dir / "FreeDOS HTML Help 1.1.1a" / "HHSTNDRD.ZIP"
    old.parent.mkdir(parents=True)
    with zipfile.ZipFile(old, "w") as output:
        output.writestr("help/index.htm", "<title>Contents</title><p>Existing FreeDOS help</p>")
    build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir)
    published = {path: path.read_bytes() for path in config.helps_dir.rglob("*") if path.is_file()}
    payload = b"@C language\r\n:Reference\r\n%Help text\r\n"
    manifest = load_help_manifest()
    entry = HelpDatabaseEntry(crc32=zlib.crc32(payload), filenames=("C.TXT",), title="HelpPC",
        collection="HelpPC 2.10", product_key="helppc")
    monkeypatch.setattr(service, "load_help_manifest", lambda: replace(manifest, entries=(entry,) if registered else ()))
    monkeypatch.setattr(service, "all_sources", lambda: ["winworld", "archiveorg"])
    monkeypatch.setattr(service, "supported_product_keys", lambda _: ["helppc"])
    monkeypatch.setattr(service, "find_unar", lambda: "unar")
    monkeypatch.setattr(service, "find_lsar", lambda: "lsar")
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    monkeypatch.setattr(transport, "defer_source", lambda *_: None)
    requests, calls = [], []
    def limited(url, **_kwargs):
        requests.append(url)
        raise HTTPError(url, 429, "quota", {"Retry-After": "0"}, None)
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=limited))
    def first(**kwargs):
        calls.append("first")
        http.download_file("https://limited.test/help", kwargs["dl_dir"] / "Help.zip")
    def fallback(**kwargs):
        calls.append("fallback")
        source = config.sources_dir / entry.collection / "C.TXT"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(payload if valid else b"unverified contents")
        return [source]
    monkeypatch.setattr(winworld, "run", first)
    monkeypatch.setattr(archiveorg, "run", fallback)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        selection = ["helppc:"] + [row["id"] for row in client.get("/api/admin/content").json()["help_packages"]
                                  if row["installed"]]
        response = client.post("/api/admin/content", json={"help_packages": selection}, headers={"Origin": config.auth_origin})
        assert response.status_code == 202, response.text
        status = wait_job(client)
        assert calls == ["first", "fallback"] and len(requests) == 3
        assert status["state"] == ("ready" if valid else "error"), status
        assert len(status["warnings"]) == 1 and "429" in status["warnings"][0]
        assert (config.helps_dir / "HelpPC 2.10/c.json.gz").exists() is valid
        assert all(path.read_bytes() == data for path, data in published.items()
                   if path.name != "catalog.json" or not valid)
        row = next(row for row in client.get("/api/downloads").json()["items"] if row["id"] == "help:helppc:")
        assert row["state"] == ("done" if valid else "error")
        assert row["total"] == 1
        if not valid:
            assert not next(row for row in client.get("/api/admin/content").json()["help_packages"]
                            if row["id"] == "helppc:")["installed"]


def test_first_run_is_read_only_until_admin_confirms_and_empty_means_none(tmp_path):
    config = config_for(tmp_path)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.get("/api/admin/content").status_code == 403
        assert client.post("/api/admin/content", json={"help_packages": [], "dos_packages": []}).status_code == 403
        admin_session(app, client)
        first = client.get("/api/admin/content").json()
        assert first["needs_setup"] and not first["configured"]
        assert first["selection"] == {"help_packages": [], "dos_packages": []}
        assert all(item["language"] == "und" for item in first["dos_packages"])
        assert app.state.dos_prompt.state == "idle"
        assert not config.sources_dir.exists() and not config.downloads_dir.exists()
        selection = {"help_packages": [], "dos_packages": []}
        assert client.post("/api/admin/content", json=selection, headers={"Origin": "https://evil.test"}).status_code == 403
        assert client.post("/api/admin/content", json={**selection, "url": "https://evil.test"},
                           headers={"Origin": config.auth_origin}).status_code == 422
        assert client.post("/api/admin/content", json={**selection, "dos_packages": ["unknown"]},
                           headers={"Origin": config.auth_origin}).status_code == 409
        assert not app.state.content.path.exists()
        response = client.post("/api/admin/content", json=selection, headers={"Origin": config.auth_origin})
        assert response.status_code == 202
        assert wait_job(client)["state"] == "ready"
        assert app.state.dos_prompt.state == "idle"  # No implicit all-packages fallback.
        assert not config.sources_dir.exists() and not config.downloads_dir.exists()
        assert client.get("/api/admin/content").json()["configured"]
    restarted = create_app(config)
    assert not restarted.state.content.choices()["needs_setup"]
    assert restarted.state.content.selected_dos() == []


def test_removed_manifest_packages_do_not_break_saved_selection_or_unrelated_help_changes(tmp_path):
    config = config_for(tmp_path)
    app = create_app(config)
    app.state.content._save_selection({"configured": True, "help_packages": [],
        "dos_packages": ["one", "removed-source-package"]})
    assert app.state.content.selected_dos() == ["one"]
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        headers = {"Origin": config.auth_origin}
        assert client.post("/api/admin/content", json={"help_packages": []}, headers=headers).status_code == 202
        assert wait_job(client)["state"] == "ready"
        assert json.loads(app.state.content.path.read_text())["dos_packages"] == ["one"]
        assert not app.state.dos_prompt.disk_dir.exists()  # No implicit DOS install/removal.
        assert client.post("/api/admin/content", json={"dos_packages": ["removed-source-package"]},
                           headers=headers).status_code == 409


def test_required_dos_packages_are_selected_and_cannot_be_removed_through_api(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    manifest = json.loads(config.dos_config_path.read_text())
    manifest["sources"][1]["required"] = True  # Enabled=false must not make a required package optional.
    config.dos_config_path.write_text(json.dumps(manifest))
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"game")
    downloaded = []
    def fetch(source, *args, **kwargs):
        downloaded.append(source["id"])
        return archive.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        headers = {"Origin": config.auth_origin}
        choices = client.get("/api/admin/content").json()
        assert choices["selection"]["dos_packages"] == ["two"]
        assert [item["required"] for item in choices["dos_packages"]] == [False, True]
        assert not choices["dos_packages"][1]["installed"]
        assert not downloaded and not config.downloads_dir.exists()  # Opening settings is read-only.
        app.state.content._save_selection({"configured": False, "help_packages": [], "dos_packages": []})
        assert app.state.content.selected_dos() == ["two"]
        # HELP-only setup neither installs DOS nor remains stuck on its mandatory defaults.
        client.post("/api/admin/content", json={"help_packages": []}, headers=headers)
        assert wait_job(client)["state"] == "ready"
        assert not downloaded and not app.state.dos_prompt.disk_dir.exists()
        assert client.get("/api/admin/content").json()["configured"]
        for selected in (["one"], []):
            assert client.post("/api/admin/content", json={"dos_packages": selected}, headers=headers).status_code == 202
            assert wait_job(client)["state"] == "ready"
            assert app.state.dos_prompt.files["GAMES/TWO/GAME.EXE"] == b"game"
            assert "two" in json.loads(app.state.dos_prompt.installed_path.read_text())
            assert "two" in json.loads(app.state.content.path.read_text())["dos_packages"]
        assert "GAMES/ONE/GAME.EXE" not in app.state.dos_prompt.files
        assert client.get("/api/admin/content").json()["selection"]["dos_packages"] == ["two"]
    restarted = create_app(config)
    assert restarted.state.content.selected_dos() == ["two"]


def test_help_and_dos_installation_updates_catalog_index_and_keeps_private_data(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10" / "C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:ReferenceTopic\r\n%Reference search text\r\n")
    selected_products = []
    def download(products, sources, cache, on_progress, *, downloads, package_ids, preserve_downloads, finalize, on_ready):
        assert preserve_downloads
        assert not finalize
        assert package_ids == (["helppc:"] if products else [])
        selected_products.extend(products)
        assert sources == config.sources_dir and cache == config.downloads_dir / "help"
        assert downloads is app.state.downloads
        on_progress({"phase": "Finding sources", "processed": 1, "total": 1, "file": "C.TXT"})
        for edition in package_ids:
            on_ready(edition)
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"game")
    downloaded = []
    def fetch(source, limit, progress, *, on_status=None):
        downloaded.append(source["id"])
        progress(len(archive.getvalue()), len(archive.getvalue()))
        return archive.getvalue()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    built_with_limits = []
    def build(*args, **kwargs):
        built_with_limits.append(kwargs["backup_count"])
        return build_help_groups(*args, **kwargs)
    monkeypatch.setattr("thelpviewer.server.content.build_help_groups", build)
    app = create_app(config)
    app.state.server_settings.update({"backup_count": 1})
    with TestClient(app, base_url=config.auth_origin) as client:
        ident = admin_session(app, client)
        private = config.state_dir / "dos" / "users" / ident / "sentinel.dat"
        private.parent.mkdir(parents=True)
        private.write_bytes(b"permanent private data")
        response = client.post("/api/admin/content", json={"help_packages": ["helppc:"], "dos_packages": ["two"]},
                               headers={"Origin": config.auth_origin})
        assert response.status_code == 202
        status = wait_job(client)
        assert status["state"] == "ready", status
        assert selected_products and downloaded == ["two"]  # Explicit selection enables opt-in packages.
        assert app.state.dos_prompt.files["GAMES/TWO/GAME.EXE"] == b"game"
        assert "GAMES/ONE/GAME.EXE" not in app.state.dos_prompt.files
        assert private.read_bytes() == b"permanent private data"
        assert source.is_file() and list((config.downloads_dir / "dos").iterdir())
        catalog = json.loads((config.helps_dir / "catalog.json").read_text())
        assert catalog[0]["file"] == "HelpPC 2.10/c.json.gz"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and client.get("/api/search/status").json()["state"] == "building":
            time.sleep(.01)
        assert client.get("/api/search/global", params={"q": "Reference"}).json()["results"]
        assert app.state.help_display_names["c.txt"] == "C language"
        first_files = dict(app.state.dos_prompt.files)
        # Deselection uninstalls published HELP/shared software, not original/private files.
        client.post("/api/admin/content", json={"help_packages": [], "dos_packages": []},
                    headers={"Origin": config.auth_origin})
        assert wait_job(client)["state"] == "ready"
        assert "GAMES/TWO/GAME.EXE" not in app.state.dos_prompt.files and private.is_file()
        assert source.is_file() and not list(config.helps_dir.rglob("*.json.gz"))
        assert json.loads((config.helps_dir / "catalog.json").read_text()) == []
        assert (config.state_dir / app.state.dos_prompt.backup / "c" / "GAMES/TWO/GAME.EXE").read_bytes() == b"game"
        assert list((config.downloads_dir / "dos").iterdir())
        assert selected_products == ["helppc"]
        assert built_with_limits == [1, 1]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and client.get("/api/search/status").json()["state"] == "building":
            time.sleep(.01)
        assert client.get("/api/search/global", params={"q": "Reference"}).json()["results"] == []


@pytest.mark.parametrize("first,fail_help", [("help", False), ("dos", False), ("help", True)])
@pytest.mark.parametrize("combined", [False, True])
def test_cross_type_requests_run_concurrently_and_preserve_both_selections(tmp_path, monkeypatch, first, fail_help, combined):
    from thelpviewer.server.downloader.service import plan_help_downloads

    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:Reference\r\n%Help text\r\n")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"game")
    entered = {kind: threading.Event() for kind in ("help", "dos")}
    release = threading.Event()

    def gate(kind):
        entered[kind].set()
        assert release.wait(5)

    def download(products, *_args, downloads, package_ids, on_ready, **_kwargs):
        rows = plan_help_downloads(products, package_ids=package_ids)
        for row in rows:
            downloads.update("help", row["id"], state="running")
        gate("help")
        if fail_help:
            raise ValueError("HELP test source unavailable")
        for row in rows:
            downloads.update("help", row["id"], state="done", percent=100)
            on_ready(row["id"])
        downloads.finish("help")
        return DownloadResult()

    def fetch(*_args, **_kwargs):
        # This transport stub must announce actual transfer work just like read_request.
        from thelpviewer.server.downloader.online import report_transfer
        report_transfer("Downloading")
        gate("dos")
        return archive.getvalue()

    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        headers = {"Origin": config.auth_origin}
        jobs = {"help": {"help_packages": ["helppc:"]}, "dos": {"dos_packages": ["one"]}}
        second = "dos" if first == "help" else "help"
        try:
            payload = {**jobs[first], **jobs[second]} if combined else jobs[first]
            response = client.post("/api/admin/content", json=payload, headers=headers)
            assert response.status_code == 202
            assert entered[first].wait(5)
            if not combined:
                response = client.post("/api/admin/content", json=jobs[second], headers=headers)
                assert response.status_code == 202, response.text
            assert entered[second].wait(5), "The other content type must start before the first is released"
            assert client.get("/api/admin/content/status").json()["scopes"] == ["dos", "help"]
            active_jobs = app.state.jobs.pending("content")
            assert len(active_jobs) == (1 if combined else 2)
            for record in active_jobs:
                assert record["state"] == "running"
                assert set(record["progress"]["operations"]) == set(record["payload"]["scope"])
            rows = client.get("/api/downloads").json()["items"]
            assert {"help:helppc:", "dos:one"} <= {row["id"] for row in rows}
            running = next(row for row in rows if row["kind"] == second)
            assert running["state"] == "running"
            assert client.post("/api/admin/content", json=jobs[second], headers=headers).status_code == 409
            requested = client.get("/api/admin/content").json()["selection"]
            assert requested == {"help_packages": ["helppc:"], "dos_packages": ["one"]}
        finally:
            release.set()
            join_content_jobs(app.state.content)
        status = wait_job(client)
        assert status["scopes"] == []
        assert status["state"] == ("error" if fail_help else "ready"), status
        assert app.state.dos_prompt.files["GAMES/ONE/GAME.EXE"] == b"game"
        assert app.state.content._saved_selection()["dos_packages"] == ["one"]
        assert app.state.content._saved_selection()["help_packages"] == ["helppc:"]
        if fail_help:
            assert "HELP test source unavailable" in status["error"]
            assert client.get("/api/downloads").json()["errors"] > 0
        else:
            assert (config.helps_dir / "HelpPC 2.10/c.json.gz").is_file()
            assert not client.get("/api/downloads").json()["active"]


def test_help_choices_are_editions_and_saved_requests_are_not_installed_content(tmp_path):
    app = create_app(config_for(tmp_path))
    choices = app.state.content.choices()
    ids = {item["id"] for item in choices["help_packages"]}
    assert {"tp:7", "bp:7.x current", "tc:2.0", "bc:3.0", "tasm:2.01", "td:4.0", "masm:5.1", "qbx:7.1", "qb45:4.5", "helppc:"} <= ids
    assert "borland" not in ids and "microsoft" not in ids
    values = {"configured": True, "help_packages": ["tp:7"], "dos_packages": []}
    app.state.content._save_selection(values)
    assert app.state.content.choices()["selection"]["help_packages"] == []
    assert json.loads(app.state.content.path.read_text()) == values


def test_dos_choices_expose_manifest_categories_and_preserve_global_selection(tmp_path):
    config = config_for(tmp_path)
    manifest = json.loads(config.dos_config_path.read_text())
    manifest["categories"] = [{"id": "games", "label": "Games"}, {"id": "tools", "label": "Tools"}]
    for source, category in zip(manifest["sources"], ("games", "tools")):
        source["category"] = category
    config.dos_config_path.write_text(json.dumps(manifest))
    app = create_app(config)
    app.state.content._save_selection({"configured": True, "help_packages": ["helppc:"], "dos_packages": ["one", "two"]})
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        choices = client.get("/api/admin/content").json()
        assert choices["dos_categories"] == manifest["categories"]
        assert [row["category"] for row in choices["dos_packages"]] == ["games", "tools"]
        assert choices["selection"] == {"help_packages": [], "dos_packages": []}
    assert json.loads(app.state.content.path.read_text())["dos_packages"] == ["one", "two"]


def test_uncategorized_dos_packages_have_an_other_category(tmp_path):
    app = create_app(config_for(tmp_path))
    choices = app.state.content.choices()
    assert choices["dos_categories"] == [{"id": "other", "label": "Other"}]
    assert all(row["category"] == "other" for row in choices["dos_packages"])


@pytest.mark.parametrize("categories,category", [
    ({}, "other"), ([{"id": "games", "label": ""}], "games"),
    ([{"id": "games", "label": "Games"}] * 2, "games"),
    ([{"id": "../bad", "label": "Bad"}], "other"),
    ([{"id": "games", "label": "Games"}], "unknown"),
    ([], []),
])
def test_invalid_dos_category_metadata_is_rejected(tmp_path, categories, category):
    config = config_for(tmp_path)
    manifest = json.loads(config.dos_config_path.read_text())
    manifest["categories"] = categories
    manifest["sources"][0]["category"] = category
    config.dos_config_path.write_text(json.dumps(manifest))
    app = create_app(config)
    with pytest.raises(ValueError, match="DOS categor|package category"):
        app.state.content.choices()


def test_separate_help_and_dos_choices_preserve_the_other_selection(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10" / "C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:Reference\r\n%Help text\r\n")
    def download(*_args, package_ids, on_ready, **_kwargs):
        for edition in package_ids:
            on_ready(edition)
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"game")
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *_args, **_kwargs: archive.getvalue())
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        headers = {"Origin": config.auth_origin}
        assert client.post("/api/admin/content", json={}, headers=headers).status_code == 409
        assert client.post("/api/admin/content", json={"help_packages": ["helppc:"], "dos_packages": ["one"]}, headers=headers).status_code == 202
        assert wait_job(client)["state"] == "ready"
        bundle = config.helps_dir / "HelpPC 2.10" / "c.json.gz"
        original = bundle.read_bytes()
        assert client.post("/api/admin/content", json={"dos_packages": []}, headers=headers).status_code == 202
        assert wait_job(client)["state"] == "ready"
        assert bundle.read_bytes() == original and "GAMES/ONE/GAME.EXE" not in app.state.dos_prompt.files
        assert client.get("/api/admin/content").json()["selection"] == {"help_packages": ["helppc:"], "dos_packages": []}
        assert client.post("/api/admin/content", json={"dos_packages": ["one"]}, headers=headers).status_code == 202
        assert wait_job(client)["state"] == "ready"
        assert client.post("/api/admin/content", json={"help_packages": []}, headers=headers).status_code == 202
        assert wait_job(client)["state"] == "ready"
        assert not bundle.exists() and app.state.dos_prompt.files["GAMES/ONE/GAME.EXE"] == b"game"
        assert source.is_file()


def test_dos_only_changes_do_not_retry_a_previously_failed_help_installation(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    app = create_app(config)
    app.state.content._save_selection({"configured": False, "help_packages": ["helppc:"], "dos_packages": []})
    def unexpected(*_args, **_kwargs):
        raise AssertionError("DOS-only settings retried HELP")
    monkeypatch.setattr("thelpviewer.server.content.download_products", unexpected)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert client.post("/api/admin/content", json={"dos_packages": []}, headers={"Origin": config.auth_origin}).status_code == 202
        assert wait_job(client)["state"] == "ready"
        data = client.get("/api/admin/content").json()
        assert not data["configured"] and data["selection"]["help_packages"] == []
        assert app.state.content._saved_selection()["help_packages"] == ["helppc:"]
        assert not config.sources_dir.exists()


@pytest.mark.parametrize("installed_kind", ["help", "dos"])
def test_existing_content_does_not_reopen_first_run_after_an_interrupted_job(tmp_path, installed_kind):
    config = config_for(tmp_path)
    app = create_app(config)
    app.state.content._save_selection({"configured": False, "help_packages": ["helppc:"], "dos_packages": ["one"]})
    if installed_kind == "dos":
        from thelpviewer.server.downloader.packages import package_cache_key
        receipt = app.state.dos_prompt.installed_path
        receipt.parent.mkdir(parents=True, exist_ok=True)
        name = "GAMES/ONE/GAME.EXE"
        program = app.state.dos_prompt.disk_dir / name
        program.parent.mkdir(parents=True)
        program.write_bytes(b"installed")
        source = json.loads(config.dos_config_path.read_text())["sources"][0]
        receipt.write_text(json.dumps({"one": package_cache_key(source), "_complete": True, "_files": {"one": [name]}}))
    else:
        bundle = config.helps_dir / "HelpPC 2.10/c.json.gz"
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_bytes(b"published help sentinel")
        (config.helps_dir / "catalog.json").write_text(json.dumps([
            {"file": "HelpPC 2.10/c.json.gz", "product": "helppc"},
        ]))
    choices = app.state.content.choices()
    assert not choices["configured"] and not choices["needs_setup"]
    assert choices["selection"] == {"help_packages": ["helppc:"] if installed_kind == "help" else [],
                                     "dos_packages": ["one"] if installed_kind == "dos" else []}
    app.state.downloads.close()


def test_startup_reconciles_unpublished_dos_completion_without_retrying_failed_job(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"installed")
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *_a, **_kw: archive.getvalue())
    app = create_app(config)
    app.state.dos_prompt.configure(["one"])
    values = {"configured": True, "help_packages": [], "dos_packages": ["one", "two"]}
    app.state.content._save_selection(values)
    ident = app.state.jobs.create("content", {"values": values, "scope": ["dos"], "configured": True})
    app.state.jobs.update(ident, "error", error="old failed publication")
    downloads = app.state.downloads
    downloads.begin("dos", [{"id": key, "label": key} for key in ("one", "two")])
    for key in ("one", "two"):
        downloads.update("dos", key, state="done", percent=100, phase="Installed")
    downloads.finish("dos", error="old failed publication")
    downloads.close()
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source",
                        lambda *_a, **_kw: pytest.fail("A terminal failure must not download on restart"))
    restarted = create_app(config)
    try:
        restarted.state.content.resume()
        rows = {row["id"]: row for row in restarted.state.downloads.snapshot(private=True)["items"]}
        assert rows["dos:one"]["state"] == "done"
        assert rows["dos:two"]["state"] == "blocked" and rows["dos:two"]["retryable"]
        assert rows["dos:operation"]["state"] == "error"
        assert restarted.state.jobs.latest("content")["state"] == "error"
        assert restarted.state.content.choices()["selection"]["dos_packages"] == ["one"]
    finally:
        restarted.state.downloads.close()


def test_reconfiguration_failure_retains_completed_setup_state(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    app = create_app(config)
    app.state.content._save_selection({"configured": True, "help_packages": [], "dos_packages": []})
    def fail(*_args, **_kwargs):
        assert app.state.content.choices()["configured"]
        assert not app.state.content.choices()["needs_setup"]
        raise ValueError("source unavailable")
    monkeypatch.setattr("thelpviewer.server.content.download_products", fail)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        assert client.post("/api/admin/content", json={"help_packages": ["helppc:"]},
                           headers={"Origin": config.auth_origin}).status_code == 202
        assert wait_job(client)["state"] == "error"
        choices = client.get("/api/admin/content").json()
        assert choices["configured"] and not choices["needs_setup"]
        assert choices["selection"]["help_packages"] == []
        assert not next(item for item in choices["help_packages"] if item["id"] == "helppc:")["installed"]
        restarted = create_app(config).state.content.choices()
        assert restarted["selection"]["help_packages"] == []
    assert create_app(config).state.content.choices()["configured"]


@pytest.mark.parametrize("kind", ["help", "dos"])
def test_failed_request_never_replaces_installed_choices_on_reopen_or_restart(tmp_path, monkeypatch, kind):
    config = config_for(tmp_path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"installed game")
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *_a, **_kw: archive.getvalue())
    app = create_app(config)
    content, dos = app.state.content, app.state.dos_prompt
    if kind == "help":
        source = config.sources_dir / "HelpPC 2.10/C.TXT"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"@C language\r\n:Reference\r\n%Help text\r\n")
        build_help_groups(["dos-reference"], config.sources_dir, config.helps_dir)
        installed, requested = "helppc:", "tasm:2.01"
    else:
        dos.configure(["one"])
        installed, requested = "one", "two"
    field = "help_packages" if kind == "help" else "dos_packages"
    content._save_selection({"configured": True, "help_packages": [], "dos_packages": [], field: [installed]})
    entered, release = threading.Event(), threading.Event()

    def fail(*_args, **_kwargs):
        entered.set()
        assert release.wait(5)
        raise ValueError("download unavailable")

    monkeypatch.setattr("thelpviewer.server.content.download_products" if kind == "help"
                        else "thelpviewer.server.downloader.packages.fetch_source", fail)
    try:
        content.start(**{field: [requested]})
        assert entered.wait(5)
        active = content.choices()
        assert active["status"]["state"] == "building" and active["selection"][field] == [requested]
        rows = active["help_packages" if kind == "help" else "dos_packages"]
        assert next(row for row in rows if row["id"] == installed)["installed"]
        assert not next(row for row in rows if row["id"] == requested)["installed"]
    finally:
        release.set()
        join_content_jobs(content, timeout=5)
    assert content.status()["state"] == "error"
    # Closing/reopening does a fresh choices request. Old content survives the
    # failed addition/removal; remembered intent remains available to Retry only.
    assert content.choices()["selection"][field] == [installed]
    assert content._saved_selection()[field] == [requested]
    assert create_app(config).state.content.choices()["selection"][field] == [installed]
    app.state.downloads.close()


def test_content_dialog_statistics_accept_only_registered_aggregate_names(tmp_path):
    app = create_app(config_for(tmp_path))
    with TestClient(app) as client:
        names = {"help-packages", "dos-packages", "midi-sources", "downloads", "server-configuration",
                 "account", "login", "users", "add-user", "registration", "registration-token",
                 "download-action", "download-error", "rebuild-dos", "rebuild-midi", "grid", "progress", "messagebox", "dialog"}
        for name in names:
            assert client.post("/api/statistics/events", json={"event": "dialog_open", "name": name}).status_code == 204
            assert client.post("/api/statistics/events", json={
                "event": "view_duration", "scope": "dialog", "name": name, "duration_ms": 5000,
            }).status_code == 204
        assert client.post("/api/statistics/events", json={"event": "dialog_open", "name": "arbitrary-private-name"}).status_code == 422
        summary = app.state.statistics.summary(limit=25)
        assert summary["dialog_opens"] == len(names)
        assert {row["value"] for row in summary["dialog"]} == names
        assert {row["value"].split(" · ")[0] for row in summary["dialog_duration"]} == names


@pytest.mark.parametrize("fail_conversion", [False, True])
def test_help_queue_remains_active_through_conversion_and_reports_its_failure(tmp_path, monkeypatch, fail_conversion):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:Reference\r\n%Reference text\r\n")
    app = create_app(config)
    entered, release = threading.Event(), threading.Event()
    def download(_products, _sources, _cache, *, downloads, finalize, on_ready, **_options):
        assert not finalize
        downloads.update("help", "helppc:", state="waiting", percent=35, phase="Awaiting conversion")
        on_ready("helppc:")
        return DownloadResult(files=[source])
    def build(*args, on_progress, **kwargs):
        on_progress({"phase": "Converting", "stage": "convert", "stage_percent": 50,
                     "processed": 1, "total": 2, "file": source.name})
        entered.set()
        assert release.wait(5)
        if fail_conversion:
            raise ValueError("Invalid HELP payload")
        return build_help_groups(*args, on_progress=on_progress, **kwargs)
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    monkeypatch.setattr("thelpviewer.server.content.build_help_groups", build)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        try:
            assert client.post("/api/admin/content", json={"help_packages": ["helppc:"]},
                headers={"Origin": config.auth_origin}).status_code == 202
            assert entered.wait(5)
            status = client.get("/api/downloads").json()
            row = next(row for row in status["items"] if row["id"] == "help:helppc:")
            assert status["active"] and 35 < status["percent"] < 100
            assert row["state"] == "running" and row["phase"] == "Converting"
            assert row["stage"] == "convert" and row["stage_percent"] == 50
            assert not list(config.helps_dir.rglob("*.json.gz"))
        finally:
            release.set()
        finished = wait_job(client)
        status = client.get("/api/downloads").json()
        row = next(row for row in status["items"] if row["id"] == "help:helppc:")
        assert not status["active"]
        if fail_conversion:
            assert finished["state"] == row["state"] == "error"
            assert row["percent"] < 100 and row["error"] == "Invalid HELP payload"
            assert not list(config.helps_dir.rglob("*.json.gz"))
        else:
            assert finished["state"] == "ready" and row["state"] == "done"
            assert row["phase"] == "Published" and row["percent"] == 100
            assert status["percent"] == 0
            assert (config.helps_dir / "HelpPC 2.10/c.json.gz").is_file()


def test_product_reconfiguration_preserves_other_products_and_archives_uninstalled_help(tmp_path, monkeypatch):
    manifest = json.loads(Path("thelpviewer/config/help-database.json").read_text())
    product = next(product for product in manifest["products"] if product["key"] == "bc")
    for query in product["sources"].values():
        query["archive_members"] = ["REFERENCE.TXT"]
    database = tmp_path / "help-database.json"
    database.write_text(json.dumps(manifest))
    monkeypatch.setenv("THELP_HELP_DATABASE_PATH", str(database))
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    for name, title in [("Borland Turbo Pascal 7.0", "Pascal"), ("Borland C++ 3.0", "C++")]:
        path = sources / name / "REFERENCE.TXT"
        path.parent.mkdir(parents=True)
        path.write_bytes(f"@{title}\r\n:ReferenceTopic\r\n%Reference help\r\n".encode())
    build_help_groups(["borland"], sources, helps)
    cpp = helps / "Borland C++ 3.0" / "reference.json.gz"
    original = cpp.read_bytes()
    build_help_groups(["borland"], sources, helps, product_keys=["tp"], keep_products=["tp", "bc"])
    assert cpp.read_bytes() == original
    result = build_help_groups([], sources, helps, product_keys=[], keep_products=["bc"])
    assert cpp.read_bytes() == original
    assert not (helps / "Borland Turbo Pascal 7.0").exists()
    assert (Path(result["backup"]) / "Borland Turbo Pascal 7.0" / "reference.json.gz").is_file()
    assert (sources / "Borland Turbo Pascal 7.0" / "REFERENCE.TXT").is_file()


def test_later_dos_failure_does_not_reject_successfully_published_help(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:Reference\r\n%Reference text\r\n")
    app = create_app(config)
    downloads = app.state.downloads
    downloads.begin("help", [{"id": "helppc:", "label": "HelpPC", "byte_progress": False}])
    downloads.begin("dos", [{"id": "two", "label": "Two", "byte_progress": False}])
    def download(*_args, finalize, on_ready, **_kwargs):
        assert not finalize
        downloads.update("help", "helppc:", state="running", percent=35)
        on_ready("helppc:")
        return DownloadResult(files=[source])
    def fail_dos(*_args, **_kwargs):
        raise ValueError("DOS archive unavailable")
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    monkeypatch.setattr(app.state.dos_prompt, "configure", fail_dos)
    try:
        app.state.content.start(help_packages=["helppc:"], dos_packages=["two"])
        join_content_jobs(app.state.content)
        assert app.state.content.status()["state"] == "error"
        assert (config.helps_dir / "HelpPC 2.10/c.json.gz").is_file()
        rows = downloads.snapshot(private=True)["items"]
        help_rows = [row for row in rows if row["kind"] == "help"]
        assert len(help_rows) == 1 and help_rows[0]["state"] == "done" and not help_rows[0]["error"]
        assert any(row["kind"] == "dos" and row["state"] == "error" for row in rows)
    finally:
        downloads.close()


def test_product_build_does_not_classify_companion_help_by_archive_folder(tmp_path):
    import shutil
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    target = sources / "Borland Turbo Assembler"
    target.mkdir(parents=True)
    shutil.copyfile(Path("var/sources/Borland Turbo Assembler/TASM.TAH"), target / "TASM.TAH")
    # A new CRC of a known companion filename must not acquire the archive's product.
    (target / "TDHELP.TDH").write_bytes(b"@Debugger\r\n:Companion\r\n%Debugger text\r\n")
    build_help_groups(["borland"], sources, helps, product_keys=["tasm"], keep_products=["tasm"])
    catalog = json.loads((helps / "catalog.json").read_text())
    assert len(catalog) == 1
    assert catalog[0]["product"] == "tasm" and catalog[0]["source_file"] == "TASM.TAH"
    assert catalog[0]["name"] == "Turbo Assembler Help" and catalog[0]["topics"] > 0
    assert (target / "TDHELP.TDH").is_file()  # Companion originals are retained.


def test_failed_conversion_keeps_published_bundles_and_can_be_retried(tmp_path, monkeypatch):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "HelpPC 2.10" / "C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:ReferenceTopic\r\n%Reference search text\r\n")
    build_help_groups(["dos-reference"], sources, helps)
    original = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    def fail(*args, **kwargs):
        raise ValueError("Conversion failed")
    with monkeypatch.context() as patch:
        patch.setattr("thelpviewer.server.converter.build.export_bundle_tree", fail)
        with pytest.raises(ValueError, match="Conversion failed"):
            build_help_groups(["dos-reference"], sources, helps)
    assert original == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    result = build_help_groups(["dos-reference"], sources, helps)
    assert result["backup"] and result["bundles"] == 1
    assert source.exists()


def test_download_selection_and_transport_are_explicit_and_bounded(tmp_path):
    assert download_products([], tmp_path / "sources", tmp_path / "downloads").files == []
    assert not (tmp_path / "downloads").exists()
    with pytest.raises(ValueError, match="Unknown"):
        download_products(["unknown"], tmp_path / "sources", tmp_path / "downloads")
    with pytest.raises(ValueError, match="private network"):
        public_url("http://192.168.1.1/file", https_only=False)
    response = io.BytesIO(b"short")
    response.headers = {"Content-Length": "10"}
    with pytest.raises(ValueError, match="incomplete"):
        list(download_chunks(response, 100))


def test_selected_help_build_preserves_unselected_groups_and_stable_paths(tmp_path):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    for product, name, title in [("Microsoft Demo", "ASM.TXT", "Default"), ("HelpPC 2.10", "C.TXT", "Reference")]:
        path = sources / product / name
        path.parent.mkdir(parents=True)
        path.write_bytes(f"@{title}\r\n:{title}Topic\r\n%{title} help\r\n".encode())
    build_help_groups(["microsoft"], sources, helps)
    original = (helps / "Microsoft Demo" / "asm.json.gz").read_bytes()
    build_help_groups(["dos-reference"], sources, helps)
    assert (helps / "Microsoft Demo" / "asm.json.gz").read_bytes() == original
    assert {item["file"] for item in json.loads((helps / "catalog.json").read_text())} == {
        "Microsoft Demo/asm.json.gz", "HelpPC 2.10/c.json.gz"}
