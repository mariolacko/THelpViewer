"""Real browser modules use the same views, events and chrome in both shells."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_search_index, _wait_for_url
from thelpviewer.server.converter.base import HelpDocument
from thelpviewer.server.converter.writers.html import HelpHtmlRenderer


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Chrome and Node.js are required")
@pytest.mark.parametrize("shell", ["bundle", "page", "export"])
def test_shared_views_geometry_palette_and_events(tmp_path, shell):
    assets = tmp_path / "assets"
    shutil.copytree(Path("www/assets"), assets, ignore=shutil.ignore_patterns("dos"))
    empty = tmp_path / "empty.json"
    empty.write_text('{"sources":[]}')
    for name in ("README.md", "CHANGELOG.md"):
        (tmp_path / name).write_text(f"# {Path(name).stem}\n\nIsolated browser fixture.\n")
    helps = tmp_path / "helps"
    helps.mkdir(); (helps / "catalog.json").write_text("[]")
    html = Path("www/index.html").read_text()
    if shell in {"page", "export"}:
        renderer = HelpHtmlRenderer(HelpDocument(
            format_name="thelp", source_name="Frame.HLP", topics=[], index_entries=[],
        ))
        html = renderer.render_index_page().replace('src="search-index.js?', 'src="assets/search-index.js?')
        if shell == "page":
            html = html.replace('<div class="tv-desktop">', '<div class="tv-desktop" data-tv-bundle-desktop>')
        (assets / "search-index.js").write_text(renderer.render_search_index_script())
    index = tmp_path / "index.html"
    index.write_text(html)
    if shell == "export":
        # Serve the standalone shell without the public bundle-only HTML adapter.
        (assets / "export.html").write_text(html.replace('<head>', '<head><base href="/">', 1))
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    log = (tmp_path / "server.log").open("w")
    server = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=log, stderr=log, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
            "THELP_STATE_DIR": str(tmp_path / "var"), "THELP_DATA_DIR": str(tmp_path / "data"),
            "THELP_HELPS_DIR": str(helps), "THELP_DOCS_DIR": str(tmp_path / "docs"),
            "THELP_README_PATH": str(tmp_path / "README.md"), "THELP_CHANGELOG_PATH": str(tmp_path / "CHANGELOG.md"),
            "THELP_STATISTICS_PATH": str(tmp_path / "data/statistics.sqlite3"),
            "THELP_SOURCES_DIR": str(tmp_path / "sources"), "THELP_DOWNLOADS_DIR": str(tmp_path / "downloads"),
            "THELP_ASSETS_DIR": str(assets), "THELP_INDEX_PATH": str(index),
            "THELP_DOS_CONFIG_PATH": str(empty), "THELP_MIDI_SOURCES_PATH": str(empty),
            "THELP_AUTH_ORIGIN": url.rstrip("/"), "THELP_DEV_AUTO_LOGIN": "0"})
    chrome = None
    try:
        _wait_for_url(url + "healthz")
        # Startup indexing can open its own progress dialog; finish that fixture
        # work before asserting active windows and menu geometry.
        _wait_for_search_index(url + "api/search/status", timeout=30.0)
        chrome = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--remote-debugging-port=0", "--user-data-dir=" + str(tmp_path / "chrome"), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        debugging = _wait_for_file(tmp_path / "chrome/DevToolsActivePort").splitlines()[0]
        script = r'''
const [port,url,outputDirectory,shell]=process.argv.slice(1);
(async()=>{
 const target=await(await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
 let seq=0;const pending=new Map(),errors=[];
 socket.addEventListener('message',event=>{const message=JSON.parse(String(event.data));
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails.exception?.description||message.params.exceptionDetails.text);
  if(pending.has(message.id)){const p=pending.get(message.id);pending.delete(message.id);message.error?p.reject(Error(message.error.message)):p.resolve(message.result);}});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});
  if(result.exceptionDetails)throw Error((result.exceptionDetails.exception?.description||result.exceptionDetails.text)+'\n'+errors.join('\n'));return result.result.value;};
 await send('Runtime.enable');await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1200,height:900,deviceScaleFactor:1,mobile:false});
 await send('Emulation.setFocusEmulationEnabled',{enabled:true});
 await send('Page.navigate',{url:shell==='export'?url+'assets/export.html':url});
 await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+15000;const check=()=>{
  const program=document.querySelector('.tv-desktop')?._tvView?.owner;
  if(program?.dialogManager){Promise.resolve(program._catalogReady).then(()=>{window.program=program;program.dialogManager.get('welcome')?.destroy();resolve();},reject);return;}
  if(Date.now()>end){reject(Error('TVision program missing'));return;}setTimeout(check,50);};check();})`);
 await evaluate(`(()=>{
  const TV=THelpViewerTV,manager=program.dialogManager;
  const view=new TV.TVWindow(new TV.TVRect(4,3,52,16),'Shared controls');
  view.panel=new TV.TVGroup(new TV.TVRect(1,1,46,10)).insertAll([
   new TV.TVStaticText(new TV.TVRect(1,1,40,3),'Shared TVision controls'),
   new TV.TVButton(new TV.TVRect(1,4,16,6),'~P~ing','probe-ping')]);
  view.nested=new TV.TVGroup(new TV.TVRect(3,6,43,9));
  view.nested.insert(new TV.TVStaticText(new TV.TVRect(0,0,20,1),'Nested bounds'));
  view.panel.growMode=TV.gfGrowHiX|TV.gfGrowHiY;view.panel.children[1].growMode=TV.gfGrowLoX|TV.gfGrowHiX;
  view.nested.growMode=TV.gfGrowHiX|TV.gfGrowLoY|TV.gfGrowHiY;view.nested.children[0].growMode=TV.gfGrowHiX;
  view.input=new TV.TVInputLine(new TV.TVRect(20,4,42,5),40);view.input.growMode=TV.gfGrowHiX;
  view.panel.insert(view.input);view.panel.insert(view.nested);view.insert(view.panel);
  const root=TV.TVView._fromHTML(view.draw());program.desktopView.root.append(root);view.resolve(root);program.desktopView.insert(view);
  root._tvWindowView=view;view.resizer=new TV.TurboVisionWindowResizer(root,'probe');
  manager.registerWindow('probe',root,{close:()=>{manager.unregisterWindow('probe');view.destroy();root.remove();},zoom:()=>view.zoom()});
  manager.activateWindow('probe');view.focus();window.probe=view;
  window.host={open:async()=>{manager.activateWindow('probe');view.focus();return view;},activate:()=>manager.activateWindow('probe')};
 })()`);
 await evaluate(`(async()=>{
  await document.fonts.ready;const TV=THelpViewerTV,focus=document.createElement('button');
  document.body.append(focus);focus.focus();window.saverFocus=focus;
  window.assertSaverExtent=()=>{
   const saver=TV.TVScreenSaver.active,area=saver.overlay.getBoundingClientRect(),cell=TV.measureCells();
   for(const part of [saver.canvas,...saver.canvas.querySelectorAll('canvas')]){
    const rect=part.getBoundingClientRect();
    if(Math.abs(rect.left-area.left)>1||Math.abs(rect.top-area.top)>1
     ||Math.abs(rect.width-area.width)>1||Math.abs(rect.height-area.height)>1)
     throw Error('Saver text/pixel surface escaped its viewport bounds');
   }
   if(saver.cols!==Math.floor(area.width/cell.width)||saver.rows!==Math.floor(area.height/cell.height)
    ||Math.abs(saver.size.x*cell.width-area.width)>1||Math.abs(saver.size.y*cell.height-area.height)>1)
    throw Error('Saver model lost fractional viewport cells');
  };
  const previous=document.documentElement.style.getPropertyValue('--tv-cell-size');
  try{for(const Saver of Object.values(TV.TVScreenSaver.modes))for(const font of [14,16]){
   document.documentElement.style.setProperty('--tv-cell-size',font+'px');window.dispatchEvent(new Event('resize'));
   const saver=new Saver();saver.start();await new Promise(requestAnimationFrame);assertSaverExtent();
   saver.stop();if(saver.timerId!==null||TV.TVScreenSaver.active||document.activeElement!==focus||!saver.overlay.hidden)
    throw Error('Stopping saver retained its timer/overlay or lost focus');
  }}finally{document.documentElement.style.setProperty('--tv-cell-size',previous);window.dispatchEvent(new Event('resize'));}
  new TV.TVScreenSaverProjector().start();assertSaverExtent();
 })()`);
 await send('Emulation.setDeviceMetricsOverride',{width:853,height:677,deviceScaleFactor:1,mobile:false});
 await evaluate(`(async()=>{await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);assertSaverExtent();
  THelpViewerTV.TVScreenSaver.stop();if(document.activeElement!==saverFocus)throw Error('Resized saver lost original focus');saverFocus.remove();})()`);
 await send('Emulation.setDeviceMetricsOverride',{width:1200,height:900,deviceScaleFactor:1,mobile:false});
 await evaluate(`(async()=>{await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);})()`);
 if(shell==='export'){
  await evaluate(`(async()=>{
   await document.fonts.ready;const TV=THelpViewerTV,view=window.probe,input=view.input;
   if(program.constructor.name!=='TVApplication')throw Error('Export did not start the generated-page application');
   const host=program.dialogManager.hostWindow._tvView;
   if(host.sizeLimits().min.x!==82||host.sizeLimits().min.y!==24||program.resizers[0].defaultSize.cols!==82||program.resizers[0].defaultSize.rows!==24)throw Error('Export lost the source HELP size/minimum');
   const original=view.getBounds(),root=view.root;input.setData('export screen');input.focus();input.root.setSelectionRange(1,5);
   window.assertExportScreen=()=>{
    const cell=TV.measureCells(),screen=program.root.getBoundingClientRect(),desktop=program.desktopView.root.getBoundingClientRect();
    const menu=program.menuBar.root.getBoundingClientRect(),status=program.statusLine.root.getBoundingClientRect();
    const near=(a,b)=>{if(Math.abs(a-b)>1)throw Error('Export screen geometry differs');};
    near(menu.top,screen.top);near(menu.height,cell.height);near(desktop.top,menu.bottom);near(desktop.bottom,status.top);near(status.bottom,screen.bottom);near(status.height,cell.height);
    for(const child of [program.menuBar,program.desktopView,program.statusLine]){
     near(child.root.getBoundingClientRect().width,screen.width);
     if(child.owner!==program||program.children.filter(candidate=>candidate===child).length!==1)throw Error('Export lost owned screen chrome');
    }
   };
   assertExportScreen();window.exportScreenProbe={view,input,original,root};
  })()`);
  for(const [width,height] of [[640,760],[1183,867]]){
   await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
   await evaluate(`new Promise((resolve,reject)=>{const end=Date.now()+5000;const check=()=>{
    if(Math.abs(program.root.clientHeight-program.size.y*THelpViewerTV.measureCells().height)<1&&Math.abs(program.root.clientWidth-program.size.x*THelpViewerTV.measureCells().width)<1){resolve();return;}
    if(Date.now()>end){reject(Error('Export resize did not update screen bounds'));return;}requestAnimationFrame(check);};check();})`);
   await evaluate(`(()=>{assertExportScreen();const {view,input,original,root}=exportScreenProbe;
    if(view.root!==root||!view.bounds.equals(original)||input.getData()!=='export screen'||document.activeElement!==input.root||input.root.selectionStart!==1||input.root.selectionEnd!==5)throw Error('Export resize lost normal window or input state');})()`);
  }
  if(errors.length)throw Error(errors.join('\n'));socket.close();return;
 }
 await evaluate(`(async()=>{
  const TV=THelpViewerTV,host=window.host,manager=program.dialogManager;
  const view=await host.open('both');window.probe=view;
  if(document.activeElement!==view.root||view.root.tabIndex!==-1)throw Error('Opening a module window did not focus its shared TVWindow root');
  if(getComputedStyle(view.root).outlineStyle!=='none')throw Error('Native focus outline obscures the TVWindow frame');
  await document.fonts.ready;
  const cell=TV.measureCells(),panel=view.panel,nested=view.nested,button=panel.children[1],root=button.root;
  {
  const textFont=getComputedStyle(document.body).fontFamily,chromeFont=getComputedStyle(program.menuBar.root).fontFamily;
  for(const element of [view.root,view.input.root,button.root,nested.root]){
   const style=getComputedStyle(element);
   if(style.fontFamily!==textFont||parseFloat(style.fontSize)!==cell.height||parseFloat(style.lineHeight)!==cell.height
    ||style.fontKerning!=='none'||style.fontVariantLigatures!=='none'||style.fontSynthesis!=='none')throw Error('Text/control typography stopped inheriting fixed VGA metrics');
  }
  for(const element of [program.menuBar.root.querySelector('.tv-menu-label'),program.statusLine.root.querySelector('.tv-status-label'),
   view.root.querySelector('.tv-border-corner'),view.root.querySelector('.tv-window-caption'),view.root.querySelector('.tv-scroll-arrow')]){
   if(element&&getComputedStyle(element).fontFamily!==chromeFont)throw Error('Chrome descendant lost its inherited CP437 font');
  }
  }
  const paintedBackground=element=>{
   for(let part=element;part;part=part.parentElement){
    const color=getComputedStyle(part).backgroundColor;
    if(color!=='rgba(0, 0, 0, 0)')return color;
   }
   return 'rgba(0, 0, 0, 0)';
  };
  const expectDOSPaint=(element,attribute)=>{
   const rgb=hex=>'rgb('+hex.slice(1).match(/../g).map(value=>parseInt(value,16)).join(', ')+')';
   const style=getComputedStyle(element);
   if(style.color!==rgb(TV.DOS_COLORS[attribute&15])||style.backgroundColor!==rgb(TV.DOS_COLORS[(attribute>>4)&15]))
    throw Error('Native DOS palette differs: '+element.className+' '+style.color+' / '+style.backgroundColor+' expected '+attribute);
  };
  const assertScreen=()=>{
   const cell=TV.measureCells(),surface=program.root.getBoundingClientRect();
   const near=(actual,expected)=>{if(Math.abs(actual-expected)>1)throw Error('Program screen bounds differ: '+actual+' / '+expected);};
   if(program.root!==document.querySelector('.tv-app')||['grid','flex'].includes(getComputedStyle(program.root).display))throw Error('Screen layout still depends on CSS tracks');
   for(const child of [program.menuBar,program.desktopView,program.statusLine]){
    if(child.owner!==program||program.children.filter(value=>value===child).length!==1)throw Error('Screen chrome is not uniquely owned');
    const rect=child.root.getBoundingClientRect();near(rect.left,surface.left);near(rect.width,surface.width);
   }
   const menu=program.menuBar.root.getBoundingClientRect(),desktop=program.desktopView.root.getBoundingClientRect(),status=program.statusLine.root.getBoundingClientRect();
   near(menu.top,surface.top);near(menu.height,cell.height);near(desktop.top,menu.bottom);
   near(desktop.bottom,status.top);near(status.height,cell.height);near(status.bottom,surface.bottom);
   const background=program.desktopView.root.querySelector('[data-tv-desktop-pattern]'),pattern=background.getBoundingClientRect();
   for(const edge of ['left','right','top','bottom'])near(pattern[edge],desktop[edge]);
   if(getComputedStyle(program.desktopView.root).padding!=='0px'||!background.textContent.includes('░'))throw Error('Desktop retains CSS padding or lost its pattern');
   const node=background.firstChild;program.desktopView.drawView();
   if(background.firstChild!==node)throw Error('Unchanged desktop redraw replaced its text');
  };
  assertScreen();
  const surface=program.root,previousWidth=surface.style.width,previousHeight=surface.style.height;
  const previousFont=document.documentElement.style.getPropertyValue('--tv-cell-size'),normalBounds=view.getBounds(),normalRoot=view.root,screenInput=view.input;
  screenInput.focus();screenInput.setData('screen resize');screenInput.root.setSelectionRange(2,7);
  try{
   for(const [width,height,font] of [[937,733,14],[1183,867,16]]){
    surface.style.width=width+'px';surface.style.height=height+'px';document.documentElement.style.setProperty('--tv-cell-size',font+'px');
    window.dispatchEvent(new Event('resize'));await new Promise(requestAnimationFrame);assertScreen();
    if(view.root!==normalRoot||!view.bounds.equals(normalBounds)||document.activeElement!==screenInput.root
     ||screenInput.getData()!=='screen resize'||screenInput.root.selectionStart!==2||screenInput.root.selectionEnd!==7)throw Error('Screen resize changed a normal window, focused input or selection');
   }
  }finally{
   surface.style.width=previousWidth;surface.style.height=previousHeight;document.documentElement.style.setProperty('--tv-cell-size',previousFont);window.dispatchEvent(new Event('resize'));
  }
  assertScreen();
  {
   const surface=document.createElement('section'),header=document.createElement('header'),desktop=document.createElement('div'),footer=document.createElement('footer');
   surface.style.cssText='position:absolute;width:640px;height:400px;visibility:hidden';
   desktop.className='tv-desktop';desktop.innerHTML='<pre class="tv-desktop-pattern" data-tv-desktop-pattern="░"></pre>';
   header.className='tv-menu-bar';footer.className='tv-status-line';surface.append(header,desktop,footer);document.body.append(surface);
   const screen=new TV.TVProgram(),area=new TV.TVDesktop(),bar=new TV.TVMenuBar(new TV.TVRect(),new TV.TVMenu()),status=new TV.TVStatusLine(new TV.TVRect());
   const near=(actual,expected)=>{if(Math.abs(actual-expected)>1)throw Error('Optional screen chrome bounds differ');};
   try{
    screen.bindRoot(surface);area.bindRoot(desktop);screen.insert(area);
    near(desktop.clientHeight,400);
    header.innerHTML=bar.draw();bar.bindRoot(header);screen.insert(bar);screen.insert(bar);
    status.bindRoot(footer);status.render();screen.insert(status);
    near(desktop.clientHeight,400-2*TV.measureCells().height);
    if(screen.children.length!==3||screen.menuBar!==bar||screen.desktopView!==area||screen.statusLine!==status)throw Error('Program did not retain its owned screen views');
    const replacement=new TV.TVMenuBar(new TV.TVRect(),new TV.TVMenu());header.innerHTML=replacement.draw();replacement.bindRoot(header);screen.insert(replacement);
    if(bar.owner||screen.children.includes(bar)||screen.children.length!==3)throw Error('Replacing menu retained a stale owner');
    screen.remove(status);near(desktop.clientHeight,400-TV.measureCells().height);
    screen.remove(replacement);near(desktop.clientHeight,400);
    screen.changeBounds(new TV.TVRect(2,3,72,28));near(desktop.clientWidth,70*TV.measureCells().width);near(desktop.clientHeight,25*TV.measureCells().height);
    screen.bindRoot(null);const bounds=screen.getBounds();surface.style.width='500px';window.dispatchEvent(new Event('resize'));
    if(!screen.bounds.equals(bounds))throw Error('Detached program retained its screen resize listener');
    replacement.bindRoot(null);
   }finally{screen.bindRoot(null);bar.bindRoot(null);status.destroy();area.bindRoot(null);surface.remove();}
  }
  {
   const input=view.input,palette=TV.buildPaletteFromCurrentStyle(),changed=TV.cloneColorPalette(palette);
   const leaf=new TV.TVMenuItem('~L~eaf','palette-leaf',0,0,'Ctrl-L');
   const blocked=new TV.TVMenuItem('~B~locked','palette-blocked').setDisabled(true);
   const deep=new TV.TVMenuItem('~D~eep','palette-deep'),branch=new TV.TVSubMenu('~N~ested').append(deep);
   const top=new TV.TVSubMenu('~P~alette').append(leaf).append(blocked).append(branch);
   const bar=new TV.TVMenuBar(new TV.TVRect(0,0,80,1),new TV.TVMenu(top));
   const action=new TV.TVStatusItem('~A~ction',0,'palette-status'),disabled=new TV.TVStatusItem('~O~ff',0,'palette-off').setDisabled(true);
   const line=new TV.TVStatusLine(new TV.TVRect(0,0,80,1),new TV.TVStatusDef(0,65535,[action,disabled]));
   const anchor=new TV.TVStatusLink('~W~eb','https://example.test/palette');line.rightItems=[anchor];
   const header=document.createElement('div'),footer=document.createElement('div');
   header.className='tv-menu-bar';footer.className='tv-status-line';header.style.width=footer.style.width='80ch';
   program.desktopView.root.append(header,footer);header.innerHTML=bar.draw();bar.bindRoot(header);line.bindRoot(footer);line.render();
   try{
    for(const [index,attribute] of [[2,0x17],[3,0x18],[4,0x1e],[5,0x2f],[6,0x28],[7,0x2c]])TV.setColorPaletteAttribute(changed,index,attribute);
    TV.applyColorPalette(changed);await new Promise(requestAnimationFrame);input.focus();
    const topNode=bar.itemElements.get(top),leafNode=bar.itemElements.get(leaf),disabledNode=bar.itemElements.get(blocked);
    expectDOSPaint(header,0x17);expectDOSPaint(topNode,0x17);expectDOSPaint(topNode.querySelector('.tv-hotkey'),0x1e);
    bar.openMenu(bar.menuRoots[0],{focusFirst:false});await new Promise(requestAnimationFrame);
    expectDOSPaint(topNode,0x2f);expectDOSPaint(topNode.nextElementSibling,0x17);expectDOSPaint(disabledNode,0x18);
    bar.markSelected(leafNode,false);expectDOSPaint(leafNode,0x2f);expectDOSPaint(leafNode.querySelector('.tv-hotkey'),0x2c);
    const branchNode=bar.itemElements.get(branch);bar.markSelected(branchNode,false);bar.openSubmenu(branchNode,{focusFirst:false});
    await new Promise(requestAnimationFrame);expectDOSPaint(leafNode,0x17);expectDOSPaint(branchNode,0x2f);
    expectDOSPaint(branchNode.nextElementSibling,0x17);bar.markSelected(bar.itemElements.get(deep),false);expectDOSPaint(bar.itemElements.get(deep),0x2f);
    bar.closeMenus({restoreFocus:false});
    topNode.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));expectDOSPaint(topNode,0x2f);
    topNode.dispatchEvent(new MouseEvent('mouseout',{bubbles:true,relatedTarget:input.root}));expectDOSPaint(topNode,0x17);
    blocked.setDisabled(false);bar.updateItem(blocked);expectDOSPaint(disabledNode,0x17);blocked.setDisabled(true);bar.updateItem(blocked);expectDOSPaint(disabledNode,0x18);
    expectDOSPaint(footer,0x17);expectDOSPaint(line.itemElements.get(disabled),0x18);
    for(const item of [action,anchor]){
     const element=line.itemElements.get(item);expectDOSPaint(element,0x17);
     element.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));expectDOSPaint(element,0x2f);expectDOSPaint(element.querySelector('.tv-hotkey'),0x2c);
     element.dispatchEvent(new MouseEvent('mouseout',{bubbles:true,relatedTarget:input.root}));expectDOSPaint(element,0x17);
     element.focus();expectDOSPaint(element,0x2f);
     if(getComputedStyle(element).outlineStyle!=='none')throw Error('Native menu/status focus added a browser outline');
     input.focus();expectDOSPaint(element,0x17);
    }
   }finally{bar.destroy();line.destroy();header.remove();footer.remove();TV.applyColorPalette(palette);await new Promise(requestAnimationFrame);input.focus();}
  }
  const assertFrameTitle=caption=>{
   if(!caption||caption.hidden)return;
   const cell=TV.measureCells(),r=caption.getBoundingClientRect(),text=caption.firstElementChild,t=text?.getBoundingClientRect();
   if(!text?.classList.contains('tv-frame-title')||getComputedStyle(caption).paddingLeft!=='0px'||getComputedStyle(caption).paddingRight!=='0px'
    ||Math.abs(t.left-r.left-cell.width)>1||Math.abs(t.top-r.top)>1||Math.abs(t.width-Math.max(0,r.width-2*cell.width))>1
    ||Math.abs(t.height-cell.height)>1)throw Error('Frame caption does not use character bounds for its inset text');
  };
  const assertFrameControl=control=>{
   if(!control||control.hidden)return;
   const cell=TV.measureCells(),r=control.getBoundingClientRect(),glyph=control.querySelector('.tv-close-glyph,.tv-zoom-glyph,.tv-dialog-title-control-glyph'),g=glyph?.getBoundingClientRect();
   if(['grid','inline-grid','flex','inline-flex'].includes(getComputedStyle(control).display)
    ||Math.abs(r.width-3*cell.width)>1||Math.abs(r.height-cell.height)>1||!glyph
    ||Math.abs(g.left-r.left-cell.width)>1||Math.abs(g.top-r.top)>1||Math.abs(g.width-cell.width)>1||Math.abs(g.height-cell.height)>1)
    throw Error('Frame control glyphs or hit area do not fill three character cells');
   const passive=control.querySelector('.tv-frame-passive');
   if(passive){
    const inactive=control.classList.contains('is-frame-control-passive');
    if(passive.hidden===inactive||getComputedStyle(control,'::after').content!=='none')throw Error('Passive zoom still depends on a CSS pseudo-element');
    if(inactive){const p=passive.getBoundingClientRect();
     if(Math.abs(p.left-r.left)>1||Math.abs(p.top-r.top)>1||Math.abs(p.width-r.width)>1||Math.abs(p.height-r.height)>1
      ||passive.textContent!=='───'||getComputedStyle(glyph).visibility!=='hidden'
      ||getComputedStyle(passive).color!==getComputedStyle(control.closest('[data-tv-window]').querySelector('.tv-border-corner')).color)
      throw Error('Passive zoom leaves an incomplete or incorrectly colored frame');
    }
   }
  };
  const assertWindowFrame=windowView=>{
   const cell=TV.measureCells();
   const owner=windowView.root,rect=owner.getBoundingClientRect(),shell=owner.firstElementChild;
   const [top,body]=shell.children,[left,client,right,bottom]=body.children;
   const near=(actual,expected)=>{if(Math.abs(actual-expected)>1)throw Error('Window frame bounds differ: '+actual+' / '+expected);};
   if(owner._tvFrame!==windowView.frame||[shell,top,body,bottom].some(part=>['grid','flex'].includes(getComputedStyle(part).display)))throw Error('Window frame still relies on CSS layout');
   if(getComputedStyle(top).cursor!==(owner.classList.contains('is-maximized')?'default':'move'))throw Error('Window Zoom changed its title cursor rule');
   const t=top.getBoundingClientRect(),b=bottom.getBoundingClientRect(),c=client.getBoundingClientRect();
   near(t.left,rect.left);near(t.top,rect.top);near(t.width,rect.width);near(t.height,cell.height);
   near(c.left,rect.left+cell.width);near(c.top,t.bottom);near(c.width,rect.width-2*cell.width);near(c.bottom,b.top);
   near(b.left,rect.left);near(b.right,rect.right);near(b.bottom,rect.bottom);near(b.height,cell.height);
   const viewport=client.firstElementChild.firstElementChild.getBoundingClientRect();
   near(viewport.left,c.left);near(viewport.top,c.top);near(viewport.width,c.width);near(viewport.height,c.height);
   for(const [side,start,end] of [[left,rect.left,c.left],[right,c.right,rect.right]]){
    const s=side.getBoundingClientRect();near(s.left,start);near(s.right,end);near(s.top,c.top);near(s.bottom,c.bottom);
   }
   for(const row of [top,bottom]){let edge=rect.left;
    for(const part of row.children){if(part.hidden)continue;const p=part.getBoundingClientRect();near(p.left,edge);near(p.height,cell.height);edge=p.right;}
    near(edge,rect.right);
   }
   const caption=top.querySelector('.tv-window-caption');
   assertFrameTitle(caption);
   top.querySelectorAll('.tv-close-control,.tv-zoom-control').forEach(assertFrameControl);
   for(const part of [left,right,...top.querySelectorAll('.tv-border-corner'),...bottom.children]){
    if(['grid','inline-grid','flex','inline-flex'].includes(getComputedStyle(part).display))throw Error('Frame drawing part still uses CSS grid/flex');
   }
   if(caption&&!caption.hidden){const r=caption.getBoundingClientRect(),column=(r.left-rect.left)/cell.width;
    if(Math.abs(column-Math.round(column))>0.01)throw Error('Window caption is between character columns');
    if(Math.abs((r.left-rect.left)-(rect.right-r.right))>cell.width+1)throw Error('Window caption is not centered');
   }
  };
  assertWindowFrame(view);
  if(manager.hostWindow)assertWindowFrame(manager.hostWindow._tvView);
  const assertBounds=(child,owner)=>{const r=child.root.getBoundingClientRect(),p=owner.root.getBoundingClientRect();
   if(Math.abs(r.left-p.left-child.bounds.x1*cell.width)>1||Math.abs(r.top-p.top-child.bounds.y1*cell.height)>1
    ||Math.abs(r.width-child.size.x*cell.width)>1||Math.abs(r.height-child.size.y*cell.height)>1)throw Error('Group geometry differs from TVRect');};
  assertBounds(nested,panel);assertBounds(nested.children[0],nested);assertBounds(button,panel);
  root.focus();const beforeMove=root.getBoundingClientRect();panel.moveTo(2,2);const afterMove=root.getBoundingClientRect();
  if(button.root!==root||document.activeElement!==root||Math.abs(afterMove.left-beforeMove.left-cell.width)>1
   ||Math.abs(afterMove.top-beforeMove.top-cell.height)>1)throw Error('Moving group replaced/focused controls or changed local coordinates');
  panel.moveTo(1,1);assertBounds(button,panel);
  const initialButton=button.getBounds(),initialTitle=button.title;
  button.setTitle('~G~o');button.focus();button.drawState(true);
  const face=root.querySelector('.tv-dialog-button-face'),label=root.querySelector('.tv-dialog-button-label');
  const edge=root.querySelector('.tv-dialog-button-edge'),shadow=root.querySelector('.tv-dialog-button-shadow'),inset=root.querySelector('.tv-dialog-button-inset');
  const buttonPalette=TV.buildPaletteFromCurrentStyle(),shadowPalette=TV.cloneColorPalette(buttonPalette);
  TV.setColorPaletteAttribute(shadowPalette,46,0x1f);TV.applyColorPalette(shadowPalette);await new Promise(requestAnimationFrame);
  if([root,face].some(part=>['grid','inline-grid','flex','inline-flex'].includes(getComputedStyle(part).display))
   ||getComputedStyle(face,'::before').content!=='none')throw Error('Button still depends on CSS grid/pseudo-element geometry');
  for(const [width,height,left] of [[16,2,false],[17,3,false],[16,4,false],[16,5,true],[8,2,true],[8,1,false],[3,2,false],[2,2,false],[1,2,false]]){
   button.flags=left?TV.bfLeftJust:TV.bfNormal;
   button.locate(new TV.TVRect(initialButton.x1,initialButton.y1,initialButton.x1+width,initialButton.y1+height));
   const rect=root.getBoundingClientRect(),f=face.getBoundingClientRect(),s=shadow.getBoundingClientRect();
   if(Math.abs(rect.width-width*cell.width)>1||Math.abs(rect.height-height*cell.height)>1
    ||Math.abs(s.top-rect.top-(height-1)*cell.height)>1||Math.abs(s.height-cell.height)>1
    ||Math.abs(f.height-(height-1)*cell.height)>1||shadow.textContent!==(height>1?' '.repeat(Math.min(2,width))+'▀'.repeat(Math.max(0,width-2)):' '.repeat(width))
    ||edge.textContent!==(height>1?'▄'+'\\n█'.repeat(height-2):''))throw Error('Button bounds/shadows diverge from character cells');
   const margin=inset.getBoundingClientRect(),caption=label.getBoundingClientRect(),side=edge.getBoundingClientRect();
   if(Math.abs(f.left-rect.left-cell.width)>1||Math.abs(f.width-width*cell.width)>1
    ||Math.abs(margin.left-f.left)>1||Math.abs(margin.width-cell.width)>1||Math.abs(margin.height-f.height)>1
    ||Math.abs(caption.left-f.left-cell.width)>1||Math.abs(caption.width-Math.max(0,width-2)*cell.width)>1
    ||Math.abs(side.right-f.right)>1||Math.abs(side.width-cell.width)>1
    ||getComputedStyle(edge).visibility!=='hidden'||getComputedStyle(shadow).visibility!=='hidden'
    ||getComputedStyle(shadow).color!=='rgb(255, 255, 255)'||getComputedStyle(shadow).backgroundColor!=='rgb(0, 0, 170)')throw Error('Button part bounds, pressed drawing or palette differ from the model');
   if(height>1){const glyph=label.querySelector('.tv-hotkey').getBoundingClientRect();
    const expectedLeft=1+(left?1:Math.max(1,Math.trunc((width-4)/2)));
    const expectedTop=Math.max(0,Math.floor(height/2)-1);
    if(Math.abs(glyph.left-rect.left-(expectedLeft+1)*cell.width)>1||Math.abs(glyph.top-rect.top-expectedTop*cell.height)>1)
     throw Error('Button title is not aligned to DOS character cells');}
   if(button.root!==root||document.activeElement!==root||root.querySelector('.tv-dialog-button-label')!==label
    ||!root.classList.contains('is-pressed'))throw Error('Button redraw lost its root, label, focus or pressed state');
  }
  button.locate(new TV.TVRect(initialButton.x1,initialButton.y1,initialButton.x1+16,initialButton.y1+4));
  button.setTitle('~D~one');
  const changedGlyph=label.querySelector('.tv-hotkey').getBoundingClientRect(),changedRect=root.getBoundingClientRect();
  if(Math.abs(changedGlyph.left-changedRect.left-7*cell.width)>1||Math.abs(changedGlyph.top-changedRect.top-cell.height)>1)
   throw Error('Changing a tall button title did not recalculate its cell alignment');
  const unchangedGlyph=label.querySelector('.tv-hotkey'),unchangedEdge=edge.firstChild,unchangedShadow=shadow.firstChild;
  button.setTitle('~D~one');button.drawView();button.bindRoot(root);
  if(button.root!==root||label.querySelector('.tv-hotkey')!==unchangedGlyph||edge.firstChild!==unchangedEdge||shadow.firstChild!==unchangedShadow
   ||document.activeElement!==root)throw Error('Unchanged button redraw replaced glyphs, text or focus');
  TV.applyColorPalette(buttonPalette);await new Promise(requestAnimationFrame);
  button.setTitle('<b>~&~');
  if(label.querySelector('b')||label.querySelector('.tv-hotkey')?.textContent!=='&')throw Error('Button caption was not escaped inside its shared drawing');
  button.setTitle('~D~one');
  button.drawState(false);
  const assertButtonPressed=down=>{
   const r=root.getBoundingClientRect(),f=face.getBoundingClientRect();
   if(root.classList.contains('is-pressed')!==down||Math.abs(f.left-r.left-(down?cell.width:0))>1
    ||getComputedStyle(edge).visibility!==(down?'hidden':'visible')||getComputedStyle(shadow).visibility!==(down?'hidden':'visible'))
    throw Error('Native button press bypassed TVButton.drawState');
  };
  root.dispatchEvent(new MouseEvent('mousedown',{button:2,bubbles:true}));assertButtonPressed(false);
  root.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));assertButtonPressed(true);
  root.dispatchEvent(new MouseEvent('mouseleave'));assertButtonPressed(false);
  if(button._releasePress)throw Error('Leaving button retained its release listeners');
  for(const key of [' ','Enter']){
   root.dispatchEvent(new KeyboardEvent('keydown',{key,code:key===' '?'Space':'Enter',bubbles:true,cancelable:true}));assertButtonPressed(true);
   document.dispatchEvent(new KeyboardEvent('keyup',{key:'x',bubbles:true}));assertButtonPressed(true);
   document.dispatchEvent(new KeyboardEvent('keyup',{key,bubbles:true}));assertButtonPressed(false);
   if(button._releasePress)throw Error('Keyboard release retained button listeners');
  }
  root.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));window.dispatchEvent(new Event('blur'));assertButtonPressed(false);
  root.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));button.setState(TV.sfDisabled,true);assertButtonPressed(false);
  if(button._releasePress)throw Error('Disabling button retained its release listeners');
  button.setState(TV.sfDisabled,false);
  const reboundButton=new TV.TVButton(new TV.TVRect(1,1,13,3),'~O~wned','owned');
  const oldButton=TV.TVView._fromHTML(reboundButton.draw());program.desktopView.root.append(oldButton);reboundButton.bindRoot(oldButton);
  oldButton.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));reboundButton.bindRoot(null);
  if(oldButton._tvView||oldButton.classList.contains('is-pressed')||reboundButton._releasePress||Object.values(reboundButton._buttonElements).some(Boolean))
   throw Error('Detached button retains drawn state, DOM or release listeners');
  const newButton=TV.TVView._fromHTML(reboundButton.draw());program.desktopView.root.append(newButton);reboundButton.bindRoot(newButton);
  reboundButton.setValue('updated').setCommandData({expanded:true});reboundButton.drawView();
  if(newButton.getAttribute('data-tv-owned')!=='updated'||newButton.getAttribute('aria-expanded')!=='true')throw Error('Button redraw lost its updated command data');
  reboundButton.setCommandData({});reboundButton.drawView();
  if(newButton.hasAttribute('aria-expanded')||newButton.hasAttribute('data-tv-expanded'))throw Error('Button redraw retained obsolete command attributes');
  oldButton.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));
  if(newButton.classList.contains('is-pressed')||reboundButton._releasePress)throw Error('A stale button still controls its rebound view');
  newButton.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));reboundButton.destroy();
  if(newButton._tvView||reboundButton.root||reboundButton._releasePress)throw Error('Destroyed button retains its root or input listeners');
  oldButton.remove();newButton.remove();button.focus();
  button.drawState(false);button.makeDefault(true);
  if(!root.classList.contains('is-default'))throw Error('Default button lost its state');
  button.setState(TV.sfDisabled,true);
  if(!root.disabled||button.press())throw Error('Disabled button accepted a command');
  root.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true}));
  if(root.classList.contains('is-pressed'))throw Error('Disabled button animated on mouse input');
  const disabled=getComputedStyle(label).color;button.setState(TV.sfDisabled,false);
  if(root.disabled||getComputedStyle(label).color===disabled)throw Error('Button did not restore its enabled palette');
  const editedButtonPalette=TV.cloneColorPalette(buttonPalette),captionNode=label.querySelector('.tv-hotkey');
  const buttonRgb=hex=>'rgb('+hex.slice(1).match(/../g).map(value=>parseInt(value,16)).join(', ')+')';
  const assertButtonPaint=(part,attr)=>{
   const style=getComputedStyle(part);
   if(style.color!==buttonRgb(TV.DOS_COLORS[attr&15])||style.backgroundColor!==buttonRgb(TV.DOS_COLORS[(attr>>4)&15]))
    throw Error('Button did not paint its DOS palette attribute '+attr+': '+style.color+' / '+style.backgroundColor);
  };
  try{
   for(const [index,attr] of [[41,0x1e],[42,0x2b],[43,0x4f],[44,0x58],[45,0x6a],[46,0x70]])TV.setColorPaletteAttribute(editedButtonPalette,index,attr);
   TV.applyColorPalette(editedButtonPalette);await new Promise(requestAnimationFrame);
   button.makeDefault(false);root.blur();assertButtonPaint(face,0x1e);assertButtonPaint(captionNode,0x1a);
   button.makeDefault(true);assertButtonPaint(face,0x2b);assertButtonPaint(captionNode,0x2a);
   root.focus();assertButtonPaint(face,0x4f);assertButtonPaint(captionNode,0x4a);
   button.setState(TV.sfDisabled,true);assertButtonPaint(face,0x58);assertButtonPaint(captionNode,0x58);
   for(const part of [inset,edge,shadow])assertButtonPaint(part,0x70);
   button.setState(TV.sfDisabled,false);button.makeDefault(false);root.blur();
   button.drawState(true);assertButtonPaint(face,0x4f);button.drawState(false);assertButtonPaint(face,0x1e);
   root.dispatchEvent(new MouseEvent('mouseenter'));assertButtonPaint(face,0x1e);
   if(getComputedStyle(root).backgroundColor!=='rgba(0, 0, 0, 0)')throw Error('Button hover filled its transparent shadow cells');
   root.dispatchEvent(new MouseEvent('mouseleave'));root.focus();
   TV.setColorPaletteAttribute(editedButtonPalette,43,0x3e);TV.applyColorPalette(editedButtonPalette);await new Promise(requestAnimationFrame);
   assertButtonPaint(face,0x3e);assertButtonPaint(captionNode,0x3a);
   if(button.root!==root||label.querySelector('.tv-hotkey')!==captionNode||document.activeElement!==root)
    throw Error('Button palette/state changes replaced controls, caption glyphs or native focus');
  }finally{button.setState(TV.sfDisabled,false);button.drawState(false);TV.applyColorPalette(buttonPalette);await new Promise(requestAnimationFrame);}
  button.makeDefault(false);button.flags=TV.bfNormal;button.setTitle(initialTitle);button.locate(initialButton);
  const initial=view.getBounds(),input=view.input,inputRoot=input.root;
  input.setData('unfinished input');input.focus();inputRoot.setSelectionRange(3,8);
  button.drawState(true);
  view.growTo(initial.width+8,initial.height+4);
  assertBounds(panel,view.root.matches('.tv-dialog-overlay')?{root:view.dialog.querySelector('.tv-dialog-client')}: {root:view.root.querySelector('.tv-viewport')});
  assertBounds(input,panel);assertBounds(button,panel);assertBounds(nested,panel);assertBounds(nested.children[0],nested);
  if(panel.size.x!==53||panel.size.y!==13||button.bounds.x1!==9||nested.bounds.y1!==10||nested.size.x!==48
   ||input.getData()!=='unfinished input'||inputRoot!==input.root||document.activeElement!==inputRoot
   ||inputRoot.selectionStart!==3||inputRoot.selectionEnd!==8||button.root!==root||!root.classList.contains('is-pressed'))throw Error('Owner growth lost bounds, mounted controls or input state');
  view.locate(initial);button.drawState(false);
  if(button.bounds.x1!==1||nested.bounds.y1!==6||nested.size.x!==40||input.size.x!==22)throw Error('Shrinking owner did not restore anchored controls');
  const resizer=view.root._tvResizer;
  if(!resizer)throw Error('Module window has no resize adapter');
  const geometry=resizer.captureGeometry();
  {
   const normal=view.getBounds(),minimum=view.minSize.copy(),font=document.documentElement.style.getPropertyValue('--tv-cell-size');
   const width=program.root.style.width,height=program.root.style.height;
   const viewport=view.root.querySelector('.tv-viewport'),frame=view.root.firstElementChild;
   try{
    document.documentElement.style.setProperty('--tv-cell-size','14px');window.dispatchEvent(new Event('resize'));
    resizer.place({left:113,top:71,cols:54,rows:20});
    const cell=TV.measureCells(),area=program.desktopView.root.getBoundingClientRect(),rect=view.root.getBoundingClientRect();
    if(Math.abs(rect.left-area.left-113)>1||Math.abs(rect.top-area.top-71)>1||Math.abs(rect.width-54*cell.width)>1||Math.abs(rect.height-20*cell.height)>1)throw Error('Model window bounds did not reach the browser surface');
    if(program.docWindows){program.docWindows.set('__probe__.md',view.root);
    const captured=program._captureUrlState().w.find(item=>item.t==='doc'&&item.f==='__probe__.md').g;program.docWindows.delete('__probe__.md');
    if(captured.join()!==[113,71,54,20,0].join())throw Error('Workspace captured stale CSS window geometry');}
    const logical=view.getBounds();program.root.style.width='200px';program.root.style.height='110px';window.dispatchEvent(new Event('resize'));
    if(view.root.clientWidth>program.desktopView.root.clientWidth||view.root.clientHeight>program.desktopView.root.clientHeight||!view.bounds.equals(logical))throw Error('Small screen changed normal bounds or failed to clip the window');
    resizer.maximize(false);assertWindowFrame(view);
    const full=view.root.getBoundingClientRect(),desktop=program.desktopView.root.getBoundingClientRect();
    for(const edge of ['left','right','top','bottom'])if(Math.abs(full[edge]-desktop[edge])>1)throw Error('Zoom failed to fill a fractional desktop extent');
    program.root.style.width=width;program.root.style.height=height;window.dispatchEvent(new Event('resize'));resizer.restore(false);
    if(resizer.captureGeometry().cols!==54||resizer.captureGeometry().rows!==20)throw Error('Zoom discarded normal dimensions');
    view.minSize=new TV.TVPoint(24,9);resizer.place({left:0,top:0,cols:1,rows:1});
    if(view.size.x!==24||view.size.y!==9)throw Error('Resize ignored TVWindow.SizeLimits');
    if([...view.root.style].some(name=>/^--tv-window-(cols|rows|left|top|min-cols|min-rows)$/.test(name)))throw Error('Window geometry still has a CSS-variable copy');
    if(view.root.querySelector('.tv-viewport')!==viewport||view.root.firstElementChild!==frame||document.activeElement!==input.root||input.getData()!=='unfinished input')throw Error('Window geometry replaced the client, frame or focused input');
   }finally{
    view.minSize=minimum;program.root.style.width=width;program.root.style.height=height;document.documentElement.style.setProperty('--tv-cell-size',font);window.dispatchEvent(new Event('resize'));view.locate(normal);resizer.place(geometry);input.focus();
   }
  }
  resizer.place({...geometry,cols:initial.width+6,rows:initial.height+2});
  assertWindowFrame(view);
  if(view.size.x!==initial.width+6||panel.size.x!==51||nested.bounds.y1!==8)throw Error('Browser resize adapter bypassed owner growth');
  resizer.maximize(false);
  assertWindowFrame(view);
  if(view.size.x!==Math.floor(view.root.clientWidth/cell.width)||panel.size.x!==view.size.x-3)throw Error('Zoom bypassed owner growth');
  const screenRoot=program.root,screenWidth=screenRoot.style.width;
  screenRoot.style.width=(screenRoot.clientWidth-6*cell.width)+'px';window.dispatchEvent(new Event('resize'));
  assertWindowFrame(view);
  if(view.size.x!==Math.floor(view.root.clientWidth/cell.width)||panel.size.x!==view.size.x-3)throw Error('Maximized module ignored a desktop resize');
  screenRoot.style.width=screenWidth;window.dispatchEvent(new Event('resize'));
  resizer.restore(false);resizer.place(geometry);input.focus();
  assertWindowFrame(view);
  const windowTitle=view.title;
  const windowCaption=view.root.querySelector('.tv-window-caption'),windowCaptionText=windowCaption.firstElementChild;
  for(const title of ['Long centered window caption '.repeat(4),'',windowTitle]){
   view.title=title;view.frame.drawTitle();assertWindowFrame(view);
   if(windowCaption.textContent!==title||windowCaption.firstElementChild!==windowCaptionText||input.root!==inputRoot||document.activeElement!==inputRoot)
    throw Error('Window caption redraw replaced controls or focus');
   const node=windowCaptionText.firstChild;view.frame.drawTitle();
   if(windowCaptionText.firstChild!==node)throw Error('Unchanged frame caption replaced its text node');
  }
  manager.open('calc');assertWindowFrame(view);
  const inactiveZoom=view.root.querySelector('[data-tv-zoom-glyph]'),zoomText=inactiveZoom.textContent;
  resizer.maximize(false);assertWindowFrame(view);resizer.restore(false);assertWindowFrame(view);
  manager.close('calc');assertWindowFrame(view);
  if(inactiveZoom.textContent!==zoomText||!view.root.querySelector('.tv-frame-passive').hidden)throw Error('Reactivating a window lost its real zoom glyph');
  input.focus();
  view.frame.setState(TV.sfActive,false);view.frame.drawView();assertWindowFrame(view);
  if(view.root._tvView!==view||view.frame.root!==view.root||input.root!==inputRoot)throw Error('TVFrame redraw lost its window owner');
  const syntaxProbe=document.createElement('div'),syntaxTheme=TV.getActiveThemePreset(),syntaxPalette=TV.cloneColorPalette(TV.getActiveColorPalette());
  const tokenKinds=['keyword','string','comment','number','preproc','asm'];
  const syntaxColors={c:['255, 255, 255','85, 255, 255','170, 170, 170','85, 255, 255','85, 255, 85','85, 255, 85'],
   pascal:['255, 255, 255','85, 255, 255','85, 255, 85','255, 85, 255','255, 255, 255','85, 255, 255'],
   asm:['255, 255, 255','85, 255, 255','85, 255, 85','85, 255, 255','85, 255, 85','85, 255, 255']};
  program.desktopView.root.append(syntaxProbe);
  try{
   for(const language of Object.keys(syntaxColors)){
    const example=document.createElement('pre');example.className='code-example code-lang-'+language;
    for(const kind of tokenKinds){const token=document.createElement('span');token.className='code-'+kind;token.textContent=kind;example.append(token);}
    syntaxProbe.append(example);
   }
   for(const theme of ['default','dark']){
    TV.applyThemeAndSyncPalette(theme);await new Promise(requestAnimationFrame);
    [...syntaxProbe.children].forEach((example,index)=>{
     const language=Object.keys(syntaxColors)[index],style=getComputedStyle(example);
     if(style.backgroundColor!=='rgb(0, 0, 170)'||style.color!=='rgb(255, 255, 85)'||style.whiteSpace!=='pre'
      ||parseFloat(style.lineHeight)!==parseFloat(style.fontSize))throw Error('Code example lost its DOS surface, spacing or row height');
     [...example.children].forEach((token,index)=>{if(getComputedStyle(token).color!=='rgb('+syntaxColors[language][index]+')')
      throw Error('Code palette changed for '+language+' '+tokenKinds[index]+' in '+theme);});
    });
   }
  }finally{syntaxProbe.remove();TV.applyThemePreset(syntaxTheme);TV.applyColorPalette(syntaxPalette);await new Promise(requestAnimationFrame);}
  for(const growable of [true,false]){
   const source=new TV.TVWindow(new TV.TVRect(0,0,36,12),'Source palette');
   source.hasScrollBars=()=>false;
   if(!growable)source.flags &= ~TV.wfGrow;
   const holder=document.createElement('div');holder.innerHTML=source.draw();
   const node=holder.firstElementChild;
   for(const key of [...node.style])if(key.startsWith('--tv-owner-'))node.style.removeProperty(key);
   node.style.setProperty('--tv-owner-content-bg','#112233');
   node.style.setProperty('--tv-owner-content-fg','#fedcba');
   node.style.setProperty('--tv-owner-frame-active-fg','#ff5555');
   node.style.setProperty('--tv-owner-frame-passive-fg','#5555ff');
   node.style.setProperty('--tv-owner-icon-active-fg','#55ff55');
   program.desktopView.root.append(node);
   try{
    source.bindRoot(node);
    if(getComputedStyle(node).backgroundColor!=='rgb(17, 34, 51)'||getComputedStyle(node).color!=='rgb(254, 220, 186)'
     ||!node.style.getPropertyValue('--tv-owner-frame-active-fg'))throw Error('Binding an exported window lost its source palette or default frame');
    const states=['is-window-inactive','is-moving','is-resizing'];
    for(const [state,color] of [['','rgb(255, 85, 85)'],['is-window-inactive','rgb(85, 85, 255)'],['is-moving','rgb(85, 255, 85)'],['is-resizing','rgb(85, 255, 85)']]){
     node.classList.remove(...states);if(state)node.classList.add(state);
     const parts=node.querySelectorAll('.tv-border-top,.tv-border-corner,.tv-border-fill,.tv-border-side,.tv-scroll-corner');
     if([...parts].some(part=>getComputedStyle(part).color!==color))throw Error('Source frame parts disagree in '+state+' / '+growable);
     const surfaces=node.querySelectorAll('.tv-border-top,.tv-frame,.tv-client-row,.tv-scroll-shell,.tv-bottom-bar,.tv-viewport,.tv-scroll-corner');
     if([...surfaces].some(part=>paintedBackground(part)!=='rgb(17, 34, 51)'))throw Error('Source window surfaces lost their owning background in '+state);
     const grow=node.querySelector('.tv-grow-handle');
     if(grow&&getComputedStyle(grow).color!==(state==='is-window-inactive'?color:'rgb(85, 255, 85)'))throw Error('Grow handle lost active/passive frame paint');
    }
    if(program._activeFindTarget){
     const name='help:source-palette-test',active=manager.activeTarget,viewport=node.querySelector('[data-tv-viewport]');
     const before=[getComputedStyle(viewport).color,getComputedStyle(viewport).backgroundColor];
     node._tvWindowView=source;manager.windows.set(name,node);manager.activeTarget=name;
     try{
      const target=program._activeFindTarget();
      if(target?.editor!==source.findEditor||target.editor.getPalette()!==null
       ||getComputedStyle(viewport).color!==before[0]||getComputedStyle(viewport).backgroundColor!==before[1])throw Error('Find adapter changed the source HELP palette');
     }finally{source.findEditor?.destroy();manager.windows.delete(name);manager.activeTarget=active;}
    }
   }finally{source.bindRoot(null);node.remove();}
  }
  if(program.windowManager){
   const wm=program.windowManager;
   const ui={window:'#123456',text:'#abcdef',link:'#ffff55',title:'#112233',title_passive:'#223344',title_text:'#ffffff',title_text_passive:'#abcdef',
    frame:'#fedcba',frame_passive:'#555555',icon:'#ff5555',icon_passive:'#55ffff',page_area:'#654321',arrow_bg:'#0000aa',arrow_fg:'#ffff55',
    scroll_glyph:'#0f0f0f',thumb_bg:'#aa0000',thumb_fg:'#55ff55',hover_bg:'#aa0000',hover_fg:'#ffffff'};
   const word='W'.repeat(220),flow={uhf_version:'2.0',_catalogFile:'css-layout-flow.json.gz',metadata:{name:'Flow layout',ui},
    topics:{'1':{id:'1',title:'Wrapping',tags:[{key:'subject',label:'Subject',value:'Layout'}],content:[word,'[rule]','End','[b]Bold[/b] [i]Italic[/i] [u]Underlined[/u]']}},contents:[{label:'One topic',topic_id:'1'}],index:[]};
   const fixed={...flow,_catalogFile:'css-layout-fixed.json.gz',metadata:{name:'Fixed layout',display:{cols:80,rows:20}}};
   const lineRects=element=>{const range=document.createRange();range.selectNodeContents(element);return [...range.getClientRects()];};
   try{
    wm.showTopic(flow,'1');const flowRoot=wm.openWindows.get(flow._catalogFile),viewport=flowRoot.querySelector('[data-tv-viewport]');
    const rgb=value=>'rgb('+value.slice(1).match(/../g).map(value=>parseInt(value,16)).join(', ')+')';
    const paint=(element,fg,bg)=>{const style=getComputedStyle(element);
     if(style.color!==rgb(fg)||paintedBackground(element)!==rgb(bg))throw Error('Source UI role lost its colors: '+element.className+' '+style.color+'/'+paintedBackground(element));};
    const caption=flowRoot.querySelector('.tv-window-caption');
    const checkSourcePalette=()=>{
     paint(viewport,ui.text,ui.window);paint(caption,ui.title_text,ui.title);
     if(flowRoot.querySelector('.tv-topic-tag')&&getComputedStyle(flowRoot.querySelector('.tv-topic-tag')).color!==rgb(ui.text))throw Error('Topic tags lost their inherited source foreground');
     paint(flowRoot.querySelector('.tv-scrollbar-y'),ui.scroll_glyph,ui.page_area);
     paint(flowRoot.querySelector('.tv-scroll-arrow'),ui.arrow_fg,ui.arrow_bg);
     paint(flowRoot.querySelector('.tv-scroll-thumb'),ui.thumb_fg,ui.thumb_bg);
     if(getComputedStyle(flowRoot.querySelector('.tv-border-corner')).color!==rgb(ui.frame)
      ||getComputedStyle(flowRoot.querySelector('.tv-close-glyph')).color!==rgb(ui.icon))throw Error('Source frame/icons were replaced by another palette role');
    };checkSourcePalette();
    const child=new TV.TVWindow(new TV.TVRect(1,1,28,12),'Nested palette'),holder=document.createElement('div');
    holder.innerHTML=child.draw();const childRoot=holder.firstElementChild;viewport.append(childRoot);
    try{
     child.bindRoot(childRoot);
     const checkChild=()=>{
      const style=getComputedStyle(childRoot),value=name=>style.getPropertyValue(name).trim();
      if(getComputedStyle(childRoot.querySelector('.tv-window-caption')).backgroundColor!==rgb(value('--tv-owner-frame-active-bg'))
       ||getComputedStyle(childRoot.querySelector('.tv-window-caption')).color!==rgb(value('--tv-owner-frame-active-fg'))
       ||getComputedStyle(childRoot.querySelector('.tv-close-glyph')).color!==rgb(value('--tv-owner-frame-icons-fg'))
       ||getComputedStyle(childRoot.querySelector('.tv-scrollbar-y')).backgroundColor!==rgb(value('--tv-owner-scroll-page-bg'))
       ||getComputedStyle(childRoot.querySelector('.tv-scroll-thumb')).color!==rgb(value('--tv-owner-scroll-controls-fg')))
       throw Error('Nested window inherited the outer source title/icon/scrollbar overrides');
     };checkChild();
    }finally{child.bindRoot(null);childRoot.remove();}
    const theme=TV.getActiveThemePreset(),palette=TV.cloneColorPalette(TV.getActiveColorPalette());
    try{for(const name of Object.keys(TV.THEME_PRESETS)){
     TV.applyThemeAndSyncPalette(name);await new Promise(requestAnimationFrame);checkSourcePalette();
    }}finally{TV.applyThemePreset(theme);TV.applyColorPalette(palette);await new Promise(requestAnimationFrame);}
    const text=flowRoot.querySelector('[data-tv-line="1"]'),pre=flowRoot.querySelector('.tv-topic-pre'),rule=flowRoot.querySelector('.tv-topic-line-rule');
    const bold=pre.querySelector('b'),italic=pre.querySelector('i'),underlined=pre.querySelector('u'),boldRange=document.createRange();
    boldRange.selectNodeContents(bold);
    if(getComputedStyle(bold).fontWeight!=='700'||getComputedStyle(italic).fontStyle!=='italic'
     ||!getComputedStyle(underlined).textDecorationLine.includes('underline')||Math.abs(boldRange.getBoundingClientRect().width-4*cell.width)>1)
     throw Error('Source formatting lost bold/italic/underline or changed VGA character widths');
    if(!text||text.textContent!==word||lineRects(text).length<2||pre.scrollWidth>pre.clientWidth+1
     ||pre.getBoundingClientRect().width>viewport.clientWidth+1)throw Error('Flowing HELP stopped wrapping long words inside its viewport');
    if(!rule||Math.abs(rule.getBoundingClientRect().height-cell.height)>1)throw Error('HELP rule wrapped into extra rows');
    wm.showTopic(fixed,'1');const fixedRoot=wm.openWindows.get(fixed._catalogFile),fixedPre=fixedRoot.querySelector('.tv-topic-pre');
    paint(caption,ui.title_text_passive,ui.title_passive);
    if(getComputedStyle(flowRoot.querySelector('.tv-border-corner')).color!==rgb(ui.frame_passive)
     ||getComputedStyle(flowRoot.querySelector('.tv-close-glyph')).color!==rgb(ui.icon_passive))throw Error('Passive source frame roles were conflated');
    const fixedText=fixedRoot.querySelector('[data-tv-line="1"]'),fixedViewport=fixedRoot.querySelector('[data-tv-viewport]');
    if(fixedText.textContent!==word||lineRects(fixedText).length!==1||fixedViewport.scrollWidth<=fixedViewport.clientWidth
     ||fixedPre.clientWidth<word.length*cell.width)throw Error('Fixed HELP lost its exact line or horizontal scrolling');
    for(const [bundle,root,area,fixedLayout] of [[flow,flowRoot,viewport,false],[fixed,fixedRoot,fixedViewport,true]]){
     bundle.topics['1'].frozen_rows=1;wm.showTopic(bundle,'1');
     const shell=root.querySelector('.tv-topic-shell'),frozen=root.querySelector('.tv-topic-pre-frozen');
     if(fixedLayout?(shell.getBoundingClientRect().width<=area.clientWidth||lineRects(frozen.querySelector('[data-tv-line="1"]')).length!==1)
      :(shell.getBoundingClientRect().width>area.clientWidth+1||lineRects(frozen.querySelector('[data-tv-line="1"]')).length<2))
      throw Error('Frozen HELP rows lost their source-specific wrapping and horizontal extent');
     if(paintedBackground(frozen)!==paintedBackground(area))throw Error('Frozen HELP header lost its opaque file background');
     delete bundle.topics['1'].frozen_rows;
    }
    flow.index=[{group:'A',entries:Array.from({length:100},(_,index)=>({label:'Alpha '+index,topic_id:'1'}))}];
    wm.showIndex(flow);viewport.scrollTop=12*cell.height;
    const frozen=flowRoot.querySelector('.tv-index-frozen');
    if(getComputedStyle(frozen).backgroundColor!==rgb(ui.window)
     ||Math.abs(frozen.getBoundingClientRect().top-viewport.getBoundingClientRect().top)>1)
     throw Error('Frozen index header no longer covers scrolling content with its file background');
    wm.showContents(flow);let outline=flowRoot._tvWindowView.outline;
    if(!outline||!outline.root.parentElement.classList.contains('tv-contents-document')
     ||Math.abs(outline.root.getBoundingClientRect().height-6*cell.height)>1)throw Error('Short HELP Contents lost its natural minimum height');
    flow.contents=Array.from({length:100},(_,index)=>({label:'Topic '+index,topic_id:'1'}));wm.showContents(flow);
    outline=flowRoot._tvWindowView.outline;
    checkSourcePalette();const row=outline.itemsRoot().children[1];
    if(paintedBackground(row)!==rgb(ui.window)||getComputedStyle(row).color!==rgb(ui.text))throw Error('Contents rows lost their owning file colors');
    if(Math.abs(outline.root.getBoundingClientRect().height-100*cell.height)>1||outline.root.querySelector('.tv-scrollbar')
     ||flowRoot.querySelectorAll('.tv-scrollbar').length!==2)throw Error('Long HELP Contents lost natural rows or created an inner scrollbar');
    outline.focusItem(90);outline.focusSelectedItem();
    paint(outline.selectedElement(),ui.hover_fg,ui.hover_bg);
    if(viewport.scrollTop<=0||!outline.selectedElement().textContent.includes('Topic 90'))throw Error('HELP Contents stopped scrolling its outer window to the selection');
    const input=outline.selectedElement();flowRoot._tvWindowView.minSize=new TV.TVPoint(24,8);
    flowRoot._tvResizer.place({left:0,top:0,cols:56,rows:14});
    if(outline.selectedElement()!==input||document.activeElement!==input||Math.abs(outline.root.getBoundingClientRect().height-100*cell.height)>1)throw Error('Resizing HELP Contents replaced selection or changed natural row height');
   }finally{wm.close(flow._catalogFile);wm.close(fixed._catalogFile);host.activate('app:both');input.focus();}
  }
  if(program._openDocWindow){
   const fence=String.fromCharCode(96).repeat(3),codeLine='  MOV AX, 1234    ; preserve spaces';
   const markdown=['# Document','','wide code '.repeat(20),'','| Name | Details |','| --- | --- |',
    '| C++ 3.0 | '+('First second '.repeat(16))+' |','',fence,codeLine,codeLine,fence].join(String.fromCharCode(10));
   const docRoot=program._openDocWindow('Frame.md',markdown);
   const doc=docRoot._tvWindowView;assertWindowFrame(doc);
   const assertDocText=()=>{
    const table=docRoot.querySelector('table'),code=docRoot.querySelector('pre');
    if(!table||!code||getComputedStyle(table).borderCollapse!=='collapse'||getComputedStyle(table).tableLayout!=='auto'||getComputedStyle(code).whiteSpace!=='pre'
     ||code.textContent!==[codeLine,codeLine].join(String.fromCharCode(10)))throw Error('Document lost its table, code rows or exact code spacing');
    for(const heading of docRoot.querySelectorAll('h1,h2,h3,h4,th')){
     const style=getComputedStyle(heading);
     if(style.color!=='rgb(255, 255, 255)'||style.fontWeight!=='700')throw Error('Document headings lost their shared white/bold paint');
    }
    for(const part of [table,...table.querySelectorAll('th,td')]){
     const style=getComputedStyle(part);
     if(style.whiteSpace!=='normal'||style.wordBreak!=='normal'||style.overflowWrap!=='normal'
      ||style.borderTopWidth!=='1px'||style.borderTopColor!=='rgb(255, 255, 85)'
      ||parseFloat(style.lineHeight)!==parseFloat(style.fontSize))throw Error('Document table lost inherited wrapping, yellow borders or row height');
    }
   };assertDocText();
   const assertDocPalette=()=>{
    const inactive=docRoot.classList.contains('is-window-inactive'),corner=docRoot.querySelector('.tv-border-corner');
    if(getComputedStyle(docRoot).backgroundColor!=='rgb(0, 0, 170)'||getComputedStyle(docRoot.querySelector('.tv-doc-document')).color!=='rgb(255, 255, 85)'
     ||getComputedStyle(corner).color!==(inactive?'rgb(170, 170, 170)':'rgb(255, 255, 255)'))throw Error('Document lost fixed editor colors or its shared active/passive frame palette');
   };assertDocPalette();
   const editorProperty='--tv-palette-viewer-text-bg',editorPrevious=document.documentElement.style.getPropertyValue(editorProperty);
   try{
    document.documentElement.style.setProperty(editorProperty,'#aa0000');await new Promise(requestAnimationFrame);assertDocPalette();
   }finally{document.documentElement.style.setProperty(editorProperty,editorPrevious);await new Promise(requestAnimationFrame);}
   for(const [cols,rows] of [[44,12],[96,30]]){docRoot._tvResizer.place({left:0,top:0,cols,rows});assertWindowFrame(doc);assertDocText();}
   const indicatorView=doc.editor.indicator,indicatorRoot=indicatorView.root,indicator=indicatorRoot.getBoundingClientRect();
   expectDOSPaint(indicatorRoot,0x1e);
   if(Math.abs(indicator.width-10*cell.width)>1||docRoot.querySelector('.tv-editor-indicator').textContent!=='RO  1:1')throw Error('Document indicator lost its character bounds');
   host.activate('app:both');assertWindowFrame(doc);assertDocPalette();doc.closeAction();
   if(doc.root||indicatorView.owner!==doc||indicatorView.root||indicatorRoot._tvView)throw Error('Closing document retained its owned indicator/palette binding');
   for(let cycle=0;cycle<2;cycle++){
    const again=program._openDocWindow('Frame.md',markdown),view=again._tvWindowView,indicator=view.editor.indicator,root=indicator.root;
    expectDOSPaint(root,0x1e);view.closeAction();
    if(again.isConnected||view.root||indicator.root||root._tvView)throw Error('Repeated document close retained indicator bindings');
   }
   host.activate('app:both');input.focus();
  }
  if(view.size.x!==initial.width||button.bounds.x1!==1||document.activeElement!==inputRoot)throw Error('Restore lost original layout/focus');
  const handle=view.root.querySelector('[data-tv-resize-handle]'),handleRect=handle.getBoundingClientRect();
  const x=handleRect.left+2,y=handleRect.top+2;
  handle.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,clientX:x,clientY:y,bubbles:true,cancelable:true}));
  document.dispatchEvent(new MouseEvent('mousemove',{buttons:1,clientX:x+4*cell.width,clientY:y+2*cell.height,bubbles:true,cancelable:true}));
  document.dispatchEvent(new MouseEvent('mouseup',{button:0,buttons:0,clientX:x+4*cell.width,clientY:y+2*cell.height,bubbles:true,cancelable:true}));
  if(view.size.x!==initial.width+4||view.size.y!==initial.height+2||panel.size.x!==49||nested.bounds.y1!==8)throw Error('Mouse resize bypassed owner growth');
  resizer.place(geometry);input.focus();
  const textDialog=new TV.TVDialog(new TV.TVRect(0,0,52,16),'Shared text clipping');
  const textInput=new TV.TVInputLine(new TV.TVRect(22,2,47,3),50).setData('retain selection');
  const longLabel='~N~ame with a long description beyond its field';
  const textLabel=new TV.TVLabel(new TV.TVRect(2,2,18,3),longLabel,textInput);
  const boundedText=new TV.TVStaticText(new TV.TVRect(2,5,18,7),'First long line beyond its field\\nSecond long line\\nThird line');
  const flowingText=new TV.TVStaticText(new TV.TVRect(2,9,2,9),'Text prepared without a fixed extent');
  textDialog.insert(new TV.TVGroup(new TV.TVRect(0,0,50,14)).insertAll([textLabel,textInput,boundedText,flowingText]));
  manager.register('text-clip-probe',textDialog);manager.open('text-clip-probe');
  const checkTextClip=(text,bounded=true)=>{
   if(getComputedStyle(text.root).overflow!==(bounded?'hidden':'visible'))throw Error('Shared text clipping does not follow current bounds: '+text.constructor.name);
   if(bounded){const rect=text.root.getBoundingClientRect(),cell=TV.measureCells();
    if(Math.abs(rect.width-text.size.x*cell.width)>1||Math.abs(rect.height-text.size.y*cell.height)>1)throw Error('Text extent differs from its character bounds');}
  };
  checkTextClip(textLabel);checkTextClip(boundedText);checkTextClip(flowingText,false);
  textInput.focus();textInput.root.setSelectionRange(2,7);
  const boundedRoot=boundedText.root,boundedNode=boundedRoot.firstChild,labelRoot=textLabel.root,labelHotkey=labelRoot.querySelector('.tv-hotkey');
  const labelPalette=TV.cloneColorPalette(TV.getActiveColorPalette()),labelColors=TV.cloneColorPalette(labelPalette);
  TV.setColorPaletteAttribute(labelColors,38,0x2a);TV.setColorPaletteAttribute(labelColors,39,0x4f);TV.setColorPaletteAttribute(labelColors,40,0x3e);
  try{
   TV.applyColorPalette(labelColors);await new Promise(requestAnimationFrame);
   expectDOSPaint(labelRoot,0x4f);expectDOSPaint(labelHotkey,0x4e);
   if(!textLabel.light||document.activeElement!==textInput.root||textInput.root.selectionStart!==2||textInput.root.selectionEnd!==7)throw Error('Label palette edit lost its linked focus or input selection');
   textInput.root.blur();expectDOSPaint(labelRoot,0x2a);expectDOSPaint(labelHotkey,0x2e);
   if(textLabel.light)throw Error('Label retained linked focus after blur');
   textLabel.setText(longLabel);expectDOSPaint(labelHotkey,0x2e);
   if(labelRoot.querySelector('.tv-hotkey')!==labelHotkey)throw Error('Label palette redraw replaced its unchanged mnemonic');
   textInput.focus();textInput.root.setSelectionRange(2,7);expectDOSPaint(labelRoot,0x4f);
  }finally{TV.applyColorPalette(labelPalette);await new Promise(requestAnimationFrame);}
  const labelBounds=textLabel.getBounds(),textBounds=boundedText.getBounds(),flowBounds=flowingText.getBounds();
  for(const width of [3,24,16]){
   textLabel.growTo(width,1);boundedText.growTo(width,2);checkTextClip(textLabel);checkTextClip(boundedText);
   if(textLabel.root!==labelRoot||labelRoot.querySelector('.tv-hotkey')!==labelHotkey||boundedText.root!==boundedRoot
    ||boundedRoot.firstChild!==boundedNode||document.activeElement!==textInput.root||textInput.root.selectionStart!==2
    ||textInput.root.selectionEnd!==7||textLabel.getText()!==longLabel)throw Error('Text resize replaced content, mnemonic or focused input state');
  }
  boundedText.locate(new TV.TVRect(2,5,2,5));checkTextClip(boundedText,false);
  boundedText.locate(textBounds);checkTextClip(boundedText);
  flowingText.locate(new TV.TVRect(2,9,18,11));checkTextClip(flowingText);
  flowingText.locate(flowBounds);checkTextClip(flowingText,false);
  textLabel.locate(labelBounds);textInput.root.blur();
  textDialog.dialog.dispatchEvent(new KeyboardEvent('keydown',{key:'n',altKey:true,bubbles:true,cancelable:true}));
  if(document.activeElement!==textInput.root||labelRoot.htmlFor!==textInput.viewId)throw Error('Clipped label mnemonic lost its linked input');
  textInput.root.setSelectionRange(2,7);textLabel.hide();textLabel.growTo(6,1);textLabel.show();checkTextClip(textLabel);
  const textFont=document.body.style.getPropertyValue('--tv-cell-size');
  try{
   for(const size of [14,16]){
    document.body.style.setProperty('--tv-cell-size',size+'px');window.dispatchEvent(new Event('resize'));
    await new Promise(requestAnimationFrame);checkTextClip(textLabel);checkTextClip(boundedText);
    if(document.activeElement!==textInput.root||textInput.root.selectionStart!==2||textInput.root.selectionEnd!==7)throw Error('Text font change lost input focus/selection');
   }
  }finally{
   if(textFont)document.body.style.setProperty('--tv-cell-size',textFont);else document.body.style.removeProperty('--tv-cell-size');
   window.dispatchEvent(new Event('resize'));await new Promise(requestAnimationFrame);
  }
  textDialog.destroy();
  if(textLabel.root||textLabel._focusScope||textLabel.light)throw Error('Detached label retained its focus bridge/state');
  {
   const foreign=new TV.TVDialog(new TV.TVRect(2,2,42,10),'Other mnemonic scope');
   const foreignInput=new TV.TVInputLine(new TV.TVRect(2,3,30,4),30);
   foreign.insertAll([new TV.TVLabel(new TV.TVRect(2,2,20,3),'~Z~ Other window',foreignInput),foreignInput]);
   program.desktopView.insert(foreign);foreign.open(false);
   const scope=new TV.TVDialog(new TV.TVRect(3,3,52,16),'Mnemonic scope');
   const field=new TV.TVInputLine(new TV.TVRect(20,2,46,3),30),source=new TV.TVInputLine(new TV.TVRect(20,4,46,5),30);
   const hiddenLabel=new TV.TVLabel(new TV.TVRect(2,2,18,3),'~N~ Hidden',source);hiddenLabel.hide();
   const disabledLabel=new TV.TVLabel(new TV.TVRect(2,4,18,5),'~D~ Disabled',field);disabledLabel.setState(TV.sfDisabled,true);
   const panel=new TV.TVGroup(new TV.TVRect(1,6,48,10));
   const nested=new TV.TVButton(new TV.TVRect(1,1,18,3),'~S~ Hidden Save','nested-save',TV.bfDefault);panel.insert(nested);panel.hide();
   const save=new TV.TVButton(new TV.TVRect(2,11,20,13),'~S~ave','scope-save',TV.bfDefault);
   scope.insertAll([hiddenLabel,new TV.TVLabel(new TV.TVRect(2,2,18,3),'~N~ame',field),field,disabledLabel,source,panel,save]);
   const commands=[];scope.handleEvent=function(event){TV.TVDialog.prototype.handleEvent.call(this,event);
    if(event.what===TV.evCommand&&['scope-save','nested-save'].includes(event.command)){commands.push([event.command,event.infoPtr]);this.clearEvent(event);}};
   program.desktopView.insert(scope);scope.open();
   const alt=key=>{source.focus();const event=new KeyboardEvent('keydown',{key,code:'Key'+key.toUpperCase(),altKey:true,bubbles:true,cancelable:true});source.root.dispatchEvent(event);return event;};
   if(!alt('n').defaultPrevented||document.activeElement!==field.root)throw Error('Hidden label shadowed the visible label mnemonic');
   const key=alt('s');if(!key.defaultPrevented||commands.length!==1||commands[0][1]!==save)throw Error('Alt button shortcut did not reach the visible button exactly once');
   source.focus();source.root.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));
   if(commands.length!==2||commands[1][1]!==save)throw Error('Hidden group supplied the default Enter button');
   nested.root.click();if(nested.press()||commands.length!==2)throw Error('Hidden group accepted a button command');
   panel.show();panel.setState(TV.sfDisabled,true);save.setState(TV.sfDisabled,true);
   alt('s');if(commands.length!==2||nested.press())throw Error('Disabled controls supplied an Alt button shortcut');
   program.menuController?.menuView?.closeMenus({restoreFocus:false});
   panel.setState(TV.sfDisabled,false);alt('s');
   if(commands.length!==3||commands[2][1]!==nested)throw Error('Reenabled nested button mnemonic did not recover');
   source.focus();disabledLabel.root.click();if(document.activeElement!==source.root)throw Error('Disabled label used native input activation');
   alt('z');if(document.activeElement!==source.root||manager.activeTarget!==scope.managerName)throw Error('Unmatched mnemonic escaped into another window');
   save.setState(TV.sfDisabled,false);scope.destroy();foreign.destroy();
  }
  {
   const scope=new TV.TVDialog(new TV.TVRect(4,4,50,18),'Tab hierarchy');scope.flags&=~TV.wfClose;scope.setState(TV.sfModal,true);
   const first=new TV.TVInputLine(new TV.TVRect(2,2,35,3),40),readOnly=new TV.TVInputLine(new TV.TVRect(2,7,35,8),40);
   readOnly.setData('Read-only fields remain selectable');
   const disabled=new TV.TVGroup(new TV.TVRect(1,4,45,6)),active=new TV.TVGroup(new TV.TVRect(1,9,45,11));
   const hidden=new TV.TVGroup(new TV.TVRect(1,12,45,14));
   const unavailable=new TV.TVInputLine(new TV.TVRect(1,0,34,1),40),nested=new TV.TVInputLine(new TV.TVRect(1,0,34,1),40);
   disabled.insert(unavailable);active.insert(nested);hidden.insert(new TV.TVInputLine(new TV.TVRect(1,0,34,1),40));
   disabled.setState(TV.sfDisabled,true);hidden.hide();scope.insertAll([first,disabled,readOnly,active,hidden]);
   program.desktopView.insert(scope);scope.open();readOnly.root.readOnly=true;
   if(!scope.closeButton.hidden)throw Error('Frame activation ignored wfClose and restored the close control');
   for(const command of [TV.TV_COMMANDS.CLOSE,TV.TV_COMMANDS.CANCEL]){
    if(manager.canDispatchCommand(command)||manager.dispatchCommand(command)||!scope.isOpen())throw Error('Dialog close command ignored wfClose');
   }
   const checkOrder=expected=>{const actual=scope._focusViews().map(view=>view._focusTarget());
    if(actual.length!==expected.length||actual.some((element,index)=>element!==expected[index].root))throw Error('Tab cycle did not respect the current owned hierarchy: '+JSON.stringify({actual:actual.map(element=>element._tvView?.viewId||element.getAttribute('data-tv-command')),expected:expected.map(view=>view.viewId)}));};
   const tab=(source,shiftKey=false)=>{source?.focus();const target=source?.root||scope.dialog;
    const event=new KeyboardEvent('keydown',{key:'Tab',code:'Tab',shiftKey,bubbles:true,cancelable:true});target.dispatchEvent(event);
    if(!event.defaultPrevented)throw Error('Dialog left Tab to native browser navigation');return document.activeElement;};
   checkOrder([first,readOnly,nested]);
   if(tab(first)!==readOnly.root||tab(readOnly)!==nested.root||tab(nested)!==first.root||tab(first,true)!==nested.root)
    throw Error('Tab/Shift-Tab did not skip disabled groups or wrap nested controls');
   disabled.setState(TV.sfDisabled,false);checkOrder([first,unavailable,readOnly,nested]);
   if(tab(first)!==unavailable.root)throw Error('Tab did not restore a reenabled group');
   disabled.hide();active.hide();first.hide();readOnly.hide();checkOrder([]);
   scope.dialog.focus();
   if(tab()!==scope.dialog||tab(null,true)!==scope.dialog||manager.activeTarget!==scope.managerName)
    throw Error('Empty modal Tab escaped to a different window');
   first.show();checkOrder([first]);
   if(tab()!==first.root||tab(first,true)!==first.root)throw Error('Tab did not recover after controls became available');
   scope.destroy();
   const windowView=new TV.TVWindow(new TV.TVRect(2,2,35,12),'Window close flag');
   const root=TV.TVView._fromHTML(windowView.draw());windowView.resolve(root);windowView.flags&=~TV.wfClose;program.desktopView.insert(windowView);
   let closed=0;const close=()=>{closed++;windowView.hide();};windowView.closeAction=close;
   manager.registerWindow('frame-flag-probe',root,{[TV.TV_COMMANDS.CLOSE]:close});
   try{
    if(!windowView.closeControl.hidden||manager.canDispatchCommand(TV.TV_COMMANDS.CLOSE)||manager.dispatchCommand(TV.TV_COMMANDS.CLOSE))
     throw Error('Window frame or manager close command ignored wfClose');
    windowView.closeControl.click();windowView.dispatchEvent(new TV.TVEvent(TV.evCommand,{command:'window-close'}));
    if(closed||!windowView.exposed())throw Error('Hidden close control bypassed the window flag');
    windowView.flags|=TV.wfClose;manager.applyActiveStates();
    if(windowView.closeControl.hidden||!manager.canDispatchCommand(TV.TV_COMMANDS.CLOSE)||!manager.dispatchCommand(TV.TV_COMMANDS.CLOSE)
     ||closed!==1||windowView.exposed())throw Error('Reenabled window close did not recover its frame and command');
   }finally{manager.unregisterWindow('frame-flag-probe');windowView.owner?.remove(windowView);windowView.bindRoot(null);root.remove();}
  }
  host.activate('app:both');input.focus();
  {
   const scope=new TV.TVDialog(new TV.TVRect(2,2,74,29),'Owned control input');
   const group=new TV.TVGroup(new TV.TVRect(1,1,70,25)),list=new TV.TVListBox(new TV.TVRect(1,1,27,7));
   list.setItems(Array.from({length:50},(_,index)=>'Owned row '+index),0);let selected=0;list.bind({onSelect:()=>selected++,onActivate:()=>selected++});
   const checks=new TV.TVCheckBoxes(new TV.TVRect(30,1,54,4),[{label:'One'},{label:'Two'}]);
   const radios=new TV.TVRadioButtons(new TV.TVRect(30,5,54,8),[{label:'First'},{label:'Second'}]);
   const multi=new TV.TVMultiCheckBoxes(new TV.TVRect(30,9,57,12),[{label:'Mode',state:0}]);
   const locked=new TV.TVInputLine(new TV.TVRect(1,14,27,15),40);locked.setData('Retained disabled input');locked.setState(TV.sfDisabled,true);
   const concealed=new TV.TVInputLine(new TV.TVRect(1,16,27,17),40);concealed.setData('Retained hidden input');concealed.hide();
   const button=new TV.TVButton(new TV.TVRect(30,14,54,16),'Action','owned-state-action');let actions=0;
   const handle=scope.handleEvent.bind(scope);scope.handleEvent=event=>{handle(event);
    if(event.what===TV.evCommand&&event.command==='owned-state-action'){actions++;scope.clearEvent(event);}};
   group.insertAll([list,checks,radios,multi,locked,concealed,button]);scope.insert(group);program.desktopView.insert(scope);scope.open();
   const roots=group.children.map(view=>view.root);
   try{
    for(const flag of [TV.sfDisabled,TV.sfVisible])for(const mask of [flag,flag|TV.sfActive]){
     list.focusItem(0,{scroll:false});list.viewport.scrollTop=0;list.scrollbarWidget.update();
     const local=group.children.map(view=>view.state&(TV.sfVisible|TV.sfDisabled));group.setState(mask,flag===TV.sfDisabled);
     if(group.children.some((view,index)=>(view.state&(TV.sfVisible|TV.sfDisabled))!==local[index]))throw Error('Combined owner state overwrote local availability');
     const actionCount=actions;if(button.press()||actions!==actionCount)throw Error('Unavailable owner accepted an action');
     const count=selected,values=[checks,radios,multi].map(view=>view.getData()),states=multi.strings.map((_option,index)=>multi.multiMark(index)),row=list.selectedElement();
     for(const type of ['mousedown','click','dblclick'])row.dispatchEvent(new MouseEvent(type,{button:0,bubbles:true,cancelable:true}));
     row.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
     list.selectItem(1);const wheel=new WheelEvent('wheel',{deltaY:80,bubbles:true,cancelable:true});list.root.dispatchEvent(wheel);
     list.scrollbarWidget.axes.y.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
     document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
     if(list.selectedIndex!==0||selected!==count||!wheel.defaultPrevented||list.viewport.scrollTop!==0)throw Error('Unavailable owner allowed list selection or scrolling');
     for(const view of [checks,radios,multi]){
      const choice=view.choiceElements[0];choice.click();
      const key=new KeyboardEvent('keydown',{key:' ',code:'Space',bubbles:true,cancelable:true});choice.dispatchEvent(key);
      if(!key.defaultPrevented)throw Error('Unavailable owner allowed native choice activation');view.press(0);
     }
     checks.choiceElements[0].checked=true;checks.choiceElements[0].dispatchEvent(new Event('change',{bubbles:true}));
     if([checks,radios,multi].some((view,index)=>view.getData()!==values[index])||multi.strings.some((_option,index)=>multi.multiMark(index)!==states[index])
      ||checks.choiceElements[0].checked!==checks.mark(0))throw Error('Unavailable owner changed a choice value or native mark');
     list.focusItem(2,{scroll:false});checks.setData(1);radios.setData(1);multi.setData(1);
     if(list.selectedIndex!==2||checks.getData()!==1||radios.getData()!==1||multi.getData()!==1)throw Error('Unavailable owner blocked a model update');
     group.setState(mask,flag!==TV.sfDisabled);const before=selected;list.selectedElement().click();checks.choiceElements[0].click();
     if(selected!==before+1||checks.getData()!==0)throw Error('Reenabled owner did not restore input');
     if(!button.press()||actions!==actionCount+1||!locked.root.disabled||!concealed.root.hidden
      ||locked.getData()!=='Retained disabled input'||concealed.getData()!=='Retained hidden input'
      ||group.children.some((view,index)=>view.root!==roots[index]))throw Error('Combined owner state lost commands, local controls or their mounted buffers');
    }
   }finally{scope.destroy();}
  }
  host.activate('app:both');input.focus();
  const plain=new TV.TVInfoRow(new TV.TVRect(0,1,32,2),'A long status line that must keep its right border inside the panel');
  const marked=new TV.TVInfoRow(new TV.TVRect(0,2,32,3));marked.setHTML('<b>marked</b>',6);
  const field=new TV.TVInputLine(new TV.TVRect(1,3,31,4),40);field.growMode=TV.gfGrowHiX;
  const list=new TV.TVListBox(new TV.TVRect(1,4,31,7));list.growMode=TV.gfGrowHiX|TV.gfGrowHiY;
  list.hScrollBar=new TV.TVScrollBar(new TV.TVRect());
  list.setItems(Array.from({length:100},(_,index)=>'Row '+index+' — '+'wide text '.repeat(10)));
  const box=new TV.TVInfoBox(new TV.TVRect(0,0,32,8),'Framed views',[plain,marked,field,list]);
  const boxRoot=TV.TVView._fromHTML(box.draw());program.desktopView.root.append(boxRoot);box.resolve(boxRoot);
  if(!(box instanceof TV.TVGroup)||box.children.some(child=>child.owner!==box)||!marked.root.querySelector('b'))throw Error('Info box lost owned views or pre-mount markup');
  field.setData('draft text');field.focus();field.root.setSelectionRange(2,6);
  const fieldRoot=field.root,plainRoot=plain.root,markedRoot=marked.root,listRoot=list.root;
  for(const [width,height] of [[40,10],[12,8],[32,8]]){
   box.growTo(width,height);
   for(const child of box.children)assertBounds(child,box);
   if(box.topFrame.text.length!==width||box.bottomFrame.text.length!==width||box.bottomFrame.bounds.y1!==height-1
    ||plain.root.textContent.length!==width||plain.root.textContent.at(-1)!=='│'
    ||field.root!==fieldRoot||plain.root!==plainRoot||marked.root!==markedRoot||list.root!==listRoot
    ||!marked.root.querySelector('b')||document.activeElement!==fieldRoot||field.getData()!=='draft text'
    ||fieldRoot.selectionStart!==2||fieldRoot.selectionEnd!==6)throw Error('Info box resize lost a frame, content or focused child');
  }
  box.moveTo(60,1);box.growTo(40,14);list.updateScrollbar();
  const scrollbar=list.scrollbarWidget;
  const assertScrollbarLayout=controller=>{
   const cell=TV.measureCells(),near=(actual,expected)=>{if(Math.abs(actual-expected)>1)throw Error('Scrollbar part bounds differ: '+actual+' / '+expected);};
   for(const [name,axis] of Object.entries(controller.axes)){
    if(axis.root.hidden)continue;
    if([axis.root,axis.backward,axis.track,axis.forward].some(part=>['flex','grid'].includes(getComputedStyle(part).display)))
     throw Error('Scrollbar still relies on CSS flex/grid geometry');
    const vertical=name==='y',root=axis.root.getBoundingClientRect(),back=axis.backward.getBoundingClientRect(),track=axis.track.getBoundingClientRect(),forward=axis.forward.getBoundingClientRect();
    const length=vertical?root.height:root.width,unit=vertical?cell.height:cell.width,arrow=Math.min(unit,length/2);
    const start=vertical?'top':'left',end=vertical?'bottom':'right',cross=vertical?'left':'top',crossEnd=vertical?'right':'bottom';
    near(back[start],root[start]);near(back[end],track[start]);near(track[end],forward[start]);near(forward[end],root[end]);
    near(back[end]-back[start],arrow);near(forward[end]-forward[start],arrow);
    for(const part of [back,track,forward]){near(part[cross],root[cross]);near(part[crossEnd],root[crossEnd]);}
    const cells=axis.cells.getBoundingClientRect();near(cells.left,track.left);near(cells.top,track.top);near(cells.right,track.right);near(cells.bottom,track.bottom);
   }
  };
  const assertListLayout=control=>{
   const bounds=control.root.getBoundingClientRect(),client=control.viewport.getBoundingClientRect();
   const axes=(control.scrollbarWidget||control.scrollController).axes,horizontal=Boolean(axes.x&&!axes.x.root.hidden);
   const cols=Math.max(0,control.size.x-(axes.y?1:0)),rows=Math.max(0,control.size.y-(horizontal?1:0));
   if(getComputedStyle(control.root).display==='grid'||control.viewport.style.position!=='absolute'
    ||Math.abs(client.left-bounds.left)>1||Math.abs(client.top-bounds.top)>1
    ||Math.abs(client.width-cols*cell.width)>1||Math.abs(client.height-rows*cell.height)>1)throw Error('List client does not follow TVision cell bounds');
   if(axes.y){const r=axes.y.root.getBoundingClientRect();if(Math.abs(r.left-client.right)>1||Math.abs(r.right-bounds.right)>1
    ||Math.abs(r.top-bounds.top)>1||Math.abs(r.bottom-client.bottom)>1)throw Error('Vertical list scrollbar is not on the client edge');}
   if(horizontal){const r=axes.x.root.getBoundingClientRect();if(Math.abs(r.left-bounds.left)>1||Math.abs(r.right-client.right)>1
    ||Math.abs(r.top-client.bottom)>1||Math.abs(r.bottom-bounds.bottom)>1)throw Error('Horizontal list scrollbar is not on the client edge');}
   assertScrollbarLayout(control.scrollbarWidget||control.scrollController);
  };
  assertListLayout(list);
  const viewportRoot=list.viewport,verticalRoot=scrollbar.axes.y.root,horizontalRoot=scrollbar.axes.x.root;
  const effectiveBackground=element=>{
   for(let part=element;part;part=part.parentElement){const color=getComputedStyle(part).backgroundColor;if(color!=='rgba(0, 0, 0, 0)')return color;}
  };
  for(const [color,background] of [['#abcdef','#123456'],['#fedcba','#654321']]){
   verticalRoot.style.setProperty('--tv-scrollbar-glyph',color);verticalRoot.style.setProperty('--tv-scrollbar-bg',background);
   if(getComputedStyle(scrollbar.axes.y.cells).color!==getComputedStyle(verticalRoot).color
    ||effectiveBackground(scrollbar.axes.y.track)!==getComputedStyle(verticalRoot).backgroundColor
    ||effectiveBackground(scrollbar.axes.y.cells)!==getComputedStyle(verticalRoot).backgroundColor)throw Error('Scrollbar track lost its owning surface palette');
  }
  verticalRoot.style.removeProperty('--tv-scrollbar-glyph');verticalRoot.style.removeProperty('--tv-scrollbar-bg');
  verticalRoot.style.setProperty('--tv-scrollbar-arrow-fg','#123456');
  for(const [width,height] of [[48,18],[20,11],[40,14]]){
   box.growTo(width,height);assertListLayout(list);
   if(list.viewport!==viewportRoot||list.scrollbarWidget!==scrollbar||scrollbar.axes.y.root!==verticalRoot
    ||scrollbar.axes.x.root!==horizontalRoot||getComputedStyle(scrollbar.axes.y.forward).color!=='rgb(18, 52, 86)')throw Error('List resize rebuilt controls or erased palette properties');
  }
  verticalRoot.style.removeProperty('--tv-scrollbar-arrow-fg');
  for(const name of ['x','y']){
   const axis=scrollbar.axes[name],trackNode=axis.cells.firstChild,thumbNode=axis.thumb.firstChild;
   axis.thumb.style.color='#123456';
   for(const ratio of [0,0.25,0.5,1]){
    scrollbar.setScrollPosition(name,scrollbar.axisMetrics(name).maxScroll*ratio);
    const metrics=scrollbar.axisMetrics(name),t=axis.track.getBoundingClientRect(),r=axis.thumb.getBoundingClientRect();
    const offset=Math.round(metrics.freeTrackCells*metrics.scrollOffset/metrics.maxScroll)*metrics.cellSize;
    if(axis.cells.childElementCount||axis.thumb.childElementCount||axis.cells.firstChild!==trackNode||axis.thumb.firstChild!==thumbNode)
     throw Error('Scrolling rebuilt per-cell nodes instead of moving the existing thumb');
    if(axis.cells.textContent!==(name==='y'?Array(metrics.cellCount).fill('▒').join('\\n'):'▒'.repeat(metrics.cellCount))
     ||axis.thumb.textContent!=='■'||Math.abs(r.width-cell.width)>1||Math.abs(r.height-cell.height)>1
     ||Math.abs(r.left-t.left-(name==='x'?offset:0))>1||Math.abs(r.top-t.top-(name==='y'?offset:0))>1)
     throw Error('Scrollbar text/thumb geometry differs from the character-cell track');
    if(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)!==axis.thumb)throw Error('Scrollbar thumb has an invalid hit area');
    if(getComputedStyle(axis.thumb).color!=='rgb(18, 52, 86)')throw Error('Moving the thumb erased its palette');
   }
   axis.thumb.style.removeProperty('color');
   scrollbar.setScrollPosition(name,0);
   const axisTrack=axis.track.getBoundingClientRect();
   axis.track.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true,
    clientX:name==='x'?axisTrack.right-1:axisTrack.left+axisTrack.width/2,
    clientY:name==='y'?axisTrack.bottom-1:axisTrack.top+axisTrack.height/2}));
   document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
   if(scrollbar.axisMetrics(name).scrollOffset<=0)throw Error('Scrollbar track stopped responding');
   scrollbar.setScrollPosition(name,0);
   const thumb=axis.thumb.getBoundingClientRect(),x=thumb.left+thumb.width/2,y=thumb.top+thumb.height/2;
   axis.thumb.dispatchEvent(new MouseEvent('mousedown',{button:0,buttons:1,bubbles:true,cancelable:true,clientX:x,clientY:y}));
   document.dispatchEvent(new MouseEvent('mousemove',{buttons:1,bubbles:true,clientX:x+(name==='x'?2*cell.width:0),clientY:y+(name==='y'?2*cell.height:0)}));
   document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
   if(scrollbar.axisMetrics(name).scrollOffset<=0||scrollbar.dragState)throw Error('Scrollbar thumb stopped dragging/releasing');
   scrollbar.setScrollPosition(name,0);
   axis.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
   document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
   const step=name==='y'?cell.height:2*cell.width;
   if(scrollbar.axisMetrics(name).scrollOffset!==step||scrollbar.repeatTimer!==null)throw Error('Scrollbar arrow did not move exactly one step');
  }
  const listBounds=list.getBounds();
  for(const [width,height] of [[3,2],[4,3],[12.5,8.5]]){
   list.growTo(width,height);assertListLayout(list);
   for(const [name,axis] of Object.entries(scrollbar.axes)){
    const metrics=scrollbar.axisMetrics(name);
    if(metrics.trackSize<metrics.cellSize&&(metrics.cellCount||!axis.thumb.hidden||axis.cells.textContent))
     throw Error('A zero-cell scrollbar track still draws a thumb or track glyph');
   }
  }
  list.locate(listBounds);assertListLayout(list);
  const makeScrollFrame=()=>{
   const root=document.createElement('div');root.style.cssText=TV.TVView._boundsStyle(2,1,18,6);
   root.innerHTML='<div data-tv-viewport style="overflow:auto;white-space:pre">'+Array.from({length:40},()=> 'A long scrolling row '.repeat(5)).join('\\n')+'</div>'
    +new TV.TVScrollBar(new TV.TVRect(),TV.sbVertical).draw();
   const logical=new TV.TVGroup(new TV.TVRect(2,1,20,7));logical.bindRoot(root);program.desktopView.root.append(root);return {root,logical};
  };
  const firstFrame=makeScrollFrame(),secondFrame=makeScrollFrame(),adapter=new TV.TVScrollBar(new TV.TVRect(),TV.sbVertical);
  adapter.bindRoot(firstFrame.root);adapter._setClientExtent(new TV.TVRect(0,0,18,6));
  const oldAxis=adapter.axes.y,oldViewport=adapter.viewport;let steps=0,updates=0;
  const step=adapter.scrollStep.bind(adapter),update=adapter.update.bind(adapter);
  adapter.scrollStep=(...args)=>{steps++;step(...args);};adapter.update=()=>{updates++;update();};
  for(let i=0;i<4;i++)adapter.bindRoot(firstFrame.root);
  oldAxis.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
  if(steps!==1||adapter._clientExtent?.width!==18||firstFrame.root._tvView!==firstFrame.logical)throw Error('Scrollbar rebind duplicated input or replaced its owning view');
  oldAxis.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  oldAxis.thumb.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true,clientY:oldAxis.thumb.getBoundingClientRect().top}));
  adapter.bindRoot(secondFrame.root);adapter._setClientExtent(new TV.TVRect(0,0,18,6));
  if(adapter.repeatTimer!==null||adapter.dragState||oldAxis.root._tvScrollbar||secondFrame.root._tvView!==secondFrame.logical)
   throw Error('Rebinding scrollbar retained a timer, drag, stale root or lost its owner');
  const beforeSteps=steps,beforeUpdates=updates;
  oldAxis.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  oldViewport.dispatchEvent(new Event('scroll'));firstFrame.root.dispatchEvent(new WheelEvent('wheel',{deltaY:5,bubbles:true,cancelable:true}));
  if(steps!==beforeSteps||updates!==beforeUpdates||adapter.viewport.scrollTop)throw Error('Detached scrollbar still accepts input');
  const finalAxis=adapter.axes.y;adapter.destroy();updates=0;
  finalAxis.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  window.dispatchEvent(new Event('resize'));
  if(adapter.root||adapter.viewport||Object.keys(adapter.axes).length||finalAxis.root._tvScrollbar||updates)throw Error('Destroyed scrollbar retains DOM or event bindings');
  adapter.bindRoot(null);new TV.TVScrollBar(new TV.TVRect()).destroy();firstFrame.root.remove();secondFrame.root.remove();
  for(const [horizontal,vertical] of [[false,false],[false,true],[true,false],[true,true]]){
   const h=horizontal?new TV.TVScrollBar(new TV.TVRect(),TV.sbHorizontal):null;
   const v=vertical?new TV.TVScrollBar(new TV.TVRect(),TV.sbVertical):null;
   const scroller=new TV.TVScroller(new TV.TVRect(2,1,20,7),h,v);
   const root=TV.TVView._fromHTML(scroller.draw());program.desktopView.root.append(root);scroller.resolve(root);
   try{
    const viewport=scroller.viewport,bar=v||h;
    viewport.innerHTML=new TV.TVStaticText(new TV.TVRect(0,0,60,40),'Scrollable content').draw();scroller.update();
    const checkExtent=()=>{
     const actual=viewport.getBoundingClientRect();
     if(Math.abs(actual.width-(scroller.size.x-(vertical?1:0))*cell.width)>1
      ||Math.abs(actual.height-(scroller.size.y-(horizontal?1:0))*cell.height)>1)
      throw Error('TVScroller does not derive its client bounds from its scrollbars');
    };
    checkExtent();
    const paint=getComputedStyle(viewport);
    if(paint.overflowX!=='auto'||paint.overflowY!=='auto'||paint.scrollbarWidth!=='none')
     throw Error('TVScroller does not share native viewport scrolling/scrollbar suppression');
    for(const name of Object.keys(bar?.axes||{})){
     if(bar.axisMetrics(name).maxScroll<=0)throw Error('TVScroller lost its content extent');
     bar.axes[name].forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
     document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
     if(bar.axisMetrics(name).scrollOffset<=0)throw Error('TVScroller arrow did not scroll its viewport');
     bar.setScrollPosition(name,0);
    }
    if(bar)viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
    else viewport.scrollTop=cell.height;
    if(!viewport.scrollTop&&!viewport.scrollLeft)throw Error('TVScroller ignored mouse wheel input');
    scroller.growTo(24,9);checkExtent();
    if(scroller.viewport!==viewport||scroller.root!==root)throw Error('TVScroller resize replaced its content');
    document.documentElement.classList.remove('tv-js');
    try{if(getComputedStyle(viewport).scrollbarWidth!=='auto')throw Error('Native scrollbar fallback is hidden without TVision enhancement');}
    finally{document.documentElement.classList.add('tv-js');}
    const before=viewport.scrollTop,arrow=bar?(v?bar.axes.y:bar.axes.x).forward:null;
    scroller.destroy();arrow?.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
    if(scroller.root||root._tvView||(bar&&bar.repeatTimer!==null)||viewport.scrollTop!==before)
     throw Error('Destroyed TVScroller retains its native bindings');
   }finally{scroller.destroy();root.remove();}
  }
  const thumbColor=getComputedStyle(scrollbar.axes.y.thumb).color,thumbBackground=getComputedStyle(scrollbar.axes.y.thumb).backgroundColor;
  scrollbar.setActive(false);const stopped=list.viewport.scrollTop;
  if([scrollbar.axes.y.backward,scrollbar.axes.y.forward].some(button=>!button.disabled||button.tabIndex!==-1))throw Error('Inactive scrollbar kept enabled native arrows');
  list.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
  scrollbar.axes.y.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  if(list.viewport.scrollTop!==stopped||scrollbar.repeatTimer!==null||getComputedStyle(scrollbar.axes.y.thumb).color!==thumbColor
   ||getComputedStyle(scrollbar.axes.y.thumb).backgroundColor!==thumbBackground)throw Error('Inactive scrollbar changed palette or accepted input');
  scrollbar.setActive(true);scrollbar.setScrollPosition('y',0);
  if([scrollbar.axes.y.backward,scrollbar.axes.y.forward].some(button=>button.disabled||button.tabIndex!==0))throw Error('Scrollbar did not restore its native arrow state');
  list.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
  if(!list.viewport.scrollTop)throw Error('Info box list stopped scrolling after resize');
  list.setItems(['Short'],0);list.updateScrollbar();
  assertListLayout(list);
  const emptyAxis=scrollbar.axes.y,emptyMetrics=scrollbar.axisMetrics('y');
  if(!emptyAxis.thumb.hidden||getComputedStyle(emptyAxis.thumb).display!=='none'
   ||emptyAxis.cells.textContent!==Array(emptyMetrics.cellCount).fill('▓').join('\\n')
   ||emptyAxis.root.getAttribute('aria-disabled')!=='true'||list.root.classList.contains('is-h-scrollable'))
   throw Error('Scrollbar did not hide its thumb and restore the inactive track when content fits');
  if(!emptyAxis.backward.disabled||!emptyAxis.forward.disabled)throw Error('Fitting content kept enabled native arrows');
  emptyAxis.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  if(scrollbar.repeatTimer!==null)throw Error('Unavailable scrollbar started arrow repeat');
  list.setItems(['123456789012345678901234567890'],0);
  if(!scrollbar.axes.x.root.hidden)throw Error('A fitting list still reserves a horizontal row');
  box.growTo(20,14);assertListLayout(list);
  if(scrollbar.axes.x.root.hidden)throw Error('List resize did not reveal its horizontal scrollbar');
  box.growTo(40,14);assertListLayout(list);
  if(!scrollbar.axes.x.root.hidden)throw Error('Widening the list did not return the horizontal row to its client');
  box.growTo(4,8);if(box.topFrame.text.length!==4)throw Error('Narrow info title escaped its frame');
  box.forEach(child=>{child.destroy?.();child.bindRoot(null);});box.bindRoot(null);boxRoot.remove();input.focus();
  const choices=new TV.TVDialog(new TV.TVRect(0,0,46,21),'Cluster state');
  const checks=new TV.TVCheckBoxes(new TV.TVRect(1,1,21,4),[
   {label:'First',checked:true},{label:'Disabled',disabled:true},{label:'Third'}]);checks.setData(4);
  const radios=new TV.TVRadioButtons(new TV.TVRect(1,6,21,9),[
   {label:'First',checked:true},{label:'Second'},{label:'Third'}]);radios.setData(2);
  const many=new TV.TVCheckBoxes(new TV.TVRect(23,1,43,13),Array.from({length:70},(_,index)=>({label:'Choice '+index,checked:index===68})));
  many.vScrollBar=new TV.TVScrollBar(new TV.TVRect(),TV.sbVertical);many.hScrollBar=new TV.TVScrollBar(new TV.TVRect());many.setData(1n<<65n);
  const horizontalOnly=new TV.TVCheckBoxes(new TV.TVRect(1,10,21,13),[{label:'Long option '.repeat(6)}]);
  horizontalOnly.hScrollBar=new TV.TVScrollBar(new TV.TVRect());
  const multi=new TV.TVMultiCheckBoxes(new TV.TVRect(1,14,21,17),[
   {label:'~M~ode',state:1},{label:'Long 🇸🇰 option '.repeat(3),state:2},{label:'Disabled',disabled:true}]);
  multi.setButtonState(2,false);
  multi.hScrollBar=new TV.TVScrollBar(new TV.TVRect());
  choices.insert(new TV.TVGroup(new TV.TVRect(0,0,44,19)).insertAll([checks,radios,many,horizontalOnly,multi]));
  manager.register('cluster-probe',choices);manager.open('cluster-probe');
  const checkClusterTabStops=()=>{
   const focusable=choices._focusViews().map(view=>view._focusTarget());
   for(const cluster of [checks,radios,many,horizontalOnly,multi]){
    const stops=focusable.filter(input=>cluster.choiceElements.includes(input));
    const enabled=cluster.choiceElements.filter(input=>!input.disabled);
    if(stops.length!==(enabled.length?1:0)||(stops.length&&stops[0]!==cluster.choiceElements[cluster.sel]))
     throw Error('Dialog Tab does not treat a cluster as one focus stop: '+cluster.type);
   }
  };checkClusterTabStops();
  if(radios.sel!==2||radios.choiceElements[2].tabIndex!==0)throw Error('Radio Tab entry ignored its pre-mount value');
  checks.focus();checks.choiceElements[checks.sel].dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));
  if(document.activeElement!==radios.choiceElements[2])throw Error('Tab did not enter the selected radio option');
  radios.choiceElements[2].dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));
  if(document.activeElement!==many.choiceElements[many.sel])throw Error('Tab stopped again inside the radio group');
  many.choiceElements[many.sel].dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));
  if(document.activeElement!==radios.choiceElements[2])throw Error('Shift-Tab did not restore the radio group entry');
  const assertClusterRows=cluster=>{
   const viewport=cluster.viewport||cluster.root,rect=viewport.getBoundingClientRect(),cell=TV.measureCells();
   cluster.choiceElements.forEach((control,index)=>{
    const row=control.parentElement,p=row.getBoundingClientRect();
    if(row.style.position!=='absolute'||Math.abs(p.left-rect.left+viewport.scrollLeft)>1
     ||Math.abs(p.top-rect.top+viewport.scrollTop-index*cell.height)>1||Math.abs(p.height-cell.height)>1
     ||p.width<viewport.clientWidth-1||(!cluster.hScrollBar&&Math.abs(p.width-viewport.clientWidth)>1)
     ||getComputedStyle(row).overflow!=='hidden')throw Error('Cluster row lost its bounded character rectangle');
    if(cluster.type==='button'){
     const button=control.getBoundingClientRect(),mark=control.querySelector('.tv-multicheck-mark').getBoundingClientRect();
     if(control.style.width==='100%'||Math.abs(button.left-p.left)>1||Math.abs(button.top-p.top)>1
      ||Math.abs(button.width-p.width)>1||Math.abs(button.height-p.height)>1||Math.abs(mark.left-p.left)>1)
      throw Error('Multi-check button escaped its row or retained native centered text');
    }
   });
  };
  for(const cluster of [checks,radios,many,horizontalOnly,multi])assertClusterRows(cluster);
  assertListLayout(many);assertListLayout(horizontalOnly);assertListLayout(multi);
  if(!multi.choiceElements[1].disabled||multi.choiceElements[1].getAttribute('aria-checked')!=='mixed')
   throw Error('Pre-mount multi-check disable mask or stored state was lost');
  multi.setButtonState(2,true);
  const clusterPalette=TV.buildPaletteFromCurrentStyle(),changedClusterPalette=TV.cloneColorPalette(clusterPalette);
  const assertChoiceColor=(element,attr)=>{
   const style=getComputedStyle(element),rgb=hex=>'rgb('+hex.slice(1).match(/../g).map(value=>parseInt(value,16)).join(', ')+')';
   if(style.color!==rgb(TV.DOS_COLORS[attr&15])||style.backgroundColor!==rgb(TV.DOS_COLORS[(attr>>4)&15]))
    throw Error('Cluster palette lost normal/focused/disabled paint: '+style.color+' / '+style.backgroundColor+' expected '+attr);
  };
  try{
   for(const [index,attr] of [[47,0x1e],[48,0x4f],[49,0x2a],[62,0x50]])TV.setColorPaletteAttribute(changedClusterPalette,index,attr);
   TV.applyColorPalette(changedClusterPalette);await new Promise(requestAnimationFrame);
   for(const cluster of [checks,radios,multi]){
    input.focus();
    const native=cluster.choiceElements[0],row=native.parentElement,mark=row.querySelector('.'+cluster.markClass);
    const before=cluster.type==='button'?cluster.multiMark(0):cluster.getData();
    assertChoiceColor(cluster.root,0x1e);assertChoiceColor(row,0x1e);
    native.focus();
    if(document.activeElement!==native)throw Error('Cluster focus did not reach its option: '+cluster.type);
    assertChoiceColor(row,0x4f);
    row.querySelectorAll('.tv-hotkey').forEach(key=>assertChoiceColor(key,0x4a));
    cluster.setButtonState(1,false);native.click();assertChoiceColor(row,0x50);
    row.querySelectorAll('.tv-hotkey').forEach(key=>assertChoiceColor(key,0x50));
    if(!native.disabled||(cluster.type==='button'?cluster.multiMark(0):cluster.getData())!==before)
     throw Error('Disabled cluster option accepted input or changed its stored value');
    cluster.setButtonState(1,true);native.focus();assertChoiceColor(row,0x4f);
    input.focus();assertChoiceColor(row,0x1e);
    row.querySelectorAll('.tv-hotkey').forEach(key=>assertChoiceColor(key,0x1a));
    if(cluster.choiceElements[0]!==native||native.parentElement!==row||row.querySelector('.'+cluster.markClass)!==mark)
     throw Error('Cluster palette/enable updates replaced mounted controls or marks');
   }
   multi.choiceElements[0].focus();TV.applyColorPalette(clusterPalette);await new Promise(requestAnimationFrame);
   assertChoiceColor(multi.choiceElements[0].parentElement,clusterPalette.flatMap(group=>group.items).find(item=>item.paletteIndex===48).attr);
   if(document.activeElement!==multi.choiceElements[0])throw Error('Live cluster palette edit lost native focus');
  }finally{TV.applyColorPalette(clusterPalette);await new Promise(requestAnimationFrame);}
  const multiButton=multi.choiceElements[0],multiRow=multiButton.parentElement;
  multiButton.click();multiButton.focus();
  if(multi.multiMark(0)!==2||multiButton.getAttribute('aria-checked')!=='mixed'||multiButton.textContent!=='[?] Mode')throw Error('Multi-check shared row lost native commands or mnemonic text');
  const packed=multi.getData();multi.setData(9);
  if(multi.getData()!==9||multi.multiMark(0)!==1||multi.multiMark(1)!==2
   ||multi.choiceElements[0]!==multiButton||multiButton.getAttribute('aria-checked')!=='true'
   ||multiButton.textContent!=='[X] Mode'||document.activeElement!==multiButton)throw Error('Multi-check SetData lost its packed record, marks or focused root');
  multi.setData(packed);
  for(const width of [30,2,20]){
   multi.growTo(width,3);assertClusterRows(multi);assertListLayout(multi);
   if(multi.choiceElements[0]!==multiButton||multiButton.parentElement!==multiRow||document.activeElement!==multiButton
    ||multi.multiMark(0)!==2)throw Error('Multi-check resize replaced state, row or focus');
  }
  if(horizontalOnly.scrollbarWidget.axes.y||horizontalOnly.viewport.clientWidth!==20*cell.width)throw Error('Horizontal-only cluster reserved a phantom vertical column');
  const marks=cluster=>Array.from(cluster.root.querySelectorAll('.tv-checkbox-mark,.tv-radio-mark'),node=>node.textContent);
  if(checks.getData()!==4||checks.choiceElements[0].checked||!checks.choiceElements[2].checked
   ||radios.getData()!==2||!radios.choiceElements[2].checked||many.getData()!==1n<<65n
   ||JSON.stringify(marks(checks))!=='["[ ]","[ ]","[X]"]'
   ||JSON.stringify(marks(radios))!=='["( )","( )","(•)"]')throw Error('Mounted clusters replaced pre-mount values');
  checks.choiceElements[0].click();radios.choiceElements[1].click();
  if(checks.getData()!==5||marks(checks)[0]!=='[X]'||radios.getData()!==1
   ||marks(radios)[1]!=='(•)'||marks(radios)[2]!=='( )')throw Error('Native cluster change did not update model and marks');
  checks.movedTo(0);checks.focus();const checkedRoot=checks.root,firstChoice=checks.choiceElements[0];
  checks.setData(0);checks.setButtonState(4,false);
  if(document.activeElement!==firstChoice||checks.root!==checkedRoot||marks(checks).some(mark=>mark!=='[ ]')
   ||!checks.choiceElements[2].disabled||checks.choiceElements[2].parentElement.className.indexOf('is-disabled')<0)throw Error('Cluster state update replaced focus or ignored disable mask');
  const firstMark=firstChoice.nextElementSibling,normal=getComputedStyle(firstChoice.parentElement);
  if(getComputedStyle(firstMark,'::before').content!=='none'||!normal.color||!normal.backgroundColor)throw Error('Cluster marks still depend on CSS content');
  firstChoice.dispatchEvent(new KeyboardEvent('keydown',{key:' ',code:'Space',bubbles:true,cancelable:true}));
  if(checks.getData()!==1||marks(checks)[0]!=='[X]')throw Error('Keyboard checkbox press did not update its mark');
  const beforeColor=getComputedStyle(firstChoice.parentElement).color;
  checks.drawView();
  if(checks.getData()!==1||marks(checks)[0]!=='[X]'||document.activeElement!==checks.choiceElements[0]
   ||!checks.choiceElements[2].disabled||getComputedStyle(checks.choiceElements[0].parentElement).color!==beforeColor)throw Error('Cluster redraw lost state, palette or focus');
  const checkInput=checks.choiceElements[0],radioInput=radios.choiceElements[1];
  for(const cluster of [checks,radios]){
   const bounds=cluster.getBounds();cluster.growTo(2,3);assertClusterRows(cluster);cluster.locate(bounds);assertClusterRows(cluster);
  }
  if(checks.choiceElements[0]!==checkInput||radios.choiceElements[1]!==radioInput||document.activeElement!==checkInput
   ||checks.getData()!==1||radios.getData()!==1)throw Error('Ordinary cluster resize replaced controls, selection or focus');
  many.viewport.scrollTop=10*cell.height;many.movedTo(65);many.focus();many.drawView();
  if(many.getData()!==1n<<65n||marks(many)[65]!=='[X]'||marks(many)[68]!=='[ ]'
   ||many.viewport.scrollTop!==10*cell.height||document.activeElement!==many.choiceElements[65])throw Error('Large cluster redraw lost data, scrolling or focus');
  many.strings[65].label='A long option '.repeat(5)+' 🇸🇰';many.drawView();assertListLayout(many);assertClusterRows(many);
  const clusterRoot=many.root,clusterViewport=many.viewport,clusterBar=many.scrollbarWidget;
  if(clusterBar.axes.x.root.hidden||document.activeElement!==many.choiceElements[65])throw Error('Wide cluster option did not reveal a horizontal scrollbar');
  many.growTo(90,12);assertListLayout(many);
  if(!clusterBar.axes.x.root.hidden||many.root!==clusterRoot||many.viewport!==clusterViewport||many.scrollbarWidget!==clusterBar
   ||many.getData()!==1n<<65n||document.activeElement!==many.choiceElements[65])throw Error('Cluster resize replaced state, focus or scroll controls');
  many.growTo(20,12);assertListLayout(many);
  if(clusterBar.axes.x.root.hidden)throw Error('Narrow cluster did not restore horizontal scrolling');
  clusterBar.setScrollPosition('x',8*cell.width);
  if(!many.viewport.scrollLeft)throw Error('Cluster horizontal scrolling does not work');
  assertClusterRows(many);
  horizontalOnly.setItems([{label:'Short'}]);assertListLayout(horizontalOnly);
  if(!horizontalOnly.scrollbarWidget.axes.x.root.hidden)throw Error('Short cluster option still reserves a horizontal row');
  horizontalOnly.hide();horizontalOnly.setItems([{label:'Hidden long option '.repeat(5)}]);horizontalOnly.show();
  await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
  assertListLayout(horizontalOnly);
  if(horizontalOnly.scrollbarWidget.axes.x.root.hidden)throw Error('Showing a hidden cluster did not recalculate overflow');
  assertClusterRows(horizontalOnly);
  const clusterFont=document.body.style.getPropertyValue('--tv-cell-size');
  try{
   for(const size of [14,16]){
    document.body.style.setProperty('--tv-cell-size',size+'px');window.dispatchEvent(new Event('resize'));
    await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
    for(const cluster of [checks,radios,many,horizontalOnly,multi])assertClusterRows(cluster);
   }
  }finally{
   if(clusterFont)document.body.style.setProperty('--tv-cell-size',clusterFont);else document.body.style.removeProperty('--tv-cell-size');
   window.dispatchEvent(new Event('resize'));await new Promise(requestAnimationFrame);
  }
  for(const cluster of [checks,radios,multi,many]){
   const nodes=[...cluster.choiceElements],value=cluster.getData(),mask=cluster.enableMask,states=cluster.strings.map((_option,index)=>cluster.multiMark(index)).join(',');
   cluster.setState(TV.sfDisabled,true);
   if(cluster.choiceElements.some(input=>!input.disabled||input.tabIndex!==-1)
    ||choices._focusViews().map(view=>view._focusTarget()).some(input=>cluster.choiceElements.includes(input)))throw Error('Disabled cluster kept an enabled choice or Tab stop');
   cluster.press(0);cluster.choiceElements[0].click();
   if(cluster.getData()!==value||cluster.enableMask!==mask||cluster.strings.map((_option,index)=>cluster.multiMark(index)).join(',')!==states)
    throw Error('Disabling a cluster reset stored values or allowed input');
   nodes.forEach(input=>assertChoiceColor(input.parentElement,cluster.getColor(4)));
   cluster.setState(TV.sfDisabled,false);checkClusterTabStops();
   if(cluster.choiceElements.some((input,index)=>input!==nodes[index]
    ||input.disabled!==(!cluster.buttonState(index)||Boolean(cluster.strings[index].disabled))))
    throw Error('Reenabling cluster replaced choices or lost individual disabled state');
  }
  const disabledBar=many.scrollbarWidget;disabledBar.setScrollPosition('y',0);
  disabledBar.axes.y.forward.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));
  if(disabledBar.repeatTimer===null)throw Error('Cluster repeat setup did not start');
  many.setState(TV.sfDisabled,true);const disabledOffset=many.viewport.scrollTop;
  if(disabledBar.repeatTimer!==null||!disabledBar.axes.y.forward.disabled)throw Error('Disabling cluster did not stop arrow repeat or disable its scrollbar');
  const disabledWheel=new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true});many.viewport.dispatchEvent(disabledWheel);
  if(!disabledWheel.defaultPrevented||many.viewport.scrollTop!==disabledOffset)throw Error('Disabled cluster still scrolls through native wheel fallback');
  manager.open('calc');manager.close('calc');
  if(!disabledBar.axes.y.forward.disabled)throw Error('Window activation enabled a disabled cluster scrollbar');
  manager.close('cluster-probe');manager.open('cluster-probe');
  if(many.choiceElements.some(input=>!input.disabled)||!disabledBar.axes.y.forward.disabled)throw Error('Reopening dialog enabled a disabled cluster');
  const outsideFocus=document.activeElement;many.focus();
  if(document.activeElement!==outsideFocus||many.getState(TV.sfFocused))throw Error('Disabled cluster claimed keyboard focus');
  many.setState(TV.sfDisabled,false);disabledBar.setScrollPosition('y',0);
  disabledBar.axes.y.thumb.dispatchEvent(new MouseEvent('mousedown',{button:0,clientY:100,bubbles:true,cancelable:true}));
  if(!disabledBar.dragState)throw Error('Cluster thumb setup did not start');
  many.setState(TV.sfDisabled,true);
  if(disabledBar.dragState)throw Error('Disabling cluster did not cancel thumb drag');
  const storedClusterValue=many.getData();many.drawView();
  if(many.getData()!==storedClusterValue||many.root.getAttribute('aria-disabled')!=='true'
   ||many.choiceElements.some(input=>!input.disabled)||!many.scrollbarWidget.axes.y.forward.disabled)
   throw Error('Disabled cluster redraw lost its model, accessibility or native disabled state');
  manager.open('calc');many.drawView();many.setState(TV.sfDisabled,false);
  if(many.scrollbarWidget.active||!many.scrollbarWidget.axes.y.forward.disabled)
   throw Error('Rebinding or enabling a background dialog cluster activated its scrollbar');
  const passiveOffset=many.viewport.scrollTop,passiveWheel=new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true});
  many.viewport.dispatchEvent(passiveWheel);
  if(!passiveWheel.defaultPrevented||many.viewport.scrollTop!==passiveOffset)throw Error('Redrawn background dialog accepted wheel input');
  manager.close('calc');checkClusterTabStops();
  if(!many.scrollbarWidget.active||many.scrollbarWidget.axes.y.forward.disabled)throw Error('Dialog reactivation did not restore enabled cluster scrolling');
  many.setItems([{label:'Replacement',checked:true},{label:'Off'}]);
  if(many.getData()!==1||marks(many)[0]!=='[X]'||many.viewport.scrollTop!==0)throw Error('Replacing cluster choices lost initial selection');
  const staleChoice=horizontalOnly.choiceElements[0],oldValue=horizontalOnly.getData();horizontalOnly.destroy();staleChoice.click();
  if(horizontalOnly.getData()!==oldValue)throw Error('Destroyed cluster still handled parent-routed input');
  choices.destroy();host.activate('app:both');input.focus();
  const lists=new TV.TVDialog(new TV.TVRect(0,0,54,25),'List lifecycle'),events=[];
  const simple=new TV.TVListViewer(new TV.TVRect(1,1,21,4));
  simple.setItems(['One','Two','Three'],1);simple.bind({onSelect:(_row,index)=>events.push('plain:'+index)});
  const prepared=new TV.TVListBox(new TV.TVRect(23,1,51,9));
  prepared.hScrollBar=new TV.TVScrollBar(new TV.TVRect(),TV.sbHorizontal);
  prepared.newList(Array.from({length:80},(_,index)=>'Row '+index+' '+ 'wide '.repeat(30)));
  prepared.focusItem(42,{scroll:false});
  prepared.bind({onSelect:(_row,index)=>events.push('list:'+index),onActivate:(_row,index)=>events.push('activate:'+index)});
  const outline=new TV.TVOutline(new TV.TVRect(1,5,21,9));
  outline.setTree([{key:'root',label:'Root',children:[{key:'child',label:'Child'}]}],'child',{expandAll:true});
  outline.bind({onSelect:row=>events.push('tree:'+row.key)});
  const grid=new TV.TVGridView(new TV.TVRect(1,10,51,20),[{title:'Name',width:36},{title:'Value',width:36}]);
  grid.setRows(Array.from({length:40},(_,index)=>['Name '+index+(index===3?' C++ + č <raw> 🇸🇰 '+'.'.repeat(80):''),'Value '+index]));
  grid.selectCell(30,1,{scroll:false});grid.setHeadersVisible(false);
  grid.bind({onSelect:(_row,index)=>events.push('grid:'+index)});
  lists.insert(new TV.TVGroup(new TV.TVRect(0,0,52,23)).insertAll([simple,prepared,outline,grid]));
  manager.register('list-probe',lists);manager.open('list-probe');await new Promise(requestAnimationFrame);
  const originalListPalette=TV.buildPaletteFromCurrentStyle(),editedListPalette=TV.cloneColorPalette(originalListPalette);
  try{
   for(const [index,attribute] of [[57,0x1e],[58,0x4f],[59,0x2b]])TV.setColorPaletteAttribute(editedListPalette,index,attribute);
   TV.applyColorPalette(editedListPalette);await new Promise(requestAnimationFrame);
   for(const control of [simple,prepared,outline,grid]){
    const row=control.selectedElement(),text=row.firstElementChild;
    input.focus();expectDOSPaint(control.root,0x1e);expectDOSPaint(row,0x2b);
    control.focusSelectedItem();expectDOSPaint(row,0x4f);
    control.setActive(false);expectDOSPaint(row,0x2b);control.setActive(true);expectDOSPaint(row,0x4f);
    const other=(control.selectedIndex+1)%control.items.length,previousIndex=control.selectedIndex;
    control.focusItem(other,{scroll:false});expectDOSPaint(row,0x1e);expectDOSPaint(control.selectedElement(),0x4f);
    control.focusItem(previousIndex,{scroll:false});control.focusSelectedItem();
    control.setState(TV.sfDisabled,true);expectDOSPaint(row,0x2b);
    if(control instanceof TV.TVGridView)expectDOSPaint(row.children[control.selectedColumn],0x2b);
    control.setState(TV.sfDisabled,false);control.focusSelectedItem();expectDOSPaint(row,0x4f);
    if(control.selectedElement()!==row||row.firstElementChild!==text)throw Error('List palette updates replaced mounted rows or text');
    if(control instanceof TV.TVGridView){expectDOSPaint(control.headerRoot,0x2b);expectDOSPaint(row.children[control.selectedColumn],0x4f);}
   }
  }finally{TV.applyColorPalette(originalListPalette);await new Promise(requestAnimationFrame);}
  for(const control of [simple,prepared,outline,grid]){
   const row=control.selectedElement(),selected=control.selectedIndex,column=control.selectedColumn,expanded=outline.expanded.size,count=events.length;
   control.focusSelectedItem();control.setState(TV.sfDisabled,true);
   if(control.itemsRoot().querySelector('[tabindex="0"]')||control.root.contains(document.activeElement))throw Error('Disabled list kept focus or a row Tab stop');
   const other=control.itemsRoot().querySelector('[data-tv-list-index="0"]');
   other.click();other.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true}));
   for(const key of ['Enter',' ','ArrowLeft','ArrowRight','ArrowDown','Home','End']){
    row.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true}));
   }
   if(control.selectedIndex!==selected||control.selectedColumn!==column||outline.expanded.size!==expanded||events.length!==count)
    throw Error('Disabled list/tree/grid accepted selection or activation input');
   control.setState(TV.sfDisabled,false);control.focusSelectedItem();
   if(control.selectedElement()!==row||document.activeElement!==row||row.tabIndex!==0)throw Error('Reenabled list lost its selection, node or focus entry');
  }
  assertListLayout(prepared);assertListLayout(grid);
  if(simple.itemsRoot().children.length!==3||simple.selectedIndex!==1||prepared.viewport.children.length!==80
   ||prepared.selectedIndex!==42||outline.selectedItem()?.key!=='child'||grid.rowsRoot.children.length!==40
   ||grid.selectedIndex!==30||grid.selectedColumn!==1||grid.rowsRoot.getAttribute('role')!=='rowgroup'
   ||grid.rowsRoot.querySelector('[data-tv-list-index="30"]')?.getAttribute('role')!=='row'
   ||!grid.selectedElement()?.querySelector('[data-tv-grid-column="1"]').classList.contains('is-selected')
   ||!grid.headerRoot.hidden)throw Error('Pre-mount list state was not rendered');
  simple.selectedElement().click();prepared.viewport.querySelector('[data-tv-list-index="2"]').click();
  outline.selectedElement().click();grid.rowsRoot.querySelector('[data-tv-list-index="3"] [data-tv-grid-column="0"]').firstElementChild.click();
  if(events.join(',')!=='plain:1,list:2,tree:child,grid:3')throw Error('Pre-mount list callbacks did not bind exactly once: '+events);
  const checkSingleRows=(control,height=1)=>{
   const r=control.itemsRoot().getBoundingClientRect(),cell=TV.measureCells();
   if(getComputedStyle(control.itemsRoot()).display==='grid')throw Error('List rows still depend on CSS grid');
   control.itemsRoot().querySelectorAll(control.itemSelector()).forEach((row,index)=>{const p=row.getBoundingClientRect();
    if(row.style.position!=='absolute'||Math.abs(p.left-r.left+control.itemsRoot().scrollLeft)>1
     ||Math.abs(p.top-r.top+control.itemsRoot().scrollTop-index*height*cell.height)>1||Math.abs(p.height-height*cell.height)>1)
     throw Error('List item is not placed in character rows');
    const texts=[...row.querySelectorAll(':scope > .tv-vlist-text')];
    texts.forEach((text,line)=>{const t=text.getBoundingClientRect(),inset=Math.min(cell.width,p.width/2),style=getComputedStyle(row),lineHeight=p.height/texts.length;
     if(text.style.position!=='absolute'||text.style.width==='100%'||Math.abs(t.left-p.left-inset)>1
      ||Math.abs(t.top-p.top-line*lineHeight)>1||Math.abs(t.width-Math.max(0,p.width-2*inset))>1||Math.abs(t.height-lineHeight)>1
      ||style.paddingLeft!=='0px'||style.paddingRight!=='0px')throw Error('List text still relies on CSS padding/percentage width or escaped its row');
    });
   });
  };
  checkSingleRows(simple);checkSingleRows(prepared);checkSingleRows(outline);
  const preparedRoot=prepared.root,preparedRow=prepared.selectedElement(),preparedBar=prepared.scrollbarWidget;
  prepared.focusSelectedItem();
  for(const [width,height] of [[35,10],[18,5],[28,8]]){
   prepared.growTo(width,height);assertListLayout(prepared);checkSingleRows(prepared);
   if(prepared.root!==preparedRoot||prepared.selectedElement()!==preparedRow||prepared.scrollbarWidget!==preparedBar
    ||document.activeElement!==preparedRow)throw Error('Single-column resize replaced a row, scrollbar or focus');
  }
  const originalRows=prepared.items;
  prepared.hide();prepared.setItems(Array.from({length:80},(_,i)=>({label:'C++ + <raw> č 😀 '+i+' '+'.'.repeat(90),icon:'💾'})),2);prepared.show();
  await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);checkSingleRows(prepared);
  if(prepared.scrollbarWidget.axes.x.root.hidden||prepared.viewport.scrollWidth<=prepared.viewport.clientWidth
   ||prepared.selectedElement().querySelector('raw'))throw Error('Hidden list preparation lost long Unicode/icon rows or text escaping');
  prepared.setItems(['Short'],0);prepared.updateScrollbar();
  if(!prepared.scrollbarWidget.axes.x.root.hidden||prepared.viewport.scrollLeft)throw Error('Short list retained horizontal scrolling');
  prepared.setItems(originalRows,2);
  simple.setItems(Array.from({length:25},(_,i)=>'Plain '+i),0);simple.focusItem(20);checkSingleRows(simple);
  if(simple.root.scrollTop<=0||simple.selectedElement().getBoundingClientRect().bottom>simple.root.getBoundingClientRect().bottom+1)throw Error('Plain list did not reveal an offscreen selection');
  simple.focusItem(0);simple.focus();const simpleRect=simple.root.getBoundingClientRect();
  const hit=document.elementFromPoint(simpleRect.left+2*cell.width,simpleRect.top+cell.height/2);
  if(simple.resolveIndex(hit)!==0)throw Error('Plain list hit testing differs from its rendered row');
  const simpleBounds=simple.getBounds(),simpleRow=simple.selectedElement(),simpleText=simpleRow.firstElementChild;
  simple.growTo(1,3);checkSingleRows(simple);simple.locate(simpleBounds);checkSingleRows(simple);
  simple.growTo(20,0);
  if(!simpleRow.classList.contains('is-flow')||simpleText.style.position||simpleText.style.width
   ||simple.root.clientHeight!==simple.items.length*cell.height)throw Error('List transition to document flow retained bounded text geometry');
  simple.locate(simpleBounds);checkSingleRows(simple);
  if(simple.selectedElement()!==simpleRow||simpleRow.firstElementChild!==simpleText||document.activeElement!==simpleRow)throw Error('List geometry transition replaced the row, text or focus');
  const listFont=document.body.style.getPropertyValue('--tv-cell-size');
  try{
   for(const size of [14,16]){
    document.body.style.setProperty('--tv-cell-size',size+'px');window.dispatchEvent(new Event('resize'));
    await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
    checkSingleRows(simple);checkSingleRows(prepared);checkSingleRows(outline);
   }
  }finally{
   if(listFont)document.body.style.setProperty('--tv-cell-size',listFont);else document.body.style.removeProperty('--tv-cell-size');
   window.dispatchEvent(new Event('resize'));await new Promise(requestAnimationFrame);
  }
  outline.setScrollViewport(lists.dialog);outline.drawView();
  if(outline.scrollViewport!==lists.dialog||outline.selectedItem()?.key!=='child')throw Error('Outline redraw lost its external scroll viewport');
  const outlineEvents=events.length;outline.selectedElement().click();
  if(events.length!==outlineEvents+1||events.at(-1)!=='tree:child')throw Error('Outline redraw lost node callbacks');
  outline.setScrollViewport();
  prepared.focusItem(42,{scroll:false});prepared.focusSelectedItem();
  prepared.viewport.scrollLeft=12*cell.width;prepared.viewport.scrollTop=20*cell.height;
  const stale=prepared.selectedElement(),staleViewport=prepared.viewport,countBefore=events.length;
  prepared.setActive(false);const palette=getComputedStyle(stale).backgroundColor;
  prepared.drawView();
  if(prepared.selectedIndex!==42||document.activeElement!==prepared.selectedElement()
   ||prepared.viewport.scrollLeft!==12*cell.width||prepared.viewport.scrollTop!==20*cell.height
   ||prepared.scrollbarWidget.active||!prepared.root.classList.contains('is-inactive')
   ||getComputedStyle(prepared.selectedElement()).backgroundColor!==palette)throw Error('List redraw lost selection, focus, scroll offsets or inactive state: '+JSON.stringify({
    selected:prepared.selectedIndex,focused:document.activeElement===prepared.selectedElement(),left:prepared.viewport.scrollLeft,top:prepared.viewport.scrollTop,
    active:prepared.scrollbarWidget.active,inactive:prepared.root.classList.contains('is-inactive'),color:getComputedStyle(prepared.selectedElement()).backgroundColor,palette,
    textWidth:prepared._itemTextWidth,scrollWidth:prepared.viewport.scrollWidth,clientWidth:prepared.viewport.clientWidth,rowWidth:prepared.selectedElement().style.width}));
  stale.click();stale.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  if(events.length!==countBefore||prepared.selectedIndex!==42||staleViewport.isConnected)throw Error('Detached list root retained event listeners');
  prepared.setActive(true);for(let i=0;i<4;i++)prepared.bindRoot(prepared.root);
  prepared.selectedElement().click();prepared.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
  if(events.slice(countBefore).join(',')!=='list:42,activate:42')throw Error('Rebinding duplicated or lost callbacks');
  grid.focusSelectedItem();grid.viewport.scrollTop=12*cell.height;grid.viewport.scrollLeft=10*cell.width;
  grid.drawView();
  if(grid.selectedColumn!==0||grid.selectedIndex!==3||grid.rowsRoot.getAttribute('role')!=='rowgroup'
   ||document.activeElement!==grid.selectedElement()||grid.viewport.scrollTop!==12*cell.height
   ||grid.viewport.scrollLeft!==10*cell.width||!grid.headerRoot.hidden)throw Error('Grid redraw lost state or its own row semantics');
  const checkGridText=(column,value)=>{
   const cell=TV.measureCells(),r=column.getBoundingClientRect(),text=column.firstElementChild,t=text?.getBoundingClientRect();
   if(!text?.classList.contains('tv-grid-text')||column.children.length!==1||text.style.position!=='absolute'
    ||text.textContent!==String(value??'')||text.querySelector('raw')||getComputedStyle(column).paddingLeft!=='0px'
    ||getComputedStyle(column).paddingRight!=='0px'||Math.abs(t.left-r.left-cell.width)>1||Math.abs(t.top-r.top)>1
    ||Math.abs(t.width-r.width+2*cell.width)>1||Math.abs(t.height-cell.height)>1
    ||getComputedStyle(text).textOverflow!=='ellipsis'||getComputedStyle(text).overflow!=='hidden'
    ||getComputedStyle(text).color!==getComputedStyle(column).color)throw Error('Grid text escaped its character inset, lost its value, clipping or palette');
  };
  const checkGridGeometry=()=>{
   const cell=TV.measureCells();
   const viewport=grid.viewport.getBoundingClientRect(),body=grid.rowsRoot.getBoundingClientRect();
   const width=Math.max(72*cell.width,viewport.width);
   if(Math.abs(body.width-width)>1||Math.abs(body.height-grid.items.length*cell.height)>1
    ||getComputedStyle(grid.rowsRoot).position!=='relative')throw Error('Grid body extent does not match its rows and columns');
   for(const index of [0,3,grid.items.length-1]){
    const row=grid.rowsRoot.children[index],r=row.getBoundingClientRect();
    if(getComputedStyle(row).display==='grid'||row.style.gridTemplateColumns||Math.abs(r.top-body.top-index*cell.height)>1
     ||Math.abs(r.left-body.left)>1||Math.abs(r.width-width)>1||Math.abs(r.height-cell.height)>1)throw Error('Grid row still depends on CSS grid geometry');
    Array.from(row.children).forEach((column,j)=>{const c=column.getBoundingClientRect();
     if(column.style.position!=='absolute'||Math.abs(c.left-r.left-j*36*cell.width)>1||Math.abs(c.top-r.top)>1
      ||Math.abs(c.width-36*cell.width)>1||Math.abs(c.height-cell.height)>1)throw Error('Grid cell does not follow character bounds');
     checkGridText(column,grid.items[index][j]);
    });
   }
   if(grid.headersVisible){const h=grid.headerRoot.getBoundingClientRect();
    if(getComputedStyle(grid.headerRoot).display==='grid'||grid.headerRoot.style.gridTemplateColumns
     ||Math.abs(h.top-viewport.top)>1||Math.abs(h.height-cell.height)>1||Math.abs(h.width-width)>1)throw Error('Grid header did not stay pinned in matching character bounds');
    Array.from(grid.headerRoot.children).forEach((column,j)=>{const c=column.getBoundingClientRect();
     if(Math.abs(c.left-h.left-j*36*cell.width)>1||Math.abs(c.width-36*cell.width)>1)throw Error('Header and data columns are not aligned');
     checkGridText(column,grid.columns[j].title);});
   }
  };
  checkGridGeometry();grid.setHeadersVisible(true);checkGridGeometry();
  grid.viewport.scrollTop=13*cell.height;grid.selectCell(12,1);grid.focusSelectedItem();
  const selectedGridCell=grid.selectedElement().querySelector('[data-tv-grid-column="1"]');
  if(selectedGridCell.getBoundingClientRect().top<grid.headerRoot.getBoundingClientRect().bottom-1)throw Error('Selected row was hidden under the sticky header');
  grid.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true,cancelable:true}));
  const pageRows=Math.floor(grid.viewport.clientHeight/cell.height)-1;
  grid.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'PageDown',bubbles:true,cancelable:true}));
  if(grid.selectedIndex!==pageRows||grid.visibleRows()!==pageRows)throw Error('Grid page navigation counted the header as a data row');
  const gridRoot=grid.root,gridRows=grid.rowsRoot,gridHeader=grid.headerRoot,gridRow=grid.selectedElement(),gridBars=grid.scrollbarWidget;
  const gridText=gridRow.firstElementChild.firstElementChild,gridHeaderText=gridHeader.firstElementChild.firstElementChild;
  for(const [width,height] of [[90,12],[42,9],[50,10]]){
   grid.growTo(width,height);assertListLayout(grid);checkGridGeometry();
   if(grid.root!==gridRoot||grid.rowsRoot!==gridRows||grid.headerRoot!==gridHeader||grid.selectedElement()!==gridRow
    ||grid.scrollbarWidget!==gridBars||document.activeElement!==gridRow||gridRow.firstElementChild.firstElementChild!==gridText
    ||gridHeader.firstElementChild.firstElementChild!==gridHeaderText)throw Error('Grid resize replaced controls, text, rows or focus');
   if(gridBars.axes.x.root.hidden!==(width>72))throw Error('Grid did not recalculate horizontal overflow after resizing');
  }
  grid.setHeadersVisible(false);
  if(grid.visibleRows()!==Math.floor(grid.viewport.clientHeight/cell.height)||!grid.headerRoot.hidden)throw Error('Hidden header still reserved a data row');
  grid.selectCell(0,1);grid.focusSelectedItem();
  grid.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'PageDown',bubbles:true,cancelable:true}));
  if(grid.selectedIndex!==grid.visibleRows())throw Error('Hidden-header page navigation used the old row count');
  grid.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'PageUp',bubbles:true,cancelable:true}));
  if(grid.selectedIndex!==0)throw Error('Grid PageUp did not return to the first row');
  grid.setHeadersVisible(true);grid.selectCell(0,0);grid.focusSelectedItem();
  const rightPoint=gridBars.axes.x.track.getBoundingClientRect();
  gridBars.axes.x.track.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true,clientX:rightPoint.right-1,clientY:rightPoint.top+rightPoint.height/2}));
  document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
  if(grid.viewport.scrollLeft<=0)throw Error('Grid horizontal scrollbar lost pointer input');
  grid.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
  if(grid.viewport.scrollTop<=0)throw Error('Grid wheel lost vertical input');
  checkGridGeometry();grid.setActive(false);const gridOffset=grid.viewport.scrollTop;
  grid.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
  if(grid.viewport.scrollTop!==gridOffset||!grid.root.classList.contains('is-inactive'))throw Error('Inactive grid accepted wheel input');
  checkGridGeometry();grid.setActive(true);
  const gridFont=document.body.style.getPropertyValue('--tv-cell-size');
  const fontGridRow=grid.selectedElement(),fontGridText=fontGridRow.firstElementChild.firstElementChild;
  try{
   for(const size of [14,16]){
    document.body.style.setProperty('--tv-cell-size',size+'px');window.dispatchEvent(new Event('resize'));
    await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);checkGridGeometry();
    if(fontGridRow.firstElementChild.firstElementChild!==fontGridText||document.activeElement!==fontGridRow)throw Error('Grid font change replaced text or focus');
   }
  }finally{
   if(gridFont)document.body.style.setProperty('--tv-cell-size',gridFont);else document.body.style.removeProperty('--tv-cell-size');
   window.dispatchEvent(new Event('resize'));await new Promise(requestAnimationFrame);
  }
  const compact=new TV.TVGridView(new TV.TVRect(1,10,31,16),[{title:'Narrow',width:3},{title:'C++ / 🇸🇰',width:8},{title:'Value',width:14}]);
  compact.setRows([['Long <raw> text','č + 😀','42'],['','Second','']]);lists.children[0].insert(compact);
  const compactRoot=TV.TVView._fromHTML(compact.draw());lists.children[0].root.append(compactRoot);compact.resolve(compactRoot);
  compact.headerRoot.childNodes.forEach((column,index)=>checkGridText(column,compact.columns[index].title));
  compact.rowsRoot.querySelectorAll('[data-tv-grid-column]').forEach(column=>checkGridText(column,compact.items[compact.resolveIndex(column)][Number(column.dataset.tvGridColumn)]));
  compact.rowsRoot.children[0].children[0].firstElementChild.click();
  if(compact.selectedIndex!==0||compact.selectedColumn!==0||compact.getText(0)!=='Long <raw> text\\tč + 😀\\t42')throw Error('Narrow grid lost nested text input or raw row data');
  lists.children[0].remove(compact);compact.destroy();compactRoot.remove();grid.focusSelectedItem();
  class ThreeLineList extends TV.TVListBox{
   _itemHeight(){return 3;}
   itemMarkup(item,index){return '<div role="option" tabindex="-1" class="tv-vlist-item" data-tv-list-index="'+index+'">'
    +item.map(text=>'<span class="tv-vlist-text">'+TV.escapeHtml(text)+'</span>').join('')+'</div>';}
  }
  const triple=new ThreeLineList(new TV.TVRect(1,10,32,18));
  triple.setItems(Array.from({length:30},(_,i)=>['Title '+i,'C++ + <raw> č 😀 '+i,'Description '+i]),0);
  lists.children[0].insert(triple);const tripleRoot=TV.TVView._fromHTML(triple.draw());
  lists.children[0].root.append(tripleRoot);triple.resolve(tripleRoot);
  triple.itemsRoot().children[2].children[2].click();triple.focusSelectedItem();
  const tripleRow=triple.selectedElement(),tripleText=tripleRow.children[2];
  if(triple.selectedIndex!==2||tripleRow.querySelector('raw'))throw Error('Generic multiline list lost nested clicks or text escaping');
  for(const [width,height] of [[19,7],[2,4],[31,8]]){
   triple.growTo(width,height);checkSingleRows(triple,3);
   if(triple.selectedElement()!==tripleRow||tripleRow.children[2]!==tripleText||document.activeElement!==tripleRow)
    throw Error('Generic multiline resize replaced text or focus');
  }
  triple.focusItem(0);triple.focus();const triplePage=triple.visibleRows();
  triple.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'PageDown',bubbles:true,cancelable:true}));
  if(triple.selectedIndex!==triplePage||triple.topItem!==Math.floor(triple.viewport.scrollTop/(3*TV.measureCells().height)))
   throw Error('Generic multiline paging counted text lines instead of records');
  const tripleFont=document.body.style.getPropertyValue('--tv-cell-size'),focusedTriple=triple.selectedElement();
  try{for(const size of [14,16]){
   document.body.style.setProperty('--tv-cell-size',size+'px');window.dispatchEvent(new Event('resize'));
   await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);checkSingleRows(triple,3);
   if(document.activeElement!==focusedTriple)throw Error('Generic multiline font change lost focus');
  }}finally{
   if(tripleFont)document.body.style.setProperty('--tv-cell-size',tripleFont);else document.body.style.removeProperty('--tv-cell-size');
   window.dispatchEvent(new Event('resize'));await new Promise(requestAnimationFrame);
  }
  lists.children[0].remove(triple);triple.destroy();tripleRoot.remove();grid.focusSelectedItem();
  grid.setActive(true);grid.setRows([]);grid.setHeadersVisible(false);await new Promise(requestAnimationFrame);
  if(grid.rowsRoot.children.length||gridBars.axes.x.root.hidden!==true||!gridBars.axes.y.root.classList.contains('is-disabled'))throw Error('Empty grid retained rows or unnecessary scrolling');
  const searchProbe=new TV.TVSearchDialog(),message=searchProbe.resultsBox;
  message.setMessage('First status');const preparedMessage=message.messageView;message.setMessage('Prepared status');
  if(message.messageView!==preparedMessage)throw Error('Pre-mount status replacement discarded its owned text view');
  program.desktopView.insert(searchProbe);
  message.drawView();if(!message.messageView.root?.isConnected||message.messageView.root.textContent!=='Prepared status')throw Error('List-owned message was not rebound');
  const preparedMessageRoot=preparedMessage.root;message.setMessage('Updated status');
  if(message.messageView!==preparedMessage||preparedMessage.root!==preparedMessageRoot||preparedMessage.getText()!=='Updated status')
   throw Error('Status update replaced its mounted text view');
  TV.TVDialog.prototype.open.call(searchProbe);
  const searchEvents=[];
  message.bind({onSelect:(_row,index)=>searchEvents.push('select:'+index),onActivate:(_row,index)=>searchEvents.push('activate:'+index)});
  const searchRows=Array.from({length:40},(_,index)=>({title:'Result '+index+' '+ 'long title '.repeat(15),source_file:'Borland C++/Very long original HELP filename '+index+'.json.gz'}));
  message.setItems(searchRows,0);checkSingleRows(message,2);assertListLayout(message);
  if(preparedMessage.root||preparedMessage.owner||preparedMessageRoot._tvView)throw Error('Results retained a discarded status binding or owner');
  const checkSearchRows=()=>{
   checkSingleRows(message,2);
   for(const row of message.itemsRoot().children){
    const text=row.firstElementChild,entry=searchRows[message.resolveIndex(row)],titleLength=entry.title.length;
    if(row.tagName==='BUTTON'||row.children.length!==1||text.textContent!==entry.title+'\\n'+entry.source_file
     ||getComputedStyle(text).whiteSpace!=='pre')throw Error('Search result did not use the shared list text drawing');
    const range=document.createRange();range.setStart(text.firstChild,0);range.setEnd(text.firstChild,1);const title=range.getBoundingClientRect();
    range.setStart(text.firstChild,titleLength+1);range.setEnd(text.firstChild,titleLength+2);const source=range.getBoundingClientRect();
    if(Math.abs(source.top-title.top-cell.height)>1)throw Error('Search source name is not exactly one character row below its title');
   }
  };
  checkSearchRows();const resultMeta=message.itemsRoot().children[3].firstElementChild,secondLine=resultMeta.getBoundingClientRect();
  const resultHit=document.elementFromPoint(secondLine.left+cell.width,secondLine.top+1.5*cell.height);
  if(resultHit!==resultMeta)throw Error('Search second line has a different native hit target');resultHit.click();
  if(message.selectedIndex!==3||searchEvents.join(',')!=='select:3'||message.selectedItem().source_file!==searchRows[3].source_file)throw Error('Search second-line click selected/activated a different result');
  message.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
  if(searchEvents.at(-1)!=='activate:3')throw Error('Search result activation was lost');
  message.focusItem(0);message.focus();const searchPage=Math.floor(message.viewport.clientHeight/(2*cell.height));
  message.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'PageDown',bubbles:true,cancelable:true}));
  if(message.selectedIndex!==searchPage||message.visibleRows()!==searchPage)throw Error('Search PageDown did not count complete two-line results');
  message.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));await new Promise(requestAnimationFrame);
  if(message.topItem!==Math.floor(message.viewport.scrollTop/(2*cell.height)))throw Error('Search topItem counted text lines instead of results');
  const searchRoot=message.root,searchRow=message.selectedElement(),searchText=searchRow.firstElementChild,searchBounds=message.getBounds();message.focusSelectedItem();
  message._paintPalette(resultMeta,0x4f);const metaColor=getComputedStyle(resultMeta).color;
  message.growTo(38,13);checkSearchRows();message.locate(searchBounds);checkSearchRows();
  if(getComputedStyle(resultMeta).color!==metaColor)throw Error('List resize erased child palette paint');
  message._paintPalette(resultMeta,null);
  if(message.root!==searchRoot||message.selectedElement()!==searchRow||searchRow.firstElementChild!==searchText||document.activeElement!==searchRow)throw Error('Search resize replaced rows, text or focus');
  const messageText='Long status message '+ 'wrapped words '.repeat(40);message.setMessage(messageText);
  const messageRoot=message.messageView.root;message.growTo(31,12);
  if(message.messageView.root!==messageRoot||message.messageText!==messageText||message.messageView.getText()!==TV.wrapTextLines(messageText,28).join("\\n")||message.itemsRoot().querySelector(message.itemSelector())
   ||message.messageView.size.x!==28||message.messageView.size.y!==TV.wrapTextLines(messageText,28).length)throw Error('Search message lost its bounds, raw text or nonselectable state');
  message.drawView();if(message.messageView.root.textContent!==TV.wrapTextLines(messageText,28).join('\\n'))throw Error('Search message redraw lost its text');
  const messageView=message.messageView,updatedMessage=messageText+'More detail.',mountedMessageRoot=messageView.root;
  message.setMessage(updatedMessage);
  if(message.messageView!==messageView||messageView.root!==mountedMessageRoot||message.messageText!==updatedMessage
   ||messageView.getText()!==TV.wrapTextLines(updatedMessage,28).join('\\n'))throw Error('Long status update replaced its view or retained stale wrapping');
  message.setMessage('Short status');
  if(messageView.root!==mountedMessageRoot||messageView.size.y!==1||messageView.getText()!=='Short status'
   ||message.scrollViewport.scrollTop||!message.scrollbarWidget.axes.y.root.classList.contains('is-disabled'))
   throw Error('Short status retained the old height or scrolling');
  const disposedMessage=message.messageView,disposedMessageRoot=disposedMessage.root;
  searchProbe.destroy();
  if(disposedMessage.root||disposedMessage.owner||disposedMessageRoot._tvView||message.messageView||message.items.length)
   throw Error('Search disposal retained its status binding, owner or items');
  const beforeDestroy=events.length,oldRow=prepared.selectedElement();prepared.destroy();oldRow.click();
  if(events.length!==beforeDestroy)throw Error('Destroyed list kept callbacks');
  lists.destroy();host.activate('app:both');input.focus();
  const flowOutline=new TV.TVOutline(new TV.TVRect());flowOutline.hasScrollbar=()=>false;
  flowOutline.setTree(Array.from({length:24},(_,i)=>({key:String(i),label:'Document topic '+i})),null,{expandAll:true});
  const flowOwner=new TV.TVGroup(new TV.TVRect(0,0,35,6)).insertAll([flowOutline]);
  const flowRoot=TV.TVView._fromHTML(flowOwner.draw());program.desktopView.root.append(flowRoot);flowOwner.resolve(flowRoot);
  const checkFlow=()=>{
   const r=flowOutline.viewport.getBoundingClientRect();
   if(flowOutline.scrollbarWidget||Math.abs(r.height-24*cell.height)>1)throw Error('Unbounded outline lost natural document height');
   Array.from(flowOutline.viewport.children).forEach((row,index)=>{const p=row.getBoundingClientRect(),text=row.firstElementChild,t=text.getBoundingClientRect();
    if(row.style.position!=='relative'||Math.abs(p.top-r.top-index*cell.height)>1||Math.abs(p.width-r.width)>1
     ||text.style.position||text.style.width||Math.abs(t.left-p.left-cell.width)>1||Math.abs(t.width-p.width+2*cell.width)>1)
     throw Error('Unbounded outline no longer flows with its native text inset');});
  };
  checkFlow();flowOwner.growTo(48,6);checkFlow();flowOutline.destroy();flowOwner.bindRoot(null);flowRoot.remove();
  {
   class LinkedStateOutline extends TV.TVOutline{
    getPalette(){return null;}
    renderNodeContent(node){return '<a href="#disabled-list-link"'+(node.tabIndex===undefined?'':' tabindex="'+node.tabIndex+'"')+'>'+TV.escapeHtml(node.label)+'</a>';}
   }
   const dialog=new TV.TVDialog(new TV.TVRect(0,0,70,26),'Disabled lists'),stateEvents=[];
   const plain=new TV.TVListViewer(new TV.TVRect(1,1,21,7));plain.setItems(Array.from({length:40},(_,i)=>'Plain '+i),1);
   const box=new TV.TVListBox(new TV.TVRect(23,1,45,8));box.newList(Array.from({length:40},(_,i)=>'Item '+i));box.focusItem(1,{scroll:false});
   const tree=new LinkedStateOutline(new TV.TVRect(1,10,23,22));
   tree.setTree([{key:'parent',label:'Parent',tabIndex:3,children:[{key:'child',label:'Child'}]},
    {key:'last',label:'Last',tabIndex:-1}], 'child',{expandAll:true});
   const table=new TV.TVGridView(new TV.TVRect(25,10,65,22),[{title:'Name',width:30},{title:'Value',width:30}]);
   table.setRows(Array.from({length:40},(_,i)=>['Row '+i,'Value '+i]));table.selectCell(1,1,{scroll:false});
   const sentinel=new TV.TVInputLine(new TV.TVRect(46,1,66,2),40),controls=[plain,box,tree,table];
   for(const control of controls)control.bind({onSelect:()=>stateEvents.push('select'),onActivate:()=>stateEvents.push('activate')});
   dialog.insert(new TV.TVGroup(new TV.TVRect(0,0,68,24)).insertAll([...controls,sentinel]));manager.register('disabled-list-probe',dialog);manager.open('disabled-list-probe');sentinel.focus();
   const links=Array.from(tree.itemsRoot().querySelectorAll('a')),originalTabs=links.map(link=>link.getAttribute('tabindex')),hash=location.hash;
   let targetClicks=0,targetPresses=0;links.forEach(link=>{
    link.addEventListener('click',event=>{targetClicks++;event.preventDefault();});
    link.addEventListener('mousedown',()=>targetPresses++);
   });
   for(let cycle=0;cycle<2;cycle++){
    tree.setState(TV.sfDisabled,true);links.forEach(link=>{link.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));link.click();});
    if(targetClicks||targetPresses||location.hash!==hash||links.some(link=>link.tabIndex!==-1))throw Error('Disabled list link reached its target, URL or Tab cycle');
    tree.setState(TV.sfDisabled,false);
    if(links.some((link,index)=>link.getAttribute('tabindex')!==originalTabs[index]))throw Error('Reenabled list did not restore exact descendant Tab attributes');
   }
   links[1].dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true}));links[1].click();
   if(targetClicks!==1||targetPresses!==1||stateEvents.join(',')!=='select')throw Error('Reenabled list link lost native/default event routing');stateEvents.length=0;sentinel.focus();
   for(const control of controls){
    const data=control.items;control.setState(TV.sfDisabled,true);
    control.focusItem(0,{scroll:false});control.focusItem(1);control.focusSelectedItem();control.focus();control.selectItem(0);
    if(control.selectedIndex!==1||control.items!==data||stateEvents.length||document.activeElement!==sentinel.root)
     throw Error('Disabled list lost programmatic updates, blocked-action semantics or outside focus');
    const viewport=control.scrollViewport||control.itemsRoot();viewport.scrollTop=0;
    const wheel=new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true});viewport.dispatchEvent(wheel);
    if(!wheel.defaultPrevented||viewport.scrollTop)throw Error('Disabled plain/framed list accepted wheel fallback');
    control.hide();control.drawView();
    if(!control.root.hidden||control.root.getAttribute('aria-disabled')!=='true')throw Error('List redraw lost visibility or disabled state');
    control.show();await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
    if(control.itemsRoot().querySelector('[tabindex="0"]')||control.itemsRoot().querySelector('a:not([tabindex="-1"])'))
     throw Error('Disabled list redraw restored a row/link Tab stop');
   }
   tree.setTree([{key:'new',label:'New parent',children:[{key:'nested',label:'New child'}]}],'nested',{expandAll:true});
   table.setRows([['New','1'],['Other','2']]);table.selectCell(1,1,{scroll:false});box.setItems(['New','Other'],1);plain.setItems(['New','Other'],1);
   manager.close('disabled-list-probe');manager.open('disabled-list-probe');sentinel.focus();
   for(const control of controls){
    if(!control.getState(TV.sfDisabled)||control.selectedIndex!==1||control.root.getAttribute('aria-disabled')!=='true')throw Error('Reopening disabled list lost updated model/state');
   }
   manager.open('calc');
   for(const control of controls){control.drawView();control.setState(TV.sfDisabled,false);
    if(control.active||control.scrollbarWidget?.active)throw Error('Rebinding/reenabling a passive list made it active');}
   manager.close('calc');sentinel.focus();
   if(tree.itemsRoot().querySelector('a').hasAttribute('tabindex'))throw Error('Updated links did not restore their original natural Tab entry');
   const foreign=plain.selectedElement();
   for(const control of [box,tree,table])control.handleEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:{type:'keydown',key:'ArrowRight',target:foreign}}));
   if(table.selectedColumn!==1||!tree.expanded.has('new')||stateEvents.length)throw Error('List subclass accepted a foreign event target');
   for(const control of controls){control.focusSelectedItem();const selected=control.selectedIndex;
    control.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',ctrlKey:true,bubbles:true,cancelable:true}));
    if(control.selectedIndex!==selected||stateEvents.length)throw Error('List consumed a modified owner/browser shortcut');}
   for(const control of controls)control.destroy();dialog.destroy();host.activate('app:both');input.focus();
  }
  const coverCanvas=document.createElement('canvas');coverCanvas.width=320;coverCanvas.height=160;
  coverCanvas.getContext('2d').fillStyle='#ff5555';coverCanvas.getContext('2d').fillRect(0,0,320,160);
  const coverPng=coverCanvas.toDataURL('image/png');window.coverProbeUrl=coverPng;
  coverCanvas.width=160;coverCanvas.height=320;coverCanvas.getContext('2d').fillStyle='#55ffff';coverCanvas.getContext('2d').fillRect(0,0,160,320);
  const portraitPng=coverCanvas.toDataURL('image/png');
  const waitImage=async(picture,loaded=true)=>{
   await new Promise((resolve,reject)=>{const end=performance.now()+4000;const check=()=>{
    if(picture.complete&&Boolean(picture.naturalWidth)===loaded&&(!loaded||picture.currentSrc===picture.src)){resolve();return;}
    if(performance.now()>end){reject(Error('Native image state did not settle'));return;}setTimeout(check,10);
   };check();});await new Promise(requestAnimationFrame);
  };
  const imageDialog=new TV.TVDialog(new TV.TVRect(0,0,46,18),'Image lifecycle');
  const imageView=new TV.TVImage(new TV.TVRect(2,1,12,6));imageView.setImage(coverPng,'Cover <one>');imageView.hide();
  const imageGroup=new TV.TVGroup(new TV.TVRect(0,0,44,16)).insertAll([imageView]);imageDialog.insert(imageGroup);
  manager.register('image-probe',imageDialog);manager.open('image-probe');
  const imageRoot=imageView.root,picture=imageRoot.querySelector('img'),placeholder=imageRoot.querySelector('span');
  expectDOSPaint(imageRoot,0x07);
  await waitImage(picture);
  if(!imageRoot.hidden||picture.hidden||!placeholder.hidden||picture.alt!=='Cover <one>'||picture.naturalWidth!==320||picture.naturalHeight!==160)throw Error('Image mount lost its prepared source, alt or visibility');
  imageView.show();imageRoot.tabIndex=0;imageView.focus();imageRoot.style.setProperty('--tv-current-frame','#123456');
  const imageMutations=[],observer=new MutationObserver(records=>imageMutations.push(...records));observer.observe(picture,{attributes:true,attributeFilter:['src']});
  for(let i=0;i<4;i++){imageView.setImage(coverPng,'Same cover');imageView.drawView();imageView.bindRoot(imageRoot);}
  await new Promise(requestAnimationFrame);
  if(imageMutations.length||imageView.root!==imageRoot||imageRoot.querySelector('img')!==picture||document.activeElement!==imageRoot
   ||picture.alt!=='Same cover'||picture.hidden||!placeholder.hidden)throw Error('Repeated image updates replaced controls, lost focus or restarted the same source');
  const checkImageBounds=()=>{
   const cell=TV.measureCells(),r=imageRoot.getBoundingClientRect(),p=picture.getBoundingClientRect(),owner=imageGroup.root.getBoundingClientRect();
   const near=(actual,expected)=>{if(Math.abs(actual-expected)>1)throw Error('Image drawing bounds differ: '+actual+' / '+expected);};
   near(r.left,owner.left+imageView.origin.x*cell.width);near(r.top,owner.top+imageView.origin.y*cell.height);
   near(r.width,imageView.size.x*cell.width);near(r.height,imageView.size.y*cell.height);
   if(['grid','flex'].includes(getComputedStyle(imageRoot).display))throw Error('Image still relies on CSS layout');
   if(getComputedStyle(picture).objectFit!=='contain'||p.left<r.left||p.right>r.right+1||p.top<r.top||p.bottom>r.bottom+1
    ||getComputedStyle(imageRoot).borderTopColor!=='rgb(18, 52, 86)')throw Error('Image escaped its character bounds or lost its frame palette');
   near(p.left,r.left+imageRoot.clientLeft);near(p.top,r.top+imageRoot.clientTop);
   near(p.width,imageRoot.clientWidth);near(p.height,imageRoot.clientHeight);
  };
  const checkImageCaption=text=>{
   const r=imageRoot.getBoundingClientRect(),caption=placeholder.getBoundingClientRect(),cell=TV.measureCells();
   if(picture.hidden===false||placeholder.hidden||placeholder.textContent!==text||caption.width>imageRoot.clientWidth+1||caption.height>imageRoot.clientHeight+1
    ||Math.abs((caption.left+caption.right)/2-r.left-imageRoot.clientLeft-imageRoot.clientWidth/2)>1
    ||Math.abs((caption.top+caption.bottom)/2-r.top-imageRoot.clientTop-imageRoot.clientHeight/2)>1
    ||Math.abs(caption.width-Math.min(text.length*cell.width,imageRoot.clientWidth))>1)throw Error('Image fallback lost centered/clipped character bounds');
  };
  imageView.growMode=TV.gfGrowHiX|TV.gfGrowHiY;
  imageGroup.growTo(48,18);checkImageBounds();imageGroup.growTo(44,16);checkImageBounds();
  imageView.growMode=0;
  for(const [width,height] of [[20,8],[7,4],[10,5]]){
   imageView.growTo(width,height);checkImageBounds();
   if(imageView.root!==imageRoot||imageRoot.querySelector('img')!==picture||imageRoot.querySelector('span')!==placeholder||document.activeElement!==imageRoot)throw Error('Image resize replaced controls or focus');
  }
  if(imageMutations.length)throw Error('Image resize restarted its source');observer.disconnect();
  const imageFont=document.documentElement.style.getPropertyValue('--tv-cell-size');
  try{
   for(const font of [14,16]){
    document.documentElement.style.setProperty('--tv-cell-size',font+'px');window.dispatchEvent(new Event('resize'));
    await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);checkImageBounds();
    if(document.activeElement!==imageRoot)throw Error('Image font resize stole focus');
   }
   imageGroup.hide();await new Promise(requestAnimationFrame);imageGroup.show();
   await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);checkImageBounds();imageView.focus();
  }finally{document.documentElement.style.setProperty('--tv-cell-size',imageFont);window.dispatchEvent(new Event('resize'));}
  const pendingCover=URL.createObjectURL(await(await fetch(coverPng)).blob());
  imageView.setImage(pendingCover,'Loading cover');checkImageCaption('Loading');await waitImage(picture);checkImageBounds();
  imageView.setImage(coverPng,'Cover again');await waitImage(picture);URL.revokeObjectURL(pendingCover);
  imageView.setImage('/assets/missing-cover-for-test.png','Missing cover');await waitImage(picture,false);
  if(!picture.hidden||placeholder.hidden||placeholder.textContent!=='No cover')throw Error('Failed image did not show its fallback');
  checkImageCaption('No cover');
  observer.observe(picture,{attributes:true,attributeFilter:['src']});imageMutations.length=0;
  imageView.setImage('/assets/missing-cover-for-test.png','Missing cover');imageView.drawView();await new Promise(requestAnimationFrame);
  if(imageMutations.length)throw Error('Redrawing a failed image retried the same request');observer.disconnect();
  imageView.setImage('data:image/png;base64,AA==','Old failed image');imageView.setImage(portraitPng,'Portrait cover');await waitImage(picture);
  picture.dispatchEvent(new Event('error'));picture.dispatchEvent(new Event('load'));
  if(picture.hidden||!placeholder.hidden||picture.naturalWidth!==160||picture.naturalHeight!==320||picture.alt!=='Portrait cover')throw Error('An old image event hid the current decoded image');
  checkImageBounds();imageView.setImage('');imageView.growTo(3,2);
  const narrow=imageRoot.getBoundingClientRect(),caption=placeholder.getBoundingClientRect();
  checkImageCaption('No cover');
  if(picture.hasAttribute('src')||!picture.hidden||placeholder.hidden||placeholder.textContent!=='No cover'
   ||caption.left<narrow.left||caption.right>narrow.right+1||imageRoot.scrollWidth>imageRoot.clientWidth)throw Error('Empty/narrow image did not clear and clip its fallback');
  imageView.growTo(10,5);imageView.setImage(coverPng,'Rebound cover');await waitImage(picture);
  const rebound=TV.TVView._fromHTML(imageView.draw());imageRoot.replaceWith(rebound);imageView.bindRoot(rebound);
  const reboundPicture=rebound.querySelector('img');await waitImage(reboundPicture);picture.dispatchEvent(new Event('error'));
  if(imageRoot._tvView||imageView.root!==rebound||reboundPicture.hidden||reboundPicture.alt!=='Rebound cover')throw Error('Image rebind retained an old root or lost its source');
  imageView.destroy();reboundPicture.dispatchEvent(new Event('load'));reboundPicture.dispatchEvent(new Event('error'));
  if(imageView.root||imageView._picture||imageView._placeholder||imageView.resizeObserver||rebound._tvView)throw Error('Destroyed image retained its event roots or resize observer');
  imageDialog.destroy();host.activate('app:both');input.focus();
  const terminalDialog=new TV.TVDialog(new TV.TVRect(0,0,62,16),'Terminal bounds');
  const terminalView=new TV.TVTerminal(new TV.TVRect(0,1,30,4),4);terminalView.growMode=TV.gfGrowHiX|TV.gfGrowHiY;
  terminalView.append('Before mount');terminalView.appendChunk('partial');
  const terminalInfo=new TV.TVInfoBox(new TV.TVRect(1,1,31,6),'Event log',[terminalView]);
  const terminalInput=new TV.TVInputLine(new TV.TVRect(43,1,58,2),40);terminalInput.setData('input draft');
  terminalDialog.insert(new TV.TVGroup(new TV.TVRect(0,0,60,14)).insertAll([terminalInfo,terminalInput]));
  manager.register('terminal-probe',terminalDialog);manager.open('terminal-probe');
  const checkTerminal=()=>{
   const r=terminalView.root.getBoundingClientRect(),color=getComputedStyle(terminalInfo.topFrame.root).color;
   if(getComputedStyle(terminalView.root).display==='flex'||terminalView.lineElements.length!==terminalView.size.y)throw Error('Terminal rows still depend on CSS flow');
   terminalView.lineElements.forEach((line,index)=>{const p=line.getBoundingClientRect();
    if(line.style.position!=='absolute'||Math.abs(p.left-r.left)>1||Math.abs(p.top-r.top-index*cell.height)>1
     ||Math.abs(p.width-terminalView.size.x*cell.width)>1||Math.abs(p.height-cell.height)>1
     ||Array.from(line.textContent).length!==terminalView.size.x||line.querySelector('source'))throw Error('Terminal row lost cell bounds, clipping or escaped text');
    if(line.querySelectorAll('[data-tv-info-side]').length!==2||Array.from(line.querySelectorAll('[data-tv-info-side]')).some(side=>getComputedStyle(side).color!==color))
     throw Error('Terminal side borders lost their frame palette');
   });
  };
  checkTerminal();
  if(!terminalView.root.textContent.includes('Before mount')||!terminalView.root.textContent.includes('partial'))throw Error('Mounting Terminal lost buffered output');
  terminalView.appendChunk(' line\\r');terminalView.appendChunk('\\nNext');
  if(terminalView.lines.at(-1)!=='partial line'||terminalView.streamTail!=='Next')throw Error('Terminal changed a split CRLF into an empty line');
  const longLog='<source> & '+'x'.repeat(100);terminalView.append(longLog);
  terminalInput.focus();terminalInput.root.setSelectionRange(2,7);
  const terminalRoot=terminalView.root,terminalFirst=terminalView.lineElements[0];
  for(const [width,height] of [[40,8],[12,3],[30,5]]){
   terminalInfo.growTo(width,height);assertBounds(terminalView,terminalInfo);checkTerminal();
   if(terminalView.root!==terminalRoot||terminalView.lineElements[0]!==terminalFirst||terminalView.lines.at(-1)!==longLog
    ||terminalView.streamTail!=='Next'||document.activeElement!==terminalInput.root
    ||terminalInput.root.selectionStart!==2||terminalInput.root.selectionEnd!==7)throw Error('Terminal resize lost its buffer, root, reused row or surrounding input focus');
  }
  const unchangedBorder=terminalView.lineElements[0].firstChild;terminalView.render();terminalView.render();
  if(terminalView.lineElements[0].firstChild!==unchangedBorder)throw Error('Unchanged Terminal output rebuilt row content');
  terminalView.drawView();checkTerminal();
  if(!terminalView.root.textContent.includes('Next')||terminalView.lines.at(-1)!==longLog)throw Error('Terminal redraw lost buffered text');
  terminalView.growTo(30,0);
  if(terminalView.lineElements.length||terminalView.root.children.length)throw Error('Zero-height Terminal retained visible rows');
  terminalView.growTo(30,3);checkTerminal();terminalView.clear();checkTerminal();
  if(terminalView.lines.length||terminalView.streamTail||terminalView.lineElements.some(line=>line.textContent.trim()!=='│'+' '.repeat(28)+'│'))throw Error('Clearing Terminal removed a border or retained text');
  terminalView.destroy();if(terminalView.root||terminalView.lineElements.length)throw Error('Terminal destroy retained browser roots');
  terminalDialog.destroy();host.activate('app:both');input.focus();
  const gaugeDialog=new TV.TVDialog(new TV.TVRect(0,0,50,12),'Progress bounds');
  const gaugeGroup=new TV.TVGroup(new TV.TVRect(1,1,41,8));
  const gaugeBar=new TV.TVBarGauge(new TV.TVRect(1,1,21,2),200),gaugePercent=new TV.TVPercentGauge(new TV.TVRect(1,3,6,4),200);
  gaugeBar.getPalette=()=>[0x4f];
  gaugeBar.growMode=TV.gfGrowHiX;gaugeGroup.insertAll([gaugeBar,gaugePercent]);gaugeDialog.insert(gaugeGroup);
  gaugeGroup.broadcast(TV.cmUpdateGauge,null,80);gaugePercent.hide();
  manager.register('gauge-probe',gaugeDialog);manager.open('gauge-probe');
  const barRoot=gaugeBar.root,percentRoot=gaugePercent.root;
  if(barRoot.textContent!=='█'.repeat(8)+'░'.repeat(12)||!percentRoot.hidden||percentRoot.textContent!=='40 %')throw Error('Gauges lost pre-mount values/visibility');
  gaugePercent.show();barRoot.tabIndex=0;gaugeBar.focus();expectDOSPaint(barRoot,0x4f);
  const unchangedGauge=barRoot.firstChild;
  gaugeGroup.broadcast(TV.cmUpdateGauge,null,81);
  if(barRoot.firstChild!==unchangedGauge||barRoot.getAttribute('aria-valuenow')!=='81')throw Error('Unchanged gauge fill rebuilt text or lost current ARIA value');
  for(const width of [45,20,40]){
   gaugeGroup.growTo(width,7);assertBounds(gaugeBar,gaugeGroup);
   const count=gaugeBar.size.x,fill=Math.floor(81*count/200);
   if(barRoot.textContent!=='█'.repeat(fill)+'░'.repeat(count-fill)||gaugeBar.root!==barRoot||gaugePercent.root!==percentRoot
    ||document.activeElement!==barRoot||getComputedStyle(barRoot).color!=='rgb(255, 255, 255)'
    ||getComputedStyle(barRoot).backgroundColor!=='rgb(170, 0, 0)')throw Error('Gauge resize replaced its root, lost focus/palette or did not repaint cells');
  }
  gaugeBar.hide();gaugeGroup.broadcast(TV.cmAddGauge,null,19);
  if(!barRoot.hidden||percentRoot.textContent!=='50 %')throw Error('Broadcast update lost gauge visibility or percent');
  gaugeBar.show();gaugeGroup.broadcast(TV.cmResetGauge,null,400);
  if(barRoot.getAttribute('aria-valuemax')!=='400'||barRoot.textContent!=='░'.repeat(gaugeBar.size.x)||percentRoot.textContent!=='0  %')throw Error('Reset did not clear gauges/change range');
  gaugeGroup.broadcast(TV.cmUpdateGauge,null,400);gaugeBar.drawView();gaugePercent.drawView();
  if(barRoot.textContent!=='█'.repeat(gaugeBar.size.x)||percentRoot.textContent!=='100%'||gaugeBar.root!==barRoot||gaugePercent.root!==percentRoot)throw Error('Completed gauge did not retain its mounted controls');
  gaugeDialog.destroy();host.activate('app:both');input.focus();
  const progressProbe=new TV.TVProgressDialog('Progress layout');
  progressProbe.update({percent:37,processed:3,total:8,file:'Sample HELP file',phase:'Converting'});
  manager.register('progress-probe',progressProbe);manager.open('progress-probe');
  const progressBarRoot=progressProbe.bar.root,progressPercentRoot=progressProbe.percent.root;
  progressProbe.setDetails([{id:'sample',name:'Sample HELP file',marker:'⚙ 37%'}],'One package');
  progressProbe.moreButton.root.click();
  if(!progressProbe.detailsExpanded)throw Error('Progress details did not open through TVEvent');
  progressProbe.update({percent:64,processed:5,total:8,file:'Another HELP file',phase:'Converting'});
  progressProbe.moreButton.root.click();
  if(progressProbe.detailsExpanded||progressProbe.bar.root!==progressBarRoot||progressProbe.percent.root!==progressPercentRoot
   ||progressBarRoot.textContent!=='█'.repeat(Math.floor(progressProbe.bar.size.x*64/100))+'░'.repeat(progressProbe.bar.size.x-Math.floor(progressProbe.bar.size.x*64/100))
   ||progressPercentRoot.textContent!=='64 %')throw Error('Progress More/Less/update lost gauge roots or painted stale progress');
  progressProbe.destroy();host.activate('app:both');input.focus();
  const columnDialog=new TV.TVDialog(new TV.TVRect(0,0,70,18),'List columns');
  const twoColumns=new TV.TVListBox(new TV.TVRect(1,1,32,10),2),threeColumns=new TV.TVListViewer(new TV.TVRect(35,1,65,9),3);
  const columnEntries=Array.from({length:60},(_,index)=>'Entry '+String(index).padStart(2,'0'));
  twoColumns.newList(columnEntries);threeColumns.setItems(columnEntries,0);
  columnDialog.insertAll([new TV.TVGroup(new TV.TVRect(0,0,68,16)).insertAll([twoColumns,threeColumns])]);
  manager.register('column-probe',columnDialog);manager.open('column-probe');await new Promise(requestAnimationFrame);
  const checkColumns=(control,rows,width)=>{
   const viewport=control.scrollViewport||control.itemsRoot(),rect=viewport.getBoundingClientRect(),items=control.itemsRoot().querySelectorAll(control.itemSelector());
   if(control.visibleRows()!==rows||getComputedStyle(viewport).display==='grid')throw Error('Column count/rows still depend on CSS grid');
   for(const index of [0,rows-1,rows,rows*2]){
    const r=items[index]?.getBoundingClientRect();if(!r)continue;
    if(Math.abs(r.left-rect.left+viewport.scrollLeft-Math.floor(index/rows)*width*cell.width)>1
     ||Math.abs(r.top-rect.top-index%rows*cell.height)>1||Math.abs(r.height-cell.height)>1)throw Error('List column position does not follow cell bounds');
   }
  };
  assertListLayout(twoColumns);checkColumns(twoColumns,8,16);checkColumns(threeColumns,8,11);
  const columnBar=twoColumns.scrollbarWidget;
  if(columnBar.axes.y||!columnBar.axes.x||columnBar.axes.x.root.hidden)throw Error('Multi-column list did not use one persistent horizontal scrollbar');
  twoColumns.focusItem(1);
  for(const expected of [9,17]){
   twoColumns.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
   if(twoColumns.selectedIndex!==expected)throw Error('Shared list did not move by one column');
  }
  if(Math.abs(twoColumns.viewport.scrollLeft-16*cell.width)>1||twoColumns.topItem!==8)throw Error('Column selection did not reveal its page');
  columnBar.setScrollPosition('x',0);
  twoColumns.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
  if(twoColumns.viewport.scrollLeft<=0)throw Error('Vertical mouse wheel did not scroll the horizontal-only list');
  columnBar.setScrollPosition('x',0);const columnTrack=columnBar.axes.x.track.getBoundingClientRect();
  columnBar.axes.x.track.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true,cancelable:true,clientX:columnTrack.right-1,clientY:columnTrack.top+columnTrack.height/2}));
  document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
  if(twoColumns.viewport.scrollLeft<=0)throw Error('Multi-column scrollbar track did not respond');
  twoColumns.setActive(false);const stoppedColumn=twoColumns.viewport.scrollLeft;
  twoColumns.viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:3,deltaMode:1,bubbles:true,cancelable:true}));
  if(twoColumns.viewport.scrollLeft!==stoppedColumn)throw Error('Inactive column list accepted scrolling');
  twoColumns.setActive(true);twoColumns.focusItem(17);twoColumns.focus();
  const columnRoot=twoColumns.root,columnViewport=twoColumns.viewport,columnRow=twoColumns.selectedElement();
  twoColumns.growTo(53,13);assertListLayout(twoColumns);checkColumns(twoColumns,12,27);
  twoColumns.growTo(31,9);assertListLayout(twoColumns);checkColumns(twoColumns,8,16);
  if(twoColumns.root!==columnRoot||twoColumns.viewport!==columnViewport||twoColumns.scrollbarWidget!==columnBar
   ||twoColumns.selectedIndex!==17||twoColumns.selectedElement()!==columnRow||document.activeElement!==columnRow)throw Error('Column resize replaced items or lost focus');
  threeColumns.focusItem(0);threeColumns.focus();threeColumns.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'PageDown',bubbles:true,cancelable:true}));
  if(threeColumns.selectedIndex!==24||threeColumns.itemsRoot().scrollLeft<=0)throw Error('Shared three-column list did not page by all visible rows');
  twoColumns.hide();twoColumns.setItems(columnEntries,17);twoColumns.show();
  await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);checkColumns(twoColumns,8,16);
  twoColumns.setItems(['Short'],0);
  if(columnBar.axes.x.root.hidden||!columnBar.axes.x.root.classList.contains('is-disabled')||twoColumns.viewport.scrollLeft!==0)
   throw Error('Short column list hid its scrollbar or retained stale scrolling');
  columnDialog.destroy();host.activate('app:both');input.focus();
  const fileProbe=new TV.TVFileOpenDialog();let openedFile=null;
  fileProbe.configure(Array.from({length:36},(_,index)=>({file:'sample'+index+'.json.gz',group:'Samples',title:'Sample '+index})),entry=>openedFile=entry);
  fileProbe.currentDirectory=fileProbe.entries[0].directory;fileProbe.refresh();
  manager.register('file-column-probe',fileProbe);manager.open('file-column-probe');await new Promise(requestAnimationFrame);
  const fileColumns=fileProbe.fileList;assertListLayout(fileColumns);checkColumns(fileColumns,8,16);
  if(document.activeElement!==fileProbe.nameInput.root||fileColumns.root.querySelector('.tv-scrollbar-y'))throw Error('File Open lost initial input focus or retained a second scrollbar');
  fileColumns.itemsRoot().querySelector('[data-tv-list-index="1"]').dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
  if(!openedFile||fileProbe.isOpen())throw Error('File list activation did not open the selected catalog entry');
  fileProbe.destroy();host.activate('app:both');input.focus();
  const positionedDialog=new TV.TVDialog(new TV.TVRect(0,0,52,27),'Window origin');
  const positionedOwner=new TV.TVGroup(new TV.TVRect(0,0,50,25));
  const positionedWindow=new TV.TVWindow(new TV.TVRect(3,4,23,12),'Positioned window');positionedOwner.insert(positionedWindow);
  positionedDialog.insert(positionedOwner);manager.register('positioned-probe',positionedDialog);manager.open('positioned-probe');
  assertBounds(positionedWindow,positionedOwner);
  positionedWindow.moveTo(9,6);assertBounds(positionedWindow,positionedOwner);
  positionedWindow.drawView();assertBounds(positionedWindow,positionedOwner);
  positionedWindow.bindRoot(null);positionedDialog.destroy();host.activate('app:both');input.focus();
  class IndependentHistory extends TV.TVDialog{
   constructor(){
    super(new TV.TVRect(0,0,42,14),'Independent history');
    const field=new TV.TVInputLine(new TV.TVRect(1,4,30,5),40);
    this.historyButton=new TV.TVHistory(new TV.TVRect(30,4,33,5),field,'unlisted-history');
    const popup=new TV.TVHistoryWindow(new TV.TVRect(1,0,33,8),'unlisted-history');
    this.insert(new TV.TVGroup(new TV.TVRect(0,0,40,12)).insertAll([field,this.historyButton,popup]));
    this.historyButton.bindWindow(popup);
   }
  }
  for(const kind of ['TVFileOpenDialog','TVChangeDirectoryDialog','TVFindDialog','IndependentHistory']){
   const historyDialog=new (kind==='IndependentHistory'?IndependentHistory:TV[kind])();manager.register('history-probe-'+kind,historyDialog);
   // Show only the owned controls; do not start MIDI preload or server search.
   TV.TVDialog.prototype.open.call(historyDialog);
   const history=historyDialog.historyButton||historyDialog.filterHistory,popup=history.window;
   popup.items=()=>Array.from({length:20},(_,index)=>({label:'History '+index,value:'History '+index}));
   const checkHistory=()=>{
    const r=history.root.getBoundingClientRect(),parts=history.iconViews;
    if(getComputedStyle(history.root).display==='grid'||parts.length!==5||history.root.children.length!==5)throw Error('History icon lost its owned text views');
    parts.forEach(part=>{const p=part.root.getBoundingClientRect(),b=part.getBounds();
     if(part.owner!==history||Math.abs(p.left-r.left-b.x1*cell.width)>1||Math.abs(p.top-r.top)>1||Math.abs(p.width-b.width*cell.width)>1||Math.abs(p.height-cell.height)>1)
      throw Error('History icon cell does not follow shared bounds');});
    const arrow=getComputedStyle(history.arrow.root),sides=parts.filter((_part,index)=>index!==2).map(part=>getComputedStyle(part.root));
    if(arrow.backgroundColor!=='rgb(0, 170, 0)'||arrow.color!=='rgb(0, 0, 0)'
     ||sides.some((style,index)=>style.backgroundColor!==(index%2?'rgb(0, 170, 0)':'rgb(170, 170, 170)')||style.backgroundImage!=='none'))throw Error('History icon lost its DOS half-cell colors');
   };
   checkHistory();const historyBounds=history.getBounds(),historyRoot=history.root;history.focus();
   history.growTo(5,2);checkHistory();history.locate(historyBounds);checkHistory();
   if(history.root!==historyRoot||document.activeElement!==historyRoot)throw Error('History resize lost its control or focus');
   history.arrow.root.click();await new Promise(requestAnimationFrame);
   if(!popup.isOpen()||history.root.getAttribute('aria-expanded')!=='true')throw Error('History did not open through TVEvent');
   assertWindowFrame(popup);
   assertBounds(popup,popup.owner);assertListLayout(popup.viewer);
   const normal=new TV.TVWindow(new TV.TVRect(1,1,21,9),'Standard window');
   const comparison=TV.TVView._fromHTML(normal.draw());popup.root.parentElement.append(comparison);normal.resolve(comparison);
   try{if(getComputedStyle(popup.root).boxShadow!==getComputedStyle(comparison).boxShadow)throw Error('History still has a private shadow instead of TVWindow drawing');}
   finally{normal.bindRoot(null);comparison.remove();}
   const trigger=history.root.getBoundingClientRect(),frame=popup.root.getBoundingClientRect();
   const x=Math.max(trigger.left,frame.left)+cell.width/2,y=Math.max(trigger.top,frame.top)+cell.height/2;
   if(x<Math.min(trigger.right,frame.right)&&y<Math.min(trigger.bottom,frame.bottom)&&!popup.root.contains(document.elementFromPoint(x,y)))
    throw Error('History trigger paints or receives input over its open popup');
   const right=popup.viewer.scrollbarWidget.axes.y.root.getBoundingClientRect(),p=popup.root.getBoundingClientRect();
   if(Math.abs(right.right-p.right)>1)throw Error('History scrollbar moved inside its frame');
   const selected=popup.viewer.selectedElement();
   if(getComputedStyle(popup.root).backgroundColor!=='rgb(0, 0, 170)'
    ||getComputedStyle(selected).backgroundColor!=='rgb(0, 170, 0)'
    ||getComputedStyle(selected).color!=='rgb(255, 255, 255)')throw Error('Shared History palette differs from DOS input/selection colors');
   const iconRoots=history.iconViews.map(view=>view.root),arrowText=history.arrow.root.firstChild,iconFocus=document.activeElement;
   const prior=TV.buildPaletteFromCurrentStyle(),edited=TV.cloneColorPalette(prior);
   TV.setColorPaletteAttribute(edited,53,0x1f);TV.setColorPaletteAttribute(edited,54,0x4a);
   TV.setColorPaletteAttribute(edited,50,0x4e);TV.setColorPaletteAttribute(edited,51,0x1f);TV.applyColorPalette(edited);await new Promise(requestAnimationFrame);
   if(getComputedStyle(popup.root).backgroundColor!=='rgb(170, 0, 0)'
    ||getComputedStyle(popup.viewer.viewport).backgroundColor!=='rgb(170, 0, 0)'
    ||getComputedStyle(selected).backgroundColor!=='rgb(0, 0, 170)')throw Error('Open History did not follow edited palette entries');
   if(history.iconViews.some((view,index)=>view.root!==iconRoots[index])||history.arrow.root.firstChild!==arrowText||document.activeElement!==iconFocus
    ||getComputedStyle(history.arrow.root).color!=='rgb(255, 255, 255)'||getComputedStyle(history.arrow.root).backgroundColor!=='rgb(0, 0, 170)'
    ||getComputedStyle(history.iconViews[0].root).backgroundColor!=='rgb(170, 0, 0)'||getComputedStyle(history.iconViews[1].root).backgroundColor!=='rgb(85, 255, 85)')throw Error('History paint depends on CSS or replaced its private views/focus');
   history.setState(TV.sfDisabled,true);if(history.arrow.getColor(1)!==history._appColor(44))throw Error('Disabled History did not use the shared disabled palette');
   history.setState(TV.sfDisabled,false);
   TV.applyColorPalette(prior);await new Promise(requestAnimationFrame);checkHistory();
   popup.viewer.selectedElement().dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
   if(popup.isOpen()||document.activeElement!==history.root)throw Error('Escape did not dismiss history/restore focus');
   history.root.click();history.focus();history.root.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
   if(popup.isOpen()||!historyDialog.isOpen())throw Error('Escape on the trigger closed the owner instead of its History');
   history.root.click();const foreignDialog=new TV.TVDialog(new TV.TVRect(0,0,24,6),'Foreign Escape');
   manager.register('history-foreign',foreignDialog);manager.open('history-foreign');
   foreignDialog.dialog.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
   if(!popup.isOpen()||foreignDialog.isOpen())throw Error('History captured Escape from another active window');
   foreignDialog.destroy();
   popup.hide();
   history.root.click();popup.closeControl.click();
   if(popup.isOpen()||document.activeElement!==history.root)throw Error('History close control did not close the popup');
   history.root.click();history.root.click();
   if(popup.isOpen())throw Error('Second History click did not close the popup');
   history.root.click();historyDialog.dialog.dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true}));
   if(popup.isOpen()||history.root.getAttribute('aria-expanded')!=='false')throw Error('Outside click did not dismiss History');
   historyDialog.destroy();host.activate('app:both');input.focus();
  }
  const editors=new TV.TVDialog(new TV.TVRect(0,0,68,20),'Editor geometry'),variants=[];
  for(const [index,[horizontal,vertical]] of [[true,true],[true,false],[false,true],[false,false]].entries()){
   const x=1+(index%2)*32,y=1+Math.floor(index/2)*8;
   const editor=new TV.TVEditor(new TV.TVRect(x,y,x+30,y+6),
    horizontal?new TV.TVScrollBar(new TV.TVRect(),TV.sbHorizontal):null,
    vertical?new TV.TVScrollBar(new TV.TVRect(),TV.sbVertical):null);
   editor.setReadOnly(false).setData('Short text');editors.insert(editor);variants.push(editor);
  }
  manager.register('editor-probe',editors);manager.open('editor-probe');await new Promise(requestAnimationFrame);
  for(const editor of variants){
   expectDOSPaint(editor.root,0x1e);expectDOSPaint(editor.textRoot,0x1e);
   const controller=editor.scrollController;
   if(controller){assertListLayout(editor);
    if(controller.axes.x&&(controller.axes.x.root.hidden||!controller.axes.x.root.classList.contains('is-disabled')))
     throw Error('Editor hid its declared scrollbar instead of disabling it');
   }else if(editor.textRoot!==editor.root||Math.abs(editor.root.clientWidth-30*cell.width)>1
    ||Math.abs(editor.root.clientHeight-6*cell.height)>1)throw Error('Unframed editor lost its full extent');
   const editorRoot=editor.root,surface=editor.textRoot;editor.focus();
   const range=document.createRange();range.setStart(surface.firstChild,1);range.setEnd(surface.firstChild,6);
   getSelection().removeAllRanges();getSelection().addRange(range);
   editor.growTo(27,5);editor.growTo(30,6);
   if(controller)assertListLayout(editor);
   if(editor.root!==editorRoot||editor.textRoot!==surface||editor.scrollController!==controller
    ||document.activeElement!==surface||getSelection().toString()!=='hort '||editor.getData()!=='Short text')
    throw Error('Editor resizing replaced its buffer, caret or scrollbars');
   editor.bindRoot(editor.root);
   if(editor.scrollController!==controller||getSelection().toString()!=='hort ')throw Error('Rebinding the same editor root lost selection');
  }
  const removedEditor=variants[0],removedRoot=removedEditor.root,removedSurface=removedEditor.textRoot;removedEditor.destroy();
  removedSurface.textContent='Stale edit';removedSurface.dispatchEvent(new InputEvent('input',{bubbles:true}));
  if(removedEditor.root||removedRoot._tvView||removedEditor.text!=='Short text')throw Error('Destroyed editor still accepted routed input');
  editors.destroy();host.activate('app:both');input.focus();
  const assertDialogFrame=dialog=>{
   const cell=TV.measureCells();
   const owner=dialog.dialog,rect=owner.getBoundingClientRect(),parts=Array.from(owner.children);
   const [top,body,bottom]=parts.map(element=>element.getBoundingClientRect());
   const close=(actual,expected)=>{if(Math.abs(actual-expected)>1)throw Error('Dialog frame left a gap between character bounds: '+actual+'/'+expected);};
   if(getComputedStyle(owner).display==='grid'||parts.some(element=>getComputedStyle(element).display==='grid'))throw Error('Dialog frame still uses CSS grid tracks');
   for(const bar of [top,bottom]){close(bar.left,rect.left);close(bar.width,rect.width);close(bar.height,cell.height);}
   close(top.top,rect.top);close(bottom.bottom,rect.bottom);close(body.top,top.bottom);close(body.bottom,bottom.top);
   for(const bar of [parts[0],parts[2]]){
    const [left,fill,right]=Array.from(bar.children).slice(0,3).map(element=>element.getBoundingClientRect());
    close(left.left,rect.left);close(left.width,cell.width);close(fill.left,left.right);close(fill.right,right.left);close(right.right,rect.right);close(right.width,cell.width);
    for(const part of Array.from(bar.children).slice(0,3)){
     if(paintedBackground(part)!==paintedBackground(bar))throw Error('Dialog frame does not show its titlebar background');
    }
   }
   if(paintedBackground(parts[1])!==paintedBackground(owner))throw Error('Dialog body does not show its owning background');
   const rows=Array.from(parts[1].children);
   for(let index=0;index+2<rows.length;index+=3){
    const [left,content,right]=rows.slice(index,index+3).map(element=>element.getBoundingClientRect());
    close(left.left,rect.left);close(left.width,cell.width);close(left.right,content.left);close(content.right,right.left);close(right.right,rect.right);
    close(left.top,content.top);close(left.height,content.height);close(right.top,content.top);close(right.height,content.height);
    if(index===0)close(content.top,body.top);
    if(index+3===rows.length)close(content.bottom,body.bottom);
    else close(content.bottom,rows[index+3].getBoundingClientRect().top);
    if(rows[index+1].classList.contains('tv-border-separator'))close(content.height,cell.height);
   }
   const caption=parts[0].querySelector('.tv-dialog-title-text');
   assertFrameTitle(caption);
   parts[0].querySelectorAll('button').forEach(assertFrameControl);
   for(const part of owner.querySelectorAll('.tv-border-corner,.tv-border-side')){
    if(['grid','inline-grid','flex','inline-flex'].includes(getComputedStyle(part).display))throw Error('Dialog frame corner/side still uses CSS layout');
   }
   if(!caption.hidden){const r=caption.getBoundingClientRect();
    close(r.top,top.top);close(r.height,cell.height);
    const column=(r.left-rect.left)/cell.width;if(Math.abs(column-Math.round(column))>0.01)throw Error('Dialog caption starts between character columns');
    for(const button of parts[0].querySelectorAll('button:not([hidden])')){const b=button.getBoundingClientRect();
     if(r.left<b.right-1&&r.right>b.left+1)throw Error('Dialog title overlaps a frame control');}
   }
  };
  for(const name of ['TVViewGalleryDialog','TVCalendarDialog','TVAsciiTableDialog','TVCalculatorDialog','TVFileOpenDialog','TVChangeDirectoryDialog','TVFindDialog','TVColorsDialog',
   'TVPuzzleDialog','TVTetrisDialog','TVMinesDialog','TVBreakOutDialog','TVSokobanDialog','TVLinesDialog','TVReversiDialog','TVLudoDialog','TVMastermindDialog','TVTronDialog','TVHanoiDialog','TVSnakeDialog']){
   const tool=new TV[name]();program.desktopView.insert(tool);tool.open();await new Promise(requestAnimationFrame);assertDialogFrame(tool);
   const rect=tool.dialog.getBoundingClientRect(),client=tool.dialog.querySelector('.tv-dialog-client').getBoundingClientRect();
   if(client.right>rect.right||client.bottom>rect.bottom)throw Error(name+' client escaped frame');
   tool.destroy();
  }
  const nativeFetch=window.fetch;
  const midiBytes=Uint8Array.from([77,84,104,100,0,0,0,6,0,0,0,1,0,96,77,84,114,107,0,0,0,13,0,144,60,100,134,0,128,60,0,0,255,47,0]);
  const cover='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="50"><rect width="40" height="50" fill="blue"/></svg>');
  const tracks=Array.from({length:7000},(_,index)=>({id:'fixture:'+index,source_id:'fixture',item_id:String(index),title:'Track '+index,game:'DOS game',available:true,file:'/fixture.mid',cover}));
  let catalogs=0;
  window.fetch=(url,options)=>{
   const path=new URL(String(url),location.href).pathname;
   if(path==='/api/midi/catalog'){catalogs++;return Promise.resolve(new Response(JSON.stringify({state:'ready',total:tracks.length,downloaded:tracks.length,tracks})));}
   if(path==='/fixture.mid')return Promise.resolve(new Response(midiBytes));
   return nativeFetch(url,options);
  };
  try{
   const player=program.dialogManager.open('midi');
   if(player.helpCtx!==2060)throw Error('Direct MIDI lost its numeric 2.1 HELP context');
   const wait=async test=>{const end=Date.now()+15000;while(!test()){if(Date.now()>end)throw Error('Direct MIDI check timed out: '+player.displayView.statusView.getText());await new Promise(resolve=>setTimeout(resolve,25));}};
   await wait(()=>player.allTracks.length===7000);player.toggleAdvanced(true);await new Promise(requestAnimationFrame);assertDialogFrame(player);
   if(player.trackListBox.itemsRoot().querySelectorAll(player.trackListBox.itemSelector()).length>60)throw Error('MIDI mounted the entire catalog');
   if(player.trackListBox.getText(0).trim()!=='01 DOS game: Track 0')throw Error('MIDI row text missing');
   const position=player.getBounds();player.toggleAdvanced(false);player.toggleAdvanced(true);
   if(player.origin.x!==position.x1||player.origin.y!==position.y1)throw Error('MIDI More moved the window');
   const started=performance.now();player.selectTrack(6999);player.trackListBox.focusSelectedItem();await new Promise(requestAnimationFrame);
   if(player.trackListBox.itemsRoot().querySelectorAll(player.trackListBox.itemSelector()).length>60||!player.trackListBox.selectedElement()?.textContent.includes('6999'))throw Error('MIDI end selection not windowed '+JSON.stringify({selected:player.trackListBox.selectedIndex,rows:player.trackListBox.itemsRoot().querySelectorAll(player.trackListBox.itemSelector()).length,text:player.trackListBox.selectedElement()?.textContent}));
   if(performance.now()-started>1500)throw Error('MIDI large list selection regressed');
   await wait(()=>player.coverView.image?.complete||player.coverView.root.querySelector('img')?.complete);
   const colors=getComputedStyle(player.displayView.titleView.root);
   if(colors.color!=='rgb(255, 255, 255)'||colors.backgroundColor!=='rgb(0, 0, 0)')throw Error('MIDI display palette differs');
   await player.playSelected();if(!player.isPlaying||!player.synth.sequence)throw Error('Direct MIDI did not start: '+player.displayView.statusView.getText());
   await new Promise(resolve=>setTimeout(resolve,500));player.pausePlayback();
   if(!player.pausedPosition||player.pausedPosition.elapsed<=0||player.isPlaying)throw Error('MIDI pause lost position');
   await player.playSelected();if(!player.isPlaying)throw Error('MIDI resume failed');
   await player.seekTo(.5);await new Promise(resolve=>setTimeout(resolve,200));
   if(player.meter.curValue<45)throw Error('MIDI seek/progress failed');
   player.stopPlayback();player.filterInput.setData('Track 6999');player.applyFilter();
   if(player.tracks.length!==1||!player.trackListBox.selectedElement()?.textContent.includes('6999'))throw Error('MIDI filter failed');
   player.rememberFilter();player.filterHistory.arrow.root.click();
   if(!player.historyWindow.isOpen())throw Error('MIDI filter history did not open');
   player.filterHistory.arrow.root.click();if(player.historyWindow.isOpen())throw Error('MIDI filter history did not close');
   player.close();if(player.isPlaying||player.synth.progressTimer!==null||player.catalogTimer!==null)throw Error('MIDI close retained work');
   player.destroy();await new Promise(resolve=>setTimeout(resolve,50));
   if(player.synth.context?.state!=='closed'||player.cache.size)throw Error('MIDI destroy retained audio/cache');
  }finally{window.fetch=nativeFetch;}
 })()`);
 if(errors.length)throw Error(errors.join('\n'));socket.close();
})().catch(error=>{console.error(error);process.exit(1);});
'''
        result = subprocess.run([NODE, "-e", script, debugging, url, str(tmp_path), shell], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
    finally:
        if chrome:
            chrome.terminate(); chrome.wait(timeout=10)
        server.terminate(); server.wait(timeout=10)
        log.close()
