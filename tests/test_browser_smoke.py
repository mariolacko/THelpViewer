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


def _wait_for_search_index(url: str, timeout: float = 300.0) -> None:
    """Prepare the full-corpus fixture before the timed UI assertions."""
    deadline = time.monotonic() + timeout
    status = {}
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2.0) as response:
                status = json.load(response)
        except OSError:
            pass
        else:
            if status.get("state") == "ready" and status.get("available"):
                return
            if status.get("state") == "error":
                raise RuntimeError(f"search index fixture failed: {status}")
        time.sleep(0.25)
    raise TimeoutError(f"search index fixture did not become ready: {url}: {status}")


def _prepare_help_fixture(helps: Path) -> None:
    """Publish the real sources used below without changing installed packages."""
    from thelpviewer.server.converter.writers.bundle import export_bundle_tree

    sources = Path("var/sources")
    selected = [sources / name for name in (
        "Borland Sidekick 2/SK2.HLP", "Norton Guides/VISTA.NG",
        "Borland Turbo C 1.x current/TCHELP.TCH",
        "Borland Turbo C 1.0/TCHELP.TCH", "Microsoft MS-DOS 6.22/HELP.HLP",
        "Borland C++ 2.0 DOS current/TCHELP.TCH",
        "Borland C++ 3.x/TVCHELP.TCH", "Norton Guides/DEBUG.NG",
        "Borland C++ 3.0/TASM.TAH", "Borland Pascal 7.0 (DE)/TASM.TAH",
        "Borland Turbo Assembler/TASM.TAH", "Borland Turbo Assembler 2.01/TASM.TAH",
        "Borland Turbo Debugger/Profiler/Assembler/TASM.TAH",
    )]
    missing = [str(path) for path in selected if not path.is_file()]
    if missing:
        pytest.skip("Original browser HELP sources unavailable: " + ", ".join(missing))
    results = export_bundle_tree(sources, helps, source_paths=selected, layout="helps")
    assert len(results) == len(selected) and all(not result.error for result in results)


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_real_browser_menu_focus_and_dynamic_command_state():
    external_url = os.environ.get("THELP_BROWSER_BASE_URL", "").rstrip("/")
    server = None
    server_state_directory = None
    if external_url:
        app_url = external_url + "/"
    else:
        app_port = _free_port()
        app_url = f"http://127.0.0.1:{app_port}/"
        server_state_directory = tempfile.TemporaryDirectory(prefix="thelpviewer-server-state-")
        helps = Path(server_state_directory.name) / "helps"
        _prepare_help_fixture(helps)
        midi_sources_path = Path(server_state_directory.name) / "midi-sources.json"
        midi_sources_path.write_text('{"sources": []}', encoding="utf-8")
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
            env={
                **os.environ,
                "THELP_STATE_DIR": server_state_directory.name,
                "THELP_HELPS_DIR": str(helps),
                "THELP_STATISTICS_PATH": str(Path(server_state_directory.name) / "statistics.sqlite3"),
                "THELP_MIDI_SOURCES_PATH": str(midi_sources_path),
            },
        )
    try:
        _wait_for_url(app_url + "healthz")
        _wait_for_search_index(app_url + "api/search/status")
        with tempfile.TemporaryDirectory(prefix="thelpviewer-chrome-") as profile_dir:
            chrome = subprocess.Popen(
                [
                    CHROME,
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--autoplay-policy=no-user-gesture-required",
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
    const key = (value, code, modifiers = 0, useActiveElement = true) => evaluate(`(() => {
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
    const assertWindowOnDesktop = async (selector, label) => {
        const bounds = await evaluate(`document.fonts.ready.then(() =>
            new Promise(resolve => requestAnimationFrame(() => {
                const desktop = document.querySelector('.tv-desktop').getBoundingClientRect();
                const window = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();
                const status = document.querySelector('.tv-status-line').getBoundingClientRect();
                resolve({ window: window.toJSON(), desktop: desktop.toJSON(),
                    status: status.toJSON(), viewportHeight: innerHeight });
            })))`, true);
        const { window: windowBounds, desktop, status, viewportHeight } = bounds;
        if (windowBounds.top < desktop.top - 1 || windowBounds.bottom > desktop.bottom + 1
            || windowBounds.left < desktop.left - 1 || windowBounds.right > desktop.right + 1
            || status.bottom > viewportHeight + 1 || desktop.bottom > status.top + 1) {
            throw new Error(`${label} opened outside the desktop: ${JSON.stringify(bounds)}`);
        }
    };

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Page.addScriptToEvaluateOnNewDocument", { source: `
        window.__tvMenuItem = (command, name = '') =>
            Array.from(document.querySelectorAll('[data-tv-command="' + command + '"]')).find((element) =>
                !name || element._tvMenuItem?.name.replaceAll('~', '') === name
            ) || null;
    ` });
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
            const open = Array.from(document.querySelectorAll('[data-tv-command="file-open"]')).find(
                (element) => element._tvMenuItem?.name === '~O~pen...'
            );
            if (open) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('Open was not bound while catalogs loaded')); return; }
            setTimeout(check, 20);
        };
        check();
    })`, true);
    await evaluate(`window.__tvMenuItem = (command, name = '') =>
        Array.from(document.querySelectorAll('[data-tv-command="' + command + '"]')).find((element) =>
            !name || element._tvMenuItem?.name.replaceAll('~', '') === name
        ) || null`);
    const helpMenuLayout = await evaluate(`(() => {
        const system = document.querySelector('[data-tv-menu-root][data-tv-help-ctx="1100"]');
        const help = document.querySelector('[data-tv-menu-root][data-tv-help-ctx="1700"]');
        return {
            systemAbout: Array.from(system?.querySelectorAll('[data-tv-command="dialog-open"]') || [])
                .filter((element) => element.textContent.trim() === 'About').length,
            helpAbout: Array.from(help?.querySelectorAll('[data-tv-command="dialog-open"]') || [])
                .filter((element) => element.textContent.trim() === 'About').length,
            helpIndex: help?.querySelectorAll('[data-tv-command="context-help-index"]').length || 0,
        };
    })()`);
    if (helpMenuLayout.systemAbout !== 0 || helpMenuLayout.helpAbout !== 1 || helpMenuLayout.helpIndex !== 1) {
        throw new Error(`Help/About menu placement is broken: ${JSON.stringify(helpMenuLayout)}`);
    }
    const generatedContextChrome = await evaluate(`(() => {
        const TV = window.THelpViewerTV;
        const view = new TV.TVContextHelpWindow();
        const root = TV.TVView._fromHTML(view.draw());
        view.resolve(root);
        const result = {
            window: root.matches('.tv-window[data-tv-window]'),
            dialog: root.matches('.tv-dialog-window') || Boolean(root.querySelector('.tv-dialog-window')),
            close: root.querySelectorAll('[data-tv-command="window-close"]').length,
            zoom: root.querySelectorAll('[data-tv-command="window-zoom"]').length,
            vertical: root.querySelectorAll(':scope > .tv-shell > .tv-client-row > .tv-scrollbar-y').length,
            horizontal: root.querySelectorAll(':scope > .tv-shell > .tv-client-row > .tv-bottom-bar .tv-scrollbar-x').length,
            grow: root.querySelectorAll('[data-tv-resize-handle]').length,
            internalButtons: root.querySelectorAll('.tv-help-viewer .tv-dialog-button').length,
        };
        view.destroy();
        return result;
    })()`);
    if (!generatedContextChrome.window || generatedContextChrome.dialog
        || generatedContextChrome.close !== 1 || generatedContextChrome.zoom !== 1
        || generatedContextChrome.vertical !== 1 || generatedContextChrome.horizontal !== 1
        || generatedContextChrome.grow !== 1 || generatedContextChrome.internalButtons !== 0) {
        throw new Error(`Generated UHF Help does not use standard TVWindow chrome: ${JSON.stringify(generatedContextChrome)}`);
    }
    const hostCloseEvent = await evaluate(`(() => {
        const TV = window.THelpViewerTV;
        const root = document.createElement('main');
        root.setAttribute('data-tv-window', '');
        root.innerHTML = '<a class="tv-close-control" href="index.html">Close</a>';
        const view = new TV.TVWindow(new TV.TVRect(), 'Generated page').bindRoot(root);
        let closes = 0;
        view.closeAction = () => { closes += 1; };
        root.querySelector('a').click();
        view.bindRoot(null);
        return closes;
    })()`);
    if (hostCloseEvent !== 1) {
        throw new Error(`Generated page close link bypassed TVWindow: ${hostCloseEvent}`);
    }
    const titleDoubleClick = await evaluate(`(() => {
        const TV = window.THelpViewerTV;
        const view = new TV.TVWindow(new TV.TVRect(0, 0, 40, 12), 'Double click');
        const root = TV.TVView._fromHTML(view.draw());
        view.bindRoot(root);
        let zooms = 0;
        view.zoomAction = () => { zooms += 1; };
        root.querySelector('.tv-window-caption').dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
        root.querySelector('.tv-zoom-control').dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
        view.bindRoot(null);
        const plain = document.createElement('main');
        plain.setAttribute('data-tv-window', '');
        plain.innerHTML = '<span>Client content</span>';
        view.bindRoot(plain);
        plain.querySelector('span').dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
        view.bindRoot(null);
        return zooms;
    })()`);
    if (titleDoubleClick !== 1) {
        throw new Error(`Double-clicking the window title did not dispatch one zoom command: ${titleDoubleClick}`);
    }
    const helpMenuPoint = await evaluate(`(() => {
        const open = __tvMenuItem('file-open', 'Open...');
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
        const open = __tvMenuItem('file-open', 'Open...');
        const rect = open.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: openPoint.x, y: openPoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: openPoint.x, y: openPoint.y, button: 'left', clickCount: 1,
    });
    await pause();
    const loadingOpen = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        const history = dialog?.querySelector('[data-tv-file-open-history-popup]');
            return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            status: dialog?.querySelectorAll('[data-tv-file-open-cancel] ~ .tv-static-text')[1]?.textContent.trim() || '',
            historyHidden: Boolean(history?.hidden && getComputedStyle(history).display === 'none'),
            statusHint: document.querySelector('[data-tv-status-hint]')?.textContent.trim() || '',
            inputFocused: document.activeElement === dialog?.querySelector('.tv-input-line'),
        };
    })()`);
    if (!loadingOpen.open || loadingOpen.status !== 'Loading HELP/DOCS...' || !loadingOpen.historyHidden
        || loadingOpen.statusHint !== 'Choose a HELP or Docs file from the two-column list.'
        || !loadingOpen.inputFocused) {
        throw new Error(`Open did not show its loading state immediately: ${JSON.stringify(loadingOpen)}`);
    }
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
                element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
            );
            const entries = dialog?.querySelectorAll('[data-tv-file-open-files] [data-tv-list-index]').length || 0;
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
            && popup._tvView?.getState(window.THelpViewerTV.sfVisible)
            && button.getAttribute('aria-expanded') === 'true');
        button?.click();
        const closed = Boolean(popup?.hidden
            && !popup?._tvView?.getState(window.THelpViewerTV.sfVisible)
            && button?.getAttribute('aria-expanded') === 'false');
        return { opened, closed, entries: popup?.querySelectorAll('[data-tv-list-index]').length || 0 };
    })()`);
    if (!emptyFileHistory.opened || !emptyFileHistory.closed || emptyFileHistory.entries !== 0) {
        throw new Error(`Empty File Open history did not toggle: ${JSON.stringify(emptyFileHistory)}`);
    }
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const toggle = Array.from(document.querySelectorAll('[data-tv-submenu-toggle]'))
                .find((element) => element._tvMenuItem?.name === 'Borland Turbo Assembler');
            if (toggle) {
                const entries = toggle._tvMenuItem.subMenu.entries();
                if (entries.map((entry) => entry.name).join('|') !== '2.0|2.01|3.0|3.1|3.2 (DE)'
                    || entries.some((entry) => entry.subMenu || entry.command !== 'bundle-open'
                        || !entry.getUrl().includes('file='))) {
                    reject(new Error('Assembler single-file editions are nested/missing/unsorted')); return;
                }
                resolve(); return;
            }
            if (Date.now() >= deadline) { reject(new Error('Assembler product menu missing')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
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
            standardClose: Boolean(help?.querySelector('[data-tv-command="window-close"]')),
            standardZoom: Boolean(help?.querySelector('[data-tv-command="window-zoom"]')),
            horizontalScrollbar: Boolean(help?.querySelector('.tv-bottom-bar .tv-scrollbar-x')),
            growHandle: Boolean(help?.querySelector('[data-tv-resize-handle]')),
            inlineNavigation: Boolean(help?.querySelector('.tv-context-help-nav')),
            statusBack: Boolean(document.querySelector('[data-tv-status-line] [data-tv-bundle-back]')),
            statusIndex: Boolean(document.querySelector('[data-tv-status-line] [data-tv-bundle-index]')),
            statusContents: Boolean(document.querySelector('[data-tv-status-line] [data-tv-bundle-help-contents]')),
            statusHint: document.querySelector('[data-tv-status-hint]')?.textContent.trim() || '',
        };
    })()`);
    if (!fileOpenHelp.helpOpen || fileOpenHelp.topic !== 'Open a File' || fileOpenHelp.context !== '2010'
        || !fileOpenHelp.standardWindow || fileOpenHelp.links < 2 || !fileOpenHelp.standardScrollbar
        || !fileOpenHelp.standardClose || !fileOpenHelp.standardZoom
        || !fileOpenHelp.horizontalScrollbar || !fileOpenHelp.growHandle
        || fileOpenHelp.inlineNavigation || !fileOpenHelp.statusBack || !fileOpenHelp.statusIndex
        || !fileOpenHelp.statusContents
        || fileOpenHelp.statusHint !== 'Links open topics or external companion HELP files.') {
        throw new Error(`File Open context help is broken: ${JSON.stringify(fileOpenHelp)}`);
    }
    const topContentsMenu = await evaluate(`(() => {
        const root = Array.from(document.querySelectorAll('[data-tv-menu-root]')).find((candidate) => {
            const item = candidate.querySelector(':scope > [data-tv-menu-toggle]')?._tvMenuItem;
            return item && ['~M~enu', '~C~ontents'].includes(item.name);
        });
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
            view: help?._tvWindowView?.currentView,
            outlines: help?.querySelectorAll('[data-tv-contents-outline]').length || 0,
            rows: help?.querySelectorAll('[data-tv-contents-outline] [data-tv-list-index]').length || 0,
            verticalScrollbars: help?.querySelectorAll('.tv-scrollbar-y').length || 0,
            ownedOutline: help?._tvWindowView?.outline?.root === help?.querySelector('[data-tv-contents-outline]'),
            ownedScrollbars: help?._tvWindowView?.scrollbars?.length || 0,
            staleDomOwnership: Boolean(help && ('_tvOutline' in help || '_tvScrollbars' in help)),
        };
    })()`);
    if (structuralContents.view !== 'contents' || structuralContents.outlines !== 1
        || structuralContents.rows < 10 || structuralContents.verticalScrollbars !== 1
        || !structuralContents.ownedOutline || structuralContents.ownedScrollbars !== 1
        || structuralContents.staleDomOwnership) {
        throw new Error(`Structural Contents uses the wrong scrollbar: ${JSON.stringify(structuralContents)}`);
    }
    await evaluate(`document.querySelector(
        '[data-tv-bundle-window="../assets/tv-context-help.json"] [data-tv-contents-outline] a[data-tv-uhf-link]'
    ).click()`);
    await pause();
    const outlineNavigation = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return { view: help?._tvWindowView?.currentView, topic: help?._tvWindowView?.currentTopic };
    })()`);
    if (outlineNavigation.view !== 'topic' || !outlineNavigation.topic) {
        throw new Error(`Contents list link did not navigate: ${JSON.stringify(outlineNavigation)}`);
    }
    await key("f", "KeyF", 2);
    await pause();
    const helpFindOwner = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return {
            editor: help?._tvWindowView?.findEditor instanceof window.THelpViewerTV.TVEditor,
            staleDomOwnership: Boolean(help && ('_tvFindEditor' in help)),
            dialogOpen: Boolean(document.querySelector('.tv-find-window')
                && !document.querySelector('.tv-find-window').closest('.tv-dialog-overlay').hidden),
        };
    })()`);
    if (!helpFindOwner.editor || helpFindOwner.staleDomOwnership || !helpFindOwner.dialogOpen) {
        throw new Error(`HELP Find editor is not owned by its window: ${JSON.stringify(helpFindOwner)}`);
    }
    await key("Escape", "Escape", 0, true);
    await evaluate(`document.querySelector('[data-tv-bundle-back]').click()`);
    const outlineKeyboardTarget = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        const item = help?.querySelector('[data-tv-contents-outline] [data-tv-list-index] a[data-tv-uhf-link]')
            ?.closest('[data-tv-list-index]');
        if (!item) { return false; }
        item.focus();
        item.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        return true;
    })()`);
    await pause();
    const outlineKeyboardView = await evaluate(`document.querySelector(
        '[data-tv-bundle-window="../assets/tv-context-help.json"]'
    )?._tvWindowView?.currentView`);
    if (!outlineKeyboardTarget || outlineKeyboardView !== 'topic') {
        throw new Error(`Contents keyboard activation did not open its target: ${outlineKeyboardView}`);
    }
    await evaluate(`document.querySelector('[data-tv-bundle-back]').click()`);
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
    const helpReturned = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return {
            heading: help?.querySelector('.tv-topic-heading')?.textContent.trim(),
            viewerCount: help?.querySelectorAll('[data-tv-help-viewer]').length || 0,
            viewerText: help?.querySelector('[data-tv-help-viewer]')?.textContent.slice(0, 100) || '',
            managerView: help?._tvWindowView?.currentView,
            managerTopic: help?._tvWindowView?.currentTopic,
        };
    })()`);
    if (helpReturned.heading !== 'Open a File') {
        throw new Error(`Context Help Back did not restore its topic: ${JSON.stringify(helpReturned)}`);
    }
    await evaluate(`document.querySelector('[data-tv-command="context-help-index"]').click()`);
    await pause();
    const contextHelpIndex = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return {
            view: help?._tvWindowView?.currentView,
            heading: help?.querySelector('.tv-index-heading')?.textContent.trim(),
            entries: help?.querySelectorAll('.tv-index-entry [data-tv-bundle-topic]').length || 0,
        };
    })()`);
    if (contextHelpIndex.view !== 'index' || contextHelpIndex.heading !== 'Index'
        || contextHelpIndex.entries < 20) {
        throw new Error(`Help > Index did not open the UHF index: ${JSON.stringify(contextHelpIndex)}`);
    }
    await evaluate(`document.querySelector(
        '[data-tv-bundle-window="../assets/tv-context-help.json"] .tv-index-entry [data-tv-bundle-topic]'
    ).click()`);
    await pause();
    const indexNavigation = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return { view: help?._tvWindowView?.currentView, topic: help?._tvWindowView?.currentTopic };
    })()`);
    if (indexNavigation.view !== 'topic' || !indexNavigation.topic) {
        throw new Error(`Index link did not navigate: ${JSON.stringify(indexNavigation)}`);
    }
    await evaluate(`document.querySelector('[data-tv-bundle-close-all]').click()`);
    const contextHelpClosed = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
            const fileOpen = document.querySelector('.tv-file-open-window .tv-input-line')?.closest('.tv-dialog-overlay');
        return {
            helpClosed: !help,
            fileOpenExists: Boolean(fileOpen),
            fileOpenVisible: Boolean(fileOpen && !fileOpen.hidden),
            activeWindows: Array.from(document.querySelectorAll('.is-window-active')).map((item) =>
                item.querySelector?.('.tv-dialog-title-text, .tv-window-caption')?.textContent || item.className
            ),
        };
    })()`);
    if (!contextHelpClosed.helpClosed || !contextHelpClosed.fileOpenVisible) {
        throw new Error(`Context Help did not return to File Open: ${JSON.stringify(contextHelpClosed)}`);
    }
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
            const menu = __tvMenuItem('window-cmd', 'Close');
            const welcome = Array.from(document.querySelectorAll('.tv-dialog-title-text'))
                .some((element) => element.textContent === 'Welcome');
            if (menu && welcome) { resolve(true); return; }
            if (Date.now() >= deadline) { reject(new Error('application did not initialize')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);

    await key("Escape", "Escape", 0, true);
    const systemMenuPoint = await evaluate(`(() => {
        const toggle = document.querySelector('[data-tv-menu-root][data-tv-help-ctx="1100"] > [data-tv-menu-toggle]');
        const rect = toggle.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mouseMoved', x: systemMenuPoint.x, y: systemMenuPoint.y,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: systemMenuPoint.x, y: systemMenuPoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: systemMenuPoint.x, y: systemMenuPoint.y, button: 'left', clickCount: 1,
    });
    const nestedPoint = await evaluate(`(() => {
        const toggle = Array.from(document.querySelectorAll('[data-tv-submenu-toggle]'))
            .find((element) => element.textContent.includes('Screen saver'));
        const rect = toggle.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mouseMoved', x: nestedPoint.x, y: nestedPoint.y,
    });
    const hoveredSubmenu = await evaluate(`(() => {
        const toggle = Array.from(document.querySelectorAll('[data-tv-submenu-toggle]'))
            .find((element) => element.textContent.includes('Screen saver'));
        const popup = toggle.closest('[data-tv-submenu-root]').querySelector('[data-tv-submenu-popup]');
        return { hidden: popup.hidden, expanded: toggle.getAttribute('aria-expanded') };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: nestedPoint.x, y: nestedPoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: nestedPoint.x, y: nestedPoint.y, button: 'left', clickCount: 1,
    });
    await pause();
    const nestedState = await evaluate(`(() => {
        const toggle = Array.from(document.querySelectorAll('[data-tv-submenu-toggle]'))
            .find((element) => element.textContent.includes('Screen saver'));
        const popup = toggle.closest('[data-tv-submenu-root]').querySelector('[data-tv-submenu-popup]');
        return { hidden: popup.hidden, expanded: toggle.getAttribute('aria-expanded') };
    })()`);
    if (hoveredSubmenu.hidden || hoveredSubmenu.expanded !== 'true'
        || nestedState.hidden || nestedState.expanded !== 'true') {
        throw new Error(`mouse activation closed the submenu: ${JSON.stringify({ hoveredSubmenu, nestedState })}`);
    }
    const projectorState = await evaluate(`(() => {
        const item = __tvMenuItem('saver-start', 'Projector');
        if (!item) { return { menuItem: false }; }
        item.click();
        const saver = window.THelpViewerTV.TVScreenSaver.active;
        const surface = saver?.surface;
        const context = surface?.getContext('2d');
        return {
            menuItem: true,
            active: saver instanceof window.THelpViewerTV.TVScreenSaverProjector,
            focused: document.activeElement === saver?.overlay,
            holeAlpha: context?.getImageData(
                saver.centerX * saver.cellWidth, saver.centerY * saver.cellHeight, 1, 1,
            ).data[3],
            darkAlpha: context?.getImageData(0, 0, 1, 1).data[3],
        };
    })()`);
    if (!projectorState.menuItem || !projectorState.active || !projectorState.focused
        || projectorState.holeAlpha !== 0 || projectorState.darkAlpha !== 255) {
        throw new Error(`Projector menu/drawing failed: ${JSON.stringify(projectorState)}`);
    }
    await key('Escape', 'Escape', 0, true);
    const projectorStopped = await evaluate(`(() => ({
        active: window.THelpViewerTV.TVScreenSaver.active,
        hidden: document.querySelector('.tv-saver-overlay')?.hidden,
    }))()`);
    if (projectorStopped.active || !projectorStopped.hidden) {
        throw new Error(`Projector did not stop on keyboard input: ${JSON.stringify(projectorStopped)}`);
    }
    await evaluate(`document.body.click()`);
    const calculatorView = await evaluate(`(() => {
        __tvMenuItem('dialog-open', 'Calculator')?.click();
        const display = document.querySelector('.tv-calc-body .tv-dialog-client > .tv-group > .tv-static-text:first-child');
        const main = display?.closest('.tv-group');
        const buttons = Array.from(main?.querySelectorAll('.tv-calc-button') || []);
        const mainRect = main?.getBoundingClientRect();
        const displayRect = display?.getBoundingClientRect();
        const firstButtonRect = buttons[0]?.getBoundingClientRect();
        return {
            open: Boolean(display && !display.closest('.tv-dialog-overlay')?.hidden),
            foreground: display ? getComputedStyle(display).color : '',
            buttons: buttons.length,
            keypadRow: Boolean(mainRect && displayRect && firstButtonRect
                && Math.abs((firstButtonRect.top - mainRect.top) - 3 * displayRect.height) < 1),
            clipped: Boolean(main && (main.scrollWidth > main.clientWidth || main.scrollHeight > main.clientHeight
                || buttons.some((button) => {
                    const rect = button.getBoundingClientRect();
                    return rect.left < mainRect.left - 0.5 || rect.top < mainRect.top - 0.5
                        || rect.right > mainRect.right + 0.5 || rect.bottom > mainRect.bottom + 0.5;
                }))),
            hint: document.querySelector('[data-tv-status-hint]')?.textContent.trim() || '',
        };
    })()`);
    if (!calculatorView.open || calculatorView.foreground !== 'rgb(255, 255, 255)'
        || calculatorView.buttons !== 20 || !calculatorView.keypadRow || calculatorView.clipped
        || calculatorView.hint !== 'Use number and operation buttons or the keyboard.') {
        throw new Error(`Calculator display/status palette is broken: ${JSON.stringify(calculatorView)}`);
    }
    await evaluate(`document.querySelector('.tv-calc-window [data-tv-command="dialog-close"]').click()`);
    await evaluate(`__tvMenuItem('dialog-open', 'Ascii Table')?.click()`);
    await pause();
    const asciiGeometry = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-ascii-window');
        const body = dialog?.querySelector('.tv-ascii-body');
        const chart = dialog?.querySelector('[data-tv-ascii-chart]');
        const report = body?.querySelector(':scope > .tv-static-text');
        const separator = body?.querySelector('.tv-border-separator');
        const separatorCorners = Array.from(body?.querySelectorAll(':scope > .tv-border-corner') || []);
        const bodyRect = body?.getBoundingClientRect();
        const chartRect = chart?.getBoundingClientRect();
        const reportRect = report?.getBoundingClientRect();
        const separatorRect = separator?.getBoundingClientRect();
        const cellWidth = chartRect ? chartRect.width / 32 : 0;
        const cellHeight = chartRect ? chartRect.height / 8 : 0;
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay')?.hidden),
            chart: chartRect && cellWidth && cellHeight
                ? [Math.round(chartRect.width / cellWidth), Math.round(chartRect.height / cellHeight)]
                : [],
            reportRow: bodyRect && reportRect && cellHeight
                ? Math.round((reportRect.top - bodyRect.top) / cellHeight)
                : -1,
            separator: Boolean(separatorRect && chartRect && reportRect
                && Math.abs(separatorRect.top - chartRect.bottom) < 1
                && Math.abs(separatorRect.bottom - reportRect.top) < 1),
            separatorCorners: separatorCorners.map((corner) => corner.textContent).join(''),
            separatorColors: [separator, ...separatorCorners]
                .filter(Boolean)
                .map((element) => getComputedStyle(element).color),
            clipped: Boolean(body && (body.scrollWidth > body.clientWidth || body.scrollHeight > body.clientHeight)),
        };
    })()`);
    if (!asciiGeometry.open || asciiGeometry.chart.join() !== '32,8'
        || asciiGeometry.reportRow !== 9 || !asciiGeometry.separator
        || asciiGeometry.separatorCorners !== '╟╢'
        || asciiGeometry.separatorColors.some((color) => color !== 'rgb(255, 255, 255)')
        || asciiGeometry.clipped) {
        throw new Error(`ASCII Chart TVRect geometry is broken: ${JSON.stringify(asciiGeometry)}`);
    }
    await key("Escape", "Escape", 0, true);
    const initialFindState = await evaluate(`(() => ({
        findDisabled: __tvMenuItem('find', 'Find')?.disabled,
        againDisabled: __tvMenuItem('find-again', 'Find Again')?.disabled,
    }))()`);
    if (initialFindState.findDisabled || !initialFindState.againDisabled) {
        throw new Error(`Global Find should be available while local Find Again remains disabled: ${JSON.stringify(initialFindState)}`);
    }
    await evaluate(`__tvMenuItem('find', 'Find').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const scope = document.querySelector('.tv-find-window .tv-radio-item input[value="global"]');
            if (scope && !scope.disabled) { resolve(true); return; }
            if (Date.now() >= deadline) {
                fetch('/api/search/status').then((response) => response.json()).then((status) =>
                    reject(new Error('global Find availability was not checked: ' + JSON.stringify({ status,
                        dialog: (() => { const view = document.querySelector('.tv-find-window')?.closest('.tv-dialog-overlay')?._tvView;
                            return { available: view?.globalAvailable, checked: view?.availabilityChecked,
                                handler: Boolean(view?.globalFindHandler), serial: view?.availabilitySerial,
                                status: view?.statusView?.text, html: scope?.outerHTML }; })(),
                    }))));
                return;
            }
            setTimeout(check, 25);
        };
        check();
    })`, true);
    const globalFindRoute = await evaluate(`(() => {
        const find = document.querySelector('.tv-find-window');
        const scope = find?.querySelector('.tv-radio-item input[value="global"]');
        scope.checked = true;
        scope.dispatchEvent(new Event('change', { bubbles: true }));
        find.querySelector('.tv-input-line').value = 'global example';
        find.querySelector('[data-tv-command="find-confirm"]').click();
        const search = document.querySelector('.tv-search-window');
        return {
            findClosed: find.closest('.tv-dialog-overlay').hidden,
            searchOpen: Boolean(search && !search.closest('.tv-dialog-overlay').hidden),
            query: search?.querySelector('.tv-input-line')?.value,
            global: search?.querySelector('.tv-radio-item input[value="global"]')?.checked,
        };
    })()`);
    if (!globalFindRoute.findClosed || !globalFindRoute.searchOpen
        || globalFindRoute.query !== 'global example' || !globalFindRoute.global) {
        throw new Error(`Find did not route to global Search Topics: ${JSON.stringify(globalFindRoute)}`);
    }
    await key('Escape', 'Escape', 0, true);
    await evaluate(`(() => {
        const doc = document.querySelector('[data-tv-command="doc-open"]');
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
        findDisabled: __tvMenuItem('find', 'Find')?.disabled,
        againDisabled: __tvMenuItem('find-again', 'Find Again')?.disabled,
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
        const ruler = document.createElement('span');
        ruler.textContent = '0'.repeat(80);
        ruler.style.cssText = 'position:absolute;visibility:hidden;white-space:pre';
        content.append(ruler);
        const requiredWidth = ruler.getBoundingClientRect().width;
        ruler.remove();
        const contentStyle = getComputedStyle(content);
        const textWidth = content.clientWidth - parseFloat(contentStyle.paddingLeft) - parseFloat(contentStyle.paddingRight);
        const code = document.createElement('pre');
        code.textContent = '0'.repeat(80);
        content.append(code);
        const codeStyle = getComputedStyle(code);
        const codeWidth = code.clientWidth - parseFloat(codeStyle.paddingLeft) - parseFloat(codeStyle.paddingRight);
        code.remove();
        return {
            viewport: pair(viewport),
            content: pair(content),
            textColumnsFit: textWidth >= requiredWidth - 1,
            codeColumnsFit: codeWidth >= requiredWidth - 1,
            wrapMode: [contentStyle.overflowWrap, contentStyle.wordBreak],
            statusHint: document.querySelector('[data-tv-status-hint]')?.textContent.trim() || '',
            caption: doc.querySelector('.tv-window-caption')?.textContent.trim() || '',
        };
    })()`);
    const editorColors = ['rgb(0, 0, 170)', 'rgb(255, 255, 85)'];
    if (docColors.viewport.join() !== editorColors.join() || docColors.content.join() !== editorColors.join()) {
        throw new Error(`Documentation does not use the Editor palette: ${JSON.stringify(docColors)}`);
    }
    if (!docColors.textColumnsFit || !docColors.codeColumnsFit
        || docColors.wrapMode.join() !== 'normal,normal') {
        throw new Error(`Documentation does not fit 80 unbroken text columns: ${JSON.stringify(docColors)}`);
    }
    if (!docColors.caption
        || docColors.statusHint !== 'Markdown is displayed with the read-only Editor palette.') {
        throw new Error(`Status line did not show contextual mini help: ${JSON.stringify(docColors)}`);
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
        const editor = doc?._tvWindowView?.editor;
        const root = editor?.root;
        const word = (root?.textContent.match(/[A-Za-z]{6,}/) || [])[0] || '';
        return {
            attached: editor instanceof window.THelpViewerTV.TVEditor,
            staleDomOwnership: Boolean(doc && ('_tvEditor' in doc || '_tvFindEditor' in doc)),
            readOnly: root?.getAttribute('aria-readonly'),
            found: word ? editor.find(word, { fromStart: true }) : false,
            indicator: doc?.querySelector('.tv-editor-indicator')?.textContent,
        };
    })()`);
    if (!docEditor.attached || docEditor.staleDomOwnership || docEditor.readOnly !== 'true'
        || !docEditor.found || !docEditor.indicator.startsWith('RO')) {
        throw new Error(`Documentation is not using the read-only editor: ${JSON.stringify(docEditor)}`);
    }

    const findNeedle = await evaluate(`(() => {
        const root = document.querySelector('.tv-doc-window')?._tvWindowView?.editor?.root;
        const value = (root?.textContent.match(/[A-Za-z]{7,}/) || [])[0] || '';
        window.__tvFindNeedle = value;
        return value;
    })()`);
    if (!findNeedle) { throw new Error('Documentation has no searchable word'); }
    await key("f", "KeyF", 2);
    await pause();
    const findOpen = await evaluate(`(() => {
        const input = document.querySelector('.tv-find-window .tv-input-line');
        const history = document.querySelector('[data-tv-find-history-popup]');
        const dialog = document.querySelector('.tv-find-window');
        const find = dialog?.querySelector('[data-tv-command="find-confirm"]');
        const cancel = dialog?.querySelector('[data-tv-command="find-cancel"]');
        if (!input || input.closest('.tv-dialog-overlay')?.hidden) { return { open: false }; }
        const historyHidden = Boolean(history?.hidden && getComputedStyle(history).display === 'none');
        const inputFocused = document.activeElement === input;
        input.value = window.__tvFindNeedle;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
        return { open: true, historyHidden, inputFocused,
            rows: Math.round(dialog.getBoundingClientRect().height / input.getBoundingClientRect().height),
            cancelGap: Math.round((cancel.getBoundingClientRect().top - find.getBoundingClientRect().top)
                / input.getBoundingClientRect().height),
            scopes: dialog.querySelectorAll('.tv-radio-item input').length,
            localSelected: dialog.querySelector('.tv-radio-item input[value="local"]')?.checked,
            globalEnabled: !dialog.querySelector('.tv-radio-item input[value="global"]')?.disabled,
        };
    })()`);
    if (!findOpen.open || !findOpen.historyHidden || !findOpen.inputFocused
        || findOpen.rows !== 12 || findOpen.cancelGap !== 2
        || findOpen.scopes !== 2 || !findOpen.localSelected || !findOpen.globalEnabled) {
        throw new Error(`Ctrl-F opened Find incorrectly: ${JSON.stringify(findOpen)}`);
    }
    await key("Enter", "Enter", 0, true);
    await pause();
    const findResult = await evaluate(`(() => ({
        closed: document.querySelector('.tv-find-window .tv-input-line')?.closest('.tv-dialog-overlay')?.hidden,
        selection: window.getSelection()?.toString() || '',
        history: JSON.parse(localStorage.getItem('thelp:find-history') || '[]'),
    }))()`);
    if (!findResult.closed || findResult.selection.toLocaleLowerCase() !== findNeedle.toLocaleLowerCase()
        || !findResult.history.includes(findNeedle)) {
        throw new Error(`Find did not search the active editor: ${JSON.stringify(findResult)}`);
    }
    const searchedFindState = await evaluate(`(() => ({
        findDisabled: __tvMenuItem('find', 'Find')?.disabled,
        againDisabled: __tvMenuItem('find-again', 'Find Again')?.disabled,
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
        const dialog = document.querySelector('.tv-find-window');
        const body = dialog?.querySelector('.tv-find-body');
        const input = dialog?.querySelector('.tv-input-line');
        const initiallyHidden = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none');
        button?.click();
        const opened = Boolean(!popup?.hidden && getComputedStyle(popup).display !== 'none'
            && button?.getAttribute('aria-expanded') === 'true');
        const viewer = popup?.querySelector('.tv-vlist-viewer');
        const scrollbar = viewer?.querySelector('.tv-scrollbar-y');
        const popupRect = popup?.getBoundingClientRect();
        const viewerRect = viewer?.getBoundingClientRect();
        const scrollbarRect = scrollbar?.getBoundingClientRect();
        const bodyRect = body?.getBoundingClientRect();
        const inputRect = input?.getBoundingClientRect();
        const cellWidth = inputRect ? inputRect.width / 30 : 0;
        const cellHeight = inputRect?.height || 0;
        const viewerInset = popupRect && viewerRect && cellWidth && cellHeight
            ? [
                Math.round((viewerRect.left - popupRect.left) / cellWidth),
                Math.round((viewerRect.top - popupRect.top) / cellHeight),
            ]
            : [];
        const scrollbarAligned = Boolean(viewerRect && scrollbarRect
            && Math.abs(scrollbarRect.top - viewerRect.top) < 1
            && Math.abs(scrollbarRect.right - popupRect.right) < 1
            && Math.abs(scrollbarRect.bottom - viewerRect.bottom) < 1);
        const shadowClearance = bodyRect && popupRect && cellHeight
            ? (bodyRect.bottom - popupRect.bottom) / cellHeight
            : -1;
        button?.click();
        const closed = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none'
            && button?.getAttribute('aria-expanded') === 'false');
        return {
            enabled: !button?.disabled,
            initiallyHidden,
            opened,
            closed,
            viewerInset,
            scrollbarAligned,
            scrollbarRightGap: scrollbarRect && popupRect ? popupRect.right - scrollbarRect.right : null,
            shadowClearance,
        };
    })()`);
    if (!findHistoryToggle.enabled || !findHistoryToggle.initiallyHidden
        || !findHistoryToggle.opened || !findHistoryToggle.closed
        || findHistoryToggle.viewerInset.join() !== '1,1'
        || !findHistoryToggle.scrollbarAligned || findHistoryToggle.shadowClearance < 0.5) {
        throw new Error(`Find history toggle is broken: ${JSON.stringify(findHistoryToggle)}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`document.querySelector('[data-tv-status-line] [data-tv-command="context-help"]')?.click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            if (document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]')) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('HELP window did not open for local Search Topics')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await key("F3", "F3", 0, true);
    await pause();
    const searchFrame = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-search-window');
        const body = dialog?.querySelector('.tv-search-body');
        const client = body?.querySelector(':scope > .tv-dialog-client');
        const sides = Array.from(body?.querySelectorAll(':scope > .tv-border-side') || []);
        const rect = (element) => {
            const value = element?.getBoundingClientRect();
            return value ? { left: value.left, right: value.right, top: value.top, bottom: value.bottom } : null;
        };
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            body: rect(body),
            client: rect(client),
            sides: sides.map(rect),
        };
    })()`);
    if (
        !searchFrame.open || searchFrame.sides.length !== 2
        || Math.abs(searchFrame.sides[0].left - searchFrame.body.left) > 1
        || Math.abs(searchFrame.sides[1].right - searchFrame.body.right) > 1
        || Math.abs(searchFrame.client.left - searchFrame.sides[0].right) > 1
        || Math.abs(searchFrame.client.right - searchFrame.sides[1].left) > 1
    ) {
        throw new Error(`Search Topic frame is misaligned: ${JSON.stringify(searchFrame)}`);
    }
    const findMnemonic = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
        dialog.resultsBox.root?.focus();
        const event = new KeyboardEvent('keydown', {
            key: 'f', code: 'KeyF', altKey: true, bubbles: true, cancelable: true,
        });
        dialog.resultsBox.root?.dispatchEvent(event);
        return { focused: document.activeElement === dialog.input.root, handled: event.defaultPrevented,
            label: dialog.input.root?.labels?.[0]?.textContent };
    })()`);
    if (!findMnemonic.focused || !findMnemonic.handled || findMnemonic.label !== 'Find:') {
        throw new Error(`Find label mnemonic did not focus its input: ${JSON.stringify(findMnemonic)}`);
    }
    const searchPalette = await evaluate(`(() => {
        const input = document.querySelector('.tv-search-window .tv-input-line');
        input.value = 'help';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const viewport = document.querySelector('[data-tv-search-results] > .tv-vlist-viewport');
        const selected = viewport?.querySelector('.tv-search-result.is-selected');
        const colors = (element) => {
            const style = element ? getComputedStyle(element) : null;
            return style ? [style.backgroundColor, style.color] : [];
        };
        return {
            entries: viewport?.querySelectorAll('.tv-search-result').length || 0,
            scopes: document.querySelectorAll('.tv-search-window .tv-radio-item input').length,
            localSelected: document.querySelector('.tv-search-window .tv-radio-item input[value="local"]')?.checked,
            globalEnabled: !document.querySelector('.tv-search-window .tv-radio-item input[value="global"]')?.disabled,
            sourceLine: selected?.querySelector('.tv-search-result-meta')?.textContent || '',
            sourceName: document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView
                .sourceView.root?.textContent || '',
            radioMark: getComputedStyle(document.querySelector('.tv-search-window .tv-radio-item input:checked + .tv-radio-mark'), '::before').content,
            viewport: colors(viewport),
            selected: colors(selected),
        };
    })()`);
    if (searchPalette.entries < 1 || searchPalette.scopes !== 2
        || !searchPalette.localSelected || !searchPalette.globalEnabled || !searchPalette.sourceLine
        || !searchPalette.sourceName.startsWith('Source: ') || !searchPalette.radioMark.includes('•')
        || searchPalette.viewport.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || searchPalette.selected.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()) {
        throw new Error(`Search Topics does not use the shared list palette: ${JSON.stringify(searchPalette)}`);
    }
    await evaluate(`(() => {
        window.__searchOriginalFetch = window.fetch;
        window.__globalReady = false;
        window.fetch = (url, options = {}) => {
            if (String(url).startsWith('/api/search/status')) {
                return Promise.resolve(new Response(JSON.stringify(window.__globalReady
                    ? { state: 'ready', percent: 100, processed: 2, total: 2, topics: 2, file: '' }
                    : { state: 'building', percent: 37, processed: 1, total: 2, topics: 1, file: 'VISTA.NG' }),
                    { status: 200, headers: { 'Content-Type': 'application/json' } }));
            }
            if (String(url).startsWith('/api/search/global')) {
                const result = window.__globalReady
                    ? { status: { state: 'ready' }, results: [{ file: 'Norton Guides/vista.json.gz',
                        help_name: 'db_VISTA III Database Programming Guide', context_hex: '378',
                        title: 'Global Vista topic', preview: 'Global search result', index_terms: [], text: '' },
                        { file: 'Borland C++/tchelp.json.gz', help_name: 'Borland C++ 7.0 Help File',
                            context_hex: '379', title: 'Second topic', preview: '', index_terms: [], text: '' }] }
                    : { state: 'building', percent: 37, processed: 1, total: 2, topics: 1, file: 'VISTA.NG' };
                return Promise.resolve(new Response(JSON.stringify(result),
                    { status: window.__globalReady ? 200 : 202, headers: { 'Content-Type': 'application/json' } }));
            }
            return window.__searchOriginalFetch(url, options);
        };
        const dialog = document.querySelector('.tv-search-window');
        const scope = dialog.querySelector('.tv-radio-item input[value="global"]');
        scope.checked = true;
        scope.dispatchEvent(new Event('change', { bubbles: true }));
        void dialog.closest('.tv-dialog-overlay')._tvView.monitorIndex();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const progress = document.querySelector('.tv-progress-window');
            if (progress && !progress.closest('.tv-dialog-overlay').hidden
                && progress.textContent.includes('1 / 2') && progress.textContent.includes('37')
                && document.querySelector('[data-tv-command="global-index-show"]')?.textContent === '▤ 37%'
                && !document.querySelector('[data-tv-command="global-index-show"]').hidden) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Index progress dialog did not appear')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const reopenedIndexProgress = await evaluate(`(() => {
        const TV = window.THelpViewerTV;
        const search = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
        const progress = search.indexProgress;
        progress.hideProgress();
        if (progress.isOpen() || !search.progressDismissed) { throw new Error('Index dialog was not hidden'); }
        const before = document.querySelectorAll('.tv-progress-window').length;
        const app = search.topView();
        app._menuBundleKey = null;
        app._syncBundleMenu();
        const menuView = document.querySelector('[data-tv-menu-bar]')._tvMenuView;
        const command = menuView.indexItem;
        const button = document.querySelector('[data-tv-command="global-index-show"]');
        const rect = button.getBoundingClientRect();
        const clock = document.querySelector('[data-tv-clock]').getBoundingClientRect();
        if (button.hidden || button.textContent !== '▤ 37%' || rect.width <= 0
            || rect.right > clock.left + 1) { throw new Error('Index status/placement lost after menu refresh'); }
        button.click();
        return { same: search.indexProgress === progress, open: progress.isOpen(),
            dismissed: search.progressDismissed, count: document.querySelectorAll('.tv-progress-window').length,
            before, standardItem: command instanceof TV.TVMenuItem, context: command.helpCtx,
            searchContext: TV.TV_HELP_CONTEXTS.hcSearch };
    })()`);
    if (!reopenedIndexProgress.same || !reopenedIndexProgress.open || reopenedIndexProgress.dismissed
        || reopenedIndexProgress.count !== reopenedIndexProgress.before || !reopenedIndexProgress.standardItem
        || reopenedIndexProgress.context !== reopenedIndexProgress.searchContext) {
        throw new Error(`Index menu did not reuse its existing dialog: ${JSON.stringify(reopenedIndexProgress)}`);
    }
    const indexProgress = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-progress-window');
        const view = dialog?.closest('.tv-dialog-overlay')?._tvView;
        const button = dialog?.querySelector('button[data-tv-command="progress-hide"]');
        const file = view?.file.root;
        const client = dialog?.querySelector('.tv-dialog-client');
        return {
            text: dialog?.textContent,
            percent: dialog?.querySelector('.tv-percent-gauge')?.textContent,
            bar: dialog?.querySelector('[data-tv-bar-gauge]')?.textContent,
            columns: view?.bar.size.x,
            buttonRowsBelowFile: button && file
                ? (button.getBoundingClientRect().top - file.getBoundingClientRect().top)
                    / parseFloat(getComputedStyle(file).fontSize) : null,
            buttonInsideFrame: button && client
                ? button.getBoundingClientRect().bottom <= client.getBoundingClientRect().bottom + 1 : false,
        };
    })()`);
    if (!indexProgress.text.includes('1 / 2') || !indexProgress.text.includes('37')
        || indexProgress.bar !== '█'.repeat(Math.floor(indexProgress.columns * 0.37))
            + '░'.repeat(indexProgress.columns - Math.floor(indexProgress.columns * 0.37))
        || Math.abs(indexProgress.buttonRowsBelowFile - 2) > 0.1
        || !indexProgress.buttonInsideFrame) {
        throw new Error(`Global index progress is incomplete: ${JSON.stringify(indexProgress)}`);
    }
    await evaluate(`window.__globalReady = true`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const progress = document.querySelector('.tv-progress-window');
            if (progress?.querySelector('[data-tv-bar-gauge]')?.textContent === '█'.repeat(progress.closest('.tv-dialog-overlay')._tvView.bar.size.x)
                && progress.querySelector('.tv-percent-gauge')?.textContent.includes('100')) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Completed global index bar was not solid')); return; }
            setTimeout(check, 20);
        };
        check();
    })`, true);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const result = document.querySelector('.tv-search-window .tv-search-result');
            const progress = document.querySelector('.tv-progress-window');
            if (result?.textContent.includes('Global Vista topic')
                && (!progress || progress.closest('.tv-dialog-overlay').hidden)) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Global result did not appear')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const globalSearchResult = await evaluate(`(() => {
        const result = document.querySelector('.tv-search-window .tv-search-result');
        const progress = document.querySelector('.tv-progress-window');
        const state = { result: result?.textContent, progressClosed: !progress || progress.closest('.tv-dialog-overlay').hidden };
        return state;
    })()`);
    if (!globalSearchResult.result.includes('Norton Guides/vista.json.gz')
        || !globalSearchResult.progressClosed
        || !(await evaluate(`document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')
            ._tvView.sourceView.root?.textContent`)).includes('db_VISTA III')) {
        throw new Error(`Global Search Topics result is incomplete: ${JSON.stringify(globalSearchResult)}`);
    }
    if (!(await evaluate(`(() => {
        const button = document.querySelector('[data-tv-command="global-index-show"]');
        return button.hidden && button.getBoundingClientRect().width === 0;
    })()`))) {
        throw new Error('Completed global index indicator stayed visible');
    }
    const selectedSource = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
        dialog.selectIndex(1);
        return dialog.sourceView.root?.textContent;
    })()`);
    if (selectedSource !== 'Source: Borland C++ 7.0 Help File') {
        throw new Error(`Search result source did not follow selection: ${selectedSource}`);
    }
    await key("Escape", "Escape", 0, true);
    await evaluate(`(() => {
        window.__globalReady = false;
        window.fetch = (url, options = {}) => String(url).startsWith('/api/search/status')
            ? Promise.resolve(new Response(JSON.stringify(window.__globalReady
                ? { state: 'ready', percent: 100, processed: 2, total: 2, topics: 2, file: '' }
                : { state: 'building', percent: 0, processed: 0, total: 2, topics: 0, file: '' }),
                { status: 200, headers: { 'Content-Type': 'application/json' } }))
            : window.__searchOriginalFetch(url, options);
        const dialog = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
        if (dialog.isOpen()) { throw new Error('Search Topics should be closed'); }
        void dialog.monitorIndex();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const progress = document.querySelector('.tv-progress-window');
            if (progress && !progress.closest('.tv-dialog-overlay').hidden
                && progress.textContent.includes('0 / 2')
                && document.querySelector('[data-tv-command="global-index-show"]')?.textContent === '▤ 0%'
                && !document.querySelector('[data-tv-command="global-index-show"]').hidden
                && progress.querySelector('[data-tv-bar-gauge]')?.textContent === '░'.repeat(progress.closest('.tv-dialog-overlay')._tvView.bar.size.x)) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Startup index progress did not appear')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`window.__globalReady = true`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const progress = document.querySelector('.tv-progress-window');
            if (progress?.querySelector('[data-tv-bar-gauge]')?.textContent === '█'.repeat(progress.closest('.tv-dialog-overlay')._tvView.bar.size.x)) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Startup index bar never filled')); return; }
            setTimeout(check, 20);
        };
        check();
    })`, true);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const progress = document.querySelector('.tv-progress-window');
            if (!progress || progress.closest('.tv-dialog-overlay').hidden) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Startup index progress stayed open')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);

    await evaluate(`(() => {
        window.__savedScopeFetch = window.fetch;
        window.fetch = (url, options = {}) => String(url).startsWith('/api/search/status')
            ? Promise.resolve(new Response('Not Found', { status: 404 }))
            : window.__savedScopeFetch(url, options);
        __tvMenuItem('find', 'Find').click();
    })()`);
    await pause();
    const unavailableFindScope = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-find-window');
        const global = dialog.querySelector('.tv-radio-item input[value="global"]');
        const local = dialog.querySelector('.tv-radio-item input[value="local"]');
        return { globalDisabled: global.disabled,
            globalDimmed: global.parentElement.classList.contains('is-disabled'),
            localEnabled: !local.disabled, localSelected: local.checked };
    })()`);
    if (!unavailableFindScope.globalDisabled || !unavailableFindScope.globalDimmed
        || !unavailableFindScope.localEnabled
        || !unavailableFindScope.localSelected) {
        throw new Error(`Find scopes ignored unavailable server search: ${JSON.stringify(unavailableFindScope)}`);
    }
    await key('Escape', 'Escape', 0, true);
    await evaluate(`__tvMenuItem('dialog-open', 'Search Topics').click()`);
    await pause();
    const unavailableTopicScope = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-search-window');
        const global = dialog.querySelector('.tv-radio-item input[value="global"]');
        const local = dialog.querySelector('.tv-radio-item input[value="local"]');
        return { globalDisabled: global.disabled,
            globalDimmed: global.parentElement.classList.contains('is-disabled'),
            localEnabled: !local.disabled, localSelected: local.checked };
    })()`);
    if (!unavailableTopicScope.globalDisabled || !unavailableTopicScope.globalDimmed
        || !unavailableTopicScope.localEnabled
        || !unavailableTopicScope.localSelected) {
        throw new Error(`Search Topic scopes ignored unavailable server search: ${JSON.stringify(unavailableTopicScope)}`);
    }
    await key('Escape', 'Escape', 0, true);
    await evaluate(`window.fetch = window.__savedScopeFetch`);
    await evaluate(`document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"] .tv-close-control')?.click()`);
    await pause();
    await evaluate(`(() => {
        const item = document.querySelector('[data-tv-command="window-cmd"]');
        const root = item && item.closest('[data-tv-menu-root]');
        const toggle = root && root.querySelector('[data-tv-menu-toggle]');
        if (!toggle) { throw new Error('Windows menu toggle was not found'); }
        toggle.focus();
        toggle.click();
    })()`);
    await key("ArrowDown", "ArrowDown", 0, true);
    await pause();
    const state = await evaluate(`(() => {
        const items = Array.from(document.querySelectorAll('[data-tv-command="window-cmd"]'));
        const commands = { Tile: 'tile', Cascade: 'cascade', 'Window List': 'list', Zoom: 'zoom',
            Next: 'next', Previous: 'previous', Close: 'close' };
        const itemCommand = (item) => commands[item._tvMenuItem?.name.replaceAll('~', '')] || '';
        const byCommand = Object.fromEntries(items.map((item) => [itemCommand(item), {
            disabled: item.disabled,
            ariaDisabled: item.getAttribute('aria-disabled'),
        }]));
        const popup = items[0] && items[0].closest('[data-tv-menu-popup]');
        return {
            popupOpen: Boolean(popup && !popup.hidden),
            focusedCommand: document.activeElement ? itemCommand(document.activeElement) : '',
            byCommand,
        };
    })()`);
    if (!state.popupOpen || state.focusedCommand !== "tile") {
        throw new Error(`Windows menu did not focus its first enabled item: ${JSON.stringify(state)}`);
    }
    for (const command of ["next", "previous"]) {
        if (!state.byCommand[command].disabled || state.byCommand[command].ariaDisabled !== "true") {
            throw new Error(`${command} should be disabled while one document is the only target: `
                + JSON.stringify(await evaluate(`Array.from(document.querySelectorAll('.tv-dialog-overlay'))
                    .filter((root) => !root.hidden).map((root) => root._tvView?.title)`)));
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
    const windowListOpen = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-winlist-window');
        const list = dialog?.querySelector('[data-tv-winlist-listviewer]');
        const viewport = list?.querySelector('[data-tv-list-viewport]');
        const selected = list?.querySelector('.tv-vlist-item.is-selected');
        const colors = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            viewport: viewport ? colors(viewport) : [],
            selected: selected ? colors(selected) : [],
        };
    })()`);
    if (!windowListOpen.open
        || windowListOpen.viewport.join() !== ['rgb(0, 170, 170)', 'rgb(0, 0, 0)'].join()
        || windowListOpen.selected.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()) {
        throw new Error(`Window List palette is wrong: ${JSON.stringify(windowListOpen)}`);
    }
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
    await evaluate(`__tvMenuItem('dialog-open', 'Colors').click()`);
    await pause();
    const colors = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Colors'
        );
        if (!dialog) { return { open: false }; }
        const main = dialog.querySelector('.tv-dialog-body > .tv-dialog-client > .tv-group');
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
        const groupItems = dialog.querySelectorAll('[data-tv-colors-groups] [data-tv-list-index]');
        const itemSelected = dialog.querySelector('[data-tv-colors-items] [data-tv-list-index].is-selected');
        const groupSelected = dialog.querySelector('[data-tv-colors-groups] [data-tv-list-index].is-selected');
        const buttonRects = Array.from(dialog.querySelectorAll(
            '[data-tv-colors-default], [data-tv-colors-reset-all], [data-tv-colors-ok], [data-tv-colors-cancel]'
        ), (element) => element.getBoundingClientRect());
        const buttonsRect = {
            left: Math.min(...buttonRects.map((rect) => rect.left)),
            top: Math.min(...buttonRects.map((rect) => rect.top)),
            right: Math.max(...buttonRects.map((rect) => rect.right)),
            bottom: Math.max(...buttonRects.map((rect) => rect.bottom)),
        };
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        const dialogDefaults = window.THelpViewerTV.buildDefaultColorPalette()
            .find((group) => group.name === 'Dialogs/Calc');
        return {
            open: !dialog.closest('.tv-dialog-overlay').hidden,
            size: [Math.round(mainRect.width / cellWidth) + 2, Math.round(mainRect.height / cellHeight) + 2],
            groupList: offset('[data-tv-colors-groups]'),
            itemList: offset('[data-tv-colors-items]'),
            foreground: offset('[data-tv-colors-foreground]'),
            background: offset('[data-tv-colors-background]'),
            display: offset('[data-tv-colors-display]'),
            buttons: [
                Math.round((buttonsRect.left - mainRect.left) / cellWidth),
                Math.round((buttonsRect.top - mainRect.top) / cellHeight),
                Math.round((buttonsRect.right - buttonsRect.left) / cellWidth),
                Math.round((buttonsRect.bottom - buttonsRect.top) / cellHeight),
            ],
            buttonCount: buttonRects.length,
            resetAllCount: dialog.querySelectorAll('[data-tv-colors-reset-all]').length,
            defaultCount: dialog.querySelectorAll('[data-tv-colors-default]').length,
            foregroundColors: dialog.querySelectorAll('[data-tv-colors-foreground] .tv-color-cell').length,
            backgroundColors: dialog.querySelectorAll('[data-tv-colors-background] .tv-color-cell').length,
            sampleRows: (dialog.querySelector('[data-tv-colors-display] > .tv-static-text')?.textContent || '')
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
        buttons: [5, 14, 50, 2],
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
        dialog.querySelector('[data-tv-colors-groups] [data-tv-list-index="2"]').click();
        dialog.querySelector('[data-tv-colors-items] [data-tv-list-index="1"]').click();
        const group = dialog.querySelector('[data-tv-colors-groups] [data-tv-list-index].is-selected');
        const item = dialog.querySelector('[data-tv-colors-items] [data-tv-list-index].is-selected');
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
        const chooseItem = (index) => dialog
            .querySelector('[data-tv-colors-items] [data-tv-list-index="' + index + '"]').click();
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
    await evaluate(`__tvMenuItem('dialog-open', 'About').click()`);
    await pause();
    const passiveColors = await evaluate(`(() => {
        const colorsDialog = document.querySelector('.tv-colors-window');
        const selected = colorsDialog.querySelector(
            '[data-tv-colors-groups] [data-tv-list-index].is-selected'
        );
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
            closeVisible: !colorsDialog.querySelector('[data-tv-close-button]').hidden,
            closePassive: colorsDialog.querySelector('[data-tv-close-button]').classList.contains('is-frame-control-passive'),
        };
    })()`);
    if (
        !passiveColors.inactive || passiveColors.cornerGlyph !== '┌'
        || !passiveColors.closeVisible || !passiveColors.closePassive
        || passiveColors.cornerColors.join() !== ['rgb(170, 170, 170)', 'rgb(0, 0, 0)'].join()
        || passiveColors.selectedColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
    ) {
        throw new Error(`Inactive Colors state differs from Turbo Vision 2.0: ${JSON.stringify(passiveColors)}`);
    }
    await evaluate(`document.querySelector('.tv-about-window [data-tv-command="about-ok"]').click()`);
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

    await evaluate(`__tvMenuItem('dialog-open', 'Widget Gallery').click()`);
    await pause();
    const gallerySetup = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Widget Gallery'
        );
        if (!dialog) { return { open: false }; }
        const label = dialog.querySelector('label[for]');
        const input = dialog.querySelector('.tv-input-line');
        label.click();
        const labelFocus = label.htmlFor === input.id && document.activeElement === input;
        dialog.querySelector('[data-tv-gallery-apply]').click();
        return {
            open: true,
            labelFocus,
        };
    })()`);
    if (!gallerySetup.open) { throw new Error('Widget Gallery did not open'); }
    await pause();
    const galleryPoint = await evaluate(`(() => {
        const item = document.querySelector('.tv-widget-gallery-window .tv-vlist-viewer [data-tv-list-index="2"]');
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
        const clickedItem = dialog.querySelector('.tv-vlist-viewer [data-tv-list-index="2"]');
        const body = dialog.querySelector('.tv-widget-gallery-body');
        const bodyRect = body.getBoundingClientRect();
        const sideRects = Array.from(body.querySelectorAll(':scope > .tv-border-side'))
            .map((element) => element.getBoundingClientRect());
        const info = dialog.querySelector('.tv-info-box');
        const infoRows = Array.from(dialog.querySelectorAll('[data-tv-terminal-line]'));
        const infoRow = infoRows.at(-1);
        const infoRect = info.getBoundingClientRect();
        const rowRect = infoRow.getBoundingClientRect();
        const infoSides = Array.from(infoRow.querySelectorAll('[data-tv-info-side]'));
        const rightInfoSideRect = infoSides.at(-1)?.getBoundingClientRect();
        const topFrameRect = info.querySelector('[data-tv-info-frame="top"]').getBoundingClientRect();
        const bottomFrameRect = info.querySelector('[data-tv-info-frame="bottom"]').getBoundingClientRect();
        const terminalRect = info.querySelector('.tv-terminal').getBoundingClientRect();
        const disabledButtonRect = dialog.querySelector('.tv-dialog-button:disabled').getBoundingClientRect();
        const clientRect = dialog.querySelector('.tv-dialog-client').getBoundingClientRect();
        const viewport = dialog.querySelector('.tv-vlist-viewer [data-tv-list-viewport]');
        const firstItem = dialog.querySelector('.tv-vlist-viewer [data-tv-list-index="0"]');
        const normalItem = dialog.querySelector('.tv-vlist-viewer [data-tv-list-index="1"]');
        const check = dialog.querySelector('.tv-checkbox-item');
        const disabledCheck = dialog.querySelector('.tv-checkbox-item:nth-child(3)');
        const radio = dialog.querySelector('.tv-radio-item');
        const multiCheck = dialog.querySelector('.tv-multicheck-item button');
        const stylePair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        multiCheck.click();
        return {
            open: true,
            checks: dialog.querySelectorAll('.tv-checkbox-item input[type="checkbox"]').length,
            radios: dialog.querySelectorAll('.tv-radio-item input[type="radio"]').length,
            multiChecks: dialog.querySelectorAll('.tv-multicheck-button').length,
            multiStates: Array.from(dialog.querySelectorAll('.tv-multicheck-button'))
                .map((element) => element.getAttribute('aria-checked')),
            multiCycled: multiCheck.getAttribute('aria-checked'),
            disabledChoices: dialog.querySelectorAll('.tv-choice-input:disabled').length,
            listItems: dialog.querySelectorAll('.tv-vlist-viewer [data-tv-list-index]').length,
            selectedItems: dialog.querySelectorAll('.tv-vlist-viewer [data-tv-list-index].is-selected').length,
            selectedIndex: dialog.querySelector(
                '.tv-vlist-viewer [data-tv-list-index].is-selected'
            )?.dataset.tvListIndex,
            listFocused: document.activeElement === clickedItem,
            disabledButtons: dialog.querySelectorAll('.tv-dialog-button:disabled').length,
            messageButtons: dialog.querySelectorAll('[data-tv-gallery-message]').length,
            staticTexts: Array.from(dialog.querySelectorAll('.tv-static-text'))
                .filter((element) => element.textContent.includes('Static text ·')).length,
            status: dialog.querySelector('.tv-terminal')?.textContent || '',
            terminalRows: infoRows.length,
            firstRowOffset: Math.abs(firstItem.getBoundingClientRect().top - viewport.getBoundingClientRect().top),
            scrollbarEnabled: !dialog.querySelector('.tv-vlist-viewer').classList.contains('is-disabled'),
            listNormalColors: stylePair(normalItem),
            listFocusedColors: stylePair(clickedItem),
            checkColors: stylePair(check),
            radioColors: stylePair(radio),
            disabledCheckColors: stylePair(disabledCheck),
            checkHotkeyColor: getComputedStyle(check.querySelector('.tv-hotkey')).color,
            infoRightBorder: infoRow.textContent.endsWith('│'),
            infoRightBorderAligned: Boolean(
                rightInfoSideRect && Math.abs(rightInfoSideRect.right - infoRect.right) < 1
            ),
            infoRowFits: rowRect.right <= infoRect.right + 0.5 && info.scrollWidth <= info.clientWidth,
            infoColumns: Math.round(infoRect.width / (bodyRect.width / 68)),
            infoFrameComplete: Math.abs(topFrameRect.top - infoRect.top) < 1
                && Math.abs(bottomFrameRect.bottom - infoRect.bottom) < 1
                && terminalRect.top >= topFrameRect.bottom - 1
                && terminalRect.bottom <= bottomFrameRect.top + 1,
            disabledButtonInside: disabledButtonRect.right <= clientRect.right + 1,
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
        || gallery.terminalRows !== 3 || !gallery.infoRightBorder || !gallery.infoRightBorderAligned
        || !gallery.infoRowFits
        || gallery.infoColumns !== 62 || !gallery.infoFrameComplete || !gallery.disabledButtonInside
        || gallery.infoSideColors.some((color) => color !== 'rgb(255, 255, 255)')
        || !gallery.frameSidesAligned
    ) {
        throw new Error(`Widget Gallery controls are incomplete: ${JSON.stringify(gallery)}`);
    }
    await evaluate(`document.querySelector('[data-tv-gallery-message]').click()`);
    await pause();
    const messageOpen = await evaluate(`(() => {
        const box = document.querySelector('.tv-msgbox-window');
        const rect = box?.getBoundingClientRect();
        const content = box?.querySelector('.tv-dialog-client > .tv-group > .tv-group:first-child')?.getBoundingClientRect();
        const titlebar = box?.querySelector('.tv-dialog-titlebar')?.getBoundingClientRect();
        const rightCorner = box?.querySelector('.tv-dialog-titlebar .tv-border-corner:last-of-type')?.getBoundingClientRect();
        const closeRect = box?.querySelector('.tv-dialog-close-control')?.getBoundingClientRect();
        const commandButtons = Array.from(box?.querySelectorAll('.tv-dialog-client > .tv-group > .tv-group:last-child .tv-dialog-button') || []);
        const buttonRects = commandButtons.map((button) => button.getBoundingClientRect());
        const cellWidth = rect ? rect.width / 42 : 0;
        return {
            open: Boolean(box && !box.closest('.tv-dialog-overlay').hidden),
            title: box?.querySelector('.tv-dialog-title-text')?.textContent || '',
            width: rect?.width || 0,
            height: rect?.height || 0,
            contentInside: Boolean(rect && content && content.left >= rect.left && content.right <= rect.right
                && content.top >= rect.top && content.bottom <= rect.bottom),
            closeButton: Boolean(box?.querySelector('.tv-dialog-close-control')),
            closePoint: closeRect ? { x: closeRect.left + closeRect.width / 2, y: closeRect.top + closeRect.height / 2 } : null,
            rightCornerAligned: Boolean(titlebar && rightCorner && Math.abs(rightCorner.right - titlebar.right) < 1),
            buttonGap: buttonRects.length > 1 ? (buttonRects[1].left - buttonRects[0].right) / cellWidth : 0,
        };
    })()`);
    if (!messageOpen.open || messageOpen.title !== 'Information'
        || messageOpen.width < 300 || messageOpen.height < 100 || !messageOpen.contentInside
        || !messageOpen.closeButton || !messageOpen.closePoint
        || !messageOpen.rightCornerAligned || messageOpen.buttonGap < 1.5) {
        throw new Error(`Widget Gallery message box has invalid geometry: ${JSON.stringify(messageOpen)}`);
    }
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: messageOpen.closePoint.x, y: messageOpen.closePoint.y,
        button: 'left', clickCount: 1,
    });
    const messagePressed = await evaluate(`(() => {
        const box = document.querySelector('.tv-msgbox-window');
        return {
            open: Boolean(box && !box.closest('.tv-dialog-overlay').hidden),
            glyph: box?.querySelector('.tv-dialog-close-control [data-tv-close-glyph]')?.textContent || '',
        };
    })()`);
    if (!messagePressed.open || messagePressed.glyph !== '⁎') {
        throw new Error(`Message box closed before mouse release: ${JSON.stringify(messagePressed)}`);
    }
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: messageOpen.closePoint.x, y: messageOpen.closePoint.y,
        button: 'left', clickCount: 1,
    });
    await pause();
    const messageResult = await evaluate(
        `document.querySelector('.tv-widget-gallery-window .tv-terminal')?.textContent || ''`
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

    await evaluate(`__tvMenuItem('dialog-open', 'Grid Viewer').click()`);
    await pause();
    const grid = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-grid-demo-window');
        const view = dialog?.querySelector('.tv-grid-view');
        const header = view?.querySelector('.tv-grid-header');
        const cell = view?.querySelector('[data-tv-list-index="0"] [data-tv-grid-column="1"]');
        cell?.click();
        cell?.closest('[data-tv-list-index]')?.focus();
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            header: header?.textContent,
            selected: view?.querySelector('.tv-grid-cell.is-selected')?.dataset.tvGridColumn,
            horizontal: Boolean(view?.querySelector('.tv-scrollbar-x')),
            vertical: Boolean(view?.querySelector('.tv-scrollbar-y')),
        };
    })()`);
    if (!grid.open || !grid.header.includes('Object') || grid.selected !== '1'
        || !grid.horizontal || !grid.vertical) {
        throw new Error(`TVGridView initial state is invalid: ${JSON.stringify(grid)}`);
    }
    const gridScroll = await evaluate(`(() => {
        const view = document.querySelector('.tv-grid-demo-window .tv-grid-view');
        const viewport = view?.querySelector('.tv-vlist-viewport');
        view?.querySelector('.tv-scrollbar-x .tv-scroll-arrow-forward')?.dispatchEvent(
            new MouseEvent('mousedown', { bubbles: true }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        return {
            overflow: viewport?.scrollWidth > viewport?.clientWidth,
            position: viewport?.scrollLeft || 0,
            visible: view?.classList.contains('is-h-scrollable'),
        };
    })()`);
    if (!gridScroll.overflow || gridScroll.position <= 0 || !gridScroll.visible) {
        throw new Error(`TVGridView horizontal scrolling failed: ${JSON.stringify(gridScroll)}`);
    }
    const gridHorizontalPoint = await evaluate(`(() => {
        const track = document.querySelector('.tv-grid-demo-window .tv-grid-view .tv-scrollbar-x .tv-scroll-track');
        const rect = track?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width * 0.9, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!gridHorizontalPoint) { throw new Error('TVGridView horizontal scrollbar track is missing'); }
    await clickPoint(gridHorizontalPoint);
    const gridHorizontalAfter = await evaluate(`document.querySelector('.tv-grid-demo-window .tv-grid-view .tv-vlist-viewport')?.scrollLeft`);
    if (gridHorizontalAfter <= gridScroll.position) {
        throw new Error(`TVGridView horizontal scrollbar track click failed: ${JSON.stringify({ gridHorizontalPoint, gridHorizontalAfter })}`);
    }
    const gridVerticalPoint = await evaluate(`(() => {
        const view = document.querySelector('.tv-grid-demo-window .tv-grid-view');
        const list = view?._tvListViewer;
        list?.setRows(Array.from({ length: 40 }, (_, index) => [
            'View ' + index, 'TVView', 'Scrollbar pointer test',
        ]));
        const arrow = view?.querySelector('.tv-scrollbar-y .tv-scroll-arrow-forward');
        const rect = arrow?.getBoundingClientRect();
        const metrics = list?.scrollbarWidget?.axisMetrics('y');
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2,
            before: list?.viewport?.scrollTop, active: list?.scrollbarWidget?.active,
            maxScroll: metrics?.maxScroll, trackSize: metrics?.trackSize,
            hit: document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)?.className,
        } : null;
    })()`);
    if (!gridVerticalPoint) { throw new Error('TVGridView vertical scrollbar arrow is missing'); }
    await clickPoint(gridVerticalPoint);
    const gridVerticalAfter = await evaluate(`document.querySelector('.tv-grid-demo-window .tv-grid-view .tv-vlist-viewport')?.scrollTop`);
    if (gridVerticalAfter <= gridVerticalPoint.before) {
        throw new Error(`TVGridView vertical scrollbar click failed: ${JSON.stringify({ gridVerticalPoint, gridVerticalAfter })}`);
    }
    const gridTrackPoint = await evaluate(`(() => {
        const view = document.querySelector('.tv-grid-demo-window .tv-grid-view');
        const track = view?.querySelector('.tv-scrollbar-y .tv-scroll-track');
        const rect = track?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height * 0.65 } : null;
    })()`);
    if (!gridTrackPoint) { throw new Error('TVGridView scrollbar track is missing'); }
    await clickPoint(gridTrackPoint);
    const gridTrackAfter = await evaluate(`document.querySelector('.tv-grid-demo-window .tv-grid-view .tv-vlist-viewport')?.scrollTop`);
    if (gridTrackAfter <= gridVerticalAfter) {
        throw new Error(`TVGridView scrollbar track click failed: ${JSON.stringify({ gridTrackPoint, gridVerticalAfter, gridTrackAfter })}`);
    }
    const gridThumbPoint = await evaluate(`(() => {
        const thumb = document.querySelector('.tv-grid-demo-window .tv-grid-view .tv-scrollbar-y .tv-thumb-cell');
        const rect = thumb?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!gridThumbPoint) { throw new Error('TVGridView scrollbar thumb is missing'); }
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: gridThumbPoint.x, y: gridThumbPoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseMoved', x: gridThumbPoint.x, y: gridThumbPoint.y + 20, button: 'left', buttons: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: gridThumbPoint.x, y: gridThumbPoint.y + 20, button: 'left', clickCount: 1,
    });
    const gridThumbAfter = await evaluate(`document.querySelector('.tv-grid-demo-window .tv-grid-view .tv-vlist-viewport')?.scrollTop`);
    if (gridThumbAfter <= gridTrackAfter) {
        throw new Error(`TVGridView scrollbar thumb drag failed: ${JSON.stringify({ gridTrackAfter, gridThumbAfter })}`);
    }
    await evaluate(`document.querySelector('.tv-grid-demo-window .tv-grid-row.is-selected')?.focus()`);
    await key('ArrowRight', 'ArrowRight', 0, true);
    const gridMoved = await evaluate(`document.querySelector('.tv-grid-demo-window .tv-grid-cell.is-selected')?.dataset.tvGridColumn`);
    if (gridMoved !== '2') { throw new Error(`TVGridView did not move right: ${gridMoved}`); }
    await evaluate(`document.querySelector('.tv-grid-demo-window [data-tv-command="grid-headers"]')?.click()`);
    const gridHeaderHidden = await evaluate(`getComputedStyle(document.querySelector('.tv-grid-demo-window .tv-grid-header')).display`);
    if (gridHeaderHidden !== 'none') { throw new Error('TVGridView header toggle failed'); }
    await key('Escape', 'Escape', 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Change dir...').click()`);
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
        const outlineView = dialog?.querySelector('.tv-dialog-client > .tv-group > .tv-vlist-viewer');
        const docs = Array.from(outlineView?.querySelectorAll('[data-tv-list-index]') || []).find((item) =>
            item.textContent.trim().endsWith('DOCS' + slash)
        );
        docs?.click();
        const selectedPath = dialog?.querySelector('.tv-input-line')?.value;
        dialog?.querySelector('[data-tv-change-dir-revert]')?.click();
        const revertedPath = dialog?.querySelector('.tv-input-line')?.value;
        dialog?.querySelector('[data-tv-change-dir-confirm]')?.click();
        return {
            open: Boolean(dialog),
            directories: outlineView?.querySelectorAll('[data-tv-list-index]').length || 0,
            sharedScrollbar: Boolean(outlineView?.querySelector('.tv-scrollbar-y')),
            outline: Boolean(outlineView?._tvListViewer)
                && Array.from(outlineView?.querySelectorAll('[data-tv-list-index]') || [])
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
    await evaluate(`__tvMenuItem('dialog-open', 'Change dir...').click()`);
    await pause();
    // Test overflow independently of how many HELP products are installed.
    await evaluate(`(() => {
        const view = document.querySelector('.tv-change-dir-window').closest('.tv-dialog-overlay')._tvView;
        view.directoryList.setTree([...view.directoryTree, ...Array.from({length: 40}, (_, index) => ({
            key: 'scroll-test-' + index, path: 'scroll-test-' + index, label: 'Test directory ' + index,
        }))], view.currentDirectory, {expandAll: true});
    })()`);
    const changeDirectoryWheelTarget = await evaluate(`(() => {
        const viewport = document.querySelector(
            '.tv-change-dir-window .tv-dialog-client > .tv-group > .tv-vlist-viewer > .tv-vlist-viewport'
        );
        const scrollbar = viewport?.parentElement?.querySelector('.tv-scrollbar-y');
        const rect = viewport?.getBoundingClientRect();
        const scrollbarRect = scrollbar?.getBoundingClientRect();
        return rect && scrollbarRect ? {
            x: scrollbarRect.left + scrollbarRect.width / 2,
            y: scrollbarRect.top + scrollbarRect.height / 2,
            before: viewport.scrollTop,
            max: viewport.scrollHeight - viewport.clientHeight,
            overScrollbar: true,
        } : null;
    })()`);
    if (!changeDirectoryWheelTarget || !changeDirectoryWheelTarget.overScrollbar
        || changeDirectoryWheelTarget.max <= 0) {
        throw new Error(`Change Directory has no wheel-scrollable directory list: ${JSON.stringify(changeDirectoryWheelTarget)}`);
    }
    await send('Input.dispatchMouseEvent', {
        type: 'mouseWheel',
        x: changeDirectoryWheelTarget.x,
        y: changeDirectoryWheelTarget.y,
        deltaX: 0,
        deltaY: 160,
    });
    await pause();
    const changeDirectoryWheelAfter = await evaluate(`document.querySelector(
        '.tv-change-dir-window .tv-vlist-viewport'
    )?.scrollTop || 0`);
    if (changeDirectoryWheelAfter <= changeDirectoryWheelTarget.before) {
        throw new Error(`Change Directory ignored the mouse wheel: ${JSON.stringify({
            changeDirectoryWheelTarget, changeDirectoryWheelAfter,
        })}`);
    }
    await evaluate(`(() => {
        const view = document.querySelector('.tv-change-dir-window').closest('.tv-dialog-overlay')._tvView;
        view.directoryList.setTree(view.directoryTree, view.currentDirectory, {expandAll: true});
    })()`);
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
    const changeDirectoryHistoryClosePoint = await evaluate(`(() => {
        const rect = document.querySelector(
            '[data-tv-change-dir-history-popup] [data-tv-close-button]'
        )?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!changeDirectoryHistoryClosePoint) {
        throw new Error('Change Directory history close control is missing');
    }
    await clickPoint(changeDirectoryHistoryClosePoint);
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

    await evaluate(`__tvMenuItem('file-open', 'Open...').click()`);
    await pause();
    const fileOpen = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        if (!dialog) { return { open: false }; }
        const slash = String.fromCharCode(92);
        const rootItems = Array.from(dialog.querySelectorAll('[data-tv-file-open-files] [data-tv-list-index]'));
        const rootDirectories = rootItems.filter((element) => element.textContent.trim().endsWith(slash));
        const docsDirectory = rootDirectories.find((element) => element.textContent.trim() === "DOCS" + slash);
        if (!docsDirectory) { return { open: true, docsDirectory: false }; }
        docsDirectory.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
        const docItems = Array.from(dialog.querySelectorAll('[data-tv-file-open-files] [data-tv-list-index]'));
        const firstFile = docItems.find((element) => !element.textContent.trim().endsWith(slash));
        if (!firstFile) { return { open: true, docsDirectory: true, files: 0 }; }
        firstFile.click();
        const input = dialog.querySelector('.tv-input-line');
        const fileList = dialog.querySelector('[data-tv-file-open-files]');
        const fileViewport = fileList.querySelector('[data-tv-list-viewport]');
        const verticalScrollbar = fileList.querySelector('.tv-scrollbar-y');
        const backwardRect = verticalScrollbar?.querySelector('[data-role="backward"]')?.getBoundingClientRect();
        const trackRect = verticalScrollbar?.querySelector('[data-role="track"]')?.getBoundingClientRect();
        const forwardRect = verticalScrollbar?.querySelector('[data-role="forward"]')?.getBoundingClientRect();
        const titlebar = dialog.querySelector('.tv-dialog-titlebar');
        const title = dialog.querySelector('.tv-dialog-title-text');
        const dialogRect = dialog.getBoundingClientRect();
        const titleRect = title.getBoundingClientRect();
        const selectedItem = dialog.querySelector('[data-tv-file-open-files] [data-tv-list-index].is-selected');
        const normalItem = Array.from(dialog.querySelectorAll('[data-tv-file-open-files] [data-tv-list-index]'))
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
            twoColumnFlow: getComputedStyle(fileViewport).gridAutoFlow,
            verticalScrollbar: Boolean(backwardRect && trackRect && forwardRect
                && trackRect.height > 1
                && forwardRect.top > backwardRect.bottom),
            horizontalScrollbar: dialog.querySelectorAll('.tv-file-open-scroll-button').length === 2
                && Boolean(dialog.querySelector('[data-tv-file-open-scroll-left] + .tv-static-text')),
            path: (dialog.querySelectorAll('[data-tv-file-open-cancel] ~ .tv-static-text')[0]?.textContent || '').trim(),
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
        || fileOpen.twoColumnFlow !== "column" || !fileOpen.horizontalScrollbar || !fileOpen.verticalScrollbar
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
    const fileListKeys = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Open a File'
        );
        const list = dialog.querySelector('[data-tv-file-open-files]');
        const entries = Array.from(list.querySelectorAll('[data-tv-list-index]'));
        const first = entries[0];
        first.focus();
        first.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
        const selected = list.querySelector('[data-tv-list-index].is-selected');
        dialog.querySelector('.tv-input-line').focus();
        return {
            rows: list._tvView?.rows,
            cssRows: getComputedStyle(list).getPropertyValue('--tv-file-list-rows').trim(),
            selected: Number(selected?.getAttribute('data-tv-list-index')),
            expected: Math.min(entries.length - 1, 8),
        };
    })()`);
    if (fileListKeys.rows !== 8 || fileListKeys.cssRows !== '8'
        || fileListKeys.selected !== fileListKeys.expected) {
        throw new Error(`File list column navigation drifted from its row count: ${JSON.stringify(fileListKeys)}`);
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

    await evaluate(`__tvMenuItem('file-open', 'Open...').click()`);
    await pause();
    const historyOpen = await evaluate(`(() => {
        const button = document.querySelector('[data-tv-file-open-history]');
        const popup = document.querySelector('[data-tv-file-open-history-popup]');
        const initiallyHidden = Boolean(popup?.hidden && getComputedStyle(popup).display === 'none');
        button.click();
        const input = document.querySelector('.tv-file-open-window .tv-input-line');
        const popupStyle = getComputedStyle(popup);
        const titleFill = popup?.querySelector('.tv-window-caption-fill');
        const selected = popup?.querySelector('[data-tv-list-index].is-selected');
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
            entries: popup?.querySelectorAll('[data-tv-list-index]').length || 0,
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
            corners: popup?.querySelectorAll('[data-tv-frame-corner]').length || 0,
            closeButtons: popup?.querySelectorAll('[data-tv-close-button]').length || 0,
            continuousTop: Boolean(titleFill && !popup?.querySelector('.tv-window-caption')
                && titleFill.textContent.includes('═')),
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
        || !historyOpen.popupAboveButton || !historyOpen.continuousTop) {
        throw new Error(`File Open history does not match THistoryWindow: ${JSON.stringify(historyOpen)}`);
    }
    const fileHistoryClosePoint = await evaluate(`(() => {
        const rect = document.querySelector('[data-tv-file-open-history-popup] [data-tv-close-button]')
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
        const rect = document.querySelector('.tv-file-open-window [data-tv-file-open-cancel] ~ .tv-static-text')?.getBoundingClientRect();
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
            if (open?.querySelectorAll('[data-tv-list-index]').length >= 2 && more) {
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
            entries: dialog.querySelectorAll('[data-tv-file-open-files] [data-tv-list-index]').length,
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
        const entry = Array.from(document.querySelectorAll('[data-tv-command="bundle-open"]')).find((element) =>
            element._tvMenuItem?.name === 'db_VISTA III'
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
        && frame.controls.every((control) => !control.hidden && control.passive
            && control.tabIndex === -1 && control.display !== 'none')
        && frame.controls[0].ariaHidden === null && frame.controls[0].ariaDisabled === null
        && frame.controls[1].ariaHidden === 'true' && frame.controls[1].ariaDisabled === 'true'
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
        const link = document.createElement('a');
        link.href = '/missing-in-app-link';
        link.target = '_blank';
        link.textContent = 'Missing local file';
        link.dataset.tvMissingLinkProbe = '1';
        readme.querySelector('[data-tv-doc-editor]').appendChild(link);
        window.__tvDesktopBeforeMissingLink = document.querySelector('[data-tv-bundle-desktop]');
        link.click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const box = document.querySelector('.tv-msgbox-window');
            const title = box?.querySelector('.tv-dialog-title-text')?.textContent;
            if (box && !box.closest('.tv-dialog-overlay').hidden && title === 'Server Error') {
                resolve(true);
                return;
            }
            if (Date.now() >= deadline) { reject(new Error('Local 404 did not open the existing MessageBox')); return; }
            setTimeout(check, 25);
        };
        check();
    })`, true);
    const local404 = await evaluate(`(() => {
        const box = document.querySelector('.tv-msgbox-window');
        return {
            sameDesktop: window.__tvDesktopBeforeMissingLink === document.querySelector('[data-tv-bundle-desktop]'),
            path: window.location.pathname,
            message: Array.from(box?.querySelectorAll('.tv-static-text') || [])
                .map((element) => element.textContent || '').join(String.fromCharCode(10)),
        };
    })()`);
    if (!local404.sameDesktop || local404.path !== '/'
        || !local404.message.includes('/missing-in-app-link')) {
        throw new Error(`Local 404 replaced the running viewer: ${JSON.stringify(local404)}`);
    }
    await evaluate(`document.querySelector('.tv-msgbox-window [data-tv-command="msgbox-cmd"]').click()`);

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

    const tiledDocs = await evaluate(`(() => {
        const doc = document.querySelector('.tv-doc-window');
        doc?._tvWindowView?.zoom();
        __tvMenuItem('window-cmd', 'Tile').click();
        return Array.from(document.querySelectorAll('.tv-doc-window')).map((element) => ({
            resizer: Boolean(element._tvResizer),
            maximized: element.classList.contains('is-maximized'),
            glyph: element.querySelector('[data-tv-zoom-glyph]')?.textContent,
            cols: element.style.getPropertyValue('--tv-window-cols'),
            restoredCols: String(element._tvResizer?.restoreSnapshot?.cols),
        }));
    })()`);
    if (tiledDocs.length < 2 || tiledDocs.some((entry) => !entry.resizer || entry.maximized
        || entry.glyph !== '↑' || entry.cols !== entry.restoredCols)) {
        throw new Error(`Tile did not synchronize document window state: ${JSON.stringify(tiledDocs)}`);
    }
    const cascadedDocs = await evaluate(`(() => {
        __tvMenuItem('window-cmd', 'Cascade').click();
        return Array.from(document.querySelectorAll('.tv-doc-window')).map((element) => ({
            left: element.style.getPropertyValue('--tv-window-left'),
            restoredLeft: element._tvResizer?.restoreSnapshot?.left,
        }));
    })()`);
    if (cascadedDocs.length < 2 || cascadedDocs.some((entry) =>
        Number.parseFloat(entry.left) !== entry.restoredLeft)) {
        throw new Error(`Cascade did not synchronize document restore positions: ${JSON.stringify(cascadedDocs)}`);
    }

    await evaluate(`__tvMenuItem('dialog-open', 'MIDI Player').click()`);
    await pause();
    const midiCompact = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'CD/MIDI Player'
        );
        const advanced = dialog?.querySelector('.tv-input-line')?.closest('.tv-group');
        const list = dialog?.querySelector('[data-tv-midi-track-list]');
        const side = dialog?.querySelector('.tv-dialog-body > .tv-border-side');
        const displayParts = Array.from(dialog?.querySelectorAll('[data-tv-midi-display] > .tv-static-text') || []);
        const displayPartNames = displayParts.map((element) => element.getAttribute('data-tv-midi-part'));
        const displayRect = dialog?.querySelector('[data-tv-midi-display]')?.getBoundingClientRect();
        const coverRect = dialog?.querySelector('.tv-image')?.getBoundingClientRect();
        dialog?.querySelector('[data-tv-bar-gauge]')?._tvView?.updateView(50);
        const meter = dialog?.querySelector('[data-tv-bar-gauge]');
        const meterRect = meter?.getBoundingClientRect();
        const controlRect = dialog?.querySelector('[data-tv-midi-previous]')?.getBoundingClientRect();
        const controls = ['midi-previous', 'midi-play', 'midi-pause', 'midi-stop', 'midi-next', 'midi-more']
            .map((command) => dialog?.querySelector('[data-tv-command="' + command + '"]')?.getBoundingClientRect());
        const listRect = list?.getBoundingClientRect();
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            synthPreloadStarted: Boolean(dialog?.closest('.tv-dialog-overlay')._tvView?.synth?.constructor.assetsPromise),
            advancedHidden: Boolean(advanced?.hidden),
            trackListHidden: Boolean(list?.hidden && getComputedStyle(list).display === 'none'),
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
            displayPartNames,
            coverBeforeDisplay: Boolean(coverRect && displayRect
                && coverRect.width > 0 && coverRect.height > 0 && coverRect.right < displayRect.left),
            verticalOrder: Boolean(displayRect && meterRect && controlRect
                && displayRect.top < meterRect.top && meterRect.top < controlRect.top),
            separatedRows: Boolean(displayRect && meterRect && controlRect
                && Math.abs((meterRect.top - displayRect.bottom) - displayRect.height / 3) < 1
                && Math.abs((controlRect.top - meterRect.bottom) - meterRect.height) < 1),
            controlGaps: Boolean(meterRect && controls.every(Boolean)
                && controls.slice(1).every((control, index) =>
                    Math.abs((control.left - controls[index].right) - meterRect.width / 40) < 1)),
            meterOwned: Boolean(meter && meter.childElementCount === 0
                && meter.textContent === '█'.repeat(20) + '░'.repeat(20)
                && meter.getAttribute('aria-valuenow') === '50'),
            positions: {
                display: displayRect ? [displayRect.top, displayRect.bottom] : null,
                meter: meterRect ? [meterRect.top, meterRect.bottom] : null,
                control: controlRect ? [controlRect.top, controlRect.bottom] : null,
                list: listRect ? [listRect.top, listRect.bottom] : null,
            },
        };
    })()`);
    if (
        !midiCompact.open || !midiCompact.synthPreloadStarted
        || !midiCompact.advancedHidden || !midiCompact.trackListHidden
        || !midiCompact.moreCollapsed
        || !midiCompact.sharedScrollbar || !midiCompact.displayTextVisible
        || midiCompact.displayPartNames.join() !== 'label,number,time,title,status'
        || !midiCompact.coverBeforeDisplay || !midiCompact.verticalOrder
        || !midiCompact.separatedRows || !midiCompact.controlGaps || !midiCompact.meterOwned
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
        const body = dialog?.querySelector('.tv-dialog-body');
        const main = dialog?.querySelector('.tv-midi-body > .tv-dialog-client > .tv-group');
        const advanced = dialog?.querySelector('.tv-input-line')?.closest('.tv-group');
        const urlInput = advanced?.querySelector('.tv-input-line');
        const rect = (element) => {
            const value = element?.getBoundingClientRect();
            return value ? { x: value.x, y: value.y, width: value.width, height: value.height, bottom: value.bottom, right: value.right } : null;
        };
        return {
            advancedVisible: !advanced?.hidden,
            moreExpanded: dialog?.querySelector('[data-tv-midi-more]')?.getAttribute('aria-expanded') === 'true',
            height: dialog?.getBoundingClientRect().height || 0,
            sideGlyphs: side?.textContent.split('\\n').length || 0,
            dialogRect: rect(dialog),
            bodyRect: rect(body),
            mainRect: rect(main),
                advancedRect: rect(advanced),
                urlRect: rect(urlInput),
            advancedClipped: Array.from(advanced?.children || []).filter((element) =>
                !element.hidden && !element.matches('[data-tv-midi-filter-history-popup]')).some((element) => {
                    const child = element.getBoundingClientRect();
                    const parent = advanced.getBoundingClientRect();
                    return child.left < parent.left - 0.5 || child.top < parent.top - 0.5
                        || child.right > parent.right + 0.5 || child.bottom > parent.bottom + 0.5;
                }),
            sideRects: Array.from(body?.querySelectorAll(':scope > .tv-border-side') || []).map(rect),
            bodyClient: body ? { width: body.clientWidth, height: body.clientHeight, scrollWidth: body.scrollWidth, scrollHeight: body.scrollHeight } : null,
        };
    })()`);
    if (
        !midiExpanded.advancedVisible || !midiExpanded.moreExpanded
        || midiExpanded.height <= midiCompact.height
        || midiExpanded.sideGlyphs <= midiCompact.sideGlyphs
        || midiExpanded.sideRects.length !== 2
        || Math.abs(midiExpanded.sideRects[0].x - midiExpanded.bodyRect.x) > 1
        || Math.abs(midiExpanded.sideRects[1].right - midiExpanded.bodyRect.right) > 1
        || Math.abs(midiExpanded.mainRect.x - midiExpanded.sideRects[0].right) > 1
        || Math.abs(midiExpanded.mainRect.y - midiExpanded.bodyRect.y) > 1
        || Math.abs(midiExpanded.mainRect.bottom - midiExpanded.bodyRect.bottom) > 1
            || midiExpanded.advancedRect.y < midiExpanded.mainRect.y
            || midiExpanded.advancedRect.bottom > midiExpanded.mainRect.bottom + 1
            || Math.abs((midiExpanded.urlRect.y - midiExpanded.advancedRect.y)
                - midiExpanded.urlRect.height) > 1
            || midiExpanded.advancedClipped
        || midiExpanded.bodyClient.scrollWidth !== midiExpanded.bodyClient.width
        || midiExpanded.bodyClient.scrollHeight !== midiExpanded.bodyClient.height
    ) {
        throw new Error(`MIDI expanded frame was not redrawn: ${JSON.stringify({ midiCompact, midiExpanded })}`);
    }
    const midiHistory = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'CD/MIDI Player');
        const player = dialog.closest('.tv-dialog-overlay')._tvView;
        player.filterInput.setData('Doom');
        player.rememberFilter();
        player.filterInput.setData('');
        player.filterHistory.root.click();
        const popup = player.historyWindow.root;
        const popupRect = popup.getBoundingClientRect();
        const inputRect = player.filterInput.root.getBoundingClientRect();
        const dialogRect = dialog.getBoundingClientRect();
        const opened = player.historyWindow.isOpen()
            && popup.textContent.includes('Doom')
            && popupRect.top >= dialogRect.top && popupRect.bottom <= inputRect.top + 1
            && popupRect.left >= dialogRect.left && popupRect.right <= dialogRect.right;
        player.historyWindow.onSelect({ value: 'Doom' }, false);
        const selected = player.filterInput.getData() === 'Doom';
        const closed = !player.historyWindow.isOpen();
        player.filterInput.setData('');
        player.applyFilter();
        return { opened, selected, closed };
    })()`);
    if (!midiHistory.opened || !midiHistory.selected || !midiHistory.closed) {
        throw new Error(`MIDI filter history failed: ${JSON.stringify(midiHistory)}`);
    }
    const midiCatalogControls = await evaluate(`(async () => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'CD/MIDI Player'
        );
        const player = dialog.closest('.tv-dialog-overlay')._tvView;
        while (player.catalogPending) { await new Promise((resolve) => setTimeout(resolve, 25)); }
        if (player.catalogTimer) { clearTimeout(player.catalogTimer); player.catalogTimer = null; }
        const fetchBeforeRetry = window.fetch;
        const timeoutBeforeRetry = window.setTimeout;
        let catalogAttempts = 0;
        let catalogRetryScheduled = false;
        window.setTimeout = (callback, delay, ...args) => {
            if (delay === 3000) {
                catalogRetryScheduled = true;
                return timeoutBeforeRetry(callback, 20, ...args);
            }
            return timeoutBeforeRetry(callback, delay, ...args);
        };
        window.fetch = async (url, options) => {
            if (String(url) === '/api/midi/catalog') {
                catalogAttempts += 1;
                return catalogAttempts === 1 ? new Response('', { status: 500 })
                    : new Response(JSON.stringify({ state: 'ready', downloaded: player.allTracks.length,
                        total: player.allTracks.length, tracks: player.allTracks }),
                        { status: 200, headers: { 'Content-Type': 'application/json' } });
            }
            return fetchBeforeRetry(url, options);
        };
        try {
            await player.refreshCatalog();
            await new Promise((resolve) => timeoutBeforeRetry(resolve, 100));
        } finally {
            window.fetch = fetchBeforeRetry;
            window.setTimeout = timeoutBeforeRetry;
        }
        const catalogRecovered = catalogRetryScheduled && catalogAttempts === 2
            && !player.catalogPending && !player.catalogTimer
            && !player.displayView.root.textContent.includes('MIDI catalog unavailable');
        const playbackEvents = [];
        const playbackEventHandler = player.onPlaybackEvent;
        player.onPlaybackEvent = (event) => playbackEvents.push(event);
        player.playbackStats = { track: { id: 'aaaaaaaaaaaaaaaa', source_id: 'karlsitretro-dos-d',
            game: 'Doom', title: 'At Doom Gate' }, durationMs: 60_000,
            activeSince: performance.now() - 30_000 };
        player.pausePlaybackStats();
        const pausedStatsTime = player.playbackStats.durationMs;
        player.playbackStats.activeSince = performance.now() - 10_000;
        player.finishPlaybackStats();
        player.onPlaybackEvent = playbackEventHandler;
        const playbackStatistics = playbackEvents.length === 1
            && playbackEvents[0].event === 'midi_play'
            && playbackEvents[0].duration_ms >= 99_000
            && playbackEvents[0].duration_ms < 102_000
            && pausedStatsTime >= 89_000 && pausedStatsTime < 91_000;
        const soundFont = await player.synth.constructor.loadAssets();
        const soundFontLoaded = soundFont.byteLength > 1000000 && Boolean(window.JSSynth?.Synthesizer);
        // A self-contained 32-second SMF fixture: no production demo library/network dependency.
        const fixtureFile = 'data:audio/midi;base64,' + btoa(String.fromCharCode(...[
            77,84,104,100,0,0,0,6,0,0,0,1,0,96,
            77,84,114,107,0,0,0,23,
            0,255,81,3,7,161,32,0,192,0,0,144,60,100,
            176,0,128,60,0,0,255,47,0,
        ]));
        const fixtureSequence = await player.loadTrack({ file: fixtureFile });
        const audioStarted = await player.synth.play(fixtureSequence,
            (elapsed, duration) => player.updateProgress(elapsed, duration), () => {});
        const loadTiming = player.synth.loadingTimes;
        const soundFontTimingRecorded = loadTiming.soundfontBytes === soundFont.byteLength
            && loadTiming.scriptsMs > 0 && loadTiming.soundfontFetchMs > 0
            && loadTiming.synthInitMs > 0 && loadTiming.soundfontLoadMs > 0;
        const progressStart = Number(player.meter.root?.getAttribute('aria-valuenow'));
        await new Promise((resolve) => setTimeout(resolve, 1600));
        const soundFontPlaying = audioStarted && player.synth.synth.getPlayerCurrentTick() > 0;
        const liveProgress = Number(player.meter.root?.getAttribute('aria-valuenow'));
        const progressRendered = liveProgress > progressStart && liveProgress < 100
            && player.synth.totalTicks === fixtureSequence.maxTick
            && player.meter.root?.textContent.includes('█');
        const progressTicks = [player.synth.synth.getPlayerCurrentTick(), player.synth.totalTicks];
        await player.synth.seekTo(0.5);
        await new Promise((resolve) => setTimeout(resolve, 200));
        const soundFontSeeked = player.synth.synth.getPlayerCurrentTick() >= player.synth.totalTicks * 0.45;
        const fixtureTrack = { id: 'fixture', item_id: 'fixture', source_id: 'local',
            title: 'Fixture track', game: 'THelpViewer', credit: 'Test fixture', sequencer: '',
            available: true, file: fixtureFile, cover: '' };
        player.allTracks = [fixtureTrack];
        player.applyFilter();
        player.activeTrackFile = fixtureTrack.file;
        player.isPlaying = true;
        player.pausePlayback();
        const pausedPosition = player.pausedPosition;
        const pauseHeld = pausedPosition?.ratio > 0.4
            && Number(player.meter.root?.getAttribute('aria-valuenow')) > 40
            && player.displayView.timeView.root?.textContent !== '0:00 / 0:00';
        await player.playSelected();
        await new Promise((resolve) => setTimeout(resolve, 250));
        const resumeTicks = [player.synth.synth.getPlayerCurrentTick(), player.synth.totalTicks];
        const resumedFromPause = player.isPlaying && !player.pausedPosition
            && player.synth.synth.getPlayerCurrentTick() >= player.synth.totalTicks * 0.4;
        player.stopPlayback();
        player.allTracks = Array.from({ length: 40 }, (_, index) => ({
            ...fixtureTrack, id: 'fixture-' + index, title: 'Fixture track ' + index,
        }));
        player.applyFilter();
        const midiTrack = player.trackListBox.root.querySelector('.tv-scrollbar-y .tv-scroll-track');
        const midiTrackRect = midiTrack.getBoundingClientRect();
        midiTrack.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true, clientX: midiTrackRect.left + midiTrackRect.width / 2,
            clientY: midiTrackRect.top + midiTrackRect.height * 0.7,
        }));
        const midiTrackScrollbarClicks = player.trackListBox.viewport.scrollTop > 0;
        player.trackListBox.select(20);
        const selectionObserver = new MutationObserver(() => {});
        selectionObserver.observe(player.trackListBox.viewport, {
            subtree: true, attributes: true,
            attributeFilter: ['role', 'class', 'aria-selected', 'tabindex'],
        });
        player.trackListBox.select(21);
        const selectionMutations = selectionObserver.takeRecords().length;
        selectionObserver.disconnect();
        const incrementalSelection = selectionMutations <= 12
            && player.trackListBox.selectedElement()?.getAttribute('aria-selected') === 'true'
            && player.trackListBox.viewport.querySelector('[data-tv-list-index="20"]')?.getAttribute('aria-selected') === 'false';
        const pointerRows = Array.from(player.trackListBox.viewport.querySelectorAll('[data-tv-list-index]'));
        const targetRow = pointerRows[30];
        targetRow.scrollIntoView({ block: 'nearest' });
        const targetRect = targetRow.getBoundingClientRect();
        let rowRectReads = 0;
        const originalRowRects = pointerRows.map((row) => row.getBoundingClientRect);
        pointerRows.forEach((row, index) => {
            row.getBoundingClientRect = function () {
                rowRectReads += 1;
                return originalRowRects[index].call(this);
            };
        });
        const playTrackBeforePointerTest = player.playTrack;
        player.playTrack = async () => {};
        targetRow.querySelector('.tv-midi-track-title').dispatchEvent(new MouseEvent('click', {
            bubbles: true, clientX: targetRect.left + 8, clientY: targetRect.top + targetRect.height / 2,
        }));
        player.playTrack = playTrackBeforePointerTest;
        pointerRows.forEach((row, index) => { row.getBoundingClientRect = originalRowRects[index]; });
        const directPointerHit = player.selectedIndex === 30 && rowRectReads <= 2;
        const liveTracks = (await (await fetch('/api/midi/catalog')).json()).tracks || [];
        player.allTracks = liveTracks;
        player.applyFilter();
        let highIndexPlaying = true;
        if (liveTracks.length > 1000 && liveTracks[1000].available) {
            player.trackListBox.scrollViewport.querySelector('[data-tv-list-index="1000"]')?.click();
            const highIndexSelected = player.selectedIndex === 1000;
            await player.playSelected();
            await new Promise((resolve) => setTimeout(resolve, 400));
            highIndexPlaying = highIndexSelected && player.selectedIndex === 1000 && player.isPlaying
                && player.synth.synth.getPlayerCurrentTick() > 0;
            player.stopPlayback();
        }
        player.allTracks = [
            { id: '1111111111111111', item_id: '1111111111111111', source_id: 'direct',
              title: 'E1M1', game: 'Doom', credit: 'Doom', sequencer: '', available: false, file: '', cover: '' },
            { id: '2222222222222222', item_id: '2222222222222222', source_id: 'direct',
              title: 'Desert', game: 'Dune', credit: 'Dune', sequencer: '', available: true,
              file: '/api/midi/files/direct/dune.mid', cover: '' },
        ];
        player.applyFilter();
        const rows = Array.from(dialog.querySelectorAll('.tv-midi-track'));
        const gameStartsAligned = rows.length === 2
            && Math.abs(rows[0].querySelector('.tv-midi-track-credit').getBoundingClientRect().x
                - rows[1].querySelector('.tv-midi-track-credit').getBoundingClientRect().x) < 1;
        const cloud = rows[0]?.querySelector('.tv-midi-track-availability')?.textContent === '☁';
        const cloudAtEnd = rows[0]?.lastElementChild?.classList.contains('tv-midi-track-availability');
        const originalPlayTrack = player.playTrack;
        const originalPrioritizeTrack = player.prioritizeTrack;
        let clickedTrackId = '';
        let pendingStoppedOldTrack = false;
        player.playTrack = async (track) => { clickedTrackId = track.id; };
        player.prioritizeTrack = async (track) => {
            pendingStoppedOldTrack = track.id === '1111111111111111'
                && !player.isPlaying && player.activeTrackFile === null;
        };
        rows[1].click();
        const clickStartsTrack = player.selectedIndex === 1
            && clickedTrackId === '2222222222222222';
        rows[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
        const arrowOnlySelects = player.selectedIndex === 0
            && clickedTrackId === '2222222222222222';
        player.activeTrackFile = fixtureFile;
        player.isPlaying = true;
        rows[0].click();
        player.playTrack = originalPlayTrack;
        player.prioritizeTrack = originalPrioritizeTrack;
        player.selectTrack(1);
        player.tracks[1].cover = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg"/%3E';
        player.updateDisplay();
        const cover = dialog.querySelector('.tv-image img');
        const coverVisible = Boolean(cover && !cover.hidden && cover.getAttribute('src') === player.tracks[1].cover);
        player.selectTrack(0);
        const meter = dialog.querySelector('[data-tv-bar-gauge]');
        const meterBounds = meter.getBoundingClientRect();
        const seekTicks = [];
        const fakeSynth = {
            resetPlayer: async () => {}, addSMFDataToPlayer: async () => {}, playPlayer: async () => {},
            getPlayerTotalTicks: () => 0, getPlayerCurrentTick: () => 100,
            isPlayerPlaying: () => true, seekPlayer: (tick) => seekTicks.push(tick), stopPlayer: () => {},
        };
        player.synth.synth = fakeSynth;
        player.synth.ensureContext = async () => fakeSynth;
        await player.synth.play({ duration: 100, maxTick: 1200, data: new ArrayBuffer(4) }, () => {}, () => {}, 50);
        const seeksFromOffset = seekTicks[0] === 600;
        player.synth.stop(false);
        let seekRatio = -1;
        player.synth.sequence = { duration: 100, notes: [] };
        player.synth.seekTo = async (ratio) => { seekRatio = ratio; };
        meter.dispatchEvent(new MouseEvent('click', {
            bubbles: true, clientX: meterBounds.left + meterBounds.width * 0.75,
        }));
        await new Promise((resolve) => setTimeout(resolve, 0));
        player.synth.sequence = null;
        const seeksToClick = Math.abs(seekRatio - 0.75) < 0.02;
        player.filterInput.root.value = 'doom';
        player.filterInput.root.dispatchEvent(new Event('input', { bubbles: true }));
        const filtered = player.tracks.length === 1 && player.tracks[0].game === 'Doom';
        const originalFetch = window.fetch;
        let priorityUrl = '';
        window.fetch = async (url, options) => {
            if (String(url).startsWith('/api/midi/priority/')) {
                priorityUrl = String(url);
                return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
            }
            return originalFetch(url, options);
        };
        try { await player.playSelected(); } finally { window.fetch = originalFetch; }
        if (player.catalogTimer) { clearTimeout(player.catalogTimer); player.catalogTimer = null; }
        let resumedId = '';
        player.playTrack = async (track) => { resumedId = track.id; };
        window.fetch = async (url, options) => {
            if (String(url) === '/api/midi/catalog') {
                return new Response(JSON.stringify({ state: 'ready', downloaded: 2, total: 2,
                    tracks: player.allTracks.map((track) => track.id === '1111111111111111'
                        ? { ...track, available: true, file: '/api/midi/files/direct/doom.mid' } : track),
                }), { status: 200, headers: { 'Content-Type': 'application/json' } });
            }
            return originalFetch(url, options);
        };
        try { await player.refreshCatalog(); } finally { window.fetch = originalFetch; }
        const advancedWidth = player.advancedView.root.getBoundingClientRect().width;
        const randomFullWidth = Math.abs(player.randomNext.root.getBoundingClientRect().width - advancedWidth) < 1;
        const downloadButtonRemoved = !player.downloadsButton
            && !player.advancedView.root.textContent.includes('Downloads');
        const menuView = document.querySelector('[data-tv-menu-bar]')._tvMenuView;
        const download = menuView.downloadItem;
        const previousStatus = download.status;
        const status = { active: true, errors: 0, percent: 50,
            items: [{ id: 'midi:test', kind: 'midi', label: 'Doom', state: 'running', percent: 50 }] };
        download.update(status, menuView);
        const noAutomaticDownloadDialog = !download.dialog?.isOpen();
        const progress = download.showDialog(player.owner);
        const downloadOpensFromMenu = progress.isOpen();
        const progressVisible = progress.isOpen()
            && progress.root.querySelector('[data-tv-bar-gauge]')?.textContent.includes('█');
        progress.hideProgress();
        const hiddenWithoutStopping = !progress.isOpen() && download.status.active;
        download.update({ ...status, percent: 75 }, menuView);
        const staysHiddenAfterHide = !progress.isOpen();
        download.update(previousStatus, menuView);
        player.filterInput.root.value = '';
        player.filterInput.root.dispatchEvent(new Event('input', { bubbles: true }));
        player.allTracks.push({ id: '3333333333333333', item_id: '3333333333333333',
            source_id: 'direct', title: 'Quake', game: 'Quake', credit: 'Quake', sequencer: '',
            available: true, file: '/api/midi/files/direct/quake.mid', cover: '' });
        player.applyFilter();
        const queued = [];
        player.playTrack = async (track) => { queued.push(track.id); };
        player.selectTrack(0);
        player.randomNext.setData(0);
        player.nextTrack(true);
        const sequentialNext = player.selectedIndex === 1 && queued.at(-1) === '2222222222222222';
        player.selectTrack(0);
        player.randomNext.setData(1);
        const originalRandom = Math.random;
        Math.random = () => 0.99;
        try { player.nextTrack(true); } finally { Math.random = originalRandom; }
        const randomNext = player.selectedIndex === 2 && queued.at(-1) === '3333333333333333'
            && player.randomNext.root?.querySelector('input')?.checked;
        player.selectTrack(0);
        player.randomNext.setData(0);
        player.loadTrack = async () => ({ duration: 10, data: new ArrayBuffer(4) });
        player.synth.play = async (_sequence, _onProgress, onDone) => {
            setTimeout(onDone, 0);
            return true;
        };
        await Object.getPrototypeOf(player).playTrack.call(player, player.tracks[0], '01');
        await new Promise((resolve) => setTimeout(resolve, 20));
        const automaticNext = player.selectedIndex === 1 && queued.at(-1) === '2222222222222222';
        return { catalogRecovered, playbackStatistics, soundFontLoaded, soundFontTimingRecorded,
            soundFontPlaying,
            progressRendered, liveProgress, progressTicks,
            pauseHeld, resumedFromPause, resumeTicks, pausedPosition,
            soundFontSeeked, highIndexPlaying, midiTrackScrollbarClicks,
            incrementalSelection, directPointerHit,
            gameStartsAligned, cloud, cloudAtEnd, clickStartsTrack, arrowOnlySelects,
            pendingStoppedOldTrack,
            coverVisible, seeksToClick, seeksFromOffset,
            filtered, priorityUrl, resumedId, sequentialNext, randomNext, automaticNext,
            downloadButtonRemoved, randomFullWidth, noAutomaticDownloadDialog, downloadOpensFromMenu,
            hiddenWithoutStopping, staysHiddenAfterHide, progressVisible };
    })()`, true);
    if (!midiCatalogControls.catalogRecovered || !midiCatalogControls.playbackStatistics
        || !midiCatalogControls.soundFontLoaded || !midiCatalogControls.soundFontTimingRecorded
        || !midiCatalogControls.soundFontPlaying
        || !midiCatalogControls.progressRendered
        || !midiCatalogControls.pauseHeld || !midiCatalogControls.resumedFromPause
        || !midiCatalogControls.soundFontSeeked
        || !midiCatalogControls.highIndexPlaying
        || !midiCatalogControls.midiTrackScrollbarClicks
        || !midiCatalogControls.incrementalSelection
        || !midiCatalogControls.directPointerHit
        || !midiCatalogControls.gameStartsAligned || !midiCatalogControls.cloud
        || !midiCatalogControls.cloudAtEnd || !midiCatalogControls.clickStartsTrack
        || !midiCatalogControls.arrowOnlySelects || !midiCatalogControls.pendingStoppedOldTrack
        || !midiCatalogControls.coverVisible
        || !midiCatalogControls.seeksToClick || !midiCatalogControls.seeksFromOffset
        || !midiCatalogControls.filtered
        || midiCatalogControls.priorityUrl !== '/api/midi/priority/direct/1111111111111111'
        || midiCatalogControls.resumedId !== '1111111111111111'
        || !midiCatalogControls.sequentialNext || !midiCatalogControls.randomNext
        || !midiCatalogControls.automaticNext
        || !midiCatalogControls.downloadButtonRemoved || !midiCatalogControls.randomFullWidth
        || !midiCatalogControls.noAutomaticDownloadDialog || !midiCatalogControls.downloadOpensFromMenu
        || !midiCatalogControls.hiddenWithoutStopping
        || !midiCatalogControls.staysHiddenAfterHide
        || !midiCatalogControls.progressVisible) {
        throw new Error(`MIDI catalog controls failed: ${JSON.stringify(midiCatalogControls)}`);
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

    await evaluate(`__tvMenuItem('dialog-open', 'Statistics').click()`);
    const statisticsDialog = await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const dialog = document.querySelector('.tv-statistics-window');
            const overlay = dialog?.closest('.tv-dialog-overlay');
            const text = Array.from(dialog?.querySelectorAll('.tv-static-text') || [])
                .map((element) => element.textContent).join('\\n');
            if (dialog && overlay && !overlay.hidden && text.includes('Visits ')) {
                resolve({
                    text,
                    lists: dialog.querySelectorAll('.tv-vlist-viewer').length,
                    ok: Boolean(dialog.querySelector('[data-tv-command="statistics-ok"]')),
                    refresh: Boolean(dialog.querySelector('[data-tv-command="statistics-refresh"]')),
                    modal: overlay.classList.contains('is-modal'),
                    palette: dialog.getAttribute('data-tv-palette'),
                    windowBackground: getComputedStyle(dialog.querySelector('.tv-dialog-body')).backgroundColor,
                    listBackground: getComputedStyle(dialog.querySelector('.tv-vlist-viewer')).backgroundColor,
                });
                return;
            }
            if (Date.now() >= deadline) { reject(new Error('Statistics dialog did not load')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    if (!statisticsDialog.ok || !statisticsDialog.refresh || statisticsDialog.modal || statisticsDialog.lists !== 2
        || statisticsDialog.palette !== 'dialog'
        || statisticsDialog.windowBackground !== 'rgb(170, 170, 170)'
        || statisticsDialog.listBackground !== 'rgb(0, 170, 170)'
        || !statisticsDialog.text.includes('no IP')) {
        throw new Error(`Statistics dialog is incomplete: ${JSON.stringify(statisticsDialog)}`);
    }
    const statisticsHorizontalScroll = await evaluate(`(() => {
        const details = document.querySelectorAll('.tv-statistics-window .tv-vlist-viewer')[1]?._tvListViewer;
        details?.newList(['A topic title much wider than this list viewport '.repeat(3)]);
        const viewport = details?.viewport;
        const scrollbar = details?.root?.querySelector('.tv-scrollbar-x');
        const overflow = viewport?.scrollWidth > viewport?.clientWidth;
        scrollbar?.querySelector('.tv-scroll-arrow-forward')?.dispatchEvent(
            new MouseEvent('mousedown', { bubbles: true }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        const position = viewport?.scrollLeft || 0;
        details?.newList(['Short topic']);
        return {
            overflow,
            position,
            visible: details?.root?.classList.contains('is-h-scrollable'),
        };
    })()`);
    if (!statisticsHorizontalScroll.overflow || statisticsHorizontalScroll.position <= 0
        || statisticsHorizontalScroll.visible) {
        throw new Error(`Statistics list horizontal scrollbar failed: ${JSON.stringify(statisticsHorizontalScroll)}`);
    }
    await evaluate(`(() => {
        window.__statisticsFetch = window.fetch;
        window.__statisticsFetches = 0;
        window.fetch = (url, options) => {
            if (String(url) === '/api/statistics/summary' && ++window.__statisticsFetches === 1) {
                return Promise.resolve(new Response('Temporary failure', { status: 503 }));
            }
            return window.__statisticsFetch(url, options);
        };
        document.querySelector('.tv-statistics-window [data-tv-command="statistics-refresh"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const text = document.querySelector('.tv-statistics-window')?.textContent || '';
            if (window.__statisticsFetches === 2 && text.includes('Visits ')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Statistics did not retry transient HTTP 503')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        window.fetch = (url, options) => String(url) === '/api/statistics/summary'
            ? Promise.resolve(new Response('Unavailable', { status: 503 }))
            : window.__statisticsFetch(url, options);
        document.querySelector('.tv-statistics-window [data-tv-command="statistics-refresh"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const text = document.querySelector('.tv-statistics-window')?.textContent || '';
            if (text.includes('Server API unavailable: HTTP 503') && text.includes('Press Refresh to retry.')) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Statistics hid the HTTP error cause')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        window.fetch = window.__statisticsFetch;
        document.querySelector('.tv-statistics-window [data-tv-command="statistics-refresh"]').click();
    })()`);
    await pause();
    const statisticsRefreshed = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-statistics-window');
        return Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden
            && Array.from(dialog.querySelectorAll('.tv-static-text')).some((item) => item.textContent.includes('Visits ')));
    })()`);
    if (!statisticsRefreshed) { throw new Error('Statistics Refresh closed or emptied the dialog'); }
    await evaluate(`document.querySelector('.tv-statistics-window [data-tv-command="statistics-ok"]').click()`);
    const statisticsClosed = await evaluate(`document.querySelector('.tv-statistics-overlay').hidden`);
    if (!statisticsClosed) { throw new Error('Statistics OK did not close the dialog'); }

    await evaluate(`__tvMenuItem('dialog-open', 'Mastermind').click()`);
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
            height: dialog?.style.getPropertyValue('--tv-dialog-height'),
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
        || mastermind.hall !== '[H]' || mastermind.columns < 54 || mastermind.columns > 58
        || mastermind.height !== '18em'
        || mastermind.boardInset <= 0 || mastermind.clipped) {
        throw new Error(`Mastermind dialog is incomplete: ${JSON.stringify(mastermind)}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Calendar').click()`);
    await pause();
    const calendarToday = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-calendar-window');
        const today = dialog?.querySelector('[data-tv-command="calendar-today"]');
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            plain: Boolean(today?.classList.contains('tv-calendar-arrow')
                && !today.classList.contains('tv-dialog-button')),
            height: today?.getBoundingClientRect().height || 0,
            rowHeight: parseFloat(getComputedStyle(dialog).lineHeight) || 0,
        };
    })()`);
    if (!calendarToday.open || !calendarToday.plain
        || calendarToday.height > calendarToday.rowHeight + 1) {
        throw new Error(`Calendar Today control occupies more than one row: ${JSON.stringify(calendarToday)}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Sokoban').click()`);
    await pause();
    for (const arrow of ['ArrowUp', 'ArrowDown', 'ArrowRight']) {
        await key(arrow, arrow, 0, true);
    }
    const sokobanSolved = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-sokoban-window');
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            level: dialog?.querySelector('.tv-info-box')?.textContent.includes('Level: 1/10'),
            solved: Boolean(dialog?.querySelector('.tv-sokoban-overlay-msg')),
            namePrompt: Array.from(document.querySelectorAll('.tv-best-window')).some((item) =>
                !item.closest('.tv-dialog-overlay').hidden),
        };
    })()`);
    if (!sokobanSolved.open || !sokobanSolved.level || !sokobanSolved.solved || sokobanSolved.namePrompt) {
        throw new Error(`Sokoban ended instead of offering the next level: ${JSON.stringify(sokobanSolved)}`);
    }
    await key('Enter', 'Enter', 0, true);
    const sokobanNext = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-sokoban-window');
        return {
            level: dialog?.querySelector('.tv-info-box')?.textContent.includes('Level: 2/10'),
            solved: Boolean(dialog?.querySelector('.tv-sokoban-overlay-msg')),
        };
    })()`);
    if (!sokobanNext.level || sokobanNext.solved) {
        throw new Error(`Sokoban did not advance to level 2: ${JSON.stringify(sokobanNext)}`);
    }
    const sokobanPaths = [
        'UUDDRRRRUULDRDL',
        'URURDRDDLLULLLUU',
        'UULLDDUURRDDLRR',
        'RRRUUULLLRDRRDDLLUUDDLLLUURR',
        'LLUUDRRDRUURDD',
        'LLUUDDDURRRRDUUU',
        'LLUUDDDRRRURUURUL',
        'LUUUDRRRRDLLDRRURU',
        'DLDRRUURRUULDDLLLLUUDRRRDRUU',
    ];
    const sokobanCampaignMoves = 3 + sokobanPaths.reduce((total, path) => total + path.length, 0);
    for (let index = 0; index < sokobanPaths.length; index++) {
        for (const move of sokobanPaths[index]) {
            const arrow = { U: 'ArrowUp', D: 'ArrowDown', L: 'ArrowLeft', R: 'ArrowRight' }[move];
            await key(arrow, arrow, 0, true);
        }
        const level = index + 2;
        const result = await evaluate(`(() => {
            const dialog = document.querySelector('.tv-sokoban-window');
            const prompt = Array.from(document.querySelectorAll('.tv-best-window')).find((item) =>
                !item.closest('.tv-dialog-overlay').hidden);
            return {
                level: dialog?.querySelector('.tv-info-box')?.textContent.includes('Level: ${level}/10'),
                solved: Boolean(dialog?.querySelector('.tv-sokoban-overlay-msg')),
                prompt: Boolean(prompt),
                score: prompt?.textContent.includes('Moves, level 10: ${sokobanCampaignMoves}') || false,
            };
        })()`);
        if (!result.level || !result.solved || result.prompt !== (level === 10)
            || (level === 10 && !result.score)) {
            throw new Error(`Sokoban level ${level} failed: ${JSON.stringify(result)}`);
        }
        if (level < 10) { await key('Enter', 'Enter', 0, true); }
    }
    await evaluate(`document.querySelector('.tv-best-window [data-tv-command="best-ok"]')?.click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = async () => {
            const payload = await fetch('/api/hall-of-fame/sokoban').then((response) => response.json());
            if (payload.entries?.some((entry) => entry.score === ${sokobanCampaignMoves} && entry.level === 10)) {
                resolve(true);
            } else if (Date.now() >= deadline) {
                reject(new Error('Sokoban campaign score was not saved'));
            } else {
                setTimeout(check, 50);
            }
        };
        check();
    })`, true);
    await key('Enter', 'Enter', 0, true);
    const sokobanRestarted = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-sokoban-window');
        return {
            first: dialog?.querySelector('.tv-info-box')?.textContent.includes('Level: 1/10'),
            solved: Boolean(dialog?.querySelector('.tv-sokoban-overlay-msg')),
        };
    })()`);
    if (!sokobanRestarted.first || sokobanRestarted.solved) {
        throw new Error(`Sokoban did not restart after the final level: ${JSON.stringify(sokobanRestarted)}`);
    }
    for (let level = 1; level < 10; level++) {
        await evaluate(`document.querySelector('.tv-sokoban-window [data-tv-command="sokoban-next"]')?.click()`);
    }
    for (const move of sokobanPaths[8]) {
        const arrow = { U: 'ArrowUp', D: 'ArrowDown', L: 'ArrowLeft', R: 'ArrowRight' }[move];
        await key(arrow, arrow, 0, true);
    }
    const skippedSokobanScore = await evaluate(`Array.from(document.querySelectorAll('.tv-best-window'))
        .some((item) => !item.closest('.tv-dialog-overlay').hidden)`);
    if (skippedSokobanScore) {
        throw new Error('Skipping nine Sokoban levels incorrectly qualified for the campaign Hall of Fame');
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Sokoban').click()`);
    await key('ArrowUp', 'ArrowUp', 0, true);
    await key('Escape', 'Escape', 0, true);
    const partialSokobanPrompt = await evaluate(`(() => {
        const prompt = Array.from(document.querySelectorAll('.tv-best-window')).find((item) =>
            !item.closest('.tv-dialog-overlay').hidden);
        return prompt?.textContent.includes('Moves, level 1: 1') || false;
    })()`);
    if (!partialSokobanPrompt) {
        throw new Error('Leaving Sokoban at level 1 did not offer a level-aware Hall of Fame entry');
    }
    await evaluate(`document.querySelector('.tv-best-window [data-tv-command="best-ok"]')?.click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = async () => {
            const payload = await fetch('/api/hall-of-fame/sokoban').then((response) => response.json());
            if (payload.entries?.some((entry) => entry.score === 1 && entry.level === 1)) {
                resolve(true);
            } else if (Date.now() >= deadline) {
                reject(new Error('Partial Sokoban result was not saved with its reached level'));
            } else {
                setTimeout(check, 50);
            }
        };
        check();
    })`, true);
    await evaluate(`__tvMenuItem('dialog-open', 'Sokoban').click()`);
    await evaluate(`document.querySelector('.tv-sokoban-window .tv-game-hall-control')?.click()`);
    await pause();
    const sokobanHall = await evaluate(`(() => {
        const dialog = Array.from(document.querySelectorAll('.tv-dialog-window')).find((item) =>
            item.querySelector('.tv-dialog-title-text')?.textContent === 'Sokoban Hall of Fame');
        return dialog?.textContent || '';
    })()`);
    if (!sokobanHall.includes('Score / Level') || !sokobanHall.includes('170 moves Lv.10')
        || !sokobanHall.includes('1 moves Lv.1')) {
        throw new Error(`Sokoban Hall of Fame omitted the reached level: ${sokobanHall}`);
    }
    await key('Escape', 'Escape', 0, true);
    await key('Escape', 'Escape', 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Tetris').click()`);
    await pause();
    const tetrisGeometry = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-tetris-window');
        const group = dialog?.querySelector('.tv-dialog-client > .tv-group');
        const field = dialog?.querySelector('[data-tv-tetris-grid]');
        const body = dialog?.querySelector('.tv-dialog-body');
        const info = dialog?.querySelector('.tv-info-box');
        const preview = dialog?.querySelector('[data-tv-tetris-preview]');
        const infoTop = info?.querySelector('[data-tv-info-frame="top"]');
        const infoBottom = info?.querySelector('[data-tv-info-frame="bottom"]');
        const hall = dialog?.querySelector('.tv-game-hall-control');
        const groupRect = group?.getBoundingClientRect();
        const fieldRect = field?.getBoundingClientRect();
        const infoRect = info?.getBoundingClientRect();
        const previewRect = preview?.getBoundingClientRect();
        const infoTopRect = infoTop?.getBoundingClientRect();
        const infoBottomRect = infoBottom?.getBoundingClientRect();
        const cellWidth = fieldRect ? fieldRect.width / 24 : 0;
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            columns: dialog && cellWidth ? Math.round(dialog.getBoundingClientRect().width / cellWidth) : 0,
            fieldInset: fieldRect && groupRect && cellWidth ? {
                x: Math.round((fieldRect.left - groupRect.left) / cellWidth),
                y: Math.round((fieldRect.top - groupRect.top) / (fieldRect.height / 18)),
            } : null,
            clipped: !group || group.scrollWidth > group.clientWidth || group.scrollHeight > group.clientHeight,
            infoFlow: Boolean(info && !info.classList.contains('is-bounded')),
            infoRows: info?.querySelectorAll('.tv-info-row').length || 0,
            infoClipped: Boolean(info && (info.scrollWidth > info.clientWidth || info.scrollHeight > info.clientHeight)),
            infoAligned: Boolean(infoRect && previewRect && infoTopRect && infoBottomRect
                && Math.abs(previewRect.width - infoRect.width) < 1
                && Math.abs(infoTopRect.width - infoRect.width) < 1
                && Math.abs(infoBottomRect.width - infoRect.width) < 1
                && Math.abs(infoBottomRect.bottom - infoRect.bottom) < 1),
            hall: hall?.textContent,
            bodyBackground: body ? getComputedStyle(body).backgroundColor : '',
            fieldBackground: field ? getComputedStyle(field).backgroundColor : '',
        };
    })()`);
    if (!tetrisGeometry.open || tetrisGeometry.columns < 53 || tetrisGeometry.columns > 55
        || tetrisGeometry.fieldInset?.x !== 2 || tetrisGeometry.fieldInset?.y !== 2
        || tetrisGeometry.clipped || !tetrisGeometry.infoFlow || tetrisGeometry.infoRows !== 5
        || tetrisGeometry.infoClipped || !tetrisGeometry.infoAligned || tetrisGeometry.hall !== '[H]'
        || tetrisGeometry.bodyBackground === 'rgb(0, 0, 0)'
        || tetrisGeometry.fieldBackground !== 'rgb(0, 0, 0)') {
        throw new Error(`Tetris geometry differs from DOS Navigator: ${JSON.stringify(tetrisGeometry)}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Snake').click()`);
    await pause();
    const snakePalette = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-snake-window');
        const body = dialog?.querySelector('.tv-dialog-body');
        const field = dialog?.querySelector('[data-tv-snake-field]');
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay').hidden),
            body: body ? getComputedStyle(body).backgroundColor : '',
            field: field ? getComputedStyle(field).backgroundColor : '',
        };
    })()`);
    if (!snakePalette.open || snakePalette.body === 'rgb(0, 0, 0)'
        || snakePalette.field !== 'rgb(0, 0, 0)') {
        throw new Error(`Snake palette leaked outside its playfield: ${JSON.stringify(snakePalette)}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Ludo').click()`);
    await pause();
    const ludoGeometry = await evaluate(`(() => {
        const progress = document.querySelector('.tv-progress-window');
        if (progress && !progress.closest('.tv-dialog-overlay').hidden) {
            progress.querySelector('[data-tv-command="progress-hide"]')?.click();
        }
        const dialog = document.querySelector('.tv-ludo-window');
        const group = dialog?.querySelector('.tv-dialog-client > .tv-group');
        const board = dialog?.querySelector('[data-tv-ludo-board]');
        const players = Array.from(dialog?.querySelectorAll('.tv-ludo-player-toggle') || []);
        const groupRect = group?.getBoundingClientRect();
        const boardRect = board?.getBoundingClientRect();
        const firstRect = players[0]?.getBoundingClientRect();
        const secondRect = players[1]?.getBoundingClientRect();
        const probe = document.createElement('span');
        probe.className = 'tv-static-text';
        probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre';
        probe.textContent = '0'.repeat(45);
        dialog?.appendChild(probe);
        const cellWidth = probe.getBoundingClientRect().width / 45;
        probe.remove();
        return {
            open: Boolean(dialog && !dialog.closest('.tv-dialog-overlay')?.hidden),
            boardColumns: boardRect && cellWidth ? Math.round(boardRect.width / cellWidth) : 0,
            players: players.length,
            hoverPoint: firstRect ? {
                x: firstRect.left + firstRect.width / 2,
                y: firstRect.top + firstRect.height / 2,
            } : null,
            oneRowButtons: Boolean(firstRect && secondRect && Math.abs(firstRect.height - (secondRect.top - firstRect.top)) < 1),
            clipped: Boolean(group && (group.scrollWidth > group.clientWidth || group.scrollHeight > group.clientHeight
                || players.some((button) => {
                    const rect = button.getBoundingClientRect();
                    return rect.left < groupRect.left - 0.5 || rect.top < groupRect.top - 0.5
                        || rect.right > groupRect.right + 0.5 || rect.bottom > groupRect.bottom + 0.5;
                }))),
        };
    })()`);
    if (ludoGeometry.hoverPoint) {
        await send('Input.dispatchMouseEvent', {
            type: 'mouseMoved', x: ludoGeometry.hoverPoint.x, y: ludoGeometry.hoverPoint.y,
        });
    }
    await pause();
    const ludoHover = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-ludo-window');
        const player = dialog?.querySelector('.tv-ludo-player-toggle');
        const body = dialog?.querySelector('.tv-dialog-body');
        const sides = Array.from(player?.querySelectorAll('[data-tv-info-side]') || []);
        return {
            player: player ? getComputedStyle(player).backgroundColor : '',
            body: body ? getComputedStyle(body).backgroundColor : '',
            sides: sides.map((side) => getComputedStyle(side).backgroundColor),
        };
    })()`);
    if (!ludoGeometry.open || ludoGeometry.boardColumns !== 45 || ludoGeometry.players !== 4
        || !ludoGeometry.oneRowButtons || ludoGeometry.clipped
        || ludoHover.sides.length !== 2 || ludoHover.player === ludoHover.body
        || ludoHover.sides.some((background) => background !== ludoHover.body)) {
        throw new Error(`Ludo TVRect geometry is broken: ${JSON.stringify({ ludoGeometry, ludoHover })}`);
    }
    await key("Escape", "Escape", 0, true);

    await evaluate(`__tvMenuItem('dialog-open', 'Tron Light Cycles').click()`);
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
            height: dialog?.style.getPropertyValue('--tv-dialog-height'),
            clipped: Boolean(group && (group.scrollWidth > group.clientWidth || group.scrollHeight > group.clientHeight)),
        };
    })()`);
    if (!tronOpen.open || tronOpen.cells !== 540 || tronOpen.heads !== 2
        || tronOpen.hall !== '[H]' || !tronOpen.timer || tronOpen.height !== '23em' || tronOpen.clipped) {
        throw new Error(`Tron dialog is incomplete: ${JSON.stringify(tronOpen)}`);
    }

    await evaluate(`__tvMenuItem('dialog-open', 'Tower of Hanoi').click()`);
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
            width: hanoi?.style.getPropertyValue('--tv-dialog-width'),
            tronPaused: tron?.querySelector('[data-tv-tron-status]')?.textContent.includes('Inactive window'),
            tronTicks: Number((tron?.querySelector('[data-tv-tron-status]')?.textContent.match(/Ticks: ([0-9]+)/) || [])[1] || 0),
            clipped: Boolean(group && (group.scrollWidth > group.clientWidth || group.scrollHeight > group.clientHeight)),
        };
    })()`);
    if (!hanoiOpen.open || hanoiOpen.towers !== 3 || hanoiOpen.disks !== 5
        || hanoiOpen.draggable !== 1 || hanoiOpen.focused !== '0' || !hanoiOpen.emptyHistory
        || hanoiOpen.hall !== '[H]' || hanoiOpen.width !== '81ch'
        || !hanoiOpen.tronPaused || hanoiOpen.clipped) {
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
        const close = help?.querySelector('[data-tv-close-button]');
        const rect = close?.getBoundingClientRect();
        return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : null;
    })()`);
    if (!hanoiHelpClosePoint) { throw new Error('Tower of Hanoi Help close control is missing'); }
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: hanoiHelpClosePoint.x, y: hanoiHelpClosePoint.y,
        button: 'left', clickCount: 1,
    });
    const hanoiHelpPressed = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return {
            helpOpen: Boolean(help),
            glyph: help?.querySelector('[data-tv-close-glyph]')?.textContent || '',
        };
    })()`);
    if (!hanoiHelpPressed.helpOpen || hanoiHelpPressed.glyph !== '⁎') {
        throw new Error(`Help close control did not remain pressed: ${JSON.stringify(hanoiHelpPressed)}`);
    }
    const hanoiHelpAwayPoint = { x: hanoiHelpClosePoint.x + 40, y: hanoiHelpClosePoint.y };
    await send('Input.dispatchMouseEvent', {
        type: 'mouseMoved', x: hanoiHelpAwayPoint.x, y: hanoiHelpAwayPoint.y,
        button: 'left', buttons: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: hanoiHelpAwayPoint.x, y: hanoiHelpAwayPoint.y,
        button: 'left', clickCount: 1,
    });
    const hanoiHelpCanceled = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]');
        return {
            helpOpen: Boolean(help),
            glyph: help?.querySelector('[data-tv-close-glyph]')?.textContent || '',
        };
    })()`);
    if (!hanoiHelpCanceled.helpOpen || hanoiHelpCanceled.glyph === '⁎') {
        throw new Error(`Dragging off Help close did not cancel it: ${JSON.stringify(hanoiHelpCanceled)}`);
    }
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: hanoiHelpClosePoint.x, y: hanoiHelpClosePoint.y,
        button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: hanoiHelpClosePoint.x, y: hanoiHelpClosePoint.y,
        button: 'left', clickCount: 1,
    });
    const hanoiHelpReleased = await evaluate(`(() => ({
        helpClosed: !document.querySelector('[data-tv-bundle-window="../assets/tv-context-help.json"]'),
        gameActive: Array.from(document.querySelectorAll('.tv-dialog-window')).some((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Tower of Hanoi'
            && element.classList.contains('is-window-active')
        ),
    }))()`);
    if (!hanoiHelpReleased.helpClosed || !hanoiHelpReleased.gameActive) {
        throw new Error(`Releasing the Help close control did not close Help: ${JSON.stringify(hanoiHelpReleased)}`);
    }
    await key("Enter", "Enter", 0, true);
    await key("ArrowRight", "ArrowRight", 0, true);
    await key("Enter", "Enter", 0, true);
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
    await key("u", "KeyU", 0, true);
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

    await evaluate(`__tvMenuItem('dialog-open', 'Puzzle').click()`);
    await pause();
    const hallOpen = await evaluate(`(() => {
        const puzzle = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Puzzle'
        );
        const button = puzzle?.querySelector('.tv-game-hall-control');
        const tiles = Array.from(puzzle?.querySelectorAll('.tv-puzzle-cell') || []);
        const invisibleTiles = tiles.filter((tile) => {
            const style = getComputedStyle(tile);
            return tile.textContent.trim() && style.color === style.backgroundColor;
        }).length;
        const highlighted = tiles.find((tile) => tile.classList.contains('is-highlight'));
        const highlightedStyle = highlighted ? getComputedStyle(highlighted) : null;
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
            invisibleTiles,
            highlightColors: highlightedStyle
                ? [highlightedStyle.backgroundColor, highlightedStyle.color]
                : [],
            open: Boolean(hall && !hall.closest('.tv-dialog-overlay').hidden),
            empty: hall?.querySelector('.tv-dialog-client > .tv-group > .tv-static-text')?.textContent.trim(),
        };
    })()`);
    await pause();
    const hallFrame = await evaluate(`(() => {
        const hall = Array.from(document.querySelectorAll('.tv-dialog-window')).find((element) =>
            element.querySelector('.tv-dialog-title-text')?.textContent === 'Puzzle Hall of Fame'
        );
        const sides = Array.from(hall?.querySelectorAll('.tv-dialog-body > [data-tv-border-side]') || []);
        return {
            sides: sides.length,
            glyphs: sides.map((side) => (side.textContent.match(/[║│]/g) || []).length),
        };
    })()`);
    if (hallOpen.button !== '[H]' || hallOpen.bracketColor !== 'rgb(255, 255, 255)'
        || hallOpen.glyphColor !== 'rgb(85, 255, 85)'
        || hallOpen.invisibleTiles !== 0
        || hallOpen.highlightColors.join() !== ['rgb(170, 170, 170)', 'rgb(0, 0, 170)'].join()
        || !hallOpen.open || hallOpen.empty !== 'No scores yet.'
        || hallFrame.sides !== 2 || hallFrame.glyphs.some((count) => count < 10)) {
        throw new Error(`Hall of Fame control is incomplete: ${JSON.stringify({ hallOpen, hallFrame })}`);
    }
    await evaluate(`(() => {
        window.__globalOpenFetch = window.fetch;
        window.fetch = (url, options = {}) => String(url).startsWith('/api/search/status')
            ? Promise.resolve(new Response(JSON.stringify({ state: 'ready' }), { status: 200 }))
            : String(url).startsWith('/api/search/global')
            ? Promise.resolve(new Response(JSON.stringify({ status: { state: 'ready' }, results: [{
                file: 'Norton Guides/vista.json.gz', help_name: 'db_VISTA III Database Programming Guide',
                context_hex: '378', title: 'VISTA API', preview: 'Open this topic', index_terms: [], text: '',
            }] }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
            : window.__globalOpenFetch(url, options);
        __tvMenuItem('dialog-open', 'Search Topics').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const scope = document.querySelector('.tv-search-window .tv-radio-item input[value="global"]');
            if (scope && !scope.disabled) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Global search scope stayed disabled')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        const search = document.querySelector('.tv-search-window');
        const scope = search.querySelector('.tv-radio-item input[value="global"]');
        scope.checked = true;
        scope.dispatchEvent(new Event('change', { bubbles: true }));
        const input = search.querySelector('.tv-input-line');
        input.value = 'vista';
        input.dispatchEvent(new Event('input', { bubbles: true }));
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const result = document.querySelector('.tv-search-window .tv-search-result');
            if (result?.textContent.includes('VISTA API')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Global VISTA result did not appear')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        window.fetch = window.__globalOpenFetch;
        document.querySelector('.tv-search-window [data-tv-command="search-ok"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const windowView = Array.from(document.querySelectorAll('[data-tv-bundle-window]'))
                .map((element) => element._tvWindowView)
                .find((view) => view?.sourceFile === 'Norton Guides/vista.json.gz'
                    && view.currentTopic === '378');
            if (windowView) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Global result did not open its HELP topic')); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        window.__docsSearchFetch = window.fetch;
        window.fetch = (url, options = {}) => String(url).startsWith('/api/search/status')
            ? Promise.resolve(new Response(JSON.stringify({ state: 'ready' }), { status: 200 }))
            : String(url).startsWith('/api/search/global')
            ? Promise.resolve(new Response(JSON.stringify({ status: { state: 'ready' }, results: [{
                kind: 'doc', file: 'README.md', help_name: 'Docs', source_file: 'README.md',
                context_hex: '', title: 'README', preview: 'Project documentation',
            }] }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
            : window.__docsSearchFetch(url, options);
        __tvMenuItem('dialog-open', 'Search Topics').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const scope = document.querySelector('.tv-search-window .tv-radio-item input[value="global"]');
            if (scope && !scope.disabled) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Docs search scope stayed disabled')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        const search = document.querySelector('.tv-search-window');
        const scope = search.querySelector('.tv-radio-item input[value="global"]');
        scope.checked = true;
        scope.dispatchEvent(new Event('change', { bubbles: true }));
        const input = search.querySelector('.tv-input-line');
        input.value = 'readme';
        input.dispatchEvent(new Event('input', { bubbles: true }));
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const result = document.querySelector('.tv-search-window .tv-search-result');
            if (result?.textContent.includes('README.md')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Global Docs result did not appear')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        window.fetch = window.__docsSearchFetch;
        document.querySelector('.tv-search-window [data-tv-command="search-ok"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (document.querySelector('.tv-doc-window')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Global Docs result did not open its document')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`__tvMenuItem('doc-open')?.click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (document.querySelector('.tv-doc-window')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Document window did not open for close test')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const inactiveClose = await evaluate(`(async () => {
        const doc = document.querySelector('.tv-doc-window');
        const help = document.querySelector('[data-tv-bundle-window]');
        help?.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        const close = doc?.querySelector('.tv-close-control');
        if (!doc || !close || !doc.classList.contains('is-window-inactive')) {
            return { ready: false, hasDoc: Boolean(doc), hasHelp: Boolean(help),
                inactive: doc?.classList.contains('is-window-inactive') };
        }
        const pointerEvents = getComputedStyle(close).pointerEvents;
        close.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        const pressedGlyph = close.querySelector('.tv-close-glyph')?.textContent;
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: 0, clientY: 0 }));
        await new Promise((resolve) => setTimeout(resolve, 20));
        const outsideStayedOpen = doc.isConnected;
        help?.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        close.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        close.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        await new Promise((resolve) => setTimeout(resolve, 20));
        return { ready: true, pointerEvents, pressedGlyph, outsideStayedOpen,
            closed: !doc.isConnected };
    })()`, true);
    if (!inactiveClose.ready || inactiveClose.pointerEvents === 'none'
        || inactiveClose.pressedGlyph !== '⁎' || !inactiveClose.outsideStayedOpen
        || !inactiveClose.closed) {
        throw new Error(`Inactive window close button did not activate on mouse release: ${JSON.stringify(inactiveClose)}`);
    }
    await evaluate(`__tvMenuItem('dialog-open', 'About')?.click()`);
    const inactiveDialogClose = await evaluate(`(async () => {
        const overlay = document.querySelector('.tv-about-overlay');
        const close = overlay?.querySelector('.tv-dialog-close-control');
        const help = document.querySelector('[data-tv-bundle-window]');
        if (!overlay || overlay.hidden || !close || !help) { return false; }
        help.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        close.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        close.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        await new Promise((resolve) => setTimeout(resolve, 20));
        return overlay.hidden;
    })()`, true);
    if (!inactiveDialogClose) { throw new Error('Inactive dialog Close did not activate on mouse release'); }
    await send('Page.navigate', { url: appUrl + '?search_doc=README.md' });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (document.querySelector('.tv-doc-window')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Docs deep link did not open the TVision document')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const indexDeadline = Date.now() + 20000;
    while (true) {
        const status = await (await fetch(appUrl + 'api/search/status')).json();
        if (status.state === 'ready') { break; }
        if (Date.now() > indexDeadline) { throw new Error(`Public index did not become ready: ${JSON.stringify(status)}`); }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    await send('Page.navigate', { url: appUrl });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (!document.getElementById('tv-public-fallback')
                && document.querySelector('[data-tv-menu-bar]')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Homepage catalog fallback remained over TVision')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const crawlableCatalog = await evaluate(`(async () => {
        const catalog = await (await fetch('helps/catalog.json')).json();
        const docs = await (await fetch('docs/catalog.json')).json();
        const menu = document.querySelector('[data-tv-menu-bar]');
        const links = Array.from(menu.querySelectorAll('a[href]')).map((link) => new URL(link.href));
        return {
            helps: catalog.every((entry) => links.some((url) => url.searchParams.get('file') === entry.file)),
            docs: docs.every((entry) => links.some((url) => url.searchParams.get('doc') === entry.file)),
            count: links.length,
        };
    })()`, true);
    if (!crawlableCatalog.helps || !crawlableCatalog.docs || !crawlableCatalog.count) {
        throw new Error('Rendered homepage lost catalog links: ' + JSON.stringify(crawlableCatalog));
    }
    await evaluate(`(() => {
        window.__crawlSamePage = true;
        const item = __tvMenuItem('bundle-open', 'VISTA.NG');
        const links = Array.from(document.querySelectorAll('[data-tv-menu-bar] a[href]'));
        const vista = item || links.find((link) => new URL(link.href).searchParams.get('file') === 'Norton Guides/vista.json.gz');
        if (!vista) { throw new Error('VISTA catalog link missing'); }
        vista.click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (window.__crawlSamePage && document.querySelector('[data-tv-bundle-window]')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Catalog anchor did not open via TVEvent on the same page')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await send('Page.navigate', { url: appUrl + '?doc=README.md' });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const doc = document.querySelector('.tv-doc-window');
            if (window.location.search === '?doc=README.md' && doc
                && !document.getElementById('tv-public-fallback')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Public Docs URL did not open TVision directly')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const publicDocUrl = await evaluate('window.location.search');
    if (publicDocUrl !== '?doc=README.md') {
        throw new Error(`Public Docs URL was not preserved: ${publicDocUrl}`);
    }
    await assertWindowOnDesktop('.tv-doc-window', 'Public Docs');
    await send('Page.navigate', {
        url: appUrl + '?file=' + encodeURIComponent('Norton Guides/vista.json.gz') + '&topic=378',
    });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const help = document.querySelector('[data-tv-bundle-window]');
            if (window.location.search.includes('topic=378') && help
                && !document.getElementById('tv-public-fallback')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Public HELP URL did not open TVision directly')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const publicHelpUrl = await evaluate('window.location.search');
    if (!publicHelpUrl.includes('topic=378')) {
        throw new Error(`Public HELP URL was not preserved: ${publicHelpUrl}`);
    }
    await assertWindowOnDesktop('[data-tv-bundle-window]', 'Public HELP topic');
    await send('Page.navigate', {
        url: appUrl + '?file=' + encodeURIComponent('Norton Guides/vista.json.gz'),
    });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const help = document.querySelector('[data-tv-bundle-window]');
            if (window.location.search.startsWith('?file=') && !window.location.search.includes('topic=')
                && help && !document.getElementById('tv-public-fallback')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Public HELP overview did not open TVision directly')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await assertWindowOnDesktop('[data-tv-bundle-window]', 'Public HELP overview');
    const crawlableTopics = await evaluate(`(() => {
        const help = document.querySelector('[data-tv-bundle-window]');
        const index = document.querySelector('[data-tv-command="bundle-index"]');
        index?.click();
        return Array.from(help.querySelectorAll('a[data-tv-bundle-topic]')).filter((link) => {
            const url = new URL(link.href);
            return url.searchParams.get('file') === 'Norton Guides/vista.json.gz' && url.searchParams.has('topic');
        }).length;
    })()`);
    if (!crawlableTopics) { throw new Error('Rendered HELP overview lost public topic URLs'); }
    const topicAnchorNavigation = await evaluate(`(async () => {
        const help = document.querySelector('[data-tv-bundle-window]');
        const link = help.querySelector('a[data-tv-bundle-topic][href*="topic="]');
        const target = link.dataset.tvBundleTopic;
        window.__crawlSamePage = true;
        link.click();
        await new Promise((resolve) => setTimeout(resolve, 50));
        return window.__crawlSamePage && help.isConnected && help._tvWindowView.currentTopic === target;
    })()`, true);
    if (!topicAnchorNavigation) { throw new Error('Real topic anchor did not navigate through TVEvent'); }
    await send('Page.navigate', {
        url: appUrl + '?topic=378&file=Norton+Guides/vista.json.gz&line=1#kept-bookmark',
    });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (document.querySelector('[data-tv-bundle-window]')
                && window.location.search === '?file=Norton+Guides%2Fvista.json.gz&topic=378&line=1'
                && window.location.hash === '#kept-bookmark') { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Canonical redirect lost TVision topic, line or bookmark')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    for (const [file, topic] of [
        ['Borland Turbo C 1.x current/tchelp.json.gz', '3'],
        ['Borland Turbo C 1.x current/tchelp.json.gz', '591'],
        ['Microsoft MS-DOS 6.22/help.json.gz', '29'],
        ['Borland Turbo C++ 1.00/tchelp.json.gz', '719'],
    ]) {
        await send('Page.navigate', { url: appUrl + '?' + new URLSearchParams({ file, topic }) });
        await evaluate(`new Promise((resolve, reject) => {
            const deadline = Date.now() + 10000;
            const check = () => {
                const view = document.querySelector('[data-tv-bundle-window]')?._tvWindowView;
                if (view?.bundle?._catalogFile === ${JSON.stringify(file)}
                    && view.currentTopic === ${JSON.stringify(topic)}
                    && !document.getElementById('tv-public-fallback')) {
                    const error = document.querySelector('.tv-msgbox-window');
                    if (error && !error.closest('.tv-dialog-overlay').hidden) {
                        reject(new Error('A valid diagnostic HELP topic displayed a website error')); return;
                    }
                    if (!document.querySelector('meta[name="description"]')?.content
                        .startsWith('Reference documentation from ')) {
                        reject(new Error('Rendered topic lost its reference-documentation metadata')); return;
                    }
                    resolve(true); return;
                }
                if (Date.now() > deadline) { reject(new Error('Diagnostic HELP topic did not render')); return; }
                setTimeout(check, 30);
            };
            check();
        })`, true);
    }
    const errorResponse = await fetch(appUrl + 'seo-missing-page', { headers: { Accept: 'text/html' } });
    if (errorResponse.status !== 404 || errorResponse.headers.get('x-robots-tag') !== 'noindex') {
        throw new Error('Missing page still returns an indexable success response');
    }
    await send('Page.navigate', { url: appUrl + 'seo-missing-page' });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const box = document.querySelector('.tv-msgbox-window');
            if (box && !box.closest('.tv-dialog-overlay').hidden
                && box.textContent.includes('/seo-missing-page')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Real HTTP 404 stopped the TVision error MessageBox')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    socket.close();
}

const timeout = setTimeout(() => {
    process.stderr.write("browser smoke test timed out\n");
    process.exit(1);
}, 60000);
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
                    timeout=65,
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
        if server_state_directory is not None:
            server_state_directory.cleanup()
