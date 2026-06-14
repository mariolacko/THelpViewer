"""Version-specific readers for Scorpions Cheater v6-v14 SCO/SCD binaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..base import HelpDocument
from .scorpion_legacy_reader import (
    ScorpionLegacyProfile,
    ScorpionVersionReaderBase,
    _build_preview_document,
    _build_sco_text_document,
    _sco_decoded_text,
)


SCORPION_LZHUF_WINDOW_SIZE = 4096
SCORPION_LZHUF_LOOKAHEAD_SIZE = 60
SCORPION_LZHUF_THRESHOLD = 2
SCORPION_LZHUF_CHAR_COUNT = 256 - SCORPION_LZHUF_THRESHOLD + SCORPION_LZHUF_LOOKAHEAD_SIZE
SCORPION_LZHUF_TREE_SIZE = SCORPION_LZHUF_CHAR_COUNT * 2 - 1
SCORPION_LZHUF_ROOT = SCORPION_LZHUF_TREE_SIZE - 1
SCORPION_LZHUF_MAX_FREQ = 0x8000
SCORPION_LZHUF_MAX_OUTPUT_SIZE = 8_000_000
SCORPION_LZHUF_POSITION_LENGTHS = (
    (3, 4, 4, 4)
    + (5,) * 8
    + (6,) * 12
    + (7,) * 24
    + (8,) * 16
)
SCORPION_LZHUF_POSITION_CODES = (
    0x00,
    0x20,
    0x30,
    0x40,
    0x50,
    0x58,
    0x60,
    0x68,
    0x70,
    0x78,
    0x80,
    0x88,
    0x90,
    0x94,
    0x98,
    0x9C,
    0xA0,
    0xA4,
    0xA8,
    0xAC,
    0xB0,
    0xB4,
    0xB8,
    0xBC,
    0xC0,
    0xC2,
    0xC4,
    0xC6,
    0xC8,
    0xCA,
    0xCC,
    0xCE,
    0xD0,
    0xD2,
    0xD4,
    0xD6,
    0xD8,
    0xDA,
    0xDC,
    0xDE,
    0xE0,
    0xE2,
    0xE4,
    0xE6,
    0xE8,
    0xEA,
    0xEC,
    0xEE,
    0xF0,
    0xF1,
    0xF2,
    0xF3,
    0xF4,
    0xF5,
    0xF6,
    0xF7,
    0xF8,
    0xF9,
    0xFA,
    0xFB,
    0xFC,
    0xFD,
    0xFE,
    0xFF,
)


@dataclass(frozen=True, slots=True)
class ScorpionLzhufBlock:
    header_offset: int
    data_offset: int
    next_offset: int
    header: bytes
    decoded: bytes
    decoded_size: int
    input_position: int
    unread_bits: int


def _build_lzhuf_decode_tables() -> tuple[tuple[int, ...], tuple[int, ...]]:
    code_table = [0] * 256
    length_table = [0] * 256
    for code, (prefix, bit_length) in enumerate(
        zip(SCORPION_LZHUF_POSITION_CODES, SCORPION_LZHUF_POSITION_LENGTHS)
    ):
        for value in range(prefix, prefix + (1 << (8 - bit_length))):
            code_table[value] = code
            length_table[value] = bit_length
    return tuple(code_table), tuple(length_table)


SCORPION_LZHUF_DECODE_CODES, SCORPION_LZHUF_DECODE_LENGTHS = _build_lzhuf_decode_tables()


class _ScorpionLzhufBitStream:
    def __init__(self, data: bytes, start_offset: int):
        self.data = data
        self.pos = start_offset
        self.buffer = 0
        self.bits_left = 0

    def _read_byte(self) -> int:
        if self.pos >= len(self.data):
            return 0
        value = self.data[self.pos]
        self.pos += 1
        return value

    def get_bit(self) -> int:
        while self.bits_left <= 8:
            self.buffer = (self.buffer | (self._read_byte() << (8 - self.bits_left))) & 0xFFFF
            self.bits_left += 8
        value = self.buffer
        self.buffer = (self.buffer << 1) & 0xFFFF
        self.bits_left -= 1
        return (value & 0x8000) >> 15

    def get_byte(self) -> int:
        while self.bits_left <= 8:
            self.buffer = (self.buffer | (self._read_byte() << (8 - self.bits_left))) & 0xFFFF
            self.bits_left += 8
        value = self.buffer
        self.buffer = (self.buffer << 8) & 0xFFFF
        self.bits_left -= 8
        return (value & 0xFF00) >> 8


class _ScorpionLzhufDecoder:
    def __init__(self, data: bytes, start_offset: int):
        self.bits = _ScorpionLzhufBitStream(data, start_offset)
        self.freq = [0] * (SCORPION_LZHUF_TREE_SIZE + 1)
        self.parents = [0] * (SCORPION_LZHUF_TREE_SIZE + SCORPION_LZHUF_CHAR_COUNT)
        self.children = [0] * SCORPION_LZHUF_TREE_SIZE
        self.text_buffer = bytearray(
            [0x20] * (SCORPION_LZHUF_WINDOW_SIZE + SCORPION_LZHUF_LOOKAHEAD_SIZE - 1)
        )

    def _start_huffman(self) -> None:
        for index in range(SCORPION_LZHUF_CHAR_COUNT):
            self.freq[index] = 1
            self.children[index] = index + SCORPION_LZHUF_TREE_SIZE
            self.parents[index + SCORPION_LZHUF_TREE_SIZE] = index

        source_index = 0
        node_index = SCORPION_LZHUF_CHAR_COUNT
        while node_index <= SCORPION_LZHUF_ROOT:
            self.freq[node_index] = self.freq[source_index] + self.freq[source_index + 1]
            self.children[node_index] = source_index
            self.parents[source_index] = node_index
            self.parents[source_index + 1] = node_index
            source_index += 2
            node_index += 1

        self.freq[SCORPION_LZHUF_TREE_SIZE] = 0xFFFF
        self.parents[SCORPION_LZHUF_ROOT] = 0

    def _reconstruct_huffman_tree(self) -> None:
        output_index = 0
        for index in range(SCORPION_LZHUF_TREE_SIZE):
            if self.children[index] >= SCORPION_LZHUF_TREE_SIZE:
                self.freq[output_index] = (self.freq[index] + 1) // 2
                self.children[output_index] = self.children[index]
                output_index += 1

        source_index = 0
        node_index = SCORPION_LZHUF_CHAR_COUNT
        while node_index < SCORPION_LZHUF_TREE_SIZE:
            following_index = source_index + 1
            frequency = self.freq[source_index] + self.freq[following_index]
            self.freq[node_index] = frequency

            insert_index = node_index - 1
            while frequency < self.freq[insert_index]:
                insert_index -= 1
            insert_index += 1

            self.freq[insert_index + 1 : node_index + 1] = self.freq[insert_index:node_index]
            self.freq[insert_index] = frequency
            self.children[insert_index + 1 : node_index + 1] = self.children[insert_index:node_index]
            self.children[insert_index] = source_index

            source_index += 2
            node_index += 1

        for index in range(SCORPION_LZHUF_TREE_SIZE):
            child = self.children[index]
            if child >= SCORPION_LZHUF_TREE_SIZE:
                self.parents[child] = index
            else:
                self.parents[child] = index
                self.parents[child + 1] = index

    def _update_huffman_tree(self, code: int) -> None:
        if self.freq[SCORPION_LZHUF_ROOT] == SCORPION_LZHUF_MAX_FREQ:
            self._reconstruct_huffman_tree()

        node = self.parents[code + SCORPION_LZHUF_TREE_SIZE]
        while node:
            self.freq[node] += 1
            frequency = self.freq[node]
            next_node = node + 1
            if frequency > self.freq[next_node]:
                while frequency > self.freq[next_node + 1]:
                    next_node += 1
                self.freq[node] = self.freq[next_node]
                self.freq[next_node] = frequency

                child = self.children[node]
                self.parents[child] = next_node
                if child < SCORPION_LZHUF_TREE_SIZE:
                    self.parents[child + 1] = next_node

                swapped_child = self.children[next_node]
                self.children[next_node] = child
                self.parents[swapped_child] = node
                if swapped_child < SCORPION_LZHUF_TREE_SIZE:
                    self.parents[swapped_child + 1] = node
                self.children[node] = swapped_child

                node = next_node
            node = self.parents[node]

    def _decode_char(self) -> int:
        code = self.children[SCORPION_LZHUF_ROOT]
        while code < SCORPION_LZHUF_TREE_SIZE:
            code += self.bits.get_bit()
            code = self.children[code]
        code -= SCORPION_LZHUF_TREE_SIZE
        self._update_huffman_tree(code)
        return code

    def _decode_position(self) -> int:
        value = self.bits.get_byte()
        code = SCORPION_LZHUF_DECODE_CODES[value] << 6
        bit_count = SCORPION_LZHUF_DECODE_LENGTHS[value] - 2
        while bit_count:
            value = (value << 1) + self.bits.get_bit()
            bit_count -= 1
        return code | (value & 0x3F)

    def decode(self) -> tuple[bytes, int, int]:
        if self.bits.pos + 4 > len(self.bits.data):
            raise ValueError("short-lzhuf-header")
        expected_size = int.from_bytes(self.bits.data[self.bits.pos : self.bits.pos + 4], "little")
        if expected_size <= 0 or expected_size > SCORPION_LZHUF_MAX_OUTPUT_SIZE:
            raise ValueError(f"bad-lzhuf-size:{expected_size}")
        self.bits.pos += 4

        self._start_huffman()
        output = bytearray()
        ring_pos = SCORPION_LZHUF_WINDOW_SIZE - SCORPION_LZHUF_LOOKAHEAD_SIZE

        while len(output) < expected_size:
            code = self._decode_char()
            if code < 256:
                output.append(code)
                self.text_buffer[ring_pos] = code
                ring_pos = (ring_pos + 1) & (SCORPION_LZHUF_WINDOW_SIZE - 1)
                continue

            source_pos = (ring_pos - self._decode_position() - 1) & (SCORPION_LZHUF_WINDOW_SIZE - 1)
            length = code - 255 + SCORPION_LZHUF_THRESHOLD
            for index in range(length):
                value = self.text_buffer[(source_pos + index) & (SCORPION_LZHUF_WINDOW_SIZE - 1)]
                output.append(value)
                self.text_buffer[ring_pos] = value
                ring_pos = (ring_pos + 1) & (SCORPION_LZHUF_WINDOW_SIZE - 1)
                if len(output) >= expected_size:
                    break

        return bytes(output), self.bits.pos, self.bits.bits_left


def _lzhuf_prefixed_header_length(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 3 > len(data):
        return 0
    if data.startswith((b"CHT", b"JOK"), offset):
        return 3
    if not data.startswith(b"HLP", offset):
        return 0
    if offset + 6 <= len(data) and data[offset + 3 : offset + 6].isdigit():
        return 6
    return 3


def _lzhuf_block_size(data: bytes, offset: int) -> int | None:
    if offset + 4 > len(data):
        return None
    size = int.from_bytes(data[offset : offset + 4], "little")
    if size <= 0 or size > SCORPION_LZHUF_MAX_OUTPUT_SIZE:
        return None
    return size


def _decode_lzhuf_block(data: bytes, offset: int) -> tuple[bytes, int, int] | None:
    if _lzhuf_block_size(data, offset) is None:
        return None
    try:
        return _ScorpionLzhufDecoder(data, offset).decode()
    except (IndexError, ValueError):
        return None


def _next_lzhuf_header_offset(data: bytes, current_offset: int, input_position: int, unread_bits: int) -> int:
    candidates = [
        input_position - unread_bits // 8,
        input_position,
        input_position - 1,
        input_position + 1,
    ]
    seen: set[int] = set()
    for candidate in candidates:
        if candidate in seen or candidate <= current_offset:
            continue
        seen.add(candidate)
        if _lzhuf_prefixed_header_length(data, candidate):
            return candidate
    return input_position


def _decode_lzhuf_prefixed_blocks(data: bytes) -> list[ScorpionLzhufBlock]:
    blocks: list[ScorpionLzhufBlock] = []
    offset = 0
    while offset < len(data):
        header_length = _lzhuf_prefixed_header_length(data, offset)
        if not header_length:
            break
        data_offset = offset + header_length
        decoded_result = _decode_lzhuf_block(data, data_offset)
        if decoded_result is None:
            break
        decoded, input_position, unread_bits = decoded_result
        next_offset = _next_lzhuf_header_offset(data, offset, input_position, unread_bits)
        blocks.append(
            ScorpionLzhufBlock(
                header_offset=offset,
                data_offset=data_offset,
                next_offset=next_offset,
                header=data[offset:data_offset],
                decoded=decoded,
                decoded_size=len(decoded),
                input_position=input_position,
                unread_bits=unread_bits,
            )
        )
        if next_offset <= offset or next_offset >= len(data) or not _lzhuf_prefixed_header_length(data, next_offset):
            break
        offset = next_offset
    return blocks


def _decode_lzhuf_source_blocks(source_name: str, data: bytes) -> list[ScorpionLzhufBlock]:
    suffix = Path(source_name).suffix.lower()
    if suffix == ".scd":
        decoded_result = _decode_lzhuf_block(data, 0)
        if decoded_result is None:
            return []
        decoded, input_position, unread_bits = decoded_result
        return [
            ScorpionLzhufBlock(
                header_offset=0,
                data_offset=0,
                next_offset=input_position,
                header=b"",
                decoded=decoded,
                decoded_size=len(decoded),
                input_position=input_position,
                unread_bits=unread_bits,
            )
        ]
    if suffix == ".sco":
        return _decode_lzhuf_prefixed_blocks(data)
    return []


def _build_sco_lzhuf_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
) -> HelpDocument | None:
    blocks = _decode_lzhuf_source_blocks(source_name, data)
    if not blocks:
        return None

    decoded_text = "\n".join(_sco_decoded_text(block.decoded).rstrip("\x00") for block in blocks)
    document = _build_sco_text_document(
        profile,
        source_name,
        data,
        decoded_text,
        parser_name="sco-lzhuf",
        parser_metadata={
            "scorpion_compression": "lzhuf",
            "scorpion_lzhuf_block_count": len(blocks),
            "scorpion_lzhuf_blocks": [
                {
                    "header_offset": block.header_offset,
                    "data_offset": block.data_offset,
                    "next_offset": block.next_offset,
                    "header": block.header.decode("ascii", errors="replace"),
                    "decoded_size": block.decoded_size,
                    "input_position": block.input_position,
                    "unread_bits": block.unread_bits,
                }
                for block in blocks
            ],
            "scorpion_lzhuf_decoded_size": sum(block.decoded_size for block in blocks),
        },
    )
    return document


class ScorpionV6LzhufReaderBase(ScorpionVersionReaderBase):
    def read_bytes(self, data: bytes):
        document = _build_sco_lzhuf_document(self.profile, self.source_path.name, data)
        if document is not None:
            return self._finalize_document(document)
        return self._finalize_document(_build_preview_document(self.profile, self.source_path.name, data))


class ScorpionV6Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV7Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV8Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV10Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV11Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV12Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV13Reader(ScorpionV6LzhufReaderBase):
    pass


class ScorpionV14Reader(ScorpionV6LzhufReaderBase):
    pass
