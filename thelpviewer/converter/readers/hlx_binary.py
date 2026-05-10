"""Deterministic reader wrapper for compiled HLX (.HLX/.hlx) files.

This reader delegates entirely to the deterministic parser in
`hlx_deterministic.parse_hlx_deterministic` and then derives positional
hotspots by scanning the file for control-byte + address sequences that
point into the pointer table inferred by the deterministic parser.

The goal: conversion must be driven only by data present inside the
HLX file (no external JSON mappings or out-of-band heuristics).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from ..base import HelpReaderBase, HelpDocument, IndexEntry, PositionedKeyword, TopicRecord, build_directional_nav_items
from .hlx_deterministic import parse_hlx_deterministic


@dataclass(frozen=True, slots=True)
class HlxIndexRecord:
    """One compiled Borland HLX index/search-entry record."""

    file_offset: int
    label: bytes
    flags: int
    target_offset: int


def is_hlx_binary(data: bytes) -> bool:
    """Conservative check whether this is a compiled HLX file.

    Keep this check lightweight — it only avoids mis-detecting textual
    source HLX files containing markers like `;SCREEN`.
    """
    if any(marker in data[:4096] for marker in (b";SCREEN", b";PAGE", b";STAMP", b";COMMENT")):
        return False
    return len(data) >= 256


def _is_printable_ascii(data: bytes) -> bool:
    return bool(data) and all(0x20 <= value < 0x7F for value in data)


def _extract_printable_strings(data: bytes) -> list[str]:
    strings: list[str] = []
    index = 0
    size = len(data)
    while index < size:
        value = data[index]
        if value != 0 and value >= 0x20 and value != 0x7F:
            end = index
            while end < size and data[end] != 0 and data[end] >= 0x20 and data[end] != 0x7F:
                end += 1
            strings.append(data[index:end].decode("cp437", errors="replace"))
            index = end + 1
            continue
        index += 1
    return strings


def _topic_shape_metrics(topics: list[TopicRecord]) -> tuple[float, float]:
    line_counts = [len(topic.raw_lines) for topic in topics if topic.raw_lines]
    if not line_counts:
        return 0.0, 1.0
    avg_lines = sum(line_counts) / len(line_counts)
    single_line_ratio = sum(1 for count in line_counts if count == 1) / len(line_counts)
    return avg_lines, single_line_ratio


def _collect_hlx_evidence(data: bytes, topics: list[TopicRecord]) -> dict[str, int | float]:
    strings = _extract_printable_strings(data)
    avg_lines, single_line_ratio = _topic_shape_metrics(topics)
    return {
        "rtf_ref_count": sum(1 for text in strings if ".rtf" in text.lower()),
        "overview_rtf_count": sum(1 for text in strings if "overview.rtf" in text.lower()),
        "lkeyword_rtf_count": sum(1 for text in strings if "lkeyword.rtf" in text.lower()),
        "hex_prefix_count": sum(
            1
            for text in strings
            if len(text) >= 8 and all(char in "0123456789ABCDEF" for char in text[:8])
        ),
        "long_string_count": sum(1 for text in strings if len(text) >= 45),
        "avg_lines_per_topic": round(avg_lines, 2),
        "single_line_ratio": round(single_line_ratio, 2),
    }


def _resolve_hlx_address(raw: int, pool_offset: int, size: int) -> int | None:
    if pool_offset <= raw < size:
        return raw
    shifted = raw + pool_offset
    if pool_offset <= shifted < size:
        return shifted
    return None


def _control_byte_profile(data: bytes, pool_offset: int) -> dict[str, object]:
    size = len(data)
    counts: dict[str, int] = {}
    valid_hits: dict[str, int] = {}
    ptr2_hits: dict[str, int] = {}
    ptr4_hits: dict[str, int] = {}

    for index, value in enumerate(data):
        if value >= 8:
            continue

        key = str(value)
        counts[key] = counts.get(key, 0) + 1
        has_valid_target = False

        if index + 3 <= size:
            raw2 = int.from_bytes(data[index + 1 : index + 3], "little")
            if _resolve_hlx_address(raw2, pool_offset, size) is not None:
                ptr2_hits[key] = ptr2_hits.get(key, 0) + 1
                has_valid_target = True

        if index + 5 <= size:
            raw4 = int.from_bytes(data[index + 1 : index + 5], "little")
            if _resolve_hlx_address(raw4, pool_offset, size) is not None:
                ptr4_hits[key] = ptr4_hits.get(key, 0) + 1
                has_valid_target = True

        if has_valid_target:
            valid_hits[key] = valid_hits.get(key, 0) + 1

    dominant = [
        int(key)
        for key, _value in sorted(
            valid_hits.items(),
            key=lambda item: (-item[1], -counts.get(item[0], 0), int(item[0])),
        )[:3]
    ]

    return {
        "control_byte_counts": counts,
        "control_byte_valid_hits": valid_hits,
        "control_byte_ptr2_hits": ptr2_hits,
        "control_byte_ptr4_hits": ptr4_hits,
        "control_byte_dominant": dominant,
    }


def _control_byte_mode_metrics(control_profile: dict[str, object]) -> dict[str, float]:
    ptr2_hits = control_profile.get("control_byte_ptr2_hits")
    ptr4_hits = control_profile.get("control_byte_ptr4_hits")

    def hit_count(source: object, control_byte: str) -> int:
        if not isinstance(source, dict):
            return 0
        value = source.get(control_byte, 0)
        return int(value)

    total_ptr2 = sum(hit_count(ptr2_hits, str(control_byte)) for control_byte in range(8))
    total_ptr4 = sum(hit_count(ptr4_hits, str(control_byte)) for control_byte in range(8))
    byte0_ptr2 = hit_count(ptr2_hits, "0")
    byte0_ptr4 = hit_count(ptr4_hits, "0")
    byte1_ptr2 = hit_count(ptr2_hits, "1")
    byte1_ptr4 = hit_count(ptr4_hits, "1")

    def ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 3)

    return {
        "control_byte_total_ptr4_ratio": ratio(total_ptr4, total_ptr2),
        "control_byte_0_ptr4_ratio": ratio(byte0_ptr4, byte0_ptr2),
        "control_byte_1_ptr4_ratio": ratio(byte1_ptr4, byte1_ptr2),
    }


def _classify_hlx_family(
    evidence: dict[str, int | float],
    topic_count: int,
    index_record_count: int,
) -> str:
    rtf_ref_count = int(evidence["rtf_ref_count"])
    overview_rtf_count = int(evidence["overview_rtf_count"])
    lkeyword_rtf_count = int(evidence["lkeyword_rtf_count"])
    long_string_count = int(evidence["long_string_count"])
    avg_lines = float(evidence["avg_lines_per_topic"])
    single_line_ratio = float(evidence["single_line_ratio"])
    total_ptr4_ratio = float(evidence.get("control_byte_total_ptr4_ratio", 0.0))
    byte1_ptr4_ratio = float(evidence.get("control_byte_1_ptr4_ratio", 0.0))

    compact_index_mode_hint = total_ptr4_ratio >= 0.6 and byte1_ptr4_ratio >= 0.5
    heading_catalog_mode_hint = total_ptr4_ratio <= 0.35 and byte1_ptr4_ratio <= 0.12

    if rtf_ref_count >= 5:
        if lkeyword_rtf_count >= 5:
            return "rtf-keyword-map"
        if overview_rtf_count >= 5:
            return "rtf-overview-map"
        return "rtf-reference-map"

    if (
        index_record_count >= 10
        and topic_count <= 100
        and long_string_count <= 10
        and avg_lines <= 2.5
        and compact_index_mode_hint
    ):
        return "compact-index"

    if topic_count >= 100 and avg_lines <= 1.75 and single_line_ratio >= 0.8:
        return "heading-catalog"

    if (
        topic_count >= 100
        and avg_lines <= 2.1
        and single_line_ratio >= 0.75
        and heading_catalog_mode_hint
    ):
        return "heading-catalog"

    if avg_lines >= 3.0 and single_line_ratio <= 0.75:
        return "topic-clusters"

    if index_record_count >= 10 and topic_count <= 100 and long_string_count <= 10:
        return "compact-index"

    return "mixed-catalog"


def _scan_hlx_index_records(data: bytes) -> list[HlxIndexRecord]:
    """Extract compiled HLX index records from Borland C++ 4.x search files.

    Observed `.HLX` files are mostly page-oriented index/search databases.
    Their useful payload is a sequence of records shaped as:

        ASCII label, NUL, 16-bit flags/count, 32-bit target offset

    Records restart after binary page headers.  The parser therefore scans
    for contiguous record runs instead of assuming one fixed table offset.
    """
    records: list[HlxIndexRecord] = []
    current_run: list[HlxIndexRecord] = []
    index = 0
    size = len(data)

    def flush_run() -> None:
        nonlocal current_run
        if len(current_run) >= 3:
            records.extend(current_run)
        current_run = []

    while index < size - 8:
        if not (0x20 <= data[index] < 0x7F):
            flush_run()
            index += 1
            continue

        end = data.find(b"\0", index, min(size, index + 128))
        if end <= index or end < 0 or end + 7 > size:
            flush_run()
            index += 1
            continue

        label = data[index:end]
        flags = int.from_bytes(data[end + 1 : end + 3], "little")
        target_offset = int.from_bytes(data[end + 3 : end + 7], "little")
        if (
            _is_printable_ascii(label)
            and target_offset % 4 == 0
            and target_offset < max(size * 4, 0x1000)
        ):
            current_run.append(
                HlxIndexRecord(
                    file_offset=index,
                    label=label,
                    flags=flags,
                    target_offset=target_offset,
                )
            )
            index = end + 7
            continue

        flush_run()
        index += 1

    flush_run()
    return records


def _records_to_document(
    records: list[HlxIndexRecord],
    source_name: str,
    data: bytes,
    metadata_extra: dict[str, object] | None = None,
) -> HelpDocument:
    """Build an index-only document from compiled HLX search records."""
    topics: list[TopicRecord] = []
    index_entries: list[IndexEntry] = []
    topic_records: list[tuple[HlxIndexRecord, TopicRecord]] = []
    seen: set[str] = set()
    filtered_records = _drop_split_label_fragments(records)

    for record in filtered_records:
        label_text = record.label.decode("ascii", errors="replace").strip()
        if not label_text:
            continue
        key = " ".join(label_text.casefold().split())
        if key in seen:
            continue
        seen.add(key)

        context_id = len(topics) + 1
        raw_label = label_text.encode("latin-1", errors="replace")
        topics.append(
            TopicRecord(
                context_id=context_id,
                raw_lines=[raw_label],
                index_terms=[raw_label],
                names=[label_text],
            )
        )
        topic_records.append((record, topics[-1]))
        index_entries.append(IndexEntry(label=raw_label, context_id=context_id))

    sorted_topics = sorted(
        topic_records,
        key=lambda item: (item[0].target_offset, item[0].file_offset),
    )
    for index, (_record, topic) in enumerate(sorted_topics):
        if index > 0:
            topic.prev_context = sorted_topics[index - 1][1].context_id
        if index + 1 < len(sorted_topics):
            topic.next_context = sorted_topics[index + 1][1].context_id
        topic.nav_items = build_directional_nav_items(topic)

    metadata = {
        "format_name": "hlx-binary",
        "hlx_kind": "compiled-index",
        "index_record_count": len(records),
        "index_topic_count": len(filtered_records),
        "topic_count": len(topics),
        "index_navigation_order": "target_offset",
    }
    if metadata_extra:
        metadata.update(metadata_extra)

    return HelpDocument(
        format_name="hlx",
        source_name=source_name,
        topics=topics,
        index_entries=index_entries,
        comments=[],
        metadata=metadata,
        binary_data=data,
    )


def _drop_split_label_fragments(records: list[HlxIndexRecord]) -> list[HlxIndexRecord]:
    """Remove labels split by HLX page boundaries when a full label exists.

    Some compiled HLX pages repeat table tails around page headers.  A label
    can therefore appear later as only its suffix (for example `ions` beside
    `DOS functions`) with the same flags and target offset.  Keep the full
    label and discard the suffix fragment.
    """
    kept: list[HlxIndexRecord] = []

    for record in records:
        label_key = record.label.lower()
        duplicate_of_full_label = False
        remove_indexes: list[int] = []

        for index, existing in enumerate(kept):
            if existing.flags != record.flags or existing.target_offset != record.target_offset:
                continue
            existing_key = existing.label.lower()
            if len(existing_key) > len(label_key) and existing_key.endswith(label_key):
                duplicate_of_full_label = True
                break
            if len(label_key) > len(existing_key) and label_key.endswith(existing_key):
                remove_indexes.append(index)

        if duplicate_of_full_label:
            continue
        for index in reversed(remove_indexes):
            kept.pop(index)
        kept.append(record)

    return kept


def _should_prefer_deterministic_topics(
    topics: list[TopicRecord],
    pointer_map: dict[int, int],
) -> bool:
    """Return True when the deterministic topic parse looks usable.

    Many HLX binaries expose searchable label runs, but only a subset are
    really index-only/search databases. For full manuals like BCW/OLE/OWL,
    `_scan_hlx_index_records` finds lots of apparent labels as well; we should
    still prefer the deterministic topic parse only when it yields something
    richer than a mostly single-line heading list.
    """
    if len(topics) < 50:
        return False

    avg_lines, single_line_ratio = _topic_shape_metrics(topics)
    if not topics or avg_lines == 0.0:
        return False

    multi_line_topics = sum(1 for topic in topics if len(topic.raw_lines) >= 3)
    rich_multi_line_topics = 0
    for topic in topics:
        if len(topic.raw_lines) < 3:
            continue
        joined = " ".join(
            raw.decode("cp437", errors="ignore").strip()
            for raw in topic.raw_lines
            if raw.strip()
        )
        if len(joined) >= 40:
            rich_multi_line_topics += 1

    has_rich_topic_shape = (
        avg_lines >= 3.0
        or single_line_ratio <= 0.75
        or (len(topics) >= 250 and avg_lines >= 2.5 and multi_line_topics >= 25)
        or (
            len(topics) >= 400
            and len(pointer_map) >= 3
            and multi_line_topics >= 30
            and rich_multi_line_topics >= 30
        )
    )
    if not has_rich_topic_shape:
        return False

    return len(pointer_map) >= 3 or len(topics) >= 50


class HlxBinaryReader(HelpReaderBase):
    """Reader that produces `HelpDocument` using deterministic parse only.

    It will attach simple `PositionedKeyword` anchors when the deterministic
    pointer table is available and occurrences of pointer values appear in
    the file preceded by a small control byte (0..7).
    """

    def read_bytes(self, data: bytes) -> HelpDocument:
        index_records = _scan_hlx_index_records(data)
        size = len(data)

        # Guess pool offset as other parsers do (stored at 4..6 or fallback)
        pool_offset_candidate = int.from_bytes(data[4:6], "little") if size >= 6 else 0
        if 0x100 <= pool_offset_candidate < size:
            pool_offset = pool_offset_candidate
        else:
            pool_offset = 0x800 if 0x800 < size else max(256, size // 8)
        control_profile = _control_byte_profile(data, pool_offset)
        control_mode_metrics = _control_byte_mode_metrics(control_profile)

        # Delegate to deterministic parser — it now always returns a topic
        # list and index entries (pointer_map may be empty).
        try:
            res = parse_hlx_deterministic(data, min_topics=1)
        except Exception:
            res = None

        if res and isinstance(res, tuple) and len(res) == 3:
            topics, index_entries, pointer_map = res
        elif res and isinstance(res, tuple) and len(res) == 2:
            topics, index_entries = res  # type: ignore[assignment]
            pointer_map = {}
        else:
            topics, index_entries, pointer_map = [], [], {}

        evidence = _collect_hlx_evidence(data, topics)
        evidence.update(control_mode_metrics)
        hlx_family = _classify_hlx_family(evidence, len(topics), len(index_records))
        prefer_deterministic_family = hlx_family in {"rtf-keyword-map", "topic-clusters"}

        if len(index_records) >= 10 and (
            not prefer_deterministic_family
            or not _should_prefer_deterministic_topics(topics, pointer_map)
        ):
            return _records_to_document(
                index_records,
                self.source_name,
                data,
                metadata_extra={
                    "hlx_family": hlx_family,
                    **evidence,
                    **control_profile,
                    **control_mode_metrics,
                },
            )

        # Build quick map: context_id -> representative offset in file.
        # We search for the first raw line of each topic in the file data
        # and prefer offsets at or beyond the guessed pool_offset.
        topic_offsets: dict[int, int] = {}
        for t in topics:
            best_off: Optional[int] = None
            for raw in t.raw_lines:
                if not raw:
                    continue
                off = data.find(raw)
                if off == -1:
                    continue
                # prefer in-pool findings
                if off >= pool_offset:
                    if best_off is None or off < best_off:
                        best_off = off
                else:
                    if best_off is None:
                        best_off = off
            topic_offsets[t.context_id] = best_off if best_off is not None else max(0, pool_offset)

        # Scan the binary for control-byte + 2/4-byte address occurrences and
        # attach `PositionedKeyword` anchors. This runs even when the
        # deterministic parser did not expose an explicit `pointer_map` —
        # in that case we attempt to map the target address to the nearest
        # topic start found in the file. All information used is read from
        # the HLX file itself.
        CONTROL_SET = set(range(0, 8))
        sorted_t_offsets = sorted(topic_offsets.items(), key=lambda x: x[1])

        def find_src_ctx_by_pos(pos: int) -> Optional[int]:
            # find topic with largest offset <= pos
            best = None
            best_off = -1
            for ctx, off in sorted_t_offsets:
                if off <= pos and off > best_off:
                    best_off = off
                    best = ctx
            if best is None and topics:
                return topics[0].context_id
            return best

        def find_target_ctx_by_addr(addr: int) -> Optional[int]:
            # prefer explicit pointer_map if present
            if addr in pointer_map:
                return pointer_map[addr]
            # otherwise map address to the nearest topic start <= addr
            best = None
            best_off = -1
            for ctx, off in sorted_t_offsets:
                if off <= addr and off > best_off:
                    best_off = off
                    best = ctx
            if best is None and topics:
                return topics[0].context_id
            return best

        for i in range(0, size):
            b = data[i]
            if b not in CONTROL_SET:
                continue
            # two-byte pointer
            if i + 3 <= size:
                raw2 = int.from_bytes(data[i + 1 : i + 3], "little")
                addr2 = _resolve_hlx_address(raw2, pool_offset, size)
                if addr2 is not None:
                    target_ctx = find_target_ctx_by_addr(addr2)
                    src_ctx = find_src_ctx_by_pos(i)
                    if target_ctx is not None and src_ctx is not None:
                        start = topic_offsets.get(src_ctx, 0)
                        seg = data[start:i]
                        col = sum(1 for ch in seg if ch != 0 and ch >= 0x20 and ch != 0x7F)
                        src_topic = next((tt for tt in topics if tt.context_id == src_ctx), None)
                        if src_topic is not None:
                            src_topic.positional_keywords.append(PositionedKeyword(target_context=target_ctx, line=0, first_column=col, last_column=col))
            # four-byte pointer
            if i + 5 <= size:
                raw4 = int.from_bytes(data[i + 1 : i + 5], "little")
                addr4 = _resolve_hlx_address(raw4, pool_offset, size)
                if addr4 is not None:
                    target_ctx = find_target_ctx_by_addr(addr4)
                    src_ctx = find_src_ctx_by_pos(i)
                    if target_ctx is not None and src_ctx is not None:
                        start = topic_offsets.get(src_ctx, 0)
                        seg = data[start:i]
                        col = sum(1 for ch in seg if ch != 0 and ch >= 0x20 and ch != 0x7F)
                        src_topic = next((tt for tt in topics if tt.context_id == src_ctx), None)
                        if src_topic is not None:
                            src_topic.positional_keywords.append(PositionedKeyword(target_context=target_ctx, line=0, first_column=col, last_column=col))

        # Final fallback: if deterministic parser returned no topics,
        # keep a single blob as a topic so converter can still produce output.
        if not topics:
            topics = [type("Topic", (), {"context_id": 1, "raw_lines": [data], "positional_keywords": [], "prev_context": None, "next_context": None, "up_context": None, "down_context": None})()]

        # Permissive fallback for single-topic files: if we still have no
        # positional keywords, scan for control+address sequences and
        # attach anchors to the single topic. This uses only data inside
        # the HLX file and preserves navigability for very small files.
        if topics and len(topics) == 1 and not any(t.positional_keywords for t in topics):
            tgt_topic = topics[0]
            seen = set()
            for i in range(0, size - 2):
                b = data[i]
                if b >= 0x20:
                    continue
                # 2-byte
                if i + 3 <= size:
                    raw2 = int.from_bytes(data[i + 1 : i + 3], "little")
                    addr2 = _resolve_hlx_address(raw2, pool_offset, size)
                    if addr2 is not None:
                        key = (tgt_topic.context_id, i, tgt_topic.context_id, 2)
                        if key in seen:
                            pass
                        else:
                            seen.add(key)
                            seg = data[pool_offset:i] if pool_offset < size else data[:i]
                            col = sum(1 for ch in seg if ch != 0 and ch >= 0x20 and ch != 0x7F)
                            tgt_topic.positional_keywords.append(PositionedKeyword(target_context=tgt_topic.context_id, line=0, first_column=col, last_column=col))
                # 4-byte
                if i + 5 <= size:
                    raw4 = int.from_bytes(data[i + 1 : i + 5], "little")
                    addr4 = _resolve_hlx_address(raw4, pool_offset, size)
                    if addr4 is not None:
                        key = (tgt_topic.context_id, i, tgt_topic.context_id, 4)
                        if key in seen:
                            pass
                        else:
                            seen.add(key)
                            seg = data[pool_offset:i] if pool_offset < size else data[:i]
                            col = sum(1 for ch in seg if ch != 0 and ch >= 0x20 and ch != 0x7F)
                            tgt_topic.positional_keywords.append(PositionedKeyword(target_context=tgt_topic.context_id, line=0, first_column=col, last_column=col))

        metadata = {
            "format_name": "hlx-binary",
            "hlx_kind": "compiled-topics",
            "hlx_family": hlx_family,
            "pointer_count": len(pointer_map),
            "topic_count": len(topics),
            **evidence,
            **control_profile,
            **control_mode_metrics,
        }

        return HelpDocument(
            format_name="hlx",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            comments=[],
            metadata=metadata,
            binary_data=data,
        )
