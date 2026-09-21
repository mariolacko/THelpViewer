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
    TVFrame,
    TVWindow,
    TVDialog,
    TVRect,
    TVStaticText,
    TVLabel,
    TVInputLine,
    TVGroup,
    TVMarkupList,
    TVListViewer,
    TVListBox,
    TVVerticalListViewer,
    TVVerticalScrollArea,
    TVOutline,
    TVInfoBox,
    TVTerminal,
    TVButtonStrip,
    TVCheckBoxes,
    TVRadioButtons,
    TVMultiCheckBoxes,
    TVButton,
    bfDefault,
    TVMessageBox,
    normalizeSearchText,
    fillBorders,
    MONTH_NAMES,
    DAYS_IN_MONTH,
    isLeapYear,
    dayOfWeek,
    TV_HELP_CONTEXTS,
    normalizeHelpContext,
} = TV;

const {
    hcApplication,
    hcSystemMenu,
    hcHelpFiles,
    hcDocuments,
    hcSearch,
    hcGames,
    hcWindows,
    hcContextHelp,
    hcAbout,
    hcFileOpen,
    hcChangeDirectory,
    hcFind,
    hcColors,
    hcWidgetGallery,
    hcMidiPlayer,
    hcHelpViewer,
    hcDocumentViewer,
    hcDialog,
    hcCalendar,
    hcAsciiTable,
    hcCalculator,
    hcScreenSaver,
    hcPuzzle,
    hcTetris,
    hcMines,
    hcBreakOut,
    hcSokoban,
    hcLines,
    hcReversi,
    hcLudo,
    hcMastermind,
    hcSnake,
    hcHanoi,
    hcTron,
} = TV_HELP_CONTEXTS;

const TV_CONTEXT_HELP_TOPICS = Object.freeze({
    [hcApplication]: { title: "THelpViewer", text: "Use the menu bar to open HELP files, documentation, tools and games.\n\nF10 activates the menu bar. F1 opens help for the current view. F6 and Shift-F6 cycle windows." },
    [hcSystemMenu]: { title: "System menu", text: "The system menu contains About, utilities, Colors, Widget Gallery, screen savers and theme selection." },
    [hcHelpFiles]: { title: "Help Files", text: "Open installs a HELP or Docs file. Catalog submenus open a source directly. The viewer preserves links between related files when the target exists." },
    [hcDocuments]: { title: "Documents", text: "Documentation opens in a read-only Editor-style window. Use Ctrl-F to find text and Ctrl-L to find the next occurrence." },
    [hcSearch]: { title: "Search", text: "Find searches the active HELP or Docs window. Find Again repeats its query. Search Topics searches the current help bundle index." },
    [hcGames]: { title: "Games", text: "Games share Turbo Vision dialogs, keyboard focus, inactive-window pause policies and a ten-entry Hall of Fame." },
    [hcWindows]: { title: "Windows", text: "Tile, Cascade and Window List arrange managed windows. F5 zooms, F6 selects the next window and Alt-F3 closes the active target." },
    [hcContextHelp]: { title: "Context Help", text: "This is THelpViewer's own context-sensitive help. Each view and menu item carries an hc... identifier, following Turbo Vision's helpCtx model." },
    [hcAbout]: { title: "About", text: "Shows the application version and authors. The version is read from the running package metadata." },
    [hcFileOpen]: { title: "Open a File", text: "Choose a HELP or Docs file from the two-column list. The down-arrow opens recent files; press it again or Escape to close the history." },
    [hcChangeDirectory]: { title: "Change Directory", text: "Select a virtual HELP/DOCS directory. Chdir applies it to Open a File, Revert restores the initial path and the arrow opens directory history." },
    [hcFind]: { title: "Find", text: "Enter text to search in the active HELP or Docs window. The arrow opens previous queries." },
    [hcColors]: { title: "Colors", text: "Choose a group and item, then edit its DOS foreground/background attribute. Default restores one item; Reset All restores the complete palette." },
    [hcWidgetGallery]: { title: "Widget Gallery", text: "Exercises shared labels, inputs, lists, clusters, scrollbars, buttons, static text, terminal and message-box components." },
    [hcMidiPlayer]: { title: "CD/MIDI Player", text: "The compact view contains transport and track selection. More reveals advanced sources and resizes the shared dialog frame." },
    [hcHelpViewer]: { title: "HELP viewer", text: "Links open topics or external companion HELP files. Use Back, Index, Contents and Search from the status line or menus." },
    [hcDocumentViewer]: { title: "Document viewer", text: "Markdown is displayed with the read-only Editor palette. The lower-left indicator reports the current line and column." },
    [hcDialog]: { title: "Dialog", text: "Tab and Shift-Tab move focus. Enter activates the default button and Escape closes the dialog unless the control uses Escape itself." },
    [hcCalendar]: { title: "Calendar", text: "Browse months and years with the arrow controls. Date calculations use Gregorian leap-year rules." },
    [hcAsciiTable]: { title: "ASCII Table", text: "Shows character codes and glyphs using the configured DOS code page presentation." },
    [hcCalculator]: { title: "Calculator", text: "Use number and operation buttons or the keyboard. Escape is reserved by the calculator and does not close it." },
    [hcScreenSaver]: { title: "Screen saver", text: "Choose a mode from the system menu. Input stops the saver and restores the previously focused control." },
    [hcPuzzle]: { title: "Puzzle", text: "Move a tile next to the blank square with the mouse or arrow keys. Solve the shuffled 4 x 4 board in as few moves as possible." },
    [hcTetris]: { title: "Tetris", text: "New starts a game. Use Left/Right to move, Up to rotate, Down to drop faster and P to pause. Pentix toggles the extended pieces." },
    [hcMines]: { title: "Mines", text: "Reveal safe squares and mark suspected mines. The game pauses while its window is inactive." },
    [hcBreakOut]: { title: "BreakOut", text: "Move the paddle, keep the ball in play and clear the bricks. The game timer pauses while another window is active." },
    [hcSokoban]: { title: "Sokoban", text: "Push every crate onto a goal. Arrow keys move the player; crates can be pushed but not pulled." },
    [hcLines]: { title: "Lines", text: "Move coloured balls to form scoring lines. Selecting and moving a ball consumes a turn unless a line is completed." },
    [hcReversi]: { title: "Reversi", text: "Place a disc that brackets one or more opposing discs. The player with the most discs when no move remains wins." },
    [hcLudo]: { title: "Ludo", text: "Roll the die and move a legal piece around the board. Bring all of your pieces home before the other players." },
    [hcMastermind]: { title: "Mastermind", text: "Build a colour guess and submit it. Feedback reports correct colours in the correct and incorrect positions." },
    [hcSnake]: { title: "Snake", text: "Use the arrow keys to steer. Eat food to grow without hitting the wall or your own body." },
    [hcHanoi]: { title: "Tower of Hanoi", text: "Move the stack to another peg without placing a larger disc on a smaller one. Use mouse, keyboard and the move history." },
    [hcTron]: { title: "Tron Light Cycles", text: "Steer both cycles simultaneously and avoid every trail. The timer pauses while the game window is inactive." },
});

const TV_CONTEXT_HELP_BUNDLE_URL = "assets/tv-context-help.json?v=20260921b";
let contextHelpBundlePromise = null;

function loadContextHelpBundle() {
    if (!contextHelpBundlePromise) {
        contextHelpBundlePromise = fetch(TV_CONTEXT_HELP_BUNDLE_URL, { cache: "no-cache" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Context help request failed: ${response.status}`);
                }
                return response.json();
            })
            .then((bundle) => {
                if (!bundle || bundle.uhf_version !== "2.0" || !bundle.topics) {
                    throw new Error("Context help is not a UHF 2.0 bundle");
                }
                return bundle;
            });
    }
    return contextHelpBundlePromise;
}

function contextHelpTopic(bundle, helpCtx) {
    const direct = bundle?.topics?.[String(helpCtx)];
    if (direct) { return direct; }
    return Object.values(bundle?.topics || {}).find((topic) =>
        Array.isArray(topic?.aliases?.ids) && topic.aliases.ids.includes(helpCtx)
    ) || bundle?.topics?.[String(hcApplication)] || null;
}

function contextHelpTag(tagBody) {
    const lowered = tagBody.toLowerCase();
    if (lowered === "b") { return { name: "b", open: "<b>", close: "</b>", raw: tagBody }; }
    if (lowered === "i") { return { name: "i", open: "<i>", close: "</i>", raw: tagBody }; }
    if (lowered === "u") { return { name: "u", open: "<u>", close: "</u>", raw: tagBody }; }
    const link = tagBody.match(/^link:topic=(-?\d+)$/i);
    if (link) {
        return {
            name: "link",
            open: `<a href="#" data-tv-context-help-topic="${escapeHtml(link[1])}">`,
            close: "</a>",
            raw: tagBody,
        };
    }
    return null;
}

function renderContextHelpInline(text) {
    const root = { name: null, open: "", close: "", raw: "", children: [] };
    const stack = [root];
    const append = (fragment) => stack[stack.length - 1].children.push(fragment);
    let index = 0;
    while (index < text.length) {
        const open = text.indexOf("[", index);
        if (open < 0) {
            append(escapeHtml(text.slice(index)));
            break;
        }
        if (open > index) { append(escapeHtml(text.slice(index, open))); }
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
            const name = tagBody.slice(1).toLowerCase();
            if (stack.length > 1 && stack[stack.length - 1].name === name) {
                const node = stack.pop();
                append(node.open + node.children.join("") + node.close);
            } else {
                append(escapeHtml(text.slice(open, close + 1)));
            }
        } else {
            const descriptor = contextHelpTag(tagBody);
            if (descriptor) { stack.push({ ...descriptor, children: [] }); }
            else { append(escapeHtml(text.slice(open, close + 1))); }
        }
        index = close + 1;
    }
    while (stack.length > 1) {
        const node = stack.pop();
        stack[stack.length - 1].children.push(escapeHtml(`[${node.raw}]`) + node.children.join(""));
    }
    return root.children.join("");
}

function renderContextHelpTopic(topic) {
    const content = Array.isArray(topic?.content) ? topic.content : [];
    return content.map((line) => {
        const raw = String(line || "");
        if (raw === "[rule]") {
            return '<div class="tv-context-help-line tv-context-help-rule" aria-hidden="true"></div>';
        }
        return `<div class="tv-context-help-line">${raw ? renderContextHelpInline(raw) : "&nbsp;"}</div>`;
    }).join("");
}

class TVContextHelpDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const helpMain = new TVGroup({
            role: "context-help-main",
            children: [
                new TVStaticText({
                    textKind: "context-help-topic",
                    name: "context-help-heading",
                }),
                TVVerticalScrollArea.renderMarkup({
                    rootClass: "tv-context-help-scroll",
                    rootAttrs: { "data-tv-context-help-scroll": true },
                    viewportClass: "tv-context-help-viewport",
                    scrollbarClass: "tv-context-help-scrollbar",
                }),
                new TVGroup({
                    role: "context-help-nav",
                    children: [
                        new TVButton({
                            command: "context-help-back",
                            disabled: true,
                            labelMarkup: "◄ Back",
                        }),
                        new TVButton({
                            command: "context-help-contents",
                            labelMarkup: "Contents",
                        }),
                        new TVStaticText({ text: "F1 Help" }),
                    ],
                }),
            ],
        });
        super(new TVRect(0, 0, 72, 24), "THelpViewer Help", {
            desktop,
            viewName: "context-help",
            helpCtx: hcContextHelp,
            content: helpMain,
            modal: true,
            palette: "help",
            defaultButtonSelector: "",
        });
        this.headingElement = this.query("[data-tv-context-help-heading]");
        this.scrollArea = new TVVerticalScrollArea(this.query("[data-tv-context-help-scroll]"));
        this.viewport = this.scrollArea.viewport;
        if (this.viewport) { this.viewport.tabIndex = 0; }
        this.backButton = this.query("[data-tv-context-help-back]");
        this.contentsButton = this.query("[data-tv-context-help-contents]");
        this.context = hcApplication;
        this.bundle = null;
        this.topicHistory = [];
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.viewport?.addEventListener("click", (event) => {
            const link = event.target.closest("[data-tv-context-help-topic]");
            if (!link || !this.viewport.contains(link)) { return; }
            event.preventDefault();
            this.showTopic(link.dataset.tvContextHelpTopic, { remember: true });
        });
        this.backButton?.addEventListener("click", () => this.goBack());
        this.contentsButton?.addEventListener("click", () => this.showTopic(hcApplication, { remember: true }));
    }

    fallbackTopic(helpCtx) {
        const fallback = TV_CONTEXT_HELP_TOPICS[helpCtx] || TV_CONTEXT_HELP_TOPICS[hcApplication];
        return {
            id: helpCtx,
            title: fallback.title,
            content: fallback.text.split("\n"),
        };
    }

    showTopic(helpCtx, { remember = false } = {}) {
        const context = normalizeHelpContext(helpCtx, hcApplication);
        if (remember && this.context !== context) { this.topicHistory.push(this.context); }
        this.context = context;
        const topic = contextHelpTopic(this.bundle, context) || this.fallbackTopic(context);
        if (this.headingElement) { this.headingElement.textContent = topic.title || "Help"; }
        if (this.viewport) {
            this.viewport.innerHTML = renderContextHelpTopic(topic);
            this.viewport.scrollTop = 0;
        }
        if (this.backButton) { this.backButton.disabled = this.topicHistory.length === 0; }
        window.requestAnimationFrame(() => this.scrollArea?.update());
    }

    goBack() {
        const previous = this.topicHistory.pop();
        if (previous == null) { return; }
        this.showTopic(previous);
    }

    open() {
        this.topicHistory = [];
        this.showTopic(this.context);
        super.open();
        this.viewport?.focus();
        void loadContextHelpBundle()
            .then((bundle) => {
                this.bundle = bundle;
                this.showTopic(this.context);
            })
            .catch((error) => {
                console.error("Failed to load context help bundle", error);
            });
    }

    openContext(helpCtx = hcApplication) {
        this.context = normalizeHelpContext(helpCtx, hcApplication);
        this.open();
    }

    captureUrlState() {
        return { topic: this.context };
    }

    restoreUrlState(state) {
        this.context = normalizeHelpContext(state?.topic, hcApplication);
        this.topicHistory = [];
        this.showTopic(this.context);
    }

    destroy() {
        this.scrollArea?.destroy();
        this.scrollArea = null;
        super.destroy();
    }
}

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
                new TVButton({ x: 9, y: 9, w: 10, flags: bfDefault, command: "about-ok", label: '~O~K' }),
            ],
        });

        super(new TVRect(0, 0, 32, 13), "About", {
            desktop,
            viewName: "about",
            helpCtx: hcAbout,
            content: aboutMain,
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
        const multiChecks = new TVMultiCheckBoxes({
            attrs: { "data-tv-gallery-multichecks": true },
            options: [
                { label: "~O~ff / On / Auto", value: "mode", state: 0 },
                { label: "~R~ead / Write / Both", value: "access", state: 1 },
                { label: "D~i~sabled", value: "disabled", state: 2, disabled: true },
            ],
        });
        const staticText = new TVStaticText({
            text: "Static text · label hotkeys · disabled states",
            name: "gallery-static",
        });
        const terminal = new TVTerminal({
            attrs: { "data-tv-gallery-terminal": true },
            width: 28,
            rows: 3,
            maxLines: 50,
        });
        const infoBox = new TVInfoBox({
            title: "Event log",
            name: "gallery-status",
            w: 30,
            children: [terminal],
        });
        const buttons = new TVButtonStrip({
            className: "tv-widget-gallery-buttons",
            buttons: [
                new TVButton({
                    flags: bfDefault,
                    command: "gallery-ok",
                    label: "~O~K",
                }),
                new TVButton({
                    command: "gallery-apply",
                    label: "~A~pply",
                }),
                new TVButton({
                    command: "gallery-message",
                    label: "~M~essage",
                }),
                new TVButton({
                    command: "gallery-clear-log",
                    label: "C~l~ear log",
                }),
                new TVButton({
                    disabled: true,
                    label: "Disabled",
                }),
            ],
        });
        const galleryPanel = (heading, child, role = "") => new TVGroup({
            tag: "section",
            role: ["widget-gallery-panel", role].filter(Boolean).join(" "),
            children: [
                new TVStaticText({
                    textKind: "widget-gallery-heading",
                    text: heading,
                }),
                child,
            ],
        });
        const galleryMain = new TVGroup({
            role: "widget-gallery-main",
            children: [
                new TVGroup({
                    role: "widget-gallery-field",
                    children: [nameLabel, nameInput],
                }),
                new TVGroup({
                    role: "widget-gallery-samples",
                    children: [
                        galleryPanel("Check boxes", checks),
                        galleryPanel("Radio buttons", radios),
                        galleryPanel("Multi check boxes", multiChecks),
                        galleryPanel(
                            "List viewer",
                            TVVerticalListViewer.renderMarkup({
                                rootClass: "tv-widget-gallery-listviewer",
                                rootAttrs: { "data-tv-gallery-list": true },
                                viewportClass: "tv-widget-gallery-list",
                            }),
                        ),
                        galleryPanel("Info box", infoBox, "widget-gallery-info"),
                        galleryPanel("Static text", staticText, "widget-gallery-static"),
                    ],
                }),
                buttons,
            ],
        });

        super(new TVRect(0, 0, 68, 29), "Widget Gallery", {
            desktop,
            viewName: "widget-gallery",
            helpCtx: hcWidgetGallery,
            content: galleryMain,
        });
        this.nameInput = this.query("[data-tv-gallery-name]");
        this.checks = this.query("[data-tv-gallery-checks]");
        this.radios = this.query("[data-tv-gallery-radios]");
        this.multiChecks = multiChecks.bind(
            this.query("[data-tv-gallery-multichecks]"),
            (option, state) => this.setStatus(`${option.value}: state ${state}`),
        );
        this.okButton = this.query("[data-tv-gallery-ok]");
        this.applyButton = this.query("[data-tv-gallery-apply]");
        this.messageButton = this.query("[data-tv-gallery-message]");
        this.clearLogButton = this.query("[data-tv-gallery-clear-log]");
        this.infoBox = infoBox.resolve(this.dialog);
        this.terminal = terminal.bind(this.query("[data-tv-gallery-terminal]"));
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
            "TMultiCheckBoxes",
            "TTerminal",
            "THistory",
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
        if (this.clearLogButton) {
            this.clearLogButton.addEventListener("click", () => this.terminal.clear());
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
        this.terminal.append(message);
    }
}

function normalizeFileDialogEntries(entries = []) {
    return entries.map((entry) => {
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
}

class TVHistory {
    constructor(storageKey, maxItems = 10) {
        this.storageKey = storageKey;
        this.maxItems = maxItems;
    }

    keys() {
        try {
            const stored = JSON.parse(window.localStorage.getItem(this.storageKey) || "[]");
            return Array.isArray(stored)
                ? stored.filter((key) => typeof key === "string").slice(0, this.maxItems)
                : [];
        } catch {
            return [];
        }
    }

    entries(items, keyFor = (item) => item.historyKey) {
        const byKey = new Map(items.map((item) => [keyFor(item), item]));
        return this.keys().map((key) => byKey.get(key)).filter(Boolean);
    }

    remember(key) {
        if (!key) { return; }
        const keys = [key, ...this.keys().filter((item) => item !== key)].slice(0, this.maxItems);
        try {
            window.localStorage.setItem(this.storageKey, JSON.stringify(keys));
        } catch {
            // Storage may be unavailable under restrictive file:// environments.
        }
    }
}

class TVHistoryViewer extends TVVerticalListViewer {}

class TVHistoryWindow extends TVWindow {
    static triggerMarkup({ name = "", ariaLabel = "History" } = {}) {
        return new TVButton({
            command: name,
            ariaLabel,
            ariaExpanded: false,
            disabled: true,
            labelMarkup: [
                '<span class="tv-file-open-history-side" aria-hidden="true">▐</span>',
                '<span class="tv-file-open-history-arrow" aria-hidden="true">↓</span>',
                '<span class="tv-file-open-history-side" aria-hidden="true">▌</span>',
            ].join(""),
        }).renderMarkup();
    }

    static renderMarkup({ popupRole = "", popupName = "", listAttrs = {} } = {}) {
        const viewerMarkup = TVVerticalListViewer.renderMarkup({
            rootClass: "tv-file-open-history-listviewer",
            rootAttrs: listAttrs,
            viewportClass: "tv-file-open-history-list",
        });
        return new TVGroup({
            role: ["file-open-history-popup", "history-window", popupRole].filter(Boolean).join(" "),
            name: popupName,
            hidden: true,
            html: [
                '<div class="tv-history-frame-row tv-history-frame-top">',
                '<span class="tv-history-frame-corner" aria-hidden="true">╔</span>',
                '<span class="tv-history-frame-fill" data-tv-border-fill="═" aria-hidden="true"></span>',
                '<span class="tv-history-frame-corner" aria-hidden="true">╗</span>',
                TVFrame.titleControlMarkup({
                    className: "tv-history-close-control",
                    glyph: "■",
                    glyphClass: "tv-close-glyph",
                    attrs: {
                        "data-tv-history-close": true,
                        "aria-label": "Close history",
                    },
                }),
                '</div>',
                '<div class="tv-history-client">',
                '<span class="tv-history-frame-side" data-tv-border-side="║" aria-hidden="true"></span>',
                viewerMarkup,
                '</div>',
                '<div class="tv-history-frame-row tv-history-frame-bottom" aria-hidden="true">',
                '<span class="tv-history-frame-corner">╚</span>',
                '<span class="tv-history-frame-fill" data-tv-border-fill="═"></span>',
                '<span class="tv-history-frame-corner">╝</span>',
                '</div>',
            ].join(""),
        }).renderMarkup();
    }

    constructor({ button, popup, viewer, items = () => [], onSelect = null } = {}) {
        super(popup);
        this.button = button;
        this.popup = popup;
        this.viewer = viewer;
        this.closeButton = popup?.querySelector("[data-tv-history-close]") || null;
        this.items = items;
        this.onSelect = onSelect;
        this.ignoreNextClick = false;
        this.button?.addEventListener("mousedown", (event) => {
            if (event.button !== 0) { return; }
            event.preventDefault();
            this.ignoreNextClick = true;
            this.toggle();
        });
        this.button?.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") { this.ignoreNextClick = false; }
        });
        this.button?.addEventListener("click", () => {
            // Pointer activation is handled on mousedown, like Turbo Vision's
            // evMouseDown path. A click without mousedown is keyboard input.
            if (this.ignoreNextClick) {
                this.ignoreNextClick = false;
                return;
            }
            this.toggle();
        });
        this.closeButton?.addEventListener("mousedown", (event) => event.stopPropagation());
        this.closeButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.hide({ restoreFocus: true });
        });
        document.addEventListener("mousedown", (event) => {
            if (!this.isOpen()) { return; }
            if (this.button?.contains(event.target) || this.popup?.contains(event.target)) { return; }
            this.hide();
        });
        this.viewer?.bind({
            onSelect: (item) => this.onSelect?.(item, false),
            onActivate: (item) => this.onSelect?.(item, true),
        });
        this._setOpen(false);
    }

    refresh() {
        const items = this.items();
        this.viewer?.setItems(items, items.length ? 0 : -1);
        if (this.button) { this.button.disabled = false; }
        return items;
    }

    isOpen() {
        return Boolean(this.popup && !this.popup.hidden);
    }

    _setOpen(open) {
        if (this.popup) {
            this.popup.hidden = !open;
            this.popup.setAttribute("aria-hidden", open ? "false" : "true");
        }
        this.button?.setAttribute("aria-expanded", open ? "true" : "false");
    }

    show() {
        if (!this.popup) { return false; }
        const items = this.refresh();
        this._setOpen(true);
        fillBorders(this.popup);
        window.requestAnimationFrame(() => {
            this.viewer?.updateScrollbar();
            const focusTarget = this.viewer?.selectedElement() || this.closeButton;
            focusTarget?.focus();
        });
        return true;
    }

    toggle() {
        if (!this.popup) { return; }
        if (this.isOpen()) { this.hide(); }
        else { this.show(); }
    }

    hide({ restoreFocus = false } = {}) {
        this._setOpen(false);
        if (restoreFocus) { this.button?.focus(); }
    }

    handleEscape(event) {
        if (event.key !== "Escape" || !this.isOpen()) { return false; }
        event.preventDefault();
        event.stopPropagation();
        this.hide({ restoreFocus: true });
        return true;
    }
}

class TVFileList extends TVListBox {
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

const TVFileListBox = TVFileList;

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
            flags: bfDefault,
            command: "file-open-confirm",
            label: "~O~pen",
        });
        const cancelButton = new TVButton({
            command: "file-open-cancel",
            label: "Cancel",
        });
        const fileOpenMain = new TVGroup({
            role: "file-open-main",
            children: [
                new TVGroup({ role: "file-open-name-label", children: [nameLabel] }),
                new TVGroup({ role: "file-open-name-input", children: [nameInput] }),
                TVHistoryWindow.triggerMarkup({ name: "file-open-history" }),
                new TVGroup({ role: "file-open-files-label", children: [filesLabel] }),
                new TVGroup({
                    role: "file-open-file-list",
                    name: "file-open-files",
                }),
                new TVGroup({
                    role: "file-open-hscroll",
                    name: "file-open-hscroll",
                    ariaHidden: true,
                    children: [
                        new TVButton({
                            command: "file-open-scroll-left",
                            tabIndex: -1,
                            labelMarkup: escapeHtml(displayCp437Char(17)),
                        }),
                        new TVStaticText({ name: "file-open-scroll-track" }),
                        new TVButton({
                            command: "file-open-scroll-right",
                            tabIndex: -1,
                            labelMarkup: escapeHtml(displayCp437Char(16)),
                        }),
                    ],
                }),
                new TVGroup({ role: "file-open-open-button", children: [openButton] }),
                new TVGroup({ role: "file-open-cancel-button", children: [cancelButton] }),
                new TVGroup({
                    role: "file-open-info",
                    children: [
                        new TVStaticText({ name: "file-open-path" }),
                        new TVStaticText({ name: "file-open-detail" }),
                    ],
                }),
                TVHistoryWindow.renderMarkup({
                    popupName: "file-open-history-popup",
                    listAttrs: { "data-tv-file-open-history-list": true },
                }),
            ],
        });

        super(new TVRect(0, 0, 49, 19), "Open a File", {
            desktop,
            viewName: "file-open",
            helpCtx: hcFileOpen,
            content: fileOpenMain,
            modal: true,
        });
        this.entries = [];
        this.configured = false;
        this.currentDirectory = "";
        this.currentItems = [];
        this.onOpen = null;
        this.history = new TVHistory("thelp:file-open-history");
        this.nameInput = this.query("[data-tv-file-open-name]");
        this.pathLabel = this.query("[data-tv-file-open-path]");
        this.detailLabel = this.query("[data-tv-file-open-detail]");
        this.openButton = this.query("[data-tv-file-open-confirm]");
        this.cancelButton = this.query("[data-tv-file-open-cancel]");
        this.historyButton = this.query("[data-tv-file-open-history]");
        this.historyPopup = this.query("[data-tv-file-open-history-popup]");
        this.scrollTrack = this.query("[data-tv-file-open-scroll-track]");
        this.fileList = new TVFileList(this.query("[data-tv-file-open-files]"), {
            itemClassName: "tv-file-open-list-item",
            itemAttrName: "data-tv-file-open-file-index",
            renderItemContent: (item) => escapeHtml(item.label),
        });
        this.fileList.onViewportChange = () => this.updateHorizontalScrollbar();
        this.historyList = new TVHistoryViewer(this.query("[data-tv-file-open-history-list]"), {
            itemClassName: "tv-file-open-history-item",
            itemAttrName: "data-tv-file-open-history-index",
            renderItemContent: (entry) => escapeHtml(entry.virtualPath),
        });
        this.fileList.bind({
            onSelect: (item) => this.selectItem(item),
            onActivate: (item) => this.activateItem(item),
        });
        this.historyWindow = new TVHistoryWindow({
            button: this.historyButton,
            popup: this.historyPopup,
            viewer: this.historyList,
            items: () => this.historyEntries(),
            onSelect: (entry, activate) => this.selectHistory(entry, activate),
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindFileOpen();
    }

    configure(entries = [], onOpen = null) {
        this.entries = normalizeFileDialogEntries(entries);
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
        this.historyWindow.hide();
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
        if (this.historyWindow.handleEscape(event)) { return; }
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

    setDirectory(path) {
        const directory = String(path || "");
        if (!this.directoryExists(directory)) { return false; }
        this.currentDirectory = directory;
        this.refresh();
        return true;
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
        return this.history.keys();
    }

    historyEntries() {
        return this.history.entries(this.entries);
    }

    remember(entry) {
        this.history.remember(entry.historyKey);
    }

    updateHistoryState() {
        this.historyWindow.refresh();
    }

    toggleHistory() {
        this.historyWindow.toggle();
    }

    hideHistory() {
        this.historyWindow.hide();
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

class TVChangeDirectoryDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const directoryLabel = new TVLabel({
            text: "~D~irectory",
            hotkey: true,
            forId: "tv-change-dir-path",
        });
        const directoryInput = new TVInputLine({
            attrs: {
                id: "tv-change-dir-path",
                autocomplete: "off",
                spellcheck: "false",
                "data-tv-change-dir-path": true,
            },
        });
        const treeLabel = new TVLabel({ text: "Directory ~t~ree", hotkey: true });
        const changeButton = new TVButton({
            flags: bfDefault,
            command: "change-dir-confirm",
            label: "~C~hdir",
        });
        const revertButton = new TVButton({
            command: "change-dir-revert",
            label: "~R~evert",
        });
        const cancelButton = new TVButton({
            command: "change-dir-cancel",
            label: "Cancel",
        });
        const changeDirectoryMain = new TVGroup({
            role: "change-dir-main",
            children: [
                new TVGroup({ role: "change-dir-path-label", children: [directoryLabel] }),
                new TVGroup({ role: "change-dir-path-input", children: [directoryInput] }),
                TVHistoryWindow.triggerMarkup({
                    name: "change-dir-history",
                    ariaLabel: "Directory history",
                }),
                new TVGroup({ role: "change-dir-tree-label", children: [treeLabel] }),
                TVVerticalListViewer.renderMarkup({
                    rootClass: "tv-change-dir-listviewer",
                    rootAttrs: { "data-tv-change-dir-list": true },
                    viewportClass: "tv-change-dir-list",
                }),
                new TVGroup({ role: "change-dir-confirm-button", children: [changeButton] }),
                new TVGroup({ role: "change-dir-revert-button", children: [revertButton] }),
                new TVGroup({ role: "change-dir-cancel-button", children: [cancelButton] }),
                new TVStaticText({
                    textKind: "change-dir-detail",
                    name: "change-dir-detail",
                }),
                TVHistoryWindow.renderMarkup({
                    popupRole: "change-dir-history-popup",
                    popupName: "change-dir-history-popup",
                    listAttrs: { "data-tv-change-dir-history-list": true },
                }),
            ],
        });

        super(new TVRect(0, 0, 46, 18), "Change Directory", {
            desktop,
            viewName: "change-dir",
            helpCtx: hcChangeDirectory,
            content: changeDirectoryMain,
            modal: true,
        });
        this.entries = [];
        this.directories = [];
        this.directoryTree = [];
        this.currentDirectory = "";
        this.initialDirectory = "";
        this.onChange = null;
        this.history = new TVHistory("thelp:directory-history");
        this.pathInput = this.query("[data-tv-change-dir-path]");
        this.detail = this.query("[data-tv-change-dir-detail]");
        this.changeButton = this.query("[data-tv-change-dir-confirm]");
        this.revertButton = this.query("[data-tv-change-dir-revert]");
        this.cancelButton = this.query("[data-tv-change-dir-cancel]");
        this.historyButton = this.query("[data-tv-change-dir-history]");
        this.historyPopup = this.query("[data-tv-change-dir-history-popup]");
        this.directoryList = new TVOutline(this.query("[data-tv-change-dir-list]"), {
            itemClassName: "tv-change-dir-item",
            itemAttrName: "data-tv-change-dir-index",
            getKey: (item) => item.path,
            getLabel: (item) => item.label,
        });
        this.historyList = new TVHistoryViewer(this.query("[data-tv-change-dir-history-list]"), {
            itemClassName: "tv-file-open-history-item",
            itemAttrName: "data-tv-change-dir-history-index",
            renderItemContent: (item) => escapeHtml(this.displayPath(item.path)),
        });
        this.directoryList.bind({
            onSelect: (item) => this.selectDirectory(item.path),
            onActivate: (item) => {
                this.selectDirectory(item.path);
                this.commit();
            },
        });
        this.historyWindow = new TVHistoryWindow({
            button: this.historyButton,
            popup: this.historyPopup,
            viewer: this.historyList,
            items: () => this.history.entries(this.directories),
            onSelect: (item, activate) => {
                this.selectDirectory(item.path);
                this.historyWindow.hide();
                if (activate) { this.commit(); }
                else { this.pathInput?.focus(); }
            },
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindChangeDirectory();
    }

    configure(entries = [], onChange = null) {
        this.entries = normalizeFileDialogEntries(entries);
        this.onChange = typeof onChange === "function" ? onChange : null;
        this.rebuildDirectories();
        this.setDirectory(this.currentDirectory);
    }

    rebuildDirectories() {
        const paths = new Set(["", "HELP", "DOCS"]);
        for (const entry of this.entries) {
            const parts = entry.directory.split("\\").filter(Boolean);
            for (let count = 1; count <= parts.length; count += 1) {
                paths.add(parts.slice(0, count).join("\\"));
            }
        }
        this.directories = Array.from(paths).sort((left, right) => {
            if (!left) { return -1; }
            if (!right) { return 1; }
            return left.localeCompare(right);
        }).map((path) => {
            const depth = path ? path.split("\\").length : 0;
            const name = path ? path.split("\\").pop() : "THelpViewer:";
            return {
                path,
                historyKey: path || ".",
                label: path ? `${"  ".repeat(depth - 1)}${name}\\` : "THelpViewer:\\",
            };
        });
        const byPath = new Map(this.directories.map((item) => [item.path, { ...item, children: [] }]));
        for (const item of byPath.values()) {
            if (!item.path) { continue; }
            const parts = item.path.split("\\");
            parts.pop();
            byPath.get(parts.join("\\"))?.children.push(item);
        }
        for (const item of byPath.values()) {
            item.label = item.path ? `${item.path.split("\\").pop()}\\` : "THelpViewer:\\";
            item.children.sort((left, right) => left.label.localeCompare(right.label));
        }
        this.directoryTree = byPath.has("") ? [byPath.get("")] : [];
        this.historyWindow.refresh();
    }

    bindChangeDirectory() {
        this.changeButton?.addEventListener("click", () => this.commit());
        this.revertButton?.addEventListener("click", () => this.setDirectory(this.initialDirectory));
        this.cancelButton?.addEventListener("click", () => this.close());
        this.pathInput?.addEventListener("change", () => this.selectInputPath());
        this.pathInput?.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                this.selectInputPath();
                this.commit();
            }
        });
        this.dialog.addEventListener("keydown", (event) => {
            if (!event.altKey || event.ctrlKey || event.metaKey) { return; }
            const key = event.key.toLowerCase();
            if (key === "d") {
                event.preventDefault();
                this.pathInput?.focus();
                this.pathInput?.select();
            } else if (key === "t") {
                event.preventDefault();
                this.directoryList.selectedElement()?.focus();
            } else if (key === "c") {
                event.preventDefault();
                this.commit();
            } else if (key === "r") {
                event.preventDefault();
                this.setDirectory(this.initialDirectory);
            }
        });
    }

    displayPath(path) {
        return `THelpViewer:\\${path ? `${path}\\` : ""}`;
    }

    normalizeInputPath(value) {
        return String(value || "")
            .replace(/^THelpViewer:/i, "")
            .replace(/[\\/]+/g, "\\")
            .replace(/^\\+|\\+$/g, "");
    }

    findDirectory(path) {
        const normalized = this.normalizeInputPath(path).toLocaleLowerCase();
        return this.directories.find((item) => item.path.toLocaleLowerCase() === normalized) || null;
    }

    setDirectory(path) {
        const item = this.findDirectory(path) || this.directories[0] || { path: "" };
        this.currentDirectory = item.path;
        this.directoryList.setTree(this.directoryTree, item.path, { expandAll: true });
        this.updatePath();
        return Boolean(item);
    }

    selectDirectory(path) {
        const item = this.findDirectory(path);
        if (!item) { return false; }
        this.currentDirectory = item.path;
        this.directoryList.selectKey(item.path);
        this.updatePath();
        return true;
    }

    selectInputPath() {
        const item = this.findDirectory(this.pathInput?.value || "");
        if (!item) {
            if (this.detail) { this.detail.textContent = "Directory does not exist"; }
            return false;
        }
        return this.selectDirectory(item.path);
    }

    updatePath() {
        if (this.pathInput) { this.pathInput.value = this.displayPath(this.currentDirectory); }
        if (this.detail) { this.detail.textContent = `${this.entries.filter((entry) => entry.directory === this.currentDirectory).length} files`; }
    }

    commit() {
        if (!this.selectInputPath()) { return; }
        const item = this.findDirectory(this.currentDirectory);
        this.history.remember(item?.historyKey);
        this.historyWindow.refresh();
        this.initialDirectory = this.currentDirectory;
        this.close();
        this.onChange?.(this.currentDirectory);
    }

    open() {
        this.historyWindow.hide();
        this.initialDirectory = this.currentDirectory;
        this.setDirectory(this.currentDirectory);
        super.open();
        window.requestAnimationFrame(() => {
            this.directoryList.updateScrollbar();
            this.pathInput?.focus();
            this.pathInput?.select();
        });
    }

    close() {
        this.historyWindow.hide();
        super.close();
    }

    onDialogKeyDown(event) {
        if (this.historyWindow.handleEscape(event)) { return; }
        super.onDialogKeyDown(event);
    }
}

class TVAsciiTableDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const chart = new TVMarkupList({
            className: "tv-ascii-chart",
            attrs: { "data-tv-ascii-chart": true },
        });
        const report = new TVStaticText({
            textKind: "ascii-report",
            name: "ascii-report",
        });
        super(new TVRect(0, 0, 34, 12), "ASCII Chart", {
            desktop,
            viewName: "ascii",
            helpCtx: hcAsciiTable,
            palette: "ascii",
            content: [chart, report],
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
            items.push(new TVButton({
                command: "ascii-code",
                value: code,
                commandData: { selected: Boolean(selected) },
                ariaLabel: `ASCII ${code}`,
                labelMarkup: escapeHtml(displayCp437Char(code)),
            }).renderMarkup());
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
        const buttons = buttonKeys.map(([key, label, aria]) =>
            new TVButton({
                command: "calc-key",
                value: key,
                ariaLabel: `Calculator key ${aria}`,
                labelMarkup: escapeHtml(label),
            })
        );
        const calcMain = new TVGroup({
            role: "calc-main",
            children: [
                new TVStaticText({
                    textKind: "calc-display",
                    name: "calc-display",
                }),
                new TVGroup({
                    role: "calc-keypad",
                    children: buttons,
                }),
            ],
        });

        super(new TVRect(0, 0, 24, 15), "Calculator", {
            desktop,
            viewName: "calc",
            helpCtx: hcCalculator,
            content: calcMain,
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
            role: "calendar-main",
            children: [
                new TVGroup({
                    role: "calendar-header",
                    children: [
                        new TVStaticText({
                            name: "calendar-caption",
                        }),
                        new TVButton({
                            command: "calendar-prev",
                            ariaLabel: "Previous month",
                            labelMarkup: escapeHtml(displayCp437Char(30)),
                        }),
                        new TVStaticText({
                            text: "  ",
                        }),
                        new TVButton({
                            command: "calendar-next",
                            ariaLabel: "Next month",
                            labelMarkup: escapeHtml(displayCp437Char(31)),
                        }),
                    ],
                }),
                new TVStaticText({
                    text: "Su Mo Tu We Th Fr Sa",
                }),
                new TVStaticText({
                    textKind: "calendar-grid",
                    name: "calendar-grid",
                }),
            ],
        });
        super(new TVRect(0, 0, 27, 11), "Calendar", {
            desktop,
            viewName: "calendar",
            helpCtx: hcCalendar,
            palette: "calendar",
            content: calendarMain,
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
                cells.push(new TVStaticText({
                    textKind: `calendar-cell${isToday ? " is-current" : ""}${!inMonth ? " is-empty" : ""}`,
                    text: inMonth ? String(current).padStart(2, " ") : "  ",
                }).renderMarkup());
                current += 1;
            }
        }
        this.grid.innerHTML = cells.join("");
    }
}

class TVColorsDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const okButton = new TVButton({
            flags: bfDefault,
            command: "colors-ok",
            label: 'O~K~',
        });
        const cancelButton = new TVButton({
            command: "colors-cancel",
            label: '~C~ancel',
        });
        const resetAllButton = new TVButton({
            command: "colors-reset-all",
            label: '~R~eset All',
        });
        const defaultButton = new TVButton({
            command: "colors-default",
            label: '~D~efault',
        });
        const buttonStrip = new TVButtonStrip({
            className: "tv-colors-dialog-buttons",
            buttons: [defaultButton, resetAllButton, okButton, cancelButton],
        });
        const groupTitle = new TVLabel({
            text: "~G~roup",
            hotkey: true,
            labelKind: "colors-group-label",
        });
        const itemTitle = new TVLabel({
            text: "~I~tem",
            hotkey: true,
            labelKind: "colors-item-label",
        });
        const fgTitle = new TVLabel({
            text: "~F~oreground",
            hotkey: true,
            labelKind: "colors-foreground-label",
        });
        const bgTitle = new TVLabel({
            text: "~B~ackground",
            hotkey: true,
            labelKind: "colors-background-label",
        });
        const colorsMain = new TVGroup({
            role: "colors-main",
            children: [
                groupTitle,
                TVVerticalListViewer.renderMarkup({
                    rootClass: "tv-colors-listviewer tv-colors-groups-listviewer",
                    rootAttrs: { "data-tv-colors-groups": true },
                    viewportClass: "tv-colors-list-viewport",
                }),
                itemTitle,
                TVVerticalListViewer.renderMarkup({
                    rootClass: "tv-colors-listviewer tv-colors-items-listviewer",
                    rootAttrs: { "data-tv-colors-items": true },
                    viewportClass: "tv-colors-list-viewport",
                }),
                fgTitle,
                new TVGroup({
                    role: "colors-selector colors-foreground",
                    name: "colors-foreground",
                }),
                bgTitle,
                new TVGroup({
                    role: "colors-selector colors-background is-background",
                    name: "colors-background",
                }),
                new TVGroup({
                    role: "colors-display",
                    name: "colors-display",
                }),
                buttonStrip,
            ],
        });
        super(new TVRect(0, 0, 61, 18), "Colors", {
            desktop,
            viewName: "colors",
            helpCtx: hcColors,
            content: colorsMain,
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
                ? escapeHtml(displayCp437Char(219))
                    + new TVMarkupList({
                        tag: "span",
                        className: "tv-color-cell-marker",
                        items: [escapeHtml(marker)],
                    }).renderMarkup()
                    + escapeHtml(displayCp437Char(219))
                : escapeHtml(icon);
            cells.push(new TVButton({
                command: "color-index",
                value: index,
                commandData: { selected: isSelected, color: DOS_COLORS[index] },
                ariaLabel: `Color ${index}`,
                ariaPressed: isSelected,
                tabIndex: isSelected ? 0 : -1,
                labelMarkup: content,
            }).renderMarkup());
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
        this.display.innerHTML = new TVStaticText({
            textKind: "colors-display-sample",
            text: "Text Text Text \nText Text Text ",
        }).renderMarkup();
        this.display.style.setProperty("--tv-colors-sample-fg", fg);
        this.display.style.setProperty("--tv-colors-sample-bg", bg);
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
            command: "midi-previous",
            tooltip: "Previous track",
            label: "◄◄",
        });
        const playButton = new TVButton({
            command: "midi-play",
            flags: bfDefault,
            label: "►",
        });
        const pauseButton = new TVButton({
            command: "midi-pause",
            tooltip: "Pause",
            label: "▌▌",
        });
        const stopButton = new TVButton({
            command: "midi-stop",
            label: "■",
        });
        const nextButton = new TVButton({
            command: "midi-next",
            tooltip: "Next track",
            label: "►►",
        });
        const moreButton = new TVButton({
            command: "midi-more",
            ariaExpanded: false,
            label: "More",
        });
        const closeButton = new TVButton({
            command: "midi-close-button",
            label: "Close",
        });
        const buttons = new TVButtonStrip({
            className: "tv-midi-buttons",
            buttons: [previousButton, playButton, pauseButton, stopButton, nextButton, moreButton, closeButton],
        });
        const sourceButtons = TV_MIDI_EXTERNAL_SOURCES.map((source, index) => new TVButton({
            command: "midi-source",
            value: index,
            tooltip: `${source.title} (${source.credit})`,
            labelMarkup: escapeHtml(source.label),
        }));
        const display = new TVGroup({
            role: "midi-display",
            children: [
                new TVGroup({
                    role: "midi-display-line",
                    children: [
                        new TVStaticText({ textKind: "midi-display-label", text: "Track" }),
                        new TVStaticText({ name: "midi-track-number", textKind: "midi-track-number", text: "01" }),
                        new TVStaticText({ name: "midi-time", textKind: "midi-display-time", text: "0:00 / 0:00" }),
                    ],
                }),
                new TVStaticText({ name: "midi-display-title", textKind: "midi-display-title" }),
                new TVStaticText({ name: "midi-status", textKind: "midi-status", text: "Ready." }),
            ],
        });
        const meter = new TVGroup({
            role: "midi-meter",
            children: [
                new TVStaticText({ name: "midi-meter", textKind: "midi-meter-fill" }),
            ],
        });
        const externalSource = new TVGroup({
            role: "midi-external",
            name: "midi-advanced",
            hidden: true,
            children: [
                new TVGroup({
                    role: "midi-url-row",
                    children: [
                        new TVLabel({ forId: "tv-midi-url-input", labelKind: "midi-url-label", text: "URL" }),
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
                            command: "midi-load-url",
                            label: "Load",
                        }),
                    ],
                }),
                new TVGroup({
                    role: "midi-source-presets",
                    children: sourceButtons,
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
            role: "midi-main",
            name: "midi-main",
            children: [display, meter, buttons, trackList, externalSource],
        });
        super(new TVRect(0, 0, 58, 23), "CD/MIDI Player", {
            desktop,
            viewName: "midi",
            helpCtx: hcMidiPlayer,
            content: main,
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
            renderItemMarkup: (track, index, selected) => new TVButton({
                command: "midi-track",
                value: index,
                commandData: { selected },
                labelMarkup: [
                    new TVMarkupList({
                        tag: "span",
                        className: "tv-midi-track-index",
                        items: [escapeHtml(String(index + 1).padStart(2, "0"))],
                    }),
                    new TVMarkupList({
                        tag: "span",
                        className: "tv-midi-track-title",
                        items: [escapeHtml(track.title)],
                    }),
                    new TVMarkupList({
                        tag: "span",
                        className: "tv-midi-track-credit",
                        items: [escapeHtml(track.credit)],
                    }),
                ].map((widget) => widget.renderMarkup()).join(""),
            }).renderMarkup(),
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

class TVFindDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const findLabel = new TVLabel({
            text: "~T~ext to find",
            hotkey: true,
            forId: "tv-find-text",
        });
        const findInput = new TVInputLine({
            attrs: {
                id: "tv-find-text",
                autocomplete: "off",
                spellcheck: "false",
                "data-tv-find-input": true,
            },
        });
        const findButton = new TVButton({
            flags: bfDefault,
            command: "find-confirm",
            label: "~F~ind",
        });
        const cancelButton = new TVButton({
            command: "find-cancel",
            label: "Cancel",
        });
        const findMain = new TVGroup({
            role: "find-main",
            children: [
                new TVGroup({ role: "find-label", children: [findLabel] }),
                new TVGroup({ role: "find-input", children: [findInput] }),
                TVHistoryWindow.triggerMarkup({
                    name: "find-history",
                    ariaLabel: "Find history",
                }),
                new TVGroup({ role: "find-confirm", children: [findButton] }),
                new TVGroup({ role: "find-cancel", children: [cancelButton] }),
                new TVStaticText({
                    textKind: "find-status",
                    name: "find-status",
                }),
                TVHistoryWindow.renderMarkup({
                    popupRole: "find-history-popup",
                    popupName: "find-history-popup",
                    listAttrs: { "data-tv-find-history-list": true },
                }),
            ],
        });
        super(new TVRect(0, 0, 49, 10), "Find", {
            desktop,
            viewName: "find",
            helpCtx: hcFind,
            content: findMain,
            modal: true,
        });
        this.history = new TVHistory("thelp:find-history");
        this.findHandler = null;
        this.findAgainHandler = null;
        this.targetLabel = "active window";
        this.input = this.query("[data-tv-find-input]");
        this.status = this.query("[data-tv-find-status]");
        this.findButton = this.query("[data-tv-find-confirm]");
        this.cancelButton = this.query("[data-tv-find-cancel]");
        this.historyButton = this.query("[data-tv-find-history]");
        this.historyPopup = this.query("[data-tv-find-history-popup]");
        this.historyList = new TVHistoryViewer(this.query("[data-tv-find-history-list]"), {
            itemClassName: "tv-file-open-history-item",
            itemAttrName: "data-tv-find-history-index",
            renderItemContent: (item) => escapeHtml(item.value),
        });
        this.historyWindow = new TVHistoryWindow({
            button: this.historyButton,
            popup: this.historyPopup,
            viewer: this.historyList,
            items: () => this.history.keys().map((value) => ({ historyKey: value, value })),
            onSelect: (item, activate) => {
                if (this.input) { this.input.value = item.value; }
                this.historyWindow.hide();
                if (activate) { this.performFind(); }
                else { this.input?.focus(); }
            },
        });
        this.findButton?.addEventListener("click", () => this.performFind());
        this.cancelButton?.addEventListener("click", () => this.close());
        this.input?.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                this.performFind();
            }
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    configure({ find = null, findAgain = null, targetLabel = "active window" } = {}) {
        this.findHandler = typeof find === "function" ? find : null;
        this.findAgainHandler = typeof findAgain === "function" ? findAgain : null;
        this.targetLabel = String(targetLabel || "active window");
        this.historyWindow.refresh();
    }

    open(initialQuery = "") {
        this.historyWindow.hide();
        if (this.input && initialQuery) { this.input.value = initialQuery; }
        if (this.status) { this.status.textContent = `Find in ${this.targetLabel}`; }
        this.historyWindow.refresh();
        super.open();
        this.input?.focus();
        this.input?.select();
    }

    performFind() {
        const query = String(this.input?.value || "").trim();
        if (!query || !this.findHandler) {
            if (this.status) { this.status.textContent = "Enter text to find."; }
            return false;
        }
        this.history.remember(query);
        this.historyWindow.refresh();
        const found = Boolean(this.findHandler(query));
        if (this.status) {
            this.status.textContent = found ? `Found in ${this.targetLabel}` : `Text not found in ${this.targetLabel}`;
        }
        if (found) { this.close(); }
        return found;
    }

    findAgain() {
        return this.findAgainHandler ? Boolean(this.findAgainHandler()) : false;
    }

    close() {
        this.historyWindow.hide();
        super.close();
    }

    onDialogKeyDown(event) {
        if (this.historyWindow.handleEscape(event)) { return; }
        super.onDialogKeyDown(event);
    }
}

class TVSearchDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const okButton = new TVButton({
            flags: bfDefault,
            command: "search-ok",
            label: '~O~K',
        });
        const cancelButton = new TVButton({
            command: "search-cancel",
            label: '~C~ancel',
        });
        const buttonStrip = new TVButtonStrip({
            className: "tv-search-buttons",
            buttons: [okButton, cancelButton],
        });
        const searchMain = new TVGroup({
            role: "search-main",
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
                    role: "search-results-panel",
                    children: [
                        TVVerticalListViewer.renderMarkup({
                            rootClass: "tv-search-results-scroll",
                            rootAttrs: { "data-tv-search-results": true },
                            viewportClass: "tv-search-results",
                        }),
                    ],
                }),
            ],
        });

        super(new TVRect(0, 0, 76, 26), "Find", {
            desktop,
            viewName: "search",
            helpCtx: hcSearch,
            content: new TVGroup({ children: [searchMain, buttonStrip] }),
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
                const parts = [
                    ["tv-search-result-title", entry.title],
                    ["tv-search-result-meta", terms],
                    ["tv-search-result-preview", entry.preview || entry.text.slice(0, 180)],
                ].map(([className, value]) => new TVMarkupList({
                    tag: "span",
                    className,
                    items: [escapeHtml(value)],
                }).renderMarkup()).join("");
                return new TVButton({
                    command: "search-index",
                    value: index,
                    commandData: { selected },
                    labelMarkup: parts,
                }).renderMarkup();
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
            this.results.innerHTML = new TVStaticText({
                textKind: "search-empty",
                text: "Search index is not available for this help file.",
            }).renderMarkup();
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const trimmed = query.trim();
        if (!trimmed) {
            this.results.innerHTML = new TVStaticText({
                textKind: "search-empty",
                text: "Type text to search across all generated topics.",
            }).renderMarkup();
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const matches = this.search(trimmed);
        if (!matches.length) {
            this.results.innerHTML = new TVStaticText({
                textKind: "search-empty",
                text: `No matches for "${trimmed}".`,
            }).renderMarkup();
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
    TV_CONTEXT_HELP_TOPICS,
    TV_CONTEXT_HELP_BUNDLE_URL,
    TVContextHelpDialog,
    TVAboutDialog,
    TVWidgetGalleryDialog,
    TVHistory,
    TVHistoryViewer,
    TVHistoryWindow,
    TVFileList,
    TVFileListBox,
    TVFileOpenDialog,
    TVChangeDirectoryDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVCalendarDialog,
    TVColorsDialog,
    TVMidiPlayerDialog,
    TVFindDialog,
    TVSearchDialog,
});
})();
