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
    applyThemePreset,
    applyThemeAndSyncPalette,
    readStoredThemePreset,
    readStoredColorPalette,
    applyColorPalette,
    buildPaletteFromCurrentStyle,
    TVDialogManager,
    TVAboutDialog,
    TVPuzzleDialog,
    TVCalendarDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVColorsDialog,
    TVSearchDialog,
    TVTetrisDialog,
    TVMinesDialog,
    TVBreakOutDialog,
    TVSokobanDialog,
    TVLinesDialog,
    TVReversiDialog,
    TVSnakeDialog,
    TVScreenSaver,
    TVWidget,
    TVButton,
    TVMenuBox,
    measureCells,
    TurboVisionScrollbar,
    TurboVisionWindowResizer,
    bindCloseButtons,
    updateWindowFrameState,
    SCROLL_REPEAT_MS,
    TRACK_CHAR,
    DISABLED_TRACK_CHAR,
    THUMB_CHAR,
    highlightCodeExamples,
} = TV;

// ── Catalog & data cache ────────────────────────────────────────────

const HELPS_DIR = "helps/";
const CATALOG_FILE = HELPS_DIR + "catalog.json";
const DOCS_DIR = "docs/";
const DOCS_CATALOG_FILE = DOCS_DIR + "catalog.json";
const bundleCache = new Map();
let catalogData = null;
let docsCatalogData = null;

function loadBundle(filename, { onProgress, signal } = {}) {
    if (bundleCache.has(filename)) {
        return Promise.resolve(bundleCache.get(filename));
    }
    const fetchUrl = HELPS_DIR + filename;
    return fetch(fetchUrl, { signal }).then(async (response) => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} loading ${filename}`);
        }
        const contentLength = Number(response.headers.get("Content-Length")) || 0;

        let compressedBytes;
        if (!contentLength || !response.body) {
            compressedBytes = new Uint8Array(await response.arrayBuffer());
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
            compressedBytes = new Uint8Array(total);
            let offset = 0;
            for (const chunk of chunks) {
                compressedBytes.set(chunk, offset);
                offset += chunk.length;
            }
        }

        // Decompress gzip → JSON
        const stream = new Blob([compressedBytes]).stream().pipeThrough(new DecompressionStream("gzip"));
        const json = await new Response(stream).text();
        const bundle = JSON.parse(json);
        bundle._catalogFile = filename;
        bundleCache.set(filename, bundle);
        return bundle;
    });
}

// ── Window rendering ────────────────────────────────────────────────

// ── Loading progress dialog (DOS Navigator Copy style) ──────────────

const PROGRESS_BAR_WIDTH = 32;

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
        this.update(0, 1);
        this.dialog.open();
    }

    update(received, total) {
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

    cancel() {
        this.cancelled = true;
        this.abortController.abort();
        this.destroy();
    }

    close() {
        this.dialog.close();
    }

    destroy() {
        this.dialog.close();
        this.dialog.overlay.remove();
    }
}

// ── Window rendering ────────────────────────────────────────────────

function renderScrollbar(axis) {
    const glyphs = axis === "y" ? ["▲", "▼"] : ["◄", "►"];
    return [
        `<div class="tv-scrollbar tv-scrollbar-${axis}" data-axis="${axis}">`,
        `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-backward" data-role="backward" aria-label="Scroll ${axis} backward">${glyphs[0]}</button>`,
        `<div class="tv-scroll-track" data-role="track"><div class="tv-scroll-cells" data-role="cells"></div><div class="tv-scroll-thumb" data-role="thumb"></div></div>`,
        `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-forward" data-role="forward" aria-label="Scroll ${axis} forward">${glyphs[1]}</button>`,
        `</div>`,
    ].join("");
}

function buildWindowHTML(bundle, contentHTML, caption) {
    const w = bundle.window;
    const style = `--tv-window-cols:${w.cols}; --tv-window-rows:${w.rows}; --tv-window-min-cols:${w.min_cols}; --tv-window-min-rows:${w.min_rows};`;
    return [
        `<main class="tv-window" data-tv-window data-tv-bundle-window="${escapeHtml(bundle.source_name)}" style="${style}">`,
        `<div class="tv-shell">`,
        `<div class="tv-border-row tv-border-top" data-tv-move-handle>`,
        `<span class="tv-border-corner" aria-hidden="true">╔</span>`,
        `<a class="tv-close-control" data-tv-close-button data-tv-bundle-close href="#" aria-label="Close window">[<span class="tv-close-glyph" data-tv-close-glyph>■</span>]</a>`,
        `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
        `<div class="tv-window-caption">${escapeHtml(caption)}</div>`,
        `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
        `<a class="tv-zoom-control" data-tv-bundle-zoom href="#" aria-label="Zoom window">[<span class="tv-zoom-glyph" data-tv-zoom-glyph>↑</span>]</a>`,
        `<span class="tv-border-corner" aria-hidden="true">╗</span>`,
        `</div>`,
        `<div class="tv-client-row">`,
        `<span class="tv-border-side tv-border-side-left" data-tv-border-side="║" aria-hidden="true"></span>`,
        `<div class="tv-frame">`,
        `<div class="tv-scroll-shell" data-tv-scroll-frame>`,
        `<div class="tv-viewport" data-tv-viewport>`,
        contentHTML,
        `</div>`,
        `</div>`,
        `</div>`,
        renderScrollbar("y"),
        `<div class="tv-bottom-bar">`,
        `<span class="tv-scroll-corner tv-scroll-corner-left" aria-hidden="true">╚</span>`,
        renderScrollbar("x"),
        `<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>`,
        `</div>`,
        `</div>`,
        `</div>`,
        `</main>`,
    ].join("\n");
}

// ── Index page rendering ────────────────────────────────────────────

function renderBundleIndex(bundle) {
    const buckets = {};
    const other = [];
    for (const entry of bundle.index_entries) {
        const label = entry.label.trim();
        if (!label) { continue; }
        const first = label[0].toUpperCase();
        if (first >= "A" && first <= "Z") {
            (buckets[first] = buckets[first] || []).push(entry);
        } else {
            other.push(entry);
        }
    }
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
    const navItems = [];
    const sections = [];

    if (other.length) {
        sections.push(renderIndexSection("#", "#", other, bundle));
    }

    for (const letter of letters) {
        if (buckets[letter] && buckets[letter].length) {
            navItems.push(`<a class="tv-index-jump" href="#" data-letter="${letter}">${letter}</a>`);
            sections.push(renderIndexSection(letter, letter, buckets[letter], bundle));
        } else {
            navItems.push(`<span class="tv-index-jump is-empty">${letter}</span>`);
        }
    }

    return [
        `<div class="tv-document tv-index-document">`,
        `<div class="tv-index-heading">${escapeHtml(bundle.index_label)}</div>`,
        `<nav class="tv-index-nav">${navItems.join("")}</nav>`,
        ...sections,
        `</div>`,
    ].join("\n");
}

function renderIndexSection(anchor, label, entries, bundle) {
    const items = entries.map((entry) => {
        return `<div class="tv-index-entry"><a href="#" data-tv-bundle-topic="${entry.context_hex}">${escapeHtml(entry.label)}</a></div>`;
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

// ── Topic navigation ────────────────────────────────────────────────

function findTopicByHex(bundle, contextHex) {
    return bundle.topics.find((t) => t.context_hex === contextHex) || null;
}

function rewriteTopicLinks(contentHTML) {
    // Rewrite static <a href="XXXX.html"> links to use data-tv-bundle-topic
    return contentHTML.replace(
        /<a\s+href="([0-9A-Fa-f]{4})\.html">/g,
        (match, hex) => `<a href="#" data-tv-bundle-topic="${hex.toUpperCase()}">`
    );
}

// ── Window manager ──────────────────────────────────────────────────

class BundleWindowManager {
    constructor(desktop, onNavigate) {
        this.desktop = desktop;
        this.onNavigate = onNavigate || null;
        this.dialogManager = null;
        this.openWindows = new Map(); // source_name → DOM element
        this.scrollbars = [];
        this.resizers = [];
        this.history = []; // { bundle, contextHex | null }
        this.currentBundle = null;
        this.currentContextHex = null;
    }

    showIndex(bundle) {
        // If the bundle has no index entries, show the help_context topic
        // (or the first topic) instead of an empty index page.
        if (!bundle.index_entries.length) {
            const fallback = bundle.help_context
                || (bundle.topics.length ? bundle.topics[0].context_hex : null);
            if (fallback) {
                this.showTopic(bundle, fallback);
                return;
            }
        }
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = null;
        const contentHTML = renderBundleIndex(bundle);
        this._openWindow(bundle, contentHTML, bundle.header_label);
        if (this.onNavigate) { this.onNavigate("Index"); }
        this._updateUrl();
    }

    showTopic(bundle, contextHex) {
        const topic = findTopicByHex(bundle, contextHex);
        if (!topic) { return; }
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = contextHex;
        const contentHTML = rewriteTopicLinks(topic.html);
        this._openWindow(bundle, contentHTML, bundle.header_label);
        if (this.onNavigate) { this.onNavigate(topic.title); }
        this._updateUrl();
    }

    _updateUrl() {
        if (!this.currentBundle) { return; }
        const catalogFile = this.currentBundle._catalogFile;
        const entry = catalogFile
            ? catalogData.find((e) => e.file === catalogFile)
            : catalogData.find((e) => e.name === this.currentBundle.header_label);
        const params = new URLSearchParams();
        if (entry) { params.set("file", entry.file); }
        if (this.currentContextHex) { params.set("topic", this.currentContextHex); }
        const qs = params.toString();
        const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
        window.history.replaceState(null, "", url);
    }

    _pushHistory() {
        if (this.currentBundle) {
            this.history.push({ bundle: this.currentBundle, contextHex: this.currentContextHex });
        }
    }

    goBack() {
        const prev = this.history.pop();
        if (!prev) { return; }
        // Restore without pushing to history again
        this.currentBundle = prev.bundle;
        this.currentContextHex = prev.contextHex;
        if (prev.contextHex) {
            const topic = findTopicByHex(prev.bundle, prev.contextHex);
            if (topic) {
                const contentHTML = rewriteTopicLinks(topic.html);
                this._openWindow(prev.bundle, contentHTML, prev.bundle.header_label);
                if (this.onNavigate) { this.onNavigate(topic.title); }
            }
        } else {
            const contentHTML = renderBundleIndex(prev.bundle);
            this._openWindow(prev.bundle, contentHTML, prev.bundle.header_label);
            if (this.onNavigate) { this.onNavigate("Index"); }
        }
    }

    _openWindow(bundle, contentHTML, caption) {
        const key = bundle.source_name;
        const existing = this.openWindows.get(key);
        if (existing) {
            // Update content in existing window
            const viewport = existing.querySelector("[data-tv-viewport]");
            if (viewport) {
                viewport.innerHTML = contentHTML;
                viewport.scrollTop = 0;
                viewport.scrollLeft = 0;
            }
            const captionEl = existing.querySelector(".tv-window-caption");
            if (captionEl) {
                captionEl.textContent = caption;
            }
            this._bindTopicLinks(existing, bundle);
            highlightCodeExamples(existing);
            fillBorders();
            return;
        }

        // Close existing windows (without resetting navigation state).
        for (const [k, el] of this.openWindows) {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + k); }
            el.remove();
        }
        this.openWindows.clear();

        const windowHTML = buildWindowHTML(bundle, contentHTML, caption);
        const template = document.createElement("template");
        template.innerHTML = windowHTML.trim();
        const windowEl = template.content.firstElementChild;
        this.desktop.appendChild(windowEl);
        this.openWindows.set(key, windowEl);
        this._initWindowWidgets(windowEl);
        this._bindTopicLinks(windowEl, bundle);
        this._bindCloseButton(windowEl, key);
        this._bindZoomButton(windowEl);
        if (this.dialogManager) { this.dialogManager.registerWindow("help:" + key, windowEl); }
        highlightCodeExamples(windowEl);
        fillBorders();
        fillDesktopPatterns();
    }

    _initWindowWidgets(windowEl) {
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        for (const frame of frames) {
            this.scrollbars.push(new TurboVisionScrollbar(frame));
        }
        this.resizers.push(new TurboVisionWindowResizer(windowEl));
    }

    _bindTopicLinks(windowEl, bundle) {
        windowEl.querySelectorAll("[data-tv-bundle-topic]").forEach((link) => {
            if (link.dataset.tvBundleBound === "1") { return; }
            link.dataset.tvBundleBound = "1";
            link.addEventListener("click", (event) => {
                event.preventDefault();
                this.showTopic(bundle, link.dataset.tvBundleTopic);
            });
        });
        // Bind letter navigation links in index
        windowEl.querySelectorAll("a[data-letter]").forEach((link) => {
            if (link.dataset.tvBundleBound === "1") { return; }
            link.dataset.tvBundleBound = "1";
            link.addEventListener("click", (event) => {
                event.preventDefault();
                const letter = link.getAttribute("data-letter");
                const section = windowEl.querySelector(`#idx-${letter}`);
                if (section) {
                    section.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
    }

    _bindCloseButton(windowEl, key) {
        const closeBtn = windowEl.querySelector("[data-tv-bundle-close]");
        if (!closeBtn) { return; }
        closeBtn.addEventListener("click", (event) => {
            event.preventDefault();
            windowEl.remove();
            this.openWindows.delete(key);
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + key); }
            this.currentBundle = null;
            this.currentContextHex = null;
            this._clearUrl();
            fillBorders();
            fillDesktopPatterns();
            if (this.onNavigate) { this.onNavigate(""); }
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
            existing.remove();
            this.openWindows.delete(key);
            if (this.onNavigate) { this.onNavigate(""); }
        }
    }

    closeAll() {
        for (const [key, el] of this.openWindows) {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + key); }
            el.remove();
        }
        this.openWindows.clear();
        this.history = [];
        this.currentBundle = null;
        this.currentContextHex = null;
        this._clearUrl();
        if (this.onNavigate) { this.onNavigate(""); }
    }

    tile() {
        const wins = [...this.openWindows.values()];
        const docs = [...this.desktop.querySelectorAll(".tv-doc-window")];
        const dialogs = this._visibleDialogs();
        const all = [...wins, ...docs, ...dialogs];
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
        });
        fillBorders();
    }

    cascade() {
        const wins = [...this.openWindows.values()];
        const docs = [...this.desktop.querySelectorAll(".tv-doc-window")];
        const dialogs = this._visibleDialogs();
        const all = [...wins, ...docs, ...dialogs];
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
        });
        fillBorders();
    }

    _visibleDialogs() {
        const overlays = this.desktop.querySelectorAll(".tv-dialog-overlay:not([hidden])");
        const dialogs = [];
        for (const overlay of overlays) {
            const win = overlay.querySelector(".tv-dialog-window");
            if (win) { dialogs.push(win); }
        }
        return dialogs;
    }

    _clearUrl() {
        window.history.replaceState(null, "", window.location.pathname);
    }
}

// ── Catalog menu items ──────────────────────────────────────────────

function buildCatalogMenuItems(catalog) {
    if (!catalog.length) { return []; }

    // Group entries by their group name; preserve insertion order.
    const groups = new Map();   // group → [entry, …]
    const ungrouped = [];
    for (const entry of catalog) {
        const group = entry.group || "";
        if (!group) {
            ungrouped.push(entry);
        } else {
            if (!groups.has(group)) { groups.set(group, []); }
            groups.get(group).push(entry);
        }
    }

    const items = [];
    let needSep = false;

    // Ungrouped entries go directly into the top-level menu.
    for (const entry of ungrouped) {
        items.push(new TVButton({
            dialog: false,
            className: "tv-menu-popup-item",
            attrs: { type: "button", "data-tv-bundle-open": entry.file },
            labelMarkup: escapeHtml(entry.name),
        }));
        needSep = true;
    }

    // Each group becomes a submenu.
    for (const [group, entries] of groups) {
        if (needSep) {
            items.push('<div class="tv-menu-popup-separator" aria-hidden="true">'
                + '<span class="tv-border-corner">├</span>'
                + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                + '<span class="tv-border-corner">┤</span>'
                + '</div>');
        }
        const subItems = entries.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-bundle-open": entry.file },
                labelMarkup: escapeHtml(entry.name),
            })
        );
        const subPopup = new TVMenuBox({
            className: "tv-menu-popup tv-submenu-popup",
            attrs: { "data-tv-submenu-popup": true, hidden: true },
            items: subItems,
        }).renderMarkup();

        items.push(
            `<div class="tv-submenu-root" data-tv-submenu-root>`
            + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
            + `${escapeHtml(group)}<span class="tv-submenu-arrow">►</span>`
            + `</button>`
            + subPopup
            + `</div>`
        );
        needSep = false;
    }

    return items;
}

function buildDocsMenuItems(docs) {
    if (!docs.length) { return []; }

    const groups = new Map();
    const ungrouped = [];
    for (const entry of docs) {
        const group = entry.group || "";
        if (!group) {
            ungrouped.push(entry);
        } else {
            if (!groups.has(group)) { groups.set(group, []); }
            groups.get(group).push(entry);
        }
    }

    const items = [];
    let needSep = false;

    for (const entry of ungrouped) {
        items.push(new TVButton({
            dialog: false,
            className: "tv-menu-popup-item",
            attrs: { type: "button", "data-tv-doc-open": entry.file },
            labelMarkup: escapeHtml(entry.name),
        }));
        needSep = true;
    }

    for (const [group, entries] of groups) {
        if (needSep) {
            items.push('<div class="tv-menu-popup-separator" aria-hidden="true">'
                + '<span class="tv-border-corner">├</span>'
                + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                + '<span class="tv-border-corner">┤</span>'
                + '</div>');
        }
        const subItems = entries.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-doc-open": entry.file },
                labelMarkup: escapeHtml(entry.name),
            })
        );
        const subPopup = new TVMenuBox({
            className: "tv-menu-popup tv-submenu-popup",
            attrs: { "data-tv-submenu-popup": true, hidden: true },
            items: subItems,
        }).renderMarkup();

        items.push(
            `<div class="tv-submenu-root" data-tv-submenu-root>`
            + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
            + `${escapeHtml(group)}<span class="tv-submenu-arrow">►</span>`
            + `</button>`
            + subPopup
            + `</div>`
        );
        needSep = false;
    }

    return items;
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

    function inlineMarkup(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
            .replace(/\*([^*]+)\*/g, '<i>$1</i>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }

    function closeList() {
        if (inList) { html.push(`</${listTag}>`); inList = false; }
    }
    function closeTable() {
        if (inTable) { html.push("</tbody></table>"); inTable = false; }
    }

    function isTableRow(line) { return line.trim().startsWith("|") && line.trim().endsWith("|"); }
    function isSepRow(line) { return /^\|[-:\s|]+\|$/.test(line.trim()); }
    function parseRow(line, tag) {
        const cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
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

function buildBundleMenuBar(catalog) {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    if (!menuBar) { return; }

    // ≡ system menu
    const sysPopupItems = [
        { type: "dialog", dialog: "about", label: "~A~bout" },
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
    ];
    const sysPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: sysPopupItems.map((entry) => {
            if (entry.type === "separator") {
                return '<div class="tv-menu-popup-separator" aria-hidden="true">'
                    + '<span class="tv-border-corner">├</span>'
                    + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                    + '<span class="tv-border-corner">┤</span>'
                    + '</div>';
            }
            if (entry.type === "submenu") {
                const subItems = entry.items.map((sub) => new TVButton({
                    dialog: false,
                    className: "tv-menu-popup-item",
                    attrs: { type: "button", "data-tv-saver-start": sub.mode },
                    labelMarkup: renderHotkeyMarkup(sub.label),
                }));
                const subPopup = new TVMenuBox({
                    className: "tv-menu-popup tv-submenu-popup",
                    attrs: { "data-tv-submenu-popup": true, hidden: true },
                    items: subItems,
                }).renderMarkup();
                return `<div class="tv-submenu-root" data-tv-submenu-root>`
                    + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
                    + `${renderHotkeyMarkup(entry.label)}<span class="tv-submenu-arrow">►</span>`
                    + `</button>`
                    + subPopup
                    + `</div>`;
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
    }).renderMarkup();
    const sysToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~≡~"),
    }).renderMarkup();

    // File menu with catalog entries
    const filePopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: buildCatalogMenuItems(catalog),
    }).renderMarkup();
    const fileToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~H~elp Files"),
    }).renderMarkup();

    // Docs menu with documentation markdown files
    const docsItems = buildDocsMenuItems(docsCatalogData || []);
    const docsPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: docsItems,
    }).renderMarkup();
    const docsToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~D~ocs"),
    }).renderMarkup();

    // Windows menu (TV standard)
    const winPopupItems = [
        { cmd: "tile", label: "~T~ile", hotkey: "" },
        { cmd: "cascade", label: "C~a~scade", hotkey: "" },
        { cmd: "list", label: "Window ~L~ist", hotkey: "Alt-0" },
        { cmd: "zoom", label: "~Z~oom", hotkey: "F5" },
        { cmd: "close", label: "~C~lose", hotkey: "Alt-F3" },
    ];
    const winPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: winPopupItems.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-window-cmd": entry.cmd },
                labelMarkup: renderHotkeyMarkup(entry.label) +
                    `<span class="tv-menu-hotkey">${escapeHtml(entry.hotkey)}</span>`,
            })
        ),
    }).renderMarkup();
    const winToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~W~indows"),
    }).renderMarkup();

    // Games menu
    const gamesPopupItems = [
        { type: "dialog", dialog: "breakout", label: "~B~reakOut" },
        { type: "dialog", dialog: "lines", label: "~L~ines" },
        { type: "dialog", dialog: "mines", label: "~M~ines" },
        { type: "dialog", dialog: "puzzle", label: "~P~uzzle" },
        { type: "dialog", dialog: "reversi", label: "~R~eversi" },
        { type: "dialog", dialog: "snake", label: "S~n~ake" },
        { type: "dialog", dialog: "sokoban", label: "~S~okoban" },
        { type: "dialog", dialog: "tetris", label: "~T~etris" },
    ];
    const gamesPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: gamesPopupItems.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-dialog-open": entry.dialog },
                labelMarkup: renderHotkeyMarkup(entry.label),
            })
        ),
    }).renderMarkup();
    const gamesToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~G~ames"),
    }).renderMarkup();

    menuBar.innerHTML = [
        `<nav class="tv-menu-items">`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        sysToggle,
        sysPopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        fileToggle,
        filePopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        docsToggle,
        docsPopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        gamesToggle,
        gamesPopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        winToggle,
        winPopupHTML,
        `</div>`,
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
    }

    start() {
        // Theme
        document.documentElement.classList.add("tv-js");
        applyThemePreset(readStoredThemePreset(), false);
        const storedPalette = readStoredColorPalette();
        if (storedPalette) {
            applyColorPalette(storedPalette, false);
        } else {
            TV.setActiveColorPalette(buildPaletteFromCurrentStyle());
        }

        this.desktop = document.querySelector("[data-tv-bundle-desktop]");
        if (!this.desktop) { return; }

        this.dialogManager = new TVDialogManager(this.desktop);
        this.dialogManager.onChange = () => this._updateStatusLine("");
        this._updateStatusLine("");

        // Register standard dialogs
        this._registerDialog("about", () => new TVAboutDialog(this.desktop));
        this._registerDialog("puzzle", () => new TVPuzzleDialog(this.desktop));
        this._registerDialog("calendar", () => new TVCalendarDialog(this.desktop));
        this._registerDialog("ascii", () => new TVAsciiTableDialog(this.desktop));
        this._registerDialog("calc", () => new TVCalculatorDialog(this.desktop));
        this._registerDialog("colors", () => new TVColorsDialog(this.desktop));
        this._registerDialog("tetris", () => new TVTetrisDialog(this.desktop));
        this._registerDialog("mines", () => new TVMinesDialog(this.desktop));
        this._registerDialog("breakout", () => new TVBreakOutDialog(this.desktop));
        this._registerDialog("sokoban", () => new TVSokobanDialog(this.desktop));
        this._registerDialog("lines", () => new TVLinesDialog(this.desktop));
        this._registerDialog("reversi", () => new TVReversiDialog(this.desktop));
        this._registerDialog("snake", () => new TVSnakeDialog(this.desktop));
        this._registerBundleSearch();
        this.dialogManager.applyActiveStates();

        // Fetch catalog dynamically and build menu
        this._loadCatalog();

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
        });
        this.windowManager.dialogManager = this.dialogManager;
    }

    _updateStatusLine(hint) {
        const hasHelpWindow = this.windowManager && this.windowManager.openWindows.size > 0;
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
        items.push(`<span class="tv-status-hint" data-tv-status-hint>${escapeHtml(hint || "THelpViewer")}</span>`);
        items.push(`<a class="tv-status-link" href="https://github.com/mariolacko/THelpViewer" target="_blank" rel="noopener">GitHub</a>`);
        statusLine.innerHTML = items.join("");
        this._bindStatusButtons();
    }

    _bindStatusButtons() {
        const statusLine = document.querySelector("[data-tv-status-line]");
        if (!statusLine) { return; }
        const closeAllBtn = statusLine.querySelector("[data-tv-bundle-close-all]");
        if (closeAllBtn) {
            closeAllBtn.addEventListener("click", (event) => {
                event.preventDefault();
                this.windowManager.closeAll();
                fillBorders();
                fillDesktopPatterns();
            });
        }
        const backBtn = statusLine.querySelector("[data-tv-bundle-back]");
        if (backBtn) {
            backBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager) { this.windowManager.goBack(); }
            });
        }
        statusLine.querySelectorAll("[data-tv-dialog-open]").forEach((el) => {
            el.addEventListener("click", (event) => {
                event.preventDefault();
                this.dialogManager.open(el.getAttribute("data-tv-dialog-open") || "");
            });
        });
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
        if (this.searchDialog && bundle && bundle.search_index) {
            this.searchDialog.searchData = { topics: bundle.search_index };
        }
    }

    _collectWindowListItems() {
        const items = [];
        if (this.windowManager) {
            for (const [key, el] of this.windowManager.openWindows) {
                const caption = el.querySelector(".tv-window-caption");
                items.push({ label: caption ? caption.textContent : key, type: "window", key, element: el });
            }
        }
        this.desktop.querySelectorAll(".tv-doc-window").forEach((el) => {
            const caption = el.querySelector(".tv-window-caption");
            items.push({ label: caption ? caption.textContent : "Document", type: "doc", element: el });
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
            dialog.close();
            dialog.overlay.remove();
            if (this.dialogManager) {
                this.dialogManager.dialogs.delete("windowlist");
            }
            document.removeEventListener("keydown", onKey);
        };

        dialog.bindCommonClose(cleanup);
        dialog.bindDrag();

        const activate = (idx) => {
            const item = items[idx];
            if (!item) { return; }
            if (item.type === "dialog" && this.dialogManager) {
                this.dialogManager.bringToFront(item.key);
            } else if ((item.type === "window" || item.type === "doc") && item.element) {
                this.desktop.appendChild(item.element);
                updateWindowFrameState(item.element, true);
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
        document.addEventListener("keydown", onKey);

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
            fetch(CATALOG_FILE),
            fetch(DOCS_CATALOG_FILE),
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
        buildBundleMenuBar(catalogData);
        fillBorders();
        this._bindMenus();
        this._showWelcome();
        this._handleUrlParams();
    }

    /** Read ?file=, ?topic=, ?search=, ?docs= from the URL and act on them. */
    async _handleUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const fileParam = params.get("file");
        const docsParam = params.get("docs");

        // Handle ?docs= independently of ?file=
        if (docsParam && docsCatalogData) {
            const docEntry = docsCatalogData.find(
                (e) => e.file === docsParam || e.name === docsParam
            );
            if (docEntry) {
                this.dialogManager.close("welcome");
                try {
                    const resp = await fetch(DOCS_DIR + docEntry.file);
                    if (resp.ok) {
                        const md = await resp.text();
                        this._openDocWindow(docEntry.file, md);
                    }
                } catch (err) {
                    console.error(`Failed to load doc from URL: ${docEntry.file}`, err);
                }
                if (!fileParam) { return; }
            }
        }

        if (!fileParam || !catalogData) { return; }

        // Find matching catalog entry (by file path or by name).
        const entry = catalogData.find(
            (e) => e.file === fileParam || e.name === fileParam
        );
        if (!entry) { return; }

        // Load bundle.
        const loadingDialog = new TVLoadingDialog(this.desktop);
        loadingDialog.show(entry.name);
        try {
            const bundle = await loadBundle(entry.file, {
                onProgress: (r, t) => loadingDialog.update(r, t),
                signal: loadingDialog.signal,
            });
            loadingDialog.destroy();
            this.dialogManager.close("welcome");
            this._updateSearchData(bundle);

            const topicParam = params.get("topic");
            const searchParam = params.get("search");

            if (topicParam) {
                const hex = topicParam.toUpperCase().padStart(4, "0");
                this.windowManager.showTopic(bundle, hex);
            } else {
                this.windowManager.showIndex(bundle);
            }

            if (searchParam && this.searchDialog) {
                this.searchDialog.searchData = { topics: bundle.search_index || [] };
                this.dialogManager.open("search");
                const input = this.searchDialog.query("input[type=text]");
                if (input) {
                    input.value = searchParam;
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                }
            }
        } catch (error) {
            loadingDialog.destroy();
            if (error.name !== "AbortError") {
                console.error(`Failed to load bundle from URL param: ${entry.file}`, error);
            }
        }
    }

    _openDocWindow(filename, markdownText) {
        const htmlContent = renderMarkdown(markdownText);
        const title = filename.replace(/\.md$/i, "").replace(/_/g, " ");
        const contentHTML = `<div class="tv-document tv-doc-document">${htmlContent}</div>`;
        const w = { cols: 78, rows: 24, min_cols: 40, min_rows: 8 };
        const style = `--tv-window-cols:${w.cols}; --tv-window-rows:${w.rows}; --tv-window-min-cols:${w.min_cols}; --tv-window-min-rows:${w.min_rows};`;
        const windowHTML = [
            `<main class="tv-window tv-doc-window" data-tv-window style="${style}">`,
            `<div class="tv-shell">`,
            `<div class="tv-border-row tv-border-top" data-tv-move-handle>`,
            `<span class="tv-border-corner" aria-hidden="true">╔</span>`,
            `<a class="tv-close-control" data-tv-close-button href="#" aria-label="Close window">[<span class="tv-close-glyph" data-tv-close-glyph>■</span>]</a>`,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<div class="tv-window-caption">${escapeHtml(title)}</div>`,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<a class="tv-zoom-control" href="#" aria-label="Zoom window">[<span class="tv-zoom-glyph" data-tv-zoom-glyph>↑</span>]</a>`,
            `<span class="tv-border-corner" aria-hidden="true">╗</span>`,
            `</div>`,
            `<div class="tv-client-row">`,
            `<span class="tv-border-side tv-border-side-left" data-tv-border-side="║" aria-hidden="true"></span>`,
            `<div class="tv-frame">`,
            `<div class="tv-scroll-shell" data-tv-scroll-frame>`,
            `<div class="tv-viewport" data-tv-viewport>`,
            contentHTML,
            `</div>`,
            `</div>`,
            `</div>`,
            renderScrollbar("y"),
            `<div class="tv-bottom-bar">`,
            `<span class="tv-scroll-corner tv-scroll-corner-left" aria-hidden="true">╚</span>`,
            renderScrollbar("x"),
            `<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>`,
            `</div>`,
            `</div>`,
            `</div>`,
            `</main>`,
        ].join("\n");

        // Close previous doc windows
        this.desktop.querySelectorAll(".tv-doc-window").forEach((el) => {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("docs"); }
            el.remove();
        });

        const template = document.createElement("template");
        template.innerHTML = windowHTML.trim();
        const windowEl = template.content.firstElementChild;
        this.desktop.appendChild(windowEl);

        // Register with window manager for focus/z-index management
        if (this.dialogManager) {
            this.dialogManager.registerWindow("docs", windowEl);
        }

        // Update URL with ?docs= parameter
        const docsUrl = new URL(window.location);
        docsUrl.searchParams.set("docs", filename);
        window.history.replaceState(null, "", docsUrl);

        // Init widgets
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        for (const frame of frames) {
            new TurboVisionScrollbar(frame);
        }
        new TurboVisionWindowResizer(windowEl);

        // Close button
        const closeBtn = windowEl.querySelector("[data-tv-close-button]");
        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.preventDefault();
                if (this.dialogManager) { this.dialogManager.unregisterWindow("docs"); }
                windowEl.remove();
                // Remove ?docs= from URL
                const closeUrl = new URL(window.location);
                closeUrl.searchParams.delete("docs");
                window.history.replaceState(null, "", closeUrl);
                fillBorders();
                fillDesktopPatterns();
            });
        }
        // Zoom
        const zoomBtn = windowEl.querySelector(".tv-zoom-control");
        if (zoomBtn) {
            zoomBtn.addEventListener("click", (e) => {
                e.preventDefault();
                const isMax = windowEl.classList.toggle("is-maximized");
                const glyph = windowEl.querySelector("[data-tv-zoom-glyph]");
                if (glyph) { glyph.textContent = isMax ? "↓" : "↑"; }
                fillBorders();
                fillDesktopPatterns();
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
        });
        dialog.bindCommonClose(() => {
            dialog.close();
            dialog.overlay.remove();
        });
        dialog.bindDrag();
        const ok = dialog.query("[data-tv-welcome-ok]");
        if (ok) {
            ok.addEventListener("click", () => {
                dialog.close();
                dialog.overlay.remove();
            });
        }
        this.dialogManager.register("welcome", dialog);
        this.dialogManager.open("welcome");
    }

    _bindMenus() {
        const menuRoots = Array.from(document.querySelectorAll("[data-tv-menu-root]"));
        let activeRoot = null;

        menuRoots.forEach((root) => {
            const toggle = root.querySelector("[data-tv-menu-toggle]");
            if (!toggle) { return; }
            toggle.addEventListener("click", (event) => {
                event.preventDefault();
                if (activeRoot === root) {
                    closeMenus();
                } else {
                    closeMenus();
                    const popup = root.querySelector("[data-tv-menu-popup]");
                    if (popup) {
                        popup.hidden = false;
                        toggle.setAttribute("aria-expanded", "true");
                        toggle.classList.add("is-current");
                        activeRoot = root;
                        requestAnimationFrame(fillBorders);
                    }
                }
            });
        });

        document.querySelectorAll("[data-tv-dialog-open]").forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                this.dialogManager.open(element.getAttribute("data-tv-dialog-open") || "");
            });
        });

        document.querySelectorAll("[data-tv-theme-set]").forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                applyThemeAndSyncPalette(element.getAttribute("data-tv-theme-set") || "default", true);
                this.dialogManager.applyActiveStates();
                fillBorders();
            });
        });

        document.querySelectorAll("[data-tv-bundle-open]").forEach((element) => {
            element.addEventListener("click", async (event) => {
                event.preventDefault();
                closeMenus();
                const filename = element.dataset.tvBundleOpen;
                const cached = bundleCache.has(filename);
                let loadingDialog = null;
                if (!cached) {
                    loadingDialog = new TVLoadingDialog(this.desktop);
                    loadingDialog.show(filename);
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
                    this.windowManager.showIndex(bundle);
                } catch (error) {
                    if (loadingDialog) { loadingDialog.destroy(); }
                    if (error.name === "AbortError") { return; }
                    console.error(`Failed to load bundle ${filename}:`, error);
                }
            });
        });

        document.querySelectorAll("[data-tv-doc-open]").forEach((element) => {
            element.addEventListener("click", async (event) => {
                event.preventDefault();
                closeMenus();
                const docFile = element.dataset.tvDocOpen;
                try {
                    const resp = await fetch(DOCS_DIR + docFile);
                    if (!resp.ok) { throw new Error(`HTTP ${resp.status}`); }
                    const md = await resp.text();
                    this._openDocWindow(docFile, md);
                } catch (error) {
                    console.error(`Failed to load doc ${docFile}:`, error);
                }
            });
        });

        document.querySelectorAll("[data-tv-window-cmd]").forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                const cmd = element.dataset.tvWindowCmd;
                if (cmd === "zoom") {
                    this.windowManager.toggleZoom();
                } else if (cmd === "close") {
                    this.windowManager.closeAll();
                    fillBorders();
                    fillDesktopPatterns();
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

        document.querySelectorAll("[data-tv-bundle-back]").forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager) {
                    this.windowManager.goBack();
                }
            });
        });

        document.addEventListener("click", (event) => {
            if (!event.target.closest("[data-tv-menu-root]")) {
                closeMenus();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && activeRoot) {
                event.preventDefault();
                closeMenus();
                return;
            }
            // F5 → Zoom
            if (event.key === "F5" && !event.ctrlKey && !event.altKey && !event.shiftKey) {
                event.preventDefault();
                this.windowManager.toggleZoom();
                return;
            }
            // Alt-F3 → Close
            if (event.key === "F3" && event.altKey && !event.ctrlKey && !event.shiftKey) {
                event.preventDefault();
                this.windowManager.closeAll();
                fillBorders();
                fillDesktopPatterns();
                return;
            }
            // Alt-0 → Window List
            if (event.key === "0" && event.altKey && !event.ctrlKey && !event.shiftKey) {
                event.preventDefault();
                this._showWindowList();
                return;
            }
        });

        function closeMenus() {
            closeSubmenus();
            menuRoots.forEach((root) => {
                const popup = root.querySelector("[data-tv-menu-popup]");
                const toggle = root.querySelector("[data-tv-menu-toggle]");
                if (popup) { popup.hidden = true; }
                if (toggle) {
                    toggle.setAttribute("aria-expanded", "false");
                    toggle.classList.remove("is-current");
                }
            });
            activeRoot = null;
        }

        function closeSubmenus() {
            document.querySelectorAll("[data-tv-submenu-popup]").forEach((popup) => {
                popup.hidden = true;
            });
            document.querySelectorAll("[data-tv-submenu-toggle]").forEach((el) => {
                el.classList.remove("is-submenu-open");
            });
        }

        // Bind submenu toggles: hover opens nested popup.
        document.querySelectorAll("[data-tv-submenu-toggle]").forEach((toggle) => {
            const root = toggle.closest("[data-tv-submenu-root]");
            if (!root) { return; }
            const popup = root.querySelector("[data-tv-submenu-popup]");
            if (!popup) { return; }

            toggle.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const isOpen = !popup.hidden;
                closeSubmenus();
                if (!isOpen) {
                    popup.hidden = false;
                    toggle.classList.add("is-submenu-open");
                    requestAnimationFrame(() => fillBorders(popup));
                }
            });

            root.addEventListener("mouseenter", () => {
                closeSubmenus();
                popup.hidden = false;
                toggle.classList.add("is-submenu-open");
                requestAnimationFrame(() => fillBorders(popup));
            });

            root.addEventListener("mouseleave", (event) => {
                // Only close if mouse isn't moving to the submenu popup
                const related = event.relatedTarget;
                if (related && (popup.contains(related) || root.contains(related))) { return; }
                popup.hidden = true;
                toggle.classList.remove("is-submenu-open");
            });
        });
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
