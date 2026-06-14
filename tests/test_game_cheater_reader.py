from __future__ import annotations

import gzip
import json
import struct
from pathlib import Path

from thelpviewer.converter.exporter import detect_format_handler, iter_help_files, load_document
from thelpviewer.converter.writers.bundle import export_bundle_tree


def _xor_fixed(text: str, size: int) -> bytes:
    decoded = text.encode("cp852")[:size].ljust(size, b"\x00")
    return bytes(value ^ 0xAA for value in decoded)


class _TextFile:
    def __init__(self) -> None:
        self.data = bytearray(512)

    def add(self, text: str) -> int:
        offset = len(self.data)
        encoded = bytes(value ^ 0xAA for value in text.encode("cp852"))
        self.data.extend(struct.pack("<H", len(encoded)))
        self.data.extend(encoded)
        return offset

    def add_long(self, text: str) -> int:
        encoded = bytes(value ^ 0xAA for value in text.encode("cp852"))
        padding = (-len(self.data)) % 512
        self.data.extend(bytes(padding))
        offset = len(self.data)
        page_count = 1
        remaining_after_first = max(0, len(encoded) - 506)
        if remaining_after_first:
            page_count += (remaining_after_first + 507) // 508
        self.data.extend(bytes(page_count * 512))
        struct.pack_into("<H", self.data, offset, len(encoded))

        source_position = 0
        page = offset
        payload_start = page + 2
        payload_capacity = 506
        while len(encoded) - source_position > payload_capacity:
            end = source_position + payload_capacity
            self.data[payload_start : payload_start + payload_capacity] = encoded[source_position:end]
            next_page = page + 512
            struct.pack_into("<I", self.data, page + 508, next_page)
            source_position = end
            page = next_page
            payload_start = page
            payload_capacity = 508
        tail = encoded[source_position:]
        self.data[payload_start : payload_start + len(tail)] = tail
        return offset


def _table(records: list[bytes], record_size: int, *, count: int | None = None) -> bytes:
    raw_count = len(records) if count is None else count
    return struct.pack("<iH", raw_count, record_size) + b"".join(records)


def _write_pair(root: Path, stem: str, records: list[bytes], record_size: int, text: _TextFile) -> None:
    (root / f"{stem}.000").write_bytes(_table(records, record_size))
    (root / f"{stem}.T00").write_bytes(text.data)


def _write_fixture(root: Path) -> Path:
    root.mkdir(parents=True)

    text = _TextFile()
    source_offset = text.add("WWW.CHEATY.SK")
    long_tail = "x" * 540
    cheat_offset = text.add_long(
        "První \x13podtržený\x13 řádek\r\n\r\n"
        "DDDLLLOOOUUUHHHÁÁÁ ─\r\nTřetí řádek " + long_tail
    )
    cheat = bytearray(111)
    cheat[1:0x33] = _xor_fixed("Žhavá hra", 50)
    struct.pack_into("<I", cheat, 0x33, source_offset)
    struct.pack_into("<I", cheat, 0x37, cheat_offset)
    struct.pack_into(">H", cheat, 0x3B, 902)
    cheat[0x3D:0x6F] = _xor_fixed("Český vydavatel", 50)
    primary = root / "CHEATDBS.000"
    primary.write_bytes(_table([bytes(cheat)], 111, count=-123))
    (root / "CHEATDBS.T00").write_bytes(text.data)

    text = _TextFile()
    body_offset = text.add("E-mail: firma@example.test")
    record = bytearray(55)
    record[1:0x33] = _xor_fixed("Firma", 50)
    struct.pack_into("<I", record, 0x33, body_offset)
    _write_pair(root, "FIRMY", [bytes(record)], 55, text)

    text = _TextFile()
    body_offset = text.add("Popis odkazu")
    record = bytearray(143)
    record[1:0x3D] = _xor_fixed("Web", 60)
    record[0x3D:0x8B] = _xor_fixed("https://example.test", 78)
    struct.pack_into("<I", record, 0x8B, body_offset)
    _write_pair(root, "GCNETADR", [bytes(record)], 143, text)

    text = _TextFile()

    def help_record(title: str, body: str) -> bytes:
        record = bytearray(39)
        record[0:0x23] = _xor_fixed(title, 35)
        struct.pack_into("<I", record, 0x23, text.add(body))
        return bytes(record)

    _write_pair(
        root,
        "GCHLP",
        [
            help_record("Ovládání", "Viz.: \x13O programu\x13"),
            help_record("!! ZDE ZAČÍNÁ INTERNÍ HELP FANDU !!", "Interní značka"),
            help_record("FMEdit", "Interní nápověda"),
            help_record("!! ZDE KONČÍ INTERNÍ HELP FANDU !!", "Interní značka"),
            help_record("O programu", "Text o programu"),
        ],
        39,
        text,
    )

    text = _TextFile()
    info_offset = text.add(
        "╔════╗\r\n"
        "║Info║\r\n"
        "├────┤\r\n"
        "│Text│\r\n"
        "└────┘"
    )
    record = bytearray(42)
    struct.pack_into(">H", record, 0x0C, 902)
    struct.pack_into("<I", record, 0x26, info_offset)
    _write_pair(root, "DBSNFO", [bytes(record)], 42, text)

    (root / "GCPRM.000").write_bytes(_table([bytes(100)], 100))
    return primary


def test_game_cheater_reader_loads_all_user_facing_tables(tmp_path: Path) -> None:
    primary = _write_fixture(tmp_path / "Game-Cheater 9.02")

    handler = detect_format_handler(primary)
    assert handler is not None
    assert handler.name == "game-cheater"
    assert iter_help_files(primary.parent) == [primary]

    document = load_document(primary)
    assert document.format_name == "game-cheater"
    assert [node.label for node in document.contents] == [
        "Cheaty",
        "Firmy",
        "Internetové adresy",
        "Nápověda",
        "Informace",
    ]
    assert [topic.names[0] for topic in document.topics] == [
        "Žhavá hra",
        "Firma",
        "Web",
        "Ovládání",
        "O programu",
        "Informace o databázi",
    ]
    cheat = document.topics[0]
    assert "" in cheat.uhf_content
    assert "První [u]podtržený[/u] řádek" in cheat.uhf_content
    assert "DDDLLLOOOUUUHHHÁÁÁ ─" in cheat.uhf_content
    assert any(line.startswith("Třetí řádek ") and line.endswith("x" * 540) for line in cheat.uhf_content)
    assert not any("¬" in line for line in cheat.uhf_content)
    assert [(tag.key, tag.label, tag.value) for tag in cheat.tags] == [
        ("publisher", "Vydavatel", "Český vydavatel"),
        ("source", "Zdroj", "WWW.CHEATY.SK"),
    ]
    assert not any(line.startswith(("Vydavatel:", "Zdroj:")) for line in cheat.uhf_content)
    assert "FMEdit" not in [topic.names[0] for topic in document.topics]
    assert document.topics[3].uhf_content == ["Viz.: [link:topic=5][u]O programu[/u][/link]"]
    assert document.topics[5].uhf_content == [
        "╔════╗",
        "║Info║",
        "╠════╣",
        "║Text║",
        "╚════╝",
    ]
    assert document.metadata["database_version"] == "9.02"
    assert len(document.metadata["source_files"]) == 11


def test_game_cheater_bundle_has_stable_name(tmp_path: Path) -> None:
    source_root = tmp_path / "sources"
    _write_fixture(source_root / "Game-Cheater 9.02")
    output = tmp_path / "helps"

    results = export_bundle_tree(source_root, output, layout="helps")

    assert len(results) == 5
    bundles = {
        result.json_path.name: result.json_path
        for result in results
    }
    assert set(bundles) == {
        "cheaty.json.gz",
        "firmy.json.gz",
        "internetove-adresy.json.gz",
        "napoveda.json.gz",
        "informace.json.gz",
    }

    cheats = json.loads(gzip.decompress(bundles["cheaty.json.gz"].read_bytes()))
    assert cheats["metadata"]["name"] == "Game-Cheater 9.02 - Cheaty"
    assert cheats["metadata"]["source"]["filename"] == "CHEATDBS.000"
    assert len(cheats["topics"]) == 1
    assert cheats["topics"]["1"]["tags"] == [
        {"key": "publisher", "value": "Český vydavatel", "label": "Vydavatel"},
        {"key": "source", "value": "WWW.CHEATY.SK", "label": "Zdroj"},
    ]

    help_payload = json.loads(gzip.decompress(bundles["napoveda.json.gz"].read_bytes()))
    assert help_payload["metadata"]["name"] == "Game-Cheater 9.02 - Nápověda"
    assert help_payload["metadata"]["source"]["filename"] == "GCHLP.000"
    assert help_payload["metadata"]["show_topic_titles"] is False
    assert set(help_payload["topics"]) == {"4", "5"}
    assert help_payload["topics"]["4"]["content"] == [
        "Viz.: [link:topic=5][u]O programu[/u][/link]"
    ]

    expected_sources = {
        "firmy.json.gz": "FIRMY.000",
        "internetove-adresy.json.gz": "GCNETADR.000",
        "informace.json.gz": "DBSNFO.000",
    }
    for bundle_name, source_name in expected_sources.items():
        payload = json.loads(gzip.decompress(bundles[bundle_name].read_bytes()))
        assert payload["metadata"]["source"]["filename"] == source_name

    catalog = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
    assert {item["topics"] for item in catalog} == {1, 2}
    assert next(item for item in catalog if item["file"].endswith("napoveda.json.gz"))["topics"] == 2
