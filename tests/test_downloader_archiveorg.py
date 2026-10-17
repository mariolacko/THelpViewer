"""Archive.org discovery of pinned DOS reference HELP files."""

import pytest
from dataclasses import replace
from urllib.error import HTTPError

from thelpviewer.help_database import SourceQuery
from thelpviewer.server.downloader import archiveorg
from thelpviewer.server.downloader.archiveorg import process_item, run
from thelpviewer.server.archives.core import ExtractorTools
from thelpviewer.server.downloader.catalog import product_spec


def test_reference_archive_search_uses_exact_members_and_product_root(tmp_path, monkeypatch):
    product = product_spec("msdos622")
    query = product.sources["archiveorg"]
    monkeypatch.setattr(archiveorg, "get_item_files", lambda _: [{"name": "en_msdos622.zip", "size": "100"}])
    plans = []
    def process(source, **_options):
        plans.append(source)
        return [tmp_path / "sources" / source.collection / "HELP.HLP"]
    result = process_item({"identifier": "dos622", "title": "MS-DOS 6.22 (English)"},
        product, query, tmp_path / "downloads", process, False, [])
    assert len(plans) == 1 and plans[0].members == ("HELP.HLP",)
    assert plans[0].collection == "Microsoft MS-DOS 6.22"
    assert result == [tmp_path / "sources/Microsoft MS-DOS 6.22/HELP.HLP"]


def test_provider_does_not_write_or_mark_originals_installed(tmp_path, monkeypatch):
    product = replace(product_spec("msdos622"), sources={"archiveorg": SourceQuery(
        "DOS", direct_urls=("https://archive.org/details/dos622",))})
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: [product])
    monkeypatch.setattr(archiveorg, "get_item", lambda _: {"identifier": "dos622", "title": "MS-DOS 6.22"})
    monkeypatch.setattr(archiveorg, "get_item_files", lambda _: [{"name": "dos.zip", "size": "100"}])
    plans = []
    assert run(["msdos622"], tmp_path / "downloads", False,
        lambda source, **_options: plans.append(source) or []) == []
    assert len(plans) == 1 and not list(tmp_path.iterdir())


def test_existing_product_version_is_not_appended_to_download_directory(tmp_path, monkeypatch):
    product = product_spec("qbx")
    monkeypatch.setattr(archiveorg, "get_item_files", lambda _: [{"name": "qb71.zip", "size": "100"}])
    plans = []
    process_item({"identifier": "qb71zip", "title": "QuickBASIC Extended 7.1"},
        product, product.sources["archiveorg"], tmp_path / "downloads",
        lambda source, **_options: plans.append(source) or [], False, [])
    assert [source.collection for source in plans] == ["Microsoft QuickBASIC Extended 7.1"]


def test_pinned_item_uses_metadata_not_search(monkeypatch):
    calls = []
    def fetch(url):
        calls.append(url)
        return {"metadata": {"identifier": "borland-package", "title": "Borland tools"}}
    monkeypatch.setattr(archiveorg, "fetch_json", fetch)
    assert archiveorg.get_item("borland-package")["title"] == "Borland tools"
    assert calls == ["https://archive.org/metadata/borland-package"]


def test_nested_metadata_archives_are_safe_and_scanned_manuals_are_not_sources():
    files = [{"name": name, "size": "100"} for name in (
        "BP700/All.zip", "BP701/All.zip", "manual_jp2.zip", "KryoFlux_dumps.ZIP",
        "../escape.zip", "/absolute.zip", "dir/../escape.zip", "dir\\escape.zip")]
    assert archiveorg.pick_download_files(files, "item") == [
        ("BP700/All.zip", "https://archive.org/download/item/BP700/All.zip"),
        ("BP701/All.zip", "https://archive.org/download/item/BP701/All.zip")]


def test_pinned_success_does_not_depend_on_advanced_search_and_keeps_member_queries(tmp_path, monkeypatch):
    base = product_spec("tasm")
    url = "https://archive.org/details/pinned"
    queries = [SourceQuery("TASM", query="broad discovery", direct_urls=(url,), archive_members=(name,))
               for name in ("TASM.TAH", "TFHELP.TFH")]
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: [
        replace(base, sources={"archiveorg": query}) for query in queries])
    monkeypatch.setattr(archiveorg, "get_item", lambda _: {"identifier": "pinned", "title": "Borland tools"})
    monkeypatch.setattr(archiveorg, "search_items", lambda *_: pytest.fail("Working pin used advanced search"))
    processed = []
    def process(**kwargs):
        members = kwargs["source_query"].archive_members
        processed.append(members)
        return [tmp_path / members[0]]
    monkeypatch.setattr(archiveorg, "process_item", process)
    result = run(["tasm"], tmp_path / "downloads", False, lambda *_a, **_k: [])
    assert processed == [("TASM.TAH",), ("TFHELP.TFH",)]
    assert result == [tmp_path / "TASM.TAH", tmp_path / "TFHELP.TFH"]


def test_unavailable_pin_does_not_drop_later_pins(tmp_path, monkeypatch):
    query = SourceQuery("TASM", direct_urls=("https://archive.org/details/missing", "https://archive.org/details/working"))
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: [replace(product_spec("tasm"), sources={"archiveorg": query})])
    def get(ident):
        if ident == "missing":
            raise HTTPError("https://archive.org/metadata/missing", 404, "missing", {}, None)
        return {"identifier": ident, "title": "TASM"}
    monkeypatch.setattr(archiveorg, "get_item", get)
    monkeypatch.setattr(archiveorg, "process_item", lambda **_kw: [tmp_path / "TASM.TAH"])
    assert run(["tasm"], tmp_path / "downloads", False,
               lambda *_a, **_k: []) == [tmp_path / "TASM.TAH"]


@pytest.mark.parametrize("failed", [False, True])
def test_empty_or_failed_items_are_not_processed_again_but_search_fallback_remains(tmp_path, monkeypatch, failed):
    item = {"identifier": "empty", "title": "Borland Turbo Assembler"}
    found = {"identifier": "working", "title": "Borland Turbo Assembler"}
    jobs = [replace(product_spec("tasm"), sources={"archiveorg": SourceQuery(
        label, direct_urls=("https://archive.org/details/empty",), query=label)}) for label in ("first", "second")]
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: jobs)
    monkeypatch.setattr(archiveorg, "get_item", lambda _: item)
    monkeypatch.setattr(archiveorg.time, "sleep", lambda _: None)
    queries, processed = [], []
    monkeypatch.setattr(archiveorg, "search_items", lambda query: queries.append(query) or [item, found])
    def process(**kwargs):
        identity = kwargs["item"]["identifier"]
        processed.append(identity)
        if identity == "empty":
            if failed:
                raise ValueError("Unsupported image")
            return []
        return [tmp_path / "TASM.TAH"]
    monkeypatch.setattr(archiveorg, "process_item", process)
    assert run(["tasm"], tmp_path / "downloads", False, lambda *_a, **_k: []) == [tmp_path / "TASM.TAH"]
    assert processed == ["empty", "working"]
    assert queries == ["first", "second"]


def test_complete_edition_stops_between_archives_without_searching_or_processing_next_recipe(tmp_path, monkeypatch):
    product = replace(product_spec("tasm"), sources={"archiveorg": SourceQuery(
        "Assembler", query="broad", direct_urls=("https://archive.org/details/tools", "https://archive.org/details/unneeded"),
        archive_members=("TASM.TAH",))})
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: [product, product])
    metadata = []
    monkeypatch.setattr(archiveorg, "get_item", lambda ident: metadata.append(ident) or {"identifier": ident, "title": "Assembler"})
    monkeypatch.setattr(archiveorg, "get_item_files", lambda _: [
        {"name": "1.zip", "size": 100}, {"name": "2.zip", "size": 200}])
    monkeypatch.setattr(archiveorg, "search_items", lambda _: pytest.fail("Already complete"))
    plans = []
    def process(source, **_options):
        plans.append(source)
        return [tmp_path / "TASM.TAH"]
    assert run(["tasm"], tmp_path / "downloads", False, process, complete=lambda: bool(plans)) == [tmp_path / "TASM.TAH"]
    assert len(plans) == 1 and plans[0].allow_partial and metadata == ["tools"]
