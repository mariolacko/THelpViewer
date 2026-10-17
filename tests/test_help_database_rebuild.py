"""CRC maintenance must not destroy the shared downloader/converter manifest."""

import json
from pathlib import Path
import stat
import sys

import pytest

from thelpviewer.help_database import crc32_file, load_help_manifest
from tools import rebuild_help_database as rebuild


@pytest.mark.parametrize("explicit", [False, True])
def test_database_tool_sources_default_to_working_state(tmp_path, monkeypatch, explicit):
    monkeypatch.setenv("THELP_DATA_DIR", str(tmp_path / "permanent"))
    monkeypatch.setenv("THELP_STATE_DIR", str(tmp_path / "work"))
    expected = tmp_path / "inputs" if explicit else tmp_path / "work" / "sources"
    if explicit:
        monkeypatch.setenv("THELP_SOURCES_DIR", str(expected))
    else:
        monkeypatch.delenv("THELP_SOURCES_DIR", raising=False)
    database = tmp_path / "help-database.json"
    monkeypatch.setattr(sys, "argv", ["rebuild_help_database.py", "--output", str(database)])
    def rebuild_database(sources, output):
        assert sources == expected and output == database
        return 0
    monkeypatch.setattr(rebuild, "rebuild_help_database", rebuild_database)
    assert rebuild.main() == 0


def test_rebuild_retains_complete_manifest_and_explicit_product_assignments(tmp_path):
    original = json.loads(Path("thelpviewer/config/help-database.json").read_text())
    database = tmp_path / "help-database.json"
    database.write_text(json.dumps(original))
    sources = tmp_path / "sources"
    sources.mkdir()

    count = rebuild.rebuild_help_database(sources, database)
    result = json.loads(database.read_text())

    for key in original.keys() - {"entries", "generated_at"}:
        assert result[key] == original[key]
    original_entries = [entry for entry in original["entries"] if "crc32" in entry]
    assert result["entries"] == original_entries
    assert count == len(original_entries)
    manifest = load_help_manifest(database)
    assert manifest.version == 2
    assert manifest.sources and manifest.converters and manifest.products and manifest.build_groups
    for crc in (0x07E89446, 0x9AC3E64A):
        assert manifest.entry_map[crc].product_key == "tasm"


def test_rebuild_merges_discovery_without_losing_verified_or_unknown_metadata(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "RENAMED.HLP"
    source.write_bytes(b"unrecognised original help file")
    crc = f"{crc32_file(source):08X}"
    entry = {
        "crc32": crc.lower(), "filenames": ["ORIGINAL.HLP"],
        "title": "Verified title", "collection": "Verified collection",
        "text_encoding": "cp852", "language": "cs", "product": "sample",
        "release": "1.2", "bundle_stem": "stable-url", "help_contents_topic_id": 7,
        "provenance": {"verified": True},
        "sources": {"winworld": {"search_text": "Sample 1.2 original disks",
                                  "direct_urls": ["https://example.com/release/1.2"]}},
    }
    database = tmp_path / "help-database.json"
    database.write_text(json.dumps({"version": 2, "extra": {"future": 1}, "entries": [entry]}))

    assert rebuild.rebuild_help_database(sources, database) == 1
    result = json.loads(database.read_text())
    assert result["version"] == 2 and result["extra"] == {"future": 1}
    expected = dict(entry, crc32=crc, filenames=["ORIGINAL.HLP", "RENAMED.HLP"])
    assert result["entries"] == [expected]
    rebuild.rebuild_help_database(sources, database)
    assert json.loads(database.read_text())["entries"] == [expected]


@pytest.mark.parametrize("content", [
    "{", "[]", '{}', '{"version": 2, "entries": {}}',
    '{"version": 1, "entries": []}',
    '{"version": 2, "entries": [{"crc32": "00000001", "filename": "OLD.HLP"}]}',
    '{"version": 2, "entries": [null]}',
    '{"version": 2, "entries": [{"crc32": "bad CRC", "filenames": ["BAD.HLP"]}]}',
    '{"version": 2, "entries": [{"crc32": "100000000", "filenames": ["BAD.HLP"]}]}',
    '{"version": 2, "entries": [{"crc32": "00000000"}]}',
    '{"version": 2, "entries": [{"crc32": "00000001", "filenames": ["A.HLP"]},'
    '{"crc32": "1", "filenames": ["B.HLP"]}]}',
])
def test_invalid_database_is_not_overwritten(tmp_path, content):
    sources = tmp_path / "sources"
    sources.mkdir()
    database = tmp_path / "help-database.json"
    database.write_text(content)
    before = database.read_bytes()

    with pytest.raises(ValueError):
        rebuild.rebuild_help_database(sources, database)
    assert database.read_bytes() == before
    assert sorted(tmp_path.iterdir()) == sorted([sources, database])


def test_missing_sources_do_not_rewrite_database(tmp_path):
    database = tmp_path / "help-database.json"
    database.write_text('{"version": 2, "entries": []}')
    before = database.read_bytes()
    with pytest.raises(ValueError, match="Sources directory"):
        rebuild.rebuild_help_database(tmp_path / "missing", database)
    assert database.read_bytes() == before


def test_failed_publication_retains_manifest_and_removes_temporary_file(tmp_path, monkeypatch):
    sources = tmp_path / "sources"
    sources.mkdir()
    database = tmp_path / "help-database.json"
    database.write_text('{"version": 2, "entries": []}')
    before = database.read_bytes()

    def fail_replace(source, target):
        assert target == database
        assert json.loads(Path(source).read_text())["version"] == 2
        raise OSError("publication failed")

    monkeypatch.setattr(rebuild.os, "replace", fail_replace)
    with pytest.raises(OSError, match="publication failed"):
        rebuild.rebuild_help_database(sources, database)
    assert database.read_bytes() == before
    assert sorted(tmp_path.iterdir()) == sorted([sources, database])


def test_new_output_copies_complete_current_manifest_and_retains_file_mode(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "NEW.HLP").write_bytes(b"unrecognised original help file")
    database = tmp_path / "help-database.json"
    original = json.loads(rebuild.help_database_path().read_text())
    original_entries = [entry for entry in original["entries"] if "crc32" in entry]
    count = len(original_entries) + 1
    assert rebuild.rebuild_help_database(sources, database) == count
    result = json.loads(database.read_text())
    assert result["version"] == 2
    for key in original.keys() - {"entries", "generated_at"}:
        assert result[key] == original[key]
    assert result["entries"][:-2] == original_entries
    assert result["entries"][-2]["kind"] == "separator"
    assert result["entries"][-1]["filenames"] == ["NEW.HLP"]
    database.chmod(0o640)
    assert rebuild.rebuild_help_database(sources, database) == count
    assert stat.S_IMODE(database.stat().st_mode) == 0o640
