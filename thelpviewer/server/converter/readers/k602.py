"""Reader for Kartoteka 602 `K6HLP` help files."""

from __future__ import annotations

from dataclasses import dataclass
import re
import struct

from ..base import HelpDocument, IndexEntry, TopicRecord, ensure_document_index
from .software602_graphics import plain_graphics_line, render_graphics_line
from .t602_310 import _TEXT602_UI_THEME


K602_MAGIC = b"\x0aK6HLP"
K602_TABLE_OFFSET = 0x0F
K602_TABLE_ENTRY_SIZE = 6
K602_TABLE_ENTRY_COUNT = 256
K602_TABLE_END = K602_TABLE_OFFSET + K602_TABLE_ENTRY_COUNT * K602_TABLE_ENTRY_SIZE
K602_MAX_COLUMNS = 70


@dataclass(frozen=True, slots=True)
class K602TopicEntry:
    context_id: int
    offset: int
    size: int


def is_k602_binary(data: bytes) -> bool:
    """Return True when the buffer looks like a Kartoteka 602 help file."""
    return data.startswith(K602_MAGIC)


class K602Reader:
    """Parse one Kartoteka 602 `K6HLP` help file into a HelpDocument."""

    def __init__(self, source_name: str = "", source_path=None) -> None:
        self.source_name = source_name
        self.source_path = source_path

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_k602_binary(data):
            raise ValueError("Input is not a Kartoteka 602 K6HLP help file.")

        table_entries = _iter_table_entries(data)
        entries = [K602TopicEntry(index, offset, size)
                   for index, offset, size in table_entries if offset]
        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []

        for entry in entries:
            raw_lines = _parse_topic_lines(data, entry)
            try:
                title = _topic_title(raw_lines, entry.context_id)
                uhf_content = _render_topic_lines(raw_lines)
            except ValueError as error:
                raise ValueError(f"K602 topic {entry.context_id}: {error}") from error
            topic = TopicRecord(
                context_id=entry.context_id,
                raw_lines=[],
                names=[title],
                uhf_content=uhf_content,
            )
            topics.append(topic)
            if _is_indexable_topic(title, raw_lines):
                index_entries.append(IndexEntry(
                    label=title.encode("utf-8"),
                    context_id=entry.context_id,
                ))

        return ensure_document_index(HelpDocument(
            format_name="k602",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata={
                "title": "Kartotéka 602",
                "stamp": data[1:11].decode("ascii", errors="replace"),
                "text_encoding": "utf-8",
                "source_encoding": "software602-direct",
                "display_width": K602_MAX_COLUMNS,
                "table_entry_count": len(table_entries),
                "topic_count": len(entries),
                "ui": dict(_TEXT602_UI_THEME),
            },
            binary_data=data,
        ))


def _iter_table_entries(data: bytes) -> list[tuple[int, int, int]]:
    file_size = _declared_file_size(data)
    if file_size != len(data):
        raise ValueError("K602 declared file size does not match input length.")
    if file_size < K602_TABLE_END:
        raise ValueError("K602 topic table is truncated.")

    entries: list[tuple[int, int, int]] = []
    # The original loader reads 0x60F header bytes and addresses entry C as
    # header + 15 + 6*C, for a byte-sized context. Initial zero slots are part
    # of the directory, not reserved header bytes or a one-based numbering.
    for index in range(K602_TABLE_ENTRY_COUNT):
        position = K602_TABLE_OFFSET + index * K602_TABLE_ENTRY_SIZE
        offset, size = struct.unpack_from("<IH", data, position)
        # Native lookup tests only the DWORD offset for an unused slot.
        # A populated zero-byte topic is valid; unused size WORDs are ignored.
        if offset and (offset < K602_TABLE_END or offset + size > file_size):
            raise ValueError(f"K602 topic table entry {index} has an invalid payload range.")
        entries.append((index, offset, size))
    return entries


def _declared_file_size(data: bytes) -> int:
    if len(data) < 15:
        raise ValueError("K602 file is too small.")
    return struct.unpack_from("<I", data, 11)[0]


def _parse_topic_lines(data: bytes, entry: K602TopicEntry) -> list[bytes]:
    lines: list[bytes] = []
    position = entry.offset
    end = entry.offset + entry.size
    while position < end:
        line_length = data[position]
        position += 1
        if position + line_length > end:
            raise ValueError(f"K602 topic {entry.context_id} has truncated line data.")
        lines.append(data[position:position + line_length])
        position += line_length
    if position != end:
        raise ValueError(f"K602 topic {entry.context_id} does not end on a line boundary.")
    return lines


def _topic_title(raw_lines: list[bytes], context_id: int) -> str:
    for raw_line in raw_lines:
        title = _clean_title(plain_graphics_line(raw_line))
        if title and not _is_rule_text(title):
            return title
    return f"Topic {context_id}"


def _render_topic_lines(raw_lines: list[bytes]) -> list[str]:
    content: list[str] = []
    for raw_line in raw_lines:
        content.append(render_graphics_line(raw_line).rstrip())
    while content and content[0] == "":
        content.pop(0)
    while content and content[-1] == "":
        content.pop()
    return content


def _clean_title(title: str) -> str:
    title = title.strip(" \t│|┌┐└┘─═■█▄▀")
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        return ""

    tokens = title.split(" ")
    cleaned_tokens: list[str] = []
    single_run: list[str] = []
    for token in tokens:
        if len(token) == 1 and token.isalpha():
            single_run.append(token)
            continue
        if single_run:
            cleaned_tokens.append("".join(single_run) if len(single_run) >= 3 else " ".join(single_run))
            single_run = []
        cleaned_tokens.append(token)
    if single_run:
        cleaned_tokens.append("".join(single_run) if len(single_run) >= 3 else " ".join(single_run))
    return " ".join(cleaned_tokens).strip()


def _is_indexable_topic(title: str, raw_lines: list[bytes]) -> bool:
    # Work from source cells, not tag-stripping that could erase literal [b].
    nonblank = [line for raw in raw_lines if (line := plain_graphics_line(raw))]
    if not nonblank:
        return False

    if len(nonblank) <= 2:
        first_line = nonblank[0]
        second_line = nonblank[1] if len(nonblank) == 2 else ""
        if _clean_title(first_line) == title and (not second_line or _is_rule_text(second_line)):
            return False

    return True


def _is_rule_text(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and all(char in "■█▄▀─═-=┌┐└┘│ " for char in stripped)


K602HelpReader = K602Reader
