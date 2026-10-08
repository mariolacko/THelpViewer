from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_viewer_starts_when_screensaver_asset_fails_to_load():
    with tempfile.TemporaryDirectory(prefix="thelp-optional-saver-") as state_dir:
        helps_dir = Path(state_dir) / "helps"
        helps_dir.mkdir()
        port = _free_port()
        app_url = f"http://127.0.0.1:{port}/"
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning"],
            cwd=Path.cwd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={**os.environ, "THELP_STATE_DIR": state_dir, "THELP_HELPS_DIR": str(helps_dir),
                 "THELP_STATISTICS_PATH": str(Path(state_dir) / "statistics.sqlite3")},
        )
        try:
            _wait_for_url(app_url + "healthz")
            with tempfile.TemporaryDirectory(prefix="thelp-optional-saver-chrome-") as profile_dir:
                chrome = subprocess.Popen(
                    [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                     "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0",
                     f"--user-data-dir={profile_dir}", "about:blank"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    env={**os.environ, "CHROME_HEADLESS": "1"},
                )
                try:
                    debugging_port = int(_wait_for_file(Path(profile_dir) / "DevToolsActivePort").splitlines()[0])
                    script = r'''
const [debuggingPort, appUrl] = process.argv.slice(1);

async function run() {
    const response = await fetch(
        `http://127.0.0.1:${debuggingPort}/json/new?${encodeURIComponent(appUrl)}`,
        { method: "PUT" }
    );
    if (!response.ok) { throw new Error(`cannot create target: ${response.status}`); }
    const target = await response.json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
        socket.addEventListener("open", resolve, { once: true });
        socket.addEventListener("error", reject, { once: true });
    });
    let sequence = 0;
    const pending = new Map();
    const errors = [];
    socket.addEventListener("message", (event) => {
        const message = JSON.parse(String(event.data));
        if (message.method === "Runtime.exceptionThrown") {
            errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
        }
        if (!pending.has(message.id)) { return; }
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) { reject(new Error(message.error.message)); }
        else { resolve(message.result); }
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const id = ++sequence;
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
    });
    try {
        await send("Page.enable");
        await send("Runtime.enable");
        await send("Network.enable");
        await send("Network.setBlockedURLs", { urls: ["*tv-screensaver.js*"] });
        await send("Page.navigate", { url: appUrl + "?doc=README.md" });
        const result = await send("Runtime.evaluate", {
            expression: `new Promise((resolve, reject) => {
                const deadline = Date.now() + 10000;
                const check = () => {
                    const ready = Boolean(document.querySelector('[data-tv-command="file-open"]')
                        && document.querySelector('.tv-doc-window')
                        && !document.getElementById('tv-public-fallback'));
                    if (ready) { resolve({ ready, saver: Boolean(window.THelpViewerTV.TVScreenSaver) }); return; }
                    if (Date.now() > deadline) { reject(new Error('viewer did not open Docs')); return; }
                    setTimeout(check, 50);
                };
                check();
            })`,
            awaitPromise: true,
            returnByValue: true,
        });
        if (result.exceptionDetails) {
            throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
        }
        if (!result.result.value.ready || result.result.value.saver || errors.length) {
            throw new Error(JSON.stringify({ result: result.result.value, errors }));
        }
    } finally {
        socket.close();
    }
}

run().catch((error) => { console.error(error); process.exitCode = 1; });
'''
                    result = subprocess.run(
                        [NODE, "-e", script, str(debugging_port), app_url],
                        capture_output=True, text=True, timeout=30,
                    )
                    assert result.returncode == 0, result.stderr
                finally:
                    chrome.terminate()
                    try:
                        chrome.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        chrome.kill()
                        chrome.wait(timeout=5)
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
