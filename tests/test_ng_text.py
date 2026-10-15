"""Text cells verified with the original NG 1.00/1.02/1.04 video renderer."""

import gzip
import json

import pytest

from thelpviewer.server.converter.readers.ng import NGReader, _decode_text
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.converter.uhf_markup import render_uhf_line
from test_ng_validation import header, long, short


@pytest.mark.parametrize("raw,cells,attributes", [
    (b"plain ^Bbold ^Uunder ^Rreverse ^Bbold ^Nnormal",
     b"plain bold under reverse bold normal",
     b"\x07"*6 + b"\x0f"*5 + b"\x7f"*6 + b"\x70"*8 + b"\x0f"*5 + b"\x07"*6),
    (b"^A1Fred^A1Fnormal^A0Fbright^Bnormal", b"rednormalbrightnormal",
     b"\x1f"*3 + b"\x07"*6 + b"\x0f"*6 + b"\x07"*6),
    (b"^Bbold^A0Fnormal", b"boldnormal", b"\x0f"*4 + b"\x07"*6),
    (b"^Bbold^Rreverse^Uunder^Uplain", b"boldreverseunderplain",
     b"\x0f"*4 + b"\x70"*7 + b"\x7f"*5 + b"\x07"*5),
    (b"A\xff\x03B", b"A   B", b"\x07"*5),
    (b"A\xff", b"A", b"\x07"),
    (b"A\xff\xffB", b"A" + b" "*255 + b"B", b"\x07"*257),
    (b"unknown^z end^", b"unknownZ end", b"\x07"*12),
    (b"^[text^] ^(math^)", b"[text] (math)", b"\x07"*13),
    (b"^^:^C00:^C09:^CFF", b"^:\0:\t:\xff", b"\x07"*7),
    (b"^Cgg", b"\x10", b"\x07"),
    (b"^C/0", b"\xf0", b"\x07"),
    (b"^C1", b"\x01", b"\x07"),
    (b"^C", b"\0", b"\x07"),
    (b"^A1", b"", b""),
    (b"^B", b"", b""),
    (b"^", b"", b""),
    (b"^a1ehello^nnormal", b"hellonormal", b"\x1e"*5 + b"\x07"*6),
    (b"^bnext", b"next", b"\x0f"*4),
    (b"plain", b"plain", b"\x07"*5),
])
def test_native_character_and_attribute_vectors(raw, cells, attributes):
    assert _decode_text(raw) == (cells, attributes)


@pytest.mark.parametrize("source,target", [(0x81, 0x9A), (0x82, 0x90), (0x84, 0x8E),
                                         (0x86, 0x8F), (0x87, 0x80), (0x91, 0x92),
                                         (0x94, 0x99), (0xA4, 0xA5)])
def test_native_oem_uppercase_applies_to_escape_dispatch_not_literal_cells(source, target):
    assert _decode_text(bytes([94, source])) == (bytes([target]), b"\x07")
    assert _decode_text(bytes([source])) == (bytes([source]), b"\x07")


def test_every_hex_literal_is_one_cell_and_is_not_recursively_reinterpreted():
    raw = b"".join(f"^C{value:02X}".encode() for value in range(256))
    assert _decode_text(raw) == (bytes(range(256)), b"\x07"*256)


def test_literal_video_controls_are_glyphs_not_browser_tabs_or_line_breaks():
    reader = NGReader()
    cells, visible, styles = reader._text_line(b"^C00\x01\x07^C09^C0A^C0D^C1A^C1B^C7F")
    assert cells == bytes([0, 1, 7, 9, 10, 13, 26, 27, 127])
    assert visible == " ☺•○◙♪→←⌂"
    assert styles == []


def test_shared_spans_do_not_stack_native_modes_or_confuse_attribute_equality():
    reader = NGReader()
    raw = b"^Bbold^Uunder^Rreverse^A1Fcolor^A1Fnormal^A0Fbright^Bplain"
    cells, visible, styles = reader._text_line(raw)
    assert cells == b"boldunderreversecolornormalbrightplain"
    assert render_uhf_line(visible, style_spans=styles) == (
        "[b]bold[/b][u]under[/u][r]reverse[/r][color:15:1]color[/color]"
        "normal[b]bright[/b]plain"
    )


@pytest.mark.parametrize("raw,visible", [
    (b"Name\xff\x03description", "Name   description"),
    (b"^B\xff\x03Name^B", "   Name"),
    (b"\xff\x03Name", "   Name"),
    (b"Multi word name\xff\x05description", "Multi word name     description"),
])
def test_short_reference_covers_the_entire_row_not_the_first_compressed_space(raw, visible):
    document = NGReader().read_bytes(header() + short([(raw, 378)]))
    topic = document.topics[0]
    assert len(topic.positional_keywords) == 1
    keyword = topic.positional_keywords[0]
    assert (keyword.target_context, keyword.line, keyword.first_column, keyword.last_column) == (378, 1, 1, len(visible))
    assert topic.raw_lines == [visible.encode("cp437")]
    assert "[link:topic=378]" in topic.uhf_content[0]
    assert "Name" in topic.uhf_content[0] or "name" in topic.uhf_content[0]


def test_row_style_does_not_leak_into_the_next_row():
    document = NGReader().read_bytes(header() + long([b"^Bbold", b"plain"]))
    assert document.topics[0].uhf_content == ["[b]bold[/b]", "plain"]


def test_incomplete_literal_never_borrows_text_from_the_next_declared_row():
    document = NGReader().read_bytes(header() + long([b"^C", b"ABC"]))
    assert document.topics[0].raw_lines == [b"\0", b"ABC"]
    assert document.topics[0].uhf_content == [" ", "ABC"]


def test_literal_brackets_glyphs_and_whole_row_targets_survive_bundle_export(tmp_path):
    source = tmp_path / "sources/Norton Guides/SAMPLE.NG"
    source.parent.mkdir(parents=True)
    original = header() + short([(b"^C1AName\xff\x03^[[test^]", 378)])
    source.write_bytes(original)
    result = export_bundle_tree(tmp_path / "sources", tmp_path / "helps", source_paths=[source], layout="helps")
    bundle = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    content = bundle["topics"]["378"]["content"][0]
    assert content == "[link:topic=378]→Name   [[[[test][/link]"
    assert source.read_bytes() == original
