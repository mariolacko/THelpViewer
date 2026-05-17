import pytest

from pathlib import Path

from thelpviewer.converter.exporter import detect_format_handler
from thelpviewer.converter.readers.tdh import (
    TdhHelpReader,
    _signed_tdh_delta,
    _tdh_runtime_table_word_count,
    is_tdh_binary,
    is_tfh_binary,
    probe_tdh_binary,
    probe_tfh_binary,
)
from thelpviewer.converter.readers.thelp import is_thelp_binary


TDH_SAMPLE = Path("sources/Borland Turbo Debugger 1.0/TDHELP.TDH")
TDH_SAMPLE_2X = Path("sources/Borland Turbo Assembler 1.0 with Turbo Debugger/TDHELP.TDH")
TFH_SAMPLE = Path("sources/Borland Turbo Profiler/TFHELP.TFH")


def test_tdh_sample_is_detected_separately_from_thelp():
    data = TDH_SAMPLE.read_bytes()

    assert is_tdh_binary(data)
    assert not is_thelp_binary(data)

    handler = detect_format_handler(TDH_SAMPLE, data)
    assert handler is not None
    assert handler.name == "tdh"


def test_tdh_2x_sample_is_detected_separately_from_thelp():
    data = TDH_SAMPLE_2X.read_bytes()

    assert is_tdh_binary(data)
    assert not is_thelp_binary(data)

    handler = detect_format_handler(TDH_SAMPLE_2X, data)
    assert handler is not None
    assert handler.name == "tdh"


def test_tdh_samples_share_early_payload_prefix_after_lead_byte():
    legacy_data = TDH_SAMPLE.read_bytes()
    later_data = TDH_SAMPLE_2X.read_bytes()
    legacy_probe = probe_tdh_binary(legacy_data)
    later_probe = probe_tdh_binary(later_data)

    assert legacy_probe is not None
    assert later_probe is not None

    legacy_payload = legacy_data[legacy_probe.encoded_payload_offset :]
    later_payload = later_data[later_probe.encoded_payload_offset :]

    assert legacy_payload[1 : 1 + 54] == later_payload[1 : 1 + 54]
    assert legacy_payload[0x37] == 0x83
    assert later_payload[0x37] == 0x91

    early_differences = [
        (legacy_payload[index], later_payload[index])
        for index in range(0x37, min(len(legacy_payload), len(later_payload), 0x00C7))
        if legacy_payload[index] != later_payload[index]
    ]
    assert (0x83, 0x91) in early_differences
    assert (0xD1, 0xDF) in early_differences
    assert (0xCF, 0xDD) in early_differences


def test_tdh_sample_families_split_at_pre_separator_runtime_width():
    legacy_data = TDH_SAMPLE.read_bytes()
    later_data = TDH_SAMPLE_2X.read_bytes()
    legacy_probe = probe_tdh_binary(legacy_data)
    later_probe = probe_tdh_binary(later_data)

    assert legacy_probe is not None
    assert later_probe is not None

    legacy_pre_separator_words = (legacy_probe.separator_offset - 2) // 2
    later_pre_separator_words = (later_probe.separator_offset - 2) // 2

    legacy_document = TdhHelpReader(source_name=TDH_SAMPLE.name, source_path=TDH_SAMPLE).read_bytes(legacy_data)
    later_document = TdhHelpReader(source_name=TDH_SAMPLE_2X.name, source_path=TDH_SAMPLE_2X).read_bytes(later_data)

    assert legacy_pre_separator_words == 518
    assert legacy_document.metadata["tdh_decode"]["runtime_table_word_count"] == 530
    assert legacy_document.metadata["tdh_decode"]["runtime_table_word_count"] - legacy_pre_separator_words == 12

    assert later_pre_separator_words == 596
    assert later_document.metadata["tdh_decode"]["runtime_table_word_count"] == 596
    assert later_document.metadata["tdh_decode"]["runtime_table_word_count"] == later_pre_separator_words


def test_tdh_reader_preserves_probe_metadata():
    data = TDH_SAMPLE.read_bytes()
    probe = probe_tdh_binary(data)

    assert probe is not None
    assert probe.table_byte_size == 0x0206
    assert probe.table_word_count == 259
    assert probe.left_table_offset == 0x0002
    assert probe.right_table_offset == 0x0208
    assert probe.separator_offset == 0x040E
    assert probe.separator_word == 1
    assert probe.encoded_payload_offset == 0x410
    assert probe.payload_lead_byte == 0xA0
    assert probe.payload_lead_cc_run == 9
    assert probe.payload_prefix_hex.startswith("A0 CC CC CC CC CC CC CC CC CC")
    assert probe.crc32 == 0xA9C668A7

    document = TdhHelpReader(source_name=TDH_SAMPLE.name, source_path=TDH_SAMPLE).read_bytes(data)
    assert document.format_name == "tdh"
    assert document.metadata["format_status"] == "decoded"
    assert document.metadata["help_contents_topic_id"] == 1
    assert document.metadata["tdh_decode"]["runtime_context_count"] == 530
    assert document.metadata["tdh_decode"]["runtime_table_word_count"] == 0x212
    assert document.metadata["tdh_decode"]["runtime_block_offset"] == 0x040E
    assert document.metadata["tdh_decode"]["negative_delta_count"] == 8
    assert document.metadata["tdh_probe"]["payload_lead_byte"] == "0xA0"
    assert len(document.topics) == 530
    assert all(
        0 < keyword.target_context < len(document.topics)
        for topic in document.topics
        for keyword in topic.positional_keywords
    )
    assert document.topics[0].names[0] == "Context 0"
    assert document.topics[1].uhf_content[0].strip() == "HELP INDEX"
    help_index_text = "\n".join(document.topics[1].uhf_content)
    assert "[link:topic=2]Help on Help[/link]" in help_index_text
    assert "[link:topic=387]Assembler[/link]" in help_index_text
    assert document.topics[1].next_context == 416
    assert document.contents[0].label == "Help on Help"
    assert document.contents[0].topic_id == 2

    alias_metadata = document.metadata["tdh_decode"]
    redirected_topics = [topic for topic in document.topics if topic.redirect_context is not None]
    assert alias_metadata["embedded_alias_context_count"] + alias_metadata["text_alias_context_count"] == len(redirected_topics)
    assert alias_metadata["out_of_range_page_word_context_count"] >= len(redirected_topics)
    assert alias_metadata["remaining_unresolved_alias_context_count"] == (
        alias_metadata["out_of_range_page_word_context_count"] - len(redirected_topics)
    )
    assert len(alias_metadata["out_of_range_page_word_contexts"]) == alias_metadata["out_of_range_page_word_context_count"]
    assert len(alias_metadata["embedded_alias_contexts"]) == alias_metadata["embedded_alias_context_count"]
    assert len(alias_metadata["text_alias_contexts"]) == alias_metadata["text_alias_context_count"]
    assert len(alias_metadata["remaining_unresolved_alias_contexts"]) == alias_metadata["remaining_unresolved_alias_context_count"]
    assert alias_metadata["out_of_range_page_word_contexts"] == [519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529]
    assert alias_metadata["embedded_alias_contexts"] == [519, 520, 521, 522, 523, 524, 525, 526, 527, 529]
    assert alias_metadata["text_alias_contexts"] == [528]
    assert alias_metadata["remaining_unresolved_alias_contexts"] == []
    assert alias_metadata["empty_placeholder_contexts"] == []
    assert alias_metadata["embedded_alias_contexts"] == sorted(alias_metadata["embedded_alias_contexts"])
    assert alias_metadata["text_alias_contexts"] == sorted(alias_metadata["text_alias_contexts"])
    assert alias_metadata["remaining_unresolved_alias_contexts"] == sorted(alias_metadata["remaining_unresolved_alias_contexts"])
    assert set(alias_metadata["embedded_alias_contexts"]) | set(alias_metadata["text_alias_contexts"]) == {
        topic.context_id for topic in redirected_topics
    }
    assert set(alias_metadata["embedded_alias_contexts"]) | set(alias_metadata["text_alias_contexts"]) | set(alias_metadata["remaining_unresolved_alias_contexts"]) == set(alias_metadata["out_of_range_page_word_contexts"])

    assembler = next(topic for topic in document.topics if topic.context_id == 387)
    assert assembler.uhf_content[0] == "The syntax for assembler statements closely"
    assert assembler.uhf_content[1] == "follows that of Turbo Assembler."

    expression = next(topic for topic in document.topics if topic.context_id == 463)
    assert expression.uhf_content[0] == "An assembler expression can have the following"
    assert expression.uhf_content[1] == "elements:"
    assert [(keyword.target_context, keyword.line, keyword.first_column, keyword.last_column) for keyword in expression.positional_keywords[:4]] == [
        (467, 3, 1, 9),
        (468, 3, 14, 20),
        (469, 3, 25, 33),
        (465, 3, 38, 46),
    ]

    function_keys = next(topic for topic in document.topics if topic.context_id == 380)
    assert function_keys.uhf_content == [
        "",
        "You can use the following keys to control the",
        "cursor position in Text panes:",
        "",
        "↑          Move cursor up one line",
        "↓          Move cursor down one line",
        "→          Move cursor right one character",
        "←          Move cursor left one character",
        "Ctrl →     Move right one word",
        "Ctrl ←     Move left one word",
        "PgUp        Move up one page",
        "PgDn        Move down one page",
    ]
    assert function_keys.positional_keywords == []

    function_commands = next(topic for topic in document.topics if topic.context_id == 382)
    assert function_commands.uhf_content == [
        "",
        "There are function keys for many commonly used",
        "functions.  Many of the Alt, Ctrl, and Shifted",
        "versions of the function keys also invoke",
        "commands, as described here.",
        "",
        "The ordinary function keys invoke the following",
        "commands:",
        "",
        "[link:topic=2]F1  Help[/link]              [link:topic=388]F2  Toggle Breakpoint[/link]",
        "[link:topic=66]F3  Close Window[/link]      [link:topic=50]F4  Run to Cursor[/link]",
        "[link:topic=65]F5  Zoom Window[/link]       [link:topic=62]F6  Next Window[/link]",
        "[link:topic=46]F7  Trace Into[/link]        [link:topic=47]F8  Step Over[/link]",
        "[link:topic=48]F9  Run[/link]               [link:topic=373]F10 Command menu[/link]",
    ]

    move_left = next(topic for topic in document.topics if topic.context_id == 521)
    assert move_left.uhf_content == [
        "  Move left one word",
        "PgUp        Move up one page",
        "PgDn        Move down one page",
    ]

    integer_format = next(topic for topic in document.topics if topic.context_id == 79)
    assert integer_format.uhf_content == [
        "",
        "The Integer Format command lets you choose how",
        "numbers are displayed in Inspectors and the",
        "watches window.  You can choose one of the",
        "following formats:",
        "",
        "■ Hex: shows the hexadecimal value only, using",
        "  the hex number format of the current language.",
        "",
        "■ Decimal: shows decimal value only.",
        "",
        "■ Both: shows the decimal value followed by the",
        "  hex value in parentheses.",
    ]
    assert integer_format.positional_keywords == []
    expression_format = next(topic for topic in document.topics if topic.context_id == 392)
    assert expression_format.uhf_content == [
        "",
        "When you supply an expression to be displayed,",
        "Turbo Debugger displays it in a suitable format",
        "based on what type of data it is.  If you wish to",
        "change the default display format for an",
        "expression, place a comma at the end of the",
        "expression, then supply an optional repeat count",
        "followed by an optional format letter.  You can",
        "only supply a repeat count for pointers or",
        "arrays.  If you use a format control on the wrong",
        "data type, it has no effect.",
    ]
    assert expression_format.positional_keywords == []

    character_format = next(topic for topic in document.topics if topic.context_id == 393)
    assert character_format.uhf_content == [
        "     Displays a character or string expression",
        "     as raw characters.  Normally, non-printing",
        "     character values are displayed as some type",
        "     of escape or numeric format.  This option",
        "     forces the characters to be displayed using",
        "     the full IBM display character set.",
        "",
        "d    Displays an integer as a decimal number.",
        "",
        "f#   Displays a floating-point format with the",
        "     specified number of digits.  If you don't",
        "     supply a number of digits, as many as",
        "     necessary are used.",
    ]
    assert character_format.positional_keywords == []

    memory_format = next(topic for topic in document.topics if topic.context_id == 394)
    assert memory_format.uhf_content == [
        "",
        "m    Displays a memory-referencing expression",
        "     as hex bytes.",
        "",
        "md   Displays a memory-referencing expression as",
        "     decimal bytes.",
        "",
        "p    Displays a raw pointer value, showing",
        "     segment as a register name if applicable.",
    ]
    assert memory_format.positional_keywords == []

    tab_width = next(topic for topic in document.topics if topic.context_id == 80)
    assert tab_width.uhf_content == [
        "",
        "Enter the number of columns that a tab occupies.",
        "",
        "Usually, you use tabs for each level of",
        "control-structure nesting in your source code.",
        "If your source code has deeply nested control",
        "structures, you can use a small tab value (like 2",
        "or 3) so that your source doesn't disappear off",
        "the right side of module and file windows.",
    ]
    assert tab_width.next_context == 395
    assert tab_width.positional_keywords == []

    invalid_tab_width = next(topic for topic in document.topics if topic.context_id == 81)
    assert invalid_tab_width.uhf_content == [
        "",
        "You have entered an invalid tab width value.",
        "",
        "Valid values are between 1 and 32.",
    ]

    changed_memory_global = next(topic for topic in document.topics if topic.context_id == 82)
    assert changed_memory_global.uhf_content == [
        "The Changed Memory Global option allows you to",
        "set a breakpoint that occurs when an area of",
        "memory changes value.  You will be prompted for",
        "the memory area to watch.",
        "",
        "Your program will execute more slowly if you set",
        "any of these breakpoints.",
        "",
        "If you are running on an 80386, make sure you've",
        "installed the hardware device driver supplied on",
        "the distribution disk; this will speed up global",
        "breakpoints.  If you have a hardware debugger",
        "board, see if the vendor supplies a device driver",
        "that lets it work with Turbo Debugger.",
    ]

    expression_true_global = next(topic for topic in document.topics if topic.context_id == 83)
    assert expression_true_global.uhf_content == [
        "",
        "The Expression True Global option allows you to",
        "set a breakpoint that occurs when the value of an",
        "expression becomes true.  You will be prompted",
        "for the expression that must become true in order",
        "for your program to stop.",
        "",
        "Your program will execute more slowly if you set",
        "any of these breakpoints.",
    ]

    file_get_info = next(topic for topic in document.topics if topic.context_id == 84)
    assert file_get_info.uhf_content == [
        "",
        "The File Get Info command displays a window that",
        "shows you the current state of the program you",
        "are debugging.  This includes",
        "",
        "■ the program name",
        "■ where and why your program is stopped",
        "■ main memory usage",
        "■ EMS memory usage",
        "■ interrupts your program has intercepted",
        "■ the DOS version",
        "■ Hardware/software breakpoints indicator",
        "■ the current date and time",
    ]

    binary_operators = next(topic for topic in document.topics if topic.context_id == 391)
    assert binary_operators.uhf_content[10] == "         ^"
    assert binary_operators.uhf_content[14] == "^"

    assert 521 in function_keys.alias_contexts
    assert 520 in next(topic for topic in document.topics if topic.context_id == 424).alias_contexts
    assert 522 in next(topic for topic in document.topics if topic.context_id == 314).alias_contexts
    assert 527 in expression_format.alias_contexts
    assert 528 in next(topic for topic in document.topics if topic.context_id == 328).alias_contexts

    alias_toggle_breakpoint = next(topic for topic in document.topics if topic.context_id == 520)
    assert alias_toggle_breakpoint.redirect_context == 424

    alias_move_left = next(topic for topic in document.topics if topic.context_id == 521)
    assert alias_move_left.redirect_context == 380

    alias_scroll_left = next(topic for topic in document.topics if topic.context_id == 522)
    assert alias_scroll_left.redirect_context == 314

    alias_edit_expression = next(topic for topic in document.topics if topic.context_id == 523)
    assert alias_edit_expression.redirect_context == 220

    alias_erase_log = next(topic for topic in document.topics if topic.context_id == 524)
    assert alias_erase_log.redirect_context == 156

    alias_changed_memory = next(topic for topic in document.topics if topic.context_id == 525)
    assert alias_changed_memory.redirect_context == 152

    alias_symbol_table = next(topic for topic in document.topics if topic.context_id == 526)
    assert alias_symbol_table.redirect_context == 294

    alias_character_format = next(topic for topic in document.topics if topic.context_id == 527)
    assert alias_character_format.redirect_context == 392

    alias_selected_character = next(topic for topic in document.topics if topic.context_id == 528)
    assert alias_selected_character.redirect_context == 328

    alias_base_or_index = next(topic for topic in document.topics if topic.context_id == 529)
    assert alias_base_or_index.redirect_context == 306

    fencepost = next(topic for topic in document.topics if topic.context_id == 445)
    assert fencepost.uhf_content == [
        "",
        "Fencepost errors are a class of error where some",
        "operation is performed one too many or one too",
        "few times, for example,",
        "",
        "for (n = 1; n < 10; n++)",
        "",
        "which should have been",
        "",
        "for (n = 1; n <= 10; n++)",
    ]


def test_structurally_valid_but_truncated_tdh_raises_clean_value_error():
    data = bytearray(0x420)
    header_word = 0x0206
    separator_offset = 2 + header_word + header_word

    data[0:2] = header_word.to_bytes(2, "big")
    data[separator_offset:separator_offset + 2] = (1).to_bytes(2, "big")
    data[separator_offset + 2] = 0xA0
    data[separator_offset + 3:separator_offset + 7] = b"\xCC\xCC\xCC\xCC"

    payload = bytes(data)
    assert probe_tdh_binary(payload) is not None

    reader = TdhHelpReader(source_name="BROKEN.TDH", source_path=Path("BROKEN.TDH"))
    with pytest.raises(ValueError, match="Unsupported or truncated TDH payload"):
        reader.read_bytes(payload)


def test_tdh_2x_sample_exposes_late_context_range():
    data = TDH_SAMPLE_2X.read_bytes()
    probe = probe_tdh_binary(data)

    assert probe is not None
    assert probe.table_byte_size == 0x0254
    assert probe.table_word_count == 298
    assert probe.left_table_offset == 0x0002
    assert probe.right_table_offset == 0x0256
    assert probe.separator_offset == 0x04AA
    assert probe.separator_word == 1
    assert probe.encoded_payload_offset == 0x04AC
    assert probe.payload_lead_byte == 0xAE
    assert probe.payload_lead_cc_run == 9
    assert probe.payload_prefix_hex.startswith("AE CC CC CC CC CC CC CC CC CC")
    assert probe.crc32 == 0xA6E139F2

    document = TdhHelpReader(source_name=TDH_SAMPLE_2X.name, source_path=TDH_SAMPLE_2X).read_bytes(data)
    assert document.format_name == "tdh"
    assert document.metadata["format_status"] == "decoded"
    assert document.metadata["help_contents_topic_id"] == 1
    assert document.metadata["tdh_decode"]["runtime_context_count"] == 596
    assert document.metadata["tdh_decode"]["runtime_table_word_count"] == 596
    assert document.metadata["tdh_decode"]["runtime_block_offset"] == 0x04AA
    assert document.metadata["tdh_decode"]["empty_placeholder_context_count"] == 1
    assert document.metadata["tdh_decode"]["empty_placeholder_contexts"] == [537]
    assert document.metadata["tdh_probe"]["payload_lead_byte"] == "0xAE"
    assert len(document.topics) == 596
    assert document.topics[0].names[0] == "Context 0"
    assert document.topics[1].uhf_content[0].strip() == "HELP INDEX"

    page_word_counts = {
        int(key, 16): count
        for key, count in document.metadata["tdh_decode"]["page_word_counts"].items()
    }
    out_of_range_page_words = sum(
        count
        for value, count in page_word_counts.items()
        if value != 0 and not 0 < value < len(document.topics)
    )
    assert out_of_range_page_words == 0

    help_index_text = "\n".join(document.topics[1].uhf_content)
    assert "[link:topic=2]Help on Help[/link]" in help_index_text
    assert "[link:topic=401]Assembler[/link]" in help_index_text
    assert "[link:topic=396]Function Keys[/link]" in help_index_text
    assert document.contents[0].label == "Help on Help"
    assert document.contents[0].topic_id == 2

    ctrl_function_keys = next(topic for topic in document.topics if topic.context_id == 530)
    assert ctrl_function_keys.uhf_content[0] == "In some cases, a Ctrl function key duplicates"

    assert next(topic for topic in document.topics if topic.context_id == 532).names[0] == "Methods"
    assert next(topic for topic in document.topics if topic.context_id == 533).names[0] == "Object Hierarchy"
    assert next(topic for topic in document.topics if topic.context_id == 534).names[0] == "Show inherited"
    assert next(topic for topic in document.topics if topic.context_id == 538).names[0] == "Parents"
    assert next(topic for topic in document.topics if topic.context_id == 537).uhf_content == [""]
    assert next(topic for topic in document.topics if topic.context_id == 539).uhf_content[1] == "Opens an object type Inspector to show the data"

    runtime_table_word_count = _tdh_runtime_table_word_count(probe)
    raw_deltas = [
        int.from_bytes(data[2 + index * 2 : 4 + index * 2], "big")
        for index in range(runtime_table_word_count)
    ]
    runtime_starts: list[int] = []
    cumulative_offset = 0
    for raw_delta in raw_deltas:
        runtime_starts.append(probe.separator_offset + cumulative_offset)
        cumulative_offset += _signed_tdh_delta(raw_delta)
    assert data[runtime_starts[537] : runtime_starts[538]] == bytes.fromhex("00000d")

    assembler = next(topic for topic in document.topics if topic.context_id == 401)
    assert assembler.uhf_content[0] == "The syntax for assembler statements closely"
    assert assembler.uhf_content[1] == "follows that of Turbo Assembler."

    function_commands = next(topic for topic in document.topics if topic.context_id == 396)
    assert function_commands.uhf_content == [
        "",
        "There are function keys for many commonly used",
        "functions.  Many of the Alt, Ctrl, and Shifted",
        "versions of the function keys also invoke",
        "commands, as described here.",
        "",
        "The ordinary function keys invoke the following",
        "commands:",
        "",
        "[link:topic=2]F1  Help[/link]              [link:topic=388]F2  Toggle Breakpoint[/link]",
        "[link:topic=66]F3  Close Window[/link]      [link:topic=50]F4  Run to Cursor[/link]",
        "[link:topic=65]F5  Zoom Window[/link]       [link:topic=62]F6  Next Window[/link]",
        "[link:topic=46]F7  Trace Into[/link]        [link:topic=47]F8  Step Over[/link]",
        "[link:topic=48]F9  Run[/link]               [link:topic=373]F10 Command menu[/link]",
    ]

    expression = next(topic for topic in document.topics if topic.context_id == 477)
    assert expression.uhf_content[0] == "An assembler expression can have the following"
    assert expression.uhf_content[1] == "elements:"
    assert [
        (keyword.target_context, keyword.line, keyword.first_column, keyword.last_column)
        for keyword in expression.positional_keywords[:4]
    ] == [
        (481, 3, 1, 9),
        (482, 3, 14, 20),
        (483, 3, 25, 33),
        (479, 3, 38, 46),
    ]

    extra_tail_topic = next(topic for topic in document.topics if topic.context_id == 544)
    assert any(line.strip() for line in extra_tail_topic.uhf_content)

    late_tail_hotspot_count = sum(
        len(topic.positional_keywords)
        for topic in document.topics
        if 530 <= topic.context_id <= 595
    )
    assert late_tail_hotspot_count > 0

    last_topic = next(topic for topic in document.topics if topic.context_id == 595)
    assert any(line.strip() for line in last_topic.uhf_content)


def test_tdh_topics_obey_runtime_screen_line_limit():
    for sample in (TDH_SAMPLE, TDH_SAMPLE_2X):
        document = TdhHelpReader(source_name=sample.name, source_path=sample).read_bytes(sample.read_bytes())
        assert max(len(topic.raw_lines) for topic in document.topics) <= 0x0F


def test_tfh_shape_is_detected_as_profiler_help():
    data = TFH_SAMPLE.read_bytes()

    assert is_tfh_binary(data)
    assert not is_tdh_binary(data)

    probe = probe_tfh_binary(data)
    assert probe is not None
    assert probe.format_name == "tfh"
    assert probe.table_byte_size == 0x016B
    assert probe.separator_word == 0
    assert probe.encoded_payload_offset == 0x02DA
    assert probe.payload_lead_byte == 0x96
    assert probe.payload_lead_cc_run == 9
    assert probe.payload_prefix_hex.startswith("96 CC CC CC CC CC CC CC CC CC")
    assert probe.crc32 == 0xEDCB6DAB

    document = TdhHelpReader(source_name=TFH_SAMPLE.name, source_path=TFH_SAMPLE).read_bytes(data)
    assert document.format_name == "tfh"
    assert document.metadata["format"] == "tfh"
    assert document.metadata["format_status"] == "decoded"
    assert document.metadata["display_width"] == 49
    assert document.metadata["help_contents_topic_id"] == 1
    assert document.metadata["tdh_probe"]["payload_lead_byte"] == "0x96"
    assert document.metadata["tfh_partial_decode"]["runtime_block_offset"] == 0x02D8
    assert document.metadata["tfh_partial_decode"]["control_word_counts"]["0x0000"] == 308
    assert document.metadata["tfh_partial_decode"]["control_word_counts"]["0x009D"] == 22
    assert document.metadata["tfh_partial_decode"]["control_word_counts"]["0x014E"] == 5
    assert document.metadata["tfh_partial_decode"]["control_word_counts"]["<short>"] == 1
    assert document.metadata["tfh_partial_decode"]["control_word_zero_count"] == 308
    assert document.metadata["tfh_partial_decode"]["control_word_context_range_count"] == 54
    assert document.metadata["tfh_partial_decode"]["text_lead_word_counts"]["0xDFF0"] == 329
    assert document.metadata["tfh_partial_decode"]["text_lead_word_counts"]["0x4FB5"] == 14
    assert document.metadata["tfh_partial_decode"]["text_lead_word_zero_count"] == 0
    assert document.metadata["tfh_partial_decode"]["text_lead_word_context_range_count"] == 0
    assert document.metadata["tfh_partial_decode"]["trimmed_synthetic_leading_blank_topics"] == 329
    assert len(document.topics) == 363
    assert len(document.contents) == 7
    assert all(
        0 < keyword.target_context < len(document.topics)
        for topic in document.topics
        for keyword in topic.positional_keywords
    )


def test_tfh_handler_detection_does_not_depend_on_tfh_suffix():
    data = TFH_SAMPLE.read_bytes()

    handler = detect_format_handler(Path("TFHELP.BIN"), data)

    assert handler is not None
    assert handler.name == "tfh"
    assert max(len(line) for topic in document.topics for line in topic.raw_lines) == 49
    assert document.contents[0].label == "Help on Help"
    assert document.contents[0].topic_id == 2
    assert document.topics[0].names[0] == "Context 0"
    assert document.topics[1].uhf_content[0].strip() == "HELP INDEX"
    tfh_help_index_text = "\n".join(document.topics[1].uhf_content)
    assert "[link:topic=2]Help on Help[/link]" in tfh_help_index_text
    assert document.topics[1].names[0] == "HELP INDEX"
    assert document.topics[2].uhf_content[0] == "Welcome to Turbo Profiler's help facility. Use"
    assert document.topics[2].uhf_content[1] == "the following keys to move around:"
    assert document.topics[20].next_context == 19
    assert document.topics[19].next_context == 334
    assert document.topics[339].next_context == 340
    assert any(item.label == "Next" and item.topic_id == 19 for item in document.topics[20].nav_items)

    file_menu = next(topic for topic in document.topics if topic.context_id == 51)
    assert file_menu.uhf_content[0] == "The File command has a number of options that"
    assert file_menu.next_context is None
    assert "[link:topic=58]Open[/link]" in file_menu.uhf_content[8]
    assert "[link:topic=235]Get Info[/link]" in file_menu.uhf_content[8]
    assert [(keyword.target_context, keyword.line, keyword.first_column, keyword.last_column) for keyword in file_menu.positional_keywords[:2]] == [
        (58, 8, 5, 8),
        (235, 8, 20, 27),
    ]

    module_window = next(topic for topic in document.topics if topic.context_id == 103)
    assert "[link:topic=149]text pane[/link]" in module_window.uhf_content[0]
    assert "[link:topic=66]Module Window[/link]" in module_window.uhf_content[0]
    assert module_window.uhf_content[1] == "source file for the module being viewed."
    assert any(
        keyword.target_context == 66
        and keyword.line == 0
        and keyword.first_column == 21
        and keyword.last_column == 33
        for keyword in module_window.positional_keywords
    )
