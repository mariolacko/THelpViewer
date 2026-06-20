"""UHF 2.0 JSON writer for the normalized ``HelpDocument`` model."""

from __future__ import annotations

import gzip
import json
import string
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__ as GENERATOR_VERSION
from ..base import HelpDocument, PositionedKeyword, TopicNavItem, TopicRecord, context_nav_action, render_topic_uhf_content
from ..uhf_markup import escape_uhf_text, format_uhf_link
from .html import HelpHtmlRenderer


SOURCE_FORMAT_BY_READER: dict[str, str] = {
    "borland": "thelp",
    "calc602": "text602",
    "fbhf": "fbhf",
    "game-cheater": "pc-fand",
    "hlx": "hlx",
    "m602": "m602",
    "norton-guide": "norton-guide",
    "quickhelp": "quickhelp",
    "software602": "m602",
    "tdh": "tdh",
    "tfh": "tfh",
    "text602": "text602",
}

TRANSPORT_METADATA_KEYS: tuple[str, ...] = (
    "hlx_kind",
    "hlx_family",
    "index_navigation_order",
    "control_byte_dominant",
    "record_count",
    "pointer_count",
    "topic_count",
    "index_record_count",
    "index_topic_count",
    "rtf_ref_count",
    "overview_rtf_count",
    "lkeyword_rtf_count",
    "hex_prefix_count",
    "long_string_count",
    "avg_lines_per_topic",
    "single_line_ratio",
)

TRANSPORT_METADATA_LIST_KEYS: tuple[str, ...] = (
    "control_byte_dominant",
)

TRANSPORT_METADATA_STRUCT_KEYS: tuple[str, ...] = ()
TRANSPORT_METADATA_KEY_LIST = "transport_metadata_keys"


def _extra_transport_metadata_keys(meta: dict[str, object]) -> list[str]:
    value = meta.get(TRANSPORT_METADATA_KEY_LIST)
    if not isinstance(value, (list, tuple)):
        return []
    keys: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key == TRANSPORT_METADATA_KEY_LIST or key in keys:
            continue
        keys.append(key)
    return keys

class HelpJsonRenderer:
    """Render one ``HelpDocument`` as a UHF 2.0 JSON structure."""

    def __init__(
        self,
        document: HelpDocument,
        display_encoding: str = "cp437",
        generator_name: str = "THelpViewer",
    ):
        self.document = document
        self.display_encoding = display_encoding
        self.generator_name = generator_name
        self.html_renderer = HelpHtmlRenderer(
            document,
            display_encoding=display_encoding,
            generator_name=generator_name,
        )
        self.suppressed_topic_ids = {
            topic.context_id
            for topic in document.topics
            if topic.redirect_context is not None and topic.redirect_context != topic.context_id
        }
        self.topic_ids = {
            topic.context_id
            for topic in document.topics
            if topic.context_id not in self.suppressed_topic_ids
        }

    def render_document(self) -> dict[str, object]:
        """Return a JSON-serializable UHF 2.0 document."""
        payload: dict[str, object] = {
            "uhf_version": "2.0",
            "metadata": self._build_metadata(),
            "converter": self._build_converter(),
            "contents": self._build_contents(),
            "index": self._build_index(),
            "topics": self._build_topics(),
        }
        default_palette = self._default_palette()
        if default_palette:
            payload["default_palette"] = default_palette
        palettes = self._build_palettes()
        if palettes:
            payload["palettes"] = palettes
        return payload

    def to_json(self, indent: int = 2) -> str:
        """Serialize the rendered UHF document to formatted JSON."""
        return json.dumps(
            self.render_document(),
            ensure_ascii=False,
            indent=indent,
        )

    def write_json(self, path: str | Path, indent: int = 2) -> Path:
        """Write the rendered UHF document to disk and return the path."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(self.to_json(indent=indent) + "\n", encoding="utf-8")
        return target_path

    def write_json_gz(
        self,
        path: str | Path,
        indent: int = 2,
        compresslevel: int = 9,
    ) -> Path:
        """Write the rendered UHF document as gzip-compressed UTF-8 JSON."""
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = (self.to_json(indent=indent) + "\n").encode("utf-8")
        target_path.write_bytes(gzip.compress(payload, compresslevel=compresslevel))
        return target_path

    def _build_metadata(self) -> dict[str, object]:
        meta = self.document.metadata or {}
        source_metadata: dict[str, object] = {
            "filename": Path(self.document.source_name).name,
            "format": self._source_format(),
            "encoding": self._source_encoding(),
        }
        payload: dict[str, object] = {
            "name": self._metadata_name(),
            "encoding": "utf-8",
            "source": source_metadata,
        }

        source_date = meta.get("source_date")
        if isinstance(source_date, str):
            cleaned_source_date = source_date.strip()
            if cleaned_source_date:
                source_metadata["date"] = cleaned_source_date

        author = self._metadata_author()
        if author:
            payload["author"] = author

        copyright_text = self._metadata_copyright()
        if copyright_text:
            payload["copyright"] = copyright_text

        display: dict[str, int] = {}
        cols = meta.get("width")
        if not isinstance(cols, int):
            cols = meta.get("display_width")
        rows = meta.get("height")
        if self._source_format() == "quickhelp" and isinstance(cols, int) and cols > 100:
            cols = None
        if isinstance(cols, int) and cols > 0:
            display["cols"] = cols
        if isinstance(rows, int) and rows > 0:
            display["rows"] = rows
        if display:
            payload["display"] = display

        help_contents_topic_id = self._help_contents_topic_id()
        if help_contents_topic_id is not None:
            payload["help_contents_topic_id"] = help_contents_topic_id

        language = self._metadata_language()
        if language:
            payload["language"] = language

        ui = self._metadata_ui()
        if ui:
            payload["ui"] = ui

        frozen_rows = meta.get("frozen_rows")
        if isinstance(frozen_rows, int) and frozen_rows > 0:
            payload["frozen_rows"] = frozen_rows

        emitted_metadata_keys: set[str] = set()

        show_topic_titles = meta.get("show_topic_titles")
        if isinstance(show_topic_titles, bool):
            payload["show_topic_titles"] = show_topic_titles
            emitted_metadata_keys.add("show_topic_titles")

        for key in TRANSPORT_METADATA_KEYS:
            value = meta.get(key)
            if isinstance(value, (str, int, float, bool)):
                payload[key] = value
                emitted_metadata_keys.add(key)

        for key in TRANSPORT_METADATA_LIST_KEYS:
            value = meta.get(key)
            if isinstance(value, list):
                payload[key] = list(value)
                emitted_metadata_keys.add(key)

        for key in TRANSPORT_METADATA_STRUCT_KEYS:
            value = meta.get(key)
            if isinstance(value, list):
                payload[key] = [dict(item) if isinstance(item, dict) else item for item in value]
                emitted_metadata_keys.add(key)
            elif isinstance(value, dict):
                payload[key] = dict(value)
                emitted_metadata_keys.add(key)

        for key in _extra_transport_metadata_keys(meta):
            if key in emitted_metadata_keys:
                continue
            value = meta.get(key)
            if isinstance(value, (str, int, float, bool)):
                payload[key] = value
            elif isinstance(value, list):
                payload[key] = [dict(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, dict):
                payload[key] = dict(value)

        return payload

    def _default_palette(self) -> str:
        """Return an explicitly configured default inline color palette name."""
        meta = self.document.metadata or {}
        value = meta.get("default_palette")
        if isinstance(value, str) and value.strip():
            return value.strip()
        value = meta.get("palette")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return ""

    def _build_palettes(self) -> dict[str, object]:
        """Return only palettes explicitly supplied by source metadata."""
        palettes: dict[str, object] = {}
        meta_palettes = (self.document.metadata or {}).get("palettes")
        if not isinstance(meta_palettes, dict):
            return palettes

        for raw_name, raw_palette in meta_palettes.items():
            if not isinstance(raw_name, str) or not raw_name.strip() or not isinstance(raw_palette, dict):
                continue
            name = raw_name.strip()
            merged: dict[str, object] = {}
            if isinstance(raw_palette.get("type"), str) and raw_palette["type"].strip():
                merged["type"] = raw_palette["type"].strip()

            raw_colors = raw_palette.get("colors")
            colors: dict[str, str] = {}
            if isinstance(raw_colors, dict):
                for key, value in raw_colors.items():
                    if isinstance(value, str) and value.strip():
                        colors[str(key)] = value.strip()
            elif isinstance(raw_colors, list):
                for index, value in enumerate(raw_colors):
                    if isinstance(value, str) and value.strip():
                        colors[str(index)] = value.strip()
            if colors:
                merged["colors"] = colors

            raw_aliases = raw_palette.get("aliases")
            aliases: dict[str, int | str] = {}
            if isinstance(raw_aliases, dict):
                for key, value in raw_aliases.items():
                    if isinstance(key, str) and key.strip() and isinstance(value, (int, str)):
                        aliases[key.strip()] = value.strip() if isinstance(value, str) else value
            if aliases:
                merged["aliases"] = aliases

            if merged:
                palettes[name] = merged
        return palettes

    def _help_contents_topic_id(self) -> int | None:
        """Return the source help contents topic id when known."""
        meta = self.document.metadata or {}
        value = meta.get("help_contents_topic_id")
        if isinstance(value, int) and value in self.topic_ids:
            return value
        if isinstance(value, str) and value.strip().isdigit():
            parsed = int(value.strip())
            if parsed in self.topic_ids:
                return parsed
        for topic in self.document.topics:
            if topic.is_help_contents and topic.context_id in self.topic_ids:
                return topic.context_id
        return None

    def _build_converter(self) -> dict[str, str]:
        return {
            "name": self.generator_name,
            "version": GENERATOR_VERSION,
            "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def _build_contents(self) -> list[dict[str, object]]:
        """Return the TOC tree prepared by the source reader."""
        return [node.to_dict() for node in self.document.contents]

    def _build_index(self) -> list[dict[str, object]]:
        grouped: dict[str, list[dict[str, object]]] = {"#": []}

        # Build helper maps to resolve index entry context ids or alias strings
        alias_id_map: dict[int, int] = {}
        alias_string_map: dict[str, int] = {}
        for topic in self.document.topics:
            try:
                topic_id = int(topic.context_id)
            except Exception:
                topic_id = topic.context_id
            for aid in getattr(topic, "alias_contexts", []) or []:
                if isinstance(aid, int):
                    alias_id_map[aid] = topic_id
            for astr in getattr(topic, "alias_strings", []) or []:
                if isinstance(astr, bytes):
                    s = self.html_renderer._decode_bytes(astr).strip().lower()
                else:
                    s = str(astr).strip().lower()
                if s:
                    alias_string_map[s] = topic_id

        for entry in self.document.index_entries:
            label = self.html_renderer._decode_bytes(entry.label).strip()
            if not label:
                continue
            group = label[0].upper()
            if group not in string.ascii_uppercase:
                group = "#"

            # Resolve target context id to one that exists in this document's topics.
            # UHF2 does not emit unresolved/debug-only index targets.
            target = entry.topic_id if entry.topic_id is not None else entry.context_id
            if target not in self.topic_ids:
                mapped = alias_id_map.get(target)
                if mapped is None:
                    mapped = alias_string_map.get(label.strip().lower())
                if mapped is not None:
                    target = mapped
            payload: dict[str, object] = {"label": label}
            if target in self.topic_ids:
                payload["topic_id"] = target
            elif entry.topic_id is not None:
                continue
            else:
                continue
            if entry.topic_id is not None:
                if entry.source_file:
                    payload["file"] = entry.source_file
                if entry.alias:
                    payload["alias"] = entry.alias
                if entry.line is not None:
                    payload["line"] = entry.line
            grouped.setdefault(group, []).append(payload)

        payload: list[dict[str, object]] = []
        if grouped["#"]:
            payload.append({"group": "#", "entries": grouped["#"]})

        for letter in string.ascii_uppercase:
            entries = grouped.get(letter)
            if entries:
                payload.append({"group": letter, "entries": entries})

        return payload

    def _build_topics(self) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        for topic in self.document.topics:
            if topic.context_id in self.suppressed_topic_ids:
                continue
            content = self._build_topic_content(topic)
            topic_payload: dict[str, object] = {
                "id": topic.context_id,
                "title": self.html_renderer._topic_heading(topic),
                "content": content,
            }

            aliases = self._build_topic_aliases(topic)
            if aliases:
                topic_payload["aliases"] = aliases
            if topic.tags:
                topic_payload["tags"] = [tag.to_dict() for tag in topic.tags]
            if topic.is_help_contents:
                topic_payload["is_help_contents"] = True
            if topic.frozen_rows > 0:
                topic_payload["frozen_rows"] = topic.frozen_rows

            nav = self._serialize_nav_items(topic.nav_items)
            if nav:
                topic_payload["nav"] = nav

            payload[str(topic.context_id)] = topic_payload

        return payload

    @staticmethod
    def _build_topic_aliases(topic: TopicRecord) -> dict[str, list[int] | list[str]] | None:
        aliases: dict[str, list[int] | list[str]] = {}
        if topic.alias_contexts:
            aliases["ids"] = list(topic.alias_contexts)
        if topic.alias_strings:
            aliases["strings"] = list(topic.alias_strings)
        return aliases or None

    def _build_topic_content(self, topic: TopicRecord) -> list[str]:
        if topic.uhf_content:
            return list(topic.uhf_content)
        if topic.sequential_keywords:
            return render_topic_uhf_content(
                topic,
                decode_bytes=self.html_renderer._decode_bytes,
                topic_ids=self.topic_ids,
            )

        content: list[str] = []
        code_line_indices = set(topic.code_line_indices or set())
        in_code_block = False

        positional_by_line: dict[int, list[PositionedKeyword]] = {}
        for keyword in topic.positional_keywords:
            positional_by_line.setdefault(keyword.line, []).append(keyword)
        for keywords in positional_by_line.values():
            keywords.sort(key=lambda keyword: keyword.first_column)

        for line_index, raw_line in enumerate(topic.raw_lines):
            line_is_code = line_index in code_line_indices
            if line_is_code and not in_code_block:
                content.append("[code]")
                in_code_block = True
            elif not line_is_code and in_code_block:
                content.append("[/code]")
                in_code_block = False

            if line_is_code:
                # For code lines, still render positional/sequential hotspots
                # as UHF inline tags so the viewer can convert them to anchors.
                line_number = line_index + 1
                if line_number in positional_by_line:
                    content.append(self._render_positioned_line(raw_line, positional_by_line[line_number]))
                    continue
                # Ensure code lines are escaped consistently — do not
                # emit raw decoded HTML into code blocks. Use
                # _render_plain_segment which applies the canonical
                # UHF escaping used elsewhere.
                content.append(self._render_plain_segment(raw_line))
                continue

            line_number = line_index + 1
            if line_number in positional_by_line:
                content.append(self._render_positioned_line(raw_line, positional_by_line[line_number]))
                continue
            content.append(self._escape_plain_text(self.html_renderer._decode_bytes(raw_line)))

        if in_code_block:
            content.append("[/code]")

        return content

    def _render_positioned_line(self, raw_line: bytes, keywords: list[PositionedKeyword]) -> str:
        parts: list[str] = []
        cursor = 0

        for keyword in keywords:
            start = max(keyword.first_column - 1, 0)
            end = min(keyword.last_column, len(raw_line))
            if start > cursor:
                parts.append(self._render_plain_segment(raw_line[cursor:start]))
            label = self._escape_plain_text(self.html_renderer._decode_bytes(raw_line[start:end]))
            parts.append(self._wrap_link_text(keyword.target_context, label))
            cursor = end

        parts.append(self._render_plain_segment(raw_line[cursor:]))
        return "".join(parts)

    def _render_plain_segment(self, raw_segment: bytes) -> str:
        return self._escape_plain_text(self.html_renderer._decode_bytes(raw_segment))

    @staticmethod
    def _escape_plain_text(text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        return escape_uhf_text(text)

    def _wrap_link_text(self, target_context: int, label: str) -> str:
        nav_action = context_nav_action(target_context)
        if nav_action:
            return f"[nav:{nav_action}]{label}[/nav]"
        if target_context not in self.topic_ids:
            return label
        return format_uhf_link(label, topic_id=target_context)

    def _metadata_name(self) -> str:
        name = self.document.display_name.strip()
        if name:
            return name
        return self.html_renderer._site_name()

    def _serialize_nav_items(self, nav_items: list[TopicNavItem]) -> dict[str, dict[str, int | str]]:
        nav: dict[str, dict[str, int | str]] = {}
        for item in nav_items:
            label = item.label.strip()
            if not label:
                continue
            payload: dict[str, int | str] = {}
            if item.action:
                payload["action"] = item.action
            if item.source_file:
                payload["file"] = item.source_file
            if item.topic_id is not None:
                payload["topic_id"] = item.topic_id
            if item.alias:
                payload["alias"] = item.alias
            if item.line is not None and item.line > 0:
                payload["line"] = item.line
            if payload:
                nav[label] = payload
        return nav

    def _metadata_author(self) -> str | None:
        meta = self.document.metadata or {}
        credit_lines = meta.get("credit_lines")
        if isinstance(credit_lines, list):
            for line in credit_lines:
                if isinstance(line, str) and line.strip():
                    return line.strip()
        return None

    def _metadata_copyright(self) -> str | None:
        meta = self.document.metadata or {}
        credit_lines = meta.get("credit_lines")
        if isinstance(credit_lines, list):
            for line in credit_lines:
                if isinstance(line, str) and line.strip():
                    lowered = line.lower()
                    if "copyright" in lowered or "(c)" in lowered:
                        return line.strip()
        return None

    def _metadata_language(self) -> str | None:
        meta = self.document.metadata or {}
        language = meta.get("language")
        if not isinstance(language, str):
            return None
        normalized = language.strip().replace("_", "-").lower()
        return normalized or None

    def _metadata_ui(self) -> dict[str, str] | None:
        meta = self.document.metadata or {}
        theme: dict[str, str] = {}
        raw_theme = meta.get("ui")
        if isinstance(raw_theme, dict):
            for key, value in raw_theme.items():
                if isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip():
                    theme[key.strip()] = value.strip()
        return theme or None

    def _source_format(self) -> str:
        suffix = Path(self.document.source_name).suffix.lower()
        if suffix in {".hlx", ".hl6"}:
            return "hlx"
        return SOURCE_FORMAT_BY_READER.get(self.document.format_name, self.document.format_name)

    def _source_encoding(self) -> str:
        meta = self.document.metadata or {}
        encoding = (meta.get("source_encoding")
                    or meta.get("text_encoding")
                    or meta.get("encoding")
                    or self.display_encoding)
        return self._normalize_encoding_name(str(encoding))

    @staticmethod
    def _normalize_encoding_name(encoding: str) -> str:
        aliases = {
            "latin1": "latin-1",
            "latin2": "latin-2",
            "utf8": "utf-8",
        }
        lowered = encoding.strip().lower()
        return aliases.get(lowered, lowered)
