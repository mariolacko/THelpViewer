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
    external_url = os.environ.get("THELP_BROWSER_BASE_URL", "").rstrip("/")
    server = None
    if external_url:
        app_url = external_url + "/"
    else:
        app_port = _free_port()
        app_url = f"http://127.0.0.1:{app_port}/"
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
        _wait_for_url(app_url + "healthz")
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
            const description = result.exceptionDetails.exception?.description;
            throw new Error(description || result.exceptionDetails.text || "browser evaluation failed");
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
    const clickPoint = async (point) => {
        await send('Input.dispatchMouseEvent', {
            type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1,
        });
        await send('Input.dispatchMouseEvent', {
            type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1,
        });
    };

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Network.enable");
    await send("Network.emulateNetworkConditions", {
        offline: false,
        latency: 700,
        downloadThroughput: -1,
        uploadThroughput: -1,
    });
    await send("Page.navigate", { url: appUrl });
    await send("Page.bringToFront");
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const open = document.querySelector('[data-tv-file-open][data-tv-menu-bound="1"]');
            if (open) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('Open was not bound while catalogs loaded')); return; }
            setTimeout(check, 20);
        };
        check();
    })`, true);
    const helpMenuPoint = await evaluate(`(() => {
        const open = document.querySelector('[data-tv-file-open]');
        const toggle = open.closest('[data-tv-menu-root]').querySelector('[data-tv-menu-toggle]');
        const rect = toggle.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: helpMenuPoint.x, y: helpMenuPoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: helpMenuPoint.x, y: helpMenuPoint.y, button: 'left', clickCount: 1,
    });
    await pause();
    const openPoint = await evaluate(`(() => {
        const open = document.querySelector('[data-tv-file-open]');
        const rect = open.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: openPoint.x, y: openPoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: openPoint.x, y: openPoint.y, button: 'left', clickCount: 1,
    });
    const loadingOpen = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        const history = dialog?.querySelector('[data-tv-file-open-history-popup]');
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            status: dialog?.querySelector('[data-tv-file-open-detail]')?.textContent.trim() || '',
            historyHidden: Boolean(history?.hidden && getComputedStyle(history).display === 'none'),
        };
    })()`);
    if (!loadingOpen.open || loadingOpen.status !== 'Loading HELP/DOCS...' || !loadingOpen.historyHidden) {
        throw new Error(`Open did not show its loading state immediately: ${JSON.stringify(loadingOpen)}`);
    }
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
                element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
            );
            const entries = dialog?.querySelectorAll('[data-tv-file-open-file-index]').length || 0;
            if (dialog && !dialog.closest('.tv-dialog-overlay').hidden && entries >= 2) {
                resolve(true);
                return;
            }
            if (Date.now() >= deadline) { reject(new Error('Open stayed empty while catalogs loaded')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const emptyFileHistory = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-file-open-history]');
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        button?.click();
        const opened = Boolean(button && !button.disabled && popup && !popup.hidden
            && button.getAttribute('aria-expanded') === 'true');
        button?.click();
        const closed = Boolean(popup?.hidden && button?.getAttribute('aria-expanded') === 'false');
        return { opened, closed, entries: popup?.querySelectorAll('[data-tv-file-open-history-index]').length || 0 };
    })()`);
    if (!emptyFileHistory.opened || !emptyFileHistory.closed || emptyFileHistory.entries !== 0) {
        throw new Error(`Empty File Open history did not toggle: ${JSON.stringify(emptyFileHistory)}`);
    }
    await key("F1", "F1");
    await evaluate(`new Promise((resolve, reject) => {
            const deadline = Date.now() + 5000;
            const check = () => {
                const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
                const heading = help?.querySelector('.tv-topic-heading');
                const links = document.querySelectorAll(
                    '[data-tv-bundle-window="../assets/tv-context-help.json"] [data-tv-bundle-topic]'
                );
                if (heading?.textContent.trim() === 'Open a File' && links.length >= 2) {
                    resolve(true);
                    return;
                }
            if (Date.now() >= deadline) { reject(new Error('context help bundle did not load')); return; }
            setTimeout(check, 25);
        };
        check();
    })`, true);
    const fileOpenHelp = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        const fileOpen = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        const vertical = help?.querySelector(':scope > .tv-shell > .tv-client-row > .tv-scrollbar-y');
        return {
            helpOpen: Boolean(help?.isConnected),
            standardWindow: Boolean(help?.matches('.tv-window[data-tv-window]')),
            topic: help?.querySelector('.tv-topic-heading')?.textContent.trim(),
            context: fileOpen?.getAttribute('data-tv-help-ctx'),
            links: help?.querySelectorAll('[data-tv-bundle-topic]').length || 0,
            standardScrollbar: Boolean(vertical),
            inlineNavigation: Boolean(help?.querySelector('.tv-context-help-nav')),
            statusBack: Boolean(document.querySelector('[data-tv-status-line] [data-tv-bundle-back]')),
            statusContents: Boolean(document.querySelector('[data-tv-status-line] [data-tv-bundle-help-contents]')),
        };
    })()`);
    if (!fileOpenHelp.helpOpen || fileOpenHelp.topic !== 'Open a File' || fileOpenHelp.context !== '2010'
        || !fileOpenHelp.standardWindow || fileOpenHelp.links < 2 || !fileOpenHelp.standardScrollbar
        || fileOpenHelp.inlineNavigation || !fileOpenHelp.statusBack || !fileOpenHelp.statusContents) {
        throw new Error(`File Open context help is broken: ${JSON.stringify(fileOpenHelp)}`);
    }
    const topContentsMenu = await evaluate(`(() => {
        const root = document.querySelector('[data-tv-bundle-menu-root]');
        const popup = root?.querySelector(':scope > [data-tv-menu-popup]');
        return {
            roots: popup?.querySelectorAll(':scope .tv-submenu-root').length || 0,
            text: popup?.textContent || '',
        };
    })()`);
    if (topContentsMenu.roots < 3 || !topContentsMenu.text.includes('Using THelpViewer')) {
        throw new Error(`Top Contents menu is empty: ${JSON.stringify(topContentsMenu)}`);
    }
    await evaluate(`document.querySelector('[data-tv-bundle-contents]').click()`);
    await pause();
    const structuralContents = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return {
            view: help?.dataset.tvStateView,
            outlines: help?.querySelectorAll('[data-tv-contents-outline]').length || 0,
            rows: help?.querySelectorAll('[data-tv-contents-outline-index]').length || 0,
            verticalScrollbars: help?.querySelectorAll('.tv-scrollbar-y').length || 0,
        };
    })()`);
    if (structuralContents.view !== 'contents' || structuralContents.outlines !== 1
        || structuralContents.rows < 10 || structuralContents.verticalScrollbars !== 1) {
        throw new Error(`Structural Contents uses the wrong scrollbar: ${JSON.stringify(structuralContents)}`);
    }
    await evaluate(`document.querySelector('[data-tv-bundle-back]').click()`);
    await evaluate(`document.querySelector('[data-tv-bundle-help-contents]').click()`);
    await pause();
    const helpContents = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        const viewport = help?.querySelector('[data-tv-viewport]');
        return {
            topic: help?.querySelector('.tv-topic-heading')?.textContent.trim(),
            table: viewport?.textContent.includes('┌──────────────────┬'),
            links: viewport?.querySelectorAll('[data-tv-bundle-topic]').length || 0,
            verticalOverflow: viewport?.scrollHeight > viewport?.clientHeight,
            horizontalOverflow: viewport?.scrollWidth > viewport?.clientWidth + 1,
            backInStatusLine: Boolean(document.querySelector('[data-tv-status-line] [data-tv-bundle-back]')),
        };
    })()`);
    if (helpContents.topic !== 'THelpViewer' || !helpContents.table || helpContents.links < 6
        || !helpContents.verticalOverflow || helpContents.horizontalOverflow || !helpContents.backInStatusLine) {
        throw new Error(`Context Help contents are incomplete: ${JSON.stringify(helpContents)}`);
    }
    await evaluate(`document.querySelector('[data-tv-bundle-back]').click()`);
    const helpReturned = await evaluate(`
        document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"] .tv-topic-heading')?.textContent.trim()
    `);
    if (helpReturned !== 'Open a File') { throw new Error('Context Help Back did not restore its topic'); }
    await evaluate(`document.querySelector('[data-tv-bundle-close-all]').click()`);
    const contextHelpClosed = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        const fileOpen = document.querySelector('[data-tv-file-open-name]')?.closest('.tv-dialog-overlay');
        return Boolean(!help && fileOpen && !fileOpen.hidden);
    })()`);
    if (!contextHelpClosed) { throw new Error('Context Help did not return to File Open'); }
    await key("Escape", "Escape", 0, true);
    await send("Network.emulateNetworkConditions", {
        offline: false,
        latency: 0,
        downloadThroughput: -1,
        uploadThroughput: -1,
    });
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
    const calculatorView = await evaluate(`(() => {
        document.querySelector('[data-tv-dialog-open="calc"]')?.click();
        const display = document.querySelector('[data-tv-calc-display]');
        return {
            open: Boolean(display && !display.closest('.tv-dialog-overlay')?.hidden),
            foreground: display ? getComputedStyle(display).color : '',
            hint: document.querySelector('[data-tv-status-hint]')?.textContent.trim() || '',
        };
    })()`);
    if (!calculatorView.open || calculatorView.foreground !== 'rgb(255, 255, 255)'
        || calculatorView.hint !== 'Calculator') {
        throw new Error(`Calculator display/status palette is broken: ${JSON.stringify(calculatorView)}`);
    }
    await evaluate(`document.querySelector('[data-tv-calc-close]')?.click()`);
    const initialFindState = await evaluate(`(() => ({
        findDisabled: document.querySelector('[data-tv-find]')?.disabled,
        againDisabled: document.querySelector('[data-tv-find-again]')?.disabled,
    }))()`);
    if (!initialFindState.findDisabled || !initialFindState.againDisabled) {
        throw new Error(`Find commands should be disabled without an active content window: ${JSON.stringify(initialFindState)}`);
    }
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

    const documentFindState = await evaluate(`(() => ({
        findDisabled: document.querySelector('[data-tv-find]')?.disabled,
        againDisabled: document.querySelector('[data-tv-find-again]')?.disabled,
    }))()`);
    if (documentFindState.findDisabled || !documentFindState.againDisabled) {
        throw new Error(`Find command state is wrong before the first search: ${JSON.stringify(documentFindState)}`);
    }

    const docColors = await evaluate(`(() => {
        const doc = document.querySelector('.tv-doc-window');
        const viewport = doc.querySelector('.tv-viewport');
        const content = doc.querySelector('.tv-doc-document');
        const pair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        return {
            viewport: pair(viewport),
            content: pair(content),
            statusHint: document.querySelector('[data-tv-status-hint]')?.textContent.trim() || '',
            caption: doc.querySelector('.tv-window-caption')?.textContent.trim() || '',
        };
    })()`);
    const editorColors = ['rgb(0, 0, 170)', 'rgb(255, 255, 85)'];
    if (docColors.viewport.join() !== editorColors.join() || docColors.content.join() !== editorColors.join()) {
        throw new Error(`Documentation does not use the Editor palette: ${JSON.stringify(docColors)}`);
    }
    if (!docColors.caption || docColors.statusHint !== docColors.caption) {
        throw new Error(`Status line did not show the active document hint: ${JSON.stringify(docColors)}`);
    }
    const docPaletteIsolation = await evaluate(`(() => {
        const TV = window.THelpViewerTV;
        const palette = TV.buildDefaultColorPalette();
        TV.setColorPaletteAttribute(palette, 13, 0x2F);
        TV.applyColorPalette(palette, false);
        const doc = document.querySelector('.tv-doc-window');
        const viewport = getComputedStyle(doc.querySelector('.tv-viewport'));
        const content = getComputedStyle(doc.querySelector('.tv-doc-document'));
        const result = {
            viewport: [viewport.backgroundColor, viewport.color],
            content: [content.backgroundColor, content.color],
        };
        TV.applyColorPalette(TV.buildDefaultColorPalette(), false);
        return result;
    })()`);
    if (
        docPaletteIsolation.viewport.join() !== editorColors.join()
        || docPaletteIsolation.content.join() !== editorColors.join()
    ) {
        throw new Error(`Viewer palette changed the fixed Editor colors: ${JSON.stringify(docPaletteIsolation)}`);
    }
    const docEditor = await evaluate(`(() => {
        const doc = document.querySelector('.tv-doc-window');
        const editor = doc?._tvEditor;
        const root = doc?.querySelector('[data-tv-editor]');
        const word = (root?.textContent.match(/[A-Za-z]{6,}/) || [])[0] || '';
        return {
            attached: editor instanceof window.THelpViewerTV.TVEditor,
            readOnly: root?.getAttribute('aria-readonly'),
            found: word ? editor.find(word, { fromStart: true }) : false,
            indicator: doc?.querySelector('.tv-editor-indicator')?.textContent,
        };
    })()`);
    if (!docEditor.attached || docEditor.readOnly !== 'true' || !docEditor.found || !docEditor.indicator.startsWith('RO')) {
        throw new Error(`Documentation is not using the read-only editor: ${JSON.stringify(docEditor)}`);
    }

    const findNeedle = await evaluate(`(() => {
        const root = document.querySelector('.tv-doc-window [data-tv-editor]');
        const value = (root?.textContent.match(/[A-Za-z]{7,}/) || [])[0] || '';
        window.__tvFindNeedle = value;
        return value;
    })()`);
    if (!findNeedle) { throw new Error('Documentation has no searchable word'); }
    await key("f", "KeyF", 2);
    await pause();
    const findOpen = await evaluate(`(() => {
        const input = document.querySelector('[data-tv-find-input]');
        const history = document.querySelector('[data-tv-find-history-popup]');
        if (!input || input.closest('.tv-dialog-overlay')?.hidden) { return { open: false }; }
        const historyHidden = Boolean(history?.hidden && getComputedStyle(history).display === 'none');
        input.value = window.__tvFindNeedle;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
        return { open: true, historyHidden };
    })()`);
    if (!findOpen.open || !findOpen.historyHidden) {
        throw new Error(`Ctrl-F opened Find incorrectly: ${JSON.stringify(findOpen)}`);
    }
    await key("Enter", "Enter", 0, true);
    await pause();
    const findResult = await evaluate(`(() => ({
        closed: document.querySelector('[data-tv-find-input]')?.closest('.tv-dialog-overlay')?.hidden,
        selection: window.getSelection()?.toString() || '',
        history: JSON.parse(localStorage.getItem('thelp:find-history') || '[]'),
    }))()`);
    if (!findResult.closed || findResult.selection.toLocaleLowerCase() !== findNeedle.toLocaleLowerCase()
        || !findResult.history.includes(findNeedle)) {
        throw new Error(`Find did not search the active editor: ${JSON.stringify(findResult)}`);
    }
    const searchedFindState = await evaluate(`(() => ({
        findDisabled: document.querySelector('[data-tv-find]')?.disabled,
        againDisabled: document.querySelector('[data-tv-find-again]')?.disabled,
    }))()`);
    if (searchedFindState.findDisabled || searchedFindState.againDisabled) {
        throw new Error(`Find Again was not enabled after a successful search: ${JSON.stringify(searchedFindState)}`);
    }
    await key("l", "KeyL", 2);
    await pause();
    const findAgainSelection = await evaluate(`window.getSelection()?.toString() || ''`);
    if (findAgainSelection.toLocaleLowerCase() !== findNeedle.toLocaleLowerCase()) {
        throw new Error(`Find Again lost the active query: ${findAgainSelection}`);
    }
    await key("f", "KeyF", 2);
    await pause();
    const findHistoryToggle = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-find-history]');
        const popup = document.querySelector('[data-tv-find-history-popup]');
        const initiallyHidden = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none');
        button?.click();
        const opened = Boolean(!popup?.hidden && getComputedStyle(popup).display !== 'none'
            && button?.getAttribute('aria-expanded') === 'true');
        button?.click();
        const closed = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none'
            && button?.getAttribute('aria-expanded') === 'false');
        return { enabled: !button?.disabled, initiallyHidden, opened, closed };
    })()`);
    if (!findHistoryToggle.enabled || !findHistoryToggle.initiallyHidden
        || !findHistoryToggle.opened || !findHistoryToggle.closed) {
        throw new Error(`Find history toggle is broken: ${JSON.stringify(findHistoryToggle)}`);
    }
    await key("Escape", "Escape", 0, true);

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

    const themeRoundTrip = await evaluate(`(() => {
        const TV = window.THelpViewerTV;
        TV.applyThemeAndSyncPalette('dark', false);
        const dark = getComputedStyle(document.documentElement);
        const darkHelp = dark.getPropertyValue('--tv-palette-help-text-bg').trim();
        TV.applyThemeAndSyncPalette('default', false);
        const restored = getComputedStyle(document.documentElement);
        return {
            appPaletteLength: TV.TV2_APP_COLOR_ATTRIBUTES.length,
            darkHelp,
            help: restored.getPropertyValue('--tv-palette-help-text-bg').trim(),
            dialogPassive: restored.getPropertyValue('--tv-palette-dialog-frame-passive-fg').trim(),
        };
    })()`);
    if (
        themeRoundTrip.appPaletteLength !== 135 || themeRoundTrip.darkHelp !== '#000000'
        || themeRoundTrip.help !== '#00aaaa' || themeRoundTrip.dialogPassive !== '#000000'
    ) {
        throw new Error(`Theme/palette round trip is broken: ${JSON.stringify(themeRoundTrip)}`);
    }

    const desktopDotBeforeColors = await evaluate(
        `getComputedStyle(document.documentElement).getPropertyValue('--tv-desktop-dot').trim()`
    );
    await evaluate(`document.querySelector('[data-tv-dialog-open="colors"]').click()`);
    await pause();
    const colors = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Colors'
        );
        if (!dialog) { return { open: false }; }
        const main = dialog.querySelector('.tv-colors-main');
        const mainRect = main.getBoundingClientRect();
        const cellWidth = mainRect.width / 59;
        const cellHeight = mainRect.height / 16;
        const offset = (selector) => {
            const rect = dialog.querySelector(selector).getBoundingClientRect();
            return [
                Math.round((rect.left - mainRect.left) / cellWidth),
                Math.round((rect.top - mainRect.top) / cellHeight),
                Math.round(rect.width / cellWidth),
                Math.round(rect.height / cellHeight),
            ];
        };
        const groupItems = dialog.querySelectorAll('[data-tv-colors-group]');
        const itemSelected = dialog.querySelector('[data-tv-colors-item].is-selected');
        const groupSelected = dialog.querySelector('[data-tv-colors-group].is-selected');
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        const dialogDefaults = window.THelpViewerTV.buildDefaultColorPalette()
            .find((group) => group.name === 'Dialogs/Calc');
        return {
            open: !dialog.closest('.tv-dialog-overlay').hidden,
            size: [Math.round(mainRect.width / cellWidth) + 2, Math.round(mainRect.height / cellHeight) + 2],
            groupList: offset('.tv-colors-groups-listviewer'),
            itemList: offset('.tv-colors-items-listviewer'),
            foreground: offset('.tv-colors-foreground'),
            background: offset('.tv-colors-background'),
            display: offset('.tv-colors-display'),
            buttons: offset('.tv-colors-dialog-buttons'),
            buttonCount: dialog.querySelectorAll('.tv-colors-dialog-buttons .tv-dialog-button').length,
            resetAllCount: dialog.querySelectorAll('[data-tv-colors-reset-all]').length,
            defaultCount: dialog.querySelectorAll('[data-tv-colors-default]').length,
            foregroundColors: dialog.querySelectorAll('[data-tv-colors-foreground] .tv-color-cell').length,
            backgroundColors: dialog.querySelectorAll('[data-tv-colors-background] .tv-color-cell').length,
            sampleRows: (dialog.querySelector('.tv-colors-display-sample')?.textContent || '')
                .split(String.fromCharCode(10)).length,
            groupNormalColors: stylePair(groupItems[1]),
            groupFocusedColors: stylePair(groupSelected),
            itemSelectedColors: stylePair(itemSelected),
            groupFocused: document.activeElement === groupSelected,
            dialogDefaultAttrs: dialogDefaults.items.map((item) => item.attr),
        };
    })()`);
    const expectedColorsGeometry = {
        size: [61, 18],
        groupList: [2, 2, 16, 11],
        itemList: [20, 2, 21, 11],
        foreground: [44, 2, 12, 4],
        background: [44, 8, 12, 2],
        display: [43, 11, 14, 2],
        buttons: [5, 14, 52, 2],
    };
    const expectedDialogAttrs = [
        0x7F, 0x7A, 0x13, 0x13, 0x70, 0x70, 0x7F, 0x7E,
        0x20, 0x2B, 0x2F, 0x78, 0x2E, 0x70, 0x30, 0x3F, 0x3E,
        0x1F, 0x2F, 0x1A, 0x20, 0x72, 0x31, 0x31, 0x30, 0x2F,
        0x3E, 0x31, 0x13, 0x38,
    ];
    if (
        !colors.open || colors.buttonCount !== 4 || colors.resetAllCount !== 1 || colors.defaultCount !== 1
        || colors.foregroundColors !== 16 || colors.backgroundColors !== 8 || colors.sampleRows !== 2
        || !colors.groupFocused
        || colors.groupNormalColors.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || colors.groupFocusedColors.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()
        || colors.itemSelectedColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
        || colors.dialogDefaultAttrs.join() !== expectedDialogAttrs.join()
        || Object.entries(expectedColorsGeometry).some(([key, value]) => colors[key].join() !== value.join())
    ) {
        throw new Error(`Colors dialog differs from Turbo Vision 2.0: ${JSON.stringify(colors)}`);
    }
    const colorsListFocus = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-colors-window');
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        dialog.querySelector('[data-tv-colors-group="2"]').click();
        dialog.querySelector('[data-tv-colors-item="1"]').click();
        const group = dialog.querySelector('[data-tv-colors-group].is-selected');
        const item = dialog.querySelector('[data-tv-colors-item].is-selected');
        const result = {
            itemFocused: document.activeElement === item,
            groupColors: stylePair(group),
            itemColors: stylePair(item),
        };
        group.click();
        return result;
    })()`);
    if (
        !colorsListFocus.itemFocused
        || colorsListFocus.groupColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
        || colorsListFocus.itemColors.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()
    ) {
        throw new Error(`Colors list focus is inconsistent: ${JSON.stringify(colorsListFocus)}`);
    }
    const colorsReset = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-colors-window');
        const defaults = window.THelpViewerTV.buildDefaultColorPalette()[2].items;
        const foreground = () => Number(
            dialog.querySelector('[data-tv-colors-foreground] [aria-pressed="true"]').dataset.tvColorIndex
        );
        const chooseItem = (index) => dialog.querySelector('[data-tv-colors-item="' + index + '"]').click();
        const chooseForeground = (index) => dialog
            .querySelector('[data-tv-colors-foreground] [data-tv-color-index="' + index + '"]').click();

        chooseItem(1);
        const expectedFirst = defaults[1].attr & 0x0F;
        const changedFirst = (expectedFirst + 1) % 16;
        chooseForeground(changedFirst);

        chooseItem(2);
        const expectedSecond = defaults[2].attr & 0x0F;
        const changedSecond = (expectedSecond + 2) % 16;
        chooseForeground(changedSecond);

        chooseItem(1);
        dialog.querySelector('[data-tv-colors-default]').click();
        const defaultedFirst = foreground();
        chooseItem(2);
        const preservedSecond = foreground();

        dialog.querySelector('[data-tv-colors-reset-all]').click();
        const resetSecond = foreground();
        return {
            expectedFirst,
            expectedSecond,
            changedFirst,
            changedSecond,
            defaultedFirst,
            preservedSecond,
            resetSecond,
        };
    })()`);
    if (
        colorsReset.defaultedFirst !== colorsReset.expectedFirst
        || colorsReset.preservedSecond !== colorsReset.changedSecond
        || colorsReset.resetSecond !== colorsReset.expectedSecond
    ) {
        throw new Error(`Colors Default/Reset All did not restore the expected scope: ${JSON.stringify(colorsReset)}`);
    }
    const sharedPalette = await evaluate(`(() => {
        const palette = window.THelpViewerTV.buildDefaultColorPalette();
        const viewer = palette.find((group) => group.name === 'Viewer');
        const puzzle = palette.find((group) => group.name === 'Puzzle');
        window.THelpViewerTV.setColorPaletteAttribute(palette, 8, 0x4F);
        return {
            viewerDefaults: viewer.items.map((item) => item.attr),
            puzzleDefaults: puzzle.items.map((item) => item.attr),
            sharedPassive: [viewer.items[0].attr, puzzle.items[0].attr],
        };
    })()`);
    if (
        sharedPalette.viewerDefaults.slice(1).join() !== [0x1F, 0x1A, 0x31, 0x31, 0x1E].join()
        || sharedPalette.puzzleDefaults.slice(1).join() !== [0x1F, 0x1A, 0x31, 0x31, 0x1E, 0x71].join()
        || sharedPalette.sharedPassive.join() !== [0x4F, 0x4F].join()
    ) {
        throw new Error(`Shared TV 2.0 palette indexes are broken: ${JSON.stringify(sharedPalette)}`);
    }
    await evaluate(`document.querySelector('[data-tv-dialog-open="about"]').click()`);
    await pause();
    const passiveColors = await evaluate(`(() => {
        const colorsDialog = document.querySelector('.tv-colors-window');
        const selected = colorsDialog.querySelector('[data-tv-colors-group].is-selected');
        const corner = colorsDialog.querySelector('.tv-dialog-titlebar > .tv-border-corner');
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        return {
            inactive: colorsDialog.classList.contains('is-window-inactive'),
            cornerGlyph: corner.textContent,
            cornerColors: stylePair(corner),
            selectedColors: stylePair(selected),
            closeHidden: colorsDialog.querySelector('[data-tv-close-button]').hidden,
        };
    })()`);
    if (
        !passiveColors.inactive || passiveColors.cornerGlyph !== '┌' || !passiveColors.closeHidden
        || passiveColors.cornerColors.join() !== ['rgb(170, 170, 170)', 'rgb(0, 0, 0)'].join()
        || passiveColors.selectedColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
    ) {
        throw new Error(`Inactive Colors state differs from Turbo Vision 2.0: ${JSON.stringify(passiveColors)}`);
    }
    await evaluate(`document.querySelector('[data-tv-about-close]').click()`);
    await pause();
    await evaluate(`document.querySelector('[data-tv-colors-foreground] [aria-pressed="true"]').focus()`);
    const foregroundBefore = await evaluate(
        `Number(document.activeElement.getAttribute('data-tv-color-index'))`
    );
    await key("ArrowRight", "ArrowRight", 0, true);
    const foregroundAfter = await evaluate(
        `Number(document.querySelector('[data-tv-colors-foreground] [aria-pressed="true"]').getAttribute('data-tv-color-index'))`
    );
    if (foregroundAfter !== (foregroundBefore + 1) % 16) {
        throw new Error(`Colors selector ignored ArrowRight: ${foregroundBefore} -> ${foregroundAfter}`);
    }
    const colorsActiveBeforeEscape = await evaluate(
        `document.querySelector('.tv-colors-window').classList.contains('is-window-active')`
    );
    const colorsFocusBeforeEscape = await evaluate(
        `({tag: document.activeElement?.tagName, color: document.activeElement?.getAttribute('data-tv-color-index'), connected: document.activeElement?.isConnected})`
    );
    const colorsEscapePrevented = await key("Escape", "Escape", 0, true);
    await pause();
    const desktopDotAfterColors = await evaluate(
        `getComputedStyle(document.documentElement).getPropertyValue('--tv-desktop-dot').trim()`
    );
    const colorsClosed = await evaluate(
        `document.querySelector('.tv-colors-window').closest('.tv-dialog-overlay').hidden`
    );
    if (
        !colorsActiveBeforeEscape || !colorsEscapePrevented || !colorsClosed
        || colorsFocusBeforeEscape.tag !== 'BUTTON' || !colorsFocusBeforeEscape.connected
        || desktopDotAfterColors !== desktopDotBeforeColors
    ) {
        throw new Error(`Colors cancel did not restore the palette: ${desktopDotBeforeColors} -> ${desktopDotAfterColors}; closed=${colorsClosed}; active=${colorsActiveBeforeEscape}; prevented=${colorsEscapePrevented}; focus=${JSON.stringify(colorsFocusBeforeEscape)}`);
    }

    await evaluate(`document.querySelector('[data-tv-dialog-open="widgets"]').click()`);
    await pause();
    const gallerySetup = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Widget Gallery'
        );
        if (!dialog) { return { open: false }; }
        const label = dialog.querySelector('label[for="tv-widget-gallery-name"]');
        const input = dialog.querySelector('#tv-widget-gallery-name');
        label.click();
        const labelFocus = document.activeElement === input;
        dialog.querySelector('[data-tv-gallery-apply]').click();
        return {
            open: true,
            labelFocus,
        };
    })()`);
    if (!gallerySetup.open) { throw new Error('Widget Gallery did not open'); }
    await pause();
    const galleryPoint = await evaluate(`(() => {
        const item = document.querySelector('[data-tv-gallery-list-index="2"]');
        const rect = item.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed',
        x: galleryPoint.x,
        y: galleryPoint.y,
        button: 'left',
        clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased',
        x: galleryPoint.x,
        y: galleryPoint.y,
        button: 'left',
        clickCount: 1,
    });
    await pause();
    const gallery = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Widget Gallery'
        );
        if (!dialog) { return { open: false }; }
        const clickedItem = dialog.querySelector('[data-tv-gallery-list-index="2"]');
        const body = dialog.querySelector('.tv-widget-gallery-body');
        const bodyRect = body.getBoundingClientRect();
        const sideRects = Array.from(body.querySelectorAll(':scope > .tv-border-side'))
            .map((element) => element.getBoundingClientRect());
        const info = dialog.querySelector('.tv-widget-gallery-info .tv-info-box');
        const infoRows = Array.from(dialog.querySelectorAll('[data-tv-terminal-line]'));
        const infoRow = infoRows.at(-1);
        const infoRect = info.getBoundingClientRect();
        const rowRect = infoRow.getBoundingClientRect();
        const viewport = dialog.querySelector('[data-tv-gallery-list] [data-tv-list-viewport]');
        const firstItem = dialog.querySelector('[data-tv-gallery-list-index="0"]');
        const normalItem = dialog.querySelector('[data-tv-gallery-list-index="1"]');
        const check = dialog.querySelector('[data-tv-checkbox-index="0"]');
        const disabledCheck = dialog.querySelector('[data-tv-checkbox-index="2"]');
        const radio = dialog.querySelector('[data-tv-radio-index="0"]');
        const multiCheck = dialog.querySelector('[data-tv-multicheck-index="0"] [data-tv-multicheck-state]');
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        multiCheck.click();
        return {
            open: true,
            checks: dialog.querySelectorAll('[data-tv-gallery-checks] input[type="checkbox"]').length,
            radios: dialog.querySelectorAll('[data-tv-gallery-radios] input[type="radio"]').length,
            multiChecks: dialog.querySelectorAll('[data-tv-gallery-multichecks] [data-tv-multicheck-state]').length,
            multiStates: Array.from(dialog.querySelectorAll('[data-tv-gallery-multichecks] [data-tv-multicheck-state]'))
                .map((element) => element.getAttribute('aria-checked')),
            multiCycled: multiCheck.getAttribute('aria-checked'),
            disabledChoices: dialog.querySelectorAll('.tv-choice-input:disabled').length,
            listItems: dialog.querySelectorAll('[data-tv-gallery-list-index]').length,
            selectedItems: dialog.querySelectorAll('[data-tv-gallery-list-index].is-selected').length,
            selectedIndex: dialog.querySelector('[data-tv-gallery-list-index].is-selected')?.dataset.tvGalleryListIndex,
            listFocused: document.activeElement === clickedItem,
            disabledButtons: dialog.querySelectorAll('.tv-dialog-button:disabled').length,
            messageButtons: dialog.querySelectorAll('[data-tv-gallery-message]').length,
            staticTexts: dialog.querySelectorAll('[data-tv-gallery-static]').length,
            status: dialog.querySelector('[data-tv-gallery-terminal]')?.textContent || '',
            terminalRows: infoRows.length,
            firstRowOffset: Math.abs(firstItem.getBoundingClientRect().top - viewport.getBoundingClientRect().top),
            scrollbarEnabled: !dialog.querySelector('[data-tv-gallery-list]').classList.contains('is-disabled'),
            listNormalColors: stylePair(normalItem),
            listFocusedColors: stylePair(clickedItem),
            checkColors: stylePair(check),
            radioColors: stylePair(radio),
            disabledCheckColors: stylePair(disabledCheck),
            checkHotkeyColor: getComputedStyle(check.querySelector('.tv-hotkey')).color,
            infoRightBorder: infoRow.textContent.endsWith('│'),
            infoRowFits: rowRect.right <= infoRect.right + 0.5 && info.scrollWidth <= info.clientWidth,
            infoSideColors: Array.from(infoRow.querySelectorAll('[data-tv-info-side]'))
                .map((element) => getComputedStyle(element).color),
            frameSidesAligned: sideRects.length === 2 && sideRects.every((rect) =>
                Math.abs(rect.top - bodyRect.top) < 1 && Math.abs(rect.height - bodyRect.height) < 1
            ),
        };
    })()`);
    if (
        !gallery.open || !gallerySetup.labelFocus || gallery.checks !== 3 || gallery.radios !== 3
        || gallery.multiChecks !== 3 || gallery.multiStates.join() !== ['true', 'true', 'mixed'].join()
        || gallery.multiCycled !== 'true'
        || gallery.disabledChoices !== 2 || gallery.listItems !== 13 || gallery.selectedItems !== 1
        || gallery.selectedIndex !== '2' || !gallery.listFocused
        || gallery.disabledButtons !== 1 || gallery.messageButtons !== 1 || gallery.staticTexts !== 1
        || !gallery.status.includes('Selected: TListViewer') || !gallery.status.includes('mode: state 1')
        || gallery.firstRowOffset > 0.5
        || !gallery.scrollbarEnabled
        || gallery.listNormalColors.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || gallery.listFocusedColors.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()
        || gallery.checkColors.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || gallery.radioColors.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || gallery.disabledCheckColors.join() !== ['rgb(0, 170, 170)', 'rgb(85, 85, 85)'].join()
        || gallery.checkHotkeyColor !== 'rgb(255, 255, 85)'
        || gallery.terminalRows !== 3 || !gallery.infoRightBorder || !gallery.infoRowFits
        || gallery.infoSideColors.some((color) => color !== 'rgb(255, 255, 255)')
        || !gallery.frameSidesAligned
    ) {
        throw new Error(`Widget Gallery controls are incomplete: ${JSON.stringify(gallery)}`);
    }
    await evaluate(`document.querySelector('[data-tv-gallery-message]').click()`);
    await pause();
    const messageOpen = await evaluate(`(() => {
        const box = document.querySelector('.tv-msgbox-window');
        return Boolean(box && !box.closest('.tv-dialog-overlay').hidden)
            && box.querySelector('.tv-dialog-title-text')?.textContent === 'Information';
    })()`);
    if (!messageOpen) { throw new Error('Widget Gallery message box did not open'); }
    await key("Escape", "Escape", 0, true);
    await pause();
    const messageResult = await evaluate(
        `document.querySelector('[data-tv-gallery-terminal]')?.textContent || ''`
    );
    if (!messageResult.includes('Message: cancel')) {
        throw new Error(`Widget Gallery message box did not report Cancel: ${messageResult}`);
    }
    await key("Escape", "Escape", 0, true);
    await pause();
    const galleryClosed = await evaluate(
        `Array.from(document.querySelectorAll('.tv-dialog-title-text'))
            .filter((element) => element.textContent === 'Widget Gallery')
            .every((element) => element.closest('.tv-dialog-overlay').hidden)`
    );
    if (!galleryClosed) { throw new Error("Escape did not close Widget Gallery"); }

    await evaluate(`document.querySelector('[data-tv-dialog-open="chdir"]').click()`);
    await pause();
    const changeDirectory = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Change Directory'
        );
        const historyPopup = dialog?.querySelector('[data-tv-change-dir-history-popup]');
        const historyHidden = Boolean(
            historyPopup?.hidden && getComputedStyle(historyPopup).display === 'none'
        );
        const slash = String.fromCharCode(92);
        const docs = Array.from(dialog?.querySelectorAll('[data-tv-change-dir-index]') || []).find((item) =>
            item.textContent.trim().endsWith('DOCS' + slash)
        );
        docs?.click();
        const selectedPath = dialog?.querySelector('[data-tv-change-dir-path]')?.value;
        dialog?.querySelector('[data-tv-change-dir-revert]')?.click();
        const revertedPath = dialog?.querySelector('[data-tv-change-dir-path]')?.value;
        dialog?.querySelector('[data-tv-change-dir-confirm]')?.click();
        return {
            open: Boolean(dialog),
            directories: dialog?.querySelectorAll('[data-tv-change-dir-index]').length || 0,
            sharedScrollbar: Boolean(dialog?.querySelector('[data-tv-change-dir-list] .tv-scrollbar-y')),
            outline: dialog?.querySelector('[data-tv-change-dir-list]')?.dataset.tvListViewer === '1'
                && Array.from(dialog?.querySelectorAll('[data-tv-change-dir-index]') || [])
                    .some((item) => /[▼►]/.test(item.textContent)),
            selectedPath,
            revertedPath,
            closed: Boolean(dialog?.closest('.tv-dialog-overlay').hidden),
            history: JSON.parse(localStorage.getItem('thelp:directory-history') || '[]'),
            historyHidden,
            slash,
        };
    })()`);
    if (
        !changeDirectory.open || changeDirectory.directories < 3 || !changeDirectory.sharedScrollbar || !changeDirectory.outline
        || !changeDirectory.selectedPath.endsWith('DOCS' + changeDirectory.slash)
        || changeDirectory.revertedPath !== 'THelpViewer:' + changeDirectory.slash
        || !changeDirectory.closed || changeDirectory.history[0] !== '.' || !changeDirectory.historyHidden
    ) {
        throw new Error(`Change Directory is incomplete: ${JSON.stringify(changeDirectory)}`);
    }
    await evaluate(`document.querySelector('[data-tv-dialog-open="chdir"]').click()`);
    await pause();
    const changeDirectoryHistoryInitial = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-change-dir-history]');
        const popup = document.querySelector('[data-tv-change-dir-history-popup]');
        const initiallyHidden = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none');
        const rect = button?.querySelector('.tv-file-open-history-arrow')?.getBoundingClientRect();
        return {
            enabled: !button?.disabled,
            initiallyHidden,
            point: rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null,
        };
    })()`);
    if (!changeDirectoryHistoryInitial.enabled || !changeDirectoryHistoryInitial.initiallyHidden
        || !changeDirectoryHistoryInitial.point) {
        throw new Error(`Change Directory history is unavailable: ${JSON.stringify(changeDirectoryHistoryInitial)}`);
    }
    await clickPoint(changeDirectoryHistoryInitial.point);
    const changeDirectoryHistoryOpened = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-change-dir-history]');
        const popup = document.querySelector('[data-tv-change-dir-history-popup]');
        return !popup?.hidden && getComputedStyle(popup).display !== 'none'
            && button?.getAttribute('aria-expanded') === 'true';
    })()`);
    await clickPoint(changeDirectoryHistoryInitial.point);
    const changeDirectoryHistoryClosed = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-change-dir-history]');
        const popup = document.querySelector('[data-tv-change-dir-history-popup]');
        return popup?.hidden && getComputedStyle(popup).display === 'none'
            && button?.getAttribute('aria-expanded') === 'false';
    })()`);
    if (!changeDirectoryHistoryOpened || !changeDirectoryHistoryClosed) {
        throw new Error(`Change Directory physical history toggle is broken: ${JSON.stringify({
            changeDirectoryHistoryOpened, changeDirectoryHistoryClosed,
        })}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`document.querySelector('[data-tv-file-open]').click()`);
    await pause();
    const fileOpen = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        if (!dialog) { return { open: false }; }
        const slash = String.fromCharCode(92);
        const rootItems = Array.from(dialog.querySelectorAll('[data-tv-file-open-file-index]'));
        const rootDirectories = rootItems.filter((element) => element.textContent.trim().endsWith(slash));
        const docsDirectory = rootDirectories.find((element) => element.textContent.trim() === "DOCS" + slash);
        if (!docsDirectory) { return { open: true, docsDirectory: false }; }
        docsDirectory.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
        const docItems = Array.from(dialog.querySelectorAll('[data-tv-file-open-file-index]'));
        const firstFile = docItems.find((element) => !element.textContent.trim().endsWith(slash));
        if (!firstFile) { return { open: true, docsDirectory: true, files: 0 }; }
        firstFile.click();
        const input = dialog.querySelector('[data-tv-file-open-name]');
        const fileList = dialog.querySelector('[data-tv-file-open-files]');
        const titlebar = dialog.querySelector('.tv-dialog-titlebar');
        const title = dialog.querySelector('.tv-dialog-title-text');
        const dialogRect = dialog.getBoundingClientRect();
        const titleRect = title.getBoundingClientRect();
        const selectedItem = dialog.querySelector('[data-tv-file-open-file-index].is-selected');
        const normalItem = Array.from(dialog.querySelectorAll('[data-tv-file-open-file-index]'))
            .find((element) => element !== selectedItem);
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        input.focus();
        return {
            open: !dialog.closest('.tv-dialog-overlay').hidden,
            modal: dialog.getAttribute('aria-modal'),
            docsDirectory: true,
            files: docItems.length,
            rootDirectories: rootDirectories.length,
            internalFrames: dialog.querySelectorAll('.tv-vlist-framed').length,
            outerTitleCorners: dialog.querySelectorAll('.tv-dialog-titlebar > .tv-border-corner').length,
            outerFooterCorners: dialog.querySelectorAll('.tv-dialog-footer > .tv-border-corner').length,
            outerTitleFills: titlebar.querySelectorAll(':scope > .tv-border-fill').length,
            titleCenterOffset: Math.abs(
                (titleRect.left + titleRect.width / 2) - (dialogRect.left + dialogRect.width / 2)
            ),
            twoColumnFlow: getComputedStyle(fileList).gridAutoFlow,
            horizontalScrollbar: Boolean(dialog.querySelector('[data-tv-file-open-hscroll]')),
            path: (dialog.querySelector('[data-tv-file-open-path]')?.textContent || '').trim(),
            name: input.value,
            focused: document.activeElement === input,
            selectedColors: stylePair(selectedItem),
            selectedTextColors: stylePair(selectedItem.querySelector('.tv-vlist-text')),
            normalColors: stylePair(normalItem),
            normalTextColors: stylePair(normalItem.querySelector('.tv-vlist-text')),
            visibleText: docItems.every((element) => {
                const text = element.querySelector('.tv-vlist-text');
                const style = getComputedStyle(text);
                const itemRect = element.getBoundingClientRect();
                const textRect = text.getBoundingClientRect();
                return Boolean(text.textContent.trim()) && style.visibility === 'visible'
                    && style.opacity === '1' && style.color !== style.backgroundColor
                    && textRect.height > 0 && textRect.top >= itemRect.top
                    && textRect.bottom <= itemRect.bottom;
            }),
            historyArrowColors: stylePair(dialog.querySelector('.tv-file-open-history-arrow')),
            historySideColors: stylePair(dialog.querySelector('.tv-file-open-history-side')),
        };
    })()`);
    if (
        !fileOpen.open || fileOpen.modal !== "true" || !fileOpen.docsDirectory
            || fileOpen.files < 2 || fileOpen.rootDirectories !== 2 || fileOpen.internalFrames !== 0
            || fileOpen.outerTitleCorners !== 2 || fileOpen.outerFooterCorners !== 2
            || fileOpen.outerTitleFills !== 1 || fileOpen.titleCenterOffset > 1
        || fileOpen.twoColumnFlow !== "column" || !fileOpen.horizontalScrollbar
        || fileOpen.path !== ["THelpViewer:", "DOCS", "*.*"].join(String.fromCharCode(92))
        || !fileOpen.name || !fileOpen.focused
        || fileOpen.selectedColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
        || fileOpen.selectedTextColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
        || fileOpen.normalColors.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || fileOpen.normalTextColors.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || !fileOpen.visibleText
        || fileOpen.historyArrowColors.join() !== ['rgb(0, 170, 0)', 'rgb(0, 0, 0)'].join()
        || fileOpen.historySideColors.join() !== ['rgb(170, 170, 170)', 'rgba(0, 0, 0, 0)'].join()
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
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        const initiallyHidden = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none');
        button.click();
        const input = document.querySelector('[data-tv-file-open-name]');
        const popupStyle = getComputedStyle(popup);
        const selected = popup?.querySelector('[data-tv-file-open-history-index].is-selected');
        const selectedStyle = getComputedStyle(selected);
        const arrowStyle = getComputedStyle(button.querySelector('.tv-file-open-history-arrow'));
        const sideStyles = Array.from(
            button.querySelectorAll('.tv-file-open-history-side'),
            (element) => getComputedStyle(element),
        );
        const cellWidth = input.getBoundingClientRect().width / 28;
        return {
            enabled: !button.disabled,
            initiallyHidden,
            open: Boolean(popup && !popup.hidden),
            entries: popup?.querySelectorAll('[data-tv-file-open-history-index]').length || 0,
            columns: Math.round(popup.getBoundingClientRect().width / cellWidth),
            frame: [popupStyle.backgroundColor, popupStyle.color],
            selected: [selectedStyle.backgroundColor, selectedStyle.color],
            arrow: [arrowStyle.backgroundColor, arrowStyle.color],
            sides: sideStyles.map((style) => ({
                background: style.backgroundColor,
                color: style.color,
                image: style.backgroundImage,
            })),
            popupAboveButton: Number(popupStyle.zIndex) > Number(getComputedStyle(button).zIndex),
            corners: popup?.querySelectorAll('.tv-history-frame-corner').length || 0,
            closeButtons: popup?.querySelectorAll('[data-tv-history-close]').length || 0,
        };
    })()`);
    if (!historyOpen.enabled || !historyOpen.initiallyHidden || !historyOpen.open || historyOpen.entries !== 1
        || historyOpen.columns !== 32 || historyOpen.corners !== 4 || historyOpen.closeButtons !== 1
        || historyOpen.frame.join() !== ['rgb(0, 0, 170)', 'rgb(255, 255, 255)'].join()
        || historyOpen.selected.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()
        || historyOpen.arrow.join() !== ['rgb(0, 170, 0)', 'rgb(0, 0, 0)'].join()
        || historyOpen.sides.some((side) => side.background !== 'rgb(170, 170, 170)'
            || side.color !== 'rgba(0, 0, 0, 0)'
            || !side.image.includes('linear-gradient')
            || !side.image.includes('rgb(0, 170, 0)'))
        || !historyOpen.popupAboveButton) {
        throw new Error(`File Open history does not match THistoryWindow: ${JSON.stringify(historyOpen)}`);
    }
    const fileHistoryClosePoint = await evaluate(`(() => {
        const rect = document.querySelector('[data-tv-file-open-history-popup] [data-tv-history-close]')
            ?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!fileHistoryClosePoint) { throw new Error('History window close control is missing'); }
    await clickPoint(fileHistoryClosePoint);
    const fileHistoryFrameClosed = await evaluate(`(() => {
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        return popup.hidden && getComputedStyle(popup).display === 'none';
    })()`);
    if (!fileHistoryFrameClosed) { throw new Error('History window close control did not close it'); }
    const fileHistoryArrowPoint = await evaluate(`(() => {
        const rect = document.querySelector(
            '[data-tv-file-open-history] .tv-file-open-history-arrow'
        )?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!fileHistoryArrowPoint) { throw new Error("File Open History arrow is missing"); }
    await clickPoint(fileHistoryArrowPoint);
    const fileHistoryReopened = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-file-open-history]');
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        const arrowRect = button.querySelector('.tv-file-open-history-arrow').getBoundingClientRect();
        const front = document.elementFromPoint(
            arrowRect.left + arrowRect.width / 2,
            arrowRect.top + arrowRect.height / 2
        );
        return {
            open: !popup.hidden && getComputedStyle(popup).display !== 'none'
                && button.getAttribute('aria-expanded') === 'true',
            triggerCovered: Boolean(front && popup.contains(front)),
        };
    })()`);
    await clickPoint(fileHistoryClosePoint);
    const fileHistoryClosed = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-file-open-history]');
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        return popup.hidden && getComputedStyle(popup).display === 'none'
            && button.getAttribute('aria-expanded') === 'false';
    })()`);
    if (!fileHistoryClosed || !fileHistoryReopened.open || !fileHistoryReopened.triggerCovered) {
        throw new Error(`File Open physical history lifecycle is broken: ${JSON.stringify({
            fileHistoryClosed, fileHistoryReopened,
        })}`);
    }
    await clickPoint(fileHistoryArrowPoint);
    const fileHistoryOutsidePoint = await evaluate(`(() => {
        const rect = document.querySelector('.tv-file-open-info')?.getBoundingClientRect();
        return rect ? { x: rect.left + 2, y: rect.top + 2 } : null;
    })()`);
    if (!fileHistoryOutsidePoint) { throw new Error('File Open info pane is missing'); }
    await clickPoint(fileHistoryOutsidePoint);
    const fileHistoryOutsideClosed = await evaluate(`(() => {
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        const dialog = popup?.closest('.tv-dialog-overlay');
        return Boolean(popup?.hidden && dialog && !dialog.hidden);
    })()`);
    if (!fileHistoryOutsideClosed) { throw new Error('Click outside did not close File Open history'); }
    await clickPoint(fileHistoryArrowPoint);
    await pause();
    await key("Escape", "Escape", 0, true);
    const escapeClosedHistoryOnly = await evaluate(`(() => {
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        const dialog = popup.closest('.tv-dialog-overlay');
        return popup.hidden && getComputedStyle(popup).display === 'none' && !dialog.hidden;
    })()`);
    if (!escapeClosedHistoryOnly) { throw new Error("Escape did not close File Open history first"); }
    await key("Escape", "Escape", 0, true);

    const restoredHash = "#tv=1.eyJ2IjoxLCJhIjowLCJ6IjpbMSwwXSwidyI6W3sidCI6ImgiLCJmIjoiQm9ybGFuZCBTaWRla2ljayAyL3NrMi5qc29uLmd6IiwidmlldyI6InRvcGljIiwiZyI6WzIxNywxMjYsNTQsMjEsMF0sInRvcGljIjoiMTI4IiwibGluZSI6MSwicyI6WzAsMF19LHsidCI6ImRsZyIsIm5hbWUiOiJmaWxlb3BlbiIsImciOlsyMzcsMTQyLDQ5LDE5LDBdfV19";
    await send("Page.navigate", { url: appUrl + "?restore=1" + restoredHash });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const open = document.querySelector('[data-tv-file-open-files]');
            const more = document.querySelector('[data-tv-line="17"] [data-tv-bundle-topic="327"]');
            if (open?.querySelectorAll('[data-tv-file-open-file-index]').length >= 2 && more) {
                resolve(true);
                return;
            }
            if (Date.now() >= deadline) { reject(new Error('saved File Open state did not restore')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const restored = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        const overlay = dialog.closest('.tv-dialog-overlay');
        const helpWindow = document.querySelector('[data-tv-bundle-window]');
        const helpScrollbar = helpWindow.querySelector('.tv-scrollbar-y');
        const titlebar = dialog.querySelector('.tv-dialog-titlebar');
        titlebar.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            clientX: 300,
            clientY: 160,
        }));
        const moving = dialog.classList.contains('is-dragging');
        const movingCorner = titlebar.querySelector('.tv-border-corner')?.textContent;
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        return {
            entries: dialog.querySelectorAll('[data-tv-file-open-file-index]').length,
            active: dialog.classList.contains('is-window-active'),
            dialogZ: Number(getComputedStyle(overlay).zIndex),
            helpZ: Number(getComputedStyle(helpWindow).zIndex),
            helpScrollbarInactive: helpScrollbar.classList.contains('is-inactive'),
            helpScrollbarColors: [
                getComputedStyle(helpScrollbar).color,
                getComputedStyle(helpScrollbar.querySelector('.tv-scroll-arrow')).color,
            ],
            moreTarget: document.querySelector('[data-tv-line="17"] [data-tv-bundle-topic="327"]')?.textContent,
            moving,
            movingCorner,
            restingCorner: titlebar.querySelector('.tv-border-corner')?.textContent,
        };
    })()`);
    if (
        restored.entries < 2 || !restored.active || restored.dialogZ <= restored.helpZ
        || !restored.helpScrollbarInactive
        || restored.helpScrollbarColors.some((color) => color !== 'rgb(0, 170, 170)')
        || restored.moreTarget !== "<more>" || !restored.moving
        || restored.movingCorner !== "┌" || restored.restingCorner !== "╔"
    ) {
        throw new Error(`Saved File Open state is incomplete: ${JSON.stringify(restored)}`);
    }
    await key("Escape", "Escape", 0, true);
    await evaluate(`document.querySelector('[data-tv-line="17"] [data-tv-bundle-topic="327"]').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const body = document.querySelector('[data-tv-bundle-window] [data-tv-viewport]')?.textContent || '';
            if (body.includes('Use the Edit|Paste command')) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('THELP continuation did not open')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        const entry = Array.from(document.querySelectorAll('[data-tv-bundle-open]')).find((element) =>
            element.dataset.tvBundleOpen === 'Norton Guides/vista.json.gz'
        );
        if (!entry) { throw new Error('Norton Guides browser fixture is missing'); }
        entry.click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const windowElement = Array.from(document.querySelectorAll('[data-tv-bundle-window]')).find((element) =>
                element.querySelector('.tv-window-caption')?.textContent.includes('db_VISTA III')
            );
            if (windowElement) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('Norton Guides window did not open')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const nortonColors = await evaluate(`(() => {
        const windowElement = Array.from(document.querySelectorAll('[data-tv-bundle-window]')).find((element) =>
            element.querySelector('.tv-window-caption')?.textContent.includes('db_VISTA III')
        );
        const color = (selector, property = 'color') =>
            getComputedStyle(windowElement.querySelector(selector))[property];
        return {
            frame: color('.tv-border-corner-tl'),
            titleBg: color('.tv-window-caption', 'backgroundColor'),
            titleFg: color('.tv-window-caption'),
            closeFg: color('.tv-close-control'),
            closeGlyph: color('.tv-close-glyph'),
            zoomGlyph: color('.tv-zoom-glyph'),
            arrowFg: color('.tv-scroll-arrow'),
            thumbFg: getComputedStyle(windowElement).getPropertyValue('--tv-owner-scroll-thumb-fg').trim(),
        };
    })()`);
    if (
        nortonColors.frame !== 'rgb(170, 170, 170)'
        || nortonColors.titleBg !== 'rgb(0, 0, 170)'
        || nortonColors.titleFg !== 'rgb(255, 255, 255)'
        || nortonColors.closeFg !== 'rgb(255, 255, 255)'
        || nortonColors.closeGlyph !== 'rgb(255, 255, 85)'
        || nortonColors.zoomGlyph !== 'rgb(255, 255, 85)'
        || nortonColors.arrowFg !== 'rgb(85, 255, 255)'
        || nortonColors.thumbFg !== '#ffffff'
    ) {
        throw new Error(`Norton Guides frame palette is broken: ${JSON.stringify(nortonColors)}`);
    }
    const nortonMovingColors = await evaluate(`(() => {
        const windowElement = Array.from(document.querySelectorAll('[data-tv-bundle-window]')).find((element) =>
            element.querySelector('.tv-window-caption')?.textContent.includes('db_VISTA III')
        );
        const titlebar = windowElement.querySelector('[data-tv-move-handle]');
        const rect = titlebar.getBoundingClientRect();
        titlebar.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            clientX: rect.left + rect.width / 2,
            clientY: rect.top + rect.height / 2,
        }));
        const pair = (selector) => {
            const style = getComputedStyle(windowElement.querySelector(selector));
            return [style.backgroundColor, style.color];
        };
        const result = {
            moving: windowElement.classList.contains('is-moving'),
            title: pair('.tv-window-caption'),
            close: pair('.tv-close-control'),
            closeGlyph: getComputedStyle(windowElement.querySelector('.tv-close-glyph')).color,
        };
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        return result;
    })()`);
    if (
        !nortonMovingColors.moving
        || nortonMovingColors.title.join() !== ['rgb(0, 0, 170)', 'rgb(255, 255, 255)'].join()
        || nortonMovingColors.close.join() !== ['rgb(0, 0, 170)', 'rgb(255, 255, 255)'].join()
        || nortonMovingColors.closeGlyph !== 'rgb(255, 255, 85)'
    ) {
        throw new Error(`Norton Guides moving palette is broken: ${JSON.stringify(nortonMovingColors)}`);
    }

    const reportedState = "#tv=1.eyJ2IjoxLCJhIjoyLCJ6IjpbMSwwLDMsMl0sInciOlt7InQiOiJoIiwiZiI6Ik5vcnRvbiBHdWlkZXMvdmlzdGEuanNvbi5neiIsInZpZXciOiJ0b3BpYyIsImciOls2LDE4OSw4MiwyNCwwXSwidG9waWMiOiIzNzgiLCJsaW5lIjoxLCJzIjpbMCwwXX0seyJ0IjoiaCIsImYiOiJOb3J0b24gR3VpZGVzL2RlYnVnLmpzb24uZ3oiLCJ2aWV3IjoidG9waWMiLCJnIjpbMTA1LDEwMiw4MiwyNCwwXSwidG9waWMiOiIzNzgiLCJsaW5lIjoxLCJzIjpbMCwwXX0seyJ0IjoiaCIsImYiOiJCb3JsYW5kIEMrKyAzLngvdHZjaGVscC5qc29uLmd6IiwidmlldyI6InRvcGljIiwiZyI6Wzk3LDcwLDg0LDI4LDBdLCJ0b3BpYyI6IjEyMCIsImxpbmUiOjEsInMiOlswLDBdfSx7InQiOiJkb2MiLCJmIjoiUkVBRE1FLm1kIiwiZyI6WzQ3LDE3LDk3LDMyLDBdLCJzIjpbMCwzMzMzXX1dfQ";
    await send("Page.navigate", { url: appUrl + "?reported=1" + reportedState });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const readme = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
                element.querySelector('.tv-window-caption')?.textContent === 'README'
            );
            if (readme?.querySelectorAll('table').length >= 2) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('reported README table state did not restore')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const readmeTable = await evaluate(`(() => {
        const readme = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
            element.querySelector('.tv-window-caption')?.textContent === 'README'
        );
        const table = Array.from(readme.querySelectorAll('table')).find((candidate) =>
            candidate.querySelectorAll('thead th').length === 6
        );
        const style = getComputedStyle(table);
        const cells = Array.from(table.querySelectorAll('th, td'));
        return {
            found: Boolean(table),
            layout: style.tableLayout,
            widthMode: style.width,
            overflowWraps: [...new Set(cells.map((cell) => getComputedStyle(cell).overflowWrap))],
            wordBreaks: [...new Set(cells.map((cell) => getComputedStyle(cell).wordBreak))],
            horizontalOverflow: table.scrollWidth > readme.querySelector('[data-tv-viewport]')?.clientWidth,
            minCellWidth: Math.min(...cells.map((cell) => cell.getBoundingClientRect().width)),
        };
    })()`);
    if (
        !readmeTable.found || readmeTable.layout !== 'auto'
        || readmeTable.overflowWraps.join() !== 'normal'
        || readmeTable.wordBreaks.join() !== 'normal'
        || readmeTable.minCellWidth < 30
    ) {
        throw new Error(`README table layout is broken: ${JSON.stringify(readmeTable)}`);
    }

    const inactiveFrameState = "#tv=1.eyJ2IjoxLCJhIjowLCJ6IjpbMSwwXSwidyI6W3sidCI6ImgiLCJmIjoiQm9ybGFuZCBDKysgMi4wIERPUyBjdXJyZW50L3RjaGVscC5qc29uLmd6IiwidmlldyI6InRvcGljIiwiZyI6WzkzLDE0MCw4NCwyOCwwXSwidG9waWMiOiIxMTY1IiwibGluZSI6MSwicyI6WzAsMF19LHsidCI6ImRvYyIsImYiOiJSRUFETUUubWQiLCJnIjpbNDcsMTcsOTcsMzIsMF0sInMiOlswLDcyMl19XX0";
    await send("Page.navigate", { url: appUrl + "?inactive-frame=1" + inactiveFrameState });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const readme = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
                element.querySelector('.tv-window-caption')?.textContent === 'README'
            );
            const help = document.querySelector('[data-tv-bundle-window]');
            if (readme && help) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('reported inactive-frame state did not restore')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const inspectPassiveFrame = `(windowElement) => {
        const top = windowElement.querySelector('.tv-border-top');
        const windowRect = windowElement.getBoundingClientRect();
        const topRect = top.getBoundingClientRect();
        const cells = Array.from(top.children)
            .filter((cell) => getComputedStyle(cell).display !== 'none')
            .map((cell) => cell.getBoundingClientRect());
        const gaps = cells.slice(1).map((cell, index) => cell.left - cells[index].right);
        const captionRect = top.querySelector('.tv-window-caption').getBoundingClientRect();
        const controls = Array.from(top.querySelectorAll('.tv-close-control, .tv-zoom-control'));
        return {
            inactive: windowElement.classList.contains('is-window-inactive'),
            leftCorner: top.querySelector('.tv-border-corner-tl')?.textContent,
            rightCorner: top.querySelector('.tv-border-corner-tr')?.textContent,
            rightEdgeDelta: Math.abs(windowRect.right - cells[cells.length - 1].right),
            maxGap: Math.max(0, ...gaps),
            captionCenterDelta: Math.abs(
                (captionRect.left + captionRect.width / 2) - (topRect.left + topRect.width / 2)
            ),
            growGlyph: windowElement.querySelector('.tv-grow-handle')?.textContent,
            controls: controls.map((control) => ({
                hidden: control.hidden,
                passive: control.classList.contains('is-frame-control-passive'),
                ariaHidden: control.getAttribute('aria-hidden'),
                ariaDisabled: control.getAttribute('aria-disabled'),
                tabIndex: control.tabIndex,
                display: getComputedStyle(control).display,
            })),
        };
    }`;
    const readmePassiveFrame = await evaluate(`(() => {
        const readme = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
            element.querySelector('.tv-window-caption')?.textContent === 'README'
        );
        return (${inspectPassiveFrame})(readme);
    })()`);
    const passiveFrameIsIntact = (frame) => (
        frame.inactive && frame.leftCorner === '┌' && frame.rightCorner === '┐'
        && frame.growGlyph === '─┘'
        && frame.rightEdgeDelta < 1 && frame.maxGap < 1 && frame.captionCenterDelta < 1
        && frame.controls.length === 2
        && frame.controls.every((control) => (
            !control.hidden && control.passive && control.ariaHidden === 'true'
            && control.ariaDisabled === 'true' && control.tabIndex === -1
            && control.display !== 'none'
        ))
    );
    if (!passiveFrameIsIntact(readmePassiveFrame)) {
        throw new Error(`Inactive README frame collapsed: ${JSON.stringify(readmePassiveFrame)}`);
    }
    await evaluate(`(() => {
        const readme = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
            element.querySelector('.tv-window-caption')?.textContent === 'README'
        );
        readme.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
    })()`);
    await pause();
    const helpPassiveFrame = await evaluate(`(() => {
        return (${inspectPassiveFrame})(document.querySelector('[data-tv-bundle-window]'));
    })()`);
    if (!passiveFrameIsIntact(helpPassiveFrame)) {
        throw new Error(`Inactive TCHELP frame collapsed: ${JSON.stringify(helpPassiveFrame)}`);
    }

    await evaluate(`(() => {
        const readme = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
            element.querySelector('.tv-window-caption')?.textContent === 'README'
        );
        const link = readme?.querySelector('a[href="docs/THelp%20Viewer/Bundle.md"]');
        if (!link) { throw new Error('README Bundle link is missing'); }
        link.click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const bundleDoc = Array.from(document.querySelectorAll('.tv-doc-window')).find((element) =>
                element.querySelector('.tv-window-caption')?.textContent === 'THelp Viewer/Bundle'
            );
            if (bundleDoc) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('README docs/ link did not open in the viewer')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);

    await evaluate(`document.querySelector('[data-tv-dialog-open="midi"]').click()`);
    await pause();
    const midiCompact = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'CD/MIDI Player'
        );
        const advanced = dialog?.querySelector('[data-tv-midi-advanced]');
        const list = dialog?.querySelector('[data-tv-midi-track-list]');
        const side = dialog?.querySelector('.tv-dialog-body > .tv-border-side');
        const displayParts = Array.from(dialog?.querySelectorAll(
            '.tv-midi-display-label, .tv-midi-track-number, .tv-midi-display-time, .tv-midi-display-title, .tv-midi-status'
        ) || []);
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            advancedHidden: Boolean(advanced?.hidden),
            moreCollapsed: dialog?.querySelector('[data-tv-midi-more]')?.getAttribute('aria-expanded') === 'false',
            sharedScrollbar: Boolean(list?.querySelector('.tv-scrollbar-y [data-role="thumb"]')),
            height: dialog?.getBoundingClientRect().height || 0,
            sideGlyphs: side?.textContent.split('\\n').length || 0,
            displayTextVisible: displayParts.length === 5 && displayParts.every((element) => {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return Boolean(element.textContent.trim()) && rect.width > 0 && rect.height > 0
                    && style.color !== style.backgroundColor;
            }),
        };
    })()`);
    if (
        !midiCompact.open || !midiCompact.advancedHidden || !midiCompact.moreCollapsed
        || !midiCompact.sharedScrollbar || !midiCompact.displayTextVisible
    ) {
        throw new Error(`MIDI compact mode is incomplete: ${JSON.stringify(midiCompact)}`);
    }
    await evaluate(`document.querySelector('[data-tv-midi-more]').click()`);
    await pause();
    const midiExpanded = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'CD/MIDI Player'
        );
        const side = dialog?.querySelector('.tv-dialog-body > .tv-border-side');
        return {
            advancedVisible: !dialog?.querySelector('[data-tv-midi-advanced]')?.hidden,
            moreExpanded: dialog?.querySelector('[data-tv-midi-more]')?.getAttribute('aria-expanded') === 'true',
            height: dialog?.getBoundingClientRect().height || 0,
            sideGlyphs: side?.textContent.split('\\n').length || 0,
        };
    })()`);
    if (
        !midiExpanded.advancedVisible || !midiExpanded.moreExpanded
        || midiExpanded.height <= midiCompact.height
        || midiExpanded.sideGlyphs <= midiCompact.sideGlyphs
    ) {
        throw new Error(`MIDI expanded frame was not redrawn: ${JSON.stringify({ midiCompact, midiExpanded })}`);
    }
    await key("Escape", "Escape", 0, true);

    const tableState = "#tv=1.eyJ2IjoxLCJhIjoxLCJ6IjpbMCwyLDFdLCJ3IjpbeyJ0IjoiaCIsImYiOiJOb3J0b24gR3VpZGVzL2RlYnVnLmpzb24uZ3oiLCJ2aWV3IjoidG9waWMiLCJnIjpbMCw0Miw4MiwyNCwwXSwidG9waWMiOiI1NzU2NCIsImxpbmUiOjEsInMiOlswLDBdfSx7InQiOiJoIiwiZiI6IkJvcmxhbmQgQysrIDMueC90dmNoZWxwLmpzb24uZ3oiLCJ2aWV3IjoidG9waWMiLCJnIjpbMTk1LDE0MCw4NCwyOCwwXSwidG9waWMiOiIxMjEiLCJsaW5lIjoxOCwicyI6WzAsMzI4XX0seyJ0IjoiZGxnIiwibmFtZSI6ImNhbGVuZGFyIiwiZyI6WzMyNSwyMDYsMjcsMTEsMF19XX0";
    await send("Page.navigate", { url: appUrl + "?thelp-table=1" + tableState });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const row = Array.from(document.querySelectorAll('[data-tv-bundle-window] .tv-topic-line')).find((line) =>
                line.textContent.includes('allocateDiscardable')
            );
            if (row?.textContent.includes('append') && row?.textContent.includes(' at ')) {
                resolve(true);
                return;
            }
            if (Date.now() >= deadline) { reject(new Error('TVCHELP table rows did not restore')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const tvcHelpTable = await evaluate(`(() => {
        const row = Array.from(document.querySelectorAll('[data-tv-bundle-window] .tv-topic-line')).find((line) =>
            line.textContent.includes('allocateDiscardable')
        );
        return {
            links: row?.querySelectorAll('a[data-tv-bundle-topic]').length || 0,
            separators: Array.from(row?.textContent || '').filter((char) => char === '│').length,
            text: row?.textContent,
        };
    })()`);
    if (tvcHelpTable.links !== 3 || tvcHelpTable.separators !== 3) {
        throw new Error(`TVCHELP table row is malformed: ${JSON.stringify(tvcHelpTable)}`);
    }

    await evaluate(`document.querySelector('[data-tv-dialog-open="mastermind"]').click()`);
    await pause();
    const mastermind = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Mastermind'
        );
        const body = dialog?.querySelector('.tv-dialog-body');
        const group = dialog?.querySelector('.tv-group');
        const board = dialog?.querySelector('[data-tv-mastermind-board]');
        const bodyRect = body?.getBoundingClientRect();
        const groupRect = group?.getBoundingClientRect();
        const boardRect = board?.getBoundingClientRect();
        const dialogRect = dialog?.getBoundingClientRect();
        const probe = document.createElement('span');
        probe.className = 'tv-static-text';
        probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre';
        probe.textContent = '0000000000';
        dialog?.appendChild(probe);
        const cellWidth = probe.getBoundingClientRect().width / 10;
        probe.remove();
        const controls = Array.from(group?.children || []);
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            rows: dialog?.querySelectorAll('.tv-mastermind-row').length || 0,
            colors: dialog?.querySelectorAll('[data-tv-mastermind-color]').length || 0,
            hall: dialog?.querySelector('.tv-game-hall-control')?.textContent || '',
            columns: dialogRect && cellWidth ? Math.round(dialogRect.width / cellWidth) : 0,
            boardInset: boardRect && groupRect ? boardRect.left - groupRect.left : 0,
            clipped: !bodyRect || !groupRect || group.scrollWidth > group.clientWidth
                || group.scrollHeight > group.clientHeight
                || controls.some((element) => {
                    const rect = element.getBoundingClientRect();
                    return rect.left < groupRect.left - 0.5 || rect.top < groupRect.top - 0.5
                        || rect.right > groupRect.right + 0.5 || rect.bottom > groupRect.bottom + 0.5;
                }),
        };
    })()`);
    if (!mastermind.open || mastermind.rows !== 10 || mastermind.colors !== 6
        || mastermind.hall !== '[H]' || mastermind.columns < 64
        || mastermind.boardInset <= 0 || mastermind.clipped) {
        throw new Error(`Mastermind dialog is incomplete: ${JSON.stringify(mastermind)}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`document.querySelector('[data-tv-dialog-open="tron"]').click()`);
    await pause();
    const tronOpen = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tron Light Cycles'
        );
        const group = dialog?.querySelector('.tv-group');
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            cells: dialog?.querySelectorAll('.tv-tron-cell').length || 0,
            heads: dialog?.querySelectorAll('.tv-tron-cell.is-head').length || 0,
            hall: dialog?.querySelector('.tv-game-hall-control')?.textContent || '',
            timer: Boolean(dialog?.querySelector('[data-tv-tron-status]')?.textContent.includes('Ticks:')),
            clipped: Boolean(group && (group.scrollWidth > group.clientWidth || group.scrollHeight > group.clientHeight)),
        };
    })()`);
    if (!tronOpen.open || tronOpen.cells !== 540 || tronOpen.heads !== 2
        || tronOpen.hall !== '[H]' || !tronOpen.timer || tronOpen.clipped) {
        throw new Error(`Tron dialog is incomplete: ${JSON.stringify(tronOpen)}`);
    }

    await evaluate(`document.querySelector('[data-tv-dialog-open="hanoi"]').click()`);
    await pause();
    const hanoiOpen = await evaluate(`(() => {
        const hanoi = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tower of Hanoi'
        );
        const tron = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tron Light Cycles'
        );
        const group = hanoi?.querySelector('.tv-group');
        return {
            open: Boolean(hanoi && !hanoi.closest('.tv-dialog-overlay').hidden),
            towers: hanoi?.querySelectorAll('.tv-hanoi-tower').length || 0,
            disks: hanoi?.querySelectorAll('.tv-hanoi-disk').length || 0,
            draggable: hanoi?.querySelectorAll('.tv-hanoi-disk[draggable="true"]').length || 0,
            focused: document.activeElement?.dataset.tvHanoiTower,
            emptyHistory: hanoi?.querySelector('[data-tv-hanoi-history]')?.textContent.includes('(empty)'),
            hall: hanoi?.querySelector('.tv-game-hall-control')?.textContent || '',
            tronPaused: tron?.querySelector('[data-tv-tron-status]')?.textContent.includes('Inactive window'),
            tronTicks: Number((tron?.querySelector('[data-tv-tron-status]')?.textContent.match(/Ticks: ([0-9]+)/) || [])[1] || 0),
            clipped: Boolean(group && (group.scrollWidth > group.clientWidth || group.scrollHeight > group.clientHeight)),
        };
    })()`);
    if (!hanoiOpen.open || hanoiOpen.towers !== 3 || hanoiOpen.disks !== 5
        || hanoiOpen.draggable !== 1 || hanoiOpen.focused !== '0' || !hanoiOpen.emptyHistory
        || hanoiOpen.hall !== '[H]' || !hanoiOpen.tronPaused || hanoiOpen.clipped) {
        throw new Error(`Tower of Hanoi dialog is incomplete: ${JSON.stringify(hanoiOpen)}`);
    }
    await key("F1", "F1");
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
            if (help?.querySelector('.tv-topic-heading')?.textContent.trim() === 'Tower of Hanoi') {
                resolve(true);
                return;
            }
            if (Date.now() >= deadline) { reject(new Error('Tower of Hanoi context help did not open')); return; }
            setTimeout(check, 25);
        };
        check();
    })`, true);
    const hanoiHelpClosePoint = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        const close = help?.querySelector('[data-tv-bundle-close]');
        const rect = close?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!hanoiHelpClosePoint) { throw new Error('Tower of Hanoi Help close control is missing'); }
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: hanoiHelpClosePoint.x, y: hanoiHelpClosePoint.y,
        button: 'left', clickCount: 1,
    });
    const hanoiHelpClosedOnPress = await evaluate(`(() => ({
        helpClosed: !document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]'),
        gameActive: Array.from(document.querySelectorAll('.tv-dialog-window')).some((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tower of Hanoi'
            && element.classList.contains('is-window-active')
        ),
    }))()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: hanoiHelpClosePoint.x, y: hanoiHelpClosePoint.y,
        button: 'left', clickCount: 1,
    });
    if (!hanoiHelpClosedOnPress.helpClosed || !hanoiHelpClosedOnPress.gameActive) {
        throw new Error(`Safari-style mouse press did not close Help: ${JSON.stringify(hanoiHelpClosedOnPress)}`);
    }
    await key("Enter", "Enter");
    await key("ArrowRight", "ArrowRight");
    await key("Enter", "Enter");
    await pause();
    const hanoiKeyboardMove = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tower of Hanoi'
        );
        return {
            history: dialog?.querySelector('[data-tv-hanoi-history]')?.textContent || '',
            status: dialog?.querySelector('[data-tv-hanoi-status]')?.textContent || '',
            focused: document.activeElement?.dataset.tvHanoiTower,
        };
    })()`);
    if (!hanoiKeyboardMove.history.includes('1→2 disk 1')
        || !hanoiKeyboardMove.status.includes('Moves: 1') || hanoiKeyboardMove.focused !== '1') {
        throw new Error(`Hanoi keyboard move failed: ${JSON.stringify(hanoiKeyboardMove)}`);
    }
    await key("u", "KeyU");
    await pause();
    const hanoiDragMove = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tower of Hanoi'
        );
        const disk = dialog?.querySelector('[data-tv-hanoi-tower="0"] .tv-hanoi-disk[draggable="true"]');
        const target = dialog?.querySelector('.tv-hanoi-tower[data-tv-hanoi-tower="2"]');
        const transfer = new DataTransfer();
        disk?.dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: transfer }));
        target?.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: transfer }));
        target?.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: transfer }));
        disk?.dispatchEvent(new DragEvent('dragend', { bubbles: true, dataTransfer: transfer }));
        return {
            history: dialog?.querySelector('[data-tv-hanoi-history]')?.textContent || '',
            status: dialog?.querySelector('[data-tv-hanoi-status]')?.textContent || '',
        };
    })()`);
    if (!hanoiDragMove.history.includes('1→3 disk 1') || !hanoiDragMove.status.includes('Moves: 1')) {
        throw new Error(`Hanoi drag move failed: ${JSON.stringify(hanoiDragMove)}`);
    }
    await key("Escape", "Escape", 0, true);
    await pause();
    const tronResumed = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tron Light Cycles'
        );
        const text = dialog?.querySelector('[data-tv-tron-status]')?.textContent || '';
        const ticks = Number((text.match(/Ticks: ([0-9]+)/) || [])[1] || 0);
        return { text, ticks, active: dialog?.classList.contains('is-window-active') };
    })()`);
    if (!tronResumed.active || tronResumed.text.includes('Inactive window')
        || tronResumed.ticks <= hanoiOpen.tronTicks) {
        throw new Error(`Tron did not resume after reactivation: ${JSON.stringify({ hanoiOpen, tronResumed })}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`document.querySelector('[data-tv-dialog-open="puzzle"]').click()`);
    await pause();
    const hallOpen = await evaluate(`(() => {
        const puzzle = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Puzzle'
        );
        const button = puzzle?.querySelector('.tv-game-hall-control');
        const bracketColor = getComputedStyle(button).color;
        const glyphColor = getComputedStyle(button?.querySelector('.tv-game-hall-glyph')).color;
        button?.click();
        const hall = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Puzzle Hall of Fame'
        );
        return {
            button: button?.textContent,
            bracketColor,
            glyphColor,
            open: Boolean(hall && !hall.closest('.tv-dialog-overlay').hidden),
            empty: hall?.querySelector('.tv-hall-empty')?.textContent.trim(),
        };
    })()`);
    if (hallOpen.button !== '[H]' || hallOpen.bracketColor !== 'rgb(255, 255, 255)'
        || hallOpen.glyphColor !== 'rgb(85, 255, 85)'
        || !hallOpen.open || hallOpen.empty !== 'No scores yet.') {
        throw new Error(`Hall of Fame control is incomplete: ${JSON.stringify(hallOpen)}`);
    }
    socket.close();
}

const timeout = setTimeout(() => {
    process.stderr.write("browser smoke test timed out\n");
    process.exit(1);
}, 35000);
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
                    [NODE, "-e", script, str(debugging_port), app_url],
                    capture_output=True,
                    text=True,
                    timeout=40,
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
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
