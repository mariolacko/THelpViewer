from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the help-context test")
def test_help_context_inheritance_resolution_and_f1_dispatch():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor(parentElement = null) {
        this.parentElement = parentElement;
        this.attributes = new Map();
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
    hasAttribute(name) { return this.attributes.has(name); }
    getAttribute(name) { return this.attributes.get(name) ?? null; }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    removeAttribute(name) { this.attributes.delete(name); }
    getBoundingClientRect() { return { width: 8, height: 16, top: 0, left: 0, right: 8 }; }
}

const listeners = new Map();
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
    addEventListener(type, handler) { listeners.set(type, handler); },
    removeEventListener(type, handler) {
        if (listeners.get(type) === handler) { listeners.delete(type); }
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return new FakeElement(); },
};
global.getComputedStyle = () => ({ getPropertyValue() { return ""; } });

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;
const H = TV.TV_HELP_CONTEXTS;

if (H.hcNoContext !== 0 || H.hcFileOpen !== 2010 || TV.hcDocumentViewer !== 2080) {
    throw new Error("help-context constants were not exported");
}

const childRoot = new FakeElement();
const child = new TV.TVWidget(childRoot).setHelpCtx(H.hcFind);
const group = new TV.TVGroup({ children: [child], helpCtx: H.hcDialog });
if (child.owner !== group || group.getHelpCtx() !== H.hcDialog) {
    throw new Error("TVGroup owner or fallback help context is broken");
}
group.setCurrent(child);
if (group.getHelpCtx() !== H.hcFind) {
    throw new Error("TVGroup did not inherit its current child's help context");
}
if (!group.renderMarkup().includes(`data-tv-help-ctx="${H.hcDialog}"`)) {
    throw new Error("TVGroup did not render its own help context");
}

const focusedParent = new FakeElement();
TV.setElementHelpContext(focusedParent, H.hcDocumentViewer);
document.activeElement = new FakeElement(focusedParent);
const root = {
    activeElement: document.activeElement,
    addEventListener(type, handler) { listeners.set(type, handler); },
    removeEventListener(type, handler) {
        if (listeners.get(type) === handler) { listeners.delete(type); }
    },
    querySelector() { return null; },
};
if (TV.resolveHelpContext({ root }) !== H.hcDocumentViewer) {
    throw new Error("focused element help context was not inherited");
}
if (TV.resolveHelpContext({
    root,
    menuController: { getHelpCtx: () => H.hcSearch },
    dialogManager: { getHelpCtx: () => H.hcFileOpen },
}) !== H.hcSearch) {
    throw new Error("active menu context did not take precedence");
}

let requested = 0;
const controller = new TV.TVHelpController({
    root,
    getDialogManager: () => ({ getHelpCtx: () => H.hcFileOpen }),
    onHelp: (helpCtx) => { requested = helpCtx; },
});
const event = {
    key: "F1", altKey: false, ctrlKey: false, metaKey: false, shiftKey: false,
    defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() {},
};
listeners.get("keydown")(event);
if (!event.defaultPrevented || requested !== H.hcDocumentViewer) {
    throw new Error("F1 did not dispatch the resolved context");
}
controller.destroy();
if (listeners.has("keydown")) {
    throw new Error("TVHelpController did not detach its listener");
}
"""

    completed = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
