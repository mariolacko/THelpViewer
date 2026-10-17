import gzip
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.writers.bundle import export_bundle, export_bundle_tree


def _load_bundle_payload(bundle_result):
    assert bundle_result.json_path.exists(), f"Expected bundle missing: {bundle_result.json_path}"
    return json.loads(gzip.decompress(bundle_result.json_path.read_bytes()).decode("utf-8"))


def test_legacy_tdh_bundle_suppresses_redirect_alias_topics(tmp_path):
    source = Path("var/sources") / "Borland Turbo Debugger 1.0" / "TDHELP.TDH"
    assert source.exists(), f"Source TDH not found: {source}"

    result = export_bundle(source, tmp_path)
    assert result.format_name == "tdh"
    assert result.topic_count == 519

    payload = _load_bundle_payload(result)
    metadata = payload.get("metadata") or {}
    assert metadata.get("source", {}).get("format") == "tdh"
    assert metadata.get("help_contents_topic_id") == 1
    assert (metadata.get("display") or {}).get("cols") == 48

    contents = payload.get("contents") or []
    assert contents[0]["label"] == "Help on Help"
    assert contents[0]["topic_id"] == 2

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) == 519
    for alias_context in range(519, 530):
        assert str(alias_context) not in topics

    help_index = topics.get("1") or {}
    assert "[link:topic=2]Help on Help[/link]" in "\n".join(help_index.get("content") or [])

    serial_port = topics.get("425") or {}
    assert 520 in ((serial_port.get("aliases") or {}).get("ids") or [])

    selected_character = topics.get("328") or {}
    assert 528 in ((selected_character.get("aliases") or {}).get("ids") or [])


def test_later_tdh_bundle_exports_known_runtime_topics(tmp_path):
    source = Path("var/sources") / "Borland Turbo Assembler 1.0 with Turbo Debugger" / "TDHELP.TDH"
    assert source.exists(), f"Source TDH not found: {source}"

    result = export_bundle(source, tmp_path)
    assert result.format_name == "tdh"
    assert result.topic_count == 597

    payload = _load_bundle_payload(result)
    metadata = payload.get("metadata") or {}
    assert metadata.get("source", {}).get("format") == "tdh"
    assert metadata.get("help_contents_topic_id") == 1
    assert (metadata.get("display") or {}).get("cols") == 48

    contents = payload.get("contents") or []
    assert contents[0]["label"] == "Help on Help"
    assert contents[0]["topic_id"] == 2

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) == 597

    help_index = topics.get("1") or {}
    help_index_text = "\n".join(help_index.get("content") or [])
    assert "[link:topic=2]Help on Help[/link]" in help_index_text
    assert "[link:topic=401]Assembler[/link]" in help_index_text
    assert "[link:topic=419]C Debugging tips[/link]" in help_index_text

    assert (topics.get("537") or {}).get("content") == [""]
    assert (topics.get("539") or {}).get("content", [None, None])[1] == "Opens an object type Inspector to show the data"
    assert (topics.get("530") or {}).get("title") == "In some cases, a Ctrl function key duplicates"


def test_tfh_bundle_exports_contents_nav_and_hotspots(tmp_path):
    source = Path("var/sources") / "Borland Turbo Profiler" / "TFHELP.TFH"
    assert source.exists(), f"Source TFH not found: {source}"

    result = export_bundle(source, tmp_path)
    assert result.format_name == "tfh"
    assert result.topic_count == 363

    payload = _load_bundle_payload(result)
    metadata = payload.get("metadata") or {}
    assert metadata.get("source", {}).get("format") == "tfh"
    assert metadata.get("help_contents_topic_id") == 1
    assert (metadata.get("display") or {}).get("cols") == 48

    contents = payload.get("contents") or []
    assert len(contents) == 7
    assert contents[0]["label"] == "Help on Help"
    assert contents[0]["topic_id"] == 2

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) == 363

    help_index = topics.get("1") or {}
    assert help_index.get("title") == "HELP INDEX"
    assert "[link:topic=2]Help on Help[/link]" in "\n".join(help_index.get("content") or [])

    topic_20 = topics.get("20") or {}
    assert (topic_20.get("nav") or {}).get("Next", {}).get("topic_id") == 19

    file_menu = topics.get("51") or {}
    assert (file_menu.get("content") or [None] * 9)[8].count("[link:topic=") >= 2
    assert "[link:topic=58]Open[/link]" in (file_menu.get("content") or [""] * 9)[8]
    assert "[link:topic=235]Get Info[/link]" in (file_menu.get("content") or [""] * 9)[8]

    module_window = topics.get("103") or {}
    assert "[link:topic=149]text pane[/link]" in (module_window.get("content") or [""])[0]
    assert "[link:topic=66]Module Window[/link]" in (module_window.get("content") or [""])[0]


def test_german_debugger_15_keeps_native_contents_and_verified_language(tmp_path):
    source = Path("var/sources/Borland Turbo Debugger 1.5 (DE)/TDHELP.TDH")
    if not source.is_file():
        pytest.skip("Original German Debugger 1.5 not available")
    results = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=[source], layout="helps")
    assert len(results) == 1 and results[0].topic_count == 536
    payload = _load_bundle_payload(results[0])
    assert payload["metadata"]["language"] == "de"
    assert payload["metadata"]["help_contents_topic_id"] == 1
    assert payload["contents"][0] == {"label": "Hilfe zur Hilfe", "children": [], "topic_id": 2}
    assert "Ausdrücke" in "\n".join(payload["topics"]["2"]["content"])
    assert not payload["metadata"].get("unresolved_contexts", {}).get("links")
    single = _load_bundle_payload(export_bundle(source, tmp_path / "single"))
    assert single["metadata"]["language"] == "de"
    assert single["contents"] == payload["contents"]
