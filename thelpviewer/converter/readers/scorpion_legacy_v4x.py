"""Version-specific readers for Scorpions Cheater v4-v5 SCO binaries."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from ..base import HelpDocument
from .scorpion_legacy_reader import (
    ScorpionLegacyProfile,
    ScorpionVersionReaderBase,
    _build_preview_document,
    _build_sco_text_document,
    _sco_decoded_text,
)


SCORPION_SCO_SIGNATURE = b"SCORPION\x00\x01"
SCORPION_SCO_HUFFMAN_TABLE_OFFSET = len(SCORPION_SCO_SIGNATURE)
SCORPION_SCO_HUFFMAN_SYMBOL_COUNT = 256
SCORPION_SCO_HUFFMAN_TABLE_SIZE = SCORPION_SCO_HUFFMAN_SYMBOL_COUNT * 2
SCORPION_SCO_HUFFMAN_STREAM_OFFSET = (
    SCORPION_SCO_HUFFMAN_TABLE_OFFSET + SCORPION_SCO_HUFFMAN_TABLE_SIZE + 0x100
)
SCORPION_SCO_HUFFMAN_STREAM_BIT_OFFSET = 0
SCORPION_SCO_PROBE_CANDIDATE_OFFSETS = (0x0A, 0x20, 0x40, 0x80, 0x100, 0x180, 0x200, 0x280, 0x300, 0x400)
SCORPION_SCO_HEADER_CANDIDATE_WORDS = 48
SCORPION_SCO_HEADER_SCALES = (1, 2, 4, 8, 16)


@dataclass(frozen=True, slots=True)
class ScorpionScoHuffmanEntry:
    start: int
    end: int
    bit_length: int
    symbol: int


class _ScorpionCheater4BitStream:
    def __init__(self, data: bytes, start_offset: int):
        self.data = data
        self.pos = start_offset
        self.buffer = 0
        self.bits_left = 0

    def read_u8(self) -> int:
        if self.pos >= len(self.data):
            raise EOFError()
        value = self.data[self.pos]
        self.pos += 1
        return value

    def _refill(self) -> None:
        if self.pos + 2 > len(self.data):
            raise EOFError()
        self.buffer = int.from_bytes(self.data[self.pos : self.pos + 2], "little")
        self.pos += 2
        self.bits_left = 16

    def get_bit(self) -> int:
        if self.bits_left == 0:
            self._refill()
        bit = 1 if (self.buffer & 0x8000) else 0
        self.buffer = (self.buffer << 1) & 0xFFFF
        self.bits_left -= 1
        return bit

    def get_bits(self, bit_count: int) -> int:
        value = 0
        for _ in range(bit_count):
            value = (value << 1) | self.get_bit()
        return value


def _sco_header_word_preview(data: bytes, *, count: int = 24) -> list[int]:
    if not data.startswith(SCORPION_SCO_SIGNATURE):
        return []

    words: list[int] = []
    offset = len(SCORPION_SCO_SIGNATURE)
    for _ in range(count):
        if offset + 2 > len(data):
            break
        words.append(int.from_bytes(data[offset : offset + 2], "little", signed=True))
        offset += 2
    return words


def _collect_sco_word_x2_offsets(data: bytes, *, count: int = 48) -> list[dict[str, int]]:
    if not data.startswith(SCORPION_SCO_SIGNATURE):
        return []

    offsets: list[dict[str, int]] = []
    seen_offsets: set[int] = set()
    offset = len(SCORPION_SCO_SIGNATURE)

    for index in range(count):
        if offset + 2 > len(data):
            break
        signed_value = int.from_bytes(data[offset : offset + 2], "little", signed=True)
        magnitude = abs(signed_value)
        block_offset = magnitude * 2
        if 10 <= block_offset < len(data) and block_offset not in seen_offsets:
            seen_offsets.add(block_offset)
            offsets.append({"index": index, "word": signed_value, "offset": block_offset})
        offset += 2

    offsets.sort(key=lambda item: int(item["offset"]))
    return offsets


def _analyze_sco_header_layout(data: bytes, *, count: int = 48) -> dict[str, list[dict[str, int]]]:
    if not data.startswith(SCORPION_SCO_SIGNATURE):
        return {"word_x2_offsets": [], "paragraph_offsets": []}

    word_x2_offsets = _collect_sco_word_x2_offsets(data, count=count)
    paragraph_offsets: list[dict[str, int]] = []
    seen_paragraph: set[int] = set()
    offset = len(SCORPION_SCO_SIGNATURE)

    for index in range(count):
        if offset + 2 > len(data):
            break
        raw = data[offset : offset + 2]
        big_endian_value = int.from_bytes(raw, "big", signed=False)
        paragraph_offset = big_endian_value * 16
        if 0 < big_endian_value < 0x1000 and 10 <= paragraph_offset < len(data):
            if paragraph_offset not in seen_paragraph:
                seen_paragraph.add(paragraph_offset)
                paragraph_offsets.append(
                    {"index": index, "word": big_endian_value, "offset": paragraph_offset}
                )
        offset += 2

    return {
        "word_x2_offsets": word_x2_offsets[:12],
        "paragraph_offsets": paragraph_offsets[:12],
    }


def _printable_ratio(payload: bytes) -> float:
    if not payload:
        return 0.0
    printable = sum(
        1
        for byte in payload
        if byte in {0x09, 0x0A, 0x0D} or 0x20 <= byte <= 0x7E or byte >= 0xA0
    )
    return printable / len(payload)


def _probe_preview_text(payload: bytes, *, limit: int = 200) -> str:
    if not payload:
        return ""
    return (
        payload[:limit]
        .decode("cp852", errors="replace")
        .replace("\r", r"\r")
        .replace("\n", r"\n")
    )


def _decode_cheater4_long_offset(bits: _ScorpionCheater4BitStream) -> int:
    value = bits.get_bits(3)
    if value <= 2:
        bit_count = value + 5
        base = (1 << bit_count) - 0x1F
        return base + bits.get_bits(bit_count)
    if value == 3:
        bit_count = 8 + bits.get_bit()
        base = (1 << bit_count) - 0x1F
        return base + bits.get_bits(bit_count)
    if value == 4:
        bit_count = 10 + bits.get_bit()
        base = (1 << bit_count) - 0x1F
        return base + bits.get_bits(bit_count)
    if value in {5, 6}:
        bit_count = value + 7
        base = (1 << bit_count) - 0x1F
        return base + bits.get_bits(bit_count)
    return 0x3FE1 + bits.get_bits(15)


def _decode_cheater4_variable_length(bits: _ScorpionCheater4BitStream) -> int:
    if bits.get_bit() == 0:
        return 4 + bits.get_bit()

    value = bits.get_bits(3)
    if value:
        return value + 5

    value = bits.get_bits(4)
    if value:
        return value + 12

    bit_count = 4
    base = 0x0C
    while bit_count != 7:
        base = (base + 2) * 2
        if bits.get_bit():
            return base + bits.get_bits(bit_count + 1)
        bit_count += 1
    return bits.get_bits(14)


def _copy_from_output_window(output: bytearray, offset: int, length: int) -> None:
    if offset <= 0 or offset > len(output):
        raise ValueError(f"bad-offset:{offset}")
    start = len(output) - offset
    for index in range(length):
        output.append(output[start + index])


def _cheater4_recent_distinct_byte(output: bytearray, rank: int, seen_table: bytearray, generation: int) -> tuple[int, int]:
    generation = (generation + 1) & 0xFF
    if generation == 0:
        seen_table[:] = b"\x00" * 256
        generation = 1

    for value in reversed(output):
        if seen_table[value] == generation:
            continue
        seen_table[value] = generation
        if rank == 0:
            return value, generation
        rank -= 1
    raise ValueError("distinct-rank-underflow")


def _probe_cheater4_decompressor(data: bytes, *, start_offset: int, output_limit: int = 8192) -> dict[str, object]:
    bits = _ScorpionCheater4BitStream(data, start_offset)
    output = bytearray()
    seen_table = bytearray(256)
    generation = 0xFF
    reason = "limit"
    detail = None

    try:
        while len(output) < output_limit:
            if bits.get_bit() == 0:
                output.append(bits.read_u8())
                continue

            token = bits.get_bits(2)
            if token == 2:
                rank = bits.get_bits(4)
                value, generation = _cheater4_recent_distinct_byte(output, rank, seen_table, generation)
                output.append(value)
                continue

            if token == 3:
                offset_class = bits.get_bits(2)
                if offset_class <= 1:
                    bit_count = offset_class + 5
                    base = 1 + 32 * offset_class
                else:
                    bit_count = offset_class + 6
                    base = 97 + 256 * (offset_class - 2)
                raw_offset = bits.get_bits(bit_count)
                if offset_class == 3 and raw_offset == 0x1FF:
                    reason = "end-marker"
                    break
                _copy_from_output_window(output, base + raw_offset, 2)
                continue

            offset = _decode_cheater4_long_offset(bits)
            length = 3 if token == 1 else _decode_cheater4_variable_length(bits)
            _copy_from_output_window(output, offset, length)
    except EOFError:
        reason = "eof"
    except ValueError as exc:
        text = str(exc)
        if text.startswith("bad-offset:"):
            reason = "bad-offset"
            detail = text.split(":", 1)[1]
        else:
            reason = "probe-error"
            detail = text

    printable_ratio = round(_printable_ratio(output), 3)
    output_length = len(output)
    quality_score = round(min(output_length, 64) * printable_ratio, 3)

    return {
        "start_offset": start_offset,
        "output_length": output_length,
        "printable_ratio": printable_ratio,
        "quality_score": quality_score,
        "reason": reason,
        "detail": detail,
        "input_position": bits.pos,
        "preview_text": _probe_preview_text(output),
    }


def _probe_best_cheater4_block(data: bytes, *, max_skip: int = 15) -> dict[str, object]:
    best_probe: dict[str, object] | None = None
    best_key: tuple[float, int, float, int] | None = None
    for skip in range(min(max_skip + 1, len(data))):
        probe = _probe_cheater4_decompressor(data, start_offset=skip)
        sort_key = (
            float(probe["quality_score"]),
            int(probe["output_length"]),
            float(probe["printable_ratio"]),
            -skip,
        )
        if best_key is None or sort_key > best_key:
            best_key = sort_key
            best_probe = probe
    if best_probe is None:
        best_probe = _probe_cheater4_decompressor(data, start_offset=0)
    best_probe = dict(best_probe)
    best_probe["block_skip"] = int(best_probe["start_offset"])
    return best_probe


def _collect_sco_signed_header_candidates(data: bytes) -> list[dict[str, object]]:
    if not data.startswith(SCORPION_SCO_SIGNATURE):
        return []

    candidates: list[dict[str, object]] = []
    header_offset = len(SCORPION_SCO_SIGNATURE)
    seen_offsets: set[int] = set()
    for word_index in range(SCORPION_SCO_HEADER_CANDIDATE_WORDS):
        offset = header_offset + word_index * 2
        if offset + 2 > len(data):
            break
        value = int.from_bytes(data[offset : offset + 2], "little", signed=True)
        magnitude = abs(value)
        if magnitude < 10:
            continue
        for scale in SCORPION_SCO_HEADER_SCALES:
            start_offset = magnitude * scale
            if not (10 <= start_offset < len(data)):
                continue
            if start_offset in seen_offsets:
                continue
            seen_offsets.add(start_offset)
            candidates.append(
                {
                    "start_offset": start_offset,
                    "source_kind": "header-word-scale",
                    "header_word_index": word_index,
                    "header_word_value": value,
                    "header_scale": scale,
                }
            )
    return candidates


def _collect_sco_block_candidates(data: bytes) -> list[dict[str, object]]:
    word_x2_offsets = _collect_sco_word_x2_offsets(data, count=SCORPION_SCO_HEADER_CANDIDATE_WORDS)
    if len(word_x2_offsets) < 2:
        return []

    candidates: list[dict[str, object]] = []
    seen_blocks: set[tuple[int, int]] = set()
    for current, following in zip(word_x2_offsets, word_x2_offsets[1:]):
        block_start = int(current["offset"])
        block_end = int(following["offset"])
        if block_end <= block_start:
            continue
        if (block_start, block_end) in seen_blocks:
            continue
        seen_blocks.add((block_start, block_end))

        block = data[block_start:block_end]
        if len(block) < 4:
            continue

        probe = _probe_best_cheater4_block(block)
        probe.update(
            {
                "start_offset": block_start,
                "source_kind": "header-word-x2-block",
                "header_word_index": int(current["index"]),
                "header_word_value": int(current["word"]),
                "block_start": block_start,
                "block_end": block_end,
                "block_length": len(block),
            }
        )
        candidates.append(probe)
    return candidates


def _collect_sco_probe_candidates(data: bytes, *, limit: int = 5) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    seen_offsets: set[int] = set()

    for start_offset in SCORPION_SCO_PROBE_CANDIDATE_OFFSETS:
        if start_offset >= len(data):
            continue
        if start_offset in seen_offsets:
            continue
        seen_offsets.add(start_offset)
        probe = _probe_cheater4_decompressor(data, start_offset=start_offset)
        probe["source_kind"] = "fixed-offset"
        candidates.append(probe)

    for candidate in _collect_sco_signed_header_candidates(data):
        start_offset = int(candidate["start_offset"])
        if start_offset in seen_offsets:
            continue
        seen_offsets.add(start_offset)
        probe = _probe_cheater4_decompressor(data, start_offset=start_offset)
        probe.update(candidate)
        candidates.append(probe)

    candidates.extend(_collect_sco_block_candidates(data))

    candidates.sort(
        key=lambda item: (
            -float(item["quality_score"]),
            -int(item["output_length"]),
            -float(item["printable_ratio"]),
            int(item["start_offset"]),
        )
    )

    if len(candidates) <= limit:
        return candidates

    selected: list[dict[str, object]] = []
    selected_ids: set[int] = set()
    selected_kinds: set[str] = set()

    for candidate in candidates:
        source_kind = str(candidate.get("source_kind") or "unknown")
        if source_kind in selected_kinds:
            continue
        selected.append(candidate)
        selected_ids.add(id(candidate))
        selected_kinds.add(source_kind)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for candidate in candidates:
            marker = id(candidate)
            if marker in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(marker)
            if len(selected) >= limit:
                break

    selected.sort(
        key=lambda item: (
            -float(item["quality_score"]),
            -int(item["output_length"]),
            -float(item["printable_ratio"]),
            int(item["start_offset"]),
        )
    )
    return selected


def _append_sco_probe_details(document: HelpDocument, data: bytes) -> HelpDocument:
    if not document.topics:
        return document

    topic = document.topics[0]
    metadata = document.metadata
    header_words = _sco_header_word_preview(data)
    header_layout = _analyze_sco_header_layout(data)
    probe_candidates = _collect_sco_probe_candidates(data)
    best_candidate = probe_candidates[0] if probe_candidates else None

    metadata["scorpion_container_signature"] = "SCORPION\\x00\\x01"
    metadata["scorpion_header_word_preview"] = header_words
    metadata["scorpion_header_layout"] = header_layout
    metadata["scorpion_probe_decoder"] = "cheater4-lz"
    metadata["scorpion_probe_candidates"] = probe_candidates
    if best_candidate is not None:
        metadata["scorpion_probe_best_start"] = best_candidate["start_offset"]
        metadata["scorpion_probe_best_reason"] = best_candidate["reason"]
        metadata["scorpion_probe_best_ratio"] = best_candidate["printable_ratio"]
        metadata["scorpion_probe_best_output_length"] = best_candidate["output_length"]
        readable_candidate = (
            float(best_candidate["printable_ratio"]) >= 0.7 and int(best_candidate["output_length"]) >= 64
        )
        metadata["scorpion_probe_status"] = "candidate-readable" if readable_candidate else "candidate-unresolved"
    else:
        metadata["scorpion_probe_status"] = "no-candidates"

    extra_lines = [
        "",
        "SCO signature: SCORPION 00 01",
        "Header words (signed little-endian, first 24):",
    ]
    if header_words:
        for index in range(0, len(header_words), 8):
            extra_lines.append(", ".join(str(value) for value in header_words[index : index + 8]))
    else:
        extra_lines.append("No header-word preview available.")

    extra_lines.extend(["", "Header table candidates:"])
    word_x2_offsets = header_layout["word_x2_offsets"]
    if word_x2_offsets:
        extra_lines.append("Signed header words * 2 look like plausible in-file block starts:")
        extra_lines.append(
            ", ".join(
                f"#{entry['index']}={entry['word']} -> 0x{entry['offset']:03X}"
                for entry in word_x2_offsets[:8]
            )
        )
        offset_values = [entry["offset"] for entry in word_x2_offsets]
        extra_lines.append(
            f"Block-start spread: 0x{min(offset_values):03X}-0x{max(offset_values):03X} across "
            f"{len(offset_values)} unique candidates."
        )
    else:
        extra_lines.append("No plausible signed-word * 2 block-start candidates fit inside this file.")

    paragraph_offsets = header_layout["paragraph_offsets"]
    if paragraph_offsets:
        extra_lines.append("Zero-high-byte words still look like paragraph/segment-table candidates:")
        extra_lines.append(
            ", ".join(
                f"#{entry['index']}=0x{entry['word']:04X} -> 0x{entry['offset']:03X}"
                for entry in paragraph_offsets[:8]
            )
        )
    else:
        extra_lines.append("No compact big-endian paragraph candidates fit inside this file.")

    extra_lines.extend(
        [
            "",
            "CHEATER4 decompressor model:",
            "bitstream: MSB-first over little-endian 16-bit words",
            "1 + 00: long-offset back-reference with variable length >= 4",
            "1 + 01: long-offset back-reference with fixed length 3",
            "1 + 10: emit Nth most recent distinct byte (N encoded in 4 bits)",
            "1 + 11: short-offset back-reference with fixed length 2; class-3 raw 0x1FF ends the stream",
            "0: copy one literal byte from the compressed input",
            "",
            f"Probe status: {metadata['scorpion_probe_status']}",
            "CHEATER4 probe candidates:",
        ]
    )
    if probe_candidates:
        for candidate in probe_candidates:
            detail = f": {candidate['detail']}" if candidate.get("detail") else ""
            source = str(candidate.get("source_kind") or "unknown")
            match source:
                case "header-word-scale":
                    source += (
                        f" word#{int(candidate['header_word_index'])}={int(candidate['header_word_value'])}"
                        f" * {int(candidate['header_scale'])}"
                    )
                case "header-word-x2-block":
                    source += (
                        f" word#{int(candidate['header_word_index'])}={int(candidate['header_word_value'])}"
                        f" -> [0x{int(candidate['block_start']):03X}, 0x{int(candidate['block_end']):03X})"
                        f" skip {int(candidate.get('block_skip') or 0)}"
                    )
            extra_lines.append(
                f"0x{int(candidate['start_offset']):03X} -> score {float(candidate['printable_ratio']):.3f}, "
                f"quality {float(candidate['quality_score']):.3f}, out {int(candidate['output_length'])} B, "
                f"source {source}, reason {candidate['reason']}{detail}"
            )
            if candidate.get("preview_text"):
                extra_lines.append(f"Preview: {candidate['preview_text']}")
    else:
        extra_lines.append("No probe candidates fit inside this file.")

    if metadata["scorpion_probe_status"] != "candidate-readable":
        extra_lines.extend(
            [
                "",
                "Current result: direct coarse application of the recovered CHEATER4 LZ model to raw SCO bytes",
                "did not produce a stable readable payload. Header-word * 2 starts behave more like a block table,",
                "while a few zero-high-byte entries still look like paragraph or segment markers before the EXE-side",
                "LZ stage.",
            ]
        )

    topic.uhf_content.extend(extra_lines)
    topic.raw_lines.extend(line.encode("cp852", errors="replace") for line in extra_lines)
    return document


def _sco_huffman_entries(data: bytes) -> list[ScorpionScoHuffmanEntry]:
    table_end = SCORPION_SCO_HUFFMAN_TABLE_OFFSET + SCORPION_SCO_HUFFMAN_TABLE_SIZE
    if len(data) < table_end or not data.startswith(SCORPION_SCO_SIGNATURE):
        return []

    values = [
        int.from_bytes(
            data[
                SCORPION_SCO_HUFFMAN_TABLE_OFFSET + symbol * 2 :
                SCORPION_SCO_HUFFMAN_TABLE_OFFSET + symbol * 2 + 2
            ],
            "little",
            signed=False,
        )
        for symbol in range(SCORPION_SCO_HUFFMAN_SYMBOL_COUNT)
    ]
    if len(set(values)) != SCORPION_SCO_HUFFMAN_SYMBOL_COUNT:
        return []

    ordered = sorted((value, symbol) for symbol, value in enumerate(values))
    entries: list[ScorpionScoHuffmanEntry] = []
    for index, (start, symbol) in enumerate(ordered):
        end = ordered[index + 1][0] if index + 1 < len(ordered) else 0x10000
        width = end - start
        if width <= 0 or width & (width - 1):
            return []
        entries.append(
            ScorpionScoHuffmanEntry(
                start=start,
                end=end,
                bit_length=16 - (width.bit_length() - 1),
                symbol=symbol,
            )
        )
    return entries


def _sco_huffman_bit(data: bytes, stream_offset: int, bit_position: int) -> int:
    byte_index = stream_offset + bit_position // 8
    return (data[byte_index] >> (7 - (bit_position % 8))) & 1


def _decode_sco_huffman_bytes(
    data: bytes,
    *,
    stream_offset: int = SCORPION_SCO_HUFFMAN_STREAM_OFFSET,
    bit_offset: int = SCORPION_SCO_HUFFMAN_STREAM_BIT_OFFSET,
    output_limit: int = 200_000,
) -> tuple[bytes, int] | None:
    if stream_offset >= len(data):
        return None

    entries = _sco_huffman_entries(data)
    if not entries:
        return None

    starts = [entry.start for entry in entries]
    bit_position = bit_offset
    bit_limit = (len(data) - stream_offset) * 8
    output = bytearray()

    while bit_position + 16 <= bit_limit and len(output) < output_limit:
        value = 0
        for index in range(16):
            value = (value << 1) | _sco_huffman_bit(data, stream_offset, bit_position + index)

        entry_index = bisect_right(starts, value) - 1
        if entry_index < 0:
            break
        entry = entries[entry_index]
        if not (entry.start <= value < entry.end):
            break
        output.append(entry.symbol)
        bit_position += entry.bit_length

    if not output:
        return None
    return bytes(output), bit_position


def _build_sco_huffman_document(
    profile: ScorpionLegacyProfile,
    source_name: str,
    data: bytes,
) -> HelpDocument | None:
    decoded_result = _decode_sco_huffman_bytes(data)
    if decoded_result is None:
        return None

    decoded, consumed_bits = decoded_result
    return _build_sco_text_document(
        profile,
        source_name,
        data,
        _sco_decoded_text(decoded),
        parser_name="v4-sco-huffman",
        parser_metadata={
            "scorpion_container_signature": "SCORPION\\x00\\x01",
            "scorpion_sco_table_entries": SCORPION_SCO_HUFFMAN_SYMBOL_COUNT,
            "scorpion_sco_stream_offset": SCORPION_SCO_HUFFMAN_STREAM_OFFSET,
            "scorpion_sco_stream_bit_offset": SCORPION_SCO_HUFFMAN_STREAM_BIT_OFFSET,
            "scorpion_sco_consumed_bits": consumed_bits,
            "scorpion_sco_decoded_size": len(decoded),
        },
    )


class ScorpionV4ScoHuffmanReaderBase(ScorpionVersionReaderBase):
    def read_bytes(self, data: bytes):
        if data.startswith(SCORPION_SCO_SIGNATURE):
            document = _build_sco_huffman_document(self.profile, self.source_path.name, data)
            if document is not None:
                return self._finalize_document(document)

        document = _build_preview_document(self.profile, self.source_path.name, data)
        if data.startswith(SCORPION_SCO_SIGNATURE):
            document = _append_sco_probe_details(document, data)
        return self._finalize_document(document)


class ScorpionV4Reader(ScorpionV4ScoHuffmanReaderBase):
    pass


class ScorpionV5Reader(ScorpionV4ScoHuffmanReaderBase):
    pass
