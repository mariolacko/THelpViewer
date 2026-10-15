import pytest

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


@pytest.mark.parametrize("encoding", ["cp1250", "cp1251", "cp1252", "windows-1252"])
def test_windows_ansi_keeps_c0_controls_instead_of_dos_screen_glyphs(encoding):
    raw = b"Windows\xa0NT\x15\x01"
    assert decode_bytes(raw, encoding) == raw.decode(encoding)
    assert build_decode_table(encoding, "unicode")[0x15] == "\x15"
    assert decode_bytes(b"\x15", "cp437") == "§"
