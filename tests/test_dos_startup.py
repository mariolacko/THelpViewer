"""DOS startup must not depend on audio permission or wait forever for a worker."""
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_dos_resize_command_keeps_mode_ratio_and_other_windows_stay_free():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class View{clearEvent(e){e.what=0;}setHelpCtx(){}handleEvent(){}setState(mask,on){this.state=on?(this.state|mask):(this.state&~mask);}getState(mask){return Boolean(this.state&mask);}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
class Rect{constructor(x1=0,y1=0,x2=0,y2=0){Object.assign(this,{x1,y1,x2,y2});}get width(){return this.x2-this.x1;}get height(){return this.y2-this.y1;}}
const TV={TVView:View,TVWindow:Window,TVStaticText:View,TVRect:Rect,
 TVPoint:class{constructor(x,y){Object.assign(this,{x,y});}},TV_HELP_CONTEXTS:{hcDosPrompt:2320},
 TVEvent:class{constructor(what,data){Object.assign(this,{what},data);}},evCommand:1,
 TV_COMMANDS:{RESIZE:'resize'},measureCells:()=>({width:8,height:16}),fillBorders(){}};
for(const name of ['TVDialog','TVSubMenu','TVMenuBar','TVStatusLine','TVMenuController','TVProgram'])TV[name]=View;
const context={URL,window:{THelpViewerTV:TV,location:{pathname:'/'},addEventListener(){}},
 document:{currentScript:{src:'http://localhost/assets/tv-dos.js'}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),context);
const dos=new TV.TVDosWindow(),vars=new Map();
TV.TurboVisionWindowResizer.prototype.restoreState=()=>true;
TV.TurboVisionWindowResizer.prototype.captureGeometry=()=>({left:0,top:0,cols:82,rows:27});
const element={_tvView:dos,closest:()=>null,querySelector:()=>null,
 style:{setProperty:(key,value)=>vars.set(key,Number(value))}};
const resizer=new TV.TurboVisionWindowResizer(element);
dos.view.canvas={width:640,height:480};
dos.root={_tvResizer:resizer};
function drag(dx,dy,maxCols=180,maxRows=90){
 resizer.dragState={startX:0,startY:0,startCols:82,startRows:32,minCols:42,minRows:15,
  maxCols,maxRows,cellWidth:8,cellHeight:16};
 resizer.onResizeMove({clientX:dx,clientY:dy});
 const cols=vars.get('--tv-window-cols'),rows=vars.get('--tv-window-rows');
 assert.ok(Number.isInteger(cols)&&Number.isInteger(rows));
 assert.ok(cols<=maxCols&&rows<=maxRows);
 const ideal=(cols-2)*8*dos.view.canvas.height/dos.view.canvas.width;
 assert.ok((rows-2)*16>=ideal&&(rows-2)*16-ideal<16);
 return {cols,rows};
}
assert.deepEqual(drag(160,0),{cols:102,rows:40});
assert.deepEqual(drag(0,160),{cols:108,rows:42});
assert.deepEqual(drag(3000,3000,100,45),{cols:100,rows:39});
assert.deepEqual(drag(-3000,-3000),{cols:42,rows:17});
for(const [width,height] of [[320,200],[640,400],[640,480],[800,600]]){
 Object.assign(dos.view.canvas,{width,height});drag(140,20);drag(0,128);drag(9999,9999,90,40);
}
// A HELP/document window does not acquire the DOS-only proportional constraint.
resizer.windowElement._tvView=new Window();
resizer.onResizeMove({clientX:160,clientY:0});
assert.equal(vars.get('--tv-window-cols'),90);assert.equal(vars.get('--tv-window-rows'),32);
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-dos.js", "www/assets/tv-shell.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_dos_numpad_keys_keep_physical_codes_and_release_held_keys():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class View{constructor(){this.eventMask=0;}clearEvent(e){e.what=0;}}
const TV={TVView:View,TVWindow:View,TVRect:class{},evKeyDown:1};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{URL,
 document:{currentScript:{src:'http://localhost/assets/tv-dos.js'}},window:{THelpViewerTV:TV}});
const view=new TV.TVDosView(),keys=[];
view.owner={active:true,getKeyCommand:()=>'',resumeSound(){}};
view.ci={sendKeyEvent:(...args)=>keys.push(args)};
function key(code,type='keydown',repeat=false,value=''){
 const event={what:1,nativeEvent:{code,type,repeat,key:value,preventDefault(){},stopPropagation(){}}};
 view.handleEvent(event);assert.equal(event.what,0);
}
const codes={NumpadDecimal:330,NumpadComma:330,NumpadDivide:331,NumpadMultiply:332,
 NumpadSubtract:333,NumpadAdd:334,NumpadEnter:335,NumpadEqual:61,NumLock:282};
for(let i=0;i<10;i++)codes['Numpad'+i]=320+i;
for(const [code,number] of Object.entries(codes)){
 const start=keys.length;key(code);key(code,'keydown',true);key(code,'keyup');
 assert.deepEqual(keys.slice(start),[[number,true],[number,false]]);
}
// NumLock changes the DOS interpretation, not the physical key sent to DOSBox.
key('Numpad1','keydown',false,'End');key('Numpad1','keyup',false,'End');
assert.deepEqual(keys.slice(-2),[[321,true],[321,false]]);
key('Numpad8');view.releaseInput();
assert.deepEqual(keys.slice(-2),[[328,true],[328,false]]);assert.equal(view.keys.size,0);
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-dos.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_dos_video_mode_resizes_frame_height_without_resetting_manual_geometry():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class View{clearEvent(e){e.what=0;}setHelpCtx(value){this.helpCtx=value;}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
let filled=0,changed=0,painted=0,maximized=false;
const TV={TVView:View,TVWindow:Window,TVStaticText:class{},TVRect:class{},
 TVPoint:class{constructor(x,y){this.x=x;this.y=y;}},TV_HELP_CONTEXTS:{hcDosPrompt:2320},
 measureCells:()=>({width:8,height:16}),fillBorders:()=>filled++};
const listeners=new Map();
const document={currentScript:{src:'http://localhost/assets/tv-dos.js'},
 addEventListener(type,fn){listeners.set(type,fn);},removeEventListener(type){listeners.delete(type);}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{URL,document,
 ImageData:class{constructor(w,h){this.data=new Uint8ClampedArray(w*h*4);}},window:{THelpViewerTV:TV}});
const win=new TV.TVDosWindow();let width=640,height=400;
const canvas={width,height,focus(){},getContext:()=>({putImageData(){painted++;}}),
 requestFullscreen:async()=>{document.fullscreenElement=canvas;}};
win.view.canvas=canvas;win.view.ci={width:()=>width,height:()=>height};win.onChange=()=>changed++;
const original={left:500,top:300,cols:82,rows:27};let geometry={...original};
const resizer={desktop:{clientWidth:2000,clientHeight:1200},captureGeometry:()=>geometry,
 place:g=>{geometry=g;},restore:()=>{maximized=false;geometry={...original};}};
win.root={_tvResizer:resizer,classList:{contains:()=>maximized}};
const frame=(w,h)=>{width=w;height=h;win.view.renderFrame(null,new Uint8Array(w*h*4));};
// Fit a restored mismatched frame even if the first mode equals canvas defaults.
geometry={...original,rows:40};frame(640,400);
assert.equal(geometry.rows,27);assert.equal(changed,1);
filled=changed=painted=0;geometry={...original};
frame(640,480);
assert.equal(geometry.cols,82);assert.equal(geometry.rows,32);assert.equal(geometry.top,300);
assert.equal(changed,1);assert.equal(filled,1);
// Redrawing this mode must not fight a manual resize or rebuild the menu each frame.
geometry={...geometry,rows:40};frame(640,480);
assert.equal(geometry.rows,40);assert.equal(changed,1);assert.equal(painted,2);
frame(640,400);assert.equal(geometry.rows,27);assert.equal(geometry.cols,82);
win.zoom();assert.equal(geometry.cols,162);assert.equal(geometry.rows,52);
frame(640,480);assert.equal(geometry.cols,162);assert.equal(geometry.rows,62);
assert.equal(win.zoomGeometry.rows,32);win.zoom();assert.equal(geometry.rows,32);assert.equal(geometry.cols,82);
// Moving up keeps a taller frame on the desktop; a short desktop also limits width.
geometry={...original,top:1000};frame(640,400);frame(640,480);
assert.ok(geometry.top+geometry.rows*16<=1200);
resizer.desktop.clientWidth=800;resizer.desktop.clientHeight=500;
frame(640,400);frame(640,480);
assert.ok(geometry.cols<82);assert.ok(geometry.rows*16<=484);
assert.ok(geometry.left+geometry.cols*8<=800&&geometry.top+geometry.rows*16<=500);
assert.ok((geometry.rows-2)*16>=(geometry.cols-2)*8*480/640);
// A mode change must not leave native fullscreen or de-maximize the window.
(async()=>{
 resizer.desktop.clientWidth=2000;resizer.desktop.clientHeight=1200;geometry={...original};
 frame(640,400);const before=geometry;
 win.fullScreen();await win.fullscreenRequest;frame(640,480);
 assert.equal(document.fullscreenElement,canvas);assert.deepEqual(geometry,before);
 document.fullscreenElement=null;listeners.get('fullscreenchange')();
 assert.equal(geometry.rows,32);assert.equal(win.pendingScreenResize,false);
 maximized=true;frame(640,400);assert.equal(maximized,true);assert.equal(geometry.rows,32);
 win.zoom();assert.equal(maximized,false);assert.equal(geometry.rows,27);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-dos.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


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
    assert source.read_bytes() == Path("thelpviewer/server/converter/assets/tv-dos.js").read_bytes()
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
 class Loading {constructor(title){assert.equal(title,mode==='updating'?'Updating DOS C':'Initializing DOS C');this.filenameView=new Text();}show(){}update(value){progress.push(value);if(mode==='cancel')this.cancelled=true;}destroy(){destroyed++;}}
 const TV={TVView:View,TVWindow:Window,TVStaticText:Text,TVRect:class{},TVPoint:class{},TVLoadingDialog:Loading,TV_HELP_CONTEXTS:{hcDosPrompt:2320}};
 const context={URL,URLSearchParams,AbortSignal,DOMException,Set,Promise,console,
  setTimeout(fn,ms){const id=++next;if(ms===500){Promise.resolve().then(fn);return id;}timers.set(id,{fn,ms});return id;},clearTimeout(id){timers.delete(id);},
  setInterval(){return 1;},clearInterval(){},
  document:{currentScript:{src:'http://localhost/assets/tv-dos.js'},hidden:false,addEventListener(){},removeEventListener(){}},
  window:{THelpViewerTV:TV,AudioContext:Audio,Worker:class{},emulators:{
   dosboxWorker:()=>{assert.notEqual(mode,'required-failed');if(mode==='preparing')assert.ok(statusCalls>=3);
    return mode==='worker-denied'?Promise.reject(new DOMException('Worker forbidden','SecurityError')):mode.endsWith('hang')?new Promise(()=>{}):Promise.resolve(ci);},
   dosboxDirect:()=>mode==='all-hang'?new Promise(()=>{}):Promise.resolve(ci)}},
  fetch:async url=>{requests.push(url);return {ok:true,json:async()=>url.endsWith('/status')?
   (['preparing','updating','cancel','required-failed'].includes(mode)&&statusCalls++<2?{state:'building',initializing:mode!=='updating',configuring:mode==='updating',percent:statusCalls*25,phase:'Downloading',current:'Required tool'}:
    mode==='required-failed'?{state:'error',error:'Required package unavailable'}:{state:'ready'}):
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
 if(mode==='required-failed'){
  assert.deepEqual(progress,[25,50]);assert.equal(destroyed,1);assert.equal(win.view.ci,null);
  assert.match(errors[0],/Required package unavailable/);
  assert.ok(!requests.some(url=>url.includes('/session')||url.includes('/bundle')));return;
 }
 if(mode==='cancel'){
  assert.deepEqual(progress,[25]);assert.equal(destroyed,1);assert.deepEqual(errors,[]);
  assert.ok(!requests.some(url=>url.includes('/bundle')));return;
 }
 if(mode==='worker-denied'){
  assert.match(errors[0],/requires Web Workers/);assert.equal(win.view.ci,null);
  assert.ok(!requests.some(url=>url.includes('full=true')));return;
 }
 if(['preparing','updating'].includes(mode)){assert.deepEqual(progress,[25,50]);assert.equal(destroyed,1);}
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
(async()=>{for(const mode of ['constructor-denied','resume-denied','worker-hang','all-hang','worker-denied','preparing','updating','required-failed','cancel','unexpected-exit'])await scenario(mode);})().catch(error=>{console.error(error);process.exitCode=1;});
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
 win.active=false; // Native fullscreen still owns its controls if TV focus changes.
 win.view.handleEvent({what:TV.evKeyDown,nativeEvent:{type:'keydown',code:'NumpadEnter',altKey:true,
  preventDefault(){},stopPropagation(){}}});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(document.fullscreenElement,null);win.active=true;
 win.fullScreen();resolveRequest();await win.fullscreenRequest;listeners.get('fullscreenchange')();
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


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_cloud_close_failure_requires_explicit_discard_and_preserves_local_failures():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let answer='cancel',exits=0,boxes=0,removed=0,local=0;
class View{setHelpCtx(){}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
class Box{static MF_WARNING=0;static MF_OK_CANCEL=3;async show(options){boxes++;
 assert.match(options.title,/without saving C/);assert.match(options.lines.join('\n'),/will not be overwritten/);
 assert.equal(win.paused,true);return answer;}destroy(){removed++;}}
const TV={TVView:View,TVWindow:Window,TVStaticText:View,TVMessageBox:Box,TVRect:class{},TVPoint:class{},TV_HELP_CONTEXTS:{}};
const document={currentScript:{src:'http://localhost/assets/tv-dos.js'},fullscreenElement:null,removeEventListener(){}};
vm.runInNewContext(fs.readFileSync('www/assets/tv-dos.js','utf8'),{URL,clearInterval(){},clearTimeout(){},document,window:{THelpViewerTV:TV}});
const win=new TV.TVDosWindow();win.syncPause=()=>{};win.owner={insert(){},remove(){}};
win.view.ci={exit:async()=>exits++};win.session={account:'reader'};
win.saveSnapshot=async()=>{local++;const error=Error('Another DOS window saved this drive');error.dosCloudSave=true;throw error;};
(async()=>{
 assert.equal(await win.stop(),false);assert.equal(exits,0);assert.equal(win.disposed,false);
 assert.equal(win.paused,false);assert.ok(win.view.ci);assert.equal(win.confirmation,null);
 // The message box's []/Escape resolve as cancel, never implicit discard.
 answer='cancel';assert.equal(await win.stop(),false);assert.equal(exits,0);
 answer='ok';await win.stop();assert.equal(exits,1);assert.equal(win.disposed,true);
 assert.equal(boxes,3);assert.equal(removed,3);assert.equal(local,3);
 const failed=new TV.TVDosWindow();failed.view.ci={};failed.session={account:'reader'};
 failed.saveSnapshot=async()=>{throw Error('Local D changed outside DOS');};
 await assert.rejects(failed.stop(),/Local D/);assert.equal(boxes,3);
 assert.ok(failed.view.ci);assert.equal(failed.disposed,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
