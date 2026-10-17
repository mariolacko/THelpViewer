"""Local-folder capabilities stay in the browser, separate from server C/media."""
import io
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

from test_dos_prompt import store_at, cd_image, floppy_image


@pytest.mark.parametrize("media", [None, "cd", "floppy"])
def test_browser_disk_boot_reserves_d_for_hot_swap_without_secure_mode(tmp_path, media):
    import uuid
    store = store_at(tmp_path)
    account = uuid.uuid4().hex
    ident = store.add_media(account, media, cd_image() if media == "cd" else floppy_image()) if media else ""
    data, metadata = store.bundle(account, ident, lazy=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        config = archive.read(".jsdos/dosbox.conf").decode()
        assert "config -securemode" not in config
        assert "mount d drive_d" in config
        assert [name for name in archive.namelist() if name.startswith("drive_d/")] == ["drive_d/"]
        if media:
            assert f'imgmount {"e" if media == "cd" else "a"} media/' in config
    assert "local" not in metadata  # No directory handle, name or content in the response.


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_local_folder_adapter_aliases_boundaries_writes_conflicts_and_deletions():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Channel {constructor(){this.onmessage=null;}close(){}postMessage(data){this.sent=data;}}
const TV={};const context={URL,Blob,TextDecoder,Uint8Array,Map,Set,crypto:require('node:crypto').webcrypto,
 BroadcastChannel:Channel,window:{THelpViewerTV:TV,isSecureContext:true,showDirectoryPicker(){}}};
vm.runInNewContext(fs.readFileSync('www/assets/tv-dos-local.js','utf8'),context);
let tick=0;
const missing=()=>{const e=new Error('missing');e.name='NotFoundError';throw e;};
class FileHandle {
 constructor(name,text){this.name=name;this.kind='file';this.write(text);}
 write(text){this.data=new Uint8Array(typeof text==='string'?Buffer.from(text):text);this.time=++tick;}
 async getFile(){const file=new Blob([this.data]);Object.defineProperty(file,'lastModified',{value:this.time});return file;}
 async isSameEntry(other){return other===this;}
 async createWritable(){let pending;return{write:async value=>{pending=value;},close:async()=>{this.write(pending);},abort:async()=>{}};}
}
class Directory {
 constructor(name='root'){this.name=name;this.kind='directory';this.children=new Map();}
 async *values(){yield* this.children.values();}
 async isSameEntry(other){return other===this;}
 async getFileHandle(name,{create=false}={}){if(!this.children.has(name)){if(!create)missing();this.children.set(name,new FileHandle(name,''));}const item=this.children.get(name);if(item.kind!=='file')throw Error('type mismatch');return item;}
 async getDirectoryHandle(name,{create=false}={}){if(!this.children.has(name)){if(!create)missing();this.children.set(name,new Directory(name));}const item=this.children.get(name);if(item.kind!=='directory')throw Error('type mismatch');return item;}
 async removeEntry(name,options){assert.ok(!options?.recursive);const item=this.children.get(name);if(!item)missing();if(item.children?.size)throw Error('Directory not empty');this.children.delete(name);}
}
const bytes=text=>new Uint8Array(Buffer.from(text));
function ciFor(drive,revision,nodes,dirty,files){const count=nodes=>nodes.reduce((n,node)=>n+1+(node.nodes?count(node.nodes):0),0);return{fsTree:async()=>({name:'.',nodes:[{name:'drive_d',nodes}]}),fsReadFile:async name=>{
 if(name==='.jsdos/local-state.json')return bytes(JSON.stringify({mount:drive.id,revision,dirty,entries:count(nodes)}));
 assert.ok(name.startsWith('drive_d/'));assert.ok(name in files,name);return bytes(files[name]);
}};}
(async()=>{
 const root=new Directory();for(const name of ['readme.txt','DELETE.TXT','Very long name.txt','VERY_L~1.TXT'])root.children.set(name,new FileHandle(name,name));
 const drive=new TV.DosLocalDrive(root);assert.ok(TV.DosLocalDrive.supported());await drive.prepare();
 assert.equal(drive.writable,true);assert.ok(drive.records.has('README.TXT'));
 assert.ok(drive.records.has('VERY_L~1.TXT'));assert.ok(drive.records.has('VERY_L~2.TXT'));
 const nodes=[{name:'README.TXT'},{name:'VERY_L~1.TXT'},{name:'VERY_L~2.TXT'},{name:'NEW',nodes:[{name:'SAVE.DAT'}]}];
 const ci=ciFor(drive,1,nodes,['README.TXT','NEW','NEW/SAVE.DAT','DELETE.TXT'],{'drive_d/README.TXT':'updated','drive_d/NEW/SAVE.DAT':'saved'});
 await drive.save(ci);assert.equal(await(await root.children.get('readme.txt').getFile()).text(),'updated');
 assert.equal(await(await root.children.get('NEW').children.get('SAVE.DAT').getFile()).text(),'saved');assert.ok(!root.children.has('DELETE.TXT'));
 assert.equal(drive.savedRevision,1);await drive.save(ci); // unchanged revision does no writes.
 root.children.get('readme.txt').write('outside');
 await assert.rejects(drive.save(ciFor(drive,2,nodes,['README.TXT'],{'drive_d/README.TXT':'overwrite'})),/outside DOS/);
 assert.equal(await(await root.children.get('readme.txt').getFile()).text(),'outside');
 for(const path of ['../secret','/etc/passwd','C:/X','A/../X','A\\X','CON','A//X','A\0X'])await assert.rejects(drive.node(path,'file'),/Invalid local DOS path/);
 const extra=new Directory();extra.children.set('DIR',new Directory('DIR'));
 const safe=new TV.DosLocalDrive(extra);await safe.prepare();extra.children.get('DIR').children.set('EXTERNAL.TXT',new FileHandle('EXTERNAL.TXT','keep'));
 await assert.rejects(safe.save(ciFor(safe,1,[],['DIR'],{})),/not empty/);
 assert.ok(extra.children.get('DIR').children.has('EXTERNAL.TXT'));
 await assert.rejects(safe.save({fsReadFile:async()=>bytes(JSON.stringify({mount:safe.id,revision:2,dirty:[]})),fsTree:async()=>({name:'.',nodes:[]})}),/unavailable/);
 await assert.rejects(safe.save({fsReadFile:async()=>bytes(JSON.stringify({mount:safe.id,revision:2,dirty:[],entries:1})),fsTree:async()=>({name:'.',nodes:[{name:'drive_d',nodes:[]}]})}),/Incomplete/);
 await assert.rejects(safe.save(ciFor(drive,3,[],[],{})),/Invalid local DOS disk state/); // Wrong folder identity cannot delete originals.
 const retryRoot=new Directory(),get=retryRoot.getFileHandle.bind(retryRoot);let fail=true;
 retryRoot.getFileHandle=async(name,options)=>{const handle=await get(name,options);if(options?.create&&fail){fail=false;const original=handle.createWritable.bind(handle);handle.createWritable=async()=>{handle.createWritable=original;throw Error('temporary write denial');};}return handle;};
 const retry=new TV.DosLocalDrive(retryRoot);await retry.prepare();const retryCi=ciFor(retry,1,[{name:'NEW.TXT'}],['NEW.TXT'],{'drive_d/NEW.TXT':'retry saved'});
 await assert.rejects(retry.save(retryCi),/temporary/);assert.ok(retry.records.has('NEW.TXT'));
 await retry.save(retryCi);assert.equal(await(await retryRoot.children.get('NEW.TXT').getFile()).text(),'retry saved');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_local_save_serializes_with_cloud_and_flushes_before_account_close():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class View{setHelpCtx(){}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
const TV={TVView:View,TVWindow:Window,TVStaticText:View,TVRect:class{},TVPoint:class{},TV_HELP_CONTEXTS:{}};
const context={URL,Promise,clearInterval(){},clearTimeout(){},window:{THelpViewerTV:TV},
 document:{currentScript:{src:'http://localhost/assets/tv-dos.js'},removeEventListener(){}}};
vm.runInNewContext(fs.readFileSync('www/assets/tv-dos.js','utf8'),context);
(async()=>{
 const win=new TV.TVDosWindow(),saved=[];let release,exited=0;
 win.view.ci={exit:async()=>exited++};win.session={account:'reader'};win.localDrive={writable:true,release(){}};
 win.saveSnapshot=async localOnly=>{saved.push(localOnly);if(saved.length===1)await new Promise(resolve=>release=resolve);};
 const local=win.save(true),cloud=win.save();assert.deepEqual(saved,[true]);release();await Promise.all([local,cloud]);
 assert.deepEqual(saved,[true,false]);assert.equal(win.saving,null);
 win.session.account='';await win.stop(false); // Account expiry never uploads old C.
 assert.deepEqual(saved,[true,false,true]);assert.equal(exited,1);assert.equal(win.disposed,true);
 const failed=new TV.TVDosWindow();failed.view.ci={};failed.session={account:''};failed.localDrive={writable:true};
 failed.saveSnapshot=async localOnly=>{assert.equal(localOnly,true);throw Error('conflict');};
 await assert.rejects(failed.stop(false),/conflict/);assert.ok(failed.view.ci);assert.equal(failed.disposed,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


def test_local_assets_are_mirrored_and_loaded_before_dos():
    for filename in ("tv-dos-local.js", "tv-dos.js", "dos/tv-dos-worker.js"):
        assert (Path("www/assets") / filename).read_bytes() == (Path("thelpviewer/server/converter/assets") / filename).read_bytes()
    source = Path("www/index.html").read_text()
    assert source.index('src="assets/tv-dos-local.js') < source.index('src="assets/tv-dos.js')


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_local_folder_picker_gesture_cancel_unsupported_and_guest_save():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class View{clearEvent(e){e.what=0;}setHelpCtx(){}setText(){}setState(){}}
class Window extends View{insertAll(children){children.forEach(child=>child.owner=this);}}
let confirmation='cancel';
class Message {static MF_CONFIRMATION=1;static MF_OK_CANCEL=2;async show(data){assert.match(data.lines.join(' '),/will not restart/);return confirmation;}destroy(){}}
const TV={TVView:View,TVWindow:Window,TVStaticText:View,TVRect:class{},TVPoint:class{},evCommand:1,TV_HELP_CONTEXTS:{hcDosPrompt:2320},
 TVMessageBox:Message,
 DosLocalDrive:class{constructor(handle){this.handle=handle;this.writable=true;}static supported(){return true;}}};
const context={URL,Promise,console,window:{THelpViewerTV:TV},document:{currentScript:{src:'http://localhost/assets/tv-dos.js'},hidden:false,fullscreenElement:null}};
vm.runInNewContext(fs.readFileSync('www/assets/tv-dos.js','utf8'),context);
(async()=>{
 const win=new TV.TVDosWindow(),handle={name:'private-folder'},calls=[];
 win.root={isConnected:true};win.active=true;win.view.ci={pause(){},resume(){}};win.session={account:''};
 context.window.showDirectoryPicker=options=>{calls.push('picker');assert.equal(options.mode,'readwrite');return Promise.resolve(handle);};
 win.confirmRestart=async()=>{throw Error('Local mount asks for restart');};
 win.restart=async()=>{throw Error('Local mount restarted DOS');};
 const pending=win.chooseLocalFolder();assert.deepEqual(calls,['picker']);await pending;assert.equal(win.localDrive,null);
 confirmation='ok';win.changeLocalFolder=async drive=>{assert.equal(drive.handle,handle);win.localDrive=drive;};
 await win.chooseLocalFolder();let saved=0;win.localDrive.save=async ci=>{assert.equal(ci,win.view.ci);saved++;};
 await win.save();assert.equal(saved,1);assert.equal(win.snapshotting,false); // No account or fetch required.
 win.session.account='reader';win.active=false; // Local flush must not upload C or require focus.
 let dirty=false;win.localDrive.hasChanges=async()=>dirty;
 await win.autoSaveLocal();assert.equal(saved,1);assert.equal(win.snapshotting,false);
 dirty=true;await win.autoSaveLocal();assert.equal(saved,2);
 win.localDrive.save=async()=>{throw Error('permission revoked');};const saveErrors=[];win.onError=e=>saveErrors.push(e.message);
 await win.autoSaveLocal();assert.equal(win.localSaveFailed,true);assert.equal(win.paused,true);
 assert.match(saveErrors[0],/permission revoked/);assert.match(saveErrors[0],/Retry local save/);
 await win.autoSaveLocal();assert.equal(saveErrors.length,1); // No repeated error boxes.
 win.localDrive.save=async()=>{saved++;};await win.save(true);
 assert.equal(saved,3);assert.equal(win.localSaveFailed,false);assert.equal(win.snapshotting,false);
 win.session.account='';
 TV.DosLocalDrive.supported=()=>false;
 await assert.rejects(win.chooseLocalFolder(),/File System Access/);
 TV.DosLocalDrive.supported=()=>true;
 context.window.showDirectoryPicker=()=>{const error=new Error('cancelled');error.name='AbortError';return Promise.reject(error);};
 const errors=[];win.onError=error=>errors.push(error);win.handleEvent({what:1,command:'dos-mount-local'});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(win.selectingLocal,false);assert.deepEqual(errors,[]);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
