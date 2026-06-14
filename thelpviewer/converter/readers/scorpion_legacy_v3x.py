"""Version-specific readers for Scorpions Cheater 3.x binaries."""

from __future__ import annotations

from pathlib import Path

from ..base import ContentNode, HelpDocument, IndexEntry, TopicRecord, ensure_document_index
from ..codepages import decode_bytes
from ..uhf_markup import render_uhf_line
from .scorpion_legacy_reader import (
    SCORPION_LEGACY_PROFILES,
    SCORPION_LEGACY_TEXT_ENCODING,
    V3_INDEX_ENTRY_RE,
    V3_TOPIC_MARKER_RE,
    ScorpionLegacyArchiveMember,
    ScorpionLegacyProfile,
    ScorpionRarSfxReaderBase,
    _build_archive_document,
    _build_preview_document,
    _embedded_rar_overlay,
    _encode_legacy_text,
    _extract_ascii_strings,
    _legacy_public_document_title,
    _legacy_raw_lines,
    _normalize_v3_title,
    _normalize_v3_topic_lines,
    _parse_rar4_members,
)


def _parse_v3_index_titles(payload: bytes) -> dict[str, str]:
    text = decode_bytes(payload, SCORPION_LEGACY_TEXT_ENCODING).replace("\r\n", "\n").replace("\r", "\n")
    titles: dict[str, str] = {}
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = V3_INDEX_ENTRY_RE.fullmatch(line)
        if match is None:
            continue
        label = _normalize_v3_title(match.group("label"))
        if label:
            titles.setdefault(match.group("marker"), label)
    return titles


def _parse_v3_index_order(payload: bytes) -> list[tuple[str, str]]:
    text = decode_bytes(payload, SCORPION_LEGACY_TEXT_ENCODING).replace("\r\n", "\n").replace("\r", "\n")
    entries: list[tuple[str, str]] = []
    seen_markers: set[str] = set()
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = V3_INDEX_ENTRY_RE.fullmatch(line)
        if match is None:
            continue
        marker = match.group("marker")
        if marker in seen_markers:
            continue
        label = _normalize_v3_title(match.group("label"))
        if not label:
            continue
        entries.append((marker, label))
        seen_markers.add(marker)
    return entries


def _v3_member_kind(name: str) -> str:
    normalized = Path(name.replace("\\", "/")).name.upper()
    if normalized.startswith("TEXTY.") or normalized.startswith("MULTI."):
        return "cheats"
    if normalized.startswith("NAVODY."):
        return "manuals"
    if normalized.startswith("VTIP"):
        return "jokes"
    if normalized == "SCC.SC":
        return "cheat-index"
    return "other"


def _v3_context_id(marker: str, fallback: int, *, section: str) -> int:
    if section == "cheats" and marker.isdigit():
        return int(marker)
    if marker.isdigit():
        base_value = int(marker)
    else:
        try:
            base_value = int(marker, 36)
        except ValueError:
            return fallback
    section_offsets = {
        "manuals": 0x100000,
        "jokes": 0x200000,
        "other": 0x300000,
        "cheat-index": 0x300000,
        "cheats": 0x400000,
    }
    try:
        return section_offsets[section] + base_value
    except KeyError:
        return fallback


def _parse_v3_member_topics(
    member_name: str,
    payload: bytes,
    *,
    title_overrides: dict[str, str],
) -> list[dict[str, object]]:
    text = decode_bytes(payload, SCORPION_LEGACY_TEXT_ENCODING).replace("\r\n", "\n").replace("\r", "\n")
    topics: list[dict[str, object]] = []
    current_marker: str | None = None
    current_lines: list[str] = []

    def flush_topic() -> None:
        nonlocal current_marker, current_lines
        if current_marker is None:
            return
        normalized_lines = _normalize_v3_topic_lines(current_lines)
        if normalized_lines:
            body_title = _normalize_v3_title(normalized_lines[0]) or current_marker
            title = title_overrides.get(current_marker, body_title)
            normalized_lines[0] = title
            topics.append(
                {
                    "marker": current_marker,
                    "title": title,
                    "member_name": member_name,
                    "lines": normalized_lines,
                }
            )
        current_marker = None
        current_lines = []

    for raw_line in text.split("\n"):
        stripped = raw_line.strip().rstrip("\x00")
        match = V3_TOPIC_MARKER_RE.fullmatch(stripped)
        if match is not None:
            flush_topic()
            current_marker = match.group(1)
            current_lines = []
            continue
        if current_marker is None:
            continue
        if stripped == "END":
            flush_topic()
            continue
        current_lines.append(raw_line.rstrip("\x00"))

    flush_topic()
    return topics


def _build_v3_archive_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
    overlay_offset: int,
    overlay: bytes,
    members: list[ScorpionLegacyArchiveMember],
) -> HelpDocument:
    from . import scorpion_legacy_reader as legacy_reader

    extracted_members = legacy_reader._extract_overlay_members(overlay) if members else {}
    cheat_title_overrides: dict[str, str] = {}
    cheat_ordered_markers: list[str] = []
    seen_cheat_markers: set[str] = set()
    for name, payload in extracted_members.items():
        if name.startswith("_/"):
            continue
        if _v3_member_kind(name) != "cheat-index":
            continue
        parsed_titles = _parse_v3_index_titles(payload)
        if parsed_titles:
            for marker, title in parsed_titles.items():
                cheat_title_overrides.setdefault(marker, title)
        for marker, _label in _parse_v3_index_order(payload):
            if marker in seen_cheat_markers:
                continue
            cheat_ordered_markers.append(marker)
            seen_cheat_markers.add(marker)

    parsed_topics: list[dict[str, object]] = []
    parsed_member_names: list[str] = []
    unparsed_member_names: list[str] = []
    seen_parsed_members: set[str] = set()

    for member in members:
        member_kind = _v3_member_kind(member.display_name)
        if member_kind == "cheat-index":
            continue
        member_payload = extracted_members.get(member.display_name) or extracted_members.get(member.raw_name)
        if member_payload is None:
            unparsed_member_names.append(member.display_name)
            continue
        member_topics = _parse_v3_member_topics(
            member.display_name,
            member_payload,
            title_overrides=cheat_title_overrides if member_kind == "cheats" else {},
        )
        if member_topics:
            for parsed_topic in member_topics:
                parsed_topic["section"] = member_kind
            parsed_topics.extend(member_topics)
            if member.display_name not in seen_parsed_members:
                parsed_member_names.append(member.display_name)
                seen_parsed_members.add(member.display_name)
            continue
        unparsed_member_names.append(member.display_name)

    if not parsed_topics:
        return _build_archive_document(profile, source_name, data, overlay_offset, overlay, members)

    section_topics: dict[str, list[dict[str, object]]] = {
        "manuals": [],
        "cheats": [],
        "jokes": [],
        "other": [],
    }
    for parsed_topic in parsed_topics:
        section = str(parsed_topic.get("section") or "other")
        section_topics.setdefault(section, []).append(parsed_topic)

    ordered_topics: list[dict[str, object]] = []
    used_topic_ids: set[int] = set()
    cheat_topics = section_topics.get("cheats", [])
    for marker in cheat_ordered_markers:
        for parsed_topic in cheat_topics:
            if str(parsed_topic["marker"]) != marker:
                continue
            marker_id = id(parsed_topic)
            if marker_id in used_topic_ids:
                continue
            ordered_topics.append(parsed_topic)
            used_topic_ids.add(marker_id)
            break

    for section_name in ("manuals", "cheats", "jokes", "other"):
        for parsed_topic in section_topics.get(section_name, []):
            if id(parsed_topic) in used_topic_ids:
                continue
            ordered_topics.append(parsed_topic)
            used_topic_ids.add(id(parsed_topic))

    title = _legacy_public_document_title(profile, source_name)
    topics: list[TopicRecord] = []
    index_entries: list[IndexEntry] = []
    contents_sections: dict[str, list[ContentNode]] = {
        "manuals": [],
        "cheats": [],
        "jokes": [],
        "other": [],
    }
    used_context_ids: set[int] = set()

    for fallback_context_id, parsed_topic in enumerate(ordered_topics, start=1):
        topic_title = str(parsed_topic["title"])
        topic_lines = list(parsed_topic["lines"])
        topic_label = _encode_legacy_text(topic_title)
        marker = str(parsed_topic["marker"])
        section = str(parsed_topic.get("section") or "other")
        context_id = _v3_context_id(marker, fallback_context_id, section=section)
        while context_id in used_context_ids:
            context_id += 1
        used_context_ids.add(context_id)
        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=_legacy_raw_lines(topic_lines),
                index_terms=[topic_label],
                alias_strings=[
                    topic_title,
                    marker,
                    str(parsed_topic["member_name"]),
                    section,
                    profile.version,
                    source_name,
                ],
                names=[topic_title],
                uhf_content=[render_uhf_line(line) for line in topic_lines],
            )
        )
        index_entries.append(IndexEntry(label=topic_label, context_id=context_id))
        contents_sections.setdefault(section, []).append(ContentNode(label=topic_title, topic_id=context_id))

    section_labels = {
        "manuals": "Návody",
        "cheats": "Cheaty",
        "jokes": "Vtipy",
        "other": "Další",
    }
    contents = [
        ContentNode(
            label=title,
            children=[
                ContentNode(label=section_labels[section_name], children=children)
                for section_name, children in (
                    ("manuals", contents_sections.get("manuals", [])),
                    ("cheats", contents_sections.get("cheats", [])),
                    ("jokes", contents_sections.get("jokes", [])),
                    ("other", contents_sections.get("other", [])),
                )
                if children
            ],
        )
    ]

    document = HelpDocument(
        format_name="scorpion-legacy",
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        contents=contents,
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
            "scorpion_parser": "v3-rar-member-topics",
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
            "parsed_topic_count": len(ordered_topics),
            "parsed_member_names": parsed_member_names,
            "unparsed_member_names": unparsed_member_names,
            "v3_index_title_count": len(cheat_title_overrides),
            "v3_index_order_count": len(cheat_ordered_markers),
            "v3_section_counts": {
                "manuals": len(section_topics.get("manuals", [])),
                "cheats": len(section_topics.get("cheats", [])),
                "jokes": len(section_topics.get("jokes", [])),
                "other": len(section_topics.get("other", [])),
            },
        },
        binary_data=data,
    )
    return ensure_document_index(document)


class ScorpionV3Reader(ScorpionRarSfxReaderBase):
    def read_bytes(self, data: bytes):
        overlay_info = _embedded_rar_overlay(data)
        if overlay_info is not None:
            overlay_offset, overlay = overlay_info
            members = _parse_rar4_members(overlay)
            if members:
                return self._finalize_document(
                    _build_v3_archive_document(self.profile, self.source_path.name, data, overlay_offset, overlay, members)
                )
        return self._finalize_document(_build_preview_document(self.profile, self.source_path.name, data))


class ScorpionV3_5Reader(ScorpionV3Reader):
    pass
