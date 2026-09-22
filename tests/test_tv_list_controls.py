from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)
DIALOG_PATHS = (
    Path("www/assets/tv-dialogs.js"),
    Path("thelpviewer/converter/assets/tv-dialogs.js"),
)


def test_turbo_vision_component_hierarchy_and_single_scroll_engine():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    source = CORE_PATHS[0].read_text(encoding="utf-8")

    assert "class TVWindow extends TVGroup" in source
    assert "class TVDialog extends TVWindow" in source
    assert "class TVRect" in source
    dialog_signature = source[
        source.index("class TVDialog extends TVWindow"):
        source.index("if (!(bounds instanceof TVRect))", source.index("class TVDialog extends TVWindow"))
    ]
    assert "constructor(bounds, title," in dialog_signature
    assert "windowClass" not in dialog_signature
    assert "bodyClass" not in dialog_signature
    assert "closeAttrs" not in dialog_signature
    assert "bodyMarkup" not in dialog_signature
    assert "class TVListViewer extends TVView" in source
    assert "class TVListBox extends TVListViewer" in source
    assert "class TVCluster extends TVView" in source
    assert "class TVCheckBoxes extends TVCluster" in source
    assert "class TVRadioButtons extends TVCluster" in source
    assert "class TVMultiCheckBoxes extends TVCluster" in source
    assert "class TVTerminal extends TVView" in source
    assert "class TVEditor extends TVView" in source
    assert "class TVOutline extends TVVerticalListViewer" in source
    assert "class TVMenuView extends TVView" in source
    assert "class TVMenuItem extends TVView" in source
    assert "class TVMenuBox extends TVMenuView" in source
    assert "class TVStatusItem extends TVView" in source
    assert "class TVDesktop extends TVGroup" in source
    assert "class TVScrollBar extends TVView" in source
    assert "static titleControlMarkup({" in source
    assert "static createTitleControl(options = {})" in source
    assert '<button class="tv-close-control"' in source
    assert '<button class="tv-zoom-control"' in source
    assert '<a class="tv-close-control"' not in source
    assert source.count("class TVScrollBar") == 1
    assert source.count("startRepeat(event, axis, direction)") == 1
    assert 'this.root?.querySelector(".tv-scrollbar-y")' in source
    assert "setScrollViewport(viewport = null, scrollbarWidget = null)" in source
    assert 'popup._tvMenuPopupScrollbar = main ? new TVScrollBar(new TVRect()).bindRoot(main) : null' in source
    group_signature = source[source.index("class TVGroup extends TVView"):source.index("this.children = []", source.index("class TVGroup extends TVView"))]
    button_signature = source[source.index("class TVButton extends TVView"):source.index("this.commandData = {}", source.index("class TVButton extends TVView"))]
    static_text_signature = source[source.index("class TVStaticText extends TVView"):source.index("this.text =", source.index("class TVStaticText extends TVView"))]
    assert "className" not in group_signature
    assert "attrs" not in group_signature
    assert "className" not in button_signature
    assert "attrs" not in button_signature
    assert "role" not in button_signature
    assert "name" not in button_signature
    assert "constructor(bounds, title, command, flags = bfNormal)" in button_signature
    assert "flags = bfNormal" in button_signature
    assert "defaultButton" not in button_signature
    assert "className" not in static_text_signature
    assert "style" not in static_text_signature
    assert "attrs" not in static_text_signature
    assert "tag" not in static_text_signature
    assert "buttonKind" not in source
    assert 'static roleClassNames(role = "")' in source
    assert "constructor(bounds = new TVRect())" in group_signature
    assert "constructor(bounds, text)" in static_text_signature
    assert "constructor(bounds, numCols = 1)" in source[source.index("class TVListViewer"):source.index("class TVListBox")]
    assert "constructor(bounds, hScrollBar = null, vScrollBar = null, indicator = null, bufSize = 65535)" in source
    assert 'constructor(bounds, title = "", number = 0)' in source
    assert "constructor(bounds, options = 0)" in source[source.index("class TVScrollBar"):source.index("const TurboVisionScrollbar")]
    assert "class TVButtonStrip" not in source
    assert "class TVMarkupList" not in source

    dialogs = DIALOG_PATHS[0].read_text(encoding="utf-8")
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    assert "class TVFileList extends TVListBox" in dialogs
    assert "class TVHistoryViewer extends TVVerticalListViewer" in dialogs
    assert "class TVHistoryWindow extends TVWindow" in dialogs
    assert "class TVChangeDirectoryDialog extends TVDialog" in dialogs
    assert "new TVOutline(new TVRect())" in dialogs
    assert "class TVHistoryWindow extends TVWindow" in dialogs
    assert "static view({ popupRole" in dialogs
    assert "handleEscape(event)" in dialogs
    assert "event.detail" not in dialogs
    assert "this.ignoreNextClick = true" in dialogs
    assert "this.button.disabled = false" in dialogs
    assert "if (!items.length) { return false; }" not in dialogs
    assert dialogs.count("TVHistoryWindow.view({") == 3
    assert dialogs.count("TVHistoryWindow.triggerView({") == 3
    assert "content: fileOpenMain" in dialogs
    assert "content: changeDirectoryMain" in dialogs
    assert "content: findMain" in dialogs
    assert "content: galleryMain" in dialogs
    assert "content: colorsMain" in dialogs
    assert "content: main" in dialogs
    assert 'presentation: "midi-source-presets"' in dialogs
    assert "TVRenderer.markup(" in dialogs
    assert '<button type="button" class="tv-file-open-history-button' not in dialogs
    assert "bodyMarkup: `" not in dialogs
    assert "new TVFileList(new TVRect(), 2)" in dialogs
    assert "new TVHistoryWindow({" in dialogs
    assert 'TVFrame.titleControlMarkup({' in dialogs
    assert '"data-tv-history-close": true' in dialogs
    assert 'TVFrame.closeMarkup("tv-history-close-control"' not in dialogs

    bundle = Path("www/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    css = Path("www/assets/turbovision.css").read_text(encoding="utf-8")
    assert 'rootClass: "tv-contents-outline"' in bundle
    assert "scrollbar: false" in bundle
    assert "outline.setScrollViewport(" in bundle
    assert ".tv-contents-outline-viewport" in css
    assert "overflow: visible" in css


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the list control test")
def test_vertical_list_keyboard_roving_focus_and_activation():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor() {
        this.attributes = new Map();
        this.dataset = {};
        this.listeners = new Map();
        this.style = {};
        this.tabIndex = 0;
        this.scrollTop = 0;
        this.clientHeight = 32;
        this.offsetTop = 0;
        this.offsetHeight = 16;
        this.children = [];
        const classes = new Set();
        this.classList = {
            toggle(name, force) {
                const enabled = force === undefined ? !classes.has(name) : Boolean(force);
                if (enabled) { classes.add(name); } else { classes.delete(name); }
                return enabled;
            },
            contains(name) { return classes.has(name); },
        };
    }
    addEventListener(type, handler) { this.listeners.set(type, handler); }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) || null; }
    appendChild(child) { this.children.push(child); }
    focus() { global.focused = this; }
    closest(selector) {
        const match = selector.match(/^\[([^\]]+)\]$/);
        return match && this.attributes.has(match[1]) ? this : null;
    }
    getBoundingClientRect() { return { top: 0 }; }
}

class TVView {
    constructor() { this.root = null; }
    bindRoot(root) { this.root = root; return this; }
    query(selector) { return this.root ? this.root.querySelector(selector) : null; }
}

class TVRect {}
class TVRenderer {
    static states = new WeakMap();
    static configure(view, options = {}) {
        this.states.set(view, { ...this.state(view), ...options });
        return view;
    }
    static state(view) { return this.states.get(view) || {}; }
}

global.escapeHtml = (value) => String(value);
global.attrsToString = () => "";
global.displayCp437Char = (value) => String(value);
global.measureCells = () => ({ width: 8, height: 16 });
global.TVRect = TVRect;
global.TVRenderer = TVRenderer;
global.TRACK_CHAR = "░";
global.DISABLED_TRACK_CHAR = "─";
global.THUMB_CHAR = "█";
global.SCROLL_REPEAT_MS = 100;
global.document = {
    activeElement: null,
    addEventListener() {},
    createElement() { return new FakeElement(); },
};
global.window = {
    addEventListener() {},
    setInterval() { return 1; },
    clearInterval() {},
};
global.TVScrollBar = class {
    constructor() {
        this.active = true;
        this.refreshCalls = 0;
        this.axes = { y: { root: scrollbar } };
    }
    bindRoot() { return this; }
    refresh() { this.refreshCalls += 1; }
    setActive(active) {
        this.active = Boolean(active);
        scrollbar.setAttribute("aria-disabled", this.active ? "false" : "true");
    }
    destroy() {}
};

const items = Array.from({ length: 5 }, (_, index) => {
    const element = new FakeElement();
    element.setAttribute("data-test-index", index);
    element.offsetTop = index * 16;
    return element;
});
const viewport = new FakeElement();
viewport.querySelectorAll = () => items;
viewport.querySelector = (selector) => {
    const match = selector.match(/data-test-index="(\d+)"/);
    return match ? items[Number(match[1])] : null;
};
const track = new FakeElement();
track.clientHeight = 64;
const cells = new FakeElement();
const thumb = new FakeElement();
const backward = new FakeElement();
const forward = new FakeElement();
const scrollbar = new FakeElement();
const root = new FakeElement();
root.querySelector = (selector) => ({
    "[data-tv-list-viewport]": viewport,
    "[data-tv-list-track]": track,
    "[data-tv-list-cells]": cells,
    "[data-tv-list-thumb]": thumb,
    "[data-tv-list-backward]": backward,
    "[data-tv-list-forward]": forward,
        ".tv-vlist-scrollbar": scrollbar,
        ".tv-scrollbar-y": scrollbar,
    }[selector] || null);

const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVListViewer");
const end = source.indexOf("\nclass TVVerticalScrollArea", start);
eval(source.slice(start, end) + "\nglobalThis.TestList = TVVerticalListViewer;");

const selected = [];
const activated = [];
const list = TVRenderer.configure(new TestList(new TVRect()), {
    itemAttrName: "data-test-index",
}).bindRoot(root);
list.items = ["zero", "one", "two", "three", "four"];
list.select(1, { scroll: false });
list.bind({
    onSelect: (_item, index) => selected.push(index),
    onActivate: (_item, index) => activated.push(index),
});

function event(key, target) {
    return {
        key,
        target,
        prevented: false,
        stopped: false,
        preventDefault() { this.prevented = true; },
        stopPropagation() { this.stopped = true; },
    };
}

const keydown = viewport.listeners.get("keydown");
const pageDown = event("PageDown", items[1]);
keydown(pageDown);
if (list.selectedIndex !== 3 || global.focused !== items[3] || !pageDown.prevented || !pageDown.stopped) {
    throw new Error("PageDown did not move selection and roving focus");
}
if (items[3].tabIndex !== 0 || items.some((item, index) => index !== 3 && item.tabIndex !== -1)) {
    throw new Error("list items do not use a single tab stop");
}
if (items[3].getAttribute("aria-selected") !== "true" || items[3].getAttribute("role") !== "option") {
    throw new Error("selected list item semantics are incomplete");
}

list.setActive(false);
if (list.scrollbarWidget.active || scrollbar.getAttribute("aria-disabled") !== "true") {
    throw new Error("inactive list state was not forwarded to the shared scrollbar");
}
list.setActive(true);

keydown(event("Enter", items[3]));
if (activated.join(",") !== "3") { throw new Error("Enter did not activate the selected row"); }

viewport.listeners.get("click")({ target: items[2] });
if (list.selectedIndex !== 2 || activated.length !== 1 || selected.at(-1) !== 2) {
    throw new Error("single click activated instead of selecting");
}
viewport.listeners.get("dblclick")({ target: items[2] });
if (activated.join(",") !== "3,2") { throw new Error("double click did not activate"); }
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_label_and_search_use_native_association_and_separate_activation():
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    core = CORE_PATHS[0].read_text(encoding="utf-8")
    dialogs = DIALOG_PATHS[0].read_text(encoding="utf-8")

    label = core[core.index("class TVLabel"):core.index("class TVInputLine")]
    search = dialogs[dialogs.index("class TVSearchDialog"):]
    search_binding = search[search.index("this.resultsBox.bind({"):search.index("document.addEventListener")]

    assert 'const tag = this.link ? "label" : "span"' in label
    assert 'for="${escapeHtml(this.link.viewId)}"' in label
    assert "openSelected()" not in search_binding.split("onActivate:", 1)[0]
    assert "openSelected()" in search_binding.split("onActivate:", 1)[1]
    assert 'event.command === "search-ok"' in search
    assert 'this.input.addEventListener("input"' not in search


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the choice control test")
def test_choice_groups_render_native_controls_and_messagebox_mnemonics():
    script = r"""
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");

global.escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
global.renderHotkeyMarkup = (value) => escapeHtml(value)
    .replace(/~(.)~/g, '<span class="tv-hotkey">$1</span>');
global.attrsToString = (attrs = {}) => Object.entries(attrs)
    .filter(([, value]) => value !== false && value !== null && value !== undefined)
    .map(([key, value]) => value === true ? key : `${key}="${escapeHtml(value)}"`)
    .join(" ");
global.TVRect = class {};
global.TVView = class {
    constructor() { this.viewId = "test-view"; }
    static roleClassNames(value = "") { return value; }
};
global.TVRenderer = class {
    static state() { return {}; }
    static viewAttrs(_view, attrs = {}) { return attrs; }
    static markup(items, options = {}) {
        return { renderMarkup: () => `<div class="${options.className || ""}" ${attrsToString(options.attributes || {})}>${items.join("")}</div>` };
    }
};

const choiceStart = source.indexOf("let tvChoiceGroupId");
const choiceEnd = source.indexOf("\nclass TVButton extends", choiceStart);
eval(source.slice(choiceStart, choiceEnd)
    + "\nglobalThis.TestChecks = TVCheckBoxes; globalThis.TestRadios = TVRadioButtons;");

const checks = new TestChecks(new TVRect(), [
        { label: "One < two", checked: true, value: "one" },
        { label: "Disabled", disabled: true },
    ]).renderMarkup();
if (!checks.includes('type="checkbox"') || !checks.includes("checked") || !checks.includes("disabled")) {
    throw new Error("checkbox group does not expose native state");
}
if (!checks.includes("One &lt; two") || !checks.includes("tv-checkbox-mark")) {
    throw new Error("checkbox label or DOS mark is incomplete");
}
if (!checks.includes('class="tv-checkbox-item is-disabled"')) {
    throw new Error("disabled checkbox does not expose its palette state");
}

const radios = new TestRadios(new TVRect(), [{ label: "A", checked: true }, { label: "B" }]).renderMarkup();
const radioNames = Array.from(radios.matchAll(/name="([^"]+)"/g), (match) => match[1]);
if ((radios.match(/type="radio"/g) || []).length !== 2
    || radioNames.length !== 2 || radioNames[0] !== radioNames[1]) {
    throw new Error("radio options are not one native group");
}

global.TVDialog = class {};
const messageStart = source.indexOf("class TVMessageBox");
const messageEnd = source.indexOf("\nfunction normalizeSearchText", messageStart);
eval(source.slice(messageStart, messageEnd) + "\nglobalThis.TestMessage = TVMessageBox;");
const cancel = TestMessage.BUTTON_DEFS.find((button) => button.cmd === "cancel");
if (!cancel || cancel.label !== "~C~ancel" || cancel.mnemonic !== "c") {
    throw new Error("Cancel mnemonic is not declared");
}
let dismissed = "";
const message = Object.create(TestMessage.prototype);
message._buttonDefs = [cancel];
message.buttonsEl = { querySelector() { return {}; } };
message._dismiss = (command) => { dismissed = command; };
const event = {
    key: "c",
    preventDefault() {},
    stopPropagation() {},
};
message._handleKey(event);
if (dismissed !== "cancel") { throw new Error("Cancel mnemonic did not dispatch its command"); }
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
