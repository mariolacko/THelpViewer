"""Real shared TVWindow rendering/navigation of the formerly title-only page."""

import json
import os
from pathlib import Path
import subprocess
import struct
import sys

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url
from test_winhelp_reader import win31, single_article  # Reuse native-source fixtures.
from thelpviewer.server.converter.readers.winhelp import WinHelpReader
from thelpviewer.server.converter.writers.json import HelpJsonRenderer


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Chrome and Node.js are required")
def test_windows_hlp_text_columns_link_and_back_in_standard_help_window(tmp_path, win31):
    helps, docs = tmp_path / "helps", tmp_path / "docs"
    helps.mkdir(); docs.mkdir()
    HelpJsonRenderer(win31, display_encoding="cp1252").write_json_gz(helps / "win31wh.json.gz")
    target_source = single_article([(b"word " * 40, b"\xff")], native_hash=1234, context_offset=130)
    target = WinHelpReader("TARGET.HLP").read_bytes(target_source)
    operand = b"\4" + struct.pack("<I", 1234) + b"TARGET.HLP\0"
    source = WinHelpReader("SOURCE.HLP").read_bytes(single_article([
        (b"", b"\xeb" + struct.pack("<H", len(operand)) + operand),
        (b"Jump to target cursor", b"\x89"), (b"", b"\xff")]))
    for stem, document in (("source", source), ("target", target)):
        HelpJsonRenderer(document, display_encoding="cp1252").write_json_gz(helps / f"{stem}.json.gz")
    (helps / "catalog.json").write_text(json.dumps([{
        "file": "win31wh.json.gz", "name": win31.metadata["title"],
        "source_file": "WIN31WH.HLP", "group": "Borland C++ 4.x", "product": "bc",
    }, *[{"file": f"{stem}.json.gz", "name": stem, "source_file": f"{stem.upper()}.HLP"}
         for stem in ("source", "target")]]))
    config = tmp_path / "config.json"
    config.write_text('{"sources":[],"files":[]}')
    (tmp_path / "content-settings.json").write_text('{"configured":true,"help_groups":[],"dos_packages":[]}')
    url = f"http://127.0.0.1:{_free_port()}/"
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app",
                               "--host", "127.0.0.1", "--port", url.split(":")[-1].rstrip("/"), "--log-level", "warning"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "THELP_STATE_DIR": str(tmp_path), "THELP_HELPS_DIR": str(helps), "THELP_DOCS_DIR": str(docs),
             "THELP_STATISTICS_PATH": str(tmp_path / "statistics.sqlite3"), "THELP_AUTH_ORIGIN": url.rstrip("/"),
             "THELP_DOS_CONFIG_PATH": str(config), "THELP_MIDI_SOURCES_PATH": str(config), "THELP_PUBLIC_BASE_URL": ""})
    chrome = None
    try:
        _wait_for_url(url + "healthz")
        profile = tmp_path / "chrome"
        chrome = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
                                    "--no-default-browser-check", "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = _wait_for_file(profile / "DevToolsActivePort").splitlines()[0]
        script = r'''
const [port,url]=process.argv.slice(1);
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
 await send('Page.navigate',{url:url+'?file=win31wh.json.gz&topic=2559'});
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+20000;const check=()=>{
  const view=document.querySelector('[data-tv-bundle-window]')?._tvWindowView;
  if(view?.currentTopic==='2559'){resolve();return;}
  if(Date.now()>end){reject(Error('Native Windows article did not open'));return;}setTimeout(check,50);
 };check();})`);
 const result=await evaluate(`(()=>{
  const root=document.querySelector('[data-tv-bundle-window]'),view=root._tvWindowView;
  const rows=Array.from(root.querySelectorAll('.tv-topic-line')).map(row=>row.textContent.replace(/\u00a0/g,' '));
  const content=root.textContent;
  return {sharedWindow:view instanceof window.THelpViewerTV.TVWindow,
   fullText:content.includes('creates a font table')&&content.includes('Comments')&&content.includes('See Also'),
   rows:rows.length,parameters:rows.includes(' Parameter   Description'),values:rows.includes('             Value     Meaning'),
   links:root.querySelectorAll('a[data-tv-bundle-topic]').length,
   scrollbars:root.querySelectorAll('.tv-scrollbar-y').length};
 })()`);
 if(!result.sharedWindow||!result.fullText||result.rows<40||!result.parameters||!result.values||result.links<4||result.scrollbars!==1)
  throw Error('Native HELP rendering differs: '+JSON.stringify(result));
 await evaluate(`document.querySelector('[data-tv-bundle-window] a[data-tv-bundle-topic="2556"]').click()`);
 if(!await evaluate(`document.querySelector('[data-tv-bundle-window]')._tvWindowView.currentTopic==='2556'`))throw Error('Native link did not open its actual article');
 await evaluate(`document.querySelector('[data-tv-command="bundle-back"]').click()`);
 if(!await evaluate(`document.querySelector('[data-tv-bundle-window]')._tvWindowView.currentTopic==='2559'`))throw Error('Back did not restore the source article');
 await send('Page.navigate',{url:url+'?file=source.json.gz&topic=0'});
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+15000;const check=()=>{
  const root=document.querySelector('[data-tv-bundle-window]');
  if(root?._tvWindowView.currentTopic==='0'&&root.querySelector('a[data-tv-source-file="TARGET.HLP"]')){resolve();return;}
  if(Date.now()>end){reject(Error('External link source did not open'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`document.querySelector('a[data-tv-source-file="TARGET.HLP"]').click()`);
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+10000;const check=()=>{
  const root=Array.from(document.querySelectorAll('[data-tv-bundle-window]')).find(root=>root._tvWindowView.bundle._catalogFile==='target.json.gz');
  if(root?._tvWindowView.currentLine===2&&root.querySelector('[data-tv-line="2"].is-target')){resolve();return;}
  if(Date.now()>end){reject(Error('External native context lost its target line'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`document.querySelector('[data-tv-command="bundle-back"]').click()`);
 if(!await evaluate(`Array.from(document.querySelectorAll('[data-tv-bundle-window]')).some(root=>root._tvWindowView.bundle._catalogFile==='source.json.gz'&&root._tvWindowView.currentTopic==='0')`))throw Error('External Back did not restore the source');
 await send('Page.navigate',{url:url+'?file=target.json.gz&topic=winhelp-hash%3A000004d2'});
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+15000;const check=()=>{
  const root=document.querySelector('[data-tv-bundle-window]');
  if(root?._tvWindowView.currentTopic==='0'&&root._tvWindowView.currentLine===2){resolve();return;}
  if(Date.now()>end){reject(Error('Public alias URL lost its cursor'));return;}setTimeout(check,50);
 };check();})`);
 if(errors.length)throw Error(errors.join('\n'));
 console.log(JSON.stringify(result));socket.close();
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([NODE, "-e", script, port, url], capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["fullText"]
    finally:
        if chrome is not None:
            chrome.terminate(); chrome.wait(timeout=10)
        server.terminate(); server.wait(timeout=10)
