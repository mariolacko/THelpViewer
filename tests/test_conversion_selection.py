"""Archive member lists select both extraction and already-present inputs."""

import json
from pathlib import Path
import zlib

import pytest

from thelpviewer.server.archives.core import ExtractorTools
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import export_tree, iter_help_files
from thelpviewer.server.converter.ingest import HelpInput, ingest_help
from thelpviewer.server.converter.selection import archive_member_selected, archive_members_for, select_help_packages
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.downloader.service import _verified_sources
from thelpviewer.help_database import HelpDatabaseEntry, SourceQuery, load_help_manifest
from dataclasses import replace


def test_archive_members_select_extraction_existing_sources_cli_and_server(tmp_path, monkeypatch):
    manifest = json.loads(Path("thelpviewer/config/help-database.json").read_text())
    product = next(product for product in manifest["products"] if product["key"] == "tp")
    product["sources"] = {"direct": {"search_text": "Reference", "archive_members": ["REFERENCE.TXT", "EXTRA_1.TXT"]}}
    manifest["entries"] = []
    root = tmp_path / "sources"
    collection = "Borland Turbo Pascal 7"
    directory = root / collection
    directory.mkdir(parents=True)
    for name in ("REFERENCE.TXT", "IGNORE.TXT", "EXTRA_1.TXT"):
        (directory / name).write_bytes(f"@{name}\r\n:Topic\r\n%{name} text\r\n".encode())
        manifest["entries"].append({
            "crc32": f"{zlib.crc32((directory / name).read_bytes()):08X}", "filenames": [name],
            "collection": collection, "title": name,
        })
    path = tmp_path / "help-database.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setenv("THELP_HELP_DATABASE_PATH", str(path))
    expected = {"REFERENCE.TXT", "EXTRA_1.TXT"}
    assert {source.name for source in iter_help_files(directory)} == expected
    assert _verified_sources("tp:7", root) is True
    assert not archive_member_selected(directory / "ignore.txt")
    assert archive_member_selected(directory / "reference.txt")

    def extract(_archive, destination, _tools):
        destination.mkdir(parents=True, exist_ok=True)
        for source in directory.iterdir():
            (destination / source.name).write_bytes(source.read_bytes())

    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", extract)
    extracted = tmp_path / "extracted"
    with select_help_packages(["tp:7"]):
        copied = ingest_help(HelpInput(tmp_path / "archive.zip", "Borland Turbo Pascal",
                                      members=archive_members_for("tp", "7")), extracted, ExtractorTools(None, None, None))
    assert {source.name for source in copied} == expected
    assert not (extracted / collection / "IGNORE.TXT").exists()
    assert (directory / "IGNORE.TXT").is_file()

    # Missing required originals remain a real failure, not a successful partial extraction.
    (directory / "REFERENCE.TXT").rename(directory / "REFERENCE.saved")
    assert _verified_sources("tp:7", root) is False
    with pytest.raises(ValueError, match="Missing archive members: REFERENCE.TXT"):
        ingest_help(HelpInput(tmp_path / "archive.zip", collection, members=("REFERENCE.TXT", "EXTRA_1.TXT")),
                    tmp_path / "missing", ExtractorTools(None, None, None))
    (directory / "REFERENCE.saved").rename(directory / "REFERENCE.TXT")

    html = export_tree(root, tmp_path / "html")
    assert {result.input_path.name for result in html} == expected
    assert all(not result.error for result in html)
    bundles = export_bundle_tree(root, tmp_path / "bundles", layout="helps", source_paths=list(directory.glob("*.TXT")))
    assert {result.input_path.name for result in bundles} == expected
    assert all(not result.error for result in bundles)
    output = tmp_path / "published"
    result = build_help_groups(["borland"], root, output, package_ids=["tp:7"], keep_packages=["tp:7"])
    assert result["bundles"] == 2
    assert {row["source_file"] for row in json.loads((output / "catalog.json").read_text())} == expected


def test_complete_pascal_edition_list_does_not_restrict_other_editions_or_partial_recipes():
    assert set(archive_members_for("tp", "7")) == {"TURBO.TPH", "OWL.TPH", "TVISION.TPH"}
    assert archive_members_for("tp", "5.5") == ("TURBO.HLP",)
    assert archive_members_for("tp", "7 (CZ)") == ()
    # QC.HLP has its own retrieval recipe, not a declaration to remove GRAPHICS/QA/etc.
    assert archive_members_for("quickc", "2.50") == ()
    assert archive_member_selected(Path("sources/Other/COMMDLGS.HLP"))
    assert archive_member_selected(Path("sources/Microsoft QuickC, C, and C++ 2.50/GRAPHICS.HLP"))


def test_all_borland_cpp_edition_components_share_explicit_source_lists():
    assert set(archive_members_for("bc", "2.0 DOS current")) == {"TCHELP.TCH", "TCHELPW.TCH"}
    assert set(archive_members_for("bc", "3.0")) == {"TCHELP.TCH"}
    assert set(archive_members_for("bc", "3.1")) == {"TCHELP.TCH", "WINHELP.TCH"}
    assert set(archive_members_for("bc", "3.x")) == {"TVCHELP.TCH", "OWLHELP.TCH"}
    for version in ("2.0 DOS current", "3.0", "3.1", "3.x"):
        assert not archive_member_selected(Path("sources") / f"Borland C++ {version}" / "HELPEX.HLP")


def test_component_revisions_do_not_disable_a_complete_edition_member_list(monkeypatch):
    from thelpviewer.server.converter import selection
    manifest = load_help_manifest()
    query = SourceQuery("Complete edition", archive_members=("TVCHELP.TCH", "OWLHELP.TCH"))
    entries = tuple(HelpDatabaseEntry(crc32=crc, filenames=(name,), title=name,
        collection="Borland C++ 3.x", product_key="bc", version="3.x", sources=sources)
        for crc, name, sources in ((1, "TVCHELP.TCH", {"direct": query}),
            (2, "OWLHELP.TCH", {"direct": query}), (3, "OWLHELP.TCH", {})))
    monkeypatch.setattr(selection, "load_help_manifest", lambda: replace(manifest, entries=entries))
    assert set(archive_members_for("bc", "3.x")) == {"TVCHELP.TCH", "OWLHELP.TCH"}


def test_native_pascal_discovery_uses_the_source_member_list_without_deleting_originals():
    root = Path("var/sources/Borland Turbo Pascal 7")
    selected = {source.name for source in iter_help_files(root)
                if archive_member_selected(source)}
    assert not {"COMMDLGS.HLP", "HELPEX.HLP", "HEAPSPY.HLP"} & selected
    assert {"TURBO.TPH", "TVISION.TPH", "OWL.TPH"} <= selected
    assert all((root / name).is_file() for name in ("COMMDLGS.HLP", "HELPEX.HLP"))
