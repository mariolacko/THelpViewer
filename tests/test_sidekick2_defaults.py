"""Native app roots enrich the catalog; they do not replace wire identities."""
import gzip
import hashlib
import json
from pathlib import Path

from thelpviewer.help_database import lookup_help_database_entry
from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


SOURCE = Path("var/sources/Borland Sidekick 2/SK2.HLP")


def test_original_sidekick2_has_a_long_header_not_an_unknown_short_contents_binding():
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == "d74837a0b2bf06bf8663ba63755831557a6722de1bab9b6da690519d9efbc82f"
    assert data[32:44] == bytes.fromhex("00 09 00 00 00 00 00 d3 01 11 32 00")
    parser = ThelpBinaryParser(data)
    metadata, screens, index, _tags = parser.parse()
    assert (metadata["format_version"], metadata["text_version"], metadata["help_contents_topic_id"]) == (4, 2, 0)
    assert (metadata["height"], metadata["width"], metadata["left_margin"]) == (17, 50, 0)
    assert parser.context_array[0] == 0xFFFFFE
    assert index == [] and len(screens) == 768
    assert not any(screen["is_help_contents"] for screen in screens)
    assert metadata["help_contents_aliases"] == []
    assert sum(offset == 0xFFFFFF for offset in parser.context_array) == 370
    assert sum(offset == 0xFFFFFE for offset in parser.context_array) == 7


def test_catalog_uses_the_original_no_application_general_root_without_aliasing_failed_slots():
    entry = lookup_help_database_entry(SOURCE)
    assert entry.crc32 == 0x58D27871
    assert entry.help_contents_topic_id == 101
    assert entry.product_key == "sk" and entry.version == "2.0"
    assert entry.sources["winworld"].archive_members == ("SK2.HLP",)
    assert "https://winworldpc.com/download/2d20744e-7356-11c3-a7c2-9d25525400ef" in entry.sources["winworld"].direct_urls
    document = ThelpHelpReader().read_path(SOURCE)
    assert document.metadata["help_contents_topic_id"] == 0
    assert len(document.topics) == 768 and len(document.index_entries) == 768
    general = next(topic for topic in document.topics if topic.context_id == 101)
    assert general.raw_lines[0].strip() == b"GENERAL SIDEKICK TOPICS"
    assert general.alias_contexts == [] and not general.is_help_contents
    assert 0 not in {topic.context_id for topic in document.topics}
    assert "unresolved_contexts" not in document.metadata


def test_verified_default_reaches_the_bundle_and_menu_without_changing_native_records(tmp_path):
    source = tmp_path / "sources/Borland Sidekick 2/SK2.HLP"
    source.parent.mkdir(parents=True)
    original = SOURCE.read_bytes()
    source.write_bytes(original)
    expected = ThelpHelpReader().read_path(SOURCE)
    output = tmp_path / "helps"
    results = export_bundle_tree(tmp_path / "sources", output, source_paths=[source], layout="helps")
    bundle = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    assert bundle["metadata"]["help_contents_topic_id"] == 101
    assert bundle["metadata"]["version"] == "2.0"
    assert bundle["metadata"]["source"]["filename"] == "SK2.HLP"
    assert set(map(int, bundle["topics"])) == {topic.context_id for topic in expected.topics}
    assert len(bundle["topics"]) == 768
    assert sum(len(group["entries"]) for group in bundle["index"]) == 768
    assert all("aliases" not in topic for topic in bundle["topics"].values())
    assert "0" not in bundle["topics"] and "376" not in bundle["topics"]
    assert "[link:topic=327]<more>[/link]" in bundle["topics"]["128"]["content"]
    assert bundle["topics"]["128"]["nav"]["Next"] == {"topic_id": 327}
    assert source.read_bytes() == original
    catalog = json.loads((output / "catalog.json").read_text())
    assert len(catalog) == 1
    assert (catalog[0]["product_name"], catalog[0]["version"], catalog[0]["file"]) == (
        "Borland Sidekick", "2.0", "Borland Sidekick 2/sk2.json.gz")
