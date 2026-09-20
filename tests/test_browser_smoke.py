from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

import pytest


NODE = shutil.which("node")
CHROME_CANDIDATES = (
    shutil.which("google-chrome"),
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
CHROME = next((path for path in CHROME_CANDIDATES if path and Path(path).is_file()), None)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_url(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"server did not become ready: {url}")


def _wait_for_file(path: Path, timeout: float = 10.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return content
        time.sleep(0.05)
    raise TimeoutError(f"file did not appear: {path}")


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_real_browser_menu_focus_and_dynamic_command_state():
    app_port = _free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "thelpviewer.server.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(app_port),
            "--log-level",
            "warning",
        ],
        cwd=Path.cwd(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_url(f"http://127.0.0.1:{app_port}/healthz")
        with tempfile.TemporaryDirectory(prefix="thelpviewer-chrome-") as profile_dir:
            chrome = subprocess.Popen(
                [
                    CHROME,
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--remote-debugging-port=0",
                    f"--user-data-dir={profile_dir}",
                    "about:blank",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "CHROME_HEADLESS": "1"},
            )
            try:
                port_text = _wait_for_file(Path(profile_dir) / "DevToolsActivePort")
                debugging_port = int(port_text.splitlines()[0])
                script = r'''
const debuggingPort = process.argv[1];
const appUrl = process.argv[2];

async function run() {
    const targetResponse = await fetch(
        `http://127.0.0.1:${debuggingPort}/json/new?${encodeURIComponent(appUrl)}`,
        { method: "PUT" }
    );
    if (!targetResponse.ok) { throw new Error(`cannot create browser target: ${targetResponse.status}`); }
    const target = await targetResponse.json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
        socket.addEventListener("open", resolve, { once: true });
        socket.addEventListener("error", reject, { once: true });
    });

    let sequence = 0;
    const pending = new Map();
    socket.addEventListener("message", (event) => {
        const message = JSON.parse(String(event.data));
        if (!message.id || !pending.has(message.id)) { return; }
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
    const evaluate = async (expression, awaitPromise = false) => {
        const result = await send("Runtime.evaluate", {
            expression,
            awaitPromise,
            returnByValue: true,
        });
        if (result.exceptionDetails) {
            throw new Error(result.exceptionDetails.text || "browser evaluation failed");
        }
        return result.result.value;
    };
    const key = (value, code, modifiers = 0, useActiveElement = false) => evaluate(`(() => {
        const target = ${useActiveElement ? "document.activeElement || document" : "document"};
        const options = {
            key: ${JSON.stringify(value)},
            code: ${JSON.stringify(code)},
            altKey: Boolean(${modifiers} & 1),
            ctrlKey: Boolean(${modifiers} & 2),
            metaKey: Boolean(${modifiers} & 4),
            shiftKey: Boolean(${modifiers} & 8),
            bubbles: true,
            cancelable: true,
        };
        const down = new KeyboardEvent('keydown', options);
        target.dispatchEvent(down);
        target.dispatchEvent(new KeyboardEvent('keyup', options));
        return down.defaultPrevented;
    })()`);
    const pause = () => evaluate("new Promise(resolve => setTimeout(resolve, 200))", true);

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Page.navigate", { url: appUrl });
    await send("Page.bringToFront");
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const menu = document.querySelector('[data-tv-window-cmd="close"]');
            const welcome = Array.from(document.querySelectorAll('.tv-dialog-title-text'))
                .some((element) => element.textContent === 'Welcome');
            if (menu && welcome) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('application did not initialize')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);

    await key("Escape", "Escape", 0, true);
    await evaluate(`(() => {
        const doc = document.querySelector('[data-tv-doc-open]');
        if (!doc) { throw new Error('documentation menu is empty'); }
        doc.click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (document.querySelector('.tv-doc-window')) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('document window did not open')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);

    await evaluate(`(() => {
        const item = document.querySelector('[data-tv-window-cmd]');
        const root = item && item.closest('[data-tv-menu-root]');
        const toggle = root && root.querySelector('[data-tv-menu-toggle]');
        if (!toggle) { throw new Error('Windows menu toggle was not found'); }
        toggle.focus();
        toggle.click();
    })()`);
    await key("ArrowDown", "ArrowDown", 0, true);
    await pause();
    const state = await evaluate(`(() => {
        const items = Array.from(document.querySelectorAll('[data-tv-window-cmd]'));
        const byCommand = Object.fromEntries(items.map((item) => [item.dataset.tvWindowCmd, {
            disabled: item.disabled,
            ariaDisabled: item.getAttribute('aria-disabled'),
        }]));
        const popup = items[0] && items[0].closest('[data-tv-menu-popup]');
        return {
            popupOpen: Boolean(popup && !popup.hidden),
            focusedCommand: document.activeElement && document.activeElement.dataset.tvWindowCmd || '',
            byCommand,
        };
    })()`);
    if (!state.popupOpen || state.focusedCommand !== "tile") {
        throw new Error(`Windows menu did not focus its first enabled item: ${JSON.stringify(state)}`);
    }
    for (const command of ["next", "previous"]) {
        if (!state.byCommand[command].disabled || state.byCommand[command].ariaDisabled !== "true") {
            throw new Error(`${command} should be disabled while one document is the only target`);
        }
    }
    for (const command of ["tile", "cascade", "list", "zoom", "close"]) {
        if (state.byCommand[command].disabled || state.byCommand[command].ariaDisabled !== "false") {
            throw new Error(`${command} should be enabled for an active document window`);
        }
    }

    await key("ArrowDown", "ArrowDown", 0, true);
    await pause();
    await key("ArrowDown", "ArrowDown", 0, true);
    await pause();
    await key("Enter", "Enter", 0, true);
    await pause();
    const windowListOpen = await evaluate(
        `Array.from(document.querySelectorAll('.tv-dialog-title-text')).some((element) => element.textContent === 'Window List')`
    );
    if (!windowListOpen) { throw new Error("Enter did not activate the focused Window List command"); }
    await key("Escape", "Escape", 0, true);
    await pause();
    const windowListClosed = await evaluate(
        `!Array.from(document.querySelectorAll('.tv-dialog-title-text')).some((element) => element.textContent === 'Window List')`
    );
    if (!windowListClosed) { throw new Error("Escape did not close the Window List dialog"); }

    await evaluate(`document.querySelector('[data-tv-dialog-open="widgets"]').click()`);
    await pause();
    const gallery = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Widget Gallery'
        );
        if (!dialog) { return { open: false }; }
        const label = dialog.querySelector('label[for="tv-widget-gallery-name"]');
        const input = dialog.querySelector('#tv-widget-gallery-name');
        label.click();
        dialog.querySelector('[data-tv-gallery-apply]').click();
        return {
            open: true,
            labelFocus: document.activeElement === input,
            checks: dialog.querySelectorAll('[data-tv-gallery-checks] input[type="checkbox"]').length,
            radios: dialog.querySelectorAll('[data-tv-gallery-radios] input[type="radio"]').length,
            disabledChoices: dialog.querySelectorAll('.tv-choice-input:disabled').length,
            listItems: dialog.querySelectorAll('[data-tv-gallery-list-index]').length,
            selectedItems: dialog.querySelectorAll('[data-tv-gallery-list-index].is-selected').length,
            disabledButtons: dialog.querySelectorAll('.tv-dialog-button:disabled').length,
            status: dialog.querySelector('[data-tv-row="status"]')?.textContent || '',
        };
    })()`);
    if (
        !gallery.open || !gallery.labelFocus || gallery.checks !== 3 || gallery.radios !== 3
        || gallery.disabledChoices !== 2 || gallery.listItems !== 5 || gallery.selectedItems !== 1
        || gallery.disabledButtons !== 1 || !gallery.status.includes('Apply command')
    ) {
        throw new Error(`Widget Gallery controls are incomplete: ${JSON.stringify(gallery)}`);
    }
    await key("Escape", "Escape", 0, true);
    await pause();
    const galleryClosed = await evaluate(
        `Array.from(document.querySelectorAll('.tv-dialog-title-text'))
            .filter((element) => element.textContent === 'Widget Gallery')
            .every((element) => element.closest('.tv-dialog-overlay').hidden)`
    );
    if (!galleryClosed) { throw new Error("Escape did not close Widget Gallery"); }

    await evaluate(`document.querySelector('[data-tv-file-open]').click()`);
    await pause();
    const fileOpen = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        if (!dialog) { return { open: false }; }
        const docsDirectory = Array.from(dialog.querySelectorAll('[data-tv-file-open-directory-index]'))
            .find((element) => element.textContent.trim() === 'DOCS');
        if (!docsDirectory) { return { open: true, docsDirectory: false }; }
        docsDirectory.click();
        const firstFile = dialog.querySelector('[data-tv-file-open-file-index]');
        if (!firstFile) { return { open: true, docsDirectory: true, files: 0 }; }
        firstFile.click();
        const input = dialog.querySelector('[data-tv-file-open-name]');
        input.focus();
        return {
            open: !dialog.closest('.tv-dialog-overlay').hidden,
            modal: dialog.getAttribute('aria-modal'),
            docsDirectory: true,
            files: dialog.querySelectorAll('[data-tv-file-open-file-index]').length,
            directories: dialog.querySelectorAll('[data-tv-file-open-directory-index]').length,
            path: dialog.querySelector('[data-tv-file-open-path]')?.textContent || '',
            name: input.value,
            focused: document.activeElement === input,
        };
    })()`);
    if (
        !fileOpen.open || fileOpen.modal !== "true" || !fileOpen.docsDirectory
        || fileOpen.files < 1 || fileOpen.directories < 2
        || fileOpen.path !== "THelpViewer:\\DOCS" || !fileOpen.name || !fileOpen.focused
    ) {
        throw new Error(`File Open dialog is incomplete: ${JSON.stringify(fileOpen)}`);
    }
    await key("Enter", "Enter", 0, true);
    await pause();
    const fileOpened = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        const history = JSON.parse(localStorage.getItem('thelp:file-open-history') || '[]');
        return {
            closed: Boolean(dialog && dialog.closest('.tv-dialog-overlay').hidden),
            remembered: history.some((entry) => entry.startsWith('doc:')),
        };
    })()`);
    if (!fileOpened.closed || !fileOpened.remembered) {
        throw new Error(`File Open did not open and remember the document: ${JSON.stringify(fileOpened)}`);
    }

    await evaluate(`document.querySelector('[data-tv-file-open]').click()`);
    await pause();
    const historyOpen = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-file-open-history]');
        button.click();
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        return !button.disabled && Boolean(popup && !popup.hidden)
            && popup.querySelectorAll('[data-tv-file-open-history-index]').length === 1;
    })()`);
    if (!historyOpen) { throw new Error("File Open history did not reopen"); }
    await key("Escape", "Escape", 0, true);
    const escapeClosedHistoryOnly = await evaluate(`(() => {
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        const dialog = popup.closest('.tv-dialog-overlay');
        return popup.hidden && !dialog.hidden;
    })()`);
    if (!escapeClosedHistoryOnly) { throw new Error("Escape did not close File Open history first"); }
    await key("Escape", "Escape", 0, true);
    socket.close();
}

const timeout = setTimeout(() => {
    process.stderr.write("browser smoke test timed out\n");
    process.exit(1);
}, 25000);
run().then(() => {
    clearTimeout(timeout);
    process.exit(0);
}).catch((error) => {
    clearTimeout(timeout);
    process.stderr.write(String(error.stack || error) + "\n");
    process.exit(1);
});
'''
                result = subprocess.run(
                    [NODE, "-e", script, str(debugging_port), f"http://127.0.0.1:{app_port}/"],
                    capture_output=True,
                    text=True,
                    timeout=30,
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
