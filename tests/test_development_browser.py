"""A browser without WebAuthn can still use the explicitly local session."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_local_browser_auto_login_without_webauthn(tmp_path):
    port = _free_port()
    app_url = f"http://localhost:{port}/"
    manifest = tmp_path / "config.json"
    manifest.write_text('{"sources": [], "files": [{"path":"TEST.TXT","text":["shared test disk"]}]}')
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "THELP_STATE_DIR": str(tmp_path), "THELP_HELPS_DIR": str(tmp_path / "helps"),
             "THELP_STATISTICS_PATH": str(tmp_path / "statistics.sqlite3"),
             "THELP_AUTH_ORIGIN": app_url.rstrip("/"), "THELP_PUBLIC_BASE_URL": "",
             "THELP_DEV_AUTO_LOGIN": "1", "THELP_MIDI_SOURCES_PATH": str(manifest),
             "THELP_DOS_CONFIG_PATH": str(manifest)},
    )
    try:
        _wait_for_url(app_url + "healthz")
        with tempfile.TemporaryDirectory(prefix="thelp-dev-login-browser-") as profile:
            chrome = subprocess.Popen(
                [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                 "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0",
                 f"--user-data-dir={profile}", "about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                debugging_port = _wait_for_file(Path(profile) / "DevToolsActivePort").splitlines()[0]
                script = r'''
const [port,url]=process.argv.slice(1);
(async()=>{
 const target=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let next=0;const pending=new Map();
 socket.onmessage=event=>{const r=JSON.parse(String(event.data)),p=pending.get(r.id);if(!p)return;
  pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);};
 const send=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++next;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 await send('Page.enable');
 await send('Page.addScriptToEvaluateOnNewDocument',{source:
  `Object.defineProperty(navigator,'credentials',{value:undefined});`});
 for(let reload=0;reload<2;reload++){
  await send('Page.navigate',{url});
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+10000;const check=()=>{
   const title=document.querySelector('.tv-menu-right .tv-menu-button')?.textContent;
   if(title==='Local Administrator'&&document.querySelector('[data-tv-command="account-server-configuration"]')){resolve();return;}
   if(Date.now()>deadline){reject(Error('Development account menu did not load: '+title));return;}setTimeout(check,50);
  };check();})`);
  if(!await evaluate(`(async()=>{if(navigator.credentials)throw Error('WebAuthn was not disabled');
   const session=await(await fetch('/api/auth/session')).json();
   return session.authenticated&&session.user.role==='admin'&&(await fetch('/api/admin/settings')).ok;})()`))throw Error('Local browser session failed');
 }
 for(const resource of ['dos','midi']){
  await evaluate(`document.querySelector('[data-tv-command="account-rebuild-${resource}"]').click()`);
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
   const box=document.querySelector('.tv-msgbox-window');
   if(box&&!box.closest('.tv-dialog-overlay').hidden){resolve();return;}
   if(Date.now()>deadline){reject(Error('Rebuild confirmation did not open'));return;}setTimeout(check,30);
  };check();})`);
  // Closing the title control is cancellation, not permission to rebuild.
  await evaluate(`document.querySelector('.tv-msgbox-window .tv-dialog-close-control').click()`);
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
   const cfg=document.querySelector('.tv-server-configuration-window')?.closest('.tv-dialog-overlay')?._tvView;
   if(cfg&&!cfg.rebuildTask){resolve();return;}
   if(Date.now()>deadline){reject(Error('Cancelled rebuild stayed busy'));return;}setTimeout(check,30);
  };check();})`);
  if(!await evaluate(`(async()=>{const s=await(await fetch('/api/admin/rebuild/${resource}')).json();return !s.backup&&!s.rebuilding;})()`))throw Error('Cancelled rebuild replaced data');
  await evaluate(`document.querySelector('[data-tv-command="account-rebuild-${resource}"]').click()`);
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
   const box=document.querySelector('.tv-msgbox-window');
   if(box&&!box.closest('.tv-dialog-overlay').hidden){resolve();return;}
   if(Date.now()>deadline){reject(Error('Second confirmation did not open'));return;}setTimeout(check,30);
  };check();})`);
  await evaluate(`Array.from(document.querySelectorAll('.tv-msgbox-window [data-tv-command="msgbox-cmd"]')).find(b=>b.textContent.includes('OK')).click()`);
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+10000;const check=()=>{
   const cfg=document.querySelector('.tv-server-configuration-window')?.closest('.tv-dialog-overlay')?._tvView;
   if(cfg&&!cfg.rebuildTask&&cfg.status.root.textContent.includes('Rebuilt.')){resolve();return;}
   if(Date.now()>deadline){reject(Error('Rebuild did not finish: '+cfg?.status.root.textContent));return;}setTimeout(check,30);
  };check();})`);
  if(!await evaluate(`(async()=>{const s=await(await fetch('/api/admin/rebuild/${resource}')).json();return s.state==='ready'&&!s.rebuilding;})()`))throw Error('Rebuilt resource is not ready');
 }
 await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'F1',code:'F1',bubbles:true,cancelable:true}))`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+10000;const check=()=>{
  if(document.body.textContent.includes('Only the local development administrator has Rebuild DOS C')){resolve();return;}
  if(Date.now()>deadline){reject(Error('Configuration F1 did not open the updated native HELP topic'));return;}setTimeout(check,50);
 };check();})`);
 socket.close();
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
                result = subprocess.run([NODE, "-e", script, debugging_port, app_url],
                                        capture_output=True, text=True, timeout=40)
                assert result.returncode == 0, result.stderr
            finally:
                chrome.terminate()
                chrome.wait(timeout=5)
    finally:
        server.terminate()
        server.wait(timeout=5)
