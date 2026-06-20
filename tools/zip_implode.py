#!/usr/bin/env python3
"""Decode PKZIP implode members (ZIP method 6) without external tools.

This is intended for old archives such as TD.ZIP / TPROF.ZIP whose bundled
DOC files use method 6 with the literal/dictionary mode carried in ZIP general-
purpose flags instead of a DCL-style in-stream prologue.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import struct
import sys
import zipfile


MAX_CODE_BITS = 16
LENGTH_BASE_2 = tuple(range(2, 66))
LENGTH_BASE_3 = tuple(range(3, 67))
LENGTH_EXTRA = (0,) * 63 + (8,)
DISTANCE_BASE_4K = tuple(1 + index * 64 for index in range(64))
DISTANCE_BASE_8K = tuple(1 + index * 128 for index in range(64))


class BitReader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._byte_index = 0
        self._bit_buffer = 0
        self._bit_count = 0

    @property
    def byte_offset(self) -> int:
        if self._bit_count != 0:
            raise ValueError("reader is not byte-aligned")
        return self._byte_index

    def read_byte(self) -> int:
        if self._bit_count != 0:
            raise ValueError("reader is not byte-aligned")
        if self._byte_index >= len(self._data):
            raise EOFError("unexpected end of implode stream")
        value = self._data[self._byte_index]
        self._byte_index += 1
        return value

    def read_bit(self) -> int:
        return self.read_bits(1)

    def read_bits(self, count: int) -> int:
        if count < 0:
            raise ValueError("bit count must be non-negative")
        while self._bit_count < count:
            if self._byte_index >= len(self._data):
                raise EOFError("unexpected end of implode stream")
            self._bit_buffer |= self._data[self._byte_index] << self._bit_count
            self._byte_index += 1
            self._bit_count += 8
        mask = (1 << count) - 1
        value = self._bit_buffer & mask
        self._bit_buffer >>= count
        self._bit_count -= count
        return value


@dataclass(frozen=True, slots=True)
class HuffmanTable:
    counts: tuple[int, ...]
    symbols: tuple[int, ...]

    def decode(self, reader: BitReader) -> int:
        code = 0
        first = 0
        index = 0
        for bit_length in range(1, len(self.counts)):
            code |= reader.read_bit() ^ 1
            count = self.counts[bit_length]
            if code < first + count:
                return self.symbols[index + (code - first)]
            index += count
            first = (first + count) << 1
            code <<= 1
        raise ValueError("invalid implode Huffman code")


@dataclass(frozen=True, slots=True)
class TreeSummary:
    name: str
    value_count: int
    pair_count: int
    byte_start: int
    byte_end: int


@dataclass(frozen=True, slots=True)
class ZipMember:
    archive_path: Path
    member_name: str
    local_header_offset: int
    compressed_offset: int
    compressed_size: int
    uncompressed_size: int
    flag_bits: int
    compression_method: int


def _build_huffman(lengths: list[int]) -> HuffmanTable:
    counts = [0] * (MAX_CODE_BITS + 1)
    for bit_length in lengths:
        if bit_length < 1 or bit_length > MAX_CODE_BITS:
            raise ValueError(f"unsupported implode code length: {bit_length}")
        counts[bit_length] += 1

    symbols: list[int] = []
    for bit_length in range(1, MAX_CODE_BITS + 1):
        for symbol, current_length in enumerate(lengths):
            if current_length == bit_length:
                symbols.append(symbol)
    return HuffmanTable(tuple(counts), tuple(symbols))


def _read_tree(reader: BitReader, name: str, value_count: int) -> tuple[HuffmanTable, TreeSummary]:
    byte_start = reader.byte_offset
    pair_count = reader.read_byte() + 1
    lengths: list[int] = []
    for _ in range(pair_count):
        pair = reader.read_byte()
        bit_length = (pair & 0x0F) + 1
        repeat_count = (pair >> 4) + 1
        lengths.extend([bit_length] * repeat_count)
    if len(lengths) != value_count:
        raise ValueError(
            f"{name} tree expands to {len(lengths)} entries, expected {value_count}"
        )
    summary = TreeSummary(
        name=name,
        value_count=value_count,
        pair_count=pair_count,
        byte_start=byte_start,
        byte_end=reader.byte_offset,
    )
    return _build_huffman(lengths), summary


def parse_implode_trees(data: bytes, flag_bits: int) -> tuple[list[TreeSummary], int, HuffmanTable | None, HuffmanTable, HuffmanTable]:
    reader = BitReader(data)
    literal_tree: HuffmanTable | None = None
    summaries: list[TreeSummary] = []

    if flag_bits & 0x0004:
        literal_tree, literal_summary = _read_tree(reader, "literal", 256)
        summaries.append(literal_summary)

    length_tree, length_summary = _read_tree(reader, "length", 64)
    distance_tree, distance_summary = _read_tree(reader, "distance", 64)
    summaries.append(length_summary)
    summaries.append(distance_summary)
    return summaries, reader.byte_offset, literal_tree, length_tree, distance_tree


def decode_implode(data: bytes, flag_bits: int, uncompressed_size: int) -> tuple[bytes, list[TreeSummary], int]:
    summaries, tree_bytes, literal_tree, length_tree, distance_tree = parse_implode_trees(data, flag_bits)
    reader = BitReader(data)

    if flag_bits & 0x0004:
        _read_tree(reader, "literal", 256)
        min_match_length = 3
        literal_coded = True
    else:
        min_match_length = 2
        literal_coded = False
    _read_tree(reader, "length", 64)
    _read_tree(reader, "distance", 64)

    length_base = LENGTH_BASE_3 if min_match_length == 3 else LENGTH_BASE_2
    distance_base = DISTANCE_BASE_8K if (flag_bits & 0x0002) else DISTANCE_BASE_4K
    low_distance_bits = 7 if (flag_bits & 0x0002) else 6

    output = bytearray()
    while len(output) < uncompressed_size:
        if reader.read_bit() == 1:
            if literal_coded:
                if literal_tree is None:
                    raise ValueError("literal tree missing for coded-literal stream")
                output.append(literal_tree.decode(reader))
            else:
                output.append(reader.read_bits(8))
            continue

        low_distance = reader.read_bits(low_distance_bits)
        distance_symbol = distance_tree.decode(reader)
        length_symbol = length_tree.decode(reader)
        distance = distance_base[distance_symbol] + low_distance
        length = length_base[length_symbol]
        if LENGTH_EXTRA[length_symbol]:
            length += reader.read_bits(8)

        for _ in range(length):
            source_index = len(output) - distance
            output.append(output[source_index] if source_index >= 0 else 0)
            if len(output) >= uncompressed_size:
                break

    return bytes(output), summaries, tree_bytes


def list_members(archive_path: Path) -> list[ZipMember]:
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()

    members: list[ZipMember] = []
    with archive_path.open("rb") as handle:
        for info in infos:
            handle.seek(info.header_offset)
            local_header = handle.read(30)

            if len(local_header) != 30 or local_header[:4] != b"PK\x03\x04":
                raise ValueError("invalid local ZIP header")

            filename_length, extra_length = struct.unpack_from("<HH", local_header, 26)
            compressed_offset = info.header_offset + 30 + filename_length + extra_length
            members.append(
                ZipMember(
                    archive_path=archive_path,
                    member_name=info.filename,
                    local_header_offset=info.header_offset,
                    compressed_offset=compressed_offset,
                    compressed_size=info.compress_size,
                    uncompressed_size=info.file_size,
                    flag_bits=info.flag_bits,
                    compression_method=info.compress_type,
                )
            )
    return members


def locate_member(archive_path: Path, member_name: str) -> ZipMember:
    for member in list_members(archive_path):
        if member.member_name == member_name:
            return member
    raise KeyError(f"There is no item named {member_name!r} in the archive")


def read_member_data(member: ZipMember) -> bytes:
    with member.archive_path.open("rb") as handle:
        handle.seek(member.compressed_offset)
        data = handle.read(member.compressed_size)
    if len(data) != member.compressed_size:
        raise ValueError("truncated ZIP member data")
    return data


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decode one ZIP method-6 (implode) member from an archive.",
    )
    parser.add_argument("archive", type=Path, help="path to the ZIP archive")
    parser.add_argument("member", nargs="?", help="member name inside the archive")
    parser.add_argument(
        "--encoding",
        default="cp437",
        help="text encoding for stdout when not using --output (default: cp437)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional output file; writes raw decoded bytes when provided",
    )
    parser.add_argument(
        "--tree-summary",
        action="store_true",
        help="print parsed tree layout to stderr before emitting content",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list archive members with ZIP offsets and metadata instead of decoding one member",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.list:
        for member in list_members(args.archive):
            print(
                f"{member.member_name}\tmethod={member.compression_method}\t"
                f"flags=0x{member.flag_bits:04X}\tlocal=0x{member.local_header_offset:06X}\t"
                f"data=0x{member.compressed_offset:06X}\tcompressed={member.compressed_size}\t"
                f"uncompressed={member.uncompressed_size}"
            )
        return 0

    if args.member is None:
        parser.error("member is required unless --list is used")

    member = locate_member(args.archive, args.member)
    if member.compression_method != 6:
        parser.error(
            f"{args.member} uses ZIP method {member.compression_method}, expected method 6"
        )
    if member.flag_bits & 0x0001:
        parser.error("encrypted implode members are not supported")
    if member.flag_bits & 0x0008:
        parser.error("streamed implode members with data descriptor are not supported")

    compressed_data = read_member_data(member)
    decoded, summaries, tree_bytes = decode_implode(
        compressed_data,
        member.flag_bits,
        member.uncompressed_size,
    )

    if args.tree_summary:
        print(
            f"member={member.member_name} flags=0x{member.flag_bits:04X} "
            f"compressed={member.compressed_size} uncompressed={member.uncompressed_size} "
            f"tree_bytes={tree_bytes}",
            file=sys.stderr,
        )
        for summary in summaries:
            print(
                f"  {summary.name}: values={summary.value_count} pairs={summary.pair_count} "
                f"bytes={summary.byte_start:#x}..{summary.byte_end:#x}",
                file=sys.stderr,
            )

    if args.output is not None:
        args.output.write_bytes(decoded)
        return 0

    text = decoded.decode(args.encoding, errors="replace")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())