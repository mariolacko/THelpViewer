"""Exercise a real WASM DOSBox, not just a fake command interface."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from thelpviewer.server.accounts.sessions import new_session
from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url
from thelpviewer.server.accounts.store import AccountStore
from thelpviewer.server.dos.store import DosPromptStore
from test_dos_prompt import floppy_image, cd_image


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Chrome and Node.js are required")
@pytest.mark.parametrize("blocked_worker", [False, True])
def test_dos_prompt_real_runtime_save_restart_and_secure_mounts(blocked_worker):
    with tempfile.TemporaryDirectory(prefix="thelp-dos-browser-") as temporary:
        root = Path(temporary)
        # DOS interaction must not race a modal rebuild of the developer's
        # unrelated full HELP library. Index behavior has separate coverage.
        helps = root / "helps"
        helps.mkdir()
        (helps / "catalog.json").write_text("[]\n", encoding="utf-8")
        docs = root / "docs"
        docs.mkdir()
        (root / "config.json").write_text('{"sources": [], "memory_mb":64, "max_c_bytes":268435456, "allow_full_disk_fallback": true, "files": [{"path":"README.TXT","text":["Shared test disk"]}]}')
        accounts = AccountStore(root / "var")
        accounts.create_user("player")
        # This fixture is an already configured DOS server, not first-run setup.
        (root / "var" / "content-settings.json").write_text(json.dumps({
            "configured": True, "help_groups": [], "dos_packages": [],
        }), encoding="utf-8")
        with accounts._connect() as database:
            ident = database.execute("SELECT id FROM accounts WHERE username='player'").fetchone()[0]
            token = new_session(database, ident)
        store = DosPromptStore(root / "var" / "dos", root / "config.json")
        store.prepare()
        extra_game = os.environ.get("THELP_DOS_TEST_GAME", "")
        extra_software = os.environ.get("THELP_DOS_TEST_SOFTWARE", "")
        if extra_software:
            prepared = Path(os.environ["THELP_DOS_TEST_C_DIR"])
            shutil.copytree(prepared / extra_software, store.disk_dir / extra_software, dirs_exist_ok=True)
        audio_test = extra_game == "DOOM" and os.environ.get("THELP_DOS_TEST_AUDIO") == "1"
        if os.environ.get("THELP_DOS_TEST_INSTALLED_GAMES") == "1" or extra_game:
            # Optional local smoke test against the actually prepared public disk.
            prepared = Path(__file__).resolve().parents[1] / "var" / "dos" / "c"
            for name in ([extra_game] if extra_game else ["BLKDROP", "SUDOKU86", "ZMIY"]):
                shutil.copytree(prepared / "GAMES" / name, store.root / "base" / "c" / "GAMES" / name, dirs_exist_ok=True)
            if audio_test:
                # Isolated test disk only: settings produced by DOOM's SETUP.
                cfg = store.root / "base" / "c" / "GAMES" / "DOOM" / "DEFAULT.CFG"
                configured = cfg.read_bytes()
                for old, new in ((b"snd_musicdevice\t\t0", b"snd_musicdevice\t\t3"),
                                 (b"snd_sfxdevice\t\t0", b"snd_sfxdevice\t\t3"),
                                 (b"snd_sbirq\t\t-1", b"snd_sbirq\t\t7"),
                                 (b"snd_sbdma\t\t-1", b"snd_sbdma\t\t1")):
                    assert old in configured
                    configured = configured.replace(old, new)
                cfg.write_bytes(configured)
        # BIOS mode 13h: fill all 320x200 pixels red, wait for a key, restore text.
        (store.root / "base" / "c" / "GFX.COM").write_bytes(bytes.fromhex(
            "b81300cd10b800a08ec031ffb900fab004f3aa31c0cd16b80300cd10cd20"))
        nested = store.root / "base" / "c" / "FREEDOS" / "APPINFO"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "TEST.LSM").write_bytes(b"nested software metadata\r\n")
        (store.root / "base" / "c" / "UNUSED.DAT").write_bytes(bytes(3 * 1024 * 1024))
        media_id = store.add_media(ident, "floppy", floppy_image())
        cd_id = store.add_media(ident, "cd", cd_image())
        port = _free_port()
        url = f"http://127.0.0.1:{port}/"
        server_log = (root / "server.log").open("w")
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"],
            stdout=server_log, stderr=subprocess.DEVNULL,
            env={**os.environ, "THELP_STATE_DIR": str(root / "var"),
                "THELP_HELPS_DIR": str(helps), "THELP_DOCS_DIR": str(docs),
                "THELP_STATISTICS_PATH": str(root / "var" / "statistics.sqlite3"),
                "THELP_DOS_CONFIG_PATH": str(root / "config.json"),
                "THELP_MIDI_SOURCES_PATH": str(root / "config.json"),
                "THELP_AUTH_ORIGIN": url.rstrip("/")},
        )
        chrome = None
        try:
            _wait_for_url(url + "healthz")
            chrome = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
                "--autoplay-policy=no-user-gesture-required", "--no-first-run", "--no-default-browser-check",
                "--remote-debugging-port=0", "--user-data-dir=" + str(root / "chrome"), "about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            debugging = _wait_for_file(root / "chrome" / "DevToolsActivePort").splitlines()[0]
            script = r'''
const [port, url, token, mediaId, cdId, blockedWorker, installedGames, extraGame, gameCommand, audioTest, softwarePath, softwareCommand, screenshotPath, softwareOutput] = process.argv.slice(1);
(async () => {
 const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method:'PUT'})).json();
 const socket = new WebSocket(target.webSocketDebuggerUrl);
 await new Promise(resolve => socket.addEventListener('open', resolve, {once:true}));
 let seq=0;const pending=new Map();const errors=[];const fileRequests=[];
 socket.addEventListener('message', event => {
  const m=JSON.parse(String(event.data));
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
  if(m.method==='Runtime.consoleAPICalled')console.error(m.params.args.map(arg=>arg.value||arg.description).join(' '));
  if(m.method==='Log.entryAdded')console.error('Browser log:',m.params.entry.text,m.params.entry.url||'');
  if(m.method==='Network.requestWillBeSent'&&m.params.request.url.includes('/api/dos/file?'))fileRequests.push(m.params.request.url);
  if(pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);}
 });
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>reject(new Error('Timed out: '+method+' '+params.expression)),installedGames==='true'?60000:35000);pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async (expression,userGesture=false)=>{
  const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture});
  if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
  return r.result.value;
 };
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');
 await send('Network.setCookie',{name:'thelp_session',value:token,url,httpOnly:true});
 if(blockedWorker==='true')await send('Page.addScriptToEvaluateOnNewDocument',{source:`window.Worker=class{constructor(){throw new DOMException('Worker blocked by embedded browser','SecurityError');}};window.AudioContext=class{constructor(){throw new DOMException('Audio blocked by embedded browser','NotAllowedError');}};`});
 await send('Page.navigate',{url});await send('Page.bringToFront');
 await evaluate(`new Promise((resolve,reject)=>{
  const deadline=Date.now()+15000;const check=()=>{
   const button=document.querySelector('[data-tv-command="dos-open"]');
   if(button){button.click();resolve(true);return;}
   if(Date.now()>deadline){reject(new Error('DOS menu missing'));return;}setTimeout(check,50);
  };check();
 })`);
 await evaluate(`new Promise((resolve,reject)=>{
  const deadline=Date.now()+30000;const check=()=>{
   const root=document.querySelector('.tv-dos-window');
   const view=root?._tvWindowView;
   if(view?.view.ci&&!view.busy){window.dos=view;resolve(true);return;}
   if(Date.now()>deadline){reject(new Error('DOS boot failed: '+root?.textContent));return;}setTimeout(check,100);
  };check();
 })`);
 await evaluate(`(()=>{
  dos.owner.dialogManager.open('calc');
  const root=dos.root,left=root.querySelector('.tv-border-side-left'),right=root.querySelector('.tv-border-side-right');
  if(!root.classList.contains('is-window-inactive')||left.getAttribute('data-tv-border-side')!=='│'
   ||right.getAttribute('data-tv-border-side')!=='│'||!right.textContent.includes('│'))throw new Error('Passive DOS frame sides differ');
  if(getComputedStyle(left).color!==getComputedStyle(right).color)throw new Error('Passive DOS side colors differ');
  dos.owner.dialogManager.close('calc');
  if(root.classList.contains('is-window-inactive')||left.getAttribute('data-tv-border-side')!=='║'
   ||right.getAttribute('data-tv-border-side')!=='║')throw new Error('Active DOS frame was not restored');
  const mover=root._tvResizer,before=mover.captureGeometry();
  mover.lastMoveDown=0;
  root.querySelector('.tv-window-caption').dispatchEvent(new MouseEvent('mousedown',{clientX:100,clientY:100,bubbles:true,cancelable:true}));
  const maxLeft=mover.moveState.maxLeft,maxTop=mover.moveState.maxTop;
  for(let i=0;i<50;i++)document.dispatchEvent(new MouseEvent('mousemove',{clientX:110+i,clientY:110+i,bubbles:true}));
  if(mover.captureGeometry().left!==before.left)throw new Error('Move positions were not coalesced');
  document.dispatchEvent(new MouseEvent('mouseup',{clientX:116,clientY:132,bubbles:true}));
  const after=mover.captureGeometry();
  if(after.left!==Math.min(maxLeft,before.left+16)||after.top!==Math.min(maxTop,before.top+32)
   ||root.classList.contains('is-moving')||mover.moveFrame!==null)throw new Error('DOS drag did not commit mouse-up position');
  mover.place(before);
 })()`);
 const result=await evaluate(`(async()=>{
  const canvas=dos.view.canvas;
  console.log('DOS flags',dos.active,dos.paused,document.hidden,canvas.width,canvas.height,dos.view.owner===dos,dos.view.listeners.length);
  await new Promise(r=>setTimeout(r,1000));
  dos.view.ci.events().onStdout(text=>console.log('DOS stdout: '+text));
  const frameOkay=!dos.root.querySelector('.tv-scrollbar')&&getComputedStyle(canvas).backgroundColor==='rgb(0, 0, 0)';
  const bottom=dos.root.querySelector('.tv-bottom-bar');
  const bottomFill=bottom.querySelector('.tv-border-fill:not(.tv-control-gap)');
  const bottomOkay=bottomFill.getBoundingClientRect().width>bottom.getBoundingClientRect().width*0.8
   &&bottomFill.textContent.includes('═')
   &&Math.abs(bottom.querySelector('.tv-grow-handle').getBoundingClientRect().right-bottom.getBoundingClientRect().right)<1;
  const allBlack=[dos.root,dos.root.querySelector('.tv-border-top'),bottom,dos.root.querySelector('.tv-frame')]
   .every(el=>getComputedStyle(el).backgroundColor==='rgb(0, 0, 0)');
  const nestedLoaded=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/FREEDOS/APPINFO/TEST.LSM')).includes('nested software');
  const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
  const rendered=pixels.some((value,index)=>index%4!==3&&value>0);
  async function command(text){
   canvas.focus();
   for(const char of text){
    const shifted=char==='>'||char===':';
    const code=char==='>'?'Period':char===' '?'Space':char==='.'?'Period':char==='/'?'Slash':char===':'?'Semicolon':char==='-'?'Minus':char.charCodeAt(0)===92?'Backslash':/^[0-9]$/.test(char)?'Digit'+char:'Key'+char.toUpperCase();
    if(shifted)canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift',code:'ShiftLeft',bubbles:true,cancelable:true}));
    for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:char,code,shiftKey:shifted,bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
    if(shifted)canvas.dispatchEvent(new KeyboardEvent('keyup',{key:'Shift',code:'ShiftLeft',bubbles:true,cancelable:true}));
    await new Promise(r=>setTimeout(r,25));
   }
   for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
   await new Promise(r=>setTimeout(r,250));
  }
  window.dosCommand=command;
  if(${JSON.stringify(softwarePath)}){
   await command('cd '+String.fromCharCode(92)+${JSON.stringify(softwarePath)}.replaceAll('/',String.fromCharCode(92)).toLowerCase());
   const before=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
   const commands=${JSON.stringify(softwareCommand)};
   for(const line of (commands.startsWith('[')?JSON.parse(commands):[commands])){await command(line);}
   await new Promise(resolve=>setTimeout(resolve,2000));
   if(${JSON.stringify(softwareOutput)}){
    const output=await Promise.race([
     dos.view.ci.fsReadFile('drive_c/'+${JSON.stringify(softwarePath)}+'/'+${JSON.stringify(softwareOutput)}),
     new Promise((_,reject)=>setTimeout(()=>reject(Error('Missing software output: '+${JSON.stringify(softwareOutput)})),5000))
    ]);
    if(!output.length)throw Error('Software produced empty output');
    return {smokeOnly:true,software:${JSON.stringify(softwarePath)},outputBytes:output.length,
     outputText:${JSON.stringify(softwareOutput)}.endsWith('.LOG')?new TextDecoder().decode(output):undefined};
   }
   const running=await dos.view.ci.getRunningProgram();
   const after=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
   const changed=after.some((value,index)=>index%4!==3&&value!==before[index]);
   if(!changed||!running||running.toUpperCase().includes('COMMAND.COM')){
    let log='';try{log=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/'+${JSON.stringify(softwarePath)}+'/BUILD.LOG'));}catch{}
    throw Error('Software did not start: '+running+' '+log);
   }
   return {smokeOnly:true,software:${JSON.stringify(softwarePath)},running,rendered:true};
  }
  let audibleSamples=0;
  const playSound=dos.playSound.bind(dos);
  dos.playSound=samples=>{if(samples.some(value=>Math.abs(value)>0.001))audibleSamples+=samples.length;playSound(samples);};
  if(${JSON.stringify(audioTest)}==='true'){
   await command('set >blaster.txt');
   const environment=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/BLASTER.TXT'));
   if(!/BLASTER=A220 I7 D1 H5 T6/i.test(environment))throw new Error('Default BLASTER environment missing: '+environment);
  }
  if(${JSON.stringify(installedGames)}==='true'||${JSON.stringify(extraGame)}){
   for(const name of (${JSON.stringify(extraGame)}?[${JSON.stringify(extraGame)}]:['BLKDROP','SUDOKU86','ZMIY'])){
    await command('cd '+String.fromCharCode(92)+'games'+String.fromCharCode(92)+name.toLowerCase());
    const before=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
    await command((${JSON.stringify(extraGame)}?${JSON.stringify(gameCommand)}:name).toLowerCase());
    if(${JSON.stringify(audioTest)}==='true'){
     await new Promise((resolve,reject)=>{const deadline=Date.now()+10000;const check=()=>{
      if(audibleSamples>0&&dos.audio?.state==='running'){resolve(true);return;}
      if(Date.now()>deadline){reject(new Error('Configured DOOM produced no audio'));return;}setTimeout(check,100);
     };check();});
    }
    if(name==='DMASTER'){
     // The original launcher asks for the display mode before starting the game.
     for(const type of ['keydown','keyup']){
      canvas.dispatchEvent(new KeyboardEvent(type,{key:'1',code:'Digit1',bubbles:true,cancelable:true}));
      await new Promise(r=>setTimeout(r,50));
     }
     await new Promise(r=>setTimeout(r,1000));
    }
    const after=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
    if(!after.some((value,index)=>index%4!==3&&value!==before[index]))throw new Error('Installed game did not draw: '+name);
    // The official direct transport synchronously clears getRunningProgram's
    // promise before returning it. Test the shell remains occupied instead.
    if(${JSON.stringify(blockedWorker)}!=='true'){
     const program=await dos.view.ci.getRunningProgram();
     if(!program||program.toUpperCase().includes('COMMAND.COM'))throw new Error('Installed game did not start: '+name+' ('+program+')');
    }
    await command('echo game-ended>probe.txt');
    const directory=(await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_c').nodes
     .find(node=>node.name.toUpperCase()==='GAMES').nodes.find(node=>node.name.toUpperCase()===name);
    if(directory.nodes.some(node=>node.name.toUpperCase()==='PROBE.TXT'))throw new Error('Installed game returned to the shell: '+name);
    if(${JSON.stringify(extraGame)}){await dos.stop(false);return {smokeOnly:true,game:name,rendered:true};}
    await dos.restart();
   }
  }
  await command('gfx');
  await new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
   const pixel=canvas.getContext('2d').getImageData(100,100,1,1).data;
   if(canvas.width===320&&canvas.height===200&&pixel[0]>100&&pixel[1]===0&&pixel[2]===0){resolve(true);return;}
   if(Date.now()>deadline){reject(new Error('DOS VGA graphics were not rendered'));return;}setTimeout(check,50);
  };check();});
  const graphics=true;
  for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
  await new Promise(r=>setTimeout(r,200));
  await command('echo hello>state.txt');
  console.log('DOS check: keyboard');
  console.log(JSON.stringify(await dos.view.ci.fsTree()));
  if(!(await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_c').nodes.some(node=>node.name.toUpperCase()==='STATE.TXT'))throw new Error('Keyboard did not create STATE.TXT');
  const text=await dos.view.ci.fsReadFile('drive_c/STATE.TXT');
  if(!new TextDecoder().decode(text).toLowerCase().includes('hello'))throw new Error('DOS keyboard did not create STATE.TXT');
  await command('mount d / >mount.txt');
  const mount=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/MOUNT.TXT'));
  if(!/secure/i.test(mount))throw new Error('MOUNT was not blocked: '+mount);
  await command('imgmount e missing.iso -t iso >image.txt');
  const image=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/IMAGE.TXT'));
  if(!/secure/i.test(image))throw new Error('IMGMOUNT was not blocked: '+image);
  await command('boot no.img >boot.txt');
  const boot=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/BOOT.TXT'));
  if(!/secure/i.test(boot))throw new Error('BOOT was not blocked: '+boot);
  await command('del readme.txt');
  await dos.save();
  if(dos.status.root.textContent.includes('C drive saved to cloud'))throw new Error('Successful save overlays the DOS screen');
  console.log('DOS check: saved');
  const revision=dos.session.revision;
  const pause=document.querySelector('[data-tv-command="dos-pause"]');pause.click();
  const paused=dos.paused;
  document.querySelector('[data-tv-command="dos-pause"]').click();
  await dos.restart(${JSON.stringify(mediaId)});
  console.log('DOS check: restarted');
  const restored=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/STATE.TXT')).toLowerCase().includes('hello');
  await command('ren state.txt renamed.txt');
  await dos.save();await dos.save();
  const renamed=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/RENAMED.TXT')).toLowerCase().includes('hello');
  if(!renamed)throw new Error('Renaming an unread private file lost its contents');
  await command('copy a:'+String.fromCharCode(92)+'approved.txt c:'+String.fromCharCode(92)+'media.txt');
  const mounted=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/MEDIA.TXT')).includes('approved media');
  await dos.restart(${JSON.stringify(cdId)});
  await command('copy d:'+String.fromCharCode(92)+'approved.txt c:'+String.fromCharCode(92)+'cd.txt');
  const cdMounted=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/CD.TXT')).includes('approved cd');
  const deleted=!(await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_c').nodes.some(node=>node.name.toUpperCase()==='README.TXT');
  return {frameOkay,bottomOkay,allBlack,nestedLoaded,rendered,graphics,paused,restored,deleted,mounted,cdMounted,revision,account:dos.session.account,mount};
 })()`);
 if(result.smokeOnly){
  if(screenshotPath){const capture=await send('Page.captureScreenshot',{format:'png'});require('node:fs').writeFileSync(screenshotPath,Buffer.from(capture.data,'base64'));}
  console.log(JSON.stringify(result));socket.close();return;
 }
 if(!result.frameOkay||!result.bottomOkay||!result.allBlack||!result.nestedLoaded||!result.rendered||!result.paused||!result.restored||!result.deleted||!result.mounted||!result.cdMounted||result.revision<1||result.account!=='player'||errors.length){throw new Error(JSON.stringify({result,errors}));}
 await evaluate(`(()=>{
  const before=dos.root._tvResizer.captureGeometry(),r=dos.root.getBoundingClientRect();
  document.querySelector('[data-tv-command="dos-zoom"]').click();
  const after=dos.root.getBoundingClientRect(),desktop=dos.root._tvResizer.desktop.getBoundingClientRect();
  if(!dos.zoomGeometry||after.width<r.width||after.height<r.height||after.right>desktop.right+1||after.bottom>desktop.bottom+1)throw new Error('DOS zoom failed to fit the desktop: '+JSON.stringify({before,window:r.toJSON(),after:after.toJSON(),desktop:desktop.toJSON(),zoomGeometry:dos.zoomGeometry}));
  if(!document.querySelector('[data-tv-command="dos-zoom"]').textContent.includes('Zoom back'))throw new Error('DOS zoom menu did not update');
  document.querySelector('[data-tv-command="dos-zoom"]').click();
  if(dos.zoomGeometry||JSON.stringify(dos.root._tvResizer.captureGeometry())!==JSON.stringify(before))throw new Error('DOS Zoom back did not restore geometry');
 })()`);
 await evaluate(`dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',altKey:true,bubbles:true,cancelable:true}))`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  const r=dos.view.canvas.getBoundingClientRect();
  if(document.fullscreenElement===dos.view.canvas&&!dos.root.classList.contains('is-maximized')&&Math.abs(r.width-innerWidth)<1&&Math.abs(r.height-innerHeight)<1){resolve(true);return;}if(Date.now()>deadline){reject(new Error('Native canvas fullscreen failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`(()=>{const key=()=>dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Pause',code:'Pause',altKey:true,bubbles:true,cancelable:true}));key();if(!dos.paused)throw new Error('Alt-Pause did not pause DOS');key();if(dos.paused)throw new Error('Alt-Pause did not resume DOS');})()`);
 await evaluate(`document.exitFullscreen()`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(!document.fullscreenElement&&!dos.root.classList.contains('is-maximized')){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen restore failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',altKey:true,bubbles:true,cancelable:true}))`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(document.fullscreenElement===dos.view.canvas){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen re-entry failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'r',code:'KeyR',ctrlKey:true,altKey:true,bubbles:true,cancelable:true}))`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(!document.fullscreenElement&&dos.confirmation?.isOpen()){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Restart shortcut did not show a visible confirmation'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`Array.from(document.querySelectorAll('.tv-msgbox-window [data-tv-command="msgbox-cmd"]')).find(button=>button.textContent.includes('Cancel')).click()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(!dos.confirmation&&dos.view.ci){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Cancelled shortcut restart stopped DOS'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',altKey:true,bubbles:true,cancelable:true}))`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(document.fullscreenElement===dos.view.canvas){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen after cancelling restart failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`(async()=>{await dos.restart();if(document.fullscreenElement!==dos.view.canvas)throw new Error('Restart lost DOS fullscreen');})()`);
 await evaluate(`(()=>{dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'m',code:'KeyM',ctrlKey:true,altKey:true,bubbles:true,cancelable:true}));})()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  const menu=document.querySelector('[data-tv-menu-bar] .tv-menu-popup:not([hidden])');
  if(!document.fullscreenElement&&menu&&menu.getBoundingClientRect().height>0){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('DOS menu shortcut did not leave fullscreen'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.click()`);
 await evaluate(`document.querySelector('[data-tv-command="dos-fullscreen"]').click()`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(document.fullscreenElement===dos.view.canvas){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen before EXIT failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`(async()=>{dos.view.ci.events().onStdout(text=>console.log('EXIT stdout: '+text));console.log('EXIT flags',dos.active,dos.paused,document.hidden);await dosCommand('echo exit-save>exit.txt');await dosCommand('exit');})()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(!dos.view.ci){resolve(true);return;}if(Date.now()>deadline){reject(new Error('Native EXIT did not finish; saving='+!!dos.saving+',snapshotting='+dos.snapshotting));return;}setTimeout(check,50);
 };check();})`);
 if(await evaluate(`Boolean(document.fullscreenElement)`))throw new Error('EXIT left the stopped DOS canvas fullscreen');
 await evaluate(`dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'m',code:'KeyM',ctrlKey:true,altKey:true,bubbles:true,cancelable:true}))`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  const menu=document.querySelector('[data-tv-menu-bar] .tv-menu-popup:not([hidden])');
  if(menu&&menu.getBoundingClientRect().height>0){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Stopped DOS cannot open its control menu'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.click()`);
 const exitSaved=await evaluate(`(async()=>{await dos.restart();return new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/EXIT.TXT')).includes('exit-save');})()`);
 if(!exitSaved)throw new Error('Native EXIT lost the last C drive change');
 if(blockedWorker!=='true'){
  const tree=await evaluate(`(async()=>{return JSON.parse(new TextDecoder().decode(await dos.view.ci.fsReadFile('.jsdos/file-state.json')));})()`);
  if(!tree.remote.includes('UNUSED.DAT'))throw new Error('DOS was not using the file-on-demand provider');
  if(fileRequests.some(url=>new URL(url).searchParams.get('name')==='UNUSED.DAT'))throw new Error('Unused shared C file was downloaded during boot or save');
 }
 await evaluate(`document.querySelector('[data-tv-command="dos-pause"]').click()`);
 const hash=await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  const raw=location.hash.slice('#tv=1.'.length).replace(/-/g,'+').replace(/_/g,'/');
  let state;try{state=JSON.parse(atob(raw));}catch{}
  if(state?.w.some(item=>item.t==='dos'&&item.p===true)){resolve(location.hash);return;}
  if(Date.now()>deadline){reject(new Error('DOS missing from URL state'));return;}setTimeout(check,50);
 };check();})`);
 const loaded=new Promise(resolve=>{const listener=event=>{
  if(JSON.parse(String(event.data)).method==='Page.loadEventFired'){socket.removeEventListener('message',listener);resolve();}
 };socket.addEventListener('message',listener);});
 await send('Page.reload');await loaded;
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+30000;const check=()=>{
  const view=document.querySelector('.tv-dos-window')?._tvWindowView;
  if(view?.view.ci&&!view.busy&&view.paused){window.dos=view;resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('DOS URL restore failed'));return;}setTimeout(check,100);
 };check();})`);
 const geometry=JSON.parse(Buffer.from(hash.slice('#tv=1.'.length),'base64url').toString()).w.find(item=>item.t==='dos').g;
 const restoredGeometry=await evaluate(`(()=>{const s=getComputedStyle(dos.root);return ['--tv-window-left','--tv-window-top','--tv-window-cols','--tv-window-rows'].map(key=>Math.round(parseFloat(s.getPropertyValue(key))));})()`);
 if(JSON.stringify(restoredGeometry)!==JSON.stringify(geometry.slice(0,4)))throw new Error('DOS window geometry was not restored');
 const stats=await evaluate(`(async()=>{return await (await fetch('/api/statistics/summary')).json();})()`);
 if(!stats.tool.some(row=>row.value==='dos-prompt'&&row.count===2)||!stats.tool_duration.some(row=>row.value.startsWith('dos-prompt · '))){throw new Error('DOS statistics missing: '+JSON.stringify({stats,errors}));}
 const closePoint=await evaluate(`(()=>{const r=dos.root.querySelector('.tv-close-control').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...closePoint});
 if(!await evaluate(`dos.root.isConnected`))throw new Error('DOS closed before mouse release');
 await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...closePoint});
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(!document.querySelector('.tv-dos-window')){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS close failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(!location.hash.includes('tv=1.')){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Closed DOS remained in URL'));return;}setTimeout(check,50);
 };check();})`);
 console.log(JSON.stringify(result));socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
'''
            installed_games = str(os.environ.get("THELP_DOS_TEST_INSTALLED_GAMES") == "1").lower()
            game_command = extra_game
            if extra_game:
                sources = json.loads(Path("thelpviewer/config/dos-prompt.json").read_text())["sources"]
                launch = next(source["launch"] for source in sources if f"\\GAMES\\{extra_game} then " in source.get("launch", ""))
                game_command = launch.split(" then ", 1)[1]
            result = subprocess.run([NODE, "-e", script, debugging, url, token, media_id, cd_id, str(blocked_worker).lower(), installed_games, extra_game, game_command, str(audio_test).lower(),
                extra_software, os.environ.get("THELP_DOS_TEST_SOFTWARE_COMMAND", "start"), os.environ.get("THELP_DOS_TEST_SCREENSHOT", ""), os.environ.get("THELP_DOS_TEST_SOFTWARE_OUTPUT", "")], capture_output=True, text=True, timeout=90)
            assert result.returncode == 0, result.stderr
            if extra_software:
                print(result.stdout)
            if not blocked_worker and not extra_game and not extra_software:
                trace = (root / "server.log").read_text()
                assert "name=GFX.COM" in trace
                assert "name=UNUSED.DAT" not in trace
        finally:
            for process in (chrome, server):
                if process:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=5)
            server_log.close()
