"""Reader and parser helpers for Turbo Vision FBHF help files."""

from __future__ import annotations

import re
import struct

from ..base import CommentRecord, HelpDocument, HelpReaderBase, IndexEntry, PositionedKeyword, TopicRecord, ensure_document_index
from .tvision_help import paragraph_lines, read_help_topic

FBHF_MAGIC = b"FBHF"
# HELPFILE.PAS's 50-column THelpWindow shrinks the viewer by two per side.
_FBHF_COLUMNS = 46
_TVHC_HEADER = re.compile(rb"^\.[ \x08]*topic(?![A-Za-z0-9_])", re.IGNORECASE)
_TVHC_WORD = re.compile(rb"[A-Za-z0-9_]+|.", re.DOTALL)
_TVHC_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# TVHC's APP contexts do not consume its automatically numbered sequence.
_TVHC_BUILTIN_CONTEXTS = {
    "Cascade": 0xFF21, "ChangeDir": 0xFF06, "Clear": 0xFF14, "Close": 0xFF27,
    "CloseAll": 0xFF22, "Copy": 0xFF12, "Cut": 0xFF11, "DosShell": 0xFF07,
    "Dragging": 1, "Exit": 0xFF08, "New": 0xFF01, "Next": 0xFF25,
    "Open": 0xFF02, "Paste": 0xFF13, "Prev": 0xFF26, "Resize": 0xFF23,
    "Save": 0xFF03, "SaveAll": 0xFF05, "SaveAs": 0xFF04, "Tile": 0xFF20,
    "Undo": 0xFF10, "Zoom": 0xFF24,
}


def is_fbhf_binary(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like an FBHF file."""
    return data[:4] == FBHF_MAGIC


def is_fbhf_source(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like TVHC textual source."""
    banner = False
    for line in data.splitlines():
        if line == b"\x1a":
            break
        if line.startswith(b";"):
            banner |= b"TurboVision FBHF format" in line
        elif line:
            return _TVHC_HEADER.match(line) is not None
    return banner


class FBHFSourceParser:
    """Parse textual FBHF source into paragraph and cross-reference structures."""

    def __init__(self, data: bytes, from_cp: str | None = None, source_name: str = ""):
        from ..codepages import guess_display_encoding
        self.data = data
        self.source_name = source_name
        self.lines = data.splitlines()
        self.topics: list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str, int, int]]]] = []
        self.name_to_num: dict[str, int] = {}
        self.help_counter = 2
        self.current_names: list[str] = []
        self.current_lines: list[tuple[int, bytes]] = []
        self.headers: dict[int, list[str]] = {}
        self.unresolved_names: list[str] = []
        self.comments: list[CommentRecord] = []
        # autodetect encoding if not given
        if from_cp:
            self.text_encoding = from_cp
        else:
            sample = self.lines[:32] if len(self.lines) > 32 else self.lines[:]
            hint = source_name or ""
            self.text_encoding = guess_display_encoding(sample, hint)

    def parse(self) -> tuple[list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str, int, int]]]], dict[str, int]]:
        """Parse the whole textual FBHF source buffer."""
        self._scan_topic_numbers()

        for line_number, line in enumerate(self.lines, 1):
            if line == b"\x1a":
                break
            line_str = line.decode("latin-1")
            if line.startswith(b";"):
                self.comments.append(
                    CommentRecord(
                        text=line_str[1:],
                        topic_context=self.name_to_num.get(self.current_names[0]) if self.current_names else None,
                    )
                )
                if self.current_names:
                    self.current_lines.append((line_number, b""))
                continue
            if line_number in self.headers:
                self._flush_topic()
                self.current_names = self.headers[line_number]
                self.current_lines = []
            elif self.current_names:
                self.current_lines.append((line_number, line))
            elif line:
                self._error("expected a .topic definition before text", line_number)

        self._flush_topic()
        known = {name.translate(_TVHC_UPPER) for name in self.name_to_num}
        unresolved = {}
        for _names, _context, _paragraphs, refs in self.topics:
            for target, _start, _length in refs:
                folded = target.translate(_TVHC_UPPER)
                if folded not in known:
                    unresolved.setdefault(folded, target)
        self.unresolved_names = list(unresolved.values())
        self._retain_active_contexts()
        return self.topics, self.name_to_num

    def _error(self, message: str, line_number: int) -> None:
        source = f" {self.source_name}" if self.source_name else ""
        raise ValueError(f"TVHC{source} line {line_number}: {message}.")

    @staticmethod
    def _word(line: bytes, position: int) -> tuple[bytes, int]:
        while position < len(line) and line[position] in (32, 8):
            position += 1
        token = _TVHC_WORD.match(line, position)
        return (token[0], token.end()) if token else (b"", position)

    def _scan_topic_numbers(self) -> None:
        known_names = set()
        for line_number, line in enumerate(self.lines, 1):
            if line == b"\x1a":
                break
            if len(line) > 253:
                self._error("physical line exceeds the native 253-byte limit", line_number)
            header = _TVHC_HEADER.match(line)
            if not header:
                if line.startswith(b"."):
                    self._error("unknown directive; expected .topic", line_number)
                continue
            names = []
            position = header.end()
            while True:
                token, position = self._word(line, position)
                if not token:
                    self._error("expected topic name", line_number)
                name = token.decode("latin-1")
                folded = name.translate(_TVHC_UPPER)
                if folded in known_names:
                    self._error(f"redefinition of topic name {name!r}", line_number)
                known_names.add(folded)
                next_token, following = self._word(line, position)
                if next_token == b"=":
                    value, position = self._word(line, following)
                    if not re.fullmatch(rb"[0-9]+", value) or int(value) > 0xFFFF:
                        self._error("expected decimal context number in 0..65535", line_number)
                    num = int(value)
                    self.help_counter = num
                else:
                    if name in _TVHC_BUILTIN_CONTEXTS:
                        num = _TVHC_BUILTIN_CONTEXTS[name]
                    else:
                        self.help_counter = (self.help_counter + 1) & 0xFFFF
                        num = self.help_counter
                self.name_to_num[name] = num
                names.append(name)
                separator, following = self._word(line, position)
                if separator != b",":
                    break  # TVHC ignores the remainder after a non-comma token.
                position = following
            self.headers[line_number] = names

    def _process_xrefs(self, raw_line: bytes, para_text_offset: int,
                       line_number: int) -> tuple[bytes, list[tuple[str, int, int]]]:
        # Mutate the same byte line as TVHC.ScanForCrossRefs, including its
        # cursor advance after an escaped '{{'; a third brace is not a link.
        processed = bytearray(raw_line)
        refs: list[tuple[str, int, int]] = []
        cursor = 0
        while (start := processed.find(b"{", cursor)) >= 0:
            label_start = start + 1
            if processed[label_start:label_start + 1] == b"{":
                del processed[label_start]
                cursor = label_start + 1
                continue
            end = processed.find(b"}", label_start)
            if end < 0:
                self._error("unterminated topic reference", line_number)
            inner = bytes(processed[label_start:end])
            label, separator, target = inner.partition(b":")
            if not separator:
                target = label
            offset = para_text_offset + label_start
            if offset > 0x7FFF:
                self._error("reference offset exceeds the signed 16-bit field", line_number)
            refs.append((target.decode("latin-1"), offset, len(label)))
            label = label.replace(b" ", b"\xff")
            processed[start:end + 1] = label
            cursor = start + len(label)
        return bytes(processed), refs

    def _flush_topic(self) -> None:
        if not self.current_names:
            return
        # Reconstruct paragraph boundaries because FBHF stores wrap-mode and raw
        # paragraph bytes, not just a flat list of rendered lines.
        paragraphs = []
        crossrefs = []
        total_offset = 0
        index = 0
        line_count = len(self.current_lines)
        leading_crs = b""

        while index < line_count:
            line_number, line = self.current_lines[index]
            if line == b"":
                leading_crs += b"\r"
                if len(leading_crs) > 4096:
                    self._error("paragraph exceeds the native 4096-byte buffer", line_number)
                index += 1
                continue

            is_wrap = line[:1] != b" "
            if len(paragraphs) >= 0x7FFF:
                self._error("topic count exceeds a signed 16-bit field", line_number)
            buffer = bytearray(leading_crs)
            leading_crs = b""
            para_refs = []

            while index < line_count:
                line_number, line = self.current_lines[index]
                if not line or (line[:1] != b" ") != is_wrap:
                    break
                processed, refs = self._process_xrefs(line, total_offset + len(buffer), line_number)
                if len(buffer) + len(processed) + 1 > 4096:
                    self._error("paragraph exceeds the native 4096-byte buffer", line_number)
                if len(crossrefs) + len(para_refs) + len(refs) > 0x7FFF:
                    self._error("topic count exceeds a signed 16-bit field", line_number)
                buffer.extend(processed)
                buffer.append(0x20 if is_wrap else 0x0D)
                para_refs.extend(refs)
                index += 1

            text = bytes(buffer)
            if text:
                paragraphs.append((is_wrap, text))
                crossrefs.extend(para_refs)
                total_offset += len(text)

        primary_name = self.current_names[0]
        self.topics.append(
            (
                self.current_names[:],
                self.name_to_num.get(primary_name, 0),
                paragraphs,
                crossrefs,
            )
        )

    def _retain_active_contexts(self) -> None:
        # THelpIndex.Add replaces a context's position, not its symbolic name.
        # Keep other contexts sharing the old object; entirely obsolete objects
        # are unindexed. Move their names to the current owner of that context.
        owners = {self.name_to_num[name]: index
                  for index, (names, _context, _paragraphs, _refs) in enumerate(self.topics)
                  for name in names}
        owned_names: dict[int, list[str]] = {}
        for name, context in self.name_to_num.items():
            owned_names.setdefault(owners[context], []).append(name)
        live = []
        for index, (names, _context, paragraphs, refs) in enumerate(self.topics):
            names = [name for name in names if owners[self.name_to_num[name]] == index]
            if not names:
                continue
            current = set(names)
            names += [name for name in owned_names[index] if name not in current]
            live.append((names, self.name_to_num[names[0]], paragraphs, refs))
        self.topics = live


class FBHFBinaryParser:
    """Parse FBHF binary structures directly into the shared intermediate model."""

    def __init__(self, data: bytes):
        self.data = data

    def parse(self) -> tuple[list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[int, int, int]]]], dict[str, int]]:
        """Parse all FBHF topics and synthesize stable topic names."""
        parsed_topics = []
        name_to_num: dict[str, int] = {}
        used_names: set[str] = set()

        offsets = self._iter_topic_offsets()
        positions = sorted({file_pos for _context, file_pos in offsets})
        index_pos = struct.unpack_from("<I", self.data, 8)[0]
        limits = dict(zip(positions, positions[1:] + [index_pos]))
        for context_id, file_pos in offsets:
            paragraphs, crossrefs = self._read_topic(file_pos, limits[file_pos])
            base_name = self._text_to_name(paragraphs[0][1]) if paragraphs else f"Topic_{context_id}"
            topic_name = self._make_unique_name(base_name, used_names)
            used_names.add(topic_name)
            name_to_num[topic_name] = context_id
            parsed_topics.append(([topic_name], context_id, paragraphs, crossrefs))

        return parsed_topics, name_to_num

    def _iter_topic_offsets(self) -> list[tuple[int, int]]:
        data = self.data
        if len(data) < 12 or data[:4] != FBHF_MAGIC:
            raise ValueError("Invalid FBHF file header.")
        if struct.unpack_from("<I", data, 4)[0] != len(data) - 8:
            raise ValueError("FBHF file size does not match its header.")
        idx_pos = struct.unpack_from("<I", data, 8)[0]
        if not 12 <= idx_pos <= len(data) - 4:
            raise ValueError("Invalid FBHF index position.")
        if struct.unpack_from("<H", data, idx_pos)[0] != 10_001:
            raise ValueError("Invalid FBHF index object type.")
        pos = idx_pos + 2
        word1 = struct.unpack_from("<H", data, pos)[0]

        tp6_end = idx_pos + 2 + 2 + word1 * 4
        if tp6_end == len(data):
            pos += 2
            positions = [struct.unpack_from("<i", data, pos + i * 4)[0] for i in range(word1)]
            if any(position < -1 for position in positions):
                raise ValueError("Invalid FBHF unused index position.")
            offsets = [(i, position) for i, position in enumerate(positions) if position != -1]
        elif idx_pos + 6 <= len(data) and (
                idx_pos + 6 + struct.unpack_from("<H", data, pos + 2)[0] * 6 == len(data)):
            used = word1
            alloc_size = struct.unpack_from("<H", data, pos + 2)[0]
            if used > alloc_size:
                raise ValueError("FBHF index Used exceeds Size.")
            pos += 4
            contexts = [struct.unpack_from("<H", data, pos + i * 2)[0] for i in range(alloc_size)]
            if any(left >= right for left, right in zip(contexts[:used], contexts[1:used])):
                raise ValueError("FBHF index contexts are not strictly sorted.")
            pos += alloc_size * 2
            positions = [struct.unpack_from("<i", data, pos + i * 4)[0] for i in range(alloc_size)]
            offsets = [(contexts[i], positions[i]) for i in range(used)]
        else:
            raise ValueError("Cannot determine FBHF index format or size.")
        if any(not 12 <= position <= idx_pos - 6 for _context, position in offsets):
            raise ValueError("FBHF topic position lies outside the topic area.")
        return offsets

    def _read_topic(self, file_pos: int, limit: int) -> tuple[list[tuple[bool, bytes]], list[tuple[int, int, int]]]:
        topic = read_help_topic(self.data, file_pos, limit, format_name="FBHF")
        return topic.paragraphs, topic.crossrefs

    @staticmethod
    def _make_unique_name(base_name: str, used_names: set[str]) -> str:
        """Keep FBHF topic identifiers unique when headings repeat."""
        if base_name not in used_names:
            return base_name
        suffix = 2
        while f"{base_name}_{suffix}" in used_names:
            suffix += 1
        return f"{base_name}_{suffix}"

    @staticmethod
    def _text_to_name(text_bytes: bytes) -> str:
        """Build a stable topic identifier from the first visible line."""
        cr_pos = text_bytes.find(0x0D)
        first_line = text_bytes[:cr_pos] if cr_pos >= 0 else text_bytes[:40]
        first_line = first_line.strip()
        result = []
        for value in first_line:
            if 65 <= value <= 90 or 97 <= value <= 122 or 48 <= value <= 57:
                result.append(chr(value))
            elif value in (32, ord("_"), ord("-"), ord("/")):
                result.append("_")
        name = "".join(result).strip("_")
        while "__" in name:
            name = name.replace("__", "_")
        return name if name else "TOPIC"


class FBHFHelpReader(HelpReaderBase):
    """High-level FBHF reader returning the shared ``HelpDocument`` model."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read one FBHF buffer and normalize it into ``HelpDocument``."""
        if not is_fbhf_binary(data):
            raise ValueError("Input is not a TurboVision FBHF help file.")
        parsed_topics, name_to_num = FBHFBinaryParser(data).parse()
        return ensure_document_index(HelpDocument(
            format_name="fbhf",
            source_name=self.source_name,
            topics=_build_fbhf_topics(parsed_topics, name_to_num),
            index_entries=_build_fbhf_index_entries(parsed_topics),
            metadata={"name_to_num": name_to_num, "display_width": _FBHF_COLUMNS},
            binary_data=data,
        ))


class FBHFSourceReader(HelpReaderBase):
    """Read TVHC textual source and normalize it into the shared document model."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read one textual FBHF source buffer."""
        parser = FBHFSourceParser(data, source_name=self.source_name)
        parsed_topics, name_to_num = parser.parse()
        return ensure_document_index(HelpDocument(
            format_name="fbhf",
            source_name=self.source_name,
            topics=_build_fbhf_topics(parsed_topics, name_to_num),
            index_entries=_build_fbhf_index_entries(parsed_topics),
            comments=parser.comments,
            metadata={"name_to_num": name_to_num, "source_format": "tvhc",
                      "display_width": _FBHF_COLUMNS,
                      "unresolved_topic_names": parser.unresolved_names,
                      "transport_metadata_keys": ["unresolved_topic_names"]},
            binary_data=None,
        ))


def _build_fbhf_topics(
    parsed_topics: list[
        tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str | int, int, int]]]
    ],
    name_to_num: dict[str, int],
) -> list[TopicRecord]:
    """Lay out native paragraph bytes before positioning their global references."""
    # TVHC assigns a context to every name on a .topic line, but all of them
    # address the same object. Resolve names to that object's primary context.
    folded_names = {name.translate(_TVHC_UPPER): primary_num
                    for names, primary_num, _paragraphs, _refs in parsed_topics for name in names}
    topics = []
    for names, primary_num, paragraphs, crossrefs in parsed_topics:
        resolved_refs = []
        for target, offset, length in crossrefs:
            # Native unresolved forward references retain their FFFFh WORD.
            target_context = target if isinstance(target, int) else folded_names.get(target.translate(_TVHC_UPPER), 0xFFFF)
            resolved_refs.append((target_context, offset, length))

        raw_lines = []
        positioned_refs = []
        paragraph_offset = 0
        for wrap, text in paragraphs:
            for start, _end, row in paragraph_lines(text, wrap, _FBHF_COLUMNS):
                start += paragraph_offset
                raw_lines.append(row.replace(b"\xff", b" "))
                for target_context, offset, length in resolved_refs:
                    first = max(offset - 1, start) - start
                    last = min(offset - 1 + length, start + len(row)) - start
                    if last > first:
                        positioned_refs.append(PositionedKeyword(
                            target_context, len(raw_lines), first + 1, last,
                        ))
            paragraph_offset += len(text)
        topics.append(
            TopicRecord(
                context_id=primary_num,
                raw_lines=raw_lines,
                names=list(names),
                alias_contexts=list(dict.fromkeys(name_to_num[name] for name in names
                                                 if name in name_to_num and name_to_num[name] != primary_num)),
                index_terms=[names[0].encode("latin-1")] if names else [],
                positional_keywords=positioned_refs,
            )
        )
    return topics


def _build_fbhf_index_entries(
    parsed_topics: list[
        tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str | int, int, int]]]
    ]
) -> list[IndexEntry]:
    """Create index entries for every visible topic alias."""
    entries = []
    for names, primary_num, _paragraphs, _crossrefs in parsed_topics:
        for name in names:
            entries.append(IndexEntry(label=name.encode("latin-1"), context_id=primary_num))
    return entries
