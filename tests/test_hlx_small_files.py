import pytest
from pathlib import Path
from thelpviewer.converter.readers.hlx_binary import HlxBinaryReader, is_hlx_binary

SMALL_FILES = [
    "data/sources/Borland C++ 4.x/BWCC.HLX",
    "data/sources/Borland C++ 4.x/OPENHELP.HLX",
    "data/sources/Borland C++ 4.x/WINSIGHT.HLX",
    "data/sources/Borland C++ 4.x/WINSPCTR.HLX",
]


def test_small_hlx_have_clean_index_records():
    for p in SMALL_FILES:
        path = Path(p)
        assert path.exists(), f"Sample file missing: {p}"
        data = path.read_bytes()
        assert is_hlx_binary(data), f"{p} not recognized as HLX binary"
        reader = HlxBinaryReader()
        reader.source_name = str(path)
        doc = reader.read_bytes(data)
        total = len(doc.topics)
        labels = [entry.label.decode("latin-1") for entry in doc.index_entries]
        assert total >= 1, f"{p} produced no topics"
        assert doc.metadata.get("hlx_kind") == "compiled-index"
        assert labels, f"{p} produced no index entries"
        assert all(label.strip() for label in labels), f"{p} produced blank index labels"
