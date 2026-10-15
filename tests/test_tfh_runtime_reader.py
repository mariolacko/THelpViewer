"""Profiler context maps and cells verified with original TPROF execution."""

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.tdh import TdhHelpReader, probe_tfh_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


SAMPLES = [
    ("Borland Turbo Profiler", 0xEDCB6DAB, 363, 363, 321,
     "9a4badb7700c04dcd3b74882f3a59ba7f984498a0ac77ac529b5f6ac65fb0df9"),
    ("Borland Turbo Assembler 2.01", 0xC7CCE043, 366, 367, 325,
     "e254bac6eadfdbc56f162cc5f7b4e7a0a1a3d58aed2519ba7119c9a28a6160f5"),
]


def source(folder):
    path = Path("data/sources") / folder / "TFHELP.TFH"
    if not path.is_file():
        pytest.skip("Original Profiler HELP not available")
    return path


@pytest.mark.parametrize("folder,crc,stored,count,links,digest", SAMPLES)
def test_profiler_maps_cells_and_links_match_native_runtime(folder, crc, stored, count, links, digest):
    path = source(folder)
    data = path.read_bytes()
    probe = probe_tfh_binary(data)
    assert probe and probe.crc32 == crc and probe.table_word_count == stored
    assert detect_format_handler("UNKNOWN.BIN", data).name == "tfh"
    document = TdhHelpReader(source_path=path).read_bytes(data)
    assert len(document.topics) == count
    assert document.metadata["display_width"] == 48
    assert document.metadata["tfh_decode"]["runtime_table_word_count"] == stored + 1
    assert sum(len(topic.positional_keywords) for topic in document.topics) == links
    ids = {topic.context_id for topic in document.topics}
    cells = [(topic.context_id, [line.hex() for line in topic.raw_lines],
              [(key.target_context, key.line, key.first_column, key.last_column)
               for key in topic.positional_keywords]) for topic in document.topics if topic.context_id]
    assert hashlib.sha256(json.dumps(cells, separators=(",", ":")).encode()).hexdigest() == digest
    assert document.topics[0].uhf_content == [""]
    assert document.contents[0].topic_id == 2
    for topic in document.topics:
        assert len(topic.raw_lines) <= 15
        assert all(len(line) <= 48 and b"<E>" not in line for line in topic.raw_lines)
        assert topic.next_context is None or topic.next_context in ids
        for key in topic.positional_keywords:
            assert key.target_context in ids
            assert 1 <= key.first_column <= key.last_column <= len(topic.raw_lines[key.line])


def test_profiler_101_final_page_and_link_are_not_discarded_as_a_tail():
    data = source(SAMPLES[1][0]).read_bytes()
    probe = probe_tfh_binary(data)
    assert probe.separator_word == 0x2C00
    document = TdhHelpReader().read_bytes(data)
    page = document.topics[-1]
    assert page.context_id == 366
    assert page.raw_lines[0] == b"There are no source modules available for you to"
    assert "[link:topic=228]Options Source Directories[/link]" in "\n".join(page.uhf_content)


@pytest.mark.parametrize("suffix,extra_rows", [
    (b"\0", []),
    (b"\r\nNEXT\0", [b"NEXT"]),
    (b" NEXT\0", [b"NEXT"]),
])
def test_profiler_hotspot_can_end_at_column_48_without_a_lookahead_reservation(suffix, extra_rows):
    original = source(SAMPLES[1][0]).read_bytes()
    stored = int.from_bytes(original[:2], "big")
    page_start = 2 + 2*stored + sum(struct.unpack_from(f">{stored}h", original, 2))

    def literal(text):
        nibbles = [n for value in text for n in (15, value & 15, value >> 4)]
        nibbles += [0] * (len(nibbles) % 2)
        return bytes(nibbles[i] | (nibbles[i+1] << 4) for i in range(0, len(nibbles), 2))

    # Replace only the last addressed page; preserve the original runtime
    # map. Native TPROF keeps all 48 cells even before NUL or CR/LF.
    block = b"\0\0" + literal(b"x"*23) + literal(b"^") + b"\0\1"
    block += literal(b"L"*25 + b"^" + suffix)
    document = TdhHelpReader().read_bytes(original[:page_start] + block)
    page = document.topics[-1]
    assert len(document.topics) == 367 and page.context_id == 366
    assert page.raw_lines == [b"x"*23 + b"L"*25, *extra_rows]
    assert page.uhf_content == [
        "x"*23 + "[link:topic=1]" + "L"*25 + "[/link]",
        *[row.decode("ascii") for row in extra_rows],
    ]
    assert [(k.target_context, k.line, k.first_column, k.last_column)
            for k in page.positional_keywords] == [(1, 0, 24, 48)]


@pytest.mark.parametrize("base_word", [0x0100, 0x4100])
def test_profiler_base_word_is_runtime_slot_presence_not_a_magic_signature(base_word):
    data = bytearray(source(SAMPLES[1][0]).read_bytes())
    base = 2 + 2 * int.from_bytes(data[:2], "big")
    struct.pack_into(">H", data, base, base_word)
    assert probe_tfh_binary(bytes(data)) is not None
    assert len(TdhHelpReader().read_bytes(bytes(data)).topics) == 367
    # A zero overlapping slot suppresses that page, just as native TPROF does.
    struct.pack_into(">H", data, base, 0)
    assert len(TdhHelpReader().read_bytes(bytes(data)).topics) == 366


@pytest.mark.parametrize("cut", [1, 10, 258, 5000])
def test_profiler_truncation_fails_without_publishing_a_partial_file(cut):
    data = source(SAMPLES[1][0]).read_bytes()
    with pytest.raises(ValueError, match="[Tt]runcated"):
        TdhHelpReader().read_bytes(data[:-cut])


@pytest.mark.parametrize("folder", [item[0] for item in SAMPLES])
def test_profiler_corrupt_map_fails_instead_of_stopping_early(folder):
    data = bytearray(source(folder).read_bytes())
    struct.pack_into(">H", data, 4, 0x8000)
    with pytest.raises(ValueError, match="context map outside file"):
        TdhHelpReader().read_bytes(bytes(data))


def test_profiler_101_exports_a_separate_complete_edition_without_changing_originals(tmp_path):
    path = source(SAMPLES[1][0])
    original = path.read_bytes()
    results = export_bundle_tree(Path("data/sources"), tmp_path, source_paths=[path], layout="helps")
    assert len(results) == 1 and results[0].topic_count == 367
    assert path.read_bytes() == original
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    entry = catalog[0]
    assert entry["product"] == "td" and entry["version"] == "1.01"
    assert entry["file"] == "Borland Turbo Debugger/Profiler/Assembler/tfhelp-1.01.json.gz"
    bundle = json.loads(gzip.decompress((tmp_path / entry["file"]).read_bytes()))
    assert len(bundle["topics"]) == 367 and "366" in bundle["topics"]
    assert bundle["metadata"]["display"]["cols"] == 48
    assert bundle["metadata"]["help_contents_topic_id"] == 1
    assert not bundle["metadata"].get("unresolved_contexts", {}).get("links")
