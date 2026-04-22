"""Reader helpers for classic Software602 M602 HelpSystem files."""

from __future__ import annotations

from collections import defaultdict
import re

from ..base import HelpDocument, HelpReaderBase, IndexEntry, TopicRecord, ensure_document_index
from ..codepages import decode_bytes, guess_display_encoding


M602_HEADER = b"\x1a(c) Software602 HelpSystem"
M602_MARKER = 0x01
M602_LINK = 0x02
M602_TITLE_END = 0xDC
M602_SEPARATOR = 0xDF
M602_INDEX_HEADER_SIZE = 6
M602_INDEX_ENTRY_SIZE = 8


def is_m602_binary(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like a classic M602 help file."""
    return data.startswith(M602_HEADER)


def detect_m602_binary_index_offset(data: bytes) -> tuple[int | None, int | None, int | None]:
    """Return `(body_offset, entry_count, root_count)` for the unencrypted tail.

    Observed classic M602 files end with an 8-byte sentinel whose last 4 bytes
    equal the absolute EOF offset and whose middle 2 bytes equal the total
    number of 8-byte index entries stored after the 6-byte tail header.
    """
    minimum_size = len(M602_HEADER) + M602_INDEX_HEADER_SIZE + M602_INDEX_ENTRY_SIZE
    if len(data) < minimum_size:
        return None, None, None

    last = data[-M602_INDEX_ENTRY_SIZE:]
    entry_count = last[2] | (last[3] << 8)
    encoded_eof = (
        (last[4] | (last[5] << 8))
        | ((last[6] | (last[7] << 8)) << 16)
    )
    if entry_count <= 0 or encoded_eof != len(data):
        return None, None, None

    tail_size = M602_INDEX_HEADER_SIZE + (entry_count * M602_INDEX_ENTRY_SIZE)
    tail_file_offset = len(data) - tail_size
    if tail_file_offset < len(M602_HEADER):
        return None, None, None

    root_count = data[tail_file_offset]
    if root_count <= 0 or root_count > entry_count:
        return None, None, None

    return tail_file_offset - len(M602_HEADER), entry_count, root_count


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


def resolve_m602_label_context(
    label: str,
    candidates: list[tuple[int, str, set[str]]],
    current_context: int | None = None,
) -> int | None:
    """Resolve one M602 hotspot label when it matches exactly one topic title."""
    matches = [
        context_id
        for context_id, _title, aliases in candidates
        if any(key in aliases for key in _iter_m602_label_keys(label))
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1 and current_context is not None:
        for context_id in matches:
            if context_id != current_context:
                return context_id
    return None


def build_m602_binary_target_context_map(
    data: bytes,
    parsed_topics: list[dict[str, object]],
    tail_offset: int | None = None,
) -> dict[int, int]:
    """Decode the unencrypted binary tail and map raw targets to topic contexts."""
    if not parsed_topics:
        return {}

    if tail_offset is None or tail_offset < 0:
        tail_offset, _entry_count, _root_count = detect_m602_binary_index_offset(data)
    if tail_offset is None or tail_offset < 0:
        return {}

    tail = data[len(M602_HEADER) + tail_offset:]
    if len(tail) < M602_INDEX_HEADER_SIZE:
        return {}
    if (len(tail) - M602_INDEX_HEADER_SIZE) % M602_INDEX_ENTRY_SIZE:
        return {}

    topic_offsets = {
        int(topic["start_offset"]) + len(M602_HEADER): int(topic["context_id"])
        for topic in parsed_topics
        if isinstance(topic.get("start_offset"), int) and isinstance(topic.get("context_id"), int)
    }
    resolved: dict[int, int] = {}
    expected_previous_offset = len(M602_HEADER)
    entries = (len(tail) - M602_INDEX_HEADER_SIZE) // M602_INDEX_ENTRY_SIZE

    for entry_index in range(entries):
        entry_offset = M602_INDEX_HEADER_SIZE + (entry_index * M602_INDEX_ENTRY_SIZE)
        entry = tail[entry_offset:entry_offset + M602_INDEX_ENTRY_SIZE]
        delta = entry[0] | (entry[1] << 8)
        raw_target_swapped = entry[2] | (entry[3] << 8)
        absolute_offset = (entry[4] | (entry[5] << 8)) | ((entry[6] | (entry[7] << 8)) << 16)

        # The index stores the raw link id with bytes swapped compared to the
        # in-band body encoding `$02 ... $02 lo hi`.
        raw_target = ((raw_target_swapped & 0x00FF) << 8) | (raw_target_swapped >> 8)
        target_context = topic_offsets.get(absolute_offset)
        if target_context is None:
            continue

        # All observed samples store the distance from the previous topic start
        # alongside the absolute file offset. Keep the check soft so unknown
        # variants can still fall back to title-based matching.
        if absolute_offset - expected_previous_offset != delta:
            expected_previous_offset = absolute_offset
            continue
        expected_previous_offset = absolute_offset
        resolved[raw_target] = target_context

    return resolved


def improve_m602_topic_links(
    topics: list[TopicRecord],
    text_encoding: str,
    exact_targets: dict[int, int] | None = None,
) -> dict[int, int]:
    """Resolve M602 raw 16-bit link ids, preferring the exact binary tail map."""
    resolved_targets = dict(exact_targets or {})
    unresolved_targets = {
        raw_target
        for topic in topics
        for raw_target in topic.sequential_keywords
        if raw_target not in resolved_targets
    }
    if unresolved_targets:
        occurrences = [
            occurrence
            for occurrence in collect_m602_link_occurrences(topics, text_encoding=text_encoding)
            if occurrence[1] in unresolved_targets
        ]
        heuristic_targets = build_m602_target_context_map(
            topics,
            occurrences,
            text_encoding=text_encoding,
        )
        for raw_target, context_id in heuristic_targets.items():
            resolved_targets.setdefault(raw_target, context_id)

    for topic in topics:
        topic.sequential_keywords = [
            resolved_targets.get(raw_target, raw_target)
            for raw_target in topic.sequential_keywords
        ]

    return resolved_targets


def collect_m602_link_occurrences(
    topics: list[TopicRecord],
    text_encoding: str,
) -> list[tuple[int, int, str]]:
    """Collect `(source_context, raw_target, label)` tuples from M602 topic bodies."""
    occurrences: list[tuple[int, int, str]] = []
    for topic in topics:
        keyword_index = 0
        for raw_line in topic.raw_lines:
            parts = raw_line.split(b"\x02")
            for part_index in range(1, len(parts), 2):
                if keyword_index >= len(topic.sequential_keywords):
                    break
                label = decode_m602_bytes(parts[part_index], text_encoding).strip()
                occurrences.append((topic.context_id, topic.sequential_keywords[keyword_index], label))
                keyword_index += 1
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
    return decode_bytes(data, text_encoding)


class M602BinaryParser:
    """Parse the encrypted M602 record stream into normalized topic data."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = len(M602_HEADER)
        self.current_topic_id = 0
        self.current_lines: list[bytes] = []
        self.current_keywords: list[int] = []
        self.current_start_offset: int | None = None
        self.topics: list[dict[str, object]] = []
        (
            self.binary_index_offset,
            self.binary_index_entry_count,
            self.binary_index_root_count,
        ) = detect_m602_binary_index_offset(data)

    def parse(self) -> list[dict[str, object]]:
        """Parse the full encrypted record stream into topic dictionaries."""
        while True:
            if self.binary_index_offset is not None and self.pos - len(M602_HEADER) >= self.binary_index_offset:
                break
            record = self._read_record()
            if record is None:
                break
            record_offset, raw_buf, visible_len = record
            if visible_len == 0:
                if self.current_topic_id:
                    self.current_lines.append(b"")
                continue
            if self._is_binary_index(raw_buf, visible_len):
                self.binary_index_offset = record_offset
                break
            if self._is_title(raw_buf, visible_len):
                self._start_topic(record_offset, raw_buf[1:visible_len - 1])
                continue
            if not self.current_topic_id:
                continue
            if self._is_separator(raw_buf, visible_len):
                self.current_lines.append(raw_buf[1:visible_len])
                continue
            self.current_lines.extend(self._decode_body_record(raw_buf, visible_len))

        self._flush_topic()
        self._finalize_topic_offsets()
        return self.topics

    def _read_record(self) -> tuple[int, bytes, int] | None:
        """Read one XOR-decoded record and strip trailing CR bytes for parsing."""
        if self.pos >= len(self.data):
            return None
        record_offset = self.pos - len(M602_HEADER)
        raw_len = self.data[self.pos] ^ 0xFA
        self.pos += 1
        if raw_len == 0:
            return record_offset, b"", 0
        if self.pos + raw_len > len(self.data):
            return None
        raw_buf = bytes(value ^ 0xFA for value in self.data[self.pos:self.pos + raw_len])
        self.pos += raw_len
        visible_len = len(raw_buf)
        while visible_len > 0 and raw_buf[visible_len - 1] == 0x0D:
            visible_len -= 1
        return record_offset, raw_buf, visible_len

    def _start_topic(self, record_offset: int, title_bytes: bytes) -> None:
        self._flush_topic()
        self.current_topic_id = len(self.topics) + 1
        self.current_start_offset = record_offset
        self.current_lines = [title_bytes]
        self.current_keywords = []

    def _flush_topic(self) -> None:
        if not self.current_topic_id:
            return
        title = self.current_lines[0].strip() if self.current_lines else f"Topic {self.current_topic_id}".encode("latin-1")
        self.topics.append(
            {
                "context_id": self.current_topic_id,
                "start_offset": self.current_start_offset,
                "end_offset": None,
                "title": title,
                "raw_lines": list(self.current_lines),
                "raw_link_targets": list(self.current_keywords),
                "sequential_keywords": list(self.current_keywords),
            }
        )
        if len(self.topics) >= 2 and self.current_start_offset is not None:
            self.topics[-2]["end_offset"] = self.current_start_offset
        self.current_topic_id = 0
        self.current_start_offset = None
        self.current_lines = []
        self.current_keywords = []

    def _decode_body_record(self, raw_buf: bytes, visible_len: int) -> list[bytes]:
        """Decode one body record and translate inline M602 links to `0x02` markers."""
        lines: list[bytes] = []
        line = bytearray()
        raw_len = len(raw_buf)
        index = 0

        if visible_len > 0 and raw_buf[0] == M602_MARKER:
            index = 1

        while index < visible_len:
            value = raw_buf[index]
            if value == M602_LINK:
                index += 1
                link_bytes = bytearray()
                while index < raw_len and raw_buf[index] != M602_LINK:
                    link_bytes.append(0x20 if raw_buf[index] == ord("_") else raw_buf[index])
                    index += 1
                if index < raw_len and raw_buf[index] == M602_LINK:
                    index += 1
                    if index + 1 < raw_len:
                        context_id = raw_buf[index] | (raw_buf[index + 1] << 8)
                        self.current_keywords.append(context_id)
                        index += 2
                    line.append(0x02)
                    line.extend(bytes(link_bytes).rstrip(b" "))
                    line.append(0x02)
                continue
            if value == 0x0D:
                lines.append(bytes(line))
                line = bytearray()
                index += 1
                continue
            line.append(value)
            index += 1

        lines.append(bytes(line))
        return lines

    @staticmethod
    def _is_title(buf: bytes, visible_len: int) -> bool:
        if visible_len <= 2 or buf[0] != M602_MARKER:
            return False
        if buf[1] == M602_LINK or buf[visible_len - 1] != M602_TITLE_END:
            return False
        return M602_SEPARATOR not in buf[1:visible_len - 1]

    @staticmethod
    def _is_separator(buf: bytes, visible_len: int) -> bool:
        if visible_len <= 1 or buf[0] != M602_MARKER:
            return False
        return M602_SEPARATOR in buf[1:visible_len]

    @staticmethod
    def _is_binary_index(buf: bytes, visible_len: int) -> bool:
        """M602 appends a binary tail which is visibly dominated by XOR key bytes."""
        if visible_len <= 10:
            return False
        fa_count = sum(value == 0xFA for value in buf[:visible_len])
        return fa_count * 8 > visible_len

    def _finalize_topic_offsets(self) -> None:
        """Close the last topic span so debugging tools can inspect record offsets."""
        if self.topics:
            self.topics[-1]["end_offset"] = len(self.data) - len(M602_HEADER)


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
                sequential_keywords=list(topic["sequential_keywords"]),
                index_terms=[topic["title"]],
            )
            for topic in parsed_topics
        ]
        resolved_targets = improve_m602_topic_links(
            topics,
            text_encoding=self.text_encoding,
            exact_targets=exact_target_map,
        )
        index_entries = [
            IndexEntry(label=topic["title"], context_id=topic["context_id"])
            for topic in parsed_topics
        ]
        resolution_mode = "binary_tail_exact"
        if len(resolved_targets) > len(exact_target_map):
            resolution_mode = "binary_tail_exact+label_title_fallback"
        return ensure_document_index(HelpDocument(
            format_name="m602",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata={
                "stamp": "(c) Software602 HelpSystem",
                "encrypted": True,
                "text_encoding": self.text_encoding,
                "link_target_kind": "m602_raw_link_code",
                "link_targets_resolved": True,
                "link_targets_exact_count": len(exact_target_map),
                "binary_index_entry_count": parser.binary_index_entry_count,
                "binary_index_root_count": parser.binary_index_root_count,
                "link_target_resolution": resolution_mode,
            },
            binary_data=data,
        ))


# Alias pre kompatibilitu
M602HelpReader = M602Reader
