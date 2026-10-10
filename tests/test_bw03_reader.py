import struct

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


def _build_bw03_sample() -> bytes:
    payloads = [
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
                index + 1,
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