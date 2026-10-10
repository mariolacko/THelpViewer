from pathlib import Path

from thelpviewer.converter.readers import scorpion_dat_reader as scorpion_dat_module
from thelpviewer.converter.readers import scorpion_legacy_reader as scorpion_legacy_module
from thelpviewer.converter.readers import scorpion_legacy_v1x as scorpion_legacy_v1x_module
from thelpviewer.converter.readers import scorpion_legacy_v4x as scorpion_legacy_v4x_module
from thelpviewer.converter.readers import scorpion_legacy_v6x as scorpion_legacy_v6x_module
from thelpviewer.converter.exporter import detect_format_handler
from thelpviewer.converter.readers.scorpion_dat_parser import SCORPION_DAT_SIGNATURE
from thelpviewer.converter.readers.scorpion_dat_reader import (
    ScorpionDatReader,
    scorpion_dat_reader_class_for_path,
)
from thelpviewer.converter.readers.scorpion_legacy_reader import (
    ScorpionLegacyReader,
    is_scorpion_legacy_binary,
    scorpion_legacy_reader_class_for_path,
    scorpion_legacy_profile_for_path,
    scorpion_version_hint_from_path,
)


RAR4_SIGNATURE = b"Rar!\x1A\x07\x00"


def _rar_block(head_type: int, flags: int, body: bytes) -> bytes:
    return b"\x00\x00" + bytes([head_type]) + flags.to_bytes(2, "little") + (7 + len(body)).to_bytes(2, "little") + body


def _rar_main_header() -> bytes:
    return _rar_block(0x73, 0x0000, b"\x00" * 6)


def _rar_file_header(
    name: str,
    *,
    pack_size: int = 0,
    unp_size: int = 0,
    method: int = 0x35,
    attributes: int = 0x20,
    flags: int = 0x8000,
) -> bytes:
    name_bytes = name.encode("latin-1")
    body = b"".join(
        (
            pack_size.to_bytes(4, "little"),
            unp_size.to_bytes(4, "little"),
            b"\x00",
            b"\x00" * 4,
            b"\x00" * 4,
            bytes([20, method]),
            len(name_bytes).to_bytes(2, "little"),
            attributes.to_bytes(4, "little"),
            name_bytes,
        )
    )
    return _rar_block(0x74, flags, body)


def _rar_end_header() -> bytes:
    return _rar_block(0x7B, 0x0000, b"")


def _build_legacy_mz_sfx(*blocks: bytes, stub_size: int = 64) -> bytes:
    header = bytearray(stub_size)
    header[:2] = b"MZ"
    header[0x02:0x04] = stub_size.to_bytes(2, "little")
    header[0x04:0x06] = (1).to_bytes(2, "little")
    header[0x08:0x0A] = (stub_size // 16).to_bytes(2, "little")
    return bytes(header) + RAR4_SIGNATURE + b"".join(blocks)


def _field(name: bytes, value: bytes) -> bytes:
    return name + len(value).to_bytes(4, "big") + value


def _record(name: str, payload: bytes) -> bytes:
    return b"".join(
        (
            _field(b"propDATE", b"2000-01-01"),
            _field(b"propNAME", name.encode("latin-1")),
            _field(b"propORIG", b"c:\\scorpion\\file.bin"),
            b"DATA",
            len(payload).to_bytes(4, "big"),
            (0).to_bytes(4, "big", signed=True),
            payload,
        )
    )


def _build_modern_dat(*records: bytes) -> bytes:
    return SCORPION_DAT_SIGNATURE + b"".join(records)


def _build_fixed_width_sco_stream(payload: bytes) -> bytes:
    table = bytearray()
    for symbol in range(256):
        table.extend((symbol << 8).to_bytes(2, "little"))
    return b"SCORPION\x00\x01" + bytes(table) + b"\x00" * 0x100 + payload


def test_scorpion_legacy_reader_detects_oldest_dat_release():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1/DATA.DAT")
    payload = b"MZ" + b"\x00" * 62

    handler = detect_format_handler(path, payload)
    assert handler is not None
    assert handler.name == "scorpion-legacy"
    assert is_scorpion_legacy_binary(path, payload)

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.format_name == "scorpion-legacy"
    assert document.metadata["scorpion_version"] == "1"
    assert document.metadata["scorpion_decoder"] == "scorpion-v1-dat-exe"
    assert document.topics[0].names == ["Scorpions Cheater 1.0"]


def test_scorpion_legacy_reader_parses_mz_sfx_archive_members():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1/DATA.DAT")
    payload = _build_legacy_mz_sfx(
        _rar_main_header(),
        _rar_file_header("VGACS.COM", unp_size=40548),
        _rar_file_header("MENU2.EXE", unp_size=86526),
        _rar_end_header(),
    )

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_wrapper"] == "dos-mz-sfx-rar"
    assert document.metadata["archive_member_count"] == 2
    assert [topic.names[0] for topic in document.topics] == [
        "Scorpions Cheater 1.0",
        "VGACS.COM",
        "MENU2.EXE",
    ]


def test_scorpion_legacy_reader_builds_structured_topics_for_version_1_release():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1/DATA.DAT")
    payload = _build_legacy_mz_sfx(
        _rar_main_header(),
        _rar_file_header("VGACS.COM", unp_size=40548),
        _rar_file_header("MENU2.EXE", unp_size=86526),
        _rar_end_header(),
    )

    structured_payload = b"\x90" * 256 + b"\x00" + b"\x00".join(
        scorpion_legacy_module._encode_legacy_text(text)
        for text in [
            "QUARANTINE",
            "Level kódy:",
            "2- OMNICORP IS ALL KNOWING",
            "THEME PARK",
            "Jako přezdívku napište Horza, pak:",
            "Ctrl+C  -Vám přidá peníze",
            "TIE FIGHTER",
            "V souboru FLIGHT.OVL změňte 36234 na 01.",
            "QUARANTINE",
            "QUEST FOR GLORY I",
            "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
            "SCORPIONS CHEATER V.1.00 byl vyroben v dubnu 96'\n\n Tato první verze je freeware.",
            "Verze 1.00",
            "Pro Scorpins Software vyrobili",
            "Honza Svatos Jr.\n                   & \n             Marek Pscolka\n\n                 04/96",
            "Pro pohyb:",
            "[%c] nahoru           [%c] dolu",
            "ESC odchod do DOSu   [F10] tisk",
            "A-Z skok na pismeno  [F1] o programu",
            "ENTER  aktivace",
            "%s",
        ]
    ) + b"\x00" * 64

    original = scorpion_legacy_module._extract_overlay_members
    scorpion_legacy_module._extract_overlay_members = lambda _overlay: {
        "VGACS.COM": b"VGACS!",
        "MENU2.EXE": structured_payload,
    }
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)
    finally:
        scorpion_legacy_module._extract_overlay_members = original

    assert document.metadata["scorpion_wrapper"] == "dos-mz-sfx-rar"
    assert document.metadata["scorpion_parser"] == "v1-menu2-string-table"
    assert document.metadata["scorpion_reader_class"] == "ScorpionV1Reader"
    assert document.metadata["parsed_member"] == "MENU2.EXE"
    assert document.metadata["help_contents_topic_id"] == 0
    assert document.topics[0].is_help_contents
    assert document.contents[0].topic_id == 0
    assert [node.label for node in document.contents[0].children] == ["O programu", "Ovládání", "Cheaty"]
    assert document.contents[0].children[2].children[0].label == "QUARANTINE"
    assert [topic.names[0] for topic in document.topics[:5]] == [
        "Scorpions Cheater 1.0",
        "O programu",
        "Ovládání",
        "QUARANTINE",
        "THEME PARK",
    ]
    assert "SCORPIONS CHEATER V.1.00 byl vyroben v dubnu 96'" in document.topics[1].uhf_content
    assert "ESC odchod do DOSu   [[F10] tisk" in document.topics[2].uhf_content
    assert "Level kódy:" in document.topics[3].uhf_content
    assert "Ctrl+C  -Vám přidá peníze" in document.topics[4].uhf_content


def test_v1_sample_topic_parser_keeps_compact_code_rows_inside_parent_topic():
    topics = scorpion_legacy_v1x_module._build_v1_sample_topics(
        [
            "QUARANTINE",
            "Level kódy:",
            "BATTLE ISLE '93",
            "Level kódy pro jednoho hráče:",
            "01 -LUMIT     13 -FINXT",
            "B113 -AIDCJF             E416 -EIABDC              H725 -CDAJKE",
            "C200 -v manuálu          F518 -AEDKGB              I822 -GDEAJF",
            "DARK FORCES",
            "LAPOSTAL  - dodá energii, štíty, zbraně a střelivo",
            "QUARANTINE",
        ]
    )

    assert [title for title, _lines in topics] == ["QUARANTINE", "BATTLE ISLE '93", "DARK FORCES"]
    battle_isle_lines = dict(topics)["BATTLE ISLE '93"]
    assert "B113 -AIDCJF             E416 -EIABDC              H725 -CDAJKE" in battle_isle_lines
    assert "C200 -v manuálu          F518 -AEDKGB              I822 -GDEAJF" in battle_isle_lines


def test_v1_sample_topic_parser_normalizes_spaced_titles():
    topics = scorpion_legacy_v1x_module._build_v1_sample_topics(
        [
            "QUARANTINE",
            "Level kódy:",
            "S Y S T E M   S H O C K",
            "cheat line",
            "A - T R A I N",
            "another cheat line",
            "F 2 9   R E T A L I A T O R",
            "last cheat line",
            "QUARANTINE",
        ]
    )

    assert [title for title, _lines in topics] == ["QUARANTINE", "SYSTEM SHOCK", "A-TRAIN", "F29 RETALIATOR"]


def test_v1_sample_topic_parser_keeps_uppercase_body_rows_inside_parent_topic():
    topics = scorpion_legacy_v1x_module._build_v1_sample_topics(
        [
            "QUARANTINE",
            "JAZZ JACKRABBIT",
            "P-BREAKSPACE-CHECK   =",
            "END     - INTERESTED",
            "F E L I X",
            "Některé kódy:",
            "FELIX     MUSIC      EMERALD    MAGIC      HEADACHE",
            "ORANGE    PANTHER    PORCHE     DUNGEON    PARADISE",
            "QUARANTINE",
        ]
    )

    assert [title for title, _lines in topics] == ["JAZZ JACKRABBIT", "FELIX"]
    assert dict(topics)["JAZZ JACKRABBIT"] == ["P-BREAKSPACE-CHECK   =", "END     - INTERESTED"]
    assert dict(topics)["FELIX"] == [
        "Některé kódy:",
        "FELIX     MUSIC      EMERALD    MAGIC      HEADACHE",
        "ORANGE    PANTHER    PORCHE     DUNGEON    PARADISE",
    ]


def test_v1_topic_parser_keeps_colon_led_code_lists_inside_parent_topic():
    topics, stop_index = scorpion_legacy_v1x_module._scan_v1_topic_stream(
        [
            "BLOODNET",
            "Kódy do virtuální reality:",
            "HOPE",
            "NOUN (SZ UP BA HM KC R ND PM CB)",
            "MEDIUM",
            "TTHEAT",
            "MAJOR",
            "BLACKWOOD",
            "KANSAS",
            "MOZART",
            "SOFTBALL(NINJA)",
            "ZARATHUSTRA",
            "BATTLE ISLE '93",
            "Level kódy pro jednoho hráče:",
            "01 -LUMIT     13 -FINXT",
            "BLOODNET",
        ],
        start_index=0,
        directory_title_keys={
            scorpion_legacy_v1x_module._v1_directory_title_key("BLOODNET"),
            scorpion_legacy_v1x_module._v1_directory_title_key("BATTLE ISLE 93'"),
        },
    )

    assert stop_index == 15
    assert [title for title, _lines in topics] == ["BLOODNET", "BATTLE ISLE '93"]
    assert dict(topics)["BLOODNET"] == [
        "Kódy do virtuální reality:",
        "HOPE",
        "NOUN (SZ UP BA HM KC R ND PM CB)",
        "MEDIUM",
        "TTHEAT",
        "MAJOR",
        "BLACKWOOD",
        "KANSAS",
        "MOZART",
        "SOFTBALL(NINJA)",
        "ZARATHUSTRA",
    ]


def test_v1_topic_parser_splits_directory_backed_suffix_titles():
    topics, _stop_index = scorpion_legacy_v1x_module._scan_v1_topic_stream(
        [
            "D E N A R I S",
            "Pro tréningový mód:",
            "stiskněte Z",
            "D O C T O R   W H O:   D A L L E K   A T T A C K",
            "Při hře napište:",
            "JAMES BOND AND OLIVER REED WERE NEVER GOOD SINGERS",
            "D O G S   O F   W A R",
            "Při hře napište: TIMBO.",
        ],
        start_index=0,
        directory_title_keys={
            scorpion_legacy_v1x_module._v1_directory_title_key("DENARIS"),
            scorpion_legacy_v1x_module._v1_directory_title_key("DOCTOR WHO"),
            scorpion_legacy_v1x_module._v1_directory_title_key("DOGS OF WAR"),
        },
    )

    assert [title for title, _lines in topics] == [
        "DENARIS",
        "DOCTOR WHO: DALLEK ATTACK",
        "DOGS OF WAR",
    ]
    assert dict(topics)["DENARIS"] == ["Pro tréningový mód:", "stiskněte Z"]


def test_v1_topic_parser_stops_before_footer_art_and_directory():
    topics = scorpion_legacy_v1x_module._build_v1_topic_stream(
        [
            "X - M A S   L E M M N I G S   D E M O",
            "Jako kód úrovně napište SNOWFLAKES.",
            "Jiný kód: VERSIONNUM; dozvíte se číslo verze.",
            "┌───┬───┬────┬───┐┌───┬─┬────┬──┬─┬───┐",
            "└┘└┘└┘┘ └│ ┴└┘┘└└┘",
            "VεRZε  |.ΘΘ",
            "7 - UP",
            "A-TRAIN",
            "AFTERBURNER",
            "BLOODNET",
            "DOOM",
            "FELIX",
            "LOGICAL",
            "QUARANTINE",
            "X - M A S   L E M M N I G S   D E M O",
        ],
        start_index=0,
    )

    assert topics == [
        (
            "X-MAS LEMMNIGS DEMO",
            [
                "Jako kód úrovně napište SNOWFLAKES.",
                "Jiný kód: VERSIONNUM; dozvíte se číslo verze.",
            ],
        )
    ]


def test_scorpion_legacy_reader_normalizes_embedded_archive_paths_for_version3():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3/CHEATER.DAT")
    payload = _build_legacy_mz_sfx(
        _rar_main_header(),
        _rar_file_header("_", attributes=0x10),
        _rar_file_header("_\\NAVODY.1", unp_size=14016),
        _rar_end_header(),
    )

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_decoder"] == "scorpion-v3-exe-dat"
    assert document.metadata["archive_member_count"] == 1
    assert document.topics[1].names == ["NAVODY.1"]
    assert "_\\NAVODY.1" in document.topics[1].alias_strings


def test_scorpion_v3_reader_parses_bracketed_member_topics():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3/CHEATER.DAT")
    payload = _build_legacy_mz_sfx(
        _rar_main_header(),
        _rar_file_header("_", attributes=0x10),
        _rar_file_header("_\\TEXTY.1", unp_size=128),
        _rar_file_header("_\\SCC.SC", unp_size=96),
        _rar_end_header(),
    )

    texty_payload = (
        "[0101]\r\n"
        "                              B A T T L E   B E A S T\r\n"
        "ULTIMATE CHEAT CODE: YOYOYO\r\n"
        "END\r\n"
        "[0001]\r\n"
        "                                H E R E T I C\r\n"
        "- IDDQD =smrt\r\n"
        "END\r\n"
    ).encode("ascii")
    scc_payload = (
        "BATTLE BEAST,[0101]-\r\n"
        "HERETIC,[0001]-\r\n"
    ).encode("ascii")

    original = scorpion_legacy_module._extract_overlay_members
    scorpion_legacy_module._extract_overlay_members = lambda _overlay: {
        "TEXTY.1": texty_payload,
        "_\\TEXTY.1": texty_payload,
        "SCC.SC": scc_payload,
        "_\\SCC.SC": scc_payload,
    }
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)
    finally:
        scorpion_legacy_module._extract_overlay_members = original

    assert document.metadata["scorpion_parser"] == "v3-rar-member-topics"
    assert document.metadata["scorpion_reader_class"] == "ScorpionV3Reader"
    assert document.metadata["parsed_topic_count"] == 2
    assert [topic.names[0] for topic in document.topics] == ["BATTLE BEAST", "HERETIC"]
    assert [topic.context_id for topic in document.topics] == [101, 1]
    assert document.topics[0].uhf_content == ["BATTLE BEAST", "ULTIMATE CHEAT CODE: YOYOYO"]
    assert document.topics[1].uhf_content == ["HERETIC", "- IDDQD =smrt"]
    assert document.contents[0].label == "Scorpions Cheater 3"
    assert [child.label for child in document.contents[0].children] == ["Cheaty"]
    assert [child.label for child in document.contents[0].children[0].children] == ["BATTLE BEAST", "HERETIC"]


def test_scorpion_v3_reader_does_not_apply_cheat_index_titles_to_jokes():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3/CHEATER.DAT")
    payload = _build_legacy_mz_sfx(
        _rar_main_header(),
        _rar_file_header("_", attributes=0x10),
        _rar_file_header("_\\TEXTY.1", unp_size=128),
        _rar_file_header("_\\VTIPSCC.SC", unp_size=128),
        _rar_file_header("_\\SCC.SC", unp_size=96),
        _rar_end_header(),
    )

    texty_payload = (
        "[0001]\r\n"
        "                                H E R E T I C\r\n"
        "- IDDQD =smrt\r\n"
        "END\r\n"
    ).encode("ascii")
    joke_payload = (
        "[0001]\r\n"
        "                                  R E T E Z\r\n"
        "Vtip text\r\n"
        "END\r\n"
    ).encode("ascii")
    scc_payload = "HERETIC,[0001]-\r\n".encode("ascii")

    original = scorpion_legacy_module._extract_overlay_members
    scorpion_legacy_module._extract_overlay_members = lambda _overlay: {
        "TEXTY.1": texty_payload,
        "_\\TEXTY.1": texty_payload,
        "VTIPSCC.SC": joke_payload,
        "_\\VTIPSCC.SC": joke_payload,
        "SCC.SC": scc_payload,
        "_\\SCC.SC": scc_payload,
    }
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)
    finally:
        scorpion_legacy_module._extract_overlay_members = original

    assert [topic.names[0] for topic in document.topics] == ["HERETIC", "RETEZ"]
    assert [topic.context_id for topic in document.topics] == [1, 0x200001]
    assert [child.label for child in document.contents[0].children] == ["Cheaty", "Vtipy"]


def test_scorpion_legacy_reader_preserves_internal_blank_lines():
    assert scorpion_legacy_v1x_module._normalize_v1_5_section_entries(
        [
            "První řádek\n\nDruhý řádek",
            "Třetí řádek",
        ]
    ) == ["První řádek", "", "Druhý řádek", "Třetí řádek"]


def test_scorpion_v3_reader_cleans_legacy_formatting_markers():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3/CHEATER.DAT")
    payload = _build_legacy_mz_sfx(
        _rar_main_header(),
        _rar_file_header("_", attributes=0x10),
        _rar_file_header("_\\TEXTY.1", unp_size=128),
        _rar_file_header("_\\SCC.SC", unp_size=96),
        _rar_end_header(),
    )

    texty_payload = (
        b"[0001]\r\n"
        b"                                  T \xEE S T\r\n"
        b"\r\n"
        b"\xE8   KOD1\r\n"
        b"\xF0[F1] \xED prida zivot\r\n"
        b"\xEE   - separator\r\n"
        b"END\r\n"
    )
    scc_payload = "TEST,[0001]-\r\n".encode("ascii")

    original = scorpion_legacy_module._extract_overlay_members
    scorpion_legacy_module._extract_overlay_members = lambda _overlay: {
        "TEXTY.1": texty_payload,
        "_\\TEXTY.1": texty_payload,
        "SCC.SC": scc_payload,
        "_\\SCC.SC": scc_payload,
    }
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)
    finally:
        scorpion_legacy_module._extract_overlay_members = original

    assert document.topics[0].uhf_content == ["TEST", "", "   KOD1", "[[F1]  prida zivot", "   - separator"]


def test_scorpion_v3_reader_preserves_layout_after_formatting_markers():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3.5/CHEATER.DAT")
    prefix = b"\x95\x00" + b"\x00" * 31
    payload = prefix + RAR4_SIGNATURE + b"".join(
        (
            _rar_main_header(),
            _rar_file_header("_", attributes=0x10),
            _rar_file_header("_\\NAVODY.1", unp_size=128),
            _rar_end_header(),
        )
    )

    navody_payload = (
        b"[M000]\r\n"
        b"Mapa\r\n"
        b"\xE8      \xDA\xC4\xC4\xBF\r\n"
        b"\xF0           \xB3END\xB3\r\n"
        b"\r\n"
        b"\xE8      \xC0\xC4\xC4\xD9\r\n"
        b"END\r\n"
    )

    original = scorpion_legacy_module._extract_overlay_members
    scorpion_legacy_module._extract_overlay_members = lambda _overlay: {
        "NAVODY.1": navody_payload,
        "_\\NAVODY.1": navody_payload,
    }
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)
    finally:
        scorpion_legacy_module._extract_overlay_members = original

    assert document.topics[0].uhf_content == [
        "Mapa",
        "      ┌──┐",
        "           │END│",
        "",
        "      └──┘",
    ]


def test_scorpion_v3_5_reader_parses_embedded_rar_without_mz_header():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3.5/CHEATER.DAT")
    prefix = b"\x95\x00" + b"\x00" * 31
    payload = prefix + RAR4_SIGNATURE + b"".join(
        (
            _rar_main_header(),
            _rar_file_header("_", attributes=0x10),
            _rar_file_header("_\\TEXTY.1", unp_size=128),
            _rar_file_header("_\\SCC.SC", unp_size=96),
            _rar_end_header(),
        )
    )

    texty_payload = (
        "[0001]\r\n"
        "                                  H E R E T I C\r\n"
        "- IDDQD =smrt\r\n"
        "END\r\n"
    ).encode("ascii")
    scc_payload = "HERETIC,[0001]-\r\n".encode("ascii")

    original = scorpion_legacy_module._extract_overlay_members
    scorpion_legacy_module._extract_overlay_members = lambda _overlay: {
        "TEXTY.1": texty_payload,
        "_\\TEXTY.1": texty_payload,
        "SCC.SC": scc_payload,
        "_\\SCC.SC": scc_payload,
    }
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)
    finally:
        scorpion_legacy_module._extract_overlay_members = original

    assert document.metadata["scorpion_parser"] == "v3-rar-member-topics"
    assert document.metadata["scorpion_reader_class"] == "ScorpionV3_5Reader"
    assert document.metadata["overlay_offset"] == len(prefix)
    assert [topic.names[0] for topic in document.topics] == ["HERETIC"]
    assert document.topics[0].uhf_content == ["HERETIC", "- IDDQD =smrt"]


def test_scorpion_legacy_reader_skips_known_non_help_resources():
    assert not is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1.5/CS.EXE"),
        b"MZ" + b"\x00" * 62,
    )
    assert not is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3/BLCK.DAT"),
        b"\xEB\x3D" + b"\x00" * 62,
    )
    assert not is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 3.5/MAIN.DAT"),
        b"MZ" + b"\x00" * 62,
    )
    assert not is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/FB.SCO"),
        b"\xEB\x67\x90" + b"\x00" * 10 + b"SCORPIONS CHEATER 4.0 font B",
    )
    assert not is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/SLEEPER.SCO"),
        b"MZ" + b"\x00" * 62,
    )
    assert not is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/SCR001.SCX"),
        b"\x00" * 64,
    )
    assert is_scorpion_legacy_binary(
        Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATAB.SCO"),
        scorpion_legacy_v4x_module.SCORPION_SCO_SIGNATURE + b"\x00" * 62,
    )


def test_scorpion_legacy_reader_extracts_version_hints_for_shareware_dirs():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 7 _shareware_/SCR1.SCD")

    assert scorpion_version_hint_from_path(path) == "7"
    profile = scorpion_legacy_profile_for_path(path)
    assert profile is not None
    assert profile.decoder_name == "scorpion-v7-shareware"
    assert not is_scorpion_legacy_binary(path, b"\x00" * 32)


def test_scorpion_legacy_reader_accepts_embedded_exe_release():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1.5/CHEATER.EXE")
    payload = bytearray(b"MZ" + b"\x90" * 62)
    payload[0x02:0x04] = len(payload).to_bytes(2, "little")
    payload[0x04:0x06] = (1).to_bytes(2, "little")
    payload[0x08:0x0A] = (4).to_bytes(2, "little")
    payload[0x1E:0x24] = b"PKLITE"

    handler = detect_format_handler(path, payload)
    assert handler is not None
    assert handler.name == "scorpion-legacy"

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(bytes(payload))

    assert document.metadata["scorpion_version"] == "1.5"
    assert document.metadata["ui"]["window"] == "cga:0"
    assert document.metadata["scorpion_decoder"] == "scorpion-v1_5-embedded-exe"
    assert document.metadata["scorpion_wrapper"] == "dos-mz-pklite"
    assert "Wrapper: dos-mz-pklite" in document.topics[0].uhf_content


def test_scorpion_legacy_reader_selects_version_specific_reader_classes():
    assert scorpion_legacy_reader_class_for_path(Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1.5/CHEATER.EXE")) is scorpion_legacy_module.ScorpionV1_5Reader
    assert scorpion_legacy_reader_class_for_path(Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATA1.SCO")) is scorpion_legacy_v4x_module.ScorpionV4Reader
    assert scorpion_legacy_reader_class_for_path(Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 7 _shareware_/SCR1.SCD")) is scorpion_legacy_v6x_module.ScorpionV7Reader


def test_scorpion_v4_reader_reports_sco_probe_metadata():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATA1.SCO")
    payload = (
        b"SCORPION\x00\x01"
        + (-49).to_bytes(2, "little", signed=True)
        + (-47).to_bytes(2, "little", signed=True)
        + (-48).to_bytes(2, "little", signed=True)
        + (-51).to_bytes(2, "little", signed=True)
        + b"\x00" * 0x120
    )

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_decoder"] == "scorpion-v4-sco"
    assert document.metadata["scorpion_reader_class"] == "ScorpionV4Reader"
    assert document.metadata["scorpion_container_signature"] == "SCORPION\\x00\\x01"
    assert document.metadata["scorpion_probe_decoder"] == "cheater4-lz"
    assert document.metadata["scorpion_header_word_preview"][:4] == [-49, -47, -48, -51]
    assert document.metadata["scorpion_header_layout"]["word_x2_offsets"]
    assert document.metadata["scorpion_probe_status"] in {"candidate-unresolved", "candidate-readable", "no-candidates"}
    assert document.metadata["scorpion_probe_candidates"]
    assert any(candidate["source_kind"] == "header-word-scale" for candidate in document.metadata["scorpion_probe_candidates"])
    assert any(
        candidate["source_kind"] == "header-word-x2-block" and "block_skip" in candidate
        for candidate in document.metadata["scorpion_probe_candidates"]
    )
    assert "SCO signature: SCORPION 00 01" in document.topics[0].uhf_content
    assert "Header table candidates:" in document.topics[0].uhf_content
    assert "CHEATER4 decompressor model:" in document.topics[0].uhf_content
    assert "CHEATER4 probe candidates:" in document.topics[0].uhf_content


def test_scorpion_v4_reader_decodes_sco_huffman_topics():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATA1.SCO")
    stream_text = (
        "[0101]\r\n"
        "B A T T L E   B E A S T\r\n"
        "⌡ITIHFO  φ - boj bude trvat tři kola místo jednoho\r\n"
        "∙\r\n"
        "[0001]\r\n"
        "H E R E T I C\r\n"
        "IDDQD - smrt\r\n"
    )
    payload = _build_fixed_width_sco_stream(scorpion_legacy_module._encode_legacy_text(stream_text))

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_reader_class"] == "ScorpionV4Reader"
    assert document.metadata["scorpion_parser"] == "v4-sco-huffman"
    assert document.metadata["scorpion_sco_table_entries"] == 256
    assert document.metadata["scorpion_sco_stream_offset"] == 0x30A
    assert document.metadata["parsed_topic_count"] == 2
    assert [topic.names[0] for topic in document.topics] == ["BATTLE BEAST", "HERETIC"]
    assert "[fg:15][b]ITIHFO  [/b][/fg] - boj bude trvat tři kola místo jednoho" in document.topics[0].uhf_content
    assert "IDDQD - smrt" in document.topics[1].uhf_content


def test_scorpion_sco_reader_labels_datav_topic_files_as_jokes():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATAV1.SCO")
    stream_text = (
        "[0001]\r\n"
        "ŘETĚZ\r\n"
        "Víte co má muž udělat, když mu žena chodí před televizí?\r\n"
        "- Jít do kuchyně zkrátit řetěz.\r\n"
        "[0002]\r\n"
        "UHLÍ\r\n"
        "Krátký vtip.\r\n"
    )
    payload = _build_fixed_width_sco_stream(scorpion_legacy_module._encode_legacy_text(stream_text))

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_parser"] == "v4-sco-huffman"
    assert document.metadata["scorpion_sco_role"] == "jokes"
    assert document.metadata["title"] == "Scorpions Cheater 4 - Vtipy"
    assert document.contents[0].label == "Scorpions Cheater 4 - Vtipy"
    assert [topic.names[0] for topic in document.topics] == ["ŘETĚZ", "UHLÍ"]


def test_scorpion_sco_reader_labels_datan_topic_files_as_manuals():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATAN1.SCO")
    stream_text = (
        "[N001]\r\n"
        "THE LEGEND OF KYRANDIA\r\n"
        "První část návodu\r\n"
    )
    payload = _build_fixed_width_sco_stream(scorpion_legacy_module._encode_legacy_text(stream_text))

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_parser"] == "v4-sco-huffman"
    assert document.metadata["scorpion_sco_role"] == "manuals"
    assert document.metadata["title"] == "Scorpions Cheater 4 - Návody"
    assert document.contents[0].label == "Scorpions Cheater 4 - Návody"
    assert document.topics[0].names == ["THE LEGEND OF KYRANDIA"]


def test_scorpion_sco_reader_labels_joke_index_files():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 5/DATAB.SCO")
    stream_text = (
        "SEZNAM,[fórů]-\r\n"
        "ŘETĚZ,[0001]-\r\n"
        "UHLÍ,[0002]-\r\n"
        "AZURIT,[0003]-\r\n"
        "ŠAMPÓN,[0004]-\r\n"
        "BINGO,[0005]-\r\n"
    )
    payload = _build_fixed_width_sco_stream(scorpion_legacy_module._encode_legacy_text(stream_text))

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_parser"] == "v4-sco-huffman"
    assert document.metadata["scorpion_sco_role"] == "joke-index"
    assert document.metadata["scorpion_sco_index_entry_count"] == 5
    assert document.metadata["scorpion_sco_index_header_count"] == 1
    assert document.metadata["scorpion_sco_index_status_counts"] == {"plain": 5}
    assert document.metadata["title"] == "Scorpions Cheater 5 - Index vtipů"
    assert document.topics[0].names == ["Index vtipů"]
    assert "ŘETĚZ,[[0001]-" in document.topics[0].uhf_content
    assert document.metadata["scorpion_sco_index_entries"][1] == {
        "label": "ŘETĚZ",
        "target_id": "0001",
        "flag": "-",
        "status": "plain",
        "kind": "entry",
    }


def test_scorpion_sco_reader_parses_universal_index_flags():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 4/DATAA.SCO")
    stream_text = (
        "SEZNAM LABELU,[1234]--\r\n"
        "4 GET IT,[2256]--\r\n"
        "ABUSE,[4023]*-\r\n"
        "CRUSADER: NO REMORSE,[2208]+-\r\n"
        "Settlers II - save editor,[P001]!-\r\n"
    )
    payload = _build_fixed_width_sco_stream(scorpion_legacy_module._encode_legacy_text(stream_text))

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.metadata["scorpion_sco_role"] == "cheat-index"
    assert document.metadata["title"] == "Scorpions Cheater 4 - Index cheatů"
    assert document.metadata["scorpion_sco_index_entry_count"] == 4
    assert document.metadata["scorpion_sco_index_header_count"] == 1
    assert document.metadata["scorpion_sco_index_status_counts"] == {
        "plain": 1,
        "new": 1,
        "updated": 1,
        "supplement": 1,
    }
    assert document.metadata["scorpion_sco_index_flag_counts"] == {
        "-": 1,
        "*": 1,
        "+": 1,
        "!": 1,
    }
    assert document.metadata["scorpion_sco_index_entries"][-1] == {
        "label": "Settlers II - save editor",
        "target_id": "P001",
        "flag": "!",
        "status": "supplement",
        "kind": "entry",
        "raw_flag": "!-",
    }


def test_scorpion_v7_index_classifies_bang_entries_as_supplements():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 7 _shareware_/DATAA.SCD")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    supplements = [
        entry
        for entry in document.metadata["scorpion_sco_index_entries"]
        if entry.get("status") == "supplement"
    ]

    assert len(supplements) == 7
    assert {entry["target_id"] for entry in supplements} == {
        "P001",
        "P002",
        "N003",
        "N004",
        "N001",
        "M000",
        "O001",
    }


def test_scorpion_v6_reader_decodes_scd_lzhuf_index():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 6 _shareware_/DATAA.SCD")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())

    assert document.metadata["scorpion_parser"] == "sco-lzhuf"
    assert document.metadata["scorpion_compression"] == "lzhuf"
    assert document.metadata["scorpion_lzhuf_block_count"] == 1
    assert document.metadata["scorpion_sco_role"] == "cheat-index"
    assert document.metadata["scorpion_sco_index_entry_count"] > 100
    assert document.topics[0].names == ["Index cheatů"]
    assert "SEZNAM LABELU,[[1234]-" in document.topics[0].uhf_content
    assert any("A-TRAIN,[[0071]*" == line for line in document.topics[0].uhf_content)


def test_scorpion_v6_reader_decodes_scd_lzhuf_marker_topics():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 6 _shareware_/DATA1.SCD")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())

    assert document.metadata["scorpion_parser"] == "sco-lzhuf"
    assert document.metadata["scorpion_sco_role"] == "cheats"
    assert document.metadata["scorpion_sco_marker_topic_count"] >= 15
    assert document.topics[0].names == ["DESCENT"]
    assert "GABBAGABBAHEY" in "\n".join(document.topics[0].uhf_content)


def test_scorpion_v10_reader_decodes_prefixed_lzhuf_sco_blocks():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 10/CHEATS.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())

    assert document.metadata["scorpion_parser"] == "sco-lzhuf"
    assert document.metadata["scorpion_sco_role"] == "cheats"
    assert document.metadata["scorpion_lzhuf_block_count"] == 12
    assert document.metadata["scorpion_sco_index_entry_count"] > 1000
    assert document.topics[0].names == ["Index cheatů"]
    assert document.topics[1].names == ["BATTLE BEAST"]
    assert any(topic.names == ["NEED FOR SPEED III"] for topic in document.topics)


def test_scorpion_v10_reader_renders_legacy_inline_styles():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 10/CHEATS.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    battle_beast = document.topics[1]
    heretic = document.topics[2]

    assert document.metadata["scorpion_sco_inline_styles"] is True
    assert "[fg:10][b]YOYOYO[/b][/fg]" in "\n".join(battle_beast.uhf_content[:3])
    assert "[fg:10][b]ITIHFO  [/b][/fg] - boj bude trvat tři kola místo jednoho" in battle_beast.uhf_content
    assert "[fg:11][b]1) [/b][/fg]Číty (používejte ve hře):" in heretic.uhf_content
    assert "≡" not in "\n".join(battle_beast.uhf_content[:4])
    assert "φ" not in "\n".join(battle_beast.uhf_content[:4])


def test_scorpion_v5_reader_renders_dos_observed_magenta_control():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 5/DATA1.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    battle_beast = next(topic for topic in document.topics if "0101" in topic.alias_strings)
    super_frog = next(topic for topic in document.topics if "0003" in topic.alias_strings)

    assert document.metadata["scorpion_sco_inline_styles"] is True
    assert "ULTIMATE CHEAT CODE: [fg:5][b]YOYOYO[/b][/fg]" in battle_beast.uhf_content
    assert "[fg:5][b]world 6/4 =103546[/b][/fg]" in super_frog.uhf_content


def test_scorpion_v5_reader_renders_dos_observed_blue_background():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 5/DATA6.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    sword_of_sodan = next(topic for topic in document.topics if "4001" in topic.alias_strings)

    assert any(
        'depište jako "[color:10:1][b]NANCY[/b][/color]"' in line
        for line in sword_of_sodan.uhf_content
    )


def test_scorpion_v10_program_renders_table_inline_styles_without_control_glyphs():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 10/DATATEXT.SCD")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    body = "\n".join(document.topics[0].uhf_content[:8])

    assert document.metadata["scorpion_sco_inline_styles"] is True
    assert document.metadata["ui"]["window"] == "cga:0"
    assert "[fg:8][b]█▀▀▀▀" in body
    assert "[fg:1][b]─┼[/b][/fg][fg:9][b]─┼" in body
    assert "SCORPIONS  CHEATER  v10.0" in body
    assert "ε" not in body
    assert "τ" not in body

    first_aid = next(topic for topic in document.topics if "R002" in topic.alias_strings)
    assert any(
        "[color:11:1][b]00000  61 68 6F 6A" in line
        for line in first_aid.uhf_content
    )


def test_scorpion_v14_program_renders_dos_observed_gray_background():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 14/DATATEXT.SCD")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    feedback = next(topic for topic in document.topics if "R010" in topic.alias_strings)
    art_only_line = next(line for line in feedback.uhf_content if "▄██▄█▌" in line)

    assert document.metadata["display_width"] == 80
    assert any("[color:15:7][b]▄██[/b][/color]" in line for line in feedback.uhf_content)
    assert art_only_line.startswith(" " * 41)


def test_scorpion_v14_reader_renders_dos_observed_fifa_colors():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 14/CHEATS.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    fifa = next(topic for topic in document.topics if "4078" in topic.alias_strings)
    body = "\n".join(fifa.uhf_content)

    assert "[fg:3][b]VANCOUVER[/b][/fg]" in body
    assert "[fg:2][b](USA)[/b][/fg]" in body
    assert "[fg:3][b]CANADU [/b][/fg][fg:2][b](FIFA)[/b][/fg]" in body
    assert "[fg:10][b]XPLAY[/b][/fg]" in body
    assert document.metadata["scorpion_sco_index_entry_count"] == 1410
    assert document.metadata["scorpion_sco_index_status_counts"]["plain"] == 1299
    assert document.metadata["scorpion_sco_index_status_counts"]["new"] == 100
    assert document.metadata["scorpion_sco_index_status_counts"]["updated"] == 11
    cheat_entries = [
        entry
        for entry in document.metadata["scorpion_sco_index_entries"]
        if entry.get("kind") == "entry" and not entry["target_id"].startswith("R")
    ]
    assert len(cheat_entries) == 1400


def test_scorpion_v14_manual_index_preserves_content_kind_suffixes():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 14/NAVODY2.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    entries = {
        entry["target_id"]: entry["label"]
        for entry in document.metadata["scorpion_sco_index_entries"]
        if entry.get("kind") == "entry"
    }

    assert entries["N051"] == "Diablo (průvodce)"
    assert entries["O001"] == "Dungeon Master II (kouzla)"
    assert entries["O003"] == "Ishar I (mapa)"
    assert entries["P001"] == "Settlers II (save editor)"
    assert not any("Warcraft" in label for label in entries.values())


def test_scorpion_sco_normalizes_epsilon_only_inside_words():
    assert scorpion_legacy_module._normalize_sco_text_line("DεFεNDεR OF THε CROWN") == "DEFENDER OF THE CROWN"
    assert (
        scorpion_legacy_module._normalize_sco_text_line(
            "ε█≡     SCORPIONS  CHEATER  v10.0     ε█τ─┼"
        )
        == "█     SCORPIONS  CHEATER  v10.0     █─┼"
    )
    assert scorpion_legacy_module._normalize_sco_text_line("ΦRUCEε") == "RUCE"


def test_scorpion_v11_reader_decodes_numbered_hlp_lzhuf_blocks():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 11/NAVODY3.SCO")

    document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())

    assert document.metadata["scorpion_parser"] == "sco-lzhuf"
    assert document.metadata["scorpion_sco_role"] == "manuals"
    assert document.metadata["scorpion_lzhuf_block_count"] > 10
    assert document.topics[0].names == ["BUD TRUCKER IN DOUBLE TROUBLE (Meri Studios '96) návod"]
    assert document.topics[1].names == ["C I T Y O F L O S T C H I L D R E N (Psygnosis '95) návod"]


def test_scorpion_dat_reader_selects_version_specific_reader_classes():
    assert scorpion_dat_reader_class_for_path(Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 15/CHEATY.DAT")) is scorpion_dat_module.ScorpionAllegroDatReader
    assert scorpion_dat_reader_class_for_path(Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 23/CHEATY.DAT")) is scorpion_dat_module.ScorpionAllegroDatReader


def test_scorpion_legacy_reader_builds_structured_topics_for_embedded_exe_release():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1.5/CHEATER.EXE")
    payload = bytearray(b"MZ" + b"\x90" * 62)
    payload[0x02:0x04] = len(payload).to_bytes(2, "little")
    payload[0x04:0x06] = (1).to_bytes(2, "little")
    payload[0x08:0x0A] = (4).to_bytes(2, "little")
    payload[0x1E:0x24] = b"PKLITE"

    structured_payload = b"\x00".join(
        scorpion_legacy_module._encode_legacy_text(text)
        for text in [
            "---- stiskni cokoli -----",
            "SCORPIONS  CHEATER V1.50",
            "Tento program je freeware.",
            "Honza Svatos Jr.",
            "MENU PRO TISK",
            "Volby:",
            "a = tisknout logo",
            "n = netisknout logo",
            "Pro pohyb:",
            "[F1] o programu      [F5] zmena barev",
            "[F9] menu pro tisk   [F10] tisk",
            "Scorpions Cheater V1.5 - Honza Svatos & Marek Pscolka",
        ]
    ) + b"\x00"
    structured_payload = b"\x90" * 256 + structured_payload + b"\x00" * 64

    original = scorpion_legacy_v1x_module._extract_pklite_members
    scorpion_legacy_v1x_module._extract_pklite_members = lambda _source_name, _data: (
        "dos-mz-pklite",
        [
            scorpion_legacy_module.ScorpionLegacyUnpackedMember(
                output_name="output.000.exe",
                display_name="CHEATER.EXE (unpacked)",
                payload=structured_payload,
            )
        ],
    )
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(bytes(payload))
    finally:
        scorpion_legacy_v1x_module._extract_pklite_members = original

    assert document.metadata["scorpion_wrapper"] == "dos-mz-pklite"
    assert document.metadata["unpacked_member_count"] == 1
    assert document.metadata["scorpion_parser"] == "v1.5-embedded-string-table"
    assert document.metadata["parsed_sample_topic_count"] == 0
    assert document.metadata["v1_5_directory_count"] == 0
    assert document.metadata["scorpion_reader_class"] == "ScorpionV1_5Reader"
    assert document.metadata["help_contents_topic_id"] == 0
    assert document.metadata["credit_lines"] == ["Honza Svatos; Marek Pscolka"]
    assert document.metadata["scorpion_authors"] == ["Honza Svatos", "Marek Pscolka"]
    assert document.topics[0].is_help_contents
    assert [node.label for node in document.contents[0].children] == ["O programu", "Menu pro tisk", "Ovládání"]
    assert [topic.names[0] for topic in document.topics] == [
        "Scorpions Cheater 1.5",
        "O programu",
        "Menu pro tisk",
        "Ovládání",
    ]
    assert "SCORPIONS  CHEATER V1.50" in document.topics[1].uhf_content
    assert "Volby:" in document.topics[2].uhf_content
    assert "[[F9] menu pro tisk   [[F10] tisk" in document.topics[3].uhf_content


def test_scorpion_legacy_reader_extracts_cheat_topics_from_embedded_exe_string_stream():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1.5/CHEATER.EXE")
    payload = bytearray(b"MZ" + b"\x90" * 62)
    payload[0x02:0x04] = len(payload).to_bytes(2, "little")
    payload[0x04:0x06] = (1).to_bytes(2, "little")
    payload[0x08:0x0A] = (4).to_bytes(2, "little")
    payload[0x1E:0x24] = b"PKLITE"

    structured_payload = b"\x00".join(
        scorpion_legacy_module._encode_legacy_text(text)
        for text in [
            "NULL CHECK",
            "Borland C++ - Copyright 1994 Borland Intl.",
            "Divide error",
            "H E R E T I C",
            "- IDDQD     =smrt",
            "- IDKFA     =žádné zbraně",
            "D E S C E N T",
            "- MITZI     =všechny klíče",
            "T H E M E   P A R K",
            "Ctrl+C  -Vám přidá peníze",
            "! A-TRAIN",
            "HERETIC",
            "DESCENT",
            "Ř AFTER THE WAR",
            "THEME PARK",
            "---- stiskni cokoli -----",
            "SCORPIONS  CHEATER V1.50",
            "Tento program je freeware.",
            "Honza Svatos Jr.",
            "MENU PRO TISK",
            "Volby:",
            "a = tisknout logo",
            "n = netisknout logo",
            "Pro pohyb:",
            "[F1] o programu      [F5] zmena barev",
            "[F9] menu pro tisk   [F10] tisk",
            "Scorpions Cheater V1.5 - Honza Svatos",
        ]
    ) + b"\x00"
    structured_payload = b"\x90" * 256 + structured_payload + b"\x00" * 64

    original = scorpion_legacy_v1x_module._extract_pklite_members
    scorpion_legacy_v1x_module._extract_pklite_members = lambda _source_name, _data: (
        "dos-mz-pklite",
        [
            scorpion_legacy_module.ScorpionLegacyUnpackedMember(
                output_name="output.000.exe",
                display_name="CHEATER.EXE (unpacked)",
                payload=structured_payload,
            )
        ],
    )
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(bytes(payload))
    finally:
        scorpion_legacy_v1x_module._extract_pklite_members = original

    assert document.metadata["scorpion_parser"] == "v1.5-embedded-string-table"
    assert document.metadata["parsed_sample_topic_count"] == 3
    assert document.metadata["v1_5_directory_count"] == 5
    assert document.metadata["v1_5_directory_counts"] == {"new": 1, "renovated": 1, "plain": 3}
    assert [topic.names[0] for topic in document.topics[:8]] == [
        "Scorpions Cheater 1.5",
        "O programu",
        "Menu pro tisk",
        "Ovládání",
        "Seznam her",
        "HERETIC",
        "DESCENT",
        "THEME PARK",
    ]
    assert "Nové položky: 1" in document.topics[4].uhf_content
    assert "Zrenovované položky: 1" in document.topics[4].uhf_content
    assert "! A-TRAIN" in document.topics[4].uhf_content
    assert "Ř AFTER THE WAR" in document.topics[4].uhf_content
    assert "- IDDQD     =smrt" in document.topics[5].uhf_content
    assert "- MITZI     =všechny klíče" in document.topics[6].uhf_content
    assert "Ctrl+C  -Vám přidá peníze" in document.topics[7].uhf_content


def test_scorpion_v1_5_directory_parser_accepts_superscript_new_marker():
    assert scorpion_legacy_v1x_module._parse_v1_5_directory_entry("ⁿ AFTER THE WAR") == ("new", "AFTER THE WAR")


def test_scorpion_v1_5_topic_stream_stops_before_footer_art_and_directory():
    strings = [
        "H E R E T I C",
        "- IDDQD     =smrt",
        "O S C A R",
        "HEX editujte OSCAR.PCN",
        "životy:",
        "- hledejte 2E FF",
        "┌───┬───┬────┬───┐",
        "-=≡│ ├┤├├┤│├├┴┐≡=-",
        "VεRZε |.5Θ",
        "7 - UP",
        "! A-TRAIN",
        "ⁿ AFTER THE WAR",
        "HERETIC",
        "OSCAR",
        "---- stiskni cokoli -----",
    ]

    topics, repeat_index = scorpion_legacy_v1x_module._scan_v1_topic_stream(strings, start_index=0)
    directory_start_index = scorpion_legacy_v1x_module._find_v1_5_directory_start_index(
        strings,
        repeat_index=repeat_index,
    )
    stop_index = scorpion_legacy_v1x_module._find_v1_5_content_stop_index(
        strings,
        directory_start_index=directory_start_index,
    )
    topics, _repeat_index = scorpion_legacy_v1x_module._scan_v1_topic_stream(
        strings,
        start_index=0,
        stop_index=stop_index,
    )
    directory_entries = scorpion_legacy_v1x_module._extract_v1_5_directory_entries(
        strings,
        repeat_index=directory_start_index,
        stop_index=len(strings),
    )

    assert topics == [
        ("HERETIC", ["- IDDQD     =smrt"]),
        ("OSCAR", ["HEX editujte OSCAR.PCN", "životy:", "- hledejte 2E FF"]),
    ]
    assert directory_entries[:3] == [
        {"status": "plain", "title": "7 - UP", "raw": "7 - UP"},
        {"status": "renovated", "title": "A-TRAIN", "raw": "! A-TRAIN"},
        {"status": "new", "title": "AFTER THE WAR", "raw": "ⁿ AFTER THE WAR"},
    ]


def test_v1_5_directory_alias_resolver_maps_known_variants_without_guessing():
    directory_entries = [
        {"status": "plain", "title": "MR. PACFORD", "raw": "MR. PACFORD"},
        {"status": "plain", "title": "SPACE QUEST IV", "raw": "SPACE QUEST IV"},
        {"status": "plain", "title": "DOOM II", "raw": "DOOM II"},
        {"status": "plain", "title": "TFX", "raw": "TFX"},
    ]

    alias_map, unresolved_titles, resolved_count = scorpion_legacy_v1x_module._resolve_v1_5_directory_entries(
        directory_entries,
        {"M R. PACFORD", "SPACE QUEST 4", "DOOM 2"},
    )

    assert resolved_count == 3
    assert directory_entries[0]["resolved_title"] == "M R. PACFORD"
    assert directory_entries[1]["resolved_title"] == "SPACE QUEST 4"
    assert directory_entries[2]["resolved_title"] == "DOOM 2"
    assert "resolved_title" not in directory_entries[3]
    assert alias_map == {
        "DOOM 2": ["DOOM II"],
        "M R. PACFORD": ["MR. PACFORD"],
        "SPACE QUEST 4": ["SPACE QUEST IV"],
    }
    assert unresolved_titles == ["TFX"]


def test_scorpion_legacy_reader_tracks_v1_5_resolved_and_unresolved_directory_titles():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 1.5/CHEATER.EXE")
    payload = bytearray(b"MZ" + b"\x90" * 62)
    payload[0x02:0x04] = len(payload).to_bytes(2, "little")
    payload[0x04:0x06] = (1).to_bytes(2, "little")
    payload[0x08:0x0A] = (4).to_bytes(2, "little")
    payload[0x1E:0x24] = b"PKLITE"

    structured_payload = b"\x00".join(
        scorpion_legacy_module._encode_legacy_text(text)
        for text in [
            "NULL CHECK",
            "Borland C++ - Copyright 1994 Borland Intl.",
            "Divide error",
            "M R.  P A C F O R D",
            "- heslo",
            "S P A C E   Q U E S T   4",
            "- rada",
            "D O O M   2",
            "- iddqd",
            "MR. PACFORD",
            "SPACE QUEST IV",
            "DOOM II",
            "TFX",
            "SPACE QUEST 4",
            "---- stiskni cokoli -----",
            "SCORPIONS  CHEATER V1.50",
            "Tento program je freeware.",
            "Honza Svatos Jr.",
            "MENU PRO TISK",
            "Volby:",
            "a = tisknout logo",
            "n = netisknout logo",
            "Pro pohyb:",
            "[F1] o programu      [F5] zmena barev",
            "[F9] menu pro tisk   [F10] tisk",
            "Scorpions Cheater V1.5 - Honza Svatos",
        ]
    ) + b"\x00"
    structured_payload = b"\x90" * 256 + structured_payload + b"\x00" * 64

    original = scorpion_legacy_v1x_module._extract_pklite_members
    scorpion_legacy_v1x_module._extract_pklite_members = lambda _source_name, _data: (
        "dos-mz-pklite",
        [
            scorpion_legacy_module.ScorpionLegacyUnpackedMember(
                output_name="output.000.exe",
                display_name="CHEATER.EXE (unpacked)",
                payload=structured_payload,
            )
        ],
    )
    try:
        document = ScorpionLegacyReader(source_name=path.name, source_path=path).read_bytes(bytes(payload))
    finally:
        scorpion_legacy_v1x_module._extract_pklite_members = original

    assert document.metadata["v1_5_directory_resolved_count"] == 4
    assert document.metadata["v1_5_directory_unresolved_titles"] == ["TFX"]
    assert document.metadata["v1_5_directory_entries"][0]["resolved_title"] == "M R. PACFORD"
    assert document.metadata["v1_5_directory_entries"][0]["resolved_context_id"] == document.topics[5].context_id
    assert "MR. PACFORD" in document.topics[5].alias_strings
    assert "SPACE QUEST IV" in document.topics[6].alias_strings


def test_scorpion_modern_dat_reader_keeps_newest_branch_and_version_metadata():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 15/CHEATY.DAT")
    payload = path.read_bytes()

    handler = detect_format_handler(path, payload)
    assert handler is not None
    assert handler.name == "scorpion-dat"

    document = ScorpionDatReader(source_name=path.name, source_path=path).read_bytes(payload)

    assert document.format_name == "scorpion-dat"
    assert document.metadata["scorpion_version"] == "15"
    assert document.metadata["scorpion_decoder"] == "scorpion-dat"
