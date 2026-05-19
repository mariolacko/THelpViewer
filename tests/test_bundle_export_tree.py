import gzip
import json
from pathlib import Path

from thelpviewer.converter.help_database import HelpDatabaseEntry, crc32_file
from thelpviewer.converter.writers import bundle as bundle_writer


def test_export_bundle_tree_prefers_tdh_candidate_with_more_topics(tmp_path, monkeypatch):
    legacy_source = Path("sources") / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_source = Path("sources") / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    assert legacy_source.exists(), f"Source TDH not found: {legacy_source}"
    assert later_source.exists(), f"Source TDH not found: {later_source}"

    input_root = tmp_path / "sources"
    legacy_copy = input_root / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_copy = input_root / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    legacy_copy.parent.mkdir(parents=True, exist_ok=True)
    later_copy.parent.mkdir(parents=True, exist_ok=True)
    legacy_copy.write_bytes(legacy_source.read_bytes())
    later_copy.write_bytes(later_source.read_bytes())

    lookup = {
        legacy_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(legacy_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
            text_encoding="cp437",
            help_contents_topic_id=1,
        ),
        later_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(later_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
        ),
    }

    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(
        bundle_writer,
        "lookup_help_database_entry",
        lambda path, _database: lookup[Path(path).resolve()],
    )

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert len(results) == 1
    result = results[0]
    assert result.input_path == later_copy
    assert result.topic_count == 596
    assert result.json_path == output_dir / "Borland Turbo Debugger/Profiler/Assembler" / "tdhelp.json.gz"

    payload = json.loads(gzip.decompress(result.json_path.read_bytes()).decode("utf-8"))
    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) == 596

    catalog = json.loads((output_dir / "catalog.json").read_text(encoding="utf-8"))
    assert catalog == [
        {
            "group": "Borland Turbo Debugger/Profiler/Assembler",
            "file": "Borland Turbo Debugger/Profiler/Assembler/tdhelp.json.gz",
            "source_file": "TDHELP.TDH",
            "source_files": ["TDHELP.TDH"],
            "name": "Turbo Debugger Help",
            "format": "borland",
            "topics": 596,
        }
    ]


def test_export_bundle_tree_uses_versioned_bundle_stems_for_tdh_variants(tmp_path, monkeypatch):
    legacy_source = Path("sources") / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_source = Path("sources") / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    assert legacy_source.exists(), f"Source TDH not found: {legacy_source}"
    assert later_source.exists(), f"Source TDH not found: {later_source}"

    input_root = tmp_path / "sources"
    legacy_copy = input_root / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    later_copy = input_root / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    legacy_copy.parent.mkdir(parents=True, exist_ok=True)
    later_copy.parent.mkdir(parents=True, exist_ok=True)
    legacy_copy.write_bytes(legacy_source.read_bytes())
    later_copy.write_bytes(later_source.read_bytes())

    lookup = {
        legacy_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(legacy_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
            bundle_stem="tdhelp-1.0",
            text_encoding="cp437",
            help_contents_topic_id=1,
        ),
        later_copy.resolve(): HelpDatabaseEntry(
            crc32=crc32_file(later_copy),
            filenames=("TDHELP.TDH",),
            title="Turbo Debugger Help",
            collection="Borland Turbo Debugger/Profiler/Assembler",
            bundle_stem="tdhelp-2.x",
        ),
    }

    monkeypatch.setattr(bundle_writer, "load_help_database", lambda: object())
    monkeypatch.setattr(
        bundle_writer,
        "lookup_help_database_entry",
        lambda path, _database: lookup[Path(path).resolve()],
    )

    output_dir = tmp_path / "preview"
    results = bundle_writer.export_bundle_tree(input_root, output_dir, layout="helps")

    assert len(results) == 2

    result_by_name = {result.json_path.name: result for result in results}
    assert set(result_by_name) == {"tdhelp-1.0.json.gz", "tdhelp-2.x.json.gz"}
    assert result_by_name["tdhelp-1.0.json.gz"].topic_count == 530
    assert result_by_name["tdhelp-2.x.json.gz"].topic_count == 596

    catalog = json.loads((output_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog_by_file = {item["file"]: item for item in catalog}
    assert set(catalog_by_file) == {
        "Borland Turbo Debugger/Profiler/Assembler/tdhelp-1.0.json.gz",
        "Borland Turbo Debugger/Profiler/Assembler/tdhelp-2.x.json.gz",
    }
    assert catalog_by_file["Borland Turbo Debugger/Profiler/Assembler/tdhelp-1.0.json.gz"]["topics"] == 530
    assert catalog_by_file["Borland Turbo Debugger/Profiler/Assembler/tdhelp-2.x.json.gz"]["topics"] == 596