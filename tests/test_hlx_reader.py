from pathlib import Path

from thelpviewer.server.converter.readers.hlx_binary import HlxBinaryReader, is_hlx_binary


def test_bcw_hlx_is_binary():
    p = Path("data/sources") / "Borland C++ 4.x" / "BCW.HLX"
    assert p.exists(), f"Source HLX not found: {p}"
    data = p.read_bytes()
    assert is_hlx_binary(data)


def test_hlx_reader_produces_topics():
    p = Path("data/sources") / "Borland C++ 4.x" / "BCW.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.format_name == "hlx"
    assert doc.metadata.get("hlx_kind") == "compiled-topics"
    assert doc.metadata.get("hlx_family") == "rtf-keyword-map"
    assert hasattr(doc, "topics")
    assert len(doc.topics) >= 100


def test_ole_hlx_stays_index_view():
    p = Path("data/sources") / "Borland C++ 4.x" / "OLE.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.metadata.get("hlx_kind") == "compiled-index"
    assert doc.metadata.get("hlx_family") == "heading-catalog"
    assert float(doc.metadata.get("control_byte_total_ptr4_ratio", 0.0)) <= 0.35
    assert float(doc.metadata.get("control_byte_1_ptr4_ratio", 0.0)) <= 0.12
    assert len(doc.topics) >= 1500


def test_winspctr_hlx_stays_index_view():
    p = Path("data/sources") / "Borland C++ 4.x" / "WINSPCTR.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.metadata.get("hlx_kind") == "compiled-index"
    assert doc.metadata.get("hlx_family") == "rtf-reference-map"
    assert len(doc.topics) >= 20


def test_hlx_control_byte_modes_are_reported():
    p = Path("data/sources") / "Borland C++ 4.x" / "BCW.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    ptr2_hits = doc.metadata.get("control_byte_ptr2_hits")
    ptr4_hits = doc.metadata.get("control_byte_ptr4_hits")
    assert isinstance(ptr2_hits, dict)
    assert isinstance(ptr4_hits, dict)
    assert int(ptr2_hits.get("0", 0)) > 0
    assert int(ptr4_hits.get("0", 0)) > 0


def test_openhelp_uses_control_byte_mode_hint_for_compact_index():
    p = Path("data/sources") / "Borland C++ 4.x" / "OPENHELP.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.metadata.get("hlx_kind") == "compiled-index"
    assert doc.metadata.get("hlx_family") == "compact-index"
    assert float(doc.metadata.get("control_byte_total_ptr4_ratio", 0.0)) >= 0.6
    assert float(doc.metadata.get("control_byte_1_ptr4_ratio", 0.0)) >= 0.5


def test_index_only_hlx_gets_prev_next_navigation():
    p = Path("data/sources") / "Borland C++ 4.x" / "RSL.HLX"
    data = p.read_bytes()
    reader = HlxBinaryReader()
    reader.source_name = str(p)
    doc = reader.read_bytes(data)
    assert doc.metadata.get("hlx_kind") == "compiled-index"
    assert doc.metadata.get("index_navigation_order") == "target_offset"
    assert len(doc.topics) >= 3

    first = doc.topics[0]
    middle = doc.topics[1]
    last = doc.topics[-1]

    assert first.prev_context is None
    assert first.next_context is not None
    assert middle.prev_context is not None
    assert middle.next_context is not None
    assert last.prev_context is not None
    assert last.next_context is None
    assert any(item.label == "Next" for item in first.nav_items)
    assert any(item.label == "Prev" for item in last.nav_items)
