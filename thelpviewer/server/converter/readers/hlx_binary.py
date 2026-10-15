"""Read standalone WinHelp keyword B+ trees stored in Borland .HLX files.

The tree contains keyword counts and offsets into the companion help's
keyword-data stream, not article bodies or inline hotspot instructions.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..base import HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from .winhelp_binary import WinHelpBTree


_HEADER_SIZE = 38


@dataclass(frozen=True, slots=True)
class HlxHeader:
    flags: int
    page_size: int
    page_splits: int
    root_page: int
    total_pages: int
    levels: int
    keyword_count: int


@dataclass(frozen=True, slots=True)
class HlxKeywordRecord:
    file_offset: int
    page: int
    label: bytes
    reference_count: int
    kwdata_offset: int


def is_hlx_binary(data: bytes) -> bool:
    """Recognize the keyword-tree signature without accepting arbitrary blobs."""
    return len(data) >= _HEADER_SIZE and data[:2] == b"\x3b\x29" and data[6:10] == b"i24\0"


class HlxBinaryParser:
    """A keyword-specific projection of the shared Windows Help B+ tree."""

    def __init__(self, data: bytes):
        self.data = data
        if not is_hlx_binary(data):
            raise ValueError("Invalid HLX keyword-tree signature (expected 293Bh / i24)")
        tree = WinHelpBTree(data)
        header = tree.header
        self.header = HlxHeader(header.flags, header.page_size, header.page_splits,
                                header.root_page, header.total_pages, header.levels,
                                header.record_count)
        self.leaf_pages = tree.leaf_pages
        self.records = [HlxKeywordRecord(record.file_offset, record.page, record.key,
                                        record.values[0], record.values[1])
                        for record in tree.records]


class HlxBinaryReader(HelpReaderBase):
    """Expose exact keywords without inventing articles or local destinations."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        parser = HlxBinaryParser(data)
        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []
        keyword_records: list[dict[str, int]] = []
        for ordinal, record in enumerate(parser.records, start=1):
            topics.append(TopicRecord(
                context_id=ordinal,
                raw_lines=[record.label],
                index_terms=[record.label],
                names=[record.label.decode(self.text_encoding, errors="replace")],
            ))
            index_entries.append(IndexEntry(label=record.label, context_id=ordinal))
            keyword_records.append({
                "keyword_id": ordinal,
                "file_offset": record.file_offset,
                "page": record.page,
                "reference_count": record.reference_count,
                "kwdata_offset": record.kwdata_offset,
            })
        header = parser.header
        return HelpDocument(
            format_name="hlx",
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            binary_data=data,
            metadata={
                "format_name": "hlx-binary",
                "hlx_kind": "compiled-index",
                "index_record_count": header.keyword_count,
                "hlx_header": {
                    "flags": header.flags,
                    "structure": "i24",
                    "page_size": header.page_size,
                    "page_splits": header.page_splits,
                    "root_page": header.root_page,
                    "total_pages": header.total_pages,
                    "levels": header.levels,
                    "leaf_pages": parser.leaf_pages,
                },
                "hlx_keyword_records": keyword_records,
                "transport_metadata_keys": ["hlx_header", "hlx_keyword_records"],
            },
        )
