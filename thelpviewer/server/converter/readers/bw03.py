"""Reader for older Microsoft BW03 help files used by CodeView-era tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct

from ..base import (
    ContentNode,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    TopicRecord,
    build_directional_nav_items,
    ensure_document_index,
)
from ..uhf_markup import UhfStyleSpan, render_uhf_line


BW03_SIGNATURE = b"BW03"
MENU_ENTRY_SIZE = 22
SCREEN_DESCRIPTOR_SIZE = 12
STYLE_TABLE_SIZE = 48
STYLE_CONTROL_BYTES = frozenset(range(0xE1, 0xF1))
SCREEN_FOOTER_RE = re.compile(r"SCREEN\s+(\d+)\s+OF\s+(\d+)\s+\((.+)\)\s*$", re.IGNORECASE)
BW03_MONO_COLORS = {
    "0": "#000000",
    "7": "#aaaaaa",
    "8": "#555555",
    "15": "#ffffff",
}


def is_bw03_binary(data: bytes) -> bool:
    """Return True when *data* starts with the BW03 signature."""
    return data.startswith(BW03_SIGNATURE)


@dataclass(frozen=True, slots=True)
class _MenuEntry:
    first_screen: int
    hotkey: str
    title: str


@dataclass(frozen=True, slots=True)
class _ScreenDescriptor:
    screen_number: int
    prev_index: int
    offset: int
    length: int


@dataclass(frozen=True, slots=True)
class _StyleEntry:
    color_attr: int
    mono_attr: int
    color_fg: int
    color_bg: int
    mono_fg: int
    mono_bg: int


def _decode_menu_title(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("cp437", errors="replace").strip()


def _parse_menu_entries(data: bytes, menu_count: int) -> list[_MenuEntry]:
    entries: list[_MenuEntry] = []
    offset = 8
    for _ in range(menu_count):
        chunk = data[offset:offset + MENU_ENTRY_SIZE]
        if len(chunk) < MENU_ENTRY_SIZE:
            raise ValueError("Incomplete BW03 menu table")
        first_screen = chunk[0]
        hotkey = bytes([chunk[1]]).decode("cp437", errors="replace")
        title = _decode_menu_title(chunk[2:])
        entries.append(_MenuEntry(first_screen=first_screen, hotkey=hotkey, title=title))
        offset += MENU_ENTRY_SIZE
    return entries


def _looks_like_descriptor_table(data: bytes, offset: int, screen_count: int) -> bool:
    if offset < 0 or offset + (screen_count * SCREEN_DESCRIPTOR_SIZE) > len(data):
        return False

    previous_offset = -1
    for index in range(min(screen_count, 4)):
        chunk = data[offset + (index * SCREEN_DESCRIPTOR_SIZE): offset + ((index + 1) * SCREEN_DESCRIPTOR_SIZE)]
        if len(chunk) < SCREEN_DESCRIPTOR_SIZE:
            return False
        screen_number, prev_index, payload_offset, payload_length = struct.unpack_from("<HHII", chunk, 0)
        if screen_number != index + 1:
            return False
        if payload_offset <= 0 or payload_length <= 0:
            return False
        if payload_offset + payload_length > len(data):
            return False
        if payload_offset <= previous_offset:
            return False
        previous_offset = payload_offset

    first_screen_number, first_prev_index, _, _ = struct.unpack_from("<HHII", data, offset)
    return first_screen_number == 1 and first_prev_index in {0, max(screen_count - 1, 0)}


def _descriptor_table_offset(data: bytes, menu_count: int, screen_count: int) -> int:
    base = 8 + (menu_count * MENU_ENTRY_SIZE)
    for candidate in range(base, base + 64):
        if _looks_like_descriptor_table(data, candidate, screen_count):
            return candidate
    raise ValueError("Unable to locate BW03 screen descriptor table")


def _parse_screen_descriptors_at_offset(data: bytes, screen_count: int, offset: int) -> list[_ScreenDescriptor]:
    entries: list[_ScreenDescriptor] = []
    for index in range(screen_count):
        chunk = data[offset + (index * SCREEN_DESCRIPTOR_SIZE): offset + ((index + 1) * SCREEN_DESCRIPTOR_SIZE)]
        if len(chunk) < SCREEN_DESCRIPTOR_SIZE:
            raise ValueError("Incomplete BW03 screen descriptor table")
        screen_number, prev_index, payload_offset, payload_length = struct.unpack_from("<HHII", chunk, 0)
        if payload_offset <= 0 or payload_length <= 0:
            raise ValueError("Invalid BW03 screen descriptor")
        entries.append(
            _ScreenDescriptor(
                screen_number=screen_number,
                prev_index=prev_index,
                offset=payload_offset,
                length=payload_length,
            )
        )
    return entries


def _parse_screen_descriptors(data: bytes, screen_count: int, menu_count: int) -> list[_ScreenDescriptor]:
    offset = _descriptor_table_offset(data, menu_count, screen_count)
    return _parse_screen_descriptors_at_offset(data, screen_count, offset)


def _attr_colors(attr: int) -> tuple[int, int]:
    return attr & 0x0F, (attr >> 4) & 0x0F


def _parse_style_table(data: bytes, menu_count: int, descriptor_offset: int) -> dict[int, _StyleEntry]:
    table_offset = 8 + (menu_count * MENU_ENTRY_SIZE)
    chunk = data[table_offset:descriptor_offset]
    if len(chunk) != STYLE_TABLE_SIZE or len(chunk) % 3 != 0:
        return {}

    entries: dict[int, _StyleEntry] = {}
    for pos in range(0, len(chunk), 3):
        color_attr, mono_attr, style_code = chunk[pos:pos + 3]
        if style_code not in STYLE_CONTROL_BYTES:
            continue
        color_fg, color_bg = _attr_colors(color_attr)
        mono_fg, mono_bg = _attr_colors(mono_attr)
        entries[style_code] = _StyleEntry(
            color_attr=color_attr,
            mono_attr=mono_attr,
            color_fg=color_fg,
            color_bg=color_bg,
            mono_fg=mono_fg,
            mono_bg=mono_bg,
        )
    return entries


def _build_style_spans(styles: list[tuple[int, int] | None]) -> list[UhfStyleSpan]:
    spans: list[UhfStyleSpan] = []
    start = 0
    while start < len(styles):
        style = styles[start]
        end = start + 1
        while end < len(styles) and styles[end] == style:
            end += 1
        if style is not None:
            fg, bg = style
            spans.append(UhfStyleSpan(start=start, end=end, fg=fg, bg=bg))
        start = end
    return spans


def _decode_screen_payload(
    payload: bytes,
    style_table: dict[int, _StyleEntry],
) -> tuple[list[bytes], list[str]]:
    raw_lines: list[bytes] = []
    uhf_lines: list[str] = []
    visible_bytes = bytearray()
    visible_styles: list[tuple[int, int] | None] = []
    current_style = style_table.get(0xE1)

    def flush_line() -> None:
        raw_line = bytes(visible_bytes)
        text = raw_line.decode("cp437", errors="replace")
        raw_lines.append(raw_line)
        uhf_lines.append(render_uhf_line(text, style_spans=_build_style_spans(visible_styles)))
        visible_bytes.clear()
        visible_styles.clear()

    def append_value(value: int) -> None:
        nonlocal current_style
        if value in STYLE_CONTROL_BYTES:
            current_style = style_table.get(value)
            return
        if value == 0x00 or value == 0x0A:
            flush_line()
            return
        if value == 0x0D:
            return
        visible_bytes.append(value)
        if current_style is None:
            visible_styles.append(None)
            return
        visible_styles.append((current_style.color_fg, current_style.color_bg))

    pos = 0
    while pos < len(payload):
        value = payload[pos]
        if value == 0xFF and pos + 2 < len(payload):
            count = payload[pos + 1]
            repeated = payload[pos + 2]
            for _ in range(count):
                append_value(repeated)
            pos += 3
            continue
        append_value(value)
        pos += 1

    if visible_bytes or not raw_lines:
        flush_line()

    while raw_lines and raw_lines[-1] == b"":
        raw_lines.pop()
        uhf_lines.pop()
    if not raw_lines:
        return [b""], [""]
    return raw_lines, uhf_lines


def _build_bw03_palettes(style_table: dict[int, _StyleEntry]) -> dict[str, object]:
    if not style_table:
        return {}

    color_aliases: dict[str, int] = {}
    mono_aliases: dict[str, int] = {}
    mono_indices: set[int] = set()
    for style_code, entry in sorted(style_table.items()):
        alias_prefix = f"bw03_{style_code:02x}"
        color_aliases[f"{alias_prefix}_fg"] = entry.color_fg
        color_aliases[f"{alias_prefix}_bg"] = entry.color_bg
        mono_aliases[f"{alias_prefix}_fg"] = entry.mono_fg
        mono_aliases[f"{alias_prefix}_bg"] = entry.mono_bg
        mono_indices.add(entry.mono_fg)
        mono_indices.add(entry.mono_bg)

    palettes: dict[str, object] = {
        "cga": {
            "type": "indexed",
            "aliases": color_aliases,
        },
        "bw03-mono": {
            "type": "indexed",
            "colors": {
                str(index): BW03_MONO_COLORS[str(index)]
                for index in sorted(mono_indices)
                if str(index) in BW03_MONO_COLORS
            },
            "aliases": mono_aliases,
        },
    }
    return palettes


def _expand_screen_payload(payload: bytes) -> bytes:
    out = bytearray()
    pos = 0
    while pos < len(payload):
        value = payload[pos]
        if value == 0xFF and pos + 2 < len(payload):
            count = payload[pos + 1]
            repeated = payload[pos + 2]
            out.extend(bytes([repeated]) * count)
            pos += 3
            continue
        if value in STYLE_CONTROL_BYTES:
            pos += 1
            continue
        if value == 0x00:
            out.extend(b"\r\n")
            pos += 1
            continue
        out.append(value)
        pos += 1
    return bytes(out)


def _split_raw_lines(payload: bytes) -> list[bytes]:
    normalized = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = [line for line in normalized.split(b"\n")]
    while lines and not lines[-1]:
        lines.pop()
    return lines or [b""]


def _visible_lines(raw_lines: list[bytes]) -> list[str]:
    return [line.decode("cp437", errors="replace").rstrip() for line in raw_lines]


def _find_screen_footer(lines: list[str]) -> tuple[int, int, str] | None:
    for line in reversed(lines):
        match = SCREEN_FOOTER_RE.search(line)
        if match:
            page = int(match.group(1))
            total = int(match.group(2))
            category = match.group(3).strip()
            return page, total, category
    return None


def _topic_name(category: str, page: int, total: int) -> str:
    if total <= 1:
        return category
    return f"{category} ({page}/{total})"


def _document_title(topics: list[TopicRecord]) -> str | None:
    for topic in topics[:1]:
        for raw_line in topic.raw_lines:
            text = raw_line.decode("cp437", errors="replace").strip()
            if not text:
                continue
            if text.startswith("# "):
                continue
            if text.upper().startswith("SCREEN "):
                continue
            if all(ch in " -_=|/\\─│┬┴┼┤├┌┐└┘" for ch in text):
                continue
            return text
    return None


def _menu_ranges(menu_entries: list[_MenuEntry], screen_count: int) -> list[tuple[_MenuEntry, range]]:
    ranges: list[tuple[_MenuEntry, range]] = []
    for index, entry in enumerate(menu_entries):
        start = entry.first_screen
        if start >= screen_count:
            continue
        end = screen_count
        if index + 1 < len(menu_entries):
            end = min(menu_entries[index + 1].first_screen, screen_count)
        if end <= start:
            continue
        ranges.append((entry, range(start, end)))
    return ranges


def _build_contents_tree(menu_entries: list[_MenuEntry], topics: list[TopicRecord]) -> list[ContentNode]:
    """Build a TOC tree from the BW03 category menu table."""
    nodes: list[ContentNode] = []
    for menu_entry, screen_range in _menu_ranges(menu_entries, len(topics)):
        if not menu_entry.title:
            continue

        topic_nodes: list[ContentNode] = []
        for topic_index in screen_range:
            if not (0 <= topic_index < len(topics)):
                continue
            topic = topics[topic_index]
            label = topic.names[0].strip() if topic.names else f"Screen {topic_index + 1}"
            if not label:
                label = f"Screen {topic_index + 1}"
            topic_nodes.append(ContentNode(label=label, topic_id=topic_index))

        if not topic_nodes:
            continue
        if len(topic_nodes) == 1 and topic_nodes[0].label == menu_entry.title:
            nodes.append(ContentNode(
                label=menu_entry.title,
                hotkey=menu_entry.hotkey,
                topic_id=topic_nodes[0].topic_id,
            ))
            continue

        child_nodes = topic_nodes
        first_topic_id = topic_nodes[0].topic_id
        if (
            len(topic_nodes) > 1
            and topic_nodes[0].topic_id is not None
            and topic_nodes[0].label == menu_entry.title
        ):
            child_nodes = topic_nodes[1:]

        nodes.append(ContentNode(
            label=menu_entry.title,
            hotkey=menu_entry.hotkey,
            topic_id=first_topic_id,
            children=child_nodes,
        ))
    return nodes


class BW03HelpReader(HelpReaderBase):
    """Parse one BW03 help file into the shared document model."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_bw03_binary(data):
            raise ValueError("Not a BW03 help file.")
        if len(data) < 8:
            raise ValueError("Incomplete BW03 header.")

        screen_count = struct.unpack_from("<H", data, 4)[0]
        menu_count = struct.unpack_from("<H", data, 6)[0]
        menu_entries = _parse_menu_entries(data, menu_count)
        descriptor_offset = _descriptor_table_offset(data, menu_count, screen_count)
        style_table = _parse_style_table(data, menu_count, descriptor_offset)
        descriptors = _parse_screen_descriptors_at_offset(data, screen_count, descriptor_offset)

        topics: list[TopicRecord] = []
        for index, descriptor in enumerate(descriptors):
            end = descriptor.offset + descriptor.length
            if end > len(data):
                raise ValueError("BW03 screen payload points outside the file.")
            raw_lines, uhf_lines = _decode_screen_payload(data[descriptor.offset:end], style_table)
            visible = _visible_lines(raw_lines)
            footer = _find_screen_footer(visible)

            names: list[str] = []
            index_terms: list[bytes] = []
            if footer is not None:
                page, total, category = footer
                names.append(_topic_name(category, page, total))
                index_terms.append(category.encode("cp437", errors="replace"))

            topics.append(
                TopicRecord(
                    context_id=index,
                    raw_lines=raw_lines,
                    uhf_content=uhf_lines,
                    index_terms=index_terms,
                    prev_context=descriptor.prev_index if 0 <= descriptor.prev_index < screen_count else None,
                    next_context=(index + 1) % screen_count if screen_count else None,
                    names=names,
                )
            )

        index_entries: list[IndexEntry] = []
        for menu_entry, screen_range in _menu_ranges(menu_entries, screen_count):
            first_context = screen_range.start
            if not (0 <= first_context < len(topics)):
                continue
            if topics[first_context].names:
                topics[first_context].names[0] = menu_entry.title
            elif menu_entry.title:
                topics[first_context].names.append(menu_entry.title)
            if menu_entry.title:
                index_entries.append(
                    IndexEntry(
                        label=menu_entry.title.encode("cp437", errors="replace"),
                        context_id=first_context,
                    )
                )
            for local_index, topic_index in enumerate(screen_range):
                topic = topics[topic_index]
                if local_index > 0:
                    topic.up_context = topic_index - 1
                if local_index + 1 < len(screen_range):
                    topic.down_context = topic_index + 1

        for topic in topics:
            topic.nav_items = build_directional_nav_items(topic)

        metadata: dict[str, object] = {
            "signature": "BW03",
            "screen_count": screen_count,
            "menu_count": menu_count,
            "menu_titles": [entry.title for entry in menu_entries],
            "text_encoding": "cp437",
            "source_family": "microsoft-bw03",
        }
        palettes = _build_bw03_palettes(style_table)
        if palettes:
            metadata["default_palette"] = "cga"
            metadata["palettes"] = palettes
        title = _document_title(topics)
        if title:
            metadata["title"] = title
            metadata["description"] = title

        return ensure_document_index(
            HelpDocument(
                format_name="bw03",
                source_name=self.source_name,
                topics=topics,
                index_entries=index_entries,
                contents=_build_contents_tree(menu_entries, topics),
                metadata=metadata,
                binary_data=data,
            )
        )


def read_bw03_path(path: str | Path) -> HelpDocument:
    """Convenience helper used by ad-hoc scripts."""
    source_path = Path(path)
    return BW03HelpReader(source_name=source_path.name, source_path=source_path).read_path(source_path)
