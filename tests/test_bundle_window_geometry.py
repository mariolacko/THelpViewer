import json
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the browser asset regression test")
def test_bundle_window_keeps_explicit_height_as_its_minimum():
    asset_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    assert asset_paths[0].read_bytes() == asset_paths[1].read_bytes()

    script = r"""
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function bundleWindowSpec(bundle)");
const end = source.indexOf("function bundleUsesFixedTopicLayout(bundle)", start);
if (start < 0 || end < 0) { throw new Error("bundleWindowSpec source not found"); }
function bundleDisplayLayout(bundle) { return bundle.metadata.display; }
eval(source.slice(start, end));
const spec = bundleWindowSpec({ metadata: { display: { cols: 80, rows: 25 } } });
process.stdout.write(JSON.stringify(spec));
"""
    result = subprocess.run(
        [NODE, "-e", script, str(asset_paths[0])],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "cols": 84,
        "rows": 29,
        "min_cols": 84,
        "min_rows": 29,
    }
