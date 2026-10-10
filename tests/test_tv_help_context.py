import json
from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)
HELP_BUNDLE_PATHS = (
    Path("www/assets/tv-context-help.json"),
    Path("thelpviewer/converter/assets/tv-context-help.json"),
)
CONTEXT_HELP_JS_PATHS = (
    Path("www/assets/tv-context-help.js"),
    Path("thelpviewer/converter/assets/tv-context-help.js"),
)


def test_dialogs_own_their_help_contexts_without_registration_maps():
    dialogs = Path("www/assets/tv-dialogs.js").read_text(encoding="utf-8")
    context_help = CONTEXT_HELP_JS_PATHS[0].read_text(encoding="utf-8")
    games = Path("www/assets/tv-games.js").read_text(encoding="utf-8")
    bundle = Path("www/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    shell = Path("www/assets/tv-shell.js").read_text(encoding="utf-8")

    assert "DIALOG_HELP_CONTEXTS" not in bundle
    assert "DIALOG_HELP_CONTEXTS" not in shell
    for context in (
        "hcAbout", "hcWidgetGallery", "hcFileOpen",
        "hcChangeDirectory", "hcAsciiTable", "hcCalculator", "hcCalendar",
        "hcColors", "hcMidiPlayer", "hcFind", "hcSearch",
        "hcStatistics", "hcSystemInformation",
        "hcAccount", "hcRegistration", "hcRegistrationTokens", "hcServerConfiguration",
        "hcGridDemo", "hcUsers",
    ):
        assert f"setHelpCtx({context})" in dialogs
    assert "setHelpCtx(hcContextHelp)" in context_help
    assert "TV_CONTEXT_HELP_TOPICS" not in dialogs
    assert "class TVContextHelpDialog" not in dialogs
    assert "TV_CONTEXT_HELP_TOPICS" in context_help
    assert "class TVContextHelpWindow extends TVHelpWindow" in context_help
    assert "class TVHelpWindow extends TVWindow" in context_help
    assert "class TVContextHelpDialog" not in context_help
    assert "class TVContextHelpScroller" not in context_help
    assert "new TVScrollBar" not in context_help
    assert "new TVContextHelpWindow()" in shell
    assert 'this.dialogManager.registerWindow(name, root' in shell
    for context in (
        "hcPuzzle", "hcTetris", "hcMines", "hcBreakOut", "hcSokoban",
        "hcLines", "hcReversi", "hcLudo", "hcMastermind", "hcTron",
        "hcHanoi", "hcSnake",
    ):
        assert f"setHelpCtx({context})" in games


def test_context_help_is_a_complete_uhf_bundle():
    assert HELP_BUNDLE_PATHS[0].read_bytes() == HELP_BUNDLE_PATHS[1].read_bytes()
    assert CONTEXT_HELP_JS_PATHS[0].read_bytes() == CONTEXT_HELP_JS_PATHS[1].read_bytes()
    bundle = json.loads(HELP_BUNDLE_PATHS[0].read_text(encoding="utf-8"))

    expected_contexts = {
        1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
        2000, 2010, 2020, 2030, 2040, 2050, 2060, 2070,
        2080, 2090, 2100, 2110, 2120, 2130,
        2140, 2150, 2160, 2170, 2180, 2190,
        2200, 2210, 2220, 2230, 2240, 2250, 2260, 2270,
        2280, 2290, 2300, 2310, 2320, 2340, 2350,
    }
    assert bundle["uhf_version"] == "2.0"
    assert bundle["metadata"]["help_contents_topic_id"] == 1000
    assert bundle["metadata"]["source"]["filename"] == "THELPVIEWER.HLP"
    assert expected_contexts <= {int(topic_id) for topic_id in bundle["topics"]}
    contents = bundle["topics"]["1000"]["content"]
    assert len(contents) > 24
    assert any("┌" in line and "┬" in line for line in contents)
    assert sum("[link:topic=" in line for line in contents) >= 3
    index_entries = [entry for group in bundle["index"] for entry in group["entries"]]
    assert {"About", "THelpViewer", "Widget Gallery"} <= {
        entry["label"] for entry in index_entries
    }
    assert {entry["topic_id"] for entry in index_entries} <= {
        int(topic_id) for topic_id in bundle["topics"]
    }
    import re
    links = {int(target) for topic in bundle["topics"].values()
             for line in topic["content"] for target in re.findall(r"\[link:topic=(\d+)\]", line)}
    assert links <= {int(topic_id) for topic_id in bundle["topics"]}
    assert {"Account", "DOS Prompt", "Registration", "Server Configuration", "Grid Viewer"} <= {
        entry["label"] for entry in index_entries
    }

    app = Path("www/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    assert 'const CONTEXT_HELP_BUNDLE_FILE = "../assets/tv-context-help.json"' in app
    assert "loadBundle(CONTEXT_HELP_BUNDLE_FILE)" in app
    assert "this.windowManager.showTopic(bundle, helpCtx)" in app
    assert 'new TVMenuItem("~I~ndex", "context-help-index")' in app
    system_menu = app.split("const systemItems = [", 1)[1].split("];", 1)[0]
    help_menu = app.split("const helpItems = [", 1)[1].split("];", 1)[0]
    assert 'dialogItem("~A~bout", "about")' not in system_menu
    assert 'dialogItem("~A~bout", "about")' in help_menu
    assert 'this._registerDialog("contexthelp"' not in app


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

if (H.hcNoContext !== 0 || H.hcFileOpen !== 2010 || TV.hcDocumentViewer !== 2080
    || H.hcTetris !== 2150 || TV.hcTron !== 2250) {
    throw new Error("help-context constants were not exported");
}

const childRoot = new FakeElement();
const child = new TV.TVView(new TV.TVRect()).bindRoot(childRoot).setHelpCtx(H.hcFind);
const group = new TV.TVGroup(new TV.TVRect()).insertAll([child]).setHelpCtx(H.hcDialog);
if (child.owner !== group || group.getHelpCtx() !== H.hcDialog) {
    throw new Error("TVGroup owner or fallback help context is broken");
}
group.setCurrent(child);
if (group.getHelpCtx() !== H.hcFind) {
    throw new Error("TVGroup did not inherit its current child's help context");
}
if (!group.draw().includes(`data-tv-help-ctx="${H.hcDialog}"`)) {
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
