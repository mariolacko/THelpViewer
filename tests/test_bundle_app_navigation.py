import json
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for alias namespace tests")
def test_explicit_alias_cannot_be_coerced_into_an_unrelated_numeric_topic():
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a);return source.slice(a,b);}
eval(section('function normalizeDirectTopicRef(bundle, ref)','function flattenUhfIndexEntries(bundle)'));
const bundle={_catalogFile:'target.json.gz',topics:{
 '0':{id:0}, '7':{id:7,aliases:{strings:['0070','70','0'],lines:{'0070':2,'70':3,'0':4}}},
 '70':{id:70}, '8':{id:8}}};
for(const [alias,line] of [['0070',2],['70',3],['0',4]]){
 assert.deepEqual(normalizeTopicTarget(bundle,alias,null,true),{topic:'7',line});
 assert.deepEqual(normalizeTopicTarget(bundle,alias,1,true),{topic:'7',line:1});
}
assert.deepEqual(normalizeTopicTarget(bundle,'70'),{topic:'70',line:null});
assert.deepEqual(normalizeTopicTarget(bundle,'0'),{topic:'0',line:null});
assert.equal(normalizeTopicTarget(bundle,'8',null,true),null);
global.window={location:{pathname:'/'}};
const CONTEXT_HELP_BUNDLE_FILE='context.json',bundleCache=new Map();
const findCatalogEntryBySourceFile=()=>({file:'target.json.gz'}),loadBundle=async()=>bundle;
eval(section('function viewerUrl(params)','function parseUhfTag(tagBody'));
assert.equal(bundleTargetUrl({}, {sourceFile:'target.hlp',topicAlias:'0070'}),'/?file=target.json.gz&alias=0070');
assert.equal(bundleTargetUrl({}, {sourceFile:'target.hlp',topicAlias:'70',topicLine:5}),'/?file=target.json.gz&alias=70&line=5');
bundleCache.set('target.json.gz',bundle);
assert.equal(bundleTargetUrl({}, {sourceFile:'target.hlp',topicAlias:'70'}),'/?file=target.json.gz&topic=7&line=3');
assert.equal(bundleTargetUrl(bundle,{bundleTopic:'70',topicAlias:'0070'}),'/?file=target.json.gz&topic=70');
const wrapBundleContent=(_bundle,html)=>html,renderTopicContent=()=> 'TEXT',bundleHeaderLabel=()=> 'HELP';
const recordTopicOpen=()=>{},bundleTopicTitle=()=> 'Topic',recordStatisticsEvent=()=>{};
eval('globalThis.Manager=class {'+section('    showTopic(bundle, contextHex','    showHelpContentsTopic(bundle)')
 +section('    async openSourceTopic(','    _focusTopicLine(')
 +section('    async _openTopicTarget(','    toggleZoom(')+'}');
const manager=new Manager();manager._pushHistory=()=>{};manager._openWindow=()=>({});
manager._focusTopicLine=()=>{};manager._normalizeLineNumber=n=>Number(n)>0?Number(n):null;
manager.onError=error=>{throw error;};
(async()=>{
 assert.equal(await manager.openSourceTopic('target.hlp','0070',null,bundle,true),true);
 assert.equal(manager.currentContextHex,'7');assert.equal(manager.currentLineNumber,2);
 await manager._openTopicTarget({_tvWindowView:{bundle}},{topicAlias:'70'});
 assert.equal(manager.currentContextHex,'7');assert.equal(manager.currentLineNumber,3);
 await manager._openTopicTarget({_tvWindowView:{bundle}},{sourceFile:'target.hlp',topicAlias:'0',topicLine:1});
 assert.equal(manager.currentContextHex,'7');assert.equal(manager.currentLineNumber,1);
 assert.equal(await manager.openSourceTopic('target.hlp','8',null,bundle,true),false);
 assert.equal(manager.currentContextHex,'7');
 await manager._openTopicTarget({_tvWindowView:{bundle}},{bundleTopic:0,topicAlias:'70'});
 assert.equal(manager.currentContextHex,'0');assert.equal(manager.currentLineNumber,null);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-bundle-app.js"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for HELP navigation tests")
def test_missing_native_topic_keeps_its_url_and_reports_error_without_replacing_the_page():
    paths = [Path("www/assets/tv-bundle-app.js"), Path("thelpviewer/server/converter/assets/tv-bundle-app.js")]
    assert paths[0].read_bytes() == paths[1].read_bytes()
    script = r'''
const fs = require('node:fs'), assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
function section(start, end) { return source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))); }
global.window = {location: {pathname: '/'}};
const CONTEXT_HELP_BUNDLE_FILE = 'context.json';
const bundle = {_catalogFile: 'Example/help.json.gz', topics: {'7': {id: 7, aliases: {ids: [17]}}}};
const bundleCache = new Map(), findCatalogEntryBySourceFile = () => null;
eval(section('function normalizeDirectTopicRef(bundle, ref)', 'function flattenUhfIndexEntries(bundle)'));
eval(section('function viewerUrl(params)', 'function parseUhfTag(tagBody'));
assert.equal(bundleTargetUrl(bundle, {bundleTopic: '999'}), '/?file=Example%2Fhelp.json.gz&topic=999');
assert.equal(bundleTargetUrl(bundle, {topicAlias: 'missing.context'}), '/?file=Example%2Fhelp.json.gz&alias=missing.context');
assert.equal(bundleTargetUrl(bundle, {bundleTopic: '17'}), '/?file=Example%2Fhelp.json.gz&topic=7');
const events = [], errors = [];
const recordStatisticsEvent = event => events.push(event);
eval('globalThis.Manager = class {' + section('    async _openTopicTarget(', '    toggleZoom(') + '}');
const manager = new Manager();
const originalPage = {id: 7}; manager.currentPage = originalPage;
manager._normalizeLineNumber = () => null;
manager.showTopic = () => false;
manager.onError = error => {errors.push(error.message); return Promise.resolve();};
(async () => {
 await manager._openTopicTarget({_tvWindowView: {bundle}}, {bundleTopic: '999'});
 assert.equal(manager.currentPage, originalPage);
 assert.deepEqual(errors, ['Cannot open HELP topic 999.']);
 assert.deepEqual(events, [{event: 'link', result: 'broken'}]);
 manager.showTopic = () => true;
 await manager._openTopicTarget({_tvWindowView: {bundle}}, {bundleTopic: '17'});
 assert.equal(errors.length, 1);
 assert.deepEqual(events.at(-1), {event: 'link', result: 'internal'});
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
    result = subprocess.run([NODE, "-e", script, str(paths[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for alias resolution tests")
def test_numeric_zero_alias_is_preserved_without_overriding_a_real_topic_zero():
    paths = [Path("www/assets/tv-bundle-app.js"), Path("thelpviewer/server/converter/assets/tv-bundle-app.js")]
    assert paths[0].read_bytes() == paths[1].read_bytes()
    script = r'''
const fs=require('node:fs'), assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
eval(source.slice(source.indexOf('function normalizeDirectTopicRef(bundle, ref)'),
                  source.indexOf('function flattenUhfIndexEntries(bundle)')));
const bundle={topics:{'100':{id:100,aliases:{ids:[0,140],strings:['Index']}}}};
assert.equal(normalizeTopicRef(bundle,0),'100');
assert.equal(normalizeTopicRef(bundle,'0'),'100');
assert.equal(normalizeTopicRef(bundle,140),'100');
assert.equal(normalizeTopicRef(bundle,'INDEX'),'100');
assert.equal(normalizeTopicAlias(0),'0');
assert.equal(caseSensitiveTopicAliasKey(0),'0');
for(const value of [null,undefined,''])assert.equal(normalizeTopicRef(bundle,value),null);
bundle.topics['0']={id:0};
assert.equal(normalizeTopicRef(bundle,0),'0');
assert.equal(normalizeTopicRef(bundle,'0'),'0');
'''
    result = subprocess.run([NODE, "-e", script, str(paths[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for alias cursor navigation tests")
def test_alias_cursor_survives_external_navigation_urls_case_and_explicit_line_override():
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a);return source.slice(a,b);}
eval(section('function normalizeDirectTopicRef(bundle, ref)','function flattenUhfIndexEntries(bundle)'));
const bundle={_catalogFile:'target.json.gz',metadata:{quickhelp_databases:[
 {first_topic_id:7,topic_count:1,case_sensitive:true}]},topics:{
 '0':{id:0,aliases:{strings:['winhelp-hash:000004d2'],lines:{'winhelp-hash:000004d2':2}}},
 '7':{id:7,aliases:{ids:[17,0],strings:['CASE.HLP!Detail'],lines:{'17':3,'CASE.HLP!Detail':4,'0':9}}}}};
assert.deepEqual(normalizeTopicTarget(bundle,'WINHELP-HASH:000004D2'),{topic:'0',line:2});
assert.deepEqual(normalizeTopicTarget(bundle,'winhelp-hash:000004d2',5),{topic:'0',line:5});
assert.deepEqual(normalizeTopicTarget(bundle,'0'),{topic:'0',line:null});
assert.deepEqual(normalizeTopicTarget(bundle,17),{topic:'7',line:3});
assert.deepEqual(normalizeTopicTarget(bundle,'case.hlp!Detail'),{topic:'7',line:4});
assert.equal(normalizeTopicTarget(bundle,'CASE.HLP!detail'),null);
assert.equal(normalizeTopicTarget(bundle,'absent'),null);
global.window={location:{pathname:'/'}};
const CONTEXT_HELP_BUNDLE_FILE='context.json',bundleCache=new Map([['target.json.gz',bundle]]);
const findCatalogEntryBySourceFile=()=>({file:'target.json.gz'}),loadBundle=async()=>bundle;
eval(section('function viewerUrl(params)','function parseUhfTag(tagBody'));
assert.equal(bundleTargetUrl(bundle,{topicAlias:'WINHELP-HASH:000004D2'}),'/?file=target.json.gz&topic=0&line=2');
assert.equal(bundleTargetUrl({}, {sourceFile:'target.hlp',topicAlias:'WINHELP-HASH:000004D2'}),'/?file=target.json.gz&topic=0&line=2');
const wrapBundleContent=(_bundle,html)=>html,renderTopicContent=()=> 'TEXT',bundleHeaderLabel=()=> 'HELP';
const recordTopicOpen=()=>{},bundleTopicTitle=()=> 'Topic';
eval('globalThis.Manager=class {'+section('    showTopic(bundle, contextHex','    showHelpContentsTopic(bundle)')
 +section('    async openSourceTopic(','    _focusTopicLine(')+'}');
const manager=new Manager(); manager.history=[];
manager._pushHistory=()=>manager.history.push([manager.currentContextHex,manager.currentLineNumber]);
manager._openWindow=()=>({});manager._focusTopicLine=(_window,line)=>manager.focusedLine=line;
(async()=>{
 assert.equal(await manager.openSourceTopic('target.hlp','WINHELP-HASH:000004D2'),true);
 assert.equal(manager.currentContextHex,'0');assert.equal(manager.currentLineNumber,2);assert.equal(manager.focusedLine,2);
 assert.equal(manager.showTopic(bundle,'case.hlp!Detail'),true);
 assert.equal(manager.currentContextHex,'7');assert.equal(manager.currentLineNumber,4);
 assert.deepEqual(manager.history.at(-1),['0',2]);
 assert.equal(manager.showTopic(bundle,'case.hlp!Detail',6),true);assert.equal(manager.currentLineNumber,6);
 assert.equal(manager.showTopic(bundle,'0'),true);assert.equal(manager.currentLineNumber,null);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-bundle-app.js"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for default HELP view tests")
def test_default_help_prefers_native_root_then_index_then_contents_without_double_history():
    paths = [Path("www/assets/tv-bundle-app.js"), Path("thelpviewer/server/converter/assets/tv-bundle-app.js")]
    assert paths[0].read_bytes() == paths[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a);return source.slice(a,b);}
eval(section('function bundleTopicList(bundle)','function bundleHasNavAction(bundle, action)'));
const wrapBundleContent=(_b,html)=>html,renderBundleIndex=()=> 'INDEX',renderBundleContents=()=> 'CONTENTS';
const bundleHeaderLabel=()=> 'HELP',recordTopicOpen=()=>{};
eval('globalThis.Manager=class {'+section('    showIndex(bundle)','    showTag(bundle, key, value, label')+'}');
function manager(){
 const m=new Manager();m.calls=[];m.history=[];
 m._pushHistory=()=>m.history.push(m.currentView);
 m._openWindow=(bundle,content)=>m.calls.push({view:m.currentView,content,bundle});
 m.onNavigate=label=>m.lastLabel=label;
 m.showTopic=(bundle,ref,line)=>{m._pushHistory();m.currentView='topic';m.currentBundle=bundle;m.calls.push({view:'topic',ref,line,bundle});};
 return m;
}
const index=[{group:'A',entries:[{label:'Alpha',topic_id:7}]}];
const contents=[{label:'Tree',topic_id:7}];
for(const bundle of [
 {metadata:{help_contents_topic_id:0},topics:{'0':{id:0}},index,contents},
 {metadata:{help_contents_topic_id:101},topics:{'101':{id:101}},index,contents:[]},
 {topics:{'9':{id:9,is_help_contents:true}},index,contents},
]){
 const m=manager();m.showDefault(bundle,12);
 assert.deepEqual(m.calls.map(c=>[c.view,c.ref,c.line]),[['topic',String(Object.values(bundle.topics)[0].id),12]]);
 assert.equal(m.history.length,1);assert.equal(m.currentBundle,bundle);
}
for(const bundle of [{topics:{'7':{id:7}},index,contents},{topics:{'7':{id:7}},index,contents:[]}]){
 const m=manager();m.showDefault(bundle);
 assert.deepEqual(m.calls.map(c=>c.view),['index']);assert.equal(m.history.length,1);
 assert.equal(m.currentBundle,bundle);assert.equal(m.lastLabel,'Index');
}
for(const method of ['showDefault','showIndex']){
 const bundle={topics:{'0':{id:0},'7':{id:7}},index:[],contents};
 const m=manager();m[method](bundle);
 assert.deepEqual(m.calls.map(c=>c.view),['contents']);assert.equal(m.history.length,1);
 assert.equal(m.currentBundle,bundle);assert.equal(m.lastLabel,'Contents');
}
for(const tree of [undefined,null,[],{}]){
 const bundle={topics:{'0':{id:0},'7':{id:7}},index:[],contents:tree};
 const m=manager();m.showDefault(bundle);
 assert.deepEqual(m.calls.map(c=>[c.view,c.ref]),[['topic','0']]);assert.equal(m.history.length,1);
}
const empty=manager();empty.showDefault({topics:{},index:[],contents:[]});
assert.deepEqual(empty.calls.map(c=>c.view),['index']);assert.equal(empty.history.length,1);
const explicit=manager();explicit.showIndex({metadata:{help_contents_topic_id:0},topics:{'0':{id:0}},index,contents});
assert.deepEqual(explicit.calls.map(c=>c.view),['index']);assert.equal(explicit.history.length,1);
'''
    result = subprocess.run([NODE, "-e", script, str(paths[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the browser asset regression test")
def test_external_help_links_prefer_the_current_product_collection():
    asset_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    assert asset_paths[0].read_bytes() == asset_paths[1].read_bytes()

    script = r'''
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function normalizeSourceFileName(value)");
const end = source.indexOf("function bundleLoadingLabel(value", start);
if (start < 0 || end < 0) { throw new Error("catalog resolver source not found"); }
let catalogData = [
    { group: "Microsoft CodeView 4.0", file: "Microsoft CodeView 4.0/cv.json.gz", source_file: "CV.HLP" },
    { group: "Microsoft QuickBASIC Extended 7.1", file: "Microsoft QuickBASIC Extended 7.1/bc.json.gz", source_file: "BC.HLP", product: "basic-pds", version: "7.1" },
    { group: "Microsoft QuickBASIC Extended 7.1", file: "Microsoft QuickBASIC Extended 7.1/cv.json.gz", source_file: "CV.HLP", product: "basic-pds", version: "7.1" },
    { group: "Microsoft QuickC, C, and C++ 6.0", file: "Microsoft QuickC, C, and C++ 6.0/cv.json.gz", source_file: "CV.HLP", product: "msc", version: "6.0" },
];
eval(source.slice(start, end));
const preferred = { _catalogFile: "Microsoft QuickBASIC Extended 7.1/bc.json.gz" };
const resolved = findCatalogEntryBySourceFile("cv.hlp", preferred);
const missing = findCatalogEntryBySourceFile("NMAKE.HLP", preferred);
catalogData.push({ group: "HelpPC 2.10", file: "HelpPC 2.10/misc.json.gz", source_file: "MISC.TXT" });
const wrongFormat = findCatalogEntryBySourceFile("MISC.HLP", preferred);
catalogData.push({ group: "Microsoft QuickBASIC Extended 7.1",
    file: "Microsoft QuickBASIC Extended 7.1/utils.json.gz", source_file: "UTILS.HLP",
    source_files: ["UTILS.HLP", "lib.hlp", "nmake.hlp", "misc.hlp"], product: "basic-pds", version: "7.1" });
const logicalDatabase = findCatalogEntryBySourceFile("MISC.HLP", preferred);
const noStemAlias = findCatalogEntryBySourceFile("misc", preferred);
const ambiguous = findCatalogEntryBySourceFile("CV.HLP");
const foreignCollection = findCatalogEntryBySourceFile("CV.HLP", { _catalogFile: "HelpPC 2.10/misc.json.gz" });
process.stdout.write(JSON.stringify({ resolved: resolved && resolved.file, missing,
    wrongFormat, logicalDatabase: logicalDatabase && logicalDatabase.file,
    noStemAlias, ambiguous, foreignCollection }));
'''
    result = subprocess.run(
        [NODE, "-e", script, str(asset_paths[0])],
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = json.loads(result.stdout)

    assert resolved["resolved"] == "Microsoft QuickBASIC Extended 7.1/cv.json.gz"
    assert resolved["missing"] is None
    assert resolved["wrongFormat"] is None
    assert resolved["logicalDatabase"] == "Microsoft QuickBASIC Extended 7.1/utils.json.gz"
    assert resolved["noStemAlias"] is None
    assert resolved["ambiguous"] is None
    assert resolved["foreignCollection"] is None


@pytest.mark.skipif(NODE is None, reason="Node.js is required for HELP navigation tests")
def test_external_missing_topic_or_file_does_not_open_an_arbitrary_page():
    script = r'''
const fs = require('node:fs'), assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
function section(start, end) {
    const offset = source.indexOf(start), limit = source.indexOf(end, offset);
    if (offset < 0 || limit < 0) throw new Error('Missing source: ' + start);
    return source.slice(offset, limit);
}
let catalogData = [{ file: 'Product/help.json.gz', source_file: 'HELP.HLP', group: 'Product' }];
const bundle = { _catalogFile: 'Product/help.json.gz', metadata: { source: { format: 'quickhelp' } },
    topics: { '0': { id: 0 }, '7': { id: 7, aliases: { strings: ['real.alias'] } } } };
eval(section('function normalizeSourceFileName(value)', 'function bundleLoadingLabel(value'));
eval(section('function normalizeDirectTopicRef(bundle, ref)', 'function flattenUhfIndexEntries(bundle)'));
eval(section('function resolveMissingSourceTopicFallback(bundle', 'function isUhfCodeStart(line)'));
function bundleSourceFormat(value) { return value.metadata.source.format; }
function bundleTopicList(value) { return Object.values(value.topics); }
async function loadBundle(file) { assert.equal(file, 'Product/help.json.gz'); return bundle; }
function bundleTopicFallbackRef() { throw new Error('Must not choose the first arbitrary topic'); }
const method = section('    async openSourceTopic(', '    _normalizeLineNumber(value)');
eval('globalThis.Manager = class {' + method + '}');
const manager = new Manager();
manager.currentBundle = bundle;
const opened = [];
manager.showTopic = (bundle, ref) => { opened.push(['topic', normalizeTopicRef(bundle, ref)]); return true; };
manager.showContents = () => opened.push(['contents']);
manager.showIndex = () => opened.push(['index']);
(async () => {
    assert.equal(await manager.openSourceTopic('HELP.HLP', 'missing.context'), false);
    assert.equal(await manager.openSourceTopic('MISSING.HLP', 'real.alias', null, bundle), false);
    assert.equal(await manager.openSourceTopic('HELP.HLP', 'missing.contents'), false);
    assert.deepEqual(opened, []);
    assert.equal(await manager.openSourceTopic('HELP.HLP', 'real.alias'), true);
    assert.deepEqual(opened.pop(), ['topic', '7']);
    assert.equal(await manager.openSourceTopic('HELP.HLP', '0'), true);
    assert.deepEqual(opened.pop(), ['topic', '0']);
    assert.equal(await manager.openSourceTopic('HELP.HLP', ''), true);
    assert.deepEqual(opened.pop(), ['contents']);
    assert.equal(await manager.openSourceTopic('HELP.HLP', '-9997'), true);
    assert.deepEqual(opened.pop(), ['index']);
    assert.equal(await manager.openSourceTopic('HELP.HLP', '!hv'), true);
    assert.deepEqual(opened.pop(), ['contents']);
    const scoped = { topics: {
        '0': { id: 0, aliases: { strings: ['first', 'FIRST.HLP!first'] } },
        '1': { id: 1, aliases: { strings: ['missing', 'SECOND.HLP!missing'] } },
    } };
    assert.equal(normalizeTopicRef(scoped, 'FIRST.HLP!missing'), null);
    assert.equal(normalizeTopicRef(scoped, 'second.hlp!missing'), '1');
    const sensitive = { metadata: { quickhelp_databases: [
        { first_topic_id: 0, topic_count: 1, case_sensitive: true },
    ] }, topics: { '0': { id: 0, aliases: { strings: ['MIXED', 'CASE.HLP!MIXED'] } } } };
    assert.equal(normalizeTopicRef(sensitive, 'mixed'), null);
    assert.equal(normalizeTopicRef(sensitive, 'case.hlp!mixed'), null);
    assert.equal(normalizeTopicRef(sensitive, 'case.hlp!MIXED'), '0');
    const container = { metadata: { source: { format: 'quickhelp' }, quickhelp_databases: [
        { name: 'FIRST.HLP', first_topic_id: 0, topic_count: 1 },
        { name: 'SECOND.HLP', first_topic_id: 1, topic_count: 2 },
    ] }, topics: { '0': { id: 0, is_help_contents: true }, '1': { id: 1 },
        '2': { id: 2, is_help_contents: true } } };
    assert.deepEqual(resolveMissingSourceTopicFallback(container, 'SECOND.HLP', 'second.hlp!HV'),
        { type: 'topic', ref: '2' });
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-bundle-app.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for public HELP link tests")
def test_public_help_links_resolve_topics_aliases_and_original_source_files():
    script = r'''
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
function section(start, end) {
    return source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
}
global.window = { location: { pathname: '/' } };
const CONTEXT_HELP_BUNDLE_FILE = '../assets/tv-context-help.json';
const bundleCache = new Map();
const file = 'Borland C++ 3.0/tchelp.json.gz';
let catalogData = [
    { file, group: 'Borland C++ 3.0', source_file: 'TCHELP.TCH' },
    { file: 'Other/asm.json.gz', group: 'Other', source_file: 'ASM.TXT' },
    { file: 'HelpPC/asm.json.gz', group: 'HelpPC', source_file: 'ASM.TXT' },
    { file: 'HelpPC/c.json.gz', group: 'HelpPC', source_file: 'C.TXT' },
];
const bundle = { _catalogFile: file, topics: {
    '0': { id: 0, aliases: { strings: ['zero'] } },
    '7': { id: 7, aliases: { strings: ['printf'] } },
} };
const escapeHtml = (value) => String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const TVView = { _controlAttrs({ commandData }) {
    return Object.fromEntries(Object.entries(commandData).map(([key, value]) =>
        ['data-tv-' + key.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase(), value]));
} };
class TVMenuItem { constructor(name, command) { this.name = name; this.command = command; } }
class TVOutline {}
eval(section('function normalizeSourceFileName(value)', 'function bundleLoadingLabel(value'));
eval(section('function normalizeDirectTopicRef(bundle, ref)', 'function flattenUhfIndexEntries(bundle)'));
eval(section('function parseUhfLinkTargetSpec(rawTarget)', 'function bundleFrozenRows(bundle, topic)'));
eval(section('function buildBundleTargetData(target)', '// ── Topic navigation'));
eval(section('function renderIndexSection(anchor', 'class TVContentsOutline'));
eval(section('class TVContentsOutline', 'function renderBundleContents(bundle)')
    + '\nglobalThis.makeOutline = () => new TVContentsOutline();');
    eval(section('function uhfTextScreenForLine(', 'function normalizedTopicTags(topic)'));
const isUhfCodeStart = () => false;
eval(section('const menuActions = new WeakMap()', 'function menuFromItems(items)')
    + '\nglobalThis.makeItem = (command, action) => withMenuAction(new TVBundleMenuItem("item", command), action);');
function expect(actual, expected) {
    if (actual !== expected) { throw new Error(JSON.stringify({ actual, expected })); }
}
const url = '/?file=Borland+C%2B%2B+3.0%2Ftchelp.json.gz';
expect(bundleTargetUrl(bundle, { bundleTopic: '007' }), url + '&topic=7');
expect(bundleTargetUrl(bundle, { topicAlias: 'PRINTF', topicLine: '12' }), url + '&topic=7&line=12');
expect(bundleTargetUrl(bundle, { bundleTopic: 0 }), url + '&topic=0');
expect(bundleTargetUrl(bundle, { topicLine: '4' }, bundle.topics['7']), url + '&topic=7&line=4');
expect(bundleTargetUrl(bundle, { topicAlias: 'missing' }), url + '&alias=missing');
expect(bundleTargetUrl(bundle, { sourceFile: 'missing.hlp', bundleTopic: '7' }), '#');
expect(bundleTargetUrl({ _catalogFile: CONTEXT_HELP_BUNDLE_FILE }, { bundleTopic: '7' }), '#');
const c = { _catalogFile: 'HelpPC/c.json.gz', topics: {} };
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', bundleTopic: '8' }), '/?file=HelpPC%2Fasm.json.gz&topic=8');
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', bundleTopic: 0 }), '/?file=HelpPC%2Fasm.json.gz&topic=0');
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', topicAlias: 'mov' }), '/?file=HelpPC%2Fasm.json.gz&alias=mov');
bundleCache.set('HelpPC/asm.json.gz', { topics: { '8': { id: 8, aliases: { strings: ['mov'] } } } });
expect(bundleTargetUrl(c, { sourceFile: 'ASM.TXT', topicAlias: 'mov' }), '/?file=HelpPC%2Fasm.json.gz&topic=8');
const inline = renderUhfInline('[link:alias=printf,line=12]printf[/link]', bundle);
if (!inline.includes('href="' + escapeHtml(url + '&topic=7&line=12') + '"')
    || !inline.includes('data-tv-topic-alias="printf"') || !inline.includes('data-tv-topic-line="12"')) {
    throw new Error('inline links lost their real URL or TVEvent target');
}
const index = renderIndexSection('P', 'P', [{ label: 'printf', topic_id: 7 }], bundle);
if (!index.includes('href="' + escapeHtml(url + '&topic=7') + '"')) {
    throw new Error('index topic did not have a real URL');
}
const outline = makeOutline();
outline.bundle = bundle;
const contents = outline.renderNodeContent({ label: 'printf', alias: 'printf' });
const more = renderUhfTopicLines({ content: ['<more>'], nav: { Down: { topic_id: 7 } } }, bundle).join('');
if (!contents.includes('href="' + escapeHtml(url + '&topic=7') + '"')
    || !more.includes('href="' + escapeHtml(url + '&topic=7') + '"')) {
    throw new Error('Contents or <more> did not expose a real topic URL');
}
expect(makeItem('bundle-open', { value: file }).getUrl(), url);
expect(makeItem('doc-open', { value: 'Formats/A & B.md' }).getUrl(), '/?doc=Formats%2FA+%26+B.md');
expect(makeItem('menu-link', { bundle, topicAlias: 'printf' }).getUrl(), url + '&topic=7');
window.location.pathname = '/index.html';
expect(bundleTargetUrl(bundle, { bundleTopic: '7' }), '/index.html' + url.slice(1) + '&topic=7');
'''
    result = subprocess.run(
        [NODE, "-e", script, "www/assets/tv-bundle-app.js"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for HELP page navigation tests")
def test_status_page_navigation_uses_tvevent_and_the_active_topic_targets():
    script = r'''
const fs = require('node:fs'), assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
function section(start, end, from = 0) {
    const offset = source.indexOf(start, from), limit = source.indexOf(end, offset);
    if (offset < 0 || limit < 0) throw new Error('Missing source: ' + start);
    return source.slice(offset, limit);
}
const TV = { evCommand: 1 }, evKeyDown = 2;
class TVProgram { handleEvent() {} clearEvent(event) { event.what = 0; } }
class TVMenuItem {}
class TVStatusItem {
    constructor(text, keyCode, command, param) { Object.assign(this, {text, keyCode, command, param}); }
}
class TVRect {}
class TVStatusLine {
    constructor(bounds, defs) { this.items = defs.items; }
    draw() { globalThis.statusItems = this.items.filter(item => item instanceof TVStatusItem); return ''; }
    bindRoot() {}
}
const kbF3 = 3, kbAltF3 = 4, kbF1 = 5;
const menuActions = new WeakMap();
const renderHotkeyMarkup = text => text, escapeHtml = text => text;
const NewStatusKey = (...args) => new TVStatusItem(...args);
const NewStatusDef = (min, max, items) => ({items});
const bundleCanShowIndex = () => false, bundleCanShowHelpContentsTopic = () => false,
      bundleCanShowContents = () => true;
globalThis.document = {querySelector() {return {};}};
const normalizeTopicRef = (bundle, ref) => String(ref);
eval(section('function buildBundleTargetData(target)', 'function renderHtmlAttributes(attrs)'));
eval(section('function findTopicByHex(bundle, contextHex)', 'function renderTopicContent(bundle, topic)'));
eval('globalThis.App = class extends TVProgram {'
    + section('    handleEvent(event) {\n        super.handleEvent(event);', '    async _openMenuLink(action)',
        source.indexOf('class TVBundleApp extends TVProgram'))
    + section('    _activeHelpWindow()', '    _activeStatusHint()') + '}');
const bundle = { topics: {
    '2': { nav: { Next: {topic_id: 81} } },
    '81': { nav: { Prev: {topic_id: 2}, Next: {topic_id: 82} } },
    '82': { nav: { Prev: {topic_id: 81} } },
    '0': { nav: { Next: {file: 'OTHER.HLP', alias: 'page.two', line: 12} } },
    '1': { nav: { Prev: {topic_id: 0}, Next: {action: 'contents'} } },
} };
const view = {bundle, currentView: 'topic', currentTopic: '2'};
const windowEl = {isConnected: true, _tvWindowView: view};
const opened = [];
const app = new App();
app.dialogManager = {activeTarget: 'help:first', windows: new Map([['help:first', windowEl]])};
app.windowManager = {openWindows: new Map([['first', windowEl]]), currentBundle: bundle,
    _openTopicTarget(window, target) { opened.push({window, target}); }};
app._activeStatusHint = () => '';
app._bindStatusButtons = () => {};
const navigationItems = () => {
    app._updateStatusLine();
    return statusItems.filter(item => item.command === 'bundle-navigation');
};
const click = item => {
    const event = {what: TV.evCommand, command: item.command, infoPtr: item};
    app.handleEvent(event); assert.equal(event.what, 0);
};
assert.deepEqual(navigationItems().map(item => item.text), ['Next']);
click(navigationItems()[0]);
assert.deepEqual(opened.pop(), {window: windowEl, target: {bundleTopic: '81'}});
view.currentTopic = '81';
assert.deepEqual(navigationItems().map(item => item.text), ['Previous', 'Next']);
click(navigationItems()[0]);
assert.equal(opened.pop().target.bundleTopic, '2');
view.currentTopic = '82';
assert.deepEqual(navigationItems().map(item => item.text), ['Previous']);
app._navigateHelpPage('Next'); assert.equal(opened.length, 0);
view.currentTopic = '1';
assert.deepEqual(navigationItems().map(item => item.text), ['Previous']);
click(navigationItems()[0]); assert.equal(opened.pop().target.bundleTopic, '0');
view.currentTopic = '0';
click(navigationItems()[0]);
assert.deepEqual(opened.pop().target, {sourceFile: 'OTHER.HLP', topicAlias: 'page.two', topicLine: '12'});
// A different active HELP window must win over the manager's last bundle/topic.
const other = {isConnected: true, _tvWindowView: {bundle: {topics: {'7': {nav: {Next: {topic_id: 19}}}}},
    currentView: 'topic', currentTopic: '7'}};
app.dialogManager.windows.set('help:other', other);
app.dialogManager.activeTarget = 'help:other';
click(navigationItems()[0]);
assert.deepEqual(opened.pop(), {window: other, target: {bundleTopic: '19'}});
for (const target of ['calculator', 'doc:README.md', 'dos:prompt', '']) {
    app.dialogManager.activeTarget = target;
    assert.deepEqual(navigationItems(), []);
    app._navigateHelpPage('Next'); assert.equal(opened.length, 0);
}
app.dialogManager.activeTarget = 'help:first';
for (const mode of ['index', 'contents', 'tag']) {
    view.currentView = mode;
    assert.deepEqual(navigationItems(), []);
    app._navigateHelpPage('Next'); assert.equal(opened.length, 0);
}
view.currentView = 'topic';
windowEl.isConnected = false;
assert.deepEqual(navigationItems(), []);
app._navigateHelpPage('Next'); assert.equal(opened.length, 0);
windowEl.isConnected = true;
view.currentTopic = 'missing';
assert.deepEqual(navigationItems(), []);
app._navigateHelpPage('Next'); assert.equal(opened.length, 0);
app._navigateHelpPage('Down'); assert.equal(opened.length, 0);
'''
    result = subprocess.run([NODE, "-e", script, "www/assets/tv-bundle-app.js"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
