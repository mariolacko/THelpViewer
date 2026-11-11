from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/server/converter/assets/tv-core.js"),
)
DIALOG_PATHS = (
    Path("www/assets/tv-dialogs.js"),
    Path("thelpviewer/server/converter/assets/tv-dialogs.js"),
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
    assert 'this.root?.querySelector(".tv-scrollbar")' in source
    assert "setScrollViewport(viewport = null, scrollbarWidget = null)" in source
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
        "mastermind-color",
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
        "putInFrontOf(target = null)",
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
    assert dialogs.count("new TVHistoryWindow(new TVRect(") == 4
    assert '"thelp:midi-filter-history"' in DIALOG_PATHS[0].read_text()
    assert dialogs.count("new TVHistory(new TVRect(") == 4
    assert "this.insert(fileOpenMain)" in dialogs
    assert "this.insert(changeDirectoryMain)" in dialogs
    assert "this.insert(findMain)" in dialogs
    assert "this.insert(galleryMain)" in dialogs
    assert "this.insert(colorsMain)" in dialogs
    midi = DIALOG_PATHS[0].read_text()
    assert "this.insert(main)" in midi
    assert "class TVSearchResultsList extends TVListBox" in dialogs
    assert "class TVSearchStatusText" not in dialogs
    assert "class TVFindStatus" not in dialogs
    assert "_rootClass" not in dialogs
    assert "_viewportClass" not in dialogs
    assert "this.mainView.changeBounds(new TVRect(" in midi
    assert "this.growTo(55," in midi
    assert "class TVImage extends TVView" in source
    assert "const cover = new TVImage(new TVRect(1, 0, 11, 5))" in midi
    assert "midi-close-button" not in dialogs
    assert 'static role = "midi-' not in dialogs
    assert "class TVMidiExternalSource" not in dialogs
    assert "class TVMidiDisplay extends TVGroup" in midi
    assert "setTrack(track, number)" in midi
    assert "class TVMidiMeter" not in dialogs
    assert "const meter = new TVBarGauge(new TVRect(12, 4, 52, 5), 100)" in midi
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
    assert '.tv-window[data-tv-palette="history"]' not in css
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
    assert "[data-tv-midi-display]" not in css
    assert ".tv-midi-window [data-tv-bar-gauge]" not in css
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
    assert "new TVAsciiTable(new TVRect(0, 0, 32, 8))" in dialogs
    assert "this.insertAll([chart, report])" in dialogs
    games = Path("www/assets/tv-games.js").read_text(encoding="utf-8")
    assert 'new TVLudoPlayerButton(new TVRect(0, player + 1, 22, player + 2), name, "ludo-player-mode"' in games
    assert 'class="tv-snake-cell tv-snake-body"' not in games
    assert ".tv-snake-body {" not in css



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
    contains(element) { return this === element || this.children.some(child => child.contains(element)); }
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
const sfVisible = 0x0001, sfDisabled = 0x0100;
class TVEvent {
    constructor(what, { infoPtr = null, nativeEvent = null } = {}) {
        this.what = what;
        this.infoPtr = infoPtr;
        this.nativeEvent = nativeEvent;
    }
}
    class TVView {
        getState(mask) { return (this.state & mask) === mask; }
        _paletteAttribute() { return null; }
        constructor() { this.root = null; this.state = sfVisible; this.size = { x: 0, y: 0 }; }
        getExtent() { return new TVRect(); }
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
global.ofSelectable = 1;
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
    _setClientExtent() { this.refresh(); }
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
root.appendChild(viewport);items.forEach(item=>viewport.appendChild(item));
root.querySelector = (selector) => ({
    "[data-tv-list-viewport]": viewport,
    "[data-tv-list-track]": track,
    "[data-tv-list-cells]": cells,
    "[data-tv-list-thumb]": thumb,
    "[data-tv-list-backward]": backward,
    "[data-tv-list-forward]": forward,
        ".tv-vlist-scrollbar": scrollbar,
        ".tv-scrollbar-y": scrollbar,
        ".tv-scrollbar": scrollbar,
    }[selector] || null);

const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVListViewer");
const end = source.indexOf("\nclass TVScroller", start);
eval(source.slice(source.indexOf('function viewAcceptsInput'), source.indexOf('\nfunction owningDesktop'))
    + source.slice(start, end) + "\nglobalThis.TestList = TVListBox;");

const selected = [];
const activated = [];
    const list = new TestList(new TVRect());
    list.bindRoot(root);
list.items = ["zero", "one", "two", "three", "four"];
list.focusItem(1, { scroll: false });
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


@pytest.mark.skipif(NODE is None, reason="Node.js is required for list state tests")
@pytest.mark.parametrize("kind", ["plain", "box", "grid", "outline"])
def test_list_view_selection_is_independent_of_current_item_and_notifications(kind):
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect(0,0,24,6);
const kind=process.argv[2],owner=new TV.TVGroup(bounds),input=new TV.TVInputLine(bounds,20);
const list=kind==='plain'?new TV.TVListViewer(bounds):kind==='box'?new TV.TVListBox(bounds):kind==='grid'?new TV.TVGridView(bounds,[{title:'A',width:12},{title:'B',width:8}]):new TV.TVOutline(bounds);
if(kind==='grid'){list.setRows([['First','1'],['Second','2'],['Third','3']]);list.selectCell(2,1,{scroll:false});}
else if(kind==='outline')list.setTree([{key:'a',label:'First',children:[{key:'b',label:'Second'},{key:'c',label:'Third'}]}],null,{expandAll:true});
else list.setItems(['First','Second','Third'],0);
owner.insertAll([input,list]);input.select();let selections=0,activations=0;
list.bind({onSelect:()=>selections++,onActivate:()=>activations++});
list.focusItem(2,{scroll:false});assert.equal(list.selectedIndex,2);assert.equal(owner.current,input);assert.equal(selections,0);assert.equal(activations,0);
assert.equal(list.select(),list);assert.equal(owner.current,list);assert(list.getState(TV.sfSelected));assert.equal(list.selectedIndex,2,'Select cleared the current item');
if(kind==='grid')assert.equal(list.selectedColumn,1,'Select changed the current grid column');
assert.equal(list.focused,2);assert.equal(selections,0);assert.equal(activations,0);assert(!list.getState(TV.sfFocused));
list.focusItem(1,{scroll:false});assert.equal(list.selectedIndex,1);assert.equal(owner.current,list);assert.equal(selections,0);
list.focusItemNum(-9);assert.equal(list.selectedIndex,0);list.focusItemNum(99);assert.equal(list.selectedIndex,2);
for(const invalid of [NaN,Infinity,undefined,1.5]){list.focusItemNum(invalid);assert.equal(list.selectedIndex,2);}
list.selectItem(1);assert.equal(list.selectedIndex,1);assert.equal(selections,1);assert.equal(activations,0);
owner.remove(list);list.select();assert.equal(list.selectedIndex,1);assert.equal(list.owner,null);assert.equal(selections,1);
list.setItems([],-1);list.focusItemNum(0);assert.equal(list.selectedIndex,-1);
'''
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0]), kind], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_ascii_and_color_select_keep_their_value_and_inherited_view_contract():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    assert DIALOG_PATHS[0].read_bytes() == DIALOG_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
eval(fs.readFileSync(process.argv[1],'utf8'));eval(fs.readFileSync(process.argv[2],'utf8'));
const TV=window.THelpViewerTV,bounds=new TV.TVRect(0,0,32,8),owner=new TV.TVGroup(bounds),input=new TV.TVInputLine(bounds,20);
const ascii=new TV.TVAsciiTable(bounds),color=new TV.TVColorSelector(bounds);owner.insertAll([input,ascii,color]);
ascii.setCode(65);color.setColor(12);input.select();assert.equal(ascii.select(),ascii);assert.equal(owner.current,ascii);
assert.equal(ascii.cells.filter(cell=>cell.commandData.selected).length,1);assert.equal(ascii.cells[65].commandData.selected,true);
assert.equal(color.select(),color);assert.equal(owner.current,color);assert.equal(color.selected,12);
assert.equal(color.buttons.filter(button=>button.commandData.selected).length,1);assert.equal(color.buttons[12].commandData.selected,true);
assert.equal(document.activeElement,null);assert(!ascii.getState(TV.sfFocused));assert(!color.getState(TV.sfFocused));
'''
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0]), str(DIALOG_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for list state tests")
def test_disabled_lists_keep_model_updates_visibility_and_explicit_selection_separate():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
global.getComputedStyle=()=>({getPropertyValue:()=>''});
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV,bounds=new TV.TVRect(0,0,20,5);
const plain=new TV.TVListViewer(bounds),box=new TV.TVListBox(bounds),tree=new TV.TVOutline(bounds);
const grid=new TV.TVGridView(bounds,[{title:'A',width:10},{title:'B',width:10}]);
plain.setItems(['First','Second'],1);box.newList(['First','Second']);box.focusItem(1,{scroll:false});
tree.setTree([{key:'parent',label:'Parent',children:[{key:'child',label:'Child'}]}],'child',{expandAll:true});
grid.setRows([['First','1'],['Second','2']]);grid.selectCell(1,1,{scroll:false});
for(const view of [plain,box,tree,grid]){
 let selections=0;view.bind({onSelect:()=>selections++,onActivate:()=>selections++});
 const data=view.items;view.setState(TV.sfFocused,true);view.setState(TV.sfDisabled,true);
 view.focus();view.focusSelectedItem();view.selectItem(0);
 assert.equal(view.getState(TV.sfFocused),false);assert.equal(view.selectedIndex,1);assert.equal(selections,0);
 view.focusItem(0,{scroll:false});view.focusItem(1);
 assert.equal(view.selectedIndex,1,'Disabled view rejected programmatic selection updates');assert.equal(view.items,data);
 assert(view.draw().includes('aria-disabled="true"'));
 view.hide();assert(/\bhidden\b/.test(view.draw().trim().match(/^<div[^>]*>/)[0]),'Redraw dropped hidden state');
 view.show();assert.equal(view.getState(TV.sfDisabled),true);
 const outside={closest:()=>({dataset:{tvListIndex:'0'}})};
 for(const key of ['Enter','ArrowRight','ArrowDown'])view.handleEvent(new TV.TVEvent(TV.evKeyDown,{nativeEvent:{key,target:outside}}));
 assert.equal(view.selectedIndex,1);assert.equal(selections,0);
 view.setState(TV.sfDisabled,false);view.selectItem(0);
 assert.equal(view.selectedIndex,0);assert.equal(selections,1,'Enabled explicit selection lost its callback');
 const owner=new TV.TVGroup(new TV.TVRect());owner.insert(view);owner.setState(TV.sfDisabled,true);
 view.selectItem(1);assert.equal(view.selectedIndex,0);assert.equal(selections,1,'Disabled owner allowed a selection callback');
 view.focusItem(1,{scroll:false});assert.equal(view.selectedIndex,1,'Disabled owner blocked a model update');
 view.focus();assert.equal(view.getState(TV.sfFocused),false);
 owner.setState(TV.sfDisabled,false);view.selectItem(0);assert.equal(selections,2);
}
'''
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for cluster state tests")
def test_disabled_clusters_preserve_masks_values_and_premount_markup():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){},activeElement:null};
global.getComputedStyle=()=>({getPropertyValue:()=>''});
eval(fs.readFileSync(process.argv[1],'utf8'));
const TV=window.THelpViewerTV,bounds=new TV.TVRect(0,0,20,5);
const options=()=>[{label:'First',checked:true,state:1},{label:'Second',state:2},{label:'Fixed disabled',disabled:true}];
const large=new TV.TVCheckBoxes(bounds,Array.from({length:70},(_,index)=>({label:String(index),disabled:index===2})));
large.setData(1n<<65n);
const views=[new TV.TVCheckBoxes(bounds,options()),new TV.TVRadioButtons(bounds,options()),
 new TV.TVMultiCheckBoxes(bounds,options()),large];
const controls=html=>html.match(/<(?:input|button)\b[^>]*>/g)||[];
for(const view of views){
 const value=view.getData(),mask=view.enableMask,selected=view.sel,states=view.strings.map((_option,index)=>view.multiMark(index));
 view.setState(TV.sfFocused,true);view.setState(TV.sfDisabled,true);
 assert.equal(view.getState(TV.sfFocused),false,'Disabled cluster retained focus state');
 assert.equal(view.getState(TV.sfDisabled),true);
 assert(view.draw().includes('aria-disabled="true"'));
 assert(controls(view.draw()).every(tag=>/\bdisabled\b/.test(tag)),'Pre-mount choices remain enabled');
 view.press(1);view.movedTo(1);view.focus();
 assert.equal(view.sel,selected);assert.equal(view.getData(),value);assert.equal(view.enableMask,mask);
 assert.deepEqual(view.strings.map((_option,index)=>view.multiMark(index)),states);
 assert.equal(view.buttonState(1),true,'Group state overwrote the individual enable mask');
 view.setButtonState(view.bit(1),false);view.setState(TV.sfDisabled,false);
 assert.equal(view.getData(),value);assert.equal(view.buttonState(1),false);
 assert.equal(view.strings[2].disabled,true);
 assert.deepEqual(controls(view.draw()).map(tag=>/\bdisabled\b/.test(tag)),
  view.strings.map((option,index)=>!view.buttonState(index)||Boolean(option.disabled)));
 view.press(1);assert.equal(view.getData(),value,'Reenabled group lost a disabled option');
 view.setState(TV.sfDisabled,true);
 view.setItems([{label:'Replacement',checked:true,state:2},{label:'Disabled',disabled:true}]);
 assert.equal(view.getState(TV.sfDisabled),true,'Option replacement cleared the group state');
 assert(controls(view.draw()).every(tag=>/\bdisabled\b/.test(tag)));
 view.setState(TV.sfDisabled,false);
 const owner=new TV.TVGroup(new TV.TVRect());owner.insert(view);
 for(const flag of [TV.sfDisabled,TV.sfVisible]){
  owner.setState(flag,flag===TV.sfDisabled);const current=view.getData(),cursor=view.sel,states=view.strings.map((_option,index)=>view.multiMark(index));
  view.press(0);view.movedTo(1);view.focus();
  assert.equal(view.getData(),current,'Unavailable owner allowed a choice press');assert.equal(view.sel,cursor);
  assert.deepEqual(view.strings.map((_option,index)=>view.multiMark(index)),states);
  view.setData(current);assert.equal(view.getData(),current);owner.setState(flag,flag!==TV.sfDisabled);
 }
}
'''
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for multi-check data tests")
def test_multicheck_data_round_trips_packed_states_and_nested_groups():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={activeElement:null,addEventListener(){}};
global.getComputedStyle=()=>({getPropertyValue:()=>''});
eval(fs.readFileSync(process.argv[1],'utf8'));const TV=window.THelpViewerTV,bounds=new TV.TVRect(0,0,30,5);
const multi=new TV.TVMultiCheckBoxes(bounds,[{label:'A',state:1},{label:'B',state:2}]);
assert.equal(multi.getData(),9,'multi-check initial data differs from its visible states');
assert.equal(multi.multiMark(0),1);assert.equal(multi.multiMark(1),2);
assert.equal(Object.hasOwn(multi.strings[0],'state'),false,'live state has a second options mirror');
assert.deepEqual([TV.cfOneBit,TV.cfTwoBits,TV.cfFourBits,TV.cfEightBits],[0x0101,0x0203,0x040f,0x08ff]);
multi.press(0);assert.equal(multi.getData(),10);multi.press(0);assert.equal(multi.getData(),8);
multi.setData(5);assert.equal(multi.multiMark(0),1);assert.equal(multi.multiMark(1),1);
assert.equal((multi.draw().match(/\[X\]/g)||[]).length,2);
multi.setData(0x80000009);multi.press(0);assert.equal(multi.getData(),0x8000000a,'Press changed unused record bits');
for(const index of [-1,2,1.5,NaN,Infinity,'0',undefined])assert.equal(multi.multiMark(index),0);
for(const value of [-1,3,NaN,Infinity,Number.MAX_SAFE_INTEGER,'5',{},1n<<32n]){
 const before=multi.getData();assert.throws(()=>multi.setData(value));assert.equal(multi.getData(),before,'invalid SetData partly changed the record');
}
const options=multi.strings,value=multi.getData();assert.throws(()=>multi.setItems([{label:'Bad',state:3}]));
assert.equal(multi.strings,options);assert.equal(multi.getData(),value);
multi.setItems([{label:'New',state:2}]);assert.equal(multi.getData(),2);assert.equal(multi.multiMark(0),2);
for(const [range,flags,states,initial,expected] of [[2,TV.cfOneBit,' X',1,0],[6,TV.cfFourBits,'012345',4,5],[4,TV.cfEightBits,' ab?',3,0]]){
 const view=new TV.TVMultiCheckBoxes(bounds,[{label:'A',state:initial},{label:'B',state:1}],range,flags,states);
 view.press(0);assert.equal(view.multiMark(0),expected);assert.equal(view.multiMark(1),1);
 assert.equal(view.getData(),expected+2**(flags>>8));
}
for(const count of [20,40]){
 const view=new TV.TVMultiCheckBoxes(bounds,Array.from({length:count},(_,index)=>({label:String(index),state:index===count-1?2:0})));
 assert.equal(typeof view.getData(),'bigint');assert.equal(view.multiMark(count-1),2);
 assert.equal(typeof view.enableMask,count>31?'bigint':'number');view.press(count-1);
 assert.equal(view.multiMark(count-1),0);view.setData(1n<<BigInt(2*(count-1)));assert.equal(view.multiMark(count-1),1);
 const stored=view.getData();view.setButtonState(view.bit(count-1),false);view.press(count-1);assert.equal(view.getData(),stored);
}
assert.throws(()=>new TV.TVMultiCheckBoxes(bounds,[],[' ','X','?']),TypeError);
assert.throws(()=>new TV.TVMultiCheckBoxes(bounds,[],3,TV.cfOneBit,' X?'),RangeError);
assert.throws(()=>new TV.TVMultiCheckBoxes(bounds,[],3,TV.cfTwoBits,' X'),RangeError);
const group=new TV.TVGroup(bounds),nested=new TV.TVGroup(bounds),input=new TV.TVInputLine(bounds,30);
const checks=new TV.TVCheckBoxes(bounds,[{label:'Check',checked:true}]);input.setData('keep');
nested.insertAll([multi,checks]);group.insertAll([input,nested]);const snapshot=group.getData();
input.setData('changed');multi.setData(0);checks.setData(0);group.setState(TV.sfDisabled,true);group.setData(snapshot);
assert.deepEqual(group.getData(),snapshot);assert.equal(multi.multiMark(0),2);
'''
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0])], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the picture validator test")
def test_registration_token_picture_validator_formats_without_changing_old_tokens():
    script = r"""
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
global.TVRect = class {};
global.sfVisible=1;global.sfDisabled=0x100;
global.ofSelectable = 1;
global.TVView = class { constructor() { this.root = null; this.state=sfVisible; } getState(mask){return (this.state & mask)=== mask;} clearEvent(event) { event.what = 0; } };
global.evBroadcast = 0x0200;
global.evKeyDown = 0x0010;
global.evCommand = 0x0100;
const start = source.indexOf('class TVPXPictureValidator');
const end = source.indexOf('\nclass TVGroup extends', start);
eval(source.slice(source.indexOf('function viewAcceptsInput'), source.indexOf('\nfunction owningDesktop')) + source.slice(start, end)
    + '\nglobalThis.Picture = TVPXPictureValidator; globalThis.Input = TVInputLine;');
const input = new Input(new TVRect(), 128).setValidator(
    new Picture('!!!!!-!!!!!-!!!!!-!!!!!-!!!!!', true));
input.setData('abcdefghjklmnpqrstvwxyz234');
if (input.getData() !== 'ABCDE-FGHJK-LMNPQ-RSTVW-XYZ23') {
    throw new Error('Token picture formatting failed: ' + input.getData());
}
if (!input.valid()) { throw new Error('Formatted token was rejected'); }
input.root = { value: 'abcdeF' };
input.handleEvent({ what: evBroadcast, infoPtr: input, nativeEvent: { type: 'input', target: input.root } });
if (input.root.value !== 'ABCDE-F') { throw new Error('Typing did not fill the separator'); }
input.root = null;
const oldToken = 'legacy-enrollment-token_with-43-characters-123';
input.setData(oldToken);
if (input.valid()) { throw new Error('Legacy token format was accepted'); }
"""
    result = subprocess.run([NODE, "-e", script, str(CORE_PATHS[0])], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the filter validator test")
def test_filter_validator_rejects_text_and_preserves_optional_numeric_input():
    script = r"""
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
global.TVRect = class {};
global.sfVisible=1;global.sfDisabled=0x100;
global.ofSelectable = 1;
global.TVView = class { constructor() { this.root = null; this.state=sfVisible; } getState(mask){return (this.state & mask)=== mask;} clearEvent(event) { event.what = 0; } };
global.evBroadcast = 0x0200;
global.evKeyDown = 0x0010;
global.evCommand = 0x0100;
const start = source.indexOf('class TVFilterValidator');
const end = source.indexOf('\nclass TVGroup extends', start);
eval(source.slice(source.indexOf('function viewAcceptsInput'), source.indexOf('\nfunction owningDesktop')) + source.slice(start, end)
    + '\nglobalThis.Filter = TVFilterValidator; globalThis.Input = TVInputLine; globalThis.Email = TVEmailValidator;');
const email = new Email();
const login = new Email(false, true);
for (const value of ['admin', 'local-development-admin', 'mario.lacko', 'mário', 'user@example.test']) {
    if (!login.isValid(value)) { throw new Error('Login validator rejects an existing identity'); }
}
for (const value of ['bad@example', 'a@@b.test', 'bad user', 'a'.repeat(65), '']) {
    if (login.isValid(value)) { throw new Error('Login validator accepts an invalid identity'); }
}
for (const value of ['reader@example.test', 'a+b@sub.example.test', 'jan.novak@example.sk']) {
    if (!email.isValid(value) || !email.isValidInput(value)) { throw new Error('Valid email rejected'); }
}
for (const value of ['', 'reader', 'reader@', 'reader@example', 'a@@b.test', 'a @b.test', 'a@b.test\n', 'a\x00@b.test', 'a@b\x7f.test', 'a'.repeat(255) + '@b.test']) {
    if (email.isValid(value)) { throw new Error('Invalid email accepted'); }
}
for (const value of ['', 'a', 'a@', 'a@b', 'a@b.']) {
    if (!email.isValidInput(value)) { throw new Error('Cannot type incomplete email'); }
}
if (!new Email(true).isValid('') || email.isValidInput('a@@b.test') || email.isValidInput('a @b.test')) {
    throw new Error('Optional email or invalid edit validation failed');
}
const validator = new Filter('0123456789');
for (const value of ['', '0', '64', '256', '999']) {
    if (!validator.isValid(value) || !validator.isValidInput(value, false)) {
        throw new Error('Numeric filter rejected digits or empty input: ' + value);
    }
}
for (const value of ['text', '1e2', '-1', '1.5', '64 MB', '１２']) {
    if (validator.isValid(value) || validator.isValidInput(value, false)) {
        throw new Error('Numeric filter accepts text: ' + value);
    }
}
const input = new Input(new TVRect(), 3).setValidator(validator);
if (!(input.eventMask & evBroadcast)) { throw new Error('Input ignores validation broadcasts'); }
input.setData('64');
input.root = { value: '64a' };
const edit = () => input.handleEvent({ what: evBroadcast, infoPtr: input, nativeEvent: { type: 'input', target: input.root } });
edit();
if (input.getData() !== '64') { throw new Error('Invalid edit was not rejected'); }
input.root.value = '256'; edit();
if (input.data !== '256') { throw new Error('Valid edit was rejected'); }
input.root.value = ''; edit();
if (input.data !== '' || !input.valid()) { throw new Error('Cannot clear inherited capacity'); }
input.root = null; input.setData('1234');
if (input.getData() !== '123') { throw new Error('Input maximum length changed'); }
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
global.sfVisible = 0x02;
global.sfDisabled = 0x0100;
global.ofSelectable = 1;
global.TVView = class {
    constructor() { this.viewId = "test-view"; this.state = sfVisible; }
    getState(mask) { return (this.state & mask) === mask; }
    static _roleClassNames(value = "") { return value; }
    static _viewBoundsStyle() { return ""; }
    _drawAttrs(attrs = {}) { return attrs; }
    _paletteStyle() { return ""; }
    drawView() { return this; }
};
global.evBroadcast = 0x0200;
global.document = {activeElement: null};
const choiceStart = source.indexOf("let tvChoiceGroupId");
const choiceEnd = source.indexOf("\nclass TVButton extends", choiceStart);
eval(source.slice(source.indexOf('function viewAcceptsInput'), source.indexOf('\nfunction owningDesktop')) + source.slice(choiceStart, choiceEnd)
    + "\nglobalThis.TestChecks = TVCheckBoxes; globalThis.TestRadios = TVRadioButtons; globalThis.TestMulti = TVMultiCheckBoxes;");

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
for (const View of [TestChecks, TestRadios, TestMulti]) {
    const view = new View(new TVRect(), [{label:'Text'}]);
    view.state = 0;
    if (!/\bhidden\b/.test(view.draw())) { throw new Error('Hidden cluster reappeared during draw'); }
}
const radios = new TestRadios(new TVRect(), [{ label: "A", checked: true }, { label: "B" }]).draw();
const radioNames = Array.from(radios.matchAll(/name="([^"]+)"/g), (match) => match[1]);
if ((radios.match(/type="radio"/g) || []).length !== 2
    || radioNames.length !== 2 || radioNames[0] !== radioNames[1]) {
    throw new Error("radio options are not one native group");
}
const stateful = new TestChecks(new TVRect(), [{label:'A',checked:true},{label:'B'}]);
stateful.setData(2);
const marks = html => Array.from(html.matchAll(/class="tv-(?:checkbox|radio)-mark"[^>]*>([^<]*)</g), match => match[1]);
if (stateful.getData() !== 2 || JSON.stringify(marks(stateful.draw())) !== '["[ ]","[X]"]'
    || stateful.strings[0].checked || !stateful.strings[1].checked) throw Error('Pre-mount checkbox value did not control its glyphs');
stateful.setButtonState(2,false);
if (!stateful.draw().includes('class="tv-checkbox-item is-disabled"')) throw Error('Pre-mount enabled mask lost');
const radioState = new TestRadios(new TVRect(), [{label:'A',checked:true},{label:'B',checked:true},{label:'C'}]);
if (radioState.getData() !== 1) throw Error('Initial radio state is not exclusive');
radioState.setData(2);
if (JSON.stringify(marks(radioState.draw())) !== '["( )","( )","(•)"]') throw Error('Radio glyphs depend on CSS or stale options');
const large = new TestChecks(new TVRect(), Array.from({length:64},(_,index)=>({label:String(index),checked:index===63})));
if (large.getData() !== 1n<<63n) throw Error('Large initial checkbox mask lost');
large.setData(1n<<40n);
const largeMarks=marks(large.draw());
if (largeMarks[40] !== '[X]' || largeMarks[63] !== '[ ]') throw Error('Large pre-mount checkbox mask lost');
for (const view of [stateful,large,radioState]) {
    const stored = view.getData();
    for (const index of [-1,view.strings.length,32 + view.strings.length,0.5,NaN,Infinity,'0',undefined]) {
        if (view.buttonState(index) || view.mark(index)) throw Error('Invalid cluster index wrapped into an existing bit');
        view.press(index);
        if (view.getData() !== stored) throw Error('Invalid cluster Press changed a stored choice');
    }
}
const multiState = new TestMulti(new TVRect(), [{label:'A',state:0}]);
multiState.press(0);
if (multiState.multiMark(0) !== 1) throw Error('Pre-mount multi-check Press requires a browser button');
multiState.setButtonState(1,false);multiState.press(0);
if (multiState.multiMark(0) !== 1) throw Error('Pre-mount disabled multi-check accepted Press');
multiState.setButtonState(1,true);multiState.press(0);
if (multiState.multiMark(0) !== 2) throw Error('Reenabled multi-check lost its stored state');

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
