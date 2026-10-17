"""Native Software602 THelpTopic fields, byte rows, context identities and links."""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.t602_310 import T602310Reader, _T602Parser, _decode_line, _decode_paragraph, _topic_rows
from thelpviewer.server.converter.readers.software602_graphics import decode_help_byte
from thelpviewer.server.converter.readers.tvision_help import paragraph_lines
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


ROOT = Path("var/sources/Software 602")


@lru_cache(maxsize=2)
def source(name):
    path = ROOT / name
    if not path.is_file():
        pytest.skip("Original Software602 HELP is not installed")
    return path.read_bytes()


def record(paragraphs, refs=()):
    encoded = struct.pack("<Hh", 10000, len(paragraphs))
    for wrap, text in paragraphs:
        encoded += struct.pack("<HB", len(text), wrap) + bytes((byte + 1) & 255 for byte in text)
    return encoded + struct.pack("<h", len(refs)) + b"".join(struct.pack("<HhB", *ref) for ref in refs)


def help_file(records, contexts=None, stamp=b"Calc602 - help test"):
    header = len(stamp) + 2
    data = bytearray(stamp + b"\r\n" + bytes(8))
    offsets = []
    for topic in records:
        offsets.append(len(data))
        data.extend(topic)
    contexts = contexts if contexts is not None else list(enumerate(range(len(records))))
    anchors = {context: offsets[index] for context, index in contexts}
    count = max(anchors, default=-1) + 1
    table = len(data)
    data.extend(struct.pack("<HH", 10001, count))
    data.extend(b"".join(struct.pack("<I", anchors.get(context, 0xFFFFFFFF)) for context in range(count)))
    struct.pack_into("<II", data, header, len(data) - (header + 4), table)
    return bytes(data), offsets, table


@pytest.mark.parametrize("stamp", [b"Calc602 - help test", b"Text602 - help with a longer stamp"])
def test_binary_0e_is_legal_in_counts_sizes_and_text_not_a_record_delimiter(stamp):
    paragraphs = [(False, b"A")] * 13 + [(True, b"\rVisible body\r")]
    data, offsets, _ = help_file([record(paragraphs)], stamp=stamp)
    parser = _T602Parser(data)
    assert data[parser.topic_start + 2] == 14  # Fourteen paragraphs.
    parsed = parser.parse()
    assert parsed[0].offset == offsets[0]
    assert len(parsed[0].paragraphs) == 14
    document = T602310Reader().read_bytes(data)
    assert document.topics[0].uhf_content == ["A"] * 13 + ["", "Visible body"]


def test_sparse_unsorted_shared_and_non_multiple_of_four_slot_count():
    data, offsets, _ = help_file([record([(False, b"First")]), record([(False, b"Other")])],
                                 contexts=[(6, 0), (2, 1), (0, 1)])
    parser = _T602Parser(data)
    assert parser.anchors == {0: offsets[1], 2: offsets[1], 6: offsets[0]}
    document = T602310Reader().read_bytes(data)
    assert [(topic.context_id, topic.names, topic.alias_contexts) for topic in document.topics] == [
        (6, ["First"], []), (0, ["Other"], [2]),
    ]
    payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()
    assert set(payload["topics"]) == {"0", "6"}
    assert payload["topics"]["0"]["aliases"]["ids"] == [2]


def test_empty_index_empty_object_and_zero_size_paragraphs_are_distinct_valid_cases():
    data, _, _ = help_file([])
    assert T602310Reader().read_bytes(data).topics == []
    data, _, _ = help_file([record([]), record([(False, b""), (True, b"\r\r")])])
    document = T602310Reader().read_bytes(data)
    assert document.topics[0].uhf_content == []
    assert document.topics[1].uhf_content == ["", ""]


def test_late_context_duplicate_captions_and_labels_with_punctuation_use_exact_ranges():
    menu = record([(False, b"Menu\r"), (False, b"First Other")], [(11, 6, 5), (301, 12, 5)])
    data, _, _ = help_file([menu, record([(False, b"Same")]), record([(False, b"Same")])],
                           contexts=[(133, 0), (11, 1), (301, 2)])
    document = T602310Reader().read_bytes(data)
    assert [t.context_id for t in document.topics] == [133, 11, 301]
    assert document.topics[0].uhf_content[-1] == "[link:topic=11]First[/link] [link:topic=301]Other[/link]"
    label = b"{a:b}[x]. A"
    data, _, _ = help_file([record([(False, label)], [(0, 1, len(label))])])
    assert T602310Reader().read_bytes(data).topics[0].uhf_content == [
        "[link:topic=0]{a:b}[[x]. A[/link]",
    ]


def test_link_range_is_balanced_across_cr_and_paragraph_boundaries():
    first = record([(False, b"aa link\r"), (False, b"next.")], [(20, 4, 9)])
    data, _, _ = help_file([first, record([(False, b"Target")])], contexts=[(0, 0), (20, 1)])
    assert T602310Reader().read_bytes(data).topics[0].uhf_content == [
        "aa [link:topic=20]link[/link]", "[link:topic=20]next[/link].",
    ]


def test_every_byte_is_decremented_and_metadata_like_bytes_in_text_survive():
    assert _decode_paragraph(bytes(range(256))) == bytes([255] + list(range(255)))
    data, _, _ = help_file([record([(False, b"Title\rAfter. A\rx\xffy\rN")])])
    assert T602310Reader().read_bytes(data).topics[0].uhf_content == ["Title", "After. A", "x y", "N"]


@pytest.mark.parametrize("first,expected", [
    (0x80, "Çùè§ß£ÆØÅæøå· ¤ò"), (0x90, "ìÞ¡Ñ¿ñ█▄▀·······"),
    (0xA0, "≡±≥≤⌠⌡÷≈°√²½¼■«»"), (0xB0, "αβΓπΣσµτΦΘΩδ∞φε∩"),
    (0xC0, "┌á└čďěŕ─üíůĺľöňó"), (0xD0, "ôäřšťú├éàýž┬ˇ´˚┼"),
    (0xE0, "┐Á┘ČĎĚŔ│ÜÍŮĹĽÖŇÓ"), (0xF0, "ÔÄŘŠŤÚ┤ÉÀÝŽ┴¨^- "),
])
@pytest.mark.parametrize("stamp", [b"Text602 - help test", b"Calc602 - help test"])
def test_complete_high_glyph_rows_use_the_native_screen_font(first, expected, stamp):
    raw = bytes(range(first, first + 16))
    assert _decode_line(raw) == expected
    data, _, _ = help_file([record([(False, b"Font\r"), (False, raw)])], stamp=stamp)
    document = T602310Reader().read_bytes(data)
    assert document.topics[0].uhf_content == ["Font", expected]
    assert document.metadata["source_encoding"] == "software602-plus1"


@pytest.mark.parametrize("value,glyph", [(0xC0, "┌"), (0xC2, "└"), (0xC7, "─"),
                                        (0xD6, "├"), (0xDF, "┼"), (0xE7, "│"),
                                        (0x98, "▀"), (0xA8, "°"), (0xB4, "Σ")])
def test_a_glyph_never_changes_with_line_length_neighbours_or_box_density(value, glyph):
    cell = bytes([value])
    assert _decode_line(cell) == glyph
    for surrounding in (b"A", b"long sentence " * 5, b"\xc7" * 9):
        assert _decode_line(surrounding + cell).endswith(glyph)
        assert _decode_line(cell + surrounding).startswith(glyph)


def test_help_draw_keeps_literal_low_cells_instead_of_graphics_style_selectors():
    raw = b"\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x13\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f"
    expected = "┏┓━╭╮╰╯│─┳↨↑↓→←└↔√±⌂"
    assert _decode_line(raw) == expected
    data, _, _ = help_file([record([(False, raw)], [(0, 10, 4)])])
    assert T602310Reader().read_bytes(data).topics[0].uhf_content == [
        "┏┓━╭╮╰╯│─[link:topic=0]┳↨↑↓[/link]→←└↔√±⌂",
    ]
    # Revision-dependent/compound glyphs occupy a cell, never become CP437
    # faces, selectors, NUL terminators or arbitrarily erased source bytes.
    assert _decode_line(b"\0\1\2\3\x0e\x0f\x10\x11\x12\x15\x16") == "�" * 11
    assert all(len(decode_help_byte(value)) == 1 for value in range(256))


def test_original_calc_keyboard_charts_keep_math_greek_slovak_and_frame_cells():
    document = T602310Reader().read_bytes(source("C602.HLP"))
    topic = next(topic for topic in document.topics if topic.context_id == 87)
    assert "  │1+│2ľ│3š│4č│5ť│6ž│7ý│8á│9í│0é│%=│ˇ´│" in topic.uhf_content
    assert "  │≈~│²½│⌠⌡│°¼│¿Æ│φ§│£∩│÷∞│±≡│Øø│¨^│ˇ´│" in topic.uhf_content
    assert "   │Àà│Ää│εè│Ŕŕ│Θτ│Ůů│Üü│¡ì│Ôô│πÞ│«≤│»≥│" in topic.uhf_content
    assert "    │Åå│Σσ│αδ│ΦΩ│Γ¤│Ňň│▀▄│æ█│Ĺĺ│┌└│┐┘│" in topic.uhf_content
    assert "     │Ľľ│Öö│Çò│√ù│ßβ│Ññ│┼µ││─│┴├│┬┤│" in topic.uhf_content
    assert " Slovenská klávesnice ▄" in topic.uhf_content
    assert "�" not in "\n".join(row for topic in document.topics for row in topic.uhf_content)


@pytest.mark.parametrize("name,row_count,cell_count,digest", [
    ("t602_310.hlp", 5802, 187010, "c3913e81f8a55d2553b166787d93f64f5317e3a9e901b233c0ecdddf82921a5c"),
    ("C602.HLP", 6405, 192409, "098c78336e9247b6aef0b70a71f7f79e68b18ff682376a91e3f19f11aebdf1a2"),
])
def test_complete_original_font_corpus_retains_one_cell_per_native_draw_byte(name, row_count, cell_count, digest):
    # Original 24:3783 Draw -> 21:330B MoveStr -> 3:1994 WriteBuf retains
    # every byte in these rows; both drivers have identical 20h..FFh fonts.
    trace = []
    lengths = []
    for topic in _T602Parser(source(name)).parse():
        rows = []
        for start, end, raw in _topic_rows(topic):
            text = _decode_line(raw)
            assert len(text) == len(raw) and "�" not in text
            lengths.append(len(raw))
            rows.append([start, end, text])
        trace.append([topic.offset, rows])
    assert len(lengths) == row_count and sum(lengths) == cell_count
    assert hashlib.sha256(json.dumps(trace, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() == digest


@pytest.mark.parametrize("text,wrap,width,expected", [
    (b"one two three\r", False, 6, [(0, 14, b"one two three")]),
    (b"one two three\r", True, 6, [(0, 4, b"one "), (4, 8, b"two "), (8, 14, b"three")]),
    (b"\r\r", True, 78, [(0, 1, b""), (1, 2, b"")]),
    (b"abcdefghijklmnop", True, 6, [(0, 6, b"abcdef"), (6, 12, b"ghijkl"), (12, 16, b"mnop")]),
    (b"abc\xffdef ghi", True, 6, [(0, 6, b"abc\xffde"), (6, 11, b"f ghi")]),
])
def test_paragraph_rows_match_original_getline_controls(text, wrap, width, expected):
    assert list(paragraph_lines(text, wrap, width)) == expected


def test_unrepresentable_pascal_row_is_reported_not_silently_erased():
    assert list(paragraph_lines(b"x" * 255, False, 78))[0][2] == b"x" * 255
    with pytest.raises(ValueError, match="longer than 255"):
        list(paragraph_lines(b"x" * 256, False, 78))


@pytest.mark.parametrize("length", [0, 10, 20, 40, 41, 42, 48, 55, 56])
def test_incomplete_original_file_fails(length):
    with pytest.raises(ValueError):
        T602310Reader().read_bytes(source("t602_310.hlp")[:length])


@pytest.mark.parametrize("field,value,message", [(0, 0, "declared file size"), (4, 0, "outside"),
                                                  (4, 0x01000000, "outside")])
def test_full_width_header_fields_are_validated(field, value, message):
    data = bytearray(source("t602_310.hlp"))
    struct.pack_into("<I", data, data.index(b"\r\n") + 2 + field, value)
    with pytest.raises(ValueError, match=message):
        T602310Reader().read_bytes(bytes(data))


@pytest.mark.parametrize("damage", ["marker", "count-low", "count-high", "short", "extra"])
def test_incomplete_anchor_array_cannot_publish_partial_text(damage):
    data, _, table = help_file([record([(False, b"Title")])])
    changed = bytearray(data)
    match damage:
        case "marker": struct.pack_into("<H", changed, table, 0)
        case "count-low": struct.pack_into("<H", changed, table + 2, 0)
        case "count-high": struct.pack_into("<H", changed, table + 2, 65535)
        case "short": changed.pop()
        case "extra": changed.append(0)
    header = changed.index(b"\r\n") + 2
    struct.pack_into("<I", changed, header, len(changed) - (header + 4))
    with pytest.raises(ValueError, match="Text602/Calc602"):
        T602310Reader().read_bytes(bytes(changed))


@pytest.mark.parametrize("relative", [-28, -1, 1, 2, 7, 8, 999999, 0x01000000])
def test_anchors_never_round_down_to_a_nearby_object(relative):
    data, offsets, table = help_file([record([(False, b"Title")])])
    changed = bytearray(data)
    struct.pack_into("<I", changed, table + 4, offsets[0] + relative)
    with pytest.raises(ValueError, match="Text602/Calc602"):
        T602310Reader().read_bytes(bytes(changed))


@pytest.mark.parametrize("paragraphs,refs", [
    ([(False, b"Short")], [(0, 0, 1)]),
    ([(False, b"Short")], [(0, 6, 1)]),
    ([(False, b"Short")], [(0, 1, 6)]),
    ([(False, b"Short")], [(400, 1, 1)]),
    ([(2, b"Short")], []),
])
def test_invalid_cross_reference_or_wrap_flag_fails(paragraphs, refs):
    data, _, _ = help_file([record(paragraphs, refs)])
    with pytest.raises(ValueError, match="Text602/Calc602"):
        T602310Reader().read_bytes(data)


@pytest.mark.parametrize("bad", [
    struct.pack("<Hh", 10000, -1),
    struct.pack("<HhH", 10000, 1, 40),
    struct.pack("<HhHB", 10000, 1, 100, 1) + b"x",
    struct.pack("<Hhh", 10000, 0, -1),
    struct.pack("<Hhh", 10000, 0, 3) + bytes(5),
])
def test_topic_cannot_borrow_bytes_from_following_topic(bad):
    data, _, _ = help_file([bad, record([(False, b"Next")])])
    with pytest.raises(ValueError, match="Text602/Calc602"):
        T602310Reader().read_bytes(data)


@pytest.mark.parametrize("name,topic_count,paragraph_count,row_count,link_count,rows_digest,refs_digest", [
    ("t602_310.hlp", 188, 1992, 5802, 1170,
     "a50705aac6ecd025d1ad5ed94fc586a32096661b5a98a9d8ba70c096686fd420",
     "e1a41a237da3b951362f5b3132e59c3009794e3bc489d042c94e3db0d86485cd"),
    ("C602.HLP", 275, 2088, 6405, 1065,
     "ed0fc9494bc77285a9b29b32bf7aaee6cf9148467eebee5eb3e1c850640b28ff",
     "2b15d865ac198148283e3d77d1fccb66eebf385bbd4998451e48450a0737ca7f"),
])
def test_every_original_row_and_link_coordinate_matches_bounded_native_execution(
        name, topic_count, paragraph_count, row_count, link_count, rows_digest, refs_digest):
    parsed = _T602Parser(source(name)).parse()
    assert len(parsed) == topic_count
    assert sum(len(topic.paragraphs) for topic in parsed) == paragraph_count
    assert sum(len(topic.crossrefs) for topic in parsed) == link_count
    trace, coordinates = [], []
    for topic in parsed:
        rows = list(_topic_rows(topic))
        trace.append([topic.offset, [[a, b, row.hex()] for a, b, row in rows]])
        refs = []
        for context, offset, length in topic.crossrefs:
            index = next(i for i, (a, b, row) in enumerate(rows) if a < offset <= b)
            refs.append((context, offset - rows[index][0] - 1, index + 1, length))
        coordinates.append([topic.offset, refs])
    assert sum(len(rows) for offset, rows in trace) == row_count
    for values, digest in ((trace, rows_digest), (coordinates, refs_digest)):
        assert hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest() == digest
    document = T602310Reader().read_bytes(source(name))
    assert sum(row.count("[link:topic=") for topic in document.topics for row in topic.uhf_content) == link_count
    ids = {str(topic.context_id) for topic in document.topics}
    assert all(target in ids for topic in document.topics for row in topic.uhf_content
               for target in re.findall(r"\[link:topic=(\d+)\]", row))
    assert document.metadata["display_width"] == 78


def test_original_contexts_shared_objects_and_unindexed_object_are_not_guessed():
    t602 = T602310Reader().read_bytes(source("t602_310.hlp"))
    assert [(t.context_id, t.alias_contexts) for t in t602.topics if t.alias_contexts] == [
        (64, [150]), (120, [151]), (107, [143]),
    ]
    assert next(t for t in t602.topics if t.context_id > 65535).names == ["Blok │ Řádkování"]
    assert t602.topics[0].context_id == 0
    c602 = T602310Reader().read_bytes(source("C602.HLP"))
    assert [(t.context_id, t.alias_contexts) for t in c602.topics if t.alias_contexts] == [(52, [53])]
    assert sum(t.names[0].startswith("Chyba !!") for t in c602.topics) == 122
    assert next(t for t in c602.topics if t.context_id == 276).uhf_content[-1].endswith("okno→ ")
    for name, doc in (("t602_310.hlp", t602), ("C602.HLP", c602)):
        anchors = _T602Parser(source(name)).anchors
        exported = {context for topic in doc.topics for context in [topic.context_id, *topic.alias_contexts]
                    if context <= 65535}
        assert exported == set(anchors)


@pytest.mark.parametrize("name,context", [("t602_310.hlp", 90), ("t602_310.hlp", 144),
                                         ("t602_310.hlp", 301), ("t602_310.hlp", 355),
                                         ("C602.HLP", 70), ("C602.HLP", 133),
                                         ("C602.HLP", 155), ("C602.HLP", 276)])
def test_corruption_in_all_late_table_regions_is_detected(name, context):
    data = bytearray(source(name))
    parser = _T602Parser(data)
    struct.pack_into("<I", data, parser.anchor_offset + 4 + context * 4, 1)
    with pytest.raises(ValueError, match=f"anchor {context} points outside"):
        T602310Reader().read_bytes(bytes(data))


def test_corrupt_late_context_preserves_published_bundles_and_retry_works(tmp_path):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / "Software 602/C602.HLP"
    copy.parent.mkdir(parents=True)
    original = source("C602.HLP")
    copy.write_bytes(original)
    kwargs = {"product_keys": ["software602"], "keep_products": ["software602"]}
    build_help_groups(["software602"], sources, helps, **kwargs)
    published = {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    broken = bytearray(original)
    parser = _T602Parser(original)
    struct.pack_into("<I", broken, parser.anchor_offset + 4 + 276 * 4, 1)
    copy.write_bytes(broken)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["software602"], sources, helps, **kwargs)
    assert published == {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert copy.read_bytes() == broken
    copy.write_bytes(original)
    result = build_help_groups(["software602"], sources, helps, **kwargs)
    assert result["bundles"] == 1
    backup = Path(result["backup"])
    assert published == {p.relative_to(backup): p.read_bytes() for p in backup.rglob("*") if p.is_file()}
