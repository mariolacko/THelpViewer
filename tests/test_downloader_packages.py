"""HELP and DOS download modules publish complete cache files atomically."""

import hashlib
import io
import zipfile
from urllib.error import HTTPError

import pytest

from thelpviewer.server.downloader import packages
from thelpviewer.server.downloader.cache import download_cached
from thelpviewer.server.file_storage import atomic_file


def test_package_download_reuses_verified_cache_and_reports_progress(tmp_path, monkeypatch):
    contents = b"archive"
    source = {"id": "game", "url": "https://games.test/game.zip", "sha256": hashlib.sha256(contents).hexdigest()}
    calls = []
    def fetch(source, limit, progress):
        calls.append(source["id"])
        if progress:
            progress(len(contents), len(contents))
        return contents
    monkeypatch.setattr(packages, "fetch_source", fetch)
    progress = []
    result, key = packages.download_package(source, tmp_path, 100, on_progress=lambda *v: progress.append(v))
    assert result == contents and progress == [(7, 7)]
    assert packages.download_package(source, tmp_path, 100)[0] == contents and calls == ["game"]
    cached = tmp_path / packages.package_cache_path(source)
    assert cached.relative_to(tmp_path).as_posix() == "game/game.zip"
    cached.write_bytes(b"corrupt")
    assert packages.download_package(source, tmp_path, 100)[0] == contents
    assert calls == ["game", "game"]  # Invalid metadata/body never reuses corrupt bytes.


def test_atomic_cache_failure_preserves_old_file_and_removes_only_its_temporary_file(tmp_path):
    destination = tmp_path / "archive"
    destination.write_bytes(b"old")
    with pytest.raises(OSError, match="interrupted"):
        with atomic_file(destination) as stream:
            stream.write(b"partial")
            raise OSError("interrupted")
    assert destination.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["archive"]
    destination.unlink()
    destination.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="symbolic"):
        with atomic_file(destination):
            pass


def test_shared_cache_processes_before_publication_and_revalidates_cached_bytes(tmp_path):
    destination = tmp_path / "archive.zip"
    events = []
    def fetch(path):
        events.append("fetch")
        assert path != destination and not destination.exists()
        path.write_bytes(b"archive")
    def process(path):
        events.append("validate")
        assert path.read_bytes() == b"archive"
        return "validated"
    assert download_cached(destination, 100, fetch, process=process) == "validated"
    assert download_cached(destination, 100, fetch, process=process) == "validated"
    assert events == ["fetch", "validate", "validate"]
    assert list(tmp_path.iterdir()) == [destination]
    def fail(path):
        raise ValueError("Invalid payload")
    with pytest.raises(ValueError, match="Invalid payload"):
        download_cached(destination, 100, fetch, process=fail)
    assert destination.read_bytes() == b"archive"
    destination.unlink()
    with pytest.raises(ValueError, match="Invalid payload"):
        download_cached(destination, 100, fetch, process=fail)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", [404, 429, "invalid archive"])
def test_package_alternatives_use_their_own_recipe_and_validate_before_cache(tmp_path, monkeypatch, failure):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("NC.EXE", b"MZ verified program")
    source = {"id": "norton", "title": "Norton Commander 4.0", "url": "https://first.test/nc.7z",
        "format": "archive", "image_member": "disk1.img", "alternatives": [
            {"url": "https://second.test/nc.zip", "format": "zip"}]}
    calls, recipes, phases = [], [], []
    def fetch(recipe, *_args, **_kwargs):
        calls.append(recipe["url"])
        if "first.test" in recipe["url"]:
            if isinstance(failure, int):
                raise HTTPError(recipe["url"], failure, "source unavailable", {}, None)
            return b"not an archive"
        return payload.getvalue()
    def process(data, recipe):
        recipes.append(recipe)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return {name: archive.read(name) for name in archive.namelist()}
    monkeypatch.setattr(packages, "fetch_source", fetch)
    files, key = packages.download_package(source, tmp_path, 10000, process=process, on_status=phases.append)
    assert files == {"NC.EXE": b"MZ verified program"}
    assert calls == [source["url"], source["alternatives"][0]["url"]]
    assert recipes[-1]["format"] == "zip" and "image_member" not in recipes[-1]
    assert recipes[-1]["id"] == "norton"
    assert phases == ["Trying alternative source 2/2"]
    cached = tmp_path / packages.package_cache_path(recipes[-1])
    assert cached.read_bytes() == payload.getvalue()
    assert sorted(path.name for path in cached.parent.iterdir()) == ["nc.zip", "nc.zip.source.json"]
    assert key == packages.package_cache_key(recipes[-1])


def test_failed_alternatives_preserve_old_cache_and_report_all_sources(tmp_path, monkeypatch):
    existing = tmp_path / "unrelated"
    existing.write_bytes(b"keep")
    source = {"id": "app", "url": "https://first.test/app.zip", "alternatives": [
        {"url": "https://second.test/app.zip"}]}
    def fail(recipe, *_args, **_kwargs):
        raise HTTPError(recipe["url"], 429, "quota", {}, None)
    monkeypatch.setattr(packages, "fetch_source", fail)
    with pytest.raises(ValueError, match="All sources failed.*first.test.*second.test"):
        packages.download_package(source, tmp_path, 100)
    assert list(tmp_path.iterdir()) == [existing] and existing.read_bytes() == b"keep"


@pytest.mark.parametrize("alternative", [{"url": "https://other.test/app.zip", "id": "another"},
    {"url": "https://other.test/app.zip", "language": "de"}, {"url": "https://127.0.0.1/app.zip"},
    {"url": "http://other.test/app.zip"}, {"url": "https://user:password@other.test/app.zip"}])
def test_invalid_alternatives_are_rejected_before_any_request(tmp_path, monkeypatch, alternative):
    monkeypatch.setattr(packages, "fetch_source", lambda *_a, **_kw: pytest.fail("Invalid source reached network"))
    with pytest.raises(ValueError):
        packages.download_package({"id": "app", "url": "https://first.test/app.zip",
            "alternatives": [alternative]}, tmp_path, 100)
    assert not list(tmp_path.iterdir())


def test_real_transport_skips_rate_limited_mirror_and_uses_an_independent_site(tmp_path, monkeypatch):
    from thelpviewer.server.downloader import transport

    calls = []
    class Response(io.BytesIO):
        headers = {}
    class Opener:
        def open(self, request, **_kwargs):
            calls.append(request.full_url)
            if "quota.test" in request.full_url:
                raise HTTPError(request.full_url, 429, "quota", {"Retry-After": "0"}, None)
            return Response(b"downloaded")
    monkeypatch.setattr(transport, "create_opener", lambda: Opener())
    source = {"id": "app", "url": "https://quota.test/primary", "alternatives": [
        {"url": "https://mirror.quota.test/another"}, {"url": "https://independent.test/app"}]}
    data, _key = packages.download_package(source, tmp_path, 100)
    assert data == b"downloaded"
    assert calls == ["https://quota.test/primary"] * 3 + ["https://independent.test/app"]


@pytest.mark.parametrize("failure", ["form", "incomplete"])
def test_missing_form_and_incomplete_response_try_another_source(tmp_path, monkeypatch, failure):
    from thelpviewer.server.downloader import transport
    calls = []
    class Response(io.BytesIO):
        headers = {}
    class Opener:
        def open(self, request, **_kwargs):
            calls.append(request.full_url)
            response = Response(b"no form" if "first.test" in request.full_url else b"valid payload")
            if failure == "incomplete" and "first.test" in request.full_url:
                response.headers = {"Content-Length": "500"}
            return response
    monkeypatch.setattr(transport, "create_opener", lambda: Opener())
    source = {"id": "app", "url": "https://first.test/app", "alternatives": [
        {"url": "https://second.test/app"}]}
    if failure == "form":
        source["download_forms"] = ["form.download"]
    data, key = packages.download_package(source, tmp_path, 1000)
    assert data == b"valid payload" and calls == [source["url"], source["alternatives"][0]["url"]]
    cached = tmp_path / packages.package_cache_path({"id": "app", **source["alternatives"][0]})
    assert cached.read_bytes() == b"valid payload"


def test_security_failure_from_processing_never_tries_an_alternative(tmp_path, monkeypatch):
    from thelpviewer.server.downloader.errors import DownloadSecurityError
    calls = []
    def fetch(source, *_args, **_kwargs):
        calls.append(source["url"])
        return b"archive"
    def process(_data, _recipe):
        raise DownloadSecurityError("Unsafe redirected peer")
    monkeypatch.setattr(packages, "fetch_source", fetch)
    with pytest.raises(DownloadSecurityError):
        packages.download_package({"id": "app", "url": "https://first.test/app", "alternatives": [
            {"url": "https://second.test/app"}]}, tmp_path, 100, process=process)
    assert calls == ["https://first.test/app"] and not list(tmp_path.iterdir())
