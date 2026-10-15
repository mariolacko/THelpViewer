"""Uncompiled DOS text, MicroCalc pages and Turbo Prolog help clauses."""

from __future__ import annotations

from pathlib import Path
import re

from ..base import (ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord,
                    build_directional_nav_items)
from ..codepages import decode_bytes
from ..uhf_markup import UhfStyleSpan, escape_uhf_text, render_uhf_line


def _text_payload(data: bytes, controls: set[int]) -> bytes | None:
    payload = data.partition(b"\x1a")[0]
    if (b"\n" not in payload or not any(65 <= value <= 90 or 97 <= value <= 122 for value in payload)
            or any(value < 32 and value not in controls for value in payload)):
        return None
    return payload


def is_microcalc_help(data: bytes) -> bool:
    payload = _text_payload(data, {2, 9, 10, 13})
    return payload is not None and any(line.startswith(b".PA") for line in payload.splitlines())


def is_dos_text_help(data: bytes) -> bool:
    payload = _text_payload(data, {9, 10, 13})
    return (payload is not None and not payload.lstrip().startswith(b"h(")
            and not any(line.startswith(b".PA") for line in payload.splitlines()))


_HELP_CLAUSE = re.compile(rb'\s*h\(\s*"((?:\\.|[^"\\])*)"\s*\)\s*\.?', re.DOTALL)
_ESCAPES = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord('"'): b'"', ord("\\"): b"\\"}


def _prolog_records(data: bytes) -> list[bytes]:
    payload = data.partition(b"\x1a")[0]
    position = 0
    records: list[bytes] = []
    while payload[position:].strip():
        match = _HELP_CLAUSE.match(payload, position)
        if match is None:
            raise ValueError("Malformed Turbo Prolog help clause.")
        raw = match.group(1)
        text = bytearray()
        index = 0
        while index < len(raw):
            value = raw[index]
            index += 1
            if value == ord("\\"):
                if index == len(raw) or raw[index] not in _ESCAPES:
                    raise ValueError("Unsupported Turbo Prolog help string escape.")
                text.extend(_ESCAPES[raw[index]])
                index += 1
            else:
                if value < 32 and value not in (9, 10, 13):
                    raise ValueError("Binary data inside Turbo Prolog help string.")
                text.append(value)
        records.append(bytes(text))
        position = match.end()
    if not records:
        raise ValueError("Empty Turbo Prolog help database.")
    return records


def is_prolog_help_source(data: bytes) -> bool:
    if not data.lstrip().startswith(b"h("):
        return False
    try:
        _prolog_records(data)
    except ValueError:
        return False
    return True


def _page_title(lines: list[bytes], fallback: str) -> str:
    for raw in lines:
        title = decode_bytes(raw, "cp437").strip()
        if any(character.isalnum() for character in title):
            return title
    return fallback


def _document(source_name: str, format_name: str, pages: list[tuple[list[bytes], list[str]]],
              *, title: str = "", ui: dict[str, str] | None = None) -> HelpDocument:
    topics: list[TopicRecord] = []
    index: list[IndexEntry] = []
    contents: list[ContentNode] = []
    for number, (raw_lines, content) in enumerate(pages, start=1):
        name = _page_title(raw_lines, f"Page {number}")
        topic = TopicRecord(context_id=number, raw_lines=raw_lines, names=[name], uhf_content=content,
                            is_help_contents=number == 1,
                            prev_context=number - 1 if number > 1 else None,
                            next_context=number + 1 if number < len(pages) else None)
        topic.nav_items = build_directional_nav_items(topic)
        topics.append(topic)
        index.append(IndexEntry(label=name.encode("cp437", errors="replace"), context_id=number))
        contents.append(ContentNode(label=name, topic_id=number))
    metadata: dict[str, object] = {"title": title or Path(source_name).stem,
        "text_encoding": "cp437", "metadata_already_decoded": True,
        "display_width": 80, "help_contents_topic_id": 1}
    if ui is not None:
        metadata["ui"] = ui
    return HelpDocument(format_name=format_name, source_name=source_name, topics=topics,
                        index_entries=index, contents=contents, metadata=metadata)


class DosTextHelpReader(HelpReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_dos_text_help(data):
            raise ValueError("Not an uncompiled DOS text help file.")
        lines = [line.expandtabs(8) for line in data.partition(b"\x1a")[0].splitlines()]
        return _document(self.source_name, "dos-text", [(lines, [escape_uhf_text(decode_bytes(line, "cp437"))
                                                               for line in lines])])


def _microcalc_page(lines: list[bytes]) -> tuple[list[bytes], list[str]]:
    bold = reverse = False
    foreground, background = 7, 0
    plain: list[bytes] = []
    content: list[str] = []
    for line in lines:
        visible = bytearray(b"     ")
        spans: list[UhfStyleSpan] = []
        start = 0
        for value in line:
            if value in (2, 9):
                if len(visible) > start:
                    spans.append(UhfStyleSpan(start, len(visible), fg=foreground, bg=background))
                start = len(visible)
                if value == 2:
                    bold = not bold
                    foreground, background = (14, 0) if bold else (7, 0)
                else:
                    reverse = not reverse
                    foreground, background = (0, 7) if reverse else (7, 0)
            else:
                visible.append(value)
        if len(visible) > start:
            spans.append(UhfStyleSpan(start, len(visible), fg=foreground, bg=background))
        plain.append(bytes(visible))
        content.append(render_uhf_line(decode_bytes(visible, "cp437"), style_spans=spans))
    return plain, content


class MicroCalcReader(HelpReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_microcalc_help(data):
            raise ValueError("Not a MicroCalc paginated text help file.")
        pages: list[list[bytes]] = [[]]
        for line in data.partition(b"\x1a")[0].splitlines():
            if line.startswith(b".PA"):
                pages.append([])
            else:
                pages[-1].append(line)
        return _document(self.source_name, "microcalc-text", [_microcalc_page(page) for page in pages],
                         title="MicroCalc", ui={"window": "cga:0", "text": "cga:7", "link": "cga:14"})


class PrologHelpReader(HelpReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        pages: list[tuple[list[bytes], list[str]]] = []
        for record in _prolog_records(data):
            lines = [line.expandtabs(8) for line in record.splitlines()]
            pages.append((lines, [escape_uhf_text(decode_bytes(line, "cp437")) for line in lines]))
        return _document(self.source_name, "prolog-help", pages)
