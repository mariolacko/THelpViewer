"""THELP records are bounded units, not permission to borrow the next record."""

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.thelp import THELP_SIG, ThelpBinaryParser, ThelpHelpReader, is_thelp_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


TABLE = b"\0 etaoinshrdlc"


def admin(version=52, text_version=1, *, signature=THELP_SIG):
    return b"Example HELP\0\x1a" + signature + b"\0" + bytes([version, text_version])


def record(kind, payload=b""):
    return struct.pack("<BH", kind, len(payload)) + payload


def file_header(version=52, *, extended=True, main=1):
    if version <= 3:
        return record(0, struct.pack("<H4B", 4, 15, 50, 2, 2) + TABLE)
    if not extended:
        return record(0, struct.pack("<H3B", 4, 15, 50, 2))
    return record(0, struct.pack("<3H3B", 4, main, 100, 15, 50, 2))


def text(raw=b"Body"):
    nibbles = [nibble for value in raw for nibble in (15, value & 15, value >> 4)] + [0, 15, 1, 0]
    if len(nibbles) % 2:
        nibbles.append(0)
    return record(2, bytes(nibbles[i] | nibbles[i+1] << 4 for i in range(0, len(nibbles), 2)))


def sample(version=52, text_version=1, *, extended=True):
    lead = admin(version, text_version) + file_header(version, extended=extended)
    if version > 3:
        lead += record(5, b"\x02" + TABLE)
    # Context 0 is a genuine contents alias, context 1 addresses the text.
    ctx_offset = len(lead) + 3 + 2 + 6 + 3 + 2
    lead += record(1, b"\x02\0\xff\xff\xff" + ctx_offset.to_bytes(3, "little"))
    lead += record(4, b"\0\0")
    kw = struct.pack("<HH", 0, 0) + (b"\0" if version <= 4 else b"\0\0")
    return lead + text() + record(3, kw)


@pytest.mark.parametrize("version,text_version,extended", [(2, 1, True), (4, 1, False),
    (4, 1, True), (4, 2, False), (4, 2, True), (5, 1, True), (51, 1, True), (52, 3, True)])
def test_complete_header_variants_keep_stored_dimensions_and_contents(version, text_version, extended):
    document = ThelpHelpReader().read_bytes(sample(version, text_version, extended=extended))
    meta = document.metadata
    assert (meta["height"], meta["width"], meta["left_margin"]) == (15, 50, 2)
    assert meta["help_contents_topic_id"] == (100 if version == 2 else None if not extended else 1)
    # Sequential formats project the source return to a flowing space;
    # the legacy positioned formats keep the fixed source row.
    assert document.topics[0].raw_lines[0] == (b"Body " if version >= 5 else b"Body")
    if version > 3 and extended:
        assert document.topics[0].alias_contexts == [0]


@pytest.mark.parametrize("cut", [0, 1, 3, 12, 13, 14, 18, 24, 25, 26, 27, 28])
def test_incomplete_administrative_fields_fail_with_a_format_diagnostic(cut):
    with pytest.raises(ValueError, match="THELP|Borland"):
        ThelpHelpReader().read_bytes(admin()[:cut])


def test_missing_file_header_is_not_a_successful_empty_help():
    with pytest.raises(ValueError, match="file header"):
        ThelpBinaryParser(admin()).parse()


def test_magic_in_record_payload_does_not_replace_the_administrative_signature():
    data = admin(signature=b"Not the signature") + record(0, THELP_SIG + bytes(20))
    with pytest.raises(ValueError, match="administrative signature"):
        ThelpHelpReader().read_bytes(data)


@pytest.mark.parametrize("version", [0, 6, 50, 53, 255])
def test_unverified_format_versions_are_not_assumed_to_have_a_known_layout(version):
    with pytest.raises(ValueError, match="format version"):
        ThelpBinaryParser(admin(version) + file_header()).parse()


@pytest.mark.parametrize("tail", [b"\2", b"\2\1", b"\2\xff\xffText", b"\7\0\0", b"garbage", b" \0"])
def test_partial_records_and_unknown_nonpadding_tails_fail_instead_of_returning_partial_help(tail):
    with pytest.raises(ValueError, match="THELP record"):
        ThelpHelpReader().read_bytes(sample() + tail)


@pytest.mark.parametrize("tail", [b" ", b"  ", b" " * 100])
def test_only_verified_complete_space_padding_is_accepted_after_the_stream(tail):
    data = sample()
    document = ThelpHelpReader().read_bytes(data + tail)
    assert document.topics == ThelpHelpReader().read_bytes(data).topics
    assert document.metadata["trailing_padding"] == {"offset": len(data), "length": len(tail), "byte": 32}


@pytest.mark.parametrize("version,kind,payload", [
    (2, 0, bytes(19)), (4, 0, bytes(4)), (4, 0, bytes(8)), (52, 0, bytes(8)),
    (52, 5, b"\2" + bytes(13)), (52, 1, b"\2\0" + bytes(3)),
    (52, 4, b"\1\0\3AB"), (52, 6, b"\xff\xff\3ABC"),
])
def test_declared_fields_cannot_use_bytes_or_nuls_in_a_following_complete_record(version, kind, payload):
    data = admin(version) + record(kind, payload) + file_header(version)
    with pytest.raises(ValueError, match="THELP"):
        ThelpBinaryParser(data).parse()


@pytest.mark.parametrize("version,payload", [(4, b"\0\0\0\0\1" + bytes(8)),
                                           (52, b"\0\0\0\0\2\0\1\0")])
def test_keyword_counts_must_fit_their_own_record(version, payload):
    data = admin(version) + file_header(version) + record(5, b"\2" + TABLE) + text()
    data += record(3, payload) + record(4, bytes(20))
    with pytest.raises(ValueError, match="THELP record 3"):
        ThelpBinaryParser(data).parse()


@pytest.mark.parametrize("payload", [b"\x0f", b"\x0e", b"\xfe", b"\xfe\xaf"])
def test_incomplete_nibble_operands_cannot_consume_the_next_record_header(payload):
    data = admin() + file_header() + record(5, b"\2" + TABLE) + record(2, payload)
    data += record(3, bytes(10))
    with pytest.raises(ValueError, match="THELP record 2"):
        ThelpBinaryParser(data).parse()


@pytest.mark.parametrize("version,comp_type", [(2, 0), (2, 1), (52, 0), (52, 255)])
def test_unknown_compression_does_not_silently_use_the_nibble_decoder(version, comp_type):
    data = admin(version) + file_header(version)
    if version <= 3:
        data = data[:-15] + bytes([comp_type]) + TABLE
    else:
        data += record(5, bytes([comp_type]) + TABLE)
    with pytest.raises(ValueError, match="compression type"):
        ThelpBinaryParser(data).parse()


def test_index_prefix_cannot_reuse_bytes_outside_the_previous_token():
    data = admin() + file_header() + record(4, b"\1\0\x20\1\0")
    with pytest.raises(ValueError, match="index prefix"):
        ThelpBinaryParser(data).parse()


@pytest.mark.parametrize("offset", [65535, 0xFFFFFD, 0xFFFFFF - 3])
def test_context_addresses_cannot_point_beyond_eof_or_be_unverified_negative_sentinels(offset):
    data = admin() + file_header() + record(1, b"\1\0" + offset.to_bytes(3, "little"))
    with pytest.raises(ValueError, match="context 0.*outside the file"):
        ThelpBinaryParser(data).parse()


def test_cut_at_a_complete_record_boundary_still_rejects_declared_missing_text():
    data = sample()
    pos = len(admin()) + len(file_header()) + len(record(5, b"\2" + TABLE)) + 11 + 5
    with pytest.raises(ValueError, match="context 1.*outside the file"):
        ThelpBinaryParser(data[:pos]).parse()


@pytest.mark.parametrize("length", [0, 2, 4, 255])
def test_index_tag_declared_length_matches_its_bounded_nul_string(length):
    data = admin() + file_header() + record(6, b"\xff\xff" + bytes([length]) + b"Tag\0")
    with pytest.raises(ValueError, match="index tag length"):
        ThelpBinaryParser(data).parse()


def test_header_extensions_aliases_and_index_tag_order_stay_intact():
    tag = b"\xff\xff\3Tag\0\0\0\1A\0\0\0\1B\0"
    parser = ThelpBinaryParser(sample() + record(6, tag))
    meta, _screens, _index, tags = parser.parse()
    assert tags == [(65535, "Tag"), (0, "A"), (0, "B")]
    assert meta["description"] == "Tag"
    assert meta["help_contents_aliases"] == [0]


def test_real_turbo_c_20_dimensions_contents_and_genuine_alias_are_read_from_the_long_header():
    document = ThelpHelpReader().read_path(Path("data/sources/Borland Turbo C 2.0/TCHELP.TCH"))
    meta = document.metadata
    assert (meta["height"], meta["width"], meta["left_margin"], meta["help_contents_topic_id"]) == (15, 50, 2, 100)
    assert len(document.topics) == 1051
    topic = next(topic for topic in document.topics if topic.context_id == 100)
    assert topic.alias_contexts == [0]


@pytest.mark.parametrize("damage", ["record_extent", "context_count", "text_operand", "last_high_operand", "nested_repeat", "table_zero", "tag_nul"])
def test_failed_thelp_server_build_keeps_publication_and_retry_works(tmp_path, damage):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "Borland Turbo C/SAMPLE.TCH"
    source.parent.mkdir(parents=True)
    data = sample()
    source.write_bytes(data)
    build_help_groups(["borland"], sources, helps)
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    match damage:
        case "record_extent":
            broken = data[:-1]
        case "context_count":
            changed = bytearray(data)
            pos = len(admin()) + len(file_header()) + len(record(5, b"\2" + TABLE))
            struct.pack_into("<H", changed, pos + 3, 100)
            broken = bytes(changed)
        case "text_operand" | "last_high_operand" | "nested_repeat" | "table_zero":
            payload = {"text_operand": b"\x0f", "last_high_operand": b"\xf1",
                       "nested_repeat": b"\x0e\x0e", "table_zero": b"\x21"}[damage]
            table = b"X" + TABLE[1:] if damage == "table_zero" else TABLE
            broken = admin() + file_header() + record(5, b"\2" + table) + record(2, payload)
            broken += record(3, bytes(6))
        case _:
            broken = data + record(6, b"\xff\xff\3Tag")
    source.write_bytes(broken)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["borland"], sources, helps)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    source.write_bytes(data)
    result = build_help_groups(["borland"], sources, helps)
    backup = Path(result["backup"])
    assert published == {path.relative_to(backup): path.read_bytes() for path in backup.rglob("*") if path.is_file()}


def test_correct_stored_geometry_and_contents_reach_the_bundle(tmp_path):
    source = tmp_path / "sources/Borland Turbo C/TCHELP.TCH"
    source.parent.mkdir(parents=True)
    original = Path("data/sources/Borland Turbo C 2.0/TCHELP.TCH").read_bytes()
    source.write_bytes(original)
    result = export_bundle_tree(tmp_path / "sources", tmp_path / "helps", source_paths=[source], layout="helps")
    payload = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    assert payload["metadata"]["display"] == {"cols": 50, "rows": 15}
    assert payload["metadata"]["help_contents_topic_id"] == 100
    assert payload["topics"]["100"]["aliases"]["ids"] == [0]
    assert source.read_bytes() == original


def test_complete_thelp_corpus_preserves_native_records_targets_and_corrected_models():
    source_hashes, models = {}, {}
    topics = positioned = sequential = indexes = 0
    roots = Path("data/sources")
    for source in sorted(roots.rglob("*")):
        if not source.is_file():
            continue
        with source.open("rb") as stream:
            prefix = stream.read(4096)
            if not is_thelp_binary(prefix):
                continue
            data = prefix + stream.read()
        name = source.relative_to(roots).as_posix()
        document = ThelpHelpReader(source_name=source.name).read_bytes(data)
        source_hashes[name] = hashlib.sha256(data).hexdigest()
        models[name] = hashlib.sha256(json.dumps(document.to_dict(), ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        topics += len(document.topics)
        indexes += len(document.index_entries)
        positioned += sum(len(t.positional_keywords) for t in document.topics)
        sequential += sum(len(t.sequential_keywords) for t in document.topics)
    assert (len(models), topics, indexes, positioned, sequential) == (66, 93_032, 85_484, 41_537, 369_218)
    for values, expected in ((source_hashes, "a954f9228d530acfae475c91590247e4554c818a3873e26843aa578aaab0a0b0"),
                             (models, "b6b98d250813484b76e3a7bf311e5567b6802c59baa400ece8f4cb00e729942e")):
        assert hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == expected
