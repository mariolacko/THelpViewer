"""Original M602 raw-byte wrap and screen-cell/hotspot vectors."""
import hashlib
import json

import pytest

from thelpviewer.server.converter.readers.m602 import M602BinaryParser, M602Reader
from thelpviewer.server.converter.readers.m602 import decode_m602_bytes
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from test_m602_validation import help_file, records, source, title


def parse(rows, width=78):
    return M602BinaryParser(help_file([records(*rows)]), width=width).parse()[0]


def spans(topic):
    return [(int.from_bytes(k.target_context.to_bytes(2, "little"), "big"),
             k.line, k.first_column, k.last_column) for k in topic["positional_keywords"]]


@pytest.mark.parametrize("width,expected,link_row", [
    (10, [b" Title \xdc", b" \xdf\xdf\xdf", b"one two ", b"three ",
          b"four five ", b"six", b" ", b"Linked label"], 8),
    (40, [b" Title \xdc", b" \xdf\xdf\xdf", b"one two three four five six", b" ", b"Linked label"], 5),
    (78, [b" Title \xdc", b" \xdf\xdf\xdf", b"one two three four five six", b" ", b"Linked label"], 5),
])
def test_original_native_wrap_title_rule_blank_and_link_vectors(width, expected, link_row):
    # Original 89A2Bh..89B44h, 894E3h split, 8959Dh links, 89770h output.
    topic = parse([title(b"Title "), b"\x01\xdf\xdf\xdf\r", b"one two three\r",
                   b"four five six\r", b"\x01\r", b"\x02Linked_label\x02\0\x0a\r"], width)
    assert topic["raw_lines"] == expected
    assert spans(topic) == [(10, link_row, 1, 12)]


def test_wrap_counts_encoded_link_bytes_before_removing_operands_and_spaces():
    topic = parse([b"one \x02two_three\x02\0\x0a\r", b"four five\r"], 15)
    assert topic["raw_lines"] == [b"one ", b"two three ", b"four five"]
    assert spans(topic) == [(10, 2, 1, 9)]


def test_hard_rows_and_last_unjoined_soft_record_do_not_wrap():
    topic = parse([b"\x01hard long row\r", b"last long row\r"], 5)
    assert topic["raw_lines"] == [b" hard long row", b"last long row"]


def test_spaces_are_not_collapsed_and_wrap_retains_the_cut_space():
    topic = parse([b"one  \r", b"two three\r"], 6)
    assert topic["raw_lines"] == [b"one   ", b"two ", b"three"]


def test_unbroken_long_word_is_not_truncated_or_force_split():
    topic = parse([b"longword\r", b"tail\r"], 4)
    assert topic["raw_lines"] == [b"longword ", b"tail"]


def test_adjacent_identical_targets_keep_separate_source_hotspots():
    topic = parse([b"\x02A\x02\0\x0a\x02B\x02\0\x0a\r"])
    assert topic["raw_lines"] == [b"AB"]
    assert topic["raw_link_targets"] == [0x0A00, 0x0A00]
    assert spans(topic) == [(10, 1, 1, 1), (10, 1, 2, 2)]


def test_literal_internal_cr_and_oem_cells_do_not_move_rows_or_disappear():
    data = help_file([records(b"\x01A\r\0\t\n\x7fB\r")])
    document = M602Reader().read_bytes(data)
    assert document.topics[0].raw_lines == [b" A\r\0\t\n\x7fB"]
    assert document.topics[0].uhf_content == [" A♪ ○◙⌂B"]


def test_only_one_terminal_cr_is_removed_and_hard_marker_is_only_leading():
    topic = parse([b"\x01A\r\r", b"\x01\x01B\r"])
    assert topic["raw_lines"] == [b" A\r", b" \x01B"]


def test_hard_marker_replacement_is_after_wrapping_and_hotspot_removal():
    assert parse([b"word \x01body\r", b"next\r"], 5)["raw_lines"] == [b"word ", b" body ", b"next"]
    topic = parse([b"\x02\x01label\x02\0\x0a\r"])
    assert topic["raw_lines"] == [b" label"]
    assert spans(topic) == [(10, 1, 1, 6)]


def test_wrapped_label_fragments_keep_the_original_target_without_reading_past_the_row():
    topic = parse([b"\x02two three\x02\0\x0a\r", b"tail\r"], 6)
    assert topic["raw_lines"] == [b"two ", b"three ", b"tail"]
    assert spans(topic) == [(10, 1, 1, 4), (10, 2, 1, 5)]


def test_safe_buffers_retain_source_beyond_the_original_short_string_concat_limit():
    topic = parse([b"A" * 254 + b"\r", b"tail\r"], 78)
    assert topic["raw_lines"] == [b"A" * 254 + b" ", b"tail"]


@pytest.mark.parametrize("row,message", [(b"", "zero-length"), (b"bad", "CR terminator")])
def test_unverified_or_missing_record_terminators_fail_explicitly(row, message):
    with pytest.raises(ValueError, match=message):
        M602Reader().read_bytes(help_file([records(row)]))


@pytest.mark.parametrize("width", [0, -1, 256, None, "78"])
def test_invalid_projection_width_fails(width):
    with pytest.raises(ValueError, match="display width"):
        parse([b"row\r"], width)


def test_all_original_rows_and_hotspots_match_independent_bounded_native_execution():
    topics = M602BinaryParser(source()).parse()
    rows = [(topic["context_id"], i, row.hex()) for topic in topics
            for i, row in enumerate(topic["raw_lines"], 1)]
    links = [(topic["context_id"], *span) for topic in topics for span in spans(topic)]
    assert len(rows) == 3012 and len(links) == 406
    # Native M602X.EXE SHA256 d4ab0fc6...; no HELP logic in the heap shim.
    for trace, digest in [(rows, "2cc0dc638d5f302b3708d2ec4bb8ade522d1badf9e1dae3c0d756bde69b2fd2d"),
                          (links, "55d216d03aeb878eed01eb81141b54a01c7ec4c3f28ff9b9f7fe482452f66699")]:
        assert hashlib.sha256((json.dumps(trace, separators=(",", ":")) + "\n").encode()).hexdigest() == digest


def test_shared_uhf_renderer_preserves_every_native_display_cell_and_czech_title():
    import re
    document = M602Reader().read_bytes(source())
    payload = HelpJsonRenderer(document, display_encoding="kamenicky").render_document()
    assert payload["topics"]["2"]["title"] == "Základní obrazovka"
    for topic in document.topics:
        content = payload["topics"][str(topic.context_id)]["content"]
        assert len(content) == len(topic.raw_lines)
        for rendered, row in zip(content, topic.raw_lines):
            visible = re.sub(r"\[link:[^\]]*\]|\[/link\]", "", rendered.replace("[[", "\ue000"))
            assert visible.replace("\ue000", "[") == decode_m602_bytes(row, "kamenicky")
