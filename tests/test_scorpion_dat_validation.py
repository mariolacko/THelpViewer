"""Declared Allegro chunk lengths cannot publish partial Scorpion articles."""

import gzip
import json
from pathlib import Path

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.converter.exporter import detect_format_handler, load_document
from thelpviewer.server.converter.readers.allegro_dat import (
    AllegroDatafileError, allegro_lzss_decompress, parse_allegro_datafile,
)
from thelpviewer.server.converter.readers.scorpion_dat_parser import (
    SCORPION_ALLEGRO_PACK_MAGIC, parse_scorpion_dat_records,
)
from thelpviewer.server.converter.readers.scorpion_dat_reader import (
    ScorpionDatReader, is_scorpion_dat_help_binary,
)
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from test_allegro_dat_reader import _dat_body, _literal_lzss, _object, _old_crypt_literal_lzss, _property


def _dat(*objects):
    return SCORPION_ALLEGRO_PACK_MAGIC + _dat_body(*objects)


def _article(text=b"[R010]\r\nArticle text", *, size=None):
    packed = _old_crypt_literal_lzss(text, b"akrab")
    return _object(b"DATA", packed, _property(b"NAME", b"article"),
                   unpacked_size=-(len(text) if size is None else size))


@pytest.mark.parametrize("packed,size", [
    (b"", 1), (b"\xff", 1), (b"\x01A", 2),
    (b"\x00\xee", 6), (b"\x07ABC\xee", 9),
    (_literal_lzss(b"text"), 5),
])
def test_lzss_short_streams_raise_instead_of_returning_partial_data(packed, size):
    with pytest.raises(AllegroDatafileError, match="decoded to .*expected"):
        allegro_lzss_decompress(packed, size)
    with pytest.raises(AllegroDatafileError, match="decoded to .*expected"):
        parse_allegro_datafile(b"slh." + _dat_body(_object(b"DATA", packed, unpacked_size=-size)))


def test_lzss_declared_size_is_nonnegative_and_stops_at_the_native_logical_end():
    with pytest.raises(AllegroDatafileError, match="nonnegative"):
        allegro_lzss_decompress(b"", -1)
    assert allegro_lzss_decompress(b"", 0) == b""
    assert allegro_lzss_decompress(b"\x07ABC\xee\xf3", 5) == b"ABCAB"
    # Unread packed bytes are skipped at chunk close, not another object.
    payload = b"slh." + _dat_body(
        _object(b"DATA", _literal_lzss(b"ABC") + b"padding", unpacked_size=-3),
        _object(b"DATA", b"next"),
    )
    assert [o.payload for o in parse_allegro_datafile(payload).objects] == [b"ABC", b"next"]


@pytest.mark.parametrize("size", [0, 1, 10])
def test_uncompressed_chunk_sizes_must_agree(size):
    with pytest.raises(AllegroDatafileError, match="mismatched"):
        parse_allegro_datafile(b"slh." + _dat_body(_object(b"DATA", b"text", unpacked_size=size)))


def test_empty_uncompressed_object_and_empty_container_are_valid():
    assert parse_allegro_datafile(b"slh." + _dat_body()).objects == ()
    assert parse_allegro_datafile(b"slh." + _dat_body(_object(b"DATA", b""))).objects[0].payload == b""
    assert not is_scorpion_dat_help_binary(_dat(_object(b"DATA", b"")))


@pytest.mark.parametrize("payload", [
    _dat(_article(size=100)),
    _dat(_object(b"DATA", b"", unpacked_size=-20)),
    _dat(_object(b"DATA", b"\x61\xee", unpacked_size=-6)),
    _dat(_object(b"DATA", b"[R010]\r\nText", unpacked_size=0)),
    _dat(_article(), _object(b"DATA", b"", _property(b"NAME", b"font1"), unpacked_size=-4096)),
    _dat(_object(b"FILE", (1).to_bytes(4, "big") + _article(size=100))),
])
def test_recognized_bad_dat_is_an_error_not_an_unsupported_or_resource_file(payload):
    path = Path("Scorpions Cheater 23/PROGRAM.DAT")
    for read in (
        parse_scorpion_dat_records,
        is_scorpion_dat_help_binary,
        lambda data: detect_format_handler(path, data),
        ScorpionDatReader(source_path=path).read_bytes,
    ):
        with pytest.raises(AllegroDatafileError):
            read(payload)


@pytest.mark.parametrize("cut", range(8, len(_dat(_article()))))
def test_truncated_recognized_container_never_becomes_a_partial_help(cut):
    with pytest.raises(AllegroDatafileError):
        is_scorpion_dat_help_binary(_dat(_article())[:cut])


def test_password_cursor_restarts_per_object_and_valid_resources_stay_non_articles():
    payload = _dat(_article(), _object(
        b"DATA", _old_crypt_literal_lzss(b"font bytes", b"akrab"),
        _property(b"NAME", b"font1"), unpacked_size=-10,
    ), _article(b"[R011]\r\nSecond article"))
    records = parse_scorpion_dat_records(payload)
    assert [r.payload for r in records] == [b"[R010]\r\nArticle text", b"font bytes", b"[R011]\r\nSecond article"]
    document = ScorpionDatReader(source_path=Path("Scorpions Cheater 23/PROGRAM.DAT")).read_bytes(payload)
    assert len(document.topics) == 2
    assert document.metadata["scorpion_resource_record_names"] == ["font1"]


def test_modern_corpus_has_complete_chunks_and_publishes_unchanged_articles(tmp_path):
    root = Path("var/sources/Scorpions Cheater DOS")
    if not root.is_dir():
        pytest.skip("Original Scorpion databases are not installed")
    sources = [path for path in sorted(root.rglob("*.DAT"))
               if path.read_bytes().startswith(SCORPION_ALLEGRO_PACK_MAGIC + b"ALL.")]
    supported = [path for path in sources if detect_format_handler(path) is not None]
    helps = tmp_path / "helps"
    results = export_bundle_tree(Path("var/sources"), helps, source_paths=supported, layout="helps")
    assert len(results) == len(supported) and all(not result.error for result in results)
    catalog = json.loads((helps / "catalog.json").read_text())
    files = records = articles = 0
    for path in sources:
        data = path.read_bytes()
        if not data.startswith(SCORPION_ALLEGRO_PACK_MAGIC + b"ALL."):
            continue
        parsed = parse_scorpion_dat_records(data)
        assert all(r.decoded_size == abs(r.uncompressed_size) for r in parsed)
        files += 1
        records += len(parsed)
        handler = detect_format_handler(path, data)
        if handler is None:
            continue  # TEXTY contains a separate SC 2000 text/catalog grammar.
        document = load_document(path)
        version = document.metadata["scorpion_version"]
        entry = next(e for e in catalog if e.get("product") == "scorpion" and e.get("version") == version
                     and path.name in e["source_files"])
        published = json.loads(gzip.decompress((helps / entry["file"]).read_bytes()))
        payload = HelpJsonRenderer(document, "utf-8").render_document()
        assert payload["topics"] == published["topics"], path
        assert payload["contents"] == published["contents"], path
        assert payload["index"] == published["index"], path
        articles += len(document.topics)
    assert files == 26 and records == 579 and articles > 1000


@pytest.mark.parametrize("damage", ["short-article", "bad-resource", "truncated-header"])
def test_failed_build_preserves_every_published_file_and_allows_retry(tmp_path, damage):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "Scorpions Cheater DOS/Scorpions Cheater 23/PROGRAM.DAT"
    source.parent.mkdir(parents=True)
    original = _dat(_article())
    source.write_bytes(original)
    # A second valid file prevents a skipped corrupt file from passing as a
    # successful partial product build and removing its old publication.
    source.with_name("CHEATY.DAT").write_bytes(_dat(_article(b"[3001]\r\nCheat")))
    build_help_groups(["scorpion"], sources, helps, product_keys=["scorpion"], keep_products=["scorpion"])
    def snapshot():
        return {p.relative_to(helps): p.read_bytes() for p in helps.rglob("*") if p.is_file()}
    previous = snapshot()
    damaged = {
        "short-article": _dat(_article(size=100)),
        "bad-resource": _dat(_article(), _object(b"DATA", b"", _property(b"NAME", b"font1"), unpacked_size=-4096)),
        "truncated-header": original[:8],
    }[damage]
    source.write_bytes(damaged)
    with pytest.raises(AllegroDatafileError):
        build_help_groups(["scorpion"], sources, helps, product_keys=["scorpion"], keep_products=["scorpion"])
    assert snapshot() == previous
    assert not list(tmp_path.glob(".helps-build-*"))
    source.write_bytes(original)
    result = build_help_groups(["scorpion"], sources, helps, product_keys=["scorpion"], keep_products=["scorpion"])
    assert result["bundles"] == 2 and Path(result["backup"]).is_dir()
    assert source.read_bytes() == original
