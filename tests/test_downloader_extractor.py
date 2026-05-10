from __future__ import annotations

from io import BytesIO
import zipfile

from thelpviewer.downloader.extractor import (
    _should_probe,
    assemble_borland_split_archives,
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
