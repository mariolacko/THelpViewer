#!/usr/bin/env python3
"""Unpack the DJP/LZO-packed GO32 image used by Scorpion's cheater.exe.

This helper mirrors the tiny DJP 1.07 / LZO 1.04 stub found in cheater.exe.
It is intentionally scoped to research workflows around the current Scorpion
23.0 binary, not to generic GO32 parsing.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes.util import find_library
from pathlib import Path


DEFAULT_COFF_BASE = 0x800
DEFAULT_COMPRESSED_OFFSET = 0x354
DEFAULT_COMPRESSED_LENGTH = 0x2F5F4
DEFAULT_UNPACKED_SIZE = 0xFA400
DEFAULT_ZERO_FILL = 0x200
DEFAULT_ENTRY_POINT = 0x10A8


_LZO_LIB: ctypes.CDLL | None | bool = None


def _parse_int(value: str) -> int:
    return int(value, 0)


def _copy_literals(src: bytes, ip: int, out: bytearray, op: int, count: int) -> tuple[int, int]:
    if count < 0:
        raise ValueError(f"negative literal count: {count}")
    if ip + count > len(src):
        raise ValueError("literal run exceeds compressed input")
    if op + count > len(out):
        raise ValueError("literal run exceeds output buffer")
    out[op : op + count] = src[ip : ip + count]
    return ip + count, op + count


def _copy_match(out: bytearray, op: int, match_pos: int, count: int) -> int:
    if count < 0:
        raise ValueError(f"negative match count: {count}")
    if match_pos < 0 or match_pos >= op:
        raise ValueError(f"invalid match position 0x{match_pos:X} at output 0x{op:X}")
    if op + count > len(out):
        raise ValueError("match copy exceeds output buffer")
    for _ in range(count):
        out[op] = out[match_pos]
        op += 1
        match_pos += 1
    return op


def _consume_extended_length(src: bytes, ip: int, seed: int) -> tuple[int, int]:
    length = seed
    while True:
        if ip >= len(src):
            raise ValueError("unexpected end of compressed input while extending length")
        value = src[ip]
        ip += 1
        if value != 0:
            return length + value, ip
        length += 0xFF


def _process_match_body(
    src: bytes,
    ip: int,
    out: bytearray,
    op: int,
    token: int,
    expected_output_size: int,
) -> tuple[bool, int, int]:
    if token >= 0x40:
        if ip >= len(src):
            raise ValueError("missing match distance byte")
        distance = 1 + ((token >> 2) & 7) + (src[ip] << 3)
        ip += 1
        length = (token >> 5) + 1
        op = _copy_match(out, op, op - distance, length)
        return False, ip, op

    if token >= 0x20:
        length = token & 0x1F
        if length == 0:
            length, ip = _consume_extended_length(src, ip, 33)
        else:
            length += 2
        if ip + 2 > len(src):
            raise ValueError("missing long-match distance word")
        distance = 1 + (int.from_bytes(src[ip : ip + 2], "little") >> 2)
        ip += 2
        op = _copy_match(out, op, op - distance, length)
        return False, ip, op

    if token >= 0x10:
        length = token & 7
        if length == 0:
            length, ip = _consume_extended_length(src, ip, 9)
        else:
            length += 2
        if ip + 2 > len(src):
            raise ValueError("missing far-match distance word")
        distance_word = ((token & 8) << 11) | int.from_bytes(src[ip : ip + 2], "little")
        ip += 2
        distance = distance_word >> 2
        if distance == 0:
            if length != 3 or op != expected_output_size:
                raise ValueError(
                    f"unexpected EOF marker: length={length} op=0x{op:X} expected=0x{expected_output_size:X}"
                )
            return True, ip, op
        op = _copy_match(out, op, op - 0x4000 - distance, length)
        return False, ip, op

    if ip >= len(src):
        raise ValueError("missing short-match distance byte")
    distance = 1 + (token >> 2) + (src[ip] << 2)
    ip += 1
    op = _copy_match(out, op, op - distance, 2)
    return False, ip, op


def _process_after_match(
    src: bytes,
    ip: int,
    out: bytearray,
    op: int,
    expected_output_size: int,
) -> tuple[bool, int, int]:
    while True:
        trailing_literals = src[ip - 2] & 3
        if trailing_literals == 0:
            return False, ip, op
        ip, op = _copy_literals(src, ip, out, op, trailing_literals)
        if ip >= len(src):
            raise ValueError("missing post-match token")
        token = src[ip]
        ip += 1
        done, ip, op = _process_match_body(src, ip, out, op, token, expected_output_size)
        if done:
            return True, ip, op


def _load_lzo_library() -> ctypes.CDLL | None:
    global _LZO_LIB
    if _LZO_LIB is False:
        return None
    if isinstance(_LZO_LIB, ctypes.CDLL):
        return _LZO_LIB

    candidates = [
        find_library("lzo2"),
        "/opt/homebrew/opt/lzo/lib/liblzo2.dylib",
        "/usr/local/opt/lzo/lib/liblzo2.dylib",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            library = ctypes.CDLL(candidate)
        except OSError:
            continue
        library.lzo_init.restype = ctypes.c_int
        library.lzo1x_decompress_safe.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.c_void_p,
        ]
        library.lzo1x_decompress_safe.restype = ctypes.c_int
        try:
            init_symbol = library.lzo_init
        except AttributeError:
            init_symbol = None
        if init_symbol is not None:
            init_symbol.restype = ctypes.c_int
            if init_symbol() != 0:
                continue
        _LZO_LIB = library
        return library

    _LZO_LIB = False
    return None


def _unpack_djp_lzo_system(payload: bytes, expected_output_size: int) -> bytes:
    library = _load_lzo_library()
    if library is None:
        raise RuntimeError("liblzo2 is not available")

    source_buffer = ctypes.create_string_buffer(payload)
    output_buffer = ctypes.create_string_buffer(expected_output_size)
    output_size = ctypes.c_size_t(expected_output_size)
    status = library.lzo1x_decompress_safe(
        ctypes.byref(source_buffer),
        len(payload),
        ctypes.byref(output_buffer),
        ctypes.byref(output_size),
        None,
    )
    if status != 0:
        raise RuntimeError(f"liblzo2 returned status {status}")
    if output_size.value != expected_output_size:
        raise RuntimeError(
            f"liblzo2 produced 0x{output_size.value:X} bytes, expected 0x{expected_output_size:X}"
        )
    return output_buffer.raw[: output_size.value]


def _unpack_djp_lzo_pure(payload: bytes, expected_output_size: int) -> bytes:
    ip = 0
    op = 0
    out = bytearray(expected_output_size)

    if not payload:
        raise ValueError("compressed payload is empty")

    token = payload[ip]
    ip += 1
    if token > 17:
        literal_count = token - 17
        if literal_count < 4:
            ip, op = _copy_literals(payload, ip, out, op, literal_count)
            if ip >= len(payload):
                raise ValueError("missing token after initial literal run")
            token = payload[ip]
            ip += 1
            done, ip, op = _process_match_body(payload, ip, out, op, token, expected_output_size)
            if not done:
                done, ip, op = _process_after_match(payload, ip, out, op, expected_output_size)
            if done:
                if ip != len(payload):
                    raise ValueError(f"EOF marker hit early at compressed offset 0x{ip:X} of 0x{len(payload):X}")
                return bytes(out)
        else:
            ip, op = _copy_literals(payload, ip, out, op, literal_count)

    while True:
        if ip >= len(payload):
            raise ValueError("missing top-level token")
        token = payload[ip]
        ip += 1
        if token >= 16:
            done, ip, op = _process_match_body(payload, ip, out, op, token, expected_output_size)
            if done:
                break
            done, ip, op = _process_after_match(payload, ip, out, op, expected_output_size)
            if done:
                break
            continue

        if token == 0:
            literal_count, ip = _consume_extended_length(payload, ip, 18)
        else:
            literal_count = token + 3
        ip, op = _copy_literals(payload, ip, out, op, literal_count)

        if ip >= len(payload):
            raise ValueError("missing token after literal run")
        token = payload[ip]
        ip += 1
        if token >= 16:
            done, ip, op = _process_match_body(payload, ip, out, op, token, expected_output_size)
            if done:
                break
            done, ip, op = _process_after_match(payload, ip, out, op, expected_output_size)
            if done:
                break
            continue

        if ip >= len(payload):
            raise ValueError("missing first-literal-run distance byte")
        distance = 0x801 + (token >> 2) + (payload[ip] << 2)
        ip += 1
        op = _copy_match(out, op, op - distance, 3)
        done, ip, op = _process_after_match(payload, ip, out, op, expected_output_size)
        if done:
            break

    if op != expected_output_size:
        raise ValueError(f"unpacked size mismatch: got 0x{op:X}, expected 0x{expected_output_size:X}")
    if ip != len(payload):
        raise ValueError(f"compressed input not fully consumed: 0x{ip:X} of 0x{len(payload):X}")
    return bytes(out)


def unpack_djp_lzo(payload: bytes, expected_output_size: int) -> bytes:
    try:
        return _unpack_djp_lzo_system(payload, expected_output_size)
    except Exception:
        return _unpack_djp_lzo_pure(payload, expected_output_size)


def _search_strings(payload: bytes, needles: list[str], max_hits: int) -> None:
    if not needles:
        return
    print("STRING SEARCH")
    for needle in needles:
        encoded = needle.encode("latin-1")
        hits: list[int] = []
        start = 0
        while True:
            position = payload.find(encoded, start)
            if position < 0:
                break
            hits.append(position)
            if len(hits) >= max_hits:
                break
            start = position + 1
        printable_hits = ", ".join(f"0x{hit:X}" for hit in hits) if hits else "-"
        print(f"  {needle!r}: {printable_hits}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", help="Path to the packed DJP executable, for example cheater.exe")
    parser.add_argument("--output", help="Optional output path for the unpacked flat image")
    parser.add_argument("--coff-base", type=_parse_int, default=DEFAULT_COFF_BASE)
    parser.add_argument("--compressed-offset", type=_parse_int, default=DEFAULT_COMPRESSED_OFFSET)
    parser.add_argument("--compressed-length", type=_parse_int, default=DEFAULT_COMPRESSED_LENGTH)
    parser.add_argument("--unpacked-size", type=_parse_int, default=DEFAULT_UNPACKED_SIZE)
    parser.add_argument("--zero-fill", type=_parse_int, default=DEFAULT_ZERO_FILL)
    parser.add_argument("--entry-point", type=_parse_int, default=DEFAULT_ENTRY_POINT)
    parser.add_argument("--string", dest="strings", action="append", default=[])
    parser.add_argument("--max-hits", type=int, default=8)
    args = parser.parse_args()

    data = Path(args.executable).read_bytes()
    start = args.coff_base + args.compressed_offset
    stop = start + args.compressed_length
    if stop > len(data):
        raise SystemExit(
            f"compressed slice 0x{start:X}-0x{stop:X} exceeds file size 0x{len(data):X}"
        )

    unpacked = unpack_djp_lzo(data[start:stop], args.unpacked_size)
    if args.zero_fill > 0:
        unpacked += b"\x00" * args.zero_fill

    print(f"file:           {args.executable}")
    print(f"coff-base:      0x{args.coff_base:X}")
    print(f"input-range:    0x{start:X}-0x{stop:X}")
    print(f"unpacked-size:  0x{len(unpacked):X}")
    print(f"entry-point:    0x{args.entry_point:X}")
    entry_offset = args.entry_point - 0x1000
    if 0 <= entry_offset < len(unpacked):
        print(f"entry-bytes:    {unpacked[entry_offset:entry_offset + 16].hex()}")
    print()

    _search_strings(unpacked, args.strings, max(1, args.max_hits))

    if args.output:
        output_path = Path(args.output)
        output_path.write_bytes(unpacked)
        print(f"wrote:          {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())