import pytest
from pathlib import Path
from thelpviewer.converter.readers.hlx_binary import HlxBinaryReader, is_hlx_binary

SMALL_FILES = [
    "sources/Borland C++ 4.x/BWCC.HLX",
    "sources/Borland C++ 4.x/OPENHELP.HLX",
    "sources/Borland C++ 4.x/WINSIGHT.HLX",
    "sources/Borland C++ 4.x/WINSPCTR.HLX",
]


def test_small_hlx_have_hotspots():
    for p in SMALL_FILES:
        path = Path(p)
        assert path.exists(), f"Sample file missing: {p}"
        data = path.read_bytes()
        assert is_hlx_binary(data), f"{p} not recognized as HLX binary"
        reader = HlxBinaryReader()
        reader.source_name = str(path)
        doc = reader.read_bytes(data)
        total = len(doc.topics)
        has_links = sum(1 for t in doc.topics if getattr(t, "positional_keywords", None))
        assert total >= 1, f"{p} produced no topics"
        assert has_links > 0, f"{p} has no positional keywords (topics={total})"
