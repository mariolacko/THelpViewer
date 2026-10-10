from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/server/converter/assets/tv-core.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the menu keyboard test")
def test_shared_menu_controller_maps_turbovision_keyboard_commands():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor() {
        this.dataset = {};
        this.attributes = new Map();
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
    contains() { return false; }
    matches() { return false; }
    querySelector() { return null; }
    querySelectorAll() { return []; }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) || null; }
    getBoundingClientRect() { return { width: 8, height: 16, top: 0, left: 0, right: 8 }; }
}

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
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement() { return new FakeElement(); },
};
global.getComputedStyle = () => ({ getPropertyValue() { return ""; } });

eval(fs.readFileSync(process.argv[1], "utf8"));
const TV = window.THelpViewerTV;
eval(fs.readFileSync(process.argv[2], "utf8"));
const guestAccount=TV.buildAccountMenu(null);
if(guestAccount.command!=='account-login'||guestAccount.subMenu)throw new Error('Guest account item is not Login');
for(const role of ['member','admin']){
 const account=TV.buildAccountMenu({authenticated:true,user:{username:'test',display_name:'Test ~<Name>~',role}});
 const commands=account.subMenu.entries().flatMap(item=>[item.command,...(item.subMenu?.entries()||[]).map(child=>child.command)]);
 if(commands.includes('account-server-configuration')!==(role==='admin')||commands.includes('account-registration-token')!==(role==='admin'))throw new Error('Account role visibility is incorrect');
 if(!commands.includes('account-colors')||!commands.includes('account-logout'))throw new Error('User configuration/sign-out missing');
 if(commands.includes('account-rebuild-dos')!==(role==='admin')||commands.includes('account-rebuild-midi')!==(role==='admin')||commands.includes('account-users')!==(role==='admin'))throw new Error('Administrator menu permissions are incorrect');
 if(account.subMenu.entries()[0].name.replaceAll('~','')!=='Account')throw new Error('Account menu label was not renamed');
 const bar=new TV.TVApplicationMenuBar(new TV.TVRect(),TV.NewMenu(account),account);
 if(!bar.draw().includes('Test ~&lt;Name&gt;~')||bar.menuMnemonic(account)!=='')throw new Error('User name was interpreted as menu markup');
}
for(const role of ['member','admin']){
 const account=TV.buildAccountMenu({authenticated:true,development:true,user:{username:'local',display_name:'Local',role}});
 const commands=account.subMenu.entries().flatMap(item=>[item.command,...(item.subMenu?.entries()||[]).map(child=>child.command)]);
 if(commands.includes('account-rebuild-dos')!==(role==='admin')||commands.includes('account-rebuild-midi')!==(role==='admin'))throw new Error('Local rebuild menu permissions are incorrect');
 if(!commands.includes('account-colors'))throw new Error('Colors is unavailable to a local member');
}

const linkedSecond = TV.NewItem("~S~econd", "F4", TV.kbF3, "second", 20);
const linkedFirst = TV.NewItem("~F~irst", "F3", TV.kbF3, "first", 10, linkedSecond);
const linkedMenu = TV.NewMenu(linkedFirst);
const linkedMarkup = new TV.TVMenuView(new TV.TVRect(), linkedMenu).draw();
if (linkedMenu.items !== linkedFirst || linkedMenu.deflt !== linkedFirst
    || linkedFirst.next !== linkedSecond || linkedMenu.entries().length !== 2
    || linkedFirst.param !== "F3" || !linkedMarkup.includes('class="tv-menu-hotkey">F3')) {
    throw new Error("source-shaped linked menu construction failed");
}

const fileItem = new TV.TVMenuItem("~O~pen HELP", "bundle-open");
const fileButton = new FakeElement();
fileButton.dataset.tvMenuItemId = fileItem._menuId;
fileButton.dataset.tvCommand = "wrong-dom-command";
const menuRoot = new FakeElement();
fileButton.closest = (selector) => ({
    "button, a": fileButton,
}[selector] || null);
menuRoot.querySelectorAll = (selector) => selector === "[data-tv-menu-item-id]" ? [fileButton] : [];
const menuView = new TV.TVMenuView(new TV.TVRect(), TV.NewMenu(fileItem)).bindRoot(menuRoot);
const cachedMenu = new TV.TVMenuView(new TV.TVRect(), TV.NewMenu(fileItem));
const cachedRoot = new FakeElement();
const cachedToggle = new FakeElement();
const cachedPopup = new FakeElement();
cachedPopup.children = [];
cachedPopup.hidden = true;
cachedRoot.querySelector = () => { throw new Error("menu root was searched after binding"); };
cachedMenu.root = new FakeElement();
cachedMenu.menuRoots = [cachedRoot];
cachedMenu.rootControls.set(cachedRoot, { toggle: cachedToggle, popup: cachedPopup });
const originalFrame = global.requestAnimationFrame;
global.requestAnimationFrame = () => 0;
cachedMenu.openMenu(cachedRoot, { focusFirst: false });
if (cachedMenu.activePopup !== cachedPopup || cachedPopup.hidden ||
    cachedToggle.getAttribute("aria-expanded") !== "true") {
    throw new Error("menu did not open from its retained control references");
}
const cachedSubmenuRoot = new FakeElement();
const cachedSubmenuToggle = new FakeElement();
const cachedSubmenuPopup = new FakeElement();
cachedSubmenuPopup.children = [];
cachedSubmenuPopup.hidden = true;
cachedMenu.submenuControls.set(cachedSubmenuToggle, {
    root: cachedSubmenuRoot, popup: cachedSubmenuPopup,
});
cachedMenu.submenuByPopup.set(cachedSubmenuPopup, {
    root: cachedSubmenuRoot, toggle: cachedSubmenuToggle, parentPopup: cachedPopup,
});
if (!cachedMenu.openSubmenu(cachedSubmenuToggle, { focusFirst: false }) ||
    cachedSubmenuPopup.hidden || cachedMenu.activePopup !== cachedSubmenuPopup) {
    throw new Error("submenu did not open from its retained control references");
}
cachedMenu.closeSubmenu(cachedSubmenuPopup, { focusToggle: false });
if (!cachedSubmenuPopup.hidden || cachedMenu.activePopup !== cachedPopup) {
    throw new Error("submenu did not return to its retained parent popup");
}
cachedMenu.closeMenus({ restoreFocus: false });
if (!cachedPopup.hidden || cachedToggle.getAttribute("aria-expanded") !== "false") {
    throw new Error("menu did not close using its retained control references");
}
global.requestAnimationFrame = originalFrame;
let dispatched = null;
const app = new TV.TVView(new TV.TVRect());
app.handleEvent = (event) => { dispatched = event; };
menuView.owner = app;
let menuMouseEvents = 0;
const handleMenuEvent = menuView.handleEvent.bind(menuView);
menuView.handleEvent = (event) => {
    if (event.what === TV.evMouseDown) { menuMouseEvents += 1; }
    handleMenuEvent(event);
};
const commandController = Object.create(TV.TVMenuController.prototype);
commandController.menuView = menuView;
commandController.commandTarget = app;
commandController.onCommand({ target: fileButton, preventDefault() {} });
if (fileButton._tvMenuItem !== fileItem || dispatched?.command !== "bundle-open"
    || dispatched.infoPtr !== fileItem || menuMouseEvents !== 1) {
    throw new Error("menu click did not pass through TVMenuView.handleEvent to the application");
}

class LinkedItem extends TV.TVMenuItem {
    getUrl() { return '/?file=sample.json.gz&topic=7'; }
}
const linkedItem = new LinkedItem('Topic', 'bundle-open');
const linkMarkup = new TV.TVMenuView(new TV.TVRect(), TV.NewMenu(linkedItem)).draw();
if (!linkMarkup.includes('<a class="tv-menu-popup-item"')
    || !linkMarkup.includes('href="/?file=sample.json.gz&amp;topic=7"')) {
    throw new Error('menu navigation fallback did not render a real anchor');
}
fileButton.tagName = 'A';
let defaultPrevented = false;
commandController.onCommand({ target: fileButton, ctrlKey: true,
    preventDefault() { defaultPrevented = true; } });
if (defaultPrevented || menuMouseEvents !== 1) {
    throw new Error('Ctrl-click should use the browser link fallback');
}
commandController.onCommand({ target: fileButton,
    preventDefault() { defaultPrevented = true; } });
if (!defaultPrevented || menuMouseEvents !== 2) {
    throw new Error('ordinary anchor click bypassed TVEvent');
}
menuMouseEvents = 1;

const mouseSubmenu = TV.NewSubMenu("~N~ested", 0, TV.NewMenu(fileItem));
const mouseToggle = new FakeElement();
mouseToggle._tvMenuItem = mouseSubmenu;
mouseToggle.matches = () => false;
menuView.itemElements.set(mouseSubmenu, mouseToggle);
const mousePopup = new FakeElement();
mousePopup.hidden = true;
mousePopup.matches = (selector) => selector === "[data-tv-submenu-popup]";
const mouseRoot = new FakeElement();
mouseRoot.children = [mousePopup];
mouseToggle.closest = (selector) => ({
    "button, a": mouseToggle,
    "[data-tv-submenu-root]": mouseRoot,
}[selector] || null);
let openedSubmenu = 0;
menuView.openSubmenu = () => { openedSubmenu += 1; mousePopup.hidden = false; return true; };
menuView.closeSubmenu = () => { throw new Error("click closed a submenu opened on hover"); };
menuView.activeRoot = menuRoot;
commandController.onHover({ target: mouseToggle, relatedTarget: null });
commandController.onCommand({ target: mouseToggle, preventDefault() {} });
if (openedSubmenu !== 2 || menuView.current !== mouseSubmenu || menuMouseEvents !== 2) {
    throw new Error("submenu hover and click bypassed TVMenuView.handleEvent");
}

const statusItem = new TV.TVStatusItem("Open", TV.kbF3, "status-open", "sample");
const statusButton = new FakeElement();
statusButton.dataset.tvCommand = "wrong-dom-command";
statusButton.closest = (selector) => selector === "button, a" ? statusButton : null;
const statusRoot = new FakeElement();
statusRoot.querySelectorAll = (selector) => selector === "button.tv-status-item" ? [statusButton] : [];
const statusLine = new TV.TVStatusLine(new TV.TVRect(),
    TV.NewStatusDef(0, 0xffff, [statusItem])).bindRoot(statusRoot);
commandController.root = { querySelector(selector) {
    return selector === "[data-tv-status-line]" ? statusRoot : null;
} };
commandController.onCommand({ target: statusButton, preventDefault() {} });
if (statusButton._tvStatusItem !== statusItem || dispatched?.command !== "status-open"
    || dispatched.infoPtr !== statusItem) {
    throw new Error("status click did not dispatch its TVStatusItem");
}

const nestedSubmenu = TV.NewSubMenu(
    "Nested",
    0,
    TV.NewMenu(TV.NewLine()),
);
const nestedMenuMarkup = new TV.TVMenuBox(
    new TV.TVRect(),
    TV.NewMenu(nestedSubmenu),
).draw();
if (!nestedMenuMarkup.includes('class="tv-submenu-root"')
    || !nestedMenuMarkup.includes('class="tv-menu-popup-separator"')
    || nestedMenuMarkup.includes('data-tv-menu-toggle')) {
    throw new Error("a separator inside a submenu erased the complete Contents item");
}

function keyEvent(key, extra = {}) {
    return {
        key,
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; },
        ...extra,
    };
}

const toggleA = { _tvMenuItem: new TV.TVSubMenu("~X~ system") };
const toggleB = { _tvMenuItem: new TV.TVSubMenu("~H~elp") };
const rootA = { id: "system", querySelector() { return toggleA; } };
const rootB = { id: "help", querySelector() { return toggleB; } };
const controller = Object.create(TV.TVMenuController.prototype);
controller.menuView = menuView;
controller.root = { querySelectorAll() { return []; } };
controller.onUnhandledKeyDown = null;
menuView.menuRoots = [rootA, rootB];
menuView.rootControls = new Map([
    [rootA, { toggle: toggleA, popup: toggleA }],
    [rootB, { toggle: toggleB, popup: toggleB }],
]);
menuView.topLevelActions = [];
menuView.activeRoot = null;
menuView.activePopup = null;
let opened = null;
let closed = 0;
menuView.openMenu = (root) => { opened = root; menuView.activeRoot = root; };
menuView.closeMenus = () => { closed += 1; menuView.activeRoot = null; };

const f10 = keyEvent("F10");
controller.onKeyDown(f10);
if (opened !== rootA || !f10.defaultPrevented) {
    throw new Error("F10 did not open the first menu through TVMenuView");
}
const secondF10 = keyEvent("F10");
controller.onKeyDown(secondF10);
if (closed !== 1 || menuView.activeRoot !== null) {
    throw new Error("F10 did not close an active menu");
}

const altH = keyEvent("h", { altKey: true });
controller.onKeyDown(altH);
if (opened !== rootB || !altH.defaultPrevented) {
    throw new Error("Alt mnemonic did not open its top-level menu");
}

const directItem = new TV.TVMenuItem("~D~irect", "direct-command");
const directAction = { _tvMenuItem: directItem };
menuView.activeRoot = null;
menuView.topLevelActions = [directAction];
const altD = keyEvent("d", { altKey: true });
controller.onKeyDown(altD);
if (dispatched?.command !== "direct-command" || dispatched.infoPtr !== directItem
    || !altD.defaultPrevented) {
    throw new Error("Alt mnemonic did not dispatch a direct menu-bar command");
}
menuView.topLevelActions = [];
menuView.activeRoot = rootB;

let move = 0;
menuView.moveSelection = (delta) => { move = delta; };
const down = keyEvent("ArrowDown");
controller.onKeyDown(down);
if (move !== 1 || !down.defaultPrevented) {
    throw new Error("ArrowDown did not move the menu selection");
}
const up = keyEvent("ArrowUp");
controller.onKeyDown(up);
if (move !== -1 || !up.defaultPrevented) {
    throw new Error("ArrowUp did not move the menu selection");
}

let switched = 0;
menuView.activePopup = toggleB;
menuView.switchRoot = (delta) => { switched = delta; };
controller.onKeyDown(keyEvent("ArrowRight"));
if (switched !== 1) { throw new Error("ArrowRight did not switch the top-level menu"); }
controller.onKeyDown(keyEvent("ArrowLeft"));
if (switched !== -1) { throw new Error("ArrowLeft did not switch the top-level menu"); }

const submenuPopup = { matches(selector) { return selector === "[data-tv-submenu-popup]"; } };
menuView.activePopup = submenuPopup;
let closedSubmenu = null;
menuView.closeSubmenu = (popup) => { closedSubmenu = popup; };
controller.onKeyDown(keyEvent("Escape"));
if (closedSubmenu !== submenuPopup) {
    throw new Error("Escape did not return from a submenu");
}

let activated = null;
const mnemonicItem = {
    _tvMenuItem: new TV.TVMenuItem("~O~pen", "open"),
    matches() { return false; },
};
menuView.activePopup = submenuPopup;
menuView.menuItems = () => [mnemonicItem];
menuView.markSelected = () => {};
menuView.activateItem = (item) => { activated = item; return true; };
if (!menuView.activateMnemonic("o") || activated !== mnemonicItem._tvMenuItem) {
    throw new Error("popup mnemonic did not activate its command through TVMenuView");
}

const foreignPopup = {};
const enabled = {
    _tvMenuItem: new TV.TVMenuItem("Enabled", "enabled"),
    closest() { return submenuPopup; },
};
const disabled = {
    _tvMenuItem: new TV.TVMenuItem("Disabled", "disabled").setDisabled(),
    closest() { return submenuPopup; },
};
const nested = {
    _tvMenuItem: new TV.TVMenuItem("Nested", "nested"),
    closest() { return foreignPopup; },
};
menuView.popupItems.set(submenuPopup, [enabled, disabled]);
const filtered = TV.TVMenuView.prototype.menuItems.call(menuView, submenuPopup);
if (filtered.length !== 1 || filtered[0] !== enabled) {
    throw new Error("menu navigation included disabled or nested items");
}
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0]), "www/assets/tv-shell.js"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_shell_and_bundle_use_the_shared_menu_controller():
    shell_paths = (
        Path("www/assets/tv-shell.js"),
        Path("thelpviewer/server/converter/assets/tv-shell.js"),
    )
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/server/converter/assets/turbovision.css"),
    )
    assert shell_paths[0].read_bytes() == shell_paths[1].read_bytes()
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert css_paths[0].read_bytes() == css_paths[1].read_bytes()

    shell = shell_paths[0].read_text(encoding="utf-8")
    bundle = bundle_paths[0].read_text(encoding="utf-8")
    css = css_paths[0].read_text(encoding="utf-8")
    assert "class TurboVisionMenus extends TVMenuController" in shell
    assert "new TVMenuController" in bundle
    assert "menuController.refresh()" in bundle
    assert "class TVApplicationMenuBar extends TVMenuBar" in shell
    assert "new TVApplicationMenuBar(new TVRect(), pageMenu(top), accountItem)" in shell
    assert "new TVApplicationMenuBar(new TVRect(), menuFromItems(topItems), accountItem)" in bundle
    assert "class TVMenuBar extends TVMenuView" not in shell
    assert "renderMenuRoot" not in bundle
    assert "new TVMenu([" not in shell + bundle
    core = Path("www/assets/tv-core.js").read_text(encoding="utf-8")
    assert "this.activateKeyCode(getKeyCode(key), key)" in core
    assert "this.menuView?.handleEvent(new TVEvent(evMouseDown" in core
    assert "_handleMenuShortcut" not in bundle
    assert "_menuGlobalsBound" not in bundle
    assert ".tv-menu-popup-item.is-menu-selected" in css


@pytest.mark.skipif(NODE is None, reason="Node.js is required for command-state behavior tests")
def test_dialog_manager_reports_commands_available_for_the_active_target():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVDialogManager");
const end = source.indexOf("// ── TVMessageBox", start);
const HOST_WINDOW_TOKEN = "__host__";
const TV_COMMANDS = {
    CLOSE: "close", CANCEL: "cancel", ZOOM: "zoom", NEXT: "next", PREVIOUS: "previous",
};
global.document = { querySelector: () => null, body: {} };
global.TVDesktop = class {};
eval(source.slice(start, end) + "\nglobalThis.TestDialogManager = TVDialogManager;");

const desktop = new TVDesktop();
desktop.root = { querySelector: () => null };
const manager = new TestDialogManager(desktop);
if (manager.canDispatchCommand(TV_COMMANDS.CLOSE) || manager.canDispatchCommand(TV_COMMANDS.NEXT)) {
    throw new Error("commands were enabled without a managed target");
}
const first = { isConnected: true };
manager.windows.set("first", first);
manager.windowCommands.set("first", { close() {}, zoom() {} });
manager.stackOrder = ["first"];
manager.activeTarget = "first";
if (!manager.canDispatchCommand(TV_COMMANDS.CLOSE) || !manager.canDispatchCommand(TV_COMMANDS.ZOOM)) {
    throw new Error("active window commands were not enabled");
}
if (manager.canDispatchCommand(TV_COMMANDS.NEXT) || manager.openWindowCount() !== 1) {
    throw new Error("Next was enabled for only one window");
}
manager.windows.set("second", { isConnected: true });
manager.stackOrder.push("second");
if (!manager.canDispatchCommand(TV_COMMANDS.NEXT) || !manager.canDispatchCommand(TV_COMMANDS.PREVIOUS)) {
    throw new Error("window cycling was not enabled for multiple targets");
}
manager.dialogs.set("dialog", { isOpen: () => true });
manager.stackOrder.push("dialog");
manager.activeTarget = "dialog";
if (!manager.canDispatchCommand(TV_COMMANDS.CLOSE) || manager.canDispatchCommand(TV_COMMANDS.ZOOM)) {
    throw new Error("dialog command state did not replace the active window state");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for command-state behavior tests")
def test_bundle_window_menu_reflects_dynamic_command_state():
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/server/converter/assets/turbovision.css"),
    )
    assert bundle_paths[0].read_bytes() == bundle_paths[1].read_bytes()
    assert css_paths[0].read_bytes() == css_paths[1].read_bytes()
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("class TVBundleApp");
const end = source.indexOf("// ── Bootstrap", start);
const TV_COMMANDS = { CLOSE: "close", ZOOM: "zoom", NEXT: "next", PREVIOUS: "previous" };
global.TVProgram = class {};
eval(source.slice(start, end) + "\nglobalThis.TestBundleApp = TVBundleApp;");

function item(command) {
    const classes = new Set();
    const attributes = new Map();
    return {
        dataset: { tvWindowCmd: command },
        disabled: false,
        tabIndex: 0,
        classList: {
            toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); },
            remove(name) { classes.delete(name); },
            contains(name) { return classes.has(name); },
        },
        setAttribute(name, value) { attributes.set(name, value); },
        getAttribute(name) { return attributes.get(name); },
        setDisabled(disabled) {
            this.disabled = Boolean(disabled);
            this.setAttribute("aria-disabled", this.disabled ? "true" : "false");
            this.classList.toggle("is-disabled", this.disabled);
        },
    };
}
const items = ["tile", "cascade", "list", "zoom", "next", "previous", "close"].map(item);
const menuState = {
    windowItems: new Map(items.map((entry) => [entry.dataset.tvWindowCmd, entry])),
    findItem: item("find"),
    findAgainItem: item("find-again"),
};
const app = Object.create(TestBundleApp.prototype);
app.menuState = menuState;
let windowCount = 0;
let targetCount = 0;
const enabledCommands = new Set();
app.dialogManager = {
    openWindowCount: () => windowCount,
    openTargets: () => new Array(targetCount),
    canDispatchCommand: (command) => enabledCommands.has(command),
};
app._updateWindowMenuState();
if (items.some((entry) => !entry.disabled || entry.getAttribute("aria-disabled") !== "true")) {
    throw new Error("window commands were enabled without open targets");
}

windowCount = 1;
targetCount = 1;
enabledCommands.add(TV_COMMANDS.CLOSE);
enabledCommands.add(TV_COMMANDS.ZOOM);
app._updateWindowMenuState();
const byCommand = Object.fromEntries(items.map((entry) => [entry.dataset.tvWindowCmd, entry]));
for (const command of ["tile", "cascade", "list", "zoom", "close"]) {
    if (byCommand[command].disabled || byCommand[command].classList.contains("is-disabled")) {
        throw new Error(`${command} was not enabled for an active window`);
    }
}
if (!byCommand.next.disabled || !byCommand.previous.disabled) {
    throw new Error("cycling was enabled for a single target");
}
enabledCommands.add(TV_COMMANDS.NEXT);
enabledCommands.add(TV_COMMANDS.PREVIOUS);
app._updateWindowMenuState();
if (byCommand.next.disabled || byCommand.previous.disabled) {
    throw new Error("cycling was not enabled for multiple targets");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(bundle_paths[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    css = css_paths[0].read_text(encoding="utf-8")
    assert '--tv-palette-menu-disabled-fg: #555555;' in css
    assert '--tv-menu-disabled: var(--tv-palette-menu-disabled-fg);' in css
    assert '.tv-menu-popup-item[aria-disabled="true"]' in css
