"""Phase-local progress must never turn a downloaded file into an installed one."""

from pathlib import Path
import shutil
import subprocess
import threading

import pytest

from thelpviewer.server.downloader.online import OnlineDownloader
from thelpviewer.server.processing import report_progress, stage_progress
from thelpviewer.server.processing import observe_progress
from thelpviewer.server.archives import core
from thelpviewer.server.jobs import JobStore


@pytest.mark.parametrize("phase", ["Waiting for processing", "Awaiting installation", "Awaiting publication"])
def test_waiting_stays_unfinished_until_published_and_survives_restart(tmp_path, phase):
    journal = JobStore(tmp_path / "jobs.sqlite3")
    queue = OnlineDownloader(journal)
    try:
        queue.begin("dos", [{"id": "package", "label": "Package", "byte_progress": False}])
        queue.update("dos", "package", state="waiting", percent=99, phase=phase, stage="install")
        queue.finish_if_idle("dos")
        queue.finish("dos")  # Neither a quiet pipeline nor finish is a publication receipt.
        status = queue.snapshot(private=True)
        assert status["active"] and status["percent"] == 99
        assert status["items"][0]["state"] == "waiting"
        restored = OnlineDownloader(journal)
        try:
            row = restored.snapshot(private=True)["items"][0]
            assert row["state"] == "pending" and row["phase"] == "Interrupted; awaiting recovery"
        finally:
            restored.close()
        queue.reconcile("dos", {"package"}, completed={"package"}, phase="Installed")
        queue.finish("dos")
        assert not queue.snapshot(private=True)["active"]
        assert queue.snapshot(private=True)["items"][0]["state"] == "done"
    finally:
        queue.close()


@pytest.mark.parametrize("reconcile", [False, True])
def test_waiting_publication_becomes_blocked_on_failure(reconcile):
    queue = OnlineDownloader()
    try:
        queue.begin("dos", [{"id": "package", "label": "Package"}])
        queue.update("dos", "package", state="waiting", phase="Awaiting publication", percent=99)
        if reconcile:
            queue.reconcile("dos", {"package"}, incomplete={"package"})
        queue.finish("dos", error="Publication failed")
        rows = queue.snapshot(private=True)["items"]
        assert next(row for row in rows if row["id"] == "dos:package")["state"] == "blocked"
        assert all(row["state"] != "done" for row in rows)
        assert not queue.snapshot(private=True)["active"]
    finally:
        queue.close()


def test_shared_scheduler_reports_waiting_before_http_and_local_processing():
    queue = OnlineDownloader()
    releases = [threading.Event(), threading.Event()]
    started = [threading.Event(), threading.Event()]
    blockers = []
    try:
        def blocking_processor():
            started[1].set()
            assert releases[1].wait(5)
        blockers = [queue.enqueue_processing(blocking_processor) for _ in range(3)]
        assert started[1].wait(2)
        queue.begin("dos", [{"id": "first", "label": "First"}, {"id": "second", "label": "Second"}])
        def first():
            started[0].set()
            assert releases[0].wait(5)
        with queue.context("dos", "first"):
            downloading = queue.enqueue(first, source="https://same.test/first.zip")
        assert started[0].wait(2)
        with queue.context("dos", "second"):
            waiting = queue.enqueue(lambda: "downloaded", source="https://same.test/second.zip")
        rows = {row["id"]: row for row in queue.snapshot(private=True)["items"]}
        assert rows["dos:first"]["state"] == "running"
        assert rows["dos:second"]["state"] == "waiting"
        assert rows["dos:second"]["phase"] == "Waiting for download"
        releases[0].set()
        downloading.result(timeout=2)
        assert waiting.result(timeout=2) == "downloaded"
        with queue.context("dos", "second"):
            queued_extract = queue.enqueue_processing(lambda: queue.snapshot(private=True))
        row = next(row for row in queue.snapshot(private=True)["items"] if row["id"] == "dos:second")
        assert row["state"] == "waiting" and row["phase"] == "Waiting for processing"
        releases[1].set()
        status = queued_extract.result(timeout=2)
        row = next(row for row in status["items"] if row["id"] == "dos:second")
        assert row["state"] == "running" and row["phase"] == "Processing"
    finally:
        for release in releases:
            release.set()
        for future in blockers:
            future.result(timeout=5)
        queue.close()


def test_finish_with_recorded_failure_does_not_leave_waiting_work_running():
    queue = OnlineDownloader()
    try:
        queue.begin("dos", [{"id": "bad", "label": "Bad"}, {"id": "prepared", "label": "Prepared"}])
        queue.update("dos", "bad", state="error", error="Cannot extract")
        queue.update("dos", "prepared", state="waiting", phase="Awaiting publication", percent=99)
        queue.finish("dos")
        status = queue.snapshot(private=True)
        assert not status["active"] and status["errors"] == 1
        assert {row["state"] for row in status["items"]} == {"error", "blocked"}
    finally:
        queue.close()


def test_retry_cooldown_reports_waiting_even_with_domain_status_callback(monkeypatch):
    from urllib.error import HTTPError
    from thelpviewer.server.downloader.transport import read_request
    queue = OnlineDownloader()
    states = []
    class Opener:
        calls = 0
        def open(self, _request, timeout):
            self.calls += 1
            if self.calls == 1:
                raise HTTPError("https://source.test/archive", 429, "Too many requests", {"Retry-After": "1"}, None)
            import io
            response = io.BytesIO(b"archive")
            response.headers = {"Content-Length": "7"}
            response.url = "https://source.test/archive"
            return response
    def sleep(_seconds):
        row = queue.snapshot(private=True)["items"][0]
        states.append((row["state"], row["phase"], row["stage_percent"]))
    monkeypatch.setattr("thelpviewer.server.downloader.transport.time.sleep", sleep)
    try:
        queue.begin("dos", [{"id": "package", "label": "Package"}])
        with queue.context("dos", "package"):
            read_request(Opener(), "https://source.test/archive", 20,
                on_status=lambda phase: queue.update("dos", "package", state="running", phase=phase))
        assert states == [("waiting", "Rate limited (HTTP 429), retry in 1s", None)]
    finally:
        queue.close()


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
assert.equal(Progress.downloadCaption({active:true,percent:35,errors:0,items:[row]}),'⚙ 35%');
row.state='done';
assert.equal(Progress.downloadSymbol(row),'✓');
assert.equal(Progress.downloadCaption({active:false,errors:0,items:[row]}),'✓');
assert.equal(Progress.downloadCaption({active:true,percent:100,errors:0,items:[row]}),'⚙ 99%');
row.state='error';
assert.equal(Progress.downloadCaption({active:false,errors:1,items:[row]}),'!');
row.state='pending';
assert.equal(Progress.downloadMarker(row),'·');
assert.equal(Progress.downloadCaption({active:true,percent:0,errors:0,items:[row]}),'… 0%');
row.state='waiting';row.stage='install';row.stage_percent=100;
assert.equal(Progress.downloadMarker(row),'◷');
assert.equal(Progress.downloadCaption({active:true,percent:75,errors:0,items:[row]}),'◷ 75%');
const downloading={state:'running',stage:'download',stage_percent:50};
const extracting={state:'running',stage:'extract',stage_percent:null};
const converting={state:'running',stage:'convert',stage_percent:25};
assert.equal(Progress.downloadCaption({active:true,percent:15,errors:0,items:[downloading,extracting,converting]}),'↓ ▣ ⚙ 15%');
assert.equal(Progress.downloadCaption({active:true,percent:25,errors:0,items:[downloading,row]}),'↓ 25%');
assert.equal(Progress.downloadCaption({active:true,percent:10,errors:0,items:[downloading,{...downloading,stage_percent:null}]}),'↓ 10%');
const pending=Array.from({length:19},()=>({state:'pending',percent:0}));
assert.equal(Progress.downloadCaption({active:true,percent:2,errors:0,items:[downloading,...pending]}),'↓ 2%');
assert.equal(Progress.downloadCaption({active:true,percent:50,errors:1,items:[downloading]}),'! ↓ 50%');
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    for name in ("tv-dialogs.js", "tv-shell.js"):
        assert (Path("www/assets") / name).read_bytes() == (Path("thelpviewer/server/converter/assets") / name).read_bytes()
