from thelpviewer.server.converter import selection
"""Archive discovery preserves verified editions and original source bytes."""

import pytest
from dataclasses import replace
from types import SimpleNamespace
from urllib.error import HTTPError
import zlib

from thelpviewer.help_database import HelpDatabaseEntry, load_help_manifest, product_entries
from thelpviewer.server.downloader import catalog, http, olddos, service, transport, winworld
from thelpviewer.server.converter import sources as collector
from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.archives.core import ExtractorTools, probe_extractable, extract_file
from thelpviewer.server.downloader.service import plan_help_downloads


def test_verified_crc_controls_destination_and_filters_unselected_editions(tmp_path, monkeypatch):
    sources = tmp_path / "sources"
    extracted = tmp_path / "extracted"
    entries = {entry.version: entry for entry in product_entries("tc")}
    files = []
    for version in ("1.x current", "2.0"):
        path = extracted / version / "TCHELP.TCH"
        path.parent.mkdir(parents=True)
        path.write_bytes(version.encode())
        files.append(path)
    monkeypatch.setattr(collector, "lookup_help_database_entry", lambda path: entries[path.read_text()])
    target = sources / entries["1.x current"].collection
    target.mkdir(parents=True)
    original = target / "TCHELP.TCH"
    original.write_bytes(b"1.x current")
    with selection.select_help_packages(["tc:2.0"]):
        copied = collector.copy_help_files(files, target, sources)
    expected = sources / entries["2.0"].collection / "TCHELP.TCH"
    assert copied == [expected] and expected.read_bytes() == b"2.0"
    assert original.read_bytes() == b"1.x current"
    # Re-running the selected edition reuses the exact original instead of overwriting it.
    with selection.select_help_packages(["tc:2.0"]):
        assert collector.copy_help_files(files, target, sources) == []


def test_unknown_conflicting_original_is_still_protected(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "lookup_help_database_entry", lambda path: None)
    source = tmp_path / "incoming.TCH"
    source.write_bytes(b"different source")
    root = tmp_path / "sources"
    target = root / "Product"
    target.mkdir(parents=True)
    original = target / "INCOMING.TCH"
    original.write_bytes(b"permanent original")
    with pytest.raises(ValueError, match="Conflicting original HELP source"):
        collector.copy_help_files([source], target, root)
    assert original.read_bytes() == b"permanent original"


@pytest.mark.parametrize("same_component", [False, True])
def test_registered_component_revision_is_retained_without_overwriting(tmp_path, monkeypatch, same_component):
    source = tmp_path / "incoming" / "TURBO.HLP"
    source.parent.mkdir()
    source.write_bytes(b"new verified revision")
    root = tmp_path / "sources"
    target = root / "Borland Turbo Pascal 5.5"
    target.mkdir(parents=True)
    original = target / "TURBO.HLP"
    original.write_bytes(b"existing verified revision")
    previous = HelpDatabaseEntry(1, ("TURBO.HLP",), "Help", "Borland Turbo Pascal 5.5",
                                product_key="tp", version="5.5", bundle_stem="turbo")
    incoming = replace(previous, crc32=2, bundle_stem="turbo" if same_component else "other")
    monkeypatch.setattr(collector, "lookup_help_database_entry", lambda path:
                        previous if path.read_bytes() == original.read_bytes() else incoming)
    if same_component:
        assert collector.copy_help_files([source], target, root) == []
    else:
        with pytest.raises(ValueError, match="Conflicting original"):
            collector.copy_help_files([source], target, root)
    assert original.read_bytes() == b"existing verified revision"


def test_registered_editions_do_not_share_original_filenames_in_one_collection():
    destinations = {}
    for entry in load_help_manifest().entries:
        for filename in entry.filenames:
            key = (entry.collection.casefold(), filename.casefold())
            identity = (entry.product_key, entry.version)
            assert key not in destinations or destinations[key] == identity, (key, identity, destinations.get(key))
            destinations[key] = identity


@pytest.mark.parametrize("conflict", [False, True])
def test_corrected_collection_relocates_only_crc_verified_originals(tmp_path, monkeypatch, conflict):
    root = tmp_path / "sources"
    old = root / "Product/HELP.TDH"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"edition one")
    incoming = tmp_path / "HELP.TDH"
    incoming.write_bytes(b"edition two")
    entries = {
        b"edition one": HelpDatabaseEntry(1, ("HELP.TDH",), "Help", "Product/1.0"),
        b"edition two": HelpDatabaseEntry(2, ("HELP.TDH",), "Help", "Product"),
    }
    canonical = root / "Product/1.0/HELP.TDH"
    monkeypatch.setattr(collector, "lookup_help_database_entry", lambda path: entries.get(path.read_bytes()))
    if conflict:
        canonical.parent.mkdir(parents=True)
        canonical.write_bytes(b"different permanent source")
        with pytest.raises(ValueError, match="Conflicting original"):
            collector.copy_help_files([incoming], old.parent, root)
        assert old.read_bytes() == b"edition one" and canonical.read_bytes() == b"different permanent source"
    else:
        assert collector.copy_help_files([incoming], old.parent, root) == [old]
        assert old.read_bytes() == b"edition two" and canonical.read_bytes() == b"edition one"


def test_winworld_broad_release_page_does_not_download_other_versions(tmp_path, monkeypatch):
    records = [(f"Pascal {version}.zip", f"https://winworldpc.com/download/{version}") for version in ("5.0", "5.5", "6.0")]
    monkeypatch.setattr(winworld, "get_download_info", lambda url: (
        "Borland Turbo Pascal " + url.rsplit("/", 1)[-1], [("Mirror", url + "/from/mirror")]))
    downloaded = []
    def process(source, **_options):
        downloaded.append(source.path.name)
        return []
    failures = []
    with selection.select_help_packages(["tp:5.5"]):
        winworld.process_version("5.x", "", "Borland Turbo Pascal", tmp_path / "downloads",
            process, False, failures,
            records=records, product_key="tp")
    assert downloaded == ["Pascal 5.5.zip"] and not failures


def test_help_plan_does_not_claim_unavailable_edition_providers(monkeypatch):
    def supported(source):
        return ["tp"] if selection.version_selected("tp", "5.5") else []
    monkeypatch.setattr("thelpviewer.server.downloader.service.supported_product_keys", supported)
    rows = plan_help_downloads(["tp"], source_keys=["winworld"], package_ids=["tp:5.0", "tp:5.5"])
    assert [(row["group"], row["sources"]) for row in rows] == [("tp:5.0", []), ("tp:5.5", ["winworld"])]
    assert selection.version_selected("tp", "5.0")  # Request context is restored.


def test_server_download_keeps_help_active_until_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "_verified_sources", lambda *_: True)
    downloads = OnlineDownloader()
    try:
        result = service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
            package_ids=["tp:5.5"], extractor=ExtractorTools("unar", "lsar", None),
            downloads=downloads, finalize=False)
        assert not result.errors
        status = downloads.snapshot(private=True)
        assert status["active"] and status["percent"] == 35
        assert status["items"][0]["state"] == "running"
        assert status["items"][0]["phase"] == "Awaiting conversion"
        downloads.finish("help", error="Conversion failed")
        row = downloads.snapshot(private=True)["items"][0]
        assert row["state"] == "error" and row["percent"] < 100
        assert row["error"] == "Conversion failed"
    finally:
        downloads.close()


def test_consumer_cancellation_is_not_a_failure_of_successfully_verified_sources(tmp_path, monkeypatch):
    from concurrent.futures import CancelledError
    monkeypatch.setattr(service, "_verified_sources", lambda *_: True)
    downloads = OnlineDownloader()
    def stopped(_edition):
        raise CancelledError("HELP conversion stopped")
    try:
        with pytest.raises(CancelledError):
            service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
                package_ids=["tp:5.5"], extractor=ExtractorTools("unar", "lsar", None),
                downloads=downloads, finalize=False, on_ready=stopped)
        row = downloads.snapshot(private=True)["items"][0]
        assert row["state"] == "running" and not row["error"]
        downloads.finish("help", error="Another edition could not be converted", block_unfinished=True)
        row = next(row for row in downloads.snapshot(private=True)["items"] if row["id"] == "help:tp:5.5")
        assert row["state"] == "blocked" and not row["error"]
    finally:
        downloads.close()


@pytest.mark.parametrize("provider", ["archiveorg", "direct", "github"])
def test_help_provider_security_failures_are_not_hidden_as_source_warnings(tmp_path, monkeypatch, provider):
    from thelpviewer.server.downloader import archiveorg, direct, github
    from thelpviewer.server.downloader.errors import DownloadSecurityError
    module = {"archiveorg": archiveorg, "direct": direct, "github": github}[provider]
    query = catalog.SourceQuery("Reference", query="reference", api_url="https://source.test/tree",
        direct_urls=("https://archive.org/details/reference",), archive_members=("HELP.HLP",))
    product = replace(catalog.PRODUCTS["tp"], sources={provider: query})
    monkeypatch.setattr(module, "products_for_source", lambda *_: [product])
    def unsafe(*_args, **_kwargs):
        raise DownloadSecurityError("Private resolved peer")
    if provider != "direct":
        monkeypatch.setattr(module, {"archiveorg": "get_item", "github": "list_repo_files"}[provider], unsafe)
    with pytest.raises(DownloadSecurityError, match="Private resolved peer"):
        module.run(["tp"], tmp_path / "downloads", False, unsafe)


@pytest.mark.parametrize("tool_kind", ["unar", "sevenzip"])
def test_extractor_diagnostics_need_not_be_utf8(tmp_path, tool_kind):
    tool = tmp_path / "archive-tool"
    tool.write_text('#!/bin/sh\nprintf "\\353\\340" >&2\n'
        'if [ "$1" = "-json" ]; then\n'
        '  printf \'{"lsarFormatName":"Zip","lsarContents":[{"name":"\\353"}]}\'\n'
        'elif [ "$1" = "l" ]; then\n'
        '  printf "Type = zip\\n"\n'
        'else\n'
        '  printf "\\353\\340"\n'
        'fi\n')
    tool.chmod(0o755)
    tools = ExtractorTools(str(tool), str(tool), None) if tool_kind == "unar" else ExtractorTools(None, None, str(tool))
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"original archive bytes")
    probe = probe_extractable(archive, tools)
    assert probe and probe.format_name.casefold() == "zip"
    assert extract_file(archive, tmp_path / "extracted", tools)
    assert archive.read_bytes() == b"original archive bytes"


def test_olddos_uses_its_public_http_origin_without_weakening_redirects(monkeypatch):
    from urllib.request import Request
    from thelpviewer.server.downloader.transport import _HTTPSRedirect
    visited = []
    monkeypatch.setattr(olddos, "fetch_olddos", lambda url: visited.append(url) or "")
    pages = olddos.get_file_listing_pages(51)
    assert pages == ["http://old-dos.ru/index.php?page=files&mode=files&do=list&cat=51"]
    assert visited == pages
    with pytest.raises(ValueError, match="HTTPS"):
        _HTTPSRedirect(https_only=False).redirect_request(Request("https://example.test/file"), None,
            302, "Found", {}, "http://example.test/file")


@pytest.fixture
def fallback_sources(tmp_path, monkeypatch):
    payloads = {"5.5": b"verified Pascal 5.5", "6.0": b"verified Pascal 6.0"}
    entries = tuple(HelpDatabaseEntry(crc32=zlib.crc32(data), filenames=("TURBO.TPH",),
        title="Pascal", collection="Pascal " + version, product_key="tp", version=version)
        for version, data in payloads.items())
    monkeypatch.setattr(service, "load_help_manifest", lambda: replace(load_help_manifest(), entries=entries))
    monkeypatch.setattr(collector, "lookup_help_database_entry", lambda path: next(
        (entry for entry in entries if entry.crc32 == zlib.crc32(path.read_bytes())), None))
    monkeypatch.setattr(service, "all_sources", lambda: ["winworld", "archiveorg", "olddos"])
    monkeypatch.setattr(service, "supported_product_keys", lambda source: ["tp"])
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    monkeypatch.setattr(transport, "defer_source", lambda *_args: None)
    return payloads, entries


def test_fallback_is_edition_scoped_crc_verified_and_skips_exhausted_site(tmp_path, monkeypatch, fallback_sources):
    payloads, entries = fallback_sources
    calls, requests, progress = [], [], []
    def limited(url, **_kwargs):
        requests.append(url)
        raise HTTPError(url, 429, "quota", {"Retry-After": "0"}, None)
    monkeypatch.setattr(http, "get_opener", lambda: SimpleNamespace(open=limited))
    def run(source):
        def provider(*, dl_dir, **_kwargs):
            sources_dir = tmp_path / "sources"
            entry = next(entry for entry in entries if selection.source_entry_selected(entry))
            calls.append((source, entry.version))
            if source == "winworld":
                http.download_file("https://limited.test/" + entry.version, dl_dir / (entry.version + ".zip"))
            if source == "olddos":
                pytest.fail("No further provider needed after complete CRC-verified originals")
            extracted = tmp_path / entry.version / "TURBO.TPH"
            extracted.parent.mkdir(parents=True, exist_ok=True)
            extracted.write_bytes(payloads[entry.version])
            return collector.copy_help_files([extracted], sources_dir / "wrong archive label", sources_dir)
        return provider
    monkeypatch.setattr(service.importlib, "import_module", lambda name: SimpleNamespace(
        run=run(next(key for key, module in service.SOURCE_RUNNERS.items() if module == name))))
    downloads = OnlineDownloader()
    try:
        result = service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
            package_ids=["tp:5.5", "tp:6.0"], extractor=ExtractorTools("unar", "lsar", None),
            downloads=downloads, on_progress=progress.append)
        assert sorted(calls) == sorted((source, version) for version in payloads for source in ("winworld", "archiveorg"))
        assert all([source for source, edition in calls if edition == version] == ["winworld", "archiveorg"]
                   for version in payloads)
        assert len(requests) == 3 and len(set(requests)) == 1
        assert len(result.files) == 2 and len(result.warnings) == 2 and not result.errors
        rows = downloads.snapshot(private=True)["items"]
        assert [row["state"] for row in rows] == ["done", "done"]
        assert all(row["total"] == 1 and not row["error"] for row in rows)
        assert any(event["phase"] == "Trying alternative source" for event in progress)
        for entry in entries:
            assert (tmp_path / "sources" / entry.collection / "TURBO.TPH").read_bytes() == payloads[entry.version]
        # Repeated installs may reuse canonical verified originals without any HTTP.
        calls.clear()
        assert not service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
            package_ids=["tp:5.5"], extractor=ExtractorTools("unar", "lsar", None), downloads=downloads).errors
        assert not calls and len(requests) == 3
    finally:
        downloads.close()


def test_provider_failure_after_retaining_complete_originals_is_recoverable(tmp_path, monkeypatch, fallback_sources):
    from thelpviewer.server.downloader.errors import SourceUnavailable
    payloads, entries = fallback_sources
    calls = []
    def provider(**_kwargs):
        sources_dir = tmp_path / "sources"
        calls.append(True)
        target = sources_dir / entries[0].collection
        target.mkdir(parents=True)
        (target / "TURBO.TPH").write_bytes(payloads["5.5"])
        raise SourceUnavailable("Optional source request unavailable")
    monkeypatch.setattr(service.importlib, "import_module", lambda _: SimpleNamespace(run=provider))
    result = service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
        package_ids=["tp:5.5"], extractor=ExtractorTools("unar", "lsar", None))
    assert calls == [True] and not result.errors and len(result.warnings) == 1


@pytest.mark.parametrize("payload", [b"wrong CRC", b"verified Pascal 6.0"])
def test_fallback_does_not_accept_wrong_crc_or_verified_sibling(tmp_path, monkeypatch, fallback_sources, payload):
    _payloads, entries = fallback_sources
    calls = []
    def provider(**_kwargs):
        sources_dir = tmp_path / "sources"
        calls.append(True)
        target = sources_dir / entries[0].collection
        target.mkdir(parents=True, exist_ok=True)
        (target / "TURBO.TPH").write_bytes(payload)
        return [target / "TURBO.TPH"]
    monkeypatch.setattr(service.importlib, "import_module", lambda _: SimpleNamespace(run=provider))
    downloads = OnlineDownloader()
    try:
        result = service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
            package_ids=["tp:5.5"], extractor=ExtractorTools("unar", "lsar", None), downloads=downloads)
        assert len(calls) == 3 and result.errors
        assert downloads.snapshot(private=True)["items"][0]["state"] == "error"
    finally:
        downloads.close()


def test_winworld_exhausted_quota_does_not_try_more_mirrors(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(winworld, "get_download_info", lambda _: ("Pascal 5.5", [
        ("First", "https://limited.test/first"), ("Second", "https://limited.test/second")]))
    def download(_source, *, url):
        calls.append(url)
        raise transport.SourceRateLimited(url)
    with pytest.raises(transport.SourceRateLimited):
        winworld.process_version("5.5", "", "Pascal", tmp_path / "downloads", download,
            False, [], records=[("Pascal.zip", "https://limited.test/page")])
    assert calls == ["https://limited.test/first"]


def test_verified_set_needs_all_components_but_only_one_revision_each(tmp_path, monkeypatch, fallback_sources):
    payloads, entries = fallback_sources
    first = entries[0]
    revision = replace(first, crc32=zlib.crc32(b"another verified revision"))
    second = replace(first, filenames=("SECOND.TPH",), crc32=zlib.crc32(b"second component"))
    manifest = replace(load_help_manifest(), entries=(first, revision, second))
    monkeypatch.setattr(service, "load_help_manifest", lambda: manifest)
    sources = tmp_path / "sources"
    target = sources / first.collection
    target.mkdir(parents=True)
    (target / "turbo.tph").write_bytes(payloads[first.version])
    assert service._verified_sources("tp:5.5", sources) is False
    (target / "SECOND.TPH").write_bytes(b"second component")
    assert service._verified_sources("tp:5.5", sources) is True
    (target / "SECOND.TPH").unlink()
    (target / "SECOND.TPH").symlink_to(target / "turbo.tph")
    assert service._verified_sources("tp:5.5", sources) is False


def test_registered_help_is_not_skipped_as_an_accessory(tmp_path, monkeypatch):
    registered = tmp_path / "UTILS.HLP"
    unknown = tmp_path / "CALC.HLP"
    registered.write_bytes(b"registered QuickBASIC utility reference")
    unknown.write_bytes(b"unregistered accessory")
    monkeypatch.setattr(collector, "lookup_help_database_entry", lambda path: object() if path == registered else None)
    assert collector.collect_help_files(tmp_path) == [registered]


def test_exact_edition_queries_and_providers_precede_family_discovery():
    with selection.select_help_packages(["tasm:3.1"]):
        jobs = catalog.products_for_source("archiveorg", ["tasm"])
        assert jobs[0].sources["archiveorg"].archive_members == ("TASM.TAH",)
        assert jobs[-1].sources["archiveorg"].archive_members == ()
    row = plan_help_downloads(["tasm"], package_ids=["tasm:3.1"])[0]
    assert row["sources"][0] == "archiveorg"


def test_server_deduplicates_failed_source_plans_and_rechecks_crc_after_each_input(tmp_path, monkeypatch, fallback_sources):
    from thelpviewer.server.converter.ingest import HelpInput
    payloads, entries = fallback_sources
    calls = []
    bad = HelpInput(tmp_path / "bad.zip", "Pascal")
    good = replace(bad, path=tmp_path / "good.zip")
    def process(plan, **_kwargs):
        calls.append(plan.path.name)
        if plan == bad:
            raise ValueError("Invalid input")
        dest = tmp_path / "sources" / entries[0].collection / "TURBO.TPH"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(payloads["5.5"])
        return [dest]
    monkeypatch.setattr(service, "process_help_input", process)
    def provider(*, process, complete, **_kwargs):
        with pytest.raises(ValueError, match="Invalid input"):
            process(bad, url="https://test/bad.zip")
        assert process(bad, url="https://test/bad.zip") == []
        assert not complete()
        result = process(good, url="https://test/good.zip")
        assert complete()
        assert process(replace(good, path=tmp_path / "unneeded.zip"), url="https://test/unneeded.zip") == []
        return result
    monkeypatch.setattr(service.importlib, "import_module", lambda _: SimpleNamespace(run=provider))
    result = service.download_products(["tp"], tmp_path / "sources", tmp_path / "downloads",
        source_keys=["archiveorg"], package_ids=["tp:5.5"], extractor=ExtractorTools("unar", "lsar", None))
    assert calls == ["bad.zip", "good.zip"] and len(result.files) == 1 and not result.errors


def test_olddos_download_endpoints_get_distinct_readable_archive_names(tmp_path, monkeypatch):
    product = replace(catalog.PRODUCTS["tasm"], sources={"olddos": catalog.SourceQuery("Assembler", keywords=("assembler",))})
    monkeypatch.setattr(olddos, "products_for_source", lambda *_: [product])
    monkeypatch.setattr(olddos, "_load_category_entries", lambda _: {})
    monkeypatch.setattr(olddos, "_entries_for_product", lambda *_: [
        {"id": str(number), "name": f"Assembler {number}", "url": f"http://old-dos.ru/show?id={number}"}
        for number in (1, 2)])
    monkeypatch.setattr(olddos, "get_download_url", lambda url: url.replace("show", "dl.php"))
    plans = []
    olddos.run(["tasm"], tmp_path / "downloads", False, lambda source, **_kw: plans.append(source) or [])
    assert [plan.path.name for plan in plans] == ["od_Assembler 1 1.archive", "od_Assembler 2 2.archive"]


def test_assembler_crc_editions_do_not_share_an_original_path():
    manifest = load_help_manifest()
    old = manifest.entry_map[0x07E89446]
    current = manifest.entry_map[0x9AC3E64A]
    assert old.collection != current.collection
    assert current.collection == "Borland Turbo Assembler"


@pytest.mark.parametrize("provider", ["archiveorg", "github"])
@pytest.mark.parametrize("version", ["5.5", "6.0"])
def test_loose_help_uses_crc_collector_and_retains_cache(tmp_path, monkeypatch, fallback_sources, provider, version):
    from thelpviewer.server.downloader import archiveorg, github

    payloads, entries = fallback_sources
    def download(_url, dest, *, process=None, **_options):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payloads[version])
        return process(dest)
    module = archiveorg if provider == "archiveorg" else github
    monkeypatch.setattr(service, "download_file", download)
    from tests.help_downloads import help_processor
    process = help_processor(tmp_path / "sources", ExtractorTools(None, None, None))
    sources, cache = tmp_path / "sources", tmp_path / "downloads"
    with selection.select_help_packages(["tp:5.5"]):
        if provider == "archiveorg":
            monkeypatch.setattr(archiveorg, "get_item_files", lambda _: [{"name": "TURBO.TPH", "size": 20}])
            product = catalog.PRODUCTS["tp"]
            result = archiveorg.process_item({"identifier": "pascal55", "title": "Pascal 5.5"}, product,
                product.sources["archiveorg"], cache, process, False, [])
        else:
            monkeypatch.setattr(github, "list_repo_files", lambda _: [
                {"name": "TURBO.TPH", "download_url": "https://github.test/TURBO.TPH"}])
            product = replace(catalog.PRODUCTS["tp"], sources={"github": catalog.SourceQuery("Pascal", api_url="https://github.test/tree")})
            monkeypatch.setattr(github, "products_for_source", lambda *_: [product])
            result = github.run(["tp"], cache, False, process)
    expected = sources / entries[0].collection / "TURBO.TPH"
    assert result == ([expected] if version == "5.5" else [])
    assert [path for path in sources.rglob("*") if path.is_file()] == result
    cached = list(cache.rglob("TURBO.TPH"))
    assert len(cached) == 1 and cached[0].read_bytes() == payloads[version]
