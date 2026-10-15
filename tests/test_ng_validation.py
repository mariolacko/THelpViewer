"""Bounded Norton Guide records, real pointers and in-memory reader input."""

import gzip
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.help_database import load_help_manifest
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.ng import NG_HEADER_SIZE, NGReader, _decrypt


def header(menu_count=0, title=b"Example", *, magic=b"NG", credits=()):
    data = bytearray(NG_HEADER_SIZE)
    data[:2] = magic
    struct.pack_into("<H", data, 6, menu_count)
    data[8:8 + len(title)] = title
    for index, text in enumerate(credits):
        start = 48 + index * 66
        data[start:start + len(text)] = text
    return bytes(data)


def record(kind, payload=b"", count=0, *, flag=0, parent=0, previous=0, next=0):
    fixed = bytearray(26)
    struct.pack_into("<HHHH", fixed, 0, kind, len(payload), count, flag)
    struct.pack_into("<I", fixed, 10, parent)
    struct.pack_into("<II", fixed, 18, previous, next)
    return _decrypt(bytes(fixed) + payload)


def menu(prompts=(), title=b"Menu"):
    pointers = b"".join(struct.pack("<I", target) for _label, target in prompts)
    text = bytearray(title + b"\0")
    descriptors = bytearray()
    text_start = len(pointers) + (len(prompts) + 1) * 8
    for label, _target in [*prompts, (b"", 0)]:
        descriptors.extend(struct.pack("<4H", text_start + len(text), 0, 0, 0))
        text.extend(label + b"\0")
    return record(2, pointers + descriptors + text, len(prompts) + 1, flag=len(pointers))


def short(lines=(), *, parent=0):
    table, text = bytearray(), bytearray()
    for label, target in lines:
        table.extend(struct.pack("<HI", len(lines) * 6 + len(text), target))
        text.extend(label + b"\0")
    return record(0, bytes(table + text), len(lines), parent=parent)


def long(lines=(), refs=None, *, parent=0, previous=0, next=0):
    payload = b"".join(line + b"\0" for line in lines)
    if refs is not None:
        payload += struct.pack("<H", len(refs))
        payload += b"".join(struct.pack("<I", target) for _label, target in refs)
        payload += b"".join(label + b"\0" for label, _target in refs)
    return record(1, payload, len(lines), flag=int(refs is not None), parent=parent,
                  previous=previous, next=next)


def field(data, offset, relative, fmt, value):
    changed = bytearray(data)
    encoded = struct.pack("<" + fmt, value)
    changed[offset + relative:offset + relative + len(encoded)] = _decrypt(encoded)
    return bytes(changed)


def sample():
    root = menu([(b"Index", 0)])
    index_offset = NG_HEADER_SIZE + len(root)
    index = short([(b"Target", 0)], parent=NG_HEADER_SIZE)
    leaf_offset = index_offset + len(index)
    root = menu([(b"Index", index_offset)])
    index = short([(b"Target", leaf_offset)], parent=NG_HEADER_SIZE)
    leaf = long([b"Body"], [(b"Index", index_offset)], parent=index_offset)
    return header(1) + root + index + leaf, index_offset, leaf_offset


@pytest.mark.parametrize("magic", [b"NG", b"EH"])
def test_reader_uses_supplied_bytes_without_opening_source_path_and_refreshes_header(tmp_path, magic):
    missing = tmp_path / "does-not-exist.ng"
    reader = NGReader(source_name="sample.ng", source_path=missing)
    first = reader.read_bytes(header(title=b"First", credits=[b"First credit"]) + long([b"First body"]))
    second = reader.read_bytes(header(1, b"Second", magic=magic, credits=[b"Second credit"]) + menu())
    assert first.source_name == second.source_name == "sample.ng"
    assert first.metadata["title"] == "First"
    assert second.metadata["title"] == "Second"
    assert second.metadata["credit_lines"][0] == "Second credit"
    assert first.topics[0].raw_lines == [b"First body"]
    assert second.topics[0].names == ["Menu"]
    assert first.metadata["credit_lines"][0] == "First credit"
    assert not missing.exists()


@pytest.mark.parametrize("cut", [0, 1, 2, 6, 8, 48, 377])
def test_incomplete_file_header_is_not_an_empty_successful_guide(cut):
    with pytest.raises(ValueError, match="Norton Guide"):
        NGReader().read_bytes(header()[:cut])


def test_full_width_title_and_credits_do_not_require_padding_nuls():
    document = NGReader().read_bytes(header(title=b"T" * 40, credits=[b"C" * 66]))
    assert document.metadata["title"] == "T" * 40
    assert document.metadata["credit_lines"][0] == "C" * 66


def test_empty_database_and_empty_record_addresses_remain_valid():
    assert NGReader().read_bytes(header()).topics == []
    root = menu([(b"Empty", 0)])
    child_offset = NG_HEADER_SIZE + len(root)
    root = menu([(b"Empty", child_offset)])
    data = header(1) + root + short() + long()
    document = NGReader().read_bytes(data)
    assert [topic.context_id for topic in document.topics] == [NG_HEADER_SIZE, child_offset, child_offset + 26]
    assert document.topics[1].raw_lines == document.topics[2].raw_lines == []
    assert document.topics[0].positional_keywords[0].target_context == child_offset
    assert f"[link:topic={child_offset}]Empty[/link]" in document.topics[0].uhf_content[0]


def test_missing_declared_menu_is_rejected_even_if_no_record_header_is_present():
    with pytest.raises(ValueError, match="menu count"):
        NGReader().read_bytes(header(1))


def test_invalid_first_record_is_not_skipped_to_a_later_candidate():
    data = header() + record(99) + long([b"Must not be recovered"])
    with pytest.raises(ValueError, match=r"entry type 99 at offset 378"):
        NGReader().read_bytes(data)


@pytest.mark.parametrize("prefix", [b"x", b"xx", b"\0\0", _decrypt(b"\xff\xff")])
def test_padding_before_the_first_record_is_not_a_root_offset_variant(prefix):
    with pytest.raises(ValueError, match="Norton Guide"):
        NGReader().read_bytes(header() + prefix + long([b"Later"]))


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_record_extents_and_partial_headers_never_publish_partial_topics(kind):
    body = short([(b"Text", 0)]) if kind == 0 else long([b"Text"]) if kind == 1 else menu()
    data = header(int(kind == 2)) + body
    for cut in range(NG_HEADER_SIZE + 1, len(data)):
        with pytest.raises(ValueError, match="Norton Guide"):
            NGReader().read_bytes(data[:cut])
    with pytest.raises(ValueError, match="record header"):
        NGReader().read_bytes(data + b"\0")


@pytest.mark.parametrize("payload,count", [(b"", 0), (b"", 1), (bytes(4), 2),
                                           (bytes(16), 2), (bytes(20), 2),
                                           (bytes(20) + b"Title", 2),
                                           (bytes(20) + b"Title\0", 2),
                                           (bytes(20) + b"Title\0Prompt\0", 2)])
def test_menu_requires_its_tables_exact_strings_and_trailing_byte(payload, count):
    with pytest.raises(ValueError, match="Norton Guide"):
        NGReader().read_bytes(header(1) + record(2, payload, count))


def test_menu_labels_are_not_arbitrarily_limited_to_40_or_50_characters():
    document = NGReader().read_bytes(header(1) + menu([(b"P" * 60, 0)], b"T" * 60))
    assert document.topics[0].names == ["T" * 60]
    assert document.topics[0].raw_lines == [b"P" * 60]


@pytest.mark.parametrize("text_offset,payload,count", [
    (0, bytes(6), 1), (5, bytes(6) + b"Text\0", 1),
    (100, bytes(6) + b"Text\0", 1), (6, bytes(6) + b"Text", 1),
    (0, bytes(6), 2),
])
def test_short_descriptors_and_strings_cannot_be_skipped_or_read_from_metadata(text_offset, payload, count):
    changed = bytearray(payload)
    struct.pack_into("<H", changed, 0, text_offset)
    with pytest.raises(ValueError, match="Norton Guide"):
        NGReader().read_bytes(header() + record(0, bytes(changed), count))


def test_short_text_offsets_can_be_shared_unsorted_and_followed_by_opaque_padding():
    payload = struct.pack("<HIHIHI", 25, 0, 18, 0, 25, 0) + b"Second\0First\0" + b"opaque padding"
    document = NGReader().read_bytes(header() + record(0, payload, 3))
    assert document.topics[0].raw_lines == [b"First", b"Second", b"First"]


def test_datasheet_descriptor_and_encrypted_space_run_byte_examples():
    payload = bytes.fromhex("0C 00 7A 01 00 00 0E 00 FF FF FF FF 41 00 42 00")
    data = header() + record(0, payload, 2)
    assert len(data) == 0x1A4
    topic = NGReader().read_bytes(data).topics[0]
    assert topic.raw_lines == [b"A", b"B"]
    assert topic.uhf_content == ["[link:topic=378]A[/link]", "B"]
    assert _decrypt(bytes.fromhex("5B E5 19 58 1A")) == b"A\xff\x03B\0"
    topic = NGReader().read_bytes(header() + long([b"A\xff\x03B"])).topics[0]
    assert topic.raw_lines == [b"A   B"]
    assert topic.uhf_content == ["A   B"]


@pytest.mark.parametrize("payload,count,flag", [
    (b"Text", 1, 0), (b"Text\0", 2, 0), (b"Text\0", 1, 1),
    (b"Text\0\x01", 1, 1), (b"Text\0\x01\0\x7a", 1, 1),
    (b"Text\0\x01\0" + bytes(4) + b"label", 1, 1),
])
def test_long_body_and_see_also_records_must_be_complete(payload, count, flag):
    with pytest.raises(ValueError, match="Norton Guide"):
        NGReader().read_bytes(header() + record(1, payload, count, flag=flag))


def test_long_counted_rows_and_empty_see_also_allow_opaque_record_padding():
    data = header() + record(1, b"Text\0\0\0opaque", 1, flag=7)
    assert NGReader().read_bytes(data).topics[0].raw_lines == [b"Text"]


@pytest.mark.parametrize("location,relative,fmt", [
    ("menu", 26, "I"), ("short", 28, "I"), ("short", 10, "I"),
    ("long", 10, "I"), ("long", 18, "I"), ("long", 22, "I"), ("long", 33, "I"),
])
def test_every_pointer_must_address_a_real_record_start_not_a_nearby_byte(location, relative, fmt):
    data, index, leaf = sample()
    source = NG_HEADER_SIZE if location == "menu" else index if location == "short" else leaf
    with pytest.raises(ValueError, match="does not address a record"):
        NGReader().read_bytes(field(data, source, relative, fmt, leaf + 1))


def test_only_long_next_accepts_the_exact_eof_terminal_marker():
    data = header() + long([b"Text"])
    document = NGReader().read_bytes(field(data, NG_HEADER_SIZE, 22, "I", len(data)))
    assert document.topics[0].next_context is None
    for relative in (10, 18):
        with pytest.raises(ValueError, match="does not address a record"):
            NGReader().read_bytes(field(data, NG_HEADER_SIZE, relative, "I", len(data)))


def test_shared_and_self_referencing_record_addresses_do_not_trigger_cycle_rejection():
    data = header() + long([b"Text"], [(b"Self", NG_HEADER_SIZE), (b"Again", NG_HEADER_SIZE)],
                           parent=NG_HEADER_SIZE, previous=NG_HEADER_SIZE, next=NG_HEADER_SIZE)
    document = NGReader().read_bytes(data)
    assert len(document.topics) == 1
    assert [kw.target_context for kw in document.topics[0].positional_keywords] == [NG_HEADER_SIZE] * 2


def test_manifest_uses_the_in_memory_reader_and_rejects_obsolete_path_initialization(tmp_path):
    manifest = load_help_manifest()
    assert next(spec for spec in manifest.converters if spec.name == "norton-guide").reader_init == "source"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"version": 2, "converters": [{
        "name": "ng", "source_kind": "compiled", "reader": "ng:Reader",
        "extensions": [".ng"], "reader_init": "path",
    }]}))
    with pytest.raises(ValueError, match="invalid reader_init"):
        load_help_manifest(path)


def test_ng_in_dos_backup_transport_is_unwrapped_once_before_reader_construction(tmp_path):
    data, _index, _leaf = sample()
    wrapper = bytearray(128)
    wrapper[:2] = b"\xff\x01"
    pathname = b"\\GUIDES\\SAMPLE.NG"
    wrapper[5:5 + len(pathname)] = pathname
    wrapper[0x53] = len(pathname) + 1
    path = tmp_path / "SAMPLE.NG"
    original = bytes(wrapper) + data
    path.write_bytes(original)
    document = load_document(path)
    assert document.binary_data == data
    assert document.metadata["source_container"] == {
        "format": "dos-backup", "pathname": "\\GUIDES\\SAMPLE.NG", "disk_number": 1,
    }
    assert len(document.topics) == 3
    assert document.topics[0].context_id == NG_HEADER_SIZE
    assert path.read_bytes() == original


@pytest.mark.parametrize("bad_field", ["root", "descriptor", "pointer", "count",
                                       "menu_table", "menu_caption"])
def test_failed_staged_ng_build_preserves_publication_and_retry_works(tmp_path, bad_field):
    data, index, leaf = sample()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "Norton Guides/SAMPLE.NG"
    source.parent.mkdir(parents=True)
    source.write_bytes(data)
    assert build_help_groups(["norton-guides"], sources, helps)["bundles"] == 1
    payload = json.loads(gzip.decompress((helps / "Norton Guides/sample.json.gz").read_bytes()))
    assert len(payload["topics"]) == 3
    assert f"[link:topic={leaf}]Target[/link]" in payload["topics"][str(index)]["content"][0]
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    match bad_field:
        case "root":
            broken = field(data, NG_HEADER_SIZE, 0, "H", 99)
        case "descriptor":
            broken = field(data, index, 26, "H", 0)
        case "pointer":
            broken = field(data, leaf, 10, "I", leaf + 1)
        case "menu_table":
            broken = field(data, NG_HEADER_SIZE, 6, "H", 0)
        case "menu_caption":
            broken = field(data, NG_HEADER_SIZE, 30, "H", 0)
        case _:
            broken = field(data, leaf, 4, "H", 1000)
    source.write_bytes(broken)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["norton-guides"], sources, helps)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    source.write_bytes(data)
    result = build_help_groups(["norton-guides"], sources, helps)
    backup = Path(result["backup"])
    assert published == {path.relative_to(backup): path.read_bytes() for path in backup.rglob("*") if path.is_file()}
