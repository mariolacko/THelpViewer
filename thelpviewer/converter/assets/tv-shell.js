// Turbo Vision shell and application bootstrap helpers.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    TVAppContext,
    TVWidget,
    TVStaticText,
    TVButton,
    TVMenuBox,
    escapeHtml,
    renderHotkeyMarkup,
    fillBorders,
    fillDesktopPatterns,
    updateClocks,
    bindCloseButtons,
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
    TVScreenSaver,
    TurboVisionScrollbar,
    measureCells,
    SCROLL_REPEAT_MS,
    TRACK_CHAR,
    DISABLED_TRACK_CHAR,
    THUMB_CHAR,
    highlightCodeExamples,
} = TV;

class TVMenuBar extends TVWidget {
    constructor(container, context) {
        super(container);
        this.context = context;
    }

    menuActions() {
        return this.context.uiConfig.menu.popup;
    }

    renderItem(entry) {
        switch (entry.type) {
            case "menu-root":
                return [
                    "<div class=\"tv-menu-root\" data-tv-menu-root>",
                    new TVButton({
                        dialog: false,
                        className: "tv-menu-item tv-menu-button",
                        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
                        labelMarkup: renderHotkeyMarkup(entry.label || "~X~"),
                    }).renderMarkup(),
                    this.renderPopup(),
                    "</div>",
                ].join("");
            case "help-link":
                return `<a class="tv-menu-item${this.context.pageKind === "index" ? " is-current" : ""}" href="${escapeHtml(this.context.helpHref)}">${renderHotkeyMarkup(entry.label || "~H~elp")}</a>`;
            case "index-link":
                return `<a class="tv-menu-item" href="${escapeHtml(this.context.indexHref)}">${renderHotkeyMarkup(entry.label || "~I~ndex")}</a>`;
            case "topic-link":
                if (!(this.context.pageKind === "topic" && this.context.topicContext && this.context.topicHref)) {
                    return "";
                }
                return `<a class="tv-menu-item is-current" href="${escapeHtml(this.context.topicHref)}">${renderHotkeyMarkup((entry.label || "~T~opic {topic}").replace("{topic}", this.context.topicContext))}</a>`;
            default:
                return "";
        }
    }

    renderPopup() {
        return new TVMenuBox({
            attrs: { "data-tv-menu-popup": true, hidden: true },
            items: this.menuActions().map((entry) => {
                if (entry.type === "separator") {
                    return '<div class="tv-menu-popup-separator" aria-hidden="true">'
                        + '<span class="tv-border-corner">├</span>'
                        + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                        + '<span class="tv-border-corner">┤</span>'
                        + '</div>';
                }
                if (entry.type === "submenu") {
                    const subItems = (entry.items || []).map((sub) => new TVButton({
                        dialog: false,
                        className: "tv-menu-popup-item",
                        attrs: sub.type === "saver"
                            ? { type: "button", "data-tv-saver-start": sub.mode }
                            : { type: "button", "data-tv-dialog-open": sub.dialog },
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
    }

    render() {
        const items = this.context.uiConfig.menu.items
            .map((entry) => this.renderItem(entry))
            .filter(Boolean);
        this.root.innerHTML = [
            `<nav class="tv-menu-items">${items.join("")}</nav>`,
            "<div class=\"tv-menu-clock\" data-tv-clock>00:00:00</div>",
        ].join("");
    }
}

class TVStatusLine extends TVWidget {
    constructor(container, context) {
        super(container);
        this.context = context;
    }

    renderItem(entry) {
        switch (entry.type) {
            case "back":
                return new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-back": true, "data-tv-fallback": this.context.indexHref },
                    labelMarkup: renderHotkeyMarkup(entry.label || "~B~ack"),
                }).renderMarkup();
            case "index-link":
                return `<a class="tv-status-item" href="${escapeHtml(this.context.indexHref)}">${renderHotkeyMarkup(entry.label || "~F1~ Index")}</a>`;
            case "dialog":
                return new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-dialog-open": entry.dialog },
                    labelMarkup: renderHotkeyMarkup(entry.label || ""),
                }).renderMarkup();
            case "hint":
                return `<span class="tv-status-hint">${escapeHtml(this.context.statusHint)}</span>`;
            case "link":
                return `<a class="tv-status-link" href="${escapeHtml(entry.href)}" target="_blank" rel="noopener">${escapeHtml(entry.label)}</a>`;
            default:
                return "";
        }
    }

    render() {
        this.root.innerHTML = this.context.uiConfig.status
            .map((entry) => this.renderItem(entry))
            .filter(Boolean)
            .join("");
    }
}

function buildAppChrome() {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    const statusLine = document.querySelector("[data-tv-status-line]");
    const context = new TVAppContext();

    if (menuBar) {
        new TVMenuBar(menuBar, context).render();
    }

    if (statusLine) {
        new TVStatusLine(statusLine, context).render();
    }
}

function bindBackButtons() {
    document.querySelectorAll("[data-tv-back]").forEach((element) => {
        if (element.dataset.tvBackBound === "1") {
            return;
        }
        element.dataset.tvBackBound = "1";
        element.addEventListener("click", (event) => {
            event.preventDefault();
            const fallback = element.getAttribute("data-tv-fallback") || "index.html";
            if (window.history.length > 1) {
                window.history.back();
                return;
            }
            window.location.href = fallback;
        });
    });
}

class TurboVisionWindowResizer {
    constructor(windowElement) {
        this.windowElement = windowElement;
        this.desktop = windowElement.closest(".tv-desktop");
        this.moveHandle = windowElement.querySelector("[data-tv-move-handle]");
        this.handle = windowElement.querySelector("[data-tv-resize-handle]");
        this.dragState = null;
        this.moveState = null;
        this.storageKey = this.buildStorageKey();
        this.restoreSnapshot = null;
        this.bind();
        if (!this.restoreState()) {
            this.centerWindow();
            this.restoreSnapshot = this.captureGeometry();
        }
        window.addEventListener("beforeunload", () => this.persistState(), { passive: true });
    }

    bind() {
        if (this.handle) {
            this.handle.addEventListener("mousedown", (event) => this.startResize(event));
        }
        if (this.moveHandle) {
            this.lastMoveDown = 0;
            this.moveHandle.addEventListener("mousedown", (event) => this.startMove(event));
        }
    }

    buildStorageKey() {
        const path = window.location.pathname.replace(/[^/]*$/, "");
        return `thelp:window:${path}`;
    }

    centerWindow() {
        if (!this.desktop) {
            return;
        }
        const left = Math.max(0, Math.floor((this.desktop.clientWidth - this.windowElement.offsetWidth) / 2));
        const top = Math.max(0, Math.floor((this.desktop.clientHeight - this.windowElement.offsetHeight) / 2));
        this.windowElement.style.setProperty("--tv-window-left", `${left}px`);
        this.windowElement.style.setProperty("--tv-window-top", `${top}px`);
    }

    startResize(event) {
        if (this.windowElement.classList.contains("is-maximized")) {
            return;
        }
        event.preventDefault();
        const cell = measureCells();
        const style = getComputedStyle(this.windowElement);
        const left = this.numericVar(style, "--tv-window-left", this.windowElement.offsetLeft);
        const top = this.numericVar(style, "--tv-window-top", this.windowElement.offsetTop);
        this.dragState = {
            startX: event.clientX,
            startY: event.clientY,
            startCols: this.numericVar(style, "--tv-window-cols", Math.round(this.windowElement.offsetWidth / cell.width)),
            startRows: this.numericVar(style, "--tv-window-rows", Math.round(this.windowElement.offsetHeight / cell.height)),
            minCols: this.numericVar(style, "--tv-window-min-cols", 80),
            minRows: this.numericVar(style, "--tv-window-min-rows", 25),
            maxCols: this.desktop ? Math.max(1, Math.floor((this.desktop.clientWidth - left) / cell.width)) : Infinity,
            maxRows: this.desktop ? Math.max(1, Math.floor((this.desktop.clientHeight - top) / cell.height)) : Infinity,
            cellWidth: cell.width,
            cellHeight: cell.height,
        };
        document.addEventListener("mousemove", this.onResizeMove);
        document.addEventListener("mouseup", this.onResizeEnd);
    }

    startMove(event) {
        if (event.target.closest(".tv-close-control")) {
            return;
        }
        event.preventDefault();
        const now = Date.now();
        const wasDblClick = now - this.lastMoveDown < 500;
        this.lastMoveDown = wasDblClick ? 0 : now;
        if (wasDblClick) {
            this.toggleMaximize(event);
            return;
        }
        if (this.windowElement.classList.contains("is-maximized")) {
            return;
        }
        const style = getComputedStyle(this.windowElement);
        this.moveState = {
            startX: event.clientX,
            startY: event.clientY,
            startLeft: this.numericVar(style, "--tv-window-left", this.windowElement.offsetLeft),
            startTop: this.numericVar(style, "--tv-window-top", this.windowElement.offsetTop),
        };
        document.addEventListener("mousemove", this.onMoveDrag);
        document.addEventListener("mouseup", this.onMoveEnd);
    }

    numericVar(style, name, fallback) {
        const value = Number.parseFloat(style.getPropertyValue(name));
        return Number.isFinite(value) ? value : fallback;
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    captureGeometry() {
        const style = getComputedStyle(this.windowElement);
        return {
            left: this.numericVar(style, "--tv-window-left", this.windowElement.offsetLeft),
            top: this.numericVar(style, "--tv-window-top", this.windowElement.offsetTop),
            cols: this.numericVar(style, "--tv-window-cols", Math.round(this.windowElement.offsetWidth / measureCells().width)),
            rows: this.numericVar(style, "--tv-window-rows", Math.round(this.windowElement.offsetHeight / measureCells().height)),
        };
    }

    sanitizeGeometry(state) {
        if (!state || typeof state !== "object") {
            return null;
        }
        const left = Number.parseFloat(state.left);
        const top = Number.parseFloat(state.top);
        const cols = Number.parseInt(state.cols, 10);
        const rows = Number.parseInt(state.rows, 10);
        if (![left, top, cols, rows].every(Number.isFinite)) {
            return null;
        }
        return {
            left: Math.max(0, left),
            top: Math.max(0, top),
            cols: Math.max(1, cols),
            rows: Math.max(1, rows),
        };
    }

    applyGeometry(geometry) {
        this.windowElement.style.setProperty("--tv-window-left", `${geometry.left}px`);
        this.windowElement.style.setProperty("--tv-window-top", `${geometry.top}px`);
        this.windowElement.style.setProperty("--tv-window-cols", String(geometry.cols));
        this.windowElement.style.setProperty("--tv-window-rows", String(geometry.rows));
    }

    readStoredState() {
        try {
            const raw = window.localStorage.getItem(this.storageKey);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    persistState() {
        const state = {
            ...this.captureGeometry(),
            maximized: this.windowElement.classList.contains("is-maximized"),
            restore: this.restoreSnapshot,
        };
        try {
            window.localStorage.setItem(this.storageKey, JSON.stringify(state));
        } catch {
            // Ignore storage failures under restrictive file:// environments.
        }
    }

    restoreState() {
        const state = this.readStoredState();
        if (!state) {
            return false;
        }
        const restore = this.sanitizeGeometry(state.restore);
        const current = this.sanitizeGeometry(state);
        if (!current) {
            return false;
        }
        this.restoreSnapshot = restore || current;
        this.applyGeometry(this.restoreSnapshot);
        this.enforceMinimumSize();
        if (state.maximized) {
            this.maximize(false);
        } else {
            this.windowElement.classList.remove("is-maximized");
        }
        fillBorders();
        return true;
    }

    enforceMinimumSize() {
        const style = getComputedStyle(this.windowElement);
        const cols = this.numericVar(style, "--tv-window-cols", 1);
        const rows = this.numericVar(style, "--tv-window-rows", 1);
        const minCols = this.numericVar(style, "--tv-window-min-cols", 1);
        const minRows = this.numericVar(style, "--tv-window-min-rows", 1);
        let changed = false;
        if (cols < minCols) {
            this.windowElement.style.setProperty("--tv-window-cols", String(minCols));
            changed = true;
        }
        if (rows < minRows) {
            this.windowElement.style.setProperty("--tv-window-rows", String(minRows));
            changed = true;
        }
        if (changed) {
            this.restoreSnapshot = this.captureGeometry();
        }
    }

    maximize(persist = true) {
        if (!this.desktop) {
            return;
        }
        if (!this.windowElement.classList.contains("is-maximized")) {
            this.restoreSnapshot = this.captureGeometry();
        }
        this.windowElement.classList.add("is-maximized");
        this.windowElement.style.setProperty("--tv-window-left", "0px");
        this.windowElement.style.setProperty("--tv-window-top", "0px");
        const zoomGlyph = this.windowElement.querySelector("[data-tv-zoom-glyph]");
        if (zoomGlyph) { zoomGlyph.textContent = "↓"; }
        fillBorders();
        if (persist) {
            this.persistState();
        }
    }

    restore(persist = true) {
        this.windowElement.classList.remove("is-maximized");
        if (this.restoreSnapshot) {
            this.applyGeometry(this.restoreSnapshot);
        }
        const zoomGlyph = this.windowElement.querySelector("[data-tv-zoom-glyph]");
        if (zoomGlyph) { zoomGlyph.textContent = "↑"; }
        fillBorders();
        if (persist) {
            this.persistState();
        }
    }

    toggleMaximize(event) {
        if (event.target.closest(".tv-close-control")) {
            return;
        }
        if (this.windowElement.classList.contains("is-maximized")) {
            this.restore();
        } else {
            this.maximize();
        }
    }

    onResizeMove = (event) => {
        if (!this.dragState) {
            return;
        }
        const deltaCols = Math.round((event.clientX - this.dragState.startX) / this.dragState.cellWidth);
        const deltaRows = Math.round((event.clientY - this.dragState.startY) / this.dragState.cellHeight);
        const nextCols = Math.min(
            this.dragState.maxCols,
            Math.max(this.dragState.minCols, this.dragState.startCols + deltaCols)
        );
        const nextRows = Math.min(
            this.dragState.maxRows,
            Math.max(this.dragState.minRows, this.dragState.startRows + deltaRows)
        );
        this.windowElement.style.setProperty("--tv-window-cols", String(nextCols));
        this.windowElement.style.setProperty("--tv-window-rows", String(nextRows));
        fillBorders();
    };

    onResizeEnd = () => {
        this.dragState = null;
        document.removeEventListener("mousemove", this.onResizeMove);
        document.removeEventListener("mouseup", this.onResizeEnd);
        this.restoreSnapshot = this.captureGeometry();
        this.persistState();
    };

    onMoveDrag = (event) => {
        if (!this.moveState) {
            return;
        }
        const width = this.windowElement.offsetWidth;
        const height = this.windowElement.offsetHeight;
        const rawLeft = this.moveState.startLeft + (event.clientX - this.moveState.startX);
        const rawTop = this.moveState.startTop + (event.clientY - this.moveState.startY);
        const maxLeft = this.desktop ? Math.max(0, this.desktop.clientWidth - width) : rawLeft;
        const maxTop = this.desktop ? Math.max(0, this.desktop.clientHeight - height) : rawTop;
        const nextLeft = this.clamp(rawLeft, 0, maxLeft);
        const nextTop = this.clamp(rawTop, 0, maxTop);
        this.windowElement.style.setProperty("--tv-window-left", `${nextLeft}px`);
        this.windowElement.style.setProperty("--tv-window-top", `${nextTop}px`);
    };

    onMoveEnd = () => {
        this.moveState = null;
        document.removeEventListener("mousemove", this.onMoveDrag);
        document.removeEventListener("mouseup", this.onMoveEnd);
        this.restoreSnapshot = this.captureGeometry();
        this.persistState();
    };
}

class TurboVisionMenus {
    constructor(dialogManager) {
        this.desktop = document.querySelector(".tv-desktop") || document.body;
        this.menuRoots = Array.from(document.querySelectorAll("[data-tv-menu-root]"));
        this.activeRoot = null;
        this.dialogManager = dialogManager;
        this.bind();
    }

        bind() {
            this.menuRoots.forEach((root) => {
                const toggle = root.querySelector("[data-tv-menu-toggle]");
                if (!toggle) {
                    return;
            }
            toggle.addEventListener("click", (event) => this.onToggleClick(event, root));
            root.addEventListener("mouseenter", () => {
                if (this.activeRoot && this.activeRoot !== root) {
                    this.openMenu(root);
                }
            });
        });

            document.querySelectorAll("[data-tv-dialog-open]").forEach((element) => {
                element.addEventListener("click", (event) => this.onDialogOpen(event, element.getAttribute("data-tv-dialog-open") || ""));
            });
            document.querySelectorAll("[data-tv-theme-set]").forEach((element) => {
                element.addEventListener("click", (event) => this.onThemeSet(event, element.getAttribute("data-tv-theme-set") || "default"));
            });

            document.addEventListener("click", (event) => this.onDocumentClick(event));
            document.addEventListener("keydown", (event) => this.onKeyDown(event));

            this.bindSubmenus();
        }

    onToggleClick(event, root) {
        event.preventDefault();
        if (this.activeRoot === root) {
            this.closeMenus();
        } else {
            this.openMenu(root);
        }
    }

        onDialogOpen(event, name) {
            event.preventDefault();
            this.closeMenus();
            this.dialogManager.open(name);
        }

        onThemeSet(event, themeName) {
            event.preventDefault();
            this.closeMenus();
            applyThemeAndSyncPalette(themeName || "default", true);
            if (this.dialogManager) {
                this.dialogManager.applyActiveStates();
            }
            if (window.THelpViewerTV && typeof window.THelpViewerTV.fillBorders === "function") {
                window.THelpViewerTV.fillBorders();
            }
        }

    onDocumentClick(event) {
        if (event.target.closest("[data-tv-menu-root]")) {
            return;
        }
        this.closeMenus();
    }

    onKeyDown(event) {
        if (event.defaultPrevented) {
            return;
        }
        if (event.key === "Escape") {
            for (const name of ["about", "puzzle", "calendar", "ascii", "colors"]) {
                if (this.dialogManager.isOpen(name)) {
                    event.preventDefault();
                    this.dialogManager.close(name);
                    return;
                }
            }
            if (this.dialogManager.isOpen("calc")) {
                return;
            }
            if (this.activeRoot) {
                event.preventDefault();
                this.closeMenus();
            }
        }
    }

    openMenu(root) {
        this.closeMenus();
        const popup = root.querySelector("[data-tv-menu-popup]");
        const toggle = root.querySelector("[data-tv-menu-toggle]");
        if (!popup || !toggle) {
            return;
        }
        popup.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        toggle.classList.add("is-current");
        this.activeRoot = root;
        fillBorders(popup);
        requestAnimationFrame(() => fillBorders(popup));
    }

    closeMenus() {
        this.closeSubmenus();
        this.menuRoots.forEach((root) => {
            const popup = root.querySelector("[data-tv-menu-popup]");
            const toggle = root.querySelector("[data-tv-menu-toggle]");
            if (popup) {
                popup.hidden = true;
            }
            if (toggle) {
                toggle.setAttribute("aria-expanded", "false");
                toggle.classList.remove("is-current");
            }
        });
        this.activeRoot = null;
    }

    closeSubmenus() {
        document.querySelectorAll("[data-tv-submenu-popup]").forEach((popup) => {
            popup.hidden = true;
        });
        document.querySelectorAll("[data-tv-submenu-toggle]").forEach((el) => {
            el.classList.remove("is-submenu-open");
        });
    }

    bindSubmenus() {
        document.querySelectorAll("[data-tv-submenu-toggle]").forEach((toggle) => {
            const root = toggle.closest("[data-tv-submenu-root]");
            if (!root) { return; }
            const popup = root.querySelector("[data-tv-submenu-popup]");
            if (!popup) { return; }

            toggle.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const isOpen = !popup.hidden;
                this.closeSubmenus();
                if (!isOpen) {
                    popup.hidden = false;
                    toggle.classList.add("is-submenu-open");
                    requestAnimationFrame(() => fillBorders(popup));
                }
            });

            root.addEventListener("mouseenter", () => {
                this.closeSubmenus();
                popup.hidden = false;
                toggle.classList.add("is-submenu-open");
                requestAnimationFrame(() => fillBorders(popup));
            });

            root.addEventListener("mouseleave", (event) => {
                const related = event.relatedTarget;
                if (related && (popup.contains(related) || root.contains(related))) { return; }
                popup.hidden = true;
                toggle.classList.remove("is-submenu-open");
            });
        });
    }

}

class TVApplication {
    constructor() {
        this.menuBar = null;
        this.searchDialog = null;
        this.menus = null;
        this.dialogManager = null;
        this.screenSaver = null;
        this.scrollbars = [];
        this.resizers = [];
        this.errors = [];
    }

    registerDialog(name, factory) {
        try {
            const dialog = factory();
            if (!dialog) {
                return null;
            }
            return this.dialogManager.register(name, dialog);
        } catch (error) {
            this.errors.push({ name, error });
            console.error(`Failed to initialize dialog: ${name}`, error);
            return null;
        }
    }

    initTheme() {
        document.documentElement.classList.add("tv-js");
        applyThemePreset(readStoredThemePreset(), false);
        const storedPalette = readStoredColorPalette();
        if (storedPalette) {
            applyColorPalette(storedPalette, false);
        } else {
            TV.setActiveColorPalette(buildPaletteFromCurrentStyle());
        }
    }

    initChrome() {
        buildAppChrome();
        bindCloseButtons();
        bindBackButtons();
    }

    initShellWidgets() {
        const desktop = document.querySelector(".tv-desktop") || document.body;
        const hostWindow = document.querySelector("[data-tv-window]");
        this.dialogManager = new TVDialogManager(desktop);
        this.dialogManager.setHostWindow(hostWindow);
        this.scrollbars = Array.from(document.querySelectorAll("[data-tv-scroll-frame]"), (frame) => new TurboVisionScrollbar(frame));
        this.resizers = Array.from(document.querySelectorAll("[data-tv-window]"), (windowElement) => new TurboVisionWindowResizer(windowElement));
        this.menus = new TurboVisionMenus(this.dialogManager);
        if (hostWindow && hostWindow.dataset.tvHostWindowBound !== "1") {
            hostWindow.dataset.tvHostWindowBound = "1";
            hostWindow.addEventListener("mousedown", (event) => {
                if (event.target.closest(".tv-close-control, .tv-grow-handle, .tv-scrollbar, .tv-menu-bar, .tv-status-line")) {
                    return;
                }
                this.dialogManager.activateHostWindow();
            });
        }
        this.registerDialog("about", () => new TVAboutDialog(desktop));
        this.registerDialog("puzzle", () => new TVPuzzleDialog(desktop));
        this.registerDialog("calendar", () => new TVCalendarDialog(desktop));
        this.registerDialog("ascii", () => new TVAsciiTableDialog(desktop));
        this.registerDialog("calc", () => new TVCalculatorDialog(desktop));
        this.registerDialog("colors", () => new TVColorsDialog(desktop));
        this.searchDialog = this.registerDialog("search", () => new TVSearchDialog(desktop));
        if (this.searchDialog) {
            this.dialogManager.bindOpeners("[data-tv-search-open]", "search");
        }
        this.dialogManager.applyActiveStates();
        // Screen savers
        const saverModes = TVScreenSaver.modes;
        const savers = {};
        for (const name of Object.keys(saverModes)) {
            savers[name] = new saverModes[name]();
        }
        document.querySelectorAll("[data-tv-saver-start]").forEach((element) => {
            element.addEventListener("click", (event) => {
                event.preventDefault();
                const saver = savers[element.dataset.tvSaverStart];
                if (saver) { saver.start(); }
            });
        });
        // Auto-start screensaver after 5 minutes of inactivity
        const SAVER_IDLE_MS = 5 * 60 * 1000;
        const saverNames = Object.keys(saverModes);
        let saverIdleTimer = null;
        const resetIdleTimer = () => {
            if (saverIdleTimer !== null) { clearTimeout(saverIdleTimer); }
            saverIdleTimer = setTimeout(() => {
                if (!TVScreenSaver.active) {
                    const mode = saverNames[Math.floor(Math.random() * saverNames.length)];
                    savers[mode].start();
                }
            }, SAVER_IDLE_MS);
        };
        for (const evt of ["mousemove", "mousedown", "keydown", "scroll", "touchstart"]) {
            document.addEventListener(evt, resetIdleTimer, { passive: true });
        }
        resetIdleTimer();
        if (this.errors.length) {
            window.THelpViewerTVInitErrors = this.errors;
        }
    }

    initLayout() {
        fillBorders();
        fillDesktopPatterns();
        updateClocks();
        window.setInterval(updateClocks, 1000);
        window.addEventListener("resize", fillBorders, { passive: true });
        window.addEventListener("resize", fillDesktopPatterns, { passive: true });
        window.addEventListener("load", fillBorders, { passive: true });
        window.addEventListener("load", fillDesktopPatterns, { passive: true });
        window.addEventListener("load", updateClocks, { passive: true });
        highlightCodeExamples(document);
    }

    start() {
        this.initTheme();
        this.initChrome();
        this.initLayout();
        this.initShellWidgets();
    }
}


Object.assign(TV, {
    TVMenuBar,
    TVStatusLine,
    TurboVisionScrollbar,
    TurboVisionWindowResizer,
    TurboVisionMenus,
    TVApplication,
    initTurboVision() {
        new TVApplication().start();
    },
});
})();
