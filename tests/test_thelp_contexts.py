"""A referring hotspot is not a destination; context offsets define aliases."""
import gzip
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.base import HelpDocument, IndexEntry, TopicRecord
from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_thelp_validation import TABLE, admin, file_header, record, text


def guide(slots, targets, *, main=1, index=(), body=None):
    head = admin() + file_header(main=main) + record(5, b"\2" + TABLE)
    index_record = record(4, struct.pack("<H", len(index)) + b"".join(
        bytes([len(label)]) + label + struct.pack("<H", target) for label, target in index))
    body = body if body is not None else b" heading\0" + b" ".join(b"\2Link\2" for _ in targets)
    text_record = text(body)
    keyword_record = record(3, struct.pack("<3H", 0, 0, len(targets))
                            + b"".join(struct.pack("<H", target) for target in targets))
    start = len(head) + 5 + 3 * len(slots) + len(index_record)
    tail = start + len(text_record) + len(keyword_record)
    offsets = [start if slot is None else tail + 2 if slot == "padding" else slot for slot in slots]
    contexts = record(1, struct.pack("<H", len(slots)) + b"".join(off.to_bytes(3, "little") for off in offsets))
    return head + contexts + index_record + text_record + keyword_record + b" " * 100


def index_entries(bundle):
    return [entry for group in bundle["index"] for entry in group["entries"]]


def test_shared_contents_record_has_one_consistent_primary_and_all_native_aliases():
    data = guide([0xFFFFFF, None, None, 0xFFFFFE], [1], main=2, index=[(b"Alias", 1)])
    document = ThelpHelpReader().read_bytes(data)
    topic = document.topics[0]
    assert (topic.context_id, topic.alias_contexts, topic.is_help_contents) == (2, [1, 0], True)
    assert topic.sequential_keywords == [1]
    assert topic.uhf_content[1] == "[link:topic=1]Link[/link] "
    assert "unresolved_contexts" not in document.metadata
    assert "context_fallbacks" not in document.metadata
    bundle = HelpJsonRenderer(document).render_document()
    assert bundle["metadata"]["help_contents_topic_id"] == 2
    assert bundle["topics"]["2"]["aliases"]["ids"] == [1, 0]
    assert index_entries(bundle) == [{"label": "Alias", "topic_id": 2}]


@pytest.mark.parametrize("targets", [[2], [2, 2]])
def test_padding_reference_keeps_its_native_target_not_a_referring_line(targets):
    data = guide([0xFFFFFF, None, "padding"], targets, index=[(b"Link", 2)])
    document = ThelpHelpReader().read_bytes(data)
    topic = document.topics[0]
    assert sum(row.count("[link:topic=2]") for row in topic.uhf_content) == len(targets)
    assert "line=" not in "\n".join(topic.uhf_content)
    assert (document.index_entries[0].topic_id, document.index_entries[0].line) == (None, None)
    assert document.metadata["unresolved_contexts"]["index"] == [2]
    assert document.metadata["unresolved_contexts"]["links"] == [2]
    assert document.metadata["unresolved_contexts"]["space_tail"] == [2]
    bundle = HelpJsonRenderer(document).render_document()
    assert index_entries(bundle) == [{"label": "Link", "topic_id": 2}]
    assert bundle["metadata"]["unresolved_contexts"] == document.metadata["unresolved_contexts"]


@pytest.mark.parametrize("slot,category", [(0xFFFFFE, "no_help"), ("padding", "space_tail")])
def test_sentinels_and_padding_are_distinct_native_failure_categories(slot, category):
    document = ThelpHelpReader().read_bytes(guide([0xFFFFFF, None, slot], [2]))
    status = document.metadata["unresolved_contexts"]
    assert status[category] == [2]
    assert status["out_of_range"] == []
    assert document.topics[0].uhf_content[1] == "[link:topic=2]Link[/link] "


def test_out_of_namespace_target_is_not_a_no_help_offset_sentinel():
    document = ThelpHelpReader().read_bytes(guide([0xFFFFFF, None], [65534]))
    status = document.metadata["unresolved_contexts"]
    assert status["out_of_range"] == [65534]
    assert status["no_help"] == []
    assert status["offsets"] == {}
    assert document.topics[0].uhf_content[1] == "[link:topic=65534]Link[/link] "


def test_unbound_contents_is_not_replaced_with_the_first_visible_topic():
    document = ThelpHelpReader().read_bytes(guide([0xFFFFFF, 0xFFFFFF, None], [1]))
    assert document.topics[0].context_id == 2
    assert document.topics[0].alias_contexts == []
    assert document.metadata["unresolved_contexts"]["unbound_contents"] == [1]
    assert document.topics[0].uhf_content[1] == "[link:topic=1]Link[/link] "


def test_a_space_run_in_a_record_is_not_classified_as_terminal_padding():
    document = HelpDocument(format_name="borland", source_name="sample", metadata={"trailing_padding": {"offset": 109}},
                            topics=[TopicRecord(1, [b"\2Link\2"], sequential_keywords=[2])], index_entries=[])
    data = b"X" * 5 + b" " * 64 + b"X" * 40 + b" " * 20
    ThelpHelpReader._annotate_unresolved_contexts(document, [0xFFFFFF, 0, 5], data)
    assert document.metadata["unresolved_contexts"]["space_tail"] == []
    assert document.metadata["unresolved_contexts"]["offsets"] == {"2": 5}
    ThelpHelpReader._annotate_unresolved_contexts(document, [0xFFFFFF, 0, 5], data)
    assert document.metadata["transport_metadata_keys"] == ["unresolved_contexts"]


def test_declared_missing_index_context_is_not_guessed_from_an_alias_string():
    document = HelpDocument(format_name="example", source_name="sample", topics=[
        TopicRecord(1, [b"Body"], alias_strings=["missing"])], index_entries=[IndexEntry(b"missing", 999)],
        metadata={"unresolved_contexts": {"index": [999]}, "transport_metadata_keys": ["unresolved_contexts"]})
    assert index_entries(HelpJsonRenderer(document).render_document()) == [{"label": "missing", "topic_id": 999}]


def test_real_transfer_arguments_alias_opens_its_record_instead_of_the_source_page():
    source = Path("var/sources/Borland C++ 3.0/TCHELP.TCH")
    document = ThelpHelpReader().read_path(source)
    owner = next(topic for topic in document.topics if 543 in topic.alias_contexts)
    source_topic = next(topic for topic in document.topics if topic.context_id == 2887)
    assert owner.context_id != source_topic.context_id
    assert "[link:topic=543]Transfer Arguments[/link]" in "\n".join(source_topic.uhf_content)
    assert "context_fallbacks" not in document.metadata


def test_real_pascal_register_alias_opens_its_record_not_the_referring_menu_row():
    document = ThelpHelpReader().read_path(Path("var/sources/Borland Turbo Pascal 7/TURBO.TPH"))
    register = next(topic for topic in document.topics if topic.context_id == 117)
    assert 477 in register.alias_contexts
    assert any("[link:topic=477]" in row and "Register" in row
               for row in next(topic for topic in document.topics if topic.context_id == 28).uhf_content)
    assert "unresolved_contexts" not in document.metadata


def test_native_contexts_and_diagnostics_reach_a_bundle_without_changing_the_source(tmp_path):
    source = tmp_path / "sources" / "Example" / "HELP.TPH"
    source.parent.mkdir(parents=True)
    data = guide([0xFFFFFF, None, "padding"], [2], index=[(b"Link", 2)])
    source.write_bytes(data)
    result = export_bundle_tree(tmp_path / "sources", tmp_path / "output", source_paths=[source], layout="helps")
    bundle = json.loads(gzip.decompress(result[0].json_path.read_bytes()))
    assert "[link:topic=2]Link[/link] " in bundle["topics"]["1"]["content"]
    assert bundle["metadata"]["unresolved_contexts"]["space_tail"] == [2]
    assert index_entries(bundle) == [{"label": "Link", "topic_id": 2}]
    assert source.read_bytes() == data
