from pathlib import Path

from thelpviewer.converter.readers.hlx_binary import HlxBinaryReader, is_hlx_binary


def test_bcw_hlx_is_binary():
    p = Path("sources") / "Borland C++ 4.x" / "BCW.HLX"
    assert p.exists(), f"Source HLX not found: {p}"
    data = p.read_bytes()
    assert is_hlx_binary(data)


def test_hlx_reader_produces_topics():
    p = Path("sources") / "Borland C++ 4.x" / "BCW.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.format_name == "hlx"
    assert hasattr(doc, "topics")
    assert len(doc.topics) >= 100
