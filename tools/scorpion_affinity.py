#!/usr/bin/env python3
"""Aggregate byte affinity stats across known Scorpion DAT ground-truth slices."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scorpion_compare import (  # type: ignore  # noqa: E402
    _byte_to_char,
    _find_record,
    _is_suspicious_byte,
    _matching_payload_indexes,
    _slice_payload,
)


@dataclass(frozen=True, slots=True)
class SampleCase:
    label: str
    path: Path
    record: str
    reference_file: Path
    marker: str | None
    byte_offset: int
    length: int


KNOWN_CASES = (
    SampleCase(
        label="R010",
        path=REPO_ROOT.parent / "Scorpion's Cheater Decoder" / "cheat23" / "program.dat",
        record="kecy",
        reference_file=REPO_ROOT / "tools" / "scorpion_ground_truth" / "r010-editorial-23.0.txt",
        marker="[R010]",
        byte_offset=0,
        length=12000,
    ),
    SampleCase(
        label="TUTOR",
        path=REPO_ROOT.parent / "Scorpion's Cheater Decoder" / "cheat23" / "program.dat",
        record="kecy2",
        reference_file=REPO_ROOT / "tools" / "scorpion_ground_truth" / "kecy2-jak-pouzivat-cheaty.txt",
        marker=None,
        byte_offset=23000,
        length=6200,
    ),
    SampleCase(
        label="R222",
        path=REPO_ROOT.parent / "Scorpion's Cheater Decoder" / "cheat23" / "program.dat",
        record="kecy2",
        reference_file=REPO_ROOT / "tools" / "scorpion_ground_truth" / "r222-o-programu-structure.txt",
        marker=None,
        byte_offset=13318,
        length=7800,
    ),
)


def _print_case_summary(case: SampleCase) -> tuple[dict[int, tuple[int, int]], tuple[int, int, int]]:
    record = _find_record(case.path, case.record)
    marker = case.marker.encode("ascii") if case.marker else None
    _, chunk = _slice_payload(record.payload, marker, case.length, case.byte_offset)
    reference_text = case.reference_file.read_text(encoding="utf-8")
    matched_indexes, matched_chars, payload_compact_size, reference_compact_size = _matching_payload_indexes(
        chunk,
        reference_text,
    )
    coverage = (matched_chars / reference_compact_size * 100.0) if reference_compact_size else 0.0
    print(
        f"{case.label:>5}  coverage={coverage:5.1f}%  matched={matched_chars:4d}  "
        f"payload_compact={payload_compact_size:4d}  ref_compact={reference_compact_size:4d}"
    )

    stats: defaultdict[int, list[int]] = defaultdict(lambda: [0, 0])
    for index, value in enumerate(chunk):
        if value in (0x0A, 0x0D):
            continue
        if index in matched_indexes:
            stats[value][0] += 1
        else:
            stats[value][1] += 1
    return {key: (value[0], value[1]) for key, value in stats.items()}, (matched_chars, payload_compact_size, reference_compact_size)


def _layout_items(aggregate: dict[int, tuple[int, int]]) -> list[tuple[int, int, int, str]]:
    items: list[tuple[int, int, int, str]] = []
    for value, (matched, unmatched) in aggregate.items():
        if unmatched < 20:
            continue
        char = _byte_to_char(value)
        if not char or char.isspace():
            continue
        is_layoutish = _is_suspicious_byte(value) or not char.isalnum()
        if not is_layoutish:
            continue
        items.append((value, matched, unmatched, char))
    return sorted(items, key=lambda item: (item[2], -item[1], item[0]), reverse=True)


def _strong_layout_bytes(items: list[tuple[int, int, int, str]]) -> list[int]:
    result: list[int] = []
    for value, matched, unmatched, char in items:
        if matched != 0 or unmatched < 50:
            continue
        if char and char.isascii() and char in ".,:;!?()[]{}<>-_/\\'\"%$#":
            continue
        result.append(value)
    return result


def main() -> int:
    aggregate: defaultdict[int, list[int]] = defaultdict(lambda: [0, 0])

    print("KNOWN CASES")
    for case in KNOWN_CASES:
        case_stats, _ = _print_case_summary(case)
        for value, (matched, unmatched) in case_stats.items():
            aggregate[value][0] += matched
            aggregate[value][1] += unmatched

    merged = {key: (value[0], value[1]) for key, value in aggregate.items()}
    layout_items = _layout_items(merged)
    strong = _strong_layout_bytes(layout_items)

    print()
    print("STRONG LAYOUT BYTES")
    for value in strong:
        char = _byte_to_char(value)
        printable = char.encode("unicode_escape").decode("ascii")
        matched, unmatched = merged[value]
        print(f"  0x{value:02x}  matched={matched:4d}  unmatched={unmatched:4d}  char={printable}")

    print()
    print("TOP LAYOUT CANDIDATES")
    for value, matched, unmatched, char in layout_items[:24]:
        printable = char.encode("unicode_escape").decode("ascii")
        print(f"  0x{value:02x}  matched={matched:4d}  unmatched={unmatched:4d}  char={printable}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
