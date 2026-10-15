"""Reader helpers for classic Software602 M602 HelpSystem files."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from ..base import HelpDocument, IndexEntry, PositionedKeyword, TopicRecord, ensure_document_index, render_topic_uhf_content
from ..codepages import decode_bytes


M602_HEADER = b"\x1a(c) Software602 HelpSystem"
M602_MARKER = 0x01
M602_LINK = 0x02
M602_TITLE_END = 0xDC
M602_SEPARATOR = 0xDF
M602_INDEX_FOOTER_SIZE = 6
M602_INDEX_ENTRY_SIZE = 8
M602_ERROR_TARGET = 0x0F27  # Native context 9999, in the inline LE target convention.
# Standard DOS client-width projection, not an on-disk field.
M602_DISPLAY_WIDTH = 78
_M602Cell = tuple[int | None, int | None]  # Literal cell or removed byte, hotspot occurrence.
_M602Record = tuple[bytes, list[_M602Cell]]


def is_m602_binary(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like a classic M602 help file."""
    return data.startswith(M602_HEADER)


@dataclass(frozen=True)
class M602IndexEntry:
    raw_target: int
    offset: int
    size: int


def _read_m602_index(data: bytes) -> tuple[int, list[M602IndexEntry]]:
    """Read native (context, absolute offset, byte size) rows and the EOF footer."""
    if not is_m602_binary(data):
        raise ValueError("Input is not a classic Software602 M602 help file.")
    if len(data) < len(M602_HEADER) + M602_INDEX_FOOTER_SIZE:
        raise ValueError("M602 has a truncated binary index footer")
    count = int.from_bytes(data[-6:-4], "little")
    if int.from_bytes(data[-4:], "little") != len(data):
        raise ValueError("M602 binary index footer has an invalid file size")
    offset = len(data) - M602_INDEX_FOOTER_SIZE - count * M602_INDEX_ENTRY_SIZE
    if offset < len(M602_HEADER):
        raise ValueError("M602 binary index count exceeds the file bounds")
    entries = []
    for index in range(count):
        start = offset + index * M602_INDEX_ENTRY_SIZE
        # Native context WORDs are LE; inline operands spell that WORD's high
        # byte first. Preserve the reader/source-HLX raw-inline-ID convention.
        entry = M602IndexEntry(
            int.from_bytes(data[start:start+2], "big"),
            int.from_bytes(data[start+2:start+6], "little"),
            int.from_bytes(data[start+6:start+8], "little"),
        )
        if entry.offset < len(M602_HEADER) or entry.offset + entry.size > offset:
            raise ValueError(f"M602 binary index entry {index} has an invalid topic range")
        entries.append(entry)
    return offset, entries


def normalize_m602_title(text: str) -> str:
    """Normalize Czech/Slovak topic labels for title-based M602 link matching."""
    return re.sub(r"\s+", " ", text.strip()).rstrip(".").casefold().strip('"')


def build_m602_title_candidates(topics: list[TopicRecord], text_encoding: str) -> list[tuple[int, str, set[str]]]:
    """Build `(context_id, title, normalized_aliases)` tuples for M602 topics."""
    candidates: list[tuple[int, str, set[str]]] = []
    for topic in topics:
        raw_title = next((line for line in topic.raw_lines if line.strip()), b"")
        title = decode_m602_bytes(raw_title.replace(b"\x02", b""), text_encoding).strip()
        if not title:
            continue
        candidates.append((topic.context_id, title, _iter_m602_title_keys(title)))
    return candidates


def build_m602_binary_target_context_map(
    data: bytes,
    parsed_topics: list[dict[str, object]],
    tail_offset: int | None = None,
) -> dict[int, int]:
    """Map native directory ranges to physical-topic contexts used by source HLX."""
    index_offset, entries = _read_m602_index(data)
    if tail_offset is not None and tail_offset != index_offset - len(M602_HEADER):
        raise ValueError("M602 binary index offset disagrees with its footer")
    topic_ranges = {
        (int(topic["start_offset"]) + len(M602_HEADER),
         int(topic["end_offset"]) + len(M602_HEADER)): int(topic["context_id"])
        for topic in parsed_topics
    }
    resolved: dict[int, int] = {}
    for entry in entries:
        target_context = topic_ranges.get((entry.offset, entry.offset + entry.size))
        if target_context is None:
            raise ValueError(f"M602 binary index target {entry.raw_target:04X} has no parsed topic")
        # The original lookup scans forward and returns its first match.
        resolved.setdefault(entry.raw_target, target_context)

    return resolved


def collect_m602_link_occurrences(
    topics: list[TopicRecord],
    text_encoding: str,
) -> list[tuple[int, int, str]]:
    """Collect `(source_context, raw_target, label)` tuples from M602 topic bodies."""
    occurrences: list[tuple[int, int, str]] = []
    for topic in topics:
        for keyword in topic.positional_keywords:
            row = topic.raw_lines[keyword.line - 1]
            label = decode_m602_bytes(row[keyword.first_column - 1:keyword.last_column], text_encoding).strip()
            occurrences.append((topic.context_id, keyword.target_context, label))
    return occurrences


def build_m602_target_context_map(
    topics: list[TopicRecord],
    occurrences: list[tuple[int, int, str]],
    text_encoding: str,
) -> dict[int, int]:
    """Resolve raw M602 link ids from labels and topic titles stored in the same document."""
    alias_map: dict[str, set[int]] = defaultdict(set)
    for context_id, _title, aliases in build_m602_title_candidates(topics, text_encoding=text_encoding):
        for alias in aliases:
            alias_map[alias].add(context_id)

    refs_by_target: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for source_context, raw_target, label in occurrences:
        refs_by_target[raw_target].append((source_context, label))

    resolved: dict[int, int] = {}
    for raw_target, refs in refs_by_target.items():
        candidate_matches: dict[int, set[str]] = defaultdict(set)
        for _source_context, label in refs:
            for key in _iter_m602_label_keys(label):
                for context_id in alias_map.get(key, ()):
                    candidate_matches[context_id].add(key)

        if not candidate_matches:
            continue

        resolved[raw_target] = min(
            candidate_matches,
            key=lambda context_id: (
                -max(len(key) for key in candidate_matches[context_id]),
                sum(abs(context_id - source_context) for source_context, _label in refs),
                min(abs(context_id - source_context) for source_context, _label in refs),
                context_id,
            ),
        )

    return resolved


def _iter_m602_title_keys(title: str) -> set[str]:
    """Build normalized aliases from one visible topic title."""
    keys = {normalize_m602_title(title)}
    title_without_parens = re.sub(r"\s*\([^)]*\)$", "", title).rstrip()
    keys.add(normalize_m602_title(title_without_parens))
    return {key for key in keys if key}


def _iter_m602_label_keys(label: str) -> set[str]:
    """Build normalized aliases from one inline hotspot label."""
    keys = {normalize_m602_title(label)}
    after_arrow = re.sub(r"^.*->\s*", "", label)
    keys.add(normalize_m602_title(after_arrow))
    return {key for key in keys if key}


def decode_m602_bytes(data: bytes, text_encoding: str) -> str:
    """Decode M602 text from either UTF-8 source dumps or DOS single-byte bytes."""
    if text_encoding == "utf-8":
        return data.decode("utf-8", errors="replace")
    # These are literal screen cells, not browser terminal controls. Decode
    # one cell at a time so NUL and internal CR do not disappear/move a row.
    literal = {0: " ", 9: "○", 10: "◙", 13: "♪", 127: "⌂"}
    return "".join(literal[value] if value in literal else decode_bytes(bytes([value]), text_encoding)
                   for value in data)


def _layout_m602_records(
    records: list[_M602Record], targets: list[int], width: int,
) -> tuple[list[bytes], list[PositionedKeyword]]:
    """Native raw-byte short-string wrapping, with bounded link-cell projection."""
    rows: list[bytes] = []
    keywords: list[PositionedKeyword] = []

    def emit(cells: list[_M602Cell]) -> None:
        row = bytearray()
        active = None
        start = 0

        def flush() -> None:
            if active is not None:
                keywords.append(PositionedKeyword(target_context=targets[active],
                                                  line=len(rows) + 1,
                                                  first_column=start + 1,
                                                  last_column=len(row)))

        for value, link in cells:
            if link != active:
                flush()
                active, start = link, len(row)
            if value is not None:
                row.append(value)
        flush()
        if row.startswith(b"\x01"):
            row[0] = 0x20
        rows.append(bytes(row))

    index = 0
    while index < len(records):
        raw, cells = records[index]
        index += 1
        if raw.startswith(b"\x01"):
            emit(cells)
            continue
        while index < len(records) and not records[index][0].startswith(b"\x01"):
            following, next_cells = records[index]
            index += 1
            raw += b" " + following
            cells = cells + [(0x20, None)] + next_cells
            while len(raw) > width:
                # Original indices are one-based; include the cut's space.
                cut = raw.rfind(b" ", 0, width) + 1
                if not cut:
                    next_space = raw.find(b" ", width - 1)
                    cut = next_space + 1 if next_space >= 0 else len(raw)
                emit(cells[:cut])
                raw, cells = raw[cut:], cells[cut:]
        emit(cells)
    return rows, keywords


class M602BinaryParser:
    """Parse the encrypted M602 record stream into normalized topic data."""

    def __init__(self, data: bytes, width: int = M602_DISPLAY_WIDTH):
        if not isinstance(width, int) or not 1 <= width <= 255:
            raise ValueError("M602 display width must be between 1 and 255 cells")
        self.data = data
        self.width = width
        self.pos = len(M602_HEADER)
        self.current_topic_id = 0
        self.current_records: list[_M602Record] = []
        self.current_title: bytes | None = None
        self.current_keywords: list[int] = []
        self.current_start_offset: int | None = None
        self.topics: list[dict[str, object]] = []
        index_offset, self.index_entries = _read_m602_index(data)
        self.binary_index_offset = index_offset - len(M602_HEADER)
        self.binary_index_entry_count = len(self.index_entries)
        self.topic_end = self.pos

    def parse(self) -> list[dict[str, object]]:
        """Decode each distinct native range, bounded by its stored byte size."""
        self.topics = []
        self.current_records, self.current_keywords = [], []
        self.current_title = None
        for start, size in sorted({(entry.offset, entry.size) for entry in self.index_entries}):
            self.pos = start
            self.topic_end = start + size
            self.current_topic_id = len(self.topics) + 1
            self.current_start_offset = start - len(M602_HEADER)
            first_record = True
            while self.pos < self.topic_end:
                record_offset, raw_buf, visible_len = self._read_record()
                if first_record and self._is_title(raw_buf, visible_len):
                    self.current_title = raw_buf[1:visible_len - 1].strip()
                try:
                    raw = raw_buf[:visible_len]
                    self.current_records.append((raw, self._decode_body_record(raw)))
                except ValueError as error:
                    raise ValueError(f"M602 topic {self.current_topic_id}, record at "
                                     f"{record_offset + len(M602_HEADER):X}h: {error}") from error
                first_record = False
            self._flush_topic()
        return self.topics

    def _read_record(self) -> tuple[int, bytes, int]:
        """Read one complete XOR-decoded Pascal string with its single CR suffix."""
        record_offset = self.pos - len(M602_HEADER)
        raw_len = self.data[self.pos] ^ 0xFA
        self.pos += 1
        if raw_len == 0:
            raise ValueError(f"M602 topic {self.current_topic_id} has a zero-length record")
        if self.pos + raw_len > self.topic_end:
            raise ValueError(f"M602 topic {self.current_topic_id} has a truncated record "
                             f"at {record_offset + len(M602_HEADER):X}h")
        raw_buf = bytes(value ^ 0xFA for value in self.data[self.pos:self.pos + raw_len])
        self.pos += raw_len
        if raw_buf[-1] != 0x0D:
            raise ValueError(f"M602 topic {self.current_topic_id} has a record without a CR terminator "
                             f"at {record_offset + len(M602_HEADER):X}h")
        return record_offset, raw_buf, len(raw_buf) - 1

    def _flush_topic(self) -> None:
        if not self.current_topic_id:
            return
        rows, keywords = _layout_m602_records(self.current_records, self.current_keywords, self.width)
        title = self.current_title
        if title is None:
            title = rows[0].strip() if rows else f"Topic {self.current_topic_id}".encode("latin-1")
        self.topics.append(
            {
                "context_id": self.current_topic_id,
                "start_offset": self.current_start_offset,
                "end_offset": self.topic_end - len(M602_HEADER),
                "title": title,
                "raw_lines": rows,
                "positional_keywords": keywords,
                "raw_link_targets": list(self.current_keywords),
            }
        )
        self.current_topic_id = 0
        self.current_start_offset = None
        self.current_records = []
        self.current_title = None
        self.current_keywords = []

    def _decode_body_record(self, raw_buf: bytes) -> list[_M602Cell]:
        """Map source bytes to literal cells and source hotspot occurrences."""
        cells: list[_M602Cell] = []
        raw_len = len(raw_buf)
        index = 0
        while index < raw_len:
            value = raw_buf[index]
            if value == M602_LINK:
                end = raw_buf.find(b"\x02", index + 1)
                if end < 0:
                    raise ValueError("unterminated hyperlink label")
                if end + 3 > raw_len:
                    raise ValueError("truncated hyperlink target")
                context_id = int.from_bytes(raw_buf[end + 1:end + 3], "little")
                occurrence = len(self.current_keywords)
                self.current_keywords.append(context_id)
                cells.append((None, occurrence))
                cells.extend((0x20 if byte == ord("_") else byte, occurrence)
                             for byte in raw_buf[index + 1:end])
                cells.extend([(None, occurrence), (None, None), (None, None)])
                index = end + 3
                continue
            cells.append((value, None))
            index += 1
        return cells

    @staticmethod
    def _is_title(buf: bytes, visible_len: int) -> bool:
        if visible_len <= 2 or buf[0] != M602_MARKER:
            return False
        if M602_LINK in buf[:visible_len] or buf[visible_len - 1] != M602_TITLE_END:
            return False
        return M602_SEPARATOR not in buf[1:visible_len - 1]


class M602Reader:
    def __init__(self, data: bytes = b"", from_cp: str | None = None,
                 source_name: str = "", source_path=None):
        self.source_name = source_name
        self.source_path = source_path
        self.text_encoding = from_cp or "kamenicky"

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read one encrypted M602 help file."""
        if not is_m602_binary(data):
            raise ValueError("Input is not a classic Software602 M602 help file.")
        parser = M602BinaryParser(data)
        parsed_topics = parser.parse()
        exact_target_map = build_m602_binary_target_context_map(
            data,
            parsed_topics,
            tail_offset=parser.binary_index_offset,
        )
        topics = [
            TopicRecord(
                context_id=topic["context_id"],
                raw_lines=list(topic["raw_lines"]),
                positional_keywords=list(topic["positional_keywords"]),
                index_terms=[topic["title"]],
            )
            for topic in parsed_topics
        ]
        missing_targets = set()
        for topic in topics:
            for keyword in topic.positional_keywords:
                raw_target = keyword.target_context
                target = exact_target_map.get(raw_target)
                if target is None:
                    missing_targets.add(raw_target)
                    target = exact_target_map.get(M602_ERROR_TARGET)
                if target is None:
                    raise ValueError(f"M602 topic {topic.context_id} references absent target "
                                     f"{raw_target:04X}h without a native error context")
                keyword.target_context = target
        topic_ids = {topic.context_id for topic in topics}
        for topic in topics:
            topic.uhf_content = render_topic_uhf_content(
                topic,
                decode_bytes=lambda raw: decode_m602_bytes(raw, self.text_encoding),
                topic_ids=topic_ids,
            )
        index_entries = [
            IndexEntry(label=topic["title"], context_id=topic["context_id"])
            for topic in parsed_topics
        ]
        return ensure_document_index(HelpDocument(
            format_name="m602",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata={
                "stamp": "(c) Software602 HelpSystem",
                "display_width": M602_DISPLAY_WIDTH,
                "encrypted": True,
                "text_encoding": self.text_encoding,
                "link_target_kind": "m602_raw_link_code",
                "link_targets_resolved": True,
                "link_targets_exact_count": len(exact_target_map),
                "binary_index_entry_count": parser.binary_index_entry_count,
                "link_target_resolution": "binary_index_error_context" if missing_targets else "binary_tail_exact",
                "missing_raw_link_targets": sorted(missing_targets),
            },
            binary_data=data,
        ))


# Manifest/export entry point.
M602HelpReader = M602Reader
