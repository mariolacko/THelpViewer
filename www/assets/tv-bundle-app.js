// Bundle viewer: single-page app that loads help JSON bundles on demand.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    renderHotkeyMarkup,
    fillBorders,
    fillDesktopPatterns,
    applyThemeAndSyncPalette,
    initializeTVTheme,
    TV_COMMANDS,
    TV_HELP_CONTEXTS,
    TV_CONTEXT_HELP_TOPICS,
    TVMenuController,
    TVHelpController,
    TVDesktop,
    TVProgram,
    TVAboutDialog,
    TVLoginDialog,
    TVRegistrationDialog,
    TVRegistrationTokenDialog,
    TVServerConfigurationDialog,
    TVApplicationMenuBar,
    buildAccountMenu,
    TVPuzzleDialog,
    TVCalendarDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVColorsDialog,
    TVViewGalleryDialog,
    TVGridDemoDialog,
    TVServerTerminalDialog,
    TVFileOpenDialog,
    TVChangeDirectoryDialog,
    TVMidiPlayerDialog,
    TVStatisticsDialog,
    TVSystemInformationDialog,
    TVFindDialog,
    TVSearchDialog,
    TVTetrisDialog,
    TVMinesDialog,
    TVBreakOutDialog,
    TVSokobanDialog,
    TVLinesDialog,
    TVReversiDialog,
    TVLudoDialog,
    TVMastermindDialog,
    TVHanoiDialog,
    TVSnakeDialog,
    TVTronDialog,
    TVGameDialog,
    TVScreenSaver,
    TVWindow,
    TVDosWindow,
    TVDialog,
    TVMessageBox,
    TVView,
    TVGroup,
    TVStaticText,
    TVPercentGauge,
    TVBarGauge,
    TVPoint,
    TVRect,
    TVEvent,
    TVIndicator,
    TVEditor,
    TVOutline,
    TVListBox,
    TVHelpViewer,
    TVHelpWindow,
    TVButton,
    bfDefault,
    sfModal,
    evKeyDown,
    cmUpdateGauge,
    cmResetGauge,
    wnNoNumber,
    TVMenuItem,
    TVMenu,
    TVMenuBar,
    TVStatusItem,
    NewLine,
    NewSubMenu,
    NewStatusKey,
    NewStatusDef,
    TVStatusLine,
    kbCtrlF,
    kbCtrlL,
    kbF1,
    kbF3,
    kbF5,
    kbF6,
    kbShiftF6,
    kbAltF3,
    kbAlt0,
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

const {
    hcSystemMenu,
    hcHelpFiles,
    hcDocuments,
    hcSearch,
    hcGames,
    hcWindows,
    hcContextHelp,
    hcDocumentViewer,
    hcNoContext,
    hcDosPrompt,
} = TV_HELP_CONTEXTS;

// ── Catalog & data cache ────────────────────────────────────────────

const HELPS_DIR = "helps/";
const CATALOG_FILE = HELPS_DIR + "catalog.json";
const CONTEXT_HELP_BUNDLE_FILE = "../assets/tv-context-help.json";
const DOCS_DIR = "docs/";
const DOCS_CATALOG_FILE = DOCS_DIR + "catalog.json";
const bundleCache = new Map();
let catalogData = null;
let docsCatalogData = null;
const URL_STATE_PREFIX = "tv=1.";

function statisticsDialogName(name) {
    const value = String(name || "").toLowerCase();
    if (value.startsWith("hall:")) { return "hall-of-fame"; }
    if (value.startsWith("highscore:")) { return "highscore"; }
    if (value.startsWith("tetris-setup:")) { return "tetris-setup"; }
    return value;
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

function statisticsOrientation() {
    const type = String(window.screen?.orientation?.type || "");
    if (type.startsWith("portrait")) { return "portrait"; }
    if (type.startsWith("landscape")) { return "landscape"; }
    if (window.matchMedia?.("(orientation: portrait)").matches) { return "portrait"; }
    if (window.matchMedia?.("(orientation: landscape)").matches) { return "landscape"; }
    return "unknown";
}

function statisticsPointer() {
    if (window.matchMedia?.("(any-pointer: fine)").matches) { return "fine"; }
    if (window.matchMedia?.("(any-pointer: coarse)").matches) { return "coarse"; }
    if (window.matchMedia?.("(any-pointer: none)").matches) { return "none"; }
    return "unknown";
}

function recordVisitStatistics() {
    recordStatisticsEvent({
        event: "visit",
        referrer: document.referrer || "",
        screen_width: window.screen?.width || window.innerWidth || 0,
        screen_height: window.screen?.height || window.innerHeight || 0,
        viewport_width: window.innerWidth || 0,
        viewport_height: window.innerHeight || 0,
        pixel_ratio: window.devicePixelRatio || 1,
        color_depth: window.screen?.colorDepth || 0,
        language: navigator.language || "",
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
        theme: TV.getActiveThemePreset?.() || "default",
        orientation: statisticsOrientation(),
        pointer: statisticsPointer(),
        reduced_motion: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
            ? "reduce"
            : "no-preference",
    });
}

function recordHelpPerformance(metric, startedAt) {
    const duration = Math.max(0, performance.now() - startedAt);
    recordStatisticsEvent({ event: "help_performance", metric, duration_ms: duration });
}

function bindVisitLifecycleStatistics() {
    let activeStartedAt = document.visibilityState === "visible" ? performance.now() : null;
    let activeDuration = 0;
    let finished = false;
    const observers = [];
    const vitals = { lcp: null, cls: 0, clsObserved: false, interactions: new Map() };

    const processLcp = (entries) => {
        const last = entries[entries.length - 1];
        if (last) { vitals.lcp = last.startTime; }
    };
    const processLayoutShift = (entries) => {
        entries.forEach((entry) => {
            if (!entry.hadRecentInput) {
                vitals.cls += entry.value;
                vitals.clsObserved = true;
            }
        });
    };
    const processEventTiming = (entries) => {
        entries.forEach((entry) => {
            if (!entry.interactionId) { return; }
            const previous = vitals.interactions.get(entry.interactionId) || 0;
            vitals.interactions.set(entry.interactionId, Math.max(previous, entry.duration || 0));
        });
    };
    const observe = (type, processor, options = {}) => {
        if (!window.PerformanceObserver?.supportedEntryTypes?.includes(type)) { return; }
        try {
            const observer = new PerformanceObserver((list) => processor(list.getEntries()));
            observer.observe({ type, buffered: true, ...options });
            observers.push({ observer, processor });
        } catch {
            // Unsupported observer options are expected on older browsers.
        }
    };
    observe("largest-contentful-paint", processLcp);
    observe("layout-shift", processLayoutShift);
    observe("event", processEventTiming, { durationThreshold: 40 });

    const recordNavigation = () => {
        const navigation = performance.getEntriesByType?.("navigation")?.[0];
        if (!navigation) { return; }
        if (Number.isFinite(navigation.responseStart)) {
            recordStatisticsEvent({ event: "performance", metric: "page_ttfb", value: navigation.responseStart });
        }
        const loadEnd = navigation.loadEventEnd || performance.now();
        if (Number.isFinite(loadEnd)) {
            recordStatisticsEvent({ event: "performance", metric: "page_load", value: loadEnd });
        }
    };
    if (document.readyState === "complete") { window.setTimeout(recordNavigation, 0); }
    else { window.addEventListener("load", () => window.setTimeout(recordNavigation, 0), { once: true }); }

    const pause = () => {
        if (activeStartedAt === null) { return; }
        activeDuration += performance.now() - activeStartedAt;
        activeStartedAt = null;
    };
    const resume = () => {
        if (!finished && activeStartedAt === null && document.visibilityState === "visible") {
            activeStartedAt = performance.now();
        }
    };
    const finish = () => {
        if (finished) { return; }
        finished = true;
        pause();
        observers.forEach(({ observer, processor }) => {
            processor(observer.takeRecords());
            observer.disconnect();
        });
        recordStatisticsEvent(
            { event: "session_end", duration_ms: activeDuration },
            { beacon: true },
        );
        if (vitals.lcp !== null) {
            recordStatisticsEvent(
                { event: "performance", metric: "lcp", value: vitals.lcp },
                { beacon: true },
            );
        }
        if (vitals.clsObserved) {
            recordStatisticsEvent(
                { event: "performance", metric: "cls", value: vitals.cls },
                { beacon: true },
            );
        }
        if (vitals.interactions.size) {
            const durations = Array.from(vitals.interactions.values()).sort((left, right) => right - left);
            const interactionIndex = Math.min(durations.length - 1, Math.floor(durations.length / 50));
            recordStatisticsEvent(
                { event: "performance", metric: "inp", value: durations[interactionIndex] },
                { beacon: true },
            );
        }
    };
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") { pause(); }
        else { resume(); }
    });
    window.addEventListener("pagehide", finish, { once: true });
}

function statisticsHelpIdentity(filename, bundle = null) {
    const sourceName = bundle?.metadata?.source?.filename;
    const helpFile = String(sourceName || filename || "").trim();
    const catalogEntry = Array.isArray(catalogData)
        ? catalogData.find((entry) => {
            const sourceFiles = Array.isArray(entry?.source_files) ? entry.source_files : [];
            const candidates = [entry?.file, entry?.source_file, ...sourceFiles]
                .map((value) => String(value || "").replace(/\\/g, "/").toLowerCase());
            return candidates.includes(String(filename || "").replace(/\\/g, "/").toLowerCase())
                || candidates.includes(helpFile.replace(/\\/g, "/").toLowerCase());
        })
        : null;
    const helpName = String(catalogEntry?.name || bundle?.metadata?.name || helpFile).trim();
    return { helpFile, helpName };
}

function recordTopicOpen(bundle, contextHex, title = "") {
    const sourceName = String(bundle?.metadata?.source?.filename || bundle?._filename || "").trim();
    if (sourceName && contextHex) {
        const topic = [String(contextHex), String(title || "").trim()].filter(Boolean).join(" ");
        recordStatisticsEvent({ event: "topic_open", help_file: sourceName, topic });
    }
}

function statisticsErrorCategory(area, error) {
    const status = String(error?.message || error || "").match(/HTTP\s+(\d{3})/i)?.[1];
    const type = String(error?.name || "Error").replace(/[^A-Za-z0-9_. -]/g, "").slice(0, 32) || "Error";
    return `${String(area || "client").slice(0, 24)}:${status || type}`;
}

function bindClientErrorStatistics() {
    window.addEventListener("error", (event) => {
        if (event.target !== window) { return; }
        recordStatisticsEvent({
            event: "client_error",
            error: statisticsErrorCategory("javascript", event.error || event.message),
        });
    });
    window.addEventListener("unhandledrejection", (event) => {
        recordStatisticsEvent({
            event: "client_error",
            error: statisticsErrorCategory("promise", event.reason),
        });
    });
}

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
    const loadStartedAt = performance.now();
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
        recordHelpPerformance("load", loadStartedAt);

        let json;
        if (/\.gz$/i.test(filename)) {
            if (typeof DecompressionStream !== "function") {
                throw new Error("This browser does not support DecompressionStream for .json.gz bundles.");
            }
            const decompressStartedAt = performance.now();
            const stream = new Blob([payloadBytes]).stream().pipeThrough(new DecompressionStream("gzip"));
            json = await new Response(stream).text();
            recordHelpPerformance("decompress", decompressStartedAt);
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

function viewerUrl(params) {
    return `${window.location.pathname}?${new URLSearchParams(params)}`;
}

function bundleTargetUrl(bundle, target, currentTopic = null) {
    const entry = target.sourceFile ? findCatalogEntryBySourceFile(target.sourceFile, bundle) : null;
    if (target.sourceFile && !entry) { return "#"; }
    const file = entry?.file || bundle?._catalogFile;
    // Application context help is not part of the public HELP catalog.
    if (!file || file === CONTEXT_HELP_BUNDLE_FILE) { return "#"; }
    const destination = file === bundle?._catalogFile ? bundle : bundleCache.get(file);
    const ref = target.bundleTopic ?? target.topicAlias ?? (target.sourceFile ? null : currentTopic?.id);
    const topic = destination ? normalizeTopicRef(destination, ref)
        : (/^-?\d+$/.test(String(ref ?? "")) ? String(Number(ref)) : null);
    const params = { file };
    if (topic) {
        params.topic = topic;
        if (Number(target.topicLine) > 0) { params.line = String(target.topicLine); }
    }
    return viewerUrl(params);
}

function parseUhfTag(tagBody, bundle, topic = null) {
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
        const href = bundleTargetUrl(bundle, {
            sourceFile: linkTarget.file,
            bundleTopic: linkTarget.topic,
            topicAlias: linkTarget.alias,
            topicLine: linkTarget.line,
        }, topic);
        const attrs = [`href="${escapeHtml(href)}"`, 'data-tv-uhf-link="1"'];
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
        const action = match[1].toLowerCase();
        const href = action === "back" ? "#" : bundleTargetUrl(bundle, {});
        return {
            name: "nav",
            open: `<a href="${escapeHtml(href)}" data-tv-nav="${action}">`,
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

function renderUhfInline(text, bundle, topic = null) {
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
        const descriptor = parseUhfTag(tagBody, bundle, topic);
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
                `<a href="${escapeHtml(bundleTargetUrl(bundle, { bundleTopic: downTarget }))}" data-tv-bundle-topic="${escapeHtml(downTarget)}">&lt;more&gt;</a>`,
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
                        `<span class="code-example">${renderUhfInline(raw, bundle, topic)}</span>`
                    )
                );
            }
            return;
        }
        lineNumber += 1;
        lines.push(wrapTopicLineMarkup(lineNumber, renderUhfInline(raw, bundle, topic)));
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

const PROGRESS_BAR_MIN_VISIBLE_MS = 180;

class TVLoadingDialog extends TVDialog {
    static viewName = "loading";

    constructor(title = "Loading") {
        super(new TVRect(0, 0, 40, 9), title);
        this.setState(sfModal, true);
        this.cancelled = false;
        this.abortController = new AbortController();
        this.openedAt = 0;
        this.progressUpdates = 0;
        this.destroyTimer = null;
        this.destroyed = false;
        this.total = 1;

        const cancelButton = new TVButton(
            new TVRect(14, 5, 25, 7),
            "~C~ancel",
            "loading-cancel",
            bfDefault,
        );

        const filename = new TVStaticText(new TVRect(0, 1, 38, 2), "\x03");
        const progressBar = new TVBarGauge(new TVRect(3, 2, 35, 3), this.total);
        const percent = new TVPercentGauge(new TVRect(17, 3, 22, 4), this.total);
        const bodyGroup = new TVGroup(new TVRect(0, 0, 38, 6)).insertAll([
                filename,
                progressBar,
                percent,
                cancelButton,
            ]);

        this.insert(bodyGroup);
        this.bindDrag();
        this.bindCommonClose(() => this.cancel());

        this.filenameView = filename;
        this.barView = progressBar;
        this.percentView = percent;
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === TV.evCommand && event.command === "loading-cancel") {
            this.cancel();
            this.clearEvent(event);
        }
    }

    get signal() {
        return this.abortController.signal;
    }

    show(filename) {
        this.filenameView.setText(filename);
        this.openedAt = performance.now();
        this.progressUpdates = 0;
        this._renderRatio(0, 1);
        this.open();
    }

    update(received, total) {
        if (received > 0) {
            this.progressUpdates += 1;
        }
        this._renderRatio(received, total);
    }

    _renderRatio(received, total) {
        const nextTotal = total > 0 ? Number(total) : 1;
        if (nextTotal !== this.total) {
            this.total = nextTotal;
            this.broadcast(cmResetGauge, null, this.total);
        }
        const progress = Math.min(Math.max(0, Number(received) || 0), this.total);
        this.broadcast(cmUpdateGauge, null, progress);
    }

    _finalizeDestroy() {
        if (this.destroyed) {
            return;
        }
        if (this.destroyTimer !== null) {
            window.clearTimeout(this.destroyTimer);
            this.destroyTimer = null;
        }
        super.destroy();
    }

    cancel() {
        this.cancelled = true;
        this.abortController.abort();
        this.destroy(true);
    }

    destroy(immediate = false) {
        if (this.destroyed) {
            return;
        }
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

class TVWindowList extends TVListBox {
    static viewName = "winlist-listviewer";

    defaultContent(item) { return escapeHtml(item?.label || ""); }
}

class TVWindowListDialog extends TVDialog {
    static viewName = "winlist";

    constructor() {
        super(new TVRect(0, 0, 40, 14), "Window List");
        this.setState(sfModal, true);
        this.list = new TVWindowList(new TVRect(1, 1, 37, 11));
        const main = new TVGroup(new TVRect(0, 0, 38, 12)).insertAll([this.list]);
        this.insert(main);
    }
}

class TVWelcomeDialog extends TVDialog {
    static viewName = "welcome";

    constructor() {
        super(new TVRect(0, 0, 34, 12), "Welcome");
        this.setState(sfModal, true);
        this.accept = null;
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === TV.evCommand && event.command === "welcome-ok") {
            this.accept?.();
            this.clearEvent(event);
        }
    }
}

// ── Window rendering ────────────────────────────────────────────────

function buildWindow(bundle, contentHTML, caption) {
    const w = bundleWindowSpec(bundle);
    const windowView = new TVHelpWindow(
        new TVRect(0, 0, w.cols, w.rows),
        bundle,
        caption,
        wnNoNumber,
    );
    windowView.minSize = new TVPoint(w.min_cols, w.min_rows);
    windowView.setContent(contentHTML);
    const windowEl = TVView._fromHTML(windowView.draw());
    windowView.resolve(windowEl);
    windowEl._tvWindowView = windowView;
    windowEl.dataset.tvBundleWindow = bundleWindowKey(bundle);
    const themeStyle = bundleUiThemeStyle(bundle);
    if (themeStyle) { windowEl.style.cssText += `;${themeStyle}`; }
    return windowEl;
}

// ── Index page rendering ────────────────────────────────────────────

function renderBundleIndex(bundle) {
    const navItems = [];
    const sections = [];
    const groups = Array.isArray(bundle.index) ? bundle.index : [];
    const byLetter = new Map(groups.map((group) => [String(group.group || ""), group]));
    if (byLetter.has("#")) {
        sections.push(renderIndexSection("#", "#", byLetter.get("#").entries || [], bundle));
    }
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((letter) => {
        const group = byLetter.get(letter);
        if (group && Array.isArray(group.entries) && group.entries.length) {
            navItems.push(`<a class="tv-index-jump" href="#idx-${letter}" data-letter="${letter}">${letter}</a>`);
            sections.push(renderIndexSection(letter, letter, group.entries, bundle));
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

function renderIndexSection(anchor, label, entries, bundle) {
    const items = entries.map((entry) => {
        if (entry == null || entry.topic_id == null) {
            const targetData = buildBundleTargetData(entry || {});
            if (!Object.keys(targetData).length) {
                return `<div class="tv-index-entry"><span>${escapeHtml(entry && entry.label ? entry.label : "")}</span></div>`;
            }
            return `<div class="tv-index-entry"><a ${renderHtmlAttributes({ href: bundleTargetUrl(bundle, targetData), ...TVView._controlAttrs({ commandData: targetData }) })}>${escapeHtml(entry.label || "")}</a></div>`;
        }
        const targetData = buildBundleTargetData({
            topic_id: entry.topic_id,
            file: entry.file,
            alias: entry.alias,
            line: entry.line,
        });
        return `<div class="tv-index-entry"><a ${renderHtmlAttributes({ href: bundleTargetUrl(bundle, targetData), ...TVView._controlAttrs({ commandData: targetData }) })}>${escapeHtml(entry.label)}</a></div>`;
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

class TVContentsOutline extends TVOutline {
    static viewName = "contents-outline";

    hasScrollbar() { return false; }

    getKey(node) { return node?._outlineKey; }

    getLabel(node) { return node?.label || ""; }

    renderNodeContent(node) {
        const label = escapeHtml(String(node?.label || ""));
        const targetData = buildBundleTargetData(node);
        return Object.keys(targetData).length
            ? `<a ${renderHtmlAttributes({ href: bundleTargetUrl(this.bundle, targetData), "data-tv-uhf-link": "1", ...TVView._controlAttrs({ commandData: targetData }) })}>${label}</a>`
            : label;
    }
}

function renderBundleContents(bundle) {
    const outline = new TVContentsOutline(new TVRect());
    return [
        `<div class="tv-document tv-index-document tv-contents-document">`,
        `<div class="tv-index-heading">Contents</div>`,
        `<div class="tv-contents-tree">`,
        outline.draw(),
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
            href: bundleTargetUrl(bundle, { bundleTopic: topic.id }),
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

function buildBundleTargetData(target) {
    const data = {};
    if (target && target.topic_id != null) {
        data.bundleTopic = String(target.topic_id);
    }
    if (target && target.file) {
        data.sourceFile = String(target.file);
    }
    if (target && target.alias) {
        data.topicAlias = String(target.alias);
    }
    if (target && target.line != null) {
        data.topicLine = String(target.line);
    }
    return data;
}

function renderHtmlAttributes(attrs) {
    return Object.entries(attrs)
        .map(([key, value]) => `${key}="${escapeHtml(String(value))}"`)
        .join(" ");
}

function renderContentsNodes(nodes, bundle) {
    return nodes.map((node) => {
        const label = escapeHtml(String(node.label || ""));
        const targetData = buildBundleTargetData(node);
        const labelHTML = Object.keys(targetData).length
            ? `<a ${renderHtmlAttributes({ href: bundleTargetUrl(bundle, targetData), "data-tv-uhf-link": "1", ...TVView._controlAttrs({ commandData: targetData }) })}>${label}</a>`
            : label;
        const children = Array.isArray(node.children) && node.children.length
            ? `<div class="tv-contents-children">${renderContentsNodes(node.children, bundle)}</div>`
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
    const windowView = windowEl._tvWindowView;
    if (windowView?.outline) {
        windowView.outline.destroy();
        windowView.outline = null;
    }
    if (windowView?.findEditor) {
        windowView.findEditor.destroy();
        windowView.findEditor = null;
    }
    if (windowView?.editor) {
        windowView.editor.destroy();
        windowView.editor = null;
    }
    const scrollbars = windowView?.scrollbars || [];
    scrollbars.forEach((scrollbar) => scrollbar.destroy());
    if (windowView) { windowView.scrollbars = []; }
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
        recordTopicOpen(bundle, normalized, bundleTopicTitle(bundle, topic));
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
                return true;
            }
            console.warn(`Bundle not found for source file: ${sourceFile}`);
            return false;
        }
        const bundle = await loadBundle(entry.file);
        const normalizedTopic = topicRef != null ? String(topicRef).trim() : "";
        const resolvedTopic = normalizedTopic ? normalizeTopicRef(bundle, normalizedTopic) : null;
        if (resolvedTopic) {
            this.showTopic(bundle, resolvedTopic, lineNumber);
            return true;
        }
        if (showFallback(bundle, resolveMissingSourceTopicFallback(bundle, sourceFile, normalizedTopic))) {
            return true;
        }
        const fallback = bundleTopicFallbackRef(bundle);
        if (fallback) {
            this.showTopic(bundle, fallback, lineNumber);
            return true;
        }
        this.showContents(bundle);
        return true;
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
        const bundle = windowEl?._tvWindowView?.bundle || null;
        if (!windowEl || !bundle) {
            return null;
        }
        this.currentBundle = bundle;
        const helpWindow = windowEl._tvWindowView;
        this.currentContextHex = helpWindow.currentTopic;
        this.currentLineNumber = this._normalizeLineNumber(helpWindow.currentLine);
        this.currentView = helpWindow.currentView;
        this.currentTag = helpWindow.currentTag ? { ...helpWindow.currentTag } : null;
        return bundle;
    }

    _openWindow(bundle, contentHTML, caption) {
        const renderStartedAt = performance.now();
        const key = bundleWindowKey(bundle);
        const applyStateData = (windowEl) => {
            const helpWindow = windowEl._tvWindowView;
            helpWindow.onLink = (link) => { void this._handleTopicLink(windowEl, link); };
            helpWindow.sourceFile = bundle._catalogFile || "";
            helpWindow.currentView = this.currentView || "index";
            helpWindow.currentTopic = this.currentContextHex || null;
            helpWindow.currentLine = this.currentLineNumber || null;
            helpWindow.currentTag = this.currentTag ? { ...this.currentTag } : null;
        };
        const existing = this.openWindows.get(key);
        if (existing) {
            const helpWindow = existing._tvWindowView;
            helpWindow.bundle = bundle;
            helpWindow.viewer.bundle = bundle;
            if (helpWindow.outline) {
                helpWindow.outline.destroy();
                helpWindow.outline = null;
            }
            if (helpWindow.findEditor) {
                helpWindow.findEditor.destroy();
                helpWindow.findEditor = null;
            }
            helpWindow.setContent(contentHTML);
            helpWindow.title = caption;
            const captionEl = existing.querySelector(".tv-window-caption");
            if (captionEl) {
                captionEl.textContent = caption;
            }
            highlightCodeExamples(existing);
            this._initContentsOutline(existing, bundle);
            applyStateData(existing);
            if (this.dialogManager) { this.dialogManager.activateWindow("help:" + key); }
            fillBorders();
            recordHelpPerformance("render", renderStartedAt);
            return existing;
        }

        const windowEl = buildWindow(bundle, contentHTML, caption);
        this.desktop.appendChild(windowEl);
        bindCloseButtons(windowEl);
        this.openWindows.set(key, windowEl);
        applyStateData(windowEl);
        this._initWindowWidgets(windowEl);
        highlightCodeExamples(windowEl);
        this._initContentsOutline(windowEl, bundle);
        windowEl._tvWindowView.closeAction = () => this.close(key);
        windowEl._tvWindowView.zoomAction = () => this.toggleZoom(windowEl);
        if (this.dialogManager) {
            this.dialogManager.registerWindow("help:" + key, windowEl, {
                [TV_COMMANDS.CLOSE]: () => this.close(key),
                [TV_COMMANDS.ZOOM]: () => this.toggleZoom(windowEl),
            });
        }
        fillBorders();
        fillDesktopPatterns();
        recordHelpPerformance("render", renderStartedAt);
        return windowEl;
    }

    _initWindowWidgets(windowEl) {
        const frames = Array.from(windowEl.querySelectorAll("[data-tv-scroll-frame]"))
            .filter((frame) => !frame.hasAttribute("data-tv-outline"));
        const windowView = windowEl._tvWindowView;
        windowView.scrollbars = Array.from(
            frames,
            (frame) => new TVScrollBar(new TVRect()).bindRoot(frame),
        );
        this.scrollbars.push(...windowView.scrollbars);
        const resizer = new TurboVisionWindowResizer(windowEl, "help:" + bundleWindowKey(windowEl._tvWindowView.bundle));
        this.resizers.push(resizer);
    }

    _initContentsOutline(windowEl, bundle) {
        const root = windowEl.querySelector("[data-tv-contents-outline]");
        if (!root || !Array.isArray(bundle.contents)) { return; }
        const withKeys = (nodes, prefix = "") => nodes.map((node, index) => ({
            ...node,
            _outlineKey: `${prefix}${index}`,
            children: withKeys(Array.isArray(node.children) ? node.children : [], `${prefix}${index}/`),
        }));
        const outline = new TVContentsOutline(new TVRect()).bindRoot(root);
        outline.bundle = bundle;
        const windowView = windowEl._tvWindowView;
        outline.setScrollViewport(
            windowEl.querySelector(".tv-frame > .tv-scroll-shell > .tv-viewport"),
            windowView.scrollbars[0] || null,
        );
        outline.setTree(withKeys(bundle.contents), null, { expandAll: true });
        outline.bind({
            onActivate: (node) => {
                const target = buildBundleTargetData(node);
                if (Object.keys(target).length) { void this._openTopicTarget(windowEl, target); }
            },
        });
        windowView.outline = outline;
        windowView.scrollbars.forEach((scrollbar) => scrollbar.refresh());
    }

    _destroyWindowWidgets(windowEl) {
        const scrollbars = windowEl?._tvWindowView?.scrollbars || [];
        const resizer = windowEl?._tvResizer || null;
        destroyWindowWidgets(windowEl);
        this.scrollbars = this.scrollbars.filter((widget) => !scrollbars.includes(widget));
        this.resizers = this.resizers.filter((widget) => widget !== resizer);
    }

    async _handleTopicLink(windowEl, link) {
        const currentBundle = windowEl._tvWindowView.bundle;
        if (link.hasAttribute("data-tv-nav")) {
            const action = (link.getAttribute("data-tv-nav") || "").toLowerCase();
            if (action === "back") { this.goBack(); }
            else if (action === "index") { this.showIndex(currentBundle); }
            else if (action === "contents") { this.showContents(currentBundle); }
            recordStatisticsEvent({ event: "link", result: "internal" });
            return;
        }

        if (link.hasAttribute("data-letter")) {
            const letter = link.getAttribute("data-letter");
            const section = windowEl.querySelector(`#idx-${letter}`);
            section?.scrollIntoView({ behavior: "smooth", block: "start" });
            recordStatisticsEvent({ event: "link", result: section ? "internal" : "broken" });
            return;
        }

        if (link.hasAttribute("data-tv-topic-tag-key")) {
            this.showTag(
                currentBundle,
                link.dataset.tvTopicTagKey,
                link.dataset.tvTopicTagValue,
                link.dataset.tvTopicTagLabel,
            );
            recordStatisticsEvent({ event: "link", result: "internal" });
            return;
        }

        return this._openTopicTarget(windowEl, {
            sourceFile: link.dataset.tvSourceFile,
            bundleTopic: link.dataset.tvBundleTopic,
            topicAlias: link.dataset.tvTopicAlias,
            topicLine: link.dataset.tvTopicLine,
        });
    }

    async _openTopicTarget(windowEl, target) {
        const currentBundle = windowEl._tvWindowView.bundle;
        const sourceFile = target.sourceFile || "";
        const lineNumber = this._normalizeLineNumber(target.topicLine);
        const topicRef = (target.bundleTopic || target.topicAlias || "").trim();
        try {
            let opened = false;
            if (sourceFile) {
                opened = await this.openSourceTopic(sourceFile, topicRef, lineNumber, currentBundle);
            } else if (topicRef) {
                opened = this.showTopic(currentBundle, topicRef, lineNumber);
            } else if (lineNumber) {
                this._pushHistory();
                this._focusTopicLine(windowEl, lineNumber);
                this.currentLineNumber = lineNumber;
                windowEl._tvWindowView.currentLine = lineNumber;
                if (this.onNavigate) { this.onNavigate(""); }
                opened = true;
            }
            recordStatisticsEvent({ event: "link", result: opened ? "internal" : "broken" });
        } catch (error) {
            console.error("Failed to open linked topic", error);
            recordStatisticsEvent({ event: "link", result: "broken" });
        }
    }

    toggleZoom(windowEl) {
        if (!windowEl) {
            // Zoom the first open window
            const first = this.openWindows.values().next().value;
            if (!first) { return; }
            windowEl = first;
        }
        windowEl._tvWindowView?.zoom();
        fillDesktopPatterns();
    }

    close(key) {
        const existing = this.openWindows.get(key);
        if (existing) {
            this._destroyWindowWidgets(existing);
            existing._tvWindowView?.destroy();
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
            el._tvWindowView?.destroy();
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

    _placeWindow(element, left, top, cols, rows) {
        if (element._tvResizer) {
            element._tvResizer.place({ left, top, cols, rows });
        } else {
            applyWindowGeometry(element, [left, top, cols, rows, 0]);
        }
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
            this._placeWindow(el, col * wCols * cell.width, row * wRows * cell.height, wCols, wRows);
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
            this._placeWindow(el, i * step * cell.width, i * step * cell.height, baseCols, baseRows);
        });
        fillBorders();
        fillDesktopPatterns();
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
    }

}

// ── Catalog menu items ──────────────────────────────────────────────

const menuActions = new WeakMap();

class TVBundleMenuItem extends TVMenuItem {
    getUrl() {
        const action = menuActions.get(this) || {};
        if (this.command === "bundle-open") { return viewerUrl({ file: action.value }); }
        if (this.command === "doc-open") { return viewerUrl({ doc: action.value }); }
        if (this.command === "menu-link") { return bundleTargetUrl(action.bundle, action); }
        return "";
    }
}

function withMenuAction(item, action = {}) {
    menuActions.set(item, action);
    return item;
}

function menuFromItems(items) {
    const linked = items.filter((item) => item instanceof TVMenuItem);
    linked.forEach((item, index) => { item.next = linked[index + 1] || null; });
    return new TVMenu(linked[0] || null);
}

function renderMenuPopupSeparator() {
    return NewLine();
}

function renderMenuSubmenu(label, items, helpCtx = hcNoContext) {
    return NewSubMenu(label, helpCtx, menuFromItems(items));
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
            group,
            groupEntries.map((entry) => renderItem(entry)),
        ));
        needSep = false;
    });

    return items;
}

function catalogMenuEntryButton(entry) {
    return withMenuAction(
        new TVBundleMenuItem(entry.menu_name || entry.name, "bundle-open"),
        { value: entry.file, bundleLabel: bundleLoadingLabel(entry) },
    );
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
    const openItem = new TVMenuItem("~O~pen...", "file-open");
    const changeDirectoryItem = withMenuAction(
        new TVMenuItem("~C~hange dir...", "dialog-open"),
        { value: "chdir" },
    );
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
            productItems.push(renderMenuSubmenu(versionNode.key, versionNode.direct));
        });
        items.push(renderMenuSubmenu(productNode.key, productItems));
    });
    return items;
}

function buildDocsMenuItems(docs) {
    return buildGroupedMenuItems(docs, (entry) =>
        withMenuAction(new TVBundleMenuItem(entry.name, "doc-open"), { value: entry.file })
    );
}

function buildBundleContentsMenuItems(nodes, bundle) {
    if (!Array.isArray(nodes)) { return []; }
    const items = [];

    nodes.forEach((node) => {
        const label = String((node && node.label) || "").trim();
        if (!label) { return; }

        const childItems = buildBundleContentsMenuItems(node.children || [], bundle);
        const targetData = buildBundleTargetData(node);
        const hasTarget = Object.keys(targetData).length > 0;
        const menuLabel = renderBundleMenuLabel(label, node && node.hotkey);

        if (childItems.length) {
            const subItems = [];
            if (hasTarget) {
                subItems.push(withMenuAction(
                    new TVBundleMenuItem(menuLabel, "menu-link"),
                    { ...targetData, bundle },
                ));
                subItems.push(renderMenuPopupSeparator());
            }
            subItems.push(...childItems);
            items.push(renderMenuSubmenu(menuLabel, subItems));
            return;
        }

        if (hasTarget) {
            items.push(withMenuAction(
                new TVBundleMenuItem(menuLabel, "menu-link"),
                { ...targetData, bundle },
            ));
            return;
        }

        items.push(new TVMenuItem(label).setDisabled());
    });

    return items;
}

function renderBundleMenuLabel(label, hotkey = "") {
    const cleanLabel = String(label || "");
    const cleanHotkey = String(hotkey || "").trim();
    if (!cleanHotkey) {
        return cleanLabel;
    }
    const matchIndex = cleanLabel.toLowerCase().indexOf(cleanHotkey.toLowerCase());
    if (matchIndex < 0) {
        return cleanLabel;
    }
    const markedLabel = cleanLabel.slice(0, matchIndex)
        + "~" + cleanLabel[matchIndex] + "~"
        + cleanLabel.slice(matchIndex + 1);
    return markedLabel;
}

function buildBundleContentsSubMenu(bundle) {
    const sourceFormat = bundleSourceFormat(bundle);
    const rawNodes = Array.isArray(bundle && bundle.contents) ? bundle.contents : [];
    const nodes = sourceFormat === "bw03"
        ? rawNodes.map((node) => ({ ...(node || {}), children: [] }))
        : rawNodes;
    if (!nodes.length) {
        return null;
    }

    const items = buildBundleContentsMenuItems(nodes, bundle);
    if (!items.length) {
        return null;
    }

    return renderMenuSubmenu(
        nodes.some((node) => node && node.hotkey) ? "~M~enu" : "~C~ontents",
        items,
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
    let paragraphLines = [];

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
    function closeParagraph() {
        if (!paragraphLines.length) { return; }
        html.push(`<p>${inlineMarkup(paragraphLines.join("\n")).replace(/ {2}\n/g, "<br>")}</p>`);
        paragraphLines = [];
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
            closeParagraph();
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
            closeParagraph();
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
        if (!line.trim()) { closeParagraph(); closeList(); html.push("<p></p>"); continue; }
        // Headings
        const hMatch = line.match(/^(#{1,6})\s+(.*)/);
        if (hMatch) {
            closeParagraph();
            closeList();
            const level = hMatch[1].length;
            html.push(`<h${level}>${inlineMarkup(hMatch[2])}</h${level}>`);
            continue;
        }
        // Horizontal rule
        if (/^[-*_]{3,}\s*$/.test(line)) { closeParagraph(); closeList(); html.push("<hr>"); continue; }
        // Unordered list
        const ulMatch = line.match(/^(\s*)[-*+]\s+(.*)/);
        if (ulMatch) {
            closeParagraph();
            if (!inList || listTag !== "ul") { closeList(); html.push("<ul>"); inList = true; listTag = "ul"; }
            html.push(`<li>${inlineMarkup(ulMatch[2])}</li>`);
            continue;
        }
        // Ordered list
        const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
        if (olMatch) {
            closeParagraph();
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
        // A physical Markdown line break is a space inside the same paragraph.
        closeList();
        paragraphLines.push(line);
    }
    if (inCode && codeLines) {
        html.push("<pre>" + codeLines.join("\n") + "</pre>");
    }
    closeParagraph();
    closeList();
    closeTable();
    return html.join("");
}

// ── Menu bar for bundle page ────────────────────────────────────────

function buildBundleMenuBar(catalog, activeBundle = null, session = null, dosWindow = null) {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    if (!menuBar) { return; }
    const dialogItem = (label, name) => withMenuAction(
        new TVMenuItem(label, "dialog-open"),
        { value: name },
    );
    const saverItems = [
        ["~S~tars", "stars"], ["~B~ounce", "bounce"],
        ["Cloc~k~", "clock"], ["~M~atrix", "matrix"],
        ["~P~rojector", "projector"],
    ].map(([label, mode]) => withMenuAction(
        new TVMenuItem(label, "saver-start"),
        { value: mode },
    ));
    const systemItems = [
        dialogItem("Ca~l~endar", "calendar"),
        dialogItem("Ascii ~T~able", "ascii"),
        dialogItem("~C~alculator", "calc"),
        dialogItem("~M~IDI Player", "midi"),
        dialogItem("C~o~lors", "colors"),
        dialogItem("~W~idget Gallery", "widgets"),
        dialogItem("~G~rid Viewer", "grid"),
        dialogItem("Server ~T~erminal", "terminal"),
        new TVMenuItem("DOS ~P~rompt", "dos-open", 0, hcDosPrompt),
        dialogItem("S~t~atistics", "statistics"),
        dialogItem("System ~I~nformation", "systeminfo"),
        NewLine(),
        renderMenuSubmenu("~S~creen saver", saverItems, hcSystemMenu),
        NewLine(),
        ...[["~L~ight Theme", "light"], ["~D~ark Theme", "dark"], ["A~u~to Theme", "auto"]]
            .map(([label, theme]) => withMenuAction(
                new TVMenuItem(label, "theme-set"),
                { value: theme },
            )),
    ];

    const findItem = new TVMenuItem("~F~ind", "find", kbCtrlF, hcNoContext, "Ctrl-F");
    const findAgainItem = new TVMenuItem("Find ~A~gain", "find-again", kbCtrlL, hcNoContext, "Ctrl-L");
    const searchItems = [
        findItem,
        findAgainItem,
        withMenuAction(
            new TVMenuItem("Search ~T~opics", "dialog-open", kbF3, hcNoContext, "F3"),
            { value: "search" },
        ),
    ];

    const winPopupItems = [
        { cmd: "tile", label: "~T~ile", hotkey: "" },
        { cmd: "cascade", label: "C~a~scade", hotkey: "" },
        { cmd: "list", label: "Window ~L~ist", hotkey: "Alt-0" },
        { cmd: "zoom", label: "~Z~oom", hotkey: "F5" },
        { cmd: "next", label: "~N~ext", hotkey: "F6" },
        { cmd: "previous", label: "~P~revious", hotkey: "Shift-F6" },
        { cmd: "close", label: "~C~lose", hotkey: "Alt-F3" },
    ];
    const windowItems = new Map();
    const windowsItems = winPopupItems.map((entry) => {
        const item = withMenuAction(
            new TVMenuItem(
                entry.label,
                "window-cmd",
                ({ zoom: kbF5, next: kbF6, previous: kbShiftF6, close: kbAltF3, list: kbAlt0 })[entry.cmd] || 0,
                hcNoContext,
                entry.hotkey,
            ),
            { value: entry.cmd },
        );
        windowItems.set(entry.cmd, item);
        return item;
    });

    const gamesPopupItems = [
        ["~B~reakOut", "breakout"], ["Tower of ~H~anoi", "hanoi"],
        ["~L~ines", "lines"], ["L~u~do", "ludo"],
        ["M~a~stermind", "mastermind"], ["~M~ines", "mines"],
        ["~P~uzzle", "puzzle"], ["~R~eversi", "reversi"],
        ["S~n~ake", "snake"], ["~S~okoban", "sokoban"],
        ["~T~etris", "tetris"], ["Tr~o~n Light Cycles", "tron"],
    ];
    const helpItems = [
        new TVMenuItem("~C~ontext Help", "context-help", kbF1, hcNoContext, "F1"),
        new TVMenuItem("~I~ndex", "context-help-index"),
        NewLine(),
        dialogItem("~A~bout", "about"),
    ];
    const topItems = [
        renderMenuSubmenu("~≡~", systemItems, hcSystemMenu),
        renderMenuSubmenu("Help ~F~iles", buildCatalogMenuItems(catalog), hcHelpFiles),
        renderMenuSubmenu("~D~ocs", buildDocsMenuItems(docsCatalogData || []), hcDocuments),
        renderMenuSubmenu("~S~earch", searchItems, hcSearch),
        renderMenuSubmenu(
            "~G~ames",
            gamesPopupItems.map(([label, name]) => dialogItem(label, name)),
            hcGames,
        ),
        renderMenuSubmenu("~W~indows", windowsItems, hcWindows),
        renderMenuSubmenu("~H~elp", helpItems, hcContextHelp),
    ];
    const contents = dosWindow?.active ? null : buildBundleContentsSubMenu(activeBundle);
    if (contents) { topItems.push(contents); }
    if (dosWindow?.active) {
        const command = (label, name, disabled = false, shortcut = "") => new TVMenuItem(label, name, 0, hcDosPrompt, shortcut).setDisabled(disabled);
        const ready = Boolean(dosWindow.view.ci) && !dosWindow.busy;
        topItems.push(renderMenuSubmenu("D~O~S Prompt", [
            command(dosWindow.paused ? "~R~esume" : "~P~ause", "dos-pause", !ready, "Alt-Pause"),
            command("Res~t~art", "dos-restart", dosWindow.busy, "Ctrl-Alt-R"),
            command("~S~ave C to cloud", "dos-save", !ready || !dosWindow.session?.account),
            NewLine(),
            command("Mount ~C~D...", "dos-mount-cd", !ready || !dosWindow.session?.account),
            command("Mount ~F~loppy...", "dos-mount-floppy", !ready || !dosWindow.session?.account),
            command("~E~ject media", "dos-eject", !ready || !dosWindow.media),
            NewLine(), command(dosWindow.zoomGeometry ? "~Z~oom back" : "~Z~oom 2×", "dos-zoom"),
            command("F~u~llscreen", "dos-fullscreen", false, "Alt-Enter"), command("C~l~ose", "dos-close"),
        ], hcDosPrompt));
    }

    const accountItem = buildAccountMenu(session);
    topItems.push(accountItem);
    const menuView = new TVApplicationMenuBar(new TVRect(), menuFromItems(topItems), accountItem);
    menuBar.innerHTML = menuView.draw()
        + '<div class="tv-menu-clock" data-tv-clock>00:00:00</div>';
    menuView.bindRoot(menuBar);
    return { view: menuView, findItem, findAgainItem, windowItems };
}

// ── Bundle application ──────────────────────────────────────────────

class TVBundleApp extends TVProgram {
    constructor() {
        super(new TVRect());
        this.desktop = null;
        this.desktopView = null;
        this.windowManager = null;
        this.dialogManager = null;
        this.menuController = null;
        this.helpController = null;
        this.docWindows = new Map();
        this._menuBundleKey = "";
        this._stateSyncTimer = null;
        this._restoringUrlState = false;
        this._lastUrlStateHash = "";
        this._catalogReady = null;
        this.lastFindTarget = null;
        this.errorMessageBox = null;
        this.localLinkHandler = null;
        this.statisticsTargets = new Map();
        this.isAdmin = false;
        this.authSession = null;
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evKeyDown) {
            const keyEvent = event.nativeEvent;
            const activeDialog = this.dialogManager?.get(this.dialogManager.activeTarget);
            if (activeDialog?.isOpen()) {
                activeDialog.dispatchEvent(new TVEvent(evKeyDown, {
                    infoPtr: activeDialog,
                    nativeEvent: keyEvent,
                }));
                activeDialog.onDialogKeyDown(keyEvent);
            }
            if (!keyEvent || keyEvent.defaultPrevented) {
                this.clearEvent(event);
                return;
            }
            const key = String(keyEvent.key || "").toLocaleLowerCase();
            if ((keyEvent.ctrlKey || keyEvent.metaKey) && !keyEvent.altKey && key === "f") {
                keyEvent.preventDefault();
                this._openFind();
            } else if ((keyEvent.ctrlKey || keyEvent.metaKey) && !keyEvent.altKey && key === "l") {
                keyEvent.preventDefault();
                this._findAgain();
            } else if (keyEvent.key === "F3" && !keyEvent.altKey && !keyEvent.ctrlKey && !keyEvent.metaKey && !keyEvent.shiftKey) {
                keyEvent.preventDefault();
                this.dialogManager.open("search");
            } else if (keyEvent.key === "F5" && !keyEvent.ctrlKey && !keyEvent.altKey && !keyEvent.shiftKey) {
                keyEvent.preventDefault();
                this.dialogManager.dispatchCommand(TV_COMMANDS.ZOOM);
            } else if (keyEvent.key === "F3" && keyEvent.altKey && !keyEvent.ctrlKey && !keyEvent.shiftKey) {
                keyEvent.preventDefault();
                this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE);
            } else if (keyEvent.key === "0" && keyEvent.altKey && !keyEvent.ctrlKey && !keyEvent.shiftKey) {
                keyEvent.preventDefault();
                this._showWindowList();
            } else if (keyEvent.key === "F6" && !keyEvent.altKey && !keyEvent.ctrlKey && !keyEvent.metaKey) {
                keyEvent.preventDefault();
                this.dialogManager.dispatchCommand(keyEvent.shiftKey ? TV_COMMANDS.PREVIOUS : TV_COMMANDS.NEXT);
            } else {
                return;
            }
            this.clearEvent(event);
            return;
        }
        if (event.what !== TV.evCommand) { return; }
        const control = event.infoPtr;
        const action = control instanceof TVMenuItem ? (menuActions.get(control) || {}) : {};
        const value = action.value ?? (control instanceof TVStatusItem
            ? (control.param && typeof control.param === "object" ? control.param.value : control.param)
            : "") ?? "";
        let handled = true;
        if (event.command === "context-help") {
            recordStatisticsEvent({ event: "tool_open", name: "context-help" });
            this.helpController?.request();
        } else if (event.command === "context-help-index") {
            void this._openContextHelpIndex();
        } else if (event.command === "find") {
            this._openFind();
        } else if (event.command === "find-again") {
            this._findAgain();
        } else if (event.command === "file-open") {
            this.dialogManager.open("fileopen");
        } else if (event.command === "dos-open") {
            void this._openDosPrompt();
        } else if (String(event.command).startsWith("dos-")) {
            this.dosWindow?.handleEvent(event);
            return;
        } else if (event.command === "account-logout") {
            this.dialogManager.open("login");
            this.dialogManager.get("login")?.handleEvent(new TVEvent(TV.evCommand, { command: "login-sign-out" }));
        } else if (String(event.command).startsWith("account-")) {
            if (["account-rebuild-dos", "account-rebuild-midi"].includes(event.command)) {
                if (this.isAdmin && this.authSession?.development) {
                    this.dialogManager.open("server-configuration");
                    this.serverConfigDialog?.handleEvent(new TVEvent(TV.evCommand, {
                        command: event.command.replace("account-", "server-"),
                    }));
                }
                this.clearEvent(event); return;
            }
            const name = event.command === "account-login" ? "login" : event.command.slice(8);
            if (["server-configuration", "registration-token"].includes(name) && !this.isAdmin) { this.clearEvent(event); return; }
            this.dialogManager.open(name);
        } else if (event.command === "dialog-open") {
            this.dialogManager.open(value);
        } else if (event.command === "theme-set") {
            recordStatisticsEvent({ event: "tool_open", name: `theme-${value || "default"}` });
            applyThemeAndSyncPalette(value || "default", true);
            this.dialogManager.applyActiveStates();
            fillBorders();
        } else if (event.command === "bundle-open") {
            void this._openBundleFile(value, action.bundleLabel || "");
        } else if (event.command === "doc-open") {
            void this._openDocFile(value);
        } else if (event.command === "menu-link") {
            void this._openMenuLink(action);
        } else if (event.command === "window-cmd") {
            this._dispatchWindowCommand(value);
        } else if (event.command === "saver-start") {
            const saver = TVScreenSaver?.modes?.[value];
            if (saver) {
                recordStatisticsEvent({ event: "tool_open", name: `screen-saver-${value}` });
                new saver().start();
            }
        } else if (event.command === "bundle-back") {
            this.windowManager?.goBack();
        } else if (event.command === "bundle-index") {
            if (this.windowManager?.currentBundle) {
                this.windowManager.showIndex(this.windowManager.currentBundle);
            }
        } else if (event.command === "bundle-help-contents") {
            if (this.windowManager?.currentBundle) {
                this.windowManager.showHelpContentsTopic(this.windowManager.currentBundle);
            }
        } else if (event.command === "bundle-contents") {
            if (this.windowManager?.currentBundle) {
                this.windowManager.showContents(this.windowManager.currentBundle);
            }
        } else if (event.command === "bundle-close-all") {
            this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE);
        } else {
            handled = false;
        }
        if (handled) { this.clearEvent(event); }
    }

    async _openMenuLink(action) {
        if (!action || !this.windowManager?.currentBundle) { return; }
        const sourceFile = action.sourceFile || "";
        const lineNumber = this.windowManager._normalizeLineNumber(action.topicLine);
        const topicRef = String(action.bundleTopic || action.topicAlias || "").trim();
        if (sourceFile) {
            await this.windowManager.openSourceTopic(
                sourceFile,
                topicRef,
                lineNumber,
                this.windowManager.currentBundle,
            );
        } else if (topicRef) {
            this.windowManager.showTopic(this.windowManager.currentBundle, topicRef, lineNumber);
        }
    }

    _dispatchWindowCommand(command) {
        if (command === "zoom") { this.dialogManager.dispatchCommand(TV_COMMANDS.ZOOM); }
        else if (command === "close") { this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE); }
        else if (command === "next") { this.dialogManager.dispatchCommand(TV_COMMANDS.NEXT); }
        else if (command === "previous") { this.dialogManager.dispatchCommand(TV_COMMANDS.PREVIOUS); }
        else if (command === "tile") { this.windowManager.tile(); }
        else if (command === "cascade") { this.windowManager.cascade(); }
        else if (command === "list") { this._showWindowList(); }
    }

    _statisticsTarget(managerName) {
        const dialog = this.dialogManager.dialogs.get(managerName);
        if (dialog?.isOpen()) {
            if (dialog instanceof TVGameDialog && dialog.hallOfFameGame) {
                return {
                    scope: "game",
                    name: String(dialog.hallOfFameGame),
                    view: dialog,
                };
            }
            return {
                scope: "dialog",
                name: statisticsDialogName(managerName),
                view: dialog,
            };
        }

        const windowEl = this.dialogManager.windows.get(managerName);
        if (!windowEl?.isConnected) { return null; }
        if (managerName === "dos:prompt") {
            const view = windowEl._tvWindowView;
            return {
                scope: "tool", name: "dos-prompt", view,
                isRunning: () => Boolean(view?.view.ci) && !view.paused && !view.busy,
            };
        }
        if (managerName.startsWith("help:")) {
            const bundle = windowEl._tvWindowView?.bundle || null;
            const identity = statisticsHelpIdentity(bundle?._catalogFile || managerName.slice(5), bundle);
            if (!identity.helpName) { return null; }
            return {
                scope: "help",
                name: identity.helpName,
                helpFile: identity.helpFile,
                view: windowEl._tvWindowView || windowEl,
            };
        }
        if (managerName.startsWith("doc:")) {
            const name = managerName.slice(4);
            return name ? { scope: "document", name, view: windowEl._tvWindowView || windowEl } : null;
        }
        return null;
    }

    _startStatisticsTarget(managerName, target) {
        const session = {
            ...target,
            activeDuration: 0,
            activeStartedAt: null,
        };
        this.statisticsTargets.set(managerName, session);
        if (target.scope === "help") {
            recordStatisticsEvent({
                event: "help_open",
                help_file: target.helpFile,
                help_name: target.name,
            });
        } else if (target.scope === "document") {
            recordStatisticsEvent({ event: "doc_open", document: target.name });
        } else if (target.scope === "tool") {
            recordStatisticsEvent({ event: "tool_open", name: target.name });
        } else {
            recordStatisticsEvent({ event: "dialog_open", name: statisticsDialogName(managerName) });
            if (target.scope === "game") {
                recordStatisticsEvent({ event: "game_open", game: target.name });
            }
        }
        return session;
    }

    _pauseStatisticsTarget(session, now = performance.now()) {
        if (!session || session.activeStartedAt === null) { return; }
        session.activeDuration += Math.max(0, now - session.activeStartedAt);
        session.activeStartedAt = null;
    }

    _finishStatisticsTarget(managerName, beacon = false, now = performance.now()) {
        const session = this.statisticsTargets.get(managerName);
        if (!session) { return; }
        this._pauseStatisticsTarget(session, now);
        this.statisticsTargets.delete(managerName);
        recordStatisticsEvent({
            event: "view_duration",
            scope: session.scope,
            name: session.name,
            result: session.scope === "game" ? session.view.getGameResult() : "",
            duration_ms: session.activeDuration,
        }, { beacon });
    }

    _syncStatisticsLifecycle() {
        if (this._statisticsFinished) { return; }
        const targets = new Map();
        this.dialogManager.dialogs.forEach((_dialog, managerName) => {
            const target = this._statisticsTarget(managerName);
            if (target) { targets.set(managerName, target); }
        });
        this.dialogManager.windows.forEach((_windowEl, managerName) => {
            const target = this._statisticsTarget(managerName);
            if (target) { targets.set(managerName, target); }
        });

        const now = performance.now();
        const activeName = document.visibilityState === "visible"
            ? this.dialogManager.activeTarget
            : "";
        this.statisticsTargets.forEach((session, managerName) => {
            if (managerName !== activeName || !targets.has(managerName) || session.isRunning?.() === false) {
                this._pauseStatisticsTarget(session, now);
            }
            if (!targets.has(managerName)) {
                this._finishStatisticsTarget(managerName, false, now);
            }
        });
        targets.forEach((target, managerName) => {
            if (!this.statisticsTargets.has(managerName)) {
                this._startStatisticsTarget(managerName, target);
            }
        });
        const active = this.statisticsTargets.get(activeName);
        if (active && active.activeStartedAt === null && active.isRunning?.() !== false) {
            active.activeStartedAt = now;
        }
    }

    _finishStatisticsTargets() {
        if (this._statisticsFinished) { return; }
        this._statisticsFinished = true;
        this.midiDialog?.finishPlaybackStats(true);
        const now = performance.now();
        Array.from(this.statisticsTargets.keys()).forEach((managerName) => {
            this._finishStatisticsTarget(managerName, true, now);
        });
    }

    start() {
        // Theme
        initializeTVTheme();
        bindClientErrorStatistics();

        const desktopRoot = document.querySelector("[data-tv-bundle-desktop]");
        if (!desktopRoot) { return; }
        this.desktopView = new TVDesktop(new TVRect()).bindRoot(desktopRoot);
        this.desktop = this.desktopView.root;

        this.dialogManager = this.desktopView.dialogManager;
        this._bindLocalLinks();
        this.dialogManager.onChange = () => {
            this.dosWindow?.setActive(this.dialogManager.activeTarget === "dos:prompt");
            this._syncStatisticsLifecycle();
            const activeBundle = this.windowManager
                ? this.windowManager.syncActiveTarget(this.dialogManager.activeTarget)
                : null;
            if (activeBundle) {
                this._updateSearchData(activeBundle);
            } else if (this.searchDialog && !this.windowManager?.openWindows.size) {
                this.searchDialog.searchData = { topics: [] };
            }
            this._syncBundleMenu();
            this._updateWindowMenuState();
            this._updateStatusLine();
            this._scheduleUrlStateSync();
        };
        this._updateStatusLine();

        this.windowManager = new BundleWindowManager(this.desktop, () => {
            this._updateStatusLine();
            this._syncBundleMenu();
            this._scheduleUrlStateSync();
        });
        this.windowManager.dialogManager = this.dialogManager;
        this._bindUrlStateSync();

        // Register standard dialogs
        this._registerDialog("about", () => new TVAboutDialog());
        const loginDialog = this._registerDialog("login", () => new TVLoginDialog());
        const registrationDialog = this._registerDialog("registration", () => new TVRegistrationDialog());
        this._registerDialog("registration-token", () => new TVRegistrationTokenDialog());
        this.serverConfigDialog = this._registerDialog("server-configuration", () => new TVServerConfigurationDialog());
        this.serverConfigDialog.onBeforeRebuild = async (resource) => {
            if (resource === "dos" && this.dosWindow) {
                await this._closeDosPrompt();
                if (this.dosWindow) { throw new Error("Cannot rebuild until the current DOS overlay is saved and closed."); }
            } else if (resource === "midi") {
                this.midiDialog?.stopPlayback();
                if (this.midiDialog) { this.midiDialog.pendingPlay = null; }
            }
        };
        this.serverConfigDialog.onRebuildStarted = (resource) => {
            if (resource === "midi") { void this.midiDialog?.refreshCatalog(); }
        };
        loginDialog.onRegister = () => this.dialogManager.open("registration");
        loginDialog.onSessionChange = (session) => this._setAuthSession(session);
        registrationDialog.onSessionChange = (session) => loginDialog.updateSession(session);
        registrationDialog.onConfirmed = () => loginDialog.close();
        this._registerDialog("puzzle", () => new TVPuzzleDialog());
        this._registerDialog("calendar", () => new TVCalendarDialog());
        this._registerDialog("ascii", () => new TVAsciiTableDialog());
        this._registerDialog("calc", () => new TVCalculatorDialog());
        this.midiDialog = this._registerDialog("midi", () => new TVMidiPlayerDialog());
        if (this.midiDialog) { this.midiDialog.onPlaybackEvent = recordStatisticsEvent; }
        this._registerDialog("colors", () => new TVColorsDialog());
        this._registerDialog("widgets", () => new TVViewGalleryDialog());
        this._registerDialog("grid", () => new TVGridDemoDialog());
        this._registerDialog("terminal", () => new TVServerTerminalDialog());
        this._registerDialog("statistics", () => new TVStatisticsDialog());
        this._registerDialog("systeminfo", () => new TVSystemInformationDialog());
        this.fileOpenDialog = this._registerDialog("fileopen", () => new TVFileOpenDialog());
        this.changeDirectoryDialog = this._registerDialog("chdir", () => new TVChangeDirectoryDialog());
        this.findDialog = this._registerDialog("find", () => new TVFindDialog());
        this._registerDialog("tetris", () => new TVTetrisDialog());
        this._registerDialog("mines", () => new TVMinesDialog());
        this._registerDialog("breakout", () => new TVBreakOutDialog());
        this._registerDialog("sokoban", () => new TVSokobanDialog());
        this._registerDialog("lines", () => new TVLinesDialog());
        this._registerDialog("reversi", () => new TVReversiDialog());
        this._registerDialog("ludo", () => new TVLudoDialog());
        this._registerDialog("mastermind", () => new TVMastermindDialog());
        this._registerDialog("snake", () => new TVSnakeDialog());
        this._registerDialog("hanoi", () => new TVHanoiDialog());
        this._registerDialog("tron", () => new TVTronDialog());
        this._registerBundleSearch();
        this.helpController = new TVHelpController({
            getMenuController: () => this.menuController,
            getDialogManager: () => this.dialogManager,
            onHelp: (helpCtx) => {
                void this._openContextHelpTopic(helpCtx);
            },
        });
        this.dialogManager.applyActiveStates();
        recordVisitStatistics();
        bindVisitLifecycleStatistics();
        document.addEventListener("visibilitychange", () => this._syncStatisticsLifecycle());
        window.addEventListener("pagehide", () => this._finishStatisticsTargets());
        window.addEventListener("pageshow", (event) => {
            if (event.persisted) {
                this._statisticsFinished = false;
                this._syncStatisticsLifecycle();
            }
        });
        const startupParams = new URLSearchParams(window.location.search);
        if (startupParams.get("server_error")) {
            const path = startupParams.get("server_path") || window.location.pathname;
            void this._showError("Server Error", `The requested address was not found:\n${path}`);
        }

        // Show a usable File/Open command immediately, then replace the menus
        // with their complete catalog-backed contents when loading finishes.
        this.menuState = buildBundleMenuBar([], null, this.authSession);
        fillBorders();
        this._bindMenus();
        void this._refreshAuthSession();
        this._catalogReady = this._loadCatalog();

        // Layout
        this.desktopView.startLayout();

    }

    _updateStatusLine() {
        const hasHelpWindow = this.windowManager && this.windowManager.openWindows.size > 0;
        const currentBundle = this.windowManager ? this.windowManager.currentBundle : null;
        const statusHint = String(this._activeStatusHint() || "THelpViewer");
        const statusLine = document.querySelector("[data-tv-status-line]");
        if (!statusLine) { return; }
        const items = [];
        if (hasHelpWindow) {
            items.push(NewStatusKey(renderHotkeyMarkup("~B~ack"), 0, "bundle-back"));
            if (currentBundle && bundleCanShowIndex(currentBundle)) {
                items.push(NewStatusKey(renderHotkeyMarkup("~I~ndex"), 0, "bundle-index"));
            }
            if (currentBundle && bundleCanShowHelpContentsTopic(currentBundle)) {
                items.push(NewStatusKey(
                    renderHotkeyMarkup("~H~elp Contents"),
                    0,
                    "bundle-help-contents",
                ));
            }
            if (currentBundle && bundleCanShowContents(currentBundle)) {
                items.push(NewStatusKey(
                    renderHotkeyMarkup("C~o~ntent"),
                    0,
                    "bundle-contents",
                ));
            }
            items.push(NewStatusKey(
                renderHotkeyMarkup("~F3~ Search"),
                kbF3,
                "dialog-open",
                "search",
            ));
            items.push(NewStatusKey(
                renderHotkeyMarkup("~Alt-F3~ Close"),
                kbAltF3,
                "bundle-close-all",
            ));
        }
        items.push(NewStatusKey(renderHotkeyMarkup("~F1~ Help"), kbF1, "context-help"));
        items.push(`<span class="tv-status-separator" aria-hidden="true">│</span>`);
        items.push(`<span class="tv-status-hint" data-tv-status-hint>${escapeHtml(statusHint)}</span>`);
        items.push(`<a class="tv-status-link" href="https://github.com/mariolacko/THelpViewer" target="_blank" rel="noopener">GitHub</a>`);
        const statusView = new TVStatusLine(
            new TVRect(),
            NewStatusDef(0, 0xffff, items),
        );
        statusLine.innerHTML = statusView.draw();
        statusView.bindRoot(statusLine);
        this._bindStatusButtons();
    }

    _activeStatusHint() {
        if (!this.dialogManager) { return ""; }
        const helpCtx = this.dialogManager.getHelpCtx();
        const helpTopic = TV_CONTEXT_HELP_TOPICS?.[helpCtx];
        if (helpTopic?.text) {
            const firstSentence = String(helpTopic.text).match(/^.*?[.!?](?:\s|$)/)?.[0];
            return (firstSentence || helpTopic.text).trim();
        }
        const target = String(this.dialogManager.activeTarget || "");
        const dialog = this.dialogManager.get(target);
        if (dialog?.isOpen()) {
            return "Tab selects a control; Enter activates it; Esc closes the dialog.";
        }
        const windowEl = this.dialogManager.windows.get(target);
        if (!windowEl?.isConnected) { return ""; }
        if (target.startsWith("help:")) {
            const helpWindow = windowEl._tvWindowView;
            const bundle = helpWindow.bundle;
            const view = helpWindow.currentView;
            if (view === "topic" && bundle) {
                const topic = findTopicByHex(bundle, helpWindow.currentTopic || "");
                if (topic) { return bundleTopicTitle(bundle, topic); }
            }
            if (view === "tag") {
                const label = helpWindow.currentTag?.label || helpWindow.currentTag?.key || "Tag";
                const value = helpWindow.currentTag?.value || "";
                return value ? `${label}: ${value}` : label;
            }
            return view === "contents" ? "Contents" : "Index";
        }
        return windowEl.querySelector(".tv-window-caption")?.textContent?.trim() || "";
    }

    _updateWindowMenuState() {
        if (!this.dialogManager) { return; }
        const windowCount = this.dialogManager.openWindowCount();
        const targetCount = this.dialogManager.openTargets().length;
        const activeTarget = this.dialogManager.activeTarget || "";
        const activeWindow = this.dialogManager.windows?.get?.(activeTarget) || null;
        const canFind = Boolean(
            activeWindow?.isConnected
            && (activeTarget.startsWith("help:") || activeTarget.startsWith("doc:"))
        );
        const activeEditor = activeWindow?._tvWindowView?.editor
            || activeWindow?._tvWindowView?.findEditor || null;
        const canFindAgain = canFind && Boolean(activeEditor?.lastQuery);
        const states = {
            tile: windowCount > 0,
            cascade: windowCount > 0,
            list: targetCount > 0,
            zoom: this.dialogManager.canDispatchCommand(TV_COMMANDS.ZOOM),
            next: this.dialogManager.canDispatchCommand(TV_COMMANDS.NEXT),
            previous: this.dialogManager.canDispatchCommand(TV_COMMANDS.PREVIOUS),
            close: this.dialogManager.canDispatchCommand(TV_COMMANDS.CLOSE),
        };
        const menuState = this.menuState;
        const updateMenuItem = (item, disabled) => {
            item?.setDisabled(disabled);
            menuState?.view?.updateItem(item);
        };
        menuState?.windowItems?.forEach((item, command) => {
            updateMenuItem(item, !states[command]);
        });
        updateMenuItem(menuState?.findItem, false);
        updateMenuItem(menuState?.findAgainItem, !canFindAgain);
    }

    _bindStatusButtons() {
        if (this.menuController) { this.menuController.commandTarget = this; }
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
        if (!url.searchParams.has("file") && !url.searchParams.has("doc")) { url.search = ""; }
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
                const helpWindow = element._tvWindowView;
                const file = helpWindow?.sourceFile || "";
                if (!file) { continue; }
                const viewport = element.querySelector("[data-tv-viewport]");
                const item = {
                    t: "h",
                    f: file,
                    view: helpWindow.currentView,
                    g: captureWindowGeometry(element),
                };
                const topic = helpWindow.currentTopic || "";
                if (topic) { item.topic = topic; }
                const visibleLine = viewport
                    ? Array.from(element.querySelectorAll(".tv-topic-line[data-tv-line]"))
                        .find((line) => line.offsetTop + line.offsetHeight >= viewport.scrollTop)
                    : null;
                const line = Number(visibleLine ? visibleLine.dataset.tvLine : helpWindow.currentLine);
                if (Number.isInteger(line) && line > 0) { item.line = line; }
                if (viewport) { item.s = [Math.round(viewport.scrollLeft), Math.round(viewport.scrollTop)]; }
                if (helpWindow.currentTag?.key && helpWindow.currentTag?.value) {
                    item.tag = [
                        helpWindow.currentTag.key,
                        helpWindow.currentTag.value,
                        helpWindow.currentTag.label || helpWindow.currentTag.key,
                    ];
                }
                const selection = captureTextSelection(viewport);
                if (selection) { item.sel = selection; }
                addWindow("help:" + key, item);
            }
        }

        this.docWindows.forEach((element, file) => {
            if (!element.isConnected) { return; }
            const viewport = element.querySelector("[data-tv-viewport]");
            const item = {
                t: "doc",
                f: file,
                g: captureWindowGeometry(element),
            };
            if (viewport) { item.s = [Math.round(viewport.scrollLeft), Math.round(viewport.scrollTop)]; }
            const selection = captureTextSelection(viewport);
            if (selection) { item.sel = selection; }
            addWindow("doc:" + file, item);
        });

        if (this.dosWindow?.root?.isConnected) {
            addWindow("dos:prompt", {
                t: "dos", g: captureWindowGeometry(this.dosWindow.root),
                p: this.dosWindow.paused,
            });
        }

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
                    if (!entry && item.f !== CONTEXT_HELP_BUNDLE_FILE) { continue; }
                    const bundle = await loadBundle(entry ? entry.file : CONTEXT_HELP_BUNDLE_FILE);
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
                    targets.push("doc:" + entry.file);
                    restored = true;
                } else if (item.t === "dos") {
                    const view = await this._openDosPrompt();
                    if (!view) { continue; }
                    this._applyUrlWindowState(view.root, item, false);
                    view.paused = item.p === true;
                    view.syncPause(); view.onChange?.();
                    targets.push("dos:prompt");
                    restored = true;
                } else if (item.t === "dlg" && item.name) {
                    const dialog = this.dialogManager.open(item.name);
                    if (!dialog) { continue; }
                    applyWindowGeometry(dialog.dialog, item.g, true);
                    if (typeof dialog.restoreUrlState === "function") {
                        dialog.restoreUrlState(item.state);
                    }
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
        this.dialogManager.onChange?.();
        const bundle = this.windowManager.syncActiveTarget(this.dialogManager.activeTarget);
        if (bundle) { this._updateSearchData(bundle); }
        this._updateStatusLine();
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

    _bindLocalLinks() {
        if (!this.desktop || this.localLinkHandler) { return; }
        this.localLinkHandler = (event) => {
            if (event.defaultPrevented || event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
                return;
            }
            const link = event.target?.closest?.("a[href]");
            if (!link || !this.desktop.contains(link)) { return; }
            const href = String(link.getAttribute("href") || "").trim();
            if (!href || href.startsWith("#") || link.hasAttribute("download")) { return; }
            let url;
            try {
                url = new URL(href, window.location.href);
            } catch {
                return;
            }
            if (url.origin !== window.location.origin || !["http:", "https:"].includes(url.protocol)) {
                if (["http:", "https:"].includes(url.protocol)) {
                    recordStatisticsEvent({ event: "link", result: "external" });
                }
                return;
            }
            event.preventDefault();
            void this._openLocalLink(url, link.target === "_blank");
        };
        this.desktop.addEventListener("click", this.localLinkHandler);
    }

    async _openLocalLink(url, newWindow = false) {
        try {
            const response = await fetch(url.href, {
                cache: "no-store",
                headers: { Accept: "application/json" },
            });
            const redirectedUrl = new URL(response.url || url.href, window.location.href);
            if (!response.ok || redirectedUrl.searchParams.has("server_error")) {
                const status = response.status || Number(redirectedUrl.searchParams.get("server_error")) || 404;
                throw Object.assign(new Error(`HTTP ${status}`), { status });
            }
            await response.body?.cancel();
            recordStatisticsEvent({ event: "link", result: "internal" });
            if (newWindow) {
                const opened = window.open(url.href, "_blank", "noopener");
                if (opened) { return; }
            }
            window.location.assign(url.href);
        } catch (error) {
            recordStatisticsEvent({ event: "link", result: "broken" });
            const status = Number(error?.status) || 0;
            const message = status === 404
                ? `The requested address was not found:\n${url.pathname}`
                : `Cannot open ${url.pathname}.\n${error?.message || error}`;
            void this._showError(status === 404 ? "Server Error" : "Navigation Error", message);
        }
    }

    _showError(title, error) {
        recordStatisticsEvent({ event: "client_error", error: statisticsErrorCategory(title, error) });
        if (!this.errorMessageBox) {
            this.errorMessageBox = new TVMessageBox();
            this.dialogManager.register("server-error", this.errorMessageBox);
        }
        const message = String(error?.message || error || "Unknown error");
        return this.errorMessageBox.show({
            type: TVMessageBox.MF_ERROR,
            title,
            lines: message.split("\n"),
            buttons: TVMessageBox.MF_OK_BUTTON,
        });
    }

    async _loadContextHelp() {
        const bundle = await loadBundle(CONTEXT_HELP_BUNDLE_FILE);
        this._updateSearchData(bundle);
        return bundle;
    }

    async _openContextHelpTopic(helpCtx) {
        try {
            const bundle = await this._loadContextHelp();
            if (!this.windowManager.showTopic(bundle, helpCtx)) {
                this.windowManager.showDefault(bundle);
            }
        } catch (error) {
            console.error("Failed to load THelpViewer Help", error);
            void this._showError("Help Error", error);
        }
    }

    async _openContextHelpIndex() {
        try {
            const bundle = await this._loadContextHelp();
            this.windowManager.showIndex(bundle);
        } catch (error) {
            console.error("Failed to load THelpViewer Help index", error);
            void this._showError("Help Error", error);
        }
    }

    _registerBundleSearch() {
        const searchDialog = this._registerDialog("search", () => new TVSearchDialog());
        if (!searchDialog) { return; }
        this.searchDialog = searchDialog;
        // Provide empty search data initially
        searchDialog.searchData = { topics: [] };
        // Override openSelected to navigate within bundle viewer
        const self = this;
        searchDialog.openSelected = async function () {
            if (this.selectedIndex < 0 || this.selectedIndex >= this.matches.length) {
                if (this.input.getData().trim()) {
                    recordStatisticsEvent({ event: "search", scope: "topic", result: "no-results" });
                }
                return;
            }
            const match = this.matches[this.selectedIndex];
            recordStatisticsEvent({ event: "search", scope: "topic", result: "found" });
            this.close();
            try {
                if (match.kind === "doc") {
                    await self._openDocFile(match.file);
                    return;
                }
                const bundle = match.file
                    ? await loadBundle(match.file)
                    : self.windowManager?.currentBundle;
                if (bundle) {
                    self._updateSearchData(bundle);
                    self.windowManager.showTopic(bundle, match.context_hex);
                }
            } catch (error) {
                void self._showError("Search Error", `Cannot open ${match.file}.\n${error?.message || error}`);
            }
        };
        void searchDialog.monitorIndex();
    }

    _updateSearchData(bundle) {
        if (this.searchDialog && bundle) {
            const sourceFile = bundle.metadata?.source?.filename
                || bundle.metadata?.catalog_source_files?.[0]
                || bundle._catalogFile || "";
            const helpName = bundle.metadata?.name || sourceFile;
            this.searchDialog.searchData = {
                topics: buildUhfSearchIndex(bundle).map((entry) => ({
                    ...entry, source_file: sourceFile, help_name: helpName,
                })),
            };
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
        this.docWindows.forEach((el, file) => {
            if (!el.isConnected) { return; }
            const caption = el.querySelector(".tv-window-caption");
            items.push({
                label: caption ? caption.textContent : "Document",
                type: "doc",
                managerName: "doc:" + file,
                element: el,
            });
        });
        if (this.dosWindow?.root?.isConnected) {
            items.push({ label: this.dosWindow.getTitle(), type: "window",
                key: "dos:prompt", managerName: "dos:prompt", element: this.dosWindow.root });
        }
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

        const dialog = new TVWindowListDialog();
        const itemsView = dialog.list;
        let selectedIdx = 0;

        const refresh = () => {
            items = this._collectWindowListItems();
            if (selectedIdx >= items.length) { selectedIdx = Math.max(0, items.length - 1); }
            itemsView.setItems(items, items.length ? selectedIdx : -1);
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
        itemsView.bind({
            onSelect: (_item, index) => { selectedIdx = index; },
            onActivate: (_item, index) => activate(index),
        });

        refresh();
        dialog.open();
        window.requestAnimationFrame(() => itemsView.selectedElement()?.focus());
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
        this.menuState = buildBundleMenuBar(catalogData, null, this.authSession, this.dosWindow);
        fillBorders();
        this._bindMenus();
        this._showWelcome();
        await this._handleUrlState();
        if (!window.location.search && catalogData.length) {
            document.getElementById("tv-public-fallback")?.remove();
        }
    }

    _syncBundleMenu() {
        if (!Array.isArray(catalogData)) { return; }
        const currentBundle = this.windowManager ? this.windowManager.currentBundle : null;
        const hasContentsMenu = !!(currentBundle && Array.isArray(currentBundle.contents) && currentBundle.contents.length);
        const nextKey = (hasContentsMenu ? bundleWindowKey(currentBundle) : "") + (this.dosWindow?.active ? ":dos" : "");
        if (nextKey === this._menuBundleKey) {
            return;
        }
        this._menuBundleKey = nextKey;
        this.menuState = buildBundleMenuBar(catalogData, hasContentsMenu ? currentBundle : null, this.authSession, this.dosWindow);
        fillBorders();
        this._bindMenus();
    }

    async _refreshAuthSession() {
        try {
            const response = await fetch("/api/auth/session", { cache: "no-store" });
            if (response.ok) { this._setAuthSession(await response.json()); }
        } catch { /* Local generated pages may have no account API. */ }
    }

    _setAuthSession(session) {
        if (this.dosWindow?.session && this.dosWindow.session.account !== (session?.user?.username || "")) {
            void this._closeDosPrompt(false);
        }
        const nextAdmin = Boolean(session?.authenticated && session.user?.role === "admin");
        if (!nextAdmin) { this.serverConfigDialog?.close(); this.dialogManager?.get("registration-token")?.close(); }
        const nextSession = session?.authenticated && session.user ? session : null;
        if (JSON.stringify(nextSession) === JSON.stringify(this.authSession)) { return; }
        this.authSession = nextSession;
        this.isAdmin = nextAdmin;
        this._menuBundleKey = null;
        const currentBundle = this.windowManager?.currentBundle || null;
        this.menuState = buildBundleMenuBar(catalogData || [], currentBundle, this.authSession, this.dosWindow);
        fillBorders();
        this._bindMenus();
    }

    async _handleUrlState() {
        const hashState = decodeUrlState(window.location.hash);
        if (hashState) {
            await this._restoreUrlState(hashState);
            document.getElementById("tv-public-fallback")?.remove();
        }
        if (window.location.search) {
            const url = new URL(window.location.href);
            const publicDoc = url.searchParams.get("doc");
            const publicFile = publicDoc ? null : url.searchParams.get("file");
            const file = publicFile || url.searchParams.get("search_file");
            const topic = url.searchParams.get("topic") || url.searchParams.get("search_topic");
            const line = url.searchParams.get("line");
            const doc = publicDoc || url.searchParams.get("search_doc");
            const canOpenFile = publicFile || (catalogData || []).some((candidate) => candidate.file === file);
            if (!hashState && file && (topic || publicFile) && canOpenFile) {
                try {
                    const bundle = await loadBundle(file);
                    this.dialogManager.get("welcome")?.destroy();
                    this._updateSearchData(bundle);
                    if (topic) { this.windowManager.showTopic(bundle, topic, line); }
                    else { this.windowManager.showDefault(bundle); }
                    document.getElementById("tv-public-fallback")?.remove();
                } catch (error) {
                    void this._showError("Search Error", `Cannot open ${file}.\n${error?.message || error}`);
                }
            } else if (!hashState && doc && (docsCatalogData || []).some((item) => item.file === doc)) {
                this.dialogManager.get("welcome")?.destroy();
                await this._openDocFile(doc);
                document.getElementById("tv-public-fallback")?.remove();
            }
            if (!publicFile && !publicDoc) {
                url.search = "";
                window.history.replaceState(null, "", url.toString());
            }
        }
    }

    _handleMarkdownLink(filename, link) {
        let decodedHref;
        try {
            decodedHref = decodeURIComponent(link.getAttribute("href") || "");
        } catch {
            return false;
        }
        const hrefPath = decodedHref.split(/[?#]/, 1)[0];
        if (!hrefPath.toLowerCase().endsWith(".md")) { return false; }
        const baseDir = filename.includes("/") ? filename.replace(/[^/]+$/, "") : "";
        const repositoryRelative = hrefPath.replace(/^\/?docs\//i, "");
        const raw = repositoryRelative !== hrefPath ? repositoryRelative : baseDir + hrefPath;
        const normalized = [];
        for (const part of raw.split("/")) {
            if (part === "..") { normalized.pop(); }
            else if (part && part !== ".") { normalized.push(part); }
        }
        const resolved = normalized.join("/");
        void this._openMarkdownDocument(resolved);
        return true;
    }

    async _openMarkdownDocument(resolved) {
        try {
            const resp = await fetch(DOCS_DIR + encodeURI(resolved));
            if (!resp.ok) { throw new Error(`HTTP ${resp.status}`); }
            const md = await resp.text();
            this._openDocWindow(resolved, md);
            recordStatisticsEvent({ event: "link", result: "internal" });
        } catch (error) {
            recordStatisticsEvent({ event: "link", result: "broken" });
            console.error(`Failed to load doc ${resolved}:`, error);
            void this._showError("Document Error", `Cannot open ${resolved}.\n${error?.message || error}`);
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
        const w = { cols: 86, rows: 24, min_cols: 40, min_rows: 8 }; // 80 code columns + frame and both document/code padding
        const windowView = new TVWindow(new TVRect(0, 0, w.cols, w.rows), title, wnNoNumber);
        windowView.minSize = new TVPoint(w.min_cols, w.min_rows);
        windowView.setHelpCtx(hcDocumentViewer);
        const windowEl = TVView._fromHTML(windowView.draw(contentHTML));
        windowView.bindRoot(windowEl);
        windowEl._tvWindowView = windowView;
        windowEl.classList.add("tv-doc-window");
        this.docWindows.set(docKey, windowEl);
        this.desktop.appendChild(windowEl);
        bindCloseButtons(windowEl);

        // Init widgets
        const indicator = new TVIndicator();
        indicator.root = TVView._fromHTML(indicator.draw());
        const horizontalScrollbar = windowEl.querySelector(".tv-bottom-bar > .tv-scrollbar-x");
        horizontalScrollbar?.before(indicator.root);
        const editor = new TVEditor(new TVRect(), null, null, indicator);
        editor.onLink = (link) => this._handleMarkdownLink(filename, link);
        windowView.insert(editor);
        windowView.editor = editor.bindRoot(windowEl.querySelector("[data-tv-doc-editor]"));
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        windowView.scrollbars = Array.from(
            frames,
            (frame) => new TVScrollBar(new TVRect()).bindRoot(frame),
        );
        new TurboVisionWindowResizer(windowEl, managerName);

        const closeWindow = () => {
            if (this.dialogManager) { this.dialogManager.unregisterWindow(managerName); }
            this.docWindows.delete(docKey);
            destroyWindowWidgets(windowEl);
            windowEl.remove();
            fillBorders();
            fillDesktopPatterns();
        };
        const toggleWindowZoom = () => {
            windowView.zoom();
            fillDesktopPatterns();
        };
        windowView.closeAction = closeWindow;
        windowView.zoomAction = toggleWindowZoom;

        // Register with window manager for focus/z-index and shared commands.
        if (this.dialogManager) {
            this.dialogManager.registerWindow(managerName, windowEl, {
                [TV_COMMANDS.CLOSE]: closeWindow,
                [TV_COMMANDS.ZOOM]: toggleWindowZoom,
            });
        }

        fillBorders();
        fillDesktopPatterns();
        return windowEl;
    }

    async _openDosPrompt() {
        if (!TVDosWindow) { return; }
        if (this.dosWindow) { this.dialogManager.activateWindow("dos:prompt"); this.dosWindow.view.canvas?.focus(); return this.dosWindow; }
        this.dialogManager.get("welcome")?.destroy();
        const windowView = new TVDosWindow();
        this.dosWindow = windowView;
        this.desktopView.insert(windowView);
        const root = TVView._fromHTML(windowView.draw());
        this.desktop.appendChild(root); windowView.resolve(root);
        windowView.onError = (error) => { void this._showError("DOS Prompt", error.message || String(error)); };
        windowView.onClose = () => { void this._closeDosPrompt(); };
        windowView.onChange = () => {
            this._menuBundleKey = null; this._syncBundleMenu();
            this._syncStatisticsLifecycle(); this._scheduleUrlStateSync();
        };
        windowView.onMenu = () => {
            const view = this.menuState?.view;
            const item = view?.menu.entries().find((entry) => entry.name === "D~O~S Prompt");
            if (item) { view.openMenu(view.rootByItem.get(item)); }
        };
        root._tvWindowView = windowView;
        bindCloseButtons(root);
        windowView.resizer = new TurboVisionWindowResizer(root, "dos:prompt");
        this.dialogManager.registerWindow("dos:prompt", root, {
            [TV_COMMANDS.CLOSE]: () => this._closeDosPrompt(),
            [TV_COMMANDS.ZOOM]: () => windowView.zoom(),
        });
        fillBorders();
        await windowView.boot();
        return windowView;
    }

    async _closeDosPrompt(save = true) {
        const windowView = this.dosWindow;
        if (!windowView || windowView.closing) { return; }
        windowView.closing = true;
        try {
            await windowView.stop(save);
            windowView.view.destroy(); windowView.resizer?.destroy();
            this.desktopView.remove(windowView); windowView.root?.remove();
            this.dosWindow = null;
            this.dialogManager.unregisterWindow("dos:prompt");
            this._menuBundleKey = null; this._syncBundleMenu(); fillBorders();
        } catch (error) { windowView.onError?.(error); }
        finally { windowView.closing = false; }
    }

    async _openBundleFile(filename, label = "") {
        const cached = bundleCache.has(filename);
        let loadingDialog = null;
        if (!cached) {
            loadingDialog = new TVLoadingDialog();
            this.desktopView.insert(loadingDialog);
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
            void this._showError("HELP File Error", `Cannot open ${filename}.\n${error?.message || error}`);
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
            void this._showError("Document Error", `Cannot open ${docFile}.\n${error?.message || error}`);
        }
    }

    _activeFindTarget() {
        const managerName = this.dialogManager?.activeTarget || "";
        if (!managerName.startsWith("help:") && !managerName.startsWith("doc:")) {
            return null;
        }
        const windowEl = this.dialogManager.windows.get(managerName);
        if (!windowEl?.isConnected) { return null; }
        const windowView = windowEl._tvWindowView;
        if (!windowView) { return null; }
        let editor = windowView.editor || windowView.findEditor;
        if (!editor) {
            const viewport = windowEl.querySelector("[data-tv-viewport]");
            if (!viewport) { return null; }
            editor = new TVEditor(new TVRect()).setReadOnly(true).bindRoot(viewport);
            editor.owner = windowView;
            windowView.findEditor = editor;
        }
        const caption = windowEl.querySelector(".tv-window-caption")?.textContent?.trim();
        return { managerName, windowEl, editor, caption: caption || "active window" };
    }

    _openFind() {
        const target = this._activeFindTarget() || this.lastFindTarget;
        if (!this.findDialog) { return false; }
        const localTarget = target?.windowEl?.isConnected && target.editor ? target : null;
        if (localTarget) { this.lastFindTarget = localTarget; }
        this.findDialog.configure({
            targetLabel: localTarget?.caption || "active window",
            globalFind: (query) => {
                this.dialogManager.open("search");
                this.searchDialog.setGlobal(true);
                this.searchDialog.input.setData(query);
                this.searchDialog.renderResults(query);
            },
            find: localTarget ? (query) => {
                const found = localTarget.editor.find(query, { fromStart: true });
                recordStatisticsEvent({
                    event: "search",
                    scope: "find",
                    result: found ? "found" : "no-results",
                });
                return found;
            } : null,
            findAgain: localTarget ? () => {
                const found = localTarget.editor.findNext();
                recordStatisticsEvent({
                    event: "search",
                    scope: "find-again",
                    result: found ? "found" : "no-results",
                });
                return found;
            } : null,
        });
        this.dialogManager.open("find");
        return true;
    }

    _findAgain() {
        const target = this._activeFindTarget() || this.lastFindTarget;
        if (!target?.windowEl?.isConnected || !target.editor) { return false; }
        this.lastFindTarget = target;
        if (!target.editor.lastQuery) {
            recordStatisticsEvent({ event: "search", scope: "find-again", result: "unavailable" });
            return false;
        }
        this.dialogManager.activateWindow(target.managerName);
        const found = target.editor.findNext();
        recordStatisticsEvent({
            event: "search",
            scope: "find-again",
            result: found ? "found" : "no-results",
        });
        return found;
    }

    _showWelcome() {
        if (this.dosWindow) { return; }
        const {
            TVRect,
            TVStaticText,
            TVGroup,
            TVButton: TVBtn,
        } = TV;
        const okButton = new TVButton(new TVRect(10, 8, 20, 10), '~O~K', "welcome-ok", bfDefault);
        const welcomeBody = new TVGroup(new TVRect(0, 0, 30, 10)).insertAll([
                new TVStaticText(new TVRect(0, 1, 30, 2), "\x03THelpViewer"),
                new TVStaticText(new TVRect(0, 3, 30, 4), "\x03Select a help file from the"),
                new TVStaticText(new TVRect(0, 4, 30, 5), "\x03File menu to get started."),
                new TVStaticText(new TVRect(0, 6, 30, 7), `\x03${Array.isArray(catalogData) ? catalogData.length : 0} help file(s) available.`),
                okButton,
            ]);
        const dialog = new TVWelcomeDialog();
        dialog.insert(welcomeBody);
        dialog.bindCommonClose(() => {
            dialog.destroy();
        });
        dialog.bindDrag();
        dialog.accept = () => dialog.destroy();
        this.dialogManager.register("welcome", dialog);
        this.dialogManager.open("welcome");
    }

    _bindMenus() {
        if (!this.menuController) {
            this.menuController = new TVMenuController({ commandTarget: this });
        } else {
            this.menuController.commandTarget = this;
            this.menuController.refresh();
        }
        if (TVScreenSaver) { TVScreenSaver.installIdleStart(); }
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

Object.assign(TV, { TVLoadingDialog, TVBundleApp, BundleWindowManager });
})();
