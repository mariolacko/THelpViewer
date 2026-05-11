from pathlib import Path

from thelpviewer.converter.exporter import detect_format_handler, load_document
from thelpviewer.downloader.collector import is_help_file_path


TAH_SAMPLE = Path("sources/Borland Turbo Assembler/TASM.TAH")


def test_tah_sample_is_detected_as_thelp():
    data = TAH_SAMPLE.read_bytes()

    handler = detect_format_handler(TAH_SAMPLE, data)

    assert handler is not None
    assert handler.name == "thelp"

    document = load_document(TAH_SAMPLE)
    assert document.format_name == "borland"
    assert document.metadata["format_version"] == 52
    assert document.metadata["text_version"] == 1
    assert len(document.topics) > 500
    assert len(document.index_entries) > 400


def test_tah_suffix_is_collected_as_help_file():
    assert is_help_file_path(Path("TASM.TAH"))