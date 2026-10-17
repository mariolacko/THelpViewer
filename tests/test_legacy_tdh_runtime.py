"""Older TDH cells verified with bounded original TD 1.0/1.5 execution."""

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.readers.tdh import (
    TdhHelpReader,
    _parse_tfh_block,
    probe_tdh_binary,
)
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


SAMPLES = [
    ("Borland Turbo Debugger 1.0", 0xA9C668A7, 530, 566,
     "7544a2c1120af0c8753d327de745b1afd7689657b3bbd6eddbebee630d5ddad8"),
    ("Borland Turbo Assembler 1.0 with Turbo Debugger", 0xA6E139F2, 597, 631,
     "61b7047beaeff0a5816da3f5251fc76695484ab36da2786f0ed7ac439abfff4c"),
    ("Borland Turbo Debugger 1.5 (DE)", 0x4B5D33CE, 536, 580,
     "dd57c28f5307f08f500812997a03ad216cbca260ba336e2299d2fe150991d8f7"),
    ("Borland Turbo Assembler 1.01 (DE)", 0xF126AD2C, 538, 579,
     "26b2fcbbeea3551b73e2615253df3d59061b0515024c2819149087be9738469e"),
]

# Original TD emits stale metadata when later punctuation/suffixes wrap a
# label. Keep that captured baseline, but separately require the corrected
# cell ranges. These fixtures are not used by production decoding.
REFLOWED_SPANS = {
    SAMPLES[0][0]: {},
    SAMPLES[1][0]: {
        225: ((398, 13, 40, 48), [(398, 13, 40, 43), (398, 14, 1, 4)]),
    },
    SAMPLES[2][0]: {
        116: ((390, 1, 34, 42), [(390, 2, 1, 9)]),
        525: ((533, 1, 33, 48), [(533, 2, 1, 16)]),
        530: ((533, 0, 26, 41), [(533, 1, 1, 16)]),
        537: ((533, 1, 33, 48), [(533, 2, 1, 16)]),
    },
    SAMPLES[3][0]: {
        67: ((41, 7, 32, 48), [(41, 7, 32, 41), (41, 8, 1, 6)]),
    },
}


def source(folder):
    path = Path("var/sources") / folder / "TDHELP.TDH"
    if not path.is_file():
        pytest.skip("Original older TDH not available")
    return path


@pytest.mark.parametrize("folder,crc,count,links,digest", SAMPLES)
def test_older_tdh_text_and_hotspots_match_native_cells(folder, crc, count, links, digest):
    path = source(folder)
    data = path.read_bytes()
    assert probe_tdh_binary(data).crc32 == crc
    document = TdhHelpReader(source_path=path).read_bytes(data)
    assert len(document.topics) == count
    assert document.metadata["display_width"] == 48
    changes = REFLOWED_SPANS[folder]
    extra_fragments = sum(len(parts) - 1 for _native, parts in changes.values())
    assert sum(len(topic.positional_keywords) for topic in document.topics) == links + extra_fragments
    ids = {topic.context_id for topic in document.topics}
    cells = []
    for topic in document.topics:
        if not topic.context_id:
            continue
        spans = [(k.target_context, k.line, k.first_column, k.last_column)
                 for k in topic.positional_keywords]
        if topic.context_id in changes:
            native, corrected = changes[topic.context_id]
            assert all(part in spans for part in corrected)
            first = spans.index(corrected[0])
            for part in corrected:
                spans.remove(part)
            spans.insert(first, native)
        cells.append((topic.context_id, [line.hex() for line in topic.raw_lines], spans))
    assert hashlib.sha256(json.dumps(cells, separators=(",", ":")).encode()).hexdigest() == digest
    for topic in document.topics:
        assert len(topic.raw_lines) <= 15
        assert all(len(line) <= 48 and b"<E>" not in line for line in topic.raw_lines)
        assert topic.next_context is None or topic.next_context in ids
        for key in topic.positional_keywords:
            assert key.target_context in ids
            assert 0 <= key.line < len(topic.raw_lines)
            assert 1 <= key.first_column <= key.last_column <= len(topic.raw_lines[key.line])


def literal(text):
    """Encode literal bytes low-nibble-first, padding the unused high nibble."""
    nibbles = [n for value in text for n in (0xF, value & 0xF, value >> 4)]
    if len(nibbles) % 2:
        nibbles.append(0)
    return bytes(nibbles[i] | (nibbles[i+1] << 4) for i in range(0, len(nibbles), 2))


def hotspot(label, target):
    return literal(b"^") + target.to_bytes(2, "big") + literal(label + b"^")


def runtime_starts(data):
    starts, offset = [], 2 + 2*int.from_bytes(data[:2], "big")
    for delta in struct.unpack_from(">530h", data, 2):
        starts.append(offset)
        offset += delta
    return starts


@pytest.mark.parametrize("owner,alias", [(518, 519), (328, 528)])
def test_overlapping_alias_uses_source_bytes_even_when_an_earlier_page_has_identical_text(owner, alias):
    original = source(SAMPLES[0][0]).read_bytes()
    data = bytearray(original)
    stored = int.from_bytes(data[:2], "big")
    starts = runtime_starts(data)
    end = starts[owner+1] if owner < stored else len(data)
    block = original[starts[owner]:end]
    assert len(block) <= starts[3] - starts[2]
    data[starts[2]:starts[2]+len(block)] = block

    # The copied page is a real, earlier context with exactly the same cells.
    # Text matching would wrongly choose 2, instead of the containing stream.
    document = TdhHelpReader().read_bytes(bytes(data))
    topics = {topic.context_id: topic for topic in document.topics}
    assert topics[2].raw_lines == topics[owner].raw_lines
    assert topics[alias].redirect_context == owner
    assert alias in topics[owner].alias_contexts
    assert alias not in topics[2].alias_contexts
    assert alias in document.metadata["tdh_decode"]["embedded_alias_contexts"]
    assert not document.metadata["tdh_decode"]["remaining_unresolved_alias_contexts"]
    assert document.metadata["tdh_probe"]["crc32"] != f"{SAMPLES[0][1]:08X}"


def test_unconsumed_alias_bytes_are_not_assigned_to_an_unrelated_similar_page():
    original = source(SAMPLES[0][0]).read_bytes()
    data = bytearray(original)
    starts = runtime_starts(data)
    block = original[starts[328]:starts[329]]
    assert len(block) <= starts[3] - starts[2]
    data[starts[2]:starts[2]+len(block)] = block
    # Page 328 now terminates before the addressed bytes at 528. Keep those
    # bytes readable independently, with an identical text copy in page 2.
    data[starts[328]+2] = 0xDD
    document = TdhHelpReader().read_bytes(bytes(data))
    topics = {topic.context_id: topic for topic in document.topics}
    assert topics[328].raw_lines == [b""]
    assert topics[528].raw_lines[0].startswith(b" floating-point")
    assert topics[528].redirect_context is None
    assert 528 not in topics[2].alias_contexts
    assert 528 not in topics[328].alias_contexts
    assert document.metadata["tdh_decode"]["remaining_unresolved_alias_contexts"] == [528]


def test_source_ranges_cover_headers_and_split_literals_but_not_the_next_unread_byte():
    record = bytes.fromhex("00 00 EF 05 00 0B 1F F4 00 2F F4 5E 0F 00")
    spans = []
    lines, keys, _ = _parse_tfh_block(
        record + b"\xaa\xcc", position_callback=lambda first, end: spans.append((first, end)),
    )
    assert lines == [b"A"] and keys[0].target_context == 11
    assert (0, 2) in spans  # Page WORD, including an alias at byte +1.
    assert (4, 6) in spans  # Aligned, uncompressed target WORD.
    assert {offset for first, end in spans for offset in range(first, end)} == set(range(len(record)))


def test_source_range_contains_the_entire_literal_that_skips_an_alias_cursor():
    original = source(SAMPLES[0][0]).read_bytes()
    spans = []
    _parse_tfh_block(
        original[63905:], hotspot_lookahead=False, max_lines=15,
        position_callback=lambda first, end: spans.append((first, end)),
    )
    # Owner 328's literal b crosses bytes 67..68; alias 528 starts at +68.
    # Sampling only the end cursor (69) misses that physical address.
    assert (67, 69) in spans


@pytest.mark.parametrize("lookahead", [False, True])
def test_later_plain_text_reflows_multiple_hotspots_with_the_same_word(lookahead):
    block = (b"\0\0" + literal(b"x"*40 + b" ") + hotspot(b"AB", 11)
             + literal(b"-") + hotspot(b"CD", 12) + literal(b"...\0"))
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=lookahead)
    assert lines == [b"x"*40, b"AB-CD..."]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (11, 1, 1, 2), (12, 1, 4, 5),
    ]


def test_repeated_word_wrap_splits_a_hotspot_without_linking_punctuation():
    block = (b"\0\0" + literal(b"x"*30 + b" ")
             + hotspot(b"word word word", 11) + literal(b"-suffix. more text.\0"))
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=False)
    assert lines == [b"x"*30 + b" word word", b"word-suffix. more text."]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (11, 0, 32, 40), (11, 1, 1, 4),
    ]


@pytest.mark.parametrize("max_lines", [1, 2, 3])
def test_oversized_pending_hotspot_obeys_screen_limit(max_lines):
    block = b"\0\0" + hotspot(b"L"*200, 11) + literal(b"\0")
    lines, keys, _ = _parse_tfh_block(block, max_lines=max_lines, hotspot_lookahead=False)
    assert lines == [b""] + [b"L"*48] * (max_lines - 1)
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (11, row, 1, 48) for row in range(1, max_lines)
    ]


def test_carried_fragment_below_screen_is_not_a_phantom_hotspot():
    block = (b"\0\0" + literal(b"x"*30 + b" ")
             + hotspot(b"word word word", 11) + literal(b"-suffix.\0"))
    lines, keys, _ = _parse_tfh_block(block, max_lines=1, hotspot_lookahead=False)
    assert lines == [b"x"*30 + b" word word"]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (11, 0, 32, 40),
    ]


def test_hard_word_wrap_keeps_a_full_hotspot_on_the_previous_row():
    block = b"\0\0" + literal(b"x"*44) + hotspot(b"ABCD", 11) + literal(b".\0")
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=False)
    assert lines == [b"x"*44 + b"ABCD", b"."]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (11, 0, 45, 48),
    ]


@pytest.mark.parametrize("folder,context,expected", [
    (SAMPLES[1][0], 225, ["[link:topic=398]byte[/link]", "[link:topic=398]list[/link]."]),
    (SAMPLES[2][0], 116, ["[link:topic=390]Assembler[/link]-Befehl"]),
    (SAMPLES[2][0], 525, ["[link:topic=533]Objekthierarchie[/link]-Fenster"]),
    (SAMPLES[2][0], 530, ["[link:topic=533]Objekthierarchie[/link]-Fenster"]),
    (SAMPLES[2][0], 537, ["[link:topic=533]Objekthierarchie[/link]-Fenster"]),
    (SAMPLES[3][0], 67, ["[link:topic=41]Breakpoint[/link]", "[link:topic=41]window[/link]."]),
])
def test_wrapped_source_labels_survive_bundle_export(tmp_path, folder, context, expected):
    path = source(folder)
    original = path.read_bytes()
    results = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=[path], layout="helps")
    assert len(results) == 1 and path.read_bytes() == original
    bundle = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    content = "\n".join(bundle["topics"][str(context)]["content"])
    assert all(fragment in content for fragment in expected)
    assert not bundle["metadata"].get("unresolved_contexts", {}).get("links")


@pytest.mark.parametrize("control", [0xD, 0xE])
def test_dictionary_nul_controls_end_the_page_in_every_profile(control):
    block = b"\0\0" + literal(b"A") + bytes([control]) + literal(b"hidden")
    for lookahead in (False, True):
        lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=lookahead)
        assert lines == [b"A"] and keys == []


def test_zero_target_consumes_the_word_and_displays_a_literal_caret():
    block = b"\0\0" + literal(b"^") + b"\0\0" + literal(b"Pointer operator\0")
    for lookahead in (False, True):
        lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=lookahead)
        assert lines == [b"^Pointer operator"] and keys == []


def test_only_the_later_hotspot_layout_reserves_a_nonspace_lookahead_cell():
    block = (b"\0\0" + literal(b"x"*23 + b"^") + b"\x80\x01"
             + literal(b"L"*25 + b"^\0"))
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=False)
    assert lines == [b"x"*23 + b"L"*25]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (0x8001, 0, 24, 48),
    ]
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=True)
    assert lines == [b"x"*23, b"L"*25]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (0x8001, 1, 1, 25),
    ]


@pytest.mark.parametrize("folder,context", [
    (SAMPLES[1][0], 596), (SAMPLES[2][0], 537), (SAMPLES[3][0], 538),
])
def test_older_final_pages_export_without_changing_originals(tmp_path, folder, context):
    path = source(folder)
    original = path.read_bytes()
    results = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=[path], layout="helps")
    assert len(results) == 1 and path.read_bytes() == original
    bundle = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    assert str(context) in bundle["topics"]
    assert bundle["metadata"]["display"]["cols"] == 48
    assert not bundle["metadata"].get("unresolved_contexts", {}).get("links")
    if context == 596:
        assert "[link:topic=596]Hardware breakpoint[/link]" in "\n".join(bundle["topics"]["55"]["content"])
