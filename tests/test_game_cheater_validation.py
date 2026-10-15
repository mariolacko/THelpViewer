"""Pc-Fand memo boundaries and incomplete databases must not lose text."""

from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.readers.game_cheater import (
    GameCheaterReader, _decode_text_block_bytes, _read_text_block_bytes, _records,
    is_game_cheater_database,
)
from test_game_cheater_reader import _TextFile, _table, _write_fixture


def memo(payload):
    # Follow native RdWr: use a pointer only when N exceeds the WHOLE page
    # remainder. The last four cells of a final page are ordinary payload.
    pages = [512, 1536, 1024, *range(2048, 2048 + 512*(len(payload)//506 + 1), 512)]
    data = bytearray(max(pages) + 512)
    struct.pack_into("<H", data, 512, len(payload))
    encoded = bytes(value ^ 0xAA for value in payload)
    position, consumed, next_index = 514, 0, 1
    while consumed < len(payload):
        rest = 512 - position % 512
        remaining = len(payload) - consumed
        count = rest if remaining <= rest else rest - 4
        count = min(count, remaining)
        data[position:position+count] = encoded[consumed:consumed+count]
        consumed += count
        if consumed < len(payload):
            target = pages[next_index]
            next_index += 1
            struct.pack_into("<I", data, position+count, target)
            position = target
    return bytes(data)


@pytest.mark.parametrize("length", [0, 1, 505, 506, 507, 508, 509, 510, 511,
                                    1014, 1015, 1016, 1017, 1018, 1019, 1527, 64645])
def test_memo_chain_keeps_complete_final_page_payload_and_noncontiguous_pages(length):
    payload = b"X" * length
    assert _read_text_block_bytes(memo(payload), 512) == payload


@pytest.mark.parametrize("length", [0, 506, 507, 508, 509, 510, 511, 1014, 1018, 1019])
def test_database_fixture_writer_uses_the_native_terminal_page_capacity(length):
    text = _TextFile()
    text.add("prefix")
    offset = text.add_long("X" * length)
    assert _read_text_block_bytes(bytes(text.data), offset) == b"X" * length
    assert len(text.data) == offset + (1 if length <= 510 else 2 if length <= 1018 else 3) * 512


def test_absent_memo_and_assigned_empty_memo_remain_distinct():
    assert _read_text_block_bytes(b"", 0) is None
    assert _read_text_block_bytes(memo(b""), 512) == b""


def test_declared_payload_keeps_nul_bytes_including_at_its_end():
    payload = b"A\0B\0\0"
    assert _read_text_block_bytes(memo(payload), 512) == payload


@pytest.mark.parametrize("offset", [-1, 1, 511, 1023, 1024])
def test_bad_memo_header_is_not_absent_text(offset):
    with pytest.raises(ValueError, match="memo header"):
        _read_text_block_bytes(bytes(1024), offset)


def test_truncated_short_memo_does_not_become_empty_text():
    data = bytearray(514)
    struct.pack_into("<H", data, 512, 1)
    with pytest.raises(ValueError, match="memo text"):
        _read_text_block_bytes(bytes(data), 512)


def test_truncated_continuation_pointer_is_not_a_page_end():
    data = bytearray(memo(b"X"*511)[:1023])
    with pytest.raises(ValueError, match="memo page pointer"):
        _read_text_block_bytes(bytes(data), 512)


@pytest.mark.parametrize("target", [0, 256, 513, 1025, 0xFFFFFFFF])
def test_invalid_continuation_pointer_is_not_empty_text(target):
    data = bytearray(memo(b"X"*511))
    struct.pack_into("<I", data, 1020, target)
    with pytest.raises(ValueError, match="memo continuation page"):
        _read_text_block_bytes(bytes(data), 512)


@pytest.mark.parametrize("length,pointer", [(511, 1020), (1019, 2044)])
def test_cycle_to_the_first_page_fails_even_if_remaining_text_would_fit(length, pointer):
    data = bytearray(memo(b"X"*length))
    struct.pack_into("<I", data, pointer, 512)
    with pytest.raises(ValueError, match="Cyclic Pc-Fand"):
        _read_text_block_bytes(bytes(data), 512)


@pytest.mark.parametrize("count", [2, -2])
def test_declared_record_count_is_not_clamped_to_the_available_file(count):
    with pytest.raises(ValueError, match="declared 2 records, available 1"):
        _records(_table([bytes(55)], 55, count=count), 55)


def test_zero_count_does_not_import_unused_record_slots():
    assert _records(_table([bytes(55)], 55, count=0), 55) == []
    assert _records(_table([b"A"*55, b"B"*55], 55, count=-1), 55) == [b"A"*55]


def test_partial_record_is_recognized_as_a_damaged_table_not_another_format():
    data = _table([bytes(111)], 111)[:-1]
    assert is_game_cheater_database(Path("CHEATDBS.000"), data)
    with pytest.raises(ValueError, match="table record"):
        _records(data, 111)


@pytest.mark.parametrize("name", ["FIRMY.000", "FIRMY.T00", "GCNETADR.000", "GCNETADR.T00",
                                  "GCHLP.000", "GCHLP.T00", "DBSNFO.000", "DBSNFO.T00"])
def test_present_optional_section_requires_both_files(tmp_path, name):
    path = _write_fixture(tmp_path / "source")
    (path.parent / name).unlink()
    with pytest.raises(ValueError, match="Incomplete Pc-Fand"):
        GameCheaterReader(source_path=path).read_path(path)


def test_fully_absent_optional_section_can_still_be_omitted(tmp_path):
    path = _write_fixture(tmp_path / "source")
    for name in ["FIRMY.000", "FIRMY.T00"]:
        (path.parent / name).unlink()
    document = GameCheaterReader(source_path=path).read_path(path)
    assert "Firmy" not in [node.label for node in document.contents]


def test_mixed_frames_and_literal_markup_are_not_rewritten_by_table_appearance():
    text = "╔══╗\r\n│[literal]│\r\n├──┤\r\n└──┘\r\n[after]".encode("cp852")
    decoded = _decode_text_block_bytes(text)
    assert decoded.plain == "╔══╗\n│[literal]│\n├──┤\n└──┘\n[after]"
    assert decoded.uhf == "╔══╗\n│[[literal]│\n├──┤\n└──┘\n[[after]"


def test_original_tables_and_every_assigned_memo_remain_readable():
    root = Path("data/sources/Game-Cheater/Game-Cheater 9.02")
    if not root.is_dir():
        pytest.skip("Original Game-Cheater database not available")
    datasheet = Path("docs/Formats/Game Cheater PC-Fand Format.md").read_text()
    example = datasheet.split("Boundary-checked payload algorithm", 1)[1].split("```python\n", 1)[1].split("```", 1)[0]
    reference = {}
    exec(compile(example, "<datasheet memo decoder>", "exec"), reference)
    layouts = {
        "CHEATDBS": (111, [0x33, 0x37], 3301),
        "FIRMY": (55, [0x33], 142),
        "GCNETADR": (143, [0x8B], 56),
        "GCHLP": (39, [0x23], 531),
        "DBSNFO": (42, [0x0E, 0x12, 0x16, 0x1A, 0x1E, 0x26], 1),
    }
    assigned = 0
    for stem, (size, fields, count) in layouts.items():
        records = _records((root / f"{stem}.000").read_bytes(), size)
        assert len(records) == count
        text = (root / f"{stem}.T00").read_bytes()
        for record in records:
            for field in fields:
                offset = struct.unpack_from("<I", record, field)[0]
                decoded = _read_text_block_bytes(text, offset)
                assert reference["read_text_block"](text, offset) == decoded
                assert (decoded is None) == (offset == 0)
                assigned += bool(offset)
    assert assigned == 7061
    path = root / "CHEATDBS.000"
    document = GameCheaterReader(source_path=path).read_path(path)
    assert len(document.topics) == 3991
    assert [len(node.children) for node in document.contents] == [3301, 142, 56, 486, 6]
    assert sum(topic.redirect_context is not None for topic in document.topics) == 103
    assert sum(line.count("[link:") for topic in document.topics for line in topic.uhf_content) == 669


@pytest.mark.parametrize("filename,cut", [("CHEATDBS.T00", 512), ("FIRMY.000", -1)])
def test_bad_source_cannot_replace_published_bundles_and_retry_is_safe(tmp_path, filename, cut):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    path = _write_fixture(sources / "Game-Cheater 9.02")
    build_help_groups(["game-cheater"], sources, helps,
                      product_keys=["game-cheater"], keep_products=["game-cheater"])
    published = {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    damaged_path = path.parent / filename
    original = damaged_path.read_bytes()
    damaged_path.write_bytes(original[:cut])
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["game-cheater"], sources, helps,
                          product_keys=["game-cheater"], keep_products=["game-cheater"])
    assert published == {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    damaged_path.write_bytes(original)
    result = build_help_groups(["game-cheater"], sources, helps,
                               product_keys=["game-cheater"], keep_products=["game-cheater"])
    assert result["bundles"] == 5 and Path(result["backup"]).is_dir()
    assert damaged_path.read_bytes() == original
