"""New originals extend, rather than replace, the fixed 66-source references."""

import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.readers.thelp import ThelpBinaryParser, ThelpHelpReader, is_thelp_binary


def test_additional_thelp_files_match_independent_c_references():
    fixtures = Path(__file__).parent / "fixtures"
    known = set(json.loads((fixtures / "thelp-native-sources.json").read_text()).values())
    references = json.loads((fixtures / "thelp-additional-references.json").read_text())
    seen = set()
    for path in sorted(Path("var/sources").rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            if not is_thelp_binary(stream.read(4096)):
                continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest in known:
            continue  # Byte-identical copies are covered by the fixed cohort.
        assert digest in references, f"New THELP source needs independent verification: {path}"
        expected = references[digest]
        seen.add(digest)
        parser = ThelpBinaryParser(data)
        parser._parse_administrative()
        text, visible = hashlib.sha256(), hashlib.sha256()
        records = rows = 0
        while parser.pos < len(data) and data[parser.pos] != 32:
            offset = parser.pos
            kind, _size = struct.unpack_from("<BH", data, offset)
            parser._parse_record()
            if kind != 2:
                continue
            lines = parser.screens[-1]["lines"]
            text.update(json.dumps([offset, [r.hex() for r in lines]], separators=(",", ":")).encode() + b"\n")
            shown, codes = ThelpHelpReader._extract_code_lines(lines)
            visible.update(json.dumps([records, [r.hex() for r in shown], sorted(codes)],
                                      separators=(",", ":")).encode() + b"\n")
            rows += len(lines)
            records += 1
        assert (records, rows) == (expected["records"], expected["rows"]), path
        assert text.hexdigest() == expected["native_text"], path
        assert visible.hexdigest() == expected["native_visible"], path
        model = ThelpHelpReader(source_name=path.name).read_bytes(data).to_dict()
        assert hashlib.sha256(json.dumps(model, ensure_ascii=False, sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest() == expected["model"], path
    if not seen:
        pytest.skip("Additional original THELP sources unavailable")
    assert seen == set(references)
