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
            "--tv-palette-desktop-bg": "#000000",
            "--tv-palette-desktop-fg": "#0000aa",
            "--tv-palette-menu-normal-bg": "#0000aa",
            "--tv-palette-menu-normal-fg": "#aaaaaa",
            "--tv-palette-menu-shortcut-fg": "#ffff55",
            "--tv-palette-menu-selected-bg": "#aaaaaa",
            "--tv-palette-menu-selected-fg": "#000000",
            "--tv-palette-menu-selected-shortcut-fg": "#aa0000",
            "--tv-palette-help-text-bg": "#000000",
            "--tv-palette-calendar-text-bg": "#000000",
            "--tv-palette-help-frame-active-bg": "#0000aa",
            "--tv-palette-help-frame-active-fg": "#aaaaaa",
            "--tv-palette-help-frame-icons-fg": "#55ffff",
            "--tv-palette-help-text-fg": "#aaaaaa",
            "--tv-muted": "#55ffff",
            "--tv-palette-help-keyword-fg": "#55ffff",
            "--tv-palette-help-keyword-selected-bg": "#00aaaa",
            "--tv-palette-help-keyword-selected-fg": "#000000",
            "--tv-palette-help-scroll-page-bg": "#000000",
            "--tv-palette-help-scroll-controls-bg": "#0000aa",
            "--tv-palette-help-scroll-controls-fg": "#ffffff",
            "--tv-palette-help-scroll-page-fg": "#5555ff",
            "--tv-palette-help-frame-passive-fg": "#aaaaaa",
            "--tv-palette-help-frame-passive-bg": "#000000",
            "--tv-palette-dialog-frame-active-bg": "#555555",
            "--tv-palette-dialog-static-fg": "#ffffff",
            "--tv-palette-dialog-frame-active-fg": "#ffff55",
            "--tv-palette-dialog-frame-passive-fg": "#ffffff",
            "--tv-palette-dialog-frame-passive-bg": "#555555",
            "--tv-palette-dialog-input-normal-bg": "#000000",
            "--tv-palette-dialog-input-normal-fg": "#55ffff",
            "--tv-palette-dialog-button-normal-bg": "#00aa00",
            "--tv-palette-dialog-button-normal-fg": "#000000",
            "--tv-palette-dialog-button-shadow-bg": "#555555",
            "--tv-palette-dialog-button-shadow-fg": "#000000",
            "--tv-palette-ascii-text-bg": "#555555",
            "--tv-palette-ascii-text-fg": "#ffffff",
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
            "--tv-palette-desktop-bg": "#aaaaaa",
            "--tv-palette-desktop-fg": "#0000aa",
            "--tv-palette-menu-normal-bg": "#aaaaaa",
            "--tv-palette-menu-selected-bg": "#00aa00",
            "--tv-palette-help-text-bg": "#00aa00",
            "--tv-palette-help-frame-active-bg": "#00aa00",
            "--tv-palette-help-frame-active-fg": "#ffffff",
            "--tv-palette-help-frame-icons-fg": "#55ff55",
            "--tv-palette-help-keyword-fg": "#ffff55",
            "--tv-palette-help-keyword-selected-bg": "#0000aa",
            "--tv-palette-help-keyword-selected-fg": "#ffff55",
            "--tv-palette-help-scroll-page-bg": "#0000aa",
            "--tv-palette-help-scroll-controls-bg": "#0000aa",
            "--tv-palette-help-scroll-controls-fg": "#00ff00",
            "--tv-palette-help-scroll-page-fg": "#00aa00",
            "--tv-palette-calendar-text-bg": "#00aaaa",
            "--tv-palette-calendar-text-fg": "#000000",
            "--tv-palette-calendar-current-fg": "#ffffff",
            "--tv-palette-ascii-text-bg": "#aaaaaa",
            "--tv-palette-ascii-text-fg": "#000000",
        },
    },
    amber: {
        label: "Amber",
        vars: {
            "--tv-palette-desktop-bg": "#000000",
            "--tv-palette-desktop-fg": "#aa5500",
            "--tv-palette-menu-normal-bg": "#aa5500",
            "--tv-palette-menu-normal-fg": "#000000",
            "--tv-palette-menu-shortcut-fg": "#ffff55",
            "--tv-palette-menu-selected-bg": "#ffaa00",
            "--tv-palette-menu-selected-fg": "#000000",
            "--tv-palette-menu-selected-shortcut-fg": "#aa0000",
            "--tv-palette-help-text-bg": "#aa5500",
            "--tv-palette-help-frame-active-bg": "#aa5500",
            "--tv-palette-help-frame-active-fg": "#ffff55",
            "--tv-palette-help-frame-icons-fg": "#ffff55",
            "--tv-palette-help-text-fg": "#000000",
            "--tv-palette-help-keyword-fg": "#ffff55",
            "--tv-palette-help-keyword-selected-bg": "#552200",
            "--tv-palette-help-keyword-selected-fg": "#ffff55",
            "--tv-palette-help-scroll-page-bg": "#552200",
            "--tv-palette-help-scroll-controls-bg": "#552200",
            "--tv-palette-help-scroll-controls-fg": "#ffff55",
            "--tv-palette-help-scroll-page-fg": "#ffaa00",
            "--tv-palette-calendar-text-bg": "#aa5500",
            "--tv-palette-calendar-text-fg": "#000000",
            "--tv-palette-calendar-current-fg": "#ffff55",
            "--tv-palette-ascii-text-bg": "#552200",
            "--tv-palette-ascii-text-fg": "#ffff55",
        },
    },
    gray: {
        label: "Gray",
        vars: {
            "--tv-palette-desktop-bg": "#aaaaaa",
            "--tv-palette-desktop-fg": "#555555",
            "--tv-palette-menu-normal-bg": "#aaaaaa",
            "--tv-palette-menu-normal-fg": "#000000",
            "--tv-palette-menu-shortcut-fg": "#555555",
            "--tv-palette-menu-selected-bg": "#ffffff",
            "--tv-palette-menu-selected-fg": "#000000",
            "--tv-palette-menu-selected-shortcut-fg": "#555555",
            "--tv-palette-help-text-bg": "#c0c0c0",
            "--tv-palette-help-frame-active-bg": "#aaaaaa",
            "--tv-palette-help-frame-active-fg": "#ffffff",
            "--tv-palette-help-frame-icons-fg": "#000000",
            "--tv-palette-help-text-fg": "#000000",
            "--tv-palette-help-keyword-fg": "#000000",
            "--tv-palette-help-keyword-selected-bg": "#555555",
            "--tv-palette-help-keyword-selected-fg": "#ffffff",
            "--tv-palette-help-scroll-page-bg": "#555555",
            "--tv-palette-help-scroll-controls-bg": "#555555",
            "--tv-palette-help-scroll-controls-fg": "#ffffff",
            "--tv-palette-help-scroll-page-fg": "#c0c0c0",
            "--tv-palette-calendar-text-bg": "#c0c0c0",
            "--tv-palette-calendar-text-fg": "#000000",
            "--tv-palette-calendar-current-fg": "#ffffff",
            "--tv-palette-ascii-text-bg": "#c0c0c0",
            "--tv-palette-ascii-text-fg": "#000000",
        },
    },
};
const DEFAULT_UI_CONFIG = Object.freeze({
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
const EDITOR_COLOR_ATTRIBUTE = 0x1e;
const WINDOW_PALETTE_INDEXES = Object.freeze({
    help: [128, 129, 130, 131, 132, 133],
    viewer: [8, 9, 10, 11, 12, 13],
    editor: [8, 9, 10, 11, 12, 13],
    dos: [128, 129, 130, 131, 132, 133],
    calendar: [16, 17, 18, 19, 20, 21],
    ascii: [24, 25, 26, 27, 28, 29],
    dialog: [32, 33, 34, 35, 36, 37],
    history: [50, 50, 50, 55, 54, 50],
});

function paletteStyle(properties) {
    return Object.entries(properties).flatMap(([name, index]) => {
        const variables = paletteVariables(index);
        return ["bg", "fg"].map((part) => `--tv-${name}-${part}:var(${variables[part][0]})`);
    }).join(";");
}
const THEME_VARIABLE_KEYS = [...new Set(
    Object.values(THEME_PRESETS).flatMap((preset) => Object.keys(preset.vars))
)];
let activeThemePreset = "default";
let activeColorPalette = null;
let measuredCell = null;
const HOST_WINDOW_TOKEN = "__host__";
const cmCut = 20;
const cmCopy = 21;
const cmPaste = 22;
const TV_COMMANDS = Object.freeze({
    MENU: "menu",
    CLOSE: "close",
    ZOOM: "zoom",
    RESIZE: "resize",
    DEFAULT_SIZE: "default-size",
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
    hcAccount: 2280,
    hcRegistration: 2290,
    hcRegistrationTokens: 2300,
    hcServerConfiguration: 2310,
    hcHelpPackages: 2311,
    hcDosPackages: 2312,
    hcMidiSources: 2315,
    hcDownloads: 2316,
    hcDosPrompt: 2320,
    hcUsers: 2350,
    hcGridDemo: 2340,
});
const {
    hcNoContext,
    hcApplication,
    hcDialog,
} = TV_HELP_CONTEXTS;

function normalizeHelpContext(value, fallback = hcNoContext) {
    if (typeof value === "string" && /^app:[a-z][a-z0-9_]{0,63}:[a-z][a-z0-9-]{0,63}$/.test(value)) { return value; }
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

// Native paint for numeric TVision palettes; browser CSS variables are the
// platform adapter for the application's editable cpAppColor attributes.
let nativeAppColors = null;
const nativePaletteViews = new Set();
let nativePaletteObserver = null;
function watchNativePalette(view, enabled) {
    if (enabled) { nativePaletteViews.add(view); } else { nativePaletteViews.delete(view); }
    if (nativePaletteViews.size && !nativePaletteObserver && typeof MutationObserver !== "undefined") {
        nativePaletteObserver = new MutationObserver(() => {
            nativeAppColors = null;
            for (const item of nativePaletteViews) { item._drawPalette(); }
        });
        nativePaletteObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["style"] });
    } else if (!nativePaletteViews.size && nativePaletteObserver) {
        nativePaletteObserver.disconnect(); nativePaletteObserver = null; nativeAppColors = null;
    }
}

function buildPaletteFromCurrentStyle() {
    const palette = buildDefaultColorPalette();
    const style = getComputedStyle(document.documentElement);
    palette.forEach((group) => {
        group.items.forEach((item) => {
            let fg = item.attr & 0x0F;
            let bg = (item.attr >> 4) & 0x0F;
            if (item.fg.length) {
                const color = parseCssColor(style.getPropertyValue(item.fg[0]));
                if (color) { fg = nearestDosColorIndex(color); }
            }
            if (item.bg.length) {
                const color = parseCssColor(style.getPropertyValue(item.bg[0]));
                if (color) { bg = nearestDosColorIndex(color); }
            }
            item.attr = ((bg & 0x0F) << 4) | (fg & 0x0F);
        });
    });
    return palette;
}

function applyColorPalette(palette, persist = false) {
    const root = document.documentElement;
    applyThemePreset(activeThemePreset, false);
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
    nativeAppColors = null;
    const requestedName = THEME_PRESETS[name] ? name : "default";
    const presetName = requestedName === "auto"
        ? ((window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light")
        : requestedName;
    const preset = THEME_PRESETS[presetName];
    const root = document.documentElement;
    THEME_VARIABLE_KEYS.forEach((key) => root.style.removeProperty(key));
    Object.keys(TV2_PALETTE_TOKENS).forEach((index) => {
        const attr = TV2_APP_COLOR_ATTRIBUTES[index - 1];
        const variables = paletteVariables(index);
        variables.bg.forEach((key) => root.style.setProperty(key, dosColor(attr, 4)));
        variables.fg.forEach((key) => root.style.setProperty(key, dosColor(attr, 0)));
    });
    Object.entries(preset.vars).forEach(([key, value]) => root.style.setProperty(key, value));
    activeThemePreset = requestedName;
    if (persist) {
        persistThemePreset(requestedName);
    }
}

function applyThemeAndSyncPalette(name, persist = false) {
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
    const cell = measureCells();

    container._tvFrame?._layout(cell);
    container.querySelectorAll("[data-tv-window], .tv-dialog-window").forEach((element) => element._tvFrame?._layout(cell));

    const borders = [];
    container.querySelectorAll("[data-tv-border-fill]").forEach((element) => {
        const char = element.getAttribute("data-tv-border-fill") || "\u2500";
        const count = Math.max(1, Math.ceil(element.clientWidth / cell.width) + 2);
        borders.push([element, char.repeat(count)]);
    });

    container.querySelectorAll("[data-tv-border-side]").forEach((element) => {
        const char = element.getAttribute("data-tv-border-side") || "\u2502";
        const count = Math.max(1, Math.ceil(element.clientHeight / cell.height));
        borders.push([element, Array.from({ length: count }, () => char).join("\n")]);
    });
    // Read every extent before writing text: each intervening write can force
    // layout of the entire desktop, including large lists in other windows.
    for (const [element, text] of borders) {
        if (element.textContent !== text) { element.textContent = text; }
    }
}

function setBorderFill(element, char) {
    if (element) {
        if (element.getAttribute("data-tv-border-fill") !== char) { element.setAttribute("data-tv-border-fill", char); }
    }
}

function setBorderSide(element, char) {
    if (element) {
        if (element.getAttribute("data-tv-border-side") !== char) { element.setAttribute("data-tv-border-side", char); }
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
    windowElement.querySelectorAll(".tv-list-viewer, .tv-vlist-viewer").forEach((listRoot) => {
        if (listRoot._tvListViewer) {
            listRoot._tvListViewer.setActive(active);
        }
    });
}

function updateWindowFrameState(windowElement, active, { dialog = false } = {}) {
    if (!windowElement) {
        return;
    }
    const view = windowElement._tvFrame?.owner || windowElement._tvView;
    if (view && view.getState(sfActive) !== Boolean(active)) { view.setState(sfActive, Boolean(active)); }
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
        : Array.from(windowElement.querySelectorAll(".tv-border-side-left, .tv-border-side-right"));
    const closeButton = windowElement.querySelector("[data-tv-close-button]");
    const closeGlyph = windowElement.querySelector("[data-tv-close-glyph]");
    const zoomButton = windowElement.querySelector("[data-tv-zoom-glyph]")?.closest("button, a");
    const resizeHandle = !dialog ? windowElement.querySelector("[data-tv-resize-handle]") : null;

    setOwnedWidgetsActive(windowElement, active);
    if (closeButton) {
        closeButton.hidden = view instanceof TVWindow && (view.flags & wfClose) === 0;
        closeButton.classList.toggle("is-frame-control-passive", !active);
        if (!active) {
            closeButton.tabIndex = -1;
        } else {
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
        const passive = zoomButton.querySelector(".tv-frame-passive");
        if (passive) { passive.hidden = dialog || active; }
    }

    if (topCorners[0]) {
        if (topCorners[0].textContent !== glyphs.topLeft) { topCorners[0].textContent = glyphs.topLeft; }
    }
    if (topCorners[topCorners.length - 1]) {
        if (topCorners.at(-1).textContent !== glyphs.topRight) { topCorners.at(-1).textContent = glyphs.topRight; }
    }
    topFills.forEach((element) => setBorderFill(element, glyphs.horizontal));
    sides.forEach((element) => setBorderSide(element, glyphs.vertical));

    if (dialog) {
        if (bottomCorners[0]) {
            if (bottomCorners[0].textContent !== glyphs.bottomLeft) { bottomCorners[0].textContent = glyphs.bottomLeft; }
        }
        if (bottomCorners[bottomCorners.length - 1]) {
            if (bottomCorners.at(-1).textContent !== glyphs.bottomRight) { bottomCorners.at(-1).textContent = glyphs.bottomRight; }
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
            if (leftCorner.textContent !== glyphs.bottomLeft) { leftCorner.textContent = glyphs.bottomLeft; }
        }
        bottomFills.forEach((element) => setBorderFill(element, glyphs.horizontal));
        if (resizeHandle) {
            // Turbo Vision 2.0 always draws the grow icon as a single-line
            // horizontal stroke plus the lower-right corner (TFrame::dragIcon).
            if (resizeHandle.textContent !== "─┘") { resizeHandle.textContent = "─┘"; }
        }
    }

    if (closeGlyph) {
        applyCloseGlyphState(closeButton, closeButton && pressedCloseButtons.has(closeButton));
    }

    fillBorders(windowElement);
}

function fillDesktopPatterns() {
    measuredCell = null;
    document.querySelectorAll("[data-tv-desktop-pattern]").forEach((element) => {
        const desktop = element.parentElement?._tvView;
        if (desktop instanceof TVDesktop) { desktop.drawView(); }
    });
}

function updateClocks() {
    const now = new Date();
    const text = [now.getHours(), now.getMinutes(), now.getSeconds()]
        .map((value) => String(value).padStart(2, "0"))
        .join(":");
    document.querySelectorAll("[data-tv-menu-bar]").forEach((element) => {
        element._tvMenuView?.clock?.setText(`\x03${text}`);
    });
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function wrapTextLines(text, columns) {
    const width = Math.max(1, Math.floor(columns));
    return String(text).split(/\r\n|\r|\n/).flatMap((line) => {
        const chars = Array.from(line), rows = [];
        while (chars.length > width) {
            const space = chars.slice(0, width + 1).lastIndexOf(" ");
            const count = space > 0 ? space : width;
            rows.push(chars.splice(0, count).join(""));
            if (chars[0] === " ") { chars.shift(); }
        }
        rows.push(chars.join(""));
        return rows;
    });
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
    const text = active ? CLOSE_PRESSED_CHAR : "\u25A0";
    if (glyph.textContent !== text) { glyph.textContent = text; }
}

const boundCloseButtons = new WeakSet();
const pressedCloseButtons = new WeakSet();

function bindCloseButtons(scope) {
    scope.querySelectorAll("[data-tv-close-button]").forEach((button) => {
        if (boundCloseButtons.has(button)) { return; }
        boundCloseButtons.add(button);
        let mouseDown = false;
        let fallbackTimer = 0;
        const setPressed = (pressed) => {
            if (pressed) { pressedCloseButtons.add(button); }
            else { pressedCloseButtons.delete(button); }
            applyCloseGlyphState(button, pressed);
        };
        button.addEventListener("mousedown", (event) => {
            if (event.button !== 0) { return; }
            if (fallbackTimer) { window.clearTimeout(fallbackTimer); fallbackTimer = 0; }
            mouseDown = true;
            setPressed(true);
            document.addEventListener("mouseup", (release) => {
                const wasDown = mouseDown;
                mouseDown = false;
                setPressed(false);
                if (!wasDown || release.button !== 0) { return; }
                const bounds = button.getBoundingClientRect();
                const inside = button.contains(release.target)
                    || (release.clientX >= bounds.left && release.clientX < bounds.right
                        && release.clientY >= bounds.top && release.clientY < bounds.bottom);
                if (!inside) { return; }
                // Safari can omit click after an inactive window gains focus on mousedown.
                // Let the native click run first; synthesize it only if it never arrives.
                fallbackTimer = window.setTimeout(() => {
                    fallbackTimer = 0;
                    if (button.isConnected && !button.disabled
                        && !button.closest(".tv-dialog-overlay")?.hidden) { button.click(); }
                }, 0);
            }, { once: true });
        });
        button.addEventListener("click", () => {
            mouseDown = false;
            setPressed(false);
            if (fallbackTimer) { window.clearTimeout(fallbackTimer); fallbackTimer = 0; }
        });
        button.addEventListener("mouseleave", () => setPressed(false));
        button.addEventListener("blur", () => setPressed(false));
    });
}

function cloneUiConfig(config) {
    return {
        status: Array.isArray(config?.status) ? config.status.map((entry) => ({ ...entry })) : [],
    };
}

function resolveUiConfig() {
    const base = cloneUiConfig(DEFAULT_UI_CONFIG);
    const override = window.TV_UI_CONFIG;
    if (!override || typeof override !== "object") {
        return base;
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
let focusVersion = 0;

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
const kbCtrlIns = 0x0400;
const kbShiftIns = 0x0500;
const kbShiftDel = 0x0700;
const kbF1 = 0x3b00;
const kbF3 = 0x3d00;
const kbF4 = 0x3e00;
const kbF5 = 0x3f00;
const kbF6 = 0x4000;
const kbShiftF6 = 0x5900;
const kbAltF3 = 0x6d00;
const kbAlt0 = 0x8100;

function getKeyCode(event) {
    if (!event || event.metaKey) { return kbNoKey; }
    if (!event.altKey && event.key === "Insert") {
        if (event.ctrlKey && !event.shiftKey) { return kbCtrlIns; }
        if (event.shiftKey && !event.ctrlKey) { return kbShiftIns; }
    }
    if (event.key === "Delete" && event.shiftKey && !event.ctrlKey && !event.altKey) { return kbShiftDel; }
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
        if (event.key === "F4" && !event.shiftKey) { return kbF4; }
        if (event.key === "F5" && !event.shiftKey) { return kbF5; }
        if (event.key === "F6") { return event.shiftKey ? kbShiftF6 : kbF6; }
    }
    return kbNoKey;
}

function clipboardKeyCommand(event) {
    switch (getKeyCode(event)) {
        case kbCtrlIns: return cmCopy;
        case kbShiftIns: return cmPaste;
        case kbShiftDel: return cmCut;
        default: return 0;
    }
}

async function writeClipboardText(text) {
    if (!navigator.clipboard?.writeText) { throw new Error("System clipboard is unavailable in this browser."); }
    await navigator.clipboard.writeText(String(text));
}

async function readClipboardText() {
    if (!navigator.clipboard?.readText) { throw new Error("System clipboard is unavailable in this browser."); }
    return navigator.clipboard.readText();
}

function saveLocalFile(name, bytes) {
    if (typeof name !== "string" || !name || /[\\/:\x00-\x1f\x7f]/.test(name) || !(bytes instanceof Uint8Array)) {
        throw new Error("Invalid local file export");
    }
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
    const link = document.createElement("a"); link.href = url; link.download = name;
    link.hidden = true; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
}

function viewAcceptsInput(view) {
    for (let current = view; current; current = current.owner) {
        if (!current.getState(sfVisible) || current.getState(sfDisabled)
            || current.root?.hidden || current.root?.disabled) { return false; }
    }
    return true;
}

function owningDesktop(view) {
    let top = view;
    for (let current = view; current; current = current.owner) {
        if (current instanceof TVDesktop) { return current; }
        top = current;
    }
    return top?.desktopView || top?.manager?.desktop
        || top?.firstThat?.(view => view instanceof TVDesktop) || null;
}

async function messageBox(owner, options) {
    const desktop = owningDesktop(owner) || owner.root?.closest?.(".tv-desktop")?._tvView;
    if (!(desktop instanceof TVDesktop)) { return; }
    const box = new TVMessageBox();
    desktop.insert(box);
    try { return await box.show(options); }
    finally { box.destroy(); }
}

function handleClipboardEvent(view, event) {
    const native = event.nativeEvent;
    if (event.what === evKeyDown && native?.defaultPrevented) { return false; }
    const command = event.what === evKeyDown ? clipboardKeyCommand(native)
        : event.what === evCommand ? event.command : 0;
    const method = command === cmCopy ? "clipCopy" : command === cmCut ? "clipCut"
        : command === cmPaste ? "clipPaste" : "";
    if (!method || typeof view[method] !== "function") { return false; }
    if (!view.commandEnabled(command)) {
        native?.preventDefault();
        view.clearEvent(event);
        return true;
    }
    const manager = owningDesktop(view)?.dialogManager, dialog = manager?.get(manager.activeTarget);
    if (dialog?.isOpen() && dialog.getState(sfModal) && !(view instanceof TVProgram)
        && !dialog.dialog.contains(view.root)) {
        native?.preventDefault();
        view.clearEvent(event);
        manager._focusTarget(manager.activeTarget);
        return true;
    }
    if (!viewAcceptsInput(view)) {
        native?.preventDefault();
        view.clearEvent(event);
        return true;
    }
    if (event.what === evKeyDown) { event.what = evCommand; event.command = command; }
    // Native editable-input clipboard actions preserve the browser's undo stack
    // and paste permission flow. Input broadcasts still pass through validators.
    if (native?.clipboardData && (view instanceof TVInputLine || (view instanceof TVEditor && command !== cmCopy))) {
        if (view.disabled || (command !== cmCopy && (view.readOnly || view.root?.readOnly))) { native.preventDefault(); }
    } else {
        native?.preventDefault();
        void view[method](native).catch((error) => {
            void messageBox(view, { title: "Clipboard", type: TVMessageBox.MF_ERROR,
                lines: [error.message, "Use your system's Copy/Paste shortcut or browser menu."] });
        });
    }
    view.clearEvent(event);
    return true;
}

const cmCommandSetChanged = 52;

class TVCommandSet {
    constructor(commands = []) {
        this._defaultEnabled = commands instanceof TVCommandSet ? commands._defaultEnabled : false;
        this._commands = new Set(commands instanceof TVCommandSet ? commands._commands : commands);
    }

    has(command) { return this._defaultEnabled !== this._commands.has(command); }
    enableCmd(command) { this._commands[this._defaultEnabled ? "delete" : "add"](command); return this; }
    disableCmd(command) { this._commands[this._defaultEnabled ? "add" : "delete"](command); return this; }
    isEmpty() { return !this._defaultEnabled && this._commands.size === 0; }

    _equals(other) {
        return this._defaultEnabled === other._defaultEnabled && this._commands.size === other._commands.size
            && [...this._commands].every(command => other._commands.has(command));
    }

    _combine(other, enable) {
        const result = new TVCommandSet();
        result._defaultEnabled = enable ? this._defaultEnabled || other._defaultEnabled
            : this._defaultEnabled && !other._defaultEnabled;
        for (const command of new Set([...this._commands, ...other._commands])) {
            const enabled = enable ? this.has(command) || other.has(command) : this.has(command) && !other.has(command);
            if (enabled !== result._defaultEnabled) { result._commands.add(command); }
        }
        return result;
    }
}

let currentCommands = new TVCommandSet();
currentCommands._defaultEnabled = true;
const commandViews = new Set();
const pendingCommandRoots = new Set();
let notifyingCommands = false;

function watchCommands(view, enabled) {
    if (enabled) { commandViews.add(view); } else { commandViews.delete(view); }
}

function commandDisabled(item) {
    return Boolean(item?.disabled || (item?.command && !currentCommands.has(item.command)));
}

function notifyCommands(source) {
    for (let view of [source, ...commandViews]) {
        while (view.owner instanceof TVGroup && view.owner.children.includes(view)) { view = view.owner; }
        pendingCommandRoots.add(view);
    }
    if (notifyingCommands) { return; }
    notifyingCommands = true;
    try {
        while (pendingCommandRoots.size) {
            const roots = [...pendingCommandRoots]; pendingCommandRoots.clear();
            for (const view of roots) {
                if (view instanceof TVGroup) { view.broadcast(cmCommandSetChanged); }
                else if ((view.eventMask & evBroadcast) !== 0) {
                    view.handleEvent(new TVEvent(evBroadcast, { command: cmCommandSetChanged }));
                }
            }
        }
    } finally { notifyingCommands = false; }
}

function recordStatisticsEvent(event, { beacon = false } = {}) {
    const body = JSON.stringify(event);
    if (beacon && typeof navigator.sendBeacon === "function") {
        try {
            if (navigator.sendBeacon(
                "/api/statistics/events",
                new Blob([body], { type: "application/json" }),
            )) { return; }
        } catch {
            // Fall through to a keepalive request.
        }
    }
    void fetch("/api/statistics/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
    }).catch(() => {});
}

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
        if (this.root && this.root !== root) { this.setState(sfFocused, false); }
        if (this.root?._tvView === this) { delete this.root._tvView; }
        this.root = root || null;
        if (this.root) { this.root._tvView = this; }
        setElementHelpContext(this.root, this.helpCtx);
        watchNativePalette(this, Boolean(this.root?.style && this._paletteAttribute() !== null));
        this._drawPalette();
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
        return (this.state & state) === state;
    }

    show() { return this.setState(sfVisible, true); }
    hide() { return this.setState(sfVisible, false); }
    exposed() { return this.getState(sfVisible) && !this.root?.hidden; }

    _focusTarget() { return this.root; }

    _canFocus() {
        if ((this.options & ofSelectable) === 0 || !viewAcceptsInput(this)) { return false; }
        const target = this._focusTarget();
        return !this.root || Boolean(target && !target.disabled && !target.hidden
            && target.isConnected !== false && target.getAttribute?.("aria-hidden") !== "true"
            && !target.closest?.("[hidden]") && target.tabIndex >= 0);
    }

    focus() {
        if (!viewAcceptsInput(this)) { return this; }
        const target = this._focusTarget();
        target?.focus?.();
        if (!this.root || (target && document.activeElement === target)) { this._recordFocus(target); }
        return this;
    }

    _recordFocus(element = null) {
        if (!viewAcceptsInput(this) || (element && document.activeElement !== element)) { return; }
        const version = ++focusVersion, path = [this];
        for (let child = this, owner = this.owner; owner instanceof TVGroup
            && !(owner instanceof TVDesktop || owner instanceof TVProgram) && owner.children.includes(child);
            child = owner, owner = owner.owner) { path.push(owner); }
        const current = () => version === focusVersion && (!element || document.activeElement === element);
        for (let index = path.length - 1; index > 0; index--) {
            if (!current()) { return; }
            const owner = path[index], child = path[index - 1];
            owner.setCurrent(child);
            if (owner.current !== child) { return; }
        }
        if (this instanceof TVGroup) { this.current?.setState(sfFocused, false); }
        for (let index = path.length - 1; index >= 0; index--) {
            if (!current()) { return; }
            const view = path[index];
            if (view instanceof TVGroup) { TVView.prototype.setState.call(view, sfFocused, true); }
            else { view.setState(sfFocused, true); }
        }
    }

    select() {
        const owner = this.owner;
        if ((this.options & ofSelectable) === 0 || !(owner instanceof TVGroup) || !owner.children.includes(this)) { return this; }
        if ((this.options & ofTopSelect) !== 0) {
            const managed = owner instanceof TVDesktop && owner.dialogManager?._targetName(this) != null;
            const current = owner.current, version = focusVersion;
            this.makeFirst();
            if (managed || this.owner !== owner || !owner.children.includes(this) || owner.current !== current
                || version !== focusVersion || (this.options & ofSelectable) === 0 || !this.getState(sfVisible)) { return this; }
        }
        owner.setCurrent(this);
        return this;
    }

    makeFirst() {
        if (this.owner instanceof TVGroup) { this.owner._reorder(this); }
        return this;
    }

    nextView() {
        if (!(this.owner instanceof TVGroup)) { return null; }
        const index = this.owner.indexOf(this);
        return index < 0 ? null : this.owner.at(index + 1);
    }

    prevView() {
        if (!(this.owner instanceof TVGroup)) { return null; }
        const index = this.owner.indexOf(this);
        return index <= 0 ? null : this.owner.at(index - 1);
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
        const grow = (value, size, difference) => {
            if ((this.growMode & gfGrowRel) === 0) { return value + difference; }
            const previous = size - difference;
            return previous ? Math.trunc((value * size + Math.floor(previous / 2)) / previous) : value;
        };
        bounds.x1 = this.bounds.x1;
        bounds.y1 = this.bounds.y1;
        bounds.x2 = this.bounds.x2;
        bounds.y2 = this.bounds.y2;
        if ((this.growMode & gfGrowLoX) !== 0) { bounds.x1 = grow(bounds.x1, this.owner?.size.x ?? change.x, change.x); }
        if ((this.growMode & gfGrowLoY) !== 0) { bounds.y1 = grow(bounds.y1, this.owner?.size.y ?? change.y, change.y); }
        if ((this.growMode & gfGrowHiX) !== 0) { bounds.x2 = grow(bounds.x2, this.owner?.size.x ?? change.x, change.x); }
        if ((this.growMode & gfGrowHiY) !== 0) { bounds.y2 = grow(bounds.y2, this.owner?.size.y ?? change.y, change.y); }
        const limits = this.sizeLimits();
        bounds.x2 = bounds.x1 + Math.max(limits.min.x, Math.min(limits.max.x, bounds.width));
        bounds.y2 = bounds.y1 + Math.max(limits.min.y, Math.min(limits.max.y, bounds.height));
        return bounds;
    }

    commandEnabled(command) { return currentCommands.has(command); }

    disableCommands(commands) {
        const values = commands instanceof TVCommandSet ? commands
            : new TVCommandSet(commands instanceof Set || Array.isArray(commands) ? commands : [commands]);
        this.setCommands(currentCommands._combine(values, false));
    }

    enableCommands(commands) {
        const values = commands instanceof TVCommandSet ? commands
            : new TVCommandSet(commands instanceof Set || Array.isArray(commands) ? commands : [commands]);
        this.setCommands(currentCommands._combine(values, true));
    }

    getCommands() {
        return new TVCommandSet(currentCommands);
    }

    setCommands(commands) {
        const enabled = new TVCommandSet(commands);
        if (currentCommands._equals(enabled)) { return; }
        currentCommands = enabled;
        notifyCommands(this);
    }

    endModal(command) { return this.owner?.endModal?.(command); }
    execute() { return 0; }
    getClipRect() { return this.getExtent(); }
    getColor(color) {
        const palette = this.getPalette();
        const mapped = Array.isArray(palette) ? palette[color - 1] : color;
        return this.owner?.getColor?.(mapped) ?? mapped;
    }
    getPalette() { return null; }

    _appColor(index) {
        if (!nativeAppColors) {
            nativeAppColors = new Map(buildPaletteFromCurrentStyle().flatMap(group => group.items.map(item => [item.paletteIndex, item.attr])));
        }
        return nativeAppColors.get(index) ?? TV2_APP_COLOR_ATTRIBUTES[index - 1];
    }

    _paletteAttribute() {
        for (let view = this; view; view = view.owner) {
            if (!Array.isArray(view.getPalette())) { continue; }
            const attr = this.getColor(1);
            return Number.isInteger(attr) && attr >= 0 && attr <= 255 ? attr : null;
        }
        return null;
    }

    _paletteStyle() {
        const attr = this._paletteAttribute();
        return attr === null ? "" : `color:${dosColor(attr, 0)};background-color:${dosColor(attr, 4)}`;
    }

    _paintPalette(element, attribute) {
        if (!element) { return; }
        this._partPalettes ||= new WeakMap();
        if (this._partPalettes.get(element) === attribute) { return; }
        element.style.color = attribute === null ? "" : dosColor(attribute, 0);
        element.style.backgroundColor = attribute === null ? "" : dosColor(attribute, 4);
        this._partPalettes.set(element, attribute);
    }

    _paintPaletteText(element, attribute, shortcut = attribute) {
        if (!element) { return; }
        this._paintPalette(element, attribute);
        element.querySelectorAll(".tv-hotkey").forEach(key => this._paintPalette(key, (attribute & 0xf0) | (shortcut & 15)));
    }

    _drawPalette() {
        if (this.root) { this._paintPalette(this.root, this._paletteAttribute()); }
        return this;
    }

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

    putInFrontOf(target = null) {
        if (this.owner instanceof TVGroup) { this.owner._reorder(this, target); }
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
        this._drawBounds();
        return this;
    }

    _placePart(element, bounds) {
        if (!element) { return; }
        this._partBounds ||= new WeakMap();
        if (this._partBounds.get(element)?.equals(bounds)) { return; }
        element.style.position = "absolute";
        element.style.left = `${bounds.x1}ch`;
        element.style.top = `${bounds.y1}em`;
        element.style.width = `${bounds.width}ch`;
        element.style.height = `${bounds.height}em`;
        this._partBounds.set(element, bounds);
    }

    _drawBounds() {
        if (!this.root) { return; }
        const bounds = this.bounds;
        const positioned = !(bounds.x1 === 0 && bounds.y1 === 0 && bounds.x2 === 0 && bounds.y2 === 0);
        this.root.style.position = positioned ? "absolute" : "";
        this.root.style.left = positioned ? `${bounds.x1}ch` : "";
        this.root.style.top = positioned ? `${bounds.y1}em` : "";
        this.root.style.width = positioned && bounds.width ? `${bounds.width}ch` : "";
        this.root.style.height = positioned && bounds.height ? `${bounds.height}em` : "";
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
        const nativeTab = event.what === evKeyDown && event.nativeEvent?.key === "Tab"
            && event.nativeEvent.type !== "keyup";
        let view = this;
        while (view && event.what !== evNothing) {
            if ((view.eventMask & event.what) !== 0) { view.handleEvent(event); }
            view = view.owner;
        }
        if (nativeTab && event.what === evNothing) { event.nativeEvent.preventDefault(); }
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

    _textBoundsStyle() {
        return [TVView._viewBoundsStyle(this), this.size.x > 0 && this.size.y > 0 ? "overflow:hidden" : ""]
            .filter(Boolean).join(";");
    }

    _drawBounds() {
        super._drawBounds();
        if (this.root) { this.root.style.overflow = this.size.x > 0 && this.size.y > 0 ? "hidden" : ""; }
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
        const bounds = this._textBoundsStyle();
        const alignStyle = centered ? "text-align:center" : "";
        const inlineStyle = [bounds, alignStyle, this._paletteStyle()].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const semanticName = this._semanticName();
        const attrString = attrsToString(this._drawAttrs({
            hidden: !this.getState(sfVisible),
            ...(semanticName ? {
                [`data-tv-${semanticName}`]: true,
                "data-tv-row": semanticName,
            } : {}),
            ...(role === "calc-display" ? { "aria-live": "polite" } : {}),
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
            const content = centered ? this.text.slice(1) : this.text;
            if (this.root.childElementCount || this.root.textContent !== content) { this.root.textContent = content; }
            this.root.style.textAlign = centered ? "center" : "";
        }
        return this;
    }

}

class TVTextScreen extends TVView {
    constructor(bounds) {
        super(bounds);
        this.screen = null;
        this._blinkTimer = null;
        this._blinkVisible = true;
        this._motionQuery = null;
        this._onMotionChange = () => this._updateBlinkTimer();
        this.eventMask = 0;
    }

    setData(screen) {
        if (!screen || !Number.isInteger(screen.cols) || screen.cols < 1 || screen.cols > 512
            || !Number.isInteger(screen.rows) || screen.rows < 1 || screen.rows > 512
            || !Array.isArray(screen.cells) || screen.cells.length !== screen.cols * screen.rows) {
            throw new TypeError("Invalid TVTextScreen dimensions/cells");
        }
        const font = screen.font;
        if (!font || !Number.isInteger(font.width) || font.width < 1 || font.width > 32
            || !Number.isInteger(font.height) || font.height < 1 || font.height > 64
            || !(font.data instanceof Uint8Array)
            || font.data.length !== 256 * font.height * Math.ceil(font.width / 8)) {
            throw new TypeError("Invalid TVTextScreen bitmap font");
        }
        if (screen.cells.some(cell => !Array.isArray(cell) || cell.length !== 3
            || cell.some(value => !Number.isInteger(value) || value < 0 || value > 255)
            || cell.slice(1).some(index => typeof screen.palette?.[index] !== "string"))) {
            throw new TypeError("Invalid TVTextScreen glyph/palette index");
        }
        if (screen.blink !== undefined && (!Array.isArray(screen.blink)
            || screen.blink.length !== screen.cells.length || screen.blink.some(flag => typeof flag !== "boolean"))) {
            throw new TypeError("Invalid TVTextScreen blink mask");
        }
        if (screen.cols * font.width * screen.rows * font.height > 16777216) {
            throw new TypeError("TVTextScreen bitmap is too large");
        }
        this._stopBlink();
        this.screen = screen;
        this._paint();
        this._startBlink();
        return this;
    }

    getData() { return this.screen; }
    dataSize() { return this.screen ? this.screen.cells.length * 3 + (this.screen.blink?.length || 0) : 0; }

    draw() {
        if (!this.screen) { return ""; }
        const { cols, rows, font, text = [] } = this.screen;
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds || `width:${cols}ch;height:${rows}em`;
        return `<canvas class="tv-text-screen" ${attrsToString(this._drawAttrs())}`
            + ` width="${cols * font.width}" height="${rows * font.height}" style="${escapeHtml(style)}"`
            + ` role="img" aria-label="${escapeHtml(text.join("\n"))}">${escapeHtml(text.join("\n"))}</canvas>`;
    }

    bindRoot(root) {
        this._stopBlink();
        super.bindRoot(root);
        this._paint();
        this._startBlink();
        return this;
    }

    destroy() { this.bindRoot(null); }

    _stopBlink() {
        if (this._blinkTimer !== null) { window.clearInterval(this._blinkTimer); }
        this._blinkTimer = null;
        this._blinkVisible = true;
        this._motionQuery?.removeEventListener("change", this._onMotionChange);
        this._motionQuery = null;
    }

    _startBlink() {
        if (!this.root || !this.screen?.blink?.some(Boolean) || typeof window === "undefined") { return; }
        this._motionQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)") || null;
        this._motionQuery?.addEventListener("change", this._onMotionChange);
        this._updateBlinkTimer();
    }

    _updateBlinkTimer() {
        if (this._blinkTimer !== null) { window.clearInterval(this._blinkTimer); }
        this._blinkTimer = null;
        this._blinkVisible = true;
        this._paint();
        if (!this.root || !this.screen?.blink?.some(Boolean) || this._motionQuery?.matches) { return; }
        // VGA text blink changes phase every 16 frames at the standard 70 Hz.
        this._blinkTimer = window.setInterval(() => {
            if (!this.root || this.root.isConnected === false) { this._stopBlink(); return; }
            this._blinkVisible = !this._blinkVisible;
            this._paint();
        }, 16000 / 70);
    }

    _paint() {
        if (!this.root || !this.screen) { return; }
        const context = this.root.getContext?.("2d");
        if (!context) { return; }
        const { cols, rows, cells, font, palette } = this.screen;
        this.root.width = cols * font.width;
        this.root.height = rows * font.height;
        const stride = Math.ceil(font.width / 8);
        cells.forEach(([glyph, fg, bg], index) => {
            const x = (index % cols) * font.width, y = Math.floor(index / cols) * font.height;
            context.fillStyle = palette[bg];
            context.fillRect(x, y, font.width, font.height);
            if (this.screen.blink?.[index] && !this._blinkVisible) { return; }
            context.fillStyle = palette[fg];
            for (let row = 0; row < font.height; row += 1) {
                for (let bit = 0; bit < font.width; bit += 1) {
                    const byte = font.data[(glyph * font.height + row) * stride + Math.floor(bit / 8)];
                    if (byte & (0x80 >> (bit % 8))) { context.fillRect(x + bit, y + row, 1, 1); }
                }
            }
        });
    }
}

class TVImage extends TVView {
    constructor(bounds) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVImage expects TVRect bounds");
        }
        super(bounds);
        this.src = "";
        this.alt = "";
        this._picture = null;
        this._placeholder = null;
        this.resizeObserver = null;
        this._onImageState = (event) => {
            if (event.currentTarget === this._picture) { this._updateImage(); }
        };
    }

    getPalette() { return [0x07]; }

    bindRoot(root) {
        if (root === this.root) { return this; }
        this.resizeObserver?.disconnect();
        this.resizeObserver = null;
        for (const type of ["load", "error"]) { this._picture?.removeEventListener(type, this._onImageState); }
        super.bindRoot(root);
        this._picture = this.root?.querySelector("img") || null;
        this._placeholder = this.root?.querySelector("span") || null;
        for (const type of ["load", "error"]) { this._picture?.addEventListener(type, this._onImageState); }
        if (root && "ResizeObserver" in window) {
            this.resizeObserver = new ResizeObserver(() => {
                if (this.root === root) { measuredCell = null; this._layout(); }
            });
            this.resizeObserver.observe(root);
        }
        return this.drawView();
    }

    draw() {
        const bounds = [TVView._viewBoundsStyle(this), this._paletteStyle()].filter(Boolean).join(";");
        const attrs = attrsToString(this._drawAttrs({ hidden: !this.getState(sfVisible) }));
        return `<div class="tv-image"${bounds ? ` style="${escapeHtml(bounds)}"` : ""} ${attrs}>`
            + `<img alt="${escapeHtml(this.alt)}"${this.src ? ` src="${escapeHtml(this.src)}"` : ""} hidden>`
            + `<span>${this.src ? "Loading" : "No cover"}</span></div>`;
    }

    _updateImage() {
        const picture = this._picture;
        const ready = Boolean(this.src && picture?.complete && picture.naturalWidth > 0
            && picture.currentSrc === picture.src);
        if (picture) { picture.hidden = !ready; }
        if (this._placeholder) {
            const text = this.src && picture && !picture.complete ? "Loading" : "No cover";
            if (this._placeholder.textContent !== text) { this._placeholder.textContent = text; }
            this._placeholder.hidden = ready;
        }
        this._layout();
    }

    _layout() {
        if (!this.root) { return; }
        const cell = measureCells(), width = this.root.clientWidth / cell.width, height = this.root.clientHeight / cell.height;
        this._placePart(this._picture, new TVRect(0, 0, width, height));
        const columns = Math.min(width, this._placeholder?.textContent.length || 0), rows = Math.min(1, height);
        const left = (width - columns) / 2, top = (height - rows) / 2;
        this._placePart(this._placeholder, new TVRect(left, top, left + columns, top + rows));
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this._layout();
        return this;
    }

    setState(state, enable) {
        super.setState(state, enable);
        if ((state & sfVisible) !== 0 && enable) { this._layout(); }
        return this;
    }

    drawView() {
        if (!this.root) { return this; }
        this._drawBounds();
        this.root.hidden = !this.getState(sfVisible);
        const picture = this._picture;
        if (picture) {
            if (picture.alt !== this.alt) { picture.alt = this.alt; }
            if (this.src) {
                if (picture.getAttribute("src") !== this.src) { picture.src = this.src; }
            } else if (picture.hasAttribute("src")) { picture.removeAttribute("src"); }
        }
        this._updateImage();
        return this;
    }

    setImage(src, alt = "") {
        this.src = String(src || "");
        this.alt = String(alt || "");
        return this.drawView();
    }

    destroy() { this.bindRoot(null); }
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
        const percent = Number(y) || 0, total = Number(z) || 0;
        const scaled = total * percent;
        return Math.trunc(Number.isFinite(scaled) ? scaled / 100 : total * (percent / 100));
    }

    solveForY(x, z) {
        const total = Number(z) || 0;
        const current = Number(x) || 0, scaled = current * 100;
        return total === 0 ? 0 : current === total ? 100
            : Math.trunc(Number.isFinite(scaled) ? scaled / total : (current / total) * 100);
    }

    _gaugeValues() {
        const maximum = Number(this.maxValue), current = Number(this.curValue);
        const maxValue = Number.isFinite(maximum) ? Math.max(0, maximum) : 0;
        const curValue = Number.isFinite(current) ? Math.min(maxValue, Math.max(0, current)) : 0;
        return { maxValue, curValue };
    }

    _gaugeText() {
        const { curValue, maxValue } = this._gaugeValues();
        return `${String(this.solveForY(curValue, maxValue)).padEnd(3, " ")}%`;
    }

    _gaugeAttrs() {
        return this._drawAttrs({
            [`data-tv-${this._semanticName()}`]: true,
            hidden: !this.getState(sfVisible),
        });
    }

    draw() {
        const bounds = [TVView._viewBoundsStyle(this), this._paletteStyle()].filter(Boolean).join(";");
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const attrs = attrsToString(this._gaugeAttrs());
        return `<div class="tv-gauge tv-${this._semanticName()}"${style} ${attrs}>${escapeHtml(this._gaugeText())}</div>`;
    }

    drawView() {
        if (!this.root) { return this; }
        const text = this._gaugeText();
        if (this.root.textContent !== text) { this.root.textContent = text; }
        for (const [name, value] of Object.entries(this._gaugeAttrs())) {
            if (typeof value === "boolean") { this.root.toggleAttribute(name, value); }
            else if (this.root.getAttribute(name) !== String(value)) { this.root.setAttribute(name, String(value)); }
        }
        return this;
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        return this.drawView();
    }

    updateView(progress) {
        const value = Number(progress);
        this.curValue = Number.isFinite(value) ? value : 0;
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

    _gaugeText() {
        const width = Number.isFinite(this.size.x) ? Math.max(0, Math.floor(this.size.x)) : 0;
        const { maxValue, curValue } = this._gaugeValues();
        const scaled = curValue * width;
        const fillSize = !maxValue ? 0 : curValue === maxValue ? width
            : Math.floor(Number.isFinite(scaled) ? scaled / maxValue : (curValue / maxValue) * width);
        return "█".repeat(fillSize) + "░".repeat(width - fillSize);
    }

    _gaugeAttrs() {
        const { maxValue, curValue } = this._gaugeValues();
        return {
            ...super._gaugeAttrs(),
            role: "progressbar",
            "aria-valuemin": 0,
            "aria-valuemax": maxValue,
            "aria-valuenow": curValue,
        };
    }
}

class TVLabel extends TVStaticText {
    constructor(bounds, text, link = null) {
        super(bounds, text);
        this.link = link instanceof TVView ? link : null;
        this._labelMarkup = null;
        this.light = false;
        this._onLabelFocus = event => this._drawPalette(event.type === "focusout" ? event.relatedTarget : event.target);
    }

    getPalette() { return [38, 39, 40].map(index => this._appColor(index)); }

    _drawPalette(focusedElement = document.activeElement) {
        if (!this.root) { this.light = false; return this; }
        this.light = Boolean(this.link?.root?.contains(focusedElement));
        this._paintPaletteText(this.root, this.getColor(this.light ? 2 : 1), this.getColor(3));
        return this;
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        for (const type of ["focusin", "focusout"]) { this._focusScope?.removeEventListener(type, this._onLabelFocus); }
        super.bindRoot(root);
        this._focusScope = root && this.link ? (this.owner?.root || root.parentElement) : null;
        for (const type of ["focusin", "focusout"]) { this._focusScope?.addEventListener(type, this._onLabelFocus); }
        this._labelMarkup = null;
        return this.drawView();
    }

    setText(text) {
        this.text = String(text ?? "");
        this.drawView();
        return this;
    }

    drawView() {
        if (!this.root) { return this; }
        if (this.root.localName !== (this.link ? "label" : "span")) { return super.drawView(); }
        const content = renderHotkeyMarkup(this.text);
        if (this._labelMarkup !== content) {
            if (this.root.innerHTML !== content) { this.root.innerHTML = content; }
            this._labelMarkup = content;
        }
        if (this.link) { this.root.htmlFor = this.link.viewId; }
        this.root.hidden = !this.getState(sfVisible);
        setElementHelpContext(this.root, this.helpCtx);
        this._drawBounds();
        this._drawPalette();
        return this;
    }

    draw() {
        const tag = this.link ? "label" : "span";
        const cls = ["tv-static-text", "tv-label", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const bounds = [this._textBoundsStyle(), this._paletteStyle()].filter(Boolean).join(";");
        const styleAttr = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const forAttr = this.link ? ` for="${escapeHtml(this.link.viewId)}"` : "";
        const attrs = attrsToString(this._drawAttrs({ hidden: !this.getState(sfVisible) }));
        const content = renderHotkeyMarkup(this.text);
        return `<${tag} class="${escapeHtml(cls)}"${styleAttr}${forAttr} ${attrs}>${content}</${tag}>`;
    }

    handleEvent(event) {
        const nativeEvent = event.nativeEvent;
        if (!this.link || nativeEvent?.defaultPrevented) { return; }
        if (!viewAcceptsInput(this) || !viewAcceptsInput(this.link)) {
            if (event.what === evMouseDown && event.infoPtr === this) {
                nativeEvent?.preventDefault(); this.clearEvent(event);
            }
            return;
        }
        const mnemonic = this.text.match(/~([^~])~/)?.[1]?.toLowerCase();
        if ((event.what === evMouseDown && event.infoPtr === this)
            || (event.what === evKeyDown && mnemonic && nativeEvent?.altKey
                && !nativeEvent.ctrlKey && !nativeEvent.metaKey
                && nativeEvent.key?.toLowerCase() === mnemonic)) {
            nativeEvent?.preventDefault();
            this.link.focus();
            this.clearEvent(event);
        }
    }
}

// Turbo Vision's TFilterValidator rejects input containing disallowed characters.
class TVFilterValidator {
    constructor(validChars) { this.validChars = String(validChars); }

    isValidInput(value, _suppressFill = false) { return this.isValid(value); }

    isValid(value) {
        return Array.from(String(value ?? "")).every(character => this.validChars.includes(character));
    }
}

// Browser-era email validation uses the same input/complete-field contract.
class TVEmailValidator {
    constructor(allowEmpty = false, allowUsername = false) {
        this.allowEmpty = Boolean(allowEmpty);
        this.allowUsername = Boolean(allowUsername);
    }

    isValidInput(value, _suppressFill = false) {
        const text = String(value ?? "");
        return text.length <= 254 && !/[\s\x00-\x1f\x7f]/.test(text) && (text.match(/@/g) || []).length <= 1;
    }

    isValid(value) {
        const text = String(value ?? "");
        return (this.allowEmpty && text === "")
            || (this.allowUsername && /^[\p{L}\p{N}_.-]{1,64}$/u.test(text))
            || (text.length <= 254 && /^[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+\.[^@\s\x00-\x1f\x7f]+$/.test(text));
    }
}

// Fixed picture subset of Turbo Vision's TPXPictureValidator: ! uppercases
// one character and literal separators can be filled while typing.
class TVPXPictureValidator {
    constructor(picture, autoFill = false) {
        this.picture = String(picture);
        this.autoFill = Boolean(autoFill);
    }

    format(value) {
        const input = String(value ?? "");
        const slots = (this.picture.match(/!/g) || []).length;
        if (!this.autoFill || input.length > this.picture.length || !/^[a-z\d-]*$/i.test(input)) {
            return input;
        }
        const characters = input.replace(/-/g, "").toUpperCase().slice(0, slots);
        let index = 0;
        let formatted = "";
        for (const symbol of this.picture) {
            if (index >= characters.length) { break; }
            if (symbol === "!") { formatted += characters[index++]; }
            else { formatted += symbol; }
        }
        return formatted;
    }

    isValid(value) {
        const expression = `^${this.picture.split("").map((symbol) => (
            symbol === "!" ? "[A-Z0-9]" : symbol.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
        )).join("")}$`;
        return new RegExp(expression).test(String(value ?? ""));
    }
}

class TVInputLine extends TVView {
    constructor(bounds, maxLen = 255) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVInputLine expects TVRect bounds");
        }
        super(bounds);
        this.options |= ofSelectable;
        this.maxLen = Math.max(1, Number(maxLen) || 255);
        this.eventMask |= evBroadcast;
        this.data = "";
        this.disabled = false;
        this.secret = false;
        this.validator = null;
        this.onClipboardEvent = (nativeEvent) => this.dispatchEvent(new TVEvent(evCommand, {
            command: { copy: cmCopy, cut: cmCut, paste: cmPaste }[nativeEvent.type], infoPtr: this, nativeEvent,
        }));
        this.onInputKeyDown = (nativeEvent) => {
            if (clipboardKeyCommand(nativeEvent)) { this.dispatchEvent(new TVEvent(evKeyDown, { infoPtr: this, nativeEvent })); }
        };
        this.onBeforeInput = (nativeEvent) => this.dispatchEvent(new TVEvent(evBroadcast, { infoPtr: this, nativeEvent }));
    }

    getPalette() { return [this._appColor(50)]; }

    bindRoot(root) {
        if (root === this.root) { return this; }
        this.beforeInput = null;
        if (this.root) {
            this.data = this.root.value;
            for (const type of ["copy", "cut", "paste"]) { this.root.removeEventListener(type, this.onClipboardEvent); }
            this.root.removeEventListener("keydown", this.onInputKeyDown);
            this.root.removeEventListener("beforeinput", this.onBeforeInput);
        }
        super.bindRoot(root);
        if (this.root) {
            if (this.root.value !== this.data) { this.root.value = this.data; }
            this.drawView();
            for (const type of ["copy", "cut", "paste"]) { this.root.addEventListener(type, this.onClipboardEvent); }
            this.root.addEventListener("keydown", this.onInputKeyDown);
            this.root.addEventListener("beforeinput", this.onBeforeInput);
        }
        return this;
    }

    _formatData(value) {
        return String(this.validator?.format?.(value) ?? value ?? "").slice(0, this.maxLen);
    }

    _editState() {
        const root = this.root;
        return root ? { root, value: root.value, start: root.selectionStart, end: root.selectionEnd,
            direction: root.selectionDirection, left: root.scrollLeft } : null;
    }

    _restoreSelection(edit, formatted = false) {
        if (!edit || edit.root !== this.root || !Number.isInteger(edit.start) || !Number.isInteger(edit.end)) { return; }
        const position = offset => Math.min(this.data.length, formatted ? this._formatData(edit.value.slice(0, offset)).length : offset);
        this.root.setSelectionRange(position(edit.start), position(edit.end), edit.direction);
        this.root.scrollLeft = edit.left;
    }

    setData(value) {
        this.beforeInput = null;
        this.data = this._formatData(value);
        if (this.root && this.root.value !== this.data) { this.root.value = this.data; }
        return this;
    }

    getData() {
        return this.root ? this.root.value : this.data;
    }

    setValidator(validator) {
        const edit = this._editState();
        this.validator = validator;
        this.setData(this.getData());
        if (edit?.value !== this.data) { this._restoreSelection(edit, true); }
        return this;
    }

    valid(_command = 0) {
        return !this.validator || this.validator.isValid(this.getData());
    }

    handleEvent(event) {
        if ((event.what === evKeyDown || event.what === evCommand) && handleClipboardEvent(this, event)) { return; }
        const native = event.nativeEvent;
        if (event.what !== evBroadcast || event.infoPtr !== this || !["beforeinput", "input"].includes(native?.type)) { return; }
        if (!this.root || native.target !== this.root) { this.clearEvent(event); return; }
        if (native.type === "beforeinput") {
            this.beforeInput = this.disabled || !viewAcceptsInput(this) || this.root.readOnly ? null : this._editState();
            if (this.beforeInput) { this.data = this.beforeInput.value; }
            const edit = this.beforeInput;
            // Cancel predictable invalid insertions before they disturb native
            // selection/Undo. Other edits are validated after the browser edit.
            if (!edit || (native.cancelable && !native.isComposing && typeof native.data === "string"
                && native.inputType?.startsWith("insert") && this.validator?.isValidInput
                && !this.validator.isValidInput(this._formatData(edit.value.slice(0, edit.start)
                    + native.data + edit.value.slice(edit.end)), false))) {
                native.preventDefault();
                this.beforeInput = null;
            }
            this.clearEvent(event);
            return;
        }
        const previous = this.beforeInput, edit = this._editState();
        this.beforeInput = null;
        const formatted = this._formatData(this.root.value);
        if (this.disabled || !viewAcceptsInput(this) || this.root.readOnly
            || (this.validator?.isValidInput && !this.validator.isValidInput(formatted, false))) {
            this.root.value = this.data = previous?.value ?? this.data;
            this._restoreSelection(previous || edit);
            this.clearEvent(event);
            return;
        }
        const changed = formatted !== this.root.value;
        if (changed) { this.root.value = formatted; }
        this.data = this.root.value;
        if (changed) { this._restoreSelection(edit, true); }
    }

    async clipCopy() {
        const start = this.root?.selectionStart, end = this.root?.selectionEnd;
        if (this.disabled || !viewAcceptsInput(this) || start == null || end == null || start === end) { return false; }
        await writeClipboardText(this.getData().slice(start, end));
        return true;
    }

    async clipCut() {
        if (this.disabled || !viewAcceptsInput(this) || !this.root || this.root.readOnly) { return false; }
        const root = this.root, value = this.getData(), start = root.selectionStart, end = root.selectionEnd;
        const focus = document.activeElement;
        if (!await this.clipCopy()) { return false; }
        if (root !== this.root || !root.isConnected || this.disabled || !viewAcceptsInput(this) || root.readOnly || this.getData() !== value
            || document.activeElement !== focus || root.selectionStart !== start || root.selectionEnd !== end) { return false; }
        return this.insertText("");
    }

    async clipPaste() {
        if (this.disabled || !viewAcceptsInput(this) || !this.root || this.root.readOnly) { return false; }
        const root = this.root, value = this.getData(), start = root.selectionStart, end = root.selectionEnd;
        const focus = document.activeElement;
        const text = await readClipboardText();
        if (!text.replace(/[\r\n]/g, "")) { return false; }
        if (root !== this.root || !root.isConnected || this.disabled || !viewAcceptsInput(this) || root.readOnly || this.getData() !== value
            || document.activeElement !== focus || root.selectionStart !== start || root.selectionEnd !== end) { return false; }
        return this.insertText(text);
    }

    insertText(text) {
        if (this.disabled || !viewAcceptsInput(this) || !this.root || this.root.readOnly) { return false; }
        const value = this.getData(), start = this.root.selectionStart, end = this.root.selectionEnd;
        if (start == null || end == null) { return false; }
        const inserted = String(text).replace(/[\r\n]/g, "").slice(0, Math.max(0, this.maxLen - value.length + end - start));
        const candidate = value.slice(0, start) + inserted + value.slice(end);
        const formatted = this._formatData(candidate);
        if (this.validator?.isValidInput && !this.validator.isValidInput(formatted, false)) { return false; }
        this.setData(formatted);
        const position = Math.min(this.data.length, this._formatData(value.slice(0, start) + inserted).length);
        this.root.setSelectionRange(position, position);
        this.root.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: inserted ? "insertFromPaste" : "deleteByCut", data: inserted }));
        return true;
    }

    setSecret(enable = true) {
        this.secret = Boolean(enable);
        if (this.root) { this.root.type = this.secret ? "password" : "text"; }
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
            this.beforeInput = null;
            this.disabled = Boolean(enable);
            if (this.root) { this.root.disabled = this.disabled; }
        }
        return super.setState(state, enable);
    }

    _inputAttrs() {
        const viewName = this._semanticName();
        return this._drawAttrs({
            type: this.secret ? "password" : "text",
            id: this.viewId,
            maxlength: this.maxLen,
            disabled: this.disabled,
            hidden: !this.getState(sfVisible),
            autocomplete: "off",
            spellcheck: "false",
            ...(viewName ? { [`data-tv-${viewName}`]: true } : {}),
        });
    }

    drawView() {
        if (!this.root) { return this; }
        this.data = this.root.value;
        this._drawBounds();
        for (const [name, value] of Object.entries(this._inputAttrs())) {
            if (typeof value === "boolean") { this.root.toggleAttribute(name, value); }
            else if (this.root.getAttribute(name) !== String(value)) { this.root.setAttribute(name, String(value)); }
        }
        return this;
    }

    draw() {
        const attrString = attrsToString({ ...this._inputAttrs(), value: this.getData() });
        const cls = ["tv-input-line", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const bounds = TVView._viewBoundsStyle(this);
        const styleAttr = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        return `<input class="${escapeHtml(cls)}"${styleAttr} ${attrString}>`;
    }

    destroy() { this.bindRoot(null); }
}

class TVGroup extends TVView {
    constructor(bounds = new TVRect()) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVGroup expects TVRect bounds");
        }
        super(bounds);
        this.options |= ofSelectable;
        this.children = [];
        this.current = null;
        this.lockFlag = 0;
        this.endState = 0;
        this.eventMask |= evBroadcast;
        this._onGroupFocus = event => {
            if (this instanceof TVDesktop || this instanceof TVProgram) { return; }
            for (let owner = this.owner; owner instanceof TVGroup
                && !(owner instanceof TVDesktop || owner instanceof TVProgram); owner = owner.owner) {
                if (owner.root?.contains(event.target)) { return; }
            }
            const owns = view => {
                for (; view; view = view.owner) { if (view === this) { return true; } }
                return false;
            };
            if (event.type === "focusin") {
                const view = TVView._fromElement(event.target);
                if (owns(view) && document.activeElement === event.target) { view._recordFocus(event.target); }
            } else {
                const actual = TVView._fromElement(document.activeElement);
                if (owns(TVView._fromElement(event.relatedTarget))
                    || (document.activeElement !== event.target && owns(actual))) { return; }
                this.setState(sfFocused, false);
            }
        };
    }

    bindRoot(root) {
        for (const type of ["focusin", "focusout"]) { this.root?.removeEventListener(type, this._onGroupFocus, true); }
        if (!root) { this.children?.forEach(view => view.bindRoot(null)); }
        super.bindRoot(root);
        for (const type of ["focusin", "focusout"]) { this.root?.addEventListener(type, this._onGroupFocus, true); }
        return this;
    }

    changeBounds(bounds) {
        const previous = this.size.copy();
        super.changeBounds(bounds);
        const delta = new TVPoint(this.size.x - previous.x, this.size.y - previous.y);
        if (delta.x || delta.y) {
            this.children.forEach((child) => {
                const next = child.calcBounds(new TVRect(), delta);
                if (!next.equals(child.bounds)) { child.changeBounds(next); }
            });
        }
        return this;
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
        const bounds = [TVView._viewBoundsStyle(this), this._paletteStyle()].filter(Boolean).join(";");
        const styleAttr = bounds ? ` style="${escapeHtml(bounds)}"` : "";
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
        if (this.current === next) { return next; }
        const previous = this.current;
        this.current = next;
        previous?.setState(sfSelected | sfFocused, false);
        if (this.current === next && next) { next.setState(sfSelected, true); }
        return this.current;
    }

    setState(state, enable) {
        const previous = this.state;
        super.setState(state, enable);
        // A child's callback may supersede some of the requested state bits.
        const pending = mask => mask & (enable ? this.state : ~this.state);
        const inherited = state & (sfActive | sfDragging);
        if (inherited) {
            for (const child of this.children.slice()) {
                const mask = pending(inherited);
                if (mask && child.owner === this) { child.setState(mask, enable); }
            }
        }
        if (pending(state & sfFocused) && this.current?.owner === this) {
            this.current?.setState(sfFocused, enable);
        }
        if ((state & sfExposed) !== 0) {
            for (const child of this.children.slice()) {
                if (pending(sfExposed) && child.owner === this && child.getState(sfVisible)) { child.setState(sfExposed, enable); }
            }
        }
        if (((previous ^ this.state) & (sfVisible | sfDisabled)) !== 0) {
            this.firstThat(view => {
                if (view instanceof TVButton && (view.flags & bfDefault) === 0) {
                    const available = viewAcceptsInput(view);
                    if (view.amDefault && !available) { view.makeDefault(false); }
                    else if (!view.amDefault && available && (view.root
                        ? document.activeElement === view.root : view.getState(sfFocused))) { view.makeDefault(true); }
                }
                return false;
            });
        }
        return this;
    }

    first() { return this.children[0] || null; }
    at(index) { return this.children[index] || null; }
    indexOf(child) { return this.children.indexOf(child); }

    broadcast(command, infoPtr = null, infoLong = 0) {
        this._broadcastEvent(new TVEvent(evBroadcast, { command, infoPtr, infoLong }));
        return infoPtr;
    }

    _broadcastEvent(event) {
        for (const child of this.children.slice()) {
            if (child.owner !== this || (child.eventMask & evBroadcast) === 0) { continue; }
            if (child instanceof TVGroup) {
                child._broadcastEvent(event);
            } else { child.handleEvent(new TVEvent(evBroadcast, event)); }
        }
        this.handleEvent(new TVEvent(evBroadcast, event));
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

    handleEvent(event) {
        if (event.what !== evKeyDown || !event.nativeEvent?.altKey
            || event.nativeEvent.defaultPrevented
            || event.nativeEvent.ctrlKey || event.nativeEvent.metaKey
            || this instanceof TVDesktop || this instanceof TVProgram
            || !this.root?.contains(event.nativeEvent.target)) { return; }
        const mnemonic = event.nativeEvent.key?.toLowerCase();
        const control = this.firstThat((view) => {
            if (!(view instanceof TVLabel || view instanceof TVButton) || !viewAcceptsInput(view)) { return false; }
            if (view instanceof TVLabel && (!view.link || !viewAcceptsInput(view.link))) { return false; }
            return (view instanceof TVLabel ? view.text : view.title).match(/~([^~])~/)?.[1]?.toLowerCase() === mnemonic;
        });
        control?.handleEvent(event);
    }

    forEach(callback) {
        if (typeof callback === "function") { this.children.forEach(callback); }
    }

    insertBefore(child, target = null) {
        this._validateInsert(child, target);
        const index = target === null ? this.children.length : this.indexOf(target);
        child.owner = this;
        this.children.splice(index, 0, child);
        return child;
    }

    delete(child) { return this.remove(child); }

    _focusViews() {
        const views = [];
        const visit = group => {
            for (const child of group.children) {
                if (child.owner !== group || !viewAcceptsInput(child) || child instanceof TVWindow) { continue; }
                if (child instanceof TVGroup && !(child.root && child._canFocus())) { visit(child); }
                else if (child._canFocus()) { views.push(child); }
            }
        };
        visit(this);
        return views;
    }

    findNext(forwards = true) {
        const selectable = this._focusViews();
        if (!selectable.length) { return null; }
        let selected = this.current;
        while (selected instanceof TVGroup && !selectable.includes(selected)) { selected = selected.current; }
        if (this.root && this.root.contains(document.activeElement)) { selected = TVView._fromElement(document.activeElement); }
        const current = selectable.indexOf(selected);
        const offset = forwards ? 1 : -1;
        const index = current < 0 ? (forwards ? 0 : selectable.length - 1)
            : (current + offset + selectable.length) % selectable.length;
        return selectable[index];
    }

    focusNext(forwards = true) {
        const next = this.findNext(forwards);
        if (!next) { return false; }
        next.focus();
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

    _validateInsert(child, target = null) {
        if (!(child instanceof TVView)) {
            throw new TypeError("TVGroup.insert expects TVView");
        }
        if (child.owner !== null || this.children.includes(child)) {
            throw new Error("TVGroup.insert expects an unowned view; remove it from its owner first");
        }
        for (let owner = this; owner; owner = owner.owner) {
            if (owner === child) { throw new Error("TVGroup.insert cannot create an ownership cycle"); }
        }
        if (target !== null && (target.owner !== this || !this.children.includes(target))) {
            throw new Error("TVGroup.insertBefore target must be an owned child");
        }
    }

    insert(child) {
        this._validateInsert(child);
        child.owner = this;
        this.children.push(child);
        return child;
    }

    insertAll(children = []) {
        children.forEach((child) => this.insert(child));
        return this;
    }

    _reorder(child, target) {
        const index = this.children.indexOf(child);
        if (child.owner !== this || index < 0 || target === child) { return; }
        if (target != null && (target.owner !== this || !this.children.includes(target))) { return; }
        const parent = child.root?.parentElement;
        if (parent && target?.root?.parentElement && target.root.parentElement !== parent) { return; }
        // Children paint back to front; their array also defines forward Tab order.
        let position = target === undefined ? this.children.length : target === null ? 0 : this.children.indexOf(target) + 1;
        if (index < position) { position--; }
        if (index === position) { return; }
        this.children.splice(index, 1);
        this.children.splice(position, 0, child);
        if (!parent) { return; }
        const roots = this.children.map(view => view.root).filter(root => root?.parentElement === parent);
        const selection = window.getSelection?.();
        const selected = selection?.rangeCount && !selection.isCollapsed
            && roots.some(root => root.contains(selection.anchorNode) || root.contains(selection.focusNode));
        const endpoints = selected ? [selection.anchorNode, selection.anchorOffset, selection.focusNode, selection.focusOffset] : null;
        if (typeof parent.moveBefore === "function") {
            const next = roots[roots.indexOf(child.root) + 1] || null;
            parent.moveBefore(child.root, next);
        } else {
            // InsertBefore blurs a moved focused subtree. Move its peers instead.
            const pivot = roots.find(root => root.contains(document.activeElement)) || child.root, pivotIndex = roots.indexOf(pivot);
            let reference = pivot;
            for (let i = pivotIndex - 1; i >= 0; i--) {
                if (roots[i].nextSibling !== reference) { parent.insertBefore(roots[i], reference); }
                reference = roots[i];
            }
            reference = pivot;
            for (let i = pivotIndex + 1; i < roots.length; i++) {
                if (reference.nextSibling !== roots[i]) { parent.insertBefore(roots[i], reference.nextSibling); }
                reference = roots[i];
            }
        }
        if (endpoints && (selection.anchorNode !== endpoints[0] || selection.anchorOffset !== endpoints[1]
            || selection.focusNode !== endpoints[2] || selection.focusOffset !== endpoints[3])) {
            selection.setBaseAndExtent(...endpoints);
        }
    }

    remove(child) {
        const index = this.children.indexOf(child);
        if (index < 0) { return null; }
        this.children.splice(index, 1);
        try {
            if (this.current === child) { this.setCurrent(null); }
        } finally {
            if (child.owner === this && !this.children.includes(child)) { child.owner = null; }
        }
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
        this.growMode = gfGrowHiX;
        this.htmlContent = null;
        this.contentLength = 0;
    }

    get infoWidth() { return this.owner instanceof TVInfoBox ? this.owner.innerW : Math.max(0, this.size.x - 2); }

    _borderRole() { return this.owner instanceof TVInfoBox ? this.owner._borderRole() : ""; }

    _rowMarkup() {
        const borderClass = TVView._roleClassNames(this._borderRole());
        if (this.htmlContent === null) { return TVInfoBox.rowHtml(this.infoWidth, this.text, borderClass); }
        const classAttr = borderClass ? ` class="${escapeHtml(borderClass)}"` : "";
        const border = `<span data-tv-info-side${classAttr}>│</span>`;
        return border + " " + this.htmlContent
            + " ".repeat(Math.max(0, this.infoWidth - 1 - this.contentLength)) + border;
    }

    draw() {
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const attrs = attrsToString(this._drawAttrs());
        return `<div class="tv-static-text tv-info-row"${style} ${attrs}>${this._rowMarkup()}</div>`;
    }

    _drawBounds() {
        super._drawBounds();
        if (this.root) { this.root.innerHTML = this._rowMarkup(); }
    }

    setText(text) {
        this.text = String(text ?? "");
        this.htmlContent = null;
        if (this.root) { this.root.innerHTML = this._rowMarkup(); }
        return this;
    }

    setHTML(html, contentLen) {
        this.htmlContent = String(html ?? "");
        this.contentLength = Math.max(0, Number(contentLen) || 0);
        if (this.root) { this.root.innerHTML = this._rowMarkup(); }
        return this;
    }
}

class TVInfoBox extends TVGroup {
    constructor(bounds, title, children = []) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVInfoBox expects TVRect bounds");
        }
        super(bounds);
        this.title = String(title ?? "");
        this.topFrame = new TVStaticText(new TVRect(0, 0, this.size.x, 1), TVInfoBox.header(this.innerW, this.title));
        this.topFrame.growMode = gfGrowHiX;
        this.bottomFrame = new TVStaticText(new TVRect(0, this.size.y - 1, this.size.x, this.size.y), TVInfoBox.footer(this.innerW));
        this.bottomFrame.growMode = gfGrowHiX | gfGrowLoY | gfGrowHiY;
        this.insertAll([this.topFrame, ...children, this.bottomFrame]);
    }

    get innerW() { return Math.max(0, this.size.x - 2); }

    _borderRole() { return String(this.constructor.borderRole || ""); }

    draw() {
        const bounds = TVView._viewBoundsStyle(this);
        const cls = [
            "tv-group",
            "tv-info-box",
            TVView._roleClassNames(this._drawRole()),
        ].filter(Boolean).join(" ");
        const attrString = attrsToString(this._drawAttrs());
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const extra = attrString ? ` ${attrString}` : "";
        return `<div class="${escapeHtml(cls)}"${style}${extra}>${this.renderChildren()}</div>`;
    }

    _drawBounds() {
        super._drawBounds();
        this.topFrame.setText(TVInfoBox.header(this.innerW, this.title));
        this.bottomFrame.setText(TVInfoBox.footer(this.innerW));
    }

    updateRow(row, text) {
        if (!(row instanceof TVInfoRow) || !this.children.includes(row)) { return; }
        row.setText(text);
    }

    updateRowHTML(row, html, contentLen) {
        if (!(row instanceof TVInfoRow) || !this.children.includes(row)) { return; }
        row.setHTML(html, contentLen);
    }

    /** ┌─── Title ───┐ */
    static header(width, title) {
        const padded = Array.from(` ${title} `).slice(0, width).join("");
        const titleLen = Array.from(padded).length;
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
        const padded = Array.from(` ${title} `).slice(0, width).join("");
        const titleLen = Array.from(padded).length;
        const left = (width - titleLen) >> 1;
        const right = width - titleLen - left;
        return "\u251C" + "\u2500".repeat(left) + padded + "\u2500".repeat(right) + "\u2524";
    }

    /** │ Label: value │  (as innerHTML with styled border) */
    static rowHtml(width, content, borderClass) {
        const classAttr = borderClass ? ` class="${escapeHtml(borderClass)}"` : "";
        const B = `<span data-tv-info-side${classAttr}>\u2502</span>`;
        const clipped = Array.from(String(content)).slice(0, Math.max(0, width - 1));
        return B + (width ? " " : "") + escapeHtml(clipped.join(""))
            + " ".repeat(Math.max(0, width - 1 - clipped.length)) + B;
    }

}

class TVTerminal extends TVView {
    constructor(bounds, maxLines = 100) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVTerminal expects TVRect bounds");
        }
        super(bounds);
        this.maxLines = Math.max(1, Number(maxLines) || 100);
        this.lines = [];
        this.streamTail = "";
        this.pendingCR = false;
        this.lineElements = [];
        this.lineHtml = [];
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
        const rows = Array.from({ length: Math.max(0, Math.floor(this.size.y)) }, (_unused, index) => (
            `<span data-tv-terminal-line="${index}" style="${TVView._boundsStyle(0, index, this.size.x, 1)}"></span>`
        )).join("");
        return `<div class="${escapeHtml(className)}"${style} ${attrString}>${rows}</div>`;
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        super.bindRoot(root);
        this.lineElements = this._queryAll("[data-tv-terminal-line]");
        this.lineHtml = [];
        this.render();
        return this;
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        if (!this.root) { return this; }
        const rows = Math.max(0, Math.floor(this.size.y));
        while (this.lineElements.length > rows) { this.lineElements.pop().remove(); }
        while (this.lineElements.length < rows) {
            const line = document.createElement("span");
            line.dataset.tvTerminalLine = String(this.lineElements.length);
            this.root.appendChild(line);
            this.lineElements.push(line);
        }
        this.lineHtml.length = rows;
        this.lineElements.forEach((line, index) => {
            line.style.position = "absolute";
            line.style.left = "0ch";
            line.style.top = `${index}em`;
            line.style.width = `${this.size.x}ch`;
            line.style.height = "1em";
        });
        this.render();
        return this;
    }

    destroy() { this.bindRoot(null); }

    append(value) {
        const nextLines = String(value ?? "").replace(/\r\n?/g, "\n").split("\n");
        this.lines.push(...nextLines);
        if (this.lines.length > this.maxLines) {
            this.lines.splice(0, this.lines.length - this.maxLines);
        }
        this.render();
    }

    appendChunk(value) {
        let text = String(value ?? "");
        if (!text) { return; }
        if (this.pendingCR && text.startsWith("\n")) { text = text.slice(1); }
        this.pendingCR = text.endsWith("\r");
        const lines = (this.streamTail + text.replace(/\r\n?/g, "\n")).split("\n");
        this.streamTail = lines.pop();
        this.lines.push(...lines);
        if (this.lines.length > this.maxLines) {
            this.lines.splice(0, this.lines.length - this.maxLines);
        }
        this.render();
    }

    clear() {
        this.lines = [];
        this.streamTail = "";
        this.pendingCR = false;
        this.render();
    }

    render() {
        if (!this.root) { return; }
        const rows = this.lineElements.length;
        const innerWidth = Math.max(0, this.size.x - 2);
        const visible = rows ? [...this.lines, ...(this.streamTail ? [this.streamTail] : [])].slice(-rows) : [];
        const offset = rows - visible.length;
        this.lineElements.forEach((element, index) => {
            const text = index >= offset ? visible[index - offset] : "";
            const clipped = Array.from(text).slice(0, Math.max(0, innerWidth - 1)).join("");
            const html = TVInfoBox.rowHtml(innerWidth, clipped);
            if (this.lineHtml[index] !== html) {
                element.innerHTML = html;
                this.lineHtml[index] = html;
            }
        });
    }
}

class TVIndicator extends TVView {
    getPalette() { return [EDITOR_COLOR_ATTRIBUTE]; }

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
        this.options |= ofSelectable;
        this.hScrollBar = hScrollBar;
        this.vScrollBar = vScrollBar;
        this.indicator = indicator;
        this.bufSize = Math.max(1, Number(bufSize) || 65535);
        this.readOnly = true;
        this.text = "";
        this.eventMask |= evBroadcast;
        this.onTextInput = nativeEvent => {
            if (this.readOnly || !viewAcceptsInput(this)) {
                nativeEvent.stopPropagation();
                if (!this.readOnly) { this.setData(this.text); }
                return;
            }
            nativeEvent.stopPropagation(); this.text = this.getData(); this.updateEndMarker(); this.updateIndicator(); this.scrollController?.update();
            this.dispatchEvent(new TVEvent(evBroadcast, { infoPtr: this, nativeEvent }));
        };
        this.onBeforeInput = nativeEvent => {
            if (this.readOnly || !viewAcceptsInput(this)) { nativeEvent.preventDefault(); return; }
            if (["insertParagraph", "insertLineBreak"].includes(nativeEvent.inputType)) {
                nativeEvent.preventDefault(); this.insertText("\n");
            } else if (nativeEvent.data && this.getData().length + nativeEvent.data.length - (this._selectionRange()?.toString().length || 0) > this.bufSize) {
                nativeEvent.preventDefault();
            }
        };
        this.lastQuery = "";
        this.lastMatchEnd = 0;
        this.onSelectionChange = () => this.updateIndicator();
        this.onLink = null;
        this.onEditorKeyDown = (nativeEvent) => {
            if (clipboardKeyCommand(nativeEvent)) { this.dispatchEvent(new TVEvent(evKeyDown, { infoPtr: this, nativeEvent })); }
        };
        this.onClipboardEvent = (nativeEvent) => this.dispatchEvent(new TVEvent(evCommand, {
            command: { copy: cmCopy, cut: cmCut, paste: cmPaste }[nativeEvent.type], infoPtr: this, nativeEvent,
        }));
        this.onContentClick = (nativeEvent) => {
            this.dispatchEvent(new TVEvent(evMouseDown, { infoPtr: this, nativeEvent }));
        };
    }

    get textRoot() { return this.viewport || this.root; }

    _focusTarget() { return this.textRoot; }

    getPalette() { return [EDITOR_COLOR_ATTRIBUTE]; }

    _drawPalette() {
        if (!this.root) { return this; }
        const attribute = this._paletteAttribute();
        this._paintPalette(this.root, attribute);
        this._paintPalette(this.textRoot, attribute);
        return this;
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        this.scrollController?.destroy();
        this.scrollController = null;
        const previous = this.textRoot;
        if (previous) {
            for (const [type, handler] of [["input", this.onTextInput], ["beforeinput", this.onBeforeInput],
                ["keyup", this.onSelectionChange], ["mouseup", this.onSelectionChange], ["click", this.onContentClick],
                ["keydown", this.onEditorKeyDown], ...["copy", "cut", "paste"].map(type => [type, this.onClipboardEvent])]) {
                previous.removeEventListener(type, handler);
            }
            document.removeEventListener("selectionchange", this.onSelectionChange);
        }
        this.viewport = null;
        super.bindRoot(root);
        this.viewport = root?.classList.contains("tv-editor-frame") ? root.querySelector(":scope > [data-tv-editor-input]") : root;
        this._drawPalette();
        const surface = this.textRoot;
        if (surface) {
            surface.setAttribute("role", "document");
            surface.setAttribute("aria-readonly", this.readOnly ? "true" : "false");
            surface.setAttribute("contenteditable", this.readOnly ? "false" : "plaintext-only");
            if (!surface.hasAttribute("tabindex")) { surface.tabIndex = 0; }
            for (const [type, handler] of [["input", this.onTextInput], ["beforeinput", this.onBeforeInput],
                ["keyup", this.onSelectionChange], ["mouseup", this.onSelectionChange], ["keydown", this.onEditorKeyDown],
                ...["copy", "cut", "paste"].map(type => [type, this.onClipboardEvent])]) { surface.addEventListener(type, handler); }
            if (this.onLink) { surface.addEventListener("click", this.onContentClick); }
            document.addEventListener("selectionchange", this.onSelectionChange);
            if (surface !== root) {
                this.scrollController = this.vScrollBar || this.hScrollBar;
                this.scrollController?.bindRoot(root);
                this.scrollController?._setClientExtent(this.getExtent(), false);
            }
        }
        this.updateEndMarker(); this.updateIndicator(); return this;
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this.scrollController?._setClientExtent(this.getExtent(), false);
        return this;
    }

    focus() {
        if (!viewAcceptsInput(this)) { return this; }
        this.textRoot?.focus();
        if (this.textRoot && document.activeElement === this.textRoot) { this._recordFocus(this.textRoot); }
        return this;
    }

    draw() {
        const bounds = TVView._viewBoundsStyle(this), content = escapeHtml(this.text);
        const attrs = attrsToString(this._drawAttrs()), style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        if (!this.hScrollBar && !this.vScrollBar) { return `<div class="tv-editor-surface" ${attrs}${style}>${content}</div>`; }
        return `<div class="tv-editor-frame" data-tv-scroll-frame ${attrs}${style}><div class="tv-editor-surface" data-tv-editor-input data-tv-viewport>${content}</div>${this.vScrollBar?.draw() || ""}${this.hScrollBar?.draw() || ""}</div>`;
    }

    updateEndMarker() {
        if (!this.textRoot || this.readOnly) { return; }
        // A final newline needs a rendered empty line for the browser caret.
        // The BR has no text bytes and is never part of the saved buffer.
        if (this.textRoot.textContent.endsWith("\n")) {
            if (this.textRoot.lastChild?.nodeName !== "BR") { this.textRoot.append(document.createElement("br")); }
        } else if (this.textRoot.lastChild?.nodeName === "BR") { this.textRoot.lastChild.remove(); }
    }

    getData() {
        if (!this.textRoot) { return this.text; }
        return (this.readOnly ? this.textRoot.innerText ?? this.textRoot.textContent ?? "" : this.textRoot.textContent || "").replace(/\r\n?/g, "\n");
    }
    setData(text) {
        text = String(text);
        if (text.length > this.bufSize) { throw new RangeError("Editor text exceeds its buffer size"); }
        this.text = text;
        if (this.textRoot) { this.textRoot.textContent = text; this.updateEndMarker(); this.updateIndicator(); this.scrollController?.update(); }
        return this;
    }

    handleEvent(event) {
        if ((event.what === evKeyDown || event.what === evCommand) && handleClipboardEvent(this, event)) { return; }
        if (event.what === evMouseDown && !viewAcceptsInput(this) && this.textRoot?.contains(event.nativeEvent?.target)) {
            event.nativeEvent.preventDefault(); this.clearEvent(event); return;
        }
        if (event.what !== evMouseDown || event.nativeEvent?.type !== "click" || !this.onLink) { return; }
        const link = event.nativeEvent.target?.closest?.("a[href]");
        if (!link || !this.textRoot?.contains(link) || !this.onLink(link)) { return; }
        event.nativeEvent.preventDefault();
        this.clearEvent(event);
    }

    setReadOnly(readOnly = true) {
        this.readOnly = Boolean(readOnly);
        this.textRoot?.setAttribute("aria-readonly", this.readOnly ? "true" : "false");
        this.textRoot?.setAttribute("contenteditable", this.readOnly ? "false" : "plaintext-only");
        return this;
    }

    async clipCopy(nativeEvent = null) {
        if (!viewAcceptsInput(this)) { return false; }
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed || !this.textRoot?.contains(selection.anchorNode)
            || !this.textRoot.contains(selection.focusNode)) { return false; }
        const text = selection.toString();
        if (nativeEvent?.clipboardData) { nativeEvent.clipboardData.setData("text/plain", text); }
        else { await writeClipboardText(text); }
        return true;
    }

    _selectionRange() {
        const selection = window.getSelection();
        return selection?.rangeCount && this.textRoot?.contains(selection.anchorNode) && this.textRoot.contains(selection.focusNode)
            ? selection.getRangeAt(0).cloneRange() : null;
    }

    async clipCut() {
        if (this.readOnly || !viewAcceptsInput(this)) { return false; }
        const range = this._selectionRange(), root = this.textRoot, text = root?.textContent;
        const focus = document.activeElement;
        if (!range || range.collapsed || !await this.clipCopy()) { return false; }
        const current = this._selectionRange();
        if (this.readOnly || !viewAcceptsInput(this) || root !== this.textRoot || !root.isConnected || document.activeElement !== focus || text !== root.textContent || !current
            || current.compareBoundaryPoints(Range.START_TO_START, range) || current.compareBoundaryPoints(Range.END_TO_END, range)) { return false; }
        return this.insertText("");
    }

    async clipPaste() {
        if (this.readOnly || !viewAcceptsInput(this)) { return false; }
        const range = this._selectionRange(), root = this.textRoot, text = root?.textContent;
        const focus = document.activeElement;
        if (!range) { return false; }
        const inserted = await readClipboardText(), current = this._selectionRange();
        if (!inserted) { return false; }
        if (this.readOnly || !viewAcceptsInput(this) || root !== this.textRoot || !root.isConnected || document.activeElement !== focus || text !== root.textContent || !current
            || current.compareBoundaryPoints(Range.START_TO_START, range) || current.compareBoundaryPoints(Range.END_TO_END, range)) { return false; }
        return this.insertText(inserted);
    }

    insertText(text) {
        const range = this._selectionRange();
        if (this.readOnly || !viewAcceptsInput(this) || !range) { return false; }
        const inserted = String(text).replace(/\r\n?/g, "\n").slice(0, Math.max(0, this.bufSize - this.textRoot.textContent.length + range.toString().length));
        range.deleteContents();
        const node = document.createTextNode(inserted);
        range.insertNode(node); this.updateEndMarker(); range.setStart(node, node.length); range.collapse(true);
        const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
        this.textRoot.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: inserted ? "insertFromPaste" : "deleteByCut", data: inserted }));
        this.updateIndicator();
        return true;
    }

    selectionOffset() {
        const selection = window.getSelection();
        if (!selection || !selection.anchorNode || !this.textRoot?.contains(selection.anchorNode)) { return 0; }
        const range = document.createRange();
        range.selectNodeContents(this.textRoot);
        range.setEnd(selection.anchorNode, selection.anchorOffset);
        return range.toString().length;
    }

    updateIndicator() {
        if (!this.textRoot || !this.indicator) { return; }
        const text = this.textRoot.textContent || "";
        const offset = Math.min(text.length, this.selectionOffset());
        const before = text.slice(0, offset);
        const lines = before.split("\n");
        this.indicator.update(lines.length, (lines[lines.length - 1] || "").length + 1);
    }

    textNodeAt(offset) {
        const walker = document.createTreeWalker(this.textRoot, NodeFilter.SHOW_TEXT);
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
        if (!this.textRoot || !value) { return false; }
        const text = this.textRoot.textContent || "";
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
        this.bindRoot(null);
    }
}

// A sparse collection for bounded remote lists. The loader owns its transport;
// the collection owns cancellation, revision consistency and a bounded cache.
class TVPagedCollection {
    constructor(pageSize, loader) {
        if (!Number.isInteger(pageSize) || pageSize < 1 || typeof loader !== "function") {
            throw new TypeError("TVPagedCollection expects a page size and loader");
        }
        this.pageSize = pageSize;
        this.loader = loader;
        this.items = [];
        this.revision = "";
        this.metadata = null;
        this.pages = new Map();
        this.pending = new Map();
        this.listeners = new Set();
        this.version = 0;
        this.pinned = new Set();
        this.failed = new Set();
    }

    get count() { return this.items.length; }
    at(index) { return this.items[index]; }
    subscribe(listener) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
    _notify(error = null, refresh = false) {
        this.change = { error, refresh };
        for (const listener of [...this.listeners]) { listener(error); }
    }

    cancel() {
        this.version++;
        for (const request of this.pending.values()) { request.controller.abort(); }
        this.pending.clear();
    }

    clear() {
        this.cancel();
        this.items = []; this.pages.clear(); this.failed.clear(); this.revision = ""; this.metadata = null;
        this._notify();
    }

    async _load(offset, refresh = false, track = "") {
        const key = `${offset}:${track}`;
        if (this.pending.has(key)) { return this.pending.get(key).promise; }
        const cached = this.pages.get(offset);
        if (cached && !refresh && !track) { this.pages.delete(offset); this.pages.set(offset, cached); return cached.data; }
        const version = this.version, controller = new AbortController();
        const request = { controller, offset, refresh, promise: null };
        this.pending.set(key, request);
        request.promise = Promise.resolve().then(() => { controller.signal.throwIfAborted(); return this.loader({ offset, limit: this.pageSize,
            revision: refresh ? "" : this.revision, track, signal: controller.signal,
            etag: cached?.etag || "", cached: cached?.data || null,
        }); }).then(data => {
            controller.signal.throwIfAborted();
            if (version !== this.version) { throw new DOMException("Collection changed", "AbortError"); }
            if (!data || !Number.isInteger(data.total) || data.total < 0 || !Number.isInteger(data.offset)
                || data.offset < 0 || !Array.isArray(data.items) || data.items.length !== Math.min(this.pageSize, data.total - data.offset)
                || data.offset + data.items.length > data.total || typeof data.revision !== "string") {
                throw new Error("Invalid list page");
            }
            if (!refresh && this.revision && data.revision !== this.revision) {
                const error = new Error("List revision changed"); error.code = "revision"; throw error;
            }
            if (data.revision !== this.revision || this.items.length !== data.total) {
                for (const other of this.pending.values()) { if (other !== request) { other.controller.abort(); } }
                this.items = new Array(data.total); this.pages.clear(); this.revision = data.revision;
            }
            // Keep object identities for a revalidated page, including selection.
            this.metadata = data;
            for (let i = 0; i < data.items.length; i++) { this.items[data.offset + i] = data.items[i]; }
            this.pages.delete(data.offset);
            this.pages.set(data.offset, { data, etag: data.etag || "" });
            for (const [start] of this.pages) {
                if (this.pages.size <= 8) { break; }
                if ([...this.pinned].some(index => index >= start && index < start + this.pageSize)) { continue; }
                this.pages.delete(start);
                for (let i = start; i < Math.min(this.count, start + this.pageSize); i++) { delete this.items[i]; }
            }
            if (this.pending.get(key) === request) { this.pending.delete(key); }
            this.failed.delete(offset);
            this._notify(null, refresh);
            return data;
        }).catch(error => {
            if (!controller.signal.aborted && version === this.version) { this.failed.add(offset); this._notify(error); }
            throw error;
        }).finally(() => { if (this.pending.get(key) === request) { this.pending.delete(key); } });
        return request.promise;
    }

    refresh(track = "", offset = 0) { this.failed.clear(); return this._load(offset, true, track); }

    async load(index) {
        if (!Number.isInteger(index) || index < 0 || index >= this.count) { return null; }
        if (!this.at(index)) { await this._load(Math.floor(index / this.pageSize) * this.pageSize); }
        return this.at(index) || null;
    }

    requestRange(start, end, pinned = []) {
        this.pinned = new Set(pinned.filter(index => index >= 0 && index < this.count));
        const wanted = new Set();
        for (let i = start; i < Math.min(end, this.count); i += this.pageSize) { wanted.add(Math.floor(i / this.pageSize) * this.pageSize); }
        if (end > start) { wanted.add(Math.floor((Math.min(end, this.count) - 1) / this.pageSize) * this.pageSize); }
        for (const index of this.pinned) { wanted.add(Math.floor(index / this.pageSize) * this.pageSize); }
        for (const [key, request] of this.pending) {
            if (!request.refresh && !wanted.has(request.offset)) { request.controller.abort(); this.pending.delete(key); }
        }
        for (const offset of wanted) { if (!this.failed.has(offset)) { void this._load(offset).catch(() => {}); } }
    }

    dispose() {
        this.cancel(); this.listeners.clear(); this.pages.clear(); this.failed.clear(); this.pinned.clear();
        this.items = []; this.metadata = null; this.revision = "";
    }
}

class TVListViewer extends TVView {
    constructor(bounds, numCols = 1, hScrollBar = null, vScrollBar = null) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVListViewer expects TVRect bounds");
        }
        super(bounds);
        this.options |= ofSelectable;
        const columns = Math.trunc(Number(numCols));
        this.numCols = Number.isFinite(columns) ? Math.max(1, columns) : 1;
        this.hScrollBar = hScrollBar;
        this.vScrollBar = vScrollBar;
        this.topItem = 0;
        this.focused = -1;
        this.range = 0;
        this.items = [];
        this.selectedIndex = -1;
        this.selectHandler = null;
        this.activateHandler = null;
        this.selectionUiRoot = null;
        this.selectionUiIndex = null;
        this._itemsRoot = null;
        this._columnLayout = null;
        this._itemTextWidth = null;
        this.boundItemsRoot = null;
        this._disabledTabIndexes = null;
        this.active = true;
        this._onListFocus = event => {
            if (!viewAcceptsInput(this) && event.type === "focusin") { event.target.blur?.(); }
            this._drawPalette(event.type === "focusout" ? event.relatedTarget : event.target);
        };
        this.onListWheel = event => {
            if (!this.active || !viewAcceptsInput(this)) { event.preventDefault(); event.stopPropagation(); }
        };
        this.onListScroll = () => {
            const viewport = this.scrollViewport || this.itemsRoot();
            if (!viewport) { return; }
            this.topItem = this.numCols > 1
                ? Math.floor(viewport.scrollLeft / (this._columnWidth() * measureCells().width)) * this.visibleRows()
                : Math.floor(viewport.scrollTop / (this._itemHeight() * measureCells().height));
            if (this._syncVisibleItems()) {
                this._layoutItems();
                this.updateSelectionUi(false);
            }
        };
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        this.root?.removeEventListener("scroll", this.onListScroll, true);
        this.root?.removeEventListener("focusin", this._onListFocus);
        this.root?.removeEventListener("focusout", this._onListFocus);
        this.root?.removeEventListener("wheel", this.onListWheel);
        if (!root) { this._disabledTabIndexes = null; }
        if (this.root?._tvListViewer === this) { delete this.root._tvListViewer; }
        this._itemsRoot = this._paintedSelection = null;
        super.bindRoot(root);
        this._itemsRoot = this._findItemsRoot(this.root);
        this._renderItems();
        this.updateSelectionUi(false);
        this._bindListEvents();
        this.root?.addEventListener("scroll", this.onListScroll, true);
        this.root?.addEventListener("focusin", this._onListFocus);
        this.root?.addEventListener("focusout", this._onListFocus);
        this.root?.addEventListener("wheel", this.onListWheel, { passive: false });
        this.root?.classList.toggle("is-inactive", !this.active);
        if (this.root) { this.root._tvListViewer = this; }
        this._drawPalette();
        return this;
    }

    _findItemsRoot(root) { return root; }
    _itemsRole() { return "listbox"; }

    _drawAttrs(attrs = {}) {
        return super._drawAttrs({ ...attrs, hidden: !this.getState(sfVisible), "aria-disabled": String(this.getState(sfDisabled)) });
    }

    _syncDisabledState() {
        if (!this.root) { return; }
        const disabled = this.getState(sfDisabled);
        this.root.classList.toggle("is-disabled", disabled);
        this.root.setAttribute("aria-disabled", String(disabled));
        if (disabled && this.root.contains(document.activeElement)) { document.activeElement.blur?.(); }
        if (!disabled && !this._disabledTabIndexes) { return; }
        this._disabledTabIndexes ||= new WeakMap();
        this.itemsRoot()?.querySelectorAll("a[href], button, input, select, textarea, [tabindex]").forEach(element => {
            if (element.matches(this.itemSelector())) { return; }
            if (disabled) {
                if (!this._disabledTabIndexes.has(element)) { this._disabledTabIndexes.set(element, element.getAttribute("tabindex")); }
                element.tabIndex = -1;
            } else if (this._disabledTabIndexes.has(element)) {
                const value = this._disabledTabIndexes.get(element);
                if (value === null) { element.removeAttribute("tabindex"); }
                else { element.setAttribute("tabindex", value); }
            }
        });
        if (!disabled) { this._disabledTabIndexes = null; }
    }

    setState(state, enable) {
        super.setState(state, enable);
        if ((state & sfDisabled) !== 0) {
            if (enable) { super.setState(sfFocused, false); }
            this._syncDisabledState();
            this.selectionUiIndex = null;
            this.updateSelectionUi(false);
            this.scrollbarWidget?.refresh();
        }
        return this;
    }

    _renderItems() {
        this.selectionUiRoot = null;
        this.selectionUiIndex = null;
        this._columnLayout = null;
        this._itemTextWidth = null;
        const root = this.itemsRoot();
        this._visibleItems = null;
        this._extentRoot = null;
        this._windowed = this.numCols === 1 && !this.hScrollBar && this.size.y > 0
            && (!this.scrollViewport || this.scrollViewport === root)
            && (this._collection || this.items.length > Math.max(200, this.size.y * 5));
        if (root) {
            root.innerHTML = this._windowed ? "" : this.items.map((item, index) => this.itemMarkup(item, index)).join("");
            if (this._windowed) {
                const extent = document.createElement("div");
                this._extentRoot = extent;
                extent.setAttribute("aria-hidden", "true");
                extent.style.cssText = `position:absolute;left:0;top:0;width:1px;height:${this.items.length * this._itemHeight()}em;pointer-events:none`;
                root.appendChild(extent);
                this._syncVisibleItems();
            }
        }
        this._syncDisabledState();
        this._layoutItems();
    }

    _syncVisibleItems() {
        const root = this.itemsRoot();
        if (!this._windowed || !root) { return false; }
        const rows = this.visibleRows(), height = this._itemHeight() * measureCells().height;
        const first = Math.max(0, Math.floor(root.scrollTop / height));
        const start = Math.max(0, first - rows), end = Math.min(this.items.length, first + rows * 2);
        const selected = this.selectedIndex;
        const focused = root.contains(document.activeElement) ? this.resolveIndex(document.activeElement) : -1;
        const previous = this._visibleItems;
        if (previous?.start === start && previous.end === end && previous.selected === selected && previous.focused === focused) { return false; }
        this._visibleItems = { start, end, selected, focused };
        const wanted = new Set(Array.from({ length: end - start }, (_, index) => start + index));
        // Retain the selected native focus target even while wheel scrolling
        // elsewhere. FocusItem/End can still reveal it through the usual path.
        if (selected >= 0 && selected < this.items.length) { wanted.add(selected); }
        if (focused >= 0 && focused < this.items.length) { wanted.add(focused); }
        const mounted = new Map();
        let changed = false;
        root.querySelectorAll(this.itemSelector()).forEach(element => {
            const index = Number(element.dataset.tvListIndex);
            if (wanted.has(index)) { mounted.set(index, element); }
            else { element.remove(); changed = true; }
        });
        let next = null;
        for (const index of [...wanted].sort((a, b) => b - a)) {
            const element = mounted.get(index) || TVView._fromHTML(this.itemMarkup(this.items[index], index));
            if (!mounted.has(index)) { changed = true; }
            this._rowItems ||= new WeakMap();
            if (this._collection && mounted.has(index) && this._rowItems.get(element) !== this.items[index]) {
                element.innerHTML = TVView._fromHTML(this.itemMarkup(this.items[index], index)).innerHTML;
                changed = true;
            }
            this._rowItems.set(element, this.items[index]);
            if (element.getAttribute("aria-posinset") !== String(index + 1)) { element.setAttribute("aria-posinset", String(index + 1)); }
            if (element.getAttribute("aria-setsize") !== String(this.items.length)) { element.setAttribute("aria-setsize", String(this.items.length)); }
            if (element.parentElement !== root || element.nextSibling !== next) { root.insertBefore(element, next); changed = true; }
            next = element;
        }
        if (changed) { this._columnLayout = null; this.selectionUiIndex = null; }
        if (viewAcceptsInput(this)) { this._collection?.requestRange(start, end, [selected, focused]); }
        return changed;
    }

    visibleRows() {
        const viewport = this.scrollViewport || this.itemsRoot();
        const height = viewport?.clientHeight
            ? viewport.clientHeight / measureCells().height : this.size.y || 1;
        return Math.max(1, Math.floor(height / this._itemHeight()));
    }

    _itemHeight() { return 1; }

    getPalette() { return [57, 58, 59].map(index => this._appColor(index)); }

    _selectionColor(focusedElement = document.activeElement) {
        return this.getColor(!this.getState(sfDisabled) && this.active && this.root?.contains(focusedElement) ? 2 : 3);
    }

    _drawPalette(focusedElement) {
        if (!this.root || this._paletteAttribute() === null) { return this; }
        const normal = this.getColor(1), selected = this.selectedElement();
        for (const part of [this.root, this.viewport, this.itemsRoot()]) { this._paintPalette(part, normal); }
        if (this._paintedSelection && this._paintedSelection !== selected) { this._paintPalette(this._paintedSelection, null); }
        this._paintPalette(selected, this._selectionColor(focusedElement));
        this._paintedSelection = selected;
        return this;
    }

    setActive(active) {
        this.active = Boolean(active);
        this.root?.classList.toggle("is-inactive", !this.active);
        this._drawPalette();
    }

    _columnWidth() {
        const viewport = this.scrollViewport || this.itemsRoot();
        const width = viewport?.clientWidth ? Math.floor(viewport.clientWidth / measureCells().width) : this.size.x;
        return Math.max(1, Math.floor(width / this.numCols) + 1);
    }

    _layoutItems() {
        const root = this.itemsRoot();
        if (!root) { return; }
        this._syncVisibleItems();
        const cell = measureCells(), multi = this.numCols > 1, height = this._itemHeight();
        const clientWidth = root.clientWidth ? Math.floor(root.clientWidth / cell.width) : this.size.x;
        const rows = multi ? this.visibleRows() : 0;
        let width = multi ? this._columnWidth() : Math.max(1, clientWidth);
        if (!multi && this.hScrollBar) {
            let textWidth = this._itemTextWidth?.width || 0;
            if (this._itemTextWidth?.cellWidth !== cell.width) {
                const range = document.createRange();
                let pixels = 0;
                root.querySelectorAll(".tv-vlist-text").forEach((text) => {
                    range.selectNodeContents(text);
                    pixels = Math.max(pixels, range.getBoundingClientRect().width);
                });
                textWidth = Math.ceil(pixels / cell.width) + 2;
                this._itemTextWidth = root.clientWidth ? { cellWidth: cell.width, width: textWidth } : null;
            }
            width = Math.max(width, textWidth);
        }
        const last = multi ? Math.max(0, Math.ceil(this.items.length / rows) - 1) : 0;
        const previous = this._columnLayout;
        const flow = !multi && this.size.y === 0;
        if (previous?.root === root && previous.rows === rows && previous.width === width
            && previous.height === height && previous.flow === flow && previous.clientWidth === clientWidth) { return; }
        this._columnLayout = { root, rows, width, height, flow, clientWidth };
        root.querySelectorAll(this.itemSelector()).forEach((element, index) => {
            if (this._windowed) { index = Number(element.dataset.tvListIndex); }
            const column = multi ? Math.floor(index / rows) : 0;
            const cellWidth = multi && column === last && last >= this.numCols - 1
                ? Math.max(1, Math.min(width, clientWidth - (this.numCols - 1) * width)) : width;
            const top = (multi ? index % rows : index) * height;
            this._layoutItem(element, index, new TVRect(column * width, top, column * width + cellWidth, top + height));
        });
        if (multi && root.contains(document.activeElement)) { this.ensureSelectionVisible(); }
        this.onListScroll();
    }

    _layoutItem(element, _index, bounds) {
        const flow = this.numCols === 1 && this.size.y === 0;
        element.classList.toggle("is-flow", flow);
        element.style.position = flow ? "relative" : "absolute";
        element.style.left = `${bounds.x1}ch`;
        element.style.top = flow ? "0em" : `${bounds.y1}em`;
        element.style.width = flow && !this.hScrollBar ? "" : `${bounds.width}ch`;
        element.style.height = `${bounds.height}em`;
        const texts = Array.from(element.children).filter(part => part.classList.contains("tv-vlist-text"));
        texts.forEach((text, row) => {
            if (flow) {
                this._partBounds?.delete(text);
                for (const property of ["position", "left", "top", "width", "height"]) { text.style.removeProperty(property); }
            } else {
                const inset = Math.min(1, bounds.width / 2);
                const height = bounds.height / texts.length;
                this._placePart(text, new TVRect(inset, row * height, Math.max(inset, bounds.width - inset), (row + 1) * height));
            }
        });
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this._layoutItems();
        return this;
    }

    drawView() {
        const focused = Boolean(this.itemsRoot()?.contains(document.activeElement));
        const viewport = this.scrollViewport || this.itemsRoot();
        const left = viewport?.scrollLeft || 0, top = viewport?.scrollTop || 0;
        super.drawView();
        const next = this.scrollViewport || this.itemsRoot();
        if (next) { next.scrollLeft = left; next.scrollTop = top; }
        if (focused) { this.focusSelectedItem(); }
        return this;
    }

    draw() {
        const className = ["tv-list-viewer", this.numCols > 1 ? "is-multi-column" : "", TVView._roleClassNames(this._drawRole())].filter(Boolean).join(" ");
        const attrs = attrsToString(this._drawAttrs(
            this._semanticName() ? { [`data-tv-${this._semanticName()}`]: true } : {},
        ));
        const bounds = [TVView._viewBoundsStyle(this), this._paletteStyle()].filter(Boolean).join(";");
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        return `<div class="${escapeHtml(className)}"${style} ${attrs}></div>`;
    }

    itemsRoot() {
        return this._itemsRoot;
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
        const label = escapeHtml(this.getText(index));
        return item?.icon ? `<span class="tv-vlist-icon">${escapeHtml(item.icon)}</span>${label}` : label;
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
        const source = items instanceof TVPagedCollection ? items : null;
        if (source && (this.numCols !== 1 || this.hScrollBar || this.size.y <= 0)) {
            throw new TypeError("Paged lists need bounded single-column views without horizontal scrolling");
        }
        this._unsubscribeCollection?.(); this._unsubscribeCollection = null;
        this._collection = source;
        this.items = this._collection ? this._collection.items : Array.isArray(items) ? [...items] : [];
        this.range = this.items.length;
        const itemsRoot = this.itemsRoot();
        const restoreFocus = Boolean(itemsRoot?.contains(document.activeElement));
        this._renderItems();
        this.focusItem(selectedIndex, { scroll: false });
        if (restoreFocus) { this.focusSelectedItem(); }
        if (this._collection) {
            const source = this._collection;
            this._unsubscribeCollection = source.subscribe(error => {
                if (source !== this._collection) { return; }
                const focused = Boolean(this.root?.contains(document.activeElement));
                this.items = source.items; this.range = source.count;
                if (this._extentRoot) { this._extentRoot.style.height = `${this.range * this._itemHeight()}em`; }
                if (this.selectedIndex >= this.range) { this.selectedIndex = this.focused = this.range - 1; }
                if (!this._windowed) { this._renderItems(); }
                else { this._visibleItems = null; this._layoutItems(); this.updateSelectionUi(false); }
                this.updateScrollbar?.();
                if (focused && !this.root.contains(document.activeElement)) {
                    this.root.tabIndex = -1; this.root.focus({ preventScroll: true }); this._collectionFocus = true;
                }
                this.loadError = error;
                this.dispatchEvent(new TVEvent(evBroadcast, { command: error ? "list-error" : "list-data", infoPtr: this }));
                if (this._collectionFocus && this.range > 0) {
                    if (this.active && this.root?.contains(document.activeElement)) { this.focusSelectedItem(); }
                    this._collectionFocus = false;
                }
            });
        }
    }

    focusItem(index, { scroll = true } = {}) {
        if (!Number.isInteger(index) || index < 0 || index >= this.items.length) {
            this.selectedIndex = -1;
        } else {
            this.selectedIndex = index;
        }
        this.focused = this.selectedIndex;
        if (this._syncVisibleItems()) { this._layoutItems(); }
        this.updateSelectionUi(scroll);
    }

    focusItemNum(index) {
        if (Number.isInteger(index) && this.range > 0) {
            this.focusItem(Math.max(0, Math.min(this.range - 1, index)));
        }
    }

    selectItem(index) {
        if (!viewAcceptsInput(this)) { return; }
        this.focusItem(index);
        if (this.selectHandler && this.selectedIndex >= 0) {
            this.selectHandler(this.items[this.selectedIndex], this.selectedIndex, null);
        }
    }

    pointerIndex(event) { return this.resolveIndex(event?.target); }

    keyDestination(index, key) {
        if (key === "ArrowDown") { return Math.min(this.items.length - 1, index + 1); }
        if (key === "ArrowUp") { return Math.max(0, index - 1); }
        if (key === "ArrowRight") { return this.numCols > 1 ? Math.min(this.items.length - 1, index + this.visibleRows()) : -1; }
        if (key === "ArrowLeft") { return this.numCols > 1 ? Math.max(0, index - this.visibleRows()) : -1; }
        if (key === "PageDown") { return Math.min(this.items.length - 1, index + this.visibleRows() * this.numCols); }
        if (key === "PageUp") { return Math.max(0, index - this.visibleRows() * this.numCols); }
        if (key === "Home") { return 0; }
        if (key === "End") { return this.items.length - 1; }
        return -1;
    }

    focusSelectedItem() {
        if (!viewAcceptsInput(this)) { return; }
        const item = this._focusTarget();
        item?.focus({ preventScroll: true });
        if (item && document.activeElement === item) { this._recordFocus(item); }
        this._drawPalette();
    }

    _focusTarget() { return this.selectedElement() || this.itemsRoot()?.querySelector(this.itemSelector()) || this.itemsRoot() || this.root; }

    focus() { return viewAcceptsInput(this) ? super.focus() : this; }

    getText(index, maxLen = Number.MAX_SAFE_INTEGER) {
        const item = this.items[index];
        const text = typeof item === "string" ? item : String(item?.label ?? (this._collection ? "Loading..." : ""));
        return Array.from(text).slice(0, Math.max(0, Number(maxLen) || 0)).join("");
    }

    isSelected(index) { return index === this.selectedIndex; }

    setRange(range) {
        this.range = Math.max(0, Number(range) || 0);
        if (this.selectedIndex >= this.range) { this.focusItem(this.range - 1); }
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
        const updateItem = (element, index) => {
            if (!element) { return; }
            const value = Number.parseInt(element.dataset.tvListIndex || "", 10);
            const selected = value === this.selectedIndex;
            element.setAttribute("role", "option");
            element.classList.toggle("is-selected", selected);
            element.setAttribute("aria-selected", selected ? "true" : "false");
            element.tabIndex = !this.getState(sfDisabled) && (selected || (this.selectedIndex < 0 && index === 0)) ? 0 : -1;
        };
        if (this.selectionUiRoot !== itemsRoot || this.selectionUiIndex === null) {
            itemsRoot.querySelectorAll(this.itemSelector()).forEach(updateItem);
        } else if (this.selectionUiIndex !== this.selectedIndex) {
            for (const index of new Set([this.selectionUiIndex, this.selectedIndex, 0])) {
                if (index < 0) { continue; }
                updateItem(itemsRoot.querySelector(`${this.itemSelector()}[data-tv-list-index="${index}"]`), index);
            }
        }
        this.selectionUiRoot = itemsRoot;
        this.selectionUiIndex = this.selectedIndex;
        this._drawPalette();
        if (scroll) {
            this.ensureSelectionVisible();
        }
    }

    ensureSelectionVisible() {
        const element = this.selectedElement();
        const itemsRoot = this.scrollViewport || this.itemsRoot();
        if (!element || !itemsRoot) {
            return;
        }
        if (this.numCols > 1) {
            const width = this._columnWidth() * measureCells().width;
            const column = Math.floor(this.selectedIndex / this.visibleRows());
            const first = Math.floor(itemsRoot.scrollLeft / width);
            const next = column < first ? column : column >= first + this.numCols ? column - this.numCols + 1 : first;
            itemsRoot.scrollLeft = next * width;
            this.onListScroll();
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
        this._bindListEvents();
    }

    _bindListEvents(itemsRoot = this.itemsRoot()) {
        if (this.boundItemsRoot === itemsRoot) { return; }
        if (this.boundItemsRoot) {
            this.boundItemsRoot.removeEventListener("click", this.onListClick, true);
            this.boundItemsRoot.removeEventListener("dblclick", this.onListClick, true);
            this.boundItemsRoot.removeEventListener("mousedown", this.onListClick, true);
            this.boundItemsRoot.removeEventListener("keydown", this.onListKeyDown, true);
        }
        this.boundItemsRoot = itemsRoot;
        if (!itemsRoot) { return; }
        itemsRoot.setAttribute("role", this._itemsRole());
        this.onListClick ||= (nativeEvent) => {
            if (nativeEvent.type === "mousedown" && viewAcceptsInput(this)) { return; }
            const event = this.dispatchEvent(new TVEvent(evMouseDown, { infoPtr: this, nativeEvent }));
            if (event.what === evNothing && !nativeEvent.target?.closest?.("a[href]")) {
                nativeEvent.stopPropagation();
            }
        };
        this.onListKeyDown ||= (nativeEvent) => {
            const event = this.dispatchEvent(new TVEvent(evKeyDown, { infoPtr: this, nativeEvent }));
            if (event.what === evNothing) { nativeEvent.stopPropagation(); }
        };
        itemsRoot.addEventListener("click", this.onListClick, true);
        itemsRoot.addEventListener("dblclick", this.onListClick, true);
        itemsRoot.addEventListener("mousedown", this.onListClick, true);
        itemsRoot.addEventListener("keydown", this.onListKeyDown, true);
    }

    destroy() { this._unsubscribeCollection?.(); this._unsubscribeCollection = null; this.bindRoot(null); }

    _acceptsInput(event) {
        const native = event.nativeEvent;
        if ((event.what !== evMouseDown && event.what !== evKeyDown)
            || !native || !this.root?.contains(native.target)) { return false; }
        if (event.what === evKeyDown && (native.altKey || native.ctrlKey || native.metaKey)) { return false; }
        if (viewAcceptsInput(this)) { return true; }
        if (event.what === evKeyDown && !["Enter", " ", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"].includes(native.key)) { return false; }
        native.preventDefault();
        native.stopPropagation();
        this.clearEvent(event);
        return false;
    }

    handleEvent(event) {
        if (!this._acceptsInput(event)) { return; }
        const nativeEvent = event.nativeEvent;
        if (event.what === evMouseDown && (nativeEvent?.type === "click" || nativeEvent?.type === "dblclick")) {
            const index = this.pointerIndex(nativeEvent);
            if (index < 0 || index >= this.items.length) { return; }
            this.focusItem(index);
            if (nativeEvent.type === "dblclick") {
                this.activateHandler?.(this.items[index], index, nativeEvent);
            } else {
                this.selectHandler?.(this.items[index], index, nativeEvent);
            }
            this.focusSelectedItem();
            this.clearEvent(event);
            return;
        }
        if (event.what !== evKeyDown || !nativeEvent || !this.items.length) { return; }
        const current = this.resolveIndex(nativeEvent.target);
        if (current < 0) { return; }
        if (nativeEvent.key === "Enter" || nativeEvent.key === " ") {
            nativeEvent.preventDefault();
            this.focusItem(current);
            if (nativeEvent.key === "Enter" && this.activateHandler) {
                this.activateHandler(this.items[current], current, nativeEvent);
            } else {
                this.selectHandler?.(this.items[current], current, nativeEvent);
            }
            this.focusSelectedItem();
            this.clearEvent(event);
            return;
        }
        const next = this.keyDestination(current, nativeEvent.key);
        if (next < 0) { return; }
        nativeEvent.preventDefault();
        this.focusItem(next);
        this.focusSelectedItem();
        if (next !== current) { this.selectHandler?.(this.items[next], next, nativeEvent); }
        this.clearEvent(event);
    }
}

class TVListBox extends TVListViewer {
    constructor(bounds, numCols = 1, scrollBar = null) {
        super(bounds, numCols, null, scrollBar);
        if (this.numCols > 1) { this.hScrollBar = new TVScrollBar(new TVRect(), sbHorizontal); }
        this.list = [];
        this.viewport = null;
        this.scrollViewport = null;
        this.externalScrollbarWidget = null;
        this.scrollbarWidget = null;
        this.scrollbar = null;
    }

    hasScrollbar() { return true; }

    newList(list = []) {
        this.list = list instanceof TVPagedCollection || Array.isArray(list) ? list : [];
        this.setItems(this.list, (this.list instanceof TVPagedCollection ? this.list.count : this.list.length) ? 0 : -1);
    }

    draw() {
        const rootClasses = [
            "tv-vlist-viewer",
            this.numCols > 1 ? "is-multi-column" : "",
            this.hScrollBar ? "has-h-scrollbar" : "",
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
        const bounds = [TVView._viewBoundsStyle(this), this._paletteStyle()].filter(Boolean).join(";");
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const scrollbarMarkup = this.hasScrollbar()
            ? ((this.numCols === 1 || this.vScrollBar) ? new TVScrollBar(new TVRect(), sbVertical).draw() : "") + (this.hScrollBar?.draw() || "")
            : "";
        return `
            <div class="${escapeHtml(rootClasses)}"${style}${scrollFrameAttr}${rootAttrsText}>
                <div class="tv-vlist-viewport" data-tv-list-viewport data-tv-viewport></div>
                ${scrollbarMarkup}
            </div>
        `;
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        this.scrollbarWidget?.destroy();
        super.bindRoot(root);
        this.scrollbarWidget = this.root?.querySelector(".tv-scrollbar")
            ? (this.hScrollBar || this.vScrollBar || new TVScrollBar(new TVRect())).bindRoot(this.root)
            : null;
        this.scrollbar = this.scrollbarWidget?.axes.y?.root || null;
        if (this.root) {
            this.root._tvListViewer = this;
        }
        this.setActive(this.active);
        this.updateScrollbar();
        return this;
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this.updateScrollbar();
        return this;
    }

    _findItemsRoot(root) {
        const external = this.scrollViewport !== this.viewport ? this.scrollViewport : null;
        this.viewport = root?.querySelector("[data-tv-list-viewport]") || null;
        const retained = external && root && external.contains(root);
        this.scrollViewport = retained ? external : this.viewport;
        if (external && !retained) { this.externalScrollbarWidget = null; }
        return this.viewport;
    }

    resolvePointerIndex(event) {
        const targetIndex = this.resolveIndex(event?.target);
        if (targetIndex >= 0) { return targetIndex; }
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
        return -1;
    }

    pointerIndex(event) { return this.resolvePointerIndex(event); }

    setItems(items = [], selectedIndex = -1) {
        if (this.scrollViewport) {
            this.scrollViewport.scrollTop = 0;
        }
        super.setItems(items, selectedIndex);
        this.updateScrollbar();
    }

    focusItem(index, { scroll = true } = {}) {
        super.focusItem(index, { scroll });
        this.updateScrollbar();
    }

    setScrollViewport(viewport = null, scrollbarWidget = null) {
        this.scrollViewport = viewport || this.viewport;
        this.externalScrollbarWidget = scrollbarWidget;
        return this;
    }

    updateScrollbar() {
        this.scrollbarWidget?._setClientExtent(this.getExtent(), this.numCols === 1);
        if (!this.scrollbarWidget) { this._layoutItems(); }
        this.externalScrollbarWidget?.refresh();
    }

    setActive(active) {
        super.setActive(active);
        this.scrollbarWidget?.setActive(this.active);
    }

    destroy() {
        super.destroy();
        this.scrollbarWidget?.destroy();
        this.scrollbarWidget = null;
        this.externalScrollbarWidget = null;
    }
}

class TVGridView extends TVListBox {
    constructor(bounds, columns = [], hScrollBar = null, vScrollBar = null) {
        super(bounds, 1, vScrollBar);
        this.columns = columns.map((column) => typeof column === "string" ? { title: column } : { ...column });
        this.hScrollBar = hScrollBar || new TVScrollBar(new TVRect(), sbHorizontal);
        this.headersVisible = true;
        this.selectedColumn = 0;
        this.headerRoot = null;
        this.rowsRoot = null;
    }

    _columnBounds() {
        let left = 0;
        return this.columns.map((column) => {
            const width = Math.min(200, Math.max(3, Math.trunc(Number(column.width) || 12)));
            const bounds = new TVRect(left, 0, left + width, 1);
            left += width;
            return bounds;
        });
    }

    _drawCells(values, header = false) {
        return this._columnBounds().map((bounds, column) => {
            const attrs = header ? 'role="columnheader"' : `role="gridcell" data-tv-grid-column="${column}"`;
            const style = TVView._boundsStyle(bounds.x1, bounds.y1, bounds.width, bounds.height);
            const textBounds = new TVRect(1, 0, bounds.width - 1, 1);
            const textStyle = TVView._boundsStyle(textBounds.x1, textBounds.y1, textBounds.width, textBounds.height);
            return `<span ${attrs} class="tv-grid-cell" style="${escapeHtml(style)}">`
                + `<span class="tv-grid-text" style="${escapeHtml(textStyle)}">${escapeHtml(String(values[column] ?? ""))}</span></span>`;
        }).join("");
    }

    draw() {
        const bounds = TVView._viewBoundsStyle(this);
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const attrs = attrsToString(this._drawAttrs({ hidden: !this.getState(sfVisible) }));
        const header = this._drawCells(this.columns.map((column) => column.title), true);
        return `<div role="grid" class="tv-vlist-viewer tv-grid-view has-h-scrollbar"${style} data-tv-scroll-frame ${attrs}>
            <div class="tv-vlist-viewport" data-tv-list-viewport data-tv-viewport>
                <div role="row" class="tv-grid-header"${this.headersVisible ? "" : " hidden"}>${header}</div>
                <div class="tv-grid-rows" data-tv-grid-rows></div>
            </div>
            ${new TVScrollBar(new TVRect(), sbVertical).draw()}${this.hScrollBar.draw()}
        </div>`;
    }

    _findItemsRoot(root) {
        super._findItemsRoot(root);
        this.headerRoot = root?.querySelector(".tv-grid-header") || null;
        this.rowsRoot = root?.querySelector("[data-tv-grid-rows]") || null;
        return this.rowsRoot;
    }

    _itemsRole() { return "rowgroup"; }

    _drawPalette(focusedElement) {
        super._drawPalette(focusedElement);
        if (!this.root) { this._paintedCell = null; return this; }
        this._paintPalette(this.headerRoot, this.getColor(3));
        const selected = this.selectedElement()?.querySelector(`[data-tv-grid-column="${this.selectedColumn}"]`);
        if (this._paintedCell && this._paintedCell !== selected) { this._paintPalette(this._paintedCell, null); }
        this._paintPalette(selected, this._selectionColor(focusedElement));
        this._paintedCell = selected;
        return this;
    }

    _layoutItems() {
        if (!this.rowsRoot || !this.viewport) { return; }
        const columns = this._columnBounds();
        const clientWidth = this.viewport.clientWidth
            ? Math.floor(this.viewport.clientWidth / measureCells().width) : Math.max(0, this.size.x - 1);
        const contentWidth = this.items.length || this.headersVisible ? columns.at(-1)?.x2 || 0 : 0;
        const width = Math.max(clientWidth, contentWidth);
        const previous = this._columnLayout;
        if (previous?.root === this.rowsRoot && previous.width === width) { return; }
        this._columnLayout = { root: this.rowsRoot, width };
        this.headerRoot.style.width = `${width}ch`;
        this.headerRoot.style.height = "1em";
        this.rowsRoot.style.width = `${width}ch`;
        this.rowsRoot.style.height = `${this.items.length}em`;
        this.rowsRoot.querySelectorAll(this.itemSelector()).forEach((row, index) => {
            this._placePart(row, new TVRect(0, index, width, index + 1));
        });
    }

    visibleRows() {
        return Math.max(1, super.visibleRows() - (this.headersVisible ? 1 : 0));
    }

    itemMarkup(row, index) {
        return `<div role="row" tabindex="-1" class="tv-vlist-item tv-grid-row" data-tv-list-index="${index}">${this._drawCells(row || [])}</div>`;
    }

    setRows(rows = []) {
        this.list = Array.isArray(rows) ? rows : [];
        this.setItems(this.list, this.list.length ? 0 : -1);
    }

    setHeadersVisible(visible) {
        this.headersVisible = Boolean(visible);
        if (this.headerRoot) { this.headerRoot.hidden = !this.headersVisible; }
        this.updateScrollbar();
    }

    getCell(row, column) { return this.items[row]?.[column]; }

    selectCell(row, column, options = {}) {
        this.selectedColumn = Math.max(0, Math.min(this.columns.length - 1, Number(column) || 0));
        this.focusItem(row, options);
    }

    getText(index, maxLen = Number.MAX_SAFE_INTEGER) {
        return Array.from((this.items[index] || []).join("\t")).slice(0, maxLen).join("");
    }

    updateSelectionUi(scroll = true) {
        super.updateSelectionUi(scroll);
        this.rowsRoot?.querySelectorAll(this.itemSelector()).forEach((row) => row.setAttribute("role", "row"));
        this.rowsRoot?.querySelectorAll("[data-tv-grid-column]").forEach((cell) => {
            cell.classList.toggle("is-selected", this.resolveIndex(cell) === this.selectedIndex
                && Number(cell.dataset.tvGridColumn) === this.selectedColumn);
        });
    }

    ensureSelectionVisible() {
        const cell = this.selectedElement()?.querySelector(`[data-tv-grid-column="${this.selectedColumn}"]`);
        if (!cell || !this.viewport) { return; }
        const cellRect = cell.getBoundingClientRect();
        const viewportRect = this.viewport.getBoundingClientRect();
        const top = viewportRect.top + (this.headersVisible ? this.headerRoot?.getBoundingClientRect().height || 0 : 0);
        if (cellRect.top < top) {
            this.viewport.scrollTop -= top - cellRect.top;
        } else if (cellRect.bottom > viewportRect.bottom) {
            this.viewport.scrollTop += cellRect.bottom - viewportRect.bottom;
        }
        if (cellRect.left < viewportRect.left) {
            this.viewport.scrollLeft -= viewportRect.left - cellRect.left;
        } else if (cellRect.right > viewportRect.right) {
            this.viewport.scrollLeft += cellRect.right - viewportRect.right;
        }
    }

    handleEvent(event) {
        if (!this._acceptsInput(event)) { return; }
        const nativeEvent = event.nativeEvent;
        if (event.what === evMouseDown) {
            const cell = nativeEvent?.target?.closest?.("[data-tv-grid-column]");
            if (cell && this.root?.contains(cell)) {
                this.selectedColumn = Number(cell.dataset.tvGridColumn);
            }
        } else if (event.what === evKeyDown && (nativeEvent?.key === "ArrowLeft" || nativeEvent?.key === "ArrowRight")) {
            const column = this.selectedColumn + (nativeEvent.key === "ArrowRight" ? 1 : -1);
            if (column >= 0 && column < this.columns.length) {
                nativeEvent.preventDefault();
                this.selectCell(this.selectedIndex, column);
                this.focusSelectedItem();
                this.selectHandler?.(this.selectedItem(), this.selectedIndex, nativeEvent);
                this.clearEvent(event);
            }
            return;
        }
        super.handleEvent(event);
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
        this.focusItem(index, options);
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
        super.bind({
            onSelect: (entry, index, event) => this.nodeSelectHandler?.(entry.node, index, event),
            onActivate: (entry, index, event) => this.nodeActivateHandler?.(entry.node, index, event),
        });
    }

    handleEvent(event) {
        if (!this._acceptsInput(event)) { return; }
        if (event.what === evKeyDown && ["ArrowLeft", "ArrowRight"].includes(event.nativeEvent?.key)) {
            const index = this.resolveIndex(event.nativeEvent.target);
            const entry = this.items[index];
            if (entry) {
                event.nativeEvent.preventDefault();
                if (event.nativeEvent.key === "ArrowRight") {
                    if (entry.hasChildren && !entry.expanded) { this.toggle(index, true); }
                    else if (entry.hasChildren) { this.focusItem(index + 1); }
                } else if (entry.hasChildren && entry.expanded) {
                    this.toggle(index, false);
                } else if (entry.parentKey) {
                    this.selectKey(entry.parentKey);
                }
                this.focusSelectedItem();
                this.clearEvent(event);
                return;
            }
        }
        super.handleEvent(event);
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
                ${this.hScrollBar?.draw() || ""}
            </div>
        `;
    }

    bindRoot(root) {
        const scrollBar = this.vScrollBar || this.hScrollBar;
        scrollBar?.destroy();
        super.bindRoot(root);
        this.viewport = this._query("[data-tv-scroll-viewport]");
        scrollBar?.bindRoot(this.root);
        this.update();
        return this;
    }

    update() {
        const scrollBar = this.vScrollBar || this.hScrollBar;
        if (scrollBar) { scrollBar._setClientExtent(this.getExtent()); }
        else { this._placePart(this.viewport, this.getExtent()); }
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this.update();
        return this;
    }

    bind() {
        this.update();
    }

    destroy() {
        this.bindRoot(null);
    }
}

class TVMenu {
    constructor(items = null, deflt = null) {
        if (items !== null && !(items instanceof TVMenuItem)) {
            throw new TypeError("TVMenu expects a linked TVMenuItem list");
        }
        this.items = items;
        this.deflt = deflt instanceof TVMenuItem ? deflt : items;
    }

    entries() {
        const items = [];
        const visited = new Set();
        for (let item = this.items; item instanceof TVMenuItem && !visited.has(item); item = item.next) {
            visited.add(item);
            items.push(item);
        }
        return items;
    }
}

class TVMenuView extends TVView {
    constructor(bounds, menu = new TVMenu(), parentMenu = null) {
        super(bounds);
        if (!(menu instanceof TVMenu)) {
            throw new TypeError("TVMenuView expects TVMenu");
        }
        this.menu = menu;
        this.parentMenu = parentMenu;
        this.current = menu.deflt;
        this.eventMask |= evMouseMove | evBroadcast;
        this.menuRoots = [];
        this.topLevelActions = [];
        this.activeRoot = null;
        this.activePopup = null;
        this.previousFocus = null;
        this.lastSelection = new WeakMap();
        this.itemElements = new Map();
        this.rootControls = new Map();
        this.rootByItem = new Map();
        this.submenuControls = new Map();
        this.submenuByPopup = new Map();
        this.popupItems = new Map();
        this.selectedElement = null;
        this.topLevelItems = new Set(menu.entries());
        this.menuBoxes = new Map();
        this._hoveredItem = null;
        this._onMenuPaint = event => {
            const target = /out$/.test(event.type) ? event.relatedTarget : event.target;
            const element = target?.closest?.("button, a");
            const item = element?._tvMenuItem;
            const previous = this._hoveredItem;
            if (event.type.startsWith("mouse")) { this._hoveredItem = this.root?.contains(element) ? item : null; }
            for (const entry of new Set([previous, item, event.target?.closest?.("button, a")?._tvMenuItem])) {
                this._paintMenuItem(entry);
            }
        };
    }

    getPalette() {
        return this.owner instanceof TVMenuView ? [1, 2, 3, 4, 5, 6] : [2, 3, 4, 5, 6, 7].map(index => this._appColor(index));
    }

    _paintMenuItem(item, element = this.itemElements.get(item)) {
        if (!element) { return; }
        const root = this.rootByItem.get(item);
        const popup = root ? this.rootControls.get(root)?.popup : this.submenuControls.get(element)?.popup;
        const selected = item === this._hoveredItem || element === document.activeElement
            || element === this.selectedElement || Boolean(popup && !popup.hidden);
        const color = this.getColor(commandDisabled(item) ? (selected ? 5 : 2) : (selected ? 4 : 1));
        this._paintPaletteText(element, color, this.getColor(commandDisabled(item) ? (selected ? 5 : 2) : (selected ? 6 : 3)));
    }

    _drawPalette() {
        if (!this.root) { return this; }
        super._drawPalette();
        if (!(this.owner instanceof TVMenuView)) {
            this.itemElements?.forEach((element, item) => this._paintMenuItem(item, element));
        }
        return this;
    }

    bindRoot(root) {
        for (const type of ["mouseover", "mouseout", "focusin", "focusout"]) { this.root?.removeEventListener(type, this._onMenuPaint); }
        if (root?._tvMenuView && root._tvMenuView !== this) { root._tvMenuView.bindRoot(null); }
        if (this.root?._tvMenuView === this) { delete this.root._tvMenuView; }
        super.bindRoot(root);
        watchCommands(this, Boolean(root) && !(this.owner instanceof TVMenuView));
        if (!root) {
            this.menuBoxes.forEach((box) => box.bindRoot(null));
            this._hoveredItem = null;
            this.itemElements.clear();
            this.popupItems.clear();
            this.rootControls.clear(); this.rootByItem.clear();
            this.submenuControls.clear(); this.submenuByPopup.clear();
            this.menuRoots = []; this.topLevelActions = [];
            this.activeRoot = this.activePopup = this.selectedElement = this.previousFocus = null;
            return this;
        }
        const items = new Map();
        const collect = (menu) => menu.entries().forEach((item) => {
            items.set(item._menuId, item);
            if (item.subMenu instanceof TVMenu) { collect(item.subMenu); }
        });
        collect(this.menu);
        this.itemElements.clear();
        if (this.owner instanceof TVMenuView) {
            items.forEach((item) => {
                const element = this.owner.itemElements.get(item);
                if (element) { this.itemElements.set(item, element); }
            });
        } else {
            root.querySelectorAll("[data-tv-menu-item-id]").forEach((element) => {
                const item = items.get(element.dataset.tvMenuItemId);
                if (item) {
                    element._tvMenuItem = item;
                    this.itemElements.set(item, element);
                    this.updateItem(item, element);
                }
            });
        }
        root._tvMenuView = this;
        if (!(this.owner instanceof TVMenuView)) {
            for (const type of ["mouseover", "mouseout", "focusin", "focusout"]) { root.addEventListener(type, this._onMenuPaint); }
        }
        this.refresh();
        this.menuBoxes.forEach((box, item) => {
            box.owner = this;
            box.bindRoot(this.itemElements.get(item)?.nextElementSibling || null);
        });
        this._drawPalette();
        return this;
    }

    refresh() {
        if (!this.root) { return; }
        this.menuRoots = Array.from(this.root.querySelectorAll("[data-tv-menu-root]"));
        this.topLevelActions = Array.from(this.itemElements)
            .filter(([item]) => this.topLevelItems.has(item) && !(item.subMenu instanceof TVMenu))
            .map(([_item, element]) => element);
        this.rootControls.clear();
        this.rootByItem.clear();
        this.menuRoots.forEach((menuRoot) => {
            const toggle = this.directChild(menuRoot, "[data-tv-menu-toggle]");
            const popup = this.directChild(menuRoot, "[data-tv-menu-popup]");
            this.rootControls.set(menuRoot, { toggle, popup });
            if (toggle?._tvMenuItem) { this.rootByItem.set(toggle._tvMenuItem, menuRoot); }
        });
        this.submenuControls.clear();
        this.submenuByPopup.clear();
        this.root.querySelectorAll("[data-tv-submenu-root]").forEach((submenuRoot) => {
            const toggle = this.directChild(submenuRoot, "[data-tv-submenu-toggle]");
            const popup = this.directChild(submenuRoot, "[data-tv-submenu-popup]");
            if (!toggle || !popup) { return; }
            this.submenuControls.set(toggle, { root: submenuRoot, popup });
            this.submenuByPopup.set(popup, {
                root: submenuRoot,
                toggle,
                parentPopup: toggle.closest(".tv-menu-popup"),
            });
        });
        if (this.activeRoot && !this.activeRoot.isConnected) {
            this.activeRoot = null;
            this.activePopup = null;
            this.previousFocus = null;
        }
        if (this.selectedElement && !this.selectedElement.isConnected) {
            this.selectedElement = null;
        }
        this.popupItems.clear();
        const popups = Array.from(this.root.querySelectorAll(".tv-menu-popup"));
        if (this.root.matches?.(".tv-menu-popup")) { popups.unshift(this.root); }
        popups.forEach((popup) => {
            this.popupItems.set(popup, Array.from(popup.querySelectorAll(".tv-menu-popup-item")).filter(
                (item) => item.closest(".tv-menu-popup") === popup
            ));
            if (!(this.owner instanceof TVMenuView)) {
                popup.setAttribute("role", "menu");
                this.menuItems(popup).forEach((item) => {
                    item.setAttribute("role", "menuitem");
                    item.tabIndex = -1;
                });
            }
        });
    }

    getHelpCtx() {
        if (!this.activeRoot) { return hcNoContext; }
        const rootItem = this.rootControls.get(this.activeRoot)?.toggle?._tvMenuItem;
        return this.current?.helpCtx || rootItem?.helpCtx || hcNoContext;
    }

    directChild(root, selector) {
        return root
            ? Array.from(root.children).find((child) => child.matches?.(selector)) || null
            : null;
    }

    menuItems(popup) {
        if (!popup) { return []; }
        return (this.popupItems.get(popup) || []).filter((item) => !commandDisabled(item._tvMenuItem));
    }

    menuMnemonic(item) {
        return item instanceof TVMenuItem
            ? (String(item.name).match(/~([^~]+)~/)?.[1] || "").charAt(0).toLowerCase()
            : "";
    }

    markSelected(element, focus = true) {
        if (!element) { return; }
        const previous = this.selectedElement?._tvMenuItem;
        if (this.selectedElement && this.selectedElement !== element) {
            this.selectedElement.classList.remove("is-menu-selected");
            this.selectedElement.tabIndex = -1;
        }
        this.selectedElement = element;
        element.classList.add("is-menu-selected");
        element.tabIndex = 0;
        this.current = element._tvMenuItem || this.current;
        this.activePopup = element.closest(".tv-menu-popup") || this.activePopup;
        if (this.activePopup) { this.lastSelection.set(this.activePopup, element); }
        if (focus) {
            element.focus({ preventScroll: true });
            element.scrollIntoView({ block: "nearest" });
        }
        this._paintMenuItem(previous);
        this._paintMenuItem(element._tvMenuItem);
    }

    selectByIndex(popup, index) {
        const items = this.menuItems(popup);
        if (!items.length) { return null; }
        const normalized = (index + items.length) % items.length;
        this.markSelected(items[normalized]);
        return items[normalized];
    }

    moveSelection(delta) {
        const popup = this.activePopup || this.rootControls.get(this.activeRoot)?.popup;
        const items = this.menuItems(popup);
        if (!items.length) { return; }
        const current = items.indexOf(document.activeElement);
        this.selectByIndex(popup, current < 0 ? (delta > 0 ? 0 : items.length - 1) : current + delta);
    }

    openMenu(menuRoot, { focusFirst = true } = {}) {
        const { popup, toggle } = this.rootControls.get(menuRoot) || {};
        if (!popup || !toggle) { return; }
        toggle.scrollIntoView?.({ block: "nearest", inline: "nearest" });
        const savedFocus = this.previousFocus
            || (document.activeElement instanceof HTMLElement ? document.activeElement : null);
        this.closeMenus({ restoreFocus: false, preservePreviousFocus: true });
        this.previousFocus = savedFocus;
        popup.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        toggle.classList.add("is-current");
        this.current = toggle._tvMenuItem || this.current;
        this.activeRoot = menuRoot;
        this.activePopup = popup;
        this._paintMenuItem(toggle._tvMenuItem);
        requestAnimationFrame(() => {
            if (popup.hidden || !popup.isConnected) { return; }
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

    openSubmenu(toggle, { focusFirst = true, scrollTop = null } = {}) {
        const { root: submenuRoot, popup } = this.submenuControls.get(toggle) || {};
        if (!submenuRoot || !popup) { return false; }
        this.closeSubmenusOutsidePath(submenuRoot, popup);
        popup.hidden = false;
        toggle.classList.add("is-submenu-open");
        toggle.setAttribute("aria-expanded", "true");
        this.current = toggle._tvMenuItem || this.current;
        this.activePopup = popup;
        this._paintMenuItem(toggle._tvMenuItem);
        requestAnimationFrame(() => {
            if (popup.hidden || !popup.isConnected) { return; }
            fitMenuPopupToViewport(submenuRoot, popup);
            fillBorders(popup);
            if (scrollTop !== null) { popup.querySelector(".tv-menu-popup-body").scrollTop = scrollTop; }
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
        if (!popup || popup.hidden) { return; }
        const { toggle, parentPopup } = this.submenuByPopup.get(popup) || {};
        this.submenuByPopup.forEach((_controls, child) => {
            if (child !== popup && popup.contains(child)) {
                this.closeSubmenu(child, { focusToggle: false });
            }
        });
        popup.hidden = true;
        resetMenuPopupLayout(popup);
        if (toggle) {
            toggle.classList.remove("is-submenu-open");
            toggle.setAttribute("aria-expanded", "false");
            this._paintMenuItem(toggle._tvMenuItem);
        }
        this.activePopup = parentPopup || null;
        if (focusToggle && toggle) { this.markSelected(toggle); }
    }

    closeSubmenusOutsidePath(submenuRoot, activePopup) {
        this.submenuByPopup.forEach((_controls, popup) => {
            if (popup !== activePopup && !popup.contains(submenuRoot)) {
                this.closeSubmenu(popup, { focusToggle: false });
            }
        });
    }

    closeSubmenus() {
        this.submenuByPopup.forEach((_controls, popup) => {
            this.closeSubmenu(popup, { focusToggle: false });
        });
    }

    closeMenus({ restoreFocus = true, preservePreviousFocus = false } = {}) {
        const focusTarget = this.previousFocus;
        const selected = this.selectedElement?._tvMenuItem;
        this.closeSubmenus();
        this.menuRoots.forEach((menuRoot) => {
            const { popup, toggle } = this.rootControls.get(menuRoot) || {};
            if (popup) {
                popup.hidden = true;
                resetMenuPopupLayout(popup);
            }
            if (toggle) {
                toggle.setAttribute("aria-expanded", "false");
                toggle.classList.remove("is-current");
                this._paintMenuItem(toggle._tvMenuItem);
            }
        });
        if (this.selectedElement) {
            this.selectedElement.classList.remove("is-menu-selected");
            this.selectedElement.tabIndex = -1;
            this.selectedElement = null;
        }
        this.activeRoot = null;
        this.activePopup = null;
        if (!preservePreviousFocus) { this.previousFocus = null; }
        if (restoreFocus) {
            const manager = owningDesktop(this)?.dialogManager;
            if (manager) { manager._focusTarget(manager.activeTarget, focusTarget); }
            else if (focusTarget?.isConnected && typeof focusTarget.focus === "function") { focusTarget.focus({ preventScroll: true }); }
        }
        this._paintMenuItem(selected);
    }

    switchRoot(delta) {
        if (!this.menuRoots.length) { return; }
        const current = this.menuRoots.indexOf(this.activeRoot);
        const index = current < 0 ? 0 : (current + delta + this.menuRoots.length) % this.menuRoots.length;
        this.openMenu(this.menuRoots[index]);
    }

    activateItem(item, nativeEvent = null) {
        if (!(item instanceof TVMenuItem) || commandDisabled(item) || !item.command) { return false; }
        this.current = item;
        const focusRemainsInMenu = Boolean(document.activeElement?.closest?.("[data-tv-menu-bar]"));
        this.closeMenus({ restoreFocus: focusRemainsInMenu });
        this.dispatchEvent(new TVEvent(evCommand, {
            command: item.command,
            infoPtr: item,
            nativeEvent,
        }));
        return true;
    }

    activateMnemonic(key, nativeEvent = null) {
        const mnemonic = String(key || "").toLowerCase();
        const element = this.menuItems(this.activePopup).find((candidate) => (
            this.menuMnemonic(candidate._tvMenuItem) === mnemonic
        ));
        if (!element) { return false; }
        this.markSelected(element);
        const item = element._tvMenuItem;
        if (item.subMenu instanceof TVMenu) {
            this.openSubmenu(element);
        } else {
            this.activateItem(item, nativeEvent);
        }
        return true;
    }

    activateKeyCode(keyCode, nativeEvent = null) {
        if (!keyCode) { return false; }
        const item = Array.from(this.itemElements.keys())
            .find((candidate) => candidate.keyCode === keyCode && !commandDisabled(candidate));
        if (!item) { return false; }
        const element = this.itemElements.get(item);
        if (item.subMenu instanceof TVMenu && !this.topLevelItems.has(item)) {
            this.openSubmenu(element);
        } else if (item.subMenu instanceof TVMenu) {
            this.openMenu(this.rootByItem.get(item));
        } else {
            this.activateItem(item, nativeEvent);
        }
        return true;
    }

    handleEvent(event) {
        if (event.what === evBroadcast && event.command === cmCommandSetChanged) {
            this.itemElements.forEach((element, item) => this._syncItemState(item, element));
            return;
        }
        if (event.what === evMouseDown) {
            const item = event.infoPtr instanceof TVMenuItem ? event.infoPtr : null;
            const element = this.itemElements.get(item);
            if (!item) {
                this.closeMenus({ restoreFocus: false });
            } else if (element && !commandDisabled(item)) {
                if (item.subMenu instanceof TVMenu && !this.topLevelItems.has(item)) {
                    this.markSelected(element, false);
                    this.openSubmenu(element, { focusFirst: false });
                } else if (item.subMenu instanceof TVMenu) {
                    const root = this.rootByItem.get(item);
                    this.openMenu(root, { focusFirst: false });
                } else {
                    this.activateItem(item, event.nativeEvent);
                }
            }
            this.clearEvent(event);
            return;
        }
        if (event.what === evMouseMove) {
            const item = event.infoPtr instanceof TVMenuItem ? event.infoPtr : null;
            const element = this.itemElements.get(item);
            if (element && !commandDisabled(item)) {
                if (this.activeRoot && item.subMenu instanceof TVMenu && !this.topLevelItems.has(item)) {
                    this.markSelected(element, false);
                    this.openSubmenu(element, { focusFirst: false });
                } else if (item.subMenu instanceof TVMenu) {
                    const root = this.rootByItem.get(item);
                    if (this.activeRoot && this.activeRoot !== root) {
                        this.openMenu(root, { focusFirst: false });
                    }
                } else if (this.activeRoot) {
                    this.markSelected(element, false);
                    this.closeSubmenusOutsidePath(element, null);
                }
            }
            this.clearEvent(event);
            return;
        }
        if (event.what !== evKeyDown) { return; }
        const key = event.nativeEvent;
        if (!key || key.defaultPrevented) { return; }
        if (this.activateKeyCode(getKeyCode(key), key)) {
            this.clearEvent(event);
            return;
        }
        const plainF10 = key.key === "F10" && !key.altKey && !key.ctrlKey && !key.metaKey && !key.shiftKey;
        if (plainF10) {
            if (this.activeRoot) { this.closeMenus(); }
            else if (this.menuRoots.length) { this.openMenu(this.menuRoots[0]); }
            this.clearEvent(event);
            return;
        }
        if (key.altKey && !key.ctrlKey && !key.metaKey && key.key.length === 1) {
            const root = this.menuRoots.find((candidate) => (
                this.menuMnemonic(this.rootControls.get(candidate)?.toggle?._tvMenuItem) === key.key.toLowerCase()
            ));
            if (root) {
                this.openMenu(root);
                this.clearEvent(event);
                return;
            }
            const action = this.topLevelActions.find((candidate) => (
                this.menuMnemonic(candidate._tvMenuItem) === key.key.toLowerCase()
            ));
            if (action) {
                this.activateItem(action._tvMenuItem, key);
                this.clearEvent(event);
                return;
            }
        }
        if (!this.activeRoot) { return; }
        if (key.key === "Escape") {
            if (this.activePopup && this.activePopup !== this.rootControls.get(this.activeRoot)?.popup) {
                this.closeSubmenu(this.activePopup);
            } else {
                this.closeMenus();
            }
        } else if (key.key === "ArrowDown" || (key.key === "Tab" && !key.shiftKey)) {
            this.moveSelection(1);
        } else if (key.key === "ArrowUp" || (key.key === "Tab" && key.shiftKey)) {
            this.moveSelection(-1);
        } else if (key.key === "Home" || key.key === "End") {
            const items = this.menuItems(this.activePopup);
            this.selectByIndex(this.activePopup, key.key === "Home" ? 0 : items.length - 1);
        } else if (key.key === "ArrowRight") {
            const current = document.activeElement;
            if (!(current?._tvMenuItem?.subMenu instanceof TVMenu)
                || !this.openSubmenu(current)) {
                this.switchRoot(1);
            }
        } else if (key.key === "ArrowLeft") {
            if (this.activePopup && this.activePopup !== this.rootControls.get(this.activeRoot)?.popup) {
                this.closeSubmenu(this.activePopup);
            } else {
                this.switchRoot(-1);
            }
        } else if (key.key === "Enter" || key.key === " ") {
            const current = document.activeElement;
            if (!this.menuItems(this.activePopup).includes(current)) { return; }
            if (current._tvMenuItem?.subMenu instanceof TVMenu) {
                this.openSubmenu(current);
            } else {
                this.activateItem(current._tvMenuItem, key);
            }
        } else if (!(key.altKey || key.ctrlKey || key.metaKey) && key.key.length === 1) {
            if (!this.activateMnemonic(key.key, key)) { return; }
        } else {
            return;
        }
        this.clearEvent(event);
    }

    updateItem(item, element = null) {
        if (!(item instanceof TVMenuItem)) { return; }
        const target = element || this.itemElements.get(item);
        if (!target) { return; }
        const name = this._drawItemName(item);
        const markup = `<span class="${target.classList.contains("tv-menu-popup-item") ? "tv-menu-popup-label" : "tv-menu-label"}">${name}</span>`
            + (target.classList.contains("tv-submenu-toggle") ? '<span class="tv-submenu-arrow">►</span>' : "")
            + (!(item.subMenu instanceof TVMenu) && item.param ? `<span class="tv-menu-hotkey">${escapeHtml(item.param)}</span>` : "");
        this._itemMarkups ||= new WeakMap();
        const changed = (this._itemMarkups.get(target) ?? target.innerHTML) !== markup;
        if (changed) { target.innerHTML = markup; }
        this._itemMarkups.set(target, markup);
        this._syncItemState(item, target);
        const popup = target.closest?.(".tv-menu-popup");
        if (!element && popup?._tvMenuBox && !popup.hidden) {
            popup._tvMenuBox._fit(popup.parentElement);
            fillBorders(popup);
        }
        if (!element && changed && this instanceof TVMenuBar) { this.drawView(); }
    }

    _syncItemState(item, target) {
        const disabled = commandDisabled(item);
        target.disabled = disabled;
        target.setAttribute("aria-disabled", disabled ? "true" : "false");
        target.classList.toggle("is-disabled", disabled);
        if (disabled) {
            if (this._hoveredItem === item) { this._hoveredItem = null; }
            target.classList.remove("is-menu-selected");
            target.tabIndex = -1;
            if (this.selectedElement === target) { this.selectedElement = null; }
        } else if (target.classList.contains("tv-menu-item")) { target.removeAttribute("tabindex"); }
        this._paintMenuItem(item, target);
    }

    setSubMenu(item, menu) {
        if (!(item instanceof TVMenuItem) || !(menu instanceof TVMenu)) { return; }
        const root = this.rootByItem.get(item);
        const popup = root && this.rootControls.get(root)?.popup;
        item.subMenu = menu;
        if (!popup) { return; }
        const open = this.activeRoot === root;
        const selected = this.selectedElement?._tvMenuItem;
        const focused = this.selectedElement === document.activeElement;
        const scroll = popup.querySelector(".tv-menu-popup-body")?.scrollTop || 0;
        const path = [];
        let active = this.activePopup;
        while (open && active && active !== popup) {
            const controls = this.submenuByPopup.get(active);
            if (!controls) { break; }
            path.unshift({ item: controls.toggle._tvMenuItem, scroll: active.querySelector(".tv-menu-popup-body").scrollTop });
            active = controls.parentPopup;
        }
        popup.outerHTML = this._drawSubMenu(item, null);
        this.bindRoot(this.root);
        if (open) {
            this.activePopup = this.rootControls.get(root).popup;
            this.activePopup.hidden = false;
            fitMenuPopupToViewport(root, this.activePopup);
            fillBorders(this.activePopup);
            this.activePopup.querySelector(".tv-menu-popup-body").scrollTop = scroll;
            for (const entry of path) {
                const toggle = this.itemElements.get(entry.item);
                if (!toggle || commandDisabled(entry.item) || !this.openSubmenu(toggle, { focusFirst: false, scrollTop: entry.scroll })) { break; }
            }
            const element = this.itemElements.get(selected);
            if (element?.closest(".tv-menu-popup") === this.activePopup) {
                this.markSelected(element, false); if (focused) { element.focus({ preventScroll: true }); }
            }
        }
    }

    layoutSubMenu(item) {
        const topRoot = this.rootByItem.get(item), controls = this.submenuControls.get(this.itemElements.get(item));
        const root = topRoot || controls?.root, popup = topRoot ? this.rootControls.get(topRoot)?.popup : controls?.popup;
        if (!popup || popup.hidden) { return; }
        const body = popup.querySelector(".tv-menu-popup-body"), scroll = body.scrollTop;
        fitMenuPopupToViewport(root, popup);
        fillBorders(popup);
        body.scrollTop = scroll;
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
            const toggleAttrs = attrsToString({
                type: "button",
                "data-tv-submenu-toggle": true,
                "data-tv-menu-item-id": item._menuId,
                ...TVView._controlAttrs({
                    command: "menu-toggle",
                    disabled: commandDisabled(item),
                    ariaHasPopup: true,
                    ariaExpanded: false,
                }),
            });
            return '<div class="tv-submenu-root" data-tv-submenu-root="true"' + helpAttr + '>'
                + '<button class="tv-menu-popup-item tv-submenu-toggle" ' + toggleAttrs + '>'
                + `<span class="tv-menu-popup-label">${this._drawItemName(item)}</span><span class="tv-submenu-arrow">►</span>`
                + '</button>'
                + this._drawSubMenu(item)
                + '</div>';
        }
        const isMenuBar = view === "bar";
        const href = item.getUrl();
        const tag = href ? "a" : "button";
        const attrs = attrsToString({
            ...(href ? { href } : { type: "button" }),
            ...(item.helpCtx !== hcNoContext ? { "data-tv-help-ctx": item.helpCtx } : {}),
            "data-tv-menu-item-id": item._menuId,
            ...TVView._controlAttrs({
                name: item.command,
                command: item.command,
                disabled: commandDisabled(item),
            }),
        });
        const className = isMenuBar ? "tv-menu-item tv-menu-button" : "tv-menu-popup-item";
        const shortcut = item.param
            ? `<span class="tv-menu-hotkey">${escapeHtml(item.param)}</span>`
            : "";
        const name = this._drawItemName(item);
        return `<${tag} class="${className}" ${attrs}><span class="${isMenuBar ? "tv-menu-label" : "tv-menu-popup-label"}">${name}</span>${shortcut}</${tag}>`;
    }

    _drawSubMenu(item, parentMenu = this) {
        let box = this.menuBoxes.get(item);
        if (box?.menu !== item.subMenu) {
            box?.destroy();
            box = new TVMenuBox(new TVRect(), item.subMenu, parentMenu);
            this.menuBoxes.set(item, box);
        }
        return box.draw();
    }

    _drawItemName(item) { return renderHotkeyMarkup(item.name); }

    renderItems(view = "popup") {
        return this.menu.entries().map((item) => this.drawItem(item, view));
    }

    draw(view = "popup") { return this.renderItems(view).join(""); }

    destroy() {
        this.closeMenus({ restoreFocus: false });
        this.bindRoot(null);
        this.owner = null;
    }
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
        param = "",
        next = null,
    ) {
        this.next = next instanceof TVMenuItem ? next : null;
        this._menuId = `tv-menu-item-${TVMenuItem.nextId++}`;
        this.name = String(name || "");
        this.command = command;
        this.flags = 0;
        this.keyCode = Number(keyCode) || kbNoKey;
        this.helpCtx = normalizeHelpContext(helpCtx);
        this.param = String(param || "");
        this.subMenu = null;
        this.separator = false;
        this.disabled = false;
    }

    // Browser navigation fallback; ordinary TVision commands remain buttons.
    getUrl() { return ""; }

    append(item) {
        if (!(item instanceof TVMenuItem)) {
            throw new TypeError("TVMenuItem.append expects TVMenuItem");
        }
        let tail = this;
        const visited = new Set();
        while (tail.next instanceof TVMenuItem && !visited.has(tail)) {
            visited.add(tail);
            tail = tail.next;
        }
        tail.next = item;
        return this;
    }

    setDisabled(disabled = true) {
        this.disabled = Boolean(disabled);
        return this;
    }
}

TVMenuItem.nextId = 1;

class TVSubMenu extends TVMenuItem {
    constructor(name, keyCode = kbNoKey, helpCtx = hcNoContext) {
        super(name, "", keyCode, helpCtx);
        this.subMenu = new TVMenu();
    }

    append(item) {
        if (!(item instanceof TVMenuItem)) {
            throw new TypeError("TVSubMenu.append expects TVMenuItem");
        }
        if (!this.subMenu.items) {
            this.subMenu.items = item;
            this.subMenu.deflt = item;
        } else {
            this.subMenu.items.append(item);
        }
        return this;
    }
}

function NewItem(name, param, keyCode, command, helpCtx, next = null) {
    return new TVMenuItem(name, command, keyCode, helpCtx, param, next);
}

function NewMenu(items = null) {
    return new TVMenu(items);
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
    const item = new TVSubMenu(name, kbNoKey, helpCtx);
    item.subMenu = subMenu;
    item.next = next instanceof TVMenuItem ? next : null;
    return item;
}

class TVMenuBar extends TVMenuView {
    constructor(bounds, menu = new TVMenu(), parentMenu = null) {
        super(bounds, menu, parentMenu);
        this._itemRects = new Map();
        this.onMenuScroll = () => { if (this.activeRoot) { this.drawView(); } };
    }

    bindRoot(root) {
        this.itemsRoot?.removeEventListener("scroll", this.onMenuScroll);
        super.bindRoot(root);
        this.itemsRoot = this.directChild(root, ".tv-menu-items");
        this.itemsRoot?.addEventListener("scroll", this.onMenuScroll, { passive: true });
        this.drawView();
        if (root) {
            document.fonts?.ready.then(() => {
                if (this.root === root && root.isConnected) { this.drawView(); }
            });
        }
        return this;
    }

    getItemRect(item) { return this._itemRects.get(item)?.copy() || new TVRect(); }

    _itemWidth(item) {
        const element = this.itemElements.get(item);
        const range = document.createRange(), cell = measureCells();
        const columns = (part) => {
            if (!part) { return 0; }
            range.selectNodeContents(part);
            return Math.ceil(range.getBoundingClientRect().width / cell.width);
        };
        const suffix = columns(element?.querySelector(".tv-menu-hotkey"));
        return Math.max(3, columns(element?.querySelector(".tv-menu-label")) + 2 + (suffix ? suffix + 2 : 0));
    }

    _layoutItems(root, items, bounds, widths = null) {
        if (!root) { return; }
        this._placePart(root, bounds);
        let column = 0;
        for (const item of items) {
            const button = this.itemElements.get(item), entry = this.rootByItem.get(item) || button;
            if (!entry || entry.hidden) { continue; }
            const width = widths?.get(item) ?? this._itemWidth(item);
            this._itemRects.set(item, new TVRect(bounds.x1 + column, bounds.y1, bounds.x1 + column + width, bounds.y1 + 1));
            this._placePart(entry, new TVRect(column, 0, column + width, 1));
            if (entry !== button) { this._placePart(button, new TVRect(0, 0, width, 1)); }
            const suffix = button.querySelector(".tv-menu-hotkey"), suffixWidth = suffix ? Array.from(suffix.textContent).length : 0;
            this._placePart(button.querySelector(".tv-menu-label"), new TVRect(1, 0, Math.max(1, width - 1 - (suffixWidth ? suffixWidth + 2 : 0)), 1));
            if (suffix) { this._placePart(suffix, new TVRect(Math.max(1, width - 1 - suffixWidth), 0, Math.max(1, width - 1), 1)); }
            column += width;
        }
    }

    _layout() {
        if (!this.itemsRoot || !this.root?.clientWidth) { return; }
        const columns = Math.floor(this.root.clientWidth / measureCells().width);
        this.setBounds(new TVRect(0, 0, columns, 1));
        this.root.style.height = `${this.size.y}em`;
        this._itemRects.clear();
        this._layoutItems(this.itemsRoot, this.menu.entries(), this.getExtent());
    }

    drawView() {
        this._layout();
        if (this.activeRoot) {
            fitMenuPopupToViewport(this.activeRoot, this.rootControls.get(this.activeRoot)?.popup);
            fillBorders(this.root);
        }
        return this;
    }

    drawItem(item, view = "bar") {
        if (view === "bar" && item.subMenu instanceof TVMenu) {
            const helpAttr = item.helpCtx !== hcNoContext ? ` data-tv-help-ctx="${item.helpCtx}"` : "";
            const toggleAttrs = attrsToString({
                type: "button",
                "data-tv-menu-toggle": true,
                "data-tv-menu-item-id": item._menuId,
                ...TVView._controlAttrs({
                    name: "menu-toggle",
                    command: "menu-toggle",
                    disabled: commandDisabled(item),
                    ariaHasPopup: true,
                    ariaExpanded: false,
                }),
            });
            return `<div class="tv-menu-root" data-tv-menu-root="true"${helpAttr}>`
                + `<button class="tv-menu-item tv-menu-button" ${toggleAttrs}><span class="tv-menu-label">${this._drawItemName(item)}</span></button>`
                + this._drawSubMenu(item, null)
                + "</div>";
        }
        return super.drawItem(item, view);
    }

    draw() {
        return `<nav class="tv-menu-items">${this.renderItems("bar").join("")}</nav>`;
    }
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

    getUrl() { return ""; }
}

// Native browser navigation keeps ordinary status commands as TVStatusItem.
class TVStatusLink extends TVStatusItem {
    constructor(text, url, newWindow = false) {
        super(text);
        this.url = String(url || "");
        this.newWindow = Boolean(newWindow);
    }

    getUrl() { return this.url; }
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
        this.rightItems = [];
        this.itemElements = new Map();
        this._itemRects = new Map();
        this._itemText = new WeakMap();
        this.eventMask |= evBroadcast;
        this.onResize = () => this.drawView();
        this._hoveredItem = null;
        this._onStatusPaint = event => {
            const target = /out$/.test(event.type) ? event.relatedTarget : event.target;
            const element = target?.closest?.("button, a"), item = element?._tvStatusItem;
            const previous = this._hoveredItem;
            if (event.type.startsWith("mouse")) { this._hoveredItem = this.root?.contains(element) ? item : null; }
            for (const entry of new Set([previous, item, event.target?.closest?.("button, a")?._tvStatusItem])) {
                this._paintStatusItem(entry);
            }
        };
    }

    getPalette() { return [2, 3, 4, 5, 6, 7].map(index => this._appColor(index)); }

    _paintStatusItem(item) {
        const element = this.itemElements.get(item);
        if (!element) { return; }
        const selected = item === this._hoveredItem || element === document.activeElement;
        this._paintPaletteText(element, this.getColor(commandDisabled(item) ? 2 : selected ? 4 : 1),
            this.getColor(commandDisabled(item) ? 2 : selected ? 6 : 3));
    }

    _drawPalette() {
        if (!this.root) { return this; }
        super._drawPalette();
        this.itemElements?.forEach((_element, item) => this._paintStatusItem(item));
        return this;
    }

    hint(_helpCtx) { return ""; }

    handleEvent(event) {
        if (event.what === evBroadcast && event.command === cmCommandSetChanged) { this.drawView(); return; }
        const mouse = event.what === evMouseDown;
        if (!mouse && event.what !== evKeyDown) { return; }
        if (event.nativeEvent?.defaultPrevented) { return; }
        const items = [...this.items, ...this.rightItems];
        const enabled = viewAcceptsInput(this);
        const keyCode = !mouse && getKeyCode(event.nativeEvent);
        const item = mouse ? event.infoPtr : enabled && keyCode
            ? items.find(item => item.keyCode === keyCode && !commandDisabled(item)) : null;
        if (mouse && !(item instanceof TVStatusItem)) { return; }
        if (!enabled || !items.includes(item) || commandDisabled(item)) {
            if (mouse) { event.nativeEvent?.preventDefault(); this.clearEvent(event); }
            return;
        }
        if (item.getUrl() || !item.command) { return; }
        if (!mouse) { this._revealItem(item); }
        event.nativeEvent?.preventDefault();
        event.what = evCommand;
        event.command = item.command;
        event.infoPtr = item;
    }

    _ensureChrome() {
        if (this.hintView) { return; }
        this.hintView = new TVStaticText(new TVRect(0, 0, 1, 1), "");
        this.separator = new TVStaticText(new TVRect(0, 0, 1, 1), "│");
        this.hintView.owner = this.separator.owner = this;
    }

    findItems(helpCtx = this.getHelpCtx()) {
        const context = normalizeHelpContext(helpCtx);
        let definition = this.defs;
        while (definition) {
            if (typeof context === "string"
                ? (context === definition.min && context === definition.max)
                    || (definition.min === hcNoContext && definition.max === 0xffff)
                : context >= definition.min && context <= definition.max) {
                this.items = definition.items;
                return this.items;
            }
            definition = definition.next;
        }
        this.items = [];
        return this.items;
    }

    drawItem(item) {
        const url = item.getUrl(), tag = url ? "a" : "button";
        const attrs = attrsToString({
            ...(url ? { href: url, ...(item.newWindow ? { target: "_blank", rel: "noopener" } : {}) } : { type: "button" }),
            ...TVView._controlAttrs({
                name: item.command,
                command: item.command,
                value: item.param && typeof item.param === "object" && Object.hasOwn(item.param, "value")
                    ? item.param.value
                    : item.param,
                commandData: item.param && typeof item.param === "object"
                    ? Object.fromEntries(Object.entries(item.param).filter(([key]) => key !== "value"))
                    : {},
                disabled: commandDisabled(item),
            }),
        });
        return `<${tag} class="tv-status-item" ${attrs}><span class="tv-status-label">${renderHotkeyMarkup(item.text)}</span></${tag}>`;
    }

    draw() {
        this._ensureChrome();
        this.hintView.setText(this.hint(this.getHelpCtx()) || "");
        return `<div class="tv-status-items">${this.items.map(item => this.drawItem(item)).join("")}</div>`
            + `<div class="tv-status-right">${this.rightItems.map(item => this.drawItem(item)).join("")}</div>`
            + this.separator.draw() + this.hintView.draw();
    }

    bindRoot(root) {
        window.removeEventListener("resize", this.onResize);
        for (const type of ["mouseover", "mouseout", "focusin", "focusout"]) { this.root?.removeEventListener(type, this._onStatusPaint); }
        if (root?._tvStatusLine && root._tvStatusLine !== this) { root._tvStatusLine.bindRoot(null); }
        if (this.root?._tvStatusLine === this) { delete this.root._tvStatusLine; }
        super.bindRoot(root);
        watchCommands(this, Boolean(root));
        if (!root) {
            this.hintView?.bindRoot(null); this.separator?.bindRoot(null);
            this._hoveredItem = null;
            this.itemElements.clear(); this._itemRects.clear();
            this.itemsRoot = this.rightRoot = null;
            return this;
        }
        this._ensureChrome();
        this.bindItems();
        for (const type of ["mouseover", "mouseout", "focusin", "focusout"]) { root.addEventListener(type, this._onStatusPaint); }
        window.addEventListener("resize", this.onResize, { passive: true });
        document.fonts?.ready.then(() => {
            if (this.root === root && root.isConnected) { this.drawView(); }
        });
        return this;
    }

    bindItems() {
        if (!this.root) { return; }
        this.root._tvStatusLine = this;
        this.itemsRoot = this.root.querySelector(":scope > .tv-status-items");
        this.rightRoot = this.root.querySelector(":scope > .tv-status-right");
        this._ensureChrome(); this.hintView.resolve(this.root); this.separator.resolve(this.root);
        this.itemElements.clear();
        const all = [...this.items, ...this.rightItems];
        for (const [selector, items] of [
            ["button.tv-status-item", all.filter(item => !item.getUrl())],
            ["a.tv-status-item", all.filter(item => item.getUrl())],
        ]) {
            this.root.querySelectorAll(selector).forEach((element, index) => {
                const item = items[index];
                if (!item) { return; }
                element._tvStatusItem = item; this.itemElements.set(item, element);
                this._itemText.set(item, item.text);
            });
        }
        this.drawView();
    }

    getItemRect(item) { return this._itemRects.get(item)?.copy() || new TVRect(); }

    _revealItem(item) { this.itemElements.get(item)?.scrollIntoView?.({ block: "nearest", inline: "nearest" }); }

    _itemWidth(item, cell, range) {
        const label = this.itemElements.get(item)?.firstElementChild;
        if (!label) { return 0; }
        range.selectNodeContents(label);
        return Math.ceil(range.getBoundingClientRect().width / cell.width) + 2;
    }

    _layoutItems(root, items, bounds, widths) {
        this._placePart(root, bounds);
        let column = 0;
        for (const item of items) {
            const element = this.itemElements.get(item), width = widths.get(item) || 0;
            if (!element) { continue; }
            this._itemRects.set(item, new TVRect(bounds.x1 + column, 0, bounds.x1 + column + width, 1));
            this._placePart(element, new TVRect(column, 0, column + width, 1));
            this._placePart(element.firstElementChild, new TVRect(1, 0, Math.max(1, width - 1), 1));
            column += width;
        }
    }

    _layout() {
        if (!this.root?.clientWidth || !this.itemsRoot || !this.rightRoot) { return; }
        const cell = measureCells(), range = document.createRange();
        const columns = Math.floor(this.root.clientWidth / cell.width), end = Math.max(0, columns - 1);
        this.setBounds(new TVRect(this.origin.x, this.origin.y, this.origin.x + columns, this.origin.y + 1));
        this.root.style.height = `${this.size.y}em`;
        this._itemRects.clear();
        const widths = new Map([...this.items, ...this.rightItems].map(item => [item, this._itemWidth(item, cell, range)]));
        const total = items => items.reduce((sum, item) => sum + widths.get(item), 0);
        const rightWidth = Math.min(total(this.rightItems), Math.floor(end / 3));
        const available = end - rightWidth, hasHint = Boolean(this.hintView.getText());
        const separatorWidth = hasHint && this.items.length ? Math.min(2, available) : 0;
        const reservedHint = hasHint ? Math.min(16, Math.floor(Math.max(0, available - separatorWidth) / 3)) : 0;
        const commandsWidth = Math.min(total(this.items), Math.max(0, available - separatorWidth - reservedHint));
        this._layoutItems(this.itemsRoot, this.items, new TVRect(0, 0, commandsWidth, 1), widths);
        this._layoutItems(this.rightRoot, this.rightItems, new TVRect(available, 0, end, 1), widths);
        this.separator.locate(new TVRect(commandsWidth, 0, commandsWidth + 1, 1));
        this.separator.setState(sfVisible, separatorWidth > 0);
        const hintLeft = commandsWidth + separatorWidth;
        this.hintView.locate(new TVRect(hintLeft, 0, Math.max(hintLeft, available), 1));
        this.hintView.setState(sfVisible, hasHint && available > hintLeft);
    }

    render() {
        if (this.root) { this.root.innerHTML = this.draw(); this.bindItems(); }
        return this;
    }

    _drawBounds() { super._drawBounds(); this.drawView(); }

    drawView() {
        if (!this.root) { return this; }
        measuredCell = null;
        this._ensureChrome(); this.hintView.setText(this.hint(this.getHelpCtx()) || "");
        this.itemElements.forEach((element, item) => {
            if (this._itemText.get(item) !== item.text) {
                element.firstElementChild.innerHTML = renderHotkeyMarkup(item.text); this._itemText.set(item, item.text);
            }
            if (element.tagName === "BUTTON") { element.disabled = commandDisabled(item); }
            if (element.tagName === "A") {
                element.setAttribute("href", item.getUrl());
                if (item.newWindow) { element.setAttribute("target", "_blank"); element.setAttribute("rel", "noopener"); }
                else { element.removeAttribute("target"); element.removeAttribute("rel"); }
                if (commandDisabled(item)) { element.tabIndex = -1; } else { element.removeAttribute("tabindex"); }
            }
            element.setAttribute("aria-disabled", commandDisabled(item) ? "true" : "false");
        });
        this._drawPalette();
        this._layout();
        return this;
    }

    destroy() { this.bindRoot(null); this.owner = null; }
}

class TVMenuBox extends TVMenuView {
    constructor(bounds, menu = new TVMenu(), parentMenu = null) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVMenuBox expects TVRect bounds");
        }
        super(bounds, menu);
        this.parentMenu = parentMenu;
    }

    bindRoot(root) {
        if (this.root && this.root !== root) {
            this.root._tvMenuPopupScrollbar?.destroy();
            delete this.root._tvMenuPopupScrollbar;
            delete this.root._tvMenuBox;
        }
        super.bindRoot(root);
        if (root) {
            root._tvMenuBox = this;
            [this.topFrame, this.main, this.bottomFrame] = root.children;
            [this.body, this.scrollbarRoot, this.rightFrame] = this.main.children;
        } else {
            this.topFrame = this.main = this.bottomFrame = this.body = this.scrollbarRoot = this.rightFrame = null;
        }
        return this;
    }

    getItemRect(item) {
        const row = this.menu.entries().indexOf(item);
        return row < 0 ? new TVRect() : new TVRect(1, row + 1, this.size.x - 1, row + 2);
    }

    _naturalWidth(cell) {
        const range = document.createRange();
        let width = 14;
        this.menu.entries().forEach((item) => {
            if (item.separator) { return; }
            const element = this.itemElements.get(item);
            const columns = (part) => {
                if (!part) { return 0; }
                range.selectNodeContents(part);
                return Math.ceil(range.getBoundingClientRect().width / cell.width);
            };
            const label = columns(element?.querySelector(".tv-menu-popup-label"));
            const suffix = columns(element?.querySelector(".tv-submenu-arrow, .tv-menu-hotkey"));
            width = Math.max(width, label + 5 + (suffix ? suffix + 2 : 0));
        });
        return width;
    }

    _fit(anchor) {
        if (!this.root || this.root.hidden) { return; }
        const cell = measureCells(), rect = anchor.getBoundingClientRect();
        const parent = this.parentMenu ? anchor.closest(".tv-menu-popup")?.getBoundingClientRect() : null;
        const top = parent ? parent.top : rect.bottom;
        const available = Math.max(3, Math.floor((window.innerHeight - 2 * cell.height - top) / cell.height));
        const rows = this.menu.entries().length;
        const height = Math.min(rows + 2, available);
        const width = Math.min(this._naturalWidth(cell) + (rows > height - 2 ? 1 : 0), Math.max(4, Math.floor(window.innerWidth / cell.width)));
        let left = parent ? rect.right - cell.width : rect.left;
        if (parent && left + width * cell.width > window.innerWidth) { left = rect.left + cell.width - width * cell.width; }
        left = Math.max(0, Math.min(left, window.innerWidth - width * cell.width));
        const maximumTop = Math.max(0, window.innerHeight - (height + 2) * cell.height);
        const nextTop = Math.max(0, Math.min(parent ? rect.top - cell.height : rect.bottom, maximumTop));
        const x = left / cell.width;
        const y = nextTop / cell.height;
        const resized = this.size.x !== width || this.size.y !== height;
        this.locate(new TVRect(x, y, x + width, y + height));
        if (resized) { this.body.querySelector(".is-menu-selected")?.scrollIntoView({ block: "nearest" }); }
        if (!this.root._tvMenuPopupScrollbar) {
            this.root._tvMenuPopupScrollbar = new TVScrollBar(new TVRect()).bindRoot(this.main);
        }
        this.root._tvMenuPopupScrollbar.refresh();
        this.menuBoxes.forEach((box) => {
            if (box.root && !box.root.hidden) { box._fit(box.root.parentElement); }
        });
    }

    _drawBounds() {
        super._drawBounds();
        if (this.root) {
            this.root.style.position = "fixed";
            this._layout();
        }
    }

    _layout() {
        if (!this.root || this.root.hidden) { return; }
        const width = this.size.x, height = this.size.y, rows = this.menu.entries().length;
        const scrolling = rows > height - 2;
        const place = (element, x, y, w, h) => this._placePart(element, new TVRect(x, y, x + Math.max(0, w), y + Math.max(0, h)));
        this.root.classList.toggle("is-scrollable", scrolling);
        this.body.classList.toggle("is-scrollable", scrolling);
        this.scrollbarRoot.hidden = this.rightFrame.hidden = !scrolling;
        place(this.topFrame, 0, 0, width, 1);
        place(this.main, 0, 1, width, height - 2);
        place(this.body, 0, 0, width, height - 2);
        place(this.bottomFrame, 0, height - 1, width, 1);
        place(this.scrollbarRoot, width - 2, 0, 1, height - 2);
        place(this.rightFrame, width - 1, 0, 1, height - 2);
        const frameRow = (row) => {
            const [left, fill, right] = row.children;
            place(left, 0, 0, 1, 1); place(fill, 1, 0, width - 2, 1); place(right, width - 1, 0, 1, 1);
        };
        frameRow(this.topFrame); frameRow(this.bottomFrame);
        let row = 0;
        const parts = Array.from(this.body.children);
        for (let index = 0; index < parts.length;) {
            const part = parts[index];
            if (part.classList.contains("tv-menu-popup-separator")) {
                place(part, 0, row++, width, 1); frameRow(part); index += 1;
            } else {
                const [left, items, right] = parts.slice(index, index + 3);
                const count = items.children.length, itemWidth = width - 2 - (scrolling ? 1 : 0);
                place(left, 0, row, 1, count); place(items, 1, row, width - 2, count); place(right, width - 1, row, 1, count);
                Array.from(items.children).forEach((entry, offset) => {
                    place(entry, 0, offset, itemWidth, 1);
                    const button = entry.classList.contains("tv-submenu-root") ? entry.firstElementChild : entry;
                    if (button !== entry) { place(button, 0, 0, itemWidth, 1); }
                    const suffix = button.querySelector(".tv-submenu-arrow, .tv-menu-hotkey");
                    const suffixWidth = suffix ? Array.from(suffix.textContent).length : 0;
                    place(button.querySelector(".tv-menu-popup-label"), 1, 0, itemWidth - 3 - (suffixWidth ? suffixWidth + 2 : 0), 1);
                    if (suffix) { place(suffix, Math.max(1, itemWidth - 2 - suffixWidth), 0, suffixWidth, 1); }
                });
                row += count; index += 3;
            }
        }
    }

    drawView() {
        if (this.root) { this._layout(); fillBorders(this.root); this.root._tvMenuPopupScrollbar?.refresh(); }
        return this;
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
        const segments = [[]];
        for (const item of this.menu.entries()) {
            if (item.separator) {
                segments.push("separator");
                segments.push([]);
            } else {
                segments[segments.length - 1].push(this.drawItem(item, "popup"));
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

function resetMenuPopupLayout(popup) {
    if (!popup?._tvMenuBox) { return; }
    popup._tvMenuBox.body.scrollTop = 0;
    popup._tvMenuPopupScrollbar?.stopRepeat();
}

function fitMenuPopupToViewport(root, popup) {
    if (root) { popup?._tvMenuBox?._fit(root); }
}

class TVMenuController {
    constructor({ root = document, onUnhandledKeyDown = null, commandTarget = null } = {}) {
        this.root = root;
        this.onUnhandledKeyDown = onUnhandledKeyDown;
        this._commandTarget = commandTarget;
        this.menuView = null;
        this.onDocumentClick = (event) => {
            if (!this.menuView?.root?.contains?.(event.target) && this.menuView?.activeRoot) {
                this.menuView.handleEvent(new TVEvent(evMouseDown, { nativeEvent: event }));
            }
        };
        this.onDocumentCommand = (event) => this.onCommand(event);
        this.onDocumentHover = (event) => this.onHover(event);
        this.onDocumentKeyDown = (event) => this.onKeyDown(event);
        this.onViewportResize = () => {
            const view = this.menuView;
            if (view instanceof TVMenuBar) { view.drawView(); return; }
            if (!view?.activeRoot) { return; }
            fitMenuPopupToViewport(view.activeRoot, view.rootControls.get(view.activeRoot)?.popup);
            fillBorders(view.root);
        };
        document.addEventListener("click", this.onDocumentClick);
        document.addEventListener("click", this.onDocumentCommand);
        document.addEventListener("mouseover", this.onDocumentHover);
        document.addEventListener("keydown", this.onDocumentKeyDown);
        window.addEventListener("resize", this.onViewportResize, { passive: true });
        this.refresh();
    }

    get commandTarget() { return this._commandTarget; }

    set commandTarget(target) {
        this._commandTarget = target;
        if (this.menuView) { this.menuView.owner = target instanceof TVView ? target : null; }
    }

    refresh() {
        this.menuView = this.root.querySelector("[data-tv-menu-bar]")?._tvMenuView || null;
        if (this.menuView) {
            this.menuView.owner = this._commandTarget instanceof TVView ? this._commandTarget : null;
            this.menuView.refresh();
        }
    }

    getHelpCtx() { return this.menuView?.getHelpCtx() || hcNoContext; }

    onCommand(nativeEvent) {
        const control = nativeEvent.target?.closest?.("button, a");
        if (!control) { return; }
        if (control.disabled || control.getAttribute("aria-disabled") === "true") {
            if (control._tvMenuItem || control._tvStatusItem) { nativeEvent.preventDefault(); }
            return;
        }
        const menuItem = control._tvMenuItem;
        if (menuItem instanceof TVMenuItem && this.menuView?.itemElements.get(menuItem) === control) {
            if (control.tagName === "A" && (nativeEvent.ctrlKey || nativeEvent.metaKey || nativeEvent.shiftKey)) { return; }
            nativeEvent.preventDefault();
            this.menuView?.handleEvent(new TVEvent(evMouseDown, {
                infoPtr: menuItem,
                nativeEvent,
            }));
            return;
        }
        const statusItem = control._tvStatusItem;
        const statusLine = this.root.querySelector("[data-tv-status-line]")?._tvStatusLine;
        if (!(statusItem instanceof TVStatusItem) || statusLine?.itemElements.get(statusItem) !== control) { return; }
        const event = new TVEvent(evMouseDown, {
            infoPtr: statusItem,
            nativeEvent,
        });
        statusLine.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (this._commandTarget instanceof TVView) {
            this._commandTarget.dispatchEvent(event);
        } else {
            this._commandTarget?.handleEvent?.(event);
        }
    }

    onHover(nativeEvent) {
        const element = nativeEvent.target?.closest?.("button, a");
        if (!element?._tvMenuItem || this.menuView?.itemElements.get(element._tvMenuItem) !== element
            || element.contains(nativeEvent.relatedTarget)) { return; }
        this.menuView?.handleEvent(new TVEvent(evMouseMove, {
            infoPtr: element._tvMenuItem || null,
            nativeEvent,
        }));
    }

    onKeyDown(nativeEvent) {
        if (nativeEvent.defaultPrevented) { return; }
        const event = new TVEvent(evKeyDown, { infoPtr: this._commandTarget, nativeEvent });
        this.menuView?.handleEvent(event);
        if (event.what === evNothing) {
            nativeEvent.preventDefault();
            nativeEvent.stopPropagation?.();
            return;
        }
        const statusLine = this.root.querySelector("[data-tv-status-line]")?._tvStatusLine;
        statusLine?.handleEvent(event);
        if (event.what === evCommand) {
            if (this._commandTarget instanceof TVView) {
                this._commandTarget.dispatchEvent(event);
            } else {
                this._commandTarget?.handleEvent?.(event);
            }
            return;
        }
        if (this.menuView?.activeRoot) { return; }
        if (this.onUnhandledKeyDown) {
            this.onUnhandledKeyDown(nativeEvent);
        } else if (this._commandTarget instanceof TVView) {
            this._commandTarget.dispatchEvent(event);
        } else {
            this._commandTarget?.handleEvent?.(event);
        }
    }

    destroy() {
        this.menuView?.closeMenus({ restoreFocus: false });
        document.removeEventListener("click", this.onDocumentClick);
        document.removeEventListener("click", this.onDocumentCommand);
        document.removeEventListener("mouseover", this.onDocumentHover);
        document.removeEventListener("keydown", this.onDocumentKeyDown);
        window.removeEventListener("resize", this.onViewportResize);
    }
}

let tvChoiceGroupId = 0;

class TVCluster extends TVView {
    constructor(bounds, options = []) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVCluster expects TVRect bounds");
        }
        super(bounds);
        this.options |= ofSelectable;
        this.strings = Array.isArray(options) ? options : [];
        this.value = this.strings.length > 31 ? 0n : 0;
        this.sel = 0;
        this.enableMask = this.strings.reduce((mask, _option, index) => mask | this.bit(index), this.value);
        this.eventMask |= evBroadcast;
        this.type = "checkbox";
        this.value = this._initialValue();
        this.itemClass = "tv-checkbox-item";
        this.markClass = "tv-checkbox-mark";
        this.choiceElements = [];
        this.hScrollBar = null;
        this.vScrollBar = null;
        this.viewport = null;
        this.scrollbarWidget = null;
        this._itemTextWidth = null;
        this._onChoiceFocus = event => this._drawPalette(event.type === "focusout" ? event.relatedTarget : event.target);
        this._onChoiceEvent = nativeEvent => {
            if (!this.root?.contains(nativeEvent.target)) { return; }
            const what = nativeEvent.type === "click" ? evMouseDown : nativeEvent.type === "keydown" ? evKeyDown : evBroadcast;
            this.dispatchEvent(new TVEvent(what, { infoPtr: this, nativeEvent }));
        };
    }

    getPalette() { return [47, 48, 49, 62].map(index => this._appColor(index)); }

    _choiceEnabled(index) {
        return !this.getState(sfDisabled) && this.buttonState(index) && !this.strings[index].disabled;
    }

    setState(state, enable) {
        super.setState(state, enable);
        if ((state & sfDisabled) !== 0) {
            if (enable) { this.setState(sfFocused, false); }
            this.syncInputs();
            this.scrollbarWidget?.refresh();
        }
        return this;
    }

    _drawPalette(focusedElement) {
        if (!this.root) { return this; }
        super._drawPalette();
        const focused = this.getState(sfDisabled) ? -1
            : this.choiceElements.indexOf(focusedElement === undefined ? document.activeElement : focusedElement);
        this.setState(sfFocused, focused >= 0);
        this.choiceElements.forEach((input, index) => {
            const disabled = !this._choiceEnabled(index);
            const color = this.getColor(disabled ? 4 : focused === index ? 2 : 1);
            const row = input.parentElement;
            this._paintPaletteText(row, color, this.getColor(disabled ? 4 : 3));
            row.style.cursor = disabled ? "default" : "pointer";
            if (this.type === "button") {
                this._paintPalette(input, color); input.style.cursor = disabled ? "default" : "pointer";
            }
        });
        return this;
    }

    bit(index) { return this.strings.length > 31 ? 1n << BigInt(index) : 1 << index; }

    _initialValue() {
        const empty = this.type === "radio" || this.strings.length <= 31 ? 0 : 0n;
        return this.strings.reduce((value, option, index) => option.checked
            ? (this.type === "radio" ? index : value | this.bit(index)) : value, empty);
    }

    _markText(index) {
        return this.type === "radio" ? `(${this.mark(index) ? "•" : " "})` : `[${this.mark(index) ? "X" : " "}]`;
    }

    setItems(options = []) {
        if (this.viewport) { this.viewport.scrollLeft = 0; this.viewport.scrollTop = 0; }
        this.strings = Array.isArray(options) ? options : [];
        this.value = this._initialValue();
        this.sel = this.type === "radio" ? this.value : 0;
        this.enableMask = this.strings.reduce((mask, _option, index) => mask | this.bit(index),
            this.strings.length > 31 ? 0n : 0);
        this.drawView();
        return this;
    }

    drawView() {
        const focused = Boolean(this.root && this.choiceElements.includes(document.activeElement));
        const left = this.viewport?.scrollLeft || 0, top = this.viewport?.scrollTop || 0;
        super.drawView();
        if (this.viewport) { this.viewport.scrollLeft = left; this.viewport.scrollTop = top; }
        if (focused) { this.focus(); }
        this.updateScrollbar();
        return this;
    }

    _itemMarkup(option, index) {
        const disabled = !this._choiceEnabled(index);
        const inputAttrs = attrsToString({
            type: this.type,
            class: "tv-choice-input",
            name: this.type === "radio" ? this.viewId : null,
            value: option.value !== undefined ? option.value : index,
            checked: this.mark(index),
            disabled,
        });
        const className = `${this.itemClass}${disabled ? " is-disabled" : ""}`;
        return `<label class="${className}"><input ${inputAttrs}><span class="${this.markClass}" aria-hidden="true">${this._markText(index)}</span> <span class="tv-choice-label">${renderHotkeyMarkup(option.label || "")}</span></label>`;
    }

    draw() {
        const items = this.strings.map((option, index) => this._itemMarkup(option, index)).join("");
        const attrs = attrsToString(this._drawAttrs({ hidden: !this.getState(sfVisible), "aria-disabled": String(this.getState(sfDisabled)) }));
        const bounds = [TVView._viewBoundsStyle(this), this._paletteStyle()].filter(Boolean).join(";");
        const style = bounds ? ` style="${escapeHtml(bounds)}"` : "";
        const scrollable = this.hScrollBar || this.vScrollBar;
        const content = scrollable
            ? `<div class="tv-cluster-viewport" data-tv-viewport>${items}</div>${this.vScrollBar?.draw() || ""}${this.hScrollBar?.draw() || ""}`
            : items;
        return `<div class="tv-cluster${this.getState(sfDisabled) ? " is-disabled" : ""}"${scrollable ? " data-tv-scroll-frame" : ""}${style} ${attrs}>${content}</div>`;
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        this.root?.removeEventListener("focusin", this._onChoiceFocus);
        this.root?.removeEventListener("focusout", this._onChoiceFocus);
        for (const type of ["click", "input", "change", "keydown"]) { this.root?.removeEventListener(type, this._onChoiceEvent); }
        this.scrollbarWidget?.destroy();
        this.choiceElements = [];
        this._itemTextWidth = null;
        super.bindRoot(root);
        this.root?.addEventListener("focusin", this._onChoiceFocus);
        this.root?.addEventListener("focusout", this._onChoiceFocus);
        for (const type of ["click", "input", "change", "keydown"]) { this.root?.addEventListener(type, this._onChoiceEvent); }
        this.viewport = this._query(".tv-cluster-viewport");
        this.scrollbarWidget = this.viewport ? (this.vScrollBar || this.hScrollBar)?.bindRoot(root) : null;
        this.updateScrollbar();
        return this;
    }

    updateScrollbar() {
        this.scrollbarWidget?._setClientExtent(this.getExtent());
        if (!this.scrollbarWidget) { this._layoutItems(); }
    }

    _layoutItems() {
        const root = this.viewport || this.root;
        if (!root) { return; }
        const cell = measureCells();
        let width = root.clientWidth ? root.clientWidth / cell.width : this.size.x;
        if (this.hScrollBar) {
            if (this._itemTextWidth?.cellWidth !== cell.width) {
                const range = document.createRange();
                let pixels = 0;
                for (const input of this.choiceElements) {
                    const label = input.parentElement.querySelector(".tv-choice-label");
                    if (!label) { continue; }
                    range.selectNodeContents(label);
                    const labelWidth = range.getBoundingClientRect().width;
                    range.selectNodeContents(input.parentElement.querySelector(`.${this.markClass}`));
                    pixels = Math.max(pixels, labelWidth + range.getBoundingClientRect().width + cell.width);
                }
                this._itemTextWidth = root.clientWidth ? { cellWidth: cell.width, width: Math.ceil(pixels / cell.width) } : null;
            }
            width = Math.max(width, this._itemTextWidth?.width || 0);
        }
        this.choiceElements.forEach((input, index) => {
            this._placePart(input.parentElement, new TVRect(0, index, width, index + 1));
            if (this.type === "button") { this._placePart(input, new TVRect(0, 0, width, 1)); }
        });
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this.updateScrollbar();
        return this;
    }

    destroy() { this.bindRoot(null); this.choiceElements = []; }

    _focusTarget() { return this._choiceEnabled(this.sel) ? this.choiceElements[this.sel] : null; }

    _canFocus() { return super._canFocus() && this.strings.some((_item, index) => this._choiceEnabled(index)); }

    focus() {
        const input = this.choiceElements[this.sel];
        if (viewAcceptsInput(this) && this._choiceEnabled(this.sel) && input && !input.disabled) {
            input.focus({ preventScroll: true });
            if (document.activeElement === input) { this._recordFocus(input); }
            else { this.setState(sfFocused, false); }
        }
        return this;
    }

    buttonState(item) {
        return Number.isInteger(item) && item >= 0 && item < this.strings.length
            && Boolean(this.enableMask & this.bit(item));
    }

    mark(item) {
        if (!Number.isInteger(item) || item < 0 || item >= this.strings.length) { return false; }
        return this.type === "radio" ? this.value === item : Boolean(this.value & this.bit(item));
    }

    multiMark(item) { return Number(this.mark(item)); }

    movedTo(item) {
        if (Number.isInteger(item) && item >= 0 && item < this.strings.length
            && this._choiceEnabled(item)) {
            const changed = this.sel !== item;
            this.sel = item;
            this.choiceElements.forEach((input, index) => { input.tabIndex = index === item && !input.disabled ? 0 : -1; });
            if (changed) {
                this.dispatchEvent(new TVEvent(evBroadcast, { command: "cluster-moved-to", infoPtr: this, infoLong: item }));
            }
        }
    }

    press(item) {
        if (!viewAcceptsInput(this) || !this._choiceEnabled(item)) { return; }
        this.movedTo(item);
        if (this.type === "radio") { this.value = item; }
        else { this.value ^= this.bit(item); }
        this.syncInputs();
    }

    setButtonState(mask, enable) {
        if (this.strings.length > 31) { mask = BigInt(mask); }
        this.enableMask = enable ? (this.enableMask | mask) : (this.enableMask & ~mask);
        this.syncInputs();
    }

    getData() { return this.value; }

    destroy() { this.bindRoot(null); }

    setData(value) {
        const focused = this.type === "radio" && this.choiceElements.includes(document.activeElement);
        this.value = this.type !== "radio" && this.strings.length > 31
            ? (BigInt(value || 0) < 0n ? 0n : BigInt(value || 0)) : Math.max(0, Number(value) || 0);
        if (this.type === "radio" && Number.isInteger(this.value) && this.value < this.strings.length) { this.sel = this.value; }
        this.syncInputs();
        if (focused) { this.focus(); }
        return this;
    }

    syncInputs() {
        const previous = this.sel, focused = this.choiceElements.includes(document.activeElement);
        if (!this._choiceEnabled(this.sel)) {
            const enabled = this.strings.findIndex((_option, index) => this._choiceEnabled(index));
            if (enabled >= 0) { this.sel = enabled; }
        }
        this.strings.forEach((option, index) => {
            if (this.type !== "button") { option.checked = this.mark(index); }
            const input = this.choiceElements[index];
            if (!input) { return; }
            input.disabled = !this._choiceEnabled(index);
            input.tabIndex = index === this.sel && !input.disabled ? 0 : -1;
            input.parentElement?.classList.toggle("is-disabled", input.disabled);
            const mark = this.type === "button" ? input.querySelector(`.${this.markClass}`) : input.nextElementSibling;
            let text;
            if (this.type === "button") {
                const state = this.multiMark(index);
                input.setAttribute("aria-checked", state === 0 ? "false" : state === 1 ? "true" : "mixed");
                text = `[${this.states[state]}]`;
            } else { input.checked = option.checked; text = this._markText(index); }
            if (mark && mark.textContent !== text) { mark.textContent = text; }
        });
        this._drawPalette();
        if (focused && previous !== this.sel) { this.focus(); }
    }

    resolve(root) {
        super.resolve(root);
        this.choiceElements = Array.from(this.root?.querySelectorAll(
            this.type === "button" ? ".tv-multicheck-button" : ".tv-choice-input",
        ) || []);
        this._itemTextWidth = null;
        this.choiceElements.forEach((element, index) => { element._tvChoiceIndex = index; });
        this.syncInputs();
        this.movedTo(this.sel);
        this.updateScrollbar();
        return this;
    }

    handleEvent(event) {
        const native = event.nativeEvent;
        if (!viewAcceptsInput(this) && this.root?.contains(native?.target)) {
            if (event.what === evBroadcast && native.type === "change") {
                this.syncInputs(); this.clearEvent(event);
            } else if (event.what === evMouseDown || (event.what === evKeyDown && !native.altKey && !native.ctrlKey && !native.metaKey
                && ["Enter", " ", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"].includes(native.key))) {
                native.preventDefault(); this.clearEvent(event);
            }
            return;
        }
        if (event.what === evKeyDown && this.type !== "radio") {
            const native = event.nativeEvent;
            const index = native?.target?._tvChoiceIndex;
            if (!Number.isInteger(index) || !this.root?.contains(native.target)
                || !this._choiceEnabled(index) || native.target.disabled || native.altKey || native.ctrlKey || native.metaKey) { return; }
            if (native.key === " " || native.key === "Enter") {
                native.preventDefault();
                this.press(index);
                event.what = evBroadcast;
                event.command = "cluster-press";
                event.infoPtr = this;
                event.infoLong = index;
                return;
            }
            const page = Math.max(1, Math.floor((this.viewport?.clientHeight || 0) / measureCells().height));
            const destinations = { ArrowDown: index + 1, ArrowRight: index + 1, ArrowUp: index - 1,
                ArrowLeft: index - 1, Home: 0, End: this.strings.length - 1,
                PageDown: index + page, PageUp: index - page };
            if (!(native.key in destinations)) { return; }
            native.preventDefault();
            let next = Math.max(0, Math.min(this.strings.length - 1, destinations[native.key]));
            const step = native.key === "Home" ? 1 : native.key === "End" ? -1 : next < index ? -1 : 1;
            while (next >= 0 && next < this.strings.length && !this._choiceEnabled(next)) { next += step; }
            if (next >= 0 && next < this.strings.length) {
                this.movedTo(next);
                this.focus();
                const input = this.choiceElements[next];
                if (this.viewport && input) {
                    const row = input.parentElement.getBoundingClientRect(), viewport = this.viewport.getBoundingClientRect();
                    if (row.top < viewport.top) { this.viewport.scrollTop -= viewport.top - row.top; }
                    else if (row.bottom > viewport.bottom) { this.viewport.scrollTop += row.bottom - viewport.bottom; }
                    this.updateScrollbar();
                }
            }
            this.clearEvent(event);
            return;
        }
        if (event.what !== evBroadcast || event.nativeEvent?.type !== "change") { return; }
        const input = event.nativeEvent.target;
        if (!this.root?.contains(input) || !input.matches?.(".tv-choice-input")) { return; }
        const index = input._tvChoiceIndex;
        if (!Number.isInteger(index)) { return; }
        if (!this._choiceEnabled(index)) {
            this.syncInputs();
            this.clearEvent(event);
            return;
        }
        this.movedTo(index);
        if (this.type === "radio") { this.value = index; }
        else if (input.checked) { this.value |= this.bit(index); }
        else { this.value &= ~this.bit(index); }
        this.syncInputs();
        event.infoLong = index;
        event.command = "cluster-press";
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
        this.value = this._initialValue();
        this.sel = this.value;
        this.viewId = `tv-radio-${++tvChoiceGroupId}`;
        this.itemClass = "tv-radio-item";
        this.markClass = "tv-radio-mark";
    }
}

const cfOneBit = 0x0101;
const cfTwoBits = 0x0203;
const cfFourBits = 0x040f;
const cfEightBits = 0x08ff;

class TVMultiCheckBoxes extends TVCluster {
    constructor(bounds, options = [], selRange = 3, flags = cfTwoBits, states = " X?") {
        super(bounds, options);
        if (!Number.isInteger(selRange) || typeof states !== "string") {
            throw new TypeError("TVMultiCheckBoxes expects a state count and marker string");
        }
        if (![cfOneBit, cfTwoBits, cfFourBits, cfEightBits].includes(flags)
            || selRange < 1 || selRange > Math.min(255, (flags & 0xff) + 1)
            || Array.from(states).length < selRange) {
            throw new RangeError("Invalid multi-check state range, flags or markers");
        }
        this.type = "button";
        this.itemClass = "tv-multicheck-item";
        this.markClass = "tv-multicheck-mark";
        this.selRange = selRange;
        this.flags = flags;
        this.states = Array.from(states);
        this.setItems(options);
    }

    _dataValue(value, count = this.strings.length) {
        if (typeof value !== "bigint" && (typeof value !== "number" || !Number.isSafeInteger(value))) {
            throw new TypeError("Multi-check data must be an integer or BigInt");
        }
        const packed = BigInt(value), width = this.flags >> 8, bits = Math.max(32, count * width);
        if (packed < 0n || packed >= (1n << BigInt(bits))) { throw new RangeError("Multi-check data exceeds its record"); }
        for (let index = 0; index < count; index++) {
            if (Number((packed >> BigInt(index * width)) & BigInt(this.flags & 0xff)) >= this.selRange) {
                throw new RangeError("Multi-check data contains an unavailable state");
            }
        }
        return bits > 32 ? packed : Number(packed);
    }

    _initialValue(options = this.strings) {
        // TCluster initializes before the subclass's packing fields are set.
        if (this.flags === undefined) { return options.length > 31 ? 0n : 0; }
        let value = 0n;
        options.forEach((option, index) => {
            const state = option.state ?? 0;
            if (!Number.isInteger(state) || state < 0 || state >= this.selRange) {
                throw new RangeError("Invalid initial multi-check state");
            }
            value |= BigInt(state) << BigInt(index * (this.flags >> 8));
        });
        return this._dataValue(value, options.length);
    }

    setItems(options = []) {
        const items = Array.isArray(options) ? options : [], value = this._initialValue(items);
        this.strings = items.map(({ state, ...option }) => option);
        this.value = value;
        this.sel = 0;
        this.enableMask = this.strings.reduce((mask, _option, index) => mask | this.bit(index), this.strings.length > 31 ? 0n : 0);
        if (this.viewport) { this.viewport.scrollLeft = 0; this.viewport.scrollTop = 0; }
        this.drawView();
        return this;
    }

    setData(value) {
        this.value = this._dataValue(value);
        this.syncInputs();
        return this;
    }

    multiMark(item) {
        if (!Number.isInteger(item) || item < 0 || item >= this.strings.length) { return 0; }
        return Number((BigInt(this.value) >> BigInt(item * (this.flags >> 8))) & BigInt(this.flags & 0xff));
    }

    mark(item) { return this.multiMark(item) !== 0; }

    _itemMarkup(option, index) {
        const state = this.multiMark(index);
        const ariaChecked = state === 0 ? "false" : (state === 1 ? "true" : "mixed");
        const disabled = !this._choiceEnabled(index);
        const attrs = attrsToString({
            type: "button",
            class: "tv-flat-button tv-multicheck-button",
            disabled,
            role: "checkbox",
            "aria-checked": ariaChecked,
        });
        const className = `${this.itemClass}${disabled ? " is-disabled" : ""}`;
        return `<label class="${className}"><button ${attrs}><span class="${this.markClass}" aria-hidden="true">[${escapeHtml(this.states[state])}]</span> <span class="tv-choice-label">${renderHotkeyMarkup(option.label || "")}</span></button></label>`;
    }

    cycle(index, button = null) {
        if (!Number.isInteger(index) || index < 0 || index >= this.strings.length) { return; }
        if (!viewAcceptsInput(this) || !this._choiceEnabled(index)) { return; }
        const target = button || this.choiceElements[index];
        if (target?.disabled) { return; }
        this.movedTo(index);
        const state = (this.multiMark(index) + 1) % this.selRange;
        const shift = BigInt(index * (this.flags >> 8)), mask = BigInt(this.flags & 0xff) << shift;
        this.value = this._dataValue((BigInt(this.value) & ~mask) | (BigInt(state) << shift));
        this.syncInputs();
        this._itemTextWidth = null;
        this.updateScrollbar();
        return state;
    }

    press(item) { return this.cycle(item); }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evMouseDown || event.nativeEvent?.type !== "click") { return; }
        const button = event.nativeEvent.target.closest?.(".tv-multicheck-button");
        if (!button || button.disabled || !this.root?.contains(button)) { return; }
        const index = button._tvChoiceIndex;
        const state = this.cycle(index, button);
        if (!Number.isInteger(state)) { return; }
        this.clearEvent(event);
        this.owner?.dispatchEvent(new TVEvent(evBroadcast, {
            command: "cluster-press",
            infoPtr: this,
            infoLong: index,
            nativeEvent: event.nativeEvent,
        }));
    }
}

const bfNormal = 0x00;
const bfDefault = 0x01;
const bfLeftJust = 0x02;
const bfBroadcast = 0x04;
const cmGrabDefault = 61;
const cmReleaseDefault = 62;

class TVButton extends TVView {
    constructor(bounds, title, command, flags = bfNormal) {
        if (!(bounds instanceof TVRect)) {
            throw new TypeError("TVButton expects TVRect bounds");
        }
        super(bounds);
        this.options |= ofSelectable;
        this.title = String(title ?? "");
        this.command = command ?? "";
        this.commandData = {};
        this.value = true;
        this.flags = flags;
        this.amDefault = (flags & bfDefault) !== 0;
        this.eventMask |= evBroadcast;
        this._localDisabled = false;
        this.disabled = !this.commandEnabled(this.command);
        if (this.disabled) { this.state |= sfDisabled; }
        this._nativeHovered = false;
        this._nativeFocused = false;
        this._onButtonPaint = Object.fromEntries(["mouseenter", "mouseleave", "focus", "blur"].map(type => [type, () => {
            if (type === "mouseenter" || type === "mouseleave") { this._nativeHovered = type === "mouseenter"; }
            else {
                this._nativeFocused = type === "focus";
                this.setState(sfFocused, this._nativeFocused);
            }
            this._drawPalette();
        }]));
        this.onButtonClick = nativeEvent => {
            if (!this.disabled && !this.root?.disabled) {
                this.dispatchEvent(new TVEvent(evMouseDown, { infoPtr: this, nativeEvent }));
            }
        };
    }

    getPalette() {
        return this._drawParts().dialog ? [41, 42, 43, 44, 45, 46].map(index => this._appColor(index)) : super.getPalette();
    }

    _drawPalette() {
        if (!this.root) { return this; }
        if (!this._drawParts().dialog) { return super._drawPalette(); }
        const parts = this._buttonElements;
        if (!parts?.face) { return this; }
        const selected = this._nativeFocused || document.activeElement === this.root || this.root.classList.contains("is-pressed");
        const color = this.getColor(this.disabled ? 4 : selected ? 3 : this.amDefault ? 2 : 1);
        this._paintPaletteText(parts.face, color, this.disabled ? color : this.getColor(5));
        for (const part of [parts.inset, parts.edge, parts.shadow]) { this._paintPalette(part, this.getColor(6)); }
        return this;
    }

    setCommandData(commandData = {}) {
        this.commandData = { ...commandData };
        if (typeof this.commandData.expanded === "boolean") {
            this.root?.setAttribute("aria-expanded", String(this.commandData.expanded));
        } else { this.root?.removeAttribute("aria-expanded"); }
        return this;
    }

    setValue(value) {
        this.value = value;
        return this;
    }

    _shadowText() {
        const width = Math.max(0, Math.ceil(this.size.x));
        if (this.size.y < 2) { return " ".repeat(width); }
        return " ".repeat(Math.min(2, width)) + "\u2580".repeat(Math.max(0, width - 2));
    }

    _edgeText() {
        const rows = Math.max(0, Math.ceil(this.size.y) - 1);
        return rows ? "▄" + "\n█".repeat(rows - 1) : "";
    }

    _titleMarkup(markup) {
        const length = Array.from(this.title.replaceAll("~", "")).length;
        const left = (this.flags & bfLeftJust) !== 0 ? 1 : Math.max(1, Math.trunc((this.size.x - length - 2) / 2));
        const top = Math.max(0, Math.floor(this.size.y / 2) - 1);
        return "\n".repeat(top) + " ".repeat(left) + markup;
    }

    bindRoot(root) {
        if (root === this.root) { return this; }
        if (this.root) { this.makeDefault(false); super.setState(sfFocused, false); }
        this._releasePress?.();
        this.root?.removeEventListener("click", this.onButtonClick);
        for (const [type, handler] of Object.entries(this._onButtonPaint)) { this.root?.removeEventListener(type, handler); }
        this._nativeHovered = false; this._nativeFocused = false;
        super.bindRoot(root);
        watchCommands(this, Boolean(root));
        this.root?.addEventListener("click", this.onButtonClick);
        for (const [type, handler] of Object.entries(this._onButtonPaint)) { this.root?.addEventListener(type, handler); }
        this._buttonElements = Object.fromEntries(["face", "inset", "label", "edge", "shadow"]
            .map(name => [name, this._query(`.tv-dialog-button-${name}`)]));
        this._captionMarkup = null;
        this._buttonClasses = new Set(this._drawParts().className.split(/\s+/).filter(Boolean));
        this._buttonAttrNames = [];
        if (this._buttonElements.face) { this.drawView(); }
        this._syncCommandState();
        return this;
    }

    _drawBounds() {
        super._drawBounds();
        if (this._buttonElements?.face) { this.drawView(); }
    }

    _layout() {
        const parts = this._buttonElements;
        if (!parts?.face) { return; }
        const width = this.size.x, height = this.size.y, faceHeight = Math.max(0, height - 1);
        const pressed = this.root.classList.contains("is-pressed"), inset = Math.min(1, width);
        this._placePart(parts.face, new TVRect(pressed ? 1 : 0, 0, width + (pressed ? 1 : 0), faceHeight));
        this._placePart(parts.inset, new TVRect(0, 0, inset, faceHeight));
        this._placePart(parts.label, new TVRect(inset, 0, Math.max(inset, width - 1), faceHeight));
        this._placePart(parts.edge, new TVRect(Math.max(0, width - 1), 0, width, faceHeight));
        this._placePart(parts.shadow, new TVRect(0, faceHeight, width, height));
        parts.edge.style.visibility = parts.shadow.style.visibility = pressed ? "hidden" : "";
    }

    drawView() {
        if (!this.root) { return this; }
        const parts = this._drawParts(), attrs = this._drawButtonAttrs(parts);
        for (const name of this._buttonAttrNames) {
            if (!Object.hasOwn(attrs, name)) { this.root.removeAttribute(name); }
        }
        for (const [name, value] of Object.entries(attrs)) {
            if (value == null || value === false) { this.root.removeAttribute(name); }
            else if (this.root.getAttribute(name) !== String(value === true ? "" : value)) {
                this.root.setAttribute(name, value === true ? "" : String(value));
            }
        }
        this._buttonAttrNames = Object.keys(attrs);
        const classes = new Set(parts.className.split(/\s+/).filter(Boolean));
        for (const name of this._buttonClasses) { if (!classes.has(name)) { this.root.classList.remove(name); } }
        for (const name of classes) { this.root.classList.add(name); }
        this._buttonClasses = classes;
        this.root.classList.toggle("is-default", this.amDefault);
        const elements = this._buttonElements, label = elements?.label || this.root;
        const markup = parts.dialog ? this._titleMarkup(parts.labelMarkup) : parts.labelMarkup;
        if (this._captionMarkup !== markup) {
            if (label.innerHTML !== markup) { label.innerHTML = markup; }
            this._captionMarkup = markup;
        }
        this._drawPalette();
        if (!elements?.face) { return this; }
        for (const [element, text] of [[elements.edge, this._edgeText()], [elements.shadow, this._shadowText()]]) {
            if (element.textContent !== text) { element.textContent = text; }
        }
        this._layout();
        return this;
    }

    destroy() { this.bindRoot(null); }

    _drawParts() {
        return {
            dialog: true,
            baseClass: "tv-dialog-button",
            className: "",
            style: "",
            labelMarkup: renderHotkeyMarkup(this.title),
            ariaLabel: "",
            ariaExpanded: typeof this.commandData.expanded === "boolean" ? this.commandData.expanded : null,
            ariaPressed: null,
            tabIndex: null,
            tooltip: "",
        };
    }

    _drawButtonAttrs(parts) {
        return this._drawAttrs({
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
        });
    }

    draw() {
        const parts = this._drawParts();
        const attrString = attrsToString(this._drawButtonAttrs(parts));
        const classNames = [parts.className, this.amDefault ? "is-default" : ""].filter(Boolean).join(" ");
        const bounds = TVView._viewBoundsStyle(this);
        const inlineStyle = [bounds, parts.style].filter(Boolean).join(";");
        const styleAttr = inlineStyle ? ` style="${escapeHtml(inlineStyle)}"` : "";
        const labelMarkup = parts.labelMarkup;
        if (parts.dialog) {
            const buttonClass = [parts.baseClass, classNames].filter(Boolean).join(" ");
            const shadow = this._shadowText();
            return `
                <button class="${buttonClass}"${styleAttr} ${attrString}>
                    <span class="tv-dialog-button-face">
                        <span class="tv-dialog-button-inset" aria-hidden="true"> </span>
                        <span class="tv-dialog-button-label">${this._titleMarkup(labelMarkup)}</span>
                        <span class="tv-dialog-button-edge" aria-hidden="true">${this._edgeText()}</span>
                    </span>
                    <span class="tv-dialog-button-shadow" aria-hidden="true">${shadow}</span>
                </button>
            `;
        }
        const classAttr = ` class="${escapeHtml(["tv-flat-button", classNames].filter(Boolean).join(" "))}"`;
        const attrs = attrString ? ` ${attrString}` : "";
        return `<button${classAttr}${styleAttr}${attrs}>${labelMarkup}</button>`;
    }

    handleEvent(event) {
        if (event.what === evBroadcast && event.command === cmCommandSetChanged) {
            this._syncCommandState();
            return;
        }
        if (event.what === evBroadcast && [cmGrabDefault, cmReleaseDefault].includes(event.command)) {
            if ((this.flags & bfDefault) !== 0) {
                const group = this._defaultGroup();
                this.amDefault = event.infoPtr instanceof TVButton
                    ? !group?.firstThat(view => view instanceof TVButton && view._defaultGroup() === group
                        && (view.flags & bfDefault) === 0 && view.amDefault && viewAcceptsInput(view))
                    : event.command === cmReleaseDefault;
                this.root?.classList.toggle("is-default", this.amDefault);
                this._drawPalette();
            }
            return;
        }
        const native = event.nativeEvent;
        if (native?.defaultPrevented) { return; }
        if (!viewAcceptsInput(this) || !this.commandEnabled(this.command)) {
            if (event.what === evMouseDown && event.infoPtr === this) {
                native?.preventDefault(); this.clearEvent(event);
            }
            return;
        }
        if (event.what === evMouseDown && this.command && !this.disabled) {
            if ((this.flags & bfBroadcast) !== 0) {
                if (this.press(native)) { native?.preventDefault(); this.clearEvent(event); }
            } else {
                event.what = evCommand;
                event.command = this.command;
                event.infoPtr = this;
            }
        } else if (event.what === evKeyDown && native?.altKey && !native.ctrlKey && !native.metaKey
            && this.title.match(/~([^~])~/)?.[1]?.toLowerCase() === native.key?.toLowerCase()
            && this.press(native)) {
            native.preventDefault();
            this.clearEvent(event);
        }
    }

    setTitle(title) {
        this.title = String(title ?? "");
        if (this._buttonElements?.face) { this.drawView(); }
        else if (this.root) { this.root.innerHTML = this._drawParts().labelMarkup; }
        return this;
    }

    _defaultGroup() {
        let group = null;
        for (let owner = this.owner; owner instanceof TVGroup && !(owner instanceof TVDesktop || owner instanceof TVProgram); owner = owner.owner) {
            group = owner;
            if (owner instanceof TVWindow) { break; }
        }
        return group;
    }

    makeDefault(enable = true) {
        if ((this.flags & bfDefault) !== 0 || this.amDefault === Boolean(enable)) { return this; }
        if (enable && !viewAcceptsInput(this)) { return this; }
        this.amDefault = Boolean(enable);
        this._defaultGroup()?.broadcast(enable ? cmGrabDefault : cmReleaseDefault, this);
        this.root?.classList.toggle("is-default", this.amDefault);
        this._drawPalette();
        return this;
    }

    drawState(down) {
        this.root?.classList.toggle("is-pressed", Boolean(down));
        this._layout();
        this._drawPalette();
        return this;
    }

    press(nativeEvent = null) {
        if (!this.command || this.disabled || !this.commandEnabled(this.command) || !viewAcceptsInput(this)) { return false; }
        const event = new TVEvent((this.flags & bfBroadcast) !== 0 ? evBroadcast : evCommand, {
            command: this.command,
            infoPtr: this,
            nativeEvent,
        });
        if (event.what === evBroadcast) {
            if (!(this.owner instanceof TVGroup)) { return false; }
            this.owner._broadcastEvent(event);
        } else { this.dispatchEvent(event); }
        return true;
    }

    _syncCommandState() {
        this.disabled = this._localDisabled || !this.commandEnabled(this.command);
        super.setState(sfDisabled, this.disabled);
        if (this.root) { this.root.disabled = this.disabled; }
        if (this.disabled) {
            this._releasePress?.(); this.drawState(false);
            super.setState(sfFocused, false); this.makeDefault(false);
        } else if (this.root && document.activeElement === this.root) { this.makeDefault(true); }
        this._drawPalette();
    }

    setState(state, enable) {
        if ((state & sfDisabled) !== 0) { this._localDisabled = Boolean(enable); }
        super.setState(state & ~sfDisabled, enable);
        this._syncCommandState();
        if ((state & sfFocused) !== 0) {
            this.makeDefault(enable && viewAcceptsInput(this) && (!this.root || document.activeElement === this.root));
        }
        if ((state & (sfDisabled | sfVisible)) !== 0) {
            if (!viewAcceptsInput(this)) {
                super.setState(sfFocused, false);
                this.makeDefault(false);
            } else if (this.root && document.activeElement === this.root) { this.makeDefault(true); }
        }
        this._drawPalette();
        return this;
    }
}

class TVFrame extends TVView {
    constructor(bounds) {
        super(bounds);
        this.frameMode = 0;
        this.titleCommands = new WeakMap();
        this._bodySections = [];
        this._bodyBorders = true;
    }

    bindRoot(root) {
        if (this.root?._tvFrame === this) { delete this.root._tvFrame; }
        // The frame paints the owner's window; it must not replace its TVView.
        this.root = root || null;
        if (this.root) { this.root._tvFrame = this; bindCloseButtons(this.root); }
        return this;
    }

    drawView() {
        if (this.root) { fillBorders(this.root); }
        return this;
    }

    _layout(cell = measureCells()) {
        if (!this.root) { return; }
        const width = this.root.clientWidth ? this.root.clientWidth / cell.width : this.size.x;
        const height = this.root.clientHeight ? this.root.clientHeight / cell.height : this.size.y;
        if (width < 2 || height < 2) { return; }
        const place = (element, x, y, w, h) => this._placePart(element, new TVRect(x, y, x + Math.max(0, w), y + Math.max(0, h)));
        if (this.root.classList.contains("tv-dialog-window")) { this._layoutDialog(width, height, place); }
        else { this._layoutWindow(width, height, place); }
    }

    _layoutWindow(width, height, place) {
        const shell = this.root.firstElementChild;
        const [titlebar, body] = shell?.children || [];
        const [left, client, right, bottom] = body?.children || [];
        if (!titlebar || !left || !client || !right || !bottom) { return; }
        place(shell, 0, 0, width, height);
        place(titlebar, 0, 0, width, 1);
        place(body, 0, 1, width, height - 1);
        place(left, 0, 0, 1, height - 2);
        place(client, 1, 0, width - 2, height - 2);
        place(right, width - 1, 0, 1, height - 2);
        place(bottom, 0, height - 2, width, 1);
        const scrollShell = client.firstElementChild;
        place(scrollShell, 0, 0, width - 2, height - 2);
        place(scrollShell?.firstElementChild, 0, 0, width - 2, height - 2);

        const [tl, gap, close, before, caption, after, zoom, lastGap, tr] = titlebar.children;
        const titleLength = caption?.classList.contains("tv-window-caption") ? Array.from(caption.textContent).length : 0;
        const titleWidth = titleLength ? Math.min(titleLength + 2, Math.max(0, width - 12)) : 0;
        const titleLeft = Math.floor((width - titleWidth) / 2);
        if (caption) { caption.hidden = !titleLength; }
        place(tl, 0, 0, 1, 1);
        place(gap, 1, 0, 1, 1);
        place(close, 2, 0, 3, 1);
        place(before, 5, 0, titleLeft - 5, 1);
        place(caption, titleLeft, 0, titleWidth, 1);
        this._layoutTitle(caption, titleWidth, place);
        place(after, titleLeft + titleWidth, 0, width - 5 - titleLeft - titleWidth, 1);
        place(zoom, width - 5, 0, 3, 1);
        place(zoom?.querySelector(".tv-frame-passive"), 0, 0, 3, 1);
        place(lastGap, width - 2, 0, 1, 1);
        place(tr, width - 1, 0, 1, 1);

        const parts = Array.from(bottom.children);
        const growable = (this.owner.flags & wfGrow) !== 0;
        const fill = parts.find((part) => part.classList.contains("tv-scrollbar-x")
            || (part.classList.contains("tv-border-fill") && !part.classList.contains("tv-control-gap")));
        const widths = parts.map((part, index) => index === 0 ? 1
            : index === parts.length - 1 ? (growable ? 2 : 1)
                : part === fill ? 0 : part._tvView?.size.x || 1);
        let column = 0;
        const spare = Math.max(0, width - widths.reduce((sum, value) => sum + value, 0));
        parts.forEach((part, index) => {
            const columns = part === fill ? spare : widths[index];
            place(part, column, 0, columns, 1);
            column += columns;
        });
    }

    _layoutDialog(width, height, place) {
        const [titlebar, body, footer] = this.root.children || [];
        if (!titlebar || !body || !footer) { return; }
        place(titlebar, 0, 0, width, 1);
        place(body, 0, 1, width, height - 2);
        place(footer, 0, height - 1, width, 1);
        const frameRow = (row) => {
            const [left, fill, right] = row.children;
            place(left, 0, 0, 1, 1);
            place(fill, 1, 0, width - 2, 1);
            place(right, width - 1, 0, 1, 1);
        };
        frameRow(titlebar); frameRow(footer);
        let rightControls = 0, close = false;
        for (const control of titlebar.children) {
            const command = this.titleCommand(control);
            if (!command || control.hidden) { continue; }
            if (command === "dialog-close") { place(control, 2, 0, 3, 1); close = true; }
            else { place(control, width - 5 - rightControls * 4, 0, 3, 1); rightControls += 1; }
        }
        const title = Array.from(titlebar.children).find((element) => element.classList.contains("tv-dialog-title-text"));
        if (title) {
            const margin = close || rightControls ? Math.max(6, 2 + rightControls * 4) : 2;
            const titleWidth = Math.min(this.getTitleWidth() + 2, Math.max(0, width - 2 * margin));
            place(title, Math.floor((width - titleWidth) / 2), 0, titleWidth, 1);
            this._layoutTitle(title, titleWidth, place);
            title.hidden = !this.getTitleWidth();
        }
        if (!this._bodyBorders) { return; }
        const parts = Array.from(body.children);
        const clients = parts.filter((element) => element.classList.contains("tv-dialog-client"));
        const heights = clients.map((_element, index) => clients.length > 1
            ? Math.max(1, this._bodySections[index]?.getBounds?.().y2 || 0) : height - 2);
        const used = heights.reduce((sum, value) => sum + value, Math.max(0, clients.length - 1));
        if (heights.length && used < height - 2) { heights[heights.length - 1] += height - 2 - used; }
        let top = 0, section = 0;
        for (let index = 0; index + 2 < parts.length; index += 3) {
            const [left, content, right] = parts.slice(index, index + 3);
            const rows = content.classList.contains("tv-dialog-client") ? heights[section++] : 1;
            place(left, 0, top, 1, rows);
            place(content, 1, top, width - 2, rows);
            place(right, width - 1, top, 1, rows);
            top += rows;
        }
    }

    bindTitleControl(button, command) {
        if (button) { this.titleCommands.set(button, command); }
        return button;
    }

    _layoutTitle(caption, width, place) {
        place(caption?.firstElementChild, 1, 0, Math.max(0, width - 2), 1);
    }

    titleCommand(button) { return button ? this.titleCommands.get(button) || "" : ""; }

    getTitleWidth() {
        return this.owner instanceof TVWindow ? Array.from(this.owner.getTitle()).length : 0;
    }

    getPalette() { return this.owner?.getPalette?.() ?? null; }

    drawTitle() {
        const title = this.owner?.getTitle?.() || "";
        const element = this.owner?.root?.querySelector?.(".tv-dialog-title-text, .tv-window-caption");
        const text = element?.firstElementChild;
        if (text && text.textContent !== title) { text.textContent = title; }
        if (this.owner?.root) { fillBorders(this.owner.root); }
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
        const passive = command === "window-zoom" ? '<span class="tv-frame-passive" aria-hidden="true" hidden>───</span>' : "";
        return `<button class="${definition.classes}" ${attrString}>[<span class="${definition.glyphClass}" ${glyphAttrString}>${escapeHtml(glyph)}</span>]${passive}</button>`;
    }

    createTitleControl(command, glyph, title = "") {
        return this.bindTitleControl(TVView._fromHTML(this.drawTitleControl(command, glyph, title)), command);
    }

    _drawDialogBody(bodyMarkup, bodyBorders = true) {
        this._bodySections = Array.isArray(bodyMarkup) ? bodyMarkup : [bodyMarkup];
        this._bodyBorders = bodyBorders;
        const renderBody = (value) => (
            value instanceof TVView
                ? value.draw()
                : String(value ?? "")
        );
        const client = (value) => `<div class="tv-dialog-client">${renderBody(value)}</div>`;
        const side = '<span class="tv-border-side" data-tv-border-side="║" aria-hidden="true"></span>';
        if (Array.isArray(bodyMarkup)) {
            const sep = '<span class="tv-border-corner" aria-hidden="true">╟</span>'
                + '<span class="tv-border-fill tv-border-separator" data-tv-border-fill="─" aria-hidden="true"></span>'
                + '<span class="tv-border-corner" aria-hidden="true">╢</span>';
            return bodyMarkup.map(section => side + client(section) + side).join(sep);
        }
        return bodyBorders ? side + client(bodyMarkup) + side : renderBody(bodyMarkup);
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
        const viewAttrs = attrsToString(dialog._drawAttrs());
        const bodyContent = this._drawDialogBody(bodyMarkup, bodyBorders);
        return `
            <div class="${overlayClasses}" ${viewAttrs} hidden>
                <div class="${windowClasses}" style="${escapeHtml(dialog?._framePaletteStyle?.("dialog") || "")}" data-tv-palette="${escapeHtml(palette)}" role="dialog" aria-modal="${modal ? "true" : "false"}" aria-label="${escapeHtml(dialog?.title || "")}">
                    <div class="${titlebarClasses}">
                        <span class="tv-border-corner" aria-hidden="true">╔</span>
                        <span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>
                        <span class="tv-border-corner" aria-hidden="true">╗</span>
                        ${this.drawTitleControl("dialog-close", "■", `Close ${dialog?.title || "dialog"}`)}
                        <div class="${titleClasses}"><span class="tv-frame-title">${escapeHtml(dialog?.title || "")}</span></div>
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
        this.palette = new.target.palette || "help";
        this.frame = this.initFrame();
        this.scrollbars = [];
        this.editor = null;
        this.findEditor = null;
        this.closeAction = null;
        this.zoomAction = null;
        this.manager = null;
        this.managerName = "";
        this.onWindowControlClick = (event) => this.dispatchWindowControl(event);
        this.onWindowKeyDown = nativeEvent => {
            if (nativeEvent.key !== "Tab" || nativeEvent.defaultPrevented
                || nativeEvent.altKey || nativeEvent.ctrlKey || nativeEvent.metaKey) { return; }
            const source = TVView._fromElement(nativeEvent.target) || this;
            for (let view = source; view; view = view.owner) {
                if (view === this) { source.dispatchEvent(new TVEvent(evKeyDown, { infoPtr: source, nativeEvent })); return; }
            }
        };
        this.onWindowTitleDoubleClick = (event) => {
            const titlebar = this.root.querySelector(".tv-border-top");
            if ((this.flags & wfZoom) === 0 || event.target.closest?.("button, a")
                || !titlebar || event.target.closest?.(".tv-border-top") !== titlebar) {
                return;
            }
            event.preventDefault();
            this.dispatchEvent(new TVEvent(evCommand, {
                command: "window-zoom", infoPtr: this, nativeEvent: event,
            }));
        };
    }

    bindRoot(root) {
        this.root?.removeEventListener("keydown", this.onWindowKeyDown);
        if (this.root?.matches?.("[data-tv-window]")) {
            this.root.removeEventListener("click", this.onWindowControlClick);
            this.root.removeEventListener("dblclick", this.onWindowTitleDoubleClick);
            this.frame.bindRoot(null);
        }
        if (root?.matches?.("[data-tv-window]") && !this.size.x && !this.size.y) {
            const size = JSON.parse(root.getAttribute("data-tv-window") || "null");
            if (Array.isArray(size) && size.length === 4 && size.every(value => Number.isSafeInteger(value) && value > 0)) {
                this.setBounds(new TVRect(0, 0, size[0], size[1]));
                this.minSize = new TVPoint(size[2], size[3]);
            }
        }
        super.bindRoot(root);
        this.root?.addEventListener("keydown", this.onWindowKeyDown);
        if (this.root?.matches?.("[data-tv-window]")) {
            this.root.tabIndex = -1;
            const defaults = new Map(this._framePaletteStyle().split(";").filter(Boolean).map(declaration => {
                const colon = declaration.indexOf(":");
                return [declaration.slice(0, colon), declaration.slice(colon + 1)];
            }));
            for (const [name, value] of defaults) {
                if (!this.root.style.getPropertyValue(name)) { this.root.style.setProperty(name, value); }
            }
            this.closeControl = this.root.querySelector(".tv-close-control");
            this.zoomControl = this.root.querySelector(".tv-zoom-control");
            this.frame.bindTitleControl(this.closeControl, "window-close");
            this.frame.bindTitleControl(this.zoomControl, "window-zoom");
            this.frame.bindRoot(this.root);
            this.root.addEventListener("click", this.onWindowControlClick);
            this.root.addEventListener("dblclick", this.onWindowTitleDoubleClick);
            this._drawBounds();
        } else {
            this.closeControl = null;
            this.zoomControl = null;
        }
        return this;
    }

    dispatchWindowControl(nativeEvent) {
        const control = nativeEvent.target?.closest?.("button, a");
        const command = (control === this.closeControl || control === this.zoomControl)
            ? this.frame.titleCommand(control) : "";
        if (!command) { return; }
        nativeEvent.preventDefault();
        nativeEvent.stopPropagation();
        this.dispatchEvent(new TVEvent(evCommand, { command, infoPtr: this, nativeEvent }));
    }

    handleEvent(event) {
        super.handleEvent(event);
        const native = event.nativeEvent;
        if (event.what === evKeyDown && native?.key === "Tab" && native.type !== "keyup"
            && !native.defaultPrevented && !native.altKey && !native.ctrlKey && !native.metaKey
            && viewAcceptsInput(this) && (!this.manager || this.getState(sfActive))
            && (!(this instanceof TVDialog) || this.keyboard)
            && !TVView._fromElement(native.target)?.capturesKey?.(native)) {
            native.preventDefault(); native.stopPropagation();
            if (!this.focusNext(!native.shiftKey)) { this.focus(); }
            this.clearEvent(event);
            return;
        }
        if (event.what !== evCommand) { return; }
        if (event.command === "window-close") {
            if ((this.flags & wfClose) !== 0) {
                if (typeof this.closeAction === "function") { this.closeAction(); }
                else { this.close(); }
            }
            this.clearEvent(event);
        } else if (event.command === "window-zoom") {
            if (typeof this.zoomAction === "function") { this.zoomAction(); }
            else { this.zoom(); }
            this.clearEvent(event);
        } else if (event.command === TV_COMMANDS.DEFAULT_SIZE && (this.flags & wfGrow) !== 0) {
            this.restoreSize();
            this.clearEvent(event);
        }
    }

    initFrame() {
        const frame = new TVFrame(this.getExtent());
        frame.owner = this;
        return frame;
    }

    _focusTarget() { return this.dialog || this.root; }

    getTitle(maxSize = Number.MAX_SAFE_INTEGER) {
        return Array.from(this.title).slice(0, Math.max(0, Number(maxSize) || 0)).join("");
    }

    getPalette() { return this.palette; }

    _framePaletteStyle(fallback = "help") {
        const indexes = WINDOW_PALETTE_INDEXES[this.getPalette()] || WINDOW_PALETTE_INDEXES[fallback];
        const names = ["frame-passive", "frame-active", "frame-icons", "scroll-page", "scroll-controls", "content"];
        return paletteStyle(Object.fromEntries(names.map((name, index) => [`owner-${name}`, indexes[index]])))
            + (this.getPalette() === "editor" ? `;--tv-owner-content-bg:${dosColor(EDITOR_COLOR_ATTRIBUTE, 4)};--tv-owner-content-fg:${dosColor(EDITOR_COLOR_ATTRIBUTE, 0)}` : "")
            + (this.getPalette() === "dos" ? ";--tv-owner-content-bg:#000000;--tv-owner-content-fg:#aaaaaa"
                + ";--tv-owner-frame-active-bg:#000000;--tv-owner-frame-passive-bg:#000000;--tv-owner-frame-icons-bg:#000000" : "");
    }

    _drawBounds() {
        this.frame?.setBounds(this.getExtent());
        if (!this.root) { return; }
        const cell = measureCells(), desktop = this.root.closest(".tv-desktop")?.getBoundingClientRect();
        const maximized = this.root.classList.contains("is-maximized");
        const width = desktop ? Math.min(this.size.x * cell.width, desktop.width) : this.size.x * cell.width;
        const height = desktop ? Math.min(this.size.y * cell.height, desktop.height) : this.size.y * cell.height;
        const drawing = {
            left: `${maximized ? 0 : this.origin.x * cell.width}px`,
            top: `${maximized ? 0 : this.origin.y * cell.height}px`,
            width: `${maximized && desktop ? desktop.width : width}px`,
            height: `${maximized && desktop ? desktop.height : height}px`,
        };
        const resized = this.root.style.width !== drawing.width || this.root.style.height !== drawing.height;
        for (const [name, value] of Object.entries(drawing)) {
            if (this.root.style[name] !== value) { this.root.style[name] = value; }
        }
        if (resized) { fillBorders(this.root); }
    }

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

    setManager(manager, name) {
        this.manager = manager;
        this.managerName = name;
    }

    setState(state, enable) {
        const visibility = (state & sfVisible) !== 0;
        const wasExposed = visibility && this.exposed();
        super.setState(state, enable);
        if (visibility && wasExposed !== this.exposed()
            && this.manager?.windows.get(this.managerName) === this.root) {
            if (this.exposed()) { this.manager._insertTarget(this.managerName, false); }
            else { this.manager._removeTarget(this.managerName, true); }
        }
        return this;
    }

    close() { this.hide(); }

    zoom() {
        if (this.root?._tvResizer) { this.root._tvResizer.toggle(); }
        else if (this.root) {
            const maximized = this.root.classList.toggle("is-maximized");
            if (maximized) {
                this.zoomRect = this.getBounds();
                const cell = measureCells(), desktop = this.root.closest(".tv-desktop");
                this.locate(desktop ? new TVRect(0, 0, Math.floor(desktop.clientWidth / cell.width), Math.floor(desktop.clientHeight / cell.height)) : this.getBounds());
            } else { this.locate(this.zoomRect.copy()); }
            if (this.zoomControl) { this.zoomControl.querySelector("[data-tv-zoom-glyph]").textContent = maximized ? "↓" : "↑"; }
        }
        return this;
    }

    restoreSize() {
        if ((this.flags & wfGrow) !== 0) { this.root?._tvResizer?.restoreDefaultSize(); }
        return this;
    }

    sizeLimits() {
        return {
            min: this.minSize.copy(),
            max: new TVPoint(Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER),
        };
    }

    hasScrollBars() { return true; }

    draw(contentMarkup = this.renderChildren()) {
        const semanticName = this._semanticName();
        const windowAttrs = attrsToString(this._drawAttrs({
            "data-tv-window": true,
            "data-tv-palette": this.getPalette() || "help",
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
        const titleMarkup = `<div class="tv-window-caption"><span class="tv-frame-title">${escapeHtml(title)}</span></div>`;
        const rightFrame = growable && this.hasScrollBars()
            ? new TVScrollBar(new TVRect(), sbVertical).draw()
            : '<span class="tv-border-side tv-border-side-right" data-tv-border-side="║" aria-hidden="true"></span>';
        const bottomFrame = growable
            ? [
                '<span class="tv-scroll-corner tv-scroll-corner-left" data-tv-frame-corner="bl" aria-hidden="true">╚</span>',
                '<span class="tv-border-fill tv-control-gap" data-tv-border-fill="═" aria-hidden="true"></span>',
                this.hasScrollBars() ? new TVScrollBar(new TVRect(), sbHorizontal).draw()
                    : '<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>',
                '<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>',
            ].join("")
            : [
                '<span class="tv-scroll-corner tv-scroll-corner-left" data-tv-frame-corner="bl" aria-hidden="true">╚</span>',
                '<span class="tv-border-fill tv-fixed-bottom-fill" data-tv-border-fill="═" aria-hidden="true"></span>',
                '<span class="tv-scroll-corner tv-scroll-corner-right" data-tv-frame-corner="br" aria-hidden="true">╝</span>',
            ].join("");
        const style = [
            this.getPalette() ? this._framePaletteStyle() : "",
            TVView._viewBoundsStyle(this),
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
        this.options |= ofCentered;
        const root = TVView._fromHTML(this.frame.drawDialog("", TVDialog.footerMarkup()));
        this.bindRoot(root);
        this.setHelpCtx(hcDialog);
        this.content = null;
        this.overlay = root;
        this.dialog = this._query(".tv-dialog-window");
        setElementHelpContext(this.dialog, this.helpCtx);
        this.titlebar = this._query(".tv-dialog-titlebar");
        this.closeButton = this._query(".tv-dialog-close-control");
        this.frame.bindTitleControl(this.closeButton, "dialog-close");
        this.frame.bindRoot(this.dialog);
        this._drawBounds();
        this.dragState = null;
        this.dragFrame = null;
        this.modal = false;
        this.keyboard = true;
        this.escapeCloses = true;
        this.previousFocus = null;
        this.destroyed = false;
        this.closeAction = () => this.close();
        this.dialog.tabIndex = -1;
        this.dialog.addEventListener("click", (event) => this.dispatchDomEvent(evMouseDown, event));
        this.dialog.addEventListener("contextmenu", (event) => this.dispatchDomEvent(evMouseDown, event));
        this.dialog.addEventListener("input", (event) => this.dispatchDomEvent(evBroadcast, event));
        this.dialog.addEventListener("change", (event) => this.dispatchDomEvent(evBroadcast, event));
        this.dialog.addEventListener("keydown", (event) => {
            this.dispatchDomEvent(evKeyDown, event);
            this.onDialogKeyDown(event);
        });
        this.dialog.addEventListener("keyup", (event) => this.onDialogKeyUp(event));
        this.onViewportResize = () => {
            if (!this.isOpen()) { return; }
            if (this.dragState) { this.onDragEnd(); }
            if ((this.options & ofCentered) !== 0) { this.center(); }
            else {
                this._drawBounds();
                const area = this._visibleArea(), rect = this.dialog.getBoundingClientRect(), cell = measureCells();
                this.moveTo(Math.max(0, Math.min(this.origin.x * cell.width, area.width - rect.width)) / cell.width,
                    Math.max(0, Math.min(this.origin.y * cell.height, area.height - rect.height)) / cell.height);
            }
            fillBorders(this.dialog);
        };
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evMouseDown && event.infoPtr === this) {
            const control = event.nativeEvent?.target?.closest?.("button");
            const command = this.titlebar?.contains(control) ? this.frame.titleCommand(control) : "";
            if (command) {
                event.nativeEvent.preventDefault();
                event.nativeEvent.stopPropagation();
                event.what = evCommand;
                event.command = command;
            }
        }
        if (event.what === evCommand && event.command === "dialog-close") {
            if (this.flags & wfClose) { this.closeAction(); }
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
        const content = this.children.length > 1 ? this.children : this.children[0] || "";
        return this.frame.drawDialog(content, TVDialog.footerMarkup());
    }

    drawContent() {
        const body = this._query(".tv-dialog-body");
        if (!body) { return; }
        if (this.closeButton) { this.closeButton.hidden = (this.flags & wfClose) === 0; }
        body.innerHTML = this.frame._drawDialogBody(this.children.length > 1 ? this.children : this.children[0] || "");
        this.children.forEach((view) => view.resolve?.(body));
        this.frame._layout();
        if (this.isOpen()) {
            updateWindowFrameState(this.dialog, this.isActive(), { dialog: true });
        }
    }

    changeBounds(bounds) {
        if (bounds instanceof TVRect && (bounds.x1 !== this.origin.x || bounds.y1 !== this.origin.y)) {
            this.options &= ~ofCentered;
        }
        super.changeBounds(bounds);
        fillBorders(this.dialog);
        return this;
    }

    setState(state, enable) {
        const wasModal = this.modal;
        super.setState(state & ~sfVisible, enable);
        if ((state & sfModal) !== 0) {
            this.modal = Boolean(enable);
            this.overlay?.classList.toggle("is-modal", this.modal);
            this.dialog?.setAttribute("aria-modal", this.modal ? "true" : "false");
        }
        const visibilityChanged = (state & sfVisible) !== 0
            && (Boolean(enable) !== this.getState(sfVisible) || Boolean(enable) !== this.isOpen());
        if (visibilityChanged) {
            if (this.owner instanceof TVGroup && this.overlay?.isConnected) {
                if (enable) { TVDialog.prototype.open.call(this, false); }
                else { TVDialog.prototype.close.call(this); }
            } else {
                super.setState(sfVisible, enable);
            }
        }
        if (wasModal !== this.modal && !visibilityChanged && this.isOpen()) { this.manager?.onChange?.(); }
        return this;
    }

    setHelpCtx(helpCtx) {
        const previous = this.helpCtx;
        super.setHelpCtx(helpCtx);
        setElementHelpContext(this.dialog, this.helpCtx);
        if (this.manager && previous !== this.helpCtx && this.isOpen() && this.manager.activeTarget === this.managerName) {
            this.manager.onChange?.();
        }
        return this;
    }

    dispatchDomEvent(what, nativeEvent) {
        const target = TVView._fromElement(nativeEvent.target) || this;
        if (target instanceof TVCluster) { return; }
        // A bound control translates its native click before it reaches the
        // dialog, so the same owner chain must not receive it a second time.
        if (nativeEvent.type === "click") {
            for (let control = target; control && control !== this; control = control.owner) {
                if (control instanceof TVButton || (control instanceof TVListViewer
                    && control.boundItemsRoot?.contains(nativeEvent.target))) { return; }
            }
        }
        return target.dispatchEvent(new TVEvent(what, {
            infoPtr: target,
            nativeEvent,
        }));
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

    open(activate = true) {
        if (this.destroyed) {
            return;
        }
        if (!(this.owner instanceof TVGroup) || !this.overlay.isConnected) {
            throw new Error("TVDialog must be inserted into a connected TVGroup before open()");
        }
        // Temporary dialogs (including MessageBox) need the same owner stack,
        // activation and focus rules as dialogs registered by the application.
        if (!this.manager && this.owner instanceof TVDesktop) { this.owner.dialogManager.register(this.viewId, this); }
        const wasOpen = this.isOpen();
        if (!wasOpen) {
            this.previousFocus = document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null;
        }
        super.setState(sfVisible, true);
        this._drawBounds();
        if ((this.options & ofCentered) !== 0) {
            this.center();
        }
        window.addEventListener("resize", this.onViewportResize, { passive: true });
        fillBorders(this.dialog);
        if (this.manager && this.managerName) {
            this.manager.onDialogOpened(this.managerName, activate);
        }
        if (activate && this.isActive() && !this.dialog.contains(document.activeElement)) {
            try {
                this.dialog.focus({ preventScroll: true });
            } catch {
                this.dialog.focus();
            }
        }
    }

    close() {
        const wasActive = this.isActive();
        if (this.dragState) { this.onDragEnd(); }
        const restoreFocus = this.previousFocus, manager = this.manager, name = this.managerName;
        this.previousFocus = null;
        super.setState(sfVisible, false);
        window.removeEventListener("resize", this.onViewportResize);
        if (manager && name) {
            manager._removeTarget(name);
            if (wasActive) { manager._focusTarget(manager.activeTarget, restoreFocus); }
            return;
        }
        if (wasActive && restoreFocus?.isConnected && typeof restoreFocus.focus === "function") {
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
        document.removeEventListener("mousemove", this.onDragMove, true);
        document.removeEventListener("mouseup", this.onDragEnd, true);
        window.removeEventListener("blur", this.onDragEnd);
        if (this.dragFrame !== null) { window.cancelAnimationFrame(this.dragFrame); this.dragFrame = null; }
        this.dragState = null;
        if (this.manager && this.managerName) {
            this.manager.unregister(this.managerName, this);
        }
        this.manager = null;
        this.managerName = "";
        this.owner?.remove?.(this);
        this.previousFocus = null;
        this.destroyed = true;
        window.removeEventListener("resize", this.onViewportResize);
        this.frame.bindRoot(null);
        this.bindRoot(null);
        this.overlay.remove();
    }

    onDialogKeyDown(event) {
        if (!this.keyboard || !this.isActive() || event.defaultPrevented) {
            return;
        }
        if (event.key === "Escape" && this.escapeCloses) {
            event.preventDefault();
            event.stopPropagation();
            this.dispatchEvent(new TVEvent(evCommand, {
                command: "dialog-close", infoPtr: this, nativeEvent: event,
            }));
            return;
        }
        if (
            event.key === "Enter"
            && !event.altKey
            && !event.ctrlKey
            && !event.metaKey
            && !event.shiftKey
            && !(event.target && (event.target.isContentEditable || event.target.closest("button, a, textarea")))
        ) {
            const defaultButton = this.firstThat((view) => (
                view instanceof TVButton
                && view.amDefault
                && view.root?.isConnected
                && !view.disabled
                && viewAcceptsInput(view)
            ));
            if (defaultButton?.root && !defaultButton.root.disabled) {
                event.preventDefault();
                event.stopPropagation();
                defaultButton.press(event);
                return;
            }
        }
        if (this.modal) {
            event.stopPropagation();
        }
    }

    onDialogKeyUp(_event) {}

    _visibleArea() {
        const rect = this.overlay.getBoundingClientRect();
        return {
            width: Math.max(0, Math.min(rect.width, (window.innerWidth || rect.width) - rect.left)),
            height: Math.max(0, Math.min(rect.height, (window.innerHeight || rect.height) - rect.top)),
        };
    }

    center() {
        this._drawBounds();
        const area = this._visibleArea(), rect = this.dialog.getBoundingClientRect(), cell = measureCells();
        const centered = this.options & ofCentered;
        const axes = centered || ofCentered;
        this.moveTo((axes & ofCenterX) !== 0 ? Math.max(0, Math.floor((area.width - rect.width) / 2)) / cell.width : this.origin.x,
            (axes & ofCenterY) !== 0 ? Math.max(0, Math.floor((area.height - rect.height) / 2)) / cell.height : this.origin.y);
        this.options = (this.options & ~ofCentered) | centered;
    }

    moveTo(x, y) {
        this.options &= ~ofCentered;
        return super.moveTo(x, y);
    }

    _drawBounds() {
        this.frame.setBounds(this.getExtent());
        if (!this.dialog) { return; }
        const cell = measureCells(), area = this._visibleArea();
        const width = area.width ? Math.min(this.size.x * cell.width, Math.max(0, area.width - 2 * cell.width)) : this.size.x * cell.width;
        const height = area.height ? Math.min(this.size.y * cell.height, area.height) : this.size.y * cell.height;
        for (const [name, value] of Object.entries({ left: `${this.origin.x * cell.width}px`, top: `${this.origin.y * cell.height}px`,
            width: `${width}px`, height: `${height}px` })) {
            if (this.dialog.style[name] !== value) { this.dialog.style[name] = value; }
        }
    }

    bindCommonClose(onClose = () => this.close()) {
        this.closeAction = onClose;
    }

    bindDrag() {
        if (!this.titlebar) {
            return;
        }
        this.titlebar.addEventListener("mousedown", (event) => this.startDrag(event));
    }

    startDrag(event) {
        if ((this.flags & wfMove) === 0 || event.button > 0 || this.dragState) { return; }
        if (event.target.closest("button, input, a")) {
            return;
        }
        event.preventDefault();
        const rect = this.dialog.getBoundingClientRect(), area = this._visibleArea();
        this.dragState = {
            startX: event.clientX,
            startY: event.clientY,
            startLeft: this.origin.x * measureCells().width,
            startTop: this.origin.y * measureCells().height,
            maxLeft: Math.max(0, area.width - rect.width),
            maxTop: Math.max(0, area.height - rect.height),
            cell: measureCells(), size: this.size.copy(),
            transform: this.dialog.style.transform || "",
        };
        this.dialog.classList.add("is-dragging");
        updateWindowFrameState(this.dialog, true, { dialog: true });
        document.addEventListener("mousemove", this.onDragMove, true);
        document.addEventListener("mouseup", this.onDragEnd, true);
        window.addEventListener("blur", this.onDragEnd);
    }

    onDragMove = (event) => {
        if (!this.dragState) { return; }
        event.preventDefault?.(); event.stopPropagation?.();
        if (event.buttons === 0) { this.onDragEnd(event); return; }
        this._updateDragPosition(event);
        if (this.dragFrame === null) { this.dragFrame = window.requestAnimationFrame(this._applyDragPosition); }
    };

    _updateDragPosition(event) {
        const rawLeft = this.dragState.startLeft + (event.clientX - this.dragState.startX);
        const rawTop = this.dragState.startTop + (event.clientY - this.dragState.startY);
        this.dragState.nextLeft = Math.min(Math.max(rawLeft, 0), this.dragState.maxLeft);
        this.dragState.nextTop = Math.min(Math.max(rawTop, 0), this.dragState.maxTop);
    }

    _applyDragPosition = () => {
        this.dragFrame = null;
        const state = this.dragState;
        if (!state || state.nextLeft === undefined) { return; }
        const offset = `translate3d(${state.nextLeft - state.startLeft}px, ${state.nextTop - state.startTop}px, 0)`;
        const x = state.nextLeft / state.cell.width, y = state.nextTop / state.cell.height;
        this.setBounds(new TVRect(x, y, x + state.size.x, y + state.size.y));
        this.dialog.style.transform = state.transform ? `${offset} ${state.transform}` : offset;
    };

    onDragEnd = (event) => {
        if (!this.dragState) { return; }
        event?.preventDefault?.(); event?.stopPropagation?.();
        if (Number.isFinite(event?.clientX) && Number.isFinite(event?.clientY)) { this._updateDragPosition(event); }
        if (this.dragFrame !== null) { window.cancelAnimationFrame(this.dragFrame); this.dragFrame = null; }
        const state = this.dragState;
        this.dialog.style.transform = state.transform;
        if (state.nextLeft !== undefined) {
            this.moveTo(state.nextLeft / state.cell.width, state.nextTop / state.cell.height);
        }
        this.dragState = null;
        this.dialog.classList.remove("is-dragging");
        updateWindowFrameState(this.dialog, this.isActive(), { dialog: true });
        document.removeEventListener("mousemove", this.onDragMove, true);
        document.removeEventListener("mouseup", this.onDragEnd, true);
        window.removeEventListener("blur", this.onDragEnd);
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
        this.managedWindows = new WeakMap();
        this.managedDialogs = new WeakMap();
        this.windowCommands = new Map();
        this.stackOrder = [];
        this.baseZIndex = 10;
        this.hostWindow = this.root?.querySelector("[data-tv-window]") || null;
        this.activeTarget = HOST_WINDOW_TOKEN;
        this.selectionVersion = 0;
        this.onChange = null;
        this.activationPress = null;
        this.activationReleaseTimer = null;
        this.onMouseDown = nativeEvent => this.handleEvent(new TVEvent(evMouseDown, { nativeEvent }));
        this.onActivationClick = nativeEvent => {
            if (!this.activationPress?.contains(nativeEvent.target)) { return; }
            nativeEvent.preventDefault(); nativeEvent.stopImmediatePropagation();
            if (nativeEvent.type !== "contextmenu") { this._clearActivationPress(); }
        };
        this.onActivationMove = nativeEvent => {
            nativeEvent.preventDefault(); nativeEvent.stopImmediatePropagation();
        };
        this.onActivationRelease = nativeEvent => {
            this.onActivationMove(nativeEvent);
            // Native click follows mouseup before this timer may release the gate.
            this.activationReleaseTimer = window.setTimeout(() => this._clearActivationPress(), 0);
        };
        this.onActivationBlur = () => this._clearActivationPress();
        this.root?.addEventListener?.("mousedown", this.onMouseDown, true);
        for (const type of ["click", "dblclick", "contextmenu"]) {
            this.root?.addEventListener?.(type, this.onActivationClick, true);
        }
    }

    _mouseTarget(nativeEvent) {
        for (let element = nativeEvent.target; element; element = element.parentElement) {
            const dialogName = this.managedDialogs.get(element)?.name, dialog = this.dialogs.get(dialogName);
            if (dialog?.overlay === element && dialog.isOpen() && dialog.dialog.contains(nativeEvent.target)) {
                return { name: dialogName, root: dialog.dialog, view: dialog };
            }
            const windowName = this.managedWindows.get(element)?.name;
            if (this.windows.get(windowName) === element && this.isOpen(windowName)) {
                return { name: windowName, root: element, view: TVView._fromElement(element) };
            }
            if (element === this.hostWindow) {
                return { name: HOST_WINDOW_TOKEN, root: element, view: TVView._fromElement(element) };
            }
            if (element === this.root) { break; }
        }
        return null;
    }

    handleEvent(event) {
        if (event.what !== evMouseDown || !event.nativeEvent) { return; }
        this._clearActivationPress();
        const native = event.nativeEvent, target = this._mouseTarget(native);
        if (!target) { return; }
        event.infoPtr = target.view;
        const modal = this.get(this.activeTarget);
        const blocked = (modal?.isOpen() && modal.getState(sfModal) && this.activeTarget !== target.name)
            || (target.view && !viewAcceptsInput(target.view));
        const selecting = this.activeTarget !== target.name;
        const selectable = !target.view || (target.view.options & ofSelectable) !== 0;
        const firstClick = (target.view?.options & ofFirstClick) !== 0;
        if (!blocked && selecting && selectable) {
            this.desktop.owner?.menuBar?.closeMenus({ restoreFocus: false });
            if (target.name === HOST_WINDOW_TOKEN) { this.activateHostWindow(); }
            else if (this.dialogs.has(target.name)) { this.bringToFront(target.name); }
            else { this.activateWindow(target.name); }
        }
        const current = this._mouseTarget(native);
        if (blocked || (selecting && (!selectable || !firstClick)) || this.activeTarget !== target.name
            || current?.name !== target.name || current.root !== target.root
            || !target.root.isConnected || target.root.hidden) {
            this.activationPress = target.root;
            native.preventDefault(); native.stopImmediatePropagation();
            this.desktop.clearEvent(event);
            document.addEventListener("mousemove", this.onActivationMove, true);
            document.addEventListener("mouseup", this.onActivationRelease, true);
            window.addEventListener("blur", this.onActivationBlur);
        }
    }

    _clearActivationPress() {
        if (this.activationReleaseTimer !== null) { window.clearTimeout(this.activationReleaseTimer); }
        this.activationReleaseTimer = null;
        this.activationPress = null;
        document.removeEventListener("mousemove", this.onActivationMove, true);
        document.removeEventListener("mouseup", this.onActivationRelease, true);
        window.removeEventListener("blur", this.onActivationBlur);
    }

    destroy() {
        this._clearActivationPress();
        this.root?.removeEventListener?.("mousedown", this.onMouseDown, true);
        for (const type of ["click", "dblclick", "contextmenu"]) {
            this.root?.removeEventListener?.(type, this.onActivationClick, true);
        }
    }

    setHostWindow(element, commands = {}) {
        this.hostWindow = element || null;
        this.windowCommands.set(HOST_WINDOW_TOKEN, { ...commands });
        this.applyActiveStates();
    }

    activateHostWindow() {
        this._selectTarget(HOST_WINDOW_TOKEN);
    }

    registerWindow(name, element, commands = {}, activate = true) {
        this.windows.set(name, element);
        this.windowCommands.set(name, { ...commands });
        const view = TVView._fromElement(element);
        if (view instanceof TVWindow && view.root === element) { view.setManager(this, name); }
        this.managedWindows.set(element, { name });
        this._insertTarget(name, activate);
    }

    unregisterWindow(name) {
        const view = TVView._fromElement(this.windows.get(name));
        if (view instanceof TVWindow && view.manager === this && view.managerName === name) { view.setManager(null, ""); }
        this.windows.delete(name);
        this.windowCommands.delete(name);
        this._removeTarget(name, true);
    }

    activateWindow(name) {
        if (!this.windows.has(name) || !this.isOpen(name)) { return; }
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        this.stackOrder.push(name);
        this._selectTarget(name);
    }

    _selectTarget(name) {
        const version = ++this.selectionVersion;
        this.activeTarget = name;
        this.applyAllZIndices();
        this.applyActiveStates();
        if (version !== this.selectionVersion) { return; }
        if (this.onChange) { this.onChange(); }
        if (version === this.selectionVersion) { this._focusTarget(name); }
    }

    _focusTarget(name, preferred = null) {
        if (this.activeTarget !== name) { return; }
        const root = this.dialogs.get(name)?.dialog || this.windows.get(name)
            || (name === HOST_WINDOW_TOKEN ? this.hostWindow : null);
        if (root?.contains(document.activeElement)) { return; }
        const target = preferred?.isConnected && (!root || root.contains(preferred)) ? preferred : root;
        if (!target?.isConnected) { return; }
        try {
            target.focus({ preventScroll: true });
        } catch {
            target.focus();
        }
    }

    _targetName(view) {
        if (view?.root === this.hostWindow && this.hostWindow) { return HOST_WINDOW_TOKEN; }
        const name = view?.manager === this ? view.managerName : null;
        return name && (this.dialogs.get(name) === view || this.windows.get(name) === view.root) ? name : null;
    }

    _reorder(view, target) {
        const name = this._targetName(view);
        if (name === null) { return false; }
        const owner = this.desktop, targetName = target == null ? target : this._targetName(target);
        if (view.owner !== owner || !owner.children.includes(view) || target === view
            || (target != null && (target.owner !== owner || !owner.children.includes(target) || targetName === null))) { return true; }
        const available = candidate => candidate === HOST_WINDOW_TOKEN
            ? Boolean(this.hostWindow?.isConnected && !this.hostWindow.hidden)
            : this.isOpen(candidate);
        const selectable = candidate => {
            const child = this.dialogs.get(candidate) || TVView._fromElement(this.windows.get(candidate));
            return available(candidate) && (!child || (viewAcceptsInput(child) && (child.options & ofSelectable) !== 0));
        };
        if (!available(name) || !viewAcceptsInput(view) || (targetName != null && !available(targetName))) { return true; }
        const modal = this.get(this.activeTarget);
        if (modal?.isOpen() && modal.getState(sfModal) && (name !== this.activeTarget || target !== undefined)) { return true; }
        // The standalone host retains its existing foreground/background policy.
        if (name === HOST_WINDOW_TOKEN) {
            const next = target === null ? this.stackOrder.filter(selectable).at(-1) || HOST_WINDOW_TOKEN : HOST_WINDOW_TOKEN;
            if (next !== this.activeTarget) {
                if (next === HOST_WINDOW_TOKEN) { this.activateHostWindow(); }
                else if (this.dialogs.has(next)) { this.bringToFront(next); }
                else { this.activateWindow(next); }
            }
            return true;
        }
        const order = this.stackOrder.filter(candidate => candidate !== name);
        const position = target === undefined || (targetName === HOST_WINDOW_TOKEN && this.activeTarget === HOST_WINDOW_TOKEN)
            ? order.length : target === null || targetName === HOST_WINDOW_TOKEN ? 0 : order.indexOf(targetName) + 1;
        order.splice(position, 0, name);
        const active = this.activeTarget === HOST_WINDOW_TOKEN && target !== undefined && targetName !== HOST_WINDOW_TOKEN
            ? HOST_WINDOW_TOKEN : order.filter(selectable).at(-1) || HOST_WINDOW_TOKEN;
        if (active === this.activeTarget && order.every((candidate, index) => candidate === this.stackOrder[index])) { return true; }
        this.stackOrder = order;
        this._selectTarget(active);
        return true;
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
        registered.setManager(null, "");
        this.dialogs.delete(name);
        const wasStacked = this.stackOrder.includes(name);
        const wasActive = this.activeTarget === name;
        if (wasStacked || wasActive) {
            this._removeTarget(name, true);
        }
        return true;
    }

    _insertTarget(name, activate) {
        if (activate) {
            this.selectionVersion++;
            this.stackOrder = this.stackOrder.filter(target => target !== name);
            this.stackOrder.push(name);
            this.activeTarget = name;
        } else if (!this.stackOrder.includes(name)) {
            const index = Math.max(0, this.stackOrder.indexOf(this.activeTarget));
            this.stackOrder.splice(index, 0, name);
        }
        this.applyAllZIndices();
        this.applyActiveStates();
        if (this.onChange) { this.onChange(); }
    }

    onDialogOpened(name, activate = true) {
        this._insertTarget(name, activate);
    }

    _removeTarget(name, focus = false) {
        const wasActive = this.activeTarget === name;
        this.stackOrder = this.stackOrder.filter(n => n !== name);
        if (wasActive) { this.activeTarget = this.openTargets().at(-1) || HOST_WINDOW_TOKEN; }
        this.applyAllZIndices();
        this.applyActiveStates();
        if (this.onChange) { this.onChange(); }
        if (focus && wasActive) { this._focusTarget(this.activeTarget); }
    }

    installDialogHooks(name, dialog) {
        if (!dialog?.overlay) { return; }
        this.managedDialogs.set(dialog.overlay, { name });
    }

    applyAllZIndices() {
        if (this.hostWindow) {
            this.hostWindow.style.zIndex = String(this.activeTarget === HOST_WINDOW_TOKEN
                ? this.baseZIndex + this.stackOrder.length : this.baseZIndex - 1);
        }
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
        this._selectTarget(name);
    }

    get(name) {
        return this.dialogs.get(name) || null;
    }

    isOpen(name) {
        const dialog = this.get(name);
        if (dialog) { return dialog.isOpen(); }
        const element = this.windows.get(name);
        return Boolean(element?.isConnected && !element.hidden);
    }

    open(name, { exclusive = false, activate = true } = {}) {
        const dialog = this.get(name);
        if (!dialog) {
            return null;
        }
        if (exclusive) {
            this.closeAllExcept(name);
        }
        if (dialog.isOpen()) {
            if (activate) { this.bringToFront(name); }
            return dialog;
        }
        dialog.open(activate);
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
        if (!this.canDispatchCommand(TV_COMMANDS.NEXT)) { return false; }
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
        return this.stackOrder.filter(name => this.isOpen(name));
    }

    openWindowCount() {
        return Array.from(this.windows.keys()).filter(name => this.isOpen(name)).length;
    }

    canDispatchCommand(command) {
        if (command === TV_COMMANDS.NEXT || command === TV_COMMANDS.PREVIOUS) {
            const dialog = this.get(this.activeTarget);
            return !(dialog?.isOpen() && dialog.getState(sfModal)) && this.openTargets().length > 1;
        }
        const target = this.activeTarget;
        if (target !== HOST_WINDOW_TOKEN && !this.isOpen(target)) { return false; }
        const dialog = this.dialogs.get(target);
        if (dialog && dialog.isOpen()) {
            return (command === TV_COMMANDS.CLOSE || command === TV_COMMANDS.CANCEL) && (dialog.flags & wfClose) !== 0;
        }
        const element = target === HOST_WINDOW_TOKEN ? this.hostWindow : this.windows.get(target);
        const view = TVView._fromElement(element);
        if ((command === TV_COMMANDS.CLOSE || command === TV_COMMANDS.CANCEL)
            && view instanceof TVWindow && (view.flags & wfClose) === 0) { return false; }
        if (command === TV_COMMANDS.DEFAULT_SIZE) {
            return view instanceof TVWindow && (view.flags & wfGrow) !== 0 && Boolean(element?._tvResizer);
        }
        return typeof this.windowCommands.get(target)?.[command] === "function";
    }

    dispatchCommand(command) {
        if ((command === TV_COMMANDS.CLOSE || command === TV_COMMANDS.CANCEL)
            && !this.canDispatchCommand(command)) { return false; }
        if (command === TV_COMMANDS.NEXT) {
            if (!this.canDispatchCommand(command)) { return false; }
            return this.cycleTarget(1);
        }
        if (command === TV_COMMANDS.PREVIOUS) {
            if (!this.canDispatchCommand(command)) { return false; }
            return this.cycleTarget(-1);
        }
        const target = this.activeTarget;
        if (target !== HOST_WINDOW_TOKEN && !this.isOpen(target)) { return false; }
        if (command === TV_COMMANDS.DEFAULT_SIZE) {
            if (!this.canDispatchCommand(command)) { return false; }
            const element = target === HOST_WINDOW_TOKEN ? this.hostWindow : this.windows.get(target);
            TVView._fromElement(element).dispatchEvent(new TVEvent(evCommand, { command }));
            return true;
        }
        const dialog = this.dialogs.get(target);
        if (dialog && dialog.isOpen()) {
            if (command === TV_COMMANDS.CLOSE || command === TV_COMMANDS.CANCEL) {
                dialog.dispatchEvent(new TVEvent(evCommand, {
                    command: "dialog-close", infoPtr: dialog,
                }));
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
            if (TVView._fromElement(event.target)?.capturesKey?.(event)) { return; }
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
        this.closeAction = () => this._dismiss(this._closeCmd || "cancel");
        this.bindDrag();
    }

    show({ type = 0, title, lines = [], buttons = TVMessageBox.MF_OK_BUTTON } = {}) {
        if (this._resolve) {
            this._dismiss(this._closeCmd || "cancel");
        }
        const boxTitle = title !== undefined ? title : TVMessageBox.TITLES[type];
        this.title = String(boxTitle ?? "");
        this.frame.drawTitle();
        const sourceLines = (Array.isArray(lines) && lines.length ? lines : [""])
            .flatMap((line) => String(line).split(/\r\n|\r|\n/));
        const requestedButtons = TVMessageBox.BUTTON_DEFS.filter(b => (buttons & b.flag) !== 0);
        const btnDefs = requestedButtons.length
            ? requestedButtons
            : TVMessageBox.BUTTON_DEFS.filter(b => b.cmd === "ok");
        const buttonWidth = 10;
        const buttonGap = 2;
        const textWidth = Math.max(...sourceLines.map((line) => Array.from(line).length), 0);
        const cellWidth = measureCells().width;
        const visibleWidth = Math.min(this.overlay.clientWidth || 78 * cellWidth, window.innerWidth || 78 * cellWidth);
        const availableWidth = Math.max(12, Math.floor(visibleWidth / cellWidth) - 2);
        const width = Math.min(availableWidth, Math.max(42, Math.min(70, textWidth) + 6, btnDefs.length * 13));
        const columns = width - 5;
        const messageLines = sourceLines.flatMap((line) => wrapTextLines(line, columns));
        const buttonsPerRow = Math.max(1, Math.min(btnDefs.length, Math.floor((width - 2 + buttonGap) / (buttonWidth + buttonGap))));
        const buttonRows = Math.ceil(btnDefs.length / buttonsPerRow);
        const height = messageLines.length + 4 + 2 * buttonRows;
        const buttonsY = messageLines.length + 2;
        this.changeBounds(new TVRect(this.bounds.x1, this.bounds.y1, this.bounds.x1 + width, this.bounds.y1 + height));
        this.bodyView.setBounds(new TVRect(0, 0, width - 2, height - 2));
        this.contentView.setBounds(new TVRect(2, 1, width - 3, buttonsY));
        this.buttonsView.setBounds(new TVRect(0, buttonsY, width - 2, buttonsY + 2 * buttonRows));
        this.contentView.children.slice().forEach((view) => this.contentView.remove(view));
        this.buttonsView.children.slice().forEach((view) => this.buttonsView.remove(view));
        this.messageViews = messageLines.map((line, index) => (
            new TVStaticText(new TVRect(0, index, width - 5, index + 1), `\x03${line}`)
        ));
        this.buttonViews = btnDefs.map((definition, index) => {
            const row = Math.floor(index / buttonsPerRow), column = index % buttonsPerRow;
            const rowCount = Math.min(buttonsPerRow, btnDefs.length - row * buttonsPerRow);
            const rowWidth = rowCount * buttonWidth + Math.max(0, rowCount - 1) * buttonGap;
            const startX = Math.max(0, Math.floor((width - 2 - rowWidth) / 2)) + column * (buttonWidth + buttonGap);
            return new TVButton(
                new TVRect(startX, row * 2, startX + buttonWidth, row * 2 + 2),
                definition.label,
                "msgbox-cmd",
                index === 0 ? bfDefault : bfNormal,
            ).setValue(definition.cmd);
        });
        this.contentView.insertAll(this.messageViews);
        this.buttonsView.insertAll(this.buttonViews);
        this.drawContent();
        this._buttonDefs = btnDefs;
        // Determine default and cancel commands
        this._defaultCmd = btnDefs.length > 0 ? btnDefs[0].cmd : null;
        this._cancelCmd = (buttons & TVMessageBox.MF_CANCEL_BUTTON) ? "cancel" : null;
        this._closeCmd = this._cancelCmd || ((buttons & TVMessageBox.MF_NO_BUTTON) ? "no" : "cancel");
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
        const command = this._closeCmd || "cancel";
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
        const axis = (this._scrollOptions & sbVertical) !== 0 ? "y" : "x";
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
        this._scrollOptions = Number(options) || sbHorizontal;
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
        this._clientExtent = null;
        this._autoHideHorizontal = true;
        this._horizontalVisible = false;
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
        if (frame === this.frame && !this.destroyed) { this.refresh(); return this; }
        if (this.frame) { this.destroy(); }
        this._clientExtent = null;
        this._autoHideHorizontal = true;
        this._horizontalVisible = false;
        if (!frame) {
            this.root = null;
            this.frame = null;
            this.host = null;
            this.viewport = null;
            return this;
        }
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
        this.active = !frame.closest(".tv-window, .tv-dialog-window")?.classList.contains("is-window-inactive");
        this.bind();
        this.setActive(this.active);
        return this;
    }

    buildAxis(axis) {
        const root = this.host.querySelector(`:scope > .tv-scrollbar-${axis}, :scope > .tv-bottom-bar > .tv-scrollbar-${axis}`);
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
        if (!this._inputEnabled() || this.axisMetrics(axis).maxScroll <= 0) { return; }
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
        if (!this._inputEnabled()) { this.stopRepeat(); return; }
        const step = axis === "y" ? this.lineHeight() : this.charWidth() * 2;
        if (axis === "y") {
            this.viewport.scrollTop += direction * step;
        } else {
            this.viewport.scrollLeft += direction * step;
        }
        this.update();
    }

    handleWheel(event) {
        if (!this._inputEnabled()) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        const preferVertical = Math.abs(Number(event.deltaY) || 0) >= Math.abs(Number(event.deltaX) || 0);
        const candidates = preferVertical ? ["y", "x"] : ["x", "y"];
        const axisName = candidates.find((name) => this.axes[name] && this.axisMetrics(name).maxScroll > 0);
        if (!axisName) { return; }
        const metrics = this.axisMetrics(axisName);
        const rawDelta = axisName === "y"
            ? Number(event.deltaY) || Number(event.deltaX) || 0
            : Number(event.deltaX) || Number(event.deltaY) || 0;
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
        if (!this._inputEnabled()) { return; }
        if (event.target.closest("[data-role='thumb']")) {
            return;
        }
        event.preventDefault();
        const details = this.axisMetrics(axis);
        if (details.maxScroll <= 0 || details.trackSize <= 0) {
            return;
        }

        const coordinate = axis === "y" ? event.clientY : event.clientX;
        const rect = details.axis.track.getBoundingClientRect();
        const relative = (axis === "y" ? coordinate - rect.top : coordinate - rect.left) - details.thumbPx / 2;
        const ratio = details.freeTrackPx > 0 ? this.clamp(relative / details.freeTrackPx, 0, 1) : 0;
        this.setScrollPosition(axis, ratio * details.maxScroll);
    }

    onThumbMouseDown(event, axis) {
        if (!this._inputEnabled()) { return; }
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
        if (!this._inputEnabled()) { this.onDragEnd(); return; }
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
        const cellCount = Math.max(0, Math.floor(trackSize / cellSize));
        const thumbCells = maxScroll > 0 && cellCount > 0 ? 1 : 0;
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
        const separator = metrics.vertical ? "\n" : "";
        const track = Array(cellCount).fill(trackChar).join(separator);
        const thumb = Array(thumbCells).fill(THUMB_CHAR).join(separator);
        if (axis.cells.textContent !== track) { axis.cells.textContent = track; }
        if (axis.thumb.textContent !== thumb) { axis.thumb.textContent = thumb; }
        const bounds = metrics.vertical
            ? new TVRect(0, thumbStart, 1, thumbStart + thumbCells)
            : new TVRect(thumbStart, 0, thumbStart + thumbCells, 1);
        this._placePart(axis.thumb, bounds);

        axis.root.classList.toggle("is-disabled", maxScroll <= 0);
        axis.root.classList.toggle("is-inactive", !this.active);
        const unavailable = !this._inputEnabled() || maxScroll <= 0;
        axis.root.setAttribute("aria-disabled", unavailable ? "true" : "false");
        for (const button of [axis.backward, axis.forward]) {
            button.disabled = unavailable;
            button.tabIndex = unavailable ? -1 : 0;
        }
        axis.thumb.hidden = thumbCells === 0;
    }

    updateAxis(axisName) {
        const axis = this.axes[axisName];
        if (axis) {
            const cell = measureCells(), vertical = axisName === "y";
            const length = vertical ? axis.root.clientHeight / cell.height : axis.root.clientWidth / cell.width;
            const arrow = Math.min(1, length / 2), end = Math.max(arrow, length - arrow);
            const bounds = (start, finish) => vertical
                ? new TVRect(0, start, 1, finish) : new TVRect(start, 0, finish, 1);
            this._placePart(axis.backward, bounds(0, arrow));
            this._placePart(axis.track, bounds(arrow, end));
            this._placePart(axis.forward, bounds(end, length));
            this._placePart(axis.cells, bounds(0, Math.max(0, end - arrow)));
            this.updateTrackGlyphs(this.axisMetrics(axisName));
        }
    }

    update() {
        if (this.destroyed) { return; }
        if (!this._inputEnabled() && (this.dragState || this.repeatTimer !== null)) { this.onDragEnd(); }
        this._layoutClient();
        this.frame?._tvView?._layoutItems?.();
        this._layoutClient();
        Object.keys(this.axes).forEach((axisName) => this.updateAxis(axisName));
    }

    _setClientExtent(extent, autoHideHorizontal = true) {
        this._clientExtent = extent.copy();
        this._autoHideHorizontal = autoHideHorizontal;
        this.refresh();
    }

    _layoutClient() {
        const extent = this._clientExtent;
        if (!this.frame || !this.viewport || !extent || extent.width <= 0 || extent.height <= 0) { return; }
        const { x, y } = this.axes;
        const client = extent.copy();
        client.x2 = Math.max(0, client.x2 - (y ? 1 : 0));
        client.y2 = Math.max(0, client.y2 - (x && this._horizontalVisible ? 1 : 0));
        this._placePart(this.viewport, client.copy());
        const horizontal = Boolean(x && (!this._autoHideHorizontal || this.viewport.scrollWidth > this.viewport.clientWidth + 1));
        if (horizontal !== this._horizontalVisible) {
            client.y2 = Math.max(0, extent.height - (horizontal ? 1 : 0));
            this._placePart(this.viewport, client.copy());
            this._horizontalVisible = horizontal;
        }
        this.frame.classList.toggle("is-h-scrollable", horizontal);
        if (y) {
            this._placePart(y.root, new TVRect(client.x2, 0, extent.width, client.y2));
        }
        if (x) {
            x.root.hidden = !horizontal;
            this._placePart(x.root, new TVRect(0, client.y2, client.x2, extent.height));
        }
    }

    _inputEnabled() {
        const view = this.frame?._tvView || TVView._fromElement(this.frame);
        return this.active && viewAcceptsInput(this) && (!view || viewAcceptsInput(view));
    }

    setActive(active) {
        this.active = Boolean(active);
        if (!this.active) {
            this.stopRepeat();
            this.onDragEnd();
        }
        this.update();
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
        this.viewport?.removeEventListener("scroll", this.onViewportScroll);
        this.frame?.removeEventListener("wheel", this.onWheel);
        window.removeEventListener("resize", this.onWindowResize);
        for (const axis of Object.values(this.axes)) {
            axis.backward.removeEventListener("mousedown", axis.onBackwardMouseDown);
            axis.forward.removeEventListener("mousedown", axis.onForwardMouseDown);
            axis.track.removeEventListener("mousedown", axis.onTrackMouseDown);
            axis.thumb.removeEventListener("mousedown", axis.onThumbMouseDown);
            if (axis.root._tvScrollbar === this) { delete axis.root._tvScrollbar; }
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        if (this.root?._tvView === this) { delete this.root._tvView; }
        this.root = this.frame = this.host = this.viewport = null;
        this.axes = {};
    }
}

class TVProgram extends TVGroup {
    constructor(bounds = new TVRect()) {
        super(bounds);
        this.desktopView = null;
        this.menuBar = null;
        this.statusLine = null;
        this.onScreenResize = () => this.initScreen();
    }

    bindRoot(root) {
        window.removeEventListener("resize", this.onScreenResize);
        super.bindRoot(root);
        if (root) {
            window.addEventListener("resize", this.onScreenResize, { passive: true });
            this.initScreen();
            document.fonts?.ready.then(() => {
                if (this.root === root && root.isConnected) { window.dispatchEvent(new Event("resize")); }
            });
        }
        return this;
    }

    insert(view) {
        const owned = this.children.includes(view) && view.owner === this;
        if (!owned) { this._validateInsert(view); }
        const slot = view instanceof TVMenuBar ? "menuBar"
            : view instanceof TVStatusLine ? "statusLine" : view instanceof TVDesktop ? "desktopView" : "";
        if (slot) {
            if (this[slot] && this[slot] !== view) { super.remove(this[slot]); }
            this[slot] = view;
        }
        if (!owned) { super.insert(view); }
        this._layoutScreen();
        return view;
    }

    remove(view) {
        const removed = super.remove(view);
        for (const slot of ["menuBar", "statusLine", "desktopView"]) {
            if (this[slot] === view) { this[slot] = null; }
        }
        this._layoutScreen();
        return removed;
    }

    initScreen() {
        if (!this.root?.clientWidth || !this.root.clientHeight) { return; }
        measuredCell = null;
        const cell = measureCells();
        this.setBounds(new TVRect(this.origin.x, this.origin.y,
            this.origin.x + this.root.clientWidth / cell.width, this.origin.y + this.root.clientHeight / cell.height));
        this._layoutScreen();
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this._layoutScreen();
        return this;
    }

    _layoutScreen() {
        if (!this.root) { return; }
        const width = this.size.x, height = this.size.y, top = this.menuBar ? 1 : 0;
        const bottom = Math.max(top, height - (this.statusLine ? 1 : 0));
        for (const [view, bounds] of [
            [this.menuBar, new TVRect(0, 0, width, 1)],
            [this.desktopView, new TVRect(0, top, width, bottom)],
            [this.statusLine, new TVRect(0, bottom, width, bottom + 1)],
        ]) {
            if (!view?.root || view.root.parentElement !== this.root) { continue; }
            // Browser window adapters keep normal/maximized window geometry;
            // changing the screen does not proportionally grow every window.
            view.setBounds(bounds);
            this._placePart(view.root, bounds);
            view.drawView();
        }
    }

    handleEvent(event) {
        super.handleEvent(event);
        const target = TVView._fromElement(document.activeElement);
        if (event.what === evCommand && [cmCut, cmCopy, cmPaste].includes(event.command)
            && (target instanceof TVInputLine || target instanceof TVEditor)) {
            target.handleEvent(event);
        } else if ((event.what === evKeyDown && clipboardKeyCommand(event.nativeEvent) === cmCopy)
            || (event.what === evCommand && event.command === cmCopy)) {
            handleClipboardEvent(this, event);
        }
    }

    async clipCopy() {
        const selection = window.getSelection(), desktop = owningDesktop(this);
        const manager = desktop?.dialogManager, dialog = manager?.get(manager.activeTarget);
        const scope = dialog?.isOpen() && dialog.getState(sfModal) ? dialog.dialog : desktop?.root;
        if (!selection || selection.isCollapsed || !scope?.contains(selection.anchorNode)
            || !scope.contains(selection.focusNode)) { return false; }
        await writeClipboardText(selection.toString());
        return true;
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
        this.dialogManager?.destroy();
        super.bindRoot(root);
        this._background = root?.querySelector(":scope > [data-tv-desktop-pattern]") || null;
        this.dialogManager = new TVDialogManager(this);
        return this;
    }

    drawView() {
        if (!this.root || !this._background) { return this; }
        const cell = measureCells(), width = this.root.clientWidth / cell.width, height = this.root.clientHeight / cell.height;
        this._placePart(this._background, new TVRect(0, 0, width, height));
        const char = this._background.getAttribute("data-tv-desktop-pattern") || "\u2591";
        const line = char.repeat(Math.max(1, Math.ceil(width) + 1));
        const text = Array(Math.max(1, Math.ceil(height) + 1)).fill(line).join("\n");
        if (this._background.textContent !== text) { this._background.textContent = text; }
        return this;
    }

    insert(view) {
        const inserted = super.insert(view);
        if (this.root && inserted.root && !inserted.root.isConnected) {
            inserted.mount(this.root);
        }
        return inserted;
    }

    setCurrent(view) {
        const manager = this.dialogManager, name = manager?._targetName(view);
        if (name == null) { return super.setCurrent(view); }
        if (view.owner !== this || !this.children.includes(view) || (view.options & ofSelectable) === 0
            || !viewAcceptsInput(view) || !view.root?.isConnected) { return this.current; }
        const modal = manager.get(manager.activeTarget);
        if (modal?.isOpen() && modal.getState(sfModal) && manager.activeTarget !== name) { return this.current; }
        if (manager.activeTarget !== name) { manager._selectTarget(name); }
        return manager.activeTarget === name ? view : this.current;
    }

    _reorder(view, target) {
        if (!this.dialogManager?._reorder(view, target)) { super._reorder(view, target); }
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
        this.dialogManager?.destroy();
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
    saveLocalFile,
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
    cmCommandSetChanged,
    cmCut,
    cmCopy,
    cmPaste,
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
    kbCtrlIns,
    kbShiftIns,
    kbShiftDel,
    kbF1,
    kbF3,
    kbF4,
    kbF5,
    kbF6,
    kbShiftF6,
    kbAltF3,
    kbAlt0,
    getKeyCode,
    writeClipboardText,
    readClipboardText,
    messageBox,
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
    recordStatisticsEvent,
    wrapTextLines,
    renderHotkeyMarkup,
    displayCp437Char,
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
    TVCommandSet,
    TVStaticText,
    TVImage,
    TVTextScreen,
    TVPercentGauge,
    TVBarGauge,
    TVLabel,
    TVPXPictureValidator,
    TVFilterValidator,
    TVEmailValidator,
    TVInputLine,
    TVListViewer,
    TVPagedCollection,
    TVGroup,
    TVInfoRow,
    TVInfoBox,
    TVTerminal,
    TVIndicator,
    TVEditor,
    TVListBox,
    TVGridView,
    TVOutline,
    TVScroller,
    TVMenu,
    NewItem,
    NewMenu,
    NewLine,
    NewSubMenu,
    TVMenuView,
    TVMenuItem,
    TVSubMenu,
    TVMenuBar,
    TVMenuBox,
    TVStatusItem,
    TVStatusLink,
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
    cfOneBit,
    cfTwoBits,
    cfFourBits,
    cfEightBits,
    TVButton,
    bfNormal,
    bfDefault,
    bfLeftJust,
    bfBroadcast,
    cmGrabDefault,
    cmReleaseDefault,
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

// Native input changes only the shared button's drawn state; commands keep
// their existing TVEvent path through the owner.
function drawButtonPress(event) {
    const keyboard = event.type === "keydown";
    if (keyboard ? (![" ", "Enter"].includes(event.key) || event.repeat || event.altKey || event.ctrlKey || event.metaKey)
        : event.button !== 0) { return; }
    const btn = event.target?.closest?.(".tv-dialog-button");
    if (!btn || !btn.isConnected || btn.disabled) { return; }
    const button = TVView._fromElement(btn);
    if (!(button instanceof TVButton)) { return; }
    button._releasePress?.();
    button.drawState(true);
    const release = (nativeEvent) => {
        if (nativeEvent?.type === "keyup" && nativeEvent.key !== event.key) { return; }
        document.removeEventListener(keyboard ? "keyup" : "mouseup", release);
        btn.removeEventListener("mouseleave", release);
        btn.removeEventListener("blur", release);
        window.removeEventListener("blur", release);
        button._releasePress = null;
        button.drawState(false);
    };
    button._releasePress = release;
    document.addEventListener(keyboard ? "keyup" : "mouseup", release);
    if (!keyboard) { btn.addEventListener("mouseleave", release); }
    btn.addEventListener("blur", release);
    window.addEventListener("blur", release);
}
document.addEventListener("mousedown", drawButtonPress);
document.addEventListener("keydown", drawButtonPress);

})();
