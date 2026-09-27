"""End-to-end checks for the server-launched terminal and the grid primitive."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from fastapi.testclient import TestClient

from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.terminal import read_job, run_command


def test_grid_is_exported_and_uses_list_scrollbars():
    source = Path("thelpviewer/converter/assets/tv-core.js").read_text(encoding="utf-8")
    assert "class TVGridView extends TVListBox" in source
    assert "setHeadersVisible(visible)" in source
    assert "selectCell(row, column, options = {})" in source
    assert "    TVGridView," in source
    assert source == Path("www/assets/tv-core.js").read_text(encoding="utf-8")


def test_terminal_chunk_boundary_preserves_utf8(tmp_path):
    job_id = "AbCdEfGhIjKl"
    key = "secret"
    job_dir = tmp_path / "terminal" / job_id
    job_dir.mkdir(parents=True)
    (job_dir / "status.json").write_text(json.dumps({
        "key_hash": hashlib.sha256(key.encode()).hexdigest(), "running": True,
    }), encoding="utf-8")
    (job_dir / "output.log").write_bytes(b"A" * 65535 + "é".encode())
    first = read_job(tmp_path, job_id, key)
    second = read_job(tmp_path, job_id, key, first["offset"])
    assert first["offset"] == 65535
    assert first["output"] + second["output"] == "A" * 65535 + "é"


def test_server_terminal_reports_launch_failure_in_window(tmp_path, capsys):
    assert run_command(tmp_path, [str(tmp_path / "missing-program")]) == 127
    lines = capsys.readouterr().out.splitlines()
    job_id = lines[0].removeprefix("Terminal job ID: ")
    key = lines[1].removeprefix("Terminal access key: ")
    result = read_job(tmp_path, job_id, key)
    assert "Could not start command:" in result["output"]
    assert result["running"] is False and result["exit_code"] == 127


def test_server_terminal_streams_output_accepts_live_input_and_locks_after_exit(tmp_path):
    config = replace(load_config(), state_dir=tmp_path, statistics_path=tmp_path / "statistics.sqlite3")
    client = TestClient(create_app(config))
    command = [
        sys.executable, "-u", "-c",
        "print('Ready', flush=True); print('Received: ' + input('Prompt: '), flush=True)",
    ]
    process = subprocess.Popen(
        [sys.executable, "-m", "thelpviewer.server.terminal", "--state-dir", str(tmp_path),
         "--label", "Interactive test", "--", *command],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        job_id = process.stdout.readline().strip().removeprefix("Terminal job ID: ")
        key = process.stdout.readline().strip().removeprefix("Terminal access key: ")
        assert len(job_id) == 12 and len(key) >= 24
        url = f"/api/terminal/jobs/{job_id}"
        headers = {"X-THelp-Terminal-Key": key}
        assert client.get(url).status_code == 404
        assert client.get(url, headers={"X-THelp-Terminal-Key": "wrong"}).status_code == 404
        assert client.post(url + "/input", json={"text": "bad"}).status_code == 404
        assert client.post("/api/terminal/jobs", json={"command": "whoami"}).status_code in (404, 405)

        offset = 0
        output = ""
        deadline = time.monotonic() + 5
        while "Prompt: " not in output and time.monotonic() < deadline:
            response = client.get(url, headers=headers, params={"offset": offset})
            assert response.status_code == 200
            chunk = response.json()
            output += chunk["output"]
            offset = chunk["offset"]
            assert chunk["running"] is True
            time.sleep(0.03)
        assert "Ready" in output and "Prompt: " in output
        assert client.post(url + "/input", headers=headers, content=b"x" * 5000).status_code == 413
        assert client.post(url + "/input", headers=headers, json={"text": "two\nlines"}).status_code == 422
        assert client.post(url + "/input", headers=headers, json={"text": "hello"}).status_code == 204
        process.wait(timeout=5)
        final = client.get(url, headers=headers, params={"offset": offset}).json()
        output += final["output"]
        assert "Received: hello" in output
        assert final["running"] is False and final["exit_code"] == 0
        assert client.post(url + "/input", headers=headers, json={"text": "late"}).status_code == 409
        status = json.loads((tmp_path / "terminal" / job_id / "status.json").read_text(encoding="utf-8"))
        assert key not in json.dumps(status)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
