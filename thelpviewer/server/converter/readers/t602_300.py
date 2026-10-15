"""Reader for legacy Text602 3.00 `T6HLP` help files."""

from __future__ import annotations

from dataclasses import dataclass
import re
import struct

from ..base import HelpDocument, IndexEntry, TopicRecord, ensure_document_index
from .software602_graphics import plain_graphics_line, render_graphics_line
from .t602_310 import _TEXT602_UI_THEME


T6HLP_MAGIC = b"\x0aT6HLP"
T6HLP_STAMP_SIZE = 11
T6HLP_FILE_SIZE_OFFSET = 0x0B
T6HLP_TABLE_OFFSET = 0x0F
T6HLP_TABLE_ENTRIES = 256
T6HLP_TABLE_ENTRY_SIZE = 6
T6HLP_MAX_COLUMNS = 70


@dataclass(frozen=True, slots=True)
class T602300TopicEntry:
    context_id: int
    offset: int
    size: int


def is_t602_300_binary(data: bytes) -> bool:
    """Return True when *data* looks like a legacy Text602 `T6HLP` file."""
    return data.startswith(T6HLP_MAGIC)


class T602300Reader:
    """Parse one legacy Text602 3.00 `T6HLP` file into a HelpDocument."""

    def __init__(self, source_name: str = "", source_path=None) -> None:
        self.source_name = source_name
        self.source_path = source_path

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_t602_300_binary(data):
            raise ValueError("Input is not a legacy Text602 T6HLP help file.")

        entries = _parse_topic_table(data)
        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []

        for previous_entry, entry, next_entry in _with_neighbors(entries):
            raw_segments = _parse_topic_segments(data, entry)
            try:
                rendered_lines = _render_topic_lines(raw_segments)
                title = _topic_title(raw_segments, entry.context_id)
            except ValueError as error:
                raise ValueError(f"T6HLP topic {entry.context_id}: {error}") from error

            topic = TopicRecord(
                context_id=entry.context_id,
                raw_lines=[],
                names=[title],
                uhf_content=rendered_lines,
                prev_context=previous_entry.context_id if previous_entry else None,
                next_context=next_entry.context_id if next_entry else None,
            )
            topics.append(topic)
            if _is_indexable_topic(title, rendered_lines):
                index_entries.append(IndexEntry(
                    label=title.encode("utf-8"),
                    context_id=entry.context_id,
                ))

        return ensure_document_index(HelpDocument(
            format_name="text602-legacy",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata={
                "title": "Text 602 3.00",
                "stamp": data[1:T6HLP_STAMP_SIZE].decode("ascii", errors="replace"),
                "text_encoding": "utf-8",
                "source_encoding": "software602-direct",
                "display_width": T6HLP_MAX_COLUMNS,
                "table_entry_count": T6HLP_TABLE_ENTRIES,
                "topic_count": len(entries),
                "ui": dict(_TEXT602_UI_THEME),
            },
            binary_data=data,
        ))


def _with_neighbors(entries: list[T602300TopicEntry]):
    for index, entry in enumerate(entries):
        previous_entry = entries[index - 1] if index > 0 else None
        next_entry = entries[index + 1] if index + 1 < len(entries) else None
        yield previous_entry, entry, next_entry


def _declared_file_size(data: bytes) -> int:
    if len(data) < T6HLP_TABLE_OFFSET:
        raise ValueError("T6HLP file is too small.")
    return struct.unpack_from("<I", data, T6HLP_FILE_SIZE_OFFSET)[0]


def _parse_topic_table(data: bytes) -> list[T602300TopicEntry]:
    file_size = _declared_file_size(data)
    if file_size != len(data):
        raise ValueError("T6HLP declared file size does not match input length.")

    table_end = T6HLP_TABLE_OFFSET + (T6HLP_TABLE_ENTRIES * T6HLP_TABLE_ENTRY_SIZE)
    if table_end > len(data):
        raise ValueError("T6HLP topic table is truncated.")

    entries: list[T602300TopicEntry] = []
    for index in range(T6HLP_TABLE_ENTRIES):
        position = T6HLP_TABLE_OFFSET + (index * T6HLP_TABLE_ENTRY_SIZE)
        offset = struct.unpack_from("<I", data, position)[0]
        size = struct.unpack_from("<H", data, position + 4)[0]
        if offset == 0:
            continue
        if offset < table_end or offset + size > file_size:
            raise ValueError(f"T6HLP table entry {index} points outside the text area.")
        entries.append(T602300TopicEntry(
            context_id=index,
            offset=offset,
            size=size,
        ))

    return entries


def _parse_topic_segments(data: bytes, entry: T602300TopicEntry) -> list[bytes]:
    segments: list[bytes] = []
    position = entry.offset
    end = position + entry.size
    while position < end:
        line_size = data[position]
        position += 1
        if position + line_size > end:
            raise ValueError(f"T6HLP topic {entry.context_id} has truncated line data.")
        segments.append(data[position:position + line_size])
        position += line_size
    return segments


def _render_topic_lines(raw_segments: list[bytes]) -> list[str]:
    lines = [render_graphics_line(segment).rstrip() for segment in raw_segments]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _topic_title(raw_segments: list[bytes], context_id: int) -> str:
    for segment in raw_segments:
        title = _clean_title(plain_graphics_line(segment))
        if title and not _is_rule_text(title):
            return title
    return f"Topic {context_id}"


def _is_indexable_topic(title: str, content: list[str]) -> bool:
    return bool(title.strip()) and any(line.strip() for line in content)


def _clean_title(text: str) -> str:
    cleaned = text.strip(" \t│|┌┐└┘─═■█▄▀")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_rule_text(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and all(char in "■█▄▀─═-=┌┐└┘│| " for char in stripped)
