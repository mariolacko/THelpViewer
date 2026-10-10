import gzip
import json
import re
from pathlib import Path

import pytest

from thelpviewer.server.converter.writers.bundle import export_bundle


def test_bcw_hlx_exports_functional_uhf_bundle(tmp_path):
    source = Path("data/sources") / "Borland C++ 4.x" / "BCW.HLX"
    assert source.exists(), f"Source HLX not found: {source}"

    result = export_bundle(source, tmp_path)
    assert result.json_path.exists(), f"Expected bundle missing: {result.json_path}"

    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))
    assert payload.get("uhf_version") == "2.0"

    metadata = payload.get("metadata") or {}
    assert metadata.get("source", {}).get("format") == "hlx"
    assert metadata.get("hlx_kind") == "compiled-topics"
    assert metadata.get("hlx_family") == "rtf-keyword-map"

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) >= 100

    nontrivial_topics = 0
    for topic in topics.values():
        content = topic.get("content") or []
        joined = " ".join(str(line).strip() for line in content if str(line).strip())
        if len(joined) >= 40:
            nontrivial_topics += 1

    assert nontrivial_topics >= 100


def test_opengl_hlx_stays_index_like_bundle(tmp_path):
    source = Path("data/sources") / "Borland C++ 4.x" / "OPENGL.HLX"
    assert source.exists(), f"Source HLX not found: {source}"

    result = export_bundle(source, tmp_path)
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))

    metadata = payload.get("metadata") or {}
    assert metadata.get("hlx_kind") == "compiled-index"
    assert metadata.get("hlx_family") == "rtf-reference-map"

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) >= 900

    for topic in topics.values():
        content = [str(line).strip() for line in (topic.get("content") or []) if str(line).strip()]
        assert len(content) <= 1

    for section in payload.get("index") or []:
        for entry in section.get("entries") or []:
            label = str(entry.get("label") or "")
            assert ".rtf" not in label.lower()
            assert not re.match(r"^[0-9A-F]{8}\s", label)


def test_helpref_hlx_stays_heading_catalog_bundle(tmp_path):
    source = Path("data/sources") / "Borland C++ 4.x" / "HELPREF.HLX"
    assert source.exists(), f"Source HLX not found: {source}"

    result = export_bundle(source, tmp_path)
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))

    metadata = payload.get("metadata") or {}
    assert metadata.get("hlx_kind") == "compiled-index"
    assert metadata.get("hlx_family") == "heading-catalog"

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) >= 100

    for topic in topics.values():
        content = [str(line).strip() for line in (topic.get("content") or []) if str(line).strip()]
        assert len(content) <= 1


def test_rsl_hlx_exports_prev_next_navigation(tmp_path):
    source = Path("data/sources") / "Borland C++ 4.x" / "RSL.HLX"
    assert source.exists(), f"Source HLX not found: {source}"

    result = export_bundle(source, tmp_path)
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))

    metadata = payload.get("metadata") or {}
    assert metadata.get("hlx_kind") == "compiled-index"
    assert metadata.get("index_navigation_order") == "target_offset"

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) >= 3

    first = topics.get("1")
    assert isinstance(first, dict)
    assert first.get("nav", {}).get("Next", {}).get("topic_id") == 2

    last_key = str(max(int(key) for key in topics))
    last = topics[last_key]
    assert last.get("nav", {}).get("Prev", {}).get("topic_id") == int(last_key) - 1


@pytest.mark.parametrize(
    ("filename", "family", "min_topics"),
    [
        ("OLE.HLX", "heading-catalog", 1500),
        ("RSL.HLX", "topic-clusters", 100),
        ("VFW.HLX", "rtf-reference-map", 500),
        ("WIN31WH.HLX", "rtf-overview-map", 2500),
        ("WIN32.HLX", "rtf-reference-map", 2000),
        ("WINSPCTR.HLX", "rtf-reference-map", 70),
    ],
)
def test_catalog_hlx_variants_remain_single_line_bundles(tmp_path, filename, family, min_topics):
    source = Path("data/sources") / "Borland C++ 4.x" / filename
    assert source.exists(), f"Source HLX not found: {source}"

    result = export_bundle(source, tmp_path)
    payload = json.loads(gzip.decompress(result.json_path.read_bytes()))

    metadata = payload.get("metadata") or {}
    assert metadata.get("hlx_kind") == "compiled-index"
    assert metadata.get("hlx_family") == family

    topics = payload.get("topics") or {}
    assert isinstance(topics, dict)
    assert len(topics) >= min_topics

    multi_line_topics = 0
    for topic in topics.values():
        content = [str(line).strip() for line in (topic.get("content") or []) if str(line).strip()]
        if len(content) >= 3:
            multi_line_topics += 1

    assert multi_line_topics == 0