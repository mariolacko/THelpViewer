"""Reader for HelpPC 2.10's documented text databases."""

from __future__ import annotations

import re

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from ..uhf_markup import escape_uhf_text, format_uhf_link


_LINK = re.compile(r"~([^~]+)~|~~")


def _lookup_key(value: str) -> str:
    return re.sub(r" {2,}", " ", value.strip()).casefold()


def is_helppc_source(data: bytes) -> bool:
    lines = data.splitlines()
    return bool(lines and lines[0].startswith(b"@") and any(line.startswith(b":") for line in lines[1:80]))


def _linked_line(text: str, keys: dict[str, tuple[str, int]], source_name: str) -> str:
    parts: list[str] = []
    last = 0
    for match in _LINK.finditer(text):
        parts.append(escape_uhf_text(text[last:match.start()]))
        label = match.group(1)
        if label is None:
            parts.append("~")
        else:
            target = keys.get(_lookup_key(label))
            if target:
                filename, topic_id = target
                parts.append(format_uhf_link(
                    escape_uhf_text(label), topic_id=topic_id,
                    source_file=filename if filename.casefold() != source_name.casefold() else None,
                ))
            else:
                parts.append(escape_uhf_text(label))
        last = match.end()
    parts.append(escape_uhf_text(text[last:]))
    return "".join(parts)


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
            marker = raw[:1]
            if marker in (b"%", b"^"):
                raw = raw[1:]
            elif marker not in (b" ", b"\t", b""):
                continue
            decoded = raw.decode("cp437").expandtabs(8)
            rendered = _linked_line(decoded, keys, source_name)
            if marker in (b"%", b"^"):
                rendered = f"[b]{rendered}[/b]"
            content.append(rendered)
            raw_lines.append(raw)
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
        metadata={"title": title, "text_encoding": "cp437", "language": "en"},
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
