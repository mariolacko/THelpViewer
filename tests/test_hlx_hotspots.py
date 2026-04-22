from pathlib import Path

from thelpviewer.converter.readers.hlx_binary import HlxBinaryReader


def test_hlx_hotspots_detected():
    p = Path("sources") / "Borland C++ 4.x" / "BCW.HLX"
    assert p.exists(), f"Source HLX not found: {p}"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    # At least one topic should contain positional hotspots mapped to other contexts
    assert any(len(t.positional_keywords) > 0 for t in doc.topics), "No positional hotspots detected"
