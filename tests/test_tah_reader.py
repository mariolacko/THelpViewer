from pathlib import Path
import json

from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.downloader.collector import is_help_file_path
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


TAH_SAMPLE = Path("data/sources/Borland Turbo Assembler/TASM.TAH")


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
    sources = [TAH_SAMPLE, Path("data/sources/Borland Turbo Assembler 2.x/TASM.TAH")]
    results = export_bundle_tree(Path("data/sources"), tmp_path, source_paths=sources, layout="helps")
    assert len(results) == 2 and all(result.format_name == "borland" for result in results)
    assert {result.json_path.name for result in results} == {"tasm.json.gz", "tasm-2.0.json.gz"}
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    release = next(entry for entry in catalog if entry.get("version") == "2.0")
    assert release["product"] == "tasm" and release["topics"] == 491
