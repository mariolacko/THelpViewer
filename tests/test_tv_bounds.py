"""Shared TVision owner growth does not need application-specific layout code."""

from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_owner_growth_masks_relative_rounding_limits_and_nested_groups():
    core = Path("www/assets/tv-core.js")
    assert core.read_bytes() == Path("thelpviewer/server/converter/assets/tv-core.js").read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){}};
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV;
const rect=view=>[view.bounds.x1,view.bounds.y1,view.bounds.x2,view.bounds.y2];
const owner=new TV.TVGroup(new TV.TVRect(3,2,83,27));
const all=[];
for(let mode=0;mode<=TV.gfGrowAll;mode++){
 const view=new TV.TVView(new TV.TVRect(2,3,20,10));view.growMode=mode;owner.insert(view);all.push(view);
}
owner.growTo(90,30);
all.forEach((view,mode)=>assert.deepEqual(rect(view),[
 2+(mode&TV.gfGrowLoX?10:0),3+(mode&TV.gfGrowLoY?5:0),
 20+(mode&TV.gfGrowHiX?10:0),10+(mode&TV.gfGrowHiY?5:0)],`grow mask ${mode}`));
owner.growTo(80,25);
all.forEach(view=>assert.deepEqual(rect(view),[2,3,20,10]));
owner.moveTo(8,9);
all.forEach(view=>assert.deepEqual(rect(view),[2,3,20,10],'moving an owner changed local child bounds'));

const relativeOwner=new TV.TVGroup(new TV.TVRect(0,0,80,20));
const relative=new TV.TVView(new TV.TVRect(20,4,60,16));
relative.growMode=TV.gfGrowAll|TV.gfGrowRel;relativeOwner.insert(relative);
relativeOwner.growTo(120,30);assert.deepEqual(rect(relative),[30,6,90,24]);
relativeOwner.growTo(80,20);assert.deepEqual(rect(relative),[20,4,60,16]);
const rounded=new TV.TVView(new TV.TVRect(1,1,7,3));rounded.growMode=TV.gfGrowHiX|TV.gfGrowHiY|TV.gfGrowRel;
const oddOwner=new TV.TVGroup(new TV.TVRect(0,0,9,5)).insertAll([rounded]);
oddOwner.growTo(13,7);assert.deepEqual(rect(rounded),[1,1,10,4]);
const zeroOwner=new TV.TVGroup(new TV.TVRect()).insertAll([relativeOwner]);
relativeOwner.growMode=TV.gfGrowAll|TV.gfGrowRel;zeroOwner.growTo(80,25);
assert.deepEqual(rect(relativeOwner),[0,0,80,20],'zero-size former owner produced invalid relative coordinates');

class Limited extends TV.TVView {
 sizeLimits(){return {min:new TV.TVPoint(8,3),max:new TV.TVPoint(30,10)};}
}
const limited=new Limited(new TV.TVRect(2,1,14,6));limited.growMode=TV.gfGrowHiX|TV.gfGrowHiY;
const limitedOwner=new TV.TVGroup(new TV.TVRect(0,0,40,15)).insertAll([limited]);
limitedOwner.growTo(100,50);assert.deepEqual(rect(limited),[2,1,32,11]);
limitedOwner.growTo(1,1);assert.deepEqual(rect(limited),[2,1,10,4]);
const output=new TV.TVRect(99,99,99,99);
limited.calcBounds(output,new TV.TVPoint());
assert.deepEqual([output.x1,output.y1,output.x2,output.y2],rect(limited),'CalcBounds did not initialize its output from current bounds');
assert.deepEqual(rect(limited),[2,1,10,4],'CalcBounds changed the view before ChangeBounds');

const outer=new TV.TVGroup(new TV.TVRect(0,0,40,15));
const nested=new TV.TVGroup(new TV.TVRect(2,2,38,13));nested.growMode=TV.gfGrowHiX|TV.gfGrowHiY;
const inner=new TV.TVView(new TV.TVRect(4,3,10,5));inner.growMode=TV.gfGrowAll;
inner.hide();nested.insert(inner);outer.insert(nested);outer.growTo(48,19);
assert.deepEqual(rect(nested),[2,2,46,17]);assert.deepEqual(rect(inner),[12,7,18,9]);
assert.equal(inner.getState(TV.sfVisible),false,'resizing exposed a hidden child');
outer.locate(new TV.TVRect(0,0,40,15));assert.deepEqual(rect(inner),[4,3,10,5]);
assert.throws(()=>outer.changeBounds({width:2,height:3}),TypeError);
assert.deepEqual(rect(outer),[0,0,40,15],'invalid resize partially changed an owner');
'''
    result = subprocess.run([shutil.which("node"), "-e", script, str(core)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
