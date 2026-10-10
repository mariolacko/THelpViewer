"""Shared in-memory data model for parsed help documents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
import re

from .uhf_markup import escape_uhf_text, format_uhf_link, parse_uhf_link_target

_BOX_LINE_BYTES = frozenset(
    {
        0x20,
        0x2D,
        0x3D,
        0x5F,
        0x7C,
        0xB0,
        0xB1,
        0xB2,
        0xB3,
        0xB4,
        0xB9,
        0xBA,
        0xBB,
        0xBC,
        0xBF,
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC4,
        0xC5,
        0xC8,
        0xC9,
        0xCA,
        0xCB,
        0xCC,
        0xCD,
        0xCE,
        0xD9,
        0xDA,
        0xDB,
        0xDC,
        0xDD,
        0xDE,
        0xDF,
    }
)

NAV_BACK_CONTEXT = -1
NAV_CONTENTS_CONTEXT = -2
NAV_INDEX_CONTEXT = -3
_NAV_ACTION_BY_CONTEXT = {
    NAV_BACK_CONTEXT: "back",
    NAV_CONTENTS_CONTEXT: "contents",
    NAV_INDEX_CONTEXT: "index",
}
_NAV_CONTEXT_BY_ACTION = {action: context for context, action in _NAV_ACTION_BY_CONTEXT.items()}


def context_nav_action(context_id: int | None) -> str | None:
    """Return the shared navigation action for one pseudo-context id."""
    if not isinstance(context_id, int):
        return None
    return _NAV_ACTION_BY_CONTEXT.get(context_id)


def nav_action_context(action: str | None) -> int | None:
    """Return the shared pseudo-context id used for one navigation action."""
    if not isinstance(action, str):
        return None
    return _NAV_CONTEXT_BY_ACTION.get(action.strip().lower())


@dataclass(slots=True)
class PositionedKeyword:
    """One positioned hotspot range pointing to another topic."""

    target_context: int
    line: int
    first_column: int
    last_column: int
    navigation: tuple[int | None, int | None, int | None, int | None] = (
        None,
        None,
        None,
        None,
    )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of one positioned hotspot record."""
        return {
            "target_context": self.target_context,
            "line": self.line,
            "first_column": self.first_column,
            "last_column": self.last_column,
            "navigation": list(self.navigation),
        }


@dataclass(slots=True)
class TopicNavItem:
    """One topic-level navigation action or link shown in a menu bar."""

    label: str
    topic_id: int | None = None
    action: str | None = None
    source_file: str | None = None
    alias: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of one normalized nav item."""
        payload: dict[str, object] = {"label": self.label}
        if self.topic_id is not None:
            payload["topic_id"] = self.topic_id
        if self.action:
            payload["action"] = self.action
        if self.source_file:
            payload["file"] = self.source_file
        if self.alias:
            payload["alias"] = self.alias
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass(slots=True)
class TopicTag:
    """One searchable topic attribute shown as a clickable tag."""

    key: str
    value: str
    label: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-safe view of one topic tag."""
        payload = {"key": self.key, "value": self.value}
        if self.label:
            payload["label"] = self.label
        return payload


@dataclass(slots=True)
class TopicRecord:
    """One logical help topic with raw text and hyperlink metadata."""

    context_id: int
    raw_lines: list[bytes]
    index_terms: list[bytes] = field(default_factory=list)
    alias_contexts: list[int] = field(default_factory=list)
    alias_strings: list[str] = field(default_factory=list)
    sequential_keywords: list[int] = field(default_factory=list)
    positional_keywords: list[PositionedKeyword] = field(default_factory=list)
    is_help_contents: bool = False
    redirect_context: int | None = None
    up_context: int | None = None
    down_context: int | None = None
    prev_context: int | None = None
    next_context: int | None = None
    names: list[str] = field(default_factory=list)
    nav_items: list[TopicNavItem] = field(default_factory=list)
    code_line_indices: set[int] = field(default_factory=set)
    frozen_rows: int = 0
    quickhelp_category_nav: TopicNavItem | None = None
    quickhelp_is_list: bool = False
    quickhelp_is_popup: bool = False
    uhf_content: list[str] = field(default_factory=list)
    tags: list[TopicTag] = field(default_factory=list)

    def to_dict(self, text_encoding: str = "latin1") -> dict[str, object]:
        """Return a JSON-safe view of one normalized help topic."""
        payload = {
            "context_id": self.context_id,
            "names": list(self.names),
            "raw_lines": [_serialize_bytes(line, text_encoding) for line in self.raw_lines],
            "index_terms": [_serialize_bytes(term, text_encoding) for term in self.index_terms],
            "alias_contexts": list(self.alias_contexts),
            "alias_strings": list(self.alias_strings),
            "sequential_keywords": list(self.sequential_keywords),
            "positional_keywords": [keyword.to_dict() for keyword in self.positional_keywords],
            "is_help_contents": self.is_help_contents,
            "redirect_context": self.redirect_context,
            "up_context": self.up_context,
            "down_context": self.down_context,
            "prev_context": self.prev_context,
            "next_context": self.next_context,
            "nav_items": [item.to_dict() for item in self.nav_items],
            "code_line_indices": sorted(self.code_line_indices),
            "frozen_rows": self.frozen_rows,
            "uhf_content": list(self.uhf_content),
            "tags": [tag.to_dict() for tag in self.tags],
        }
        if self.quickhelp_category_nav is not None:
            payload["quickhelp_category_nav"] = self.quickhelp_category_nav.to_dict()
        if self.quickhelp_is_list:
            payload["quickhelp_is_list"] = True
        if self.quickhelp_is_popup:
            payload["quickhelp_is_popup"] = True
        return payload


@dataclass(slots=True)
class IndexEntry:
    """One index label pointing to a topic or to a generic UHF target."""

    label: bytes
    context_id: int
    topic_id: int | None = None
    source_file: str | None = None
    alias: str | None = None
    line: int | None = None

    def to_dict(self, text_encoding: str = "latin1") -> dict[str, object]:
        """Return a JSON-safe view of one visible index entry."""
        payload: dict[str, object] = {
            "label": _serialize_bytes(self.label, text_encoding),
            "context_id": self.context_id,
        }
        if self.topic_id is not None:
            payload["topic_id"] = self.topic_id
        if self.source_file:
            payload["file"] = self.source_file
        if self.alias:
            payload["alias"] = self.alias
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass(slots=True)
class ContentNode:
    """One table-of-contents node."""

    label: str
    hotkey: str = ""
    topic_id: int | None = None
    source_file: str | None = None
    alias: str | None = None
    line: int | None = None
    children: list["ContentNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of one TOC node."""
        payload: dict[str, object] = {
            "label": self.label,
            "children": [child.to_dict() for child in self.children],
        }
        if self.hotkey:
            payload["hotkey"] = self.hotkey
        if self.topic_id is not None:
            payload["topic_id"] = self.topic_id
        if self.source_file:
            payload["file"] = self.source_file
        if self.alias:
            payload["alias"] = self.alias
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass(slots=True)
class CommentRecord:
    """One preserved source comment, optionally scoped to a specific topic."""

    text: str
    topic_context: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe view of one preserved source comment."""
        return {
            "text": self.text,
            "topic_context": self.topic_context,
        }


@dataclass(slots=True)
class HelpDocument:
    """Normalized document model shared by all readers and renderers."""

    format_name: str
    source_name: str
    topics: list[TopicRecord]
    index_entries: list[IndexEntry]
    contents: list[ContentNode] = field(default_factory=list)
    comments: list[CommentRecord] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    binary_data: bytes | None = None

    @property
    def display_name(self) -> str:
        """Human-friendly document name prepared by readers when available."""
        for key in ("title", "display_name", "description"):
            value = self.metadata.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
        source_path = Path(self.source_name)
        stem = source_path.stem.strip()
        if stem:
            return stem.lower()
        return source_path.name.lower()

    @staticmethod
    def topic_filename(context_id: int) -> str:
        """Map a numeric context id to a stable HTML file name."""
        return f"{context_id:04X}.html"

    def to_dict(
        self,
        text_encoding: str = "latin1",
        include_binary_data: bool = False,
    ) -> dict[str, object]:
        """Return a JSON-safe snapshot of the normalized help document."""
        payload = {
            "format_name": self.format_name,
            "source_name": self.source_name,
            "display_name": self.display_name,
            "text_encoding": text_encoding,
            "topic_count": len(self.topics),
            "index_entry_count": len(self.index_entries),
            "comment_count": len(self.comments),
            "topics": [topic.to_dict(text_encoding=text_encoding) for topic in self.topics],
            "index_entries": [entry.to_dict(text_encoding=text_encoding) for entry in self.index_entries],
            "contents": [node.to_dict() for node in self.contents],
            "comments": [comment.to_dict() for comment in self.comments],
            "metadata": _json_safe(self.metadata, text_encoding),
        }
        if include_binary_data and self.binary_data is not None:
            payload["binary_data"] = {
                "size": len(self.binary_data),
                "hex": self.binary_data.hex(),
            }
        return payload

    def to_json(
        self,
        text_encoding: str = "latin1",
        include_binary_data: bool = False,
        indent: int = 2,
    ) -> str:
        """Serialize the document model to formatted JSON text."""
        return json.dumps(
            self.to_dict(text_encoding=text_encoding, include_binary_data=include_binary_data),
            ensure_ascii=False,
            indent=indent,
        )

    def write_json(
        self,
        path: str | Path,
        text_encoding: str = "latin1",
        include_binary_data: bool = False,
        indent: int = 2,
    ) -> Path:
        """Write the document model to a JSON file and return its path."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            self.to_json(
                text_encoding=text_encoding,
                include_binary_data=include_binary_data,
                indent=indent,
            ),
            encoding="utf-8",
        )
        return target_path


class HelpReaderBase(ABC):
    """Common interface shared by binary and textual help readers."""

    def __init__(
        self,
        source_name: str = "input.hlp",
        text_encoding: str = "latin1",
        source_path: str | Path | None = None,
    ):
        self.source_name = source_name
        self.text_encoding = text_encoding
        self.source_path = Path(source_path) if source_path is not None else None

    @abstractmethod
    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read raw file bytes and return the normalized document model."""

    def read_path(self, path: str | Path) -> HelpDocument:
        """Load bytes from disk and delegate to ``read_bytes``."""
        source_path = Path(path)
        self.source_name = source_path.name
        self.source_path = source_path
        return self.read_bytes(source_path.read_bytes())


_UHF_NAV_ACTION_RE = re.compile(r"\[nav:([^\]]+)\](.*?)\[/nav\]")
_UHF_NAV_LINK_RE = re.compile(r"\[link:([^\]]+)\](.*?)\[/link\]")
_UHF_INLINE_STYLE_RE = re.compile(
    r"\[/?(?:b|i|u|r|fg[:=][^\]]+|bg[:=][^\]]+|color[:=][^\]]+)\]"
)


def first_non_null(values: list[int | None]) -> int | None:
    """Return the first non-None value from one candidate list."""
    for value in values:
        if value is not None:
            return value
    return None


def topic_prev_next(topic: TopicRecord) -> tuple[int | None, int | None]:
    """Return topic previous/next targets from explicit fields or hotspot metadata."""
    if topic.prev_context is not None or topic.next_context is not None:
        return topic.prev_context, topic.next_context

    left_candidates: list[int | None] = []
    right_candidates: list[int | None] = []
    for keyword in topic.positional_keywords:
        left_candidates.append(keyword.navigation[0])
        right_candidates.append(keyword.navigation[1])
    return first_non_null(left_candidates), first_non_null(right_candidates)


def merge_nav_items(*groups: list[TopicNavItem]) -> list[TopicNavItem]:
    """Merge nav item lists while preserving first-seen label order."""
    merged: list[TopicNavItem] = []
    seen_labels: set[str] = set()
    for group in groups:
        for item in group:
            label = item.label.strip()
            if not label or label in seen_labels:
                continue
            seen_labels.add(label)
            merged.append(item)
    return merged


def build_directional_nav_items(topic: TopicRecord) -> list[TopicNavItem]:
    """Create default Up/Down/Prev/Next nav items from topic links."""
    prev_context, next_context = topic_prev_next(topic)
    items: list[TopicNavItem] = []
    for label, target_context in (
        ("Up", topic.up_context),
        ("Down", topic.down_context),
        ("Prev", prev_context),
        ("Next", next_context),
    ):
        if target_context is None:
            continue
        items.append(TopicNavItem(label=label, topic_id=target_context))
    return items


def render_topic_uhf_content(
    topic: TopicRecord,
    *,
    decode_bytes: Callable[[bytes], str],
    topic_ids: set[int],
    fallback_map: dict[int, dict[str, int | str]] | None = None,
) -> list[str]:
    """Render one normalized topic body as UHF content lines.

    Readers use this when they preserve raw lines plus hotspot metadata in the
    shared model but still want export-ready UHF without duplicating renderer
    logic in individual writers.
    """
    resolved_fallbacks = fallback_map or {}
    content: list[str] = []
    code_line_indices = set(topic.code_line_indices or set())
    in_code_block = False

    positional_by_line: dict[int, list[PositionedKeyword]] = {}
    for keyword in topic.positional_keywords:
        positional_by_line.setdefault(keyword.line, []).append(keyword)
    for keywords in positional_by_line.values():
        keywords.sort(key=lambda keyword: keyword.first_column)

    sequential_index = 0
    for line_index, raw_line in enumerate(topic.raw_lines):
        line_is_code = line_index in code_line_indices
        if line_is_code and not in_code_block:
            content.append("[code]")
            in_code_block = True
        elif not line_is_code and in_code_block:
            content.append("[/code]")
            in_code_block = False

        decoded_line = decode_bytes(raw_line)
        if (
            not line_is_code
            and decoded_line.strip().casefold() == "<more>"
            and topic.down_context in topic_ids
        ):
            content.append(format_uhf_link("<more>", topic_id=topic.down_context))
            continue

        line_number = line_index + 1
        if line_number in positional_by_line:
            content.append(
                _render_positioned_uhf_line(
                    raw_line,
                    positional_by_line[line_number],
                    decode_bytes=decode_bytes,
                    topic_ids=topic_ids,
                    fallback_map=resolved_fallbacks,
                )
            )
            continue

        if topic.sequential_keywords:
            rendered_line, next_index = _render_sequential_uhf_line(
                raw_line,
                topic.sequential_keywords,
                sequential_index,
                decode_bytes=decode_bytes,
                topic_ids=topic_ids,
                fallback_map=resolved_fallbacks,
            )
            if next_index != sequential_index:
                content.append(rendered_line)
                sequential_index = next_index
                continue

        content.append(escape_uhf_text(decoded_line))

    if in_code_block:
        content.append("[/code]")

    return content


def _render_positioned_uhf_line(
    raw_line: bytes,
    keywords: list[PositionedKeyword],
    *,
    decode_bytes: Callable[[bytes], str],
    topic_ids: set[int],
    fallback_map: dict[int, dict[str, int | str]],
) -> str:
    """Render one line with positioned hotspot ranges."""
    parts: list[str] = []
    cursor = 0

    for keyword in keywords:
        start = max(keyword.first_column - 1, 0)
        end = min(keyword.last_column, len(raw_line))
        if start > cursor:
            parts.append(_escape_uhf_segment(raw_line[cursor:start], decode_bytes))
        label = _escape_uhf_segment(raw_line[start:end], decode_bytes)
        parts.append(
            _wrap_uhf_link_target(
                keyword.target_context,
                label,
                topic_ids=topic_ids,
                fallback_map=fallback_map,
            )
        )
        cursor = end

    parts.append(_escape_uhf_segment(raw_line[cursor:], decode_bytes))
    return "".join(parts)


def _render_sequential_uhf_line(
    raw_line: bytes,
    keywords: list[int],
    start_index: int,
    *,
    decode_bytes: Callable[[bytes], str],
    topic_ids: set[int],
    fallback_map: dict[int, dict[str, int | str]],
) -> tuple[str, int]:
    """Render one line with the shared in-band sequential hotspot delimiter."""
    if b"\x02" not in raw_line:
        return _escape_uhf_segment(raw_line, decode_bytes), start_index

    parts: list[str] = []
    buffer = bytearray()
    in_hotspot = False
    keyword_index = start_index

    for value in raw_line:
        if value != 0x02:
            buffer.append(value)
            continue

        if in_hotspot:
            label = _escape_uhf_segment(bytes(buffer), decode_bytes)
            if keyword_index < len(keywords):
                parts.append(
                    _wrap_uhf_link_target(
                        keywords[keyword_index],
                        label,
                        topic_ids=topic_ids,
                        fallback_map=fallback_map,
                    )
                )
                keyword_index += 1
            else:
                parts.append(label)
            buffer.clear()
            in_hotspot = False
            continue

        if buffer:
            parts.append(_escape_uhf_segment(bytes(buffer), decode_bytes))
            buffer.clear()
        in_hotspot = True

    if buffer:
        parts.append(_escape_uhf_segment(bytes(buffer), decode_bytes))

    return "".join(parts), keyword_index


def _wrap_uhf_link_target(
    target_context: int,
    label: str,
    *,
    topic_ids: set[int],
    fallback_map: dict[int, dict[str, int | str]],
) -> str:
    """Format one visible label as a UHF link or nav action when resolvable."""
    nav_action = context_nav_action(target_context)
    if nav_action:
        return f"[nav:{nav_action}]{label}[/nav]"

    if target_context in topic_ids:
        return format_uhf_link(label, topic_id=target_context)

    fallback = fallback_map.get(target_context)
    if fallback is None:
        return label

    topic_id = fallback.get("topic_id")
    if topic_id is not None and not isinstance(topic_id, int):
        topic_id = None

    source_file = fallback.get("source_file")
    if not isinstance(source_file, str) or not source_file.strip():
        source_file = None

    alias = fallback.get("alias")
    if not isinstance(alias, str) or not alias.strip():
        alias = None

    line = fallback.get("line")
    if not isinstance(line, int) or line <= 0:
        line = None

    if topic_id is None and source_file is None and alias is None and line is None:
        return label

    return format_uhf_link(
        label,
        topic_id=topic_id,
        source_file=source_file,
        alias=alias,
        line=line,
    )


def _escape_uhf_segment(raw: bytes, decode_bytes: Callable[[bytes], str]) -> str:
    """Decode and escape one literal text segment for UHF output."""
    return escape_uhf_text(decode_bytes(raw))


def extract_nav_items_from_uhf(
    content: list[str],
    *,
    valid_topic_ids: set[int] | None = None,
) -> list[TopicNavItem]:
    """Extract leading nav bar items from already prepared UHF content lines."""
    items: list[TopicNavItem] = []
    for line in _leading_nav_lines(content):
        for action, raw_label in _UHF_NAV_ACTION_RE.findall(line):
            label = _strip_inline_markup(raw_label)
            action_name = action.strip().lower()
            if label and action_name:
                items.append(TopicNavItem(label=label, action=action_name))
        for target_text, raw_label in _UHF_NAV_LINK_RE.findall(line):
            label = _strip_inline_markup(raw_label)
            if not label:
                continue
            target = parse_uhf_link_target(target_text)
            if not target:
                continue
            topic_id = target.get("topic_id")
            source_file = target.get("source_file")
            if (
                isinstance(topic_id, int)
                and valid_topic_ids is not None
                and not isinstance(source_file, str)
                and topic_id not in valid_topic_ids
            ):
                continue
            item = TopicNavItem(label=label)
            if isinstance(topic_id, int):
                item.topic_id = topic_id
            if isinstance(source_file, str) and source_file.strip():
                item.source_file = source_file.strip()
            alias = target.get("alias")
            if isinstance(alias, str) and alias.strip():
                item.alias = alias.strip()
            line_number = target.get("line")
            if isinstance(line_number, int) and line_number > 0:
                item.line = line_number
            if item.topic_id is not None or item.source_file or item.alias or item.line is not None:
                items.append(item)
    return merge_nav_items(items)


def _leading_nav_lines(content: list[str]) -> list[str]:
    """Return the initial contiguous UHF lines that behave like a nav bar."""
    lines: list[str] = []
    started = False
    for line in content:
        if line == "[rule]":
            if started:
                continue
            continue
        if not line.strip():
            if started:
                break
            continue
        has_nav = "[nav:" in line or "[link:" in line
        if has_nav:
            started = True
            lines.append(line)
            continue
        if started:
            break
        return []
    return lines


def _strip_inline_markup(text: str) -> str:
    """Remove inline UHF style markup from one visible label."""
    plain = _UHF_INLINE_STYLE_RE.sub("", text)
    return plain.replace("[[", "[").strip()


def ensure_document_index(document: HelpDocument) -> HelpDocument:
    """Populate a simple per-topic index when the source format has none."""
    if document.index_entries:
        return document

    generated = build_fallback_index_entries(document.topics)
    if generated:
        document.index_entries = generated
        document.metadata.setdefault("index_generated", True)
    return document


def build_fallback_index_entries(topics: list[TopicRecord]) -> list[IndexEntry]:
    """Create one fallback index entry per topic in source order."""
    entries: list[IndexEntry] = []
    seen_contexts: set[int] = set()

    for topic in topics:
        if topic.context_id in seen_contexts:
            continue
        label = _fallback_index_label(topic)
        if not label:
            continue
        entries.append(IndexEntry(label=label, context_id=topic.context_id))
        seen_contexts.add(topic.context_id)

    return entries


def _fallback_index_label(topic: TopicRecord) -> bytes | None:
    """Pick one stable label from topic metadata or visible source lines."""
    for label in topic.index_terms:
        normalized = _normalize_index_label_bytes(label)
        if normalized:
            return normalized

    for raw_line in topic.raw_lines:
        normalized = _normalize_index_label_bytes(raw_line)
        if not normalized:
            continue
        if normalized.startswith(b"."):
            continue
        if _looks_like_box_line(normalized):
            continue
        return normalized

    for name in topic.names:
        normalized = name.strip()
        if normalized and not normalized.startswith("."):
            return normalized.encode("latin-1", errors="replace")

    return None


def _normalize_index_label_bytes(raw: bytes) -> bytes:
    """Strip link markers and surrounding whitespace from one fallback label."""
    return raw.replace(b"\x02", b"").strip()


def _looks_like_box_line(raw: bytes) -> bool:
    """Return True for pure border/underline lines that should not become index labels."""
    if not raw:
        return False
    return all(value in _BOX_LINE_BYTES for value in raw)


def _decode_bytes(value: bytes, text_encoding: str) -> str:
    """Decode raw help text for human-readable JSON inspection."""
    if text_encoding == "utf-8":
        return value.decode("utf-8", errors="replace")
    try:
        return value.decode(text_encoding, errors="replace")
    except LookupError:
        from .codepages import decode_bytes

        return decode_bytes(value, text_encoding)


def _serialize_bytes(value: bytes, text_encoding: str) -> dict[str, str]:
    """Expose both decoded text and raw bytes for lossless JSON export."""
    return {
        "text": _decode_bytes(value, text_encoding),
        "hex": value.hex(),
    }


def _json_safe(value: object, text_encoding: str) -> object:
    """Convert nested document metadata to values accepted by ``json``."""
    if isinstance(value, bytes):
        return _serialize_bytes(value, text_encoding)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item, text_encoding) for item in value]
    if isinstance(value, list):
        return [_json_safe(item, text_encoding) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item, text_encoding) for key, item in value.items()}
    return value
