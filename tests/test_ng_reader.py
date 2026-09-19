from pathlib import Path
import re

from thelpviewer.converter.readers.ng import NG_HEADER_SIZE, NGReader, _decrypt


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
    source_paths = sorted((Path("sources") / "Norton Guides").glob("*.NG"))
    assert len(source_paths) == 58

    total_topics = 0
    for source_path in source_paths:
        reader = NGReader(source_path)
        document = reader.read()
        physical_offsets = _physical_record_offsets(reader.data)
        topic_ids = {topic.context_id for topic in document.topics}

        assert [topic.context_id for topic in document.topics] == physical_offsets
        assert len(document.topics) == len(physical_offsets)
        assert sum(
            1
            for offset in physical_offsets
            if _decrypt(reader.data[offset:offset + 2]) == b"\x02\x00"
        ) == reader.menu_count

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


def test_ng_reader_keeps_compact_long_entry_targets():
    document = NGReader(Path("sources") / "Norton Guides" / "AREACODE.NG").read()
    topics = {topic.context_id: topic for topic in document.topics}

    assert topics[4276].names[0] == "Wyckoff, NJ"
    assert any("[link:topic=4276]" in line for line in topics[3402].uhf_content)


def test_ng_reader_uses_the_stored_menu_count_without_a_phantom_prompt():
    document = NGReader(Path("sources") / "Norton Guides" / "4DOS.NG").read()
    menu_topics = [topic for topic in document.topics if topic.context_id in (378, 486)]

    assert [topic.names[0] for topic in menu_topics] == ["4DOS", "Tables"]
    assert [keyword.target_context for keyword in menu_topics[0].positional_keywords] == [
        687,
        146336,
        253328,
    ]
