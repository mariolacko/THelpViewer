"""Phase-local progress must never turn a downloaded file into an installed one."""

from pathlib import Path
import shutil
import subprocess

import pytest

from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.processing import report_progress, stage_progress
from thelpviewer.server.processing import observe_progress
from thelpviewer.server.archives import core


def test_shared_queue_exposes_unknown_and_known_stage_progress_until_owner_finishes():
    queue = OnlineDownloader()
    try:
        queue.begin("help", [{"id": "reference", "label": "Reference", "byte_progress": False}])
        with queue.context("help", "reference"):
            for stage, values, expected in (
                ("download", {"received": 100, "bytes_total": 100}, 100),
                ("extract", {}, None),
                ("convert", {"processed": 1, "total": 4}, 25),
                ("publish", {}, None),
            ):
                report_progress("Current phase", stage=stage, **values)
                status = queue.snapshot(private=True)
                row = status["items"][0]
                assert status["active"] and row["state"] == "running"
                assert row["stage"] == stage and row["stage_percent"] == expected
                assert row["percent"] < 100
            queue.update("help", "reference", phase="Retry in 5s")
            assert queue.snapshot(private=True)["items"][0]["stage_percent"] is None
        queue.update("help", "reference", state="done", phase="Published", percent=100)
        queue.finish("help")
        assert not queue.snapshot(private=True)["active"]
        assert queue.snapshot(private=True)["items"][0]["state"] == "done"
        assert not queue.snapshot()["items"]
    finally:
        queue.close()


def test_unknown_totals_have_no_stage_percentage_and_transfer_counts_do_not_leak_into_conversion():
    assert stage_progress("download", received=100) == {"stage": "download", "stage_percent": None}
    assert stage_progress("convert", received=100, bytes_total=100) == {"stage": "convert", "stage_percent": None}
    assert stage_progress("extract", processed=3, total=4)["stage_percent"] == 75


@pytest.mark.parametrize("tool", ["unar", "7zz"])
def test_external_extractor_reports_its_own_progress_without_finishing_queue(tmp_path, monkeypatch, tool):
    events = []
    def run(command, destination, limits, *, progress):
        if tool == "unar":
            assert "-quiet" not in command
            for part in (b"archive: 7-Zip\n  first (10 B)... O", b"K.\n", b"  second (30 B)... OK.\n"):
                progress(part)
        else:
            assert "-bsp1" in command
            for part in (b"  2", b"5%\x08\x08\x08", b" 50%\r"):
                progress(part)
        return True, ""
    monkeypatch.setattr(core, "_run_tool", run)
    function = core._extract_with_unar if tool == "unar" else core._extract_with_7zz
    options = {"entries": 4} if tool == "unar" else {}
    queue = OnlineDownloader()
    try:
        queue.begin("dos", [{"id": "package", "label": "Package"}])
        with queue.context("dos", "package"), observe_progress(lambda event: (
                events.append(event), queue.update("dos", "package", **event))):
            assert function(tmp_path / "source.7z", tmp_path, core.ExtractorTools("unar", "lsar", "7zz"),
                            **options) == (True, "")
        assert [event["stage_percent"] for event in events] == [0, 25, 50]
        row = queue.snapshot(private=True)["items"][0]
        assert row["stage"] == "extract" and row["stage_percent"] == 50
        assert row["state"] != "done"
    finally:
        queue.close()


def test_tool_output_progress_is_streamed_before_exit(tmp_path):
    import sys
    chunks = []
    success, _message = core._run_tool([sys.executable, "-c",
        "import sys,time; print('25%',flush=True); time.sleep(.1); print('50%',flush=True)"],
        tmp_path, core.ExtractionLimits(timeout=5), progress=chunks.append)
    assert success and b"25%" in chunks[0] and b"50%" in b"".join(chunks)


def test_tool_failure_diagnostic_keeps_actual_error_not_success_listing(tmp_path):
    import sys
    success, message = core._run_tool([sys.executable, "-c",
        "print('file... OK.\\n'*1000); "
        "print('\\x1b[31mERROR: Unsupported Method : last.bin\\x1b[0m\\x08'); "
        "raise SystemExit(2)"], tmp_path, core.ExtractionLimits(timeout=5))
    assert not success
    assert message == "ERROR: Unsupported Method : last.bin"


@pytest.mark.parametrize("tool", ["unar", "7zz"])
def test_real_external_archive_progress_reaches_100_only_after_validation(tmp_path, tool):
    if not shutil.which(tool) or (tool == "unar" and not shutil.which("lsar")):
        pytest.skip("External archive tool required")
    # Unsupported ZIP method selection normally reaches this branch; a 7z
    # container lets us exercise it without mocking the extractor itself.
    sevenzip = shutil.which("7zz") or shutil.which("7z")
    if not sevenzip:
        pytest.skip("7-Zip needed to create the fixture")
    source = tmp_path / "text.txt"
    source.write_text("archive payload")
    archive = tmp_path / "source.7z"
    subprocess.run([sevenzip, "a", str(archive), source.name], cwd=tmp_path,
                   check=True, capture_output=True)
    tools = core.ExtractorTools(shutil.which("unar"), shutil.which("lsar"), None) if tool == "unar" else (
        core.ExtractorTools(None, None, sevenzip))
    events = []
    with observe_progress(events.append):
        result = core.extract_file(archive, tmp_path / "expanded", tools)
    assert result.files[0].read_text() == "archive payload"
    assert events[-1]["stage"] == "extract" and events[-1]["stage_percent"] == 100
    assert all(event["stage_percent"] is None or 0 <= event["stage_percent"] <= 100 for event in events)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js required")
def test_same_unicode_stage_rendering_in_menu_caption_and_downloads_list():
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
class TVDialog {}
const source=fs.readFileSync('www/assets/tv-dialogs.js','utf8');
eval(source.slice(source.indexOf('class TVProgressDialog extends'),source.indexOf('class TVSearchDialog extends'))
    +'\nglobalThis.Progress=TVProgressDialog;');
const row={state:'running',stage:'download',stage_percent:100,percent:35};
assert.equal(Progress.downloadMarker(row),'↓ 100%');
row.stage='extract';row.stage_percent=null;
assert.equal(Progress.downloadMarker(row),'▣');
row.stage='convert';row.stage_percent=25;
assert.equal(Progress.downloadMarker(row),'⚙ 25%');
row.stage='publish';row.stage_percent=null;
assert.equal(Progress.downloadCaption({active:true,errors:0,items:[row]}),'⚙');
row.state='done';
assert.equal(Progress.downloadSymbol(row),'✓');
assert.equal(Progress.downloadCaption({active:false,errors:0,items:[row]}),'✓');
assert.notEqual(Progress.downloadCaption({active:true,errors:0,items:[row]}),'✓');
row.state='error';
assert.equal(Progress.downloadCaption({active:false,errors:1,items:[row]}),'!');
row.state='pending';
assert.equal(Progress.downloadMarker(row),'·');
assert.equal(Progress.downloadCaption({active:true,errors:0,items:[row]}),'…');
const downloading={state:'running',stage:'download',stage_percent:50};
const extracting={state:'running',stage:'extract',stage_percent:null};
const converting={state:'running',stage:'convert',stage_percent:25};
assert.equal(Progress.downloadCaption({active:true,errors:0,items:[downloading,extracting,converting]}),'↓ 50% ▣ ⚙ 25%');
assert.equal(Progress.downloadCaption({active:true,errors:0,items:[downloading,{...downloading,stage_percent:null}]}),'↓');
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    for name in ("tv-dialogs.js", "tv-shell.js"):
        assert (Path("www/assets") / name).read_bytes() == (Path("thelpviewer/server/converter/assets") / name).read_bytes()
