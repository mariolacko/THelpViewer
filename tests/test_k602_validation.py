"""K6HLP directory boundaries and complete, row-balanced topic decoding."""

import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.k602 import (
    K602Reader, K602TopicEntry, K602_TABLE_OFFSET, K602_TABLE_END,
    _iter_table_entries, _parse_topic_lines,
)
from thelpviewer.server.converter.readers.software602_graphics import decode_graphics_cells, decode_graphics_byte
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


ORIGINAL = Path("data/sources/Software 602/K602.HLP")


def source():
    if not ORIGINAL.is_file():
        pytest.skip("Original K602 HELP is not installed")
    return ORIGINAL.read_bytes()


def records(*lines):
    return b"".join(bytes([len(line)]) + line for line in lines)


def help_file(blocks, slots=None, physical_order=None):
    """Create the native 256-slot directory without assuming sorted offsets."""
    slots = slots or list(range(len(blocks)))
    header = bytearray(K602_TABLE_END)
    header[:11] = b"\x0aK6HLP86278"
    body = bytearray()
    for index in physical_order or range(len(blocks)):
        struct.pack_into("<IH", header, K602_TABLE_OFFSET + slots[index] * 6,
                         len(header) + len(body), len(blocks[index]))
        body.extend(blocks[index])
    struct.pack_into("<I", header, 11, len(header) + len(body))
    return bytes(header + body)


def replace_entry(data, slot, offset, size):
    changed = bytearray(data)
    struct.pack_into("<IH", changed, K602_TABLE_OFFSET + slot * 6, offset, size)
    return bytes(changed)


def test_sparse_and_physically_reordered_topics_keep_their_context_ids():
    data = help_file([records(b"First", b"alpha"), records(b"Second", b"beta")],
                     slots=[2, 7], physical_order=[1, 0])
    document = K602Reader().read_bytes(data)
    assert document.metadata["table_entry_count"] == 256
    assert [(topic.context_id, topic.names, topic.uhf_content) for topic in document.topics] == [
        (2, ["First"], ["First", "alpha"]),
        (7, ["Second"], ["Second", "beta"]),
    ]
    payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()
    assert set(payload["topics"]) == {"2", "7"}


def test_unused_slots_at_both_ends_and_shared_payloads_are_valid():
    data = bytearray(help_file([records(b"Shared", b"body")], slots=[4]))
    # Leading/trailing zero slots remain part of the fixed directory.
    data[K602_TABLE_OFFSET:K602_TABLE_OFFSET+6] = data[K602_TABLE_OFFSET+24:K602_TABLE_OFFSET+30]
    data[K602_TABLE_OFFSET+24:K602_TABLE_OFFSET+30] = b"\0" * 6
    document = K602Reader().read_bytes(bytes(data))
    assert document.metadata["table_entry_count"] == 256
    assert [topic.context_id for topic in document.topics] == [0]
    data[K602_TABLE_OFFSET+12:K602_TABLE_OFFSET+18] = data[K602_TABLE_OFFSET:K602_TABLE_OFFSET+6]
    document = K602Reader().read_bytes(bytes(data))
    assert [topic.context_id for topic in document.topics] == [0, 2]
    assert document.topics[0].uhf_content == document.topics[1].uhf_content


def test_valid_text_that_looks_like_another_descriptor_is_not_a_directory_entry():
    # At the payload start these six bytes also spell offset 1664, size 1.
    block = records(b"\x06\0\0\1\0" + b"x" * 123)
    document = K602Reader().read_bytes(help_file([block]))
    assert len(document.topics) == 1
    assert document.metadata["table_entry_count"] == 256
    assert len(document.topics[0].uhf_content[0]) == 128


@pytest.mark.parametrize("slot", [1, 2, 3])
@pytest.mark.parametrize("offset,size", [(K602_TABLE_END-1, 1), (1000, 0), (100000, 10), (1, 1)])
def test_invalid_middle_or_final_directory_entries_cannot_end_the_table(slot, offset, size):
    data = help_file([records(b"a"), records(b"b"), records(b"c"), records(b"d")])
    with pytest.raises(ValueError, match="K602 topic table"):
        K602Reader().read_bytes(replace_entry(data, slot, offset, size))


def test_payload_cannot_overlap_the_final_directory_entry():
    data = help_file([records(b"first"), records(b"second")])
    with pytest.raises(ValueError, match="K602 topic table"):
        K602Reader().read_bytes(replace_entry(data, 0, K602_TABLE_END-1, 1))


@pytest.mark.parametrize("length", [0, 6, 10, 11, 14, 15, 116, 117, 118, 122,
                                    K602_TABLE_END-6, K602_TABLE_END-1])
def test_incomplete_headers_and_directories_fail_with_value_error(length):
    data = bytearray(help_file([records(b"text")])[:length])
    if length >= 15:
        struct.pack_into("<I", data, 11, len(data))
    with pytest.raises(ValueError):
        K602Reader().read_bytes(bytes(data))


def test_empty_directory_and_unused_size_words_are_valid():
    data = bytearray(K602_TABLE_END)
    data[:11] = b"\x0aK6HLP86278"
    struct.pack_into("<I", data, 11, len(data))
    struct.pack_into("<H", data, K602_TABLE_OFFSET + 4, 65535)
    document = K602Reader().read_bytes(bytes(data))
    assert document.topics == []
    assert document.metadata["table_entry_count"] == 256


def test_populated_zero_byte_topic_at_eof_is_valid():
    data = help_file([records(b"text")], slots=[255])
    document = K602Reader().read_bytes(replace_entry(data, 0, len(data), 0))
    assert [topic.context_id for topic in document.topics] == [0, 255]
    assert document.topics[0].uhf_content == []


@pytest.mark.parametrize("delta", [-1, 1])
def test_declared_size_cannot_hide_truncated_or_extra_bytes(delta):
    data = bytearray(help_file([records(b"text")]))
    struct.pack_into("<I", data, 11, len(data)+delta)
    with pytest.raises(ValueError, match="declared file size"):
        K602Reader().read_bytes(bytes(data))


def test_line_cannot_borrow_bytes_from_the_next_topic():
    with pytest.raises(ValueError, match="K602 topic 0 has truncated line"):
        K602Reader().read_bytes(help_file([b"\x05abc", records(b"second")]))


def test_single_zero_length_record_is_an_empty_topic_not_an_unused_slot():
    document = K602Reader().read_bytes(help_file([b"\0", records(b"title", b"", b"body")]))
    assert [topic.context_id for topic in document.topics] == [0, 1]
    assert document.topics[0].uhf_content == []
    assert document.topics[1].uhf_content == ["title", "", "body"]


@pytest.mark.parametrize("newline", [b"\x8d\x0a", b"\x0a"])
@pytest.mark.parametrize("marker", [b"\x02", b"\x04"])
def test_lf_and_8d_are_native_glyphs_not_invented_internal_line_breaks(newline, marker):
    data = help_file([records(b"Title", marker+b"one"+newline+b"two"+marker+b" plain")])
    content = K602Reader().read_bytes(data).topics[0].uhf_content
    tag = "b" if marker == b"\x02" else "i"
    glyphs = " ╯" if len(newline) == 2 else "╯"
    assert content == ["Title", f"[{tag}]one{glyphs}two[/{tag}] plain"]


def test_literal_native_blocks_and_brackets_are_not_removed_from_the_body():
    data = help_file([records(b"Title", b"[\x96/\x97] \x18\x19 <\r>",
                              b"\x02bold\x97\x02\x96", b"\x02open")])
    assert K602Reader().read_bytes(data).topics[0].uhf_content == [
        "Title", "[[█/▄] ↑↓ <↵>", "[b]bold▄[/b]█", "[b]open[/b]",
    ]


def test_different_native_highlight_selectors_switch_category_instead_of_cancelling_it():
    data = help_file([records(b"Title", b"\x02one\x04two\x04 plain", b"\x04one\x02two\x02 plain")])
    assert K602Reader().read_bytes(data).topics[0].uhf_content == [
        "Title", "[b]one[/b][i]two[/i] plain", "[i]one[/i][b]two[/b] plain",
    ]


def test_all_byte_contexts_including_zero_and_255_have_exact_native_slots():
    data = help_file([records(str(context).encode()) for context in range(256)])
    document = K602Reader().read_bytes(data)
    assert [topic.context_id for topic in document.topics] == list(range(256))
    assert [topic.names for topic in document.topics] == [[str(context)] for context in range(256)]


def test_original_rows_match_the_original_executable_before_screen_handoff():
    data = source()
    assert hashlib.sha256(data).hexdigest() == "189dc2f97670f3ca3ebc2f950aecf3fd3976ecd2e03b619b80522570e0bf8d83"
    document = K602Reader().read_bytes(data)
    # Golden trace from bounded original K602.EXE 071A:02BD execution,
    # stopping before the screen writer: literal font bytes and categories.
    trace = [[context, [decode_graphics_cells(row) for row in _parse_topic_lines(data, K602TopicEntry(context, offset, size))]]
             for context, offset, size in _iter_table_entries(data) if offset]
    assert sum(len(rows) for context, rows in trace) == 1773
    encoded = json.dumps(trace, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == "6759d69ef558e294b532267bd4a1f64a630aab2ebadfbab6016e03ffd95699ee"
    names = [(topic.context_id, topic.names) for topic in document.topics]
    index = [(entry.context_id, entry.label.decode()) for entry in document.index_entries]
    for values, digest in ((names, "bb1cecb6d53e12a8f303f00cee2971e5ccd1b2a97c0841313c9fc03f6336dea2"),
                           (index, "ab170af54cd43383003d42e8993eb74668c1e24b08c36a7e9fe312098de5cb51")):
        assert hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() == digest
    assert len(document.topics) == 115
    assert document.metadata["table_entry_count"] == 256
    assert document.topics[0].context_id == 17
    assert all(not topic.alias_contexts for topic in document.topics)


@pytest.mark.parametrize("first,expected", [
    (0x80, "Çùè§ß£ÆØÅæøå· ¤ò"), (0x90, "ìÞ¡Ñ¿ñ█▄▀·······"),
    (0xA0, "≡±≥≤⌠⌡÷≈°√²½¼■«»"), (0xB0, "αβΓπΣσµτΦΘΩδ∞φε∩"),
    (0xC0, "┌á└čďěŕ─üíůĺľöňó"), (0xD0, "ôäřšťú├éàýž┬ˇ´˚┼"),
    (0xE0, "┐Á┘ČĎĚŔ│ÜÍŮĹĽÖŇÓ"), (0xF0, "ÔÄŘŠŤÚ┤ÉÀÝŽ┴¨^-·"),
])
def test_high_bytes_follow_the_native_font_not_kamenicky(first, expected):
    assert "".join(decode_graphics_byte(value) for value in range(first, first+16)) == expected


def test_shortcut_dash_and_greek_keyboard_chart_use_real_native_glyphs():
    document = K602Reader().read_bytes(source())
    intro = next(topic for topic in document.topics if topic.context_id == 136)
    assert "spustit. Např. <Alt-S> otevře submenu [i]Soubor[/i]." in intro.uhf_content
    chart = next(topic for topic in document.topics if topic.context_id == 78)
    assert "         │Åå│Σσ│αδ│ΦΩ│Γ¤│Ňň│▀▄│æ█│Ĺĺ│┌└│┐┘│" in chart.uhf_content
    long_topic = next(topic for topic in document.topics if topic.context_id == 57)
    assert len(long_topic.uhf_content) == 4  # One stored long row is not three rows.
    assert long_topic.uhf_content[1].count(" ╯") == 2


def test_underline_selector_and_empty_spans_use_shared_uhf_rendering():
    data = help_file([records(b"Title", b"\x13under\x13 plain", b"\x02\x02", b"\x04next")])
    assert K602Reader().read_bytes(data).topics[0].uhf_content == [
        "Title", "[u]under[/u] plain", "", "[i]next[/i]",
    ]


@pytest.mark.parametrize("selector", [0x0F, 0x14, 0x16])
def test_unrepresented_cell_size_selectors_fail_instead_of_becoming_false_glyphs(selector):
    with pytest.raises(ValueError, match=f"K602 topic 0: Unsupported Software602 font-size selector {selector:02X}h"):
        K602Reader().read_bytes(help_file([records(b"Title", bytes([selector])+b"text")]))


def test_literal_uhf_tags_remain_text_and_index_stub_detection_does_not_strip_them():
    data = help_file([records(b"[b]Title[/b]", b"\x98\x98\x98")])
    document = K602Reader().read_bytes(data)
    assert document.topics[0].names == ["[b]Title[/b]"]
    assert document.topics[0].uhf_content == ["[[b]Title[[/b]", "▀▀▀"]
    # ensure_document_index may add a fallback when every topic is a stub.
    assert document.index_entries[0].label.decode() == "[b]Title[/b]"


def test_maximum_byte_row_length_is_counted_with_wider_arithmetic():
    document = K602Reader().read_bytes(help_file([records(b"x"*255)]))
    assert document.topics[0].uhf_content == ["x"*255]


def test_untranscribed_compound_key_glyphs_are_visible_cells_not_silent_deletions():
    assert decode_graphics_cells(b"a\0\1\3\x0e\x10b") == [(value, 0) for value in b"a\0\1\3\x0e\x10b"]
    assert "".join(decode_graphics_byte(value) for value in b"a\0\1\3\x0e\x10b") == "a" + "\uFFFD"*5 + "b"


@pytest.mark.parametrize("slot", [21, 125, 217, 255])
def test_original_bad_descriptor_never_becomes_a_shorter_successful_help(slot):
    with pytest.raises(ValueError, match="K602 topic table"):
        K602Reader().read_bytes(replace_entry(source(), slot, 1, 1))


@pytest.mark.parametrize("cut", [1, 10, 100])
def test_truncated_original_fails_even_if_declared_size_is_rewritten(cut):
    data = bytearray(source()[:-cut])
    struct.pack_into("<I", data, 11, len(data))
    with pytest.raises(ValueError, match="K602 topic table"):
        K602Reader().read_bytes(bytes(data))


def test_failed_real_staged_conversion_preserves_live_bundles_and_retry_works(tmp_path):
    original = source()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / "Software 602/K602.HLP"
    copy.parent.mkdir(parents=True)
    copy.write_bytes(original)
    kwargs = {"product_keys": ["software602"], "keep_products": ["software602"]}
    build_help_groups(["software602"], sources, helps, **kwargs)
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    damaged = replace_entry(original, 125, 1, 1)
    copy.write_bytes(damaged)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["software602"], sources, helps, **kwargs)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert copy.read_bytes() == damaged
    copy.write_bytes(original)
    result = build_help_groups(["software602"], sources, helps, **kwargs)
    assert result["bundles"] == 1 and result["backup"]
    backup = Path(result["backup"])
    assert published == {path.relative_to(backup): path.read_bytes() for path in backup.rglob("*") if path.is_file()}
