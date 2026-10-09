"""DOS startup must not depend on audio permission or wait forever for a worker."""
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_dos_zoom_doubles_client_area_restores_and_limits_to_desktop():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class View{clearEvent(e){e.what=0;}setHelpCtx(value){this.helpCtx=value;}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
let filled=0,focused=0,changed=0;
const TV={TVView:View,TVWindow:Window,TVStaticText:class{},TVRect:class{},TVPoint:class{},evCommand:1,TV_HELP_CONTEXTS:{hcDosPrompt:2320},
 measureCells:()=>({width:8,height:16}),fillBorders:()=>filled++};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{URL,window:{THelpViewerTV:TV},
 document:{currentScript:{src:'http://localhost/assets/tv-dos.js'}}});
const win=new TV.TVDosWindow();win.view.canvas={focus(){focused++;}};win.onChange=()=>changed++;
const original={left:500,top:300,cols:82,rows:27};let geometry=original;
const resizer={desktop:{clientWidth:2000,clientHeight:1200},captureGeometry:()=>geometry,place:g=>{geometry=g;}};
win.root={_tvResizer:resizer,classList:{contains:()=>false}};
win.handleEvent({what:1,command:'dos-zoom'});
assert.equal(geometry.cols,162);assert.equal(geometry.rows,52); // Client area, not frame, doubles.
win.handleEvent({what:1,command:'dos-zoom'});assert.deepEqual(geometry,original);assert.equal(win.zoomGeometry,null);
resizer.desktop.clientWidth=800;resizer.desktop.clientHeight=600;
win.zoom();assert.ok(geometry.cols*8<=800);assert.ok(geometry.rows*16<=600);
assert.ok(geometry.left>=0&&geometry.top>=0);
assert.ok(geometry.left+geometry.cols*8<=800&&geometry.top+geometry.rows*16<=600);
win.zoom();assert.deepEqual(geometry,original);assert.equal(filled,4);assert.equal(focused,4);assert.equal(changed,4);
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-dos.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_embedded_dos_startup_survives_audio_denial_and_reports_worker_timeout():
    source = Path("www/assets/tv-dos.js")
    assert source.read_bytes() == Path("thelpviewer/converter/assets/tv-dos.js").read_bytes()
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
async function scenario(mode){
 const timers=new Map();let next=0;const notices=[],requests=[],progress=[];let statusCalls=0,destroyed=0;
 class View{constructor(){this.eventMask=0;}clearEvent(e){e.what=0;}setHelpCtx(value){this.helpCtx=value;}}
 class Window extends View{constructor(){super();this.root={isConnected:true};}insertAll(children){children.forEach(child=>child.owner=this);}}
 class Text extends View{setText(text){this.text=text;notices.push(text);}setState(flag,value){this.visible=value;}}
 let exitHandler;
 const ci={events:()=>({onFrame(){},onSoundPush(){},onExit(fn){exitHandler=fn;},onStdout(fn){fn('THelpViewer DOS Prompt - use the DOS Prompt menu for media.');}}),
  pause(){},resume(){},exit:async()=>{}};
 let resumeCalls=0;
 class Audio {constructor(){if(mode==='constructor-denied')throw new Error('Audio denied by embedded browser');}
  resume(){resumeCalls++;return Promise.reject(new Error('Autoplay denied'));}close(){return Promise.resolve();}}
 class Loading {constructor(title){assert.equal(title,'Initializing DOS C');this.filenameView=new Text();}show(){}update(value){progress.push(value);if(mode==='cancel')this.cancelled=true;}destroy(){destroyed++;}}
 const TV={TVView:View,TVWindow:Window,TVStaticText:Text,TVRect:class{},TVPoint:class{},TVLoadingDialog:Loading,TV_HELP_CONTEXTS:{hcDosPrompt:2320}};
 const context={URL,AbortSignal,DOMException,Set,Promise,console,
  setTimeout(fn,ms){const id=++next;if(ms===500){Promise.resolve().then(fn);return id;}timers.set(id,{fn,ms});return id;},clearTimeout(id){timers.delete(id);},
  setInterval(){return 1;},clearInterval(){},
  document:{currentScript:{src:'http://localhost/assets/tv-dos.js'},hidden:false,addEventListener(){},removeEventListener(){}},
  window:{THelpViewerTV:TV,AudioContext:Audio,Worker:class{},emulators:{
   dosboxWorker:()=>mode==='worker-denied'?Promise.reject(new DOMException('Worker forbidden','SecurityError')):mode.endsWith('hang')?new Promise(()=>{}):Promise.resolve(ci),
   dosboxDirect:()=>mode==='all-hang'?new Promise(()=>{}):Promise.resolve(ci)}},
  fetch:async url=>{requests.push(url);return {ok:true,json:async()=>url.endsWith('/status')?
   (['preparing','cancel'].includes(mode)&&statusCalls++<2?{state:'building',initializing:true,percent:statusCalls*25,phase:'Downloading',current:'Game'}:{state:'ready'}):
   {account:'',revision:0,base_id:'base',allow_full_disk_fallback:mode!=='worker-denied'},
   headers:{get:name=>name==='X-DOS-Revision'?'0':'base'},arrayBuffer:async()=>new ArrayBuffer(0)};}};
 vm.runInNewContext(source,context);
 const win=new TV.TVDosWindow();win.view.canvas={focus(){}};
 win.owner={insert(){}};
 const errors=[];win.onError=error=>errors.push(error.message);
 const boot=win.boot();
 if(mode.endsWith('hang')){
  for(let i=0;i<50&&!notices.includes('Starting DOSBox worker...');i++)await Promise.resolve();
  const timeout=Array.from(timers.values()).find(timer=>timer.ms===30000);
  assert.ok(timeout,'Worker deadline not registered');timeout.fn();
  if(mode==='all-hang'){
   for(let i=0;i<50&&!notices.includes('Starting DOSBox without worker...');i++)await Promise.resolve();
   const direct=Array.from(timers.values()).find(timer=>timer.ms===30000);
   assert.ok(direct,'Direct backend deadline not registered');direct.fn();
  }
 }
 await boot;
 assert.equal(win.busy,false);
 if(mode==='cancel'){
  assert.deepEqual(progress,[25]);assert.equal(destroyed,1);assert.deepEqual(errors,[]);
  assert.ok(!requests.some(url=>url.includes('/bundle')));return;
 }
 if(mode==='worker-denied'){
  assert.match(errors[0],/requires Web Workers/);assert.equal(win.view.ci,null);
  assert.ok(!requests.some(url=>url.includes('full=true')));return;
 }
 if(mode==='preparing'){assert.deepEqual(progress,[25,50]);assert.equal(destroyed,1);}
 assert.ok(notices.includes('Loading DOS C drive...'));
 if(mode==='all-hang'){
  assert.equal(win.view.ci,null);assert.match(errors[0],/dosboxDirect startup timed out/);assert.equal(win.status.visible,true);
 }else{
  assert.equal(win.view.ci,ci);assert.deepEqual(errors,[]);assert.equal(win.status.visible,false);
 }
 if(mode==='worker-hang')assert.ok(notices.includes('Starting DOSBox without worker...'));
 if(mode==='resume-denied')assert.ok(resumeCalls>0);
 if(mode==='unexpected-exit'){
  context.document.fullscreenElement=win.view.canvas;
  context.document.exitFullscreen=async()=>{context.document.fullscreenElement=null;};
  exitHandler();await Promise.resolve();
  assert.equal(win.view.ci,null);assert.equal(context.document.fullscreenElement,null);
  assert.ok(notices.includes('DOS stopped. Choose Restart from DOS Prompt.'));
 }
 await win.stop(false);
}
(async()=>{for(const mode of ['constructor-denied','resume-denied','worker-hang','all-hang','worker-denied','preparing','cancel','unexpected-exit'])await scenario(mode);})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script, str(source)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_native_fullscreen_pending_reentry_denial_and_stopped_menu():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const listeners=new Map(),errors=[];let requests=0,resolveRequest;
class View{clearEvent(event){event.what=0;}dispatchEvent(event){this.handleEvent(event);}setHelpCtx(value){this.helpCtx=value;}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
const TV={TVView:View,TVWindow:Window,TVStaticText:class{},TVRect:class{},TVPoint:class{},
 TVEvent:class{constructor(what,data){this.what=what;Object.assign(this,data);}},evCommand:1,evKeyDown:2,TV_HELP_CONTEXTS:{hcDosPrompt:2320}};
const document={currentScript:{src:'http://localhost/assets/tv-dos.js'},fullscreenElement:null,
 addEventListener(type,fn){listeners.set(type,fn);},
 removeEventListener(type,fn){if(listeners.get(type)===fn)listeners.delete(type);},
 async exitFullscreen(){document.fullscreenElement=null;listeners.get('fullscreenchange')?.();}};
const context={URL,console,document,window:{THelpViewerTV:TV}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const win=new TV.TVDosWindow();win.onError=error=>errors.push(error.message);win.active=true;
const canvas={focus(){},requestFullscreen(){requests++;return new Promise(resolve=>{
 resolveRequest=()=>{document.fullscreenElement=canvas;resolve();};});}};
win.view.canvas=canvas;
(async()=>{
 win.fullScreen();win.fullScreen();assert.equal(requests,1);
 resolveRequest();await win.fullscreenRequest;listeners.get('fullscreenchange')();
 // Browser has exited, but its fullscreenchange notification is still queued.
 document.fullscreenElement=null;
 win.fullScreen();assert.equal(requests,2);
 resolveRequest();await win.fullscreenRequest;listeners.get('fullscreenchange')();
 assert.equal(document.fullscreenElement,canvas);
 let menu=0;win.onMenu=()=>menu++;
 win.view.handleEvent({what:TV.evKeyDown,nativeEvent:{type:'keydown',code:'KeyM',ctrlKey:true,altKey:true,
  preventDefault(){},stopPropagation(){}}});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(document.fullscreenElement,null);assert.equal(menu,1); // No running CI.
 canvas.requestFullscreen=()=>Promise.reject(new Error('Fullscreen denied'));
 win.fullScreen();await win.fullscreenRequest;
 assert.equal(win.fullscreenChanged,null);assert.equal(win.fullscreenRequest,null);
 assert.deepEqual(errors,['Fullscreen denied']);assert.equal(listeners.size,0);
 const commands=[];win.handleEvent=event=>{commands.push(event.command);event.what=0;};
 for(const [code,ctrlKey,altKey,command] of [['Enter',false,true,'dos-fullscreen'],['Pause',false,true,'dos-pause'],['F16',false,true,'dos-pause'],['KeyR',true,true,'dos-restart']]){
  win.view.handleEvent({what:TV.evKeyDown,nativeEvent:{type:'keydown',code,ctrlKey,altKey,preventDefault(){},stopPropagation(){}}});
  assert.equal(commands.at(-1),command);
 }
 const count=commands.length;
 win.view.handleEvent({what:TV.evKeyDown,nativeEvent:{type:'keydown',code:'Enter',altKey:true,repeat:true,preventDefault(){},stopPropagation(){}}});
 win.view.handleEvent({what:TV.evKeyDown,nativeEvent:{type:'keyup',code:'Enter',altKey:true,preventDefault(){},stopPropagation(){}}});
 assert.equal(commands.length,count);
 assert.equal(win.getKeyCommand({code:'Enter',altKey:true,ctrlKey:true}), '');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-dos.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
