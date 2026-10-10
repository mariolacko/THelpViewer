from pathlib import Path
import shutil
import subprocess

import pytest


SAVER_PATHS = (
    Path("www/assets/tv-screensaver.js"),
    Path("thelpviewer/server/converter/assets/tv-screensaver.js"),
)
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for screen saver behavior tests")
def test_screen_saver_restores_focus_and_remeasures_on_resize():
    assert SAVER_PATHS[0].read_bytes() == SAVER_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");

class FakeElement {
    constructor() {
        this.hidden = false;
        this.tabIndex = -1;
        this.clientWidth = 100;
        this.clientHeight = 50;
        this.isConnected = true;
        this.listeners = new Map();
        this.children = [];
        this.style = {};
        this.drawCalls = [];
        this.textContent = "";
        this.innerHTML = "";
    }
    set textContent(value) { this._textContent = value; this.children = []; }
    get textContent() { return this._textContent; }
    appendChild(child) { this.children.push(child); }
    setAttribute() {}
    addEventListener(name, callback) { this.listeners.set(name, callback); }
    focus() { document.activeElement = this; }
    getContext() {
        return {
            fillRect: (...args) => this.drawCalls.push(["fill", ...args]),
            clearRect: (...args) => this.drawCalls.push(["clear", ...args]),
        };
    }
}

class FakeView {
    constructor() { this.eventMask = 1 | 16; }
    bindRoot(root) { this.root = root; }
    dispatchEvent(event) {
        if (this.eventMask & event.what) { this.handleEvent(event); }
    }
    clearEvent(event) { event.what = 0; }
}

const windowListeners = new Map();
const documentListeners = new Map();
let timeoutCallback = null;
let timeoutDelay = null;
global.HTMLElement = FakeElement;
global.window = global;
global.window.addEventListener = (name, callback) => windowListeners.set(name, callback);
global.window.removeEventListener = (name, callback) => {
    if (windowListeners.get(name) === callback) { windowListeners.delete(name); }
};
global.document = {
    activeElement: null,
    body: new FakeElement(),
    createElement: () => new FakeElement(),
    addEventListener(name, callback) { documentListeners.set(name, callback); },
};
global.setInterval = () => 1;
global.clearInterval = () => {};
global.setTimeout = (callback, delay) => {
    timeoutCallback = callback;
    timeoutDelay = delay;
    return 2;
};
global.clearTimeout = () => {};
global.window.THelpViewerTV = {
    TVView: FakeView,
    TVRect: class {},
    TVEvent: class { constructor(what, options) { Object.assign(this, options); this.what = what; } },
    evMouseDown: 1,
    evMouseMove: 4,
    evKeyDown: 16,
    escapeHtml: (value) => String(value),
    measureCells: () => ({ width: 10, height: 10 }),
};

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;
class TestSaver extends TV.TVScreenSaver {
    init() { this.initCount = (this.initCount || 0) + 1; }
    update() { this.updateCount = (this.updateCount || 0) + 1; }
}

const previous = new FakeElement();
document.activeElement = previous;
const saver = new TestSaver();
saver.start();
if (!(saver instanceof TV.TVView) || document.activeElement !== saver.overlay || saver.cols !== 10 || saver.rows !== 5) {
    throw new Error("screen saver did not focus and measure its overlay");
}
saver.overlay.clientWidth = 170;
saver.overlay.clientHeight = 80;
windowListeners.get("resize")();
if (saver.cols !== 17 || saver.rows !== 8 || saver.initCount !== 2 || saver.updateCount !== 2) {
    throw new Error("active screen saver did not remeasure and reinitialize after resize");
}
saver.overlay.listeners.get("mousemove")({ type: "mousemove" });
if (document.activeElement !== previous || TV.TVScreenSaver.active !== null) {
    throw new Error("TVEvent mouse movement did not stop the saver and restore focus");
}
if (windowListeners.has("resize")) {
    throw new Error("screen saver left its resize listener attached");
}

const projector = new TV.TVScreenSaverProjector();
projector.start();
if (projector.overlay.style.background !== "transparent" ||
        projector.canvas.children[0] !== projector.surface ||
        !projector.surface.drawCalls.some(([kind]) => kind === "clear")) {
    throw new Error("projector did not draw a transparent aperture over the page");
}
const oldX = projector.centerX;
const oldY = projector.centerY;
projector.update();
projector.update();
if (projector.centerX === oldX && projector.centerY === oldY) {
    throw new Error("projector aperture did not move");
}
projector.overlay.clientWidth = 150;
projector.overlay.clientHeight = 70;
windowListeners.get("resize")();
if (projector.surface.width !== 150 || projector.surface.height !== 70 ||
        projector.cols !== 15 || projector.rows !== 7 ||
        !projector.surface.drawCalls.some(([kind]) => kind === "clear")) {
    throw new Error("projector did not redraw its aperture after resize");
}
projector.overlay.listeners.get("keydown")({ type: "keydown", key: "Escape" });
if (TV.TVScreenSaver.active || projector.overlay.style.background !== "" ||
        projector.canvas.children.length || document.activeElement !== previous) {
    throw new Error("projector did not clean up and restore focus on keyboard input");
}

TV.TVScreenSaver.installIdleStart(1234);
TV.TVScreenSaver.installIdleStart(1234);
if (documentListeners.size !== 5 || timeoutDelay !== 1234 || !timeoutCallback) {
    throw new Error("idle start was not installed exactly once");
}
timeoutCallback();
if (!TV.TVScreenSaver.active) {
    throw new Error("idle timeout did not start a screen saver");
}
TV.TVScreenSaver.stop();
'''
    subprocess.run(
        [NODE, "-e", script, str(SAVER_PATHS[0])],
        check=True,
        capture_output=True,
        text=True,
    )


def test_generated_and_bundle_apps_enable_shared_idle_start():
    shell = Path("www/assets/tv-shell.js").read_text(encoding="utf-8")
    bundle = Path("www/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    assert "TVScreenSaver.installIdleStart();" in shell
    assert "TVScreenSaver.installIdleStart();" in bundle
