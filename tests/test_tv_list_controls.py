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
    assert "class TVPoint" in source
    dialog_signature = source[
        source.index("class TVDialog extends TVWindow"):
        source.index("if (!(bounds instanceof TVRect))", source.index("class TVDialog extends TVWindow"))
    ]
    assert "constructor(bounds, title)" in dialog_signature
    assert "setDrawOptions" not in source
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
    assert "class TVOutline extends TVListBox" in source
    assert "class TVMenuView extends TVView" in source
    assert "class TVMenu {" in source
    assert "class TVMenuItem {" in source
    assert "class TVMenuBox extends TVMenuView" in source
    assert "class TVStatusItem {" in source
    assert "class TVStatusLine extends TVView" in source
    assert "class TVDesktop extends TVGroup" in source
    assert "class TVScrollBar extends TVView" in source
    assert 'drawTitleControl(command, glyph, title = "")' in source
    assert 'createTitleControl(command, glyph, title = "")' in source
    assert 'classes: "tv-close-control"' in source
    assert 'classes: "tv-zoom-control"' in source
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
    button_class = source[source.index("class TVButton extends TVView"):source.index("class TVFrame extends TVView")]
    for browser_field in ("this.ariaLabel", "this.ariaExpanded", "this.tabIndex", "this.tooltip", "this.labelMarkup"):
        assert browser_field not in button_class
    assert "constructor(bounds, title, command, flags = bfNormal)" in button_signature
    assert "flags = bfNormal" in button_signature
    assert "defaultButton" not in button_signature
    assert "className" not in static_text_signature
    assert "style" not in static_text_signature
    assert "attrs" not in static_text_signature
    assert "tag" not in static_text_signature
    assert "buttonKind" not in source
    assert 'baseClass: "tv-dialog-button"' in source
    for specialized_command in (
        "calc-key", "ascii-code", "calendar-prev", "color-index", "midi-track",
        "search-index", "mines-face", "ludo-player-mode", "ludo-piece",
        "mastermind-color", "file-open-scroll-left",
    ):
        assert f'"{specialized_command}"' not in button_class
    assert 'class TVCalculatorButton extends TVButton' in Path("www/assets/tv-dialogs.js").read_text(encoding="utf-8")
    assert "this.presentation =" not in group_signature
    assert "this.viewName =" not in group_signature
    assert 'static _roleClassNames(role = "")' in source
    assert "constructor(bounds = new TVRect())" in group_signature
    assert "constructor(bounds, text)" in static_text_signature
    assert "constructor(bounds, numCols = 1, hScrollBar = null, vScrollBar = null)" in source[source.index("class TVListViewer"):source.index("class TVListBox")]
    assert "constructor(bounds, hScrollBar = null, vScrollBar = null, indicator = null, bufSize = 65535)" in source
    assert 'constructor(bounds, title = "", number = 0)' in source
    for original_method in (
        "calcBounds(bounds, delta)",
        "commandEnabled(command)",
        "disableCommands(commands)",
        "enableCommands(commands)",
        "endModal(command)",
        "getClipRect()",
        "makeGlobal(source)",
        "makeLocal(source)",
        "mouseInView(point)",
        "putInFrontOf(target)",
        "sizeLimits()",
        "execView(view)",
        "lock()",
        "unlock()",
        "redraw()",
        "getTitleWidth()",
        "frameLine(y, width = this.size.x)",
    ):
        assert original_method in source
    for original_constant in (
        "const wfMove = 0x01",
        "const wfGrow = 0x02",
        "const wfClose = 0x04",
        "const wfZoom = 0x08",
        "const sbVertical = 0x0001",
        "const wnNoNumber = 255",
    ):
        assert original_constant in source
    assert "constructor(bounds, options = sbHorizontal)" in source[source.index("class TVScrollBar"):source.index("class TVDesktop")]
    assert "class TVButtonStrip" not in source
    assert "class TVMarkupList" not in source

    dialogs = DIALOG_PATHS[0].read_text(encoding="utf-8")
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    assert "class TVFileList extends TVListBox" in dialogs
    assert "class TVHistoryViewer extends TVListBox" in dialogs
    assert "class TVHistoryWindow extends TVWindow" in dialogs
    assert "class TVChangeDirectoryDialog extends TVDialog" in dialogs
    assert "class TVDirectoryList" not in dialogs
    assert "new TVOutline(new TVRect(2, 5, 31, 13))" in dialogs
    assert "class TVHistoryWindow extends TVWindow" in dialogs
    assert "class TVHistory extends TVButton" in dialogs
    assert "constructor(bounds, link, historyId)" in dialogs
    assert "this.insert(this.viewer)" in dialogs
    assert "handleEscape(event)" in dialogs
    assert "event.detail" not in dialogs
    assert "ignoreNextClick" not in dialogs
    assert "this.window.toggle()" in dialogs
    assert "this.buttonView?.setState(sfDisabled, false)" in dialogs
    assert "if (!items.length) { return false; }" not in dialogs
    assert dialogs.count("new TVHistoryWindow(new TVRect(") == 3
    assert dialogs.count("new TVHistory(new TVRect(") == 3
    assert "this.insert(fileOpenMain)" in dialogs
    assert "this.insert(changeDirectoryMain)" in dialogs
    assert "this.insert(findMain)" in dialogs
    assert "this.insert(galleryMain)" in dialogs
    assert "this.insert(colorsMain)" in dialogs
    assert "this.insert(main)" in dialogs
    assert "class TVSearchResultsList extends TVListBox" in dialogs
    assert "class TVSearchStatusText" not in dialogs
    assert "class TVFindStatus" not in dialogs
    assert "_rootClass" not in dialogs
    assert "_viewportClass" not in dialogs
    assert "this.mainView.changeBounds(new TVRect(" in dialogs
    assert "this.locate(new TVRect(0, 0, 44," in dialogs
    assert "midi-close-button" not in dialogs
    assert 'static role = "midi-' not in dialogs
    assert "class TVMidiExternalSource" not in dialogs
    assert "class TVMidiDisplay extends TVGroup" in dialogs
    assert "setTrack(track, number)" in dialogs
    assert "class TVMidiMeter extends TVGroup" in dialogs
    assert "setProgress(value)" in dialogs
    assert "this.setSize(" not in dialogs
    assert "TVMarkupView" not in dialogs
    assert "class TVAsciiTable extends TVGroup" in dialogs
    assert "class TVCalendarView extends TVGroup" in dialogs
    assert "class TVColorSelector extends TVGroup" in dialogs
    assert "class TVColorDisplay extends TVGroup" in dialogs
    assert "onSelectorKeyDown" not in dialogs
    color_selector = dialogs[dialogs.index("class TVColorSelector"):dialogs.index("class TVColorDisplay")]
    assert "handleEvent(event)" in color_selector
    assert 'event.what = evCommand' in color_selector
    assert 'event.command = "color-index"' in color_selector
    for role_only_class in (
        "TVContextHelpHeading",
        "TVContextHelpNavigation",
        "TVWidgetList",
        "TVFileInputLine",
        "TVFileScrollTrack",
        "TVFileInfoPane",
        "TVDirectoryDetail",
        "TVAsciiReport",
        "TVCalculatorIndicator",
        "TVCalendarCell",
        "TVColorSample",
    ):
        assert f"class {role_only_class}" not in dialogs
    assert "TVRenderer" not in source
    assert '<button type="button" class="tv-file-open-history-button' not in dialogs
    assert "bodyMarkup: `" not in dialogs
    assert "new TVFileList(new TVRect(" in dialogs
    history_window = dialogs[dialogs.index("class TVHistoryWindow"):dialogs.index("class TVFileList")]
    assert "draw()" not in history_window
    assert "this.flags = wfClose" in history_window
    assert 'static role = "history-window"' not in history_window

    bundle = Path("www/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    css = Path("www/assets/turbovision.css").read_text(encoding="utf-8")
    assert 'static role = "contents-outline"' not in bundle
    assert "hasScrollbar() { return false; }" in bundle
    assert 'outline.rootClass = "tv-contents-outline"' not in bundle
    assert "outline.setScrollViewport(" in bundle
    assert "[data-tv-contents-outline] > .tv-vlist-viewport" in css
    assert "overflow: visible" in css
    assert ".tv-search-results-scroll" not in css
    assert ".tv-search-empty" not in css
    assert ".tv-find-status" not in css
    assert "\n[data-tv-search-results] > .tv-vlist-viewport {" not in css
    assert css.count("[hidden]") == 1
    assert ".tv-find-window .tv-input-line" not in css
    assert ".tv-file-open-window .tv-file-input-line" not in css
    assert ".tv-change-dir-window .tv-file-input-line" not in css
    assert ".tv-midi-display" not in css
    assert ".tv-midi-meter" not in css
    assert ".tv-midi-external" not in css
    assert ".tv-midi-track-list" not in css
    assert "[data-tv-midi-display]" in css
    assert "[data-tv-midi-meter]" in css
    for stale_selector in (
        ".tv-file-open-file-list",
        ".tv-file-open-history-listviewer",
        ".tv-change-dir-listviewer",
        ".tv-context-help-topic",
        ".tv-context-help-nav-text",
        ".tv-calendar-cell",
        ".tv-colors-display-sample",
        ".tv-calc-display",
        ".tv-winlist-window",
    ):
        assert stale_selector not in css
    assert "\n.tv-calc-button {" not in css
    for redundant_geometry in (
        ".tv-ascii-body",
        ".tv-tetris-window {",
        ".tv-ludo-window {",
        "[data-tv-winlist-listviewer] > .tv-vlist-viewport",
        "[data-tv-winlist-listviewer] .tv-vlist-item",
    ):
        assert redundant_geometry not in css
    for redundant_size in (
        "min-width: 71ch",
        "height: 23em",
        "width: 60ch",
        "width: 54ch",
        "    height: 6em;",
    ):
        assert redundant_size not in css
    assert "Math.max(0, bounds.width - 1)" in dialogs
    assert "Math.max(0, bounds.height - 2)" in dialogs
    assert "new TVAsciiTable(new TVRect())" in dialogs
    assert "this.insertAll([chart, report])" in dialogs
    games = Path("www/assets/tv-games.js").read_text(encoding="utf-8")
    assert 'new TVLudoPlayerButton(new TVRect(0, player + 1, 22, player + 2), name, "ludo-player-mode"' in games
    assert 'class="tv-snake-cell tv-snake-body"' not in games
    assert ".tv-snake-body {" not in css
    input_rule_start = css.index("\n.tv-input-line {")
    input_rule = css[input_rule_start:css.index("}", input_rule_start) + 1]
    assert "box-sizing: border-box" in input_rule


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
    removeEventListener(type) { this.listeners.delete(type); }
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

const evNothing = 0;
const evMouseDown = 1;
const evKeyDown = 16;
class TVEvent {
    constructor(what, { infoPtr = null, nativeEvent = null } = {}) {
        this.what = what;
        this.infoPtr = infoPtr;
        this.nativeEvent = nativeEvent;
    }
}
    class TVView {
        constructor() { this.root = null; }
        bindRoot(root) { this.root = root; return this; }
        _query(selector) { return this.root ? this.root.querySelector(selector) : null; }
        dispatchEvent(event) { this.handleEvent(event); return event; }
        clearEvent(event) { event.what = evNothing; }
}

class TVRect {}

global.escapeHtml = (value) => String(value);
global.attrsToString = () => "";
global.displayCp437Char = (value) => String(value);
global.measureCells = () => ({ width: 8, height: 16 });
global.TVRect = TVRect;
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
    element.setAttribute("data-tv-list-index", index);
    element.dataset.tvListIndex = String(index);
    element.offsetTop = index * 16;
    return element;
});
const viewport = new FakeElement();
viewport.querySelectorAll = () => items;
viewport.querySelector = (selector) => {
    const match = selector.match(/data-tv-list-index="(\d+)"/);
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
const end = source.indexOf("\nclass TVScroller", start);
eval(source.slice(start, end) + "\nglobalThis.TestList = TVListBox;");

const selected = [];
const activated = [];
    const list = new TestList(new TVRect());
    list.bindRoot(root);
list.items = ["zero", "one", "two", "three", "four"];
list.select(1, { scroll: false });
list.bind({
    onSelect: (_item, index) => selected.push(index),
    onActivate: (_item, index) => activated.push(index),
});

function event(type, target, key = "") {
    return {
        type,
        key,
        target,
        prevented: false,
        stopped: false,
        preventDefault() { this.prevented = true; },
        stopPropagation() { this.stopped = true; },
    };
}

const keydown = viewport.listeners.get("keydown");
const pageDown = event("keydown", items[1], "PageDown");
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

keydown(event("keydown", items[3], "Enter"));
if (activated.join(",") !== "3") { throw new Error("Enter did not activate the selected row"); }

viewport.listeners.get("click")(event("click", items[2]));
if (list.selectedIndex !== 2 || activated.length !== 1 || selected.at(-1) !== 2) {
    throw new Error("single click activated instead of selecting");
}
viewport.listeners.get("dblclick")(event("dblclick", items[2]));
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
    search_binding = search[
        search.index("this.resultsBox.bind({"):
        search.index("    handleEvent(event)", search.index("this.resultsBox.bind({"))
    ]

    assert 'const tag = this.link ? "label" : "span"' in label
    assert 'for="${escapeHtml(this.link.viewId)}"' in label
    assert "openSelected()" not in search_binding.split("onActivate:", 1)[0]
    assert "openSelected()" in search_binding.split("onActivate:", 1)[1]
    assert 'event.command === "search-ok"' in search
    assert 'this.input.addEventListener("input"' not in search
    assert 'document.addEventListener("keydown"' not in search


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the picture validator test")
def test_registration_token_picture_validator_formats_without_changing_old_tokens():
    script = r"""
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
global.TVRect = class {};
global.TVView = class { constructor() { this.root = null; } };
global.evBroadcast = 0x0200;
const start = source.indexOf('class TVPXPictureValidator');
const end = source.indexOf('\nclass TVGroup extends', start);
eval(source.slice(start, end)
    + '\nglobalThis.Picture = TVPXPictureValidator; globalThis.Input = TVInputLine;');
const input = new Input(new TVRect(), 128).setValidator(
    new Picture('!!!!!-!!!!!-!!!!!-!!!!!-!!!!!', true));
input.setData('abcdefghjklmnpqrstvwxyz234');
if (input.getData() !== 'ABCDE-FGHJK-LMNPQ-RSTVW-XYZ23') {
    throw new Error('Token picture formatting failed: ' + input.getData());
}
if (!input.valid()) { throw new Error('Formatted token was rejected'); }
input.root = { value: 'abcdeF' };
input.handleEvent({ what: evBroadcast, infoPtr: input, nativeEvent: { type: 'input' } });
if (input.root.value !== 'ABCDE-F') { throw new Error('Typing did not fill the separator'); }
input.root = null;
const oldToken = 'legacy-enrollment-token_with-43-characters-123';
input.setData(oldToken);
if (input.valid()) { throw new Error('Legacy token format was accepted'); }
"""
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0])], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


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
    static _roleClassNames(value = "") { return value; }
    static _viewBoundsStyle() { return ""; }
    _drawAttrs(attrs = {}) { return attrs; }
};
global.evBroadcast = 0x0200;
const choiceStart = source.indexOf("let tvChoiceGroupId");
const choiceEnd = source.indexOf("\nclass TVButton extends", choiceStart);
eval(source.slice(choiceStart, choiceEnd)
    + "\nglobalThis.TestChecks = TVCheckBoxes; globalThis.TestRadios = TVRadioButtons;");

const checks = new TestChecks(new TVRect(), [
        { label: "One < two", checked: true, value: "one" },
        { label: "Disabled", disabled: true },
    ]).draw();
if (!checks.includes('type="checkbox"') || !checks.includes("checked") || !checks.includes("disabled")) {
    throw new Error("checkbox group does not expose native state");
}
if (!checks.includes("One &lt; two") || !checks.includes("tv-checkbox-mark")) {
    throw new Error("checkbox label or DOS mark is incomplete");
}
if (!checks.includes('class="tv-checkbox-item is-disabled"')) {
    throw new Error("disabled checkbox does not expose its palette state");
}

const radios = new TestRadios(new TVRect(), [{ label: "A", checked: true }, { label: "B" }]).draw();
const radioNames = Array.from(radios.matchAll(/name="([^"]+)"/g), (match) => match[1]);
if ((radios.match(/type="radio"/g) || []).length !== 2
    || radioNames.length !== 2 || radioNames[0] !== radioNames[1]) {
    throw new Error("radio options are not one native group");
}

global.TVDialog = class { onDialogKeyDown() {} };
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
message.buttonViews = [];
message._dismiss = (command) => { dismissed = command; };
const event = {
    key: "c",
    preventDefault() {},
    stopPropagation() {},
};
message.onDialogKeyDown(event);
if (dismissed !== "cancel") { throw new Error("Cancel mnemonic did not dispatch its command"); }
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
