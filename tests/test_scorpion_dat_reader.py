from pathlib import Path

from thelpviewer.server.converter.base import HelpDocument
from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.scorpion_dat_parser import SCORPION_DAT_SIGNATURE
from thelpviewer.server.converter.readers.scorpion_dat_reader import (
    ScorpionDatReader,
    _normalize_title,
    _render_payload_lines,
    is_scorpion_dat_binary,
    is_scorpion_dat_help_binary,
)
from thelpviewer.server.converter.readers.scorpion_dat_parser import parse_scorpion_dat_records
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


def _sample_cheaty23_path() -> Path:
    return Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 23/CHEATY.DAT")


def _sample_navody23_path() -> Path:
    return Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 23/NAVODY.DAT")


def _sample_easter23_path() -> Path:
    return Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 23/EASTER.DAT")


def _sample_program23_path() -> Path:
    return Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 23/PROGRAM.DAT")


def _sample_texty21_path() -> Path:
    return Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 21/TEXTY.DAT")


def test_scorpion_dat_reader_detects_modern_old_crypt_allegro_dat():
    path = _sample_cheaty23_path()
    payload = path.read_bytes()

    handler = detect_format_handler(path, payload)

    assert payload.startswith(SCORPION_DAT_SIGNATURE)
    assert is_scorpion_dat_binary(payload)
    assert handler is not None
    assert handler.name == "scorpion-dat"


def test_scorpion_dat_detection_skips_empty_resource_only_dat():
    path = _sample_texty21_path()
    payload = path.read_bytes()

    handler = detect_format_handler(path, payload)

    assert is_scorpion_dat_binary(payload)
    assert not is_scorpion_dat_help_binary(payload)
    assert handler is None


def test_scorpion_dat_parser_uses_decoded_payload_for_real_cheaty23_records():
    records = parse_scorpion_dat_records(_sample_cheaty23_path().read_bytes())

    assert len(records) == 32
    assert {record.payload_source for record in records} == {"decoded"}
    assert next(record for record in records if record.name == "ch05").payload.startswith(b"[3001]")


def test_scorpion_dat_reader_renders_kamenicky_text_and_inline_styles():
    document = ScorpionDatReader(
        source_name="CHEATY.DAT",
        source_path=_sample_cheaty23_path(),
    ).read_bytes(_sample_cheaty23_path().read_bytes())
    by_alias = {
        alias: topic
        for topic in document.topics
        for alias in topic.alias_strings
    }
    topic = by_alias["L002"]
    body = "\n".join(topic.uhf_content[:20])

    assert topic.names[0] == "COMMANDOS 2: Men of Courage"
    assert "Číty" in body
    assert "[fg:11][b]1) [/b][/fg]" in body
    assert "[fg:10][b]GONZOANDJON[/b][/fg]" in body
    assert "[fg:15][b]Shift[/b][/fg]" in body
    assert "[fg:14][b]X[/b][/fg]" in body
    assert document.metadata["source_text_encoding"] == "kamenicky"


def test_scorpion_dat_reader_normalizes_spaced_titles_without_merging_words():
    assert _normalize_title("B A T T L E   B E A S T") == "BATTLE BEAST"
    assert _normalize_title("C O M M A N D O S   2 :  Men of Courage") == "COMMANDOS 2: Men of Courage"
    assert _normalize_title("Q U I C K E N   f o r   W i n d o w s") == "QUICKEN for Windows"
    assert _normalize_title("PAGE MILL 3. 0") == "PAGE MILL 3.0"


def test_scorpion_dat_reader_fixes_spaced_windows_titles_in_easter_bundle():
    document = ScorpionDatReader(
        source_name="EASTER.DAT",
        source_path=_sample_easter23_path(),
    ).read_bytes(_sample_easter23_path().read_bytes())
    by_alias = {
        alias: topic
        for topic in document.topics
        for alias in topic.alias_strings
    }

    assert by_alias["0047"].names[0] == "QUICKEN for Windows"
    assert by_alias["0046"].names[0] == "QUATTRO PRO for Windows"
    assert by_alias["0049"].names[0] == "TURBO PASCAL for Windows"


def test_scorpion_dat_bundle_index_lists_article_titles():
    path = _sample_cheaty23_path()
    document = ScorpionDatReader(
        source_name=path.name,
        source_path=path,
    ).read_bytes(path.read_bytes())

    payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()
    labels = [entry["label"] for group in payload["index"] for entry in group["entries"]]

    assert len(labels) == len(document.topics)
    assert "COMMANDOS 2: Men of Courage" in labels


def test_scorpion_dat_reader_maps_full_foreground_palette_spans():
    document = ScorpionDatReader(
        source_name="CHEATY.DAT",
        source_path=_sample_cheaty23_path(),
    ).read_bytes(_sample_cheaty23_path().read_bytes())
    by_alias = {
        alias: topic
        for topic in document.topics
        for alias in topic.alias_strings
    }

    body = "\n".join(by_alias["8001"].uhf_content)

    assert "[fg:11][b]Offset        změňte na         pro tento efekt[/b][/fg]" in body
    assert "[fg:8][b]-----------------------------------------------[/b][/fg]" in body


def test_scorpion_dat_reader_uses_e6_as_modern_background_reset():
    lines = _render_payload_lines(b"\xF7\xF1blue\xE6 plain")

    assert [line.uhf for line in lines] == [
        "[color:11:1][b]blue[/b][/color][fg:11][b] plain[/b][/fg]"
    ]


def test_scorpion_dat_reader_distinguishes_e5_background_from_literal_n():
    lines = _render_payload_lines(b"\xF5\xDC\xE5\xDC\xDB\xDB\xE6 kampa\xE5,")

    assert [line.uhf for line in lines] == [
        "[fg:15][b]▄[/b][/fg][color:15:7][b]▄██[/b][/color]"
        "[fg:15][b] kampaň,[/b][/fg]"
    ]


def test_scorpion_v15_dat_reader_restores_literal_n_from_e5():
    path = Path("data/sources/Scorpions Cheater DOS/Scorpions Cheater 15/CHEATY.DAT")
    document = ScorpionDatReader(source_name=path.name, source_path=path).read_bytes(path.read_bytes())
    topgun = next(topic for topic in document.topics if "9011" in topic.alias_strings)

    assert "první ťíslo je kampaň," in "\n".join(topgun.uhf_content)


def test_scorpion_dat_reader_repairs_extended_sc_text_bytes_and_soft_breaks():
    cheats = ScorpionDatReader(
        source_name="CHEATY.DAT",
        source_path=_sample_cheaty23_path(),
    ).read_bytes(_sample_cheaty23_path().read_bytes())
    guides = ScorpionDatReader(
        source_name="NAVODY.DAT",
        source_path=_sample_navody23_path(),
    ).read_bytes(_sample_navody23_path().read_bytes())
    easter = ScorpionDatReader(
        source_name="EASTER.DAT",
        source_path=_sample_easter23_path(),
    ).read_bytes(_sample_easter23_path().read_bytes())

    cheat_topics = {
        alias: topic
        for topic in cheats.topics
        for alias in topic.alias_strings
    }
    guide_topics = {
        alias: topic
        for topic in guides.topics
        for alias in topic.alias_strings
    }
    easter_topics = {
        alias: topic
        for topic in easter.topics
        for alias in topic.alias_strings
    }

    assert "před Shang Tsungem" in "\n".join(cheat_topics["4086"].uhf_content)
    assert "Petr Minařík" in "\n".join(cheat_topics["K029"].uhf_content)
    assert "müsli tyčinku" in "\n".join(guide_topics["N118"].uhf_content)
    assert "Stručný průchod hrou:" in "\n".join(guide_topics["N008"].uhf_content)
    assert "Kübelwagenem" in "\n".join(guide_topics["N273"].uhf_content)
    assert "k mříži" in "\n".join(guide_topics["N286"].uhf_content)
    assert "mŕtvol" in "\n".join(guide_topics["N204"].uhf_content)
    assert "Otočila se  o 180°" in "\n".join(guide_topics["N158"].uhf_content)
    assert "adresáři" in "\n".join(easter_topics["0009"].uhf_content)
    assert "√" not in "\n".join(guide_topics["N008"].uhf_content)
    assert "■" not in "\n".join(guide_topics["N286"].uhf_content)
    assert "²" not in "\n".join(cheat_topics["K029"].uhf_content)


def test_scorpion_dat_bundle_exposes_black_ui_theme_and_resource_inventory():
    path = _sample_program23_path()
    document = ScorpionDatReader(
        source_name=path.name,
        source_path=path,
    ).read_bytes(path.read_bytes())

    assert document.metadata["ui"]["window"] == "cga:0"
    assert document.metadata["display_width"] == 80
    assert document.metadata["scorpion_resource_record_count"] == 23
    assert "FONT1" in document.metadata["scorpion_resource_record_names"]
    assert "obr1" in document.metadata["scorpion_resource_record_names"]
    assert "record_names" not in document.metadata
    assert "scorpion_record_inventory" not in document.metadata
    assert "allegro_object_count" not in document.metadata
    assert "allegro_object_types" not in document.metadata
    assert "allegro_object_names" not in document.metadata
    assert "topic_boundaries" not in document.metadata

    payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()

    assert payload["metadata"]["ui"]["window"] == "cga:0"
    assert payload["metadata"]["display"]["cols"] == 80
    assert payload["metadata"]["scorpion_resource_record_count"] == 23
    assert "FONT1" in payload["metadata"]["scorpion_resource_record_names"]
    assert "obr1" in payload["metadata"]["scorpion_resource_record_names"]
    assert "record_names" not in payload["metadata"]
    assert "scorpion_record_inventory" not in payload["metadata"]
    assert "allegro_object_count" not in payload["metadata"]
    assert "allegro_object_types" not in payload["metadata"]
    assert "allegro_object_names" not in payload["metadata"]
    assert "topic_boundaries" not in payload["metadata"]


def test_uhf_writer_maps_source_date_into_existing_source_metadata():
    document = HelpDocument(
        format_name="scorpion-dat",
        source_name="CHEATY.DAT",
        topics=[],
        index_entries=[],
        metadata={"title": "Scorpion", "source_date": "2002-01-02"},
    )

    payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()

    assert payload["metadata"]["source"]["date"] == "2002-01-02"
