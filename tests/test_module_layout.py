"""Configuration and relocated server modules retain their runtime behavior."""

import importlib

from thelpviewer import __version__
from thelpviewer.config import CONFIG_DIR, PROJECT_ROOT
from thelpviewer.help_database import help_database_path, load_help_manifest
from thelpviewer.server.config import load_config
from thelpviewer.server.converter.writers.bundle import _write_bundle_index
from thelpviewer.server.downloader.__main__ import _build_parser


def test_checked_in_viewer_version_matches_the_package():
    html = (PROJECT_ROOT / "www/index.html").read_text(encoding="utf-8")
    assert f'data-tv-generator-version="{__version__}"' in html
    assert f'content="THelp Viewer Converter {__version__}"' in html


def test_default_configuration_is_grouped_and_explicit_overrides_still_work(tmp_path, monkeypatch):
    for name in ("THELP_HELP_DATABASE_PATH", "THELP_DOS_CONFIG_PATH", "THELP_MIDI_SOURCES_PATH"):
        monkeypatch.delenv(name, raising=False)
    config = load_config()
    assert config.dos_config_path == CONFIG_DIR / "dos-prompt.json"
    assert config.midi_sources_path == CONFIG_DIR / "midi-sources.json"
    assert help_database_path() == CONFIG_DIR / "help-database.json"
    for path in (config.dos_config_path, config.midi_sources_path, help_database_path()):
        assert path.is_file()
    monkeypatch.setenv("THELP_HELP_DATABASE_PATH", str(tmp_path / "help.json"))
    monkeypatch.setenv("THELP_DOS_CONFIG_PATH", str(tmp_path / "dos.json"))
    monkeypatch.setenv("THELP_MIDI_SOURCES_PATH", str(tmp_path / "midi.json"))
    config = load_config()
    assert help_database_path() == tmp_path / "help.json"
    assert config.dos_config_path == tmp_path / "dos.json"
    assert config.midi_sources_path == tmp_path / "midi.json"


def test_manifest_providers_and_all_converter_symbols_resolve_in_server_modules():
    manifest = load_help_manifest(CONFIG_DIR / "help-database.json")
    assert manifest.sources and manifest.converters
    for source in manifest.sources:
        assert source.runner.startswith("thelpviewer.server.downloader.")
        assert callable(importlib.import_module(source.runner).run)
    for converter in manifest.converters:
        for symbol in (converter.reader, converter.loader, converter.matcher,
                       converter.reject_matcher, converter.detector):
            if not symbol:
                continue
            module, attribute = symbol.split(":", 1)
            assert module.startswith("thelpviewer.server.converter.")
            assert callable(getattr(importlib.import_module(module), attribute))


def test_downloader_defaults_and_exported_site_image_use_project_root(tmp_path, monkeypatch):
    for name in ("THELP_DATA_DIR", "THELP_STATE_DIR", "THELP_SOURCES_DIR", "THELP_DOWNLOADS_DIR"):
        monkeypatch.delenv(name, raising=False)
    args = _build_parser(PROJECT_ROOT).parse_args([])
    assert load_config().sources_dir == PROJECT_ROOT / "var" / "sources"
    assert args.out_dir == str(PROJECT_ROOT / "var" / "sources")
    assert args.dl_dir == str(PROJECT_ROOT / "var" / "downloads" / "help")
    _write_bundle_index(tmp_path)
    assert (tmp_path / "assets" / "Thelp.png").read_bytes() == (PROJECT_ROOT / "Thelp.png").read_bytes()
    assert (tmp_path / "assets" / "tv-bundle-app.js").is_file()
    assert (tmp_path / "index.html").is_file()


def test_sources_default_to_state_not_permanent_data_and_support_explicit_override(tmp_path, monkeypatch):
    monkeypatch.delenv("THELP_SOURCES_DIR", raising=False)
    monkeypatch.setenv("THELP_STATE_DIR", str(tmp_path / "work"))
    monkeypatch.setenv("THELP_DATA_DIR", str(tmp_path / "permanent"))
    assert load_config().sources_dir == tmp_path / "work" / "sources"
    assert _build_parser(PROJECT_ROOT).parse_args([]).out_dir == str(tmp_path / "work" / "sources")
    monkeypatch.setenv("THELP_SOURCES_DIR", str(tmp_path / "inputs"))
    assert load_config().sources_dir == tmp_path / "inputs"
    assert _build_parser(PROJECT_ROOT).parse_args([]).out_dir == str(tmp_path / "inputs")
