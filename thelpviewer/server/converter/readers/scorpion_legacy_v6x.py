"""Version-specific readers for Scorpions Cheater v6-v14 SCO/SCD binaries."""

from __future__ import annotations

from pathlib import Path

from ..base import HelpDocument
from ..text_screen import BitmapFont
from .scorpion_legacy_reader import (
    ScorpionLegacyProfile,
    ScorpionVersionReaderBase,
    _build_preview_document,
    _build_sco_text_document,
    _sco_decoded_text,
)
from .scorpion_lzhuf import (
    SCORPION_LZHUF_MAX_OUTPUT_SIZE, ScorpionLzhufBlock, ScorpionLzhufDecoder,
)
from .scorpion_screens import legacy_default_font


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
        return ScorpionLzhufDecoder(data, offset).decode()
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
    artwork_font: BitmapFont | None = None,
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
        artwork_font=artwork_font,
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
        font = (legacy_default_font(self.source_path.parent, float(self.profile.version))
                if self.source_path.stem.upper() in {"DATATEXT", "DATAHELP"} else None)
        document = _build_sco_lzhuf_document(self.profile, self.source_path.name, data, font)
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
