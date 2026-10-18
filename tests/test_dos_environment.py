"""Manifest-defined DOS PATH entries and preservation of unrelated AUTOEXEC lines."""

import json

import pytest

from thelpviewer.server.dos.config import load_dos_config
from thelpviewer.server.dos.environment import autoexec_with_path
from thelpviewer.server.dos.paths import DosError
from test_dos_package_recipes import zipped
from test_dos_prompt import payload, store_at


@pytest.mark.parametrize("value", ["", None, [], "../OUTSIDE", "C:\\TOOLS", "A;B", "TOOLS\nECHO BAD"])
def test_package_path_requires_a_relative_c_directory(tmp_path, value):
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [{"id": "tool", "path": value}]}))
    with pytest.raises(DosError, match="Invalid C drive path"):
        load_dos_config(manifest)


@pytest.mark.parametrize("current", [
    b"@ECHO OFF\nset path=OLD;Z:\\\nREM keep me\nVC\n",
    b'@ECHO OFF\r\nSET "PATH=OLD"\r\nREM keep me\r\nVC\r\n',
    b"@ECHO OFF\r\nREM keep me\r\nVC\r\n",
])
def test_managed_path_is_inserted_before_launch_and_preserves_other_lines(current):
    configured = b"SET PATH=C:\\MANUAL;Z:\\\r\n"
    expected = b"@ECHO OFF\r\nSET PATH=C:\\COMPRESS;C:\\MANUAL;Z:\\\r\nREM keep me\r\nVC\r\n"
    assert autoexec_with_path(current, configured, ["COMPRESS", "COMPRESS"]) == expected
    assert autoexec_with_path(expected, configured, ["COMPRESS"]) == expected


def test_installs_and_uninstalls_manage_only_the_shared_path_line(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    config = json.loads(store.config_path.read_text())
    config["files"].append({"path": "AUTOEXEC.BAT", "text": ["@ECHO OFF", "SET PATH=C:\\MANUAL;Z:\\", "ECHO boot"]})
    config["sources"] = [
        {"id": "one", "format": "zip", "target": "COMPRESS", "path": "compress", "url": "https://tools.test/one.zip"},
        {"id": "two", "format": "zip", "target": "COMPRESS", "path": "COMPRESS", "url": "https://tools.test/two.zip"},
        {"id": "other", "format": "zip", "target": "TOOLS/OTHER", "path": "tools/other", "url": "https://tools.test/other.zip"},
    ]
    store.config_path.write_text(json.dumps(config))
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source",
        lambda source, *_a, **_kw: zipped({source["id"].upper() + ".EXE": source["id"].encode()}))
    try:
        store.configure(["one", "two", "other"])
        expected = b"@ECHO OFF\r\nSET PATH=C:\\COMPRESS;C:\\TOOLS\\OTHER;C:\\MANUAL;Z:\\\r\nECHO boot\r\n"
        assert store.files["AUTOEXEC.BAT"] == expected
        account = "a" * 32
        store.save(account, payload(store, files={"AUTOEXEC.BAT": b"private boot"}))
        (store.disk_dir / "AUTOEXEC.BAT").write_bytes(expected + b"REM manual boot line\r\n")
        store.configure(["two"])
        assert store.files["AUTOEXEC.BAT"] == b"@ECHO OFF\r\nSET PATH=C:\\COMPRESS;C:\\MANUAL;Z:\\\r\nECHO boot\r\nREM manual boot line\r\n"
        store.configure([])
        assert b"SET PATH=C:\\MANUAL;Z:\\\r\n" in store.files["AUTOEXEC.BAT"]
        assert b"COMPRESS" not in store.files["AUTOEXEC.BAT"]
        assert store.overlay(account)[1]["AUTOEXEC.BAT"] == b"private boot"
    finally:
        store.downloads.close()


def test_failed_publication_restores_previous_path(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    config = json.loads(store.config_path.read_text())
    config["sources"] = [{"id": "tool", "format": "zip", "target": "COMPRESS", "path": "COMPRESS", "url": "https://tools.test/tool.zip"}]
    store.config_path.write_text(json.dumps(config))
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", lambda *_a, **_kw: zipped({"TOOL.EXE": b"tool"}))
    try:
        store.configure(["tool"])
        before = store.files["AUTOEXEC.BAT"]
        write = __import__("thelpviewer.server.dos.store", fromlist=["atomic_file"]).atomic_file
        def fail(path, contents):
            if path == store._published_receipt:
                raise OSError("publication failed")
            return write(path, contents)
        monkeypatch.setattr("thelpviewer.server.dos.store.atomic_file", fail)
        with pytest.raises(DosError, match="publication failed"):
            store.configure([])
        assert (store.disk_dir / "AUTOEXEC.BAT").read_bytes() == before
        assert store.files["AUTOEXEC.BAT"] == before
    finally:
        store.downloads.close()
