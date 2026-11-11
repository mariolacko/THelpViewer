"""Checks for the grid primitive and removal of the server terminal."""

from pathlib import Path
import shutil
import subprocess

import pytest

def test_grid_is_exported_and_uses_list_scrollbars():
    source = Path("thelpviewer/server/converter/assets/tv-core.js").read_text(encoding="utf-8")
    assert "class TVGridView extends TVListBox" in source
    assert "setHeadersVisible(visible)" in source
    assert "selectCell(row, column, options = {})" in source
    assert "    TVGridView," in source
    assert source == Path("www/assets/tv-core.js").read_text(encoding="utf-8")


def test_server_terminal_is_removed():
    for file in ("tv-dialogs.js", "tv-shell.js", "tv-bundle-app.js"):
        source = Path("www/assets", file).read_text(encoding="utf-8")
        assert "TVServerTerminalDialog" not in source
        assert "/api/terminal/" not in source
    assert not Path("thelpviewer/server/terminal.py").exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_grid_character_columns_text_and_pre_mount_selection():
    script = r'''
const assert=require('node:assert/strict'),fs=require('node:fs');
global.window={};global.document={addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV;
const grid=new TV.TVGridView(new TV.TVRect(0,0,40,10),[
 {title:'Name',width:20},{title:'Value',width:8.9},'Default',
 {title:'Small',width:1},{title:'Large',width:Infinity}]);
const cells=grid._columnBounds();
assert.deepEqual(cells.map(r=>[r.x1,r.y1,r.x2,r.y2]),[
 [0,0,20,1],[20,0,28,1],[28,0,40,1],[40,0,43,1],[43,0,243,1]]);
assert.equal(grid.numCols,1,'table columns changed inherited list columns');
const values=['<name>','A&B','😀','four','five'];grid.setRows([values,['second']]);
grid.selectCell(1,3,{scroll:false});grid.setHeadersVisible(false);
assert.equal(grid.selectedIndex,1);assert.equal(grid.selectedColumn,3);
assert.equal(grid.getText(0),'<name>\tA&B\t😀\tfour\tfive');
assert.equal(grid.getText(0,3),'<na');assert.equal(grid.getCell(0,2),'😀');
assert.ok(grid.itemMarkup(values,0).includes('&lt;name&gt;'));
assert.ok(grid.itemMarkup(values,0).includes('A&amp;B'));
assert.ok(grid.draw().includes('class="tv-grid-header" hidden'));
assert.ok(!grid.draw().includes('headers-hidden'));
grid.setHeadersVisible(true);assert.ok(!grid.draw().includes('class="tv-grid-header" hidden'));
grid.setHeadersVisible(false);
grid.setRows([]);assert.equal(grid.selectedIndex,-1);assert.equal(grid.getText(0),'');
assert.equal(grid.getCell(0,0),undefined);
'''
    subprocess.run([shutil.which("node"), "-e", script, "www/assets/tv-core.js"],
                   check=True, capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_terminal_keeps_partial_lines_and_split_crlf_with_a_bounded_buffer():
    script = r'''
const assert=require('node:assert/strict'),fs=require('node:fs');
global.window={};global.document={addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV,terminal=new TV.TVTerminal(new TV.TVRect(0,0,20,3),3);
terminal.append('one\rtwo\r\nthree');
assert.deepEqual(terminal.lines,['one','two','three']);
terminal.clear();
terminal.appendChunk('one\r');terminal.appendChunk('');terminal.appendChunk('\ntw');
assert.deepEqual(terminal.lines,['one']);assert.equal(terminal.streamTail,'tw');
terminal.appendChunk('o\r');terminal.appendChunk('\nthree\nfour\nfi');terminal.appendChunk('ve');
assert.deepEqual(terminal.lines,['two','three','four']);assert.equal(terminal.streamTail,'five');
terminal.appendChunk(null);assert.equal(terminal.streamTail,'five');
terminal.appendChunk('\r');terminal.clear();terminal.appendChunk('\n');
assert.deepEqual(terminal.lines,['']);assert.equal(terminal.streamTail,'');
terminal.append('last');assert.equal(terminal.lines.at(-1),'last');
'''
    subprocess.run([shutil.which("node"), "-e", script, "www/assets/tv-core.js"],
                   check=True, capture_output=True, text=True)
