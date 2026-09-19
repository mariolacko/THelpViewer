"""Reader for Norton Guide .NG binary help files.

Supports Norton Guide (``NG``) and Expert Help (``EH``) databases.
Format reference: https://www.davep.org/norton-guides/file-format/
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

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
_BOX_TRIM_CHARS = " \t\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c\u2580\u2584\u2588\u258c\u2590\u2591\u2592\u2593\u25a0-=|_"


def is_ng_binary(data: bytes) -> bool:
    """Return True if the buffer starts with a Norton Guide magic signature."""
    return len(data) >= 2 and data[:2] in (b"NG", b"EH")


def _decrypt(data: bytes) -> bytes:
    """XOR-decrypt a block of NG data using the fixed key 0x1A."""
    return bytes(b ^ 0x1A for b in data)


def _expand_text(raw: bytes) -> bytes:
    """Expand NG in-line formatting codes to plain CP437 bytes.

    Handled sequences:
      0xFF nn      → nn ASCII space characters (column-padding run)
      ^B ^U ^N ^R  → bold/underline/normal/reverse toggle (stripped)
      ^Cnn         → literal byte with hex value nn (kept)
      ^Ann         → foreground/background attribute (stripped)
      ^^           → literal '^' character
    All other bytes are kept as-is (CP437 box-drawing chars remain intact).
    """
    out = bytearray()
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == 0xFF:
            # Space run: next byte is the count of spaces to insert
            if i + 1 < len(raw):
                out.extend(b" " * raw[i + 1])
                i += 2
            else:
                i += 1
        elif c == 0x5E:  # b'^'
            if i + 1 >= len(raw):
                out.append(c)
                i += 1
                continue
            code = raw[i + 1] & 0xDF  # fold to uppercase
            if code in (0x42, 0x55, 0x4E, 0x52):
                # ^B bold / ^U underline / ^N normal / ^R reverse — strip marker
                i += 2
            elif code == 0x43 and i + 3 < len(raw):
                # ^Cnn — emit the byte whose hex value is nn
                try:
                    val = int(raw[i + 2: i + 4], 16)
                    out.append(val)
                except (ValueError, TypeError):
                    pass
                i += 4
            elif code == 0x41 and i + 3 < len(raw):
                # ^Ann — attribute/colour code, strip entirely
                i += 4
            elif raw[i + 1] == 0x5E:
                # ^^ → literal caret
                out.append(0x5E)
                i += 2
            else:
                # Unknown ^x — skip
                i += 2
        else:
            out.append(c)
            i += 1
    return bytes(out)


class NGReader(HelpReaderBase):
    """Parse a Norton Guide .NG binary file into a HelpDocument."""

    def __init__(self, path: Path, encoding: Optional[str] = None):
        self.path = path
        self.encoding = encoding or "cp437"
        self.data = path.read_bytes()
        if not is_ng_binary(self.data):
            raise ValueError(f"Not a Norton Guide file: {path}")
        d = self.data
        # Header is stored in plain CP437 (not encrypted).
        self.magic = d[:2].decode("ascii", errors="replace")
        self.version = int.from_bytes(d[2:4], "little")
        self.menu_count = int.from_bytes(d[6:8], "little")
        self.title = d[8:48].split(b"\x00")[0].decode(self.encoding, errors="replace").strip()
        self.credit_lines: list[str] = []
        for i in range(5):
            start = 48 + i * 66
            line = d[start: start + 66].split(b"\x00")[0].decode(self.encoding, errors="replace").strip()
            self.credit_lines.append(line)
        # Aliases used by the exporter
        self.filename = self.title
        self.version_str = self.credit_lines[0] if self.credit_lines else ""
        self.copyright = self.credit_lines[1] if len(self.credit_lines) > 1 else ""
        self.author = self.credit_lines[2] if len(self.credit_lines) > 2 else ""

    # ------------------------------------------------------------------
    # HelpReaderBase interface
    # ------------------------------------------------------------------

    def read_bytes(self, data: bytes) -> HelpDocument:
        if data != self.data:
            if not is_ng_binary(data):
                raise ValueError(f"Not a Norton Guide file: {self.path}")
            self.data = data
        return self.read()

    def read(self) -> HelpDocument:
        d = self.data
        root_offset = self._detect_root_offset(d)
        topics, index_entries, help_contents_topic_id = self._traverse(d, root_offset)

        return ensure_document_index(HelpDocument(
            format_name="norton-guide",
            source_name=str(self.path.name),
            topics=topics,
            index_entries=index_entries,
            metadata={
                "encoding": self.encoding,
                "text_encoding": self.encoding,
                "metadata_already_decoded": True,
                "title": self.title,
                "credit_lines": self.credit_lines,
                "help_contents_topic_id": help_contents_topic_id,
            },
            binary_data=self.data,
        ))

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def _detect_root_offset(self, data: bytes) -> int:
        """Locate the first valid record after the fixed-size header."""
        root_offset = NG_HEADER_SIZE
        for delta in range(0, 64, 2):
            candidate = root_offset + delta
            blk = _decrypt(data[candidate: candidate + 6])
            if len(blk) < 6:
                continue
            eid = int.from_bytes(blk[0:2], "little")
            elen = int.from_bytes(blk[2:4], "little")
            if eid in (0, 1, 2) and candidate + 26 + elen <= len(data):
                return candidate
        return root_offset

    def _traverse(
        self,
        data: bytes,
        root_offset: int,
    ) -> tuple[list[TopicRecord], list[IndexEntry], int | None]:
        """Read every physical record and build the TopicRecord list."""
        topics_by_offset: dict[int, TopicRecord] = {}
        topic_order: list[int] = []
        record_kind: dict[int, str] = {}
        parent_line_by_topic: dict[int, int] = {}
        direct_child_labels: dict[int, str] = {}
        menu_specs: dict[int, tuple[list[int], str, list[str]]] = {}

        offset = root_offset
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

            if record_index < self.menu_count:
                if eid != 2:
                    raise ValueError(f"Expected Norton Guide MENU record at offset {offset}, got {eid}")
            elif eid not in (0, 1):
                raise ValueError(f"Unknown Norton Guide entry type {eid} at offset {offset}")

            entry = _decrypt(data[offset:record_end])

            if eid == 2:
                topic, child_offsets, title, prompt_labels = self._build_menu_topic(
                    entry,
                    offset,
                    is_help_contents=(offset == root_offset),
                )
                if topic is not None:
                    topics_by_offset[offset] = topic
                    topic_order.append(offset)
                    record_kind[offset] = "menu"
                    menu_specs[offset] = (child_offsets, title, prompt_labels)
                    for child_offset, label in zip(child_offsets, prompt_labels):
                        cleaned = self._clean_label(label)
                        if child_offset not in (0, _NO_PTR) and self._is_usable_label(cleaned):
                            direct_child_labels.setdefault(child_offset, cleaned)
            elif eid == 0:
                topic, _child_offsets, child_labels, parent_line = self._build_short_topic(
                    entry,
                    offset,
                    is_help_contents=(offset == root_offset),
                )
                if topic is not None:
                    topics_by_offset[offset] = topic
                    topic_order.append(offset)
                    record_kind[offset] = "short"
                    parent_line_by_topic[offset] = parent_line
                    for child_offset, label in child_labels:
                        cleaned = self._clean_label(label)
                        if child_offset not in (0, _NO_PTR) and self._is_usable_label(cleaned):
                            direct_child_labels.setdefault(child_offset, cleaned)
            else:
                topic, _related_offsets, parent_line = self._build_long_topic(entry, offset)
                if topic is not None:
                    topics_by_offset[offset] = topic
                    topic_order.append(offset)
                    record_kind[offset] = "long"
                    parent_line_by_topic[offset] = parent_line

            offset = record_end
            record_index += 1

        self._finalize_menu_topics(topics_by_offset, menu_specs)
        self._resolve_topic_names(topics_by_offset, topic_order, record_kind, parent_line_by_topic, direct_child_labels)

        valid_topic_ids = set(topics_by_offset)
        for topic in topics_by_offset.values():
            # A few compilers use the byte immediately after the final record
            # as the terminal NEXT value instead of 0 or 0xFFFFFFFF.
            for attribute in ("up_context", "down_context", "prev_context", "next_context"):
                if getattr(topic, attribute) == len(data):
                    setattr(topic, attribute, None)
            topic.nav_items = merge_nav_items(
                extract_nav_items_from_uhf(topic.uhf_content, valid_topic_ids=valid_topic_ids),
                build_directional_nav_items(topic),
            )

        topics = [topics_by_offset[offset] for offset in topic_order]
        index_entries = self._build_index_entries(topics)
        help_contents_topic_id = root_offset if root_offset in topics_by_offset else (topic_order[0] if topic_order else None)
        return topics, index_entries, help_contents_topic_id

    # ------------------------------------------------------------------
    # Block processors
    # ------------------------------------------------------------------

    def _build_menu_topic(
        self,
        entry: bytes,
        self_offset: int,
        is_help_contents: bool,
    ) -> tuple[TopicRecord | None, list[int], str, list[str]]:
        """Parse a MENU entry into a TopicRecord."""
        prompt_count = max(0, int.from_bytes(entry[4:6], "little") - 1)
        child_offsets: list[int] = []
        for i in range(prompt_count):
            base = 26 + i * 4
            if base + 4 > len(entry):
                break
            child_offsets.append(int.from_bytes(entry[base: base + 4], "little"))

        title, prompt_labels = self._extract_menu_text(entry, prompt_count)
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
    ) -> tuple[TopicRecord | None, list[int], list[tuple[int, str]], int]:
        """Parse a SHORT entry into a TopicRecord (menu/index page)."""
        line_count = int.from_bytes(entry[4:6], "little")
        parent_line = int.from_bytes(entry[8:10], "little")
        parent_offset = int.from_bytes(entry[10:14], "little")

        child_offsets: list[int] = []
        child_labels: list[tuple[int, str]] = []
        raw_lines: list[bytes] = []
        uhf_lines: list[str] = []
        pos_kws: list[PositionedKeyword] = []

        for i in range(line_count):
            base = 26 + i * 6
            if base + 6 > len(entry):
                break
            text_offset = int.from_bytes(entry[base: base + 2], "little")
            child_offset = int.from_bytes(entry[base + 2: base + 6], "little")
            child_offsets.append(child_offset)

            if text_offset <= 0:
                continue
            text_offset += 26  # Sample guides store SHORT text offsets relative to the fixed header.
            if text_offset >= len(entry):
                continue
            null_pos = entry.find(b"\x00", text_offset)
            if null_pos == -1:
                raw_line = entry[text_offset:]
            else:
                raw_line = entry[text_offset:null_pos]

            expanded = _expand_text(raw_line)
            visible_text, style_spans, ff_visible_index = _expand_text_to_uhf_parts(raw_line, self.encoding)
            ff_byte_pos = raw_line.find(b"\xff")
            link_spans: list[UhfLinkSpan] = []
            label_text = ""
            if child_offset not in (0, _NO_PTR):
                if ff_byte_pos > 0 and ff_visible_index is not None:
                    link_end = ff_visible_index
                else:
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

        if not raw_lines:
            return None, child_offsets, child_labels, parent_line

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
    ) -> tuple[TopicRecord | None, list[int], int]:
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
            null_pos = entry.find(b"\x00", text_off)
            if null_pos == -1:
                break
            source_line = entry[text_off: null_pos]
            raw_lines.append(_expand_text(source_line))
            visible_text, style_spans, _ff_visible_index = _expand_text_to_uhf_parts(source_line, self.encoding)
            uhf_lines.append(render_uhf_line(visible_text, style_spans=style_spans))
            text_off = null_pos + 1

        pos_kws: list[PositionedKeyword] = []
        see_also_targets: list[int] = []
        if see_also_flag and text_off + 2 <= len(entry):
            sa_count = int.from_bytes(entry[text_off: text_off + 2], "little")
            text_off += 2
            sa_ptrs: list[int] = []
            for _ in range(sa_count):
                if text_off + 4 > len(entry):
                    break
                ptr = int.from_bytes(entry[text_off: text_off + 4], "little")
                sa_ptrs.append(ptr)
                if ptr not in (0, _NO_PTR):
                    see_also_targets.append(ptr)
                text_off += 4
            sa_labels: list[str] = []
            for _ in range(sa_count):
                null_pos = entry.find(b"\x00", text_off)
                if null_pos == -1:
                    break
                sa_labels.append(
                    entry[text_off: null_pos].decode(self.encoding, errors="replace").strip()
                )
                text_off = null_pos + 1

            valid = [
                (lbl, ptr)
                for lbl, ptr in zip(sa_labels, sa_ptrs)
                if ptr not in (0, _NO_PTR) and lbl
            ]
            if valid:
                raw_lines.append(b"")
                uhf_lines.append("")
                line_bytes = bytearray(b"See also: ")
                positions: list[tuple[int, int, int]] = []
                for lbl, ptr in valid:
                    start = len(line_bytes)
                    line_bytes.extend(lbl.encode(self.encoding, errors="replace"))
                    end = len(line_bytes)
                    positions.append((start, end, ptr))
                    line_bytes.extend(b"  ")
                raw_lines.append(bytes(line_bytes))
                uhf_lines.append(
                    render_uhf_line(
                        line_bytes.decode(self.encoding, errors="replace"),
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

        if not raw_lines:
            return None, [ptr for ptr in (prev_offset, next_offset, *see_also_targets) if ptr not in (0, _NO_PTR)], parent_line

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
        related_offsets = [ptr for ptr in (parent_offset, prev_offset, next_offset, *see_also_targets) if ptr not in (0, _NO_PTR)]
        return topic, related_offsets, parent_line

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _finalize_menu_topics(
        self,
        topics_by_offset: dict[int, TopicRecord],
        menu_specs: dict[int, tuple[list[int], str, list[str]]],
    ) -> None:
        """Populate MENU topics once child topics are known."""
        for offset, (child_offsets, title, prompt_labels) in menu_specs.items():
            topic = topics_by_offset[offset]
            raw_lines: list[bytes] = []
            uhf_lines: list[str] = []
            pos_kws: list[PositionedKeyword] = []
            resolved_labels: list[str] = []

            for index, child_offset in enumerate(child_offsets):
                label = self._clean_label(prompt_labels[index]) if index < len(prompt_labels) else ""
                if not self._is_usable_label(label):
                    label = ""
                if not label:
                    child_topic = topics_by_offset.get(child_offset)
                    if child_topic is not None:
                        label = self._topic_label(child_topic)
                if not label and child_offset not in (0, _NO_PTR):
                    label = f"Context {child_offset}"
                if not label:
                    continue

                raw = label.encode(self.encoding, errors="replace")
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
                resolved_labels.append(label)

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

    def _extract_menu_text(self, entry: bytes, prompt_count: int) -> tuple[str, list[str]]:
        """Extract a MENU title and its prompt labels from the fixed layout."""
        text_start = 26 + prompt_count * 4 + (prompt_count + 1) * 8
        if text_start >= len(entry):
            return "", []

        def read_label(index: int) -> tuple[str, int]:
            if index >= len(entry):
                return "", len(entry)
            end = entry.find(b"\x00", index)
            if end == -1:
                end = len(entry)
                next_index = end
            else:
                next_index = end + 1
            raw = entry[index:end].replace(b"\xff", b" ")
            return self._clean_label(raw.decode(self.encoding, errors="replace")), next_index

        title, index = read_label(text_start)
        prompts: list[str] = []
        for _ in range(prompt_count):
            prompt, index = read_label(index)
            prompts.append(prompt)
        return title, prompts

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
        return self._clean_label(parent_topic.raw_lines[parent_line - 1].decode(self.encoding, errors="replace"))

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
            cleaned = self._clean_label(raw_line.decode(self.encoding, errors="replace"))
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


def _expand_text_to_uhf_parts(raw: bytes, encoding: str) -> tuple[str, list[UhfStyleSpan], int | None]:
    """Expand one NG line to visible text plus UHF style spans."""
    visible_chars: list[str] = []
    visible_styles: list[tuple[bool, bool, bool, int | None, int | None]] = []
    bold = False
    underline = False
    reverse = False
    fg: int | None = None
    bg: int | None = None
    first_pad_visible_index: int | None = None
    index = 0

    def append_char(value: int) -> None:
        visible_chars.append(bytes([value]).decode(encoding, errors="replace"))
        visible_styles.append((bold, underline, reverse, fg, bg))

    while index < len(raw):
        value = raw[index]
        if value == 0xFF:
            if first_pad_visible_index is None:
                first_pad_visible_index = len(visible_chars)
            if index + 1 < len(raw):
                for _ in range(raw[index + 1]):
                    append_char(0x20)
                index += 2
            else:
                index += 1
            continue

        if value == 0x5E:
            if index + 1 >= len(raw):
                append_char(value)
                index += 1
                continue
            code = raw[index + 1] & 0xDF
            if code == 0x42:  # ^B
                bold = not bold
                index += 2
                continue
            if code == 0x55:  # ^U
                underline = not underline
                index += 2
                continue
            if code == 0x52:  # ^R
                reverse = not reverse
                index += 2
                continue
            if code == 0x4E:  # ^N
                bold = False
                underline = False
                reverse = False
                fg = None
                bg = None
                index += 2
                continue
            if code == 0x43 and index + 3 < len(raw):  # ^Cnn
                try:
                    append_char(int(raw[index + 2:index + 4], 16))
                except (TypeError, ValueError):
                    pass
                index += 4
                continue
            if code == 0x41 and index + 3 < len(raw):  # ^Ann
                try:
                    attr = int(raw[index + 2:index + 4], 16)
                    fg = attr & 0x0F
                    bg = (attr >> 4) & 0x0F
                except (TypeError, ValueError):
                    pass
                index += 4
                continue
            if raw[index + 1] == 0x5E:  # ^^
                append_char(0x5E)
                index += 2
                continue
            index += 2
            continue

        append_char(value)
        index += 1

    visible_text = "".join(visible_chars)
    spans: list[UhfStyleSpan] = []
    start = 0
    while start < len(visible_chars):
        style = visible_styles[start]
        end = start + 1
        while end < len(visible_chars) and visible_styles[end] == style:
            end += 1
        bold_value, underline_value, reverse_value, fg_value, bg_value = style
        if bold_value or underline_value or reverse_value or fg_value is not None or bg_value is not None:
            spans.append(
                UhfStyleSpan(
                    start=start,
                    end=end,
                    bold=bold_value,
                    underline=underline_value,
                    reverse=reverse_value,
                    fg=fg_value,
                    bg=bg_value,
                )
            )
        start = end

    return visible_text, spans, first_pad_visible_index


def _format_ng_link(link: UhfLinkSpan, label: str) -> str:
    """Render one NG internal pointer as a UHF link."""
    return format_uhf_link(label, topic_id=link.target_context, line=link.target_line)
