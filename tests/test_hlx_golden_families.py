import json
from pathlib import Path

import pytest

from thelpviewer.converter.readers.hlx_binary import HlxBinaryReader


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_FILE = REPO_ROOT / "tests" / "golden" / "hlx" / "families.json"


def _load_fixtures() -> list[dict[str, object]]:
    return json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture", _load_fixtures(), ids=lambda item: str(item["name"]))
def test_hlx_family_fixture(fixture: dict[str, object]) -> None:
    source_path = REPO_ROOT / "data" / "sources" / str(fixture["group"]) / str(fixture["file"])
    data = source_path.read_bytes()
    document = HlxBinaryReader(source_name=source_path.name, source_path=source_path).read_bytes(data)
    metadata = document.metadata

    assert metadata.get("hlx_kind") == fixture["hlx_kind"]
    assert metadata.get("hlx_family") == fixture["hlx_family"]
    assert len(document.topics) >= int(fixture.get("min_topics", 0))

    pointer_count = int(metadata.get("pointer_count", 0))
    if "min_pointer_count" in fixture:
        assert pointer_count >= int(fixture["min_pointer_count"])
    if "max_pointer_count" in fixture:
        assert pointer_count <= int(fixture["max_pointer_count"])

    hotspot_count = sum(len(topic.positional_keywords) for topic in document.topics)
    if "min_hotspots" in fixture:
        assert hotspot_count >= int(fixture["min_hotspots"])

    expected_prefix = [int(value) for value in fixture.get("control_byte_prefix", [])]
    actual_prefix = list(metadata.get("control_byte_dominant", []))[: len(expected_prefix)]
    assert actual_prefix == expected_prefix