"""Shared boundaries exercised through the actual HELP, DOS and MIDI consumers."""

from io import BytesIO
import gzip
import json
from pathlib import Path
import stat
import sys
import threading
import zipfile

import pytest

from thelpviewer.server.archives import core
from thelpviewer.server.archives.core import ExtractionError, ExtractionLimits, UnsafeArchiveError
from thelpviewer.server.archives.nested import extract_nested
from thelpviewer.server.converter.ingest import HelpInput, ingest_help
from thelpviewer.server.converter.results import ConversionError
from thelpviewer.server.converter.validation import load_bundle
from thelpviewer.server.converter.writers.bundle import export_bundle_tree
from thelpviewer.server.downloader.attempts import try_sources
from thelpviewer.server.downloader.cache import download_cached
from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.dos.packages import DosPackageExtractor
from thelpviewer.server.file_storage import atomic_file
from thelpviewer.server.midi.library import MidiLibrary
from thelpviewer.server.processing import observe_progress, report_progress


def zipped(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return output.getvalue()


def test_concurrent_consumers_fetch_one_cache_file_once_and_validate_each_selection(tmp_path):
    downloads = OnlineDownloader()
    fetching, processing, release, second = (threading.Event() for _ in range(4))
    calls, selections = [], []
    destination = tmp_path / "shared.zip"
    def fetch(path):
        calls.append(path)
        path.write_bytes(b"shared archive")
        fetching.set()
    def consume(selection):
        def process(path):
            assert path.read_bytes() == b"shared archive"
            if selection == "first":
                processing.set()
                assert release.wait(5)
            selections.append(selection)
            return selection
        return download_cached(destination, 1024, fetch, process=process)
    first = downloads.enqueue_processing(lambda: consume("first"))
    try:
        assert fetching.wait(2) and processing.wait(2)
        other = downloads.enqueue_processing(lambda: second.set() or consume("second"))
        assert second.wait(2) and not other.done()
        release.set()
        assert first.result(timeout=2) == "first" and other.result(timeout=2) == "second"
        assert len(calls) == 1 and selections == ["first", "second"]
        assert destination.read_bytes() == b"shared archive"
    finally:
        release.set()
        downloads.close()


@pytest.mark.parametrize("consumer", ["help", "dos", "midi"])
@pytest.mark.parametrize("unsafe", ["../HELP.HLP", "/HELP.HLP", "C:/HELP.HLP", "folder/../../HELP.HLP",
                                   "\x01CompObj", "\x05SummaryInformation", "symlink"])
def test_every_consumer_rejects_the_same_unsafe_archive(tmp_path, consumer, unsafe):
    name = unsafe
    if unsafe == "symlink":
        name = zipfile.ZipInfo("HELP.HLP")
        name.create_system = 3
        name.external_attr = (stat.S_IFLNK | 0o777) << 16
    data = zipped([(name, b"outside")])
    library = MidiLibrary(tmp_path / "var/midi", None)
    try:
        with pytest.raises(UnsafeArchiveError):
            if consumer == "help":
                archive = tmp_path / "source.zip"
                archive.write_bytes(data)
                ingest_help(HelpInput(archive, "Reference", members=("HELP.HLP",)),
                            tmp_path / "sources", None)
            elif consumer == "dos":
                DosPackageExtractor(1024).extract(data, {"format": "zip"})
            else:
                library._process_item({"id": "test"}, {"kind": "zip", "game": "Test"}, data)
        assert not (tmp_path / "sources").exists()
        assert not (tmp_path / "HELP.HLP").exists()
    finally:
        library.close()


def test_shared_extraction_accepts_dot_directory_and_preserves_binary_data(tmp_path):
    data = zipped([("./", b""), ("./bin/HELP.HLP", b"\x00\xff\x01")])
    source = tmp_path / "source.zip"
    source.write_bytes(data)
    result = core.extract_file(source, tmp_path / "expanded")
    assert result.total_bytes == 3
    assert [path.relative_to(tmp_path / "expanded").as_posix() for path in result.files] == ["bin/HELP.HLP"]
    assert result.files[0].read_bytes() == b"\x00\xff\x01"


@pytest.mark.parametrize("limits", [ExtractionLimits(max_files=1), ExtractionLimits(max_bytes=3)])
def test_shared_zip_budget_rejects_before_writing(tmp_path, limits):
    source = tmp_path / "source.zip"
    source.write_bytes(zipped([("one", b"123"), ("two", b"4")]))
    with pytest.raises(UnsafeArchiveError, match="quota"):
        core.extract_file(source, tmp_path / "expanded", limits=limits)
    assert list((tmp_path / "expanded").iterdir()) == []


@pytest.mark.parametrize("entries", [[("folder", b"file"), ("folder/member", b"data")],
                                    [("folder/member", b"data"), ("folder", b"file")]])
def test_shared_zip_rejects_file_directory_collisions_before_writing(tmp_path, entries):
    source = tmp_path / "source.zip"
    source.write_bytes(zipped(entries))
    with pytest.raises(UnsafeArchiveError, match="file/directory"):
        core.extract_file(source, tmp_path / "expanded")
    assert list((tmp_path / "expanded").iterdir()) == []


def test_nested_archives_have_an_explicit_depth_limit(tmp_path):
    source = tmp_path / "contents"
    source.mkdir()
    (source / "outer.zip").write_bytes(zipped([("inner.zip", zipped([("text.txt", b"text")]))]))
    with pytest.raises(ExtractionError, match="depth limit"):
        extract_nested(source, core.ExtractorTools(None, None, None), limits=ExtractionLimits(max_depth=1))


def test_external_extraction_timeout_stops_the_child(tmp_path):
    with pytest.raises(ExtractionError, match="timed out"):
        core._run_tool([sys.executable, "-c", "import time; time.sleep(10)"],
                       tmp_path, ExtractionLimits(timeout=.05))


def test_embedded_zip_end_record_does_not_misclassify_a_disk_image(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import json
    source = tmp_path / "disk.img"
    payload = bytearray(zipped([("inside.txt", b"text")]))
    offset = payload.index(b"PK\x01\x02")
    payload[offset:offset + 4] = b"BAD!"
    source.write_bytes(b"FAT image prefix" + payload)
    assert zipfile.is_zipfile(source)
    with pytest.raises(ExtractionError, match="central directory"):
        with core.open_zip(source):
            pass
    monkeypatch.setattr(core.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout=json.dumps({
        "lsarFormatName": "FAT12", "lsarContents": [{"XADFileName": "HELP.ZIP", "XADFileSize": 4}]})))
    tools = core.ExtractorTools("unar", "lsar", None)
    assert core.probe_extractable(source, tools).format_name == "FAT12"
    def extract(_path, destination, _tools, _limits, **_options):
        (destination / "HELP.ZIP").write_bytes(b"data")
        return True, ""
    monkeypatch.setattr(core, "_extract_with_unar", extract)
    result = core.extract_file(source, tmp_path / "expanded", tools)
    assert result.files[0].read_bytes() == b"data"


def test_program_section_listing_is_not_an_archive(tmp_path, monkeypatch):
    from types import SimpleNamespace
    source = tmp_path / "program.exe"
    source.write_bytes(b"program")
    monkeypatch.setattr(core.subprocess, "run", lambda *_a, **_k: SimpleNamespace(
        returncode=0, stdout="Type = PE\n----------\nPath = .debug0\nSize = 12\n"))
    assert core.probe_extractable(source, core.ExtractorTools(None, None, "7zz")) is None


@pytest.mark.parametrize("filename", ["INSTALAR.DOC", "document.bin", "unknown.pak", "disguised.zip"])
@pytest.mark.parametrize("tools", [core.ExtractorTools(None, None, None), core.ExtractorTools("unar", "lsar", None),
                                   core.ExtractorTools(None, None, "7zz")])
def test_ole_document_signature_is_a_leaf_not_an_archive(tmp_path, monkeypatch, filename, tools):
    document = core.OLE_COMPOUND_SIGNATURE + b"\0" * 504
    source = tmp_path / filename
    source.write_bytes(document)
    def unexpected_probe(*_args, **_kwargs):
        pytest.fail("An external tool inspected document streams as archive members")
    monkeypatch.setattr(core.subprocess, "run", unexpected_probe)
    assert core.probe_extractable(source, tools) is None
    with pytest.raises(ExtractionError, match="OLE compound document, not an archive"):
        core.extract_file(source, tmp_path / "out", tools)
    assert not list((tmp_path / "out").iterdir())
    assert source.read_bytes() == document


def test_help_member_discovery_skips_compound_documents_and_still_extracts_nested_help(tmp_path, monkeypatch):
    document = core.OLE_COMPOUND_SIGNATURE + b"\0" * 504
    archive = tmp_path / "software.zip"
    archive.write_bytes(zipped([("INSTALAR.DOC", document),
                               ("TOOLS.ZIP", zipped([("TDHELP.TDH", b"original help")]))]))
    def unexpected_probe(*_args, **_kwargs):
        pytest.fail("Compound document sent to an external archive tool")
    monkeypatch.setattr(core.subprocess, "run", unexpected_probe)
    collected = ingest_help(HelpInput(archive, "Debugger", members=("TDHELP.TDH",)),
                            tmp_path / "sources", core.ExtractorTools(None, None, None))
    assert [path.name for path in collected] == ["TDHELP.TDH"]
    assert collected[0].read_bytes() == b"original help"
    assert not list((tmp_path / "sources").rglob("INSTALAR.DOC*"))


def test_archive_policy_failure_cannot_be_hidden_by_fallback():
    calls = []
    def attempt(source):
        calls.append(source)
        raise UnsafeArchiveError("Unsafe source")
    with pytest.raises(UnsafeArchiveError):
        try_sources(["first", "second"], attempt, errors=(ValueError,))
    assert calls == ["first"]


def test_dos_recipe_cannot_wrap_unsafe_archive_as_a_recoverable_source(tmp_path, monkeypatch):
    from thelpviewer.server.downloader import packages
    calls = []
    data = zipped([("../GAME.EXE", b"unsafe")])
    def fetch(source, *_a, **_k):
        calls.append(source["url"])
        return data
    monkeypatch.setattr(packages, "fetch_source", fetch)
    source = {"id": "game", "url": "https://first.example/game.zip", "format": "zip",
              "alternatives": [{"url": "https://second.example/game.zip", "format": "zip"}]}
    with pytest.raises(UnsafeArchiveError):
        packages.download_package(source, tmp_path / "cache", 1024,
            process=DosPackageExtractor(1024).extract)
    assert calls == [source["url"]]


def test_failed_processing_does_not_publish_new_cache_and_retry_can_succeed(tmp_path):
    destination = tmp_path / "cache/source.zip"
    def fetch(path):
        path.write_bytes(b"raw archive")
    def reject(_path):
        raise ExtractionError("Missing disk part")
    with pytest.raises(ExtractionError, match="disk part"):
        download_cached(destination, 100, fetch, process=reject)
    assert not destination.exists() and not list(destination.parent.iterdir())
    assert download_cached(destination, 100, fetch, process=lambda path: path.read_bytes()) == b"raw archive"
    with pytest.raises(ExtractionError):
        download_cached(destination, 100, fetch, process=reject)
    assert destination.read_bytes() == b"raw archive"


@pytest.mark.parametrize("fetch_fails", [False, True])
def test_unreadable_cached_placeholder_is_refetched_atomically(tmp_path, monkeypatch, fetch_fails):
    import errno
    destination = tmp_path / "source.zip"
    destination.write_bytes(b"old cached bytes")
    original_open = Path.open
    def unavailable(path, *args, **kwargs):
        if path == destination:
            raise OSError(errno.EIO, "Input/output error")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", unavailable)
    def fetch(path):
        path.write_bytes(b"fresh archive")
        if fetch_fails:
            raise OSError("Network unavailable")
    events, processed = [], []
    with observe_progress(events.append):
        if fetch_fails:
            with pytest.raises(OSError, match="Network unavailable"):
                download_cached(destination, 100, fetch)
        else:
            result = download_cached(destination, 100, fetch,
                on_cached=lambda: pytest.fail("Unreadable cache counted as a hit"),
                process=lambda path: processed.append(path) or path.read_bytes())
            assert result == b"fresh archive" and processed[0] != destination
    monkeypatch.setattr(Path, "open", original_open)
    assert destination.read_bytes() == (b"old cached bytes" if fetch_fails else b"fresh archive")
    assert [event["phase"] for event in events] == ["Cached download unreadable; fetching again"]
    assert list(tmp_path.iterdir()) == [destination]


def test_discovery_can_collect_members_across_disks_without_relaxing_pinned_validation(tmp_path):
    sources = tmp_path / "sources"
    for number, name in enumerate(("FIRST.HLP", "SECOND.HLP", "OTHER.TXT")):
        archive = tmp_path / f"disk{number}.zip"
        archive.write_bytes(zipped([(name, name.encode())]))
        plan = HelpInput(archive, "Reference", members=("FIRST.HLP", "SECOND.HLP"), allow_partial=True)
        paths = ingest_help(plan, sources, core.ExtractorTools(None, None, None))
        assert [path.name for path in paths] == ([name] if number < 2 else [])
    assert {path.name for path in sources.rglob("*") if path.is_file()} == {"FIRST.HLP", "SECOND.HLP"}
    with pytest.raises(ValueError, match="Missing archive members"):
        ingest_help(HelpInput(archive, "Reference", members=("FIRST.HLP",)),
                    sources, core.ExtractorTools(None, None, None))
    archive.write_bytes(zipped([("a/FIRST.HLP", b"one"), ("b/FIRST.HLP", b"two")]))
    with pytest.raises(ValueError, match="ambiguous"):
        ingest_help(HelpInput(archive, "Reference", members=("FIRST.HLP",), allow_partial=True),
                    sources, core.ExtractorTools(None, None, None))


def test_atomic_writer_preserves_previous_file_after_failure(tmp_path):
    path = tmp_path / "bundle"
    path.write_bytes(b"published")
    with pytest.raises(ValueError):
        with atomic_file(path) as stream:
            stream.write(b"partial")
            raise ValueError("Conversion failed")
    assert path.read_bytes() == b"published"
    assert list(tmp_path.iterdir()) == [path]


def test_local_processing_events_reach_the_shared_queue_and_observer_is_restored():
    queue = OnlineDownloader()
    try:
        queue.begin("dos", [{"id": "one", "label": "One"}])
        events = []
        with observe_progress(events.append):
            with queue.context("dos", "one"):
                report_progress("Extracting", "Disk.img", stage="extract")
                row = queue.snapshot(private=True)["items"][0]
                assert row["phase"] == "Extracting" and row["state"] == "running"
            report_progress("Outer")
        assert [event["phase"] for event in events] == ["Outer"]
    finally:
        queue.close()


@pytest.mark.parametrize("invalid", [b"not gzip", gzip.compress(b"{}"),
    gzip.compress(json.dumps({"uhf_version": "2.0", "metadata": {}, "topics": {"1": {"id": 2, "content": []}},
                              "contents": [], "index": []}).encode())])
def test_bundle_validation_rejects_incomplete_or_inconsistent_output(tmp_path, invalid):
    path = tmp_path / "invalid.json.gz"
    path.write_bytes(invalid)
    with pytest.raises(ConversionError, match="UHF"):
        load_bundle(path)


def test_catalog_rebuild_is_identical_to_fresh_export(tmp_path):
    from thelpviewer.server.converter.catalog import rebuild_catalog
    source = tmp_path / "sources/Reference.TXT"
    source.parent.mkdir()
    source.write_bytes(b"@Reference\r\n:Topic\r\n%Body\r\n")
    output = tmp_path / "helps"
    result = export_bundle_tree(source.parent, output, layout="helps")
    assert len(result) == 1 and not result[0].error
    before = (output / "catalog.json").read_bytes()
    rebuild_catalog(output, output / "catalog.json")
    assert (output / "catalog.json").read_bytes() == before


def test_server_build_uses_one_catalog_pass_and_rejects_corrupt_stage(tmp_path, monkeypatch):
    from thelpviewer.server.converter import build
    from thelpviewer.server.converter.writers import bundle
    from thelpviewer.server.converter.writers.json import HelpJsonRenderer
    source = tmp_path / "sources/HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@Reference\r\n:Topic\r\n%Body\r\n")
    output = tmp_path / "helps"
    monkeypatch.setattr(bundle, "rebuild_catalog", lambda *_: pytest.fail("Duplicate catalog pass"))
    calls = []
    original = build.rebuild_catalog
    def catalog(*args):
        calls.append(True)
        return original(*args)
    monkeypatch.setattr(build, "rebuild_catalog", catalog)
    build.build_help_groups(["dos-reference"], source.parent.parent, output)
    assert calls == [True]
    published = {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}
    def invalid(_self, path, **_options):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(b"{}"))
        return path
    monkeypatch.setattr(HelpJsonRenderer, "write_json_gz", invalid)
    with pytest.raises(ConversionError, match="UHF"):
        build.build_help_groups(["dos-reference"], source.parent.parent, output)
    assert all((output / path).read_bytes() == data for path, data in published.items())
    assert not list(output.parent.glob(".helps-build-*"))
    assert source.read_bytes() == b"@Reference\r\n:Topic\r\n%Body\r\n"


def test_midi_raw_cache_is_processed_on_reuse_without_another_http_transfer(tmp_path, monkeypatch):
    midi = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60MTrk\x00\x00\x00\x04\x00\xff\x2f\x00"
    library = MidiLibrary(tmp_path / "var/midi", None)
    calls = []
    monkeypatch.setattr(library, "_fetch", lambda *_a: calls.append(True) or midi)
    source = {"id": "music", "allowed_hosts": ["music.test"]}
    item = {"kind": "midi", "filename": "theme.mid", "url": "https://music.test/theme.mid"}
    try:
        assert library._download_item(source, item)
        cached = list((tmp_path / "var/downloads/midi").iterdir())
        assert len(cached) == 1 and cached[0].read_bytes() == midi
        (library.root / "music/theme.mid").unlink()
        assert library._download_item(source, item)
        assert calls == [True]
        assert (library.root / "music/theme.mid").read_bytes() == midi
    finally:
        library.close()


@pytest.mark.parametrize("fails", [False, True])
def test_standalone_help_job_closes_only_its_owned_downloader(tmp_path, monkeypatch, fails):
    from types import SimpleNamespace
    from thelpviewer.server.downloader import service
    owned = []
    class TrackedDownloader(OnlineDownloader):
        def close(self):
            owned.append(self)
            super().close()
    monkeypatch.setattr(service, "OnlineDownloader", TrackedDownloader)
    monkeypatch.setattr(service, "supported_product_keys", lambda *_: ["tp"])
    def run(**_options):
        if fails:
            raise UnsafeArchiveError("Unsafe")
        return []
    monkeypatch.setattr(service.importlib, "import_module", lambda _: SimpleNamespace(run=run))
    options = dict(source_keys=["direct"], dry_run=True)
    if fails:
        with pytest.raises(UnsafeArchiveError):
            service.download_products(["tp"], tmp_path / "sources", tmp_path / "cache", **options)
    else:
        service.download_products(["tp"], tmp_path / "sources", tmp_path / "cache", **options)
    assert len(owned) == 1 and owned[0]._closed
    shared = OnlineDownloader()
    try:
        if fails:
            with pytest.raises(UnsafeArchiveError):
                service.download_products(["tp"], tmp_path / "sources", tmp_path / "cache", downloads=shared, **options)
        else:
            service.download_products(["tp"], tmp_path / "sources", tmp_path / "cache", downloads=shared, **options)
        assert not shared._closed and len(owned) == 1
    finally:
        shared.close()
