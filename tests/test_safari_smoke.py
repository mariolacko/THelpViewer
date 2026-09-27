"""Opt-in Safari regression for window closing and File Open history."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


SAFARIDRIVER = shutil.which("safaridriver")
REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
    except HTTPError as error:
        result = json.load(error)
    if isinstance(result.get("value"), dict) and result["value"].get("error"):
        raise AssertionError(result["value"].get("message") or result["value"]["error"])
    return result


def _wait_until(check, description: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except OSError:
            pass
        time.sleep(0.1)
    raise AssertionError(f"Safari did not {description}")


@pytest.mark.skipif(
    SAFARIDRIVER is None or os.environ.get("THELP_SAFARI_TEST") != "1",
    reason="Set THELP_SAFARI_TEST=1 after enabling Safari > Developer > Allow remote automation",
)
def test_safari_window_close_and_file_history_toggle():
    app_port = _free_port()
    driver_port = _free_port()
    app_url = f"http://127.0.0.1:{app_port}/"
    driver_url = f"http://127.0.0.1:{driver_port}"
    with tempfile.TemporaryDirectory(prefix="thelpviewer-safari-state-") as state_dir:
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app",
             "--host", "127.0.0.1", "--port", str(app_port), "--log-level", "warning"],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "THELP_STATE_DIR": state_dir,
                "THELP_STATISTICS_PATH": str(Path(state_dir) / "statistics.sqlite3"),
            },
        )
        driver = subprocess.Popen(
            [SAFARIDRIVER, "-p", str(driver_port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        session = None
        try:
            _wait_until(lambda: urlopen(app_url + "healthz", timeout=1).status == 200, "start the app")
            _wait_until(lambda: _request(driver_url + "/status")["value"]["ready"], "start WebDriver")
            session = _request(driver_url + "/session", "POST", {
                "capabilities": {"alwaysMatch": {"browserName": "safari"}},
            })["value"]["sessionId"]
            endpoint = f"{driver_url}/session/{session}"
            _request(endpoint + "/url", "POST", {"url": app_url})

            def execute(script: str):
                return _request(endpoint + "/execute/sync", "POST", {
                    "script": script, "args": [],
                })["value"]

            def click(selector: str) -> None:
                element = _request(endpoint + "/element", "POST", {
                    "using": "css selector", "value": selector,
                })["value"]["element-6066-11e4-a52e-4f735466cecf"]
                _request(endpoint + f"/element/{element}/click", "POST", {})

            _wait_until(
                lambda: execute("return !!document.querySelector('[data-tv-command=\"file-open\"]')"),
                "initialize the File menu",
            )
            execute("document.querySelector('[data-tv-command=\"welcome-ok\"]')?.click()")
            execute("document.querySelector('[data-tv-command=\"file-open\"]')?.click()")
            _wait_until(
                lambda: execute("return !!document.querySelector('.tv-file-open-window')"
                                " && !document.querySelector('.tv-file-open-window').closest('.tv-dialog-overlay').hidden"),
                "open File Open",
            )
            assert execute("const button = document.querySelector('[data-tv-file-open-history]');"
                           "const popup = document.querySelector('[data-tv-file-open-history-popup]');"
                           "button.click(); return !popup.hidden && button.getAttribute('aria-expanded') === 'true'")
            assert execute("const button = document.querySelector('[data-tv-file-open-history]');"
                           "const popup = document.querySelector('[data-tv-file-open-history-popup]');"
                           "button.click(); return popup.hidden && button.getAttribute('aria-expanded') === 'false'")
            click(".tv-file-open-window .tv-dialog-close-control")
            _wait_until(
                lambda: execute("return document.querySelector('.tv-file-open-window')"
                                ".closest('.tv-dialog-overlay').hidden"),
                "close File Open",
            )

            execute("document.querySelector('[data-tv-status-line] [data-tv-command=\"context-help\"]')"
                    ".click()")
            _wait_until(
                lambda: execute("return !!document.querySelector("
                                "'[data-tv-bundle-window=\"../assets/tv-context-help.json\"]')"),
                "open the HELP window",
            )
            click('[data-tv-bundle-window="../assets/tv-context-help.json"] .tv-close-control')
            _wait_until(
                lambda: execute("return !document.querySelector("
                                "'[data-tv-bundle-window=\"../assets/tv-context-help.json\"]')"),
                "close the HELP window",
            )
            _request(endpoint + "/url", "POST", {"url": app_url + "?search_doc=README.md"})
            _wait_until(lambda: execute("return !!document.querySelector('.tv-doc-window')"),
                        "open the document window")
            execute("document.querySelector('[data-tv-status-line] [data-tv-command=\"context-help\"]')"
                    ".click()")
            _wait_until(
                lambda: execute("return !!document.querySelector("
                                "'[data-tv-bundle-window=\"../assets/tv-context-help.json\"]')"
                                " && document.querySelector('.tv-doc-window')"
                                ".classList.contains('is-window-inactive')"),
                "make the document window inactive",
            )
            execute("const close = document.querySelector('.tv-doc-window .tv-close-control');"
                    "close.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));"
                    "close.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));")
            _wait_until(lambda: execute("return !document.querySelector('.tv-doc-window')"),
                        "close the inactive document window")
        finally:
            if session is not None:
                try:
                    _request(f"{driver_url}/session/{session}", "DELETE")
                except OSError:
                    pass
            driver.terminate()
            server.terminate()
            driver.wait(timeout=5)
            server.wait(timeout=5)
