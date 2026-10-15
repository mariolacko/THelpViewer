import struct

import pytest

from thelpviewer.server.converter.readers.bw03 import BW03HelpReader
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


CONTROL_TABLE = bytes(
    [
        0x17, 0x07, 0xE1,
        0x12, 0x07, 0xE2,
        0x13, 0x70, 0xE3,
        0x1F, 0x0F, 0xE4,
        0x08, 0x00, 0xE5,
        0x30, 0x07, 0xE6,
        0x34, 0x07, 0xE7,
        0x02, 0x07, 0xE8,
        0x20, 0x70, 0xE9,
        0x14, 0x70, 0xEA,
        0x03, 0x07, 0xEB,
        0x87, 0x87, 0xEC,
        0x39, 0x70, 0xED,
        0x3F, 0x0F, 0xEE,
        0x74, 0x70, 0xEF,
        0x0F, 0x0F, 0xF0,
    ]
)
RESERVED_DESCRIPTOR_COUNT = 40


def _menu_entry(first_screen: int, hotkey: str, title: str) -> bytes:
    return bytes([first_screen, ord(hotkey)]) + title.encode("cp437").ljust(20, b"\x00")


def _build_bw03_sample(payloads=None) -> bytes:
    payloads = payloads if payloads is not None else [
        b"\xE1# 1\r\n\xE2CODEVIEW (R) HELP SYSTEM\xE1\r\n\xE1Use \xE4ALT+H\xE1 to open help.\r\nSCREEN 1 OF 1 (Introducing Help)\r\n",
        b"# 2\r\nDisplay overview      SCREEN 1 OF 3 (Display Commands)\r\n",
        b"# 3\r\nDisplay detail        SCREEN 2 OF 3 (Display Commands)\r\n",
        b"# 4\r\nDisplay extra         SCREEN 3 OF 3 (Display Commands)\r\n",
    ]
    menu_table = b"".join(
        [
            _menu_entry(0, "I", "Introducing Help"),
            _menu_entry(1, "D", "Display Commands"),
        ]
    )
    screen_count = len(payloads)
    menu_count = 2
    descriptor_offset = 8 + len(menu_table) + len(CONTROL_TABLE)
    payload_offset = descriptor_offset + (RESERVED_DESCRIPTOR_COUNT * 12)

    descriptors: list[bytes] = []
    payload_chunks: list[bytes] = []
    current_offset = payload_offset
    for index, payload in enumerate(payloads):
        descriptors.append(
            struct.pack(
                "<HHII",
                (index + 1) % screen_count,
                screen_count - 1 if index == 0 else index - 1,
                current_offset,
                len(payload),
            )
        )
        payload_chunks.append(payload)
        current_offset += len(payload)

    descriptors.extend([b"\x00" * 12] * (RESERVED_DESCRIPTOR_COUNT - screen_count))

    header = b"BW03" + struct.pack("<HH", screen_count, menu_count)
    return header + menu_table + CONTROL_TABLE + b"".join(descriptors) + b"".join(payload_chunks)


def test_bw03_reader_recovers_inline_footers_and_clickable_category_nodes():
    data = _build_bw03_sample()
    document = BW03HelpReader(source_name="CV.HLP").read_bytes(data)

    assert document.format_name == "bw03"
    assert [topic.names for topic in document.topics] == [
        ["Introducing Help"],
        ["Display Commands"],
        ["Display Commands (2/3)"],
        ["Display Commands (3/3)"],
    ]

    assert [entry.label.decode("cp437") for entry in document.index_entries] == [
        "Introducing Help",
        "Display Commands",
    ]

    assert len(document.contents) == 2
    display_node = document.contents[1]
    assert display_node.label == "Display Commands"
    assert display_node.topic_id == 1
    assert [child.label for child in display_node.children] == [
        "Display Commands (2/3)",
        "Display Commands (3/3)",
    ]
    assert [child.topic_id for child in display_node.children] == [2, 3]

    assert document.metadata["default_palette"] == "cga"
    palettes = document.metadata["palettes"]
    assert palettes["cga"]["aliases"]["bw03_e1_bg"] == 1
    assert palettes["cga"]["aliases"]["bw03_e4_fg"] == 15
    assert palettes["bw03-mono"]["aliases"]["bw03_ef_bg"] == 7

    help_line = next(line for line in document.topics[0].uhf_content if "ALT+H" in line)
    assert "[color:15:1]ALT+H[/color]" in help_line

    payload = HelpJsonRenderer(document).render_document()
    assert payload["default_palette"] == "cga"
    assert sorted(payload["palettes"]) == ["bw03-mono", "cga"]


def _table_offset(data):
    return 8 + struct.unpack_from("<H", data, 6)[0] * 22 + len(CONTROL_TABLE)


def test_descriptor_navigation_is_not_replaced_with_sequential_screen_numbers():
    data = bytearray(_build_bw03_sample())
    table = _table_offset(data)
    struct.pack_into("<HH", data, table, 2, 1)
    struct.pack_into("<HH", data, table + 12, 0, 3)
    document = BW03HelpReader().read_bytes(bytes(data))
    assert [(topic.next_context, topic.prev_context) for topic in document.topics] == [
        (2, 1), (0, 3), (3, 1), (0, 2),
    ]
    assert any(item.label == "Next" and item.topic_id == 2 for item in document.topics[0].nav_items)
    assert any(item.label == "Prev" and item.topic_id == 1 for item in document.topics[0].nav_items)


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4, 40])
def test_small_and_full_native_circular_screen_sets_are_valid(count):
    table = 8 + len(CONTROL_TABLE)
    payload_start = table + RESERVED_DESCRIPTOR_COUNT * 12
    payloads = [f"Screen {i}\r\n".encode() for i in range(count)]
    descriptors = []
    position = payload_start
    for index, payload in enumerate(payloads):
        descriptors.append(struct.pack("<HHII", (index + 1) % count, (index - 1) % count,
                                       position, len(payload)))
        position += len(payload)
    descriptors += [b"\0" * 12] * (RESERVED_DESCRIPTOR_COUNT - count)
    data = b"BW03" + struct.pack("<HH", count, 0) + CONTROL_TABLE + b"".join(descriptors + payloads)
    document = BW03HelpReader().read_bytes(data)
    assert len(document.topics) == count
    assert [topic.raw_lines for topic in document.topics] == [[f"Screen {i}".encode()] for i in range(count)]
    if count:
        assert document.topics[-1].next_context == 0 and document.topics[0].prev_context == count - 1


@pytest.mark.parametrize("change", ["screen-count", "menu-count", "style-code", "duplicate-style",
                                     "menu-target", "next", "prev",
                                     "late-next", "late-prev", "header-payload", "table-payload",
                                     "past-eof", "zero-length", "long-length"])
def test_bad_header_tables_and_all_descriptors_raise_value_error(change):
    data = bytearray(_build_bw03_sample())
    table = _table_offset(data)
    if change == "screen-count":
        struct.pack_into("<H", data, 4, 41)
    elif change == "menu-count":
        struct.pack_into("<H", data, 6, 65535)
    elif change == "style-code":
        data[table - 46] = 0
    elif change == "duplicate-style":
        data[table - 43] = 0xE1
    elif change == "menu-target":
        data[8] = 4
    elif change in ("next", "prev", "late-next", "late-prev"):
        record = table + (36 if change.startswith("late-") else 0)
        struct.pack_into("<H", data, record + (2 if change.endswith("prev") else 0), 4)
    elif change.endswith("payload") or change == "past-eof":
        offset = {"header-payload": 0, "table-payload": table,
                  "past-eof": len(data)}[change]
        struct.pack_into("<I", data, table + 4, offset)
    else:
        struct.pack_into("<I", data, table + 8, 0 if change == "zero-length" else 0xFFFFFFFF)
    with pytest.raises(ValueError, match="BW03"):
        BW03HelpReader().read_bytes(bytes(data))


@pytest.mark.parametrize("cut", [0, 1, 4, 7, 8, 30, 60, 99, 100, 147, 579, 580])
def test_truncated_header_and_reserved_descriptor_area_fail(cut):
    with pytest.raises(ValueError, match="BW03"):
        BW03HelpReader().read_bytes(_build_bw03_sample()[:cut])


@pytest.mark.parametrize("control", [b"\xff", b"\xff\5"])
def test_incomplete_repeat_is_not_a_literal_nbsp_or_partial_row(control):
    data = bytearray(_build_bw03_sample())
    table = _table_offset(data)
    offset, size = struct.unpack_from("<II", data, table + 4)
    data[offset + size - len(control):offset + size] = control
    with pytest.raises(ValueError, match="BW03 screen 0: Truncated BW03 repeat control"):
        BW03HelpReader().read_bytes(bytes(data))


def test_repeat_operands_cannot_be_borrowed_from_following_screen():
    data = bytearray(_build_bw03_sample())
    table = _table_offset(data)
    offset, size = struct.unpack_from("<II", data, table + 4)
    data[offset + size - 1] = 0xFF
    assert data[offset + size:offset + size + 2] == b"# "
    with pytest.raises(ValueError, match="repeat control"):
        BW03HelpReader().read_bytes(bytes(data))


def test_style_triplets_can_be_reordered_without_changing_their_codes():
    original = _build_bw03_sample()
    data = bytearray(original)
    style = _table_offset(data) - len(CONTROL_TABLE)
    data[style:style+48] = b"".join(CONTROL_TABLE[i:i+3] for i in range(45, -1, -3))
    assert BW03HelpReader().read_bytes(bytes(data)).topics == BW03HelpReader().read_bytes(original).topics


def test_unused_slots_and_unindexed_tail_are_not_fabricated_as_topics():
    original = _build_bw03_sample()
    data = bytearray(original)
    table = _table_offset(data)
    data[table+4*12:table+5*12] = b"unknown slot"
    data.extend(b"\r\nUnindexed command summary\r\n\0")
    document = BW03HelpReader().read_bytes(bytes(data))
    assert document.topics[:4] == BW03HelpReader().read_bytes(original).topics
    assert document.topics[4].raw_lines == [b"", b"Unindexed command summary"]
    assert document.contents[-1].label == "Command summary"


@pytest.mark.parametrize("payload,expected", [
    (b"A\xff\3 \xff\2\xc4B\r\n", b"A   \xc4\xc4B"),
    (b"A\xff\0XB\r\n", b"AB"),
    (b"\xff\3\xff\r\n", b"\xff\xff\xff"),
    (b"A\xff\2\0B\r\n", b"A\0\0B"),
])
def test_complete_rle_is_single_pass_and_zero_count_is_valid(payload, expected):
    document = BW03HelpReader().read_bytes(_build_bw03_sample([payload] + [b"Other\r\n"] * 3))
    assert document.topics[0].raw_lines[0] == expected
    if payload == b"A\xff\2\0B\r\n":
        assert document.topics[0].uhf_content == ["[color:7:0]A  B[/color]"]


def test_styles_persist_across_rows_and_reset_at_each_screen():
    document = BW03HelpReader().read_bytes(_build_bw03_sample([
        b"\xe4Bright\r\nStill bright\r\nSame style\0Ignored\r\n", b"Default\r\n", b"Other\r\n", b"Last\r\n",
    ]))
    assert document.topics[0].uhf_content == [
        "[color:15:1]Bright[/color]", "[color:15:1]Still bright[/color]", "[color:15:1]Same style[/color]",
    ]
    assert document.topics[1].uhf_content == ["[color:7:0]Default[/color]"]


def test_absolute_payload_positions_do_not_require_physical_screen_order():
    data = bytearray(_build_bw03_sample())
    table = _table_offset(data)
    first, last = data[table+4:table+12], data[table+40:table+48]
    data[table+4:table+12], data[table+40:table+48] = last, first
    before = BW03HelpReader().read_bytes(_build_bw03_sample())
    after = BW03HelpReader().read_bytes(bytes(data))
    assert after.topics[0].raw_lines == before.topics[3].raw_lines
    assert after.topics[3].raw_lines == before.topics[0].raw_lines
    assert after.topics[0].next_context == 1 and after.topics[3].next_context == 0


@pytest.mark.parametrize("count", [0, 1, 4])
def test_loader_compatible_compact_table_does_not_require_40_reserved_records(count):
    start = 8 + len(CONTROL_TABLE) + count * 12
    payloads = [f"Compact {i}\0".encode() for i in range(count)]
    descriptors = []
    for index, payload in enumerate(payloads):
        descriptors.append(struct.pack("<HHII", (index + 1) % count, (index - 1) % count,
                                       start, len(payload)))
        start += len(payload)
    data = b"BW03" + struct.pack("<HH", count, 0) + CONTROL_TABLE + b"".join(descriptors + payloads)
    document = BW03HelpReader().read_bytes(data)
    assert [topic.raw_lines for topic in document.topics] == [[f"Compact {i}".encode()] for i in range(count)]


def test_nul_ends_screen_and_hides_no_phantom_later_lines_or_bad_controls():
    payloads = [b"Visible\0not a line\xff", b"Other\0", b"Third\0", b"Last\0"]
    document = BW03HelpReader().read_bytes(_build_bw03_sample(payloads))
    assert document.topics[0].raw_lines == [b"Visible"]
    assert document.topics[0].uhf_content == ["[color:7:0]Visible[/color]"]


def test_repeated_style_newline_and_eof_bytes_are_literal_dos_cells():
    payload = b"\xe4A\xff\2\xe1\xff\1\x0a\xff\1\x01\xff\1\x7f\0"
    document = BW03HelpReader().read_bytes(_build_bw03_sample([payload] + [b"Other\0"] * 3))
    assert document.topics[0].raw_lines == [b"A\xe1\xe1\x0a\x01\x7f"]
    assert document.topics[0].uhf_content == ["[color:15:1]Aßß◙☺⌂[/color]"]


def test_summary_pages_are_plain_text_not_screen_rle_or_style_commands():
    data = _build_bw03_sample() + b"First [page]\r\n\x0c\xff\xe1Second\r\n\0ignored\xff"
    document = BW03HelpReader().read_bytes(data)
    assert len(document.topics) == 6
    assert document.topics[4].uhf_content == ["[color:7:0]First [[page][/color]"]
    assert document.topics[5].raw_lines == [b"\xff\xe1Second"]
    assert document.topics[5].uhf_content == ["[color:7:0]\u00a0ßSecond[/color]"]
    assert document.topics[4].next_context == 5 and document.topics[4].prev_context is None
    assert document.topics[5].prev_context == 4 and document.topics[5].next_context is None
    assert [node.topic_id for node in document.contents[-1].children] == [4, 5]
    assert any(entry.label == b"Command summary" and entry.context_id == 4 for entry in document.index_entries)


@pytest.mark.parametrize("tail", [b"No terminator", b"Bad\x1bcontrol\0"])
def test_incomplete_or_unknown_summary_controls_fail_without_partial_export(tail):
    with pytest.raises(ValueError, match="BW03 command[- ]summary"):
        BW03HelpReader().read_bytes(_build_bw03_sample() + tail)


def test_menu_order_is_independent_of_screen_order():
    data = bytearray(_build_bw03_sample())
    data[8:52] = data[30:52] + data[8:30]
    document = BW03HelpReader().read_bytes(bytes(data))
    assert [node.label for node in document.contents] == ["Display Commands", "Introducing Help"]
    assert [node.topic_id for node in document.contents] == [1, 0]
    assert [node.topic_id for node in document.contents[0].children] == [2, 3]
    assert document.topics[0].down_context is None


def test_multiple_menu_labels_may_point_to_the_same_screen():
    data = bytearray(_build_bw03_sample())
    data[30] = 0
    document = BW03HelpReader().read_bytes(bytes(data))
    assert [node.topic_id for node in document.contents] == [0, 0]
    assert [entry.context_id for entry in document.index_entries] == [0, 0]
    assert document.topics[0].names == ["Introducing Help"]
    assert document.topics[0].down_context == 1


def test_custom_high_byte_style_ids_follow_the_dictionary_not_e1_f0_constants():
    data = bytearray(_build_bw03_sample([b"\x80Custom\0"] + [b"Other\0"] * 3))
    table = _table_offset(data)
    data[table - 46] = 0x80
    document = BW03HelpReader().read_bytes(bytes(data))
    assert document.topics[0].raw_lines == [b"Custom"]
    assert document.topics[0].uhf_content == ["[color:7:1]Custom[/color]"]
    assert document.metadata["palettes"]["cga"]["aliases"]["bw03_80_bg"] == 1


def test_a_high_byte_absent_from_dictionary_is_a_printable_oem_glyph():
    document = BW03HelpReader().read_bytes(_build_bw03_sample([b"\xf1\0"] + [b"Other\0"] * 3))
    assert document.topics[0].raw_lines == [b"\xf1"]
    assert document.topics[0].uhf_content == ["[color:7:0]±[/color]"]
