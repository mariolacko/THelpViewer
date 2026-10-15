"""Reader for Borland Turbo Debugger/Profiler runtime help files.

TDH/TFH files are not THELP/TPH/TCH variants. Both formats now decode through
the runtime-aligned nibble/text parser. Both use runtime-map entries
cumulatively summed as signed 16-bit deltas from the
block base. Newer maps include a final page and may reference continuations
through the native loader's overlapping payload prefix.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import struct
import zlib

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, PositionedKeyword, TopicRecord, build_directional_nav_items, context_nav_action
from ..codepages import decode_bytes
from ..uhf_markup import UhfLinkSpan, format_uhf_link, render_uhf_line

TDH_MIN_TABLE_WORD_COUNT = 0x0200
TDH_MAX_TABLE_WORD_COUNT = 0x0800
TDH_MIN_SIZE = 0x420
TDH_RUNTIME_TABLE_WORD_COUNT = 0x212
TDH_LEGACY_MAP_MAX_WORD_COUNT = 0x254
TFH_MIN_TABLE_WORD_COUNT = 0x0100
TFH_MIN_SIZE = 0x2E0
TFH_SYNTHETIC_LEADING_CRLF_WORD = 0xDFF0
RUNTIME_SCREEN_LINE_WIDTH = 0x30
TDH_MAX_SCREEN_LINES = 0x0F

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
    0xD: b"\x00",
    0xE: b"\x00",
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
    table_offset: int
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
            "table_offset": self.table_offset,
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
    min_table_word_count: int,
    max_table_word_count: int = TDH_MAX_TABLE_WORD_COUNT,
) -> TdhProbe | None:
    """Return structural information when *data* matches a known TDH/TFH shape."""
    if len(data) < min_size:
        return None
    header_word = struct.unpack_from(">H", data, 0)[0]

    # Word zero is the context-map WORD count, not two byte-sized tables.
    # Later DOS/Windows/32-bit maps can have odd word counts. The WORD at
    # the block base overlaps slot zero and slot one's next-page field: it is
    # not a version/separator signature in either family.
    table_word_count = header_word
    if not min_table_word_count <= table_word_count <= max_table_word_count:
        return None
    table_byte_size = 2 * table_word_count
    table_offset = 2
    separator_offset = table_offset + table_byte_size
    encoded_payload_offset = separator_offset + 2
    if encoded_payload_offset + 2 >= len(data):
        return None
    separator_word = struct.unpack_from(">H", data, separator_offset)[0]
    if struct.unpack_from(">H", data, 2)[0] != 1:
        return None
    first_page_context = struct.unpack_from(">H", data, separator_offset + 1)[0]
    if not 0 < first_page_context < header_word:
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
        table_offset=table_offset,
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
        min_table_word_count=TDH_MIN_TABLE_WORD_COUNT,
    )


def probe_tfh_binary(data: bytes) -> TdhProbe | None:
    """Return structural TFH information when *data* matches known samples."""
    return _probe_runtime_help_binary(
        data,
        format_name="tfh",
        title="Turbo Profiler Help",
        description="Borland Turbo Profiler TFH help file",
        min_size=TFH_MIN_SIZE,
        min_table_word_count=TFH_MIN_TABLE_WORD_COUNT,
        # Known Profiler maps occupy the smaller range. The overlapping base
        # WORD is not a family signature (1.01 has 2C00h, not 0000h).
        max_table_word_count=TDH_MIN_TABLE_WORD_COUNT - 1,
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
                raise ValueError("Truncated runtime HELP literal escape")
            return chr(low | (high << 4)), offset, half
        return TFH_NIBBLE_TEXT[nibble].decode("latin1"), offset, half


def _parse_tfh_block(
    block: bytes,
    *,
    text_lead_word: int | None = None,
    max_lines: int | None = None,
    position_callback: Callable[[int, int], None] | None = None,
    hotspot_lookahead: bool = True,
) -> tuple[list[bytes], list[PositionedKeyword], bool]:
    """Parse cells/hotspots; report consumed half-open source-byte ranges."""
    if len(block) < 2:
        raise ValueError("Truncated runtime HELP page header")
    offset = 2
    half = 0
    pushback_symbol: str | None = None
    pending_prefix = ""
    pending_hotspot_target: int | None = None
    lines: list[str] = []
    keywords: list[PositionedKeyword] = []
    line_width = RUNTIME_SCREEN_LINE_WIDTH
    if position_callback is not None:
        position_callback(0, 2)

    def get_symbol() -> str | None:
        nonlocal offset, half, pushback_symbol
        if pushback_symbol is not None:
            symbol = pushback_symbol
            pushback_symbol = None
            return symbol
        first_byte = offset
        symbol, offset, half = _read_tfh_symbol(block, offset, half)
        if position_callback is not None and symbol is not None:
            # A literal can cross bytes; a consumed high/low nibble belongs
            # to its physical byte even when the final cursor skips it.
            position_callback(first_byte, offset + bool(half))
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

    def display_row(parts: list[str]) -> str:
        # Native row/prefix buffers are C strings. A NUL inside a label cuts
        # its visible text, not its encoded field or closing caret.
        return "".join(parts).split("\x00", 1)[0].rstrip(" ")

    def wrap_text(current_parts: list[str]) -> tuple[list[str], str]:
        wrap_at = "".join(current_parts).rfind(" ")
        if wrap_at <= 0:
            wrap_at = line_width
            carry_start = line_width
        else:
            carry_start = wrap_at + 1

        # Ordinary text after a hotspot can wrap its label again (e.g. a
        # hyphenated suffix or punctuation at column 49). Move/split the
        # ranges together with the cells, not by searching the finished text.
        reflowed: list[PositionedKeyword] = []
        for keyword in keywords:
            if keyword.line != len(lines):
                reflowed.append(keyword)
                continue
            first = keyword.first_column - 1
            last = keyword.last_column
            if first < min(last, wrap_at):
                reflowed.append(PositionedKeyword(
                    target_context=keyword.target_context,
                    line=keyword.line,
                    first_column=first + 1,
                    last_column=min(last, wrap_at),
                    navigation=keyword.navigation,
                ))
            if max(first, carry_start) < last:
                reflowed.append(PositionedKeyword(
                    target_context=keyword.target_context,
                    line=keyword.line + 1,
                    first_column=max(first, carry_start) - carry_start + 1,
                    last_column=last - carry_start,
                    navigation=keyword.navigation,
                ))
        keywords[:] = reflowed
        return current_parts[:wrap_at], "".join(current_parts[carry_start:]).split("\x00", 1)[0]

    while True:
        current_parts = list(pending_prefix)
        current_columns = len(current_parts)
        pending_prefix = ""
        end_of_topic = False
        line_break_encountered = False

        if pending_hotspot_target is not None and current_columns:
            if current_columns > line_width:
                visible_prefix = current_parts[:line_width]
                keywords.append(
                    PositionedKeyword(
                        target_context=pending_hotspot_target,
                        line=len(lines),
                        first_column=1,
                        last_column=line_width,
                    )
                )
                pending_prefix = "".join(current_parts[line_width:])
                lines.append(display_row(visible_prefix))
                if max_lines is not None and len(lines) >= max_lines:
                    break
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
            if symbol is None:
                raise ValueError("Truncated runtime HELP text: missing topic terminator")
            if symbol == "\x00":
                end_of_topic = True
                break
            if symbol in ("\r", "\n"):
                consume_line_break(symbol)
                line_break_encountered = True
                break
            if symbol == "^":
                if half:
                    offset += 1
                    half = 0
                if offset + 2 > len(block):
                    raise ValueError("Truncated runtime HELP hotspot target")
                target_context = struct.unpack_from(">H", block, offset)[0]
                if position_callback is not None:
                    position_callback(offset, offset + 2)
                offset += 2
                if target_context == 0:
                    # Native zero-target controls consume their raw WORD and
                    # display a literal caret (e.g. Pascal pointer operators).
                    symbol = "^"
                else:
                    label_parts: list[str] = []
                    label_has_nul = False
                    while True:
                        label_symbol = get_symbol()
                        if label_symbol is None or label_symbol == "^":
                            if label_symbol is None:
                                field = "trailer: missing closing caret" if label_has_nul else "label"
                                raise ValueError(f"Truncated runtime HELP hotspot {field}")
                            break
                        if label_symbol == "\x00":
                            label_has_nul = True
                        label_parts.append(label_symbol)
                    if not label_parts:
                        symbol = get_symbol()
                        continue
                    label = "".join(label_parts)
                    hotspot_width = line_width
                    if hotspot_lookahead:
                        # TD 4/5 reserves a cell unless the character after the
                        # closing caret is a space. Older TD and Profiler do
                        # not inspect it. Preserve the normal text stream.
                        following = get_symbol()
                        if following != " ":
                            hotspot_width -= 1
                        if following is not None:
                            unread_symbol(following)
                    if current_columns + len(label) > hotspot_width:
                        pending_prefix = label.split("\x00", 1)[0]
                        pending_hotspot_target = target_context if pending_prefix else None
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
                    symbol = get_symbol()
                    continue
            if symbol == "\t":
                symbol = " "
            current_parts.append(symbol)
            current_columns += 1
            if current_columns > line_width:
                current_parts, pending_prefix = wrap_text(current_parts)
                current_columns = len(current_parts)
                break
            symbol = get_symbol()

        if current_parts or not lines or line_break_encountered:
            lines.append(display_row(current_parts))
        if end_of_topic:
            break
        if max_lines is not None and len(lines) >= max_lines:
            break

    # A carried fragment may fall below the native screen-row limit. Only
    # expose ranges on displayed cells, including after trailing-space trim.
    keywords = [
        PositionedKeyword(
            target_context=keyword.target_context,
            line=keyword.line,
            first_column=keyword.first_column,
            last_column=min(keyword.last_column, len(lines[keyword.line])),
            navigation=keyword.navigation,
        )
        for keyword in keywords
        if keyword.line < len(lines) and keyword.first_column <= len(lines[keyword.line])
    ]

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
    """Return the initial TDH map width for known sample families.

    TD 1.0 loads a legacy fixed 0x212-word map, which extends 12 words past the
    visible pre-separator prefix. Later files also address a final
    page at the stored map's cumulative end; authored references can extend
    that initial map through the native loader's overlapping payload prefix.
    """
    pre_separator_word_count = max((probe.separator_offset - 2) // 2, 0)
    # Slot N overlaps the base WORD in older editions too. A nonzero WORD
    # enables their genuine cumulative-end page (including TD 2.x's target
    # 596), not just final pages in the 4.x/5.x editions.
    return max(TDH_RUNTIME_TABLE_WORD_COUNT, pre_separator_word_count + 1)


def _empty_tdh_alias_stats() -> dict[str, object]:
    """Return the empty alias-stat structure for truncated TDH payloads."""
    return {
        "out_of_range_page_word_context_count": 0,
        "embedded_alias_context_count": 0,
        "remaining_unresolved_alias_context_count": 0,
        "empty_placeholder_context_count": 0,
        "out_of_range_page_word_contexts": [],
        "embedded_alias_contexts": [],
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
    context_count = probe.header_word + 1
    size_table_end = probe.separator_offset
    if size_table_end + 2 > len(data):
        return [], {}, {}, 0, 0, 0, 0, 0

    # Native TPROF preloads 600 map WORDs, beyond the stored prefix. Slot N
    # overlaps the base WORD: zero disables it in 1.0, nonzero enables the
    # genuine cumulative-end page in 1.01. It is not that page's byte length.
    deltas = struct.unpack_from(f">{context_count}h", data, 2)
    runtime_block_offset = size_table_end
    starts = []
    offset = runtime_block_offset
    for delta in deltas:
        starts.append(offset)
        offset += delta
    if any(not runtime_block_offset <= start <= len(data)
           or (context_id != 0 and delta != 0 and start + 2 > len(data))
           for context_id, (start, delta) in enumerate(zip(starts, deltas))):
        raise ValueError("Unsupported or truncated TFH payload: context map outside file")
    boundaries = sorted(set(starts) | {len(data)})
    topics: list[TopicRecord] = []
    control_word_counts: dict[str, int] = {}
    text_lead_word_counts: dict[str, int] = {}
    trimmed_prefix_topics = 0
    control_word_zero_count = 0
    control_word_context_range_count = 0
    text_lead_word_zero_count = 0
    text_lead_word_context_range_count = 0
    for context_id, (offset, delta) in enumerate(zip(starts, deltas)):
        if delta == 0:
            continue
        next_offset = boundaries[bisect_right(boundaries, offset)]
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

        if context_id == 0:
            # Opaque slot zero is not a page with a text terminator.
            lines, positional_keywords, trimmed_synthetic_blank = [b""], [], False
        else:
            lines, positional_keywords, trimmed_synthetic_blank = _parse_tfh_block(
                raw_block,
                text_lead_word=text_lead_word,
                max_lines=TDH_MAX_SCREEN_LINES,
                # Original TPROF does not reserve a post-hotspot cell.
                hotspot_lookahead=False,
            )
        if trimmed_synthetic_blank:
            trimmed_prefix_topics += 1
        label = _label_from_tfh_lines(lines, context_id)
        text_lines = _render_tfh_uhf_lines(lines, positional_keywords)
        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=lines,
                index_terms=[label] if context_id else [],
                names=[label.decode("latin1")],
                positional_keywords=positional_keywords,
                is_help_contents=context_id == 1,
                next_context=control_word if control_word is not None and 0 < control_word < context_count else None,
                uhf_content=text_lines,
            )
        )
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


def _read_tfh_document(data: bytes, probe: TdhProbe, source_name: str) -> HelpDocument:
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
            "display_width": RUNTIME_SCREEN_LINE_WIDTH,
            "language": "en",
            "tdh_probe": probe.to_metadata(),
            "tfh_decode": {
                "stored_map_word_count": probe.header_word,
                "runtime_table_word_count": probe.header_word + 1,
                "context_count": len(topics),
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
            },
            "help_contents_topic_id": help_contents_topic_id,
        },
        binary_data=data,
    )


def _decode_tdh_topics(
    data: bytes,
    probe: TdhProbe,
    *,
    runtime_table_word_count: int | None = None,
) -> tuple[list[TopicRecord], dict[str, int], int, int, dict[str, object]]:
    """Return decoded TDH topics from the runtime-aligned signed delta map."""
    runtime_table_word_count = runtime_table_word_count or _tdh_runtime_table_word_count(probe)
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

    if any(raw_deltas[context_id] != 0 and start != len(data)
           and not probe.separator_offset <= start <= len(data) - 2
           for context_id, start in enumerate(runtime_starts)):
        raise ValueError("Unsupported or truncated TDH payload: context map outside file")

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
        if context_id != 0 and raw_deltas[context_id] != 0
        and (page_word := page_words[context_id]) is not None
        and page_word != 0
        and not 0 < page_word < context_count
    }
    modern_layout = probe.header_word > TDH_LEGACY_MAP_MAX_WORD_COUNT
    topic_boundaries = sorted(
        {
            start
            for context_id, start in enumerate(runtime_starts)
            if 0 <= start < len(data)
            and (not modern_layout or context_id <= probe.header_word)
            and (page_word := page_words[context_id]) is not None
            and (page_word == 0 or 0 < page_word < context_count)
        }
    )

    topics: list[TopicRecord] = []
    page_word_counts: dict[str, int] = {}
    trimmed_prefix_topics = 0
    alias_owner_by_context: dict[int, int] = {}
    for context_id, start in enumerate(runtime_starts):
        # The native page routine rejects a zero map entry before seeking.
        # It is an absent context, not another copy of its following page.
        if context_id and raw_deltas[context_id] == 0:
            continue
        if start == len(data):
            continue
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

        def note_embedded_alias(first_byte: int, end_byte: int) -> None:
            for relative_offset in range(first_byte, end_byte):
                alias_context = out_of_range_context_by_start.get(start + relative_offset)
                if alias_context is not None and alias_context != context_id:
                    alias_owner_by_context.setdefault(alias_context, context_id)

        if context_id and out_of_range_context_by_start:
            # Alias offsets can sit past a visible page boundary. Scan the
            # runtime stream as the original viewer did, but keep that scan
            # separate from the bounded text rendered for this topic.
            _parse_tfh_block(
                data[start:],
                text_lead_word=page_word,
                max_lines=TDH_MAX_SCREEN_LINES,
                position_callback=note_embedded_alias,
                hotspot_lookahead=modern_layout,
            )

        if context_id == 0:
            lines, positional_keywords, trimmed_synthetic_blank = [b""], [], False
        else:
            lines, positional_keywords, trimmed_synthetic_blank = _parse_tfh_block(
                raw_block,
                text_lead_word=page_word,
                max_lines=TDH_MAX_SCREEN_LINES,
                hotspot_lookahead=modern_layout,
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
                is_help_contents=(context_id == 1),
                next_context=page_word if 0 < page_word < len(runtime_starts) else None,
                uhf_content=text_lines,
            )
        )

    if modern_layout:
        # Native loaders read beyond the stored map. Only import extra slots
        # actually referenced by the source, not arbitrary text interpreted as
        # hundreds of new topics. The same signed-delta addressing applies.
        referenced_contexts = {keyword.target_context for topic in topics
                               for keyword in topic.positional_keywords}
        referenced_contexts.update(word for word in page_words[1:probe.header_word + 1]
                                   if word is not None and 0 < word < TDH_MAX_TABLE_WORD_COUNT)
        required_words = max((context + 1 for context in referenced_contexts
                              if 0 < context < TDH_MAX_TABLE_WORD_COUNT), default=0)
        if required_words > runtime_table_word_count:
            return _decode_tdh_topics(data, probe, runtime_table_word_count=required_words)
        # An overlapping slot is a redirect only when its decoded cells and
        # hotspots exactly equal the real page containing its source offset.
        # No title matching or case/whitespace normalization is needed.
        by_context = {topic.context_id: topic for topic in topics}
        owner_by_start = {runtime_starts[topic.context_id]: topic.context_id
                          for topic in topics if 0 < topic.context_id <= probe.header_word}
        owner_starts = sorted(owner_by_start)
        for topic in topics:
            if topic.context_id <= probe.header_word:
                continue
            start = runtime_starts[topic.context_id]
            owner_index = bisect_right(owner_starts, start) - 1
            if owner_index < 0:
                continue
            owner_id = owner_by_start[owner_starts[owner_index]]
            owner = by_context[owner_id]
            if topic.raw_lines == owner.raw_lines and topic.positional_keywords == owner.positional_keywords:
                alias_owner_by_context[topic.context_id] = owner_id
                out_of_range_context_by_start[start] = topic.context_id

    unresolved_alias_contexts = set(out_of_range_context_by_start.values()) - set(alias_owner_by_context)
    out_of_range_alias_contexts = sorted(out_of_range_context_by_start.values())
    embedded_alias_contexts = sorted(alias_owner_by_context)
    embedded_alias_context_count = len(alias_owner_by_context)
    remaining_unresolved_alias_contexts = sorted(unresolved_alias_contexts)
    empty_placeholder_contexts = sorted(
        topic.context_id
        for topic in topics
        if topic.context_id != 0
        and topic.names == [f"Context {topic.context_id}"]
        and not any(line.strip() for line in topic.uhf_content)
    )
    alias_stats = {
        "runtime_table_word_count": runtime_table_word_count,
        "absent_contexts": [context for context, delta in enumerate(raw_deltas) if context and delta == 0],
        "out_of_range_page_word_context_count": len(out_of_range_context_by_start),
        "embedded_alias_context_count": embedded_alias_context_count,
        "remaining_unresolved_alias_context_count": len(remaining_unresolved_alias_contexts),
        "empty_placeholder_context_count": len(empty_placeholder_contexts),
        "out_of_range_page_word_contexts": out_of_range_alias_contexts,
        "embedded_alias_contexts": embedded_alias_contexts,
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
            "display_width": RUNTIME_SCREEN_LINE_WIDTH,
            "language": "en",
            "tdh_probe": probe.to_metadata(),
            "tdh_decode": {
                "runtime_context_count": alias_stats["runtime_table_word_count"],
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
        match source_suffix:
            case ".tfh":
                probe = probe_tfh_binary(data)
            case ".tdh":
                probe = probe_tdh_binary(data)
            case _:
                probe = probe_tdh_binary(data) or probe_tfh_binary(data)
        if probe is None:
            raise ValueError("Unsupported Borland runtime help format")

        if probe.format_name == "tfh":
            return _read_tfh_document(data, probe, self.source_name)
        return _read_tdh_document(data, probe, self.source_name)


def read_tdh(path: str | Path) -> HelpDocument:
    """Convenience helper for loading a TDH/TFH file from disk."""
    source_path = Path(path)
    return TdhHelpReader(source_name=source_path.name, source_path=source_path).read_path(source_path)
