import struct

from thelpviewer.converter.readers.fbhf import FBHFHelpReader, FBHFSourceReader
from thelpviewer.converter.writers.json import HelpJsonRenderer


def _topic(paragraph: bytes, crossrefs: list[tuple[int, int, int]]) -> bytes:
    payload = bytearray(struct.pack("<HhHB", 10_000, 1, len(paragraph), 1))
    payload.extend(paragraph)
    payload.extend(struct.pack("<h", len(crossrefs)))
    for context_id, offset, length in crossrefs:
        payload.extend(struct.pack("<HhB", context_id, offset, length))
    return bytes(payload)


def _binary_fbhf() -> bytes:
    first = _topic(b"See target", [(1, 5, 6)])
    second = _topic(b"Target topic", [])
    first_offset = 12
    second_offset = first_offset + len(first)
    index_offset = second_offset + len(second)
    index = struct.pack("<HHii", 10_001, 2, first_offset, second_offset)
    file_size = index_offset + len(index)
    header = b"FBHF" + struct.pack("<II", file_size - 8, index_offset)
    return header + first + second + index


def test_source_reader_preserves_case_insensitive_cross_reference():
    source = (
        b".topic First=2\r\n"
        b"See {Second topic:second}.\r\n"
        b".topic Second=3\r\n"
        b"Target.\r\n"
    )

    document = FBHFSourceReader(source_name="sample.txt").read_bytes(source)
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()

    assert document.topics[0].sequential_keywords == [3]
    assert payload["topics"]["2"]["content"] == ["See [link:topic=3]Second topic[/link]."]


def test_binary_reader_preserves_cross_reference():
    document = FBHFHelpReader(source_name="sample.hlp").read_bytes(_binary_fbhf())
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()

    assert document.topics[0].sequential_keywords == [1]
    assert payload["topics"]["0"]["content"] == ["See [link:topic=1]target[/link]"]
