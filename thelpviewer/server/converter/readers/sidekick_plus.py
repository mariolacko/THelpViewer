"""Sidekick Plus paragraph directories, paginated screens and scoped hotspots."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from ..base import ContentNode, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord, build_directional_nav_items
from ..codepages import decode_bytes
from ..uhf_markup import UhfLinkSpan, UhfStyleSpan, format_uhf_link, render_uhf_line


_STAMP = b"Borland Help\x00\x01"
_HEADER_SIZE = 2 + len(_STAMP)
_GROUP_TABLE_END = 0x410
_CONTEXT_TABLE_SIZE = 256 * 6
_UNUSED = b"\xff" * 6
_CONTINUATION_START = 1 << 24


def is_sidekick_plus_binary(data: bytes) -> bool:
    # The original Help module compares the initial WORD with the executable's
    # configured pairing tag, not with a universal magic value of 9B00h.
    return data[2:_HEADER_SIZE] == _STAMP


@dataclass(frozen=True, slots=True)
class _Screen:
    group: int
    slot: int
    rows: int
    columns: int
    offset: int
    size: int
    title: bytes
    references: tuple[tuple[int, int, int], ...]
    pages: tuple[bytes, ...]

    @property
    def context_id(self) -> int:
        return (self.group << 8) | self.slot


def _screens(data: bytes, common_group: int | None = None
             ) -> tuple[list[int], list[_Screen], list[dict[str, int]]]:
    if not is_sidekick_plus_binary(data) or len(data) < _GROUP_TABLE_END:
        raise ValueError("Not a supported Sidekick Plus help directory.")
    groups: list[int] = []
    bases: list[int] = []
    for position in range(_HEADER_SIZE, _GROUP_TABLE_END, 4):
        paragraph, group = struct.unpack_from("<HH", data, position)
        if paragraph == 0xFFFF:
            break
        base = paragraph * 16
        if group in groups or base < _GROUP_TABLE_END or base + _CONTEXT_TABLE_SIZE > len(data):
            raise ValueError("Invalid Sidekick Plus group directory.")
        if bases and base < bases[-1] + _CONTEXT_TABLE_SIZE:
            raise ValueError("Overlapping Sidekick Plus group directories.")
        groups.append(group)
        bases.append(base)
    else:
        raise ValueError("Unterminated Sidekick Plus group directory.")
    if not groups:
        raise ValueError("Empty Sidekick Plus group directory.")
    # Standalone conversion uses the first group as its common-help binding,
    # as in the inspected distribution. A runtime can supply another binding;
    # selector zero is not an arbitrary group-directory ordinal.
    common_group = groups[0] if common_group is None else common_group
    if type(common_group) is not int or common_group not in groups:
        raise ValueError("Sidekick Plus common help group is absent from the directory.")

    screens: list[_Screen] = []
    redirects: list[dict[str, int]] = []
    for number, (group, base) in enumerate(zip(groups, bases)):
        limit = bases[number + 1] if number + 1 < len(bases) else len(data)
        ranges: set[tuple[int, int]] = set()
        for slot in range(256):
            descriptor = data[base + slot * 6:base + (slot + 1) * 6]
            # Native Help tests the dimension WORD before consulting offsets.
            if descriptor[:2] == _UNUSED[:2]:
                continue
            rows, columns, offset, size = struct.unpack("<BBHH", descriptor)
            # Native Help reloads its default paragraph and the low offset
            # byte as a slot. It does not interpret this as a text pointer.
            if offset >> 8 == 0xFF:
                redirects.append({"context_id": (group << 8) | slot,
                                  "target_context": (common_group << 8) | (offset & 0xFF),
                                  "descriptor": int.from_bytes(descriptor, "little")})
                continue
            start, end = base + offset, base + offset + size
            if not (1 <= rows <= 25 and 1 <= columns <= 80 and size > 0
                    and offset >= _CONTEXT_TABLE_SIZE and end <= limit):
                raise ValueError(f"Invalid Sidekick Plus screen descriptor for {group}:{slot}.")
            ranges.add((start, end))
            raw = data[start:end]
            position = 0
            references = []
            while raw[position:position + 3] != b"\xff\xff\xff":
                if position + 3 > len(raw):
                    raise ValueError("Unterminated Sidekick Plus hotspot table.")
                page, bank, target = raw[position:position + 3]
                if not page:
                    raise ValueError("Invalid Sidekick Plus hotspot page.")
                references.append((page, group if bank else common_group, target))
                position += 3
            try:
                body, title, tail = raw[position + 3:].rsplit(b"\x00", 2)
            except ValueError as exc:
                raise ValueError("Unterminated Sidekick Plus screen/title.") from exc
            if tail or b"\x00" in title or not title.strip(b" "):
                raise ValueError("Invalid Sidekick Plus screen title.")
            pages = tuple(body.split(b"\xff\xff"))
            if any(page > len(pages) for page, _group, _slot in references):
                raise ValueError("Sidekick Plus hotspot refers to a nonexistent page.")
            screens.append(_Screen(group, slot, rows, columns, start, size, title, tuple(references), pages))
        previous_end = base + _CONTEXT_TABLE_SIZE
        for start, end in sorted(ranges):
            if start < previous_end:
                raise ValueError("Overlapping Sidekick Plus screen records.")
            previous_end = end
    if not screens:
        raise ValueError("Sidekick Plus contains no text screens.")
    return groups, screens, redirects


def _text(raw: bytes) -> str:
    # A raw-character escape writes a VGA cell, including low-byte glyphs.
    return decode_bytes(raw.replace(b"\x00", b" "), "cp437").replace("\t", "○").replace("\n", "◙").replace("\r", "♪").replace("\x7f", "⌂")


def _page(raw: bytes, screen: _Screen, references: list[tuple[int, int]]
          ) -> tuple[list[bytes], list[str]]:
    lines: list[bytes] = []
    content: list[str] = []
    line = bytearray()
    styles: list[UhfStyleSpan] = []
    links: list[UhfLinkSpan] = []
    start = 0
    reference = 0
    target: int | None = None
    attribute = 1

    def finish_span() -> None:
        nonlocal start
        if len(line) > start:
            styles.append(UhfStyleSpan(start, len(line), bold=attribute == 2,
                                       underline=attribute == 3, reverse=attribute == 4))
            if target is not None:
                links.append(UhfLinkSpan(start, len(line), target))
        start = len(line)

    def finish_line() -> None:
        nonlocal start, attribute, target
        finish_span()
        if len(line) > screen.columns:
            raise ValueError(f"Sidekick Plus line exceeds its declared width in {screen.context_id}.")
        # decode_bytes intentionally drops NULs. An escaped NUL is a blank VGA
        # cell; replace it before decoding so hotspot columns remain exact.
        visible = bytes(line).replace(b"\x00", b" ")
        lines.append(visible)
        content.append(render_uhf_line(_text(visible),
                                      style_spans=styles, link_spans=links,
                                      link_formatter=lambda span, label: format_uhf_link(label, topic_id=span.target_context)))
        line.clear()
        styles.clear()
        links.clear()
        start = 0
        # Help calls the native string printer separately for each row. It
        # starts each call with the window's normal category, not the prior row.
        attribute = 1
        target = None

    position = 0
    while position < len(raw):
        value = raw[position]
        position += 1
        if value == 0xFF:
            if position == len(raw):
                raise ValueError("Truncated Sidekick Plus raw-character escape.")
            line.append(raw[position])
            position += 1
        elif 1 <= value <= 5:
            finish_span()
            attribute = value
            target = None
            if attribute == 5:
                if reference >= len(references):
                    raise ValueError("Sidekick Plus hotspot has no table entry.")
                group, slot = references[reference]
                target = (group << 8) | slot
                reference += 1
        elif value == 6:
            # Native toggle swaps normal/emphasis and key/selected categories;
            # a hotspot's category is left unchanged.
            if attribute < 5:
                finish_span()
                attribute = ((attribute - 1) ^ 1) + 1
        elif value == 13:
            finish_line()
        elif value == 0:
            raise ValueError("Unexpected Sidekick Plus screen terminator.")
        elif value == 0xFE:
            raise ValueError("Unsupported Sidekick Plus embedded runtime-string reference.")
        else:
            line.append(value)
    finish_line()
    if len(lines) > screen.rows or reference != len(references):
        raise ValueError("Invalid Sidekick Plus page height or hotspot boundaries.")
    return lines, content


class SidekickPlusReader(HelpReaderBase):
    def __init__(self, source_name: str = "input.hlp", text_encoding: str = "latin1",
                 source_path=None, *, common_group: int | None = None):
        super().__init__(source_name=source_name, text_encoding=text_encoding, source_path=source_path)
        self.common_group = common_group

    def read_bytes(self, data: bytes) -> HelpDocument:
        groups, screens, redirects = _screens(data, self.common_group)
        topics: list[TopicRecord] = []
        index: list[IndexEntry] = []
        contents: list[ContentNode] = []
        descriptors: list[dict[str, object]] = []
        owners: dict[tuple[int, int], TopicRecord] = {}
        group_nodes: dict[int, ContentNode] = {}
        next_page_id = _CONTINUATION_START
        for screen in screens:
            identity = (screen.offset, screen.size)
            if identity in owners:
                owners[identity].alias_contexts.append(screen.context_id)
                continue
            page_ids = [screen.context_id, *range(next_page_id, next_page_id + len(screen.pages) - 1)]
            next_page_id += len(screen.pages) - 1
            title = _text(screen.title).strip(" ")
            index.append(IndexEntry(screen.title.strip(b" "), screen.context_id))
            node = ContentNode(label=title, topic_id=screen.context_id)
            if screen.group not in group_nodes:
                group_node = ContentNode(label=title, topic_id=screen.context_id)
                group_nodes[screen.group] = group_node
                contents.append(group_node)
            group_nodes[screen.group].children.append(node)
            for number, (page_id, raw) in enumerate(zip(page_ids, screen.pages)):
                references = [(group, slot) for page, group, slot in screen.references if page == number + 1]
                lines, content = _page(raw, screen, references)
                topic = TopicRecord(context_id=page_id, raw_lines=lines, uhf_content=content,
                                    names=[title if not number else f"{title} — Page {number + 1}"],
                                    prev_context=page_ids[number - 1] if number else None,
                                    next_context=page_ids[number + 1] if number + 1 < len(page_ids) else None)
                topic.nav_items = build_directional_nav_items(topic)
                topics.append(topic)
                if number:
                    node.children.append(ContentNode(label=f"Page {number + 1}", topic_id=page_id))
                else:
                    owners[identity] = topic
            descriptors.append({"context_id": screen.context_id, "group": screen.group, "slot": screen.slot,
                                "offset": screen.offset, "size": screen.size, "rows": screen.rows,
                                "columns": screen.columns, "page_ids": page_ids})
        owners_by_context = {context: topic for topic in topics for context in [topic.context_id, *topic.alias_contexts]}
        targets = {redirect["context_id"]: redirect["target_context"] for redirect in redirects}
        for context_id in targets:
            target = context_id
            seen: set[int] = set()
            while target in targets:
                if target in seen:
                    raise ValueError("Cyclic Sidekick Plus context redirection.")
                seen.add(target)
                target = targets[target]
            if target in owners_by_context:
                owners_by_context[target].alias_contexts.append(context_id)
        existing = {context for topic in topics for context in [topic.context_id, *topic.alias_contexts]}
        unresolved = sorted({(group << 8) | slot for screen in screens for _page, group, slot in screen.references} - existing)
        topics[0].is_help_contents = True
        return HelpDocument(format_name="sidekick-plus", source_name=self.source_name, topics=topics,
                            index_entries=index, contents=contents, metadata={
                                "title": "SideKick Plus Help", "text_encoding": "cp437",
                                "metadata_already_decoded": True, "help_contents_topic_id": topics[0].context_id,
                                "display_width": max(screen.columns for screen in screens),
                                "height": max(screen.rows for screen in screens),
                                "sidekick_plus_groups": groups, "sidekick_plus_contexts": descriptors,
                                "sidekick_plus_common_group": groups[0] if self.common_group is None else self.common_group,
                                "sidekick_plus_version_tag": int.from_bytes(data[:2], "little"),
                                "sidekick_plus_redirects": redirects, "unresolved_contexts": {"links": unresolved},
                                "transport_metadata_keys": ["sidekick_plus_groups", "sidekick_plus_contexts",
                                                            "sidekick_plus_common_group", "sidekick_plus_version_tag",
                                                            "sidekick_plus_redirects", "unresolved_contexts"],
                            })
