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
const context={window:{},document:{addEventListener(){}},console};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const TV=context.window.THelpViewerTV;
function root(view){
 const attrs=new Map([['data-tv-view-id',view.viewId]]);
 return {value:'',classList:{toggle(){}},addEventListener(){},removeEventListener(){},
  getAttribute:key=>attrs.get(key),setAttribute:(key,value)=>attrs.set(key,value)};
}
for(const [validator,value] of [[null,'Ján'],[null,'Novák'],[null,'Unstored nickname'],
 [new TV.TVEmailValidator(),'name@example.test'],[new TV.TVFilterValidator('0123456789'),'64']]){
 const input=new TV.TVInputLine(new TV.TVRect(0,0,20,1),100);
 if(validator)input.setValidator(validator);
 input.resolve(root(input));input.root.value=value;
 input.handleEvent(new TV.TVEvent(TV.evBroadcast,{infoPtr:input,nativeEvent:{type:'input'}}));
 assert.equal(input.data,value);
 assert.ok(input.draw().includes(value));
 input.resolve(root(input));assert.equal(input.getData(),value);
 if(validator){
  input.root.value='invalid input';
  input.handleEvent(new TV.TVEvent(TV.evBroadcast,{infoPtr:input,nativeEvent:{type:'input'}}));
  assert.equal(input.getData(),value);assert.equal(input.data,value);
 }
}
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-core.js"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
