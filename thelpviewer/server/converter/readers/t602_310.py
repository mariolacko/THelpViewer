"""Software602's +1-encoded Turbo Vision THelpTopic / THelpIndex stream."""

from __future__ import annotations

import struct

from ..base import HelpDocument, IndexEntry, TopicRecord
from .software602_graphics import decode_help_byte
from .tvision_help import TVHelpTopic, paragraph_lines, read_help_topic
from ..uhf_markup import UhfLinkSpan, format_uhf_link, render_uhf_line

# ─── Format detection ────────────────────────────────────────────────────────

_TEXT602_HDR = b'Text602 - help'
_CALC602_HDR = b'Calc602 - help'
_TEXT602_COLUMNS = 78

_TEXT602_UI_THEME: dict[str, str] = {
    "window": "#005454",
    "text": "#a8fcfc",
    "link": "#a8a800",
    "title": "#a8a800",
    "title_passive": "#005454",
    "title_text": "#005454",
    "title_text_passive": "#a8a800",
    "frame": "#a8a800",
    "frame_passive": "#a8a800",
    "icon": "#005454",
    "icon_passive": "#a8a800",
    "page_area": "#005454",
    "hover_bg": "#a8a800",
    "hover_fg": "#005454",
    "arrow_bg": "#a8a800",
    "arrow_fg": "#005454",
    "scroll_glyph": "#a8a800",
    "thumb_bg": "#a8a800",
    "thumb_fg": "#005454",
    "code_bg": "#005454",
    "code_text": "#a8fcfc",
}


def is_t602_310_binary(data: bytes) -> bool:
    """Return True when *data* looks like a Text602 or Calc602 help file."""
    return data.startswith(_TEXT602_HDR) or data.startswith(_CALC602_HDR)


class _T602Parser:
    def __init__(self, data: bytes) -> None:
        self.data = data
        crlf = data.find(b'\r\n')
        if crlf < 0:
            raise ValueError('Text602/Calc602: missing ASCII header terminator')
        try:
            self.file_header_str = data[:crlf].decode('ascii')
        except UnicodeDecodeError as exc:
            raise ValueError('Text602/Calc602: invalid ASCII header') from exc
        header = crlf + 2
        self.topic_start = header + 8
        if self.topic_start > len(data):
            raise ValueError('Text602/Calc602: incomplete binary header')
        size, self.anchor_offset = struct.unpack_from('<II', data, header)
        if size != len(data) - (header + 4):
            raise ValueError('Text602/Calc602: declared file size does not match input')
        if not self.topic_start <= self.anchor_offset <= len(data) - 4:
            raise ValueError('Text602/Calc602: anchor table points outside the body')
        marker, count = struct.unpack_from('<HH', data, self.anchor_offset)
        if marker != 0x2711:
            raise ValueError('Text602/Calc602: invalid anchor table marker')
        if self.anchor_offset + 4 + count * 4 != len(data):
            raise ValueError('Text602/Calc602: incomplete anchor table or unexpected trailing bytes')
        self.anchors = {}
        for context in range(count):
            offset = struct.unpack_from('<I', data, self.anchor_offset + 4 + context * 4)[0]
            if offset == 0xFFFFFFFF:
                continue
            if not self.topic_start <= offset <= self.anchor_offset - 6:
                raise ValueError(f'Text602/Calc602: anchor {context} points outside the body')
            if data[offset:offset + 2] != b'\x10\x27':
                raise ValueError(f'Text602/Calc602: anchor {context} has an invalid topic object type')
            self.anchors[context] = offset

    def parse(self) -> list[TVHelpTopic]:
        topics = []
        offsets = sorted(set(self.anchors.values()))
        position = self.topic_start
        while position < self.anchor_offset:
            limit = next((offset for offset in offsets if offset > position), self.anchor_offset)
            topic = read_help_topic(self.data, position, limit, format_name='Text602/Calc602')
            topics.append(topic)
            position = topic.end
        if set(self.anchors.values()) - {topic.offset for topic in topics}:
            raise ValueError('Text602/Calc602: anchor does not address an exact topic object')
        return topics


def _decode_paragraph(text: bytes) -> bytes:
    # Original THelpTopic.Load decrements every stored byte, including controls.
    return bytes((value - 1) & 0xFF for value in text)


def _decode_line(text: bytes) -> str:
    return ''.join(decode_help_byte(value) for value in text)


def _topic_rows(topic: TVHelpTopic):
    total = 0
    for wrap, stored in topic.paragraphs:
        text = _decode_paragraph(stored)
        for start, end, row in paragraph_lines(text, wrap, _TEXT602_COLUMNS):
            yield total + start, total + end, row
        total += len(text)


def _topic_title(topic: TVHelpTopic, context: int) -> str:
    for _start, _end, row in _topic_rows(topic):
        title = _decode_line(row).strip()
        if title:
            return title
    return f'Topic_{context}'


def _render_topic(topic: TVHelpTopic, targets: dict[int, int]) -> list[str]:
    content = []
    for start, _end, row in _topic_rows(topic):
        spans = []
        for target, position, length in topic.crossrefs:
            first = max(position - 1, start) - start
            last = min(position - 1 + length, start + len(row)) - start
            if last > first:
                spans.append(UhfLinkSpan(first, last, target_context=targets[target]))
        if len(row) in (76, 77) and set(row) == {0x98} and not spans:
            content.append('[rule]')
        else:
            content.append(render_uhf_line(_decode_line(row), link_spans=spans,
                                         link_formatter=lambda span, label: format_uhf_link(
                                             label, topic_id=span.target_context)))
    return content


class T602310Reader:
    def __init__(self, source_name: str = '', source_path=None) -> None:
        self.source_name = source_name
        self.source_path = source_path

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_t602_310_binary(data):
            raise ValueError('Input is not a Software602 Text602/Calc602 help file.')
        parser = _T602Parser(data)
        records = parser.parse()
        by_offset = {}
        for context, offset in parser.anchors.items():
            by_offset.setdefault(offset, []).append(context)
        # Native contexts identify indexed objects. Preserve unindexed physical
        # objects in a disjoint address-derived UHF namespace above WORD IDs.
        primary = {record.offset: by_offset.get(record.offset, [65536 + record.offset])[0]
                   for record in records}
        targets = {context: primary[offset] for context, offset in parser.anchors.items()}
        missing = {context for record in records for context, _position, _length in record.crossrefs
                   if context not in targets}
        if missing:
            raise ValueError('Text602/Calc602: missing cross-reference contexts: '
                             + ', '.join(str(context) for context in sorted(missing)))
        topics, index = [], []
        for record in records:
            context = primary[record.offset]
            title = _topic_title(record, context)
            topics.append(TopicRecord(context_id=context, raw_lines=[], names=[title],
                                      alias_contexts=by_offset.get(record.offset, [context])[1:],
                                      uhf_content=_render_topic(record, targets)))
            index.append(IndexEntry(title.encode('utf-8'), context))
        return HelpDocument(format_name='calc602' if data.startswith(_CALC602_HDR) else 'text602',
                            source_name=self.source_name, topics=topics, index_entries=index,
                            metadata={'text_encoding': 'utf-8', 'source_encoding': 'software602-plus1',
                                      'stamp': parser.file_header_str, 'display_width': _TEXT602_COLUMNS,
                                      'ui': dict(_TEXT602_UI_THEME)}, binary_data=data)
