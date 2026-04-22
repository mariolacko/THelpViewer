"""Deterministic reader wrapper for compiled HLX (.HLX/.hlx) files.

This reader delegates entirely to the deterministic parser in
`hlx_deterministic.parse_hlx_deterministic` and then derives positional
hotspots by scanning the file for control-byte + address sequences that
point into the pointer table inferred by the deterministic parser.

The goal: conversion must be driven only by data present inside the
HLX file (no external JSON mappings or out-of-band heuristics).
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path

from ..base import HelpReaderBase, HelpDocument, PositionedKeyword
from .hlx_deterministic import parse_hlx_deterministic


def is_hlx_binary(data: bytes) -> bool:
    """Conservative check whether this is a compiled HLX file.

    Keep this check lightweight — it only avoids mis-detecting textual
    source HLX files containing markers like `;SCREEN`.
    """
    if any(marker in data[:4096] for marker in (b";SCREEN", b";PAGE", b";STAMP", b";COMMENT")):
        return False
    return len(data) >= 256


class HlxBinaryReader(HelpReaderBase):
    """Reader that produces `HelpDocument` using deterministic parse only.

    It will attach simple `PositionedKeyword` anchors when the deterministic
    pointer table is available and occurrences of pointer values appear in
    the file preceded by a small control byte (0..7).
    """

    def read_bytes(self, data: bytes) -> HelpDocument:
        size = len(data)

        # Guess pool offset as other parsers do (stored at 4..6 or fallback)
        pool_offset_candidate = int.from_bytes(data[4:6], "little") if size >= 6 else 0
        if 0x100 <= pool_offset_candidate < size:
            pool_offset = pool_offset_candidate
        else:
            pool_offset = 0x800 if 0x800 < size else max(256, size // 8)

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
                addr2 = raw2 if pool_offset <= raw2 < size else (raw2 + pool_offset if pool_offset <= raw2 + pool_offset < size else None)
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
                addr4 = raw4 if pool_offset <= raw4 < size else (raw4 + pool_offset if pool_offset <= raw4 + pool_offset < size else None)
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
                    addr2 = raw2 if pool_offset <= raw2 < size else (raw2 + pool_offset if pool_offset <= raw2 + pool_offset < size else None)
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
                    addr4 = raw4 if pool_offset <= raw4 < size else (raw4 + pool_offset if pool_offset <= raw4 + pool_offset < size else None)
                    if addr4 is not None:
                        key = (tgt_topic.context_id, i, tgt_topic.context_id, 4)
                        if key in seen:
                            pass
                        else:
                            seen.add(key)
                            seg = data[pool_offset:i] if pool_offset < size else data[:i]
                            col = sum(1 for ch in seg if ch != 0 and ch >= 0x20 and ch != 0x7F)
                            tgt_topic.positional_keywords.append(PositionedKeyword(target_context=tgt_topic.context_id, line=0, first_column=col, last_column=col))

        metadata = {"format_name": "hlx-binary", "pointer_count": len(pointer_map), "topic_count": len(topics)}

        return HelpDocument(
            format_name="hlx",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            comments=[],
            metadata=metadata,
            binary_data=data,
        )
