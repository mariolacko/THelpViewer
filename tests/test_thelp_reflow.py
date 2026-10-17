"""Sequential THELP uses byte words, not a border-derived table grammar."""
import gzip
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_thelp_reader import _screen


@pytest.mark.parametrize("lines,width,expected", [
    ([b"Hello world"], 10, [b"Hello ", b"world "]),
    ([b"Hello", b"world"], 76, [b"Hello world "]),
    ([b" Fixed", b"row"], 76, [b" Fixed", b"row "]),
    ([b"one  two   three"], 10, [b"one  two   ", b"three "]),
    ([b"one   "], 3, [b"one   "]),
    ([b"longindivisibleword", b"next"], 5, [b"longindivisibleword ", b"next "]),
    ([b"one", b"", b"two"], 76, [b"one ", b"", b"two "]),
    ([b"\2 alpha \2\xb3", b"\2 beta \2\xb3", b"\2 gamma \2\xb3"], 10,
     [b"\2 alpha \2\xb3 ", b"\2 beta \2\xb3 ", b"\2 gamma \2\xb3 "]),
    ([b"\2 alpha \2\xb3", b"\2 beta \2\xb3", b"\2 gamma \2\xb3"], 76,
     [b"\2 alpha \2\xb3 \2 beta \2\xb3 \2 gamma \2\xb3 "]),
    ([b"\5 Fixed", b"\5 end"], 10, [b"\5 Fixed \5 ", b"end "]),
    ([b"\5 Fixed", b"\5 end"], 76, [b"\5 Fixed \5 end "]),
    ([b"\3heart"], 76, [b"\3heart "]),
    ([b"hello\0world"], 76, [b"hello world "]),
    ([b"hello\0\0world"], 76, [b"hello ", b"", b"world "]),
])
def test_original_tp7_formatter_vectors(lines, width, expected):
    assert ThelpHelpReader._wrap_text_lines(lines, width) == expected


def test_zero_width_is_not_an_infinite_wrap_loop():
    with pytest.raises(ValueError, match="width"):
        ThelpHelpReader._wrap_text_lines([b"text"], 0)


def test_leading_literal_space_is_fixed_but_a_leading_control_is_not():
    rows = [b" Fixed long text", b"\5 Fixed long text\5", b"\tword word"]
    assert ThelpHelpReader._wrap_text_lines(rows, 10) == [
        b" Fixed long text", b"\5 Fixed ", b"long text\5 ", b"\tword word "]


def test_examples_are_projected_after_flow_and_the_parser_rows_are_not_mutated():
    screen = _screen(1, [b"\5code", b"continued\5", b" normal"])
    original = list(screen["lines"])
    topic = ThelpHelpReader._build_topics([screen], {"format_version": 52, "width": 20})[0]
    assert topic.raw_lines == [b"code continued ", b" normal"]
    assert topic.code_line_indices == {0}
    assert screen["lines"] == original


@pytest.mark.parametrize("version", [2, 4])
def test_legacy_positioned_rows_are_not_reflowed(version):
    rows = [b"First", b"Second"]
    screen = _screen(1, rows)
    screen["keywords_v4"] = [(2, 2, 1, 6, 0, 0, 0, 0)]
    topic = ThelpHelpReader._build_topics([screen], {"format_version": version, "width": 80})[0]
    assert topic.raw_lines == rows
    assert topic.positional_keywords[0].line == 2


def test_header_width_and_margin_bound_the_chosen_dos_viewport():
    screen = _screen(1, [b"alpha beta gamma"])
    assert ThelpHelpReader._build_topics([screen],
        {"format_version": 52, "width": 13, "left_margin": 3})[0].raw_lines == [b"alpha beta ", b"gamma "]


def test_hotspots_are_atomic_without_a_table_border_and_keep_native_target_order():
    screen = _screen(1, [b"prefix \2two words\2", b"\2another label\2", b" fixed"])
    screen["keywords_v5"] = [2, 3]
    document = ThelpHelpReader()._build_document({"format_version": 52, "width": 15},
        [screen, _screen(2, [b" A"]), _screen(3, [b" B"])], [], None)
    ThelpHelpReader.refresh_rendered_uhf_content(document, encoding="cp437")
    assert document.topics[0].sequential_keywords == [2, 3]
    assert document.topics[0].uhf_content == ["prefix ", "[link:topic=2]two words[/link] ",
        "[link:topic=3]another label[/link] ", " fixed"]


def test_large_words_and_fixed_rows_do_not_reproduce_native_buffer_overflow():
    keyword = b"\2" + b"word " * 1_000 + b"\2"
    fixed = b" " + b"fixed" * 1_000
    rows = [keyword] * 20 + [fixed]
    assert ThelpHelpReader._wrap_text_lines(rows, 76) == [keyword + b" "] * 20 + [fixed]


def test_flow_does_not_turn_a_referring_row_into_an_orphan_destination():
    screen = _screen(1, [b" heading", b"one", b"two", b"\2orphan\2", b" fixed"])
    screen["keywords_v5"] = [999]
    document = ThelpHelpReader()._build_document({"format_version": 52, "width": 76},
        [screen], [(b"orphan", 999)], None)
    ThelpHelpReader.refresh_rendered_uhf_content(document, encoding="cp437")
    entry = document.index_entries[0]
    assert (entry.context_id, entry.topic_id, entry.line) == (999, None, None)
    assert document.topics[0].uhf_content[1] == "one two [link:topic=999]orphan[/link] "


def test_original_cpp_table_uses_normal_word_flow_and_retains_all_42_targets():
    source = Path("var/sources/Borland C++ 3.0/TCHELP.TCH")
    data = source.read_bytes()
    _meta, screens, _, _ = ThelpBinaryParser(data).parse()
    original = next(s for s in screens if s["id"] == 2088)
    assert sum(b"\2" in row for row in original["lines"]) == 50
    document = ThelpHelpReader(source.name).read_bytes(data)
    topic = next(t for t in document.topics if t.context_id == 2088)
    assert topic.sequential_keywords == original["keywords_v5"]
    table_rows = [row for row in topic.raw_lines if row.count(b"\2") == 14]
    assert len(table_rows) == 6
    assert all(len(row.replace(b"\2", b"")) == 70 for row in table_rows)
    assert sum(row.count("[link:") for row in topic.uhf_content) == 50
    assert source.read_bytes() == data


def test_native_flow_reaches_canonical_bundle_without_changing_the_original(tmp_path):
    source = Path("var/sources/Borland C++ 3.0/TCHELP.TCH")
    data = source.read_bytes()
    result = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=[source], layout="helps")
    bundle = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    rows = bundle["topics"]["2088"]["content"]
    assert sum(row.count("[link:") == 7 for row in rows) == 6
    assert sum(row.count("[link:") for row in rows) == 50
    assert source.read_bytes() == data
