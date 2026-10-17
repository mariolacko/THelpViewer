"""Consumer defaults and page contexts are not keyword-navigation indices."""
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from test_thelp_contexts import guide
from test_thelp_reader import _screen
from test_thelp_validation import TABLE, admin, file_header, record, sample, text


def test_original_pascal4_default_slots_select_the_native_index_record():
    data = Path("var/sources/Borland Turbo Pascal 4.0/TURBO.HLP").read_bytes()
    parser = ThelpBinaryParser(data)
    meta, screens, _index, _tags = parser.parse()
    assert meta["help_contents_topic_id"] == 100
    assert parser.context_array[100] == 4985
    assert len(parser.context_array) == 509
    expected = [context for context, offset in enumerate(parser.context_array) if offset == 0xFFFFFF]
    assert len(expected) == 129
    assert meta["help_contents_aliases"] == expected
    index = next(screen for screen in screens if screen["id"] == 100)
    assert index["is_help_contents"] and index["alias_ids"] == expected
    document = ThelpHelpReader().read_bytes(data)
    assert "unresolved_contexts" not in document.metadata
    bundle = HelpJsonRenderer(document).render_document()
    assert bundle["metadata"]["help_contents_topic_id"] == 100
    assert bundle["topics"]["100"]["aliases"]["ids"] == expected
    assert bundle["topics"]["100"]["is_help_contents"] is True
    # Directories refers to context 140 (FFFFFFh); it is not a row anchor.
    assert any("[link:topic=140]" in row for row in bundle["topics"]["114"]["content"])


@pytest.mark.parametrize("version,text_version", [(1, 1), (3, 1), (4, 1), (4, 2)])
def test_unverified_short_header_defaults_do_not_claim_a_context_zero_binding(version, text_version):
    document = ThelpHelpReader().read_bytes(sample(version, text_version, extended=False))
    assert document.metadata["help_contents_topic_id"] is None
    assert document.metadata["help_contents_aliases"] == []
    assert document.topics[0].context_id == 1
    assert not document.topics[0].is_help_contents
    assert "help_contents_topic_id" not in HelpJsonRenderer(document).render_document()["metadata"]


def test_verified_default_with_no_context_100_does_not_select_another_body():
    document = ThelpHelpReader().read_bytes(sample(2))
    assert document.metadata["help_contents_topic_id"] == 100
    assert document.topics[0].context_id == 1
    assert document.topics[0].alias_contexts == []
    assert not document.topics[0].is_help_contents
    assert "help_contents_topic_id" not in HelpJsonRenderer(document).render_document()["metadata"]


@pytest.mark.parametrize("version,text_version", [(4, 1), (4, 2)])
def test_short_header_keeps_genuine_context_zero_without_promoting_it_to_contents(version, text_version):
    head = admin(version, text_version) + file_header(version, extended=False) + record(5, b"\2" + TABLE)
    start = len(head) + 11
    contexts = record(1, struct.pack("<H", 2) + start.to_bytes(3, "little") + b"\xff\xff\xff")
    keyword = record(3, struct.pack("<HHB7BH", 0, 0, 1, 1, 4, 7, 1, 1, 1, 1, 0))
    document = ThelpHelpReader().read_bytes(head + contexts + text(b" Link") + keyword)
    topic = document.topics[0]
    assert topic.context_id == 0 and topic.alias_contexts == []
    assert not topic.is_help_contents and document.metadata["help_contents_topic_id"] is None
    assert topic.positional_keywords[0].target_context == 0
    assert "[link:topic=0]Link[/link]" in topic.uhf_content[0]
    assert topic.nav_items == []


def test_stored_context_zero_contents_is_not_confused_with_a_page_chain_terminator():
    document = ThelpHelpReader().read_bytes(guide([None, 0xFFFFFF], [0], main=0))
    topic = document.topics[0]
    assert (topic.context_id, topic.alias_contexts, topic.is_help_contents) == (0, [1], True)
    assert topic.up_context is None and topic.down_context is None
    assert topic.nav_items == []
    assert topic.uhf_content[1] == "[link:topic=0]Link[/link] "
    bundle = HelpJsonRenderer(document).render_document()
    assert bundle["metadata"]["help_contents_topic_id"] == 0
    assert "nav" not in bundle["topics"]["0"]


def test_shared_stored_contents_binding_does_not_require_a_negative_alias_slot():
    document = ThelpHelpReader().read_bytes(guide([0xFFFFFE, None, None], [1], main=2))
    assert (document.topics[0].context_id, document.topics[0].alias_contexts,
            document.topics[0].is_help_contents) == (2, [1], True)
    assert HelpJsonRenderer(document).render_document()["metadata"]["help_contents_topic_id"] == 2


def test_invalid_contents_word_does_not_promote_unassigned_physical_text_to_contents():
    document = ThelpHelpReader().read_bytes(guide([0xFFFFFF, 0xFFFFFE], [], main=65535))
    assert document.topics[0].context_id == 65536
    assert not document.topics[0].is_help_contents
    assert document.topics[0].alias_contexts == []
    assert "help_contents_topic_id" not in HelpJsonRenderer(document).render_document()["metadata"]


@pytest.mark.parametrize("up,down", [(0, 0), (0, 82), (81, 83), (82, 0)])
def test_page_navigation_uses_context_words_not_positioned_keyword_buttons(up, down):
    screen = _screen(7, [b" Link"])
    screen["link_up"], screen["link_down"] = up, down
    screen["keywords_v4"] = [(0, 0, 1, 4, 1, 2, 3, 4)]
    document = ThelpHelpReader()._build_document({}, [screen], [], binary_data=None)
    ThelpHelpReader.refresh_rendered_uhf_content(document, encoding="cp437")
    topic = document.topics[0]
    assert topic.positional_keywords[0].navigation == (1, 2, 3, 4)
    assert (topic.up_context, topic.prev_context) == (up or None, up or None)
    assert (topic.down_context, topic.next_context) == (down or None, down or None)
    expected = {label: {"topic_id": target} for label, target in
                (("Up", up), ("Down", down), ("Prev", up), ("Next", down)) if target}
    bundle = HelpJsonRenderer(document).render_document()
    assert bundle["topics"]["7"].get("nav", {}) == expected
