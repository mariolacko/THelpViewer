"""Runtime HELP corruption must fail before a staged server publication."""

from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.tdh import TdhHelpReader, _parse_tfh_block


TDH_SOURCES = [
    "Borland Turbo Debugger 1.0/TDHELP.TDH",
    "Borland Turbo Assembler 1.0 with Turbo Debugger/TDHELP.TDH",
    "Borland Turbo Debugger 1.5 (DE)/TDHELP.TDH",
    "Borland Turbo Assembler 1.01 (DE)/TDHELP.TDH",
    *[f"Borland Turbo Assembler {version}/{name}.TDH"
      for version in ("4.x", "5.x") for name in ("TDHELP", "TD32HELP", "TDWHELP")],
]
TFH_SOURCES = [
    "Borland Turbo Profiler/TFHELP.TFH",
    "Borland Turbo Assembler 2.01/TFHELP.TFH",
]


def source(relative):
    path = Path("data/sources") / relative
    if not path.is_file():
        pytest.skip("Original runtime HELP not available")
    return path


def literal(text):
    nibbles = [n for value in text for n in (0xF, value & 0xF, value >> 4)]
    if len(nibbles) % 2:
        nibbles.append(0)
    return bytes(nibbles[i] | (nibbles[i+1] << 4) for i in range(0, len(nibbles), 2))


def unavailable_tail_size(data):
    stored = int.from_bytes(data[:2], "big")
    base = 2 + 2 * stored
    if int.from_bytes(data[base:base+2], "big") != 0:
        return 0
    end = base + sum(struct.unpack_from(f">{stored}h", data, 2))
    return max(len(data) - end, 0)


@pytest.mark.parametrize("relative", TDH_SOURCES + TFH_SOURCES)
@pytest.mark.parametrize("cut", [1, 10, 50, 100])
def test_truncated_runtime_help_does_not_return_a_partial_document(relative, cut):
    path = source(relative)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="[Tt]runcated"):
        # TFH 1.0's unavailable final context has unaddressed trailing bytes.
        # Cut actual mapped data, rather than claiming unused bytes are text.
        TdhHelpReader(source_path=path).read_bytes(original[:-(unavailable_tail_size(original) + cut)])


def test_unavailable_tail_is_not_a_mandatory_page_or_file_length_signature():
    path = source(TFH_SOURCES[0])
    original = path.read_bytes()
    ignored = unavailable_tail_size(original)
    assert ignored == 159
    reader = TdhHelpReader(source_path=path)
    assert reader.read_bytes(original[:-ignored]).topics == reader.read_bytes(original).topics


@pytest.mark.parametrize("block,field", [
    (b"", "page header"),
    (b"\0", "page header"),
    (b"\0\0", "topic terminator"),
    (b"\0\0\x11", "topic terminator"),
    (b"\0\0\x0f", "literal escape"),
    (b"\0\0\xf1", "literal escape"),
    (b"\0\0\xff", "literal escape"),
    (b"\0\0" + literal(b"^"), "hotspot target"),
    (b"\0\0" + literal(b"^") + b"\1", "hotspot target"),
])
def test_incomplete_runtime_fields_are_not_interpreted_as_a_page_end(block, field):
    with pytest.raises(ValueError, match=field):
        _parse_tfh_block(block)


@pytest.mark.parametrize("label", [b"word", b"L"*1000])
def test_unclosed_hotspot_label_fails_even_if_it_would_fill_the_screen(label):
    block = b"\0\0" + literal(b"^") + b"\0\1" + literal(label)
    with pytest.raises(ValueError, match="hotspot label"):
        _parse_tfh_block(block, max_lines=15)


@pytest.mark.parametrize("label", [b"word", b"L"*1000])
def test_unfinished_hidden_hotspot_trailer_cannot_hide_truncation(label):
    block = b"\0\0" + literal(b"^") + b"\0\1" + literal(label + b"\0hidden")
    with pytest.raises(ValueError, match="hotspot trailer"):
        _parse_tfh_block(block, max_lines=15)


def test_complete_hidden_trailer_retains_visible_label_and_target():
    block = b"\0\0" + literal(b"^") + b"\0\1" + literal(b"Label\0hidden^\r\n\0")
    lines, keys, _ = _parse_tfh_block(block)
    assert lines == [b"Label"]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [
        (1, 0, 1, 5),
    ]


@pytest.mark.parametrize("lookahead", [False, True])
@pytest.mark.parametrize("prefix,label,suffix,expected,line,first,last", [
    (b"x"*46, b"Label\0hidden", b"\r\nNEXT\0",
     [b"x"*46, b"Label", b"NEXT"], 1, 1, 5),
    (b"prefix ", b"Label\0hidden", b"\r\nNEXT\0",
     [b"prefix Label", b"NEXT"], 0, 8, 12),
    (b"prefix ", b"Label\0hidden\r\nmore", b"\r\nNEXT\0",
     [b"prefix Label", b"NEXT"], 0, 8, 12),
    (b"prefix ", b"Label\0hidden", b" visible\0",
     [b"prefix Label"], 0, 8, 12),
    (b"x"*46, b"Label\0hidden", b" visible\0",
     [b"x"*46, b"Label visible"], 1, 1, 5),
    (b"x"*46, b"\0hidden", b"\r\nNEXT\0",
     [b"x"*46, b"", b"NEXT"], None, None, None),
    (b"", b"A\tB", b"\0", [b"A\tB"], 0, 1, 3),
    (b"", b"A\r\nB", b"\0", [b"A\r\nB"], 0, 1, 4),
])
def test_hotspot_c_strings_match_native_profiler_and_td45(
    lookahead, prefix, label, suffix, expected, line, first, last,
):
    # Captured original line helpers: NUL ends the visible C string, not
    # the encoded label. Only displayed cells receive a projected hotspot.
    block = b"\0\0" + literal(prefix) + literal(b"^") + b"\0\x0b"
    block += literal(label + b"^" + suffix)
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=lookahead, max_lines=15)
    assert lines == expected
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == (
        [] if line is None else [(11, line, first, last)]
    )


def test_hidden_newline_is_not_a_substitute_for_the_closing_caret():
    block = b"\0\0" + literal(b"^") + b"\0\1" + literal(b"Label\0hidden\r\nNEXT\0")
    with pytest.raises(ValueError, match="hotspot trailer: missing closing caret"):
        _parse_tfh_block(block, max_lines=15)


@pytest.mark.parametrize("lookahead", [False, True])
def test_datasheet_embedded_nul_byte_example(lookahead):
    block = bytes.fromhex("00 00 EF 05 00 0B 1F F4 00 2F F4 5E 0F 00")
    lines, keys, _ = _parse_tfh_block(block, hotspot_lookahead=lookahead)
    assert lines == [b"A"]
    assert [(k.target_context, k.line, k.first_column, k.last_column) for k in keys] == [(11, 0, 1, 1)]


def test_native_screen_limit_is_a_valid_stop_without_a_later_nul():
    lines, keys, _ = _parse_tfh_block(b"\0\0" + literal(b"row\r\n"*15), max_lines=15)
    assert lines == [b"row"] * 15 and keys == []


def test_unused_overlapping_eof_slot_is_not_fabricated_as_a_page():
    path = source("Borland Turbo Assembler 4.x/TD32HELP.TDH")
    original = path.read_bytes()
    document = TdhHelpReader(source_path=path).read_bytes(original)
    stored = int.from_bytes(original[:2], "big")
    assert len(document.topics) == 774
    assert stored not in {topic.context_id for topic in document.topics}


@pytest.mark.parametrize("relative", [TDH_SOURCES[1], TFH_SOURCES[1]])
def test_real_bad_help_cannot_replace_published_bundles_and_can_be_retried(tmp_path, relative):
    original = source(relative).read_bytes()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / relative
    copy.parent.mkdir(parents=True)
    copy.write_bytes(original)
    build_help_groups(["borland"], sources, helps, product_keys=["td"], keep_products=["td"])
    published = {path.relative_to(helps): path.read_bytes()
                 for path in helps.rglob("*") if path.is_file()}

    copy.write_bytes(original[:-50])
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["borland"], sources, helps, product_keys=["td"], keep_products=["td"])
    assert published == {path.relative_to(helps): path.read_bytes()
                         for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert copy.read_bytes() == original[:-50]

    copy.write_bytes(original)
    result = build_help_groups(["borland"], sources, helps, product_keys=["td"], keep_products=["td"])
    assert result["backup"] and result["bundles"] == 1
    backup = Path(result["backup"])
    assert published == {path.relative_to(backup): path.read_bytes()
                         for path in backup.rglob("*") if path.is_file()}
    assert copy.read_bytes() == original
