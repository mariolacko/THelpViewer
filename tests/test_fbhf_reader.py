import gzip
import hashlib
import json
from pathlib import Path
import re
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import detect_format_handler
from thelpviewer.server.converter.readers.fbhf import (
    FBHFBinaryParser, FBHFHelpReader, FBHFSourceParser, FBHFSourceReader, is_fbhf_source,
)
from thelpviewer.server.converter.writers.html import HelpHtmlRenderer
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


def _topic(paragraph: bytes, crossrefs: list[tuple[int, int, int]]) -> bytes:
    payload = bytearray(struct.pack("<HhHB", 10_000, 1, len(paragraph), 1))
    payload.extend(paragraph)
    payload.extend(struct.pack("<h", len(crossrefs)))
    for context_id, offset, length in crossrefs:
        payload.extend(struct.pack("<HhB", context_id, offset, length))
    return bytes(payload)


def _binary_fbhf() -> bytes:
    first = _topic(b"See target", [(1, 5, 6)])
    second = _topic(b"Target topic", [])
    first_offset = 12
    second_offset = first_offset + len(first)
    index_offset = second_offset + len(second)
    index = struct.pack("<HHii", 10_001, 2, first_offset, second_offset)
    file_size = index_offset + len(index)
    header = b"FBHF" + struct.pack("<II", file_size - 8, index_offset)
    return header + first + second + index


def test_source_reader_preserves_case_insensitive_cross_reference():
    source = (
        b".topic First=2\r\n"
        b"See {Second topic:second}.\r\n"
        b".topic Second=3\r\n"
        b"Target.\r\n"
    )

    document = FBHFSourceReader(source_name="sample.txt").read_bytes(source)
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()

    assert [ref.target_context for ref in document.topics[0].positional_keywords] == [3]
    assert payload["topics"]["2"]["content"] == ["See [link:topic=3]Second topic[/link]. "]


def test_binary_reader_preserves_cross_reference():
    document = FBHFHelpReader(source_name="sample.hlp").read_bytes(_binary_fbhf())
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()

    assert [ref.target_context for ref in document.topics[0].positional_keywords] == [1]
    assert payload["topics"]["0"]["content"] == ["See [link:topic=1]target[/link]"]


def _file(records, contexts, *, bp7=False, allocation=None):
    positions = []
    offset = 12
    for record in records:
        positions.append(offset)
        offset += len(record)
    if bp7:
        size = len(contexts) if allocation is None else allocation
        ids = [context for context, _record in contexts] + [0xFFFF] * (size - len(contexts))
        slots = [positions[record] for _context, record in contexts] + [-1] * (size - len(contexts))
        index = struct.pack("<HHH", 10_001, len(contexts), size)
        index += struct.pack(f"<{size}H", *ids) + struct.pack(f"<{size}i", *slots)
    else:
        slots = [-1] * (max((context for context, _record in contexts), default=-1) + 1)
        for context, record in contexts:
            slots[context] = positions[record]
        index = struct.pack("<HH", 10_001, len(slots)) + struct.pack(f"<{len(slots)}i", *slots)
    body = b"".join(records) + index
    return b"FBHF" + struct.pack("<II", len(body) + 4, offset) + body


@pytest.mark.parametrize("bp7", [False, True])
def test_empty_index_is_valid(bp7):
    document = FBHFHelpReader().read_bytes(_file([], [], bp7=bp7))
    assert document.topics == []


@pytest.mark.parametrize("bp7", [False, True])
def test_sparse_contexts_and_shared_record_keep_real_link_targets(bp7):
    data = _file([_topic(b"See alias", [(20, 5, 5)])], [(3, 0), (20, 0)],
                 bp7=bp7, allocation=10 if bp7 else None)
    document = FBHFHelpReader().read_bytes(data)
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()
    assert [topic.context_id for topic in document.topics] == [3, 20]
    assert payload["topics"]["3"]["content"] == ["See [link:topic=20]alias[/link]"]


def test_source_alias_context_is_retained_and_link_resolves_to_its_topic():
    source = (b".topic First=2, Shortcut=20\r\nSee {Alias:shortcut}.\r\n"
              b".topic Second=21\r\nOther topic.\r\n")
    document = FBHFSourceReader().read_bytes(source)
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()
    assert [topic.context_id for topic in document.topics] == [2, 21]
    assert document.topics[0].alias_contexts == [20]
    assert payload["topics"]["2"]["aliases"]["ids"] == [20]
    assert payload["topics"]["2"]["content"] == ["See [link:topic=2]Alias[/link]. "]
    assert any(entry["label"] == "Shortcut" and entry["topic_id"] == 2
               for group in payload["index"] for entry in group["entries"])


def test_source_number_scan_obeys_dos_eof():
    source = b".topic First=2\r\nText.\r\n\x1a\r\n.topic Ignored=99\r\n"
    document = FBHFSourceReader().read_bytes(source)
    assert document.metadata["name_to_num"] == {"First": 2}
    assert [topic.context_id for topic in document.topics] == [2]


def test_tvhc_builtin_contexts_do_not_consume_auto_numbers():
    source = (b".topic Open, OpenFile\r\nSee {Next}.\r\n"
              b".topic Next\r\nNext command.\r\n.topic Custom\r\nCustom.\r\n")
    document = FBHFSourceReader().read_bytes(source)
    assert document.metadata["name_to_num"] == {"Open": 0xFF02, "OpenFile": 3, "Next": 0xFF25, "Custom": 4}
    assert document.topics[0].alias_contexts == [3]
    assert [ref.target_context for ref in document.topics[0].positional_keywords] == [0xFF25]


def test_tvhc_explicit_number_overrides_builtin_and_advances_sequence():
    document = FBHFSourceReader().read_bytes(
        b".topic Open=20, Shortcut\r\nOpen.\r\n.topic Custom\r\nCustom.\r\n")
    assert document.metadata["name_to_num"] == {"Open": 20, "Shortcut": 21, "Custom": 22}


def test_tvhc_word_counter_wraps_at_65535():
    document = FBHFSourceReader().read_bytes(b".topic High=65535\r\nHigh.\r\n.topic Zero\r\nZero.\r\n")
    assert document.metadata["name_to_num"] == {"High": 65535, "Zero": 0}


@pytest.mark.parametrize("split", ["row", "paragraph"])
def test_global_cross_reference_is_balanced_across_text_boundaries(split):
    if split == "row":
        record = _topic(b"See link\rnext.", [(1, 5, 9)])
    else:
        record = (struct.pack("<Hh", 10_000, 2)
                  + struct.pack("<HB", 8, 1) + b"See link"
                  + struct.pack("<HB", 5, 1) + b"next."
                  + struct.pack("<hHhB", 1, 1, 5, 8))
    document = FBHFHelpReader().read_bytes(_file([record, _topic(b"Target", [])], [(0, 0), (1, 1)]))
    payload = HelpJsonRenderer(document, display_encoding="cp437").render_document()
    assert [ref.target_context for ref in document.topics[0].positional_keywords] == [1, 1]
    assert payload["topics"]["0"]["content"] == [
        "See [link:topic=1]link[/link]", "[link:topic=1]next[/link].",
    ]


@pytest.mark.parametrize("offset,fmt,value", [
    (4, "I", 0), (8, "I", 0), (8, "I", 1_000_000),
    (12, "H", 0), (14, "h", -1), (16, "H", 0xFFFF), (18, "B", 2),
    (29, "h", -1), (29, "h", 20), (33, "h", 0), (33, "h", -1), (35, "B", 255),
    (57, "H", 0), (59, "H", 255), (61, "i", -2), (61, "i", 0),
    (61, "i", 57), (65, "i", 35),
])
def test_invalid_object_fields_raise_value_error(offset, fmt, value):
    data = bytearray(_binary_fbhf())
    struct.pack_into("<" + fmt, data, offset, value)
    with pytest.raises(ValueError, match="FBHF"):
        FBHFHelpReader().read_bytes(bytes(data))


@pytest.mark.parametrize("cut", range(1, len(_binary_fbhf())))
def test_truncated_file_never_returns_partial_topics(cut):
    with pytest.raises(ValueError, match="FBHF"):
        FBHFHelpReader().read_bytes(_binary_fbhf()[:cut])


@pytest.mark.parametrize("record", [
    struct.pack("<Hh", 10_000, 0),  # missing reference count
    struct.pack("<HhH", 10_000, 1, 8),  # missing Wrap / text
    struct.pack("<HhHB", 10_000, 1, 8, 1) + b"x",  # short text
    struct.pack("<HhhH", 10_000, 0, 1, 0),  # incomplete reference
])
def test_topic_cannot_consume_following_topic_or_index(record):
    data = _file([record, _topic(b"Next", [])], [(0, 0), (1, 1)])
    with pytest.raises(ValueError, match="FBHF"):
        FBHFHelpReader().read_bytes(data)


@pytest.mark.parametrize("change", ["used", "unsorted", "duplicate", "negative-position"])
def test_invalid_bp7_index_is_rejected(change):
    data = bytearray(_file([_topic(b"One", []), _topic(b"Two", [])],
                           [(3, 0), (7, 1)], bp7=True, allocation=10))
    index = struct.unpack_from("<I", data, 8)[0]
    if change == "used":
        struct.pack_into("<H", data, index + 2, 11)
    elif change == "unsorted":
        struct.pack_into("<HH", data, index + 6, 7, 3)
    elif change == "duplicate":
        struct.pack_into("<HH", data, index + 6, 3, 3)
    else:
        struct.pack_into("<i", data, index + 6 + 20, -1)
    with pytest.raises(ValueError, match="FBHF"):
        FBHFHelpReader().read_bytes(bytes(data))


def _paragraph_topic(paragraphs, refs=()):
    data = bytearray(struct.pack("<Hh", 10_000, len(paragraphs)))
    for wrap, text in paragraphs:
        data.extend(struct.pack("<HB", len(text), int(wrap)))
        data.extend(text)
    data.extend(struct.pack("<h", len(refs)))
    for ref in refs:
        data.extend(struct.pack("<HhB", *ref))
    return bytes(data)


@pytest.mark.parametrize("wrap", [False, True])
def test_cr_consumes_one_byte_without_adding_an_extra_terminal_row(wrap):
    text = b"\r\rTitle  \r\r End \r"
    document = FBHFHelpReader().read_bytes(_file([_paragraph_topic([(wrap, text)])], [(0, 0)]))
    assert document.topics[0].raw_lines == [b"", b"", b"Title  ", b"", b" End "]
    assert HelpJsonRenderer(document).render_document()["topics"]["0"]["content"] == [
        "", "", "Title  ", "", " End ",
    ]


def test_empty_paragraph_has_no_rows_but_an_authored_cr_has_one():
    record = _paragraph_topic([(True, b""), (False, b"\r"), (True, b"Title")])
    document = FBHFHelpReader().read_bytes(_file([record], [(0, 0)]))
    assert document.topics[0].raw_lines == [b"", b"Title"]


@pytest.mark.parametrize("bp7", [False, True])
def test_wrapping_obeys_original_help_window_width_and_keeps_consumed_spaces(bp7):
    text = b"first " * 10 + b"end"
    document = FBHFHelpReader().read_bytes(_file([_topic(text, [])], [(0, 0)], bp7=bp7))
    assert document.metadata["display_width"] == 46
    assert document.topics[0].raw_lines == [b"first " * 7, b"first " * 3 + b"end"]
    assert HelpJsonRenderer(document).render_document()["metadata"]["display"]["cols"] == 46
    assert HelpHtmlRenderer(document)._window_geometry() == (50, 18)


def test_nonwrapping_paragraph_is_not_word_wrapped_or_indented():
    text = b"X" * 100 + b"\r tail  \r"
    record = _paragraph_topic([(False, text)])
    document = FBHFHelpReader().read_bytes(_file([record], [(0, 0)]))
    assert document.topics[0].raw_lines == [b"X" * 100, b" tail  "]


@pytest.mark.parametrize("fill", [b"X", b"\xff"])
def test_long_nonbreaking_reference_keeps_fragments_and_never_enters_the_text(fill):
    # Ordinary space before the label is a wrap delimiter; FF inside it is not.
    label = fill * 60
    text = b"A " + label + b" end"
    document = FBHFHelpReader().read_bytes(_file([_topic(text, [(0, 3, 60)])], [(0, 0)]))
    topic = document.topics[0]
    visible = label.replace(b"\xff", b" ")
    assert topic.raw_lines == [b"A ", visible[:46], visible[46:] + b" end"]
    assert topic.sequential_keywords == []
    assert [(ref.target_context, ref.line, ref.first_column, ref.last_column)
            for ref in topic.positional_keywords] == [(0, 2, 1, 46), (0, 3, 1, 14)]
    payload = HelpJsonRenderer(document).render_document()
    assert payload["topics"]["0"]["content"] == [
        "A ", f"[link:topic=0]{visible[:46].decode()}[/link]",
        f"[link:topic=0]{visible[46:].decode()}[/link] end",
    ]


def test_nonbreaking_spaces_are_normalized_only_after_wrap_and_reference_positioning():
    text = b"X" * 35 + b" Long\xfflabel end"
    document = FBHFHelpReader().read_bytes(_file([_topic(text, [(0, 37, 10)])], [(0, 0)]))
    assert document.topics[0].raw_lines == [b"X" * 35 + b" Long label ", b"end"]
    ref = document.topics[0].positional_keywords[0]
    assert (ref.line, ref.first_column, ref.last_column) == (1, 37, 46)
    assert HelpJsonRenderer(document).render_document()["topics"]["0"]["content"] == [
        "X" * 35 + " [link:topic=0]Long label[/link] ", "end",
    ]


def test_wrap_split_reference_counts_cr_and_paragraph_bytes_without_trimming_cells():
    text = b"one " * 12 + b"\r"
    record = _paragraph_topic([(True, text), (False, b"\rnext\r")], [(0, 41, 14)])
    document = FBHFHelpReader().read_bytes(_file([record], [(0, 0)]))
    assert document.topics[0].raw_lines == [b"one " * 11, b"one ", b"", b"next"]
    assert [(ref.line, ref.first_column, ref.last_column)
            for ref in document.topics[0].positional_keywords] == [(1, 41, 44), (2, 1, 4), (4, 1, 4)]
    assert HelpJsonRenderer(document).render_document()["topics"]["0"]["content"] == [
        "one " * 10 + "[link:topic=0]one [/link]", "[link:topic=0]one [/link]",
        "", "[link:topic=0]next[/link]",
    ]


def test_literal_02_is_a_character_not_an_inserted_hotspot_delimiter():
    text = b"\x02 [x] link"
    document = FBHFHelpReader().read_bytes(_file([_topic(text, [(0, 7, 4)])], [(0, 0)]))
    assert document.topics[0].raw_lines == [text]
    assert HelpJsonRenderer(document).render_document()["topics"]["0"]["content"] == [
        "☻ [[x] [link:topic=0]link[/link]",
    ]
    assert HelpHtmlRenderer(document)._render_topic_lines(document.topics[0])[1] == (
        '☻ [x] <a href="0000.html">link</a>'
    )


def test_unsorted_reference_array_still_links_the_correct_columns():
    document = FBHFHelpReader().read_bytes(_file([_topic(b"one two", [(0, 5, 3), (0, 1, 3)])], [(0, 0)]))
    assert HelpJsonRenderer(document).render_document()["topics"]["0"]["content"] == [
        "[link:topic=0]one[/link] [link:topic=0]two[/link]",
    ]


def test_missing_destination_preserves_label_without_binding_a_different_context():
    document = FBHFHelpReader().read_bytes(_file([_topic(b"See target", [(99, 5, 6)])], [(0, 0)]))
    assert document.topics[0].positional_keywords[0].target_context == 99
    assert HelpJsonRenderer(document).render_document()["topics"]["0"]["content"] == ["See target"]


def test_tvhc_and_binary_paragraphs_use_the_same_layout_and_reference_coordinates():
    source = b".topic First=2\r\nTitle\r\n" + b"word " * 15 + b"{linked text:First}\r\n\r\n fixed\r\n"
    compiled = _paragraph_topic([
        (True, b"Title " + b"word " * 15 + b"linked\xfftext "),
        (False, b"\r fixed\r"),
    ], [(2, 82, 11)])
    text_doc = FBHFSourceReader().read_bytes(source)
    binary_doc = FBHFHelpReader().read_bytes(_file([compiled], [(2, 0)]))
    assert text_doc.topics[0].raw_lines == binary_doc.topics[0].raw_lines
    assert text_doc.topics[0].positional_keywords == binary_doc.topics[0].positional_keywords
    assert HelpJsonRenderer(text_doc).render_document()["topics"]["2"]["content"] == (
        HelpJsonRenderer(binary_doc).render_document()["topics"]["2"]["content"]
    )


@pytest.mark.parametrize("name,source_hash,topic_count,row_count,cell_count,ref_count,row_hash,ref_hash", [
    ("DEMOHELP.HLP", "84eb6628aa9b8967156989c5bf0dfbe78a1aefee4531acd98c25bbcff3f254e1",
     39, 483, 13725, 40, "34f2eb460c78972e7b639514f5bb683fbae885709c8bcefc0a44b6c00489f809",
     "eb60191e449bb92d1e992004800b54961cae072eb74c63793ce0c20511ed44f8"),
    ("DEMOHELP_BP7.HLP", "2cb9bc120644d7b83b2a6b1efd146c4ee35d8cf437d2b77dde779e933feadd35",
     55, 592, 16981, 47, "50c9e1533888aac229a4ca1991db7bb714f61bf92259f0d3d0d8fbd35ba7b8ee",
     "b76aed3cd5bc0872a13e97cbd67c4409404d3627570da1f850043f0231ddac12"),
])
def test_reference_corpus_matches_original_paragraph_routine(
        name, source_hash, topic_count, row_count, cell_count, ref_count, row_hash, ref_hash):
    # Optional neighbouring research originals, never copied into the HELP catalog.
    path = Path(__file__).resolve().parents[2] / "HelpTools" / "samples" / name
    if not path.is_file():
        pytest.skip("FBHF reference original unavailable")
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == source_hash
    document = FBHFHelpReader().read_bytes(data)
    assert len(document.topics) == topic_count
    assert sum(len(topic.raw_lines) for topic in document.topics) == row_count
    assert sum(len(row) for topic in document.topics for row in topic.raw_lines) == cell_count
    # Digest measured by the native 16-bit routine independently of the reader.
    rows = [[topic.context_id, [row.hex() for row in topic.raw_lines]] for topic in document.topics]
    assert hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest() == row_hash
    locations = [[topic.context_id,
                  [[ref.target_context, ref.first_column - 1, ref.line,
                    ref.last_column - ref.first_column + 1] for ref in topic.positional_keywords]]
                 for topic in document.topics]
    assert hashlib.sha256(json.dumps(locations, separators=(",", ":")).encode()).hexdigest() == ref_hash
    parsed, _ = FBHFBinaryParser(data).parse()
    assert sum(len(refs) for _names, _context, _paragraphs, refs in parsed) == ref_count
    payload = HelpJsonRenderer(document).render_document()
    exported = []
    for topic in document.topics:
        lines = payload["topics"][str(topic.context_id)]["content"]
        for line in lines:
            exported.extend(re.findall(r"\[link:topic=(\d+)\](.*?)\[/link\]", line))
    assert len(exported) == ref_count
    assert {int(target) for target, _label in exported} <= {topic.context_id for topic in document.topics}


def test_staged_server_build_keeps_wrap_links_and_refuses_unrepresentable_rows(tmp_path):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / "Borland FBHF" / "sample.hlp"
    copy.parent.mkdir(parents=True)
    text = b"one " * 12 + b"\rnext"
    original = _file([_topic(text, [(0, 41, 12)])], [(0, 0)])
    copy.write_bytes(original)
    assert build_help_groups(["borland"], sources, helps)["bundles"] == 1
    catalog = json.loads((helps / "catalog.json").read_text())
    assert len(catalog) == 1
    assert catalog[0]["file"] == "Borland FBHF/sample.json.gz"
    assert catalog[0]["source_file"] == "sample.hlp"
    payload = json.loads(gzip.decompress((helps / catalog[0]["file"]).read_bytes()))
    assert payload["metadata"]["display"]["cols"] == 46
    assert payload["topics"]["0"]["content"] == [
        "one " * 10 + "[link:topic=0]one [/link]", "[link:topic=0]one [/link]",
        "[link:topic=0]nex[/link]t",
    ]
    published = {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    copy.write_bytes(_file([_paragraph_topic([(False, b"X" * 256)])], [(0, 0)]))
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["borland"], sources, helps)
    assert published == {path.relative_to(helps): path.read_bytes() for path in helps.rglob("*") if path.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    copy.write_bytes(original)
    result = build_help_groups(["borland"], sources, helps)
    backup = Path(result["backup"])
    assert result["bundles"] == 1
    assert published == {path.relative_to(backup): path.read_bytes() for path in backup.rglob("*") if path.is_file()}


@pytest.mark.parametrize("header", [b".TOPIC", b".ToPiC", b". topic", b".\x08TOPIC"])
def test_tvhc_topic_command_is_case_insensitive_and_uses_native_token_spacing(header):
    data = header + b" First \x08= 2 , Alias=20\r\nSee {alias}.\r\n"
    assert is_fbhf_source(data)
    assert detect_format_handler("sample.txt", data).name == "fbhf-source"
    document = FBHFSourceReader().read_bytes(data)
    assert document.metadata["name_to_num"] == {"First": 2, "Alias": 20}
    assert document.topics[0].alias_contexts == [20]
    assert HelpJsonRenderer(document).render_document()["topics"]["2"]["content"] == [
        "See [link:topic=2]alias[/link]. ",
    ]


def test_detection_does_not_confuse_a_quoted_command_or_comment_with_a_real_header():
    assert not is_fbhf_source(b"Text mentions .topic A=2\r\n")
    assert not is_fbhf_source(b";Example: .topic A=2\r\n")
    assert not is_fbhf_source(b".topical A=2\r\n")
    assert not is_fbhf_source(b"\x1a\r\n.topic A=2\r\n")
    assert is_fbhf_source(b";COMMENT TurboVision FBHF format, 0 topics\r\n")
    data = b";Preamble\r\n" * 500 + b".TOPIC A=2\r\nText\r\n"
    assert is_fbhf_source(data)  # A legitimate preamble is not limited to 4096 bytes.
    assert len(FBHFSourceReader().read_bytes(data).topics) == 1


def test_embedded_topic_example_does_not_override_another_text_help_format():
    data = b"@Example\r\n:First\r\n.topic Foo=2\r\nText\r\n"
    assert not is_fbhf_source(data)
    assert detect_format_handler("ASM.TXT", data).name == "helppc"
    assert not is_fbhf_source(b"Introductory prose\r\n.topic A=2\r\nText\r\n")


def test_explicit_source_reader_can_read_an_empty_native_source_without_a_detector_banner():
    assert FBHFSourceReader().read_bytes(b";Comment only\r\n\r\n\x1a").topics == []


@pytest.mark.parametrize("header", [b".topic", b".topic A,", b".topic A=", b".topic A=wrong",
                                     b".topic A=-1", b".topic A=65536", b".topic A=2x"])
def test_malformed_topic_definition_has_a_source_line_diagnostic(header):
    with pytest.raises(ValueError, match=r"TVHC broken.txt line 2:"):
        FBHFSourceReader(source_name="broken.txt").read_bytes(b";Comment\r\n" + header + b"\r\nText\r\n")


@pytest.mark.parametrize("source,line", [
    (b".topic A=2\r\nText\r\n.topic a=3\r\nOther\r\n", 3),
    (b".topic A=2,A=3\r\nText\r\n", 1),
])
def test_symbol_redefinition_is_rejected_instead_of_overwriting_a_topic(source, line):
    with pytest.raises(ValueError, match=rf"line {line}: redefinition of topic name"):
        FBHFSourceReader().read_bytes(source)


def test_name_folding_changes_only_ascii_letters_not_high_dos_bytes():
    data = b".topic \xdf=2\r\nSee {ss}.\r\n.topic ss=3\r\nSee {\xdf}.\r\n"
    document = FBHFSourceReader().read_bytes(data)
    assert document.metadata["name_to_num"] == {"ß": 2, "ss": 3}
    assert [[ref.target_context for ref in topic.positional_keywords] for topic in document.topics] == [[3], [2]]
    assert document.metadata["unresolved_topic_names"] == []


def test_numeric_context_replacement_keeps_other_aliases_and_moves_symbolic_references():
    source = (b".topic First=2,Alias=20\r\nSee {First} {Alias} {Replacement}.\r\n"
              b".topic Replacement=2\r\nNew text.\r\n")
    document = FBHFSourceReader().read_bytes(source)
    assert [topic.context_id for topic in document.topics] == [20, 2]
    assert [topic.names for topic in document.topics] == [["Alias"], ["Replacement", "First"]]
    assert all(topic.alias_contexts == [] for topic in document.topics)
    payload = HelpJsonRenderer(document).render_document()
    assert payload["topics"]["20"]["content"] == [
        "See [link:topic=2]First[/link] [link:topic=20]Alias[/link] [link:topic=2]Replacement[/link]. ",
    ]
    assert payload["topics"]["2"]["content"] == ["New text. "]
    assert {entry["label"]: entry["topic_id"] for group in payload["index"] for entry in group["entries"]} == {
        "First": 2, "Alias": 20, "Replacement": 2,
    }


def test_complete_numeric_replacement_keeps_only_the_current_indexed_object():
    source = b".topic Old=2\r\nOld text.\r\n.topic New=2\r\nSee {Old}.\r\n"
    document = FBHFSourceReader().read_bytes(source)
    assert len(document.topics) == 1
    assert document.topics[0].names == ["New", "Old"]
    assert HelpJsonRenderer(document).render_document()["topics"]["2"]["content"] == [
        "See [link:topic=2]Old[/link]. ",
    ]


def test_multiple_symbolic_names_for_one_numeric_alias_do_not_duplicate_alias_ids():
    source = b".topic A=2,B=2,C=20,D=20\r\nSee {D}.\r\n"
    document = FBHFSourceReader().read_bytes(source)
    assert document.topics[0].names == ["A", "B", "C", "D"]
    assert document.topics[0].alias_contexts == [20]
    assert document.topics[0].positional_keywords[0].target_context == 2


@pytest.mark.parametrize("text,expected", [
    (b"{{A}", b"{A}"), (b"{{{A}", b"{{A}"), (b"{{{{A}", b"{{A"),
    (b"{{literal} {A}", b"{literal} A"), (b"{A}{A}", b"AA"),
])
def test_brace_escaping_uses_the_original_mutating_scanner_cursor(text, expected):
    parser = FBHFSourceParser(b".topic A=2\r\n" + text + b"\r\n")
    topics, _ = parser.parse()
    assert topics[0][2] == [(True, expected + b" ")]
    refs = topics[0][3]
    assert [(target, offset, length) for target, offset, length in refs] == (
        [("A", 11, 1)] if text == b"{{literal} {A}" else
        [("A", 1, 1), ("A", 2, 1)] if text == b"{A}{A}" else
        [("A", 3, 1)] if text == b"{{{{A}" else []
    )


def test_unterminated_reference_aborts_with_its_actual_line_not_partial_plain_text():
    source = b".topic A=2\r\n First\r\n\r\nSee {unfinished\r\n.topic B=3\r\nOther\r\n"
    with pytest.raises(ValueError, match=r"TVHC sample.txt line 4: unterminated topic reference"):
        FBHFSourceReader(source_name="sample.txt").read_bytes(source)


def test_unresolved_reference_retains_the_native_ffff_placeholder_and_diagnostics():
    source = b".topic A=2\r\nSee {shown:Missing} and {missing}.\r\n"
    document = FBHFSourceReader().read_bytes(source)
    assert [ref.target_context for ref in document.topics[0].positional_keywords] == [0xFFFF, 0xFFFF]
    assert document.metadata["unresolved_topic_names"] == ["Missing"]
    payload = HelpJsonRenderer(document).render_document()
    assert payload["metadata"]["unresolved_topic_names"] == ["Missing"]
    assert payload["topics"]["2"]["content"] == ["See shown and missing. "]


def test_native_unresolved_ffff_word_can_address_a_real_ffff_context():
    source = b".topic A=2\r\nSee {missing}.\r\n.topic Last=65535\r\nLast text.\r\n"
    document = FBHFSourceReader().read_bytes(source)
    assert document.metadata["unresolved_topic_names"] == ["missing"]
    assert HelpJsonRenderer(document).render_document()["topics"]["2"]["content"] == [
        "See [link:topic=65535]missing[/link]. ",
    ]


def test_unknown_command_or_text_before_a_topic_is_not_silently_ignored():
    with pytest.raises(ValueError, match=r"line 3: unknown directive"):
        FBHFSourceReader().read_bytes(b".topic A=2\r\nText\r\n.screen B\r\nOther\r\n")
    with pytest.raises(ValueError, match=r"line 1: expected a .topic definition"):
        FBHFSourceReader().read_bytes(b"Unowned text\r\n.topic A=2\r\nOther\r\n")


def test_native_physical_line_limit_does_not_count_crlf_or_split_other_low_bytes():
    source = b".topic A=2\r\n " + b"X" * 252 + b"\r\n \x0b\x0c\x1e\x1f\r\n"
    document = FBHFSourceReader().read_bytes(source)
    assert document.topics[0].raw_lines == [b" " + b"X" * 252, b" \x0b\x0c\x1e\x1f"]
    with pytest.raises(ValueError, match=r"line 2: physical line exceeds.*253"):
        FBHFSourceReader().read_bytes(b".topic A=2\r\n " + b"X" * 253 + b"\r\n")


def test_only_a_standalone_1a_ends_source_not_a_literal_arrow_at_line_start():
    source = b".topic A=2\r\n\x1a text\r\n.topic B=3\r\nOther\r\n\x1a\r\n.topic Ignored=4\r\n"
    parser = FBHFSourceParser(source)
    topics, numbers = parser.parse()
    assert numbers == {"A": 2, "B": 3}
    assert topics[0][2] == [(True, b"\x1a text ")]
    assert HelpJsonRenderer(FBHFSourceReader().read_bytes(source)).render_document()["topics"]["2"]["content"] == [
        "→ text ",
    ]


def test_paragraph_limit_includes_join_bytes_and_leading_crs():
    parser = FBHFSourceParser(b".topic A=2\r\n" + b"abc\r\n" * 1024)
    topics, _ = parser.parse()
    assert len(topics[0][2][0][1]) == 4096
    with pytest.raises(ValueError, match=r"line 1026: paragraph exceeds.*4096"):
        FBHFSourceReader().read_bytes(b".topic A=2\r\n" + b"abc\r\n" * 1025)
    with pytest.raises(ValueError, match=r"paragraph exceeds.*4096"):
        FBHFSourceReader().read_bytes(b".topic A=2\r\n\r\n" + b"abc\r\n" * 1024)


def test_reference_offsets_and_counts_must_fit_the_persisted_signed_fields():
    blocks = (b" " + b"X" * 252 + b"\r\n") * 15 + b"\r\n"
    with pytest.raises(ValueError, match="reference offset exceeds the signed 16-bit field"):
        FBHFSourceReader().read_bytes(b".topic A=2\r\n" + blocks * 9 + b" {A}\r\n")
    with pytest.raises(ValueError, match="topic count exceeds a signed 16-bit field"):
        FBHFSourceReader().read_bytes(b".topic A=2\r\n" + (b"{}" * 126 + b"\r\n") * 261)


def test_complete_native_bp7_source_reconstructs_every_byte_of_the_reference_file():
    root = Path(__file__).resolve().parents[2]
    source_path = root / "TVisionJS/references/turbovision-delphi/Demos/Demohelp.txt"
    binary_path = root / "HelpTools/samples/DEMOHELP_BP7.HLP"
    if not source_path.is_file() or not binary_path.is_file():
        pytest.skip("Native TVHC source/reference pair unavailable")
    source, binary = source_path.read_bytes(), binary_path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == "62cbe3bab97c16cf3f28a51dc489cb487dfd104d86d9cd5ba8d01e741192c99b"
    parser = FBHFSourceParser(source)
    topics, numbers = parser.parse()
    assert len(topics) == 55
    assert sum(len(refs) for _names, _context, _paragraphs, refs in topics) == 47
    assert parser.unresolved_names == []
    folded = {name.upper(): context for name, context in numbers.items()}
    records = [_paragraph_topic(paragraphs, [(folded[target.upper()], offset, length)
                                           for target, offset, length in refs])
               for _names, _context, paragraphs, refs in topics]
    contexts = sorted((numbers[name], index) for index, (names, _context, _paragraphs, _refs)
                      in enumerate(topics) for name in names)
    reconstructed = _file(records, contexts, bp7=True, allocation=60)
    assert reconstructed == binary
    assert hashlib.sha256(reconstructed).hexdigest() == "2cb9bc120644d7b83b2a6b1efd146c4ee35d8cf437d2b77dde779e933feadd35"
    source_doc = FBHFSourceReader().read_bytes(source)
    binary_doc = FBHFHelpReader().read_bytes(binary)
    source_content = HelpJsonRenderer(source_doc).render_document()["topics"]
    binary_content = HelpJsonRenderer(binary_doc).render_document()["topics"]
    assert {context: topic["content"] for context, topic in source_content.items()} == {
        context: topic["content"] for context, topic in binary_content.items()
    }


@pytest.mark.parametrize("broken", [b"{unclosed", b"X" * 254, b".screen B"])
def test_staged_source_build_refuses_partial_output_and_retry_keeps_native_commands(tmp_path, broken):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    path = sources / "Borland FBHF/source.txt"
    path.parent.mkdir(parents=True)
    valid = b".TOPIC First=2\r\nSee {Alias}.\r\n.TOPIC Other=3,Alias=20\r\nTarget\r\n"
    path.write_bytes(valid)
    assert build_help_groups(["borland"], sources, helps)["bundles"] == 1
    catalog = json.loads((helps / "catalog.json").read_text())
    payload = json.loads(gzip.decompress((helps / catalog[0]["file"]).read_bytes()))
    assert payload["topics"]["2"]["content"] == ["See [link:topic=3]Alias[/link]. "]
    published = {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    path.write_bytes(b".TOPIC First=2\r\n" + broken + b"\r\n")
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["borland"], sources, helps)
    assert published == {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    path.write_bytes(valid)
    assert build_help_groups(["borland"], sources, helps)["bundles"] == 1
