from thelpviewer.server.converter.readers.thelp import ThelpHelpReader


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
    cells = [b"\2   [ ]  \2\xb3", b"\2   ( )  \2\xb3", b"\2   .    \2\xb3",
             b"\2   ->   \2\xb3", b"\2   ++   \2\xb3", b"\2   --   \2\xb3", b"\2   &    \2\xb3"]
    restored = ThelpHelpReader._wrap_text_lines([header.encode("cp437"), *cells, b" tail"], 76)

    assert restored == [
        header.encode("cp437"),
        b" ".join(cells) + b" ",
        b" tail",
    ]
    visible_row = restored[1].replace(b"\2", b"").decode("cp437")
    assert [idx for idx, char in enumerate(visible_row) if char == "\u2502"] == [
        8,
        18,
        28,
        38,
        48,
        58,
        68,
    ]


def test_sequential_hotspot_table_restores_inside_link_separators_and_partial_row():
    header = b" ======\xd1======\xd1======\xb8"
    cells = [b"\2  alpha\xb3\2", b"\2  beta \xb3\2", b"\2  gamma\xb3\2", b"\2  omega\xb3\2"]
    restored = ThelpHelpReader._wrap_text_lines([header, *cells, b" tail"], 26)

    assert restored == [
        header,
        b" ".join(cells[:3]) + b" ",
        cells[3] + b" ",
        b" tail",
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
