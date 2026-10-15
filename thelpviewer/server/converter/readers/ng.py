"""Reader for Norton Guide .NG binary help files.

Supports Norton Guide (``NG``) and Expert Help (``EH``) databases.
Format reference: https://www.davep.org/norton-guides/file-format/
"""
from __future__ import annotations

from pathlib import Path

from ..base import (
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    PositionedKeyword,
    TopicRecord,
    build_directional_nav_items,
    ensure_document_index,
    extract_nav_items_from_uhf,
    merge_nav_items,
)
from ..codepages import build_decode_table
from ..uhf_markup import (
    UhfLinkSpan,
    UhfStyleSpan,
    format_uhf_link,
    render_uhf_line,
)

# Size of the NG file header in bytes:
#   magic(2) + unknown(2) + unknown(2) + menu_count(2) + title(40) + 5×credit_line(66)
NG_HEADER_SIZE = 2 + 2 + 2 + 2 + 40 + 5 * 66  # = 378

# Sentinel value used for "no pointer" in NG files
_NO_PTR = 0xFFFFFFFF
_OEM_UPPER = {0x81: 0x9A, 0x82: 0x90, 0x84: 0x8E, 0x86: 0x8F,
              0x87: 0x80, 0x91: 0x92, 0x94: 0x99, 0xA4: 0xA5}
_BOX_TRIM_CHARS = " \t\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c\u2580\u2584\u2588\u258c\u2590\u2591\u2592\u2593\u25a0-=|_"


def is_ng_binary(data: bytes) -> bool:
    """Return True if the buffer starts with a Norton Guide magic signature."""
    return len(data) >= 2 and data[:2] in (b"NG", b"EH")


def _decrypt(data: bytes) -> bytes:
    """XOR-decrypt a block of NG data using the fixed key 0x1A."""
    return bytes(b ^ 0x1A for b in data)


def _decode_text(raw: bytes) -> tuple[bytes, bytes]:
    """Decode one bounded string to native character/attribute cells.

    Attribute changes replace one byte, not independent stacked modes.
    NG's native hex routine performs byte arithmetic, even on non-hex input.
    Missing operands use the string's NUL; never borrow another line's bytes.
    """
    cells, attributes = bytearray(), bytearray()
    attribute = 0x07
    index = 0

    def uppercase(value: int) -> int:
        return value - 32 if 0x61 <= value <= 0x7A else _OEM_UPPER.get(value, value)

    def hex_operand() -> int:
        nonlocal index
        result = 0
        for digit in range(2):
            if index >= len(raw):
                return result
            value = uppercase(raw[index])
            index += 1
            if value == 0:
                index = len(raw)
                return result
            nibble = (value - (0x30 if value <= 0x39 else 0x37)) & 0xFF
            result = nibble if digit == 0 else ((result << 4) | nibble) & 0xFF
        return result

    while index < len(raw):
        value = raw[index]
        index += 1
        if value == 0:
            break
        if value == 0xFF:
            if index == len(raw):
                break
            count = raw[index]
            index += 1
            if count == 0:
                break
            cells.extend(b" " * count)
            attributes.extend(bytes([attribute]) * count)
            continue
        if value == 0x5E:
            if index == len(raw):
                break
            code = uppercase(raw[index])
            index += 1
            if code in (0x41, 0x42, 0x4E, 0x52, 0x55):
                requested = hex_operand() if code == 0x41 else {
                    0x42: 0x0F, 0x4E: 0x07, 0x52: 0x70, 0x55: 0x7F,
                }[code]
                attribute = 0x07 if attribute == requested else requested
                continue
            value = hex_operand() if code == 0x43 else code
        cells.append(value)
        attributes.append(attribute)
    return bytes(cells), bytes(attributes)


class NGReader(HelpReaderBase):
    """Parse a Norton Guide .NG binary file into a HelpDocument."""

    def __init__(self, source_name: str = "input.ng", text_encoding: str = "cp437",
                 source_path: str | Path | None = None):
        super().__init__(source_name, text_encoding, source_path)
        self.encoding = text_encoding
        self._glyphs = build_decode_table(text_encoding, "unicode")
        # NG writes literal video cells, not terminal TAB/CR/LF controls.
        for value, glyph in {0: " ", 9: "○", 10: "◙", 13: "♪", 127: "⌂"}.items():
            self._glyphs[value] = glyph

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_ng_binary(data):
            raise ValueError(f"Not a Norton Guide file: {self.source_name}")
        if len(data) < NG_HEADER_SIZE:
            raise ValueError(f"Truncated Norton Guide file header: {self.source_name}")
        menu_count = int.from_bytes(data[6:8], "little")
        title = data[8:48].split(b"\x00", 1)[0].decode(self.encoding, errors="replace").strip()
        credit_lines = []
        for i in range(5):
            start = 48 + i * 66
            line = data[start: start + 66].split(b"\x00", 1)[0].decode(self.encoding, errors="replace").strip()
            credit_lines.append(line)
        topics, index_entries, help_contents_topic_id = self._traverse(data, menu_count)

        return ensure_document_index(HelpDocument(
            format_name="norton-guide",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata={
                "encoding": self.encoding,
                "text_encoding": self.encoding,
                "metadata_already_decoded": True,
                "title": title,
                "credit_lines": credit_lines,
                "help_contents_topic_id": help_contents_topic_id,
            },
            binary_data=data,
        ))

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    @staticmethod
    def _require(entry: bytes, position: int, size: int, record: int, field: str) -> None:
        if not 0 <= position <= position + size <= len(entry):
            raise ValueError(f"Truncated Norton Guide {field} in record at offset {record}")

    def _read_string(self, entry: bytes, position: int, record: int, field: str) -> tuple[bytes, int]:
        self._require(entry, position, 1, record, field)
        end = entry.find(b"\x00", position)
        if end < 0:
            raise ValueError(f"Unterminated Norton Guide {field} in record at offset {record}")
        return entry[position:end], end + 1

    def _traverse(
        self,
        data: bytes,
        menu_count: int,
    ) -> tuple[list[TopicRecord], list[IndexEntry], int | None]:
        """Read every physical record and build the TopicRecord list."""
        topics_by_offset: dict[int, TopicRecord] = {}
        topic_order: list[int] = []
        record_kind: dict[int, str] = {}
        parent_line_by_topic: dict[int, int] = {}
        direct_child_labels: dict[int, str] = {}
        menu_specs: dict[int, tuple[list[int], str, list[bytes]]] = {}

        pointers: list[tuple[int, str, int]] = []
        offset = NG_HEADER_SIZE
        record_index = 0
        while offset < len(data):
            if offset + 26 > len(data):
                raise ValueError(f"Truncated Norton Guide record header at offset {offset}")

            header = _decrypt(data[offset: offset + 26])
            eid = int.from_bytes(header[0:2], "little")
            payload_size = int.from_bytes(header[2:4], "little")
            record_end = offset + 26 + payload_size
            if record_end > len(data):
                raise ValueError(
                    f"Truncated Norton Guide record at offset {offset}: "
                    f"expected {26 + payload_size} bytes"
                )

            if record_index < menu_count:
                if eid != 2:
                    raise ValueError(f"Expected Norton Guide MENU record at offset {offset}, got {eid}")
            elif eid not in (0, 1):
                raise ValueError(f"Unknown Norton Guide entry type {eid} at offset {offset}")

            entry = _decrypt(data[offset:record_end])

            match eid:
                case 2:
                    topic, child_offsets, title, prompt_labels = self._build_menu_topic(
                        entry,
                        offset,
                        is_help_contents=(offset == NG_HEADER_SIZE),
                    )
                    record_kind[offset] = "menu"
                    menu_specs[offset] = (child_offsets, title, prompt_labels)
                    pointers.extend((offset, "menu prompt", target) for target in child_offsets)
                    for child_offset, label in zip(child_offsets, prompt_labels):
                        cleaned = self._clean_label("".join(self._glyphs[value] for value in label))
                        if child_offset not in (0, _NO_PTR) and self._is_usable_label(cleaned):
                            direct_child_labels.setdefault(child_offset, cleaned)
                case 0:
                    topic, child_offsets, child_labels, parent_line = self._build_short_topic(
                        entry,
                        offset,
                        is_help_contents=(offset == NG_HEADER_SIZE),
                    )
                    record_kind[offset] = "short"
                    parent_line_by_topic[offset] = parent_line
                    pointers.extend((offset, "SHORT target", target) for target in child_offsets)
                    pointers.append((offset, "parent", int.from_bytes(header[10:14], "little")))
                    for child_offset, label in child_labels:
                        cleaned = self._clean_label(label)
                        if child_offset not in (0, _NO_PTR) and self._is_usable_label(cleaned):
                            direct_child_labels.setdefault(child_offset, cleaned)
                case _:
                    topic, related_offsets, parent_line = self._build_long_topic(entry, offset)
                    record_kind[offset] = "long"
                    parent_line_by_topic[offset] = parent_line
                    pointers.extend((offset, "See Also", target) for target in related_offsets)
                    for field, start in (("parent", 10), ("previous", 18), ("next", 22)):
                        pointers.append((offset, field, int.from_bytes(header[start:start + 4], "little")))

            topics_by_offset[offset] = topic
            topic_order.append(offset)
            offset = record_end
            record_index += 1

        if record_index < menu_count:
            raise ValueError("Norton Guide menu count exceeds the physical record count")
        for source, field, target in pointers:
            if target in (0, _NO_PTR) or (field == "next" and target == len(data)):
                continue
            if target not in topics_by_offset:
                raise ValueError(f"Norton Guide {field} in record at offset {source} "
                                 f"does not address a record: {target}")

        self._finalize_menu_topics(topics_by_offset, menu_specs)
        self._resolve_topic_names(topics_by_offset, topic_order, record_kind, parent_line_by_topic, direct_child_labels)

        valid_topic_ids = set(topics_by_offset)
        for topic in topics_by_offset.values():
            # A few compilers use the byte immediately after the final record
            # as the terminal NEXT value instead of 0 or 0xFFFFFFFF.
            if topic.next_context == len(data):
                topic.next_context = None
            topic.nav_items = merge_nav_items(
                extract_nav_items_from_uhf(topic.uhf_content, valid_topic_ids=valid_topic_ids),
                build_directional_nav_items(topic),
            )

        topics = [topics_by_offset[offset] for offset in topic_order]
        index_entries = self._build_index_entries(topics)
        help_contents_topic_id = NG_HEADER_SIZE if topic_order else None
        return topics, index_entries, help_contents_topic_id

    # ------------------------------------------------------------------
    # Block processors
    # ------------------------------------------------------------------

    def _build_menu_topic(
        self,
        entry: bytes,
        self_offset: int,
        is_help_contents: bool,
    ) -> tuple[TopicRecord, list[int], str, list[bytes]]:
        """Parse a MENU entry into a TopicRecord."""
        stored_count = int.from_bytes(entry[4:6], "little")
        if stored_count < 1:
            raise ValueError(f"Invalid Norton Guide MENU count in record at offset {self_offset}")
        prompt_count = stored_count - 1
        self._require(entry, 26, prompt_count * 4, self_offset, "MENU pointer table")
        child_offsets: list[int] = []
        for i in range(prompt_count):
            base = 26 + i * 4
            child_offsets.append(int.from_bytes(entry[base: base + 4], "little"))

        title, prompt_labels = self._extract_menu_text(entry, prompt_count, self_offset)
        topic = TopicRecord(
            context_id=self_offset,
            raw_lines=[],
            positional_keywords=[],
            is_help_contents=is_help_contents,
            names=[title] if title else [],
            uhf_content=[],
        )
        return topic, child_offsets, title, prompt_labels

    def _build_short_topic(
        self,
        entry: bytes,
        self_offset: int,
        is_help_contents: bool,
    ) -> tuple[TopicRecord, list[int], list[tuple[int, str]], int]:
        """Parse a SHORT entry into a TopicRecord (menu/index page)."""
        line_count = int.from_bytes(entry[4:6], "little")
        parent_line = int.from_bytes(entry[8:10], "little")
        parent_offset = int.from_bytes(entry[10:14], "little")
        table_end = 26 + line_count * 6
        self._require(entry, 26, line_count * 6, self_offset, "SHORT descriptor table")

        child_offsets: list[int] = []
        child_labels: list[tuple[int, str]] = []
        raw_lines: list[bytes] = []
        uhf_lines: list[str] = []
        pos_kws: list[PositionedKeyword] = []

        for i in range(line_count):
            base = 26 + i * 6
            text_offset = int.from_bytes(entry[base: base + 2], "little")
            child_offset = int.from_bytes(entry[base + 2: base + 6], "little")
            child_offsets.append(child_offset)

            text_offset += 26  # Relative to the payload start, after the fixed header.
            if text_offset < table_end:
                raise ValueError(f"Norton Guide SHORT text overlaps its descriptor table "
                                 f"in record at offset {self_offset}")
            raw_line, _end = self._read_string(entry, text_offset, self_offset, "SHORT line")

            expanded, visible_text, style_spans = self._text_line(raw_line)
            link_spans: list[UhfLinkSpan] = []
            label_text = ""
            if child_offset not in (0, _NO_PTR):
                # A SHORT destination belongs to its whole selectable row.
                link_end = len(visible_text)
                label_text = self._clean_label(visible_text[:link_end])
                line_num = len(raw_lines) + 1
                pos_kws.append(PositionedKeyword(
                    target_context=child_offset,
                    line=line_num,
                    first_column=1,
                    last_column=link_end,
                ))
                if link_end > 0:
                    link_spans.append(UhfLinkSpan(start=0, end=link_end, target_context=child_offset))
            else:
                label_text = self._clean_label(visible_text)

            raw_lines.append(expanded)
            uhf_lines.append(
                render_uhf_line(
                    visible_text,
                    style_spans=style_spans,
                    link_spans=link_spans,
                    link_formatter=_format_ng_link,
                )
            )
            if child_offset not in (0, _NO_PTR) and label_text:
                child_labels.append((child_offset, label_text))

        first_text = self._first_visible_label(raw_lines)
        up = parent_offset if parent_offset not in (0, _NO_PTR) else None

        return TopicRecord(
            context_id=self_offset,
            raw_lines=raw_lines,
            positional_keywords=pos_kws,
            is_help_contents=is_help_contents,
            up_context=up,
            names=[first_text] if first_text else [],
            uhf_content=uhf_lines,
        ), child_offsets, child_labels, parent_line

    def _build_long_topic(
        self,
        entry: bytes,
        self_offset: int,
    ) -> tuple[TopicRecord, list[int], int]:
        """Parse a LONG entry into a TopicRecord (content page)."""
        line_count = int.from_bytes(entry[4:6], "little")
        see_also_flag = int.from_bytes(entry[6:8], "little")
        parent_line = int.from_bytes(entry[8:10], "little")
        parent_offset = int.from_bytes(entry[10:14], "little")
        prev_offset = int.from_bytes(entry[18:22], "little")
        next_offset = int.from_bytes(entry[22:26], "little")

        raw_lines: list[bytes] = []
        uhf_lines: list[str] = []
        text_off = 26
        for _ in range(line_count):
            source_line, text_off = self._read_string(entry, text_off, self_offset, "LONG line")
            expanded, visible_text, style_spans = self._text_line(source_line)
            raw_lines.append(expanded)
            uhf_lines.append(render_uhf_line(visible_text, style_spans=style_spans))

        pos_kws: list[PositionedKeyword] = []
        see_also_targets: list[int] = []
        if see_also_flag:
            self._require(entry, text_off, 2, self_offset, "See Also count")
            sa_count = int.from_bytes(entry[text_off: text_off + 2], "little")
            text_off += 2
            self._require(entry, text_off, sa_count * 4, self_offset, "See Also pointer table")
            sa_ptrs: list[int] = []
            for _ in range(sa_count):
                ptr = int.from_bytes(entry[text_off: text_off + 4], "little")
                sa_ptrs.append(ptr)
                if ptr not in (0, _NO_PTR):
                    see_also_targets.append(ptr)
                text_off += 4
            sa_labels: list[bytes] = []
            for _ in range(sa_count):
                label, text_off = self._read_string(entry, text_off, self_offset, "See Also label")
                sa_labels.append(label)

            if sa_count:
                raw_lines.append(b"")
                uhf_lines.append("")
                line_bytes = bytearray(b"See also: ")
                positions: list[tuple[int, int, int]] = []
                for lbl, ptr in zip(sa_labels, sa_ptrs):
                    start = len(line_bytes)
                    line_bytes.extend(lbl)
                    end = len(line_bytes)
                    if ptr not in (0, _NO_PTR):
                        positions.append((start, end, ptr))
                    line_bytes.extend(b"  ")
                raw_lines.append(bytes(line_bytes))
                uhf_lines.append(
                    render_uhf_line(
                        "".join(self._glyphs[value] for value in line_bytes),
                        link_spans=[
                            UhfLinkSpan(start=start, end=end, target_context=ptr)
                            for start, end, ptr in positions
                        ],
                        link_formatter=_format_ng_link,
                    )
                )
                sa_line_num = len(raw_lines)
                for start, end, ptr in positions:
                    pos_kws.append(PositionedKeyword(
                        target_context=ptr,
                        line=sa_line_num,
                        first_column=start + 1,
                        last_column=end,
                    ))

        first_text = self._first_visible_label(raw_lines)
        up = parent_offset if parent_offset not in (0, _NO_PTR) else None
        prev_context = prev_offset if prev_offset not in (0, _NO_PTR) else None
        next_context = next_offset if next_offset not in (0, _NO_PTR) else None

        topic = TopicRecord(
            context_id=self_offset,
            raw_lines=raw_lines,
            positional_keywords=pos_kws,
            is_help_contents=False,
            up_context=up,
            prev_context=prev_context,
            next_context=next_context,
            names=[first_text] if first_text else [],
            uhf_content=uhf_lines,
        )
        return topic, see_also_targets, parent_line

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _finalize_menu_topics(
        self,
        topics_by_offset: dict[int, TopicRecord],
        menu_specs: dict[int, tuple[list[int], str, list[bytes]]],
    ) -> None:
        """Keep authored MENU cells and source slot order, not guessed labels."""
        for offset, (child_offsets, title, prompt_labels) in menu_specs.items():
            topic = topics_by_offset[offset]
            raw_lines: list[bytes] = []
            uhf_lines: list[str] = []
            pos_kws: list[PositionedKeyword] = []
            resolved_labels: list[str] = []

            for index, child_offset in enumerate(child_offsets):
                raw = prompt_labels[index]
                label = "".join(self._glyphs[value] for value in raw)
                raw_lines.append(raw)
                if child_offset not in (0, _NO_PTR):
                    line_num = len(raw_lines)
                    pos_kws.append(PositionedKeyword(
                        target_context=child_offset,
                        line=line_num,
                        first_column=1,
                        last_column=len(label),
                    ))
                    uhf_lines.append(
                        render_uhf_line(
                            label,
                            link_spans=[UhfLinkSpan(start=0, end=len(label), target_context=child_offset)],
                            link_formatter=_format_ng_link,
                        )
                    )
                else:
                    uhf_lines.append(render_uhf_line(label))
                cleaned = self._clean_label(label)
                if self._is_usable_label(cleaned):
                    resolved_labels.append(cleaned)

            topic.raw_lines = raw_lines
            topic.uhf_content = uhf_lines
            topic.positional_keywords = pos_kws
            if title:
                topic.names = self._merge_primary_name(topic.names, title)
            elif resolved_labels and not topic.names:
                topic.names = [resolved_labels[0]]

    def _resolve_topic_names(
        self,
        topics_by_offset: dict[int, TopicRecord],
        topic_order: list[int],
        record_kind: dict[int, str],
        parent_line_by_topic: dict[int, int],
        direct_child_labels: dict[int, str],
    ) -> None:
        """Prefer the visible parent label for LONG topics."""
        for offset in topic_order:
            if record_kind.get(offset) != "long":
                continue

            topic = topics_by_offset[offset]
            label = self._clean_label(direct_child_labels.get(offset, ""))
            if not label:
                parent_topic = topics_by_offset.get(topic.up_context or 0)
                parent_line = parent_line_by_topic.get(offset, 0)
                label = self._label_from_parent_line(parent_topic, parent_line)
            if self._is_usable_label(label):
                topic.names = self._merge_primary_name(topic.names, label)

    def _build_index_entries(self, topics: list[TopicRecord]) -> list[IndexEntry]:
        """Build one visible index label for every parsed topic."""
        entries: list[IndexEntry] = []
        for topic in topics:
            label = self._topic_label(topic)
            if not label:
                continue
            entries.append(
                IndexEntry(
                    label=label.encode(self.encoding, errors="replace"),
                    context_id=topic.context_id,
                )
            )
        return entries

    # ------------------------------------------------------------------
    # Text / label helpers
    # ------------------------------------------------------------------

    def _text_line(self, raw: bytes) -> tuple[bytes, str, list[UhfStyleSpan]]:
        cells, attributes = _decode_text(raw)
        spans: list[UhfStyleSpan] = []
        start = 0
        while start < len(cells):
            attribute = attributes[start]
            end = start + 1
            while end < len(cells) and attributes[end] == attribute:
                end += 1
            match attribute:
                case 0x07:
                    pass  # Normal uses the shared viewer's body palette.
                case 0x0F:
                    spans.append(UhfStyleSpan(start, end, bold=True))
                case 0x70:
                    spans.append(UhfStyleSpan(start, end, reverse=True))
                case 0x7F:
                    spans.append(UhfStyleSpan(start, end, underline=True))
                case _:
                    spans.append(UhfStyleSpan(start, end, fg=attribute & 15, bg=attribute >> 4))
            start = end
        return cells, "".join(self._glyphs[value] for value in cells), spans

    def _extract_menu_text(self, entry: bytes, prompt_count: int, record: int) -> tuple[str, list[bytes]]:
        """Read the native eight-byte descriptors and payload-relative text."""
        table_start = 26 + int.from_bytes(entry[6:8], "little")
        if table_start < 26 + prompt_count * 4:
            raise ValueError(f"Norton Guide MENU descriptors overlap the pointer table "
                             f"in record at offset {record}")
        self._require(entry, table_start, (prompt_count + 1) * 8,
                      record, "MENU descriptor table")
        text_start = table_start + (prompt_count + 1) * 8
        title, _end = self._read_string(entry, text_start, record, "MENU title")
        prompts: list[bytes] = []
        for index in range(prompt_count + 1):
            descriptor = table_start + index * 8
            text_offset = 26 + int.from_bytes(entry[descriptor:descriptor + 2], "little")
            if text_offset < text_start:
                raise ValueError(f"Norton Guide MENU text overlaps its descriptor table "
                                 f"in record at offset {record}")
            label, _end = self._read_string(entry, text_offset, record, "MENU prompt")
            if index < prompt_count:
                prompts.append(label)
            elif label:
                raise ValueError(f"Invalid Norton Guide MENU terminator in record at offset {record}")
        return self._clean_label("".join(self._glyphs[value] for value in title)), prompts

    @staticmethod
    def _clean_label(text: str) -> str:
        cleaned = text.replace("\x00", "").strip()
        cleaned = cleaned.strip(_BOX_TRIM_CHARS)
        return " ".join(cleaned.split())

    def _label_from_parent_line(
        self,
        parent_topic: TopicRecord | None,
        parent_line: int,
    ) -> str:
        if parent_topic is None or parent_line <= 0 or parent_line > len(parent_topic.raw_lines):
            return ""
        return self._clean_label("".join(self._glyphs[value] for value in parent_topic.raw_lines[parent_line - 1]))

    def _topic_label(self, topic: TopicRecord) -> str:
        if topic.names:
            cleaned = self._clean_label(topic.names[0])
            if self._is_usable_label(cleaned):
                return cleaned
        return self._first_visible_label(topic.raw_lines)

    def _first_visible_label(self, raw_lines: list[bytes]) -> str:
        for raw_line in raw_lines:
            if not raw_line.strip():
                continue
            cleaned = self._clean_label("".join(self._glyphs[value] for value in raw_line))
            if self._is_usable_label(cleaned):
                return cleaned
        return ""

    @staticmethod
    def _merge_primary_name(existing: list[str], primary: str) -> list[str]:
        cleaned = primary.strip()
        if not cleaned:
            return list(existing)
        rest = [name for name in existing if name.strip() and name.strip() != cleaned]
        return [cleaned, *rest]

    @staticmethod
    def _is_usable_label(text: str) -> bool:
        if not text:
            return False
        if any(ord(char) < 32 for char in text):
            return False
        return any(char.isalnum() for char in text)


def _format_ng_link(link: UhfLinkSpan, label: str) -> str:
    """Render one NG internal pointer as a UHF link."""
    return format_uhf_link(label, topic_id=link.target_context, line=link.target_line)
