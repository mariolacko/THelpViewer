"""Real TVTextScreen pixels, ownership, line cursors and shared HELP chrome."""

import json
import os
from pathlib import Path
import hashlib
import subprocess
import sys

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url
from test_text_screen import screen_document
from thelpviewer.server.converter.base import TopicRecord
from thelpviewer.server.converter.writers.json import HelpJsonRenderer
from thelpviewer.server.converter.exporter import load_document
from thelpviewer.server.converter.readers.scorpion_bundle import _build_sco_program_documents


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Chrome and Node.js are required")
@pytest.mark.parametrize("version", [4, 5, 6, 14, 21])
def test_custom_font_screen_in_standard_help_window_draws_palette_pixels_and_releases_old_views(tmp_path, version):
    helps, docs = tmp_path / "helps", tmp_path / "docs"
    helps.mkdir(); docs.mkdir()
    document = screen_document()
    document.metadata["text_encoding"] = "utf-8"
    document.topics[0].uhf_content.append('[link:topic=8]Next article[/link]')
    document.topics[0].raw_lines.append(b'Next article')
    document.topics.append(TopicRecord(8, [b'Ordinary article'], names=['Next']))
    HelpJsonRenderer(document, "utf-8").write_json_gz(helps / "screen.json.gz")
    catalog = [{"file": "screen.json.gz", "name": "Native Screen", "source_file": "SCREEN.DAT"}]
    native_topic, native_digest = "", ""
    art_topic, art_line, art_digest = "", "", ""
    blink_digest = ""
    source = Path(f"data/sources/Scorpions Cheater DOS/Scorpions Cheater {version}" +
                  (" _shareware_" if version == 6 else "")) / (
        "PROGRAM.DAT" if version == 21 else "DATATEXT.SCO" if version < 6 else "DATATEXT.SCD")
    if source.is_file():
        native = load_document(source)
        if version != 21:
            native = _build_sco_program_documents((source,), (native,))
        HelpJsonRenderer(native, "utf-8").write_json_gz(helps / "program.json.gz")
        catalog.append({"file": "program.json.gz", "name": "Scorpion Program", "source_file": "PROGRAM.DAT"})
        font = native.fonts["program-font"].data
        cga = [bytes.fromhex(value) + b"\xff" for value in (
            "000000", "0000aa", "00aa00", "00aaaa", "aa0000", "aa00aa", "aa5500", "aaaaaa",
            "555555", "5555ff", "55ff55", "55ffff", "ff5555", "ff55ff", "ffff55", "ffffff")]
        if version >= 6:
            name = "egg" if version == 21 else "SCR2.SCD" if version == 6 else "SCREENS.SCO/0"
            native_topic = str(next(t.context_id for t in native.topics if t.alias_strings == [name]))
            screen = native.text_screens[next(t.uhf_content[0][8:-1] for t in native.topics if str(t.context_id) == native_topic)]
            pixels = bytearray()
            for y in range(400):
                for x in range(640):
                    glyph, fg, bg = screen.cells[(y // 16) * 80 + x // 8]
                    pixels.extend(cga[fg if font[glyph * 16 + y % 16] & (0x80 >> (x % 8)) else bg])
            native_digest = hashlib.sha256(pixels).hexdigest()
            if screen.blink:
                off_pixels = bytearray()
                for y in range(400):
                    for x in range(640):
                        index = (y // 16) * 80 + x // 8
                        glyph, fg, bg = screen.cells[index]
                        ink = not screen.blink[index] and font[glyph * 16 + y % 16] & (0x80 >> (x % 8))
                        off_pixels.extend(cga[fg if ink else bg])
                blink_digest = hashlib.sha256(off_pixels).hexdigest()
        special = lambda glyph: 0xB0 <= glyph <= 0xDF if version <= 6 else glyph == 0xD2
        article = next(t for t in native.topics if any(line.startswith("[screen:inline-")
                       and any(special(glyph) for glyph, _, _ in native.text_screens[line[8:-1]].cells)
                       for line in t.uhf_content))
        index = next(i for i, line in enumerate(article.uhf_content) if line.startswith("[screen:inline-")
                     and any(special(glyph) for glyph, _, _ in native.text_screens[line[8:-1]].cells))
        art_topic, art_line = str(article.context_id), str(index + 1)
        screen = native.text_screens[article.uhf_content[index][8:-1]]
        pixels = bytearray()
        for y in range(16):
            for x in range(640):
                glyph, fg, bg = screen.cells[x // 8]
                pixels.extend(cga[fg if font[glyph * 16 + y] & (0x80 >> (x % 8)) else bg])
        art_digest = hashlib.sha256(pixels).hexdigest()
    (helps / "catalog.json").write_text(json.dumps(catalog))
    config = tmp_path / "config.json"
    config.write_text('{"sources":[],"files":[]}')
    (tmp_path / "content-settings.json").write_text('{"configured":true,"help_packages":[],"dos_packages":[]}')
    url = f"http://127.0.0.1:{_free_port()}/"
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
                               "--port", url.split(":")[-1].rstrip("/"), "--log-level", "warning"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "THELP_STATE_DIR": str(tmp_path), "THELP_HELPS_DIR": str(helps), "THELP_DOCS_DIR": str(docs),
             "THELP_STATISTICS_PATH": str(tmp_path / "statistics.sqlite3"), "THELP_AUTH_ORIGIN": url.rstrip("/"),
             "THELP_DOS_CONFIG_PATH": str(config), "THELP_MIDI_SOURCES_PATH": str(config), "THELP_PUBLIC_BASE_URL": ""})
    chrome = None
    try:
        _wait_for_url(url + "healthz")
        profile = tmp_path / "chrome"
        chrome = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
                                   "--no-default-browser-check", "--remote-debugging-port=0", f"--user-data-dir={profile}",
                                   "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = _wait_for_file(profile / "DevToolsActivePort").splitlines()[0]
        script = r'''
const [port,url,nativeTopic,nativeDigest,artTopic,artLine,artDigest,blinkDigest]=process.argv.slice(1);
(async()=>{
 const target=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let seq=0;const pending=new Map(),errors=[];
 socket.onmessage=event=>{const m=JSON.parse(String(event.data));
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}};
 const send=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 await send('Page.enable');await send('Runtime.enable');
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 await send('Page.navigate',{url:url+'?file=screen.json.gz&topic=7&line=3'});
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+20000;const check=()=>{
  const root=document.querySelector('[data-tv-bundle-window]');
  if(root?._tvWindowView.currentTopic==='7'&&root.querySelectorAll('canvas.tv-text-screen').length===2){resolve();return;}
  if(Date.now()>end){reject(Error('TextScreen did not open'));return;}setTimeout(check,50);
 };check();})`);
 const result=await evaluate(`(()=>{
  const root=document.querySelector('[data-tv-bundle-window]'),viewer=root._tvWindowView.viewer;
  window.oldScreens=viewer.textScreens.slice();
  const canvas=viewer.textScreens[0].root,ctx=canvas.getContext('2d');
  const pixel=(x,y)=>Array.from(ctx.getImageData(x,y,1,1).data);
  const rect=canvas.getBoundingClientRect(),charHeight=parseFloat(getComputedStyle(canvas).fontSize);
  return {sharedWindow:root._tvWindowView instanceof window.THelpViewerTV.TVWindow,
   sharedViews:viewer.textScreens.every(v=>v instanceof window.THelpViewerTV.TVTextScreen&&v.owner===viewer),
   pixels:[pixel(0,0),pixel(1,0),pixel(1,1)],size:[canvas.width,canvas.height],
   rowHeight:rect.height,charHeight,rows:Array.from(root.querySelectorAll('.tv-topic-line')).map(r=>Number(r.dataset.tvLine)),
   cursor:root.querySelector('[data-tv-line="3"].is-target')!==null,images:root.querySelectorAll('img').length,
   scrollbars:root.querySelectorAll('.tv-scrollbar-y').length};
 })()`);
 if(!result.sharedWindow||!result.sharedViews||!result.cursor||result.images||result.scrollbars!==1
  ||JSON.stringify(result.rows)!=='[1,2,3,4,5]'||JSON.stringify(result.size)!=='[4,2]'
  ||Math.abs(result.rowHeight-result.charHeight)>0.1
  ||JSON.stringify(result.pixels)!=='[[171,205,239,255],[0,0,0,255],[171,205,239,255]]')
  throw Error('Native TextScreen differs: '+JSON.stringify(result));
 await evaluate(`document.querySelector('a[data-tv-bundle-topic="8"]').click()`);
 if(!await evaluate(`(()=>{const viewer=document.querySelector('[data-tv-bundle-window]')._tvWindowView.viewer;
  return viewer.textScreens.length===0&&window.oldScreens.every(v=>v.root===null&&v.owner===null);})()`))
  throw Error('Leaving screen retained stale view roots');
 await evaluate(`document.querySelector('[data-tv-command="bundle-back"]').click()`);
 if(!await evaluate(`document.querySelector('[data-tv-bundle-window]')._tvWindowView.viewer.textScreens.length===2`))
  throw Error('Back did not restore TextScreen');
 const search=await(await fetch(url+'api/search/global?q=Native')).json();
 if(!search.results.some(r=>r.context_hex==='7'&&r.file==='screen.json.gz'))throw Error('Screen transcription was not searchable: '+JSON.stringify(search));
 if(nativeTopic){
  await send('Page.navigate',{url:url+'?file=program.json.gz&topic='+nativeTopic});
  await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+20000;const check=()=>{
   const viewer=document.querySelector('[data-tv-bundle-window]')?._tvWindowView.viewer;
   if(viewer?.textScreens.length===25){resolve();return;}
   if(Date.now()>end){reject(Error('Native Scorpion screen did not open'));return;}setTimeout(check,50);
  };check();})`);
  const digest=await evaluate(`(async()=>{
   const viewer=document.querySelector('[data-tv-bundle-window]')._tvWindowView.viewer;
   const first=viewer.textScreens[0].root.getBoundingClientRect();
   const rowHeight=parseFloat(getComputedStyle(viewer.textScreens[0].root).fontSize);
   if(viewer.textScreens.some((view,row)=>Math.abs(view.root.getBoundingClientRect().top-first.top-row*rowHeight)>0.1))
    throw Error('Native TextScreen rows have gaps or overlap');
   const pixels=new Uint8Array(640*400*4);
   viewer.textScreens.forEach((view,row)=>pixels.set(view.root.getContext('2d').getImageData(0,0,640,16).data,row*640*16*4));
   const hash=new Uint8Array(await crypto.subtle.digest('SHA-256',pixels));
   return Array.from(hash,value=>value.toString(16).padStart(2,'0')).join('');
  })()`);
  if(digest!==nativeDigest)throw Error('Native Scorpion glyph/palette pixels differ: '+digest);
  if(blinkDigest){
   if(!await evaluate(`(()=>{const v=document.querySelector('[data-tv-bundle-window]')._tvWindowView.viewer;
    window.blinkViews=v.textScreens.filter(s=>s.screen.blink?.some(Boolean));
    return window.blinkViews.length>0&&window.blinkViews.every(s=>s._blinkTimer===null&&s._blinkVisible);})()`))
    throw Error('Reduced motion did not retain visible native blink glyphs');
   await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
   await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
    if(window.blinkViews.every(s=>s._blinkTimer!==null&&!s._blinkVisible)){resolve();return;}
    if(Date.now()>end){reject(Error('Native blink did not change phase'));return;}setTimeout(check,5);
   };check();})`);
   const offDigest=await evaluate(`(async()=>{
    const views=document.querySelector('[data-tv-bundle-window]')._tvWindowView.viewer.textScreens;
    const pixels=new Uint8Array(640*400*4);
    views.forEach((v,row)=>pixels.set(v.root.getContext('2d').getImageData(0,0,640,16).data,row*640*16*4));
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',pixels)),v=>v.toString(16).padStart(2,'0')).join('');
   })()`);
   if(offDigest!==blinkDigest)throw Error('Blink off phase changed background or unflagged glyphs: '+offDigest);
   await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
   await evaluate(`new Promise(resolve=>setTimeout(resolve,50))`);
   if(!await evaluate(`window.blinkViews.every(v=>v._blinkTimer===null&&v._blinkVisible)`))
    throw Error('Changing reduced motion retained a timer');
   await evaluate(`document.querySelector('[data-tv-bundle-window]')._tvWindowView.viewer.setContent('Next article')`);
   if(!await evaluate(`window.blinkViews.every(v=>v.root===null&&v.owner===null&&v._blinkTimer===null&&v._motionQuery===null)`))
    throw Error('Leaving blink screen retained animation or owned roots');
  }
 }
 if(artTopic){
  await send('Page.navigate',{url:url+'?file=program.json.gz&topic='+artTopic+'&line='+artLine});
  await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+20000;const check=()=>{
   const root=document.querySelector('[data-tv-bundle-window]');
   if(root?._tvWindowView.currentTopic==='${artTopic}'&&root.querySelector('[data-tv-line="${artLine}"].is-target canvas.tv-text-screen')){
    resolve();return;}
   if(Date.now()>end){reject(Error('Inline artwork row/cursor did not open'));return;}setTimeout(check,50);
  };check();})`);
  const inlineDigest=await evaluate(`(async()=>{
   const canvas=document.querySelector('[data-tv-line="${artLine}"].is-target canvas.tv-text-screen');
   const pixels=canvas.getContext('2d').getImageData(0,0,640,16).data;
   return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',pixels)),v=>v.toString(16).padStart(2,'0')).join('');
  })()`);
  if(inlineDigest!==artDigest)throw Error('Inline custom glyph pixels differ: '+inlineDigest);
 }
 if(errors.length)throw Error(errors.join('\n'));
 console.log(JSON.stringify(result));socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
'''
        result = subprocess.run([NODE, "-e", script, port, url, native_topic, native_digest, art_topic, art_line, art_digest, blink_digest],
                                capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr
    finally:
        if chrome is not None:
            chrome.terminate(); chrome.wait(timeout=10)
        server.terminate(); server.wait(timeout=10)
