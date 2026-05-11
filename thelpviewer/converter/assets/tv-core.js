// Turbo Vision core utilities and widgets for generated help pages.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};

const SCROLL_REPEAT_MS = 75;
const TRACK_CHAR = "\u2592";
const DISABLED_TRACK_CHAR = "\u2593";
const THUMB_CHAR = "\u25A0";
const CLOSE_PRESSED_CHAR = "\u2217";
const CP437_TABLE = ["\u0000", "\u263a", "\u263b", "\u2665", "\u2666", "\u2663", "\u2660", "\u2022", "\u25d8", "\t", "\n", "\u2642", "\u2640", "\r", "\u266b", "\u263c", "\u25ba", "\u25c4", "\u2195", "\u203c", "\u00b6", "\u00a7", "\u25ac", "\u21a8", "\u2191", "\u2193", "\u2192", "\u2190", "\u221f", "\u2194", "\u25b2", "\u25bc", " ", "!", "\"", "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?", "@", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "\\", "]", "^", "_", "`", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "{", "|", "}", "~", "\u007f", "\u00c7", "\u00fc", "\u00e9", "\u00e2", "\u00e4", "\u00e0", "\u00e5", "\u00e7", "\u00ea", "\u00eb", "\u00e8", "\u00ef", "\u00ee", "\u00ec", "\u00c4", "\u00c5", "\u00c9", "\u00e6", "\u00c6", "\u00f4", "\u00f6", "\u00f2", "\u00fb", "\u00f9", "\u00ff", "\u00d6", "\u00dc", "\u00a2", "\u00a3", "\u00a5", "\u20a7", "\u0192", "\u00e1", "\u00ed", "\u00f3", "\u00fa", "\u00f1", "\u00d1", "\u00aa", "\u00ba", "\u00bf", "\u2310", "\u00ac", "\u00bd", "\u00bc", "\u00a1", "\u00ab", "\u00bb", "\u2591", "\u2592", "\u2593", "\u2502", "\u2524", "\u2561", "\u2562", "\u2556", "\u2555", "\u2563", "\u2551", "\u2557", "\u255d", "\u255c", "\u255b", "\u2510", "\u2514", "\u2534", "\u252c", "\u251c", "\u2500", "\u253c", "\u255e", "\u255f", "\u255a", "\u2554", "\u2569", "\u2566", "\u2560", "\u2550", "\u256c", "\u2567", "\u2568", "\u2564", "\u2565", "\u2559", "\u2558", "\u2552", "\u2553", "\u256b", "\u256a", "\u2518", "\u250c", "\u2588", "\u2584", "\u258c", "\u2590", "\u2580", "\u03b1", "\u00df", "\u0393", "\u03c0", "\u03a3", "\u03c3", "\u00b5", "\u03c4", "\u03a6", "\u0398", "\u03a9", "\u03b4", "\u221e", "\u03c6", "\u03b5", "\u2229", "\u2261", "\u00b1", "\u2265", "\u2264", "\u2320", "\u2321", "\u00f7", "\u2248", "\u00b0", "\u2219", "\u00b7", "\u221a", "\u207f", "\u00b2", "\u25a0", "\u00a0"];
const MONTH_NAMES = [
    "",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const PUZZLE_START = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", " "];
const PUZZLE_HIGHLIGHT_MAP = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1];
const DOS_COLORS = [
    "#000000", "#0000aa", "#00aa00", "#00aaaa",
    "#aa0000", "#aa00aa", "#aa5500", "#aaaaaa",
    "#555555", "#5555ff", "#55ff55", "#55ffff",
    "#ff5555", "#ff55ff", "#ffff55", "#ffffff",
];
const THEME_PRESETS = {
    default: {
        label: "Default",
        vars: {},
    },
    light: {
        label: "Light",
        vars: {},
    },
    dark: {
        label: "Dark",
        vars: {
            "--tv-desktop": "#000000",
            "--tv-desktop-dot": "#0000aa",
            "--tv-appbar-bg": "#0000aa",
            "--tv-appbar-text": "#aaaaaa",
            "--tv-appbar-hotkey": "#ffff55",
            "--tv-appbar-active-bg": "#aaaaaa",
            "--tv-appbar-active-text": "#000000",
            "--tv-appbar-active-hotkey": "#aa0000",
            "--tv-help-pane": "#000000",
            "--tv-window": "#000000",
            "--tv-search-results-pane": "#000000",
            "--tv-puzzle-pane": "#000000",
            "--tv-calendar-pane": "#000000",
            "--tv-title": "#0000aa",
            "--tv-title-text": "#ffffff",
            "--tv-icon": "#55ffff",
            "--tv-text": "#aaaaaa",
            "--tv-muted": "#55ffff",
            "--tv-link": "#55ffff",
            "--tv-hover-bg": "#00aaaa",
            "--tv-hover-fg": "#000000",
            "--tv-page-area": "#000000",
            "--tv-arrow-bg": "#0000aa",
            "--tv-arrow-fg": "#aaaaaa",
            "--tv-scroll-glyph": "#5555ff",
            "--tv-thumb-fg": "#ffffff",
            "--tv-frame-line": "#aaaaaa",
            "--tv-frame-passive": "#555555",
            "--tv-title-passive": "#000000",
            "--tv-title-text-passive": "#aaaaaa",
            "--tv-icon-passive": "#aaaaaa",
            "--tv-dialog-bg": "#555555",
            "--tv-dialog-fg": "#ffffff",
            "--tv-dialog-frame": "#ffffff",
            "--tv-dialog-title": "#ffff55",
            "--tv-dialog-frame-passive": "#aaaaaa",
            "--tv-dialog-title-passive": "#555555",
            "--tv-dialog-title-text-passive": "#ffffff",
            "--tv-dialog-icon-passive": "#ffffff",
            "--tv-dialog-input-bg": "#000000",
            "--tv-dialog-input-fg": "#55ffff",
            "--tv-dialog-button-face": "#00aa00",
            "--tv-dialog-button-fg": "#000000",
            "--tv-dialog-button-shadow-bg": "#555555",
            "--tv-dialog-button-shadow-fg": "#000000",
            "--tv-dialog-button-edge-bg": "#555555",
            "--tv-dialog-button-edge-fg": "#000000",
            "--tv-ascii-pane": "#555555",
            "--tv-ascii-text": "#ffffff",
            "--tv-calc-display-bg": "#000000",
            "--tv-calc-display-fg": "#55ffff",
            "--tv-code-bg": "#0000aa",
            "--tv-code-text": "#aaaaaa",
            "--tv-code-keyword": "#ffff55",
            "--tv-code-string": "#55ffff",
            "--tv-code-comment": "#55ff55",
            "--tv-code-number": "#ffffff",
        },
    },
    auto: {
        label: "Auto",
        vars: {},
    },
    green: {
        label: "Green",
        vars: {
            "--tv-desktop": "#aaaaaa",
            "--tv-desktop-dot": "#0000aa",
            "--tv-appbar-bg": "#aaaaaa",
            "--tv-appbar-active-bg": "#00aa00",
            "--tv-help-pane": "#00aa00",
            "--tv-window": "#00aa00",
            "--tv-title": "#00aa00",
            "--tv-title-text": "#ffffff",
            "--tv-icon": "#55ff55",
            "--tv-link": "#ffff55",
            "--tv-hover-bg": "#0000aa",
            "--tv-hover-fg": "#ffff55",
            "--tv-page-area": "#0000aa",
            "--tv-arrow-bg": "#0000aa",
            "--tv-arrow-fg": "#00aa00",
            "--tv-scroll-glyph": "#00aa00",
            "--tv-thumb-fg": "#00ff00",
            "--tv-search-results-pane": "#00aaaa",
            "--tv-puzzle-pane": "#00aaaa",
            "--tv-puzzle-normal": "#000000",
            "--tv-puzzle-highlight": "#ffffff",
            "--tv-calendar-pane": "#00aaaa",
            "--tv-calendar-normal": "#000000",
            "--tv-calendar-current": "#ffffff",
            "--tv-ascii-pane": "#aaaaaa",
            "--tv-ascii-text": "#000000",
            "--tv-calc-display-bg": "#0000aa",
            "--tv-calc-display-fg": "#aaaaaa",
        },
    },
    amber: {
        label: "Amber",
        vars: {
            "--tv-desktop": "#000000",
            "--tv-desktop-dot": "#aa5500",
            "--tv-appbar-bg": "#aa5500",
            "--tv-appbar-text": "#000000",
            "--tv-appbar-hotkey": "#ffff55",
            "--tv-appbar-active-bg": "#ffaa00",
            "--tv-appbar-active-text": "#000000",
            "--tv-appbar-active-hotkey": "#aa0000",
            "--tv-help-pane": "#aa5500",
            "--tv-window": "#aa5500",
            "--tv-title": "#aa5500",
            "--tv-title-text": "#000000",
            "--tv-icon": "#ffff55",
            "--tv-text": "#000000",
            "--tv-link": "#ffff55",
            "--tv-hover-bg": "#552200",
            "--tv-hover-fg": "#ffff55",
            "--tv-page-area": "#552200",
            "--tv-arrow-bg": "#552200",
            "--tv-arrow-fg": "#ffaa00",
            "--tv-scroll-glyph": "#ffaa00",
            "--tv-thumb-fg": "#ffff55",
            "--tv-frame-line": "#ffff55",
            "--tv-search-results-pane": "#aa5500",
            "--tv-puzzle-pane": "#aa5500",
            "--tv-puzzle-normal": "#000000",
            "--tv-puzzle-highlight": "#ffff55",
            "--tv-calendar-pane": "#aa5500",
            "--tv-calendar-normal": "#000000",
            "--tv-calendar-current": "#ffff55",
            "--tv-ascii-pane": "#552200",
            "--tv-ascii-text": "#ffff55",
            "--tv-calc-display-bg": "#552200",
            "--tv-calc-display-fg": "#ffff55",
        },
    },
    gray: {
        label: "Gray",
        vars: {
            "--tv-desktop": "#aaaaaa",
            "--tv-desktop-dot": "#555555",
            "--tv-appbar-bg": "#aaaaaa",
            "--tv-appbar-text": "#000000",
            "--tv-appbar-hotkey": "#555555",
            "--tv-appbar-active-bg": "#ffffff",
            "--tv-appbar-active-text": "#000000",
            "--tv-appbar-active-hotkey": "#555555",
            "--tv-help-pane": "#c0c0c0",
            "--tv-window": "#c0c0c0",
            "--tv-title": "#aaaaaa",
            "--tv-title-text": "#000000",
            "--tv-icon": "#000000",
            "--tv-text": "#000000",
            "--tv-link": "#000000",
            "--tv-hover-bg": "#555555",
            "--tv-hover-fg": "#ffffff",
            "--tv-page-area": "#555555",
            "--tv-arrow-bg": "#555555",
            "--tv-arrow-fg": "#ffffff",
            "--tv-scroll-glyph": "#c0c0c0",
            "--tv-thumb-fg": "#ffffff",
            "--tv-frame-line": "#ffffff",
            "--tv-search-results-pane": "#c0c0c0",
            "--tv-puzzle-pane": "#c0c0c0",
            "--tv-puzzle-normal": "#000000",
            "--tv-puzzle-highlight": "#ffffff",
            "--tv-calendar-pane": "#c0c0c0",
            "--tv-calendar-normal": "#000000",
            "--tv-calendar-current": "#ffffff",
            "--tv-ascii-pane": "#c0c0c0",
            "--tv-ascii-text": "#000000",
            "--tv-calc-display-bg": "#555555",
            "--tv-calc-display-fg": "#ffffff",
        },
    },
};
const THEME_VARIABLE_KEYS = [...new Set(
    Object.values(THEME_PRESETS).flatMap((preset) => Object.keys(preset.vars))
)];
const DEFAULT_UI_CONFIG = Object.freeze({
    menu: {
        popup: [
            { type: "dialog", dialog: "about", label: "~A~bout" },
            { type: "dialog", dialog: "puzzle", label: "~P~uzzle" },
            { type: "dialog", dialog: "calendar", label: "Ca~l~endar" },
            { type: "dialog", dialog: "ascii", label: "Ascii ~T~able" },
            { type: "dialog", dialog: "calc", label: "~C~alculator" },
            { type: "dialog", dialog: "colors", label: "C~o~lors" },
            { type: "separator" },
            { type: "submenu", label: "~S~creen saver", items: [
                { type: "saver", mode: "stars", label: "~S~tars" },
                { type: "saver", mode: "bounce", label: "~B~ounce" },
                { type: "saver", mode: "clock", label: "Cloc~k~" },
                { type: "saver", mode: "matrix", label: "~M~atrix" },
            ] },
            { type: "separator" },
            { type: "theme", theme: "light", label: "~L~ight Theme" },
            { type: "theme", theme: "dark", label: "~D~ark Theme" },
            { type: "theme", theme: "auto", label: "A~u~to Theme" },
        ],
        items: [
            { type: "menu-root", label: "~X~" },
            { type: "help-link", label: "~H~elp" },
            { type: "index-link", label: "~I~ndex" },
            { type: "topic-link", label: "~T~opic {topic}", whenTopic: true },
        ],
    },
    status: [
        { type: "back", label: "~B~ack" },
        { type: "index-link", label: "~F1~ Index" },
        { type: "dialog", dialog: "search", label: "~F3~ Search" },
        { type: "hint" },
        { type: "link", href: "https://github.com/mariolacko/THelpViewer", label: "GitHub" },
    ],
});
const COLOR_GROUPS = [
    {
        name: "Desktop",
        items: ["Color"],
    },
    {
        name: "Menus",
        items: [
            "Normal",
            "Disabled",
            "Shortcut",
            "Selected",
            "Selected disabled",
            "Shortcut selected",
        ],
    },
    {
        name: "Dialogs/Calc",
        items: [
            "Frame/background",
            "Frame icons",
            "Scroll bar page",
            "Scroll bar icons",
            "Static text",
            "Label normal",
            "Label selected",
            "Label shortcut",
            "Button normal",
            "Button default",
            "Button selected",
            "Button disabled",
            "Button shortcut",
            "Button shadow",
            "Cluster normal",
            "Cluster selected",
            "Cluster shortcut",
            "Input normal",
            "Input selected",
            "Input arrow",
            "History button",
            "History sides",
            "History bar page",
            "History bar icons",
            "List normal",
            "List focused",
            "List selected",
            "List divider",
            "Information pane",
        ],
    },
    {
        name: "Viewer",
        items: [
            "Frame passive",
            "Frame active",
            "Frame icons",
            "Scroll bar page",
            "Scroll bar icons",
            "Text",
        ],
    },
    {
        name: "Puzzle",
        items: [
            "Frame passive",
            "Frame active",
            "Frame icons",
            "Scroll bar page",
            "Scroll bar icons",
            "Normal text",
            "Highlighted text",
        ],
    },
    {
        name: "Calendar",
        items: [
            "Frame passive",
            "Frame active",
            "Frame icons",
            "Scroll bar page",
            "Scroll bar icons",
            "Normal text",
            "Current day",
        ],
    },
    {
        name: "Ascii table",
        items: [
            "Frame passive",
            "Frame active",
            "Frame icons",
            "Scroll bar page",
            "Scroll bar icons",
            "Text",
        ],
    },
];
const COLOR_ITEM_DEFAULTS = {
    "Desktop/Color": { attr: 0x71, bg: ["--tv-desktop"], fg: ["--tv-desktop-dot"] },
    "Menus/Normal": { attr: 0x70, bg: ["--tv-appbar-bg"], fg: ["--tv-appbar-text"] },
    "Menus/Shortcut": { attr: 0x74, fg: ["--tv-appbar-hotkey"] },
    "Menus/Selected": { attr: 0x20, bg: ["--tv-appbar-active-bg"], fg: ["--tv-appbar-active-text"] },
    "Menus/Shortcut selected": { attr: 0x24, fg: ["--tv-appbar-active-hotkey"] },
    "Dialogs/Calc/Frame/background": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame", "--tv-dialog-title"] },
    "Dialogs/Calc/Frame icons": { attr: 0x72, fg: ["--tv-dialog-icon"] },
    "Dialogs/Calc/Scroll bar page": { attr: 0x11, bg: ["--tv-page-area"], fg: ["--tv-scroll-glyph"] },
    "Dialogs/Calc/Scroll bar icons": { attr: 0x13, bg: ["--tv-arrow-bg"], fg: ["--tv-arrow-fg", "--tv-thumb-fg"] },
    "Dialogs/Calc/Static text": { attr: 0x70, fg: ["--tv-dialog-fg", "--tv-dialog-title"] },
    "Dialogs/Calc/Label normal": { attr: 0x70, fg: ["--tv-dialog-fg", "--tv-dialog-title"] },
    "Dialogs/Calc/Label selected": { attr: 0x1E, fg: ["--tv-dialog-fg", "--tv-dialog-title"] },
    "Dialogs/Calc/Label shortcut": { attr: 0x74, fg: ["--tv-appbar-hotkey"] },
    "Dialogs/Calc/Button normal": { attr: 0x20, bg: ["--tv-dialog-button-face"], fg: ["--tv-dialog-button-fg"] },
    "Dialogs/Calc/Button default": { attr: 0x20, bg: ["--tv-dialog-button-face"], fg: ["--tv-dialog-button-fg"] },
    "Dialogs/Calc/Button selected": { attr: 0x1E, bg: ["--tv-dialog-button-face"], fg: ["--tv-dialog-button-fg"] },
    "Dialogs/Calc/Button shortcut": { attr: 0x24, fg: ["--tv-appbar-hotkey"] },
    "Dialogs/Calc/Button shadow": { attr: 0x70, bg: ["--tv-dialog-button-shadow-bg", "--tv-dialog-button-edge-bg"], fg: ["--tv-dialog-button-shadow-fg", "--tv-dialog-button-edge-fg"] },
    "Dialogs/Calc/Input normal": { attr: 0x1E, bg: ["--tv-dialog-input-bg"], fg: ["--tv-dialog-input-fg"] },
    "Dialogs/Calc/Input selected": { attr: 0x1E, bg: ["--tv-dialog-input-bg"], fg: ["--tv-dialog-input-fg"] },
    "Dialogs/Calc/Input arrow": { attr: 0x1F, fg: ["--tv-dialog-input-fg"] },
    "Dialogs/Calc/Information pane": { attr: 0x30, bg: ["--tv-search-results-pane"], fg: ["--tv-dialog-fg"] },
    "Viewer/Frame passive": { attr: 0x37, bg: ["--tv-title-passive"], fg: ["--tv-frame-passive"] },
    "Viewer/Frame active": { attr: 0x3F, bg: ["--tv-title"], fg: ["--tv-frame-line", "--tv-title-text"] },
    "Viewer/Frame icons": { attr: 0x3A, fg: ["--tv-icon", "--tv-icon-passive"] },
    "Viewer/Text": { attr: 0x20, bg: ["--tv-window"], fg: ["--tv-text"] },
    "Puzzle/Frame passive": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame-passive"] },
    "Puzzle/Frame active": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame", "--tv-dialog-title"] },
    "Puzzle/Frame icons": { attr: 0x72, fg: ["--tv-dialog-icon", "--tv-dialog-icon-passive"] },
    "Puzzle/Normal text": { attr: 0x30, bg: ["--tv-puzzle-pane"], fg: ["--tv-puzzle-normal"] },
    "Puzzle/Highlighted text": { attr: 0x3F, fg: ["--tv-puzzle-highlight"] },
    "Calendar/Frame passive": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame-passive"] },
    "Calendar/Frame active": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame", "--tv-dialog-title"] },
    "Calendar/Frame icons": { attr: 0x72, fg: ["--tv-dialog-icon", "--tv-dialog-icon-passive"] },
    "Calendar/Normal text": { attr: 0x30, bg: ["--tv-calendar-pane"], fg: ["--tv-calendar-normal"] },
    "Calendar/Current day": { attr: 0x3F, fg: ["--tv-calendar-current"] },
    "Ascii table/Frame passive": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame-passive"] },
    "Ascii table/Frame active": { attr: 0x70, bg: ["--tv-dialog-bg"], fg: ["--tv-dialog-frame", "--tv-dialog-title"] },
    "Ascii table/Frame icons": { attr: 0x72, fg: ["--tv-dialog-icon", "--tv-dialog-icon-passive"] },
    "Ascii table/Text": { attr: 0x70, bg: ["--tv-ascii-pane"], fg: ["--tv-ascii-text"] },
};
const COLOR_PALETTE_VARIABLE_KEYS = [...new Set(
    Object.values(COLOR_ITEM_DEFAULTS).flatMap((entry) => [...(entry.bg || []), ...(entry.fg || [])])
)];
let activeThemePreset = "default";
let activeColorPalette = null;
let measuredCell = null;
const HOST_WINDOW_TOKEN = "__host__";

function colorItemKey(groupName, itemName) {
    return `${groupName}/${itemName}`;
}

function cloneColorPalette(palette) {
    return palette.map((group) => ({
        name: group.name,
        index: group.index,
        items: group.items.map((item) => ({
            name: item.name,
            key: item.key,
            attr: item.attr,
            bg: item.bg ? [...item.bg] : [],
            fg: item.fg ? [...item.fg] : [],
        })),
    }));
}

function buildDefaultColorPalette() {
    return COLOR_GROUPS.map((group) => ({
        name: group.name,
        index: 0,
        items: group.items.map((name) => {
            const defaults = COLOR_ITEM_DEFAULTS[colorItemKey(group.name, name)] || {};
            return {
                name,
                key: colorItemKey(group.name, name),
                attr: defaults.attr ?? 0x70,
                bg: [...(defaults.bg || [])],
                fg: [...(defaults.fg || [])],
            };
        }),
    }));
}

function serializeColorPalette(palette) {
    return palette.map((group) => ({
        index: group.index,
        attrs: group.items.map((item) => item.attr),
    }));
}

function restoreColorPalette(serialized) {
    const palette = buildDefaultColorPalette();
    if (!Array.isArray(serialized)) {
        return palette;
    }
    serialized.forEach((savedGroup, groupIndex) => {
        const targetGroup = palette[groupIndex];
        if (!targetGroup || !savedGroup) {
            return;
        }
        const nextIndex = Number.parseInt(savedGroup.index, 10);
        if (Number.isInteger(nextIndex) && nextIndex >= 0 && nextIndex < targetGroup.items.length) {
            targetGroup.index = nextIndex;
        }
        if (Array.isArray(savedGroup.attrs)) {
            savedGroup.attrs.forEach((attr, itemIndex) => {
                if (targetGroup.items[itemIndex] && Number.isInteger(attr) && attr >= 0 && attr <= 0xFF) {
                    targetGroup.items[itemIndex].attr = attr;
                }
            });
        }
    });
    return palette;
}

function readStoredColorPalette() {
    try {
        const raw = window.localStorage.getItem("thelp:color-palette");
        return raw ? restoreColorPalette(JSON.parse(raw)) : null;
    } catch {
        return null;
    }
}

function persistColorPalette(palette) {
    try {
        window.localStorage.setItem("thelp:color-palette", JSON.stringify(serializeColorPalette(palette)));
    } catch {
        // Ignore storage failures under restrictive file:// environments.
    }
}

function clearStoredColorPalette() {
    try {
        window.localStorage.removeItem("thelp:color-palette");
    } catch {
        // Ignore storage failures under restrictive file:// environments.
    }
}

function dosColor(attr, shift) {
    return DOS_COLORS[(attr >> shift) & 0x0F] || DOS_COLORS[0];
}

function parseCssColor(value) {
    const text = String(value || "").trim();
    if (!text) {
        return null;
    }
    const hex = text.match(/^#([0-9a-f]{6})$/i);
    if (hex) {
        return {
            r: Number.parseInt(hex[1].slice(0, 2), 16),
            g: Number.parseInt(hex[1].slice(2, 4), 16),
            b: Number.parseInt(hex[1].slice(4, 6), 16),
        };
    }
    const rgb = text.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (rgb) {
        return {
            r: Number.parseInt(rgb[1], 10),
            g: Number.parseInt(rgb[2], 10),
            b: Number.parseInt(rgb[3], 10),
        };
    }
    return null;
}

function nearestDosColorIndex(color) {
    if (!color) {
        return 0;
    }
    let bestIndex = 0;
    let bestDistance = Number.POSITIVE_INFINITY;
    DOS_COLORS.forEach((hex, index) => {
        const ref = parseCssColor(hex);
        const distance =
            (color.r - ref.r) ** 2 +
            (color.g - ref.g) ** 2 +
            (color.b - ref.b) ** 2;
        if (distance < bestDistance) {
            bestDistance = distance;
            bestIndex = index;
        }
    });
    return bestIndex;
}

function buildPaletteFromCurrentStyle() {
    const palette = buildDefaultColorPalette();
    const style = getComputedStyle(document.documentElement);
    palette.forEach((group) => {
        group.items.forEach((item) => {
            let fg = item.attr & 0x0F;
            let bg = (item.attr >> 4) & 0x0F;
            if (item.fg.length) {
                fg = nearestDosColorIndex(parseCssColor(style.getPropertyValue(item.fg[0])));
            }
            if (item.bg.length) {
                bg = nearestDosColorIndex(parseCssColor(style.getPropertyValue(item.bg[0])));
            }
            item.attr = ((bg & 0x0F) << 4) | (fg & 0x0F);
        });
    });
    return palette;
}

function applyColorPalette(palette, persist = false) {
    const root = document.documentElement;
    COLOR_PALETTE_VARIABLE_KEYS.forEach((key) => root.style.removeProperty(key));
    palette.forEach((group) => {
        group.items.forEach((item) => {
            const fg = dosColor(item.attr, 0);
            const bg = dosColor(item.attr, 4);
            item.bg.forEach((key) => root.style.setProperty(key, bg));
            item.fg.forEach((key) => root.style.setProperty(key, fg));
        });
    });
    activeColorPalette = cloneColorPalette(palette);
    if (persist) {
        persistColorPalette(activeColorPalette);
    }
}

function readStoredThemePreset() {
    try {
        const value = window.localStorage.getItem("thelp:theme-preset");
        return value && THEME_PRESETS[value] ? value : "default";
    } catch {
        return "default";
    }
}

function persistThemePreset(name) {
    try {
        window.localStorage.setItem("thelp:theme-preset", name);
    } catch {
        // Ignore storage failures under restrictive file:// environments.
    }
}

function applyThemePreset(name, persist = false) {
    const requestedName = THEME_PRESETS[name] ? name : "default";
    const presetName = requestedName === "auto"
        ? ((window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light")
        : requestedName;
    const preset = THEME_PRESETS[presetName];
    const root = document.documentElement;
    THEME_VARIABLE_KEYS.forEach((key) => root.style.removeProperty(key));
    Object.entries(preset.vars).forEach(([key, value]) => root.style.setProperty(key, value));
    activeThemePreset = requestedName;
    if (persist) {
        persistThemePreset(requestedName);
    }
}

function applyThemeAndSyncPalette(name, persist = false) {
    const root = document.documentElement;
    COLOR_PALETTE_VARIABLE_KEYS.forEach((key) => root.style.removeProperty(key));
    applyThemePreset(name, persist);
    const palette = buildPaletteFromCurrentStyle();
    applyColorPalette(palette, persist);
    return palette;
}

function isLeapYear(year) {
    return year % 4 === 0;
}

function dayOfWeek(day, month, year) {
    let calcMonth = month;
    let calcYear = year;
    if (calcMonth < 3) {
        calcMonth += 10;
        calcYear -= 1;
    } else {
        calcMonth -= 2;
    }
    const century = Math.floor(calcYear / 100);
    const yr = calcYear % 100;
    let dw = (((26 * calcMonth - 2) / 10) | 0) + day + yr + ((yr / 4) | 0) + ((century / 4) | 0) - (2 * century);
    dw %= 7;
    if (dw < 0) {
        dw += 7;
    }
    return dw;
}

function measureCells() {
    if (measuredCell) {
        return measuredCell;
    }
    const probe = document.createElement("span");
    probe.textContent = "0";
    probe.style.position = "absolute";
    probe.style.visibility = "hidden";
    probe.style.whiteSpace = "pre";
    document.body.appendChild(probe);
    const rect = probe.getBoundingClientRect();
    measuredCell = {
        width: rect.width || 8,
        height: rect.height || 16,
    };
    probe.remove();
    return measuredCell;
}

function fillBorders(root) {
    const container = (root instanceof HTMLElement) ? root : document;
    measuredCell = null;
    const cell = measureCells();

    container.querySelectorAll("[data-tv-border-fill]").forEach((element) => {
        const char = element.getAttribute("data-tv-border-fill") || "\u2500";
        const count = Math.max(1, Math.ceil(element.clientWidth / cell.width) + 2);
        element.textContent = char.repeat(count);
    });

    container.querySelectorAll("[data-tv-border-side]").forEach((element) => {
        const char = element.getAttribute("data-tv-border-side") || "\u2502";
        const count = Math.max(1, Math.ceil(element.clientHeight / cell.height));
        element.textContent = `${Array.from({ length: count }, () => char).join("\n")}`;
    });
}

function setBorderFill(element, char) {
    if (element) {
        element.setAttribute("data-tv-border-fill", char);
    }
}

function setBorderSide(element, char) {
    if (element) {
        element.setAttribute("data-tv-border-side", char);
    }
}

function updateWindowFrameState(windowElement, active, { dialog = false } = {}) {
    if (!windowElement) {
        return;
    }
    const singleFrame = !dialog && windowElement.classList.contains("is-resizing");
    const topBar = dialog
        ? windowElement.querySelector(".tv-dialog-titlebar")
        : windowElement.querySelector(".tv-border-top");
    const bottomBar = dialog
        ? windowElement.querySelector(".tv-dialog-footer")
        : windowElement.querySelector(".tv-bottom-bar");
    const topCorners = topBar ? Array.from(topBar.querySelectorAll(".tv-border-corner")) : [];
    const bottomCorners = bottomBar ? Array.from(bottomBar.querySelectorAll(".tv-border-corner")) : [];
    const topFills = topBar ? Array.from(topBar.querySelectorAll(".tv-border-fill")) : [];
    const bottomFills = bottomBar ? Array.from(bottomBar.querySelectorAll(".tv-border-fill")) : [];
    const sides = dialog
        ? Array.from(windowElement.querySelectorAll("[data-tv-border-side]"))
        : Array.from(windowElement.querySelectorAll(".tv-border-side-left"));
    const closeButton = windowElement.querySelector("[data-tv-close-button]");
    const closeGlyph = windowElement.querySelector("[data-tv-close-glyph]");
    const resizeHandle = !dialog ? windowElement.querySelector("[data-tv-resize-handle]") : null;

    const horiz = singleFrame ? "─" : (active ? "═" : "─");
    const vert = singleFrame ? "│" : (active ? "║" : "│");
    const tl = singleFrame ? "┌" : (active ? "╔" : "┌");
    const tr = singleFrame ? "┐" : (active ? "╗" : "┐");
    const bl = singleFrame ? "└" : (active ? "╚" : "└");
    const br = singleFrame ? "┘" : (active ? "╝" : "┘");

    if (topCorners[0]) {
        topCorners[0].textContent = tl;
    }
    if (topCorners[topCorners.length - 1]) {
        topCorners[topCorners.length - 1].textContent = tr;
    }
    topFills.forEach((element) => setBorderFill(element, horiz));
    sides.forEach((element) => setBorderSide(element, vert));

    if (dialog) {
        if (bottomCorners[0]) {
            bottomCorners[0].textContent = bl;
        }
        if (bottomCorners[bottomCorners.length - 1]) {
            bottomCorners[bottomCorners.length - 1].textContent = br;
        }
        bottomFills.forEach((element) => setBorderFill(element, horiz));

        // Update internal separator T-connectors (e.g. ASCII table ╟/╢)
        const tMap = active && !singleFrame
            ? { "├": "╟", "┤": "╢", "┬": "╤", "┴": "╧" }
            : { "╟": "├", "╢": "┤", "╤": "┬", "╧": "┴" };
        const bodyCorners = Array.from(windowElement.querySelectorAll(".tv-border-corner"))
            .filter((el) => !(topBar && topBar.contains(el)) && !(bottomBar && bottomBar.contains(el)));
        for (const el of bodyCorners) {
            const mapped = tMap[el.textContent];
            if (mapped) { el.textContent = mapped; }
        }
    } else {
        const leftCorner = windowElement.querySelector(".tv-scroll-corner-left");
        if (leftCorner) {
            leftCorner.textContent = bl;
        }
        bottomFills.forEach((element) => setBorderFill(element, horiz));
        if (resizeHandle) {
            resizeHandle.textContent = active ? "─┘" : "─┘";
        }
    }

    if (closeGlyph) {
        applyCloseGlyphState(closeButton, closeButton && closeButton.dataset.tvClosePressed === "1");
    }

    fillBorders();
}

function fillDesktopPatterns() {
    measuredCell = null;
    const cell = measureCells();

    document.querySelectorAll("[data-tv-desktop-pattern]").forEach((element) => {
        const char = element.getAttribute("data-tv-desktop-pattern") || "\u2591";
        const cols = Math.max(1, Math.ceil(element.clientWidth / cell.width) + 1);
        const rows = Math.max(1, Math.ceil(element.clientHeight / cell.height) + 1);
        const line = char.repeat(cols);
        element.textContent = Array.from({ length: rows }, () => line).join("\n");
    });
}

function updateClocks() {
    const now = new Date();
    const text = [now.getHours(), now.getMinutes(), now.getSeconds()]
        .map((value) => String(value).padStart(2, "0"))
        .join(":");
    document.querySelectorAll("[data-tv-clock]").forEach((element) => {
        element.textContent = text;
    });
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function renderHotkeyMarkup(text) {
    const value = String(text ?? "");
    const parts = [];
    let buffer = "";
    let inHotkey = false;

    for (const char of value) {
        if (char === "~") {
            if (buffer) {
                const segment = escapeHtml(buffer);
                parts.push(inHotkey ? `<span class="tv-hotkey">${segment}</span>` : segment);
                buffer = "";
            }
            inHotkey = !inHotkey;
            continue;
        }
        buffer += char;
    }

    if (buffer) {
        const segment = escapeHtml(buffer);
        parts.push(inHotkey ? `<span class="tv-hotkey">${segment}</span>` : segment);
    }

    return parts.join("");
}

function displayCp437Char(code) {
    if (code === 0) {
        return " ";
    }
    if (code === 9) {
        return "\u25CB";
    }
    if (code === 10) {
        return "\u25D9";
    }
    if (code === 13) {
        return "\u266A";
    }
    if (code === 127) {
        return "\u2302";
    }
    return CP437_TABLE[code] ?? " ";
}

function applyCloseGlyphState(button, active) {
    const glyph = button && button.querySelector("[data-tv-close-glyph]");
    if (!glyph) {
        return;
    }
    glyph.textContent = active ? CLOSE_PRESSED_CHAR : "\u25A0";
}

function bindCloseButtons(scope = document) {
    scope.querySelectorAll("[data-tv-close-button]").forEach((button) => {
        if (button.dataset.tvCloseBound === "1") {
            return;
        }
        button.dataset.tvCloseBound = "1";
        const setPressed = (pressed) => {
            if (pressed) {
                button.dataset.tvClosePressed = "1";
            } else {
                delete button.dataset.tvClosePressed;
            }
            applyCloseGlyphState(button, pressed);
        };
        button.addEventListener("mousedown", () => setPressed(true));
        button.addEventListener("mouseup", () => setPressed(false));
        button.addEventListener("mouseleave", () => setPressed(false));
        button.addEventListener("blur", () => setPressed(false));
    });
}

function cloneUiConfig(config) {
    function cloneEntry(entry) {
        const clone = { ...entry };
        if (Array.isArray(clone.items)) {
            clone.items = clone.items.map((sub) => ({ ...sub }));
        }
        return clone;
    }
    return {
        menu: {
            popup: Array.isArray(config?.menu?.popup) ? config.menu.popup.map(cloneEntry) : [],
            items: Array.isArray(config?.menu?.items) ? config.menu.items.map(cloneEntry) : [],
        },
        status: Array.isArray(config?.status) ? config.status.map(cloneEntry) : [],
    };
}

function resolveUiConfig() {
    const base = cloneUiConfig(DEFAULT_UI_CONFIG);
    const override = window.TV_UI_CONFIG;
    if (!override || typeof override !== "object") {
        return base;
    }
    if (Array.isArray(override.menu?.popup)) {
        base.menu.popup = override.menu.popup.map((entry) => ({ ...entry }));
    }
    if (Array.isArray(override.menu?.items)) {
        base.menu.items = override.menu.items.map((entry) => ({ ...entry }));
    }
    if (Array.isArray(override.status)) {
        base.status = override.status.map((entry) => ({ ...entry }));
    }
    return base;
}

class TVAppContext {
    constructor(body = document.body) {
        this.body = body;
        this.helpHref = body.dataset.tvHelpHref || "index.html";
        this.indexHref = body.dataset.tvIndexHref || "index.html";
        this.pageKind = body.dataset.tvPageKind || "index";
        this.statusHint = body.dataset.tvStatusHint || "";
        this.topicContext = body.dataset.tvTopicContext || "";
        this.topicHref = body.dataset.tvTopicHref || "";
        this.uiConfig = resolveUiConfig();
    }
}

function attrsToString(attrs = {}) {
    return Object.entries(attrs)
        .filter(([, value]) => value !== false && value !== null && value !== undefined)
        .map(([key, value]) => {
            if (value === true) {
                return key;
            }
            return `${key}="${escapeHtml(value)}"`;
        })
        .join(" ");
}

class TVWidget {
    constructor(root = null) {
        this.root = root;
    }

    /** Build inline CSS for character-cell bounds (x, y, w, h). */
    static boundsStyle(x, y, w, h) {
        const parts = [];
        if (x !== undefined || y !== undefined) { parts.push("position:absolute"); }
        if (x !== undefined) { parts.push(`left:${x}ch`); }
        if (y !== undefined) { parts.push(`top:${y}em`); }
        if (w !== undefined) { parts.push(`width:${w}ch`); }
        if (h !== undefined) { parts.push(`height:${h}em`); }
        return parts.join(";");
    }

    static fromHTML(markup) {
        const template = document.createElement("template");
        template.innerHTML = markup.trim();
        return template.content.firstElementChild;
    }

    mount(parent) {
        if (this.root && parent) {
            parent.appendChild(this.root);
        }
        return this.root;
    }

    query(selector) {
        return this.root ? this.root.querySelector(selector) : null;
    }

    queryAll(selector) {
        return this.root ? Array.from(this.root.querySelectorAll(selector)) : [];
    }

    setHTML(markup) {
        if (this.root) {
            this.root.innerHTML = markup;
        }
        return this.root;
    }
}

class TVStaticText extends TVWidget {
    constructor({
        tag = "div",
        name = "",
        text = "",
        html = "",
        className = "",
        style = "",
        align = "",
        title = false,
        attrs = {},
        x, y, w, h,
    } = {}) {
        super();
        this.tag = tag;
        this.name = name;
        this.text = text;
        this.html = html;
        this.className = className;
        this.style = style;
        this.align = align;
        this.title = title;
        this.attrs = attrs;
        this.x = x; this.y = y; this.w = w; this.h = h;
    }

    renderMarkup() {
        const cls = ["tv-static-text", this.title ? "tv-title" : "", this.className].filter(Boolean).join(" ");
        const classAttr = ` class="${escapeHtml(cls)}"`;
        const bounds = TVWidget.boundsStyle(this.x, this.y, this.w, this.h);
        const alignStyle = this.align ? `text-align:${this.align}` : "";
        const inlineStyle = [bounds, alignStyle, this.style].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const attrString = attrsToString(this.attrs);
        const attrs = attrString ? ` ${attrString}` : "";
        const nameAttr = this.name ? ` data-tv-row="${escapeHtml(this.name)}"` : "";
        const content = this.html || escapeHtml(this.text);
        return `<${this.tag}${classAttr}${styleAttr}${attrs}${nameAttr}>${content}</${this.tag}>`;
    }
}

class TVLabel extends TVStaticText {
    constructor({
        text = "",
        className = "",
        style = "",
        attrs = {},
        html = "",
        forId = "",
        hotkey = false,
        x, y, w, h,
    } = {}) {
        const labelAttrs = { ...attrs };
        if (forId) {
            labelAttrs.for = forId;
        }
        super({
            tag: "span",
            className: ["tv-label", className].filter(Boolean).join(" "),
            style,
            attrs: labelAttrs,
            text,
            html: html || (hotkey ? renderHotkeyMarkup(text) : ""),
            x, y, w, h,
        });
    }
}

class TVInputLine extends TVWidget {
    constructor({
        className = "",
        style = "",
        width = "",
        attrs = {},
        x, y, w, h,
    } = {}) {
        super();
        this.className = className;
        this.style = style;
        this.width = width;
        this.attrs = attrs;
        this.x = x; this.y = y; this.w = w; this.h = h;
    }

    renderMarkup() {
        const attrString = attrsToString({ type: "text", ...this.attrs });
        const cls = ["tv-input-line", this.className].filter(Boolean).join(" ");
        const bounds = TVWidget.boundsStyle(this.x, this.y, this.w, this.h);
        const inlineStyle = [bounds, this.width ? `width:${this.width}` : "", this.style].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        return `<input class="${escapeHtml(cls)}"${styleAttr} ${attrString}>`;
    }
}

class TVListViewer extends TVWidget {
    constructor({
        tag = "div",
        className = "",
        attrs = {},
        items = [],
    } = {}) {
        super();
        this.tag = tag;
        this.className = className;
        this.attrs = attrs;
        this.items = items;
    }

    renderMarkup() {
        const classAttr = this.className ? ` class="${escapeHtml(this.className)}"` : "";
        const attrString = attrsToString(this.attrs);
        const attrs = attrString ? ` ${attrString}` : "";
        return `<${this.tag}${classAttr}${attrs}>${this.items.join("")}</${this.tag}>`;
    }
}

class TVGroup extends TVWidget {
    constructor({
        tag = "div",
        className = "",
        columns = "",
        rows = "",
        gap = "",
        align = "",
        padding = "",
        width = "",
        height = "",
        attrs = {},
        children = [],
        html = "",
        x, y, w, h,
    } = {}) {
        super();
        this.tag = tag;
        this.className = className;
        this.columns = columns;
        this.rows = rows;
        this.gap = gap;
        this.align = align;
        this.padding = padding;
        this.width = width;
        this.height = height;
        this.attrs = attrs;
        this.children = children;
        this.html = html;
        this.x = x; this.y = y; this.w = w; this.h = h;
    }

    /** True if any child has absolute positioning (x or y). */
    _hasPositionedChildren() {
        return this.children.some((child) =>
            child && typeof child === "object" && (child.x !== undefined || child.y !== undefined)
        );
    }

    renderChildren() {
        if (this.html) {
            return this.html;
        }
        return this.children.map((child) => {
            if (typeof child === "string") {
                return child;
            }
            if (child && typeof child.renderMarkup === "function") {
                return child.renderMarkup();
            }
            return "";
        }).join("");
    }

    renderMarkup() {
        const cls = ["tv-group", this.className].filter(Boolean).join(" ");
        const bounds = TVWidget.boundsStyle(this.x, this.y, this.w, this.h);
        const positioned = this._hasPositionedChildren() ? "position:relative" : "";
        const parts = [
            bounds,
            positioned,
            this.columns ? `grid-template-columns:${this.columns}` : "",
            this.rows ? `grid-template-rows:${this.rows}` : "",
            this.gap ? `gap:${this.gap}` : "",
            this.align ? `align-items:${this.align}` : "",
            this.padding ? `padding:${this.padding}` : "",
            this.width ? `width:${this.width}` : "",
            this.height ? `height:${this.height}` : "",
        ].filter(Boolean).join(";");
        const styleAttr = parts ? ` style="${escapeHtml(parts)}"` : "";
        const attrString = attrsToString(this.attrs);
        const attrs = attrString ? ` ${attrString}` : "";
        return `<${this.tag} class="${escapeHtml(cls)}"${styleAttr}${attrs}>${this.renderChildren()}</${this.tag}>`;
    }
}

// ── TVInfoBox — framed info-box container with title ────────────────

class TVInfoBox extends TVWidget {
    /**
     * @param {Object} opts
     * @param {string} opts.title   — frame title shown in header
     * @param {number} opts.w       — total width in ch (including border chars)
     * @param {Array}  opts.children — array of TVWidget instances rendered inside the frame
     * @param {number} [opts.x] — absolute left position in ch
     * @param {number} [opts.y] — absolute top position in em
     * @param {number} [opts.h] — explicit height in em
     */
    constructor({ title = "", name = "", borderClass = "", w = 20, children = [], x, y, h, attrs = {}, className = "" } = {}) {
        super();
        this.title = title;
        this.name = name;
        this.borderClass = borderClass;
        this.w = w;
        this.children = children;
        this.x = x; this.y = y; this.h = h;
        this.attrs = attrs;
        this.className = className;
        this._el = null;
        this._rows = {};
    }

    get innerW() { return this.w - 2; }

    renderMarkup() {
        const innerW = this.innerW;
        const parts = [];
        // Header
        parts.push(`<span data-tv-info-frame>${escapeHtml(TVInfoBox.header(innerW, this.title))}</span>`);
        // Children — all TVWidget instances
        for (const child of this.children) {
            if (child && typeof child.renderMarkup === "function") {
                parts.push(child.renderMarkup());
            }
        }
        // Footer
        parts.push(`<span data-tv-info-frame>${escapeHtml(TVInfoBox.footer(innerW))}</span>`);

        const bounds = TVWidget.boundsStyle(this.x, this.y, this.w, this.h);
        const cls = ["tv-info-box", this.className].filter(Boolean).join(" ");
        const attrString = attrsToString(this.attrs);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const extra = attrString ? ` ${attrString}` : "";
        const nameAttr = this.name ? ` data-tv-box="${escapeHtml(this.name)}"` : "";
        return `<div class="${escapeHtml(cls)}" data-tv-info-w="${innerW}"${nameAttr}${style}${extra}>${parts.join("")}</div>`;
    }

    resolve(rootEl) {
        this._el = null;
        this._rows = {};
        if (!rootEl) { return this; }
        this._el = this.name
            ? rootEl.querySelector(`[data-tv-box="${this.name}"]`)
            : rootEl.querySelector(".tv-info-box");
        if (!this._el) { return this; }
        for (const child of this.children) {
            if (child && child.name) {
                const el = this._el.querySelector(`[data-tv-row="${child.name}"]`);
                if (el) { this._rows[child.name] = el; }
            }
        }
        return this;
    }

    updateRow(name, text) {
        const el = this._rows[name];
        if (!el) { return; }
        el.innerHTML = TVInfoBox.rowHtml(this.innerW, text, this.borderClass);
    }

    updateRowHTML(name, html, contentLen) {
        const el = this._rows[name];
        if (!el) { return; }
        const w = this.innerW;
        const B = this.borderClass
            ? `<span class="${escapeHtml(this.borderClass)}">\u2502</span>`
            : "\u2502";
        const padding = " ".repeat(Math.max(0, w - 1 - contentLen));
        el.innerHTML = B + " " + html + padding + B;
    }

    getRow(name) {
        return this._rows[name] || null;
    }

    /** ┌─── Title ───┐ */
    static header(width, title) {
        const padded = ` ${title} `;
        const titleLen = padded.length;
        const left = (width - titleLen) >> 1;
        const right = width - titleLen - left;
        return "\u250C" + "\u2500".repeat(left) + padded + "\u2500".repeat(right) + "\u2510";
    }

    /** └─────────────┘ */
    static footer(width) {
        return "\u2514" + "\u2500".repeat(width) + "\u2518";
    }

    /** ├─── Title ───┤ */
    static separator(width, title) {
        const padded = ` ${title} `;
        const titleLen = padded.length;
        const left = (width - titleLen) >> 1;
        const right = width - titleLen - left;
        return "\u251C" + "\u2500".repeat(left) + padded + "\u2500".repeat(right) + "\u2524";
    }

    /** │ Label: value │  (as innerHTML with styled border) */
    static rowHtml(width, content, borderClass) {
        const B = borderClass
            ? `<span class="${escapeHtml(borderClass)}">\u2502</span>`
            : "\u2502";
        return B + " " + escapeHtml(content) + " ".repeat(Math.max(0, width - 1 - content.length)) + B;
    }

    /** Apply header/footer/separator text to elements from a spec array.
     *  spec: [{ el, type: "header"|"footer"|"separator", title }] */
    static applyBorders(width, specs) {
        for (const { el, type, title } of specs) {
            if (!el) { continue; }
            if (type === "header") { el.textContent = TVInfoBox.header(width, title); }
            else if (type === "footer") { el.textContent = TVInfoBox.footer(width); }
            else if (type === "separator") { el.textContent = TVInfoBox.separator(width, title); }
        }
    }
}

class TVListBox extends TVWidget {
    constructor(root = null, {
        itemClassName = "",
        itemAttrName = "data-tv-list-index",
        selectedClassName = "is-selected",
        renderItemContent = null,
        renderItemMarkup = null,
    } = {}) {
        super(root);
        this.itemClassName = itemClassName;
        this.itemAttrName = itemAttrName;
        this.selectedClassName = selectedClassName;
        this.renderItemContent = renderItemContent;
        this.renderItemMarkup = renderItemMarkup;
        this.items = [];
        this.selectedIndex = -1;
        this.selectHandler = null;
        this.activateHandler = null;
    }

    itemSelector() {
        return `[${this.itemAttrName}]`;
    }

    resolveIndex(target) {
        const element = target && target.closest ? target.closest(this.itemSelector()) : null;
        if (!element) {
            return -1;
        }
        const value = Number.parseInt(element.getAttribute(this.itemAttrName), 10);
        return Number.isInteger(value) ? value : -1;
    }

    defaultContent(item, index) {
        if (this.renderItemContent) {
            return this.renderItemContent(item, index);
        }
        if (typeof item === "string") {
            return escapeHtml(item);
        }
        return escapeHtml(item && item.label ? item.label : "");
    }

    defaultMarkup(item, index) {
        const className = [
            this.itemClassName,
            index === this.selectedIndex ? this.selectedClassName : "",
        ].filter(Boolean).join(" ");
        return `
            <div role="button" tabindex="0" class="${className}" ${this.itemAttrName}="${index}">
                <span class="tv-colors-list-text">${this.defaultContent(item, index)}</span>
            </div>
        `;
    }

    itemMarkup(item, index) {
        if (this.renderItemMarkup) {
            return this.renderItemMarkup(item, index, index === this.selectedIndex);
        }
        return this.defaultMarkup(item, index);
    }

    setItems(items = [], selectedIndex = -1) {
        this.items = Array.isArray(items) ? [...items] : [];
        if (this.root) {
            this.root.innerHTML = this.items.map((item, index) => this.itemMarkup(item, index)).join("");
        }
        this.select(selectedIndex, { scroll: false });
    }

    select(index, { scroll = true } = {}) {
        if (!Number.isInteger(index) || index < 0 || index >= this.items.length) {
            this.selectedIndex = -1;
        } else {
            this.selectedIndex = index;
        }
        this.updateSelectionUi(scroll);
    }

    selectedItem() {
        return this.selectedIndex >= 0 ? this.items[this.selectedIndex] : null;
    }

    selectedElement() {
        return this.root
            ? this.root.querySelector(`${this.itemSelector()}[${this.itemAttrName}="${this.selectedIndex}"]`)
            : null;
    }

    updateSelectionUi(scroll = true) {
        if (!this.root) {
            return;
        }
        this.queryAll(this.itemSelector()).forEach((element) => {
            const value = Number.parseInt(element.getAttribute(this.itemAttrName), 10);
            element.classList.toggle(this.selectedClassName, value === this.selectedIndex);
        });
        if (scroll) {
            this.ensureSelectionVisible();
        }
    }

    ensureSelectionVisible() {
        const element = this.selectedElement();
        if (!element || !this.root) {
            return;
        }
        const top = element.offsetTop;
        const bottom = top + element.offsetHeight;
        const viewTop = this.root.scrollTop;
        const viewBottom = viewTop + this.root.clientHeight;

        if (top < viewTop) {
            this.root.scrollTop = top;
        } else if (bottom > viewBottom) {
            this.root.scrollTop = bottom - this.root.clientHeight;
        }
    }

    bind({ onSelect = null, onActivate = null } = {}) {
        this.selectHandler = onSelect;
        this.activateHandler = onActivate;
        if (!this.root || this.root.dataset.tvListBoxBound === "1") {
            return;
        }
        this.root.dataset.tvListBoxBound = "1";
        this.root.addEventListener("click", (event) => {
            const index = this.resolveIndex(event.target);
            if (index < 0) {
                return;
            }
            this.select(index);
            if (this.selectHandler) {
                this.selectHandler(this.items[index], index, event);
            }
        });
        this.root.addEventListener("dblclick", (event) => {
            const index = this.resolveIndex(event.target);
            if (index < 0) {
                return;
            }
            this.select(index);
            if (this.activateHandler) {
                this.activateHandler(this.items[index], index, event);
            }
        });
    }
}

class TVVerticalListViewer extends TVWidget {
    static renderMarkup({
        rootClass = "",
        rootAttrs = {},
        viewportClass = "",
        scrollbarClass = "tv-vlist-scrollbar",
        arrowClass = "tv-vlist-arrow",
        trackClass = "tv-vlist-track",
        cellsClass = "tv-vlist-cells",
        thumbClass = "tv-vlist-thumb",
    } = {}) {
        const rootAttrString = attrsToString(rootAttrs);
        const rootAttrsText = rootAttrString ? ` ${rootAttrString}` : "";
        return `
            <div class="${escapeHtml(rootClass)}"${rootAttrsText}>
                <div class="${escapeHtml(viewportClass)}" data-tv-list-viewport></div>
                <div class="${escapeHtml(scrollbarClass)}" aria-hidden="true">
                    <button type="button" class="${escapeHtml(arrowClass)}" data-tv-list-backward tabindex="-1">${escapeHtml(displayCp437Char(30))}</button>
                    <div class="${escapeHtml(trackClass)}" data-tv-list-track>
                        <div class="${escapeHtml(cellsClass)}" data-tv-list-cells></div>
                        <div class="${escapeHtml(thumbClass)}" data-tv-list-thumb></div>
                    </div>
                    <button type="button" class="${escapeHtml(arrowClass)}" data-tv-list-forward tabindex="-1">${escapeHtml(displayCp437Char(31))}</button>
                </div>
            </div>
        `;
    }

    constructor(root = null, {
        itemClassName = "",
        itemAttrName = "data-tv-list-index",
        selectedClassName = "is-selected",
        renderItemContent = null,
        renderItemMarkup = null,
    } = {}) {
        super(root);
        this.itemClassName = itemClassName;
        this.itemAttrName = itemAttrName;
        this.selectedClassName = selectedClassName;
        this.renderItemContent = renderItemContent;
        this.renderItemMarkup = renderItemMarkup;
        this.items = [];
        this.selectedIndex = -1;
        this.selectHandler = null;
        this.activateHandler = null;
        this.repeatTimer = null;
        this.viewport = this.query("[data-tv-list-viewport]");
        this.track = this.query("[data-tv-list-track]");
        this.cells = this.query("[data-tv-list-cells]");
        this.thumb = this.query("[data-tv-list-thumb]");
        this.backward = this.query("[data-tv-list-backward]");
        this.forward = this.query("[data-tv-list-forward]");
    }

    itemSelector() {
        return `[${this.itemAttrName}]`;
    }

    resolveIndex(target) {
        const element = target && target.closest ? target.closest(this.itemSelector()) : null;
        if (!element) {
            return -1;
        }
        const value = Number.parseInt(element.getAttribute(this.itemAttrName), 10);
        return Number.isInteger(value) ? value : -1;
    }

    defaultContent(item, index) {
        if (this.renderItemContent) {
            return this.renderItemContent(item, index);
        }
        if (typeof item === "string") {
            return escapeHtml(item);
        }
        return escapeHtml(item && item.label ? item.label : "");
    }

    defaultMarkup(item, index) {
        const className = [
            this.itemClassName,
            index === this.selectedIndex ? this.selectedClassName : "",
        ].filter(Boolean).join(" ");
        return `
            <div role="button" tabindex="0" class="${className}" ${this.itemAttrName}="${index}">
                <span class="tv-colors-list-text">${this.defaultContent(item, index)}</span>
            </div>
        `;
    }

    itemMarkup(item, index) {
        if (this.renderItemMarkup) {
            return this.renderItemMarkup(item, index, index === this.selectedIndex);
        }
        return this.defaultMarkup(item, index);
    }

    setItems(items = [], selectedIndex = -1) {
        this.items = Array.isArray(items) ? [...items] : [];
        if (this.viewport) {
            this.viewport.innerHTML = this.items.map((item, index) => this.itemMarkup(item, index)).join("");
            this.viewport.scrollTop = 0;
        }
        this.select(selectedIndex, { scroll: false });
        this.updateScrollbar();
    }

    select(index, { scroll = true } = {}) {
        if (!Number.isInteger(index) || index < 0 || index >= this.items.length) {
            this.selectedIndex = -1;
        } else {
            this.selectedIndex = index;
        }
        this.updateSelectionUi(scroll);
    }

    selectedItem() {
        return this.selectedIndex >= 0 ? this.items[this.selectedIndex] : null;
    }

    selectedElement() {
        return this.viewport
            ? this.viewport.querySelector(`${this.itemSelector()}[${this.itemAttrName}="${this.selectedIndex}"]`)
            : null;
    }

    updateSelectionUi(scroll = true) {
        if (!this.viewport) {
            return;
        }
        this.viewport.querySelectorAll(this.itemSelector()).forEach((element) => {
            const value = Number.parseInt(element.getAttribute(this.itemAttrName), 10);
            element.classList.toggle(this.selectedClassName, value === this.selectedIndex);
        });
        if (scroll) {
            this.ensureSelectionVisible();
        }
        this.updateScrollbar();
    }

    ensureSelectionVisible() {
        const element = this.selectedElement();
        if (!element || !this.viewport) {
            return;
        }
        const top = element.offsetTop;
        const bottom = top + element.offsetHeight;
        const viewTop = this.viewport.scrollTop;
        const viewBottom = viewTop + this.viewport.clientHeight;

        if (top < viewTop) {
            this.viewport.scrollTop = top;
        } else if (bottom > viewBottom) {
            this.viewport.scrollTop = bottom - this.viewport.clientHeight;
        }
    }

    visibleRows() {
        if (!this.viewport) {
            return 1;
        }
        return Math.max(1, Math.floor(this.viewport.clientHeight / measureCells().height));
    }

    maxScrollRows() {
        return Math.max(this.items.length - this.visibleRows(), 0);
    }

    scrollRow() {
        if (!this.viewport) {
            return 0;
        }
        return Math.round(this.viewport.scrollTop / measureCells().height);
    }

    setScrollRow(row) {
        if (!this.viewport) {
            return;
        }
        const clamped = Math.min(Math.max(row, 0), this.maxScrollRows());
        this.viewport.scrollTop = clamped * measureCells().height;
        this.updateScrollbar();
    }

    updateScrollbar() {
        if (!this.track || !this.cells || !this.thumb) {
            return;
        }
        const cellHeight = measureCells().height;
        const trackRows = Math.max(1, Math.floor(this.track.clientHeight / cellHeight));
        const maxScroll = this.maxScrollRows();
        const scrollRow = this.scrollRow();
        const thumbRows = maxScroll > 0 ? 1 : 0;
        const freeRows = Math.max(trackRows - thumbRows, 0);
        const thumbStart = maxScroll > 0 ? Math.round((scrollRow / maxScroll) * freeRows) : 0;
        const trackChar = maxScroll > 0 ? TRACK_CHAR : DISABLED_TRACK_CHAR;

        this.cells.innerHTML = "";
        this.thumb.innerHTML = "";
        this.cells.style.gridTemplateRows = `repeat(${trackRows}, 1em)`;
        this.thumb.style.gridTemplateRows = `repeat(${thumbRows}, 1em)`;
        this.thumb.style.transform = `translateY(${thumbStart * cellHeight}px)`;

        for (let index = 0; index < trackRows; index += 1) {
            const cell = document.createElement("span");
            cell.className = "tv-colors-scroll-cell";
            cell.textContent = trackChar;
            this.cells.appendChild(cell);
        }
        for (let index = 0; index < thumbRows; index += 1) {
            const cell = document.createElement("span");
            cell.className = "tv-colors-thumb-cell";
            cell.textContent = THUMB_CHAR;
            this.thumb.appendChild(cell);
        }

        if (this.root) {
            this.root.classList.toggle("is-disabled", maxScroll <= 0);
        }
        this.thumb.style.display = thumbRows > 0 ? "grid" : "none";
    }

    scrollBy(delta) {
        this.setScrollRow(this.scrollRow() + delta);
    }

    onTrackMouseDown(event) {
        if (event.target.closest("[data-tv-list-thumb]")) {
            return;
        }
        event.preventDefault();
        const maxScroll = this.maxScrollRows();
        if (maxScroll <= 0 || !this.track) {
            return;
        }
        const rect = this.track.getBoundingClientRect();
        const cellHeight = measureCells().height;
        const trackRows = Math.max(1, Math.floor(this.track.clientHeight / cellHeight));
        const clickRow = Math.max(0, Math.floor((event.clientY - rect.top) / cellHeight));
        const freeRows = Math.max(trackRows - 1, 0);
        const targetRow = freeRows > 0 ? Math.round((clickRow / freeRows) * maxScroll) : 0;
        this.setScrollRow(targetRow);
    }

    startRepeat(event, delta) {
        event.preventDefault();
        this.stopRepeat();
        this.scrollBy(delta);
        this.repeatTimer = window.setInterval(() => this.scrollBy(delta), SCROLL_REPEAT_MS);
    }

    stopRepeat() {
        if (this.repeatTimer !== null) {
            window.clearInterval(this.repeatTimer);
            this.repeatTimer = null;
        }
    }

    bind({ onSelect = null, onActivate = null } = {}) {
        this.selectHandler = onSelect;
        this.activateHandler = onActivate;
        if (!this.root || this.root.dataset.tvListViewerBound === "1") {
            return;
        }
        this.root.dataset.tvListViewerBound = "1";
        if (this.viewport) {
            this.viewport.addEventListener("click", (event) => {
                const index = this.resolveIndex(event.target);
                if (index < 0) {
                    return;
                }
                this.select(index);
                if (this.selectHandler) {
                    this.selectHandler(this.items[index], index, event);
                }
            });
            this.viewport.addEventListener("dblclick", (event) => {
                const index = this.resolveIndex(event.target);
                if (index < 0) {
                    return;
                }
                this.select(index);
                if (this.activateHandler) {
                    this.activateHandler(this.items[index], index, event);
                }
            });
            this.viewport.addEventListener("keydown", (event) => {
                const index = this.resolveIndex(event.target);
                if (index < 0) {
                    return;
                }
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    this.select(index);
                    if (this.activateHandler) {
                        this.activateHandler(this.items[index], index, event);
                    } else if (this.selectHandler) {
                        this.selectHandler(this.items[index], index, event);
                    }
                }
            });
            this.viewport.addEventListener("scroll", () => this.updateScrollbar(), { passive: true });
            this.viewport.addEventListener("wheel", () => this.updateScrollbar(), { passive: true });
        }
        if (this.backward) {
            this.backward.addEventListener("mousedown", (event) => this.startRepeat(event, -1));
        }
        if (this.forward) {
            this.forward.addEventListener("mousedown", (event) => this.startRepeat(event, 1));
        }
        if (this.track) {
            this.track.addEventListener("mousedown", (event) => this.onTrackMouseDown(event));
        }
        document.addEventListener("mouseup", () => this.stopRepeat(), { passive: true });
        window.addEventListener("resize", () => this.updateScrollbar(), { passive: true });
    }
}

class TVVerticalScrollArea extends TVWidget {
    static renderMarkup({
        rootClass = "",
        rootAttrs = {},
        viewportClass = "",
        scrollbarClass = "",
        arrowClass = "",
        trackClass = "",
        cellsClass = "",
        thumbClass = "",
    } = {}) {
        const rootAttrString = attrsToString(rootAttrs);
        const rootAttrsText = rootAttrString ? ` ${rootAttrString}` : "";
        return `
            <div class="${escapeHtml(rootClass)}"${rootAttrsText}>
                <div class="${escapeHtml(viewportClass)}" data-tv-scroll-viewport></div>
                <div class="${escapeHtml(scrollbarClass)}" aria-hidden="true">
                    <button type="button" class="${escapeHtml(arrowClass)}" data-tv-scroll-backward tabindex="-1">${escapeHtml(displayCp437Char(30))}</button>
                    <div class="${escapeHtml(trackClass)}" data-tv-scroll-track>
                        <div class="${escapeHtml(cellsClass)}" data-tv-scroll-cells></div>
                        <div class="${escapeHtml(thumbClass)}" data-tv-scroll-thumb></div>
                    </div>
                    <button type="button" class="${escapeHtml(arrowClass)}" data-tv-scroll-forward tabindex="-1">${escapeHtml(displayCp437Char(31))}</button>
                </div>
            </div>
        `;
    }

    constructor(root = null) {
        super(root);
        this.viewport = this.query("[data-tv-scroll-viewport]");
        this.track = this.query("[data-tv-scroll-track]");
        this.cells = this.query("[data-tv-scroll-cells]");
        this.thumb = this.query("[data-tv-scroll-thumb]");
        this.backward = this.query("[data-tv-scroll-backward]");
        this.forward = this.query("[data-tv-scroll-forward]");
        this.repeatTimer = null;
    }

    maxScroll() {
        if (!this.viewport) {
            return 0;
        }
        return Math.max(this.viewport.scrollHeight - this.viewport.clientHeight, 0);
    }

    lineHeight() {
        return measureCells().height;
    }

    setScrollPosition(value) {
        if (!this.viewport) {
            return;
        }
        const clamped = Math.min(Math.max(value, 0), this.maxScroll());
        this.viewport.scrollTop = clamped;
        this.update();
    }

    scrollStep(direction) {
        this.setScrollPosition((this.viewport ? this.viewport.scrollTop : 0) + (direction * this.lineHeight()));
    }

    startRepeat(event, direction) {
        event.preventDefault();
        this.stopRepeat();
        this.scrollStep(direction);
        this.repeatTimer = window.setInterval(() => this.scrollStep(direction), SCROLL_REPEAT_MS);
    }

    stopRepeat() {
        if (this.repeatTimer !== null) {
            window.clearInterval(this.repeatTimer);
            this.repeatTimer = null;
        }
    }

    onTrackMouseDown(event) {
        if (event.target.closest("[data-tv-scroll-thumb]")) {
            return;
        }
        event.preventDefault();
        if (!this.track) {
            return;
        }
        const maxScroll = this.maxScroll();
        const cellHeight = this.lineHeight();
        const trackRows = Math.max(1, Math.floor(this.track.clientHeight / cellHeight));
        const freeRows = Math.max(trackRows - 1, 0);
        const rect = this.track.getBoundingClientRect();
        const clickRow = Math.max(0, Math.floor((event.clientY - rect.top) / cellHeight));
        const ratio = freeRows > 0 ? clickRow / freeRows : 0;
        this.setScrollPosition(ratio * maxScroll);
    }

    update() {
        if (!this.track || !this.cells || !this.thumb || !this.viewport) {
            return;
        }
        const cellHeight = this.lineHeight();
        const trackRows = Math.max(1, Math.floor(this.track.clientHeight / cellHeight));
        const maxScroll = this.maxScroll();
        const thumbRows = maxScroll > 0 ? 1 : 0;
        const freeRows = Math.max(trackRows - thumbRows, 0);
        const ratio = maxScroll > 0 ? this.viewport.scrollTop / maxScroll : 0;
        const thumbStart = Math.round(freeRows * ratio);
        const trackChar = maxScroll > 0 ? TRACK_CHAR : DISABLED_TRACK_CHAR;

        this.cells.innerHTML = "";
        this.thumb.innerHTML = "";
        this.cells.style.gridTemplateRows = `repeat(${trackRows}, 1em)`;
        this.thumb.style.gridTemplateRows = `repeat(${thumbRows}, 1em)`;
        this.thumb.style.transform = `translateY(${thumbStart * cellHeight}px)`;

        for (let index = 0; index < trackRows; index += 1) {
            const cell = document.createElement("span");
            cell.className = "tv-search-scroll-cell";
            cell.textContent = trackChar;
            this.cells.appendChild(cell);
        }
        for (let index = 0; index < thumbRows; index += 1) {
            const cell = document.createElement("span");
            cell.className = "tv-search-thumb-cell";
            cell.textContent = THUMB_CHAR;
            this.thumb.appendChild(cell);
        }

        if (this.root) {
            this.root.classList.toggle("is-disabled", maxScroll <= 0);
        }
        this.thumb.style.display = thumbRows > 0 ? "grid" : "none";
    }

    bind() {
        if (!this.root || this.root.dataset.tvScrollAreaBound === "1") {
            return;
        }
        this.root.dataset.tvScrollAreaBound = "1";
        if (this.viewport) {
            this.viewport.addEventListener("scroll", () => this.update(), { passive: true });
            this.viewport.addEventListener("wheel", () => this.update(), { passive: true });
        }
        if (this.backward) {
            this.backward.addEventListener("mousedown", (event) => this.startRepeat(event, -1));
        }
        if (this.forward) {
            this.forward.addEventListener("mousedown", (event) => this.startRepeat(event, 1));
        }
        if (this.track) {
            this.track.addEventListener("mousedown", (event) => this.onTrackMouseDown(event));
        }
        document.addEventListener("mouseup", () => this.stopRepeat(), { passive: true });
        window.addEventListener("resize", () => this.update(), { passive: true });
    }
}

class TVMenuBox extends TVWidget {
    constructor({
        className = "tv-menu-popup",
        attrs = {},
        items = [],
    } = {}) {
        super();
        this.className = className;
        this.attrs = attrs;
        this.items = items;
    }

    renderMarkup() {
        const popupAttrs = attrsToString(this.attrs);
        const attrs = popupAttrs ? ` ${popupAttrs}` : "";
        const borderFill = '<span class="tv-border-fill" data-tv-border-fill="\u2500" aria-hidden="true"></span>';
        const scrollbarMarkup = '<div class="tv-scrollbar tv-scrollbar-y tv-menu-popup-scrollbar" data-tv-menu-scrollbar hidden aria-hidden="true">'
            + `<button type="button" class="tv-scroll-arrow" data-tv-menu-scroll-backward tabindex="-1">${escapeHtml(displayCp437Char(30))}</button>`
            + '<div class="tv-scroll-track" data-tv-menu-scroll-track>'
            + '<div class="tv-scroll-cells" data-tv-menu-scroll-cells></div>'
            + '<div class="tv-scroll-thumb" data-tv-menu-scroll-thumb></div>'
            + '</div>'
            + `<button type="button" class="tv-scroll-arrow" data-tv-menu-scroll-forward tabindex="-1">${escapeHtml(displayCp437Char(31))}</button>`
            + '</div>';
        // Split items into segments at separator strings to render them as body-level rows.
        const segments = [[]];
        for (const item of this.items) {
            const html = typeof item === "string" ? item : item.renderMarkup();
            if (typeof item === "string" && html.indexOf("tv-menu-popup-separator") !== -1) {
                segments.push("separator");
                segments.push([]);
            } else {
                segments[segments.length - 1].push(html);
            }
        }
        const bodyRows = [];
        for (const seg of segments) {
            if (seg === "separator") {
                bodyRows.push(
                    '<div class="tv-menu-popup-separator" aria-hidden="true">'
                    + '<span class="tv-border-corner tv-menu-popup-separator-left">\u251C</span>'
                    + '<span class="tv-border-fill tv-menu-popup-separator-fill" data-tv-border-fill="\u2500"></span>'
                    + '<span class="tv-border-corner tv-menu-popup-separator-right">\u2524</span>'
                    + '<span class="tv-border-fill tv-menu-popup-separator-scroll-fill" data-tv-border-fill="\u2500"></span>'
                    + '<span class="tv-border-corner tv-menu-popup-separator-frame-right">\u2524</span>'
                    + '</div>'
                );
            } else if (seg.length > 0) {
                bodyRows.push(
                    '<span class="tv-border-side tv-menu-popup-side tv-menu-popup-side-left" data-tv-border-side="\u2502" aria-hidden="true"></span>'
                    + '<div class="tv-menu-popup-items">' + seg.join("") + '</div>'
                    + '<span class="tv-border-side tv-menu-popup-side tv-menu-popup-side-right" data-tv-border-side="\u2502" aria-hidden="true"></span>'
                );
            }
        }
        return '<div class="' + this.className + '"' + attrs + '>'
            + '<div class="tv-menu-popup-row">'
            + '<span class="tv-border-corner" aria-hidden="true">\u250C</span>'
            + borderFill
            + '<span class="tv-border-corner" aria-hidden="true">\u2510</span>'
            + '</div>'
            + '<div class="tv-menu-popup-main">'
            + '<div class="tv-menu-popup-body">'
            + bodyRows.join("")
            + '</div>'
            + scrollbarMarkup
            + '<span class="tv-border-side tv-menu-popup-frame-side" data-tv-border-side="\u2502" aria-hidden="true"></span>'
            + '</div>'
            + '<div class="tv-menu-popup-row">'
            + '<span class="tv-border-corner" aria-hidden="true">\u2514</span>'
            + borderFill
            + '<span class="tv-border-corner" aria-hidden="true">\u2518</span>'
            + '</div>'
            + '</div>';
    }
}

function getMenuPopupScrollbarParts(popup) {
    if (!popup) {
        return null;
    }
    const body = popup.querySelector(".tv-menu-popup-body");
    const scrollbar = popup.querySelector("[data-tv-menu-scrollbar]");
    const track = popup.querySelector("[data-tv-menu-scroll-track]");
    const cells = popup.querySelector("[data-tv-menu-scroll-cells]");
    const thumb = popup.querySelector("[data-tv-menu-scroll-thumb]");
    const backward = popup.querySelector("[data-tv-menu-scroll-backward]");
    const forward = popup.querySelector("[data-tv-menu-scroll-forward]");
    return body && scrollbar && track && cells && thumb && backward && forward
        ? { body, scrollbar, track, cells, thumb, backward, forward }
        : null;
}

function stopMenuPopupScrollRepeat(popup) {
    const state = popup && popup._tvMenuPopupScrollbarState;
    if (!state || state.repeatTimer === null) {
        return;
    }
    window.clearInterval(state.repeatTimer);
    state.repeatTimer = null;
}

function setMenuPopupScrollTop(popup, scrollTop) {
    const parts = getMenuPopupScrollbarParts(popup);
    if (!parts) {
        return;
    }
    const maxScroll = Math.max(parts.body.scrollHeight - parts.body.clientHeight, 0);
    parts.body.scrollTop = Math.min(Math.max(scrollTop, 0), maxScroll);
    syncMenuPopupScrollbar(popup);
}

function scrollMenuPopupByRows(popup, deltaRows) {
    const parts = getMenuPopupScrollbarParts(popup);
    if (!parts) {
        return;
    }
    const cellHeight = measureCells().height || 16;
    setMenuPopupScrollTop(popup, parts.body.scrollTop + (deltaRows * cellHeight));
}

function getMenuPopupScrollbarMetrics(parts, cellHeight) {
    const scrollbarRows = Math.max(1, Math.floor(parts.scrollbar.clientHeight / cellHeight));
    const trackRows = Math.max(1, scrollbarRows - 2);
    return { scrollbarRows, trackRows };
}

function syncMenuPopupScrollbar(popup) {
    const parts = getMenuPopupScrollbarParts(popup);
    if (!parts) {
        return;
    }
    const { body, scrollbar, track, cells, thumb } = parts;
    const cellHeight = measureCells().height || 16;
    const needsScrollbar = body.scrollHeight > body.clientHeight + 1;
    popup.classList.toggle("is-scrollable", needsScrollbar);
    body.classList.toggle("is-scrollable", needsScrollbar);
    scrollbar.hidden = !needsScrollbar;
    cells.innerHTML = "";
    thumb.innerHTML = "";

    if (!needsScrollbar) {
        track.style.height = "";
        thumb.style.display = "none";
        return;
    }

    const { trackRows } = getMenuPopupScrollbarMetrics(parts, cellHeight);
    const maxScroll = Math.max(body.scrollHeight - body.clientHeight, 0);
    const thumbRows = maxScroll > 0 ? 1 : 0;
    const freeRows = Math.max(trackRows - thumbRows, 0);
    const thumbStart = maxScroll > 0 ? Math.round((body.scrollTop / maxScroll) * freeRows) : 0;
    const trackChar = maxScroll > 0 ? TRACK_CHAR : DISABLED_TRACK_CHAR;

    track.style.height = `${trackRows * cellHeight}px`;
    cells.style.gridTemplateRows = `repeat(${trackRows}, 1em)`;
    thumb.style.gridTemplateRows = `repeat(${thumbRows}, 1em)`;
    thumb.style.transform = `translateY(${thumbStart * cellHeight}px)`;

    for (let index = 0; index < trackRows; index += 1) {
        const cell = document.createElement("span");
        cell.className = "tv-scroll-cell";
        cell.textContent = trackChar;
        cells.appendChild(cell);
    }

    for (let index = 0; index < thumbRows; index += 1) {
        const cell = document.createElement("span");
        cell.className = "tv-scroll-thumb-cell";
        cell.textContent = THUMB_CHAR;
        thumb.appendChild(cell);
    }

    thumb.style.display = thumbRows > 0 ? "grid" : "none";
}

function bindMenuPopupScrollbar(popup) {
    if (!popup || popup.dataset.tvMenuScrollbarBound === "1") {
        return;
    }
    const parts = getMenuPopupScrollbarParts(popup);
    if (!parts) {
        return;
    }
    const state = {
        repeatTimer: null,
        dragState: null,
    };
    popup.dataset.tvMenuScrollbarBound = "1";
    popup._tvMenuPopupScrollbarState = state;

    const startRepeat = (event, direction) => {
        event.preventDefault();
        stopMenuPopupScrollRepeat(popup);
        scrollMenuPopupByRows(popup, direction);
        state.repeatTimer = window.setInterval(() => scrollMenuPopupByRows(popup, direction), SCROLL_REPEAT_MS);
    };

    const onTrackMouseDown = (event) => {
        if (event.target.closest("[data-tv-menu-scroll-thumb]")) {
            return;
        }
        event.preventDefault();
        const cellHeight = measureCells().height || 16;
        const { trackRows } = getMenuPopupScrollbarMetrics(parts, cellHeight);
        const maxScroll = Math.max(parts.body.scrollHeight - parts.body.clientHeight, 0);
        if (maxScroll <= 0) {
            return;
        }
        const rect = parts.track.getBoundingClientRect();
        const clickRow = Math.max(0, Math.floor((event.clientY - rect.top) / cellHeight));
        const thumbRows = 1;
        const freeRows = Math.max(trackRows - thumbRows, 0);
        const targetRow = freeRows > 0 ? Math.round((clickRow / freeRows) * maxScroll / cellHeight) : 0;
        setMenuPopupScrollTop(popup, targetRow * cellHeight);
    };

    const onDragMove = (event) => {
        if (!state.dragState) {
            return;
        }
        const delta = event.clientY - state.dragState.startClientY;
        const scrollDelta = state.dragState.freeTrackPx > 0
            ? (delta / state.dragState.freeTrackPx) * state.dragState.maxScroll
            : 0;
        setMenuPopupScrollTop(popup, state.dragState.startScrollTop + scrollDelta);
    };

    const onDragEnd = () => {
        state.dragState = null;
        document.removeEventListener("mousemove", onDragMove);
        document.removeEventListener("mouseup", onDragEnd);
    };

    const onThumbMouseDown = (event) => {
        event.preventDefault();
        const thumbRect = parts.thumb.getBoundingClientRect();
        const maxScroll = Math.max(parts.body.scrollHeight - parts.body.clientHeight, 0);
        state.dragState = {
            startClientY: event.clientY,
            startScrollTop: parts.body.scrollTop,
            maxScroll,
            freeTrackPx: Math.max(parts.track.clientHeight - thumbRect.height, 0),
        };
        document.addEventListener("mousemove", onDragMove);
        document.addEventListener("mouseup", onDragEnd);
    };

    parts.body.addEventListener("scroll", () => syncMenuPopupScrollbar(popup), { passive: true });
    parts.backward.addEventListener("mousedown", (event) => startRepeat(event, -1));
    parts.forward.addEventListener("mousedown", (event) => startRepeat(event, 1));
    parts.track.addEventListener("mousedown", onTrackMouseDown);
    parts.thumb.addEventListener("mousedown", onThumbMouseDown);
    document.addEventListener("mouseup", () => stopMenuPopupScrollRepeat(popup), { passive: true });
    window.addEventListener("resize", () => syncMenuPopupScrollbar(popup), { passive: true });
}

function resetMenuPopupLayout(popup) {
    if (!popup) {
        return;
    }
    bindMenuPopupScrollbar(popup);
    popup.classList.remove("is-scrollable");
    popup.style.top = "";
    popup.style.maxHeight = "";
    const body = popup.querySelector(".tv-menu-popup-body");
    if (body) {
        body.scrollTop = 0;
        body.style.maxHeight = "";
        body.style.overflowY = "";
        body.classList.remove("is-scrollable");
    }
    const parts = getMenuPopupScrollbarParts(popup);
    if (parts) {
        parts.scrollbar.hidden = true;
        syncMenuPopupScrollbar(popup);
    }
}

function fitMenuPopupToViewport(root, popup) {
    if (!root || !popup) {
        return;
    }
    bindMenuPopupScrollbar(popup);
    const cellHeight = measureCells().height || 16;
    const rootRect = root.getBoundingClientRect();
    const parentPopupRect = root.matches("[data-tv-submenu-root]")
        ? root.closest(".tv-menu-popup")?.getBoundingClientRect() || null
        : null;
    const defaultTop = root.matches("[data-tv-submenu-root]") ? -cellHeight : rootRect.height;
    const body = popup.querySelector(".tv-menu-popup-body");

    popup.classList.remove("is-scrollable");
    popup.style.top = `${defaultTop}px`;
    popup.style.maxHeight = "";
    if (body) {
        body.scrollTop = 0;
        body.style.maxHeight = "";
        body.style.overflowY = "";
        body.classList.remove("is-scrollable");
    }

    let popupRect = popup.getBoundingClientRect();
    const reservedBottomRows = 2;
    const minGlobalTop = parentPopupRect ? parentPopupRect.top : rootRect.top + defaultTop;
    const availablePopupHeight = Math.max(
        cellHeight * 4,
        window.innerHeight - (cellHeight * reservedBottomRows) - minGlobalTop,
    );
    const maxPopupRows = Math.max(4, Math.floor(availablePopupHeight / cellHeight));
    const maxPopupHeight = maxPopupRows * cellHeight;
    if (popupRect.height > maxPopupHeight && body) {
        const maxBodyHeight = Math.max(cellHeight, maxPopupHeight - (cellHeight * 2));
        popup.classList.add("is-scrollable");
        popup.style.maxHeight = `${Math.round(maxPopupHeight)}px`;
        body.style.maxHeight = `${Math.round(maxBodyHeight)}px`;
        body.style.overflowY = "auto";
        body.classList.add("is-scrollable");
        popupRect = popup.getBoundingClientRect();
    }

    let nextTop = defaultTop;
    const minTop = minGlobalTop - rootRect.top;
    const maxTop = minGlobalTop + maxPopupHeight - rootRect.top - popupRect.height;
    if (nextTop > maxTop) {
        nextTop = maxTop;
    }
    if (nextTop < minTop) {
        nextTop = minTop;
    }

    popup.style.top = `${Math.round(nextTop)}px`;
    syncMenuPopupScrollbar(popup);
    window.requestAnimationFrame(() => {
        if (!popup.hidden) {
            syncMenuPopupScrollbar(popup);
        }
    });
}

class TVButtonStrip extends TVWidget {
    constructor({
        className = "",
        attrs = {},
        buttons = [],
        x, y, w, h,
    } = {}) {
        super();
        this.className = className;
        this.attrs = attrs;
        this.buttons = buttons;
        this.x = x; this.y = y; this.w = w; this.h = h;
    }

    renderMarkup() {
        return new TVStaticText({
            className: this.className,
            attrs: this.attrs,
            html: this.buttons.map((button) => typeof button === "string" ? button : button.renderMarkup()).join(""),
            x: this.x, y: this.y, w: this.w, h: this.h,
        }).renderMarkup();
    }
}

class TVCheckBoxes extends TVWidget {
    constructor({
        className = "",
        attrs = {},
        options = [],
    } = {}) {
        super();
        this.className = className;
        this.attrs = attrs;
        this.options = options;
    }

    renderMarkup() {
        const items = this.options.map((option, index) => {
            const checked = option.checked ? "X" : " ";
            return `
                <button
                    type="button"
                    class="tv-checkbox-item"
                    data-tv-checkbox-index="${index}"
                    ${attrsToString(option.attrs || {})}
                >[${checked}] ${escapeHtml(option.label || "")}</button>
            `;
        }).join("");
        return new TVListViewer({
            className: this.className,
            attrs: this.attrs,
            items: [items],
        }).renderMarkup();
    }
}

class TVRadioButtons extends TVWidget {
    constructor({
        className = "",
        attrs = {},
        options = [],
    } = {}) {
        super();
        this.className = className;
        this.attrs = attrs;
        this.options = options;
    }

    renderMarkup() {
        const items = this.options.map((option, index) => {
            const checked = option.checked ? "\u00B7" : " ";
            return `
                <button
                    type="button"
                    class="tv-radio-item"
                    data-tv-radio-index="${index}"
                    ${attrsToString(option.attrs || {})}
                >(${checked}) ${escapeHtml(option.label || "")}</button>
            `;
        }).join("");
        return new TVListViewer({
            className: this.className,
            attrs: this.attrs,
            items: [items],
        }).renderMarkup();
    }
}

class TVButton extends TVWidget {
    constructor({
        label = "",
        labelMarkup = "",
        className = "",
        attrs = {},
        dialog = true,
        tag = "button",
        baseClass = "tv-dialog-button",
        width = "",
        x, y, w, h,
    } = {}) {
        super();
        this.labelMarkup = label ? renderHotkeyMarkup(label) : labelMarkup;
        this.className = className;
        this.attrs = attrs;
        this.dialog = dialog;
        this.tag = tag;
        this.baseClass = baseClass;
        this.width = width;
        this.x = x; this.y = y; this.w = w; this.h = h;
    }

    renderMarkup() {
        const baseAttrs = this.tag === "button" ? { type: "button" } : {};
        const attrString = attrsToString({ ...baseAttrs, ...this.attrs });
        const classNames = [this.className].filter(Boolean).join(" ");
        const bounds = TVWidget.boundsStyle(this.x, this.y, this.w, this.h);
        const widthStyle = this.width ? `min-width:${this.width}` : "";
        const inlineStyle = [bounds, widthStyle].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        if (this.dialog) {
            const buttonClass = [this.baseClass, classNames].filter(Boolean).join(" ");
            const shadow = " " + "\u2580".repeat(20);
            return `
                <button class="${buttonClass}"${styleAttr} ${attrString}>
                    <span class="tv-dialog-button-face">
                        <span class="tv-dialog-button-label">${this.labelMarkup}</span>
                        <span class="tv-dialog-button-edge" aria-hidden="true">▄</span>
                    </span>
                    <span class="tv-dialog-button-shadow" aria-hidden="true">${shadow}</span>
                </button>
            `;
        }
        const classAttr = classNames ? ` class="${classNames}"` : "";
        const attrs = attrString ? ` ${attrString}` : "";
        return `<${this.tag}${classAttr}${styleAttr}${attrs}>${this.labelMarkup}</${this.tag}>`;
    }
}

class TVFrame extends TVWidget {
    static closeMarkup(className, attrs = {}) {
        const attrString = attrsToString({
            ...attrs,
            "data-tv-close-button": true,
        });
        return `<button type="button" class="${className}" ${attrString}>[<span class="tv-close-glyph" data-tv-close-glyph>■</span>]</button>`;
    }

    static dialogMarkup({
        overlayClass,
        windowClass,
        ariaLabel,
        titlebarClass,
        bodyClass,
        footerClass,
        titleClass,
        title,
        closeClass,
        closeAttrs,
        bodyMarkup,
        footerMarkup,
        bodyBorders = true,
    }) {
        const overlayClasses = ["tv-dialog-overlay", overlayClass].filter(Boolean).join(" ");
        const windowClasses = ["tv-dialog-window", windowClass].filter(Boolean).join(" ");
        const titlebarClasses = ["tv-dialog-titlebar", titlebarClass].filter(Boolean).join(" ");
        const footerClasses = ["tv-dialog-footer", footerClass].filter(Boolean).join(" ");
        const titleClasses = ["tv-dialog-title-text", titleClass].filter(Boolean).join(" ");
        const closeClasses = ["tv-dialog-close-control", closeClass].filter(Boolean).join(" ");
        const bodyClasses = ["tv-dialog-body", bodyClass].filter(Boolean).join(" ");
        let bodyContent;
        if (Array.isArray(bodyMarkup)) {
            const side = '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
            const sep = '<span class="tv-border-corner" aria-hidden="true">╟</span>'
                + '<span class="tv-border-fill tv-border-separator" data-tv-border-fill="─" aria-hidden="true"></span>'
                + '<span class="tv-border-corner" aria-hidden="true">╢</span>';
            bodyContent = bodyMarkup.map(section => side + section + side).join(sep);
        } else if (bodyBorders) {
            bodyContent = '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>'
                + bodyMarkup
                + '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
        } else {
            bodyContent = bodyMarkup;
        }
        return `
            <div class="${overlayClasses}" hidden>
                <div class="${windowClasses}" role="dialog" aria-modal="true" aria-label="${escapeHtml(ariaLabel)}">
                    <div class="${titlebarClasses}">
                        <span class="tv-border-corner" aria-hidden="true">╔</span>
                        <span class="tv-border-fill tv-dialog-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>
                        ${TVFrame.closeMarkup(closeClasses, closeAttrs)}
                        <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
                        <div class="${titleClasses}">${escapeHtml(title)}</div>
                        <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
                        <span class="tv-border-corner" aria-hidden="true">╗</span>
                    </div>
                    <div class="${bodyClasses}">${bodyContent}</div>
                    <div class="${footerClasses}">${footerMarkup}</div>
                </div>
            </div>
        `;
    }
}

class TVDialog extends TVWidget {
    static footerMarkup() {
        return `
            <span class="tv-border-corner" aria-hidden="true">╚</span>
            <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
            <span class="tv-border-corner" aria-hidden="true">╝</span>
        `;
    }

    constructor({
        desktop,
        overlayClass,
        windowClass,
        ariaLabel,
        title,
        titlebarClass,
        bodyClass,
        footerClass,
        titleClass,
        closeClass,
        closeAttrs = {},
        bodyMarkup,
        footerMarkup,
        bodyBorders,
        width,
        height,
        left,
        top,
    }) {
        const root = TVWidget.fromHTML(
            TVFrame.dialogMarkup({
                overlayClass,
                windowClass,
                ariaLabel,
                titlebarClass,
                bodyClass,
                footerClass,
                titleClass,
                title,
                closeClass,
                closeAttrs,
                bodyMarkup,
                footerMarkup,
                bodyBorders,
            })
        );
        super(root);
        this.desktop = desktop;
        this.overlay = root;
        this.dialog = this.query(".tv-dialog-window");
        this.titlebar = this.query(".tv-dialog-titlebar");
        this.closeButton = this.query(".tv-dialog-close-control");
        if (width) this.dialog.style.setProperty("--tv-dialog-width", width);
        if (height) this.dialog.style.setProperty("--tv-dialog-height", height);
        if (left) this.dialog.style.setProperty("--tv-dialog-left", left);
        if (top) this.dialog.style.setProperty("--tv-dialog-top", top);
        this.hasPosition = false;
        this.dragState = null;
        this.manager = null;
        this.managerName = "";
        this.dialog.tabIndex = -1;
        this.mount(desktop);
        bindCloseButtons(this.overlay);
    }

    setManager(manager, name) {
        this.manager = manager;
        this.managerName = name;
    }

    isOpen() {
        return !this.overlay.hidden;
    }

    isActive() {
        if (!this.manager || !this.managerName) {
            return this.isOpen();
        }
        return this.isOpen() && this.manager.activeTarget === this.managerName;
    }

    open() {
        this.overlay.hidden = false;
        if (!this.hasPosition) {
            this.center();
        }
        fillBorders();
        if (this.manager && this.managerName) {
            this.manager.onDialogOpened(this.managerName);
        }
        try {
            this.dialog.focus({ preventScroll: true });
        } catch {
            this.dialog.focus();
        }
    }

    close() {
        this.overlay.hidden = true;
        if (this.manager && this.managerName) {
            this.manager.onDialogClosed(this.managerName);
        }
    }

    center() {
        const width = this.dialog.offsetWidth;
        const height = this.dialog.offsetHeight;
        const left = Math.max(0, Math.floor((this.overlay.clientWidth - width) / 2));
        const top = Math.max(0, Math.floor((this.overlay.clientHeight - height) / 2));
        this.dialog.style.setProperty("--tv-dialog-left", `${left}px`);
        this.dialog.style.setProperty("--tv-dialog-top", `${top}px`);
    }

    bindCommonClose(onClose = () => this.close()) {
        this.overlay.addEventListener("click", (event) => {
            if (event.target === this.overlay) {
                onClose();
            }
        });
        if (this.closeButton) {
            this.closeButton.addEventListener("mousedown", (event) => event.stopPropagation());
            this.closeButton.addEventListener("mouseup", (event) => {
                event.preventDefault();
                event.stopPropagation();
                onClose();
            });
            this.closeButton.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                onClose();
            });
        }
    }

    bindDrag() {
        if (!this.titlebar) {
            return;
        }
        this.titlebar.addEventListener("mousedown", (event) => this.startDrag(event));
    }

    startDrag(event) {
        if (event.target.closest("button, input, a")) {
            return;
        }
        event.preventDefault();
        const style = getComputedStyle(this.dialog);
        this.dragState = {
            startX: event.clientX,
            startY: event.clientY,
            startLeft: Number.parseFloat(style.getPropertyValue("--tv-dialog-left")) || this.dialog.offsetLeft,
            startTop: Number.parseFloat(style.getPropertyValue("--tv-dialog-top")) || this.dialog.offsetTop,
        };
        document.addEventListener("mousemove", this.onDragMove);
        document.addEventListener("mouseup", this.onDragEnd);
    }

    onDragMove = (event) => {
        if (!this.dragState) {
            return;
        }
        const rawLeft = this.dragState.startLeft + (event.clientX - this.dragState.startX);
        const rawTop = this.dragState.startTop + (event.clientY - this.dragState.startY);
        const maxLeft = Math.max(0, this.overlay.clientWidth - this.dialog.offsetWidth);
        const maxTop = Math.max(0, this.overlay.clientHeight - this.dialog.offsetHeight);
        const nextLeft = Math.min(Math.max(rawLeft, 0), maxLeft);
        const nextTop = Math.min(Math.max(rawTop, 0), maxTop);
        this.dialog.style.setProperty("--tv-dialog-left", `${nextLeft}px`);
        this.dialog.style.setProperty("--tv-dialog-top", `${nextTop}px`);
        this.hasPosition = true;
    };

    onDragEnd = () => {
        this.dragState = null;
        document.removeEventListener("mousemove", this.onDragMove);
        document.removeEventListener("mouseup", this.onDragEnd);
    };
}

class TVDialogManager {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        this.desktop = desktop;
        this.dialogs = new Map();
        this.windows = new Map();
        this.stackOrder = [];
        this.baseZIndex = 10;
        this.hostWindow = document.querySelector("[data-tv-window]");
        this.activeTarget = HOST_WINDOW_TOKEN;
        this.onChange = null;
    }

    setHostWindow(element) {
        this.hostWindow = element || null;
        this.applyActiveStates();
    }

    activateHostWindow() {
        this.activeTarget = HOST_WINDOW_TOKEN;
        this.applyAllZIndices();
        this.applyActiveStates();
    }

    registerWindow(name, element) {
        this.windows.set(name, element);
        if (!element.dataset.tvWindowManaged) {
            element.dataset.tvWindowManaged = "1";
            element.addEventListener("mousedown", () => {
                this.activateWindow(name);
            });
        }
        this.activateWindow(name);
    }

    unregisterWindow(name) {
        this.windows.delete(name);
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        if (this.activeTarget === name) {
            this.activeTarget = this.stackOrder.length
                ? this.stackOrder[this.stackOrder.length - 1]
                : HOST_WINDOW_TOKEN;
        }
        this.applyAllZIndices();
        this.applyActiveStates();
    }

    activateWindow(name) {
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        this.stackOrder.push(name);
        this.activeTarget = name;
        this.applyAllZIndices();
        this.applyActiveStates();
    }

    register(name, dialog) {
        this.dialogs.set(name, dialog);
        if (dialog && typeof dialog.setManager === "function") {
            dialog.setManager(this, name);
        }
        this.installDialogHooks(name, dialog);
        return dialog;
    }

    onDialogOpened(name) {
        if (!this.stackOrder.includes(name)) {
            this.stackOrder.push(name);
        }
        this.bringToFront(name);
        if (this.onChange) { this.onChange(); }
    }

    onDialogClosed(name) {
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        if (this.activeTarget === name) {
            this.activeTarget = this.stackOrder.length
                ? this.stackOrder[this.stackOrder.length - 1]
                : HOST_WINDOW_TOKEN;
        }
        this.applyAllZIndices();
        this.applyActiveStates();
        if (this.onChange) { this.onChange(); }
    }

    installDialogHooks(name, dialog) {
        if (!dialog || !dialog.overlay || dialog.overlay.dataset.tvDialogManaged === "1") {
            return;
        }
        dialog.overlay.dataset.tvDialogManaged = "1";
        dialog.overlay.dataset.tvDialogName = name;
        const focusTarget = dialog.dialog || dialog.overlay;
        focusTarget.addEventListener("mousedown", () => {
            if (dialog.isOpen()) {
                this.bringToFront(name);
            }
        });
    }

    applyAllZIndices() {
        for (let i = 0; i < this.stackOrder.length; i++) {
            const name = this.stackOrder[i];
            const z = this.baseZIndex + i;
            const dialog = this.dialogs.get(name);
            if (dialog && dialog.overlay) {
                dialog.overlay.style.zIndex = String(z);
            }
            const windowEl = this.windows.get(name);
            if (windowEl) {
                windowEl.style.zIndex = String(z);
            }
        }
    }

    applyActiveStates() {
        const target = this.activeTarget;
        const isHostActive = target === HOST_WINDOW_TOKEN;
        if (this.hostWindow) {
            this.hostWindow.classList.toggle("is-window-active", isHostActive);
            this.hostWindow.classList.toggle("is-window-inactive", !isHostActive);
            updateWindowFrameState(this.hostWindow, isHostActive, { dialog: false });
        }
        this.windows.forEach((el, name) => {
            const active = name === target;
            el.classList.toggle("is-window-active", active);
            el.classList.toggle("is-window-inactive", !active);
            updateWindowFrameState(el, active, { dialog: false });
        });
        this.dialogs.forEach((dialog, name) => {
            if (!dialog || !dialog.dialog) {
                return;
            }
            const isOpen = dialog.isOpen();
            const isActive = isOpen && name === target;
            dialog.dialog.classList.toggle("is-window-active", isActive);
            dialog.dialog.classList.toggle("is-window-inactive", isOpen && !isActive);
            updateWindowFrameState(dialog.dialog, isActive, { dialog: true });
        });
    }

    bringToFront(name) {
        const dialog = this.get(name);
        if (!dialog || !dialog.isOpen()) {
            return;
        }
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        this.stackOrder.push(name);
        this.activeTarget = name;
        this.applyAllZIndices();
        this.applyActiveStates();
        try {
            dialog.dialog.focus({ preventScroll: true });
        } catch {
            dialog.dialog.focus();
        }
    }

    get(name) {
        return this.dialogs.get(name) || null;
    }

    isOpen(name) {
        const dialog = this.get(name);
        return Boolean(dialog) && dialog.isOpen();
    }

    open(name, { exclusive = false } = {}) {
        const dialog = this.get(name);
        if (!dialog) {
            return null;
        }
        if (exclusive) {
            this.closeAllExcept(name);
        }
        if (dialog.isOpen()) {
            this.bringToFront(name);
            return dialog;
        }
        dialog.open();
        return dialog;
    }

    close(name) {
        const dialog = this.get(name);
        if (dialog) {
            dialog.close();
        }
    }

    closeAllExcept(except = "") {
        this.dialogs.forEach((dialog, name) => {
            if (name !== except) {
                dialog.close();
            }
        });
    }

    firstOpen(names = []) {
        return names.find((name) => this.isOpen(name)) || "";
    }

    bindOpeners(selector, name, { exclusive = false } = {}) {
        document.querySelectorAll(selector).forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                this.open(name, { exclusive });
            });
        });
    }
}

// ── TVMessageBox ────────────────────────────────────────────────────
// TurboVision-style modal MessageBox (extends TVDialog).
// Blocks all interaction until a button is pressed.
//
// Button flags (combinable):
//   TVMessageBox.MF_OK_BUTTON     — OK button (default action)
//   TVMessageBox.MF_YES_BUTTON    — Yes button
//   TVMessageBox.MF_NO_BUTTON     — No button
//   TVMessageBox.MF_CANCEL_BUTTON — Cancel button (Escape key)
//
// Usage:
//   this.msgBox = new TVMessageBox(parentEl);
//   const cmd = await this.msgBox.show({
//       title: "Game Over", lines: ["Score: 42"],
//       buttons: TVMessageBox.MF_OK_BUTTON,
//   });
//   // cmd === "ok"

class TVMessageBox extends TVDialog {
    // Title types
    static MF_WARNING      = 0;
    static MF_ERROR        = 1;
    static MF_INFORMATION  = 2;
    static MF_CONFIRMATION = 3;
    static TITLES = ["Warning", "Error", "Information", "Confirm"];
    // Button flags
    static MF_YES_BUTTON    = 0x0100;
    static MF_NO_BUTTON     = 0x0200;
    static MF_OK_BUTTON     = 0x0400;
    static MF_CANCEL_BUTTON = 0x0800;
    // Presets
    static MF_OK_CANCEL    = 0x0400 | 0x0800;
    static MF_YES_NO_CANCEL = 0x0100 | 0x0200 | 0x0800;

    static BUTTON_DEFS = [
        { flag: 0x0100, cmd: "yes",    label: "~Y~es" },
        { flag: 0x0200, cmd: "no",     label: "~N~o" },
        { flag: 0x0400, cmd: "ok",     label: "O~K~" },
        { flag: 0x0800, cmd: "cancel", label: "Cancel" },
    ];

    constructor(parentEl) {
        super({
            desktop: parentEl,
            overlayClass: "tv-msgbox-overlay",
            windowClass: "tv-msgbox-window",
            ariaLabel: "Message",
            title: "",
            bodyMarkup: '<div class="tv-msgbox-body" data-tv-msgbox-body>'
                + '<div class="tv-msgbox-content" data-tv-msgbox-content></div>'
                + '<div class="tv-msgbox-buttons" data-tv-msgbox-buttons></div>'
                + '</div>',
            footerMarkup: TVDialog.footerMarkup(),
            width: "auto",
        });
        // Remove close button — msgbox has no [■]
        if (this.closeButton) { this.closeButton.remove(); }
        this.contentEl = this.query("[data-tv-msgbox-content]");
        this.buttonsEl = this.query("[data-tv-msgbox-buttons]");
        this.titleEl = this.query(".tv-dialog-title-text");
        this.hasPosition = true; // CSS handles centering
        this._resolve = null;
        this._onKey = (e) => this._handleKey(e);
        // Block clicks from reaching parent dialog
        this.overlay.addEventListener("click", (e) => e.stopPropagation());
        this.overlay.addEventListener("mousedown", (e) => e.stopPropagation());
    }

    show({ type = 0, title, lines = [], buttons = TVMessageBox.MF_OK_BUTTON } = {}) {
        const boxTitle = title !== undefined ? title : TVMessageBox.TITLES[type];
        if (this.titleEl) { this.titleEl.textContent = boxTitle; }
        // Content
        if (this.contentEl) {
            const parts = [];
            for (const line of lines) {
                parts.push('<div class="tv-msgbox-text">' + escapeHtml(line) + '</div>');
            }
            this.contentEl.innerHTML = parts.join("");
        }
        // Buttons
        const btnDefs = TVMessageBox.BUTTON_DEFS.filter(b => (buttons & b.flag) !== 0);
        if (this.buttonsEl) {
            const btnHtml = btnDefs.map(b =>
                new TVButton({ label: b.label, attrs: { "data-tv-msgbox-cmd": b.cmd } }).renderMarkup()
            ).join("");
            this.buttonsEl.innerHTML = btnHtml;
        }
        // Determine default and cancel commands
        this._defaultCmd = btnDefs.length > 0 ? btnDefs[0].cmd : null;
        this._cancelCmd = (buttons & TVMessageBox.MF_CANCEL_BUTTON) ? "cancel" : null;
        // Show
        this.overlay.hidden = false;
        fillBorders();
        // Focus first button
        const firstBtn = this.buttonsEl && this.buttonsEl.querySelector("button");
        if (firstBtn) { firstBtn.focus(); }
        // Bind events
        this.overlay.addEventListener("keydown", this._onKey);
        if (this.buttonsEl) {
            this.buttonsEl.addEventListener("click", (e) => {
                const btn = e.target.closest("[data-tv-msgbox-cmd]");
                if (btn) { this._dismiss(btn.getAttribute("data-tv-msgbox-cmd")); }
            }, { once: true });
        }
        return new Promise((resolve) => { this._resolve = resolve; });
    }

    hide() {
        this.overlay.hidden = true;
        this.overlay.removeEventListener("keydown", this._onKey);
        this._resolve = null;
    }

    _dismiss(cmd) {
        const resolve = this._resolve;
        this.hide();
        if (resolve) { resolve(cmd); }
    }

    _handleKey(e) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            const focused = this.buttonsEl && this.buttonsEl.querySelector("button:focus");
            const cmd = focused
                ? focused.getAttribute("data-tv-msgbox-cmd")
                : this._defaultCmd;
            if (cmd) { this._dismiss(cmd); }
        } else if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            this._dismiss(this._cancelCmd || this._defaultCmd);
        } else if (e.key === "Tab") {
            // Trap focus within buttons
            const btns = this.buttonsEl ? [...this.buttonsEl.querySelectorAll("button")] : [];
            if (btns.length > 1) {
                e.preventDefault();
                const idx = btns.indexOf(document.activeElement);
                const next = e.shiftKey
                    ? (idx - 1 + btns.length) % btns.length
                    : (idx + 1) % btns.length;
                btns[next].focus();
            }
        } else {
            // Hotkey matching: Y/N/K/C for Yes/No/OK/Cancel
            const key = e.key.toLowerCase();
            const hotkeyMap = { y: "yes", n: "no", k: "ok" };
            if (hotkeyMap[key]) {
                const btn = this.buttonsEl && this.buttonsEl.querySelector(`[data-tv-msgbox-cmd="${hotkeyMap[key]}"]`);
                if (btn) { e.preventDefault(); e.stopPropagation(); this._dismiss(hotkeyMap[key]); }
            }
        }
    }
}

function normalizeSearchText(text) {
    const value = String(text ?? "");
    if (typeof value.normalize === "function") {
        return value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    }
    return value.toLowerCase();
}

class TurboVisionScrollbar {
    constructor(frame) {
        this.frame = frame;
        this.host = frame.closest(".tv-client-row") || frame.parentElement;
        this.viewport = frame.querySelector("[data-tv-viewport]");
        this.axes = {
            x: this.buildAxis("x"),
            y: this.buildAxis("y"),
        };
        this.resizeObserver = null;
        this.dragState = null;
        this.repeatTimer = null;
        this.bind();
        this.update();
    }

    buildAxis(axis) {
        const root = this.host.querySelector(`.tv-scrollbar-${axis}`);
        return {
            axis,
            root,
            track: root.querySelector("[data-role='track']"),
            cells: root.querySelector("[data-role='cells']"),
            thumb: root.querySelector("[data-role='thumb']"),
            backward: root.querySelector("[data-role='backward']"),
            forward: root.querySelector("[data-role='forward']"),
        };
    }

    bind() {
        this.viewport.addEventListener("scroll", () => this.update(), { passive: true });
        window.addEventListener("resize", () => this.update(), { passive: true });

        for (const axis of Object.values(this.axes)) {
            axis.backward.addEventListener("mousedown", (event) => this.startRepeat(event, axis.axis, -1));
            axis.forward.addEventListener("mousedown", (event) => this.startRepeat(event, axis.axis, 1));
            axis.track.addEventListener("mousedown", (event) => this.onTrackMouseDown(event, axis.axis));
            axis.thumb.addEventListener("mousedown", (event) => this.onThumbMouseDown(event, axis.axis));
        }

        document.addEventListener("mouseup", () => this.stopRepeat(), { passive: true });

        if ("ResizeObserver" in window) {
            this.resizeObserver = new ResizeObserver(() => this.update());
            this.resizeObserver.observe(this.viewport);
            if (this.viewport.firstElementChild) {
                this.resizeObserver.observe(this.viewport.firstElementChild);
            }
        }
    }

    startRepeat(event, axis, direction) {
        event.preventDefault();
        this.scrollStep(axis, direction);
        this.stopRepeat();
        this.repeatTimer = window.setInterval(() => this.scrollStep(axis, direction), SCROLL_REPEAT_MS);
    }

    stopRepeat() {
        if (this.repeatTimer !== null) {
            window.clearInterval(this.repeatTimer);
            this.repeatTimer = null;
        }
    }

    scrollStep(axis, direction) {
        const step = axis === "y" ? this.lineHeight() : this.charWidth() * 2;
        if (axis === "y") {
            this.viewport.scrollTop += direction * step;
        } else {
            this.viewport.scrollLeft += direction * step;
        }
        this.update();
    }

    lineHeight() {
        return measureCells().height;
    }

    charWidth() {
        return measureCells().width;
    }

    onTrackMouseDown(event, axis) {
        if (event.target.closest("[data-role='thumb']")) {
            return;
        }
        event.preventDefault();
        const details = this.axisMetrics(axis);
        if (details.maxScroll <= 0 || details.trackSize <= 0) {
            return;
        }

        const coordinate = axis === "y" ? event.clientY : event.clientX;
        const rect = details.track.getBoundingClientRect();
        const relative = (axis === "y" ? coordinate - rect.top : coordinate - rect.left) - details.thumbPx / 2;
        const ratio = details.freeTrackPx > 0 ? this.clamp(relative / details.freeTrackPx, 0, 1) : 0;
        this.setScrollPosition(axis, ratio * details.maxScroll);
    }

    onThumbMouseDown(event, axis) {
        event.preventDefault();
        const metrics = this.axisMetrics(axis);
        this.dragState = {
            axis,
            startClient: axis === "y" ? event.clientY : event.clientX,
            startScroll: axis === "y" ? this.viewport.scrollTop : this.viewport.scrollLeft,
            maxScroll: metrics.maxScroll,
            freeTrackPx: metrics.freeTrackPx,
        };
        document.addEventListener("mousemove", this.onDragMove);
        document.addEventListener("mouseup", this.onDragEnd);
    }

    onDragMove = (event) => {
        if (!this.dragState) {
            return;
        }
        const client = this.dragState.axis === "y" ? event.clientY : event.clientX;
        const delta = client - this.dragState.startClient;
        const scrollDelta = this.dragState.freeTrackPx > 0
            ? (delta / this.dragState.freeTrackPx) * this.dragState.maxScroll
            : 0;
        this.setScrollPosition(this.dragState.axis, this.dragState.startScroll + scrollDelta);
    };

    onDragEnd = () => {
        this.dragState = null;
        document.removeEventListener("mousemove", this.onDragMove);
        document.removeEventListener("mouseup", this.onDragEnd);
        this.stopRepeat();
    };

    setScrollPosition(axis, value) {
        if (axis === "y") {
            this.viewport.scrollTop = value;
        } else {
            this.viewport.scrollLeft = value;
        }
        this.update();
    }

    axisMetrics(axisName) {
        const axis = this.axes[axisName];
        const vertical = axisName === "y";
        const viewportSize = vertical ? this.viewport.clientHeight : this.viewport.clientWidth;
        const scrollSize = vertical ? this.viewport.scrollHeight : this.viewport.scrollWidth;
        const maxScroll = Math.max(scrollSize - viewportSize, 0);
        const cellSize = vertical ? this.lineHeight() : this.charWidth();
        const trackSize = vertical ? axis.track.clientHeight : axis.track.clientWidth;
        const cellCount = Math.max(1, Math.floor(trackSize / cellSize));
        const thumbCells = maxScroll > 0 ? 1 : 0;
        const freeTrackCells = Math.max(cellCount - thumbCells, 0);
        const freeTrackPx = freeTrackCells * cellSize;
        const thumbPx = thumbCells * cellSize;
        const scrollOffset = vertical ? this.viewport.scrollTop : this.viewport.scrollLeft;
        return {
            axis,
            vertical,
            viewportSize,
            scrollSize,
            maxScroll,
            cellSize,
            trackSize,
            cellCount,
            thumbCells,
            freeTrackCells,
            freeTrackPx,
            thumbPx,
            scrollOffset,
        };
    }

    updateTrackGlyphs(metrics) {
        const { axis, cellCount, thumbCells, freeTrackCells, maxScroll, scrollOffset } = metrics;
        const ratio = maxScroll > 0 ? scrollOffset / maxScroll : 0;
        const thumbStart = Math.round(freeTrackCells * ratio);
        const trackChar = maxScroll > 0 ? TRACK_CHAR : DISABLED_TRACK_CHAR;

        axis.cells.textContent = "";
        axis.thumb.textContent = "";

        if (metrics.vertical) {
            axis.cells.style.gridTemplateRows = `repeat(${cellCount}, 1em)`;
            axis.cells.style.gridTemplateColumns = "1ch";
            axis.thumb.style.gridTemplateRows = `repeat(${thumbCells}, 1em)`;
            axis.thumb.style.gridTemplateColumns = "1ch";
            axis.thumb.style.transform = `translateY(${thumbStart * metrics.cellSize}px)`;
        } else {
            axis.cells.style.gridTemplateColumns = `repeat(${cellCount}, 1ch)`;
            axis.cells.style.gridTemplateRows = "1em";
            axis.thumb.style.gridTemplateColumns = `repeat(${thumbCells}, 1ch)`;
            axis.thumb.style.gridTemplateRows = "1em";
            axis.thumb.style.transform = `translateX(${thumbStart * metrics.cellSize}px)`;
        }

        for (let index = 0; index < cellCount; index += 1) {
            const cell = document.createElement("span");
            cell.className = "tv-scroll-cell";
            cell.textContent = trackChar;
            axis.cells.appendChild(cell);
        }

        for (let index = 0; index < thumbCells; index += 1) {
            const cell = document.createElement("span");
            cell.className = "tv-thumb-cell";
            cell.textContent = THUMB_CHAR;
            axis.thumb.appendChild(cell);
        }

        axis.root.classList.toggle("is-disabled", maxScroll <= 0);
        if (thumbCells > 0) {
            axis.thumb.style.display = "grid";
        } else {
            axis.thumb.style.display = "none";
        }
    }

    updateAxis(axisName) {
        this.updateTrackGlyphs(this.axisMetrics(axisName));
    }

    update() {
        this.updateAxis("x");
        this.updateAxis("y");
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }
}

Object.assign(TV, {
    SCROLL_REPEAT_MS,
    TRACK_CHAR,
    DISABLED_TRACK_CHAR,
    THUMB_CHAR,
    MONTH_NAMES,
    DAYS_IN_MONTH,
    PUZZLE_START,
    PUZZLE_HIGHLIGHT_MAP,
    DOS_COLORS,
    THEME_PRESETS,
    DEFAULT_UI_CONFIG,
    COLOR_GROUPS,
    buildDefaultColorPalette,
    buildPaletteFromCurrentStyle,
    readStoredColorPalette,
    applyColorPalette,
    clearStoredColorPalette,
    readStoredThemePreset,
    applyThemePreset,
    applyThemeAndSyncPalette,
    cloneColorPalette,
    dosColor,
    isLeapYear,
    dayOfWeek,
    measureCells,
    fillBorders,
    fillDesktopPatterns,
    updateClocks,
    escapeHtml,
    renderHotkeyMarkup,
    displayCp437Char,
    bindCloseButtons,
    normalizeSearchText,
    updateWindowFrameState,
    resetMenuPopupLayout,
    fitMenuPopupToViewport,
    TVAppContext,
    TVWidget,
    TVStaticText,
    TVLabel,
    TVInputLine,
    TVListViewer,
    TVGroup,
    TVInfoBox,
    TVListBox,
    TVVerticalListViewer,
    TVVerticalScrollArea,
    TVMenuBox,
    TVButtonStrip,
    TVCheckBoxes,
    TVRadioButtons,
    TVButton,
    TVFrame,
    TVDialog,
    TVMessageBox,
    TVDialogManager,
    TurboVisionScrollbar,
});
TV.getActiveThemePreset = () => activeThemePreset;
TV.getActiveColorPalette = () => activeColorPalette;
TV.setActiveColorPalette = (value) => { activeColorPalette = value; };

// Global button press animation via JS class (CSS :active unreliable on re-click)
document.addEventListener("mousedown", (event) => {
    const btn = event.target.closest(".tv-dialog-button");
    if (!btn) { return; }
    btn.classList.add("is-pressed");
    const release = () => {
        btn.classList.remove("is-pressed");
    };
    document.addEventListener("mouseup", release, { once: true });
    btn.addEventListener("mouseleave", release, { once: true });
});

})();
