"""Low-first THELP nibble grammar, physical endings and restored link cells."""

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader, is_thelp_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_thelp_validation import admin, file_header, record


TABLE = b"\0ABCDEFGHIJKLM"


def packed(nibbles):
    assert len(nibbles) % 2 == 0
    return bytes(low | high << 4 for low, high in zip(nibbles[::2], nibbles[1::2]))


def parse_text(payload, *, table=TABLE, version=52, following=b""):
    header = file_header(version)
    if version <= 3:
        header = header[:-14] + table
        compression = b""
    else:
        compression = record(5, b"\2" + table)
    parser = ThelpBinaryParser(admin(version) + header + compression + record(2, payload) + following)
    parser.parse()
    return parser.screens[0]


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5, 51, 52])
@pytest.mark.parametrize("payload,lines", [
    (b"", []), (b"\x21", [b"AB"]), (b"\x0d", [b"M"]),
    (b"\x01", [b"A"]), (b"\x00", [b"", b""]),
    (b"\x01\x21", [b"A", b"AB"]),
])
def test_both_halves_of_the_last_byte_are_consumed_without_an_eot(version, payload, lines):
    screen = parse_text(payload, version=version)
    assert screen["lines"] == lines
    assert not screen["text_complete"]


@pytest.mark.parametrize("prefix", [[], [1]])
def test_raw_bytes_keep_low_high_operand_order_in_both_alignments(prefix):
    for value in range(256):
        if value == 1:  # A non-repeated literal SOH is the logical EOT.
            continue
        nibbles = prefix + [15, value & 15, value >> 4]
        if len(nibbles) % 2:
            nibbles.append(0)
        assert parse_text(packed(nibbles))["lines"] == [b"A" * len(prefix) + bytes([value])]


@pytest.mark.parametrize("prefix", [[], [1]])
def test_repeat_counts_and_table_characters_in_both_alignments(prefix):
    for count in range(2, 18):
        for character in range(14):
            nibbles = prefix + [14, count - 2, character, 1]
            if len(nibbles) % 2:
                nibbles.append(0)
            expected = ([b"A" * len(prefix)] + [b""] * (count - 1) + [b"A"]
                        if character == 0 else [b"A" * len(prefix) + TABLE[character:character+1] * count + b"A"])
            assert parse_text(packed(nibbles))["lines"] == expected


@pytest.mark.parametrize("prefix", [[], [1]])
def test_repeated_raw_bytes_are_not_recursively_interpreted_as_nibble_commands(prefix):
    for count in (2, 17):
        for value in (0, 2, 5, 13, 14, 15, 20, 128, 255):
            nibbles = prefix + [14, count - 2, 15, value & 15, value >> 4, 1]
            if len(nibbles) % 2:
                nibbles.append(0)
            assert parse_text(packed(nibbles))["lines"] == [b"A" * len(prefix) + bytes([value]) * count + b"A"]


def test_zero_valued_lookup_entries_end_lines_for_direct_and_repeated_codes():
    table = TABLE[:3] + b"\0" + TABLE[4:]
    assert parse_text(b"\x31", table=table)["lines"] == [b"A"]
    assert parse_text(packed([1, 14, 0, 3]), table=table)["lines"] == [b"A", b""]


@pytest.mark.parametrize("version", [2, 52])
def test_lookup_entry_zero_is_the_reserved_newline_not_a_printable_character(version):
    with pytest.raises(ValueError, match="entry zero must be NUL"):
        parse_text(b"\x21", table=b"Z" + TABLE[1:], version=version)


@pytest.mark.parametrize("payload", [b"\xf1", b"\xe1", b"\x0f", b"\x0e", b"\xfe", b"\xfe\xaf"])
def test_incomplete_last_low_or_high_opcode_cannot_borrow_from_a_keyword_record(payload):
    with pytest.raises(ValueError, match="THELP record 2"):
        parse_text(payload, following=record(3, bytes(6)))


@pytest.mark.parametrize("nibbles", [[14, 0, 14, 0], [1, 14, 15, 14]])
def test_repeat_character_e_is_undefined_not_a_silently_dropped_run(nibbles):
    with pytest.raises(ValueError, match="repeat character nibble 0xE"):
        parse_text(packed(nibbles))


@pytest.mark.parametrize("nibbles,lines,complete", [
    ([1, 15, 1, 0], [b"A"], False),
    ([1, 0, 15, 1, 0, 0], [b"A"], True),
    ([1, 0, 0, 15, 1, 0], [b"A", b""], True),
    ([1, 14, 1, 0, 15, 1, 0, 0], [b"A", b"", b""], True),
])
def test_eot_alignment_and_the_page_completion_newline_are_preserved(nibbles, lines, complete):
    screen = parse_text(packed(nibbles))
    assert screen["lines"] == lines
    assert screen["text_complete"] is complete


def test_early_logical_eot_does_not_change_the_declared_next_record_boundary():
    data = record(2, packed([1, 15, 1, 0]) + b"\xee\xff") + record(3, bytes(6))
    parser = ThelpBinaryParser(admin() + file_header() + record(5, b"\2" + TABLE) + data)
    parser.parse()
    assert parser.screens[0]["lines"] == [b"A"]
    assert parser.screens[0]["link_down"] == 0
    assert parser.pos == len(parser.data)


def test_real_pascal_last_letters_and_the_entire_positioned_hotspot_are_restored():
    document = ThelpHelpReader().read_path(Path("data/sources/Borland Pascal 4.0/TURBO.HLP"))
    topics = {topic.context_id: topic for topic in document.topics}
    assert topics[34].raw_lines[-1] == b" Compile  Options"
    assert topics[5].raw_lines[-1] == b" Alt-F10       Displays the version screen"
    assert topics[10].raw_lines[-1] == b" Change dir  OS shell     Quit"
    assert topics[183].raw_lines[-1] == b"SPtr"
    assert topics[183].uhf_content[-1] == "[link:topic=466]SPtr[/link]"
    keyword = topics[183].positional_keywords[-1]
    assert (keyword.target_context, keyword.line, keyword.first_column, keyword.last_column) == (466, 13, 1, 4)


def test_restored_native_link_cell_reaches_the_bundle_without_changing_the_original(tmp_path):
    source = tmp_path / "sources/Borland Turbo Pascal 4.0/TURBO.HLP"
    source.parent.mkdir(parents=True)
    original = Path("data/sources/Borland Pascal 4.0/TURBO.HLP").read_bytes()
    source.write_bytes(original)
    result = export_bundle_tree(tmp_path / "sources", tmp_path / "helps", source_paths=[source], layout="helps")
    payload = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    assert payload["topics"]["183"]["content"][-1] == "[link:topic=466]SPtr[/link]"
    assert "466" in payload["topics"]
    assert source.read_bytes() == original


def test_every_physical_text_record_matches_the_independent_c_nibble_reference_rows():
    # DEHELP.C getNibble/getByte + bounded grammar events, projected to rows
    # up to the logical EOT. This is not a capture of its source formatter/GUI.
    digest = hashlib.sha256()
    files = records = 0
    root = Path("data/sources")
    for source in sorted(root.rglob("*")):
        if not source.is_file():
            continue
        with source.open("rb") as stream:
            prefix = stream.read(4096)
            if not is_thelp_binary(prefix):
                continue
            data = prefix + stream.read()
        files += 1
        name = source.relative_to(root).as_posix()
        parser = ThelpBinaryParser(data)
        parser._parse_administrative()
        while parser.pos < len(data) and data[parser.pos] != 32:
            start = parser.pos
            kind, _size = struct.unpack_from("<BH", data, start)
            parser._parse_record()
            if kind == 2:
                rows = [line.hex() for line in parser.screens[-1]["lines"]]
                digest.update(json.dumps((name, start, rows), separators=(",", ":")).encode() + b"\n")
                records += 1
    assert (files, records) == (66, 93_142)
    assert digest.hexdigest() == "93677d27d3455b126291dc711aab7bdb33d29598e68becc0e17887cc4de7057e"
