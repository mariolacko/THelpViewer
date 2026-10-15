"""Reader for modern Scorpion's Cheater Allegro DAT content databases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from ..codepages import KAMENICKY
from ..uhf_markup import UhfStyleSpan, render_uhf_line
from .scorpion_reader import (
    SCORPION_ATTRIBUTE_CONTROLS,
    SCORPION_BACKGROUND_CONTROLS,
    SCORPION_BACKGROUND_RESET_CONTROL,
    SCORPION_DISPLAY_COLUMNS,
    SCORPION_LINE_BREAK_CONTROL,
    SCORPION_RENDER_TAB_TEXT,
    SCORPION_RESET_CONTROL,
    SCORPION_SOFT_BREAK_BYTE,
    SCORPION_STYLE_CONTROLS,
    SCORPION_TEXT_ENCODING,
    SCORPION_UI_THEME,
    scorpion_version_hint_from_path,
)
from .scorpion_dat_parser import (
    SCORPION_ALLEGRO_PASSWORD,
    SCORPION_ALLEGRO_PACK_MAGIC,
    SCORPION_DAT_SIGNATURE,
    ScorpionDatArticle,
    ScorpionDatRecord,
    parse_scorpion_dat_records,
    split_scorpion_record_articles,
)
from .scorpion_sc2000 import catalog_topic, is_sc2000_catalog, is_sc2000_prose
from .scorpion_screens import inline_text_screen, modern_screens


SCORPION_DAT_TRANSPORT_METADATA_KEYS = (
    "scorpion_version",
    "scorpion_decoder",
    "scorpion_allegro_old_crypt_password",
    "scorpion_allegro_raw_magic",
    "scorpion_reader_class",
    "scorpion_resource_record_count",
    "scorpion_resource_record_names",
    "scorpion_unconverted_record_names",
)
SCORPION_TEXT_BYTE_OVERRIDES = {
    0xE0: "ŕ",
    0xFB: "ü",
    0xFC: "ü",
    0xFD: "ř",
    0xFE: " ",
    0xFF: " ",
}
SCORPION_RESOURCE_RECORD_RE = re.compile(
    r"^(?:_main|datum[A-Z]?|egg|font\d+|fontok|fontkruh|library[A-Z]?|"
    r"librar|obr\d+|obrview|pirat|rok[A-Z]?|scroll|seznam[A-Z]?|verze[A-Z]?|xicht)$",
    re.IGNORECASE,
)
_SPACED_TITLE_RUN_RE = re.compile(r"(?<!\S)(?:[\w+./&-]\s+){1,}[\w+./&-](?!\S)", re.UNICODE)
_SPACED_DECIMAL_RUN_RE = re.compile(r"(\d)\.\s+((?:\d(?:\s+\d)*)\b)")
SCORPION_DAT_BACKGROUND_RESET_CONTROLS = frozenset(
    {SCORPION_BACKGROUND_RESET_CONTROL, 0xE6}
)


@dataclass(frozen=True, slots=True)
class _RenderedLine:
    text: str
    uhf: str
    has_code_style: bool = False
    cells: tuple[tuple[int, int, int], ...] = ()


def is_scorpion_dat_binary(data: bytes) -> bool:
    """Return True when bytes look like a modern Scorpion Allegro DAT file."""
    return data.startswith(SCORPION_DAT_SIGNATURE)


def is_scorpion_dat_help_binary(data: bytes) -> bool:
    """Identify article containers; malformed recognized DATs must fail a build."""
    if not is_scorpion_dat_binary(data):
        return False
    records = parse_scorpion_dat_records(data)
    return any(_is_text_record(record) or is_sc2000_catalog(record) for record in records)


def _decode_scorpion_byte(value: int) -> str:
    override = SCORPION_TEXT_BYTE_OVERRIDES.get(value)
    if override is not None:
        return override
    char = KAMENICKY.get(value)
    if char is not None:
        return char
    return bytes((value,)).decode("latin-1", errors="replace")


def _is_soft_break_byte(payload: bytes, index: int) -> bool:
    if payload[index] != SCORPION_SOFT_BREAK_BYTE:
        return False

    pos = index + 1
    while pos < len(payload) and payload[pos] == 0x20:
        pos += 1

    return pos >= len(payload) or payload[pos] in (0x0D, 0x0A, SCORPION_LINE_BREAK_CONTROL)


def _is_literal_e5_n(payload: bytes, index: int) -> bool:
    if index <= 0 or index + 1 >= len(payload):
        return False
    previous_char = _decode_scorpion_byte(payload[index - 1])
    next_char = _decode_scorpion_byte(payload[index + 1])
    return previous_char.isalnum() and next_char in ",.;:!?)]}"


def _close_style_span(
    spans: list[UhfStyleSpan],
    *,
    start: int | None,
    end: int,
    fg: int | None,
    bg: int | None,
) -> None:
    if start is None or (fg is None and bg is None) or end <= start:
        return
    spans.append(UhfStyleSpan(start=start, end=end, bold=fg is not None, fg=fg, bg=bg))


def _render_payload_lines(payload: bytes) -> list[_RenderedLine]:
    """Render one Scorpion article stream to visible lines plus UHF styling."""
    lines: list[_RenderedLine] = []
    chars: list[str] = []
    cells = []
    spans: list[UhfStyleSpan] = []
    current_fg: int | None = None
    current_bg: int | None = None
    span_start: int | None = None
    previous_was_cr = False

    def finish_line() -> None:
        nonlocal chars, cells, spans, current_fg, current_bg, span_start
        _close_style_span(
            spans,
            start=span_start,
            end=len(chars),
            fg=current_fg,
            bg=current_bg,
        )
        text = "".join(chars).rstrip()
        lines.append(
            _RenderedLine(
                text=text,
                uhf=render_uhf_line(text, style_spans=spans),
                has_code_style=any(span.fg == SCORPION_STYLE_CONTROLS[0xF0] for span in spans),
                cells=tuple(cells[:len(text)]),
            )
        )
        chars = []
        cells = []
        spans = []
        current_fg = None
        current_bg = None
        span_start = None

    def append_char(glyph: int, char: str) -> None:
        chars.append(char)
        cells.append((glyph, 7 if current_fg is None else current_fg,
                      0 if current_bg is None else current_bg))

    index = 0
    while index < len(payload):
        value = payload[index]
        if value == 0x0A and previous_was_cr:
            previous_was_cr = False
            index += 1
            continue
        previous_was_cr = value == 0x0D

        if value in (0x0D, 0x0A, SCORPION_LINE_BREAK_CONTROL):
            finish_line()
            index += 1
            continue
        if _is_soft_break_byte(payload, index):
            index += 1
            continue
        if value == 0x09:
            for space in SCORPION_RENDER_TAB_TEXT:
                append_char(32, space)
            index += 1
            continue
        if value == 0xE5 and _is_literal_e5_n(payload, index):
            append_char(value, "ň")
            index += 1
            continue
        if value == SCORPION_RESET_CONTROL:
            _close_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_fg = None
            span_start = len(chars) if current_bg is not None else None
            index += 1
            continue
        if value in SCORPION_STYLE_CONTROLS:
            _close_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_fg = SCORPION_STYLE_CONTROLS[value]
            span_start = len(chars)
            index += 1
            continue
        if value in SCORPION_DAT_BACKGROUND_RESET_CONTROLS:
            _close_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_bg = None
            span_start = len(chars) if current_fg is not None else None
            index += 1
            continue
        if value in SCORPION_BACKGROUND_CONTROLS:
            _close_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_bg = SCORPION_BACKGROUND_CONTROLS[value]
            span_start = len(chars)
            index += 1
            continue
        if value in SCORPION_ATTRIBUTE_CONTROLS:
            index += 1
            continue
        if value < 0x20:
            append_char(32, " ")
            index += 1
            continue
        append_char(value, _decode_scorpion_byte(value))
        index += 1

    if chars or spans:
        finish_line()
    return lines


def _plain_lines(lines: list[_RenderedLine]) -> list[str]:
    return [line.text for line in lines]


def _drop_marker_line(lines: list[_RenderedLine], page_tag: str | None) -> list[_RenderedLine]:
    if not page_tag or not lines:
        return lines
    marker = f"[{page_tag}]"
    if lines[0].text.strip() == marker:
        return lines[1:]
    return lines


def _normalize_title(line: str) -> str:
    chunks = [
        _SPACED_TITLE_RUN_RE.sub(lambda match: re.sub(r"\s+", "", match.group(0)), chunk.strip())
        for chunk in re.split(r"\s{2,}", line)
        if chunk.strip()
    ]
    title = " ".join(chunks)
    title = _SPACED_DECIMAL_RUN_RE.sub(
        lambda match: f"{match.group(1)}.{re.sub(r'\s+', '', match.group(2))}",
        title,
    )
    title = re.sub(r"\s+([:;,.!?])", r"\1", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()


def _guess_article_title(article: ScorpionDatArticle, lines: list[_RenderedLine]) -> str:
    for line in lines:
        title = _normalize_title(line.text)
        if title:
            return title
    if article.page_tag:
        return article.page_tag
    return article.record_name


def _topic_from_article(
    article: ScorpionDatArticle,
    *,
    context_id: int,
    screens: dict | None = None,
) -> TopicRecord | None:
    rendered = _drop_marker_line(_render_payload_lines(article.payload), article.page_tag)
    while rendered and not rendered[0].text.strip():
        rendered.pop(0)
    while rendered and not rendered[-1].text.strip():
        rendered.pop()
    if not rendered:
        return None

    title = _guess_article_title(article, rendered)
    raw_lines = [line.text.encode("utf-8") for line in rendered]
    uhf_lines = [line.uhf for line in rendered]
    if screens is not None:
        for index, line in enumerate(rendered):
            if index == 0:
                continue
            screen = inline_text_screen(line.cells, line.text, "program-font")
            if screen is not None:
                screen_id = f"inline-{context_id}-{index}"
                screens[screen_id] = screen
                uhf_lines[index] = f"[screen:{screen_id}]"
    aliases = [article.record_name]
    if article.page_tag:
        aliases.append(article.page_tag)

    return TopicRecord(
        context_id=context_id,
        raw_lines=raw_lines,
        index_terms=[title.encode("utf-8")],
        alias_strings=aliases,
        names=[title],
        code_line_indices={index for index, line in enumerate(rendered) if line.has_code_style},
        uhf_content=uhf_lines,
    )


def _is_text_record(record: ScorpionDatRecord) -> bool:
    if is_sc2000_prose(record) or SCORPION_RESOURCE_RECORD_RE.match(record.name):
        return False
    return any(article.page_tag for article in split_scorpion_record_articles(record))


def _display_name_from_source(path: Path) -> str:
    name = path.stem.lower()
    return {
        "cheaty": "Scorpion's Cheater - Cheaty",
        "navody": "Scorpion's Cheater - Návody",
        "program": "Scorpion's Cheater - Program",
        "vtipy": "Scorpion's Cheater - Vtipy",
        "easter": "Scorpion's Cheater - Easter Eggs",
        "texty": "Scorpion's Cheater - Texty",
    }.get(name, path.stem)


def _normalize_source_date(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    for fmt in ("%m-%d-%Y, %H:%M", "%m-%d-%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _shared_source_date(records: list[ScorpionDatRecord]) -> str | None:
    source_dates = {
        normalized
        for record in records
        if record.date
        for normalized in [_normalize_source_date(record.date)]
        if normalized is not None
    }
    if len(source_dates) == 1:
        return next(iter(source_dates))
    return None


def _build_contents(topics: list[TopicRecord], source_path: Path) -> list[ContentNode]:
    return [
        ContentNode(
            label=_display_name_from_source(source_path),
            children=[
                ContentNode(label=topic.names[0] if topic.names else str(topic.context_id), topic_id=topic.context_id)
                for topic in topics
            ],
        )
    ]


class ScorpionAllegroDatReader(HelpReaderBase):
    """Parse the shared Allegro-backed Scorpion DAT format into topics."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_scorpion_dat_binary(data):
            raise ValueError("Not a modern Scorpion DAT file.")

        records = parse_scorpion_dat_records(data)
        if not records:
            raise ValueError("Scorpion DAT file contains no readable records.")

        source_path = self.source_path or Path(self.source_name)
        fonts, screens = {}, {}
        font, screen_records = modern_screens(records) if source_path.name.lower() == "program.dat" else (None, [])
        if font is not None:
            fonts["program-font"] = font
        unconverted_records = [record for record in records if is_sc2000_prose(record)]
        resource_records = [record for record in records if not _is_text_record(record)
                            and not is_sc2000_catalog(record) and record not in unconverted_records]

        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []
        catalog_contents: list[ContentNode] = []

        for record in records:
            if is_sc2000_catalog(record):
                topic, entries, children = catalog_topic(
                    record, self.source_path or Path(self.source_name), len(topics),
                )
                topics.append(topic)
                index_entries.extend(entries)
                catalog_contents.extend(children)
                continue
            if not _is_text_record(record):
                continue
            for article in split_scorpion_record_articles(record):
                if not article.page_tag:
                    continue
                topic = _topic_from_article(article, context_id=len(topics), screens=screens if font is not None else None)
                if topic is None:
                    continue
                topics.append(topic)
                index_entries.append(IndexEntry(label=topic.names[0].encode("utf-8"), context_id=topic.context_id))

        if not topics:
            raise ValueError("Scorpion DAT file contains no readable articles.")

        screen_contents = []
        # Resource views follow all articles; existing article IDs stay intact.
        if source_path.name.lower() == "program.dat":
            for record, screen in screen_records:
                screen_id = f"screen-{record.index}"
                screens[screen_id] = screen
                title = f"Obrazovka: {record.name}"
                topic = TopicRecord(context_id=len(topics),
                    raw_lines=[line.encode("utf-8") for line in screen.text],
                    names=[title], index_terms=[title.encode("utf-8")], alias_strings=[record.name],
                    uhf_content=[f"[screen:{screen_id}]"],
                )
                topics.append(topic)
                index_entries.append(IndexEntry(label=title.encode("utf-8"), context_id=topic.context_id))
                screen_contents.append(ContentNode(label=title, topic_id=topic.context_id))
        metadata: dict[str, object] = {
            "title": _display_name_from_source(source_path),
            "description": _display_name_from_source(source_path),
            "text_encoding": "utf-8",
            "source_text_encoding": SCORPION_TEXT_ENCODING,
            "display_width": SCORPION_DISPLAY_COLUMNS,
            "ui": dict(SCORPION_UI_THEME),
            "source_family": "scorpion-dat",
            "scorpion_decoder": "scorpion-dat",
            "scorpion_allegro_old_crypt_password": SCORPION_ALLEGRO_PASSWORD.decode("ascii"),
            "scorpion_allegro_raw_magic": SCORPION_ALLEGRO_PACK_MAGIC.hex(" ").upper(),
            "record_count": len(records),
            "scorpion_resource_record_count": len(resource_records),
            "scorpion_resource_record_names": [record.name for record in resource_records],
            "topic_count": len(topics),
            "transport_metadata_keys": list(SCORPION_DAT_TRANSPORT_METADATA_KEYS),
        }
        if catalog_contents:
            metadata["source_text_encoding"] = "cp1250"
        if unconverted_records:
            metadata["scorpion_unconverted_record_names"] = [record.name for record in unconverted_records]
        source_date = _shared_source_date(records)
        if source_date is not None:
            metadata["source_date"] = source_date
        version_hint = scorpion_version_hint_from_path(source_path)
        if version_hint:
            metadata["scorpion_version"] = version_hint
        metadata["scorpion_reader_class"] = type(self).__name__

        contents = _build_contents(topics, source_path)
        if screen_contents:
            contents[0].children = contents[0].children[:-len(screen_contents)]
            contents[0].children.append(ContentNode(label="Obrazovky programu", children=screen_contents))
        contents[0].children.extend(catalog_contents)
        return HelpDocument(
            format_name="scorpion-dat",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            contents=contents,
            metadata=metadata,
            binary_data=data,
            fonts=fonts,
            text_screens=screens,
        )


ScorpionV15DatReader = ScorpionAllegroDatReader
ScorpionV16DatReader = ScorpionAllegroDatReader
ScorpionV21DatReader = ScorpionAllegroDatReader
ScorpionV22DatReader = ScorpionAllegroDatReader
ScorpionV23DatReader = ScorpionAllegroDatReader


SCORPION_DAT_VERSION_READER_CLASSES = {
    "15": ScorpionAllegroDatReader,
    "16": ScorpionAllegroDatReader,
    "21": ScorpionAllegroDatReader,
    "22": ScorpionAllegroDatReader,
    "23": ScorpionAllegroDatReader,
}


def scorpion_dat_reader_class_for_path(path: str | Path) -> type[ScorpionAllegroDatReader] | None:
    version_hint = scorpion_version_hint_from_path(path)
    if version_hint is None:
        return None
    return SCORPION_DAT_VERSION_READER_CLASSES.get(version_hint)


class ScorpionDatReader(HelpReaderBase):
    """Dispatch modern Scorpion DAT files to the matching format reader class."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        source_path = self.source_path or Path(self.source_name)
        reader_class = scorpion_dat_reader_class_for_path(source_path) or ScorpionAllegroDatReader
        reader = reader_class(source_name=self.source_name, source_path=source_path)
        return reader.read_bytes(data)
