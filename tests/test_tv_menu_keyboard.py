from pathlib import Path
import shutil
import subprocess

import pytest


NODE = shutil.which("node")
CORE_PATHS = (
    Path("www/assets/tv-core.js"),
    Path("thelpviewer/converter/assets/tv-core.js"),
)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for the menu keyboard test")
def test_shared_menu_controller_maps_turbovision_keyboard_commands():
    assert CORE_PATHS[0].read_bytes() == CORE_PATHS[1].read_bytes()

    script = r"""
const fs = require("node:fs");

class FakeElement {
    constructor() {
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

const toggleA = { mnemonic: "x" };
const toggleB = { mnemonic: "h" };
const rootA = { id: "system", querySelector() { return toggleA; } };
const rootB = { id: "help", querySelector() { return toggleB; } };
const controller = Object.create(TV.TVMenuController.prototype);
controller.menuRoots = [rootA, rootB];
controller.topLevelActions = [];
controller.activeRoot = null;
controller.activePopup = null;
controller.onUnhandledKeyDown = null;
controller.menuMnemonic = (element) => element.mnemonic || "";
let opened = null;
let closed = 0;
controller.openMenu = (root) => { opened = root; controller.activeRoot = root; };
controller.closeMenus = () => { closed += 1; controller.activeRoot = null; };

const f10 = keyEvent("F10");
controller.onKeyDown(f10);
if (opened !== rootA || !f10.defaultPrevented) {
    throw new Error("F10 did not open the first menu");
}
const secondF10 = keyEvent("F10");
controller.onKeyDown(secondF10);
if (closed !== 1 || controller.activeRoot !== null) {
    throw new Error("F10 did not close an active menu");
}

const altH = keyEvent("h", { altKey: true });
controller.onKeyDown(altH);
if (opened !== rootB || !altH.defaultPrevented) {
    throw new Error("Alt mnemonic did not open its top-level menu");
}

let directClicks = 0;
const directAction = { mnemonic: "d", click() { directClicks += 1; } };
controller.activeRoot = null;
controller.topLevelActions = [directAction];
controller.menuMnemonic = (element) => element.mnemonic || "";
const altD = keyEvent("d", { altKey: true });
controller.onKeyDown(altD);
if (directClicks !== 1 || !altD.defaultPrevented) {
    throw new Error("Alt mnemonic did not activate a direct menu-bar command");
}
controller.topLevelActions = [];
controller.activeRoot = rootB;

let move = 0;
controller.moveSelection = (delta) => { move = delta; };
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
controller.activePopup = { matches() { return false; } };
controller.switchRoot = (delta) => { switched = delta; };
controller.onKeyDown(keyEvent("ArrowRight"));
if (switched !== 1) { throw new Error("ArrowRight did not switch the top-level menu"); }
controller.onKeyDown(keyEvent("ArrowLeft"));
if (switched !== -1) { throw new Error("ArrowLeft did not switch the top-level menu"); }

const submenuPopup = { matches(selector) { return selector === "[data-tv-submenu-popup]"; } };
controller.activePopup = submenuPopup;
let closedSubmenu = null;
controller.closeSubmenu = (popup) => { closedSubmenu = popup; };
controller.onKeyDown(keyEvent("Escape"));
if (closedSubmenu !== submenuPopup) {
    throw new Error("Escape did not return from a submenu");
}

let clicked = 0;
const mnemonicItem = {
    disabled: false,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return submenuPopup; },
    matches() { return false; },
    click() { clicked += 1; },
};
controller.activePopup = submenuPopup;
controller.menuItems = () => [mnemonicItem];
controller.menuMnemonic = () => "o";
controller.markSelected = () => {};
if (!controller.activateMnemonic("o") || clicked !== 1) {
    throw new Error("popup mnemonic did not activate its command");
}

const foreignPopup = {};
const enabled = {
    disabled: false,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return submenuPopup; },
};
const disabled = {
    disabled: true,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return submenuPopup; },
};
const nested = {
    disabled: false,
    getAttribute() { return null; },
    classList: { contains() { return false; } },
    closest() { return foreignPopup; },
};
submenuPopup.querySelectorAll = () => [enabled, disabled, nested];
controller.menuItems = TV.TVMenuController.prototype.menuItems;
const filtered = controller.menuItems(submenuPopup);
if (filtered.length !== 1 || filtered[0] !== enabled) {
    throw new Error("menu navigation included disabled or nested items");
}
"""
    result = subprocess.run(
        [NODE, "-e", script, str(CORE_PATHS[0])],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_shell_and_bundle_use_the_shared_menu_controller():
    shell_paths = (
        Path("www/assets/tv-shell.js"),
        Path("thelpviewer/converter/assets/tv-shell.js"),
    )
    bundle_paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/converter/assets/tv-bundle-app.js"),
    )
    css_paths = (
        Path("www/assets/turbovision.css"),
        Path("thelpviewer/converter/assets/turbovision.css"),
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
    assert "_menuGlobalsBound" not in bundle
    assert ".tv-menu-popup-item.is-menu-selected" in css
