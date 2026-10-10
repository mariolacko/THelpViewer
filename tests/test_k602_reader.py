from functools import lru_cache
from pathlib import Path

from thelpviewer.converter.exporter import detect_format_handler, load_document
from thelpviewer.converter.readers.k602 import K602Reader, is_k602_binary
from thelpviewer.converter.writers.json import HelpJsonRenderer


K602_PATH = Path("data/sources") / "Software 602" / "K602.HLP"


@lru_cache(maxsize=1)
def _k602_document():
    return K602Reader(str(K602_PATH), K602_PATH).read_bytes(K602_PATH.read_bytes())


def test_k602_is_detected_by_manifest_converter_registry():
    data = K602_PATH.read_bytes()
    handler = detect_format_handler(K602_PATH, data)

    assert is_k602_binary(data)
    assert handler is not None
    assert handler.name == "k602"

    document = load_document(K602_PATH)
    assert document.format_name == "k602"


def test_k602_reader_parses_topic_table_and_text_blocks():
    document = _k602_document()

    assert len(document.topics) == 115
    assert len(document.index_entries) == 92
    assert document.metadata["table_entry_count"] == 239
    assert document.metadata["topic_count"] == 115
    assert document.metadata["title"] == "Kartotéka 602"
    assert document.metadata["text_encoding"] == "utf-8"
    assert document.metadata["source_encoding"] == "software602-direct"
    assert document.metadata["ui"]["window"] == "#005454"

    topic = next(topic for topic in document.topics if topic.context_id == 109)
    assert topic.names == ["Nová databáze"]
    assert "  [b]Nová databáze [/b]" in topic.uhf_content
    assert "vytvoření struktury věty datového ([b]DBF[/b]) souboru." in topic.uhf_content

    labels = [entry.label.decode("utf-8") for entry in document.index_entries]
    assert "Uložení makra" not in labels
    assert "Příkaz zruší seznam příkazů pro tisk." not in labels
    assert "Topic 90" not in labels
    assert "Topic 91" not in labels
    assert labels.count("Výběr klávesnice") == 8

    macro_stub = next(topic for topic in document.topics if topic.context_id == 18)
    assert macro_stub.names == ["Uložení makra"]
    assert macro_stub.uhf_content == ["  Uložení makra", "   ■■■■■■■■■■■■■■■"]


def test_k602_strips_line_attributes_without_losing_box_art():
    document = _k602_document()

    intro = next(topic for topic in document.topics if topic.context_id == 120)
    assert intro.names == ["Kartotéka K602"]
    assert " ┌────────────────────────────────────────────┐" in intro.uhf_content
    assert " │          [b]K a r t o t é k a  K602           [/b]│" in intro.uhf_content
    assert not any(line.endswith("ů") for line in intro.uhf_content[:12])

    all_text = "\n".join(line for topic in document.topics for line in topic.uhf_content)
    assert "Vyčištění Ú" not in all_text
    assert "Databáze Ú" not in all_text
    assert "Výběr Ú" not in all_text
    assert "☻" not in all_text
    assert "♦" not in all_text


def test_k602_json_payload_is_renderable():
    payload = HelpJsonRenderer(_k602_document(), display_encoding="utf-8").render_document()

    assert payload["metadata"]["source"]["format"] == "k602"
    assert payload["metadata"]["source"]["encoding"] == "software602-direct"
    assert payload["topics"]["109"]["title"] == "Nová databáze"
    assert payload["topics"]["120"]["title"] == "Kartotéka K602"
