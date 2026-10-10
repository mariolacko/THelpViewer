from functools import lru_cache
from pathlib import Path

from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.t602_300 import T602300Reader, is_t602_300_binary
from thelpviewer.server.converter.readers.t602_310 import T602310Reader
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


@lru_cache(maxsize=1)
def _c602_document():
    path = Path("data/sources") / "Software 602" / "C602.HLP"
    return T602310Reader(str(path), path).read_bytes(path.read_bytes())


@lru_cache(maxsize=1)
def _t602_document():
    path = Path("data/sources") / "Software 602" / "t602_310.hlp"
    return T602310Reader(str(path), path).read_bytes(path.read_bytes())


@lru_cache(maxsize=1)
def _t602_300_document():
    path = Path("data/sources") / "Software 602" / "t602_300.hlp"
    return T602300Reader(str(path), path).read_bytes(path.read_bytes())


def _topic_by_name(document, name):
    return next(topic for topic in document.topics if topic.names == [name])


def _topics_by_name(document, name):
    return [topic for topic in document.topics if topic.names == [name]]


def test_text602_and_calc602_expose_green_t602_ui_theme():
    for document in (_t602_document(), _c602_document()):
        assert document.metadata["ui"]["window"] == "#005454"
        assert document.metadata["ui"]["text"] == "#a8fcfc"
        assert document.metadata["ui"]["link"] == "#a8a800"
        assert document.metadata["ui"]["frame"] == "#a8a800"
        assert document.metadata["ui"]["icon"] == "#005454"
        assert document.metadata["ui"]["arrow_bg"] == "#a8a800"
        assert document.metadata["ui"]["thumb_bg"] == "#a8a800"

        payload = HelpJsonRenderer(document, display_encoding="utf-8").render_document()
        assert payload["metadata"]["ui"]["window"] == "#005454"
        assert payload["metadata"]["ui"]["text"] == "#a8fcfc"
        assert payload["metadata"]["ui"]["link"] == "#a8a800"
        assert payload["metadata"]["ui"]["frame"] == "#a8a800"
        assert payload["metadata"]["ui"]["icon"] == "#005454"


def test_text602_and_calc602_keep_navigation_links_resolved():
    t602_links = sum(line.count("[link:topic=") for topic in _t602_document().topics for line in topic.uhf_content)
    c602_links = sum(line.count("[link:topic=") for topic in _c602_document().topics for line in topic.uhf_content)

    assert t602_links >= 780
    assert c602_links >= 1000


def test_text602_and_calc602_drop_trailing_topic_rules():
    for document in (_t602_document(), _c602_document()):
        assert not any(topic.uhf_content and topic.uhf_content[-1] == "[rule]" for topic in document.topics)


def test_text602_index_links_menu_entries_without_corrupting_footer():
    document = _t602_document()
    index_topic = _topic_by_name(document, "Text602 | Abecední rejstřík nápovědy.")
    contents_topic = _topic_by_name(document, "Text602 | Obsah")

    assert any("]Jdi na konec bloku[/link]" in line for line in index_topic.uhf_content)
    assert index_topic.uhf_content[-1] == f"■ [link:topic={contents_topic.context_id}]Obsah nápovědy[/link]"
    assert "[link:topic=12]Obsah[/link] nápovědy" not in index_topic.uhf_content


def test_text602_contents_uses_its_complete_source_link_table():
    document = _t602_document()
    contents_topic = _topic_by_name(document, "Text602 | Obsah")
    text = "\n".join(contents_topic.uhf_content)

    for label in (
        "Formátování bloku",
        "Inverze označení bloku",
        "Zapsání bloku na disk",
        "Načtení bloku z disku",
        "Vytvoření obsahu",
        "Vytvoření indexu",
    ):
        assert f"]{label}[/link]" in text

    assert "]Načtení[/link] bloku z disku" not in text


def test_text602_context_summary_is_followed_by_a_blank_line():
    document = _t602_document()
    centered_line = _topic_by_name(
        document,
        "Řádka | Centrování textu na řádce        <Ctrl-OC>",
    )
    database_field = _topic_by_name(document, "Řádka | Políčko")

    assert centered_line.uhf_content[:3] == [
        "Centrování textu na řádku",
        "",
        "Text na řádku, kde je umístěn kurzor, je možné vystředit mezi "
        "definované a aktivní okraje. Zároveň je u daného odstavce změněn "
        "styl: Zarovnání na střed.",
    ]
    assert database_field.uhf_content[:3] == [
        "Vložení pole",
        "",
        "Při návrhu formuláře pro kartotéku se mezi příkazy menu Řádka "
        "zpřístupnil příkaz Políčko, který je při editaci běžných dokumentů "
        "nepřístupný. Tento příkaz použijete ke vkládání polí formuláře jako "
        "referencí na položky záznamů zvolené databáze.",
    ]


def test_text602_helpctx_links_use_exact_editor_and_cardfile_targets():
    document = _t602_document()
    index_topic = _topic_by_name(document, "Text602 | Abecední rejstřík nápovědy.")
    editor_open, cardfile_open = _topics_by_name(
        document,
        "Soubor | Otevření                 <F3>",
    )
    editor_calculator, _, cardfile_calculator = _topics_by_name(
        document,
        "Text602 | Kalkulačka              <Alt-Q>",
    )
    _, cardfile_go_to = _topics_by_name(
        document,
        "Menu Jdi na                       <Alt-J>",
    )
    _, cardfile_edit = _topics_by_name(
        document,
        "Menu Edit                         <Alt-E>",
    )
    _, cardfile_find = _topics_by_name(
        document,
        "Jdi na | Najít                    <Ctrl-QF>",
    )
    _, cardfile_print = _topics_by_name(document, "Soubor | Tisk")
    _, cardfile_basic_help = _topics_by_name(document, "Základní pohyb v nápovědě")
    editor_find_next = _topic_by_name(document, "Vzorce | Další                    <Ctrl-L>")
    cardfile_find_next = _topic_by_name(document, "Jdi na | Další                    <Ctrl-L>")
    cardfile_forms = _topic_by_name(document, "Menu Formulář                     <Alt-F>")
    cardfile_functions = _topic_by_name(document, "Seznam funkcí kartotéky")
    cardfile_show_deleted = _topic_by_name(document, "Zobrazit | Zrušené")
    editor_window = _topic_by_name(document, "Text602 | Editor")

    text = "\n".join(index_topic.uhf_content)
    assert f"[link:topic={cardfile_open.context_id}]Otevřít databázový soubor[/link]" in text
    assert f"[link:topic={editor_open.context_id}]Otevřít databázový soubor[/link]" not in text
    assert f"[link:topic={cardfile_calculator.context_id}]Kalkulačka v kartotéce[/link]" in text
    assert f"[link:topic={editor_calculator.context_id}]Kalkulačka v kartotéce[/link]" not in text
    assert f"[link:topic={cardfile_go_to.context_id}]Pohyb v databázi[/link]" in text
    assert f"[link:topic={cardfile_basic_help.context_id}]Kartotéka - základní pohyb v nápovědě[/link]" in text
    assert f"[link:topic={editor_find_next.context_id}]Najít další výskyt řetězce[/link]" in text
    assert f"[link:topic={cardfile_edit.context_id}]Editace položek[/link]" in text
    assert f"[link:topic={cardfile_forms.context_id}]Formuláře[/link]" in text
    assert f"[link:topic={editor_window.context_id}]Otevření okna s editorem[/link]" in text
    assert f"[link:topic={cardfile_find.context_id}]Najít záznam[/link]" in text
    assert f"[link:topic={cardfile_find_next.context_id}]Najdi další záznam[/link]" in text
    assert f"[link:topic={cardfile_show_deleted.context_id}]Zobrazení zrušených záznamů[/link]" in text
    assert f"[link:topic={cardfile_functions.context_id}]Vestavěné funkce kartotéky[/link]" in text
    assert f"[link:topic={cardfile_print.context_id}]Tisk databáze[/link]" in text


def test_text602_topic_footer_links_index_and_contents():
    document = _t602_document()
    opening_topic = _topic_by_name(document, "Soubor | Otevření                 <F3>")
    contents_topic = _topic_by_name(document, "Text602 | Obsah")
    index_topic = _topic_by_name(document, "Text602 | Abecední rejstřík nápovědy.")

    assert opening_topic.uhf_content[-1] == (
        f"■ [link:topic={index_topic.context_id}]Rejstřík[/link]  "
        f"[link:topic={contents_topic.context_id}]Obsah[/link]"
    )


def test_text602_marked_title_screens_and_keyboard_alias_links_are_preserved():
    document = _t602_document()
    block_start = _topic_by_name(document, "Blok | Začátek                    <F7> +                                    <Ctrl-KB>")
    block_end = _topic_by_name(document, "Blok | Konec                      <F8> +                                    <Ctrl-KK>")
    keyboard_menu = _topic_by_name(document, "Menu Klávesnice")
    czech_keyboard = _topic_by_name(document, "Klávesnice | Český psací stroj    <Alt-2>")
    ibm_keyboard = _topic_by_name(document, "Klávesnice | Počítačová klávesnice       <Alt-5>")

    assert "Označuje začátek bloku." in block_start.uhf_content
    assert "Označuje konec bloku." in block_end.uhf_content
    assert any(
        f"[link:topic={czech_keyboard.context_id}]Česká profesionální[/link]" in line
        for line in keyboard_menu.uhf_content
    )
    assert any(
        f"[link:topic={ibm_keyboard.context_id}]Anglická podle IBM[/link]" in line
        for line in keyboard_menu.uhf_content
    )


def test_c602_context_menu_links_are_resolved_without_linking_ascii_art():
    doc = _c602_document()

    graph_topic = doc.topics[49]
    assert graph_topic.context_id == 50
    assert any("┌─────┬─────┬───────── názvy kategorií" in line for line in graph_topic.uhf_content)
    assert not any("[link:topic=54]┌" in line for line in graph_topic.uhf_content)
    assert not any("[link:topic=56](legenda)" in line for line in graph_topic.uhf_content)
    assert not any("[link:topic=56]4 α" in line for line in graph_topic.uhf_content)
    assert "■ [link:topic=51]Výběr 2D grafu[/link]" in graph_topic.uhf_content
    assert "  [link:topic=52]Výběr 3D grafu[/link]" in graph_topic.uhf_content
    assert "■ [link:topic=53]Nadpis grafu[/link]" in graph_topic.uhf_content

    graph_3d_topic = doc.topics[51]
    assert graph_3d_topic.context_id == 52
    assert "■ [link:topic=51]Výběr 2D grafu[/link]" in graph_3d_topic.uhf_content


def test_c602_uses_software602_character_overrides():
    doc = _c602_document()

    contents = doc.topics[128]
    assert contents.context_id == 129
    assert contents.uhf_content[0] == "■ Úvod"

    finance = doc.topics[100]
    assert " │ FV(Úrok,PočetObdobí,Splátka,<SoučasnáHodnota>,<Typ>)                    │" in finance.uhf_content
    assert "Úrok - úroková míra (rate - RATE)." in finance.uhf_content

    all_text = "\n".join(line for topic in doc.topics for line in topic.uhf_content)
    for bad_text in ("⌡vod", "⌡rok", "zvláš╘", "pamě╘", "TERMINßL", "KLADN≈", "ZßPORN≈", "bu─"):
        assert bad_text not in all_text


def test_t602_300_is_detected_by_manifest_converter_registry():
    path = Path("data/sources") / "Software 602" / "t602_300.hlp"
    data = path.read_bytes()
    handler = detect_format_handler(path, data)

    assert is_t602_300_binary(data)
    assert handler is not None
    assert handler.name == "text602-legacy"


def test_t602_300_reader_parses_legacy_length_prefixed_rows():
    document = _t602_300_document()

    assert document.format_name == "text602-legacy"
    assert len(document.topics) == 191
    assert len(document.index_entries) == 191
    assert document.metadata["stamp"] == "T6HLP86278"
    assert document.metadata["title"] == "Text 602 3.00"
    assert document.metadata["ui"]["window"] == "#005454"

    opening = next(topic for topic in document.topics if topic.context_id == 35)
    assert opening.names == ["Otevření"]
    assert opening.uhf_content[:5] == [
        "     Příkaz je určen pro otevření (načtení",
        "z disku) pracovního textového souboru. Není-li",
        "stávající (dosud editovaný) soubor uložen, bude",
        "zobrazen dotaz, zda má být zapsán na disk či",
        "nikoliv.",
    ]
    assert "zapsat do dialogového rámečku [b]Jméno souboru[/b]. Při" in opening.uhf_content

    all_text = "\n".join(line for topic in document.topics for line in topic.uhf_content)
    for bad_text in ("načtení.z", "Není-li/stávající", "bude,zobrazen", "či\x08", "[97]", "[96]"):
        assert bad_text not in all_text
