"""The fixed source cohort used by the independent THELP reference digests."""

import hashlib
import json
from pathlib import Path

import pytest


def original_thelp_corpus():
    root = Path("var/sources")
    expected = json.loads((Path(__file__).parent / "fixtures/thelp-native-sources.json").read_text())
    missing = [name for name in expected if not (root / name).is_file()]
    if missing:
        pytest.skip("Original THELP reference cohort unavailable: " + ", ".join(missing))
    for name, digest in sorted(expected.items(), key=lambda entry: Path(entry[0])):
        path = root / name
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, f"Reference input changed: {path}"
        yield path, data
