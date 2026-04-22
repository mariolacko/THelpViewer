#!/usr/bin/env python3
"""Scan one Scorpion DAT record for the best-matching start offset of a reference block."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scorpion_compare import (  # noqa: E402
    _compact_payload_map,
    _compact_reference_map,
    _find_record,
    _matching_payload_indexes,
)
from thelpviewer.converter.readers.scorpion_dat import _display_stream  # noqa: E402


def _prefix_match_chars(chunk: bytes, reference_compact: str, probe_bytes: int) -> int:
    payload_compact, _ = _compact_payload_map(chunk[:probe_bytes])
    matched = 0
    for left, right in zip(payload_compact, reference_compact):
        if left != right:
            break
        matched += 1
    return matched


def _preview_lines(chunk: bytes, width: int = 100) -> str:
    lines = [line.strip() for line in _display_stream(chunk).splitlines() if line.strip()]
    if not lines:
        return ""
    preview = " | ".join(lines[:2])
    preview = " ".join(preview.split())
    if len(preview) > width:
        preview = preview[: width - 3] + "..."
    return preview


def _score_candidate(
    *,
    coverage: float,
    lead: int,
    prefix_chars: int,
    lead_cap: int,
    lead_divisor: float,
    prefix_bonus: float,
) -> float:
    lead_penalty = min(lead, lead_cap) / lead_divisor
    return coverage - lead_penalty + prefix_chars * prefix_bonus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to one Scorpion DAT file")
    parser.add_argument("record", help="Record name, for example 'kecy2'")
    parser.add_argument("reference_file", help="UTF-8 reference text file")
    parser.add_argument("--marker", help="Optional ASCII marker, for example '[R010]'")
    parser.add_argument("--start", type=int, default=0, help="First byte offset to test")
    parser.add_argument("--stop", type=int, help="Last byte offset to test (inclusive)")
    parser.add_argument("--step", type=int, default=16, help="Offset scan step in bytes")
    parser.add_argument(
        "--length",
        type=int,
        help="Slice length for each candidate; defaults to max(4096, 3x reference bytes)",
    )
    parser.add_argument("--top", type=int, default=20, help="How many best candidates to print")
    parser.add_argument(
        "--prefix-probe-bytes",
        type=int,
        default=512,
        help="How many leading bytes to use for direct prefix matching",
    )
    parser.add_argument(
        "--lead-cap",
        type=int,
        default=500,
        help="Maximum matched-index lead penalty in bytes",
    )
    parser.add_argument(
        "--lead-divisor",
        type=float,
        default=25.0,
        help="Lead-penalty divisor; bigger means weaker penalty",
    )
    parser.add_argument(
        "--prefix-bonus",
        type=float,
        default=2.0,
        help="Per-char score bonus for exact compact prefix matches",
    )
    args = parser.parse_args()

    path = Path(args.path)
    reference_text = Path(args.reference_file).read_text(encoding="utf-8")
    reference_compact, _ = _compact_reference_map(reference_text)
    record = _find_record(path, args.record)

    marker_bytes = args.marker.encode("ascii") if args.marker else None
    base_offset = 0
    if marker_bytes is not None:
        base_offset = record.payload.find(marker_bytes)
        if base_offset < 0:
            raise SystemExit(f"Marker {marker_bytes!r} not found in payload")

    start = max(0, args.start)
    stop = args.stop if args.stop is not None else len(record.payload)
    length = args.length or max(4096, len(reference_text.encode("utf-8")) * 3)

    results: list[tuple[float, float, int, int, int, str]] = []
    for relative_offset in range(start, stop + 1, max(1, args.step)):
        offset = base_offset + relative_offset
        chunk = record.payload[offset:offset + length]
        if not chunk:
            continue

        matched_indexes, matched_chars, _, reference_compact_size = _matching_payload_indexes(chunk, reference_text)
        if not matched_indexes or reference_compact_size <= 0:
            continue

        lead = min(matched_indexes)
        coverage = (matched_chars / reference_compact_size) * 100.0
        prefix_chars = _prefix_match_chars(chunk, reference_compact, args.prefix_probe_bytes)
        score = _score_candidate(
            coverage=coverage,
            lead=lead,
            prefix_chars=prefix_chars,
            lead_cap=args.lead_cap,
            lead_divisor=args.lead_divisor,
            prefix_bonus=args.prefix_bonus,
        )
        results.append((score, coverage, lead, prefix_chars, offset, _preview_lines(chunk)))

    results.sort(reverse=True)

    print(f"file:      {path}")
    print(f"record:    {record.name}")
    if marker_bytes is not None:
        print(f"marker:    {args.marker}")
        print(f"base-off:  {base_offset}")
    print(f"scan:      start={start} stop={stop} step={args.step}")
    print(f"length:    {length}")
    print(f"top:       {args.top}")
    print()

    print("BEST CANDIDATES")
    for score, coverage, lead, prefix_chars, offset, preview in results[: args.top]:
        print(
            f"  offset={offset:6d}  score={score:7.2f}  coverage={coverage:6.2f}%  "
            f"lead={lead:4d}  prefix={prefix_chars:3d}"
        )
        if preview:
            print(f"    {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
