from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
ASSET_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/server/converter/assets/tv-core.js"),
)
DIALOG_PATHS = (
    Path("www/assets/tv-dialogs.js"),
    Path("thelpviewer/server/converter/assets/tv-dialogs.js"),
)
GAME_PATHS = (
    Path("www/assets/tv-games.js"),
    Path("thelpviewer/server/converter/assets/tv-games.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_state_queries_require_all_requested_flags_and_accept_the_empty_mask():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const flags=[TV.sfVisible,TV.sfCursorVis,TV.sfCursorIns,TV.sfShadow,TV.sfActive,TV.sfSelected,
 TV.sfFocused,TV.sfDragging,TV.sfDisabled,TV.sfModal,TV.sfDefault,TV.sfExposed];
const view=new TV.TVView(bounds);
assert.equal(view.getState(TV.sfVisible),true);
assert.equal(view.getState(TV.sfVisible|TV.sfDisabled),false,'a partial state matched the whole query');
assert.equal(view.getState(0),true,'the empty query requires no flags');
for(const first of flags){
 for(const second of flags){
  if(first===second)continue;
  view.state=0;view.setState(first,true);
  assert.equal(view.getState(first),true);assert.equal(view.getState(second),false);
  assert.equal(view.getState(first|second),false,'one flag satisfied a two-flag query');
  view.setState(second,true);assert.equal(view.getState(first|second),true);
  view.setState(first,false);assert.equal(view.getState(first|second),false);
  assert.equal(view.getState(second),true,'query or partial clear changed an unrelated flag');
  assert.equal(view.getState(0),true);
 }
}
view.state=0;assert.equal(view.getState(0),true);assert.equal(view.getState(TV.sfVisible),false);
view.setState(TV.sfVisible|TV.sfSelected|TV.sfFocused|TV.sfShadow,true);
assert.equal(view.getState(TV.sfVisible|TV.sfSelected|TV.sfFocused),true);
assert.equal(view.getState(TV.sfVisible|TV.sfSelected|TV.sfDisabled),false);
assert.equal(view.getState(0x8000),false);assert.equal(view.getState(TV.sfVisible|0x8000),false);
const before=view.state;for(const mask of [0,TV.sfVisible,TV.sfFocused|TV.sfDisabled,0xffff])view.getState(mask);
assert.equal(view.state,before,'GetState changed the view');
for(const control of [new TV.TVGroup(bounds),new TV.TVWindow(bounds,'State'),new TV.TVInputLine(bounds),
 new TV.TVButton(bounds,'Action',1),new TV.TVListBox(bounds),new TV.TVCheckBoxes(bounds,[{label:'Choice'}])]){
 control.setState(TV.sfSelected,true);assert.equal(control.getState(TV.sfSelected|TV.sfFocused),false);
 control.setState(TV.sfFocused,true);assert.equal(control.getState(TV.sfSelected|TV.sfFocused),true);
 control.setState(TV.sfFocused,false);assert.equal(control.getState(TV.sfSelected|TV.sfFocused),false);
 assert.equal(control.getState(TV.sfSelected),true);assert.equal(control.getState(0),true);
}
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
@pytest.mark.parametrize("scenario", ["combined", "local", "callbacks"])
def test_group_state_masks_preserve_child_state_and_newer_callbacks(scenario):
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
class Tracked extends TV.TVView {
 constructor(){super(bounds);this.calls=[];}
 setState(mask,on){super.setState(mask,on);this.calls.push([mask,on]);this.changed?.(mask,on);return this;}
}
const inherited=TV.sfActive|TV.sfDragging,all=inherited|TV.sfFocused|TV.sfExposed;
if(process.argv[2]==='combined'){
 for(const Base of [TV.TVGroup,TV.TVWindow]){
  const group=new Base(bounds,'States'),panel=new TV.TVGroup(bounds),current=new Tracked(),peer=new Tracked(),other=new Tracked();
  const hidden=new TV.TVGroup(bounds),hiddenChild=new Tracked();hidden.insert(hiddenChild);hidden.hide();
  panel.insertAll([current,peer]);panel.setCurrent(current);group.insertAll([panel,other,hidden]);group.setCurrent(panel);
  group.setState(TV.sfFocused|TV.sfExposed,true);
  assert(group.getState(TV.sfFocused|TV.sfExposed));assert(current.getState(TV.sfFocused|TV.sfExposed));
  for(const view of [peer,other]){assert(view.getState(TV.sfExposed),'visible peer did not become exposed');assert(!view.getState(TV.sfFocused));}
  assert(!hidden.getState(TV.sfExposed));assert(!hiddenChild.getState(TV.sfExposed));
  group.setState(TV.sfFocused|TV.sfExposed,false);
  for(const view of [group,panel,current,peer,other,hidden,hiddenChild])assert.equal(view.state&(TV.sfFocused|TV.sfExposed),0);
  for(const view of [current,peer,other,hiddenChild])view.calls=[];
  group.setState(all,true);
  for(const view of [group,panel,current,peer,other,hidden,hiddenChild])assert(view.getState(inherited),'activity/dragging did not reach a descendant');
  assert(current.getState(TV.sfFocused));assert(!peer.getState(TV.sfFocused));assert(!other.getState(TV.sfFocused));
  assert.equal(hidden.state&(TV.sfFocused|TV.sfExposed),0);assert.equal(hiddenChild.state&(TV.sfFocused|TV.sfExposed),0);
  assert.equal(current.calls.filter(([mask])=>mask&TV.sfFocused).length,1,'current focus was delivered twice');
  for(const view of [peer,other,hiddenChild])assert.equal(view.calls.filter(([mask])=>mask&TV.sfFocused).length,0);
  group.setState(all,false);
  for(const view of [group,panel,current,peer,other,hidden,hiddenChild])assert.equal(view.state&all,0);
  assert.equal(group.current,panel);assert.equal(panel.current,current);assert(current.getState(TV.sfSelected));assert(!hidden.getState(TV.sfVisible));
 }
}
if(process.argv[2]==='local'){
 for(const local of [TV.sfVisible,TV.sfDisabled,TV.sfSelected,TV.sfShadow,TV.sfModal,TV.sfDefault,TV.sfCursorVis,TV.sfCursorIns]){
  const group=new TV.TVGroup(bounds),first=new Tracked(),second=new Tracked();
  first.setState(local,true);second.setState(local,false);group.insertAll([first,second]);group.setCurrent(first);
  const before=[first.state&local,second.state&local];
  for(const on of [true,false,true]){
   group.setState(inherited|local,on);
   assert.deepEqual([first.state&local,second.state&local],before,'owner state overwrote a child local flag '+local);
   for(const child of [first,second])assert.equal(child.state&inherited,on?inherited:0);
   assert.equal(group.getState(local),on);
  }
 }
}
if(process.argv[2]==='callbacks'){
 {
  const group=new TV.TVGroup(bounds),foreign=new TV.TVGroup(bounds),first=new Tracked(),survivor=new Tracked(),moved=new Tracked();
  group.insertAll([first,survivor,moved]);first.changed=(mask,on)=>{
   if(on&&(mask&TV.sfActive)){delete first.changed;group.remove(first);group.remove(moved);foreign.insert(moved);}
  };
  group.setState(inherited,true);
  assert(survivor.getState(inherited),'removing an earlier recipient skipped a surviving child');
  assert.equal(moved.owner,foreign);assert.equal(moved.state&inherited,0,'old owner changed a reparented child');
 }
 {
  const group=new TV.TVGroup(bounds),first=new Tracked(),last=new Tracked();group.insertAll([first,last]);group.setCurrent(first);
  first.changed=(mask,on)=>{if(on&&(mask&TV.sfActive)){delete first.changed;group.setState(TV.sfActive|TV.sfFocused|TV.sfExposed,false);}};
  group.setState(all,true);
  for(const view of [group,first,last]){
   assert.equal(view.state&(TV.sfActive|TV.sfFocused|TV.sfExposed),0,'stale propagation overrode a newer owner state');
   assert(view.getState(TV.sfDragging),'unrelated pending dragging state was lost');
  }
 }
 {
  const group=new TV.TVGroup(bounds),first=new Tracked(),last=new Tracked();group.insertAll([first,last]);group.setCurrent(first);
  first.changed=(mask,on)=>{if(on&&(mask&TV.sfFocused)){delete first.changed;last.focus();}};
  group.setState(TV.sfFocused|TV.sfExposed,true);
  assert.equal(group.current,last);assert(last.getState(TV.sfFocused|TV.sfExposed));assert(!first.getState(TV.sfFocused));
  assert(first.getState(TV.sfExposed));
  first.calls=[];last.calls=[];const before=group.state;group.setState(0,true);
  assert.equal(group.state,before);assert.equal(first.calls.length+last.calls.length,0);
 }
}
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0]), scenario], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
@pytest.mark.parametrize("kind", ["group", "window", "program"])
def test_insert_rejects_foreign_ownership_duplicates_and_cycles_before_mutation(kind):
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
if(process.argv[2]==='program'){
 const program=new TV.TVProgram(),other=new TV.TVProgram();
 for(const Base of [TV.TVMenuBar,TV.TVStatusLine,TV.TVDesktop]){
  const current=new Base(bounds),foreign=new Base(bounds);program.insert(current);other.insert(foreign);
  const slot=Base===TV.TVMenuBar?'menuBar':Base===TV.TVStatusLine?'statusLine':'desktopView';
  const before=program.children.slice();
  assert.throws(()=>program.insert(foreign),'program stole a foreign screen view');
  assert.equal(program[slot],current);assert.equal(current.owner,program);assert.equal(foreign.owner,other);
  assert.deepEqual(program.children,before);assert(other.children.includes(foreign));
  program.insert(current);assert.equal(program.children.filter(view=>view===current).length,1);
  const replacement=new Base(bounds);program.insert(replacement);
  assert.equal(program[slot],replacement);assert.equal(current.owner,null);assert.equal(replacement.owner,program);
 }
 assert.throws(()=>program.insert(program));assert.equal(program.owner,null);
}else{
 const Base=process.argv[2]==='window'?TV.TVWindow:TV.TVGroup;
 const owner=new Base(bounds,'Owner'),other=new TV.TVGroup(bounds),first=new TV.TVView(bounds),last=new TV.TVView(bounds);
 first.setHelpCtx(123);owner.insertAll([first,last]);owner.setCurrent(first);first.focus();
 const order=owner.children.slice(),state=first.state;
 for(const attempt of [()=>owner.insert(first),()=>owner.insertBefore(first,last),()=>other.insert(first),()=>other.insertBefore(first,null)]){
  assert.throws(attempt,'an owned view was inserted again');
  assert.deepEqual(owner.children,order);assert.equal(first.owner,owner);assert.equal(first.state,state);
  assert.equal(owner.current,first);assert.equal(owner.getHelpCtx(),123);assert.equal(other.children.length,0);
 }
 const candidate=new TV.TVView(bounds),foreign=new TV.TVView(bounds);other.insert(foreign);
 for(const target of [foreign,new TV.TVView(bounds),{}]){
  assert.throws(()=>owner.insertBefore(candidate,target),'a foreign target was silently treated as append');
  assert.equal(candidate.owner,null);assert.deepEqual(owner.children,order);
 }
 assert.throws(()=>owner.insert(owner));assert.equal(owner.owner,null);
 const nested=new TV.TVGroup(bounds);owner.insert(nested);
 assert.throws(()=>nested.insert(owner));assert.equal(owner.owner,null);assert.equal(nested.owner,owner);assert.equal(nested.children.length,0);
 const before=new TV.TVView(bounds),tail=new TV.TVView(bounds);owner.insertBefore(before,last);owner.insertBefore(tail,null);
 assert.deepEqual(owner.children,[first,before,last,nested,tail]);assert.equal(before.owner,owner);assert.equal(tail.owner,owner);
 assert.equal(owner.remove(first),first);assert.equal(owner.current,null);assert.equal(first.owner,null);
 other.insert(first);assert.equal(first.owner,other);assert(!owner.children.includes(first));assert.equal(other.children.filter(view=>view===first).length,1);
 assert.throws(()=>owner.insert(null),TypeError);assert.throws(()=>owner.insertBefore({},last),TypeError);
}
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0]), kind], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
@pytest.mark.parametrize("scenario", ["guards", "top", "callbacks"])
def test_view_select_uses_owned_selection_and_top_select_without_stale_state(scenario):
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const child=()=>{const view=new TV.TVView(bounds);view.options|=TV.ofSelectable;return view;};
if(process.argv[2]==='guards'){
 const unowned=child(),unownedState=unowned.state;assert.equal(unowned.select(),unowned);assert.equal(unowned.state,unownedState);
 const owner=new TV.TVGroup(bounds),first=child(),next=child(),decoration=new TV.TVStaticText(bounds,'Caption');
 owner.insertAll([first,next,decoration]);first.select();assert.equal(owner.current,first);const order=owner.children.slice(),state=decoration.state;
 assert.equal(decoration.select(),decoration);assert.equal(owner.current,first);assert.equal(decoration.state,state);
 next.select();assert.equal(owner.current,next);assert(next.getState(TV.sfSelected));assert(!first.getState(TV.sfSelected));
 assert(!next.getState(TV.sfFocused),'Select forced browser focus');assert.deepEqual(owner.children,order);
 first.select();next.options&=~TV.ofSelectable;next.select();assert.equal(owner.current,first);assert(!next.getState(TV.sfSelected));
 owner.remove(next);next.options|=TV.ofSelectable;next.select();assert.equal(next.owner,null);assert(!next.getState(TV.sfSelected));
 const panel=new TV.TVGroup(bounds),field=child();panel.insert(field);field.select();owner.insert(panel);panel.select();
 assert.equal(owner.current,panel);assert.equal(panel.current,field);assert(!field.getState(TV.sfFocused));
}
if(process.argv[2]==='top'){
 for(const Base of [TV.TVGroup,TV.TVWindow,TV.TVDesktop]){
  const owner=new Base(bounds,'Select'),first=child(),raised=child(),last=child();raised.options|=TV.ofTopSelect;
  owner.insertAll([first,raised,last]);first.select();assert.equal(owner.current,first);
  assert.equal(raised.select(),raised);assert.deepEqual(owner.children,[first,last,raised]);assert.equal(owner.current,raised);
  assert(raised.getState(TV.sfSelected));assert(!first.getState(TV.sfSelected));assert(!raised.getState(TV.sfFocused));
  raised.select();assert.deepEqual(owner.children,[first,last,raised]);assert.equal(owner.current,raised);
  last.select();assert.equal(owner.current,last);assert.deepEqual(owner.children,[first,last,raised],'ordinary Select reordered children');
  raised.putInFrontOf(null);raised.hide();raised.select();assert.deepEqual(owner.children,[first,last,raised]);assert.equal(owner.current,last);assert(!raised.getState(TV.sfSelected));
 }
}
if(process.argv[2]==='callbacks'){
 const owner=new TV.TVGroup(bounds),first=child(),requested=child(),newer=child();owner.insertAll([first,requested,newer]);first.select();
 const base=first.setState.bind(first);let redirect=true;first.setState=(mask,on)=>{base(mask,on);
  if(redirect&&!on&&(mask&TV.sfSelected)){redirect=false;newer.select();}return first;};
 requested.select();assert.equal(owner.current,newer);assert(newer.getState(TV.sfSelected));assert(!requested.getState(TV.sfSelected),'stale Select reselected its abandoned target');
 first.setState=base;first.select();const foreign=new TV.TVGroup(bounds),peer=child();foreign.insert(peer);peer.select();
 first.setState=(mask,on)=>{base(mask,on);if(!on&&(mask&TV.sfSelected)){owner.remove(requested);foreign.insert(requested);}return first;};
 requested.select();assert.equal(requested.owner,foreign);assert.equal(foreign.current,peer);assert(!requested.getState(TV.sfSelected),'Select changed a reparented target');
 first.setState=base;first.select();const top=child();top.options|=TV.ofTopSelect;owner.insertBefore(top,first);
 const make=top.makeFirst.bind(top);top.makeFirst=()=>{make();newer.select();return top;};top.select();
 assert.equal(owner.current,newer);assert(!top.getState(TV.sfSelected),'TopSelect overwrote newer selection');
 first.select();const outside=child();top.putInFrontOf(null);top.makeFirst=()=>{make();outside.focus();return top;};top.select();
 assert.equal(owner.current,first);assert(outside.getState(TV.sfFocused));assert(!top.getState(TV.sfSelected),'TopSelect overwrote newer focus');
 top.makeFirst=()=>{make();owner.remove(top);return top;};top.select();assert.equal(top.owner,null);assert(!top.getState(TV.sfSelected));
}
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0]), scenario], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
@pytest.mark.parametrize("kind", ["group", "window", "desktop"])
def test_sibling_navigation_stops_at_boundaries_and_follows_live_owner_order(kind):
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const Base={group:TV.TVGroup,window:TV.TVWindow,desktop:TV.TVDesktop}[process.argv[2]],owner=new Base(bounds,'Siblings');
const first=new TV.TVView(bounds),current=new TV.TVInputLine(bounds,20),nested=new TV.TVGroup(bounds),last=new TV.TVView(bounds);
const inner=new TV.TVView(bounds);nested.insert(inner);
assert.equal(first.nextView(),null);assert.equal(first.prevView(),null);
owner.insert(first);assert.equal(first.nextView(),null);assert.equal(first.prevView(),null);
owner.insertAll([current,nested,last]);owner.setCurrent(current);current.setHelpCtx(123);current.setData('Unchanged');current.setState(TV.sfFocused,true);
nested.hide();last.setState(TV.sfDisabled,true);
const states=[first,current,nested,last].map(view=>view.state);
function check(expected){
 let view=expected[0],forward=[],backward=[];
 while(view&&forward.length<=expected.length){forward.push(view);view=view.nextView();}
 assert.equal(view,null,'NextView wrapped instead of terminating');assert.deepEqual(forward,expected);
 view=expected.at(-1);while(view&&backward.length<=expected.length){backward.push(view);view=view.prevView();}
 assert.equal(view,null,'PrevView wrapped instead of terminating');assert.deepEqual(backward,expected.slice().reverse());
 assert.equal(owner.current,current);assert.equal(owner.getHelpCtx(),123);assert.equal(current.getData(),'Unchanged');
 [first,current,nested,last].forEach((view,index)=>{assert.equal(view.state,states[index]);assert.equal(view.owner,owner);});
 assert.equal(inner.nextView(),null);assert.equal(inner.prevView(),null);
}
check([first,current,nested,last]);first.makeFirst();check([current,nested,last,first]);
first.putInFrontOf(null);check([first,current,nested,last]);last.putInFrontOf(current);check([first,current,last,nested]);
owner.remove(first);assert.equal(first.nextView(),null);assert.equal(first.prevView(),null);
assert.equal(current.prevView(),null);assert.equal(nested.nextView(),null);
const other=new TV.TVGroup(bounds),peer=new TV.TVView(bounds);other.insertAll([peer,first]);
assert.equal(first.prevView(),peer);assert.equal(first.nextView(),null);assert.equal(peer.prevView(),null);assert.equal(peer.nextView(),first);
assert.equal(owner.children.includes(first),false);assert.equal(owner.current,current);
const unowned=new TV.TVView(bounds);assert.equal(unowned.nextView(),null);assert.equal(unowned.prevView(),null);
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0]), kind], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
@pytest.mark.parametrize("kind", ["group", "window", "desktop"])
def test_reordering_preserves_ownership_current_state_and_handles_boundaries(kind):
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const Base={group:TV.TVGroup,window:TV.TVWindow,desktop:TV.TVDesktop}[process.argv[2]],owner=new Base(bounds,'Order');
const views=Array.from({length:4},()=>new TV.TVView(bounds)),[a,b,c,d]=views;
owner.insertAll(views);owner.setCurrent(b);b.setHelpCtx(123);b.setState(TV.sfFocused,true);
const states=views.map(view=>view.state),array=owner.children;
owner.insert=owner.insertBefore=owner.remove=()=>{throw Error('Reorder transferred ownership');};
function check(expected){
 assert.equal(owner.children,array,'reorder replaced the owned collection');assert.deepEqual(owner.children,expected);
 assert.equal(owner.current,b);assert.equal(owner.getHelpCtx(),123);
 views.forEach((view,index)=>{assert.equal(view.owner,owner);assert.equal(view.state,states[index]);});
}
assert.equal(a.makeFirst(),a);check([b,c,d,a]);assert.equal(a.makeFirst(),a);check([b,c,d,a]);
assert.equal(b.putInFrontOf(c),b);check([c,b,d,a]);b.putInFrontOf(c);check([c,b,d,a]);
a.putInFrontOf(c);check([c,a,b,d]);b.putInFrontOf(null);check([b,c,a,d]);
d.putInFrontOf();check([d,b,c,a]);d.makeFirst();check([b,c,a,d]);
const foreign=new TV.TVGroup(bounds),other=new TV.TVView(bounds),unowned=new TV.TVView(bounds);foreign.insert(other);
for(const target of [b,other,unowned,{},null]){
 b.putInFrontOf(target);check([b,c,a,d]);
}
assert.equal(unowned.makeFirst(),unowned);assert.equal(unowned.putInFrontOf(a),unowned);
assert.equal(unowned.owner,null);check([b,c,a,d]);
const single=new TV.TVGroup(bounds),only=new TV.TVView(bounds);single.insert(only);single.setCurrent(only);
only.makeFirst();only.putInFrontOf(null);only.putInFrontOf(only);assert.deepEqual(single.children,[only]);assert.equal(single.current,only);
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0]), kind], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_remove_releases_ownership_after_callback_errors_and_restores_default_buttons():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const owner=new TV.TVGroup(bounds),other=new TV.TVGroup(bounds),view=new TV.TVView(bounds),survivor=new TV.TVView(bounds);
owner.insertAll([view,survivor]);owner.setCurrent(view);view.setState(TV.sfFocused,true);
const set=view.setState.bind(view);view.setState=(mask,on)=>{set(mask,on);if(!on&&(mask&TV.sfFocused))throw Error('Controlled release failure');return view;};
assert.throws(()=>owner.remove(view),/Controlled release failure/);
assert.equal(owner.current,null);assert.deepEqual(owner.children,[survivor]);assert.equal(view.owner,null);
assert.equal(view.state&(TV.sfFocused|TV.sfSelected),0);other.insert(view);assert.equal(view.owner,other);
const primary=new TV.TVButton(bounds,'Default',1,TV.bfDefault),temporary=new TV.TVButton(bounds,'Temporary',2);
owner.insertAll([primary,temporary]);owner.setCurrent(temporary);temporary.setState(TV.sfFocused,true);
assert.equal(primary.amDefault,false);assert.equal(temporary.amDefault,true);
owner.remove(temporary);assert.equal(primary.amDefault,true);assert.equal(temporary.amDefault,false);assert.equal(temporary.owner,null);
const old=new TV.TVView(bounds);owner.insert(old);owner.setCurrent(old);
const base=old.setState.bind(old);old.setState=(mask,on)=>{base(mask,on);if(!on&&(mask&TV.sfFocused))survivor.focus();return old;};
owner.remove(old);assert.equal(old.owner,null);assert.equal(owner.current,survivor);assert(survivor.getState(TV.sfFocused|TV.sfSelected));
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_dialog_mnemonics_use_enabled_owned_controls_only():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV;
function bind(view){
 view.root={hidden:false,disabled:false,contains(){return true;},appendChild(){},classList:{toggle(){}},setAttribute(){},
  focus(){document.activeElement=this;}};
 return view;
}
function state(view,flag,on){TV.TVView.prototype.setState.call(view,flag,on);}
function alt(group,key,extra={}){
 const native={key,altKey:true,ctrlKey:false,metaKey:false,target:group.root,defaultPrevented:false,
  preventDefault(){this.defaultPrevented=true;},...extra};
 const event=new TV.TVEvent(TV.evKeyDown,{nativeEvent:native});group.dispatchEvent(event);return event;
}
const group=bind(new TV.TVGroup(new TV.TVRect())), commands=[];
group.handleEvent=function(event){TV.TVGroup.prototype.handleEvent.call(this,event);
 if(event.what===TV.evCommand){commands.push([event.command,event.infoPtr]);this.clearEvent(event);}};
const input=bind(new TV.TVInputLine(new TV.TVRect(),30));
const label=bind(new TV.TVLabel(new TV.TVRect(),'~N~ame',input));group.insertAll([label,input]);
assert.equal(alt(group,'n').what,TV.evNothing);assert.equal(document.activeElement,input.root);
state(label,TV.sfVisible,false);document.activeElement=null;
assert.equal(alt(group,'n').what,TV.evKeyDown,'hidden label consumed its mnemonic');
assert.equal(document.activeElement,null);state(label,TV.sfVisible,true);
state(input,TV.sfDisabled,true);
assert.equal(alt(group,'n').what,TV.evKeyDown);state(input,TV.sfDisabled,false);
const button=bind(new TV.TVButton(new TV.TVRect(),'~S~ave','save'));
group.insert(button);alt(group,'s');
assert.deepEqual(commands,[['save',button]],'Alt did not activate its owned button once');
for(const [view,flag] of [[button,TV.sfVisible],[button,TV.sfDisabled],[group,TV.sfVisible],[group,TV.sfDisabled]]){
 state(view,flag,flag===TV.sfDisabled);const count=commands.length;
 assert.equal(button.press(),false,'hidden/disabled hierarchy accepted a button press');
 alt(group,'s');assert.equal(commands.length,count);state(view,flag,flag!==TV.sfDisabled);
}
const panel=bind(new TV.TVGroup(new TV.TVRect()));group.insert(panel);
const nested=bind(new TV.TVButton(new TV.TVRect(),'~S~ave nested','nested'));panel.insert(nested);
state(button,TV.sfVisible,false);state(panel,TV.sfVisible,false);const before=commands.length;
alt(group,'s');assert.equal(commands.length,before,'hidden nested group supplied a mnemonic');
state(panel,TV.sfVisible,true);alt(group,'s');assert.equal(commands.at(-1)[0],'nested');
state(button,TV.sfVisible,true);
const prevented=alt(group,'s',{defaultPrevented:true});
assert.equal(prevented.what,TV.evKeyDown);assert.equal(commands.at(-1)[0],'nested');
for(const modifier of ['ctrlKey','metaKey']){alt(group,'s',{[modifier]:true});assert.equal(commands.at(-1)[0],'nested');}
const program=bind(new TV.TVProgram()),desktop=bind(new TV.TVDesktop(new TV.TVRect()));program.insert(desktop);
const foreign=bind(new TV.TVGroup(new TV.TVRect())),field=bind(new TV.TVInputLine(new TV.TVRect(),30));
foreign.insertAll([bind(new TV.TVLabel(new TV.TVRect(),'~Z~ Other window',field)),field]);desktop.insert(foreign);
document.activeElement=null;alt(program,'z');
assert.equal(document.activeElement,null,'program mnemonic search reached a different window');
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_group_focus_navigation_starts_at_the_correct_end_and_checks_owners():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV;
function view(){
 const item=new TV.TVView(new TV.TVRect());item.options|=TV.ofSelectable;
 item.root={hidden:false,disabled:false,tabIndex:0,classList:{toggle(){}},setAttribute(){},focus(){document.activeElement=this;}};
 return item;
}
const outer=new TV.TVGroup(new TV.TVRect()),group=new TV.TVGroup(new TV.TVRect());outer.insert(group);
const first=view(),disabled=view(),last=view();group.insertAll([first,disabled,last]);disabled.setState(TV.sfDisabled,true);
assert.equal(group.focusNext(false),true);assert.equal(group.current,last,'backward navigation without current must choose the last item');
assert.equal(document.activeElement,last.root);assert.equal(last.getState(TV.sfSelected|TV.sfFocused),true);
group.selectNext(false);assert.equal(group.current,first);assert.equal(last.state&(TV.sfSelected|TV.sfFocused),0);
group.selectNext(false);assert.equal(group.current,last);
group.setCurrent(null);group.selectNext();assert.equal(group.current,first);
last.setState(TV.sfVisible,false);group.setCurrent(last);group.selectNext(false);assert.equal(group.current,first);
last.show();first.root.disabled=true;group.selectNext();assert.equal(group.current,last);first.root.disabled=false;
for(const flag of [TV.sfVisible,TV.sfDisabled]){
 outer.setState(flag,flag===TV.sfDisabled);const selected=group.current,focus=document.activeElement;
 assert.equal(group.focusNext(),false,'unavailable owner allowed navigation');
 assert.equal(group.current,selected);assert.equal(document.activeElement,focus);outer.setState(flag,flag!==TV.sfDisabled);
}
first.hide();last.hide();assert.equal(group.selectNext(false),false);
first.show();last.show();group.remove(first);group.remove(disabled);group.remove(last);
const layout=new TV.TVGroup(new TV.TVRect()),a=view(),b=view(),unselected=view();
const controls=[new TV.TVInputLine(new TV.TVRect()),new TV.TVEditor(new TV.TVRect()),new TV.TVListBox(new TV.TVRect()),
 new TV.TVButton(new TV.TVRect(),'Button',1),new TV.TVCheckBoxes(new TV.TVRect(),[{label:'Choice'}])];
assert(controls.every(view=>typeof view.options==='number'&&(view.options&TV.ofSelectable)!==0));
assert.equal(controls.at(-1).strings[0].label,'Choice');
const scroll=new TV.TVScrollBar(new TV.TVRect(),TV.sbVertical);assert.equal(scroll.options&TV.ofSelectable,0);
group.insert(scroll);
unselected.options&=~TV.ofSelectable;layout.insertAll([a,unselected,b]);group.insertAll([layout,last]);
a.focus();assert.equal(group.current,layout);assert.equal(layout.current,a);
assert.equal(group.findNext(),b);assert.equal(group.current,layout);assert.equal(layout.current,a,'FindNext mutated selection');
group.focusNext();assert.equal(layout.current,b);group.focusNext();assert.equal(group.current,last);
group.focusNext();assert.equal(layout.current,a);group.focusNext(false);assert.equal(group.current,last);
layout.hide();assert.equal(group.findNext(),last);layout.show();b.root.tabIndex=-1;
a.focus();assert.equal(group.findNext(),last,'negative native Tab entry was selected');b.root.tabIndex=0;
let redirect=true;const setState=a.setState.bind(a);a.setState=(mask,enable)=>{setState(mask,enable);
 if(redirect&&!enable&&(mask&TV.sfFocused)){redirect=false;last.focus();}return a;};
group.focusNext();assert.equal(group.current,last);assert.equal(document.activeElement,last.root,'FocusNext overwrote a newer callback focus');
assert.equal(b.getState(TV.sfFocused),false);layout.hide();last.hide();assert.equal(group.findNext(),null);
const receiver=new TV.TVView(new TV.TVRect()),key={key:'Tab',type:'keydown',defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}};
receiver.dispatchEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:key}));assert.equal(key.defaultPrevented,false);
receiver.handleEvent=event=>receiver.clearEvent(event);
receiver.dispatchEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:key}));assert.equal(key.defaultPrevented,true,'consumed Tab retained native browser navigation');
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_native_focus_tracks_owned_current_paths_and_preserves_newer_selection():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
function bind(view,parent=null){
 const listeners=new Map(),root={nodeType:1,parentElement:parent,hidden:false,disabled:false,isConnected:true,tabIndex:0,style:{},
  classList:{toggle(){}},setAttribute(){},removeAttribute(){},getAttribute(){return null;},focus(){document.activeElement=this;},
  contains(node){for(;node;node=node.parentElement)if(node===this)return true;return false;},
  addEventListener(type,handler){listeners.set(type,handler);},removeEventListener(type,handler){if(listeners.get(type)===handler)listeners.delete(type);}};
 root.listeners=listeners;view.bindRoot(root);return view;
}
const desktop=new TV.TVDesktop(bounds),scope=bind(new TV.TVGroup(bounds));desktop.insert(scope);scope.setHelpCtx(2000);
const left=bind(new TV.TVGroup(bounds),scope.root),right=bind(new TV.TVGroup(bounds),scope.root);scope.insertAll([left,right]);
const first=bind(new TV.TVView(bounds),left.root),next=bind(new TV.TVView(bounds),left.root),last=bind(new TV.TVView(bounds),right.root);
left.insertAll([first,next]);right.insert(last);first.setHelpCtx(1001);last.setHelpCtx(1002);
first.root.focus();scope._onGroupFocus({type:'focusin',target:first.root});
assert.equal(scope.current,left);assert.equal(left.current,first);assert.equal(first.getState(TV.sfFocused),true);assert.equal(scope.getHelpCtx(),1001);
assert.equal(left.getState(TV.sfSelected),true);assert.equal(first.getState(TV.sfSelected),true);
scope._onGroupFocus({type:'focusout',target:first.root,relatedTarget:last.root});last.root.focus();scope._onGroupFocus({type:'focusin',target:last.root});
assert.equal(scope.current,right);assert.equal(right.current,last);assert.equal(first.getState(TV.sfFocused),false);assert.equal(left.getState(TV.sfFocused),false);
assert.equal(left.current,first,'leaving a group discarded its remembered child');assert.equal(scope.getHelpCtx(),1002);
const outside={nodeType:1,parentElement:null};document.activeElement=last.root;
scope._onGroupFocus({type:'focusout',target:last.root,relatedTarget:outside});
assert.equal(scope.getState(TV.sfFocused),false);assert.equal(last.getState(TV.sfFocused),false);assert.equal(right.current,last);
scope.root.focus();scope._onGroupFocus({type:'focusin',target:scope.root});
assert.equal(scope.getState(TV.sfFocused),true);assert.equal(last.getState(TV.sfFocused),false,'frame focus falsely focused its remembered child');
first.focus();assert.equal(scope.current,left);assert.equal(left.current,first);assert.equal(first.getState(TV.sfFocused),true);
right.setState(TV.sfDisabled,true);last.focus();assert.equal(document.activeElement,first.root);assert.equal(scope.current,left);right.setState(TV.sfDisabled,false);
let redirect=true;const setState=first.setState.bind(first);
first.setState=(state,enable)=>{setState(state,enable);if(redirect&&!enable&&(state&TV.sfFocused)){redirect=false;last.focus();}return first;};
next.focus();assert.equal(document.activeElement,last.root);assert.equal(scope.current,right);assert.equal(right.current,last);
assert.equal(last.getState(TV.sfFocused),true);assert.equal(next.getState(TV.sfFocused),false,'stale focus replayed after a callback redirect');
first.focus();left.remove(first);assert.equal(left.current,null);assert.equal(first.owner,null);assert.equal(first.state&(TV.sfSelected|TV.sfFocused),0);
assert.equal(scope.getHelpCtx(),2000,'removed current child supplied help context');
const root=scope.root;scope.bindRoot(root);assert.equal(root.listeners.size,2);scope.bindRoot(null);
assert.equal(root.listeners.size,0);assert.equal(root._tvView,undefined);assert.equal(scope.getState(TV.sfFocused),false);
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_window_close_command_respects_the_frame_flag():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV,view=new TV.TVWindow(new TV.TVRect(),'Close flags');let closed=0;
view.closeAction=()=>closed++;view.flags&=~TV.wfClose;
const blocked=new TV.TVEvent(TV.evCommand,{command:'window-close'});view.handleEvent(blocked);
assert.equal(closed,0,'window close bypassed wfClose');assert.equal(blocked.what,TV.evNothing);
view.flags|=TV.wfClose;view.handleEvent(new TV.TVEvent(TV.evCommand,{command:'window-close'}));
assert.equal(closed,1);
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_button_broadcast_stays_in_its_owner_and_reaches_each_subscriber_once():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const records=[],commands=[];
class Group extends TV.TVGroup{
 constructor(name){super(bounds);this.name=name;}
 handleEvent(event){super.handleEvent(event);
  if(event.what===TV.evBroadcast){records.push([this.name,event.command,event.infoPtr,event.infoLong,event.nativeEvent]);this.clearEvent(event);}
  else if(event.what===TV.evCommand){commands.push([this.name,event.command,event.infoPtr]);}}
}
class Listener extends TV.TVView{
 constructor(name,consume=false){super(bounds);this.name=name;this.consume=consume;this.eventMask|=TV.evBroadcast;}
 handleEvent(event){if(event.what===TV.evBroadcast){records.push([this.name,event.command,event.infoPtr,event.infoLong,event.nativeEvent]);if(this.consume)this.clearEvent(event);}}
}
const outer=new Group('outer'),owner=new Group('owner'),nested=new Group('nested');outer.insert(owner);
const button=new TV.TVButton(bounds,'~B~roadcast','changed',TV.bfBroadcast),normal=new TV.TVButton(bounds,'Normal','normal');
const first=new Listener('first',true),last=new Listener('last'),quiet=new Listener('quiet');quiet.eventMask&=~TV.evBroadcast;
nested.insertAll([first,quiet,last]);owner.insertAll([button,normal,nested]);
const ignored=new Group('ignored');ignored.eventMask&=~TV.evBroadcast;ignored.insert(new Listener('ignored-child'));owner.insert(ignored);
const native={type:'click',defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}};
assert.equal(button.press(native),true);
assert.deepEqual(records.map(record=>record[0]),['first','last','nested','owner'],'broadcast mode did not notify its local owner tree once');
assert(records.every(record=>record[1]==='changed'&&record[2]===button&&record[4]===native));assert.equal(commands.length,0);
records.length=0;normal.press();assert.deepEqual(commands.map(record=>record[0]),['owner','outer']);assert.equal(records.length,0);
const click=new TV.TVEvent(TV.evMouseDown,{infoPtr:button,nativeEvent:native});button.dispatchEvent(click);
assert.equal(click.what,TV.evNothing);assert.deepEqual(records.map(record=>record[0]),['first','last','nested','owner']);assert.equal(commands.length,2);
records.length=0;
const key={key:'b',altKey:true,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}};
button.handleEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:key}));assert.equal(key.defaultPrevented,true);
assert.deepEqual(records.map(record=>record[0]),['first','last','nested','owner']);
owner.setState(TV.sfDisabled,true);records.length=0;assert.equal(button.press(),false);assert.equal(records.length,0);
owner.broadcast('model-update',button,17);
assert.deepEqual(records.map(record=>record[0]),['first','last','nested','owner']);assert(records.every(record=>record[3]===17));
owner.setState(TV.sfDisabled,false);records.length=0;
const origin=new TV.TVView(bounds);origin.eventMask|=TV.evBroadcast;owner.insert(origin);
origin.dispatchEvent(new TV.TVEvent(TV.evBroadcast,{command:'native-edit',infoPtr:origin}));
assert.deepEqual(records.map(record=>record[0]),['owner'],'upward input notification was rebroadcast into sibling controls');
owner.remove(button);assert.equal(button.press(),false);
records.length=0;const firstHandler=first.handleEvent.bind(first);
first.handleEvent=event=>{firstHandler(event);nested.remove(last);};
owner.broadcast('removal',owner);
assert.deepEqual(records.map(record=>record[0]),['first','nested','owner'],'broadcast delivered to a removed subscriber');
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_button_commands_keep_their_numeric_identity_and_zero_is_inert():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const owner=new TV.TVGroup(bounds),records=[];
owner.handleEvent=event=>{if([TV.evCommand,TV.evBroadcast].includes(event.what)){
 records.push([event.what,event.command,event.infoPtr,event.nativeEvent]);owner.clearEvent(event);}};
for(const command of [TV.cmCut,TV.cmCopy,TV.cmPaste,0xffff,'app:probe:run']){
 for(const flags of [TV.bfNormal,TV.bfBroadcast]){
  const button=new TV.TVButton(bounds,'~R~un',command,flags);owner.insert(button);
  const what=flags===TV.bfBroadcast?TV.evBroadcast:TV.evCommand;
  assert.equal(button.command,command,'button converted its command before dispatch');
  const native={type:'click',preventDefault(){this.defaultPrevented=true;}};
  assert.equal(button.press(native),true);
  assert.deepEqual(records.pop(),[what,command,button,native]);
  button.dispatchEvent(new TV.TVEvent(TV.evMouseDown,{infoPtr:button,nativeEvent:native}));
  assert.deepEqual(records.pop(),[what,command,button,native]);
  const key={key:'r',altKey:true,preventDefault(){this.defaultPrevented=true;}};
  button.dispatchEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:key}));
  assert.deepEqual(records.pop(),[what,command,button,key]);assert.equal(key.defaultPrevented,true);
  owner.remove(button);
 }
}
for(const command of [0,'',null,undefined]){
 for(const flags of [TV.bfNormal,TV.bfBroadcast]){
  const button=new TV.TVButton(bounds,'~R~un',command,flags);owner.insert(button);
  assert.equal(button.press(),false,'empty command activated a button');
  const native={key:'r',altKey:true,preventDefault(){this.defaultPrevented=true;}};
  button.dispatchEvent(new TV.TVEvent(TV.evMouseDown,{infoPtr:button,nativeEvent:native}));
  button.dispatchEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:native}));
  assert.equal(records.length,0,'empty command escaped to its owner');
  if(command===0)assert.equal(button.command,0,'zero command changed type');
  owner.remove(button);
 }
}
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_command_sets_update_controls_and_restore_exact_independent_snapshots():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const group=new TV.TVGroup(bounds),commands=[],signals=[];
const base=group.handleEvent.bind(group);group.handleEvent=event=>{base(event);
 if(event.what===TV.evCommand){commands.push(event.command);group.clearEvent(event);}
 if(event.what===TV.evBroadcast&&event.command===TV.cmCommandSetChanged)signals.push(event.command);};
const original=group.getCommands(),set=new TV.TVCommandSet();
assert.equal(set.isEmpty(),true);set.enableCmd(21).enableCmd('app:probe:run');
assert.equal(set.has(21),true);assert.equal(set.has('21'),false);assert.equal(set.has('app:probe:run'),true);
const clone=new TV.TVCommandSet(set);clone.disableCmd(21);assert.equal(set.has(21),true);
group.setCommands(set);set.enableCmd(0xffff);
assert.equal(group.commandEnabled(21),true);assert.equal(group.commandEnabled(0xffff),false,'setCommands retained the caller set');
assert.equal(group.commandEnabled('never-seen'),false,'setCommands did not replace the full set');
group.enableCommands([0xffff,'extra']);group.disableCommands(new TV.TVCommandSet([21,'extra']));
assert.equal(group.commandEnabled(21),false);assert.equal(group.commandEnabled(0xffff),true);assert.equal(group.commandEnabled('extra'),false);
group.setCommands(original);assert.equal(group.commandEnabled('never-seen'),true,'snapshot lost initially enabled unknown commands');
assert.equal(original.has(21),true);assert.equal(original.has(0xffff),true);
group.disableCommands(original);assert.equal(group.getCommands().isEmpty(),true);
assert.equal(group.commandEnabled('never-seen'),false);group.enableCommands(original);
const allExceptCopy=new TV.TVCommandSet(original).disableCmd(21);group.disableCommands(allExceptCopy);
assert.equal(group.commandEnabled(21),true);assert.equal(group.commandEnabled('21'),false);assert.equal(group.commandEnabled(0xffff),false);
group.enableCommands(allExceptCopy);assert.equal(group.commandEnabled('never-seen'),true);
const button=new TV.TVButton(bounds,'~R~un',21),local=new TV.TVButton(bounds,'Local',21);
local.setState(TV.sfDisabled,true);group.insertAll([button,local]);
const item=new TV.TVMenuItem('Run',21),menu=new TV.TVMenuBar(bounds,new TV.TVMenu(item));group.insert(menu);
const statusItem=new TV.TVStatusItem('F4 Run',TV.kbF4,21),line=new TV.TVStatusLine(bounds,new TV.TVStatusDef(0,65535,[statusItem]));group.insert(line);
signals.length=0;group.disableCommands(21);assert.equal(signals.length,1,'change did not notify the owner tree once');
assert.equal(button.disabled,true,'command change did not disable its button');assert.equal(button.getState(TV.sfDisabled),true);
assert.equal(button.press(),false);assert.equal(menu.activateItem(item),false);
const event=new TV.TVEvent(TV.evKeyDown,{nativeEvent:{key:'F4'}});line.handleEvent(event);assert.equal(event.what,TV.evKeyDown);
const click=new TV.TVEvent(TV.evMouseDown,{infoPtr:statusItem,nativeEvent:{preventDefault(){}}});line.dispatchEvent(click);assert.equal(commands.length,0);
group.disableCommands(21);assert.equal(signals.length,1,'unchanged set emitted another notification');
const late=new TV.TVButton(bounds,'Late',21);assert.equal(late.disabled,true,'new button ignored the current command set');group.insert(late);
group.enableCommands(21);assert.equal(button.disabled,false);assert.equal(local.disabled,true,'command enable erased local sfDisabled');assert.equal(late.disabled,false);
assert.equal(item.disabled,false,'global state overwrote the menu item flag');assert.equal(statusItem.disabled,false);
assert.equal(button.press(),true);assert.equal(menu.activateItem(item),true);
const enabled=new TV.TVEvent(TV.evKeyDown,{nativeEvent:{key:'F4',preventDefault(){}}});line.dispatchEvent(enabled);
assert.deepEqual(commands,[21,21,21]);
const saved=group.getCommands();group.disableCommands([0xffff,'app:probe:run']);
assert.equal(saved.has(0xffff),true);assert.equal(saved.has('app:probe:run'),true,'snapshot mutated with live state');group.setCommands(saved);
let once=true;const observer=new TV.TVView(bounds);observer.eventMask|=TV.evBroadcast;
observer.handleEvent=event=>{if(once&&event.command===TV.cmCommandSetChanged){once=false;group.enableCommands(21);}};
group.insertBefore(observer,button);group.disableCommands(21);
assert.equal(button.disabled,false,'stale command notification overwrote a callback change');assert.equal(button.press(),true);
group.setCommands(original);
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_first_click_selects_managed_windows_and_protects_modal_or_newer_focus():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const listeners=new Map(),add=(type,fn)=>{if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);};
const remove=(type,fn)=>listeners.get(type)?.delete(fn);
global.window={addEventListener:add,removeEventListener:remove,setTimeout(){return 1;},clearTimeout(){}};
global.document={addEventListener:add,removeEventListener:remove,activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const initialListeners=new Map([...listeners].map(([type,set])=>[type,new Set(set)]));
const root=(parentElement=null)=>({nodeType:1,parentElement,isConnected:true,hidden:false,querySelector(){return null;},classList:{toggle(){}},setAttribute(){},
 addEventListener:add,removeEventListener:remove,contains(node){for(;node;node=node.parentElement)if(node===this)return true;return false;}});
const desktop=new TV.TVDesktop(bounds);desktop.root=root();const manager=new TV.TVDialogManager(desktop);
manager.applyAllZIndices=manager.applyActiveStates=manager._focusTarget=()=>{};
const view=new TV.TVWindow(bounds,'Target'),other=new TV.TVWindow(bounds,'Other');
view.root=root(desktop.root);view.root._tvView=view;other.root=root(desktop.root);other.root._tvView=other;
manager.registerWindow('target',view.root);manager.registerWindow('other',other.root);
const leaf=root(view.root),mouse=(target=leaf)=>({target,button:0,defaultPrevented:false,
 preventDefault(){this.defaultPrevented=true;},stopImmediatePropagation(){this.stopped=true;}});
const down=(target=leaf)=>{const native=mouse(target),event=new TV.TVEvent(TV.evMouseDown,{nativeEvent:native});manager.handleEvent(event);return event;};
let version=manager.selectionVersion,event=down();
assert.equal(manager.activeTarget,'target');assert.equal(manager.selectionVersion,version+1);
assert.equal(event.what,TV.evNothing);assert.equal(event.nativeEvent.defaultPrevented,true);assert.equal(event.nativeEvent.stopped,true);
const click=mouse();manager.onActivationClick(click);assert.equal(click.defaultPrevented,true);assert.equal(manager.activationPress,null);
version=manager.selectionVersion;event=down();assert.equal(event.what,TV.evMouseDown);assert.equal(event.nativeEvent.defaultPrevented,false);
assert.equal(manager.selectionVersion,version,'active input repeated desktop activation');
view.options|=TV.ofFirstClick;manager.activateWindow('other');event=down();assert.equal(manager.activeTarget,'target');assert.equal(event.what,TV.evMouseDown);
view.options&=~TV.ofSelectable;manager.activateWindow('other');event=down();assert.equal(manager.activeTarget,'other');assert.equal(event.what,TV.evNothing);
view.options|=TV.ofSelectable;view.setState(TV.sfDisabled,true);event=down();assert.equal(manager.activeTarget,'other');assert.equal(event.what,TV.evNothing);view.setState(TV.sfDisabled,false);
const modal=new TV.TVGroup(bounds);modal.setState(TV.sfModal,true);modal.isOpen=()=>true;
manager.dialogs.set('modal',modal);manager.activeTarget='modal';event=down();assert.equal(manager.activeTarget,'modal');assert.equal(event.what,TV.evNothing);
manager.dialogs.delete('modal');manager.activateWindow('other');
manager.onChange=()=>{if(manager.activeTarget==='target')manager.activateWindow('other');};
event=down();assert.equal(manager.activeTarget,'other');assert.equal(event.what,TV.evNothing,'activation callback allowed input into the old target');manager.onChange=null;
manager.unregisterWindow('target');version=manager.selectionVersion;event=down();assert.equal(manager.activeTarget,'other');assert.equal(manager.selectionVersion,version);assert.equal(event.nativeEvent.defaultPrevented,false);
const host=new TV.TVWindow(bounds,'Host');host.root=root(desktop.root);host.root._tvView=host;manager.setHostWindow(host.root);
event=down(root(host.root));assert.equal(event.what,TV.evNothing);const hostName=manager.activeTarget;
assert.notEqual(hostName,'other');assert.equal(manager.activationPress,host.root);
const context=mouse(root(host.root));context.type='contextmenu';manager.onActivationClick(context);
assert.equal(context.defaultPrevented,true);assert.equal(manager.activationPress,host.root,'right-click context menu released the gesture before mouseup');
manager.onActivationBlur();assert.equal(manager.activationPress,null);
manager.activateWindow('other');event=down(root(host.root));assert.equal(event.what,TV.evNothing);
manager.destroy();assert.equal(manager.activationPress,null);assert.equal(manager.activationReleaseTimer,null);
for(const [type,set] of listeners)assert.deepEqual([...set],[...(initialListeners.get(type)||[])],'desktop cleanup retained '+type+' listeners');
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_button_default_role_preserves_flags_and_stays_in_its_window():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect();
const program=new TV.TVProgram(),desktop=new TV.TVDesktop(bounds);program.insert(desktop);
const windowA=new TV.TVWindow(bounds,'A'),windowB=new TV.TVWindow(bounds,'B');desktop.insert(windowA);desktop.insert(windowB);
const buttons=new TV.TVGroup(bounds),nested=new TV.TVGroup(bounds);windowA.insertAll([buttons,nested]);
const primary=new TV.TVButton(bounds,'OK','ok',TV.bfDefault),temporary=new TV.TVButton(bounds,'Other','other');
const foreign=new TV.TVButton(bounds,'B default','b',TV.bfDefault);buttons.insert(primary);nested.insert(temporary);windowB.insert(foreign);
assert.equal(primary.amDefault,true);assert.equal(temporary.amDefault,false);
assert.deepEqual([TV.cmGrabDefault,TV.cmReleaseDefault],[61,62]);
temporary.makeDefault(true);assert.equal(temporary.flags,TV.bfNormal,'makeDefault rewrote the declared button flags');
assert.equal(temporary.amDefault,true);assert.equal(primary.amDefault,false);assert.equal(foreign.amDefault,true);
temporary.makeDefault(false);assert.equal(temporary.amDefault,false);assert.equal(primary.amDefault,true);
primary.makeDefault(false);assert.equal(primary.flags,TV.bfDefault);assert.equal(primary.amDefault,true,'declared default was permanently removed');
temporary.setState(TV.sfFocused,true);assert.equal(temporary.amDefault,true);assert.equal(primary.amDefault,false);
nested.setState(TV.sfDisabled,true);assert.equal(temporary.amDefault,false);assert.equal(primary.amDefault,true);
nested.setState(TV.sfDisabled,false);assert.equal(temporary.amDefault,true);assert.equal(primary.amDefault,false);
temporary.setState(TV.sfFocused,false);assert.equal(primary.amDefault,true);
temporary.setState(TV.sfFocused,true);temporary.setState(TV.sfDisabled,true);
assert.equal(temporary.amDefault,false);assert.equal(primary.amDefault,true);
temporary.setState(TV.sfDisabled,false);temporary.setState(TV.sfFocused,true);
assert.equal(primary.amDefault,false);temporary.hide();assert.equal(primary.amDefault,true);
assert.equal(temporary.flags,TV.bfNormal);assert.equal(primary.flags,TV.bfDefault);assert.equal(foreign.amDefault,true);
temporary.show();temporary.setState(TV.sfFocused,false);
const observer=new TV.TVView(bounds);observer.eventMask|=TV.evBroadcast;let redirect='grab';
const other=new TV.TVButton(bounds,'Next','next');nested.insert(other);buttons.insertBefore(observer,primary);
observer.handleEvent=event=>{
 if(redirect==='grab'&&event.command===TV.cmGrabDefault&&event.infoPtr===temporary){redirect='';temporary.setState(TV.sfFocused,false);}
 else if(redirect==='release'&&event.command===TV.cmReleaseDefault&&event.infoPtr===temporary){redirect='';other.setState(TV.sfFocused,true);}
};
temporary.setState(TV.sfFocused,true);assert.equal(temporary.amDefault,false);assert.equal(primary.amDefault,true,'stale Grab overrode a newer focus decision');
temporary.setState(TV.sfFocused,true);redirect='release';temporary.setState(TV.sfFocused,false);
assert.equal(other.amDefault,true);assert.equal(primary.amDefault,false,'stale Release overrode a newer temporary default');
other.setState(TV.sfFocused,false);assert.equal(primary.amDefault,true);
const embedded=new TV.TVWindow(bounds,'Embedded'),innerDefault=new TV.TVButton(bounds,'OK','inner-ok',TV.bfDefault),innerOther=new TV.TVButton(bounds,'Other','inner-other');
embedded.insertAll([innerDefault,innerOther]);windowA.insert(embedded);innerOther.setState(TV.sfFocused,true);
assert.equal(primary.amDefault,true);assert.equal(innerDefault.amDefault,false);
temporary.setState(TV.sfFocused,true);temporary.setState(TV.sfFocused,false);
assert.equal(primary.amDefault,true,'embedded window changed its parent default scope');innerOther.setState(TV.sfFocused,false);
'''
    result = subprocess.run([NODE, "-e", script, str(ASSET_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_system_information_is_a_shared_tv_dialog_without_private_layout_css():
    dialogs = DIALOG_PATHS[1].read_text(encoding="utf-8")
    core = ASSET_PATHS[1].read_text(encoding="utf-8")
    bundle = Path("thelpviewer/server/converter/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    shell = Path("thelpviewer/server/converter/assets/tv-shell.js").read_text(encoding="utf-8")

    system_info = dialogs[
        dialogs.index("class TVSystemInformationDialog"):
        dialogs.index("class TVFindDialog")
    ]
    assert "extends TVDialog" in system_info
    assert system_info.count("new TVListBox(") == 2
    assert '"system-information-ok"' in system_info
    assert '"system-information-refresh"' in system_info
    assert "setHelpCtx(hcSystemInformation)" in system_info
    assert "class TVSystemInformationDialog" in dialogs
    assert "hcSystemInformation: 2270" in core
    assert 'dialogItem("System ~I~nformation", "systeminfo")' in bundle
    assert 'this._registerDialog("systeminfo"' in bundle
    assert 'this.registerDialog("systeminfo"' in shell


def test_dynamic_dialog_content_redraws_its_shared_frame():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    source = ASSET_PATHS[0].read_text(encoding="utf-8")
    draw_content = source[
        source.index("    drawContent() {", source.index("class TVDialog extends TVWindow")):
        source.index("\n    setState(state, enable)", source.index("    drawContent() {", source.index("class TVDialog extends TVWindow")))
    ]
    assert "this.children.forEach((view) => view.resolve?.(body));" in draw_content
    assert "if (this.isOpen())" in draw_content
    assert "updateWindowFrameState(this.dialog, this.isActive(), { dialog: true });" in draw_content


def test_concrete_dialogs_keep_tv_view_references_instead_of_rediscovering_dom():
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    assert GAME_PATHS[0].read_bytes() == GAME_PATHS[1].read_bytes()

    for path in (DIALOG_PATHS[0], GAME_PATHS[0]):
        source = path.read_text(encoding="utf-8")
        assert 'this.query("[data-tv-' not in source
        assert 'this.queryAll("[data-tv-' not in source

    core = ASSET_PATHS[0].read_text(encoding="utf-8")
    assert "class TVEvent" in core
    assert "handleEvent(event)" in core
    assert "target.dispatchEvent(new TVEvent" in core
    assert "class TVRenderer" not in core
    assert "TVRenderer" not in core

    dialogs = DIALOG_PATHS[0].read_text(encoding="utf-8")
    games = GAME_PATHS[0].read_text(encoding="utf-8")
    for source in (dialogs, games):
        assert "constructor(desktop" not in source
        assert 'document.querySelector(".tv-desktop")' not in source
    assert "class TVGameDialog extends TVDialog" in games
    assert "class TVPuzzleDialog extends TVGameDialog" in games
    assert "new TVGroup(" in games
    assert "new TVButton(" in games
    assert "new TVStaticText(" in games


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the dialog behaviour test")
def test_tv_dialog_shared_keyboard_modal_and_focus_behaviour():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor(name = "element") {
        this.name = name;
        this.hidden = false;
        this.disabled = false;
        this.isConnected = true;
        this.style = { setProperty() {}, removeProperty() {} };
        this.dataset = {};
        this.attributes = new Map();
        this.listeners = new Map();
        this.offsetWidth = 80;
        this.offsetHeight = 25;
        this.clientWidth = 160;
        this.clientHeight = 50;
        this.clicked = 0;
        const classes = new Set();
        this.classList = {
            add(...names) { names.forEach((name) => classes.add(name)); },
            remove(...names) { names.forEach((name) => classes.delete(name)); },
            contains(name) { return classes.has(name); },
            toggle(name, force) {
                const enabled = force === undefined ? !classes.has(name) : Boolean(force);
                if (enabled) { classes.add(name); } else { classes.delete(name); }
                return enabled;
            },
        };
    }
    addEventListener(type, handler) { this.listeners.set(type, handler); }
    removeEventListener(type) { this.listeners.delete(type); }
    appendChild() {}
    remove() { this.isConnected = false; }
    focus() { document.activeElement = this; }
    click() { this.clicked += 1; }
    contains(element) { return element === this; }
    closest(selector) {
        if (selector === "[hidden]") { return null; }
        return null;
    }
    getAttribute(name) { return this.attributes.get(name) || null; }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    removeAttribute(name) { this.attributes.delete(name); }
    getBoundingClientRect() { return { left: 0, top: 0, right: 8, bottom: 16, width: 8, height: 16 }; }
    querySelector() { return null; }
    querySelectorAll() { return []; }
}

global.HTMLElement = FakeElement;
global.window = global;
global.window.THelpViewerTV = {};
global.window.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
global.window.matchMedia = () => ({ matches: false });
global.window.addEventListener = () => {};
global.window.removeEventListener = () => {};
global.window.requestAnimationFrame = (callback) => callback();
global.document = {
    activeElement: null,
    body: new FakeElement("body"),
    documentElement: new FakeElement("documentElement"),
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return new FakeElement("created"); },
};
global.getComputedStyle = () => ({ getPropertyValue() { return ""; } });

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;
const desktop = new TV.TVDesktop(new TV.TVRect()).bindRoot(document.body);
const manager = desktop.dialogManager;

    function buildDialog(options = {}) {
    const overlay = new FakeElement("overlay");
    overlay.hidden = true;
    const dialogElement = new FakeElement("dialog");
    const titlebar = new FakeElement("titlebar");
    const first = new FakeElement("first");
    const second = new FakeElement("second");
    const defaultButton = new FakeElement("default");
    const closeButton = new FakeElement("close");
    dialogElement.querySelector = (selector) => (
        selector === ".tv-dialog-button.is-default" ? defaultButton
            : selector === "[data-tv-close-button]" ? closeButton
            : null
    );
    dialogElement.querySelectorAll = () => [first, second];
    overlay.querySelector = (selector) => {
        if (selector === ".tv-dialog-window") { return dialogElement; }
        if (selector === ".tv-dialog-titlebar") { return titlebar; }
        return null;
    };
    overlay.querySelectorAll = () => [];
    TV.TVView._fromHTML = () => overlay;
        const instance = new TV.TVDialog(new TV.TVRect(0, 0, 40, 12), "Test");
        if (options.helpCtx) { instance.setHelpCtx(options.helpCtx); }
        if (options.modal) { instance.setState(TV.sfModal, true); }
        if (options.escapeCloses === false) { instance.escapeCloses = false; }
        const defaultView = new TV.TVButton(new TV.TVRect(), "OK", "accept", TV.bfDefault);
        const firstView = new TV.TVView(new TV.TVRect()), secondView = new TV.TVView(new TV.TVRect());
        for (const [view, root] of [[firstView,first],[secondView,second]]) {
            view.options |= TV.ofSelectable; root.tabIndex = 0; view.bindRoot(root);
        }
        defaultButton.tabIndex = 0;
        instance.insertAll([firstView,secondView,defaultView]);
        defaultView.bindRoot(defaultButton);
    desktop.insert(instance);
    return { instance, overlay, dialogElement, first, second, firstView, secondView, defaultButton, defaultView, closeButton };
}

function keyEvent(key, target, extra = {}) {
    return {
        key,
        target,
        defaultPrevented: false,
        propagationStopped: false,
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.propagationStopped = true; },
        ...extra,
    };
}

const launcher = new FakeElement("launcher");
document.activeElement = launcher;
const regular = buildDialog();
regular.instance.open();
if (document.activeElement !== regular.dialogElement) { throw new Error("dialog did not receive focus"); }
const regularHandleEvent = regular.instance.handleEvent.bind(regular.instance);
let acceptedCommands = 0;
let escapedCommands = 0;
regular.instance.handleEvent = (tvEvent) => {
    if (tvEvent.what === TV.evCommand && tvEvent.command === "accept") {
        if (tvEvent.infoPtr !== regular.defaultView) { throw new Error("default button lost its TVView source"); }
        acceptedCommands += 1;
        regular.instance.clearEvent(tvEvent);
        return;
    }
    if (tvEvent.what === TV.evCommand && tvEvent.command === "dialog-close") { escapedCommands += 1; }
    regularHandleEvent(tvEvent);
};

const contextual = buildDialog({ helpCtx: TV.TV_HELP_CONTEXTS.hcFind });
if (contextual.overlay.getAttribute("data-tv-help-ctx") !== String(TV.TV_HELP_CONTEXTS.hcFind)
    || contextual.dialogElement.getAttribute("data-tv-help-ctx") !== String(TV.TV_HELP_CONTEXTS.hcFind)) {
    throw new Error("TVDialog did not retain its own help context");
}

regular.instance.startDrag({
    target: regular.dialogElement,
    clientX: 10,
    clientY: 10,
    preventDefault() {},
});
if (!regular.dialogElement.classList.contains("is-dragging")) {
    throw new Error("dialog move frame state was not preserved");
}
regular.instance.onDragEnd();
if (regular.dialogElement.classList.contains("is-dragging")) {
    throw new Error("dialog move frame state was not cleared");
}

const enter = keyEvent("Enter", regular.dialogElement);
regular.instance.onDialogKeyDown(enter);
if (acceptedCommands !== 1 || regular.defaultButton.clicked !== 0 || !enter.defaultPrevented) {
    throw new Error("Enter did not dispatch the default button command");
}

regular.instance.setCurrent(regular.defaultView);document.activeElement = regular.defaultButton;
const tab = keyEvent("Tab", regular.defaultButton);
regular.instance.handleEvent(new TV.TVEvent(TV.evKeyDown, {nativeEvent:tab}));
regular.instance.onDialogKeyDown(tab);
if (document.activeElement !== regular.first) { throw new Error("Tab did not wrap focus"); }
for (const view of [regular.firstView,regular.secondView,regular.defaultView]) view.hide();
for (const shiftKey of [false, true]) {
    regular.second.focus();
    const emptyTab = keyEvent("Tab", regular.second, { shiftKey });
    regular.instance.handleEvent(new TV.TVEvent(TV.evKeyDown, {nativeEvent:emptyTab}));
    regular.instance.onDialogKeyDown(emptyTab);
    if (!emptyTab.defaultPrevented || document.activeElement !== regular.dialogElement) {
        throw new Error("Tab escaped a dialog with no available controls");
    }
}
for (const view of [regular.firstView,regular.secondView,regular.defaultView]) view.show();

const escape = keyEvent("Escape", regular.dialogElement);
regular.instance.onDialogKeyDown(escape);
if (!regular.overlay.hidden || document.activeElement !== launcher || escapedCommands !== 1) {
    throw new Error("Escape did not dispatch Close and restore focus");
}

const calculatorLike = buildDialog({ escapeCloses: false });
calculatorLike.instance.open();
const calculatorEscape = keyEvent("Escape", calculatorLike.dialogElement);
calculatorLike.instance.onDialogKeyDown(calculatorEscape);
if (calculatorLike.overlay.hidden || calculatorEscape.defaultPrevented) {
    throw new Error("escapeCloses=false was ignored");
}

const modal = buildDialog({ modal: true });
modal.instance.open();
const letter = keyEvent("p", modal.dialogElement);
modal.instance.onDialogKeyDown(letter);
if (!letter.propagationStopped || letter.defaultPrevented) {
    throw new Error("modal dialog did not isolate an unhandled key");
}

const frameMarkup = (title, modal, body = "") => {
    const frame = new TV.TVFrame(new TV.TVRect());
    frame.owner = new TV.TVWindow(new TV.TVRect(), title);
    frame.owner.palette = "dialog";
    frame.owner.setState(TV.sfModal, modal);
    const markup = frame.drawDialog(body, "");
    if (!markup.includes(`data-tv-view-id="${frame.owner.viewId}"`)) {
        throw new Error("dialog frame lost its owner's binding identity");
    }
    return markup;
};
const modalMarkup = frameMarkup("Modal", true);
const nonModalMarkup = frameMarkup("Non-modal", false);
    class TestObjectBody extends TV.TVGroup { static role = "object-body"; }
    const objectBody = new TestObjectBody(new TV.TVRect()).insertAll([
        new TV.TVStaticText(new TV.TVRect(), "TV object"),
    ]);
    const objectBodyMarkup = frameMarkup("Object body", false, objectBody);
const objectSectionsMarkup = frameMarkup("Object sections", false, [
        new TV.TVStaticText(new TV.TVRect(), "First"),
        new TV.TVStaticText(new TV.TVRect(), "Second"),
    ]);
const menuItem = new TV.TVMenuItem(
    "~A~bout", "dialog-open", TV.kbF3, TV.TV_HELP_CONTEXTS.hcSystemMenu, "F3",
);
const semanticButtonMarkup = new TV.TVMenuView(new TV.TVRect(), TV.NewMenu(menuItem)).draw("bar");
if (!modalMarkup.includes('aria-modal="true"') || !modalMarkup.includes("is-modal")) {
    throw new Error("modal markup is incomplete");
}
if (!nonModalMarkup.includes('aria-modal="false"')) {
    throw new Error("non-modal markup is incorrectly announced as modal");
}
if (!objectBodyMarkup.includes('class="tv-group tv-object-body"') || !objectBodyMarkup.includes("TV object")) {
    throw new Error("TVFrame did not render a TV object body");
}
if (!objectSectionsMarkup.includes("First") || !objectSectionsMarkup.includes("Second")
    || !objectSectionsMarkup.includes("tv-border-separator")) {
    throw new Error("TVFrame did not render TV object sections");
}
        if (!semanticButtonMarkup.includes("tv-menu-item")
            || !semanticButtonMarkup.includes('data-tv-command="dialog-open"')
            || !semanticButtonMarkup.includes('class="tv-hotkey">A</span>bout')
            || !semanticButtonMarkup.includes('class="tv-menu-hotkey">F3</span>')
            || menuItem.keyCode !== TV.kbF3
            || semanticButtonMarkup.includes("data-tv-key-code")
            || !semanticButtonMarkup.includes(`data-tv-help-ctx="${TV.TV_HELP_CONTEXTS.hcSystemMenu}"`)
            || semanticButtonMarkup.includes('aria-expanded=')) {
        throw new Error("TVMenuItem semantic properties did not reach the renderer");
}
const titlebarMarkup = modalMarkup.slice(
    modalMarkup.indexOf('class="tv-dialog-titlebar '),
    modalMarkup.indexOf('class="tv-dialog-body ')
);
if ((titlebarMarkup.match(/data-tv-border-fill=/g) || []).length !== 1) {
    throw new Error("dialog title frame is not a single continuous line");
}

const managedWindow = new FakeElement("managed-window");
let closeCalls = 0;
let zoomCalls = 0;
manager.registerWindow("viewer", managedWindow, {
    [TV.TV_COMMANDS.CLOSE]: () => { closeCalls += 1; },
    [TV.TV_COMMANDS.ZOOM]: () => { zoomCalls += 1; },
});
if (!manager.dispatchCommand(TV.TV_COMMANDS.ZOOM) || zoomCalls !== 1) {
    throw new Error("active window did not receive Zoom");
}
if (!manager.dispatchCommand(TV.TV_COMMANDS.CLOSE) || closeCalls !== 1) {
    throw new Error("active window did not receive Close");
}

const managedDialog = buildDialog();
let dialogCloseCalls = 0;
let managedCloseCommands = 0;
const managedHandleEvent = managedDialog.instance.handleEvent.bind(managedDialog.instance);
managedDialog.instance.handleEvent = (tvEvent) => {
    if (tvEvent.what === TV.evCommand && tvEvent.command === "dialog-close") {
        managedCloseCommands += 1;
    }
    managedHandleEvent(tvEvent);
};
managedDialog.instance.bindCommonClose(() => {
    dialogCloseCalls += 1;
    managedDialog.instance.close();
});
manager.register("managed-dialog", managedDialog.instance);
managedDialog.instance.open();
managedDialog.instance.dispatchEvent(new TV.TVEvent(TV.evMouseDown, {
    infoPtr: managedDialog.instance, nativeEvent: { target: managedDialog.overlay, type: "click" },
}));
if (dialogCloseCalls !== 0 || managedDialog.overlay.hidden) {
    throw new Error("overlay click closed a Turbo Vision dialog");
}
managedDialog.instance.open();
if (managedDialog.closeButton.hidden) {
    throw new Error("active dialog close control is hidden");
}
TV.updateWindowFrameState(managedDialog.dialogElement, false, { dialog: true });
if (managedDialog.closeButton.hidden
    || !managedDialog.closeButton.classList.contains("is-frame-control-passive")
    || managedDialog.closeButton.getAttribute("aria-disabled") !== null) {
    throw new Error("inactive dialog close control is not visible and passive");
}
TV.updateWindowFrameState(managedDialog.dialogElement, true, { dialog: true });
if (!manager.dispatchCommand(TV.TV_COMMANDS.CLOSE) || dialogCloseCalls !== 1 || managedCloseCommands !== 1) {
    throw new Error("active dialog did not receive Close");
}
managedDialog.instance.open();
if (!manager.dispatchCommand(TV.TV_COMMANDS.CANCEL) || dialogCloseCalls !== 2 || managedCloseCommands !== 2) {
    throw new Error("active dialog did not receive Cancel through its command path");
}
managedDialog.instance.destroy();
if (manager.get("managed-dialog") !== null || managedDialog.overlay.isConnected || managedDialog.instance.owner !== null) {
    throw new Error("destroy did not remove and unregister the dialog");
}
managedDialog.instance.open();
if (managedDialog.overlay.isConnected || !managedDialog.overlay.hidden) {
    throw new Error("a destroyed dialog was reopened");
}

const secondWindow = new FakeElement("second-window");
manager.registerWindow("second", secondWindow);
const expectedNext = manager.openTargets()[0];
if (!manager.dispatchCommand(TV.TV_COMMANDS.NEXT) || manager.activeTarget !== expectedNext) {
    throw new Error("Next did not cycle to the following managed target");
}
if (!manager.dispatchCommand(TV.TV_COMMANDS.PREVIOUS) || manager.activeTarget !== "second") {
    throw new Error("Previous did not cycle to the preceding managed target");
}
"""
    result = subprocess.run(
        [NODE, "-e", script, str(ASSET_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_calculator_preserves_escape_as_a_calculator_key():
    dialog_paths = (
        Path("www/assets/tv-dialogs.js"),
        Path("thelpviewer/server/converter/assets/tv-dialogs.js"),
    )
    assert dialog_paths[0].read_bytes() == dialog_paths[1].read_bytes()
    source = dialog_paths[0].read_text(encoding="utf-8")
    calculator = source[source.index("class TVCalculatorDialog"):source.index("class TVCalendarDialog")]
    assert "this.escapeCloses = false" in calculator


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the calendar behavior test")
def test_calendar_uses_gregorian_leap_year_rules():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function isLeapYear");
const end = source.indexOf("function dayOfWeek", start);
eval(source.slice(start, end) + "\nglobalThis.testLeapYear = isLeapYear;");
const expected = new Map([
    [1900, false],
    [2000, true],
    [2023, false],
    [2024, true],
    [2100, false],
]);
for (const [year, leap] of expected) {
    if (testLeapYear(year) !== leap) {
        throw new Error(`unexpected leap-year result for ${year}`);
    }
}
'''
    subprocess.run(
        [NODE, "-e", script, str(ASSET_PATHS[0])],
        check=True,
        capture_output=True,
        text=True,
    )


def test_calendar_matches_dos_navigator_geometry_and_navigation():
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    source = DIALOG_PATHS[0].read_text(encoding="utf-8")
    calendar = source[source.index("class TVCalendarView"):source.index("class TVColorSelector")]
    assert 'new TVRect(0, 0, 30, 10), "Calendar"' in calendar
    assert 'new TVRect(0, 2, 28, 8)' in calendar
    assert '"Mo  Tu  We  Th  Fr  Sa  Su  "' in calendar
    assert '"calendar-today"' in calendar
    assert "this.changeDay(-7)" in calendar
    assert "this.changeDay(7)" in calendar
    assert "this.changeYear(-1)" in calendar
    assert "this.changeYear(1)" in calendar


def test_close_and_zoom_commands_are_routed_to_the_active_target():
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    shell_paths = (
        Path("www/assets/tv-shell.js"),
        Path("thelpviewer/server/converter/assets/tv-shell.js"),
    )
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert shell_paths[0].read_bytes() == shell_paths[1].read_bytes()

    bundle_source = bundle_paths[0].read_text(encoding="utf-8")
    shell_source = shell_paths[0].read_text(encoding="utf-8")
    assert 'registerWindow("help:" + key, windowEl, {' in bundle_source
    assert "registerWindow(managerName, windowEl, {" in bundle_source
    assert bundle_source.count("dispatchCommand(TV_COMMANDS.CLOSE)") >= 2
    assert bundle_source.count("dispatchCommand(TV_COMMANDS.ZOOM)") >= 1
    assert "kbF5" in bundle_source
    assert "kbF6" in bundle_source
    assert "kbShiftF6" in bundle_source
    assert "kbAltF3" in bundle_source
    assert "_handleMenuShortcut" not in bundle_source
    assert "this.windowManager.closeAll()" not in bundle_source
    assert "this.windowManager.toggleZoom()" not in bundle_source
    assert "setHostWindow(hostWindow, hostWindow ? {" in shell_source
    assert "dispatchCommand(TV_COMMANDS.CLOSE)" in shell_source
    assert "dispatchCommand(TV_COMMANDS.ZOOM)" in shell_source
