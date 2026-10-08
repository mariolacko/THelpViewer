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


@pytest.mark.skipif(NODE is None, reason="Node.js is required for public HELP link tests")
def test_public_help_links_resolve_topics_aliases_and_original_source_files():
    script = r'''
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
function section(start, end) {
    return source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
}
global.window = { location: { pathname: '/' } };
const CONTEXT_HELP_BUNDLE_FILE = '../assets/tv-context-help.json';
const bundleCache = new Map();
const file = 'Borland C++ 3.0/tchelp.json.gz';
let catalogData = [
    { file, group: 'Borland C++ 3.0', source_file: 'TCHELP.TCH' },
    { file: 'Other/asm.json.gz', group: 'Other', source_file: 'ASM.TXT' },
    { file: 'HelpPC/asm.json.gz', group: 'HelpPC', source_file: 'ASM.TXT' },
    { file: 'HelpPC/c.json.gz', group: 'HelpPC', source_file: 'C.TXT' },
];
const bundle = { _catalogFile: file, topics: {
    '0': { id: 0, aliases: { strings: ['zero'] } },
    '7': { id: 7, aliases: { strings: ['printf'] } },
} };
const escapeHtml = (value) => String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const TVView = { _controlAttrs({ commandData }) {
    return Object.fromEntries(Object.entries(commandData).map(([key, value]) =>
        ['data-tv-' + key.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase(), value]));
} };
class TVMenuItem { constructor(name, command) { this.name = name; this.command = command; } }
class TVOutline {}
eval(section('function normalizeSourceFileName(value)', 'function bundleLoadingLabel(value'));
eval(section('function normalizeDirectTopicRef(bundle, ref)', 'function flattenUhfIndexEntries(bundle)'));
eval(section('function parseUhfLinkTargetSpec(rawTarget)', 'function bundleFrozenRows(bundle, topic)'));
eval(section('function buildBundleTargetData(target)', '// ── Topic navigation'));
eval(section('function renderIndexSection(anchor', 'class TVContentsOutline'));
eval(section('class TVContentsOutline', 'function renderBundleContents(bundle)')
    + '\nglobalThis.makeOutline = () => new TVContentsOutline();');
eval(section('function wrapTopicLineMarkup(', 'function normalizedTopicTags(topic)'));
const isUhfCodeStart = () => false;
eval(section('const menuActions = new WeakMap()', 'function menuFromItems(items)')
    + '\nglobalThis.makeItem = (command, action) => withMenuAction(new TVBundleMenuItem("item", command), action);');
function expect(actual, expected) {
    if (actual !== expected) { throw new Error(JSON.stringify({ actual, expected })); }
}
const url = '/?file=Borland+C%2B%2B+3.0%2Ftchelp.json.gz';
expect(bundleTargetUrl(bundle, { bundleTopic: '007' }), url + '&topic=7');
expect(bundleTargetUrl(bundle, { topicAlias: 'PRINTF', topicLine: '12' }), url + '&topic=7&line=12');
expect(bundleTargetUrl(bundle, { bundleTopic: 0 }), url + '&topic=0');
expect(bundleTargetUrl(bundle, { topicLine: '4' }, bundle.topics['7']), url + '&topic=7&line=4');
expect(bundleTargetUrl(bundle, { topicAlias: 'missing' }), url);
expect(bundleTargetUrl(bundle, { sourceFile: 'missing.hlp', bundleTopic: '7' }), '#');
expect(bundleTargetUrl({ _catalogFile: CONTEXT_HELP_BUNDLE_FILE }, { bundleTopic: '7' }), '#');
const c = { _catalogFile: 'HelpPC/c.json.gz', topics: {} };
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', bundleTopic: '8' }), '/?file=HelpPC%2Fasm.json.gz&topic=8');
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', bundleTopic: 0 }), '/?file=HelpPC%2Fasm.json.gz&topic=0');
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', topicAlias: 'mov' }), '/?file=HelpPC%2Fasm.json.gz');
bundleCache.set('HelpPC/asm.json.gz', { topics: { '8': { id: 8, aliases: { strings: ['mov'] } } } });
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', topicAlias: 'mov' }), '/?file=HelpPC%2Fasm.json.gz&topic=8');
const inline = renderUhfInline('[link:alias=printf,line=12]printf[/link]', bundle);
if (!inline.includes('href="' + escapeHtml(url + '&topic=7&line=12') + '"')
    || !inline.includes('data-tv-topic-alias="printf"') || !inline.includes('data-tv-topic-line="12"')) {
    throw new Error('inline links lost their real URL or TVEvent target');
}
const index = renderIndexSection('P', 'P', [{ label: 'printf', topic_id: 7 }], bundle);
if (!index.includes('href="' + escapeHtml(url + '&topic=7') + '"')) {
    throw new Error('index topic did not have a real URL');
}
const outline = makeOutline();
outline.bundle = bundle;
const contents = outline.renderNodeContent({ label: 'printf', alias: 'printf' });
const more = renderUhfTopicLines({ content: ['<more>'], nav: { Down: { topic_id: 7 } } }, bundle).join('');
if (!contents.includes('href="' + escapeHtml(url + '&topic=7') + '"')
    || !more.includes('href="' + escapeHtml(url + '&topic=7') + '"')) {
    throw new Error('Contents or <more> did not expose a real topic URL');
}
expect(makeItem('bundle-open', { value: file }).getUrl(), url);
expect(makeItem('doc-open', { value: 'Formats/A & B.md' }).getUrl(), '/?doc=Formats%2FA+%26+B.md');
expect(makeItem('menu-link', { bundle, topicAlias: 'printf' }).getUrl(), url + '&topic=7');
window.location.pathname = '/index.html';
expect(bundleTargetUrl(bundle, { bundleTopic: '7' }), '/index.html' + url.slice(1) + '&topic=7');
'''
    result = subprocess.run(
        [NODE, "-e", script, "www/assets/tv-bundle-app.js"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
