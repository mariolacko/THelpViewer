"""Pascal 7 ^T placeholders are substitutions, not emphasis delimiters."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_thelp_reader import _screen
from test_thelp_validation import TABLE, admin, file_header, record


@pytest.mark.parametrize("raw,expected", [
    ([b"\x14 Turbo \x14 Pascal"], [b"Turbo Pascal"]),
    ([b"\x14Turbo\x14 Pascal"], [b"Turbo Pascal"]),
    ([b"pre\x14discard\x14post"], [b"preTurbopost"]),
    ([b"\x14\x14"], [b"Turbo"]),
    ([b"\x14\x14\x14\x14"], [b"TurboTurbo"]),
    ([b"before\x14unclosed"], [b"beforeTurbo"]),
    ([b"\x14ignored", b"second\x14after"], [b"Turboafter"]),
    ([b"\x14ignored\5code\5\x14after"], [b"Turboafter"]),
    ([b"\2\x14Turbo\x14 Pascal\2"], [b"\2Turbo Pascal\2"]),
    ([b"  \x14 ignored \x14 tail  ", b""], [b"  Turbo tail  ", b""]),
    ([b"\x14ignored", b"\x14", b"after"], [b"Turbo", b"after"]),
])
def test_literal_controls_match_the_original_turbo_decoder(raw, expected):
    # TURBO.EXE CRC32 0951BC69, isolated decode routine 468FDh..469C9h.
    assert ThelpHelpReader._substitute_product_name(raw, b"Turbo") == expected


@pytest.mark.parametrize("description,name", [
    ("Turbo Pascal Help", b"Turbo"), ("Turbo Pascal Hilfe", b"Turbo"),
    ("Borland Pascal Help", b"Borland"), ("Borland Pascal Hilfe", b"Borland"),
    (None, b"Turbo"), ("Unidentified Help", b"Turbo"),
])
def test_profile_comes_from_native_tags_not_filename_or_guessed_emphasis(description, name):
    meta = {"format_version": 52, "text_version": 2, "description": description}
    topic = ThelpHelpReader._build_topics([_screen(1, [b"\x14 Turbo \x14 Pascal"])], meta)[0]
    assert topic.raw_lines == [name + b" Pascal"]
    assert not topic.code_line_indices


@pytest.mark.parametrize("version,text_version", [(2, 1), (4, 2), (51, 1), (52, 1), (52, 3)])
def test_other_text_variants_do_not_discard_unverified_control_glyphs(version, text_version):
    rows = [b"literal \x14paragraph glyph"]
    topic = ThelpHelpReader._build_topics([_screen(1, rows)],
        {"format_version": version, "text_version": text_version})[0]
    assert topic.raw_lines == rows


def packed_runs(runs):
    nibbles = []
    for count, value in [*runs, (1, 1)]:
        if count > 1:
            nibbles.extend((14, count - 2))
        nibbles.extend((15, value & 15, value >> 4))
    if len(nibbles) % 2:
        nibbles.append(0)
    return bytes(nibbles[i] | nibbles[i+1] << 4 for i in range(0, len(nibbles), 2))


@pytest.mark.parametrize("runs,expected", [
    ([(4, 20), (1, ord('A')), (1, 20), (1, ord('B'))], [b"TurboBBBB"]),
    ([(2, 20), (1, 20), (1, ord('B'))], [b"TurboBB"]),
    ([(1, 20), (4, ord('X')), (1, 20), (1, ord('Y'))], [b"TurboYYYY"]),
    ([(1, 20), (3, 0), (1, 20), (1, ord('Z'))], [b"TurboZZZ"]),
    ([(1, 20), (4, ord('X')), (2, ord('Y')), (1, 20), (1, ord('Z'))], [b"TurboZZ"]),
    ([(1, 20), (4, ord('X')), (1, 20), (1, 0), (1, ord('Z'))], [b"Turbo", b"", b"", b"", b"Z"]),
])
def test_substitution_is_before_rle_emission_and_retains_suppressed_repeat_count(runs, expected):
    # Both original TP7 and BP7 routines test ^T before STOSB/REP STOSB,
    # retaining CH until a visible ordinary character is actually emitted.
    binary = (admin(text_version=2) + file_header() + record(5, b"\2" + TABLE)
              + record(2, packed_runs(runs)) + record(3, bytes(6)))
    meta, screens, _, _ = ThelpBinaryParser(binary).parse()
    assert screens[0]["product_runs"] == bytes(value for pair in [*runs, (1, 1)] for value in pair)
    topic = ThelpHelpReader._build_topics(screens, meta)[0]
    # The native substitution output is then laid out by the word formatter;
    # a wrappable return contributes a trailing space, an empty row stays hard.
    assert topic.raw_lines == [line + b" " if line else b"" for line in expected]


def test_substitution_precedes_example_state_and_resets_per_physical_text_record():
    first = _screen(11, [b"\x14\5ignored"])
    second = _screen(22, [b"visible", b"\x14ignored\x14end"])
    first["link_down"], second["link_up"] = 22, 11
    meta = {"format_version": 52, "text_version": 2}
    topics = ThelpHelpReader._build_topics([first, second], meta)
    assert [topic.raw_lines for topic in topics] == [[b"Turbo"], [b"visible", b"Turboend"]]
    assert all(not topic.code_line_indices for topic in topics)
    assert first["lines"] == [b"\x14\5ignored"]  # Lossless source data is not mutated.


def test_hotspot_target_and_visible_label_survive_product_substitution():
    first = _screen(11, [b"\2\x14 Turbo \x14 Pascal\2"])
    first["keywords_v5"] = [22]
    document = ThelpHelpReader()._build_document(
        {"format_version": 52, "text_version": 2, "description": "Borland Pascal Help"},
        [first, _screen(22, [b"Target"])], [], None)
    ThelpHelpReader.refresh_rendered_uhf_content(document, encoding="cp437")
    assert document.topics[0].uhf_content == ["[link:topic=22]Borland Pascal[/link]"]
    assert document.topics[0].sequential_keywords == [22]


def test_native_originals_keep_raw_placeholders_but_project_correct_product_names():
    root = Path("var/sources")
    for name, product in [("Borland Turbo Pascal 7", "Turbo"), ("Borland Pascal 7.x current", "Borland")]:
        data = (root / name / "TURBO.TPH").read_bytes()
        _meta, screens, _, _ = ThelpBinaryParser(data).parse()
        assert any(b"\x14" in row for screen in screens for row in screen["lines"])
        document = ThelpHelpReader().read_bytes(data)
        topic = next(topic for topic in document.topics if topic.context_id == 2)
        assert topic.raw_lines[1] == f" \xdc Welcome to {product} Pascal's Online Help".encode("latin-1")
        assert not any(b"\x14" in row for topic in document.topics for row in topic.raw_lines)


def test_borland_product_name_reaches_bundle_and_source_stays_immutable(tmp_path):
    source = Path("var/sources/Borland Pascal 7.x current/TURBO.TPH")
    before = source.read_bytes()
    results = export_bundle_tree(Path("var/sources"), tmp_path, source_paths=[source], layout="helps")
    payload = json.loads(gzip.decompress(results[0].json_path.read_bytes()))
    assert "Welcome to Borland Pascal's Online Help" in "\n".join(payload["topics"]["2"]["content"])
    assert source.read_bytes() == before


def test_placeholder_records_match_original_turbo_and_borland_decoder_capture():
    digest = hashlib.sha256()
    files = records = rows = markers = 0
    root = Path("var/sources")
    for source in sorted(root.rglob("TURBO.TPH")):
        meta, screens, _, _ = ThelpBinaryParser(source.read_bytes()).parse()
        affected = [screen for screen in screens if "product_runs" in screen]
        if not affected:
            continue
        files += 1
        name = b"Borland" if str(meta.get("description") or "").casefold().startswith("borland pascal") else b"Turbo"
        for ordinal, screen in enumerate(screens):
            if "product_runs" not in screen:
                continue
            visible = ThelpHelpReader._substitute_product_name(screen["lines"], name, screen["product_runs"])
            digest.update(json.dumps((source.relative_to(root).as_posix(), ordinal,
                name.hex(), [line.hex() for line in visible]), separators=(",", ":")).encode() + b"\n")
            records += 1
            rows += len(visible)
            markers += sum(line.count(b"\x14") for line in screen["lines"])
    assert (files, records, rows, markers) == (8, 791, 20_584, 2_306)
    assert digest.hexdigest() == "d268765ddd4113309a232cfcf0ed48afdad59d6278c6b0252c1a0ad0eac98d3e"
