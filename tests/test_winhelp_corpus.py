"""Payload hashes independently confirmed using HelpDeco's native decoder."""

import hashlib
import json
from pathlib import Path
import struct
import zlib

import pytest

from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.winhelp_binary import WinHelpFile, WinHelpTopics
from thelpviewer.server.converter.readers.winhelp_text import WinHelpDisplay


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [("Borland C++ 4.x", f) for f in json.loads((ROOT / "tests/golden/winhelp/borland452.json").read_text())]
FIXTURES += [("Borland C++ 4.5", f) for f in json.loads((ROOT / "tests/golden/winhelp/borland45.json").read_text())]
DISPLAY_FIELDS = json.loads((ROOT / "tests/golden/winhelp/display_fields.json").read_text())


@pytest.mark.parametrize(("collection", "fixture"), FIXTURES,
                         ids=[collection + "/" + fixture["file"] for collection, fixture in FIXTURES])
def test_windows_help_payloads_and_keyword_destinations(collection, fixture):
    source = ROOT / "data/sources" / collection / fixture["file"]
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == fixture["source_sha256"]
    assert f"{zlib.crc32(data):08X}" == fixture["crc32"]
    file = WinHelpFile(data)
    topics = WinHelpTopics(file)
    assert topics.system.minor == fixture["minor"]
    assert topics.system.flags == fixture["flags"]
    digest = hashlib.sha256()
    count = headers = total_size = 0
    fields = []
    for record in topics.links():
        digest.update(struct.pack("<IIIBII", record.position, record.previous, record.following,
                                  record.record_type, len(record.data1), len(record.data2)))
        digest.update(record.data1)
        digest.update(record.data2)
        count += 1
        headers += record.record_type == 2
        total_size += len(record.data1) + len(record.data2)
        if record.record_type in {0x20, 0x23}:
            display = WinHelpDisplay.read(record)
            assert display.paragraphs
            fields.append([display.size & 0xFFFFFFFF, display.length, display.table_type,
                           display.minimum_width, [list(c) for c in display.columns]])
    assert digest.hexdigest() == fixture["record_sha256"]
    assert count == fixture["records"] and headers == fixture["topics"]
    assert total_size == fixture["decoded_size"]
    field_count, field_digest = DISPLAY_FIELDS[collection + "/" + fixture["file"]]
    assert len(fields) == field_count
    assert hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest() == field_digest
    articles = list(topics.articles())
    assert [a.number for a in articles] == list(range(fixture["topics"]))
    targets = file.keyword_targets(source.with_suffix(".HLX").read_bytes())
    assert len(targets) == fixture["keywords"]
    offsets = tuple(offset for _, values in targets for offset in values)
    assert len(offsets) == fixture["references"]
    resolved = topics.resolve_offsets(offsets)
    assert all(target is not None and target.topic_number in range(fixture["topics"]) for target in resolved)
    assert detect_format_handler(source, data).name == "winhelp"
