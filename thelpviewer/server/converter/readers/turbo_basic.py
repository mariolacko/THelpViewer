"""Turbo Basic's word-record TBH profile, not the later nibble THELP grammar."""

from __future__ import annotations

import struct

from ..base import (ContentNode, HelpDocument, HelpReaderBase, PositionedKeyword,
                    TopicRecord, ensure_document_index, render_topic_uhf_content)
from ..codepages import decode_bytes_box_aware


TURBO_BASIC_PREFIX = b"TURBO BASIC HELP FILE.\0\x1a$*$* &&&&$*$\0"


def is_turbo_basic_binary(data: bytes) -> bool:
    return data.startswith(TURBO_BASIC_PREFIX)


def text_rows(data: bytes, packed: bool) -> list[bytes]:
    """Project native FE-space packing and NUL/SOH display controls."""
    rows: dict[int, bytes] = {}
    row, position = 0, 0
    line = bytearray()
    while position < len(data):
        value = data[position]
        position += 1
        if packed and value == 0xFE:
            if position == len(data):
                raise ValueError("Truncated Turbo Basic space run")
            line.extend(b" " * data[position])
            position += 1
        elif value == 0:
            rows[row] = bytes(line)
            row += 1
            line.clear()
        elif value == 1:
            continue
        else:
            line.append(value)
        if len(line) > 65535 or row > 65535:
            raise ValueError("Turbo Basic text exceeds the bounded display range")
    if line:
        # The original consumer's final partial-row flush reads a different
        # buffer. Do not silently manufacture text for this unverified case.
        raise ValueError("Unterminated Turbo Basic text row")
    return [rows.get(number, b"") for number in range(max(rows, default=-1) + 1)]


class TurboBasicHelpReader(HelpReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_turbo_basic_binary(data):
            raise ValueError("Not a Turbo Basic help file")
        position = len(TURBO_BASIC_PREFIX)
        if data[position:position + 2] != b"\1\1":
            raise ValueError("Unsupported Turbo Basic help version")
        position += 2
        parameters = None
        contexts = None
        pages: dict[int, tuple[list[bytes], list[tuple[int, ...]]]] = {}
        current = None
        awaiting_keywords = False
        while position < len(data):
            if position + 4 > len(data):
                raise ValueError("Truncated Turbo Basic record header")
            offset = position
            kind, size = struct.unpack_from("<HH", data, position)
            position += 4
            end = position + size + (2 if kind == 4 else 0)
            if end > len(data):
                raise ValueError("Truncated Turbo Basic record payload")
            payload = data[position:end]
            if awaiting_keywords and kind != 4:
                raise ValueError("Missing Turbo Basic keyword record after text")
            match kind:
                case 0:
                    if parameters is not None or size != 10:
                        raise ValueError("Invalid Turbo Basic file header")
                    parameters = struct.unpack("<5H", payload)
                    if not all(0 < n <= 255 for n in parameters[2:4]) or parameters[4] not in {0, 1}:
                        raise ValueError("Unsupported Turbo Basic dimensions or space packing")
                case 2:
                    if parameters is None or contexts is not None or size < 2:
                        raise ValueError("Invalid Turbo Basic context directory")
                    count = struct.unpack_from("<H", payload)[0]
                    if size != 2 + 6 * count:
                        raise ValueError("Invalid Turbo Basic context directory size")
                    contexts = [struct.unpack_from("<HI", payload, 2 + 6 * i) for i in range(count)]
                case 3:
                    if contexts is None or parameters is None:
                        raise ValueError("Missing Turbo Basic headers before text")
                    pages[offset] = (text_rows(payload, bool(parameters[4])), [])
                    current = offset
                    awaiting_keywords = True
                case 4:
                    if current is None or not awaiting_keywords:
                        raise ValueError("Turbo Basic keyword record without text")
                    count = struct.unpack_from("<H", payload)[0]
                    if size != count * 12:
                        raise ValueError("Invalid Turbo Basic keyword table size")
                    pages[current][1].extend(struct.unpack_from("<8BI", payload, 2 + 12 * i) for i in range(count))
                    awaiting_keywords = False
                case _:
                    raise ValueError(f"Unsupported Turbo Basic record type {kind}")
            position = end
        if parameters is None or contexts is None or not pages or awaiting_keywords:
            raise ValueError("Incomplete Turbo Basic help file")

        identities: dict[int, list[int]] = {offset: [] for offset in pages}
        for slot, (_stored_id, offset) in enumerate(contexts):
            if offset == 0xFFFFFFFF:
                continue
            if offset not in pages:
                raise ValueError(f"Turbo Basic context {slot} does not address a text record")
            identities[offset].append(slot)
        # Continuation screens have no context slot, but native links address
        # them by absolute offset. Keep them as distinct, stable topic objects.
        for ordinal, ids in enumerate(identities.values()):
            if not ids:
                ids.append(0x10000 + ordinal)

        topics = []
        for offset, (lines, keywords) in pages.items():
            ids = identities[offset]
            links = []
            for line, first, last, _reserved, left, right, up, down, target in keywords:
                if target not in pages:
                    raise ValueError("Turbo Basic hyperlink does not address a text record")
                if not (1 <= line <= len(lines) and 1 <= first <= last <= len(lines[line - 1])):
                    raise ValueError("Turbo Basic hyperlink lies outside its text cells")
                links.append(PositionedKeyword(identities[target][0], line, first, last, (left, right, up, down)))
            title = next((decode_bytes_box_aware(raw, "cp437").strip() for raw in lines if raw.strip()), f"Screen {ids[0]}")
            topics.append(TopicRecord(context_id=ids[0], alias_contexts=ids[1:], raw_lines=lines,
                positional_keywords=links, names=[title], is_help_contents=100 in ids))
        topic_ids = {ident for ids in identities.values() for ident in ids}
        for topic in topics:
            topic.uhf_content = render_topic_uhf_content(topic,
                decode_bytes=lambda raw: decode_bytes_box_aware(raw, "cp437"), topic_ids=topic_ids)
        return ensure_document_index(HelpDocument(format_name="turbo-basic", source_name=self.source_name,
            topics=topics, index_entries=[], contents=[ContentNode(label=t.names[0], topic_id=t.context_id) for t in topics],
            metadata={"title": "Turbo Basic Help", "text_encoding": "cp437", "metadata_already_decoded": True,
                "format_version": 1, "text_version": 1, "height": parameters[2], "width": parameters[3],
                "display_width": parameters[3], "help_contents_topic_id": 100,
                "space_packing": parameters[4], "header_words": list(parameters[:2]),
                "context_directory": [list(entry) for entry in contexts],
                "text_record_offsets": {str(ids[0]): offset for offset, ids in identities.items()}}))
