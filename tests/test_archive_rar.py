"""Exercise actual solid-RAR decoding, not just archive-header listing.

The fixture is libarchive's test_read_format_rar5_multiple_files_solid.rar.uu:
https://github.com/libarchive/libarchive/blob/master/libarchive/test/test_read_format_rar5_multiple_files_solid.rar.uu
It contains four deterministic 4096-byte test buffers, no application files.
"""

import binascii
from pathlib import Path

import pytest

from thelpviewer.server.archives.core import extract_file, require_extractor_tools


@pytest.mark.parametrize("sfx", [False, True])
def test_shared_extractor_decodes_compressed_solid_rar_with_arbitrary_extension(tmp_path, sfx):
    tools = require_extractor_tools(dry_run=True)
    if not tools.available:
        pytest.skip("unar/lsar or 7-Zip required; Debian also needs 7zip-rar")
    lines = Path("tests/fixtures/archives/rar5-solid.rar.uu").read_text().splitlines()
    payload = b"".join(binascii.a2b_uu(line) for line in lines[1:-1])
    source = tmp_path / "software.archive"
    source.write_bytes((b"MZ" + b"\0" * 126 if sfx else b"") + payload)
    destination = tmp_path / "expanded"
    result = extract_file(source, destination, tools)
    assert result.total_bytes == 4 * 4096
    assert {path.relative_to(destination).as_posix() for path in result.files} == {
        "test1.bin", "test2.bin", "test3.bin", "test4.bin"}
    assert all(path.stat().st_size == 4096 for path in result.files)
    assert len({path.read_bytes() for path in result.files}) == 4
