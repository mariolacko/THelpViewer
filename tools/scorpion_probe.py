#!/usr/bin/env python3
"""Inspect raw Scorpion DAT records for reverse-engineering work."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import textwrap
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.converter.readers.scorpion_dat import (
    SCORPION_ALLOWED_DISPLAY_CHARS,
    SCORPION_ALLOWED_PUNCTUATION,
    SCORPION_CHAR_MAP,
    SCORPION_DROP_BYTES,
    _cp852_stream,
    _display_stream,
    _parse_records,
)


RESEARCH_DROP_PROFILES = {
    "generic-layout": frozenset({0x40, 0x60, 0x80, 0x90, 0xA0, 0xA1, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0, 0xF1}),
    "text-only-strong": frozenset({0x40, 0x60, 0x9E, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xC0, 0xC1, 0xC2, 0xC3, 0xDB, 0xF0, 0xF1, 0xF2, 0xF4, 0xF5, 0xF6}),
}


def _hex_lines(data: bytes, width: int = 16) -> list[str]:
    lines: list[str] = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_part = " ".join(f"{value:02x}" for value in chunk)
        ascii_part = "".join(chr(value) if 0x20 <= value < 0x7F else "." for value in chunk)
        lines.append(f"{offset:04x}: {hex_part:<{width * 3 - 1}}  {ascii_part}")
    return lines


def _slice_payload(payload: bytes, marker: bytes | None, length: int, byte_offset: int) -> tuple[int, bytes]:
    if marker is None:
        start = max(0, byte_offset)
        return start, payload[start:start + length]
    offset = payload.find(marker)
    if offset < 0:
        raise ValueError(f"Marker {marker!r} not found in payload.")
    start = max(0, offset + byte_offset)
    return start, payload[start:start + length]


def _parse_extra_drop(text: str | None) -> set[int]:
    if not text:
        return set()
    values: set[int] = set()
    for part in text.split(","):
        token = part.strip().lower()
        if not token:
            continue
        if token.startswith("0x"):
            token = token[2:]
        values.add(int(token, 16))
    return values


def _display_stream_with_drop(payload: bytes, extra_drop: set[int]) -> str:
    out: list[str] = []
    drop_bytes = set(SCORPION_DROP_BYTES) | extra_drop
    for value in payload:
        if value in (0x0D, 0x0A):
            out.append("\n")
        elif value == 0x09:
            out.append(" ")
        elif value < 0x20:
            out.append(" ")
        elif value in drop_bytes:
            continue
        elif value in SCORPION_CHAR_MAP:
            out.append(SCORPION_CHAR_MAP[value])
        else:
            out.append(bytes((value,)).decode("cp852", errors="replace"))
    return "".join(out)


def _text_islands_view(text: str) -> str:
    cleaned: list[str] = []
    allowed = SCORPION_ALLOWED_PUNCTUATION | set("@")
    for char in text:
        if (
            char.isalnum()
            or char in SCORPION_ALLOWED_DISPLAY_CHARS
            or char in allowed
        ):
            cleaned.append(char)
        elif char == "\n":
            cleaned.append("\n")
        else:
            cleaned.append(" ")

    normalized = "".join(cleaned)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.splitlines())
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to one Scorpion DAT file")
    parser.add_argument("record", help="Record name, for example 'kecy' or 'seznam'")
    parser.add_argument("--marker", help="Optional ASCII marker, for example '[R010]'")
    parser.add_argument("--length", type=int, default=512, help="Number of payload bytes to dump")
    parser.add_argument(
        "--byte-offset",
        type=int,
        default=0,
        help="Additional byte offset applied after the marker (or from record start when no marker is used)",
    )
    parser.add_argument(
        "--drop-profile",
        choices=sorted(RESEARCH_DROP_PROFILES),
        help="Optional research-only extra drop-byte profile for layout-heavy slices",
    )
    parser.add_argument(
        "--extra-drop",
        help="Comma-separated hex byte values to drop in addition to the default runtime set, for example '40,60,a0'",
    )
    parser.add_argument(
        "--text-islands",
        action="store_true",
        help="Also print a normalized text-islands view after applying extra drop bytes",
    )
    args = parser.parse_args()

    path = Path(args.path)
    records = _parse_records(path.read_bytes())
    record = next((item for item in records if item.name == args.record), None)
    if record is None:
        raise SystemExit(f"Record {args.record!r} not found in {path}")

    marker = args.marker.encode("ascii") if args.marker else None
    offset, chunk = _slice_payload(record.payload, marker, args.length, args.byte_offset)
    extra_drop = set()
    if args.drop_profile:
        extra_drop.update(RESEARCH_DROP_PROFILES[args.drop_profile])
    extra_drop.update(_parse_extra_drop(args.extra_drop))

    print(f"file:   {path}")
    print(f"record: {record.name}")
    print(f"offset: {offset}")
    print(f"length: {len(chunk)}")
    if extra_drop:
        print("extra-drop:", ", ".join(f"0x{value:02x}" for value in sorted(extra_drop)))
    print()

    print("HEX")
    print("\n".join(_hex_lines(chunk)))
    print()

    print("CP852")
    print(textwrap.indent(_cp852_stream(chunk), "  "))
    print()

    print("DISPLAY")
    print(textwrap.indent(_display_stream(chunk), "  "))
    if extra_drop:
        display_text = _display_stream_with_drop(chunk, extra_drop)
        print()
        print("DISPLAY WITH EXTRA DROP")
        print(textwrap.indent(display_text, "  "))
        if args.text_islands:
            print()
            print("TEXT ISLANDS")
            print(textwrap.indent(_text_islands_view(display_text), "  "))
    elif args.text_islands:
        print()
        print("TEXT ISLANDS")
        print(textwrap.indent(_text_islands_view(_display_stream(chunk)), "  "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
