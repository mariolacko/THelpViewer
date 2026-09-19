import json
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the browser asset regression test")
def test_markdown_links_escape_attributes_and_reject_script_schemes():
    asset_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    assert asset_paths[0].read_bytes() == asset_paths[1].read_bytes()

    script = r"""
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function renderMarkdown(md)");
const marker = "\n// ── Menu bar for bundle page";
const end = source.indexOf(marker, start);
if (start < 0 || end < 0) { throw new Error("renderMarkdown source not found"); }
eval(source.slice(start, end));
const injected = renderMarkdown(`[x](\" onmouseover=\"location='//evil.test')`);
const scripted = renderMarkdown(`[x](javascript:alert(1))`);
process.stdout.write(JSON.stringify({ injected, scripted }));
"""
    result = subprocess.run(
        [NODE, "-e", script, str(asset_paths[0])],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)

    assert ' onmouseover="' not in rendered["injected"]
    assert "&quot;" in rendered["injected"]
    assert "javascript:" not in rendered["scripted"]
