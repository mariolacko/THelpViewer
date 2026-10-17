"""Concatenated LN databases must retain content, identity and local offsets."""

import gzip
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.catalog import rebuild_catalog
from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.quickhelp import QuickHelpReader
from thelpviewer.server.converter.writers.bundle import export_bundle, export_bundle_tree


def _database(name, records, contexts, *, attributes=0):
    """Small uncompressed LN fixture with database-relative section pointers."""
    blobs = []
    for text, target in records:
        text = text.encode("ascii")
        attrs = bytes([len(text)])
        if target is not None:
            link = bytes([1, len(text)])
            link += (b"\x00" + struct.pack("<H", 0x8000 | target)
                     if isinstance(target, int) else target.encode("ascii") + b"\x00")
            attrs += b"\xff" + link
        binary = bytes([len(text) + 1]) + text + bytes([len(attrs) + 1]) + attrs
        compact = b"".join(b"\x1a" + bytes([value]) if 0x10 <= value <= 0x1a
                           else bytes([value]) for value in binary)
        blobs.append(struct.pack("<H", len(binary)) + compact)
    strings = b"".join(alias.encode("ascii") + b"\x00" for alias, _topic in contexts)
    mapping = b"".join(struct.pack("<H", topic) for _alias, topic in contexts)
    index_offset = 0x46
    strings_offset = index_offset + 4 * (len(records) + 1)
    map_offset = strings_offset + len(strings)
    text_offset = map_offset + len(mapping)
    offsets = [text_offset]
    for blob in blobs:
        offsets.append(offsets[-1] + len(blob))
    header = bytearray(0x46)
    header[:2] = b"LN"
    struct.pack_into("<HHBBHHHH", header, 2, 2, attributes, ord(":"), 0,
                     len(records), len(contexts), 80, 0)
    header[0x10:0x1e] = name.encode("ascii").ljust(14, b"\x00")
    struct.pack_into("<10I", header, 0x1e, 0, index_offset, strings_offset,
                     map_offset, 0, 0, text_offset, 0, 0, offsets[-1])
    return bytes(header) + struct.pack(f"<{len(offsets)}I", *offsets) + strings + mapping + b"".join(blobs)


def test_concatenated_database_keeps_distinct_ids_and_local_direct_links():
    first = _database("FIRST.HLP", [("First", 0)], [("h.contents", 0)])
    second = _database("SECOND.HLP", [("Second", 0)], [("h.contents", 0)])
    document = QuickHelpReader(source_name="PACK.HLP").read_bytes(first + second)

    assert [topic.context_id for topic in document.topics] == [0, 1]
    assert document.topics[0].uhf_content == ["[link:topic=0]First[/link]"]
    assert document.topics[1].uhf_content == ["[link:topic=1]Second[/link]"]
    assert "SECOND.HLP!h.contents" in document.topics[1].alias_strings
    assert [entry.context_id for entry in document.index_entries] == [0, 1]
    assert [node.topic_id for node in document.contents] == [0, 1]
    assert document.metadata["help_contents_topic_id"] == 0
    assert document.metadata["quickhelp_databases"][1] == {
        "name": "SECOND.HLP", "offset": len(first), "size": len(second),
        "first_topic_id": 1, "topic_count": 1, "case_sensitive": False,
    }


def test_logical_database_links_resolve_in_same_container_and_from_sibling(tmp_path):
    container = tmp_path / "PACK.hlp"
    container.write_bytes(
        _database("FIRST.HLP", [("Second", "SECOND.HLP!h.contents")], [("h.contents", 0)])
        + _database("SECOND.HLP", [("Local", "h.contents")], [("h.contents", 0)])
    )
    source = tmp_path / "OTHER.hlp"
    source.write_bytes(_database("OTHER.HLP", [("Second", "SECOND.HLP!h.contents")], [("other", 0)]))

    for path in (container, source):
        document = load_document(path)
        assert document.topics[0].uhf_content == [
            "[link:file=PACK.hlp,topic=1,alias=SECOND.HLP!h.contents]Second[/link]",
        ]
    assert load_document(container).topics[1].uhf_content == ["[link:topic=1,alias=h.contents]Local[/link]"]


def test_secondary_contents_navigation_stays_in_its_own_database():
    first = _database("FIRST.HLP", [("First", None)], [("h.contents", 0)])
    second = _database("SECOND.HLP", [("Contents", "-9996")], [("h.contents", 0)])
    document = QuickHelpReader().read_bytes(first + second)
    assert document.topics[1].uhf_content == ["[link:topic=1]Contents[/link]"]
    assert document.topics[1].nav_items[0].topic_id == 1


def test_qualified_navigation_selects_named_database_not_current_home(tmp_path):
    source = tmp_path / "PACK.HLP"
    source.write_bytes(
        _database("FIRST.HLP", [("Second home", "SECOND.HLP!hv")], [("h.contents", 0)])
        + _database("SECOND.HLP", [("First home", "FIRST.HLP!hv")], [("h.contents", 0)])
    )
    document = load_document(source)
    assert document.topics[0].uhf_content == ["[link:file=PACK.HLP,topic=1,alias=SECOND.HLP!hv]Second home[/link]"]
    assert document.topics[1].uhf_content == ["[link:file=PACK.HLP,topic=0,alias=FIRST.HLP!hv]First home[/link]"]
    other = tmp_path / "OTHER.HLP"
    other.write_bytes(_database("OTHER.HLP", [("Index", "SECOND.HLP!vx")], [("other", 0)]))
    assert load_document(other).topics[0].uhf_content == ["[link:file=PACK.HLP,alias=SECOND.HLP!vx]Index[/link]"]


def test_in_memory_conversion_preserves_qualified_links_without_a_sibling_directory():
    first = _database("FIRST.HLP", [("Second", "SECOND.HLP!h.contents")], [("first", 0)])
    second = _database("SECOND.HLP", [("Second", None)], [("h.contents", 0)])
    document = QuickHelpReader().read_bytes(first + second)
    assert document.topics[0].uhf_content == [
        "[link:file=SECOND.HLP,alias=SECOND.HLP!h.contents]Second[/link]",
    ]


def test_named_database_with_missing_context_does_not_guess_another_database(tmp_path):
    source = tmp_path / "SOURCE.HLP"
    source.write_bytes(_database("SOURCE.HLP", [("Link", "FIRST.HLP!missing")], [("missing", 0)]))
    (tmp_path / "PACK.HLP").write_bytes(
        _database("FIRST.HLP", [("First", None)], [("first", 0)])
        + _database("SECOND.HLP", [("Second", None)], [("missing", 0)])
    )
    document = load_document(source)
    assert document.topics[0].uhf_content == ["[link:file=FIRST.HLP,alias=FIRST.HLP!missing]Link[/link]"]


def test_case_sensitive_contexts_are_not_folded_locally_or_across_files(tmp_path):
    source = tmp_path / "SOURCE.HLP"
    source.write_bytes(_database("SOURCE.HLP", [("Link", "CASE.HLP!mixed")], [("source", 0)]))
    case = tmp_path / "CASE.HLP"
    case.write_bytes(_database("CASE.HLP", [("Link", "mixed")], [("MIXED", 0)], attributes=1))
    assert load_document(source).topics[0].uhf_content == ["[link:file=CASE.HLP,alias=CASE.HLP!mixed]Link[/link]"]
    assert load_document(case).topics[0].uhf_content == ["Link"]


def test_context_index_is_invalidated_when_source_is_replaced(tmp_path):
    source = tmp_path / "SOURCE.HLP"
    source.write_bytes(_database("SOURCE.HLP", [("Link", "TARGET.HLP!target")], [("source", 0)]))
    target = tmp_path / "TARGET.HLP"
    target.write_bytes(_database("TARGET.HLP", [("Target", None)], [("target", 0)]))
    assert "topic=0" in load_document(source).topics[0].uhf_content[0]
    target.write_bytes(_database("TARGET.HLP", [("Other", None), ("Target", None)], [("target", 1)]))
    assert "topic=1" in load_document(source).topics[0].uhf_content[0]


@pytest.mark.parametrize("corrupt", ["short", "zero-size", "oversize", "trailing", "truncated-second"])
def test_invalid_container_does_not_silently_drop_data(corrupt):
    original = _database("FIRST.HLP", [("First", None)], [("first", 0)])
    data = bytearray(original)
    if corrupt == "short":
        data = data[:20]
    elif corrupt == "zero-size":
        struct.pack_into("<I", data, 0x42, 0)
    elif corrupt == "oversize":
        struct.pack_into("<I", data, 0x42, len(data) + 1)
    elif corrupt == "trailing":
        data += b"unexpected trailing bytes"
    else:
        data += original[:-1]
    with pytest.raises(ValueError, match="QuickHelp"):
        QuickHelpReader().read_bytes(bytes(data))


def test_single_and_tree_export_keep_physical_url_and_logical_catalog_names(tmp_path):
    source = tmp_path / "PACK.HLP"
    source.write_bytes(
        _database("FIRST.HLP", [("First", None)], [("first", 0)])
        + _database("SECOND.HLP", [("Second", 0)], [("second", 0)])
    )
    single = export_bundle(source, tmp_path / "single")
    results = export_bundle_tree(tmp_path, tmp_path / "tree", layout="helps", source_paths=[source])
    assert single.topic_count == results[0].topic_count == 2
    assert single.json_path.name == results[0].json_path.name == "pack.json.gz"
    payload = json.loads(gzip.decompress(single.json_path.read_bytes()))
    assert set(payload["topics"]) == {"0", "1"}
    assert payload["metadata"]["catalog_source_files"] == ["PACK.HLP", "FIRST.HLP", "SECOND.HLP"]
    assert len(payload["metadata"]["quickhelp_databases"]) == 2
    catalog_path = tmp_path / "tree" / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    assert catalog[0]["source_files"] == ["PACK.HLP", "FIRST.HLP", "SECOND.HLP"]
    rebuild_catalog(tmp_path / "tree", catalog_path)
    assert json.loads(catalog_path.read_text()) == catalog


@pytest.mark.parametrize("product,filename,counts", [
    ("Microsoft QuickBASIC Extended 7.1", "BC.HLP", [20, 22]),
    ("Microsoft QuickBASIC Extended 7.1", "LINK.HLP", [155, 51]),
    ("Microsoft QuickBASIC Extended 7.1", "UTILS.HLP", [59, 102, 73, 43, 36]),
    ("Microsoft QuickC, C, and C++ 6.0", "LINK.HLP", [155, 51]),
])
def test_original_multi_database_files_export_every_topic_without_renumbering_first(product, filename, counts):
    source = Path("var/sources") / product / filename
    if not source.exists():
        pytest.skip("Original Microsoft corpus is not installed")
    document = load_document(source)
    assert len(document.topics) == sum(counts)
    assert [entry["topic_count"] for entry in document.metadata["quickhelp_databases"]] == counts
    assert [topic.context_id for topic in document.topics] == list(range(sum(counts)))
    first_size = struct.unpack_from("<I", source.read_bytes(), 0x42)[0]
    first = QuickHelpReader(source_name=source.name, source_path=source).read_bytes(source.read_bytes()[:first_size])
    assert document.topics[:counts[0]] == first.topics
