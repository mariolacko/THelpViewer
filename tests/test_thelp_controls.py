"""Native Turbo Example toggles are ^E, not arbitrary OEM glyphs."""

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader, is_thelp_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_thelp_reader import _screen
from thelp_corpus import original_thelp_corpus


@pytest.mark.parametrize("raw,visible,codes", [
    ([b" \5#include <stdio.h>", b"  return 0;", b" } \5", b" tail"],
     [b" #include <stdio.h>", b"  return 0;", b" } ", b" tail"], {0, 1, 2}),
    ([b"\5", b"  code", b"", b"\5", b"after"], [b"", b"  code", b"", b"", b"after"], {0, 1, 2}),
    ([b"\5\5", b"text"], [b"", b"text"], set()),
    ([b"\5 \5", b"text"], [b" ", b"text"], {0}),
    ([b"before \5code\5 after", b"text"], [b"before code after", b"text"], {0}),
    ([b"\5code", b"\5\5", b"continued\5", b"after"], [b"code", b"", b"continued", b"after"], {0, 1, 2}),
    ([b"\5", b"code", b"\x10\5", b"after"], [b"", b"code", b"\x10", b"after"], {0, 1, 2}),
    ([b"\t \5  code\t\5  "], [b"\t   code\t  "], {0}),
])
def test_each_toggle_keeps_rows_bytes_indentation_and_closing_inline_text(raw, visible, codes):
    assert ThelpHelpReader._extract_code_lines(raw) == (visible, codes)


@pytest.mark.parametrize("glyph", [3, 16])
@pytest.mark.parametrize("prefix", [b"", b"   ", b"\t"])
def test_heart_and_triangle_do_not_start_or_end_an_example(glyph, prefix):
    rows = [prefix + bytes([glyph]), prefix + bytes([glyph]) + b" caption", b"following row"]
    assert ThelpHelpReader._extract_code_lines(rows) == (rows, set())
    rows = [b"\5code", *rows, b"\5", b"normal"]
    visible, codes = ThelpHelpReader._extract_code_lines(rows)
    assert visible == [b"code", *rows[1:4], b"", b"normal"]
    assert codes == {0, 1, 2, 3}


def test_native_markers_override_heading_and_pascal_filename_heuristics():
    screen = _screen(1, [b"SAMPLE.PAS", b"----", b"\5code\5", b"not part of the example"])
    topic = ThelpHelpReader._build_topics([screen], {})[0]
    assert topic.raw_lines == [b"SAMPLE.PAS", b"----", b"code", b"not part of the example"]
    assert topic.code_line_indices == {2}


def test_legacy_example_heading_still_uses_only_the_existing_optional_heuristic():
    rows = [b" Example:", b"  code", b" See Also:", b" reference"]
    assert ThelpHelpReader._extract_code_lines(rows) == (rows, set())
    assert ThelpHelpReader._extract_code_lines(rows, use_example_heuristic=True) == (rows, {1})


def test_marker_only_rows_do_not_shift_positioned_hotspots():
    screen = _screen(1, [b"\5", b" code", b"\5", b"Link"])
    screen["keywords_v4"] = [(2, 4, 1, 4, 0, 0, 0, 0)]
    document = ThelpHelpReader()._build_document({}, [screen, _screen(2, [b"Target"])], [], None)
    ThelpHelpReader.refresh_rendered_uhf_content(document, encoding="cp437")
    assert document.topics[0].raw_lines == [b"", b" code", b"", b"Link"]
    assert document.topics[0].uhf_content[-1] == "[link:topic=2]Link[/link]"


def test_code_state_follows_page_links_and_aliases_not_physical_record_order():
    first = _screen(11, [b"First", b"\5code"])
    second = _screen(22, [b"continued", b"\5", b"normal"])
    third = _screen(33, [b"unrelated"])
    first["link_down"] = 23
    second["alias_ids"] = [23]
    second["link_up"] = 11
    topics = ThelpHelpReader._build_topics([second, third, first], {})
    assert [topic.code_line_indices for topic in topics] == [{0}, set(), {1}]
    assert topics[0].raw_lines == [b"continued", b"", b"normal"]


def test_multi_page_toggle_parity_and_closed_example_do_not_leak_to_later_pages():
    screens = [_screen(11, [b"\5start"]), _screen(22, [b"\5normal\5", b"code"]),
               _screen(33, [b"end\5", b"normal"]), _screen(44, [b"normal"])]
    for first, second in zip(screens, screens[1:]):
        first["link_down"] = second["id"]
        second["link_up"] = first["id"]
    assert ThelpHelpReader._example_entry_states(screens) == [False, True, True, False]


def test_missing_nonreciprocal_and_zero_links_do_not_invent_a_predecessor():
    first = _screen(0, [b"\5start"])
    second = _screen(2, [b"normal"])
    first["link_down"] = 2
    second["link_up"] = 0  # Native end sentinel, even when context zero exists.
    assert ThelpHelpReader._example_entry_states([first, second]) == [False, False]
    first["id"], second["link_up"] = 1, 1
    first["link_down"] = 3
    assert ThelpHelpReader._example_entry_states([first, second]) == [False, False]
    second["link_up"] = 99
    assert ThelpHelpReader._example_entry_states([first, second]) == [False, False]
    first["link_down"], second["id"], second["link_up"] = 0, 0, 1
    assert ThelpHelpReader._example_entry_states([first, second]) == [False, False]


def test_cycles_have_no_guessed_entry_state_and_long_chains_do_not_recurse():
    first = _screen(1, [b"\5"])
    second = _screen(2, [b"\5"])
    first["link_up"], first["link_down"] = 2, 2
    second["link_up"], second["link_down"] = 1, 1
    assert ThelpHelpReader._example_entry_states([first, second]) == [False, False]
    screens = [_screen(i + 1, [b"\5"] if i == 0 else [b"continued"]) for i in range(2_000)]
    for first, second in zip(screens, screens[1:]):
        first["link_down"] = second["id"]
        second["link_up"] = first["id"]
    assert ThelpHelpReader._example_entry_states(list(reversed(screens))) == [True] * 1_999 + [False]


def test_real_czech_menu_arrow_preserves_its_cell_and_is_not_a_code_toggle():
    source = Path("var/sources/Borland Turbo Pascal 7 (CZ)/TURBO.TPH")
    document = ThelpHelpReader().read_path(source)
    topic = next(topic for topic in document.topics if topic.context_id == 434)
    assert any(row.startswith(b"    \x10    \xb3") for row in topic.raw_lines)
    assert not topic.code_line_indices
    assert any(line.startswith("    ►    │") for line in topic.uhf_content)


def test_real_puts_inline_closing_toggle_does_not_remain_as_a_club():
    source = Path("var/sources/Borland C++ 2.0 DOS current/TCHELP.TCH")
    document = ThelpHelpReader().read_path(source)
    topic = next(topic for topic in document.topics if topic.context_id == 1388)
    start = topic.raw_lines.index(b" #include <stdio.h>")
    assert topic.raw_lines[start + 8] == b" } "
    assert topic.code_line_indices == set(range(start, start + 9))
    assert not any(b"\5" in line for line in topic.raw_lines)
    assert "♣" not in "\n".join(topic.uhf_content)


def test_arrow_and_native_source_rows_reach_the_bundle_without_modifying_source(tmp_path):
    source = Path("var/sources/Borland Turbo Pascal 7 (CZ)/TURBO.TPH")
    original = source.read_bytes()
    result = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=[source], layout="helps")
    payload = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    assert any(line.startswith("    ►    │") for line in payload["topics"]["434"]["content"])
    assert all("[code]" not in line for line in payload["topics"]["434"]["content"])
    assert source.read_bytes() == original


def test_all_physical_rows_match_the_independent_boa_toggle_reference():
    # Reference is a standalone C implementation of BOA's byte-toggle rule,
    # not a DOS GUI capture or a per-cell styled shared-model representation.
    digest = hashlib.sha256()
    files = records = rows = code_rows = inherited_pages = 0
    root = Path("var/sources")
    for source, data in original_thelp_corpus():
        assert is_thelp_binary(data)
        files += 1
        name = source.relative_to(root).as_posix()
        _meta, screens, _index, _tags = ThelpBinaryParser(data).parse()
        entries = ThelpHelpReader._example_entry_states(screens)
        for ordinal, (screen, entry) in enumerate(zip(screens, entries)):
            visible, codes = ThelpHelpReader._extract_code_lines(screen["lines"], initial_code_state=entry)
            digest.update(json.dumps((name, ordinal, [line.hex() for line in visible], sorted(codes)),
                                     separators=(",", ":")).encode() + b"\n")
            records += 1
            rows += len(visible)
            code_rows += len(codes)
            inherited_pages += entry
    assert (files, records, rows, code_rows, inherited_pages) == (66, 93_142, 2_212_161, 201_770, 0)
    assert digest.hexdigest() == "743ec4c968003e0f25c55d6784032fe72a6dcbbd79f22cffc471f8e7e6c51228"
