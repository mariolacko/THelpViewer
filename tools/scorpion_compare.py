#!/usr/bin/env python3
"""Compare a Scorpion DAT payload slice with a known-good reference text."""

from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.converter.readers.scorpion_dat import (  # noqa: E402
    SCORPION_CHAR_MAP,
    _display_stream,
    _parse_records,
)


def _find_record(path: Path, name: str):
    records = _parse_records(path.read_bytes())
    record = next((item for item in records if item.name == name), None)
    if record is None:
        raise SystemExit(f"Record {name!r} not found in {path}")
    return record


def _slice_payload(
    payload: bytes,
    marker: bytes | None,
    length: int,
    byte_offset: int,
) -> tuple[int, bytes]:
    if marker is None:
        start = max(0, byte_offset)
        return start, payload[start:start + length]
    offset = payload.find(marker)
    if offset < 0:
        raise SystemExit(f"Marker {marker!r} not found in payload")
    start = max(0, offset + byte_offset)
    return start, payload[start:start + length]


def _paired_lines(reference: str, display: str) -> list[tuple[str, str]]:
    left = reference.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    right = display.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    size = max(len(left), len(right))
    rows: list[tuple[str, str]] = []
    for index in range(size):
        rows.append(
            (
                left[index] if index < len(left) else "",
                right[index] if index < len(right) else "",
            )
        )
    return rows


def _is_suspicious_byte(value: int) -> bool:
    if value in (0x09, 0x0A, 0x0D):
        return False
    if value < 0x20:
        return True
    if 0x20 <= value < 0x7F:
        return False
    return True


def _byte_to_char(value: int) -> str:
    if value in (0x0D, 0x0A, 0x09):
        return " "
    if value < 0x20:
        return ""
    if value in SCORPION_CHAR_MAP:
        return SCORPION_CHAR_MAP[value]
    return bytes((value,)).decode("cp852", errors="replace")


def _alignable_char(char: str) -> str:
    if not char:
        return ""
    if char.isalnum():
        return char.casefold()
    if char in "'!?":
        return char
    return ""


def _compact_reference_map(text: str) -> tuple[str, list[int]]:
    compact: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        normalized = _alignable_char(char)
        if not normalized:
            continue
        compact.append(normalized)
        positions.append(index)
    return "".join(compact), positions


def _compact_payload_map(payload: bytes) -> tuple[str, list[int]]:
    compact: list[str] = []
    positions: list[int] = []
    for index, value in enumerate(payload):
        normalized = _alignable_char(_byte_to_char(value))
        if not normalized:
            continue
        compact.append(normalized)
        positions.append(index)
    return "".join(compact), positions


def _matching_payload_indexes(payload: bytes, reference_text: str) -> tuple[set[int], int, int, int]:
    payload_compact, payload_positions = _compact_payload_map(payload)
    reference_compact, _ = _compact_reference_map(reference_text)
    matcher = SequenceMatcher(None, payload_compact, reference_compact, autojunk=False)

    matched_indexes: set[int] = set()
    matched_chars = 0
    for block in matcher.get_matching_blocks():
        if block.size <= 0:
            continue
        matched_chars += block.size
        for payload_position in payload_positions[block.a:block.a + block.size]:
            matched_indexes.add(payload_position)

    return matched_indexes, matched_chars, len(payload_compact), len(reference_compact)


def _candidate_drop_bytes(payload: bytes, matched_indexes: set[int]) -> list[tuple[int, int, int, str]]:
    matched_counts: Counter[int] = Counter()
    unmatched_counts: Counter[int] = Counter()

    for index, value in enumerate(payload):
        if value in (0x0A, 0x0D):
            continue
        if index in matched_indexes:
            matched_counts[value] += 1
        else:
            unmatched_counts[value] += 1

    candidates: list[tuple[int, int, int, str]] = []
    for value, unmatched in unmatched_counts.most_common():
        matched = matched_counts[value]
        if unmatched < 4:
            continue

        decoded = _byte_to_char(value)
        if not decoded or decoded.isspace():
            continue
        is_control_like = _is_suspicious_byte(value) or not decoded.isalnum()
        if not is_control_like:
            continue
        normalized = _alignable_char(decoded)
        if normalized and not _is_suspicious_byte(value) and matched >= unmatched:
            continue
        candidates.append((value, unmatched, matched, decoded or "<ctl>"))
        if len(candidates) >= 24:
            break

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to one Scorpion DAT file")
    parser.add_argument("record", help="Record name, for example 'kecy'")
    parser.add_argument("reference_file", help="UTF-8 text file with reference text")
    parser.add_argument("--marker", help="Optional ASCII marker, for example '[R010]'")
    parser.add_argument(
        "--length",
        type=int,
        help="Number of payload bytes to compare; defaults to 4x reference length",
    )
    parser.add_argument(
        "--byte-offset",
        type=int,
        default=0,
        help="Additional byte offset applied after the marker (or from file start when no marker is used)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    reference_text = Path(args.reference_file).read_text(encoding="utf-8")
    marker = args.marker.encode("ascii") if args.marker else None

    record = _find_record(path, args.record)
    length = args.length or max(512, len(reference_text.encode("utf-8")) * 4)
    offset, chunk = _slice_payload(record.payload, marker, length, args.byte_offset)
    display = _display_stream(chunk)

    print(f"file:   {path}")
    print(f"record: {record.name}")
    print(f"offset: {offset}")
    print(f"length: {len(chunk)}")
    print()

    matched_indexes, matched_chars, payload_compact_size, reference_compact_size = _matching_payload_indexes(
        chunk,
        reference_text,
    )
    if reference_compact_size:
        coverage = (matched_chars / reference_compact_size) * 100.0
    else:
        coverage = 0.0
    print("ALIGNMENT SUMMARY")
    print(f"  reference compact chars: {reference_compact_size}")
    print(f"  payload compact chars:   {payload_compact_size}")
    print(f"  matched compact chars:   {matched_chars}")
    print(f"  reference coverage:      {coverage:.1f}%")
    print()

    print("REFERENCE VS DISPLAY")
    print()
    for index, (left, right) in enumerate(_paired_lines(reference_text, display), start=1):
        print(f"{index:02d} R: {left}")
        print(f"   D: {right}")
    print()

    candidates = _candidate_drop_bytes(chunk, matched_indexes)
    if candidates:
        print("CANDIDATE CONTROL / DROP BYTES")
        for value, unmatched, matched, decoded in candidates:
            printable = decoded.encode("unicode_escape").decode("ascii")
            print(
                f"  0x{value:02x}  unmatched={unmatched:4d}  matched={matched:4d}  char={printable}"
            )
        print()

    suspicious = Counter(value for value in chunk if _is_suspicious_byte(value))
    if suspicious:
        print("TOP SUSPICIOUS BYTES")
        for value, count in suspicious.most_common(24):
            print(f"  0x{value:02x}  {count:4d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
