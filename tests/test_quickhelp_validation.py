"""LN section bounds and all three decoding stages fail without partial HELP."""

from pathlib import Path
import struct

import pytest

from test_quickhelp_containers import _database
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.quickhelp import QuickHelpReader, _keyword_expand


def _encoded_database(binary, *, compact=None, dictionary=b"", tree=None):
    data = bytearray(_database("TEST.HLP", [("Test", None)], [("test", 0)]))
    index, _strings, _mapping, _keywords, _huffman, text = struct.unpack_from("<6I", data, 0x22)
    header_and_tables = data[:text]
    huffman = struct.pack(f"<{len(tree) + 1}h", *tree, 0) if tree is not None else b""
    if compact is None:
        compact = b"".join(b"\x1a" + bytes([value]) if 0x10 <= value <= 0x1a
                           else bytes([value]) for value in binary)
    start = text + len(dictionary) + len(huffman)
    raw = struct.pack("<H", len(binary)) + compact
    struct.pack_into("<II", header_and_tables, index, start, start + len(raw))
    struct.pack_into("<III", header_and_tables, 0x2e,
                     text if dictionary else 0, text + len(dictionary) if huffman else 0, start)
    struct.pack_into("<I", header_and_tables, 0x42, start + len(raw))
    return bytes(header_and_tables) + dictionary + huffman + raw


@pytest.mark.parametrize("offset,value", [
    (0x22, 0), (0x22, 0xFFFFFFFF), (0x26, 70), (0x26, 0xFFFFFFFF),
    (0x2a, 70), (0x2a, 0xFFFFFFFF), (0x2e, 70), (0x32, 70),
    (0x36, 70), (0x36, 0xFFFFFFFF),
])
def test_invalid_sections_cannot_read_header_or_another_section(offset, value):
    data = bytearray(_database("TEST.HLP", [("Test", None)], [("test", 0)]))
    struct.pack_into("<I", data, offset, value)
    with pytest.raises(ValueError, match="QuickHelp"):
        QuickHelpReader().read_bytes(bytes(data))


@pytest.mark.parametrize("change", ["before-text", "equal", "reverse", "beyond-end", "short", "last-end"])
def test_invalid_topic_ranges_never_become_empty_topics(change):
    data = bytearray(_database("TEST.HLP", [("First", None), ("Second", None)], [("first", 0)]))
    index = struct.unpack_from("<I", data, 0x22)[0]
    a, b, end = struct.unpack_from("<3I", data, index)
    offsets = {
        "before-text": (a - 1, b, end), "equal": (a, a, end),
        "reverse": (a, a - 1, end), "beyond-end": (a, end + 1, end),
        "short": (a, a + 1, end), "last-end": (a, b, end - 1),
    }[change]
    struct.pack_into("<3I", data, index, *offsets)
    with pytest.raises(ValueError, match="QuickHelp topic index"):
        QuickHelpReader().read_bytes(bytes(data))


def test_invalid_context_topic_is_not_used_for_a_link():
    data = _database("TEST.HLP", [("Test", None)], [("test", 1)])
    with pytest.raises(ValueError, match="context map"):
        QuickHelpReader().read_bytes(data)


def test_invalid_direct_link_target_is_not_silently_discarded():
    data = _database("TEST.HLP", [("Test", 1)], [("test", 0)])
    with pytest.raises(ValueError, match="direct link references a nonexistent topic"):
        QuickHelpReader().read_bytes(data)


def test_nonzero_huffman_pointer_does_not_describe_an_absent_tree():
    data = bytearray(_encoded_database(b"\1\1"))
    text = struct.unpack_from("<I", data, 0x36)[0]
    struct.pack_into("<I", data, 0x32, text)
    with pytest.raises(ValueError, match="section boundaries"):
        QuickHelpReader().read_bytes(bytes(data))


def test_context_cannot_terminate_in_the_mapping_table():
    data = bytearray(_database("TEST.HLP", [("Test", None)], [("test", 0)]))
    mapping = struct.unpack_from("<I", data, 0x2a)[0]
    data[mapping - 1] = ord("x")
    with pytest.raises(ValueError, match="context string"):
        QuickHelpReader().read_bytes(bytes(data))


@pytest.mark.parametrize("tree", [[2], [1, -1, -2], [6, -1, -2], [4, 2, -1], [0, -1]])
def test_invalid_huffman_nodes_fail_before_decoding(tree):
    with pytest.raises(ValueError, match="Huffman"):
        QuickHelpReader().read_bytes(_encoded_database(b"\1\1", compact=b"\0", tree=tree))


def test_truncated_huffman_terminator_is_rejected():
    data = bytearray(_encoded_database(b"\1\1", compact=b"\0", tree=[4, -255, -255]))
    text = struct.unpack_from("<I", data, 0x36)[0]
    struct.pack_into("<h", data, text - 2, -1)
    with pytest.raises(ValueError, match="Huffman tree terminator"):
        QuickHelpReader().read_bytes(bytes(data))


@pytest.mark.parametrize("dictionary", [b"\5abc", b"\1x" * 1025])
def test_invalid_dictionary_does_not_silently_stop(dictionary):
    with pytest.raises(ValueError, match="dictionary"):
        QuickHelpReader().read_bytes(_encoded_database(b"\1\1", dictionary=dictionary))


@pytest.mark.parametrize("compact", [b"", b"A", b"\x18", b"\x19", b"\x19A", b"\x1a", b"\x10"])
def test_incomplete_compression_control_fails_with_database_and_topic(compact):
    with pytest.raises(ValueError, match="database 'TEST.HLP', topic 0:.*Truncated"):
        QuickHelpReader().read_bytes(_encoded_database(b"\1\1", compact=compact))


@pytest.mark.parametrize("compact", [b"\x10\0", b"\x17\xff"])
def test_invalid_dictionary_reference_is_not_dropped(compact):
    with pytest.raises(ValueError, match="dictionary reference"):
        QuickHelpReader().read_bytes(_encoded_database(b"\1\1", compact=compact))


@pytest.mark.parametrize("compact", [b"\x18\3", b"\x19A\3"])
def test_run_cannot_exceed_outlen(compact):
    with pytest.raises(ValueError, match="exceeds OUTLEN"):
        QuickHelpReader().read_bytes(_encoded_database(b"\1\1", compact=compact))


@pytest.mark.parametrize("binary,field", [
    (b"\0", "zero-length text"), (b"\2A\0", "zero-length attribute"),
    (b"\5ab", "text block"), (b"\2A", "attribute block"),
    (b"\2A\5x", "attribute block"),
    (b"\2A\4\1\xff\1", "link range"),
    (b"\2A\6\1\xff\1\1x", "link context"),
    (b"\2A\6\1\xff\1\1\0", "direct link target"),
])
def test_truncated_binary_blocks_and_links_are_not_returned_as_plain_text(binary, field):
    with pytest.raises(ValueError, match=field):
        QuickHelpReader().read_bytes(_encoded_database(binary))


def test_dictionary_space_repeat_and_escape_produce_exact_declared_bytes():
    assert _keyword_expand(b"\x14\0\x18\2\x19X\3\x1a\x10", 11, [b"word"]) == b"word   XXX\x10"
    document = QuickHelpReader().read_bytes(_encoded_database(
        b"\6Hello\2\5", compact=b"\6\x10\0\2\5", dictionary=b"\5Hello"))
    assert document.topics[0].uhf_content == ["Hello"]


@pytest.mark.parametrize("tree,compact", [(None, b"\1\1"), ([4, -255, -255], b"\0"), ([-255], b"")])
def test_topic_ends_at_outlen_not_a_nul_or_huffman_padding(tree, compact):
    document = QuickHelpReader().read_bytes(_encoded_database(b"\1\1", compact=compact, tree=tree))
    assert document.topics[0].raw_lines == [b""]
    assert document.topics[0].uhf_content == [""]


def test_outlen_zero_is_a_valid_empty_topic():
    assert QuickHelpReader().read_bytes(_encoded_database(b"")).topics[0].raw_lines == []


SOURCES = sorted(str(path) for path in Path("data/sources").glob("Microsoft*/*.HLP")
                 if path.read_bytes()[:4] == b"LN\2\0")


@pytest.mark.parametrize("source", SOURCES)
def test_all_installed_original_quickhelp_databases_decode_every_declared_topic(source):
    data = Path(source).read_bytes()
    offset = count = 0
    while offset < len(data):
        count += struct.unpack_from("<H", data, offset + 8)[0]
        offset += struct.unpack_from("<I", data, offset + 0x42)[0]
    document = load_document(source)
    assert len(document.topics) == count
    assert all(topic.raw_lines for topic in document.topics)


def test_bad_quickhelp_preserves_published_library_and_retry_works(tmp_path):
    original = Path("data/sources/Microsoft QuickC, C, and C++ 2.50/QA.HLP").read_bytes()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "Microsoft QuickC, C, and C++ 2.50" / "QA.HLP"
    source.parent.mkdir(parents=True)
    source.write_bytes(original)
    build_help_groups(["microsoft"], sources, helps)
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    damaged = bytearray(original)
    index = struct.unpack_from("<I", damaged, 0x22)[0]
    first_topic = struct.unpack_from("<I", damaged, index)[0]
    struct.pack_into("<H", damaged, first_topic, 0xFFFF)
    source.write_bytes(damaged)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["microsoft"], sources, helps)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    source.write_bytes(original)
    result = build_help_groups(["microsoft"], sources, helps)
    assert result["backup"] and result["bundles"] == 1
