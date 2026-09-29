"""HelpPC and FreeDOS HTML import behaviour."""

import gzip
from io import BytesIO
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

import pytest

from thelpviewer.converter.exporter import detect_format_handler, load_document
from thelpviewer.converter.writers.bundle import export_bundle_tree
from thelpviewer.help_database import load_help_database, lookup_help_database_entry


def test_helppc_exports_separate_databases_with_cross_file_links(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "ASM.TXT").write_bytes(b"@Assembly\r\n:first:alias\r\n^First\r\n See ~second~ and ~~ literal\r\n")
    (sources / "C.TXT").write_bytes(b"@C\r\n:second\r\n%Second\r\n")

    results = export_bundle_tree(sources, tmp_path / "out", layout="helps")
    assert {result.json_path.name for result in results} == {"asm.json.gz", "c.json.gz"}
    assert {result.format_name for result in results} == {"helppc"}
    payload = json.loads(gzip.decompress((tmp_path / "out" / "asm.json.gz").read_bytes()))
    assert len(payload["topics"]) == 1
    first = payload["topics"]["1"]
    assert any("[link:file=C.TXT,topic=1]second[/link]" in line for line in first["content"])
    assert any("~ literal" in line for line in first["content"])
    assert len(payload["index"]) == 2
    catalog = json.loads((tmp_path / "out" / "catalog.json").read_text(encoding="utf-8"))
    assert {entry["source_file"] for entry in catalog} == {"ASM.TXT", "C.TXT"}


def test_helppc_links_match_keys_with_repeated_spaces(tmp_path):
    (tmp_path / "ASM.TXT").write_bytes(
        b"@Assembly\r\n:First  Key\r\n See ~first key~ and ~SECOND KEY~ and ~second   key~\r\n"
    )
    (tmp_path / "C.TXT").write_bytes(b"@C\r\n:Second  Key\r\n Text\r\n")

    document = load_document(tmp_path / "ASM.TXT")
    line = document.topics[0].uhf_content[0]
    assert "[link:topic=1]first key[/link]" in line
    assert "[link:file=C.TXT,topic=1]SECOND KEY[/link]" in line
    assert "[link:file=C.TXT,topic=1]second   key[/link]" in line


def test_freedos_zip_import_keeps_internal_links_and_preformatted_text(tmp_path):
    source = tmp_path / "HHSTNDRD.ZIP"
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("help/index.htm", "<html><head><title>Contents</title></head><body><pre>Read <a href='../base/foo.htm'>foo</a> now.\n  Next</pre></body></html>")
        archive.writestr("base/foo.htm", "<html><head><title>Foo</title></head><body><h1>Foo</h1><p>Done.</p></body></html>")
    source.write_bytes(buffer.getvalue())

    assert detect_format_handler(source).name == "freedos-html"
    document = load_document(source)
    assert len(document.topics) == 2
    index_topic = next(topic for topic in document.topics if topic.is_help_contents)
    foo_topic = next(topic for topic in document.topics if topic.names == ["Foo"])
    assert any(f"[link:topic={foo_topic.context_id}]foo[/link]" in line for line in index_topic.uhf_content)
    assert any(line.startswith("  Next") for line in index_topic.uhf_content)
    assert "[b]Foo[/b]" in foo_topic.uhf_content

    results = export_bundle_tree(tmp_path, tmp_path / "out", layout="helps")
    assert len(results) == 1
    payload = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    assert payload["metadata"]["help_contents_topic_id"] == index_topic.context_id


def test_reference_crc_records_match_downloaded_files_when_present():
    root = Path("sources")
    paths = [
        *(root / "HelpPC 2.10" / name for name in (
            "ASM.TXT", "C.TXT", "HARDWARE.TXT", "INTERRUP.TXT", "MISC.TXT", "TABLES.TXT"
        )),
        root / "FreeDOS HTML Help 1.1.1a" / "HHSTNDRD.ZIP",
        root / "Microsoft MS-DOS 6.22" / "HELP.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45QCK.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45ADVR.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45ENER.HLP",
    ]
    database = load_help_database()
    for path in paths:
        if path.exists():
            entry = lookup_help_database_entry(path, database)
            assert entry is not None
            assert entry.product_key in {"freedos-help", "helppc", "msdos622", "qb45"}


def test_downloaded_reference_help_exports_into_help_files_catalog(tmp_path):
    root = Path("sources")
    required = (
        root / "FreeDOS HTML Help 1.1.1a" / "HHSTNDRD.ZIP",
        root / "HelpPC 2.10" / "ASM.TXT",
        root / "Microsoft MS-DOS 6.22" / "HELP.HLP",
        root / "Microsoft QuickBASIC 4.5" / "QB45QCK.HLP",
    )
    if not all(path.is_file() for path in required):
        pytest.skip("DOS reference help files were not downloaded")

    selected_sources = tmp_path / "sources"
    selected_sources.mkdir()
    for name in (
        "FreeDOS HTML Help 1.1.1a", "HelpPC 2.10",
        "Microsoft MS-DOS 6.22", "Microsoft QuickBASIC 4.5",
    ):
        shutil.copytree(root / name, selected_sources / name)
    results = export_bundle_tree(selected_sources, tmp_path / "helps", layout="helps")
    assert len(results) == 11
    assert all(result.topic_count > 0 for result in results)
    catalog = json.loads((tmp_path / "helps" / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog) == 11
    assert {entry["product"] for entry in catalog} == {
        "freedos-help", "helppc", "msdos622", "qb45",
    }
    assert {entry["group"] for entry in catalog} == {
        "FreeDOS HTML Help 1.1.1a", "HelpPC 2.10",
        "Microsoft MS-DOS 6.22", "Microsoft QuickBASIC 4.5",
    }
    assert all((tmp_path / "helps" / entry["file"]).is_file() for entry in catalog)
