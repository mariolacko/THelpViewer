"""Experimental reader for Scorpion's Cheater `.dat` content databases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

from ..base import (
    ContentNode,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    TopicRecord,
)
from ..uhf_markup import format_uhf_link


SCORPION_DAT_SIGNATURE = b"\x12\x1E\x03-ALL."
FIELD_DATE = b"propDATE"
FIELD_NAME = b"propNAME"
FIELD_ORIG = b"propORIG"
FIELD_DATA = b"DATA"
PAGE_TAG_RE = re.compile(rb"\[([A-Z0-9]{4})\]")
BRACKET_TAG_RE = re.compile(r"\[\s*([A-Z0-9](?:\s*[A-Z0-9]){3})\s*\]")
LINE_TAG_RE = re.compile(r"(?m)^\s*[`' ]*([A-Z](?:\s*\d){3})\b")
SCORPION_DROP_BYTES = frozenset({0x8D, 0x94, 0x9D, 0x9E, 0xF0, 0xF2, 0xF7})
SCORPION_CHAR_MAP = {
    0x87: "č",
    0x88: "ě",
    0x91: "ž",
    0xA8: "š",
    0xA9: "ř",
}
SCORPION_ALLOWED_DISPLAY_CHARS = set("áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ")
SCORPION_ALLOWED_PUNCTUATION = set(" .,:;!?&'\"()+-/%@[]=*_#<>")
RESOURCE_RECORD_RE = re.compile(
    r"^(?:_main|datum(?:[A-Z])?|egg|font\d+|fontok|fontkruh|library[A-Z]?|obr\d+|obrview|pirat|rok[A-Z]?|scroll|verze[A-Z]?|xicht)$",
    re.IGNORECASE,
)
SCORPION_TITLE_OVERRIDES = {
    "D220": "DOPISY z verze 22.0",
    "R005": "Minislovník + zkratky",
    "R006": "Dotazník",
    "R010": "Editorial a korespondence",
    "R201": "Nejčastější otázky & odpovědi",
    "R222": "O programu",
    "R223": "Kontakt",
    "R204": "Historie",
}
SCORPION_PROGRAM_MENU = [
    ("O programu", "R222"),
    ("Editorial a korespondence", "R010"),
    ("Spolupracovali", "program-spolupracovali"),
    ("Kontakt", "R223"),
    ("Historie", "R204"),
    ("Dotazník", "R006"),
    ("Nejčastější otázky & odpovědi", "R201"),
    ("Jak používat cheaty ??", None),
    ("WWW adresy", None),
    ("Minislovník + zkratky", "R005"),
    ("Cheater 2000", None),
    ("Herní servery", None),
]
SCORPION_PROGRAM_MENU_HINTS = {
    "Editorial a korespondence": ("Editorial", "koresp"),
    "Historie": ("His",),
    "Dotazník": ("Dot",),
    "Nejčastější otázky & odpovědi": ("Nej", "odpov"),
    "Jak používat cheaty ??": ("Jak", "cheat"),
    "WWW adresy": ("WWW", "ad"),
    "Minislovník + zkratky": ("Minisl", "zkrat"),
    "Cheater 2000": ("Cheater", "2000", "er 20"),
    "Herní servery": ("Hern", "server"),
}
SCORPION_PROGRAM_SYNTHETIC_TOPICS = (
    ("kecy", "Spolupracovali", "program-spolupracovali", "spolu"),
)
SCORPION_LIBRARY_SECTIONS = (
    ("cheaty.dat", "Cheaty"),
    ("navody.dat", "Návody"),
    ("vtipy.dat", "Vtipy"),
    ("easter.dat", "Easter"),
)
SCORPION_SECTION_ANCHORS = (
    ("kecy", "R010", b"DOPISY", "D220"),
)


def is_scorpion_dat_binary(data: bytes) -> bool:
    """Return True when *data* looks like a Scorpion DAT content database."""
    if not data.startswith(SCORPION_DAT_SIGNATURE):
        return False
    if data.startswith(b"\x00\x00\x01\x00"):
        return False
    first_record = data.find(FIELD_DATE, 0, 64)
    return first_record >= 0 and data.find(FIELD_NAME, first_record, first_record + 64) >= 0


@dataclass(frozen=True, slots=True)
class _ScorpionRecord:
    date: str
    name: str
    origin: str
    payload: bytes
    trailer: bytes
    page_tag: str | None


@dataclass(frozen=True, slots=True)
class _ScorpionSegment:
    page_tag: str | None
    body: str
    source_body: str | None = None
    raw_payload: bytes | None = None


@dataclass(frozen=True, slots=True)
class _ScorpionMenuEntry:
    label: str
    alias: str | None
    start: int
    blob: bytes
    hint: str
    raw_hint: str = ""


def _read_length_prefixed_field(data: bytes, offset: int, field_name: bytes) -> tuple[bytes, int]:
    if data[offset:offset + len(field_name)] != field_name:
        raise ValueError(f"Expected {field_name!r} at offset {offset}")
    offset += len(field_name)
    if offset + 4 > len(data):
        raise ValueError("Incomplete Scorpion DAT length field")
    size = int.from_bytes(data[offset:offset + 4], "big")
    offset += 4
    end = offset + size
    if end > len(data):
        raise ValueError("Scorpion DAT field points outside the file")
    return data[offset:end], end


def _parse_records(data: bytes) -> list[_ScorpionRecord]:
    records: list[_ScorpionRecord] = []
    offset = data.find(FIELD_DATE)
    if offset < 0:
        return records

    while offset >= 0 and offset < len(data):
        try:
            date_bytes, offset = _read_length_prefixed_field(data, offset, FIELD_DATE)
            name_bytes, offset = _read_length_prefixed_field(data, offset, FIELD_NAME)
            origin_bytes, offset = _read_length_prefixed_field(data, offset, FIELD_ORIG)
        except ValueError:
            break

        if data[offset:offset + len(FIELD_DATA)] != FIELD_DATA:
            break
        offset += len(FIELD_DATA)
        if offset + 4 > len(data):
            break
        payload_size = int.from_bytes(data[offset:offset + 4], "big")
        offset += 4
        payload_end = offset + payload_size
        trailer_end = payload_end + 4
        if trailer_end > len(data):
            break

        payload = data[offset:payload_end]
        trailer = data[payload_end:trailer_end]
        offset = trailer_end

        page_match = PAGE_TAG_RE.search(payload[:256])
        page_tag = page_match.group(1).decode("ascii", errors="replace") if page_match else None
        records.append(
            _ScorpionRecord(
                date=date_bytes.decode("latin-1", errors="replace"),
                name=name_bytes.decode("latin-1", errors="replace"),
                origin=origin_bytes.decode("latin-1", errors="replace"),
                payload=payload,
                trailer=trailer,
                page_tag=page_tag,
            )
        )

        if data[offset:offset + len(FIELD_DATE)] != FIELD_DATE:
            break

    return records


def _ascii_stream(payload: bytes) -> str:
    """Return a printable ASCII-biased view of one proprietary payload."""
    if not payload:
        return ""

    out: list[str] = []
    for value in payload:
        if value in (0x0D, 0x0A):
            out.append("\n")
        elif value == 0x09:
            out.append(" ")
        elif 0x20 <= value < 0x7F:
            out.append(chr(value))
        else:
            # Most non-ASCII bytes are formatting opcodes. Keeping them produces
            # far noisier output than a clean ASCII-biased fallback.
            out.append(" ")
    return "".join(out)


def _cp852_stream(payload: bytes) -> str:
    """Return a one-byte-per-char CP852-ish view suitable for title recovery."""
    if not payload:
        return ""

    out: list[str] = []
    for value in payload:
        if value in (0x0D, 0x0A):
            out.append("\n")
        elif value == 0x09:
            out.append(" ")
        elif value < 0x20:
            out.append(" ")
        else:
            out.append(bytes((value,)).decode("cp852", errors="replace"))
    return "".join(out)


def _display_stream(payload: bytes) -> str:
    """Return a best-effort display text view with known control bytes removed."""
    if not payload:
        return ""

    out: list[str] = []
    for value in payload:
        if value in (0x0D, 0x0A):
            out.append("\n")
        elif value == 0x09:
            out.append(" ")
        elif value < 0x20:
            out.append(" ")
        elif value in SCORPION_DROP_BYTES:
            continue
        elif value in SCORPION_CHAR_MAP:
            out.append(SCORPION_CHAR_MAP[value])
        else:
            out.append(bytes((value,)).decode("cp852", errors="replace"))
    return "".join(out)


def _normalize_tag(token: str | None) -> str | None:
    if not token:
        return None
    normalized = re.sub(r"\s+", "", token).upper()
    if len(normalized) != 4 or not normalized.isalnum():
        return None
    return normalized


def _fold_ascii_alnum(text: str) -> tuple[str, list[int]]:
    folded_chars: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        decomp = unicodedata.normalize("NFKD", char)
        base = "".join(
            piece
            for piece in decomp
            if not unicodedata.combining(piece)
        )
        if not base:
            continue
        for piece in base:
            lowered = piece.casefold()
            if lowered.isascii() and lowered.isalnum():
                folded_chars.append(lowered)
                positions.append(index)
    return "".join(folded_chars), positions


def _find_folded_ascii_index(
    haystack_folded: str,
    haystack_positions: list[int],
    needle: str,
    *,
    start_char: int = 0,
) -> int | None:
    start_index = 0
    if start_char > 0:
        while start_index < len(haystack_positions) and haystack_positions[start_index] < start_char:
            start_index += 1
    needle_folded, _ = _fold_ascii_alnum(needle)
    if not needle_folded:
        return None
    folded_index = haystack_folded.find(needle_folded, start_index)
    if folded_index < 0:
        return None
    return haystack_positions[folded_index]


def _menu_blob_hint(blob: bytes) -> str:
    if not blob:
        return ""
    text = _cp852_stream(blob)
    folded, _ = _fold_ascii_alnum(text)
    return folded.upper()


def _extract_program_menu_target_hint(text: str, raw_hint: str = "") -> str:
    folded, _ = _fold_ascii_alnum(text)
    if not folded:
        return ""

    raw_folded = raw_hint.casefold()
    r_index = raw_folded.find("r")
    if r_index >= 0:
        digits: list[str] = []
        for char in raw_folded[r_index + 1:]:
            if char.isdigit():
                digits.append(char)
                if len(digits) >= 4:
                    break
            elif digits and char.isalpha():
                continue
            elif digits:
                break
        if digits:
            number = "".join(digits)
            if len(number) <= 3:
                return f"R{number.zfill(3)}"
            return f"R{number}"

    matches = list(re.finditer(r"\d+", folded))
    if not matches:
        return ""
    if len(matches) == 1:
        value = matches[0].group(0)
        if not raw_hint and len(value) <= 2:
            return ""
        return value if len(value) >= 2 else ""

    merged = "".join(match.group(0) for match in matches[:2])
    if len(merged) <= 4:
        if not raw_hint and len(merged) <= 2:
            return ""
        return merged if len(merged) >= 2 else ""
    value = matches[0].group(0)
    if not raw_hint and len(value) <= 2:
        return ""
    return value if len(value) >= 2 else ""


def _find_program_menu_label_start(
    haystack_folded: str,
    haystack_positions: list[int],
    label: str,
    *,
    start_char: int,
) -> int | None:
    found = _find_folded_ascii_index(
        haystack_folded,
        haystack_positions,
        label,
        start_char=start_char,
    )
    if found is not None:
        return found
    for hint in SCORPION_PROGRAM_MENU_HINTS.get(label, ()):
        found = _find_folded_ascii_index(
            haystack_folded,
            haystack_positions,
            hint,
            start_char=start_char,
        )
        if found is not None:
            return found
    return None


def _extract_program_menu_entries(record: _ScorpionRecord) -> list[_ScorpionMenuEntry]:
    menu_end = record.payload.find(b"04x")
    if menu_end < 0:
        menu_end = len(record.payload)
    menu_text = _cp852_stream(record.payload[:menu_end])
    menu_folded, menu_positions = _fold_ascii_alnum(menu_text)

    cursor = _find_program_menu_label_start(
        menu_folded,
        menu_positions,
        "O programu",
        start_char=0,
    )
    if cursor is None:
        return []

    alias_by_label = dict(SCORPION_PROGRAM_MENU)
    positions: list[tuple[str, int]] = []
    for label, _alias in SCORPION_PROGRAM_MENU:
        found = _find_program_menu_label_start(
            menu_folded,
            menu_positions,
            label,
            start_char=cursor,
        )
        if found is None or found >= menu_end:
            continue
        positions.append((label, found))
        cursor = found + 1

    entries: list[_ScorpionMenuEntry] = []
    for index, (label, start) in enumerate(positions):
        next_pos = menu_end
        if index + 1 < len(positions):
            next_pos = positions[index + 1][1]
        label_end = start + len(label)
        blob = record.payload[label_end:next_pos]
        slice_text = menu_text[start:next_pos]
        raw_hint = _menu_blob_hint(blob)
        entries.append(
            _ScorpionMenuEntry(
                label=label,
                alias=alias_by_label.get(label),
                start=start,
                blob=blob,
                hint=_extract_program_menu_target_hint(slice_text, raw_hint),
                raw_hint=raw_hint,
            )
        )
    return entries


def _valid_tag_context(text: str, position: int) -> bool:
    if position <= 24:
        return True
    prefix = text[max(0, position - 12):position]
    if prefix.strip() == "":
        return True
    return "\n" in prefix


def _looks_like_segment_start(text: str, end_position: int) -> bool:
    suffix = text[end_position:end_position + 12]
    if suffix.strip() == "":
        return True
    if "\n" in suffix:
        return True

    heading_probe = text[end_position:end_position + 20]
    return sum(ch.isupper() for ch in heading_probe) >= 4 and sum(ch.islower() for ch in heading_probe) <= 1


def _tag_matches_record_family(record: _ScorpionRecord, tag: str) -> bool:
    base = record.page_tag
    if not base:
        return True
    if base[0].isalpha():
        if tag[0].isalpha():
            return tag[0] == base[0]
        return tag[0].isdigit()
    return tag[0].isdigit()


def _find_page_markers(record: _ScorpionRecord, text: str) -> list[tuple[int, str]]:
    markers: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    for match in BRACKET_TAG_RE.finditer(text):
        tag = _normalize_tag(match.group(1))
        if (
            not tag
            or not _valid_tag_context(text, match.start())
            or not _looks_like_segment_start(text, match.end())
            or not _tag_matches_record_family(record, tag)
        ):
            continue
        key = (match.start(), tag)
        if key not in seen:
            markers.append(key)
            seen.add(key)

    for match in LINE_TAG_RE.finditer(text):
        tag = _normalize_tag(match.group(1))
        if not tag or tag == "CTRL":
            continue
        if not _valid_tag_context(text, match.start()) or not _tag_matches_record_family(record, tag):
            continue
        key = (match.start(), tag)
        if key not in seen:
            markers.append(key)
            seen.add(key)

    markers.sort(key=lambda item: item[0])
    return markers


def _split_segments(record: _ScorpionRecord) -> list[_ScorpionSegment]:
    text = _ascii_stream(record.payload)
    source_text = _cp852_stream(record.payload)
    markers = _find_page_markers(record, text)
    if not markers:
        return [
            _ScorpionSegment(
                page_tag=record.page_tag,
                body=text,
                source_body=source_text,
                raw_payload=record.payload,
            )
        ]

    segments: list[_ScorpionSegment] = []
    for index, (start, tag) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        body = text[start:end]
        source_body = source_text[start:end]
        segments.append(
            _ScorpionSegment(
                page_tag=tag,
                body=body,
                source_body=source_body,
                raw_payload=record.payload[start:end],
            )
        )
    return _split_section_anchors(record, segments)


def _split_section_anchors(record: _ScorpionRecord, segments: list[_ScorpionSegment]) -> list[_ScorpionSegment]:
    if not segments:
        return segments

    result: list[_ScorpionSegment] = []
    for segment in segments:
        split_segment = False
        raw_payload = segment.raw_payload or b""
        for record_name, parent_tag, needle, synthetic_tag in SCORPION_SECTION_ANCHORS:
            if record.name.lower() != record_name or segment.page_tag != parent_tag:
                continue
            relative_offset = raw_payload.find(needle)
            if relative_offset <= 0:
                continue

            pre_body = segment.body[:relative_offset]
            pre_source = (segment.source_body or "")[:relative_offset]
            pre_raw = raw_payload[:relative_offset]

            post_body = segment.body[relative_offset:]
            post_source = (segment.source_body or "")[relative_offset:]
            post_raw = raw_payload[relative_offset:]

            result.append(
                _ScorpionSegment(
                    page_tag=segment.page_tag,
                    body=pre_body,
                    source_body=pre_source,
                    raw_payload=pre_raw,
                )
            )
            result.append(
                _ScorpionSegment(
                    page_tag=synthetic_tag,
                    body=post_body,
                    source_body=post_source,
                    raw_payload=post_raw,
                )
            )
            split_segment = True
            break

        if not split_segment:
            result.append(segment)
    return result


def _clean_visible_line(raw_line: str) -> str:
    line = raw_line.replace("`", " ").replace("\\", " ")
    line = re.sub(r"\[[^\]]+\]", " ", line)
    line = "".join(
        char
        if (
            (char.isascii() and (char.isalnum() or char in SCORPION_ALLOWED_PUNCTUATION))
            or char in SCORPION_ALLOWED_DISPLAY_CHARS
            or char.isspace()
        )
        else " "
        for char in line
    )
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _clean_heading_source(raw_line: str) -> str:
    line = raw_line.replace("`", " ").replace("\\", " ")
    line = re.sub(r"\[[^\]]+\]", " ", line)
    line = "".join(
        char
        if (
            (char.isascii() and (char.isalnum() or char in SCORPION_ALLOWED_PUNCTUATION))
            or char in SCORPION_ALLOWED_DISPLAY_CHARS
            or char.isspace()
        )
        else " "
        for char in line
    )
    return line.strip()


def _clean_title_source_line(raw_line: str) -> str:
    line = raw_line.replace("`", " ").replace("\\", " ")
    line = re.sub(r"\[[^\]]+\]", " ", line)
    line = "".join(
        char
        if (
            char.isascii() and char.isalnum()
            or char in " .,:;!?&'\"()+-/%"
        )
        else " "
        for char in line
    )
    return line.strip()


def _looks_like_heading(line: str) -> bool:
    compact = line.replace(" ", "")
    if len(compact) < 4:
        return False
    return compact.isupper() or line.count(" ") >= max(3, len(line) // 5)


def _join_title_tokens(tokens: list[str]) -> list[str]:
    joined: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if len(token) == 1 and token.isalnum():
            chars = [token]
            probe = index + 1
            while probe < len(tokens) and len(tokens[probe]) == 1 and tokens[probe].isalnum():
                chars.append(tokens[probe])
                probe += 1
            if len(chars) >= 2:
                joined.append("".join(chars))
                index = probe
                continue

        if (
            token.isalpha()
            and index + 1 < len(tokens)
            and tokens[index + 1].isalpha()
            and (len(token) == 1 or len(tokens[index + 1]) <= 2)
        ):
            joined.append(token + tokens[index + 1])
            index += 2
            continue

        joined.append(token)
        index += 1

    return joined


def _normalize_heading(line: str) -> str:
    parts = [part.strip() for part in re.split(r"\s{2,}", line) if part.strip()]
    if not parts:
        return _clean_visible_line(line)

    normalized_parts: list[str] = []
    for part in parts:
        tokens = [token for token in part.split() if token]
        tokens = _join_title_tokens(tokens)
        normalized_parts.append(" ".join(tokens))

    normalized = " ".join(normalized_parts)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    normalized = re.sub(r"([(\[\"])\s+", r"\1", normalized)
    normalized = re.sub(r"\s+([)\]\"])", r"\1", normalized)
    normalized = re.sub(r"\s*'\s*(\d)", r"'\1", normalized)
    normalized = re.sub(r"\s*-\s*", " - ", normalized)
    return normalized.strip()


def _normalize_title_heading(line: str) -> str:
    parts = [part.strip() for part in re.split(r"\s{3,}", line) if part.strip()]
    if not parts:
        parts = [line.strip()]

    normalized_parts: list[str] = []
    for part in parts:
        tokens = [token for token in part.split() if token]
        if not tokens:
            continue

        merged_tokens: list[str] = []
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token == "'" and index + 2 < len(tokens) and tokens[index + 1].isdigit() and tokens[index + 2].isdigit():
                merged_tokens.append("'" + tokens[index + 1] + tokens[index + 2])
                index += 3
                continue
            if token.isalpha() and len(token) == 1 and index + 1 < len(tokens) and tokens[index + 1].isalpha() and len(tokens[index + 1]) <= 2:
                merged_tokens.append(token + tokens[index + 1])
                index += 2
                continue
            if token.isalpha() and len(token) >= 4 and index + 1 < len(tokens) and tokens[index + 1].isalpha() and len(tokens[index + 1]) <= 2:
                merged_tokens.append(token + tokens[index + 1])
                index += 2
                continue
            merged_tokens.append(token)
            index += 1
        tokens = merged_tokens

        short_tokens = sum(
            1
            for token in tokens
            if len(token) <= 2 and any(char.isalnum() for char in token)
        )
        if short_tokens >= max(2, len(tokens) - 1):
            normalized_part = "".join(tokens)
        else:
            normalized_part = " ".join(_join_title_tokens(tokens))
        normalized_parts.append(normalized_part)

    normalized = " ".join(normalized_parts)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    normalized = re.sub(r"\s*'\s*(\d)", r"'\1", normalized)
    normalized = re.sub(r"\bT he\b", "The", normalized)
    normalized = re.sub(r"\bA dventure\b", "Adventure", normalized)
    normalized = re.sub(r"\s*-\s*", " - ", normalized)
    return normalized.strip()


def _title_candidate_score(candidate: str) -> int:
    letters = sum(ch.isalpha() for ch in candidate)
    digits = sum(ch.isdigit() for ch in candidate)
    weird = sum(
        1
        for ch in candidate
        if not (ch.isalnum() or ch in " .,:;!?&'\"()+-/%")
    )
    score = letters * 3 + digits
    if _looks_like_heading(candidate):
        score += 20
    score -= weird * 8
    score -= max(len(candidate) - 72, 0)
    if candidate.endswith((".", ":", ";", ",")):
        score -= 6
    return score


def _is_plausible_title(candidate: str) -> bool:
    compact = _compact_text(candidate)
    if len(compact) < 6 or len(candidate) > 80:
        return False
    if candidate.endswith(":"):
        return False
    if re.match(r"^\d+[.)]\s", candidate):
        return False
    words = candidate.split()
    if len(words) > 10:
        return False
    if candidate.count(",") > 2 or candidate.count(";") > 0:
        return False
    return True


def _segment_title_candidates(segment: _ScorpionSegment) -> list[str]:
    source = segment.source_body or segment.body
    candidates: list[str] = []
    for raw_line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = _clean_title_source_line(raw_line)
        if segment.page_tag and _normalize_tag(cleaned.strip("[] ")) == segment.page_tag:
            continue
        if not cleaned:
            continue
        candidate = _normalize_title_heading(cleaned)
        compact = _compact_text(candidate)
        if len(compact) < 6:
            continue
        candidates.append(candidate)
        if len(candidates) >= 4:
            break
    return candidates


def _segment_visible_lines(segment: _ScorpionSegment) -> list[str]:
    display_body = _display_stream(segment.raw_payload or b"")
    body_text = display_body or segment.body
    lines: list[str] = []
    seen_blank = False
    for raw_line in body_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        heading_source = _clean_heading_source(raw_line)
        line = _clean_visible_line(raw_line)
        if segment.page_tag and _normalize_tag(line.strip("[] ")) == segment.page_tag:
            continue
        if not line:
            if not seen_blank and lines:
                lines.append("")
                seen_blank = True
            continue
        if _looks_like_heading(heading_source):
            line = _normalize_heading(heading_source)
        seen_blank = False
        lines.append(line)

    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _guess_segment_title(record: _ScorpionRecord, segment: _ScorpionSegment, visible_lines: list[str]) -> str:
    if segment.page_tag and segment.page_tag in SCORPION_TITLE_OVERRIDES:
        return SCORPION_TITLE_OVERRIDES[segment.page_tag]
    if not segment.page_tag and record.name.lower().startswith("seznam"):
        return "Seznam položek"

    for candidate in _segment_title_candidates(segment):
        if _is_plausible_title(candidate):
            return candidate

    if visible_lines:
        first_line = visible_lines[0].strip()
        if _is_plausible_title(first_line):
            return first_line

    for line in visible_lines[:4]:
        candidate = line.strip()
        if not candidate or not _looks_like_heading(candidate):
            continue
        compact = _compact_text(candidate)
        if len(compact) >= 6 and len(candidate) <= 80:
            return candidate

    best_candidate: str | None = None
    best_score: int | None = None
    for line in visible_lines[:6]:
        candidate = line.strip()
        if not candidate:
            continue
        if len(candidate) < 6 or sum(ch.isalpha() for ch in candidate) < 4:
            continue
        score = _title_candidate_score(candidate)
        if best_score is None or score > best_score:
            best_candidate = candidate
            best_score = score

    if best_candidate:
        return best_candidate

    title = record.name.strip() or "record"
    if segment.page_tag:
        return f"{title} [{segment.page_tag}]"
    return title


def _is_duplicate_heading(line: str, title: str) -> bool:
    compact_line = _compact_text(line)
    compact_title = _compact_text(title)
    if len(compact_line) < 6 or len(compact_title) < 6:
        return False
    if compact_line == compact_title:
        return True
    if compact_line.startswith(compact_title[: max(6, len(compact_title) // 2)]):
        return True
    if _looks_like_heading(line) and compact_title[:6] in compact_line:
        return True
    return False


def _topic_lines(record: _ScorpionRecord, segment: _ScorpionSegment, visible_lines: list[str], title: str) -> list[str]:
    lines: list[str] = [title]
    body_lines = list(visible_lines)
    if body_lines and _is_duplicate_heading(body_lines[0], title):
        body_lines = body_lines[1:]

    if body_lines and body_lines[0] != title:
        lines.append("")
        lines.extend(body_lines)
    if not body_lines:
        lines.extend(["", "<binary resource record>"])

    lines.extend(
        [
            "",
            f"Source record: {record.name}",
        ]
    )
    if segment.page_tag:
        lines.append(f"Page tag: {segment.page_tag}")
    lines.append(f"Date: {record.date}")
    lines.append(f"Origin: {record.origin}")
    return lines


def _is_textual_record(record: _ScorpionRecord, segments: list[_ScorpionSegment], visible_lines: list[str]) -> bool:
    if len(segments) > 1:
        return True
    if record.page_tag:
        return True
    if RESOURCE_RECORD_RE.match(record.name):
        return False
    return any(sum(ch.isalpha() for ch in line) >= 4 for line in visible_lines)


def _display_name_from_source(path: Path) -> str:
    stem = path.stem.lower()
    labels = {
        "cheaty": "Scorpion's Cheater - Cheats",
        "navody": "Scorpion's Cheater - Guides",
        "program": "Scorpion's Cheater - Program",
        "vtipy": "Scorpion's Cheater - Jokes",
        "easter": "Scorpion's Cheater - Easter",
    }
    return labels.get(stem, f"Scorpion's Cheater - {path.stem}")


def _build_alias_topic_lookup(topics: list[TopicRecord]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for topic in topics:
        lookup[str(topic.context_id)] = topic.context_id
        for alias in topic.alias_strings:
            normalized = alias.strip()
            if normalized:
                lookup.setdefault(normalized, topic.context_id)
    return lookup


def _compact_map(text: str) -> tuple[str, list[int]]:
    compact: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        if char.isalnum():
            compact.append(char.lower())
            positions.append(index)
    return "".join(compact), positions


def _compact_text(text: str) -> str:
    return "".join(char.lower() for char in text if char.isalnum())


def _find_compact_position(text: str, needle: str) -> int | None:
    compact, positions = _compact_map(text)
    target = "".join(char.lower() for char in needle if char.isalnum())
    if not target:
        return None
    compact_index = compact.find(target)
    if compact_index < 0:
        return None
    return positions[compact_index]


def _build_synthetic_program_topic(
    *,
    record: _ScorpionRecord,
    title: str,
    alias: str,
    search_term: str,
    context_id: int,
) -> TopicRecord | None:
    text = _ascii_stream(record.payload)
    start = _find_compact_position(text, search_term)
    if start is None:
        return None

    end = len(text)
    for marker_start, marker_tag in _find_page_markers(record, text):
        if marker_start > start and marker_tag.startswith("R"):
            end = marker_start
            break

    body = text[start:end]
    raw_body = record.payload[start:end]
    segment = _ScorpionSegment(
        page_tag=None,
        body=body,
        source_body=_cp852_stream(raw_body),
        raw_payload=raw_body,
    )
    visible_lines = _segment_visible_lines(segment)
    if not visible_lines:
        return None
    title_compact = _compact_text(title)
    if visible_lines and _compact_text(visible_lines[0]).startswith(title_compact[: min(5, len(title_compact))]):
        visible_lines = visible_lines[1:]

    content_lines = _topic_lines(
        record,
        segment,
        visible_lines,
        title,
    )
    raw_lines = [line.encode("cp852", errors="replace") for line in content_lines]
    return TopicRecord(
        context_id=context_id,
        raw_lines=raw_lines,
        index_terms=[title.encode("cp852", errors="replace")],
        alias_strings=[record.name, alias],
        names=[title],
        uhf_content=list(content_lines),
    )


def _build_program_contents(
    alias_lookup: dict[str, int],
    menu_entries: list[_ScorpionMenuEntry] | None = None,
) -> list[ContentNode]:
    if menu_entries is None:
        menu_entries = [
            _ScorpionMenuEntry(label=label, alias=alias, start=-1, blob=b"", hint="")
            for label, alias in SCORPION_PROGRAM_MENU
        ]
    program_nodes: list[ContentNode] = []
    for entry in menu_entries:
        topic_id = alias_lookup.get(entry.alias) if entry.alias else None
        program_nodes.append(
            ContentNode(
                label=entry.label,
                topic_id=topic_id,
                alias=entry.alias if entry.alias and topic_id is not None else None,
            )
        )
    return [ContentNode(label="Program", children=program_nodes)]


def _build_program_menu_lines(
    alias_lookup: dict[str, int],
    menu_entries: list[_ScorpionMenuEntry] | None = None,
) -> list[str]:
    if menu_entries is None:
        menu_entries = [
            _ScorpionMenuEntry(label=label, alias=alias, start=-1, blob=b"", hint="")
            for label, alias in SCORPION_PROGRAM_MENU
        ]
    lines = ["Seznam položek", "", "Programové menu", ""]
    for entry in menu_entries:
        if entry.alias and entry.alias in alias_lookup:
            lines.append(f"- {format_uhf_link(entry.label, alias=entry.alias)}")
        else:
            lines.append(f"- {entry.label}")
    return lines


def _preferred_topic_alias(topic: TopicRecord) -> str | None:
    for alias in topic.alias_strings:
        cleaned = alias.strip()
        if not cleaned:
            continue
        if cleaned == cleaned.lower() and any(char.isalpha() for char in cleaned):
            continue
        normalized = _normalize_tag(cleaned)
        if normalized:
            return normalized
    for alias in topic.alias_strings:
        cleaned = alias.strip()
        if cleaned:
            return cleaned
    return None


def _build_external_scorpion_section(base_dir: Path, filename: str, label: str) -> ContentNode | None:
    source_path = base_dir / filename
    if not source_path.exists():
        return None

    try:
        document = ScorpionDatReader(str(source_path)).read_bytes(source_path.read_bytes())
    except Exception:
        return None

    main_topic = next((topic for topic in document.topics if topic.is_main_index), None)
    children: list[ContentNode] = []
    for topic in document.topics:
        if topic.is_main_index and len(document.topics) > 1:
            continue
        title = next((name.strip() for name in topic.names if name.strip()), f"Topic {topic.context_id}")
        alias = _preferred_topic_alias(topic)
        children.append(
            ContentNode(
                label=title,
                source_file=source_path.name,
                alias=alias,
                topic_id=topic.context_id if not alias else None,
            )
        )

    if not children:
        return None

    section = ContentNode(label=label, children=children)
    if main_topic is not None:
        alias = _preferred_topic_alias(main_topic)
        section.source_file = source_path.name
        section.alias = alias
        if alias is None:
            section.topic_id = main_topic.context_id
    return section


def _build_program_library_contents(
    alias_lookup: dict[str, int],
    source_path: Path,
    menu_entries: list[_ScorpionMenuEntry] | None = None,
) -> list[ContentNode]:
    contents = _build_program_contents(alias_lookup, menu_entries)
    for filename, label in SCORPION_LIBRARY_SECTIONS:
        section = _build_external_scorpion_section(source_path.parent, filename, label)
        if section is not None:
            contents.append(section)
    return contents


class ScorpionDatReader(HelpReaderBase):
    """Parse one Scorpion DAT file into a minimal topic/index document."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_scorpion_dat_binary(data):
            raise ValueError("Not a Scorpion DAT file.")

        records = _parse_records(data)
        if not records:
            raise ValueError("Scorpion DAT file contains no readable records.")

        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []

        context_id = 0
        for record in records:
            if RESOURCE_RECORD_RE.match(record.name):
                continue
            segments = _split_segments(record)
            emitted_for_record = False

            for segment in segments:
                visible_lines = _segment_visible_lines(segment)
                if not _is_textual_record(record, segments, visible_lines):
                    continue

                title = _guess_segment_title(record, segment, visible_lines)
                content_lines = _topic_lines(record, segment, visible_lines, title)
                raw_lines = [line.encode("cp852", errors="replace") for line in content_lines]
                aliases = [record.name]
                if segment.page_tag:
                    aliases.append(segment.page_tag)

                topics.append(
                    TopicRecord(
                        context_id=context_id,
                        raw_lines=raw_lines,
                        index_terms=[title.encode("cp852", errors="replace")],
                        alias_strings=aliases,
                        names=[title],
                        uhf_content=list(content_lines),
                    )
                )
                index_entries.append(
                    IndexEntry(
                        label=title.encode("cp852", errors="replace"),
                        context_id=context_id,
                    )
                )
                context_id += 1
                emitted_for_record = True

            if not emitted_for_record and not RESOURCE_RECORD_RE.match(record.name):
                visible_lines = _segment_visible_lines(_ScorpionSegment(page_tag=record.page_tag, body=_ascii_stream(record.payload)))
                if not visible_lines:
                    continue
                segment = _ScorpionSegment(page_tag=record.page_tag, body=_ascii_stream(record.payload))
                title = _guess_segment_title(record, segment, visible_lines)
                content_lines = _topic_lines(record, segment, visible_lines, title)
                raw_lines = [line.encode("cp852", errors="replace") for line in content_lines]
                aliases = [record.name]
                if record.page_tag:
                    aliases.append(record.page_tag)
                topics.append(
                    TopicRecord(
                        context_id=context_id,
                        raw_lines=raw_lines,
                        index_terms=[title.encode("cp852", errors="replace")],
                        alias_strings=aliases,
                        names=[title],
                        uhf_content=list(content_lines),
                    )
                )
                index_entries.append(
                    IndexEntry(
                        label=title.encode("cp852", errors="replace"),
                        context_id=context_id,
                    )
                )
                context_id += 1

        source_path = Path(self.source_name)
        program_menu_entries: list[_ScorpionMenuEntry] = []
        if source_path.stem.lower() == "program":
            records_by_name = {record.name: record for record in records}
            seznam_record = records_by_name.get("seznam")
            if seznam_record is not None:
                program_menu_entries = _extract_program_menu_entries(seznam_record)
            for record_name, title, alias, search_term in SCORPION_PROGRAM_SYNTHETIC_TOPICS:
                if any(alias in topic.alias_strings for topic in topics):
                    continue
                record = records_by_name.get(record_name)
                if record is None:
                    continue
                synthetic = _build_synthetic_program_topic(
                    record=record,
                    title=title,
                    alias=alias,
                    search_term=search_term,
                    context_id=context_id,
                )
                if synthetic is None:
                    continue
                topics.append(synthetic)
                index_entries.append(
                    IndexEntry(
                        label=title.encode("cp852", errors="replace"),
                        context_id=context_id,
                    )
                )
                context_id += 1

        alias_lookup = _build_alias_topic_lookup(topics)
        contents: list[ContentNode] = []

        if source_path.stem.lower() == "program":
            contents = _build_program_library_contents(alias_lookup, source_path, program_menu_entries)
            for topic in topics:
                if "seznam" in {alias.lower() for alias in topic.alias_strings}:
                    topic.is_main_index = True
                    topic.names = ["Seznam položek"]
                    topic.index_terms = [b"Seznam polozek"]
                    topic.uhf_content = _build_program_menu_lines(alias_lookup, program_menu_entries)
                    topic.raw_lines = [line.encode("cp852", errors="replace") for line in topic.uhf_content]
                    break
        else:
            for topic in topics:
                if any(alias.lower().startswith("seznam") for alias in topic.alias_strings):
                    topic.is_main_index = True
                    break

        metadata: dict[str, object] = {
            "title": _display_name_from_source(source_path),
            "description": _display_name_from_source(source_path),
            "text_encoding": "cp852",
            "source_family": "scorpion-dat",
            "experimental_decode": True,
            "record_count": len(records),
            "topic_count": len(topics),
            "record_names": [record.name for record in records],
        }
        if program_menu_entries:
            metadata["program_menu_hints"] = [
                {
                    "label": entry.label,
                    "hint": entry.hint,
                    "raw_hint": entry.raw_hint,
                }
                for entry in program_menu_entries
                if entry.hint or entry.raw_hint
            ]

        return HelpDocument(
            format_name="scorpion-dat",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            contents=contents,
            metadata=metadata,
            binary_data=data,
        )
