"""Reader for the Pc-Fand database used by Game-Cheater 9.02."""

from __future__ import annotations

import struct
import re
from dataclasses import dataclass
from pathlib import Path

from ..base import (
    ContentNode,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    TopicRecord,
    TopicTag,
)
from ..codepages import CP852_BOX_CONFLICTS, decode_bytes, decode_bytes_box_aware
from ..uhf_markup import escape_uhf_text, format_uhf_link


XOR_KEY = 0xAA
HEADER_SIZE = 6
MEMO_PAGE_SIZE = 512
PC_FAND_STYLE_CONTROLS = frozenset({0x01, 0x02, 0x04, 0x05, 0x11, 0x13, 0x17})
UHF_STYLE_TAGS = {0x02: "b", 0x13: "u", 0x17: "i"}
UNAMBIGUOUS_BOX_BYTES = frozenset(
    {0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB9, 0xBA, 0xBB, 0xBC, 0xBF,
     0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC8, 0xC9, 0xCA, 0xCB,
     0xCC, 0xCD, 0xCE, 0xD9, 0xDA, 0xDB, 0xDC, 0xDF}
)
BOX_CONTEXT_BYTES = UNAMBIGUOUS_BOX_BYTES | CP852_BOX_CONFLICTS.keys()
PC_FAND_INTERNAL_HELP_START = "!! ZDE ZAČÍNÁ INTERNÍ HELP FANDU !!"
PC_FAND_INTERNAL_HELP_END = "!! ZDE KONČÍ INTERNÍ HELP FANDU !!"
UHF_UNDERLINE_RE = re.compile(r"\[u\](.*?)\[/u\]", re.IGNORECASE)
UHF_INLINE_TAG_RE = re.compile(r"\[/?(?:b|i|u)\]", re.IGNORECASE)
DOUBLE_BOX_TRANSLATION = str.maketrans(
    {
        "┌": "╔",
        "┐": "╗",
        "└": "╚",
        "┘": "╝",
        "├": "╠",
        "┤": "╣",
        "┬": "╦",
        "┴": "╩",
        "┼": "╬",
        "─": "═",
        "│": "║",
    }
)
GAME_CHEATER_DATABASE_FILES = (
    "CHEATDBS.000",
    "CHEATDBS.T00",
    "FIRMY.000",
    "FIRMY.T00",
    "GCNETADR.000",
    "GCNETADR.T00",
    "GCHLP.000",
    "GCHLP.T00",
    "DBSNFO.000",
    "DBSNFO.T00",
    "GCPRM.000",
)


def decode_xor_string(data: bytes) -> str:
    """Decode one fixed XOR-0xAA CP852 string field."""
    decoded = bytes(value ^ XOR_KEY for value in data).rstrip(b"\x00 ")
    return decoded.decode("cp852", errors="replace").strip()


@dataclass(frozen=True, slots=True)
class DecodedTextBlock:
    plain: str
    uhf: str


def _read_text_block_bytes(data: bytes, offset: int) -> bytes | None:
    """Read one Pc-Fand memo block, following chained 512-byte pages."""
    if offset == 0:
        return None
    if offset < 0 or offset + 2 > len(data):
        return None
    length = struct.unpack_from("<H", data, offset)[0]
    position = offset + 2
    remaining = length
    encoded = bytearray()
    visited_pages: set[int] = set()

    while remaining:
        bytes_left_on_page = MEMO_PAGE_SIZE - (position % MEMO_PAGE_SIZE)
        if remaining <= bytes_left_on_page:
            if position + remaining > len(data):
                return None
            encoded.extend(data[position : position + remaining])
            break

        payload_size = bytes_left_on_page - 4
        pointer_offset = position + payload_size
        if payload_size < 0 or pointer_offset + 4 > len(data):
            return None
        encoded.extend(data[position:pointer_offset])
        remaining -= payload_size
        next_page = struct.unpack_from("<I", data, pointer_offset)[0]
        if (
            next_page < MEMO_PAGE_SIZE
            or next_page % MEMO_PAGE_SIZE != 0
            or next_page + MEMO_PAGE_SIZE > len(data)
            or next_page in visited_pages
        ):
            return None
        visited_pages.add(next_page)
        position = next_page

    return bytes(value ^ XOR_KEY for value in encoded).rstrip(b"\x00")


def _decode_text_block_bytes(data: bytes) -> DecodedTextBlock:
    plain_parts: list[str] = []
    uhf_parts: list[str] = []
    text_buffer = bytearray()
    active_tags: list[str] = []

    def flush_text() -> None:
        if not text_buffer:
            return
        raw_text = bytes(text_buffer)
        decoded_parts: list[str] = []
        start = 0
        while start < len(raw_text):
            is_box_run = raw_text[start] in BOX_CONTEXT_BYTES
            end = start + 1
            while end < len(raw_text) and (raw_text[end] in BOX_CONTEXT_BYTES) == is_box_run:
                end += 1
            chunk = raw_text[start:end]
            if is_box_run and any(value in UNAMBIGUOUS_BOX_BYTES for value in chunk):
                decoded_parts.append(decode_bytes_box_aware(chunk, "cp852"))
            else:
                decoded_parts.append(decode_bytes(chunk, "cp852"))
            start = end
        decoded = "".join(decoded_parts)
        plain_parts.append(decoded)
        uhf_parts.append(escape_uhf_text(decoded))
        text_buffer.clear()

    def append_newline() -> None:
        flush_text()
        for active_tag in reversed(active_tags):
            uhf_parts.append(f"[/{active_tag}]")
        plain_parts.append("\n")
        uhf_parts.append("\n")
        for active_tag in active_tags:
            uhf_parts.append(f"[{active_tag}]")

    index = 0
    while index < len(data):
        value = data[index]
        if value == 0x0D:
            append_newline()
            if index + 1 < len(data) and data[index + 1] == 0x0A:
                index += 1
        elif value == 0x0A:
            append_newline()
        elif value in PC_FAND_STYLE_CONTROLS:
            flush_text()
            tag = UHF_STYLE_TAGS.get(value)
            if tag is not None:
                if tag in active_tags:
                    position = active_tags.index(tag)
                    nested_tags = active_tags[position + 1 :]
                    for active_tag in reversed(nested_tags):
                        uhf_parts.append(f"[/{active_tag}]")
                    uhf_parts.append(f"[/{tag}]")
                    active_tags.remove(tag)
                    for active_tag in nested_tags:
                        uhf_parts.append(f"[{active_tag}]")
                else:
                    uhf_parts.append(f"[{tag}]")
                    active_tags.append(tag)
        elif value != 0x00:
            text_buffer.append(value)
        index += 1

    flush_text()
    for tag in reversed(active_tags):
        uhf_parts.append(f"[/{tag}]")
    return DecodedTextBlock(
        plain=_normalize_mixed_box_tables("".join(plain_parts)),
        uhf=_normalize_mixed_box_tables("".join(uhf_parts)),
    )


def _normalize_mixed_box_tables(text: str) -> str:
    """Make Pc-Fand tables with double headers use one consistent border."""
    lines = text.split("\n")
    inside_double_table = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("╔") and "═" in stripped:
            inside_double_table = True
        if inside_double_table:
            lines[index] = line.translate(DOUBLE_BOX_TRANSLATION)
        if inside_double_table and stripped.endswith(("┘", "╝")):
            inside_double_table = False
    return "\n".join(lines)


def _normalized_help_title(value: str) -> str:
    return " ".join(value.replace("[[", "[").split()).casefold()


def _link_help_topic_references(topics: list[TopicRecord]) -> None:
    """Turn underlined Pc-Fand help titles into UHF topic links."""
    targets: dict[str, list[int]] = {}
    for topic in topics:
        if not topic.names:
            continue
        targets.setdefault(_normalized_help_title(topic.names[0]), []).append(topic.context_id)

    for topic in topics:
        def replace(match: re.Match[str]) -> str:
            markup = match.group(1)
            label = UHF_INLINE_TAG_RE.sub("", markup)
            candidates = targets.get(_normalized_help_title(label), [])
            if not candidates:
                return match.group(0)
            target = min(candidates, key=lambda context_id: abs(context_id - topic.context_id))
            return format_uhf_link(f"[u]{markup}[/u]", topic_id=target)

        topic.uhf_content = [UHF_UNDERLINE_RE.sub(replace, line) for line in topic.uhf_content]


def read_text_block(data: bytes, offset: int) -> str | None:
    """Decode one absolute-offset text block as plain Unicode text."""
    decoded = _read_text_block_bytes(data, offset)
    if decoded is None:
        return None
    return _decode_text_block_bytes(decoded).plain


def _read_formatted_text_block(data: bytes, offset: int) -> DecodedTextBlock | None:
    decoded = _read_text_block_bytes(data, offset)
    if decoded is None:
        return None
    return _decode_text_block_bytes(decoded)


def decode_version_code(code: int) -> str:
    """Return the display form of a Game-Cheater record version code."""
    if code == 0:
        return "alias / redirect"
    return f"{code // 100}.{code % 100:02d}"


def is_game_cheater_database(path: Path, data: bytes) -> bool:
    """Return True for the primary Game-Cheater 9.02 database index."""
    if path.name.upper() != "CHEATDBS.000" or len(data) < HEADER_SIZE:
        return False
    record_size = struct.unpack_from("<H", data, 4)[0]
    return record_size == 111 and (len(data) - HEADER_SIZE) % record_size == 0


def _records(data: bytes, expected_size: int, *, derive_count: bool = False) -> list[bytes]:
    if len(data) < HEADER_SIZE:
        raise ValueError("Pc-Fand table header is incomplete")
    record_size = struct.unpack_from("<H", data, 4)[0]
    if record_size != expected_size:
        raise ValueError(f"Unexpected record size {record_size}; expected {expected_size}")
    available = (len(data) - HEADER_SIZE) // record_size
    raw_count = struct.unpack_from("<i", data, 0)[0]
    count = available if derive_count else min(abs(raw_count) or available, available)
    return [
        data[HEADER_SIZE + index * record_size : HEADER_SIZE + (index + 1) * record_size]
        for index in range(count)
    ]


def _split_text(text: str | None) -> list[str]:
    if text is None:
        return []
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _split_decoded_text(text: DecodedTextBlock | None) -> tuple[list[str], list[str]]:
    if text is None:
        return [], []
    return _split_text(text.plain), _split_text(text.uhf)


def _sibling_map(source_path: Path) -> dict[str, Path]:
    return {
        path.name.upper(): path
        for path in source_path.parent.iterdir()
        if path.is_file()
    }


class GameCheaterReader(HelpReaderBase):
    """Convert all useful Game-Cheater tables beside ``CHEATDBS.000``."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        if self.source_path is None:
            raise ValueError("Game-Cheater conversion requires the source path and sibling database files")
        if not is_game_cheater_database(self.source_path, data):
            raise ValueError("Not a Game-Cheater CHEATDBS.000 table")

        siblings = _sibling_map(self.source_path)
        text_path = siblings.get("CHEATDBS.T00")
        if text_path is None:
            raise ValueError("CHEATDBS.T00 is required beside CHEATDBS.000")

        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []
        contents: list[ContentNode] = []
        next_context = 1

        def add_section(
            label: str,
            entries: list[tuple[str, list[str], list[str], list[str], list[TopicTag]]],
        ) -> list[TopicRecord]:
            nonlocal next_context
            children: list[ContentNode] = []
            section_topics: list[TopicRecord] = []
            for title, plain_lines, uhf_lines, metadata_lines, tags in entries:
                cleaned_title = title.strip()
                if not cleaned_title:
                    continue
                context_id = next_context
                next_context += 1
                visible_lines = list(metadata_lines)
                if visible_lines and plain_lines:
                    visible_lines.append("")
                visible_lines.extend(plain_lines)
                visible_uhf = [escape_uhf_text(line) for line in metadata_lines]
                if visible_uhf and uhf_lines:
                    visible_uhf.append("")
                visible_uhf.extend(uhf_lines)
                raw_lines = [line.encode("utf-8") for line in visible_lines]
                topic = TopicRecord(
                    context_id=context_id,
                    raw_lines=raw_lines,
                    index_terms=[cleaned_title.encode("utf-8")],
                    alias_strings=[label, cleaned_title],
                    names=[cleaned_title],
                    uhf_content=visible_uhf,
                    tags=tags,
                )
                topics.append(topic)
                section_topics.append(topic)
                index_entries.append(IndexEntry(label=cleaned_title.encode("utf-8"), context_id=context_id))
                children.append(ContentNode(label=cleaned_title, topic_id=context_id))
            for index, topic in enumerate(section_topics):
                topic.prev_context = section_topics[index - 1].context_id if index else None
                topic.next_context = section_topics[index + 1].context_id if index + 1 < len(section_topics) else None
            if children:
                contents.append(ContentNode(label=label, children=children))
            return section_topics

        cheat_text = text_path.read_bytes()
        cheat_entries: list[tuple[str, list[str], list[str], list[str], list[TopicTag]]] = []
        for record in _records(data, 111, derive_count=True):
            title = decode_xor_string(record[0x01:0x33])
            source = read_text_block(cheat_text, struct.unpack_from("<I", record, 0x33)[0])
            body = _read_formatted_text_block(cheat_text, struct.unpack_from("<I", record, 0x37)[0])
            version = decode_version_code(struct.unpack_from(">H", record, 0x3B)[0])
            publisher = decode_xor_string(record[0x3D:0x6F])
            tags: list[TopicTag] = []
            if publisher:
                tags.append(TopicTag(key="publisher", label="Vydavatel", value=publisher))
            if source:
                source_value = " / ".join(line.strip() for line in _split_text(source) if line.strip())
                if source_value:
                    tags.append(TopicTag(key="source", label="Zdroj", value=source_value))
            metadata_lines = [f"Verze záznamu: {version}"]
            plain_lines, uhf_lines = _split_decoded_text(body)
            cheat_entries.append((title, plain_lines, uhf_lines, metadata_lines, tags))
        add_section("Cheaty", cheat_entries)

        pair = self._read_pair(siblings, "FIRMY")
        if pair is not None:
            index_data, text_data = pair
            entries = []
            for record in _records(index_data, 55):
                title = decode_xor_string(record[0x01:0x33])
                body = _read_formatted_text_block(text_data, struct.unpack_from("<I", record, 0x33)[0])
                plain_lines, uhf_lines = _split_decoded_text(body)
                entries.append((title, plain_lines, uhf_lines, [], []))
            add_section("Firmy", entries)

        pair = self._read_pair(siblings, "GCNETADR")
        if pair is not None:
            index_data, text_data = pair
            entries = []
            for record in _records(index_data, 143):
                title = decode_xor_string(record[0x01:0x3D])
                url = decode_xor_string(record[0x3D:0x8B])
                body = _read_formatted_text_block(text_data, struct.unpack_from("<I", record, 0x8B)[0])
                metadata_lines = [f"URL: {url}"] if url else []
                plain_lines, uhf_lines = _split_decoded_text(body)
                entries.append((title, plain_lines, uhf_lines, metadata_lines, []))
            add_section("Internetové adresy", entries)

        pair = self._read_pair(siblings, "GCHLP")
        if pair is not None:
            index_data, text_data = pair
            entries = []
            inside_internal_help = False
            for record in _records(index_data, 39):
                title = decode_xor_string(record[0x00:0x23])
                if title == PC_FAND_INTERNAL_HELP_START:
                    inside_internal_help = True
                    continue
                if title == PC_FAND_INTERNAL_HELP_END:
                    inside_internal_help = False
                    continue
                if inside_internal_help:
                    continue
                body = _read_formatted_text_block(text_data, struct.unpack_from("<I", record, 0x23)[0])
                plain_lines, uhf_lines = _split_decoded_text(body)
                entries.append((title, plain_lines, uhf_lines, [], []))
            help_topics = add_section("Nápověda", entries)
            _link_help_topic_references(help_topics)

        pair = self._read_pair(siblings, "DBSNFO")
        database_version = None
        if pair is not None:
            index_data, text_data = pair
            records = _records(index_data, 42)
            if records:
                record = records[0]
                database_version = decode_version_code(struct.unpack_from(">H", record, 0x0C)[0])
                entries = []
                for title, offset_position in (
                    ("Upozornění", 0x0E),
                    ("Finanční přispěvatelé", 0x12),
                    ("Závěrečné informace", 0x16),
                    ("Černá listina", 0x1A),
                    ("Rady a tipy", 0x1E),
                    ("Informace o databázi", 0x26),
                ):
                    body = _read_formatted_text_block(
                        text_data,
                        struct.unpack_from("<I", record, offset_position)[0],
                    )
                    if body:
                        plain_lines, uhf_lines = _split_decoded_text(body)
                        entries.append((title, plain_lines, uhf_lines, [], []))
                add_section("Informace", entries)

        source_files = [name for name in GAME_CHEATER_DATABASE_FILES if name in siblings]
        metadata: dict[str, object] = {
            "title": "Game-Cheater 9.02",
            "author": "Jiří Kalous",
            "language": "cs",
            "text_encoding": "utf-8",
            "source_encoding": "cp852",
            "metadata_already_decoded": True,
            "source_files": source_files,
            "record_count": len(topics),
            "transport_metadata_keys": ["record_count"],
        }
        if database_version:
            metadata["database_version"] = database_version
            metadata["transport_metadata_keys"].append("database_version")

        return HelpDocument(
            format_name="game-cheater",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            contents=contents,
            metadata=metadata,
            binary_data=data,
        )

    @staticmethod
    def _read_pair(siblings: dict[str, Path], stem: str) -> tuple[bytes, bytes] | None:
        index_path = siblings.get(f"{stem}.000")
        text_path = siblings.get(f"{stem}.T00")
        if index_path is None or text_path is None:
            return None
        return index_path.read_bytes(), text_path.read_bytes()
