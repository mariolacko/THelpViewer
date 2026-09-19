from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
from pathlib import Path
import sys
import zipfile


def _load_zip_implode_module():
    tool_path = Path(__file__).resolve().parents[1] / "tools" / "zip_implode.py"
    spec = spec_from_file_location("zip_implode", tool_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_list_members_reports_names_and_offsets(tmp_path):
    module = _load_zip_implode_module()

    archive_path = tmp_path / "sample.zip"
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("ALPHA.TXT", b"alpha")
        archive.writestr("nested/BETA.BIN", b"beta-data")
    archive_path.write_bytes(buffer.getvalue())

    members = module.list_members(archive_path)

    assert [member.member_name for member in members] == ["ALPHA.TXT", "nested/BETA.BIN"]
    assert all(member.local_header_offset < member.compressed_offset for member in members)
    assert all(member.compressed_size == member.uncompressed_size for member in members)

    beta = module.locate_member(archive_path, "nested/BETA.BIN")
    assert beta.member_name == "nested/BETA.BIN"
    assert beta.uncompressed_size == len(b"beta-data")
    assert beta.compression_method == zipfile.ZIP_STORED


def test_main_lists_members(tmp_path, capsys):
    module = _load_zip_implode_module()

    archive_path = tmp_path / "sample.zip"
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("ALPHA.TXT", b"alpha")
        archive.writestr("nested/BETA.BIN", b"beta-data")
    archive_path.write_bytes(buffer.getvalue())

    assert module.main([str(archive_path), "--list"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("ALPHA.TXT\tmethod=0\tflags=0x0000\tlocal=0x")
    assert lines[1].startswith("nested/BETA.BIN\tmethod=0\tflags=0x0000\tlocal=0x")
