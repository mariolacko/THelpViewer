"""Reader scaffolding for Borland Turbo Debugger/Profiler runtime help files.

TDH/TFH files are not THELP/TPH/TCH variants.  The known Turbo Debugger and
Turbo Profiler samples start with product-specific decoder tables and an
encoded payload.  We can identify the format and preserve the observed
structure, but the text decoder is still unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import zlib

from ..base import HelpDocument, HelpReaderBase, IndexEntry, TopicRecord

TDH_MIN_TABLE_BYTE_SIZE = 0x0200
TDH_MAX_TABLE_BYTE_SIZE = 0x0800
TDH_CONFIRMED_SAMPLE_CRC32 = 0xA9C668A7
TDH_MIN_SIZE = 0x420
TFH_MIN_TABLE_BYTE_SIZE = 0x0100
TFH_MIN_SIZE = 0x2E0


@dataclass(frozen=True, slots=True)
class TdhProbe:
    """Observed structural summary for one Borland runtime help file."""

    format_name: str
    title: str
    description: str
    header_word: int
    table_byte_size: int
    table_word_count: int
    left_table_offset: int
    right_table_offset: int
    separator_offset: int
    separator_word: int
    encoded_payload_offset: int
    encoded_payload_size: int
    payload_lead_byte: int
    payload_lead_cc_run: int
    payload_prefix_hex: str
    crc32: int

    def to_metadata(self) -> dict[str, object]:
        """Return a JSON-safe representation for diagnostics."""
        return {
            "format": self.format_name,
            "header_word": f"0x{self.header_word:04X}",
            "table_byte_size": self.table_byte_size,
            "table_word_count": self.table_word_count,
            "left_table_offset": self.left_table_offset,
            "right_table_offset": self.right_table_offset,
            "separator_offset": self.separator_offset,
            "separator_word": f"0x{self.separator_word:04X}",
            "encoded_payload_offset": self.encoded_payload_offset,
            "encoded_payload_size": self.encoded_payload_size,
            "payload_lead_byte": f"0x{self.payload_lead_byte:02X}",
            "payload_lead_cc_run": self.payload_lead_cc_run,
            "payload_prefix_hex": self.payload_prefix_hex,
            "crc32": f"{self.crc32:08X}",
        }


def _payload_lead_cc_run(data: bytes, encoded_payload_offset: int) -> int:
    """Return the count of consecutive 0xCC bytes after the lead payload byte."""
    cc_run = 0
    for value in data[encoded_payload_offset + 1 :]:
        if value != 0xCC:
            break
        cc_run += 1
    return cc_run


def _probe_runtime_help_binary(
    data: bytes,
    *,
    format_name: str,
    title: str,
    description: str,
    min_size: int,
    min_table_byte_size: int,
    require_even_table_size: bool,
    allowed_separator_words: set[int],
) -> TdhProbe | None:
    """Return structural information when *data* matches a known TDH/TFH shape."""
    if len(data) < min_size:
        return None
    header_word = struct.unpack_from(">H", data, 0)[0]

    # Known files use the first word as a byte count for each of two decoder
    # tables. TDH samples use even word tables and separator 0x0001; TFH uses
    # the same layout with an odd table byte count and separator 0x0000.
    table_byte_size = header_word
    if (
        table_byte_size < min_table_byte_size
        or table_byte_size > TDH_MAX_TABLE_BYTE_SIZE
        or (require_even_table_size and table_byte_size % 2)
    ):
        return None
    table_word_count = (table_byte_size + 1) // 2
    left_table_offset = 2
    right_table_offset = left_table_offset + table_byte_size
    separator_offset = right_table_offset + table_byte_size
    encoded_payload_offset = separator_offset + 2
    if encoded_payload_offset + 2 >= len(data):
        return None
    separator_word = struct.unpack_from(">H", data, separator_offset)[0]
    if separator_word not in allowed_separator_words:
        return None
    if not (0x80 <= data[encoded_payload_offset] <= 0xBF):
        return None
    if data[encoded_payload_offset + 1:encoded_payload_offset + 5] != b"\xcc\xcc\xcc\xcc":
        return None
    payload_lead_byte = data[encoded_payload_offset]
    payload_lead_cc_run = _payload_lead_cc_run(data, encoded_payload_offset)
    payload_prefix_hex = data[encoded_payload_offset : encoded_payload_offset + 16].hex(" ").upper()

    return TdhProbe(
        format_name=format_name,
        title=title,
        description=description,
        header_word=header_word,
        table_byte_size=table_byte_size,
        table_word_count=table_word_count,
        left_table_offset=left_table_offset,
        right_table_offset=right_table_offset,
        separator_offset=separator_offset,
        separator_word=separator_word,
        encoded_payload_offset=encoded_payload_offset,
        encoded_payload_size=len(data) - encoded_payload_offset,
        payload_lead_byte=payload_lead_byte,
        payload_lead_cc_run=payload_lead_cc_run,
        payload_prefix_hex=payload_prefix_hex,
        crc32=zlib.crc32(data) & 0xFFFFFFFF,
    )


def probe_tdh_binary(data: bytes) -> TdhProbe | None:
    """Return structural TDH information when *data* matches known samples."""
    return _probe_runtime_help_binary(
        data,
        format_name="tdh",
        title="Turbo Debugger Help",
        description="Borland Turbo Debugger TDH help file",
        min_size=TDH_MIN_SIZE,
        min_table_byte_size=TDH_MIN_TABLE_BYTE_SIZE,
        require_even_table_size=True,
        allowed_separator_words={1},
    )


def probe_tfh_binary(data: bytes) -> TdhProbe | None:
    """Return structural TFH information when *data* matches known samples."""
    return _probe_runtime_help_binary(
        data,
        format_name="tfh",
        title="Turbo Profiler Help",
        description="Borland Turbo Profiler TFH help file",
        min_size=TFH_MIN_SIZE,
        min_table_byte_size=TFH_MIN_TABLE_BYTE_SIZE,
        require_even_table_size=False,
        allowed_separator_words={0},
    )


def is_tdh_binary(data: bytes) -> bool:
    """Return ``True`` for known Borland Turbo Debugger TDH help data."""
    return probe_tdh_binary(data) is not None


def is_tfh_binary(data: bytes) -> bool:
    """Return ``True`` for known Borland Turbo Profiler TFH help data."""
    return probe_tfh_binary(data) is not None


class TdhHelpReader(HelpReaderBase):
    """Reader for currently identified but undecoded TDH/TFH files."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read a TDH/TFH file into a diagnostic document.

        This intentionally does not invent topics.  Until the encoded stream is
        decoded from the original format, the reader emits one explicit status
        topic so runtime help files are visible in catalogs without being
        mistaken for fully converted help.
        """
        source_suffix = self.source_path.suffix.casefold() if self.source_path else ""
        if source_suffix == ".tfh":
            probe = probe_tfh_binary(data)
        elif source_suffix == ".tdh":
            probe = probe_tdh_binary(data)
        else:
            probe = probe_tdh_binary(data) or probe_tfh_binary(data)
        if probe is None:
            raise ValueError("Unsupported Borland runtime help format")

        lines = [
            probe.title.encode("ascii"),
            b"",
            b"This Borland runtime help file is detected, but its encoded payload is not decoded yet.",
            b"The file is not a Borland THELP/TPH/TCH variant.",
            b"",
            f"Format: {probe.format_name.upper()}".encode("ascii"),
            f"CRC32: {probe.crc32:08X}".encode("ascii"),
            f"Encoded payload offset: 0x{probe.encoded_payload_offset:04X}".encode("ascii"),
            f"Encoded payload size: {probe.encoded_payload_size}".encode("ascii"),
            f"Payload lead byte: 0x{probe.payload_lead_byte:02X}".encode("ascii"),
            f"Payload lead 0xCC run: {probe.payload_lead_cc_run}".encode("ascii"),
        ]
        topic = TopicRecord(
            context_id=1,
            raw_lines=lines,
            index_terms=[probe.title.encode("ascii")],
            names=[f"{probe.format_name.upper()} format status"],
            is_help_contents=True,
            uhf_content=[line.decode("ascii") for line in lines],
        )
        return HelpDocument(
            format_name=probe.format_name,
            source_name=self.source_name,
            topics=[topic],
            index_entries=[IndexEntry(label=probe.title.encode("ascii"), context_id=1, topic_id=1)],
            metadata={
                "title": probe.title,
                "description": probe.description,
                "format": probe.format_name,
                "format_status": "undecoded",
                "text_encoding": "cp437",
                "language": "en",
                "tdh_probe": probe.to_metadata(),
            },
            binary_data=data,
        )


def read_tdh(path: str | Path) -> HelpDocument:
    """Convenience helper for loading a TDH/TFH file from disk."""
    source_path = Path(path)
    return TdhHelpReader(source_name=source_path.name, source_path=source_path).read_path(source_path)
