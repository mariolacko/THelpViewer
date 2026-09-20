import re

from thelpviewer.converter.readers.thelp import ThelpHelpReader


def _screen(context_id, lines):
    return {
        "id": context_id,
        "alias_ids": [],
        "lines": lines,
        "keywords_v4": [],
        "keywords_v5": [],
        "indices": [],
        "is_help_contents": False,
        "link_up": None,
        "link_down": None,
    }


def test_orphan_screens_get_unique_synthetic_contexts_and_empty_ones_are_skipped():
    metadata = {}

    topics = ThelpHelpReader._build_topics(
        [
            _screen(7, [b"Normal"]),
            _screen(0xFFFF, []),
            _screen(0xFFFF, [b"First orphan"]),
            _screen(0xFFFF, [b"Second orphan"]),
        ],
        metadata,
    )

    assert [topic.context_id for topic in topics] == [7, 0x10000, 0x10001]
    assert metadata["orphan_screen_contexts"] == [0x10000, 0x10001]
    assert metadata["skipped_empty_orphan_screens"] == 1


def test_more_marker_links_to_the_thelp_down_continuation():
    first = _screen(128, [b"First page", b"<more>"])
    first["link_down"] = 327
    document = ThelpHelpReader("SK2.HLP")._build_document(
        {},
        [first, _screen(327, [b"Second page"])],
        [],
        binary_data=None,
    )

    ThelpHelpReader.refresh_rendered_uhf_content(document, encoding="cp437")

    assert document.topics[0].uhf_content[-1] == "[link:topic=327]<more>[/link]"


def test_sequential_hotspot_table_cells_are_restored_to_rows():
    header = (
        " "
        + "\u2550" * 7
        + "\u2564"
        + ("\u2550" * 9 + "\u2564") * 5
        + "\u2550" * 9
        + "\u2555"
    )
    cells = [
        "[link:topic=2087]   [[ ]  [/link]\u2502",
        "[link:topic=2086]   ( )  [/link]\u2502",
        "[link:topic=2085]   .    [/link]\u2502",
        "[link:topic=2085]   ->   [/link]\u2502",
        "[link:topic=2082]   ++   [/link]\u2502",
        "[link:topic=2082]   --   [/link]\u2502",
        "[link:topic=2081]   &    [/link]\u2502",
    ]

    restored = ThelpHelpReader._restore_sequential_hotspot_tables(
        [header, *cells, "tail"]
    )

    assert restored == [
        header,
        cells[0] + "".join(f" {cell}" for cell in cells[1:]),
        "tail",
    ]
    visible_row = re.sub(
        r"\[link:[^\]]+\]|\[/link\]",
        "",
        restored[1],
    ).replace("[[", "[")
    assert [idx for idx, char in enumerate(visible_row) if char == "\u2502"] == [
        8,
        18,
        28,
        38,
        48,
        58,
        68,
    ]


def test_example_code_detection_stops_before_see_also_heading():
    raw_lines = [
        b" Example:",
        b"  #undef DEBUG",
        b"",
        b" See Also:",
        b"\x02  #if, #ifdef, #ifndef\x02",
    ]

    assert ThelpHelpReader._detect_example_code_lines(raw_lines) == {1}


def test_example_code_detection_keeps_blank_lines_between_code_lines():
    raw_lines = [
        b" Example:",
        b"  first line",
        b"",
        b"  second line",
    ]

    assert ThelpHelpReader._detect_example_code_lines(raw_lines) == {1, 2, 3}
