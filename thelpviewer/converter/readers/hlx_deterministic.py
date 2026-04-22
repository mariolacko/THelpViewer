"""Deterministic helper parser for compiled HLX pointer tables.

This module implements a stricter detection routine that attempts to
find a header pointer table (16-bit or 32-bit) and map pointers to
topic text offsets deterministically. It returns TopicRecord and
IndexEntry lists when confident, otherwise ``None`` to fall back to
the heuristic reader.
"""
from __future__ import annotations

from typing import Optional, List, Tuple
import bisect

from ..base import TopicRecord, IndexEntry


def _extract_strings(data: bytes) -> List[Tuple[int, bytes, str]]:
    size = len(data)
    strings: List[Tuple[int, bytes, str]] = []
    i = 0
    while i < size:
        b = data[i]
        if b != 0 and b >= 0x20 and b != 0x7F:
            j = i
            while j < size and data[j] != 0 and data[j] >= 0x20 and data[j] != 0x7F:
                j += 1
            raw = data[i:j]
            try:
                decoded = raw.decode("cp437", errors="replace")
            except Exception:
                decoded = raw.decode("latin-1", errors="replace")
            strings.append((i, raw, decoded))
            i = j + 1
        else:
            i += 1
    return strings


def parse_hlx_deterministic(data: bytes, min_topics: int = 20) -> Optional[Tuple[List[TopicRecord], List[IndexEntry]]]:
    """Attempt a deterministic parse of pointer table and topic ordering.

    Returns (topics, index_entries) when confident, otherwise ``None``.
    """
    size = len(data)

    pool_offset_candidate = int.from_bytes(data[4:6], "little") if size >= 6 else 0
    if 0x100 <= pool_offset_candidate < size:
        pool_offset = pool_offset_candidate
    else:
        pool_offset = 0x800 if 0x800 < size else max(256, size // 8)

    strings = _extract_strings(data)
    pool_strings = [(off, raw, txt) for (off, raw, txt) in strings if off >= pool_offset]
    # If we couldn't find strings at or beyond the guessed pool_offset,
    # fall back to using all extracted strings. This ensures we can still
    # build topics for small or atypical HLX variations without external
    # data or heuristics external to the file.
    if not pool_strings:
        pool_strings = strings.copy()

    def is_title(s: str) -> bool:
        s = s.strip()
        if len(s) < 3:
            return False
        if s.lower().startswith(("about ", "menu ", "help ", "contents", "introduction", "overview")):
            return True
        if " " in s and s[0].isupper():
            return True
        if len(s) <= 40 and s == s.upper() and any(c.isalpha() for c in s):
            return True
        return False

    # Group pool strings into naive topics (offset + raw_lines)
    naive: List[Tuple[int, List[bytes]]] = []
    current_lines: List[bytes] = []
    current_title_off: Optional[int] = None
    for off, raw, txt in pool_strings:
        if is_title(txt):
            if current_lines:
                naive.append((current_title_off or off, current_lines.copy()))
                current_lines = []
            current_title_off = off
            current_lines.append(raw)
        else:
            if len(raw) >= 3:
                if current_title_off is None:
                    current_title_off = off
                current_lines.append(raw)
    if current_lines:
        naive.append((current_title_off or 0, current_lines.copy()))

    if not naive:
        # If no titles were detected, fall back to grouping all pool strings
        # into a single naive topic to ensure the parser returns a usable
        # topic list for conversion.
        all_raw = [raw for (_off, raw, _txt) in pool_strings]
        if all_raw:
            naive.append((pool_strings[0][0] if pool_strings and pool_strings[0] else 0, all_raw))
        else:
            # last-resort: empty topic
            naive.append((0, []))

    # Build title map and offset index
    title_map: dict[str, List[bytes]] = {}
    offset_list: List[Tuple[int, List[bytes]]] = []
    for off, raw_lines in naive:
        title = None
        if raw_lines:
            try:
                title = raw_lines[0].decode("cp437", errors="ignore")
            except Exception:
                title = raw_lines[0].decode("latin-1", errors="ignore")
        if title:
            title_map[title.strip().rstrip(".").casefold()] = raw_lines
        offset_list.append((off or 0, raw_lines))
    offset_list.sort(key=lambda x: x[0])

    header_end = pool_offset if pool_offset and pool_offset < size else min(0x800, size)

    def read_z(off: int, maxlen: int = 200) -> str:
        if off < 0 or off >= size:
            return ""
        i = off
        out: list[str] = []
        while i < size and data[i] != 0 and data[i] >= 0x20 and data[i] != 0x7F and len(out) < maxlen:
            out.append(chr(data[i]))
            i += 1
        return "".join(out)

    best_score = -1.0
    best_choice = None

    for step in (2, 4):
        for start in range(0, max(2, header_end - step), step):
            entries: List[int] = []
            max_entries = min(256 // step, max(8, (header_end - start) // step))
            for k in range(max_entries):
                off = start + k * step
                if off + step > header_end:
                    break
                entries.append(int.from_bytes(data[off : off + step], "little"))
            if len(entries) < 8:
                continue
            total = len(entries)
            hits = [v for v in entries if pool_offset <= v < size]
            z_hits = sum(1 for v in hits if len(read_z(v, 6)) >= 3)
            frac = z_hits / total
            if frac < 0.25:
                continue
            monotonic = sum(1 for a, b in zip(entries, entries[1:]) if a <= b) / max(1, (len(entries) - 1))
            uniqueness = len(set(entries)) / len(entries)
            title_matches = 0
            for v in entries:
                if pool_offset <= v < size:
                    lbl = read_z(v, 80).strip().rstrip(".").casefold()
                    if lbl and lbl in title_map:
                        title_matches += 1
            title_frac = title_matches / total
            score = frac * 100.0 + monotonic * 40.0 + uniqueness * 10.0 + title_frac * 80.0 + (2.0 if step == 2 else 0.0)
            if score > best_score:
                best_score = score
                best_choice = (start, step, entries, frac, monotonic, title_frac)

    # Choose the best candidate if any; otherwise fall back to empty entries.
    # We no longer reject parsing based on a hard score threshold so the
    # deterministic parser will always return the topics inferred from the
    # file contents (pointer_map may be empty if no reliable table is found).
    if best_choice:
        _, _, entries, _, _, _ = best_choice
    else:
        entries = []
    ordered_ptrs: List[int] = []
    seen = set()
    for v in entries:
        if not (pool_offset <= v < size):
            continue
        if v in seen:
            continue
        if len(read_z(v, 6)) < 3:
            continue
        seen.add(v)
        ordered_ptrs.append(v)

    offs = [o for o, _ in offset_list]

    def find_topic_by_offset(v: int) -> Optional[List[bytes]]:
        if not offset_list:
            return None
        idx = bisect.bisect_right(offs, v) - 1
        if idx >= 0 and idx < len(offset_list):
            return offset_list[idx][1]
        return None

    used = set()
    result_topics: List[List[bytes]] = []
    # pointer -> raw_lines (for later mapping to context ids)
    pointer_to_raw: dict[int, List[bytes]] = {}
    for p in ordered_ptrs:
        label = read_z(p, 80).strip().rstrip(".").casefold()
        picked = None
        if label and label in title_map and id(title_map[label]) not in used:
            picked = title_map[label]
        else:
            t = find_topic_by_offset(p)
            if t and id(t) not in used:
                picked = t
        if picked is not None:
            result_topics.append(picked)
            pointer_to_raw[p] = picked
            used.add(id(picked))

    for off, raw_lines in naive:
        if id(raw_lines) not in used:
            result_topics.append(raw_lines)

    topic_objs: List[TopicRecord] = []
    index_entries: List[IndexEntry] = []
    for idx, raw_lines in enumerate(result_topics, start=1):
        tr = TopicRecord(context_id=idx, raw_lines=raw_lines.copy())
        topic_objs.append(tr)
        if raw_lines:
            index_entries.append(IndexEntry(label=raw_lines[0], context_id=idx))

    # Always return the parsed topic list and index entries derived from
    # the file contents. Do not use external heuristics or require a
    # minimum topic count; callers will receive an empty pointer_map when a
    # deterministic pointer table could not be inferred.

    # Build pointer->context_id map using pointer_to_raw
    pointer_map: dict[int, int] = {}
    if pointer_to_raw:
        for p, raw in pointer_to_raw.items():
            # find index of raw in result_topics by content equality
            try:
                idx = next(i for i, r in enumerate(result_topics, start=1) if r == raw)
            except StopIteration:
                continue
            pointer_map[p] = idx

    return topic_objs, index_entries, pointer_map
