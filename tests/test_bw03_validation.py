"""Original BW03 output stays intact while damaged staged builds cannot publish."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.bw03 import BW03HelpReader


SOURCES = [
    ("Microsoft MASM and CodeView 5.0/CV.HLP", 20,
     "f99201f784bda0550b0954d0e8fcbf290c1f0618246db7d9a8852cfceba8dee5"),
    ("Microsoft MASM and CodeView 5.1/CV.HLP", 24,
     "6020c37874c360f428d2581417923721f98340b1fcc3387ecf687b1739cbb2c2"),
    ("Microsoft MASM and CodeView 5.1/CVP.HLP", 24,
     "c1421f9379c846f508702c6ee303ffe345591ffd7acb902d6ddc3aebf47b703d"),
]


def source(relative):
    path = Path("var/sources") / relative
    if not path.is_file():
        pytest.skip("Original BW03 source is not installed")
    return path


@pytest.mark.parametrize("relative,count,digest", SOURCES)
def test_every_original_preserves_its_complete_model_and_native_circular_links(relative, count, digest):
    document = load_document(source(relative))
    assert len(document.topics) == count + 1
    # The newly exported native short-help block is the only model addition.
    snapshot = asdict(document)
    # These historical baselines predate the shared alias-cursor field.
    # BW03 has no such aliases: assert that, then compare all original fields.
    for topic in snapshot["topics"]:
        assert topic.pop("alias_lines") == {}
    # Shared native-screen resources were added later too. BW03 still has
    # none, so keep the original independent hashes rather than regenerating
    # expectations from changed text/navigation.
    assert snapshot.pop("fonts") == {}
    assert snapshot.pop("text_screens") == {}
    snapshot["topics"] = snapshot["topics"][:count]
    snapshot["contents"] = snapshot["contents"][:-1]
    snapshot["index_entries"] = snapshot["index_entries"][:-1]
    assert hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=repr).encode()).hexdigest() == digest
    assert [topic.next_context for topic in document.topics[:count]] == list(range(1, count)) + [0]
    assert [topic.prev_context for topic in document.topics[:count]] == [count - 1] + list(range(count - 1))
    ids = {topic.context_id for topic in document.topics}
    assert all(item.topic_id in ids for topic in document.topics for item in topic.nav_items)
    summary = document.topics[count]
    assert summary.names == ["Command summary"]
    assert any(b"Execute Code" in line or b"Execute Code" in line.replace(b"=", b" ") for line in summary.raw_lines)
    assert any(b"Examine Data" in line for line in summary.raw_lines)
    assert document.contents[-1].topic_id == count


@pytest.mark.parametrize("relative,_count,_digest", SOURCES)
@pytest.mark.parametrize("cut", [1, 10, 50, 100])
def test_truncating_indexed_text_is_not_hidden_by_the_unindexed_tail(relative, _count, _digest, cut):
    path = source(relative)
    data = path.read_bytes()
    count, menus = struct.unpack_from("<HH", data, 4)
    table = 8 + 22 * menus + 48
    end = max(offset + size for offset, size in (
        struct.unpack_from("<II", data, table + i * 12 + 4) for i in range(count)))
    assert end < len(data)  # Known unindexed summary is not a mandatory screen.
    reader = BW03HelpReader(source_name=path.name, source_path=path)
    assert reader.read_bytes(data[:end]).topics == reader.read_bytes(data).topics[:count]
    with pytest.raises(ValueError, match="payload lies outside"):
        reader.read_bytes(data[:end-cut])


@pytest.mark.parametrize("relative,_count,_digest", SOURCES)
def test_incomplete_rle_in_last_original_screen_is_not_read_from_summary(relative, _count, _digest):
    data = bytearray(source(relative).read_bytes())
    count, menus = struct.unpack_from("<HH", data, 4)
    table = 8 + 22 * menus + 48
    offset, length = struct.unpack_from("<II", data, table + (count - 1) * 12 + 4)
    data[offset+length-1] = 255
    with pytest.raises(ValueError, match=f"BW03 screen {count-1}: Truncated BW03 repeat control"):
        BW03HelpReader().read_bytes(bytes(data))


def test_invalid_real_screen_preserves_published_catalog_and_retry_works(tmp_path):
    relative = SOURCES[0][0]
    original = source(relative).read_bytes()
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    copy = sources / relative
    copy.parent.mkdir(parents=True)
    copy.write_bytes(original)
    build_help_groups(["microsoft"], sources, helps)
    published = {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    damaged = bytearray(original)
    count, menus = struct.unpack_from("<HH", damaged, 4)
    table = 8 + 22 * menus + 48
    struct.pack_into("<H", damaged, table + (count - 1) * 12, count)
    copy.write_bytes(damaged)
    with pytest.raises(ValueError, match="HELP conversion failed"):
        build_help_groups(["microsoft"], sources, helps)
    assert published == {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    assert not list(tmp_path.glob(".helps-build-*"))
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert copy.read_bytes() == damaged
    copy.write_bytes(original)
    result = build_help_groups(["microsoft"], sources, helps)
    assert result["backup"] and result["bundles"] == 1
    backup = Path(result["backup"])
    assert published == {p.relative_to(backup): p.read_bytes() for p in backup.rglob("*") if p.is_file()}
