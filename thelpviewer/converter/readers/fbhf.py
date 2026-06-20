"""Reader and parser helpers for Turbo Vision FBHF help files."""

from __future__ import annotations

import struct

from ..base import CommentRecord, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord, ensure_document_index

FBHF_MAGIC = b"FBHF"


def is_fbhf_binary(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like an FBHF file."""
    return data[:4] == FBHF_MAGIC


def is_fbhf_source(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like TVHC textual source."""
    header = data[:4096]
    return b".topic " in header or b"TurboVision FBHF format" in header


class FBHFSourceParser:
    """Parse textual FBHF source into paragraph and cross-reference structures."""

    def __init__(self, data: bytes, from_cp: str | None = None, source_name: str = ""):
        from ..codepages import guess_display_encoding
        self.data = data
        self.lines = data.splitlines()
        self.topics: list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str, int, int]]]] = []
        self.name_to_num: dict[str, int] = {}
        self.help_counter = 2
        self.current_names: list[str] = []
        self.current_lines: list[bytes] = []
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

        for line in self.lines:
            if line == b"\x1a" or (line and line[0] == 0x1A):
                break
            line_str = line.decode("latin-1")
            if line_str.startswith(";") and not line_str.startswith("."):
                self.comments.append(
                    CommentRecord(
                        text=line_str[1:],
                        topic_context=self.name_to_num.get(self.current_names[0]) if self.current_names else None,
                    )
                )
                if self.current_names:
                    self.current_lines.append(b"")
                continue
            if line_str.startswith(".topic "):
                self._flush_topic()
                self.current_names = []
                self.current_lines = []
                for part in line_str[7:].split(","):
                    part = part.strip()
                    if "=" in part:
                        name, _num = part.split("=", 1)
                        name = name.strip()
                    else:
                        name = part
                    if name:
                        self.current_names.append(name)
            elif self.current_names:
                self.current_lines.append(line)

        self._flush_topic()
        return self.topics, self.name_to_num

    def _scan_topic_numbers(self) -> None:
        for line in self.lines:
            line_str = line.decode("latin-1")
            if not line_str.startswith(".topic "):
                continue
            for part in line_str[7:].split(","):
                part = part.strip()
                if "=" in part:
                    name, num_str = part.split("=", 1)
                    name = name.strip()
                    num = int(num_str.strip())
                    self.help_counter = num
                else:
                    name = part
                    self.help_counter += 1
                    num = self.help_counter
                if name:
                    self.name_to_num[name] = num

    def _process_xrefs(self, raw_line: bytes, para_text_offset: int) -> tuple[bytes, list[tuple[str, int, int]]]:
        # Cross-reference targets live outside the text stream, so the textual
        # source rebuilds them as `{label:target}` placeholders first.
        processed = b""
        refs: list[tuple[str, int, int]] = []
        pos = 0
        while pos < len(raw_line):
            if raw_line[pos:pos + 1] == b"{":
                if raw_line[pos:pos + 2] == b"{{":
                    processed += b"{"
                    pos += 2
                    continue
                end = raw_line.find(b"}", pos + 1)
                if end == -1:
                    processed += raw_line[pos:pos + 1]
                    pos += 1
                    continue
                inner = raw_line[pos + 1:end].decode("latin-1")
                if ":" in inner:
                    text, alias = inner.split(":", 1)
                else:
                    text = inner
                    alias = inner
                text_bytes = text.encode("latin-1").replace(b" ", b"\xff")
                refs.append((alias, para_text_offset + len(processed) + 1, len(text_bytes)))
                processed += text_bytes
                pos = end + 1
            else:
                processed += raw_line[pos:pos + 1]
                pos += 1
        return processed, refs

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
            line = self.current_lines[index]
            if line == b"":
                leading_crs += b"\r"
                index += 1
                continue

            is_wrap = line[:1] != b" "
            buffer = bytearray(leading_crs)
            leading_crs = b""
            para_refs = []

            if is_wrap:
                while index < line_count and self.current_lines[index] != b"" and self.current_lines[index][:1] != b" ":
                    processed, refs = self._process_xrefs(self.current_lines[index], total_offset + len(buffer))
                    buffer.extend(processed)
                    buffer.append(0x20)
                    para_refs.extend(refs)
                    index += 1
            else:
                while index < line_count and self.current_lines[index] != b"" and self.current_lines[index][:1] == b" ":
                    processed, refs = self._process_xrefs(self.current_lines[index], total_offset + len(buffer))
                    buffer.extend(processed)
                    buffer.append(0x0D)
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


class FBHFBinaryParser:
    """Parse FBHF binary structures directly into the shared intermediate model."""

    def __init__(self, data: bytes):
        self.data = data

    def parse(self) -> tuple[list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[int, int, int]]]], dict[str, int]]:
        """Parse all FBHF topics and synthesize stable topic names."""
        parsed_topics = []
        name_to_num: dict[str, int] = {}
        used_names: set[str] = set()

        for context_id, file_pos in self._iter_topic_offsets():
            paragraphs, crossrefs = self._read_topic(file_pos)
            base_name = self._text_to_name(paragraphs[0][1]) if paragraphs else f"Topic_{context_id}"
            topic_name = self._make_unique_name(base_name, used_names)
            used_names.add(topic_name)
            name_to_num[topic_name] = context_id
            parsed_topics.append(([topic_name], context_id, paragraphs, crossrefs))

        return parsed_topics, name_to_num

    def _iter_topic_offsets(self) -> list[tuple[int, int]]:
        data = self.data
        idx_pos = struct.unpack_from("<I", data, 8)[0]
        pos = idx_pos + 2
        word1 = struct.unpack_from("<H", data, pos)[0]
        word2 = struct.unpack_from("<H", data, pos + 2)[0]

        tp6_end = idx_pos + 2 + 2 + word1 * 4
        bp7_end = idx_pos + 2 + 4 + word2 * 6

        if tp6_end == len(data):
            pos += 2
            positions = [struct.unpack_from("<i", data, pos + i * 4)[0] for i in range(word1)]
            return [(i, positions[i]) for i in range(word1) if positions[i] >= 0]

        if bp7_end == len(data):
            used = word1
            alloc_size = word2
            pos += 4
            contexts = [struct.unpack_from("<H", data, pos + i * 2)[0] for i in range(alloc_size)]
            pos += alloc_size * 2
            positions = [struct.unpack_from("<i", data, pos + i * 4)[0] for i in range(alloc_size)]
            return [(contexts[i], positions[i]) for i in range(used)]

        raise ValueError(
            f"Cannot determine FBHF index format (tp6_end={tp6_end}, bp7_end={bp7_end}, file={len(data)})"
        )

    def _read_topic(self, file_pos: int) -> tuple[list[tuple[bool, bytes]], list[tuple[int, int, int]]]:
        pos = file_pos + 2
        paragraph_count = struct.unpack_from("<h", self.data, pos)[0]
        pos += 2

        paragraphs: list[tuple[bool, bytes]] = []
        for _ in range(paragraph_count):
            paragraph_size = struct.unpack_from("<H", self.data, pos)[0]
            pos += 2
            wrap = bool(self.data[pos])
            pos += 1
            paragraph_text = self.data[pos:pos + paragraph_size]
            pos += paragraph_size
            paragraphs.append((wrap, paragraph_text))

        ref_count = struct.unpack_from("<h", self.data, pos)[0]
        pos += 2
        crossrefs: list[tuple[int, int, int]] = []
        for _ in range(ref_count):
            ref_context = struct.unpack_from("<H", self.data, pos)[0]
            pos += 2
            ref_offset = struct.unpack_from("<h", self.data, pos)[0]
            pos += 2
            ref_length = self.data[pos]
            pos += 1
            crossrefs.append((ref_context, ref_offset, ref_length))

        return paragraphs, crossrefs

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
            topics=_build_fbhf_topics(parsed_topics),
            index_entries=_build_fbhf_index_entries(parsed_topics),
            metadata={"name_to_num": name_to_num},
            binary_data=data,
        ))


class FBHFSourceReader(HelpReaderBase):
    """Read TVHC textual source and normalize it into the shared document model."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Read one textual FBHF source buffer."""
        if not is_fbhf_source(data):
            raise ValueError("Input does not look like TurboVision FBHF source.")
        parser = FBHFSourceParser(data)
        parsed_topics, name_to_num = parser.parse()
        return ensure_document_index(HelpDocument(
            format_name="fbhf",
            source_name=self.source_name,
            topics=_build_fbhf_topics(parsed_topics),
            index_entries=_build_fbhf_index_entries(parsed_topics),
            comments=parser.comments,
            metadata={"name_to_num": name_to_num, "source_format": "tvhc"},
            binary_data=None,
        ))


def _build_fbhf_topics(
    parsed_topics: list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str, int, int]]]]
) -> list[TopicRecord]:
    """Flatten FBHF paragraphs into the raw line representation used by HTML export."""
    topics = []
    for names, primary_num, paragraphs, _crossrefs in parsed_topics:
        raw_lines = []
        for wrap, text in paragraphs:
            chunks = [chunk.rstrip(b" ") for chunk in text.split(b"\r")] if wrap else list(text.split(b"\r"))
            for chunk in chunks:
                if not chunk:
                    raw_lines.append(b"")
                elif wrap:
                    raw_lines.append(chunk)
                elif chunk.startswith(b" "):
                    raw_lines.append(chunk)
                else:
                    raw_lines.append(b" " + chunk)
        topics.append(
            TopicRecord(
                context_id=primary_num,
                raw_lines=raw_lines,
                names=list(names),
                index_terms=[names[0].encode("latin-1")] if names else [],
            )
        )
    return topics


def _build_fbhf_index_entries(
    parsed_topics: list[tuple[list[str], int, list[tuple[bool, bytes]], list[tuple[str, int, int]]]]
) -> list[IndexEntry]:
    """Create index entries for every visible topic alias."""
    entries = []
    for names, primary_num, _paragraphs, _crossrefs in parsed_topics:
        for name in names:
            entries.append(IndexEntry(label=name.encode("latin-1"), context_id=primary_num))
    return entries
