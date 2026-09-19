import re

from thelpviewer.converter.readers.thelp import ThelpHelpReader


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
