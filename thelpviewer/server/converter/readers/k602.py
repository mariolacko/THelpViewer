"""Reader for Kartoteka 602 `K6HLP` help files."""

from __future__ import annotations

from dataclasses import dataclass
import re
import struct

from ..base import HelpDocument, IndexEntry, TopicRecord, ensure_document_index
from ..codepages import CP437_LOW, KAMENICKY
from ..uhf_markup import escape_uhf_text
from .t602_310 import _T602_BOX, _T602_TEXT, _TEXT602_UI_THEME


K602_MAGIC = b"\x0aK6HLP"
K602_TABLE_OFFSET = 0x75
K602_BOLD_MARKERS = {0x02, 0x04}
K602_TRAILING_ATTRS = {0x96, 0x97}


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

        entries = _parse_topic_table(data)
        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []

        for entry in entries:
            raw_lines = _parse_topic_lines(data, entry)
            title = _topic_title(raw_lines, entry.context_id)
            uhf_content = _render_topic_lines(raw_lines)
            topic = TopicRecord(
                context_id=entry.context_id,
                raw_lines=[],
                names=[title],
                uhf_content=uhf_content,
            )
            topics.append(topic)
            if _is_indexable_topic(title, uhf_content):
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
                "table_entry_count": _topic_table_entry_count(data),
                "topic_count": len(entries),
                "ui": dict(_TEXT602_UI_THEME),
            },
            binary_data=data,
        ))


def _topic_table_entry_count(data: bytes) -> int:
    return len(_iter_table_entries(data))


def _parse_topic_table(data: bytes) -> list[K602TopicEntry]:
    entries: list[K602TopicEntry] = []
    for index, offset, size in _iter_table_entries(data):
        if offset == 0 and size == 0:
            continue
        entries.append(K602TopicEntry(
            context_id=index + 1,
            offset=offset,
            size=size,
        ))
    return entries


def _iter_table_entries(data: bytes) -> list[tuple[int, int, int]]:
    file_size = _declared_file_size(data)
    if file_size != len(data):
        raise ValueError("K602 declared file size does not match input length.")

    entries: list[tuple[int, int, int]] = []
    position = K602_TABLE_OFFSET
    while position + 6 <= len(data):
        index = len(entries)
        offset = struct.unpack_from("<I", data, position)[0]
        size = struct.unpack_from("<H", data, position + 4)[0]
        next_position = position + 6
        if offset or size:
            if offset < next_position or size <= 0 or offset + size > file_size:
                break
        entries.append((index, offset, size))
        position = next_position

    if not entries:
        raise ValueError("K602 topic table is empty or malformed.")
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
        title = _clean_title(_plain_line(raw_line))
        if title and not _is_rule_text(title):
            return title
    return f"Topic {context_id}"


def _render_topic_lines(raw_lines: list[bytes]) -> list[str]:
    content: list[str] = []
    for raw_line in raw_lines:
        rendered = _render_line(raw_line).rstrip()
        content.extend(rendered.split("\n"))
    while content and content[0] == "":
        content.pop(0)
    while content and content[-1] == "":
        content.pop()
    return content


def _render_line(raw_line: bytes) -> str:
    raw_line = _strip_line_attrs(raw_line)
    parts: list[str] = []
    bold = False
    index = 0
    while index < len(raw_line):
        value = raw_line[index]
        if _is_inline_attr(raw_line, index):
            index += 1
            continue
        if value in K602_BOLD_MARKERS:
            parts.append("[/b]" if bold else "[b]")
            bold = not bold
            index += 1
            continue
        if value == 0x8D and index + 1 < len(raw_line) and raw_line[index + 1] == 0x0A:
            parts.append("\n")
            index += 2
            continue
        parts.append(escape_uhf_text(_decode_k602_byte(value)))
        index += 1
    if bold:
        parts.append("[/b]")
    return "".join(parts)


def _plain_line(raw_line: bytes) -> str:
    raw_line = _strip_line_attrs(raw_line)
    chars: list[str] = []
    index = 0
    while index < len(raw_line):
        value = raw_line[index]
        if _is_inline_attr(raw_line, index) or value in K602_BOLD_MARKERS:
            index += 1
            continue
        if value == 0x8D and index + 1 < len(raw_line) and raw_line[index + 1] == 0x0A:
            chars.append(" ")
            index += 2
            continue
        chars.append(_decode_k602_byte(value))
        index += 1
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def _clean_title(title: str) -> str:
    title = title.strip(" \t│|┌┐└┘─═■")
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


def _is_indexable_topic(title: str, content: list[str]) -> bool:
    nonblank = [line.strip() for line in content if line.strip()]
    if not nonblank:
        return False

    if len(nonblank) <= 2:
        first_line = _plain_uhf_text(nonblank[0])
        second_line = _plain_uhf_text(nonblank[1]) if len(nonblank) == 2 else ""
        if _clean_title(first_line) == title and (not second_line or _is_rule_text(second_line)):
            return False

    return True


def _plain_uhf_text(text: str) -> str:
    return text.replace("[b]", "").replace("[/b]", "").replace("[[", "[")


def _strip_line_attrs(raw_line: bytes) -> bytes:
    return raw_line.rstrip(b" " + bytes(K602_TRAILING_ATTRS))


def _is_inline_attr(raw_line: bytes, index: int) -> bool:
    value = raw_line[index]
    if value != 0x97:
        return False
    previous_value = raw_line[index - 1] if index > 0 else None
    next_value = raw_line[index + 1] if index + 1 < len(raw_line) else None
    return previous_value in K602_BOLD_MARKERS or next_value in K602_BOLD_MARKERS


def _decode_k602_byte(value: int) -> str:
    if value == 0x00:
        return " "
    if value == 0x0A:
        return "\n"
    if value == 0x0D:
        return "\u21B5"
    if value < 0x20:
        return CP437_LOW.get(value, "")
    if value < 0x80:
        return chr(value)
    return _T602_BOX.get(value, _T602_TEXT.get(value, KAMENICKY.get(value, f"[{value:02X}]")))


def _is_rule_text(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and all(char in "■▀─═-=┌┐└┘│ " for char in stripped)


K602HelpReader = K602Reader
