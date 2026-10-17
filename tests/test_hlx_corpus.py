"""Every native record, independently enumerated using HelpDeco's B+ tree code."""

import hashlib
import json
from pathlib import Path
import zlib

import pytest

from thelpviewer.server.converter.readers.hlx_binary import HlxBinaryParser, HlxBinaryReader


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "tests/golden/hlx/keyword_trees.json").read_text())


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda item: item["file"])
def test_hlx_native_keyword_tree(fixture):
    path = ROOT / "var/sources/Borland C++ 4.x" / fixture["file"]
    data = path.read_bytes()
    assert f"{zlib.crc32(data):08X}" == fixture["crc32"]
    assert hashlib.sha256(data).hexdigest() == fixture["source_sha256"]
    parser = HlxBinaryParser(data)
    records = [[r.file_offset, r.label.hex(), r.reference_count, r.kwdata_offset]
               for r in parser.records]
    digest = hashlib.sha256((json.dumps(records, separators=(",", ":")) + "\n").encode()).hexdigest()
    assert digest == fixture["record_sha256"]
    assert parser.header.total_pages == fixture["pages"]
    assert parser.header.levels == fixture["levels"]
    assert parser.header.keyword_count == len(records) == fixture["keywords"]
    assert sum(r.reference_count for r in parser.records) == fixture["references"]
    assert parser.records[0].label.decode("cp1252") == fixture["first"]
    assert parser.records[-1].label.decode("cp1252") == fixture["last"]

    document = HlxBinaryReader(source_name=path.name, text_encoding="cp1252").read_bytes(data)
    assert document.binary_data == data
    assert document.metadata["hlx_kind"] == "compiled-index"
    assert len(document.topics) == len(document.index_entries) == len(records)
    assert [topic.raw_lines for topic in document.topics] == [[r.label] for r in parser.records]
    assert [entry.label for entry in document.index_entries] == [r.label for r in parser.records]
    for ordinal, (topic, record) in enumerate(zip(document.topics, parser.records), start=1):
        assert topic.context_id == ordinal
        assert not topic.positional_keywords and not topic.sequential_keywords and not topic.nav_items
        assert topic.prev_context is None and topic.next_context is None
        assert document.metadata["hlx_keyword_records"][ordinal - 1] == {
            "keyword_id": ordinal, "file_offset": record.file_offset, "page": record.page,
            "reference_count": record.reference_count, "kwdata_offset": record.kwdata_offset,
        }
