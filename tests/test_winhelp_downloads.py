"""Retain original Windows Help data; detection/conversion is independent."""

from pathlib import Path
import shutil

import pytest

from thelpviewer.server.downloader import archiveorg, catalog, service, winworld
from thelpviewer.server.converter.sources import collect_help_files, copy_help_files
from tests.help_downloads import help_processor
from thelpviewer.server.archives.core import ExtractorTools
from thelpviewer.server.converter.readers.winhelp_binary import WinHelpFile


def test_windows_help_is_retained_by_archive_collection_and_duplicate_copy(tmp_path):
    original = Path("var/sources/Borland C++ 4.x/OPENHELP.HLP").read_bytes()
    source = tmp_path / "extracted"
    source.mkdir()
    help_path = source / "OPENHELP.HLP"
    help_path.write_bytes(original)
    assert collect_help_files(source) == [help_path]
    destination = tmp_path / "sources"
    copied = copy_help_files([help_path], destination / "Borland C++", destination)
    assert copied[0].read_bytes() == original
    assert copy_help_files([help_path], destination / "Borland C++", destination) == []
    help_path.write_bytes(b"another revision")
    with pytest.raises(ValueError, match="Conflicting"):
        copy_help_files([help_path], copied[0].parent, destination)
    assert copied[0].read_bytes() == original


def test_archiveorg_direct_hlp_download_is_not_deleted(tmp_path, monkeypatch):
    product = catalog.product_spec("bc")
    query = product.sources["archiveorg"]
    original = Path("var/sources/Borland C++ 4.x/OPENHELP.HLP").read_bytes()
    monkeypatch.setattr(archiveorg, "get_item_files", lambda _: [{"name": "OPENHELP.HLP", "size": str(len(original))}])
    def download(_url, path, *, process, **_options):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original)
        return process(path)
    monkeypatch.setattr(service, "download_file", download)
    result = archiveorg.process_item({"identifier": "borland", "title": "Borland C++ 4.52"},
                                    product, query, tmp_path / "downloads",
                                    help_processor(tmp_path / "sources", ExtractorTools(None, None, None)), False, [])
    assert len(result) == 1 and result[0].read_bytes() == original


def test_copy_rejects_a_dangling_destination_symlink(tmp_path):
    original = tmp_path / "OPENHELP.HLP"
    original.write_bytes(b"original")
    target = tmp_path / "sources"
    target.mkdir()
    outside = tmp_path / "outside.hlp"
    (target / original.name).symlink_to(outside)
    with pytest.raises(ValueError, match="Conflicting"):
        copy_help_files([original], target, target)
    assert not outside.exists() and (target / original.name).is_symlink()


def test_archiveorg_can_select_iso_without_selecting_raw_flux_images():
    files = [{"name": "dos.iso", "size": "123"}, {"name": "disk.raw", "size": "456"}]
    assert archiveorg.pick_download_files(files, "item") == [("dos.iso", "https://archive.org/download/item/dos.iso")]


def test_repeated_crc_provenance_is_one_edition_job_per_provider():
    for provider in ("winworld", "archiveorg"):
        jobs = catalog.products_for_source(provider, ["bc"])
        # Other verified editions can add jobs; repeated pair records must not.
        assert len([job for job in jobs if job.default_version == "4.5"]) == 1
        assert len([job for job in jobs if job.default_version == "4.52"]) == 1
        pinned = next(j for j in jobs if j.default_version == "4.52")
        assert len(pinned.sources[provider].archive_members) == 40
        assert pinned.collection_prefixes == ("Borland C++ 4.x",)
        older = next(j for j in jobs if j.default_version == "4.5")
        assert older.collection_prefixes == ("Borland C++ 4.5",)
        members = older.sources[provider].archive_members
        assert len(members) == 4
        assert {Path(member).name for member in members} == {"BCW.HLP", "BCW.HLX", "OWL.HLP", "OWL.HLX"}
        if provider == "archiveorg":
            assert all("/" not in member for member in members)


def test_actual_pinned_cd_download_retains_exact_matching_index_and_hlp(tmp_path, monkeypatch):
    archive = Path("var/downloads/help/Borland C++ 4.52.7z")
    sevenzip = shutil.which("7zz") or shutil.which("7z")
    if not archive.exists() or not sevenzip:
        pytest.skip("Cached original CD archive and 7-Zip are needed")
    pinned = next(j for j in catalog.products_for_source("winworld", ["bc"]) if j.default_version == "4.52")
    monkeypatch.setattr(winworld, "products_for_source", lambda *_: [pinned])
    monkeypatch.setattr(winworld, "get_download_info", lambda _: ("Borland C++ 4.52",
        [("mirror", "https://example.com/bc452.7z")]))
    def cached(_url, destination, *, process, **_options):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, destination)
        return process(destination)
    monkeypatch.setattr(service, "download_file", cached)
    files = winworld.run(["bc"], tmp_path / "downloads", False,
                        help_processor(tmp_path / "sources", ExtractorTools(None, None, sevenzip)))
    assert len(files) == 40
    for path in files:
        assert path.read_bytes() == (Path("var/sources/Borland C++ 4.x") / path.name).read_bytes()
        if path.suffix == ".HLP":
            companion = path.with_suffix(".HLX")
            assert WinHelpFile(path.read_bytes()).stream("|KWBTREE") == companion.read_bytes()
