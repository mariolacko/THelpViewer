import os

from thelpviewer.converter.readers.hlx_deterministic import parse_hlx_deterministic


def test_hlx_deterministic_ole_basic():
    """Basic sanity: deterministic parser reads topics/indexes from OLE.HLX
    without relying on external fixtures or mappings.
    """
    p = os.path.join("sources", "Borland C++ 4.x", "OLE.HLX")
    data = open(p, "rb").read()
    res = parse_hlx_deterministic(data, min_topics=1)
    assert res is not None
    topics, index_entries, pointer_map = res
    assert isinstance(topics, list) and len(topics) > 0
    assert isinstance(index_entries, list) and len(index_entries) > 0

    # If a pointer table was inferred, validate the mapping points into the
    # string pool and references valid topic indices.
    if pointer_map:
        for addr, ctx in pointer_map.items():
            assert isinstance(addr, int) and 0 <= addr < len(data)
            assert isinstance(ctx, int) and 1 <= ctx <= len(topics)
            raw = topics[ctx - 1].raw_lines[0] if topics[ctx - 1].raw_lines else b""
            assert isinstance(raw, (bytes, bytearray))
            assert len(raw) >= 1
