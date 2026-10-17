"""Display-text HELP grammars and source containers, not binary fallbacks."""

import gzip
import json
from pathlib import Path

import pytest

from thelpviewer.help_database import lookup_help_database_entry
from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.readers.dos_text import (
    DosTextHelpReader, MicroCalcReader, PrologHelpReader,
)
from thelpviewer.server.converter.readers.source_containers import unpack_dos_backup
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


def _backup(payload, pathname=b"\\PROLOG\\REFERENCE.HLP", *, flag=0xFF, disk=1):
    header = bytearray(128)
    header[0:2] = bytes((flag, disk))
    header[5:5 + len(pathname)] = pathname
    header[0x53] = len(pathname) + 1
    return bytes(header) + payload


def test_microcalc_pages_preserve_runtime_color_state_not_tab_or_nested_styles():
    data = (b"Title\r\n\x02Bright\r\nStill bright\x09Reverse\x02Normal\x09Normal again\r\n"
            b".PA page separator\r\nNext page\r\n\x1a")
    document = MicroCalcReader(source_name="MC.HLP").read_bytes(data)
    first, second = document.topics
    assert first.raw_lines == [b"     Title", b"     Bright",
                               b"     Still brightReverseNormalNormal again"]
    assert first.uhf_content == [
        "[color:7:0]     Title[/color]",
        "[color:7:0]     [/color][color:14:0]Bright[/color]",
        "[color:14:0]     Still bright[/color][color:0:7]Reverse[/color]"
        "[color:7:0]Normal[/color][color:7:0]Normal again[/color]",
    ]
    assert second.uhf_content == ["[color:7:0]     Next page[/color]"]
    assert second.raw_lines == [b"     Next page"]
    assert first.next_context == 2 and second.prev_context == 1
    assert first.is_help_contents and not second.is_help_contents
    assert [node.topic_id for node in document.contents] == [1, 2]
    payload = HelpJsonRenderer(document).render_document()
    assert payload["metadata"]["ui"]["window"] == "cga:0"
    assert payload["topics"]["1"]["nav"]["Next"] == {"topic_id": 2}
    assert payload["topics"]["2"]["nav"]["Prev"] == {"topic_id": 1}


def test_microcalc_exact_page_command_cp437_and_literal_markup():
    data = "Übersicht [link:topic=99]\r\n.pa is ordinary text\r\n .PA too\r\n.PA\r\nEnde\r\n".encode("cp437")
    document = MicroCalcReader().read_bytes(data)
    assert len(document.topics) == 2
    assert document.topics[0].names == ["Übersicht [link:topic=99]"]
    assert "[[link:topic=99]" in document.topics[0].uhf_content[0]
    assert document.topics[0].raw_lines[1:] == [b"     .pa is ordinary text", b"      .PA too"]


def test_dos_text_preserves_lines_oem_boxes_and_tab_stops_without_links():
    data = "┌──┐\r\nÜbersicht\r\n\r\nA\tB [link:topic=99]\r\n└──┘\r\n".encode("cp437") + b"\x1aignored"
    document = DosTextHelpReader(source_name="PROLOG.HLP").read_bytes(data)
    assert len(document.topics) == 1
    topic = document.topics[0]
    assert topic.names == ["Übersicht"]
    assert topic.raw_lines[2] == b""
    assert topic.uhf_content == ["┌──┐", "Übersicht", "", "A       B [[link:topic=99]", "└──┘"]
    assert not topic.positional_keywords and not topic.sequential_keywords


@pytest.mark.parametrize("data", [
    b"Title\r\n\x00binary", b"Title\r\n\x01binary", b"Just one line",
    b"\r\n\r\n", b"h(\"unterminated\r\n", b".PA\r\nMicroCalc\r\n",
])
def test_plain_text_does_not_accept_binary_specialized_or_empty_files(data):
    with pytest.raises(ValueError):
        DosTextHelpReader().read_bytes(data)


def test_prolog_clause_records_are_display_pages_not_executable_source():
    data = rb'h("First\n\tText [b]\nQuote: \" and slash: \\")' + b'\r\n' + rb'h("Second\r\nEnd").' + b'\x1a'
    document = PrologHelpReader(source_name="XHELP.HLP").read_bytes(data)
    assert [topic.raw_lines for topic in document.topics] == [
        [b"First", b"        Text [b]", b'Quote: " and slash: \\'], [b"Second", b"End"],
    ]
    assert document.topics[0].uhf_content[1] == "        Text [[b]"
    assert [topic.context_id for topic in document.topics] == [1, 2]


@pytest.mark.parametrize("data", [
    b"", b'h("unterminated)', b'h("unsupported\\q")', b'h("ok")\nrun("code")',
    b'h("ok") garbage', b'h("ok")..', b'h("binary\x00")', b'h("text")\n42',
])
def test_prolog_rejects_entire_malformed_or_executable_sequence(data):
    with pytest.raises(ValueError):
        PrologHelpReader().read_bytes(data)
    if data.startswith(b"h("):
        assert detect_format_handler("XHELP.HLP", data) is None


@pytest.mark.parametrize("name,data,format_name", [
    ("MC.HLP", b"Title\r\n.PA\r\nNext\r\n", "microcalc-text"),
    ("XHELP.HLP", b'h("First\\n")\r\nh("Second")', "prolog-help"),
    ("PROLOG.HLP", b"Prolog help\r\nText\r\n", "dos-text"),
])
def test_manifest_dispatches_text_grammars_only_for_hlp(name, data, format_name):
    assert detect_format_handler(name, data).name == format_name
    assert detect_format_handler(Path(name).with_suffix(".bin"), data) is None


def test_backup_is_transport_for_any_inner_reader_and_never_writes_embedded_path(tmp_path):
    payload = b"MicroCalc\r\n.PA\r\nSecond page\r\n"
    wrapped = _backup(payload, b"\\SOMEWHERE\\MC.HLP")
    assert unpack_dos_backup(wrapped) == (payload, {
        "format": "dos-backup", "pathname": "\\SOMEWHERE\\MC.HLP", "disk_number": 1,
    })
    source = tmp_path / "MC.HLP"
    source.write_bytes(wrapped)
    assert detect_format_handler(source).name == "microcalc-text"
    document = load_document(source)
    assert len(document.topics) == 2
    metadata = HelpJsonRenderer(document).render_document()["metadata"]
    assert metadata["source_container"]["pathname"] == "\\SOMEWHERE\\MC.HLP"
    assert metadata["source"]["filename"] == "MC.HLP"
    assert source.read_bytes() == wrapped
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("flag,disk", [(0, 1), (0xFF, 2), (0xFF, 0)])
def test_incomplete_or_later_volume_backup_cannot_be_imported(flag, disk):
    wrapped = _backup(b"Title\r\nHelp\r\n", flag=flag, disk=disk)
    with pytest.raises(ValueError, match="Incomplete/multi-volume"):
        unpack_dos_backup(wrapped)
    assert detect_format_handler("PROLOG.HLP", wrapped) is None


@pytest.mark.parametrize("offset,value", [(0x53, 0), (0x53, 79), (4, 1), (0x54, 1), (0x52, 1), (24, 1)])
def test_invalid_backup_headers_are_not_stripped(offset, value):
    data = bytearray(_backup(b"Title\r\nHelp\r\n"))
    data[offset] = value
    original = bytes(data)
    assert unpack_dos_backup(original) == (original, {})


@pytest.mark.parametrize("path", [b"relative.HLP", b"\\..\\FILE.HLP", b"\\DIR\\..\\FILE.HLP",
                                      b"\\DIR\\FILE?.HLP", b"\\DIR\\\\FILE.HLP", b"\\DIR\x00FILE.HLP"])
def test_invalid_backup_pathnames_are_not_used(path):
    original = _backup(b"Title\r\nHelp\r\n", path)
    assert unpack_dos_backup(original) == (original, {})


def test_empty_backup_payload_fails():
    with pytest.raises(ValueError, match="no file payload"):
        unpack_dos_backup(_backup(b""))


def test_original_turbo_basic_and_prolog_corpus_converts_and_retains_crc_metadata(tmp_path):
    root = Path("var/sources")
    selected = [path for path in root.rglob("*") if path.suffix.upper() in {".HLP", ".TBH"}
                and path.parts[2].startswith(("Borland Turbo Basic", "Borland Turbo Prolog"))]
    if not selected:
        pytest.skip("Original Turbo Basic/Prolog help files are not available")
    assert len(selected) == 29
    formats = {}
    for path in selected:
        entry = lookup_help_database_entry(path)
        assert entry is not None and entry.product_key in {"tbasic", "tprolog"}
        document = load_document(path)
        formats[document.format_name] = formats.get(document.format_name, 0) + 1
        expected = {"microcalc-text": 7, "prolog-help": 2, "dos-text": 1, "turbo-basic": 108}[document.format_name]
        assert len(document.topics) == expected
        assert all("�" not in line for topic in document.topics for line in topic.uhf_content)
    assert formats == {"microcalc-text": 3, "prolog-help": 1, "dos-text": 22, "turbo-basic": 3}

    results = export_bundle_tree(root, tmp_path / "helps", source_paths=selected, layout="helps")
    assert results and all(not result.error for result in results)
    catalog = json.loads((tmp_path / "helps" / "catalog.json").read_text())
    assert {item["product"] for item in catalog} == {"tbasic", "tprolog"}
    assert {item["product_name"] for item in catalog} == {"Borland Turbo Basic", "Borland Turbo Prolog"}
    for item in catalog:
        bundle = json.loads(gzip.decompress((tmp_path / "helps" / item["file"]).read_bytes()))
        assert item["topics"] == len(bundle["topics"])
        assert not item["file"].startswith("Candidates/")

    # Exercise the same selective/staged builder used by the server, retaining
    # an installed unrelated product rather than replacing the whole library.
    prior_source = tmp_path / "prior-source" / "HelpPC 2.10" / "C.TXT"
    prior_source.parent.mkdir(parents=True)
    prior_source.write_bytes(b"@C language\r\n:Reference\r\n Existing help\r\n")
    live = tmp_path / "published"
    prior = export_bundle_tree(tmp_path / "prior-source", live, layout="helps")[0]
    before = prior.json_path.read_bytes()
    progress = []
    result = build_help_groups(["borland"], root, live, product_keys=["tbasic", "tprolog"],
                               keep_products=["helppc", "tbasic", "tprolog"], on_progress=progress.append)
    assert Path(result["backup"]).is_dir()
    assert prior.json_path.read_bytes() == before
    published = json.loads((live / "catalog.json").read_text())
    assert result["bundles"] == len(published) == len(catalog) + 1
    assert {item["product"] for item in published} == {"helppc", "tbasic", "tprolog"}
    assert progress and any(item.get("total", 0) > 0 for item in progress)
