"""UHF retains native glyph/font bytes and palette indexes, not raster images."""

import base64
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from thelpviewer.server.converter.base import HelpDocument, TopicRecord
from thelpviewer.server.converter.text_screen import BitmapFont, TextScreen
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.server.search_index import _topic_rows


def screen_document():
    font = bytearray(256 * 2)
    font[65 * 2:65 * 2 + 2] = b"\x80\x40"
    screen = TextScreen(2, 2, ((65, 2, 0), (66, 1, 2), (0, 0, 1), (255, 2, 1)),
                        "source-font", "source", ("[Native]", "<text>"))
    return HelpDocument("test", "test.dat", [TopicRecord(7, [b"Before", b"[Native]", b"<text>", b"After"],
                        names=["Screen"], uhf_content=["Before", "[screen:art]", "After"])],
                        [], fonts={"source-font": BitmapFont(2, 2, bytes(font))}, text_screens={"art": screen},
                        metadata={"palettes": {"source": {"type": "indexed", "colors": {
                            "0": "#000000", "1": "#123456", "2": "#abcdef"}}}})


def test_roundtrip_keeps_cell_indexes_font_bits_and_search_transcription():
    document = screen_document()
    payload = HelpJsonRenderer(document).render_document()
    assert payload["topics"]["7"]["content"] == ["Before", "[screen:art]", "After"]
    screen = payload["text_screens"]["art"]
    assert screen["cells"] == [[65, 2, 0], [66, 1, 2], [0, 0, 1], [255, 2, 1]]
    assert screen["palette"] == "source" and screen["font"] == "source-font"
    assert base64.b64decode(payload["fonts"]["source-font"]["data"]) == document.fonts["source-font"].data
    assert "PNG" not in json.dumps(payload) and "image/png" not in json.dumps(payload)
    assert list(_topic_rows(payload, "test.json.gz", "Test"))[0][-2:] == (
        "Before\n[Native]\n<text>\nAfter", "Before [Native] <text>")
    plain = HelpJsonRenderer(HelpDocument("test", "plain", [], [])).render_document()
    assert "fonts" not in plain and "text_screens" not in plain


@pytest.mark.parametrize("cell_format,expected", [
    ("glyph-fg-bg", bytes((65, 2, 0, 66, 1, 2, 0, 0, 1, 255, 2, 1))),
    ("dos-text", bytes((65, 2, 66, 0x21, 0, 0x10, 255, 0x12))),
])
def test_base64_forms_store_native_bytes_without_changing_palette_or_font(cell_format, expected):
    document = screen_document()
    screen = replace(document.text_screens["art"], cell_format=cell_format)
    payload = HelpJsonRenderer(replace(document, text_screens={"art": screen})).render_document()["text_screens"]["art"]
    assert payload["cell_format"] == cell_format and "cells" not in payload
    assert base64.b64decode(payload["data"], validate=True) == expected
    assert payload["font"] == "source-font" and payload["palette"] == "source"


@pytest.mark.parametrize("cell_format", [None, "glyph-fg-bg", "dos-text-blink"])
def test_explicit_blink_mask_is_lossless_in_readable_and_packed_forms(cell_format):
    screen = replace(screen_document().text_screens["art"], cell_format=cell_format,
                     blink=(True, False, True, False))
    payload = screen.to_dict()
    if cell_format == "dos-text-blink":
        assert base64.b64decode(payload["data"]) == bytes((65, 0x82, 66, 0x21, 0, 0x90, 255, 0x12))
        assert "blink" not in payload
    else:
        assert payload["blink"] == [True, False, True, False]


def test_bright_background_mode_uses_bit_seven_as_a_palette_index_not_blink():
    screen = TextScreen(1, 1, ((65, 15, 9),), "source-font", cell_format="dos-text-bright")
    assert base64.b64decode(screen.to_dict()["data"]) == b"A\x9f"
    assert not screen.blink


@pytest.mark.parametrize("change", [
    {"blink": (True,)}, {"blink": (1, 0, 0, 0)},
    {"blink": (True, False, False, False), "cell_format": "dos-text"},
    {"blink": (True, False, False, False), "cell_format": "dos-text-bright"},
    {"cells": ((65, 1, 8),) * 4, "cell_format": "dos-text-blink"},
    {"cells": ((65, 1, 16),) * 4, "cell_format": "dos-text-bright"},
])
def test_invalid_blink_masks_and_ambiguous_dos_modes_are_rejected(change):
    with pytest.raises(ValueError):
        replace(screen_document().text_screens["art"], **change)


@pytest.mark.parametrize("change", [{"width": 0}, {"height": True}, {"width": 33}, {"data": b"short"}])
def test_bad_font_dimensions_and_incomplete_glyph_tables_are_rejected(change):
    with pytest.raises(ValueError):
        replace(screen_document().fonts["source-font"], **change)


@pytest.mark.parametrize("change", [{"cols": 0}, {"rows": True}, {"cells": ((1, 2, 3),)},
    {"cells": ((65, -1, 0),) * 4}, {"cells": ((256, 1, 0),) * 4}, {"cells": ((65, True, 0),) * 4},
    {"font": "bad/path"}, {"palette": "source;url()"}, {"text": ("one",)}, {"text": ("a\nb", "c")},
    {"cell_format": "unknown"}, {"cell_format": "dos-text", "cells": ((65, 1, 8),) * 4},
])
def test_bad_screen_cells_dimensions_and_references_are_rejected(change):
    with pytest.raises(ValueError):
        replace(screen_document().text_screens["art"], **change)


def test_writer_requires_real_resource_font_and_palette_targets():
    document = screen_document()
    for bad in [replace(document, fonts={}), replace(document, text_screens={}),
                replace(document, text_screens={"bad/path": document.text_screens["art"]}),
                replace(document, metadata={}),
                replace(document, text_screens={"art": replace(document.text_screens["art"], cells=((65, 9, 0),) * 4)})]:
        with pytest.raises(ValueError):
            HelpJsonRenderer(bad).render_document()
    cga = replace(document, text_screens={"art": replace(document.text_screens["art"], palette="cga")},
                  metadata={"palettes": {"cga": {"colors": {"1": "#123456"}}}})
    assert HelpJsonRenderer(cga).render_document()["text_screens"]["art"]["palette"] == "cga"
    code = replace(document, text_screens={}, fonts={}, topics=[TopicRecord(7, [],
        uhf_content=["[code]", "[screen:missing]", "[/code]", "[[screen:literal]"])])
    assert HelpJsonRenderer(code).render_document()["topics"]["7"]["content"][1] == "[screen:missing]"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_shared_view_draws_original_bits_palette_and_addressable_help_rows(tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(HelpJsonRenderer(screen_document()).to_json())
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const core=fs.readFileSync('www/assets/tv-core.js','utf8'),source=fs.readFileSync('www/assets/tv-bundle-app.js','utf8');
function section(s,a,b){const x=s.indexOf(a),y=s.indexOf(b,x);assert(x>=0&&y>x);return s.slice(x,y);}
class TVRect {constructor(){}}
class TVView {constructor(){this.root=null;} static _viewBoundsStyle(){return '';}
 _drawAttrs(){return {};} bindRoot(root){this.root=root;return this;}}
const escapeHtml=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const attrsToString=()=>'';
eval(section(core,'class TVTextScreen extends TVView','class TVImage extends TVView')+'globalThis.ScreenView=TVTextScreen;');
const TVTextScreen=globalThis.ScreenView;
const bundle=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
const resolveUhfColor=(bundle,key)=>{const [p,i]=key.split(':');return bundle.palettes[p]?.colors[i]||null;};
const normalizeTopicRef=()=>null,isUhfCodeStart=line=>/^\[code/.test(line),renderUhfInline=text=>escapeHtml(text);
eval(section(source,'function uhfTextScreenForLine(','function normalizedTopicTags('));
const screen=uhfTextScreenForLine(bundle,'[screen:art]');assert(screen);
for(const [cell_format,bytes] of [['dos-text',[65,2,66,0x21,0,0x10,255,0x12]],
 ['glyph-fg-bg',[65,2,0,66,1,2,0,0,1,255,2,1]]]){
 const packed={...bundle.text_screens.art,cell_format,data:Buffer.from(bytes).toString('base64')};delete packed.cells;
 const decoded=uhfTextScreenForLine({...bundle,text_screens:{art:packed}},'[screen:art]');
 assert.deepEqual(decoded.cells,screen.cells);assert.deepEqual(decoded.palette,screen.palette);
 for(const bad of [{...packed,cells:screen.cells},{...packed,data:'bad'},
  {...packed,cell_format:'unknown'}, {...packed,data:Buffer.from(bytes.slice(1)).toString('base64')}]){
  assert.equal(uhfTextScreenForLine({...bundle,text_screens:{art:bad}},'[screen:art]'),null);
 }
}
const blink={...bundle.text_screens.art,cell_format:'dos-text',data:Buffer.from([65,0x82,66,0x21,0,0x10,255,0x12]).toString('base64')};
delete blink.cells;assert.equal(uhfTextScreenForLine({...bundle,text_screens:{art:blink}},'[screen:art]'),null);
blink.cell_format='dos-text-blink';
const animated=uhfTextScreenForLine({...bundle,text_screens:{art:blink}},'[screen:art]');
assert.deepEqual(animated.cells,screen.cells);assert.deepEqual(animated.blink,[true,false,false,false]);
const bright={...blink,cell_format:'dos-text-bright',data:Buffer.from([65,0x92,66,0x21,0,0x10,255,0x12]).toString('base64')};
const brightColors={...bundle,palettes:{source:{colors:{...bundle.palettes.source.colors,9:'#5555ff'}}}};
assert.deepEqual(uhfTextScreenForLine({...brightColors,text_screens:{art:bright}},'[screen:art]').cells[0],[65,2,9]);
for(const bad of [{...blink,blink:[true,false,false,false]},
 {...bundle.text_screens.art,blink:[true]}, {...bundle.text_screens.art,blink:[1,0,0,0]}]){
 assert.equal(uhfTextScreenForLine({...bundle,text_screens:{art:bad}},'[screen:art]'),null);
}
assert.deepEqual(screen.palette,{0:'#000000',1:'#123456',2:'#abcdef'});
const calls=[],context={fillStyle:'',fillRect(...args){calls.push([this.fillStyle,...args]);}};
const view=new TVTextScreen(new TVRect()).setData(screen).bindRoot({getContext:()=>context});
assert.equal(view.dataSize(),12);assert.equal(view.root.width,4);assert.equal(view.root.height,4);
assert.deepEqual(calls.slice(0,3),[['#000000',0,0,2,2],['#abcdef',0,0,1,1],['#abcdef',1,1,1,1]]);
assert(view.draw().includes('width="4" height="4"'));assert(!view.draw().includes('<img'));
const views=[];const lines=renderUhfTopicLines(bundle.topics['7'],bundle,views);
assert.equal(lines.length,4);assert.equal(views.length,2);
for(let i=0;i<4;i++)assert(lines[i].includes(`data-tv-line="${i+1}"`));
assert(lines[1].includes('<canvas')&&lines[1].includes('[Native]'));
assert(lines[2].includes('&lt;text>'));assert(lines[3].includes('After'));
assert.equal(renderUhfTopicLines({content:['[code]','[screen:art]','[/code]']},bundle).length,1);
assert(!renderUhfTopicLines({content:['[code]','[screen:art]','[/code]']},bundle)[0].includes('<canvas'));
for(const bad of [{...bundle.text_screens.art,cells:[[65,99,0]]}, {...bundle.text_screens.art,cols:2.5},
 {...bundle.text_screens.art,font:'missing'}, {...bundle.text_screens.art,text:['wrong length']}]){
 assert.equal(uhfTextScreenForLine({...bundle,text_screens:{art:bad}},'[screen:art]'),null);
}
assert.equal(uhfTextScreenForLine({...bundle,fonts:{'source-font':{width:2,height:2,data:'bad'}}},'[screen:art]'),null);
assert.equal(uhfTextScreenForLine(bundle,'[[screen:art]'),null);
view.bindRoot(null);assert.equal(view.root,null);
// Shared-view animation owns its timer and responds to reduced motion; no CSS animation.
const timers=new Map(),listeners=new Set();let id=0;
const motion={matches:false,addEventListener:(n,f)=>listeners.add(f),removeEventListener:(n,f)=>listeners.delete(f)};
globalThis.window={matchMedia:()=>motion,setInterval:f=>{timers.set(++id,f);return id;},clearInterval:i=>timers.delete(i)};
const animatedCalls=[],animatedContext={fillStyle:'',fillRect(...args){animatedCalls.push([this.fillStyle,...args]);}};
const animatedView=new TVTextScreen(new TVRect()).setData(animated).bindRoot({getContext:()=>animatedContext,isConnected:true});
assert.equal(timers.size,1);assert.equal(listeners.size,1);animatedCalls.length=0;
Array.from(timers.values())[0]();
assert.deepEqual(animatedCalls[0],['#000000',0,0,2,2]);
assert(!animatedCalls.some(c=>c[0]==='#abcdef'&&c[1]<2&&c[2]<2&&c[3]===1));
motion.matches=true;Array.from(listeners)[0]();assert.equal(timers.size,0);
assert.equal(animatedView._blinkVisible,true);
motion.matches=false;Array.from(listeners)[0]();assert.equal(timers.size,1);
const split=[];renderUhfTopicLines(bundle.topics['7'],{...bundle,text_screens:{art:blink}},split);
assert.deepEqual(split[0].screen.blink,[true,false]);assert.deepEqual(split[1].screen.blink,[false,false]);
animatedView.setData(screen);assert.equal(timers.size,0);assert.equal(listeners.size,0);
animatedView.setData(animated);assert.equal(timers.size,1);animatedView.bindRoot(null);
assert.equal(timers.size,0);assert.equal(listeners.size,0);assert.equal(animatedView.root,null);
animatedView._onMotionChange();assert.equal(timers.size,0); // Already queued preference notification.
'''
    result = subprocess.run([shutil.which("node"), "-e", script, str(bundle)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    for filename in ("tv-core.js", "tv-bundle-app.js", "tv-context-help.js", "turbovision.css"):
        assert (Path("www/assets") / filename).read_bytes() == (
            Path("thelpviewer/server/converter/assets") / filename).read_bytes()
