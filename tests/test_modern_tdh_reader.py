"""Newer TDH maps/layout, verified against the original 4.0/5.0 DOS parser."""

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.help_database import load_help_manifest, lookup_help_database_entry
from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.tdh import TdhHelpReader, probe_tdh_binary
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


SAMPLES = [
    ("4.x", "TD32HELP.TDH", 0x7C2A5934, 777, 774, 758, [59, 60, 776]),
    ("4.x", "TDHELP.TDH", 0xBBF9DEFB, 728, 727, 720, [725, 726]),
    ("4.x", "TDWHELP.TDH", 0x77B4692D, 731, 731, 714, [60]),
    ("5.x", "TD32HELP.TDH", 0x7D23BEE7, 817, 818, 772, []),
    ("5.x", "TDHELP.TDH", 0x1A84ACE2, 776, 777, 733, []),
    ("5.x", "TDWHELP.TDH", 0x86079353, 775, 776, 726, [78]),
]

# Exact cells and hotspot coordinates confirmed by matching native execution.
NATIVE_DIGESTS = {
    ("4.x", "TD32HELP.TDH"): "5233df7186b08df4a32747da1a9d87ac542d60f6c7b80ea91a38f37a2c81b146",
    ("4.x", "TDHELP.TDH"): "7825709a8f8f759986543fcbd4255194f7e2e84bfbf0ac3719c92e63d16c755e",
    ("4.x", "TDWHELP.TDH"): "b9b21e9bb4b9f20e18ce2ea3273283e643840330bf776ae15c1d54521f34d676",
    ("5.x", "TD32HELP.TDH"): "8c3b9f7935ce1b900bcb0c43b2553625c7297adabb118ebbe0679c38a7162e60",
    ("5.x", "TDHELP.TDH"): "33b894f3d65612a16f1e7a2d077bc4b5735dc9be7747394edb9bf606291162b2",
    ("5.x", "TDWHELP.TDH"): "e11264bb585133f365d495fb7d60a62392dbab233482f2733bbb2451d5ce73a4",
}


def source(version, filename):
    path = Path("var/sources") / f"Borland Turbo Assembler {version}" / filename
    if not path.is_file():
        pytest.skip("Original newer TDH not available")
    return path


@pytest.mark.parametrize("version,filename,crc,count,topics,links,absent", SAMPLES)
def test_modern_corpus_keeps_real_pages_links_and_absent_contexts(version, filename, crc, count, topics, links, absent):
    path = source(version, filename)
    data = path.read_bytes()
    probe = probe_tdh_binary(data)
    assert probe and probe.crc32 == crc and probe.header_word == count
    assert probe.separator_offset == 2 + 2 * count
    assert detect_format_handler("UNKNOWN.BIN", data).name == "tdh"
    document = TdhHelpReader(source_path=path).read_bytes(data)
    assert len(document.topics) == topics
    assert document.metadata["display_width"] == 48
    assert document.metadata["tdh_decode"]["absent_contexts"] == absent
    assert document.topics[0].uhf_content == [""]
    assert document.contents[0].label == "Help on Help"
    ids = {topic.context_id for topic in document.topics}
    assert ids.isdisjoint(absent)
    assert sum(len(topic.positional_keywords) for topic in document.topics) == links
    cells = [(topic.context_id, [row.hex() for row in topic.raw_lines],
              [(key.target_context, key.line, key.first_column, key.last_column)
               for key in topic.positional_keywords]) for topic in document.topics]
    digest = hashlib.sha256(json.dumps(cells, separators=(",", ":")).encode()).hexdigest()
    assert digest == NATIVE_DIGESTS[version, filename]
    for topic in document.topics:
        assert len(topic.raw_lines) <= 15
        assert all(len(line) <= 48 for line in topic.raw_lines)
        assert all(b"<E>" not in line for line in topic.raw_lines)
        assert topic.next_context is None or topic.next_context in ids
        for keyword in topic.positional_keywords:
            assert keyword.target_context in ids
            assert 1 <= keyword.first_column <= keyword.last_column <= len(topic.raw_lines[keyword.line])


def test_variable_overlapping_base_word_and_literal_lead_are_not_version_signatures():
    for filename, expected in (("TDHELP.TDH", 0xC101), ("TDWHELP.TDH", 0x0901)):
        probe = probe_tdh_binary(source("4.x", filename).read_bytes())
        assert probe.separator_word == expected
    assert probe_tdh_binary(source("4.x", "TDHELP.TDH").read_bytes()).payload_lead_byte == 0xC3


def test_final_goto_page_and_payload_overlap_alias_remain_navigable():
    dos = TdhHelpReader().read_bytes(source("5.x", "TDHELP.TDH").read_bytes())
    assert "[link:topic=776]Goto[/link]" in "\n".join(dos.topics[774].uhf_content)
    assert "[link:topic=774]Exports list[/link]" in "\n".join(dos.topics[-1].uhf_content)
    windows = TdhHelpReader().read_bytes(source("5.x", "TDWHELP.TDH").read_bytes())
    alias = next(topic for topic in windows.topics if topic.context_id == 776)
    owner = next(topic for topic in windows.topics if topic.context_id == 775)
    assert alias.redirect_context == 775
    assert owner.alias_contexts == [776]
    assert owner.raw_lines == alias.raw_lines
    assert windows.metadata["tdh_decode"]["runtime_table_word_count"] == 777


def test_malformed_or_truncated_map_fails_without_publishing_partial_topics():
    data = source("4.x", "TD32HELP.TDH").read_bytes()
    with pytest.raises(ValueError, match="context map outside file"):
        TdhHelpReader().read_bytes(data[:-5000])
    bad = bytearray(data)
    struct.pack_into(">H", bad, 4, 0x8000)
    with pytest.raises(ValueError, match="context map outside file"):
        TdhHelpReader().read_bytes(bytes(bad))
    bad = bytearray(data)
    struct.pack_into(">H", bad, 2, 2)
    assert probe_tdh_binary(bytes(bad)) is None


def test_modern_bundle_versions_titles_aliases_and_source_ownership(tmp_path):
    paths = [source(version, filename) for version, filename, *_ in SAMPLES]
    originals = {path: hashlib.sha256(path.read_bytes()).digest() for path in paths}
    results = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=paths, layout="helps")
    assert len(results) == 6 and all(result.format_name == "tdh" for result in results)
    assert sum(result.topic_count for result in results) == 4602
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    assert {entry["version"] for entry in catalog} == {"4.0", "5.0"}
    assert {entry["product"] for entry in catalog} == {"td"}
    for entry in catalog:
        bundle = json.loads(gzip.decompress((tmp_path / entry["file"]).read_bytes()))
        assert entry["topics"] == len(bundle["topics"])
        assert bundle["metadata"]["display"]["cols"] == 48
        assert not bundle["metadata"].get("unresolved_contexts", {}).get("links")
        if entry["file"].endswith("tdwhelp-5.0.json.gz"):
            assert "776" not in bundle["topics"]
            assert bundle["topics"]["775"]["aliases"]["ids"] == [776]
    manifest = load_help_manifest()
    for path in paths:
        assert hashlib.sha256(path.read_bytes()).digest() == originals[path]
        assert lookup_help_database_entry(path, manifest.entry_map).product_key == "td"
