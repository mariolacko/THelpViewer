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
    "--tv-search-results-pane": ["--tv-palette-dialog-info-bg"],
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

class TVRect {
    constructor(x1 = 0, y1 = 0, x2 = x1, y2 = y1) {
        this.x1 = Number(x1) || 0;
        this.y1 = Number(y1) || 0;
        this.x2 = Number(x2) || this.x1;
        this.y2 = Number(y2) || this.y1;
    }

    get width() { return Math.max(0, this.x2 - this.x1); }
    get height() { return Math.max(0, this.y2 - this.y1); }
}

let tvViewSequence = 0;
const tvRenderState = new WeakMap();

const evNothing = 0x0000;
const evMouseDown = 0x0001;
const evMouseUp = 0x0002;
const evMouseMove = 0x0004;
const evMouseAuto = 0x0008;
const evKeyDown = 0x0010;
const evCommand = 0x0100;
const evBroadcast = 0x0200;

class TVEvent {
    constructor(what = evNothing, { command = "", infoPtr = null, nativeEvent = null } = {}) {
        this.what = what;
        this.command = command;
        this.infoPtr = infoPtr;
        this.nativeEvent = nativeEvent;
    }
}

/**
 * Browser adapter for TVision views.  DOM presentation belongs here, never in
 * a public view constructor.  Application code may select a semantic
 * presentation, while element names, classes and attributes stay private to
 * the renderer.
 */
class TVRenderer {
    static configure(view, options = {}) {
        if (!(view instanceof TVView)) {
            throw new TypeError("TVRenderer expects a TVView");
        }
        tvRenderState.set(view, { ...this.state(view), ...options });
        return view;
    }

    static state(view) {
        return tvRenderState.get(view) || {};
    }

    static viewAttrs(view, attrs = {}) {
        return {
            "data-tv-view-id": view.viewId,
            ...(view.helpCtx !== hcNoContext ? { "data-tv-help-ctx": view.helpCtx } : {}),
            ...attrs,
        };
    }

    static markup(items = [], options = {}) {
        return this.configure(new TVMarkupView(items), options);
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
        this.viewId = `tv-view-${++tvViewSequence}`;
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

    static viewBoundsStyle(view) {
        const bounds = view?.bounds;
        if (!(bounds instanceof TVRect)) { return ""; }
        if (bounds.x1 === 0 && bounds.y1 === 0 && bounds.x2 === 0 && bounds.y2 === 0) {
            return "";
        }
        return this.boundsStyle(
            bounds.x1,
            bounds.y1,
            bounds.width || undefined,
            bounds.height || undefined,
        );
    }

    static roleClassNames(role = "") {
        return String(role).split(/\s+/).filter(Boolean).map((name) => (
            name.startsWith("is-") ? name : `tv-${name}`
        )).join(" ");
    }

    static controlAttrs({
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

    static fromHTML(markup) {
        const template = document.createElement("template");
        template.innerHTML = markup.trim();
        return template.content.firstElementChild;
    }

    static fromElement(element) {
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

    setBounds(bounds) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVView.setBounds expects TVRect");
        }
        this.bounds = bounds;
        return this;
    }

    setState(state, enable) {
        if (state === "visible") {
            if (this.root) { this.root.hidden = !enable; }
        } else if (state === "active") {
            this.root?.classList.toggle("is-active", Boolean(enable));
        } else if (state === "expanded") {
            this.root?.setAttribute("aria-expanded", enable ? "true" : "false");
        }
        return this;
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
            view.handleEvent(event);
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
        super();
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVStaticText expects TVRect bounds");
        }
        this.bounds = bounds;
        this.text = String(text ?? "");
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const cls = [
            "tv-static-text",
            rendering.title ? "tv-title" : "",
            TVView.roleClassNames(rendering.presentation),
        ].filter(Boolean).join(" ");
        const classAttr = ` class="${escapeHtml(cls)}"`;
        const bounds = TVView.viewBoundsStyle(this);
        const alignStyle = rendering.align ? `text-align:${rendering.align}` : "";
        const inlineStyle = [bounds, alignStyle].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const liveKinds = new Set(["calc-display", "midi-status", "find-status"]);
        const liveNames = new Set(["tron-status", "hanoi-history", "hanoi-status"]);
        const semanticName = rendering.viewName
            ? String(rendering.viewName).replace(/[^a-zA-Z0-9_-]/g, "-")
            : "";
        const attrString = attrsToString(TVRenderer.viewAttrs(this, {
            ...(semanticName ? {
                [`data-tv-${semanticName}`]: true,
                "data-tv-row": semanticName,
            } : {}),
            ...(liveKinds.has(rendering.presentation) || liveNames.has(semanticName) ? { "aria-live": "polite" } : {}),
            ...(semanticName === "ludo-board" ? { role: "grid", "aria-label": "Ludo board" } : {}),
            ...(semanticName === "tron-field" ? { role: "img", "aria-label": "Tron arena" } : {}),
        }));
        const attrs = attrString ? ` ${attrString}` : "";
        return `<div${classAttr}${styleAttr}${attrs}>${escapeHtml(this.text)}</div>`;
    }

    getText() {
        return this.text;
    }

    setText(text) {
        this.text = String(text ?? "");
        if (this.root) { this.root.textContent = this.text; }
        return this;
    }

    draw() {
        return this.renderMarkup();
    }
}

class TVLabel extends TVStaticText {
    constructor(bounds, text, link = null) {
        super(bounds, text);
        this.link = link instanceof TVView ? link : null;
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const tag = this.link ? "label" : "span";
        const cls = ["tv-static-text", "tv-label", TVView.roleClassNames(rendering.presentation)].filter(Boolean).join(" ");
        const bounds = TVView.viewBoundsStyle(this);
        const styleAttr = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const forAttr = this.link ? ` for="${escapeHtml(this.link.viewId)}"` : "";
        const attrs = attrsToString(TVRenderer.viewAttrs(this));
        const content = rendering.hotkey ? renderHotkeyMarkup(this.text) : escapeHtml(this.text);
        return `<${tag} class="${escapeHtml(cls)}"${styleAttr}${forAttr} ${attrs}>${content}</${tag}>`;
    }
}

class TVInputLine extends TVView {
    constructor(bounds, maxLen = 255) {
        super();
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVInputLine expects TVRect bounds");
        }
        this.bounds = bounds;
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

    selectAll() {
        this.root?.select();
        return this;
    }

    setState(state, enable) {
        if (state === "disabled") {
            this.disabled = Boolean(enable);
            if (this.root) { this.root.disabled = this.disabled; }
            return this;
        }
        return super.setState(state, enable);
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const viewName = rendering.viewName
            ? String(rendering.viewName).replace(/[^a-zA-Z0-9_-]/g, "-")
            : "";
        const attrString = attrsToString(TVRenderer.viewAttrs(this, {
            type: "text",
            id: this.viewId,
            maxlength: this.maxLen,
            value: this.data,
            disabled: this.disabled,
            placeholder: rendering.placeholder || null,
            autocomplete: rendering.autocomplete || null,
            spellcheck: rendering.spellcheck ?? null,
            ...(viewName ? { [`data-tv-${viewName}`]: true } : {}),
        }));
        const cls = ["tv-input-line", TVView.roleClassNames(rendering.presentation)].filter(Boolean).join(" ");
        const bounds = TVView.viewBoundsStyle(this);
        const inlineStyle = [bounds, rendering.width ? `width:${rendering.width}` : ""].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
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

class TVMarkupView extends TVView {
    constructor(items = []) {
        super();
        this.items = Array.isArray(items) ? items : [items];
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const element = rendering.element || "div";
        const classAttr = rendering.className ? ` class="${escapeHtml(rendering.className)}"` : "";
        const attrString = attrsToString(TVRenderer.viewAttrs(this, rendering.attributes || {}));
        const attrs = attrString ? ` ${attrString}` : "";
        return `<${element}${classAttr}${attrs}>${this.items.join("")}</${element}>`;
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
    }

    /** True if any child has absolute positioning (x or y). */
    _hasPositionedChildren() {
        return this.children.some((child) =>
            child instanceof TVView && (child.bounds.x1 !== 0 || child.bounds.y1 !== 0)
        );
    }

    renderChildren() {
        return this.children.map((child) => {
            if (child && typeof child.renderMarkup === "function") {
                return child.renderMarkup();
            }
            return "";
        }).join("");
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const cls = ["tv-group", TVView.roleClassNames(rendering.presentation)].filter(Boolean).join(" ");
        const bounds = TVView.viewBoundsStyle(this);
        const positioned = this._hasPositionedChildren() ? "position:relative" : "";
        const parts = [
            bounds,
            positioned,
            rendering.columns ? `grid-template-columns:${rendering.columns}` : "",
            rendering.rows ? `grid-template-rows:${rendering.rows}` : "",
            rendering.gap ? `gap:${rendering.gap}` : "",
            rendering.align ? `align-items:${rendering.align}` : "",
            rendering.padding ? `padding:${rendering.padding}` : "",
            rendering.width ? `width:${rendering.width}` : "",
            rendering.height ? `height:${rendering.height}` : "",
        ].filter(Boolean).join(";");
        const styleAttr = parts ? ` style="${escapeHtml(parts)}"` : "";
        const viewName = rendering.viewName
            ? String(rendering.viewName).replace(/[^a-zA-Z0-9_-]/g, "-")
            : "";
        const attrString = attrsToString(TVRenderer.viewAttrs(this, {
            ...(viewName ? { [`data-tv-${viewName}`]: rendering.value ?? true } : {}),
            hidden: rendering.hidden || false,
            "aria-label": rendering.ariaLabel || null,
            "aria-hidden": rendering.ariaHidden ?? null,
        }));
        const attrs = attrString ? ` ${attrString}` : "";
        return `<div class="${escapeHtml(cls)}"${styleAttr}${attrs}>${this.renderChildren()}</div>`;
    }

    setCurrent(child) {
        this.current = this.children.includes(child) ? child : null;
        return this.current;
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

class TVInfoBox extends TVView {
    /**
     * @param {Object} opts
     * @param {string} opts.title   — frame title shown in header
     * @param {number} opts.w       — total width in ch (including border chars)
     * @param {Array}  opts.children — array of TVView instances rendered inside the frame
     * @param {number} [opts.x] — absolute left position in ch
     * @param {number} [opts.y] — absolute top position in em
     * @param {number} [opts.h] — explicit height in em
     */
    constructor(bounds, title, children = []) {
        super();
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVInfoBox expects TVRect bounds");
        }
        this.bounds = bounds;
        this.title = String(title ?? "");
        this.children = Array.isArray(children) ? children : [];
        this.children.forEach((child) => {
            if (child instanceof TVView) { child.owner = this; }
            if (child instanceof TVStaticText && TVRenderer.state(child).viewName) {
                const rendering = TVRenderer.state(child);
                TVRenderer.configure(child, {
                    presentation: [rendering.presentation, "info-row"].filter(Boolean).join(" "),
                });
            }
        });
        this._el = null;
        this._rows = {};
    }

    get innerW() { return this.bounds.width - 2; }

    renderMarkup() {
        const innerW = this.innerW;
        const parts = [];
        // Header
        parts.push(`<span data-tv-info-frame>${escapeHtml(TVInfoBox.header(innerW, this.title))}</span>`);
        // Children — all TVView instances
        for (const child of this.children) {
            if (child && typeof child.renderMarkup === "function") {
                parts.push(child.renderMarkup());
            }
        }
        // Footer
        parts.push(`<span data-tv-info-frame>${escapeHtml(TVInfoBox.footer(innerW))}</span>`);

        const rendering = TVRenderer.state(this);
        const bounds = TVView.viewBoundsStyle(this);
        const cls = ["tv-info-box", TVView.roleClassNames(rendering.presentation)].filter(Boolean).join(" ");
        const attrString = attrsToString(TVRenderer.viewAttrs(this));
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const extra = attrString ? ` ${attrString}` : "";
        return `<div class="${escapeHtml(cls)}" data-tv-info-w="${innerW}"${style}${extra}>${parts.join("")}</div>`;
    }

    resolve(rootEl) {
        this._el = null;
        this._rows = {};
        if (!rootEl) { return this; }
        this._el = rootEl.getAttribute?.("data-tv-view-id") === this.viewId
            ? rootEl
            : rootEl.querySelector(`[data-tv-view-id="${this.viewId}"]`);
        if (!this._el) { return this; }
        this.bindRoot(this._el);
        for (const child of this.children) {
            child?.resolve?.(this._el);
            const viewName = child ? TVRenderer.state(child).viewName : "";
            if (viewName) {
                const el = this._el.querySelector(`[data-tv-row="${viewName}"]`);
                if (el) { this._rows[viewName] = el; }
            }
        }
        return this;
    }

    updateRow(name, text) {
        const el = this._rows[name];
        if (!el) { return; }
        el.innerHTML = TVInfoBox.rowHtml(
            this.innerW,
            text,
            TVView.roleClassNames(TVRenderer.state(this).borderPresentation),
        );
    }

    updateRowHTML(name, html, contentLen) {
        const el = this._rows[name];
        if (!el) { return; }
        const w = this.innerW;
        const borderClass = TVView.roleClassNames(TVRenderer.state(this).borderPresentation);
        const classAttr = borderClass ? ` class="${escapeHtml(borderClass)}"` : "";
        const B = `<span data-tv-info-side${classAttr}>\u2502</span>`;
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
        super();
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVTerminal expects TVRect bounds");
        }
        this.bounds = bounds;
        this.width = bounds.width;
        this.rows = bounds.height;
        this.maxLines = Math.max(1, Number(maxLines) || 100);
        this.lines = [];
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const className = ["tv-terminal", TVView.roleClassNames(rendering.presentation)].filter(Boolean).join(" ");
        const attrString = attrsToString(TVRenderer.viewAttrs(this, {
            role: "log",
            "aria-live": "polite",
            ...(rendering.viewName ? { [`data-tv-${rendering.viewName}`]: true } : {}),
        }));
        const rows = Array.from({ length: this.rows }, (_unused, index) => (
            `<span data-tv-terminal-line="${index}"></span>`
        )).join("");
        return `<div class="${escapeHtml(className)}" ${attrString}>${rows}</div>`;
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
        const visible = this.lines.slice(-this.rows);
        const offset = this.rows - visible.length;
        this.queryAll("[data-tv-terminal-line]").forEach((element, index) => {
            const text = index >= offset ? visible[index - offset] : "";
            const clipped = Array.from(text).slice(0, Math.max(0, this.width - 1)).join("");
            element.innerHTML = TVInfoBox.rowHtml(this.width, clipped);
        });
    }
}

class TVIndicator extends TVView {
    renderMarkup() {
        const className = "tv-editor-indicator";
        const attrString = attrsToString(TVRenderer.viewAttrs(this, { "aria-live": "polite" }));
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
    constructor(bounds, numCols = 1) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVListViewer expects TVRect bounds");
        }
        super(bounds);
        this.numCols = Math.max(1, Number(numCols) || 1);
        this.itemClassName = "";
        this.itemAttrName = "data-tv-list-index";
        this.selectedClassName = "is-selected";
        this.renderItemContent = null;
        this.renderItemMarkup = null;
        this.items = [];
        this.selectedIndex = -1;
        this.selectHandler = null;
        this.activateHandler = null;
    }

    applyRenderer() {
        const rendering = TVRenderer.state(this);
        this.itemClassName = rendering.itemClassName || "";
        this.itemAttrName = rendering.itemAttrName || "data-tv-list-index";
        this.selectedClassName = rendering.selectedClassName || "is-selected";
        this.renderItemContent = rendering.renderItemContent || null;
        this.renderItemMarkup = rendering.renderItemMarkup || null;
        return this;
    }

    bindRoot(root) {
        super.bindRoot(root);
        this.applyRenderer();
        if (this.root) {
            this.root.dataset.tvListBox = "1";
        }
        return this;
    }

    itemsRoot() {
        return this.root;
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
            "tv-vlist-item",
            this.itemClassName,
            index === this.selectedIndex ? this.selectedClassName : "",
        ].filter(Boolean).join(" ");
        return `<div role="option" tabindex="-1" class="${className}" ${this.itemAttrName}="${index}"><span class="tv-vlist-text tv-colors-list-text">${this.defaultContent(item, index)}</span></div>`;
    }

    itemMarkup(item, index) {
        if (this.renderItemMarkup) {
            return this.renderItemMarkup(item, index, index === this.selectedIndex);
        }
        return this.defaultMarkup(item, index);
    }

    setItems(items = [], selectedIndex = -1) {
        this.applyRenderer();
        this.items = Array.isArray(items) ? [...items] : [];
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
        this.updateSelectionUi(scroll);
    }

    selectedItem() {
        return this.selectedIndex >= 0 ? this.items[this.selectedIndex] : null;
    }

    selectedElement() {
        const itemsRoot = this.itemsRoot();
        return itemsRoot
            ? itemsRoot.querySelector(`${this.itemSelector()}[${this.itemAttrName}="${this.selectedIndex}"]`)
            : null;
    }

    updateSelectionUi(scroll = true) {
        const itemsRoot = this.itemsRoot();
        if (!itemsRoot) {
            return;
        }
        const elements = Array.from(itemsRoot.querySelectorAll(this.itemSelector()));
        elements.forEach((element, index) => {
            const value = Number.parseInt(element.getAttribute(this.itemAttrName), 10);
            const selected = value === this.selectedIndex;
            element.setAttribute("role", "option");
            element.classList.toggle(this.selectedClassName, selected);
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

class TVListBox extends TVListViewer {}

class TVVerticalListViewer extends TVListBox {
    static renderMarkup({
        rootClass = "",
        rootAttrs = {},
        viewportClass = "",
        scrollbar = true,
        scrollbarClass = "tv-vlist-scrollbar",
        arrowClass = "tv-vlist-arrow",
        trackClass = "tv-vlist-track",
        cellsClass = "tv-vlist-cells",
        thumbClass = "tv-vlist-thumb",
    } = {}) {
        const rootAttrString = attrsToString(rootAttrs);
        const rootAttrsText = rootAttrString ? ` ${rootAttrString}` : "";
        const rootClasses = ["tv-vlist-viewer", rootClass].filter(Boolean).join(" ");
        const viewportClasses = ["tv-vlist-viewport", viewportClass].filter(Boolean).join(" ");
        const scrollFrameAttr = scrollbar ? " data-tv-scroll-frame" : "";
        const scrollbarMarkup = scrollbar
            ? TVScrollBar.renderMarkup("y", {
                rootClass: scrollbarClass,
                arrowClass,
                trackClass,
                cellsClass,
                thumbClass,
            })
            : "";
        return `
            <div class="${escapeHtml(rootClasses)}"${scrollFrameAttr}${rootAttrsText}>
                <div class="${escapeHtml(viewportClasses)}" data-tv-list-viewport data-tv-viewport></div>
                ${scrollbarMarkup}
            </div>
        `;
    }

    static bindRendered(viewer, hostView) {
        if (!(viewer instanceof TVVerticalListViewer) || !(hostView instanceof TVView)) {
            throw new TypeError("TVVerticalListViewer.bindRendered expects viewer and host TVView");
        }
        return viewer.bindRoot(hostView.query(".tv-vlist-viewer"));
    }

    constructor(bounds, numCols = 1) {
        super(bounds, numCols);
        this.viewport = null;
        this.scrollViewport = null;
        this.externalScrollbarWidget = null;
        this.scrollbarWidget = null;
        this.scrollbar = null;
        this.active = true;
    }

    bindRoot(root) {
        this.scrollbarWidget?.destroy();
        super.bindRoot(root);
        this.viewport = this.query("[data-tv-list-viewport]");
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

class TVOutline extends TVVerticalListViewer {
    constructor(bounds, numCols = 1) {
        super(bounds, numCols);
        this.getChildren = (node) => node?.children || [];
        this.getKey = (node) => node?.key ?? node?.path ?? node?.id ?? node?.label;
        this.getLabel = (node) => node?.label ?? "";
        this.renderNodeContent = null;
        this.renderItemContent = (entry) => this.renderEntry(entry);
        this.tree = [];
        this.expanded = new Set();
        this.nodeSelectHandler = null;
        this.nodeActivateHandler = null;
    }

    applyRenderer() {
        super.applyRenderer();
        const rendering = TVRenderer.state(this);
        this.getChildren = rendering.getChildren || ((node) => node?.children || []);
        this.getKey = rendering.getKey || ((node) => node?.key ?? node?.path ?? node?.id ?? node?.label);
        this.getLabel = rendering.getLabel || ((node) => node?.label ?? "");
        this.renderNodeContent = rendering.renderNodeContent || null;
        this.renderItemContent = (entry) => this.renderEntry(entry);
        return this;
    }

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
        const content = this.renderNodeContent
            ? this.renderNodeContent(entry.node, entry)
            : escapeHtml(String(this.getLabel(entry.node)));
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

class TVVerticalScrollArea extends TVView {
    static bindRendered(scrollArea, hostView) {
        if (!(scrollArea instanceof TVVerticalScrollArea) || !(hostView instanceof TVView)) {
            throw new TypeError("TVVerticalScrollArea.bindRendered expects scroll area and host TVView");
        }
        return scrollArea.bindRoot(hostView.query("[data-tv-scroll-frame]"));
    }

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
            <div class="${escapeHtml(rootClass)}" data-tv-scroll-frame${rootAttrsText}>
                <div class="${escapeHtml(viewportClass)}" data-tv-scroll-viewport data-tv-viewport></div>
                ${TVScrollBar.renderMarkup("y", {
                    rootClass: scrollbarClass,
                    arrowClass,
                    trackClass,
                    cellsClass,
                    thumbClass,
                })}
            </div>
        `;
    }

    constructor(bounds) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVVerticalScrollArea expects TVRect bounds");
        }
        super(bounds);
        this.viewport = null;
        this.scrollbarWidget = null;
    }

    bindRoot(root) {
        this.scrollbarWidget?.destroy();
        super.bindRoot(root);
        this.viewport = this.query("[data-tv-scroll-viewport]");
        this.scrollbarWidget = this.root ? new TVScrollBar(new TVRect()).bindRoot(this.root) : null;
        return this;
    }

    update() {
        this.scrollbarWidget?.refresh();
    }

    bind() {
        this.update();
    }

    destroy() {
        this.scrollbarWidget?.destroy();
        this.scrollbarWidget = null;
    }
}

class TVMenuView extends TVView {
    renderItems(items = [], view = "popup") {
        return items.map((item) => (
            typeof item === "string" ? item : item?.renderMarkup?.(view) || ""
        ));
    }
}

/**
 * Turbo Vision menu command descriptor. TMenuItem is not a TButton: the
 * owning TMenuView decides whether it is drawn in a menu bar or menu box.
 */
class TVMenuItem extends TVView {
    constructor(label, command = "", value = true, commandData = {}) {
        super();
        this.label = String(label || "");
        this.command = command;
        this.value = value;
        this.commandData = commandData;
        this.disabled = false;
    }

    setDisabled(disabled = true) {
        this.disabled = Boolean(disabled);
        return this;
    }

    renderMarkup(view = "popup") {
        const isMenuBar = view === "bar";
        const attrs = attrsToString({
            type: "button",
            ...TVView.controlAttrs({
                name: this.command,
                command: this.command,
                value: this.value,
                commandData: this.commandData,
                disabled: this.disabled,
                ariaHasPopup: isMenuBar ? true : null,
                ariaExpanded: isMenuBar ? false : null,
            }),
        });
        const className = isMenuBar ? "tv-menu-item tv-menu-button" : "tv-menu-popup-item";
        return `<button class="${className}" ${attrs}>${this.label}</button>`;
    }
}

/** Turbo Vision status-line command descriptor (TStatusItem). */
class TVStatusItem extends TVView {
    constructor(text, command = "", value = true, commandData = {}) {
        super();
        this.text = String(text || "");
        this.command = command;
        this.value = value;
        this.commandData = commandData;
        this.disabled = false;
    }

    setDisabled(disabled = true) {
        this.disabled = Boolean(disabled);
        return this;
    }

    renderMarkup() {
        const attrs = attrsToString({
            type: "button",
            ...TVView.controlAttrs({
                name: this.command,
                command: this.command,
                value: this.value,
                commandData: this.commandData,
                disabled: this.disabled,
            }),
        });
        return `<button class="tv-status-item" ${attrs}>${this.text}</button>`;
    }
}

class TVMenuBox extends TVMenuView {
    constructor(bounds, items = []) {
        super(bounds);
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVMenuBox expects TVRect bounds");
        }
        this.items = Array.isArray(items) ? items : [];
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const popupAttrs = attrsToString(TVRenderer.viewAttrs(this, rendering.attributes || {}));
        const attrs = popupAttrs ? ` ${popupAttrs}` : "";
        const className = rendering.className || "tv-menu-popup";
        const borderFill = '<span class="tv-border-fill" data-tv-border-fill="\u2500" aria-hidden="true"></span>';
        const scrollbarMarkup = TVScrollBar.renderMarkup("y", {
            rootClass: "tv-menu-popup-scrollbar",
        });
        // Split items into segments at separator strings to render them as body-level rows.
        const segments = [[]];
        for (const html of this.renderItems(this.items, "popup")) {
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
    const scrollbar = main?.querySelector(":scope > .tv-menu-popup-scrollbar") || null;
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
    constructor({ root = document, onUnhandledKeyDown = null } = {}) {
        this.root = root;
        this.onUnhandledKeyDown = onUnhandledKeyDown;
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
        this.onDocumentKeyDown = (event) => this.onKeyDown(event);
        document.addEventListener("click", this.onDocumentClick);
        document.addEventListener("keydown", this.onDocumentKeyDown);
        this.refresh();
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

    onKeyDown(event) {
        if (event.defaultPrevented) {
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
            if (this.onUnhandledKeyDown) { this.onUnhandledKeyDown(event); }
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
        document.removeEventListener("keydown", this.onDocumentKeyDown);
    }
}

let tvChoiceGroupId = 0;

class TVCluster extends TVView {
    constructor(bounds, options = []) {
        super();
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVCluster expects TVRect bounds");
        }
        this.bounds = bounds;
        this.options = Array.isArray(options) ? options : [];
        this.type = "checkbox";
        this.itemClass = "tv-checkbox-item";
        this.itemAttr = "data-tv-checkbox-index";
        this.markClass = "tv-checkbox-mark";
    }

    renderMarkup() {
        const items = this.options.map((option, index) => {
            const inputAttrs = attrsToString({
                type: this.type,
                class: "tv-choice-input",
                name: this.type === "radio" ? this.viewId : null,
                value: option.value !== undefined ? option.value : index,
                checked: Boolean(option.checked),
                disabled: Boolean(option.disabled),
                ...(option.attrs || {}),
            });
            const className = `${this.itemClass}${option.disabled ? " is-disabled" : ""}`;
            return `<label class="${className}" ${this.itemAttr}="${index}"><input ${inputAttrs}><span class="${this.markClass}" aria-hidden="true"></span> <span class="tv-choice-label">${renderHotkeyMarkup(option.label || "")}</span></label>`;
        }).join("");
        const rendering = TVRenderer.state(this);
        return TVRenderer.markup([items], {
            className: TVView.roleClassNames(rendering.presentation),
            attributes: TVRenderer.viewAttrs(this, rendering.viewName ? { [`data-tv-${rendering.viewName}`]: true } : {}),
        }).renderMarkup();
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
        this.changeHandler = null;
    }

    renderMarkup() {
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
        const rendering = TVRenderer.state(this);
        return TVRenderer.markup([items], {
            className: TVView.roleClassNames(rendering.presentation),
            attributes: TVRenderer.viewAttrs(this, rendering.viewName ? { [`data-tv-${rendering.viewName}`]: true } : {}),
        }).renderMarkup();
    }

    bind(root, onChange = null) {
        this.bindRoot(root);
        this.changeHandler = onChange;
        if (!root || root.dataset.tvMultiCheckBound === "1") { return this; }
        root.dataset.tvMultiCheckBound = "1";
        root.addEventListener("click", (event) => {
            const button = event.target.closest("[data-tv-multicheck-state]");
            if (!button || button.disabled) { return; }
            const item = button.closest(`[${this.itemAttr}]`);
            const index = Number.parseInt(item?.getAttribute(this.itemAttr) || "", 10);
            this.cycle(index, button);
        });
        return this;
    }

    cycle(index, button = null) {
        if (!Number.isInteger(index) || index < 0 || index >= this.options.length) { return; }
        const target = button || this.query(`[${this.itemAttr}="${index}"] [data-tv-multicheck-state]`);
        if (!target || target.disabled) { return; }
        const state = (Number.parseInt(target.dataset.tvMulticheckState || "0", 10) + 1) % this.states.length;
        target.dataset.tvMulticheckState = String(state);
        target.setAttribute("aria-checked", state === 0 ? "false" : (state === 1 ? "true" : "mixed"));
        const mark = target.querySelector(`.${this.markClass}`);
        if (mark) { mark.textContent = `[${this.states[state]}]`; }
        this.options[index].state = state;
        if (this.changeHandler) { this.changeHandler(this.options[index], state, index); }
    }
}

const bfNormal = 0x00;
const bfDefault = 0x01;
const bfLeftJust = 0x02;
const bfBroadcast = 0x04;

class TVButton extends TVView {
    constructor(bounds, title, command, flags = bfNormal) {
        super();
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVButton expects TVRect bounds");
        }
        this.bounds = bounds;
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

    presentation() {
        const data = this.commandData || {};
        const plain = new Set([
            "file-open-history", "change-dir-history", "find-history",
            "context-help-back", "context-help-contents",
            "file-open-scroll-left", "file-open-scroll-right",
            "ascii-code", "calendar-prev", "calendar-next", "color-index",
            "midi-previous", "midi-play", "midi-pause", "midi-stop", "midi-next",
            "midi-more", "midi-close-button", "midi-source", "midi-load-url",
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
        } else if (this.command === "color-index") {
            classes.push("tv-color-cell");
        } else if (["midi-previous", "midi-play", "midi-pause", "midi-stop", "midi-next"].includes(this.command)) {
            classes.push("tv-midi-control");
        } else if (this.command === "midi-more") {
            classes.push("tv-midi-more-action");
        } else if (this.command === "midi-close-button") {
            classes.push("tv-midi-close-action");
        } else if (this.command === "midi-source") {
            classes.push("tv-midi-source-preset");
        } else if (this.command === "midi-load-url") {
            classes.push("tv-midi-url-load");
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
        return {
            dialog: !plain.has(this.command),
            baseClass: this.command === "calc-key" ? "tv-calc-button" : "tv-dialog-button",
            className: classes.join(" "),
            style: this.command === "color-index" && data.color
                ? `--tv-color-cell:${data.color}`
                : "",
        };
    }

    renderMarkup() {
        const rendering = TVRenderer.state(this);
        const presentation = this.presentation();
        const attrString = attrsToString(TVRenderer.viewAttrs(this, {
            type: "button",
            ...TVView.controlAttrs({
                name: this.command,
                value: this.value,
                command: this.command,
                commandData: this.commandData,
                disabled: this.disabled,
                hidden: rendering.hidden || false,
                ariaLabel: rendering.ariaLabel || "",
                ariaExpanded: rendering.ariaExpanded ?? null,
                ariaPressed: rendering.ariaPressed ?? null,
                ariaHasPopup: rendering.ariaHasPopup ?? null,
                tabIndex: rendering.tabIndex ?? null,
                tooltip: rendering.tooltip || "",
                draggable: rendering.draggable ?? null,
            }),
        }));
        const classNames = [presentation.className, (this.flags & bfDefault) !== 0 ? "is-default" : ""].filter(Boolean).join(" ");
        const bounds = TVView.viewBoundsStyle(this);
        const widthStyle = rendering.width ? `min-width:${rendering.width}` : "";
        const inlineStyle = [bounds, widthStyle, presentation.style].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const labelMarkup = rendering.labelMarkup || renderHotkeyMarkup(this.title);
        if (presentation.dialog) {
            const buttonClass = [presentation.baseClass, classNames].filter(Boolean).join(" ");
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

    draw() {
        return this.renderMarkup();
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
        const label = this.query(".tv-dialog-button-label");
        if (label) { label.innerHTML = renderHotkeyMarkup(this.title); }
        return this;
    }

    makeDefault(enable = true) {
        this.flags = enable ? (this.flags | bfDefault) : (this.flags & ~bfDefault);
        this.root?.classList.toggle("is-default", Boolean(enable));
        return this;
    }

    press() {
        if (this.root && !this.root.disabled) { this.root.click(); }
    }

    setState(state, enable) {
        if (state === "disabled") {
            this.disabled = Boolean(enable);
            if (this.root) { this.root.disabled = Boolean(enable); }
            return this;
        }
        return super.setState(state, enable);
    }
}

class TVFrame extends TVView {
    static titleControlMarkup({
        className = "", glyph = "", glyphClass = "", glyphAttrs = {}, attrs = {},
    } = {}) {
        const attrString = attrsToString(attrs);
        const glyphAttrString = attrsToString(glyphAttrs);
        const classes = ["tv-dialog-title-control", className].filter(Boolean).join(" ");
        const glyphClasses = ["tv-dialog-title-control-glyph", glyphClass].filter(Boolean).join(" ");
        return `<button type="button" class="${escapeHtml(classes)}" ${attrString}>[<span class="${escapeHtml(glyphClasses)}" ${glyphAttrString}>${escapeHtml(glyph)}</span>]</button>`;
    }

    static createTitleControl(options = {}) {
        return TVView.fromHTML(TVFrame.titleControlMarkup(options));
    }

    static closeMarkup(className, attrs = {}) {
        return TVFrame.titleControlMarkup({
            className,
            glyph: "■",
            glyphClass: "tv-close-glyph",
            glyphAttrs: { "data-tv-close-glyph": true },
            attrs: {
                ...attrs,
                "data-tv-close-button": true,
            },
        });
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
        modal = false,
        palette = "dialog",
    }) {
        const overlayClasses = ["tv-dialog-overlay", modal ? "is-modal" : "", overlayClass].filter(Boolean).join(" ");
        const windowClasses = ["tv-dialog-window", windowClass].filter(Boolean).join(" ");
        const titlebarClasses = ["tv-dialog-titlebar", titlebarClass].filter(Boolean).join(" ");
        const footerClasses = ["tv-dialog-footer", footerClass].filter(Boolean).join(" ");
        const titleClasses = ["tv-dialog-title-text", titleClass].filter(Boolean).join(" ");
        const closeClasses = ["tv-dialog-close-control", closeClass].filter(Boolean).join(" ");
        const bodyClasses = ["tv-dialog-body", bodyClass].filter(Boolean).join(" ");
        const renderBody = (value) => (
            value && typeof value.renderMarkup === "function"
                ? value.renderMarkup()
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
                + renderBody(bodyMarkup)
                + '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
        } else {
            bodyContent = renderBody(bodyMarkup);
        }
        return `
            <div class="${overlayClasses}" hidden>
                <div class="${windowClasses}" data-tv-palette="${escapeHtml(palette)}" role="dialog" aria-modal="${modal ? "true" : "false"}" aria-label="${escapeHtml(ariaLabel)}">
                    <div class="${titlebarClasses}">
                        <span class="tv-border-corner" aria-hidden="true">╔</span>
                        <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
                        <span class="tv-border-corner" aria-hidden="true">╗</span>
                        ${TVFrame.closeMarkup(closeClasses, closeAttrs)}
                        <div class="${titleClasses}">${escapeHtml(title)}</div>
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
        this.number = Number(number) || 0;
    }

    static renderMarkup({
        className = "",
        attrs = {},
        style = "",
        caption = "",
        contentMarkup = "",
        closeAttrs = {},
        zoomAttrs = {},
    } = {}) {
        const windowClasses = ["tv-window", className].filter(Boolean).join(" ");
        const windowAttrs = attrsToString({ "data-tv-window": true, ...attrs });
        const styleAttr = style ? ` style="${escapeHtml(style)}"` : "";
        const closeAttrString = attrsToString({
            type: "button",
            "data-tv-close-button": true,
            "aria-label": "Close window",
            ...closeAttrs,
        });
        const zoomAttrString = attrsToString({
            type: "button",
            "aria-label": "Zoom window",
            ...zoomAttrs,
        });
        return [
            `<main class="${escapeHtml(windowClasses)}" ${windowAttrs}${styleAttr}>`,
            `<div class="tv-shell">`,
            `<div class="tv-border-row tv-border-top" data-tv-move-handle>`,
            `<span class="tv-border-corner tv-border-corner-tl" data-tv-frame-corner="tl" aria-hidden="true">╔</span>`,
            `<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<button class="tv-close-control" ${closeAttrString}>[<span class="tv-close-glyph" data-tv-close-glyph>■</span>]</button>`,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<div class="tv-window-caption">${escapeHtml(caption)}</div>`,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<button class="tv-zoom-control" ${zoomAttrString}>[<span class="tv-zoom-glyph" data-tv-zoom-glyph>↑</span>]</button>`,
            `<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<span class="tv-border-corner tv-border-corner-tr" data-tv-frame-corner="tr" aria-hidden="true">╗</span>`,
            `</div>`,
            `<div class="tv-client-row">`,
            `<span class="tv-border-side tv-border-side-left" data-tv-border-side="║" aria-hidden="true"></span>`,
            `<div class="tv-frame"><div class="tv-scroll-shell" data-tv-scroll-frame>`,
            `<div class="tv-viewport" data-tv-viewport>${contentMarkup}</div>`,
            `</div></div>`,
            TVScrollBar.renderMarkup("y"),
            `<div class="tv-bottom-bar">`,
            `<span class="tv-scroll-corner tv-scroll-corner-left" data-tv-frame-corner="bl" aria-hidden="true">╚</span>`,
            `<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>`,
            TVScrollBar.renderMarkup("x"),
            `<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>`,
            `</div>`,
            `</div>`,
            `</div>`,
            `</main>`,
        ].join("");
    }

    static create(options = {}) {
        return TVView.fromHTML(TVWindow.renderMarkup(options));
    }
}

class TVDialog extends TVWindow {
    static footerMarkup() {
        return `
            <span class="tv-border-corner" aria-hidden="true">╚</span>
            <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
            <span class="tv-border-corner" aria-hidden="true">╝</span>
        `;
    }

    constructor(bounds, title, {
        desktop,
        viewName = "dialog",
        content = "",
        modal = false,
        palette = "dialog",
        helpCtx = hcDialog,
        keyboard = true,
        escapeCloses = true,
        defaultButtonSelector = ".tv-dialog-button.is-default",
    } = {}) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVDialog expects TVRect bounds");
        }
        const viewClass = String(viewName || "dialog").replace(/[^a-zA-Z0-9_-]/g, "-");
        const classPrefix = `tv-${viewClass}`;
        const root = TVView.fromHTML(
            TVFrame.dialogMarkup({
                overlayClass: `${classPrefix}-overlay`,
                windowClass: `${classPrefix}-window`,
                ariaLabel: title,
                titlebarClass: `${classPrefix}-titlebar`,
                bodyClass: `${classPrefix}-body`,
                footerClass: `${classPrefix}-footer`,
                titleClass: `${classPrefix}-title`,
                title,
                closeClass: `${classPrefix}-close-control`,
                closeAttrs: {
                    [`data-tv-${viewClass}-close`]: true,
                    "aria-label": `Close ${title || "dialog"}`,
                },
                bodyMarkup: content,
                footerMarkup: TVDialog.footerMarkup(),
                modal,
                palette,
            })
        );
        super(bounds, title);
        this.bindRoot(root);
        this.setHelpCtx(helpCtx);
        this.desktop = desktop;
        this.content = content instanceof TVView ? content : null;
        if (this.content) { this.content.owner = this; }
        this.overlay = root;
        this.dialog = this.query(".tv-dialog-window");
        this.content?.resolve(this.dialog);
        setElementHelpContext(this.dialog, helpCtx);
        this.titlebar = this.query(".tv-dialog-titlebar");
        this.closeButton = this.query(".tv-dialog-close-control");
        if (bounds.width) this.dialog.style.setProperty("--tv-dialog-width", `${bounds.width}ch`);
        if (bounds.height) this.dialog.style.setProperty("--tv-dialog-height", `${bounds.height}em`);
        this.hasPosition = false;
        this.dragState = null;
        this.manager = null;
        this.managerName = "";
        this.modal = modal;
        this.keyboard = keyboard;
        this.escapeCloses = escapeCloses;
        this.defaultButtonSelector = defaultButtonSelector;
        this.previousFocus = null;
        this.destroyed = false;
        this.closeAction = () => this.close();
        this.dialog.tabIndex = -1;
        this.mount(desktop);
        bindCloseButtons(this.overlay);
        this.dialog.addEventListener("click", (event) => this.dispatchDomEvent(evMouseDown, event));
        this.dialog.addEventListener("contextmenu", (event) => this.dispatchDomEvent(evMouseDown, event));
        this.dialog.addEventListener("input", (event) => this.dispatchDomEvent(evBroadcast, event));
        this.dialog.addEventListener("change", (event) => this.dispatchDomEvent(evBroadcast, event));
        this.dialog.addEventListener("keydown", (event) => {
            this.dispatchDomEvent(evKeyDown, event);
            this.onDialogKeyDown(event);
        });
    }

    dispatchDomEvent(what, nativeEvent) {
        const target = TVView.fromElement(nativeEvent.target) || this;
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
            const defaultButton = this.dialog.querySelector(this.defaultButtonSelector);
            if (defaultButton && !defaultButton.disabled) {
                event.preventDefault();
                event.stopPropagation();
                defaultButton.click();
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

    center() {
        const width = this.dialog.offsetWidth;
        const height = this.dialog.offsetHeight;
        const left = Math.max(0, Math.floor((this.overlay.clientWidth - width) / 2));
        const top = Math.max(0, Math.floor((this.overlay.clientHeight - height) / 2));
        this.dialog.style.setProperty("--tv-dialog-left", `${left}px`);
        this.dialog.style.setProperty("--tv-dialog-top", `${top}px`);
    }

    setSize({ width, height } = {}) {
        if (width) {
            this.dialog.style.setProperty("--tv-dialog-width", width);
        }
        if (height) {
            this.dialog.style.setProperty("--tv-dialog-height", height);
        }
        fillBorders(this.dialog);
    }

    bindCommonClose(onClose = () => this.close()) {
        this.closeAction = onClose;
        this.overlay.addEventListener("click", (event) => {
            if (event.target === this.overlay) {
                onClose();
            }
        });
        if (this.closeButton) {
            this.closeButton.addEventListener("mousedown", (event) => {
                if (event.button !== 0) { return; }
                event.preventDefault();
                event.stopPropagation();
                onClose();
            });
            this.closeButton.addEventListener("mouseup", (event) => {
                event.stopPropagation();
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
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        this.desktop = desktop;
        this.dialogs = new Map();
        this.windows = new Map();
        this.windowCommands = new Map();
        this.stackOrder = [];
        this.baseZIndex = 10;
        this.hostWindow = document.querySelector("[data-tv-window]");
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
        { flag: 0x0100, cmd: "yes",    label: "~Y~es", mnemonic: "y" },
        { flag: 0x0200, cmd: "no",     label: "~N~o", mnemonic: "n" },
        { flag: 0x0400, cmd: "ok",     label: "O~K~", mnemonic: "k" },
        { flag: 0x0800, cmd: "cancel", label: "~C~ancel", mnemonic: "c" },
    ];

    constructor(parentEl) {
        super(new TVRect(0, 0, 42, 12), "", {
            desktop: parentEl,
            viewName: "msgbox",
            content: TVRenderer.configure(new TVGroup(new TVRect()).insertAll([
                    TVRenderer.configure(new TVGroup(new TVRect()).insertAll([]), { presentation: "msgbox-content", viewName: "msgbox-content" }),
                    TVRenderer.configure(new TVGroup(new TVRect()).insertAll([]), { presentation: "msgbox-buttons", viewName: "msgbox-buttons" }),
                ]), { presentation: "msgbox-body", viewName: "msgbox-body" }),
            modal: true,
            keyboard: false,
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
        if (this.buttonsEl) {
            this.buttonsEl.addEventListener("click", (e) => {
                const btn = e.target.closest("[data-tv-msgbox-cmd]");
                if (btn) { this._dismiss(btn.getAttribute("data-tv-msgbox-cmd")); }
            });
        }
    }

    show({ type = 0, title, lines = [], buttons = TVMessageBox.MF_OK_BUTTON } = {}) {
        if (this._resolve) {
            this._dismiss(this._cancelCmd || this._defaultCmd);
        }
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
        const requestedButtons = TVMessageBox.BUTTON_DEFS.filter(b => (buttons & b.flag) !== 0);
        const btnDefs = requestedButtons.length
            ? requestedButtons
            : TVMessageBox.BUTTON_DEFS.filter(b => b.cmd === "ok");
        if (this.buttonsEl) {
            const btnHtml = btnDefs.map((b, index) =>
                new TVButton(new TVRect(), b.label, "msgbox-cmd", index === 0 ? bfDefault : bfNormal).setValue(b.cmd).renderMarkup()
            ).join("");
            this.buttonsEl.innerHTML = btnHtml;
        }
        this._buttonDefs = btnDefs;
        // Determine default and cancel commands
        this._defaultCmd = btnDefs.length > 0 ? btnDefs[0].cmd : null;
        this._cancelCmd = (buttons & TVMessageBox.MF_CANCEL_BUTTON) ? "cancel" : null;
        // Show
        super.open();
        // Focus first button
        const firstBtn = this.buttonsEl && this.buttonsEl.querySelector("button");
        if (firstBtn) { firstBtn.focus(); }
        // Bind events
        this.overlay.addEventListener("keydown", this._onKey);
        return new Promise((resolve) => { this._resolve = resolve; });
    }

    hide() {
        this.overlay.removeEventListener("keydown", this._onKey);
        super.close();
        this._resolve = null;
    }

    _dismiss(cmd) {
        const resolve = this._resolve;
        this.hide();
        if (resolve) { resolve(cmd); }
    }

    destroy() {
        const resolve = this._resolve;
        const command = this._cancelCmd || this._defaultCmd;
        this.overlay.removeEventListener("keydown", this._onKey);
        this._resolve = null;
        super.destroy();
        if (resolve) { resolve(command); }
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
            const key = e.key.toLowerCase();
            const definition = (this._buttonDefs || []).find((button) => button.mnemonic === key);
            if (definition) {
                const btn = this.buttonsEl && this.buttonsEl.querySelector(`[data-tv-msgbox-cmd="${definition.cmd}"]`);
                if (btn) { e.preventDefault(); e.stopPropagation(); this._dismiss(definition.cmd); }
            }
            if (!e.defaultPrevented) {
                e.stopPropagation();
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

class TVScrollBar extends TVView {
    static renderMarkup(axis, {
        rootClass = "",
        arrowClass = "",
        trackClass = "",
        cellsClass = "",
        thumbClass = "",
    } = {}) {
        const glyphs = axis === "y" ? ["▲", "▼"] : ["◄", "►"];
        return [
            `<div class="tv-scrollbar tv-scrollbar-${axis} ${escapeHtml(rootClass)}" data-axis="${axis}">`,
            `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-backward ${escapeHtml(arrowClass)}" data-role="backward" aria-label="Scroll ${axis} backward">${glyphs[0]}</button>`,
            `<div class="tv-scroll-track ${escapeHtml(trackClass)}" data-role="track"><div class="tv-scroll-cells ${escapeHtml(cellsClass)}" data-role="cells"></div><div class="tv-scroll-thumb ${escapeHtml(thumbClass)}" data-role="thumb"></div></div>`,
            `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-forward ${escapeHtml(arrowClass)}" data-role="forward" aria-label="Scroll ${axis} forward">${glyphs[1]}</button>`,
            `</div>`,
        ].join("");
    }

    constructor(bounds, options = 0) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVScrollBar expects TVRect bounds");
        }
        super(bounds);
        this.options = options;
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
        this.onWindowResize = () => this.update();
        this.onDocumentMouseUp = () => this.stopRepeat();
    }

    bindRoot(frame) {
        super.bindRoot(frame);
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
    }
}

const TurboVisionScrollbar = TVScrollBar;

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
        this.dialogManager = new TVDialogManager(this.root);
        return this;
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
    TVRect,
    TVRenderer,
    TVView,
    TVStaticText,
    TVLabel,
    TVInputLine,
    TVListViewer,
    TVGroup,
    TVInfoBox,
    TVTerminal,
    TVIndicator,
    TVEditor,
    TVListBox,
    TVVerticalListViewer,
    TVOutline,
    TVVerticalScrollArea,
    TVMenuView,
    TVMenuItem,
    TVMenuBox,
    TVStatusItem,
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
    TVDesktop,
    TVScrollBar,
    TurboVisionScrollbar,
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
