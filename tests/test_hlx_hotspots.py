from pathlib import Path

from thelpviewer.converter.readers.hlx_binary import HlxBinaryReader


def test_content_rich_hlx_prefers_deterministic_topics():
    p = Path("data/sources") / "Borland C++ 4.x" / "BCW.HLX"
    assert p.exists(), f"Source HLX not found: {p}"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.metadata.get("hlx_kind") == "compiled-topics"
    assert doc.metadata.get("pointer_count", 0) > 0
    assert any(topic.positional_keywords for topic in doc.topics)


def test_topic_rich_hlx_without_pointer_map_still_uses_topics():
    p = Path("data/sources") / "Borland C++ 4.x" / "BCDOS.HLX"
    assert p.exists(), f"Source HLX not found: {p}"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.metadata.get("hlx_kind") == "compiled-topics"
    assert doc.metadata.get("pointer_count", 0) == 0
    assert len(doc.topics) >= 50
    assert any(topic.positional_keywords for topic in doc.topics)
