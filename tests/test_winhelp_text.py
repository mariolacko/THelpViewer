"""Boundaries and native HC31 field/control vectors, not printable-run guesses."""

import struct

import pytest

from thelpviewer.server.converter.readers.winhelp_binary import WinHelpTopicLink
from thelpviewer.server.converter.readers.winhelp_text import (
    _Cursor, WinHelpCommand, WinHelpDisplay, WinHelpFont, context_hash,
    decode_font_text, macro_navigation, read_fonts, read_link,
)
from thelpviewer.server.converter.readers.winhelp import _Layout


def short(value, signed=False, wide=False):
    bias = 16384 if wide else 64
    n = value + bias if signed else value
    return (2 * n + int(wide)).to_bytes(2 if wide else 1, "little")


def display(commands, *, flags=0, fields=b"", table=None, column=0):
    text = b"".join(text + b"\0" for text, _ in commands)
    data1 = b"\x00\x80" + short(len(text), wide=len(text) > 127)
    if table is not None:
        data1 += bytes((len(table), 1)) + b"".join(struct.pack("<hh", *c) for c in table)
        data1 += struct.pack("<h", column) + b"\x11\x22\x80"
    data1 += b"\0\x80\0\0" + struct.pack("<H", flags) + fields
    data1 += b"".join(command for _, command in commands)
    if table is not None:
        data1 += b"\xff\xff"
    return WinHelpTopicLink(72, 12, 0xFFFFFFFF, 0x23 if table is not None else 0x20, data1, text)


FONT = WinHelpFont(0, 20, 3, b"Arial", b"\0\0\0", b"\xff\xff\xff")


@pytest.mark.parametrize("raw,signed,value", [
    ("00", False, 0), ("fe", False, 127), ("01 01", False, 128),
    ("ff ff", False, 32767), ("00", True, -64), ("80", True, 0),
    ("fe", True, 63), ("01 00", True, -16384), ("ff ff", True, 16383),
])
def test_compressed_shorts(raw, signed, value):
    cursor = _Cursor(bytes.fromhex(raw) + b"Z", "vector")
    assert cursor.short(signed=signed) == value
    assert cursor.take(1) == b"Z"


@pytest.mark.parametrize("raw,signed,value", [
    ("00 00", False, 0), ("fe ff", False, 32767),
    ("01 00 01 00", False, 32768), ("ff ff ff ff", False, 2147483647),
    ("00 00", True, -16384), ("00 80", True, 0), ("fe ff", True, 16383),
    # HelpDeco scanlong/Wine use 40000000h, not the old prose's 04000000h.
    ("01 80 00 80", True, 16384), ("01 00 00 80", True, 0),
    ("01 00 00 00", True, -1073741824), ("ff ff ff ff", True, 1073741823),
])
def test_compressed_longs(raw, signed, value):
    cursor = _Cursor(bytes.fromhex(raw) + b"Z", "vector")
    assert cursor.long(signed=signed) == value
    assert cursor.take(1) == b"Z"


@pytest.mark.parametrize("raw,operation", [(b"", "short"), (b"\1", "short"),
                                          (b"\0", "long"), (b"\1\0\0", "long")])
def test_compressed_integers_do_not_read_outside_operand(raw, operation):
    with pytest.raises(ValueError, match="Truncated"):
        getattr(_Cursor(raw, "operand"), operation)()


def test_format_and_strings_advance_separately_even_for_empty_text():
    record = display([(b"", b"\x80\x01\0"), (b"bold", b"\x80\0\0"),
                      (b"normal", b"\x82"), (b"", b"\xff")])
    paragraph = WinHelpDisplay.read(record).paragraphs[0]
    assert [(c.text, c.text_offset, c.opcode, c.value) for c in paragraph.commands] == [
        (b"", 0, 0x80, 1), (b"bold", 1, 0x80, 0), (b"normal", 6, 0x82, 0), (b"", 13, 0xFF, 0)]
    layout = _Layout((FONT, WinHelpFont(1, 20, 3, b"Arial", FONT.foreground, FONT.background)), "cp1252")
    layout.record(record)
    assert "".join(c.char for c in layout.rows[0]) == "boldnormal"
    assert [c.font for c in layout.rows[0]] == [1] * 4 + [0] * 6


def test_conditional_metrics_borders_tabs_and_opaque_prefix_are_bounded():
    fields = b"\x00\x80" + b"".join(short(n, True) for n in (1, 2, 3, 12, 24, -12))
    fields += b"\x48\x01\0" + short(2, True) + short(36)
    fields += short(0x4000 | 60, wide=True) + short(2)
    paragraph = WinHelpDisplay.read(display([(b"test", b"\xff")], flags=0x37F, fields=fields)).paragraphs[0]
    assert paragraph.prefix == b"\0\x80\0\0"
    assert paragraph.unknown == 0 and paragraph.metrics == (1, 2, 3, 12, 24, -12)
    assert paragraph.border == (0x48, 1) and paragraph.tabs == ((36, 0), (60, 2))


def test_table_columns_and_cell_end_are_native_not_inferred_from_text():
    parsed = WinHelpDisplay.read(display([(b"not a caption", b"\xff")], table=((12, 100), (24, 200)), column=1))
    assert parsed.columns == ((12, 100), (24, 200))
    assert parsed.table_type == 1 and parsed.paragraphs[0].column == 1
    assert parsed.paragraphs[0].prefix == b"\x11\x22\x80\0\x80\0\0"
    with pytest.raises(ValueError, match="column"):
        WinHelpDisplay.read(display([(b"test", b"\xff")], table=((0, 10),), column=1))


@pytest.mark.parametrize("damage", ["format-tail", "text-tail", "no-nul", "opcode", "font-operand", "picture-size"])
def test_invalid_control_streams_fail_instead_of_publishing_text_fragments(damage):
    record = display([(b"test", b"\xff")])
    fmt, text = record.data1, record.data2
    if damage == "format-tail": fmt += b"\0"
    if damage == "text-tail": text += b"x"
    if damage == "no-nul": text = text[:-1]
    if damage == "opcode": fmt = fmt[:-1] + b"\x7f"
    if damage == "font-operand": fmt = fmt[:-1] + b"\x80\1"
    if damage == "picture-size": fmt = fmt[:-1] + b"\x86\x22\x08\x80\0"
    with pytest.raises(ValueError):
        WinHelpDisplay.read(WinHelpTopicLink(72, 12, 0xFFFFFFFF, 0x20, fmt, text))


def test_large_embedded_picture_uses_full_signed_long_bias_and_payload_boundary():
    payload = b"\1\0\x6c\x50" + bytes(20000)
    size = struct.pack("<I", 2 * (len(payload) + 0x40000000) + 1)
    parsed = WinHelpDisplay.read(display([(b"", b"\x86\x22" + size + short(3) + payload),
                                        (b"after", b"\xff")]))
    assert parsed.paragraphs[0].commands[0].hotspots == 3
    assert parsed.paragraphs[0].commands[1].text == b"after"


@pytest.mark.parametrize("alignment,expected", [(0, "a         XYZ"), (1, "a      XYZ"), (2, "a        XYZ")])
def test_tab_alignment_and_native_paragraph_border(alignment, expected):
    fields = b"\x08\1\0" + short(1, True) + short(0x4000 | 120, wide=True) + short(alignment)
    layout = _Layout((FONT,), "cp1252", width=24)
    layout.record(display([(b"a", b"\x83"), (b"XYZ", b"\x82"), (b"", b"\xff")], flags=0x300, fields=fields))
    assert ["".join(c.char for c in row) for row in layout.rows] == [expected, "─" * 24]


def test_authored_margin_wrap_nbsp_and_literal_hyphen_are_retained():
    layout = _Layout((FONT,), "cp1252", width=14)
    record = display([(b"one", b"\x8b"), (b"two-", b"\x8c"), (b"three four five", b"\xff")],
                     flags=0x10, fields=short(12, True))
    layout.record(record)
    rows = ["".join(c.char for c in row) for row in layout.rows]
    assert rows == [" one\xa0two-three", " four five"]


def test_fonts_have_native_eleven_byte_descriptors_and_no_unbounded_names():
    raw = struct.pack("<HHHH", 1, 1, 8, 16) + b"Symbol\0\0"
    raw += b"\x03\x18\x02\0\0\x10\x20\x30\xff\xff\xff"
    font, = read_fonts(raw)
    assert font == WinHelpFont(3, 24, 2, b"Symbol", b"\x10\x20\x30", b"\xff\xff\xff")
    with pytest.raises(ValueError, match="length"):
        read_fonts(raw[:-1])
    invalid = raw[:19] + b"\1\0" + raw[21:]
    with pytest.raises(ValueError, match="index"):
        read_fonts(invalid)


@pytest.mark.parametrize("raw,text,unknown", [(b"Ab", "Αβ", ()), (b"\xb7\xbe\xe6", "•⎯⎛", ()),
                                            (b"\x94", "\ufffd", (148,))])
def test_symbol_font_is_not_decoded_as_ansi_letters(raw, text, unknown):
    symbol = WinHelpFont(0, 20, 2, b"Symbol", FONT.foreground, FONT.background)
    assert decode_font_text(raw, symbol, "cp1252") == (text, unknown)
    assert decode_font_text(b"\x80\xa0", FONT, "cp1252") == ("€\xa0", ())


@pytest.mark.parametrize("opcode", [0xE2, 0xE3, 0xE6, 0xE7])
def test_hc31_link_operand_is_context_hash_not_topic_offset(opcode):
    assert read_link(WinHelpCommand(b"", 0, opcode, b"\x78\x56\x34\x12", 0x12345678)).kind == "context-hash"


@pytest.mark.parametrize("kind,tail,file,window", [(0, b"", None, None), (1, b"\x07", None, 7),
    (4, b"other.hlp\0", b"other.hlp", None), (6, b"secondary\0other.hlp\0", b"other.hlp", b"secondary")])
def test_external_link_window_precedes_filename(kind, tail, file, window):
    payload = bytes((kind,)) + struct.pack("<I", 123) + tail
    command = WinHelpCommand(b"", 0, 0xEB, struct.pack("<H", len(payload)) + payload)
    link = read_link(command)
    assert (link.value, link.file, link.window) == (123, file, window)
    with pytest.raises(ValueError):
        read_link(WinHelpCommand(b"", 0, 0xEB, command.operand[:-1]))


def test_macro_length_counts_whole_following_payload_not_minus_three():
    macro = b'JumpID("", "abc")\0'
    operand = struct.pack("<H", len(macro)) + macro
    commands = WinHelpDisplay.read(display([(b"", b"\xc8" + operand), (b"label", b"\x89"),
                                          (b"end", b"\xff")])).paragraphs[0].commands
    assert read_link(commands[0]).value == macro[:-1]
    assert commands[1].text == b"label" and commands[2].text == b"end"


def test_context_hash_native_ascii_case_and_rollover():
    assert context_hash(b"abc") == context_hash(b"ABC") == (17 * 43 + 18) * 43 + 19
    assert context_hash(b"") == 1
    with pytest.raises(ValueError): context_hash(b"not a context")


@pytest.mark.parametrize("raw,file,name", [(b'JumpID("OWL.HLP", "ABC")', b"OWL.HLP", b"ABC"),
                                         (b"JI(`',`abc')", None, b"abc"),
    (b'IfThenElse(IsMark("home"),"GotoMark(`home\')", "JumpID(`owl.hlp\',`ABC\')")', b"owl.hlp", b"ABC")])
def test_macro_navigation_reads_native_quotes_without_host_eval(raw, file, name):
    link = macro_navigation(raw)
    assert link.kind == "context-hash" and link.file == file and link.value == context_hash(name)


@pytest.mark.parametrize("raw", [b'ExecFile("evil.exe")', b'JumpID("", "ABC"):ExecFile("x")',
                               b'JumpID("", "unterminated)', b"open('x')", b"x(" * 40 + b")" * 40])
def test_unknown_or_multi_command_macros_remain_unavailable(raw):
    assert macro_navigation(raw) is None


def test_contents_macro_retains_source_file():
    link = macro_navigation(b'JumpContents("BCW.HLP")')
    assert link.kind == "contents" and link.file == b"BCW.HLP"
