"""HELP and DOS download modules publish complete cache files atomically."""

import hashlib

import pytest

from thelpviewer.server.downloader import packages
from thelpviewer.server.downloader.cache import atomic_download


def test_package_download_reuses_verified_cache_and_reports_progress(tmp_path, monkeypatch):
    contents = b"archive"
    source = {"id": "game", "url": "https://games.test/game.zip", "sha256": hashlib.sha256(contents).hexdigest()}
    calls = []
    def fetch(source, limit, progress):
        calls.append(source["id"])
        progress(len(contents), len(contents))
        return contents
    monkeypatch.setattr(packages, "fetch_source", fetch)
    progress = []
    result, key = packages.download_package(source, tmp_path, 100, on_progress=lambda *v: progress.append(v))
    assert result == contents and progress == [(7, 7)]
    assert packages.download_package(source, tmp_path, 100)[0] == contents and calls == ["game"]
    (tmp_path / key).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        packages.download_package(source, tmp_path, 100)


def test_atomic_cache_failure_preserves_old_file_and_removes_only_its_temporary_file(tmp_path):
    destination = tmp_path / "archive"
    destination.write_bytes(b"old")
    with pytest.raises(OSError, match="interrupted"):
        with atomic_download(destination) as stream:
            stream.write(b"partial")
            raise OSError("interrupted")
    assert destination.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["archive"]
    destination.unlink()
    destination.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="symbolic"):
        with atomic_download(destination):
            pass
