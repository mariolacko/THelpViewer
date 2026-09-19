from __future__ import annotations

from io import BytesIO
import zipfile

from thelpviewer.downloader.extractor import (
    ExtractorTools,
    _should_probe,
    assemble_borland_split_archives,
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
