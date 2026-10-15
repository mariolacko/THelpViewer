"""Microsoft SZ media parts interrupt one stream, including inside tokens."""

from pathlib import Path
import hashlib
import shutil

import pytest

from thelpviewer.server.downloader.extractor import (
    ExtractorTools,
    MAX_EXPANDED_PAYLOAD,
    QBASIC_SZ_SIGNATURE,
    SZ_SIGNATURE,
    _decompress_sz_payload,
    collect_archive_members,
    expand_single_file_payloads,
)
from thelpviewer.server.converter.exporter import load_document


def _literal_stream(payload):
    return b"".join(bytes([(1 << len(payload[index:index + 8])) - 1])
                    + payload[index:index + 8] for index in range(0, len(payload), 8))


def _write_parts(root, payload, stream, cuts, name="REFERENCE.HL$"):
    boundaries = [0, *cuts, len(stream)]
    paths = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        number = index + 1
        directory = root / f"disk{number}"
        directory.mkdir(parents=True)
        path = directory / (name if number == 1 else name[:-1] + str(number))
        header = (QBASIC_SZ_SIGNATURE + len(payload).to_bytes(4, "little") if number == 1
                  else SZ_SIGNATURE + bytes([number]))
        path.write_bytes(header + stream[start:end])
        paths.append(path)
    return paths


@pytest.mark.parametrize("split_at", [1, 2, 4, 5])
def test_split_sz_preserves_control_bits_and_overlapping_dictionary_matches(tmp_path, split_at):
    payload = b"ABCABCABC"
    # Three literals, then a six-byte overlapping match at initial position FEEh.
    stream = b"\x07ABC\xee\xf3"
    parts = _write_parts(tmp_path, payload, stream, [split_at])
    originals = [part.read_bytes() for part in parts]

    expand_single_file_payloads(tmp_path, ExtractorTools(None, None, None))

    assert parts[0].with_suffix(".HLP").read_bytes() == payload
    assert [part.read_bytes() for part in parts] == originals
    assert not parts[1].with_suffix(".HLP").exists()


def test_split_sz_joins_three_parts_case_insensitively(tmp_path):
    payload = b"Three media parts with control bytes and literal bytes"
    parts = _write_parts(tmp_path, payload, _literal_stream(payload), [3, 22])
    parts[1].rename(parts[1].with_name(parts[1].name.lower()))

    expand_single_file_payloads(tmp_path, ExtractorTools(None, None, None))

    assert parts[0].with_suffix(".HLP").read_bytes() == payload


@pytest.mark.parametrize("kind,error", [
    ("missing", "Missing Microsoft SZ continuation part 2"),
    ("gap", "Missing Microsoft SZ continuation part 2"),
    ("wrong_number", "Invalid Microsoft SZ continuation header"),
    ("wrong_signature", "Invalid Microsoft SZ continuation header"),
    ("empty", "Invalid Microsoft SZ continuation header"),
    ("truncated", "Missing literal byte|Unexpected end of compressed stream"),
    ("duplicate", "Ambiguous Microsoft SZ parts"),
    ("other_edition", "Ambiguous Microsoft SZ parts"),
])
def test_invalid_split_sz_fails_without_creating_partial_output(tmp_path, kind, error):
    payload = b"An intact help payload across two disks"
    parts = _write_parts(tmp_path, payload, _literal_stream(payload), [3])
    first, second = parts
    if kind == "missing":
        second.unlink()
    elif kind == "gap":
        second.rename(second.with_name("REFERENCE.HL3"))
    elif kind == "wrong_number":
        second.write_bytes(SZ_SIGNATURE + b"\x03" + second.read_bytes()[8:])
    elif kind == "wrong_signature":
        second.write_bytes(b"BADPART\x02" + second.read_bytes()[8:])
    elif kind == "empty":
        second.write_bytes(SZ_SIGNATURE + b"\x02")
    elif kind == "truncated":
        second.write_bytes(second.read_bytes()[:-1])
    elif kind == "duplicate":
        duplicate = tmp_path / "another_disk/REFERENCE.HL2"
        duplicate.parent.mkdir()
        duplicate.write_bytes(second.read_bytes())
    elif kind == "other_edition":
        other = tmp_path / "other_edition/reference.hl$"
        other.parent.mkdir()
        other.write_bytes(first.read_bytes())
    original = first.read_bytes()

    with pytest.raises(ValueError, match=error):
        expand_single_file_payloads(tmp_path, ExtractorTools(None, None, None))

    assert first.read_bytes() == original
    assert not list(tmp_path.rglob("*.HLP"))


@pytest.mark.parametrize("header", [
    QBASIC_SZ_SIGNATURE,
    b"SZDD\x88\xf0\x27\x33A\x00",
])
def test_sz_rejects_short_headers_and_unbounded_output(header):
    with pytest.raises(ValueError, match="Truncated .* header"):
        _decompress_sz_payload(header)
    with pytest.raises(ValueError, match="exceeds 64 MiB"):
        _decompress_sz_payload(header + (MAX_EXPANDED_PAYLOAD + 1).to_bytes(4, "little"))


def test_szdd_rejects_unknown_compression_method():
    with pytest.raises(ValueError, match="Unsupported SZDD compression method"):
        _decompress_sz_payload(b"SZDD\x88\xf0\x27\x33B\x00\x00\x00\x00\x00")


def test_unrelated_continuation_filename_is_not_substituted(tmp_path):
    payload = b"The second part must have the same source name"
    parts = _write_parts(tmp_path, payload, _literal_stream(payload), [3])
    parts[1].rename(parts[1].with_name("OTHER.HL2"))
    with pytest.raises(ValueError, match="Missing Microsoft SZ continuation part 2"):
        expand_single_file_payloads(tmp_path, ExtractorTools(None, None, None))
    assert not list(tmp_path.rglob("*.HLP"))


def test_bad_split_payload_prevents_copying_other_members(tmp_path, monkeypatch):
    payload = b"Broken split file must not produce a partial product"
    def extract(_archive, destination, _tools):
        parts = _write_parts(destination, payload, _literal_stream(payload), [3])
        parts[1].unlink()
        (destination / "OTHER.HLP").write_bytes(b"valid companion")
        return True
    monkeypatch.setattr("thelpviewer.server.downloader.extractor.extract_file", extract)
    monkeypatch.setattr("thelpviewer.server.downloader.extractor.extract_nested", lambda *_: None)
    sources = tmp_path / "sources"
    with pytest.raises(ValueError, match="Missing Microsoft SZ continuation part 2"):
        collect_archive_members(tmp_path / "archive.zip", ("REFERENCE.HLP", "OTHER.HLP"),
                                "Reference", sources, ExtractorTools(None, None, None))
    assert not sources.exists()


@pytest.mark.parametrize("header", [
    QBASIC_SZ_SIGNATURE,
    b"SZDD\x88\xf0\x27\x33A\x00",
])
def test_standalone_sz_still_expands_without_external_tools(tmp_path, header):
    payload = b"A complete standalone help file"
    (tmp_path / "ONE.HL$").write_bytes(header + len(payload).to_bytes(4, "little") + _literal_stream(payload))

    expand_single_file_payloads(tmp_path, ExtractorTools(None, None, None))

    assert (tmp_path / "ONE.HLP").read_bytes() == payload


def test_sz_expansion_rejects_symlinked_parts(tmp_path):
    outside = tmp_path / "outside"
    outside.write_bytes(b"do not read")
    tree = tmp_path / "extract"
    tree.mkdir()
    (tree / "REFERENCE.HL2").symlink_to(outside)
    with pytest.raises(ValueError, match="unsafe symbolic link"):
        expand_single_file_payloads(tree, ExtractorTools(None, None, None))
    assert outside.read_bytes() == b"do not read"


@pytest.mark.parametrize("backend", ["default", "7zz"])
def test_real_quickc250_split_advisor_is_complete_and_reader_decodable(tmp_path, backend):
    archive = Path("var/downloads/help/ao_microsoft-quick-c-2.50_Microsoft QuickC 2.50.zip")
    binary = shutil.which("7zz") or shutil.which("7z")
    unar = shutil.which("unar")
    lsar = shutil.which("lsar")
    if not archive.is_file() or not binary or backend == "default" and not (unar and lsar):
        pytest.skip("Cached QuickC 2.50 floppy distribution and extractor required")
    tools = ExtractorTools(unar, lsar, binary) if backend == "default" else ExtractorTools(None, None, binary)
    sources = tmp_path / "sources"

    collected = collect_archive_members(archive, ("QC.HLP",), "QuickC 2.50", sources, tools)

    assert collected == [sources / "QuickC 2.50/QC.HLP"]
    assert [path for path in sources.rglob("*") if path.is_file()] == collected
    data = collected[0].read_bytes()
    assert len(data) == 504694
    assert hashlib.sha256(data).hexdigest() == "5c256559a80df21a8040f440c6e1726bb8c56fa10a02866ad0cea0306c88fd43"
    document = load_document(collected[0])
    assert len(document.topics) == 876
    assert len(document.index_entries) == 414
    assert document.metadata["source_file_aliases"] == ["qc.hlp"]
