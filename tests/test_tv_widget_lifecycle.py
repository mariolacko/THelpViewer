from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)
SHELL_PATHS = (
    Path("www/assets/tv-shell.js"),
    Path("thelpviewer/converter/assets/tv-shell.js"),
)
BUNDLE_PATHS = (
    Path("www/assets/tv-bundle-app.js"),
    Path("thelpviewer/converter/assets/tv-bundle-app.js"),
)
CONTEXT_HELP_PATHS = (
    Path("www/assets/tv-context-help.js"),
    Path("thelpviewer/converter/assets/tv-context-help.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for gauge behavior tests")
def test_dos_navigator_gauges_receive_broadcast_progress_commands():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVPercentGauge");
const end = source.indexOf("\nclass TVLabel", start);
const evBroadcast = 0x0200;
const cmUpdateGauge = 12000;
const cmResetGauge = 12001;
const cmAddGauge = 12002;
class TVRect {
    constructor(x1 = 0, y1 = 0, x2 = 0, y2 = 0) { this.x1 = x1; this.y1 = y1; this.x2 = x2; this.y2 = y2; }
    get width() { return this.x2 - this.x1; }
}
class TVView {
    constructor(bounds) { this.bounds = bounds; this.size = { x: bounds.width }; this.eventMask = 0; this.root = null; }
    handleEvent() {}
    drawView() { this.drawCount = (this.drawCount || 0) + 1; return this; }
    _drawAttrs(attrs) { return attrs; }
    static _viewBoundsStyle() { return ""; }
}
const attrsToString = () => "";
const escapeHtml = (value) => String(value);
eval(source.slice(start, end) + "\nglobalThis.PercentGauge = TVPercentGauge; globalThis.BarGauge = TVBarGauge;");

const percent = new PercentGauge(new TVRect(0, 0, 5, 1), 200);
percent.handleEvent({ what: evBroadcast, command: cmUpdateGauge, infoLong: 50 });
if (percent.curValue !== 50 || !percent.draw().includes("25 %")) throw new Error("update failed");
percent.handleEvent({ what: evBroadcast, command: cmAddGauge, infoLong: 25 });
if (percent.curValue !== 75) throw new Error("add failed");
percent.handleEvent({ what: evBroadcast, command: cmResetGauge, infoLong: 300 });
if (percent.maxValue !== 300 || percent.curValue !== 0) throw new Error("reset failed");

const bar = new BarGauge(new TVRect(0, 0, 10, 1), 100);
bar.updateView(40);
const markup = bar.draw();
if (!markup.includes("▓▓▓▓░░░░░░")) throw new Error(`unexpected bar: ${markup}`);
'''
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_application_commands_use_tvision_handle_event_flow():
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    shell = SHELL_PATHS[0].read_text(encoding="utf-8")
    bundle = BUNDLE_PATHS[0].read_text(encoding="utf-8")
    dialogs = Path("www/assets/tv-dialogs.js").read_text(encoding="utf-8")
    games = Path("www/assets/tv-games.js").read_text(encoding="utf-8")

    assert 'new TVMenuController({ commandTarget: this })' in bundle
    assert "this.menus.commandTarget = this" in shell
    assert "class TVApplication extends TVProgram" in shell and "handleEvent(event)" in shell
    assert "bindActions()" not in shell
    assert "class TVGameDialog extends TVDialog" in games
    assert 'event.command === "hall-of-fame"' in games
    assert "class TVWindow extends TVGroup" in core
    assert 'event.command === "window-close"' in core
    assert 'event.command === "window-zoom"' in core
    assert "_bindCloseButton(" not in bundle
    assert "_bindZoomButton(" not in bundle
    assert "onDialogKeyDown(event)" not in dialogs


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the widget lifecycle test")
def test_scrollbar_and_resizer_destroy_global_resources():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    assert SHELL_PATHS[0].read_bytes() == SHELL_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeTarget {
    constructor() {
        this.listeners = new Map();
        this.attributes = new Map();
        this.style = { setProperty() {} };
        this.dataset = {};
        this.isConnected = true;
        this.clientWidth = 80;
        this.clientHeight = 25;
        this.scrollWidth = 80;
        this.scrollHeight = 25;
        this.scrollLeft = 0;
        this.scrollTop = 0;
        this.offsetWidth = 80;
        this.offsetHeight = 25;
        this.offsetLeft = 0;
        this.offsetTop = 0;
        this.firstElementChild = null;
        const classes = new Set();
        this.classList = {
            add(name) { classes.add(name); },
            remove(name) { classes.delete(name); },
            contains(name) { return classes.has(name); },
            toggle(name, force) {
                const enabled = force === undefined ? !classes.has(name) : Boolean(force);
                if (enabled) { classes.add(name); } else { classes.delete(name); }
                return enabled;
            },
        };
    }
    addEventListener(type, handler) { this.listeners.set(type, handler); }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) || null; }
    removeEventListener(type, handler) {
        if (this.listeners.get(type) === handler) { this.listeners.delete(type); }
    }
    querySelectorAll() { return []; }
}

function buildAxis() {
    const root = new FakeTarget();
    const parts = {
        "[data-role='track']": new FakeTarget(),
        "[data-role='cells']": new FakeTarget(),
        "[data-role='thumb']": new FakeTarget(),
        "[data-role='backward']": new FakeTarget(),
        "[data-role='forward']": new FakeTarget(),
    };
    root.querySelector = (selector) => parts[selector];
    return { root, parts };
}

const windowTarget = new FakeTarget();
windowTarget.location = { pathname: "/viewer/index.html" };
windowTarget.localStorage = { getItem() { return null; }, setItem() {} };
windowTarget.dispatchEvent = () => {};
global.window = windowTarget;
global.document = new FakeTarget();
global.CustomEvent = class {};
global.getComputedStyle = () => ({ getPropertyValue() { return ""; } });
global.measureCells = () => ({ width: 8, height: 16 });
global.fillBorders = () => {};
global.SCROLL_REPEAT_MS = 100;
global.TRACK_CHAR = "░";
global.DISABLED_TRACK_CHAR = "─";
global.THUMB_CHAR = "█";
global.TVRect = class {};
global.TVView = class {
    constructor() { this.root = null; }
    bindRoot(root) { this.root = root; return this; }
};

let observer;
class FakeResizeObserver {
    constructor() { this.observed = []; this.disconnected = 0; observer = this; }
    observe(target) { this.observed.push(target); }
    disconnect() { this.disconnected += 1; this.observed = []; }
}
global.ResizeObserver = FakeResizeObserver;
window.ResizeObserver = FakeResizeObserver;
global.sbHorizontal = 0x0000;

const core = fs.readFileSync(process.argv[1], "utf8");
const scrollbarStart = core.indexOf("class TVScrollBar");
const scrollbarEnd = core.indexOf("\nclass TVProgram", scrollbarStart);
eval(core.slice(scrollbarStart, scrollbarEnd) + "\nglobalThis.TestScrollbar = TVScrollBar;");
TestScrollbar.prototype.update = function () { this.updateCalls = (this.updateCalls || 0) + 1; };

const viewport = new FakeTarget();
viewport.firstElementChild = new FakeTarget();
viewport.scrollHeight = 100;
const x = buildAxis();
const y = buildAxis();
const host = new FakeTarget();
host.querySelector = (selector) => selector === ".tv-scrollbar-x" ? x.root : y.root;
const frame = new FakeTarget();
frame.closest = (selector) => selector === ".tv-client-row" ? host : null;
frame.parentElement = host;
frame.querySelector = (selector) => selector === "[data-tv-viewport]" ? viewport : null;
const logicalOwner = {};
frame._tvView = logicalOwner;

const scrollbar = new TestScrollbar(new TVRect()).bindRoot(frame);
if (frame._tvView !== logicalOwner) {
    throw new Error("scrollbar replaced the logical TVView owning its frame");
}
if (!viewport.listeners.has("scroll") || !frame.listeners.has("wheel")
    || !window.listeners.has("resize") || !document.listeners.has("mouseup")) {
    throw new Error("scrollbar did not bind its global resources");
}
let wheelPrevented = false;
let wheelStopped = false;
frame.listeners.get("wheel")({
    deltaX: 0,
    deltaY: 1,
    deltaMode: 1,
    preventDefault() { wheelPrevented = true; },
    stopPropagation() { wheelStopped = true; },
});
if (!wheelPrevented || !wheelStopped || viewport.scrollTop !== 16) {
    throw new Error(`scrollbar ignored wheel input: ${viewport.scrollTop}`);
}
scrollbar.refresh();
if (!observer || observer.observed.length !== 2) {
    throw new Error("scrollbar did not refresh ResizeObserver targets");
}
let inactivePrevented = false;
scrollbar.setActive(false);
scrollbar.startRepeat({ preventDefault() { inactivePrevented = true; } }, "y", 1);
if (inactivePrevented || scrollbar.repeatTimer !== null || x.root.getAttribute("aria-disabled") !== "true") {
    throw new Error("inactive scrollbar accepted input");
}
scrollbar.setActive(true);
scrollbar.destroy();
scrollbar.destroy();
if (viewport.listeners.has("scroll") || frame.listeners.has("wheel")
    || window.listeners.has("resize") || document.listeners.has("mouseup")) {
    throw new Error("scrollbar left a global listener behind");
}
if (observer.disconnected < 1 || x.parts["[data-role='thumb']"].listeners.has("mousedown")) {
    throw new Error("scrollbar left observer or axis listeners behind");
}

const shell = fs.readFileSync(process.argv[2], "utf8");
const resizerStart = shell.indexOf("class TurboVisionWindowResizer");
const resizerEnd = shell.indexOf("\nclass TurboVisionMenus", resizerStart);
eval(shell.slice(resizerStart, resizerEnd) + "\nglobalThis.TestResizer = TurboVisionWindowResizer;");

const resizeHandle = new FakeTarget();
const moveHandle = new FakeTarget();
const desktop = new FakeTarget();
desktop.clientWidth = 800;
desktop.clientHeight = 500;
const windowElement = new FakeTarget();
windowElement.closest = () => desktop;
windowElement.querySelector = (selector) => {
    if (selector === "[data-tv-move-handle]") { return moveHandle; }
    if (selector === "[data-tv-resize-handle]") { return resizeHandle; }
    return null;
};

const resizer = new TestResizer(windowElement);
if (!resizeHandle.listeners.has("mousedown") || !moveHandle.listeners.has("mousedown") || !window.listeners.has("beforeunload")) {
    throw new Error("resizer did not bind its resources");
}
resizer.setMoveFrame(true);
if (!windowElement.classList.contains("is-moving")) {
    throw new Error("move frame state was not preserved");
}
resizer.setMoveFrame(false);
if (windowElement.classList.contains("is-moving")) {
    throw new Error("move frame state was not cleared");
}
resizer.destroy();
resizer.destroy();
if (resizeHandle.listeners.has("mousedown") || moveHandle.listeners.has("mousedown") || window.listeners.has("beforeunload")) {
    throw new Error("resizer left a listener behind");
}
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0]), str(SHELL_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_dynamic_windows_destroy_widgets_before_removing_the_dom():
    assert BUNDLE_PATHS[0].read_bytes() == BUNDLE_PATHS[1].read_bytes()
    source = BUNDLE_PATHS[0].read_text(encoding="utf-8")

    assert "function destroyWindowWidgets(windowEl)" in source
    assert "scrollbars.forEach((scrollbar) => scrollbar.destroy())" in source
    assert "windowEl._tvResizer.destroy()" in source
    assert "this._destroyWindowWidgets(existing);\n            existing._tvWindowView?.destroy();\n            existing.remove();" in source
    assert "this._destroyWindowWidgets(el);\n            el._tvWindowView?.destroy();\n            el.remove();" in source
    assert "destroyWindowWidgets(windowEl);\n            windowEl.remove();" in source
    context_help = CONTEXT_HELP_PATHS[0].read_text(encoding="utf-8")
    assert 'frame?.querySelector(".tv-scrollbar")?._tvScrollbar?.refresh()' in context_help


def test_help_windows_use_the_tvision_window_and_scroller_hierarchy():
    assert BUNDLE_PATHS[0].read_bytes() == BUNDLE_PATHS[1].read_bytes()
    assert CONTEXT_HELP_PATHS[0].read_bytes() == CONTEXT_HELP_PATHS[1].read_bytes()
    source = CONTEXT_HELP_PATHS[0].read_text(encoding="utf-8")
    bundle = BUNDLE_PATHS[0].read_text(encoding="utf-8")

    assert "class TVHelpViewer extends TVScroller" in source
    assert "class TVHelpWindow extends TVWindow" in source
    assert "this.viewer = this.initViewer(this.getExtent(), bundle)" in source
    assert "this.insert(this.viewer)" in source
    assert "const windowView = new TVHelpWindow(" in bundle
    assert "helpWindow.setContent(contentHTML)" in bundle
    assert "viewport.innerHTML = contentHTML" not in bundle
    assert "TVHelpViewer," in source
    assert "TVHelpWindow," in source
    assert "class TVHelpWindow" not in bundle


def test_temporary_dialogs_use_the_shared_destroy_lifecycle():
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    bundle = BUNDLE_PATHS[0].read_text(encoding="utf-8")
    games = Path("www/assets/tv-games.js").read_text(encoding="utf-8")

    assert "this.manager.unregister(this.managerName, this)" in core
    assert "super.destroy();" in bundle
    assert bundle.count("dialog.destroy();") >= 2
    assert "this.destroy();" in games
    assert "dialog.overlay.remove();" not in bundle
    assert "dlg.overlay.remove();" not in games


def test_applications_follow_the_tvision_program_hierarchy():
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    shell = SHELL_PATHS[0].read_text(encoding="utf-8")
    bundle = BUNDLE_PATHS[0].read_text(encoding="utf-8")

    assert "class TVProgram extends TVGroup" in core
    assert "class TVApplication extends TVProgram" in shell
    assert "class TVBundleApp extends TVProgram" in bundle
    assert "super(new TVRect());" in shell
    assert "super(new TVRect());" in bundle


def test_active_window_state_controls_scrollbars_and_scopes_frame_redraw():
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    shell = SHELL_PATHS[0].read_text(encoding="utf-8")
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/converter/assets/turbovision.css"),
    )
    assert css_paths[0].read_bytes() == css_paths[1].read_bytes()
    css = css_paths[0].read_text(encoding="utf-8")

    frame_state = core[
        core.index("function windowFrameMode"):
        core.index("function fillDesktopPatterns")
    ]
    assert 'windowElement.querySelectorAll(".tv-scrollbar")' in frame_state
    assert "scrollbarWidgets.forEach((scrollbar) => scrollbar.setActive(active))" in frame_state
    assert "listRoot._tvListViewer.setActive(active)" in frame_state
    assert "fillBorders(windowElement)" in frame_state
    assert "fillBorders();" not in frame_state
    assert 'windowElement.classList.contains("is-moving")' in frame_state
    assert '.tv-scrollbar, .tv-menu-bar' not in shell
    assert ".tv-scrollbar.is-inactive" in css
    assert ".tv-vlist-scrollbar.is-inactive" not in css
    inactive_scrollbar_css = css[
        css.index(".tv-scrollbar.is-inactive"):
        css.index(".tv-js .tv-scrollbar")
    ]
    assert "--tv-frame-passive" not in inactive_scrollbar_css
    assert "pointer-events: none" in inactive_scrollbar_css
