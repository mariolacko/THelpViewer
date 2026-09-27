// Turbo Vision core utilities and widgets for generated help pages.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};

const SCROLL_REPEAT_MS = 75;
const TRACK_CHAR = "\u2592";
const DISABLED_TRACK_CHAR = "\u2593";
const THUMB_CHAR = "\u25A0";
const CLOSE_PRESSED_CHAR = "\u204e";
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
            "--tv-calc-display-fg": "#ffffff",
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
            "--tv-puzzle-pane": "#00aaaa",
            "--tv-puzzle-normal": "#000000",
            "--tv-puzzle-highlight": "#ffffff",
            "--tv-calendar-pane": "#00aaaa",
            "--tv-calendar-normal": "#000000",
            "--tv-calendar-current": "#ffffff",
            "--tv-ascii-pane": "#aaaaaa",
            "--tv-ascii-text": "#000000",
            "--tv-calc-display-bg": "#0000aa",
            "--tv-calc-display-fg": "#ffffff",
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
            "--tv-puzzle-pane": "#aa5500",
            "--tv-puzzle-normal": "#000000",
            "--tv-puzzle-highlight": "#ffff55",
            "--tv-calendar-pane": "#aa5500",
            "--tv-calendar-normal": "#000000",
            "--tv-calendar-current": "#ffff55",
            "--tv-ascii-pane": "#552200",
            "--tv-ascii-text": "#ffff55",
            "--tv-calc-display-bg": "#552200",
            "--tv-calc-display-fg": "#ffffff",
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
const DEFAULT_UI_CONFIG = Object.freeze({
    menu: {
        popup: [
            { type: "context-help", label: "~C~ontext Help" },
            { type: "separator" },
            { type: "dialog", dialog: "about", label: "~A~bout" },
            { type: "dialog", dialog: "puzzle", label: "~P~uzzle" },
            { type: "dialog", dialog: "hanoi", label: "Tower of ~H~anoi" },
            { type: "dialog", dialog: "tron", label: "Tr~o~n Light Cycles" },
            { type: "dialog", dialog: "calendar", label: "Ca~l~endar" },
            { type: "dialog", dialog: "ascii", label: "Ascii ~T~able" },
            { type: "dialog", dialog: "calc", label: "~C~alculator" },
            { type: "dialog", dialog: "midi", label: "~M~IDI Player" },
            { type: "dialog", dialog: "colors", label: "C~o~lors" },
            { type: "dialog", dialog: "widgets", label: "~W~idget Gallery" },
            { type: "dialog", dialog: "systeminfo", label: "System ~I~nformation" },
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
        { type: "context-help", label: "~F1~ Help" },
        { type: "dialog", dialog: "search", label: "~F3~ Search" },
        { type: "hint" },
        { type: "link", href: "https://github.com/mariolacko/THelpViewer", label: "GitHub" },
    ],
});
// Borland Turbo Vision 2.0 cpAppColor. Palette indexes are 1-based.
const TV2_APP_COLOR_ATTRIBUTES = Object.freeze([
    0x71, 0x70, 0x78, 0x74, 0x20, 0x28, 0x24, 0x17, 0x1F, 0x1A, 0x31, 0x31, 0x1E, 0x71, 0x1F,
    0x37, 0x3F, 0x3A, 0x13, 0x13, 0x3E, 0x21, 0x3F, 0x70, 0x7F, 0x7A, 0x13, 0x13, 0x70, 0x7F, 0x7E,
    0x70, 0x7F, 0x7A, 0x13, 0x13, 0x70, 0x70, 0x7F, 0x7E, 0x20, 0x2B, 0x2F, 0x78, 0x2E, 0x70, 0x30,
    0x3F, 0x3E, 0x1F, 0x2F, 0x1A, 0x20, 0x72, 0x31, 0x31, 0x30, 0x2F, 0x3E, 0x31, 0x13, 0x38, 0x00,
    0x17, 0x1F, 0x1A, 0x71, 0x71, 0x1E, 0x17, 0x1F, 0x1E, 0x20, 0x2B, 0x2F, 0x78, 0x2E, 0x10, 0x30,
    0x3F, 0x3E, 0x70, 0x2F, 0x7A, 0x20, 0x12, 0x31, 0x31, 0x30, 0x2F, 0x3E, 0x31, 0x13, 0x38, 0x00,
    0x37, 0x3F, 0x3A, 0x13, 0x13, 0x3E, 0x30, 0x3F, 0x3E, 0x20, 0x2B, 0x2F, 0x78, 0x2E, 0x30, 0x70,
    0x7F, 0x7E, 0x1F, 0x2F, 0x1A, 0x20, 0x32, 0x31, 0x71, 0x70, 0x2F, 0x7E, 0x71, 0x13, 0x78, 0x00,
    0x37, 0x3F, 0x3A, 0x13, 0x13, 0x30, 0x3E, 0x1E,
]);

const TV2_PALETTE_TOKENS = Object.freeze({
    1: "desktop",
    2: "menu-normal", 3: "menu-disabled", 4: "menu-shortcut",
    5: "menu-selected", 6: "menu-selected-disabled", 7: "menu-selected-shortcut",
    8: "viewer-frame-passive", 9: "viewer-frame-active", 10: "viewer-frame-icons",
    11: "viewer-scroll-page", 12: "viewer-scroll-controls", 13: "viewer-text", 14: "viewer-highlight",
    16: "calendar-frame-passive", 17: "calendar-frame-active", 18: "calendar-frame-icons",
    19: "calendar-scroll-page", 20: "calendar-scroll-controls", 21: "calendar-text", 22: "calendar-current",
    24: "ascii-frame-passive", 25: "ascii-frame-active", 26: "ascii-frame-icons",
    27: "ascii-scroll-page", 28: "ascii-scroll-controls", 29: "ascii-text",
    32: "dialog-frame-passive", 33: "dialog-frame-active", 34: "dialog-frame-icons",
    35: "dialog-scroll-page", 36: "dialog-scroll-controls", 37: "dialog-static",
    38: "dialog-label-normal", 39: "dialog-label-selected", 40: "dialog-label-shortcut",
    41: "dialog-button-normal", 42: "dialog-button-default", 43: "dialog-button-selected",
    44: "dialog-button-disabled", 45: "dialog-button-shortcut", 46: "dialog-button-shadow",
    47: "dialog-cluster-normal", 48: "dialog-cluster-selected", 49: "dialog-cluster-shortcut",
    50: "dialog-input-normal", 51: "dialog-input-selected", 52: "dialog-input-arrow",
    53: "dialog-history-button", 54: "dialog-history-sides", 55: "dialog-history-page",
    56: "dialog-history-controls", 57: "dialog-list-normal", 58: "dialog-list-focused",
    59: "dialog-list-selected", 60: "dialog-list-divider", 61: "dialog-info",
    62: "dialog-cluster-disabled",
    128: "help-frame-passive", 129: "help-frame-active", 130: "help-frame-icons",
    131: "help-scroll-page", 132: "help-scroll-controls", 133: "help-text",
    134: "help-keyword", 135: "help-keyword-selected",
});

function paletteVariables(paletteIndex) {
    const token = TV2_PALETTE_TOKENS[paletteIndex];
    return token ? {
        bg: [`--tv-palette-${token}-bg`],
        fg: [`--tv-palette-${token}-fg`],
    } : { bg: [], fg: [] };
}

const COLOR_GROUP_DEFINITIONS = Object.freeze([
    { name: "Desktop", items: [["Color", 1]] },
    { name: "Menus", items: [
        ["Normal", 2], ["Disabled", 3], ["Shortcut", 4], ["Selected", 5],
        ["Selected disabled", 6], ["Shortcut selected", 7],
    ] },
    { name: "Dialogs/Calc", items: [
        ["Frame/background", 33], ["Frame icons", 34], ["Scroll bar page", 35], ["Scroll bar icons", 36],
        ["Static text", 37], ["Label normal", 38], ["Label selected", 39], ["Label shortcut", 40],
        ["Button normal", 41], ["Button default", 42], ["Button selected", 43], ["Button disabled", 44],
        ["Button shortcut", 45], ["Button shadow", 46], ["Cluster normal", 47], ["Cluster selected", 48],
        ["Cluster shortcut", 49], ["Input normal", 50], ["Input selected", 51], ["Input arrow", 52],
        ["History button", 53], ["History sides", 54], ["History bar page", 55], ["History bar icons", 56],
        ["List normal", 57], ["List focused", 58], ["List selected", 59], ["List divider", 60],
        ["Information pane", 61], ["Cluster disabled", 62],
    ] },
    { name: "Viewer", items: [
        ["Frame passive", 8], ["Frame active", 9], ["Frame icons", 10],
        ["Scroll bar page", 11], ["Scroll bar icons", 12], ["Text", 13],
    ] },
    { name: "Puzzle", items: [
        ["Frame passive", 8], ["Frame active", 9], ["Frame icons", 10],
        ["Scroll bar page", 11], ["Scroll bar icons", 12], ["Normal text", 13], ["Highlighted text", 14],
    ] },
    { name: "Calendar", items: [
        ["Frame passive", 16], ["Frame active", 17], ["Frame icons", 18],
        ["Scroll bar page", 19], ["Scroll bar icons", 20], ["Normal text", 21], ["Current day", 22],
    ] },
    { name: "Ascii table", items: [
        ["Frame passive", 24], ["Frame active", 25], ["Frame icons", 26],
        ["Scroll bar page", 27], ["Scroll bar icons", 28], ["Text", 29],
    ] },
]);

const COLOR_GROUPS = COLOR_GROUP_DEFINITIONS.map((group) => ({
    name: group.name,
    items: group.items.map(([name]) => name),
}));
const EDITABLE_PALETTE_INDEXES = [...new Set(
    COLOR_GROUP_DEFINITIONS.flatMap((group) => group.items.map(([, paletteIndex]) => paletteIndex))
)];
const COLOR_PALETTE_VARIABLE_KEYS = EDITABLE_PALETTE_INDEXES.flatMap((paletteIndex) => {
    const variables = paletteVariables(paletteIndex);
    return [...variables.bg, ...variables.fg];
});
const THEME_PALETTE_TARGETS = Object.freeze({
    "--tv-desktop": ["--tv-palette-desktop-bg"],
    "--tv-desktop-dot": ["--tv-palette-desktop-fg"],
    "--tv-appbar-bg": ["--tv-palette-menu-normal-bg"],
    "--tv-appbar-text": ["--tv-palette-menu-normal-fg"],
    "--tv-appbar-hotkey": ["--tv-palette-menu-shortcut-fg"],
    "--tv-appbar-active-bg": ["--tv-palette-menu-selected-bg"],
    "--tv-appbar-active-text": ["--tv-palette-menu-selected-fg"],
    "--tv-appbar-active-hotkey": ["--tv-palette-menu-selected-shortcut-fg"],
    "--tv-help-pane": ["--tv-palette-help-text-bg"],
    "--tv-window": ["--tv-palette-help-text-bg"],
    "--tv-puzzle-pane": ["--tv-palette-viewer-text-bg"],
    "--tv-puzzle-normal": ["--tv-palette-viewer-text-fg"],
    "--tv-puzzle-highlight": ["--tv-palette-viewer-highlight-fg"],
    "--tv-calendar-pane": ["--tv-palette-calendar-text-bg"],
    "--tv-calendar-normal": ["--tv-palette-calendar-text-fg"],
    "--tv-calendar-current": ["--tv-palette-calendar-current-fg"],
    "--tv-ascii-pane": ["--tv-palette-ascii-text-bg"],
    "--tv-ascii-text": ["--tv-palette-ascii-text-fg"],
    "--tv-title": ["--tv-palette-help-frame-active-bg"],
    "--tv-title-text": ["--tv-palette-help-frame-active-fg"],
    "--tv-icon": ["--tv-palette-help-frame-icons-fg"],
    "--tv-frame-passive": ["--tv-palette-help-frame-passive-fg"],
    "--tv-title-passive": ["--tv-palette-help-frame-passive-bg"],
    "--tv-title-text-passive": ["--tv-palette-help-frame-passive-fg"],
    "--tv-icon-passive": ["--tv-palette-help-frame-passive-fg"],
    "--tv-text": ["--tv-palette-help-text-fg"],
    "--tv-link": ["--tv-palette-help-keyword-fg"],
    "--tv-hover-bg": ["--tv-palette-help-keyword-selected-bg"],
    "--tv-hover-fg": ["--tv-palette-help-keyword-selected-fg"],
    "--tv-page-area": ["--tv-palette-help-scroll-page-bg"],
    "--tv-scroll-glyph": ["--tv-palette-help-scroll-page-fg"],
    "--tv-arrow-bg": ["--tv-palette-help-scroll-controls-bg"],
    "--tv-arrow-fg": ["--tv-palette-help-scroll-controls-fg"],
    "--tv-thumb-fg": ["--tv-palette-help-scroll-controls-fg"],
    "--tv-frame-line": ["--tv-palette-help-frame-active-fg"],
    "--tv-dialog-bg": ["--tv-palette-dialog-frame-active-bg"],
    "--tv-dialog-fg": ["--tv-palette-dialog-static-fg"],
    "--tv-dialog-frame": ["--tv-palette-dialog-frame-active-fg"],
    "--tv-dialog-title": ["--tv-palette-dialog-frame-active-fg"],
    "--tv-dialog-icon": ["--tv-palette-dialog-frame-icons-fg"],
    "--tv-dialog-frame-passive": ["--tv-palette-dialog-frame-passive-fg"],
    "--tv-dialog-title-passive": ["--tv-palette-dialog-frame-passive-bg"],
    "--tv-dialog-title-text-passive": ["--tv-palette-dialog-frame-passive-fg"],
    "--tv-dialog-icon-passive": ["--tv-palette-dialog-frame-passive-fg"],
    "--tv-dialog-input-bg": ["--tv-palette-dialog-input-normal-bg"],
    "--tv-dialog-input-fg": ["--tv-palette-dialog-input-normal-fg"],
    "--tv-dialog-button-face": ["--tv-palette-dialog-button-normal-bg"],
    "--tv-dialog-button-fg": ["--tv-palette-dialog-button-normal-fg"],
    "--tv-dialog-button-disabled": ["--tv-palette-dialog-button-disabled-fg"],
    "--tv-dialog-button-shadow-bg": ["--tv-palette-dialog-button-shadow-bg"],
    "--tv-dialog-button-shadow-fg": ["--tv-palette-dialog-button-shadow-fg"],
    "--tv-dialog-button-edge-bg": ["--tv-palette-dialog-button-shadow-bg"],
    "--tv-dialog-button-edge-fg": ["--tv-palette-dialog-button-shadow-fg"],
});
function themeVariableTargets(key) {
    return THEME_PALETTE_TARGETS[key] || [key];
}
const THEME_VARIABLE_KEYS = [...new Set(
    Object.values(THEME_PRESETS).flatMap((preset) => (
        Object.keys(preset.vars).flatMap(themeVariableTargets)
    ))
)];
let activeThemePreset = "default";
let activeColorPalette = null;
let measuredCell = null;
const HOST_WINDOW_TOKEN = "__host__";
const TV_COMMANDS = Object.freeze({
    MENU: "menu",
    CLOSE: "close",
    ZOOM: "zoom",
    RESIZE: "resize",
    NEXT: "next",
    PREVIOUS: "previous",
    OK: "ok",
    CANCEL: "cancel",
    DEFAULT: "default",
});
const TV_HELP_CONTEXTS = Object.freeze({
    hcNoContext: 0,
    hcDragging: 1,
    hcApplication: 1000,
    hcSystemMenu: 1100,
    hcHelpFiles: 1200,
    hcDocuments: 1300,
    hcSearch: 1400,
    hcGames: 1500,
    hcWindows: 1600,
    hcContextHelp: 1700,
    hcAbout: 2000,
    hcFileOpen: 2010,
    hcChangeDirectory: 2020,
    hcFind: 2030,
    hcColors: 2040,
    hcWidgetGallery: 2050,
    hcMidiPlayer: 2060,
    hcHelpViewer: 2070,
    hcDocumentViewer: 2080,
    hcDialog: 2090,
    hcCalendar: 2100,
    hcAsciiTable: 2110,
    hcCalculator: 2120,
    hcScreenSaver: 2130,
    hcPuzzle: 2140,
    hcTetris: 2150,
    hcMines: 2160,
    hcBreakOut: 2170,
    hcSokoban: 2180,
    hcLines: 2190,
    hcReversi: 2200,
    hcLudo: 2210,
    hcMastermind: 2220,
    hcSnake: 2230,
    hcHanoi: 2240,
    hcTron: 2250,
    hcStatistics: 2260,
    hcSystemInformation: 2270,
});
const {
    hcNoContext,
    hcApplication,
    hcDialog,
} = TV_HELP_CONTEXTS;

function normalizeHelpContext(value, fallback = hcNoContext) {
    const context = Number(value);
    return Number.isInteger(context) && context >= hcNoContext ? context : fallback;
}

function elementHelpContext(element) {
    let current = element && typeof element.hasAttribute === "function" ? element : null;
    while (current) {
        if (current.hasAttribute("data-tv-help-ctx")) {
            const context = normalizeHelpContext(current.getAttribute("data-tv-help-ctx"));
            if (context !== hcNoContext) { return context; }
        }
        current = current.parentElement;
    }
    return hcNoContext;
}

function setElementHelpContext(element, helpCtx) {
    if (!element) { return; }
    const context = normalizeHelpContext(helpCtx);
    if (context === hcNoContext) {
        element.removeAttribute?.("data-tv-help-ctx");
    } else if (typeof element.setAttribute === "function") {
        element.setAttribute("data-tv-help-ctx", String(context));
    }
}

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
            paletteIndex: item.paletteIndex,
            attr: item.attr,
            bg: item.bg ? [...item.bg] : [],
            fg: item.fg ? [...item.fg] : [],
        })),
    }));
}

function buildDefaultColorPalette() {
    return COLOR_GROUP_DEFINITIONS.map((group) => ({
        name: group.name,
        index: 0,
        items: group.items.map(([name, paletteIndex]) => {
            const variables = paletteVariables(paletteIndex);
            return {
                name,
                key: colorItemKey(group.name, name),
                paletteIndex,
                attr: TV2_APP_COLOR_ATTRIBUTES[paletteIndex - 1] ?? 0x70,
                bg: [...variables.bg],
                fg: [...variables.fg],
            };
        }),
    }));
}

function setColorPaletteAttribute(palette, paletteIndex, attr) {
    if (!Number.isInteger(paletteIndex) || !Number.isInteger(attr) || attr < 0 || attr > 0xFF) {
        return false;
    }
    let changed = false;
    palette.forEach((group) => {
        group.items.forEach((item) => {
            if (item.paletteIndex === paletteIndex) {
                item.attr = attr;
                changed = true;
            }
        });
    });
    return changed;
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
    const restoredAttributes = new Map();
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
                const targetItem = targetGroup.items[itemIndex];
                if (
                    targetItem
                    && Number.isInteger(attr)
                    && attr >= 0
                    && attr <= 0xFF
                    && !restoredAttributes.has(targetItem.paletteIndex)
                ) {
                    restoredAttributes.set(targetItem.paletteIndex, attr);
                }
            });
        }
    });
    restoredAttributes.forEach((attr, paletteIndex) => {
        setColorPaletteAttribute(palette, paletteIndex, attr);
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
    const attributes = new Map();
    palette.forEach((group) => {
        group.items.forEach((item) => {
            if (!attributes.has(item.paletteIndex)) {
                attributes.set(item.paletteIndex, item.attr);
            }
        });
    });
    attributes.forEach((attr, paletteIndex) => {
        const variables = paletteVariables(paletteIndex);
        variables.bg.forEach((key) => root.style.setProperty(key, dosColor(attr, 4)));
        variables.fg.forEach((key) => root.style.setProperty(key, dosColor(attr, 0)));
    });
    activeColorPalette = buildDefaultColorPalette();
    attributes.forEach((attr, paletteIndex) => {
        setColorPaletteAttribute(activeColorPalette, paletteIndex, attr);
    });
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
    Object.entries(preset.vars).forEach(([key, value]) => {
        themeVariableTargets(key).forEach((target) => root.style.setProperty(target, value));
    });
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

function initializeTVTheme() {
    document.documentElement.classList.add("tv-js");
    applyThemePreset(readStoredThemePreset(), false);
    const storedPalette = readStoredColorPalette();
    if (storedPalette) {
        applyColorPalette(storedPalette, false);
    } else {
        activeColorPalette = buildPaletteFromCurrentStyle();
    }
    return cloneColorPalette(activeColorPalette);
}

function isLeapYear(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
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

const TV_FRAME_GLYPHS = Object.freeze({
    active: Object.freeze({ horizontal: "═", vertical: "║", topLeft: "╔", topRight: "╗", bottomLeft: "╚", bottomRight: "╝" }),
    passive: Object.freeze({ horizontal: "─", vertical: "│", topLeft: "┌", topRight: "┐", bottomLeft: "└", bottomRight: "┘" }),
    dragging: Object.freeze({ horizontal: "─", vertical: "│", topLeft: "┌", topRight: "┐", bottomLeft: "└", bottomRight: "┘" }),
});

function windowFrameMode(windowElement, active, dialog) {
    const dragging = windowElement.classList.contains("is-resizing")
        || windowElement.classList.contains("is-moving")
        || (dialog && windowElement.classList.contains("is-dragging"));
    return dragging ? "dragging" : (active ? "active" : "passive");
}

function setOwnedWidgetsActive(windowElement, active) {
    const scrollbarWidgets = new Set();
    windowElement.querySelectorAll(".tv-scrollbar").forEach((scrollbar) => {
        if (scrollbar._tvScrollbar) {
            scrollbarWidgets.add(scrollbar._tvScrollbar);
        } else {
            scrollbar.classList.toggle("is-inactive", !active);
            scrollbar.setAttribute("aria-disabled", active ? "false" : "true");
        }
    });
    scrollbarWidgets.forEach((scrollbar) => scrollbar.setActive(active));
    windowElement.querySelectorAll("[data-tv-list-viewer]").forEach((listRoot) => {
        if (listRoot._tvListViewer) {
            listRoot._tvListViewer.setActive(active);
        }
    });
}

function updateWindowFrameState(windowElement, active, { dialog = false } = {}) {
    if (!windowElement) {
        return;
    }
    const frameMode = windowFrameMode(windowElement, active, dialog);
    const glyphs = TV_FRAME_GLYPHS[frameMode];
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
    const zoomButton = windowElement.querySelector("[data-tv-zoom-glyph]")?.closest("button, a");
    const resizeHandle = !dialog ? windowElement.querySelector("[data-tv-resize-handle]") : null;

    setOwnedWidgetsActive(windowElement, active);
    if (closeButton) {
        closeButton.hidden = dialog && !active;
        closeButton.classList.toggle("is-frame-control-passive", !dialog && !active);
        if (!dialog && !active) {
            closeButton.setAttribute("aria-hidden", "true");
            closeButton.setAttribute("aria-disabled", "true");
            closeButton.tabIndex = -1;
        } else {
            closeButton.removeAttribute("aria-hidden");
            closeButton.removeAttribute("aria-disabled");
            closeButton.removeAttribute("tabindex");
        }
    }
    if (zoomButton) {
        zoomButton.hidden = dialog && !active;
        zoomButton.classList.toggle("is-frame-control-passive", !dialog && !active);
        if (!dialog && !active) {
            zoomButton.setAttribute("aria-hidden", "true");
            zoomButton.setAttribute("aria-disabled", "true");
            zoomButton.tabIndex = -1;
        } else {
            zoomButton.removeAttribute("aria-hidden");
            zoomButton.removeAttribute("aria-disabled");
            zoomButton.removeAttribute("tabindex");
        }
    }

    if (topCorners[0]) {
        topCorners[0].textContent = glyphs.topLeft;
    }
    if (topCorners[topCorners.length - 1]) {
        topCorners[topCorners.length - 1].textContent = glyphs.topRight;
    }
    topFills.forEach((element) => setBorderFill(element, glyphs.horizontal));
    sides.forEach((element) => setBorderSide(element, glyphs.vertical));

    if (dialog) {
        if (bottomCorners[0]) {
            bottomCorners[0].textContent = glyphs.bottomLeft;
        }
        if (bottomCorners[bottomCorners.length - 1]) {
            bottomCorners[bottomCorners.length - 1].textContent = glyphs.bottomRight;
        }
        bottomFills.forEach((element) => setBorderFill(element, glyphs.horizontal));

        // Update internal separator T-connectors (e.g. ASCII table ╟/╢)
        const tMap = frameMode === "active"
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
            leftCorner.textContent = glyphs.bottomLeft;
        }
        bottomFills.forEach((element) => setBorderFill(element, glyphs.horizontal));
        if (resizeHandle) {
            // Turbo Vision 2.0 always draws the grow icon as a single-line
            // horizontal stroke plus the lower-right corner (TFrame::dragIcon).
            resizeHandle.textContent = "─┘";
        }
    }

    if (closeGlyph) {
        applyCloseGlyphState(closeButton, closeButton && closeButton.dataset.tvClosePressed === "1");
    }

    fillBorders(windowElement);
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

class TVPoint {
    constructor(x = 0, y = 0) {
        this.x = Number(x) || 0;
        this.y = Number(y) || 0;
    }

    copy() { return new TVPoint(this.x, this.y); }
    equals(other) { return other instanceof TVPoint && this.x === other.x && this.y === other.y; }
    move(deltaX, deltaY) {
        this.x += Number(deltaX) || 0;
        this.y += Number(deltaY) || 0;
        return this;
    }
}

class TVRect {
    constructor(x1 = 0, y1 = 0, x2 = x1, y2 = y1) {
        this.x1 = Number.isFinite(Number(x1)) ? Number(x1) : 0;
        this.y1 = Number.isFinite(Number(y1)) ? Number(y1) : 0;
        this.x2 = Number.isFinite(Number(x2)) ? Number(x2) : this.x1;
        this.y2 = Number.isFinite(Number(y2)) ? Number(y2) : this.y1;
    }

    get width() { return Math.max(0, this.x2 - this.x1); }
    get height() { return Math.max(0, this.y2 - this.y1); }

    copy() { return new TVRect(this.x1, this.y1, this.x2, this.y2); }
    equals(other) {
        return other instanceof TVRect
            && this.x1 === other.x1 && this.y1 === other.y1
            && this.x2 === other.x2 && this.y2 === other.y2;
    }
    contains(x, y) {
        return x >= this.x1 && x < this.x2 && y >= this.y1 && y < this.y2;
    }
    move(deltaX, deltaY) {
        this.x1 += Number(deltaX) || 0;
        this.x2 += Number(deltaX) || 0;
        this.y1 += Number(deltaY) || 0;
        this.y2 += Number(deltaY) || 0;
        return this;
    }
    grow(deltaX, deltaY) {
        this.x1 -= Number(deltaX) || 0;
        this.x2 += Number(deltaX) || 0;
        this.y1 -= Number(deltaY) || 0;
        this.y2 += Number(deltaY) || 0;
        return this;
    }
    intersect(other) {
        if (!(other instanceof TVRect)) { return this; }
        this.x1 = Math.max(this.x1, other.x1);
        this.y1 = Math.max(this.y1, other.y1);
        this.x2 = Math.max(this.x1, Math.min(this.x2, other.x2));
        this.y2 = Math.max(this.y1, Math.min(this.y2, other.y2));
        return this;
    }
    union(other) {
        if (!(other instanceof TVRect)) { return this; }
        this.x1 = Math.min(this.x1, other.x1);
        this.y1 = Math.min(this.y1, other.y1);
        this.x2 = Math.max(this.x2, other.x2);
        this.y2 = Math.max(this.y2, other.y2);
        return this;
    }
}

let tvViewSequence = 0;

const evNothing = 0x0000;
const evMouseDown = 0x0001;
const evMouseUp = 0x0002;
const evMouseMove = 0x0004;
const evMouseAuto = 0x0008;
const evKeyDown = 0x0010;
const evCommand = 0x0100;
const evBroadcast = 0x0200;

// DOS Navigator GAUGE.PAS broadcast commands.
const cmUpdateGauge = 12000;
const cmResetGauge = 12001;
const cmAddGauge = 12002;

// TView state masks (Borland Turbo Vision 2.0 / DOS Navigator views.pas).
const sfVisible = 0x0001;
const sfCursorVis = 0x0002;
const sfCursorIns = 0x0004;
const sfShadow = 0x0008;
const sfActive = 0x0010;
const sfSelected = 0x0020;
const sfFocused = 0x0040;
const sfDragging = 0x0080;
const sfDisabled = 0x0100;
const sfModal = 0x0200;
const sfDefault = 0x0400;
const sfExposed = 0x0800;

// TView option masks.
const ofSelectable = 0x0001;
const ofTopSelect = 0x0002;
const ofFirstClick = 0x0004;
const ofFramed = 0x0008;
const ofPreProcess = 0x0010;
const ofPostProcess = 0x0020;
const ofBuffered = 0x0040;
const ofTileable = 0x0080;
const ofCenterX = 0x0100;
const ofCenterY = 0x0200;
const ofCentered = 0x0300;
const ofValidate = 0x0400;

// TView grow and drag masks.
const gfGrowLoX = 0x01;
const gfGrowLoY = 0x02;
const gfGrowHiX = 0x04;
const gfGrowHiY = 0x08;
const gfGrowAll = 0x0f;
const gfGrowRel = 0x10;
const dmDragMove = 0x01;
const dmDragGrow = 0x02;
const dmLimitLoX = 0x10;
const dmLimitLoY = 0x20;
const dmLimitHiX = 0x40;
const dmLimitHiY = 0x80;
const dmLimitAll = 0xf0;

// TWindow flags and StandardScrollBar options.
const wfMove = 0x01;
const wfGrow = 0x02;
const wfClose = 0x04;
const wfZoom = 0x08;
const wfMaxi = 0x10;
const wnNoNumber = 255;
const sbHorizontal = 0x0000;
const sbVertical = 0x0001;
const sbHandleKeyboard = 0x0002;

// Turbo Vision-compatible key codes used by menu and status descriptors.
const kbNoKey = 0x0000;
const kbCtrlF = 0x0006;
const kbCtrlL = 0x000c;
const kbF1 = 0x3b00;
const kbF3 = 0x3d00;
const kbF5 = 0x3f00;
const kbF6 = 0x4000;
const kbShiftF6 = 0x5900;
const kbAltF3 = 0x6d00;
const kbAlt0 = 0x8100;

function getKeyCode(event) {
    if (!event || event.metaKey) { return kbNoKey; }
    if (event.ctrlKey && !event.altKey && !event.shiftKey && event.key?.length === 1) {
        const code = event.key.toUpperCase().charCodeAt(0);
        return code >= 0x40 && code <= 0x5f ? code - 0x40 : kbNoKey;
    }
    if (event.altKey && !event.ctrlKey && !event.shiftKey) {
        if (event.key === "F3") { return kbAltF3; }
        if (event.key === "0") { return kbAlt0; }
    }
    if (!event.altKey && !event.ctrlKey) {
        if (event.key === "F1" && !event.shiftKey) { return kbF1; }
        if (event.key === "F3" && !event.shiftKey) { return kbF3; }
        if (event.key === "F5" && !event.shiftKey) { return kbF5; }
        if (event.key === "F6") { return event.shiftKey ? kbShiftF6 : kbF6; }
    }
    return kbNoKey;
}

const disabledCommands = new Set();

class TVEvent {
    constructor(what = evNothing, { command = "", infoPtr = null, infoLong = 0, nativeEvent = null } = {}) {
        this.what = what;
        this.command = command;
        this.infoPtr = infoPtr;
        this.infoLong = Number(infoLong) || 0;
        this.nativeEvent = nativeEvent;
    }
}

class TVView {
    constructor(bounds = new TVRect()) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVView expects TVRect bounds");
        }
        this.root = null;
        this.owner = null;
        this.helpCtx = hcNoContext;
        this.bounds = bounds;
        this.origin = new TVPoint(bounds.x1, bounds.y1);
        this.size = new TVPoint(bounds.width, bounds.height);
        this.cursor = new TVPoint();
        this.growMode = 0;
        this.dragMode = dmLimitLoY;
        this.options = 0;
        this.state = sfVisible;
        this.eventMask = evMouseDown | evKeyDown | evCommand;
        this.viewId = `tv-view-${++tvViewSequence}`;
    }

    _drawAttrs(attrs = {}) {
        return {
            "data-tv-view-id": this.viewId,
            ...(this.helpCtx !== hcNoContext ? { "data-tv-help-ctx": this.helpCtx } : {}),
            ...attrs,
        };
    }

    _drawRole() { return String(this.constructor.role || ""); }

    _semanticName() {
        return String(this.constructor.viewName || "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    /** Build inline CSS for character-cell bounds (x, y, w, h). */
    static _boundsStyle(x, y, w, h) {
        const parts = [];
        if (x !== undefined || y !== undefined) { parts.push("position:absolute"); }
        if (x !== undefined) { parts.push(`left:${x}ch`); }
        if (y !== undefined) { parts.push(`top:${y}em`); }
        if (w !== undefined) { parts.push(`width:${w}ch`); }
        if (h !== undefined) { parts.push(`height:${h}em`); }
        return parts.join(";");
    }

    static _viewBoundsStyle(view) {
        const bounds = view?.bounds;
        if (!(bounds instanceof TVRect)) { return ""; }
        if (bounds.x1 === 0 && bounds.y1 === 0 && bounds.x2 === 0 && bounds.y2 === 0) {
            return "";
        }
        return this._boundsStyle(
            bounds.x1,
            bounds.y1,
            bounds.width || undefined,
            bounds.height || undefined,
        );
    }

    static _roleClassNames(role = "") {
        return String(role).split(/\s+/).filter(Boolean).map((name) => (
            name.startsWith("is-") ? name : `tv-${name}`
        )).join(" ");
    }

    static _controlAttrs({
        name = "",
        value = true,
        command = "",
        commandData = {},
        disabled = false,
        hidden = false,
        ariaLabel = "",
        ariaExpanded = null,
        ariaPressed = null,
        ariaHidden = null,
        ariaHasPopup = null,
        tabIndex = null,
        tooltip = "",
        draggable = null,
    } = {}) {
        const attrs = {};
        if (name) { attrs[`data-tv-${name}`] = value; }
        if (command) { attrs["data-tv-command"] = command; }
        Object.entries(commandData).forEach(([key, item]) => {
            const dataName = String(key).replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
            attrs[`data-tv-${dataName}`] = item;
        });
        if (disabled) { attrs.disabled = true; }
        if (hidden) { attrs.hidden = true; }
        if (ariaLabel) { attrs["aria-label"] = ariaLabel; }
        if (ariaExpanded !== null) { attrs["aria-expanded"] = String(ariaExpanded === true || ariaExpanded === "true"); }
        if (ariaPressed !== null) { attrs["aria-pressed"] = String(ariaPressed === true || ariaPressed === "true"); }
        if (ariaHidden !== null) { attrs["aria-hidden"] = String(ariaHidden === true || ariaHidden === "true"); }
        if (ariaHasPopup !== null) { attrs["aria-haspopup"] = String(ariaHasPopup === true || ariaHasPopup === "true"); }
        if (tabIndex !== null) { attrs.tabindex = tabIndex; }
        if (tooltip) { attrs.title = tooltip; }
        if (draggable !== null) { attrs.draggable = String(draggable === true || draggable === "true"); }
        return attrs;
    }

    static _fromHTML(markup) {
        const template = document.createElement("template");
        template.innerHTML = markup.trim();
        return template.content.firstElementChild;
    }

    static _fromElement(element) {
        let current = element?.nodeType === 1 ? element : null;
        while (current) {
            if (current._tvView instanceof TVView) { return current._tvView; }
            current = current.parentElement;
        }
        return null;
    }

    mount(parent) {
        if (this.root && parent) {
            parent.appendChild(this.root);
        }
        return this.root;
    }

    bindRoot(root) {
        if (this.root?._tvView === this) { delete this.root._tvView; }
        this.root = root || null;
        if (this.root) { this.root._tvView = this; }
        setElementHelpContext(this.root, this.helpCtx);
        return this;
    }

    _query(selector) {
        return this.root ? this.root.querySelector(selector) : null;
    }

    _queryAll(selector) {
        return this.root ? Array.from(this.root.querySelectorAll(selector)) : [];
    }

    _setHTML(markup) {
        if (this.root) {
            this.root.innerHTML = markup;
        }
        return this.root;
    }

    setBounds(bounds) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVView.setBounds expects TVRect");
        }
        this.bounds = bounds;
        this.origin.x = bounds.x1;
        this.origin.y = bounds.y1;
        this.size.x = bounds.width;
        this.size.y = bounds.height;
        return this;
    }

    getBounds() { return this.bounds.copy(); }

    getExtent() { return new TVRect(0, 0, this.size.x, this.size.y); }

    locate(bounds) { return this.changeBounds(bounds); }

    moveTo(x, y) {
        return this.changeBounds(new TVRect(
            Number(x) || 0,
            Number(y) || 0,
            (Number(x) || 0) + this.size.x,
            (Number(y) || 0) + this.size.y,
        ));
    }

    setCursor(x, y) {
        this.cursor.x = Number(x) || 0;
        this.cursor.y = Number(y) || 0;
        return this;
    }

    showCursor() { return this.setState(sfCursorVis, true); }
    hideCursor() { return this.setState(sfCursorVis, false); }
    blockCursor() { return this.setState(sfCursorIns, true); }
    normalCursor() { return this.setState(sfCursorIns, false); }

    setState(state, enable) {
        const mask = Number(state) || 0;
        this.state = enable ? (this.state | mask) : (this.state & ~mask);
        if ((mask & sfVisible) !== 0 && this.root) { this.root.hidden = !enable; }
        if ((mask & sfActive) !== 0) { this.root?.classList.toggle("is-active", Boolean(enable)); }
        if ((mask & sfFocused) !== 0) { this.root?.classList.toggle("is-focused", Boolean(enable)); }
        if ((mask & sfSelected) !== 0) { this.root?.classList.toggle("is-selected", Boolean(enable)); }
        if ((mask & sfDisabled) !== 0 && this.root) {
            this.root.classList.toggle("is-disabled", Boolean(enable));
            this.root.setAttribute("aria-disabled", enable ? "true" : "false");
        }
        return this;
    }

    getState(state) {
        return (this.state & state) !== 0;
    }

    show() { return this.setState(sfVisible, true); }
    hide() { return this.setState(sfVisible, false); }
    exposed() { return this.getState(sfVisible) && !this.root?.hidden; }

    focus() {
        this.root?.focus?.();
        return this.setState(sfFocused, true);
    }

    select() {
        this.owner?.setCurrent?.(this);
        return this.setState(sfSelected, true);
    }

    makeFirst() {
        if (this.owner instanceof TVGroup) {
            this.owner.remove(this);
            this.owner.insert(this);
            this.root?.parentElement?.appendChild(this.root);
        }
        return this;
    }

    nextView() {
        if (!(this.owner instanceof TVGroup)) { return null; }
        const index = this.owner.indexOf(this);
        return index < 0 ? null : this.owner.at((index + 1) % this.owner.children.length);
    }

    prevView() {
        if (!(this.owner instanceof TVGroup)) { return null; }
        const index = this.owner.indexOf(this);
        return index < 0 ? null : this.owner.at((index + this.owner.children.length - 1) % this.owner.children.length);
    }

    topView() {
        let view = this;
        while (view.owner) { view = view.owner; }
        return view;
    }

    dataSize() { return 0; }
    getData() { return null; }
    setData(_value) { return this; }
    valid(_command = 0) { return true; }

    calcBounds(bounds, delta) {
        if (!(bounds instanceof TVRect)) { return null; }
        const change = delta instanceof TVPoint ? delta : new TVPoint(delta?.x, delta?.y);
        if ((this.growMode & gfGrowLoX) !== 0) { bounds.x1 += change.x; }
        if ((this.growMode & gfGrowLoY) !== 0) { bounds.y1 += change.y; }
        if ((this.growMode & gfGrowHiX) !== 0) { bounds.x2 += change.x; }
        if ((this.growMode & gfGrowHiY) !== 0) { bounds.y2 += change.y; }
        return bounds;
    }

    commandEnabled(command) { return !disabledCommands.has(command); }

    disableCommands(commands) {
        const values = commands instanceof Set || Array.isArray(commands) ? commands : [commands];
        for (const command of values) { disabledCommands.add(command); }
    }

    enableCommands(commands) {
        const values = commands instanceof Set || Array.isArray(commands) ? commands : [commands];
        for (const command of values) { disabledCommands.delete(command); }
    }

    getCommands() {
        return new Set(Object.values(TV_COMMANDS).filter((command) => !disabledCommands.has(command)));
    }

    setCommands(commands) {
        disabledCommands.clear();
        const enabled = new Set(commands instanceof Set || Array.isArray(commands) ? commands : []);
        Object.values(TV_COMMANDS).forEach((command) => {
            if (!enabled.has(command)) { disabledCommands.add(command); }
        });
    }

    endModal(command) { return this.owner?.endModal?.(command); }
    execute() { return 0; }
    getClipRect() { return this.getExtent(); }
    getColor(color) { return color; }
    getPalette() { return null; }

    makeGlobal(source) {
        const point = source instanceof TVPoint ? source.copy() : new TVPoint(source?.x, source?.y);
        for (let view = this; view; view = view.owner) { point.move(view.origin.x, view.origin.y); }
        return point;
    }

    makeLocal(source) {
        const point = source instanceof TVPoint ? source.copy() : new TVPoint(source?.x, source?.y);
        const chain = [];
        for (let view = this; view; view = view.owner) { chain.push(view); }
        chain.forEach((view) => point.move(-view.origin.x, -view.origin.y));
        return point;
    }

    mouseInView(point) {
        const local = point instanceof TVPoint ? point : new TVPoint(point?.x, point?.y);
        return this.getExtent().contains(local.x, local.y);
    }

    putInFrontOf(target) {
        if (!(this.owner instanceof TVGroup) || target?.owner !== this.owner) { return this; }
        this.owner.remove(this);
        this.owner.insertBefore(this, target);
        target.root?.parentElement?.insertBefore(this.root, target.root);
        return this;
    }

    sizeLimits() {
        return { min: new TVPoint(0, 0), max: new TVPoint(Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER) };
    }

    draw() {
        return "";
    }
    update() { return this.drawView(); }

    drawView() {
        const markup = this.draw();
        if (this.root && typeof markup === "string" && markup.trim()) {
            const replacement = TVView._fromHTML(markup);
            this.root.replaceWith(replacement);
            this.resolve(replacement);
        }
        return this;
    }

    changeBounds(bounds) {
        this.setBounds(bounds);
        if (!this.root) { return this; }
        const positioned = !(bounds.x1 === 0 && bounds.y1 === 0 && bounds.x2 === 0 && bounds.y2 === 0);
        this.root.style.position = positioned ? "absolute" : "";
        this.root.style.left = positioned ? `${bounds.x1}ch` : "";
        this.root.style.top = positioned ? `${bounds.y1}em` : "";
        this.root.style.width = positioned && bounds.width ? `${bounds.width}ch` : "";
        this.root.style.height = positioned && bounds.height ? `${bounds.height}em` : "";
        return this;
    }

    growTo(x, y) {
        return this.changeBounds(new TVRect(
            this.bounds.x1,
            this.bounds.y1,
            this.bounds.x1 + Math.max(0, Number(x) || 0),
            this.bounds.y1 + Math.max(0, Number(y) || 0),
        ));
    }

    resolve(root) {
        if (!root) { return this; }
        if (root.getAttribute?.("data-tv-view-id") === this.viewId) {
            this.bindRoot(root);
        } else {
            this.bindRoot(root.querySelector?.(`[data-tv-view-id="${this.viewId}"]`) || null);
        }
        return this;
    }

    handleEvent(_event) {}

    clearEvent(event) {
        event.what = evNothing;
    }

    dispatchEvent(event) {
        let view = this;
        while (view && event.what !== evNothing) {
            if ((view.eventMask & event.what) !== 0) { view.handleEvent(event); }
            view = view.owner;
        }
        return event;
    }

    setHelpCtx(helpCtx) {
        this.helpCtx = normalizeHelpContext(helpCtx);
        setElementHelpContext(this.root, this.helpCtx);
        return this;
    }

    getHelpCtx() {
        return elementHelpContext(this.root) || this.helpCtx;
    }
}

class TVStaticText extends TVView {
    constructor(bounds, text) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVStaticText expects TVRect bounds");
        }
        super(bounds);
        this.text = String(text ?? "");
    }

    draw() {
        const role = this._drawRole();
        const centered = this.text.charCodeAt(0) === 3;
        const text = centered ? this.text.slice(1) : this.text;
        const cls = [
            "tv-static-text",
            TVView._roleClassNames(role),
        ].filter(Boolean).join(" ");
        const classAttr = ` class="${escapeHtml(cls)}"`;
        const bounds = TVView._viewBoundsStyle(this);
        const alignStyle = centered ? "text-align:center" : "";
        const inlineStyle = [bounds, alignStyle].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const liveNames = new Set(["tron-status", "hanoi-history", "hanoi-status"]);
        const semanticName = this._semanticName();
        const attrString = attrsToString(this._drawAttrs({
            ...(semanticName ? {
                [`data-tv-${semanticName}`]: true,
                "data-tv-row": semanticName,
            } : {}),
            ...(role === "calc-display" || liveNames.has(semanticName) ? { "aria-live": "polite" } : {}),
            ...(semanticName === "ludo-board" ? { role: "grid", "aria-label": "Ludo board" } : {}),
            ...(semanticName === "tron-field" ? { role: "img", "aria-label": "Tron arena" } : {}),
        }));
        const attrs = attrString ? ` ${attrString}` : "";
        return `<div${classAttr}${styleAttr}${attrs}>${escapeHtml(text)}</div>`;
    }

    getText() {
        return this.text;
    }

    setText(text) {
        this.text = String(text ?? "");
        if (this.root) {
            const centered = this.text.charCodeAt(0) === 3;
            this.root.textContent = centered ? this.text.slice(1) : this.text;
            this.root.style.textAlign = centered ? "center" : "";
        }
        return this;
    }

}

class TVPercentGauge extends TVView {
    static viewName = "percent-gauge";

    constructor(bounds, maxValue) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVPercentGauge expects TVRect bounds");
        }
        super(bounds);
        this.eventMask |= evBroadcast;
        this.maxValue = Number(maxValue) || 0;
        this.curValue = 0;
    }

    solveForX(y, z) {
        return Math.trunc((Number(z) || 0) * ((Number(y) || 0) * 0.01));
    }

    solveForY(x, z) {
        const total = Number(z) || 0;
        return total === 0 ? 0 : Math.trunc(((Number(x) || 0) * 100) / total);
    }

    draw() {
        const percentDone = this.solveForY(this.curValue, this.maxValue);
        const text = `${String(percentDone).padEnd(3, " ")}%`;
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const attrs = attrsToString(this._drawAttrs({ "data-tv-percent-gauge": true }));
        return `<div class="tv-gauge tv-percent-gauge"${style} ${attrs}>${escapeHtml(text)}</div>`;
    }

    updateView(progress) {
        this.curValue = Number(progress) || 0;
        this.drawView();
        return this;
    }

    addProgress(progress) {
        return this.updateView(this.curValue + (Number(progress) || 0));
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evBroadcast) { return; }
        if (event.command === cmUpdateGauge) {
            this.updateView(event.infoLong);
        } else if (event.command === cmResetGauge) {
            this.maxValue = event.infoLong;
            this.updateView(0);
        } else if (event.command === cmAddGauge) {
            this.addProgress(event.infoLong);
        }
    }
}

class TVBarGauge extends TVPercentGauge {
    static viewName = "bar-gauge";

    draw() {
        const width = Math.max(0, this.size.x);
        const percentDone = this.solveForY(this.curValue, this.maxValue);
        const fillSize = Math.min(width, Math.max(0, this.solveForX(percentDone, width)));
        const text = "▓".repeat(fillSize) + "░".repeat(width - fillSize);
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const attrs = attrsToString(this._drawAttrs({ "data-tv-bar-gauge": true }));
        return `<div class="tv-gauge tv-bar-gauge"${style} ${attrs}>${escapeHtml(text)}</div>`;
    }
}

class TVLabel extends TVStaticText {
    constructor(bounds, text, link = null) {
        super(bounds, text);
        this.link = link instanceof TVView ? link : null;
    }

    draw() {
        const tag = this.link ? "label" : "span";
        const cls = ["tv-static-text", "tv-label", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const bounds = TVView._viewBoundsStyle(this);
        const styleAttr = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const forAttr = this.link ? ` for="${escapeHtml(this.link.viewId)}"` : "";
        const attrs = attrsToString(this._drawAttrs());
        const content = renderHotkeyMarkup(this.text);
        return `<${tag} class="${escapeHtml(cls)}"${styleAttr}${forAttr} ${attrs}>${content}</${tag}>`;
    }
}

class TVInputLine extends TVView {
    constructor(bounds, maxLen = 255) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVInputLine expects TVRect bounds");
        }
        super(bounds);
        this.maxLen = Math.max(1, Number(maxLen) || 255);
        this.data = "";
        this.disabled = false;
    }

    setData(value) {
        this.data = String(value ?? "").slice(0, this.maxLen);
        if (this.root) { this.root.value = this.data; }
        return this;
    }

    getData() {
        return this.root ? this.root.value : this.data;
    }

    focus() {
        this.root?.focus();
        return this;
    }

    selectAll(enable = true) {
        if (enable) {
            this.root?.select();
        } else if (this.root) {
            const end = this.root.selectionEnd ?? this.root.value.length;
            this.root.setSelectionRange(end, end);
        }
        return this;
    }

    setState(state, enable) {
        if ((state & sfDisabled) !== 0) {
            this.disabled = Boolean(enable);
            if (this.root) { this.root.disabled = this.disabled; }
        }
        return super.setState(state, enable);
    }

    draw() {
        const viewName = this._semanticName();
        const attrString = attrsToString(this._drawAttrs({
            type: "text",
            id: this.viewId,
            maxlength: this.maxLen,
            value: this.data,
            disabled: this.disabled,
            autocomplete: "off",
            spellcheck: false,
            ...(viewName ? { [`data-tv-${viewName}`]: true } : {}),
        }));
        const cls = ["tv-input-line", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const bounds = TVView._viewBoundsStyle(this);
        const styleAttr = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        return `<input class="${escapeHtml(cls)}"${styleAttr} ${attrString}>`;
    }

    resolve(root) {
        super.resolve(root);
        if (this.root) {
            this.root.value = this.data;
            this.root.disabled = this.disabled;
        }
        return this;
    }
}

class TVGroup extends TVView {
    constructor(bounds = new TVRect()) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVGroup expects TVRect bounds");
        }
        super(bounds);
        this.children = [];
        this.current = null;
        this.lockFlag = 0;
        this.endState = 0;
        this.eventMask |= evBroadcast;
    }

    /** True if any child has absolute positioning (x or y). */
    _hasPositionedChildren() {
        return this.children.some((child) =>
            child instanceof TVView && (child.bounds.x1 !== 0 || child.bounds.y1 !== 0)
        );
    }

    renderChildren() {
        return this.children.map((child) => {
            if (child && typeof child.draw === "function") {
                return child.draw();
            }
            return "";
        }).join("");
    }

    draw() {
        const cls = ["tv-group", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const bounds = TVView._viewBoundsStyle(this);
        const positioned = this._hasPositionedChildren()
            ? `${bounds ? "" : "position:relative;"}display:block`
            : "";
        const parts = [
            bounds,
            positioned,
        ].filter(Boolean).join(";");
        const styleAttr = parts ? ` style="${escapeHtml(parts)}"` : "";
        const viewName = this._semanticName();
        const attrString = attrsToString(this._drawAttrs({
            ...(viewName ? { [`data-tv-${viewName}`]: this.value ?? true } : {}),
            hidden: !this.getState(sfVisible),
        }));
        const attrs = attrString ? ` ${attrString}` : "";
        return `<div class="${escapeHtml(cls)}"${styleAttr}${attrs}>${this.renderChildren()}</div>`;
    }

    setCurrent(child) {
        const next = this.children.includes(child) ? child : null;
        if (this.current && this.current !== next) {
            this.current.setState(sfSelected | sfFocused, false);
        }
        this.current = next;
        if (next) { next.setState(sfSelected, true); }
        return this.current;
    }

    setState(state, enable) {
        super.setState(state, enable);
        if ((state & (sfActive | sfDragging)) !== 0) {
            this.children.forEach((child) => child.setState(state, enable));
        } else if ((state & sfFocused) !== 0) {
            this.current?.setState(sfFocused, enable);
        } else if ((state & sfExposed) !== 0) {
            this.children.forEach((child) => {
                if (child.getState(sfVisible)) { child.setState(sfExposed, enable); }
            });
        }
        return this;
    }

    first() { return this.children[0] || null; }
    at(index) { return this.children[index] || null; }
    indexOf(child) { return this.children.indexOf(child); }

    broadcast(command, infoPtr = null, infoLong = 0) {
        this.children.forEach((child) => {
            if ((child.eventMask & evBroadcast) !== 0) {
                child.handleEvent(new TVEvent(evBroadcast, { command, infoPtr, infoLong }));
            }
            if (child instanceof TVGroup) {
                child.broadcast(command, infoPtr, infoLong);
            }
        });
        return infoPtr;
    }

    firstThat(predicate) {
        if (typeof predicate !== "function") { return null; }
        for (const child of this.children) {
            if (predicate(child)) { return child; }
            if (child instanceof TVGroup) {
                const match = child.firstThat(predicate);
                if (match) { return match; }
            }
        }
        return null;
    }

    forEach(callback) {
        if (typeof callback === "function") { this.children.forEach(callback); }
    }

    insertBefore(child, target) {
        if (!(child instanceof TVView)) {
            throw new TypeError("TVGroup.insertBefore expects TVView");
        }
        const index = this.indexOf(target);
        if (index < 0) { return this.insert(child); }
        child.owner = this;
        this.children.splice(index, 0, child);
        return child;
    }

    delete(child) { return this.remove(child); }

    focusNext(forwards = true) {
        const selectable = this.children.filter((child) => (
            child.getState(sfVisible) && !child.getState(sfDisabled)
            && ((child.options & ofSelectable) !== 0 || child.root?.tabIndex >= 0)
        ));
        if (!selectable.length) { return false; }
        const current = selectable.indexOf(this.current);
        const offset = forwards ? 1 : -1;
        const index = (current + offset + selectable.length) % selectable.length;
        this.setCurrent(selectable[index]);
        selectable[index].focus();
        return true;
    }

    selectNext(forwards = true) { return this.focusNext(forwards); }

    lock() { this.lockFlag += 1; }

    unlock() {
        if (this.lockFlag > 0) { this.lockFlag -= 1; }
        if (this.lockFlag === 0) { this.redraw(); }
    }

    redraw() {
        if (this.lockFlag === 0) { this.drawView(); }
        return this;
    }

    execView(view) { return view instanceof TVView ? view.execute() : 0; }

    execute() {
        this.endState = 0;
        this.show();
        return this.endState;
    }

    endModal(command) {
        this.endState = command;
        if (this.getState(sfModal)) { this.hide(); }
        else { this.owner?.endModal?.(command); }
        return command;
    }

    insert(child) {
        if (!(child instanceof TVView)) {
            throw new TypeError("TVGroup.insert expects TVView");
        }
        child.owner = this;
        this.children.push(child);
        return child;
    }

    insertAll(children = []) {
        children.forEach((child) => this.insert(child));
        return this;
    }

    remove(child) {
        const index = this.children.indexOf(child);
        if (index < 0) { return null; }
        this.children.splice(index, 1);
        child.owner = null;
        return child;
    }

    dataSize() { return this.children.reduce((size, child) => size + (child.dataSize?.() || 0), 0); }

    getData() { return this.children.map((child) => child.getData?.()); }

    setData(values) {
        if (Array.isArray(values)) {
            this.children.forEach((child, index) => child.setData?.(values[index]));
        }
        return this;
    }

    valid(command = 0) { return this.children.every((child) => child.valid?.(command) !== false); }

    getHelpCtx() {
        const currentContext = this.current && typeof this.current.getHelpCtx === "function"
            ? this.current.getHelpCtx()
            : hcNoContext;
        return currentContext || super.getHelpCtx();
    }

    resolve(root) {
        super.resolve(root);
        this.children.forEach((child) => child.resolve?.(this.root || root));
        return this;
    }
}

// ── TVInfoBox — framed info-box container with title ────────────────

class TVInfoRow extends TVStaticText {
    constructor(bounds, text = "") {
        super(bounds, text);
        this.infoWidth = 0;
    }

    _borderRole() { return this.owner instanceof TVInfoBox ? this.owner._borderRole() : ""; }

    draw() {
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const attrs = attrsToString(this._drawAttrs());
        return `<div class="tv-static-text tv-info-row"${style} ${attrs}>${TVInfoBox.rowHtml(
            this.infoWidth,
            this.text,
            TVView._roleClassNames(this._borderRole()),
        )}</div>`;
    }

    setText(text) {
        this.text = String(text ?? "");
        if (this.root) {
            this.root.innerHTML = TVInfoBox.rowHtml(
                this.infoWidth,
                this.text,
                TVView._roleClassNames(this._borderRole()),
            );
        }
        return this;
    }

    setHTML(html, contentLen) {
        if (!this.root) { return this; }
        const borderClass = TVView._roleClassNames(this._borderRole());
        const classAttr = borderClass ? ` class="${escapeHtml(borderClass)}"` : "";
        const border = `<span data-tv-info-side${classAttr}>│</span>`;
        const padding = " ".repeat(Math.max(0, this.infoWidth - 1 - contentLen));
        this.root.innerHTML = border + " " + html + padding + border;
        return this;
    }
}

class TVInfoBox extends TVView {
    constructor(bounds, title, children = []) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVInfoBox expects TVRect bounds");
        }
        super(bounds);
        this.title = String(title ?? "");
        this.children = Array.isArray(children) ? children : [];
        this.children.forEach((child) => {
            if (child instanceof TVView) { child.owner = this; }
        });
        this._el = null;
    }

    get innerW() { return this.bounds.width - 2; }

    _borderRole() { return String(this.constructor.borderRole || ""); }

    draw() {
        const innerW = this.innerW;
        const bounded = this.children.some((child) => (
            child instanceof TVView
            && (child.bounds.x1 !== 0 || child.bounds.y1 !== 0
                || child.bounds.x2 !== 0 || child.bounds.y2 !== 0)
        ));
        const parts = [];
        // Header
        parts.push(`<span data-tv-info-frame="top">${escapeHtml(TVInfoBox.header(innerW, this.title))}</span>`);
        // Children — all TVView instances
        for (const child of this.children) {
            if (child && typeof child.draw === "function") {
                if (child instanceof TVInfoRow) {
                    child.infoWidth = innerW;
                }
                parts.push(child.draw());
            }
        }
        // Footer
        parts.push(`<span data-tv-info-frame="bottom">${escapeHtml(TVInfoBox.footer(innerW))}</span>`);

        const bounds = TVView._viewBoundsStyle(this);
        const cls = [
            "tv-info-box",
            bounded ? "is-bounded" : "",
            TVView._roleClassNames(this._drawRole()),
        ].filter(Boolean).join(" ");
        const attrString = attrsToString(this._drawAttrs());
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const extra = attrString ? ` ${attrString}` : "";
        return `<div class="${escapeHtml(cls)}" data-tv-info-w="${innerW}"${style}${extra}>${parts.join("")}</div>`;
    }

    resolve(rootEl) {
        this._el = null;
        if (!rootEl) { return this; }
        this._el = rootEl.getAttribute?.("data-tv-view-id") === this.viewId
            ? rootEl
            : rootEl.querySelector(`[data-tv-view-id="${this.viewId}"]`);
        if (!this._el) { return this; }
        this.bindRoot(this._el);
        for (const child of this.children) {
            child?.resolve?.(this._el);
        }
        return this;
    }

    updateRow(row, text) {
        if (!(row instanceof TVInfoRow) || !this.children.includes(row)) { return; }
        row.infoWidth = this.innerW;
        row.setText(text);
    }

    updateRowHTML(row, html, contentLen) {
        if (!(row instanceof TVInfoRow) || !this.children.includes(row)) { return; }
        row.infoWidth = this.innerW;
        row.setHTML(html, contentLen);
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
        const classAttr = borderClass ? ` class="${escapeHtml(borderClass)}"` : "";
        const B = `<span data-tv-info-side${classAttr}>\u2502</span>`;
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

class TVTerminal extends TVView {
    constructor(bounds, maxLines = 100) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVTerminal expects TVRect bounds");
        }
        super(bounds);
        this.width = bounds.width;
        this.rows = bounds.height;
        this.maxLines = Math.max(1, Number(maxLines) || 100);
        this.lines = [];
    }

    draw() {
        const className = ["tv-terminal", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const attrString = attrsToString(this._drawAttrs({
            role: "log",
            "aria-live": "polite",
            ...(this._semanticName() ? { [`data-tv-${this._semanticName()}`]: true } : {}),
        }));
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const rows = Array.from({ length: this.rows }, (_unused, index) => (
            `<span data-tv-terminal-line="${index}"></span>`
        )).join("");
        return `<div class="${escapeHtml(className)}"${style} ${attrString}>${rows}</div>`;
    }

    bind(root) {
        this.bindRoot(root);
        this.render();
        return this;
    }

    append(value) {
        const nextLines = String(value ?? "").split(/\r?\n/);
        this.lines.push(...nextLines);
        if (this.lines.length > this.maxLines) {
            this.lines.splice(0, this.lines.length - this.maxLines);
        }
        this.render();
    }

    clear() {
        this.lines = [];
        this.render();
    }

    render() {
        if (!this.root) { return; }
        const innerWidth = Math.max(0, this.width - 2);
        const visible = this.lines.slice(-this.rows);
        const offset = this.rows - visible.length;
        this._queryAll("[data-tv-terminal-line]").forEach((element, index) => {
            const text = index >= offset ? visible[index - offset] : "";
            const clipped = Array.from(text).slice(0, Math.max(0, innerWidth - 1)).join("");
            element.innerHTML = TVInfoBox.rowHtml(innerWidth, clipped);
        });
    }
}

class TVIndicator extends TVView {
    draw() {
        const className = "tv-editor-indicator";
        const attrString = attrsToString(this._drawAttrs({ "aria-live": "polite" }));
        return `<span class="${escapeHtml(className)}" ${attrString}>RO  1:1</span>`;
    }

    update(line, column) {
        if (this.root) { this.root.textContent = `RO  ${line}:${column}`; }
    }
}

class TVEditor extends TVView {
    constructor(bounds, hScrollBar = null, vScrollBar = null, indicator = null, bufSize = 65535) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVEditor expects TVRect bounds");
        }
        super(bounds);
        this.hScrollBar = hScrollBar;
        this.vScrollBar = vScrollBar;
        this.indicator = indicator;
        this.bufSize = Math.max(1, Number(bufSize) || 65535);
        this.readOnly = true;
        this.lastQuery = "";
        this.lastMatchEnd = 0;
        this.onSelectionChange = () => this.updateIndicator();
    }

    bindRoot(root) {
        if (this.root) {
            this.root.removeEventListener("keyup", this.onSelectionChange);
            this.root.removeEventListener("mouseup", this.onSelectionChange);
            document.removeEventListener("selectionchange", this.onSelectionChange);
        }
        super.bindRoot(root);
        if (this.root) {
            this.root.dataset.tvEditor = "1";
            this.root.setAttribute("role", "document");
            this.root.setAttribute("aria-readonly", this.readOnly ? "true" : "false");
            if (!this.root.hasAttribute("tabindex")) { this.root.tabIndex = 0; }
            this.root.addEventListener("keyup", this.onSelectionChange);
            this.root.addEventListener("mouseup", this.onSelectionChange);
            document.addEventListener("selectionchange", this.onSelectionChange);
        }
        this.updateIndicator();
        return this;
    }

    setReadOnly(readOnly = true) {
        this.readOnly = Boolean(readOnly);
        this.root?.setAttribute("aria-readonly", this.readOnly ? "true" : "false");
        return this;
    }

    selectionOffset() {
        const selection = window.getSelection();
        if (!selection || !selection.anchorNode || !this.root?.contains(selection.anchorNode)) { return 0; }
        const range = document.createRange();
        range.selectNodeContents(this.root);
        range.setEnd(selection.anchorNode, selection.anchorOffset);
        return range.toString().length;
    }

    updateIndicator() {
        if (!this.root || !this.indicator) { return; }
        const text = this.root.textContent || "";
        const offset = Math.min(text.length, this.selectionOffset());
        const before = text.slice(0, offset);
        const lines = before.split("\n");
        this.indicator.update(lines.length, (lines[lines.length - 1] || "").length + 1);
    }

    textNodeAt(offset) {
        const walker = document.createTreeWalker(this.root, NodeFilter.SHOW_TEXT);
        let remaining = offset;
        let node = walker.nextNode();
        while (node) {
            if (remaining <= node.nodeValue.length) {
                return { node, offset: remaining };
            }
            remaining -= node.nodeValue.length;
            node = walker.nextNode();
        }
        return null;
    }

    find(query, { fromStart = false } = {}) {
        const value = String(query || "");
        if (!this.root || !value) { return false; }
        const text = this.root.textContent || "";
        const start = fromStart || value !== this.lastQuery ? 0 : this.lastMatchEnd;
        let index = text.toLocaleLowerCase().indexOf(value.toLocaleLowerCase(), start);
        if (index < 0 && start > 0) {
            index = text.toLocaleLowerCase().indexOf(value.toLocaleLowerCase());
        }
        if (index < 0) { return false; }
        const first = this.textNodeAt(index);
        const last = this.textNodeAt(index + value.length);
        if (!first || !last) { return false; }
        const range = document.createRange();
        range.setStart(first.node, first.offset);
        range.setEnd(last.node, last.offset);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        first.node.parentElement?.scrollIntoView({ block: "center" });
        this.lastQuery = value;
        this.lastMatchEnd = index + value.length;
        this.updateIndicator();
        return true;
    }

    findNext() {
        return this.find(this.lastQuery);
    }

    destroy() {
        if (!this.root) { return; }
        this.root.removeEventListener("keyup", this.onSelectionChange);
        this.root.removeEventListener("mouseup", this.onSelectionChange);
        document.removeEventListener("selectionchange", this.onSelectionChange);
        this.root = null;
    }
}

class TVListViewer extends TVView {
    constructor(bounds, numCols = 1, hScrollBar = null, vScrollBar = null) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVListViewer expects TVRect bounds");
        }
        super(bounds);
        this.numCols = Math.max(1, Number(numCols) || 1);
        this.hScrollBar = hScrollBar;
        this.vScrollBar = vScrollBar;
        this.topItem = 0;
        this.focused = -1;
        this.range = 0;
        this.items = [];
        this.selectedIndex = -1;
        this.selectHandler = null;
        this.activateHandler = null;
    }

    draw() {
        const className = ["tv-list-viewer", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const attrs = attrsToString(this._drawAttrs(
            this._semanticName() ? { [`data-tv-${this._semanticName()}`]: true } : {},
        ));
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        return `<div class="${escapeHtml(className)}"${style} ${attrs}></div>`;
    }

    bindRoot(root) {
        super.bindRoot(root);
        if (this.root) {
            this.root.dataset.tvListBox = "1";
        }
        return this;
    }

    itemsRoot() {
        return this.root;
    }

    itemSelector() {
        return "[data-tv-list-index]";
    }

    resolveIndex(target) {
        const element = target && target.closest ? target.closest(this.itemSelector()) : null;
        if (!element) {
            return -1;
        }
        const value = Number.parseInt(element.dataset.tvListIndex || "", 10);
        return Number.isInteger(value) ? value : -1;
    }

    defaultContent(item, index) {
        if (typeof item === "string") {
            return escapeHtml(item);
        }
        return escapeHtml(item && item.label ? item.label : "");
    }

    defaultMarkup(item, index) {
        const className = [
            "tv-vlist-item",
            index === this.selectedIndex ? "is-selected" : "",
        ].filter(Boolean).join(" ");
        return `<div role="option" tabindex="-1" class="${className}" data-tv-list-index="${index}"><span class="tv-vlist-text">${this.defaultContent(item, index)}</span></div>`;
    }

    itemMarkup(item, index) {
        return this.defaultMarkup(item, index);
    }

    setItems(items = [], selectedIndex = -1) {
        this.items = Array.isArray(items) ? [...items] : [];
        this.range = this.items.length;
        const itemsRoot = this.itemsRoot();
        if (itemsRoot) {
            itemsRoot.innerHTML = this.items.map((item, index) => this.itemMarkup(item, index)).join("");
        }
        this.select(selectedIndex, { scroll: false });
    }

    select(index, { scroll = true } = {}) {
        if (!Number.isInteger(index) || index < 0 || index >= this.items.length) {
            this.selectedIndex = -1;
        } else {
            this.selectedIndex = index;
        }
        this.focused = this.selectedIndex;
        this.updateSelectionUi(scroll);
    }

    focusItem(index) {
        this.select(index);
        this.selectedElement()?.focus();
    }

    focusItemNum(index) { this.focusItem(index); }

    selectItem(index) {
        this.select(index);
        if (this.selectHandler && this.selectedIndex >= 0) {
            this.selectHandler(this.items[this.selectedIndex], this.selectedIndex, null);
        }
    }

    getText(index, maxLen = Number.MAX_SAFE_INTEGER) {
        const item = this.items[index];
        const text = typeof item === "string" ? item : String(item?.label ?? "");
        return Array.from(text).slice(0, Math.max(0, Number(maxLen) || 0)).join("");
    }

    isSelected(index) { return index === this.selectedIndex; }

    setRange(range) {
        this.range = Math.max(0, Number(range) || 0);
        if (this.selectedIndex >= this.range) { this.select(this.range - 1); }
    }

    selectedItem() {
        return this.selectedIndex >= 0 ? this.items[this.selectedIndex] : null;
    }

    selectedElement() {
        const itemsRoot = this.itemsRoot();
        return itemsRoot
            ? itemsRoot.querySelector(`${this.itemSelector()}[data-tv-list-index="${this.selectedIndex}"]`)
            : null;
    }

    updateSelectionUi(scroll = true) {
        const itemsRoot = this.itemsRoot();
        if (!itemsRoot) {
            return;
        }
        const elements = Array.from(itemsRoot.querySelectorAll(this.itemSelector()));
        elements.forEach((element, index) => {
            const value = Number.parseInt(element.dataset.tvListIndex || "", 10);
            const selected = value === this.selectedIndex;
            element.setAttribute("role", "option");
            element.classList.toggle("is-selected", selected);
            element.setAttribute("aria-selected", selected ? "true" : "false");
            element.tabIndex = selected || (this.selectedIndex < 0 && index === 0) ? 0 : -1;
        });
        if (scroll) {
            this.ensureSelectionVisible();
        }
    }

    ensureSelectionVisible() {
        const element = this.selectedElement();
        const itemsRoot = this.itemsRoot();
        if (!element || !itemsRoot) {
            return;
        }
        const elementRect = element.getBoundingClientRect();
        const rootRect = itemsRoot.getBoundingClientRect();
        if (elementRect.top < rootRect.top) {
            itemsRoot.scrollTop -= rootRect.top - elementRect.top;
        } else if (elementRect.bottom > rootRect.bottom) {
            itemsRoot.scrollTop += elementRect.bottom - rootRect.bottom;
        }
    }

    bind({ onSelect = null, onActivate = null } = {}) {
        this.selectHandler = onSelect;
        this.activateHandler = onActivate;
        const itemsRoot = this.itemsRoot();
        if (!itemsRoot || itemsRoot.dataset.tvListBoxBound === "1") {
            return;
        }
        itemsRoot.dataset.tvListBoxBound = "1";
        itemsRoot.setAttribute("role", "listbox");
        itemsRoot.addEventListener("click", (event) => {
            const index = this.resolveIndex(event.target);
            if (index < 0) {
                return;
            }
            this.select(index);
            if (this.selectHandler) {
                this.selectHandler(this.items[index], index, event);
            }
        });
        itemsRoot.addEventListener("dblclick", (event) => {
            const index = this.resolveIndex(event.target);
            if (index < 0) {
                return;
            }
            this.select(index);
            if (this.activateHandler) {
                this.activateHandler(this.items[index], index, event);
            }
        });
        itemsRoot.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    onKeyDown(event) {
        const current = this.resolveIndex(event.target);
        if (current < 0 || !this.items.length) {
            return;
        }
        let next = current;
        if (event.key === "ArrowDown" || event.key === "ArrowRight") {
            next = Math.min(this.items.length - 1, current + 1);
        } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
            next = Math.max(0, current - 1);
        } else if (event.key === "Home") {
            next = 0;
        } else if (event.key === "End") {
            next = this.items.length - 1;
        } else if (event.key === "Enter") {
            event.preventDefault();
            event.stopPropagation();
            this.select(current);
            if (this.activateHandler) {
                this.activateHandler(this.items[current], current, event);
            } else if (this.selectHandler) {
                this.selectHandler(this.items[current], current, event);
            }
            return;
        } else if (event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            this.select(current);
            if (this.selectHandler) {
                this.selectHandler(this.items[current], current, event);
            }
            return;
        } else {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.select(next);
        const element = this.selectedElement();
        if (element) { element.focus(); }
        if (this.selectHandler && next !== current) {
            this.selectHandler(this.items[next], next, event);
        }
    }
}

class TVListBox extends TVListViewer {
    constructor(bounds, numCols = 1, scrollBar = null) {
        super(bounds, numCols, null, scrollBar);
        this.list = [];
        this.viewport = null;
        this.scrollViewport = null;
        this.externalScrollbarWidget = null;
        this.scrollbarWidget = null;
        this.scrollbar = null;
        this.active = true;
    }

    hasScrollbar() { return true; }

    newList(list = []) {
        this.list = Array.isArray(list) ? list : [];
        this.setItems(this.list, this.list.length ? 0 : -1);
    }

    draw() {
        const rootClasses = [
            "tv-vlist-viewer",
            TVView._roleClassNames(this._drawRole()),
        ].filter(Boolean).join(" ");
        const scrollFrameAttr = this.hasScrollbar() ? " data-tv-scroll-frame" : "";
        const attrString = attrsToString(this._drawAttrs(
            {
                ...(this._semanticName() ? { [`data-tv-${this._semanticName()}`]: true } : {}),
                hidden: !this.getState(sfVisible),
            },
        ));
        const rootAttrsText = attrString ? ` ${attrString}` : "";
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const scrollbarMarkup = this.hasScrollbar()
            ? new TVScrollBar(new TVRect(), sbVertical).draw()
            : "";
        return `
            <div class="${escapeHtml(rootClasses)}"${style}${scrollFrameAttr}${rootAttrsText}>
                <div class="tv-vlist-viewport" data-tv-list-viewport data-tv-viewport></div>
                ${scrollbarMarkup}
            </div>
        `;
    }

    bindRoot(root) {
        this.scrollbarWidget?.destroy();
        super.bindRoot(root);
        this.viewport = this._query("[data-tv-list-viewport]");
        this.scrollViewport = this.viewport;
        this.scrollbarWidget = this.root?.querySelector(".tv-scrollbar-y")
            ? new TVScrollBar(new TVRect()).bindRoot(this.root)
            : null;
        this.scrollbar = this.scrollbarWidget?.axes.y?.root || null;
        if (this.root) {
            this.root.dataset.tvListViewer = "1";
            this.root._tvListViewer = this;
        }
        return this;
    }

    itemsRoot() {
        return this.viewport;
    }

    resolvePointerIndex(event) {
        if (event && (event.clientX !== 0 || event.clientY !== 0) && this.viewport) {
            const element = Array.from(this.viewport.querySelectorAll(this.itemSelector())).find((item) => {
                const rect = item.getBoundingClientRect();
                return event.clientX >= rect.left && event.clientX < rect.right
                    && event.clientY >= rect.top && event.clientY < rect.bottom;
            });
            if (element) {
                return this.resolveIndex(element);
            }
        }
        return this.resolveIndex(event?.target);
    }

    setItems(items = [], selectedIndex = -1) {
        if (this.scrollViewport) {
            this.scrollViewport.scrollTop = 0;
        }
        super.setItems(items, selectedIndex);
        this.updateScrollbar();
    }

    select(index, { scroll = true } = {}) {
        super.select(index, { scroll });
        this.updateScrollbar();
    }

    ensureSelectionVisible() {
        const element = this.selectedElement();
        const viewport = this.scrollViewport;
        if (!element || !viewport) {
            return;
        }
        const elementRect = element.getBoundingClientRect();
        const viewportRect = viewport.getBoundingClientRect();
        if (elementRect.top < viewportRect.top) {
            viewport.scrollTop -= viewportRect.top - elementRect.top;
        } else if (elementRect.bottom > viewportRect.bottom) {
            viewport.scrollTop += elementRect.bottom - viewportRect.bottom;
        }
    }

    visibleRows() {
        if (!this.scrollViewport) {
            return 1;
        }
        return Math.max(1, Math.floor(this.scrollViewport.clientHeight / measureCells().height));
    }

    setScrollViewport(viewport = null, scrollbarWidget = null) {
        this.scrollViewport = viewport || this.viewport;
        this.externalScrollbarWidget = scrollbarWidget;
        return this;
    }

    updateScrollbar() {
        this.scrollbarWidget?.refresh();
        this.externalScrollbarWidget?.refresh();
    }

    setActive(active) {
        this.active = Boolean(active);
        if (this.root) {
            this.root.classList.toggle("is-inactive", !this.active);
        }
        this.scrollbarWidget?.setActive(this.active);
    }

    bind({ onSelect = null, onActivate = null } = {}) {
        this.selectHandler = onSelect;
        this.activateHandler = onActivate;
        if (!this.root || this.root.dataset.tvListViewerBound === "1") {
            return;
        }
        this.root.dataset.tvListViewerBound = "1";
        if (this.viewport) {
            this.viewport.setAttribute("role", "listbox");
            this.viewport.addEventListener("click", (event) => {
                const index = this.resolvePointerIndex(event);
                if (index < 0) {
                    return;
                }
                this.select(index);
                if (this.selectHandler) {
                    this.selectHandler(this.items[index], index, event);
                }
                this.selectedElement()?.focus({ preventScroll: true });
            });
            this.viewport.addEventListener("dblclick", (event) => {
                const index = this.resolvePointerIndex(event);
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
                if (index < 0 || !this.items.length) {
                    return;
                }
                let next = index;
                if (event.key === "Enter") {
                    event.preventDefault();
                    event.stopPropagation();
                    this.select(index);
                    if (this.activateHandler) {
                        this.activateHandler(this.items[index], index, event);
                    } else if (this.selectHandler) {
                        this.selectHandler(this.items[index], index, event);
                    }
                    this.selectedElement()?.focus({ preventScroll: true });
                    return;
                } else if (event.key === " ") {
                    event.preventDefault();
                    event.stopPropagation();
                    this.select(index);
                    if (this.selectHandler) {
                        this.selectHandler(this.items[index], index, event);
                    }
                    this.selectedElement()?.focus({ preventScroll: true });
                    return;
                } else if (event.key === "ArrowDown") {
                    next = Math.min(this.items.length - 1, index + 1);
                } else if (event.key === "ArrowUp") {
                    next = Math.max(0, index - 1);
                } else if (event.key === "Home") {
                    next = 0;
                } else if (event.key === "End") {
                    next = this.items.length - 1;
                } else if (event.key === "PageDown") {
                    next = Math.min(this.items.length - 1, index + this.visibleRows());
                } else if (event.key === "PageUp") {
                    next = Math.max(0, index - this.visibleRows());
                } else {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                this.select(next);
                if (this.selectHandler && next !== index) {
                    this.selectHandler(this.items[next], next, event);
                }
                this.selectedElement()?.focus({ preventScroll: true });
            });
        }
    }

    destroy() {
        this.scrollbarWidget?.destroy();
        this.scrollbarWidget = null;
        this.externalScrollbarWidget = null;
    }
}

class TVOutline extends TVListBox {
    constructor(bounds, numCols = 1) {
        super(bounds, numCols);
        this.tree = [];
        this.expanded = new Set();
        this.nodeSelectHandler = null;
        this.nodeActivateHandler = null;
    }

    getChildren(node) { return node?.children || []; }

    getKey(node) { return node?.key ?? node?.path ?? node?.id ?? node?.label; }

    getLabel(node) { return node?.label ?? ""; }

    renderNodeContent(node) { return escapeHtml(String(this.getLabel(node))); }

    defaultContent(entry) { return this.renderEntry(entry); }

    nodeKey(node, fallback = "") {
        const key = this.getKey(node);
        return String(key == null ? fallback : key);
    }

    childrenOf(node) {
        const children = this.getChildren(node);
        return Array.isArray(children) ? children : [];
    }

    expandAll(nodes = this.tree, prefix = "") {
        nodes.forEach((node, index) => {
            const key = this.nodeKey(node, `${prefix}${index}`);
            const children = this.childrenOf(node);
            if (children.length) {
                this.expanded.add(key);
                this.expandAll(children, `${key}/`);
            }
        });
    }

    flatten(nodes = this.tree, depth = 0, parentKey = "") {
        const result = [];
        nodes.forEach((node, index) => {
            const key = this.nodeKey(node, `${parentKey}${index}`);
            const children = this.childrenOf(node);
            const entry = {
                node,
                key,
                parentKey,
                depth,
                hasChildren: children.length > 0,
                expanded: children.length > 0 && this.expanded.has(key),
            };
            result.push(entry);
            if (entry.expanded) {
                result.push(...this.flatten(children, depth + 1, key));
            }
        });
        return result;
    }

    renderEntry(entry) {
        const indent = "  ".repeat(entry.depth);
        const marker = entry.hasChildren ? (entry.expanded ? "▼ " : "► ") : "· ";
        const content = this.renderNodeContent(entry.node, entry);
        return `${escapeHtml(indent + marker)}${content}`;
    }

    setTree(nodes = [], selectedKey = null, { expandAll = false } = {}) {
        this.tree = Array.isArray(nodes) ? nodes : [];
        this.expanded.clear();
        if (expandAll) { this.expandAll(); }
        this.refreshTree(selectedKey);
    }

    refreshTree(selectedKey = this.selectedEntry()?.key ?? null) {
        const entries = this.flatten();
        const index = selectedKey == null
            ? (entries.length ? 0 : -1)
            : entries.findIndex((entry) => entry.key === String(selectedKey));
        super.setItems(entries, index >= 0 ? index : (entries.length ? 0 : -1));
    }

    selectedEntry() {
        return super.selectedItem();
    }

    selectedItem() {
        return this.selectedEntry()?.node || null;
    }

    indexForKey(key) {
        return this.items.findIndex((entry) => entry.key === String(key));
    }

    selectKey(key, options = {}) {
        const index = this.indexForKey(key);
        this.select(index, options);
        return index >= 0;
    }

    toggle(index, expanded = null) {
        const entry = this.items[index];
        if (!entry?.hasChildren) { return false; }
        const shouldExpand = expanded == null ? !this.expanded.has(entry.key) : Boolean(expanded);
        if (shouldExpand) { this.expanded.add(entry.key); }
        else { this.expanded.delete(entry.key); }
        this.refreshTree(entry.key);
        return true;
    }

    bind({ onSelect = null, onActivate = null } = {}) {
        this.nodeSelectHandler = onSelect;
        this.nodeActivateHandler = onActivate;
        if (this.viewport && this.viewport.dataset.tvOutlineKeysBound !== "1") {
            this.viewport.dataset.tvOutlineKeysBound = "1";
            this.viewport.addEventListener("keydown", (event) => {
                if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") { return; }
                const index = this.resolveIndex(event.target);
                const entry = this.items[index];
                if (!entry) { return; }
                event.preventDefault();
                event.stopImmediatePropagation();
                if (event.key === "ArrowRight") {
                    if (entry.hasChildren && !entry.expanded) {
                        this.toggle(index, true);
                    } else if (entry.hasChildren) {
                        this.select(index + 1);
                    }
                } else if (entry.hasChildren && entry.expanded) {
                    this.toggle(index, false);
                } else if (entry.parentKey) {
                    this.selectKey(entry.parentKey);
                }
                this.selectedElement()?.focus({ preventScroll: true });
            }, true);
        }
        super.bind({
            onSelect: (entry, index, event) => this.nodeSelectHandler?.(entry.node, index, event),
            onActivate: (entry, index, event) => this.nodeActivateHandler?.(entry.node, index, event),
        });
    }
}

class TVScroller extends TVView {
    constructor(bounds, hScrollBar = null, vScrollBar = null) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVScroller expects TVRect bounds");
        }
        super(bounds);
        this.hScrollBar = hScrollBar instanceof TVScrollBar ? hScrollBar : null;
        this.vScrollBar = vScrollBar instanceof TVScrollBar ? vScrollBar : null;
        this.delta = new TVPoint();
        this.limit = new TVPoint();
        this.viewport = null;
    }

    draw() {
        const attrString = attrsToString(this._drawAttrs(
            this._semanticName() ? { [`data-tv-${this._semanticName()}`]: true } : {},
        ));
        const attrs = attrString ? ` ${attrString}` : "";
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const className = ["tv-scroller", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        return `
            <div class="${escapeHtml(className)}" data-tv-scroll-frame${style}${attrs}>
                <div class="tv-scroller-viewport" data-tv-scroll-viewport data-tv-viewport></div>
                ${this.vScrollBar?.draw() || ""}
            </div>
        `;
    }

    bindRoot(root) {
        this.vScrollBar?.destroy();
        super.bindRoot(root);
        this.viewport = this._query("[data-tv-scroll-viewport]");
        this.vScrollBar?.bindRoot(this.root);
        return this;
    }

    update() {
        this.vScrollBar?.refresh();
    }

    bind() {
        this.update();
    }

    destroy() {
        this.vScrollBar?.destroy();
    }
}

class TVMenu {
    constructor(items = []) {
        this.items = Array.isArray(items) ? items : [];
        this.defaultItem = null;
    }
}

class TVMenuView extends TVView {
    constructor(bounds, menu = new TVMenu()) {
        super(bounds);
        if (!(menu instanceof TVMenu)) {
            throw new TypeError("TVMenuView expects TVMenu");
        }
        this.menu = menu;
    }

    drawItem(item, view = "popup") {
        if (item.separator) {
            return '<div class="tv-menu-popup-separator" aria-hidden="true">'
                + '<span class="tv-border-corner">├</span>'
                + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                + '<span class="tv-border-corner">┤</span>'
                + '</div>';
        }
        if (item.subMenu instanceof TVMenu) {
            const helpAttr = item.helpCtx !== hcNoContext ? ` data-tv-help-ctx="${item.helpCtx}"` : "";
            return '<div class="tv-submenu-root" data-tv-submenu-root="true"' + helpAttr + '>'
                + '<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle="true">'
                + item.name + '<span class="tv-submenu-arrow">►</span>'
                + '</button>'
                + new TVMenuBox(new TVRect(), item.subMenu, this).draw()
                + '</div>';
        }
        const isMenuBar = view === "bar";
        const attrs = attrsToString({
            type: "button",
            ...(item.keyCode !== kbNoKey ? { "data-tv-key-code": item.keyCode } : {}),
            ...(item.helpCtx !== hcNoContext ? { "data-tv-help-ctx": item.helpCtx } : {}),
            ...TVView._controlAttrs({
                name: item.command,
                command: item.command,
                value: item.value(),
                commandData: item.commandData(),
                disabled: item.disabled,
                ariaHasPopup: isMenuBar ? true : null,
                ariaExpanded: isMenuBar ? false : null,
            }),
        });
        const className = isMenuBar ? "tv-menu-item tv-menu-button" : "tv-menu-popup-item";
        return `<button class="${className}" ${attrs}>${item.name}</button>`;
    }

    renderItems(items = this.menu.items, view = "popup") {
        return items.map((item) => (
            typeof item === "string" ? item : item instanceof TVMenuItem ? this.drawItem(item, view) : ""
        ));
    }

    draw(view = "popup") { return this.renderItems(this.menu.items, view).join(""); }
}

/**
 * Turbo Vision menu command descriptor. TMenuItem is not a TButton: the
 * owning TMenuView decides whether it is drawn in a menu bar or menu box.
 */
class TVMenuItem {
    constructor(
        name,
        command = "",
        keyCode = kbNoKey,
        helpCtx = hcNoContext,
        param = true,
        next = null,
    ) {
        this.next = next instanceof TVMenuItem ? next : null;
        this.name = String(name || "");
        this.command = command;
        this.flags = 0;
        this.keyCode = Number(keyCode) || kbNoKey;
        this.helpCtx = normalizeHelpContext(helpCtx);
        this.param = param;
        this.subMenu = null;
        this.separator = false;
        this.disabled = false;
    }

    value() {
        return this.param && typeof this.param === "object"
            ? (Object.hasOwn(this.param, "value") ? this.param.value : true)
            : this.param;
    }

    commandData() {
        if (!this.param || typeof this.param !== "object") { return {}; }
        const { value: _value, ...data } = this.param;
        return data;
    }

    setDisabled(disabled = true) {
        this.disabled = Boolean(disabled);
        return this;
    }

}

function NewLine(next = null) {
    const item = new TVMenuItem("");
    item.separator = true;
    item.next = next instanceof TVMenuItem ? next : null;
    return item;
}

function NewSubMenu(name, helpCtx, subMenu, next = null) {
    if (!(subMenu instanceof TVMenu)) {
        throw new TypeError("NewSubMenu expects TVMenu");
    }
    const item = new TVMenuItem(name, "", kbNoKey, helpCtx);
    item.subMenu = subMenu;
    item.next = next instanceof TVMenuItem ? next : null;
    return item;
}

/** Turbo Vision status-line command descriptor (TStatusItem). */
class TVStatusItem {
    constructor(text, keyCode = 0, command = "", param = true, next = null) {
        this.next = next instanceof TVStatusItem ? next : null;
        this.text = String(text || "");
        this.keyCode = keyCode;
        this.command = command;
        this.param = param;
        this.disabled = false;
    }

    setDisabled(disabled = true) {
        this.disabled = Boolean(disabled);
        return this;
    }

}

class TVStatusDef {
    constructor(min, max, items = [], next = null) {
        this.next = next instanceof TVStatusDef ? next : null;
        this.min = normalizeHelpContext(min);
        this.max = normalizeHelpContext(max);
        this.items = Array.isArray(items) ? items : [];
    }
}

function NewStatusKey(text, keyCode, command, param = true, next = null) {
    return new TVStatusItem(text, keyCode, command, param, next);
}

function NewStatusDef(min, max, items, next = null) {
    return new TVStatusDef(min, max, items, next);
}

class TVStatusLine extends TVView {
    constructor(bounds, statusDefs = NewStatusDef(hcNoContext, 0xffff, [])) {
        super(bounds);
        if (!(statusDefs instanceof TVStatusDef)) {
            throw new TypeError("TVStatusLine expects TVStatusDef");
        }
        this.defs = statusDefs;
        this.items = statusDefs.items;
    }

    findItems(helpCtx = this.getHelpCtx()) {
        const context = normalizeHelpContext(helpCtx);
        let definition = this.defs;
        while (definition) {
            if (context >= definition.min && context <= definition.max) {
                this.items = definition.items;
                return this.items;
            }
            definition = definition.next;
        }
        this.items = [];
        return this.items;
    }

    drawItem(item) {
        const attrs = attrsToString({
            type: "button",
            ...(item.keyCode !== kbNoKey ? { "data-tv-key-code": item.keyCode } : {}),
            ...TVView._controlAttrs({
                name: item.command,
                command: item.command,
                value: item.param && typeof item.param === "object" && Object.hasOwn(item.param, "value")
                    ? item.param.value
                    : item.param,
                commandData: item.param && typeof item.param === "object"
                    ? Object.fromEntries(Object.entries(item.param).filter(([key]) => key !== "value"))
                    : {},
                disabled: item.disabled,
            }),
        });
        return `<button class="tv-status-item" ${attrs}>${item.text}</button>`;
    }

    draw() {
        return this.items.map((item) => (
            typeof item === "string" ? item : item instanceof TVStatusItem ? this.drawItem(item) : ""
        )).join("");
    }
}

class TVMenuBox extends TVMenuView {
    constructor(bounds, menu = new TVMenu(), parentMenu = null) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVMenuBox expects TVRect bounds");
        }
        super(bounds, menu);
        this.parentMenu = parentMenu;
    }

    draw() {
        const isSubMenu = Boolean(this.parentMenu);
        const popupAttrs = attrsToString(this._drawAttrs({
            [isSubMenu ? "data-tv-submenu-popup" : "data-tv-menu-popup"]: true,
            hidden: true,
        }));
        const attrs = popupAttrs ? ` ${popupAttrs}` : "";
        const className = `tv-menu-popup${isSubMenu ? " tv-submenu-popup" : ""}`;
        const borderFill = '<span class="tv-border-fill" data-tv-border-fill="\u2500" aria-hidden="true"></span>';
        const scrollbarMarkup = new TVScrollBar(new TVRect(), sbVertical).draw();
        // Split items into segments at separator strings to render them as body-level rows.
        const segments = [[]];
        for (const html of this.renderItems(this.menu.items, "popup")) {
            if (/^<div class="tv-menu-popup-separator(?:\s|\")/.test(html.trim())) {
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
        return '<div class="' + className + '"' + attrs + '>'
            + '<div class="tv-menu-popup-row">'
            + '<span class="tv-border-corner" aria-hidden="true">\u250C</span>'
            + borderFill
            + '<span class="tv-border-corner" aria-hidden="true">\u2510</span>'
            + '</div>'
            + '<div class="tv-menu-popup-main" data-tv-scroll-frame>'
            + '<div class="tv-menu-popup-body" data-tv-viewport>'
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
    const main = Array.from(popup.children).find((node) => node.classList?.contains("tv-menu-popup-main")) || null;
    const body = main
        ? Array.from(main.children).find((node) => node.classList?.contains("tv-menu-popup-body")) || null
        : null;
    const scrollbar = main?.querySelector(":scope > .tv-scrollbar-y") || null;
    const track = scrollbar?.querySelector("[data-role='track']") || null;
    const cells = scrollbar?.querySelector("[data-role='cells']") || null;
    const thumb = scrollbar?.querySelector("[data-role='thumb']") || null;
    const backward = scrollbar?.querySelector("[data-role='backward']") || null;
    const forward = scrollbar?.querySelector("[data-role='forward']") || null;
    return body && scrollbar && track && cells && thumb && backward && forward
        ? { body, scrollbar, track, cells, thumb, backward, forward }
        : null;
}

function syncMenuPopupScrollbar(popup) {
    const parts = getMenuPopupScrollbarParts(popup);
    if (!parts) {
        return;
    }
    const { body, scrollbar } = parts;
    const needsScrollbar = body.scrollHeight > body.clientHeight + 1;
    popup.classList.toggle("is-scrollable", needsScrollbar);
    body.classList.toggle("is-scrollable", needsScrollbar);
    scrollbar.hidden = !needsScrollbar;
    popup._tvMenuPopupScrollbar?.refresh();
}

function bindMenuPopupScrollbar(popup) {
    if (!popup || popup.dataset.tvMenuScrollbarBound === "1") {
        return;
    }
    const parts = getMenuPopupScrollbarParts(popup);
    if (!parts) {
        return;
    }
    popup.dataset.tvMenuScrollbarBound = "1";
    const main = popup.querySelector(".tv-menu-popup-main");
    popup._tvMenuPopupScrollbar = main ? new TVScrollBar(new TVRect()).bindRoot(main) : null;
}

function resetMenuPopupLayout(popup) {
    if (!popup) {
        return;
    }
    bindMenuPopupScrollbar(popup);
    popup.classList.remove("is-scrollable");
    popup.style.position = "";
    popup.style.left = "";
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
    const cell = measureCells();
    const cellHeight = cell.height || 16;
    const cellWidth = cell.width || 8;
    const rootRect = root.getBoundingClientRect();
    const isSubmenu = root.matches("[data-tv-submenu-root]");
    const parentPopupRect = isSubmenu
        ? root.closest(".tv-menu-popup")?.getBoundingClientRect() || null
        : null;
    const defaultTop = isSubmenu ? rootRect.top - cellHeight : rootRect.height;
    const defaultLeft = isSubmenu ? rootRect.right - cellWidth : 0;
    const body = popup.querySelector(".tv-menu-popup-body");

    popup.classList.remove("is-scrollable");
    popup.style.position = isSubmenu ? "fixed" : "";
    popup.style.left = isSubmenu ? `${Math.round(defaultLeft)}px` : "";
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

    if (isSubmenu) {
        let nextTop = defaultTop;
        const minTop = minGlobalTop;
        const maxTop = minGlobalTop + maxPopupHeight - popupRect.height;
        if (nextTop > maxTop) {
            nextTop = maxTop;
        }
        if (nextTop < minTop) {
            nextTop = minTop;
        }

        let nextLeft = defaultLeft;
        if (nextLeft + popupRect.width > window.innerWidth) {
            nextLeft = rootRect.left + cellWidth - popupRect.width;
        }
        const minLeft = 0;
        const maxLeft = Math.max(0, window.innerWidth - popupRect.width);
        if (nextLeft < minLeft) {
            nextLeft = minLeft;
        }
        if (nextLeft > maxLeft) {
            nextLeft = maxLeft;
        }

        popup.style.left = `${Math.round(nextLeft)}px`;
        popup.style.top = `${Math.round(nextTop)}px`;
    } else {
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
    }
    syncMenuPopupScrollbar(popup);
    window.requestAnimationFrame(() => {
        if (!popup.hidden) {
            syncMenuPopupScrollbar(popup);
        }
    });
}

class TVMenuController {
    constructor({ root = document, onUnhandledKeyDown = null, commandTarget = null } = {}) {
        this.root = root;
        this.onUnhandledKeyDown = onUnhandledKeyDown;
        this.commandTarget = commandTarget;
        this.menuRoots = [];
        this.topLevelActions = [];
        this.activeRoot = null;
        this.activePopup = null;
        this.previousFocus = null;
        this.lastSelection = new WeakMap();
        this.onDocumentClick = (event) => {
            if (!event.target.closest("[data-tv-menu-root]")) {
                this.closeMenus();
            }
        };
        this.onDocumentCommand = (event) => this.onCommand(event);
        this.onDocumentKeyDown = (event) => this.onKeyDown(event);
        document.addEventListener("click", this.onDocumentClick);
        document.addEventListener("click", this.onDocumentCommand);
        document.addEventListener("keydown", this.onDocumentKeyDown);
        this.refresh();
    }

    onCommand(nativeEvent) {
        const control = nativeEvent.target?.closest?.("[data-tv-command]");
        if (!control || !control.closest("[data-tv-menu-bar], [data-tv-status-line]")) { return; }
        const command = control.dataset.tvCommand || "";
        if (!command || command === "menu-toggle" || control.disabled || control.getAttribute("aria-disabled") === "true") {
            return;
        }
        nativeEvent.preventDefault();
        const event = new TVEvent(evCommand, { command, infoPtr: control, nativeEvent });
        if (this.commandTarget instanceof TVView) {
            this.commandTarget.dispatchEvent(event);
        } else {
            this.commandTarget?.handleEvent?.(event);
        }
        if (control.closest("[data-tv-menu-root]")) {
            const focusRemainsInMenu = Boolean(document.activeElement?.closest?.("[data-tv-menu-bar]"));
            this.closeMenus({ restoreFocus: focusRemainsInMenu });
        }
    }

    refresh() {
        this.menuRoots = Array.from(this.root.querySelectorAll("[data-tv-menu-root]"));
        this.topLevelActions = Array.from(this.root.querySelectorAll(".tv-menu-items > .tv-menu-item"));
        if (this.activeRoot && !this.activeRoot.isConnected) {
            this.activeRoot = null;
            this.activePopup = null;
            this.previousFocus = null;
        }
        this.menuRoots.forEach((menuRoot) => this.bindMenuRoot(menuRoot));
        this.root.querySelectorAll(".tv-menu-popup").forEach((popup) => {
            popup.setAttribute("role", "menu");
            this.menuItems(popup).forEach((item) => {
                item.setAttribute("role", "menuitem");
                item.tabIndex = -1;
                if (item.dataset.tvKeyboardMenuItemBound !== "1") {
                    item.dataset.tvKeyboardMenuItemBound = "1";
                    item.addEventListener("mouseenter", () => this.markSelected(item, false));
                }
            });
        });
        this.root.querySelectorAll("[data-tv-submenu-toggle]").forEach((toggle) => this.bindSubmenu(toggle));
    }

    getHelpCtx() {
        const selected = this.root.querySelector(".tv-menu-popup-item.is-menu-selected");
        const currentRoot = this.activeRoot?.querySelector("[data-tv-menu-toggle]") || this.activeRoot;
        return elementHelpContext(selected) || elementHelpContext(currentRoot) || hcNoContext;
    }

    bindMenuRoot(menuRoot) {
        const toggle = menuRoot.querySelector("[data-tv-menu-toggle]");
        if (!toggle || toggle.dataset.tvKeyboardMenuBound === "1") {
            return;
        }
        toggle.dataset.tvKeyboardMenuBound = "1";
        toggle.addEventListener("click", (event) => {
            event.preventDefault();
            if (this.activeRoot === menuRoot) {
                this.closeMenus({ restoreFocus: false });
                toggle.focus();
            } else {
                this.openMenu(menuRoot, { focusFirst: false });
            }
        });
        menuRoot.addEventListener("mouseenter", () => {
            if (this.activeRoot && this.activeRoot !== menuRoot) {
                this.openMenu(menuRoot, { focusFirst: false });
            }
        });
    }

    bindSubmenu(toggle) {
        if (toggle.dataset.tvKeyboardSubmenuBound === "1") {
            return;
        }
        const submenuRoot = toggle.closest("[data-tv-submenu-root]");
        const popup = this.directChild(submenuRoot, "[data-tv-submenu-popup]");
        if (!submenuRoot || !popup) {
            return;
        }
        toggle.dataset.tvKeyboardSubmenuBound = "1";
        toggle.setAttribute("aria-haspopup", "true");
        toggle.setAttribute("aria-expanded", "false");
        toggle.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (popup.hidden) {
                this.openSubmenu(toggle, { focusFirst: false });
            } else {
                this.closeSubmenu(popup, { focusToggle: false });
            }
        });
        submenuRoot.addEventListener("mouseenter", () => {
            this.openSubmenu(toggle, { focusFirst: false });
        });
        submenuRoot.addEventListener("mouseleave", (event) => {
            const related = event.relatedTarget;
            if (related && (popup.contains(related) || submenuRoot.contains(related))) {
                return;
            }
            this.closeSubmenu(popup, { focusToggle: false });
        });
    }

    directChild(root, selector) {
        return root
            ? Array.from(root.children).find((child) => child.matches?.(selector)) || null
            : null;
    }

    menuItems(popup) {
        if (!popup) {
            return [];
        }
        return Array.from(popup.querySelectorAll(".tv-menu-popup-item")).filter((item) => (
            item.closest(".tv-menu-popup") === popup
            && !item.disabled
            && item.getAttribute("aria-disabled") !== "true"
            && !item.classList.contains("is-disabled")
        ));
    }

    menuMnemonic(element) {
        const hotkey = element ? element.querySelector(".tv-hotkey") : null;
        return hotkey ? hotkey.textContent.trim().toLowerCase() : "";
    }

    markSelected(item, focus = true) {
        if (!item) {
            return;
        }
        this.root.querySelectorAll(".tv-menu-popup-item.is-menu-selected").forEach((current) => {
            current.classList.remove("is-menu-selected");
            current.tabIndex = -1;
        });
        item.classList.add("is-menu-selected");
        item.tabIndex = 0;
        this.activePopup = item.closest(".tv-menu-popup") || this.activePopup;
        if (this.activePopup) {
            this.lastSelection.set(this.activePopup, item);
        }
        if (focus) {
            item.focus({ preventScroll: true });
            item.scrollIntoView({ block: "nearest" });
        }
    }

    selectByIndex(popup, index) {
        const items = this.menuItems(popup);
        if (!items.length) {
            return null;
        }
        const normalized = (index + items.length) % items.length;
        this.markSelected(items[normalized]);
        return items[normalized];
    }

    moveSelection(delta) {
        const popup = this.activePopup || this.activeRoot?.querySelector("[data-tv-menu-popup]");
        const items = this.menuItems(popup);
        if (!items.length) {
            return;
        }
        const current = items.indexOf(document.activeElement);
        this.selectByIndex(popup, current < 0 ? (delta > 0 ? 0 : items.length - 1) : current + delta);
    }

    openMenu(menuRoot, { focusFirst = true } = {}) {
        const popup = menuRoot?.querySelector("[data-tv-menu-popup]");
        const toggle = menuRoot?.querySelector("[data-tv-menu-toggle]");
        if (!popup || !toggle) {
            return;
        }
        const savedFocus = this.previousFocus
            || (document.activeElement instanceof HTMLElement ? document.activeElement : null);
        this.closeMenus({ restoreFocus: false, preservePreviousFocus: true });
        this.previousFocus = savedFocus;
        popup.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        toggle.classList.add("is-current");
        this.activeRoot = menuRoot;
        this.activePopup = popup;
        requestAnimationFrame(() => {
            fitMenuPopupToViewport(menuRoot, popup);
            fillBorders(popup);
            if (focusFirst) {
                const remembered = this.lastSelection.get(popup);
                if (remembered && this.menuItems(popup).includes(remembered)) {
                    this.markSelected(remembered);
                } else {
                    this.selectByIndex(popup, 0);
                }
            }
        });
    }

    openSubmenu(toggle, { focusFirst = true } = {}) {
        const submenuRoot = toggle?.closest("[data-tv-submenu-root]");
        const popup = this.directChild(submenuRoot, "[data-tv-submenu-popup]");
        if (!submenuRoot || !popup) {
            return false;
        }
        this.closeSubmenusOutsidePath(submenuRoot, popup);
        popup.hidden = false;
        toggle.classList.add("is-submenu-open");
        toggle.setAttribute("aria-expanded", "true");
        this.activePopup = popup;
        requestAnimationFrame(() => {
            fitMenuPopupToViewport(submenuRoot, popup);
            fillBorders(popup);
            if (focusFirst) {
                const remembered = this.lastSelection.get(popup);
                if (remembered && this.menuItems(popup).includes(remembered)) {
                    this.markSelected(remembered);
                } else {
                    this.selectByIndex(popup, 0);
                }
            }
        });
        return true;
    }

    closeSubmenu(popup, { focusToggle = true } = {}) {
        if (!popup) {
            return;
        }
        const submenuRoot = popup.closest("[data-tv-submenu-root]");
        const toggle = this.directChild(submenuRoot, "[data-tv-submenu-toggle]");
        popup.querySelectorAll("[data-tv-submenu-popup]").forEach((child) => {
            if (child !== popup) { this.closeSubmenu(child, { focusToggle: false }); }
        });
        popup.hidden = true;
        resetMenuPopupLayout(popup);
        if (toggle) {
            toggle.classList.remove("is-submenu-open");
            toggle.setAttribute("aria-expanded", "false");
        }
        this.activePopup = toggle?.closest(".tv-menu-popup") || null;
        if (focusToggle && toggle) {
            this.markSelected(toggle);
        }
    }

    closeSubmenusOutsidePath(submenuRoot, activePopup) {
        this.root.querySelectorAll("[data-tv-submenu-popup]").forEach((popup) => {
            if (popup === activePopup || popup.contains(submenuRoot)) {
                return;
            }
            this.closeSubmenu(popup, { focusToggle: false });
        });
    }

    closeSubmenus() {
        this.root.querySelectorAll("[data-tv-submenu-popup]").forEach((popup) => {
            this.closeSubmenu(popup, { focusToggle: false });
        });
    }

    closeMenus({ restoreFocus = true, preservePreviousFocus = false } = {}) {
        const focusTarget = this.previousFocus;
        this.closeSubmenus();
        this.menuRoots.forEach((menuRoot) => {
            const popup = menuRoot.querySelector("[data-tv-menu-popup]");
            const toggle = menuRoot.querySelector("[data-tv-menu-toggle]");
            if (popup) {
                popup.hidden = true;
                resetMenuPopupLayout(popup);
            }
            if (toggle) {
                toggle.setAttribute("aria-expanded", "false");
                toggle.classList.remove("is-current");
            }
        });
        this.root.querySelectorAll(".tv-menu-popup-item.is-menu-selected").forEach((item) => {
            item.classList.remove("is-menu-selected");
            item.tabIndex = -1;
        });
        this.activeRoot = null;
        this.activePopup = null;
        if (!preservePreviousFocus) {
            this.previousFocus = null;
        }
        if (restoreFocus && focusTarget?.isConnected && typeof focusTarget.focus === "function") {
            focusTarget.focus({ preventScroll: true });
        }
    }

    switchRoot(delta) {
        if (!this.menuRoots.length) {
            return;
        }
        const current = this.menuRoots.indexOf(this.activeRoot);
        const index = current < 0 ? 0 : (current + delta + this.menuRoots.length) % this.menuRoots.length;
        this.openMenu(this.menuRoots[index]);
    }

    activateMnemonic(key) {
        const mnemonic = String(key || "").toLowerCase();
        const item = this.menuItems(this.activePopup).find((candidate) => this.menuMnemonic(candidate) === mnemonic);
        if (!item) {
            return false;
        }
        this.markSelected(item);
        if (item.matches("[data-tv-submenu-toggle]")) {
            this.openSubmenu(item);
        } else {
            item.click();
        }
        return true;
    }

    activateKeyCode(keyCode) {
        if (!keyCode) { return false; }
        const item = Array.from(this.root.querySelectorAll(`[data-tv-key-code="${keyCode}"]`))
            .find((candidate) => !candidate.disabled && candidate.getAttribute("aria-disabled") !== "true");
        if (!item) { return false; }
        item.click();
        if (this.activeRoot) { this.closeMenus(); }
        return true;
    }

    onKeyDown(event) {
        if (event.defaultPrevented) {
            return;
        }
        if (this.activateKeyCode(getKeyCode(event))) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        const plainF10 = event.key === "F10" && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
        if (plainF10) {
            event.preventDefault();
            if (this.activeRoot) {
                this.closeMenus();
            } else if (this.menuRoots.length) {
                this.openMenu(this.menuRoots[0]);
            }
            return;
        }
        if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.length === 1) {
            const root = this.menuRoots.find((candidate) => {
                const toggle = candidate.querySelector("[data-tv-menu-toggle]");
                return this.menuMnemonic(toggle) === event.key.toLowerCase();
            });
            if (root) {
                event.preventDefault();
                this.openMenu(root);
                return;
            }
            const action = this.topLevelActions.find((candidate) => (
                this.menuMnemonic(candidate) === event.key.toLowerCase()
            ));
            if (action) {
                event.preventDefault();
                this.closeMenus({ restoreFocus: false });
                action.click();
                return;
            }
        }
        if (!this.activeRoot) {
            if (this.onUnhandledKeyDown) {
                this.onUnhandledKeyDown(event);
            } else if (this.commandTarget instanceof TVView) {
                this.commandTarget.dispatchEvent(new TVEvent(evKeyDown, {
                    infoPtr: this.commandTarget,
                    nativeEvent: event,
                }));
            } else {
                this.commandTarget?.handleEvent?.(new TVEvent(evKeyDown, {
                    infoPtr: this.commandTarget,
                    nativeEvent: event,
                }));
            }
            return;
        }
        if (event.key === "Escape") {
            event.preventDefault();
            if (this.activePopup?.matches("[data-tv-submenu-popup]")) {
                this.closeSubmenu(this.activePopup);
            } else {
                this.closeMenus();
            }
            return;
        }
        if (event.key === "ArrowDown" || (event.key === "Tab" && !event.shiftKey)) {
            event.preventDefault();
            this.moveSelection(1);
            return;
        }
        if (event.key === "ArrowUp" || (event.key === "Tab" && event.shiftKey)) {
            event.preventDefault();
            this.moveSelection(-1);
            return;
        }
        if (event.key === "Home" || event.key === "End") {
            event.preventDefault();
            const items = this.menuItems(this.activePopup);
            this.selectByIndex(this.activePopup, event.key === "Home" ? 0 : items.length - 1);
            return;
        }
        if (event.key === "ArrowRight") {
            event.preventDefault();
            const current = document.activeElement;
            if (current?.matches?.("[data-tv-submenu-toggle]") && this.openSubmenu(current)) {
                return;
            }
            this.switchRoot(1);
            return;
        }
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            if (this.activePopup?.matches("[data-tv-submenu-popup]")) {
                this.closeSubmenu(this.activePopup);
            } else {
                this.switchRoot(-1);
            }
            return;
        }
        if (event.key === "Enter" || event.key === " ") {
            const current = document.activeElement;
            if (this.menuItems(this.activePopup).includes(current)) {
                event.preventDefault();
                if (current.matches("[data-tv-submenu-toggle]")) {
                    this.openSubmenu(current);
                } else {
                    current.click();
                }
            }
            return;
        }
        if (!event.altKey && !event.ctrlKey && !event.metaKey && event.key.length === 1 && this.activateMnemonic(event.key)) {
            event.preventDefault();
        }
    }

    destroy() {
        this.closeMenus({ restoreFocus: false });
        document.removeEventListener("click", this.onDocumentClick);
        document.removeEventListener("click", this.onDocumentCommand);
        document.removeEventListener("keydown", this.onDocumentKeyDown);
    }
}

let tvChoiceGroupId = 0;

class TVCluster extends TVView {
    constructor(bounds, options = []) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVCluster expects TVRect bounds");
        }
        super(bounds);
        this.options = Array.isArray(options) ? options : [];
        this.value = 0;
        this.sel = 0;
        this.enableMask = this.options.reduce((mask, _option, index) => mask | (1 << index), 0);
        this.eventMask |= evBroadcast;
        this.type = "checkbox";
        this.itemClass = "tv-checkbox-item";
        this.itemAttr = "data-tv-checkbox-index";
        this.markClass = "tv-checkbox-mark";
    }

    draw() {
        const items = this.options.map((option, index) => {
            const inputAttrs = attrsToString({
                type: this.type,
                class: "tv-choice-input",
                name: this.type === "radio" ? this.viewId : null,
                value: option.value !== undefined ? option.value : index,
                checked: Boolean(option.checked),
                disabled: Boolean(option.disabled),
            });
            const className = `${this.itemClass}${option.disabled ? " is-disabled" : ""}`;
            return `<label class="${className}" ${this.itemAttr}="${index}"><input ${inputAttrs}><span class="${this.markClass}" aria-hidden="true"></span> <span class="tv-choice-label">${renderHotkeyMarkup(option.label || "")}</span></label>`;
        }).join("");
        const attrs = attrsToString(this._drawAttrs());
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        return `<div${style} ${attrs}>${items}</div>`;
    }

    buttonState(item) { return (this.enableMask & (1 << item)) !== 0; }

    mark(item) {
        return this.type === "radio" ? this.value === item : (this.value & (1 << item)) !== 0;
    }

    movedTo(item) {
        if (Number.isInteger(item) && item >= 0 && item < this.options.length) { this.sel = item; }
    }

    press(item) {
        if (!this.buttonState(item)) { return; }
        this.movedTo(item);
        if (this.type === "radio") { this.value = item; }
        else { this.value ^= 1 << item; }
        this.syncInputs();
    }

    setButtonState(mask, enable) {
        this.enableMask = enable ? (this.enableMask | mask) : (this.enableMask & ~mask);
        this.syncInputs();
    }

    getData() { return this.value; }

    setData(value) {
        this.value = Math.max(0, Number(value) || 0);
        this.syncInputs();
        return this;
    }

    syncInputs() {
        if (!this.root) { return; }
        Array.from(this.root.querySelectorAll(".tv-choice-input")).forEach((input, index) => {
            input.checked = this.mark(index);
            input.disabled = !this.buttonState(index) || Boolean(this.options[index]?.disabled);
            this.options[index].checked = input.checked;
        });
    }

    resolve(root) {
        super.resolve(root);
        this.options.forEach((option, index) => {
            if (option.checked) {
                this.value = this.type === "radio" ? index : (this.value | (1 << index));
            }
        });
        this.syncInputs();
        return this;
    }

    handleEvent(event) {
        if (event.what !== evBroadcast || event.nativeEvent?.type !== "change") { return; }
        const input = event.nativeEvent.target;
        if (!this.root?.contains(input) || !input.matches?.(".tv-choice-input")) { return; }
        const label = input.closest(`[${this.itemAttr}]`);
        const index = Number.parseInt(label?.getAttribute(this.itemAttr) || "", 10);
        if (!Number.isInteger(index)) { return; }
        this.movedTo(index);
        if (this.type === "radio") { this.value = index; }
        else if (input.checked) { this.value |= 1 << index; }
        else { this.value &= ~(1 << index); }
        this.syncInputs();
    }
}

class TVCheckBoxes extends TVCluster {
    constructor(bounds, options = []) {
        super(bounds, options);
    }
}

class TVRadioButtons extends TVCluster {
    constructor(bounds, options = []) {
        super(bounds, options);
        this.type = "radio";
        this.viewId = `tv-radio-${++tvChoiceGroupId}`;
        this.itemClass = "tv-radio-item";
        this.itemAttr = "data-tv-radio-index";
        this.markClass = "tv-radio-mark";
    }
}

class TVMultiCheckBoxes extends TVCluster {
    constructor(bounds, options = [], states = [" ", "X", "?"]) {
        super(bounds, options);
        this.type = "button";
        this.itemClass = "tv-multicheck-item";
        this.itemAttr = "data-tv-multicheck-index";
        this.markClass = "tv-multicheck-mark";
        this.states = Array.isArray(states) && states.length > 1
            ? states.map(String)
            : [" ", "X", "?"];
    }

    draw() {
        const items = this.options.map((option, index) => {
            const state = Math.max(0, Math.min(
                this.states.length - 1,
                Number.isInteger(option.state) ? option.state : 0,
            ));
            const ariaChecked = state === 0 ? "false" : (state === 1 ? "true" : "mixed");
            const attrs = attrsToString({
                type: "button",
                class: "tv-multicheck-button",
                disabled: Boolean(option.disabled),
                role: "checkbox",
                "aria-checked": ariaChecked,
                "data-tv-multicheck-state": state,
            });
            const className = `${this.itemClass}${option.disabled ? " is-disabled" : ""}`;
            return `<label class="${className}" ${this.itemAttr}="${index}"><button ${attrs}><span class="${this.markClass}" aria-hidden="true">[${escapeHtml(this.states[state])}]</span> <span class="tv-choice-label">${renderHotkeyMarkup(option.label || "")}</span></button></label>`;
        }).join("");
        const attrs = attrsToString(this._drawAttrs());
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        return `<div${style} ${attrs}>${items}</div>`;
    }

    cycle(index, button = null) {
        if (!Number.isInteger(index) || index < 0 || index >= this.options.length) { return; }
        const target = button || this._query(`[${this.itemAttr}="${index}"] [data-tv-multicheck-state]`);
        if (!target || target.disabled) { return; }
        const state = (Number.parseInt(target.dataset.tvMulticheckState || "0", 10) + 1) % this.states.length;
        target.dataset.tvMulticheckState = String(state);
        target.setAttribute("aria-checked", state === 0 ? "false" : (state === 1 ? "true" : "mixed"));
        const mark = target.querySelector(`.${this.markClass}`);
        if (mark) { mark.textContent = `[${this.states[state]}]`; }
        this.options[index].state = state;
        return state;
    }

    handleEvent(event) {
        if (event.what !== evMouseDown || event.nativeEvent?.type !== "click") { return; }
        const button = event.nativeEvent.target.closest?.("[data-tv-multicheck-state]");
        if (!button || button.disabled || !this.root?.contains(button)) { return; }
        const item = button.closest(`[${this.itemAttr}]`);
        const index = Number.parseInt(item?.getAttribute(this.itemAttr) || "", 10);
        const state = this.cycle(index, button);
        if (!Number.isInteger(state)) { return; }
        this.clearEvent(event);
        this.owner?.dispatchEvent(new TVEvent(evBroadcast, {
            command: "cluster-press",
            infoPtr: this,
            nativeEvent: event.nativeEvent,
        }));
    }
}

const bfNormal = 0x00;
const bfDefault = 0x01;
const bfLeftJust = 0x02;
const bfBroadcast = 0x04;

class TVButton extends TVView {
    constructor(bounds, title, command, flags = bfNormal) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVButton expects TVRect bounds");
        }
        super(bounds);
        this.title = String(title ?? "");
        this.command = String(command || "");
        this.commandData = {};
        this.value = true;
        this.flags = flags;
        this.disabled = false;
    }

    setCommandData(commandData = {}) {
        this.commandData = { ...commandData };
        return this;
    }

    setValue(value) {
        this.value = value;
        return this;
    }

    _drawParts() {
        const data = this.commandData || {};
        const plain = new Set([
            "file-open-history", "change-dir-history", "find-history",
            "file-open-scroll-left", "file-open-scroll-right",
            "ascii-code", "calendar-prev", "calendar-next", "color-index",
            "midi-track", "search-index", "mines-face", "ludo-player-mode", "ludo-piece",
        ]);
        const classes = [];
        if (["file-open-history", "change-dir-history", "find-history"].includes(this.command)) {
            classes.push("tv-file-open-history-button");
            if (this.command === "change-dir-history") { classes.push("tv-change-dir-history-button"); }
            if (this.command === "find-history") { classes.push("tv-find-history-button"); }
        } else if (this.command === "ascii-code") {
            classes.push("tv-ascii-cell");
        } else if (["calendar-prev", "calendar-next"].includes(this.command)) {
            classes.push("tv-calendar-arrow");
        } else if (["file-open-scroll-left", "file-open-scroll-right"].includes(this.command)) {
            classes.push("tv-file-open-scroll-button");
        } else if (this.command === "color-index") {
            classes.push("tv-color-cell");
        } else if (this.command === "midi-track") {
            classes.push("tv-midi-track");
        } else if (this.command === "search-index") {
            classes.push("tv-search-result");
        } else if (this.command === "mines-face") {
            classes.push("tv-mines-face");
        } else if (this.command === "ludo-player-mode") {
            classes.push("tv-ludo-player-toggle", `tv-ludo-${data.color || "red"}`);
        } else if (this.command === "ludo-piece") {
            classes.push(...String(data.classes || "").split(/\s+/).filter(Boolean));
        } else if (this.command === "mastermind-color") {
            classes.push("tv-mastermind-color", `tv-mastermind-color-${data.color ?? 0}`);
        }
        if (data.selected) { classes.push("is-selected"); }
        const historyCommand = ["file-open-history", "change-dir-history", "find-history"].includes(this.command);
        const labels = {
            "file-open-scroll-left": displayCp437Char(17),
            "file-open-scroll-right": displayCp437Char(16),
            "calendar-prev": displayCp437Char(30),
            "calendar-next": displayCp437Char(31),
            "ludo-piece": "♟",
        };
        let labelMarkup = renderHotkeyMarkup(labels[this.command] ?? this.title);
        if (historyCommand) {
            labelMarkup = [
                '<span class="tv-file-open-history-side" aria-hidden="true">▐</span>',
                '<span class="tv-file-open-history-arrow" aria-hidden="true">↓</span>',
                '<span class="tv-file-open-history-side" aria-hidden="true">▌</span>',
            ].join("");
        } else if (this.command === "ascii-code") {
            labelMarkup = escapeHtml(displayCp437Char(this.value));
        } else if (this.command === "color-index") {
            const full = escapeHtml(displayCp437Char(219));
            labelMarkup = data.selected
                ? `${full}<span class="tv-color-cell-marker">${escapeHtml(displayCp437Char(8))}</span>${full}`
                : full.repeat(3);
        } else if (this.command === "midi-track") {
            labelMarkup = [
                `<span class="tv-midi-track-index">${escapeHtml(String(data.index + 1).padStart(2, "0"))}</span>`,
                `<span class="tv-midi-track-title">${escapeHtml(data.title || "")}</span>`,
                `<span class="tv-midi-track-credit">${escapeHtml(data.credit || "")}</span>`,
            ].join("");
        } else if (this.command === "search-index") {
            labelMarkup = [
                ["tv-search-result-title", data.title],
                ["tv-search-result-meta", data.meta],
                ["tv-search-result-preview", data.preview],
            ].map(([className, text]) => `<span class="${className}">${escapeHtml(text || "")}</span>`).join("");
        } else if (this.command === "ludo-piece") {
            labelMarkup = '<span class="tv-ludo-piece-glyph">♟</span>';
        }
        const ariaLabels = {
            "file-open-history": "History",
            "change-dir-history": "Directory history",
            "find-history": "Find history",
            "calendar-prev": "Previous month",
            "calendar-next": "Next month",
        };
        const tooltips = {
            "midi-previous": "Previous track",
            "midi-pause": "Pause",
            "midi-next": "Next track",
        };
        return {
            dialog: !plain.has(this.command),
            baseClass: this.command === "calc-key"
                ? "tv-dialog-button tv-calc-button"
                : "tv-dialog-button",
            className: classes.join(" "),
            style: this.command === "color-index" && data.color
                ? `--tv-color-cell:${data.color}`
                : "",
            labelMarkup,
            ariaLabel: ariaLabels[this.command]
                || (this.command === "ascii-code" ? `ASCII ${this.value}` : "")
                || (this.command === "calc-key" ? `Calculator key ${data.description || this.title}` : "")
                || (this.command === "color-index" ? `Color ${this.value}` : "")
                || (this.command === "ludo-player-mode" ? `${data.playerName || this.title} player mode` : "")
                || (this.command === "ludo-piece" ? `${data.playerName || "Ludo"} piece ${Number(this.value) + 1}` : ""),
            ariaExpanded: historyCommand || this.command === "midi-more" ? Boolean(data.expanded) : null,
            ariaPressed: this.command === "color-index" ? Boolean(data.selected) : null,
            tabIndex: ["file-open-scroll-left", "file-open-scroll-right"].includes(this.command)
                ? -1
                : (this.command === "color-index" ? (data.selected ? 0 : -1) : null),
            tooltip: tooltips[this.command] || data.description || "",
        };
    }

    draw() {
        const parts = this._drawParts();
        const attrString = attrsToString(this._drawAttrs({
            type: "button",
            ...TVView._controlAttrs({
                name: this.command,
                value: this.value,
                command: this.command,
                commandData: this.commandData,
                disabled: this.disabled,
                hidden: !this.getState(sfVisible),
                ariaLabel: parts.ariaLabel,
                ariaExpanded: parts.ariaExpanded,
                ariaPressed: parts.ariaPressed,
                tabIndex: parts.tabIndex,
                tooltip: parts.tooltip,
            }),
        }));
        const classNames = [parts.className, (this.flags & bfDefault) !== 0 ? "is-default" : ""].filter(Boolean).join(" ");
        const bounds = TVView._viewBoundsStyle(this);
        const inlineStyle = [bounds, parts.style].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const labelMarkup = parts.labelMarkup;
        if (parts.dialog) {
            const buttonClass = [parts.baseClass, classNames].filter(Boolean).join(" ");
            const shadow = " " + "\u2580".repeat(20);
            return `
                <button class="${buttonClass}"${styleAttr} ${attrString}>
                    <span class="tv-dialog-button-face">
                        <span class="tv-dialog-button-label">${labelMarkup}</span>
                        <span class="tv-dialog-button-edge" aria-hidden="true">▄</span>
                    </span>
                    <span class="tv-dialog-button-shadow" aria-hidden="true">${shadow}</span>
                </button>
            `;
        }
        const classAttr = classNames ? ` class="${classNames}"` : "";
        const attrs = attrString ? ` ${attrString}` : "";
        return `<button${classAttr}${styleAttr}${attrs}>${labelMarkup}</button>`;
    }

    handleEvent(event) {
        if (event.what === evMouseDown && this.command && !this.disabled) {
            event.what = evCommand;
            event.command = this.command;
            event.infoPtr = this;
        }
    }

    setTitle(title) {
        this.title = String(title ?? "");
        const label = this._query(".tv-dialog-button-label");
        if (label) { label.innerHTML = this._drawParts().labelMarkup; }
        else if (this.root) { this.root.innerHTML = this._drawParts().labelMarkup; }
        return this;
    }

    makeDefault(enable = true) {
        this.flags = enable ? (this.flags | bfDefault) : (this.flags & ~bfDefault);
        this.root?.classList.toggle("is-default", Boolean(enable));
        return this;
    }

    drawState(down) {
        this.root?.classList.toggle("is-pressed", Boolean(down));
        return this;
    }

    press() {
        if (this.root && !this.root.disabled) { this.root.click(); }
    }

    setState(state, enable) {
        if ((state & sfDisabled) !== 0) {
            this.disabled = Boolean(enable);
            if (this.root) { this.root.disabled = Boolean(enable); }
        }
        return super.setState(state, enable);
    }
}

class TVFrame extends TVView {
    constructor(bounds) {
        super(bounds);
        this.frameMode = 0;
    }

    getTitleWidth() {
        return this.owner instanceof TVWindow ? Array.from(this.owner.getTitle()).length : 0;
    }

    getPalette() { return this.owner?.getPalette?.() ?? null; }

    drawTitle() {
        const title = this.owner?.getTitle?.() || "";
        const element = this.owner?.root?.querySelector?.(".tv-dialog-title-text, .tv-window-caption");
        if (element) { element.textContent = title; }
        return this;
    }

    frameLine(y, width = this.size.x) {
        const top = Number(y) <= 0;
        const bottom = Number(y) >= Math.max(0, this.size.y - 1);
        if (top || bottom) {
            return `${top ? "╔" : "╚"}${"═".repeat(Math.max(0, width - 2))}${top ? "╗" : "╝"}`;
        }
        return `║${" ".repeat(Math.max(0, width - 2))}║`;
    }

    draw() {
        const rows = [];
        for (let y = 0; y < Math.max(0, this.size.y); y += 1) {
            rows.push(this.frameLine(y));
        }
        return rows.join("\n");
    }

    handleEvent(event) {
        if (event.what !== evCommand || !(this.owner instanceof TVWindow)) { return; }
        if (event.command === "close" && (this.owner.flags & wfClose) !== 0) {
            this.owner.close();
            this.clearEvent(event);
        } else if (event.command === "zoom" && (this.owner.flags & wfZoom) !== 0) {
            this.owner.zoom();
            this.clearEvent(event);
        }
    }

    setState(state, enable) {
        super.setState(state, enable);
        if ((state & (sfActive | sfDragging)) !== 0) { this.drawView(); }
        return this;
    }

    drawTitleControl(command, glyph, title = "") {
        const ownerName = String(this.owner?.constructor?.viewName || "dialog")
            .replace(/[^a-zA-Z0-9_-]/g, "-");
        const definitions = {
            "window-close": {
                classes: "tv-close-control",
                glyphClass: "tv-close-glyph",
                attrs: { "data-tv-close-button": true },
                glyphAttrs: { "data-tv-close-glyph": true },
            },
            "window-zoom": {
                classes: "tv-zoom-control",
                glyphClass: "tv-zoom-glyph",
                attrs: {},
                glyphAttrs: { "data-tv-zoom-glyph": true },
            },
            "dialog-close": {
                classes: `tv-dialog-title-control tv-dialog-close-control tv-${ownerName}-close-control`,
                glyphClass: "tv-dialog-title-control-glyph tv-close-glyph",
                attrs: {
                    "data-tv-close-button": true,
                    [`data-tv-${ownerName}-close`]: true,
                },
                glyphAttrs: { "data-tv-close-glyph": true },
            },
            "hall-of-fame": {
                classes: "tv-dialog-title-control tv-game-hall-control",
                glyphClass: "tv-dialog-title-control-glyph tv-game-hall-glyph",
                attrs: {},
                glyphAttrs: {},
            },
        };
        const definition = definitions[command];
        if (!definition) { throw new Error(`Unknown TFrame title command: ${command}`); }
        const attrString = attrsToString({
            type: "button",
            "data-tv-command": command,
            "aria-label": title || command,
            ...definition.attrs,
        });
        const glyphAttrString = attrsToString(definition.glyphAttrs);
        return `<button class="${definition.classes}" ${attrString}>[<span class="${definition.glyphClass}" ${glyphAttrString}>${escapeHtml(glyph)}</span>]</button>`;
    }

    createTitleControl(command, glyph, title = "") {
        return TVView._fromHTML(this.drawTitleControl(command, glyph, title));
    }

    drawDialog(bodyMarkup = "", footerMarkup = "", bodyBorders = true) {
        const dialog = this.owner;
        const viewName = String(dialog?.constructor?.viewName || "dialog").replace(/[^a-zA-Z0-9_-]/g, "-");
        const classPrefix = `tv-${viewName}`;
        const modal = dialog?.getState?.(sfModal) || false;
        const palette = dialog?.getPalette?.() || "dialog";
        const overlayClasses = ["tv-dialog-overlay", modal ? "is-modal" : "", `${classPrefix}-overlay`].filter(Boolean).join(" ");
        const windowClasses = `tv-dialog-window ${classPrefix}-window`;
        const titlebarClasses = `tv-dialog-titlebar ${classPrefix}-titlebar`;
        const footerClasses = `tv-dialog-footer ${classPrefix}-footer`;
        const titleClasses = `tv-dialog-title-text ${classPrefix}-title`;
        const bodyClasses = `tv-dialog-body ${classPrefix}-body`;
        const renderBody = (value) => (
            value instanceof TVView
                ? value.draw()
                : String(value ?? "")
        );
        let bodyContent;
        if (Array.isArray(bodyMarkup)) {
            const side = '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
            const sep = '<span class="tv-border-corner" aria-hidden="true">╟</span>'
                + '<span class="tv-border-fill tv-border-separator" data-tv-border-fill="─" aria-hidden="true"></span>'
                + '<span class="tv-border-corner" aria-hidden="true">╢</span>';
            bodyContent = bodyMarkup.map(section => side + renderBody(section) + side).join(sep);
        } else if (bodyBorders) {
            bodyContent = '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>'
                + `<div class="tv-dialog-client">${renderBody(bodyMarkup)}</div>`
                + '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
        } else {
            bodyContent = renderBody(bodyMarkup);
        }
        return `
            <div class="${overlayClasses}" hidden>
                <div class="${windowClasses}" data-tv-palette="${escapeHtml(palette)}" role="dialog" aria-modal="${modal ? "true" : "false"}" aria-label="${escapeHtml(dialog?.title || "")}">
                    <div class="${titlebarClasses}">
                        <span class="tv-border-corner" aria-hidden="true">╔</span>
                        <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
                        <span class="tv-border-corner" aria-hidden="true">╗</span>
                        ${this.drawTitleControl("dialog-close", "■", `Close ${dialog?.title || "dialog"}`)}
                        <div class="${titleClasses}">${escapeHtml(dialog?.title || "")}</div>
                    </div>
                    <div class="${bodyClasses}">${bodyContent}</div>
                    <div class="${footerClasses}">${footerMarkup}</div>
                </div>
            </div>
        `;
    }
}

class TVWindow extends TVGroup {
    constructor(bounds, title = "", number = 0) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVWindow expects TVRect bounds");
        }
        super(bounds);
        this.title = String(title ?? "");
        this.number = Number(number) === wnNoNumber ? 0 : (Number(number) || 0);
        this.flags = wfMove | wfGrow | wfClose | wfZoom;
        this.state |= sfShadow;
        this.options |= ofSelectable | ofTopSelect;
        this.growMode = gfGrowAll | gfGrowRel;
        this.zoomRect = bounds.copy();
        this.maxiRect = bounds.copy();
        this.minSize = new TVPoint(16, 6);
        this.palette = new.target.palette || 0;
        this.frame = this.initFrame();
        this.closeAction = null;
        this.zoomAction = null;
        this.onWindowControlMouseDown = (event) => {
            if (event.button !== 0 || !event.target.closest("[data-tv-command='window-close']")) { return; }
            this.dispatchWindowControl(event);
        };
        this.onWindowControlClick = (event) => this.dispatchWindowControl(event);
    }

    bindRoot(root) {
        if (this.root?.matches?.("[data-tv-window]")) {
            this.root.removeEventListener("mousedown", this.onWindowControlMouseDown);
            this.root.removeEventListener("click", this.onWindowControlClick);
        }
        super.bindRoot(root);
        if (this.root?.matches?.("[data-tv-window]")) {
            this.root.addEventListener("mousedown", this.onWindowControlMouseDown);
            this.root.addEventListener("click", this.onWindowControlClick);
        }
        return this;
    }

    dispatchWindowControl(nativeEvent) {
        const control = nativeEvent.target?.closest?.("[data-tv-command]");
        if (!control || !this.root?.contains(control)) { return; }
        const command = control.dataset.tvCommand || "";
        if (command !== "window-close" && command !== "window-zoom") { return; }
        nativeEvent.preventDefault();
        nativeEvent.stopPropagation();
        if (nativeEvent.type === "mousedown" && command === "window-close") {
            nativeEvent.stopImmediatePropagation();
        }
        this.dispatchEvent(new TVEvent(evCommand, { command, infoPtr: this, nativeEvent }));
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "window-close") {
            if (typeof this.closeAction === "function") { this.closeAction(); }
            else { this.close(); }
            this.clearEvent(event);
        } else if (event.command === "window-zoom") {
            if (typeof this.zoomAction === "function") { this.zoomAction(); }
            else { this.zoom(); }
            this.clearEvent(event);
        }
    }

    initFrame() {
        const frame = new TVFrame(this.getExtent());
        frame.owner = this;
        return frame;
    }

    getTitle(maxSize = Number.MAX_SAFE_INTEGER) {
        return Array.from(this.title).slice(0, Math.max(0, Number(maxSize) || 0)).join("");
    }

    getPalette() { return this.palette; }

    standardScrollBar(options = 0) {
        const vertical = (options & sbVertical) !== 0;
        const extent = this.getExtent();
        const bounds = vertical
            ? new TVRect(Math.max(0, extent.x2 - 1), 1, extent.x2, Math.max(1, extent.y2 - 1))
            : new TVRect(1, Math.max(0, extent.y2 - 1), Math.max(1, extent.x2 - 1), extent.y2);
        const scrollBar = new TVScrollBar(bounds, options);
        this.insert(scrollBar);
        return scrollBar;
    }

    close() { this.hide(); }

    zoom() {
        this.root?.classList.toggle("is-maximized");
        return this;
    }

    sizeLimits() {
        return {
            min: this.minSize.copy(),
            max: new TVPoint(Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER),
        };
    }

    draw(contentMarkup = this.renderChildren()) {
        const limits = this.sizeLimits();
        const semanticName = this._semanticName();
        const windowAttrs = attrsToString(this._drawAttrs({
            "data-tv-window": true,
            ...(semanticName ? { [`data-tv-${semanticName}`]: true } : {}),
            hidden: !this.getState(sfVisible),
        }));
        const growable = (this.flags & wfGrow) !== 0;
        const windowClasses = [
            "tv-window",
            TVView._roleClassNames(this._drawRole()),
            growable ? "is-growable" : "is-fixed-window",
        ].filter(Boolean).join(" ");
        const framePlaceholder = '<span class="tv-border-fill tv-frame-control-placeholder" data-tv-border-fill="═" aria-hidden="true"></span>';
        const closeControl = (this.flags & wfClose) !== 0
            ? this.frame.drawTitleControl("window-close", "■", "Close window")
            : framePlaceholder;
        const zoomControl = (this.flags & wfZoom) !== 0
            ? this.frame.drawTitleControl("window-zoom", "↑", "Zoom window")
            : framePlaceholder;
        const title = this.getTitle();
        const titleMarkup = title
            ? `<div class="tv-window-caption">${escapeHtml(title)}</div>`
            : '<span class="tv-border-fill tv-window-caption-fill" data-tv-border-fill="═" aria-hidden="true"></span>';
        const rightFrame = growable
            ? new TVScrollBar(new TVRect(), sbVertical).draw()
            : '<span class="tv-border-side tv-border-side-right" data-tv-border-side="║" aria-hidden="true"></span>';
        const bottomFrame = growable
            ? [
                '<span class="tv-scroll-corner tv-scroll-corner-left" data-tv-frame-corner="bl" aria-hidden="true">╚</span>',
                '<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>',
                new TVScrollBar(new TVRect(), sbHorizontal).draw(),
                '<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>',
            ].join("")
            : [
                '<span class="tv-scroll-corner tv-scroll-corner-left" data-tv-frame-corner="bl" aria-hidden="true">╚</span>',
                '<span class="tv-border-fill tv-fixed-bottom-fill" data-tv-border-fill="═" aria-hidden="true"></span>',
                '<span class="tv-scroll-corner tv-scroll-corner-right" data-tv-frame-corner="br" aria-hidden="true">╝</span>',
            ].join("");
        const style = [
            this.size.x ? `--tv-window-cols:${this.size.x}` : "",
            this.size.y ? `--tv-window-rows:${this.size.y}` : "",
            limits.min.x ? `--tv-window-min-cols:${limits.min.x}` : "",
            limits.min.y ? `--tv-window-min-rows:${limits.min.y}` : "",
        ].filter(Boolean).join(";");
        const styleAttr = style ? ` style="${escapeHtml(style)}"` : "";
        return [
            `<main class="${escapeHtml(windowClasses)}" ${windowAttrs}${styleAttr}>`,
            `<div class="tv-shell">`,
            `<div class="tv-border-row tv-border-top" data-tv-move-handle>`,
            `<span class="tv-border-corner tv-border-corner-tl" data-tv-frame-corner="tl" aria-hidden="true">╔</span>`,
            `<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>`,
            closeControl,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            titleMarkup,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            zoomControl,
            `<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<span class="tv-border-corner tv-border-corner-tr" data-tv-frame-corner="tr" aria-hidden="true">╗</span>`,
            `</div>`,
            `<div class="tv-client-row">`,
            `<span class="tv-border-side tv-border-side-left" data-tv-border-side="║" aria-hidden="true"></span>`,
            `<div class="tv-frame"><div class="tv-scroll-shell" data-tv-scroll-frame>`,
            `<div class="tv-viewport" data-tv-viewport>${contentMarkup}</div>`,
            `</div></div>`,
            rightFrame,
            `<div class="tv-bottom-bar">`,
            bottomFrame,
            `</div>`,
            `</div>`,
            `</div>`,
            `</main>`,
        ].join("");
    }
}

class TVDialog extends TVWindow {
    static viewName = "dialog";
    static palette = "dialog";

    static footerMarkup() {
        return `
            <span class="tv-border-corner" aria-hidden="true">╚</span>
            <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
            <span class="tv-border-corner" aria-hidden="true">╝</span>
        `;
    }

    constructor(bounds, title) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVDialog expects TVRect bounds");
        }
        super(bounds, title);
        this.flags = wfMove | wfClose;
        this.growMode = 0;
        const root = TVView._fromHTML(this.frame.drawDialog("", TVDialog.footerMarkup()));
        this.bindRoot(root);
        this.setHelpCtx(hcDialog);
        this.content = null;
        this.overlay = root;
        this.dialog = this._query(".tv-dialog-window");
        setElementHelpContext(this.dialog, this.helpCtx);
        this.titlebar = this._query(".tv-dialog-titlebar");
        this.closeButton = this._query(".tv-dialog-close-control");
        if (bounds.width) this.dialog.style.setProperty("--tv-dialog-width", `${bounds.width}ch`);
        if (bounds.height) this.dialog.style.setProperty("--tv-dialog-height", `${bounds.height}em`);
        this.hasPosition = false;
        this.dragState = null;
        this.manager = null;
        this.managerName = "";
        this.modal = false;
        this.keyboard = true;
        this.escapeCloses = true;
        this.previousFocus = null;
        this.destroyed = false;
        this.closeAction = () => this.close();
        this.dialog.tabIndex = -1;
        bindCloseButtons(this.overlay);
        this.dialog.addEventListener("mousedown", (event) => {
            if (event.button !== 0 || !event.target.closest("[data-tv-command='dialog-close']")) { return; }
            this.dispatchDomEvent(evMouseDown, event);
        });
        this.dialog.addEventListener("click", (event) => this.dispatchDomEvent(evMouseDown, event));
        this.dialog.addEventListener("contextmenu", (event) => this.dispatchDomEvent(evMouseDown, event));
        this.dialog.addEventListener("input", (event) => this.dispatchDomEvent(evBroadcast, event));
        this.dialog.addEventListener("change", (event) => this.dispatchDomEvent(evBroadcast, event));
        this.dialog.addEventListener("keydown", (event) => {
            this.dispatchDomEvent(evKeyDown, event);
            this.onDialogKeyDown(event);
        });
        this.dialog.addEventListener("keyup", (event) => this.onDialogKeyUp(event));
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evMouseDown && event.infoPtr === this) {
            const control = event.nativeEvent?.target?.closest?.("[data-tv-command]");
            if (control && this.dialog.contains(control)) {
                event.nativeEvent.preventDefault();
                event.nativeEvent.stopPropagation();
                event.what = evCommand;
                event.command = control.dataset.tvCommand || "";
            }
        }
        if (event.what === evCommand && event.command === "dialog-close") {
            this.closeAction();
            this.clearEvent(event);
        }
    }

    insert(view) {
        const inserted = super.insert(view);
        this.content = this.children.length === 1 ? this.children[0] : null;
        this.drawContent();
        return inserted;
    }

    draw() {
        const content = this.children.map((view) => view.draw()).join("");
        return this.frame.drawDialog(content, TVDialog.footerMarkup());
    }

    drawContent() {
        const body = this._query(".tv-dialog-body");
        if (!body) { return; }
        const render = (view) => view?.draw?.() || "";
        const side = '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
        if (this.children.length <= 1) {
            body.innerHTML = side
                + `<div class="tv-dialog-client">${this.children[0] ? render(this.children[0]) : ""}</div>`
                + side;
        } else {
            const separator = '<span class="tv-border-corner" aria-hidden="true">╟</span>'
                + '<span class="tv-border-fill tv-border-separator" data-tv-border-fill="─" aria-hidden="true"></span>'
                + '<span class="tv-border-corner" aria-hidden="true">╢</span>';
            body.innerHTML = this.children.map((view) => side + render(view) + side).join(separator);
        }
        this.children.forEach((view) => view.resolve?.(body));
        if (this.isOpen()) {
            updateWindowFrameState(this.dialog, this.isActive(), { dialog: true });
        }
    }

    setState(state, enable) {
        super.setState(state, enable);
        if ((state & sfModal) !== 0) {
            this.modal = Boolean(enable);
            this.overlay?.classList.toggle("is-modal", this.modal);
            this.dialog?.setAttribute("aria-modal", this.modal ? "true" : "false");
        }
        return this;
    }

    setHelpCtx(helpCtx) {
        super.setHelpCtx(helpCtx);
        setElementHelpContext(this.dialog, this.helpCtx);
        return this;
    }

    dispatchDomEvent(what, nativeEvent) {
        const target = TVView._fromElement(nativeEvent.target) || this;
        return target.dispatchEvent(new TVEvent(what, {
            infoPtr: target,
            nativeEvent,
        }));
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
        if (this.destroyed) {
            return;
        }
        if (!(this.owner instanceof TVDesktop) || !this.overlay.isConnected) {
            throw new Error("TVDialog must be inserted into TVDesktop before open()");
        }
        const wasOpen = this.isOpen();
        if (!wasOpen) {
            this.previousFocus = document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null;
        }
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
        const restoreFocus = this.previousFocus;
        this.previousFocus = null;
        this.overlay.hidden = true;
        if (this.manager && this.managerName) {
            this.manager.onDialogClosed(this.managerName);
        }
        if (restoreFocus && restoreFocus.isConnected && typeof restoreFocus.focus === "function") {
            try {
                restoreFocus.focus({ preventScroll: true });
            } catch {
                restoreFocus.focus();
            }
        }
    }

    destroy() {
        if (this.destroyed) {
            return;
        }
        if (this.isOpen()) {
            this.close();
        }
        document.removeEventListener("mousemove", this.onDragMove);
        document.removeEventListener("mouseup", this.onDragEnd);
        this.dragState = null;
        if (this.manager && this.managerName) {
            this.manager.unregister(this.managerName, this);
        }
        this.manager = null;
        this.managerName = "";
        this.owner?.remove?.(this);
        this.previousFocus = null;
        this.destroyed = true;
        this.overlay.remove();
    }

    focusableElements() {
        const selector = [
            "a[href]",
            "button:not([disabled])",
            "input:not([disabled])",
            "select:not([disabled])",
            "textarea:not([disabled])",
            '[tabindex]:not([tabindex="-1"])',
        ].join(",");
        return Array.from(this.dialog.querySelectorAll(selector)).filter((element) => (
            !element.hidden
            && !element.closest("[hidden]")
            && element.getAttribute("aria-hidden") !== "true"
        ));
    }

    onDialogKeyDown(event) {
        if (!this.keyboard || !this.isActive() || event.defaultPrevented) {
            return;
        }
        if (event.key === "Escape" && this.escapeCloses) {
            event.preventDefault();
            event.stopPropagation();
            this.closeAction();
            return;
        }
        if (
            event.key === "Enter"
            && !event.altKey
            && !event.ctrlKey
            && !event.metaKey
            && !event.shiftKey
            && !(event.target && event.target.closest("button, a, textarea, [contenteditable='true']"))
        ) {
            const defaultButton = this.firstThat((view) => (
                view instanceof TVButton
                && (view.flags & bfDefault) !== 0
                && !view.disabled
                && !view.hidden
            ));
            if (defaultButton?.root && !defaultButton.root.disabled) {
                event.preventDefault();
                event.stopPropagation();
                defaultButton.press();
                return;
            }
        }
        if (event.key === "Tab") {
            const focusable = this.focusableElements();
            if (focusable.length) {
                event.preventDefault();
                event.stopPropagation();
                const current = focusable.indexOf(document.activeElement);
                const next = event.shiftKey
                    ? (current <= 0 ? focusable.length - 1 : current - 1)
                    : (current < 0 || current === focusable.length - 1 ? 0 : current + 1);
                focusable[next].focus();
                return;
            }
        }
        if (this.modal) {
            event.stopPropagation();
        }
    }

    onDialogKeyUp(_event) {}

    center() {
        const width = this.dialog.offsetWidth;
        const height = this.dialog.offsetHeight;
        const left = Math.max(0, Math.floor((this.overlay.clientWidth - width) / 2));
        const top = Math.max(0, Math.floor((this.overlay.clientHeight - height) / 2));
        this.dialog.style.setProperty("--tv-dialog-left", `${left}px`);
        this.dialog.style.setProperty("--tv-dialog-top", `${top}px`);
    }

    changeBounds(bounds) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVDialog.changeBounds expects TVRect");
        }
        this.setBounds(bounds);
        this.dialog.style.setProperty("--tv-dialog-width", `${bounds.width}ch`);
        this.dialog.style.setProperty("--tv-dialog-height", `${bounds.height}em`);
        fillBorders(this.dialog);
        return this;
    }

    bindCommonClose(onClose = () => this.close()) {
        this.closeAction = onClose;
        if (!this._commonCloseBound) {
            this._commonCloseBound = true;
            this.overlay.addEventListener("click", (event) => {
                if (event.target === this.overlay) {
                    this.closeAction();
                }
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
        this.dialog.classList.add("is-dragging");
        updateWindowFrameState(this.dialog, true, { dialog: true });
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
        this.dialog.classList.remove("is-dragging");
        updateWindowFrameState(this.dialog, this.isActive(), { dialog: true });
        document.removeEventListener("mousemove", this.onDragMove);
        document.removeEventListener("mouseup", this.onDragEnd);
        if (this.manager && this.manager.onChange) {
            this.manager.onChange();
        }
    };
}

class TVDialogManager {
    constructor(desktop) {
        if (!(desktop instanceof TVDesktop)) {
            throw new TypeError("TVDialogManager expects TVDesktop");
        }
        this.desktop = desktop;
        this.root = desktop.root;
        this.dialogs = new Map();
        this.windows = new Map();
        this.windowCommands = new Map();
        this.stackOrder = [];
        this.baseZIndex = 10;
        this.hostWindow = this.root?.querySelector("[data-tv-window]") || null;
        this.activeTarget = HOST_WINDOW_TOKEN;
        this.onChange = null;
    }

    setHostWindow(element, commands = {}) {
        this.hostWindow = element || null;
        this.windowCommands.set(HOST_WINDOW_TOKEN, { ...commands });
        this.applyActiveStates();
    }

    activateHostWindow() {
        this.activeTarget = HOST_WINDOW_TOKEN;
        this.applyAllZIndices();
        this.applyActiveStates();
        if (this.onChange) { this.onChange(); }
    }

    registerWindow(name, element, commands = {}) {
        this.windows.set(name, element);
        this.windowCommands.set(name, { ...commands });
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
        this.windowCommands.delete(name);
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

    activateWindow(name) {
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        this.stackOrder.push(name);
        this.activeTarget = name;
        this.applyAllZIndices();
        this.applyActiveStates();
        if (this.onChange) { this.onChange(); }
    }

    register(name, dialog) {
        if (!(dialog instanceof TVDialog)) {
            throw new TypeError("TVDialogManager.register expects TVDialog");
        }
        if (dialog.owner !== this.desktop) {
            this.desktop.insert(dialog);
        }
        this.dialogs.set(name, dialog);
        if (dialog && typeof dialog.setManager === "function") {
            dialog.setManager(this, name);
        }
        this.installDialogHooks(name, dialog);
        return dialog;
    }

    unregister(name, dialog = null) {
        const registered = this.dialogs.get(name);
        if (!registered || (dialog && registered !== dialog)) {
            return false;
        }
        this.dialogs.delete(name);
        const wasStacked = this.stackOrder.includes(name);
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        const wasActive = this.activeTarget === name;
        if (wasActive) {
            this.activeTarget = this.stackOrder.length
                ? this.stackOrder[this.stackOrder.length - 1]
                : HOST_WINDOW_TOKEN;
        }
        if (wasStacked || wasActive) {
            this.applyAllZIndices();
            this.applyActiveStates();
            if (this.onChange) { this.onChange(); }
        }
        return true;
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

    getHelpCtx() {
        const target = this.activeTarget;
        if (target === HOST_WINDOW_TOKEN) {
            return elementHelpContext(this.hostWindow);
        }
        const dialog = this.dialogs.get(target);
        if (dialog?.dialog && dialog.isOpen()) {
            return elementHelpContext(dialog.dialog);
        }
        return elementHelpContext(this.windows.get(target));
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
        if (this.onChange) { this.onChange(); }
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

    cycleTarget(delta = 1) {
        const targets = this.openTargets();
        if (!targets.length) {
            return false;
        }
        const current = targets.indexOf(this.activeTarget);
        const start = current < 0 ? (delta > 0 ? -1 : 0) : current;
        const index = (start + delta + targets.length) % targets.length;
        const target = targets[index];
        const dialog = this.dialogs.get(target);
        if (dialog) {
            this.bringToFront(target);
        } else {
            this.activateWindow(target);
        }
        return true;
    }

    openTargets() {
        return this.stackOrder.filter((name) => {
            const dialog = this.dialogs.get(name);
            if (dialog) { return dialog.isOpen(); }
            const windowElement = this.windows.get(name);
            return Boolean(windowElement && windowElement.isConnected);
        });
    }

    openWindowCount() {
        return Array.from(this.windows.values()).filter((element) => element?.isConnected).length;
    }

    canDispatchCommand(command) {
        if (command === TV_COMMANDS.NEXT || command === TV_COMMANDS.PREVIOUS) {
            return this.openTargets().length > 1;
        }
        const target = this.activeTarget;
        const dialog = this.dialogs.get(target);
        if (dialog && dialog.isOpen()) {
            return command === TV_COMMANDS.CLOSE || command === TV_COMMANDS.CANCEL;
        }
        return typeof this.windowCommands.get(target)?.[command] === "function";
    }

    dispatchCommand(command) {
        if (command === TV_COMMANDS.NEXT) {
            if (!this.canDispatchCommand(command)) { return false; }
            return this.cycleTarget(1);
        }
        if (command === TV_COMMANDS.PREVIOUS) {
            if (!this.canDispatchCommand(command)) { return false; }
            return this.cycleTarget(-1);
        }
        const target = this.activeTarget;
        const dialog = this.dialogs.get(target);
        if (dialog && dialog.isOpen()) {
            if (command === TV_COMMANDS.CLOSE || command === TV_COMMANDS.CANCEL) {
                dialog.closeAction();
                return true;
            }
            if (typeof dialog.handleCommand === "function" && dialog.handleCommand(command)) {
                return true;
            }
            return false;
        }
        const handler = this.windowCommands.get(target)?.[command];
        if (typeof handler === "function") {
            handler();
            return true;
        }
        return false;
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

function resolveHelpContext({ root = document, menuController = null, dialogManager = null } = {}) {
    const menuContext = menuController?.getHelpCtx?.() || hcNoContext;
    if (menuContext !== hcNoContext) { return menuContext; }
    const focusContext = elementHelpContext(root.activeElement || document.activeElement);
    if (focusContext !== hcNoContext) { return focusContext; }
    const managedContext = dialogManager?.getHelpCtx?.() || hcNoContext;
    if (managedContext !== hcNoContext) { return managedContext; }
    const activeContext = elementHelpContext(root.querySelector?.(".is-window-active[data-tv-help-ctx]"));
    if (activeContext !== hcNoContext) { return activeContext; }
    return elementHelpContext(document.body) || hcApplication;
}

class TVHelpController {
    constructor({
        root = document,
        getMenuController = () => null,
        getDialogManager = () => null,
        onHelp = null,
    } = {}) {
        this.root = root;
        this.getMenuController = getMenuController;
        this.getDialogManager = getDialogManager;
        this.onHelp = onHelp;
        this.onKeyDown = (event) => {
            if (
                event.key !== "F1" || event.altKey || event.ctrlKey
                || event.metaKey || event.shiftKey || event.defaultPrevented
            ) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            this.request();
        };
        this.root.addEventListener("keydown", this.onKeyDown, true);
    }

    currentContext() {
        return resolveHelpContext({
            root: this.root,
            menuController: this.getMenuController(),
            dialogManager: this.getDialogManager(),
        });
    }

    request(helpCtx = null) {
        const context = helpCtx == null ? this.currentContext() : normalizeHelpContext(helpCtx, hcApplication);
        this.onHelp?.(context);
        return context;
    }

    destroy() {
        this.root.removeEventListener("keydown", this.onKeyDown, true);
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
//   this.msgBox = new TVMessageBox();
//   desktop.insert(this.msgBox);
//   const cmd = await this.msgBox.show({
//       title: "Game Over", lines: ["Score: 42"],
//       buttons: TVMessageBox.MF_OK_BUTTON,
//   });
//   // cmd === "ok"

class TVMessageBox extends TVDialog {
    static viewName = "msgbox";

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
        { flag: 0x0100, cmd: "yes",    label: "~Y~es", mnemonic: "y" },
        { flag: 0x0200, cmd: "no",     label: "~N~o", mnemonic: "n" },
        { flag: 0x0400, cmd: "ok",     label: "O~K~", mnemonic: "k" },
        { flag: 0x0800, cmd: "cancel", label: "~C~ancel", mnemonic: "c" },
    ];

    constructor() {
        const contentView = new TVGroup(new TVRect(2, 1, 39, 3));
        const buttonsView = new TVGroup(new TVRect(0, 3, 40, 5));
        const bodyView = new TVGroup(new TVRect(0, 0, 40, 5)).insertAll([
            contentView,
            buttonsView,
        ]);
        super(new TVRect(0, 0, 42, 7), "");
        this.insert(bodyView);
        this.setState(sfModal, true);
        this.contentView = contentView;
        this.buttonsView = buttonsView;
        this.bodyView = bodyView;
        this.messageViews = [];
        this.buttonViews = [];
        this._resolve = null;
        this.closeAction = () => this._dismiss(this._cancelCmd || this._defaultCmd || "cancel");
        this.bindDrag();
    }

    show({ type = 0, title, lines = [], buttons = TVMessageBox.MF_OK_BUTTON } = {}) {
        if (this._resolve) {
            this._dismiss(this._cancelCmd || this._defaultCmd);
        }
        const boxTitle = title !== undefined ? title : TVMessageBox.TITLES[type];
        this.title = String(boxTitle ?? "");
        this.frame.drawTitle();
        const messageLines = Array.isArray(lines) && lines.length ? lines.map((line) => String(line)) : [""];
        const requestedButtons = TVMessageBox.BUTTON_DEFS.filter(b => (buttons & b.flag) !== 0);
        const btnDefs = requestedButtons.length
            ? requestedButtons
            : TVMessageBox.BUTTON_DEFS.filter(b => b.cmd === "ok");
        const buttonWidth = 10;
        const buttonGap = 2;
        const buttonsWidth = btnDefs.length * buttonWidth + Math.max(0, btnDefs.length - 1) * buttonGap;
        const textWidth = Math.max(...messageLines.map((line) => Array.from(line).length), 0);
        const width = Math.max(42, Math.min(70, textWidth) + 6, btnDefs.length * 13);
        const height = messageLines.length + 6;
        const buttonsY = height - 4;
        this.changeBounds(new TVRect(this.bounds.x1, this.bounds.y1, this.bounds.x1 + width, this.bounds.y1 + height));
        this.bodyView.setBounds(new TVRect(0, 0, width - 2, height - 2));
        this.contentView.setBounds(new TVRect(2, 1, width - 3, buttonsY));
        this.buttonsView.setBounds(new TVRect(0, buttonsY, width - 2, buttonsY + 2));
        this.contentView.children.slice().forEach((view) => this.contentView.remove(view));
        this.buttonsView.children.slice().forEach((view) => this.buttonsView.remove(view));
        this.messageViews = messageLines.map((line, index) => (
            new TVStaticText(new TVRect(0, index, width - 5, index + 1), `\x03${line}`)
        ));
        const startX = Math.max(0, Math.floor((width - 2 - buttonsWidth) / 2));
        this.buttonViews = btnDefs.map((definition, index) => (
            new TVButton(
                new TVRect(startX + index * (buttonWidth + buttonGap), 0, startX + index * (buttonWidth + buttonGap) + buttonWidth, 2),
                definition.label,
                "msgbox-cmd",
                index === 0 ? bfDefault : bfNormal,
            ).setValue(definition.cmd)
        ));
        this.contentView.insertAll(this.messageViews);
        this.buttonsView.insertAll(this.buttonViews);
        this.drawContent();
        this._buttonDefs = btnDefs;
        // Determine default and cancel commands
        this._defaultCmd = btnDefs.length > 0 ? btnDefs[0].cmd : null;
        this._cancelCmd = (buttons & TVMessageBox.MF_CANCEL_BUTTON) ? "cancel" : null;
        // Show
        super.open();
        // Focus first button
        this.buttonViews[0]?.focus();
        return new Promise((resolve) => { this._resolve = resolve; });
    }

    hide() {
        super.close();
        this._resolve = null;
    }

    _dismiss(cmd) {
        const resolve = this._resolve;
        this.hide();
        if (resolve) { resolve(cmd); }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "msgbox-cmd") {
            this._dismiss(String(event.infoPtr?.value || this._defaultCmd || ""));
            this.clearEvent(event);
        }
    }

    onDialogKeyDown(event) {
        super.onDialogKeyDown(event);
        if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.key.length !== 1) { return; }
        const key = event.key.toLowerCase();
        const definition = (this._buttonDefs || []).find((button) => button.mnemonic === key);
        if (!definition) { return; }
        event.preventDefault();
        event.stopPropagation();
        this._dismiss(definition.cmd);
    }

    destroy() {
        const resolve = this._resolve;
        const command = this._cancelCmd || this._defaultCmd;
        this._resolve = null;
        super.destroy();
        if (resolve) { resolve(command); }
    }

}

function normalizeSearchText(text) {
    const value = String(text ?? "");
    if (typeof value.normalize === "function") {
        return value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    }
    return value.toLowerCase();
}

class TVScrollBar extends TVView {
    draw() {
        const axis = (this.options & sbVertical) !== 0 ? "y" : "x";
        const glyphs = axis === "y" ? ["▲", "▼"] : ["◄", "►"];
        return [
            `<div class="tv-scrollbar tv-scrollbar-${axis}" data-axis="${axis}">`,
            `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-backward" data-role="backward" aria-label="Scroll ${axis} backward">${glyphs[0]}</button>`,
            `<div class="tv-scroll-track" data-role="track"><div class="tv-scroll-cells" data-role="cells"></div><div class="tv-scroll-thumb" data-role="thumb"></div></div>`,
            `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-forward" data-role="forward" aria-label="Scroll ${axis} forward">${glyphs[1]}</button>`,
            `</div>`,
        ].join("");
    }

    constructor(bounds, options = sbHorizontal) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVScrollBar expects TVRect bounds");
        }
        super(bounds);
        this.options = Number(options) || sbHorizontal;
        this.value = 0;
        this.min = 0;
        this.max = 0;
        this.pgStep = 1;
        this.arStep = 1;
        this.frame = null;
        this.host = null;
        this.viewport = null;
        this.axes = {};
        this.resizeObserver = null;
        this.dragState = null;
        this.repeatTimer = null;
        this.destroyed = false;
        this.active = true;
        this.onViewportScroll = () => this.update();
        this.onWheel = (event) => this.handleWheel(event);
        this.onWindowResize = () => this.update();
        this.onDocumentMouseUp = () => this.stopRepeat();
    }

    setParams(value, min, max, pgStep, arStep) {
        this.min = Number(min) || 0;
        this.max = Math.max(this.min, Number(max) || 0);
        this.pgStep = Math.max(1, Number(pgStep) || 1);
        this.arStep = Math.max(1, Number(arStep) || 1);
        this.setValue(value);
    }

    setRange(min, max) { this.setParams(this.value, min, max, this.pgStep, this.arStep); }

    setStep(pgStep, arStep) { this.setParams(this.value, this.min, this.max, pgStep, arStep); }

    setValue(value) {
        this.value = this.clamp(Number(value) || 0, this.min, this.max);
        if (this.viewport) {
            const axis = this.axes.y ? "y" : "x";
            this.setScrollPosition(axis, this.value);
        }
        return this.value;
    }

    bindRoot(frame) {
        if (!frame) {
            this.root = null;
            this.frame = null;
            this.host = null;
            this.viewport = null;
            return this;
        }
        if (this.root?._tvView === this) { delete this.root._tvView; }
        // A scrollbar is an adapter for a scroll frame; it must not replace
        // the logical TVView that owns that frame (for example TVListViewer).
        this.root = frame;
        this.frame = frame;
        this.host = frame.querySelector(":scope > .tv-scrollbar")
            ? frame
            : (frame.closest(".tv-client-row") || frame.parentElement);
        this.viewport = frame.querySelector("[data-tv-viewport]");
        this.axes = {};
        for (const axisName of ["x", "y"]) {
            const axis = this.buildAxis(axisName);
            if (axis) { this.axes[axisName] = axis; }
        }
        for (const axis of Object.values(this.axes)) {
            axis.root._tvScrollbar = this;
        }
        this.destroyed = false;
        this.active = !frame.closest(".tv-window")?.classList.contains("is-window-inactive");
        this.bind();
        this.setActive(this.active);
        this.update();
        return this;
    }

    buildAxis(axis) {
        const root = this.host.querySelector(`.tv-scrollbar-${axis}`);
        if (!root) { return null; }
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
        this.viewport.addEventListener("scroll", this.onViewportScroll, { passive: true });
        this.frame.addEventListener("wheel", this.onWheel, { passive: false });
        window.addEventListener("resize", this.onWindowResize, { passive: true });

        for (const axis of Object.values(this.axes)) {
            axis.onBackwardMouseDown = (event) => this.startRepeat(event, axis.axis, -1);
            axis.onForwardMouseDown = (event) => this.startRepeat(event, axis.axis, 1);
            axis.onTrackMouseDown = (event) => this.onTrackMouseDown(event, axis.axis);
            axis.onThumbMouseDown = (event) => this.onThumbMouseDown(event, axis.axis);
            axis.backward.addEventListener("mousedown", axis.onBackwardMouseDown);
            axis.forward.addEventListener("mousedown", axis.onForwardMouseDown);
            axis.track.addEventListener("mousedown", axis.onTrackMouseDown);
            axis.thumb.addEventListener("mousedown", axis.onThumbMouseDown);
        }

        document.addEventListener("mouseup", this.onDocumentMouseUp, { passive: true });

        if ("ResizeObserver" in window) {
            this.resizeObserver = new ResizeObserver(() => this.update());
            this.observeContent();
        }
    }

    observeContent() {
        if (!this.resizeObserver) { return; }
        this.resizeObserver.disconnect();
        this.resizeObserver.observe(this.viewport);
        if (this.viewport.firstElementChild) {
            this.resizeObserver.observe(this.viewport.firstElementChild);
        }
    }

    refresh() {
        if (this.destroyed) { return; }
        this.observeContent();
        this.update();
    }

    startRepeat(event, axis, direction) {
        if (!this.active) { return; }
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

    handleWheel(event) {
        if (!this.active) { return; }
        const preferVertical = Math.abs(Number(event.deltaY) || 0) >= Math.abs(Number(event.deltaX) || 0);
        const candidates = preferVertical ? ["y", "x"] : ["x", "y"];
        const axisName = candidates.find((name) => this.axes[name] && this.axisMetrics(name).maxScroll > 0);
        if (!axisName) { return; }
        const metrics = this.axisMetrics(axisName);
        const rawDelta = axisName === "y" ? Number(event.deltaY) || 0 : Number(event.deltaX) || 0;
        if (!rawDelta) { return; }
        const unit = event.deltaMode === 1
            ? metrics.cellSize
            : (event.deltaMode === 2 ? metrics.viewportSize : 1);
        const next = this.clamp(metrics.scrollOffset + rawDelta * unit, 0, metrics.maxScroll);
        if (next === metrics.scrollOffset) { return; }
        event.preventDefault();
        event.stopPropagation();
        this.setScrollPosition(axisName, next);
    }

    lineHeight() {
        return measureCells().height;
    }

    charWidth() {
        return measureCells().width;
    }

    onTrackMouseDown(event, axis) {
        if (!this.active) { return; }
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
        if (!this.active) { return; }
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
        const unavailable = !this.active || maxScroll <= 0;
        axis.root.setAttribute("aria-disabled", unavailable ? "true" : "false");
        axis.backward.tabIndex = unavailable ? -1 : 0;
        axis.forward.tabIndex = unavailable ? -1 : 0;
        if (thumbCells > 0) {
            axis.thumb.style.display = "grid";
        } else {
            axis.thumb.style.display = "none";
        }
    }

    updateAxis(axisName) {
        if (this.axes[axisName]) {
            this.updateTrackGlyphs(this.axisMetrics(axisName));
        }
    }

    update() {
        if (this.destroyed) { return; }
        Object.keys(this.axes).forEach((axisName) => this.updateAxis(axisName));
    }

    setActive(active) {
        this.active = Boolean(active);
        for (const axis of Object.values(this.axes)) {
            axis.root.classList.toggle("is-inactive", !this.active);
            const unavailable = !this.active || axis.root.classList.contains("is-disabled");
            axis.root.setAttribute("aria-disabled", unavailable ? "true" : "false");
            axis.backward.tabIndex = unavailable ? -1 : 0;
            axis.forward.tabIndex = unavailable ? -1 : 0;
        }
        if (!this.active) {
            this.stopRepeat();
            this.onDragEnd();
        }
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    destroy() {
        if (this.destroyed) { return; }
        this.destroyed = true;
        this.stopRepeat();
        this.dragState = null;
        document.removeEventListener("mousemove", this.onDragMove);
        document.removeEventListener("mouseup", this.onDragEnd);
        document.removeEventListener("mouseup", this.onDocumentMouseUp);
        this.viewport.removeEventListener("scroll", this.onViewportScroll);
        this.frame.removeEventListener("wheel", this.onWheel);
        window.removeEventListener("resize", this.onWindowResize);
        for (const axis of Object.values(this.axes)) {
            axis.backward.removeEventListener("mousedown", axis.onBackwardMouseDown);
            axis.forward.removeEventListener("mousedown", axis.onForwardMouseDown);
            axis.track.removeEventListener("mousedown", axis.onTrackMouseDown);
            axis.thumb.removeEventListener("mousedown", axis.onThumbMouseDown);
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        if (this.root?._tvView === this) { delete this.root._tvView; }
    }
}

class TVProgram extends TVGroup {
    constructor(bounds = new TVRect()) {
        super(bounds);
        this.desktop = null;
        this.menuBar = null;
        this.statusLine = null;
    }
}

class TVDesktop extends TVGroup {
    constructor(bounds = new TVRect()) {
        super(bounds);
        this.dialogManager = null;
        this.layoutStarted = false;
        this.clockTimer = null;
        this.onResize = () => {
            fillBorders();
            fillDesktopPatterns();
        };
        this.onLoad = () => {
            this.onResize();
            updateClocks();
        };
    }

    bindRoot(root) {
        super.bindRoot(root);
        this.dialogManager = new TVDialogManager(this);
        return this;
    }

    insert(view) {
        const inserted = super.insert(view);
        if (this.root && inserted.root && !inserted.root.isConnected) {
            inserted.mount(this.root);
        }
        return inserted;
    }

    startLayout() {
        if (this.layoutStarted) { return; }
        this.layoutStarted = true;
        this.onLoad();
        this.clockTimer = window.setInterval(updateClocks, 1000);
        window.addEventListener("resize", this.onResize, { passive: true });
        window.addEventListener("load", this.onLoad, { passive: true });
    }

    destroy() {
        if (!this.layoutStarted) { return; }
        this.layoutStarted = false;
        if (this.clockTimer !== null) {
            window.clearInterval(this.clockTimer);
            this.clockTimer = null;
        }
        window.removeEventListener("resize", this.onResize);
        window.removeEventListener("load", this.onLoad);
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
    TV2_APP_COLOR_ATTRIBUTES,
    TV2_PALETTE_TOKENS,
    TV_FRAME_GLYPHS,
    THEME_PRESETS,
    DEFAULT_UI_CONFIG,
    TV_COMMANDS,
    TV_HELP_CONTEXTS,
    evNothing,
    evMouseDown,
    evMouseUp,
    evMouseMove,
    evMouseAuto,
    evKeyDown,
    evCommand,
    evBroadcast,
    cmUpdateGauge,
    cmResetGauge,
    cmAddGauge,
    sfVisible,
    sfCursorVis,
    sfCursorIns,
    sfShadow,
    sfActive,
    sfSelected,
    sfFocused,
    sfDragging,
    sfDisabled,
    sfModal,
    sfDefault,
    sfExposed,
    ofSelectable,
    ofTopSelect,
    ofFirstClick,
    ofFramed,
    ofPreProcess,
    ofPostProcess,
    ofBuffered,
    ofTileable,
    ofCenterX,
    ofCenterY,
    ofCentered,
    ofValidate,
    gfGrowLoX,
    gfGrowLoY,
    gfGrowHiX,
    gfGrowHiY,
    gfGrowAll,
    gfGrowRel,
    dmDragMove,
    dmDragGrow,
    dmLimitLoX,
    dmLimitLoY,
    dmLimitHiX,
    dmLimitHiY,
    dmLimitAll,
    wfMove,
    wfGrow,
    wfClose,
    wfZoom,
    wfMaxi,
    wnNoNumber,
    sbHorizontal,
    sbVertical,
    sbHandleKeyboard,
    kbNoKey,
    kbCtrlF,
    kbCtrlL,
    kbF1,
    kbF3,
    kbF5,
    kbF6,
    kbShiftF6,
    kbAltF3,
    kbAlt0,
    getKeyCode,
    TVEvent,
    COLOR_GROUPS,
    buildDefaultColorPalette,
    buildPaletteFromCurrentStyle,
    readStoredColorPalette,
    applyColorPalette,
    clearStoredColorPalette,
    readStoredThemePreset,
    applyThemePreset,
    applyThemeAndSyncPalette,
    initializeTVTheme,
    cloneColorPalette,
    setColorPaletteAttribute,
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
    normalizeHelpContext,
    elementHelpContext,
    setElementHelpContext,
    resolveHelpContext,
    resetMenuPopupLayout,
    fitMenuPopupToViewport,
    TVAppContext,
    TVPoint,
    TVRect,
    TVView,
    TVStaticText,
    TVPercentGauge,
    TVBarGauge,
    TVLabel,
    TVInputLine,
    TVListViewer,
    TVGroup,
    TVInfoRow,
    TVInfoBox,
    TVTerminal,
    TVIndicator,
    TVEditor,
    TVListBox,
    TVOutline,
    TVScroller,
    TVMenu,
    NewLine,
    NewSubMenu,
    TVMenuView,
    TVMenuItem,
    TVMenuBox,
    TVStatusItem,
    TVStatusDef,
    NewStatusKey,
    NewStatusDef,
    TVStatusLine,
    TVMenuController,
    TVHelpController,
    TVCluster,
    TVCheckBoxes,
    TVRadioButtons,
    TVMultiCheckBoxes,
    TVButton,
    bfNormal,
    bfDefault,
    bfLeftJust,
    bfBroadcast,
    TVFrame,
    TVWindow,
    TVDialog,
    TVMessageBox,
    TVDialogManager,
    TVProgram,
    TVDesktop,
    TVScrollBar,
});
Object.assign(TV, TV_HELP_CONTEXTS);
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
