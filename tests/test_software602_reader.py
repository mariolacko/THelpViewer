from functools import lru_cache
from pathlib import Path

from thelpviewer.converter.readers.software602 import Text602Reader
from thelpviewer.converter.writers.json import HelpJsonRenderer


@lru_cache(maxsize=1)
def _c602_document():
    path = Path("sources") / "Software 602" / "C602.HLP"
    return Text602Reader(str(path), path).read_bytes(path.read_bytes())


@lru_cache(maxsize=1)
def _t602_document():
    path = Path("sources") / "Software 602" / "T602_310.HLP"
    return Text602Reader(str(path), path).read_bytes(path.read_bytes())


def test_text602_and_calc602_expose_green_t602_ui_theme():
    for document in (_t602_document(), _c602_document()):
        assert document.metadata["ui"]["window"] == "#005454"
        assert document.metadata["ui"]["text"] == "#a8fcfc"
        assert document.metadata["ui"]["link"] == "#a8a800"
        assert document.metadata["ui"]["frame"] == "#a8a800"
        assert document.metadata["ui"]["icon"] == "#005454"
        assert document.metadata["ui"]["arrow_bg"] == "#a8a800"
        assert document.metadata["ui"]["thumb_bg"] == "#a8a800"

        payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()
        assert payload["metadata"]["ui"]["window"] == "#005454"
        assert payload["metadata"]["ui"]["text"] == "#a8fcfc"
        assert payload["metadata"]["ui"]["link"] == "#a8a800"
        assert payload["metadata"]["ui"]["frame"] == "#a8a800"
        assert payload["metadata"]["ui"]["icon"] == "#005454"


def test_text602_and_calc602_keep_navigation_links_resolved():
    t602_links = sum(line.count("[link:topic=") for topic in _t602_document().topics for line in topic.uhf_content)
    c602_links = sum(line.count("[link:topic=") for topic in _c602_document().topics for line in topic.uhf_content)

    assert t602_links >= 780
    assert c602_links >= 1000


def test_text602_and_calc602_drop_trailing_topic_rules():
    for document in (_t602_document(), _c602_document()):
        assert not any(topic.uhf_content and topic.uhf_content[-1] == "[rule]" for topic in document.topics)


def test_c602_context_menu_links_are_resolved_without_linking_ascii_art():
    doc = _c602_document()

    graph_topic = doc.topics[49]
    assert graph_topic.context_id == 50
    assert any("┌─────┬─────┬───────── názvy kategorií" in line for line in graph_topic.uhf_content)
    assert not any("[link:topic=54]┌" in line for line in graph_topic.uhf_content)
    assert not any("[link:topic=56](legenda)" in line for line in graph_topic.uhf_content)
    assert not any("[link:topic=56]4 α" in line for line in graph_topic.uhf_content)
    assert "■ [link:topic=51]Výběr 2D grafu[/link]" in graph_topic.uhf_content
    assert "  [link:topic=52]Výběr 3D grafu[/link]" in graph_topic.uhf_content
    assert "■ [link:topic=53]Nadpis grafu[/link]" in graph_topic.uhf_content

    graph_3d_topic = doc.topics[51]
    assert graph_3d_topic.context_id == 52
    assert "■ [link:topic=51]Výběr 2D grafu[/link]" in graph_3d_topic.uhf_content


def test_c602_uses_software602_character_overrides():
    doc = _c602_document()

    contents = doc.topics[128]
    assert contents.context_id == 129
    assert contents.uhf_content[0] == "■ Úvod"

    finance = doc.topics[100]
    assert " │ FV(Úrok,PočetObdobí,Splátka,<SoučasnáHodnota>,<Typ>)                    │" in finance.uhf_content
    assert "Úrok - úroková míra (rate - RATE)." in finance.uhf_content

    all_text = "\n".join(line for topic in doc.topics for line in topic.uhf_content)
    for bad_text in ("⌡vod", "⌡rok", "zvláš╘", "pamě╘", "TERMINßL", "KLADN≈", "ZßPORN≈", "bu─"):
        assert bad_text not in all_text
