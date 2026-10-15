"""Paragraph offsets, scoped hotspots and explicit Sidekick Plus pages."""

import gzip
import json
from pathlib import Path
import re
import struct
import zlib

import pytest

from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.readers.sidekick_plus import SidekickPlusReader, is_sidekick_plus_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


SOURCE = Path("data/sources/Borland Sidekick Plus/SKPLUS.HLP")
SIGNATURE = b"\x00\x9bBorland Help\x00\x01"


def _screen(text, title=b"Title", references=()):
    return b"".join(bytes(ref) for ref in references) + b"\xff\xff\xff" + text + b"\x00" + title + b"\x00"


def _sample(groups=None):
    if groups is None:
        groups = [(7, {0: _screen(b"\x01First\r\x05Local\x01", references=[(1, 255, 1)]),
                       1: _screen(b"\x02Other\xff\xffcontinued\x01")}),
                  (0x107, {0: _screen(b"\x05Cross group\x01", references=[(1, 0, 1)])})]
    data = bytearray(SIGNATURE + bytes(1024))
    for number, (group, records) in enumerate(groups):
        data.extend(b"padding"[:(-len(data)) % 16].ljust((-len(data)) % 16, b"x"))
        base = len(data)
        struct.pack_into("<HH", data, 16 + number * 4, base // 16, group)
        data.extend(b"\xff" * 1536)
        for slot, record in records.items():
            if isinstance(record, int):
                data[base + slot * 6:base + (slot + 1) * 6] = bytes((0, 255, record, 255, 255, 255))
            else:
                offset = len(data) - base
                struct.pack_into("<BBHH", data, base + slot * 6, 25, 80, offset, len(record))
                data.extend(record)
    struct.pack_into("<HH", data, 16 + len(groups) * 4, 65535, 0)
    return bytes(data)


def test_detector_is_signature_based_not_filename_or_crc():
    data = _sample()
    assert is_sidekick_plus_binary(data)
    assert detect_format_handler("unknown.bin", data).name == "sidekick-plus"
    for tag in (0, 0x1234, 0xABCD, 0xFFFF):
        changed = tag.to_bytes(2, "little") + data[2:]
        assert detect_format_handler("different.bin", changed).name == "sidekick-plus"
        assert SidekickPlusReader().read_bytes(changed).metadata["sidekick_plus_version_tag"] == tag
    for other in (b"", b"Borland Help\x00", b"\x00\x9bSidekick Plus", data[:15],
                  b"\x00\x9bBorland Help\x00\x02", b"\x00\x00\x01\x0c\x02Help text #0\x00"):
        assert not is_sidekick_plus_binary(other)


def test_native_group_slot_ids_pages_and_scoped_hotspots():
    document = SidekickPlusReader(source_name="SKPLUS.HLP").read_bytes(_sample())
    first, other, continuation, cross = document.topics
    assert [topic.context_id for topic in document.topics] == [1792, 1793, 1 << 24, 67328]
    assert first.uhf_content == ["First", "[link:topic=1793]Local[/link]"]
    assert cross.uhf_content == ["[link:topic=1793]Cross group[/link]"]
    assert other.uhf_content == ["[b]Other[/b]"]
    assert continuation.uhf_content == ["continued"]
    assert other.next_context == continuation.context_id
    assert continuation.prev_context == other.context_id
    assert continuation.next_context is None and cross.prev_context is None
    assert document.contents[0].children[1].children[0].topic_id == 1 << 24
    assert document.metadata["sidekick_plus_groups"] == [7, 263]
    assert document.metadata["unresolved_contexts"] == {"links": []}


def test_source_page_numbers_select_their_own_hotspot_targets():
    screen = _screen(b"\x05First\x01\xff\xff\x05Second\x01", references=[(1, 255, 1), (2, 255, 0)])
    data = _sample([(2, {0: screen, 1: _screen(b"Destination")})])
    document = SidekickPlusReader().read_bytes(data)
    assert document.topics[0].uhf_content == ["[link:topic=513]First[/link]"]
    assert document.topics[1].uhf_content == ["[link:topic=512]Second[/link]"]


def test_empty_pages_spaces_oem_glyphs_and_literal_markup_are_preserved():
    data = _sample([(1, {0: _screen(b"\x03\xff\x11\xff\x18\xff\x00\xff\t\xff\n\xff\r\xff\x01\x01 [link:topic=9]  \xff\xff\xff\xffEnd")})])
    document = SidekickPlusReader().read_bytes(data)
    assert document.topics[0].uhf_content == ["[u]◄↑ ○◙♪☺[/u] [[link:topic=9]  "]
    assert document.topics[1].uhf_content == [""]
    assert document.topics[2].uhf_content == ["End"]
    assert document.topics[0].raw_lines[0].endswith(b" [link:topic=9]  ")
    assert b"\x00" not in document.topics[0].raw_lines[0]


def test_help_starts_each_native_row_with_the_normal_category():
    data = _sample([(1, {0: _screen(b"\x02bold\rstill\x03key\rmore\x01 \x05two\rlines\x01", references=[(1, 255, 0)])})])
    topic = SidekickPlusReader().read_bytes(data).topics[0]
    assert topic.uhf_content == ["[b]bold[/b]", "still[u]key[/u]", "more [link:topic=256]two[/link]", "lines"]


@pytest.mark.parametrize("selector", [1, 7, 255])
def test_every_nonzero_hotspot_selector_keeps_the_current_group(selector):
    data = _sample([(7, {0: _screen(b"\x05Here\x01", references=[(1, selector, 1)]),
                        1: _screen(b"Current")}), (263, {1: _screen(b"Not a directory ordinal")})])
    document = SidekickPlusReader().read_bytes(data)
    assert document.topics[0].uhf_content == ["[link:topic=1793]Here[/link]"]


def test_explicit_common_binding_is_shared_by_default_scope_and_redirects():
    data = _sample([(7, {0: _screen(b"\x05Default\x01", references=[(1, 0, 1)]), 2: 1}),
                    (263, {1: _screen(b"The runtime's common group")})])
    document = SidekickPlusReader(common_group=263).read_bytes(data)
    assert document.topics[0].uhf_content == ["[link:topic=67329]Default[/link]"]
    assert document.topics[1].alias_contexts == [1794]
    assert document.metadata["sidekick_plus_common_group"] == 263
    assert document.metadata["unresolved_contexts"]["links"] == []
    for invalid in (999, True, "263"):
        with pytest.raises(ValueError, match="common help group"):
            SidekickPlusReader(common_group=invalid).read_bytes(data)


def test_native_category_toggle_selected_category_and_unescaped_oem_glyphs():
    data = _sample([(7, {0: _screen(b"\x01normal\x06bold\x06normal\r\x03key\x06selected\x06key\r"
                                       b"\x05link\x06still\x01\r\x0f\t\n\x08", references=[(1, 255, 0)])})])
    topic = SidekickPlusReader().read_bytes(data).topics[0]
    assert topic.uhf_content == ["normal[b]bold[/b]normal", "[u]key[/u][r]selected[/r][u]key[/u]",
                                 "[link:topic=1792]linkstill[/link]", "☼○◙◘"]


def test_hotspot_at_end_of_native_string_does_not_require_an_extra_category_byte():
    data = _sample([(7, {0: _screen(b"\x05Label", references=[(1, 255, 0)])})])
    assert SidekickPlusReader().read_bytes(data).topics[0].uhf_content == ["[link:topic=1792]Label[/link]"]


def test_shared_source_record_is_a_real_alias_not_duplicated_text():
    data = bytearray(_sample([(65535, {0: _screen(b"Game"), 1: _screen(b"unused")})]))
    data[0x416:0x41C] = data[0x410:0x416]
    document = SidekickPlusReader().read_bytes(bytes(data))
    assert len(document.topics) == 1
    assert document.topics[0].context_id == 0xFFFF00
    assert document.topics[0].alias_contexts == [0xFFFF01]
    payload = HelpJsonRenderer(document).render_document()
    assert payload["topics"][str(0xFFFF00)]["aliases"]["ids"] == [0xFFFF01]


def test_missing_source_targets_and_dangling_redirects_are_not_guessed_or_deleted():
    data = _sample([(0x104, {0: _screen(b"\x05Missing\x01 \x05Runtime\x01", references=[(1, 255, 90), (1, 255, 146)]), 146: 129})])
    document = SidekickPlusReader().read_bytes(data)
    assert document.topics[0].uhf_content == ["[link:topic=66650]Missing[/link] [link:topic=66706]Runtime[/link]"]
    assert document.metadata["unresolved_contexts"]["links"] == [66650, 66706]
    assert document.metadata["sidekick_plus_redirects"] == [{"context_id": 66706, "target_context": 66689,
                                                            "descriptor": int.from_bytes(b"\x00\xff\x81\xff\xff\xff", "little")}]


def test_redirect_chains_resolve_without_new_text_and_cycles_fail():
    data = _sample([(7, {128: 129, 129: 130, 130: _screen(b"Real text")}), (263, {10: 128})])
    document = SidekickPlusReader().read_bytes(data)
    assert len(document.topics) == 1
    assert document.topics[0].context_id == 1922
    assert document.topics[0].alias_contexts == [1920, 1921, 67338]
    cyclic = _sample([(7, {0: 1, 1: 0, 2: _screen(b"Text")})])
    with pytest.raises(ValueError, match="Cyclic"):
        SidekickPlusReader().read_bytes(cyclic)


def test_native_unused_dimensions_take_precedence_over_redirect_offset_bytes():
    data = bytearray(_sample())
    data[0x410:0x416] = b"\xff\xff\x00\xff\x00\x00"
    document = SidekickPlusReader().read_bytes(bytes(data))
    assert all(topic.context_id != 1792 for topic in document.topics)
    assert document.metadata["sidekick_plus_redirects"] == []


@pytest.mark.parametrize("body,refs", [
    (b"\x05no entry\x01", []), (b"no hotspot", [(1, 255, 0)]),
    (b"\x05bad page\x01", [(2, 255, 0)]), (b"\x05zero page\x01", [(0, 255, 0)]),
    (b"truncated\xff", []), (b"\x00early end", []), (b"\xfe\x00\x12", []),
    (b"x" * 81, []), (b"\r" * 25, []),
])
def test_invalid_text_or_hotspot_metadata_fails_without_partial_output(body, refs):
    with pytest.raises(ValueError):
        SidekickPlusReader().read_bytes(_sample([(1, {0: _screen(body, references=refs)})]))


@pytest.mark.parametrize("offset,fmt,value", [
    (16, "<H", 0), (16, "<H", 65534), (18, "<H", 0x107),
    (20, "<H", 0x41), (0x410, "B", 26), (0x411, "B", 0),
    (0x412, "<H", 0), (0x414, "<H", 65535),
])
def test_invalid_group_and_context_directories_are_rejected(offset, fmt, value):
    data = bytearray(_sample())
    struct.pack_into(fmt, data, offset, value)
    with pytest.raises(ValueError):
        SidekickPlusReader().read_bytes(bytes(data))


def test_partial_record_overlap_is_not_a_native_alias():
    data = bytearray(_sample())
    struct.pack_into("<H", data, 0x418, 1537)
    with pytest.raises(ValueError):
        SidekickPlusReader().read_bytes(bytes(data))


def test_truncated_title_empty_directory_and_unknown_zero_height_layout_fail():
    for data in (_sample()[:-1], _sample([]), _sample()[:1024]):
        with pytest.raises(ValueError):
            SidekickPlusReader().read_bytes(data)
    data = bytearray(_sample())
    data[0x410] = 0
    with pytest.raises(ValueError, match="descriptor"):
        SidekickPlusReader().read_bytes(bytes(data))


def test_top_level_sentinel_is_required_not_inferred_from_zero_padding():
    data = bytearray(_sample())
    # Repeat valid entries to fill the directory: a duplicate group is invalid,
    # not an implicit end marker. The real terminator tests the paragraph word.
    struct.pack_into("<HH", data, 24, 0, 0)
    with pytest.raises(ValueError):
        SidekickPlusReader().read_bytes(bytes(data))


def test_corpus_topic_pages_targets_and_aliases_are_structural():
    if not SOURCE.exists():
        pytest.skip("Sidekick Plus original not available")
    data = SOURCE.read_bytes()
    assert zlib.crc32(data) == 0x418860F6
    document = load_document(SOURCE)
    assert document.format_name == "sidekick-plus"
    assert len(document.metadata["sidekick_plus_groups"]) == 18
    assert len(document.metadata["sidekick_plus_contexts"]) == 1086
    assert len(document.topics) == 1165
    assert sum(len(item["page_ids"]) - 1 for item in document.metadata["sidekick_plus_contexts"]) == 79
    assert sum(len(topic.alias_contexts) for topic in document.topics) == 4
    assert document.metadata["help_contents_topic_id"] == 768
    assert document.metadata["display_width"] == 80
    assert document.metadata["sidekick_plus_common_group"] == 3
    assert document.metadata["sidekick_plus_version_tag"] == 0x9B00
    assert len(document.metadata["sidekick_plus_redirects"]) == 3
    assert document.metadata["unresolved_contexts"]["links"] == [858, 5892, 8195, 8242, 66646, 70822]
    owners = {alias: topic.context_id for topic in document.topics for alias in topic.alias_contexts}
    assert {context: owners[context] for context in (66583, 66706, 66709)} == {66583: 896, 66706: 897, 66709: 898}
    rendered = HelpJsonRenderer(document).render_document()
    links = [int(target) for topic in rendered["topics"].values() for line in topic["content"]
             for target in re.findall(r"\[link:topic=(\d+)\]", line)]
    assert len(links) == 2051
    known = {topic.context_id for topic in document.topics} | {alias for topic in document.topics for alias in topic.alias_contexts}
    assert sum(target not in known for target in links) == 6
    vogon = next(topic for topic in document.topics if topic.context_id == 16776960)
    assert vogon.uhf_content[13] == "to the Galaxy and is used with the "
    first = next(topic for topic in document.topics if topic.context_id == 768)
    assert "[link:topic=899] Edit Clipboard       [/link]" in first.uhf_content[5]
    notepad_index = next(topic for topic in document.topics if topic.context_id == 66561)
    descriptor = next(item for item in document.metadata["sidekick_plus_contexts"] if item["context_id"] == 66561)
    assert len(descriptor["page_ids"]) == 9
    assert notepad_index.next_context == descriptor["page_ids"][1]


def test_bundle_export_adds_supported_sidekick_plus_in_existing_product_layout(tmp_path):
    if not SOURCE.exists():
        pytest.skip("Sidekick Plus original not available")
    output = tmp_path / "helps"
    results = export_bundle_tree(Path("data/sources"), output, layout="helps", source_paths=[SOURCE])
    assert len(results) == 1 and results[0].format_name == "sidekick-plus"
    assert results[0].topic_count == 1165
    path = output / "Borland Sidekick Plus/skplus.json.gz"
    bundle = json.loads(gzip.decompress(path.read_bytes()))
    assert bundle["metadata"]["source"]["format"] == "sidekick-plus"
    assert bundle["metadata"]["product"] == "sk"
    assert bundle["metadata"]["display"]["cols"] == 80
    assert bundle["topics"]["768"]["title"] == "The Services Menu"
