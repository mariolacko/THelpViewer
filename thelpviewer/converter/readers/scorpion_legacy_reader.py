"""Version-aware scaffold readers for early Scorpions Cheater releases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tempfile

from ...downloader.extractor import ExtractorTools, extract_file, find_lsar, find_sevenzip, find_unar
from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord, ensure_document_index
from ..codepages import KAMENICKY, decode_bytes
from ..uhf_markup import UhfStyleSpan, render_uhf_line
from .scorpion_reader import (
    SCORPION_ATTRIBUTE_CONTROLS,
    SCORPION_BACKGROUND_CONTROLS,
    SCORPION_BACKGROUND_RESET_CONTROL,
    SCORPION_DISPLAY_COLUMNS,
    SCORPION_LEGACY_CONTAINER_STEMS,
    SCORPION_LINE_BREAK_CONTROL,
    SCORPION_RENDER_TAB_TEXT,
    SCORPION_RESET_CONTROL,
    SCORPION_SOFT_BREAK_BYTE,
    SCORPION_STYLE_CONTROLS,
    SCORPION_TEXT_ENCODING,
    SCORPION_UI_THEME,
    encode_scorpion_text,
    scorpion_raw_lines,
    scorpion_version_hint_from_path,
)


ASCII_STRING_RE = re.compile(rb"[ -~]{4,}")
DOS_MZ_SIGNATURE = b"MZ"
RAR4_SIGNATURE = b"Rar!\x1A\x07\x00"
PKLITE_SIGNATURE = b"PKLITE"
RAR_FILE_HEAD = 0x74
RAR_ENDARC_HEAD = 0x7B
MSDOS_DIRECTORY_ATTRIBUTE = 0x10
SCORPION_LEGACY_TEXT_ENCODING = SCORPION_TEXT_ENCODING
V3_TOPIC_MARKER_RE = re.compile(r"^\[([A-Z0-9]{4})\]$")
V3_INDEX_ENTRY_RE = re.compile(r"^(?P<label>.+?),\[(?P<marker>[A-Z0-9]{4})\][*-]$")
V3_FORMATTING_CHARS = frozenset(
    char
    for byte, char in KAMENICKY.items()
    if 0xE1 <= byte <= 0xF8 and byte != 0xEE
)
SCO_FORMATTING_CHARS = frozenset(
    char
    for byte, char in KAMENICKY.items()
    if 0xE1 <= byte <= 0xFB and byte not in {0xEE, 0xF8}
)
SCO_TOPIC_MARKER_RE = re.compile(r"^\[([A-Z0-9]{4})\]$")
SCO_INDEX_ENTRY_RE = re.compile(r",\[[^\]]+\][*+!\-]")
SCO_INDEX_ENTRY_LINE_RE = re.compile(r"^(?P<label>.+?),\[(?P<target>[^\]]+)\](?P<flag>[*+!\-]+)$")
SCO_INDEX_FLAG_STATUS = {
    "-": "plain",
    "*": "new",
    "+": "updated",
    "!": "supplement",
}
SCORPION_LEGACY_TRANSPORT_METADATA_KEYS = (
    "scorpion_version",
    "scorpion_decoder",
    "scorpion_reader_class",
    "scorpion_authors",
    "scorpion_v3_section",
    "scorpion_sco_role",
    "scorpion_sco_source_files",
    "scorpion_sco_index_entry_count",
    "scorpion_sco_index_header_count",
    "scorpion_sco_index_entries",
    "scorpion_sco_index_status_counts",
    "scorpion_sco_index_flag_counts",
    "scorpion_sco_inline_styles",
    "scorpion_compression",
    "scorpion_lzhuf_block_count",
    "scorpion_lzhuf_blocks",
    "scorpion_lzhuf_decoded_size",
)


@dataclass(frozen=True, slots=True)
class ScorpionLegacyProfile:
    version: str
    label: str
    family: str
    decoder_name: str
    suffixes: tuple[str, ...]
    description: str


@dataclass(frozen=True, slots=True)
class ScorpionLegacyArchiveMember:
    raw_name: str
    display_name: str
    packed_size: int
    unpacked_size: int
    method: int
    attributes: int


@dataclass(frozen=True, slots=True)
class ScorpionLegacyUnpackedMember:
    output_name: str
    display_name: str
    payload: bytes


def _encode_legacy_text(text: str) -> bytes:
    return encode_scorpion_text(text)


def _legacy_raw_lines(lines: list[str]) -> list[bytes]:
    return scorpion_raw_lines(lines)


SCORPION_LEGACY_PROFILES = (
    ScorpionLegacyProfile(
        version="1",
        label="Scorpions Cheater 1.0",
        family="v1-dat-exe",
        decoder_name="scorpion-v1-dat-exe",
        suffixes=(".dat",),
        description="Oldest RSFX/MZ-packed DAT wrapper used by the first public DOS release 1.00.",
    ),
    ScorpionLegacyProfile(
        version="1.5",
        label="Scorpions Cheater 1.5",
        family="v1.5-embedded-exe",
        decoder_name="scorpion-v1_5-embedded-exe",
        suffixes=(".exe",),
        description="Early release where the corpus appears to be embedded directly in the DOS executable.",
    ),
    ScorpionLegacyProfile(
        version="3",
        label="Scorpions Cheater 3",
        family="v3-exe-dat",
        decoder_name="scorpion-v3-exe-dat",
        suffixes=(".dat",),
        description="Executable-style DAT family used before the SCO split corpus appears.",
    ),
    ScorpionLegacyProfile(
        version="3.5",
        label="Scorpions Cheater 3.5",
        family="v3.5-early-dat",
        decoder_name="scorpion-v3_5-early-dat",
        suffixes=(".dat",),
        description="Expanded pre-SCO DAT family with multiple raw data members.",
    ),
    ScorpionLegacyProfile(
        version="4",
        label="Scorpions Cheater 4",
        family="v4-sco",
        decoder_name="scorpion-v4-sco",
        suffixes=(".sco",),
        description="First SCORPION/SCO corpus layout with external library files.",
    ),
    ScorpionLegacyProfile(
        version="5",
        label="Scorpions Cheater 5",
        family="v5-sco",
        decoder_name="scorpion-v5-sco",
        suffixes=(".sco",),
        description="Second SCO-only corpus layout before SCD/SCX split screens appeared.",
    ),
    ScorpionLegacyProfile(
        version="6",
        label="Scorpions Cheater 6",
        family="v6-shareware",
        decoder_name="scorpion-v6-shareware",
        suffixes=(".sco", ".scd", ".scx"),
        description="Shareware-era split corpus using SCD libraries plus SCO helpers and SCX screens.",
    ),
    ScorpionLegacyProfile(
        version="7",
        label="Scorpions Cheater 7",
        family="v7-shareware",
        decoder_name="scorpion-v7-shareware",
        suffixes=(".sco", ".scd", ".scx"),
        description="Later shareware split corpus with dedicated screen and driver resources.",
    ),
    ScorpionLegacyProfile(
        version="8",
        label="Scorpions Cheater 8",
        family="v8-shareware",
        decoder_name="scorpion-v8-shareware",
        suffixes=(".sco", ".scd", ".scx"),
        description="Last shareware branch before the larger magazine-distributed library sets.",
    ),
    ScorpionLegacyProfile(
        version="10",
        label="Scorpions Cheater 10",
        family="v10-library",
        decoder_name="scorpion-v10-library",
        suffixes=(".sco", ".scd", ".scx"),
        description="Magazine-era library split with CHEATS/NAVODY/JOKES/SCREENS resources.",
    ),
    ScorpionLegacyProfile(
        version="11",
        label="Scorpions Cheater 11",
        family="v11-library",
        decoder_name="scorpion-v11-library",
        suffixes=(".sco", ".scd", ".scx"),
        description="Expanded SCO library branch with NAVODY volumes and indexed screen banks.",
    ),
    ScorpionLegacyProfile(
        version="12",
        label="Scorpions Cheater 12",
        family="v12-library",
        decoder_name="scorpion-v12-library",
        suffixes=(".sco", ".scd", ".scx"),
        description="Three-volume NAVODY branch prior to the return to DAT in version 15.",
    ),
    ScorpionLegacyProfile(
        version="13",
        label="Scorpions Cheater 13",
        family="v13-library",
        decoder_name="scorpion-v13-library",
        suffixes=(".sco", ".scd", ".scx"),
        description="Late SCO branch with larger cheat and help libraries.",
    ),
    ScorpionLegacyProfile(
        version="14",
        label="Scorpions Cheater 14",
        family="v14-library",
        decoder_name="scorpion-v14-library",
        suffixes=(".sco", ".scd", ".scx"),
        description="Last pre-DAT SCO/SCD/SCX generation before the modern DAT family.",
    ),
)

SCORPION_LEGACY_PROFILE_BY_VERSION = {profile.version: profile for profile in SCORPION_LEGACY_PROFILES}
SCORPION_LEGACY_SKIP_FILENAMES_BY_VERSION = {
    "1.5": frozenset({"CS.EXE"}),
    "3": frozenset({"BLCK.DAT"}),
    "3.5": frozenset({"BLCK.DAT", "MAIN.DAT"}),
}
SCORPION_LEGACY_RESOURCE_FILENAMES = frozenset(
    {
        "DRIVER.SCO",
        "FA.SCO",
        "FB.SCO",
        "FC.SCO",
        "FD.SCO",
        "FE.SCO",
        "FF.SCO",
        "FOK.SCO",
        "FONT.SCO",
        "SCREENS.SCO",
        "SLEEPER.SCO",
        "SPELDATA.SCO",
        "SP.SCX",
        "XMAS.SCX",
    }
)
SCORPION_LEGACY_RESOURCE_FILENAME_RE = re.compile(r"^SCR\d+\.(?:SCD|SCX)$", re.IGNORECASE)
SCORPION_LEGACY_FONT_HEADER_RE = re.compile(rb"SCORPIONS CHEATER [^\x00]{0,40}font", re.IGNORECASE)
SCO_INLINE_STYLE_VERSIONS = frozenset({"4", "5", "6", "7", "8", "10", "11", "12", "13", "14"})
SCO_FORMATTING_BYTE_BY_CHAR = {
    char: byte
    for byte, char in KAMENICKY.items()
    if 0xE1 <= byte <= 0xFB and byte != 0xF8
}


@dataclass(frozen=True, slots=True)
class StyledScoLine:
    text: str
    uhf: str


def _normalize_sco_text_line(text: str) -> str:
    if not text:
        return ""
    normalized = _normalize_v3_epsilon_controls(text)
    normalized = "".join(char for char in normalized if char not in SCO_FORMATTING_CHARS)
    return normalized.strip()


def _close_sco_style_span(
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


def _sco_line_has_fixed_art(text: str) -> bool:
    return any("\u2500" <= char <= "\u259f" for char in text)


def _trim_sco_style_spans(text: str, spans: list[UhfStyleSpan]) -> tuple[str, list[UhfStyleSpan]]:
    left = 0 if _sco_line_has_fixed_art(text) else len(text) - len(text.lstrip())
    right = len(text.rstrip())
    if right <= left:
        return "", []

    trimmed_spans: list[UhfStyleSpan] = []
    for span in spans:
        start = max(span.start, left) - left
        end = min(span.end, right) - left
        if end <= start:
            continue
        trimmed_spans.append(
            UhfStyleSpan(
                start=start,
                end=end,
                bold=span.bold,
                italic=span.italic,
                underline=span.underline,
                reverse=span.reverse,
                fg=span.fg,
                bg=span.bg,
            )
        )
    return text[left:right], trimmed_spans


def _sco_epsilon_is_literal_e(text: str, index: int) -> bool:
    previous_char = _nearest_non_space(text, index - 1, -1)
    next_char = _nearest_non_space(text, index + 1, 1)
    return previous_char.isalnum() and next_char.isalnum()


def _sco_e5_is_literal_n(text: str, index: int) -> bool:
    if index <= 0 or index + 1 >= len(text):
        return False
    return text[index - 1].isalnum() and text[index + 1] in ",.;:!?)]}"


def _render_sco_text_line(text: str, *, inline_styles: bool = False) -> StyledScoLine:
    if not inline_styles:
        normalized = _normalize_sco_text_line(text)
        return StyledScoLine(normalized, render_uhf_line(normalized))

    chars: list[str] = []
    spans: list[UhfStyleSpan] = []
    current_fg: int | None = None
    current_bg: int | None = None
    span_start: int | None = None

    for index, char in enumerate(text):
        if char == "\t":
            chars.extend(SCORPION_RENDER_TAB_TEXT)
            continue

        control_byte = SCO_FORMATTING_BYTE_BY_CHAR.get(char)
        if control_byte is None:
            chars.append(char)
            continue

        if control_byte == 0xEE and _sco_epsilon_is_literal_e(text, index):
            chars.append("E")
            continue

        if control_byte == 0xE5 and _sco_e5_is_literal_n(text, index):
            chars.append("ň")
            continue

        if control_byte == SCORPION_RESET_CONTROL:
            _close_sco_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_fg = None
            span_start = len(chars) if current_bg is not None else None
            continue

        if control_byte in SCORPION_STYLE_CONTROLS:
            _close_sco_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_fg = SCORPION_STYLE_CONTROLS[control_byte]
            span_start = len(chars)
            continue

        if control_byte == SCORPION_BACKGROUND_RESET_CONTROL:
            _close_sco_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_bg = None
            span_start = len(chars) if current_fg is not None else None
            continue

        if control_byte in SCORPION_BACKGROUND_CONTROLS:
            _close_sco_style_span(
                spans,
                start=span_start,
                end=len(chars),
                fg=current_fg,
                bg=current_bg,
            )
            current_bg = SCORPION_BACKGROUND_CONTROLS[control_byte]
            span_start = len(chars)
            continue

        if control_byte in (SCORPION_LINE_BREAK_CONTROL, SCORPION_SOFT_BREAK_BYTE):
            continue

        if control_byte in SCORPION_ATTRIBUTE_CONTROLS:
            continue

        chars.append(char)

    _close_sco_style_span(
        spans,
        start=span_start,
        end=len(chars),
        fg=current_fg,
        bg=current_bg,
    )
    text_value, trimmed_spans = _trim_sco_style_spans("".join(chars), spans)
    return StyledScoLine(text_value, render_uhf_line(text_value, style_spans=trimmed_spans))


def _normalize_sco_styled_entries(entries: list[StyledScoLine]) -> list[StyledScoLine]:
    normalized: list[StyledScoLine] = []
    pending_blank = False
    for entry in entries:
        if not entry.text.strip():
            if normalized:
                pending_blank = True
            continue
        if _is_v1_5_placeholder_entry(entry.text):
            continue
        if pending_blank and normalized and normalized[-1].text != "":
            normalized.append(StyledScoLine("", ""))
        pending_blank = False
        if normalized and normalized[-1].text == entry.text:
            continue
        normalized.append(entry)
    while normalized and normalized[-1].text == "":
        normalized.pop()
    return normalized


def _sco_decoded_text(decoded: bytes) -> str:
    return decode_bytes(decoded, SCORPION_LEGACY_TEXT_ENCODING).replace("\r\n", "\n").replace("\r", "\n")


def _sco_text_is_readable(text: str) -> bool:
    if not text:
        return False
    marker_count = sum(1 for line in text.split("\n") if SCO_TOPIC_MARKER_RE.fullmatch(line.strip()))
    index_count = len(SCO_INDEX_ENTRY_RE.findall(text))
    lowered = text.lower()
    word_hits = sum(
        lowered.count(word)
        for word in (" kód", " cheat", " level", " napi", " edit", " návod", "scorpions")
    )
    return marker_count > 0 or index_count >= 5 or word_hits >= 3


def _parse_sco_huffman_topics(text: str, *, inline_styles: bool = False) -> list[dict[str, object]]:
    topics: list[dict[str, object]] = []
    current_marker: str | None = None
    current_lines: list[StyledScoLine] = []

    def flush_topic() -> None:
        nonlocal current_marker, current_lines
        if current_marker is None:
            return
        normalized_entries = _normalize_sco_styled_entries(current_lines)
        normalized_lines = [entry.text for entry in normalized_entries]
        if normalized_lines:
            body_title = _normalize_v3_title(normalized_lines[0]) or current_marker
            normalized_lines[0] = body_title
            normalized_uhf_lines = [entry.uhf for entry in normalized_entries]
            normalized_uhf_lines[0] = render_uhf_line(body_title)
            topics.append(
                {
                    "marker": current_marker,
                    "title": body_title,
                    "lines": normalized_lines,
                    "uhf_lines": normalized_uhf_lines,
                }
            )
        current_marker = None
        current_lines = []

    for raw_line in text.split("\n"):
        line = _render_sco_text_line(raw_line.rstrip("\x00"), inline_styles=inline_styles)
        marker_match = SCO_TOPIC_MARKER_RE.fullmatch(line.text)
        if marker_match is not None:
            flush_topic()
            current_marker = marker_match.group(1)
            current_lines = []
            continue
        if current_marker is not None:
            current_lines.append(line)

    flush_topic()
    return topics


def _parse_sco_index_entries(topic_lines: list[str]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for line in topic_lines:
        cleaned_line = line.strip().replace("«", "").replace("»", "")
        match = SCO_INDEX_ENTRY_LINE_RE.fullmatch(cleaned_line)
        if match is None:
            continue
        label = _normalize_v3_title(match.group("label")) or match.group("label").strip()
        target = match.group("target").strip()
        raw_flag = match.group("flag")
        # v8+ appends a second flag of unknown purpose, for example `*-`, `+-`, or
        # `--`. The first character carries the visible status/color.
        flag = raw_flag[0]
        kind = "header" if label.upper().startswith("SEZNAM") else "entry"
        entry = {
            "label": label,
            "target_id": target,
            "flag": flag,
            "status": SCO_INDEX_FLAG_STATUS.get(flag, "unknown"),
            "kind": kind,
        }
        if len(raw_flag) > 1:
            entry["raw_flag"] = raw_flag
        entries.append(entry)
    return entries


def _sco_index_counts(entries: list[dict[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        if entry.get("kind") == "header":
            continue
        value = entry.get(key)
        if not isinstance(value, str) or not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _sco_single_topic_title(
    default_title: str,
    source_name: str,
    topic_lines: list[str],
    index_entries: list[dict[str, object]],
) -> tuple[str, str | None]:
    normalized_source_name = source_name.upper()
    normalized_stem = Path(source_name).stem.upper()
    first_line = topic_lines[0].upper() if topic_lines else ""
    has_index_entries = any(entry.get("kind") == "entry" for entry in index_entries)
    if normalized_stem in {"DATAA", "CHEATS"} and has_index_entries:
        return "Index cheatů", "cheat-index"
    if has_index_entries and (normalized_stem in {"DATAB", "JOKES"} or "[FÓRŮ]" in first_line):
        return "Index vtipů", "joke-index"
    if has_index_entries and (normalized_stem == "HELPS" or normalized_stem.startswith("NAVODY")):
        return "Index návodů", "manual-index"
    if has_index_entries:
        return "Index", "index"
    return default_title, None


def _sco_marker_topic_title(default_title: str, source_name: str) -> tuple[str, str | None]:
    normalized_stem = Path(source_name).stem.upper()
    if normalized_stem.startswith("DATAN") or normalized_stem.startswith("NAVODY") or normalized_stem == "HELPS":
        return "Návody", "manuals"
    if normalized_stem.startswith("DATAV") or normalized_stem == "JOKES":
        return "Vtipy", "jokes"
    if normalized_stem.startswith("DATA") and normalized_stem[4:].isdigit():
        return "Cheaty", "cheats"
    if normalized_stem == "CHEATS":
        return "Cheaty", "cheats"
    if normalized_stem in {"DATATEXT", "DATAHELP"}:
        return "Program", "program"
    return default_title, None


def _sco_prefix_styled_lines_before_first_marker(text: str, *, inline_styles: bool = False) -> list[StyledScoLine]:
    prefix_lines: list[StyledScoLine] = []
    for raw_line in text.split("\n"):
        line = _render_sco_text_line(raw_line.rstrip("\x00"), inline_styles=inline_styles)
        if SCO_TOPIC_MARKER_RE.fullmatch(line.text):
            break
        prefix_lines.append(line)
    return _normalize_sco_styled_entries(prefix_lines)


def _sco_prefix_lines_before_first_marker(text: str) -> list[str]:
    return [entry.text for entry in _sco_prefix_styled_lines_before_first_marker(text)]


def _sco_index_title_overrides(index_entries: list[dict[str, object]]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for entry in index_entries:
        if entry.get("kind") != "entry":
            continue
        target = entry.get("target_id")
        label = entry.get("label")
        if isinstance(target, str) and isinstance(label, str) and target:
            titles.setdefault(target, label)
    return titles


def _build_sco_text_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    decoded_text: str,
    *,
    parser_name: str,
    parser_metadata: dict[str, object],
) -> HelpDocument | None:
    if not _sco_text_is_readable(decoded_text):
        return None

    inline_styles = profile.version in SCO_INLINE_STYLE_VERSIONS
    parsed_topics = _parse_sco_huffman_topics(decoded_text, inline_styles=inline_styles)
    prefix_topic_entries = _sco_prefix_styled_lines_before_first_marker(decoded_text, inline_styles=inline_styles)
    prefix_topic_lines = [entry.text for entry in prefix_topic_entries]
    prefix_topic_uhf_lines = [entry.uhf for entry in prefix_topic_entries]
    title = _legacy_public_document_title(profile, source_name)
    topics: list[TopicRecord] = []
    index_entries: list[IndexEntry] = []
    contents: list[ContentNode]
    sco_role: str | None = None
    sco_index_entries: list[dict[str, object]] = []

    if parsed_topics:
        library_title, sco_role = _sco_marker_topic_title(title, source_name)
        if sco_role is not None:
            title = f"{profile.label} - {library_title}"
        content_nodes: list[ContentNode] = []
        sco_index_entries = _parse_sco_index_entries(prefix_topic_lines)
        title_overrides = _sco_index_title_overrides(sco_index_entries)
        if prefix_topic_lines and sco_index_entries:
            index_title, index_role = _sco_single_topic_title(
                "Index", source_name, prefix_topic_lines, sco_index_entries
            )
            topic_label = _encode_legacy_text(index_title)
            topics.append(
                TopicRecord(
                    context_id=0,
                    raw_lines=_legacy_raw_lines(prefix_topic_lines),
                    index_terms=[topic_label],
                    alias_strings=[profile.version, source_name, parser_name, index_role or "index"],
                    names=[index_title],
                    uhf_content=prefix_topic_uhf_lines,
                )
            )
            index_entries.append(IndexEntry(label=topic_label, context_id=0))
            content_nodes.append(ContentNode(label=index_title, topic_id=0))

        for context_id, parsed_topic in enumerate(parsed_topics, start=1):
            marker = str(parsed_topic["marker"])
            topic_title = title_overrides.get(marker, str(parsed_topic["title"]))
            topic_lines = list(parsed_topic["lines"])
            topic_uhf_lines = list(parsed_topic.get("uhf_lines", topic_lines))
            if topic_lines:
                topic_lines[0] = topic_title
            if topic_uhf_lines:
                topic_uhf_lines[0] = render_uhf_line(topic_title)
            topic_label = _encode_legacy_text(topic_title)
            topics.append(
                TopicRecord(
                    context_id=context_id,
                    raw_lines=_legacy_raw_lines(topic_lines),
                    index_terms=[topic_label],
                    alias_strings=[topic_title, marker, profile.version, source_name],
                    names=[topic_title],
                    uhf_content=topic_uhf_lines,
                )
            )
            index_entries.append(IndexEntry(label=topic_label, context_id=context_id))
            content_nodes.append(ContentNode(label=topic_title, topic_id=context_id))
        contents = [ContentNode(label=title, children=content_nodes)]
    else:
        decoded_entries = [
            _render_sco_text_line(line.rstrip("\x00"), inline_styles=inline_styles)
            for line in decoded_text.split("\n")
        ]
        normalized_entries = _normalize_sco_styled_entries(decoded_entries)
        topic_lines = [entry.text for entry in normalized_entries]
        topic_uhf_lines = [entry.uhf for entry in normalized_entries]
        if not topic_lines:
            return None
        sco_index_entries = _parse_sco_index_entries(topic_lines)
        topic_title, sco_role = _sco_single_topic_title(title, source_name, topic_lines, sco_index_entries)
        topic_label = _encode_legacy_text(topic_title)
        topics = [
            TopicRecord(
                context_id=0,
                raw_lines=_legacy_raw_lines(topic_lines),
                index_terms=[topic_label],
                alias_strings=[profile.version, source_name, "sco-huffman"],
                names=[topic_title],
                uhf_content=topic_uhf_lines,
            )
        ]
        index_entries = [IndexEntry(label=topic_label, context_id=0)]
        contents = [ContentNode(label=topic_title, topic_id=0)]
        if sco_role is not None:
            title = f"{profile.label} - {topic_title}"

    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        contents=contents,
        metadata={
            "title": title,
            "description": title,
            "metadata_already_decoded": True,
            "text_encoding": SCORPION_LEGACY_TEXT_ENCODING,
            "display_width": SCORPION_DISPLAY_COLUMNS,
            "source_family": "scorpion-legacy",
            "scorpion_version": profile.version,
            "scorpion_decoder": profile.decoder_name,
            "scorpion_family": profile.family,
            "scorpion_versions_order": [item.version for item in SCORPION_LEGACY_PROFILES],
            "file_size": len(data),
            "header_hex": data[:32].hex(" "),
            "ascii_preview": _extract_ascii_strings(data),
            "scorpion_parser": parser_name,
            "parsed_topic_count": len(topics),
            "scorpion_sco_marker_topic_count": len(parsed_topics),
            "scorpion_sco_role": sco_role,
            "scorpion_sco_inline_styles": inline_styles,
            "scorpion_sco_index_entry_count": sum(
                1 for entry in sco_index_entries if entry.get("kind") == "entry"
            ),
            "scorpion_sco_index_header_count": sum(
                1 for entry in sco_index_entries if entry.get("kind") == "header"
            ),
            "scorpion_sco_index_status_counts": _sco_index_counts(sco_index_entries, "status"),
            "scorpion_sco_index_flag_counts": _sco_index_counts(sco_index_entries, "flag"),
            "scorpion_sco_index_entries": sco_index_entries,
        },
        binary_data=data,
    )
    document.metadata.update(parser_metadata)
    return ensure_document_index(document)



def scorpion_legacy_profile_for_path(path: str | Path) -> ScorpionLegacyProfile | None:
    version = scorpion_version_hint_from_path(path)
    if version is None:
        return None
    return SCORPION_LEGACY_PROFILE_BY_VERSION.get(version)


def _is_scorpion_legacy_resource_file(path: Path, data: bytes | None = None) -> bool:
    name = path.name.upper()
    if name in SCORPION_LEGACY_RESOURCE_FILENAMES:
        return True
    if SCORPION_LEGACY_RESOURCE_FILENAME_RE.fullmatch(name):
        return True
    if data is None:
        return False
    if path.suffix.lower() == ".sco" and data.startswith(DOS_MZ_SIGNATURE):
        return True
    if SCORPION_LEGACY_FONT_HEADER_RE.search(data[:128]):
        return True
    return False


def is_scorpion_legacy_binary(path: str | Path, data: bytes | None = None) -> bool:
    source_path = Path(path)
    profile = scorpion_legacy_profile_for_path(source_path)
    if profile is None:
        return False
    skipped_names = SCORPION_LEGACY_SKIP_FILENAMES_BY_VERSION.get(profile.version, frozenset())
    if source_path.name.upper() in skipped_names:
        return False
    if _is_scorpion_legacy_resource_file(source_path, data):
        return False
    return source_path.suffix.lower() in profile.suffixes


def _extract_ascii_strings(data: bytes, *, min_len: int = 4, limit: int = 24) -> list[str]:
    strings: list[str] = []
    for match in ASCII_STRING_RE.finditer(data):
        text = match.group().decode("ascii", errors="ignore").strip()
        if not text:
            continue
        strings.append(text)
        if len(strings) >= limit:
            break
    return strings


def _extract_meaningful_ascii_strings(data: bytes, *, limit: int = 12) -> list[str]:
    strings: list[str] = []
    for match in ASCII_STRING_RE.finditer(data):
        text = match.group().decode("ascii", errors="ignore").strip()
        if len(text) < 6:
            continue
        alpha_count = sum(char.isalpha() for char in text)
        punctuation_count = sum(not char.isalnum() and char != " " for char in text)
        if alpha_count < 4:
            continue
        if punctuation_count > max(1, len(text) // 4):
            continue
        strings.append(text)
        if len(strings) >= limit:
            break
    return strings


def _self_contained_exe_wrapper(data: bytes) -> str | None:
    payload_size = _mz_payload_size(data)
    if payload_size is None or payload_size != len(data):
        return None
    header_window = data[: min(len(data), 128)]
    if PKLITE_SIGNATURE in header_window:
        return "dos-mz-pklite"
    return "dos-mz"


def _mz_payload_size(data: bytes) -> int | None:
    if len(data) < 0x1C or data[:2] != DOS_MZ_SIGNATURE:
        return None
    last_page_bytes = int.from_bytes(data[0x02:0x04], "little")
    total_pages = int.from_bytes(data[0x04:0x06], "little")
    header_size = int.from_bytes(data[0x08:0x0A], "little") * 16
    if total_pages <= 0:
        return None
    tail_size = 512 if last_page_bytes == 0 else last_page_bytes
    payload_size = (total_pages - 1) * 512 + tail_size
    if payload_size < header_size or payload_size > len(data):
        return None
    return payload_size


def _embedded_rar_overlay(data: bytes) -> tuple[int, bytes] | None:
    payload_size = _mz_payload_size(data)
    if payload_size is not None and payload_size < len(data):
        overlay = data[payload_size:]
        if overlay.startswith(RAR4_SIGNATURE):
            return payload_size, overlay

    embedded_offset = data.find(RAR4_SIGNATURE)
    if embedded_offset <= 0:
        return None
    return embedded_offset, data[embedded_offset:]


def _normalize_archive_member_name(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("./")
    while normalized.startswith("_/"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _parse_rar4_members(overlay: bytes) -> list[ScorpionLegacyArchiveMember]:
    if not overlay.startswith(RAR4_SIGNATURE):
        return []

    members: list[ScorpionLegacyArchiveMember] = []
    offset = len(RAR4_SIGNATURE)
    while offset + 7 <= len(overlay):
        head_type = overlay[offset + 2]
        flags = int.from_bytes(overlay[offset + 3 : offset + 5], "little")
        head_size = int.from_bytes(overlay[offset + 5 : offset + 7], "little")
        if head_size < 7 or offset + head_size > len(overlay):
            break

        add_size = 0
        if head_type == RAR_FILE_HEAD:
            name_offset = offset + 32
            if offset + 32 > len(overlay):
                break
            packed_size = int.from_bytes(overlay[offset + 7 : offset + 11], "little")
            unpacked_size = int.from_bytes(overlay[offset + 11 : offset + 15], "little")
            if flags & 0x0100:
                if offset + 40 > len(overlay):
                    break
                packed_size |= int.from_bytes(overlay[offset + 32 : offset + 36], "little") << 32
                unpacked_size |= int.from_bytes(overlay[offset + 36 : offset + 40], "little") << 32
                name_offset = offset + 40
            method = overlay[offset + 25]
            name_size = int.from_bytes(overlay[offset + 26 : offset + 28], "little")
            attributes = int.from_bytes(overlay[offset + 28 : offset + 32], "little")
            name_end = name_offset + name_size
            if name_end > offset + head_size:
                break
            raw_name = overlay[name_offset:name_end].decode("latin-1", errors="replace")
            display_name = _normalize_archive_member_name(raw_name)
            add_size = packed_size
            if display_name and not (attributes & MSDOS_DIRECTORY_ATTRIBUTE):
                members.append(
                    ScorpionLegacyArchiveMember(
                        raw_name=raw_name,
                        display_name=display_name,
                        packed_size=packed_size,
                        unpacked_size=unpacked_size,
                        method=method,
                        attributes=attributes,
                    )
                )

        offset += head_size + add_size
        if head_type == RAR_ENDARC_HEAD:
            break

    return members


def _extract_overlay_members(overlay: bytes) -> dict[str, bytes]:
    tools = ExtractorTools(
        unar=find_unar(),
        lsar=find_lsar(),
        sevenzip=find_sevenzip(),
    )
    if not tools.available:
        return {}

    with tempfile.TemporaryDirectory(prefix="scorpion-legacy-") as tmp_dir:
        temp_root = Path(tmp_dir)
        archive_path = temp_root / "overlay.rar"
        extract_root = temp_root / "extract"
        archive_path.write_bytes(overlay)
        if not extract_file(archive_path, extract_root, tools):
            return {}

        extracted: dict[str, bytes] = {}
        for item in sorted(extract_root.rglob("*")):
            if not item.is_file():
                continue
            payload = item.read_bytes()
            relative_name = item.relative_to(extract_root).as_posix()
            for key in {
                relative_name,
                item.name,
                _normalize_archive_member_name(relative_name),
                _normalize_archive_member_name(item.name),
            }:
                if key:
                    extracted.setdefault(key, payload)
        return extracted


def _text_preview_lines(data: bytes, *, limit: int = 12) -> list[str]:
    sample = data[:4096]
    if not sample or (b"\n" not in sample and b"\r" not in sample):
        return []
    newline_count = sample.count(b"\n") + sample.count(b"\r")
    text_like_bytes = sum(1 for byte in sample if byte in {0x09, 0x0A, 0x0D} or 0x20 <= byte <= 0x7E or byte >= 0xA0)
    if newline_count < 2 or text_like_bytes / len(sample) < 0.7:
        return []
    decoded = decode_bytes(sample, SCORPION_LEGACY_TEXT_ENCODING).replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in decoded.split("\n"):
        line = raw_line.rstrip("\x00").strip()
        if not line:
            continue
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _member_preview_lines(data: bytes) -> list[str]:
    lines = _text_preview_lines(data)
    if lines:
        return lines
    strings = _extract_meaningful_ascii_strings(data, limit=12)
    if not strings:
        strings = _extract_ascii_strings(data, limit=12)
    if strings:
        return strings
    return [f"Header: {data[:32].hex(' ')}", "No printable preview extracted from this member."]


def _build_preview_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    *,
    wrapper_name: str | None = None,
) -> HelpDocument:
    title = _legacy_public_document_title(profile, source_name)
    lines = _preview_lines(profile, source_name, data, wrapper_name=wrapper_name)
    topic = TopicRecord(
        context_id=0,
        raw_lines=_legacy_raw_lines(lines),
        index_terms=[title.encode("latin-1", errors="replace")],
        alias_strings=[profile.version, profile.family, source_name],
        names=[title],
        uhf_content=[render_uhf_line(line) for line in lines],
    )
    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name=source_name,
        topics=[topic],
        index_entries=[IndexEntry(label=title.encode("latin-1", errors="replace"), context_id=0)],
        metadata={
            "title": title,
            "description": title,
            "text_encoding": SCORPION_LEGACY_TEXT_ENCODING,
            "source_family": "scorpion-legacy",
            "scorpion_version": profile.version,
            "scorpion_decoder": profile.decoder_name,
            "scorpion_family": profile.family,
            "scorpion_versions_order": [item.version for item in SCORPION_LEGACY_PROFILES],
            "file_size": len(data),
            "header_hex": data[:32].hex(" "),
            "ascii_preview": _extract_ascii_strings(data),
        },
        binary_data=data,
    )
    if wrapper_name is not None:
        document.metadata["scorpion_wrapper"] = wrapper_name
    return ensure_document_index(document)


def _legacy_public_document_title(profile: ScorpionLegacyProfile, source_name: str) -> str:
    source_path = Path(source_name)
    if (
        source_path.suffix.upper() in {".DAT", ".EXE"}
        and source_path.stem.upper() in SCORPION_LEGACY_CONTAINER_STEMS
    ):
        return profile.label
    return f"{profile.label} - {source_name}"


def _normalize_v3_title(text: str) -> str:
    stripped = _normalize_v3_text_line(text)
    if not stripped:
        return ""
    if any(char.islower() for char in stripped):
        return re.sub(r"\s{2,}", " ", stripped)
    return _normalize_v1_title(stripped)


def _normalize_v3_text_line(text: str, *, preserve_layout: bool = False) -> str:
    if not text:
        return ""
    normalized = _normalize_v3_epsilon_controls(text)
    normalized = "".join(char for char in normalized if char not in V3_FORMATTING_CHARS)
    if preserve_layout:
        return normalized.rstrip()
    return normalized.strip()


def _normalize_v3_topic_lines(entries: list[str]) -> list[str]:
    normalized: list[str] = []
    for entry in entries:
        if entry.strip() and _is_v1_5_placeholder_entry(entry):
            continue
        normalized.append(_normalize_v3_text_line(entry, preserve_layout=True))
    while normalized and not normalized[0].strip():
        normalized.pop(0)
    while normalized and not normalized[-1].strip():
        normalized.pop()
    return normalized


def _nearest_non_space(text: str, start: int, step: int) -> str:
    index = start
    while 0 <= index < len(text):
        char = text[index]
        if not char.isspace():
            return char
        index += step
    return ""


def _normalize_v3_epsilon_controls(text: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(text):
        if char != "ε":
            chars.append(char)
            continue
        previous_char = _nearest_non_space(text, index - 1, -1)
        next_char = _nearest_non_space(text, index + 1, 1)
        if previous_char.isalnum() and next_char.isalnum():
            chars.append("E")
    return "".join(chars)


def _build_archive_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    overlay_offset: int,
    overlay: bytes,
    members: list[ScorpionLegacyArchiveMember],
) -> HelpDocument:
    title = _legacy_public_document_title(profile, source_name)
    extracted_members = _extract_overlay_members(overlay) if any(member.packed_size > 0 for member in members) else {}
    overview_lines = [
        title,
        "",
        f"Decoder: {profile.decoder_name}",
        f"Family: {profile.family}",
        f"File: {source_name}",
        f"Size: {len(data)} bytes",
        f"Wrapper: DOS MZ SFX with embedded RAR overlay",
        f"Overlay offset: {overlay_offset}",
        f"Overlay size: {len(overlay)} bytes",
        f"Contained files: {len(members)}",
        "",
        "Archive members:",
    ]
    overview_lines.extend(
        f"{member.display_name} ({member.unpacked_size} B, packed {member.packed_size} B, method 0x{member.method:02X})"
        for member in members
    )

    topics = [
        TopicRecord(
            context_id=0,
            raw_lines=_legacy_raw_lines(overview_lines),
            index_terms=[title.encode("latin-1", errors="replace")],
            alias_strings=[profile.version, profile.family, source_name, "archive-overview"],
            names=[title],
            uhf_content=[render_uhf_line(line) for line in overview_lines],
        )
    ]
    index_entries = [IndexEntry(label=title.encode("latin-1", errors="replace"), context_id=0)]

    for context_id, member in enumerate(members, start=1):
        member_payload = extracted_members.get(member.display_name) or extracted_members.get(member.raw_name)
        member_lines = [
            member.display_name,
            "",
            f"Wrapper file: {source_name}",
            f"Archive path: {member.raw_name}",
            f"Packed size: {member.packed_size} bytes",
            f"Unpacked size: {member.unpacked_size} bytes",
            f"RAR method: 0x{member.method:02X}",
            f"DOS attributes: 0x{member.attributes:08X}",
            "",
        ]
        if member_payload is None:
            member_lines.append("Preview unavailable: archive member could not be unpacked in this environment.")
        else:
            member_lines.append("Preview:")
            member_lines.extend(_member_preview_lines(member_payload))

        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=_legacy_raw_lines(member_lines),
                index_terms=[member.display_name.encode("latin-1", errors="replace")],
                alias_strings=[member.display_name, member.raw_name, profile.version, source_name],
                names=[member.display_name],
                uhf_content=[render_uhf_line(line) for line in member_lines],
            )
        )
        index_entries.append(IndexEntry(label=member.display_name.encode("latin-1", errors="replace"), context_id=context_id))

    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        metadata={
            "title": title,
            "description": title,
            "text_encoding": SCORPION_LEGACY_TEXT_ENCODING,
            "source_family": "scorpion-legacy",
            "scorpion_version": profile.version,
            "scorpion_decoder": profile.decoder_name,
            "scorpion_family": profile.family,
            "scorpion_versions_order": [item.version for item in SCORPION_LEGACY_PROFILES],
            "file_size": len(data),
            "header_hex": data[:32].hex(" "),
            "ascii_preview": _extract_ascii_strings(data),
            "scorpion_wrapper": "dos-mz-sfx-rar",
            "overlay_offset": overlay_offset,
            "overlay_size": len(overlay),
            "archive_member_count": len(members),
            "archive_members": [
                {
                    "name": member.display_name,
                    "raw_name": member.raw_name,
                    "packed_size": member.packed_size,
                    "unpacked_size": member.unpacked_size,
                    "method": member.method,
                    "attributes": member.attributes,
                }
                for member in members
            ],
        },
        binary_data=data,
    )
    return ensure_document_index(document)


def _preview_lines(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    *,
    wrapper_name: str | None = None,
) -> list[str]:
    lines = [
        profile.label,
        "",
        f"Decoder: {profile.decoder_name}",
        f"Family: {profile.family}",
        f"File: {source_name}",
        f"Size: {len(data)} bytes",
    ]
    if wrapper_name:
        lines.append(f"Wrapper: {wrapper_name}")
    lines.extend(
        [
        f"Header: {data[:32].hex(' ')}",
        f"Description: {profile.description}",
        "",
        "ASCII preview:",
        ]
    )
    strings = _extract_ascii_strings(data)
    if strings:
        lines.extend(strings)
    else:
        lines.append("No printable ASCII strings extracted from this binary slice.")
    return lines


class ScorpionVersionReaderBase:
    def __init__(self, profile: ScorpionLegacyProfile, source_name: str, source_path: Path):
        self.profile = profile
        self.source_name = source_name
        self.source_path = source_path

    def _finalize_document(self, document: HelpDocument) -> HelpDocument:
        document.metadata["scorpion_reader_class"] = type(self).__name__
        document.metadata["ui"] = dict(SCORPION_UI_THEME)
        raw_keys = document.metadata.get("transport_metadata_keys")
        transport_keys = [key for key in raw_keys if isinstance(key, str)] if isinstance(raw_keys, list) else []
        for key in SCORPION_LEGACY_TRANSPORT_METADATA_KEYS:
            if key not in transport_keys:
                transport_keys.append(key)
        document.metadata["transport_metadata_keys"] = transport_keys
        return document

    def read_bytes(self, data: bytes) -> HelpDocument:
        return self._finalize_document(_build_preview_document(self.profile, self.source_path.name, data))


class ScorpionRarSfxReaderBase(ScorpionVersionReaderBase):
    def read_bytes(self, data: bytes) -> HelpDocument:
        overlay_info = _embedded_rar_overlay(data)
        if overlay_info is not None:
            overlay_offset, overlay = overlay_info
            members = _parse_rar4_members(overlay)
            if members:
                return self._finalize_document(
                    _build_archive_document(self.profile, self.source_path.name, data, overlay_offset, overlay, members)
                )
        return self._finalize_document(_build_preview_document(self.profile, self.source_path.name, data))


from .scorpion_legacy_v1x import (
    ScorpionV1Reader,
    ScorpionV1_5Reader,
    _is_v1_5_placeholder_entry,
    _normalize_v1_5_section_entries,
    _normalize_v1_title,
)
from .scorpion_legacy_v3x import ScorpionV3Reader, ScorpionV3_5Reader
from .scorpion_legacy_v4x import ScorpionV4Reader, ScorpionV5Reader
from .scorpion_legacy_v6x import (
    ScorpionV6Reader,
    ScorpionV7Reader,
    ScorpionV8Reader,
    ScorpionV10Reader,
    ScorpionV11Reader,
    ScorpionV12Reader,
    ScorpionV13Reader,
    ScorpionV14Reader,
)


SCORPION_VERSION_READER_CLASSES = {
    "1": ScorpionV1Reader,
    "1.5": ScorpionV1_5Reader,
    "3": ScorpionV3Reader,
    "3.5": ScorpionV3_5Reader,
    "4": ScorpionV4Reader,
    "5": ScorpionV5Reader,
    "6": ScorpionV6Reader,
    "7": ScorpionV7Reader,
    "8": ScorpionV8Reader,
    "10": ScorpionV10Reader,
    "11": ScorpionV11Reader,
    "12": ScorpionV12Reader,
    "13": ScorpionV13Reader,
    "14": ScorpionV14Reader,
}


def scorpion_legacy_reader_class_for_path(path: str | Path) -> type[ScorpionVersionReaderBase] | None:
    profile = scorpion_legacy_profile_for_path(path)
    if profile is None:
        return None
    return SCORPION_VERSION_READER_CLASSES.get(profile.version)


class ScorpionLegacyReader(HelpReaderBase):
    """Version-aware scaffold reader for pre-v15 Scorpions Cheater formats."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        source_path = self.source_path or Path(self.source_name)
        profile = scorpion_legacy_profile_for_path(source_path)
        if profile is None:
            raise ValueError("Not a versioned legacy Scorpions Cheater file.")
        skipped_names = SCORPION_LEGACY_SKIP_FILENAMES_BY_VERSION.get(profile.version, frozenset())
        if source_path.name.upper() in skipped_names:
            raise ValueError("Scorpions Cheater resource file is not a help corpus.")
        if _is_scorpion_legacy_resource_file(source_path, data):
            raise ValueError("Scorpions Cheater resource file is not a help corpus.")
        if source_path.suffix.lower() not in profile.suffixes:
            raise ValueError("Scorpions Cheater file does not match the expected version family.")

        reader_class = scorpion_legacy_reader_class_for_path(source_path) or ScorpionVersionReaderBase
        reader = reader_class(profile=profile, source_name=self.source_name, source_path=source_path)
        return reader.read_bytes(data)
