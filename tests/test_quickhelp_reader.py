import gzip
import json
from pathlib import Path

from thelpviewer.converter.exporter import load_document
from thelpviewer.converter.writers.bundle import export_bundle


def test_quickhelp_list_topic_lines_are_linkified():
    path = Path("sources") / "Microsoft QuickC, C, and C++ 6.0" / "PWB.HLP"
    doc = load_document(path)

    topic = doc.topics[1]
    assert topic.quickhelp_is_list is True
    assert any("[link:topic=" in line for line in topic.uhf_content[1:])


def test_quickhelp_category_target_is_resolved():
    path = Path("sources") / "Microsoft QuickC, C, and C++ 6.0" / "RC.HLP"
    doc = load_document(path)

    topic = doc.topics[1]
    assert topic.quickhelp_category_nav is not None
    assert topic.quickhelp_category_nav.topic_id == 0
    assert topic.quickhelp_category_nav.line == 1


def test_quickhelp_popup_topics_are_flagged():
    path = Path("sources") / "Microsoft QuickC, C, and C++ 6.0" / "QH.HLP"
    doc = load_document(path)

    topic = doc.topics[12]
    assert topic.quickhelp_is_popup is True


def test_quickhelp_popup_topics_export_as_standard_topics(tmp_path):
    source = Path("sources") / "Microsoft QuickC, C, and C++ 6.0" / "QH.HLP"
    result = export_bundle(source, tmp_path)
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))

    topic = (payload.get("topics") or {}).get("12") or {}
    assert topic.get("title") == "Print  Use this command to copy all or part of a topic to LPT1. When you"
    assert "quickhelp_is_popup" not in topic
    assert "quickhelp_category_nav" not in topic


def test_quickbasic_marker_only_contents_nav_is_reader_rendered():
    path = Path("sources") / "Microsoft QuickBASIC Extended 7.1" / "BAS7QCK.HLP"
    doc = load_document(path)

    nav_line = next(
        line
        for topic in doc.topics
        for line in topic.uhf_content
        if "Contents" in line and "Back" in line
    )
    assert "[nav:contents]Contents[/nav]" in nav_line
    assert "[nav:back]Back[/nav]" in nav_line
    assert "◄[b]Contents[/b]►" not in nav_line