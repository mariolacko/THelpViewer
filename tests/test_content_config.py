"""Shared source validation and atomic settings publication protect live content."""

import json
import re

import pytest

from thelpviewer.server.content_config import read_source_manifest
from thelpviewer.server.dos.config import load_dos_config
from thelpviewer.server.midi.sources import configured_sources
from thelpviewer.server.json_storage import write_json


@pytest.mark.parametrize("data", [[], {}, {"sources": None}, {"sources": [None]},
    {"sources": [{"id": "../escape"}]}, {"sources": [{"id": 3}]},
    {"sources": [{"id": "same", "name": "One"}, {"id": "same", "name": "Two"}]}])
def test_dos_and_midi_use_the_same_structural_source_validation(tmp_path, data):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(data))
    for loader in (load_dos_config, configured_sources):
        with pytest.raises(ValueError):
            loader(path)


def test_source_manifest_preserves_domain_metadata_and_empty_selection(tmp_path):
    path = tmp_path / "sources.json"
    data = {"sources": [{"id": "one", "name": "First", "enabled": False,
                          "files": [{"path": "TEST.TXT", "text": ["Original"]}]}], "memory_mb": 16}
    path.write_text(json.dumps(data))
    assert read_source_manifest(path, "Test", re.compile(r"[a-z]+")) == data
    assert configured_sources(path) == data["sources"]
    assert load_dos_config(path)["sources"] == data["sources"]
    assert load_dos_config(None)["sources"] == [] and configured_sources(None) == []
    assert json.loads(path.read_text()) == data


@pytest.mark.parametrize("language", [None, [], "Czech", "en-gb", "en<script>"])
def test_dos_language_metadata_is_validated_before_installation(tmp_path, language):
    path = tmp_path / "dos.json"
    path.write_text(json.dumps({"sources": [{"id": "test", "language": language}]}))
    with pytest.raises(ValueError, match="language"):
        load_dos_config(path)


@pytest.mark.parametrize("required", [None, 0, 1, "true", []])
def test_dos_required_metadata_is_a_boolean(tmp_path, required):
    path = tmp_path / "dos.json"
    path.write_text(json.dumps({"sources": [{"id": "test", "required": required}]}))
    with pytest.raises(ValueError, match="required must be a boolean"):
        load_dos_config(path)


def test_failed_json_replacement_keeps_settings_and_cleans_temporary_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    write_json(path, {"sources": ["one"], "name": "Žofia"})
    original = path.read_bytes()
    def fail(*_args):
        raise OSError("disk unavailable")
    monkeypatch.setattr("thelpviewer.server.json_storage.os.replace", fail)
    with pytest.raises(OSError, match="disk unavailable"):
        write_json(path, {"sources": []})
    assert path.read_bytes() == original and list(tmp_path.iterdir()) == [path]


def test_invalid_json_value_and_symlink_do_not_replace_live_settings(tmp_path):
    path = tmp_path / "settings.json"
    write_json(path, {"sources": ["one"]})
    original = path.read_bytes()
    for value in ({"bad": object()}, {"bad": float("nan")}):
        with pytest.raises((TypeError, ValueError)):
            write_json(path, value)
        assert path.read_bytes() == original and list(tmp_path.iterdir()) == [path]
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="symbolic links"):
        write_json(alias, {"sources": []})
    assert path.read_bytes() == original and alias.is_symlink()
