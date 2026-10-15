"""Decode bounded Windows Help containers, B+ trees and compressed topic records.

This module does not turn formatting streams into guessed article text.
Native TOPICPOS, TOPICOFFSET and context hashes are distinct address spaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_right
from functools import lru_cache
import struct


_TREE_HEADER = struct.Struct("<HHH16sHHHHHHI")
_NO_PAGE = 0xFFFF
_NO_OFFSET = 0xFFFFFFFF
_FILE_HEADER = struct.Struct("<IIB")
_LINK_HEADER = struct.Struct("<IIIIIB")
_MAX_RECORD_BYTES = 16 * 1024 * 1024


def _bounded(data: bytes, offset: int, size: int, description: str) -> bytes:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f"Truncated WinHelp {description} at {offset:#x}")
    return data[offset:offset + size]


def is_winhelp_binary(data: bytes) -> bool:
    return len(data) >= 16 and data[:4] == b"\x3f\x5f\x03\x00"


@dataclass(frozen=True, slots=True)
class WinHelpTreeHeader:
    flags: int
    page_size: int
    structure: str
    page_splits: int
    root_page: int
    total_pages: int
    levels: int
    record_count: int


@dataclass(frozen=True, slots=True)
class WinHelpTreeRecord:
    file_offset: int
    page: int
    key: bytes | int
    values: tuple[bytes | int, ...]


class WinHelpBTree:
    """Shared page traversal for string/numeric WinHelp index descriptors."""

    def __init__(self, data: bytes):
        self.data = data
        if len(data) < _TREE_HEADER.size:
            raise ValueError("Truncated WinHelp B+ tree header")
        (magic, flags, page_size, structure, zero, splits, root, minus_one,
         pages, levels, count) = _TREE_HEADER.unpack_from(data)
        descriptor = structure.split(b"\0", 1)[0]
        if magic != 0x293B or zero or minus_one != _NO_PAGE or not flags & 2:
            raise ValueError("Invalid WinHelp B+ tree header constants")
        if descriptor not in {b"z4", b"F4", b"i24", b"L4", b"Lz"}:
            raise ValueError(f"Unsupported WinHelp B+ tree descriptor {descriptor!r}")
        if page_size < 8 or not pages or not 1 <= levels <= pages or root >= pages:
            raise ValueError("Invalid WinHelp B+ tree geometry")
        if len(data) != _TREE_HEADER.size + pages * page_size:
            raise ValueError("WinHelp page count/size does not match the file length")
        self.header = WinHelpTreeHeader(flags, page_size, descriptor.decode("ascii"),
                                        splits, root, pages, levels, count)
        self.leaf_pages: list[int] = []
        self.records: list[WinHelpTreeRecord] = []
        self._parse()

    def _field(self, pos: int, end: int, kind: str) -> tuple[bytes | int, int]:
        if kind in "ziF":
            terminator = self.data.find(b"\0", pos, end)
            if terminator < 0:
                raise ValueError(f"Truncated WinHelp B+ tree string at {pos:#x}")
            return self.data[pos:terminator], terminator + 1
        size = 2 if kind == "2" else 4
        if pos + size > end:
            raise ValueError(f"Truncated WinHelp B+ tree operand at {pos:#x}")
        return int.from_bytes(self.data[pos:pos + size], "little"), pos + size

    def _parse(self) -> None:
        header = self.header
        pending = [(header.root_page, header.levels)]
        visited: set[int] = set()
        links: list[tuple[int, int]] = []
        while pending:
            page, level = pending.pop()
            if page >= header.total_pages:
                raise ValueError(f"WinHelp page reference outside the tree: {page}")
            if page in visited:
                raise ValueError(f"Repeated/cyclic WinHelp tree page {page}")
            visited.add(page)
            start = _TREE_HEADER.size + page * header.page_size
            unused, count = struct.unpack_from("<HH", self.data, start)
            end = start + header.page_size - unused
            pos = start + (6 if level > 1 else 8)
            if end < pos:
                raise ValueError(f"Invalid WinHelp free-space count on page {page}")
            if level > 1:
                children = [struct.unpack_from("<H", self.data, start + 4)[0]]
                for _ in range(count):
                    _, pos = self._field(pos, end, header.structure[0])
                    child, pos = self._field(pos, end, "2")
                    children.append(child)
                pending.extend((child, level - 1) for child in reversed(children))
            else:
                self.leaf_pages.append(page)
                links.append(struct.unpack_from("<HH", self.data, start + 4))
                for _ in range(count):
                    record_start = pos
                    key, pos = self._field(pos, end, header.structure[0])
                    values: list[bytes | int] = []
                    for kind in header.structure[1:]:
                        value, pos = self._field(pos, end, kind)
                        values.append(value)
                    self.records.append(WinHelpTreeRecord(record_start, page, key, tuple(values)))
            if pos != end:
                raise ValueError(f"WinHelp record count/free-space boundary mismatch on page {page}")
        for index, page in enumerate(self.leaf_pages):
            previous = self.leaf_pages[index - 1] if index else _NO_PAGE
            following = self.leaf_pages[index + 1] if index + 1 < len(self.leaf_pages) else _NO_PAGE
            if links[index] != (previous, following):
                raise ValueError(f"WinHelp leaf chain disagrees with tree order on page {page}")
        if len(self.records) != header.record_count:
            raise ValueError("WinHelp record count does not match the reachable leaf records")


@dataclass(frozen=True, slots=True)
class WinHelpStream:
    offset: int
    reserved: int
    flags: int
    data: bytes


class WinHelpFile:
    """Read declared internal streams, not printable data from unused space."""

    def __init__(self, data: bytes):
        if not is_winhelp_binary(data):
            raise ValueError("Invalid Windows Help file signature")
        self.data = data
        _, directory, free, length = struct.unpack_from("<IIII", data)
        if length != len(data):
            raise ValueError("Windows Help file length does not match its header")
        self.directory = self._stream(directory)
        tree = WinHelpBTree(self.directory.data)
        if tree.header.structure not in {"z4", "F4"}:
            raise ValueError("Invalid Windows Help directory descriptor")
        self.streams: dict[bytes, WinHelpStream] = {}
        ranges = [(0, 16), (directory, directory + self.directory.reserved)]
        for record in tree.records:
            if record.key in self.streams:
                raise ValueError(f"Duplicate Windows Help internal filename {record.key!r}")
            stream = self._stream(record.values[0])
            self.streams[record.key] = stream
            ranges.append((stream.offset, stream.offset + stream.reserved))
        seen: set[int] = set()
        while free != _NO_OFFSET:
            if free in seen:
                raise ValueError("Cyclic Windows Help free-block chain")
            seen.add(free)
            size, following = struct.unpack("<II", _bounded(data, free, 8, "free block"))
            if size < 8:
                raise ValueError("Invalid Windows Help free-block size")
            _bounded(data, free, size, "free-block range")
            ranges.append((free, free + size))
            free = following
        ranges.sort()
        if any(first[1] > second[0] for first, second in zip(ranges, ranges[1:])):
            raise ValueError("Overlapping Windows Help stream/free-block allocations")

    def _stream(self, offset: int) -> WinHelpStream:
        reserved, used, flags = _FILE_HEADER.unpack(_bounded(self.data, offset, 9, "stream header"))
        if reserved < used + 9:
            raise ValueError("Windows Help stream used size exceeds its allocation")
        _bounded(self.data, offset, reserved, "stream allocation")
        return WinHelpStream(offset, reserved, flags,
                             _bounded(self.data, offset + 9, used, "stream data"))

    def stream(self, name: str) -> bytes:
        try:
            return self.streams[name.encode("ascii")].data
        except KeyError:
            raise ValueError(f"Missing Windows Help stream {name}") from None

    def keyword_targets(self, tree_data: bytes | None = None) -> list[tuple[bytes, tuple[int, ...]]]:
        tree = WinHelpBTree(tree_data if tree_data is not None else self.stream("|KWBTREE"))
        if tree.header.structure != "i24":
            raise ValueError("Unsupported Windows Help keyword descriptor")
        if tree_data is not None:
            embedded = WinHelpBTree(self.stream("|KWBTREE"))
            if [(r.key, r.values) for r in tree.records] != [(r.key, r.values) for r in embedded.records]:
                raise ValueError("HLX keywords do not match this Windows Help revision")
        data = self.stream("|KWDATA")
        if len(data) % 4:
            raise ValueError("Misaligned Windows Help KWDATA array")
        records: list[tuple[bytes, tuple[int, ...]]] = []
        for record in tree.records:
            count, offset = record.values
            raw = _bounded(data, offset, 4 * count, "keyword targets")
            records.append((record.key, tuple(value[0] for value in struct.iter_unpack("<I", raw))))
        return records


def decompress_lz77(data: bytes, limit: int, *, padded_block: bool = False) -> bytes:
    """WinHelp's backward-copy LZ77, not the SZDD rotating dictionary."""
    output = bytearray()
    pos = 0
    while pos < len(data):
        if padded_block and len(output) == limit:
            break
        mask = data[pos]
        pos += 1
        for bit in range(8):
            if pos == len(data) or padded_block and len(output) == limit:
                break
            if mask & (1 << bit):
                value = int.from_bytes(_bounded(data, pos, 2, "LZ77 token"), "little")
                pos += 2
                distance, count = (value & 0xFFF) + 1, (value >> 12) + 3
                if distance > len(output):
                    raise ValueError("WinHelp LZ77 copy precedes the output buffer")
                if len(output) + count > limit:
                    raise ValueError("WinHelp LZ77 expansion exceeds its bound")
                for _ in range(count):
                    output.append(output[-distance])
            else:
                if len(output) >= limit:
                    raise ValueError("WinHelp LZ77 expansion exceeds its bound")
                output.append(data[pos])
                pos += 1
    return bytes(output)


@dataclass(frozen=True, slots=True)
class WinHelpSystem:
    minor: int
    flags: int
    timestamp: int
    records: tuple[tuple[int, bytes], ...]

    @classmethod
    def read(cls, data: bytes) -> WinHelpSystem:
        magic, minor, major, timestamp, flags = struct.unpack("<HHHIH", _bounded(data, 0, 12, "SYSTEM header"))
        if magic != 0x036C or major != 1:
            raise ValueError("Invalid Windows Help SYSTEM signature")
        records: list[tuple[int, bytes]] = []
        if minor <= 16:
            if b"\0" not in data[12:]:
                raise ValueError("Unterminated Windows Help title")
            records.append((1, data[12:data.index(b"\0", 12) + 1]))
        else:
            pos = 12
            while pos < len(data):
                kind, size = struct.unpack("<HH", _bounded(data, pos, 4, "SYSTEM record header"))
                payload = _bounded(data, pos + 4, size, "SYSTEM record")
                records.append((kind, payload))
                pos += 4 + size
        return cls(minor, flags, timestamp, tuple(records))


class WinHelpPhrases:
    def __init__(self, data: bytes, minor: int):
        count, marker = struct.unpack("<HH", _bounded(data, 0, 4, "phrase header"))
        if marker != 0x0100:
            raise ValueError("Unsupported Windows Help phrase-table variant")
        offset_start = 4 if minor <= 16 else 8
        table = _bounded(data, offset_start, (count + 1) * 2, "phrase offset table")
        offsets = [value[0] - len(table) for value in struct.iter_unpack("<H", table)]
        packed = data[offset_start + len(table):]
        if minor <= 16:
            plain = packed
        else:
            expected = struct.unpack_from("<I", data, 4)[0]
            if expected != offsets[-1]:
                raise ValueError("Windows Help phrase length disagrees with its offset table")
            plain = decompress_lz77(packed, expected)
            if len(plain) != expected:
                raise ValueError("Windows Help phrase expansion length mismatch")
        if offsets[0] != 0 or offsets[-1] != len(plain) or any(a > b for a, b in zip(offsets, offsets[1:])):
            raise ValueError("Invalid Windows Help phrase offsets")
        self.phrases = tuple(plain[start:end] for start, end in zip(offsets, offsets[1:]))

    def expand(self, data: bytes, expected: int) -> bytes:
        if not 0 <= expected <= _MAX_RECORD_BYTES:
            raise ValueError("Windows Help decoded record exceeds its size limit")
        output = bytearray()
        pos = 0
        while pos < len(data):
            value = data[pos]
            pos += 1
            if 1 <= value <= 15:
                if pos == len(data):
                    raise ValueError("Truncated Windows Help phrase token")
                token = (value - 1) * 256 + data[pos]
                pos += 1
                index = token // 2
                if index >= len(self.phrases):
                    raise ValueError("Windows Help phrase index outside the table")
                output.extend(self.phrases[index])
                if token & 1:
                    output.append(32)
            else:
                output.append(value)
            if len(output) > expected:
                raise ValueError("Windows Help phrase expansion exceeds its declared length")
        # HC31 consumers zero-fill unused declared text space. WIN31WH's
        # original records also rely on that padding; do not read past input.
        return bytes(output).ljust(expected, b"\0")


@dataclass(frozen=True, slots=True)
class WinHelpTopicLink:
    position: int
    previous: int
    following: int
    record_type: int
    data1: bytes
    data2: bytes


@dataclass(frozen=True, slots=True)
class WinHelpArticle:
    position: int
    number: int
    title: bytes
    macros: tuple[bytes, ...]
    browse_previous: int
    browse_following: int
    non_scroll: int
    scroll: int
    next_topic: int
    records: tuple[WinHelpTopicLink, ...]


@dataclass(frozen=True, slots=True)
class WinHelpTopicTarget:
    topic_number: int
    record_position: int
    character_offset: int


class WinHelpTopics:
    """Read linked native record payloads; formatting is a separate layer."""

    def __init__(self, file: WinHelpFile):
        self.system = WinHelpSystem.read(file.stream("|SYSTEM"))
        if self.system.minor <= 16:
            raise ValueError("Windows Help 3.0 topic addressing is not implemented")
        if self.system.flags not in {0, 4, 8}:
            raise ValueError("Unsupported Windows Help topic compression flags")
        self.data = file.stream("|TOPIC")
        self.block_size = 2048 if self.system.flags == 8 else 4096
        # HC31 keeps the 16-KiB logical TOPICPOS stride even for plain blocks.
        self.address_size = 16384
        self.phrases = WinHelpPhrases(file.stream("|Phrases"), self.system.minor) if b"|Phrases" in file.streams else None
        if b"|PhrIndex" in file.streams:
            raise ValueError("Windows Help Hall phrase compression is not implemented")

    @lru_cache(maxsize=8)
    def _block(self, number: int) -> bytes:
        start = number * self.block_size
        _bounded(self.data, start, 12, "topic-block header")
        packed = self.data[start + 12:min(len(self.data), start + self.block_size)]
        return (decompress_lz77(packed, self.address_size, padded_block=True)
                if self.system.flags else packed)

    def _read(self, position: int, size: int) -> tuple[bytes, int]:
        if position < 12 or size < 0:
            raise ValueError("Invalid Windows Help TOPICPOS/read size")
        number, offset = divmod(position - 12, self.address_size)
        output = bytearray()
        while size:
            block = self._block(number)
            if offset == len(block):
                number += 1
                offset = 0
                continue
            if offset >= len(block):
                raise ValueError("Windows Help TOPICPOS outside its decompressed block")
            count = min(size, len(block) - offset)
            output.extend(block[offset:offset + count])
            size -= count
            offset += count
            if size:
                number += 1
                offset = 0
        return bytes(output), number * self.address_size + offset + 12

    def links(self):
        position = 12
        visited: set[int] = set()
        previous = _NO_OFFSET
        while position not in {0, _NO_OFFSET}:
            if position in visited:
                raise ValueError("Cyclic Windows Help topic-link chain")
            visited.add(position)
            header, after = self._read(position, _LINK_HEADER.size)
            size, expanded, back, following, first_size, kind = _LINK_HEADER.unpack(header)
            if following in {0, _NO_OFFSET}:
                return  # The terminal sentinel has no displayable payload.
            if back != previous or not _LINK_HEADER.size <= first_size <= size:
                raise ValueError("Invalid Windows Help topic-link header/previous pointer")
            if size > _MAX_RECORD_BYTES or expanded > _MAX_RECORD_BYTES:
                raise ValueError("Windows Help topic-link record exceeds its size limit")
            data1, after = self._read(after, first_size - _LINK_HEADER.size)
            packed, _ = self._read(after, size - first_size)
            if expanded > len(packed):
                if self.phrases is None:
                    raise ValueError("Compressed Windows Help text has no phrase table")
                data2 = self.phrases.expand(packed, expanded)
            else:
                data2 = packed[:expanded]
            yield WinHelpTopicLink(position, back, following, kind, data1, data2)
            previous = position
            position = following

    def articles(self):
        """Group only native type-2 headers and their linked display records."""
        header: WinHelpTopicLink | None = None
        records: list[WinHelpTopicLink] = []

        def article() -> WinHelpArticle:
            if header is None or len(header.data1) != 28:
                raise ValueError("Invalid Windows Help 3.1 topic header")
            _, back, following, number, non_scroll, scroll, next_topic = struct.unpack("<IIIIIII", header.data1)
            # The stored buffer length also terminates its last string;
            # HC31 consumers append a safe NUL after phrase expansion.
            strings = header.data2.rstrip(b"\0").split(b"\0")
            return WinHelpArticle(header.position, number, strings[0], tuple(strings[1:]),
                                  back, following, non_scroll, scroll, next_topic, tuple(records))

        for record in self.links():
            if record.record_type == 2:
                if header is not None:
                    previous_article = article()
                    if previous_article.next_topic != record.position:
                        raise ValueError("Windows Help topic-header chain disagrees with record order")
                    yield previous_article
                header = record
                records = []
            elif header is None:
                raise ValueError("Windows Help display record precedes its topic header")
            else:
                records.append(record)
        if header is not None:
            yield article()

    def _target_index(self) -> tuple[list[int], list[tuple[int, int, int]]]:
        """Build bounded TOPICOFFSET ranges from native TopicLength fields."""
        starts: list[int] = []
        ranges: list[tuple[int, int, int]] = []
        block = -1
        characters = 0
        for article in self.articles():
            for record in article.records:
                if record.record_type not in {0x20, 0x23}:
                    raise ValueError("Unsupported Windows Help display-record type")
                number = (record.position - 12) // self.address_size
                if number != block:
                    block, characters = number, 0
                size_word = int.from_bytes(_bounded(record.data1, 0, 2, "compressed TopicSize"), "little")
                pos = 4 if size_word & 1 else 2
                first = _bounded(record.data1, pos, 1, "compressed TopicLength")[0]
                length = first >> 1
                if first & 1:
                    length += _bounded(record.data1, pos + 1, 1, "compressed TopicLength operand")[0] * 128
                if characters + length > 0x8000:
                    raise ValueError("Windows Help TopicLength exceeds its block address range")
                if length:
                    starts.append(block * 0x8000 + characters)
                    ranges.append((block * 0x8000 + characters + length, article.number, record.position))
                characters += length
        if any(first >= second for first, second in zip(starts, starts[1:])):
            raise ValueError("Non-monotonic Windows Help topic character ranges")
        return starts, ranges

    def resolve_offsets(self, offsets: tuple[int, ...]) -> list[WinHelpTopicTarget | None]:
        """Resolve inside an actual record span, never to a nearest article."""
        starts, ranges = self._target_index()
        resolved: list[WinHelpTopicTarget | None] = []
        for offset in offsets:
            index = bisect_right(starts, offset) - 1
            if index >= 0 and offset < ranges[index][0]:
                _, topic, position = ranges[index]
                resolved.append(WinHelpTopicTarget(topic, position, offset - starts[index]))
            else:
                resolved.append(None)  # Missing spans/macros remain unresolved.
        return resolved
