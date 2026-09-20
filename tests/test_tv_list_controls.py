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

class TVWidget {
    constructor(root = null) { this.root = root; }
    query(selector) { return this.root ? this.root.querySelector(selector) : null; }
}

global.escapeHtml = (value) => String(value);
global.attrsToString = () => "";
global.displayCp437Char = (value) => String(value);
global.measureCells = () => ({ width: 8, height: 16 });
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
}[selector] || null);

const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVVerticalListViewer");
const end = source.indexOf("\nclass TVVerticalScrollArea", start);
eval(source.slice(start, end) + "\nglobalThis.TestList = TVVerticalListViewer;");

const framedMarkup = TestList.renderMarkup({
    rootClass: "test-list",
    viewportClass: "test-viewport",
    frameTitle: "Files",
});
if (
    !framedMarkup.includes("tv-vlist-framed")
    || !framedMarkup.includes("tv-vlist-frame-top")
    || !framedMarkup.includes(" Files ")
    || !framedMarkup.includes('data-tv-border-side="│"')
    || !framedMarkup.includes("└")
) {
    throw new Error("framed list markup is incomplete");
}

const selected = [];
const activated = [];
const list = new TestList(root, { itemAttrName: "data-test-index" });
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

let inactivePrevented = false;
list.setActive(false);
list.startRepeat({ preventDefault() { inactivePrevented = true; } }, 1);
if (inactivePrevented || list.repeatTimer !== null || scrollbar.getAttribute("aria-disabled") !== "true") {
    throw new Error("inactive list scrollbar accepted input");
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
    search_binding = search[search.index("this.resultsBox.bind({"):search.index("this.okButton.addEventListener")]

    assert 'tag: forId ? "label" : "span"' in label
    assert "openSelected()" not in search_binding.split("onActivate:", 1)[0]
    assert "openSelected()" in search_binding.split("onActivate:", 1)[1]


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
global.attrsToString = (attrs = {}) => Object.entries(attrs)
    .filter(([, value]) => value !== false && value !== null && value !== undefined)
    .map(([key, value]) => value === true ? key : `${key}="${escapeHtml(value)}"`)
    .join(" ");
global.TVWidget = class { constructor(root = null) { this.root = root; } };
global.TVListViewer = class {
    constructor({ className = "", attrs = {}, items = [] } = {}) {
        this.className = className;
        this.attrs = attrs;
        this.items = items;
    }
    renderMarkup() { return `<div class="${this.className}" ${attrsToString(this.attrs)}>${this.items.join("")}</div>`; }
};

const choiceStart = source.indexOf("let tvChoiceGroupId");
const choiceEnd = source.indexOf("\nclass TVButton extends", choiceStart);
eval(source.slice(choiceStart, choiceEnd)
    + "\nglobalThis.TestChecks = TVCheckBoxes; globalThis.TestRadios = TVRadioButtons;");

const checks = new TestChecks({
    options: [
        { label: "One < two", checked: true, value: "one" },
        { label: "Disabled", disabled: true },
    ],
}).renderMarkup();
if (!checks.includes('type="checkbox"') || !checks.includes("checked") || !checks.includes("disabled")) {
    throw new Error("checkbox group does not expose native state");
}
if (!checks.includes("One &lt; two") || !checks.includes("tv-checkbox-mark")) {
    throw new Error("checkbox label or DOS mark is incomplete");
}

const radios = new TestRadios({
    name: "mode",
    options: [{ label: "A", checked: true }, { label: "B" }],
}).renderMarkup();
if ((radios.match(/type="radio"/g) || []).length !== 2 || (radios.match(/name="mode"/g) || []).length !== 2) {
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
