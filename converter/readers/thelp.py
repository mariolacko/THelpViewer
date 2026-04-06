"""Reader and parser helpers for Borland THELP binary help files."""

from __future__ import annotations

import re
import struct

from ..base import CommentRecord, HelpDocument, HelpReaderBase, IndexEntry, PositionedKeyword, TopicRecord

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


def is_thelp_binary(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like a THELP or Turbo C help file."""
    # Accept Borland Pascal/TPH and Turbo C/TCH
    if data.find(THELP_SIG, 0, 200) >= 0:
        return True
    # Turbo C: startswith TURBO C HELP FILE.\0\x1a and then THELP_SIG
    if data.startswith(b"TURBO C HELP FILE.") and data[17:18] == b"\0" and data[18:19] == b"\x1a":
        # THELP_SIG by convention je na offsete 20
        if data.find(THELP_SIG, 20, 80) >= 0:
            return True
    return False


class ThelpHlxSourceParser:
    """Parse HLDC-style textual HLX source into THELP screen structures."""

    def __init__(self, data: bytes):
        self.data = data
        if b"\r\n" in data:
            self.raw_lines = data.split(b"\r\n")
        else:
            self.raw_lines = data.split(b"\n")

        self.meta = {
            "stamp": "TURBO PASCAL HELP FILE.",
            "signature": "$*$* &&&&$*$",
            "format_version": 0,
            "text_version": 1,
            "height": None,
            "width": None,
            "left_margin": 0,
            "description": None,
            "main_index": 0,
            "casesense": False,
            "context_count": None,
            "unused_contexts": {},
            "index_order": [],
            "tag_order": [],
        }
        self.screens: list[dict[str, object]] = []
        self.all_index_entries: list[tuple[str, int]] = []
        self.all_index_tags: list[tuple[str, int, str]] = []
        self.comments: list[CommentRecord] = []
        self.in_comment = False
        self._reset_screen_state()

    def parse(self) -> tuple[dict[str, object], list[dict[str, object]], list[tuple[str, int]], list[tuple[str, int, str]]]:
        """Parse the whole HLX buffer and return screen dictionaries."""
        for raw_line in self.raw_lines:
            self._handle_line(raw_line)
        self._flush_screen()
        self.meta["_internal_version"] = (
            41 if self.meta["format_version"] == 4 and self.meta["text_version"] == 2 else self.meta["format_version"]
        )
        return self.meta, self.screens, self.all_index_entries, self.all_index_tags

    def _reset_screen_state(self) -> None:
        self.current_screen: int | None = None
        self.current_text_lines: list[bytes] = []
        self.current_keywords_v4: list[tuple[int, int, int, int, int | None, int | None, int | None, int | None]] = []
        self.current_keywords_v5: list[int] = []
        self.current_alias_ids: list[int] = []
        self.current_screen_indices: list[str] = []
        self.current_screen_tag: str | None = None
        self.current_is_main = False
        self.current_is_page = False
        self.current_link_up: int | None = None
        self.current_link_down: int | None = None
        self.current_text_complete_override: bool | None = None
        self.reading_text = False
        self.post_directive_blanks = 0

    def _start_screen(self, context_id: int, is_page: bool) -> None:
        self.current_screen = context_id
        self.current_is_page = is_page
        self.current_text_lines = []
        self.current_keywords_v4 = []
        self.current_keywords_v5 = []
        self.current_alias_ids = []
        self.current_screen_indices = []
        self.current_screen_tag = None
        self.current_is_main = False
        self.current_link_up = None
        self.current_link_down = None
        self.current_text_complete_override = None
        self.reading_text = True
        self.post_directive_blanks = 0

    def _flush_screen(self, ended_by_endscreen: bool = False) -> None:
        if self.current_screen is None:
            return

        # HLDC-style text can end a topic with ambiguous blank lines; keep enough
        # state here to reconstruct whether the original binary text record ended
        # with a deliberate trailing blank line.
        current_iv = self.meta["format_version"]
        if current_iv == 4 and self.meta["text_version"] == 2:
            current_iv = 41

        trailing_blanks = 0
        if current_iv >= 5 and current_iv != 41:
            tmp_lines = list(self.current_text_lines)
            while tmp_lines and tmp_lines[-1] == b"":
                tmp_lines.pop()
                trailing_blanks += 1
        else:
            while self.current_text_lines and self.current_text_lines[-1] == b"":
                self.current_text_lines.pop()
                trailing_blanks += 1

        has_keywords = len(self.current_keywords_v4) > 0 or len(self.current_keywords_v5) > 0
        has_directives = (
            has_keywords
            or len(self.current_screen_indices) > 0
            or self.current_screen_tag is not None
            or self.current_is_main
        )

        if self.current_text_complete_override is not None:
            text_complete = self.current_text_complete_override
        elif current_iv >= 5 and current_iv != 41:
            text_complete = False
        elif ended_by_endscreen or has_keywords:
            if has_keywords:
                text_complete = trailing_blanks >= 1
            elif has_directives:
                text_complete = self.post_directive_blanks >= 1
            else:
                text_complete = trailing_blanks >= 1
        elif has_directives:
            text_complete = self.post_directive_blanks >= 2
        else:
            text_complete = trailing_blanks >= 2

        self.screens.append(
            {
                "id": self.current_screen,
                "alias_ids": self.current_alias_ids,
                "lines": self.current_text_lines,
                "keywords_v4": self.current_keywords_v4,
                "keywords_v5": self.current_keywords_v5,
                "indices": self.current_screen_indices,
                "is_main": self.current_is_main,
                "group_end": ended_by_endscreen,
                "text_complete": text_complete,
                "link_up": self.current_link_up,
                "link_down": self.current_link_down,
                "is_page": self.current_is_page,
            }
        )
        for name in self.current_screen_indices:
            self.all_index_entries.append((name, self.current_screen))
        if self.current_is_main:
            self.meta["main_index"] = self.current_screen

        self._reset_screen_state()

    def _handle_line(self, raw_line: bytes) -> None:
        line_str = raw_line.decode("latin-1")

        if line_str == ";CBEGIN":
            self.in_comment = True
            return
        if line_str == ";CEND":
            self.in_comment = False
            return
        if self.in_comment:
            return

        if line_str.startswith(";STAMP "):
            self.meta["stamp"] = line_str[7:]
            return
        if line_str.startswith(";SIGNATURE "):
            self.meta["signature"] = line_str[11:]
            return
        if line_str.startswith(";VERSION "):
            self.meta["text_version"] = int(line_str[9:].strip())
            return
        if line_str.startswith(";HEIGHT "):
            self.meta["height"] = int(line_str[8:].strip())
            return
        if line_str.startswith(";WIDTH "):
            self.meta["width"] = int(line_str[7:].strip())
            return
        if line_str.startswith(";LMARGIN "):
            self.meta["left_margin"] = int(line_str[9:].strip())
            return
        if line_str == ";CASESENSE":
            self.meta["casesense"] = True
            return
        if line_str.startswith(";DESCRIPTION "):
            self.meta["description"] = line_str[13:]
            return
        if line_str.startswith(";CONTEXTCOUNT "):
            self.meta["context_count"] = int(line_str[14:].strip())
            return

        match = re.match(r"^;UNUSEDCTX\s+(\d+)\s+((?:0x)?[0-9A-Fa-f]+)$", line_str)
        if match:
            self.meta["unused_contexts"][int(match.group(1))] = int(match.group(2), 16)
            return

        match = re.match(r"^;INDEXORDER\s+(\d+)\s+(.+)$", line_str)
        if match:
            self.meta["index_order"].append((match.group(2), int(match.group(1))))
            return

        match = re.match(r"^;TAGORDER\s+(\d+)\s+(.+)$", line_str)
        if match:
            self.meta["tag_order"].append((int(match.group(1)), match.group(2)))
            return

        if line_str.startswith(";COMMENT "):
            self.comments.append(
                CommentRecord(
                    text=line_str[9:],
                    topic_context=self.current_screen,
                )
            )
            match = re.match(r"^;COMMENT\s+ALIASCTX\s+(\d+)$", line_str)
            if match:
                self.current_alias_ids.append(int(match.group(1)))
                return
            match = re.search(r"FormatVersion\s+(\d+)", line_str)
            if match:
                self.meta["format_version"] = int(match.group(1))
            return

        match = re.match(r"^;SCREEN\s+(\w+)", line_str)
        if match:
            if self.current_screen is not None:
                self._flush_screen()
            value = match.group(1)
            self._start_screen(0xFFFF if value.startswith("noscreen") else int(value), is_page=False)
            return

        match = re.match(r"^;PAGE\s+(\d+)", line_str)
        if match:
            if self.current_screen is not None:
                self._flush_screen()
            self._start_screen(int(match.group(1)), is_page=True)
            return

        match = re.match(r"^;ALIASCTX\s+(\d+)$", line_str)
        if match:
            self.current_alias_ids.append(int(match.group(1)))
            return

        if line_str == ";ENDSCREEN":
            self._flush_screen(ended_by_endscreen=True)
            return

        match = re.match(
            r"^;KEYWORD4\s+(\d+)\s+AT\s+\((\d+),(\d+)-(\d+)\)(?:\s+NAV\s+\((\d+),(\d+),(\d+),(\d+)\))?$",
            line_str,
        )
        if match:
            self.reading_text = False
            self.post_directive_blanks = 0
            context_id = int(match.group(1))
            line_num = int(match.group(2))
            col1 = int(match.group(3))
            col2 = int(match.group(4))
            navigation = (
                tuple(int(match.group(i)) for i in range(5, 9))
                if match.group(5)
                else (None, None, None, None)
            )
            self.current_keywords_v4.append((context_id, line_num, col1, col2, *navigation))
            return

        match = re.match(r"^;KEYWORD\s+(\d+)", line_str)
        if match:
            self.reading_text = False
            self.post_directive_blanks = 0
            self.current_keywords_v5.append(int(match.group(1)))
            return

        match = re.match(r"^;INDEX\s+(.+)", line_str)
        if match:
            self.reading_text = False
            self.post_directive_blanks = 0
            index_name = match.group(1)
            self.current_screen_indices.append(index_name)
            if self.current_screen_tag:
                self.all_index_tags.append((index_name, self.current_screen, self.current_screen_tag))
                self.current_screen_tag = None
            return

        match = re.match(r"^;SCREENTAG\s+(.+)", line_str)
        if match:
            self.reading_text = False
            self.post_directive_blanks = 0
            self.current_screen_tag = match.group(1)
            return

        if line_str == ";MAININDEX":
            self.reading_text = False
            self.post_directive_blanks = 0
            self.current_is_main = True
            return

        if line_str == ";TEXTCOMPLETE":
            self.reading_text = False
            self.post_directive_blanks = 0
            self.current_text_complete_override = True
            return

        match = re.match(r"^;LINK\s+UP\s+(\d+)\s+DOWN\s+(\d+)", line_str)
        if match:
            self.reading_text = False
            self.post_directive_blanks = 0
            self.current_link_up = int(match.group(1))
            self.current_link_down = int(match.group(2))
            return

        if self.current_screen is not None and self.reading_text:
            self.current_text_lines.append(raw_line)
            return
        if self.current_screen is not None and not self.reading_text:
            if line_str == "":
                self.post_directive_blanks += 1
            else:
                self.post_directive_blanks = 0


def parse_hlx_data(data: bytes):
    """Compatibility wrapper around ``ThelpHlxSourceParser``."""
    return ThelpHlxSourceParser(data).parse()


class ThelpBinaryParser:
    """Parse THELP binary records directly into the shared intermediate model."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.format_version = 0
        self.text_version = 0
        self.internal_version = 0
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
            "main_index": 0,
            "casesense": False,
            "context_count": None,
            "unused_contexts": {},
            "index_order": [],
            "tag_order": [],
        }

    def parse(self) -> tuple[dict[str, object], list[dict[str, object]], list[tuple[bytes, int]], list[tuple[int, str]]]:
        """Parse the whole THELP file into screen dictionaries and metadata."""
        self._parse_administrative()
        while self.pos < len(self.data):
            self._parse_record()
        self.meta["_internal_version"] = self.internal_version
        index_entries = [(label, context_id) for _idx, label, context_id in self.idx_list]
        return self.meta, self.screens, index_entries, self.index_tags

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
        fv = self.internal_version
        if fv <= 3:
            options = self.read_word()
            self.meta["height"] = self.read_byte()
            self.meta["width"] = self.read_byte()
            self.meta["left_margin"] = self.read_byte()
            comp_type = self.read_byte()
            char_table = list(self.read_bytes(14))
            self.comp_rec = (comp_type, char_table)
            self.left_margin = self.meta["left_margin"]
            self.meta["casesense"] = bool(options & OF_CASESENSE)
            return

        if (fv == 4 or fv == 41) and rec_length <= 5:
            options = self.read_word()
            self.meta["height"] = self.read_byte()
            self.meta["width"] = self.read_byte()
            self.meta["left_margin"] = self.read_byte()
            self.left_margin = self.meta["left_margin"]
            self.meta["casesense"] = bool(options & OF_CASESENSE)
            self.file_hdr = {"main_idx": 0}
            return

        # fv>=5 or fv=41 with 9-byte header (e.g. SK2/KATO)
        options = self.read_word()
        main_idx = self.read_word()
        self.read_word()
        self.meta["height"] = self.read_byte()
        self.meta["width"] = self.read_byte()
        self.meta["left_margin"] = self.read_byte()
        self.left_margin = self.meta["left_margin"]
        self.meta["casesense"] = bool(options & OF_CASESENSE)
        self.meta["main_index"] = main_idx
        self.file_hdr = {"main_idx": main_idx}

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
            if offset == 0xFFFFFE:
                self.meta["unused_contexts"][i] = 0xFFFFFE
            if offset < 0xFFFF00:
                offset_to_contexts.setdefault(offset, []).append(i)
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
            "is_main": False,
            "group_end": False,
            "text_complete": False,
            "link_up": None,
            "link_down": None,
            "is_page": self.internal_version >= 5 and self.internal_version != 41 and self.keyword_rec["down"] != 0,
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
        if self.internal_version >= 5 and self.internal_version != 41:
            screen["text_complete"] = trailing_newlines_before_eot > trailing_blank_lines

        screen["lines"] = text_lines

    def _parse_keyword(self) -> None:
        screen = self._require_current_screen()

        if self.internal_version < 5 or self.internal_version == 41:
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
            return

        up_ctx = self.read_word()
        down_ctx = self.read_word()
        kw_cnt = self.read_word()
        screen["keywords_v5"].extend(self.read_word() for _ in range(kw_cnt))
        screen["indices"].extend(label for _idx, label, context in self.idx_list if context == self.screen_num)
        screen["link_up"] = up_ctx
        screen["link_down"] = down_ctx
        screen["group_end"] = down_ctx == 0
        if self.file_hdr and self.screen_num == self.file_hdr["main_idx"]:
            screen["is_main"] = True
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
        meta, screens, index_entries, _index_tags = ThelpBinaryParser(data).parse()
        return self._build_document(meta, screens, index_entries, binary_data=data)

    def _build_document(
        self,
        meta: dict[str, object],
        screens: list[dict[str, object]],
        index_entries: list[tuple[str | bytes, int]],
        binary_data: bytes | None,
        comments: list[CommentRecord] | None = None,
    ) -> HelpDocument:
        """Build the final document model from parsed THELP structures."""
        return HelpDocument(
            format_name="borland",
            source_name=self.source_name,
            topics=self._build_topics(screens),
            index_entries=[
                IndexEntry(label=self._normalize_label(label), context_id=context_id)
                for label, context_id in index_entries
            ],
            comments=list(comments or []),
            metadata=meta,
            binary_data=binary_data,
        )

    @staticmethod
    def _normalize_label(label: str | bytes) -> bytes:
        """Normalize textual or raw index labels to bytes."""
        if isinstance(label, bytes):
            return label
        return label.encode("latin-1")

    @classmethod
    def _build_topics(cls, screens: list[dict[str, object]]) -> list[TopicRecord]:
        """Convert parsed screen dictionaries into typed topic records."""
        topics = []
        for screen in screens:
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

            topics.append(
                TopicRecord(
                    context_id=screen["id"],
                    raw_lines=list(screen["lines"]),
                    index_terms=[cls._normalize_label(name) for name in screen.get("indices", [])],
                    alias_contexts=list(screen.get("alias_ids", [])),
                    sequential_keywords=list(screen.get("keywords_v5", [])),
                    positional_keywords=positional_keywords,
                    is_main_index=bool(screen.get("is_main")),
                    up_context=screen.get("link_up"),
                    down_context=screen.get("link_down"),
                )
            )
        return topics
