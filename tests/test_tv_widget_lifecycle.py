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

const core = fs.readFileSync(process.argv[1], "utf8");
const scrollbarStart = core.indexOf("class TVScrollBar");
const scrollbarEnd = core.indexOf("\nconst TurboVisionScrollbar", scrollbarStart);
eval(core.slice(scrollbarStart, scrollbarEnd) + "\nglobalThis.TestScrollbar = TVScrollBar;");
TestScrollbar.prototype.update = function () { this.updateCalls = (this.updateCalls || 0) + 1; };

const viewport = new FakeTarget();
viewport.firstElementChild = new FakeTarget();
const x = buildAxis();
const y = buildAxis();
const host = new FakeTarget();
host.querySelector = (selector) => selector === ".tv-scrollbar-x" ? x.root : y.root;
const frame = new FakeTarget();
frame.closest = (selector) => selector === ".tv-client-row" ? host : null;
frame.parentElement = host;
frame.querySelector = (selector) => selector === "[data-tv-viewport]" ? viewport : null;

const scrollbar = new TestScrollbar(new TVRect()).bindRoot(frame);
if (!viewport.listeners.has("scroll") || !window.listeners.has("resize") || !document.listeners.has("mouseup")) {
    throw new Error("scrollbar did not bind its global resources");
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
if (viewport.listeners.has("scroll") || window.listeners.has("resize") || document.listeners.has("mouseup")) {
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
    assert "this._destroyWindowWidgets(existing);\n            existing.remove();" in source
    assert "this._destroyWindowWidgets(el);\n            el.remove();" in source
    assert "destroyWindowWidgets(windowEl);\n            windowEl.remove();" in source
    assert "(existing._tvScrollbars || []).forEach((scrollbar) => scrollbar.refresh())" in source


def test_temporary_dialogs_use_the_shared_destroy_lifecycle():
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    bundle = BUNDLE_PATHS[0].read_text(encoding="utf-8")
    games = Path("www/assets/tv-games.js").read_text(encoding="utf-8")

    assert "this.manager.unregister(this.managerName, this)" in core
    assert "this.dialog.destroy();" in bundle
    assert bundle.count("dialog.destroy();") >= 3
    assert "dlg.destroy();" in games
    assert "dialog.overlay.remove();" not in bundle
    assert "dlg.overlay.remove();" not in games


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
    assert ".tv-vlist-scrollbar.is-inactive" in css
    inactive_scrollbar_css = css[
        css.index(".tv-scrollbar.is-inactive"):
        css.index(".tv-js .tv-scrollbar")
    ]
    inactive_list_start = css.index(".tv-vlist-scrollbar.is-inactive")
    inactive_list_css = css[
        inactive_list_start:
        css.index(".tv-vlist-track", inactive_list_start)
    ]
    assert "--tv-frame-passive" not in inactive_scrollbar_css
    assert "--tv-frame-passive" not in inactive_list_css
    assert "pointer-events: none" in inactive_scrollbar_css
    assert "pointer-events: none" in inactive_list_css
