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

    const docColors = await evaluate(`(() => {
        const doc = document.querySelector('.tv-doc-window');
        const viewport = doc.querySelector('.tv-viewport');
        const content = doc.querySelector('.tv-doc-document');
        const pair = (element) => {
            const style = getComputedStyle(element);
            return [style.backgroundColor, style.color];
        };
        return { viewport: pair(viewport), content: pair(content) };
    })()`);
    const editorColors = ['rgb(0, 0, 170)', 'rgb(255, 255, 85)'];
    if (docColors.viewport.join() !== editorColors.join() || docColors.content.join() !== editorColors.join()) {
        throw new Error(`Documentation does not use the Editor palette: ${JSON.stringify(docColors)}`);
    }

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
            resetCount: dialog.querySelectorAll('[data-tv-colors-reset]').length,
            foregroundColors: dialog.querySelectorAll('[data-tv-colors-foreground] .tv-color-cell').length,
            backgroundColors: dialog.querySelectorAll('[data-tv-colors-background] .tv-color-cell').length,
            sampleRows: dialog.querySelectorAll('.tv-colors-display-sample br').length + 1,
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
        buttons: [23, 14, 34, 2],
    };
    const expectedDialogAttrs = [
        0x7F, 0x7A, 0x13, 0x13, 0x70, 0x70, 0x7F, 0x7E,
        0x20, 0x2B, 0x2F, 0x78, 0x2E, 0x70, 0x30, 0x3F, 0x3E,
        0x1F, 0x2F, 0x1A, 0x20, 0x72, 0x31, 0x31, 0x30, 0x2F,
        0x3E, 0x31, 0x13,
    ];
    if (
        !colors.open || colors.buttonCount !== 3 || colors.resetCount !== 1
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
            currentGroups: dialog.querySelectorAll('.tv-colors-listviewer.is-current').length,
            groupColors: stylePair(group),
            itemColors: stylePair(item),
        };
        group.click();
        return result;
    })()`);
    if (
        !colorsListFocus.itemFocused || colorsListFocus.currentGroups !== 1
        || colorsListFocus.groupColors.join() !== ['rgb(0, 170, 170)', 'rgb(255, 255, 85)'].join()
        || colorsListFocus.itemColors.join() !== ['rgb(0, 170, 0)', 'rgb(255, 255, 255)'].join()
    ) {
        throw new Error(`Colors list focus is inconsistent: ${JSON.stringify(colorsListFocus)}`);
    }
    const colorsReset = await evaluate(`(() => {
        const dialog = document.querySelector('.tv-colors-window');
        const expected = window.THelpViewerTV.buildDefaultColorPalette()[2].items[1].attr & 0x0F;
        const changed = (expected + 1) % 16;
        dialog.querySelector('[data-tv-colors-foreground] [data-tv-color-index="' + changed + '"]').click();
        const changedIndex = Number(dialog.querySelector('[data-tv-colors-foreground] [aria-pressed="true"]').dataset.tvColorIndex);
        dialog.querySelector('[data-tv-colors-reset]').click();
        const resetIndex = Number(dialog.querySelector('[data-tv-colors-foreground] [aria-pressed="true"]').dataset.tvColorIndex);
        return { expected, changed, changedIndex, resetIndex };
    })()`);
    if (colorsReset.changedIndex !== colorsReset.changed || colorsReset.resetIndex !== colorsReset.expected) {
        throw new Error(`Colors Reset did not restore defaults: ${JSON.stringify(colorsReset)}`);
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
        const infoRow = dialog.querySelector('[data-tv-row="status"]');
        const infoRect = info.getBoundingClientRect();
        const rowRect = infoRow.getBoundingClientRect();
        return {
            open: true,
            checks: dialog.querySelectorAll('[data-tv-gallery-checks] input[type="checkbox"]').length,
            radios: dialog.querySelectorAll('[data-tv-gallery-radios] input[type="radio"]').length,
            disabledChoices: dialog.querySelectorAll('.tv-choice-input:disabled').length,
            listItems: dialog.querySelectorAll('[data-tv-gallery-list-index]').length,
            selectedItems: dialog.querySelectorAll('[data-tv-gallery-list-index].is-selected').length,
            selectedIndex: dialog.querySelector('[data-tv-gallery-list-index].is-selected')?.dataset.tvGalleryListIndex,
            listFocused: document.activeElement === clickedItem,
            disabledButtons: dialog.querySelectorAll('.tv-dialog-button:disabled').length,
            status: dialog.querySelector('[data-tv-row="status"]')?.textContent || '',
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
        || gallery.disabledChoices !== 2 || gallery.listItems !== 5 || gallery.selectedItems !== 1
        || gallery.selectedIndex !== '2' || !gallery.listFocused
        || gallery.disabledButtons !== 1 || !gallery.status.includes('Selected: TListViewer')
        || !gallery.infoRightBorder || !gallery.infoRowFits
        || gallery.infoSideColors.some((color) => color !== 'rgb(255, 255, 255)')
        || !gallery.frameSidesAligned
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
