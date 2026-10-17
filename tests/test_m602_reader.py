from functools import lru_cache
from pathlib import Path
import re

from thelpviewer.server.converter.base import TopicRecord
from thelpviewer.server.converter.readers.m602 import (
    M602BinaryParser,
    M602Reader,
    build_m602_binary_target_context_map,
    collect_m602_link_occurrences,
)
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


M602_PATH = Path("var/sources") / "Software 602" / "M602_200.HLP"


@lru_cache(maxsize=1)
def _m602_document():
    return M602Reader(str(M602_PATH), source_path=M602_PATH).read_bytes(M602_PATH.read_bytes())


def test_m602_binary_tail_resolves_all_raw_link_targets():
    data = M602_PATH.read_bytes()
    parser = M602BinaryParser(data)
    parsed_topics = parser.parse()
    exact_targets = build_m602_binary_target_context_map(
        data,
        parsed_topics,
        tail_offset=parser.binary_index_offset,
    )
    raw_topics = [
        TopicRecord(
            context_id=topic["context_id"],
            raw_lines=list(topic["raw_lines"]),
            positional_keywords=list(topic["positional_keywords"]),
            index_terms=[topic["title"]],
        )
        for topic in parsed_topics
    ]
    raw_occurrences = collect_m602_link_occurrences(raw_topics, "kamenicky")
    raw_targets = {raw_target for _source, raw_target, _label in raw_occurrences}

    assert len(parsed_topics) == 201
    assert parser.binary_index_entry_count == 201
    assert len(raw_occurrences) == 406
    assert len(raw_targets) == 119
    assert raw_targets <= set(exact_targets)


def test_m602_output_keeps_links_and_dos_glyphs():
    document = _m602_document()
    topic_ids = {topic.context_id for topic in document.topics}
    all_lines = [line for topic in document.topics for line in topic.uhf_content]
    all_text = "\n".join(all_lines)
    linked_targets = {
        int(match.group(1))
        for match in re.finditer(r"\[link:topic=(\d+)\]", all_text)
    }

    assert len(document.topics) == 201
    assert document.metadata["link_target_resolution"] == "binary_tail_exact"
    assert not any(topic.uhf_content and topic.uhf_content[-1] == "[rule]" for topic in document.topics)
    assert linked_targets <= topic_ids
    assert sum(line.count("[link:topic=") for line in all_lines) == 406

    topic_2 = document.topics[1].uhf_content
    assert topic_2[0] == " Základní obrazovka ▄"
    assert "Základní obrazovku tvoří dva [link:topic=14]panely[/link], které poskytují informace o " in topic_2
    assert any("Pod panely je umístěn [link:topic=20]povelový řádek[/link] a" in row for row in topic_2)
    assert "[[↕]" in all_text
    assert "▲" in all_text
    assert "▼" in all_text


def test_m602_json_links_target_existing_topics():
    payload = HelpJsonRenderer(_m602_document(), display_encoding="kamenicky").render_document()
    topics = payload["topics"]
    topic_ids = {int(topic_id) for topic_id in topics}
    all_text = "\n".join(
        line
        for topic in topics.values()
        for line in topic.get("content", [])
    )
    linked_targets = {
        int(match.group(1))
        for match in re.finditer(r"\[link:topic=(\d+)\]", all_text)
    }

    assert len(topics) == 201
    assert linked_targets <= topic_ids


def test_m602_default_ui_matches_thelp_palette():
    for asset_path in (
        Path("thelpviewer") / "server" / "converter" / "assets" / "tv-bundle-app.js",
        Path("www") / "assets" / "tv-bundle-app.js",
    ):
        text = asset_path.read_text(encoding="utf-8")
        assert _source_theme(text, "m602") == _source_theme(text, "thelp")


def _source_theme(text: str, name: str) -> dict[str, str]:
    match = re.search(rf"    {re.escape(name)}: \{{\n(?P<body>.*?)\n    \}},", text, re.DOTALL)
    assert match is not None
    theme: dict[str, str] = {}
    for key, value in re.findall(r'        ([a-z_]+): "([^"]+)",', match.group("body")):
        theme[key] = value
    return theme
