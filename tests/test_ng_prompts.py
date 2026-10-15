"""Native NG menu addressing and literal OEM navigation captions."""

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.readers.ng import NGReader, _decrypt
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_ng_validation import field, header, long, menu, record


def test_menu_uses_descriptor_offsets_not_sequential_string_order():
    # Four source slots: Second, First, Second again, and the title itself.
    # The descriptor table can be separated from the target DWORDs by padding.
    strings = b"Title\0First\0Second\0\0"
    table_offset = 4 * 4 + 3
    text_start = table_offset + 5 * 8
    offsets = [text_start + 12, text_start + 6, text_start + 12,
               text_start, text_start + len(strings) - 1]
    descriptors = b"".join(struct.pack("<4H", value, 0, 0, 0) for value in offsets)
    payload = struct.pack("<4I", 378, 378, 378, 378) + b"gap" + descriptors + strings
    document = NGReader().read_bytes(header(1) + record(2, payload, 5, flag=table_offset))
    topic = document.topics[0]
    assert topic.names == ["Title"]
    assert topic.raw_lines == [b"Second", b"First", b"Second", b"Title"]
    assert [kw.target_context for kw in topic.positional_keywords] == [378] * 4
    assert topic.uhf_content == [f"[link:topic=378]{label}[/link]"
                                 for label in ("Second", "First", "Second", "Title")]


@pytest.mark.parametrize("offset", [0, 4, 19, 65535])
def test_menu_descriptor_text_must_stay_after_the_table_and_inside_the_record(offset):
    data = header(1) + menu([(b"Prompt", 378)])
    with pytest.raises(ValueError, match="Norton Guide MENU"):
        NGReader().read_bytes(field(data, 378, 30, "H", offset))


def test_menu_descriptor_location_cannot_overlap_targets_or_leave_the_record():
    data = header(1) + menu([(b"Prompt", 378)])
    for offset in (0, 3, 65535):
        with pytest.raises(ValueError, match="Norton Guide MENU"):
            NGReader().read_bytes(field(data, 378, 6, "H", offset))


def test_menu_requires_the_pointed_empty_terminator_not_arbitrary_trailing_bytes():
    data = header(1) + menu([(b"Prompt", 378)])
    prompt_offset = int.from_bytes(_decrypt(data[408:410]), "little")
    with pytest.raises(ValueError, match="MENU terminator"):
        NGReader().read_bytes(field(data, 378, 38, "H", prompt_offset))
    damaged = data[:-1] + _decrypt(b"x")
    with pytest.raises(ValueError, match="MENU prompt"):
        NGReader().read_bytes(damaged)


def test_menu_preserves_blank_symbol_only_padded_and_duplicate_slots():
    labels = [b"", b"---", b"\xc4\xc4", b"  Same\xff\xff  ", b"Same"]
    data = header(1) + menu([(label, 378) for label in labels])
    topic = NGReader().read_bytes(data).topics[0]
    assert topic.raw_lines == labels
    assert len(topic.positional_keywords) == len(labels)
    assert [(kw.line, kw.first_column, kw.last_column) for kw in topic.positional_keywords] == [
        (i + 1, 1, len(label)) for i, label in enumerate(labels)]
    assert topic.uhf_content == ["", "[link:topic=378]---[/link]",
                                 "[link:topic=378]──[/link]",
                                 "[link:topic=378]  Same\u00a0\u00a0  [/link]",
                                 "[link:topic=378]Same[/link]"]
    assert not any("Context" in line for line in topic.uhf_content)


@pytest.mark.parametrize("label", [b"^bINTERRUPT SERVICES^b", b"The ^BVariables^N Window",
                                  b"^^", b"A\xff\xffB", b" A  B ", b"\x10\x11"])
def test_navigation_captions_use_literal_cells_not_body_escapes(label):
    visible = "".join(NGReader()._glyphs[value] for value in label)
    topic = NGReader().read_bytes(header(1) + menu([(label, 378)])).topics[0]
    assert topic.raw_lines == [label]
    assert topic.uhf_content == [f"[link:topic=378]{visible}[/link]"]
    topic = NGReader().read_bytes(header() + long([b"Body"], [(label, 378)])).topics[0]
    assert topic.raw_lines[-1] == b"See also: " + label + b"  "
    assert topic.uhf_content[-1] == f"See also: [link:topic=378]{visible}[/link]  "
    kw = topic.positional_keywords[0]
    assert (kw.first_column, kw.last_column) == (11, 10 + len(label))


def test_see_also_keeps_empty_targets_null_target_captions_and_source_order():
    refs = [(b"", 378), (b"No target", 0), (b" Again ", 378), (b"None", 0xFFFFFFFF)]
    topic = NGReader().read_bytes(header() + long([b"Body"], refs)).topics[0]
    assert topic.raw_lines[-1] == b"See also:   No target   Again   None  "
    assert topic.uhf_content[-1] == "See also:   No target  [link:topic=378] Again [/link]  None  "
    assert [(kw.target_context, kw.first_column, kw.last_column) for kw in topic.positional_keywords] == [
        (378, 11, 10), (378, 24, 30)]


def test_real_ff_captions_and_literal_see_also_escapes():
    document = NGReader().read_path(Path("data/sources/Norton Guides/BEATLES.NG"))
    topics = {topic.context_id: topic for topic in document.topics}
    assert topics[378].raw_lines[0] == b"The\xfflist\xffof\xffalbums"
    assert "The\u00a0list\u00a0of\u00a0albums" in topics[378].uhf_content[0]
    assert topics[747].raw_lines[1:4] == [b"Epigraph", b"Epigraph\xff", b"Epigraph\xff\xff"]
    document = NGReader().read_path(Path("data/sources/Norton Guides/DPMI.NG"))
    topic = next(topic for topic in document.topics if topic.context_id == 59273)
    assert "^bINTERRUPT SERVICES^b" in topic.uhf_content[-1]
    document = NGReader().read_path(Path("data/sources/Norton Guides/GT_LIBNG.NG"))
    topic = next(topic for topic in document.topics if topic.context_id == 1511)
    assert topic.uhf_content[-1] == "See also: GT_S2ARR()  "
    assert topic.positional_keywords == []


def test_preserved_caption_bytes_and_links_reach_the_published_bundle(tmp_path):
    source = tmp_path / "sources/Norton Guides/SAMPLE.NG"
    source.parent.mkdir(parents=True)
    original = header(1) + menu([(b"  ^B[Caption]\xff  ", 378)])
    source.write_bytes(original)
    result = export_bundle_tree(tmp_path / "sources", tmp_path / "helps", source_paths=[source], layout="helps")
    bundle = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    assert bundle["topics"]["378"]["content"] == ["[link:topic=378]  ^B[[Caption]\u00a0  [/link]"]
    assert source.read_bytes() == original


def test_all_original_caption_cells_and_descriptor_addresses_match_the_native_baseline():
    digest = hashlib.sha256()
    titles = prompts = related = cells_total = menus = 0
    for source in sorted(Path("data/sources/Norton Guides").glob("*.NG")):
        data = source.read_bytes()
        document = NGReader().read_bytes(data)
        topics = {topic.context_id: topic for topic in document.topics}
        offset = 378
        while offset < len(data):
            head = _decrypt(data[offset:offset + 26])
            kind, size, count = struct.unpack_from("<HHH", head)
            entry = _decrypt(data[offset:offset + 26 + size])
            labels = []
            if kind == 2:
                table = 26 + int.from_bytes(entry[6:8], "little")
                pos = table + 8 * count
                labels.append(("title", entry[pos:entry.index(0, pos)]))
                titles += 1
                menus += 1
                for index in range(count):
                    pos = 26 + int.from_bytes(entry[table + 8*index:table + 8*index + 2], "little")
                    raw = entry[pos:entry.index(0, pos)]
                    if index == count - 1:
                        assert raw == b""
                    else:
                        assert topics[offset].raw_lines[index] == raw
                        labels.append(("menu", raw))
                        prompts += 1
            elif kind == 1 and int.from_bytes(entry[6:8], "little"):
                pos = 26
                for _ in range(count):
                    pos = entry.index(0, pos) + 1
                sa_count = int.from_bytes(entry[pos:pos + 2], "little")
                pos += 2 + 4 * sa_count
                for _ in range(sa_count):
                    end = entry.index(0, pos)
                    labels.append(("see-also", entry[pos:end]))
                    pos = end + 1
                    related += 1
                if sa_count:
                    assert topics[offset].raw_lines[-1] == b"See also: " + b"".join(
                        raw + b"  " for _kind, raw in labels)
            for index, (label_kind, raw) in enumerate(labels):
                # Native plain loop writes every byte unchanged in these
                # captions; none contain terminal cursor-movement controls.
                assert all(value >= 16 for value in raw)
                item = (source.name, offset, label_kind, index, raw.hex())
                digest.update(json.dumps(item, separators=(",", ":")).encode() + b"\n")
                cells_total += len(raw)
            offset += len(entry)
    assert (menus, titles, prompts, related, cells_total) == (120, 120, 553, 13_878, 111_967)
    assert digest.hexdigest() == "b49a803f880c9bc5e891c4899cb4fdb9b12fa8666ba67616a1afffcf5fb8e984"
