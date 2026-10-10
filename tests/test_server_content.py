"""Content setup calls modules, publishes safely and never touches private disks."""

from dataclasses import replace
import gzip
import io
import json
import time
import zipfile

from fastapi.testclient import TestClient
import pytest

from thelpviewer.converter.build import build_help_groups
from thelpviewer.downloader.service import DownloadResult, download_products
from thelpviewer.downloader.transport import download_chunks, public_url
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
        token = app.state.accounts._new_session(database, ident)
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
        assert client.post("/api/admin/content", json={"help_groups": [], "dos_packages": []}).status_code == 403
        admin_session(app, client)
        first = client.get("/api/admin/content").json()
        assert first["needs_setup"] and not first["configured"]
        assert first["selection"] == {"help_groups": [], "dos_packages": []}
        assert app.state.dos_prompt.state == "idle"
        assert not config.sources_dir.exists() and not config.downloads_dir.exists()
        selection = {"help_groups": [], "dos_packages": []}
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


def test_help_and_dos_installation_updates_catalog_index_and_keeps_private_data(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    source = config.sources_dir / "HelpPC 2.10" / "C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:ReferenceTopic\r\n%Reference search text\r\n")
    selected_products = []
    def download(products, sources, downloads, on_progress):
        selected_products.extend(products)
        assert sources == config.sources_dir and downloads == config.downloads_dir / "help"
        on_progress({"phase": "Finding sources", "processed": 1, "total": 1, "file": "C.TXT"})
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"game")
    downloaded = []
    def fetch(source, limit, progress):
        downloaded.append(source["id"])
        progress(len(archive.getvalue()), len(archive.getvalue()))
        return archive.getvalue()
    monkeypatch.setattr("thelpviewer.server.dos_prompt.fetch_dos_source", fetch)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        ident = admin_session(app, client)
        private = config.state_dir / "dos" / "users" / ident / "sentinel.dat"
        private.parent.mkdir(parents=True)
        private.write_bytes(b"permanent private data")
        response = client.post("/api/admin/content", json={"help_groups": ["dos-reference"], "dos_packages": ["two"]},
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
        # Deselection is not an uninstall; another empty job preserves installed files.
        client.post("/api/admin/content", json={"help_groups": [], "dos_packages": []},
                    headers={"Origin": config.auth_origin})
        assert wait_job(client)["state"] == "ready"
        assert app.state.dos_prompt.files == first_files and private.is_file()


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
        patch.setattr("thelpviewer.converter.build.export_bundle_tree", fail)
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
