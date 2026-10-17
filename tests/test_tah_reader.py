from pathlib import Path
import json

from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.sources import is_help_file_path
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.help_database import load_help_manifest, lookup_help_database_entry
from thelpviewer.help_packages import help_packages


TAH_SAMPLE = Path("var/sources/Borland Turbo Assembler/TASM.TAH")


def test_tah_sample_is_detected_as_thelp():
    data = TAH_SAMPLE.read_bytes()

    handler = detect_format_handler(TAH_SAMPLE, data)

    assert handler is not None
    assert handler.name == "thelp"

    document = load_document(TAH_SAMPLE)
    assert document.format_name == "borland"
    assert document.metadata["format_version"] == 52
    assert document.metadata["text_version"] == 1
    assert len(document.topics) > 500
    assert len(document.index_entries) > 400


def test_tah_suffix_is_collected_as_help_file():
    assert is_help_file_path(Path("TASM.TAH"))


def test_tasm_20_has_distinct_bundle_instead_of_colliding_with_other_edition(tmp_path):
    sources = [TAH_SAMPLE, Path("var/sources/Borland Turbo Assembler 2.x/TASM.TAH")]
    results = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=sources, layout="helps")
    assert len(results) == 2 and all(result.format_name == "borland" for result in results)
    assert {result.json_path.name for result in results} == {"tasm.json.gz", "tasm-2.0.json.gz"}
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    release = next(entry for entry in catalog if entry.get("version") == "2.0")
    assert release["product"] == "tasm" and release["topics"] == 491


def test_all_assembler_sources_publish_under_verified_versions_without_duplicate_copies(tmp_path):
    root = Path("var/sources")
    sources = [root / name / "TASM.TAH" for name in (
        "Borland C++ 3.0", "Borland C++ 3.x", "Borland Pascal 7.0 (DE)",
        "Borland Turbo Assembler", "Borland Turbo Assembler 2.01",
        "Borland Turbo Debugger/Profiler/Assembler")]
    assert all(lookup_help_database_entry(path) is not None for path in sources)
    before = {path: path.read_bytes() for path in sources}
    results = export_bundle_tree(root, tmp_path / "helps", source_paths=sources, layout="helps")
    assert len(results) == 5 and all(not result.error for result in results)
    catalog = json.loads((tmp_path / "helps/catalog.json").read_text())
    assert {entry["product_name"] for entry in catalog} == {"Borland Turbo Assembler"}
    assert {entry["version"] for entry in catalog} == {"2.0", "2.01", "3.0", "3.1", "3.2 (DE)"}
    assert len([entry for entry in catalog if entry["version"] == "3.0"]) == 1
    assert next(entry for entry in catalog if entry["version"] == "3.0")["file"] == "Borland C++ 3.0/tasm.json.gz"
    assert next(entry for entry in catalog if entry["version"] == "3.2 (DE)")["file"] == "Borland Pascal 7.0 (DE)/tasm.json.gz"
    assert not any(entry["file"].startswith("Borland C++ 3.x/") for entry in catalog)
    assert {item["id"] for item in help_packages() if item["product"] == "tasm"} == {
        "tasm:2.0", "tasm:2.01", "tasm:3.0", "tasm:3.1", "tasm:3.2 (DE)"}
    assert load_help_manifest().entry_map[0xC74EE5C6].language == "de"
    assert all(path.read_bytes() == data for path, data in before.items())
