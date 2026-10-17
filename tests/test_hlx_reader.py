import struct

import pytest

from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.hlx import is_hlx_source
from thelpviewer.server.converter.readers.hlx_binary import HlxBinaryParser, HlxBinaryReader, is_hlx_binary


PAGE_SIZE = 128
HEADER_SIZE = 38
NO_PAGE = 0xFFFF


def _leaf(records, previous=NO_PAGE, following=NO_PAGE, *, size=PAGE_SIZE):
    body = b"".join(key + b"\0" + struct.pack("<HI", count, address)
                    for key, count, address in records)
    used = 8 + len(body)
    assert used <= size
    # Deliberately plausible dead labels/pointers in the free-space area.
    garbage = (b"DEADBEEF stale.rtf\0\x01\0\x80\0\0\0" * size)[:size - used]
    return struct.pack("<HHHH", size - used, len(records), previous, following) + body + garbage


def _branch(first, separators=(), *, size=PAGE_SIZE):
    body = b"".join(label + b"\0" + struct.pack("<H", child) for label, child in separators)
    used = 6 + len(body)
    assert used <= size
    return struct.pack("<HHH", size - used, len(separators), first) + body + b"X" * (size - used)


def _tree(pages, *, root=0, levels=1, count=1, size=PAGE_SIZE, flags=2):
    return (struct.pack("<HHH16sHHHHHHI", 0x293B, flags, size, b"i24\0stale.rtf",
                        0, 0, root, NO_PAGE, len(pages), levels, count) + b"".join(pages))


def _three_levels():
    # Physical page order is unrelated to the logical keyword order.
    pages = [
        _leaf([(b"C", 1, 0x10004)], previous=5),
        _branch(3, [(b"B", 5)]),
        _branch(1, [(b"C", 4)]),
        _leaf([(b"A", 2, 0x10000)], following=5),
        _branch(0),
        _leaf([(b"B", 1, 0x10008)], previous=3, following=0),
    ]
    return _tree(pages, root=2, levels=3, count=3)


def _replace_word(data, offset, value):
    result = bytearray(data)
    struct.pack_into("<H", result, offset, value)
    return bytes(result)


def test_declared_records_only_no_synthetic_hotspots_or_article_groups():
    keys = [(b"!", 2, 0x10000), (b"RTF 32-bit", 3, 0x10008), (b"x", 1, 0)]
    data = _tree([_leaf(keys)], count=3)
    parser = HlxBinaryParser(data)
    assert [(r.label, r.reference_count, r.kwdata_offset) for r in parser.records] == keys
    document = HlxBinaryReader().read_bytes(data)
    assert [t.raw_lines for t in document.topics] == [[key] for key, _, _ in keys]
    assert all(not t.positional_keywords and not t.nav_items for t in document.topics)
    assert document.binary_data == data
    assert not any(key in document.metadata for key in ("pointer_count", "hlx_family", "control_byte_dominant"))


def test_multilevel_tree_follows_children_and_double_linked_leaf_order():
    parser = HlxBinaryParser(_three_levels())
    assert parser.leaf_pages == [3, 5, 0]
    assert [r.label for r in parser.records] == [b"A", b"B", b"C"]
    # KWDATA offsets are not local HLX offsets or a page-navigation order.
    assert [r.kwdata_offset for r in parser.records] == [0x10000, 0x10008, 0x10004]


@pytest.mark.parametrize("size", [64, 1024, 2048, 4096])
def test_page_size_is_not_a_pool_start(size):
    parser = HlxBinaryParser(_tree([_leaf([(b"first", 1, 0)], size=size)], size=size))
    assert parser.records[0].file_offset == 46
    assert parser.records[0].label == b"first"


def test_duplicates_and_suffix_labels_are_not_discarded():
    records = [(b"functions", 1, 4), (b"ions", 1, 4), (b"IONS", 2, 8), (b"ions", 1, 4)]
    document = HlxBinaryReader().read_bytes(_tree([_leaf(records)], count=4))
    assert [entry.label for entry in document.index_entries] == [r[0] for r in records]
    assert len(document.topics) == 4


def test_keywords_have_no_arbitrary_ascii_length_limit():
    key = b"A" * 180 + b"\xa0NT?"
    data = _tree([_leaf([(key, 4, 0xFFFF0000)], size=256)], size=256)
    reader = HlxBinaryReader(text_encoding="cp1252")
    document = reader.read_bytes(data)
    assert document.topics[0].raw_lines == [key]
    assert document.topics[0].names == ["A" * 180 + "\u00a0NT?"]
    assert document.metadata["hlx_keyword_records"][0]["kwdata_offset"] == 0xFFFF0000


def test_empty_leaf_and_unreferenced_allocated_page():
    data = _tree([_leaf([]), b"garbage" + b"\0" * (PAGE_SIZE - 7)], count=0)
    parser = HlxBinaryParser(data)
    assert parser.records == [] and parser.leaf_pages == [0]
    assert HlxBinaryReader().read_bytes(data).topics == []


def test_extra_header_flags_are_preserved_not_used_to_guess_a_family():
    parser = HlxBinaryParser(_tree([_leaf([(b"Windows", 1, 0)])], flags=0x2002))
    assert parser.header.flags == 0x2002


def test_source_directive_text_inside_a_real_keyword_is_not_a_source_file(tmp_path):
    data = _tree([_leaf([(b";SCREEN syntax", 1, 0)])])
    assert is_hlx_binary(data)
    assert HlxBinaryParser(data).records[0].label == b";SCREEN syntax"
    handler = detect_format_handler(tmp_path / "keyword.hlx", data)
    assert handler is not None and handler.source_kind == "index"
    assert handler.load(tmp_path / "keyword.hlx", data).metadata["hlx_kind"] == "compiled-index"


def test_other_btree_descriptor_is_not_mistaken_for_this_keyword_format():
    data = bytearray(_tree([_leaf([(b"key", 1, 0)])]))
    data[6:10] = b"Lz\0\0"
    assert not is_hlx_binary(data)
    with pytest.raises(ValueError, match="signature"):
        HlxBinaryParser(data)


@pytest.mark.parametrize("data", [b"", b"\0" * 4096, b"Not a tree" * 300,
                                   b";SCREEN 1\nHello\n;ENDSCREEN\n" * 20,
                                   b";COMMENT binary-looking \x3b\x29i24\0" * 20])
def test_detector_does_not_accept_unrelated_or_source_hlx(data):
    assert not is_hlx_binary(data)
    with pytest.raises(ValueError, match="signature"):
        HlxBinaryParser(data)


def test_source_hlx_uses_its_separate_reader(tmp_path):
    data = b";SCREEN 12\nhello\n;ENDSCREEN\n"
    assert is_hlx_source(data) and not is_hlx_binary(data)
    path = tmp_path / "source.hlx"
    handler = detect_format_handler(path, data)
    assert handler is not None
    document = handler.load(path, data)
    assert document.topics[0].context_id == 12
    assert document.topics[0].raw_lines == [b"hello"]


@pytest.mark.parametrize(("offset", "value"), [
    (0, 0), (2, 0), (4, 7), (22, 1), (26, 1), (28, 0), (30, 0), (30, 2),
    (32, 0), (32, 2), (34, 2), (38, 0xFFFF), (40, 0), (40, 0xFFFF),
    (42, 0), (44, 0),
])
def test_invalid_header_page_counts_and_links_fail(offset, value):
    data = _replace_word(_tree([_leaf([(b"key", 1, 0)])]), offset, value)
    with pytest.raises(ValueError):
        HlxBinaryReader().read_bytes(data)


@pytest.mark.parametrize("suffix", [b"", b"\0", b"additional page"])
def test_truncated_or_appended_files_do_not_fall_back_to_scanned_text(suffix):
    data = _tree([_leaf([(b"key", 1, 0)])])
    damaged = data[:-1] if not suffix else data + suffix
    assert is_hlx_binary(damaged)
    with pytest.raises(ValueError, match="file length"):
        HlxBinaryParser(damaged)


@pytest.mark.parametrize("cut", range(7))
def test_operands_cannot_borrow_bytes_from_unused_page_tail(cut):
    data = _tree([_leaf([(b"keyword", 1, 0)])])
    unused = struct.unpack_from("<H", data, 38)[0]
    data = _replace_word(data, 38, unused + cut + 1)
    with pytest.raises(ValueError, match="Truncated"):
        HlxBinaryParser(data)


def test_unterminated_key_cannot_scan_the_next_page():
    page = struct.pack("<HHHH", 0, 1, NO_PAGE, NO_PAGE) + b"A" * (PAGE_SIZE - 8)
    data = _tree([page, _leaf([(b"not part of first key", 1, 0)])])
    with pytest.raises(ValueError, match="Truncated"):
        HlxBinaryParser(data)


@pytest.mark.parametrize("child", [2, NO_PAGE, 6])
def test_duplicate_cyclic_and_out_of_range_index_children_fail(child):
    data = _three_levels()
    data = _replace_word(data, 38 + 2 * PAGE_SIZE + 4, child)
    with pytest.raises(ValueError):
        HlxBinaryParser(data)


def test_index_separator_operand_is_bounded_by_used_space():
    data = _three_levels()
    offset = 38 + 2 * PAGE_SIZE
    unused = struct.unpack_from("<H", data, offset)[0]
    with pytest.raises(ValueError, match="Truncated"):
        HlxBinaryParser(_replace_word(data, offset, unused + 1))


def test_invalid_tree_export_fails_without_overwriting_an_existing_bundle(tmp_path):
    from thelpviewer.server.converter.writers.bundle import export_bundle

    source = tmp_path / "damaged.hlx"
    source.write_bytes(_tree([_leaf([(b"key", 1, 0)])])[:-1])
    destination = tmp_path / "out"
    destination.mkdir()
    published = destination / "damaged.json.gz"
    published.write_bytes(b"previous verified bundle")
    result = export_bundle(source, destination)
    assert bool(result.error)
    assert published.read_bytes() == b"previous verified bundle"
