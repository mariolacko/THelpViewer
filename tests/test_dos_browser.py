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
@pytest.mark.parametrize("blocked_worker,text_rendering", [(False, True), (True, True), (False, False)])
def test_dos_prompt_real_runtime_save_restart_and_browser_mounts(blocked_worker, text_rendering):
    with tempfile.TemporaryDirectory(prefix="thelp-dos-browser-") as temporary:
        root = Path(temporary).resolve()
        # DOS interaction must not race a modal rebuild of the developer's
        # unrelated full HELP library. Index behavior has separate coverage.
        helps = root / "helps"
        helps.mkdir()
        (helps / "catalog.json").write_text("[]\n", encoding="utf-8")
        docs = root / "docs"
        docs.mkdir()
        (root / "config.json").write_text(json.dumps({"sources": [], "memory_mb": 64,
            "allow_full_disk_fallback": True, "text_rendering": text_rendering,
            "files": [{"path": "README.TXT", "text": ["Shared test disk"]}]}))
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
        # BIOS mode 12h: 640x480 with a red last pixel; wait, then restore text.
        (store.root / "base" / "c" / "GFX480.COM").write_bytes(bytes.fromhex(
            "b81200cd10b8040c31dbb97f02badf01cd1031c0cd16b80300cd10cd20"))
        # Direct B800 writes, not DOS stdout: 'A' and a CP437 full block.
        (store.root / "base" / "c" / "TEXTMEM.COM").write_bytes(bytes.fromhex(
            "b800b88ec026c7060000411f26c7060200db2e31c0cd16b80300cd10cd20"))
        # Standard ROM 8x8 font switches an 80-column mode to 50 text rows.
        (store.root / "base" / "c" / "TEXT50.COM").write_bytes(bytes.fromhex(
            "b8121131dbcd1031c0cd16b80300cd10cd20"))
        # BIOS uploads a custom solid glyph for A, paints it, waits, then restores
        # the ROM font. The browser must never substitute CP437 for this glyph.
        custom = bytearray.fromhex(
            "0e07b81011bb0010b90100ba4100bd0000cd10b800b88ec026c7060000411f31c0cd16b80300cd10cd20")
        custom[15:17] = (0x100 + len(custom)).to_bytes(2, "little")
        (store.root / "base" / "c" / "CUSTOM.COM").write_bytes(custom + b"\xff" * 16)
        # Set the BIOS NumLock flag in this isolated test, independent of host LEDs.
        (store.root / "base" / "c" / "NUMON.COM").write_bytes(bytes.fromhex(
            "1eb840008ed8800e1700201fc3"))
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
const [port, url, token, mediaId, cdId, blockedWorker, installedGames, extraGame, gameCommand, audioTest, softwarePath, softwareCommand, screenshotPath, softwareOutput, textRendering] = process.argv.slice(1);
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
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>reject(new Error('Timed out: '+method+' '+params.expression)),90000);pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async (expression,userGesture=false)=>{
  const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture});
  if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);
  return r.result.value;
 };
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('Log.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
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
  root.querySelector('.tv-window-caption').dispatchEvent(new MouseEvent('mousedown',{clientX:100,clientY:100,buttons:1,bubbles:true,cancelable:true}));
  const maxLeft=mover.moveState.maxLeft,maxTop=mover.moveState.maxTop;
  for(let i=0;i<50;i++)document.dispatchEvent(new MouseEvent('mousemove',{clientX:110+i,clientY:110+i,buttons:1,bubbles:true}));
  if(mover.captureGeometry().left!==before.left)throw new Error('Move positions were not coalesced');
  document.dispatchEvent(new MouseEvent('mouseup',{clientX:116,clientY:132,bubbles:true}));
  const after=mover.captureGeometry();
  if(after.left!==Math.min(maxLeft,before.left+16)||after.top!==Math.min(maxTop,before.top+32)
   ||root.classList.contains('is-moving')||mover.moveFrame!==null)throw new Error('DOS drag did not commit mouse-up position');
  mover.place(before);
 })()`);
 // Send the complete real mouse sequence, not just a synthetic dblclick. The
 // mover must not maximize on the second mousedown before TVWindow zooms.
 const initialGeometry=await evaluate(`dos.root._tvResizer.captureGeometry()`);
 for(let cycle=0;cycle<2;cycle++){
  const point=await evaluate(`(()=>{const r=dos.root.querySelector('.tv-window-caption').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
  for(const clickCount of [1,2]){
   await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount,...point});
   await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount,...point});
  }
  await evaluate(`(()=>{
   if(dos.root.classList.contains('is-maximized')||Boolean(dos.zoomGeometry)!==${cycle===0})throw Error('Double-click bypassed DOS proportional Zoom');
   const rect=dos.view.root.getBoundingClientRect(),ratio=dos.view.canvas.height/dos.view.canvas.width;
   if(rect.height<rect.width*ratio-1||rect.height-rect.width*ratio>17)throw Error('Double-click stretched DOS screen');
  })()`);
 }
 const doubleClickGeometry=await evaluate(`dos.root._tvResizer.captureGeometry()`);
 if(JSON.stringify(doubleClickGeometry)!==JSON.stringify(initialGeometry))throw Error('Double-click Zoom back lost geometry');
 const result=await evaluate(`(async()=>{
  const canvas=dos.view.canvas;
  console.log('DOS flags',dos.active,dos.paused,document.hidden,canvas.width,canvas.height,dos.view.owner===dos,dos.view.listeners.length);
  await new Promise(r=>setTimeout(r,1000));
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
  const rendered=dos.view.textMode ? dos.view.textScreen.root.textContent.includes('C:') : pixels.some((value,index)=>index%4!==3&&value>0);
  async function command(text,keypad=false){
   if(window.commandCi!==dos.view.ci){window.commandCi=dos.view.ci;dos.view.ci.events().onStdout(text=>console.log('DOS command stdout: '+text));}
   dos.view.focus();
   for(const char of text){
    while(dos.snapshotting||dos.busy){await new Promise(r=>setTimeout(r,20));}
    const shifted=char==='>'||char===':'||char==='_';
    const keypadCode=keypad?({'.':'NumpadDecimal','/':'NumpadDivide','*':'NumpadMultiply','-':'NumpadSubtract','+':'NumpadAdd'}[char]||(/^[0-9]$/.test(char)?'Numpad'+char:'')):'';
    const code=keypadCode||(char==='>'?'Period':char===' '?'Space':char==='.'?'Period':char==='/'?'Slash':char===':'?'Semicolon':char==='-'||char==='_'?'Minus':char.charCodeAt(0)===92?'Backslash':/^[0-9]$/.test(char)?'Digit'+char:'Key'+char.toUpperCase());
    if(shifted)canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Shift',code:'ShiftLeft',bubbles:true,cancelable:true}));
    for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:char,code,shiftKey:shifted,bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
    if(shifted)canvas.dispatchEvent(new KeyboardEvent('keyup',{key:'Shift',code:'ShiftLeft',bubbles:true,cancelable:true}));
    await new Promise(r=>setTimeout(r,25));
   }
   for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:keypad?'NumpadEnter':'Enter',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
   await new Promise(r=>setTimeout(r,250));
  }
  window.dosCommand=command;
  await command('custom');
  await new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
   const p=canvas.getContext('2d').getImageData(0,0,8,16).data;
   if(!dos.view.textMode&&!canvas.hidden&&p.every((v,i)=>i%4===3||v===255)){resolve();return;}
   if(Date.now()>end){reject(Error('Custom DOS font did not retain native pixel rendering: '+JSON.stringify({text:dos.view.textMode,hidden:canvas.hidden,pixels:Array.from(p.slice(0,32)),width:canvas.width,height:canvas.height})));return;}setTimeout(check,30);
  };check();});
  await command('');
  if(${JSON.stringify(textRendering)}==='false'){
   await new Promise(resolve=>setTimeout(resolve,250));
   if(dos.session.text_rendering!==false||dos.view.textMode||canvas.hidden
    ||!canvas.getContext('2d').getImageData(0,0,640,400).data.some((v,i)=>i%4!==3&&v>0))
    throw Error('Configured canvas-only rendering did not display DOS text');
   await dos.stop(false);return {smokeOnly:true,canvasOnly:true};
  }
  if(!dos.view.textMode||!canvas.hidden||dos.view.textScreen.owner!==dos.view)
   throw Error('Standard DOS text was not rendered by the shared character view');
  await command('textmem');
  await new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
   const screen=dos.view.textScreen.screen;
   if(dos.view.textMode&&screen.cells[0][0]===65&&screen.cells[1][0]===219){resolve();return;}
   if(Date.now()>end){reject(Error('Direct video-memory cells were not published'));return;}setTimeout(check,30);
  };check();});
  const chars=dos.view.textScreen.root.querySelectorAll('.tv-text-screen-row > span');
  if(chars[0].textContent!=='A'||chars[1].textContent!=='█'||getComputedStyle(chars[0]).color!=='rgb(255, 255, 255)'
   ||getComputedStyle(chars[0]).backgroundColor!=='rgb(0, 0, 170)')throw Error('Native glyph/attribute palette differs');
  await command('');
  await command('text50');
  await new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
   if(dos.view.textMode&&dos.view.textScreen.screen.rows===50){resolve();return;}
   if(Date.now()>end){reject(Error('80x50 text mode was not published'));return;}setTimeout(check,30);
  };check();});
  await command('');
  if(${JSON.stringify(softwarePath)}){
   await command('cd '+String.fromCharCode(92)+${JSON.stringify(softwarePath)}.replaceAll('/',String.fromCharCode(92)).toLowerCase());
   const before=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
   const beforeText=JSON.stringify(dos.view.textScreen.screen?.cells);
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
   const changed=dos.view.textMode ? JSON.stringify(dos.view.textScreen.screen?.cells)!==beforeText
    : after.some((value,index)=>index%4!==3&&value!==before[index]);
   if(!changed||!running||running.toUpperCase().includes('COMMAND.COM')){
    let log='';try{log=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/'+${JSON.stringify(softwarePath)}+'/BUILD.LOG'));}catch{}
    throw Error('Software did not start: '+running+' '+log);
   }
   dos.root._tvResizer.maximize();
   await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
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
  const textGeometry=dos.root._tvResizer.captureGeometry();
  await command('gfx480');
  await new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
   if(canvas.width===640&&canvas.height===480&&!dos.view.textMode&&!canvas.hidden){resolve(true);return;}
   if(Date.now()>deadline){reject(new Error('640x480 video mode was not rendered'));return;}setTimeout(check,50);
  };check();});
  const highGeometry=dos.root._tvResizer.captureGeometry(),client=canvas.getBoundingClientRect();
  if(highGeometry.cols!==textGeometry.cols||highGeometry.rows<=textGeometry.rows
   ||client.height<client.width*480/640||client.height-client.width*480/640>17)
   throw new Error('DOS frame did not grow with video mode: '+JSON.stringify({textGeometry,highGeometry,client:client.toJSON()}));
  const corner=canvas.getContext('2d').getImageData(639,479,1,1).data;
  if(corner[0]<100||corner[1]!==0||corner[2]!==0)throw new Error('640x480 bottom-right pixel missing');
  const resizer=dos.root._tvResizer;
  for(const [dx,dy] of [[160,0],[0,160],[-9999,-9999],[9999,9999]]){
   resizer.place({...highGeometry,left:20,top:20});
   const handle=dos.root.querySelector('[data-tv-resize-handle]');
   handle.dispatchEvent(new MouseEvent('mousedown',{clientX:100,clientY:100,bubbles:true,cancelable:true}));
   document.dispatchEvent(new MouseEvent('mousemove',{clientX:100+dx,clientY:100+dy,bubbles:true}));
   const rect=canvas.getBoundingClientRect(),cell=window.THelpViewerTV.measureCells();
   const frame=dos.root.getBoundingClientRect(),desktop=resizer.desktop.getBoundingClientRect();
   if(rect.height<rect.width*480/640-1||rect.height-rect.width*480/640>cell.height+1
    ||frame.right>desktop.right+1||frame.bottom>desktop.bottom+1)
    throw new Error('DOS resize lost the video ratio: '+JSON.stringify({dx,dy,rect:rect.toJSON(),frame:frame.toJSON(),desktop:desktop.toJSON()}));
   document.dispatchEvent(new MouseEvent('mouseup',{clientX:100+dx,clientY:100+dy,bubbles:true}));
  }
  resizer.place(highGeometry);
  const running=dos.view.ci;
  dos.zoom();
  const app=document.querySelector('[data-tv-bundle-desktop]')._tvView.owner;
  app._dispatchWindowCommand(window.THelpViewerTV.TV_COMMANDS.DEFAULT_SIZE);
  const defaultGeometry=resizer.captureGeometry(),defaultClient=canvas.getBoundingClientRect();
  if(dos.zoomGeometry||dos.view.ci!==running||defaultGeometry.cols!==resizer.defaultSize.cols
   ||defaultClient.height<defaultClient.width*480/640-1
   ||defaultClient.height-defaultClient.width*480/640>17)
   throw new Error('DOS default size lost video ratio or restarted emulation: '+JSON.stringify(defaultGeometry));
  for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
  await new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
   if(canvas.height===400&&dos.view.textMode&&canvas.hidden&&dos.root._tvResizer.captureGeometry().rows===textGeometry.rows){resolve(true);return;}
   if(Date.now()>deadline){reject(new Error('DOS frame did not shrink back to text mode'));return;}setTimeout(check,50);
  };check();});
  await command('gfx');
  await new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
   const pixel=canvas.getContext('2d').getImageData(100,100,1,1).data;
   if(canvas.width===320&&canvas.height===200&&pixel[0]>100&&pixel[1]===0&&pixel[2]===0){resolve(true);return;}
   if(Date.now()>deadline){reject(new Error('DOS VGA graphics were not rendered: '+JSON.stringify({active:dos.active,paused:dos.paused,busy:dos.busy,dragging:dos.getState(THelpViewerTV.sfDragging),width:canvas.width,height:canvas.height,text:dos.view.textMode})));return;}setTimeout(check,50);
  };check();});
  const graphics=true;
  for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,25));}
  await new Promise(r=>setTimeout(r,200));
  await command('numon');
  await command('echo 0123456789+-*/.>numpad.txt',true);
  const numpad=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/NUMPAD.TXT')).trim();
  if(numpad!=='0123456789+-*/.')throw new Error('DOS numpad input differs: '+JSON.stringify(numpad));
  await command('echo hello>state.txt');
  console.log('DOS check: keyboard');
  console.log(JSON.stringify(await dos.view.ci.fsTree()));
  if(!(await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_c').nodes.some(node=>node.name.toUpperCase()==='STATE.TXT'))throw new Error('Keyboard did not create STATE.TXT');
  const text=await dos.view.ci.fsReadFile('drive_c/STATE.TXT');
  if(!new TextDecoder().decode(text).toLowerCase().includes('hello'))throw new Error('DOS keyboard did not create STATE.TXT');
  await command('mount x drive_c >mount.txt');
  const mount=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/MOUNT.TXT'));
  if(!/mounted/i.test(mount)||/secure/i.test(mount))throw new Error('Browser MOUNT failed: '+mount);
  await command('echo virtual-only>x:'+String.fromCharCode(92)+'virtual.txt');
  if(!new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/VIRTUAL.TXT')).includes('virtual-only'))throw Error('MOUNT did not use the virtual filesystem');
  await command('imgmount e missing.iso -t iso >image.txt');
  const image=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/IMAGE.TXT'));
  if(/secure/i.test(image))throw new Error('IMGMOUNT is still blocked: '+image);
  await command('boot no.img >boot.txt');
  const boot=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/BOOT.TXT'));
  if(/secure/i.test(boot))throw new Error('BOOT is still blocked: '+boot);
  await command('del readme.txt');
  await dos.save();
  if(dos.status.root.textContent.includes('C drive saved to cloud'))throw new Error('Successful save overlays the DOS screen');
  console.log('DOS check: saved');
  const revision=dos.session.revision;
  const pause=document.querySelector('[data-tv-command="dos-pause"]');pause.click();
  const paused=dos.paused;
  const panel=dos.view.pauseDialog,vm=dos.view.ci;
  if(!panel.isOpen()||panel.owner!==dos.view||panel.flags!==0||!panel.closeButton.hidden
   ||getComputedStyle(dos.view.surface).filter!=='grayscale(1)')throw Error('Manual pause panel/gray screen missing');
  const box=panel.dialog.getBoundingClientRect();
  panel.startDrag({target:panel.titlebar,clientX:1,clientY:1});
  if(panel.dragState||panel.dialog.getBoundingClientRect().left!==box.left)throw Error('Pause panel can be moved');
  panel.overlay.querySelector('[data-tv-command="dos-resume"]').click();
  if(dos.paused||panel.isOpen()||dos.view.ci!==vm||getComputedStyle(dos.view.surface).filter!=='none')
   throw Error('Resume did not restore the same running DOS instance');
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
  await command('copy e:'+String.fromCharCode(92)+'approved.txt c:'+String.fromCharCode(92)+'cd.txt');
  const cdMounted=new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/CD.TXT')).includes('approved cd');
  if (${JSON.stringify(blockedWorker)} === 'false') {
   // Real browser FileSystemDirectoryHandle/File objects; only the native picker
   // is replaced with an isolated OPFS directory, never the user's host files.
   const folder=await(await navigator.storage.getDirectory()).getDirectoryHandle('dos-local-fixture',{create:true});
   const write=async(name,text)=>{const handle=await folder.getFileHandle(name,{create:true});const stream=await handle.createWritable();await stream.write(text);await stream.close();};
   await write('INPUT.TXT','local-only input');await write('DELETE.TXT','delete');await write('MOVE.TXT','move');
   window.showDirectoryPicker=async options=>{if(options.mode!=='readwrite')throw Error('Local folder not writable');return folder;};
   await command('gfx');
   const originalCi=dos.view.ci;
   // The native permission/confirmation gesture is covered separately. Exercise
   // the actual Worker protocol here, with no restart or keyboard injection.
   await dos.changeLocalFolder(new THelpViewerTV.DosLocalDrive(folder));
   if(dos.view.ci!==originalCi)throw Error('Local mount restarted DOS');
   const programAfterMount=await dos.view.ci.getRunningProgram();
   if(!programAfterMount.toUpperCase().includes('GFX')||canvas.width!==320||canvas.height!==200)throw Error('Local mount interrupted the running VGA program: '+JSON.stringify({programAfterMount,width:canvas.width,height:canvas.height}));
   for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,30));}
   await new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=async()=>{
    if(/^(COMMAND|DOSBOX)$/.test((await dos.view.ci.getRunningProgram()).trim().toUpperCase())){resolve();return;}
    if(Date.now()>deadline){reject(Error('Graphics fixture did not return to the command shell'));return;}setTimeout(check,30);
   };void check();});
   if(!dos.localDrive||!dos.view.ci)throw Error('Local mount failed: '+dos.status.root.textContent);
   const connectedMount=dos.localDrive.id;
   try{await dos.localConnection.replace({mount:'invalid',writable:true,maxFileBytes:1024,entries:[{path:'../OUTSIDE',directory:true}]});throw Error('Accepted unsafe staged local path');}
   catch(error){if(error.message==='Accepted unsafe staged local path')throw error;}
   if(JSON.parse(new TextDecoder().decode(await dos.view.ci.fsReadFile('.jsdos/local-state.json'))).mount!==connectedMount)throw Error('Rejected local replacement damaged the current mount');
   await command('copy d:'+String.fromCharCode(92)+'input.txt c:'+String.fromCharCode(92)+'fromd.txt');
   if(!new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/FROMD.TXT')).includes('local-only input'))throw Error('Local D read failed');
   // DOS opens D:\INPUT.TXT and waits for one key while retaining the file
   // handle. A hot disconnect must fail without killing this running program.
   await dos.view.ci.fsWriteFile('drive_c/HOLD.COM',new Uint8Array([
    ...[0xba,0x14,0x01,0xb8,0x00,0x3d,0xcd,0x21,0x89,0xc3,0xb4,0x08,0xcd,0x21,0xb4,0x3e,0xcd,0x21,0xcd,0x20],
    ...new TextEncoder().encode('D:'+String.fromCharCode(92)+'INPUT.TXT'),0]));
   await command('rescan -a');
   await command('hold');
   const holding=await dos.view.ci.getRunningProgram();
   if(!holding.toUpperCase().includes('HOLD'))throw Error('Local open-file fixture did not start: '+holding);
   try{await dos.changeLocalFolder(null);throw Error('Disconnected an open local file');}
   catch(error){if(!/Close files/.test(error.message))throw error;}
   if(dos.view.ci!==originalCi||!dos.localDrive)throw Error('Failed disconnect replaced the running DOS session');
   for(const type of ['keydown','keyup']){canvas.dispatchEvent(new KeyboardEvent(type,{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,30));}
   await command('echo still-running>alive.txt');
   if(!new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/ALIVE.TXT')).includes('still-running'))throw Error('Failed hot swap did not preserve the DOS process');
   await command('echo saved>d:'+String.fromCharCode(92)+'out.txt');
   await command('md d:'+String.fromCharCode(92)+'empty');
   await command('del d:'+String.fromCharCode(92)+'delete.txt');
   await command('ren d:'+String.fromCharCode(92)+'move.txt moved.txt');
   if(!(await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_d').nodes.some(node=>node.name==='INPUT.TXT'))throw Error('Local D tree is incomplete');
   // No manual Save: automatic D flush works even with the window inactive.
   dos.setActive(false);
   const deadline=Date.now()+8000;
   while(dos.localDrive.savedRevision!==JSON.parse(new TextDecoder().decode(await dos.view.ci.fsReadFile('.jsdos/local-state.json'))).revision){
    if(dos.localSaveFailed||Date.now()>deadline)throw Error('Automatic local save failed');
    await new Promise(resolve=>setTimeout(resolve,100));
   }
   dos.setActive(true);
   if(!(await(await folder.getFileHandle('OUT.TXT')).getFile()).size)throw Error('Local D write failed');
   await folder.getDirectoryHandle('EMPTY');await folder.getFileHandle('MOVED.TXT');
   if(new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_d/MOVED.TXT'))!=='move')throw Error('Renamed local file lost bytes after save');
   try{await folder.getFileHandle('DELETE.TXT');throw Error('Local deletion not saved');}catch(error){if(error.name!=='NotFoundError')throw error;}
   await dos.restart();
   if(!new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_d/OUT.TXT')).includes('saved'))throw Error('Local D restart failed');
   await command('copy e:'+String.fromCharCode(92)+'approved.txt c:'+String.fromCharCode(92)+'localcd.txt');
   if(!new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/LOCALCD.TXT')).includes('approved cd'))throw Error('CD did not move to E');
   const config=await(await fetch('/api/dos/session')).json();
   if(Object.keys(config.remote_files).some(name=>name==='OUT.TXT'||name==='MOVED.TXT'))throw Error('Local D leaked to server C');
   const connectedCi=dos.view.ci;
   await dos.changeLocalFolder(null);
   if(dos.view.ci!==connectedCi)throw Error('Local disconnect restarted DOS');
   if((await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_d').nodes.length)throw Error('Disconnected local D still contains host files');
   await command('dir d:'+String.fromCharCode(92)+' /b>emptyd.txt');
   if(/INPUT|OUT|MOVED/.test(new TextDecoder().decode(await dos.view.ci.fsReadFile('drive_c/EMPTYD.TXT'))))throw Error('DOS directory cache still exposes the disconnected folder');
  }
  const deleted=!(await dos.view.ci.fsTree()).nodes.find(node=>node.name==='drive_c').nodes.some(node=>node.name.toUpperCase()==='README.TXT');
  return {frameOkay,bottomOkay,allBlack,nestedLoaded,rendered,graphics,paused,restored,deleted,mounted,cdMounted,revision,account:dos.session.account,mount};
 })()`);
 if(result.smokeOnly){
  if(screenshotPath){const capture=await send('Page.captureScreenshot',{format:'png'});require('node:fs').writeFileSync(screenshotPath,Buffer.from(capture.data,'base64'));}
  console.log(JSON.stringify(result));socket.close();return;
 }
 if(!result.frameOkay||!result.bottomOkay||!result.allBlack||!result.nestedLoaded||!result.rendered||!result.paused||!result.restored||!result.deleted||!result.mounted||!result.cdMounted||result.revision<1||result.account!=='player'||errors.length){throw new Error(JSON.stringify({result,errors}));}
 await evaluate(`(()=>{
  dos.setActive(false);
  if(dos.view.pauseDialog.isOpen()||dos.view.root.classList.contains('is-paused'))throw Error('Inactivity opened the manual pause panel');
  dos.setActive(true);
 })()`);
 await evaluate(`(()=>{
  const resizer=dos.root._tvResizer,geometry=resizer.captureGeometry(),ci=dos.view.ci;
  const original={pause:ci.pause,resume:ci.resume,motion:ci.sendMouseMotion,button:ci.sendMouseButton};
  let pauses=0,resumes=0,mouse=0;
  ci.pause=function(){pauses++;return original.pause.call(this);};
  ci.resume=function(){resumes++;return original.resume.call(this);};
  ci.sendMouseMotion=function(...args){mouse++;return original.motion.apply(this,args);};
  ci.sendMouseButton=function(...args){mouse++;return original.button.apply(this,args);};
  const down=()=>{resizer.moveHandle.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0,buttons:1,clientX:100,clientY:100}));};
  try{
   dos.setActive(true);down();
   if(!dos.getState(THelpViewerTV.sfDragging)||!resizer.moveState||!pauses)throw Error('DOS movement did not pause through sfDragging');
   if(getComputedStyle(dos.view.surface).filter!=='grayscale(1)'||dos.view.pauseDialog.isOpen())throw Error('Dragging did not gray DOS without a pause panel');
   dos.view.canvas.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,cancelable:true,buttons:1,clientX:140,clientY:140}));
   if(!resizer.moveState||mouse)throw Error('DOS stole the frame drag over its canvas');
   const resumed=resumes;
   dos.view.canvas.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,button:0,buttons:0,clientX:160,clientY:160}));
   if(resizer.moveState||dos.getState(THelpViewerTV.sfDragging)||dos.root.classList.contains('is-moving')||mouse||resumes<=resumed)throw Error('Mouse-up over DOS did not finish/resume the frame drag');
   if(getComputedStyle(dos.view.surface).filter!=='none')throw Error('Dragging left DOS gray');
   dos.paused=true;dos.syncPause();down();const manuallyPaused=resumes;
   window.dispatchEvent(new Event('blur'));
   if(resizer.moveState||dos.getState(THelpViewerTV.sfDragging)||!dos.paused||resumes!==manuallyPaused)throw Error('Blur left a stuck drag or lost manual DOS pause');
   if(getComputedStyle(dos.view.surface).filter!=='grayscale(1)'||!dos.view.pauseDialog.isOpen())throw Error('Ending a drag lost manual Pause presentation');
  }finally{ci.pause=original.pause;ci.resume=original.resume;ci.sendMouseMotion=original.motion;ci.sendMouseButton=original.button;dos.paused=false;dos.syncPause();resizer.place(geometry);}
 })()`);
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
  const r=dos.view.root.getBoundingClientRect();
  if(document.fullscreenElement===dos.view.root&&!dos.root.classList.contains('is-maximized')&&Math.abs(r.width-innerWidth)<1&&Math.abs(r.height-innerHeight)<1){resolve(true);return;}if(Date.now()>deadline){reject(new Error('Native canvas fullscreen failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`(()=>{const key=()=>dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Pause',code:'Pause',altKey:true,bubbles:true,cancelable:true}));key();if(!dos.paused)throw new Error('Alt-Pause did not pause DOS');key();if(dos.paused)throw new Error('Alt-Pause did not resume DOS');})()`);
 await evaluate(`(()=>{
  dos.dispatchEvent(new THelpViewerTV.TVEvent(THelpViewerTV.evCommand,{command:'dos-pause'}));
  const panel=dos.view.pauseDialog,rect=panel.dialog.getBoundingClientRect();
  if(!panel.isOpen()||!document.fullscreenElement.contains(panel.dialog)||rect.left<0||rect.top<0
   ||rect.right>innerWidth||rect.bottom>innerHeight)throw Error('Pause panel is outside native fullscreen');
  for(const el of [panel.dialog,panel.titlebar,panel.dialog.querySelector('.tv-static-text')]){
   const style=getComputedStyle(el);
   if(!style.fontFamily.includes('IBM VGA')||parseFloat(style.fontSize)!==16)
    throw Error('Embedded TVDialog lost the shared font: '+style.fontFamily+' / '+style.fontSize);
  }
 })()`);
 if(screenshotPath){const capture=await send('Page.captureScreenshot',{format:'png'});require('node:fs').writeFileSync(screenshotPath,Buffer.from(capture.data,'base64'));}
 await evaluate(`(()=>{
  const panel=dos.view.pauseDialog;
  dos.view.focus();
  if(document.activeElement!==panel.dialog)throw Error('DOS focus escaped the pause panel');
  panel.dialog.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));
  if(dos.paused||panel.isOpen())throw Error('Enter did not press the default Resume button');
 })()`);
 // A fullscreen key can target the document after browser focus changes.
 await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',altKey:true,bubbles:true,cancelable:true}))`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(!document.fullscreenElement&&!dos.root.classList.contains('is-maximized')){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen restore failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'NumpadEnter',altKey:true,bubbles:true,cancelable:true}))`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(document.fullscreenElement===dos.view.root){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen re-entry failed'));return;}setTimeout(check,50);
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
  if(document.fullscreenElement===dos.view.root){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen after cancelling restart failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`(async()=>{await dos.restart();if(document.fullscreenElement!==dos.view.root)throw new Error('Restart lost DOS fullscreen');})()`);
 await evaluate(`(()=>{dos.view.canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'m',code:'KeyM',ctrlKey:true,altKey:true,bubbles:true,cancelable:true}));})()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  const menu=document.querySelector('[data-tv-menu-bar] .tv-menu-popup:not([hidden])');
  if(!document.fullscreenElement&&menu&&menu.getBoundingClientRect().height>0){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('DOS menu shortcut did not leave fullscreen'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.view.canvas.click()`);
 await evaluate(`document.querySelector('[data-tv-command="dos-fullscreen"]').click()`,true);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(document.fullscreenElement===dos.view.root){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS fullscreen before EXIT failed'));return;}setTimeout(check,50);
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
 // A genuinely different cloud write must not trap Close, or silently overwrite it.
 await evaluate(`(async()=>{
  const state=await(await fetch('/api/dos/session')).json(),unchanged={};
  for(const name of state.overlay_files)unchanged[name]=state.remote_files[name].sha256;
  const response=await fetch('/api/dos/overlay',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({
   base_id:state.base_id,revision:state.revision,account:state.account,files:{'OTHER.TXT':btoa('another DOS window')},unchanged,
   deleted:Object.keys(state.files).filter(name=>!state.remote_files[name]),directories:[]})});
  if(!response.ok)throw Error('Could not simulate second DOS window');
  window.foreignRevision=(await response.json()).revision;
 })()`);
 const closePoint=await evaluate(`(()=>{const r=dos.root.querySelector('.tv-close-control').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...closePoint});
 if(!await evaluate(`dos.root.isConnected`))throw new Error('DOS closed before mouse release');
 await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...closePoint});
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(dos.confirmation?.isOpen()){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Cloud conflict offered no way to close DOS'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.confirmation.closeAction()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+3000;const check=()=>{
  if(!dos.confirmation&&!dos.closing&&dos.root.isConnected&&dos.view.ci){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Cancel discarded DOS after a cloud conflict'));return;}setTimeout(check,50);
 };check();})`);
 await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...closePoint});
 await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...closePoint});
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(dos.confirmation?.isOpen()){resolve(true);return;}
  if(Date.now()>deadline){reject(new Error('Repeated close lost its confirmation'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`dos.confirmation.buttonViews.find(button=>button.value==='ok').press()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(!document.querySelector('.tv-dos-window')){resolve(true);return;}if(Date.now()>deadline){reject(new Error('DOS close failed'));return;}setTimeout(check,50);
 };check();})`);
 await evaluate(`(async()=>{const response=await(await fetch('/api/dos/session')).json();
  if(response.revision!==foreignRevision||!response.remote_files['OTHER.TXT'])throw Error('Discard overwrote the other DOS disk');})()`);
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
                extra_software, os.environ.get("THELP_DOS_TEST_SOFTWARE_COMMAND", "start"), os.environ.get("THELP_DOS_TEST_SCREENSHOT", ""), os.environ.get("THELP_DOS_TEST_SOFTWARE_OUTPUT", ""), str(text_rendering).lower()], capture_output=True, text=True, timeout=180)
            assert result.returncode == 0, result.stderr
            if extra_software:
                print(result.stdout)
            if text_rendering and not blocked_worker and not extra_game and not extra_software:
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
