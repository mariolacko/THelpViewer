import json
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the browser asset regression test")
def test_external_help_links_prefer_the_current_product_collection():
    asset_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    assert asset_paths[0].read_bytes() == asset_paths[1].read_bytes()

    script = r'''
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function normalizeSourceFileName(value)");
const end = source.indexOf("function bundleLoadingLabel(value", start);
if (start < 0 || end < 0) { throw new Error("catalog resolver source not found"); }
let catalogData = [
    { group: "Microsoft CodeView 4.0", file: "Microsoft CodeView 4.0/cv.json.gz", source_file: "CV.HLP" },
    { group: "Microsoft QuickBASIC Extended 7.1", file: "Microsoft QuickBASIC Extended 7.1/bc.json.gz", source_file: "BC.HLP", product: "basic-pds", version: "7.1" },
    { group: "Microsoft QuickBASIC Extended 7.1", file: "Microsoft QuickBASIC Extended 7.1/cv.json.gz", source_file: "CV.HLP", product: "basic-pds", version: "7.1" },
    { group: "Microsoft QuickC, C, and C++ 6.0", file: "Microsoft QuickC, C, and C++ 6.0/cv.json.gz", source_file: "CV.HLP", product: "msc", version: "6.0" },
];
eval(source.slice(start, end));
const preferred = { _catalogFile: "Microsoft QuickBASIC Extended 7.1/bc.json.gz" };
const resolved = findCatalogEntryBySourceFile("cv.hlp", preferred);
const missing = findCatalogEntryBySourceFile("NMAKE.HLP", preferred);
process.stdout.write(JSON.stringify({ resolved: resolved && resolved.file, missing }));
'''
    result = subprocess.run(
        [NODE, "-e", script, str(asset_paths[0])],
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = json.loads(result.stdout)

    assert resolved["resolved"] == "Microsoft QuickBASIC Extended 7.1/cv.json.gz"
    assert resolved["missing"] is None
