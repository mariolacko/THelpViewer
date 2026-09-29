"""Archive.org discovery of pinned DOS reference HELP files."""

import pytest

from thelpviewer.downloader.archiveorg import process_item, run
from thelpviewer.downloader.extractor import ExtractorTools
from thelpviewer.downloader.catalog import product_spec


def test_reference_archive_search_uses_exact_members_and_product_root(tmp_path, monkeypatch):
    product = product_spec("msdos622")
    query = product.sources["archiveorg"]
    monkeypatch.setattr(
        "thelpviewer.downloader.archiveorg.get_item_files",
        lambda _identifier: [{"name": "en_msdos622.zip", "size": "4478365"}],
    )
    monkeypatch.setattr(
        "thelpviewer.downloader.archiveorg.download_file",
        lambda _url, _dest: None,
    )
    collected = []

    def fake_collect(_archive, members, label, sources_dir, _extractor):
        collected.append((members, label))
        return [sources_dir / label / "HELP.HLP"]

    monkeypatch.setattr("thelpviewer.downloader.archiveorg.collect_archive_members", fake_collect)
    sources = tmp_path / "sources"
    result = process_item(
        {"identifier": "en_msdos622.zip", "title": "MS-DOS 6.22 (English)"},
        product,
        query,
        tmp_path / "downloads",
        sources,
        ExtractorTools(None, None, None),
        False,
        [],
    )

    assert collected == [(('HELP.HLP',), 'Microsoft MS-DOS 6.22')]
    assert result == [sources / "Microsoft MS-DOS 6.22" / "HELP.HLP"]


def test_reference_archive_search_skips_existing_selected_files(tmp_path, monkeypatch):
    source = tmp_path / "sources" / "Microsoft MS-DOS 6.22" / "HELP.HLP"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"existing")
    monkeypatch.setattr(
        "thelpviewer.downloader.archiveorg.get_item",
        lambda *_: pytest.fail("existing candidate was searched again"),
    )

    assert run(
        ["msdos622"],
        tmp_path / "sources",
        tmp_path / "downloads",
        False,
        ExtractorTools(None, None, None),
    ) == []


def test_existing_product_version_is_not_appended_to_download_directory(tmp_path, monkeypatch):
    product = product_spec("qbx")
    query = product.sources["archiveorg"]
    monkeypatch.setattr(
        "thelpviewer.downloader.archiveorg.get_item_files",
        lambda _identifier: [{"name": "qb71.zip", "size": "100"}],
    )
    monkeypatch.setattr("thelpviewer.downloader.archiveorg.download_file", lambda *_: None)
    labels = []

    def fake_collect(_archive, label, _sources_dir, _extractor, *, lang_code):
        labels.append(label)
        return []

    monkeypatch.setattr("thelpviewer.downloader.archiveorg.collect_from_archive", fake_collect)
    process_item(
        {"identifier": "qb71zip", "title": "QuickBASIC Extended 7.1"},
        product,
        query,
        tmp_path / "downloads",
        tmp_path / "sources",
        ExtractorTools(None, None, None),
        False,
        [],
    )

    assert labels == ["Microsoft QuickBASIC Extended 7.1"]
