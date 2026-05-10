"""Helpers for building inline UHF 2.0 markup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class UhfStyleSpan:
    """Character range with inline UHF style attributes."""

    start: int
    end: int
    bold: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False
    fg: int | None = None
    bg: int | None = None


@dataclass(slots=True)
class UhfLinkSpan:
    """Character range with a topic-link target."""

    start: int
    end: int
    target_context: int | None = None
    target_alias: str | None = None
    target_source_file: str | None = None
    target_line: int | None = None


def escape_uhf_text(text: str) -> str:
    """Escape literal bracket characters for UHF inline markup."""
    return text.replace("[", "[[")


def format_uhf_link_target(
    *,
    topic_id: int | None = None,
    alias: str | None = None,
    source_file: str | None = None,
    line: int | None = None,
) -> str:
    """Serialize one UHF link target using the canonical key=value syntax."""
    parts: list[str] = []

    if source_file is not None:
        cleaned_source = source_file.strip()
        if cleaned_source:
            parts.append(f"file={cleaned_source}")

    if topic_id is not None:
        parts.append(f"topic={int(topic_id)}")

    if alias is not None:
        cleaned_alias = alias.strip()
        if cleaned_alias:
            parts.append(f"alias={cleaned_alias}")

    if line is not None:
        normalized_line = int(line)
        if normalized_line > 0:
            parts.append(f"line={normalized_line}")

    if not parts:
        raise ValueError("UHF link target requires at least one of topic_id/alias/file/line")

    return ",".join(parts)


def format_uhf_link(
    label: str,
    *,
    topic_id: int | None = None,
    alias: str | None = None,
    source_file: str | None = None,
    line: int | None = None,
) -> str:
    """Wrap label text into one UHF link tag."""
    target = format_uhf_link_target(
        topic_id=topic_id,
        alias=alias,
        source_file=source_file,
        line=line,
    )
    return f"[link:{target}]{label}[/link]"


def parse_uhf_link_target(raw_target: str) -> dict[str, int | str] | None:
    """Parse one UHF link target in canonical `key=value` syntax."""
    target = str(raw_target or "").strip()
    if not target:
        return None

    result: dict[str, int | str] = {}
    for part in target.split(","):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            return None
        key, value = chunk.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if key == "file":
            result["source_file"] = value
            continue
        if key == "topic":
            try:
                result["topic_id"] = int(value, 10)
            except ValueError:
                return None
            continue
        if key == "alias":
            result["alias"] = value
            continue
        if key == "line":
            try:
                line_number = int(value, 10)
            except ValueError:
                return None
            if line_number > 0:
                result["line"] = line_number
            continue

    return result or None


def render_uhf_line(
    text: str,
    *,
    style_spans: list[UhfStyleSpan] | None = None,
    link_spans: list[UhfLinkSpan] | None = None,
    link_formatter: Callable[[UhfLinkSpan, str], str] | None = None,
) -> str:
    """Render one visible line into UHF inline markup."""
    if not text:
        return ""

    normalized_styles = _normalize_style_spans(style_spans or [], len(text))
    normalized_links = _normalize_link_spans(link_spans or [], len(text))
    boundaries = {0, len(text)}

    for span in normalized_styles:
        boundaries.add(span.start)
        boundaries.add(span.end)
    for span in normalized_links:
        boundaries.add(span.start)
        boundaries.add(span.end)

    rendered_parts: list[str] = []
    ordered = sorted(boundaries)
    for start, end in zip(ordered, ordered[1:]):
        if end <= start:
            continue
        segment = escape_uhf_text(text[start:end])
        if not segment:
            continue
        active_link = _active_link(normalized_links, start, end)
        if active_link is not None and link_formatter is not None:
            segment = link_formatter(active_link, segment)
        active_style = _active_style(normalized_styles, start, end)
        rendered_parts.append(_apply_style_tags(segment, active_style))

    return "".join(rendered_parts)


def _normalize_style_spans(spans: list[UhfStyleSpan], text_len: int) -> list[UhfStyleSpan]:
    normalized: list[UhfStyleSpan] = []
    for span in spans:
        start = max(0, min(text_len, span.start))
        end = max(0, min(text_len, span.end))
        if end <= start:
            continue
        normalized.append(
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
    return normalized


def _normalize_link_spans(spans: list[UhfLinkSpan], text_len: int) -> list[UhfLinkSpan]:
    normalized: list[UhfLinkSpan] = []
    for span in spans:
        start = max(0, min(text_len, span.start))
        end = max(0, min(text_len, span.end))
        if end <= start:
            continue
        normalized.append(
            UhfLinkSpan(
                start=start,
                end=end,
                target_context=span.target_context,
                target_alias=span.target_alias,
                target_source_file=span.target_source_file,
                target_line=span.target_line,
            )
        )
    return normalized


def _active_link(spans: list[UhfLinkSpan], start: int, end: int) -> UhfLinkSpan | None:
    for span in spans:
        if span.start <= start and span.end >= end:
            return span
    return None


def _active_style(spans: list[UhfStyleSpan], start: int, end: int) -> UhfStyleSpan:
    style = UhfStyleSpan(start=start, end=end)
    for span in spans:
        if span.start <= start and span.end >= end:
            style.bold = style.bold or span.bold
            style.italic = style.italic or span.italic
            style.underline = style.underline or span.underline
            style.reverse = style.reverse or span.reverse
            if span.fg is not None:
                style.fg = span.fg
            if span.bg is not None:
                style.bg = span.bg
    return style


def _apply_style_tags(text: str, style: UhfStyleSpan) -> str:
    result = text
    if style.bold:
        result = f"[b]{result}[/b]"
    if style.italic:
        result = f"[i]{result}[/i]"
    if style.underline:
        result = f"[u]{result}[/u]"
    if style.reverse:
        result = f"[r]{result}[/r]"
    if style.fg is not None and style.bg is not None:
        result = f"[color:{style.fg}:{style.bg}]{result}[/color]"
    elif style.fg is not None:
        result = f"[fg:{style.fg}]{result}[/fg]"
    elif style.bg is not None:
        result = f"[bg:{style.bg}]{result}[/bg]"
    return result
