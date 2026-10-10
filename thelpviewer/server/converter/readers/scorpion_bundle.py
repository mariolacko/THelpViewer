"""Bundle export rules for Scorpions Cheater reader families."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

from ..base import ContentNode, HelpDocument, IndexEntry, TopicRecord
from ..bundle_types import BundleDocumentVariant, BundleSourceGroup
from ..codepages import decode_bytes
from ..uhf_markup import format_uhf_link_target, render_uhf_line
from .scorpion_reader import (
    SCORPION_TEXT_ENCODING,
    encode_scorpion_text,
    scorpion_version_hint_from_path,
    strip_legacy_container_suffix,
)


SCORPION_V3_SECTION_BUNDLES = (
    ("manuals", "navody", "Návody"),
    ("cheats", "cheaty", "Cheaty"),
    ("jokes", "vtipy", "Vtipy"),
)
SCORPION_SCO_CHEAT_DATA_RE = re.compile(r"^DATA(?P<number>\d+)\.SC[OD]$", re.IGNORECASE)
SCORPION_SCO_JOKE_DATA_RE = re.compile(r"^DATAV(?P<number>\d+)\.SC[OD]$", re.IGNORECASE)
SCORPION_SCO_MANUAL_DATA_RE = re.compile(r"^DATAN(?P<number>\d+)\.SC[OD]$", re.IGNORECASE)
SCORPION_SCO_NAVODY_DATA_RE = re.compile(r"^NAVODY(?P<number>\d+)\.SCO$", re.IGNORECASE)
SCORPION_SCO_TOPIC_MARKER_RE = re.compile(r"^(?:[A-Z]\d{3}|[A-Z]{2}\d{2}|\d{4})$")
SCORPION_SCO_INDEX_ENTRY_LINE_RE = re.compile(r"^.+?,\[(?P<target>[^\]]+)\](?:[»«]*[*+!\-]*[A-Za-z]*)?$")
SCORPION_SCO_PROGRAM_MARKER_RE = re.compile(r"^R\d{3}$")
SCORPION_UHF_STYLE_TAG_RE = re.compile(r"\[(?:/?(?:b|i|u|r|fg|bg|color)|(?:fg|bg|color)(?::|=)[^\]]+)\]")
SCORPION_PROGRAM_NUMBERED_LINE_RE = re.compile(r"^(?P<number>\d{1,2})\.\s+\S")
SCORPION_SCO_GROUPABLE_PARSERS = frozenset({"v4-sco-huffman", "sco-lzhuf"})
SCORPION_SCO_CATEGORY_CONFIG = {
    "cheats": {
        "bundle_stem": "cheaty",
        "label": "Cheaty",
        "role": "cheats",
        "index_roles": frozenset({"cheat-index"}),
        "source_name": "Cheaty",
        "description": "Scorpions Cheater cheat data",
    },
    "jokes": {
        "bundle_stem": "vtipy",
        "label": "Vtipy",
        "role": "jokes",
        "index_roles": frozenset({"joke-index"}),
        "source_name": "Vtipy",
        "description": "Scorpions Cheater joke data",
    },
    "manuals": {
        "bundle_stem": "navody",
        "label": "Návody",
        "role": "manuals",
        "index_roles": frozenset({"manual-index"}),
        "source_name": "Návody",
        "description": "Scorpions Cheater manual data",
    },
    "program": {
        "bundle_stem": "program",
        "label": "Program",
        "role": "program",
        "index_roles": frozenset(),
        "source_name": "Program",
        "description": "Scorpions Cheater program text",
    },
}


def _topic_section(topic: TopicRecord) -> str:
    for alias in topic.alias_strings:
        if alias in {"manuals", "cheats", "jokes", "other"}:
            return alias
    return ""


def _metadata_transport_keys(metadata: dict[str, object]) -> list[str]:
    keys = metadata.get("transport_metadata_keys")
    if isinstance(keys, list):
        return [key for key in keys if isinstance(key, str) and key.strip()]
    return []


def _append_metadata_transport_key(metadata: dict[str, object], key: str) -> None:
    keys = _metadata_transport_keys(metadata)
    if key not in keys:
        keys.append(key)
    metadata["transport_metadata_keys"] = keys


def _v3_section_document(document: HelpDocument, section: str, label: str) -> HelpDocument | None:
    topics = [topic for topic in document.topics if _topic_section(topic) == section]
    if not topics:
        return None

    topic_ids = {topic.context_id for topic in topics}
    index_entries = [
        entry
        for entry in document.index_entries
        if entry.context_id in topic_ids or entry.topic_id in topic_ids
    ]
    base_title = str(document.metadata.get("title") or document.display_name).strip()
    base_title = strip_legacy_container_suffix(base_title, document.source_name)
    section_title = f"{base_title} - {label}" if base_title else label
    contents = [
        ContentNode(
            label=section_title,
            children=[
                ContentNode(
                    label=topic.names[0] if topic.names else str(topic.context_id),
                    topic_id=topic.context_id,
                )
                for topic in topics
            ],
        )
    ]
    metadata = dict(document.metadata)
    metadata.update(
        {
            "title": section_title,
            "display_name": section_title,
            "description": section_title,
            "scorpion_v3_section": section,
            "parsed_topic_count": len(topics),
        }
    )
    _append_metadata_transport_key(metadata, "scorpion_v3_section")
    return HelpDocument(
        format_name=document.format_name,
        source_name=document.source_name,
        topics=topics,
        index_entries=index_entries,
        contents=contents,
        comments=list(document.comments),
        metadata=metadata,
        binary_data=document.binary_data,
    )


def _v3_section_variants(document: HelpDocument) -> list[BundleDocumentVariant]:
    if document.format_name != "scorpion-legacy":
        return []
    if document.metadata.get("scorpion_parser") != "v3-rar-member-topics":
        return []

    variants: list[BundleDocumentVariant] = []
    for section, bundle_stem, label in SCORPION_V3_SECTION_BUNDLES:
        section_document = _v3_section_document(document, section, label)
        if section_document is not None:
            variants.append(BundleDocumentVariant(bundle_stem=bundle_stem, document=section_document))
    return variants


def _sco_version_number(path: Path) -> float | None:
    version = scorpion_version_hint_from_path(path)
    if version is None:
        return None
    try:
        return float(version)
    except ValueError:
        return None


def _sco_regex_number(path: Path, regex: re.Pattern[str]) -> int | None:
    match = regex.fullmatch(path.name)
    if match is None:
        return None
    return int(match.group("number"))


def _sco_source_category(path: Path) -> str | None:
    version = _sco_version_number(path)
    if version is None or version < 4:
        return None
    suffix = path.suffix.upper()
    if suffix not in {".SCO", ".SCD"}:
        return None
    stem = path.stem.upper()
    if stem in {"DATAA", "CHEATS"} or SCORPION_SCO_CHEAT_DATA_RE.fullmatch(path.name):
        return "cheats"
    if stem in {"DATAB", "JOKES"} or SCORPION_SCO_JOKE_DATA_RE.fullmatch(path.name):
        return "jokes"
    if (
        stem == "HELPS"
        or SCORPION_SCO_MANUAL_DATA_RE.fullmatch(path.name)
        or SCORPION_SCO_NAVODY_DATA_RE.fullmatch(path.name)
    ):
        return "manuals"
    if stem in {"DATAHELP", "DATATEXT"}:
        return "program"
    return None


def _sco_category_sort_key(path: Path, category: str) -> tuple[int, int, str]:
    stem = path.stem.upper()
    if category == "cheats":
        if stem == "DATAA":
            return (0, 0, path.name.upper())
        if stem == "CHEATS":
            return (1, 0, path.name.upper())
        number = _sco_regex_number(path, SCORPION_SCO_CHEAT_DATA_RE)
        if number is not None:
            return (2, number, path.name.upper())
    if category == "jokes":
        if stem == "DATAB":
            return (0, 0, path.name.upper())
        if stem == "JOKES":
            return (1, 0, path.name.upper())
        number = _sco_regex_number(path, SCORPION_SCO_JOKE_DATA_RE)
        if number is not None:
            return (2, number, path.name.upper())
    if category == "manuals":
        if stem == "HELPS":
            return (0, 0, path.name.upper())
        number = _sco_regex_number(path, SCORPION_SCO_MANUAL_DATA_RE)
        if number is not None:
            return (1, number, path.name.upper())
        number = _sco_regex_number(path, SCORPION_SCO_NAVODY_DATA_RE)
        if number is not None:
            return (1, number, path.name.upper())
    if category == "program":
        if stem == "DATAHELP":
            return (0, 0, path.name.upper())
        if stem == "DATATEXT":
            return (1, 0, path.name.upper())
    return (99, 0, path.name.upper())


def _sco_category_source_groups(paths: list[Path]) -> dict[tuple[Path, str], tuple[Path, ...]]:
    groups: dict[tuple[Path, str], list[Path]] = {}
    for path in paths:
        category = _sco_source_category(path)
        if category is None:
            continue
        groups.setdefault((path.parent, category), []).append(path)
    return {
        key: tuple(sorted(items, key=lambda item: _sco_category_sort_key(item, key[1])))
        for key, items in groups.items()
        if items
    }


def _is_mergeable_sco_category_document(document: HelpDocument, category: str) -> bool:
    config = SCORPION_SCO_CATEGORY_CONFIG[category]
    role = document.metadata.get("scorpion_sco_role")
    if document.format_name != "scorpion-legacy":
        return False
    if document.metadata.get("scorpion_parser") not in SCORPION_SCO_GROUPABLE_PARSERS:
        return False
    if role == config["role"]:
        return bool(document.topics)
    return role in config["index_roles"] and bool(document.topics)


def _remap_optional_context(value: int | None, context_map: dict[int, int]) -> int | None:
    if value is None:
        return None
    return context_map.get(value, value)


def _remap_topic_record(topic: TopicRecord, context_map: dict[int, int]) -> TopicRecord:
    context_id = context_map[topic.context_id]
    nav_items = [
        replace(item, topic_id=_remap_optional_context(item.topic_id, context_map))
        for item in topic.nav_items
    ]
    quickhelp_category_nav = (
        None
        if topic.quickhelp_category_nav is None
        else replace(
            topic.quickhelp_category_nav,
            topic_id=_remap_optional_context(topic.quickhelp_category_nav.topic_id, context_map),
        )
    )
    positional_keywords = [
        replace(keyword, target_context=context_map.get(keyword.target_context, keyword.target_context))
        for keyword in topic.positional_keywords
    ]
    return replace(
        topic,
        context_id=context_id,
        raw_lines=list(topic.raw_lines),
        index_terms=list(topic.index_terms),
        alias_contexts=[context_map.get(alias, alias) for alias in topic.alias_contexts],
        alias_strings=list(topic.alias_strings),
        sequential_keywords=[context_map.get(keyword, keyword) for keyword in topic.sequential_keywords],
        positional_keywords=positional_keywords,
        up_context=_remap_optional_context(topic.up_context, context_map),
        down_context=_remap_optional_context(topic.down_context, context_map),
        prev_context=_remap_optional_context(topic.prev_context, context_map),
        next_context=_remap_optional_context(topic.next_context, context_map),
        names=list(topic.names),
        nav_items=nav_items,
        code_line_indices=set(topic.code_line_indices),
        quickhelp_category_nav=quickhelp_category_nav,
        uhf_content=list(topic.uhf_content),
    )


def _sco_index_title_overrides(documents: tuple[HelpDocument, ...]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for document in documents:
        entries = document.metadata.get("scorpion_sco_index_entries")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("kind") != "entry":
                continue
            target_id = entry.get("target_id")
            label = entry.get("label")
            if isinstance(target_id, str) and target_id and isinstance(label, str) and label:
                titles.setdefault(target_id, label)
    return titles


def _topic_marker(topic: TopicRecord) -> str | None:
    for alias in topic.alias_strings:
        if SCORPION_SCO_TOPIC_MARKER_RE.fullmatch(alias):
            return alias
    return None


def _retitle_topic(topic: TopicRecord, title: str) -> TopicRecord:
    encoded_title = encode_scorpion_text(title)
    raw_lines = list(topic.raw_lines)
    if raw_lines:
        raw_lines[0] = encoded_title
    uhf_content = list(topic.uhf_content)
    if uhf_content:
        uhf_content[0] = render_uhf_line(title)
    return replace(
        topic,
        raw_lines=raw_lines,
        index_terms=[encoded_title],
        names=[title],
        uhf_content=uhf_content,
    )


def _topic_index_label(topic: TopicRecord) -> bytes:
    if topic.names:
        return encode_scorpion_text(topic.names[0])
    if topic.index_terms:
        return topic.index_terms[0]
    return str(topic.context_id).encode("ascii")


def _sco_cross_bundle_link_target(target: str, source_paths: tuple[Path, ...]) -> str | None:
    if SCORPION_SCO_PROGRAM_MARKER_RE.fullmatch(target):
        bundle_group = source_paths[0].parent.name if source_paths else ""
        source_file = f"{bundle_group}/program.json.gz" if bundle_group else "program.json.gz"
        return format_uhf_link_target(source_file=source_file, alias=target)
    return None


def _link_sco_index_topic_lines(
    topic: TopicRecord,
    marker_to_context: dict[str, int],
    source_paths: tuple[Path, ...],
) -> TopicRecord:
    uhf_content = list(topic.uhf_content)
    if not uhf_content:
        return topic

    changed = False
    for index, raw_line in enumerate(topic.raw_lines[: len(uhf_content)]):
        try:
            text = decode_bytes(raw_line, SCORPION_TEXT_ENCODING).strip()
        except Exception:
            continue
        match = SCORPION_SCO_INDEX_ENTRY_LINE_RE.fullmatch(text)
        if match is None:
            continue
        target = match.group("target").strip()
        if "[link:" in uhf_content[index]:
            continue
        target_context = marker_to_context.get(target)
        if target_context is not None:
            link_target = format_uhf_link_target(topic_id=target_context)
        else:
            link_target = _sco_cross_bundle_link_target(target, source_paths)
        if link_target is None:
            continue
        uhf_content[index] = f"[link:{link_target}]{uhf_content[index]}[/link]"
        changed = True

    if not changed:
        return topic
    return replace(topic, uhf_content=uhf_content)


def _plain_uhf_text(text: str) -> str:
    return SCORPION_UHF_STYLE_TAG_RE.sub("", text).replace("[[", "[").strip()


def _link_sco_program_numbered_index(topic: TopicRecord) -> TopicRecord:
    uhf_content = list(topic.uhf_content)
    if not uhf_content:
        return topic

    number_lines: dict[str, list[int]] = {}
    for line_number, line in enumerate(uhf_content, start=1):
        if "[link:" in line:
            continue
        match = SCORPION_PROGRAM_NUMBERED_LINE_RE.match(_plain_uhf_text(line))
        if match is None:
            continue
        number_lines.setdefault(match.group("number"), []).append(line_number)

    changed = False
    for occurrences in number_lines.values():
        if len(occurrences) < 2:
            continue
        source_line = occurrences[0]
        target_line = occurrences[1]
        if source_line >= target_line:
            continue
        index = source_line - 1
        link_target = format_uhf_link_target(topic_id=topic.context_id, line=target_line)
        uhf_content[index] = f"[link:{link_target}]{uhf_content[index]}[/link]"
        changed = True

    if not changed:
        return topic
    return replace(topic, uhf_content=uhf_content)


def _merged_source_name(source_paths: tuple[Path, ...], category: str) -> str:
    stems = {path.stem.upper() for path in source_paths}
    suffixes = {path.suffix.upper() for path in source_paths}
    if category == "cheats":
        if "CHEATS" in stems:
            return "CHEATS.SCO"
        return "DATA*.SCD" if suffixes == {".SCD"} else "DATA*.SCO"
    if category == "jokes":
        if "JOKES" in stems:
            return "JOKES.SCO"
        return "DATAV*.SCD" if suffixes == {".SCD"} else "DATAV*.SCO"
    if category == "manuals":
        if "HELPS" in stems:
            return "HELPS.SCO"
        if any(stem.startswith("NAVODY") for stem in stems):
            return "NAVODY*.SCO"
        return "DATAN*.SCD" if suffixes == {".SCD"} else "DATAN*.SCO"
    if category == "program":
        return "PROGRAM.SCD" if suffixes == {".SCD"} else "PROGRAM.SCO"
    return source_paths[0].name


def _merge_sco_category_documents(
    source_paths: tuple[Path, ...],
    documents: tuple[HelpDocument, ...],
    category: str,
) -> HelpDocument:
    if not all(_is_mergeable_sco_category_document(document, category) for document in documents):
        source_names = ", ".join(path.name for path in source_paths)
        raise ValueError(f"Scorpions SCO/SCD {category} group is not fully decoded: {source_names}")

    config = SCORPION_SCO_CATEGORY_CONFIG[category]
    first_document = next(
        (document for document in documents if document.metadata.get("scorpion_sco_role") == config["role"]),
        documents[0],
    )
    base_title = str(first_document.metadata.get("title") or first_document.display_name).split(" - ", 1)[0].strip()
    label = str(config["label"])
    title = f"{base_title} - {label}" if base_title else label
    title_overrides = _sco_index_title_overrides(documents)
    topics: list[TopicRecord] = []
    context_id = 0
    marker_topic_count = 0

    for document in documents:
        context_map: dict[int, int] = {}
        for topic in document.topics:
            context_map[topic.context_id] = context_id
            context_id += 1
        for topic in document.topics:
            remapped_topic = _remap_topic_record(topic, context_map)
            marker = _topic_marker(remapped_topic)
            if marker is not None:
                marker_topic_count += 1
                title_override = title_overrides.get(marker)
                if title_override:
                    remapped_topic = _retitle_topic(remapped_topic, title_override)
            topics.append(remapped_topic)

    marker_to_context = {
        marker: topic.context_id
        for topic in topics
        if (marker := _topic_marker(topic)) is not None
    }
    topics = [
        _link_sco_index_topic_lines(topic, marker_to_context, source_paths)
        for topic in topics
    ]
    if category == "program":
        topics = [_link_sco_program_numbered_index(topic) for topic in topics]

    index_entries = [
        IndexEntry(label=_topic_index_label(topic), context_id=topic.context_id)
        for topic in topics
    ]

    contents = [
        ContentNode(
            label=title,
            children=[
                ContentNode(
                    label=topic.names[0] if topic.names else str(topic.context_id),
                    topic_id=topic.context_id,
                )
                for topic in topics
            ],
        )
    ]
    metadata = dict(first_document.metadata)
    lzhuf_counts = [
        count
        for document in documents
        if isinstance(count := document.metadata.get("scorpion_lzhuf_block_count"), int)
    ]
    index_entries_metadata = [
        entry
        for document in documents
        if isinstance(document.metadata.get("scorpion_sco_index_entries"), list)
        for entry in document.metadata["scorpion_sco_index_entries"]
    ]
    index_status_counts = Counter(
        entry["status"]
        for entry in index_entries_metadata
        if isinstance(entry, dict)
        and entry.get("kind") == "entry"
        and isinstance(entry.get("status"), str)
    )
    index_flag_counts = Counter(
        entry["flag"]
        for entry in index_entries_metadata
        if isinstance(entry, dict)
        and entry.get("kind") == "entry"
        and isinstance(entry.get("flag"), str)
    )
    metadata.update(
        {
            "title": title,
            "display_name": title,
            "description": title,
            "parsed_topic_count": len(topics),
            "scorpion_sco_role": config["role"],
            "scorpion_sco_source_files": [path.name for path in source_paths],
            "scorpion_sco_merged_category": category,
            "scorpion_sco_marker_topic_count": marker_topic_count,
            "scorpion_sco_index_entries": index_entries_metadata,
            "scorpion_sco_index_entry_count": sum(
                1 for entry in index_entries_metadata if isinstance(entry, dict) and entry.get("kind") == "entry"
            ),
            "scorpion_sco_index_header_count": sum(
                1 for entry in index_entries_metadata if isinstance(entry, dict) and entry.get("kind") == "header"
            ),
            "scorpion_sco_index_status_counts": dict(index_status_counts),
            "scorpion_sco_index_flag_counts": dict(index_flag_counts),
        }
    )
    if lzhuf_counts:
        metadata["scorpion_compression"] = "lzhuf"
        metadata["scorpion_lzhuf_block_count"] = sum(lzhuf_counts)
    _append_metadata_transport_key(metadata, "scorpion_sco_role")
    _append_metadata_transport_key(metadata, "scorpion_sco_source_files")
    _append_metadata_transport_key(metadata, "scorpion_sco_merged_category")
    _append_metadata_transport_key(metadata, "scorpion_sco_marker_topic_count")
    _append_metadata_transport_key(metadata, "scorpion_sco_index_entry_count")
    _append_metadata_transport_key(metadata, "scorpion_sco_index_header_count")
    _append_metadata_transport_key(metadata, "scorpion_sco_index_status_counts")
    _append_metadata_transport_key(metadata, "scorpion_sco_index_flag_counts")
    return HelpDocument(
        format_name=first_document.format_name,
        source_name=_merged_source_name(source_paths, category),
        topics=topics,
        index_entries=index_entries,
        contents=contents,
        metadata=metadata,
    )


def _build_sco_cheat_documents(source_paths: tuple[Path, ...], documents: tuple[HelpDocument, ...]) -> HelpDocument:
    return _merge_sco_category_documents(source_paths, documents, "cheats")


def _build_sco_joke_documents(source_paths: tuple[Path, ...], documents: tuple[HelpDocument, ...]) -> HelpDocument:
    return _merge_sco_category_documents(source_paths, documents, "jokes")


def _build_sco_manual_documents(source_paths: tuple[Path, ...], documents: tuple[HelpDocument, ...]) -> HelpDocument:
    return _merge_sco_category_documents(source_paths, documents, "manuals")


def _build_sco_program_documents(source_paths: tuple[Path, ...], documents: tuple[HelpDocument, ...]) -> HelpDocument:
    return _merge_sco_category_documents(source_paths, documents, "program")


SCORPION_SCO_CATEGORY_BUILDERS = {
    "cheats": _build_sco_cheat_documents,
    "jokes": _build_sco_joke_documents,
    "manuals": _build_sco_manual_documents,
    "program": _build_sco_program_documents,
}


def bundle_source_groups(paths: list[Path]) -> list[BundleSourceGroup]:
    groups: list[BundleSourceGroup] = []
    for (_parent, category), source_paths in _sco_category_source_groups(paths).items():
        config = SCORPION_SCO_CATEGORY_CONFIG[category]
        groups.append(
            BundleSourceGroup(
                source_paths=source_paths,
                bundle_stem=str(config["bundle_stem"]),
                build_document=SCORPION_SCO_CATEGORY_BUILDERS[category],
                description=str(config["description"]),
            )
        )
    return groups


def document_variants(document: HelpDocument) -> list[BundleDocumentVariant]:
    return _v3_section_variants(document)
