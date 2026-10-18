// Separate package dialogs with a shared Turbo Vision layout and workflow.
(function () {
"use strict";
const TV = window.THelpViewerTV;
const { TVDialog, TVRect, TVGroup, TVLabel, TVInputLine, TVListBox, TVCheckBoxes,
    TVButton, TVInfoBox, TVInfoRow, TVMessageBox, messageBox, TVLoginDialog, TVRegistrationDialog,
    TVProgressDialog, bfDefault, evCommand, evBroadcast, evKeyDown, sfDisabled, sfModal, sfVisible,
    sbVertical, TVScrollBar, TVPoint, gfGrowLoX, gfGrowLoY, gfGrowHiX, gfGrowHiY,
    wrapTextLines, normalizeSearchText, TV_HELP_CONTEXTS } = TV;

function languageFlag(language) {
    const region = language?.split("-")[1] || ({ cs: "CZ", sk: "SK", en: "GB", de: "DE", fr: "FR", es: "ES",
        it: "IT", pl: "PL", ru: "RU", uk: "UA", pt: "PT", nl: "NL", hu: "HU", ja: "JP", zh: "CN" })[language];
    return /^[A-Z]{2}$/.test(region || "") ? Array.from(region, (letter) => String.fromCodePoint(0x1f1e6 + letter.charCodeAt(0) - 65)).join("") : "🌐";
}

class TVPackagesDialog extends TVDialog {
    constructor(bounds, title) {
        super(bounds, title);
        this.setState(sfModal, false);
        this.kind = this.constructor.packageKind;
        const midi = this.kind === "midi";
        const groupsRight = this.kind === "dos" ? 30 : 29;
        const right = this.size.x - 4;
        this.filterInput = new TVInputLine(new TVRect(11, 0, right, 1), 255);
        this.filterLabel = new TVLabel(new TVRect(2, 0, 11, 1), "~F~ilter:", this.filterInput);
        this.filterText = "";
        this.categories = new TVListBox(new TVRect(2, 2, groupsRight, midi ? 11 : 13));
        this.categories.hScrollBar = new TVScrollBar(new TVRect());
        this.items = new TVCheckBoxes(new TVRect(32, 2, right, 11));
        this.items.vScrollBar = new TVScrollBar(new TVRect(), sbVertical);
        this.items.hScrollBar = new TVScrollBar(new TVRect());
        this.categoryLabel = new TVLabel(new TVRect(2, 1, groupsRight, 2), "~G~roups", this.categories);
        this.itemLabel = new TVLabel(new TVRect(32, 1, right, 2), "~V~ersions", this.items);
        this.enabled = new TVCheckBoxes(new TVRect(2, 12, 29, 13));
        this.groupAll = new TVCheckBoxes(new TVRect(32, 12, right, 13), [{ label: "Selec~t~ / Deselect All" }]);
        this.descriptionRows = Array.from({ length: 3 }, (_item, row) => new TVInfoRow(new TVRect(0, row + 1, right - 4, row + 2)));
        this.descriptionBox = new TVInfoBox(new TVRect(2, 14, right, 19), "Description", this.descriptionRows);
        this.indexButton = new TVButton(new TVRect(47, 20, 64, 22), "~L~oad albums", "packages-index");
        this.selectAllButton = new TVButton(new TVRect(2, 20, midi ? 16 : 17, 22), "~S~elect All", "packages-all");
        this.deselectAllButton = new TVButton(new TVRect(midi ? 18 : 19, 20, midi ? 34 : 36, 22), "D~e~select All", "packages-none");
        this.applyButton = new TVButton(new TVRect(midi ? 36 : 38, 20, midi ? 45 : 48, 22), "~A~pply", "packages-apply", bfDefault);
        this.refreshButton = new TVButton(new TVRect(right - (midi ? 24 : 28), 20, right - (midi ? 13 : 15), 22), "~R~efresh", "packages-refresh");
        this.closeButtonView = new TVButton(new TVRect(right - (midi ? 11 : 13), 20, right, 22), "~C~lose", "packages-close");
        this.categories.growMode = gfGrowHiY;
        this.items.growMode = gfGrowHiX | gfGrowHiY;
        this.itemLabel.growMode = this.filterInput.growMode = gfGrowHiX;
        this.groupAll.growMode = this.descriptionBox.growMode = gfGrowHiX | gfGrowLoY | gfGrowHiY;
        for (const view of [this.enabled, this.indexButton, this.selectAllButton, this.deselectAllButton, this.applyButton]) {
            view.growMode = gfGrowLoY | gfGrowHiY;
        }
        this.refreshButton.growMode = this.closeButtonView.growMode = gfGrowLoX | gfGrowHiX | gfGrowLoY | gfGrowHiY;
        this.insert(new TVGroup(new TVRect(0, 0, this.size.x - 2, this.size.y - 2)).insertAll([
            this.filterLabel, this.filterInput, this.indexButton, this.categoryLabel, this.categories, this.itemLabel, this.items,
            this.enabled, this.groupAll, this.descriptionBox, this.selectAllButton, this.deselectAllButton, this.applyButton,
            this.refreshButton, this.closeButtonView,
        ]));
        this.draft = null; this.category = null;
        this.requestVersion = 0; this.submitting = false; this.valid = false;
        this.pollTask = null; this.indexTask = null;
        this.installing = false;
        this.onBeforeInstall = null; this.onInstalled = null; this.onMidiApplied = null;
        this.categories.bind({ onSelect: (item) => this.selectCategory(item?.id) });
        this.bindCommonClose(() => this.close()); this.bindDrag(); this.initControls();
    }

    open() {
        const wasOpen = this.isOpen(); super.open();
        if (!wasOpen) {
            this.draft = null; // Reopening reads receipts, not a failed installation draft.
            this.categories.newList([]); this.items.setItems([]);
            this.enabled.setItems([]); this.groupAll.setData(0);
            void this.loadChoices();
            this.filterInput.focus();
        }
    }
    close() { this.requestVersion += 1; super.close(); }

    changeBounds(bounds) {
        const delta = new TVPoint(bounds.width - this.size.x, bounds.height - this.size.y);
        super.changeBounds(bounds);
        if (this.content && (delta.x || delta.y)) {
            this.content.growTo(this.size.x - 2, this.size.y - 2);
            for (const view of this.content.children) {
                view.changeBounds(view.calcBounds(view.getBounds(), delta));
            }
            for (const row of this.descriptionRows) { row.growTo(this.descriptionBox.innerW, 1); }
            if (this.kind === "dos" && this.draft && delta.x) {
                for (const option of this.items.options) {
                    option.label = this.packageLabel(this.draft.packages.find((item) => item.id === option.id));
                }
                this.items.drawView();
            }
            this.descriptionBox.drawView();
            this.updateDescription();
            this.categories.updateScrollbar(); this.items.updateScrollbar();
        }
        return this;
    }

    async checkFirstRun() {
        const version = this.requestVersion;
        try {
            const data = await TVLoginDialog.request("/api/admin/content");
            if (!data.needs_setup) { return; }
            while (version === this.requestVersion && !this.destroyed) {
                const active = this.manager?.get(this.manager.activeTarget);
                if (!(active instanceof TVMessageBox || active instanceof TVLoginDialog
                    || active instanceof TVRegistrationDialog) || !active.isOpen()) { this.open(); return; }
                await new Promise((resolve) => setTimeout(resolve, 100));
            }
        } catch { /* Standalone pages and signed-out sessions have no setup API. */ }
    }

    initControls() {
        const midi = this.kind === "midi";
        this.setHelpCtx(TV_HELP_CONTEXTS[{ help: "hcHelpPackages", dos: "hcDosPackages", midi: "hcMidiSources" }[this.kind]]);
        this.categoryLabel.setText(midi ? "~G~roups / Sources" : "~G~roups");
        this.itemLabel.setText(this.kind === "help" ? "~V~ersions / Guides" : midi ? "Albu~m~s" : "~P~ackages");
        for (const view of [this.enabled, this.indexButton]) { view.setState(sfVisible, midi); }
        this.updateButtons();
    }

    updateButtons() {
        this.applyButton.setState(sfDisabled, !this.valid || this.submitting || (this.kind === "midi" && Boolean(this.indexTask)));
        const empty = !this.valid || !(this.kind === "midi" ? this.draft?.sources.length : this.draft?.packages.length);
        this.selectAllButton.setState(sfDisabled, empty); this.deselectAllButton.setState(sfDisabled, empty);
        const source = this.draft?.sources?.find((item) => item.id === this.category);
        const optional = this.items.options.flatMap((item, index) => item.required ? [] : [index]);
        const futureAlbums = this.kind === "midi" && source && !this.filterText;
        this.indexButton.setState(sfDisabled, !this.valid || !source || source.indexed || Boolean(this.indexTask));
        this.groupAll.setState(sfDisabled, !this.valid || (!optional.length && !futureAlbums));
        this.groupAll.setData(futureAlbums && source.all_albums
            || optional.length > 0 && optional.every((index) => this.items.mark(index)) ? 1 : 0);
    }

    async loadChoices(preserveDraft = false) {
        if (preserveDraft) { this.rememberSelection(); }
        const version = ++this.requestVersion, kind = this.kind;
        this.valid = false; this.updateButtons();
        try {
            const data = await TVLoginDialog.request(kind === "midi" ? "/api/admin/midi-sources" : "/api/admin/content");
            if (version !== this.requestVersion || !this.isOpen() || kind !== this.kind) { return; }
            const old = preserveDraft ? this.draft : null;
            if (kind === "midi") {
                this.draft = this.midiDraft(data, old);
            } else {
                const field = kind === "help" ? "help_packages" : "dos_packages";
                const categories = data[kind === "help" ? "help_categories" : "dos_categories"], packages = data[field];
                if (!Array.isArray(categories) || !Array.isArray(packages)
                    || packages.some((item) => !categories.some((category) => category.id === item.category))) {
                    throw new Error("Package configuration is unavailable. Restart the server after updating its code.");
                }
                this.draft = { packages, categories, selected: new Set((old ? [...old.selected] : data.selection[field])
                    .filter((id) => packages.some((item) => item.id === id))) };
                this.installing = data.status.scopes.includes(kind);
                if (data.status.state === "building") { void this.followProgress(data.status); }
            }
            this.renderDraft();
        } catch (error) { if (version === this.requestVersion && this.isOpen()) { this.showError(error); } }
    }

    midiDraft(data, previous) {
        const sources = data.sources.map((source) => {
            const prior = previous?.sources.find((item) => item.id === source.id);
            return prior ? { ...source, selected: prior.selected, all_albums: prior.all_albums,
                albums: source.albums.map((album) => ({ ...album, selected: prior.all_albums
                    || prior.albums.some((item) => item.id === album.id && item.selected) })) } : source;
        });
        return { sources, categories: sources.map((source) => ({ id: source.id, label: source.name })) };
    }

    renderDraft() {
        const draft = this.draft, category = this.category;
        for (const item of draft.packages || []) { if (item.required) { draft.selected.add(item.id); } }
        this.items.setItems([]); this.category = null;
        this.categories.newList(draft.categories.filter((item) => !this.filterText
            || normalizeSearchText(item.label).includes(this.filterText) || this.matchingItems(item.id).length));
        const index = this.categories.items.findIndex((item) => item.id === category);
        this.categories.select(index >= 0 ? index : 0); this.selectCategory(this.categories.selectedItem()?.id);
        this.valid = true; this.updateButtons();
    }

    matchingItems(category) {
        const draft = this.draft, group = draft?.categories.find((item) => item.id === category);
        const items = this.kind === "midi" ? draft?.sources.find((item) => item.id === category)?.albums || []
            : (draft?.packages || []).filter((item) => item.category === category);
        return items.filter((item) => !this.filterText || normalizeSearchText([
            group?.label, item.label, item.name, item.description,
        ].filter(Boolean).join(" ")).includes(this.filterText));
    }

    applyFilter() {
        this.filterText = normalizeSearchText(this.filterInput.getData().trim());
        if (!this.valid) { return; }
        this.rememberSelection(); this.renderDraft();
    }

    rememberSelection() {
        const draft = this.draft;
        if (!draft || !this.category) { return; }
        if (this.kind === "midi") {
            const source = draft.sources.find((item) => item.id === this.category);
            const selected = new Map(this.items.options.map((item, index) => [item.id, this.items.mark(index)]));
            if (source) { source.albums.forEach((album) => {
                if (selected.has(album.id)) { album.selected = selected.get(album.id); }
            }); }
        } else {
            this.items.options.forEach((item, index) => {
                if (item.required || this.items.mark(index)) { draft.selected.add(item.id); } else { draft.selected.delete(item.id); }
            });
        }
    }

    selectCategory(id) {
        this.rememberSelection(); this.category = id || null;
        const draft = this.draft;
        if (this.kind === "midi") {
            const source = draft?.sources.find((item) => item.id === this.category);
            this.enabled.setItems(source ? [{ label: "~E~nable source", checked: source.selected }] : []);
            this.items.setItems(this.matchingItems(this.category).map((album) => ({ ...album, label: album.name, checked: album.selected })));
        } else {
            this.items.setItems(this.matchingItems(this.category).map((item) => ({
                ...item, checked: item.required || draft.selected.has(item.id), disabled: Boolean(item.required),
                label: this.packageLabel(item),
            })));
        }
        this.updateDescription(); this.updateButtons();
    }

    packageLabel(item) {
        const name = item.label + (item.installed ? " *" : "");
        if (this.kind !== "dos") { return name; }
        // Reserve checkbox/space, scrollbar and three cells for emoji fallback fonts.
        const column = Math.max(this.items.size.x - 8,
            ...this.draft.packages.map((entry) => Array.from(entry.label).length + 3));
        return name + " ".repeat(Math.max(1, column - Array.from(name).length)) + languageFlag(item.language);
    }

    updateDescription() {
        const item = this.items.options[this.items.sel];
        const text = item ? (this.kind === "midi" ? item.name : item.description || "No description available.")
            : this.filterText ? "No matching packages or cached albums."
                : this.kind === "midi" ? "No cached albums. Use Load albums to read this source." : "No packages in this group.";
        const lines = text.split("\n").flatMap((line) => wrapTextLines(line, this.descriptionBox.innerW - 1));
        this.descriptionRows.forEach((row, index) => this.descriptionBox.updateRow(row, lines[index] || ""));
    }

    setGroupAll(all) {
        if (!this.valid) { return; }
        this.items.options.forEach((item) => { item.checked = all || Boolean(item.required); }); this.items.setItems(this.items.options);
        this.rememberSelection();
        if (this.kind === "midi") {
            const source = this.draft?.sources.find((item) => item.id === this.category);
            if (source) { source.all_albums = all && !this.filterText; }
        }
        this.updateButtons();
    }

    setAll(all) {
        if (!this.valid) { return; }
        this.rememberSelection();
        if (this.kind === "midi") {
            for (const source of this.draft.sources) {
                source.selected = all; source.all_albums = all;
                source.albums.forEach((album) => { album.selected = all; });
            }
        } else {
            this.draft.selected = new Set(this.draft.packages.filter((item) => all || item.required).map((item) => item.id));
        }
        // The draft now owns every group; don't write the old pane back over it.
        const category = this.category; this.category = null;
        this.selectCategory(category);
    }

    showError(error) {
        if (this.isOpen()) { void messageBox(this, { title: this.getTitle(), type: TVMessageBox.MF_ERROR, lines: [error.message] }); }
    }

    async applySelection() {
        if (this.kind !== "midi" && this.installing) { this.progress?.open(); return; }
        if (this.applyButton.state & sfDisabled) { return; }
        this.rememberSelection();
        const kind = this.kind, draft = this.draft, selection = {};
        if (kind === "midi") {
            selection.sources = draft.sources.filter((source) => source.selected).map((source) => source.id);
            selection.albums = Object.fromEntries(draft.sources.map((source) => [source.id,
                source.all_albums ? null : source.albums.filter((album) => album.selected).map((album) => album.id)]));
        } else {
            selection[kind === "help" ? "help_packages" : "dos_packages"] = [...draft.selected];
        }
        if (!this.isOpen()) { return; }
        this.submitting = true; this.updateButtons();
        try {
            if (kind === "dos") { await this.onBeforeInstall?.(); }
            const status = await TVLoginDialog.request(kind === "midi" ? "/api/admin/midi-sources" : "/api/admin/content",
                kind === "midi" ? "PUT" : "POST", selection);
            if (kind === "midi") { this.onMidiApplied?.(); } else {
                this.installing = status.scopes.includes(kind);
                void this.followProgress(status);
            }
        } catch (error) { this.showError(error); }
        finally { this.submitting = false; this.updateButtons(); }
    }

    followProgress(status) {
        if (this.pollTask) { return this.pollTask; }
        this.pollTask = this.pollProgress(status).finally(() => { this.pollTask = null; this.updateButtons(); });
        return this.pollTask;
    }

    async pollProgress(status) {
        this.progress = this.owner.owner.downloadProgress.showDialog(this.owner);
        try {
            while (!this.destroyed) {
                this.installing = status.scopes.includes(this.kind);
                this.progress.setOperation(status);
                if (status.state === "error") { throw new Error(status.error || "Content installation failed."); }
                if (status.state !== "building") {
                    await this.onInstalled?.();
                    if (this.isOpen() && this.kind !== "midi") { await this.loadChoices(true); }
                    if (status.warnings?.length) { this.showError(new Error(`${status.warnings.length} source warning(s): ${status.warnings[0]}`)); }
                    break;
                }
                await new Promise((resolve) => setTimeout(resolve, 1000));
                status = await TVLoginDialog.request("/api/admin/content/status");
            }
        } catch (error) { this.showError(error); }
        finally { this.progress.setOperation(null); }
    }

    loadAlbumIndex() {
        if (this.kind !== "midi" || this.indexButton.state & sfDisabled) { return; }
        this.indexTask = this.indexAlbums(this.category).finally(() => { this.indexTask = null; this.updateButtons(); });
        this.updateButtons();
    }

    async indexAlbums(provider) {
        const progress = new TVProgressDialog("Indexing MIDI Albums", "Reading source pages...");
        progress.setHelpCtx(TV_HELP_CONTEXTS.hcMidiSources);
        this.owner.insert(progress); this.owner.dialogManager.register("midi-source-progress", progress); progress.open();
        try {
            let status = await TVLoginDialog.request(`/api/admin/midi-sources/${encodeURIComponent(provider)}/index`, "POST");
            while (!this.destroyed) {
                progress.update(status);
                if (status.state === "error") { throw new Error(status.error || "Album indexing failed."); }
                if (!status.indexing) { break; }
                await new Promise((resolve) => setTimeout(resolve, 500));
                status = await TVLoginDialog.request("/api/admin/midi-sources/status");
            }
            if (this.isOpen()) {
                this.rememberSelection();
                const data = await TVLoginDialog.request("/api/admin/midi-sources");
                this.draft = this.midiDraft(data, this.draft);
                this.renderDraft();
            }
        } catch (error) { this.showError(error); }
        finally { progress.destroy(); }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evBroadcast) {
            if (event.infoPtr === this.filterInput && event.nativeEvent?.type === "input") {
                this.applyFilter();
            } else if (event.command === "cluster-press") {
                if (!this.valid) { this.clearEvent(event); return; }
                else if (event.infoPtr === this.items) {
                    this.rememberSelection();
                    if (this.kind === "midi") {
                        this.draft.sources.find((item) => item.id === this.category).all_albums = false;
                    }
                    this.updateDescription(); this.updateButtons();
                } else if (this.kind === "midi" && event.infoPtr === this.enabled) {
                    this.draft.sources.find((item) => item.id === this.category).selected = this.enabled.mark(0);
                } else if (event.infoPtr === this.groupAll) {
                    this.setGroupAll(this.groupAll.mark(0));
                } else { return; }
            } else if (event.command === "cluster-moved-to" && event.infoPtr === this.items) { this.updateDescription(); }
            else { return; }
        } else if (event.what === evKeyDown && event.infoPtr === this.filterInput
                && ["ArrowDown", "Enter"].includes(event.nativeEvent?.key)) {
            if (this.items.options.length) { this.items.focus(); }
            event.nativeEvent.preventDefault();
        } else if (event.what === evCommand) {
            switch (event.command) {
                case "packages-index": this.loadAlbumIndex(); break;
                case "packages-all": this.setAll(true); break;
                case "packages-none": this.setAll(false); break;
                case "packages-apply": void this.applySelection(); break;
                case "packages-refresh": void this.loadChoices(); break;
                case "packages-close": this.close(); break;
                default: return;
            }
        } else { return; }
        this.clearEvent(event);
    }
}

class TVHelpPackagesDialog extends TVPackagesDialog {
    static viewName = "help-packages";
    static packageKind = "help";
    constructor() { super(new TVRect(0, 0, 82, 24), "HELP Packages"); }
}

class TVDosPackagesDialog extends TVPackagesDialog {
    static viewName = "dos-packages";
    static packageKind = "dos";
    constructor() { super(new TVRect(0, 0, 90, 24), "DOS Packages"); }
}

class TVMidiSourcesDialog extends TVPackagesDialog {
    static viewName = "midi-sources";
    static packageKind = "midi";
    constructor() { super(new TVRect(0, 0, 94, 24), "MIDI Sources"); }
}

Object.assign(TV, { TVPackagesDialog, TVHelpPackagesDialog, TVDosPackagesDialog, TVMidiSourcesDialog });
})();
