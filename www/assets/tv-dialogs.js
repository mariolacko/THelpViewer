// Turbo Vision dialogs for generated help pages.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    renderHotkeyMarkup,
    displayCp437Char,
    cloneColorPalette,
    setColorPaletteAttribute,
    buildDefaultColorPalette,
    applyColorPalette,
    dosColor,
    DOS_COLORS,
    COLOR_GROUPS,
    TVDialog,
    TVStaticText,
    TVLabel,
    TVInputLine,
    TVGroup,
    TVMarkupList,
    TVListViewer,
    TVListBox,
    TVVerticalListViewer,
    TVInfoBox,
    TVButtonStrip,
    TVCheckBoxes,
    TVRadioButtons,
    TVButton,
    TVMessageBox,
    normalizeSearchText,
    fillBorders,
    MONTH_NAMES,
    DAYS_IN_MONTH,
    isLeapYear,
    dayOfWeek,
} = TV;

class TVAboutDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const body = document.body;
        const siteName = body.dataset.tvSiteName || "THelpViewer";
        const generatorVersion = body.dataset.tvGeneratorVersion || "unknown";
        const generatorAuthors = body.dataset.tvAuthors || "Mario Lacko + Copilot + Codex";
        const aboutMain = new TVGroup({
            w: 28, h: 14,
            children: [
                new TVStaticText({ x: 0, y: 1, w: 28, align: "center", title: true, text: siteName }),
                new TVStaticText({ x: 0, y: 3, w: 28, align: "center", text: `Version ${generatorVersion}` }),
                new TVStaticText({ x: 0, y: 5, w: 28, align: "center", text: "Copyright (c) 2026" }),
                new TVStaticText({ x: 0, y: 7, w: 28, align: "center", text: generatorAuthors }),
                new TVButton({ x: 9, y: 9, w: 10, className: "is-default", attrs: { "data-tv-about-ok": true }, label: '~O~K' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "About",
            title: "About",
            closeAttrs: {
                "data-tv-about-close": true,
                "aria-label": "Close about dialog",
            },
            bodyMarkup: aboutMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "32ch",
            height: "min(13em, calc(100% - 2em))",
        });
        this.okButton = this.query("[data-tv-about-ok]");
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        if (this.okButton) {
            this.okButton.addEventListener("click", () => this.close());
        }
    }
}

class TVWidgetGalleryDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const nameLabel = new TVLabel({
            text: "~N~ame:",
            hotkey: true,
            forId: "tv-widget-gallery-name",
        });
        const nameInput = new TVInputLine({
            attrs: {
                id: "tv-widget-gallery-name",
                value: "Turbo Vision",
                autocomplete: "off",
                "data-tv-gallery-name": true,
            },
        });
        const checks = new TVCheckBoxes({
            attrs: { "data-tv-gallery-checks": true },
            options: [
                { label: "~F~rames", value: "frames", checked: true },
                { label: "~S~hadows", value: "shadows", checked: true },
                { label: "D~i~sabled", value: "disabled", disabled: true },
            ],
        });
        const radios = new TVRadioButtons({
            attrs: { "data-tv-gallery-radios": true },
            name: "tv-widget-gallery-mode",
            options: [
                { label: "~T~ext", value: "text", checked: true },
                { label: "~G~raphics", value: "graphics" },
                { label: "~M~ono", value: "mono", disabled: true },
            ],
        });
        const staticText = new TVStaticText({
            text: "Static text · label hotkeys · disabled states",
            attrs: { "data-tv-gallery-static": true },
        });
        const infoBox = new TVInfoBox({
            title: "Event log",
            name: "gallery-status",
            w: 30,
            children: [
                new TVStaticText({ tag: "span", name: "status", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const buttons = new TVButtonStrip({
            className: "tv-widget-gallery-buttons",
            buttons: [
                new TVButton({
                    className: "is-default",
                    attrs: { "data-tv-gallery-ok": true },
                    label: "~O~K",
                }),
                new TVButton({
                    attrs: { "data-tv-gallery-apply": true },
                    label: "~A~pply",
                }),
                new TVButton({
                    attrs: { "data-tv-gallery-message": true },
                    label: "~M~essage",
                }),
                new TVButton({
                    attrs: { disabled: true },
                    label: "Disabled",
                }),
            ],
        });

        super({
            desktop,
            ariaLabel: "Widget Gallery",
            title: "Widget Gallery",
            bodyClass: "tv-widget-gallery-body",
            closeAttrs: {
                "data-tv-gallery-close": true,
                "aria-label": "Close widget gallery",
            },
            bodyMarkup: `
                <div class="tv-widget-gallery-main">
                    <div class="tv-widget-gallery-field">
                        ${nameLabel.renderMarkup()}
                        ${nameInput.renderMarkup()}
                    </div>
                    <div class="tv-widget-gallery-samples">
                        <section class="tv-widget-gallery-panel">
                            <div class="tv-widget-gallery-heading">Check boxes</div>
                            ${checks.renderMarkup()}
                        </section>
                        <section class="tv-widget-gallery-panel">
                            <div class="tv-widget-gallery-heading">Radio buttons</div>
                            ${radios.renderMarkup()}
                        </section>
                        <section class="tv-widget-gallery-panel">
                            <div class="tv-widget-gallery-heading">List viewer</div>
                            ${TVVerticalListViewer.renderMarkup({
                                rootClass: "tv-widget-gallery-listviewer",
                                rootAttrs: { "data-tv-gallery-list": true },
                                viewportClass: "tv-widget-gallery-list",
                            })}
                        </section>
                        <section class="tv-widget-gallery-panel tv-widget-gallery-info">
                            <div class="tv-widget-gallery-heading">Info box</div>
                            ${infoBox.renderMarkup()}
                        </section>
                        <section class="tv-widget-gallery-panel tv-widget-gallery-static">
                            <div class="tv-widget-gallery-heading">Static text</div>
                            ${staticText.renderMarkup()}
                        </section>
                    </div>
                    ${buttons.renderMarkup()}
                </div>
            `,
            footerMarkup: TVDialog.footerMarkup(),
            width: "68ch",
            height: "min(23em, calc(100% - 2em))",
            left: "3ch",
            top: "2em",
        });
        this.nameInput = this.query("[data-tv-gallery-name]");
        this.checks = this.query("[data-tv-gallery-checks]");
        this.radios = this.query("[data-tv-gallery-radios]");
        this.okButton = this.query("[data-tv-gallery-ok]");
        this.applyButton = this.query("[data-tv-gallery-apply]");
        this.messageButton = this.query("[data-tv-gallery-message]");
        this.infoBox = infoBox.resolve(this.dialog);
        this.messageBox = null;
        this.listBox = new TVVerticalListViewer(this.query("[data-tv-gallery-list]"), {
            itemClassName: "tv-widget-gallery-list-item",
            itemAttrName: "data-tv-gallery-list-index",
        });
        this.listBox.setItems([
            "TDialog",
            "TInputLine",
            "TListViewer",
            "TButton",
            "TScrollBar",
            "TCheckBoxes",
            "TRadioButtons",
            "TStaticText",
            "TLabel",
            "TMessageBox",
        ], 0);
        this.listBox.bind({
            onSelect: (item) => this.setStatus(`Selected: ${item}`),
            onActivate: (item) => this.setStatus(`Activated: ${item}`),
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindGallery();
        this.setStatus("Ready");
    }

    bindGallery() {
        if (this.nameInput) {
            this.nameInput.addEventListener("input", () => this.setStatus(`Name: ${this.nameInput.value || "(empty)"}`));
        }
        for (const group of [this.checks, this.radios]) {
            group?.addEventListener("change", (event) => {
                const input = event.target.closest("input");
                if (input) { this.setStatus(`${input.value}: ${input.checked ? "on" : "off"}`); }
            });
        }
        if (this.applyButton) {
            this.applyButton.addEventListener("click", () => this.setStatus("Apply command"));
        }
        if (this.messageButton) {
            this.messageButton.addEventListener("click", async () => {
                if (!this.messageBox) {
                    this.messageBox = new TVMessageBox(this.desktop);
                }
                const command = await this.messageBox.show({
                    type: TVMessageBox.MF_INFORMATION,
                    lines: ["Turbo Vision message box"],
                    buttons: TVMessageBox.MF_OK_CANCEL,
                });
                this.setStatus(`Message: ${command}`);
            });
        }
        if (this.okButton) {
            this.okButton.addEventListener("click", () => this.close());
        }
    }

    open() {
        super.open();
        window.requestAnimationFrame(() => this.listBox.updateScrollbar());
    }

    setStatus(message) {
        this.infoBox.updateRow("status", message);
    }
}

class TVFileListBox extends TVListBox {
    constructor(root = null, options = {}) {
        super(root, options);
        this.rows = 8;
        this.onViewportChange = null;
    }

    select(index, options = {}) {
        super.select(index, options);
        if (this.onViewportChange) { this.onViewportChange(); }
    }

    firstColumn() {
        if (!this.root || !this.root.clientWidth) { return 0; }
        const columnWidth = this.root.clientWidth / 2;
        return Math.max(0, Math.round(this.root.scrollLeft / columnWidth));
    }

    scrollColumns(delta) {
        if (!this.root || !this.items.length) { return; }
        const columns = Math.ceil(this.items.length / this.rows);
        const maxColumn = Math.max(0, columns - 2);
        const nextColumn = Math.min(maxColumn, Math.max(0, this.firstColumn() + delta));
        this.root.scrollLeft = nextColumn * (this.root.clientWidth / 2);
        if (this.onViewportChange) { this.onViewportChange(); }
    }

    ensureSelectionVisible() {
        if (!this.root || this.selectedIndex < 0) { return; }
        const column = Math.floor(this.selectedIndex / this.rows);
        const firstColumn = this.firstColumn();
        if (column < firstColumn) {
            this.scrollColumns(column - firstColumn);
        } else if (column > firstColumn + 1) {
            this.scrollColumns(column - firstColumn - 1);
        }
    }

    onKeyDown(event) {
        const current = this.resolveIndex(event.target);
        if (current < 0 || !this.items.length) { return; }
        let next = current;
        if (event.key === "ArrowDown") {
            next = Math.min(this.items.length - 1, current + 1);
        } else if (event.key === "ArrowUp") {
            next = Math.max(0, current - 1);
        } else if (event.key === "ArrowRight") {
            next = Math.min(this.items.length - 1, current + this.rows);
        } else if (event.key === "ArrowLeft") {
            next = Math.max(0, current - this.rows);
        } else if (event.key === "PageDown") {
            next = Math.min(this.items.length - 1, current + this.rows * 2);
        } else if (event.key === "PageUp") {
            next = Math.max(0, current - this.rows * 2);
        } else if (event.key === "Home") {
            next = 0;
        } else if (event.key === "End") {
            next = this.items.length - 1;
        } else if (event.key === "Enter") {
            event.preventDefault();
            event.stopPropagation();
            this.select(current);
            this.activateHandler?.(this.items[current], current, event);
            return;
        } else if (event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            this.select(current);
            this.selectHandler?.(this.items[current], current, event);
            return;
        } else {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.select(next);
        this.selectedElement()?.focus();
        if (next !== current) {
            this.selectHandler?.(this.items[next], next, event);
        }
    }
}

class TVFileOpenDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const nameLabel = new TVLabel({
            text: "~N~ame",
            hotkey: true,
            forId: "tv-file-open-name",
        });
        const nameInput = new TVInputLine({
            attrs: {
                id: "tv-file-open-name",
                value: "*.*",
                autocomplete: "off",
                spellcheck: "false",
                "data-tv-file-open-name": true,
            },
        });
        const filesLabel = new TVLabel({ text: "~F~iles", hotkey: true });
        const openButton = new TVButton({
            className: "is-default",
            attrs: { "data-tv-file-open-confirm": true },
            label: "~O~pen",
        });
        const cancelButton = new TVButton({
            attrs: { "data-tv-file-open-cancel": true },
            label: "Cancel",
        });

        super({
            desktop,
            ariaLabel: "Open a File",
            title: "Open a File",
            bodyClass: "tv-file-open-body",
            closeAttrs: {
                "data-tv-file-open-close": true,
                "aria-label": "Close file open dialog",
            },
            bodyMarkup: `
                <div class="tv-file-open-main">
                    <div class="tv-file-open-name-label">${nameLabel.renderMarkup()}</div>
                    <div class="tv-file-open-name-input">${nameInput.renderMarkup()}</div>
                    <button type="button" class="tv-file-open-history-button" data-tv-file-open-history
                            aria-label="History" disabled>▐<span class="tv-hotkey">↓</span>▌</button>
                    <div class="tv-file-open-files-label">${filesLabel.renderMarkup()}</div>
                    <div class="tv-file-open-file-list" data-tv-file-open-files></div>
                    <div class="tv-file-open-hscroll" data-tv-file-open-hscroll aria-hidden="true">
                        <button type="button" data-tv-file-open-scroll-left tabindex="-1">${escapeHtml(displayCp437Char(17))}</button>
                        <span data-tv-file-open-scroll-track></span>
                        <button type="button" data-tv-file-open-scroll-right tabindex="-1">${escapeHtml(displayCp437Char(16))}</button>
                    </div>
                    <div class="tv-file-open-open-button">${openButton.renderMarkup()}</div>
                    <div class="tv-file-open-cancel-button">${cancelButton.renderMarkup()}</div>
                    <div class="tv-file-open-info">
                        <div data-tv-file-open-path></div>
                        <div data-tv-file-open-detail></div>
                    </div>
                    <div class="tv-file-open-history-popup" data-tv-file-open-history-popup hidden>
                        ${TVVerticalListViewer.renderMarkup({
                            rootClass: "tv-file-open-history-listviewer",
                            rootAttrs: { "data-tv-file-open-history-list": true },
                            viewportClass: "tv-file-open-history-list",
                        })}
                    </div>
                </div>
            `,
            footerMarkup: TVDialog.footerMarkup(),
            width: "49ch",
            height: "19em",
            modal: true,
        });
        this.entries = [];
        this.configured = false;
        this.currentDirectory = "";
        this.currentItems = [];
        this.onOpen = null;
        this.storageKey = "thelp:file-open-history";
        this.nameInput = this.query("[data-tv-file-open-name]");
        this.pathLabel = this.query("[data-tv-file-open-path]");
        this.detailLabel = this.query("[data-tv-file-open-detail]");
        this.openButton = this.query("[data-tv-file-open-confirm]");
        this.cancelButton = this.query("[data-tv-file-open-cancel]");
        this.historyButton = this.query("[data-tv-file-open-history]");
        this.historyPopup = this.query("[data-tv-file-open-history-popup]");
        this.scrollTrack = this.query("[data-tv-file-open-scroll-track]");
        this.fileList = new TVFileListBox(this.query("[data-tv-file-open-files]"), {
            itemClassName: "tv-file-open-list-item",
            itemAttrName: "data-tv-file-open-file-index",
            renderItemContent: (item) => escapeHtml(item.label),
        });
        this.fileList.onViewportChange = () => this.updateHorizontalScrollbar();
        this.historyList = new TVVerticalListViewer(this.query("[data-tv-file-open-history-list]"), {
            itemClassName: "tv-file-open-history-item",
            itemAttrName: "data-tv-file-open-history-index",
            renderItemContent: (entry) => escapeHtml(entry.virtualPath),
        });
        this.fileList.bind({
            onSelect: (item) => this.selectItem(item),
            onActivate: (item) => this.activateItem(item),
        });
        this.historyList.bind({
            onSelect: (entry) => this.selectHistory(entry),
            onActivate: (entry) => this.selectHistory(entry, true),
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindFileOpen();
    }

    configure(entries = [], onOpen = null) {
        this.entries = entries.map((entry) => {
            const kind = entry.kind === "doc" ? "doc" : "help";
            const root = kind === "doc" ? "DOCS" : "HELP";
            const group = String(entry.group || "").replace(/[\\/]+/g, "\\");
            const directory = group ? `${root}\\${group}` : root;
            const fileName = String(entry.fileName || entry.name || entry.file || "").split(/[\\/]/).pop();
            return {
                ...entry,
                kind,
                directory,
                fileName,
                virtualPath: `${directory}\\${fileName}`,
                historyKey: `${kind}:${entry.file}`,
            };
        }).filter((entry) => entry.file && entry.fileName);
        this.configured = true;
        this.onOpen = typeof onOpen === "function" ? onOpen : null;
        if (!this.directoryExists(this.currentDirectory)) {
            this.currentDirectory = "";
        }
        this.refresh();
    }

    bindFileOpen() {
        this.openButton?.addEventListener("click", () => this.openSelected());
        this.cancelButton?.addEventListener("click", () => this.close());
        this.historyButton?.addEventListener("click", () => this.toggleHistory());
        this.query("[data-tv-file-open-scroll-left]")?.addEventListener("mousedown", (event) => {
            event.preventDefault();
            this.fileList.scrollColumns(-1);
        });
        this.query("[data-tv-file-open-scroll-right]")?.addEventListener("mousedown", (event) => {
            event.preventDefault();
            this.fileList.scrollColumns(1);
        });
        this.nameInput?.addEventListener("input", () => this.selectNameMatch());
        this.dialog.addEventListener("keydown", (event) => {
            if (!event.altKey || event.ctrlKey || event.metaKey) { return; }
            const key = event.key.toLowerCase();
            if (key === "n" && this.nameInput) {
                event.preventDefault();
                this.nameInput.focus();
                this.nameInput.select();
            } else if (key === "f") {
                event.preventDefault();
                this.fileList.selectedElement()?.focus();
            } else if (key === "o") {
                event.preventDefault();
                this.openSelected();
            }
        });
    }

    open() {
        this.refresh();
        super.open();
        window.requestAnimationFrame(() => {
            this.updateHorizontalScrollbar();
            this.nameInput?.focus();
            this.nameInput?.select();
        });
    }

    close() {
        this.hideHistory();
        super.close();
    }

    onDialogKeyDown(event) {
        if (event.key === "Escape" && this.historyPopup && !this.historyPopup.hidden) {
            event.preventDefault();
            event.stopPropagation();
            this.hideHistory();
            this.historyButton?.focus();
            return;
        }
        super.onDialogKeyDown(event);
    }

    directoryExists(path) {
        if (!path) { return true; }
        return this.entries.some((entry) => (
            entry.directory === path || entry.directory.startsWith(`${path}\\`)
        ));
    }

    parentDirectory(path) {
        const parts = String(path || "").split("\\").filter(Boolean);
        parts.pop();
        return parts.join("\\");
    }

    buildItems() {
        if (!this.configured) {
            return [{ type: "status", label: "Loading HELP/DOCS..." }];
        }
        if (!this.entries.length) {
            return [{ type: "status", label: "No HELP or DOCS files" }];
        }
        const prefix = this.currentDirectory ? `${this.currentDirectory}\\` : "";
        const directories = new Map();
        const files = [];
        for (const entry of this.entries) {
            if (entry.directory === this.currentDirectory) {
                files.push({ type: "file", label: entry.fileName, entry });
                continue;
            }
            if (!entry.directory.startsWith(prefix)) { continue; }
            const rest = entry.directory.slice(prefix.length);
            const child = rest.split("\\")[0];
            if (!child) { continue; }
            const path = prefix + child;
            directories.set(path, {
                type: "directory",
                label: `${child}\\`,
                path,
            });
        }
        const result = [];
        if (this.currentDirectory) {
            result.push({
                type: "parent",
                label: "..\\",
                path: this.parentDirectory(this.currentDirectory),
            });
        }
        result.push(...Array.from(directories.values()).sort((left, right) => left.label.localeCompare(right.label)));
        result.push(...files.sort((left, right) => left.label.localeCompare(right.label)));
        return result;
    }

    refresh() {
        this.currentItems = this.buildItems();
        this.fileList.setItems(this.currentItems, this.currentItems.length ? 0 : -1);
        if (this.nameInput) { this.nameInput.value = "*.*"; }
        this.updateInfo(this.currentItems[0] || null);
        this.updateHistoryState();
        this.updateHorizontalScrollbar();
    }

    currentMaskPath() {
        const directory = this.currentDirectory ? `${this.currentDirectory}\\` : "";
        return `THelpViewer:\\${directory}*.*`;
    }

    selectItem(item) {
        if (!item || item.type === "status" || !this.nameInput) { return; }
        this.nameInput.value = item.type === "file" ? item.entry.fileName : `${item.label}*.*`;
        this.updateInfo(item);
    }

    updateInfo(item) {
        if (this.pathLabel) {
            this.pathLabel.textContent = ` ${this.currentMaskPath()}`;
        }
        if (!this.detailLabel) { return; }
        if (!item) {
            this.detailLabel.textContent = "";
        } else if (item.type === "status") {
            this.detailLabel.textContent = ` ${item.label}`;
        } else if (item.type === "file") {
            const format = String(item.entry.format || (item.entry.kind === "doc" ? "Markdown" : "Help")).toUpperCase();
            const topics = Number.isInteger(item.entry.topics) ? `  ${item.entry.topics} topics` : "";
            this.detailLabel.textContent = ` ${item.entry.fileName}  ${format}${topics}`;
        } else {
            this.detailLabel.textContent = ` ${item.label}  Directory`;
        }
    }

    activateItem(item) {
        if (!item) { return; }
        if (item.type === "file") {
            this.openEntry(item.entry);
        } else if (item.type === "directory" || item.type === "parent") {
            this.currentDirectory = item.path;
            this.refresh();
            this.fileList.selectedElement()?.focus();
        }
    }

    selectNameMatch() {
        const query = String(this.nameInput?.value || "").trim().toLocaleLowerCase();
        if (!query || query.includes("*")) { return; }
        const index = this.currentItems.findIndex((item) => item.label.toLocaleLowerCase().startsWith(query));
        if (index >= 0) {
            this.fileList.select(index);
            this.updateInfo(this.currentItems[index]);
        }
    }

    openSelected() {
        const query = String(this.nameInput?.value || "").trim().toLocaleLowerCase();
        const exact = this.currentItems.find((item) => (
            item.type === "file" && item.entry.fileName.toLocaleLowerCase() === query
        ));
        if (exact) {
            this.openEntry(exact.entry);
            return;
        }
        this.activateItem(this.fileList.selectedItem());
    }

    openEntry(entry) {
        if (!entry || !this.onOpen) { return; }
        this.remember(entry);
        this.close();
        this.onOpen(entry);
    }

    updateHorizontalScrollbar() {
        if (!this.scrollTrack) { return; }
        const trackLength = 29;
        const columns = Math.max(1, Math.ceil(this.currentItems.length / this.fileList.rows));
        const maxColumn = Math.max(0, columns - 2);
        const position = maxColumn
            ? Math.round((this.fileList.firstColumn() / maxColumn) * (trackLength - 1))
            : -1;
        const cells = Array.from({ length: trackLength }, () => displayCp437Char(177));
        if (position >= 0) { cells[position] = displayCp437Char(254); }
        this.scrollTrack.textContent = cells.join("");
    }

    storedHistoryKeys() {
        try {
            const stored = JSON.parse(window.localStorage.getItem(this.storageKey) || "[]");
            return Array.isArray(stored) ? stored.filter((key) => typeof key === "string").slice(0, 10) : [];
        } catch {
            return [];
        }
    }

    historyEntries() {
        const byKey = new Map(this.entries.map((entry) => [entry.historyKey, entry]));
        return this.storedHistoryKeys().map((key) => byKey.get(key)).filter(Boolean);
    }

    remember(entry) {
        const keys = [entry.historyKey, ...this.storedHistoryKeys().filter((key) => key !== entry.historyKey)].slice(0, 10);
        try {
            window.localStorage.setItem(this.storageKey, JSON.stringify(keys));
        } catch {
            // Storage may be unavailable under restrictive file:// environments.
        }
    }

    updateHistoryState() {
        const history = this.historyEntries();
        this.historyList.setItems(history, history.length ? 0 : -1);
        if (this.historyButton) {
            this.historyButton.disabled = history.length === 0;
        }
    }

    toggleHistory() {
        if (!this.historyPopup || this.historyButton?.disabled) { return; }
        if (this.historyPopup.hidden) {
            this.updateHistoryState();
            this.historyPopup.hidden = false;
            window.requestAnimationFrame(() => {
                this.historyList.updateScrollbar();
                this.historyList.selectedElement()?.focus();
            });
        } else {
            this.hideHistory();
        }
    }

    hideHistory() {
        if (this.historyPopup) { this.historyPopup.hidden = true; }
    }

    selectHistory(entry, activate = false) {
        if (!entry) { return; }
        this.currentDirectory = entry.directory;
        this.refresh();
        const index = this.currentItems.findIndex((item) => (
            item.type === "file" && item.entry.historyKey === entry.historyKey
        ));
        this.fileList.select(index);
        this.selectItem(this.currentItems[index]);
        if (activate) {
            this.openEntry(entry);
        } else {
            this.hideHistory();
            this.nameInput?.focus();
        }
    }
}

class TVAsciiTableDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const chart = new TVMarkupList({
            className: "tv-ascii-chart",
            attrs: { "data-tv-ascii-chart": true },
        });
        const report = new TVStaticText({
            className: "tv-ascii-report",
            attrs: { "data-tv-ascii-report": true },
        });
        super({
            desktop,
            windowClass: "tv-ascii-window",
            palette: "ascii",
            ariaLabel: "ASCII Table",
            title: "ASCII Chart",
            bodyClass: "tv-ascii-body",
            closeAttrs: {
                "data-tv-ascii-close": true,
                "aria-label": "Close ASCII table",
            },
            bodyMarkup: [chart.renderMarkup(), report.renderMarkup()],
            footerMarkup: TVDialog.footerMarkup(),
            width: "34ch",
            height: "min(12em, calc(100% - 2em))",
            left: "4ch",
            top: "3em",
        });
        this.selectedCode = 0;
        this.chart = this.query("[data-tv-ascii-chart]");
        this.report = this.query("[data-tv-ascii-report]");
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        if (this.chart) {
            this.chart.addEventListener("click", (event) => this.onCellEvent(event));
            this.chart.addEventListener("focusin", (event) => this.onCellEvent(event));
            this.chart.addEventListener("mousemove", (event) => {
                if (event.buttons & 1) {
                    this.onCellEvent(event);
                }
            });
        }
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
        this.renderChart();
    }

    open() {
        super.open();
        this.renderChart();
    }

    renderChart() {
        if (!this.chart) {
            return;
        }
        const items = [];
        for (let code = 0; code < 256; code += 1) {
            const selected = code === this.selectedCode ? " is-selected" : "";
            items.push(
                `<button type="button" class="tv-ascii-cell${selected}" data-tv-ascii-code="${code}" aria-label="ASCII ${code}">${escapeHtml(displayCp437Char(code))}</button>`
            );
        }
        this.chart.innerHTML = items.join("");
        this.updateReport(this.selectedCode);
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        let nextCode = this.selectedCode;
        if (event.key === "ArrowLeft") {
            nextCode = (this.selectedCode + 255) & 0xFF;
        } else if (event.key === "ArrowRight") {
            nextCode = (this.selectedCode + 1) & 0xFF;
        } else if (event.key === "ArrowUp") {
            nextCode = (this.selectedCode + 224) & 0xFF;
        } else if (event.key === "ArrowDown") {
            nextCode = (this.selectedCode + 32) & 0xFF;
        } else {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.selectCode(nextCode);
    }

    onCellEvent(event) {
        const cell = event.target.closest("[data-tv-ascii-code]");
        if (!cell) {
            return;
        }
        const code = Number.parseInt(cell.getAttribute("data-tv-ascii-code"), 10);
        if (!Number.isInteger(code) || code < 0 || code > 255) {
            return;
        }
        this.selectCode(code);
    }

    selectCode(code) {
        this.selectedCode = code;
        if (this.chart) {
            this.chart.querySelectorAll("[data-tv-ascii-code]").forEach((element) => {
                const cellCode = Number.parseInt(element.getAttribute("data-tv-ascii-code"), 10);
                element.classList.toggle("is-selected", cellCode === code);
            });
        }
        this.updateReport(code);
    }

    updateReport(code) {
        if (!this.report) {
            return;
        }
        const char = code === 0 ? " " : displayCp437Char(code);
        const decimal = String(code).padStart(3, " ");
        const hex = code.toString(16).toUpperCase().padStart(2, "0");
        this.report.textContent = `  Char: ${char} Decimal: ${decimal} Hex ${hex}`.padEnd(32, " ");
    }
}

class TVCalculatorDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const buttonKeys = [
            ["CLEAR", "C", "C"],
            ["BACK", displayCp437Char(27), "Backspace"],
            ["PERCENT", "%", "%"],
            ["SIGN", displayCp437Char(241), "Change sign"],
            ["7", "7", "7"],
            ["8", "8", "8"],
            ["9", "9", "9"],
            ["DIVIDE", "/", "/"],
            ["4", "4", "4"],
            ["5", "5", "5"],
            ["6", "6", "6"],
            ["MULTIPLY", "*", "*"],
            ["1", "1", "1"],
            ["2", "2", "2"],
            ["3", "3", "3"],
            ["MINUS", "-", "-"],
            ["0", "0", "0"],
            ["DOT", ".", "."],
            ["EQUALS", "=", "="],
            ["PLUS", "+", "+"],
        ];
        const buttonValueMap = {
            CLEAR: "C",
            BACK: "\u001B",
            PERCENT: "%",
            SIGN: "\u00B1",
            DIVIDE: "/",
            MULTIPLY: "*",
            MINUS: "-",
            DOT: ".",
            EQUALS: "=",
            PLUS: "+",
        };
        const buttonsMarkup = buttonKeys.map(([key, label, aria]) =>
            new TVButton({
                baseClass: "tv-calc-button",
                attrs: {
                    "data-tv-calc-key": key,
                    "aria-label": `Calculator key ${aria}`,
                },
                labelMarkup: escapeHtml(label),
            }).renderMarkup()
        ).join("");
        const calcMain = new TVGroup({
            className: "tv-calc-main",
            children: [
                new TVStaticText({
                    className: "tv-calc-display",
                    attrs: { "data-tv-calc-display": true, "aria-live": "polite" },
                }),
                new TVGroup({
                    className: "tv-calc-keypad",
                    html: buttonsMarkup,
                }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Calculator",
            title: "Calculator",
            closeAttrs: {
                "data-tv-calc-close": true,
                "aria-label": "Close calculator",
            },
            bodyMarkup: calcMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "24ch",
            height: "min(15em, calc(100% - 2em))",
            left: "5ch",
            top: "3em",
            escapeCloses: false,
        });
        this.buttonValueMap = buttonValueMap;
        this.status = "first";
        this.number = "0";
        this.sign = " ";
        this.operate = "=";
        this.operand = 0;
        this.display = this.query("[data-tv-calc-display]");
        this.buttons = this.queryAll("[data-tv-calc-key]");
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.updateDisplay();
    }

    bind() {
        this.buttons.forEach((button) => {
            button.addEventListener("click", () => {
                const token = button.getAttribute("data-tv-calc-key") || "";
                this.calcKey(this.buttonValueMap[token] || token);
            });
        });
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
        document.addEventListener("keyup", (event) => this.onKeyUp(event));
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        const mapped = this.mapKeyEvent(event);
        if (!mapped) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.calcKey(mapped);
    }

    onKeyUp(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.key === "Enter" || event.key === "Backspace" || event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
        }
    }

    mapKeyEvent(event) {
        if (event.key === "Backspace") {
            return "\b";
        }
        if (event.key === "Escape") {
            return "\u001B";
        }
        if (event.key === "Enter") {
            return "\r";
        }
        if (event.key === "_") {
            return "_";
        }
        if (event.key && event.key.length === 1) {
            return event.key;
        }
        return "";
    }

    clear() {
        this.status = "first";
        this.number = "0";
        this.sign = " ";
        this.operate = "=";
        this.operand = 0;
    }

    error() {
        this.status = "error";
        this.number = "Error";
        this.sign = " ";
    }

    setDisplay(value) {
        if (!Number.isFinite(value)) {
            this.error();
            return;
        }
        if (value < 0) {
            this.sign = "-";
            this.number = String(-value);
        } else {
            this.sign = " ";
            this.number = String(value);
        }
        if (this.number.length > 25) {
            this.error();
        }
    }

    getDisplayValue() {
        return Number.parseFloat(this.number) || 0;
    }

    checkFirst() {
        if (this.status === "first") {
            this.status = "valid";
            this.number = "0";
            this.sign = " ";
        }
    }

    calcKey(key) {
        if (!key) {
            return;
        }
        let value = String(key).toUpperCase();
        if (this.status === "error" && value !== "C") {
            value = " ";
        }

        switch (value) {
            case "0":
            case "1":
            case "2":
            case "3":
            case "4":
            case "5":
            case "6":
            case "7":
            case "8":
            case "9":
                this.checkFirst();
                if (this.number.length < 15) {
                    if (this.number === "0") {
                        this.number = "";
                    }
                    this.number += value;
                }
                break;
            case ".":
                this.checkFirst();
                if (!this.number.includes(".")) {
                    this.number += ".";
                }
                break;
            case "\b":
            case "\u001B": {
                this.checkFirst();
                if (this.number.length <= 1) {
                    this.number = "0";
                } else {
                    this.number = this.number.slice(0, -1);
                }
                break;
            }
            case "_":
            case "\u00B1":
                this.sign = this.sign === " " ? "-" : " ";
                break;
            case "+":
            case "-":
            case "*":
            case "/":
            case "=":
            case "%":
            case "\r": {
                if (this.status === "valid") {
                    this.status = "first";
                    let r = this.getDisplayValue() * (this.sign === "-" ? -1 : 1);
                    if (value === "%") {
                        if (this.operate === "+" || this.operate === "-") {
                            r = (this.operand * r) / 100;
                        } else {
                            r /= 100;
                        }
                    }
                    switch (this.operate) {
                        case "+":
                            this.setDisplay(this.operand + r);
                            break;
                        case "-":
                            this.setDisplay(this.operand - r);
                            break;
                        case "*":
                            this.setDisplay(this.operand * r);
                            break;
                        case "/":
                            if (r === 0) {
                                this.error();
                            } else {
                                this.setDisplay(this.operand / r);
                            }
                            break;
                        default:
                            break;
                    }
                }
                this.operate = value === "\r" ? "=" : value;
                this.operand = this.getDisplayValue() * (this.sign === "-" ? -1 : 1);
                break;
            }
            case "C":
                this.clear();
                break;
            default:
                break;
        }
        this.updateDisplay();
    }

    updateDisplay() {
        if (!this.display) {
            return;
        }
        const width = 18;
        const lead = Math.max(0, width - this.number.length - 2);
        const text = `${" ".repeat(lead)}${this.sign}${this.number} `;
        this.display.textContent = text.slice(-width).padEnd(width, " ");
    }
}

class TVCalendarDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const now = new Date();
        const calendarMain = new TVGroup({
            className: "tv-calendar-main",
            children: [
                new TVGroup({
                    className: "tv-calendar-header",
                    children: [
                        new TVStaticText({
                            attrs: { "data-tv-calendar-caption": true },
                        }),
                        new TVButton({
                            dialog: false,
                            className: "tv-calendar-arrow",
                            attrs: {
                                type: "button",
                                "data-tv-calendar-prev": true,
                                "aria-label": "Previous month",
                            },
                            labelMarkup: escapeHtml(displayCp437Char(30)),
                        }),
                        new TVStaticText({
                            attrs: { "aria-hidden": "true" },
                            text: "  ",
                        }),
                        new TVButton({
                            dialog: false,
                            className: "tv-calendar-arrow",
                            attrs: {
                                type: "button",
                                "data-tv-calendar-next": true,
                                "aria-label": "Next month",
                            },
                            labelMarkup: escapeHtml(displayCp437Char(31)),
                        }),
                    ],
                }),
                new TVStaticText({
                    text: "Su Mo Tu We Th Fr Sa",
                }),
                new TVStaticText({
                    className: "tv-calendar-grid",
                    attrs: { "data-tv-calendar-grid": true },
                }),
            ],
        }).renderMarkup();
        super({
            desktop,
            windowClass: "tv-calendar-window",
            palette: "calendar",
            ariaLabel: "Calendar",
            title: "Calendar",
            bodyClass: "tv-calendar-body",
            closeAttrs: {
                "data-tv-calendar-close": true,
                "aria-label": "Close calendar",
            },
            bodyMarkup: calendarMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "27ch",
            height: "min(11em, calc(100% - 2em))",
            left: "4ch",
            top: "3em",
        });
        this.caption = this.query("[data-tv-calendar-caption]");
        this.grid = this.query("[data-tv-calendar-grid]");
        this.prevButton = this.query("[data-tv-calendar-prev]");
        this.nextButton = this.query("[data-tv-calendar-next]");
        this.curYear = now.getFullYear();
        this.curMonth = now.getMonth() + 1;
        this.curDay = now.getDate();
        this.year = this.curYear;
        this.month = this.curMonth;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.render();
    }

    bind() {
        if (this.prevButton) {
            this.prevButton.addEventListener("click", () => this.changeMonth(-1));
        }
        if (this.nextButton) {
            this.nextButton.addEventListener("click", () => this.changeMonth(1));
        }
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        if (event.key === "+" || event.key === "ArrowDown") {
            event.preventDefault();
            this.changeMonth(1);
        } else if (event.key === "-" || event.key === "ArrowUp") {
            event.preventDefault();
            this.changeMonth(-1);
        }
    }

    changeMonth(delta) {
        this.month += delta;
        if (this.month > 12) {
            this.month = 1;
            this.year += 1;
        } else if (this.month < 1) {
            this.month = 12;
            this.year -= 1;
        }
        this.render();
    }

    daysInMonth(month, year) {
        return DAYS_IN_MONTH[month] + (month === 2 && isLeapYear(year) ? 1 : 0);
    }

    render() {
        if (!this.grid || !this.caption) {
            return;
        }
        this.caption.textContent = `${MONTH_NAMES[this.month].padStart(9, " ")} ${String(this.year).padStart(4, " ")}`;
        const first = 1 - dayOfWeek(1, this.month, this.year);
        const days = this.daysInMonth(this.month, this.year);
        const cells = [];
        let current = first;
        for (let row = 0; row < 6; row += 1) {
            for (let col = 0; col < 7; col += 1) {
                const inMonth = current >= 1 && current <= days;
                const isToday = inMonth
                    && this.year === this.curYear
                    && this.month === this.curMonth
                    && current === this.curDay;
                cells.push(
                    `<span class="tv-calendar-cell${isToday ? " is-current" : ""}${!inMonth ? " is-empty" : ""}">${inMonth ? String(current).padStart(2, " ") : "  "}</span>`
                );
                current += 1;
            }
        }
        this.grid.innerHTML = cells.join("");
    }
}

class TVColorsDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const okButton = new TVButton({
            className: "is-default",
            attrs: { "data-tv-colors-ok": true },
            label: 'O~K~',
        });
        const cancelButton = new TVButton({
            attrs: { "data-tv-colors-cancel": true },
            label: '~C~ancel',
        });
        const resetAllButton = new TVButton({
            attrs: { "data-tv-colors-reset-all": true },
            label: '~R~eset All',
        });
        const defaultButton = new TVButton({
            attrs: { "data-tv-colors-default": true },
            label: '~D~efault',
        });
        const buttonStrip = new TVButtonStrip({
            className: "tv-colors-dialog-buttons",
            buttons: [defaultButton, resetAllButton, okButton, cancelButton],
        }).renderMarkup();
        const groupTitle = new TVLabel({
            text: "~G~roup",
            hotkey: true,
            className: "tv-colors-group-label",
        }).renderMarkup();
        const itemTitle = new TVLabel({
            text: "~I~tem",
            hotkey: true,
            className: "tv-colors-item-label",
        }).renderMarkup();
        const fgTitle = new TVLabel({
            text: "~F~oreground",
            hotkey: true,
            className: "tv-colors-foreground-label",
        }).renderMarkup();
        const bgTitle = new TVLabel({
            text: "~B~ackground",
            hotkey: true,
            className: "tv-colors-background-label",
        }).renderMarkup();
        super({
            desktop,
            ariaLabel: "Colors",
            title: "Colors",
            windowClass: "tv-colors-window",
            bodyClass: "tv-colors-body",
            closeAttrs: {
                "data-tv-colors-close": true,
                "aria-label": "Close colors dialog",
            },
            bodyMarkup: `
                <div class="tv-colors-main">
                    <div class="tv-colors-panels">
                        <div class="tv-colors-column">
                            ${groupTitle}
                            ${TVVerticalListViewer.renderMarkup({
                                rootClass: "tv-colors-listviewer tv-colors-groups-listviewer",
                                rootAttrs: { "data-tv-colors-groups": true },
                                viewportClass: "tv-colors-list-viewport",
                            })}
                        </div>
                        <div class="tv-colors-column">
                            ${itemTitle}
                            ${TVVerticalListViewer.renderMarkup({
                                rootClass: "tv-colors-listviewer tv-colors-items-listviewer",
                                rootAttrs: { "data-tv-colors-items": true },
                                viewportClass: "tv-colors-list-viewport",
                            })}
                        </div>
                        <div class="tv-colors-side">
                            ${fgTitle}
                            <div class="tv-colors-selector tv-colors-foreground" data-tv-colors-foreground></div>
                            ${bgTitle}
                            <div class="tv-colors-selector tv-colors-background is-background" data-tv-colors-background></div>
                            <div class="tv-colors-display" data-tv-colors-display></div>
                        </div>
                    </div>
                    ${buttonStrip}
                </div>
            `,
            footerMarkup: TVDialog.footerMarkup(),
            width: "61ch",
            height: "min(18em, calc(100% - 2em))",
            left: "3ch",
            top: "2em",
        });
        this.groupList = this.query("[data-tv-colors-groups]");
        this.itemList = this.query("[data-tv-colors-items]");
        this.foreground = this.query("[data-tv-colors-foreground]");
        this.background = this.query("[data-tv-colors-background]");
        this.display = this.query("[data-tv-colors-display]");
        this.okButton = this.query("[data-tv-colors-ok]");
        this.cancelButton = this.query("[data-tv-colors-cancel]");
        this.defaultButton = this.query("[data-tv-colors-default]");
        this.resetAllButton = this.query("[data-tv-colors-reset-all]");
        this.groupBox = new TVVerticalListViewer(this.groupList, {
            itemClassName: "tv-colors-list-item",
            itemAttrName: "data-tv-colors-group",
            renderItemContent: (group) => escapeHtml(group.name),
        });
        this.itemBox = new TVVerticalListViewer(this.itemList, {
            itemClassName: "tv-colors-list-item",
            itemAttrName: "data-tv-colors-item",
            renderItemContent: (item) => escapeHtml(item.name),
        });
        this.selectedGroup = 0;
        this.pendingPalette = cloneColorPalette(TV.getActiveColorPalette() || buildDefaultColorPalette());
        this.previousPalette = cloneColorPalette(this.pendingPalette);
        this.bindCommonClose(() => this.cancel());
        this.bindDrag();
        this.bind();
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    bind() {
        this.groupBox.bind({
            onSelect: (_group, index) => this.onGroupSelect(index),
        });
        this.itemBox.bind({
            onSelect: (_item, index) => this.onItemSelect(index),
        });
        if (this.foreground) {
            this.foreground.addEventListener("click", (event) => this.onSelectorClick(event, "fg"));
            this.foreground.addEventListener("keydown", (event) => this.onSelectorKeyDown(event, "fg"));
        }
        if (this.background) {
            this.background.addEventListener("click", (event) => this.onSelectorClick(event, "bg"));
            this.background.addEventListener("keydown", (event) => this.onSelectorKeyDown(event, "bg"));
        }
        if (this.okButton) {
            this.okButton.addEventListener("click", () => this.confirm());
        }
        if (this.cancelButton) {
            this.cancelButton.addEventListener("click", () => this.cancel());
        }
        if (this.defaultButton) {
            this.defaultButton.addEventListener("click", () => this.restoreSelectedDefault());
        }
        if (this.resetAllButton) {
            this.resetAllButton.addEventListener("click", () => this.resetAllColors());
        }
    }

    open() {
        this.previousPalette = cloneColorPalette(TV.getActiveColorPalette() || buildDefaultColorPalette());
        this.pendingPalette = cloneColorPalette(this.previousPalette);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
        super.open();
        window.requestAnimationFrame(() => {
            this.groupBox.updateScrollbar();
            this.itemBox.updateScrollbar();
            this.groupBox.selectedElement()?.focus();
        });
    }

    onGroupSelect(index) {
        if (!Number.isInteger(index) || index < 0 || index >= COLOR_GROUPS.length) {
            return;
        }
        this.selectedGroup = index;
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    onItemSelect(index) {
        const group = this.pendingPalette[this.selectedGroup];
        if (!group || !Number.isInteger(index) || index < 0 || index >= group.items.length) {
            return;
        }
        group.index = index;
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    onSelectorClick(event, type) {
        const button = event.target.closest("[data-tv-color-index]");
        if (!button) {
            return;
        }
        const colorIndex = Number.parseInt(button.getAttribute("data-tv-color-index"), 10);
        if (!Number.isInteger(colorIndex)) {
            return;
        }
        const group = this.pendingPalette[this.selectedGroup];
        if (!group) {
            return;
        }
        const item = group.items[group.index] || group.items[0];
        if (!item) {
            return;
        }
        const keepFocus = document.activeElement === button;
        let attr;
        if (type === "fg") {
            attr = (item.attr & 0xF0) | (colorIndex & 0x0F);
        } else {
            attr = ((colorIndex & 0x0F) << 4) | (item.attr & 0x0F);
        }
        setColorPaletteAttribute(this.pendingPalette, item.paletteIndex, attr);
        applyColorPalette(this.pendingPalette, false);
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
        if (keepFocus) {
            const selector = type === "fg" ? this.foreground : this.background;
            window.requestAnimationFrame(() => {
                selector?.querySelector(`[data-tv-color-index="${colorIndex}"]`)?.focus();
            });
        }
    }

    onSelectorKeyDown(event, type) {
        const button = event.target.closest("[data-tv-color-index]");
        if (!button || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
            return;
        }
        const maxColor = type === "bg" ? 7 : 15;
        let color = Number.parseInt(button.getAttribute("data-tv-color-index"), 10);
        if (event.key === "ArrowLeft") {
            color = color > 0 ? color - 1 : maxColor;
        } else if (event.key === "ArrowRight") {
            color = color < maxColor ? color + 1 : 0;
        } else if (event.key === "ArrowUp") {
            color = color > 3 ? color - 4 : (color === 0 ? maxColor : color + maxColor - 4);
        } else {
            color = color < maxColor - 3 ? color + 4 : (color === maxColor ? 0 : color - maxColor + 4);
        }
        event.preventDefault();
        event.stopPropagation();
        const selector = type === "fg" ? this.foreground : this.background;
        selector?.querySelector(`[data-tv-color-index="${color}"]`)?.click();
        selector?.querySelector(`[data-tv-color-index="${color}"]`)?.focus();
    }

    selectedItem() {
        const group = this.pendingPalette[this.selectedGroup];
        return group ? (group.items[group.index] || group.items[0]) : null;
    }

    confirm() {
        applyColorPalette(this.pendingPalette, true);
        this.close();
    }

    cancel() {
        applyColorPalette(this.previousPalette, false);
        this.close();
    }

    restoreSelectedDefault() {
        const group = this.pendingPalette[this.selectedGroup];
        const item = group?.items[group.index];
        const defaultItem = buildDefaultColorPalette()[this.selectedGroup]?.items[group?.index];
        if (!item || !defaultItem) {
            return;
        }
        setColorPaletteAttribute(this.pendingPalette, item.paletteIndex, defaultItem.attr);
        applyColorPalette(this.pendingPalette, false);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    resetAllColors() {
        const groupIndexes = this.pendingPalette.map((group) => group.index);
        this.pendingPalette = buildDefaultColorPalette();
        this.pendingPalette.forEach((group, index) => {
            const previousIndex = groupIndexes[index];
            if (Number.isInteger(previousIndex) && previousIndex >= 0 && previousIndex < group.items.length) {
                group.index = previousIndex;
            }
        });
        applyColorPalette(this.pendingPalette, false);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    renderGroups() {
        this.groupBox.setItems(this.pendingPalette, this.selectedGroup);
    }

    renderItems() {
        if (!this.itemBox.root) {
            return;
        }
        const group = this.pendingPalette[this.selectedGroup];
        this.itemBox.setItems(group.items, group.index);
    }

    renderSelectors() {
        const item = this.selectedItem();
        if (!item) {
            return;
        }
        const fg = item.attr & 0x0F;
        const bg = (item.attr >> 4) & 0x0F;
        if (this.foreground) {
            this.foreground.innerHTML = this.renderSelectorCells(16, fg);
        }
        if (this.background) {
            this.background.innerHTML = this.renderSelectorCells(8, bg);
        }
    }

    renderSelectorCells(count, selected) {
        const marker = displayCp437Char(8);
        const icon = displayCp437Char(219).repeat(3);
        const cells = [];
        for (let index = 0; index < count; index += 1) {
            const isSelected = index === selected;
            const content = isSelected
                ? `${escapeHtml(displayCp437Char(219))}<span class="tv-color-cell-marker">${escapeHtml(marker)}</span>${escapeHtml(displayCp437Char(219))}`
                : escapeHtml(icon);
            cells.push(`
                <button
                    type="button"
                    class="tv-color-cell${isSelected ? " is-selected" : ""}"
                    data-tv-color-index="${index}"
                    style="--tv-color-cell:${DOS_COLORS[index]};"
                    aria-label="Color ${index}"
                    aria-pressed="${isSelected ? "true" : "false"}"
                    tabindex="${isSelected ? "0" : "-1"}"
                >${content}</button>
            `);
        }
        return cells.join("");
    }

    renderDisplay() {
        if (!this.display) {
            return;
        }
        const item = this.selectedItem();
        if (!item) {
            return;
        }
        const fg = dosColor(item.attr, 0);
        const bg = dosColor(item.attr, 4);
        const text = escapeHtml("Text Text Text ");
        this.display.innerHTML = `<span class="tv-colors-display-sample" style="color:${fg};background:${bg};">${text}<br>${text}</span>`;
    }
}

const TV_MIDI_LIBRARY = Object.freeze([
    {
        title: "THelpViewer - Neon Grid",
        file: "assets/midi/modern-neon-grid.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Byte Runner",
        file: "assets/midi/modern-byte-runner.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Soft Circuit",
        file: "assets/midi/modern-soft-circuit.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Terminal Drift",
        file: "assets/midi/modern-terminal-drift.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Night Cache",
        file: "assets/midi/modern-night-cache.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Pixel Rain",
        file: "assets/midi/modern-pixel-rain.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Vector Sunrise",
        file: "assets/midi/modern-vector-sunrise.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Copper Lanes",
        file: "assets/midi/modern-copper-lanes.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Glass Towers",
        file: "assets/midi/modern-glass-towers.mid",
        credit: "Original demo",
    },
    {
        title: "THelpViewer - Data Stream",
        file: "assets/midi/modern-data-stream.mid",
        credit: "Original demo",
    },
    {
        title: "Komiku - Disco Challenge",
        file: "assets/midi/oga-komiku-disco-challenge.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Pop City",
        file: "assets/midi/oga-komiku-pop-city.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - The Big Dancefloor",
        file: "assets/midi/oga-komiku-big-dancefloor.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Everything Is Groovy",
        file: "assets/midi/oga-komiku-everything-is-groovy.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Road 1 Chill",
        file: "assets/midi/oga-komiku-road-1-chill.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Road 1 Fight",
        file: "assets/midi/oga-komiku-road-1-fight.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Road 2 Chill",
        file: "assets/midi/oga-komiku-road-2-chill.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Road 3 Fight",
        file: "assets/midi/oga-komiku-road-3-fight.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Road 4 Fight",
        file: "assets/midi/oga-komiku-road-4-fight.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - We Have to Dance Together",
        file: "assets/midi/oga-komiku-we-have-to-dance-together.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - Dropda Basstion",
        file: "assets/midi/oga-komiku-dropda-basstion.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Komiku - The Test",
        file: "assets/midi/oga-komiku-the-test.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - Broken Arm",
        file: "assets/midi/oga-roppy-broken-arm.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - Casual Afternoon",
        file: "assets/midi/oga-roppy-casual-afternoon.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - Icy Garden",
        file: "assets/midi/oga-roppy-icy-garden.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - Journey Forgotten",
        file: "assets/midi/oga-roppy-journey-forgotten.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - No One",
        file: "assets/midi/oga-roppy-no-one.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - Standardized Anxiety",
        file: "assets/midi/oga-roppy-standardized-anxiety.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Roppy Chop Studios - Without Time",
        file: "assets/midi/oga-roppy-without-time.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "nene - Long Away Home",
        file: "assets/midi/oga-nene-long-away-home.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "Tozan - Stringsvop",
        file: "assets/midi/oga-tozan-stringsvop.mid",
        credit: "OpenGameArt CC0",
    },
    {
        title: "F. Abt - Vocalise No. 1",
        file: "assets/midi/vocalise-1.mid",
        credit: "Mutopia Project",
    },
    {
        title: "F. Abt - When the Swallows Homeward Fly",
        file: "assets/midi/when-the-swallows-homeward-fly.mid",
        credit: "Mutopia Project",
    },
    {
        title: "J. Andre - Sonatine Op. 34 No. 1",
        file: "assets/midi/andre-sonatine-op34-1.mid",
        credit: "Mutopia Project",
    },
    {
        title: "A. Adam - Giselle",
        file: "assets/midi/giselle.mid",
        credit: "Mutopia Project",
    },
    {
        title: "A. Adam - Minuit Chretiens",
        file: "assets/midi/minuit-chretiens.mid",
        credit: "Mutopia Project",
    },
    {
        title: "S. Adams - The Blue Mountains",
        file: "assets/midi/blue-mountains.mid",
        credit: "Mutopia Project",
    },
    {
        title: "I. Albeniz - Rumores de la Caleta",
        file: "assets/midi/rumores-de-la-caleta.mid",
        credit: "Mutopia Project",
    },
    {
        title: "C. V. Alkan - Op. 31 No. 1",
        file: "assets/midi/alkan-op31-1.mid",
        credit: "Mutopia Project",
    },
    {
        title: "C. V. Alkan - Op. 31 No. 2",
        file: "assets/midi/alkan-op31-2.mid",
        credit: "Mutopia Project",
    },
    {
        title: "C. V. Alkan - Toccatina",
        file: "assets/midi/alkan-toccatina.mid",
        credit: "Mutopia Project",
    },
    {
        title: "C. P. E. Bach - Rondo",
        file: "assets/midi/cpe-bach-rondo.mid",
        credit: "Mutopia Project",
    },
    {
        title: "J. S. Bach - BWV 259",
        file: "assets/midi/bach-bwv-259.mid",
        credit: "Mutopia Project",
    },
    {
        title: "J. S. Bach - BWV 269",
        file: "assets/midi/bach-bwv-269.mid",
        credit: "Mutopia Project",
    },
    {
        title: "J. S. Bach - BWV 347",
        file: "assets/midi/bach-bwv-347.mid",
        credit: "Mutopia Project",
    },
    {
        title: "J. S. Bach - Anna Magdalena 20a",
        file: "assets/midi/bach-anna-magdalena-20a.mid",
        credit: "Mutopia Project",
    },
    ...Array.from({ length: 15 }, (_unused, index) => {
        const number = index + 1;
        return {
            title: `J. S. Bach - Invention No. ${number}`,
            file: `assets/midi/bach-invention-${String(number).padStart(2, "0")}.mid`,
            credit: "Mutopia Project",
        };
    }),
]);

const TV_MIDI_EXTERNAL_SOURCES = Object.freeze([
    {
        label: "Commons CC0",
        title: "Wikimedia - Au clair de la lune",
        file: "https://upload.wikimedia.org/wikipedia/commons/e/e6/Au_clair_de_le_lune_chant_et_piano.midi",
        credit: "Wikimedia Commons CC0",
        external: true,
    },
    {
        label: "Commons PD",
        title: "Wikimedia - Saint-Saens Op. 166",
        file: "https://upload.wikimedia.org/wikipedia/commons/5/55/Saint-saens_sonate_hautbois_op166_1er_mouvement_piano.midi",
        credit: "Wikimedia Commons PD/CC0",
        external: true,
    },
    {
        label: "ToBeFree 1",
        title: "ToBeFree - 03 May 2020",
        file: "https://upload.wikimedia.org/wikipedia/commons/c/c3/03may2020-tobefree-generated.mid",
        credit: "Wikimedia Commons CC BY-SA 4.0",
        external: true,
    },
    {
        label: "ToBeFree 2",
        title: "ToBeFree - Friendship",
        file: "https://upload.wikimedia.org/wikipedia/commons/2/26/Friendship-tobefree-generated.mid",
        credit: "Wikimedia Commons CC BY-SA 4.0",
        external: true,
    },
    {
        label: "ToBeFree 3",
        title: "ToBeFree - Infinite Adventures",
        file: "https://upload.wikimedia.org/wikipedia/commons/5/57/Infiniteadventurestheme-tobefree-generated.mid",
        credit: "Wikimedia Commons CC BY-SA 4.0",
        external: true,
    },
]);

const MIDI_DEFAULT_TEMPO_US = 500000;

function midiReadString(view, state, length) {
    let text = "";
    for (let index = 0; index < length; index += 1) {
        text += String.fromCharCode(view.getUint8(state.offset));
        state.offset += 1;
    }
    return text;
}

function midiReadU8(view, state) {
    if (state.offset >= view.byteLength) {
        throw new Error("Unexpected end of MIDI data.");
    }
    const value = view.getUint8(state.offset);
    state.offset += 1;
    return value;
}

function midiReadU16(view, state) {
    if (state.offset + 2 > view.byteLength) {
        throw new Error("Unexpected end of MIDI data.");
    }
    const value = view.getUint16(state.offset, false);
    state.offset += 2;
    return value;
}

function midiReadU32(view, state) {
    if (state.offset + 4 > view.byteLength) {
        throw new Error("Unexpected end of MIDI data.");
    }
    const value = view.getUint32(state.offset, false);
    state.offset += 4;
    return value;
}

function midiReadVariableLength(view, state, limit) {
    let value = 0;
    for (let count = 0; count < 4; count += 1) {
        if (state.offset >= limit) {
            throw new Error("Unexpected end of MIDI variable length value.");
        }
        const byte = midiReadU8(view, state);
        value = (value << 7) | (byte & 0x7F);
        if ((byte & 0x80) === 0) {
            return value;
        }
    }
    throw new Error("MIDI variable length value is too long.");
}

function midiEventDataLength(status) {
    const type = status & 0xF0;
    return type === 0xC0 || type === 0xD0 ? 1 : 2;
}

function parseMidiFile(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    const state = { offset: 0 };
    if (midiReadString(view, state, 4) !== "MThd") {
        throw new Error("MIDI header not found.");
    }
    const headerLength = midiReadU32(view, state);
    const headerEnd = state.offset + headerLength;
    const format = midiReadU16(view, state);
    const trackCount = midiReadU16(view, state);
    const division = midiReadU16(view, state);
    state.offset = headerEnd;
    if ((division & 0x8000) !== 0) {
        throw new Error("SMPTE MIDI timing is not supported.");
    }
    if (format > 1) {
        throw new Error(`Unsupported MIDI format ${format}.`);
    }
    const ticksPerBeat = division || 384;
    const events = [];
    let maxTick = 0;

    for (let trackIndex = 0; trackIndex < trackCount; trackIndex += 1) {
        if (midiReadString(view, state, 4) !== "MTrk") {
            throw new Error("MIDI track chunk not found.");
        }
        const trackLength = midiReadU32(view, state);
        const trackEnd = state.offset + trackLength;
        let tick = 0;
        let runningStatus = 0;

        while (state.offset < trackEnd) {
            const delta = midiReadVariableLength(view, state, trackEnd);
            tick += delta;
            maxTick = Math.max(maxTick, tick);
            let status = midiReadU8(view, state);
            if (status < 0x80) {
                if (!runningStatus) {
                    throw new Error("MIDI running status without previous status.");
                }
                state.offset -= 1;
                status = runningStatus;
            } else if (status < 0xF0) {
                runningStatus = status;
            } else {
                runningStatus = 0;
            }

            if (status === 0xFF) {
                const metaType = midiReadU8(view, state);
                const length = midiReadVariableLength(view, state, trackEnd);
                if (metaType === 0x51 && length >= 3) {
                    const tempo = (view.getUint8(state.offset) << 16)
                        | (view.getUint8(state.offset + 1) << 8)
                        | view.getUint8(state.offset + 2);
                    events.push({ type: "tempo", tick, tempo });
                }
                state.offset += length;
                if (metaType === 0x2F) {
                    state.offset = trackEnd;
                }
                continue;
            }

            if (status === 0xF0 || status === 0xF7) {
                const length = midiReadVariableLength(view, state, trackEnd);
                state.offset += length;
                continue;
            }

            const channel = status & 0x0F;
            const eventType = status & 0xF0;
            const dataLength = midiEventDataLength(status);
            const note = midiReadU8(view, state);
            const value = dataLength === 2 ? midiReadU8(view, state) : 0;
            if (eventType === 0x90 && value > 0) {
                events.push({ type: "noteOn", tick, channel, note, velocity: value });
            } else if (eventType === 0x80 || (eventType === 0x90 && value === 0)) {
                events.push({ type: "noteOff", tick, channel, note });
            }
        }
        state.offset = trackEnd;
    }

    events.sort((left, right) => {
        if (left.tick !== right.tick) {
            return left.tick - right.tick;
        }
        if (left.type === right.type) {
            return 0;
        }
        return left.type === "tempo" ? -1 : 1;
    });

    let tempo = MIDI_DEFAULT_TEMPO_US;
    let lastTick = 0;
    let seconds = 0;
    for (const event of events) {
        seconds += ((event.tick - lastTick) * tempo) / ticksPerBeat / 1000000;
        event.time = seconds;
        lastTick = event.tick;
        if (event.type === "tempo") {
            tempo = event.tempo || tempo;
        }
    }

    const activeNotes = new Map();
    const notes = [];
    for (const event of events) {
        if (event.type === "noteOn") {
            const key = `${event.channel}:${event.note}`;
            const pending = activeNotes.get(key) || [];
            pending.push(event);
            activeNotes.set(key, pending);
        } else if (event.type === "noteOff") {
            const key = `${event.channel}:${event.note}`;
            const pending = activeNotes.get(key);
            if (!pending || !pending.length) {
                continue;
            }
            const start = pending.shift();
            if (!pending.length) {
                activeNotes.delete(key);
            }
            notes.push({
                time: start.time,
                duration: Math.max(0.04, event.time - start.time),
                midi: start.note,
                velocity: start.velocity,
                channel: start.channel,
            });
        }
    }

    for (const pending of activeNotes.values()) {
        for (const start of pending) {
            notes.push({
                time: start.time,
                duration: 0.4,
                midi: start.note,
                velocity: start.velocity,
                channel: start.channel,
            });
        }
    }

    notes.sort((left, right) => left.time - right.time || left.midi - right.midi);
    const duration = notes.reduce((max, note) => Math.max(max, note.time + note.duration), seconds);
    if (!notes.length) {
        throw new Error("No playable MIDI notes found.");
    }
    return {
        format,
        trackCount,
        ticksPerBeat,
        maxTick,
        notes,
        duration,
    };
}

function midiNoteFrequency(note) {
    return 440 * Math.pow(2, (note - 69) / 12);
}

function formatMidiTime(seconds) {
    const safeSeconds = Math.max(0, Math.floor(seconds || 0));
    const minutes = Math.floor(safeSeconds / 60);
    const rest = String(safeSeconds % 60).padStart(2, "0");
    return `${minutes}:${rest}`;
}

function normalizeMidiUrl(value) {
    const trimmed = String(value || "").trim();
    if (!trimmed) {
        throw new Error("Enter a MIDI URL first.");
    }
    const url = new URL(trimmed, window.location.href);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
        throw new Error("Only HTTP and HTTPS MIDI URLs are supported.");
    }
    if (window.location.protocol === "https:" && url.protocol !== "https:") {
        throw new Error("Use an HTTPS MIDI URL on an HTTPS page.");
    }
    return url.href;
}

function titleFromMidiUrl(url) {
    try {
        const parsed = new URL(url);
        const filename = decodeURIComponent(parsed.pathname.split("/").filter(Boolean).pop() || "");
        const title = filename.replace(/\.(midi?|kar)$/i, "").replace(/[_-]+/g, " ").trim();
        return title || parsed.hostname || "External MIDI";
    } catch {
        return "External MIDI";
    }
}

function looksLikeMidiUrl(url) {
    try {
        return /\.(mid|midi)(?:$|[?#])/i.test(new URL(url, window.location.href).href);
    } catch {
        return false;
    }
}

function extractMidiUrlFromHtml(html, baseUrl) {
    const candidates = [];
    const attrPattern = /\b(?:href|src)=["']([^"']+\.(?:mid|midi)(?:[?#][^"']*)?)["']/gi;
    let match = attrPattern.exec(html);
    while (match) {
        candidates.push(match[1]);
        match = attrPattern.exec(html);
    }
    const barePattern = /https?:\/\/[^\s"'<>]+?\.(?:mid|midi)(?:[?#][^\s"'<>]*)?/gi;
    match = barePattern.exec(html);
    while (match) {
        candidates.push(match[0]);
        match = barePattern.exec(html);
    }
    for (const candidate of candidates) {
        try {
            const url = new URL(candidate, baseUrl).href;
            if (looksLikeMidiUrl(url)) {
                return url;
            }
        } catch {
            continue;
        }
    }
    return "";
}

class TVMidiSynth {
    constructor() {
        this.context = null;
        this.master = null;
        this.nodes = [];
        this.progressTimer = null;
        this.finishTimer = null;
        this.startedAt = 0;
        this.sequence = null;
        this.onProgress = null;
        this.onDone = null;
    }

    async ensureContext() {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
            throw new Error("Web Audio is not available in this browser.");
        }
        if (!this.context) {
            this.context = new AudioContextCtor();
            this.master = this.context.createGain();
            this.master.gain.value = 0.72;
            this.master.connect(this.context.destination);
        }
        if (this.context.state === "suspended") {
            await this.context.resume();
        }
        return this.context;
    }

    async play(sequence, onProgress, onDone) {
        this.stop(false);
        const context = await this.ensureContext();
        this.sequence = sequence;
        this.onProgress = onProgress;
        this.onDone = onDone;
        this.startedAt = context.currentTime + 0.08;
        this.schedule(sequence);
        this.progressTimer = window.setInterval(() => this.reportProgress(), 120);
        this.finishTimer = window.setTimeout(() => this.finish(), Math.max(250, (sequence.duration + 0.25) * 1000));
        this.reportProgress();
    }

    schedule(sequence) {
        const context = this.context;
        if (!context || !this.master) {
            return;
        }
        for (const note of sequence.notes) {
            const start = this.startedAt + note.time;
            const end = start + note.duration;
            const releaseEnd = end + 0.06;
            if (releaseEnd <= context.currentTime) {
                continue;
            }
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.type = note.channel === 9 ? "square" : (note.channel % 2 ? "triangle" : "sine");
            oscillator.frequency.setValueAtTime(midiNoteFrequency(note.midi), start);
            const peak = Math.min(0.09, 0.025 + (note.velocity / 127) * 0.055);
            gain.gain.setValueAtTime(0.0001, start);
            gain.gain.linearRampToValueAtTime(peak, start + 0.012);
            gain.gain.setValueAtTime(peak * 0.78, Math.max(start + 0.02, end - 0.04));
            gain.gain.exponentialRampToValueAtTime(0.0001, releaseEnd);
            oscillator.connect(gain);
            gain.connect(this.master);
            oscillator.start(start);
            oscillator.stop(releaseEnd);
            this.nodes.push({ oscillator, gain });
        }
    }

    reportProgress() {
        if (!this.context || !this.sequence || !this.onProgress) {
            return;
        }
        const elapsed = Math.max(0, this.context.currentTime - this.startedAt);
        this.onProgress(Math.min(elapsed, this.sequence.duration), this.sequence.duration);
    }

    finish() {
        const onDone = this.onDone;
        const sequence = this.sequence;
        this.stop(false);
        if (onDone) {
            onDone(sequence);
        }
    }

    stop(report = true) {
        if (this.progressTimer !== null) {
            window.clearInterval(this.progressTimer);
            this.progressTimer = null;
        }
        if (this.finishTimer !== null) {
            window.clearTimeout(this.finishTimer);
            this.finishTimer = null;
        }
        for (const node of this.nodes) {
            try { node.oscillator.stop(); } catch { /* already stopped */ }
            try { node.oscillator.disconnect(); } catch { /* already disconnected */ }
            try { node.gain.disconnect(); } catch { /* already disconnected */ }
        }
        this.nodes = [];
        const progress = this.onProgress;
        this.sequence = null;
        this.onProgress = null;
        this.onDone = null;
        if (report && progress) {
            progress(0, 0);
        }
    }
}

class TVMidiPlayerDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const previousButton = new TVButton({
            dialog: false,
            className: "tv-midi-control",
            attrs: { "data-tv-midi-previous": true, title: "Previous track" },
            label: "◄◄",
        });
        const playButton = new TVButton({
            dialog: false,
            className: "tv-midi-control is-default",
            attrs: { "data-tv-midi-play": true },
            label: "►",
        });
        const pauseButton = new TVButton({
            dialog: false,
            className: "tv-midi-control",
            attrs: { "data-tv-midi-pause": true, title: "Pause" },
            label: "▌▌",
        });
        const stopButton = new TVButton({
            dialog: false,
            className: "tv-midi-control",
            attrs: { "data-tv-midi-stop": true },
            label: "■",
        });
        const nextButton = new TVButton({
            dialog: false,
            className: "tv-midi-control",
            attrs: { "data-tv-midi-next": true, title: "Next track" },
            label: "►►",
        });
        const moreButton = new TVButton({
            dialog: false,
            className: "tv-midi-more-action",
            attrs: { "data-tv-midi-more": true, "aria-expanded": "false" },
            label: "More",
        });
        const closeButton = new TVButton({
            dialog: false,
            className: "tv-midi-close-action",
            attrs: { "data-tv-midi-close-button": true },
            label: "Close",
        });
        const buttons = new TVButtonStrip({
            className: "tv-midi-buttons",
            buttons: [previousButton, playButton, pauseButton, stopButton, nextButton, moreButton, closeButton],
        }).renderMarkup();
        const sourceButtons = TV_MIDI_EXTERNAL_SOURCES.map((source, index) => new TVButton({
            dialog: false,
            className: "tv-midi-source-preset",
            attrs: {
                "data-tv-midi-source": index,
                title: `${source.title} (${source.credit})`,
            },
            labelMarkup: escapeHtml(source.label),
        }).renderMarkup()).join("");
        const display = new TVGroup({
            className: "tv-midi-display",
            children: [
                new TVGroup({
                    className: "tv-midi-display-line",
                    children: [
                        new TVStaticText({ tag: "span", className: "tv-midi-display-label", text: "Track" }),
                        new TVStaticText({ tag: "span", className: "tv-midi-track-number", attrs: { "data-tv-midi-track-number": true }, text: "01" }),
                        new TVStaticText({ tag: "span", className: "tv-midi-display-time", attrs: { "data-tv-midi-time": true }, text: "0:00 / 0:00" }),
                    ],
                }),
                new TVStaticText({ className: "tv-midi-display-title", attrs: { "data-tv-midi-display-title": true } }),
                new TVStaticText({ className: "tv-midi-status", attrs: { "data-tv-midi-status": true }, text: "Ready." }),
            ],
        });
        const meter = new TVGroup({
            className: "tv-midi-meter",
            children: [
                new TVStaticText({ tag: "span", className: "tv-midi-meter-fill", attrs: { "data-tv-midi-meter": true } }),
            ],
        });
        const externalSource = new TVGroup({
            className: "tv-midi-external",
            attrs: { "data-tv-midi-advanced": true, hidden: true },
            children: [
                new TVGroup({
                    className: "tv-midi-url-row",
                    children: [
                        new TVStaticText({ tag: "label", className: "tv-midi-url-label", attrs: { for: "tv-midi-url-input" }, text: "URL" }),
                        new TVInputLine({
                            className: "tv-midi-url-input",
                            attrs: {
                                id: "tv-midi-url-input",
                                "data-tv-midi-url": true,
                                spellcheck: "false",
                                placeholder: "https://example.com/song.mid",
                            },
                        }),
                        new TVButton({
                            dialog: false,
                            className: "tv-midi-url-load",
                            attrs: { "data-tv-midi-load-url": true },
                            label: "Load",
                        }),
                    ],
                }),
                new TVGroup({
                    className: "tv-midi-source-presets",
                    html: sourceButtons,
                }),
            ],
        });
        const trackList = TVVerticalListViewer.renderMarkup({
            rootClass: "tv-midi-track-list",
            rootAttrs: { "data-tv-midi-track-list": true },
            viewportClass: "tv-midi-track-viewport",
            scrollbarClass: "tv-midi-list-scrollbar",
            arrowClass: "tv-midi-list-arrow",
            trackClass: "tv-midi-list-track",
            cellsClass: "tv-midi-list-cells",
            thumbClass: "tv-midi-list-thumb",
        });
        const main = new TVGroup({
            className: "tv-midi-main",
            attrs: { "data-tv-midi-main": true },
            children: [display, meter, buttons, trackList, externalSource],
        }).renderMarkup();
        super({
            desktop,
            ariaLabel: "MIDI Player",
            title: "CD/MIDI Player",
            bodyClass: "tv-midi-body",
            closeAttrs: {
                "data-tv-midi-close": true,
                "aria-label": "Close MIDI player",
            },
            bodyMarkup: main,
            footerMarkup: TVDialog.footerMarkup(),
            width: "58ch",
            height: "min(23em, calc(100% - 2em))",
            left: "4ch",
            top: "3em",
        });
        this.selectedIndex = 0;
        this.cache = new Map();
        this.loadSerial = 0;
        this.isPlaying = false;
        this.synth = new TVMidiSynth();
        this.trackNumber = this.query("[data-tv-midi-track-number]");
        this.displayTitle = this.query("[data-tv-midi-display-title]");
        this.time = this.query("[data-tv-midi-time]");
        this.status = this.query("[data-tv-midi-status]");
        this.meter = this.query("[data-tv-midi-meter]");
        this.previousButton = this.query("[data-tv-midi-previous]");
        this.playButton = this.query("[data-tv-midi-play]");
        this.pauseButton = this.query("[data-tv-midi-pause]");
        this.stopButton = this.query("[data-tv-midi-stop]");
        this.nextButton = this.query("[data-tv-midi-next]");
        this.moreButton = this.query("[data-tv-midi-more]");
        this.closeActionButton = this.query("[data-tv-midi-close-button]");
        this.main = this.query("[data-tv-midi-main]");
        this.advanced = this.query("[data-tv-midi-advanced]");
        this.urlInput = this.query("[data-tv-midi-url]");
        this.loadUrlButton = this.query("[data-tv-midi-load-url]");
        this.sourceButtons = this.queryAll("[data-tv-midi-source]");
        this.trackListBox = new TVVerticalListViewer(this.query("[data-tv-midi-track-list]"), {
            itemClassName: "tv-midi-track",
            itemAttrName: "data-tv-midi-track",
            renderItemMarkup: (track, index, selected) => `
                <button type="button" class="tv-midi-track${selected ? " is-selected" : ""}" data-tv-midi-track="${index}">
                    <span class="tv-midi-track-index">${String(index + 1).padStart(2, "0")}</span>
                    <span class="tv-midi-track-title">${escapeHtml(track.title)}</span>
                    <span class="tv-midi-track-credit">${escapeHtml(track.credit)}</span>
                </button>
            `,
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.trackListBox.setItems(TV_MIDI_LIBRARY, this.selectedIndex);
        this.updateDisplay();
    }

    bind() {
        this.trackListBox.bind({
            onSelect: (_track, index) => this.selectTrack(index),
            onActivate: (_track, index) => {
                this.selectTrack(index);
                this.playSelected();
            },
        });
        if (this.previousButton) {
            this.previousButton.addEventListener("click", () => this.previousTrack());
        }
        if (this.playButton) {
            this.playButton.addEventListener("click", () => this.playSelected());
        }
        if (this.pauseButton) {
            this.pauseButton.addEventListener("click", () => this.pausePlayback());
        }
        if (this.stopButton) {
            this.stopButton.addEventListener("click", () => this.stopPlayback());
        }
        if (this.nextButton) {
            this.nextButton.addEventListener("click", () => this.nextTrack());
        }
        if (this.moreButton) {
            this.moreButton.addEventListener("click", () => this.toggleAdvanced());
        }
        if (this.closeActionButton) {
            this.closeActionButton.addEventListener("click", () => this.close());
        }
        if (this.loadUrlButton) {
            this.loadUrlButton.addEventListener("click", () => this.playExternalUrl());
        }
        if (this.urlInput) {
            this.urlInput.addEventListener("keydown", (event) => {
                if (event.key === "Enter") {
                    event.preventDefault();
                    this.playExternalUrl();
                }
            });
        }
        this.sourceButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const index = Number.parseInt(button.getAttribute("data-tv-midi-source"), 10);
                this.playExternalPreset(index);
            });
        });
    }

    close() {
        this.stopPlayback();
        super.close();
    }

    toggleAdvanced() {
        if (!this.advanced) {
            return;
        }
        const expanded = this.advanced.hidden;
        this.advanced.hidden = !expanded;
        this.main?.classList.toggle("is-advanced", expanded);
        this.moreButton?.setAttribute("aria-expanded", expanded ? "true" : "false");
        if (this.moreButton) {
            this.moreButton.textContent = expanded ? "Less" : "More";
        }
        this.setSize({
            height: expanded ? "min(27em, calc(100% - 2em))" : "min(23em, calc(100% - 2em))",
        });
        this.trackListBox.updateScrollbar();
    }

    selectTrack(index) {
        if (!Number.isInteger(index) || index < 0 || index >= TV_MIDI_LIBRARY.length) {
            return;
        }
        this.selectedIndex = index;
        this.trackListBox.select(index);
        this.updateDisplay();
    }

    previousTrack() {
        const nextIndex = (this.selectedIndex - 1 + TV_MIDI_LIBRARY.length) % TV_MIDI_LIBRARY.length;
        this.selectTrack(nextIndex);
        if (this.isPlaying) {
            this.playSelected();
        }
    }

    nextTrack() {
        const nextIndex = (this.selectedIndex + 1) % TV_MIDI_LIBRARY.length;
        this.selectTrack(nextIndex);
        if (this.isPlaying) {
            this.playSelected();
        }
    }

    selectedTrack() {
        return TV_MIDI_LIBRARY[this.selectedIndex] || TV_MIDI_LIBRARY[0];
    }

    updateDisplay() {
        const track = this.selectedTrack();
        this.updateTrackDisplay(track, String(this.selectedIndex + 1).padStart(2, "0"));
        this.updateProgress(0, 0, { status: false });
    }

    updateTrackDisplay(track, number) {
        if (this.trackNumber) {
            this.trackNumber.textContent = number;
        }
        if (this.displayTitle) {
            this.displayTitle.textContent = track.title;
        }
        if (this.time) {
            this.time.textContent = "0:00 / 0:00";
        }
    }

    async loadTrack(track) {
        if (this.cache.has(track.file)) {
            return this.cache.get(track.file);
        }
        let response;
        try {
            response = await fetch(track.file);
        } catch (error) {
            if (track.external) {
                throw new Error("Cannot load external source. The server may block browser CORS.");
            }
            throw error;
        }
        if (!response.ok) {
            throw new Error(`Cannot load ${track.file} (${response.status}).`);
        }
        const contentType = response.headers.get("content-type") || "";
        if (track.external && !looksLikeMidiUrl(response.url || track.file) && !/midi|audio\/|octet-stream/i.test(contentType)) {
            let midiUrl = "";
            try {
                midiUrl = extractMidiUrlFromHtml(await response.text(), response.url || track.file);
            } catch {
                throw new Error("Cannot read external page. The server may block browser CORS.");
            }
            if (!midiUrl) {
                throw new Error("No MIDI download link found on the external page.");
            }
            let midiResponse;
            try {
                midiResponse = await fetch(midiUrl);
            } catch {
                throw new Error("Cannot load MIDI link from external page. The server may block browser CORS.");
            }
            if (!midiResponse.ok) {
                throw new Error(`Cannot load ${midiUrl} (${midiResponse.status}).`);
            }
            response = midiResponse;
        }
        let sequence;
        try {
            sequence = parseMidiFile(await response.arrayBuffer());
        } catch (error) {
            if (track.external) {
                throw new Error(`External source is not a playable MIDI file: ${error.message}`);
            }
            throw error;
        }
        this.cache.set(track.file, sequence);
        return sequence;
    }

    async playSelected() {
        const track = this.selectedTrack();
        this.trackListBox.select(this.selectedIndex);
        await this.playTrack(track, String(this.selectedIndex + 1).padStart(2, "0"));
    }

    playExternalUrl() {
        let file;
        try {
            file = normalizeMidiUrl(this.urlInput ? this.urlInput.value : "");
        } catch (error) {
            this.setStatus(error && error.message ? error.message : "Invalid MIDI URL.");
            return;
        }
        this.playExternalTrack({
            title: titleFromMidiUrl(file),
            file,
            credit: "External URL",
            external: true,
        });
    }

    playExternalPreset(index) {
        const source = TV_MIDI_EXTERNAL_SOURCES[index];
        if (!source) {
            return;
        }
        if (this.urlInput) {
            this.urlInput.value = source.file;
        }
        this.playExternalTrack(source);
    }

    playExternalTrack(track) {
        this.trackListBox.select(-1);
        this.playTrack(track, "URL");
    }

    async playTrack(track, number) {
        const serial = ++this.loadSerial;
        this.updateTrackDisplay(track, number);
        this.setStatus(`Loading ${track.title}...`);
        this.updateProgress(0, 0, { status: false });
        if (this.playButton) {
            this.playButton.disabled = true;
        }
        try {
            const sequence = await this.loadTrack(track);
            if (serial !== this.loadSerial) {
                return;
            }
            await this.synth.play(
                sequence,
                (elapsed, duration) => this.updateProgress(elapsed, duration),
                () => {
                    this.isPlaying = false;
                    this.setStatus(`Finished ${track.title}.`);
                },
            );
            this.isPlaying = true;
            this.setStatus(`Playing ${track.title} (${formatMidiTime(sequence.duration)}).`);
        } catch (error) {
            this.isPlaying = false;
            this.setStatus(error && error.message ? error.message : "MIDI playback failed.");
        } finally {
            if (this.playButton) {
                this.playButton.disabled = false;
            }
        }
    }

    pausePlayback() {
        this.loadSerial += 1;
        this.isPlaying = false;
        this.synth.stop();
        this.setStatus("Paused.");
    }

    stopPlayback(message = "Stopped.") {
        this.loadSerial += 1;
        this.isPlaying = false;
        this.synth.stop();
        this.updateProgress(0, 0, { status: false });
        this.setStatus(message);
    }

    updateProgress(elapsed, duration, { status = true } = {}) {
        if (this.meter) {
            const ratio = duration > 0 ? Math.max(0, Math.min(1, elapsed / duration)) : 0;
            this.meter.style.width = `${Math.round(ratio * 100)}%`;
        }
        if (this.time) {
            this.time.textContent = `${formatMidiTime(elapsed)} / ${formatMidiTime(duration)}`;
        }
        if (status && duration > 0) {
            this.setStatus(`Playing ${formatMidiTime(elapsed)} / ${formatMidiTime(duration)}.`);
        }
    }

    setStatus(message) {
        if (this.status) {
            this.status.textContent = message;
        }
    }
}

class TVSearchDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const okButton = new TVButton({
            className: "is-default",
            attrs: { "data-tv-search-ok": true },
            label: '~O~K',
        });
        const cancelButton = new TVButton({
            attrs: { "data-tv-search-cancel": true },
            label: '~C~ancel',
        });
        const buttonStrip = new TVButtonStrip({
            className: "tv-search-buttons",
            buttons: [okButton, cancelButton],
        });
        const searchMain = new TVGroup({
            className: "tv-search-main",
            children: [
                new TVGroup({
                    tag: "label",
                    columns: "auto minmax(0,1fr)",
                    gap: "1ch",
                    align: "center",
                    children: [
                        new TVLabel({
                            text: "Find:",
                        }),
                        new TVInputLine({
                            attrs: {
                                spellcheck: "false",
                                autocomplete: "off",
                                "data-tv-search-input": true,
                            },
                        }),
                    ],
                }),
                new TVStaticText({
                    text: "Enter text and choose a topic.",
                }),
                new TVGroup({
                    className: "tv-search-results-panel",
                    children: [
                        TVVerticalListViewer.renderMarkup({
                            rootClass: "tv-search-results-scroll",
                            rootAttrs: { "data-tv-search-results": true },
                            viewportClass: "tv-search-results",
                        }),
                    ],
                }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Search help",
            title: "Find",
            bodyClass: "tv-search-body",
            closeAttrs: {
                "data-tv-search-close": true,
                "aria-label": "Close search",
            },
            bodyMarkup: `
                ${searchMain}
                ${buttonStrip.renderMarkup()}
            `,
            footerMarkup: TVDialog.footerMarkup(),
            width: "76ch",
            height: "min(26em, calc(100% - 2ch))",
            left: "2ch",
            top: "2em",
        });
        this.searchData = window.TV_SEARCH_INDEX && Array.isArray(window.TV_SEARCH_INDEX.topics)
            ? window.TV_SEARCH_INDEX
            : { topics: [] };
        this.input = this.query("[data-tv-search-input]");
        this.okButton = this.query("[data-tv-search-ok]");
        this.cancelButton = this.query("[data-tv-search-cancel]");
        this.resultsBox = new TVVerticalListViewer(this.query("[data-tv-search-results]"), {
            itemClassName: "tv-search-result",
            itemAttrName: "data-tv-search-index",
            renderItemMarkup: (entry, index, selected) => {
                const terms = entry.index_terms && entry.index_terms.length
                    ? `Index: ${entry.index_terms.slice(0, 4).join(", ")}`
                    : entry.title;
                return `
                    <button type="button" class="tv-search-result${selected ? " is-selected" : ""}" data-tv-search-index="${index}">
                        <span class="tv-search-result-title">${escapeHtml(entry.title)}</span>
                        <span class="tv-search-result-meta">${escapeHtml(terms)}</span>
                        <span class="tv-search-result-preview">${escapeHtml(entry.preview || entry.text.slice(0, 180))}</span>
                    </button>
                `;
            },
        });
        this.results = this.resultsBox.viewport;
        this.matches = [];
        this.selectedIndex = -1;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        if (!this.root) {
            return;
        }

        this.input.addEventListener("input", () => this.renderResults(this.input.value));
        this.resultsBox.bind({
            onSelect: (_entry, index) => {
                this.selectIndex(index);
            },
            onActivate: (_entry, index) => {
                this.selectIndex(index);
                this.openSelected();
            },
        });
        this.okButton.addEventListener("click", () => this.openSelected());
        this.cancelButton.addEventListener("click", () => this.close());
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    onKeyDown(event) {
        if (event.key === "F3") {
            event.preventDefault();
            if (this.isOpen()) {
                this.input.focus();
                this.input.select();
            } else {
                this.open("");
            }
            return;
        }
        if (event.key === "Escape" && this.isActive()) {
            event.preventDefault();
            this.close();
            return;
        }
        if (!this.isActive()) {
            return;
        }
        if (event.key === "Enter") {
            event.preventDefault();
            this.openSelected();
            return;
        }
        if (event.key === "ArrowDown") {
            event.preventDefault();
            this.moveSelection(1);
            return;
        }
        if (event.key === "ArrowUp") {
            event.preventDefault();
            this.moveSelection(-1);
        }
    }

    open(initialQuery = "") {
        super.open();
        if (typeof initialQuery === "string") {
            this.input.value = initialQuery;
        }
        this.renderResults(this.input.value);
        window.requestAnimationFrame(() => this.resultsBox.updateScrollbar());
        this.input.focus();
        this.input.select();
    }

    moveSelection(delta) {
        if (!this.matches.length) {
            return;
        }
        const next = this.selectedIndex < 0
            ? 0
            : Math.max(0, Math.min(this.matches.length - 1, this.selectedIndex + delta));
        this.selectIndex(next);
    }

    selectIndex(index) {
        if (!Number.isInteger(index) || index < 0 || index >= this.matches.length) {
            this.selectedIndex = -1;
            this.updateSelectionUi();
            return;
        }
        this.selectedIndex = index;
        this.updateSelectionUi();
    }

    updateSelectionUi() {
        this.resultsBox.select(this.selectedIndex);
        this.okButton.classList.toggle("is-active", this.selectedIndex >= 0);
    }

    openSelected() {
        if (this.selectedIndex < 0 || this.selectedIndex >= this.matches.length) {
            return;
        }
        window.location.href = this.matches[this.selectedIndex].href;
    }

    renderResults(query) {
        if (!this.results) {
            return;
        }
        this.matches = [];
        this.selectedIndex = -1;
        this.okButton.classList.remove("is-active");
        if (!this.searchData.topics.length) {
            this.results.innerHTML = "<div class=\"tv-search-empty\">Search index is not available for this help file.</div>";
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const trimmed = query.trim();
        if (!trimmed) {
            this.results.innerHTML = "<div class=\"tv-search-empty\">Type text to search across all generated topics.</div>";
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const matches = this.search(trimmed);
        if (!matches.length) {
            this.results.innerHTML = `<div class="tv-search-empty">No matches for "${escapeHtml(trimmed)}".</div>`;
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        this.matches = matches.slice(0, 60);
        this.resultsBox.setItems(this.matches, 0);
        this.selectIndex(0);
        fillBorders();
    }

    search(query) {
        const terms = normalizeSearchText(query).split(/\s+/).filter(Boolean);
        if (!terms.length) {
            return [];
        }

        const matches = [];
        outer: for (const entry of this.searchData.topics) {
            entry._titleNorm ||= normalizeSearchText(entry.title);
            entry._termsNorm ||= normalizeSearchText((entry.index_terms || []).join("\n"));
            entry._textNorm ||= normalizeSearchText(`${entry.preview || ""}\n${entry.text || ""}\n${entry.context_hex || ""}`);

            let score = 0;
            for (const term of terms) {
                if (entry._titleNorm.includes(term)) {
                    score += 12;
                    continue;
                }
                if (entry._termsNorm.includes(term)) {
                    score += 8;
                    continue;
                }
                if (entry._textNorm.includes(term)) {
                    score += 3;
                    continue;
                }
                continue outer;
            }
            matches.push({ ...entry, _score: score });
        }

        matches.sort((left, right) => {
            if (right._score !== left._score) {
                return right._score - left._score;
            }
            return left.context_id - right.context_id;
        });
        return matches;
    }
}


Object.assign(TV, {
    TVAboutDialog,
    TVWidgetGalleryDialog,
    TVFileOpenDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVCalendarDialog,
    TVColorsDialog,
    TVMidiPlayerDialog,
    TVSearchDialog,
});
})();
