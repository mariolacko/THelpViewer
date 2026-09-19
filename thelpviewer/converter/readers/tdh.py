"""Reader for Borland Turbo Debugger/Profiler runtime help files.

TDH/TFH files are not THELP/TPH/TCH variants. Both formats now decode through
the runtime-aligned nibble/text parser. TFH uses a direct size table; TDH uses
runtime-map entries that are cumulatively summed as signed 16-bit deltas from
the separator/base offset, using the larger of the legacy `0x212` width and the
full pre-separator prefix for the known sample families.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
import re
import struct
import zlib

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, PositionedKeyword, TopicRecord, build_directional_nav_items, context_nav_action
from ..codepages import decode_bytes
from ..uhf_markup import UhfLinkSpan, format_uhf_link, render_uhf_line

TDH_MIN_TABLE_BYTE_SIZE = 0x0200
TDH_MAX_TABLE_BYTE_SIZE = 0x0800
TDH_MIN_SIZE = 0x420
TDH_RUNTIME_TABLE_WORD_COUNT = 0x212
TFH_MIN_TABLE_BYTE_SIZE = 0x0100
TFH_MIN_SIZE = 0x2E0
TFH_UNKNOWN_MARKER = b"<E>"
TFH_SYNTHETIC_LEADING_CRLF_WORD = 0xDFF0
TFH_SCREEN_LINE_WIDTH = 0x31
TDH_MAX_SCREEN_LINES = 0x0F
_TDH_ALIAS_TAG_RE = re.compile(r"\[/?(?:link|nav)[^\]]*\]")
_TDH_ALIAS_WS_RE = re.compile(r"\s+")

TFH_NIBBLE_TEXT = {
    0x1: b"e",
    0x2: b"t",
    0x3: b"r",
    0x4: b"o",
    0x5: b"i",
    0x6: b"n",
    0x7: b"a",
    0x8: b"s",
    0x9: b"l",
    0xA: b"c",
    0xB: b"h",
    0xC: b" ",
    0xD: b"^",
    0xE: TFH_UNKNOWN_MARKER,
}


@dataclass(frozen=True, slots=True)
class TdhProbe:
    """Observed structural summary for one Borland runtime help file."""

    format_name: str
    title: str
    description: str
    header_word: int
    table_byte_size: int
    table_word_count: int
    left_table_offset: int
    right_table_offset: int
    separator_offset: int
    separator_word: int
    encoded_payload_offset: int
    encoded_payload_size: int
    payload_lead_byte: int
    payload_lead_cc_run: int
    payload_prefix_hex: str
    crc32: int

    def to_metadata(self) -> dict[str, object]:
        """Return a JSON-safe representation for diagnostics."""
        return {
            "format": self.format_name,
            "header_word": f"0x{self.header_word:04X}",
            "table_byte_size": self.table_byte_size,
            "table_word_count": self.table_word_count,
            "left_table_offset": self.left_table_offset,
            "right_table_offset": self.right_table_offset,
            "separator_offset": self.separator_offset,
            "separator_word": f"0x{self.separator_word:04X}",
            "encoded_payload_offset": self.encoded_payload_offset,
            "encoded_payload_size": self.encoded_payload_size,
            "payload_lead_byte": f"0x{self.payload_lead_byte:02X}",
            "payload_lead_cc_run": self.payload_lead_cc_run,
            "payload_prefix_hex": self.payload_prefix_hex,
            "crc32": f"{self.crc32:08X}",
        }


def _payload_lead_cc_run(data: bytes, encoded_payload_offset: int) -> int:
    """Return the count of consecutive 0xCC bytes after the lead payload byte."""
    cc_run = 0
    for value in data[encoded_payload_offset + 1 :]:
        if value != 0xCC:
            break
        cc_run += 1
    return cc_run


def _probe_runtime_help_binary(
    data: bytes,
    *,
    format_name: str,
    title: str,
    description: str,
    min_size: int,
    min_table_byte_size: int,
    require_even_table_size: bool,
    allowed_separator_words: set[int],
) -> TdhProbe | None:
    """Return structural information when *data* matches a known TDH/TFH shape."""
    if len(data) < min_size:
        return None
    header_word = struct.unpack_from(">H", data, 0)[0]

    # Known runtime-help files share one observable outer shape: the first word
    # gives the byte length of one visible pre-separator half, followed by a
    # matching second half and then one family marker/separator word. TDH uses
    # even-sized halves and separator 0x0001; TFH reuses the same probe shape
    # with an odd-sized size-table prefix and separator 0x0000.
    table_byte_size = header_word
    if (
        table_byte_size < min_table_byte_size
        or table_byte_size > TDH_MAX_TABLE_BYTE_SIZE
        or (require_even_table_size and table_byte_size % 2)
    ):
        return None
    table_word_count = (table_byte_size + 1) // 2
    left_table_offset = 2
    right_table_offset = left_table_offset + table_byte_size
    separator_offset = right_table_offset + table_byte_size
    encoded_payload_offset = separator_offset + 2
    if encoded_payload_offset + 2 >= len(data):
        return None
    separator_word = struct.unpack_from(">H", data, separator_offset)[0]
    if separator_word not in allowed_separator_words:
        return None
    if not (0x80 <= data[encoded_payload_offset] <= 0xBF):
        return None
    if data[encoded_payload_offset + 1:encoded_payload_offset + 5] != b"\xcc\xcc\xcc\xcc":
        return None
    payload_lead_byte = data[encoded_payload_offset]
    payload_lead_cc_run = _payload_lead_cc_run(data, encoded_payload_offset)
    payload_prefix_hex = data[encoded_payload_offset : encoded_payload_offset + 16].hex(" ").upper()

    return TdhProbe(
        format_name=format_name,
        title=title,
        description=description,
        header_word=header_word,
        table_byte_size=table_byte_size,
        table_word_count=table_word_count,
        left_table_offset=left_table_offset,
        right_table_offset=right_table_offset,
        separator_offset=separator_offset,
        separator_word=separator_word,
        encoded_payload_offset=encoded_payload_offset,
        encoded_payload_size=len(data) - encoded_payload_offset,
        payload_lead_byte=payload_lead_byte,
        payload_lead_cc_run=payload_lead_cc_run,
        payload_prefix_hex=payload_prefix_hex,
        crc32=zlib.crc32(data) & 0xFFFFFFFF,
    )


def probe_tdh_binary(data: bytes) -> TdhProbe | None:
    """Return structural TDH information when *data* matches known samples."""
    return _probe_runtime_help_binary(
        data,
        format_name="tdh",
        title="Turbo Debugger Help",
        description="Borland Turbo Debugger TDH help file",
        min_size=TDH_MIN_SIZE,
        min_table_byte_size=TDH_MIN_TABLE_BYTE_SIZE,
        require_even_table_size=True,
        allowed_separator_words={1},
    )


def probe_tfh_binary(data: bytes) -> TdhProbe | None:
    """Return structural TFH information when *data* matches known samples."""
    return _probe_runtime_help_binary(
        data,
        format_name="tfh",
        title="Turbo Profiler Help",
        description="Borland Turbo Profiler TFH help file",
        min_size=TFH_MIN_SIZE,
        min_table_byte_size=TFH_MIN_TABLE_BYTE_SIZE,
        require_even_table_size=False,
        allowed_separator_words={0},
    )


def is_tdh_binary(data: bytes) -> bool:
    """Return ``True`` for known Borland Turbo Debugger TDH help data."""
    return probe_tdh_binary(data) is not None


def is_tfh_binary(data: bytes) -> bool:
    """Return ``True`` for known Borland Turbo Profiler TFH help data."""
    return probe_tfh_binary(data) is not None


def _read_tfh_raw_nibble(block: bytes, offset: int, half: int) -> tuple[int | None, int, int]:
    """Read one raw nibble from a TFH block in low-then-high order."""
    if offset >= len(block):
        return None, offset, half
    value = block[offset]
    nibble = (value & 0x0F) if half == 0 else (value >> 4)
    half ^= 1
    if half == 0:
        offset += 1
    return nibble, offset, half


def _read_tfh_symbol(block: bytes, offset: int, half: int) -> tuple[str | None, int, int]:
    """Read one decoded TFH symbol from a block stream."""
    while True:
        nibble, offset, half = _read_tfh_raw_nibble(block, offset, half)
        if nibble is None:
            return None, offset, half
        if nibble == 0:
            continue
        if nibble == 0xF:
            low, offset, half = _read_tfh_raw_nibble(block, offset, half)
            high, offset, half = _read_tfh_raw_nibble(block, offset, half)
            if low is None or high is None:
                return None, offset, half
            return chr(low | (high << 4)), offset, half
        return TFH_NIBBLE_TEXT[nibble].decode("latin1"), offset, half


def _parse_tfh_block(
    block: bytes,
    *,
    text_lead_word: int | None = None,
    max_target_context: int | None = None,
    max_lines: int | None = None,
    position_callback: callable | None = None,
) -> tuple[list[bytes], list[PositionedKeyword], bool]:
    """Parse one TFH block into visible lines and positioned hotspots."""
    offset = 2 if len(block) >= 2 else 0
    half = 0
    pushback_symbol: str | None = None
    pending_prefix = ""
    pending_hotspot_target: int | None = None
    lines: list[str] = []
    keywords: list[PositionedKeyword] = []

    def get_symbol() -> str | None:
        nonlocal offset, half, pushback_symbol
        if pushback_symbol is not None:
            symbol = pushback_symbol
            pushback_symbol = None
            return symbol
        symbol, offset, half = _read_tfh_symbol(block, offset, half)
        return symbol

    def unread_symbol(symbol: str) -> None:
        nonlocal pushback_symbol
        pushback_symbol = symbol

    def consume_line_break(first_symbol: str) -> None:
        next_symbol: str | None = get_symbol()
        if first_symbol == "\r" and next_symbol == "\n":
            next_symbol = get_symbol()
        elif first_symbol == "\n" and next_symbol == "\r":
            next_symbol = get_symbol()
        if next_symbol is not None:
            unread_symbol(next_symbol)

    def skip_hidden_nul_trailer() -> bool:
        """Discard hidden trailer bytes after NUL until the next line break."""
        while True:
            hidden_symbol = get_symbol()
            if hidden_symbol is None:
                return False
            if hidden_symbol in ("\r", "\n"):
                consume_line_break(hidden_symbol)
                return True

    def wrap_text(current_parts: list[str]) -> tuple[list[str], str]:
        wrap_at = "".join(current_parts).rfind(" ")
        if wrap_at <= 0:
            return current_parts[:TFH_SCREEN_LINE_WIDTH], "".join(current_parts[TFH_SCREEN_LINE_WIDTH:])
        return current_parts[:wrap_at], "".join(current_parts[wrap_at + 1 :])

    while True:
        current_parts = list(pending_prefix)
        current_columns = len(current_parts)
        pending_prefix = ""
        end_of_topic = False
        line_break_encountered = False

        if pending_hotspot_target is not None and current_columns:
            if current_columns > TFH_SCREEN_LINE_WIDTH:
                visible_prefix = current_parts[:TFH_SCREEN_LINE_WIDTH]
                keywords.append(
                    PositionedKeyword(
                        target_context=pending_hotspot_target,
                        line=len(lines),
                        first_column=1,
                        last_column=TFH_SCREEN_LINE_WIDTH,
                    )
                )
                pending_prefix = "".join(current_parts[TFH_SCREEN_LINE_WIDTH:])
                lines.append("".join(visible_prefix).rstrip(" "))
                continue
            keywords.append(
                PositionedKeyword(
                    target_context=pending_hotspot_target,
                    line=len(lines),
                    first_column=1,
                    last_column=current_columns,
                )
            )
            pending_hotspot_target = None

        symbol = get_symbol()
        while True:
            if position_callback is not None:
                position_callback(offset, current_columns, half)
            if symbol is None:
                if current_columns == 0:
                    end_of_topic = True
                    break
                end_of_topic = True
                break
            if symbol == "\x00":
                end_of_topic = True
                break
            if symbol in ("\r", "\n"):
                consume_line_break(symbol)
                line_break_encountered = True
                break
            if symbol == "^":
                saved_offset = offset
                saved_half = half
                if half:
                    offset += 1
                    half = 0
                if offset + 2 > len(block):
                    end_of_topic = current_columns > 0
                    break
                target_context = struct.unpack_from(">H", block, offset)[0]
                if current_columns == 0 and saved_half and target_context == 0:
                    end_of_topic = True
                    break
                offset += 2
                if (
                    target_context == 0
                    or (
                        max_target_context is not None
                        and not 0 < target_context < max_target_context
                    )
                ):
                    offset = saved_offset
                    half = saved_half
                    symbol = "^"
                else:
                    label_parts: list[str] = []
                    line_break_after_hotspot = False
                    while True:
                        label_symbol = get_symbol()
                        if position_callback is not None:
                            position_callback(offset, current_columns, half)
                        if label_symbol is None or label_symbol == "^":
                            break
                        if label_symbol == "\x00":
                            line_break_after_hotspot = skip_hidden_nul_trailer()
                            break
                        label_parts.append(label_symbol)
                    if (
                        line_break_after_hotspot
                        and current_columns == 0
                        and label_parts[:2] == ["\r", "\n"]
                    ):
                        end_of_topic = True
                        break
                    if not label_parts:
                        if line_break_after_hotspot:
                            break
                        symbol = get_symbol()
                        continue
                    if line_break_after_hotspot:
                        while label_parts and label_parts[-1] in {"\r", "\n"}:
                            label_parts.pop()
                        if not label_parts:
                            break
                    label = "".join(label_parts)
                    if current_columns + len(label) > TFH_SCREEN_LINE_WIDTH:
                        pending_prefix = label
                        pending_hotspot_target = target_context
                        break
                    first_column = current_columns + 1
                    current_parts.extend(label_parts)
                    current_columns += len(label_parts)
                    keywords.append(
                        PositionedKeyword(
                            target_context=target_context,
                            line=len(lines),
                            first_column=first_column,
                            last_column=current_columns,
                        )
                    )
                    if line_break_after_hotspot:
                        break
                    symbol = get_symbol()
                    continue
            if symbol == "\t":
                symbol = " "
            current_parts.append(symbol)
            current_columns += 1
            if current_columns > TFH_SCREEN_LINE_WIDTH:
                current_parts, pending_prefix = wrap_text(current_parts)
                current_columns = len(current_parts)
                break
            symbol = get_symbol()

        if current_parts or not lines or line_break_encountered:
            lines.append("".join(current_parts).rstrip(" "))
        if end_of_topic:
            break
        if max_lines is not None and len(lines) >= max_lines:
            break

    trimmed_synthetic_blank = False
    if text_lead_word == TFH_SYNTHETIC_LEADING_CRLF_WORD and lines and lines[0] == "":
        lines = lines[1:] or [""]
        keywords = [
            PositionedKeyword(
                target_context=keyword.target_context,
                line=max(keyword.line - 1, 0),
                first_column=keyword.first_column,
                last_column=keyword.last_column,
            )
            for keyword in keywords
        ]
        trimmed_synthetic_blank = True

    return [line.encode("latin1") for line in lines], keywords, trimmed_synthetic_blank


def _normalize_tdh_alias_text(lines: list[str]) -> str:
    text = "\n".join(lines)
    text = _TDH_ALIAS_TAG_RE.sub("", text)
    text = text.replace("[[", "[").replace("]]", "]")
    text = _TDH_ALIAS_WS_RE.sub(" ", text)
    return text.strip().lower()


def _tdh_alias_owner_by_text(topics: list[TopicRecord], alias_contexts: set[int]) -> dict[int, int]:
    normalized = {
        topic.context_id: _normalize_tdh_alias_text(topic.uhf_content)
        for topic in topics
    }
    owners: dict[int, int] = {}
    for context_id in sorted(alias_contexts):
        text = normalized.get(context_id, "")
        if not text:
            continue
        best_match: tuple[int, int] | None = None
        for owner_id in range(context_id):
            haystack = normalized.get(owner_id, "")
            if not haystack:
                continue
            for trim in range(0, min(8, len(text))):
                fragment = text[trim:]
                if len(fragment) < 8:
                    continue
                if fragment in haystack:
                    candidate = (trim, owner_id)
                    if best_match is None or candidate < best_match:
                        best_match = candidate
                    break
        if best_match is not None:
            owners[context_id] = best_match[1]
    return owners


def _label_from_tfh_lines(lines: list[bytes], context_id: int) -> bytes:
    """Choose a stable visible label for one decoded TFH topic."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        return stripped[:80]
    return f"Context {context_id}".encode("ascii")


def _signed_tdh_delta(value: int) -> int:
    """Return one TDH runtime table entry as a signed 16-bit delta."""
    return value - 0x10000 if value & 0x8000 else value


def _tdh_runtime_table_word_count(probe: TdhProbe) -> int:
    """Return the active TDH runtime map width for known sample families.

    TD 1.0 loads a legacy fixed 0x212-word map, which extends 12 words past the
    visible pre-separator prefix. The later 2.x sample keeps the whole
    pre-separator prefix as runtime map data, so use whichever is larger.
    """
    pre_separator_word_count = max((probe.separator_offset - 2) // 2, 0)
    return max(TDH_RUNTIME_TABLE_WORD_COUNT, pre_separator_word_count)


def _empty_tdh_alias_stats() -> dict[str, object]:
    """Return the empty alias-stat structure for truncated TDH payloads."""
    return {
        "out_of_range_page_word_context_count": 0,
        "embedded_alias_context_count": 0,
        "text_alias_context_count": 0,
        "remaining_unresolved_alias_context_count": 0,
        "empty_placeholder_context_count": 0,
        "out_of_range_page_word_contexts": [],
        "embedded_alias_contexts": [],
        "text_alias_contexts": [],
        "remaining_unresolved_alias_contexts": [],
        "empty_placeholder_contexts": [],
    }


def _build_tfh_contents(topics: list[TopicRecord]) -> tuple[list[ContentNode], int | None]:
    """Build a flat contents list from the HELP INDEX topic when present."""
    help_topic = next((topic for topic in topics if topic.is_help_contents), None)
    if help_topic is None:
        return [], None

    line_map = {index: decode_bytes(line, "cp437") for index, line in enumerate(help_topic.raw_lines)}
    nodes: list[ContentNode] = []
    for keyword in sorted(help_topic.positional_keywords, key=lambda item: (item.line, item.first_column)):
        line = line_map.get(keyword.line, "")
        if not line:
            continue
        start = max(keyword.first_column - 1, 0)
        end = min(keyword.last_column, len(line))
        label = line[start:end].strip()
        if not label:
            continue
        nodes.append(ContentNode(label=label, topic_id=keyword.target_context))
    return nodes, help_topic.context_id


def _wrap_tfh_uhf_link(target_context: int | None, label: str) -> str:
    """Wrap one TDH/TFH hotspot label into canonical inline UHF markup."""
    if target_context is None:
        return label
    nav_action = context_nav_action(target_context)
    if nav_action:
        return f"[nav:{nav_action}]{label}[/nav]"
    return format_uhf_link(label, topic_id=target_context)


def _render_tfh_uhf_lines(
    lines: list[bytes],
    positional_keywords: list[PositionedKeyword],
) -> list[str]:
    """Render TDH/TFH visible lines with inline UHF links for hotspots."""
    keywords_by_line: dict[int, list[PositionedKeyword]] = {}
    for keyword in positional_keywords:
        keywords_by_line.setdefault(keyword.line, []).append(keyword)
    for keywords in keywords_by_line.values():
        keywords.sort(key=lambda keyword: (keyword.first_column, keyword.last_column))

    rendered_lines: list[str] = []
    for line_index, raw_line in enumerate(lines):
        text = decode_bytes(raw_line, "cp437")
        link_spans = [
            UhfLinkSpan(
                start=max(keyword.first_column - 1, 0),
                end=min(keyword.last_column, len(text)),
                target_context=keyword.target_context,
            )
            for keyword in keywords_by_line.get(line_index, [])
            if keyword.last_column > keyword.first_column - 1
        ]
        rendered_lines.append(
            render_uhf_line(
                text,
                link_spans=link_spans,
                link_formatter=lambda span, segment: _wrap_tfh_uhf_link(span.target_context, segment),
            )
        )
    return rendered_lines


def _decode_tfh_topics(
    data: bytes,
    probe: TdhProbe,
) -> tuple[list[TopicRecord], dict[str, int], dict[str, int], int, int, int, int, int]:
    """Return decoded TFH topics from the runtime-aligned block map."""
    context_count = probe.header_word
    size_table_end = 2 + context_count * 2
    if size_table_end + 2 > len(data):
        return [], {}, {}, 0, 0, 0, 0, 0

    sizes = [struct.unpack_from(">H", data, 2 + index * 2)[0] for index in range(context_count)]
    runtime_block_offset = size_table_end
    topics: list[TopicRecord] = []
    control_word_counts: dict[str, int] = {}
    text_lead_word_counts: dict[str, int] = {}
    trimmed_prefix_topics = 0
    control_word_zero_count = 0
    control_word_context_range_count = 0
    text_lead_word_zero_count = 0
    text_lead_word_context_range_count = 0
    offset = runtime_block_offset
    for context_id, size in enumerate(sizes):
        next_offset = offset + size
        if next_offset > len(data):
            break
        raw_block = data[offset:next_offset]
        control_word = struct.unpack_from(">H", raw_block, 0)[0] if len(raw_block) >= 2 else None
        text_lead_word = struct.unpack_from(">H", raw_block, 2)[0] if len(raw_block) >= 4 else None

        control_word_key = "<short>" if control_word is None else f"0x{control_word:04X}"
        control_word_counts[control_word_key] = control_word_counts.get(control_word_key, 0) + 1
        if control_word == 0:
            control_word_zero_count += 1
        elif control_word is not None and 0 < control_word < context_count:
            control_word_context_range_count += 1

        text_lead_word_key = "<short>" if text_lead_word is None else f"0x{text_lead_word:04X}"
        text_lead_word_counts[text_lead_word_key] = text_lead_word_counts.get(text_lead_word_key, 0) + 1
        if text_lead_word == 0:
            text_lead_word_zero_count += 1
        elif text_lead_word is not None and 0 < text_lead_word < context_count:
            text_lead_word_context_range_count += 1

        lines, positional_keywords, trimmed_synthetic_blank = _parse_tfh_block(
            raw_block,
            text_lead_word=text_lead_word,
            max_target_context=context_count,
        )
        if trimmed_synthetic_blank:
            trimmed_prefix_topics += 1
        label = _label_from_tfh_lines(lines, context_id)
        text_lines = _render_tfh_uhf_lines(lines, positional_keywords)
        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=lines,
                index_terms=[label],
                names=[label.decode("latin1")],
                positional_keywords=positional_keywords,
                is_help_contents=(label == b"HELP INDEX"),
                next_context=control_word if control_word is not None and 0 < control_word < context_count else None,
                uhf_content=text_lines,
            )
        )
        offset = next_offset
    for topic in topics:
        topic.nav_items = build_directional_nav_items(topic)
    return (
        topics,
        control_word_counts,
        text_lead_word_counts,
        trimmed_prefix_topics,
        control_word_zero_count,
        control_word_context_range_count,
        text_lead_word_zero_count,
        text_lead_word_context_range_count,
    )


def _read_tfh_partial_document(data: bytes, probe: TdhProbe, source_name: str) -> HelpDocument:
    """Return a decoded TFH document with topic text, hotspots, and next links."""
    (
        topics,
        control_word_counts,
        text_lead_word_counts,
        trimmed_prefix_topics,
        control_word_zero_count,
        control_word_context_range_count,
        text_lead_word_zero_count,
        text_lead_word_context_range_count,
    ) = _decode_tfh_topics(data, probe)
    if not topics:
        raise ValueError("Unsupported or truncated TFH payload")
    hotspot_count = sum(len(topic.positional_keywords) for topic in topics)
    contents, help_contents_topic_id = _build_tfh_contents(topics)
    index_entries = [
        IndexEntry(label=topic.index_terms[0], context_id=topic.context_id, topic_id=topic.context_id)
        for topic in topics
        if topic.index_terms
    ]
    return HelpDocument(
        format_name=probe.format_name,
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        contents=contents,
        metadata={
            "title": probe.title,
            "description": probe.description,
            "format": probe.format_name,
            "format_status": "decoded",
            "text_encoding": "latin1",
            "display_width": TFH_SCREEN_LINE_WIDTH,
            "language": "en",
            "tdh_probe": probe.to_metadata(),
            "tfh_partial_decode": {
                "context_count": probe.header_word,
                "runtime_block_offset": probe.separator_offset,
                "payload_offset": probe.encoded_payload_offset,
                "hotspot_count": hotspot_count,
                "control_word_counts": control_word_counts,
                "control_word_zero_count": control_word_zero_count,
                "control_word_context_range_count": control_word_context_range_count,
                "text_lead_word_counts": text_lead_word_counts,
                "text_lead_word_zero_count": text_lead_word_zero_count,
                "text_lead_word_context_range_count": text_lead_word_context_range_count,
                "leading_word_counts": text_lead_word_counts,
                "leading_word_zero_count": text_lead_word_zero_count,
                "leading_word_context_range_count": text_lead_word_context_range_count,
                "trimmed_synthetic_leading_blank_topics": trimmed_prefix_topics,
                "unknown_marker": TFH_UNKNOWN_MARKER.decode("ascii"),
            },
            "help_contents_topic_id": help_contents_topic_id,
        },
        binary_data=data,
    )


def _decode_tdh_topics(
    data: bytes,
    probe: TdhProbe,
) -> tuple[list[TopicRecord], dict[str, int], int, int, dict[str, object]]:
    """Return decoded TDH topics from the runtime-aligned signed delta map."""
    runtime_table_word_count = _tdh_runtime_table_word_count(probe)
    runtime_table_end = 2 + runtime_table_word_count * 2
    if runtime_table_end > len(data):
        return [], {}, 0, 0, _empty_tdh_alias_stats()

    raw_deltas = [
        struct.unpack_from(">H", data, 2 + index * 2)[0]
        for index in range(runtime_table_word_count)
    ]
    runtime_block_offset = probe.separator_offset
    runtime_starts: list[int] = []
    cumulative_offset = 0
    negative_delta_count = 0
    for raw_delta in raw_deltas:
        runtime_starts.append(runtime_block_offset + cumulative_offset)
        signed_delta = _signed_tdh_delta(raw_delta)
        if signed_delta < 0:
            negative_delta_count += 1
        cumulative_offset += signed_delta

    page_words: list[int | None] = []
    context_count = len(runtime_starts)
    for start in runtime_starts:
        if start < 0 or start + 2 > len(data):
            page_words.append(None)
            continue
        page_word = struct.unpack_from(">H", data, start)[0]
        page_words.append(page_word)
    out_of_range_context_by_start = {
        start: context_id
        for context_id, start in enumerate(runtime_starts)
        if (page_word := page_words[context_id]) is not None
        and page_word != 0
        and not 0 < page_word < context_count
    }
    topic_boundaries = sorted(
        {
            start
            for context_id, start in enumerate(runtime_starts)
            if 0 <= start < len(data)
            and (page_word := page_words[context_id]) is not None
            and (page_word == 0 or 0 < page_word < context_count)
        }
    )

    topics: list[TopicRecord] = []
    page_word_counts: dict[str, int] = {}
    trimmed_prefix_topics = 0
    alias_owner_by_context: dict[int, int] = {}
    for context_id, start in enumerate(runtime_starts):
        if start < 0 or start + 2 > len(data):
            break
        boundary_index = bisect_right(topic_boundaries, start)
        block_end = topic_boundaries[boundary_index] if boundary_index < len(topic_boundaries) else len(data)
        raw_block = data[start:block_end]
        page_word = page_words[context_id]
        if page_word is None:
            break
        page_word_key = f"0x{page_word:04X}"
        page_word_counts[page_word_key] = page_word_counts.get(page_word_key, 0) + 1

        def note_embedded_alias(relative_offset: int, current_columns: int, half: int) -> None:
            alias_context = out_of_range_context_by_start.get(start + relative_offset)
            if alias_context is None or alias_context == context_id:
                return
            alias_owner_by_context.setdefault(alias_context, context_id)

        if out_of_range_context_by_start:
            # Alias offsets can sit past a visible page boundary. Scan the
            # runtime stream as the original viewer did, but keep that scan
            # separate from the bounded text rendered for this topic.
            _parse_tfh_block(
                data[start:],
                text_lead_word=page_word,
                max_target_context=len(runtime_starts),
                max_lines=TDH_MAX_SCREEN_LINES,
                position_callback=note_embedded_alias,
            )

        lines, positional_keywords, trimmed_synthetic_blank = _parse_tfh_block(
            raw_block,
            text_lead_word=page_word,
            max_target_context=len(runtime_starts),
            max_lines=TDH_MAX_SCREEN_LINES,
        )
        if trimmed_synthetic_blank:
            trimmed_prefix_topics += 1

        if context_id == 0:
            label = b"Context 0"
            index_terms: list[bytes] = []
        else:
            label = _label_from_tfh_lines(lines, context_id)
            index_terms = [label]

        text_lines = _render_tfh_uhf_lines(lines, positional_keywords)
        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=lines,
                index_terms=index_terms,
                names=[label.decode("latin1")],
                positional_keywords=positional_keywords,
                is_help_contents=(context_id == 1 and label == b"HELP INDEX"),
                next_context=page_word if 0 < page_word < len(runtime_starts) else None,
                uhf_content=text_lines,
            )
        )

    unresolved_alias_contexts = set(out_of_range_context_by_start.values()) - set(alias_owner_by_context)
    out_of_range_alias_contexts = sorted(out_of_range_context_by_start.values())
    embedded_alias_contexts = sorted(alias_owner_by_context)
    embedded_alias_context_count = len(alias_owner_by_context)
    text_alias_owners = _tdh_alias_owner_by_text(topics, unresolved_alias_contexts)
    text_alias_contexts = sorted(text_alias_owners)
    for alias_context, owner_context in text_alias_owners.items():
        alias_owner_by_context.setdefault(alias_context, owner_context)
    remaining_unresolved_alias_contexts = sorted(unresolved_alias_contexts - set(text_alias_owners))
    empty_placeholder_contexts = sorted(
        topic.context_id
        for topic in topics
        if topic.context_id != 0
        and topic.names == [f"Context {topic.context_id}"]
        and not any(line.strip() for line in topic.uhf_content)
    )
    alias_stats = {
        "out_of_range_page_word_context_count": len(out_of_range_context_by_start),
        "embedded_alias_context_count": embedded_alias_context_count,
        "text_alias_context_count": len(text_alias_owners),
        "remaining_unresolved_alias_context_count": len(remaining_unresolved_alias_contexts),
        "empty_placeholder_context_count": len(empty_placeholder_contexts),
        "out_of_range_page_word_contexts": out_of_range_alias_contexts,
        "embedded_alias_contexts": embedded_alias_contexts,
        "text_alias_contexts": text_alias_contexts,
        "remaining_unresolved_alias_contexts": remaining_unresolved_alias_contexts,
        "empty_placeholder_contexts": empty_placeholder_contexts,
    }

    topic_by_context = {topic.context_id: topic for topic in topics}
    for alias_context, owner_context in sorted(alias_owner_by_context.items()):
        owner_topic = topic_by_context.get(owner_context)
        alias_topic = topic_by_context.get(alias_context)
        if owner_topic is None:
            continue
        if alias_context == owner_context:
            continue
        if alias_context not in owner_topic.alias_contexts:
            owner_topic.alias_contexts.append(alias_context)
        if alias_topic is not None:
            alias_topic.redirect_context = owner_context

    for topic in topics:
        topic.nav_items = build_directional_nav_items(topic)
    return topics, page_word_counts, trimmed_prefix_topics, negative_delta_count, alias_stats


def _read_tdh_document(data: bytes, probe: TdhProbe, source_name: str) -> HelpDocument:
    """Return a decoded TDH document with runtime-aligned topics and hotspots."""
    topics, page_word_counts, trimmed_prefix_topics, negative_delta_count, alias_stats = _decode_tdh_topics(data, probe)
    if not topics:
        raise ValueError("Unsupported or truncated TDH payload")

    hotspot_count = sum(len(topic.positional_keywords) for topic in topics)
    contents, help_contents_topic_id = _build_tfh_contents(topics)
    index_entries = [
        IndexEntry(label=topic.index_terms[0], context_id=topic.context_id, topic_id=topic.context_id)
        for topic in topics
        if topic.index_terms
    ]
    return HelpDocument(
        format_name=probe.format_name,
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        contents=contents,
        metadata={
            "title": probe.title,
            "description": probe.description,
            "format": probe.format_name,
            "format_status": "decoded",
            "text_encoding": "latin1",
            "display_width": TFH_SCREEN_LINE_WIDTH,
            "language": "en",
            "tdh_probe": probe.to_metadata(),
            "tdh_decode": {
                "runtime_context_count": len(topics),
                "runtime_table_word_count": _tdh_runtime_table_word_count(probe),
                "runtime_block_offset": probe.separator_offset,
                "payload_offset": probe.encoded_payload_offset,
                "hotspot_count": hotspot_count,
                "page_word_counts": page_word_counts,
                "negative_delta_count": negative_delta_count,
                "trimmed_synthetic_leading_blank_topics": trimmed_prefix_topics,
                **alias_stats,
            },
            "help_contents_topic_id": help_contents_topic_id,
        },
        binary_data=data,
    )


class TdhHelpReader(HelpReaderBase):
    """Reader for Borland runtime help files."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read a TDH/TFH file into a decoded runtime-help document."""
        source_suffix = self.source_path.suffix.casefold() if self.source_path else ""
        if source_suffix == ".tfh":
            probe = probe_tfh_binary(data)
        elif source_suffix == ".tdh":
            probe = probe_tdh_binary(data)
        else:
            probe = probe_tdh_binary(data) or probe_tfh_binary(data)
        if probe is None:
            raise ValueError("Unsupported Borland runtime help format")

        if probe.format_name == "tfh":
            return _read_tfh_partial_document(data, probe, self.source_name)
        return _read_tdh_document(data, probe, self.source_name)


def read_tdh(path: str | Path) -> HelpDocument:
    """Convenience helper for loading a TDH/TFH file from disk."""
    source_path = Path(path)
    return TdhHelpReader(source_name=source_path.name, source_path=source_path).read_path(source_path)
