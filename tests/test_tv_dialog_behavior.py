from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
ASSET_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the dialog behaviour test")
def test_tv_dialog_shared_keyboard_modal_and_focus_behaviour():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor(name = "element") {
        this.name = name;
        this.hidden = false;
        this.disabled = false;
        this.isConnected = true;
        this.style = { setProperty() {}, removeProperty() {} };
        this.dataset = {};
        this.attributes = new Map();
        this.listeners = new Map();
        this.offsetWidth = 80;
        this.offsetHeight = 25;
        this.clientWidth = 160;
        this.clientHeight = 50;
        this.clicked = 0;
        const classes = new Set();
        this.classList = {
            add(...names) { names.forEach((name) => classes.add(name)); },
            remove(...names) { names.forEach((name) => classes.delete(name)); },
            contains(name) { return classes.has(name); },
            toggle(name, force) {
                const enabled = force === undefined ? !classes.has(name) : Boolean(force);
                if (enabled) { classes.add(name); } else { classes.delete(name); }
                return enabled;
            },
        };
    }
    addEventListener(type, handler) { this.listeners.set(type, handler); }
    removeEventListener(type) { this.listeners.delete(type); }
    appendChild() {}
    remove() { this.isConnected = false; }
    focus() { document.activeElement = this; }
    click() { this.clicked += 1; }
    closest(selector) {
        if (selector === "[hidden]") { return null; }
        return null;
    }
    getAttribute(name) { return this.attributes.get(name) || null; }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    removeAttribute(name) { this.attributes.delete(name); }
    getBoundingClientRect() { return { width: 8, height: 16 }; }
    querySelector() { return null; }
    querySelectorAll() { return []; }
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
    body: new FakeElement("body"),
    documentElement: new FakeElement("documentElement"),
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return new FakeElement("created"); },
};
global.getComputedStyle = () => ({ getPropertyValue() { return ""; } });

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;

function buildDialog(options = {}) {
    const overlay = new FakeElement("overlay");
    overlay.hidden = true;
    const dialogElement = new FakeElement("dialog");
    const titlebar = new FakeElement("titlebar");
    const first = new FakeElement("first");
    const second = new FakeElement("second");
    const defaultButton = new FakeElement("default");
    const closeButton = new FakeElement("close");
    dialogElement.querySelector = (selector) => (
        selector === ".tv-dialog-button.is-default" ? defaultButton
            : selector === "[data-tv-close-button]" ? closeButton
            : null
    );
    dialogElement.querySelectorAll = () => [first, second];
    overlay.querySelector = (selector) => {
        if (selector === ".tv-dialog-window") { return dialogElement; }
        if (selector === ".tv-dialog-titlebar") { return titlebar; }
        return null;
    };
    overlay.querySelectorAll = () => [];
    TV.TVWidget.fromHTML = () => overlay;
    const instance = new TV.TVDialog({
        desktop: document.body,
        ariaLabel: "Test",
        title: "Test",
        bodyMarkup: "",
        footerMarkup: "",
        ...options,
    });
    return { instance, overlay, dialogElement, first, second, defaultButton, closeButton };
}

function keyEvent(key, target, extra = {}) {
    return {
        key,
        target,
        defaultPrevented: false,
        propagationStopped: false,
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.propagationStopped = true; },
        ...extra,
    };
}

const launcher = new FakeElement("launcher");
document.activeElement = launcher;
const regular = buildDialog();
regular.instance.open();
if (document.activeElement !== regular.dialogElement) { throw new Error("dialog did not receive focus"); }

regular.instance.startDrag({
    target: regular.dialogElement,
    clientX: 10,
    clientY: 10,
    preventDefault() {},
});
if (!regular.dialogElement.classList.contains("is-dragging")) {
    throw new Error("dialog move frame state was not preserved");
}
regular.instance.onDragEnd();
if (regular.dialogElement.classList.contains("is-dragging")) {
    throw new Error("dialog move frame state was not cleared");
}

const enter = keyEvent("Enter", regular.dialogElement);
regular.instance.onDialogKeyDown(enter);
if (regular.defaultButton.clicked !== 1 || !enter.defaultPrevented) {
    throw new Error("Enter did not invoke the default button");
}

document.activeElement = regular.second;
const tab = keyEvent("Tab", regular.second);
regular.instance.onDialogKeyDown(tab);
if (document.activeElement !== regular.first) { throw new Error("Tab did not wrap focus"); }

const escape = keyEvent("Escape", regular.dialogElement);
regular.instance.onDialogKeyDown(escape);
if (!regular.overlay.hidden || document.activeElement !== launcher) {
    throw new Error("Escape did not close and restore focus");
}

const calculatorLike = buildDialog({ escapeCloses: false });
calculatorLike.instance.open();
const calculatorEscape = keyEvent("Escape", calculatorLike.dialogElement);
calculatorLike.instance.onDialogKeyDown(calculatorEscape);
if (calculatorLike.overlay.hidden || calculatorEscape.defaultPrevented) {
    throw new Error("escapeCloses=false was ignored");
}

const modal = buildDialog({ modal: true });
modal.instance.open();
const letter = keyEvent("p", modal.dialogElement);
modal.instance.onDialogKeyDown(letter);
if (!letter.propagationStopped || letter.defaultPrevented) {
    throw new Error("modal dialog did not isolate an unhandled key");
}

const modalMarkup = TV.TVFrame.dialogMarkup({
    ariaLabel: "Modal",
    title: "Modal",
    bodyMarkup: "",
    footerMarkup: "",
    modal: true,
});
const nonModalMarkup = TV.TVFrame.dialogMarkup({
    ariaLabel: "Non-modal",
    title: "Non-modal",
    bodyMarkup: "",
    footerMarkup: "",
});
if (!modalMarkup.includes('aria-modal="true"') || !modalMarkup.includes("is-modal")) {
    throw new Error("modal markup is incomplete");
}
if (!nonModalMarkup.includes('aria-modal="false"')) {
    throw new Error("non-modal markup is incorrectly announced as modal");
}
const titlebarMarkup = modalMarkup.slice(
    modalMarkup.indexOf('class="tv-dialog-titlebar"'),
    modalMarkup.indexOf('class="tv-dialog-body"')
);
if ((titlebarMarkup.match(/data-tv-border-fill=/g) || []).length !== 1) {
    throw new Error("dialog title frame is not a single continuous line");
}

const manager = new TV.TVDialogManager(document.body);
const managedWindow = new FakeElement("managed-window");
let closeCalls = 0;
let zoomCalls = 0;
manager.registerWindow("viewer", managedWindow, {
    [TV.TV_COMMANDS.CLOSE]: () => { closeCalls += 1; },
    [TV.TV_COMMANDS.ZOOM]: () => { zoomCalls += 1; },
});
if (!manager.dispatchCommand(TV.TV_COMMANDS.ZOOM) || zoomCalls !== 1) {
    throw new Error("active window did not receive Zoom");
}
if (!manager.dispatchCommand(TV.TV_COMMANDS.CLOSE) || closeCalls !== 1) {
    throw new Error("active window did not receive Close");
}

const managedDialog = buildDialog();
let dialogCloseCalls = 0;
managedDialog.instance.bindCommonClose(() => {
    dialogCloseCalls += 1;
    managedDialog.instance.close();
});
manager.register("managed-dialog", managedDialog.instance);
managedDialog.instance.open();
if (managedDialog.closeButton.hidden) {
    throw new Error("active dialog close control is hidden");
}
TV.updateWindowFrameState(managedDialog.dialogElement, false, { dialog: true });
if (!managedDialog.closeButton.hidden) {
    throw new Error("inactive dialog close control is still drawn");
}
TV.updateWindowFrameState(managedDialog.dialogElement, true, { dialog: true });
if (!manager.dispatchCommand(TV.TV_COMMANDS.CLOSE) || dialogCloseCalls !== 1) {
    throw new Error("active dialog did not receive Close");
}
managedDialog.instance.destroy();
if (manager.get("managed-dialog") !== null || managedDialog.overlay.isConnected) {
    throw new Error("destroy did not remove and unregister the dialog");
}
managedDialog.instance.open();
if (managedDialog.overlay.isConnected || !managedDialog.overlay.hidden) {
    throw new Error("a destroyed dialog was reopened");
}

const secondWindow = new FakeElement("second-window");
manager.registerWindow("second", secondWindow);
if (!manager.dispatchCommand(TV.TV_COMMANDS.NEXT) || manager.activeTarget !== "viewer") {
    throw new Error("Next did not cycle to the following managed target");
}
if (!manager.dispatchCommand(TV.TV_COMMANDS.PREVIOUS) || manager.activeTarget !== "second") {
    throw new Error("Previous did not cycle to the preceding managed target");
}
"""
    result = subprocess.run(
        [NODE, "-e", script, str(ASSET_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_calculator_preserves_escape_as_a_calculator_key():
    dialog_paths = (
        Path("www/assets/tv-dialogs.js"),
        Path("thelpviewer/converter/assets/tv-dialogs.js"),
    )
    assert dialog_paths[0].read_bytes() == dialog_paths[1].read_bytes()
    source = dialog_paths[0].read_text(encoding="utf-8")
    calculator = source[source.index("class TVCalculatorDialog"):source.index("class TVCalendarDialog")]
    assert "escapeCloses: false" in calculator


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the calendar behavior test")
def test_calendar_uses_gregorian_leap_year_rules():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function isLeapYear");
const end = source.indexOf("function dayOfWeek", start);
eval(source.slice(start, end) + "\nglobalThis.testLeapYear = isLeapYear;");
const expected = new Map([
    [1900, false],
    [2000, true],
    [2023, false],
    [2024, true],
    [2100, false],
]);
for (const [year, leap] of expected) {
    if (testLeapYear(year) !== leap) {
        throw new Error(`unexpected leap-year result for ${year}`);
    }
}
'''
    subprocess.run(
        [NODE, "-e", script, str(ASSET_PATHS[0])],
        check=True,
        capture_output=True,
        text=True,
    )


def test_close_and_zoom_commands_are_routed_to_the_active_target():
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    shell_paths = (
        Path("www/assets/tv-shell.js"),
        Path("thelpviewer/converter/assets/tv-shell.js"),
    )
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert shell_paths[0].read_bytes() == shell_paths[1].read_bytes()

    bundle_source = bundle_paths[0].read_text(encoding="utf-8")
    shell_source = shell_paths[0].read_text(encoding="utf-8")
    assert 'registerWindow("help:" + key, windowEl, {' in bundle_source
    assert "registerWindow(managerName, windowEl, {" in bundle_source
    assert bundle_source.count("dispatchCommand(TV_COMMANDS.CLOSE)") >= 3
    assert bundle_source.count("dispatchCommand(TV_COMMANDS.ZOOM)") >= 2
    assert "this.windowManager.closeAll()" not in bundle_source
    assert "this.windowManager.toggleZoom()" not in bundle_source
    assert "setHostWindow(hostWindow, hostWindow ? {" in shell_source
    assert "dispatchCommand(TV_COMMANDS.CLOSE)" in shell_source
    assert "dispatchCommand(TV_COMMANDS.ZOOM)" in shell_source
