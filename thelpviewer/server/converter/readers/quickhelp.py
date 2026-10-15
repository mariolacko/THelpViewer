"""Reader for Microsoft QuickHelp LN binary help files (.HLP).

Supports QB 4.5, QuickC 2.0, MASM 6 and compatible products.
Format specification: fancidev/DosHelp (MIT licence) - Format.txt
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
import re
import struct
from pathlib import Path
from ..base import (
    ContentNode,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    PositionedKeyword,
    TopicNavItem,
    TopicRecord,
    context_nav_action,
    ensure_document_index,
    extract_nav_items_from_uhf,
    nav_action_context,
)
from ..uhf_markup import UhfLinkSpan, UhfStyleSpan, format_uhf_link, render_uhf_line


_QUICKHELP_GRID_SPLIT_RE = re.compile(r"(\s{2,})")


# ---------------------------------------------------------------------------
# Public detector
# ---------------------------------------------------------------------------

def is_quickhelp_binary(data: bytes) -> bool:
    """Return True when the buffer starts with the QuickHelp 'LN' signature."""
    return len(data) >= 4 and data[:2] == b"LN" and data[2:4] == b"\x02\x00"


def _quickhelp_databases(data: bytes):
    """Yield complete databases; all section offsets are relative to each one."""
    offset = 0
    while offset < len(data):
        if len(data) - offset < 0x46 or not is_quickhelp_binary(data[offset:offset + 4]):
            raise ValueError(f"Invalid QuickHelp database header at offset {offset}.")
        size = struct.unpack_from("<I", data, offset + 0x42)[0]
        if size < 0x46 or offset + size > len(data):
            raise ValueError(f"Invalid QuickHelp DatabaseSize at offset {offset}: {size}.")
        yield offset, data[offset:offset + size]
        offset += size


def _quickhelp_contexts(data: bytes, count: int, strings_offset: int, map_offset: int):
    if not 0x46 <= strings_offset <= map_offset <= len(data) or map_offset + count * 2 > len(data):
        raise ValueError("QuickHelp context map exceeds its database.")
    result: list[tuple[str, int]] = []
    position = strings_offset
    for index in range(count):
        end = data.find(b"\x00", position, map_offset)
        if end < 0:
            raise ValueError("Unterminated QuickHelp context string.")
        context = data[position:end].decode("latin-1")
        topic_id = struct.unpack_from("<H", data, map_offset + index * 2)[0]
        result.append((context, topic_id))
        position = end + 1
    return result


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
    if huff_off == topic_text_off:
        return []
    size = topic_text_off - huff_off
    if not 0x46 <= huff_off < topic_text_off <= len(data) or size % 2 or size > 1024:
        raise ValueError("Invalid QuickHelp Huffman tree size.")
    values = list(struct.unpack_from(f"<{size // 2}h", data, huff_off))
    if values[-1] != 0 or 0 in values[:-1] or len(values) == 1:
        raise ValueError("Invalid QuickHelp Huffman tree terminator.")
    nodes = values[:-1]
    for index, value in enumerate(nodes):
        # The serialized post-order numbering puts both children after their
        # parent. Checking this also rules out cycles before decoding any topic.
        if value > 0 and (value % 2 or not index < value // 2 < len(nodes)
                          or index + 1 >= len(nodes)):
            raise ValueError("Invalid QuickHelp Huffman child offset.")
    return nodes


def _huffman_decode(compressed: bytes, tree: list[int]) -> Iterator[int]:
    """Decode a Huffman-encoded byte stream using the given tree.

    Bits are read MSB-first from each byte.
    Yields compact bytes on demand; OUTLEN, not Huffman padding, stops expansion.
    """
    if not tree:
        yield from compressed  # no Huffman tree → data is already compact
        return

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
                raise ValueError("Invalid QuickHelp Huffman child offset.")
            v = tree[node]
            if v < 0:
                # Leaf: emit symbol
                yield v & 0xFF
                break
            bit = next_bit()
            if bit is None:
                return
            if bit == 0:
                # 0-bit child: navigate to tree[v // 2]
                node = v // 2
            else:
                # 1-bit child: always the next sequential node
                node = node + 1


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
            raise ValueError("Truncated QuickHelp dictionary entry.")
        keywords.append(data[pos: pos + length])
        pos += length
    if len(keywords) > 1024:
        raise ValueError("QuickHelp dictionary exceeds 1024 entries.")
    return keywords


def _keyword_expand(compact: Iterable[int], outlen: int, keywords: list[bytes]) -> bytes:
    """Expand keyword-compressed + RLE data to the binary topic representation."""
    out = bytearray()
    values = iter(compact)

    def read_byte() -> int:
        try:
            return next(values)
        except StopIteration:
            raise ValueError("Truncated QuickHelp compressed topic before OUTLEN.") from None

    while len(out) < outlen:
        b = read_byte()
        match b:
            case _ if b < 0x10 or b > 0x1A:
                # Value byte: copy as-is
                out.append(b)
            case 0x1A:
                # Escape: next byte is literal
                out.append(read_byte())
            case 0x19:
                # Repeat: repeat_byte × repeat_count
                repeat_byte = read_byte()
                repeat_count = read_byte()
                out.extend(bytes([repeat_byte]) * repeat_count)
            case 0x18:
                # Space run
                out.extend(b" " * read_byte())
            case _:
                # Dictionary lookup (0x10–0x17): 10-bit index
                idx = ((b & 3) << 8) | read_byte()
                if idx >= len(keywords) or not keywords[idx]:
                    raise ValueError("Invalid QuickHelp dictionary reference.")
                out.extend(keywords[idx])
                if b & 4:  # Append-Space bit
                    out.append(0x20)
        if len(out) > outlen:
            raise ValueError("QuickHelp expansion exceeds OUTLEN.")
    return bytes(out)


QH_MARKER_OPEN = "◄"
QH_MARKER_CLOSE = "►"


@dataclass(slots=True, frozen=True)
class _ExternalQuickHelpTarget:
    """Resolved cross-file QuickHelp target."""

    source_file: str
    topic_id: int | None = None
    context_alias: str | None = None


@dataclass(slots=True)
class _QuickHelpTopicOptions:
    """Extra QuickHelp topic directives captured during command-line parsing."""

    frozen_rows: int = 0
    category_param: str | None = None
    is_list: bool = False
    is_popup: bool = False


@dataclass(slots=True, frozen=True)
class _QuickHelpContextIndex:
    name: str
    topic_base: int
    case_sensitive: bool
    contexts: dict[str, int]


@lru_cache(maxsize=256)
def _cached_quickhelp_context_indices(path_str: str, mtime_ns: int, size: int):
    """Index every logical database, invalidating cached data after replacement."""
    indices: list[_QuickHelpContextIndex] = []
    topic_base = 0
    try:
        for _offset, data in _quickhelp_databases(Path(path_str).read_bytes()):
            attributes, topic_count, context_count = (
                struct.unpack_from("<H", data, offset)[0] for offset in (4, 8, 10)
            )
            name = data[0x10:0x1E].split(b"\x00")[0].decode("latin-1")
            strings_offset, map_offset = struct.unpack_from("<II", data, 0x26)
            case_sensitive = bool(attributes & 1)
            contexts = {
                context if case_sensitive else context.upper(): topic_base + topic_id
                for context, topic_id in _quickhelp_contexts(data, context_count, strings_offset, map_offset)
                if topic_id < topic_count
            }
            indices.append(_QuickHelpContextIndex(name, topic_base, case_sensitive, contexts))
            topic_base += topic_count
    except (OSError, ValueError, struct.error):
        return ()
    return tuple(indices)


def _read_quickhelp_context_indices(path: Path):
    try:
        info = path.stat()
    except OSError:
        return ()
    return _cached_quickhelp_context_indices(str(path), info.st_mtime_ns, info.st_size)


def _resolve_external_quickhelp_target(
    context_str: str,
    source_path: Path | None,
) -> _ExternalQuickHelpTarget | None:
    """Resolve a QuickHelp `database!context` or bare cross-file context."""
    explicit_file: str | None = None
    target_context = context_str.strip()
    if "!" in target_context:
        explicit_file, target_context = target_context.split("!", 1)
        explicit_file = explicit_file.strip() or None
        target_context = target_context.strip()
        if explicit_file is not None:
            repeated_file, separator, remainder = target_context.partition("!")
            if separator and repeated_file.casefold() == explicit_file.casefold():
                target_context = remainder.strip()
    elif target_context.count(".") >= 2:
        # Microsoft Advisor also emits qualified references as
        # `database.context` (for example `OS2.h.overview`) instead of the
        # documented `database!context` form. Keep these as real cross-file
        # links even when the optional database is not installed.
        database, qualified_context = target_context.split(".", 1)
        if database and qualified_context:
            explicit_file = f"{database}.HLP"
            target_context = qualified_context
    if not target_context:
        return None
    if source_path is None:
        # In-memory conversion has no sibling directory. Keep explicit targets
        # with their namespace so an installed logical database can resolve them.
        if explicit_file is not None:
            filename = Path(explicit_file).name
            return _ExternalQuickHelpTarget(filename, context_alias=f"{filename}!{target_context}")
        return None

    try:
        candidates = sorted(
            (path for path in source_path.parent.iterdir() if path.is_file() and path.suffix.casefold() == ".hlp"),
            key=lambda path: path.name.casefold(),
        )
    except OSError:
        candidates = []
    databases = [(path, index) for path in candidates for index in _read_quickhelp_context_indices(path)]
    if explicit_file is not None:
        wanted = Path(explicit_file).name.casefold()
        named = [(path, index) for path, index in databases
                 if wanted in {path.name.casefold(), path.stem.casefold(),
                               index.name.casefold(), Path(index.name).stem.casefold()}]
        # Recover an absent/misspelled filename only from a unique sibling
        # context. If the named database exists, never substitute another one.
        if named:
            databases = named
        if named and target_context.upper() in {"HV", "VX"}:
            candidate, index = named[0]
            if target_context.upper() == "VX":
                return _ExternalQuickHelpTarget(candidate.name, context_alias=f"{index.name}!vx")
            # Home is database-scoped even when several databases share a file.
            # Prefer declared home aliases, then the database's first topic.
            homes = [(context.upper(), topic_id) for context, topic_id in index.contexts.items()]
            topic_id = next((ident for alias, ident in homes if alias == "-9996" or alias.endswith("!HV")), None)
            if topic_id is None:
                topic_id = next((ident for alias, ident in homes if alias == "H.CONTENTS"), None)
            if topic_id is None:
                topic_id = next((ident for alias, ident in homes if alias.endswith(".CONTENTS")), index.topic_base)
            return _ExternalQuickHelpTarget(candidate.name, topic_id, f"{index.name}!hv")

    matches: list[_ExternalQuickHelpTarget] = []
    for candidate, index in databases:
        key = target_context if index.case_sensitive else target_context.upper()
        topic_id = index.contexts.get(key)
        if topic_id is None:
            continue
        alias = f"{index.name}!{target_context}" if index.topic_base and index.name else target_context
        matches.append(
            _ExternalQuickHelpTarget(
                source_file=candidate.name,
                topic_id=topic_id,
                context_alias=alias,
            )
        )

    if explicit_file is not None:
        if len({(match.source_file.casefold(), match.topic_id) for match in matches}) == 1:
            return matches[0]
        fallback_file = Path(explicit_file).name.strip()
        if fallback_file:
            return _ExternalQuickHelpTarget(
                source_file=fallback_file,
                context_alias=f"{fallback_file}!{target_context}" if named else target_context,
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
        match value:
            case 0x11:
                pieces.append(QH_MARKER_OPEN)
            case 0x10:
                pieces.append(QH_MARKER_CLOSE)
            case _:
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


def _quickhelp_marker_nav_links(
    text_data: bytes,
    line_keywords: list[UhfLinkSpan],
) -> list[UhfLinkSpan]:
    """Return built-in nav links encoded only by QuickHelp marker bytes."""
    nav_links: list[UhfLinkSpan] = []
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
        if linked:
            start_marker = None
            continue

        label = text_data[label_start:label_end].decode("cp437", errors="replace")
        normalized = " ".join(label.split()).casefold()
        match normalized:
            case "contents" | "index" | "back":
                action = normalized
            case _:
                action = None

        if action is not None:
            target_context = nav_action_context(action)
            if target_context is not None:
                nav_links.append(
                    UhfLinkSpan(
                        start=label_start,
                        end=label_end,
                        target_context=target_context,
                    )
                )

        start_marker = None

    return nav_links


# ---------------------------------------------------------------------------
# Binary topic decompilation (Step 1 reversal)
# ---------------------------------------------------------------------------

def _decompile_topic(
    binary: bytes,
    control_char: int,
    context_map: dict[str, int],
    topic_count: int,
    source_path: Path | None,
    topic_base: int = 0,
    case_sensitive: bool = False,
) -> tuple[list[bytes], list[PositionedKeyword], list[str], list[str], _QuickHelpTopicOptions]:
    """Decompile a binary topic into display lines and hyperlink data.

    Returns:
        (raw_lines, positional_keywords, names, uhf_lines, topic_options)
        where names are :n (topic title) values.
    """
    raw_lines: list[bytes] = []
    keywords: list[PositionedKeyword] = []
    names: list[str] = []
    uhf_lines: list[str] = []
    topic_options = _QuickHelpTopicOptions()

    pos = 0
    while pos < len(binary):
        # --- Text block ---
        text_block_len = binary[pos]
        pos += 1
        if text_block_len == 0:
            raise ValueError("Invalid QuickHelp zero-length text block.")
        if pos + text_block_len - 1 > len(binary):
            raise ValueError("Truncated QuickHelp text block.")
        text_data = binary[pos: pos + text_block_len - 1]
        pos += text_block_len - 1

        # --- Attribute block ---
        if pos >= len(binary):
            raise ValueError("Missing QuickHelp attribute block.")
        attr_block_len = binary[pos]
        pos += 1
        if attr_block_len == 0:
            raise ValueError("Invalid QuickHelp zero-length attribute block.")
        if pos + attr_block_len - 1 > len(binary):
            raise ValueError("Truncated QuickHelp attribute block.")
        attr_data = binary[pos: pos + attr_block_len - 1]
        pos += attr_block_len - 1

        line_index = len(raw_lines) + 1  # 1-based: renderer uses enumerate(start=1)

        # --- Decode colon commands embedded in text ---
        if len(text_data) > 0 and text_data[0] == control_char:
            # This is a command line; handle topic name command
            if len(text_data) >= 2:
                cmd_char = text_data[1:2]
                param = text_data[2:].decode("latin-1", errors="replace").strip()
                match cmd_char:
                    case b"n":
                        names.append(param)
                    case b"l":
                        try:
                            topic_options.frozen_rows = max(0, int(param.split()[0]))
                        except (IndexError, ValueError):
                            pass
                    case b"c" if param:
                        topic_options.category_param = param
                    case b"i":
                        topic_options.is_list = True
                    case b"g":
                        topic_options.is_popup = True
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
                topic_base=topic_base,
                case_sensitive=case_sensitive,
            )

        marker_nav_links = _quickhelp_marker_nav_links(text_data, line_keywords)
        if marker_nav_links:
            line_keywords.extend(marker_nav_links)

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
                link_formatter=lambda link, label: _format_quickhelp_link(link, label, topic_base + topic_count),
            )
        )
        raw_lines.append(stored_text)

    return raw_lines, keywords, names, uhf_lines, topic_options


def _parse_links(
    links_data: bytes,
    line_index: int,
    context_map: dict[str, int],
    topic_count: int,
    out: list[PositionedKeyword],
    line_keywords: list[UhfLinkSpan],
    *,
    source_path: Path | None,
    topic_base: int = 0,
    case_sensitive: bool = False,
) -> None:
    """Parse the links section of an attribute block and append to out."""
    pos = 0
    while pos < len(links_data):
        if pos + 2 > len(links_data):
            raise ValueError("Truncated QuickHelp link range.")
        start_idx = links_data[pos]       # 1-based
        end_idx = links_data[pos + 1]     # 1-based
        pos += 2

        # Read NUL-terminated context string
        nul = links_data.find(b"\x00", pos)
        if nul < 0:
            raise ValueError("Unterminated QuickHelp link context.")
        context_str = links_data[pos:nul].decode("latin-1", errors="replace")
        pos = nul + 1

        if context_str == "":
            # No context string → read WORD topic index
            if pos + 2 > len(links_data):
                raise ValueError("Truncated QuickHelp direct link target.")
            raw_idx = struct.unpack_from("<H", links_data, pos)[0]
            pos += 2
            # Highest bit may be set (direct topic index marker)
            local_idx = raw_idx & 0x7FFF
            if local_idx >= topic_count:
                raise ValueError("QuickHelp direct link references a nonexistent topic.")
            topic_idx = topic_base + local_idx
        else:
            # Check QuickHelp built-in navigation contexts first.
            ctx_upper = context_str.upper()
            if ctx_upper == "!B":
                topic_idx = nav_action_context("back")
            elif ctx_upper == "!HV" or ctx_upper == "-9996":
                # Home-view context: source Contents topic.
                topic_idx = nav_action_context("contents")
            elif ctx_upper == "!VX" or ctx_upper == "-9997":
                # Index-view context
                topic_idx = nav_action_context("index")
            else:
                # Try local resolution first
                topic_idx = context_map.get(context_str if case_sensitive else ctx_upper, -1)
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
            topic_base <= topic_idx < topic_base + topic_count
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

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_quickhelp_binary(data):
            raise ValueError("Not a QuickHelp LN file (missing 'LN' signature or wrong version).")
        documents: list[HelpDocument] = []
        databases: list[dict[str, object]] = []
        topic_base = 0
        for offset, section in _quickhelp_databases(data):
            document = self._read_database(section, topic_base)
            documents.append(document)
            databases.append({
                "name": document.metadata["db_name"], "offset": offset,
                "size": len(section), "first_topic_id": topic_base,
                "topic_count": len(document.topics),
                "case_sensitive": bool(struct.unpack_from("<H", section, 4)[0] & 1),
            })
            topic_base += len(document.topics)

        document = documents[0]
        if len(documents) > 1:
            document.contents = [
                ContentNode(
                    label=part.display_name,
                    topic_id=part.metadata.get("help_contents_topic_id"),
                    children=[ContentNode(label=topic.names[0] if topic.names else str(topic.context_id),
                                          topic_id=topic.context_id) for topic in part.topics],
                ) for part in documents
            ]
            for part in documents[1:]:
                document.topics.extend(part.topics)
                document.index_entries.extend(part.index_entries)
        document.metadata["quickhelp_databases"] = databases
        document.metadata["source_file_aliases"] = [item["name"] for item in databases if item["name"]]
        document.metadata["transport_metadata_keys"] = ["db_name", "quickhelp_databases"]
        return document

    def _read_database(self, data: bytes, topic_base: int) -> HelpDocument:  # noqa: C901

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

        sections = [topic_index_off, ctx_strings_off, ctx_map_off]
        sections.extend(offset for offset in (keywords_off, huffman_tree_off) if offset)
        sections.extend((topic_text_off, len(data)))
        if (sections != sorted(sections) or sections[0] < 0x46
                or topic_index_off + (topic_count + 1) * 4 > ctx_strings_off
                or ctx_map_off + context_count * 2 > sections[3]
                or huffman_tree_off and huffman_tree_off == topic_text_off):
            raise ValueError("Invalid QuickHelp section boundaries.")

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
        if (topic_offsets[0] != topic_text_off or topic_offsets[-1] != len(data)
                or any(end - start < 2 for start, end in zip(topic_offsets, topic_offsets[1:]))):
            raise ValueError("Invalid QuickHelp topic index boundaries.")

        # --- Read context strings and their database-local topic indices ---
        contexts = _quickhelp_contexts(data, context_count, ctx_strings_off, ctx_map_off)
        if any(index >= topic_count for _context, index in contexts):
            raise ValueError("QuickHelp context map references a nonexistent topic.")
        ctx_strings = [context for context, _index in contexts]
        ctx_topic_indices = [index for _context, index in contexts]

        # Build context string → topic index lookup (case-insensitive)
        case_sensitive = bool(attributes & 0x01)
        context_map: dict[str, int] = {}
        for ctx_str, topic_idx in zip(ctx_strings, ctx_topic_indices):
            key = ctx_str if case_sensitive else ctx_str.upper()
            context_map[key] = topic_base + topic_idx

        # --- Decode each topic ---
        topics: list[TopicRecord] = []
        quickhelp_category_params: dict[int, str] = {}
        for i in range(topic_count):
            t_start = topic_offsets[i]
            t_end = topic_offsets[i + 1]
            raw_topic = data[t_start:t_end]

            try:
                raw_lines, pos_keywords, names, uhf_lines, topic_options = _decode_topic(
                    raw_topic, tree, keywords, control_char,
                    context_map, topic_count, self.source_path, topic_base, case_sensitive,
                )
            except ValueError as error:
                raise ValueError(f"QuickHelp database {db_name!r}, topic {i}: {error}") from error

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
                if db_name:
                    alias_strings.append(f"{db_name}!{cleaned}")

            topic = TopicRecord(
                context_id=topic_base + i,
                raw_lines=raw_lines,
                positional_keywords=pos_keywords,
                names=names,
                alias_strings=alias_strings,
                frozen_rows=topic_options.frozen_rows,
                quickhelp_is_list=topic_options.is_list,
                quickhelp_is_popup=topic_options.is_popup,
                uhf_content=uhf_lines,
            )
            topic.nav_items = extract_nav_items_from_uhf(
                uhf_lines,
                valid_topic_ids=set(range(topic_base, topic_base + topic_count)),
            )
            if topic_options.category_param:
                quickhelp_category_params[topic_base + i] = topic_options.category_param
            topics.append(topic)

        help_contents_topic_id = _quickhelp_help_contents_topic_id(topics)
        if help_contents_topic_id is not None:
            topics[help_contents_topic_id - topic_base].is_help_contents = True
        if topic_base and topics:
            # Contents inside a later database refers to that database's home,
            # not the first database in the physical HLP container.
            home_id = help_contents_topic_id if help_contents_topic_id is not None else topic_base
            for topic in topics:
                topic.uhf_content = [re.sub(
                    r"\[nav:contents\](.*?)\[/nav\]",
                    lambda match: format_uhf_link(match.group(1), topic_id=home_id), line,
                ) for line in topic.uhf_content]
                topic.nav_items = extract_nav_items_from_uhf(
                    topic.uhf_content, valid_topic_ids=set(range(topic_base, topic_base + topic_count)),
                )

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
                index_entries.append(IndexEntry(label=label, context_id=topic_base + topic_idx))

        _linkify_quickhelp_grid_topics(topics, index_entries)
        label_lookup = _build_quickhelp_index_lookup(topics, index_entries)
        _resolve_quickhelp_category_topics(topics, quickhelp_category_params, label_lookup)
        _linkify_quickhelp_list_topics(topics, label_lookup)

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
        if help_contents_topic_id is not None:
            metadata["help_contents_topic_id"] = help_contents_topic_id

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
    topic_base: int = 0,
    case_sensitive: bool = False,
) -> tuple[list[bytes], list[PositionedKeyword], list[str], list[str], _QuickHelpTopicOptions]:
    """Full three-stage decoding pipeline for one topic."""
    if len(raw_topic) < 2:
        raise ValueError("Truncated QuickHelp topic OUTLEN.")

    # OUTLEN = uncompressed binary size (Step 1 output size)
    outlen = struct.unpack_from("<H", raw_topic, 0)[0]
    compressed = raw_topic[2:]

    # Step 3 reverse: Huffman decode → compact data
    compact = _huffman_decode(compressed, tree)

    # Step 2 reverse: keyword expand + RLE → binary topic data
    binary = _keyword_expand(compact, outlen, keywords)

    # Step 1 reverse: decompile binary lines
    return _decompile_topic(binary, control_char, context_map, topic_count, source_path,
                            topic_base, case_sensitive)


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


def _quickhelp_help_contents_topic_id(topics: list[TopicRecord]) -> int | None:
    """Return the QuickHelp contents topic when the database exposes one."""
    for topic in topics:
        aliases = {alias.strip().upper() for alias in topic.alias_strings}
        if "-9996" in aliases or any(alias.endswith("!HV") for alias in aliases):
            return topic.context_id

    for topic in topics:
        aliases = {alias.strip().casefold() for alias in topic.alias_strings}
        if "h.contents" in aliases:
            return topic.context_id

    for topic in topics:
        title = " ".join(name.strip() for name in topic.names if name.strip()).casefold()
        if "contents" not in title:
            continue
        if any(alias.strip().casefold().endswith(".contents") for alias in topic.alias_strings):
            return topic.context_id

    return None


def _normalize_quickhelp_index_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def _quickhelp_register_link_label(
    lookup: dict[str, int],
    ambiguous: set[str],
    label: str,
    topic_id: int,
) -> None:
    normalized = _normalize_quickhelp_index_label(label)
    if not normalized or normalized in ambiguous:
        return
    existing = lookup.get(normalized)
    if existing is None:
        lookup[normalized] = topic_id
        return
    if existing != topic_id:
        ambiguous.add(normalized)
        lookup.pop(normalized, None)


def _build_quickhelp_index_lookup(topics: list[TopicRecord], index_entries: list[IndexEntry]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    ambiguous: set[str] = set()
    for entry in index_entries:
        label = entry.label.decode("latin-1", errors="replace").strip()
        if not label:
            continue
        _quickhelp_register_link_label(lookup, ambiguous, label, entry.context_id)

    for topic in topics:
        for label in topic.names:
            cleaned = label.strip()
            if cleaned:
                _quickhelp_register_link_label(lookup, ambiguous, cleaned, topic.context_id)
        for alias in topic.alias_strings:
            cleaned = alias.strip()
            if cleaned:
                _quickhelp_register_link_label(lookup, ambiguous, cleaned, topic.context_id)
    return lookup


def _quickhelp_list_candidate_labels(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    labels: list[str] = []
    words = stripped.split(None, 1)
    if words:
        labels.append(words[0])

    line_label = re.split(r"\s{2,}", stripped, maxsplit=1)[0].strip()
    if line_label and line_label not in labels:
        labels.append(line_label)
    return labels


def _resolve_quickhelp_list_target(
    line_text: str,
    label_lookup: dict[str, int],
    *,
    skip_topic_id: int | None = None,
) -> tuple[str, int] | None:
    for label in _quickhelp_list_candidate_labels(line_text):
        target_topic = label_lookup.get(_normalize_quickhelp_index_label(label))
        if target_topic is None:
            continue
        if skip_topic_id is not None and target_topic == skip_topic_id:
            continue
        return label, target_topic
    return None


def _linkify_quickhelp_list_line(
    line: str,
    raw_line: bytes,
    label_lookup: dict[str, int],
    *,
    topic_id: int,
) -> str:
    if "[" in line:
        return line

    raw_text = raw_line.decode("cp437", errors="replace")
    resolved = _resolve_quickhelp_list_target(raw_text, label_lookup, skip_topic_id=topic_id)
    if resolved is None:
        return line

    label, target_topic = resolved
    leading = line[: len(line) - len(line.lstrip())]
    body = line[len(leading):]
    if not body.startswith(label):
        return line
    return f"{leading}{format_uhf_link(label, topic_id=target_topic)}{body[len(label):]}"


def _find_quickhelp_list_line(
    topic: TopicRecord,
    label_lookup: dict[str, int],
    *,
    wanted_topic_id: int,
) -> int | None:
    for line_number, raw_line in enumerate(topic.raw_lines, start=1):
        raw_text = raw_line.decode("cp437", errors="replace")
        resolved = _resolve_quickhelp_list_target(raw_text, label_lookup)
        if resolved is not None and resolved[1] == wanted_topic_id:
            return line_number
    return None


def _resolve_quickhelp_category_target(
    category_param: str,
    topics: list[TopicRecord],
    label_lookup: dict[str, int],
    *,
    current_topic: TopicRecord,
) -> TopicNavItem | None:
    cleaned = " ".join(category_param.split())
    if not cleaned:
        return None

    alias = cleaned
    target_topic = label_lookup.get(_normalize_quickhelp_index_label(cleaned))
    explicit_line: int | None = None

    if target_topic is None:
        head, sep, tail = cleaned.rpartition(" ")
        if sep:
            candidate_alias = head.strip()
            candidate_line = tail.strip()
            if candidate_alias and candidate_line.isdigit():
                resolved_topic = label_lookup.get(_normalize_quickhelp_index_label(candidate_alias))
                if resolved_topic is not None:
                    alias = candidate_alias
                    target_topic = resolved_topic
                    explicit_line = max(1, int(candidate_line))

    if target_topic is None:
        return TopicNavItem(label="Category", alias=alias)

    line_number: int | None = None
    target_record = next((topic for topic in topics if topic.context_id == target_topic), None)
    if target_record is not None and target_record.quickhelp_is_list:
        if explicit_line is not None:
            line_number = explicit_line
        else:
            line_number = _find_quickhelp_list_line(
                target_record,
                label_lookup,
                wanted_topic_id=current_topic.context_id,
            )

    item = TopicNavItem(label="Category", topic_id=target_topic, alias=alias)
    if line_number is not None:
        item.line = line_number
    return item


def _resolve_quickhelp_category_topics(
    topics: list[TopicRecord],
    category_params: dict[int, str],
    label_lookup: dict[str, int],
) -> None:
    for topic in topics:
        category_param = category_params.get(topic.context_id)
        if not category_param:
            continue
        topic.quickhelp_category_nav = _resolve_quickhelp_category_target(
            category_param,
            topics,
            label_lookup,
            current_topic=topic,
        )


def _linkify_quickhelp_list_topics(topics: list[TopicRecord], label_lookup: dict[str, int]) -> None:
    if not label_lookup:
        return

    for topic in topics:
        if not topic.quickhelp_is_list or not topic.uhf_content or not topic.raw_lines:
            continue
        topic.uhf_content = [
            _linkify_quickhelp_list_line(line, raw_line, label_lookup, topic_id=topic.context_id)
            for line, raw_line in zip(topic.uhf_content, topic.raw_lines)
        ]


def _linkify_quickhelp_grid_line(line: str, topic_id: int, label_lookup: dict[str, int]) -> str:
    if "[" in line:
        return line

    parts = _QUICKHELP_GRID_SPLIT_RE.split(line)
    if len(parts) < 3:
        return line

    replacements = 0
    for index in range(0, len(parts), 2):
        chunk = parts[index]
        stripped = chunk.strip()
        if not stripped:
            continue
        target_topic = label_lookup.get(_normalize_quickhelp_index_label(stripped))
        if target_topic is None or target_topic == topic_id:
            continue
        leading = chunk[: len(chunk) - len(chunk.lstrip())]
        trailing = chunk[len(chunk.rstrip()):]
        parts[index] = f"{leading}{format_uhf_link(stripped, topic_id=target_topic)}{trailing}"
        replacements += 1

    return "".join(parts) if replacements >= 2 else line


def _linkify_quickhelp_grid_topics(topics: list[TopicRecord], index_entries: list[IndexEntry]) -> None:
    label_lookup = _build_quickhelp_index_lookup(topics, index_entries)
    if not label_lookup:
        return
    for topic in topics:
        if not topic.uhf_content:
            continue
        topic.uhf_content = [
            _linkify_quickhelp_grid_line(line, topic.context_id, label_lookup)
            for line in topic.uhf_content
        ]


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
