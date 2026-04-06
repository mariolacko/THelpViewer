"""Markdown writer — exports one .md file per help topic."""

from __future__ import annotations

from pathlib import Path

from ..base import HelpDocument, TopicRecord
from ..codepages import build_decode_table, decode_bytes_box_aware


class HelpMarkdownRenderer:
    """Render ``HelpDocument`` topics as individual Markdown files."""

    def __init__(
        self,
        document: HelpDocument,
        display_encoding: str = "cp437",
    ):
        self.document = document
        self.display_encoding = display_encoding
        self.decode_table = (
            None if display_encoding == "utf-8"
            else build_decode_table(display_encoding, "unicode")
        )

    def write_site(self, output_dir: str | Path) -> Path:
        """Write ``index.md`` and one topic file per context id."""
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / "index.md").write_text(
            self.render_index(), encoding="utf-8",
        )

        for topic in self.document.topics:
            filename = f"{topic.context_id:04X}.md"
            (target_dir / filename).write_text(
                self.render_topic(topic), encoding="utf-8",
            )

        return target_dir

    def render_index(self) -> str:
        """Render the alphabetical index as a Markdown document."""
        lines: list[str] = []
        lines.append(f"# {self.document.display_name}\n")
        lines.append(f"Format: {self.document.format_name}  ")
        lines.append(f"Topics: {len(self.document.topics)}  ")
        lines.append(f"Index entries: {len(self.document.index_entries)}\n")

        if self.document.index_entries:
            lines.append("## Index\n")
            for entry in self.document.index_entries:
                label = self._decode_bytes(entry.label).strip()
                if not label:
                    continue
                href = f"{entry.context_id:04X}.md"
                lines.append(f"- [{label}]({href})")

        lines.append("")
        return "\n".join(lines)

    def render_topic(self, topic: TopicRecord) -> str:
        """Render one topic as a Markdown document."""
        title = self._topic_heading(topic)
        lines: list[str] = []
        lines.append(f"# {title}\n")

        context_hex = f"{topic.context_id:04X}"
        lines.append(f"Context: `{context_hex}`\n")

        # Render body as a fenced code block to preserve formatting.
        body_lines = self._render_body_lines(topic)
        if body_lines:
            lines.append("```")
            lines.extend(body_lines)
            lines.append("```")

        # Cross-references section.
        xrefs = self._collect_xrefs(topic)
        if xrefs:
            lines.append("")
            lines.append("## See also\n")
            for ctx_id, label in xrefs:
                href = f"{ctx_id:04X}.md"
                lines.append(f"- [{label}]({href})")

        lines.append("")
        return "\n".join(lines)

    def _render_body_lines(self, topic: TopicRecord) -> list[str]:
        """Decode raw topic lines into plain-text strings."""
        lines: list[str] = []
        for raw_line in topic.raw_lines:
            stripped = raw_line.strip(b" \t")
            if stripped and all(b in (0x05, 0x10) for b in stripped):
                continue
            text = self._decode_bytes(raw_line.replace(b"\x02", b""))
            lines.append(text)
        return lines

    def _collect_xrefs(self, topic: TopicRecord) -> list[tuple[int, str]]:
        """Collect unique cross-reference targets from a topic."""
        seen: set[int] = set()
        xrefs: list[tuple[int, str]] = []
        for kw in topic.positional_keywords:
            if kw.target_context not in seen:
                seen.add(kw.target_context)
                target = self._topic_by_context(kw.target_context)
                label = self._topic_heading(target) if target else f"Context {kw.target_context}"
                xrefs.append((kw.target_context, label))
        for ctx_id in topic.sequential_keywords:
            if ctx_id not in seen:
                seen.add(ctx_id)
                target = self._topic_by_context(ctx_id)
                label = self._topic_heading(target) if target else f"Context {ctx_id}"
                xrefs.append((ctx_id, label))
        return xrefs

    def _topic_heading(self, topic: TopicRecord) -> str:
        """Extract a readable title from the first non-empty text line."""
        box_chars = " \t\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c\u2580\u2584\u2588\u2591\u2592\u2593\u25a0"
        underline_chars = set(box_chars.strip() + "-_=|")
        for raw_line in topic.raw_lines:
            if not raw_line.strip():
                continue
            text = self._decode_bytes(raw_line.replace(b"\x02", b""))
            compact = text.strip()
            if not compact:
                continue
            if all(ch in underline_chars for ch in compact):
                continue
            compact = compact.strip(box_chars).strip()
            if compact:
                return compact
        if topic.index_terms:
            return self._decode_bytes(topic.index_terms[0])
        if topic.names:
            return topic.names[0]
        return f"Context {topic.context_id}"

    def _topic_by_context(self, context_id: int) -> TopicRecord | None:
        for topic in self.document.topics:
            if topic.context_id == context_id:
                return topic
        return None

    def _decode_bytes(self, data: bytes) -> str:
        if self.display_encoding == "utf-8":
            return data.replace(b"\x00", b"").decode("utf-8", errors="replace").replace("\r", "")
        if self.display_encoding == "cp852":
            return decode_bytes_box_aware(data, "cp852")
        return "".join(
            self.decode_table[value]
            for value in data
            if value != 0x00 and value != 0x0D
        )
