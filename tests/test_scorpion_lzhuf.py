"""Independent native DOS decoder output, including NUL glyphs in fonts."""

import base64
from hashlib import sha256
from pathlib import Path

import pytest

from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.scorpion_bundle import _build_sco_program_documents, _merge_sco_category_documents
from thelpviewer.server.converter.readers.scorpion_lzhuf import ScorpionLzhufDecoder
from thelpviewer.server.converter.readers.scorpion_screens import decode_resource_bank, legacy_screens
from thelpviewer.server.converter.readers.scorpion_legacy_reader import _render_sco_text_line, _sco_decoded_text
from thelpviewer.server.converter.readers.scorpion_dat_reader import _render_payload_lines
from thelpviewer.server.converter.writers.json import HelpJsonRenderer

ROOT = Path("data/sources/Scorpions Cheater DOS")
FONT_HASHES = [
    "1580b25396baf217138be59c340dffb80f9c6cab1faca8913eda27303ebcab0a",
    "675cb1a4c6f45d1367dea5bbe6551f433591390f47f57d1053186be57b53bd0a",
    "10feba13969be6fc94d4a0a6f9226c1555e9bf5e356353bc15c9a4214d813c5e",
    "b84cd163018531be1e79d1136823fdeb329c7f6beac1d11fb57d2835679f6015",
    "87535ee36731ebcc145726277cea12bdabc61f9c9ddf2c03500f90eb6ca51efe",
    "4b33a75c02cafbe148e6ed6ffe5ad7584b382662e6aa323b48070b6958baa566",
    "ddbdcb16e7847b8288586e6a7f88b11cba1e1534693ea39425c01c006508f354",
]
SCREEN_HASHES = {
    6: "d6bd2017a0daa41d6ef7a44e53dc05b00cde59988c1127647b0cd78ec8f9e001",
    7: "99b4fd63e856d01e2d3a96c2a0fe86a7880d915a106efc7124850f034a363336",
    8: "9aaffa7570851abe32893d32d3d7523f93435edd3965e7e7d0c9a17a574eec9f",
    10: "4bb00fe19c3e172495e04513d3382875c007a8c2efd3d2083b14ae280f7cb3b8",
    11: "593b683f78bb54b85b38e8c9ada27fa939762ea4016ab0a944ac60c46183cb99",
    12: "83621a3d8c2d6a4ddb37e6820c642014702bf5a1d3d7dde83b412646a08ae45b",
    13: "d7c020732aa752ca956b132b1263a8ec51eda45295c1cc700a9ff94b6067dfe9",
    14: "31313538ee3da24cc66a7624b4ac12829dbd99e57eface0e42539120465b4651",
}


def directory(version):
    path = ROOT / (f"Scorpions Cheater {version} _shareware_" if version < 9 else f"Scorpions Cheater {version}")
    if not path.is_dir():
        pytest.skip("Original Scorpion sources are not installed")
    return path


def test_nul_symbol_updates_leaf_zero_and_its_ancestors():
    decoder = ScorpionLzhufDecoder(b"", 0)
    decoder._start_huffman()
    root_frequency = decoder.freq[626]
    decoder._update_huffman_tree(0)
    assert decoder.freq[decoder.parents[627]] == 2
    assert decoder.freq[626] == root_frequency + 1


def test_inline_art_keeps_original_glyph_indexes_colors_and_article_row_position():
    raw = b"  \xf0\xd2\x99\xf7\xdb\xe5\xdc\xed\xc4"
    legacy = _render_sco_text_line(_sco_decoded_text(raw), inline_styles=True)
    modern = _render_payload_lines(raw)[0]
    expected = ((32, 7, 0), (32, 7, 0), (0xD2, 10, 0), (0x99, 10, 0),
                (0xDB, 10, 1), (0xDC, 10, 7), (0xC4, 7, 7))
    assert legacy.cells == modern.cells == expected
    # Same Unicode transcription need not mean the same native glyph byte.
    assert _render_payload_lines(b"\xd2\xfb\xfc")[0].cells == ((0xD2, 7, 0), (0xFB, 7, 0), (0xFC, 7, 0))
    source = load_document(directory(14) / "DATATEXT.SCD")
    topic = next(t for t in source.topics if "R010" in t.alias_strings)
    index = next(i for i, line in enumerate(topic.raw_lines) if b"\xdc\xdb\xdb\xdc\xdb\xdd" in line)
    screen = source.text_screens[topic.uhf_content[index][8:-1]]
    assert screen.rows == 1 and screen.cols == 80
    assert screen.text[0].startswith(" " * 41)
    assert len(topic.uhf_content) == len(topic.raw_lines)


@pytest.mark.parametrize("version", [10, 11, 12, 13, 14])
def test_all_seven_fonts_match_the_original_cheat14_decoder(version):
    raw = (directory(version) / "FONT.SCO").read_bytes()
    fonts = decode_resource_bank(raw, b"FNT", 4096)
    assert [sha256(font).hexdigest() for font in fonts] == FONT_HASHES


@pytest.mark.parametrize("version", SCREEN_HASHES)
def test_every_screen_including_blink_cells_matches_native_decoder(version):
    path = directory(version)
    if version < 9:
        screens = [ScorpionLzhufDecoder(p.read_bytes(), 0).decode()[0] for p in sorted(path.glob("SCR*.SCD"))]
    else:
        screens = decode_resource_bank((path / "SCREENS.SCO").read_bytes(), b"SCR", 4000)
    assert sha256(b"".join(screens)).hexdigest() == SCREEN_HASHES[version]


@pytest.mark.parametrize("version,count", [(6, 6), (7, 5), (8, 5), (10, 8), (11, 8), (12, 8), (13, 8), (14, 8)])
def test_companions_share_program_bundle_preserving_original_article_ids(version, count):
    path = directory(version) / "DATATEXT.SCD"
    if not path.is_file():
        path = directory(version) / "DATAHELP.SCD"
    source = load_document(path)
    baseline = _merge_sco_category_documents((path,), (source,), "program")
    merged = _build_sco_program_documents((path,), (source,))
    payload = HelpJsonRenderer(merged, "utf-8").render_document()
    assert len(merged.topics) == len(source.topics) + count
    assert [t.alias_strings for t in merged.topics[:-count]] == [t.alias_strings for t in source.topics]
    assert merged.topics[:-count] == baseline.topics
    assert len(merged.fonts) == 7
    assert len(merged.contents[0].children[-1].children) == count
    for index, topic in enumerate(merged.topics[-count:]):
        screen = merged.text_screens[f"legacy-screen-{index}"]
        assert topic.uhf_content == [f"[screen:legacy-screen-{index}]"]
        assert len(base64.b64decode(payload["text_screens"][f"legacy-screen-{index}"]["data"])) == 4000
        assert screen.font == "program-font"
    assert merged.metadata.get("scorpion_unconverted_screen_names", []) == []
    assert payload["metadata"].get("scorpion_unconverted_screen_names", []) == []


def test_v6_blink_templates_keep_every_original_attribute_and_append_after_static_topics():
    path = directory(6)
    fonts, screens, deferred = legacy_screens(path, 6)
    assert deferred == []
    assert [name for name, _ in screens] == ["SCR3.SCD", "SCR4.SCD", "SCR5.SCD", "SCR1.SCD", "SCR2.SCD", "SCR6.SCD"]
    for name, screen in screens:
        raw = ScorpionLzhufDecoder((path / name).read_bytes(), 0).decode()[0]
        assert base64.b64decode(screen.to_dict()["data"]) == raw
        assert sum(screen.blink) == sum(bool(attr & 128) for attr in raw[1::2])
        assert all(bg <= 7 for _, _, bg in screen.cells)
        assert screen.cell_format == ("dos-text-blink" if any(screen.blink) else "dos-text")


@pytest.mark.parametrize("version", [4, 5])
def test_v4_v5_inline_art_uses_native_default_a_font_without_affecting_titles_or_prose(version):
    path = ROOT / f"Scorpions Cheater {version}" / "DATATEXT.SCO"
    if not path.is_file():
        pytest.skip("Original Scorpion sources are not installed")
    document = load_document(path)
    assert document.fonts["program-font"].data == (path.parent / "FA.SCO").read_bytes()[127:]
    assert len(document.text_screens) == 8
    for topic in document.topics:
        assert len(topic.raw_lines) == len(topic.uhf_content)
        for index, line in enumerate(topic.uhf_content):
            if line.startswith("[screen:"):
                screen = document.text_screens[line[8:-1]]
                assert screen.cols == 80 and screen.rows == 1
                assert screen.font == "program-font"
    payload = HelpJsonRenderer(document).render_document()
    assert all(name.startswith("inline-") for name in payload["text_screens"])


@pytest.mark.parametrize("cut", [4, 8, 20])
def test_truncated_font_payloads_fail_instead_of_using_synthetic_eof_bits(cut):
    raw = (directory(14) / "FONT.SCO").read_bytes()
    with pytest.raises(ValueError, match="truncated"):
        decode_resource_bank(raw[:-cut], b"FNT", 4096)


def test_missing_default_font_does_not_substitute_unicode_or_a_different_font(tmp_path):
    path = directory(8)
    (tmp_path / "SCR1.SCD").write_bytes((path / "SCR1.SCD").read_bytes())
    with pytest.raises(ValueError, match="missing"):
        legacy_screens(tmp_path, 8)


@pytest.mark.parametrize("name", ["FA.SCO", "SCR1.SCD"])
def test_companion_resources_cannot_read_outside_sources_through_symlinks(tmp_path, name):
    source = directory(8)
    (tmp_path / "FA.SCO").write_bytes((source / "FA.SCO").read_bytes())
    (tmp_path / "SCR1.SCD").write_bytes((source / "SCR1.SCD").read_bytes())
    (tmp_path / name).unlink()
    (tmp_path / name).symlink_to((source / name).resolve())
    with pytest.raises(ValueError, match="symbolic"):
        legacy_screens(tmp_path, 8)


@pytest.mark.parametrize("raw", [b"FNT", b"FNT\x00\x10\x00\x00", b"FNT\x00\x20\x00\x00", b"bad"])
def test_invalid_resource_headers_and_empty_payloads_are_rejected(raw):
    with pytest.raises(ValueError):
        decode_resource_bank(raw, b"FNT", 4096)
