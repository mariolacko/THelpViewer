"""Sidekick 1 contexts/pages, native controls and strict malformed-file handling."""

import gzip
import json
from pathlib import Path
import re

import pytest

from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.readers.sidekick1 import Sidekick1Reader, is_sidekick1_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


SOURCE = Path("data/sources/Borland Sidekick 1.x current/SK.HLP")
REFERENCE = Path("data/sources/Borland Sidekick 1.56b/SK.HLP")
ZERO = b"\x01\x0c\x02Help text #0\x00"


def _context(text, rows=3, columns=40):
    return bytes((rows, columns)) + text + b"\x00"


def _sample(first=b"\x02General\x03\x02Continuation", *, tag=0x1234):
    return tag.to_bytes(2, "little") + ZERO + _context(first) + _context(b"\x02Other")


def test_detector_uses_structure_not_crc_version_filename_or_plain_text():
    data = _sample(tag=0xABCD)
    assert is_sidekick1_binary(data)
    assert detect_format_handler("UNKNOWN.BIN", data).name == "sidekick1"
    for invalid in (b"", data[2:], b"\0\0Sidekick\r\nHelp\r\n", data[:8], b"\x00\x9bBorland Help\0"):
        assert not is_sidekick1_binary(invalid)


def test_original_context_ids_and_continuation_navigation_do_not_collide():
    document = Sidekick1Reader(source_name="SK.HLP").read_bytes(_sample())
    assert [topic.context_id for topic in document.topics] == [0, 1, 3, 2]
    assert [entry.context_id for entry in document.index_entries] == [1, 2]
    assert document.contents[0].topic_id == 1
    assert document.contents[0].children[0].topic_id == 3
    first, continuation, other = document.topics[1:]
    assert first.next_context == 3 and continuation.prev_context == 1
    assert continuation.next_context is None and other.prev_context is None
    assert first.is_help_contents
    assert document.metadata["sidekick_version_tag"] == 0x1234
    descriptor = document.metadata["sidekick_contexts"][1]
    assert descriptor == {"context_id": 1, "offset": 18, "rows": 3, "columns": 40, "page_ids": [1, 3]}


def test_attribute_selection_replaces_roles_and_persists_across_lines_and_pages():
    document = Sidekick1Reader().read_bytes(_sample(b"\x01Bold\r\nstill\x04Key\x03Next\x02Normal"))
    assert document.topics[1].uhf_content == ["[b]Bold[/b]", "[b]still[/b][u]Key[/u]"]
    assert document.topics[2].uhf_content == ["[u]Next[/u]Normal"]
    assert document.topics[2].raw_lines == [b"NextNormal"]


def test_oem_arrows_and_literal_brackets_are_not_controls_or_source_links():
    document = Sidekick1Reader().read_bytes(_sample(
        b"\x02Keys \x04\x11\x18\x19\x1a\x1b\x02 [link:topic=99]\r\nSymbols: \x09 \x7f"))
    assert document.topics[1].uhf_content == ["Keys [u]◄↑↓→←[/u] [[link:topic=99]", "Symbols: ○ ⌂"]
    payload = HelpJsonRenderer(document).render_document()
    labels = [entry["label"] for group in payload["index"] for entry in group["entries"]]
    assert "Keys ◄↑↓→← [link:topic=99]" in labels
    assert payload["topics"]["1"]["content"] == document.topics[1].uhf_content


def test_empty_pages_and_authored_spaces_are_not_collapsed():
    document = Sidekick1Reader().read_bytes(_sample(b"\x02  Title  \x03\x03Final"))
    assert document.topics[1].raw_lines == [b"  Title  "]
    assert document.topics[2].uhf_content == [""]
    assert document.topics[3].uhf_content == ["Final"]
    assert document.metadata["sidekick_contexts"][1]["page_ids"] == [1, 3, 4]


def test_terminal_more_links_only_to_the_structural_continuation_and_preserves_layout():
    document = Sidekick1Reader().read_bytes(_sample(
        b"\x02Heading\r\n  \x01More..  \r\n \x03\x02Second\x03\x02Last"))
    first, second, last = document.topics[1:4]
    assert first.raw_lines == [b"Heading", b"  More..  ", b" "]
    assert first.uhf_content == [
        "Heading", "  [b][link:topic=3]More..[/link][/b][b]  [/b]", "[b] [/b]",
    ]
    assert first.next_context == 3 and second.next_context == 4
    assert second.uhf_content == ["Second"]  # Navigation does not invent a cue.
    assert last.next_context is None and last.uhf_content == ["Last"]


@pytest.mark.parametrize("body,linked", [
    (b"\x02Heading More..\x03Second", True),
    (b"\x02Heading More..", False),
    (b"\x02More..\r\nNot the last line\x03Second", False),
    (b"\x02More.. words\x03Second", False),
    (b"\x02SomeMore..\x03Second", False),
    (b"\x02more..\x03Second", False),
])
def test_more_is_a_terminal_presentation_cue_not_an_arbitrary_word_link(body, linked):
    document = Sidekick1Reader().read_bytes(_sample(body))
    assert any("[link:topic=" in line for line in document.topics[1].uhf_content) is linked


def test_eof_is_only_structural_at_a_context_boundary_and_stale_padding_is_ignored():
    original = _sample(b"\x02Arrow \x1a")
    padded = original + b"\x1a"
    padded += (b"OLD BUFFER TEXT" * 10)[:(-len(padded)) % 128]
    document = Sidekick1Reader().read_bytes(padded)
    assert len(document.topics) == 3
    assert document.topics[1].uhf_content == ["Arrow →"]
    assert all("OLD BUFFER" not in line for topic in document.topics for line in topic.uhf_content)
    assert len(Sidekick1Reader().read_bytes(original + b"\x1a").topics) == 3


def test_eof_marker_can_start_the_final_dos_record():
    # Context data plus its terminating NUL occupies exactly one 128-byte record.
    data = b"\x34\x12" + ZERO + _context(b"\x02" + b"Text" + b" " * 50 + b"\r\n" + b" " * 50,
                                            rows=2, columns=78)
    assert len(data) == 128
    assert len(Sidekick1Reader().read_bytes(data + b"\x1a" + b"x" * 127).topics) == 2


@pytest.mark.parametrize("data", [
    b"unknown", b"\x34\x12" + ZERO[:-1], b"\x34\x12" + ZERO + b"\x02",
    b"\x34\x12" + ZERO + _context(b"Text", rows=0),
    b"\x34\x12" + ZERO + _context(b"Text", rows=24),
    b"\x34\x12" + ZERO + _context(b"Text", columns=0),
    b"\x34\x12" + ZERO + _context(b"Text", columns=79),
    _sample()[:-1], _sample() + b"garbage", _sample() + b"\x1aunrounded garbage",
    _sample() + b"\x1a" + bytes(256), _sample() + bytes(65536),
])
def test_invalid_structure_fails_without_truncating_the_file(data):
    with pytest.raises(ValueError):
        Sidekick1Reader().read_bytes(data)


@pytest.mark.parametrize("body,rows,columns", [
    (b"Text\nMore", 3, 40), (b"Text\rMore", 3, 40), (b"Text\r", 3, 40),
    (b"Text\x08", 3, 40), (b"Text\xff", 3, 40),
    (b"Too wide", 2, 3), (b"First\r\nSecond", 1, 40),
])
def test_unsupported_cursor_or_overflow_layout_is_rejected_not_clipped(body, rows, columns):
    with pytest.raises(ValueError):
        Sidekick1Reader().read_bytes(b"\x34\x12" + ZERO + _context(body, rows, columns))


def test_corpus_preserves_every_context_page_and_structural_boundary():
    if not SOURCE.is_file():
        pytest.skip("Sidekick 1 original not available")
    data = SOURCE.read_bytes()
    document = load_document(SOURCE)
    assert document.format_name == "sidekick1"
    descriptors = document.metadata["sidekick_contexts"]
    assert len(descriptors) == 67 and len(document.topics) == 148
    assert document.metadata["sidekick_version_tag"] == 0x5DEB
    assert len(document.index_entries) == len(document.contents) == 66
    assert descriptors[1]["page_ids"] == [1, *range(67, 81)]
    assert descriptors[2]["page_ids"] == [2, *range(81, 91)]
    assert descriptors[-1] == {"context_id": 66, "offset": 42016, "rows": 3, "columns": 50, "page_ids": [66]}
    assert all(data[item["offset"]:item["offset"] + 2] == bytes((item["rows"], item["columns"]))
               for item in descriptors)
    assert sum(len(item["page_ids"]) for item in descriptors) == len(document.topics)
    assert not is_sidekick1_binary(Path("data/sources/Borland Sidekick Plus/SKPLUS.HLP").read_bytes())
    for item in descriptors:
        assert len(item["page_ids"]) == data[item["offset"] + 2:data.index(b"\0", item["offset"] + 2)].count(b"\3") + 1
    payload = HelpJsonRenderer(document).render_document()
    assert payload["metadata"]["source"]["format"] == "sidekick1"
    more_links = []
    for topic in payload["topics"].values():
        assert all(str(target["topic_id"]) in payload["topics"] for target in topic.get("nav", {}).values())
        assert all("�" not in line and not any(ord(char) < 32 for char in line) for line in topic["content"])
        for line in topic["content"]:
            for target in re.findall(r"\[link:topic=(\d+)\]More\.\.\[/link\]", line):
                assert int(target) == topic["nav"]["Next"]["topic_id"]
                more_links.append(target)
    assert len(more_links) == 80
    first_wordstar = payload["topics"]["2"]
    assert "[link:topic=81]More..[/link]" in first_wordstar["content"][-1]


def test_second_runtime_original_uses_the_same_reader_without_version_special_cases():
    if not REFERENCE.is_file():
        pytest.skip("Independent Sidekick 1.56b runtime sample not available")
    document = load_document(REFERENCE)
    assert len(document.topics) == 179
    assert len(document.metadata["sidekick_contexts"]) == 72
    assert document.metadata["sidekick_version_tag"] == 0x2BE4
    assert document.metadata["sidekick_contexts"][-1]["page_ids"] == [71, 178]


def test_export_registers_original_filename_and_real_page_count_in_catalog(tmp_path):
    if not SOURCE.is_file():
        pytest.skip("Sidekick 1 original not available")
    before = SOURCE.read_bytes()
    results = export_bundle_tree(Path("data/sources"), tmp_path / "helps", source_paths=[SOURCE], layout="helps")
    assert len(results) == 1 and results[0].topic_count == 148
    catalog = json.loads((tmp_path / "helps" / "catalog.json").read_text())
    assert catalog[0]["product"] == "sk"
    assert catalog[0]["source_files"] == ["SK.HLP"]
    assert catalog[0]["name"] == "Sidekick Help System"
    bundle = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    assert catalog[0]["topics"] == len(bundle["topics"]) == 148
    assert len(bundle["metadata"]["sidekick_contexts"]) == 67
    assert bundle["metadata"]["help_contents_topic_id"] == 1
    assert SOURCE.read_bytes() == before
