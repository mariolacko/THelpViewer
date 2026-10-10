from pathlib import Path
import shutil
import subprocess

import pytest


ASSET_PATHS = (
    Path("www/assets/tv-bundle-app.js"),
    Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
)


def test_bundle_statistics_cover_requested_aggregate_signals():
    source = ASSET_PATHS[1].read_text(encoding="utf-8")

    assert 'event: "session_end"' in source
    assert 'event: "dialog_open"' in source
    assert 'event: "tool_open"' in source
    assert 'event: "search"' in source
    assert 'event: "link"' in source
    assert 'event: "view_duration"' in source
    assert 'dialog instanceof TVGameDialog' in source
    assert 'session.view.getGameResult()' in source
    assert 'scope: "help"' in source
    assert 'scope: "document"' in source
    assert 'scope: "dialog"' in source
    assert 'scope: "game"' in source
    assert "GAME_DIALOG_NAMES" not in source
    assert "recordHelpOpen" not in source
    assert "this.dialogManager.windows.forEach" in source
    assert 'document.visibilityState === "visible"' in source
    assert 'metric: "page_ttfb"' in source
    assert 'metric: "page_load"' in source
    assert 'metric: "lcp"' in source
    assert 'metric: "cls"' in source
    assert 'metric: "inp"' in source
    assert 'event: "help_performance"' in source
    assert 'recordHelpPerformance("load"' in source
    assert 'recordHelpPerformance("decompress"' in source
    assert 'recordHelpPerformance("render"' in source
    assert "statisticsOrientation()" in source
    assert "statisticsPointer()" in source
    assert '"(prefers-reduced-motion: reduce)"' in source


def test_search_telemetry_never_sends_the_query_text():
    source = ASSET_PATHS[1].read_text(encoding="utf-8")
    search_calls = [
        line.strip()
        for line in source.splitlines()
        if 'event: "search"' in line
    ]

    assert search_calls
    assert all("query" not in line for line in search_calls)


def test_statistics_asset_mirror_is_current():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_managed_dos_statistics_exclude_boot_pause_hidden_and_inactive_intervals():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8'),events=[];
let now=0;
const document={visibilityState:'visible'};
const context={document,performance:{now:()=>now},TVGameDialog:class{},
 recordStatisticsEvent:event=>events.push(event),statisticsDialogName:name=>name};
const app={statisticsTargets:new Map(),dialogManager:{dialogs:new Map(),windows:new Map(),activeTarget:'dos:prompt'}};
for(const name of ['_statisticsTarget','_startStatisticsTarget','_pauseStatisticsTarget','_finishStatisticsTarget','_syncStatisticsLifecycle','_finishStatisticsTargets']){
 const start=source.indexOf('    '+name+'(');
 assert.ok(start>=0);
 const tail=source.slice(start),next=tail.slice(1).search(/\n    (?:async )?\w+\(/)+1;
 app[name]=vm.runInNewContext('({'+tail.slice(0,next)+'}).'+name,context);
}
const view={view:{ci:null},busy:true,paused:false};
app.dialogManager.windows.set('dos:prompt',{isConnected:true,_tvWindowView:view});
app._syncStatisticsLifecycle(); // Opening counts even before the emulator boots.
now=2000;view.view.ci={};view.busy=false;app._syncStatisticsLifecycle();
now=5000;view.paused=true;app._syncStatisticsLifecycle();
now=20000;view.paused=false;app._syncStatisticsLifecycle();
now=21000;document.visibilityState='hidden';app._syncStatisticsLifecycle();
now=29000;document.visibilityState='visible';app.dialogManager.activeTarget='other';app._syncStatisticsLifecycle();
now=31000;app.dialogManager.activeTarget='dos:prompt';app._syncStatisticsLifecycle();
now=33000;app.dialogManager.windows.delete('dos:prompt');app._syncStatisticsLifecycle();
assert.equal(events.length,2);
assert.equal(events[0].event,'tool_open');assert.equal(events[0].name,'dos-prompt');
assert.equal(events[1].event,'view_duration');assert.equal(events[1].scope,'tool');
assert.equal(events[1].duration_ms,6000);assert.equal(app.statisticsTargets.size,0);
app.dialogManager.windows.set('dos:prompt',{isConnected:true,_tvWindowView:view});
app._syncStatisticsLifecycle();app._finishStatisticsTargets();
const beforeExit=events.length;
document.visibilityState='hidden';app._syncStatisticsLifecycle();app._finishStatisticsTargets();
assert.equal(events.length,beforeExit); // Exit must not reopen counters on visibilitychange.
'''
    result = subprocess.run([shutil.which("node"), "-e", script, str(ASSET_PATHS[0])],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
