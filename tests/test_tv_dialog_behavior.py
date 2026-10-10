from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
ASSET_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/server/converter/assets/tv-core.js"),
)
DIALOG_PATHS = (
    Path("www/assets/tv-dialogs.js"),
    Path("thelpviewer/server/converter/assets/tv-dialogs.js"),
)
GAME_PATHS = (
    Path("www/assets/tv-games.js"),
    Path("thelpviewer/server/converter/assets/tv-games.js"),
)


def test_system_information_is_a_shared_tv_dialog_without_private_layout_css():
    dialogs = DIALOG_PATHS[1].read_text(encoding="utf-8")
    core = ASSET_PATHS[1].read_text(encoding="utf-8")
    bundle = Path("thelpviewer/server/converter/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    shell = Path("thelpviewer/server/converter/assets/tv-shell.js").read_text(encoding="utf-8")

    system_info = dialogs[
        dialogs.index("class TVSystemInformationDialog"):
        dialogs.index("class TVFindDialog")
    ]
    assert "extends TVDialog" in system_info
    assert system_info.count("new TVListBox(") == 2
    assert '"system-information-ok"' in system_info
    assert '"system-information-refresh"' in system_info
    assert "setHelpCtx(hcSystemInformation)" in system_info
    assert "class TVSystemInformationDialog" in dialogs
    assert "hcSystemInformation: 2270" in core
    assert 'dialogItem("System ~I~nformation", "systeminfo")' in bundle
    assert 'this._registerDialog("systeminfo"' in bundle
    assert 'this.registerDialog("systeminfo"' in shell


def test_dynamic_dialog_content_redraws_its_shared_frame():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
    source = ASSET_PATHS[0].read_text(encoding="utf-8")
    draw_content = source[
        source.index("    drawContent() {", source.index("class TVDialog extends TVWindow")):
        source.index("\n    setState(state, enable)", source.index("    drawContent() {", source.index("class TVDialog extends TVWindow")))
    ]
    assert "this.children.forEach((view) => view.resolve?.(body));" in draw_content
    assert "if (this.isOpen())" in draw_content
    assert "updateWindowFrameState(this.dialog, this.isActive(), { dialog: true });" in draw_content


def test_concrete_dialogs_keep_tv_view_references_instead_of_rediscovering_dom():
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    assert GAME_PATHS[0].read_bytes() == GAME_PATHS[1].read_bytes()

    for path in (DIALOG_PATHS[0], GAME_PATHS[0]):
        source = path.read_text(encoding="utf-8")
        assert 'this.query("[data-tv-' not in source
        assert 'this.queryAll("[data-tv-' not in source

    core = ASSET_PATHS[0].read_text(encoding="utf-8")
    assert "class TVEvent" in core
    assert "handleEvent(event)" in core
    assert "target.dispatchEvent(new TVEvent" in core
    assert "class TVRenderer" not in core
    assert "TVRenderer" not in core

    dialogs = DIALOG_PATHS[0].read_text(encoding="utf-8")
    games = GAME_PATHS[0].read_text(encoding="utf-8")
    for source in (dialogs, games):
        assert "constructor(desktop" not in source
        assert 'document.querySelector(".tv-desktop")' not in source
    assert "class TVGameDialog extends TVDialog" in games
    assert "class TVPuzzleDialog extends TVGameDialog" in games
    assert "new TVGroup(" in games
    assert "new TVButton(" in games
    assert "new TVStaticText(" in games


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
    contains(element) { return element === this; }
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
const desktop = new TV.TVDesktop(new TV.TVRect()).bindRoot(document.body);
const manager = desktop.dialogManager;

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
    TV.TVView._fromHTML = () => overlay;
        const instance = new TV.TVDialog(new TV.TVRect(0, 0, 40, 12), "Test");
        if (options.helpCtx) { instance.setHelpCtx(options.helpCtx); }
        if (options.modal) { instance.setState(TV.sfModal, true); }
        if (options.escapeCloses === false) { instance.escapeCloses = false; }
        const defaultView = new TV.TVButton(new TV.TVRect(), "OK", "accept", TV.bfDefault);
        instance.insert(defaultView);
        defaultView.bindRoot(defaultButton);
    desktop.insert(instance);
    return { instance, overlay, dialogElement, first, second, defaultButton, defaultView, closeButton };
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
const regularHandleEvent = regular.instance.handleEvent.bind(regular.instance);
let acceptedCommands = 0;
let escapedCommands = 0;
regular.instance.handleEvent = (tvEvent) => {
    if (tvEvent.what === TV.evCommand && tvEvent.command === "accept") {
        if (tvEvent.infoPtr !== regular.defaultView) { throw new Error("default button lost its TVView source"); }
        acceptedCommands += 1;
        regular.instance.clearEvent(tvEvent);
        return;
    }
    if (tvEvent.what === TV.evCommand && tvEvent.command === "dialog-close") { escapedCommands += 1; }
    regularHandleEvent(tvEvent);
};

const contextual = buildDialog({ helpCtx: TV.TV_HELP_CONTEXTS.hcFind });
if (contextual.overlay.getAttribute("data-tv-help-ctx") !== String(TV.TV_HELP_CONTEXTS.hcFind)
    || contextual.dialogElement.getAttribute("data-tv-help-ctx") !== String(TV.TV_HELP_CONTEXTS.hcFind)) {
    throw new Error("TVDialog did not retain its own help context");
}

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
if (acceptedCommands !== 1 || regular.defaultButton.clicked !== 0 || !enter.defaultPrevented) {
    throw new Error("Enter did not dispatch the default button command");
}

document.activeElement = regular.second;
const tab = keyEvent("Tab", regular.second);
regular.instance.onDialogKeyDown(tab);
if (document.activeElement !== regular.first) { throw new Error("Tab did not wrap focus"); }

const escape = keyEvent("Escape", regular.dialogElement);
regular.instance.onDialogKeyDown(escape);
if (!regular.overlay.hidden || document.activeElement !== launcher || escapedCommands !== 1) {
    throw new Error("Escape did not dispatch Close and restore focus");
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

const frameMarkup = (title, modal, body = "") => {
    const frame = new TV.TVFrame(new TV.TVRect());
    frame.owner = {
        title,
        constructor: { viewName: "dialog" },
        getState: (state) => modal && state === TV.sfModal,
        getPalette: () => "dialog",
    };
    return frame.drawDialog(body, "");
};
const modalMarkup = frameMarkup("Modal", true);
const nonModalMarkup = frameMarkup("Non-modal", false);
    class TestObjectBody extends TV.TVGroup { static role = "object-body"; }
    const objectBody = new TestObjectBody(new TV.TVRect()).insertAll([
        new TV.TVStaticText(new TV.TVRect(), "TV object"),
    ]);
    const objectBodyMarkup = frameMarkup("Object body", false, objectBody);
const objectSectionsMarkup = frameMarkup("Object sections", false, [
        new TV.TVStaticText(new TV.TVRect(), "First"),
        new TV.TVStaticText(new TV.TVRect(), "Second"),
    ]);
const menuItem = new TV.TVMenuItem(
    "~A~bout", "dialog-open", TV.kbF3, TV.TV_HELP_CONTEXTS.hcSystemMenu, "F3",
);
const semanticButtonMarkup = new TV.TVMenuView(new TV.TVRect(), TV.NewMenu(menuItem)).draw("bar");
if (!modalMarkup.includes('aria-modal="true"') || !modalMarkup.includes("is-modal")) {
    throw new Error("modal markup is incomplete");
}
if (!nonModalMarkup.includes('aria-modal="false"')) {
    throw new Error("non-modal markup is incorrectly announced as modal");
}
if (!objectBodyMarkup.includes('class="tv-group tv-object-body"') || !objectBodyMarkup.includes("TV object")) {
    throw new Error("TVFrame did not render a TV object body");
}
if (!objectSectionsMarkup.includes("First") || !objectSectionsMarkup.includes("Second")
    || !objectSectionsMarkup.includes("tv-border-separator")) {
    throw new Error("TVFrame did not render TV object sections");
}
        if (!semanticButtonMarkup.includes("tv-menu-item")
            || !semanticButtonMarkup.includes('data-tv-command="dialog-open"')
            || !semanticButtonMarkup.includes('class="tv-hotkey">A</span>bout')
            || !semanticButtonMarkup.includes('class="tv-menu-hotkey">F3</span>')
            || menuItem.keyCode !== TV.kbF3
            || semanticButtonMarkup.includes("data-tv-key-code")
            || !semanticButtonMarkup.includes(`data-tv-help-ctx="${TV.TV_HELP_CONTEXTS.hcSystemMenu}"`)
            || semanticButtonMarkup.includes('aria-expanded=')) {
        throw new Error("TVMenuItem semantic properties did not reach the renderer");
}
const titlebarMarkup = modalMarkup.slice(
    modalMarkup.indexOf('class="tv-dialog-titlebar '),
    modalMarkup.indexOf('class="tv-dialog-body ')
);
if ((titlebarMarkup.match(/data-tv-border-fill=/g) || []).length !== 1) {
    throw new Error("dialog title frame is not a single continuous line");
}

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
let managedCloseCommands = 0;
const managedHandleEvent = managedDialog.instance.handleEvent.bind(managedDialog.instance);
managedDialog.instance.handleEvent = (tvEvent) => {
    if (tvEvent.what === TV.evCommand && tvEvent.command === "dialog-close") {
        managedCloseCommands += 1;
    }
    managedHandleEvent(tvEvent);
};
managedDialog.instance.bindCommonClose(() => {
    dialogCloseCalls += 1;
    managedDialog.instance.close();
});
manager.register("managed-dialog", managedDialog.instance);
managedDialog.instance.open();
managedDialog.overlay.listeners.get("click")({ target: managedDialog.overlay, type: "click" });
if (dialogCloseCalls !== 1 || !managedDialog.overlay.hidden) {
    throw new Error("overlay click did not close through the dialog event path");
}
managedDialog.instance.open();
if (managedDialog.closeButton.hidden) {
    throw new Error("active dialog close control is hidden");
}
TV.updateWindowFrameState(managedDialog.dialogElement, false, { dialog: true });
if (managedDialog.closeButton.hidden
    || !managedDialog.closeButton.classList.contains("is-frame-control-passive")
    || managedDialog.closeButton.getAttribute("aria-disabled") !== null) {
    throw new Error("inactive dialog close control is not visible and passive");
}
TV.updateWindowFrameState(managedDialog.dialogElement, true, { dialog: true });
if (!manager.dispatchCommand(TV.TV_COMMANDS.CLOSE) || dialogCloseCalls !== 2 || managedCloseCommands !== 1) {
    throw new Error("active dialog did not receive Close");
}
managedDialog.instance.open();
if (!manager.dispatchCommand(TV.TV_COMMANDS.CANCEL) || dialogCloseCalls !== 3 || managedCloseCommands !== 2) {
    throw new Error("active dialog did not receive Cancel through its command path");
}
managedDialog.instance.destroy();
if (manager.get("managed-dialog") !== null || managedDialog.overlay.isConnected || managedDialog.instance.owner !== null) {
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
        Path("thelpviewer/server/converter/assets/tv-dialogs.js"),
    )
    assert dialog_paths[0].read_bytes() == dialog_paths[1].read_bytes()
    source = dialog_paths[0].read_text(encoding="utf-8")
    calculator = source[source.index("class TVCalculatorDialog"):source.index("class TVCalendarDialog")]
    assert "this.escapeCloses = false" in calculator


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


def test_calendar_matches_dos_navigator_geometry_and_navigation():
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    source = DIALOG_PATHS[0].read_text(encoding="utf-8")
    calendar = source[source.index("class TVCalendarView"):source.index("class TVColorSelector")]
    assert 'new TVRect(0, 0, 30, 10), "Calendar"' in calendar
    assert 'new TVRect(0, 2, 28, 8)' in calendar
    assert '"Mo  Tu  We  Th  Fr  Sa  Su  "' in calendar
    assert '"calendar-today"' in calendar
    assert "this.changeDay(-7)" in calendar
    assert "this.changeDay(7)" in calendar
    assert "this.changeYear(-1)" in calendar
    assert "this.changeYear(1)" in calendar


def test_close_and_zoom_commands_are_routed_to_the_active_target():
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    shell_paths = (
        Path("www/assets/tv-shell.js"),
        Path("thelpviewer/server/converter/assets/tv-shell.js"),
    )
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert shell_paths[0].read_bytes() == shell_paths[1].read_bytes()

    bundle_source = bundle_paths[0].read_text(encoding="utf-8")
    shell_source = shell_paths[0].read_text(encoding="utf-8")
    assert 'registerWindow("help:" + key, windowEl, {' in bundle_source
    assert "registerWindow(managerName, windowEl, {" in bundle_source
    assert bundle_source.count("dispatchCommand(TV_COMMANDS.CLOSE)") >= 2
    assert bundle_source.count("dispatchCommand(TV_COMMANDS.ZOOM)") >= 1
    assert "kbF5" in bundle_source
    assert "kbF6" in bundle_source
    assert "kbShiftF6" in bundle_source
    assert "kbAltF3" in bundle_source
    assert "_handleMenuShortcut" not in bundle_source
    assert "this.windowManager.closeAll()" not in bundle_source
    assert "this.windowManager.toggleZoom()" not in bundle_source
    assert "setHostWindow(hostWindow, hostWindow ? {" in shell_source
    assert "dispatchCommand(TV_COMMANDS.CLOSE)" in shell_source
    assert "dispatchCommand(TV_COMMANDS.ZOOM)" in shell_source
