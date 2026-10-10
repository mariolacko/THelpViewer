from thelpviewer.server.converter.codepages import _cached_decode_table, build_decode_table, decode_bytes


def test_decode_bytes_reuses_cached_codepage_table_without_exposing_mutable_cache():
    _cached_decode_table.cache_clear()

    assert decode_bytes(b"Hello", "cp437") == "Hello"
    assert decode_bytes(bytes([0x82]), "cp437") == "é"
    cache_info = _cached_decode_table.cache_info()
    assert cache_info.misses == 1
    assert cache_info.hits == 1

    public_table = build_decode_table("cp437", "unicode")
    public_table[0x82] = "changed"
    assert decode_bytes(bytes([0x82]), "cp437") == "é"
