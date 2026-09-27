// Turbo Vision shell and application bootstrap helpers.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    TVAppContext,
    TVRect,
    TVView,
    TVStaticText,
    TVMenu,
    NewLine,
    NewSubMenu,
    TVMenuView,
    TVMenuItem,
    TVMenuBox,
    NewStatusKey,
    TVStatusLine,
    TVDesktop,
    TVProgram,
    TVEvent,
    escapeHtml,
    renderHotkeyMarkup,
    fillBorders,
    bindCloseButtons,
    applyThemeAndSyncPalette,
    initializeTVTheme,
    TV_COMMANDS,
    TV_HELP_CONTEXTS,
    TVMenuController,
    TVHelpController,
    TVAboutDialog,
    TVContextHelpWindow,
    TVPuzzleDialog,
    TVHanoiDialog,
    TVTronDialog,
    TVCalendarDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVColorsDialog,
    TVViewGalleryDialog,
    TVMidiPlayerDialog,
    TVSystemInformationDialog,
    TVSearchDialog,
    TVScreenSaver,
    TVScrollBar,
    measureCells,
    SCROLL_REPEAT_MS,
    TRACK_CHAR,
    DISABLED_TRACK_CHAR,
    THUMB_CHAR,
    highlightCodeExamples,
    setElementHelpContext,
    kbF1,
    kbF3,
    evKeyDown,
} = TV;

const {
    hcSystemMenu,
    hcHelpViewer,
    hcNoContext,
} = TV_HELP_CONTEXTS;

class TVMenuBar extends TVMenuView {
    constructor(bounds, context) {
        super(bounds);
        this.context = context;
    }

    menuActions() {
        return this.context.uiConfig.menu.popup;
    }

    renderItem(entry) {
        switch (entry.type) {
            case "menu-root":
                return [
                    `<div class="tv-menu-root" data-tv-menu-root data-tv-help-ctx="${hcSystemMenu}">`,
                    this.drawItem(new TVMenuItem(
                        renderHotkeyMarkup(entry.label || "~X~"),
                        "menu-toggle",
                    ), "bar"),
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
        return new TVMenuBox(new TVRect(), new TVMenu(this.menuActions().map((entry) => {
                if (entry.type === "separator") {
                    return NewLine();
                }
                if (entry.type === "submenu") {
                    const subItems = (entry.items || []).map((sub) => new TVMenuItem(
                        renderHotkeyMarkup(sub.label),
                        sub.type === "saver" ? "saver-start" : "dialog-open",
                        0,
                        hcNoContext,
                        sub.type === "saver" ? sub.mode : sub.dialog,
                    ));
                    return NewSubMenu(
                        renderHotkeyMarkup(entry.label),
                        hcSystemMenu,
                        new TVMenu(subItems),
                    );
                }
                const action = entry.type === "theme"
                    ? { command: "theme-set", value: entry.theme }
                    : entry.type === "saver"
                        ? { command: "saver-start", value: entry.mode }
                        : entry.type === "context-help"
                            ? { command: "context-help" }
                        : { command: "dialog-open", value: entry.dialog };
                return new TVMenuItem(
                    renderHotkeyMarkup(entry.label),
                    action.command,
                    0,
                    hcNoContext,
                    action.value,
                );
            }))).draw();
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

class TVPageStatusLine extends TVStatusLine {
    constructor(bounds, context) {
        super(bounds);
        this.context = context;
    }

    renderItem(entry) {
        switch (entry.type) {
            case "back":
                return NewStatusKey(
                    renderHotkeyMarkup(entry.label || "~B~ack"),
                    0,
                    "back",
                    { value: true, fallback: this.context.indexHref },
                );
            case "index-link":
                return `<a class="tv-status-item" href="${escapeHtml(this.context.indexHref)}">${renderHotkeyMarkup(entry.label || "~F1~ Index")}</a>`;
            case "context-help":
                return NewStatusKey(
                    renderHotkeyMarkup(entry.label || "~F1~ Help"),
                    kbF1,
                    "context-help",
                );
            case "dialog":
                return NewStatusKey(
                    renderHotkeyMarkup(entry.label || ""),
                    entry.dialog === "search" ? kbF3 : 0,
                    "dialog-open",
                    entry.dialog,
                );
            case "hint":
                return `<span class="tv-status-hint">${escapeHtml(this.context.statusHint)}</span>`;
            case "link":
                return `<a class="tv-status-link" href="${escapeHtml(entry.href)}" target="_blank" rel="noopener">${escapeHtml(entry.label)}</a>`;
            default:
                return "";
        }
    }

    render() {
        const items = this.context.uiConfig.status
            .map((entry) => this.renderItem(entry))
            .filter(Boolean);
        const hintIndex = items.findIndex((item) => typeof item === "string" && item.indexOf("tv-status-hint") !== -1);
        if (hintIndex > 0) {
            items.splice(hintIndex, 0, '<span class="tv-status-separator" aria-hidden="true">│</span>');
        }
        this.items = items;
        this.root.innerHTML = this.draw();
    }
}

function buildAppChrome() {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    const statusLine = document.querySelector("[data-tv-status-line]");
    const context = new TVAppContext();

    if (menuBar) {
        new TVMenuBar(new TVRect(), context).bindRoot(menuBar).render();
    }

    if (statusLine) {
        new TVPageStatusLine(new TVRect(), context).bindRoot(statusLine).render();
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
        this.destroyed = false;
        this.onHandleMouseDown = (event) => this.startResize(event);
        this.onMoveHandleMouseDown = (event) => this.startMove(event);
        this.onBeforeUnload = () => this.persistState();
        this.bind();
        if (!this.restoreState()) {
            this.centerWindow();
            this.restoreSnapshot = this.captureGeometry();
        }
        window.addEventListener("beforeunload", this.onBeforeUnload, { passive: true });
    }

    bind() {
        if (this.handle) {
            this.handle.addEventListener("mousedown", this.onHandleMouseDown);
        }
        if (this.moveHandle) {
            this.lastMoveDown = 0;
            this.moveHandle.addEventListener("mousedown", this.onMoveHandleMouseDown);
        }
    }

    buildStorageKey() {
        const path = window.location.pathname.replace(/[^/]*$/, "");
        const identity = this.windowElement.dataset.tvWindowStorageKey || "";
        return identity ? `thelp:window:${path}:${identity}` : `thelp:window:${path}`;
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
        this.setResizeFrame(true);
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
        this.setMoveFrame(true);
        document.addEventListener("mousemove", this.onMoveDrag);
        document.addEventListener("mouseup", this.onMoveEnd);
    }

    setResizeFrame(active) {
        this.windowElement.classList.toggle("is-resizing", active);
        this.setWindowFrame(active);
    }

    setMoveFrame(active) {
        if (this.windowElement.classList.contains("is-resizing")) {
            return;
        }
        this.windowElement.classList.toggle("is-moving", active);
        this.setWindowFrame(active);
    }

    setWindowFrame(singleFrame) {
        const chars = singleFrame
            ? { tl: "┌", tr: "┐", bl: "└", top: "─", side: "│" }
            : { tl: "╔", tr: "╗", bl: "╚", top: "═", side: "║" };
        this.windowElement.querySelectorAll("[data-tv-frame-corner]").forEach((element) => {
            const corner = element.getAttribute("data-tv-frame-corner");
            if (corner && chars[corner]) {
                element.textContent = chars[corner];
            }
        });
        this.windowElement.querySelectorAll(".tv-border-top [data-tv-border-fill]").forEach((element) => {
            element.setAttribute("data-tv-border-fill", chars.top);
        });
        this.windowElement.querySelectorAll("[data-tv-border-side]").forEach((element) => {
            element.setAttribute("data-tv-border-side", chars.side);
        });
        fillBorders(this.windowElement);
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
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
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
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
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
        this.setResizeFrame(false);
        document.removeEventListener("mousemove", this.onResizeMove);
        document.removeEventListener("mouseup", this.onResizeEnd);
        this.restoreSnapshot = this.captureGeometry();
        this.persistState();
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
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
        this.setMoveFrame(false);
        document.removeEventListener("mousemove", this.onMoveDrag);
        document.removeEventListener("mouseup", this.onMoveEnd);
        this.restoreSnapshot = this.captureGeometry();
        this.persistState();
        window.dispatchEvent(new CustomEvent("tv-window-state-change"));
    };

    destroy() {
        if (this.destroyed) { return; }
        if (this.windowElement.isConnected) {
            this.persistState();
        }
        this.destroyed = true;
        this.dragState = null;
        this.moveState = null;
        document.removeEventListener("mousemove", this.onResizeMove);
        document.removeEventListener("mouseup", this.onResizeEnd);
        document.removeEventListener("mousemove", this.onMoveDrag);
        document.removeEventListener("mouseup", this.onMoveEnd);
        window.removeEventListener("beforeunload", this.onBeforeUnload);
        if (this.handle) {
            this.handle.removeEventListener("mousedown", this.onHandleMouseDown);
        }
        if (this.moveHandle) {
            this.moveHandle.removeEventListener("mousedown", this.onMoveHandleMouseDown);
        }
        this.windowElement.classList.remove("is-resizing");
        this.windowElement.classList.remove("is-moving");
    }
}

class TurboVisionMenus extends TVMenuController {
    constructor(dialogManager) {
        super();
        this.desktop = dialogManager?.desktop?.root || null;
        this.dialogManager = dialogManager;
    }
}

class TVApplication extends TVProgram {
    constructor() {
        super(new TVRect());
        this.menuBar = null;
        this.searchDialog = null;
        this.menus = null;
        this.helpController = null;
        this.contextHelpWindow = null;
        this.dialogManager = null;
        this.desktopView = null;
        this.screenSaver = null;
        this.scrollbars = [];
        this.resizers = [];
        this.errors = [];
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
            if (keyEvent.key === "F5" && !keyEvent.ctrlKey && !keyEvent.altKey && !keyEvent.shiftKey) {
                keyEvent.preventDefault();
                this.dialogManager.dispatchCommand(TV_COMMANDS.ZOOM);
            } else if (keyEvent.key === "F3" && keyEvent.altKey && !keyEvent.ctrlKey && !keyEvent.shiftKey) {
                keyEvent.preventDefault();
                this.dialogManager.dispatchCommand(TV_COMMANDS.CLOSE);
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
        const value = control?.getAttribute?.(`data-tv-${event.command}`) || "";
        let handled = true;
        if (event.command === "dialog-open") {
            this.dialogManager.open(value);
        } else if (event.command === "theme-set") {
            applyThemeAndSyncPalette(value || "default", true);
            this.dialogManager.applyActiveStates();
            fillBorders();
        } else if (event.command === "context-help") {
            this.helpController?.request();
        } else if (event.command === "saver-start") {
            const Saver = TVScreenSaver.modes[value];
            if (Saver) { new Saver().start(); }
        } else {
            handled = false;
        }
        if (handled) { this.clearEvent(event); }
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

    initContextHelpWindow() {
        try {
            const name = "contexthelp";
            const helpWindow = new TVContextHelpWindow();
            helpWindow.hide();
            const root = TVView._fromHTML(helpWindow.draw());
            helpWindow.resolve(root);
            root.dataset.tvWindowStorageKey = name;
            this.desktopView.insert(helpWindow);
            bindCloseButtons(root);

            const frame = root.querySelector("[data-tv-scroll-frame]");
            const scrollbar = frame ? new TVScrollBar(new TVRect()).bindRoot(frame) : null;
            const resizer = new TurboVisionWindowResizer(root);
            if (scrollbar) { this.scrollbars.push(scrollbar); }
            this.resizers.push(resizer);

            const close = () => {
                helpWindow.hide();
                this.dialogManager.unregisterWindow(name);
                fillBorders(root);
            };
            const zoom = () => {
                if (root.classList.contains("is-maximized")) { resizer.restore(); }
                else { resizer.maximize(); }
            };
            helpWindow.closeAction = close;
            helpWindow.zoomAction = zoom;
            helpWindow.openAction = () => {
                this.dialogManager.registerWindow(name, root, {
                    [TV_COMMANDS.CLOSE]: close,
                    [TV_COMMANDS.ZOOM]: zoom,
                });
                scrollbar?.refresh();
                fillBorders(root);
            };
            this.contextHelpWindow = helpWindow;
            return helpWindow;
        } catch (error) {
            this.errors.push({ name: "contexthelp", error });
            console.error("Failed to initialize context help window", error);
            return null;
        }
    }

    initTheme() {
        initializeTVTheme();
    }

    initChrome() {
        buildAppChrome();
        bindCloseButtons();
        bindBackButtons();
    }

    initShellWidgets() {
        const desktop = document.querySelector(".tv-desktop") || document.body;
        const hostWindow = document.querySelector("[data-tv-window]");
        this.desktopView = new TVDesktop(new TVRect()).bindRoot(desktop);
        this.dialogManager = this.desktopView.dialogManager;
        setElementHelpContext(hostWindow, hcHelpViewer);
        this.scrollbars = Array.from(
            document.querySelectorAll("[data-tv-scroll-frame]"),
            (frame) => new TVScrollBar(new TVRect()).bindRoot(frame),
        );
        this.resizers = Array.from(document.querySelectorAll("[data-tv-window]"), (windowElement) => new TurboVisionWindowResizer(windowElement));
        const hostResizer = this.resizers.find((resizer) => resizer.windowElement === hostWindow);
        this.dialogManager.setHostWindow(hostWindow, hostWindow ? {
            [TV_COMMANDS.CLOSE]: () => hostWindow.querySelector(".tv-close-control")?.click(),
            [TV_COMMANDS.ZOOM]: () => {
                if (!hostResizer) { return; }
                if (hostWindow.classList.contains("is-maximized")) {
                    hostResizer.restore();
                } else {
                    hostResizer.maximize();
                }
            },
        } : {});
        this.menus = new TurboVisionMenus(this.dialogManager);
        this.menus.commandTarget = this;
        if (hostWindow && hostWindow.dataset.tvHostWindowBound !== "1") {
            hostWindow.dataset.tvHostWindowBound = "1";
            hostWindow.addEventListener("mousedown", (event) => {
                if (event.target.closest(".tv-close-control, .tv-grow-handle, .tv-menu-bar, .tv-status-line")) {
                    return;
                }
                this.dialogManager.activateHostWindow();
            });
        }
        this.registerDialog("about", () => new TVAboutDialog());
        this.registerDialog("puzzle", () => new TVPuzzleDialog());
        this.registerDialog("hanoi", () => new TVHanoiDialog());
        this.registerDialog("tron", () => new TVTronDialog());
        this.registerDialog("calendar", () => new TVCalendarDialog());
        this.registerDialog("ascii", () => new TVAsciiTableDialog());
        this.registerDialog("calc", () => new TVCalculatorDialog());
        this.registerDialog("midi", () => new TVMidiPlayerDialog());
        this.registerDialog("colors", () => new TVColorsDialog());
        this.registerDialog("widgets", () => new TVViewGalleryDialog());
        this.registerDialog("systeminfo", () => new TVSystemInformationDialog());
        this.searchDialog = this.registerDialog("search", () => new TVSearchDialog());
        this.initContextHelpWindow();
        this.helpController = new TVHelpController({
            getMenuController: () => this.menus,
            getDialogManager: () => this.dialogManager,
            onHelp: (helpCtx) => this.contextHelpWindow?.openContext(helpCtx),
        });
        if (this.searchDialog) {
            this.dialogManager.bindOpeners("[data-tv-search-open]", "search");
        }
        this.dialogManager.applyActiveStates();
        TVScreenSaver.installIdleStart();
        if (this.errors.length) {
            window.THelpViewerTVInitErrors = this.errors;
        }
    }

    initLayout() {
        highlightCodeExamples(document);
        this.desktopView?.startLayout();
    }

    start() {
        this.initTheme();
        this.initChrome();
        this.initShellWidgets();
        this.initLayout();
    }
}


Object.assign(TV, {
    TVMenuBar,
    TVPageStatusLine,
    TVScrollBar,
    TurboVisionWindowResizer,
    TurboVisionMenus,
    TVApplication,
    initTurboVision() {
        new TVApplication().start();
    },
});
})();
