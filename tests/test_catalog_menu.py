"""Release metadata and sibling labels identify every HELP without hiding files."""

import gzip
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from thelpviewer.help_database import load_help_manifest
from thelpviewer.server.converter.catalog import rebuild_catalog
from thelpviewer.server.converter.writers.bundle import export_bundle_tree


def test_original_debugger_revisions_export_into_distinct_release_branches(tmp_path):
    originals = [Path("data/sources/Borland Turbo Debugger 1.0/TDHELP.TDH"),
        Path("data/sources/Borland Turbo Assembler 1.0 with Turbo Debugger/TDHELP.TDH")]
    results = export_bundle_tree(Path("data/sources"), tmp_path, layout="helps", source_paths=originals)
    assert len(results) == 2
    assert {result.version for result in results} == {"1.0", "2.x"}
    assert all(result.product == "td" for result in results)
    for result in results:
        payload = json.loads(gzip.decompress(result.json_path.read_bytes()))
        assert payload["metadata"]["version"] == result.version
    rebuild_catalog(tmp_path, tmp_path / "catalog.json")
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    assert {entry["version"] for entry in catalog} == {"1.0", "2.x"}
    assert {entry["product_name"] for entry in catalog} == {"Borland Turbo Debugger"}


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_real_menu_objects_keep_release_branches_and_disambiguate_only_sibling_labels():
    manifest = load_help_manifest()
    catalog = [{"file": f"Debugger/{entry.bundle_stem}.json.gz", "name": entry.title,
        "product_name": "Borland Turbo Debugger", "version": entry.version}
        for entry in (manifest.entry_map[0xA9C668A7], manifest.entry_map[0xA6E139F2])]
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const core=fs.readFileSync('www/assets/tv-core.js','utf8'),source=fs.readFileSync('www/assets/tv-bundle-app.js','utf8');
const kbNoKey=0,hcNoContext=0,normalizeHelpContext=n=>Number(n)||0,bundleLoadingLabel=e=>e.name;
function part(text,start,end){return text.slice(text.indexOf(start),text.indexOf(end,text.indexOf(start)));}
eval(part(core,'class TVMenu {','class TVMenuView ')+part(core,'class TVMenuItem {','class TVMenuBar ')
 +part(source,'const menuActions = new WeakMap();','function buildDocsMenuItems(')+`
const releases=buildCatalogMenuItems(JSON.parse(process.argv[1])).filter(item=>item.subMenu);
assert.equal(releases.length,1);const branches=releases[0].subMenu.entries();
assert.deepEqual(branches.map(item=>item.name),['1.0','2.x']);
assert(branches.every(item=>item.subMenu.entries().length===1));
const entries=[{name:'Same Help',file:'Example/first.json.gz',product_name:'Example',version:'1'},
 {name:'Same Help',file:'Example/second.json.gz',product_name:'Example',version:'1'},
 {name:'Other Help',file:'Example/other.json.gz',product_name:'Example',version:'1'}];
const menu=buildCatalogMenuItems(entries).find(item=>item.subMenu).subMenu.entries()[0].subMenu.entries();
assert.deepEqual(menu.map(item=>item.name),['Same Help (first)','Same Help (second)','Other Help']);
assert.deepEqual(menu.map(item=>menuActions.get(item).value),entries.map(entry=>entry.file));
const ambiguous=catalogMenuEntryButtons([{name:'Same Help',file:'A/help.json.gz'},{name:'Same Help',file:'B/help.json.gz'}]);
assert.deepEqual(ambiguous.map(item=>item.name),['Same Help (A/help.json.gz)','Same Help (B/help.json.gz)']);
`);
'''
    result = subprocess.run([shutil.which("node"), "-e", script, json.dumps(catalog)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
