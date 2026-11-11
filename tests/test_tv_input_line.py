"""Input models survive shared-dialog redraws, with and without validators."""
from pathlib import Path
import shutil
import subprocess

import pytest

NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_input_events_preserve_plain_and_validated_values_when_rebound():
    assert Path("www/assets/tv-core.js").read_bytes() == Path("thelpviewer/server/converter/assets/tv-core.js").read_bytes()
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={window:{},document:{addEventListener(){}},getComputedStyle:()=>({getPropertyValue:()=>''}),console};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const TV=context.window.THelpViewerTV;
function root(view){
 const attrs=new Map([['data-tv-view-id',view.viewId]]);
 return {value:'',style:{},classList:{toggle(){}},addEventListener(){},removeEventListener(){},
  getAttribute:key=>attrs.get(key),setAttribute:(key,value)=>attrs.set(key,value),
  toggleAttribute:(key,on)=>on?attrs.set(key,''):attrs.delete(key)};
}
for(const [validator,value] of [[null,'Ján'],[null,'Novák'],[null,'Unstored nickname'],
 [new TV.TVEmailValidator(),'name@example.test'],[new TV.TVFilterValidator('0123456789'),'64']]){
 const input=new TV.TVInputLine(new TV.TVRect(0,0,20,1),100);
 if(validator)input.setValidator(validator);
 input.resolve(root(input));input.root.value=value;
 input.handleEvent(new TV.TVEvent(TV.evBroadcast,{infoPtr:input,nativeEvent:{type:'input',target:input.root}}));
 assert.equal(input.data,value);
 assert.ok(input.draw().includes(value));
 input.resolve(root(input));assert.equal(input.getData(),value);
 if(validator){
  input.root.value='invalid input';
  input.handleEvent(new TV.TVEvent(TV.evBroadcast,{infoPtr:input,nativeEvent:{type:'input',target:input.root}}));
  assert.equal(input.getData(),value);assert.equal(input.data,value);
 }
}
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-core.js"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_input_edits_and_clipboard_recheck_the_owner_hierarchy():
    assert Path("www/assets/tv-core.js").read_bytes() == Path("thelpviewer/server/converter/assets/tv-core.js").read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
let clipboardCalls=0;
Object.defineProperty(global,'navigator',{value:{clipboard:{async writeText(){clipboardCalls++;},async readText(){clipboardCalls++;return 'paste';}}}});
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV;
(async()=>{
 const group=new TV.TVGroup(new TV.TVRect()),input=new TV.TVInputLine(new TV.TVRect(),40);group.insert(input);
 input.root={value:'',hidden:false,disabled:false,readOnly:false,isConnected:true,selectionStart:1,selectionEnd:3,
  selectionDirection:'forward',scrollLeft:0,setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end;}};
 const send=type=>{const native={type,target:input.root,cancelable:true,inputType:'insertText',data:'X',
  defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}};
  const event=new TV.TVEvent(TV.evBroadcast,{infoPtr:input,nativeEvent:native});input.handleEvent(event);return native;};
 for(const flag of [TV.sfDisabled,TV.sfVisible]){
  input.setData('kept');group.setState(flag,flag===TV.sfDisabled);
  assert.equal(send('beforeinput').defaultPrevented,true,'unavailable owner allowed a native edit');
  input.root.value='forged';send('input');assert.equal(input.getData(),'kept');
  assert.equal(input.insertText('X'),false);
  assert.equal(await input.clipCopy(),false);assert.equal(await input.clipCut(),false);assert.equal(await input.clipPaste(),false);
  assert.equal(clipboardCalls,0,'unavailable input accessed the clipboard');
  input.setData('server update');assert.equal(input.getData(),'server update');
  group.setState(flag,flag!==TV.sfDisabled);
  assert.equal(send('beforeinput').defaultPrevented,false);
  input.root.value='accepted';send('input');assert.equal(input.getData(),'accepted');
 }
 let release;const pending=new Promise(resolve=>release=resolve);
 navigator.clipboard.readText=async()=>{clipboardCalls++;await pending;return 'delayed';};
 input.setData('kept');const paste=input.clipPaste();group.setState(TV.sfDisabled,true);release();
 assert.equal(await paste,false);assert.equal(input.getData(),'kept','pending paste ignored a newly disabled owner');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-core.js"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
