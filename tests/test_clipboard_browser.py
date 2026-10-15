"""System clipboard commands and native shortcuts use shared Turbo Vision views."""

from pathlib import Path
import subprocess
import sys

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Chrome and Node.js are required")
def test_system_clipboard_shortcuts_validation_and_readonly_views(tmp_path):
    (tmp_path / "assets").symlink_to(Path.cwd() / "www/assets", target_is_directory=True)
    (tmp_path / "index.html").write_text(
        '<!doctype html><html><head><link rel="stylesheet" href="assets/turbovision.css">'
        '<script src="assets/tv-core.js"></script></head><body class="tv-page">'
        '<main class="tv-desktop" style="width:100vw;height:100vh"></main></body></html>',
        encoding="utf-8",
    )
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(tmp_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    chrome = None
    try:
        _wait_for_url(url)
        profile = tmp_path / "chrome"
        chrome = subprocess.Popen(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
             "--no-default-browser-check", "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        debugging = _wait_for_file(profile / "DevToolsActivePort").splitlines()[0]
        script = r'''
const [port,url]=process.argv.slice(1);
(async()=>{
 const target=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let next=0,loaded=false;const pending=new Map();
 socket.onmessage=event=>{const r=JSON.parse(String(event.data));if(r.method==='Page.loadEventFired')loaded=true;
  const p=pending.get(r.id);if(!p)return;
  pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);};
 const send=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++next;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 await send('Page.enable');await send('Runtime.enable');await send('Page.navigate',{url});
 await new Promise((resolve,reject)=>{const end=Date.now()+5000;const check=()=>{
  if(loaded){resolve();return;}if(Date.now()>end){reject(Error('Clipboard fixture navigation timed out'));return;}setTimeout(check,20);
 };check();});await send('Page.bringToFront');
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+5000;const check=()=>{
  if(window.THelpViewerTV?.TVInputLine&&document.querySelector('.tv-desktop')){resolve();return;}
  if(Date.now()>end){reject(Error('Clipboard fixture did not load'));return;}setTimeout(check,20);
 };check();})`);
 await send('Browser.grantPermissions',{origin:new URL(url).origin,permissions:['clipboardReadWrite','clipboardSanitizedWrite']});
 await evaluate(`(()=>{
  const TV=window.THelpViewerTV;
  window.program=new TV.TVProgram(new TV.TVRect());
  window.desktop=new TV.TVDesktop(new TV.TVRect()).bindRoot(document.querySelector('.tv-desktop'));program.insert(desktop);
  window.dialog=new TV.TVDialog(new TV.TVRect(0,0,46,12),'Clipboard test');
  window.source=new TV.TVInputLine(new TV.TVRect(2,1,40,2),40);
  window.destination=new TV.TVInputLine(new TV.TVRect(2,3,40,4),8);
  window.numeric=new TV.TVInputLine(new TV.TVRect(2,5,40,6),4).setValidator(new TV.TVFilterValidator('0123456789'));
  dialog.insert(new TV.TVGroup(new TV.TVRect(0,0,44,10)).insertAll([source,destination,numeric]));desktop.insert(dialog);dialog.open();
  window.commandCount=0;const original=source.handleEvent.bind(source);
  source.handleEvent=event=>{if(event.what===TV.evCommand&&[TV.cmCut,TV.cmCopy,TV.cmPaste].includes(event.command))commandCount++;original(event);};
  if(TV.getKeyCode({key:'Insert',ctrlKey:true})!==TV.kbCtrlIns
   ||TV.getKeyCode({key:'Insert',shiftKey:true})!==TV.kbShiftIns
   ||TV.getKeyCode({key:'Delete',shiftKey:true})!==TV.kbShiftDel)throw Error('DOS clipboard key codes are not mapped');
  source.setData('abcdef');source.focus();source.root.setSelectionRange(1,4);
  source.root.dispatchEvent(new KeyboardEvent('keydown',{key:'Insert',ctrlKey:true,bubbles:true,cancelable:true}));
 })()`);
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=async()=>{
  if(await navigator.clipboard.readText()==='bcd'){resolve();return;}
  if(Date.now()>end){reject(Error('Ctrl+Insert did not copy the selected text'));return;}setTimeout(()=>check().catch(reject),20);
 };check().catch(reject);})`);
 await evaluate(`destination.setData('12');destination.focus();destination.root.setSelectionRange(1,1);
  destination.root.dispatchEvent(new KeyboardEvent('keydown',{key:'Insert',shiftKey:true,bubbles:true,cancelable:true}));`);
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
  if(destination.getData()==='1bcd2'){resolve();return;}
  if(Date.now()>end){reject(Error('Shift+Insert did not paste at the cursor'));return;}setTimeout(check,20);
 };check();})`);
 await evaluate(`source.focus();source.root.setSelectionRange(1,4);
  source.root.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',shiftKey:true,bubbles:true,cancelable:true}));`);
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
  if(source.getData()==='aef'){resolve();return;}
  if(Date.now()>end){reject(Error('Shift+Delete did not cut the selected text'));return;}setTimeout(check,20);
 };check();})`);
 await evaluate(`(async()=>{
  numeric.setData('123');numeric.focus();numeric.selectAll();
  await navigator.clipboard.writeText('');if(await numeric.clipPaste()||numeric.getData()!=='123')throw Error('Empty clipboard removed selected text');
  await navigator.clipboard.writeText('letters');if(await numeric.clipPaste()||numeric.getData()!=='123')throw Error('Paste bypassed the numeric validator');
  await navigator.clipboard.writeText('456789');if(!await numeric.clipPaste()||numeric.getData()!=='4567')throw Error('Paste bypassed input maximum length');
  destination.setData('xy');destination.focus();destination.root.setSelectionRange(1,1);
  await navigator.clipboard.writeText('a\\r\\nb');await destination.clipPaste();
  if(destination.getData()!=='xaby')throw Error('Single-line paste kept line breaks');
  const clipboard=Object.getOwnPropertyDescriptor(navigator,'clipboard');
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>Promise.reject(Error('Denied'))}});
  try{source.setData('keep');source.focus();source.selectAll();
   let failed=false;try{await source.clipCut();}catch{failed=true;}
   if(!failed||source.getData()!=='keep')throw Error('A denied clipboard write destroyed input text');
  }finally{if(clipboard)Object.defineProperty(navigator,'clipboard',clipboard);else delete navigator.clipboard;}
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{readText:()=>new Promise(resolve=>window.finishRead=resolve)}});
  try{source.setData('unchanged');source.focus();source.selectAll();const task=source.clipPaste();destination.focus();finishRead('delayed');
   if(await task||source.getData()!=='unchanged')throw Error('Delayed Paste edited a control after focus changed');
  }finally{if(clipboard)Object.defineProperty(navigator,'clipboard',clipboard);else delete navigator.clipboard;}
  source.setData('native text');source.focus();source.selectAll();
 })()`);
 const modifier=await evaluate(`/mac|iphone|ipad/i.test(navigator.platform)?4:2`);
 const nativeKey=async(key,command)=>{
  await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:'Key'+key.toUpperCase(),windowsVirtualKeyCode:key.toUpperCase().charCodeAt(0),modifiers:modifier,commands:[command]});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:'Key'+key.toUpperCase(),modifiers:0});
 };
 await nativeKey('c','copy');
 if(!await evaluate(`navigator.clipboard.readText().then(text=>text==='native text'&&commandCount>0)`))throw Error('Native Copy did not use the system clipboard/TVEvent');
 await nativeKey('x','cut');
 if(!await evaluate(`source.getData()===''`))throw Error('Native Cut did not edit input');
 await nativeKey('v','paste');
 if(!await evaluate(`source.getData()==='native text'`))throw Error('Native Paste failed');
 await nativeKey('z','undo');
 if(!await evaluate(`source.getData()===''`))throw Error('Native clipboard actions lost the browser undo history');
 await evaluate(`(()=>{const TV=window.THelpViewerTV;
  dialog.close();window.editor=new TV.TVEditor(new TV.TVRect());
  const root=document.createElement('div');root.textContent='Read-only document';editor.bindRoot(root);desktop.insert(editor);root.focus();
  const range=document.createRange();range.selectNodeContents(root);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
  root.dispatchEvent(new KeyboardEvent('keydown',{key:'Insert',ctrlKey:true,bubbles:true,cancelable:true}));
 })()`);
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=async()=>{
  if(await navigator.clipboard.readText()==='Read-only document'){resolve();return;}
  if(Date.now()>end){reject(Error('Read-only editor DOS Copy failed'));return;}setTimeout(()=>check().catch(reject),20);
 };check().catch(reject);})`);
 await evaluate(`(async()=>{
  await navigator.clipboard.writeText('replacement');
  if(await editor.clipCut()||await editor.clipPaste()||editor.root.textContent!=='Read-only document')throw Error('Clipboard changed read-only document');
  editor.setReadOnly(false);if(!await editor.clipCut()||editor.root.textContent!=='')throw Error('Editable editor Cut failed');
  await navigator.clipboard.writeText('<b>plain text</b>');if(!await editor.clipPaste()||editor.root.textContent!=='<b>plain text</b>'||editor.root.querySelector('b'))throw Error('Editable Paste failed or inserted HTML');
  editor.destroy();dialog.destroy();
  const TV=window.THelpViewerTV;
  window.errorText='Download of Norton Commander 4.0 is rate limited (HTTP 429). Try again later; installed files are unchanged.';
  window.errorBox=new TV.TVMessageBox();desktop.insert(errorBox);void errorBox.show({title:'DOS Packages',lines:[errorText]});
  const restored=errorBox.messageViews.map(view=>view.text.slice(1)).join(' ');
  if(errorBox.messageViews.length<2||restored!==errorText)throw Error('Long download errors are truncated instead of wrapped');
  errorBox.messageViews.forEach(view=>{const row=view.root.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(view.root);
   const ink=range.getBoundingClientRect();if(ink.left<row.left-1||ink.right>row.right+1||row.bottom>errorBox.contentView.root.getBoundingClientRect().bottom)throw Error('Wrapped message text leaves its row/group');});
  errorBox.destroy();
 })()`);
 await send('Emulation.setDeviceMetricsOverride',{width:260,height:700,deviceScaleFactor:1,mobile:false});
 await evaluate(`(()=>{const TV=window.THelpViewerTV,box=new TV.TVMessageBox();desktop.insert(box);
  void box.show({lines:['VeryLongWordWithoutSpaces'.repeat(5),'Second paragraph\\nThird paragraph'],buttons:TV.TVMessageBox.MF_YES_NO_CANCEL|TV.TVMessageBox.MF_OK_BUTTON});
  if(box.messageViews.some(view=>Array.from(view.text.slice(1)).length>view.bounds.width)||box.buttonViews[2].bounds.y1===0)throw Error('Narrow MessageBox does not wrap words/buttons');
  const frame=box.dialog.getBoundingClientRect();if(frame.right>innerWidth||box.buttonViews.some(view=>view.root.getBoundingClientRect().right>frame.right))throw Error('Narrow MessageBox buttons leave the screen');
  box.destroy();
 })()`);
 socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
'''
        result = subprocess.run([NODE, "-e", script, debugging, url], capture_output=True, text=True, timeout=25)
        assert result.returncode == 0, result.stderr
    finally:
        if chrome:
            chrome.terminate()
            chrome.wait(timeout=5)
        server.terminate()
        server.wait(timeout=5)
