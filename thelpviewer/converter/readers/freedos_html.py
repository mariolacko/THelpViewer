"""Import FreeDOS HHSTNDRD HTML help archives into one linked document."""

from __future__ import annotations

from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZipFile

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from ..uhf_markup import escape_uhf_text, format_uhf_link


def is_freedos_html_archive(path, data: bytes) -> bool:
    if path.name.upper() != "HHSTNDRD.ZIP" or not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with ZipFile(BytesIO(data)) as archive:
            return "help/index.htm" in {name.lower() for name in archive.namelist()}
    except BadZipFile:
        return False


def _resolve_link(source: str, href: str, ids: dict[str, int]) -> int | None:
    parsed = urlsplit(href)
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
    return ids.get("/".join(parts).lower())


class _PageParser(HTMLParser):
    def __init__(self, source: str, ids: dict[str, int]):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.ids = ids
        self.title = ""
        self.lines: list[str] = []
        self.line = ""
        self.in_title = False
        self.in_head = False
        self.in_pre = False
        self.skip = 0
        self.link_open = False

    def _newline(self) -> None:
        self.lines.append(self.line.rstrip())
        self.line = ""

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
                    self.line = "• "
                elif tag in ("h1", "h2", "h3"):
                    self.line = "[b]"
            case "td" | "th" if self.line.strip():
                self.line += "  |  "
            case "a" if not self.in_head:
                target = _resolve_link(self.source, values.get("href") or "", self.ids)
                if target is not None:
                    self.line += f"[link:topic={target}]"
                    self.link_open = True
            case "b" | "strong" if not self.in_head:
                self.line += "[b]"

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
                    self.line += "[/b]"
                self._newline()
            case "a" if self.link_open:
                self.line += "[/link]"
                self.link_open = False
            case "b" | "strong" if not self.in_head:
                self.line += "[/b]"

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
                self.line += escape_uhf_text(chunk.replace("\r", ""))
        else:
            normalized = " ".join(data.split())
            if normalized:
                if self.line and not self.line.endswith(" ") and data[:1].isspace():
                    self.line += " "
                self.line += escape_uhf_text(normalized)

    def finish(self) -> tuple[str, list[str]]:
        if self.line:
            self._newline()
        compact: list[str] = []
        for line in self.lines:
            if line or (compact and compact[-1]):
                compact.append(line)
        return self.title.strip(), compact


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
            topics: list[TopicRecord] = []
            index: list[IndexEntry] = []
            sections: dict[str, ContentNode] = {}
            for info in files:
                source = info.filename
                parser = _PageParser(source, ids)
                parser.feed(archive.read(info).decode("utf-8", errors="replace"))
                title, content = parser.finish()
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
