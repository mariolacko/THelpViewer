"""HTML renderer for the normalized help document model."""

from __future__ import annotations

import html
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from ..base import HelpDocument, PositionedKeyword, TopicRecord
from ..codepages import build_decode_table, decode_bytes_box_aware
from .. import __version__ as GENERATOR_VERSION


BOX_TRIM_CHARS = " \t\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c\u2580\u2584\u2588\u258c\u2590\u2591\u2592\u2593\u25a0\u2261"
BOX_ONLY_CHARS = set(BOX_TRIM_CHARS.strip() + "-_=|")
CODE_BLOCK_MARKER_BYTES = {0x03, 0x05, 0x10}
_EXAMPLE_HEADER_RE = re.compile(r"^Examples?\s*:", re.IGNORECASE)
PACKAGE_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
SITE_ASSET_DIR_NAME = "assets"
TV_DESKTOP_PATTERN_CHAR = "░"
GENERATOR_AUTHORS = "Mario Lacko + Copilot"
GENERATOR_LICENSE = "GPL-3.0"
TV_SCROLL_GLYPHS = {
    "y": ("▲", "▼"),
    "x": ("◄", "►"),
}
PASCAL_KEYWORDS = {
    "and",
    "array",
    "asm",
    "begin",
    "case",
    "const",
    "constructor",
    "destructor",
    "div",
    "do",
    "downto",
    "else",
    "end",
    "file",
    "for",
    "function",
    "goto",
    "if",
    "implementation",
    "in",
    "inherited",
    "interface",
    "label",
    "mod",
    "nil",
    "not",
    "object",
    "of",
    "or",
    "packed",
    "procedure",
    "program",
    "record",
    "repeat",
    "set",
    "shl",
    "shr",
    "string",
    "then",
    "to",
    "type",
    "unit",
    "until",
    "uses",
    "var",
    "while",
    "with",
    "xor",
}
CODE_TOKEN_RE = re.compile(r"(\{[^}]*\}|\(\*.*?\*\)|//.*$|'(?:''|[^'])*')", re.IGNORECASE)
CODE_FULL_COMMENT_RE = re.compile(r"^(\s*)(\{[^}]*\}|\(\*.*?\*\)|//.*)(\s*)$", re.IGNORECASE)
CODE_KEYWORD_RE = re.compile(r"\b(" + "|".join(sorted(PASCAL_KEYWORDS, key=len, reverse=True)) + r")\b", re.IGNORECASE)
CODE_NUMBER_RE = re.compile(r"(?<![\w&])(\$[0-9A-Fa-f]+|\d+(?:\.\d+)?)(?![\w;])")


def copy_site_assets(target_dir: str | Path) -> Path:
    """Replace one generated site's ``assets`` directory with current package assets."""
    target_asset_dir = Path(target_dir) / SITE_ASSET_DIR_NAME
    if target_asset_dir.exists():
        shutil.rmtree(target_asset_dir)
    if not PACKAGE_ASSET_DIR.is_dir():
        return target_asset_dir
    for source_path in PACKAGE_ASSET_DIR.rglob("*"):
        if not source_path.is_file():
            continue
        relative_path = source_path.relative_to(PACKAGE_ASSET_DIR)
        destination_path = target_asset_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
    return target_asset_dir


class HelpHtmlRenderer:
    """Render ``HelpDocument`` objects into a static multi-page HTML site."""

    def __init__(
        self,
        document: HelpDocument,
        display_encoding: str = "cp437",
        generator_name: str = "THelp Viewer Converter",
    ):
        self.document = document
        self.display_encoding = display_encoding
        self.generator_name = generator_name
        self.generator_version = GENERATOR_VERSION
        self.generator_authors = GENERATOR_AUTHORS
        self.generator_license = GENERATOR_LICENSE
        self.generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        self.decode_table = None if display_encoding == "utf-8" else build_decode_table(display_encoding, "unicode")
        self.asset_version = self._asset_version()
        self.search_version = self._search_version()
        self._bundle_mode = False
        meta = document.metadata or {}
        self._uses_code_heuristic = (
            meta.get("format_version") == 4 and meta.get("text_version") == 1
        )

    def write_site(self, output_dir: str | Path) -> Path:
        """Write ``index.html`` and one topic page per context id."""
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        self._write_assets(target_dir)
        (target_dir / "search-index.js").write_text(self.render_search_index_script(), encoding="utf-8")
        (target_dir / "index.html").write_text(self.render_index_page(), encoding="utf-8")

        for topic in self.document.topics:
            topic_path = target_dir / self.document.topic_filename(topic.context_id)
            topic_path.write_text(self.render_topic_page(topic), encoding="utf-8")

        return target_dir

    def render_index_page(self) -> str:
        """Render the alphabetical index page."""
        letters = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
        buckets = self._bucket_index_entries()
        sections: list[str] = []

        other_entries = buckets.pop(None, [])
        if other_entries:
            sections.append(self._render_index_section("other", "#", self._render_index_groups(other_entries)))

        nav_items: list[str] = []
        for letter in letters:
            if buckets.get(letter):
                nav_items.append(f"<a class=\"tv-index-jump\" href=\"#{letter}\">{letter}</a>")
                sections.append(self._render_index_section(letter, letter, self._render_index_groups(buckets[letter])))
            else:
                nav_items.append(f"<span class=\"tv-index-jump is-empty\">{letter}</span>")

        content_html = "\n".join(
            [
                "<div class=\"tv-document tv-index-document\">",
                "<a id=\"top\"></a>",
                f"<div class=\"tv-index-heading\">{html.escape(self._index_label())}</div>",
                f"<nav class=\"tv-index-nav\">{''.join(nav_items)}</nav>",
                *sections,
                "</div>",
            ]
        )
        return self._render_page(
            page_title=f"{self._site_name()} - Index",
            content_html=content_html,
            page_class="tv-index-page",
            menu_topic=None,
            status_hint=self._index_label(),
        )

    def render_topic_page(self, topic: TopicRecord) -> str:
        """Render one topic page including navigation and body text."""
        context_hex = f"{topic.context_id:04X}"
        content_html = "\n".join(
            [
                "<pre class=\"tv-pre tv-topic-pre\">",
                *self._render_topic_lines(topic),
                "</pre>",
            ]
        )
        return self._render_page(
            page_title=f"{self._site_name()} - {context_hex}",
            content_html=content_html,
            page_class="tv-topic-page",
            menu_topic=topic,
            status_hint=self._topic_heading(topic),
        )

    def _render_page(
        self,
        page_title: str,
        content_html: str,
        page_class: str = "",
        menu_topic: TopicRecord | None = None,
        status_hint: str = "",
    ) -> str:
        title = html.escape(page_title)
        window_title = html.escape(self._header_label())
        body_class = " ".join(part for part in ("tv-page", page_class) if part)
        window_style = html.escape(self._window_style())
        body_attrs = " ".join(
            [
                f'class="{body_class}"',
                f'data-tv-site-name="{html.escape(self._site_name())}"',
                f'data-tv-source-name="{html.escape(self.document.display_name)}"',
                f'data-tv-generator="{html.escape(self.generator_name)}"',
                f'data-tv-generator-version="{html.escape(self.generator_version)}"',
                f'data-tv-generated-at="{html.escape(self.generated_at)}"',
                f'data-tv-authors="{html.escape(self.generator_authors)}"',
                f'data-tv-license="{html.escape(self.generator_license)}"',
                f'data-tv-format-name="{html.escape(self.document.format_name)}"',
                f'data-tv-topic-count="{len(self.document.topics)}"',
                f'data-tv-index-count="{len(self.document.index_entries)}"',
                f'data-tv-page-kind="{"topic" if menu_topic is not None else "index"}"',
                f'data-tv-help-href="{html.escape(self._help_href())}"',
                f'data-tv-index-href="{html.escape("index.html")}"',
                f'data-tv-status-hint="{html.escape(status_hint)}"',
                (
                    f'data-tv-topic-context="{menu_topic.context_id:04X}" '
                    f'data-tv-topic-href="{html.escape(self.document.topic_filename(menu_topic.context_id))}"'
                )
                if menu_topic is not None
                else "",
            ]
        )
        return "\n".join(
            [
                "<!DOCTYPE html>",
                "<html lang=\"en\">",
                "<head>",
                "<meta charset=\"utf-8\">",
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
                f"<title>{title}</title>",
                f"<meta name=\"description\" content=\"{title} — TurboVision-style help file viewer\">",
                "<meta name=\"theme-color\" content=\"#000080\">",
                f"<meta name=\"GENERATOR\" content=\"{html.escape(self.generator_name)} {html.escape(self.generator_version)}\">",
                f"<link rel=\"stylesheet\" href=\"{SITE_ASSET_DIR_NAME}/turbovision.css?v={self.asset_version}\">",
                f"<script defer src=\"search-index.js?v={self.search_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/tv-core.js?v={self.asset_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/tv-highlight.js?v={self.asset_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/tv-dialogs.js?v={self.asset_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/tv-screensaver.js?v={self.asset_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/tv-games.js?v={self.asset_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/tv-shell.js?v={self.asset_version}\"></script>",
                f"<script defer src=\"{SITE_ASSET_DIR_NAME}/turbovision.js?v={self.asset_version}\"></script>",
                "</head>",
                f"<body {body_attrs}>",
                "<div class=\"tv-app\">",
                "<header class=\"tv-menu-bar\" data-tv-menu-bar></header>",
                "<div class=\"tv-desktop\">",
                f"<pre class=\"tv-desktop-pattern\" data-tv-desktop-pattern=\"{TV_DESKTOP_PATTERN_CHAR}\" aria-hidden=\"true\"></pre>",
                f"<main class=\"tv-window\" data-tv-window style=\"{window_style}\">",
                "<div class=\"tv-shell\">",
                "<div class=\"tv-border-row tv-border-top\" data-tv-move-handle>",
                "<span class=\"tv-border-corner\" aria-hidden=\"true\">╔</span>",
                "<a class=\"tv-close-control\" data-tv-close-button href=\"index.html\" aria-label=\"Close window\">[<span class=\"tv-close-glyph\" data-tv-close-glyph>■</span>]</a>",
                "<span class=\"tv-border-fill\" data-tv-border-fill=\"═\" aria-hidden=\"true\"></span>",
                f"<div class=\"tv-window-caption\">{window_title}</div>",
                "<span class=\"tv-border-fill\" data-tv-border-fill=\"═\" aria-hidden=\"true\"></span>",
                "<span class=\"tv-border-corner\" aria-hidden=\"true\">╗</span>",
                "</div>",
                "<div class=\"tv-client-row\">",
                "<span class=\"tv-border-side tv-border-side-left\" data-tv-border-side=\"║\" aria-hidden=\"true\"></span>",
                "<div class=\"tv-frame\">",
                "<div class=\"tv-scroll-shell\" data-tv-scroll-frame>",
                "<div class=\"tv-viewport\" data-tv-viewport>",
                content_html,
                "</div>",
                "</div>",
                "</div>",
                self._render_scrollbar("y"),
                "<div class=\"tv-bottom-bar\">",
                "<span class=\"tv-scroll-corner tv-scroll-corner-left\" aria-hidden=\"true\">╚</span>",
                self._render_scrollbar("x"),
                "<button type=\"button\" class=\"tv-grow-handle\" data-tv-resize-handle aria-label=\"Resize window\">─┘</button>",
                "</div>",
                "</div>",
                "</div>",
                "</main>",
                "</div>",
                "<footer class=\"tv-status-line\" data-tv-status-line></footer>",
                "</div>",
                "</body>",
                "</html>",
            ]
        ) + "\n"

    def _window_style(self) -> str:
        """Expose preferred Turbo Vision window size through CSS variables."""
        cols, rows = self._window_geometry()
        min_cols, min_rows = self._window_min_geometry(cols, rows)
        return (
            f"--tv-window-cols:{cols}; --tv-window-rows:{rows}; "
            f"--tv-window-min-cols:{min_cols}; --tv-window-min-rows:{min_rows};"
        )

    def _window_geometry(self) -> tuple[int, int]:
        """Choose a stable outer window size instead of stretching to the viewport."""
        width = self.document.metadata.get("width")
        height = self.document.metadata.get("height")

        if isinstance(width, int) and width > 0:
            cols = width + 3
        elif self.document.format_name == "fbhf":
            cols = 50
        else:
            cols = 82

        if isinstance(height, int) and height > 0:
            rows = height + 3
        elif self.document.format_name == "fbhf":
            rows = 18
        else:
            rows = 24

        return cols, rows

    def _window_min_geometry(self, cols: int, rows: int) -> tuple[int, int]:
        """Choose resize minima from help metadata or from a generic 80x25 default."""
        width = self.document.metadata.get("width")
        height = self.document.metadata.get("height")

        if isinstance(width, int) and width > 0 and isinstance(height, int) and height > 0:
            return cols, rows
        # Never let the resize minimum exceed the initial geometry, otherwise
        # smaller help windows jump to a larger size on the first resize drag.
        return min(cols, 80), min(rows, 25)

    def _asset_version(self) -> int:
        """Return a stable cache-busting version for bundled assets."""
        latest = 0.0
        if PACKAGE_ASSET_DIR.is_dir():
            for source_path in PACKAGE_ASSET_DIR.rglob("*"):
                if source_path.is_file():
                    latest = max(latest, source_path.stat().st_mtime)
        return int(latest) if latest else 0

    def _search_version(self) -> str:
        """Return a content-based cache-busting version for ``search-index.js``."""
        digest = hashlib.sha1()
        digest.update(self.document.source_name.encode("utf-8", errors="replace"))
        digest.update(self.document.format_name.encode("ascii", errors="replace"))
        for topic in self.document.topics:
            digest.update(topic.context_id.to_bytes(4, "little", signed=False))
            for raw_line in topic.raw_lines:
                digest.update(raw_line)
                digest.update(b"\n")
            for term in topic.index_terms:
                digest.update(term)
                digest.update(b"\0")
        for entry in self.document.index_entries:
            digest.update(entry.context_id.to_bytes(4, "little", signed=False))
            digest.update(entry.label)
            digest.update(b"\0")
        return digest.hexdigest()[:12]

    def render_search_index_script(self) -> str:
        """Emit a static client-side search index for the current help tree."""
        payload = {
            "site_name": self._site_name(),
            "source_name": self.document.display_name,
            "topics": self._search_topics_payload(),
        }
        return "window.TV_SEARCH_INDEX = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"

    def _search_topics_payload(self) -> list[dict[str, object]]:
        labels_by_context: dict[int, list[str]] = {}
        for entry in self.document.index_entries:
            label = self._decode_bytes(entry.label).strip()
            if label:
                labels_by_context.setdefault(entry.context_id, []).append(label)

        payload: list[dict[str, object]] = []
        for topic in self.document.topics:
            title = self._topic_heading(topic)
            body_lines = self._searchable_topic_lines(topic)
            preview = " ".join(body_lines[:3]).strip()
            if len(preview) > 180:
                preview = preview[:177].rstrip() + "..."
            payload.append(
                {
                    "context_id": topic.context_id,
                    "context_hex": f"{topic.context_id:04X}",
                    "href": self.document.topic_filename(topic.context_id),
                    "title": title,
                    "preview": preview,
                    "index_terms": sorted(
                        {
                            *labels_by_context.get(topic.context_id, []),
                            *(self._decode_bytes(term).strip() for term in topic.index_terms if term.strip()),
                        }
                    ),
                    "text": "\n".join(body_lines),
                }
            )
        return payload

    def _searchable_topic_lines(self, topic: TopicRecord) -> list[str]:
        """Collect normalized plain-text lines for client-side search."""
        lines: list[str] = []
        for raw_line in topic.raw_lines:
            if self._is_code_block_marker(raw_line):
                continue
            text = self._decode_bytes(raw_line.replace(b"\x02", b"")).replace("\x00", "").strip()
            if not text or self._is_underline(text):
                continue
            compact = " ".join(text.split())
            compact = compact.strip(BOX_TRIM_CHARS).strip()
            if compact:
                lines.append(compact)
        return lines

    def _render_scrollbar(self, axis: str) -> str:
        """Emit one TurboVision-style scrollbar."""
        backward, forward = TV_SCROLL_GLYPHS[axis]

        return (
            f"<div class=\"tv-scrollbar tv-scrollbar-{axis}\" data-axis=\"{axis}\">"
            f"<button type=\"button\" class=\"tv-scroll-arrow tv-scroll-arrow-backward\" data-role=\"backward\" aria-label=\"Scroll {axis} backward\">{backward}</button>"
            f"<div class=\"tv-scroll-track\" data-role=\"track\"><div class=\"tv-scroll-cells\" data-role=\"cells\"></div><div class=\"tv-scroll-thumb\" data-role=\"thumb\"></div></div>"
            f"<button type=\"button\" class=\"tv-scroll-arrow tv-scroll-arrow-forward\" data-role=\"forward\" aria-label=\"Scroll {axis} forward\">{forward}</button>"
            "</div>"
        )

    def _render_index_groups(self, entries: list[tuple[bytes, int]]) -> list[str]:
        """Render index entries as grouped HTML blocks instead of raw text."""
        if not entries:
            return ["<div class=\"tv-index-empty\">(empty)</div>"]

        lines: list[str] = []
        group: list[tuple[bytes, int]] = []
        current_label: bytes | None = None

        def flush() -> None:
            if not group:
                return
            label = group[0][0]
            rendered_label = html.escape(self._decode_bytes(label))
            if len(group) == 1:
                lines.append(f"<div class=\"tv-index-entry\">{self._topic_link(group[0][1], rendered_label)}</div>")
                return

            lines.append("<div class=\"tv-index-entry-group\">")
            lines.append(f"<div class=\"tv-index-group-label\">{rendered_label}</div>")
            lines.append("<div class=\"tv-index-group-items\">")
            for _, context_id in group:
                topic = self._topic_by_context(context_id)
                topic_label = html.escape(self._topic_heading(topic)) if topic else f"Context {context_id}"
                lines.append(f"<div class=\"tv-index-group-item\">{self._topic_link(context_id, topic_label)}</div>")
            lines.append("</div>")
            lines.append("</div>")

        for entry in entries:
            label, _context_id = entry
            if current_label is None or label == current_label:
                group.append(entry)
                current_label = label
                continue
            flush()
            group = [entry]
            current_label = label

        flush()
        return lines

    def _render_index_section(self, anchor: str, label: str, body_lines: list[str]) -> str:
        """Render one alphabet bucket in the index page."""
        return "\n".join(
            [
                f"<section class=\"tv-index-section\" id=\"{html.escape(anchor)}\">",
                "<div class=\"tv-index-section-heading\">",
                f"<span class=\"tv-index-section-label\">{html.escape(label)}</span>",
                "<a class=\"tv-top-link\" href=\"#top\">Top</a>",
                "</div>",
                "<div class=\"tv-index-section-body\">",
                *body_lines,
                "</div>",
                "</section>",
            ]
        )

    def _render_topic_lines(self, topic: TopicRecord) -> list[str]:
        rendered: list[str] = [""]
        positional_by_line: dict[int, list[PositionedKeyword]] = {}
        for keyword in topic.positional_keywords:
            positional_by_line.setdefault(keyword.line, []).append(keyword)
        for keyword_list in positional_by_line.values():
            keyword_list.sort(key=lambda keyword: keyword.first_column)

        sequential_index = 0
        in_code_block = False
        for line_number, raw_line in enumerate(topic.raw_lines, start=1):
            # THELP uses standalone control-byte lines to toggle code examples.
            if self._is_code_block_marker(raw_line):
                in_code_block = not in_code_block
                continue

            # Heuristic for TC 2.0/2.01: detect "Example:" lines.
            if self._uses_code_heuristic:
                decoded = self._decode_bytes(raw_line)
                if _EXAMPLE_HEADER_RE.match(decoded):
                    in_code_block = True
                elif in_code_block and decoded.strip() and not decoded.startswith(" "):
                    in_code_block = False

            if line_number in positional_by_line:
                line_html = self._render_positioned_line(raw_line, positional_by_line[line_number])
                rendered.append(self._wrap_code_line(line_html, in_code_block))
                continue
            if b"\x02" in raw_line and topic.sequential_keywords:
                # Newer THELP variants store hotspot ranges inline and targets sequentially.
                line_html, sequential_index = self._render_sequential_line(
                    raw_line, topic.sequential_keywords, sequential_index
                )
                rendered.append(self._wrap_code_line(line_html, in_code_block))
                continue
            line_html = html.escape(self._decode_bytes(raw_line), quote=False)
            rendered.append(self._wrap_code_line(line_html, in_code_block))
        return rendered

    def _wrap_code_line(self, line_html: str, in_code_block: bool) -> str:
        """Wrap code-example lines so CSS can style them differently."""
        if not in_code_block:
            return line_html
        if not line_html:
            return "<span class=\"code-example code-example-empty\">&nbsp;</span>"
        if self._bundle_mode:
            return f"<span class=\"code-example\">{line_html}</span>"
        return f"<span class=\"code-example\">{self._highlight_code_line(line_html)}</span>"

    def _highlight_code_line(self, line_html: str) -> str:
        """Apply lightweight Pascal-like syntax highlighting to code-example lines."""
        if "<a " in line_html or "<span " in line_html:
            return line_html
        full_comment = CODE_FULL_COMMENT_RE.match(line_html)
        if full_comment:
            leading, token, trailing = full_comment.groups()
            return f'{leading}<span class="code-comment code-comment-line">{token}</span>{trailing}'

        parts: list[str] = []
        cursor = 0
        for match in CODE_TOKEN_RE.finditer(line_html):
            start, end = match.span()
            if start > cursor:
                parts.append(self._highlight_code_plain(line_html[cursor:start]))
            token = match.group(0)
            css_class = "code-string" if token.startswith("'") else "code-comment"
            parts.append(f"<span class=\"{css_class}\">{token}</span>")
            cursor = end
        if cursor < len(line_html):
            parts.append(self._highlight_code_plain(line_html[cursor:]))
        return "".join(parts)

    def _highlight_code_plain(self, text: str) -> str:
        """Highlight keywords and numbers inside non-comment code fragments."""
        highlighted = CODE_KEYWORD_RE.sub(lambda match: f"<span class=\"code-keyword\">{match.group(0)}</span>", text)
        highlighted = CODE_NUMBER_RE.sub(lambda match: f"<span class=\"code-number\">{match.group(0)}</span>", highlighted)
        return highlighted

    def _render_positioned_line(self, raw_line: bytes, keywords: list[PositionedKeyword]) -> str:
        """Render old-format keyword links with explicit line/column ranges."""
        parts: list[str] = []
        cursor = 0
        for keyword in keywords:
            start = max(keyword.first_column - 1, 0)
            end = min(keyword.last_column, len(raw_line))
            if start > cursor:
                parts.append(html.escape(self._decode_bytes(raw_line[cursor:start]), quote=False))
            label = html.escape(self._decode_bytes(raw_line[start:end]), quote=False)
            parts.append(self._topic_link(keyword.target_context, label))
            cursor = end
        parts.append(html.escape(self._decode_bytes(raw_line[cursor:]), quote=False))
        return "".join(parts)

    def _render_sequential_line(self, raw_line: bytes, keywords: list[int], start_index: int) -> tuple[str, int]:
        """Render new-format inline hotspots delimited by ``0x02`` markers."""
        parts: list[str] = []
        buffer = bytearray()
        in_hotspot = False
        keyword_index = start_index

        for value in raw_line:
            if value != 0x02:
                buffer.append(value)
                continue

            if in_hotspot:
                text = html.escape(self._decode_bytes(bytes(buffer)), quote=False)
                if keyword_index < len(keywords):
                    parts.append(self._topic_link(keywords[keyword_index], text))
                    keyword_index += 1
                else:
                    parts.append(text)
                buffer.clear()
                in_hotspot = False
                continue

            if buffer:
                parts.append(html.escape(self._decode_bytes(bytes(buffer)), quote=False))
                buffer.clear()
            in_hotspot = True

        if buffer:
            parts.append(html.escape(self._decode_bytes(bytes(buffer)), quote=False))
        return "".join(parts), keyword_index

    def _bucket_index_entries(self) -> dict[str | None, list[tuple[bytes, int]]]:
        """Group index entries by the first visible ASCII letter."""
        buckets: dict[str | None, list[tuple[bytes, int]]] = {None: []}
        for entry in self.document.index_entries:
            letter = self._index_bucket(entry.label)
            buckets.setdefault(letter, []).append((entry.label, entry.context_id))
        return buckets

    def _index_bucket(self, raw_label: bytes) -> str | None:
        text = self._decode_bytes(raw_label).lstrip()
        if not text:
            return None
        first = text[0].upper()
        if "A" <= first <= "Z":
            return first
        return None

    def _topic_by_context(self, context_id: int) -> TopicRecord | None:
        for topic in self.document.topics:
            if topic.context_id == context_id:
                return topic
        return None

    def _topic_heading(self, topic: TopicRecord) -> str:
        """Extract a readable title from the first non-empty text lines."""
        for raw_line in topic.raw_lines:
            if not raw_line.strip():
                continue
            text = self._decode_bytes(raw_line.replace(b"\x02", b""))
            compact = text.strip()
            if not compact:
                continue
            if self._is_underline(compact):
                continue
            # Replace box-drawing glyphs with spaces, then collapse and strip.
            cleaned = compact
            for ch in BOX_TRIM_CHARS:
                if ch in (" ", "\t"):
                    continue
                cleaned = cleaned.replace(ch, " ")
            compact = " ".join(cleaned.split()).strip()
            if compact:
                return compact
        if topic.index_terms:
            return self._decode_bytes(topic.index_terms[0])
        if topic.names:
            return topic.names[0]
        return f"Context {topic.context_id}"

    def _is_underline(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True
        return all(char in BOX_ONLY_CHARS for char in stripped)

    def _is_code_block_marker(self, raw_line: bytes) -> bool:
        """Detect standalone THELP code-example delimiters such as ``0x05``."""
        stripped = raw_line.strip(b" \t")
        if not stripped:
            return False
        return any(value in CODE_BLOCK_MARKER_BYTES for value in stripped) and all(value in CODE_BLOCK_MARKER_BYTES for value in stripped)

    def _decode_bytes(self, data: bytes) -> str:
        if self.display_encoding == "utf-8":
            return data.replace(b"\x00", b"").decode("utf-8", errors="replace").replace("\r", "")
        if self.display_encoding == "cp852":
            return decode_bytes_box_aware(data, "cp852")
        return "".join(self.decode_table[value] for value in data if value != 0x00 and value != 0x0D)

    def _topic_link(self, context_id: int, label_html: str) -> str:
        if self._topic_by_context(context_id) is None:
            return label_html
        return f"<a href=\"{self.document.topic_filename(context_id)}\">{label_html}</a>"

    def _help_topic(self) -> TopicRecord | None:
        """Return the best landing topic for the Help menu item."""
        # Use main_index from metadata if available
        main_idx = self.document.metadata.get("main_index")
        if main_idx is not None and isinstance(main_idx, int):
            topic = self._topic_by_context(main_idx)
            if topic is not None:
                return topic
        # Fall back to topic marked as main index
        for topic in self.document.topics:
            if topic.is_main_index:
                return topic
        return self.document.topics[0] if self.document.topics else None

    def _help_href(self) -> str:
        topic = self._help_topic()
        if topic is None:
            return "index.html"
        return self.document.topic_filename(topic.context_id)

    def _site_name(self) -> str:
        desc = self.document.metadata.get("description")
        if desc and isinstance(desc, str):
            return desc
        stamp = self.document.metadata.get("stamp", "")
        if isinstance(stamp, str):
            cleaned = stamp.replace(" HELP FILE.", "").strip()
            if cleaned and all(ord(c) < 128 for c in cleaned):
                return cleaned.title() + " Help"
        if self.document.format_name == "borland":
            return "Turbo Pascal Help"
        if self.document.format_name == "fbhf":
            return "Turbo Vision Help"
        if self.document.format_name in {"m602", "software602"}:
            return "Software602 Help"
        return "Help"

    def _header_label(self) -> str:
        return f"{self._site_name()} ({self.document.display_name})"

    def _index_label(self) -> str:
        if self.document.format_name == "borland":
            return "Turbo Help Index"
        if self.document.format_name == "fbhf":
            return "Help Index"
        if self.document.format_name in {"m602", "software602"}:
            return "Software602 Help Index"
        return "Help Index"

    def render_json_bundle(self) -> dict[str, object]:
        """Return a JSON-serializable bundle with pre-rendered HTML for every topic."""
        self._bundle_mode = True
        cols, rows = self._window_geometry()
        min_cols, min_rows = self._window_min_geometry(cols, rows)
        help_topic = self._help_topic()

        topics_payload: list[dict[str, object]] = []
        for topic in self.document.topics:
            topic_html = "\n".join(
                [
                    "<pre class=\"tv-pre tv-topic-pre\">",
                    *self._render_topic_lines(topic),
                    "</pre>",
                ]
            )
            topics_payload.append(
                {
                    "context_id": topic.context_id,
                    "context_hex": f"{topic.context_id:04X}",
                    "title": self._topic_heading(topic),
                    "html": topic_html,
                    "is_main_index": topic.is_main_index,
                }
            )

        index_entries_payload: list[dict[str, object]] = []
        for entry in self.document.index_entries:
            label = self._decode_bytes(entry.label).strip()
            index_entries_payload.append(
                {
                    "label": label,
                    "context_id": entry.context_id,
                    "context_hex": f"{entry.context_id:04X}",
                }
            )

        search_index = self._search_topics_payload()

        return {
            "name": self._site_name(),
            "source_name": self.document.display_name,
            "format_name": self.document.format_name,
            "encoding": self.display_encoding,
            "header_label": self._header_label(),
            "index_label": self._index_label(),
            "window": {
                "cols": cols,
                "rows": rows,
                "min_cols": min_cols,
                "min_rows": min_rows,
            },
            "help_context": f"{help_topic.context_id:04X}" if help_topic else None,
            "topic_count": len(self.document.topics),
            "index_entry_count": len(self.document.index_entries),
            "index_entries": index_entries_payload,
            "topics": topics_payload,
            "search_index": search_index,
        }

    def _write_assets(self, target_dir: Path) -> None:
        """Copy shared CSS, JS and font files next to generated HTML pages."""
        copy_site_assets(target_dir)
