"""Native M602 directory ranges, complete records and exact link destinations."""

import hashlib
import json
from pathlib import Path
import re
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.m602 import (
    M602_HEADER, M602_ERROR_TARGET, M602BinaryParser, M602Reader,
    build_m602_binary_target_context_map,
)
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


ORIGINAL = Path("var/sources/Software 602/M602_200.HLP")


def source():
    if not ORIGINAL.is_file():
        pytest.skip("Original M602 HELP is not installed")
    return ORIGINAL.read_bytes()


def records(*rows):
    return bytes(value ^ 0xFA for row in rows for value in bytes([len(row)]) + row)


def title(text):
    return b"\x01" + text + b"\xdc\r"


def help_file(blocks, targets=None, order=None):
    targets = targets if targets is not None else list(range(len(blocks)))
    body = b"".join(blocks)
    offset = len(M602_HEADER)
    entries = []
    for target, block in zip(targets, blocks):
        entries.append(target.to_bytes(2, "big") + struct.pack("<IH", offset, len(block)))
        offset += len(block)
    table = b"".join(entries[i] for i in (order if order is not None else range(len(entries))))
    eof = len(M602_HEADER) + len(body) + len(table) + 6
    return M602_HEADER + body + table + struct.pack("<HI", len(entries), eof)


def change_entry(data, index, *, target=None, offset=None, size=None):
    changed = bytearray(data)
    count = int.from_bytes(data[-6:-4], "little")
    start = len(data) - 6 - count * 8 + index * 8
    if target is not None:
        changed[start:start+2] = target.to_bytes(2, "big")
    if offset is not None:
        struct.pack_into("<I", changed, start+2, offset)
    if size is not None:
        struct.pack_into("<H", changed, start+6, size)
    return bytes(changed)


def test_first_directory_row_is_a_real_context_not_an_index_header():
    data = help_file([records(title(b"First")), records(title(b"Second"))], [0xFFFF, 0x1234])
    parser = M602BinaryParser(data)
    topics = parser.parse()
    assert build_m602_binary_target_context_map(data, topics) == {0xFFFF: 1, 0x1234: 2}
    assert topics[-1]["end_offset"] == parser.binary_index_offset
    assert parser.binary_index_entry_count == 2


def test_directory_order_is_not_topic_order_and_sizes_are_not_offset_deltas():
    data = help_file([records(title(b"First"), b"a\r"), records(title(b"Second"), b"longer\r")],
                     [0xDC01, 0xDF02], order=[1, 0])
    parser = M602BinaryParser(data)
    topics = parser.parse()
    assert [topic["title"] for topic in topics] == [b"First", b"Second"]
    assert build_m602_binary_target_context_map(data, topics) == {0xDF02: 2, 0xDC01: 1}


def test_two_contexts_can_share_a_topic_and_native_duplicate_lookup_uses_first_match():
    data = help_file([records(title(b"One")), records(title(b"Two"))], [0x1234, 0x5678])
    first = M602BinaryParser(data).index_entries[0]
    shared = change_entry(data, 1, offset=first.offset, size=first.size)
    parser = M602BinaryParser(shared)
    topics = parser.parse()
    assert len(topics) == 1
    assert build_m602_binary_target_context_map(shared, topics) == {0x1234: 1, 0x5678: 1}
    duplicate = change_entry(data, 1, target=0x1234)
    parser = M602BinaryParser(duplicate)
    assert build_m602_binary_target_context_map(duplicate, parser.parse()) == {0x1234: 1}


def test_empty_directory_and_zero_byte_topics_are_not_truncation():
    assert M602Reader().read_bytes(help_file([])).topics == []
    data = help_file([b"", records(title(b"Second"))], [0xFFFF, 0])
    document = M602Reader().read_bytes(data)
    assert [topic.context_id for topic in document.topics] == [1, 2]
    assert document.topics[0].uhf_content == []


def test_gaps_between_native_ranges_do_not_become_text_records():
    first, second = records(title(b"First")), records(title(b"Second"))
    data = help_file([first + b"\x10garbage", second])
    data = change_entry(data, 0, size=len(first))
    document = M602Reader().read_bytes(data)
    assert [topic.uhf_content for topic in document.topics] == [[" First▄"], [" Second▄"]]


def test_body_title_terminators_and_link_operands_do_not_start_another_topic():
    row = b"\x01text \x02link\x02\x01\xdc\r"
    data = help_file([records(title(b"First"), row, b"\x01not a title\xdc\r"), records(title(b"Second"))],
                     [0, 0xDC01])
    document = M602Reader().read_bytes(data)
    assert len(document.topics) == 2
    assert document.topics[0].uhf_content[1:] == [" text [link:topic=2]link[/link]", " not a title▄"]


@pytest.mark.parametrize("target", [0xDF01, 0xDC01, 0x0D01, 0x0D0D, 0x0201])
def test_target_bytes_are_not_line_markers_separators_or_cr_terminators(target):
    row = b"\x01prefix \x02Second\x02" + target.to_bytes(2, "little") + b"\r"
    data = help_file([records(title(b"First"), row), records(title(b"Second"))], [0, target])
    assert M602Reader().read_bytes(data).topics[0].uhf_content[1] == " prefix [link:topic=2]Second[/link]"


def test_valid_fa_glyphs_cannot_trigger_a_binary_tail_density_guess():
    data = help_file([records(title(b"First"), b"\xfa" * 100 + b"\r", b"after\r")])
    document = M602Reader().read_bytes(data)
    assert len(document.topics[0].uhf_content) == 3
    assert document.topics[0].uhf_content[-1] == "after"


def test_hotspot_padding_and_underscores_keep_native_display_columns():
    data = help_file([records(title(b"First"), b"\x02Second____\x02\x01\0 after\r"),
                      records(title(b"Second"))], [0, 1])
    assert M602Reader().read_bytes(data).topics[0].uhf_content[1] == "[link:topic=2]Second    [/link] after"


def test_unknown_target_uses_original_9999_error_context_not_a_similar_title():
    row = b"\x02Second\x02\x02\0\r"  # Raw target 2 also coincides with an output ordinal.
    data = help_file([records(title(b"Error")), records(title(b"Second"), row)], [M602_ERROR_TARGET, 0x1234])
    document = M602Reader().read_bytes(data)
    assert document.topics[1].uhf_content[1] == "[link:topic=1]Second[/link]"
    assert document.metadata["missing_raw_link_targets"] == [2]
    assert document.metadata["link_target_resolution"] == "binary_index_error_context"


def test_absent_target_without_error_context_is_not_guessed_from_title_or_output_id():
    data = help_file([records(title(b"First"), b"\x02Second\x02\x02\0\r"),
                      records(title(b"Second"))], [0, 0x1234])
    with pytest.raises(ValueError, match="absent target 0002h"):
        M602Reader().read_bytes(data)


@pytest.mark.parametrize("row,message", [
    (b"\x02unclosed\r", "unterminated hyperlink"),
    (b"\x02closed\x02\r", "truncated hyperlink target"),
    (b"\x02closed\x02\x01\r", "truncated hyperlink target"),
])
def test_incomplete_links_fail_without_dropping_their_text(row, message):
    with pytest.raises(ValueError, match=message):
        M602Reader().read_bytes(help_file([records(title(b"First"), row)]))


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("offset,size", [(1, 1), (999999, 0), (27, 65535)])
def test_bad_directory_ranges_fail_instead_of_guessing_a_link(index, offset, size):
    data = help_file([records(title(b"First")), records(title(b"Second")), records(title(b"Third"))])
    with pytest.raises(ValueError, match="invalid topic range"):
        M602Reader().read_bytes(change_entry(data, index, offset=offset, size=size))


def test_record_cannot_borrow_bytes_from_the_next_topic_or_index():
    for blocks in ([b"\x00", records(title(b"Next"))], [b"\x00"]):  # Decoded length 250.
        with pytest.raises(ValueError, match="truncated record"):
            M602Reader().read_bytes(help_file(blocks))


@pytest.mark.parametrize("cut", [1, 2, 4, 6, 8, 30, 100])
def test_truncated_original_never_becomes_a_shorter_successful_help(cut):
    with pytest.raises(ValueError):
        M602Reader().read_bytes(source()[:-cut])


@pytest.mark.parametrize("length", [0, 1, 26, 27, 28, 30, 32])
def test_incomplete_header_or_footer_fails(length):
    with pytest.raises(ValueError):
        M602BinaryParser(help_file([])[:length])


def test_footer_count_and_eof_are_checked_and_supplied_tail_cannot_override_them():
    data = bytearray(help_file([records(title(b"First"))]))
    struct.pack_into("<H", data, len(data)-6, 65535)
    with pytest.raises(ValueError, match="count exceeds"):
        M602Reader().read_bytes(bytes(data))
    data = help_file([records(title(b"First"))])
    parser = M602BinaryParser(data)
    with pytest.raises(ValueError, match="disagrees"):
        build_m602_binary_target_context_map(data, parser.parse(), tail_offset=0)


def test_original_directory_matches_bounded_original_lookup_execution():
    data = source()
    assert hashlib.sha256(data).hexdigest() == "68400f18501288affa7cf7138e111cf70a67aacd0ba8fad8b64d7407f2676e99"
    parser = M602BinaryParser(data)
    trace = [(int.from_bytes(entry.raw_target.to_bytes(2, "big"), "little"), entry.offset, entry.size)
             for entry in parser.index_entries]
    # M602X.EXE 89121h–891AFh execution: all 201 native context WORDs
    # select their own directory slots; an absent context selects 9999.
    assert hashlib.sha256(json.dumps(trace, separators=(",", ":")).encode()).hexdigest() == (
        "e6caa3c3b96b36f5b3df75634ebf95af2257a5e69d8158118826a2a28caab836")
    topics = parser.parse()
    targets = build_m602_binary_target_context_map(data, topics)
    assert len(topics) == len(targets) == 201
    assert targets[M602_ERROR_TARGET] == 1
    assert topics[-1]["end_offset"] == parser.binary_index_offset
    assert topics[-1]["end_offset"] - topics[-1]["start_offset"] == 158
    assert M602Reader().read_bytes(data).metadata["missing_raw_link_targets"] == []


def test_original_titles_index_and_native_link_destinations_are_retained():
    document = M602Reader(source_name=ORIGINAL.name).read_bytes(source())
    payload = HelpJsonRenderer(document, display_encoding="kamenicky").render_document()
    parser = M602BinaryParser(source())
    topics = parser.parse()
    targets = build_m602_binary_target_context_map(source(), topics)
    assert set(payload["topics"]) == {str(i) for i in range(1, 202)}
    assert payload["topics"]["2"]["title"] == "Základní obrazovka"
    assert payload["topics"]["2"]["content"][0] == " Základní obrazovka ▄"
    assert payload["metadata"]["display"] == {"cols": 78}
    assert [t.context_id for t in document.topics] == [entry.context_id for entry in document.index_entries]
    assert [k.target_context for t in document.topics for k in t.positional_keywords] == [
        targets[raw] for topic in topics for raw in topic["raw_link_targets"]]
    assert sum(row.count("[link:topic=") for t in document.topics for row in t.uhf_content) == 406


def test_failed_real_staged_conversion_preserves_publication_and_retry_works(tmp_path):
    original = source()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / "Software 602/M602_200.HLP"
    copy.parent.mkdir(parents=True)
    copy.write_bytes(original)
    kwargs = {"product_keys": ["software602"], "keep_products": ["software602"]}
    build_help_groups(["software602"], sources, helps, **kwargs)
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    copy.write_bytes(change_entry(original, 100, size=65535))
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["software602"], sources, helps, **kwargs)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    copy.write_bytes(original)
    result = build_help_groups(["software602"], sources, helps, **kwargs)
    backup = Path(result["backup"])
    assert result["bundles"] == 1
    assert published == {path.relative_to(backup): path.read_bytes() for path in backup.rglob("*") if path.is_file()}
