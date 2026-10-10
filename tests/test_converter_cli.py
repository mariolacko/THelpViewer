import sys

import pytest

from thelpviewer.server.converter import __main__ as converter_cli
from thelpviewer.server.converter.writers.bundle import BundleResult


def test_bundle_cli_exits_unsuccessfully_when_export_reports_error(tmp_path, monkeypatch):
    source = tmp_path / "broken.hlp"
    source.write_bytes(b"broken")
    result = BundleResult(
        input_path=source,
        json_path=tmp_path / "output" / "broken.json.gz",
        format_name="ERROR",
        topic_count=0,
        display_name="broken",
        source_files=(source.name,),
    )
    monkeypatch.setattr(converter_cli, "export_bundle", lambda *_args, **_kwargs: result)
    monkeypatch.setattr(converter_cli, "load_help_database", lambda: object())
    monkeypatch.setattr(converter_cli, "lookup_help_database_entry", lambda *_args: None)
    monkeypatch.setattr(sys, "argv", ["converter", "--bundle", str(source), str(tmp_path / "output")])

    with pytest.raises(SystemExit) as exc_info:
        converter_cli.main()

    assert exc_info.value.code == 1
