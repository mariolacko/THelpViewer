"""Import FreeDOS HHSTNDRD HTML help archives into one linked document."""

from __future__ import annotations

from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZipFile

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from ..uhf_markup import escape_uhf_text, format_uhf_link_target


_TEXT_SPACE = " \t\r\n"
_COLLAPSIBLE_SPACE = re.compile(r"[ \t\r\n]+")


def is_freedos_html_archive(path, data: bytes) -> bool:
    if path.name.upper() != "HHSTNDRD.ZIP" or not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with ZipFile(BytesIO(data)) as archive:
            return "help/index.htm" in {name.lower() for name in archive.namelist()}
    except BadZipFile:
        return False


def _resolve_link(source: str, href: str, ids: dict[str, int],
                  anchors: dict[str, dict[str, int]]) -> tuple[int, int | None] | None:
    try:
        parsed = urlsplit(href)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    target = unquote(parsed.path).replace("\\", "/")
    if not target:
        target = source
    elif target.startswith("/"):
        target = target.lstrip("/")
    else:
        target = str(PurePosixPath(source).parent / target)
    parts: list[str] = []
    for part in target.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    path = "/".join(parts).lower()
    topic_id = ids.get(path)
    if topic_id is None:
        return None
    line = anchors.get(path, {}).get(unquote(parsed.fragment)) if parsed.fragment else None
    return topic_id, line


class _PageParser(HTMLParser):
    def __init__(self, source: str, ids: dict[str, int], anchors: dict[str, dict[str, int]]):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.ids = ids
        self.anchors = anchors
        self.named_anchors: dict[str, int] = {}
        self.id_anchors: dict[str, int] = {}
        self.title = ""
        self.lines: list[str] = []
        self.line = ""
        self.line_text = ""
        self.pending_space: int | None = None
        self.inline_tags: list[tuple[str, str, str]] = []
        self.in_title = False
        self.in_head = False
        self.in_pre = False
        self.skip = 0

    def _start_inline(self, tag: str, opening: str, closing: str) -> None:
        self.inline_tags.append((tag, opening, closing))
        self.line += opening

    def _end_inline(self, tag: str) -> None:
        for index in range(len(self.inline_tags) - 1, -1, -1):
            if self.inline_tags[index][0] == tag:
                # Keep any still-active child style, even in crossed source
                # tags, without emitting unbalanced per-line UHF markup.
                self.line += "".join(item[2] for item in reversed(self.inline_tags[index:]))
                self.line += "".join(item[1] for item in self.inline_tags[index + 1:])
                del self.inline_tags[index]
                break

    def _newline(self) -> None:
        self.lines.append(
            self.line.rstrip(_TEXT_SPACE) + "".join(item[2] for item in reversed(self.inline_tags))
            if self.line_text.strip(_TEXT_SPACE) else ""
        )
        self.line = "".join(item[1] for item in self.inline_tags)
        self.line_text = ""
        self.pending_space = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        match tag:
            case "script" | "style":
                self.skip += 1
            case "head":
                self.in_head = True
            case "title":
                self.in_title = True
            case "pre":
                self._newline()
                self.in_pre = True
            case "h1" | "h2" | "h3" | "p" | "div" | "tr" | "li" | "hr" | "br" if not self.in_head:
                self._newline()
                if tag == "li":
                    self.line += "• "
                    self.line_text += "• "
                elif tag in ("h1", "h2", "h3"):
                    self._start_inline(tag, "[b]", "[/b]")
            case "td" | "th" if self.line_text.strip(_TEXT_SPACE):
                self.line += "  |  "
                self.line_text += "  |  "
            case "a" if not self.in_head and not self.skip:
                target = (_resolve_link(self.source, values.get("href") or "", self.ids, self.anchors)
                          if "href" in values else None)
                opening = f"[link:{format_uhf_link_target(topic_id=target[0], line=target[1])}]" if target else ""
                self._start_inline(tag, opening, "[/link]" if target else "")
            case "b" | "strong" if not self.in_head:
                self._start_inline(tag, "[b]", "[/b]")
        # Block tags have already started their display line. A bookmark is
        # a destination, not a hyperlink when it has no href attribute.
        if not self.in_head and not self.skip:
            if values.get("id"):
                self.id_anchors.setdefault(values["id"], len(self.lines))
            if tag == "a" and values.get("name"):
                self.named_anchors.setdefault(values["name"], len(self.lines))

    def handle_endtag(self, tag: str) -> None:
        match tag:
            case "script" | "style":
                self.skip = max(0, self.skip - 1)
            case "head":
                self.in_head = False
            case "title":
                self.in_title = False
            case "pre":
                self._newline()
                self.in_pre = False
            case "h1" | "h2" | "h3" | "p" | "div" | "tr" | "li" if not self.in_head:
                if tag in ("h1", "h2", "h3"):
                    self._end_inline(tag)
                self._newline()
            case "a":
                self._end_inline(tag)
            case "b" | "strong" if not self.in_head:
                self._end_inline(tag)

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.in_title:
            self.title += data
        if self.in_head:
            return
        if self.in_pre:
            chunks = data.split("\n")
            for index, chunk in enumerate(chunks):
                if index:
                    self._newline()
                chunk = chunk.replace("\r", "")
                self.line += escape_uhf_text(chunk)
                self.line_text += chunk
        else:
            collapsed = _COLLAPSIBLE_SPACE.sub(" ", data)
            normalized = collapsed.strip(" ")
            if normalized:
                if self.line_text and not self.line_text.endswith(" ") and (
                        self.pending_space is not None or collapsed.startswith(" ")):
                    # Insert a deferred separator at its original style/link
                    # boundary, not inside a subsequently opened inline tag.
                    position = self.pending_space if self.pending_space is not None else len(self.line)
                    self.line = self.line[:position] + " " + self.line[position:]
                    self.line_text += " "
                self.pending_space = None
                self.line += escape_uhf_text(normalized)
                self.line_text += normalized
            if collapsed.endswith(" ") and self.line_text and not self.line_text.endswith(" "):
                if self.pending_space is None:
                    self.pending_space = len(self.line)

    def finish(self) -> tuple[str, list[str], dict[str, int]]:
        if self.line_text:
            self._newline()
        compact: list[str] = []
        line_numbers: dict[int, int] = {}
        for index, line in enumerate(self.lines):
            if line or (compact and compact[-1]):
                compact.append(line)
                if line:
                    line_numbers[index] = len(compact)
        # Bookmarks between blocks land on the next text line, after the same
        # blank-line compaction used by both parsing passes. End bookmarks
        # point to the last emitted row; empty pages have no invented line.
        next_line = len(compact) or None
        for index in range(len(self.lines) - 1, -1, -1):
            next_line = line_numbers.get(index, next_line)
            if next_line is not None:
                line_numbers[index] = next_line
        anchors: dict[str, int] = {}
        for name, index in (self.named_anchors | self.id_anchors).items():
            line = line_numbers.get(index, len(compact) or None)
            if line is not None:
                anchors[name] = line
        return self.title.strip(), compact, anchors


class FreeDOSHtmlReader(HelpReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        with ZipFile(BytesIO(data)) as archive:
            files = sorted(
                (info for info in archive.infolist() if info.filename.lower().endswith((".htm", ".html")) and not info.is_dir()),
                key=lambda info: info.filename.lower(),
            )
            if not files or not any(info.filename.lower() == "help/index.htm" for info in files):
                raise ValueError("Not a FreeDOS HHSTNDRD help archive")
            if len(files) > 2000 or sum(info.file_size for info in files) > 50_000_000:
                raise ValueError("FreeDOS HTML help archive is too large")
            ids = {info.filename.lower(): number for number, info in enumerate(files, 1)}
            if len(ids) != len(files):
                raise ValueError("Ambiguous FreeDOS HTML member names")
            pages = {info.filename: archive.read(info).decode("utf-8", errors="replace") for info in files}
            anchors: dict[str, dict[str, int]] = {}
            # Forward and cross-page fragments require the destinations before
            # rendering links. Both passes use exactly the same line layout.
            for source, text in pages.items():
                parser = _PageParser(source, ids, {})
                parser.feed(text)
                _title, _content, anchors[source.lower()] = parser.finish()
            topics: list[TopicRecord] = []
            index: list[IndexEntry] = []
            sections: dict[str, ContentNode] = {}
            for info in files:
                source = info.filename
                parser = _PageParser(source, ids, anchors)
                parser.feed(pages[source])
                title, content, _anchors = parser.finish()
                title = title or PurePosixPath(source).stem
                topic_id = ids[source.lower()]
                topics.append(TopicRecord(
                    context_id=topic_id, raw_lines=[line.encode("utf-8") for line in content],
                    names=[title], index_terms=[title.encode("utf-8")], uhf_content=content,
                    is_help_contents=source.lower() == "help/index.htm",
                ))
                index.append(IndexEntry(label=title.encode("utf-8"), context_id=topic_id))
                section = source.split("/", 1)[0]
                sections.setdefault(section, ContentNode(label=section.title())).children.append(
                    ContentNode(label=title, topic_id=topic_id)
                )
        return HelpDocument(
            format_name="freedos-html", source_name=self.source_name,
            topics=topics, index_entries=index, contents=list(sections.values()),
            metadata={
                "title": "FreeDOS HTML Help", "text_encoding": "utf-8",
                "metadata_already_decoded": True, "language": "en",
                "help_contents_topic_id": ids["help/index.htm"],
            },
        )
