from pathlib import Path

from thelpviewer.converter.exporter import detect_format_handler
from thelpviewer.converter.readers.tdh import (
    TdhHelpReader,
    is_tdh_binary,
    is_tfh_binary,
    probe_tdh_binary,
    probe_tfh_binary,
)
from thelpviewer.converter.readers.thelp import is_thelp_binary


TDH_SAMPLE = Path("sources/Borland Turbo Debugger 1.0/TDHELP.TDH")
TFH_SAMPLE = Path("sources/Borland Turbo Profiler/TFHELP.TFH")


def test_tdh_sample_is_detected_separately_from_thelp():
    data = TDH_SAMPLE.read_bytes()

    assert is_tdh_binary(data)
    assert not is_thelp_binary(data)

    handler = detect_format_handler(TDH_SAMPLE, data)
    assert handler is not None
    assert handler.name == "tdh"


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
    assert document.metadata["format_status"] == "undecoded"
    assert document.metadata["tdh_probe"]["payload_lead_byte"] == "0xA0"
    assert document.topics


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
    assert document.metadata["format_status"] == "undecoded"
    assert document.metadata["tdh_probe"]["payload_lead_byte"] == "0x96"
