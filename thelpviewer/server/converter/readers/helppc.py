"""Reader for HelpPC 2.10's documented text databases."""

from __future__ import annotations

import re

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from ..uhf_markup import UhfLinkSpan, UhfStyleSpan, format_uhf_link, render_uhf_line


_DISPLAY_COLUMNS = 80


def _lookup_key(value: str) -> str:
    return re.sub(r" {2,}", " ", value.strip()).casefold()


def is_helppc_source(data: bytes) -> bool:
    lines = data.splitlines()
    return bool(lines and lines[0].startswith(b"@") and any(line.startswith(b":") for line in lines[1:80]))


def _link_segments(text: str):
    parts: list[str] = []
    in_link = False
    position = 0
    while position < len(text):
        if text[position] == "~":
            if text[position:position + 2] == "~~":
                parts.append("~")
                position += 2
                continue
            yield "".join(parts), in_link
            parts.clear()
            in_link = not in_link
        else:
            parts.append(text[position])
        position += 1
    # An unterminated native link marker is still a control, not a displayed
    # tilde. Keep its trailing text without inventing a complete link target.
    yield "".join(parts), False


def _display_line(raw: bytes, keys: dict[str, tuple[str, int]],
                  source_name: str) -> tuple[bytes, str] | None:
    if not raw:
        return b"", ""
    marker, body = raw[:1], raw[1:]
    if marker not in (b"%", b"^", b" ", b"\t"):
        return None
    if marker == b"^":
        if len(body) > _DISPLAY_COLUMNS:
            raise ValueError("HelpPC centered line exceeds the 80-column runtime limit")
        # HELPPC.COM computes this from strlen(source + 1), before expanding
        # tabs or consuming tilde controls. Do not center a rendered UHF string.
        origin = (_DISPLAY_COLUMNS - len(body)) // 2
    else:
        origin = 8 if marker == b"\t" else 1
    visible = " " * origin
    links: list[UhfLinkSpan] = []

    def append(text: str) -> None:
        nonlocal visible
        for number, part in enumerate(text.split("\t")):
            if number:
                visible += " " * (8 - len(visible) % 8)
            visible += part

    for text, is_link in _link_segments(body.decode("cp437")):
        start = len(visible)
        append(text)
        if is_link:
            target = keys.get(_lookup_key(text))
            if target:
                filename, topic_id = target
                links.append(UhfLinkSpan(
                    start, len(visible), topic_id,
                    target_source_file=filename if filename.casefold() != source_name.casefold() else None,
                ))
    styles = [UhfStyleSpan(origin, len(visible), bold=True)] if marker in (b"%", b"^") else []
    return visible.encode("cp437"), render_uhf_line(
        visible, style_spans=styles, link_spans=links,
        link_formatter=lambda span, label: format_uhf_link(
            label, topic_id=span.target_context, source_file=span.target_source_file,
        ),
    )


def _parse_source(filename: str, data: bytes) -> tuple[str, list[tuple[list[str], list[bytes]]]]:
    if not is_helppc_source(data):
        raise ValueError(f"Not a HelpPC text database: {filename}")
    lines = data.splitlines()
    title = lines[0][1:].decode("cp437").strip()
    records: list[tuple[list[str], list[bytes]]] = []
    for line in lines[1:]:
        if line.startswith(b":"):
            names = [name.strip() for name in line.decode("cp437")[1:].split(":") if name.strip()]
            if names:
                records.append((names, []))
        elif records:
            records[-1][1].append(line)
    return title, records


def _build_document(source_name: str, sources: list[tuple[str, bytes]]) -> HelpDocument:
    parsed = {filename: _parse_source(filename, data) for filename, data in sources}
    keys: dict[str, tuple[str, int]] = {}
    for filename in sorted(parsed, key=str.casefold):
        for topic_id, (names, _lines) in enumerate(parsed[filename][1], start=1):
            for name in names:
                keys.setdefault(_lookup_key(name), (filename, topic_id))

    title, records = parsed[source_name]

    topics: list[TopicRecord] = []
    index: list[IndexEntry] = []
    contents: list[ContentNode] = []
    section = ContentNode(label=title)
    for next_id, (names, lines) in enumerate(records, start=1):
        content: list[str] = []
        raw_lines: list[bytes] = []
        for raw in lines:
            display = _display_line(raw, keys, source_name)
            if display is None:
                continue
            plain, rendered = display
            content.append(rendered)
            raw_lines.append(plain)
        topics.append(TopicRecord(
            context_id=next_id, raw_lines=raw_lines, names=names,
            index_terms=[name.encode("cp437") for name in names], uhf_content=content,
        ))
        for name in names:
            index.append(IndexEntry(label=name.encode("cp437"), context_id=next_id))
        section.children.append(ContentNode(label=names[0], topic_id=next_id))
    contents.append(section)
    return HelpDocument(
        format_name="helppc", source_name=source_name, topics=topics,
        index_entries=index, contents=contents,
        metadata={"title": title, "text_encoding": "cp437", "language": "en",
                  "display_width": _DISPLAY_COLUMNS},
    )


class HelpPCReader(HelpReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        sources = [(self.source_name, data)]
        if self.source_path is not None:
            for path in sorted(self.source_path.parent.iterdir()):
                if path.is_file() and path.name.casefold() != self.source_name.casefold() and path.suffix.lower() == ".txt":
                    sibling = path.read_bytes()
                    if is_helppc_source(sibling):
                        sources.append((path.name, sibling))
        return _build_document(self.source_name, sources)
