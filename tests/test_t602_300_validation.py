"""T6HLP native byte contexts, Pascal rows and shared graphics-font cells."""

import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.t602_300 import (
    T602300Reader, _parse_topic_table, _parse_topic_segments,
)
from thelpviewer.server.converter.readers.software602_graphics import decode_graphics_cells
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


ORIGINAL = Path("var/sources/Software 602/t602_300.hlp")
TABLE_END = 0x60F


def source():
    if not ORIGINAL.is_file():
        pytest.skip("Original T602 3.00 HELP is not installed")
    return ORIGINAL.read_bytes()


def rows(*lines):
    return b"".join(bytes([len(line)]) + line for line in lines)


def help_file(blocks, slots=None, order=None):
    slots = slots if slots is not None else list(range(len(blocks)))
    header = bytearray(TABLE_END)
    header[:11] = b"\x0aT6HLP86278"
    body = bytearray()
    for index in order if order is not None else range(len(blocks)):
        struct.pack_into("<IH", header, 15+slots[index]*6, TABLE_END+len(body), len(blocks[index]))
        body.extend(blocks[index])
    struct.pack_into("<I", header, 11, TABLE_END+len(body))
    return bytes(header+body)


def replace_entry(data, slot, offset, size):
    changed = bytearray(data)
    struct.pack_into("<IH", changed, 15+slot*6, offset, size)
    return bytes(changed)


def test_sparse_directory_uses_native_contexts_not_populated_or_one_based_ordinals():
    data = help_file([rows(b"Zero", b"a"), rows(b"Last", b"b")], slots=[0, 255], order=[1, 0])
    document = T602300Reader().read_bytes(data)
    assert [(topic.context_id, topic.names) for topic in document.topics] == [(0, ["Zero"]), (255, ["Last"])]
    assert document.topics[0].next_context == 255
    assert document.topics[1].prev_context == 0
    assert all(not topic.alias_contexts for topic in document.topics)
    payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()
    assert set(payload["topics"]) == {"0", "255"}
    assert payload["metadata"]["display"]["cols"] == 70


def test_all_256_byte_contexts_retain_their_slots():
    document = T602300Reader().read_bytes(help_file([rows(str(context).encode()) for context in range(256)]))
    assert [topic.context_id for topic in document.topics] == list(range(256))
    assert [topic.names for topic in document.topics] == [[str(context)] for context in range(256)]


def test_unused_size_words_shared_payloads_and_empty_topics_are_native_cases():
    data = help_file([rows(b"Shared", b"body")], slots=[4])
    first = _parse_topic_table(data)[0]
    data = replace_entry(data, 0, 0, 65535)
    data = replace_entry(data, 5, first.offset, first.size)
    data = replace_entry(data, 255, len(data), 0)
    document = T602300Reader().read_bytes(data)
    assert [topic.context_id for topic in document.topics] == [4, 5, 255]
    assert document.topics[0].uhf_content == document.topics[1].uhf_content
    assert document.topics[2].uhf_content == []


def test_empty_directory_is_not_an_invalid_nonempty_topic():
    assert T602300Reader().read_bytes(help_file([])).topics == []


def test_zero_length_rows_keep_authored_paragraph_gaps():
    data = help_file([rows(b"Title", b"", b"one", b"", b"", b"two", b"")])
    entry = _parse_topic_table(data)[0]
    assert _parse_topic_segments(data, entry) == [b"Title", b"", b"one", b"", b"", b"two", b""]
    assert T602300Reader().read_bytes(data).topics[0].uhf_content == ["Title", "", "one", "", "", "two"]


def test_nul_inside_a_row_is_a_glyph_cell_not_a_record_separator():
    document = T602300Reader().read_bytes(help_file([rows(b"Title", b"a\0b", b"after")]))
    assert document.topics[0].uhf_content == ["Title", "a\ufffdb", "after"]


def test_title_shadow_and_body_block_glyphs_do_not_disappear():
    data = help_file([rows(b"", b"  \x02Title \x02\x97", b"   \x98\x98\x98", b"", b"body\x96")])
    topic = T602300Reader().read_bytes(data).topics[0]
    assert topic.names == ["Title"]
    assert topic.uhf_content == ["  [b]Title [/b]▄", "   ▀▀▀", "", "body█"]


def test_native_style_switching_reset_and_literal_markup_use_shared_spans():
    data = help_file([rows(b"[b]Title[/b]", b"\x02bold\x04italic\x04 plain", b"next",
                          b"\x13under\x13 plain", b"\x02\x02")])
    topic = T602300Reader().read_bytes(data).topics[0]
    assert topic.names == ["[b]Title[/b]"]
    assert topic.uhf_content == ["[[b]Title[[/b]", "[b]bold[/b][i]italic[/i] plain", "next", "[u]under[/u] plain"]


def test_native_low_glyphs_keyboard_dashes_and_math_keep_their_cells():
    data = help_file([rows(b"Title", b"<Alt\xfeS> <\r> \x17\x18\x19", b"\xa9\xb4\xb5\xb0\xba", b"a\x8d\x0ab")])
    assert T602300Reader().read_bytes(data).topics[0].uhf_content == [
        "Title", "<Alt-S> <↵> ↨↑↓", "√ΣσαΩ", "a ╯b",
    ]


@pytest.mark.parametrize("selector", [0x0F, 0x14, 0x16])
def test_unrepresented_font_sizes_fail_explicitly(selector):
    with pytest.raises(ValueError, match=f"T6HLP topic 0: Unsupported Software602 font-size selector {selector:02X}h"):
        T602300Reader().read_bytes(help_file([rows(b"Title", bytes([selector])+b"text")]))


@pytest.mark.parametrize("slot", [0, 127, 255])
@pytest.mark.parametrize("offset,size", [(1, 1), (TABLE_END-1, 0), (999999, 0), (TABLE_END, 65535)])
def test_invalid_ranges_cannot_hide_in_unused_or_final_slots(slot, offset, size):
    data = help_file([rows(b"Title")], slots=[1])
    with pytest.raises(ValueError, match="points outside"):
        T602300Reader().read_bytes(replace_entry(data, slot, offset, size))


@pytest.mark.parametrize("length", [0, 6, 10, 11, 14, 15, 100, TABLE_END-1])
def test_truncated_header_and_directory_fail(length):
    data = bytearray(help_file([rows(b"Title")])[:length])
    if length >= 15:
        struct.pack_into("<I", data, 11, len(data))
    with pytest.raises(ValueError):
        T602300Reader().read_bytes(bytes(data))


@pytest.mark.parametrize("delta", [-1, 1])
def test_declared_file_size_must_match(delta):
    data = bytearray(help_file([rows(b"Title")]))
    struct.pack_into("<I", data, 11, len(data)+delta)
    with pytest.raises(ValueError, match="declared file size"):
        T602300Reader().read_bytes(bytes(data))


def test_incomplete_row_cannot_borrow_from_the_next_topic():
    with pytest.raises(ValueError, match="T6HLP topic 0 has truncated line"):
        T602300Reader().read_bytes(help_file([b"\x04ab", rows(b"Next")]))


def test_maximum_byte_row_length_uses_wider_increment_arithmetic():
    topic = T602300Reader().read_bytes(help_file([rows(b"Title", b"x"*255)])).topics[0]
    assert topic.uhf_content[1] == "x"*255


def test_original_rows_match_bounded_original_printer_execution():
    data = source()
    assert hashlib.sha256(data).hexdigest() == "f258a874876cc3f01c620e50eabff6d46f054412679067a4855ca16613684b66"
    entries = _parse_topic_table(data)
    trace = [[entry.context_id, [decode_graphics_cells(row) for row in _parse_topic_segments(data, entry)]]
             for entry in entries]
    # Original T602.EXE 0C44:0272, stopped before glyph/pixel handoff.
    assert sum(len(rows) for context, rows in trace) == 3360
    assert sum(not row for entry in entries for row in _parse_topic_segments(data, entry)) == 631
    assert sum(not row for context, rows in trace for row in rows) == 635  # Four selector-only rows.
    assert sum(len(row) for context, rows in trace for row in rows) == 95759
    encoded = json.dumps(trace, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == "754d12e69eca07a27eb968898cec4cbab4c15aec94af1dfaf34f0db8fc596428"
    document = T602300Reader().read_bytes(data)
    names = [(topic.context_id, topic.names) for topic in document.topics]
    index = [(entry.context_id, entry.label.decode()) for entry in document.index_entries]
    for values, digest in ((names, "30619d2164371653adf67ce9084188ada94cd34850de3d1c97905fde88d35abb"),
                           (index, "baa45ef5d5354bd0a5e5840a4496b87388bc7bde85d7e303f990cb9a761a17db")):
        assert hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() == digest
    assert len(document.topics) == len(document.index_entries) == 191
    assert document.topics[0].context_id == 0
    assert all(not topic.alias_contexts for topic in document.topics)


@pytest.mark.parametrize("slot", [0, 34, 127, 255])
def test_damaged_original_descriptor_never_publishes_a_partial_help(slot):
    with pytest.raises(ValueError, match="points outside"):
        T602300Reader().read_bytes(replace_entry(source(), slot, 1, 1))


def test_failed_real_staged_conversion_keeps_live_bundles_and_retry_works(tmp_path):
    original = source()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / "Software 602/t602_300.hlp"
    copy.parent.mkdir(parents=True)
    copy.write_bytes(original)
    kwargs = {"product_keys": ["software602"], "keep_products": ["software602"]}
    build_help_groups(["software602"], sources, helps, **kwargs)
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    damaged = replace_entry(original, 34, 1, 1)
    copy.write_bytes(damaged)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["software602"], sources, helps, **kwargs)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert copy.read_bytes() == damaged
    copy.write_bytes(original)
    result = build_help_groups(["software602"], sources, helps, **kwargs)
    backup = Path(result["backup"])
    assert result["bundles"] == 1
    assert published == {path.relative_to(backup): path.read_bytes() for path in backup.rglob("*") if path.is_file()}
