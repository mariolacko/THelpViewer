"""The DOS palette is the single source for defaults, themes and user colors."""

from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_palette_defaults_theme_transitions_and_saved_custom_colors():
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const properties=new Map(),stored=new Map();let dark=true;
global.document={addEventListener(){},documentElement:{
 classList:{add(){}},style:{setProperty:(key,value)=>properties.set(key,value),removeProperty:key=>properties.delete(key)}}};
global.window={localStorage:{getItem:key=>stored.get(key)||null,setItem:(key,value)=>stored.set(key,value),removeItem:key=>stored.delete(key)},
 matchMedia:()=>({matches:dark})};
global.getComputedStyle=()=>({getPropertyValue:key=>properties.get(key)||''});
eval(fs.readFileSync('www/assets/tv-core.js','utf8'));
const TV=window.THelpViewerTV;
for(const group of TV.buildPaletteFromCurrentStyle())for(const item of group.items){
 assert.equal(item.attr,TV.TV2_APP_COLOR_ATTRIBUTES[item.paletteIndex-1],'Missing browser colors replaced DOS defaults before initialization');
}
const defaults=()=>{for(const [index,token] of Object.entries(TV.TV2_PALETTE_TOKENS)){
 const attr=TV.TV2_APP_COLOR_ATTRIBUTES[index-1];
 assert.equal(properties.get(`--tv-palette-${token}-bg`),TV.DOS_COLORS[(attr>>4)&15]);
 assert.equal(properties.get(`--tv-palette-${token}-fg`),TV.DOS_COLORS[attr&15]);}};
TV.initializeTVTheme();defaults();
for(const group of TV.buildPaletteFromCurrentStyle())for(const item of group.items){
 assert.equal(item.attr,TV.TV2_APP_COLOR_ATTRIBUTES[item.paletteIndex-1]);
}
const paletteKeys=new Set(Object.values(TV.TV2_PALETTE_TOKENS).flatMap(token=>['bg','fg'].map(part=>`--tv-palette-${token}-${part}`)));
for(const preset of Object.values(TV.THEME_PRESETS))for(const key of Object.keys(preset.vars)){
 assert(paletteKeys.has(key)||key.startsWith('--tv-code-')||key==='--tv-muted','Theme needs a second variable translation: '+key);
}
const fields=['help-text-bg','help-frame-active-bg','help-frame-active-fg','help-scroll-controls-fg','help-frame-passive-fg','dialog-frame-active-fg'];
const expected={
 dark:['#000000','#0000aa','#aaaaaa','#ffffff','#aaaaaa','#ffff55'],
 green:['#00aa00','#00aa00','#ffffff','#00ff00','#aaaaaa','#ffffff'],
 amber:['#aa5500','#aa5500','#ffff55','#ffff55','#aaaaaa','#ffffff'],
 gray:['#c0c0c0','#aaaaaa','#ffffff','#ffffff','#aaaaaa','#ffffff'],
};
for(const [theme,colors] of Object.entries(expected)){
 TV.applyThemePreset(theme);
 fields.forEach((field,index)=>assert.equal(properties.get('--tv-palette-'+field),colors[index],theme+' '+field));
}
TV.applyThemeAndSyncPalette('dark');
assert.equal(properties.get('--tv-palette-help-text-fg'),'#aaaaaa');
assert.equal(properties.get('--tv-palette-help-frame-active-fg'),'#aaaaaa');
let palette=TV.buildPaletteFromCurrentStyle();
TV.setColorPaletteAttribute(palette,50,0x4f);TV.applyColorPalette(palette,true);
assert.equal(properties.get('--tv-palette-dialog-input-normal-bg'),'#aa0000');
assert.equal(properties.get('--tv-palette-help-text-fg'),'#aaaaaa','User colors discarded the active theme');
TV.initializeTVTheme();
assert.equal(properties.get('--tv-palette-dialog-input-normal-bg'),'#aa0000','Initialization lost saved colors');
TV.applyThemeAndSyncPalette('default');defaults();
TV.applyThemeAndSyncPalette('auto');assert.equal(properties.get('--tv-palette-help-text-bg'),'#000000');
dark=false;TV.applyThemeAndSyncPalette('auto');defaults();
TV.applyColorPalette([],false);defaults();
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_dialog_controls_do_not_duplicate_native_palette_and_bounds_drawing_in_css():
    css = Path("www/assets/turbovision.css").read_text()
    for selector in (".tv-file-open-history-", ".tv-ascii-cell", ".tv-calendar-arrow",
                     "[data-tv-ascii-chart]", "[data-tv-calendar-grid]", ".tv-color-cell",
                     "[data-tv-colors-display]", "[data-tv-file-open-cancel]",
                     "[data-tv-change-dir-cancel]", ".tv-search-result",
                     ".tv-cluster.has-scrollbars", ".tv-checkbox-item:focus-within",
                     ".tv-radio-item:focus-within", ".tv-multicheck-item:focus-within",
                     ".tv-dialog-button.is-default", ".tv-dialog-button.is-pressed",
                     ".tv-dialog-button:disabled", ".tv-dialog-button:focus-visible"):
        assert selector not in css
    assert "--tv-colors-sample-" not in css
    assert "--tv-palette-dialog-cluster-" not in css
    assert "--tv-palette-dialog-button-" not in css
    assert "--tv-dialog-button-" not in css
    assert "--tv-dialog-input-" not in css
