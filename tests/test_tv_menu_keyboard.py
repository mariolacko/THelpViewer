from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the menu keyboard test")
def test_shared_menu_controller_maps_turbovision_keyboard_commands():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor() {
        this.dataset = {};
        this.style = { setProperty() {}, removeProperty() {} };
        this.classList = { add() {}, remove() {}, contains() { return false; }, toggle() {} };
        this.isConnected = true;
    }
    addEventListener() {}
    removeEventListener() {}
    appendChild() {}
    remove() {}
    focus() { document.activeElement = this; }
    closest() { return null; }
    querySelector() { return null; }
    querySelectorAll() { return []; }
    getBoundingClientRect() { return { width: 8, height: 16, top: 0, left: 0, right: 8 }; }
}

global.HTMLElement = FakeElement;
global.window = global;
global.window.THelpViewerTV = {};
global.window.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
global.window.matchMedia = () => ({ matches: false });
global.window.addEventListener = () => {};
global.window.requestAnimationFrame = (callback) => callback();
global.document = {
    activeElement: null,
    body: new FakeElement(),
    documentElement: new FakeElement(),
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return new FakeElement(); },
};
global.getComputedStyle = () => ({ getPropertyValue() { return ""; } });

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;

function keyEvent(key, extra = {}) {
    return {
        key,
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; },
        ...extra,
    };
}

const toggleA = { mnemonic: "x" };
const toggleB = { mnemonic: "h" };
const rootA = { id: "system", querySelector() { return toggleA; } };
const rootB = { id: "help", querySelector() { return toggleB; } };
const controller = Object.create(TV.TVMenuController.prototype);
controller.menuRoots = [rootA, rootB];
controller.topLevelActions = [];
controller.activeRoot = null;
controller.activePopup = null;
controller.onUnhandledKeyDown = null;
controller.menuMnemonic = (element) => element.mnemonic || "";
let opened = null;
let closed = 0;
controller.openMenu = (root) => { opened = root; controller.activeRoot = root; };
controller.closeMenus = () => { closed += 1; controller.activeRoot = null; };

const f10 = keyEvent("F10");
controller.onKeyDown(f10);
if (opened !== rootA || !f10.defaultPrevented) {
    throw new Error("F10 did not open the first menu");
}
const secondF10 = keyEvent("F10");
controller.onKeyDown(secondF10);
if (closed !== 1 || controller.activeRoot !== null) {
    throw new Error("F10 did not close an active menu");
}

const altH = keyEvent("h", { altKey: true });
controller.onKeyDown(altH);
if (opened !== rootB || !altH.defaultPrevented) {
    throw new Error("Alt mnemonic did not open its top-level menu");
}

let directClicks = 0;
const directAction = { mnemonic: "d", click() { directClicks += 1; } };
controller.activeRoot = null;
controller.topLevelActions = [directAction];
controller.menuMnemonic = (element) => element.mnemonic || "";
const altD = keyEvent("d", { altKey: true });
controller.onKeyDown(altD);
if (directClicks !== 1 || !altD.defaultPrevented) {
    throw new Error("Alt mnemonic did not activate a direct menu-bar command");
}
controller.topLevelActions = [];
controller.activeRoot = rootB;

let move = 0;
controller.moveSelection = (delta) => { move = delta; };
const down = keyEvent("ArrowDown");
controller.onKeyDown(down);
if (move !== 1 || !down.defaultPrevented) {
    throw new Error("ArrowDown did not move the menu selection");
}
const up = keyEvent("ArrowUp");
controller.onKeyDown(up);
if (move !== -1 || !up.defaultPrevented) {
    throw new Error("ArrowUp did not move the menu selection");
}

let switched = 0;
controller.activePopup = { matches() { return false; } };
controller.switchRoot = (delta) => { switched = delta; };
controller.onKeyDown(keyEvent("ArrowRight"));
if (switched !== 1) { throw new Error("ArrowRight did not switch the top-level menu"); }
controller.onKeyDown(keyEvent("ArrowLeft"));
if (switched !== -1) { throw new Error("ArrowLeft did not switch the top-level menu"); }

const submenuPopup = { matches(selector) { return selector === "[data-tv-submenu-popup]"; } };
controller.activePopup = submenuPopup;
let closedSubmenu = null;
controller.closeSubmenu = (popup) => { closedSubmenu = popup; };
controller.onKeyDown(keyEvent("Escape"));
if (closedSubmenu !== submenuPopup) {
    throw new Error("Escape did not return from a submenu");
}

let clicked = 0;
const mnemonicItem = {
    disabled: false,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return submenuPopup; },
    matches() { return false; },
    click() { clicked += 1; },
};
controller.activePopup = submenuPopup;
controller.menuItems = () => [mnemonicItem];
controller.menuMnemonic = () => "o";
controller.markSelected = () => {};
if (!controller.activateMnemonic("o") || clicked !== 1) {
    throw new Error("popup mnemonic did not activate its command");
}

const foreignPopup = {};
const enabled = {
    disabled: false,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return submenuPopup; },
};
const disabled = {
    disabled: true,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return submenuPopup; },
};
const nested = {
    disabled: false,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return foreignPopup; },
};
submenuPopup.querySelectorAll = () => [enabled, disabled, nested];
controller.menuItems = TV.TVMenuController.prototype.menuItems;
const filtered = controller.menuItems(submenuPopup);
if (filtered.length !== 1 || filtered[0] !== enabled) {
    throw new Error("menu navigation included disabled or nested items");
}
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_shell_and_bundle_use_the_shared_menu_controller():
    shell_paths = (
        Path("www/assets/tv-shell.js"),
        Path("thelpviewer/converter/assets/tv-shell.js"),
    )
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/converter/assets/turbovision.css"),
    )
    assert shell_paths[0].read_bytes() == shell_paths[1].read_bytes()
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert css_paths[0].read_bytes() == css_paths[1].read_bytes()

    shell = shell_paths[0].read_text(encoding="utf-8")
    bundle = bundle_paths[0].read_text(encoding="utf-8")
    css = css_paths[0].read_text(encoding="utf-8")
    assert "class TurboVisionMenus extends TVMenuController" in shell
    assert "new TVMenuController" in bundle
    assert "menuController.refresh()" in bundle
    assert "_menuGlobalsBound" not in bundle
    assert ".tv-menu-popup-item.is-menu-selected" in css


@pytest.mark.skipif(NODE is None, reason="Node.js is required for command-state behavior tests")
def test_dialog_manager_reports_commands_available_for_the_active_target():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVDialogManager");
const end = source.indexOf("// ── TVMessageBox", start);
const HOST_WINDOW_TOKEN = "__host__";
const TV_COMMANDS = {
    CLOSE: "close", CANCEL: "cancel", ZOOM: "zoom", NEXT: "next", PREVIOUS: "previous",
};
global.document = { querySelector: () => null, body: {} };
eval(source.slice(start, end) + "\nglobalThis.TestDialogManager = TVDialogManager;");

const manager = new TestDialogManager({});
if (manager.canDispatchCommand(TV_COMMANDS.CLOSE) || manager.canDispatchCommand(TV_COMMANDS.NEXT)) {
    throw new Error("commands were enabled without a managed target");
}
const first = { isConnected: true };
manager.windows.set("first", first);
manager.windowCommands.set("first", { close() {}, zoom() {} });
manager.stackOrder = ["first"];
manager.activeTarget = "first";
if (!manager.canDispatchCommand(TV_COMMANDS.CLOSE) || !manager.canDispatchCommand(TV_COMMANDS.ZOOM)) {
    throw new Error("active window commands were not enabled");
}
if (manager.canDispatchCommand(TV_COMMANDS.NEXT) || manager.openWindowCount() !== 1) {
    throw new Error("Next was enabled for only one window");
}
manager.windows.set("second", { isConnected: true });
manager.stackOrder.push("second");
if (!manager.canDispatchCommand(TV_COMMANDS.NEXT) || !manager.canDispatchCommand(TV_COMMANDS.PREVIOUS)) {
    throw new Error("window cycling was not enabled for multiple targets");
}
manager.dialogs.set("dialog", { isOpen: () => true });
manager.stackOrder.push("dialog");
manager.activeTarget = "dialog";
if (!manager.canDispatchCommand(TV_COMMANDS.CLOSE) || manager.canDispatchCommand(TV_COMMANDS.ZOOM)) {
    throw new Error("dialog command state did not replace the active window state");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for command-state behavior tests")
def test_bundle_window_menu_reflects_dynamic_command_state():
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/converter/assets/turbovision.css"),
    )
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert css_paths[0].read_bytes() == css_paths[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVBundleApp");
const end = source.indexOf("// ── Bootstrap", start);
const TV_COMMANDS = { CLOSE: "close", ZOOM: "zoom", NEXT: "next", PREVIOUS: "previous" };
eval(source.slice(start, end) + "\nglobalThis.TestBundleApp = TVBundleApp;");

function item(command) {
    const classes = new Set();
    const attributes = new Map();
    return {
        dataset: { tvWindowCmd: command },
        disabled: false,
        tabIndex: 0,
        classList: {
            toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); },
            remove(name) { classes.delete(name); },
            contains(name) { return classes.has(name); },
        },
        setAttribute(name, value) { attributes.set(name, value); },
        getAttribute(name) { return attributes.get(name); },
    };
}
const items = ["tile", "cascade", "list", "zoom", "next", "previous", "close"].map(item);
global.document = { querySelectorAll: () => items };
const app = Object.create(TestBundleApp.prototype);
let windowCount = 0;
let targetCount = 0;
const enabledCommands = new Set();
app.dialogManager = {
    openWindowCount: () => windowCount,
    openTargets: () => new Array(targetCount),
    canDispatchCommand: (command) => enabledCommands.has(command),
};
app._updateWindowMenuState();
if (items.some((entry) => !entry.disabled || entry.getAttribute("aria-disabled") !== "true")) {
    throw new Error("window commands were enabled without open targets");
}

windowCount = 1;
targetCount = 1;
enabledCommands.add(TV_COMMANDS.CLOSE);
enabledCommands.add(TV_COMMANDS.ZOOM);
app._updateWindowMenuState();
const byCommand = Object.fromEntries(items.map((entry) => [entry.dataset.tvWindowCmd, entry]));
for (const command of ["tile", "cascade", "list", "zoom", "close"]) {
    if (byCommand[command].disabled || byCommand[command].classList.contains("is-disabled")) {
        throw new Error(`${command} was not enabled for an active window`);
    }
}
if (!byCommand.next.disabled || !byCommand.previous.disabled) {
    throw new Error("cycling was enabled for a single target");
}
enabledCommands.add(TV_COMMANDS.NEXT);
enabledCommands.add(TV_COMMANDS.PREVIOUS);
app._updateWindowMenuState();
if (byCommand.next.disabled || byCommand.previous.disabled) {
    throw new Error("cycling was not enabled for multiple targets");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(bundle_paths[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    css = css_paths[0].read_text(encoding="utf-8")
    assert '--tv-palette-menu-disabled-fg: #555555;' in css
    assert '--tv-menu-disabled: var(--tv-palette-menu-disabled-fg);' in css
    assert '.tv-menu-popup-item[aria-disabled="true"]' in css
