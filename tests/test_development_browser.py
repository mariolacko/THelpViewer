"""A browser without WebAuthn can still use the explicitly local session."""

import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url
from thelpviewer.server.midi.library import MidiLibrary


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_local_browser_auto_login_without_webauthn(tmp_path):
    port = _free_port()
    app_url = f"http://localhost:{port}/"
    manifest = tmp_path / "config.json"
    manifest.write_text(json.dumps({"categories": [{"id": "games", "label": "Games"},
        {"id": "development", "label": "Programming"}, {"id": "empty", "label": "Empty"}], "sources": [
        {"id": "game", "category": "games", "title": "Test game", "language": "cs", "description": "First test game description: česká logická hra", "url": "https://packages.test/game.zip",
         "format": "zip", "target": "GAMES/TEST", "enabled": False},
        {"id": "second-game", "category": "games", "title": "Second game", "language": "en-US", "description": "Second test game description", "url": "https://packages.test/second.zip",
         "format": "zip", "target": "GAMES/SECOND", "enabled": False},
        {"id": "compiler", "category": "development", "title": "Test compiler", "url": "https://packages.test/compiler.zip",
         "format": "zip", "target": "DEV/TEST", "enabled": False}],
        "files": [{"path": "TEST.TXT", "text": ["shared test disk"]}]}))
    midi_manifest = tmp_path / "midi.json"
    midi_manifest.write_text('{"sources": [{"id":"one","name":"First source","enabled":false,"pages":["https://music.test/one"],'
        '"allowed_hosts":["music.test"],"extract":{"mode":"anchors"}},'
        '{"id":"two","name":"Second source","enabled":false,"pages":["https://music.test/two"],'
        '"allowed_hosts":["music.test"],"extract":{"mode":"anchors"}}]}')
    cached = MidiLibrary(tmp_path / "midi", midi_manifest)
    cached._items = [{"id": f"{index:016x}", "source_id": provider, "game": game,
        "title": "Theme", "url": f"https://music.test/{index}.mid", "filename": f"{index}.mid",
        "kind": "midi", "sequencer": "Test"}
        for index, (provider, game) in enumerate((("one", "Doom"), ("one", "Quake"), ("two", "Keen")), 1)]
    cached._save_catalog()
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "THELP_STATE_DIR": str(tmp_path), "THELP_DATA_DIR": str(tmp_path),
             "THELP_DOWNLOADS_DIR": str(tmp_path / "downloads"), "THELP_SOURCES_DIR": str(tmp_path / "sources"),
             "THELP_HELPS_DIR": str(tmp_path / "helps"),
             "THELP_STATISTICS_PATH": str(tmp_path / "statistics.sqlite3"),
             "THELP_AUTH_ORIGIN": app_url.rstrip("/"), "THELP_PUBLIC_BASE_URL": "",
             "THELP_DEV_AUTO_LOGIN": "1", "THELP_MIDI_SOURCES_PATH": str(midi_manifest),
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
const [port,url,screenshotPrefix]=process.argv.slice(1);
(async()=>{
 const target=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let next=0;const pending=new Map(),statisticsFailures=[];
 socket.onmessage=event=>{const r=JSON.parse(String(event.data));
  if(r.method==='Network.responseReceived'&&r.params.response.url.includes('/api/statistics/events')&&r.params.response.status>=400)
   statisticsFailures.push(r.params.response.status);
  const p=pending.get(r.id);if(!p)return;
  pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);};
 const send=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++next;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 await send('Page.enable');
 await send('Network.enable');
 await send('Page.addScriptToEvaluateOnNewDocument',{source:
  `Object.defineProperty(navigator,'credentials',{value:undefined});`});
 for(let reload=0;reload<2;reload++){
  await send('Page.navigate',{url});
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+10000;const check=()=>{
   const title=document.querySelector('.tv-menu-right .tv-menu-button')?.textContent;
   if(title==='Admin'&&document.querySelector('[data-tv-command="account-server-configuration"]')){resolve();return;}
   if(Date.now()>deadline){reject(Error('Development account menu did not load: '+title));return;}setTimeout(check,50);
  };check();})`);
  if(!await evaluate(`(async()=>{if(navigator.credentials)throw Error('WebAuthn was not disabled');
   const session=await(await fetch('/api/auth/session')).json();
   return session.authenticated&&session.user.role==='admin'&&(await fetch('/api/admin/settings')).ok;})()`))throw Error('Local browser session failed');
 }
 await evaluate(`(async()=>{
  window.waitPackages=async(test,message)=>{const end=Date.now()+5000;while(!test()){
   if(Date.now()>end)throw Error(message);await new Promise(resolve=>setTimeout(resolve,20));}};
  await waitPackages(()=>{const v=document.querySelector('.tv-help-packages-window')?.closest('.tv-dialog-overlay')?._tvView;
   return v?.isOpen()&&v.valid&&v.items.options.length;},'Universal first-run chooser did not open');
  const TV=window.THelpViewerTV,v=document.querySelector('.tv-help-packages-window').closest('.tv-dialog-overlay')._tvView;
  window.packages=v;
  if(!(v instanceof TV.TVPackagesDialog)||!(v.categories instanceof TV.TVListBox)||!(v.items instanceof TV.TVCheckBoxes))
   throw Error('Chooser bypassed shared TVision views');
  if(v.kind!=='help'||!v.items.options.some(item=>item.id==='tp:7'))throw Error('HELP editions missing');
  if(v.heading||v.size.x!==82||v.size.y!==24||v.items.bounds.y1!==2||v.groupAll.bounds.y1!==12
   ||!(v.filterInput instanceof TV.TVInputLine)||v.filterInput.bounds.y1!==0||v.filterLabel.link!==v.filterInput)throw Error('Package dimensions/filter row');
  if(v.descriptionBox.bounds.y1!==14||v.categories.bounds.y2!==v.groupAll.bounds.y2)throw Error('Package groups/description alignment');
  if(v.categoryLabel.root.textContent.includes('~')||!v.categoryLabel.root.querySelector('.tv-hotkey'))throw Error('Dynamic TVLabel lost its mnemonic');
  v.items.choiceElements[0].click();
  v.items.choiceElements[0].dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  if(v.draft.selected.size!==1)throw Error('Arrows changed checkbox selection');
  v.items.choiceElements[v.items.sel].dispatchEvent(new KeyboardEvent('keydown',{key:' ',bubbles:true,cancelable:true}));
  if(v.draft.selected.size!==2)throw Error('Space did not toggle edition');
  const body=v.content.root.getBoundingClientRect();
  const frame=v.dialog.getBoundingClientRect();
  if(frame.top<0||frame.bottom>innerHeight||frame.left<0||frame.right>innerWidth)throw Error('Package window does not fit the desktop');
  for(const control of [v.categories,v.items,v.groupAll,v.descriptionBox,v.applyButton,v.selectAllButton,v.deselectAllButton]){
   const r=control.root.getBoundingClientRect();
   if(r.left<body.left-1||r.right>body.right+1||r.bottom>body.bottom+1)throw Error('Package control escapes frame');
  }
  const confirmation=()=>document.querySelector('.tv-msgbox-window:not([hidden])')?.closest('.tv-dialog-overlay')._tvView;
  v.close();
  let data=await(await fetch('/api/admin/content')).json();
  if(data.configured||data.status.state!=='idle')throw Error('Closing package choices started installation');
  v.open();await waitPackages(()=>v.valid,'HELP choices did not reload');
  v.applyButton.root.click();
  if(confirmation()?.isOpen())throw Error('Apply opened a redundant selection confirmation');
  await waitPackages(()=>v.progress&&!v.pollTask&&!v.submitting&&v.valid,'Empty selection did not finish');
  v.close();data=await(await fetch('/api/admin/content')).json();
  if(!data.configured||data.needs_setup||data.status.percent!==100)throw Error('First-run choices not saved');
 })()`);
 await evaluate(`(()=>{
  const TV=window.THelpViewerTV,owner=document.querySelector('.tv-help-packages-window').closest('.tv-dialog-overlay')._tvView.owner;
  const progress=new TV.TVProgressDialog('Downloads');owner.insert(progress);
  const status={active:true,percent:2,errors:1,items:Array.from({length:30},(_,i)=>({id:String(i),kind:['help','dos','midi'][i%3],label:'Package/album '+i,
   percent:i===0?2:i===1?100:0,stage:'download',stage_percent:i===0?2:null,phase:'Downloading',
   state:i===0?'running':i===1?'done':i===2?'error':'pending'}))};
  progress.updateDownloads(status);
  progress.open();const compact=progress.dialog.getBoundingClientRect();
  if(progress.size.x!==64||progress.size.y>11)throw Error('Compact Downloads retains excessive empty space');
  const clientBounds=progress.content.root.getBoundingClientRect(),buttonsBottom=progress.hideButton.root.getBoundingClientRect().bottom;
  if(clientBounds.bottom-buttonsBottom>2)throw Error('Unused rows remain below Downloads buttons');
  const checkButtonShadow=button=>{
   const shadow=button.root.querySelector('.tv-dialog-button-shadow');
   if(shadow?.textContent!==' '+'▀'.repeat(button.size.x-1))throw Error('Resized TVButton lost its bottom shadow: '+JSON.stringify({title:button.title,width:button.size.x,shadow:shadow?.textContent}));
   const r=shadow.getBoundingClientRect(),bounds=button.root.getBoundingClientRect();
   if(r.height<1||r.top<bounds.top||r.bottom>bounds.bottom+1)throw Error('TVButton bottom shadow is clipped');
  };
  checkButtonShadow(progress.hideButton);checkButtonShadow(progress.moreButton);
  const buttonRoot=progress.hideButton.root;
  progress.hideButton.focus();progress.hideButton.drawState(true);
  for(const width of [16,8,12]){
   const b=progress.hideButton.bounds;
   progress.hideButton.locate(new TV.TVRect(b.x1,b.y1,b.x1+width,b.y2));checkButtonShadow(progress.hideButton);
   if(progress.hideButton.root!==buttonRoot||document.activeElement!==buttonRoot||!buttonRoot.classList.contains('is-pressed'))throw Error('Button resize replaced its root/focus/pressed state');
  }
  progress.hideButton.drawState(false);
  progress.overlay.click();if(!progress.isOpen())throw Error('Clicking outside a modal TVDialog closed it');
  if(!progress.moreButton.getState(TV.sfVisible)||progress.details.getState(TV.sfVisible))throw Error('Progress details are not initially compact');
  progress.moreButton.root.click();
  checkButtonShadow(progress.hideButton);checkButtonShadow(progress.moreButton);
  const expanded=progress.dialog.getBoundingClientRect(),body=progress.content.root.getBoundingClientRect(),list=progress.details.root.getBoundingClientRect();
  if(progress.details.root.classList.contains('is-h-scrollable'))throw Error('Short Downloads rows unnecessarily hide their percentage behind a horizontal scrollbar');
  const labels=progress.details.items.map(item=>item.label.trim());
  if(!progress.detailsExpanded||expanded.width!==compact.width||expanded.height<=compact.height||list.bottom>body.bottom
   ||labels.length!==29||!labels[0].endsWith('↓ 2%')||!labels[1].endsWith('!')||!labels[2].endsWith('·')
   ||progress.hideButton.bounds.x1!==3||progress.moreButton.bounds.x1!==47
   ||!progress.detailsCaption.text.includes('29 packages/albums · 1 failed')||getComputedStyle(progress.details.root).backgroundColor==='rgba(0, 0, 0, 0)')throw Error('Expanded shared download progress layout/states failed');
  progress.details.focusItem(20);const scroll=progress.details.scrollbarWidget.value;
  progress.updateDownloads(status);
  if(progress.details.selectedIndex!==20||progress.details.scrollbarWidget.value!==scroll
   ||document.activeElement!==progress.details.selectedElement())throw Error('Live progress reset list selection/scroll/focus');
  const selected=progress.details.selectedItem().id;
  status.items[0].state='done';status.items[0].percent=100;progress.updateDownloads(status);
  if(progress.details.items.length!==28||progress.details.selectedItem().id!==selected||progress.bar.curValue!==2)throw Error('Completed row did not disappear or changed selection/overall gauge');
  progress.moreButton.root.click();if(progress.detailsExpanded||progress.dialog.getBoundingClientRect().height>compact.height)throw Error('Less did not restore compact progress');
  progress.moreButton.root.click();status.items.forEach(item=>{item.state='done';item.percent=100;});
  progress.updateDownloads({...status,active:false,percent:0,errors:0});
  if(progress.details.items.length||progress.detailsExpanded||progress.moreButton.getState(TV.sfVisible)
   ||progress.hideButton.bounds.x1!==25||progress.bar.curValue!==100||progress.size.y>10)throw Error('Finished queue did not empty/collapse Downloads');
  const phase='Rate limited (HTTP 429), retry in 50s',file='Borland Turbo Assembler 1.0 with Turbo Debugger (5.25-360k) - original installation and HELP archive.7z';
  status.items[0].state='running';status.items[0].label='A very long package name: '+file;
  progress.updateDownloads({...status,active:true});
  progress.setOperation({state:'building',phase,percent:0,processed:0,total:60,file});
  progress.toggleDetails(true);
  const compactText=text=>Array.from(text).filter(c=>c.trim()).join('');
  if(compactText(progress.file.text)!==compactText(file)||!progress.summary.text.includes('0 / 60'))throw Error('Downloads truncated its filename/status: '+JSON.stringify({file:progress.file.text,summary:progress.summary.text,size:progress.size}));
  const controls=[progress.summary,progress.bar,progress.percent,progress.file,progress.hideButton,progress.detailsCaption,progress.details];
  const client=progress.content.root.getBoundingClientRect();
  for(let i=0;i<controls.length;i++){
   const control=controls[i],r=control.root.getBoundingClientRect();
   if(r.left<client.left-1||r.right>client.right+1||r.bottom>client.bottom+1
    ||(i&&r.top<controls[i-1].root.getBoundingClientRect().bottom-1))throw Error('Downloads information overlaps/escapes its client area');
  }
  for(const text of [progress.summary,progress.file])if(text.root.scrollWidth>text.root.clientWidth+1||text.root.scrollHeight>text.root.clientHeight+1)
   throw Error('Downloads text does not fit its shared static view');
  if(!progress.details.items[0].label.includes(file)||!progress.details.root.classList.contains('is-h-scrollable'))throw Error('Downloads lost the complete package name/horizontal scrolling');
  window.downloadLayoutTest=progress;
 })()`);
 const downloadLayoutScreenshot=await send('Page.captureScreenshot',{format:'png'});
 require('node:fs').writeFileSync(screenshotPrefix+'-downloads.png',Buffer.from(downloadLayoutScreenshot.data,'base64'));
 await evaluate(`(()=>{
  const progress=window.downloadLayoutTest;
  progress.setOperation(null);
  progress.updateDownloads({active:true,percent:42,errors:0,items:[
   {id:'help',kind:'help',label:'Turbo Pascal 7',state:'running',phase:'Downloading',stage:'download',stage_percent:42},
   {id:'dos',kind:'dos',label:'Commander Keen',state:'pending'},
   {id:'midi',kind:'midi',label:'Doom soundtrack',state:'pending'},
  ]});
  progress.toggleDetails(false);
  if(progress.size.x!==64||progress.size.y!==11)throw Error('Short download status is not compact');
 })()`);
 const compactDownloadScreenshot=await send('Page.captureScreenshot',{format:'png'});
 require('node:fs').writeFileSync(screenshotPrefix+'-downloads-compact.png',Buffer.from(compactDownloadScreenshot.data,'base64'));
 await evaluate(`(()=>{
  const progress=window.downloadLayoutTest;progress.toggleDetails(true);
  if(progress.details.size.y!==3||progress.size.y>16)throw Error('Short Downloads queue has excessive blank list rows');
 })()`);
 const expandedDownloadScreenshot=await send('Page.captureScreenshot',{format:'png'});
 require('node:fs').writeFileSync(screenshotPrefix+'-downloads-expanded.png',Buffer.from(expandedDownloadScreenshot.data,'base64'));
 await evaluate(`(()=>{
  const progress=window.downloadLayoutTest;
  progress.destroy();
 })()`);
 await evaluate(`(async()=>{
  const TV=window.THelpViewerTV,help=packages,manager=help.owner.dialogManager;
  window.helpPackages=help;
  const dialogs={help,dos:manager.get('dos-packages'),midi:manager.get('midi-sources')};
  window.packageDialogs=dialogs;window.packages=dialogs.dos;
  for(const kind of ['dos','midi','help','dos']){
   document.querySelector('[data-tv-command="account-'+(kind==='midi'?'midi-sources':kind+'-packages')+'"]').click();
   await waitPackages(()=>dialogs[kind].isOpen()&&dialogs[kind].valid,'Package dialog did not load: '+kind);
  }
  if(new Set(Object.values(dialogs)).size!==3||document.querySelector('.tv-packages-window')
   ||Object.values(dialogs).some(v=>!(v instanceof TV.TVPackagesDialog)||v.mode||!v.isOpen()))
   throw Error('Package dialogs do not have independent windows and a shared base');
  if(!(dialogs.dos instanceof TV.TVDosPackagesDialog)||!(dialogs.midi instanceof TV.TVMidiSourcesDialog)
   ||!(help instanceof TV.TVHelpPackagesDialog))throw Error('Wrong concrete package class');
  const v=dialogs.dos;
  v.categories.selectItem(0);v.items.choiceElements[0].click();
  if(!v.descriptionRows.map(row=>row.text).join(' ').includes('First test game description'))throw Error('Description missing');
  if(!v.items.options[0].label.endsWith('🇨🇿')||!v.items.options[1].label.endsWith('🇺🇸'))throw Error('Package language flags missing');
  v.items.choiceElements[0].dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  if(!v.descriptionRows.map(row=>row.text).join(' ').includes('Second test game description'))throw Error('Description did not follow focus');
  v.categories.selectItem(1);v.groupAll.choiceElements[0].click();v.groupAll.choiceElements[0].click();
  if([...v.draft.selected].join(',')!=='game')throw Error('Deselect All affected another category');
  v.groupAll.choiceElements[0].click();v.categories.selectItem(0);
  if(!v.items.mark(0)||v.items.mark(1))throw Error('Category switch lost marks');
  if(v.groupAll.mark(0))throw Error('Partial category has checked Select/Deselect All');
  v.groupAll.choiceElements[0].click();if(v.draft.selected.size!==3||!v.groupAll.mark(0))throw Error('Category checkbox did not select all visible rows');
  v.categories.selectItem(2);
  if(v.items.options.length||!(v.groupAll.state&TV.sfDisabled)||v.selectAllButton.disabled)throw Error('Global selection is disabled in an empty category');
  v.deselectAllButton.root.click();if(v.draft.selected.size)throw Error('Global Deselect All kept a hidden category');
  v.selectAllButton.root.click();if(v.draft.selected.size!==3)throw Error('Global Select All omitted hidden category');
  manager.open('help-packages');help.items.choiceElements[0].click();const selectedHelp=[...help.draft.selected].join(',');
  if(!help.descriptionRows.map(row=>row.text).join(' ').includes('Turbo Pascal 4'))throw Error('HELP edition description missing');
  const localHelp=help.draft.selected.size;
  help.groupAll.choiceElements[0].click();
  if(help.draft.selected.size!==help.items.options.length||help.draft.selected.size<=localHelp)throw Error('HELP category checkbox missed guides');
  help.selectAllButton.root.click();if(help.draft.selected.size!==help.draft.packages.length)throw Error('Global HELP selection missed other groups');
  help.deselectAllButton.root.click();if(help.draft.selected.size)throw Error('Global HELP clear missed other groups');
  help.items.choiceElements[0].click();
  manager.open('dos-packages');
  if(v.draft.selected.size!==3||!help.isOpen()||[...help.draft.selected].join(',')!==selectedHelp)throw Error('Window switch lost independent drafts');
  if(v.helpCtx!==TV.TV_HELP_CONTEXTS.hcDosPackages||!document.querySelector('.tv-status-line').textContent.includes('Choose DOS categories'))throw Error('Window switch did not refresh context/mini help');
  help.close();help.open();await waitPackages(()=>help.valid&&!help.draft.selected.size,'Reopening treated draft as installed');
  v.close();v.open();await waitPackages(()=>v.valid,'DOS reopen failed');v.categories.selectItem(0);v.setAll(true);v.categories.selectItem(1);v.setAll(true);
  v.filterInput.root.value='compiler';v.filterInput.root.dispatchEvent(new InputEvent('input',{bubbles:true}));
  if(v.categories.items.length!==1||v.items.options.length!==1)throw Error('Apply fixture is not filtered');
  const request=TV.TVLoginDialog.request;let posts=0,state='building',scopes=['dos'];
  TV.TVLoginDialog.request=async(path,method,data)=>{
   if(path==='/api/admin/content'&&method==='POST'){
    posts++;
    if(data.dos_packages){if(Object.keys(data).join(',')!=='dos_packages'||data.dos_packages.length!==3)throw Error('Apply omitted hidden selections or changed HELP');}
    else if(data.help_packages?.length===1){scopes=['dos','help'];}
    else throw Error('Unexpected package request');
    return {state,scopes:state==='building'?scopes:[],percent:5,error:'Test failure'};
   }
   if(path==='/api/admin/content/status')return {state,scopes:state==='building'?scopes:[],percent:100,error:'Test failure'};
   return request(path,method,data);
  };
  const confirmation=()=>document.querySelector('.tv-msgbox-window')?.closest('.tv-dialog-overlay')._tvView;
  try{
   const applying=v.applySelection();if(confirmation()?.isOpen())throw Error('DOS Apply opened a selection confirmation');
   await applying;
   await waitPackages(()=>v.pollTask&&!v.applyButton.disabled,'Apply remains disabled during server work');
   v.categories.selectItem(0);v.items.choiceElements[0].click();const selected=[...v.draft.selected].join(',');
   await v.applySelection();if(posts!==1||!v.progress.isOpen())throw Error('Busy Apply duplicated job');
   help.setAll(false);help.items.choiceElements[0].click();
   help.followProgress({state,scopes,percent:5});
   if(help.installing)throw Error('Other content type incorrectly blocks Apply');
   const next=help.applySelection();if(confirmation()?.isOpen())throw Error('Queued HELP Apply opened a selection confirmation');
   await next;
   if(posts!==2||!help.installing)throw Error('Second content type was not submitted while monitoring the first');
   state='ready';await waitPackages(()=>!v.pollTask&&!help.pollTask&&v.valid,'Package job never finished');
   if([...v.draft.selected].join(',')!==selected||v.applyButton.disabled
    ||v.filterInput.getData()!=='compiler'||v.items.options.length!==1)throw Error('Completion discarded edits/filter');
  }finally{
   TV.TVLoginDialog.request=request;v.progress?.close();
   v.filterInput.root.value='';v.filterInput.root.dispatchEvent(new InputEvent('input',{bubbles:true}));
  }
  const midi=dialogs.midi;manager.open('midi-sources');
  await waitPackages(()=>midi.valid&&midi.categories.items.length===2,'MIDI sources did not load');
  midi.selectAllButton.root.click();
  if(midi.draft.sources.some(s=>!s.selected||!s.all_albums||s.albums.some(a=>!a.selected)))throw Error('Global MIDI select missed provider/albums');
  midi.deselectAllButton.root.click();
  if(midi.draft.sources.some(s=>s.selected||s.all_albums||s.albums.some(a=>a.selected)))throw Error('Global MIDI clear missed provider/albums');
  midi.setGroupAll(true);
  const source=()=>midi.draft.sources.find(item=>item.id==='one');
  midi.categories.selectItem(0);midi.enabled.choiceElements[0].click();midi.items.choiceElements[1].click();
  if(!source().selected||source().all_albums||source().albums[1].selected)throw Error('MIDI source/album controls failed');
  midi.categories.selectItem(1);if(midi.items.options[0].label!=='Keen')throw Error('Source switch did not change albums');
  midi.categories.selectItem(0);if(midi.items.mark(1)||!midi.enabled.mark(0))throw Error('Source switch lost MIDI draft');
  manager.open('help-packages');manager.open('midi-sources');
  if(midi.items.mark(1)||!midi.enabled.mark(0)||!help.isOpen()||!v.isOpen())throw Error('Window switch lost MIDI draft or closed sibling');
  const color=getComputedStyle(midi.items.root).backgroundColor;
  if(color==='rgba(0, 0, 0, 0)'||color!==getComputedStyle(midi.items.choiceElements[0].parentElement).backgroundColor)throw Error('Pane background incomplete');
  midi.setGroupAll(false);if(source().all_albums||source().albums.some(album=>album.selected))throw Error('MIDI Deselect All failed');
  midi.groupAll.choiceElements[0].click();if(!source().all_albums||source().albums.some(album=>!album.selected))throw Error('MIDI Select All failed');
  midi.setGroupAll(false);midi.items.choiceElements[0].click();
  const sourceData=await request('/api/admin/midi-sources');
  sourceData.sources[0].indexed=true;
  sourceData.sources[0].albums.push({id:'new-album',name:'New soundtrack',selected:true});
  let indexPosts=0,indexPolls=0;
  TV.TVLoginDialog.request=async(path,method,data)=>{
   if(path==='/api/admin/midi-sources/one/index'&&method==='POST'){
    indexPosts++;return {state:'building',indexing:true,phase:'Indexing',percent:25};
   }
   if(path==='/api/admin/midi-sources/status'){indexPolls++;return {state:'ready',indexing:false,percent:100};}
   if(path==='/api/admin/midi-sources')return sourceData;
   return request(path,method,data);
  };
  try{
   source().indexed=false;midi.updateButtons();midi.loadAlbumIndex();
   const progress=manager.get('midi-source-progress');
   if(!progress?.isOpen()||progress.helpCtx!==TV.TV_HELP_CONTEXTS.hcMidiSources)throw Error('Album index progress missing');
   manager.open('help-packages');await waitPackages(()=>!midi.indexTask,'Album index did not finish');
   manager.open('midi-sources');
   if(indexPosts!==1||indexPolls!==1||!progress.destroyed||!source().indexed||!source().selected||source().all_albums
    ||!source().albums[0].selected||source().albums[1].selected||source().albums[2].selected)throw Error('Background album indexing lost the draft');
  }finally{TV.TVLoginDialog.request=request;}
  midi.close();midi.open();await waitPackages(()=>midi.valid,'MIDI reopen failed');
  if(midi.draft.sources.some(source=>source.selected))throw Error('Cancelled MIDI draft was saved');
  let writes=0;const originalFetch=window.fetch;
  window.fetch=(url,options)=>{if(String(url)==='/api/admin/midi-sources'&&options?.method==='PUT')writes++;
   return originalFetch(url,options);};
  try{
   const applying=midi.applySelection();if(confirmation()?.isOpen())throw Error('MIDI Apply opened a selection confirmation');
   await midi.applySelection();await applying;
   if(writes!==1||midi.submitting)throw Error('MIDI selection was not saved exactly once');
  }finally{window.fetch=originalFetch;Object.values(dialogs).forEach(v=>v.close());}
 })()`);
 await evaluate(`(async()=>{
  const TV=window.THelpViewerTV,{help,dos,midi}=packageDialogs,manager=help.owner.dialogManager;
  window.typePackageFilter=(v,text)=>{
   v.filterInput.focus();v.filterInput.root.value=text;
   v.filterInput.root.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:text}));
   if(document.activeElement!==v.filterInput.root)throw Error('Filtering stole input focus');
  };
  for(const v of [help,dos,midi]){v.open();await waitPackages(()=>v.valid,'Filter fixture failed to load');}
  manager.open('dos-packages');dos.setAll(false);dos.categories.selectItem(0);
  dos.items.choiceElements[1].click();
  typePackageFilter(dos,'CESKA LOGICKA');
  if(dos.categories.items.length!==1||dos.items.options.length!==1||dos.items.options[0].id!=='game'
   ||!dos.draft.selected.has('second-game'))throw Error('Case/accent/description filter lost a hidden DOS selection');
  dos.items.choiceElements[0].click();typePackageFilter(dos,'');
  if(dos.categories.items.length!==3||!dos.items.mark(0)||!dos.items.mark(1))throw Error('Clearing filter lost DOS marks');
  typePackageFilter(dos,'Programming');
  if(dos.category!=='development'||dos.items.options[0]?.id!=='compiler')throw Error('Category-name filter did not cross groups');
  typePackageFilter(dos,'no such package 192846');
  if(dos.categories.items.length||dos.items.options.length||!dos.groupAll.getState(TV.sfDisabled)
   ||dos.selectAllButton.disabled||!dos.descriptionRows[0].text.includes('No matching'))throw Error('Empty filter state is inconsistent');
  let applies=0;const apply=dos.applySelection;dos.applySelection=async()=>{applies++;};
  const enter=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});
  dos.filterInput.root.dispatchEvent(enter);dos.applySelection=apply;
  if(applies||!enter.defaultPrevented)throw Error('Enter in Filter submitted an installation');
  dos.selectAllButton.root.click();
  if(dos.draft.selected.size!==3)throw Error('Global Select All was restricted by Filter');
  typePackageFilter(dos,'First test');dos.groupAll.choiceElements[0].click();
  if(dos.draft.selected.has('game')||!dos.draft.selected.has('second-game')||!dos.draft.selected.has('compiler'))
   throw Error('Filtered group toggle modified hidden packages');
  typePackageFilter(dos,'');
  dos.filterInput.focus();
 })()`);
 // Real browser typing must take the same TVInputLine -> TVEvent path.
 await send('Input.insertText',{text:'compiler'});
 await evaluate(`(()=>{
  const {dos,help,midi}=packageDialogs,manager=help.owner.dialogManager;
  if(dos.items.options.length!==1||dos.items.options[0].id!=='compiler')throw Error('Native typing did not filter live');
  dos.filterInput.root.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  if(document.activeElement!==dos.items.choiceElements[0])throw Error('Filter ArrowDown did not focus results');
  typePackageFilter(dos,'');
  manager.open('help-packages');help.setAll(false);
  const selected=help.items.options[0].id,target=help.draft.packages.find(item=>item.id==='tp:7');
  help.items.choiceElements[0].click();typePackageFilter(help,target.label.toUpperCase());
  if(!help.items.options.some(item=>item.id===target.id)||!help.draft.selected.has(selected))throw Error('HELP filter lost the hidden edition');
  help.items.choiceElements[help.items.options.findIndex(item=>item.id===target.id)].click();
  typePackageFilter(help,'');
  if(!help.draft.selected.has(selected)||!help.draft.selected.has(target.id))throw Error('HELP filter did not retain edition marks');
  manager.open('midi-sources');midi.setAll(true);typePackageFilter(midi,'qUaKe');
  if(midi.categories.items.length!==1||midi.items.options.length!==1||midi.items.options[0].name!=='Quake')throw Error('MIDI album filter failed');
  midi.items.choiceElements[0].click();
  const source=midi.draft.sources.find(s=>s.id==='one'),other=midi.draft.sources.find(s=>s.id==='two');
  if(source.albums.find(a=>a.name==='Quake').selected||!source.albums.find(a=>a.name==='Doom').selected
   ||source.all_albums||!other.all_albums||!other.albums[0].selected)throw Error('MIDI selection was stored by filtered row position rather than ID');
  midi.setGroupAll(true);
  if(source.all_albums||source.albums.some(a=>!a.selected))throw Error('Filtered MIDI selection incorrectly included future albums');
  midi.setGroupAll(false);
  if(!source.albums.find(a=>a.name==='Doom').selected||source.albums.find(a=>a.name==='Quake').selected)throw Error('Filtered MIDI deselection changed hidden albums');
  typePackageFilter(midi,'');
  if(midi.categories.items.length!==2||!midi.items.mark(0)||midi.items.mark(1))throw Error('Clearing MIDI filter changed marks');
  typePackageFilter(midi,'no such album 192846');midi.selectAllButton.root.click();
  if(midi.draft.sources.some(s=>!s.selected||!s.all_albums||s.albums.some(a=>!a.selected)))throw Error('Global MIDI select was filtered');
  midi.deselectAllButton.root.click();
  if(midi.draft.sources.some(s=>s.selected||s.all_albums||s.albums.some(a=>a.selected)))throw Error('Global MIDI clear was filtered');
  typePackageFilter(midi,'');
  Object.values(packageDialogs).forEach(v=>v.close());
 })()`);
 for(const kind of ['help','dos','midi']){
  await evaluate(`(async()=>{const v=packageDialogs['${kind}'];v.open();await waitPackages(()=>v.valid,'Screenshot dialog did not load');
   if(v.size.x!==({help:82,dos:90,midi:94}['${kind}'])||v.size.y!==24||v.descriptionBox.bounds.y1!==14)throw Error('Wrong package layout');
   const body=v.content.root.getBoundingClientRect(),frame=v.dialog.getBoundingClientRect();
   if(frame.top<0||frame.bottom>innerHeight||frame.left<0||frame.right>innerWidth)throw Error('Package frame escapes desktop');
   for(const control of [v.filterInput,v.categories,v.items,v.descriptionBox,v.applyButton]){
    const r=control.root.getBoundingClientRect();if(r.right>body.right+1||r.bottom>body.bottom+1)throw Error('Package control escapes dialog');
   }
  })()`);
  const screenshot=await send('Page.captureScreenshot',{format:'png'});
  require('node:fs').writeFileSync(screenshotPrefix+'-'+kind+'.png',Buffer.from(screenshot.data,'base64'));
  await evaluate(`packageDialogs['${kind}'].close()`);
 }
 const antivirusPoint=await evaluate(`(async()=>{
  const v=packageDialogs.dos,TV=window.THelpViewerTV;
  v.open();await waitPackages(()=>v.valid,'DOS catalog test did not open');
  const manifest=JSON.parse(${JSON.stringify(require('node:fs').readFileSync('thelpviewer/config/dos-prompt.json','utf8'))});
  v.draft={categories:manifest.categories,packages:manifest.sources.map(source=>({...source,label:source.title,installed:false})),selected:new Set()};
  v.renderDraft();
  if(v.categories.bounds.x2!==30||v.categories.root.classList.contains('is-h-scrollable')
   ||v.categories.viewport.scrollWidth>v.categories.viewport.clientWidth+1)throw Error('DOS Groups still needs a horizontal scrollbar');
  const required=['utils','volkov-commander-405'];
  if(required.some(id=>!v.draft.selected.has(id)))throw Error('Required packages are not selected');
  v.setAll(true);v.setAll(false);
  if(v.draft.selected.size!==2||required.some(id=>!v.draft.selected.has(id)))throw Error('Global Deselect All removed required packages');
  for(const id of required){
   const source=v.draft.packages.find(item=>item.id===id);
   v.categories.selectItem(v.draft.categories.findIndex(item=>item.id===source.category));
   const index=v.items.options.findIndex(item=>item.id===id),input=v.items.choiceElements[index];
   if(!input.disabled||!v.items.mark(index))throw Error('Required package checkbox is editable');
   input.click();v.items.press(index);v.setGroupAll(false);
   if(!v.items.mark(index)||!v.draft.selected.has(id))throw Error('Required package could be deselected');
  }
  for(let index=0;index<v.draft.categories.length;index++){
   v.categories.selectItem(index);await new Promise(requestAnimationFrame);
   if(v.items.viewport.scrollWidth>v.items.viewport.clientWidth+1)throw Error('DOS names/flags do not fit: '+JSON.stringify({
    category:v.category,size:v.size.x,pane:v.items.size.x,width:v.items.viewport.clientWidth,scroll:v.items.viewport.scrollWidth,
    font:getComputedStyle(v.items.viewport).font,rows:v.items.choiceElements.map(input=>({text:input.parentElement.textContent,width:input.parentElement.lastElementChild.getBoundingClientRect().width}))}));
   const columns=v.items.options.map(item=>Array.from(item.label.slice(0,-(item.label.endsWith('🌐')?2:4))).length);
   if(columns.some(column=>column!==columns[0]))throw Error('Flags are not padded to a common text column');
  }
  if(v.items.root.querySelector('.tv-choice-annotation'))throw Error('Special flag markup remains');
  v.changeBounds(new TV.TVRect(0,0,94,26));v.center();
  if(!v.enabled.root.hidden)throw Error('Hidden MIDI checkbox covers DOS groups');
  if(v.size.x!==94||v.content.size.x!==92||v.items.bounds.x2!==90||v.descriptionBox.bounds.x2!==90
   ||v.closeButtonView.bounds.x2!==90||v.categories.bounds.y2!==v.groupAll.bounds.y2)throw Error('Package controls did not follow frame bounds');
  v.categories.selectItem(v.draft.categories.findIndex(item=>item.id==='games-platform'));
  await new Promise(requestAnimationFrame);
  const flags=Array.from(v.items.root.querySelectorAll('.tv-choice-label')).map(label=>{
   const node=label.firstChild,range=document.createRange();
   range.setStart(node,node.length-4);range.setEnd(node,node.length);return range.getBoundingClientRect();
  });
  const right=v.items.viewport.getBoundingClientRect().right;
  if(flags.length<2||flags.some(flag=>Math.abs(flag.left-flags[0].left)>1||flag.right>right+1))throw Error('Plain-text language flags are misaligned or clipped');
  v.categories.viewport.scrollTop=v.categories.viewport.scrollHeight;v.categories.updateScrollbar();
  await new Promise(requestAnimationFrame);
  const index=v.draft.categories.findIndex(item=>item.id==='antivirus');
  const item=v.categories.viewport.querySelector('[data-tv-list-index="'+index+'"]'),r=item.getBoundingClientRect();
  const x=r.left+20,y=(r.top+r.bottom)/2;
  if(document.elementFromPoint(x,y)?.closest('[data-tv-list-index]')!==item)throw Error('Antivirus row is covered by another view');
  return {x,y};
 })()`);
 await evaluate(`(async()=>{
  const TV=window.THelpViewerTV,owner=packages.owner,manager=owner.dialogManager;
  const statistics=new TV.TVStatisticsDialog();owner.insert(statistics);statistics.open();
  await waitPackages(()=>statistics.sections.length>20,'Statistics did not load');
  const starts=[...statistics.categories.viewport.querySelectorAll('.tv-vlist-text')].map(element=>{
   const text=element.lastChild,range=document.createRange();range.selectNode(text);return range.getBoundingClientRect().left;
  });
  if(Math.max(...starts)-Math.min(...starts)>1)throw Error('Statistics emoji labels are not aligned');
  const icons=statistics.categories.viewport.querySelectorAll('.tv-vlist-icon');
  if(icons.length!==statistics.sections.length)throw Error('Statistics bypassed the shared list icon column');
  statistics.destroy();
  const player=manager.get('midi');player.open();
  await waitPackages(()=>!player.catalogPending,'MIDI catalog did not load');
  player.toggleAdvanced(true);
  player.allTracks=[{id:'test',title:'Track',credit:'Game',available:false}];player.applyFilter();
  player.trackListBox.focusItem(0);
  const colors=element=>[getComputedStyle(element).backgroundColor,getComputedStyle(element).color].join();
  const focused=colors(player.trackListBox.selectedElement());
  player.moreButton.root.focus();const selected=colors(player.trackListBox.selectedElement());
  player.close();
  const progress=new TV.TVProgressDialog('Downloads');owner.insert(progress);
  progress.updateDownloads({active:true,percent:10,errors:0,items:[{id:'test',kind:'dos',label:'Package',state:'running',percent:10}]});
  progress.open();progress.toggleDetails(true);progress.details.focusItem(0);
  if(colors(progress.details.selectedElement())!==focused)throw Error('Downloads/MIDI focused row palettes differ');
  progress.hideButton.root.focus();
  if(colors(progress.details.selectedElement())!==selected)throw Error('Downloads/MIDI unfocused selection palettes differ');
  progress.destroy();
 })()`);
 await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...antivirusPoint});
 await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...antivirusPoint});
 await evaluate(`(()=>{const v=packageDialogs.dos;if(v.category!=='antivirus'||v.items.options.length!==2)throw Error('Mouse click did not open Antivirus');})()`);
 const dosCatalogScreenshot=await send('Page.captureScreenshot',{format:'png'});
 require('node:fs').writeFileSync(screenshotPrefix+'-dos-catalog.png',Buffer.from(dosCatalogScreenshot.data,'base64'));
 await evaluate(`packageDialogs.dos.close()`);
 for(const resource of ['dos','midi']){
  await evaluate(`document.querySelector('[data-tv-command="account-rebuild-${resource}"]').click()`);
  if(await evaluate(`document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView.isOpen()`))throw Error('Rebuild unexpectedly opened Server Configuration');
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
  await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
   const box=document.querySelector('.tv-msgbox-window');
   if(box&&!box.closest('.tv-dialog-overlay').hidden&&box.textContent.includes('Rebuilt.')){resolve();return;}
   if(Date.now()>deadline){reject(Error('Standalone rebuild completion missing'));return;}setTimeout(check,30);
  };check();})`);
  await evaluate(`Array.from(document.querySelectorAll('.tv-msgbox-window [data-tv-command="msgbox-cmd"]')).find(b=>b.textContent.includes('OK')).click()`);
 }
 await evaluate(`(async()=>{const v=document.querySelector('[data-tv-menu-bar]')._tvMenuView,p=v.downloadItem;p.stop();
  const data={active:true,percent:25,errors:0,items:Array.from({length:100},(_,i)=>({id:'dos:'+i,kind:'dos',
   label:'Test package '+i,state:i?'pending':'running',percent:i?0:25,phase:'Downloading',stage:'download',stage_percent:i?null:25}))};
  p.update(data,v);const root=v.rootByItem.get(p),account=v.itemElements.get(v.rightItem),clock=document.querySelector('[data-tv-clock]');
  if(root.hidden||v.itemElements.get(p).textContent!=='↓ 25%'||root.getBoundingClientRect().left<account.getBoundingClientRect().right
   ||root.getBoundingClientRect().right>clock.getBoundingClientRect().left)throw Error('Download progress is not between account and clock');
  v.itemElements.get(p).click();await new Promise(requestAnimationFrame);const popup=v.activePopup;
  if(popup.hidden||!popup.classList.contains('is-scrollable')||popup.getBoundingClientRect().right>innerWidth
   ||!popup.textContent.includes('Test package 99'))throw Error('Shared download menu list/scrollbar is broken: '+JSON.stringify({hidden:popup.hidden,
    scrollable:popup.classList.contains('is-scrollable'),right:popup.getBoundingClientRect().right,width:innerWidth,
    last:popup.textContent.includes('Test package 99'),text:popup.textContent.slice(0,300)}));
  const body=popup.querySelector('.tv-menu-popup-body'),bar=popup.querySelector(':scope > .tv-menu-popup-main > .tv-scrollbar-y');
  const press=(element,x,y)=>{element.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0,clientX:x,clientY:y}));
   document.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0,clientX:x,clientY:y}));};
  const forward=bar.querySelector('[data-role="forward"]'),fr=forward.getBoundingClientRect();
  press(forward,fr.left+fr.width/2,fr.top+fr.height/2);
  if(body.scrollTop<=0||popup.hidden)throw Error('Download menu arrow did not scroll its own viewport');
  const arrowScroll=body.scrollTop,track=bar.querySelector('[data-role="track"]'),tr=track.getBoundingClientRect();
  press(track,tr.left+tr.width/2,tr.bottom-1);
  if(body.scrollTop<=arrowScroll)throw Error('Download menu scrollbar track did not scroll');
  body.scrollTop=0;
  const thumb=bar.querySelector('[data-role="thumb"]'),thumbRect=thumb.getBoundingClientRect();
  thumb.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0,
   clientX:thumbRect.left+thumbRect.width/2,clientY:thumbRect.top+thumbRect.height/2}));
  document.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,buttons:1,
   clientX:thumbRect.left+thumbRect.width/2,clientY:thumbRect.top+thumbRect.height/2+40}));
  document.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0}));
  if(body.scrollTop<=0)throw Error('Download menu scrollbar thumb did not drag');
  const liveScroll=body.scrollTop;p.update(data,v);
  if(body.scrollTop!==liveScroll)throw Error('Download menu poll reset scrollbar position');
  v.itemElements.get(p.showItem).click();await new Promise(requestAnimationFrame);
  if(p.dialog!==packages.progress||p.dialog.getTitle()!=='Downloads'||!p.dialog.isOpen()||p.dialog.modal
   ||p.dialog.details.items.length!==100||p.dialog.helpCtx!==window.THelpViewerTV.TV_HELP_CONTEXTS.hcDownloads)throw Error('Shared Downloads dialog is not reused from menu/content');
  p.dialog.setOperation({state:'building',phase:'Converting',percent:80,processed:8,total:10,downloads:{new_files:3,cached_files:4,bytes:1048576}});
  p.update(data,v);
  if(p.dialog.bar.curValue!==80||!p.dialog.detailsCaption.text.includes('3 new · 4 cached'))throw Error('Download updates erased conversion progress/cache counts');
  p.dialog.setOperation(null);p.dialog.close();
  v.itemElements.get(p).click();await new Promise(requestAnimationFrame);
  const row=p.rows.get('dos:0'),el=v.itemElements.get(row);
  data.percent=50;data.items[0].percent=50;data.items[0].stage_percent=50;p.update(data,v);
  if(v.activePopup!==popup||popup.hidden||v.itemElements.get(row)!==el||!el.textContent.includes('50%'))throw Error('Live update rebuilt/closed the download popup');
  for(const [stage,phase,percent,caption] of [['extract','Extracting',null,'▣'],['convert','Converting',40,'⚙ 40%'],
      ['convert','Converting',100,'⚙ 100%'],['publish','Publishing',null,'⚙']]){
   Object.assign(data.items[0],{stage,phase,stage_percent:percent});p.update(data,v);
   const current=v.itemElements.get(row),marker=p.dialog.details.items[0].label.trim();
   if(v.itemElements.get(p).textContent!==caption.split(' ')[0]+' 50%'||!current.textContent.startsWith(caption.split(' ')[0])
      ||(percent===null&&current.textContent.includes('%'))||!marker.endsWith(caption)
      ||v.activePopup!==popup||popup.hidden||p.completed.subMenu.entries().length!==0)
    throw Error('Phase glyph/percentage/completion is wrong: '+JSON.stringify({stage,caption,actual:v.itemElements.get(p).textContent,text:current.textContent,marker}));
  }
  for(const phase of ['Waiting for source','Waiting for processing','Awaiting publication']){
   Object.assign(data.items[0],{state:'waiting',phase,stage:'install',stage_percent:null});p.update(data,v);
   if(p.rows.get('dos:0').param!==phase.split(' ').at(-1)
     ||v.itemElements.get(p).textContent!=='◷ 50%')throw Error('Waiting reason/batch percentage was lost: '+JSON.stringify({phase,param:p.rows.get('dos:0').param,caption:v.itemElements.get(p).textContent}));
  }
  Object.assign(data.items[0],{state:'running',stage:'download',stage_percent:50,phase:'Downloading'});p.update(data,v);
  data.items.push({id:'midi:new',kind:'midi',label:'DOOM',state:'running',percent:10});p.update(data,v);
  if(v.activePopup.hidden||!v.activePopup.textContent.includes('MIDI: DOOM'))throw Error('Added download did not preserve the open popup');
  data.items.unshift({id:'midi:track:urgent',kind:'midi',label:'Selected song',state:'running',percent:5,priority:-10});p.update(data,v);
  if(v.itemElements.get(p.rows.get('midi:track:urgent')).getBoundingClientRect().top>=v.itemElements.get(row).getBoundingClientRect().top)throw Error('Selected song did not move to the front of the shared menu');
  data.items.slice(0,75).forEach(item=>{item.state='done';item.percent=100;});p.update(data,v);
  const header=v.itemElements.get(p.completed),completePopup=v.submenuControls.get(header).popup;
  if(v.rootControls.get(root).popup.querySelector('.tv-menu-popup-item')!==header
   ||p.completed.subMenu.entries().length!==75||v.itemElements.get(row).closest('.tv-menu-popup')!==completePopup)throw Error('Completed downloads were not moved to the first submenu');
  header.click();await new Promise(requestAnimationFrame);
  if(v.activePopup!==completePopup||completePopup.hidden||!completePopup.classList.contains('is-scrollable'))throw Error('Completed download submenu did not open/scroll');
  const completedBody=completePopup.querySelector('.tv-menu-popup-body'),parentScroll=v.rootControls.get(root).popup.querySelector('.tv-menu-popup-body').scrollTop;
  const completedArrow=completePopup.querySelector(':scope > .tv-menu-popup-main > .tv-scrollbar-y [data-role="forward"]'),ca=completedArrow.getBoundingClientRect();
  press(completedArrow,ca.left+ca.width/2,ca.top+ca.height/2);
  if(completedBody.scrollTop<=0||v.rootControls.get(root).popup.querySelector('.tv-menu-popup-body').scrollTop!==parentScroll)
   throw Error('Completed submenu scrollbar targeted the parent menu');
  completePopup.querySelector('.tv-menu-popup-body').scrollTop=240;
  const completedScroll=completePopup.querySelector('.tv-menu-popup-body').scrollTop;
  data.items[75].state='done';data.items[75].percent=100;p.update(data,v);await new Promise(requestAnimationFrame);
  const updatedComplete=v.submenuControls.get(v.itemElements.get(p.completed)).popup;
  if(v.activePopup!==updatedComplete||updatedComplete.hidden||updatedComplete.querySelector('.tv-menu-popup-body').scrollTop!==completedScroll
   ||p.completed.subMenu.entries().length!==76)throw Error('Live completion closed/reset the open completed submenu');
  document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  data.items.forEach(item=>{item.state='done';item.percent=100;});p.update({active:false,percent:0,errors:0,items:data.items},v);
  if(v.rootByItem.get(p).hidden||v.itemElements.get(p).textContent!=='✓'||p.completed.subMenu.entries().length!==data.items.length)
   throw Error('Finished counter did not clear its percentage while retaining history');
  p.update({active:true,percent:0,errors:0,items:[...data.items,{id:'midi:next-batch',kind:'midi',label:'Next batch',state:'pending',percent:0}]},v);
  if(v.itemElements.get(p).textContent!=='… 0%')throw Error('New batch did not restart its total at zero or retained the completed tick');
  const TV=window.THelpViewerTV,desktop=document.querySelector('.tv-desktop')._tvView;
  const failure={id:'midi:failed-test',kind:'midi',label:"Karl's IT Retro — DOS S: Space Quest: Chapter I – The Sarien Encounter",
   state:'error',percent:0,error:"'ascii' codec can't encode character '\\u2013': "+'Long error details. '.repeat(20)+'Final detail.',retryable:true};
  const failedStatus={active:false,percent:0,errors:1,items:[failure]},requests=[];
  const originalRequest=TV.TVLoginDialog.request;
  TV.TVLoginDialog.request=async(path,method,body)=>{requests.push({path,method,body});return {accepted:true};};
  const actionFinished=()=>new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
   if(!p.actionPending){resolve();return;}if(Date.now()>deadline){reject(Error('Download action did not finish'));return;}setTimeout(check,10);
  };check();});
  const openFailure=async()=>{p.update(failedStatus,v);v.itemElements.get(p).click();await new Promise(requestAnimationFrame);
   v.itemElements.get(p.rows.get(failure.id)).click();await new Promise(resolve=>setTimeout(resolve,0));
   const d=desktop.dialogManager.get('download-action');if(!d?.isOpen())throw Error('Failed menu click did not open an action dialog via TEvent');
   const bounds=d.content.root.getBoundingClientRect();
   if(d.retryButton.root.getBoundingClientRect().bottom>bounds.bottom||d.retryButton.root.disabled===failure.retryable)
    throw Error('Download action layout or retry state is wrong');
   const text=d.firstThat(view=>view instanceof TV.TVStaticText),shown=text.root.textContent.replace(/\\s/g,'');
   if(!shown.includes(failure.label.replace(/\\s/g,''))||!shown.includes(failure.error.replace(/\\s/g,''))
    ||!shown.includes('Removeonlyclearsthisqueueentry;filesarekept.')||text.root.getBoundingClientRect().bottom>d.retryButton.root.getBoundingClientRect().top)
    throw Error('Download failure truncated/overlapped its label, error or notice: '+JSON.stringify({shown,
     label:failure.label.replace(/\\s/g,''),error:failure.error.replace(/\\s/g,''),text:text.root.getBoundingClientRect().toJSON(),button:d.retryButton.root.getBoundingClientRect().toJSON()}));return d;};
  try{
   let d=await openFailure();d.closeButton.click();await new Promise(resolve=>setTimeout(resolve,0));
   if(requests.length||p.actionPending)throw Error('Closing failed download dialog performed an action');
   d=await openFailure();d.dialog.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
   await new Promise(resolve=>setTimeout(resolve,0));if(requests.length||p.actionPending)throw Error('Escape performed a download action');
   d=await openFailure();d.retryButton.root.click();await actionFinished();
   if(requests.length!==1||requests[0].path!=='/api/downloads/action'||requests[0].method!=='POST'
    ||requests[0].body.id!==failure.id||requests[0].body.action!=='retry')throw Error('Retry sent wrong failed item or action');
   failure.retryable=false;d=await openFailure();
   d.firstThat(view=>view instanceof TV.TVButton&&view.command==='download-remove').root.click();
   await actionFinished();
   if(requests.length!==2||requests[1].body.action!=='remove'||p.actionPending)throw Error('Remove did not clear only the chosen queue entry');
   failure.state='blocked';failure.phase='Not started';failure.error='';failure.retryable=true;
   d=await openFailure();
   if(d.title!=='Download not completed')throw Error('Blocked download still looks like an active transfer');
   d.retryButton.root.click();await actionFinished();
   if(requests.length!==3||requests[2].body.action!=='retry')throw Error('Blocked menu row cannot resume via TEvent');
  }finally{TV.TVLoginDialog.request=originalRequest;}
  p.update({active:false,percent:100,errors:0,items:[]},v);
  if(!v.rootByItem.get(p).hidden)throw Error('Idle download indicator stayed visible');
 })()`);
 await send('Emulation.setDeviceMetricsOverride',{width:320,height:700,deviceScaleFactor:1,mobile:false});
 await evaluate(`(async()=>{
  const TV=window.THelpViewerTV,v=document.querySelector('[data-tv-menu-bar]')._tvMenuView,p=v.downloadItem;
  const item={id:'midi:narrow',kind:'midi',label:'A long album title – with Unicode music 🎵',state:'error',percent:0,
   error:'Download failed. '+('Detail with words. ').repeat(5),retryable:true};
  p.update({active:false,percent:0,errors:1,items:[item]},v);
  const task=p.failedItem(p.rows.get(item.id),document.querySelector('.tv-desktop')._tvView);
  await new Promise(resolve=>setTimeout(resolve,0));
  const d=document.querySelector('.tv-desktop')._tvView.dialogManager.get('download-action');
  const rect=d.dialog.getBoundingClientRect(),body=d.content.root.getBoundingClientRect();
  if(rect.left<0||rect.right>innerWidth+1)throw Error('Download failure does not fit a narrow viewport');
  const text=d.firstThat(view=>view instanceof TV.TVStaticText);
  if(!text.root.textContent.replace(/\\s/g,'').includes(item.error.replace(/\\s/g,'')))throw Error('Narrow failure text was truncated');
  const buttons=d.content.children.filter(view=>view instanceof TV.TVButton);
  if(buttons.length!==3||buttons.some(button=>{const r=button.root.getBoundingClientRect();return r.left<body.left||r.right>body.right+1||r.bottom>body.bottom+1;})
   ||buttons[0].root.getBoundingClientRect().top>=buttons[2].root.getBoundingClientRect().top)throw Error('Narrow failure buttons did not wrap inside the frame');
  d.closeButton.click();await task;p.update({active:false,percent:0,errors:0,items:[]},v);
 })()`);
 await send('Emulation.clearDeviceMetricsOverride');
 await evaluate(`(async()=>{
  const player=document.querySelector('.tv-midi-window').closest('.tv-dialog-overlay')._tvView;
  clearTimeout(player.catalogTimer);player.catalogTimer=null;
  if(player.catalogPending)throw Error('Previous MIDI catalog request is still active');
  const catalogFetch=window.fetch,wasOpen=player.isOpen(),synthClass=player.synth.constructor,assetsLoader=synthClass.loadAssets;
  const tracks=[{id:'valid-song',item_id:'valid-song',source_id:'one',
   game:'Doom',title:'Theme',available:true,file:'/api/midi/files/one/theme.mid',cover:''}];
  window.fetch=(url,options)=>String(url)==='/api/midi/catalog'
   ?Promise.resolve(new Response(JSON.stringify({state:'partial',tracks,downloaded:1,total:2,
    errors:['Downloaded data is not a valid-size MIDI file']}),{headers:{'Content-Type':'application/json'}}))
   :catalogFetch(url,options);
  synthClass.loadAssets=()=>Promise.resolve();
  try{if(!wasOpen)player.open();else void player.refreshCatalog();
   await new Promise((resolve,reject)=>{const end=Date.now()+3000;const check=()=>{
    if(!player.catalogPending){resolve();return;}
    if(Date.now()>end){reject(Error('Partial MIDI catalog did not load'));return;}setTimeout(check,10);
   };check();});
   if(player.displayView.statusView.text!=='1/2 ready · 1 download errors'||player.selectedTrack()?.id!=='valid-song')
    throw Error('An unrelated failed album replaced the usable player/catalog status: '+JSON.stringify({open:player.isOpen(),status:player.displayView.statusView.text,track:player.selectedTrack()?.id}));
  }finally{window.fetch=catalogFetch;synthClass.loadAssets=assetsLoader;if(!wasOpen)player.close();}
  const originalFetch=window.fetch;let older,newer;
  window.fetch=(url,options)=>String(url).startsWith('/api/midi/priority/')
   ?new Promise(resolve=>{if(String(url).endsWith('/older'))older=resolve;else newer=resolve;})
   :originalFetch(url,options);
  try{
   const first=player.prioritizeTrack({id:'older',item_id:'older',source_id:'one',title:'Older song'});
   const second=player.prioritizeTrack({id:'newer',item_id:'newer',source_id:'one',title:'Newer song'});
   newer(new Response('{}',{status:200}));await second;older(new Response('{}',{status:404}));await first;
   if(player.pendingPlay?.id!=='newer')throw Error('An older priority response erased the newer playback selection');
  }finally{window.fetch=originalFetch;clearTimeout(player.catalogTimer);player.catalogTimer=null;player.pendingPlay=null;}
 })()`);
 await evaluate(`document.querySelector('[data-tv-command="account-server-configuration"]').click()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  const cfg=document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView;
  if(cfg.backupCount.getData()==='2'&&!(cfg.saveButton.state&0x0100)){resolve();return;}
  if(Date.now()>deadline){reject(Error('Backup setting did not load'));return;}setTimeout(check,30);
 };check();})`);
 await evaluate(`(async()=>{
  const cfg=document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView;
  cfg.backupCount.setData('0');await cfg.saveSettings();
  if(!cfg.status.root.textContent.includes('between 1 and 100'))throw Error('Invalid backup count accepted');
  if((await(await fetch('/api/admin/settings')).json()).backup_count!==2)throw Error('Invalid backup count saved');
  cfg.backupCount.setData('3');cfg.saveButton.root.click();
 })()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=async()=>{
  if((await(await fetch('/api/admin/settings')).json()).backup_count===3){resolve();return;}
  if(Date.now()>deadline){reject(Error('Backup setting was not saved'));return;}setTimeout(check,30);
 };void check();})`);
 await evaluate(`(async()=>{
  const cfg=document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView;
  cfg.close();cfg.open();await cfg.loadSettings();
  if(cfg.backupCount.getData()!=='3')throw Error('Backup count did not persist across reopen');
  const input=cfg.backupCount.root.getBoundingClientRect(),frame=cfg.root.getBoundingClientRect();
  if(input.left<frame.left||input.right>frame.right||input.top<frame.top||input.bottom>frame.bottom)
   throw Error('Backup input is outside the configuration frame');
 })()`);
 await evaluate(`(async()=>{
  const cfg=document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView;
  if(cfg.cacheDays.getData()!=='30')throw Error('Default download cache lifetime did not load');
  cfg.cacheDays.setData('0');await cfg.saveSettings();
  if(!cfg.status.root.textContent.includes('between 1 and 3650'))throw Error('Invalid cache lifetime accepted');
  if((await(await fetch('/api/admin/settings')).json()).download_cache_days!==30)throw Error('Invalid cache lifetime saved');
  cfg.cacheDays.setData('14');await cfg.saveSettings();
  if((await(await fetch('/api/admin/settings')).json()).download_cache_days!==14)throw Error('Cache lifetime not saved');
  cfg.close();cfg.open();await cfg.loadSettings();
  if(cfg.cacheDays.getData()!=='14')throw Error('Cache lifetime did not persist across reopen');
  const frame=cfg.root.getBoundingClientRect();
  for(const control of [cfg.capacity,cfg.backupCount,cfg.cacheDays]){
   const r=control.root.getBoundingClientRect();
   if(r.left<frame.left||r.right>frame.right||r.top<frame.top||r.bottom>frame.bottom)
    throw Error('Numeric server setting extends outside its frame');
  }
 })()`);
 await evaluate(`void document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView.capacity.focus()`);
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'l',code:'KeyL',modifiers:1});
 await send('Input.dispatchKeyEvent',{type:'keyUp',key:'l',code:'KeyL',modifiers:1});
 if(!await evaluate(`document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView.cacheDays.root===document.activeElement`)){
  throw Error('Cache lifetime mnemonic did not focus its input');
 }
 await evaluate(`(()=>{
  const cfg=document.querySelector('.tv-server-configuration-window').closest('.tv-dialog-overlay')._tvView;
  const bounds=cfg.clearCacheButton.root.getBoundingClientRect(),frame=cfg.root.getBoundingClientRect();
  if(bounds.left<frame.left||bounds.right>frame.right||bounds.bottom>frame.bottom)
   throw Error('Clear cache button is outside Server Configuration');
  if(cfg.size.x!==82||cfg.size.y!==27||cfg.status.bounds.y2>cfg.saveButton.bounds.y1)
   throw Error('Cache action expanded/clipped the configuration dialog');
  const actions=[cfg.helpPackagesButton,cfg.dosPackagesButton,cfg.midiSourcesButton,
   cfg.usersButton,cfg.colorsButton,cfg.clearCacheButton];
  for(let i=0;i<actions.length;i++){
   const b=actions[i],r=b.root.getBoundingClientRect();
   if(b.size.x!==24||b.size.y!==2||b.bounds.x1!==2+26*(i%3)||b.bounds.y1!==15+3*Math.floor(i/3))
    throw Error('Server action buttons do not form an equally spaced grid');
   if(r.left<frame.left||r.right>frame.right||r.top<frame.top||r.bottom>frame.bottom)
    throw Error('Server action/shadow extends past its frame');
  }
  if(cfg.saveButton.size.x!==cfg.cancelButton.size.x||cfg.saveButton.bounds.y1!==cfg.cancelButton.bounds.y1||
   cfg.cancelButton.bounds.x2!==cfg.clearCacheButton.bounds.x2)
   throw Error('Save/Cancel are not aligned below the action grid');
  window.cacheTest={cfg,fetch:window.fetch,calls:0};
  window.fetch=async function(input,options){
   if(String(input)==='/api/admin/cache/clear'){
    cacheTest.calls++;if(options?.method!=='POST')throw Error('Cache cleanup is not POST');
    return new Response(JSON.stringify({files:3,bytes:1048576}),{status:200,headers:{'Content-Type':'application/json'}});
   }return cacheTest.fetch.call(this,input,options);
  };
  cfg.clearCacheButton.root.click();
 })()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  const box=document.querySelector('.tv-msgbox-window');
  if(box&&!box.closest('.tv-dialog-overlay').hidden&&box.textContent.includes('Delete cached HELP')){
   if(!box.textContent.includes('all original HELP and licence files')||!box.textContent.includes('may not be downloadable again')){
    reject(Error('Cache confirmation does not warn about manual HELP original deletion'));return;
   }resolve();return;}
  if(Date.now()>deadline){reject(Error('Cache confirmation missing'));return;}setTimeout(check,20);
 };check();})`);
 await evaluate(`document.querySelector('.tv-msgbox-window .tv-dialog-close-control').click()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(!cacheTest.cfg.clearingCache){if(cacheTest.calls)reject(Error('Title close deleted cache'));else resolve();return;}
  if(Date.now()>deadline){reject(Error('Cancelled cache cleanup stayed busy'));return;}setTimeout(check,20);
 };check();})`);
 await evaluate(`cacheTest.cfg.clearCacheButton.root.click()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  const box=document.querySelector('.tv-msgbox-window');
  if(box&&!box.closest('.tv-dialog-overlay').hidden&&box.textContent.includes('Delete cached HELP')){resolve();return;}
  if(Date.now()>deadline){reject(Error('Second cache confirmation missing'));return;}setTimeout(check,20);
 };check();})`);
 await evaluate(`Array.from(document.querySelectorAll('.tv-msgbox-window [data-tv-command="msgbox-cmd"]')).find(b=>b.textContent.includes('OK')).click()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  const box=document.querySelector('.tv-msgbox-window');
  if(box&&!box.closest('.tv-dialog-overlay').hidden&&box.textContent.includes('Removed 3 files')){
   if(!box.textContent.includes('downloads and HELP originals')){reject(Error('Cache result omits original files'));return;}
   resolve();return;}
  if(Date.now()>deadline){reject(Error('Cache result missing'));return;}setTimeout(check,20);
 };check();})`);
 await evaluate(`document.querySelector('.tv-msgbox-window .tv-dialog-close-control').click()`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
  if(!cacheTest.cfg.clearingCache){
   window.fetch=cacheTest.fetch;if(cacheTest.calls!==1)reject(Error('Cache cleared more than once'));else resolve();return;
  }if(Date.now()>deadline){reject(Error('Cache action stayed busy'));return;}setTimeout(check,20);
 };check();})`);
 const serverCacheScreenshot=await send('Page.captureScreenshot',{format:'png'});
 require('node:fs').writeFileSync(screenshotPrefix+'-server-cache.png',Buffer.from(serverCacheScreenshot.data,'base64'));
 await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'F1',code:'F1',bubbles:true,cancelable:true}))`);
 await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+10000;const check=()=>{
   if(document.body.textContent.includes('Configuration groups HELP Packages, DOS Packages, MIDI Sources')){resolve();return;}
  if(Date.now()>deadline){reject(Error('Configuration F1 did not open the updated native HELP topic'));return;}setTimeout(check,50);
 };check();})`);
 const restored={v:1,a:1,z:[0,1],w:[
  {t:'dlg',name:'help-packages',g:[0,0,94,26,0]},
  {t:'dlg',name:'dos-packages',g:[0,42,94,26,0]}]};
 await send('Page.navigate',{url:url+'?package-test=restore#tv=1.'+Buffer.from(JSON.stringify(restored)).toString('base64url')});
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+5000;const check=()=>{
  const v=document.querySelector('.tv-dos-packages-window')?.closest('.tv-dialog-overlay')?._tvView;
  if(v?.valid&&v.items.options.length){resolve();return;}
  if(Date.now()>end){reject(Error('Restored DOS dialog did not load: '+JSON.stringify({url:location.href,
   open:v?.isOpen(),valid:v?.valid,text:document.body.textContent.slice(-500)})));return;}setTimeout(check,20);
 };check();})`);
 const checkbox=await evaluate(`(async()=>{await new Promise(requestAnimationFrame);const v=document.querySelector('.tv-dos-packages-window').closest('.tv-dialog-overlay')._tvView;
  const input=v.groupAll.choiceElements[0];
  if(v.size.x!==94||v.size.y!==26||v.descriptionBox.bounds.x2!==90||v.content.size.x!==92)
   throw Error('URL restoration stretched only the package frame');
  if(v.groupAll.getState(window.THelpViewerTV.sfDisabled)||input.disabled||v.groupAll.root.getAttribute('aria-disabled')==='true')
   throw Error('Restored category checkbox is disabled');
  const r=input.parentElement.getBoundingClientRect();return {x:r.left+10,y:r.top+r.height/2};})()`);
 await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',buttons:1,clickCount:1,...checkbox});
 await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',buttons:0,clickCount:1,...checkbox});
 await evaluate(`(()=>{const v=document.querySelector('.tv-dos-packages-window').closest('.tv-dialog-overlay')._tvView;
  if(!v.groupAll.mark(0)||!v.items.options.every((item,index)=>v.items.mark(index)))
   throw Error('Restored category checkbox ignores real mouse input: '+JSON.stringify({mark:v.groupAll.mark(0),
    target:document.elementFromPoint(${checkbox.x},${checkbox.y})?.outerHTML?.slice(0,300),
    active:v.manager.activeTarget,dialog:v.manager.get(v.manager.activeTarget)?.getTitle()}));})()`);
 if(statisticsFailures.length)throw Error('Managed dialogs generated invalid statistics events: '+statisticsFailures.join(','));
 socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
'''
                result = subprocess.run([NODE, "-e", script, debugging_port, app_url, str(tmp_path / "packages")],
                                        capture_output=True, text=True, timeout=40)
                assert result.returncode == 0, result.stderr
                assert json.loads((tmp_path / "midi-settings.json").read_text()) == {"sources": [], "albums": {"one": None, "two": None}}
            finally:
                chrome.terminate()
                chrome.wait(timeout=5)
    finally:
        server.terminate()
        server.wait(timeout=5)
