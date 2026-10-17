"""TBH word records, independently verified against the original TB.EXE."""

import hashlib
import json
from pathlib import Path
import struct
import zlib

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.readers.thelp import is_thelp_binary
from thelpviewer.server.converter.readers.turbo_basic import (
    TURBO_BASIC_PREFIX, TurboBasicHelpReader, is_turbo_basic_binary, text_rows,
)


def _record(kind, data):
    return struct.pack("<HH", kind, len(data)) + data


def _sample(packing=1):
    header = TURBO_BASIC_PREFIX + b"\1\1" + _record(0, struct.pack("<5H", 0, 0, 15, 48, packing))
    offset = len(header) + 4 + 2 + 6 * 2
    text = b"First\0A\xfe\3B\0" if packing else b"First\0A   B\0"
    page = _record(3, text)
    target = offset + len(page) + 4 + 2 + 12
    # Keyword length excludes its count WORD, unlike the context record.
    links = struct.pack("<HHH8BI", 4, 12, 1, 1, 1, 5, 0, 0, 0, 0, 0, target)
    contexts = _record(2, struct.pack("<HHIHI", 2, 0, offset, 1, offset))
    return header + contexts + page + links + _record(3, b"Next\0") + struct.pack("<HHH", 4, 0, 0)


@pytest.mark.parametrize("packing", [0, 1])
def test_word_records_absolute_links_aliases_and_unmapped_continuations(packing):
    data = _sample(packing)
    assert is_turbo_basic_binary(data) and not is_thelp_binary(data)
    assert detect_format_handler("renamed.tbh", data).name == "turbo-basic"
    document = TurboBasicHelpReader().read_bytes(data)
    first, second = document.topics
    assert first.context_id == 0 and first.alias_contexts == [1]
    assert second.context_id == 0x10001
    assert first.raw_lines == [b"First", b"A   B"] and second.raw_lines == [b"Next"]
    link, = first.positional_keywords
    assert (link.target_context, link.line, link.first_column, link.last_column) == (second.context_id, 1, 1, 5)
    assert f"[link:topic={second.context_id}]First[/link]" in first.uhf_content[0]
    assert document.metadata["space_packing"] == packing


@pytest.mark.parametrize("packed,raw,expected", [
    (True, b"A\xfe\0B\0", [b"AB"]),
    (True, b"A\xfe\3B\0", [b"A   B"]),
    (True, b"\xfe\xff\0", [b" " * 255]),
    (False, b"A\xfe\3B\0", [b"A\xfe\3B"]),
    (False, b"A\xfe\0B\0", [b"A\xfe", b"B"]),
    (True, b"A\1B\0\0C\0", [b"AB", b"", b"C"]),
    (False, b"A\xffB\0", [b"A\xffB"]),
    (True, b"A\xffB\0", [b"A\xffB"]),
])
def test_native_text_alphabet_space_runs_and_blank_rows(packed, raw, expected):
    # Injected into TB.EXE's original renderer as well as the physical corpus.
    assert text_rows(raw, packed) == expected


@pytest.mark.parametrize("raw", [b"\xfe", b"text", b"text\0partial"])
def test_incomplete_text_is_not_silently_published(raw):
    with pytest.raises(ValueError):
        text_rows(raw, True)


def test_every_truncation_is_bounded_and_rejected():
    data = _sample()
    for cut in range(len(data)):
        with pytest.raises(ValueError):
            TurboBasicHelpReader().read_bytes(data[:cut])


@pytest.mark.parametrize("damage", ["version", "mode", "context-size", "context-offset",
                                   "keyword-size", "keyword-offset", "keyword-cells", "record-type"])
def test_invalid_headers_lengths_and_non_record_targets_are_rejected(damage):
    data = bytearray(_sample())
    first = len(TURBO_BASIC_PREFIX) + 2
    contexts = first + 14
    text = contexts + 18
    keywords = text + 4 + len(b"First\0A\xfe\3B\0")
    match damage:
        case "version": data[len(TURBO_BASIC_PREFIX)] = 2
        case "mode": struct.pack_into("<H", data, first + 12, 2)
        case "context-size": struct.pack_into("<H", data, contexts + 2, 13)
        case "context-offset": struct.pack_into("<I", data, contexts + 8, text + 1)
        case "keyword-size": struct.pack_into("<H", data, keywords + 2, 11)
        case "keyword-offset": struct.pack_into("<I", data, keywords + 14, text + 1)
        case "keyword-cells": data[keywords + 7] = 0
        case "record-type": struct.pack_into("<H", data, text, 5)
    with pytest.raises(ValueError):
        TurboBasicHelpReader().read_bytes(bytes(data))


def test_failed_tbh_build_keeps_live_publication(tmp_path):
    sources, live = tmp_path / "sources", tmp_path / "helps"
    path = sources / "Borland Turbo Basic 1.x current/TBHELP.TBH"
    path.parent.mkdir(parents=True)
    path.write_bytes(_sample())
    build_help_groups(["borland"], sources, live, product_keys=["tbasic"], keep_products=["tbasic"])
    before = {p.relative_to(live): p.read_bytes() for p in live.rglob("*") if p.is_file()}
    path.write_bytes(_sample()[:-1])
    with pytest.raises(ValueError):
        build_help_groups(["borland"], sources, live, product_keys=["tbasic"], keep_products=["tbasic"])
    assert before == {p.relative_to(live): p.read_bytes() for p in live.rglob("*") if p.is_file()}


def test_original_rows_match_native_renderer_and_all_links_resolve():
    sources = sorted(Path("var/sources").rglob("TBHELP.TBH"))
    if not sources:
        pytest.skip("Original Turbo Basic help unavailable")
    # SHA256 of [absolute record offset, hex display rows] JSON lines produced
    # by executing TB.EXE 6D57h; no Python text decoder supplied its rows.
    native = {
        "3ADC1C1F": (207, "330f976860d8ec61596deaca1f64e024e2939911e3de25a76f415483d98964a6"),
        "E9E8BE71": (257, "e6294fa8eb4e6b11f878658060ea552871cd6e92cbbdc2d5e952a3c0c903fe3f"),
    }
    for path in sources:
        crc = f"{zlib.crc32(path.read_bytes()):08X}"
        count, expected = native[crc]
        document = load_document(path)
        assert document.format_name == "turbo-basic" and len(document.topics) == 108
        ids = {t.context_id for t in document.topics}
        assert 100 in ids and sum(t.context_id >= 65536 for t in document.topics) == 42
        assert sum(len(t.positional_keywords) for t in document.topics) == count
        digest = hashlib.sha256()
        for topic in document.topics:
            assert all(link.target_context in ids for link in topic.positional_keywords)
            offset = document.metadata["text_record_offsets"][str(topic.context_id)]
            digest.update(json.dumps([offset, [row.hex() for row in topic.raw_lines]],
                                     separators=(",", ":")).encode() + b"\n")
        assert digest.hexdigest() == expected, path
