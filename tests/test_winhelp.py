"""Native Windows Help containers and codecs, without guessed rendering."""

import struct

import pytest

from thelpviewer.server.converter.readers.winhelp_binary import (
    WinHelpBTree, WinHelpFile, WinHelpPhrases, WinHelpSystem, WinHelpTopics,
    decompress_lz77, is_winhelp_binary,
)


def tree(descriptor, records, *, size=1024):
    def field(kind, value):
        return value + b"\0" if kind in "ziF" else int(value).to_bytes(2 if kind == "2" else 4, "little")
    body = b"".join(b"".join(field(kind, value) for kind, value in zip(descriptor, row))
                    for row in records)
    unused = size - 8 - len(body)
    assert unused >= 0
    header = struct.pack("<HHH16sHHHHHHI", 0x293B, 0x402, size, descriptor.encode(),
                         0, 0, 0, 0xFFFF, 1, 1, len(records))
    return header + struct.pack("<HHHH", unused, len(records), 0xFFFF, 0xFFFF) + body + b"X" * unused


def help_file(streams):
    # The internal FILEHEADER (9 bytes) is not part of each stream payload.
    start = 16 + 9 + 38 + 1024
    entries, data = [], bytearray()
    for name, payload in streams:
        entries.append((name.encode(), start + len(data)))
        data.extend(struct.pack("<IIB", 9 + len(payload), len(payload), 4) + payload)
    directory = tree("z4", entries)
    result = struct.pack("<IIII", 0x35F3F, 16, 0xFFFFFFFF, start + len(data))
    return result + struct.pack("<IIB", len(directory) + 9, len(directory), 4) + directory + data


def system(flags=4, records=()):
    return (struct.pack("<HHHIH", 0x36C, 21, 1, 0, flags)
            + b"".join(struct.pack("<HH", kind, len(data)) + data for kind, data in records))


def literals(data):
    return b"".join(b"\0" + data[i:i + 8] for i in range(0, len(data), 8))


def phrases(*values, minor=21):
    offsets = [2 * (len(values) + 1)]
    for value in values:
        offsets.append(offsets[-1] + len(value))
    data = b"".join(values)
    return (struct.pack("<HH", len(values), 0x100)
            + (struct.pack("<I", len(data)) if minor > 16 else b"")
            + b"".join(struct.pack("<H", value) for value in offsets)
            + (literals(data) if minor > 16 else data))


def topic_data():
    title = b"Native title"  # Implicit terminator at the declared buffer end.
    header1 = struct.pack("<IIIIIII", 0, 0xFFFFFFFF, 0xFFFFFFFF, 0,
                          0xFFFFFFFF, 12 + 49 + len(title), 0xFFFFFFFF)
    next_record = 12 + 49 + len(title)
    data1 = b"\x00\x80\x0a"  # Compressed TopicSize then TopicLength=5.
    data2 = b"test\0"
    terminal = next_record + 21 + len(data1) + len(data2)
    header = struct.pack("<IIIIIB", 49 + len(title), len(title), 0xFFFFFFFF,
                         next_record, 49, 2) + header1 + title
    display = struct.pack("<IIIIIB", 21 + len(data1) + len(data2), len(data2),
                          12, terminal, 21 + len(data1), 0x20) + data1 + data2
    end = struct.pack("<IIIIIB", 0, 0, next_record, 0xFFFFFFFF, 0, 0)
    return struct.pack("<III", 0xFFFFFFFF, 12, 0) + header + display + end


@pytest.mark.parametrize(("descriptor", "records"), [
    ("z4", [(b"|TOPIC", 100), (b"baggage", 200)]),
    ("F4", [(b"|TOPIC", 100)]),
    ("i24", [(b"keyword", 2, 4)]),
    ("L4", [(0, 0), (0xFFFFFFFF, 12)]),
    ("Lz", [(0, b"Title"), (65535, b"Other title")]),
])
def test_shared_btree_preserves_string_and_numeric_fields(descriptor, records):
    parsed = WinHelpBTree(tree(descriptor, records))
    assert [(record.key, *record.values) for record in parsed.records] == records
    assert parsed.records[0].file_offset == 46


def test_declared_streams_and_keyword_data_are_separate_address_spaces():
    keyword_tree = tree("i24", [(b"one", 2, 4), (b"two", 1, 0)])
    data = help_file([( "|KWBTREE", keyword_tree), ("|KWDATA", struct.pack("<III", 0, 200, 0xFFFFFFFF)),
                      ("opaque", b"dead.rtf\0not an article")])
    assert is_winhelp_binary(data)
    file = WinHelpFile(data)
    assert file.stream("opaque") == b"dead.rtf\0not an article"
    assert file.keyword_targets() == [(b"one", (200, 0xFFFFFFFF)), (b"two", (0,))]
    assert file.keyword_targets(keyword_tree) == file.keyword_targets()
    with pytest.raises(ValueError, match="revision"):
        file.keyword_targets(tree("i24", [(b"different", 2, 4), (b"two", 1, 0)]))


@pytest.mark.parametrize("damage", ["signature", "length", "directory", "allocation", "overlap"])
def test_invalid_container_headers_and_allocations_fail(damage):
    original = help_file([("a", b"test")])
    data = bytearray(original)
    if damage == "signature":
        data[:4] = b"fake"
    elif damage == "length":
        data.append(0)
    elif damage == "directory":
        struct.pack_into("<I", data, 4, len(data))
    elif damage == "allocation":
        struct.pack_into("<I", data, 16, 9)
    else:
        struct.pack_into("<I", data, 8, 16)
    with pytest.raises(ValueError):
        WinHelpFile(bytes(data))


def test_missing_stream_and_bad_keyword_target_bounds_fail():
    file = WinHelpFile(help_file([("|KWBTREE", tree("i24", [(b"key", 2, 0)])),
                                  ("|KWDATA", struct.pack("<I", 123))]))
    with pytest.raises(ValueError, match="Missing"):
        file.stream("|SYSTEM")
    with pytest.raises(ValueError, match="keyword targets"):
        file.keyword_targets()


def test_system_keeps_unknown_records_and_does_not_guess_commands():
    parsed = WinHelpSystem.read(system(0, [(1, b"Title\0"), (0x1234, b"opaque")]))
    assert parsed.minor == 21 and parsed.flags == 0
    assert parsed.records == ((1, b"Title\0"), (0x1234, b"opaque"))
    with pytest.raises(ValueError, match="Truncated"):
        WinHelpSystem.read(system(0, [(1, b"Title\0")])[:-1])


@pytest.mark.parametrize("size", [0, 1, 8, 9, 16, 99])
def test_lz77_literal_groups(size):
    data = bytes(range(size))
    assert decompress_lz77(literals(data), size) == data


def test_lz77_overlap_copies_and_block_padding_are_bounded():
    assert decompress_lz77(b"\x02A\0\0", 4) == b"AAAA"
    assert decompress_lz77(b"\x02A\0\xf0", 19) == b"A" * 19
    assert decompress_lz77(b"\0Agarbage", 1, padded_block=True) == b"A"
    for data, size in [(b"\x01\0", 3), (b"\x01\0\0", 3), (b"\x02A\0\0", 3), (b"\0AB", 1)]:
        with pytest.raises(ValueError):
            decompress_lz77(data, size)


@pytest.mark.parametrize("minor", [15, 21])
def test_phrase_tables_expand_pairs_spaces_nuls_and_safe_padding(minor):
    table = WinHelpPhrases(phrases(b"hello", b"world", minor=minor), minor)
    assert table.phrases == (b"hello", b"world")
    assert table.expand(b"\1\0\1\3!\0", 13) == b"helloworld !\0"
    assert table.expand(b"\1\0", 8) == b"hello\0\0\0"
    with pytest.raises(ValueError, match="Truncated"):
        table.expand(b"\1", 5)
    with pytest.raises(ValueError, match="outside"):
        table.expand(b"\1\xff", 5)
    with pytest.raises(ValueError, match="exceeds"):
        table.expand(b"\1\0", 4)
    with pytest.raises(ValueError, match="size limit"):
        table.expand(b"", 0xFFFFFFFF)


def test_phrase_table_cannot_allocate_from_an_untrusted_four_byte_size():
    data = bytearray(phrases(b"test"))
    struct.pack_into("<I", data, 4, 0xFFFFFFFF)
    with pytest.raises(ValueError, match="offset table"):
        WinHelpPhrases(bytes(data), 21)


def test_native_articles_and_offsets_retain_zero_and_real_character_spans():
    file = WinHelpFile(help_file([("|SYSTEM", system(0)), ("|TOPIC", topic_data())]))
    topics = WinHelpTopics(file)
    articles = list(topics.articles())
    assert len(articles) == 1 and articles[0].number == 0
    assert articles[0].title == b"Native title"
    assert articles[0].records[0].data2 == b"test\0"
    resolved = topics.resolve_offsets((0, 4, 5, 500, 0xFFFFFFFF))
    assert resolved[0].topic_number == 0 and resolved[0].character_offset == 0
    assert resolved[1].character_offset == 4
    assert resolved[2:] == [None, None, None]


def test_plain_topic_blocks_still_use_the_16k_logical_position_stride():
    first = struct.pack("<III", 0xFFFFFFFF, 12, 0) + b"A" * 4084
    second = struct.pack("<III", 12, 16396, 0) + b"B" * 100
    file = WinHelpFile(help_file([("|SYSTEM", system(0)), ("|TOPIC", first + second)]))
    topics = WinHelpTopics(file)
    assert topics.address_size == 16384 and topics.block_size == 4096
    assert topics._read(12 + 4080, 8) == (b"AAAABBBB", 16396 + 4)
    assert topics._read(12 + 4084, 4) == (b"BBBB", 16396 + 4)
    with pytest.raises(ValueError, match="TOPICPOS"):
        topics._read(12 + 5000, 1)


@pytest.mark.parametrize("damage", ["cycle", "previous", "length", "expanded", "topic-header"])
def test_bad_topic_chains_and_sizes_do_not_use_adjacent_memory(damage):
    data = bytearray(topic_data())
    if damage == "cycle":
        struct.pack_into("<I", data, 12 + 12, 12)
    elif damage == "previous":
        struct.pack_into("<I", data, 12 + 8, 0)
    elif damage == "length":
        struct.pack_into("<I", data, 12 + 16, 10)
    elif damage == "expanded":
        struct.pack_into("<I", data, 12 + 4, 0xFFFFFFFF)
    else:
        struct.pack_into("<I", data, 12 + 16, 48)
    topics = WinHelpTopics(WinHelpFile(help_file([("|SYSTEM", system(0)), ("|TOPIC", bytes(data))])))
    with pytest.raises(ValueError):
        list(topics.articles())


def test_unsupported_hall_codec_is_explicit_not_a_printable_string_fallback():
    file = WinHelpFile(help_file([("|SYSTEM", system()), ("|TOPIC", b""), ("|PhrIndex", b"")]))
    with pytest.raises(ValueError, match="Hall"):
        WinHelpTopics(file)
