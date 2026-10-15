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
    def download(products, sources, cache, on_progress, *, downloads, package_ids):
        assert package_ids == (["helppc:"] if products else [])
        selected_products.extend(products)
        assert sources == config.sources_dir and cache == config.downloads_dir / "help"
        assert downloads is app.state.downloads
        on_progress({"phase": "Finding sources", "processed": 1, "total": 1, "file": "C.TXT"})
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
    monkeypatch.setattr("thelpviewer.server.content.download_products", lambda *_args, **_kwargs: DownloadResult())
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
        receipt = app.state.dos_prompt.installed_path
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"one": "a" * 64, "_complete": True}))
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
        content._worker.join(timeout=5)
    assert not content._worker.is_alive() and content.status()["state"] == "error"
    # Closing/reopening does a fresh choices request. Old content survives the
    # failed addition/removal; remembered intent remains available to Retry only.
    assert content.choices()["selection"][field] == [installed]
    assert content._saved_selection()[field] == [requested]
    assert create_app(config).state.content.choices()["selection"][field] == [installed]
    app.state.downloads.close()


def test_content_dialog_statistics_accept_only_registered_aggregate_names(tmp_path):
    app = create_app(config_for(tmp_path))
    with TestClient(app) as client:
        names = {"help-packages", "dos-packages", "midi-sources", "downloads"}
        for name in names:
            assert client.post("/api/statistics/events", json={"event": "dialog_open", "name": name}).status_code == 204
            assert client.post("/api/statistics/events", json={
                "event": "view_duration", "scope": "dialog", "name": name, "duration_ms": 5000,
            }).status_code == 204
        assert client.post("/api/statistics/events", json={"event": "dialog_open", "name": "arbitrary-private-name"}).status_code == 422
        summary = client.get("/api/statistics/summary").json()
        assert summary["dialog_opens"] == 4
        assert {row["value"] for row in summary["dialog"]} == names
        assert {row["value"].split(" · ")[0] for row in summary["dialog_duration"]} == names


def test_product_reconfiguration_preserves_other_products_and_archives_uninstalled_help(tmp_path):
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


def test_product_build_does_not_classify_companion_help_by_archive_folder(tmp_path):
    import shutil
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    target = sources / "Borland Turbo Assembler"
    target.mkdir(parents=True)
    shutil.copyfile(Path("data/sources/Borland Turbo Assembler/TASM.TAH"), target / "TASM.TAH")
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
