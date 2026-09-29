from __future__ import annotations

from io import BytesIO
import zipfile

import pytest

from thelpviewer.downloader.extractor import (
    ExtractorTools,
    _should_probe,
    assemble_borland_split_archives,
    collect_archive_members,
    expand_single_file_payloads,
    extract_file,
)


def test_assemble_borland_split_zip_parts(tmp_path):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("TCHELP.TCH", b"complete help payload")
    zip_data = buffer.getvalue()
    split_at = len(zip_data) // 2

    part1 = tmp_path / "HELP.CA1"
    part2 = tmp_path / "HELP.CA2"
    part1.write_bytes(b"\x02\x00\x00\x00" + zip_data[:split_at])
    part2.write_bytes(b"\x01\x00\x00\x00" + zip_data[split_at:])

    assembled = assemble_borland_split_archives(tmp_path)

    assert assembled == [tmp_path / "__assembled_split_archives" / "HELP.ZIP"]
    assert assembled[0].read_bytes() == zip_data
    assert not _should_probe(part1)
    assert not _should_probe(part2)


def test_extract_file_rejects_symlinks_from_external_extractor(tmp_path, monkeypatch):
    archive = tmp_path / "unsafe.zip"
    archive.write_bytes(b"archive")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    destination = tmp_path / "extract"

    def fake_extract(_path, dest, _tools):
        (dest / "escape.txt").symlink_to(outside)
        return True, None

    monkeypatch.setattr("thelpviewer.downloader.extractor._extract_with_unar", fake_extract)
    tools = ExtractorTools(unar="unar", lsar="lsar", sevenzip=None)

    assert extract_file(archive, destination, tools) is False
    assert list(destination.iterdir()) == []
    assert outside.read_text(encoding="utf-8") == "secret"


def test_collect_archive_members_keeps_only_configured_language(tmp_path, monkeypatch):
    archive = tmp_path / "help.zip"
    archive.write_bytes(b"test")

    def fake_extract(_path, dest, _tools):
        for language in ("EN", "DE"):
            member = dest / "HELP" / language / "HHSTNDRD" / "HHSTNDRD.ZIP"
            member.parent.mkdir(parents=True)
            member.write_bytes(language.encode("ascii"))
        return True

    monkeypatch.setattr("thelpviewer.downloader.extractor.extract_file", fake_extract)
    tools = ExtractorTools(unar="unar", lsar="lsar", sevenzip=None)

    collected = collect_archive_members(
        archive,
        ("HELP/EN/HHSTNDRD/HHSTNDRD.ZIP",),
        "FreeDOS Help",
        tmp_path / "sources",
        tools,
    )

    assert len(collected) == 1
    assert collected[0].read_bytes() == b"EN"


def test_collect_archive_members_rejects_missing_files(tmp_path, monkeypatch):
    archive = tmp_path / "help.zip"
    archive.write_bytes(b"test")
    monkeypatch.setattr("thelpviewer.downloader.extractor.extract_file", lambda *_: True)
    monkeypatch.setattr("thelpviewer.downloader.extractor.extract_nested", lambda *_: None)
    tools = ExtractorTools(unar="unar", lsar="lsar", sevenzip=None)

    with pytest.raises(ValueError, match="QB45QCK.HLP"):
        collect_archive_members(
            archive,
            ("QB45QCK.HLP",),
            "QuickBASIC",
            tmp_path / "sources",
            tools,
        )


def test_expand_kwaj_help_payload(tmp_path):
    payload = b"LN\x02\x00test help"
    compressed = (
        b"KWAJ\x88\xf0\x27\xd1"
        + (0).to_bytes(2, "little")
        + (18).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + len(payload).to_bytes(4, "little")
        + payload
    )
    (tmp_path / "HELP.HL_").write_bytes(compressed)

    expand_single_file_payloads(tmp_path, ExtractorTools(None, None, None))

    assert (tmp_path / "HELP.HLP").read_bytes() == payload
