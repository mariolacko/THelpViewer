"""Shared sparse list collection: revisions, cancellation and a bounded cache."""
from pathlib import Path
import shutil
import subprocess
import pytest

NODE = shutil.which('node')

@pytest.mark.skipif(NODE is None, reason='Node.js is required')
def test_remote_collection_keeps_pages_bounded_and_rejects_stale_responses():
    source = Path('www/assets/tv-core.js').read_text()
    model = source[source.index('class TVPagedCollection {'):source.index('class TVListViewer extends TVView')]
    script = model + r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 let calls=0,revision='one',blocked=null;
 const loader=async({offset,limit,signal})=>{
  calls++;if(blocked){const resolve=await new Promise(r=>blocked={resolve:r,signal});await resolve;}
  return {offset,total:5000,revision,items:Array.from({length:limit},(_,i)=>({label:'Row '+(offset+i)}))};
 };
 const model=new TVPagedCollection(100,loader);
 let notifications=0;model.subscribe(()=>notifications++);
 await model.refresh();assert(model.count===5000&&Object.keys(model.items).length===100,'Initial page was not sparse');
 await Promise.all([model.load(355),model.load(359)]);assert(calls===2,'Page requests were not deduplicated');
 assert(model.at(355).label==='Row 355'&&!model.at(1000),'Wrong logical indices');
 model.pinned=new Set([0]);for(let i=4;i<20;i++)await model.load(i*100);
 assert(model.pages.size<=8&&Object.keys(model.items).length<=800&&model.at(0),'Page cache grew or lost pinned selection');
 const before=notifications;blocked=true;
 const old=model.load(2500).catch(e=>e.name);
 await new Promise(r=>setTimeout(r,0));const pending=blocked;
 model.clear();blocked=null;revision='two';await model.refresh();
 pending.resolve();assert(await old==='AbortError','An obsolete response was accepted');
 assert(model.revision==='two'&&!model.at(2500)&&notifications===before+2,'Old query changed the new collection');
 blocked=true;model.requestRange(3000,3020,[0]);await new Promise(r=>setTimeout(r,0));const scrolled=blocked;
 blocked=null;model.requestRange(4000,4020,[0]);assert(scrolled.signal.aborted,'Obsolete scrolling request was not cancelled');
 scrolled.resolve();await new Promise(r=>setTimeout(r,0));
 assert(model.pending.size===0,'Finished requests leaked');
 model.dispose();assert(!model.pending.size&&!model.listeners.size&&!model.items.length,'Disposal retained resources');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
