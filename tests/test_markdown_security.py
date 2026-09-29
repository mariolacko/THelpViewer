import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CSS_PATHS = (
    Path("www/assets/turbovision.css"),
    Path("thelpviewer/converter/assets/turbovision.css"),
)


def test_document_tables_keep_readable_columns_and_use_window_scrolling():
    assert CSS_PATHS[0].read_bytes() == CSS_PATHS[1].read_bytes()
    css = CSS_PATHS[0].read_text(encoding="utf-8")
    table_rule = re.search(r"\.tv-doc-document table \{(.*?)\n\}", css, re.DOTALL)
    assert table_rule is not None
    declarations = table_rule.group(1)

    assert "width: max-content;" in declarations
    assert "min-width: 100%;" in declarations
    assert "table-layout: auto;" in declarations
    assert "overflow-wrap: normal;" in declarations
    assert "word-break: normal;" in declarations


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


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the browser asset regression test")
def test_markdown_tables_keep_escaped_and_inline_code_pipes_in_one_cell():
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
const escaped = renderMarkdown(String.raw`| A | B |
| --- | --- |
| x \| y | z |`);
const inlineCode = renderMarkdown(`| A | B |
| --- | --- |
| \`x | y\` | z |`);
process.stdout.write(JSON.stringify({ escaped, inlineCode }));
"""
    result = subprocess.run(
        [NODE, "-e", script, str(asset_paths[0])],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)

    assert rendered["escaped"].count("<td>") == 2
    assert "<td>x | y</td>" in rendered["escaped"]
    assert rendered["inlineCode"].count("<td>") == 2
    assert "<td><code>x | y</code></td>" in rendered["inlineCode"]


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the browser asset regression test")
def test_markdown_soft_wrapped_lines_form_one_paragraph_and_keep_links():
    asset_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    assert asset_paths[0].read_bytes() == asset_paths[1].read_bytes()

    script = r"""
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function renderMarkdown(md)");
const end = source.indexOf("\n// ── Menu bar for bundle page", start);
eval(source.slice(start, end));
const soft = renderMarkdown("First source line\ncontinues here.\n\nNext paragraph.");
const link = renderMarkdown("[HelpPC format\nreference](https://example.test/help)");
const hard = renderMarkdown("First line  \nsecond line");
process.stdout.write(JSON.stringify({ soft, link, hard }));
"""
    result = subprocess.run(
        [NODE, "-e", script, str(asset_paths[0])],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = json.loads(result.stdout)

    assert rendered["soft"].startswith("<p>First source line\ncontinues here.</p>")
    assert "<p>Next paragraph.</p>" in rendered["soft"]
    assert '<a href="https://example.test/help"' in rendered["link"]
    assert "First line<br>second line" in rendered["hard"]
