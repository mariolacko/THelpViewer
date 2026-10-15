"""Decode native Turbo Vision THelpTopic persistence and byte-based paragraph layout."""

from dataclasses import dataclass
import struct


@dataclass(frozen=True, slots=True)
class TVHelpTopic:
    offset: int
    end: int
    paragraphs: list[tuple[bool, bytes]]
    crossrefs: list[tuple[int, int, int]]


def read_help_topic(data: bytes, offset: int, limit: int, *, format_name: str) -> TVHelpTopic:
    def require(position: int, size: int) -> None:
        if not 0 <= position <= position + size <= limit <= len(data):
            raise ValueError(f"Truncated {format_name} topic at offset {offset}.")

    require(offset, 4)
    marker, paragraph_count = struct.unpack_from("<Hh", data, offset)
    if marker != 10000:
        raise ValueError(f"Invalid {format_name} topic object type at offset {offset}.")
    if paragraph_count < 0:
        raise ValueError(f"Negative {format_name} paragraph count.")
    position = offset + 4
    paragraphs = []
    for _ in range(paragraph_count):
        require(position, 3)
        size, wrap = struct.unpack_from("<HB", data, position)
        if wrap not in (0, 1):
            raise ValueError(f"Invalid {format_name} paragraph Wrap flag.")
        position += 3
        require(position, size)
        paragraphs.append((bool(wrap), data[position:position + size]))
        position += size
    require(position, 2)
    count = struct.unpack_from("<h", data, position)[0]
    if count < 0:
        raise ValueError(f"Negative {format_name} cross-reference count.")
    position += 2
    require(position, count * 5)
    text_size = sum(len(text) for _wrap, text in paragraphs)
    crossrefs = []
    for _ in range(count):
        context, start, length = struct.unpack_from("<HhB", data, position)
        if start < 1 or start - 1 + length > text_size:
            raise ValueError(f"{format_name} cross-reference range exceeds the topic text.")
        crossrefs.append((context, start, length))
        position += 5
    return TVHelpTopic(offset, position, paragraphs, crossrefs)


def paragraph_lines(text: bytes, wrap: bool, width: int):
    """Yield (byte start, consumed end, visible bytes), matching THelpTopic.GetLine.

    CR consumes a byte but no column. FF is not a wrap delimiter. Native
    Pascal rows have a byte length, so 256-byte rows cannot be represented.
    """
    if not 1 <= width <= 255:
        raise ValueError("Turbo Vision HELP line width must be between 1 and 255.")
    position = 0
    while position < len(text):
        stop = min(position + 256, len(text))
        cr = text.find(b"\r", position, stop)
        end = cr + 1 if cr >= 0 else stop
        if wrap and end - position >= width:
            end = min(position + width, len(text))
            boundary = end
            while boundary > position and (boundary == len(text) or text[boundary] not in (32, 13, 10)):
                boundary -= 1
            if boundary > position:
                end = boundary + 1
        row = text[position:end]
        if len(row) > 255:
            raise ValueError("Unrepresentable Turbo Vision HELP row longer than 255 bytes.")
        if row.endswith(b"\r"):
            row = row[:-1]
        yield position, end, row
        position = end
