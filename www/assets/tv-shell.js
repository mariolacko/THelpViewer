// Turbo Vision shell and application bootstrap helpers.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    TVAppContext,
    TVRect,
    TVView,
    TVStaticText,
    TVGroup,
    TVDialog,
    TVButton,
    TVMessageBox,
    TVProgressDialog,
    bfDefault,
    sfModal,
    sfDisabled,
    TVMenu,
    TVMenuBar,
    NewLine,
    NewSubMenu,
    TVMenuItem,
    TVSubMenu,
    TVStatusItem,
    NewStatusKey,
    TVStatusLine,
    TVDesktop,
    TVWindow,
    TVProgram,
    TVEvent,
    escapeHtml,
    wrapTextLines,
    renderHotkeyMarkup,
    fillBorders,
    updateWindowFrameState,
    bindCloseButtons,
    applyThemeAndSyncPalette,
    initializeTVTheme,
    TV_COMMANDS,
    TV_HELP_CONTEXTS,
    TVMenuController,
    TVHelpController,
    TVAboutDialog,
    TVLoginDialog,
    TVAccountDialog,
    TVUsersDialog,
    TVRegistrationDialog,
    TVAddUserDialog,
    TVRegistrationTokenDialog,
    TVServerConfigurationDialog,
    TVHelpPackagesDialog,
    TVDosPackagesDialog,
    TVMidiSourcesDialog,
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
    TVGridDemoDialog,
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
    evCommand,
} = TV;

const {
    hcSystemMenu,
    hcHelpViewer,
    hcNoContext,
    hcAccount,
    hcColors,
    hcRegistrationTokens,
    hcServerConfiguration,
    hcHelpPackages,
    hcDosPackages,
    hcMidiSources,
    hcUsers,
} = TV_HELP_CONTEXTS;

const pageMenuActions = new WeakMap();

function pageMenuItem(name, command, value = "", param = "") {
    const item = new TVMenuItem(name, command, 0, hcNoContext, param);
    pageMenuActions.set(item, { value });
    return item;
}

function pageMenu(items) {
    const linked = items.filter((item) => item instanceof TVMenuItem);
    linked.forEach((item, index) => { item.next = linked[index + 1] || null; });
    return new TVMenu(linked[0] || null);
}

function pageSubMenu(name, items, helpCtx = hcNoContext) {
    return NewSubMenu(name, helpCtx, pageMenu(items));
}

class TVDownloadActionDialog extends TVDialog {
    constructor(item) {
        const width = Math.min(72, Math.max(20, Math.floor(window.innerWidth / measureCells().width) - 2));
        const label = `${item.kind.toUpperCase()}: ${item.label}`;
        const notice = "Remove only clears this queue entry; files are kept."
            + (item.retryable ? "" : "\nRetry is unavailable while work runs or for this operation.");
        const lines = wrapTextLines([label, "", item.error || "Download failed.", "", notice].join("\n"), width - 6);
        const buttonWidth = 14, buttonGap = 3;
        const buttonsPerRow = Math.max(1, Math.min(3, Math.floor((width - 2 + buttonGap) / (buttonWidth + buttonGap))));
        const buttonRows = Math.ceil(3 / buttonsPerRow);
        const buttonsY = lines.length + 2;
        const height = lines.length + 4 + 2 * buttonRows;
        super(new TVRect(0, 0, width, height), "Download failed");
        this.setHelpCtx(TV_HELP_CONTEXTS.hcDownloads);
        this.setState(sfModal, true);
        const buttons = ["~R~etry", "Re~m~ove", "~C~ancel"].map((title, index) => {
            const row = Math.floor(index / buttonsPerRow), column = index % buttonsPerRow;
            const count = Math.min(buttonsPerRow, 3 - row * buttonsPerRow);
            const rowWidth = count * buttonWidth + (count - 1) * buttonGap;
            const x = Math.floor((width - 2 - rowWidth) / 2) + column * (buttonWidth + buttonGap);
            const y = buttonsY + row * 2;
            return new TVButton(new TVRect(x, y, x + buttonWidth, y + 2), title,
                ["download-retry", "download-remove", "download-cancel"][index], index === 0 ? bfDefault : 0);
        });
        this.retryButton = buttons[0];
        this.retryButton.setState(sfDisabled, !item.retryable);
        this.insert(new TVGroup(new TVRect(0, 0, width - 2, height - 2)).insertAll([
            new TVStaticText(new TVRect(2, 1, width - 4, lines.length + 1), lines.join("\n")),
            ...buttons,
        ]));
        this.bindCommonClose(() => this.dismiss("cancel"));
        this.bindDrag();
        this.resolveAction = null;
    }
    show() {
        super.open();
        return new Promise((resolve) => { this.resolveAction = resolve; });
    }
    dismiss(action) {
        const resolve = this.resolveAction;
        this.resolveAction = null;
        super.close();
        resolve?.(action);
    }
    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && ["download-retry", "download-remove", "download-cancel"].includes(event.command)) {
            this.dismiss(event.command.slice(9));
            this.clearEvent(event);
        }
    }
    destroy() { this.dismiss("cancel"); super.destroy(); }
}

class TVDownloadProgress extends TVSubMenu {
    constructor() {
        super("↓", 0, TV_HELP_CONTEXTS.hcDownloads);
        this.status = { active: false, errors: 0, percent: 0, items: [] };
        this.rows = new Map();
        this.completed = new TVSubMenu("Completed downloads (0)", 0, this.helpCtx);
        this.showItem = new TVMenuItem("~S~how Downloads...", "downloads-show", 0, this.helpCtx);
        this.dialog = null;
        this.signature = "";
        this.pollTimer = null;
        this.getMenuView = null;
        this.stopped = false;
        this.requestSerial = 0;
        this.actionPending = false;
    }

    update(status, view) {
        this.status = status;
        const showPercent = status.active || (status.percent > 0 && status.percent < 100);
        this.name = showPercent ? `↓ ${status.percent}%` : "↓";
        const width = Math.max(12, Math.min(64, Math.floor(window.innerWidth / (measureCells().width || 8)) - 18));
        const signature = width + ":" + status.items.map((item) => `${item.id}:${item.state === "done"}`).join("|");
        const changed = signature !== this.signature;
        const items = status.items.map((item) => {
            const marker = item.state === "done" ? "✓" : item.state === "error" ? "!" : item.state === "running" ? "↓" : "·";
            const label = `${item.kind.toUpperCase()}: ${item.label}`;
            const title = `${marker} ${label.length > width ? label.slice(0, width - 1) + "…" : label}`;
            const row = this.rows.get(item.id) || new TVMenuItem("", "", 0, this.helpCtx);
            const wait = /in (\d+)s$/.exec(item.phase || "");
            row.name = title; row.param = item.state === "error" ? "Failed" : wait ? `Wait ${wait[1]}s` : `${item.percent}%`;
            row.command = item.state === "error" ? "downloads-failed" : "";
            this.rows.set(item.id, row);
            return row;
        });
        if (changed) {
            this.signature = signature;
            this.rows = new Map(status.items.map((item, index) => [item.id, items[index]]));
            const completed = items.filter((_item, index) => status.items[index].state === "done");
            const pending = items.filter((_item, index) => status.items[index].state !== "done");
            this.completed.name = `Completed downloads (${completed.length})`;
            this.completed.setDisabled(!completed.length);
            this.completed.subMenu = pageMenu(completed);
            const menu = pageMenu([this.completed, this.showItem, ...(pending.length ? [NewLine(), ...pending] : [])]);
            if (view) { view.setSubMenu(this, menu); } else { this.subMenu = menu; }
        }
        view?.updateItem(this);
        view?.updateItem(this.completed);
        items.forEach((item) => view?.updateItem(item));
        view?.showDownloads();
        view?.layoutSubMenu(this);
        view?.layoutSubMenu(this.completed);
        if (this.dialog && !this.dialog.destroyed) { this.dialog.updateDownloads(status); }
    }

    showDialog(desktop) {
        if (!this.dialog || this.dialog.destroyed) {
            this.dialog = new TVProgressDialog("Downloads", "Preparing downloads...");
            this.dialog.setHelpCtx(this.helpCtx);
            this.dialog.setState(sfModal, false);
            desktop.dialogManager.register("downloads", this.dialog);
        }
        this.dialog.updateDownloads(this.status);
        this.dialog.open();
        return this.dialog;
    }

    async failedItem(control, desktop) {
        if (this.actionPending || !desktop) { return; }
        const id = [...this.rows].find(([_id, row]) => row === control)?.[0];
        const item = this.status.items.find((row) => row.id === id && row.state === "error");
        if (!item) { return; }
        this.actionPending = true;
        const dialog = new TVDownloadActionDialog(item);
        desktop.dialogManager.register("download-action", dialog);
        try {
            const action = await dialog.show();
            if (action === "cancel") { return; }
            await TVLoginDialog.request("/api/downloads/action", "POST", { id, action });
            await this.refresh();
        } catch (error) {
            const box = new TVMessageBox(); desktop.dialogManager.register("download-error", box);
            try { await box.show({ title: "Download", type: TVMessageBox.MF_ERROR, lines: [error.message] }); }
            finally { box.destroy(); }
        } finally {
            dialog.destroy();
            this.actionPending = false;
        }
    }

    start(getMenuView) {
        if (this.getMenuView) { return; }
        this.getMenuView = getMenuView;
        this.stopped = false;
        void this.refresh();
        window.addEventListener("pagehide", () => this.stop());
        window.addEventListener("pageshow", (event) => { if (event.persisted) { this.stopped = false; void this.refresh(); } });
    }

    stop() { this.stopped = true; this.requestSerial += 1; window.clearTimeout(this.pollTimer); }

    async refresh() {
        const serial = ++this.requestSerial;
        window.clearTimeout(this.pollTimer);
        try {
            const response = await fetch("/api/downloads", { cache: "no-store" });
            if (serial !== this.requestSerial) { return; }
            if (response.status === 404) { this.stop(); return; }
            if (!response.ok) { throw new Error("Downloader status unavailable"); }
            const status = await response.json();
            if (serial !== this.requestSerial) { return; }
            if (!this.stopped) { this.update(status, this.getMenuView?.()); }
        } catch { /* A temporary network failure does not stop server work. */ }
        if (!this.stopped && serial === this.requestSerial) { this.pollTimer = window.setTimeout(() => void this.refresh(), this.status.active ? 1000 : 5000); }
    }
}

// Application extension: classic TMenuBar has no right-aligned item option.
class TVApplicationMenuBar extends TVMenuBar {
    constructor(bounds, menu, rightItem, downloadItem = new TVDownloadProgress()) {
        const items = menu.entries();
        items.splice(items.indexOf(rightItem) + 1, 0, downloadItem);
        super(bounds, pageMenu(items));
        this.rightItem = rightItem;
        this.downloadItem = downloadItem;
    }
    _drawItemName(item) {
        return item === this.rightItem && item.subMenu instanceof TVMenu
            ? escapeHtml(item.name) : super._drawItemName(item);
    }
    menuMnemonic(item) {
        return item === this.rightItem && item.subMenu instanceof TVMenu ? "" : super.menuMnemonic(item);
    }
    draw() {
        const left = this.menu.entries().filter((item) => item !== this.rightItem && item !== this.downloadItem);
        return `<nav class="tv-menu-items">${left.map((item) => this.drawItem(item, "bar")).join("")}`
            + `<div class="tv-menu-right">${this.drawItem(this.rightItem, "bar")}${this.drawItem(this.downloadItem, "bar")}</div></nav>`;
    }
    bindRoot(root) {
        super.bindRoot(root);
        this.downloadItem.update(this.downloadItem.status, this);
        this.showDownloads();
        return this;
    }
    showDownloads() {
        const root = this.rootByItem.get(this.downloadItem);
        if (!root) { return; }
        // Finished rows remain accessible through the Completed downloads submenu.
        root.hidden = !this.downloadItem.status.items.length && !this.downloadItem.status.active
            && !this.downloadItem.status.errors && this.activeRoot !== root;
        this.menuRoots = this.menuRoots.filter((item) => !item.hidden);
        if (!root.hidden && !this.menuRoots.includes(root)) { this.menuRoots.push(root); }
    }
    refresh() { super.refresh(); if (this.downloadItem) { this.showDownloads(); } }
}

function buildAccountMenu(session) {
    if (!session?.authenticated || !session.user) { return new TVMenuItem("~L~ogin", "account-login", 0, hcAccount); }
    const user = session.user;
    const admin = user.role === "admin";
    return pageSubMenu(String(user.display_name || user.username), [
        new TVMenuItem("~A~ccount", "account-profile", 0, hcAccount),
        pageSubMenu("~C~onfiguration", [
            ...(admin ? [
                new TVMenuItem("~S~erver Configuration", "account-server-configuration", 0, hcServerConfiguration),
                new TVMenuItem("~H~ELP Packages...", "account-help-packages", 0, hcHelpPackages),
                new TVMenuItem("~D~OS Packages...", "account-dos-packages", 0, hcDosPackages),
                new TVMenuItem("~M~IDI Sources...", "account-midi-sources", 0, hcMidiSources),
                new TVMenuItem("~U~sers", "account-users", 0, hcUsers),
                new TVMenuItem("~R~egistration Token", "account-registration-token", 0, hcRegistrationTokens),
                NewLine(),
            ] : []),
            new TVMenuItem("~C~olors", "account-colors", 0, hcColors),
            pageSubMenu("~T~heme", [
                new TVMenuItem("~L~ight", "theme-light"),
                new TVMenuItem("~D~ark", "theme-dark"),
                new TVMenuItem("~A~uto", "theme-auto"),
            ], hcColors),
            ...(admin ? [
                NewLine(),
                new TVMenuItem("Re~b~uild DOS C...", "account-rebuild-dos", 0, hcServerConfiguration),
                new TVMenuItem("Rebuild M~I~DI...", "account-rebuild-midi", 0, hcServerConfiguration),
            ] : []),
        ], admin ? hcServerConfiguration : hcColors),
        NewLine(),
        new TVMenuItem("Sign ~O~ut", "account-logout"),
    ], hcAccount);
}

function buildPageMenuBar(root, context, session = null, downloadProgress = root._tvMenuView?.downloadItem) {
    const dialog = (name, title) => pageMenuItem(title, "dialog-open", name);
    const savers = [
        pageMenuItem("~S~tars", "saver-start", "stars"),
        pageMenuItem("~B~ounce", "saver-start", "bounce"),
        pageMenuItem("Cloc~k~", "saver-start", "clock"),
        pageMenuItem("~M~atrix", "saver-start", "matrix"),
        pageMenuItem("~P~rojector", "saver-start", "projector"),
    ];
    const system = [
        new TVMenuItem("~C~ontext Help", "context-help"),
        NewLine(),
        dialog("about", "~A~bout"),
        dialog("puzzle", "~P~uzzle"),
        dialog("hanoi", "Tower of ~H~anoi"),
        dialog("tron", "Tr~o~n Light Cycles"),
        dialog("calendar", "Ca~l~endar"),
        dialog("ascii", "Ascii ~T~able"),
        dialog("calc", "~C~alculator"),
        dialog("midi", "~M~IDI Player"),
        ...(!session?.authenticated ? [dialog("colors", "C~o~lors")] : []),
        dialog("widgets", "~W~idget Gallery"),
        dialog("grid", "~G~rid Viewer"),
        dialog("systeminfo", "System ~I~nformation"),
        NewLine(),
        pageSubMenu("~S~creen saver", savers, hcSystemMenu),
        ...(!session?.authenticated ? [
            NewLine(),
            new TVMenuItem("~L~ight Theme", "theme-light"),
            new TVMenuItem("~D~ark Theme", "theme-dark"),
            new TVMenuItem("A~u~to Theme", "theme-auto"),
        ] : []),
    ];
    const top = [
        pageSubMenu("~≡~", system, hcSystemMenu),
        pageMenuItem("~H~elp", "page-open", context.helpHref),
        pageMenuItem("~I~ndex", "page-open", context.indexHref),
    ];
    if (context.pageKind === "topic" && context.topicContext && context.topicHref) {
        top.push(pageMenuItem(`~T~opic ${context.topicContext}`, "page-open", context.topicHref));
    }
    const accountItem = buildAccountMenu(session);
    top.push(accountItem);
    const menuBar = new TVApplicationMenuBar(new TVRect(), pageMenu(top), accountItem, downloadProgress);
    root.innerHTML = menuBar.draw()
        + '<div class="tv-menu-clock" data-tv-clock>00:00:00</div>';
    menuBar.bindRoot(root);
    return menuBar;
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
        this.bindItems();
    }
}

function buildAppChrome() {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    const statusLine = document.querySelector("[data-tv-status-line]");
    const context = new TVAppContext();

    if (menuBar) {
        buildPageMenuBar(menuBar, context);
    }

    if (statusLine) {
        new TVPageStatusLine(new TVRect(), context).bindRoot(statusLine).render();
    }
}

class TurboVisionWindowResizer {
    constructor(windowElement, identity = "") {
        this.windowElement = windowElement;
        windowElement._tvResizer = this;
        this.identity = identity;
        this.desktop = windowElement.closest(".tv-desktop");
        this.moveHandle = windowElement.querySelector("[data-tv-move-handle]");
        this.handle = windowElement.querySelector("[data-tv-resize-handle]");
        this.dragState = null;
        this.moveState = null;
        this.moveFrame = null;
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
        return this.identity ? `thelp:window:${path}:${this.identity}` : `thelp:window:${path}`;
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
            maxLeft: this.desktop ? Math.max(0, this.desktop.clientWidth - this.windowElement.offsetWidth) : Infinity,
            maxTop: this.desktop ? Math.max(0, this.desktop.clientHeight - this.windowElement.offsetHeight) : Infinity,
        };
        this.setMoveFrame(true);
        document.addEventListener("mousemove", this.onMoveDrag);
        document.addEventListener("mouseup", this.onMoveEnd);
    }

    setResizeFrame(active) {
        this.windowElement.classList.toggle("is-resizing", active);
        this.setWindowFrame();
    }

    setMoveFrame(active) {
        if (this.windowElement.classList.contains("is-resizing")) {
            return;
        }
        this.windowElement.classList.toggle("is-moving", active);
        this.setWindowFrame();
    }

    setWindowFrame() {
        updateWindowFrameState(this.windowElement, !this.windowElement.classList.contains("is-window-inactive"));
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

    place(geometry) {
        this.windowElement.classList.remove("is-maximized");
        this.applyGeometry(geometry);
        const zoomGlyph = this.windowElement.querySelector("[data-tv-zoom-glyph]");
        if (zoomGlyph) { zoomGlyph.textContent = "↑"; }
        this.restoreSnapshot = this.captureGeometry();
        this.persistState();
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
        this.windowElement.classList.remove("is-maximized");
        this.restoreSnapshot = restore || current;
        this.applyGeometry(this.restoreSnapshot);
        this.enforceMinimumSize();
        if (this.desktop) {
            const geometry = this.captureGeometry();
            geometry.left = this.clamp(geometry.left, 0, Math.max(0, this.desktop.clientWidth - this.windowElement.offsetWidth));
            geometry.top = this.clamp(geometry.top, 0, Math.max(0, this.desktop.clientHeight - this.windowElement.offsetHeight));
            this.restoreSnapshot = geometry;
            this.applyGeometry(geometry);
        }
        if (state.maximized) {
            this.maximize(false);
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

    toggle() {
        if (this.windowElement.classList.contains("is-maximized")) {
            this.restore();
        } else {
            this.maximize();
        }
    }

    toggleMaximize(event) {
        if (event.target.closest(".tv-close-control")) { return; }
        this.toggle();
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
        const rawLeft = this.moveState.startLeft + (event.clientX - this.moveState.startX);
        const rawTop = this.moveState.startTop + (event.clientY - this.moveState.startY);
        this.moveState.nextLeft = this.clamp(rawLeft, 0, this.moveState.maxLeft);
        this.moveState.nextTop = this.clamp(rawTop, 0, this.moveState.maxTop);
        if (this.moveFrame === null) {
            this.moveFrame = window.requestAnimationFrame(this.applyMove);
        }
    };

    applyMove = () => {
        this.moveFrame = null;
        if (!this.moveState || this.moveState.nextLeft === undefined) { return; }
        this.windowElement.style.setProperty("--tv-window-left", `${this.moveState.nextLeft}px`);
        this.windowElement.style.setProperty("--tv-window-top", `${this.moveState.nextTop}px`);
    };

    onMoveEnd = (event) => {
        if (this.moveState && Number.isFinite(event?.clientX) && Number.isFinite(event?.clientY)) {
            this.onMoveDrag(event);
        }
        if (this.moveFrame !== null) { window.cancelAnimationFrame(this.moveFrame); }
        this.applyMove();
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
        if (this.moveFrame !== null) { window.cancelAnimationFrame(this.moveFrame); this.moveFrame = null; }
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
        if (this.windowElement._tvResizer === this) { delete this.windowElement._tvResizer; }
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
        this.isAdmin = false;
        this.authSession = null;
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evKeyDown) {
            const keyEvent = event.nativeEvent;
            const activeDialog = this.dialogManager?.get(this.dialogManager.activeTarget);
            // Child input has already traversed its owner chain; never dispatch it back.
            if (activeDialog?.isOpen() && event.infoPtr === this) {
                activeDialog.handleEvent(new TVEvent(evKeyDown, {
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
        const action = control instanceof TVMenuItem ? (pageMenuActions.get(control) || {}) : {};
        const value = action.value ?? (control instanceof TVStatusItem
            ? (control.param && typeof control.param === "object" ? control.param.value : control.param)
            : "") ?? "";
        let handled = true;
        if (event.command === "downloads-show") {
            this.downloadProgress?.showDialog(this.desktopView);
        } else if (event.command === "downloads-failed") {
            void this.downloadProgress?.failedItem(control, this.desktopView);
        } else if (event.command === "account-logout") {
            this.dialogManager.open("login");
            this.dialogManager.get("login")?.handleEvent(new TVEvent(evCommand, { command: "login-sign-out" }));
        } else if (String(event.command).startsWith("account-")) {
            if (["account-rebuild-dos", "account-rebuild-midi"].includes(event.command)) {
                if (this.isAdmin) {
                    this.serverConfigDialog?.handleEvent(new TVEvent(evCommand, {
                        command: event.command.replace("account-", "server-"),
                    }));
                }
                this.clearEvent(event); return;
            }
            const name = event.command === "account-login" ? "login"
                : event.command === "account-profile" ? "account" : event.command.slice(8);
            if (["server-configuration", "help-packages", "dos-packages", "midi-sources", "registration-token", "users", "add-user"].includes(name) && !this.isAdmin) { this.clearEvent(event); return; }
            this.dialogManager.open(name);
        } else if (event.command === "dialog-open") {
            this.dialogManager.open(value);
        } else if (["theme-light", "theme-dark", "theme-auto"].includes(event.command)) {
            applyThemeAndSyncPalette(event.command.slice(6), true);
            this.dialogManager.applyActiveStates();
            fillBorders();
        } else if (event.command === "context-help") {
            this.helpController?.request();
        } else if (event.command === "saver-start") {
            const Saver = TVScreenSaver?.modes?.[value];
            if (Saver) { new Saver().start(); }
        } else if (event.command === "page-open") {
            window.location.href = value;
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
            this.desktopView.insert(helpWindow);
            bindCloseButtons(root);

            const frame = root.querySelector("[data-tv-scroll-frame]");
            const scrollbar = frame ? new TVScrollBar(new TVRect()).bindRoot(frame) : null;
            const resizer = new TurboVisionWindowResizer(root, name);
            if (scrollbar) { this.scrollbars.push(scrollbar); }
            this.resizers.push(resizer);

            const close = () => {
                helpWindow.hide();
                this.dialogManager.unregisterWindow(name);
                fillBorders(root);
            };
            const zoom = () => helpWindow.zoom();
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
    }

    _setAuthSession(session) {
        const nextAdmin = Boolean(session?.authenticated && session.user?.role === "admin");
        if (!nextAdmin) {
            for (const name of ["help-packages", "dos-packages", "midi-sources"]) { this.dialogManager?.get(name)?.close(); }
            this.dialogManager?.get("downloads")?.close();
            this.dialogManager?.get("midi-source-progress")?.close();
        }
        if (!session?.authenticated) { this.dialogManager?.get("account")?.close(); }
        if (!nextAdmin) { this.serverConfigDialog?.close(); this.dialogManager?.get("registration-token")?.close(); this.dialogManager?.get("users")?.close(); this.dialogManager?.get("add-user")?.close(); }
        const nextSession = session?.authenticated && session.user ? session : null;
        if (JSON.stringify(nextSession) === JSON.stringify(this.authSession)) { return; }
        this.authSession = nextSession;
        this.isAdmin = nextAdmin;
        if (nextAdmin) { void this.helpPackagesDialog?.checkFirstRun(); }
        const menuBar = document.querySelector("[data-tv-menu-bar]");
        if (menuBar) {
            buildPageMenuBar(menuBar, new TVAppContext(), this.authSession, this.downloadProgress);
            this.menus?.refresh();
            void this.downloadProgress?.refresh();
        }
    }

    async _refreshAuthSession() {
        try {
            const response = await fetch("/api/auth/session", { cache: "no-store" });
            if (response.ok) { this._setAuthSession(await response.json()); }
        } catch { /* Standalone generated pages can run without the account API. */ }
    }

    initShellWidgets() {
        const desktop = document.querySelector(".tv-desktop") || document.body;
        const hostWindow = document.querySelector("[data-tv-window]");
        this.desktopView = new TVDesktop(new TVRect()).bindRoot(desktop);
        this.insert(this.desktopView);
        this.dialogManager = this.desktopView.dialogManager;
        setElementHelpContext(hostWindow, hcHelpViewer);
        const hostView = hostWindow
            ? new TVWindow(new TVRect(), document.title).bindRoot(hostWindow)
            : null;
        if (hostView) {
            this.desktopView.insert(hostView);
            hostView.closeAction = () => window.location.assign(hostView.closeControl.href);
            hostView.zoomAction = () => hostView.zoom();
        }
        this.scrollbars = Array.from(
            document.querySelectorAll("[data-tv-scroll-frame]"),
            (frame) => new TVScrollBar(new TVRect()).bindRoot(frame),
        );
        this.resizers = Array.from(document.querySelectorAll("[data-tv-window]"), (windowElement) => new TurboVisionWindowResizer(windowElement));
        this.dialogManager.setHostWindow(hostWindow, hostWindow ? {
            [TV_COMMANDS.CLOSE]: () => hostView.dispatchEvent(new TVEvent(evCommand, {
                command: "window-close", infoPtr: hostView,
            })),
            [TV_COMMANDS.ZOOM]: () => hostView.dispatchEvent(new TVEvent(evCommand, {
                command: "window-zoom", infoPtr: hostView,
            })),
        } : {});
        this.menus = new TurboVisionMenus(this.dialogManager);
        this.menus.commandTarget = this;
        this.downloadProgress = this.menus.menuView?.downloadItem;
        this.downloadProgress?.start(() => this.menus.menuView);
        if (hostWindow && this.boundHostWindow !== hostWindow) {
            this.boundHostWindow = hostWindow;
            hostWindow.addEventListener("mousedown", (event) => {
                if (event.target.closest(".tv-close-control, .tv-grow-handle, .tv-menu-bar, .tv-status-line")) {
                    return;
                }
                this.dialogManager.activateHostWindow();
            });
        }
        this.registerDialog("about", () => new TVAboutDialog());
        const loginDialog = this.registerDialog("login", () => new TVLoginDialog());
        const accountDialog = this.registerDialog("account", () => new TVAccountDialog());
        accountDialog.onSessionChange = (session) => this._setAuthSession(session);
        const usersDialog = this.registerDialog("users", () => new TVUsersDialog());
        usersDialog.onSessionChange = (session) => this._setAuthSession(session);
        const addUserDialog = this.registerDialog("add-user", () => new TVAddUserDialog());
        addUserDialog.onCreated = (user) => { void usersDialog.refreshUsers(user.id); };
        const registrationDialog = this.registerDialog("registration", () => new TVRegistrationDialog());
        this.registerDialog("registration-token", () => new TVRegistrationTokenDialog());
        this.serverConfigDialog = this.registerDialog("server-configuration", () => new TVServerConfigurationDialog());
        this.helpPackagesDialog = this.registerDialog("help-packages", () => new TVHelpPackagesDialog());
        this.registerDialog("dos-packages", () => new TVDosPackagesDialog());
        this.midiSourcesDialog = this.registerDialog("midi-sources", () => new TVMidiSourcesDialog());
        this.midiSourcesDialog.onMidiApplied = () => {
            const player = this.dialogManager.get("midi");
            player?.stopPlayback();
            if (player) { player.pendingPlay = null; void player.refreshCatalog(); }
        };
        this.serverConfigDialog.onBeforeRebuild = (resource) => {
            if (resource === "midi") {
                const player = this.dialogManager.get("midi");
                player?.stopPlayback();
                if (player) { player.pendingPlay = null; }
            }
        };
        loginDialog.onRegister = () => this.dialogManager.open("registration");
        loginDialog.onSessionChange = (session) => this._setAuthSession(session);
        registrationDialog.onSessionChange = (session) => loginDialog.updateSession(session);
        registrationDialog.onConfirmed = () => loginDialog.close();
        void this._refreshAuthSession();
        this.registerDialog("puzzle", () => new TVPuzzleDialog());
        this.registerDialog("hanoi", () => new TVHanoiDialog());
        this.registerDialog("tron", () => new TVTronDialog());
        this.registerDialog("calendar", () => new TVCalendarDialog());
        this.registerDialog("ascii", () => new TVAsciiTableDialog());
        this.registerDialog("calc", () => new TVCalculatorDialog());
        this.registerDialog("midi", () => new TVMidiPlayerDialog());
        this.registerDialog("colors", () => new TVColorsDialog());
        this.registerDialog("widgets", () => new TVViewGalleryDialog());
        this.registerDialog("grid", () => new TVGridDemoDialog());
        this.registerDialog("systeminfo", () => new TVSystemInformationDialog());
        this.searchDialog = this.registerDialog("search", () => new TVSearchDialog());
        void this.searchDialog?.monitorIndex();
        this.initContextHelpWindow();
        this.helpController = new TVHelpController({
            getMenuController: () => this.menus,
            getDialogManager: () => this.dialogManager,
            onHelp: (helpCtx) => this.contextHelpWindow?.openContext(helpCtx),
        });
        this.dialogManager.applyActiveStates();
        if (TVScreenSaver) { TVScreenSaver.installIdleStart(); }
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
    TVDownloadProgress,
    TVApplicationMenuBar,
    buildAccountMenu,
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
