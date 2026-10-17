"""Reader and parser helpers for Borland THELP binary help files."""

from __future__ import annotations

from pathlib import Path
import re
import struct

from ..base import (
    CommentRecord,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    PositionedKeyword,
    TopicNavItem,
    TopicRecord,
    ensure_document_index,
    render_topic_uhf_content,
)
from ..codepages import decode_bytes, decode_bytes_box_aware
from .turbo_basic import is_turbo_basic_binary

THELP_SIG = b"$*$* &&&&$*$"

RT_FILE_HEADER = 0
RT_CONTEXT = 1
RT_TEXT = 2
RT_KEYWORD = 3
RT_INDEX = 4
RT_COMPRESSION = 5
RT_INDEX_TAGS = 6

OF_CASESENSE = 0x0004
NC_RAW_CHAR = 0x0F
NC_REP_CHAR = 0x0E
TURBO_EXAMPLE_MARKER = b"\x05"
PRODUCT_NAME_MARKER = b"\x14"
# The ordinary 80-column DOS help view leaves 76 cells for flowing text.
THELP_WRAP_WIDTH = 76
# Match standalone headers like "Example:", "Examples", "Example 1:".
# Do not match prose such as "example code for ..." inside an indented list.
EXAMPLE_HEADER_RE = re.compile(r"^\s*Examples?(?:\s+\d+)?\s*(?:[:.)-]\s*)?$", re.IGNORECASE)
EXAMPLE_TERMINATOR_RE = re.compile(
    r"^\s*(?:See Also|Notes?|Remarks?|Warnings?|Syntax|Description|Parameters?|"
    r"Returns?|Return Value|Errors?)\s*:\s*$",
    re.IGNORECASE,
)
PASCAL_SAMPLE_TOPIC_RE = re.compile(r"^\s*\{?[^{}\s]+\.PAS\}?\s*$", re.IGNORECASE)
KNOWN_THELP_TITLES: dict[str, str] = {
    "TURBO4": "Turbo Pascal 4",
    "TURBO5": "Turbo Pascal 5",
    "TURBO5DE": "Turbo Pascal 5 DE",
    "TURBO6": "Turbo Pascal 6",
    "TURBO7": "Turbo Pascal 7",
    "TURBO7CZ": "Turbo Pascal 7 CZ",
    "TURBODE": "Turbo Pascal DE",
    "DEMOHELP": "Demo Help TP6",
    "DEMOHELP_BP7": "Demo Help BP7",
    "TVISION": "Turbo Vision",
    "OWL": "ObjectWindows Library",
    "WINDOWS": "Windows API",
    "TCHELP": "Turbo C Help",
    "TCWHELP": "Turbo C for Windows",
    "SHED": "Resource Workshop",
    "SK2": "Sidekick 2",
    "MCISTRWH": "MCI String Help",
    "PENAPIWH": "Pen API Help",
}


def is_thelp_binary(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like a THELP or Turbo C help file."""
    if is_turbo_basic_binary(data):
        return False
    # Accept Borland Pascal/TPH, Turbo C/TCH and other `*.T?H` variants
    # when they still contain the THELP signature. Some variants keep a
    # larger loader/header prefix.
    if data.find(THELP_SIG, 0, min(len(data), 4096)) >= 0:
        return True
    # Turbo C: startswith TURBO C HELP FILE.\0\x1a and then THELP_SIG
    if data.startswith(b"TURBO C HELP FILE.") and data[17:18] == b"\0" and data[18:19] == b"\x1a":
        # THELP_SIG by convention je na offsete 20
        if data.find(THELP_SIG, 20, 80) >= 0:
            return True
    return False


class ThelpFormatVariant:
    """Format-specific behavior layered on top of the shared THELP record parser."""

    variant_name = "unknown"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        raise NotImplementedError

    def parse_keyword_record(self, parser: "ThelpBinaryParser", screen: dict[str, object]) -> None:
        raise NotImplementedError

    def is_page_screen(self, parser: "ThelpBinaryParser") -> bool:
        return False

    @property
    def tracks_text_complete(self) -> bool:
        return False


class ThelpFormatV1ToV3(ThelpFormatVariant):
    """Early THELP variants with compression table stored in the file header."""

    variant_name = "v1-v3"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        parser._parse_legacy_file_header()

    def parse_keyword_record(self, parser: "ThelpBinaryParser", screen: dict[str, object]) -> None:
        parser._parse_legacy_keyword_record(screen)


class ThelpFormatV4(ThelpFormatVariant):
    """Format 4 files with short/long headers and positioned keywords."""

    variant_name = "v4"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        if rec_length <= 5:
            parser._parse_short_file_header()
            return
        parser._parse_extended_file_header()

    def parse_keyword_record(self, parser: "ThelpBinaryParser", screen: dict[str, object]) -> None:
        parser._parse_legacy_keyword_record(screen)


class ThelpFormatV41(ThelpFormatVariant):
    """BOA-documented 4.2 text format with legacy keywords and optional long header."""

    variant_name = "v41"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        if rec_length <= 5:
            parser._parse_short_file_header()
            return
        parser._parse_extended_file_header()

    def parse_keyword_record(self, parser: "ThelpBinaryParser", screen: dict[str, object]) -> None:
        parser._parse_legacy_keyword_record(screen)


class ThelpFormatV5(ThelpFormatVariant):
    """Page-oriented THELP files with 16-bit keyword target lists."""

    variant_name = "v5"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        parser._parse_extended_file_header()

    def parse_keyword_record(self, parser: "ThelpBinaryParser", screen: dict[str, object]) -> None:
        parser._parse_page_keyword_record(screen)

    def is_page_screen(self, parser: "ThelpBinaryParser") -> bool:
        return parser.keyword_rec["down"] != 0

    @property
    def tracks_text_complete(self) -> bool:
        return True


class ThelpFormatV51(ThelpFormatV5):
    """Observed format 51 branch used by Borland C++ 2.x/3.x TCH bundles."""

    variant_name = "v51"


class ThelpFormatV52Plus(ThelpFormatV5):
    """Observed format 52+ branch with index tag extensions."""

    variant_name = "v52+"


def make_thelp_variant(format_version: int, text_version: int, internal_version: int) -> ThelpFormatVariant:
    """Choose the semantic THELP parser branch for one compiled help file."""
    if format_version not in {1, 2, 3, 4, 5, 51, 52}:
        raise ValueError(f"Unsupported THELP format version {format_version}")
    if internal_version <= 3:
        return ThelpFormatV1ToV3()
    if internal_version == 4:
        return ThelpFormatV4()
    if internal_version == 41:
        return ThelpFormatV41()
    if internal_version == 5:
        return ThelpFormatV5()
    if internal_version == 51:
        return ThelpFormatV51()
    if internal_version >= 52:
        return ThelpFormatV52Plus()
    raise ValueError(
        f"Unsupported THELP variant: format_version={format_version}, "
        f"text_version={text_version}, internal_version={internal_version}"
    )


class ThelpBinaryParser:
    """Parse THELP binary records directly into the shared intermediate model."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self._read_limit = len(data)
        self._record_start: int | None = None
        self._record_type: int | None = None
        self.format_version = 0
        self.text_version = 0
        self.internal_version = 0
        self.variant: ThelpFormatVariant | None = None
        self.comp_rec: tuple[int, list[int]] | None = None
        self.context_array: list[int] = []
        self.context_by_offset: dict[int, int] = {}
        self.context_aliases: dict[int, list[int]] = {}
        self.file_hdr: dict[str, int | None] | None = None
        self.idx_list: list[tuple[int, bytes, int]] = []
        self.index_tags: list[tuple[int, str]] = []
        self.keyword_rec = {"up": 0, "down": 0, "cnt": 0}
        self.screen_num = 0xFFFF
        self.left_margin = 0
        self.current_screen: dict[str, object] | None = None
        self.screens: list[dict[str, object]] = []
        self.meta = {
            "stamp": "TURBO PASCAL HELP FILE.",
            "signature": "$*$* &&&&$*$",
            "format_version": 0,
            "text_version": 1,
            "height": None,
            "width": None,
            "left_margin": 0,
            "description": None,
            "help_contents_topic_id": None,
            "casesense": False,
            "context_count": None,
            "special_contexts": {},
            "no_help_contexts": {},
            "unused_contexts": {},
            "help_contents_aliases": [],
            "index_order": [],
            "tag_order": [],
        }

    def parse(self) -> tuple[dict[str, object], list[dict[str, object]], list[tuple[bytes, int]], list[tuple[int, str]]]:
        """Parse the whole THELP file into screen dictionaries and metadata."""
        self._parse_administrative()
        while self.pos < len(self.data):
            if self.data[self.pos] == 0x20 and all(value == 0x20 for value in self.data[self.pos:]):
                self._record_trailing_padding(self.pos)
                break
            if self.pos + 3 > len(self.data):
                raise ValueError(f"Truncated THELP record header at offset {self.pos}")
            rec_type = self.data[self.pos]
            rec_length = struct.unpack_from("<H", self.data, self.pos + 1)[0]
            rec_end = self.pos + 3 + rec_length
            if rec_type not in {RT_FILE_HEADER, RT_CONTEXT, RT_TEXT, RT_KEYWORD, RT_INDEX, RT_COMPRESSION, RT_INDEX_TAGS}:
                raise ValueError(f"Unknown THELP record type {rec_type} at offset {self.pos}")
            if rec_end > len(self.data):
                raise ValueError(f"Truncated THELP record {rec_type} at offset {self.pos}: "
                                 f"declared end {rec_end} exceeds file size {len(self.data)}")
            self._parse_record()
        if self.file_hdr is None:
            raise ValueError("Missing THELP file header record")
        self.meta["_internal_version"] = self.internal_version
        index_entries = [(label, context_id) for _idx, label, context_id in self.idx_list]
        return self.meta, self.screens, index_entries, self.index_tags

    def _record_trailing_padding(self, offset: int) -> None:
        """Record the already-validated terminal space extension."""
        self.meta["trailing_padding"] = {
            "offset": offset,
            "length": len(self.data) - offset,
            "byte": 0x20,
        }

    def _require(self, n: int) -> None:
        if n < 0 or self.pos + n > self._read_limit:
            location = ("administrative header" if self._record_start is None else
                        f"record {self._record_type} at offset {self._record_start}")
            raise ValueError(f"Truncated THELP {location}: need {n} bytes at offset "
                             f"{self.pos}, boundary {self._read_limit}")

    def read_bytes(self, n: int) -> bytes:
        self._require(n)
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def read_byte(self) -> int:
        self._require(1)
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_word(self) -> int:
        self._require(2)
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def read_stringz_bytes(self) -> bytes:
        end = self.data.find(b"\0", self.pos, self._read_limit)
        if end < 0:
            location = ("administrative header" if self._record_start is None else
                        f"record {self._record_type} at offset {self._record_start}")
            raise ValueError(f"Unterminated THELP string in {location} at offset {self.pos}")
        text = self.data[self.pos:end]
        self.pos = end + 1
        return text

    def _parse_administrative(self) -> None:
        self.meta["stamp"] = self.read_stringz_bytes().decode("latin-1")
        marker = self.read_byte()
        if marker != 0x1A:
            raise ValueError(f"Invalid THELP stamp terminator: expected 0x1A, got 0x{marker:02X}")
        self.meta["signature"] = self.read_stringz_bytes().decode("latin-1")
        if self.meta["signature"] != THELP_SIG.decode("ascii"):
            raise ValueError("Invalid THELP administrative signature")
        self.format_version = self.read_byte()
        self.text_version = self.read_byte()
        self.internal_version = 41 if self.format_version == 4 and self.text_version == 2 else self.format_version
        self.meta["format_version"] = self.format_version
        self.meta["text_version"] = self.text_version
        self.variant = make_thelp_variant(self.format_version, self.text_version, self.internal_version)
        self.meta["format_variant"] = self.variant.variant_name

    def _parse_record(self) -> None:
        old_pos = self.pos
        rec_type = self.read_byte()
        rec_length = self.read_word()
        rec_end = old_pos + 3 + rec_length
        self._read_limit = rec_end
        self._record_start, self._record_type = old_pos, rec_type
        try:
            match rec_type:
                case 0:
                    self._parse_file_header(rec_length)
                case 1:
                    self._parse_context()
                case 2:
                    self._parse_text(old_pos, rec_length)
                case 3:
                    self._parse_keyword()
                case 4:
                    self._parse_index()
                case 5:
                    self._parse_compression()
                case 6:
                    self._parse_index_tags(rec_end)
            self.pos = rec_end
        finally:
            self._read_limit = len(self.data)
            self._record_start = self._record_type = None

    def _parse_file_header(self, rec_length: int = 0) -> None:
        if self.variant is None:
            raise ValueError("THELP format variant was not initialized before file header parsing.")
        self.variant.parse_file_header(self, rec_length)

    def _parse_legacy_file_header(self) -> None:
        """Parse the early header variant with inline compression table."""
        options = self.read_word()
        self.meta["height"] = self.read_byte()
        self.meta["width"] = self.read_byte()
        self.meta["left_margin"] = self.read_byte()
        self._parse_compression()
        self.left_margin = self.meta["left_margin"]
        self.meta["casesense"] = bool(options & OF_CASESENSE)
        # Pascal 4's format 2/1 consumer binds its default screen to slot 100.
        # This is not a field in the short header or a rule for other profiles.
        help_contents_topic_id = 100 if (self.format_version, self.text_version) == (2, 1) else None
        self.meta["help_contents_topic_id"] = help_contents_topic_id
        self.file_hdr = {"help_contents_topic_id": help_contents_topic_id}

    def _parse_short_file_header(self) -> None:
        """Parse the short file header used by format 4 / short 4.2 files."""
        options = self.read_word()
        self.meta["height"] = self.read_byte()
        self.meta["width"] = self.read_byte()
        self.meta["left_margin"] = self.read_byte()
        self.left_margin = self.meta["left_margin"]
        self.meta["casesense"] = bool(options & OF_CASESENSE)
        self.meta["help_contents_topic_id"] = None
        self.file_hdr = {"help_contents_topic_id": None}

    def _parse_extended_file_header(self) -> None:
        """Parse the long file header used by page-oriented THELP variants."""
        options = self.read_word()
        help_contents_topic_id = self.read_word()
        self.read_word()
        self.meta["height"] = self.read_byte()
        self.meta["width"] = self.read_byte()
        self.meta["left_margin"] = self.read_byte()
        self.left_margin = self.meta["left_margin"]
        self.meta["casesense"] = bool(options & OF_CASESENSE)
        self.meta["help_contents_topic_id"] = help_contents_topic_id
        self.file_hdr = {"help_contents_topic_id": help_contents_topic_id}

    def _parse_context(self) -> None:
        context_num = self.read_word()
        self.meta["context_count"] = context_num
        self.context_array = []
        for context_id in range(context_num):
            b1 = self.read_byte()
            b2 = self.read_byte()
            b3 = self.read_byte()
            offset = b1 + (b2 << 8) + (b3 << 16)
            if offset not in {0xFFFFFF, 0xFFFFFE} and offset >= len(self.data):
                raise ValueError(f"THELP context {context_id} offset {offset} is outside the file")
            self.context_array.append(offset)

        offset_to_contexts: dict[int, list[int]] = {}
        for i, offset in enumerate(self.context_array):
            if offset in {0xFFFFFF, 0xFFFFFE}:
                self.meta["special_contexts"][i] = offset
            if offset == 0xFFFFFE:
                self.meta["no_help_contexts"][i] = 0xFFFFFE
                self.meta["unused_contexts"][i] = 0xFFFFFE
            if offset not in {0xFFFFFF, 0xFFFFFE}:
                offset_to_contexts.setdefault(offset, []).append(i)

        help_contents_topic_id = (self.file_hdr or {}).get("help_contents_topic_id")
        if isinstance(help_contents_topic_id, int) and 0 <= help_contents_topic_id < len(self.context_array):
            help_contents_offset = self.context_array[help_contents_topic_id]
            if help_contents_offset not in {0xFFFFFF, 0xFFFFFE}:
                alias_ids = [
                    idx
                    for idx, offset in enumerate(self.context_array)
                    if offset == 0xFFFFFF and idx != help_contents_topic_id
                ]
                bucket = offset_to_contexts[help_contents_offset]
                bucket[:] = [help_contents_topic_id] + [ctx for ctx in bucket if ctx != help_contents_topic_id]
                bucket.extend(alias_ids)
                self.meta["help_contents_aliases"] = list(alias_ids)
        self.context_by_offset = {offset: ctxs[0] for offset, ctxs in offset_to_contexts.items()}
        self.context_aliases = {offset: ctxs[1:] for offset, ctxs in offset_to_contexts.items() if len(ctxs) > 1}

    def _parse_text(self, old_pos: int, rec_length: int) -> None:
        if self.comp_rec is None:
            raise ValueError("Missing THELP compression table before text record.")

        screen_num = self._get_screen_num(old_pos)
        screen = {
            "id": screen_num,
            "alias_ids": list(self.context_aliases.get(old_pos, [])),
            "lines": [],
            "keywords_v4": [],
            "keywords_v5": [],
            "indices": [],
            "is_help_contents": screen_num != 0xFFFF and screen_num == (self.file_hdr or {}).get("help_contents_topic_id"),
            "group_end": False,
            "text_complete": False,
            "link_up": None,
            "link_down": None,
            "is_page": self.variant.is_page_screen(self) if self.variant is not None else False,
        }
        self.screens.append(screen)
        self.current_screen = screen
        self.screen_num = screen_num

        remaining = rec_length
        get_next = True
        this_byte = 0
        line_buf = bytearray()
        text_lines: list[bytes] = []
        trailing_newlines = 0
        trailing_newlines_before_eot = 0
        product_runs = bytearray() if (self.format_version, self.text_version) == (52, 2) else None

        def remember_run(character: int, count: int = 1) -> None:
            if product_runs is not None:
                product_runs.extend((count, character))

        def emit_line() -> None:
            nonlocal line_buf
            text_lines.append(bytes(line_buf))
            line_buf = bytearray()

        def get_nibble() -> int:
            nonlocal remaining, get_next, this_byte
            if get_next:
                this_byte = self.read_byte()
                remaining -= 1
                nibble = this_byte & 0x0F
                this_byte >>= 4
                get_next = False
                return nibble
            nibble = this_byte
            get_next = True
            return nibble

        # Fetching the final byte does not consume its pending high nibble.
        while remaining > 0 or not get_next:
            nibble = get_nibble()
            if nibble == 0x00:
                remember_run(0)
                emit_line()
                trailing_newlines += 1
                continue
            if 0x01 <= nibble <= 0x0D:
                character = self.comp_rec[1][nibble]
                remember_run(character)
                if character == 0:
                    emit_line()
                    trailing_newlines += 1
                else:
                    line_buf.append(character)
                    trailing_newlines = 0
                continue
            if nibble == NC_REP_CHAR:
                count_nibble = get_nibble()
                char_nibble = get_nibble()
                repeat_count = count_nibble + 2
                if char_nibble <= 0x0D and self.comp_rec[1][char_nibble] == 0:
                    remember_run(0, repeat_count)
                    for _ in range(repeat_count):
                        emit_line()
                    trailing_newlines += repeat_count
                elif 0x01 <= char_nibble <= 0x0D:
                    remember_run(self.comp_rec[1][char_nibble], repeat_count)
                    line_buf.extend([self.comp_rec[1][char_nibble]] * repeat_count)
                    trailing_newlines = 0
                elif char_nibble == NC_RAW_CHAR:
                    raw = get_nibble() + get_nibble() * 16
                    remember_run(raw, repeat_count)
                    line_buf.extend([raw] * repeat_count)
                    trailing_newlines = 0
                else:
                    raise ValueError("Invalid THELP repeat character nibble 0xE")
                continue
            if nibble == NC_RAW_CHAR:
                raw = get_nibble() + get_nibble() * 16
                remember_run(raw)
                if raw == 1:
                    trailing_newlines_before_eot = trailing_newlines
                    break
                line_buf.append(raw)
                trailing_newlines = 0

        if line_buf:
            emit_line()

        trailing_blank_lines = 0
        while trailing_blank_lines < len(text_lines) and text_lines[-1 - trailing_blank_lines] == b"":
            trailing_blank_lines += 1
        if self.variant is not None and self.variant.tracks_text_complete:
            screen["text_complete"] = trailing_newlines_before_eot > trailing_blank_lines

        screen["lines"] = text_lines
        if product_runs is not None and 0x14 in product_runs[1::2]:
            # Keep token runs only where the consumer needs them: ^T is tested
            # before RLE emission, and a suppressed run retains the repeat count.
            screen["product_runs"] = bytes(product_runs)

    def _parse_keyword(self) -> None:
        screen = self._require_current_screen()
        if self.variant is None:
            raise ValueError("THELP format variant was not initialized before keyword parsing.")
        self.variant.parse_keyword_record(self, screen)

    def _parse_legacy_keyword_record(self, screen: dict[str, object]) -> None:
        """Parse the classic keyword block with positioned hotspots."""
        up_ctx = self.read_word()
        down_ctx = self.read_word()
        kw_cnt = self.read_byte()
        for _ in range(kw_cnt):
            line = self.read_byte()
            first_col = self.read_byte()
            last_col = self.read_byte()
            left_btn = self.read_byte()
            right_btn = self.read_byte()
            up_btn = self.read_byte()
            down_btn = self.read_byte()
            context = self.read_word()
            screen["keywords_v4"].append(
                (
                    context,
                    line,
                    first_col - self.left_margin,
                    last_col - self.left_margin,
                    left_btn,
                    right_btn,
                    up_btn,
                    down_btn,
                )
            )
        screen["indices"].extend(label for _idx, label, context in self.idx_list if context == self.screen_num)
        screen["link_up"] = up_ctx
        screen["link_down"] = down_ctx
        screen["group_end"] = down_ctx == 0
        self.keyword_rec = {"up": up_ctx, "down": down_ctx, "cnt": kw_cnt}

    def _parse_page_keyword_record(self, screen: dict[str, object]) -> None:
        """Parse the page-oriented keyword block with 16-bit target ids."""
        up_ctx = self.read_word()
        down_ctx = self.read_word()
        kw_cnt = self.read_word()
        screen["keywords_v5"].extend(self.read_word() for _ in range(kw_cnt))
        screen["indices"].extend(label for _idx, label, context in self.idx_list if context == self.screen_num)
        screen["link_up"] = up_ctx
        screen["link_down"] = down_ctx
        screen["group_end"] = down_ctx == 0
        self.keyword_rec = {"up": up_ctx, "down": down_ctx, "cnt": kw_cnt}

    def _parse_index(self) -> None:
        count = self.read_word()
        self.idx_list = []
        prev_label = b""
        self.meta["index_order"] = []
        for idx in range(count):
            head = self.read_byte()
            keep = (head >> 5) & 0x07
            new_len = head & 0x1F
            if keep > len(prev_label):
                raise ValueError(f"Invalid THELP index prefix length {keep} for entry {idx}")
            label = prev_label[:keep] + self.read_bytes(new_len)
            prev_label = label
            context_id = self.read_word()
            self.idx_list.append((idx, label, context_id))
            self.meta["index_order"].append((label.decode("latin-1"), context_id))

    def _parse_compression(self) -> None:
        comp_type = self.read_byte()
        char_table = list(self.read_bytes(14))
        if comp_type != 2:
            raise ValueError(f"Unsupported THELP compression type {comp_type}")
        if char_table[0] != 0:
            raise ValueError("Invalid THELP compression table: entry zero must be NUL")
        self.comp_rec = (comp_type, char_table)

    def _parse_index_tags(self, rec_end: int) -> None:
        self.index_tags = []
        self.meta["tag_order"] = []
        while self.pos < rec_end:
            idx_num = self.read_word()
            text_length = self.read_byte()
            tag_str = self.read_stringz_bytes().decode("latin-1")
            if len(tag_str) != text_length:
                raise ValueError(f"Invalid THELP index tag length at record offset {self._record_start}")
            self.index_tags.append((idx_num, tag_str))
            self.meta["tag_order"].append((idx_num, tag_str))
            if idx_num == 0xFFFF:
                self.meta["description"] = tag_str

    def _get_screen_num(self, file_pos: int) -> int:
        return self.context_by_offset.get(file_pos, 0xFFFF)

    def _require_current_screen(self) -> dict[str, object]:
        if self.current_screen is None:
            raise ValueError("Encountered THELP keyword record without a preceding text record.")
        return self.current_screen


class ThelpHelpReader(HelpReaderBase):
    """High-level THELP reader returning the shared ``HelpDocument`` model."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read one THELP buffer and normalize it into ``HelpDocument``."""
        if not is_thelp_binary(data):
            raise ValueError("Input is not a Borland THELP help file.")
        parser = ThelpBinaryParser(data)
        meta, screens, index_entries, _index_tags = parser.parse()
        meta.setdefault("text_encoding", "cp437")
        self._populate_title_metadata(meta)
        document = self._build_document(meta, screens, index_entries, binary_data=data)
        self._annotate_unresolved_contexts(document, parser.context_array, data)
        encoding = str((document.metadata or {}).get("text_encoding") or "cp437")
        self.refresh_rendered_uhf_content(document, encoding=encoding)
        return document

    def _build_document(
        self,
        meta: dict[str, object],
        screens: list[dict[str, object]],
        index_entries: list[tuple[str | bytes, int]],
        binary_data: bytes | None,
        comments: list[CommentRecord] | None = None,
    ) -> HelpDocument:
        """Build the final document model from parsed THELP structures."""
        return ensure_document_index(HelpDocument(
            format_name="borland",
            source_name=self.source_name,
            topics=self._build_topics(screens, meta),
            index_entries=[
                IndexEntry(label=self._normalize_label(label), context_id=context_id)
                for label, context_id in index_entries
            ],
            comments=list(comments or []),
            metadata=meta,
            binary_data=binary_data,
        ))

    @staticmethod
    def _decode_context_text(raw: bytes | str, encoding: str) -> str:
        """Decode bytes from the current help file using its declared text encoding."""
        if isinstance(raw, str):
            return raw
        try:
            if encoding == "cp852":
                return decode_bytes_box_aware(raw, encoding)
            return decode_bytes(raw, encoding)
        except LookupError:
            return decode_bytes(raw, "cp437")

    @classmethod
    def refresh_rendered_uhf_content(cls, document: HelpDocument, *, encoding: str) -> None:
        """Render native references without guessing another destination.

        Genuine aliases address the same Text record. Missing targets remain
        explicit links; the viewer reports failure without replacing the page.
        Exporters repeat this after selecting the final display encoding.
        """
        link_targets = {context for topic in document.topics
                        for context in [topic.context_id, *topic.alias_contexts,
                                        *topic.sequential_keywords,
                                        *(keyword.target_context for keyword in topic.positional_keywords)]}
        for topic in document.topics:
            rendered_content = render_topic_uhf_content(
                topic,
                decode_bytes=lambda raw: cls._decode_context_text(raw, encoding),
                topic_ids=link_targets,
            )
            topic.uhf_content = rendered_content

    @staticmethod
    def _annotate_unresolved_contexts(
        document: HelpDocument,
        context_array: list[int],
        data: bytes,
    ) -> None:
        """Classify missing native destinations, never their referring rows."""
        topic_ids = {context for topic in document.topics
                     for context in [topic.context_id, *topic.alias_contexts]}
        unresolved_index: set[int] = set()
        unresolved_links: set[int] = set()

        for entry in document.index_entries:
            if entry.topic_id in topic_ids:
                continue
            if entry.context_id not in topic_ids:
                unresolved_index.add(entry.context_id)

        for topic in document.topics:
            for target in topic.sequential_keywords:
                if target not in topic_ids:
                    unresolved_links.add(target)
            for keyword in topic.positional_keywords:
                if keyword.target_context not in topic_ids:
                    unresolved_links.add(keyword.target_context)

        if not unresolved_index and not unresolved_links:
            return

        unresolved_all = unresolved_index | unresolved_links
        offsets = {str(context): context_array[context] for context in sorted(unresolved_all)
                   if 0 <= context < len(context_array)}
        padding_start = (document.metadata.get("trailing_padding") or {}).get("offset")
        document.metadata["unresolved_contexts"] = {
            "index": sorted(unresolved_index),
            "links": sorted(unresolved_links),
            "space_tail": sorted(context for context in unresolved_all
                                 if isinstance(padding_start, int) and 0 <= context < len(context_array)
                                 and padding_start <= context_array[context] < len(data)),
            "no_help": sorted(int(context) for context, offset in offsets.items() if offset == 0xFFFFFE),
            "unbound_contents": sorted(int(context) for context, offset in offsets.items() if offset == 0xFFFFFF),
            "out_of_range": sorted(context for context in unresolved_all
                                   if not 0 <= context < len(context_array)),
            "offsets": offsets,
        }
        keys = document.metadata.setdefault("transport_metadata_keys", [])
        if "unresolved_contexts" not in keys:
            keys.append("unresolved_contexts")

    @staticmethod
    def _normalize_label(label: str | bytes) -> bytes:
        """Normalize textual or raw index labels to bytes."""
        if isinstance(label, bytes):
            return label
        return label.encode("latin-1")

    def _populate_title_metadata(self, meta: dict[str, object]) -> None:
        """Fill `metadata.title` for known THELP bundles when the file itself has no label."""
        if isinstance(meta.get("title"), str) and meta["title"].strip():
            return
        description = meta.get("description")
        if isinstance(description, str) and description.strip():
            return

        source_stem = Path(self.source_name).stem.upper()
        title = self._infer_title_from_source(source_stem, meta)
        if title:
            meta["title"] = title

    @staticmethod
    def _infer_title_from_source(source_stem: str, meta: dict[str, object]) -> str | None:
        """Infer a stable bundle title from known Borland file names and format ids."""
        if source_stem == "TURBO":
            format_version = meta.get("format_version")
            if isinstance(format_version, int):
                if format_version <= 3:
                    return "Turbo Pascal 4"
                if format_version == 4:
                    return "Turbo Pascal 5"
                if format_version == 51:
                    return "Turbo Pascal 6"
                if format_version >= 52:
                    return "Borland Pascal 7"

        return KNOWN_THELP_TITLES.get(source_stem)

    @classmethod
    def _build_topics(cls, screens: list[dict[str, object]], meta: dict[str, object]) -> list[TopicRecord]:
        """Convert parsed screen dictionaries into typed topic records."""
        topics = []
        orphan_context_ids: list[int] = []
        skipped_empty_orphans = 0
        if (meta.get("format_version"), meta.get("text_version")) == (52, 2):
            # Pascal 7's decoder substitutes an application-owned short string,
            # not an emphasis attribute. Native IndexTags identify the product;
            # an untagged stream uses the verified Turbo Pascal viewer default.
            description = str(meta.get("description") or "").casefold()
            product_name = b"Borland" if description.startswith("borland pascal") else b"Turbo"
            screens = [dict(screen, lines=cls._substitute_product_name(
                screen["lines"], product_name, screen.get("product_runs")))
                       for screen in screens]
        example_states = cls._example_entry_states(screens)
        width = meta.get("width")
        # UHF stores fixed display rows. Choose a bounded DOS viewport once;
        # the lossless parser retains the authored rows and compressed bytes.
        wrap_width = (min(THELP_WRAP_WIDTH, max(1, width - int(meta.get("left_margin") or 0)))
                      if isinstance(width, int) and width > 0 and int(meta.get("format_version") or 0) >= 5
                      else None)
        for screen_index, screen in enumerate(screens):
            display_lines = (cls._wrap_text_lines(screen["lines"], wrap_width)
                             if wrap_width is not None else list(screen["lines"]))
            raw_lines, code_line_indices = cls._extract_code_lines(
                display_lines,
                use_example_heuristic=True,
                initial_code_state=example_states[screen_index],
            )
            if not example_states[screen_index] and not any(TURBO_EXAMPLE_MARKER in line for line in screen["lines"]):
                code_line_indices.update(cls._detect_pascal_sample_code_lines(raw_lines))
            positional_keywords = []
            for keyword in screen.get("keywords_v4", []):
                context_id, line, col1, col2, left_btn, right_btn, up_btn, down_btn = keyword
                positional_keywords.append(
                    PositionedKeyword(
                        target_context=context_id,
                        line=line,
                        first_column=col1,
                        last_column=col2,
                        navigation=(left_btn, right_btn, up_btn, down_btn),
                    )
                )

            context_id = int(screen["id"])
            if context_id == 0xFFFF:
                has_topic_data = bool(
                    any(line.strip() for line in raw_lines)
                    or positional_keywords
                    or screen.get("keywords_v5")
                    or screen.get("indices")
                )
                if not has_topic_data:
                    skipped_empty_orphans += 1
                    continue
                context_id = 0x10000 + len(orphan_context_ids)
                orphan_context_ids.append(context_id)

            topic = TopicRecord(
                context_id=context_id,
                raw_lines=raw_lines,
                index_terms=[cls._normalize_label(name) for name in screen.get("indices", [])],
                alias_contexts=list(screen.get("alias_ids", [])),
                sequential_keywords=list(screen.get("keywords_v5", [])),
                positional_keywords=positional_keywords,
                is_help_contents=bool(screen.get("is_help_contents")),
                up_context=screen.get("link_up") or None,
                down_context=screen.get("link_down") or None,
                prev_context=screen.get("link_up") or None,
                next_context=screen.get("link_down") or None,
                code_line_indices=code_line_indices,
            )
            # Zero terminates a page chain. Positioned keyword navigation
            # bytes select another hotspot, never a topic-level destination.
            topic.nav_items = [TopicNavItem(label=label, topic_id=target)
                               for label, target in (("Up", topic.up_context), ("Down", topic.down_context),
                                                     ("Prev", topic.prev_context), ("Next", topic.next_context))
                               if target is not None]
            topics.append(topic)
        if orphan_context_ids:
            meta["orphan_screen_contexts"] = orphan_context_ids
        if skipped_empty_orphans:
            meta["skipped_empty_orphan_screens"] = skipped_empty_orphans
        return topics

    @staticmethod
    def _wrap_text_lines(lines: list[bytes], width: int) -> list[bytes]:
        """Project sequential THELP text with the native byte-word algorithm.

        A leading literal space or empty row is fixed. Otherwise join soft
        returns, retaining their space and atomic 02h-delimited keywords.
        Process controls before removing example markers: they occupy no
        formatter cells, but a leading marker still makes a row wrappable.
        Long indivisible words/fixed rows are retained for horizontal scroll.
        """
        if width <= 0:
            raise ValueError("THELP wrap width must be positive")
        output: list[bytes] = []
        row = bytearray()
        row_width = 0
        # A raw-escape NUL is lossless in the codec, but the consumer's
        # uncompressed buffer still treats it as a row boundary.
        for line in (part for source_line in lines for part in source_line.split(b"\0")):
            if not line or line.startswith(b" "):
                if row:
                    output.append(bytes(row))
                    row.clear()
                    row_width = 0
                output.append(line)
                continue
            position = 0
            while position < len(line):
                word = bytearray()
                word_width = 0
                in_keyword = False
                while position < len(line):
                    value = line[position]
                    if value == 0x20 and not in_keyword:
                        break
                    word.append(value)
                    position += 1
                    if value >= 7:
                        word_width += 1
                    elif value == 2:
                        in_keyword = not in_keyword
                if row_width and row_width + word_width > width:
                    output.append(bytes(row))
                    row.clear()
                    row_width = 0
                if position == len(line):
                    word.append(0x20)  # A wrappable source return is a space.
                else:
                    while position < len(line) and line[position] == 0x20:
                        word.append(0x20)
                        position += 1
                row.extend(word)
                row_width += sum(value >= 7 for value in word)
        if row:
            output.append(bytes(row))
        return output

    @staticmethod
    def _example_entry_states(screens: list[dict[str, object]]) -> list[bool]:
        """Carry ^E state along actual reciprocal page links, not file order."""
        parity = [sum(line.count(TURBO_EXAMPLE_MARKER) for line in screen["lines"]) % 2
                  for screen in screens]
        states = [False] * len(screens)
        if not any(parity):
            return states
        by_context = {context: index for index, screen in enumerate(screens)
                      for context in [screen["id"], *screen.get("alias_ids", [])] if context != 0xFFFF}
        predecessors = []
        for screen in screens:
            up = screen.get("link_up")
            previous = by_context.get(up) if up not in (None, 0) else None
            if previous is not None:
                down = screens[previous].get("link_down")
                if down in (None, 0) or down not in [screen["id"], *screen.get("alias_ids", [])]:
                    previous = None
            predecessors.append(previous)
        resolved, unknown = set(), set()
        for index in range(len(screens)):
            route, visiting = [], set()
            current = index
            while current is not None and current not in resolved and current not in visiting:
                route.append(current)
                visiting.add(current)
                current = predecessors[current]
            if current in visiting:
                # A cycle has no established entry state; do not invent one.
                cycle_start = route.index(current)
                resolved.update(route[cycle_start:])
                unknown.update(route[cycle_start:])
                route = route[:cycle_start]
            for current in reversed(route):
                previous = predecessors[current]
                if previous in unknown:
                    unknown.add(current)
                elif previous is not None:
                    states[current] = states[previous] ^ bool(parity[previous])
                resolved.add(current)
        return states

    @staticmethod
    def _substitute_product_name(
        raw_lines: list[bytes], product_name: bytes, runs: bytes | None = None,
    ) -> list[bytes]:
        """Replace each ^T-delimited placeholder before interpreting text controls."""
        if not any(PRODUCT_NAME_MARKER in line for line in raw_lines):
            return list(raw_lines)
        # The original decoder's toggle belongs to one physical Text record.
        # Suppressed placeholder bytes include NUL row boundaries and controls.
        if runs is None:
            text = b"\0".join(raw_lines) + b"\0"
            runs = bytes(value for character in text for value in (1, character))
        visible = bytearray()
        suppressed = False
        repeat_count = 0
        for count, character in zip(runs[::2], runs[1::2]):
            if count > 1:
                repeat_count = count
            if character == 1:
                break
            if character == 0x14:
                suppressed = not suppressed
                if suppressed:
                    visible.extend(product_name)
            elif not suppressed:
                visible.extend(bytes((character,)) * (repeat_count or 1))
                repeat_count = 0
        lines = bytes(visible).split(b"\0")
        if lines[-1] == b"":
            lines.pop()
        return lines

    @staticmethod
    def _extract_code_lines(
        raw_lines: list[bytes],
        *,
        use_example_heuristic: bool = False,
        initial_code_state: bool = False,
    ) -> tuple[list[bytes], set[int]]:
        """Decode native ^E toggles without losing rows, whitespace or glyphs."""
        cleaned_lines: list[bytes] = []
        code_line_indices: set[int] = set()
        in_code_block = initial_code_state
        saw_explicit_markers = initial_code_state

        for raw_line in raw_lines:
            parts = raw_line.split(TURBO_EXAMPLE_MARKER)
            line_is_code = False
            for part_index, part in enumerate(parts):
                if in_code_block and part:
                    line_is_code = True
                if part_index < len(parts) - 1:
                    in_code_block = not in_code_block
                    saw_explicit_markers = True
            visible_line = b"".join(parts)
            if line_is_code or (not visible_line.strip(b" \t") and in_code_block):
                code_line_indices.add(len(cleaned_lines))
            cleaned_lines.append(visible_line)

        if use_example_heuristic and not saw_explicit_markers:
            code_line_indices.update(ThelpHelpReader._detect_example_code_lines(cleaned_lines))

        return cleaned_lines, code_line_indices

    @staticmethod
    def _detect_example_code_lines(raw_lines: list[bytes]) -> set[int]:
        """Detect TC 2.x example blocks from the visible text."""
        code_line_indices: set[int] = set()
        in_example = False
        saw_code_line = False
        pending_blank_indices: list[int] = []
        # Lines consisting of a repeated non-alphanumeric glyph (box-drawing,
        # dashes, equals, etc.) are typically decorative borders. When such
        # a line follows an Example header, treat it as decoration and do not
        # mark it as example code.
        decorative_re = re.compile(r"^\s*([^A-Za-z0-9\s])\1{2,}\s*$")

        for index, raw_line in enumerate(raw_lines):
            decoded = raw_line.decode("cp437", errors="replace")
            if EXAMPLE_HEADER_RE.match(decoded):
                in_example = True
                saw_code_line = False
                pending_blank_indices = []
                continue

            if not in_example:
                continue

            if not decoded.strip():
                if saw_code_line:
                    pending_blank_indices.append(index)
                continue

            # Skip decorative border lines immediately after the Example
            # heading (e.g. " ▀▀▀▀▀..."). Do not treat them as code.
            if decorative_re.match(decoded) and not saw_code_line:
                continue

            if saw_code_line and EXAMPLE_TERMINATOR_RE.match(decoded):
                in_example = False
                saw_code_line = False
                pending_blank_indices = []
                continue

            if raw_line[:1] not in (b" ", b"\t"):
                in_example = False
                saw_code_line = False
                pending_blank_indices = []
                continue

            if pending_blank_indices:
                code_line_indices.update(pending_blank_indices)
                pending_blank_indices = []

            saw_code_line = True
            if decoded.strip():
                code_line_indices.add(index)

        return code_line_indices

    @staticmethod
    def _detect_pascal_sample_code_lines(raw_lines: list[bytes]) -> set[int]:
        """Detect Borland Pascal sample-source topics embedded as plain THELP text."""
        if len(raw_lines) < 4:
            return set()
        first_text_index = next((index for index, line in enumerate(raw_lines) if line.strip()), None)
        if first_text_index is None:
            return set()
        title = raw_lines[first_text_index].decode("cp437", errors="replace").strip()
        if not PASCAL_SAMPLE_TOPIC_RE.match(title):
            return set()

        start_index = first_text_index + 1
        while start_index < len(raw_lines):
            decoded = raw_lines[start_index].decode("cp437", errors="replace").strip()
            if not decoded:
                start_index += 1
                continue
            if re.fullmatch(r"[^A-Za-z0-9\s]{3,}", decoded):
                start_index += 1
                continue
            break

        end_index = len(raw_lines) - 1
        while end_index >= start_index and not raw_lines[end_index].strip():
            end_index -= 1
        if end_index < start_index:
            return set()
        return set(range(start_index, end_index + 1))
