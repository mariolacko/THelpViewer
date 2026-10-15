"""Provider selectors are not user-facing archive names or progress labels."""

import zipfile

import pytest

from thelpviewer.server.downloader import direct, winworld
from thelpviewer.server.downloader.cache import download_filename
from thelpviewer.server.downloader.extractor import ExtractorTools, find_sevenzip, extract_file
from thelpviewer.server.downloader.http import observe_downloads


@pytest.mark.parametrize("name,expected", [
    ("Microsoft%20QuickC%202.50.zip", "Microsoft QuickC 2.50.zip"),
    ("Borland Turbo Pascal 7.0 (1992).7z", "Borland Turbo Pascal 7.0 _1992_.7z"),
    ("../../unsafe%2Fpath%5Cname.zip", "_.._unsafe_path_name.zip"),
    ("..", "archive"),
])
def test_readable_archive_names_stay_within_download_directory(name, expected):
    assert download_filename(name) == expected


def test_pinned_winworld_archive_uses_page_title_and_does_not_need_family_scraping(tmp_path, monkeypatch):
    selector = "64c3bec2-abc2-b9c3-aa03-11c3a6c2bb2a"
    page = f"https://winworldpc.com/download/{selector}"
    mirror = page + "/from/c39ac2af-c381-c2bf-1b25-11c3a4e284a2"
    html = f'<h1>Borland Turbo Assembler 2.0 (5.25-360k)</h1><a href="{mirror.removeprefix("https://winworldpc.com")}">Server 2</a>'
    monkeypatch.setattr(winworld, "fetch_polite", lambda url: html)
    calls = []
    def download(url, dest):
        calls.append((url, dest.name))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"archive")
        return dest
    monkeypatch.setattr(winworld, "download_file", download)
    monkeypatch.setattr(winworld, "collect_archive_members", lambda *args: [tmp_path / "TASM.TAH"])
    failures = []
    result = winworld.process_version("2.0", "", "Borland Turbo Assembler", tmp_path / "downloads",
        tmp_path / "sources", ExtractorTools(None, None, None), False, failures,
        records=[(selector, page)], archive_members=("TASM.TAH",))
    assert result == [tmp_path / "TASM.TAH"] and not failures
    assert calls == [(mirror, "Borland Turbo Assembler 2.0 _5.25-360k_.archive")]


def test_direct_archive_url_is_decoded_for_the_disk_name(tmp_path, monkeypatch):
    from types import SimpleNamespace
    query = SimpleNamespace(direct_urls=("https://example.test/Microsoft%20QuickC%202.50.zip",),
        archive_members=("QC.HLP",))
    product = SimpleNamespace(key="quickc", label="Microsoft QuickC", collection_prefixes=("Microsoft QuickC 2.50",),
        sources={"direct": query})
    monkeypatch.setattr(direct, "products_for_source", lambda *args: [product])
    calls = []
    monkeypatch.setattr(direct, "download_file", lambda url, dest: calls.append(dest))
    monkeypatch.setattr(direct, "collect_archive_members", lambda *args: [])
    direct.run(["quickc"], tmp_path / "sources", tmp_path / "downloads", False, ExtractorTools(None, None, None))
    assert calls[0].name == "direct_quickc_Microsoft QuickC 2.50.zip"


def test_extraction_reports_its_phase_instead_of_completed_download_bytes(tmp_path):
    tool = find_sevenzip()
    if not tool:
        pytest.skip("7-Zip is required")
    archive = tmp_path / "Readable archive.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("HELP.TXT", "Help")
    events = []
    with observe_downloads(events.append):
        assert extract_file(archive, tmp_path / "expanded", ExtractorTools(None, None, tool))
    assert events == [{"phase": "Extracting", "file": archive.name, "received": 0, "bytes_total": 0}]


def test_source_queue_counts_new_and_cached_files_and_preserves_waiting_jobs(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from thelpviewer.server.downloader import service
    from thelpviewer.server.downloader.http import report_progress
    monkeypatch.setattr(service, "supported_product_keys", lambda _: ["tp", "tc"])
    def run(**kwargs):
        report_progress("Reading source page")
        report_progress("Downloaded", "Help.zip", downloaded_size=16)
        report_progress("Using cached archive", "Other Help.zip")
        if kwargs["product_keys"] == ["tc"]:
            report_progress("Source warning", warning="One mirror unavailable")
        return []
    monkeypatch.setattr(service.importlib, "import_module", lambda _: SimpleNamespace(run=run))
    events = []
    result = service.download_products(["tp", "tc"], tmp_path / "sources", tmp_path / "downloads",
        source_keys=["winworld"], dry_run=True, on_progress=events.append)
    assert [job["state"] for job in events[0]["queue"]] == ["running", "pending"]
    assert [job["state"] for job in events[-1]["queue"]] == ["checked", "checked"]
    assert not events[0]["queue"][0].get("warning")
    assert events[-1]["queue"][1]["warning"] and result.warnings == ["winworld/tc: One mirror unavailable"]
    assert events[-1]["downloads"] == {"new_files": 2, "cached_files": 2, "bytes": 32}
    reading = [event for event in events if event["phase"] == "Reading source page"]
    assert [event["file"] for event in reading] == ["Borland Turbo Pascal", "Borland Turbo C"]
    assert all(not event["received"] and not event["bytes_total"] for event in reading)
