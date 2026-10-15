"""Validated Sidekick 1 screen contexts with explicit intra-context pages."""

from __future__ import annotations

from dataclasses import dataclass
import re

from ..base import (
    ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord,
    build_directional_nav_items,
)
from ..codepages import decode_bytes
from ..uhf_markup import UhfLinkSpan, UhfStyleSpan, format_uhf_link, render_uhf_line


_CONTEXT_ZERO = b"\x01\x0c\x02Help text #0\x00"
_ATTRIBUTES = {1, 2, 4}


def is_sidekick1_binary(data: bytes) -> bool:
    """Recognize the observed English screen-stream family, not a CRC/version."""
    return data[2:2 + len(_CONTEXT_ZERO)] == _CONTEXT_ZERO


@dataclass(frozen=True, slots=True)
class _Context:
    offset: int
    rows: int
    columns: int
    pages: tuple[bytes, ...]


def _contexts(data: bytes) -> list[_Context]:
    if not is_sidekick1_binary(data) or len(data) > 65536:
        raise ValueError("Not a supported Sidekick 1 help stream.")
    result: list[_Context] = []
    position = 2
    while position < len(data):
        if data[position] == 0x1A:
            tail = len(data) - position
            if tail > 1 and (tail > 128 or len(data) % 128):
                raise ValueError("Invalid Sidekick 1 EOF record padding.")
            break
        if position + 2 >= len(data):
            raise ValueError("Truncated Sidekick 1 context header.")
        rows, columns = data[position:position + 2]
        if not (1 <= rows <= 23 and 1 <= columns <= 78):
            raise ValueError(f"Invalid Sidekick 1 dimensions at offset {position}.")
        end = data.find(b"\x00", position + 2)
        if end < 0:
            raise ValueError(f"Unterminated Sidekick 1 context at offset {position}.")
        result.append(_Context(position, rows, columns, tuple(data[position + 2:end].split(b"\x03"))))
        position = end + 1
    return result


def _display_text(raw: bytes) -> str:
    # The native printer writes these VGA cells; they are not TAB/DEL actions.
    return decode_bytes(raw, "cp437").replace("\t", "○").replace("\x7f", "⌂")


def _page(data: bytes, attribute: int, context: _Context,
          next_context: int | None) -> tuple[list[bytes], list[str], int]:
    raw_lines: list[bytes] = []
    line_styles: list[list[UhfStyleSpan]] = []
    line = bytearray()
    spans: list[UhfStyleSpan] = []
    start = 0

    def finish_span() -> None:
        nonlocal start
        if len(line) > start:
            spans.append(UhfStyleSpan(start, len(line), bold=attribute == 1, underline=attribute == 4))
        start = len(line)

    def finish_line() -> None:
        nonlocal start
        finish_span()
        if len(line) > context.columns:
            raise ValueError(f"Sidekick 1 line exceeds its declared width at offset {context.offset}.")
        raw_lines.append(bytes(line))
        line_styles.append(list(spans))
        line.clear()
        spans.clear()
        start = 0

    position = 0
    while position < len(data):
        value = data[position]
        position += 1
        if value in _ATTRIBUTES:
            finish_span()
            attribute = value
        elif value == 13:
            if position == len(data) or data[position] != 10:
                raise ValueError("Unsupported Sidekick 1 bare cursor return.")
            position += 1
            finish_line()
        elif value in (8, 10):
            raise ValueError("Unsupported Sidekick 1 cursor movement.")
        elif value == 0xFF:
            raise ValueError("Unsupported Sidekick 1 raw-character escape.")
        else:
            line.append(value)
    finish_line()
    if len(raw_lines) > context.rows:
        raise ValueError(f"Sidekick 1 page exceeds its declared height at offset {context.offset}.")
    last_text_line = next((index for index in range(len(raw_lines) - 1, -1, -1)
                           if raw_lines[index].strip(b" ")), None)
    content: list[str] = []
    for index, (raw, styles) in enumerate(zip(raw_lines, line_styles)):
        links: list[UhfLinkSpan] = []
        # The word is authored text, not a source hotspot. Only the actual 03
        # page boundary supplies a target for this terminal continuation cue.
        if next_context is not None and index == last_text_line:
            marker = re.search(rb"(?<!\w)More\.\.[ ]*$", raw)
            if marker:
                links.append(UhfLinkSpan(marker.start(), marker.start() + 6, next_context))
        content.append(render_uhf_line(
            _display_text(raw), style_spans=styles, link_spans=links,
            link_formatter=lambda span, label: format_uhf_link(label, topic_id=span.target_context),
        ))
    return raw_lines, content, attribute


class Sidekick1Reader(HelpReaderBase):
    """Keep source context IDs; append continuation-page IDs without collisions."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        records = _contexts(data)
        topics: list[TopicRecord] = []
        index: list[IndexEntry] = []
        contents: list[ContentNode] = []
        descriptors: list[dict[str, object]] = []
        next_page_id = len(records)
        home_id = 1 if len(records) > 1 else 0
        for context_id, context in enumerate(records):
            page_ids = [context_id, *range(next_page_id, next_page_id + len(context.pages) - 1)]
            next_page_id += len(context.pages) - 1
            attribute = 2
            heading = ""
            node: ContentNode | None = None
            for number, (page_id, page) in enumerate(zip(page_ids, context.pages)):
                next_context = page_ids[number + 1] if number + 1 < len(page_ids) else None
                raw_lines, content, attribute = _page(page, attribute, context, next_context)
                if number == 0:
                    label = next((line.strip(b" ") for line in raw_lines if line.strip(b" ")),
                                 f"Context {context_id}".encode("ascii"))
                    heading = _display_text(label)
                    if context_id:
                        index.append(IndexEntry(label=label, context_id=context_id))
                        node = ContentNode(label=heading, topic_id=context_id)
                        contents.append(node)
                title = heading if number == 0 else f"{heading} — Page {number + 1}"
                topic = TopicRecord(context_id=page_id, raw_lines=raw_lines, names=[title], uhf_content=content,
                                    is_help_contents=page_id == home_id,
                                    prev_context=page_ids[number - 1] if number else None,
                                    next_context=next_context)
                topic.nav_items = build_directional_nav_items(topic)
                topics.append(topic)
                if number and node is not None:
                    node.children.append(ContentNode(label=f"Page {number + 1}", topic_id=page_id))
            descriptors.append({"context_id": context_id, "offset": context.offset,
                                "rows": context.rows, "columns": context.columns, "page_ids": page_ids})
        return HelpDocument(format_name="sidekick1", source_name=self.source_name, topics=topics,
                            index_entries=index, contents=contents, metadata={
                                "title": "Sidekick Help System", "text_encoding": "cp437",
                                "metadata_already_decoded": True, "help_contents_topic_id": home_id,
                                "display_width": max(record.columns for record in records),
                                "height": max(record.rows for record in records),
                                "sidekick_version_tag": int.from_bytes(data[:2], "little"),
                                "sidekick_contexts": descriptors,
                                "transport_metadata_keys": ["sidekick_version_tag", "sidekick_contexts"],
                            })
