from thelpviewer.server.converter import selection
"""Edition selection controls real downloads, publication and removal."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_server_content import config_for, admin_session, wait_job
from thelpviewer.help_packages import help_packages
from thelpviewer.server.app import create_app
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.downloader import catalog, winworld
from thelpviewer.server.archives.core import ExtractorTools
from thelpviewer.server.downloader.service import DownloadResult, download_products


def test_help_groups_match_menu_names_and_combine_quickbasic_editions():
    packages = help_packages()
    assert {item["version"] for item in packages if item["category"] == "Microsoft QuickBASIC"} == {"4.5", "7.1"}
    assert {item["id"] for item in packages if item["category"] == "Borland Turbo Pascal"} >= {"tp:5.0", "tp:5.5", "tp:7"}
    assert {item["id"] for item in packages if item["category"] == "Scorpions Cheater"} >= {"scorpion:1", "scorpion:21", "scorpion:23"}
    assert all(item["description"] and "Install or remove" not in item["description"] for item in packages)
    assert "BIOS" in next(item for item in packages if item["product"] == "helppc")["description"]


def test_help_descriptions_identify_the_actual_edition_and_fall_back_to_the_product():
    rows = {item["id"]: item for item in help_packages([{"product": "tp", "version": "99"}])}
    assert rows["tp:4.0"]["description"] != rows["tp:7"]["description"]
    assert "Turbo Pascal 4" in rows["tp:4.0"]["description"]
    assert "Profiler" in rows["td:"]["description"]
    assert "MicroCalc" in rows["tbasic:1.x current"]["description"]
    assert "CodeView" in rows["masm:5.1"]["description"]
    assert rows["tp:99"]["description"]


def test_shareware_releases_have_one_installation_id_matching_their_source_collections():
    catalog = [{"product": "scorpion", "version": f"{version} _shareware_"} for version in (6, 7, 8)]
    ids = {item["id"] for item in help_packages(catalog)}
    for version in (6, 7, 8):
        assert f"scorpion:{version} _shareware_" in ids
        assert f"scorpion:{version}" not in ids


def test_removed_manifest_help_ids_do_not_block_an_unrelated_dos_selection(tmp_path):
    app = create_app(config_for(tmp_path))
    content = app.state.content
    content._save_selection({"configured": True, "help_packages": ["scorpion:6", "scorpion:6 _shareware_"],
                             "dos_packages": []})
    try:
        assert content._saved_selection()["help_packages"] == ["scorpion:6 _shareware_"]
    finally:
        app.state.downloads.close()


def test_empty_edition_selection_needs_no_extractor_or_download_directory(tmp_path):
    assert download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
        package_ids=[], extractor=ExtractorTools(None, None, None)).files == []
    assert not (tmp_path / "downloads").exists()


def test_install_and_remove_one_version_keeps_its_sibling_and_originals(tmp_path, monkeypatch):
    manifest = json.loads(Path("thelpviewer/config/help-database.json").read_text())
    product = next(product for product in manifest["products"] if product["key"] == "tp")
    for query in product["sources"].values():
        query["archive_members"] = ["REFERENCE.TXT"]
    database = tmp_path / "help-database.json"
    database.write_text(json.dumps(manifest))
    monkeypatch.setenv("THELP_HELP_DATABASE_PATH", str(database))
    config = config_for(tmp_path)
    for version in ("5.0", "5.5"):
        source = config.sources_dir / ("Borland Turbo Pascal " + version) / "REFERENCE.TXT"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"@Pascal reference\r\n:Reference\r\n%Pascal text\r\n")
    calls = []
    def download(products, *_args, **kwargs):
        calls.append((products, kwargs["package_ids"]))
        for edition in kwargs["package_ids"]:
            kwargs["on_ready"](edition)
        return DownloadResult()
    monkeypatch.setattr("thelpviewer.server.content.download_products", download)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        admin_session(app, client)
        headers = {"Origin": config.auth_origin}
        def apply(editions):
            response = client.post("/api/admin/content", json={"help_packages": editions}, headers=headers)
            assert response.status_code == 202, response.text
            status = wait_job(client)
            assert status["state"] == "ready", status
        apply(["tp:5.0"])
        assert (config.helps_dir / "Borland Turbo Pascal 5.0/reference.json.gz").is_file()
        assert not (config.helps_dir / "Borland Turbo Pascal 5.5/reference.json.gz").exists()
        original = (config.helps_dir / "Borland Turbo Pascal 5.0/reference.json.gz").read_bytes()
        apply(["tp:5.0", "tp:5.5"])
        assert (config.helps_dir / "Borland Turbo Pascal 5.0/reference.json.gz").read_bytes() == original
        apply(["tp:5.0"])
        assert not (config.helps_dir / "Borland Turbo Pascal 5.5").exists()
        assert (config.sources_dir / "Borland Turbo Pascal 5.5/REFERENCE.TXT").is_file()
        selected = client.get("/api/admin/content").json()
        assert selected["selection"]["help_packages"] == ["tp:5.0"]
        assert not next(item for item in selected["help_packages"] if item["id"] == "tp:5.5")["installed"]
        assert client.post("/api/admin/content", json={"help_groups": ["tp"]}, headers=headers).status_code == 422
    assert calls == [(["tp"], ["tp:5.0"]), (["tp"], ["tp:5.5"]), ([], [])]


def test_missing_edition_does_not_remove_published_sibling(tmp_path):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "Borland Turbo Pascal 5.0/REFERENCE.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@Pascal\r\n:Reference\r\n%Help\r\n")
    build_help_groups(["borland"], sources, helps)
    before = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="tp:5.5"):
        build_help_groups(["borland"], sources, helps, package_ids=["tp:5.5"], keep_packages=["tp:5.5"])
    assert before == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}


def test_downloader_filters_release_pages_and_restores_context(tmp_path, monkeypatch):
    requested = []
    monkeypatch.setattr(winworld, "get_version_urls", lambda slug: [("5.0", "https://test/5"), ("5.5", "https://test/55"), ("7.0", "https://test/7")])
    def process(**kwargs):
        requested.append(kwargs["version_name"])
        return []
    monkeypatch.setattr(winworld, "process_version", process)
    result = download_products(["tp"], tmp_path / "sources", tmp_path / "downloads", dry_run=True,
        source_keys=["winworld"], package_ids=["tp:5.5"])
    assert not result.warnings and requested == ["5.5"]
    # The selection is local to this call, not a process-global provider filter.
    assert selection.version_selected("tp", "7.0")
    with selection.select_help_packages(["tp:5.5"]):
        jobs = catalog.products_for_source("archiveorg", ["tp"])
        assert not any(job.default_version == "4.0" for job in jobs)
        assert not selection.version_selected("tp", "7.0")
    with selection.select_help_packages(["tp:7"]):
        assert selection.version_selected("tp", "7.0")
        assert not selection.version_selected("tp", "7.1")


def test_build_uses_verified_crc_version_not_the_archive_folder(tmp_path):
    import shutil
    source = tmp_path / "sources/Borland C++ 999/TASM.TAH"
    source.parent.mkdir(parents=True)
    shutil.copyfile("var/sources/Borland Turbo Assembler/TASM.TAH", source)
    build_help_groups(["borland"], tmp_path / "sources", tmp_path / "helps",
        package_ids=["tasm:3.1"], keep_packages=["tasm:3.1"])
    entries = json.loads((tmp_path / "helps/catalog.json").read_text())
    assert len(entries) == 1 and entries[0]["product"] == "tasm" and entries[0]["version"] == "3.1"


def test_non_crc_database_uses_its_canonical_publication_version(tmp_path):
    import shutil
    source = tmp_path / "sources/Scorpions Cheater DOS/Scorpions Cheater 1/DATA.DAT"
    source.parent.mkdir(parents=True)
    shutil.copyfile("var/sources/Scorpions Cheater DOS/Scorpions Cheater 1/DATA.DAT", source)
    build_help_groups(["scorpion"], tmp_path / "sources", tmp_path / "helps",
        package_ids=["scorpion:1"], keep_packages=["scorpion:1"])
    entries = json.loads((tmp_path / "helps/catalog.json").read_text())
    assert entries and all(entry["product"] == "scorpion" and entry["version"] == "1" for entry in entries)


def test_verified_archive_edition_does_not_require_version_in_remote_title(tmp_path, monkeypatch):
    from dataclasses import replace
    from thelpviewer.server.downloader import archiveorg
    job = next(job for job in catalog.products_for_source("archiveorg", ["tp"]) if job.default_version == "4.0")
    job = replace(job, sources={"archiveorg": replace(job.sources["archiveorg"], query=None)})
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: [job])
    monkeypatch.setattr(archiveorg, "get_item", lambda _: {"identifier": "verified-distribution", "title": "Original media"})
    monkeypatch.setattr(archiveorg.time, "sleep", lambda *_: None)
    calls = []
    monkeypatch.setattr(archiveorg, "process_item", lambda **kwargs: calls.append(kwargs["item"]) or [])
    with selection.select_help_packages(["tp:4.0"]):
        archiveorg.run(["tp"], tmp_path / "downloads", True, lambda *_a, **_k: [])
    assert calls
