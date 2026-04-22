"""Reader for Microsoft QuickHelp LN binary help files (.HLP).

Supports QB 4.5, QuickC 2.0, MASM 6 and compatible products.
Format specification: fancidev/DosHelp (MIT licence) - Format.txt
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import struct
from pathlib import Path
from ..base import (
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    PositionedKeyword,
    TopicRecord,
    context_nav_action,
    ensure_document_index,
    extract_nav_items_from_uhf,
    nav_action_context,
)
from ..uhf_markup import UhfLinkSpan, UhfStyleSpan, format_uhf_link, render_uhf_line


# ---------------------------------------------------------------------------
# Public detector
# ---------------------------------------------------------------------------

def is_quickhelp_binary(data: bytes) -> bool:
    """Return True when the buffer starts with the QuickHelp 'LN' signature."""
    return len(data) >= 4 and data[:2] == b"LN" and data[2:4] == b"\x02\x00"


# ---------------------------------------------------------------------------
# Huffman decompression (Steps 3 and 2 reversal)
# ---------------------------------------------------------------------------

def _read_huffman_tree(data: bytes, huff_off: int, topic_text_off: int) -> list[int]:
    """Read the Huffman tree as a list of signed int16 values.

    Root is at index 0.  Internal node at index i with value V>0:
      - 0-bit child → tree[V // 2]
      - 1-bit child → tree[i + 1]
    Leaf node: value < 0, symbol = value & 0xFF.
    Terminator: value == 0 (stops the list).
    """
    nodes: list[int] = []
    pos = huff_off
    while pos + 1 < topic_text_off:
        val = struct.unpack_from("<h", data, pos)[0]  # signed int16
        pos += 2
        if val == 0:
            break
        nodes.append(val)
    return nodes


def _huffman_decode(compressed: bytes, tree: list[int]) -> bytes:
    """Decode a Huffman-encoded byte stream using the given tree.

    Bits are read MSB-first from each byte.
    Returns raw bytes (compact representation, Step 2 input).
    """
    if not tree:
        return compressed  # no Huffman tree → data is already compact

    result = bytearray()
    bit_buf = 0
    bits_avail = 0
    comp_pos = 0

    def next_bit() -> int | None:
        nonlocal bit_buf, bits_avail, comp_pos
        if bits_avail == 0:
            if comp_pos >= len(compressed):
                return None
            bit_buf = compressed[comp_pos]
            comp_pos += 1
            bits_avail = 8
        bits_avail -= 1
        return (bit_buf >> bits_avail) & 1  # MSB first

    while True:
        node = 0  # root is always at index 0
        while True:
            if node >= len(tree):
                return bytes(result)
            v = tree[node]
            if v < 0:
                # Leaf: emit symbol
                result.append(v & 0xFF)
                break
            bit = next_bit()
            if bit is None:
                return bytes(result)
            if bit == 0:
                # 0-bit child: navigate to tree[v // 2]
                node = v // 2
            else:
                # 1-bit child: always the next sequential node
                node = node + 1

    return bytes(result)


def _read_keywords(data: bytes, kw_off: int, huff_off: int) -> list[bytes]:
    """Read the keyword dictionary (length-prefixed strings, no NUL terminator)."""
    keywords: list[bytes] = []
    if kw_off == 0:
        return keywords
    pos = kw_off
    while pos < huff_off:
        length = data[pos]
        pos += 1
        if pos + length > huff_off:
            break
        keywords.append(data[pos: pos + length])
        pos += length
    return keywords


def _keyword_expand(compact: bytes, outlen: int, keywords: list[bytes]) -> bytes:
    """Expand keyword-compressed + RLE data to the binary topic representation."""
    out = bytearray()
    i = 0
    while len(out) < outlen and i < len(compact):
        b = compact[i]
        i += 1
        if b < 0x10 or b > 0x1A:
            # Value byte: copy as-is
            out.append(b)
        elif b == 0x1A:
            # Escape: next byte is literal
            if i < len(compact):
                out.append(compact[i])
                i += 1
        elif b == 0x19:
            # Repeat: repeat_byte × repeat_count
            if i + 1 < len(compact):
                repeat_byte = compact[i]
                i += 1
                repeat_count = compact[i]
                i += 1
                out.extend(bytes([repeat_byte]) * repeat_count)
        elif b == 0x18:
            # Space run
            if i < len(compact):
                space_count = compact[i]
                i += 1
                out.extend(b" " * space_count)
        else:
            # Dictionary lookup (0x10–0x17): 10-bit index
            if i < len(compact):
                lo = compact[i]
                i += 1
                idx = ((b & 3) << 8) | lo
                if idx < len(keywords):
                    out.extend(keywords[idx])
                if b & 4:  # Append-Space bit
                    out.append(0x20)
    return bytes(out)


QH_MARKER_OPEN = "◄"
QH_MARKER_CLOSE = "►"


@dataclass(slots=True, frozen=True)
class _ExternalQuickHelpTarget:
    """Resolved cross-file QuickHelp target."""

    source_file: str
    topic_id: int | None = None
    context_alias: str | None = None


@lru_cache(maxsize=256)
def _read_quickhelp_context_index(path_str: str) -> dict[str, int]:
    """Read only the context-string → topic-id map from one QuickHelp file."""
    path = Path(path_str)
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    if not is_quickhelp_binary(data):
        return {}

    (_, _attributes, _control_char, _pad, _topic_count, context_count, _display_width, _predef_ctx_count) = struct.unpack_from(
        "<HHBBHHHH",
        data,
        0x02,
    )
    (_reserved1, _topic_index_off, ctx_strings_off, ctx_map_off, _keywords_off, _huffman_tree_off, _topic_text_off, _reserved2, _reserved3, _db_size) = struct.unpack_from(
        "<IIIIIIIIII",
        data,
        0x1E,
    )

    context_strings: list[str] = []
    pos = ctx_strings_off
    for _ in range(context_count):
        nul = data.find(b"\x00", pos)
        if nul < 0:
            break
        context_strings.append(data[pos:nul].decode("latin-1", errors="replace"))
        pos = nul + 1

    index: dict[str, int] = {}
    for i, context_str in enumerate(context_strings):
        if ctx_map_off + (i + 1) * 2 > len(data):
            break
        topic_id = struct.unpack_from("<H", data, ctx_map_off + i * 2)[0]
        index.setdefault(context_str, topic_id)
        index.setdefault(context_str.upper(), topic_id)
    return index


def _find_quickhelp_sibling_file(source_path: Path, file_hint: str) -> Path | None:
    """Resolve one DOS-style help file name in the current source directory."""
    wanted = file_hint.strip()
    if not wanted:
        return None

    wanted_name = Path(wanted).name.casefold()
    wanted_stem = Path(wanted).stem.casefold()
    for candidate in sorted(source_path.parent.glob("*.HLP")):
        if candidate.name.casefold() == wanted_name:
            return candidate
    for candidate in sorted(source_path.parent.glob("*.HLP")):
        if candidate.stem.casefold() == wanted_stem:
            return candidate
    return None


def _resolve_external_quickhelp_target(
    context_str: str,
    source_path: Path | None,
) -> _ExternalQuickHelpTarget | None:
    """Resolve a QuickHelp `database!context` or bare cross-file context."""
    if source_path is None:
        return None

    explicit_file: str | None = None
    target_context = context_str.strip()
    if "!" in target_context:
        explicit_file, target_context = target_context.split("!", 1)
        explicit_file = explicit_file.strip() or None
        target_context = target_context.strip()
    if not target_context:
        return None

    if explicit_file is not None:
        candidates = []
        resolved = _find_quickhelp_sibling_file(source_path, explicit_file)
        if resolved is not None:
            candidates.append(resolved)
    else:
        candidates = sorted(source_path.parent.glob("*.HLP"))

    try:
        current_file = source_path.resolve()
    except OSError:
        current_file = source_path

    matches: list[_ExternalQuickHelpTarget] = []
    for candidate in candidates:
        try:
            if explicit_file is None and candidate.resolve() == current_file:
                continue
        except OSError:
            if explicit_file is None and candidate == source_path:
                continue

        context_index = _read_quickhelp_context_index(str(candidate))
        topic_id = context_index.get(target_context)
        if topic_id is None:
            topic_id = context_index.get(target_context.upper())
        if topic_id is None:
            continue
        matches.append(
            _ExternalQuickHelpTarget(
                source_file=candidate.name,
                topic_id=topic_id,
                context_alias=target_context,
            )
        )
        if explicit_file is not None:
            break

    if explicit_file is not None:
        if matches:
            return matches[0]
        fallback_file = Path(explicit_file).name.strip()
        if fallback_file:
            return _ExternalQuickHelpTarget(
                source_file=fallback_file,
                context_alias=target_context,
            )
        return None

    unique_matches = {(match.source_file.casefold(), match.topic_id): match for match in matches}
    if len(unique_matches) == 1:
        return next(iter(unique_matches.values()))
    return None


def _strip_quickhelp_markers(text_data: bytes) -> bytes:
    """Remove QuickHelp visual marker bytes from stored raw text."""
    return bytes(b for b in text_data if b not in (0x10, 0x11))


def _decode_quickhelp_visible_text(text_data: bytes) -> str:
    """Decode one display line, keeping QuickHelp tab markers visible."""
    pieces: list[str] = []
    for value in text_data:
        if value == 0x11:
            pieces.append(QH_MARKER_OPEN)
        elif value == 0x10:
            pieces.append(QH_MARKER_CLOSE)
        else:
            pieces.append(bytes((value,)).decode("cp437", errors="replace"))
    return "".join(pieces)


def _quickhelp_stripped_to_visible_boundaries(text_data: bytes) -> list[int]:
    """Map stripped-text character boundaries back to visible-text columns."""
    boundaries = [0]
    visible_index = 0
    for value in text_data:
        visible_index += 1
        if value in (0x10, 0x11):
            continue
        boundaries.append(visible_index)
    return boundaries


def _quickhelp_marker_style_spans(
    text_data: bytes,
    line_keywords: list[UhfLinkSpan],
) -> list[UhfStyleSpan]:
    """Highlight marker-delimited segments that are not hyperlinks."""
    spans: list[UhfStyleSpan] = []
    start_marker: int | None = None
    for index, value in enumerate(text_data):
        if value == 0x11:
            start_marker = index
            continue
        if value != 0x10 or start_marker is None or index <= start_marker + 1:
            continue
        label_start = start_marker + 1
        label_end = index
        linked = any(
            keyword.start < label_end and keyword.end > label_start
            for keyword in line_keywords
        )
        if not linked:
            spans.append(UhfStyleSpan(start=label_start, end=label_end, bold=True))
        start_marker = None
    return spans


# ---------------------------------------------------------------------------
# Binary topic decompilation (Step 1 reversal)
# ---------------------------------------------------------------------------

def _decompile_topic(
    binary: bytes,
    control_char: int,
    context_map: dict[str, int],
    topic_count: int,
    source_path: Path | None,
) -> tuple[list[bytes], list[PositionedKeyword], list[str], list[str], int]:
    """Decompile a binary topic into display lines and hyperlink data.

    Returns:
        (raw_lines, positional_keywords, names, uhf_lines, frozen_rows)
        where names are :n (topic title) values.
    """
    raw_lines: list[bytes] = []
    keywords: list[PositionedKeyword] = []
    names: list[str] = []
    uhf_lines: list[str] = []
    frozen_rows = 0

    pos = 0
    while pos < len(binary):
        # --- Text block ---
        if pos >= len(binary):
            break
        text_block_len = binary[pos]
        pos += 1
        if text_block_len == 0:
            break
        text_data = binary[pos: pos + text_block_len - 1]
        pos += text_block_len - 1

        # --- Attribute block ---
        if pos >= len(binary):
            raw_lines.append(_strip_quickhelp_markers(text_data))
            break
        attr_block_len = binary[pos]
        pos += 1
        if attr_block_len == 0:
            break
        attr_data = binary[pos: pos + attr_block_len - 1]
        pos += attr_block_len - 1

        line_index = len(raw_lines) + 1  # 1-based: renderer uses enumerate(start=1)

        # --- Decode colon commands embedded in text ---
        if len(text_data) > 0 and text_data[0] == control_char:
            # This is a command line; handle topic name command
            if len(text_data) >= 2:
                cmd_char = text_data[1:2]
                param = text_data[2:].decode("latin-1", errors="replace").strip()
                if cmd_char == b"n":
                    names.append(param)
                elif cmd_char == b"l":
                    try:
                        frozen_rows = max(0, int(param.split()[0]))
                    except (IndexError, ValueError):
                        pass
            # Command lines are not displayed; skip to next
            continue

        # --- Parse links from AttrBlockData ---
        # Find the 0xFF separator between styles and links
        ff_pos = -1
        for k in range(len(attr_data)):
            if attr_data[k] == 0xFF:
                ff_pos = k
                break
        style_bytes = attr_data[:ff_pos] if ff_pos >= 0 else attr_data

        line_keywords: list[UhfLinkSpan] = []
        if ff_pos >= 0:
            links_data = attr_data[ff_pos + 1:]
            _parse_links(
                links_data,
                line_index,
                context_map,
                topic_count,
                keywords,
                line_keywords,
                source_path=source_path,
            )

        has_markers = any(value in (0x10, 0x11) for value in text_data)
        stored_text = _strip_quickhelp_markers(text_data)
        style_spans = []
        if not has_markers:
            style_spans = _parse_quickhelp_style_spans(
                style_bytes,
                len(text_data),
                _quickhelp_stripped_to_visible_boundaries(text_data),
            )
        else:
            style_spans = _quickhelp_marker_style_spans(text_data, line_keywords)
        visible_text = _decode_quickhelp_visible_text(text_data)
        uhf_lines.append(
            render_uhf_line(
                visible_text,
                style_spans=style_spans,
                link_spans=line_keywords,
                link_formatter=lambda link, label: _format_quickhelp_link(link, label, topic_count),
            )
        )
        raw_lines.append(stored_text)

    return raw_lines, keywords, names, uhf_lines, frozen_rows


def _parse_links(
    links_data: bytes,
    line_index: int,
    context_map: dict[str, int],
    topic_count: int,
    out: list[PositionedKeyword],
    line_keywords: list[UhfLinkSpan],
    *,
    source_path: Path | None,
) -> None:
    """Parse the links section of an attribute block and append to out."""
    pos = 0
    while pos + 2 <= len(links_data):
        start_idx = links_data[pos]       # 1-based
        end_idx = links_data[pos + 1]     # 1-based
        pos += 2

        # Read NUL-terminated context string
        nul = links_data.find(b"\x00", pos)
        if nul < 0:
            break
        context_str = links_data[pos:nul].decode("latin-1", errors="replace")
        pos = nul + 1

        if context_str == "":
            # No context string → read WORD topic index
            if pos + 2 > len(links_data):
                break
            raw_idx = struct.unpack_from("<H", links_data, pos)[0]
            pos += 2
            # Highest bit may be set (direct topic index marker)
            topic_idx = raw_idx & 0x7FFF
        else:
            # Check QuickHelp built-in navigation contexts first.
            ctx_upper = context_str.upper()
            if ctx_upper == "!B":
                topic_idx = nav_action_context("back")
            elif ctx_upper.endswith("!HV") or ctx_upper == "-9996":
                # Home-view context: Contents / main topic
                topic_idx = nav_action_context("contents")
            elif ctx_upper.endswith("!VX") or ctx_upper == "-9997":
                # Index-view context
                topic_idx = nav_action_context("index")
            else:
                # Try local resolution first
                topic_idx = context_map.get(ctx_upper, -1)
                if topic_idx < 0:
                    topic_idx = context_map.get(context_str, -1)
                if topic_idx < 0:
                    external_target = _resolve_external_quickhelp_target(context_str, source_path)
                    if external_target is None:
                        continue  # truly unresolved link — skip
                    line_keywords.append(
                        UhfLinkSpan(
                            start=max(start_idx - 1, 0),
                            end=max(end_idx, 0),
                            target_context=external_target.topic_id,
                            target_alias=external_target.context_alias,
                            target_source_file=external_target.source_file,
                        )
                    )
                    continue

        if context_nav_action(topic_idx) or (
            0 <= topic_idx < topic_count
        ):
            out.append(PositionedKeyword(
                target_context=topic_idx,
                line=line_index,
                first_column=start_idx,   # 1-based; renderer subtracts 1 internally
                last_column=end_idx,      # 1-based inclusive → used as exclusive slice end
            ))
            line_keywords.append(
                UhfLinkSpan(
                    start=max(start_idx - 1, 0),
                    end=max(end_idx, 0),
                    target_context=topic_idx,
                    target_alias=context_str.strip() if context_str.strip() else None,
                )
            )


# ---------------------------------------------------------------------------
# Main reader class
# ---------------------------------------------------------------------------

class QuickHelpReader(HelpReaderBase):
    """Parse a Microsoft QuickHelp LN binary file into HelpDocument."""

    def read_bytes(self, data: bytes) -> HelpDocument:  # noqa: C901
        if not is_quickhelp_binary(data):
            raise ValueError("Not a QuickHelp LN file (missing 'LN' signature or wrong version).")

        # --- File header (starting at offset 0x02) ---
        #  02-04  WORD  Version          always 2
        #  04-06  WORD  Attributes
        #  06-07  BYTE  ControlCharacter
        #  07-08  BYTE  (padding)
        #  08-0A  WORD  TopicCount
        #  0A-0C  WORD  ContextCount
        #  0C-0E  WORD  DisplayWidth
        #  0E-10  WORD  PredefinedCtxCount
        #  10-1E  BYTE[14] DatabaseName
        #  1E-22  DWORD (reserved)
        #  22-26  DWORD TopicIndexOffset
        #  26-2A  DWORD ContextStringsOffset
        #  2A-2E  DWORD ContextMapOffset
        #  2E-32  DWORD KeywordsOffset
        #  32-36  DWORD HuffmanTreeOffset
        #  36-3A  DWORD TopicTextOffset
        #  3A-3E  DWORD (reserved)
        #  3E-42  DWORD (reserved)
        #  42-46  DWORD DatabaseSize

        (
            version, attributes, control_char, _pad,
            topic_count, context_count, display_width, predef_ctx_count,
        ) = struct.unpack_from("<HHBBHHHH", data, 0x02)

        db_name_raw = data[0x10:0x1E]
        db_name = db_name_raw.split(b"\x00")[0].decode("latin-1", errors="replace")

        (
            _reserved1,
            topic_index_off, ctx_strings_off, ctx_map_off,
            keywords_off, huffman_tree_off, topic_text_off,
            _reserved2, _reserved3, db_size,
        ) = struct.unpack_from("<IIIIIIIIII", data, 0x1E)

        # If HuffmanTree section is absent, huffman_tree_off == 0
        if huffman_tree_off == 0:
            huffman_tree_off = topic_text_off  # no huffman section
        # If Keywords section is absent, keywords_off == 0
        if keywords_off == 0:
            keywords_off = huffman_tree_off

        # --- Read Huffman tree ---
        tree = _read_huffman_tree(data, huffman_tree_off, topic_text_off)

        # --- Read keyword dictionary ---
        keywords = _read_keywords(data, keywords_off, huffman_tree_off)

        # --- Read topic index (TopicCount+1 DWORDs) ---
        topic_offsets: list[int] = []
        for i in range(topic_count + 1):
            off = struct.unpack_from("<I", data, topic_index_off + i * 4)[0]
            topic_offsets.append(off)

        # --- Read context strings ---
        ctx_strings: list[str] = []
        pos = ctx_strings_off
        for _ in range(context_count):
            nul = data.find(b"\x00", pos)
            if nul < 0:
                break
            ctx_strings.append(data[pos:nul].decode("latin-1", errors="replace"))
            pos = nul + 1

        # --- Read context map (ContextCount WORDs) ---
        ctx_topic_indices: list[int] = []
        for i in range(context_count):
            idx = struct.unpack_from("<H", data, ctx_map_off + i * 2)[0]
            ctx_topic_indices.append(idx)

        # Build context string → topic index lookup (case-insensitive)
        case_sensitive = bool(attributes & 0x01)
        context_map: dict[str, int] = {}
        for ctx_str, topic_idx in zip(ctx_strings, ctx_topic_indices):
            key = ctx_str if case_sensitive else ctx_str.upper()
            context_map[key] = topic_idx

        # --- Decode each topic ---
        topics: list[TopicRecord] = []
        for i in range(topic_count):
            t_start = topic_offsets[i]
            t_end = topic_offsets[i + 1]
            raw_topic = data[t_start:t_end]

            try:
                raw_lines, pos_keywords, names, uhf_lines, frozen_rows = _decode_topic(
                    raw_topic, tree, keywords, control_char,
                    context_map, topic_count, self.source_path,
                )
            except Exception:
                raw_lines = []
                pos_keywords = []
                names = []
                uhf_lines = []
                frozen_rows = 0

            if not names:
                derived_heading = _quickhelp_topic_heading(
                    TopicRecord(context_id=i, raw_lines=raw_lines)
                )
                if derived_heading:
                    names = [derived_heading]

            alias_strings: list[str] = []
            seen_aliases: set[str] = set()
            for ctx_str, topic_idx in zip(ctx_strings, ctx_topic_indices):
                if topic_idx != i:
                    continue
                cleaned = ctx_str.strip()
                if not cleaned:
                    continue
                marker = cleaned.casefold()
                if marker in seen_aliases:
                    continue
                seen_aliases.add(marker)
                alias_strings.append(cleaned)

            topic = TopicRecord(
                context_id=i,
                raw_lines=raw_lines,
                positional_keywords=pos_keywords,
                names=names,
                alias_strings=alias_strings,
                frozen_rows=frozen_rows,
                uhf_content=uhf_lines,
            )
            topic.nav_items = extract_nav_items_from_uhf(
                uhf_lines,
                valid_topic_ids=set(range(topic_count)),
            )
            topics.append(topic)

        # --- Build index entries ---
        # Prefer `:n` topic titles as visible labels; fall back to context strings.
        # De-duplicate: one entry per topic (first title wins).
        index_entries: list[IndexEntry] = []
        seen_topics: set[int] = set()
        for ctx_str, topic_idx in zip(ctx_strings, ctx_topic_indices):
            if topic_idx < len(topics) and topic_idx not in seen_topics:
                seen_topics.add(topic_idx)
                title_names = topics[topic_idx].names
                if title_names:
                    label = title_names[0].encode("latin-1", errors="replace")
                else:
                    heading = _quickhelp_topic_heading(topics[topic_idx])
                    if heading:
                        label = heading.encode("latin-1", errors="replace")
                    else:
                        label = ctx_str.encode("latin-1", errors="replace")
                index_entries.append(IndexEntry(label=label, context_id=topic_idx))

        metadata: dict[str, object] = {
            "db_name": db_name,
            "version": version,
            "display_width": display_width,
            "text_encoding": "cp437",
            "control_char": chr(control_char) if 0x20 <= control_char <= 0x7E else f"0x{control_char:02X}",
        }
        title = _derive_quickhelp_title(topics, source_name=self.source_name, db_name=db_name)
        if title:
            metadata["title"] = title

        return ensure_document_index(HelpDocument(
            format_name="quickhelp",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata=metadata,
        ))


def _decode_topic(
    raw_topic: bytes,
    tree: list[int],
    keywords: list[bytes],
    control_char: int,
    context_map: dict[str, int],
    topic_count: int,
    source_path: Path | None,
) -> tuple[list[bytes], list[PositionedKeyword], list[str], list[str], int]:
    """Full three-stage decoding pipeline for one topic."""
    if len(raw_topic) < 2:
        return [], [], [], [], 0

    # OUTLEN = uncompressed binary size (Step 1 output size)
    outlen = struct.unpack_from("<H", raw_topic, 0)[0]
    compressed = raw_topic[2:]

    # Step 3 reverse: Huffman decode → compact data
    compact = _huffman_decode(compressed, tree)

    # Step 2 reverse: keyword expand + RLE → binary topic data
    binary = _keyword_expand(compact, outlen, keywords)

    # Step 1 reverse: decompile binary lines
    return _decompile_topic(binary, control_char, context_map, topic_count, source_path)


def _parse_quickhelp_style_spans(
    style_bytes: bytes,
    visible_text_len: int,
    stripped_to_visible: list[int],
) -> list[UhfStyleSpan]:
    """Decode QuickHelp style runs into character spans."""
    spans: list[UhfStyleSpan] = []
    if not style_bytes:
        return spans

    raw_pos = 0
    current_style = 0
    index = 0
    raw_text_len = max(len(stripped_to_visible) - 1, 0)

    while raw_pos < raw_text_len and index < len(style_bytes):
        chunk_len = style_bytes[index]
        index += 1
        raw_end = min(raw_pos + chunk_len, raw_text_len)
        if current_style and raw_end > raw_pos:
            start = stripped_to_visible[raw_pos]
            end = stripped_to_visible[raw_end]
            if end > start:
                spans.append(
                    UhfStyleSpan(
                        start=max(0, min(visible_text_len, start)),
                        end=max(0, min(visible_text_len, end)),
                        bold=bool(current_style & 0x01),
                        italic=bool(current_style & 0x02),
                        underline=bool(current_style & 0x04),
                    )
                )
        raw_pos = raw_end
        if index < len(style_bytes):
            current_style = style_bytes[index]
            index += 1

    return spans


def _format_quickhelp_link(link: UhfLinkSpan, label: str, topic_count: int) -> str:
    """Render one QuickHelp target as UHF inline markup."""
    if link.target_source_file:
        return format_uhf_link(
            label,
            source_file=link.target_source_file,
            topic_id=link.target_context,
            alias=link.target_alias,
            line=link.target_line,
        )
    target_context = link.target_context
    if target_context is None and link.target_alias:
        return format_uhf_link(label, alias=link.target_alias, line=link.target_line)
    nav_action = context_nav_action(target_context)
    if nav_action:
        return f"[nav:{nav_action}]{label}[/nav]"
    if isinstance(target_context, int) and 0 <= target_context < topic_count:
        return format_uhf_link(
            label,
            topic_id=target_context,
            alias=link.target_alias,
            line=link.target_line,
        )
    return label


def _quickhelp_topic_heading(topic: TopicRecord) -> str:
    """Return the best visible heading stored in one QuickHelp topic."""
    for name in topic.names:
        cleaned = name.strip()
        if cleaned:
            return cleaned
    for raw_line in topic.raw_lines:
        text = raw_line.replace(b"\x02", b"").decode("cp437", errors="replace").strip()
        if _is_quickhelp_heading_line(text):
            return text
    return ""


def _is_quickhelp_heading_line(text: str) -> bool:
    """Reject nav bars, box lines and empty filler when deriving a heading."""
    cleaned = text.strip()
    if not cleaned:
        return False
    lowered = cleaned.casefold()
    words = lowered.split()
    if len(words) >= 2 and all(word in {"up", "down", "contents", "index", "back", "next", "prev", "previous"} for word in words):
        return False
    if all(ch in " -_=|/\\[]<>()─│┬┴┼┤├┌┐└┘═║╔╗╚╝╠╣╦╩╬" for ch in cleaned):
        return False
    return True


def _is_quickhelp_title_candidate(text: str, *, source_name: str, db_name: str) -> bool:
    """Reject internal markers and file names when deriving a bundle title."""
    cleaned = text.strip()
    if not cleaned or cleaned.startswith("."):
        return False

    lowered = cleaned.casefold()
    if lowered in {
        "table of contents",
        "contents",
    }:
        return False

    blocked = {
        Path(source_name).name.casefold(),
        Path(source_name).stem.casefold(),
        Path(db_name).name.casefold(),
        Path(db_name).stem.casefold(),
    }
    return lowered not in blocked


def _score_quickhelp_title(text: str) -> int:
    """Prefer real document titles over menu pages and generic section headings."""
    lowered = text.casefold()
    score = 0
    if "help" in lowered or "quickhelp" in lowered:
        score += 120
    if lowered.endswith(" overview"):
        score += 80
    if "microsoft" in lowered:
        score += 40
    if lowered.endswith(" contents") or lowered == "contents":
        score -= 80
    if lowered.endswith(" menu"):
        score -= 40
    if lowered.endswith(" command"):
        score -= 30
    if lowered.startswith("what is "):
        score -= 20
    score -= max(0, len(text) - 48)
    return score


def _normalize_quickhelp_title(text: str) -> str:
    """Convert generic landing-page labels such as `LINK Overview` to bundle titles."""
    cleaned = text.strip()
    if cleaned.casefold().endswith(" overview"):
        return cleaned[:-9].rstrip() + " Help"
    return cleaned


def _derive_quickhelp_title(topics: list[TopicRecord], *, source_name: str, db_name: str) -> str | None:
    """Pick the most human-readable document title from QuickHelp topic headings."""
    fallback_title: str | None = None

    for index, topic in enumerate(topics):
        heading = _quickhelp_topic_heading(topic)
        if not _is_quickhelp_title_candidate(heading, source_name=source_name, db_name=db_name):
            continue
        normalized = _normalize_quickhelp_title(heading)
        if fallback_title is None:
            fallback_title = normalized
        if index <= 8 and _score_quickhelp_title(heading) >= 100:
            return normalized
        if index <= 2 and heading.casefold().endswith(" overview"):
            return normalized

    return fallback_title
