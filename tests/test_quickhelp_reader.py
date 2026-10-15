import gzip
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.writers.bundle import export_bundle


def test_quickhelp_list_topic_lines_are_linkified():
    path = Path("data/sources") / "Microsoft QuickC, C, and C++ 6.0" / "PWB.HLP"
    doc = load_document(path)

    topic = doc.topics[1]
    assert topic.quickhelp_is_list is True
    assert any("[link:topic=" in line for line in topic.uhf_content[1:])


def test_quickhelp_category_target_is_resolved():
    path = Path("data/sources") / "Microsoft QuickC, C, and C++ 6.0" / "RC.HLP"
    doc = load_document(path)

    topic = doc.topics[1]
    assert topic.quickhelp_category_nav is not None
    assert topic.quickhelp_category_nav.topic_id == 0
    assert topic.quickhelp_category_nav.line == 1


def test_quickhelp_popup_topics_are_flagged():
    path = Path("data/sources") / "Microsoft QuickC, C, and C++ 6.0" / "QH.HLP"
    doc = load_document(path)

    topic = doc.topics[12]
    assert topic.quickhelp_is_popup is True


def test_quickhelp_popup_topics_export_as_standard_topics(tmp_path):
    source = Path("data/sources") / "Microsoft QuickC, C, and C++ 6.0" / "QH.HLP"
    result = export_bundle(source, tmp_path)
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))

    topic = (payload.get("topics") or {}).get("12") or {}
    assert topic.get("title") == "Print  Use this command to copy all or part of a topic to LPT1. When you"
    assert "quickhelp_is_popup" not in topic
    assert "quickhelp_category_nav" not in topic


def test_quickbasic_marker_only_contents_nav_is_reader_rendered():
    path = Path("data/sources") / "Microsoft QuickBASIC Extended 7.1" / "BAS7QCK.HLP"
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


@pytest.mark.parametrize("with_advisor", [False, True])
def test_quickc_250_marker_nav_buttons_are_reader_rendered(tmp_path, with_advisor):
    originals = Path("data/sources/Microsoft QuickC, C, and C++ 2.50")
    path = tmp_path / "ERRORS.HLP"
    path.write_bytes((originals / path.name).read_bytes())
    if with_advisor:
        (tmp_path / "QC.HLP").write_bytes((originals / "QC.HLP").read_bytes())
    doc = load_document(path)

    nav_line = doc.topics[8].uhf_content[0]
    if with_advisor:
        assert "[link:file=QC.HLP,topic=0,alias=h.contents]Contents[/link]" in nav_line
        assert "[link:file=QC.HLP,topic=852,alias=h.index]Index[/link]" in nav_line
    else:
        assert "[nav:contents]Contents[/nav]" in nav_line
        assert "[nav:index]Index[/nav]" in nav_line
    assert "[nav:back]Back[/nav]" in nav_line
    assert "◄[b]Contents[/b]►" not in nav_line


def test_existing_external_quickhelp_target_keeps_file_topic_and_alias():
    path = Path("data/sources") / "Microsoft QuickBASIC Extended 7.1" / "BC.HLP"
    doc = load_document(path)

    assert any(
        "[link:file=CV.HLP,topic=90,alias=cv.contents]" in line
        for topic in doc.topics
        for line in topic.uhf_content
    )


def test_missing_external_quickhelp_target_remains_a_real_link():
    path = Path("data/sources") / "Microsoft QuickC, C, and C++ 6.0" / "PWB.HLP"
    doc = load_document(path)

    assert any(
        "[link:file=misc.hlp,alias=pwbrmake]" in line
        for topic in doc.topics
        for line in topic.uhf_content
    )


def test_qualified_missing_quickhelp_targets_remain_real_links():
    path = Path("data/sources") / "Microsoft QuickC, C, and C++ 6.0" / "PWB.HLP"
    doc = load_document(path)
    content = "\n".join(line for topic in doc.topics for line in topic.uhf_content)

    assert "[link:file=OS2.HLP,alias=h.overview]OS/2 Overview[/link]" in content
    assert "[link:file=OS2.HLP,alias=h.contents]OS/2 API[/link]" in content
    assert "[link:file=WIN.HLP,alias=h.contents]Windows API[/link]" in content
    assert "[link:file=LAN.HLP,alias=h.contents]Network API[/link]" in content


def test_quickbasic_advisor_links_resolve_across_original_disks():
    root = Path("data/sources/Microsoft QuickBASIC 4.5")
    if not (root / "QB45ADVR.HLP").is_file():
        return
    quick = load_document(root / "QB45QCK.HLP")
    advisor = load_document(root / "QB45ADVR.HLP")
    quick_content = "\n".join(line for topic in quick.topics for line in topic.uhf_content)
    advisor_content = "\n".join(line for topic in advisor.topics for line in topic.uhf_content)

    assert "[link:file=QB45ADVR.HLP,topic=185,alias=.erasex]Example►[/link]" in quick_content
    assert "[link:file=QB45ADVR.HLP,topic=88,alias=.vupri]VIEW PRINT statement►[/link]" in quick_content
    assert "[link:file=QB45ADVR.HLP,topic=" in quick_content
    assert "[link:file=QB45QCK.HLP,topic=" in advisor_content


def test_quickc_250_qa_file_is_an_intact_search_stub():
    path = Path("data/sources/Microsoft QuickC, C, and C++ 2.50/QA.HLP")
    doc = load_document(path)

    assert len(doc.topics) == 2
    assert "taw080554" in doc.topics[0].alias_strings
    assert "Null context for help file search order" in doc.topics[0].uhf_content[0]
