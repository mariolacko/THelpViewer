import hashlib
import json
from pathlib import Path
import re

from thelpviewer.server.converter.readers.ng import NG_HEADER_SIZE, NGReader, _decode_text, _decrypt


_LOCAL_LINK_RE = re.compile(r"\[link:topic=(-?\d+)\b")
_NAV_ATTRIBUTES = ("up_context", "down_context", "prev_context", "next_context")


def _physical_record_offsets(data: bytes) -> list[int]:
    offsets: list[int] = []
    offset = NG_HEADER_SIZE
    while offset < len(data):
        assert offset + 26 <= len(data)
        header = _decrypt(data[offset: offset + 26])
        assert int.from_bytes(header[0:2], "little") in (0, 1, 2)
        payload_size = int.from_bytes(header[2:4], "little")
        offsets.append(offset)
        offset += 26 + payload_size
    assert offset == len(data)
    return offsets


def test_ng_reader_preserves_every_record_and_link_in_the_corpus():
    source_paths = sorted((Path("var/sources") / "Norton Guides").glob("*.NG"))
    assert len(source_paths) == 58

    total_topics = 0
    source_hashes, models = {}, {}
    for source_path in source_paths:
        data = source_path.read_bytes()
        document = NGReader(source_name=source_path.name).read_bytes(data)
        source_hashes[source_path.name] = hashlib.sha256(data).hexdigest()
        model = json.dumps(document.to_dict(), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode()
        models[source_path.name] = hashlib.sha256(model).hexdigest()
        physical_offsets = _physical_record_offsets(data)
        topic_ids = {topic.context_id for topic in document.topics}

        assert [topic.context_id for topic in document.topics] == physical_offsets
        assert len(document.topics) == len(physical_offsets)
        assert sum(
            1
            for offset in physical_offsets
            if _decrypt(data[offset:offset + 2]) == b"\x02\x00"
        ) == int.from_bytes(data[6:8], "little")

        for topic in document.topics:
            assert all(
                keyword.target_context in topic_ids
                for keyword in topic.positional_keywords
            )
            assert all(
                getattr(topic, attribute) is None
                or getattr(topic, attribute) in topic_ids
                for attribute in _NAV_ATTRIBUTES
            )
            assert all(
                int(match.group(1)) in topic_ids
                for line in topic.uhf_content
                for match in _LOCAL_LINK_RE.finditer(line)
            )

        total_topics += len(document.topics)

    assert total_topics == 21_309
    # Source bytes stay unchanged. Models include the native text/category
    # and whole-SHORT-row corrections; the independent cell hash is below.
    for values, expected in (
        (source_hashes, "6d37d26a096bc96eec58ac9e4363429a1a63afa10d6250eb8157391990b85a1b"),
        (models, "ff848d86fce1c3eab9a101d820b42135ee626b9c240241aeffca21f7564e3e10"),
    ):
        assert hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == expected


def test_ng_reader_keeps_compact_long_entry_targets():
    document = NGReader().read_path(Path("var/sources") / "Norton Guides" / "AREACODE.NG")
    topics = {topic.context_id: topic for topic in document.topics}

    assert topics[4276].names[0] == "Wyckoff, NJ 201"
    assert any("[link:topic=4276]" in line for line in topics[3402].uhf_content)


def test_ng_reader_uses_the_stored_menu_count_without_a_phantom_prompt():
    document = NGReader().read_path(Path("var/sources") / "Norton Guides" / "4DOS.NG")
    menu_topics = [topic for topic in document.topics if topic.context_id in (378, 486)]

    assert [topic.names[0] for topic in menu_topics] == ["4DOS", "Tables"]
    assert [keyword.target_context for keyword in menu_topics[0].positional_keywords] == [
        687,
        146336,
        253328,
    ]


def test_all_original_ng_body_cells_match_the_native_instruction_loop_baseline():
    digest = hashlib.sha256()
    rows = cells_total = overflow = 0
    for source in sorted((Path("var/sources") / "Norton Guides").glob("*.NG")):
        data = source.read_bytes()
        for offset in _physical_record_offsets(data):
            head = _decrypt(data[offset:offset + 26])
            kind = int.from_bytes(head[:2], "little")
            size, count = int.from_bytes(head[2:4], "little"), int.from_bytes(head[4:6], "little")
            entry = _decrypt(data[offset:offset + 26 + size])
            positions = []
            if kind == 0:
                positions = [26 + int.from_bytes(entry[26 + 6*i:28 + 6*i], "little") for i in range(count)]
            elif kind == 1:
                position = 26
                for _ in range(count):
                    positions.append(position)
                    position = entry.index(0, position) + 1
            for line, position in enumerate(positions):
                raw = entry[position:entry.index(0, position)]
                cells, attributes = _decode_text(raw)
                # Original video WORDs at 78 columns, plus original instruction
                # loop capture before its video sink for the longer logical tails.
                item = (source.name, offset, line, cells.hex(), attributes.hex())
                digest.update(json.dumps(item, separators=(",", ":")).encode())
                digest.update(b"\n")
                rows += 1
                cells_total += len(cells)
                overflow += len(cells) > 78
    assert (rows, cells_total, overflow) == (509_785, 17_967_220, 888)
    assert digest.hexdigest() == "63124b7e9e4cdf9fdfe70a55ee05cedc30c4fd449912bec7ff42ff05bd31f3a8"
