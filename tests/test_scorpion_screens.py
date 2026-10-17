"""Native Scorpion screens retain every source cell and default font byte."""

from pathlib import Path
import base64

import pytest

from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.scorpion_dat_parser import parse_scorpion_dat_records
from thelpviewer.server.converter.readers.scorpion_screens import decode_text_screen
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


@pytest.mark.parametrize("version,count", [("15", 9), ("16", 9), ("21", 10), ("22", 10), ("23", 10)])
def test_program_screens_preserve_native_order_glyph_attributes_font_and_all_articles(version, count):
    path = Path(f"var/sources/Scorpions Cheater DOS/Scorpions Cheater {version}/PROGRAM.DAT")
    if not path.is_file():
        pytest.skip("Original Scorpion PROGRAM resources are not installed")
    data = path.read_bytes()
    records = parse_scorpion_dat_records(data)
    document = load_document(path)
    payload = HelpJsonRenderer(document, "utf-8").render_document()
    screen_records = [record for record in records if len(record.payload) == 4000]
    assert len([name for name in document.text_screens if name.startswith("screen-")]) == count == len(screen_records)
    font = next(record for record in records if record.name.lower() == ("obr4" if version == "15" else "font1"))
    assert base64.b64decode(payload["fonts"]["program-font"]["data"]) == font.payload
    topics = document.topics[-count:]
    for record, topic in zip(screen_records, topics):
        screen = payload["text_screens"][f"screen-{record.index}"]
        assert topic.alias_strings == [record.name]
        assert topic.uhf_content == [f"[screen:screen-{record.index}]"]
        assert screen["cols"] == 80 and screen["rows"] == 25 and screen["cell_format"] == "dos-text"
        assert "cells" not in screen and base64.b64decode(screen["data"]) == record.payload
        assert len(screen["text"]) == 25
    assert document.contents[0].children[-1].label == "Obrazovky programu"
    assert len(document.contents[0].children[-1].children) == count
    assert document.topics[:-count] and all(not t.uhf_content[0].startswith('[screen:') for t in document.topics[:-count])
    assert path.read_bytes() == data


@pytest.mark.parametrize("data", [b"", b"\0" * 3999, b"\0" * 4001, b"A\x80" * 2000])
def test_incomplete_screens_and_unverified_blink_attributes_are_not_guessed(data):
    with pytest.raises(ValueError):
        decode_text_screen(data, "font")


def test_screen_bytes_are_glyph_codes_not_article_style_controls():
    cells = b"\xf0\x1e" + b"\x20\x00" * 1999
    screen = decode_text_screen(cells, "font")
    assert screen.cells[0] == (0xF0, 14, 1)
