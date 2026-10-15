"""Native Pc-Fand name lookup, empty aliases and embedded help stay reachable."""

from pathlib import Path
import re
import struct

import pytest

from thelpviewer.server.converter.base import TopicRecord
from thelpviewer.server.converter.readers.game_cheater import (
    GameCheaterReader, PC_FAND_HELP_FOLD, _help_display_text, _help_name_matches,
    _link_help_topic_references, _read_text_block_bytes, _records,
)
from thelpviewer.server.converter.readers.game_cheater_bundle import document_variants
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.server.converter.uhf_markup import escape_uhf_text
from test_game_cheater_reader import _TextFile, _table, _write_fixture


@pytest.mark.parametrize("label,pattern,expected", [
    ("Hledání cheatu", "hledání cheatů", True),
    ("ČĆĐŁŃÖŐŘŚŠŤŮŰÝŹŻ", "CCD LNOOR SSTUUYZZ".replace(" ", ""), True),
    ("straße", "STRASSE", False),
    ("root ", "root", False),
    ("a  b", "a b", False),
    ("[a]", "[a]", True),
    ("abc*", "abc", False),
    ("", "", True), ("", "*", True), ("", "**", False),
    ("*", "**", True), ("abc", "**", False),
    ("one", "?ne", True), ("one", "??", False),
    ("anything END", "*end", True), ("END", "*end", True),
    ("ABC", "*?", False), ("ABC?", "*?", True),
    ("?end", "*?end", True), ("Aend", "*?end", False),
    ("aaab", "*ab", True), ("ababa", "*aba", True),
])
def test_name_mask_matches_native_byte_rules(label, pattern, expected):
    assert _help_name_matches(label.encode("cp852"), pattern.encode("cp852")) is expected


def test_first_physical_match_is_not_the_nearest_or_lowest_context():
    topic = TopicRecord(90, [], uhf_content=["[u]Name[/u]"])
    _link_help_topic_references([topic], [(b"Name", 500), (b"Name", 91)])
    assert topic.uhf_content == ["[link:topic=500][u]Name[/u][/link]"]


def test_literal_tags_brackets_and_exact_whitespace_do_not_become_markup_or_a_new_name():
    title = "[u] [[b] [i]"
    caption = escape_uhf_text(title)
    topic = TopicRecord(9, [], uhf_content=[
        escape_uhf_text("[u]Name[/u]"),
        f"[u]{caption}[/u] and [u] a  b [/u]",
        "[u][b]Name[/b][/u]",
    ])
    _link_help_topic_references([topic], [(title.encode(), 7), (b"Name", 8), (b"a b", 10)])
    assert topic.uhf_content == [
        "[[u]Name[[/u]",
        f"[link:topic=7][u]{caption}[/u][/link] and [u] a  b [/u]",
        "[u][b]Name[/b][/u]",
    ]


@pytest.mark.parametrize("source,expected", [
    (b"{description}\r\n\r\nBODY", b"\r\nBODY"),
    (b"{description}\rBODY", b"BODY"),
    (b"{description}\nBODY", b""),
    (b"{description}", b""),
    (b"text {description}\r\nBODY", b"text {description}\r\nBODY"),
])
def test_hidden_description_line_uses_native_cr_boundary(source, expected):
    assert _help_display_text(source) == expected


def replace_help(root, rows):
    text = _TextFile()
    records = []
    for title, body in rows:
        record = bytearray(39)
        record[:35] = bytes(value ^ 0xAA for value in title.encode("cp852").ljust(35, b" "))
        offset = text.add(body) if body is not None else 0
        struct.pack_into("<I", record, 35, offset)
        records.append(bytes(record))
    (root / "GCHLP.000").write_bytes(_table(records, 39))
    (root / "GCHLP.T00").write_bytes(text.data)


def test_empty_named_records_resolve_to_following_text_in_links_index_contents_and_navigation(tmp_path):
    path = _write_fixture(tmp_path / "sources")
    replace_help(path.parent, [
        ("root", "\x13Alias\x13 and \x13Hledání cheatu\x13"),
        ("Alias", None), ("Second alias", ""),
        ("Target", "{hidden}\r\n\r\nTARGET"),
        ("hledání cheatů", "SEARCH"), ("Trailing empty", None),
    ])
    doc = GameCheaterReader(source_path=path).read_path(path)
    help_doc = next(v.document for v in document_variants(doc) if v.bundle_stem == "napoveda")
    payload = HelpJsonRenderer(help_doc, "utf-8").render_document()
    assert set(payload["topics"]) == {"4", "7", "8", "9"}
    assert payload["topics"]["4"]["content"] == [
        "[link:topic=7][u]Alias[/u][/link] and [link:topic=8][u]Hledání cheatu[/u][/link]",
    ]
    assert payload["topics"]["7"]["content"] == ["", "TARGET"]
    assert payload["topics"]["7"]["aliases"]["ids"] == [6, 5]
    assert {"Alias", "Second alias"} <= set(payload["topics"]["7"]["aliases"]["strings"])
    assert payload["metadata"]["help_contents_topic_id"] == 4
    index = {e["label"]: e["topic_id"] for group in payload["index"] for e in group["entries"]}
    assert index["Alias"] == index["Second alias"] == 7
    assert [(n["label"], n["topic_id"]) for n in payload["contents"][0]["children"]][1:3] == [
        ("Alias", 7), ("Second alias", 7),
    ]
    root = next(t for t in help_doc.topics if t.context_id == 4)
    target = next(t for t in help_doc.topics if t.context_id == 7)
    assert root.next_context == 7 and target.prev_context == 4


def test_complete_original_help_lookup_matches_independent_source_record_scan():
    path = Path("data/sources/Game-Cheater/Game-Cheater 9.02/CHEATDBS.000")
    if not path.is_file():
        pytest.skip("Original Game-Cheater is not installed")
    records = _records(path.with_name("GCHLP.000").read_bytes(), 39)
    memo = path.with_name("GCHLP.T00").read_bytes()
    rows = [(bytes(value ^ 0xAA for value in r[:35]).rstrip(b" "),
             _read_text_block_bytes(memo, struct.unpack_from("<I", r, 35)[0]) or b"") for r in records]
    # Compile the native mask grammar into a byte regex independently of the
    # reader's recursive matcher. A byte after '*' is always a literal.
    patterns = []
    for name, _body in rows:
        name = name.translate(PC_FAND_HELP_FOLD)
        expression = bytearray()
        p = 0
        while p < len(name):
            if name[p] == ord("*"):
                expression.extend(b".*")
                p += 1
                if p < len(name):
                    expression.extend(re.escape(name[p:p+1]))
            elif name[p] == ord("?"):
                expression.extend(b".")
            else:
                expression.extend(re.escape(name[p:p+1]))
            p += 1
        patterns.append(re.compile(bytes(expression), re.DOTALL))
    body_records = [i for i, (_name, body) in enumerate(rows) if body]
    document = GameCheaterReader(source_path=path).read_path(path)
    help_doc = next(v.document for v in document_variants(document) if v.bundle_stem == "napoveda")
    assert len(help_doc.topics) == len(body_records) == 383
    targets = dict(zip(body_records, [t.context_id for t in help_doc.topics]))
    checked = 0
    for i in body_records:
        visible = _help_display_text(rows[i][1])
        expected = []
        for match in re.finditer(b"\x13([^\x13]*)\x13", visible):
            label = match[1].translate(PC_FAND_HELP_FOLD)
            first = next(j for j, pattern in enumerate(patterns) if pattern.fullmatch(label))
            while not rows[first][1] and first + 1 < len(rows):
                first += 1
            expected.append(targets[first])
        topic = next(t for t in help_doc.topics if t.context_id == targets[i])
        actual = [int(target) for line in topic.uhf_content
                  for target in re.findall(r"\[link:topic=(\d+)\]", line)]
        assert actual == expected, (i, rows[i][0])
        checked += len(actual)
    assert checked == 669
    payload = HelpJsonRenderer(help_doc, "utf-8").render_document()
    assert len(payload["topics"]) == 383
    assert all(e["topic_id"] in {int(i) for i in payload["topics"]}
               for group in payload["index"] for e in group["entries"])
