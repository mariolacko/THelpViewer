from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/server/converter/assets/tv-core.js"),
)
SHELL_PATHS = (
    Path("www/assets/tv-shell.js"),
    Path("thelpviewer/server/converter/assets/tv-shell.js"),
)
BUNDLE_PATHS = (
    Path("www/assets/tv-bundle-app.js"),
    Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
)
CONTEXT_HELP_PATHS = (
    Path("www/assets/tv-context-help.js"),
    Path("thelpviewer/server/converter/assets/tv-context-help.js"),
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
const attrsToString = (attrs) => Object.entries(attrs).map(([key, value]) => `${key}="${value}"`).join(" ");
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
if (!bar.draw().includes("░░░░░░░░░░")) throw new Error("empty track is not shaded");
bar.updateView(40);
const markup = bar.draw();
if (!markup.includes("████░░░░░░")) throw new Error(`unexpected bar: ${markup}`);
if (!markup.includes('role="progressbar"') || !markup.includes('aria-valuenow="40"')) {
    throw new Error(`progress semantics missing: ${markup}`);
}
bar.updateView(100);
if (!bar.draw().includes("██████████")) throw new Error("completed track is not solid");
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
    assert "new TVWindow(new TVRect(), document.title).bindRoot(hostWindow)" in shell
    assert 'hostWindow.querySelector(".tv-close-control")?.click()' not in shell
    assert "bindActions()" not in shell
    assert "class TVGameDialog extends TVDialog" in games
    assert 'event.command === "hall-of-fame"' in games
    assert "class TVWindow extends TVGroup" in core
    assert 'event.command === "window-close"' in core
    assert 'event.command === "window-zoom"' in core
    assert "_bindCloseButton(" not in bundle
    assert "_bindZoomButton(" not in bundle
    assert "onDialogKeyDown(event)" not in dialogs


@pytest.mark.skipif(NODE is None, reason="Node.js is required for index monitoring tests")
def test_global_index_monitor_keeps_polling_and_ignores_stale_or_destroyed_requests():
    paths = [Path("www/assets/tv-dialogs.js"), Path("thelpviewer/server/converter/assets/tv-dialogs.js")]
    assert paths[0].read_bytes() == paths[1].read_bytes()
    script = r'''
const fs = require("fs"), assert = require("node:assert/strict");
const source = fs.readFileSync(process.argv[1], "utf8");
class TVDialog { destroy() { this.destroyed = true; } }
const start = source.indexOf("class TVSearchDialog");
eval(source.slice(start, source.indexOf("Object.assign(TV,", start)) + "\nglobalThis.Search = TVSearchDialog;");
const timers = new Map(); let nextTimer = 0;
global.setTimeout = (callback, delay) => { timers.set(++nextTimer, { callback, delay }); return nextTimer; };
global.clearTimeout = (id) => timers.delete(id);
const make = () => {
    const search = Object.create(Search.prototype);
    Object.assign(search, { indexMonitorSerial: 0, indexMonitorTimer: null, indexProgress: null,
        indexStatus: { state: "idle" }, searchSerial: 0, availabilitySerial: 0, statuses: [],
        onIndexStatus(status) { this.statuses.push(status); }, isOpen() { return false; },
        showIndexProgress() {
            this.indexProgress ||= { values: [], update(status) { this.values.push(status); }, destroy() { this.destroyed = true; } };
        },
    });
    return search;
};
const response = (state, percent = 0) => ({ ok: true, status: 200, async json() { return { state, percent }; } });
const onlyTimer = (delay) => {
    assert.equal(timers.size, 1);
    assert.equal([...timers.values()][0].delay, delay);
};
(async () => {
    const waitingSearch = make();
    let refreshed = 0;
    Object.assign(waitingSearch, { indexSearchPending: true, isOpen: () => true, isGlobal: () => true,
        input: { getData: () => "compiler" }, renderResults: () => { refreshed += 1; } });
    global.fetch = async () => response("ready", 100);
    await waitingSearch.monitorIndex();
    assert.equal(refreshed, 1, "a fast build finishing before progress opens did not refresh pending results");
    await waitingSearch.monitorIndex();
    assert.equal(refreshed, 1, "idle polling reset a completed search");
    waitingSearch.destroy();
    assert.equal(timers.size, 0);
    const search = make();
    global.fetch = async () => response("ready", 100);
    await search.monitorIndex();
    onlyTimer(5000);
    assert.equal(search.indexProgress, null);
    global.fetch = async () => response("building", 37);
    await search.monitorIndex();
    onlyTimer(250);
    assert.deepEqual(search.indexStatus, { state: "building", percent: 37 });
    const progress = search.indexProgress;
    global.fetch = async () => response("paused", 37);
    await search.monitorIndex();
    onlyTimer(1000);
    assert.equal(search.indexStatus.state, "paused");
    assert.equal(search.indexProgress, progress, "pause discarded the existing progress window");
    global.fetch = async () => response("ready", 100);
    await search.monitorIndex();
    onlyTimer(600);
    assert.equal(progress.values[0].percent, 100);
    const [id, timer] = timers.entries().next().value;
    timers.delete(id); timer.callback();
    onlyTimer(5000);
    assert.equal(progress.destroyed, true);
    assert.equal(search.indexProgress, null);

    global.fetch = async () => { throw new Error("offline"); };
    await search.monitorIndex();
    onlyTimer(5000);
    assert.equal(search.indexStatus.state, "unavailable");
    global.fetch = async () => ({ ok: false, status: 404 });
    await search.monitorIndex();
    assert.equal(timers.size, 0, "static exports must not poll a missing API forever");

    const pending = [];
    global.fetch = () => new Promise((resolve) => pending.push(resolve));
    const older = search.monitorIndex(), newer = search.monitorIndex();
    pending[1](response("ready", 100)); await newer;
    pending[0](response("building", 20)); await older;
    onlyTimer(5000);
    assert.equal(search.indexStatus.state, "ready", "stale request replaced current status");
    const inFlight = search.monitorIndex();
    search.destroy();
    const count = search.statuses.length;
    pending[2](response("building", 50)); await inFlight;
    assert.equal(search.statuses.length, count);
    assert.equal(timers.size, 0, "destroy left an index monitor alive");
})().catch((error) => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run([NODE, "-e", script, str(paths[0])], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for catalog menu tests")
def test_catalog_menu_collapses_only_single_file_levels_and_keeps_versions_and_targets():
    assert BUNDLE_PATHS[0].read_bytes() == BUNDLE_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
const assert = require("node:assert/strict");
const core = fs.readFileSync(process.argv[1], "utf8");
const app = fs.readFileSync(process.argv[2], "utf8");
const kbNoKey = 0, hcNoContext = 0;
const normalizeHelpContext = (context) => context;
const viewerUrl = (target) => "/?" + new URLSearchParams(target);
const bundleLoadingLabel = (entry) => entry.name;
eval(core.slice(core.indexOf("class TVMenu {"), core.indexOf("class TVMenuView"))
    + core.slice(core.indexOf("class TVMenuItem {"), core.indexOf("class TVMenuBar"))
    + app.slice(app.indexOf("const menuActions = new WeakMap()"), app.indexOf("function buildDocsMenuItems"))
    + "\nglobalThis.buildMenu = buildCatalogMenuItems;");

const entry = (file, product, version, name = "Reference") => ({
    file, product_name: product, version, name,
});
const files = (catalog) => buildMenu(catalog).filter((item) =>
    !item.separator && !["file-open", "dialog-open"].includes(item.command));
const checkTarget = (item, file) => {
    assert.equal(item.command, "bundle-open");
    assert.equal(item.subMenu, null);
    assert.equal(new URL(item.getUrl(), "https://example.test").searchParams.get("file"), file);
};

assert.deepEqual(files([]), []);
const single = files([entry("C++ 7/help.json.gz", "Compiler", "7.0")]);
assert.equal(single.length, 1);
assert.equal(single[0].name, "Compiler 7.0");
checkTarget(single[0], "C++ 7/help.json.gz");
const unknown = files([entry("guide.json.gz", "Guide", "")]);
assert.equal(unknown[0].name, "Guide");
checkTarget(unknown[0], "guide.json.gz");

const releases = [entry("asm10.json.gz", "Assembler", "10.0"),
    entry("asm2.json.gz", "Assembler", "2.0"),
    entry("asm201.json.gz", "Assembler", "2.01")];
const original = JSON.stringify(releases);
const editions = files(releases)[0].subMenu.entries();
assert.deepEqual(editions.map((item) => item.name), ["2.0", "2.01", "10.0"]);
editions.forEach((item, index) => checkTarget(item,
    ["asm2.json.gz", "asm201.json.gz", "asm10.json.gz"][index]));
assert.equal(JSON.stringify(releases), original, "menu must not rewrite catalog metadata");

const mixed = files([entry("single.json.gz", "Compiler", "1.0"),
    entry("v2/c.json.gz", "Compiler", "2.0"),
    entry("v2/cpp.json.gz", "Compiler", "2.0")])[0].subMenu.entries();
assert.deepEqual(mixed.map((item) => item.name), ["1.0", "2.0"]);
checkTarget(mixed[0], "single.json.gz");
const multi = mixed[1].subMenu.entries();
assert.deepEqual(multi.map((item) => item.name), ["Reference (c)", "Reference (cpp)"]);
multi.forEach((item, index) => checkTarget(item, ["v2/c.json.gz", "v2/cpp.json.gz"][index]));

const sameEdition = files([entry("a.json.gz", "Compiler", "2.0", "Language"),
    entry("b.json.gz", "Compiler", "2.0", "Library")])[0];
assert.equal(sameEdition.name, "Compiler");
assert.equal(sameEdition.subMenu.entries()[0].name, "2.0");
assert.equal(sameEdition.subMenu.entries()[0].subMenu.entries().length, 2);

const unversioned = files([entry("a.json.gz", "Guides", "", "First"),
    entry("b.json.gz", "Guides", "", "Second"),
    entry("c.json.gz", "Guides", "1.0")])[0].subMenu.entries();
assert.deepEqual(unversioned.map((item) => item.name), ["First", "Second", "", "1.0"]);
assert.equal(unversioned[2].separator, true);
checkTarget(unversioned[3], "c.json.gz");
const standalone = files([entry("solo.json.gz", "", "", "Standalone")])[0];
assert.equal(standalone.name, "Standalone");
checkTarget(standalone, "solo.json.gz");
'''
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0]), str(BUNDLE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the widget lifecycle test")
def test_scrollbar_and_resizer_destroy_global_resources():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    assert SHELL_PATHS[0].read_bytes() == SHELL_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeTarget {
    constructor() {
        this.listeners = new Map();
        this.captures = new Map();
        this.attributes = new Map();
        const styleValues = new Map();
        this.style = {
            setProperty(name, value) { styleValues.set(name, String(value)); },
            getPropertyValue(name) { return styleValues.get(name) || ""; },
        };
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
    addEventListener(type, handler, capture = false) { this.listeners.set(type, handler); this.captures.set(type, capture); }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) || null; }
    removeEventListener(type, handler) {
        if (this.listeners.get(type) === handler) { this.listeners.delete(type); this.captures.delete(type); }
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
global.getComputedStyle = (target) => target.style;
global.measureCells = () => ({ width: 8, height: 16 });
global.fillBorders = () => {};
global.updateWindowFrameState = () => {};
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
host.querySelector = (selector) => {
    if (selector === ":scope > .tv-scrollbar-x, :scope > .tv-bottom-bar > .tv-scrollbar-x") { return x.root; }
    if (selector === ":scope > .tv-scrollbar-y, :scope > .tv-bottom-bar > .tv-scrollbar-y") { return y.root; }
    return null;
};
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
global.sfDragging = 0x0080;
const ownedView = { state: 0, setState(mask, enable) { this.state = enable ? this.state | mask : this.state & ~mask; } };
windowElement._tvView = ownedView;
windowElement.style.setProperty("--tv-window-cols", "80");
windowElement.style.setProperty("--tv-window-rows", "25");
const zoomGlyph = { textContent: "↓" };
windowElement.closest = () => desktop;
windowElement.querySelector = (selector) => {
    if (selector === "[data-tv-move-handle]") { return moveHandle; }
    if (selector === "[data-tv-resize-handle]") { return resizeHandle; }
    if (selector === "[data-tv-zoom-glyph]") { return zoomGlyph; }
    return null;
};

const resizer = new TestResizer(windowElement);
if (!resizeHandle.listeners.has("mousedown") || !moveHandle.listeners.has("mousedown") || !window.listeners.has("beforeunload")) {
    throw new Error("resizer did not bind its resources");
}
const readStoredState = resizer.readStoredState;
for (const [state, expectedLeft, expectedTop] of [
    [{ left: 16, top: 32, cols: 70, rows: 20 }, 16, 32],
    [{ left: 424, top: 6069, cols: 70, rows: 20 }, 424, 475],
    [{ left: 9999, top: 9999, cols: 70, rows: 20 }, 720, 475],
    [{ left: 9999, top: 9999, cols: 70, rows: 20,
        restore: { left: 24, top: 48, cols: 60, rows: 18 } }, 24, 48],
    [{ left: 0, top: 0, cols: 70, rows: 20, maximized: true,
        restore: { left: 9999, top: 9999, cols: 70, rows: 20 } }, 720, 475],
]) {
    resizer.readStoredState = () => state;
    if (!resizer.restoreState() || resizer.restoreSnapshot.left !== expectedLeft
        || resizer.restoreSnapshot.top !== expectedTop) {
        throw new Error("saved window geometry was not constrained to its desktop");
    }
    if (state.maximized) { resizer.restore(false); }
    if (resizer.captureGeometry().left !== expectedLeft || resizer.captureGeometry().top !== expectedTop) {
        throw new Error("restored/maximized window lost its constrained restore position");
    }
}
desktop.clientWidth = 40; desktop.clientHeight = 20;
resizer.readStoredState = () => ({ left: 100, top: 100, cols: 70, rows: 20 });
resizer.restoreState();
if (resizer.restoreSnapshot.left !== 0 || resizer.restoreSnapshot.top !== 0) {
    throw new Error("oversized window produced negative restore bounds");
}
desktop.clientWidth = 800; desktop.clientHeight = 500;
resizer.readStoredState = readStoredState;
resizer.setMoveFrame(true);
if (!windowElement.classList.contains("is-moving")) {
    throw new Error("move frame state was not preserved");
}
windowElement.classList.add("is-maximized");
resizer.place({ left: 16, top: 32, cols: 70, rows: 20 });
if (windowElement.classList.contains("is-maximized") || zoomGlyph.textContent !== "↑"
    || windowElement.style.getPropertyValue("--tv-window-cols") !== "70"
    || resizer.restoreSnapshot.left !== 16 || resizer.restoreSnapshot.rows !== 20) {
    throw new Error("window layout did not update resizer geometry and restore state");
}
resizer.setMoveFrame(false);
if (windowElement.classList.contains("is-moving")) {
    throw new Error("move frame state was not cleared");
}
resizer.maximize(false);
resizer.restoreDefaultSize();
let defaults = resizer.captureGeometry();
if (defaults.cols !== 80 || defaults.rows !== 25 || defaults.left !== 16 || defaults.top !== 32
    || windowElement.classList.contains("is-maximized") || zoomGlyph.textContent !== "↑") {
    throw new Error("default size used saved geometry or lost the pre-zoom position");
}
desktop.clientWidth = 32; desktop.clientHeight = 16;
resizer.restoreDefaultSize();
defaults = resizer.captureGeometry();
if (defaults.cols > 4 || defaults.rows > 1 || defaults.left < 0 || defaults.top < 0
    || defaults.left + defaults.cols * 8 > desktop.clientWidth
    || defaults.top + defaults.rows * 16 > desktop.clientHeight) {
    throw new Error("default size escaped a small desktop");
}
desktop.clientWidth = 800; desktop.clientHeight = 500;
resizer.place({ left: 16, top: 32, cols: 70, rows: 20 });
const animationFrames = new Map();
let frameNumber = 0, widthReads = 0, heightReads = 0;
window.requestAnimationFrame = (callback) => { animationFrames.set(++frameNumber, callback); return frameNumber; };
window.cancelAnimationFrame = (id) => animationFrames.delete(id);
Object.defineProperty(windowElement, "offsetWidth", { get() { widthReads++; return 80; } });
Object.defineProperty(windowElement, "offsetHeight", { get() { heightReads++; return 25; } });
resizer.startMove({ clientX: 10, clientY: 20, target: { closest() { return null; } }, preventDefault() {} });
if (!(ownedView.state & sfDragging) || !document.captures.get("mousemove") || !document.captures.get("mouseup")) {
    throw new Error("move did not acquire TV dragging state and capture-phase mouse tracking");
}
widthReads = heightReads = 0;
for (let i = 0; i < 50; i++) { resizer.onMoveDrag({ clientX: 100 + i, clientY: 200 + i }); }
if (animationFrames.size !== 1 || widthReads || heightReads
    || windowElement.style.getPropertyValue("--tv-window-left") !== "16px") {
    throw new Error("drag did not coalesce writes or cached bounds were reread");
}
const [frameId, apply] = animationFrames.entries().next().value;
animationFrames.delete(frameId); apply();
if (windowElement.style.getPropertyValue("--tv-window-left") !== "155px") {
    throw new Error("drag did not apply the latest queued position");
}
resizer.onMoveEnd({ clientX: 110, clientY: 220, buttons: 0 });
if (animationFrames.size || windowElement.style.getPropertyValue("--tv-window-left") !== "116px"
    || windowElement.style.getPropertyValue("--tv-window-top") !== "232px"
    || resizer.restoreSnapshot.left !== 116 || resizer.restoreSnapshot.top !== 232) {
    throw new Error("drag did not flush and persist the final mouse-up position");
}
if (ownedView.state & sfDragging) { throw new Error("move left sfDragging set"); }
for (const reason of ["release", "blur"]) {
    resizer.startMove({ clientX: 10, clientY: 20, target: { closest() { return null; } }, preventDefault() {} });
    if (reason === "release") { resizer.onMoveDrag({ buttons: 0 }); }
    else { window.listeners.get("blur")(); }
    if (resizer.moveState || (ownedView.state & sfDragging) || windowElement.classList.contains("is-moving")) {
        throw new Error(`${reason} left a stuck move`);
    }
}
resizer.moveState = { startX: 0, startY: 0, startLeft: 0, startTop: 0, maxLeft: 720, maxTop: 475 };
resizer.onMoveDrag({ clientX: 9999, clientY: 9999 });
if (resizer.moveState.nextLeft !== 720 || resizer.moveState.nextTop !== 475) {
    throw new Error("cached drag bounds did not clamp the position");
}
resizer.destroy();
resizer.destroy();
if (animationFrames.size) { throw new Error("destroy left a queued drag frame behind"); }
if (windowElement._tvResizer) { throw new Error("destroy left a stale resizer reference"); }
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
    assert "const scrollbars = windowView?.scrollbars || []" in source
    assert "windowView.outline = outline" in source
    assert "const target = buildBundleTargetData(node)" in source
    assert "void this._openTopicTarget(windowEl, target)" in source
    assert "_tvOutline" not in source
    assert "_tvScrollbars" not in source
    assert "_tvEditor" not in source
    assert "_tvFindEditor" not in source
    assert "windowView.editor = editor.bindRoot" in source
    assert "windowView.findEditor = editor" in source
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
    assert "helpWindow.setContent(contentHTML, textScreens)" in bundle
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
    assert "this.insert(this.desktopView);" in shell
    assert "this.insert(this.desktopView);" in bundle


def test_active_window_state_controls_scrollbars_and_scopes_frame_redraw():
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    shell = SHELL_PATHS[0].read_text(encoding="utf-8")
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/server/converter/assets/turbovision.css"),
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
