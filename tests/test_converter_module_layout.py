"""Fresh-process reader imports and manifest dispatch after module moves."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_winhelp_reader import single_article
from thelpviewer.help_database import load_help_manifest
from thelpviewer.server.converter.exporter import _resolve_dotted_path


@pytest.mark.parametrize("module", [
    "readers.software602_graphics", "readers.tvision_help", "readers.source_containers",
    "readers.winhelp_binary", "readers.winhelp_text", "readers.hlx_binary",
    "writers.bundle_extensions",
])
def test_reader_helpers_import_fresh_and_load_registered_windows_help(tmp_path, module):
    source = tmp_path / "REFERENCE.HLP"
    source.write_bytes(single_article([(b"Reference text", b"\xff")]))
    script = """
import importlib
import sys
importlib.import_module('thelpviewer.server.converter.' + sys.argv[1])
from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.writers.bundle_extensions import (
    discover_bundle_source_groups, document_bundle_variants,
)
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
document = load_document(sys.argv[2])
assert document.format_name == 'winhelp'
assert document.topics[0].uhf_content == ['Reference text']
assert HelpJsonRenderer(document).render_document()['topics']['0']['content'] == ['Reference text']
assert discover_bundle_source_groups([]) == []
assert document_bundle_variants(document) == []
assert 'thelpviewer.server.app' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script, module, str(source)],
        cwd=Path(__file__).resolve().parents[1], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_all_manifest_converter_targets_resolve_after_moves():
    for converter in load_help_manifest().converters:
        for field in ("reader", "loader", "matcher", "reject_matcher", "detector"):
            target = getattr(converter, field)
            if target:
                assert callable(_resolve_dotted_path(target)), (converter.name, field, target)
