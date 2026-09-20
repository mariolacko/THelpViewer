// Bundle viewer: single-page app that loads help JSON bundles on demand.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    renderHotkeyMarkup,
    fillBorders,
    fillDesktopPatterns,
    updateClocks,
    applyThemeAndSyncPalette,
    initializeTVTheme,
    TVDialogManager,
    TV_COMMANDS,
    TVMenuController,
    TVAboutDialog,
    TVPuzzleDialog,
    TVCalendarDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVColorsDialog,
    TVWidgetGalleryDialog,
    TVFileOpenDialog,
    TVChangeDirectoryDialog,
    TVMidiPlayerDialog,
    TVSearchDialog,
    TVTetrisDialog,
    TVMinesDialog,
    TVBreakOutDialog,
    TVSokobanDialog,
    TVLinesDialog,
    TVReversiDialog,
    TVLudoDialog,
    TVSnakeDialog,
    TVScreenSaver,
    TVWindow,
    TVWidget,
    TVIndicator,
    TVEditor,
    TVButton,
    TVMenuBox,
    measureCells,
    TVScrollBar,
    TurboVisionWindowResizer,
    bindCloseButtons,
    SCROLL_REPEAT_MS,
    TRACK_CHAR,
    DISABLED_TRACK_CHAR,
    THUMB_CHAR,
    highlightCodeExamples,
    DOS_COLORS,
} = TV;

// ── Catalog & data cache ────────────────────────────────────────────

const HELPS_DIR = "helps/";
const CATALOG_FILE = HELPS_DIR + "catalog.json";
const DOCS_DIR = "docs/";
const DOCS_CATALOG_FILE = DOCS_DIR + "catalog.json";
const bundleCache = new Map();
let catalogData = null;
let docsCatalogData = null;
const URL_STATE_PREFIX = "tv=1.";

function encodeUrlState(state) {
    const json = JSON.stringify(state);
    const bytes = new TextEncoder().encode(json);
    let binary = "";
    for (const byte of bytes) {
        binary += String.fromCharCode(byte);
    }
    return URL_STATE_PREFIX + btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function decodeUrlState(hash) {
    const raw = String(hash || "").replace(/^#/, "");
    if (!raw.startsWith(URL_STATE_PREFIX)) { return null; }
    try {
        const base64 = raw.slice(URL_STATE_PREFIX.length).replace(/-/g, "+").replace(/_/g, "/");
        const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
        const binary = atob(padded);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index);
        }
        const state = JSON.parse(new TextDecoder().decode(bytes));
        return state && state.v === 1 && Array.isArray(state.w) ? state : null;
    } catch {
        return null;
    }
}

function numericCssVar(style, name, fallback) {
    const value = Number.parseFloat(style.getPropertyValue(name));
    return Number.isFinite(value) ? value : fallback;
}

function captureWindowGeometry(element, dialog = false) {
    if (!element) { return null; }
    const style = getComputedStyle(element);
    const cell = measureCells ? measureCells() : { width: 9, height: 16 };
    const leftName = dialog ? "--tv-dialog-left" : "--tv-window-left";
    const topName = dialog ? "--tv-dialog-top" : "--tv-window-top";
    const colsName = dialog ? "" : "--tv-window-cols";
    const rowsName = dialog ? "" : "--tv-window-rows";
    const left = numericCssVar(style, leftName, element.offsetLeft);
    const top = numericCssVar(style, topName, element.offsetTop);
    const cols = colsName
        ? numericCssVar(style, colsName, Math.round(element.offsetWidth / cell.width))
        : Math.round(element.offsetWidth / cell.width);
    const rows = rowsName
        ? numericCssVar(style, rowsName, Math.round(element.offsetHeight / cell.height))
        : Math.round(element.offsetHeight / cell.height);
    return [
        Math.max(0, Math.round(left)),
        Math.max(0, Math.round(top)),
        Math.max(1, Math.round(cols)),
        Math.max(1, Math.round(rows)),
        element.classList.contains("is-maximized") ? 1 : 0,
    ];
}

function applyWindowGeometry(element, geometry, dialog = false) {
    if (!element || !Array.isArray(geometry) || geometry.length < 2) { return; }
    const left = Math.max(0, Number(geometry[0]) || 0);
    const top = Math.max(0, Number(geometry[1]) || 0);
    const cols = Math.max(1, Number(geometry[2]) || 1);
    const rows = Math.max(1, Number(geometry[3]) || 1);
    const maximized = Boolean(Number(geometry[4]));
    if (dialog) {
        element.style.setProperty("--tv-dialog-left", `${left}px`);
        element.style.setProperty("--tv-dialog-top", `${top}px`);
        element.style.setProperty("--tv-dialog-width", `${cols}ch`);
        element.style.setProperty("--tv-dialog-height", `${rows}em`);
    } else {
        element.style.setProperty("--tv-window-left", `${left}px`);
        element.style.setProperty("--tv-window-top", `${top}px`);
        element.style.setProperty("--tv-window-cols", String(cols));
        element.style.setProperty("--tv-window-rows", String(rows));
        element.classList.toggle("is-maximized", maximized);
        const glyph = element.querySelector("[data-tv-zoom-glyph]");
        if (glyph) { glyph.textContent = maximized ? "↓" : "↑"; }
    }
}

function textLineCol(text, offset) {
    const safeOffset = Math.max(0, Math.min(Number(offset) || 0, text.length));
    const before = text.slice(0, safeOffset);
    const parts = before.split("\n");
    return [parts.length, parts[parts.length - 1].length];
}

function textOffsetFromLineCol(text, line, col) {
    const targetLine = Math.max(1, Number(line) || 1);
    const targetCol = Math.max(0, Number(col) || 0);
    let offset = 0;
    let currentLine = 1;
    while (currentLine < targetLine && offset < text.length) {
        const next = text.indexOf("\n", offset);
        if (next < 0) { return text.length; }
        offset = next + 1;
        currentLine += 1;
    }
    const lineEnd = text.indexOf("\n", offset);
    const maxOffset = lineEnd < 0 ? text.length : lineEnd;
    return Math.min(offset + targetCol, maxOffset);
}

function textOffsetForNode(root, node, offset) {
    try {
        const range = document.createRange();
        range.selectNodeContents(root);
        range.setEnd(node, offset);
        const value = range.toString().length;
        if (typeof range.detach === "function") { range.detach(); }
        return value;
    } catch {
        return -1;
    }
}

function textNodeAtOffset(root, offset) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let total = 0;
    let last = null;
    let current = walker.nextNode();
    while (current) {
        last = current;
        const length = current.nodeValue.length;
        if (total + length >= offset) {
            return { node: current, offset: Math.max(0, Math.min(length, offset - total)) };
        }
        total += length;
        current = walker.nextNode();
    }
    return last ? { node: last, offset: last.nodeValue.length } : null;
}

function captureTextSelection(root) {
    const selection = window.getSelection ? window.getSelection() : null;
    if (!root || !selection || selection.rangeCount === 0 || selection.isCollapsed) { return null; }
    const range = selection.getRangeAt(0);
    if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) { return null; }
    const text = root.textContent || "";
    const start = textOffsetForNode(root, range.startContainer, range.startOffset);
    const end = textOffsetForNode(root, range.endContainer, range.endOffset);
    if (start < 0 || end < 0 || start === end) { return null; }
    return [...textLineCol(text, start), ...textLineCol(text, end)];
}

function restoreTextSelection(root, selectionState) {
    if (!root || !Array.isArray(selectionState) || selectionState.length < 4) { return; }
    const text = root.textContent || "";
    const start = textNodeAtOffset(root, textOffsetFromLineCol(text, selectionState[0], selectionState[1]));
    const end = textNodeAtOffset(root, textOffsetFromLineCol(text, selectionState[2], selectionState[3]));
    if (!start || !end) { return; }
    const range = document.createRange();
    range.setStart(start.node, start.offset);
    range.setEnd(end.node, end.offset);
    const selection = window.getSelection ? window.getSelection() : null;
    if (selection) {
        selection.removeAllRanges();
        selection.addRange(range);
    }
}

function loadBundle(filename, { onProgress, signal } = {}) {
    if (bundleCache.has(filename)) {
        return Promise.resolve(bundleCache.get(filename));
    }
    const fetchUrl = HELPS_DIR + filename;
    return fetch(fetchUrl, { signal, cache: "no-store" }).then(async (response) => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} loading ${filename}`);
        }
        const contentLength = Number(response.headers.get("Content-Length")) || 0;

        let payloadBytes;
        if (!contentLength || !response.body) {
            payloadBytes = new Uint8Array(await response.arrayBuffer());
            if (onProgress) { onProgress(1, 1); }
        } else {
            const reader = response.body.getReader();
            const chunks = [];
            let received = 0;
            const simulateSlow = new URLSearchParams(window.location.search).has("slow");
            while (true) {
                if (signal && signal.aborted) {
                    await reader.cancel();
                    throw new DOMException("Aborted", "AbortError");
                }
                const { done, value } = await reader.read();
                if (done) { break; }
                chunks.push(value);
                received += value.length;
                if (onProgress) { onProgress(received, contentLength); }
                if (simulateSlow) { await new Promise((r) => setTimeout(r, 80)); }
            }
            // Reassemble
            const total = chunks.reduce((s, c) => s + c.length, 0);
            payloadBytes = new Uint8Array(total);
            let offset = 0;
            for (const chunk of chunks) {
                payloadBytes.set(chunk, offset);
                offset += chunk.length;
            }
        }

        let json;
        if (/\.gz$/i.test(filename)) {
            if (typeof DecompressionStream !== "function") {
                throw new Error("This browser does not support DecompressionStream for .json.gz bundles.");
            }
            const stream = new Blob([payloadBytes]).stream().pipeThrough(new DecompressionStream("gzip"));
            json = await new Response(stream).text();
        } else {
            json = new TextDecoder("utf-8").decode(payloadBytes);
        }
        const bundle = JSON.parse(json);
        if (bundle.uhf_version !== "2.0") {
            throw new Error(`Unsupported bundle version in ${filename}: ${bundle.uhf_version || "missing"}`);
        }
        bundle._catalogFile = filename;
        bundleCache.set(filename, bundle);
        return bundle;
    });
}

function bundleSourceFilename(bundle) {
    return (((bundle.metadata || {}).source || {}).filename) || "help";
}

function bundleSourceName(bundle) {
    return String(bundleSourceFilename(bundle) || "help").toLowerCase();
}

function normalizeSourceFileName(value) {
    return String(value || "").trim().toLowerCase();
}

function normalizeSourceFileStem(value) {
    const normalized = normalizeSourceFileName(value);
    if (!normalized) {
        return "";
    }
    const name = normalized.split(/[\\/]/).pop() || normalized;
    return name.replace(/\.[^.]+$/, "");
}

function preferredCatalogEntry(entries, preferredBundle = null) {
    if (!entries.length) {
        return null;
    }
    const preferredFile = String((preferredBundle || {})._catalogFile || "").trim();
    const preferredEntry = preferredFile && Array.isArray(catalogData)
        ? catalogData.find((entry) => normalizeSourceFileName(entry.file || "") === normalizeSourceFileName(preferredFile))
        : null;
    if (!preferredEntry) {
        return entries[0];
    }

    const preferredGroup = normalizeSourceFileName(preferredEntry.group || "");
    const sameGroup = preferredGroup
        ? entries.find((entry) => normalizeSourceFileName(entry.group || "") === preferredGroup)
        : null;
    if (sameGroup) {
        return sameGroup;
    }

    const preferredProduct = normalizeSourceFileName(preferredEntry.product || "");
    const preferredVersion = normalizeSourceFileName(preferredEntry.version || "");
    const sameProductVersion = entries.find((entry) =>
        preferredProduct
        && normalizeSourceFileName(entry.product || "") === preferredProduct
        && normalizeSourceFileName(entry.version || "") === preferredVersion
    );
    return sameProductVersion || entries[0];
}

function findCatalogEntryBySourceFile(sourceFile, preferredBundle = null) {
    const wanted = normalizeSourceFileName(sourceFile);
    if (!wanted || !Array.isArray(catalogData)) {
        return null;
    }
    const sourceFiles = (entry) => {
        const values = [];
        if (entry && typeof entry.source_file === "string") {
            values.push(entry.source_file);
        }
        if (entry && Array.isArray(entry.source_files)) {
            for (const value of entry.source_files) {
                if (typeof value === "string") {
                    values.push(value);
                }
            }
        }
        return values;
    };
    // Check explicit source files and the source_files array
    let matches = catalogData.filter((entry) => sourceFiles(entry).some((value) => normalizeSourceFileName(value) === wanted));
    let found = preferredCatalogEntry(matches, preferredBundle);
    if (found) { return found; }

    // Check bundle file path (catalog entry 'file')
    found = catalogData.find((entry) => normalizeSourceFileName(entry.file || "") === wanted) || null;
    if (found) { return found; }

    const wantedStem = normalizeSourceFileStem(sourceFile);
    if (!wantedStem) { return null; }

    matches = catalogData.filter((entry) =>
        sourceFiles(entry).some((value) => normalizeSourceFileStem(value) === wantedStem)
        || normalizeSourceFileStem(entry.file || "") === wantedStem
    );
    return preferredCatalogEntry(matches, preferredBundle);
}

function bundleLoadingLabel(value, fallback = "") {
    if (value && typeof value === "object") {
        const name = String(value.name || "").trim();
        if (name) {
            return name;
        }
        const file = String(value.file || "").trim();
        if (file) {
            return file.split("/").pop() || file;
        }
    }
    const text = String(value || fallback || "").trim();
    if (!text) {
        return "Help";
    }
    return text.split("/").pop() || text;
}

function bundleDisplayLayout(bundle) {
    const display = ((bundle.metadata || {}).display) || {};
    let cols = Number.isInteger(display.cols) && display.cols > 0 ? display.cols : null;
    const rows = Number.isInteger(display.rows) && display.rows > 0 ? display.rows : null;

    // QuickHelp 2.50 stores a 160-column screen hint that is not the intended
    // outer help-window width. Treat it as source metadata, not fixed layout.
    if (bundleSourceFormat(bundle) === "quickhelp" && Number.isInteger(cols) && cols > 100) {
        cols = null;
    }

    return { cols, rows };
}

function bundleTitle(bundle) {
    return ((bundle.metadata || {}).name) || "Help";
}

function bundleHeaderLabel(bundle) {
    const title = bundleTitle(bundle);
    const sourceName = bundleSourceName(bundle);
    return sourceName ? `${title} (${sourceName})` : title;
}

function formatHlxControlBytes(values) {
    if (!Array.isArray(values)) {
        return "";
    }
    return values
        .map((value) => Number.parseInt(value, 10))
        .filter((value) => Number.isInteger(value) && value >= 0)
        .slice(0, 3)
        .map((value) => `0x${value.toString(16).toUpperCase()}`)
        .join(" ");
}

function bundleDiagnosticItems(bundle) {
    if (bundleSourceFormat(bundle) !== "hlx") {
        return [];
    }

    const metadata = bundle && typeof bundle === "object" ? (bundle.metadata || {}) : {};
    const items = [];

    if (typeof metadata.hlx_kind === "string" && metadata.hlx_kind.trim()) {
        items.push({ label: "Kind", value: metadata.hlx_kind.trim() });
    }
    if (typeof metadata.hlx_family === "string" && metadata.hlx_family.trim()) {
        items.push({ label: "Family", value: metadata.hlx_family.trim() });
    }
    if (Number.isInteger(metadata.pointer_count)) {
        items.push({ label: "Ptrs", value: String(metadata.pointer_count) });
    }
    const controlBytes = formatHlxControlBytes(metadata.control_byte_dominant);
    if (controlBytes) {
        items.push({ label: "Ctrl", value: controlBytes });
    }
    return items;
}

function renderBundleDiagnostics(bundle) {
    void bundle;
    return "";
}

function wrapBundleContent(bundle, contentHTML) {
    void bundle;
    return contentHTML;
}

function bundleWindowSpec(bundle) {
    const display = bundleDisplayLayout(bundle);
    let cols = 82;
    let rows = 24;
    const hasExplicitCols = Number.isInteger(display.cols) && display.cols > 0;
    const hasExplicitRows = Number.isInteger(display.rows) && display.rows > 0;
    if (Number.isInteger(display.cols) && display.cols > 0) {
        cols = display.cols + 4;
    }
    if (Number.isInteger(display.rows) && display.rows > 0) {
        rows = display.rows + 4;
    }
    return {
        cols,
        rows,
        min_cols: hasExplicitCols ? cols : Math.min(cols, 82),
        min_rows: hasExplicitRows ? rows : Math.min(rows, 25),
    };
}

function bundleUsesFixedTopicLayout(bundle) {
    const display = bundleDisplayLayout(bundle);
    return Number.isInteger(display.cols) && display.cols > 0;
}

function bundleWindowKey(bundle) {
    return bundle._catalogFile || bundleSourceFilename(bundle) || bundleHeaderLabel(bundle);
}

function bundleTopicList(bundle) {
    const topics = bundle.topics && typeof bundle.topics === "object"
        ? Object.values(bundle.topics)
        : [];
    topics.sort((a, b) => (Number(a.id) || 0) - (Number(b.id) || 0));
    return topics;
}

function bundleHelpContentsTopicRef(bundle) {
    const metadata = bundle && typeof bundle === "object" ? (bundle.metadata || {}) : {};
    const direct = normalizeDirectTopicRef(bundle, metadata.help_contents_topic_id);
    if (direct) { return direct; }
    const topics = bundleTopicList(bundle);
    const helpContents = topics.find((topic) => topic && topic.is_help_contents);
    if (helpContents) { return String(helpContents.id); }
    return null;
}

function bundleFirstTopicRef(bundle) {
    const topics = bundleTopicList(bundle);
    return topics.length ? String(topics[0].id) : null;
}

function bundleTopicFallbackRef(bundle) {
    return bundleHelpContentsTopicRef(bundle) || bundleFirstTopicRef(bundle);
}

function normalizeDirectTopicRef(bundle, ref) {
    if (ref == null) { return null; }
    const raw = String(ref).trim();
    if (!raw) { return null; }
    const topics = bundle.topics && typeof bundle.topics === "object" ? bundle.topics : {};
    if (Object.prototype.hasOwnProperty.call(topics, raw)) {
        return raw;
    }
    if (/^[0-9]+$/.test(raw)) {
        const normalized = String(parseInt(raw, 10));
        if (Object.prototype.hasOwnProperty.call(topics, normalized)) {
            return normalized;
        }
    }
    return null;
}

function normalizeTopicAlias(value) {
    return String(value || "").trim().toLowerCase();
}

function bundleAliasMap(bundle) {
    if (bundle._topicAliasMap instanceof Map) {
        return bundle._topicAliasMap;
    }

    const aliasMap = new Map();
    const topics = bundle.topics && typeof bundle.topics === "object" ? bundle.topics : {};
    for (const [rawKey, topic] of Object.entries(topics)) {
        const resolvedTopic = normalizeDirectTopicRef(bundle, rawKey)
            || (topic && topic.id != null ? normalizeDirectTopicRef(bundle, topic.id) : null)
            || String(rawKey).trim();
        const aliases = topic && typeof topic === "object" ? topic.aliases : null;
        const addAlias = (value) => {
            const normalized = normalizeTopicAlias(value);
            if (!normalized || aliasMap.has(normalized)) {
                return;
            }
            aliasMap.set(normalized, resolvedTopic);
        };

        if (aliases && typeof aliases === "object") {
            const ids = Array.isArray(aliases.ids) ? aliases.ids : [];
            const strings = Array.isArray(aliases.strings) ? aliases.strings : [];
            ids.forEach((value) => addAlias(value));
            strings.forEach((value) => addAlias(value));
        }
    }

    bundle._topicAliasMap = aliasMap;
    return aliasMap;
}

function normalizeTopicRef(bundle, ref) {
    const direct = normalizeDirectTopicRef(bundle, ref);
    if (direct) {
        return direct;
    }
    const alias = normalizeTopicAlias(ref);
    if (!alias) {
        return null;
    }
    return bundleAliasMap(bundle).get(alias) || null;
}

function flattenUhfIndexEntries(bundle) {
    const entries = [];
    if (!Array.isArray(bundle.index)) {
        return entries;
    }
    bundle.index.forEach((group) => {
        const groupEntries = Array.isArray(group && group.entries) ? group.entries : [];
        groupEntries.forEach((entry) => {
            if (entry == null) {
                return;
            }
            if (entry.topic_id == null) { return; }
            const payload = {
                label: entry.label || "",
                context_id: entry.topic_id,
                context_hex: String(entry.topic_id),
            };
            if (entry.line != null) {
                payload.line = entry.line;
            }
        if (entry.file) {
            payload.file = entry.file;
        }
            entries.push(payload);
        });
    });
    return entries;
}

function bundleIndexEntries(bundle) {
    return flattenUhfIndexEntries(bundle);
}

function bundleHasIndexEntries(bundle) {
    return bundleIndexEntries(bundle).length > 0;
}

function bundleHasNavAction(bundle, action) {
    const wanted = String(action || "").toLowerCase();
    if (!wanted) { return false; }
    return bundleTopicList(bundle).some((topic) => {
        const nav = topic && topic.nav && typeof topic.nav === "object" ? topic.nav : {};
        return Object.values(nav).some((item) =>
            item
            && typeof item === "object"
            && String(item.action || "").toLowerCase() === wanted
        );
    });
}

function bundleCanShowIndex(bundle) {
    return bundleHasIndexEntries(bundle);
}

function bundleCanShowContents(bundle) {
    return Array.isArray(bundle.contents) && bundle.contents.length > 0;
}

function bundleCanShowHelpContentsTopic(bundle) {
    return !!bundleHelpContentsTopicRef(bundle);
}

function resolveMissingSourceTopicFallback(bundle, sourceFile, topicRef) {
    const localRef = bundle ? normalizeTopicRef(bundle, topicRef) : null;
    if (localRef) {
        return { type: "topic", ref: localRef };
    }

    if (!bundle || bundleSourceFormat(bundle) !== "quickhelp") {
        return null;
    }

    const normalizedSource = normalizeSourceFileName(sourceFile);
    const normalizedTopic = normalizeTopicAlias(topicRef);
    if (!normalizedTopic) {
        return null;
    }
    if (/(^|[!:])(?:[a-z0-9_.-]+\.)?contents$/.test(normalizedTopic)) {
        return { type: "contents" };
    }
    if (/(^|[!:])(?:[a-z0-9_.-]+\.)?index$/.test(normalizedTopic)) {
        return { type: "index" };
    }
    if ((normalizedSource === "qc.hlp" || normalizedSource === "qc") && /\.lst(?:v\d+)?(?:$|[!:])/.test(normalizedTopic)) {
        return { type: "contents" };
    }
    return null;
}

function isUhfCodeStart(line) {
    return /^\[code(?::[A-Za-z0-9_-]+)?\]$/i.test(line);
}

function stripUhfMarkup(text) {
    let result = "";
    let index = 0;
    while (index < text.length) {
        const ch = text[index];
        if (ch !== "[") {
            result += ch;
            index += 1;
            continue;
        }
        if (text[index + 1] === "[") {
            result += "[";
            index += 2;
            continue;
        }
        const close = text.indexOf("]", index + 1);
        if (close < 0) {
            result += text.slice(index);
            break;
        }
        index = close + 1;
    }
    return result;
}

function normalizeSearchText(text) {
    return stripUhfMarkup(String(text || "")).replace(/\s+/g, " ").trim();
}

function bundleTopicTitle(bundle, topic) {
    if (topic && typeof topic.title === "string" && topic.title.trim()) {
        return topic.title.trim();
    }
    return topic && topic.id != null ? `Topic ${topic.id}` : "Topic";
}

function renderUhfRule(bundle) {
    void bundle;
    return escapeHtml("─".repeat(512));
}

const STANDARD_UHF_PALETTES = {
    cga: {
        type: "indexed",
        colors: DOS_COLORS.reduce((acc, color, index) => {
            acc[String(index)] = color;
            return acc;
        }, {}),
        aliases: {
            black: 0,
            blue: 1,
            green: 2,
            cyan: 3,
            red: 4,
            magenta: 5,
            brown: 6,
            lightgray: 7,
            light_gray: 7,
            darkgray: 8,
            dark_gray: 8,
            lightblue: 9,
            light_blue: 9,
            lightgreen: 10,
            light_green: 10,
            lightcyan: 11,
            light_cyan: 11,
            lightred: 12,
            light_red: 12,
            lightmagenta: 13,
            light_magenta: 13,
            yellow: 14,
            white: 15,
        },
    },
};

function normalizedUhfPalettes(bundle) {
    if (bundle && bundle._normalizedPalettes) {
        return bundle._normalizedPalettes;
    }
    const palettes = {};
    Object.entries(STANDARD_UHF_PALETTES).forEach(([name, palette]) => {
        palettes[name] = {
            type: palette.type || "indexed",
            colors: { ...(palette.colors || {}) },
            aliases: { ...(palette.aliases || {}) },
        };
    });

    const source = bundle && bundle.palettes && typeof bundle.palettes === "object" ? bundle.palettes : {};
    Object.entries(source).forEach(([name, palette]) => {
        if (!name || !palette || typeof palette !== "object") {
            return;
        }
        const target = palettes[name] || { type: "indexed", colors: {}, aliases: {} };
        if (typeof palette.type === "string" && palette.type.trim()) {
            target.type = palette.type.trim();
        }
        if (Array.isArray(palette.colors)) {
            palette.colors.forEach((color, index) => {
                if (typeof color === "string" && color.trim()) {
                    target.colors[String(index)] = color.trim();
                }
            });
        } else if (palette.colors && typeof palette.colors === "object") {
            Object.entries(palette.colors).forEach(([key, color]) => {
                if (typeof color === "string" && color.trim()) {
                    target.colors[String(key)] = color.trim();
                }
            });
        }
        if (palette.aliases && typeof palette.aliases === "object") {
            Object.entries(palette.aliases).forEach(([key, value]) => {
                if (key && (typeof value === "string" || Number.isInteger(value))) {
                    target.aliases[key] = value;
                }
            });
        }
        palettes[name] = target;
    });

    if (bundle) {
        bundle._normalizedPalettes = palettes;
    }
    return palettes;
}

function defaultUhfPaletteName(bundle) {
    const value = bundle && typeof bundle.default_palette === "string" ? bundle.default_palette.trim() : "";
    return value || "cga";
}

function normalizeUhfCssColor(value) {
    const color = String(value || "").trim();
    if (color.toLowerCase() === "transparent") {
        return "transparent";
    }
    let match = color.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (match) {
        return `#${match[1].toLowerCase()}`;
    }
    match = color.match(/^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i);
    if (match) {
        const parts = match.slice(1).map((part) => parseInt(part, 10));
        if (parts.every((part) => part >= 0 && part <= 255)) {
            return `rgb(${parts[0]},${parts[1]},${parts[2]})`;
        }
    }
    return null;
}

function resolveUhfPaletteValue(bundle, paletteName, value, seen) {
    const raw = String(value || "").trim();
    if (!raw) {
        return null;
    }
    const direct = normalizeUhfCssColor(raw);
    if (direct) {
        return direct;
    }
    const paletteMatch = raw.match(/^([A-Za-z][A-Za-z0-9_-]*):(.+)$/);
    if (paletteMatch && !/^rgb\s*\(/i.test(raw)) {
        return resolveUhfPaletteColor(bundle, paletteMatch[1], paletteMatch[2], seen);
    }
    return resolveUhfPaletteColor(bundle, paletteName, raw, seen);
}

function resolveUhfPaletteColor(bundle, paletteName, key, seen = new Set()) {
    const palettes = normalizedUhfPalettes(bundle);
    const palette = palettes[paletteName];
    if (!palette) {
        return null;
    }
    const rawKey = String(key || "").trim();
    if (!rawKey) {
        return null;
    }
    const seenKey = `${paletteName}:${rawKey.toLowerCase()}`;
    if (seen.has(seenKey)) {
        return null;
    }
    seen.add(seenKey);

    if (/^\d+$/.test(rawKey) && Object.prototype.hasOwnProperty.call(palette.colors || {}, rawKey)) {
        return resolveUhfPaletteValue(bundle, paletteName, palette.colors[rawKey], seen);
    }

    const aliasKey = rawKey.toLowerCase();
    if (palette.aliases && Object.prototype.hasOwnProperty.call(palette.aliases, aliasKey)) {
        return resolveUhfPaletteValue(bundle, paletteName, palette.aliases[aliasKey], seen);
    }

    if (Object.prototype.hasOwnProperty.call(palette.colors || {}, rawKey)) {
        return resolveUhfPaletteValue(bundle, paletteName, palette.colors[rawKey], seen);
    }

    return null;
}

function resolveUhfColor(bundle, rawValue, seen = new Set()) {
    const value = String(rawValue || "").trim();
    if (!value) {
        return null;
    }

    const direct = normalizeUhfCssColor(value);
    if (direct) {
        return direct;
    }

    const paletteMatch = value.match(/^([A-Za-z][A-Za-z0-9_-]*):(.+)$/);
    if (paletteMatch && !/^rgb\s*\(/i.test(value)) {
        return resolveUhfPaletteColor(bundle, paletteMatch[1], paletteMatch[2], seen);
    }

    return resolveUhfPaletteColor(bundle, defaultUhfPaletteName(bundle), value, seen);
}

const UHF_UI_THEME_VARS = {
    window: ["--tv-window", "--tv-owner-content-bg"],
    text: ["--tv-text", "--tv-owner-content-fg"],
    link: "--tv-link",
    title: ["--tv-title", "--tv-owner-title-active-bg", "--tv-owner-icon-active-bg", "--tv-owner-frame-icons-bg"],
    title_passive: ["--tv-title-passive", "--tv-owner-title-passive-bg"],
    title_text: ["--tv-title-text", "--tv-owner-title-active-fg"],
    title_text_passive: ["--tv-title-text-passive", "--tv-owner-title-passive-fg"],
    frame: ["--tv-frame-line", "--tv-owner-frame-active-fg"],
    frame_passive: ["--tv-frame-passive", "--tv-owner-frame-passive-fg"],
    icon: ["--tv-icon", "--tv-owner-icon-active-fg", "--tv-owner-frame-icons-fg"],
    icon_passive: ["--tv-icon-passive", "--tv-owner-icon-passive-fg"],
    page_area: ["--tv-page-area", "--tv-owner-scroll-page-bg"],
    hover_bg: "--tv-hover-bg",
    hover_fg: "--tv-hover-fg",
    arrow_bg: ["--tv-arrow-bg", "--tv-owner-scroll-controls-bg"],
    arrow_fg: ["--tv-arrow-fg", "--tv-owner-scroll-controls-fg"],
    scroll_glyph: ["--tv-scroll-glyph", "--tv-owner-scroll-page-fg"],
    thumb_bg: ["--tv-thumb-bg", "--tv-owner-scroll-thumb-bg"],
    thumb_fg: ["--tv-thumb-fg", "--tv-owner-scroll-thumb-fg"],
    code_bg: "--tv-code-bg",
    code_text: "--tv-code-text",
};

const DEFAULT_UHF_UI_BY_SOURCE_FORMAT = {
    thelp: {
        window: "cga:3",
        text: "cga:0",
        link: "cga:14",
        title: "cga:3",
        title_text: "cga:15",
        frame: "cga:15",
        icon: "cga:10",
        page_area: "cga:1",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        code_bg: "cga:1",
        code_text: "cga:14",
    },
    quickhelp: {
        window: "cga:0",
        text: "cga:7",
        link: "cga:14",
        title: "cga:0",
        title_passive: "cga:0",
        title_text: "cga:15",
        frame: "cga:7",
        icon: "cga:14",
        page_area: "cga:0",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        arrow_bg: "cga:0",
        arrow_fg: "cga:7",
        scroll_glyph: "cga:7",
        thumb_bg: "transparent",
        thumb_fg: "cga:14",
        code_bg: "cga:0",
        code_text: "cga:7",
    },
    bw03: {
        window: "cga:1",
        text: "cga:7",
        link: "cga:14",
        title: "cga:1",
        title_text: "cga:15",
        frame: "cga:7",
        icon: "cga:14",
        page_area: "cga:0",
        hover_bg: "cga:7",
        hover_fg: "cga:1",
        code_bg: "cga:0",
        code_text: "cga:7",
    },
    "norton-guide": {
        window: "cga:1",
        text: "cga:7",
        link: "cga:14",
        title: "cga:1",
        title_passive: "cga:1",
        title_text: "cga:15",
        frame: "cga:7",
        icon: "cga:14",
        page_area: "cga:1",
        hover_bg: "cga:7",
        hover_fg: "cga:1",
        arrow_bg: "cga:1",
        arrow_fg: "cga:11",
        scroll_glyph: "cga:11",
        thumb_bg: "transparent",
        thumb_fg: "cga:15",
        code_bg: "cga:1",
        code_text: "cga:7",
    },
    m602: {
        window: "cga:3",
        text: "cga:0",
        link: "cga:14",
        title: "cga:3",
        title_text: "cga:15",
        frame: "cga:15",
        icon: "cga:10",
        page_area: "cga:1",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        code_bg: "cga:1",
        code_text: "cga:14",
    },
    text602: {
        window: "cga:0",
        text: "cga:7",
        link: "cga:11",
        title: "cga:0",
        title_text: "cga:15",
        frame: "cga:7",
        icon: "cga:12",
        page_area: "cga:0",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        code_bg: "cga:0",
        code_text: "cga:7",
    },
    hlx: {
        window: "cga:3",
        text: "cga:0",
        link: "cga:14",
        title: "cga:3",
        title_text: "cga:15",
        frame: "cga:15",
        icon: "cga:10",
        page_area: "cga:1",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        code_bg: "cga:1",
        code_text: "cga:14",
    },
    tdh: {
        window: "cga:3",
        text: "cga:0",
        link: "cga:14",
        title: "cga:3",
        title_text: "cga:15",
        frame: "cga:15",
        icon: "cga:10",
        page_area: "cga:1",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        code_bg: "cga:1",
        code_text: "cga:14",
    },
    tfh: {
        window: "cga:3",
        text: "cga:0",
        link: "cga:14",
        title: "cga:3",
        title_text: "cga:15",
        frame: "cga:15",
        icon: "cga:10",
        page_area: "cga:1",
        hover_bg: "cga:1",
        hover_fg: "cga:14",
        code_bg: "cga:1",
        code_text: "cga:14",
    },
};

function bundleSourceFormat(bundle) {
    const metadata = bundle && typeof bundle === "object" ? (bundle.metadata || {}) : {};
    const source = metadata.source && typeof metadata.source === "object" ? metadata.source : {};
    const format = source.format || metadata.format;
    return typeof format === "string" ? format.trim().toLowerCase() : "";
}

function bundleUiThemeStyle(bundle) {
    const metadata = bundle && typeof bundle === "object" ? (bundle.metadata || {}) : {};
    const defaultTheme = DEFAULT_UHF_UI_BY_SOURCE_FORMAT[bundleSourceFormat(bundle)] || {};
    const explicitTheme = metadata.ui && typeof metadata.ui === "object" ? metadata.ui : {};
    const theme = { ...defaultTheme, ...explicitTheme };
    const declarations = [];
    Object.entries(UHF_UI_THEME_VARS).forEach(([key, cssVars]) => {
        const raw = theme[key];
        if (typeof raw !== "string" || !raw.trim()) {
            return;
        }
        const color = resolveUhfColor(bundle, raw);
        if (color) {
            const variables = Array.isArray(cssVars) ? cssVars : [cssVars];
            variables.forEach((cssVar) => declarations.push(`${cssVar}:${color}`));
        }
    });
    return declarations.join("; ");
}

function parseUhfLinkTargetSpec(rawTarget) {
    const targetText = String(rawTarget || "").trim();
    if (!targetText) {
        return null;
    }

    const target = {};
    let recognized = false;
    for (const part of targetText.split(",")) {
        const chunk = part.trim();
        if (!chunk || !chunk.includes("=")) {
            return null;
        }
        const eq = chunk.indexOf("=");
        const key = chunk.slice(0, eq).trim().toLowerCase();
        const value = chunk.slice(eq + 1).trim();
        if (!value) {
            continue;
        }
        if (key === "file") {
            target.file = value;
            recognized = true;
            continue;
        }
        if (key === "topic") {
            if (!/^-?\d+$/.test(value)) {
                return null;
            }
            target.topic = value;
            recognized = true;
            continue;
        }
        if (key === "alias") {
            target.alias = value;
            recognized = true;
            continue;
        }
        if (key === "line") {
            if (!/^\d+$/.test(value) || parseInt(value, 10) <= 0) {
                return null;
            }
            target.line = String(parseInt(value, 10));
            recognized = true;
        }
    }

    return recognized ? target : null;
}

function parseUhfTag(tagBody, bundle) {
    const lowered = tagBody.toLowerCase();
    if (lowered === "b") { return { name: "b", open: "<b>", close: "</b>", raw: tagBody }; }
    if (lowered === "i") { return { name: "i", open: "<i>", close: "</i>", raw: tagBody }; }
    if (lowered === "u") { return { name: "u", open: "<u>", close: "</u>", raw: tagBody }; }
    if (lowered === "r") { return { name: "r", open: '<span class="tv-uhf-reverse">', close: "</span>", raw: tagBody }; }

    let match = tagBody.match(/^link:(.+)$/i);
    if (match) {
        const linkTarget = parseUhfLinkTargetSpec(match[1]);
        if (!linkTarget) {
            return null;
        }
        const attrs = ['href="#"', 'data-tv-uhf-link="1"'];
        if (linkTarget.file) {
            attrs.push(`data-tv-source-file="${escapeHtml(linkTarget.file)}"`);
        }
        if (linkTarget.topic) {
            attrs.push(`data-tv-bundle-topic="${escapeHtml(linkTarget.topic)}"`);
        }
        if (linkTarget.alias) {
            attrs.push(`data-tv-topic-alias="${escapeHtml(linkTarget.alias)}"`);
        }
        if (linkTarget.line) {
            attrs.push(`data-tv-topic-line="${escapeHtml(linkTarget.line)}"`);
        }
        return {
            name: "link",
            open: `<a ${attrs.join(" ")}>`,
            close: "</a>",
            raw: tagBody,
        };
    }

    match = tagBody.match(/^nav:(back|contents|index)$/i);
    if (match) {
        return {
            name: "nav",
            open: `<a href="#" data-tv-nav="${escapeHtml(match[1].toLowerCase())}">`,
            close: "</a>",
            raw: tagBody,
        };
    }

    match = tagBody.match(/^fg[:=](.+)$/i);
    if (match) {
        const color = resolveUhfColor(bundle, match[1]);
        if (color) {
            return {
                name: "fg",
                open: `<span style="color:${color}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    match = tagBody.match(/^bg[:=](.+)$/i);
    if (match) {
        const color = resolveUhfColor(bundle, match[1]);
        if (color) {
            return {
                name: "bg",
                open: `<span style="background:${color}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    match = tagBody.match(/^color:(.+?)(?::(.+))?$/i);
    if (match) {
        const fg = resolveUhfColor(bundle, match[1]);
        const bg = match[2] != null ? resolveUhfColor(bundle, match[2]) : null;
        if (fg && (match[2] == null || bg)) {
            const styles = [`color:${fg}`];
            if (bg) {
                styles.push(`background:${bg}`);
            }
            return {
                name: "color",
                open: `<span style="${styles.join(";")}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    match = tagBody.match(/^color=(.+)$/i);
    if (match) {
        const fg = resolveUhfColor(bundle, match[1]);
        if (fg) {
            return {
                name: "color",
                open: `<span style="color:${fg}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    return null;
}

function renderUhfInline(text, bundle) {
    const root = { name: null, open: "", close: "", raw: "", children: [] };
    const stack = [root];

    function append(fragment) {
        stack[stack.length - 1].children.push(fragment);
    }

    let index = 0;
    while (index < text.length) {
        const open = text.indexOf("[", index);
        if (open < 0) {
            append(escapeHtml(text.slice(index)));
            break;
        }
        if (open > index) {
            append(escapeHtml(text.slice(index, open)));
        }
        if (text[open + 1] === "[") {
            append("[");
            index = open + 2;
            continue;
        }
        const close = text.indexOf("]", open + 1);
        if (close < 0) {
            append(escapeHtml(text.slice(open)));
            break;
        }
        const tagBody = text.slice(open + 1, close);
        if (tagBody.startsWith("/")) {
            const closeName = tagBody.slice(1).toLowerCase();
            if (stack.length > 1 && stack[stack.length - 1].name === closeName) {
                const node = stack.pop();
                append(node.open + node.children.join("") + node.close);
            } else {
                append(escapeHtml(text.slice(open, close + 1)));
            }
            index = close + 1;
            continue;
        }
        const descriptor = parseUhfTag(tagBody, bundle);
        if (!descriptor) {
            append(escapeHtml(text.slice(open, close + 1)));
            index = close + 1;
            continue;
        }
        stack.push({ ...descriptor, children: [] });
        index = close + 1;
    }

    while (stack.length > 1) {
        const node = stack.pop();
        stack[stack.length - 1].children.push(
            escapeHtml(`[${node.raw}]`) + node.children.join("")
        );
    }

    return root.children.join("");
}

function bundleFrozenRows(bundle, topic) {
    if (topic && Object.prototype.hasOwnProperty.call(topic, "frozen_rows")) {
        return Math.max(0, Number(topic.frozen_rows) || 0);
    }
    return Math.max(0, Number((bundle.metadata || {}).frozen_rows) || 0);
}

function wrapTopicLineMarkup(lineNumber, html, extraClass = "") {
    const classSuffix = extraClass ? ` ${extraClass}` : "";
    return `<span class="tv-topic-line${classSuffix}" data-tv-line="${lineNumber}">${html}</span>`;
}

function renderUhfTopicLines(topic, bundle) {
    const lines = [];
    const content = Array.isArray(topic && topic.content) ? topic.content : [];
    const downTarget = topic && topic.nav && topic.nav.Down
        ? normalizeTopicRef(bundle, topic.nav.Down.topic_id)
        : null;
    let inCodeBlock = false;
    let lineNumber = 0;

    content.forEach((line) => {
        const raw = String(line || "");
        if (isUhfCodeStart(line)) {
            inCodeBlock = true;
            return;
        }
        if (line === "[/code]") {
            inCodeBlock = false;
            return;
        }
        if (line === "[rule]") {
            lineNumber += 1;
            lines.push(wrapTopicLineMarkup(lineNumber, renderUhfRule(bundle), "tv-topic-line-rule"));
            return;
        }
        if (!inCodeBlock && raw.trim().toLowerCase() === "<more>" && downTarget) {
            lineNumber += 1;
            lines.push(wrapTopicLineMarkup(
                lineNumber,
                `<a href="#" data-tv-bundle-topic="${escapeHtml(downTarget)}">&lt;more&gt;</a>`,
            ));
            return;
        }
        if (inCodeBlock) {
            lineNumber += 1;
            if (!raw) {
                lines.push(
                    wrapTopicLineMarkup(
                        lineNumber,
                        '<span class="code-example code-example-empty">&nbsp;</span>'
                    )
                );
            } else {
                lines.push(
                    wrapTopicLineMarkup(
                        lineNumber,
                        `<span class="code-example">${renderUhfInline(raw, bundle)}</span>`
                    )
                );
            }
            return;
        }
        lineNumber += 1;
        lines.push(wrapTopicLineMarkup(lineNumber, renderUhfInline(raw, bundle)));
    });

    return lines;
}

function normalizedTopicTags(topic) {
    const tags = Array.isArray(topic && topic.tags) ? topic.tags : [];
    return tags.flatMap((tag) => {
        if (!tag || typeof tag !== "object") { return []; }
        const key = String(tag.key || "").trim();
        const value = String(tag.value || "").trim();
        if (!key || !value) { return []; }
        const label = String(tag.label || key).trim() || key;
        return [{ key, value, label }];
    });
}

function renderTopicTags(topic) {
    const tags = normalizedTopicTags(topic);
    if (!tags.length) { return ""; }
    const links = tags.map((tag) => {
        const attrs = renderHtmlAttributes({
            href: "#",
            "data-tv-topic-tag-key": tag.key,
            "data-tv-topic-tag-value": tag.value,
            "data-tv-topic-tag-label": tag.label,
        });
        return [
            '<span class="tv-topic-tag">',
            `<span class="tv-topic-tag-label">${escapeHtml(tag.label)}:</span> `,
            `<a ${attrs}>${escapeHtml(tag.value)}</a>`,
            "</span>",
        ].join("");
    });
    return `<div class="tv-topic-tags">${links.join("\n")}</div>`;
}

function renderUhfTopic(topic, bundle) {
    const lines = renderUhfTopicLines(topic, bundle);
    const title = bundleTopicTitle(bundle, topic);
    const metadata = bundle && typeof bundle === "object" ? (bundle.metadata || {}) : {};
    const titleHTML = title && metadata.show_topic_titles === true
        ? `<div class="tv-topic-heading">${escapeHtml(title)}</div>`
        : "";
    const tagHTML = renderTopicTags(topic);
    const frozenRows = Math.min(bundleFrozenRows(bundle, topic), lines.length);
    const fixedLayoutClass = bundleUsesFixedTopicLayout(bundle) ? " tv-topic-pre-fixed" : "";
    if (frozenRows > 0) {
        const frozenLines = lines.slice(0, frozenRows);
        const bodyLines = lines.slice(frozenRows);
        const html = [
            titleHTML,
            tagHTML,
            '<div class="tv-topic-shell">',
            `<pre class="tv-pre tv-topic-pre${fixedLayoutClass} tv-topic-pre-frozen">`,
            ...frozenLines,
            "</pre>",
        ];
        if (bodyLines.length) {
            html.push(
                `<pre class="tv-pre tv-topic-pre${fixedLayoutClass} tv-topic-pre-body">`,
                ...bodyLines,
                "</pre>",
            );
        }
        html.push("</div>");
        return html.join("\n");
    }

    return [
        titleHTML,
        tagHTML,
        `<pre class="tv-pre tv-topic-pre${fixedLayoutClass}">`,
        "",
        ...lines,
        "</pre>",
    ].join("\n");
}

function buildUhfSearchIndex(bundle) {
    if (Array.isArray(bundle._searchIndex)) {
        return bundle._searchIndex;
    }

    const indexTermsByTopic = new Map();
    flattenUhfIndexEntries(bundle).forEach((entry) => {
        const topicKey = String(entry.context_id);
        if (!indexTermsByTopic.has(topicKey)) {
            indexTermsByTopic.set(topicKey, []);
        }
        if (entry.label) {
            indexTermsByTopic.get(topicKey).push(entry.label);
        }
    });

    bundle._searchIndex = bundleTopicList(bundle).map((topic) => {
        const bodyLines = [];
        const content = Array.isArray(topic && topic.content) ? topic.content : [];
        let inCodeBlock = false;
        content.forEach((line) => {
            if (isUhfCodeStart(line)) {
                inCodeBlock = true;
                return;
            }
            if (line === "[/code]") {
                inCodeBlock = false;
                return;
            }
            if (inCodeBlock || line === "[rule]") {
                return;
            }
            const compact = normalizeSearchText(line);
            if (compact) {
                bodyLines.push(compact);
            }
        });
        normalizedTopicTags(topic).forEach((tag) => {
            bodyLines.push(normalizeSearchText(`${tag.label}: ${tag.value}`));
        });

        let preview = bodyLines.slice(0, 3).join(" ").trim();
        if (preview.length > 180) {
            preview = preview.slice(0, 177).trimEnd() + "...";
        }

        const topicKey = String(topic.id);
        return {
            context_id: topic.id,
            context_hex: topicKey,
            title: bundleTopicTitle(bundle, topic),
            preview,
            index_terms: Array.from(new Set(indexTermsByTopic.get(topicKey) || [])).sort(),
            text: bodyLines.join("\n"),
        };
    });

    return bundle._searchIndex;
}

// ── Window rendering ────────────────────────────────────────────────

// ── Loading progress dialog (DOS Navigator Copy style) ──────────────

const PROGRESS_BAR_WIDTH = 32;
const PROGRESS_BAR_ANIMATION_MS = 90;
const PROGRESS_BAR_MIN_VISIBLE_MS = 180;

class TVLoadingDialog {
    constructor(desktop) {
        const {
            TVDialog,
            TVStaticText,
            TVGroup,
            TVButtonStrip,
            TVButton: TVBtn,
        } = TV;
        this.desktop = desktop;
        this.cancelled = false;
        this.abortController = new AbortController();
        this.openedAt = 0;
        this.progressUpdates = 0;
        this.animationTimer = null;
        this.animationFrame = 0;
        this.destroyTimer = null;
        this.destroyed = false;


        const cancelButton = new TVBtn({
            x: 15, y: 5, w: 10,
            className: "is-default",
            attrs: { "data-tv-loading-cancel": true },
            labelMarkup: renderHotkeyMarkup("~C~ancel"),
        });

        const bodyGroup = new TVGroup({
            w: 38, h: 6,
            children: [
                new TVStaticText({ x: 0, y: 1, w: 38, align: "center", className: "tv-loading-filename", text: "" }),
                new TVStaticText({ x: 0, y: 2, w: 38, align: "center", className: "tv-loading-bar-line", text: "" }),
                new TVStaticText({ x: 0, y: 3, w: 38, align: "center", className: "tv-loading-percent", text: "0%" }),
                cancelButton,
            ],
        }).renderMarkup();

        this.dialog = new TVDialog({
            desktop,
            overlayClass: "tv-loading-overlay",
            ariaLabel: "Loading",
            title: "Loading",
            closeAttrs: { "data-tv-loading-close": true, "aria-label": "Cancel loading" },
            bodyMarkup: bodyGroup,
            footerMarkup: TVDialog.footerMarkup(),
            width: "40ch",
            height: "min(9em, calc(100% - 2em))",
            top: "5em",
            modal: true,
        });
        this.dialog.bindDrag();

        // Bind Cancel button
        const cancelEl = this.dialog.query("[data-tv-loading-cancel]");
        if (cancelEl) {
            cancelEl.addEventListener("click", () => this.cancel());
        }
        // Bind close [■] button
        this.dialog.bindCommonClose(() => this.cancel());

        this.filenameEl = this.dialog.query(".tv-loading-filename");
        this.barEl = this.dialog.query(".tv-loading-bar-line");
        this.percentEl = this.dialog.query(".tv-loading-percent");
    }

    get signal() {
        return this.abortController.signal;
    }

    show(filename) {
        if (this.filenameEl) { this.filenameEl.textContent = filename; }
        this.openedAt = performance.now();
        this.progressUpdates = 0;
        this._renderRatio(0, 1);
        this.dialog.open();
    }

    update(received, total) {
        if (received > 0) {
            this.progressUpdates += 1;
        }
        this._renderRatio(received, total);
    }

    _renderRatio(received, total) {
        const ratio = total > 0 ? Math.min(received / total, 1) : 0;
        const filled = Math.round(ratio * PROGRESS_BAR_WIDTH);
        const empty = PROGRESS_BAR_WIDTH - filled;
        if (this.barEl) {
            this.barEl.textContent = "█".repeat(filled) + "░".repeat(empty);
        }
        if (this.percentEl) {
            this.percentEl.textContent = `${Math.round(ratio * 100)}%`;
        }
    }

    _startIndeterminate() {
        this._stopIndeterminate();
        this.animationFrame = 0;
        this.animationTimer = window.setInterval(() => {
            const lead = this.animationFrame % PROGRESS_BAR_WIDTH;
            const cells = new Array(PROGRESS_BAR_WIDTH).fill("░");
            for (let index = 0; index < 6; index += 1) {
                cells[(lead + index) % PROGRESS_BAR_WIDTH] = "█";
            }
            this.animationFrame += 1;
            if (this.barEl) {
                this.barEl.textContent = cells.join("");
            }
        }, PROGRESS_BAR_ANIMATION_MS);
    }

    _stopIndeterminate() {
        if (this.animationTimer !== null) {
            window.clearInterval(this.animationTimer);
            this.animationTimer = null;
        }
    }

    _finalizeDestroy() {
        if (this.destroyed) {
            return;
        }
        this.destroyed = true;
        this._stopIndeterminate();
        if (this.destroyTimer !== null) {
            window.clearTimeout(this.destroyTimer);
            this.destroyTimer = null;
        }
        this.dialog.destroy();
    }

    cancel() {
        this.cancelled = true;
        this.abortController.abort();
        this.destroy(true);
    }

    close() {
        this.dialog.close();
    }

    destroy(immediate = false) {
        if (this.destroyed) {
            return;
        }
        this._stopIndeterminate();
        const elapsed = performance.now() - this.openedAt;
        const shouldDelay = !immediate && !this.cancelled && this.progressUpdates <= 1;
        const delay = shouldDelay ? Math.max(0, PROGRESS_BAR_MIN_VISIBLE_MS - elapsed) : 0;
        if (delay > 0) {
            if (this.destroyTimer !== null) {
                window.clearTimeout(this.destroyTimer);
            }
            this.destroyTimer = window.setTimeout(() => this._finalizeDestroy(), delay);
            return;
        }
        this._finalizeDestroy();
    }
}

// ── Window rendering ────────────────────────────────────────────────

function buildWindowHTML(bundle, contentHTML, caption) {
    const w = bundleWindowSpec(bundle);
    const themeStyle = bundleUiThemeStyle(bundle);
    const style = `--tv-window-cols:${w.cols}; --tv-window-rows:${w.rows}; --tv-window-min-cols:${w.min_cols}; --tv-window-min-rows:${w.min_rows};${themeStyle ? ` ${themeStyle};` : ""}`;
    return TVWindow.renderMarkup({
        attrs: { "data-tv-bundle-window": bundleWindowKey(bundle) },
        style,
        caption,
        contentMarkup: contentHTML,
        closeAttrs: { "data-tv-bundle-close": true },
        zoomAttrs: { "data-tv-bundle-zoom": true },
    });
}

// ── Index page rendering ────────────────────────────────────────────

function renderBundleIndex(bundle) {
    const navItems = [];
    const sections = [];
    const groups = Array.isArray(bundle.index) ? bundle.index : [];
    const byLetter = new Map(groups.map((group) => [String(group.group || ""), group]));
    if (byLetter.has("#")) {
        sections.push(renderIndexSection("#", "#", byLetter.get("#").entries || []));
    }
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((letter) => {
        const group = byLetter.get(letter);
        if (group && Array.isArray(group.entries) && group.entries.length) {
            navItems.push(`<a class="tv-index-jump" href="#" data-letter="${letter}">${letter}</a>`);
            sections.push(renderIndexSection(letter, letter, group.entries));
        } else {
            navItems.push(`<span class="tv-index-jump is-empty">${letter}</span>`);
        }
    });

    return [
        `<div class="tv-document tv-index-document">`,
        `<div class="tv-index-frozen">`,
        `<div class="tv-index-heading">Index</div>`,
        `<nav class="tv-index-nav">${navItems.join("")}</nav>`,
        `</div>`,
        ...sections,
        `</div>`,
    ].join("\n");
}

function renderIndexSection(anchor, label, entries) {
    const items = entries.map((entry) => {
        if (entry == null || entry.topic_id == null) {
            const targetAttrs = buildBundleTargetDataset(entry || {});
            if (!Object.keys(targetAttrs).length) {
                return `<div class="tv-index-entry"><span>${escapeHtml(entry && entry.label ? entry.label : "")}</span></div>`;
            }
            return `<div class="tv-index-entry"><a ${renderHtmlAttributes({ href: "#", ...targetAttrs })}>${escapeHtml(entry.label || "")}</a></div>`;
        }
        const targetAttrs = buildBundleTargetDataset({
            topic_id: entry.topic_id,
            file: entry.file,
            alias: entry.alias,
            line: entry.line,
        });
        return `<div class="tv-index-entry"><a ${renderHtmlAttributes({ href: "#", ...targetAttrs })}>${escapeHtml(entry.label)}</a></div>`;
    });
    return [
        `<section class="tv-index-section" id="idx-${escapeHtml(anchor)}">`,
        `<div class="tv-index-section-heading">`,
        `<span class="tv-index-section-label">${escapeHtml(label)}</span>`,
        `</div>`,
        `<div class="tv-index-section-body">`,
        ...items,
        `</div>`,
        `</section>`,
    ].join("\n");
}

function renderBundleContents(bundle) {
    const nodes = Array.isArray(bundle.contents) ? bundle.contents : [];
    return [
        `<div class="tv-document tv-index-document tv-contents-document">`,
        `<div class="tv-index-heading">Contents</div>`,
        `<div class="tv-contents-tree">`,
        renderContentsNodes(nodes),
        `</div>`,
        `</div>`,
    ].join("\n");
}

function renderBundleTagTopics(bundle, key, value, label) {
    const topics = bundleTopicList(bundle).filter((topic) => (
        normalizedTopicTags(topic).some((tag) => tag.key === key && tag.value === value)
    ));
    const entries = topics.map((topic) => {
        const attrs = renderHtmlAttributes({
            href: "#",
            "data-tv-bundle-topic": topic.id,
        });
        return `<div class="tv-index-entry"><a ${attrs}>${escapeHtml(bundleTopicTitle(bundle, topic))}</a></div>`;
    });
    if (!entries.length) {
        entries.push('<div class="tv-index-empty">No matching topics.</div>');
    }
    return [
        '<div class="tv-document tv-index-document tv-tag-document">',
        `<div class="tv-index-heading">${escapeHtml(label || key)}: ${escapeHtml(value)}</div>`,
        ...entries,
        "</div>",
    ].join("\n");
}

function buildBundleTargetDataset(target) {
    const attrs = {};
    if (target && target.topic_id != null) {
        attrs["data-tv-bundle-topic"] = String(target.topic_id);
    }
    if (target && target.file) {
        attrs["data-tv-source-file"] = String(target.file);
    }
    if (target && target.alias) {
        attrs["data-tv-topic-alias"] = String(target.alias);
    }
    if (target && target.line != null) {
        attrs["data-tv-topic-line"] = String(target.line);
    }
    return attrs;
}

function renderHtmlAttributes(attrs) {
    return Object.entries(attrs)
        .map(([key, value]) => `${key}="${escapeHtml(String(value))}"`)
        .join(" ");
}

function renderContentsNodes(nodes) {
    return nodes.map((node) => {
        const label = escapeHtml(String(node.label || ""));
        const targetAttrs = buildBundleTargetDataset(node);
        const labelHTML = Object.keys(targetAttrs).length
            ? `<a ${renderHtmlAttributes({ href: "#", "data-tv-uhf-link": "1", ...targetAttrs })}>${label}</a>`
            : label;
        const children = Array.isArray(node.children) && node.children.length
            ? `<div class="tv-contents-children">${renderContentsNodes(node.children)}</div>`
            : "";
        return [
            `<div class="tv-contents-node">`,
            `<div class="tv-contents-label">${labelHTML}</div>`,
            children,
            `</div>`,
        ].join("\n");
    }).join("\n");
}

// ── Topic navigation ────────────────────────────────────────────────

function findTopicByHex(bundle, contextHex) {
    const normalized = normalizeTopicRef(bundle, contextHex);
    if (!normalized) { return null; }
    return (bundle.topics && bundle.topics[normalized]) || null;
}

function renderTopicContent(bundle, topic) {
    return renderUhfTopic(topic, bundle);
}

// ── Window manager ──────────────────────────────────────────────────

function destroyWindowWidgets(windowEl) {
    if (!windowEl) { return; }
    if (windowEl._tvEditor) {
        windowEl._tvEditor.destroy();
        windowEl._tvEditor = null;
    }
    const scrollbars = Array.isArray(windowEl._tvScrollbars) ? windowEl._tvScrollbars : [];
    scrollbars.forEach((scrollbar) => scrollbar.destroy());
    windowEl._tvScrollbars = [];
    if (windowEl._tvResizer) {
        windowEl._tvResizer.destroy();
        windowEl._tvResizer = null;
    }
}

class BundleWindowManager {
    constructor(desktop, onNavigate) {
        this.desktop = desktop;
        this.onNavigate = onNavigate || null;
        this.dialogManager = null;
        this.openWindows = new Map(); // source_name → DOM element
        this.scrollbars = [];
        this.resizers = [];
        this.history = []; // { bundle, contextHex | null, lineNumber | null }
        this.currentBundle = null;
        this.currentContextHex = null;
        this.currentLineNumber = null;
        this.currentView = "index";
        this.currentTag = null;
    }

    showIndex(bundle) {
        // If the UHF2 bundle has no index entries, show the first available topic
        // instead of an empty index page.
        if (!bundleHasIndexEntries(bundle)) {
            const fallback = bundleFirstTopicRef(bundle);
            if (fallback) {
                this.showTopic(bundle, fallback);
                return;
            }
        }
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = null;
        this.currentLineNumber = null;
        this.currentView = "index";
        this.currentTag = null;
        const contentHTML = wrapBundleContent(bundle, renderBundleIndex(bundle));
        this._openWindow(bundle, contentHTML, bundleHeaderLabel(bundle));
        if (this.onNavigate) { this.onNavigate("Index"); }
    }

    showTopic(bundle, contextHex, lineNumber = null) {
        const normalized = normalizeTopicRef(bundle, contextHex);
        const topic = normalized ? ((bundle.topics && bundle.topics[normalized]) || null) : null;
        if (!topic) {
            console.warn(`Topic not found: ${contextHex}`);
            return false;
        }
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = normalized;
        this.currentLineNumber = this._normalizeLineNumber(lineNumber);
        this.currentView = "topic";
        this.currentTag = null;
        const contentHTML = wrapBundleContent(bundle, renderTopicContent(bundle, topic));
        const windowEl = this._openWindow(bundle, contentHTML, bundleHeaderLabel(bundle));
        this._focusTopicLine(windowEl, this.currentLineNumber);
        if (this.onNavigate) { this.onNavigate(bundleTopicTitle(bundle, topic)); }
        return true;
    }

    showHelpContentsTopic(bundle) {
        const helpContentsTopic = bundleHelpContentsTopicRef(bundle);
        if (helpContentsTopic) {
            this.showTopic(bundle, helpContentsTopic);
        }
    }

    showDefault(bundle, lineNumber = null) {
        const helpContentsTopic = bundleHelpContentsTopicRef(bundle);
        if (helpContentsTopic) {
            this.showTopic(bundle, helpContentsTopic, lineNumber);
            return;
        }
        this.showIndex(bundle);
    }

    showContents(bundle) {
        if (Array.isArray(bundle.contents) && bundle.contents.length) {
            this._pushHistory();
            this.currentBundle = bundle;
            this.currentContextHex = null;
            this.currentLineNumber = null;
            this.currentView = "contents";
            this.currentTag = null;
            this._openWindow(bundle, wrapBundleContent(bundle, renderBundleContents(bundle)), bundleHeaderLabel(bundle));
            if (this.onNavigate) { this.onNavigate("Contents"); }
            return;
        }
        const fallback = bundleTopicFallbackRef(bundle);
        if (fallback) {
            this.showTopic(bundle, fallback);
            return;
        }
    }

    showTag(bundle, key, value, label = "") {
        const normalizedKey = String(key || "").trim();
        const normalizedValue = String(value || "").trim();
        if (!normalizedKey || !normalizedValue) { return false; }
        const normalizedLabel = String(label || normalizedKey).trim() || normalizedKey;
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = null;
        this.currentLineNumber = null;
        this.currentView = "tag";
        this.currentTag = { key: normalizedKey, value: normalizedValue, label: normalizedLabel };
        const contentHTML = wrapBundleContent(
            bundle,
            renderBundleTagTopics(bundle, normalizedKey, normalizedValue, normalizedLabel),
        );
        this._openWindow(bundle, contentHTML, bundleHeaderLabel(bundle));
        if (this.onNavigate) { this.onNavigate(`${normalizedLabel}: ${normalizedValue}`); }
        return true;
    }

    async openSourceTopic(sourceFile, topicRef, lineNumber = null, fallbackBundle = null) {
        const showFallback = (bundle, fallback) => {
            if (!bundle || !fallback) {
                return false;
            }
            if (fallback.type === "topic" && fallback.ref) {
                this.showTopic(bundle, fallback.ref, lineNumber);
                return true;
            }
            if (fallback.type === "index") {
                this.showIndex(bundle);
                return true;
            }
            if (fallback.type === "contents") {
                this.showContents(bundle);
                return true;
            }
            return false;
        };

        const entry = findCatalogEntryBySourceFile(sourceFile, fallbackBundle || this.currentBundle);
        if (!entry) {
            if (showFallback(fallbackBundle, resolveMissingSourceTopicFallback(fallbackBundle, sourceFile, topicRef))) {
                return;
            }
            console.warn(`Bundle not found for source file: ${sourceFile}`);
            return;
        }
        const bundle = await loadBundle(entry.file);
        const normalizedTopic = topicRef != null ? String(topicRef).trim() : "";
        const resolvedTopic = normalizedTopic ? normalizeTopicRef(bundle, normalizedTopic) : null;
        if (resolvedTopic) {
            this.showTopic(bundle, resolvedTopic, lineNumber);
            return;
        }
        if (showFallback(bundle, resolveMissingSourceTopicFallback(bundle, sourceFile, normalizedTopic))) {
            return;
        }
        const fallback = bundleTopicFallbackRef(bundle);
        if (fallback) {
            this.showTopic(bundle, fallback, lineNumber);
            return;
        }
        this.showContents(bundle);
    }

    _normalizeLineNumber(value) {
        const numeric = Number(value);
        if (Number.isInteger(numeric) && numeric > 0) {
            return numeric;
        }
        return null;
    }

    _focusTopicLine(windowEl, lineNumber) {
        const normalized = this._normalizeLineNumber(lineNumber);
        if (!windowEl || !normalized) {
            return;
        }
        const viewport = windowEl.querySelector("[data-tv-viewport]");
        const targetLine = windowEl.querySelector(`[data-tv-line="${normalized}"]`);
        if (!viewport || !targetLine) {
            return;
        }
        windowEl.querySelectorAll(".tv-topic-line.is-target").forEach((line) => {
            line.classList.remove("is-target");
        });
        targetLine.classList.add("is-target");
        const targetTop = targetLine.offsetTop;
        const padding = Math.max(targetLine.offsetHeight * 2, 16);
        viewport.scrollTop = Math.max(0, targetTop - padding);
    }

    _pushHistory() {
        if (this.currentBundle) {
            this.history.push({
                bundle: this.currentBundle,
                contextHex: this.currentContextHex,
                lineNumber: this.currentLineNumber,
                view: this.currentView,
                tag: this.currentTag ? { ...this.currentTag } : null,
            });
        }
    }

    goBack() {
        const prev = this.history.pop();
        if (!prev) { return; }
        // Restore without pushing to history again
        this.currentBundle = prev.bundle;
        this.currentContextHex = prev.contextHex;
        this.currentLineNumber = this._normalizeLineNumber(prev.lineNumber);
        this.currentView = prev.view || (prev.contextHex ? "topic" : "index");
        this.currentTag = prev.tag || null;
        if (prev.contextHex) {
            const topic = findTopicByHex(prev.bundle, prev.contextHex);
            if (topic) {
                const contentHTML = wrapBundleContent(prev.bundle, renderTopicContent(prev.bundle, topic));
                const windowEl = this._openWindow(prev.bundle, contentHTML, bundleHeaderLabel(prev.bundle));
                this._focusTopicLine(windowEl, this.currentLineNumber);
                if (this.onNavigate) { this.onNavigate(bundleTopicTitle(prev.bundle, topic)); }
            }
        } else if (this.currentView === "contents") {
            this.currentLineNumber = null;
            const contentHTML = wrapBundleContent(prev.bundle, renderBundleContents(prev.bundle));
            this._openWindow(prev.bundle, contentHTML, bundleHeaderLabel(prev.bundle));
            if (this.onNavigate) { this.onNavigate("Contents"); }
        } else if (this.currentView === "tag" && this.currentTag) {
            this.currentLineNumber = null;
            const { key, value, label } = this.currentTag;
            const contentHTML = wrapBundleContent(prev.bundle, renderBundleTagTopics(prev.bundle, key, value, label));
            this._openWindow(prev.bundle, contentHTML, bundleHeaderLabel(prev.bundle));
            if (this.onNavigate) { this.onNavigate(`${label}: ${value}`); }
        } else {
            this.currentLineNumber = null;
            const contentHTML = wrapBundleContent(prev.bundle, renderBundleIndex(prev.bundle));
            this._openWindow(prev.bundle, contentHTML, bundleHeaderLabel(prev.bundle));
            if (this.onNavigate) { this.onNavigate("Index"); }
        }
    }

    syncActiveTarget(target) {
        if (!String(target || "").startsWith("help:")) {
            return null;
        }
        const key = String(target).slice(5);
        const windowEl = this.openWindows.get(key);
        const bundle = windowEl?._tvBundle || null;
        if (!windowEl || !bundle) {
            return null;
        }
        this.currentBundle = bundle;
        this.currentContextHex = windowEl.dataset.tvStateTopic || null;
        this.currentLineNumber = this._normalizeLineNumber(windowEl.dataset.tvStateLine);
        this.currentView = windowEl.dataset.tvStateView || "index";
        this.currentTag = windowEl.dataset.tvStateTagKey && windowEl.dataset.tvStateTagValue
            ? {
                key: windowEl.dataset.tvStateTagKey,
                value: windowEl.dataset.tvStateTagValue,
                label: windowEl.dataset.tvStateTagLabel || windowEl.dataset.tvStateTagKey,
            }
            : null;
        return bundle;
    }

    _openWindow(bundle, contentHTML, caption) {
        const key = bundleWindowKey(bundle);
        const applyStateData = (windowEl) => {
            windowEl.dataset.tvStateType = "h";
            windowEl.dataset.tvStateFile = bundle._catalogFile || "";
            windowEl.dataset.tvStateView = this.currentView || "index";
            windowEl.dataset.tvStateTopic = this.currentContextHex || "";
            windowEl.dataset.tvStateLine = this.currentLineNumber ? String(this.currentLineNumber) : "";
            if (this.currentTag) {
                windowEl.dataset.tvStateTagKey = this.currentTag.key || "";
                windowEl.dataset.tvStateTagValue = this.currentTag.value || "";
                windowEl.dataset.tvStateTagLabel = this.currentTag.label || "";
            } else {
                delete windowEl.dataset.tvStateTagKey;
                delete windowEl.dataset.tvStateTagValue;
                delete windowEl.dataset.tvStateTagLabel;
            }
        };
        const existing = this.openWindows.get(key);
        if (existing) {
            existing._tvBundle = bundle;
            // Update content in existing window
            const viewport = existing.querySelector("[data-tv-viewport]");
            if (viewport) {
                viewport.innerHTML = contentHTML;
                viewport.scrollTop = 0;
                viewport.scrollLeft = 0;
                (existing._tvScrollbars || []).forEach((scrollbar) => scrollbar.refresh());
            }
            const captionEl = existing.querySelector(".tv-window-caption");
            if (captionEl) {
                captionEl.textContent = caption;
            }
            highlightCodeExamples(existing);
            this._bindTopicLinks(existing, bundle);
            applyStateData(existing);
            if (this.dialogManager) { this.dialogManager.activateWindow("help:" + key); }
            fillBorders();
            return existing;
        }

        const windowHTML = buildWindowHTML(bundle, contentHTML, caption);
        const template = document.createElement("template");
        template.innerHTML = windowHTML.trim();
        const windowEl = template.content.firstElementChild;
        windowEl._tvBundle = bundle;
        windowEl.dataset.tvWindowStorageKey = "help:" + key;
        this.desktop.appendChild(windowEl);
        bindCloseButtons(windowEl);
        this.openWindows.set(key, windowEl);
        applyStateData(windowEl);
        this._initWindowWidgets(windowEl);
        highlightCodeExamples(windowEl);
        this._bindTopicLinks(windowEl, bundle);
        this._bindCloseButton(windowEl, key);
        this._bindZoomButton(windowEl);
        if (this.dialogManager) {
            this.dialogManager.registerWindow("help:" + key, windowEl, {
                [TV_COMMANDS.CLOSE]: () => this.close(key),
                [TV_COMMANDS.ZOOM]: () => this.toggleZoom(windowEl),
            });
        }
        fillBorders();
        fillDesktopPatterns();
        return windowEl;
    }

    _initWindowWidgets(windowEl) {
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        windowEl._tvScrollbars = Array.from(frames, (frame) => new TVScrollBar(frame));
        this.scrollbars.push(...windowEl._tvScrollbars);
        const resizer = new TurboVisionWindowResizer(windowEl);
        windowEl._tvResizer = resizer;
        this.resizers.push(resizer);
    }

    _destroyWindowWidgets(windowEl) {
        const scrollbars = Array.isArray(windowEl?._tvScrollbars) ? windowEl._tvScrollbars : [];
        const resizer = windowEl?._tvResizer || null;
        destroyWindowWidgets(windowEl);
        this.scrollbars = this.scrollbars.filter((widget) => !scrollbars.includes(widget));
        this.resizers = this.resizers.filter((widget) => widget !== resizer);
    }

    _bindTopicLinks(windowEl, bundle) {
        if (windowEl.dataset.tvBundleLinksBound === "1") { return; }
        windowEl.dataset.tvBundleLinksBound = "1";
        windowEl.addEventListener("click", async (event) => {
            const navLink = event.target.closest("[data-tv-nav]");
            if (navLink && windowEl.contains(navLink)) {
                event.preventDefault();
                const action = (navLink.getAttribute("data-tv-nav") || "").toLowerCase();
                if (action === "back") {
                    this.goBack();
                } else if (action === "index") {
                    this.showIndex(bundle);
                } else if (action === "contents") {
                    this.showContents(bundle);
                }
                return;
            }

            const letterLink = event.target.closest("a[data-letter]");
            if (letterLink && windowEl.contains(letterLink)) {
                event.preventDefault();
                const letter = letterLink.getAttribute("data-letter");
                const section = document.getElementById(`idx-${letter}`);
                if (section) {
                    section.scrollIntoView({ behavior: "smooth", block: "start" });
                }
                return;
            }

            const tagLink = event.target.closest("[data-tv-topic-tag-key]");
            if (tagLink && windowEl.contains(tagLink)) {
                event.preventDefault();
                this.showTag(
                    bundle,
                    tagLink.dataset.tvTopicTagKey,
                    tagLink.dataset.tvTopicTagValue,
                    tagLink.dataset.tvTopicTagLabel,
                );
                return;
            }

            const link = event.target.closest(
                "[data-tv-uhf-link], [data-tv-bundle-topic], [data-tv-topic-alias], [data-tv-source-file]"
            );
            if (!link || !windowEl.contains(link)) { return; }

            event.preventDefault();
            const sourceFile = link.dataset.tvSourceFile || "";
            const lineNumber = this._normalizeLineNumber(link.dataset.tvTopicLine);
            const topicRef = (link.dataset.tvBundleTopic || link.dataset.tvTopicAlias || "").trim();
            try {
                if (sourceFile) {
                    await this.openSourceTopic(sourceFile, topicRef, lineNumber, bundle);
                } else if (topicRef) {
                    this.showTopic(bundle, topicRef, lineNumber);
                } else if (lineNumber) {
                    this._pushHistory();
                    this._focusTopicLine(windowEl, lineNumber);
                    this.currentLineNumber = lineNumber;
                    if (this.onNavigate) { this.onNavigate(""); }
                }
            } catch (error) {
                console.error("Failed to open linked topic", error);
            }
        });
    }

    _bindCloseButton(windowEl, key) {
        const closeBtn = windowEl.querySelector("[data-tv-bundle-close]");
        if (!closeBtn) { return; }
        closeBtn.addEventListener("click", (event) => {
            event.preventDefault();
            this.close(key);
        });
    }

    _bindZoomButton(windowEl) {
        const zoomBtn = windowEl.querySelector("[data-tv-bundle-zoom]");
        if (!zoomBtn) { return; }
        zoomBtn.addEventListener("click", (event) => {
            event.preventDefault();
            this.toggleZoom(windowEl);
        });
    }

    toggleZoom(windowEl) {
        if (!windowEl) {
            // Zoom the first open window
            const first = this.openWindows.values().next().value;
            if (!first) { return; }
            windowEl = first;
        }
        const isMax = windowEl.classList.toggle("is-maximized");
        const glyph = windowEl.querySelector("[data-tv-zoom-glyph]");
        if (glyph) {
            glyph.textContent = isMax ? "↓" : "↑";
        }
        fillBorders();
        fillDesktopPatterns();
    }

    close(key) {
        const existing = this.openWindows.get(key);
        if (existing) {
            this._destroyWindowWidgets(existing);
            existing.remove();
            this.openWindows.delete(key);
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + key); }
            if (this.currentBundle && bundleWindowKey(this.currentBundle) === key) {
                this.currentBundle = null;
                this.currentContextHex = null;
                this.currentLineNumber = null;
                this.currentView = "index";
                this.currentTag = null;
            }
            fillBorders();
            fillDesktopPatterns();
            if (this.onNavigate) { this.onNavigate(""); }
        }
    }

    closeAll() {
        for (const [key, el] of this.openWindows) {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + key); }
            this._destroyWindowWidgets(el);
            el.remove();
        }
        this.openWindows.clear();
        this.history = [];
        this.currentBundle = null;
        this.currentContextHex = null;
        this.currentView = "index";
        this.currentTag = null;
        if (this.onNavigate) { this.onNavigate(""); }
    }

    tile() {
        const all = this.dialogManager ? [...this.dialogManager.windows.values()] : [...this.openWindows.values()];
        if (all.length === 0) { return; }
        const cell = TV.measureCells ? TV.measureCells() : { width: 9, height: 16 };
        const dw = this.desktop.clientWidth;
        const dh = this.desktop.clientHeight;
        const cols = Math.ceil(Math.sqrt(all.length));
        const rows = Math.ceil(all.length / cols);
        const wCols = Math.floor(dw / cell.width / cols);
        const wRows = Math.floor(dh / cell.height / rows);
        all.forEach((el, i) => {
            const col = i % cols;
            const row = Math.floor(i / cols);
            el.classList.remove("is-maximized");
            el.style.setProperty("--tv-window-left", `${col * wCols * cell.width}px`);
            el.style.setProperty("--tv-window-top", `${row * wRows * cell.height}px`);
            el.style.setProperty("--tv-window-cols", String(wCols));
            el.style.setProperty("--tv-window-rows", String(wRows));
            const g = el.querySelector("[data-tv-zoom-glyph]");
            if (g) { g.textContent = "↑"; }
            if (el._tvResizer) {
                el._tvResizer.restoreSnapshot = el._tvResizer.captureGeometry();
                el._tvResizer.persistState();
            }
        });
        fillBorders();
        fillDesktopPatterns();
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
    }

    cascade() {
        const all = this.dialogManager ? [...this.dialogManager.windows.values()] : [...this.openWindows.values()];
        if (all.length === 0) { return; }
        const cell = TV.measureCells ? TV.measureCells() : { width: 9, height: 16 };
        const dw = this.desktop.clientWidth;
        const dh = this.desktop.clientHeight;
        const baseCols = Math.floor(dw / cell.width * 0.75);
        const baseRows = Math.floor(dh / cell.height * 0.75);
        const step = 2; // cells offset per window
        all.forEach((el, i) => {
            el.classList.remove("is-maximized");
            el.style.setProperty("--tv-window-left", `${i * step * cell.width}px`);
            el.style.setProperty("--tv-window-top", `${i * step * cell.height}px`);
            el.style.setProperty("--tv-window-cols", String(baseCols));
            el.style.setProperty("--tv-window-rows", String(baseRows));
            const g = el.querySelector("[data-tv-zoom-glyph]");
            if (g) { g.textContent = "↑"; }
            if (el._tvResizer) {
                el._tvResizer.restoreSnapshot = el._tvResizer.captureGeometry();
                el._tvResizer.persistState();
            }
        });
        fillBorders();
        fillDesktopPatterns();
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
    }

}

// ── Catalog menu items ──────────────────────────────────────────────

function renderMenuPopupSeparator() {
    return '<div class="tv-menu-popup-separator" aria-hidden="true">'
        + '<span class="tv-border-corner">├</span>'
        + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
        + '<span class="tv-border-corner">┤</span>'
        + '</div>';
}

function renderMenuPopup(items, attrs = {}, className = "tv-menu-popup") {
    return new TVMenuBox({ className, attrs, items }).renderMarkup();
}

function renderMenuSubmenu(labelMarkup, items) {
    return [
        `<div class="tv-submenu-root" data-tv-submenu-root="true">`,
        `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle="true">`,
        `${labelMarkup}<span class="tv-submenu-arrow">►</span>`,
        `</button>`,
        renderMenuPopup(items, { "data-tv-submenu-popup": true, hidden: true }, "tv-menu-popup tv-submenu-popup"),
        `</div>`,
    ].join("");
}

function renderMenuRoot(labelMarkup, items, rootAttrs = {}) {
    const rootMarkup = renderHtmlAttributes({
        class: "tv-menu-root",
        "data-tv-menu-root": "true",
        ...rootAttrs,
    });
    const toggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup,
    }).renderMarkup();
    return [
        `<div ${rootMarkup}>`,
        toggle,
        renderMenuPopup(items, { "data-tv-menu-popup": true, hidden: true }),
        `</div>`,
    ].join("");
}

function splitGroupedMenuEntries(entries) {
    const groups = new Map();
    const ungrouped = [];
    entries.forEach((entry) => {
        const group = entry.group || "";
        if (!group) {
            ungrouped.push(entry);
            return;
        }
        if (!groups.has(group)) {
            groups.set(group, []);
        }
        groups.get(group).push(entry);
    });
    return { groups, ungrouped };
}

function buildGroupedMenuItems(entries, renderItem) {
    if (!entries.length) {
        return [];
    }

    const { groups, ungrouped } = splitGroupedMenuEntries(entries);
    const items = [];
    let needSep = false;

    ungrouped.forEach((entry) => {
        items.push(renderItem(entry));
        needSep = true;
    });

    groups.forEach((groupEntries, group) => {
        if (needSep) {
            items.push(renderMenuPopupSeparator());
        }
        items.push(renderMenuSubmenu(
            escapeHtml(group),
            groupEntries.map((entry) => renderItem(entry)),
        ));
        needSep = false;
    });

    return items;
}

function catalogMenuEntryButton(entry) {
    return new TVButton({
        dialog: false,
        className: "tv-menu-popup-item",
        attrs: { type: "button", "data-tv-bundle-open": entry.file, "data-tv-bundle-label": bundleLoadingLabel(entry) },
        labelMarkup: escapeHtml(entry.menu_name || entry.name),
    });
}

function catalogProductLabel(entry) {
    return String(entry.product_name || "").trim();
}

function catalogVersionLabel(entry) {
    return String(entry.version || "").trim();
}

function catalogTreeNode(map, ordered, key) {
    if (!map.has(key)) {
        const node = { key, direct: [], versionMap: new Map(), versions: [] };
        map.set(key, node);
        ordered.push(node);
    }
    return map.get(key);
}

function buildCatalogMenuItems(catalog) {
    const openItem = new TVButton({
        dialog: false,
        className: "tv-menu-popup-item",
        attrs: { type: "button", "data-tv-file-open": true },
        labelMarkup: renderHotkeyMarkup("~O~pen..."),
    });
    const changeDirectoryItem = new TVButton({
        dialog: false,
        className: "tv-menu-popup-item",
        attrs: { type: "button", "data-tv-dialog-open": "chdir" },
        labelMarkup: renderHotkeyMarkup("~C~hange dir..."),
    });
    if (!catalog.length) { return [openItem, changeDirectoryItem]; }

    const directItems = [];
    const productMap = new Map();
    const products = [];

    catalog.forEach((entry) => {
        const product = catalogProductLabel(entry);
        if (!product) {
            directItems.push(catalogMenuEntryButton(entry));
            return;
        }

        const productNode = catalogTreeNode(productMap, products, product);
        const version = catalogVersionLabel(entry);
        if (!version) {
            productNode.direct.push(catalogMenuEntryButton(entry));
            return;
        }

        const versionNode = catalogTreeNode(productNode.versionMap, productNode.versions, version);
        versionNode.direct.push(catalogMenuEntryButton(entry));
    });

    const items = [openItem, changeDirectoryItem, renderMenuPopupSeparator(), ...directItems];
    if (directItems.length && products.length) {
        items.push(renderMenuPopupSeparator());
    }
    products.forEach((productNode) => {
        const productItems = [...productNode.direct];
        if (productItems.length && productNode.versions.length) {
            productItems.push(renderMenuPopupSeparator());
        }
        productNode.versions.forEach((versionNode) => {
            productItems.push(renderMenuSubmenu(escapeHtml(versionNode.key), versionNode.direct));
        });
        items.push(renderMenuSubmenu(escapeHtml(productNode.key), productItems));
    });
    return items;
}

function buildDocsMenuItems(docs) {
    return buildGroupedMenuItems(docs, (entry) =>
        new TVButton({
            dialog: false,
            className: "tv-menu-popup-item",
            attrs: { type: "button", "data-tv-doc-open": entry.file },
            labelMarkup: escapeHtml(entry.name),
        })
    );
}

function buildBundleContentsMenuItems(nodes) {
    if (!Array.isArray(nodes)) { return []; }
    const items = [];

    nodes.forEach((node) => {
        const label = String((node && node.label) || "").trim();
        if (!label) { return; }

        const childItems = buildBundleContentsMenuItems(node.children || []);
        const targetAttrs = buildBundleTargetDataset(node);
        const hasTarget = Object.keys(targetAttrs).length > 0;
        const labelMarkup = renderBundleMenuLabel(label, node && node.hotkey);

        if (childItems.length) {
            const subItems = [];
            if (hasTarget) {
                subItems.push(new TVButton({
                    dialog: false,
                    className: "tv-menu-popup-item",
                    attrs: { type: "button", "data-tv-menu-link": "1", ...targetAttrs },
                    labelMarkup,
                }));
                subItems.push(renderMenuPopupSeparator());
            }
            subItems.push(...childItems);
            items.push(renderMenuSubmenu(labelMarkup, subItems));
            return;
        }

        if (hasTarget) {
            items.push(new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-menu-link": "1", ...targetAttrs },
                labelMarkup,
            }));
            return;
        }

        items.push(`<div class="tv-menu-popup-item is-disabled">${escapeHtml(label)}</div>`);
    });

    return items;
}

function renderBundleMenuLabel(label, hotkey = "") {
    const cleanLabel = String(label || "");
    const cleanHotkey = String(hotkey || "").trim();
    if (!cleanHotkey) {
        return escapeHtml(cleanLabel);
    }
    const matchIndex = cleanLabel.toLowerCase().indexOf(cleanHotkey.toLowerCase());
    if (matchIndex < 0) {
        return escapeHtml(cleanLabel);
    }
    const markedLabel = cleanLabel.slice(0, matchIndex)
        + "~" + cleanLabel[matchIndex] + "~"
        + cleanLabel.slice(matchIndex + 1);
    return renderHotkeyMarkup(markedLabel);
}

function buildBundleContentsMenuRoot(bundle) {
    const sourceFormat = bundleSourceFormat(bundle);
    const rawNodes = Array.isArray(bundle && bundle.contents) ? bundle.contents : [];
    const nodes = sourceFormat === "bw03"
        ? rawNodes.map((node) => ({ ...(node || {}), children: [] }))
        : rawNodes;
    if (!nodes.length) {
        return "";
    }

    const items = buildBundleContentsMenuItems(nodes);
    if (!items.length) {
        return "";
    }

    return renderMenuRoot(
        renderHotkeyMarkup(nodes.some((node) => node && node.hotkey) ? "~M~enu" : "~C~ontents"),
        items,
        { "data-tv-bundle-menu-root": "true" },
    );
}

// ── Minimal Markdown → HTML renderer ────────────────────────────────

function renderMarkdown(md) {
    const lines = md.replace(/\r\n?/g, "\n").split("\n");
    const html = [];
    let inCode = false;
    let codeLines = null;
    let inList = false;
    let listTag = "";
    let inTable = false;

    function isSafeMarkdownHref(href) {
        const value = String(href || "").trim();
        if (!value || /[\u0000-\u001f\u007f]/.test(value)) { return false; }
        const scheme = value.match(/^([a-z][a-z0-9+.-]*):/i);
        return !scheme || ["http", "https", "mailto"].includes(scheme[1].toLowerCase());
    }

    function inlineMarkup(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
            .replace(/\*([^*]+)\*/g, '<i>$1</i>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => {
                if (!isSafeMarkdownHref(href)) { return label; }
                const safeHref = href.trim().replace(/"/g, "&quot;");
                return `<a href="${safeHref}" target="_blank" rel="noopener">${label}</a>`;
            });
    }

    function closeList() {
        if (inList) { html.push(`</${listTag}>`); inList = false; }
    }
    function closeTable() {
        if (inTable) { html.push("</tbody></table>"); inTable = false; }
    }

    function isTableRow(line) { return line.trim().startsWith("|") && line.trim().endsWith("|"); }
    function isSepRow(line) { return /^\|[-:\s|]+\|$/.test(line.trim()); }
    function splitTableCells(line) {
        const row = line.trim().replace(/^\|/, "").replace(/\|$/, "");
        const cells = [];
        let cell = "";
        let inCode = false;
        for (let i = 0; i < row.length; i++) {
            const char = row[i];
            if (char === "`") {
                inCode = !inCode;
                cell += char;
            } else if (char === "\\" && row[i + 1] === "|") {
                cell += "|";
                i++;
            } else if (char === "|" && !inCode) {
                cells.push(cell);
                cell = "";
            } else {
                cell += char;
            }
        }
        cells.push(cell);
        return cells;
    }
    function parseRow(line, tag) {
        const cells = splitTableCells(line);
        return "<tr>" + cells.map((c) => `<${tag}>${inlineMarkup(c.trim())}</${tag}>`).join("") + "</tr>";
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Fenced code block
        if (line.startsWith("```") ) {
            if (inCode) {
                // End code block
                html.push("<pre>" + codeLines.join("\n") + "</pre>");
                codeLines = null;
                inCode = false;
            } else {
                closeList(); closeTable();
                codeLines = [];
                inCode = true;
            }
            continue;
        }
        if (inCode) {
            codeLines.push(line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"));
            continue;
        }
        // Table: header row followed by separator row
        if (!inTable && isTableRow(line) && i + 1 < lines.length && isSepRow(lines[i + 1])) {
            closeList();
            html.push("<table>");
            html.push("<thead>" + parseRow(line, "th") + "</thead>");
            html.push("<tbody>");
            inTable = true;
            i++; // skip separator row
            continue;
        }
        if (inTable) {
            if (isTableRow(line)) { html.push(parseRow(line, "td")); continue; }
            closeTable();
        }
        // Blank → close list, add empty paragraph for spacing
        if (!line.trim()) { closeList(); html.push("<p></p>"); continue; }
        // Headings
        const hMatch = line.match(/^(#{1,6})\s+(.*)/);
        if (hMatch) {
            closeList();
            const level = hMatch[1].length;
            html.push(`<h${level}>${inlineMarkup(hMatch[2])}</h${level}>`);
            continue;
        }
        // Horizontal rule
        if (/^[-*_]{3,}\s*$/.test(line)) { closeList(); html.push("<hr>"); continue; }
        // Unordered list
        const ulMatch = line.match(/^(\s*)[-*+]\s+(.*)/);
        if (ulMatch) {
            if (!inList || listTag !== "ul") { closeList(); html.push("<ul>"); inList = true; listTag = "ul"; }
            html.push(`<li>${inlineMarkup(ulMatch[2])}</li>`);
            continue;
        }
        // Ordered list
        const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
        if (olMatch) {
            if (!inList || listTag !== "ol") { closeList(); html.push("<ol>"); inList = true; listTag = "ol"; }
            html.push(`<li>${inlineMarkup(olMatch[2])}</li>`);
            continue;
        }
        // List continuation: indented line appended to last <li>
        if (inList && /^\s{2,}/.test(line)) {
            const last = html.length - 1;
            if (last >= 0 && html[last].startsWith("<li>")) {
                html[last] = html[last].replace(/<\/li>$/, ` ${inlineMarkup(line.trim())}</li>`);
                continue;
            }
        }
        // Regular paragraph line
        closeList();
        html.push(`<p>${inlineMarkup(line)}</p>`);
    }
    if (inCode && codeLines) {
        html.push("<pre>" + codeLines.join("\n") + "</pre>");
    }
    closeList();
    closeTable();
    return html.join("");
}

// ── Menu bar for bundle page ────────────────────────────────────────

function buildBundleMenuBar(catalog, activeBundle = null) {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    if (!menuBar) { return; }

    // ≡ system menu
    const sysPopupItems = [
        { type: "dialog", dialog: "about", label: "~A~bout" },
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
    ];
    const sysPopupHTML = new TVMenuBox({
        items: sysPopupItems.map((entry) => {
            if (entry.type === "separator") {
                return renderMenuPopupSeparator();
            }
            if (entry.type === "submenu") {
                const subItems = entry.items.map((sub) => new TVButton({
                    dialog: false,
                    className: "tv-menu-popup-item",
                    attrs: { type: "button", "data-tv-saver-start": sub.mode },
                    labelMarkup: renderHotkeyMarkup(sub.label),
                }));
                return renderMenuSubmenu(renderHotkeyMarkup(entry.label), subItems);
            }
            const attrs = entry.type === "theme"
                ? { type: "button", "data-tv-theme-set": entry.theme }
                : entry.type === "saver"
                    ? { type: "button", "data-tv-saver-start": entry.mode }
                    : { type: "button", "data-tv-dialog-open": entry.dialog };
            return new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs,
                labelMarkup: renderHotkeyMarkup(entry.label),
            });
        }),
    });
    const sysRootHTML = renderMenuRoot(renderHotkeyMarkup("~≡~"), sysPopupHTML.items);

    // File menu with catalog entries
    const fileRootHTML = renderMenuRoot(renderHotkeyMarkup("~H~elp Files"), buildCatalogMenuItems(catalog));

    // Docs menu with documentation markdown files
    const docsItems = buildDocsMenuItems(docsCatalogData || []);
    const docsRootHTML = renderMenuRoot(renderHotkeyMarkup("~D~ocs"), docsItems);

    // Windows menu (TV standard)
    const winPopupItems = [
        { cmd: "tile", label: "~T~ile", hotkey: "" },
        { cmd: "cascade", label: "C~a~scade", hotkey: "" },
        { cmd: "list", label: "Window ~L~ist", hotkey: "Alt-0" },
        { cmd: "zoom", label: "~Z~oom", hotkey: "F5" },
        { cmd: "next", label: "~N~ext", hotkey: "F6" },
        { cmd: "previous", label: "~P~revious", hotkey: "Shift-F6" },
        { cmd: "close", label: "~C~lose", hotkey: "Alt-F3" },
    ];
    const winRootHTML = renderMenuRoot(
        renderHotkeyMarkup("~W~indows"),
        winPopupItems.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-window-cmd": entry.cmd },
                labelMarkup: renderHotkeyMarkup(entry.label) +
                    `<span class="tv-menu-hotkey">${escapeHtml(entry.hotkey)}</span>`,
            })
        ),
    );

    // Games menu
    const gamesPopupItems = [
        { type: "dialog", dialog: "breakout", label: "~B~reakOut" },
        { type: "dialog", dialog: "lines", label: "~L~ines" },
        { type: "dialog", dialog: "ludo", label: "L~u~do" },
        { type: "dialog", dialog: "mines", label: "~M~ines" },
        { type: "dialog", dialog: "puzzle", label: "~P~uzzle" },
        { type: "dialog", dialog: "reversi", label: "~R~eversi" },
        { type: "dialog", dialog: "snake", label: "S~n~ake" },
        { type: "dialog", dialog: "sokoban", label: "~S~okoban" },
        { type: "dialog", dialog: "tetris", label: "~T~etris" },
    ];
    const gamesRootHTML = renderMenuRoot(
        renderHotkeyMarkup("~G~ames"),
        gamesPopupItems.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-dialog-open": entry.dialog },
                labelMarkup: renderHotkeyMarkup(entry.label),
            })
        ),
    );

    const bundleContentsRootHTML = buildBundleContentsMenuRoot(activeBundle);

    menuBar.innerHTML = [
        `<nav class="tv-menu-items">`,
        sysRootHTML,
        fileRootHTML,
        docsRootHTML,
        gamesRootHTML,
        winRootHTML,
        bundleContentsRootHTML ? `<div class="tv-menu-separator" aria-hidden="true">│</div>` : ``,
        bundleContentsRootHTML,
        `</nav>`,
        `<div class="tv-menu-clock" data-tv-clock>00:00:00</div>`,
    ].join("");
}

// ── Bundle application ──────────────────────────────────────────────

class TVBundleApp {
    constructor() {
        this.desktop = null;
        this.windowManager = null;
        this.dialogManager = null;
        this.menuController = null;
        this.docWindows = new Map();
        this._menuBundleKey = "";
        this._stateSyncTimer = null;
        this._restoringUrlState = false;
        this._lastUrlStateHash = "";
        this._catalogReady = null;
    }

    start() {
        // Theme
        initializeTVTheme();

        this.desktop = document.querySelector("[data-tv-bundle-desktop]");
        if (!this.desktop) { return; }

        this.dialogManager = new TVDialogManager(this.desktop);
        this.dialogManager.onChange = () => {
            const activeBundle = this.windowManager
                ? this.windowManager.syncActiveTarget(this.dialogManager.activeTarget)
                : null;
            if (activeBundle) {
                this._updateSearchData(activeBundle);
                this._syncBundleMenu();
            }
            this._updateWindowMenuState();
            this._updateStatusLine("");
            this._scheduleUrlStateSync();
        };
        this._updateStatusLine("");

        // Register standard dialogs
        this._registerDialog("about", () => new TVAboutDialog(this.desktop));
        this._registerDialog("puzzle", () => new TVPuzzleDialog(this.desktop));
        this._registerDialog("calendar", () => new TVCalendarDialog(this.desktop));
        this._registerDialog("ascii", () => new TVAsciiTableDialog(this.desktop));
        this._registerDialog("calc", () => new TVCalculatorDialog(this.desktop));
        this._registerDialog("midi", () => new TVMidiPlayerDialog(this.desktop));
        this._registerDialog("colors", () => new TVColorsDialog(this.desktop));
        this._registerDialog("widgets", () => new TVWidgetGalleryDialog(this.desktop));
        this.fileOpenDialog = this._registerDialog("fileopen", () => new TVFileOpenDialog(this.desktop));
        this.changeDirectoryDialog = this._registerDialog("chdir", () => new TVChangeDirectoryDialog(this.desktop));
        this._registerDialog("tetris", () => new TVTetrisDialog(this.desktop));
        this._registerDialog("mines", () => new TVMinesDialog(this.desktop));
        this._registerDialog("breakout", () => new TVBreakOutDialog(this.desktop));
        this._registerDialog("sokoban", () => new TVSokobanDialog(this.desktop));
        this._registerDialog("lines", () => new TVLinesDialog(this.desktop));
        this._registerDialog("reversi", () => new TVReversiDialog(this.desktop));
        this._registerDialog("ludo", () => new TVLudoDialog(this.desktop));
        this._registerDialog("snake", () => new TVSnakeDialog(this.desktop));
        this._registerBundleSearch();
        this.dialogManager.applyActiveStates();

        // Show a usable File/Open command immediately, then replace the menus
        // with their complete catalog-backed contents when loading finishes.
        buildBundleMenuBar([], null);
        fillBorders();
        this._bindMenus();
        this._catalogReady = this._loadCatalog();

        // Layout
        fillBorders();
        fillDesktopPatterns();
        updateClocks();
        window.setInterval(updateClocks, 1000);
        window.addEventListener("resize", fillBorders, { passive: true });
        window.addEventListener("resize", fillDesktopPatterns, { passive: true });
        window.addEventListener("load", fillBorders, { passive: true });
        window.addEventListener("load", fillDesktopPatterns, { passive: true });

        this.windowManager = new BundleWindowManager(this.desktop, (hint) => {
            this._updateStatusLine(hint);
            this._syncBundleMenu();
            this._scheduleUrlStateSync();
        });
        this.windowManager.dialogManager = this.dialogManager;
        this._bindUrlStateSync();
    }

    _updateStatusLine(hint) {
        const hasHelpWindow = this.windowManager && this.windowManager.openWindows.size > 0;
        const currentBundle = this.windowManager ? this.windowManager.currentBundle : null;
        const statusLine = document.querySelector("[data-tv-status-line]");
        if (!statusLine) { return; }
        const items = [];
        if (hasHelpWindow) {
            items.push(new TVButton({
                dialog: false,
                className: "tv-status-item",
                attrs: { type: "button", "data-tv-bundle-back": true },
                labelMarkup: renderHotkeyMarkup("~B~ack"),
            }).renderMarkup());
            if (currentBundle && bundleCanShowIndex(currentBundle)) {
                items.push(new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-bundle-index": true },
                    labelMarkup: renderHotkeyMarkup("~I~ndex"),
                }).renderMarkup());
            }
            if (currentBundle && bundleCanShowHelpContentsTopic(currentBundle)) {
                items.push(new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-bundle-help-contents": true },
                    labelMarkup: renderHotkeyMarkup("~H~elp Contents"),
                }).renderMarkup());
            }
            if (currentBundle && bundleCanShowContents(currentBundle)) {
                items.push(new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-bundle-contents": true },
                    labelMarkup: renderHotkeyMarkup("C~o~ntent"),
                }).renderMarkup());
            }
            items.push(new TVButton({
                dialog: false,
                className: "tv-status-item",
                attrs: { type: "button", "data-tv-dialog-open": "search" },
                labelMarkup: renderHotkeyMarkup("~F3~ Search"),
            }).renderMarkup());
            items.push(new TVButton({
                dialog: false,
                className: "tv-status-item",
                attrs: { type: "button", "data-tv-bundle-close-all": true },
                labelMarkup: renderHotkeyMarkup("~Alt-F3~ Close"),
            }).renderMarkup());
        }
        items.push(new TVButton({
            dialog: false,
            className: "tv-status-item",
            attrs: { type: "button", "data-tv-dialog-open": "about" },
            labelMarkup: renderHotkeyMarkup("~F1~ About"),
        }).renderMarkup());
        items.push(`<span class="tv-status-separator" aria-hidden="true">│</span>`);
        items.push(`<span class="tv-status-hint" data-tv-status-hint>${escapeHtml(hint || "THelpViewer")}</span>`);
        items.push(`<a class="tv-status-link" href="https://github.com/mariolacko/THelpViewer" target="_blank" rel="noopener">GitHub</a>`);
        statusLine.innerHTML = items.join("");
        this._bindStatusButtons();
    }

    _updateWindowMenuState() {
        if (!this.dialogManager) { return; }
        const windowCount = this.dialogManager.openWindowCount();
        const targetCount = this.dialogManager.openTargets().length;
        const states = {
            tile: windowCount > 0,
            cascade: windowCount > 0,
            list: targetCount > 0,
            zoom: this.dialogManager.canDispatchCommand(TV_COMMANDS.ZOOM),
            next: this.dialogManager.canDispatchCommand(TV_COMMANDS.NEXT),
            previous: this.dialogManager.canDispatchCommand(TV_COMMANDS.PREVIOUS),
            close: this.dialogManager.canDispatchCommand(TV_COMMANDS.CLOSE),
        };
        document.querySelectorAll("[data-tv-window-cmd]").forEach((item) => {
            const enabled = Boolean(states[item.dataset.tvWindowCmd]);
            item.disabled = !enabled;
            item.setAttribute("aria-disabled", enabled ? "false" : "true");
            item.classList.toggle("is-disabled", !enabled);
            if (!enabled) {
                item.classList.remove("is-menu-selected");
                item.tabIndex = -1;
            }
        });
    }

    _bindStatusButtons() {
        const statusLine = document.querySelector("[data-tv-status-line]");
        if (!statusLine) { return; }
        const closeAllBtn = statusLine.querySelector("[data-tv-bundle-close-all]");
        if (closeAllBtn) {
            closeAllBtn.addEventListener("click", (event) => {
                event.preventDefault();
                this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE);
            });
        }
        const backBtn = statusLine.querySelector("[data-tv-bundle-back]");
        if (backBtn) {
            backBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager) { this.windowManager.goBack(); }
            });
        }
        const indexBtn = statusLine.querySelector("[data-tv-bundle-index]");
        if (indexBtn) {
            indexBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager && this.windowManager.currentBundle) {
                    this.windowManager.showIndex(this.windowManager.currentBundle);
                }
            });
        }
        const helpContentsBtn = statusLine.querySelector("[data-tv-bundle-help-contents]");
        if (helpContentsBtn) {
            helpContentsBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager && this.windowManager.currentBundle) {
                    this.windowManager.showHelpContentsTopic(this.windowManager.currentBundle);
                }
            });
        }
        const contentsBtn = statusLine.querySelector("[data-tv-bundle-contents]");
        if (contentsBtn) {
            contentsBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager && this.windowManager.currentBundle) {
                    this.windowManager.showContents(this.windowManager.currentBundle);
                }
            });
        }
        statusLine.querySelectorAll("[data-tv-dialog-open]").forEach((el) => {
            el.addEventListener("click", (event) => {
                event.preventDefault();
                this.dialogManager.open(el.getAttribute("data-tv-dialog-open") || "");
            });
        });
    }

    _bindUrlStateSync() {
        window.addEventListener("tv-window-state-change", () => this._scheduleUrlStateSync());
        document.addEventListener("selectionchange", () => this._scheduleUrlStateSync());
        document.addEventListener("keyup", () => this._scheduleUrlStateSync());
        this.desktop.addEventListener("scroll", () => this._scheduleUrlStateSync(), true);
    }

    _scheduleUrlStateSync() {
        if (this._restoringUrlState) { return; }
        window.clearTimeout(this._stateSyncTimer);
        this._stateSyncTimer = window.setTimeout(() => this._syncUrlState(), 180);
    }

    _syncUrlState() {
        if (this._restoringUrlState) { return; }
        const state = this._captureUrlState();
        const url = new URL(window.location.href);
        url.search = "";
        if (state) {
            url.hash = encodeUrlState(state);
        } else if (url.hash.replace(/^#/, "").startsWith(URL_STATE_PREFIX)) {
            url.hash = "";
        } else {
            return;
        }
        const next = url.toString();
        if (next !== window.location.href && next !== this._lastUrlStateHash) {
            this._lastUrlStateHash = next;
            window.history.replaceState(null, "", next);
        }
    }

    _captureUrlState() {
        if (!this.dialogManager) { return null; }
        const windows = [];
        const targets = [];
        const addWindow = (target, item) => {
            if (!target || !item) { return; }
            windows.push(item);
            targets.push(target);
        };

        if (this.windowManager) {
            for (const [key, element] of this.windowManager.openWindows) {
                const file = element.dataset.tvStateFile || "";
                if (!file) { continue; }
                const viewport = element.querySelector("[data-tv-viewport]");
                const item = {
                    t: "h",
                    f: file,
                    view: element.dataset.tvStateView || "index",
                    g: captureWindowGeometry(element),
                };
                const topic = element.dataset.tvStateTopic || "";
                if (topic) { item.topic = topic; }
                const visibleLine = viewport
                    ? Array.from(element.querySelectorAll(".tv-topic-line[data-tv-line]"))
                        .find((line) => line.offsetTop + line.offsetHeight >= viewport.scrollTop)
                    : null;
                const line = Number(visibleLine ? visibleLine.dataset.tvLine : element.dataset.tvStateLine);
                if (Number.isInteger(line) && line > 0) { item.line = line; }
                if (viewport) { item.s = [Math.round(viewport.scrollLeft), Math.round(viewport.scrollTop)]; }
                if (element.dataset.tvStateTagKey && element.dataset.tvStateTagValue) {
                    item.tag = [
                        element.dataset.tvStateTagKey,
                        element.dataset.tvStateTagValue,
                        element.dataset.tvStateTagLabel || element.dataset.tvStateTagKey,
                    ];
                }
                const selection = captureTextSelection(viewport);
                if (selection) { item.sel = selection; }
                addWindow("help:" + key, item);
            }
        }

        this.desktop.querySelectorAll(".tv-doc-window").forEach((element) => {
            const file = element.dataset.tvStateFile || "";
            if (!file) { return; }
            const viewport = element.querySelector("[data-tv-viewport]");
            const item = {
                t: "doc",
                f: file,
                g: captureWindowGeometry(element),
            };
            if (viewport) { item.s = [Math.round(viewport.scrollLeft), Math.round(viewport.scrollTop)]; }
            const selection = captureTextSelection(viewport);
            if (selection) { item.sel = selection; }
            addWindow(element.dataset.tvManagerName || ("doc:" + file), item);
        });

        this.dialogManager.dialogs.forEach((dialog, name) => {
            if (name === "welcome" || !dialog || !dialog.isOpen()) { return; }
            const item = {
                t: "dlg",
                name,
                g: captureWindowGeometry(dialog.dialog, true),
            };
            if (typeof dialog.captureUrlState === "function") {
                const dialogState = dialog.captureUrlState();
                if (dialogState !== undefined && dialogState !== null) {
                    item.state = dialogState;
                }
            }
            addWindow(name, item);
        });

        if (!windows.length) { return null; }
        const targetIndex = new Map(targets.map((target, index) => [target, index]));
        const order = [];
        this.dialogManager.stackOrder.forEach((target) => {
            const index = targetIndex.get(target);
            if (Number.isInteger(index) && !order.includes(index)) {
                order.push(index);
            }
        });
        targets.forEach((_target, index) => {
            if (!order.includes(index)) { order.push(index); }
        });
        const active = targetIndex.has(this.dialogManager.activeTarget)
            ? targetIndex.get(this.dialogManager.activeTarget)
            : order[order.length - 1];
        return { v: 1, a: active, z: order, w: windows };
    }

    async _restoreUrlState(state) {
        if (!state || !Array.isArray(state.w) || !state.w.length) { return false; }
        this._restoringUrlState = true;
        const targets = [];
        let restored = false;
        try {
            this.dialogManager.close("welcome");
            for (const item of state.w) {
                if (!item || typeof item !== "object") { continue; }
                if (item.t === "h") {
                    const entry = (catalogData || []).find((candidate) => candidate.file === item.f || candidate.name === item.f);
                    if (!entry) { continue; }
                    const bundle = await loadBundle(entry.file);
                    this._updateSearchData(bundle);
                    if (item.view === "contents") {
                        this.windowManager.showContents(bundle);
                    } else if (item.view === "tag" && Array.isArray(item.tag) && item.tag.length >= 2) {
                        this.windowManager.showTag(bundle, item.tag[0], item.tag[1], item.tag[2] || item.tag[0]);
                    } else if (item.view === "index") {
                        this.windowManager.showIndex(bundle);
                    } else if (item.topic) {
                        this.windowManager.showTopic(bundle, item.topic, item.line || null);
                    } else {
                        this.windowManager.showDefault(bundle, item.line || null);
                    }
                    const key = bundleWindowKey(bundle);
                    const windowEl = this.windowManager.openWindows.get(key);
                    this._applyUrlWindowState(windowEl, item, false);
                    targets.push("help:" + key);
                    restored = true;
                } else if (item.t === "doc") {
                    const entry = (docsCatalogData || []).find((candidate) => candidate.file === item.f || candidate.name === item.f);
                    if (!entry) { continue; }
                    const response = await fetch(DOCS_DIR + entry.file);
                    if (!response.ok) { continue; }
                    const windowEl = this._openDocWindow(entry.file, await response.text());
                    this._applyUrlWindowState(windowEl, item, false);
                    targets.push(windowEl.dataset.tvManagerName || ("doc:" + entry.file));
                    restored = true;
                } else if (item.t === "dlg" && item.name) {
                    const dialog = this.dialogManager.open(item.name);
                    if (!dialog) { continue; }
                    if (item.state && typeof dialog.restoreUrlState === "function") {
                        dialog.restoreUrlState(item.state);
                    }
                    applyWindowGeometry(dialog.dialog, item.g, true);
                    dialog.hasPosition = true;
                    targets.push(item.name);
                    restored = true;
                }
            }
            if (restored) {
                this._restoreUrlStack(state, targets);
                fillBorders();
                fillDesktopPatterns();
                this._syncBundleMenu();
            }
        } finally {
            this._restoringUrlState = false;
            if (restored) { this._syncUrlState(); }
        }
        return restored;
    }

    _applyUrlWindowState(windowEl, item, dialog = false) {
        if (!windowEl || !item) { return; }
        applyWindowGeometry(windowEl, item.g, dialog);
        const viewport = windowEl.querySelector("[data-tv-viewport]");
        if (viewport && Array.isArray(item.s)) {
            viewport.scrollLeft = Math.max(0, Number(item.s[0]) || 0);
            viewport.scrollTop = Math.max(0, Number(item.s[1]) || 0);
        }
        if (viewport && item.sel) {
            restoreTextSelection(viewport, item.sel);
        }
    }

    _restoreUrlStack(state, targets) {
        const order = Array.isArray(state.z) ? state.z : [];
        const stack = [];
        order.forEach((index) => {
            const target = targets[Number(index)];
            if (target && !stack.includes(target)) { stack.push(target); }
        });
        targets.forEach((target) => {
            if (target && !stack.includes(target)) { stack.push(target); }
        });
        const modalTargets = stack.filter((target) => {
            const dialog = this.dialogManager.get(target);
            return dialog && dialog.modal && dialog.isOpen();
        });
        if (modalTargets.length) {
            const modalNames = new Set(modalTargets);
            const nonModalTargets = stack.filter((target) => !modalNames.has(target));
            stack.splice(0, stack.length, ...nonModalTargets, ...modalTargets);
        }
        this.dialogManager.stackOrder = stack;
        const activeTarget = modalTargets.length
            ? modalTargets[modalTargets.length - 1]
            : targets[Number(state.a)];
        if (activeTarget) {
            this.dialogManager.activeTarget = activeTarget;
        } else if (stack.length) {
            this.dialogManager.activeTarget = stack[stack.length - 1];
        } else {
            this.dialogManager.activateHostWindow();
            return;
        }
        this.dialogManager.applyAllZIndices();
        this.dialogManager.applyActiveStates();
        const bundle = this.windowManager.syncActiveTarget(this.dialogManager.activeTarget);
        if (bundle) { this._updateSearchData(bundle); }
        this._updateStatusLine("");
    }

    _registerDialog(name, factory) {
        try {
            const dialog = factory();
            if (dialog) {
                this.dialogManager.register(name, dialog);
                return dialog;
            }
        } catch (error) {
            console.error(`Failed to initialize dialog: ${name}`, error);
        }
        return null;
    }

    _registerBundleSearch() {
        const searchDialog = this._registerDialog("search", () => new TVSearchDialog(this.desktop));
        if (!searchDialog) { return; }
        this.searchDialog = searchDialog;
        // Provide empty search data initially
        searchDialog.searchData = { topics: [] };
        // Override openSelected to navigate within bundle viewer
        const self = this;
        searchDialog.openSelected = function () {
            if (this.selectedIndex < 0 || this.selectedIndex >= this.matches.length) {
                return;
            }
            const match = this.matches[this.selectedIndex];
            this.close();
            if (self.windowManager && self.windowManager.currentBundle) {
                self.windowManager.showTopic(self.windowManager.currentBundle, match.context_hex);
            }
        };
    }

    _updateSearchData(bundle) {
        if (this.searchDialog && bundle) {
            this.searchDialog.searchData = { topics: buildUhfSearchIndex(bundle) };
        }
    }

    _collectWindowListItems() {
        const items = [];
        if (this.windowManager) {
            for (const [key, el] of this.windowManager.openWindows) {
                const caption = el.querySelector(".tv-window-caption");
                items.push({
                    label: caption ? caption.textContent : key,
                    type: "window",
                    key,
                    managerName: "help:" + key,
                    element: el,
                });
            }
        }
        this.desktop.querySelectorAll(".tv-doc-window").forEach((el) => {
            const caption = el.querySelector(".tv-window-caption");
            items.push({
                label: caption ? caption.textContent : "Document",
                type: "doc",
                managerName: el.dataset.tvManagerName || "",
                element: el,
            });
        });
        if (this.dialogManager) {
            this.dialogManager.dialogs.forEach((dialog, name) => {
                if (dialog && dialog.isOpen()) {
                    const captionEl = dialog.dialog ? dialog.dialog.querySelector(".tv-dialog-title-text") : null;
                    items.push({
                        label: captionEl ? captionEl.textContent : name,
                        type: "dialog",
                        key: name,
                    });
                }
            });
        }
        return items;
    }

    _showWindowList() {
        let items = this._collectWindowListItems();
        if (items.length === 0) { return; }

        const { TVDialog } = TV;

        const renderItems = (list, selectedIdx) =>
            list.map((item, i) =>
                `<button class="tv-winlist-item${i === selectedIdx ? ' is-selected' : ''}" data-tv-winlist-idx="${i}" type="button">${escapeHtml(item.label)}</button>`
            ).join("");

        const dialog = new TVDialog({
            desktop: this.desktop,
            windowClass: "tv-winlist-window",
            bodyClass: "tv-winlist-body",
            ariaLabel: "Window List",
            title: "Window List",
            closeAttrs: {
                "data-tv-winlist-close": true,
                "aria-label": "Close window list",
            },
            bodyMarkup: '<div class="tv-winlist-items"></div>',
            footerMarkup: TVDialog.footerMarkup(),
            width: "40ch",
            height: "min(14em, calc(100% - 2em))",
            modal: true,
        });

        const itemsContainer = dialog.query(".tv-winlist-items");
        let selectedIdx = 0;

        const refresh = () => {
            items = this._collectWindowListItems();
            if (selectedIdx >= items.length) { selectedIdx = Math.max(0, items.length - 1); }
            if (itemsContainer) {
                itemsContainer.innerHTML = renderItems(items, selectedIdx);
            }
        };

        const updateSelection = () => {
            if (itemsContainer) {
                itemsContainer.querySelectorAll(".tv-winlist-item").forEach((el, i) => {
                    el.classList.toggle("is-selected", i === selectedIdx);
                });
            }
        };

        const observer = new MutationObserver(() => {
            if (dialog.isOpen()) { refresh(); }
        });
        observer.observe(this.desktop, { childList: true });

        if (this.dialogManager) {
            this.dialogManager.register("windowlist", dialog);
        }

        const cleanup = () => {
            observer.disconnect();
            dialog.dialog.removeEventListener("keydown", onKey);
            dialog.destroy();
        };

        dialog.bindCommonClose(cleanup);
        dialog.bindDrag();

        const activate = (idx) => {
            const item = items[idx];
            if (!item) { return; }
            if (item.type === "dialog" && this.dialogManager) {
                this.dialogManager.bringToFront(item.key);
            } else if ((item.type === "window" || item.type === "doc") && this.dialogManager) {
                this.dialogManager.activateWindow(item.managerName);
            }
            cleanup();
        };

        const onKey = (event) => {
            if (!dialog.isOpen()) { return; }
            if (event.key === "Escape") { event.preventDefault(); cleanup(); return; }
            if (event.key === "ArrowDown") { event.preventDefault(); selectedIdx = (selectedIdx + 1) % items.length; updateSelection(); return; }
            if (event.key === "ArrowUp") { event.preventDefault(); selectedIdx = (selectedIdx - 1 + items.length) % items.length; updateSelection(); return; }
            if (event.key === "Enter") { event.preventDefault(); activate(selectedIdx); return; }
        };
        dialog.dialog.addEventListener("keydown", onKey);

        dialog.overlay.addEventListener("click", (event) => {
            const btn = event.target.closest("[data-tv-winlist-idx]");
            if (btn) {
                activate(parseInt(btn.dataset.tvWinlistIdx, 10));
            }
        });

        refresh();
        dialog.open();
    }

    async _loadCatalog() {
        // Load both help and docs catalogs in parallel.
        const [helpResp, docsResp] = await Promise.allSettled([
            fetch(CATALOG_FILE, { cache: "no-store" }),
            fetch(DOCS_CATALOG_FILE, { cache: "no-store" }),
        ]);

        if (helpResp.status === "fulfilled" && helpResp.value.ok) {
            catalogData = await helpResp.value.json();
            if (!Array.isArray(catalogData)) { catalogData = []; }
        } else {
            catalogData = [];
        }

        if (docsResp.status === "fulfilled" && docsResp.value.ok) {
            docsCatalogData = await docsResp.value.json();
            if (!Array.isArray(docsCatalogData)) { docsCatalogData = []; }
        } else {
            docsCatalogData = [];
        }
        const entries = [
            ...catalogData.map((entry) => ({
                ...entry,
                kind: "help",
                fileName: entry.source_file || entry.name,
            })),
            ...docsCatalogData.map((entry) => ({
                ...entry,
                kind: "doc",
                fileName: String(entry.file || "").split("/").pop() || entry.name,
            })),
        ];
        if (this.fileOpenDialog) {
            this.fileOpenDialog.configure(entries, (entry) => {
                if (entry.kind === "doc") {
                    this._openDocFile(entry.file);
                } else {
                    this._openBundleFile(entry.file, entry.name);
                }
            });
        }
        if (this.changeDirectoryDialog) {
            this.changeDirectoryDialog.configure(entries, (directory) => {
                this.fileOpenDialog?.setDirectory(directory);
            });
        }
        buildBundleMenuBar(catalogData, null);
        fillBorders();
        this._bindMenus();
        this._showWelcome();
        await this._handleUrlState();
    }

    _syncBundleMenu() {
        if (!Array.isArray(catalogData)) { return; }
        const currentBundle = this.windowManager ? this.windowManager.currentBundle : null;
        const hasContentsMenu = !!(currentBundle && Array.isArray(currentBundle.contents) && currentBundle.contents.length);
        const nextKey = hasContentsMenu ? bundleWindowKey(currentBundle) : "";
        if (nextKey === this._menuBundleKey) {
            return;
        }
        this._menuBundleKey = nextKey;
        buildBundleMenuBar(catalogData, hasContentsMenu ? currentBundle : null);
        fillBorders();
        this._bindMenus();
    }

    async _handleUrlState() {
        const hashState = decodeUrlState(window.location.hash);
        if (hashState) { await this._restoreUrlState(hashState); }
        if (window.location.search) {
            const url = new URL(window.location.href);
            url.search = "";
            window.history.replaceState(null, "", url.toString());
        }
    }

    _openDocWindow(filename, markdownText) {
        const docKey = String(filename || "");
        const managerName = "doc:" + docKey;
        const existing = this.docWindows.get(docKey);
        if (existing?.isConnected) {
            this.dialogManager.activateWindow(managerName);
            return existing;
        }
        this.docWindows.delete(docKey);
        const htmlContent = renderMarkdown(markdownText);
        const title = filename.replace(/\.md$/i, "").replace(/_/g, " ");
        const contentHTML = `<div class="tv-document tv-doc-document" data-tv-doc-editor>${htmlContent}</div>`;
        const w = { cols: 78, rows: 24, min_cols: 40, min_rows: 8 };
        const style = `--tv-window-cols:${w.cols}; --tv-window-rows:${w.rows}; --tv-window-min-cols:${w.min_cols}; --tv-window-min-rows:${w.min_rows};`;
        const windowHTML = TVWindow.renderMarkup({
            className: "tv-doc-window",
            style,
            caption: title,
            contentMarkup: contentHTML,
        });

        const template = document.createElement("template");
        template.innerHTML = windowHTML.trim();
        const windowEl = template.content.firstElementChild;
        windowEl.dataset.tvStateType = "doc";
        windowEl.dataset.tvStateFile = filename;
        windowEl.dataset.tvManagerName = managerName;
        windowEl.dataset.tvWindowStorageKey = managerName;
        this.docWindows.set(docKey, windowEl);
        this.desktop.appendChild(windowEl);
        bindCloseButtons(windowEl);

        // Init widgets
        const indicator = new TVIndicator();
        indicator.root = TVWidget.fromHTML(indicator.renderMarkup());
        const horizontalScrollbar = windowEl.querySelector(".tv-bottom-bar > .tv-scrollbar-x");
        horizontalScrollbar?.before(indicator.root);
        windowEl._tvEditor = new TVEditor(windowEl.querySelector("[data-tv-doc-editor]"), { indicator });
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        windowEl._tvScrollbars = Array.from(frames, (frame) => new TVScrollBar(frame));
        windowEl._tvResizer = new TurboVisionWindowResizer(windowEl);

        const closeWindow = () => {
            if (this.dialogManager) { this.dialogManager.unregisterWindow(managerName); }
            this.docWindows.delete(docKey);
            destroyWindowWidgets(windowEl);
            windowEl.remove();
            fillBorders();
            fillDesktopPatterns();
        };
        const toggleWindowZoom = () => {
            const isMax = windowEl.classList.toggle("is-maximized");
            const glyph = windowEl.querySelector("[data-tv-zoom-glyph]");
            if (glyph) { glyph.textContent = isMax ? "↓" : "↑"; }
            fillBorders();
            fillDesktopPatterns();
        };

        // Register with window manager for focus/z-index and shared commands.
        if (this.dialogManager) {
            this.dialogManager.registerWindow(managerName, windowEl, {
                [TV_COMMANDS.CLOSE]: closeWindow,
                [TV_COMMANDS.ZOOM]: toggleWindowZoom,
            });
        }

        // Close button
        const closeBtn = windowEl.querySelector("[data-tv-close-button]");
        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.preventDefault();
                closeWindow();
            });
        }
        // Zoom
        const zoomBtn = windowEl.querySelector(".tv-zoom-control");
        if (zoomBtn) {
            zoomBtn.addEventListener("click", (e) => {
                e.preventDefault();
                toggleWindowZoom();
            });
        }

        // Intercept .md links to open in-viewer instead of navigating
        const self = this;
        const baseDir = filename.includes("/") ? filename.replace(/[^/]+$/, "") : "";
        windowEl.querySelectorAll("a[href]").forEach((link) => {
            const href = link.getAttribute("href");
            if (href && href.endsWith(".md")) {
                link.addEventListener("click", async (e) => {
                    e.preventDefault();
                    // Resolve relative path and normalize ../
                    const raw = baseDir ? baseDir + decodeURIComponent(href) : decodeURIComponent(href);
                    const parts = raw.split("/");
                    const normalized = [];
                    for (const p of parts) {
                        if (p === "..") { normalized.pop(); }
                        else if (p && p !== ".") { normalized.push(p); }
                    }
                    const resolved = normalized.join("/");
                    try {
                        const resp = await fetch(DOCS_DIR + encodeURI(resolved));
                        if (!resp.ok) { throw new Error(`HTTP ${resp.status}`); }
                        const md = await resp.text();
                        self._openDocWindow(resolved, md);
                    } catch (error) {
                        console.error(`Failed to load doc ${resolved}:`, error);
                    }
                });
            }
        });

        fillBorders();
        fillDesktopPatterns();
        return windowEl;
    }

    async _openBundleFile(filename, label = "") {
        const cached = bundleCache.has(filename);
        let loadingDialog = null;
        if (!cached) {
            loadingDialog = new TVLoadingDialog(this.desktop);
            loadingDialog.show(bundleLoadingLabel(label, filename));
        }
        try {
            const bundle = await loadBundle(filename, {
                onProgress: (received, total) => {
                    if (loadingDialog) { loadingDialog.update(received, total); }
                },
                signal: loadingDialog ? loadingDialog.signal : undefined,
            });
            if (loadingDialog) { loadingDialog.destroy(); }
            this._updateSearchData(bundle);
            this.windowManager.showDefault(bundle);
        } catch (error) {
            if (loadingDialog) { loadingDialog.destroy(); }
            if (error.name === "AbortError") { return; }
            console.error(`Failed to load bundle ${filename}:`, error);
        }
    }

    async _openDocFile(docFile) {
        try {
            const resp = await fetch(DOCS_DIR + docFile);
            if (!resp.ok) { throw new Error(`HTTP ${resp.status}`); }
            const md = await resp.text();
            this._openDocWindow(docFile, md);
        } catch (error) {
            console.error(`Failed to load doc ${docFile}:`, error);
        }
    }

    _showWelcome() {
        const {
            TVDialog,
            TVStaticText,
            TVGroup,
            TVButton: TVBtn,
        } = TV;
        const welcomeBody = new TVGroup({
            w: 30, h: 9,
            children: [
                new TVStaticText({ x: 0, y: 1, w: 30, align: "center", title: true, text: "THelpViewer" }),
                new TVStaticText({ x: 0, y: 3, w: 30, align: "center", text: "Select a help file from the" }),
                new TVStaticText({ x: 0, y: 4, w: 30, align: "center", text: "File menu to get started." }),
                new TVStaticText({ x: 0, y: 6, w: 30, align: "center", text: `${Array.isArray(catalogData) ? catalogData.length : 0} help file(s) available.` }),
                new TVButton({ x: 10, y: 8, w: 10, className: "is-default", attrs: { "data-tv-welcome-ok": true }, label: '~O~K' }),
            ],
        }).renderMarkup();
        const dialog = new TVDialog({
            desktop: this.desktop,
            ariaLabel: "Welcome",
            title: "Welcome",
            closeAttrs: {
                "data-tv-about-close": true,
                "aria-label": "Close welcome dialog",
            },
            bodyMarkup: welcomeBody,
            footerMarkup: TVDialog.footerMarkup(),
            width: "34ch",
            height: "min(12em, calc(100% - 2em))",
            modal: true,
        });
        dialog.bindCommonClose(() => {
            dialog.destroy();
        });
        dialog.bindDrag();
        const ok = dialog.query("[data-tv-welcome-ok]");
        if (ok) {
            ok.addEventListener("click", () => {
                dialog.destroy();
            });
        }
        this.dialogManager.register("welcome", dialog);
        this.dialogManager.open("welcome");
    }

    _handleMenuShortcut(event) {
        if (event.key === "F5" && !event.ctrlKey && !event.altKey && !event.shiftKey) {
            event.preventDefault();
            this.dialogManager.dispatchCommand(TV_COMMANDS.ZOOM);
            return;
        }
        if (event.key === "F3" && event.altKey && !event.ctrlKey && !event.shiftKey) {
            event.preventDefault();
            this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE);
            return;
        }
        if (event.key === "0" && event.altKey && !event.ctrlKey && !event.shiftKey) {
            event.preventDefault();
            this._showWindowList();
            return;
        }
        if (event.key === "F6" && !event.altKey && !event.ctrlKey && !event.metaKey) {
            event.preventDefault();
            this.dialogManager.dispatchCommand(event.shiftKey ? TV_COMMANDS.PREVIOUS : TV_COMMANDS.NEXT);
        }
    }

    _bindMenus() {
        if (!this.menuController) {
            this.menuController = new TVMenuController({
                onUnhandledKeyDown: (event) => this._handleMenuShortcut(event),
            });
        } else {
            this.menuController.refresh();
        }
        const closeMenus = () => this.menuController.closeMenus();

        document.querySelectorAll("[data-tv-file-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                this.dialogManager.open("fileopen");
            });
        });

        document.querySelectorAll("[data-tv-dialog-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                this.dialogManager.open(element.getAttribute("data-tv-dialog-open") || "");
            });
        });

        document.querySelectorAll("[data-tv-theme-set]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                applyThemeAndSyncPalette(element.getAttribute("data-tv-theme-set") || "default", true);
                this.dialogManager.applyActiveStates();
                fillBorders();
            });
        });

        document.querySelectorAll("[data-tv-bundle-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                const filename = element.dataset.tvBundleOpen;
                const bundleLabel = element.dataset.tvBundleLabel || "";
                this._openBundleFile(filename, bundleLabel);
            });
        });

        document.querySelectorAll("[data-tv-current-topic], [data-tv-menu-link]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", async (event) => {
                event.preventDefault();
                closeMenus();
                if (!this.windowManager || !this.windowManager.currentBundle) {
                    return;
                }
                const sourceFile = element.dataset.tvSourceFile || "";
                const lineNumber = this.windowManager._normalizeLineNumber(element.dataset.tvTopicLine);
                const topicRef = (
                    element.dataset.tvCurrentTopic
                    || element.dataset.tvBundleTopic
                    || element.dataset.tvTopicAlias
                    || ""
                ).trim();
                if (sourceFile) {
                    await this.windowManager.openSourceTopic(sourceFile, topicRef, lineNumber, this.windowManager.currentBundle);
                    return;
                }
                if (!topicRef) {
                    return;
                }
                this.windowManager.showTopic(this.windowManager.currentBundle, topicRef, lineNumber);
            });
        });

        document.querySelectorAll("[data-tv-doc-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                this._openDocFile(element.dataset.tvDocOpen);
            });
        });

        document.querySelectorAll("[data-tv-window-cmd]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                const cmd = element.dataset.tvWindowCmd;
                if (cmd === "zoom") {
                    this.dialogManager.dispatchCommand(TV_COMMANDS.ZOOM);
                } else if (cmd === "close") {
                    this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE);
                } else if (cmd === "next") {
                    this.dialogManager.dispatchCommand(TV_COMMANDS.NEXT);
                } else if (cmd === "previous") {
                    this.dialogManager.dispatchCommand(TV_COMMANDS.PREVIOUS);
                } else if (cmd === "tile") {
                    this.windowManager.tile();
                } else if (cmd === "cascade") {
                    this.windowManager.cascade();
                } else if (cmd === "list") {
                    this._showWindowList();
                }
            });
        });

        // Screen saver triggers
        document.querySelectorAll("[data-tv-saver-start]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                const mode = element.dataset.tvSaverStart;
                const saver = TVScreenSaver.modes[mode];
                if (saver) {
                    new saver().start();
                }
            });
        });
        TVScreenSaver.installIdleStart();

        document.querySelectorAll("[data-tv-bundle-back]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager) {
                    this.windowManager.goBack();
                }
            });
        });

        this._updateWindowMenuState();
    }
}

// ── Bootstrap ───────────────────────────────────────────────────────

function initBundleApp() {
    const body = document.body;
    if (!body || body.dataset.tvPageKind !== "bundle-index") {
        return;
    }
    new TVBundleApp().start();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initBundleApp, { once: true });
} else {
    initBundleApp();
}

Object.assign(TV, { TVBundleApp, BundleWindowManager });
})();
