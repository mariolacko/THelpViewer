"""Reader and parser helpers for Borland THELP binary help files."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import struct

from ..base import (
    CommentRecord,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    PositionedKeyword,
    TopicRecord,
    build_directional_nav_items,
    ensure_document_index,
    render_topic_uhf_content,
)
from ..codepages import decode_bytes, decode_bytes_box_aware
from ..uhf_markup import escape_uhf_text, format_uhf_link

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
CODE_BLOCK_MARKER_BYTES = {0x03, 0x05, 0x10}
FORMAT_MARKER_BYTES = bytes((0x14,))
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
    """Format 4 THELP files with the short 5-byte file header."""

    variant_name = "v4"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        parser._parse_short_file_header(help_contents_topic_id=0)

    def parse_keyword_record(self, parser: "ThelpBinaryParser", screen: dict[str, object]) -> None:
        parser._parse_legacy_keyword_record(screen)


class ThelpFormatV41(ThelpFormatVariant):
    """BOA-documented 4.2 text format with legacy keywords and optional long header."""

    variant_name = "v41"

    def parse_file_header(self, parser: "ThelpBinaryParser", rec_length: int) -> None:
        if rec_length <= 5:
            parser._parse_short_file_header(help_contents_topic_id=0)
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
        self.format_version = 0
        self.text_version = 0
        self.internal_version = 0
        self.variant: ThelpFormatVariant | None = None
        self.comp_rec: tuple[int, list[int]] | None = None
        self.context_array: list[int] = []
        self.context_aliases: dict[int, list[int]] = {}
        self.file_hdr: dict[str, int] | None = None
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
            "help_contents_topic_id": 0,
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
            if self.pos + 3 > len(self.data):
                self._record_trailing_data(self.pos)
                break
            rec_type = self.data[self.pos]
            rec_length = struct.unpack_from("<H", self.data, self.pos + 1)[0]
            rec_end = self.pos + 3 + rec_length
            if rec_type not in {RT_FILE_HEADER, RT_CONTEXT, RT_TEXT, RT_KEYWORD, RT_INDEX, RT_COMPRESSION, RT_INDEX_TAGS}:
                self._record_trailing_data(self.pos)
                break
            if rec_end > len(self.data):
                self._record_trailing_data(self.pos)
                break
            self._parse_record()
        self.meta["_internal_version"] = self.internal_version
        index_entries = [(label, context_id) for _idx, label, context_id in self.idx_list]
        return self.meta, self.screens, index_entries, self.index_tags

    def _record_trailing_data(self, offset: int) -> None:
        """Persist opaque bytes after the last valid BOA-style record."""
        if offset >= len(self.data):
            return
        tail = self.data[offset:]
        if not tail:
            return
        if set(tail) == {0x20}:
            self.meta["trailing_padding"] = {
                "offset": offset,
                "length": len(tail),
                "byte": 0x20,
            }
            return
        self.meta["trailing_data"] = {
            "offset": offset,
            "length": len(tail),
        }

    def read_bytes(self, n: int) -> bytes:
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def read_byte(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_word(self) -> int:
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def read_stringz_bytes(self) -> bytes:
        start = self.pos
        while self.pos < len(self.data) and self.data[self.pos] != 0:
            self.pos += 1
        text = self.data[start:self.pos]
        self.pos += 1
        return text

    def _parse_administrative(self) -> None:
        self.meta["stamp"] = self.read_stringz_bytes().decode("latin-1")
        marker = self.read_byte()
        if marker != 0x1A:
            raise ValueError(f"Expected 0x1A after stamp, got 0x{marker:02X}")
        self.meta["signature"] = self.read_stringz_bytes().decode("latin-1")
        self.format_version = self.read_byte()
        self.text_version = self.read_byte()
        self.internal_version = 41 if self.format_version == 4 and self.text_version == 2 else self.format_version
        self.meta["format_version"] = self.format_version
        self.meta["text_version"] = self.text_version
        self.variant = make_thelp_variant(self.format_version, self.text_version, self.internal_version)
        self.meta["format_variant"] = self.variant.variant_name

    def _parse_record(self) -> None:
        if self.pos + 3 > len(self.data):
            self.pos = len(self.data)
            return
        old_pos = self.pos
        rec_type = self.read_byte()
        rec_length = self.read_word()
        rec_end = old_pos + 3 + rec_length
        if rec_type == RT_FILE_HEADER:
            self._parse_file_header(rec_length)
        elif rec_type == RT_CONTEXT:
            self._parse_context()
        elif rec_type == RT_TEXT:
            self._parse_text(old_pos, rec_length)
        elif rec_type == RT_KEYWORD:
            self._parse_keyword()
        elif rec_type == RT_INDEX:
            self._parse_index()
        elif rec_type == RT_COMPRESSION:
            self._parse_compression()
        elif rec_type == RT_INDEX_TAGS:
            self._parse_index_tags(rec_end)
        if self.pos != rec_end:
            self.pos = rec_end

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
        comp_type = self.read_byte()
        char_table = list(self.read_bytes(14))
        self.comp_rec = (comp_type, char_table)
        self.left_margin = self.meta["left_margin"]
        self.meta["casesense"] = bool(options & OF_CASESENSE)
        self.file_hdr = {"help_contents_topic_id": 0}

    def _parse_short_file_header(self, *, help_contents_topic_id: int) -> None:
        """Parse the short file header used by format 4 / short 4.2 files."""
        options = self.read_word()
        self.meta["height"] = self.read_byte()
        self.meta["width"] = self.read_byte()
        self.meta["left_margin"] = self.read_byte()
        if self.meta["width"] == 0 and self.meta["left_margin"] > 80:
            self.meta["raw_width"] = self.meta["width"]
            self.meta["raw_left_margin"] = self.meta["left_margin"]
            self.meta["width"] = 80
            self.meta["left_margin"] = 2
        self.left_margin = self.meta["left_margin"]
        self.meta["casesense"] = bool(options & OF_CASESENSE)
        self.meta["help_contents_topic_id"] = help_contents_topic_id
        self.file_hdr = {"help_contents_topic_id": help_contents_topic_id}

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
        for _ in range(context_num):
            b1 = self.read_byte()
            b2 = self.read_byte()
            b3 = self.read_byte()
            self.context_array.append(b1 + (b2 << 8) + (b3 << 16))

        offset_to_contexts: dict[int, list[int]] = {}
        for i, offset in enumerate(self.context_array):
            if offset in {0xFFFFFF, 0xFFFFFE}:
                self.meta["special_contexts"][i] = offset
            if offset == 0xFFFFFE:
                self.meta["no_help_contexts"][i] = 0xFFFFFE
                self.meta["unused_contexts"][i] = 0xFFFFFE
            if offset not in {0xFFFFFF, 0xFFFFFE}:
                offset_to_contexts.setdefault(offset, []).append(i)

        help_contents_topic_id = 0
        if self.file_hdr is not None:
            help_contents_topic_id = int(self.file_hdr.get("help_contents_topic_id", 0) or 0)
        if 0 <= help_contents_topic_id < len(self.context_array):
            help_contents_offset = self.context_array[help_contents_topic_id]
            if help_contents_offset < 0xFFFF00:
                alias_ids = [
                    idx
                    for idx, offset in enumerate(self.context_array)
                    if offset == 0xFFFFFF and idx != help_contents_topic_id
                ]
                if alias_ids:
                    bucket = offset_to_contexts.setdefault(help_contents_offset, [])
                    if help_contents_topic_id in bucket:
                        bucket[:] = [help_contents_topic_id] + [
                            ctx for ctx in bucket if ctx != help_contents_topic_id
                        ]
                    else:
                        bucket.insert(0, help_contents_topic_id)
                    for alias_id in alias_ids:
                        if alias_id not in bucket:
                            bucket.append(alias_id)
                    self.meta["help_contents_aliases"] = list(alias_ids)
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
            "is_help_contents": False,
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

        while remaining > 0:
            nibble = get_nibble()
            if nibble == 0x00:
                emit_line()
                trailing_newlines += 1
                continue
            if 0x01 <= nibble <= 0x0D:
                line_buf.append(self.comp_rec[1][nibble])
                trailing_newlines = 0
                continue
            if nibble == NC_REP_CHAR:
                count_nibble = get_nibble()
                char_nibble = get_nibble()
                repeat_count = count_nibble + 2
                if char_nibble == 0x00:
                    for _ in range(repeat_count):
                        emit_line()
                    trailing_newlines += repeat_count
                elif 0x01 <= char_nibble <= 0x0D:
                    line_buf.extend([self.comp_rec[1][char_nibble]] * repeat_count)
                    trailing_newlines = 0
                elif char_nibble == NC_RAW_CHAR:
                    raw = get_nibble() + get_nibble() * 16
                    line_buf.extend([raw] * repeat_count)
                    trailing_newlines = 0
                continue
            if nibble == NC_RAW_CHAR:
                raw = get_nibble() + get_nibble() * 16
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
        if self.file_hdr and self.screen_num == self.file_hdr["help_contents_topic_id"]:
            screen["is_help_contents"] = True
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
            label = prev_label[:keep] + self.read_bytes(new_len)
            prev_label = label
            context_id = self.read_word()
            self.idx_list.append((idx, label, context_id))
            self.meta["index_order"].append((label.decode("latin-1"), context_id))

    def _parse_compression(self) -> None:
        comp_type = self.read_byte()
        char_table = list(self.read_bytes(14))
        self.comp_rec = (comp_type, char_table)

    def _parse_index_tags(self, rec_end: int) -> None:
        self.index_tags = []
        self.meta["tag_order"] = []
        while self.pos < rec_end:
            idx_num = self.read_word()
            self.read_byte()
            tag_str = self.read_stringz_bytes().decode("latin-1")
            self.index_tags.append((idx_num, tag_str))
            self.meta["tag_order"].append((idx_num, tag_str))
            if idx_num == 0xFFFF:
                self.meta["description"] = tag_str

    def _get_screen_num(self, file_pos: int) -> int:
        for i, offset in enumerate(self.context_array):
            if offset == file_pos:
                return i
        return 0xFFFF

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
        self._annotate_context_fallbacks(document)
        self._apply_context_fallbacks(document)
        self._apply_keyword_index_targets(document)
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

    @staticmethod
    def _label_forms(label: str) -> set[str]:
        """Return normalized label variants for conservative alias matching."""
        text = " ".join(label.strip().split())
        if not text:
            return set()
        forms = {text.casefold()}
        parts = [part.strip() for part in text.split(",") if part.strip()]
        forms.update(part.casefold() for part in parts)
        if len(parts) > 1:
            forms.add(" ".join(parts).casefold())
        if "$" in text:
            stripped = text.replace("$", "").strip()
            if stripped:
                forms.add(" ".join(stripped.split()).casefold())
                stripped_parts = [part.strip() for part in stripped.split(",") if part.strip()]
                forms.update(part.casefold() for part in stripped_parts)
                if len(stripped_parts) > 1:
                    forms.add(" ".join(stripped_parts).casefold())
        return {form for form in forms if form}

    @classmethod
    def _annotate_context_fallbacks(cls, document: HelpDocument) -> None:
        """Derive context-level fallback targets from actual orphan keyword occurrences."""
        topic_ids = {topic.context_id for topic in document.topics}
        encoding = str((document.metadata or {}).get("text_encoding") or "cp437")

        occurrences = cls._collect_orphan_keyword_occurrences(document, topic_ids, encoding)

        fallbacks: dict[str, dict[str, int | str]] = {}
        for context_id, hits in occurrences.items():
            if context_id in topic_ids or not hits:
                continue
            locations = {(topic_id, line_number) for topic_id, line_number, _label in hits}
            if len(locations) != 1:
                continue

            topic_id, line_number = next(iter(locations))
            label = next((value.strip() for _topic_id, _line, value in hits if value.strip()), "")
            fallbacks[str(context_id)] = {
                "topic_id": topic_id,
                "line": line_number,
                "label": label,
                "source": "keyword-single",
            }

        if fallbacks:
            document.metadata["context_fallbacks"] = fallbacks

    @classmethod
    def _collect_orphan_keyword_occurrences(
        cls,
        document: HelpDocument,
        topic_ids: set[int],
        encoding: str,
    ) -> dict[int, list[tuple[int, int, str]]]:
        """Return actual hotspot labels that target orphan context ids."""
        occurrences: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
        for topic in document.topics:
            for keyword in topic.positional_keywords:
                if keyword.target_context in topic_ids:
                    continue
                line_index = keyword.line - 1
                if not (0 <= line_index < len(topic.raw_lines)):
                    continue
                raw_line = topic.raw_lines[line_index]
                start = max(keyword.first_column - 1, 0)
                end = min(keyword.last_column, len(raw_line))
                label = cls._decode_context_text(raw_line[start:end], encoding).strip()
                if label:
                    occurrences[keyword.target_context].append((topic.context_id, keyword.line, label))

            keyword_index = 0
            for line_number, raw_line in enumerate(topic.raw_lines, start=1):
                if b"\x02" not in raw_line or keyword_index >= len(topic.sequential_keywords):
                    continue
                parts = raw_line.split(b"\x02")
                for part_index in range(1, len(parts), 2):
                    if keyword_index >= len(topic.sequential_keywords):
                        break
                    target_context = topic.sequential_keywords[keyword_index]
                    keyword_index += 1
                    if target_context in topic_ids:
                        continue
                    label = cls._decode_context_text(parts[part_index], encoding).strip()
                    if label:
                        occurrences[target_context].append((topic.context_id, line_number, label))
        return occurrences

    @classmethod
    def _apply_context_fallbacks(cls, document: HelpDocument) -> None:
        """Project reader-specific orphan-context knowledge into the shared model."""
        topic_ids = {topic.context_id for topic in document.topics}
        fallback_map = {
            int(context_id): target
            for context_id, target in (document.metadata.get("context_fallbacks", {}) or {}).items()
            if str(context_id).isdigit() and isinstance(target, dict)
        }
        if not fallback_map:
            return

        for entry in document.index_entries:
            if entry.context_id in topic_ids:
                continue
            fallback = fallback_map.get(entry.context_id)
            if fallback is None:
                continue
            topic_id = fallback.get("topic_id")
            if topic_id in topic_ids:
                entry.topic_id = topic_id
                line = fallback.get("line")
                if isinstance(line, int) and line > 0:
                    entry.line = line
                source_file = fallback.get("source_file")
                if isinstance(source_file, str) and source_file.strip():
                    entry.source_file = source_file.strip()
                alias = fallback.get("alias")
                if isinstance(alias, str) and alias.strip():
                    entry.alias = alias.strip()

        encoding = str((document.metadata or {}).get("text_encoding") or "cp437")
        cls.refresh_rendered_uhf_content(document, encoding=encoding)

    @classmethod
    def refresh_rendered_uhf_content(cls, document: HelpDocument, *, encoding: str) -> None:
        """Rebuild THELP UHF lines that depend on resolved orphan targets.

        The reader can discover fallback link targets before the final display
        encoding is known. Exporters call this again after applying the help
        database encoding so pre-rendered link labels do not keep stale CP437
        text.
        """
        topic_ids = {topic.context_id for topic in document.topics}
        fallback_map = {
            int(context_id): target
            for context_id, target in (document.metadata.get("context_fallbacks", {}) or {}).items()
            if str(context_id).isdigit() and isinstance(target, dict)
        }
        for topic in document.topics:
            rendered_content = render_topic_uhf_content(
                topic,
                decode_bytes=lambda raw: cls._decode_context_text(raw, encoding),
                topic_ids=topic_ids,
                fallback_map=fallback_map,
            )
            topic.uhf_content = cls._restore_sequential_hotspot_tables(rendered_content)

    @classmethod
    def _restore_sequential_hotspot_tables(cls, lines: list[str]) -> list[str]:
        """Rebuild THELP tables stored as a flat sequence of linked cells."""
        restored: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            restored.append(line)
            column_count = cls._table_header_column_count(line)
            if column_count < 2:
                index += 1
                continue

            cell_index = index + 1
            cells: list[str] = []
            while cell_index < len(lines) and cls._is_sequential_table_cell(lines[cell_index]):
                cells.append(lines[cell_index])
                cell_index += 1

            if len(cells) >= column_count:
                for offset in range(0, len(cells), column_count):
                    row_cells = cells[offset:offset + column_count]
                    restored.append(
                        row_cells[0] + "".join(f" {cell}" for cell in row_cells[1:])
                    )
                index = cell_index
                continue

            index += 1
        return restored

    @staticmethod
    def _table_header_column_count(line: str) -> int:
        """Return the number of cells described by a top table border."""
        if "╤" not in line or "╕" not in line:
            return 0
        if line.rfind("╕") < line.find("╤"):
            return 0
        return line.count("╤") + 1

    @staticmethod
    def _is_sequential_table_cell(line: str) -> bool:
        """Return true for one linked cell emitted as its own THELP line."""
        stripped = line.rstrip()
        return (
            (stripped.endswith("│") or stripped.endswith("│[/link]"))
            and line.count("[link:") == 1
            and line.count("[/link]") == 1
        )

    @classmethod
    def _apply_keyword_index_targets(cls, document: HelpDocument) -> None:
        """Resolve orphan index entries from real RT_Keyword hotspot occurrences."""
        topic_ids = {topic.context_id for topic in document.topics}
        encoding = str((document.metadata or {}).get("text_encoding") or "cp437")
        occurrences = cls._collect_orphan_keyword_occurrences(document, topic_ids, encoding)
        resolved: dict[int, dict[str, object]] = {}
        ambiguous: dict[int, dict[str, object]] = {}

        for index, entry in enumerate(document.index_entries):
            if entry.topic_id is not None or entry.context_id in topic_ids:
                continue
            label = cls._decode_context_text(entry.label, encoding).strip()
            if not label:
                continue
            hits = occurrences.get(entry.context_id, [])
            if not hits:
                continue

            label_forms = cls._label_forms(label)
            matched_hits = [
                hit for hit in hits
                if label_forms and not cls._label_forms(hit[2]).isdisjoint(label_forms)
            ]
            chosen = cls._choose_keyword_index_hit(matched_hits)
            source = "keyword-label"

            if chosen is None and len(hits) == 1:
                chosen = hits[0]
                source = "keyword-single-context"

            if chosen is None:
                candidate_hits = matched_hits or hits
                ambiguous[index] = {
                    "context_id": entry.context_id,
                    "label": label,
                    "hits": [
                        {"topic_id": topic_id, "line": line, "label": hit_label}
                        for topic_id, line, hit_label in candidate_hits
                    ],
                }
                continue

            topic_id, line_number, hit_label = chosen
            entry.topic_id = topic_id
            if line_number > 0:
                entry.line = line_number
            resolved[index] = {
                "context_id": entry.context_id,
                "label": label,
                "topic_id": topic_id,
                "line": line_number,
                "hotspot_label": hit_label,
                "source": source,
            }

        if resolved:
            document.metadata["keyword_index_targets"] = resolved
        if ambiguous:
            document.metadata["ambiguous_keyword_index_targets"] = ambiguous

    @staticmethod
    def _choose_keyword_index_hit(
        hits: list[tuple[int, int, str]],
    ) -> tuple[int, int, str] | None:
        """Choose a keyword-derived index target only when the binary evidence is unique."""
        if not hits:
            return None
        locations = {(topic_id, line_number) for topic_id, line_number, _label in hits}
        if len(locations) == 1:
            return hits[0]
        return None

    @classmethod
    def _render_topic_uhf_content(
        cls,
        topic: TopicRecord,
        *,
        topic_ids: set[int],
        fallback_map: dict[int, dict[str, int | str]],
        encoding: str,
    ) -> list[str]:
        """Render one topic directly to UHF using reader-resolved fallback targets."""
        content: list[str] = []
        code_line_indices = set(topic.code_line_indices or set())
        in_code_block = False

        positional_by_line: dict[int, list[PositionedKeyword]] = defaultdict(list)
        for keyword in topic.positional_keywords:
            positional_by_line[keyword.line].append(keyword)
        for keywords in positional_by_line.values():
            keywords.sort(key=lambda keyword: keyword.first_column)

        sequential_index = 0
        for line_index, raw_line in enumerate(topic.raw_lines):
            line_is_code = line_index in code_line_indices
            if line_is_code and not in_code_block:
                content.append("[code]")
                in_code_block = True
            elif not line_is_code and in_code_block:
                content.append("[/code]")
                in_code_block = False

            line_number = line_index + 1
            if line_number in positional_by_line:
                content.append(
                    cls._render_positioned_uhf_line(
                        raw_line,
                        positional_by_line[line_number],
                        topic_ids=topic_ids,
                        fallback_map=fallback_map,
                        encoding=encoding,
                    )
                )
                continue

            if b"\x02" in raw_line and topic.sequential_keywords:
                rendered_line, sequential_index = cls._render_sequential_uhf_line(
                    raw_line,
                    topic.sequential_keywords,
                    sequential_index,
                    topic_ids=topic_ids,
                    fallback_map=fallback_map,
                    encoding=encoding,
                )
                content.append(rendered_line)
                continue

            content.append(cls._escape_uhf_segment(raw_line, encoding))

        if in_code_block:
            content.append("[/code]")

        return content

    @classmethod
    def _render_positioned_uhf_line(
        cls,
        raw_line: bytes,
        keywords: list[PositionedKeyword],
        *,
        topic_ids: set[int],
        fallback_map: dict[int, dict[str, int | str]],
        encoding: str,
    ) -> str:
        """Render one line with positioned hotspots directly to UHF."""
        parts: list[str] = []
        cursor = 0

        for keyword in keywords:
            start = max(keyword.first_column - 1, 0)
            end = min(keyword.last_column, len(raw_line))
            if start > cursor:
                parts.append(cls._escape_uhf_segment(raw_line[cursor:start], encoding))
            label = cls._escape_uhf_text_fragment(raw_line[start:end], encoding)
            parts.append(
                cls._wrap_uhf_link_target(
                    keyword.target_context,
                    label,
                    topic_ids=topic_ids,
                    fallback_map=fallback_map,
                )
            )
            cursor = end

        parts.append(cls._escape_uhf_segment(raw_line[cursor:], encoding))
        return "".join(parts)

    @classmethod
    def _render_sequential_uhf_line(
        cls,
        raw_line: bytes,
        keywords: list[int],
        start_index: int,
        *,
        topic_ids: set[int],
        fallback_map: dict[int, dict[str, int | str]],
        encoding: str,
    ) -> tuple[str, int]:
        """Render one line with in-band sequential hotspots directly to UHF."""
        parts: list[str] = []
        buffer = bytearray()
        in_hotspot = False
        keyword_index = start_index

        for value in raw_line:
            if value != 0x02:
                buffer.append(value)
                continue

            if in_hotspot:
                label = cls._escape_uhf_text_fragment(bytes(buffer), encoding)
                if keyword_index < len(keywords):
                    parts.append(
                        cls._wrap_uhf_link_target(
                            keywords[keyword_index],
                            label,
                            topic_ids=topic_ids,
                            fallback_map=fallback_map,
                        )
                    )
                    keyword_index += 1
                else:
                    parts.append(label)
                buffer.clear()
                in_hotspot = False
                continue

            if buffer:
                parts.append(cls._escape_uhf_segment(bytes(buffer), encoding))
                buffer.clear()
            in_hotspot = True

        if buffer:
            parts.append(cls._escape_uhf_segment(bytes(buffer), encoding))

        return "".join(parts), keyword_index

    @classmethod
    def _wrap_uhf_link_target(
        cls,
        target_context: int,
        label: str,
        *,
        topic_ids: set[int],
        fallback_map: dict[int, dict[str, int | str]],
    ) -> str:
        """Format one visible label as a universal UHF link when a target exists."""
        if target_context in topic_ids:
            return format_uhf_link(label, topic_id=target_context)

        fallback = fallback_map.get(target_context)
        if fallback is None:
            return label

        return format_uhf_link(
            label,
            topic_id=fallback.get("topic_id"),
            source_file=fallback.get("source_file"),
            alias=fallback.get("alias"),
            line=fallback.get("line"),
        )

    @classmethod
    def _escape_uhf_text_fragment(cls, raw: bytes | str, encoding: str) -> str:
        """Decode one visible segment and escape it for literal UHF text."""
        return escape_uhf_text(cls._decode_context_text(raw, encoding))

    @classmethod
    def _escape_uhf_segment(cls, raw: bytes | str, encoding: str) -> str:
        """Decode and escape one non-hotspot segment."""
        return cls._escape_uhf_text_fragment(raw, encoding)

    @staticmethod
    def _annotate_unresolved_contexts(
        document: HelpDocument,
        context_array: list[int],
        data: bytes,
    ) -> None:
        """Record unresolved context ids for TCH/THELP variants with orphan links."""
        topic_ids = {topic.context_id for topic in document.topics}
        resolved_fallbacks = {
            int(context_id)
            for context_id in (document.metadata.get("context_fallbacks", {}) or {}).keys()
            if str(context_id).isdigit()
        }
        unresolved_index: set[int] = set()
        unresolved_links: set[int] = set()

        for entry in document.index_entries:
            if entry.topic_id in topic_ids:
                continue
            if entry.context_id not in topic_ids and entry.context_id not in resolved_fallbacks:
                unresolved_index.add(entry.context_id)

        for topic in document.topics:
            for target in topic.sequential_keywords:
                if target not in topic_ids and target not in resolved_fallbacks:
                    unresolved_links.add(target)
            for keyword in topic.positional_keywords:
                if keyword.target_context not in topic_ids and keyword.target_context not in resolved_fallbacks:
                    unresolved_links.add(keyword.target_context)

        if not unresolved_index and not unresolved_links:
            return

        def _space_tail_context(context_id: int) -> bool:
            if not (0 <= context_id < len(context_array)):
                return False
            offset = context_array[context_id]
            if not (0 <= offset < len(data)):
                return False
            chunk = data[offset:offset + 64]
            return bool(chunk) and set(chunk) == {0x20}

        unresolved_all = unresolved_index | unresolved_links
        document.metadata["unresolved_contexts"] = {
            "index": sorted(unresolved_index),
            "links": sorted(unresolved_links),
            "space_tail": sorted(context_id for context_id in unresolved_all if _space_tail_context(context_id)),
        }

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
        for screen in screens:
            raw_lines, code_line_indices = cls._extract_code_lines(
                list(screen["lines"]),
                use_example_heuristic=True,
            )
            code_line_indices.update(cls._detect_pascal_sample_code_lines(raw_lines))
            raw_lines = cls._strip_format_markers(raw_lines)
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
                up_context=screen.get("link_up"),
                down_context=screen.get("link_down"),
                code_line_indices=code_line_indices,
            )
            topic.nav_items = build_directional_nav_items(topic)
            topics.append(topic)
        if orphan_context_ids:
            meta["orphan_screen_contexts"] = orphan_context_ids
        if skipped_empty_orphans:
            meta["skipped_empty_orphan_screens"] = skipped_empty_orphans
        return topics

    @staticmethod
    def _strip_format_markers(raw_lines: list[bytes]) -> list[bytes]:
        """Remove THELP inline style delimiters from visible text.

        Borland help files use byte 0x14 around emphasized product names
        (for example ``Turbo``). In CP437 that byte is a paragraph glyph,
        but in THELP payload it is not meant to be displayed.
        """
        return [raw_line.replace(FORMAT_MARKER_BYTES, b"") for raw_line in raw_lines]

    @staticmethod
    def _extract_code_lines(
        raw_lines: list[bytes],
        *,
        use_example_heuristic: bool = False,
    ) -> tuple[list[bytes], set[int]]:
        """Strip THELP code markers and expose code lines as zero-based indices."""
        cleaned_lines: list[bytes] = []
        code_line_indices: set[int] = set()
        in_code_block = False
        saw_explicit_markers = False

        for raw_line in raw_lines:
            stripped = raw_line.strip(b" \t")
            # Marker-only lines toggle code mode (e.g. b"\x05" or b"\x10\x05").
            if stripped and all(value in CODE_BLOCK_MARKER_BYTES for value in stripped):
                in_code_block = not in_code_block
                saw_explicit_markers = True
                continue

            # Some THELP files place the marker byte(s) at the start of a
            # line immediately followed by source text (e.g. b" \x05#include...").
            # Treat a leading marker sequence as a toggle and, if the
            # marker is followed by text, expose the remainder as a code
            # line (or normal text when closing).
            left_stripped = raw_line.lstrip(b" \t")
            if left_stripped and left_stripped[0] in CODE_BLOCK_MARKER_BYTES:
                # measure consecutive marker bytes at line start
                idx = 0
                while idx < len(left_stripped) and left_stripped[idx] in CODE_BLOCK_MARKER_BYTES:
                    idx += 1
                remainder = left_stripped[idx:]
                in_code_block = not in_code_block
                saw_explicit_markers = True
                if remainder:
                    if in_code_block:
                        code_line_indices.add(len(cleaned_lines))
                    cleaned_lines.append(remainder)
                continue

            if in_code_block:
                code_line_indices.add(len(cleaned_lines))
            cleaned_lines.append(raw_line)

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
