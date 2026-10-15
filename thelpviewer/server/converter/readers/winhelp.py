"""HC31 articles and native keyword/context targets in shared fixed-cell UHF.

The cell projection is not Windows proportional-font/pixel emulation.
Unrendered objects and unsupported macros remain explicit, not lost text.
"""

from dataclasses import dataclass
from functools import lru_cache

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord, TopicNavItem
from ..uhf_markup import UhfLinkSpan, UhfStyleSpan, format_uhf_link, render_uhf_line
from .winhelp_binary import WinHelpBTree, WinHelpFile, WinHelpTopics
from .winhelp_text import WinHelpDisplay, WinHelpLink, _Cursor, decode_font_text, macro_navigation, read_fonts, read_link


def _alias(value: int) -> str:
    return f"winhelp-hash:{value:08x}"


@dataclass(frozen=True, slots=True)
class _Cell:
    char: str
    font: int
    link: WinHelpLink | None
    origin: tuple[int, int] | None = None


class _Layout:
    def __init__(self, fonts, encoding: str, wanted=frozenset(), width: int = 80):
        self.fonts, self.encoding, self.width = fonts, encoding, width
        self.wanted = wanted
        self.font = 0
        self.link = None
        self.rows = []
        self.anchors = {}
        self.objects = []
        self.unmapped = set()
        self.row = []
        self.indent = self.first_indent = 0
        self.tabs = ()
        self.first_line = True
        self.border = None
        self.alignment = 0

    def _margin(self):
        return max(0, self.indent + (self.first_indent if self.first_line else 0))

    def _start(self):
        if not self.row:
            if self.first_line and self.border and self.border[0] & 3:
                self.rows.append([_Cell("─", self.font, None) for _ in range(self.width)])
            self.row = [_Cell(" ", self.font, None) for _ in range(min(self._margin(), self.width - 1))]

    def _finish(self, *, paragraph=False):
        gap = max(0, self.width - len(self.row))
        padding = gap if self.alignment & 0x400 else gap // 2 if self.alignment & 0x800 else 0
        if self.row and padding:
            self.row = [_Cell(" ", self.font, None) for _ in range(padding)] + self.row
        self.rows.append(self.row)
        if paragraph and self.border and self.border[0] & 9:
            self.rows.append([_Cell("─", self.font, None) for _ in range(self.width)])
        self.row = []
        self.first_line = bool(paragraph)

    def _append(self, cells):
        self._start()
        self.row.extend(cells)
        while len(self.row) > self.width:
            candidates = [i for i in range(self._margin() + 1, min(self.width + 1, len(self.row)))
                          if self.row[i].char == " "]
            if not candidates:
                break  # Preserve an oversized word instead of clipping it.
            cut = candidates[-1]
            tail = self.row[cut + 1:]
            self.row = self.row[:cut]
            self._finish()
            self._start()
            self.row.extend(tail)

    def _text(self, raw, position, offset):
        # ANSI bytes are retained in the source; special-font transcription is
        # separate from paragraph parsing and never changes address counts.
        if not raw:
            return
        text, unknown = decode_font_text(raw, self.fonts[self.font], self.encoding)
        self.unmapped.update((self.font, byte) for byte in unknown)
        self._append([_Cell(char, self.font, self.link, (position, offset + i) if (position, offset + i) in self.wanted else None)
                      for i, char in enumerate(text)])

    def _tab(self, following):
        self._start()
        stop, kind = next(((stop, kind) for stop, kind in self.tabs if stop > len(self.row)),
                          (((len(self.row) // 8) + 1) * 8, 0))
        field_width = 0
        if kind:
            for command in following:
                field_width += len(command.text)
                if command.opcode in {0x81, 0x82, 0x83, 0xFF}:
                    break
                if command.opcode == 0x8B:
                    field_width += 1
        start = stop - (field_width if kind == 1 else field_width // 2 if kind == 2 else 0)
        self._append([_Cell(" ", self.font, None) for _ in range(max(0, start - len(self.row)))])

    def record(self, record):
        display = WinHelpDisplay.read(record)
        normal_width = self.width
        total = sum(max(1, width + gap) for width, gap in display.columns)
        widths = [max(2, round(normal_width * max(1, gap + width) / total))
                  for width, gap in display.columns]
        start_line = len(self.rows) + 1
        self.anchors[(record.position, 0)] = start_line
        table_cells = {}
        native_extra = 0
        for paragraph in display.paragraphs:
            if display.columns:
                saved_rows, self.rows = self.rows, []
                saved_row, self.row = self.row, []
            metrics = paragraph.metrics
            cell_width = max(2, widths[paragraph.column] - 2) if display.columns else normal_width
            self.width = max(2, cell_width - round((metrics[4] or 0) / 12))
            self.indent = round((metrics[3] or 0) / 12)
            self.first_indent = round((metrics[5] or 0) / 12)
            self.tabs = tuple((round(stop / 12), kind) for stop, kind in paragraph.tabs)
            self.border = paragraph.border
            self.alignment = paragraph.flags
            self.first_line = True
            if not display.columns and metrics[0] and self.rows and self.rows[-1]:
                self.rows.append([])
            for index, command in enumerate(paragraph.commands):
                origin = command.text_offset + native_extra
                self._text(command.text, record.position, origin)
                opcode = command.opcode
                if opcode == 0x80:
                    if command.value >= len(self.fonts):
                        raise ValueError("WinHelp font selection outside FONT descriptors")
                    self.font = command.value
                elif opcode in {0x81, 0x82}:
                    self._finish(paragraph=opcode == 0x82)
                elif opcode == 0x83:
                    self._tab(paragraph.commands[index + 1:])
                elif opcode in {0xE0, 0xE1, 0xE2, 0xE3, 0xE6, 0xE7, 0xEA, 0xEB, 0xEE, 0xEF, 0xC8, 0xCC}:
                    self.link = read_link(command)
                elif opcode == 0x89:
                    self.link = None
                elif opcode == 0x8B:
                    self._append([_Cell("\xa0", self.font, self.link, (record.position, origin))])
                elif opcode in {0x86, 0x87, 0x88}:
                    cur = _Cursor(command.operand, "picture object")
                    kind, size = cur.integer(1), cur.long(signed=True)
                    if kind == 0x22:
                        cur.short()
                    payload = cur.take(size)
                    marker = "[Embedded object]" if kind == 5 else "\u25a7"
                    if kind in {3, 0x22}:
                        embedded = int.from_bytes(payload[:2], "little")
                        if embedded not in {0, 1} or len(payload) < 4:
                            raise ValueError("Invalid WinHelp picture reference")
                        if embedded == 0:
                            marker = "\u25a7"
                    self.objects.append({"record": record.position, "placement": opcode, "kind": kind,
                                         "hotspots": command.hotspots, "payload": payload.hex()})
                    self._append([_Cell(char, self.font, self.link) for char in marker])
                    native_extra += command.hotspots
                elif opcode in {0x20, 0x21}:
                    self._text(f"[Field {command.value}]".encode("ascii"), record.position, origin)
                elif opcode == 0xFF and self.row:
                    self._finish(paragraph=True)
            if display.columns:
                if self.row:
                    self._finish(paragraph=True)
                table_cells.setdefault(paragraph.column, []).extend(self.rows)
                self.rows, self.row = saved_rows, saved_row
                self.width = normal_width
        if display.columns:
            # Stored column geometry, not borders/caption guesses. Fixed-cell
            # projection retains each cell's paragraphs and every styled link.
            count = max((len(rows) for rows in table_cells.values()), default=0)
            for index in range(count):
                row = []
                for column, width in enumerate(widths):
                    cell = table_cells.get(column, [])
                    content = cell[index] if index < len(cell) else []
                    row.extend(content)
                    if column + 1 < len(widths):
                        row.extend(_Cell(" ", self.font, None) for _ in range(max(2, width - len(content))))
                self.rows.append(row)
        self.width = normal_width
        for line, row in enumerate(self.rows[start_line - 1:], start_line):
            for cell in row:
                if cell.origin:
                    self.anchors.setdefault(cell.origin, line)


class WinHelpReader(HelpReaderBase):
    def __init__(self, source_name="input.hlp", text_encoding="cp1252", source_path=None):
        super().__init__(source_name, text_encoding, source_path)

    def read_bytes(self, data: bytes) -> HelpDocument:
        file = WinHelpFile(data)
        native = WinHelpTopics(file)
        if native.system.minor != 21 or native.system.flags not in {0, 4}:
            raise ValueError("Unverified WinHelp visual-record version/compression profile")
        fonts = read_fonts(file.stream("|FONT"))
        articles = list(native.articles())
        if len({a.number for a in articles}) != len(articles):
            raise ValueError("Duplicate native WinHelp article numbers")
        contexts = WinHelpBTree(file.stream("|CONTEXT")) if b"|CONTEXT" in file.streams else None
        if contexts and contexts.header.structure != "L4":
            raise ValueError("Invalid WinHelp context descriptor")
        keywords = file.keyword_targets() if b"|KWBTREE" in file.streams else []
        system_contents = [int.from_bytes(value, "little") for kind, value in native.system.records
                           if kind == 3 and len(value) == 4]
        offsets = {offset for _, values in keywords for offset in values}
        if contexts:
            offsets.update(r.values[0] for r in contexts.records)
        offsets.update(system_contents)
        offsets.update(v for a in articles for v in (a.browse_previous, a.browse_following) if v != 0xFFFFFFFF)
        ordered = tuple(sorted(offsets))
        resolved = dict(zip(ordered, native.resolve_offsets(ordered)))
        hash_targets = {r.key: resolved.get(r.values[0]) for r in contexts.records} if contexts else {}
        article_aliases = {}
        for hash_value, target in hash_targets.items():
            if target:
                article_aliases.setdefault(target.topic_number, []).append(_alias(hash_value))
        wanted = frozenset((target.record_position, target.character_offset)
                           for target in resolved.values() if target)
        anchors = {}
        for article in articles:
            layout = _Layout(fonts, self.text_encoding, wanted)
            for record in article.records:
                layout.record(record)
            anchors[article.number] = layout.anchors

        @lru_cache(maxsize=None)
        def target_line(target):
            if target is None:
                return None
            mapping = anchors[target.topic_number]
            return mapping.get((target.record_position, target.character_offset),
                               mapping.get((target.record_position, 0), 1))

        article_alias_lines = {}
        for value, target in hash_targets.items():
            if target and target_line(target) > 1:
                article_alias_lines.setdefault(target.topic_number, {})[_alias(value)] = target_line(target)

        macros = {}

        def link_markup(link, label):
            if link.kind == "macro":
                navigation = macro_navigation(link.value)
                if navigation is not None:
                    return link_markup(navigation, label)
            if link.file and link.file.lower() == self.source_name.encode(self.text_encoding).lower():
                link = WinHelpLink(link.kind, link.value)
            if link.kind == "context-hash":
                target = hash_targets.get(link.value) if not link.file else None
                if target:
                    return format_uhf_link(label, topic_id=target.topic_number, line=target_line(target))
                return format_uhf_link(label, alias=_alias(link.value),
                                       source_file=link.file.decode(self.text_encoding) if link.file else None)
            if link.kind == "topic-number":
                return format_uhf_link(label, topic_id=link.value)
            if link.kind == "contents":
                return format_uhf_link(label, alias="winhelp-contents",
                                       source_file=link.file.decode(self.text_encoding) if link.file else None)
            # Preserve unimplemented native macros as explicit unavailable
            # destinations; never execute native commands or JavaScript.
            alias = "winhelp-macro:" + link.value.hex()
            macros[alias] = {"alias": alias, "macro": link.value.decode(self.text_encoding)}
            return format_uhf_link(label, alias=alias)

        topics = []
        source_objects = []
        unmapped = set()
        for article in articles:
            layout = _Layout(fonts, self.text_encoding)
            for record in article.records:
                layout.record(record)
            source_objects.extend({"topic": article.number, **obj} for obj in layout.objects)
            unmapped.update(layout.unmapped)
            content = []
            raw_lines = []
            for row in layout.rows:
                text = "".join(cell.char for cell in row)
                styles, links = [], []
                start = 0
                while start < len(row):
                    end = start + 1
                    cell = row[start]
                    while end < len(row) and row[end].font == cell.font and row[end].link is cell.link:
                        end += 1
                    font = fonts[cell.font]
                    styles.append(UhfStyleSpan(start, end, bold=bool(font.attributes & 1),
                                               italic=bool(font.attributes & 2), underline=bool(font.attributes & 0x14)))
                    if cell.link:
                        links.append(UhfLinkSpan(start, end, target_alias=str(len(links))))
                    start = end
                native_links = [row[span.start].link for span in links]
                content.append(render_uhf_line(text, style_spans=styles, link_spans=links,
                                               link_formatter=lambda span, label: link_markup(native_links[int(span.target_alias)], label)))
                raw_lines.append(text.encode(self.text_encoding, errors="replace"))
            aliases = article_aliases.get(article.number, [])
            topic = TopicRecord(article.number, raw_lines, names=[article.title.decode(self.text_encoding)],
                                alias_strings=aliases, alias_lines=article_alias_lines.get(article.number, {}),
                                uhf_content=content)
            if article.non_scroll != 0xFFFFFFFF and (article.scroll, 0) in layout.anchors:
                topic.frozen_rows = layout.anchors[(article.scroll, 0)] - 1
            for name, value in (("Prev", article.browse_previous), ("Next", article.browse_following)):
                target = resolved.get(value)
                if target:
                    topic.nav_items.append(TopicNavItem(name, target.topic_number, line=target_line(target)))
            topics.append(topic)
        index = []
        for label, values in keywords:
            for value in values:
                target = resolved.get(value)
                if target:
                    index.append(IndexEntry(label, target.topic_number, topic_id=target.topic_number, line=target_line(target)))
                else:
                    raise ValueError("WinHelp keyword has no bounded native destination")
        contents = resolved.get(system_contents[0]) if system_contents else None
        if contents:
            start_topic = next(t for t in topics if t.context_id == contents.topic_number)
            start_topic.is_help_contents = True
            start_topic.alias_strings.append("winhelp-contents")
            if target_line(contents) > 1:
                start_topic.alias_lines["winhelp-contents"] = target_line(contents)
        title = next((value.rstrip(b"\0").decode(self.text_encoding)
                      for kind, value in native.system.records if kind == 1), self.source_name)
        copyright_text = next((value.rstrip(b"\0").decode(self.text_encoding)
                               for kind, value in native.system.records if kind == 2), "")
        return HelpDocument("winhelp", self.source_name, topics, index, binary_data=data,
                            contents=[ContentNode(t.names[0], topic_id=t.context_id) for t in topics if t.names[0]],
                            metadata={"title": title, "copyright": copyright_text, "text_encoding": self.text_encoding,
                                      "display_width": 80, "show_topic_titles": False,
                                      "help_contents_topic_id": contents.topic_number if contents else None,
                                      "winhelp_projection": "fixed-cell-text", "winhelp_objects": source_objects,
                                      "winhelp_fonts": [{"attributes": f.attributes, "half_points": f.half_points,
                                                         "family": f.family, "face": f.face.decode(self.text_encoding),
                                                         "foreground": f.foreground.hex(), "background": f.background.hex()}
                                                        for f in fonts],
                                      "winhelp_macros": list(macros.values()),
                                      "winhelp_unmapped_glyphs": sorted(unmapped),
                                      "transport_metadata_keys": ["winhelp_projection", "winhelp_objects", "winhelp_fonts", "winhelp_macros", "winhelp_unmapped_glyphs"]})
