"""Actual articles, native addresses and shared UHF export of HC31 text."""

import gzip
import json
from pathlib import Path
import re
import struct

import pytest

from test_winhelp import help_file, system, tree
from test_winhelp_text import display
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import iter_help_files
from thelpviewer.server.converter.readers.winhelp import WinHelpReader
from thelpviewer.server.converter.writers.bundle import export_bundle
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.server.converter.readers.winhelp_text import context_hash


ROOT = Path(__file__).resolve().parents[1]
CORPUS = [("Borland C++ 4.x", f) for f in json.loads((ROOT / "tests/golden/winhelp/borland452.json").read_text())]
CORPUS += [("Borland C++ 4.5", f) for f in json.loads((ROOT / "tests/golden/winhelp/borland45.json").read_text())]


def single_article(commands, *, native_hash=None, source_name=b"Native", context_offset=0):
    record = display(commands)
    start = 12 + 49 + len(source_name)
    end = start + 21 + len(record.data1) + len(record.data2)
    article = struct.pack("<IIIIIII", 0, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0xFFFFFFFF, start, end)
    topic = struct.pack("<III", 0xFFFFFFFF, 12, 0)
    topic += struct.pack("<IIIIIB", 49 + len(source_name), len(source_name), 0xFFFFFFFF, start, 49, 2)
    topic += article + source_name
    topic += struct.pack("<IIIIIB", end - start, len(record.data2), 12, end, 21 + len(record.data1), 0x20)
    topic += record.data1 + record.data2
    topic += struct.pack("<IIIIIB", 0, 0, start, 0xFFFFFFFF, 0, 0)
    font = struct.pack("<HHHH", 1, 1, 8, 16) + b"Arial\0\0\0" + bytes((0, 20, 3)) + bytes(8)
    streams = [("|SYSTEM", system(0, [(1, b"Native help\0"), (2, b"Native copyright\0"), (3, bytes(4))])), ("|FONT", font),
               ("|TOPIC", topic), ("|KWBTREE", tree("i24", [(b"keyword", 1, 0)])),
               ("|KWDATA", struct.pack("<I", 0))]
    if native_hash is not None:
        streams.append(("|CONTEXT", tree("L4", [(native_hash, context_offset)])))
    return help_file(streams)


def visible(row):
    return re.sub(r"\[/?(?:b|i|u|link(?::[^\]]+)?|fg:[^\]]+|bg:[^\]]+)\]", "", row).replace("[[", "[")


def test_native_article_zero_and_hash_identity_are_distinct_from_keyword_ordinal():
    native_hash = context_hash(b"ABC")
    source = single_article([(b"", b"\xe3" + struct.pack("<I", native_hash)),
                             (b"go", b"\x89"), (b" body", b"\xff")], native_hash=native_hash)
    doc = WinHelpReader("native.hlp").read_bytes(source)
    assert [t.context_id for t in doc.topics] == [0]
    assert doc.topics[0].uhf_content == ["[link:topic=0,line=1]go[/link] body"]
    assert doc.topics[0].alias_strings == [f"winhelp-hash:{native_hash:08x}", "winhelp-contents"]
    assert [(e.label, e.topic_id, e.line) for e in doc.index_entries] == [(b"keyword", 0, 1)]
    rendered = HelpJsonRenderer(doc, display_encoding="cp1252").render_document()
    assert rendered["metadata"]["help_contents_topic_id"] == 0
    assert doc.metadata["copyright"] == "Native copyright"
    assert rendered["topics"]["0"]["is_help_contents"]


def test_missing_external_targets_and_unsupported_macros_are_preserved_not_deleted():
    payload = b"\4" + struct.pack("<I", 0x12345678) + b"other.hlp\0"
    macro = b'ExecFile("external.exe")\0'
    source = single_article([(b"", b"\xeb" + struct.pack("<H", len(payload)) + payload),
        (b"external", b"\x89"), (b" ", b"\xe3" + struct.pack("<I", 0x87654321)),
        (b"missing", b"\x89"), (b" ", b"\xcc" + struct.pack("<H", len(macro)) + macro),
        (b"native action", b"\x89"), (b"", b"\xff")])
    doc = WinHelpReader().read_bytes(source)
    row = doc.topics[0].uhf_content[0]
    assert "[link:file=other.hlp,alias=winhelp-hash:12345678]external[/link]" in row
    assert "[link:alias=winhelp-hash:87654321]missing[/link]" in row
    assert "[link:alias=winhelp-macro:" in row and "native action[/link]" in row
    assert doc.metadata["winhelp_macros"][0]["macro"] == macro[:-1].decode()


def test_context_target_at_nonzero_text_cursor_maps_to_wrapped_display_line():
    text = b"word " * 40
    source = single_article([(text, b"\xff")], native_hash=1234, context_offset=130)
    doc = WinHelpReader().read_bytes(source)
    assert len(doc.topics[0].uhf_content) > 1
    # The context is still article 0; its cursor is not another topic number.
    assert "winhelp-hash:000004d2" in doc.topics[0].alias_strings
    assert doc.topics[0].alias_lines == {"winhelp-hash:000004d2": 2}
    payload = HelpJsonRenderer(doc, display_encoding="cp1252").render_document()
    assert payload["topics"]["0"]["aliases"]["lines"] == {"winhelp-hash:000004d2": 2}
    assert doc.topics[0].to_dict()["alias_lines"] == {"winhelp-hash:000004d2": 2}
    link_source = single_article([(b"", b"\xe3" + struct.pack("<I", 1234)),
                                  (text, b"\x89"), (b"", b"\xff")],
                                 native_hash=1234, context_offset=130)
    linked = WinHelpReader().read_bytes(link_source)
    assert "[link:topic=0,line=2]" in linked.topics[0].uhf_content[0]


def test_generic_alias_lines_apply_to_exported_numeric_and_symbolic_index_targets():
    from thelpviewer.server.converter.base import HelpDocument, TopicRecord, IndexEntry

    topic = TopicRecord(7, [b"first", b"second", b"third"],
                        alias_contexts=[17], alias_strings=["details"],
                        alias_lines={"17": 2, "details": 3})
    doc = HelpDocument("winhelp", "input.hlp", [topic],
                       [IndexEntry(b"numeric", 17), IndexEntry(b"details", 999)])
    payload = HelpJsonRenderer(doc).render_document()
    entries = [entry for group in payload["index"] for entry in group["entries"]]
    assert {entry["label"]: (entry["topic_id"], entry["line"]) for entry in entries} == {
        "numeric": (7, 2), "details": (7, 3)}
    topic.alias_lines["not-declared"] = 2
    with pytest.raises(ValueError, match="declared aliases"):
        HelpJsonRenderer(doc).render_document()


def test_invalid_font_and_format_fail_without_turning_into_title_only_articles():
    source = single_article([(b"", b"\x80\xff\xff"), (b"text", b"\xff")])
    with pytest.raises(ValueError, match="font selection"):
        WinHelpReader().read_bytes(source)


@pytest.fixture(scope="module")
def win31():
    source = ROOT / "data/sources/Borland C++ 4.x/WIN31WH.HLP"
    return WinHelpReader(source.name).read_bytes(source.read_bytes())


def test_fonttbl_is_the_actual_full_article_with_authored_columns_and_real_links(win31):
    topic = next(t for t in win31.topics if t.context_id == 2559)
    rows = [visible(row) for row in topic.uhf_content]
    assert rows[0].strip() == r"\fonttbl RTF statement"
    assert len(rows) > 40
    assert any("creates a font table" in row for row in rows)
    assert any(r"{\fn\family font-name;}" in row for row in rows)
    assert " Parameter   Description" in rows
    assert "             Value     Meaning" in rows
    assert any(row.strip() == "─" * len(row) for row in rows if row)
    assert any(row.startswith(" font-name   Specifies") for row in rows)
    assert {int(v) for row in topic.uhf_content for v in re.findall(r"\[link:topic=(\d+),", row)} == {2552, 2556, 2561, 2572}
    keyword, = [e for e in win31.index_entries if e.label == b"\\fonttbl RTF statement"]
    assert (keyword.topic_id, keyword.line) == (2559, 1)
    assert next(t for t in win31.topics if t.context_id == 52).names != topic.names


def test_native_hlp_body_exports_through_standard_uhf_not_a_new_html_renderer(win31):
    payload = HelpJsonRenderer(win31, display_encoding="cp1252").render_document()
    assert payload["metadata"]["source"]["format"] == "winhelp"
    assert payload["metadata"]["display"]["cols"] == 80
    assert payload["metadata"]["show_topic_titles"] is False
    assert payload["metadata"]["winhelp_projection"] == "fixed-cell-text"
    assert payload["metadata"]["winhelp_fonts"]
    assert len(payload["topics"]) == 3623
    assert len(payload["topics"]["2559"]["content"]) > 40
    assert "<" not in "".join(payload["topics"]["2559"]["content"])
    assert payload["metadata"]["winhelp_unmapped_glyphs"] == [(12, 148)]


def test_unrendered_picture_payloads_and_positions_remain_explicit(win31):
    objects = win31.metadata["winhelp_objects"]
    assert len(objects) == 605
    assert all(o["placement"] in {0x86, 0x87, 0x88} and o["payload"] for o in objects)
    assert any("▧" in row for topic in win31.topics for row in topic.uhf_content)


def test_matching_hlp_is_selected_instead_of_duplicate_index_bundle(tmp_path):
    collection = ROOT / "data/sources/Borland C++ 4.x"
    for ext in ("HLP", "HLX"):
        (tmp_path / f"OPENHELP.{ext}").write_bytes((collection / f"OPENHELP.{ext}").read_bytes())
    assert [p.name for p in iter_help_files(tmp_path)] == ["OPENHELP.HLP"]
    (tmp_path / "OPENHELP.HLP").unlink()
    assert [p.name for p in iter_help_files(tmp_path)] == ["OPENHELP.HLX"]


def test_hlp_bundle_has_native_title_article_zero_contents_and_browse(tmp_path):
    source = ROOT / "data/sources/Borland C++ 4.x/OPENHELP.HLP"
    result = export_bundle(source, tmp_path)
    assert result.format_name == "winhelp" and result.topic_count == 42
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))
    assert payload["metadata"]["source"]["filename"] == "OPENHELP.HLP"
    topic = payload["topics"]["0"]
    assert topic["title"] == "Using Help in Borland C++"
    assert topic["frozen_rows"] > 0
    assert topic["is_help_contents"]
    assert topic["nav"] and all(n["topic_id"] in range(42) for n in topic["nav"].values())


def test_failed_hlp_conversion_keeps_existing_published_bundles(tmp_path):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    product = sources / "Borland C++ 4.x"
    product.mkdir(parents=True)
    valid = single_article([(b"valid body", b"\xff")])
    (product / "NATIVE.HLP").write_bytes(valid)
    build_help_groups(["borland"], sources, helps)
    before = {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    (product / "NATIVE.HLP").write_bytes(single_article([(b"broken body", b"\x7f")]))
    with pytest.raises(ValueError, match="conversion failed"):
        build_help_groups(["borland"], sources, helps)
    assert {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("collection,fixture", CORPUS,
                         ids=[collection + "/" + f["file"] for collection, f in CORPUS])
def test_all_retained_hlp_articles_and_keyword_destinations_convert(collection, fixture):
    source = ROOT / "data/sources" / collection / fixture["file"]
    doc = WinHelpReader(source.name).read_bytes(source.read_bytes())
    assert len(doc.topics) == fixture["topics"]
    assert len(doc.index_entries) == fixture["references"]
    topic_map = {t.context_id: t for t in doc.topics}
    assert set(topic_map) == set(range(fixture["topics"]))
    assert doc.metadata["title"] == fixture["title"]
    for entry in doc.index_entries:
        assert entry.topic_id in topic_map
        assert 1 <= entry.line <= max(1, len(topic_map[entry.topic_id].uhf_content))
    for topic in doc.topics:
        assert set(topic.alias_lines) <= set(topic.alias_strings)
        assert all(1 < line <= max(1, len(topic.uhf_content)) for line in topic.alias_lines.values())
        for item in topic.nav_items:
            assert item.topic_id in topic_map
        for row in topic.uhf_content:
            for target in re.findall(r"\[link:topic=(\d+),", row):
                assert int(target) in topic_map
