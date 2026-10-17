import gzip
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.readers.hlx_binary import HlxBinaryParser
from thelpviewer.server.converter.writers.bundle import export_bundle


SOURCES = [Path("var/sources") / collection for collection in ("Borland C++ 4.x", "Borland C++ 4.5")]


@pytest.mark.parametrize("source", sorted(path for root in SOURCES for path in root.glob("*.HLX")),
                         ids=lambda path: path.parent.name + "/" + path.name)
def test_hlx_exports_exact_keyword_labels_and_retains_companion_addresses(tmp_path, source):
    parser = HlxBinaryParser(source.read_bytes())
    result = export_bundle(source, tmp_path)
    assert result.format_name == "hlx" and result.json_path.exists()
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))
    assert payload["uhf_version"] == "2.0"
    metadata = payload["metadata"]
    assert metadata["source"]["format"] == "hlx"
    assert metadata["source"]["encoding"] == "cp1252"
    assert metadata["hlx_kind"] == "compiled-index"
    assert metadata["index_record_count"] == parser.header.keyword_count
    assert len(payload["topics"]) == len(parser.records)
    assert len(metadata["hlx_keyword_records"]) == len(parser.records)
    assert metadata["hlx_header"]["leaf_pages"] == parser.leaf_pages

    from thelpviewer.server.converter.uhf_markup import escape_uhf_text
    for ordinal, record in enumerate(parser.records, start=1):
        topic = payload["topics"][str(ordinal)]
        label = record.label.decode("cp1252")
        assert topic["content"] == [escape_uhf_text(label)]
        assert not topic.get("nav")
        assert metadata["hlx_keyword_records"][ordinal - 1] == {
            "keyword_id": ordinal, "file_offset": record.file_offset, "page": record.page,
            "reference_count": record.reference_count, "kwdata_offset": record.kwdata_offset,
        }

    # These are real index records, not heuristic strings recovered from free space.
    entries = [entry for section in payload["index"] for entry in section["entries"]]
    assert len(entries) == len(parser.records)
    assert {entry["label"] for entry in entries} == {r.label.decode("cp1252") for r in parser.records}
    assert not any(key in metadata for key in ("hlx_family", "pointer_count", "control_byte_dominant"))
