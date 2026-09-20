from pathlib import Path
import shutil
import subprocess

import pytest


SAVER_PATHS = (
    Path("www/assets/tv-screensaver.js"),
    Path("thelpviewer/converter/assets/tv-screensaver.js"),
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
        this.textContent = "";
        this.innerHTML = "";
    }
    appendChild() {}
    setAttribute() {}
    addEventListener(name, callback) { this.listeners.set(name, callback); }
    focus() { document.activeElement = this; }
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
    escapeHtml: (value) => String(value),
    displayCp437Char: (value) => String(value),
    measureCells: () => ({ width: 10, height: 10 }),
};

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;
class TestSaver extends TV.TVScreenSaver {
    init() { this.initCount = (this.initCount || 0) + 1; }
    tick() { this.tickCount = (this.tickCount || 0) + 1; }
}

const previous = new FakeElement();
document.activeElement = previous;
const saver = new TestSaver();
saver.start();
if (document.activeElement !== saver.overlay || saver.cols !== 10 || saver.rows !== 5) {
    throw new Error("screen saver did not focus and measure its overlay");
}
saver.overlay.clientWidth = 170;
saver.overlay.clientHeight = 80;
windowListeners.get("resize")();
if (saver.cols !== 17 || saver.rows !== 8 || saver.initCount !== 2 || saver.tickCount !== 1) {
    throw new Error("active screen saver did not remeasure and reinitialize after resize");
}
saver.stop();
if (document.activeElement !== previous || TV.TVScreenSaver.active !== null) {
    throw new Error("screen saver did not restore focus on stop");
}
if (windowListeners.has("resize")) {
    throw new Error("screen saver left its resize listener attached");
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
