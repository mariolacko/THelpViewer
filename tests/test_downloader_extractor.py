from __future__ import annotations

from io import BytesIO
import zipfile

import pytest

from thelpviewer.server.archives.core import ExtractorTools, UnsafeArchiveError, extract_file
from thelpviewer.server.archives.nested import _should_probe
from thelpviewer.server.archives.containers import assemble_borland_split_archives, expand_single_file_payloads
from thelpviewer.server.converter.ingest import collect_archive_members


def test_assemble_borland_split_zip_parts(tmp_path):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("TCHELP.TCH", b"complete help payload")
    zip_data = buffer.getvalue()
    split_at = len(zip_data) // 2

    part1 = tmp_path / "HELP.CA1"
    part2 = tmp_path / "HELP.CA2"
    part1.write_bytes(b"\x02\x00\x00\x00" + zip_data[:split_at])
    part2.write_bytes(b"\x01" + split_at.to_bytes(3, "little") + zip_data[split_at:])

    assembled = assemble_borland_split_archives(tmp_path)

    assert assembled == [tmp_path / "__assembled_split_archives" / "HELP.ZIP"]
    assert assembled[0].read_bytes() == zip_data
    assert not _should_probe(part1)
    assert not _should_probe(part2)


@pytest.mark.parametrize("header_size,parts_count", [(4, 2), (5, 4), (5, 11)])
@pytest.mark.parametrize("bad_offset", [False, True])
def test_split_headers_offsets_and_lettered_parts(tmp_path, header_size, parts_count, bad_offset):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("TVCHELP.TCH", bytes(range(256)) * 4)
    payload = stream.getvalue()
    offset = 0
    for index in range(parts_count):
        end = len(payload) * (index + 1) // parts_count
        number = str(index + 1) if index < 9 else chr(ord("A") + index - 9)
        bitmap = ((1 << parts_count) - 1) ^ (1 << index)
        position = offset + (1 if bad_offset and index == 1 else 0)
        part = tmp_path / f"WHELP.CA{number}"
        part.write_bytes(bitmap.to_bytes(header_size - 3, "little") + position.to_bytes(3, "little") + payload[offset:end])
        assert not _should_probe(part)
        offset = end
    assembled = assemble_borland_split_archives(tmp_path)
    if bad_offset:
        assert not assembled
    else:
        assert len(assembled) == 1 and assembled[0].read_bytes() == payload


def test_lettered_parts_do_not_hide_microsoft_cabinets(tmp_path):
    cabinet = tmp_path / "SETUP.CAB"
    cabinet.write_bytes(b"MSCF" + b"\0" * 32)
    assert _should_probe(cabinet)
    (tmp_path / "SETUP.CA1").write_bytes(b"split")
    assert _should_probe(cabinet)
    cabinet.write_bytes(b"not a split part without the first volume")
    (tmp_path / "SETUP.CA1").unlink()
    assert _should_probe(cabinet)


def test_extract_file_rejects_symlinks_from_external_extractor(tmp_path, monkeypatch):
    archive = tmp_path / "unsafe.zip"
    archive.write_bytes(b"archive")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    destination = tmp_path / "extract"

    def fake_extract(_path, dest, _tools, _limits, **_options):
        (dest / "escape.txt").symlink_to(outside)
        return True, None

    monkeypatch.setattr("thelpviewer.server.archives.core._extract_with_unar", fake_extract)
    monkeypatch.setattr("thelpviewer.server.archives.core.probe_extractable", lambda *_: None)
    tools = ExtractorTools(unar="unar", lsar="lsar", sevenzip=None)

    with pytest.raises(UnsafeArchiveError, match="symbolic link"):
        extract_file(archive, destination, tools)
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

    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", fake_extract)
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
    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", lambda *_: True)
    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_nested", lambda *_a, **_k: None)
    tools = ExtractorTools(unar="unar", lsar="lsar", sevenzip=None)

    with pytest.raises(ValueError, match="QB45QCK.HLP"):
        collect_archive_members(
            archive,
            ("QB45QCK.HLP",),
            "QuickBASIC",
            tmp_path / "sources",
            tools,
        )


@pytest.mark.parametrize("prefix", ["", "cd_iso__extracted/", "outer/cd_iso__extracted/"])
def test_collect_archive_members_matches_nested_paths_at_component_boundaries(tmp_path, monkeypatch, prefix):
    def fake_extract(_path, dest, _tools):
        for relative, content in ((f"{prefix}BC45/BIN/BCW.HLP", b"selected"),
                                  (f"{prefix}XBC45/BIN/BCW.HLP", b"not a component match"),
                                  (f"{prefix}BC45/OTHER/BCW.HLP", b"wrong directory")):
            path = dest / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return True

    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", fake_extract)
    collected = collect_archive_members(tmp_path / "cd.7z", ("bc45\\bin\\bcw.hlp",),
                                        "Borland", tmp_path / "sources", ExtractorTools(None, None, None))
    assert len(collected) == 1 and collected[0].read_bytes() == b"selected"


def test_collect_archive_members_rejects_ambiguous_nested_paths(tmp_path, monkeypatch):
    def fake_extract(_path, dest, _tools):
        for prefix in ("first_iso__extracted", "second_iso__extracted"):
            path = dest / prefix / "BC45/BIN/BCW.HLP"
            path.parent.mkdir(parents=True)
            path.write_bytes(prefix.encode("ascii"))
        return True

    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", fake_extract)
    with pytest.raises(ValueError, match="ambiguous"):
        collect_archive_members(tmp_path / "cd.7z", ("BC45/BIN/BCW.HLP",),
                                "Borland", tmp_path / "sources", ExtractorTools(None, None, None))
    assert not (tmp_path / "sources").exists()


def test_collect_archive_members_accepts_byte_identical_assembled_copies(tmp_path, monkeypatch):
    def extract(_path, dest, _tools):
        for prefix in ("disk/assembled", "assembled"):
            path = dest / prefix / "TASM.TAH"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"identical original")
    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", extract)
    paths = collect_archive_members(tmp_path / "disks.7z", ("TASM.TAH",), "Assembler",
                                   tmp_path / "sources", ExtractorTools(None, None, None))
    assert len(paths) == 1 and paths[0].read_bytes() == b"identical original"


def test_member_selection_prioritizes_needed_split_archive_and_skips_bad_siblings(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from thelpviewer.server.archives import nested
    requested = []
    def extract(source, dest, _tools, **_kwargs):
        dest.mkdir(exist_ok=True, parents=True)
        if source.name == "disks.7z":
            (dest / "TASM.ZIP").write_bytes(b"assembler archive")
            (dest / "BROKEN.ZIP").write_bytes(b"unrelated corrupt Windows help")
        else:
            requested.append(source.name)
            assert source.name == "TASM.ZIP", "Expanded unrelated broken sibling"
            (dest / "TASM.TAH").write_bytes(b"selected help")
    monkeypatch.setattr("thelpviewer.server.converter.ingest.extract_file", extract)
    monkeypatch.setattr(nested, "extract_file", extract)
    monkeypatch.setattr(nested, "probe_extractable", lambda *_args, **_kw: SimpleNamespace())
    paths = collect_archive_members(tmp_path / "disks.7z", ("TASM.TAH",), "Assembler",
                                   tmp_path / "sources", ExtractorTools(None, None, None))
    assert requested == ["TASM.ZIP"] and len(paths) == 1


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
