"""CRC-edition sources are executable downloader jobs, not ignored metadata."""

from pathlib import Path
import shutil

import pytest

from thelpviewer.help_database import crc32_file
from thelpviewer.server.downloader import archiveorg, catalog, direct, service, winworld
from thelpviewer.server.downloader.extractor import ExtractorTools


def test_provider_catalog_includes_editions_and_keeps_product_keys_unique():
    jobs = catalog.products_for_source("winworld", ["td"])
    assert jobs[0].sources["winworld"].slug == "turbo-assembler"
    assert len(jobs) == 8  # Family, Profiler 1.01, six DOS/Win/32 editions.
    assert {job.key for job in jobs} == {"td"}
    assert {job.default_version for job in jobs[1:]} == {"1.01", "4.0", "5.0"}
    assert len(catalog.supported_product_keys("winworld")) == len(set(catalog.supported_product_keys("winworld")))
    assert catalog.products_for_source("winworld", ["missing"]) == []


def test_quickc250_advisor_has_executable_exact_member_provenance():
    jobs = catalog.products_for_source("direct", ["quickc"])
    assert len(jobs) == 1
    job = jobs[0]
    assert job.collection_prefixes == ("Microsoft QuickC, C, and C++ 2.50",)
    assert job.default_version == "2.50"
    origin = job.sources["direct"]
    assert origin.archive_members == ("QC.HLP",)
    assert origin.direct_urls == (
        "https://archive.org/download/microsoft-quick-c-2.50/Microsoft%20QuickC%202.50.zip",
    )
    fallback = [job for job in catalog.products_for_source("archiveorg", ["quickc"])
                if job.collection_prefixes == ("Microsoft QuickC, C, and C++ 2.50",)]
    assert len(fallback) == 1
    assert fallback[0].sources["archiveorg"].archive_members == ("QC.HLP",)
    assert fallback[0].sources["archiveorg"].query
    assert "QC.HL2" in fallback[0].sources["archiveorg"].search_text


@pytest.mark.parametrize("version,archive_name,selector,crc", [
    ("2.0", "Borland Turbo Assembler 2.0 _5.25-360k_.7z",
     "64c3bec2-abc2-b9c3-aa03-11c3a6c2bb2a", 0x07E89446),
    ("2.01", "Borland Turbo Assembler 2.01 _5.25_.7z",
     "501ac3a8-59c2-bdc3-a511-c3a4e280a613", 0xC517BD6D),
])
def test_pinned_winworld_edition_survives_family_discovery_failure_and_extracts_real_archive(
        tmp_path, monkeypatch, version, archive_name, selector, crc):
    archive = Path("var/downloads/help") / archive_name
    sevenzip = shutil.which("7zz") or shutil.which("7z")
    if not archive.is_file() or not sevenzip:
        pytest.skip("Cached original archive and 7-Zip are needed for real extraction")
    jobs = catalog.products_for_source("winworld", ["tasm"])
    assert len(jobs) == 3
    jobs = [job for job in jobs if job.sources["winworld"].slug or job.default_version == version]
    monkeypatch.setattr(winworld, "products_for_source", lambda *_: jobs)

    def unavailable(*_):
        raise RuntimeError("Product listing unavailable")
    monkeypatch.setattr(winworld, "get_version_urls", unavailable)
    requested = []
    monkeypatch.setattr(winworld, "get_download_info", lambda url: (requested.append(url) or archive_name,
        [("mirror", "https://example.com/tasm.7z")]))
    def cached(_url, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, destination)
        return destination
    monkeypatch.setattr(winworld, "download_file", cached)
    sources = tmp_path / "sources"
    result = winworld.run(["tasm"], sources, tmp_path / "downloads", False,
                          ExtractorTools(None, None, sevenzip))
    assert requested == [f"https://winworldpc.com/download/{selector}"]
    edition = next(job for job in jobs if job.default_version == version)
    assert result == [sources / edition.collection_prefixes[0] / "TASM.TAH"]
    assert crc32_file(result[0]) == crc
    assert list(sources.rglob("TFHELP.TFH")) == []
    assert list(sources.rglob("THELP.COM")) == []


@pytest.mark.parametrize("disk,collection,crc", [
    ("Disk2-Utilities.img", "Borland Turbo Assembler 1.01 (DE)", 0xF126AD2C),
    ("Disk4-Hilfe.img", "Borland Turbo Debugger 1.5 (DE)", 0x4B5D33CE),
])
def test_pinned_disk_image_uses_edition_collection_and_exact_member(tmp_path, monkeypatch, disk, collection, crc):
    archive = Path(f"var/downloads/help/ao_borland-tassm-1.01-tdebug-1.5-german_{disk}")
    sevenzip = shutil.which("7zz") or shutil.which("7z")
    if not archive.is_file() or not sevenzip:
        pytest.skip("Cached original disk image and 7-Zip are needed for real extraction")
    jobs = catalog.products_for_source("direct", ["td"])
    assert len(jobs) == 2
    jobs = [job for job in jobs if job.collection_prefixes == (collection,)]
    assert len(jobs) == 1 and jobs[0].default_version == "1.5"
    monkeypatch.setattr(direct, "products_for_source", lambda *_: jobs)
    requested = []
    def cached(url, destination):
        requested.append(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, destination)
        return destination
    monkeypatch.setattr(direct, "download_file", cached)
    sources = tmp_path / "sources"
    result = direct.run(["td"], sources, tmp_path / "downloads", False,
                        ExtractorTools(None, None, sevenzip))
    assert requested == [f"https://archive.org/download/borland-tassm-1.01-tdebug-1.5-german/{disk}"]
    assert result == [sources / collection / "TDHELP.TDH"]
    assert crc32_file(result[0]) == crc
    assert [path for path in sources.rglob("*") if path.is_file()] == result


def test_pascal4_provenance_downloads_the_original_help_not_runtime_companions(tmp_path, monkeypatch):
    archive = Path("var/downloads/help/ao_BorlandTurboPascal4.0_disk1_compiler.img")
    sevenzip = shutil.which("7zz") or shutil.which("7z")
    if not archive.is_file() or not sevenzip:
        pytest.skip("Cached original compiler disk and 7-Zip are needed for real extraction")
    jobs = [job for job in catalog.products_for_source("direct", ["tp"])
            if job.collection_prefixes == ("Borland Turbo Pascal 4.0",)]
    assert len(jobs) == 1 and jobs[0].default_version == "4.0"
    assert jobs[0].sources["direct"].archive_members == ("TURBO.HLP",)
    monkeypatch.setattr(direct, "products_for_source", lambda *_: jobs)
    requested = []

    def cached(url, destination):
        requested.append(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, destination)
        return destination

    monkeypatch.setattr(direct, "download_file", cached)
    sources = tmp_path / "sources"
    result = direct.run(["tp"], sources, tmp_path / "downloads", False, ExtractorTools(None, None, sevenzip))
    assert requested == ["https://archive.org/download/BorlandTurboPascal4.0/disk1_compiler.img"]
    assert result == [sources / "Borland Turbo Pascal 4.0/TURBO.HLP"]
    assert crc32_file(result[0]) == 0x58AB33C3
    assert result[0].read_bytes() == Path("data/sources/Borland Turbo Pascal 4.0/TURBO.HLP").read_bytes()
    assert [path for path in sources.rglob("*") if path.is_file()] == result
    provenance = [job for job in catalog.products_for_source("archiveorg", ["tp"])
                  if job.collection_prefixes == ("Borland Turbo Pascal 4.0",)]
    assert len(provenance) == 1
    assert provenance[0].sources["archiveorg"].direct_urls == ("https://archive.org/details/BorlandTurboPascal4.0",)
    assert provenance[0].sources["archiveorg"].query and provenance[0].sources["archiveorg"].search_text


def test_sidekick2_pinned_archive_keeps_the_catalog_collection_and_only_its_help(tmp_path, monkeypatch):
    archive = Path("var/downloads/help/ww_sidekick2_19910111.7z")
    sevenzip = shutil.which("7zz") or shutil.which("7z")
    if not archive.is_file() or not sevenzip:
        pytest.skip("Cached original distribution and 7-Zip are needed for real extraction")
    jobs = [job for job in catalog.products_for_source("winworld", ["sk"])
            if job.collection_prefixes == ("Borland Sidekick 2",)]
    assert len(jobs) == 1 and jobs[0].default_version == "2.0"
    monkeypatch.setattr(winworld, "products_for_source", lambda *_: jobs)
    requested = []
    monkeypatch.setattr(winworld, "get_download_info", lambda url: (requested.append(url) or "Borland Sidekick 2",
        [("mirror", "https://example.com/sk2.7z")]))

    def cached(_url, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive, destination)
        return destination

    monkeypatch.setattr(winworld, "download_file", cached)
    sources = tmp_path / "sources"
    result = winworld.run(["sk"], sources, tmp_path / "downloads", False, ExtractorTools(None, None, sevenzip))
    assert requested == ["https://winworldpc.com/download/2d20744e-7356-11c3-a7c2-9d25525400ef"]
    assert result == [sources / "Borland Sidekick 2/SK2.HLP"]
    assert crc32_file(result[0]) == 0x58D27871
    assert result[0].read_bytes() == Path("data/sources/Borland Sidekick 2/SK2.HLP").read_bytes()
    assert [path for path in sources.rglob("*") if path.is_file()] == result
    assert not (sources / "Borland Sidekick 2.0").exists()


def test_archiveorg_consumes_edition_queries_without_repeating_successful_items(tmp_path, monkeypatch):
    jobs = catalog.products_for_source("archiveorg", ["tasm"])
    assert len(jobs) == 3
    monkeypatch.setattr(archiveorg, "products_for_source", lambda *_: jobs)
    monkeypatch.setattr(archiveorg.time, "sleep", lambda *_: None)
    queries, processed = [], []
    item = {"identifier": "tasm201", "title": "Borland Turbo Assembler 2.01"}
    monkeypatch.setattr(archiveorg, "search_items", lambda query: queries.append(query) or [item])
    def collect(**kwargs):
        processed.append(kwargs["item"]["identifier"])
        return [tmp_path / "TASM.TAH"]
    monkeypatch.setattr(archiveorg, "process_item", collect)
    result = archiveorg.run(["tasm"], tmp_path / "sources", tmp_path / "downloads",
                           False, ExtractorTools(None, None, None))
    assert queries == [job.sources["archiveorg"].query for job in jobs]
    assert processed == ["tasm201"]
    assert result == [tmp_path / "TASM.TAH"]


def test_server_download_invokes_provider_once_for_all_editions(tmp_path, monkeypatch):
    calls, progress = [], []
    def run(**kwargs):
        calls.append(kwargs["product_keys"])
        assert len(catalog.products_for_source("winworld", kwargs["product_keys"])) == 8
        return [tmp_path / "TDHELP.TDH"]
    monkeypatch.setattr(winworld, "run", run)
    result = service.download_products(["td"], tmp_path / "sources", tmp_path / "downloads",
                                       source_keys=["winworld"], dry_run=True,
                                       on_progress=progress.append)
    assert calls == [["td"]]
    assert result.files == [tmp_path / "TDHELP.TDH"] and not result.warnings
    assert progress[-1]["processed"] == progress[-1]["total"] == 1
