"""Version-specific readers for Scorpions Cheater 1.x binaries."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile

from ..base import ContentNode, HelpDocument, IndexEntry, TopicRecord, ensure_document_index
from ..codepages import decode_bytes
from ..uhf_markup import render_uhf_line
from .scorpion_legacy_reader import (
    SCORPION_LEGACY_PROFILES,
    SCORPION_LEGACY_TEXT_ENCODING,
    ScorpionLegacyArchiveMember,
    ScorpionLegacyProfile,
    ScorpionLegacyUnpackedMember,
    ScorpionRarSfxReaderBase,
    ScorpionVersionReaderBase,
    _build_archive_document,
    _build_preview_document,
    _embedded_rar_overlay,
    _extract_ascii_strings,
    _legacy_public_document_title,
    _legacy_raw_lines,
    _member_preview_lines,
    _normalize_v3_epsilon_controls,
    _parse_rar4_members,
    _self_contained_exe_wrapper,
)


V1_MAIN_TITLE = "SCORPIONS CHEATER V.1.00"
V1_SAMPLE_TOPIC_START = "QUARANTINE"
V1_CODE_TABLE_TOKEN_RE = re.compile(r"(?:^|\s)[A-Z]?\d{2,4}\s*-[A-Z0-9]{4,}(?=\s|$)")
V1_BODY_ROW_COLUMN_TOKEN_RE = re.compile(r"^[A-Z0-9][A-Z0-9'./&+-]*$")
V1_SPACED_TITLE_RUN_RE = re.compile(r"(?<!\S)(?:[\w+./&:-]\s+){1,}[\w+./&:-](?!\S)", re.UNICODE)
V1_SPACED_DECIMAL_RUN_RE = re.compile(r"(\d)\.\s+((?:\d(?:\s+\d)*)\b)")
V1_5_PLAUSIBLE_TITLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 !'()+./&:-]*$")
V1_5_RUNTIME_NOISE_MARKERS = ("copyright", "divide error", "outofrange")
# Raw v1.5 directory labels are stored as standalone human-readable strings in
# the repeated-title block. They are not stable IDs and sometimes differ from
# the topic-title rows in the corpus stream.
V1_5_DIRECTORY_TITLE_OVERRIDES = {
    "BATTLE ISLE I": "BATTLE ISLE",
    "BLACKSTONE": "BLACK STONE",
    "DARK SUN II": "DARK SUN 2 -WAKE OF THE RAVAGER",
    "DOOM I": "DOOM",
    "MR. PACFORD": "M R. PACFORD",
    "KYRANDIA II": "LEGEND OF KYRANDIA 2",
    "LEMMINGS I": "LEMMINGS",
    "MAGIC CARPET I": "MAGIC CARPET",
    "MORTAL KOMBAT I": "MORTAL KOMBAT",
    "OH NO! MORE LEMMINGS": "OH NO! MORE LEMMNIGS",
    "OMF": "ONE MUST FALL 2097",
    "POPULOUS I": "POPULOUS",
    "REBEL ASSAULT CD": "REBELT ASSAULT CD",
    "S.C. OUT": "S. C. OUT",
    "WOLF 3D": "WOLFENSTEIN 3D",
    "X-MAS LEMMINGS": "X-MAS LEMMNIGS DEMO",
    "HORROR ZOMBIES": "HORROR ZOMBIES FROM THE CRYPT",
}
V1_5_MAIN_TITLE = "SCORPIONS  CHEATER V1.50"
V1_5_PRINT_MENU_TITLE = "MENU PRO TISK"
V1_5_CONTROLS_TITLE = "Pro pohyb:"
V1_5_FOOTER_PREFIX = "Scorpions Cheater V1.5 -"


def _extract_pklite_members(source_name: str, data: bytes) -> tuple[str | None, list[ScorpionLegacyUnpackedMember]]:
    suffix = Path(source_name).suffix.lower() or ".bin"
    try:
        with tempfile.TemporaryDirectory(prefix="scorpion-pklite-") as tmp_dir:
            temp_root = Path(tmp_dir)
            input_path = temp_root / f"input{suffix}"
            input_path.write_bytes(data)
            result = subprocess.run(
                ["deark", "-od", str(temp_root), "-m", "pklite", str(input_path)],
                capture_output=True,
                text=True,
            )
            stdout = result.stdout or ""
            wrapper_name = None
            if "Format: PKLITE-compressed EXE" in stdout:
                wrapper_name = "dos-mz-pklite"
            elif "Format: PKLITE-compressed COM" in stdout:
                wrapper_name = "dos-com-pklite"
            if result.returncode != 0 or wrapper_name is None:
                return wrapper_name, []

            outputs = sorted(path for path in temp_root.iterdir() if path.is_file() and path.name.startswith("output."))
            if not outputs:
                return wrapper_name, []

            unpacked_members: list[ScorpionLegacyUnpackedMember] = []
            single_output = len(outputs) == 1
            for path in outputs:
                payload = path.read_bytes()
                display_name = f"{source_name} (unpacked)" if single_output else f"{source_name} / {path.name}"
                unpacked_members.append(
                    ScorpionLegacyUnpackedMember(
                        output_name=path.name,
                        display_name=display_name,
                        payload=payload,
                    )
                )
            return wrapper_name, unpacked_members
    except FileNotFoundError:
        return None, []


def _decode_cstring_region(data: bytes, start: int, end: int) -> list[str]:
    strings: list[str] = []
    for raw in data[start:end].split(b"\x00"):
        if not raw.strip(b"\r\n\t "):
            continue
        text = decode_bytes(raw, SCORPION_LEGACY_TEXT_ENCODING)
        text = text.replace("\n\r", "\n").replace("\r\n", "\n").replace("\r", "\n").strip()
        if text:
            strings.append(text)
    return strings


def _find_prefixed_entry(strings: list[str], prefix: str) -> int | None:
    prefix_lower = prefix.lower()
    for index, entry in enumerate(strings):
        if entry.lower().startswith(prefix_lower):
            return index
    return None


def _find_exact_entry(strings: list[str], target: str, *, start: int = 0) -> int | None:
    target_lower = target.lower()
    for index in range(start, len(strings)):
        if strings[index].strip().lower() == target_lower:
            return index
    return None


def _is_v1_5_placeholder_entry(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    alpha_count = sum(char.isalpha() for char in stripped)
    if "%" in stripped and alpha_count < 6:
        return True
    reduced = stripped.replace("%s", "").replace("%c", "")
    reduced = reduced.replace("\n", "").replace("\r", "").strip(" [](),.&-\t")
    return not reduced


def _normalize_v1_5_section_entries(entries: list[str]) -> list[str]:
    normalized: list[str] = []
    pending_blank = False
    for entry in entries:
        if not entry.strip():
            if normalized:
                pending_blank = True
            continue
        if _is_v1_5_placeholder_entry(entry):
            continue
        for raw_line in entry.split("\n"):
            line = raw_line.strip()
            if not line:
                if normalized:
                    pending_blank = True
                continue
            if _is_v1_5_placeholder_entry(line):
                continue
            if pending_blank and normalized and normalized[-1] != "":
                normalized.append("")
            pending_blank = False
            if normalized and normalized[-1] == line:
                continue
            normalized.append(line)
    while normalized and normalized[-1] == "":
        normalized.pop()
    return normalized


def _is_v1_topic_title(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped[0].isdigit() or stripped.startswith("%") or ":" in stripped:
        return False
    # Compact code-table rows like "B113 -AIDCJF ... E416 -EIABDC ..." belong
    # to the previous topic body, not to the topic-title stream.
    if len(V1_CODE_TABLE_TOKEN_RE.findall(stripped)) >= 2:
        return False
    chunks = [chunk.strip() for chunk in re.split(r"\s{2,}", stripped) if chunk.strip()]
    # Uppercase tables such as "MOIST     RUBIA ..." or rows like
    # "P-BREAKSPACE-CHECK   =" also belong to the current topic body.
    if len(chunks) >= 4 and all(" " not in chunk and V1_BODY_ROW_COLUMN_TOKEN_RE.fullmatch(chunk) for chunk in chunks):
        return False
    if len(chunks) >= 2 and " " not in chunks[0] and any(chunk.startswith(("=", "-")) for chunk in chunks[1:]):
        return False
    if any(char.islower() for char in stripped):
        return False
    alpha_count = sum(char.isalpha() for char in stripped)
    if alpha_count < 4:
        return False
    return all(
        (not char.isalpha()) or char.upper() == char
        for char in stripped
    )


def _normalize_v1_title(text: str) -> str:
    text = re.sub(r"(?<=\w)([:;])", r" \1", text)
    chunks = [
        V1_SPACED_TITLE_RUN_RE.sub(lambda match: re.sub(r"\s+", "", match.group(0)), chunk.strip())
        for chunk in re.split(r"\s{2,}", text)
        if chunk.strip()
    ]
    title = " ".join(chunks)
    title = V1_SPACED_DECIMAL_RUN_RE.sub(
        lambda match: f"{match.group(1)}.{re.sub(r'\s+', '', match.group(2))}",
        title,
    )
    title = re.sub(r"\s+([:;,.!?])", r"\1", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()


def _v1_directory_title_key(text: str) -> str:
    return _canonicalize_v1_5_title(_normalize_v1_title(text))


def _parse_v1_directory_title(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    normalized = _normalize_v3_epsilon_controls(stripped)
    if not V1_5_PLAUSIBLE_TITLE_RE.fullmatch(normalized):
        return None
    if sum(char.isalpha() for char in normalized) < 2:
        return None
    return _normalize_v1_title(normalized)


def _v1_directory_title_matches(candidate_title: str, directory_title_keys: set[str]) -> bool:
    candidate_key = _v1_directory_title_key(candidate_title)
    if candidate_key in directory_title_keys:
        return True
    for key in directory_title_keys:
        if not candidate_key.startswith(key):
            continue
        suffix = candidate_key[len(key) :]
        if suffix and suffix[0] in " :;(":
            return True
    return False


def _extract_v1_directory_title_keys(strings: list[str], *, repeat_index: int) -> set[str]:
    start_index = repeat_index
    while start_index > 0 and _parse_v1_directory_title(strings[start_index - 1]) is not None:
        start_index -= 1

    keys: set[str] = set()
    for entry in strings[start_index:]:
        title = _parse_v1_directory_title(entry)
        if title is None:
            if keys:
                break
            continue
        keys.add(_v1_directory_title_key(title))
        override = V1_5_DIRECTORY_TITLE_OVERRIDES.get(title)
        if override:
            keys.add(_v1_directory_title_key(override))
    return keys


def _find_v1_directory_start_index(strings: list[str], *, repeat_index: int) -> int:
    start_index = repeat_index
    while start_index > 0 and _parse_v1_directory_title(strings[start_index - 1]) is not None:
        start_index -= 1
    return start_index


def _find_v1_content_stop_index(strings: list[str], *, directory_start_index: int) -> int:
    for index in range(max(0, directory_start_index - 32), directory_start_index):
        entry = strings[index].strip()
        if not entry:
            continue
        box_count = sum(char in "┌┐└┘├┤┬┴┼─│■≡" for char in entry)
        if box_count >= 4:
            return index
    return directory_start_index


def _find_v1_repeat_title_index(strings: list[str], *, start_index: int) -> int | None:
    if start_index >= len(strings):
        return None
    start_title = _normalize_v1_title(strings[start_index])
    if not start_title:
        return None
    for index in range(start_index + 1, len(strings)):
        if _normalize_v1_title(strings[index]) == start_title:
            return index
    return None


def _build_v1_topic_stream(strings: list[str], *, start_index: int) -> list[tuple[str, list[str]]]:
    repeat_index = _find_v1_repeat_title_index(strings, start_index=start_index)
    directory_title_keys = None
    stop_index = None
    if repeat_index is not None:
        extracted_directory_title_keys = _extract_v1_directory_title_keys(strings, repeat_index=repeat_index)
        if len(extracted_directory_title_keys) >= 8:
            directory_title_keys = extracted_directory_title_keys
            directory_start_index = _find_v1_directory_start_index(strings, repeat_index=repeat_index)
            stop_index = _find_v1_content_stop_index(strings, directory_start_index=directory_start_index)
    topics, _stop_index = _scan_v1_topic_stream(
        strings,
        start_index=start_index,
        directory_title_keys=directory_title_keys,
        stop_index=stop_index,
    )
    return topics


def _scan_v1_topic_stream(
    strings: list[str],
    *,
    start_index: int,
    directory_title_keys: set[str] | None = None,
    stop_index: int | None = None,
) -> tuple[list[tuple[str, list[str]]], int]:
    topics: list[tuple[str, list[str]]] = []
    seen_titles: set[str] = set()
    current_title: str | None = None
    current_lines: list[str] = []
    effective_stop_index = stop_index if stop_index is not None else len(strings)
    in_colon_list = False

    for index, entry in enumerate(strings[start_index:effective_stop_index], start_index):
        normalized_title = _normalize_v1_title(entry.strip())
        is_directory_backed_title = (
            directory_title_keys is not None
            and bool(normalized_title)
            and _v1_directory_title_matches(normalized_title, directory_title_keys)
            and not any(char.islower() for char in entry)
        )
        if _is_v1_topic_title(entry) or is_directory_backed_title:
            if (
                current_title is not None
                and in_colon_list
                and directory_title_keys is not None
                and not _v1_directory_title_matches(normalized_title, directory_title_keys)
            ):
                current_lines.append(entry)
                continue
            if current_title is not None:
                normalized_lines = _normalize_v1_5_section_entries(current_lines)
                if normalized_lines:
                    topics.append((current_title, normalized_lines))
                    seen_titles.add(current_title)
            if normalized_title in seen_titles:
                effective_stop_index = index
                current_title = None
                current_lines = []
                break
            current_title = normalized_title
            current_lines = []
            in_colon_list = False
            continue
        if current_title is not None:
            current_lines.append(entry)
            if entry.strip().endswith(":"):
                in_colon_list = True

    if current_title is not None and current_title not in seen_titles:
        normalized_lines = _normalize_v1_5_section_entries(current_lines)
        if normalized_lines:
            topics.append((current_title, normalized_lines))
    return topics, effective_stop_index


def _build_v1_sample_topics(strings: list[str]) -> list[tuple[str, list[str]]]:
    start_index = _find_exact_entry(strings, V1_SAMPLE_TOPIC_START)
    if start_index is None:
        return []
    return _build_v1_topic_stream(strings, start_index=start_index)


def _find_v1_5_topic_start(strings: list[str], *, stop_index: int) -> int | None:
    corpus_strings = strings[:stop_index]
    for start_index, entry in enumerate(corpus_strings):
        if not _is_v1_topic_title(entry):
            continue
        topics, _repeat_index = _scan_v1_topic_stream(corpus_strings, start_index=start_index)
        if len(topics) < 3:
            continue
        first_titles = [title for title, _lines in topics[:3]]
        if len(first_titles) < 3 or not all(V1_5_PLAUSIBLE_TITLE_RE.fullmatch(title) for title in first_titles):
            continue
        first_lines = [line.lower() for line in topics[0][1][:3]]
        if any(marker in line for line in first_lines for marker in V1_5_RUNTIME_NOISE_MARKERS):
            continue
        return start_index
    return None


def _parse_v1_5_directory_entry(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    if not stripped:
        return None
    status = "plain"
    title = stripped
    if stripped.startswith(("Ř ", "ⁿ ")):
        status = "new"
        title = stripped[2:].strip()
    elif stripped.startswith("! "):
        status = "renovated"
        title = stripped[2:].strip()
    if not title:
        return None
    if not V1_5_PLAUSIBLE_TITLE_RE.fullmatch(title):
        return None
    if title in {V1_5_MAIN_TITLE, V1_5_PRINT_MENU_TITLE, "S C O R P I O N S"}:
        return None
    return status, title


def _extract_v1_5_directory_entries(strings: list[str], *, repeat_index: int, stop_index: int) -> list[dict[str, str]]:
    start_index = repeat_index
    while start_index > 0 and _parse_v1_5_directory_entry(strings[start_index - 1]) is not None:
        start_index -= 1

    entries: list[dict[str, str]] = []
    for entry in strings[start_index:stop_index]:
        parsed = _parse_v1_5_directory_entry(entry)
        if parsed is None:
            if entries:
                break
            continue
        status, title = parsed
        entries.append({"status": status, "title": title, "raw": entry.strip()})
    return entries


def _find_v1_5_directory_start_index(strings: list[str], *, repeat_index: int) -> int:
    start_index = repeat_index
    while start_index > 0 and _parse_v1_5_directory_entry(strings[start_index - 1]) is not None:
        start_index -= 1
    return start_index


def _find_v1_5_content_stop_index(strings: list[str], *, directory_start_index: int) -> int:
    for index in range(max(0, directory_start_index - 32), directory_start_index):
        entry = strings[index].strip()
        if not entry:
            continue
        box_count = sum(char in "┌┐└┘├┤┬┴┼─│■╔╗╚╝╦╩╠╣═║≡" for char in entry)
        if box_count >= 4:
            return index
    return directory_start_index


def _canonicalize_v1_5_title(text: str) -> str:
    text = text.strip().upper()
    text = re.sub(r"\(ARCADE\)", "", text)
    text = re.sub(r"\bTHE\b", "", text)
    text = re.sub(r"\bCD\b", "", text)
    text = re.sub(r"\bVERSION\b", "", text)
    text = re.sub(r"\bSHAREWARE\b", "", text)
    roman_map = {
        "VII": "7",
        "VI": "6",
        "IV": "4",
        "III": "3",
        "II": "2",
        "I": "1",
    }
    tokens = [roman_map.get(token, token) for token in re.split(r"\s+", text) if token]
    text = " ".join(tokens)
    text = text.replace("'", "")
    text = text.replace(".", "")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _resolve_v1_5_directory_title(title: str, topic_titles: set[str]) -> str | None:
    if title in topic_titles:
        return title
    override = V1_5_DIRECTORY_TITLE_OVERRIDES.get(title)
    if override in topic_titles:
        return override

    canonical_lookup: dict[str, list[str]] = {}
    for topic_title in topic_titles:
        canonical_lookup.setdefault(_canonicalize_v1_5_title(topic_title), []).append(topic_title)
    hits = canonical_lookup.get(_canonicalize_v1_5_title(title), [])
    if len(hits) == 1:
        return hits[0]
    return None


def _resolve_v1_5_directory_entries(
    directory_entries: list[dict[str, str]],
    topic_titles: set[str],
) -> tuple[dict[str, list[str]], list[str], int]:
    aliases_by_title: dict[str, list[str]] = {}
    unresolved_titles: list[str] = []
    resolved_count = 0

    for entry in directory_entries:
        resolved_title = _resolve_v1_5_directory_title(entry["title"], topic_titles)
        if resolved_title is None:
            unresolved_titles.append(entry["title"])
            continue
        entry["resolved_title"] = resolved_title
        resolved_count += 1
        if entry["title"] != resolved_title:
            aliases_by_title.setdefault(resolved_title, []).append(entry["title"])

    return aliases_by_title, unresolved_titles, resolved_count


def _build_structured_topic(context_id: int, title: str, alias: str, lines: list[str]) -> TopicRecord:
    return TopicRecord(
        context_id=context_id,
        raw_lines=_legacy_raw_lines(lines),
        index_terms=[title.encode("latin-1", errors="replace")],
        alias_strings=[alias],
        names=[title],
        uhf_content=[render_uhf_line(line) for line in lines],
    )


def _topic_content_node(topic: TopicRecord) -> ContentNode:
    return ContentNode(
        label=topic.names[0] if topic.names else str(topic.context_id),
        topic_id=topic.context_id,
    )


def _build_legacy_topic_contents(
    title: str,
    topics: list[TopicRecord],
    *,
    grouped_start_index: int,
    grouped_label: str = "Cheaty",
) -> list[ContentNode]:
    children = [_topic_content_node(topic) for topic in topics[1:grouped_start_index]]
    if grouped_start_index < len(topics):
        children.append(
            ContentNode(
                label=grouped_label,
                children=[_topic_content_node(topic) for topic in topics[grouped_start_index:]],
            )
        )
    return [ContentNode(label=title, topic_id=0, children=children)]


def _split_v1_5_author_names(text: str) -> list[str]:
    authors: list[str] = []
    for part in re.split(r"\s+&\s+", text):
        cleaned = re.sub(r"\s+", " ", part).strip(" -")
        if cleaned:
            authors.append(cleaned)
    return authors


def _extract_v1_5_authors(lines: list[str]) -> list[str]:
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith(V1_5_FOOTER_PREFIX):
            continue
        return _split_v1_5_author_names(stripped[len(V1_5_FOOTER_PREFIX) :])
    return []


def _build_v1_main_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    overlay_offset: int,
    overlay: bytes,
    members: list[ScorpionLegacyArchiveMember],
) -> HelpDocument | None:
    from . import scorpion_legacy_reader as legacy_reader

    extracted_members = legacy_reader._extract_overlay_members(overlay)
    menu_payload = extracted_members.get("MENU2.EXE")
    if menu_payload is None:
        return None

    strings = _decode_cstring_region(menu_payload, 0, len(menu_payload))
    title_index = _find_prefixed_entry(strings, V1_MAIN_TITLE)
    controls_index = _find_prefixed_entry(strings, V1_5_CONTROLS_TITLE)
    if title_index is None or controls_index is None or controls_index <= title_index:
        return None

    controls_end = len(strings)
    for index in range(controls_index + 1, len(strings)):
        entry = strings[index]
        if entry.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") or _is_v1_5_placeholder_entry(entry):
            controls_end = index
            break

    intro_lines = _normalize_v1_5_section_entries(strings[title_index:controls_index])
    controls_lines = _normalize_v1_5_section_entries(strings[controls_index:controls_end])
    sample_topics = _build_v1_sample_topics(strings)
    if not intro_lines or not controls_lines:
        return None

    title = _legacy_public_document_title(profile, source_name)
    overview_lines = [
        title,
        "",
        f"Decoder: {profile.decoder_name}",
        f"Family: {profile.family}",
        f"File: {source_name}",
        f"Size: {len(data)} bytes",
        "Wrapper: DOS MZ SFX with embedded RAR overlay",
        f"Overlay offset: {overlay_offset}",
        f"Overlay size: {len(overlay)} bytes",
        f"Contained files: {len(members)}",
        f"Parsed from: MENU2.EXE ({len(menu_payload)} bytes)",
        "",
        "Parsed sections:",
        "O programu",
        "Ovládání",
    ]
    overview_lines.extend(topic_title for topic_title, _topic_lines in sample_topics)

    topics = [
        TopicRecord(
            context_id=0,
            raw_lines=_legacy_raw_lines(overview_lines),
            index_terms=[title.encode("latin-1", errors="replace")],
            alias_strings=[profile.version, profile.family, source_name, "parsed-overview"],
            is_help_contents=True,
            names=[title],
            uhf_content=[render_uhf_line(line) for line in overview_lines],
        ),
        _build_structured_topic(1, "O programu", "o-programu", intro_lines),
        _build_structured_topic(2, "Ovládání", "ovladani", controls_lines),
    ]
    index_entries = [
        IndexEntry(label=title.encode("latin-1", errors="replace"), context_id=0),
        IndexEntry(label=b"O programu", context_id=1),
        IndexEntry(label=b"Ovladani", context_id=2),
    ]

    context_id = 3
    for topic_title, topic_lines in sample_topics:
        topics.append(_build_structured_topic(context_id, topic_title, f"v1-sample-{context_id}", topic_lines))
        index_entries.append(IndexEntry(label=topic_title.encode("latin-1", errors="replace"), context_id=context_id))
        context_id += 1

    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        contents=_build_legacy_topic_contents(title, topics, grouped_start_index=3),
        metadata={
            "title": title,
            "description": title,
            "text_encoding": SCORPION_LEGACY_TEXT_ENCODING,
            "help_contents_topic_id": 0,
            "source_family": "scorpion-legacy",
            "scorpion_version": profile.version,
            "scorpion_decoder": profile.decoder_name,
            "scorpion_family": profile.family,
            "scorpion_versions_order": [item.version for item in SCORPION_LEGACY_PROFILES],
            "file_size": len(data),
            "header_hex": data[:32].hex(" "),
            "ascii_preview": _extract_ascii_strings(data),
            "scorpion_wrapper": "dos-mz-sfx-rar",
            "scorpion_parser": "v1-menu2-string-table",
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
            "parsed_member": "MENU2.EXE",
            "parsed_sample_topic_count": len(sample_topics),
        },
        binary_data=data,
    )
    return ensure_document_index(document)


def _build_v1_5_main_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    wrapper_name: str,
    members: list[ScorpionLegacyUnpackedMember],
) -> HelpDocument | None:
    if source_name.lower() != "cheater.exe":
        return None

    main_member = next((member for member in members if member.output_name.lower().endswith(".exe")), None)
    if main_member is None:
        return None

    payload = main_member.payload
    strings = _decode_cstring_region(payload, 0, len(payload))

    title_index = _find_prefixed_entry(strings, V1_5_MAIN_TITLE)
    print_menu_index = _find_prefixed_entry(strings, V1_5_PRINT_MENU_TITLE)
    controls_index = _find_prefixed_entry(strings, V1_5_CONTROLS_TITLE)
    footer_index = _find_prefixed_entry(strings, V1_5_FOOTER_PREFIX)
    if title_index is None or print_menu_index is None or controls_index is None or footer_index is None:
        return None

    intro_start = title_index
    if title_index > 0 and strings[title_index - 1].startswith("---- stiskni cokoli"):
        intro_start = title_index - 1

    sample_topics: list[tuple[str, list[str]]] = []
    directory_entries: list[dict[str, str]] = []
    topic_start_index = _find_v1_5_topic_start(strings, stop_index=title_index)
    if topic_start_index is not None:
        sample_topics, repeat_index = _scan_v1_topic_stream(strings[:title_index], start_index=topic_start_index)
        if repeat_index < title_index:
            directory_start_index = _find_v1_5_directory_start_index(strings, repeat_index=repeat_index)
            topic_stop_index = _find_v1_5_content_stop_index(
                strings,
                directory_start_index=directory_start_index,
            )
            sample_topics, _repeat_index = _scan_v1_topic_stream(
                strings[:title_index],
                start_index=topic_start_index,
                stop_index=topic_stop_index,
            )
            directory_entries = _extract_v1_5_directory_entries(
                strings,
                repeat_index=directory_start_index,
                stop_index=title_index,
            )

    intro_lines = _normalize_v1_5_section_entries(strings[intro_start:print_menu_index])
    print_menu_lines = _normalize_v1_5_section_entries(strings[print_menu_index:controls_index])
    controls_lines = _normalize_v1_5_section_entries(strings[controls_index : footer_index + 1])
    if not intro_lines or not print_menu_lines or not controls_lines:
        return None
    authors = _extract_v1_5_authors(controls_lines)

    title = _legacy_public_document_title(profile, source_name)
    overview_lines = [
        title,
        "",
        f"Decoder: {profile.decoder_name}",
        f"Family: {profile.family}",
        f"File: {source_name}",
        f"Size: {len(data)} bytes",
        f"Wrapper: {wrapper_name}",
        f"Parsed from: {main_member.output_name} ({len(main_member.payload)} bytes)",
        "",
        "Parsed sections:",
        "O programu",
        "Menu pro tisk",
        "Ovládání",
    ]
    if directory_entries:
        overview_lines.append("Seznam her")
    if sample_topics:
        overview_lines.append(f"Cheat topics: {len(sample_topics)}")

    directory_lines: list[str] = []
    if directory_entries:
        status_counts = {status: sum(1 for entry in directory_entries if entry["status"] == status) for status in {"new", "renovated", "plain"}}
        directory_lines = [
            f"Nové položky: {status_counts['new']}",
            f"Zrenovované položky: {status_counts['renovated']}",
            f"Ostatní položky: {status_counts['plain']}",
            "",
        ]
        directory_lines.extend(entry["raw"] for entry in directory_entries)

    topics = [
        TopicRecord(
            context_id=0,
            raw_lines=_legacy_raw_lines(overview_lines),
            index_terms=[title.encode("latin-1", errors="replace")],
            alias_strings=[profile.version, profile.family, source_name, "parsed-overview"],
            is_help_contents=True,
            names=[title],
            uhf_content=[render_uhf_line(line) for line in overview_lines],
        ),
        _build_structured_topic(1, "O programu", "o-programu", intro_lines),
        _build_structured_topic(2, "Menu pro tisk", "menu-pro-tisk", print_menu_lines),
        _build_structured_topic(3, "Ovládání", "ovladani", controls_lines),
    ]
    index_entries = [
        IndexEntry(label=title.encode("latin-1", errors="replace"), context_id=0),
        IndexEntry(label=b"O programu", context_id=1),
        IndexEntry(label=b"Menu pro tisk", context_id=2),
        IndexEntry(label=b"Ovladani", context_id=3),
    ]
    context_id = 4
    if directory_lines:
        topics.append(_build_structured_topic(context_id, "Seznam her", "seznam-her", directory_lines))
        index_entries.append(IndexEntry(label=b"Seznam her", context_id=context_id))
        context_id += 1
    cheat_topic_start_index = len(topics)

    topic_aliases_by_title: dict[str, list[str]] = {}
    unresolved_directory_titles: list[str] = []
    resolved_directory_count = 0
    if sample_topics and directory_entries:
        topic_aliases_by_title, unresolved_directory_titles, resolved_directory_count = _resolve_v1_5_directory_entries(
            directory_entries,
            {topic_title for topic_title, _topic_lines in sample_topics},
        )

    for topic_title, topic_lines in sample_topics:
        topic_record = _build_structured_topic(context_id, topic_title, f"v1_5-sample-{context_id}", topic_lines)
        for alias_title in topic_aliases_by_title.get(topic_title, []):
            if alias_title not in topic_record.alias_strings:
                topic_record.alias_strings.append(alias_title)
        topics.append(topic_record)
        index_entries.append(IndexEntry(label=topic_title.encode("latin-1", errors="replace"), context_id=context_id))
        context_id += 1

    context_by_title = {topic.names[0]: topic.context_id for topic in topics if topic.names}
    for entry in directory_entries:
        resolved_title = entry.get("resolved_title")
        if isinstance(resolved_title, str) and resolved_title in context_by_title:
            entry["resolved_context_id"] = context_by_title[resolved_title]

    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        metadata={
            "title": title,
            "description": title,
            "text_encoding": SCORPION_LEGACY_TEXT_ENCODING,
            "help_contents_topic_id": 0,
            "source_family": "scorpion-legacy",
            "scorpion_version": profile.version,
            "scorpion_decoder": profile.decoder_name,
            "scorpion_family": profile.family,
            "scorpion_versions_order": [item.version for item in SCORPION_LEGACY_PROFILES],
            "file_size": len(data),
            "header_hex": data[:32].hex(" "),
            "ascii_preview": _extract_ascii_strings(data),
            "scorpion_wrapper": wrapper_name,
            "scorpion_parser": "v1.5-embedded-string-table",
            "unpacked_member_count": len(members),
            "parsed_sample_topic_count": len(sample_topics),
            "v1_5_directory_count": len(directory_entries),
            "v1_5_directory_resolved_count": resolved_directory_count,
            "v1_5_directory_unresolved_titles": unresolved_directory_titles,
            "v1_5_directory_counts": {
                "new": sum(1 for entry in directory_entries if entry["status"] == "new"),
                "renovated": sum(1 for entry in directory_entries if entry["status"] == "renovated"),
                "plain": sum(1 for entry in directory_entries if entry["status"] == "plain"),
            },
            "v1_5_directory_entries": directory_entries,
            "unpacked_members": [
                {
                    "name": member.display_name,
                    "output_name": member.output_name,
                    "size": len(member.payload),
                }
                for member in members
            ],
            "v1_5_string_table_window": {
                "start": 0,
                "end": len(payload),
                "source_output": main_member.output_name,
            },
        },
        binary_data=data,
    )
    document.contents = _build_legacy_topic_contents(
        title,
        topics,
        grouped_start_index=cheat_topic_start_index,
    )
    if authors:
        document.metadata["credit_lines"] = ["; ".join(authors)]
        document.metadata["scorpion_authors"] = authors
    return ensure_document_index(document)


def _build_unpacked_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    wrapper_name: str,
    members: list[ScorpionLegacyUnpackedMember],
) -> HelpDocument:
    title = _legacy_public_document_title(profile, source_name)
    overview_lines = [
        title,
        "",
        f"Decoder: {profile.decoder_name}",
        f"Family: {profile.family}",
        f"File: {source_name}",
        f"Size: {len(data)} bytes",
        f"Wrapper: {wrapper_name}",
        f"Decompressed files: {len(members)}",
        "",
        "Unpacked outputs:",
    ]
    overview_lines.extend(f"{member.display_name} ({len(member.payload)} B)" for member in members)

    topics = [
        TopicRecord(
            context_id=0,
            raw_lines=_legacy_raw_lines(overview_lines),
            index_terms=[title.encode("latin-1", errors="replace")],
            alias_strings=[profile.version, profile.family, source_name, "unpacked-overview"],
            names=[title],
            uhf_content=[render_uhf_line(line) for line in overview_lines],
        )
    ]
    index_entries = [IndexEntry(label=title.encode("latin-1", errors="replace"), context_id=0)]

    for context_id, member in enumerate(members, start=1):
        member_lines = [
            member.display_name,
            "",
            f"Wrapper file: {source_name}",
            f"Generated file: {member.output_name}",
            f"Unpacked size: {len(member.payload)} bytes",
            "",
            "Preview:",
        ]
        member_lines.extend(_member_preview_lines(member.payload))
        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=_legacy_raw_lines(member_lines),
                index_terms=[member.display_name.encode("latin-1", errors="replace")],
                alias_strings=[member.display_name, member.output_name, profile.version, source_name],
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
            "scorpion_wrapper": wrapper_name,
            "unpacked_member_count": len(members),
            "unpacked_members": [
                {
                    "name": member.display_name,
                    "output_name": member.output_name,
                    "size": len(member.payload),
                }
                for member in members
            ],
        },
        binary_data=data,
    )
    return ensure_document_index(document)


class ScorpionV1Reader(ScorpionRarSfxReaderBase):
    def read_bytes(self, data: bytes):
        overlay_info = _embedded_rar_overlay(data)
        if overlay_info is not None:
            overlay_offset, overlay = overlay_info
            members = _parse_rar4_members(overlay)
            if members:
                structured_document = _build_v1_main_document(
                    self.profile,
                    self.source_path.name,
                    data,
                    overlay_offset,
                    overlay,
                    members,
                )
                if structured_document is not None:
                    return self._finalize_document(structured_document)
                return self._finalize_document(
                    _build_archive_document(self.profile, self.source_path.name, data, overlay_offset, overlay, members)
                )
        return self._finalize_document(_build_preview_document(self.profile, self.source_path.name, data))


class ScorpionV1_5Reader(ScorpionVersionReaderBase):
    def read_bytes(self, data: bytes):
        wrapper_name = _self_contained_exe_wrapper(data)
        deark_wrapper_name, unpacked_members = _extract_pklite_members(self.source_path.name, data)
        if deark_wrapper_name is not None:
            wrapper_name = deark_wrapper_name
        if unpacked_members:
            structured_document = _build_v1_5_main_document(
                self.profile,
                self.source_path.name,
                data,
                wrapper_name or "pklite",
                unpacked_members,
            )
            if structured_document is not None:
                return self._finalize_document(structured_document)
            return self._finalize_document(
                _build_unpacked_document(
                    self.profile,
                    self.source_path.name,
                    data,
                    wrapper_name or "pklite",
                    unpacked_members,
                )
            )
        return self._finalize_document(
            _build_preview_document(self.profile, self.source_path.name, data, wrapper_name=wrapper_name)
        )
