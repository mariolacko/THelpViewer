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
    TVView,
    TVRect,
    TVStaticText,
    TVMarkupView,
    TVLabel,
    TVInputLine,
    TVGroup,
    TVListViewer,
    TVListBox,
    TVVerticalListViewer,
    TVVerticalScrollArea,
    TVOutline,
    TVInfoBox,
    TVTerminal,
    TVCheckBoxes,
    TVRadioButtons,
    TVMultiCheckBoxes,
    TVButton,
    bfNormal,
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
    evNothing,
    evMouseDown,
    evKeyDown,
    evCommand,
    evBroadcast,
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
    constructor() {
        const headingView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "context-help-heading", presentation: "context-help-topic" });
        const scrollHost = new TVMarkupView([TVVerticalScrollArea.renderMarkup({
            rootClass: "tv-context-help-scroll",
            rootAttrs: { "data-tv-context-help-scroll": true },
            viewportClass: "tv-context-help-viewport",
            scrollbarClass: "tv-context-help-scrollbar",
        })]);
        const backButton = (new TVButton(new TVRect(), "", "context-help-back", bfNormal).setState("disabled", true)).setDrawOptions({ labelMarkup: "◄ Back" });
        const contentsButton = (new TVButton(new TVRect(), "", "context-help-contents", bfNormal)).setDrawOptions({ labelMarkup: "Contents" });
        const helpMain = (new TVGroup(new TVRect()).insertAll([
                headingView,
                scrollHost,
                (new TVGroup(new TVRect()).insertAll([
                        backButton,
                        contentsButton,
                        new TVStaticText(new TVRect(), "F1 Help"),
                    ])).setDrawOptions({ presentation: "context-help-nav" }),
            ])).setDrawOptions({ presentation: "context-help-main" });
        super(new TVRect(0, 0, 72, 24), "THelpViewer Help", {
            viewName: "context-help",
            helpCtx: hcContextHelp,
            content: helpMain,
            modal: true,
            palette: "help",
            defaultButtonSelector: "",
        });
        this.headingView = headingView;
        this.scrollArea = TVVerticalScrollArea.bindRendered(
            new TVVerticalScrollArea(new TVRect()),
            scrollHost,
        );
        this.viewport = this.scrollArea.viewport;
        if (this.viewport) { this.viewport.tabIndex = 0; }
        this.backButton = backButton;
        this.contentsButton = contentsButton;
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
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "context-help-back") { this.goBack(); }
        else if (event.command === "context-help-contents") { this.showTopic(hcApplication, { remember: true }); }
        else { return; }
        this.clearEvent(event);
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
        this.headingView.setText(topic.title || "Help");
        if (this.viewport) {
            this.viewport.innerHTML = renderContextHelpTopic(topic);
            this.viewport.scrollTop = 0;
        }
        this.backButton.setState("disabled", this.topicHistory.length === 0);
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
    constructor() {
        const body = document.body;
        const siteName = body.dataset.tvSiteName || "THelpViewer";
        const generatorVersion = body.dataset.tvGeneratorVersion || "unknown";
        const generatorAuthors = body.dataset.tvAuthors || "Mario Lacko + Copilot + Codex";
        const okButton = new TVButton(new TVRect(9, 9, (9) + (10), 9), '~O~K', "about-ok", bfDefault);
        const aboutMain = new TVGroup(new TVRect(0, 0, (0) + (28), (0) + (14))).insertAll([
                (new TVStaticText(new TVRect(0, 1, (0) + (28), 1), siteName)).setDrawOptions({ align: "center", title: true }),
                (new TVStaticText(new TVRect(0, 3, (0) + (28), 3), `Version ${generatorVersion}`)).setDrawOptions({ align: "center" }),
                (new TVStaticText(new TVRect(0, 5, (0) + (28), 5), "Copyright (c) 2026")).setDrawOptions({ align: "center" }),
                (new TVStaticText(new TVRect(0, 7, (0) + (28), 7), generatorAuthors)).setDrawOptions({ align: "center" }),
                okButton,
            ]);

        super(new TVRect(0, 0, 32, 13), "About", {
            viewName: "about",
            helpCtx: hcAbout,
            content: aboutMain,
        });
        this.okButton = okButton;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "about-ok") {
            this.close();
            this.clearEvent(event);
        }
    }
}

class TVViewGalleryDialog extends TVDialog {
    constructor() {
        const nameLabel = (new TVLabel(new TVRect(), "~N~ame:")).setDrawOptions({ hotkey: true });
        const nameInput = (new TVInputLine(new TVRect(), 255).setData("Turbo Vision")).setDrawOptions({ autocomplete: "off", viewName: 'gallery-name' });
        nameLabel.link = nameInput;
        const checks = (new TVCheckBoxes(new TVRect(), [
                { label: "~F~rames", value: "frames", checked: true },
                { label: "~S~hadows", value: "shadows", checked: true },
                { label: "D~i~sabled", value: "disabled", disabled: true },
            ])).setDrawOptions({ viewName: "gallery-checks" });
        const radios = (new TVRadioButtons(new TVRect(), [
                { label: "~T~ext", value: "text", checked: true },
                { label: "~G~raphics", value: "graphics" },
                { label: "~M~ono", value: "mono", disabled: true },
            ])).setDrawOptions({ viewName: "gallery-radios" });
        const multiChecks = (new TVMultiCheckBoxes(new TVRect(), [
                { label: "~O~ff / On / Auto", value: "mode", state: 0 },
                { label: "~R~ead / Write / Both", value: "access", state: 1 },
                { label: "D~i~sabled", value: "disabled", state: 2, disabled: true },
            ])).setDrawOptions({ viewName: "gallery-multichecks" });
        const staticText = (new TVStaticText(new TVRect(), "Static text · label hotkeys · disabled states")).setDrawOptions({ viewName: "gallery-static" });
        const terminal = (new TVTerminal(new TVRect(0, 0, 28, 3), 50)).setDrawOptions({ viewName: "gallery-terminal" });
        const infoBox = (new TVInfoBox(new TVRect(0, 0, (0) + (30), 0), "Event log", [terminal])).setDrawOptions({ viewName: "gallery-status" });
        const okButton = new TVButton(new TVRect(), "~O~K", "gallery-ok", bfDefault);
        const applyButton = new TVButton(new TVRect(), "~A~pply", "gallery-apply", bfNormal);
        const messageButton = new TVButton(new TVRect(), "~M~essage", "gallery-message", bfNormal);
        const clearLogButton = new TVButton(new TVRect(), "C~l~ear log", "gallery-clear-log", bfNormal);
        const buttons = (new TVGroup(new TVRect()).insertAll([
                okButton,
                applyButton,
                messageButton,
                clearLogButton,
                new TVButton(new TVRect(), "Disabled", "", bfNormal).setState("disabled", true),
            ])).setDrawOptions({ presentation: "widget-gallery-buttons" });
        const galleryPanel = (heading, child, role = "") => (new TVGroup(new TVRect()).insertAll([
                (new TVStaticText(new TVRect(), heading)).setDrawOptions({ presentation: "widget-gallery-heading" }),
                child,
            ])).setDrawOptions({ presentation: ["widget-gallery-panel", role].filter(Boolean).join(" ") });
        const listHost = new TVMarkupView([TVVerticalListViewer.renderMarkup({
            rootClass: "tv-widget-gallery-listviewer",
            rootAttrs: { "data-tv-gallery-list": true },
            viewportClass: "tv-widget-gallery-list",
        })]);
        const galleryMain = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([nameLabel, nameInput])).setDrawOptions({ presentation: "widget-gallery-field" }),
                (new TVGroup(new TVRect()).insertAll([
                        galleryPanel("Check boxes", checks),
                        galleryPanel("Radio buttons", radios),
                        galleryPanel("Multi check boxes", multiChecks),
                        galleryPanel(
                            "List viewer",
                            listHost,
                        ),
                        galleryPanel("Info box", infoBox, "widget-gallery-info"),
                        galleryPanel("Static text", staticText, "widget-gallery-static"),
                    ])).setDrawOptions({ presentation: "widget-gallery-samples" }),
                buttons,
            ])).setDrawOptions({ presentation: "widget-gallery-main" });

        super(new TVRect(0, 0, 68, 29), "Widget Gallery", {
            viewName: "widget-gallery",
            helpCtx: hcWidgetGallery,
            content: galleryMain,
        });
        this.nameInput = nameInput;
        this.checks = checks;
        this.radios = radios;
        this.multiChecks = multiChecks.bind(
            multiChecks.root,
            (option, state) => this.setStatus(`${option.value}: state ${state}`),
        );
        this.okButton = okButton;
        this.applyButton = applyButton;
        this.messageButton = messageButton;
        this.clearLogButton = clearLogButton;
        this.infoBox = infoBox.resolve(this.dialog);
        this.terminal = terminal.bind(terminal.root);
        this.messageBox = null;
        this.listBox = TVVerticalListViewer.bindRendered((new TVVerticalListViewer(new TVRect())).setDrawOptions({
            itemClassName: "tv-widget-gallery-list-item",
            itemAttrName: "data-tv-gallery-list-index",
        }), listHost);
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
        // TVDialog translates browser input to Turbo Vision events.
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evBroadcast) {
            if (event.infoPtr === this.nameInput) {
                this.setStatus(`Name: ${this.nameInput.getData() || "(empty)"}`);
            } else if (event.infoPtr === this.checks || event.infoPtr === this.radios) {
                const input = event.nativeEvent.target.closest("input");
                if (input) { this.setStatus(`${input.value}: ${input.checked ? "on" : "off"}`); }
            } else { return; }
            this.clearEvent(event);
            return;
        }
        if (event.what !== evCommand) { return; }
        if (event.command === "gallery-ok") { this.close(); }
        else if (event.command === "gallery-apply") { this.setStatus("Apply command"); }
        else if (event.command === "gallery-clear-log") { this.terminal.clear(); }
        else if (event.command === "gallery-message") { void this.showMessage(); }
        else { return; }
        this.clearEvent(event);
    }

    async showMessage() {
        if (!this.messageBox) {
            this.messageBox = new TVMessageBox();
            this.owner?.insert(this.messageBox);
        }
        const command = await this.messageBox.show({
            type: TVMessageBox.MF_INFORMATION,
            lines: ["Turbo Vision message box"],
            buttons: TVMessageBox.MF_OK_CANCEL,
        });
        this.setStatus(`Message: ${command}`);
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
    static triggerView({ name = "", ariaLabel = "History" } = {}) {
        return (new TVButton(new TVRect(), "", name, bfNormal).setState("disabled", true)).setDrawOptions({ labelMarkup: [
                '<span class="tv-file-open-history-side" aria-hidden="true">▐</span>',
                '<span class="tv-file-open-history-arrow" aria-hidden="true">↓</span>',
                '<span class="tv-file-open-history-side" aria-hidden="true">▌</span>',
            ].join(""), ariaLabel: ariaLabel, ariaExpanded: false });
    }

    static view({ popupRole = "", popupName = "", listAttrs = {} } = {}) {
        const viewerMarkup = TVVerticalListViewer.renderMarkup({
            rootClass: "tv-file-open-history-listviewer",
            rootAttrs: listAttrs,
            viewportClass: "tv-file-open-history-list",
        });
        return (new TVGroup(new TVRect()).insertAll([new TVMarkupView([[
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
            ].join("")])])).setDrawOptions({ presentation: ["file-open-history-popup", "history-window", popupRole].filter(Boolean).join(" "), viewName: popupName, hidden: true });
    }

    constructor({ button, popup, viewer, items = () => [], onSelect = null } = {}) {
        super(new TVRect(), "History");
        this.buttonView = button instanceof TVView ? button : null;
        this.popupView = popup instanceof TVView ? popup : null;
        this.button = this.buttonView?.root || null;
        this.popup = this.popupView?.root || null;
        this.bindRoot(this.popup);
        this.viewer = viewer;
        if (this.viewer && !this.viewer.root) {
            this.viewer.bindRoot(this.popup?.querySelector(".tv-file-open-history-listviewer") || null);
        }
        this.closeButton = this.popup?.querySelector("[data-tv-history-close]") || null;
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
    constructor(bounds, numCols = 2) {
        super(bounds, numCols);
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
    constructor() {
        const nameLabel = (new TVLabel(new TVRect(), "~N~ame")).setDrawOptions({ hotkey: true });
        const nameInput = (new TVInputLine(new TVRect(), 255).setData("*.*")).setDrawOptions({ autocomplete: "off", spellcheck: "false", viewName: 'file-open-name' });
        nameLabel.link = nameInput;
        const filesLabel = (new TVLabel(new TVRect(), "~F~iles")).setDrawOptions({ hotkey: true });
        const openButton = new TVButton(new TVRect(), "~O~pen", "file-open-confirm", bfDefault);
        const cancelButton = new TVButton(new TVRect(), "Cancel", "file-open-cancel", bfNormal);
        const historyButton = TVHistoryWindow.triggerView({ name: "file-open-history" });
        const fileListHost = (new TVGroup(new TVRect()).insertAll([])).setDrawOptions({ presentation: "file-open-file-list", viewName: "file-open-files" });
        const scrollLeftButton = (new TVButton(new TVRect(), "", "file-open-scroll-left", bfNormal)).setDrawOptions({ labelMarkup: escapeHtml(displayCp437Char(17)), tabIndex: -1 });
        const scrollTrack = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "file-open-scroll-track" });
        const scrollRightButton = (new TVButton(new TVRect(), "", "file-open-scroll-right", bfNormal)).setDrawOptions({ labelMarkup: escapeHtml(displayCp437Char(16)), tabIndex: -1 });
        const pathLabel = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "file-open-path" });
        const detailLabel = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "file-open-detail" });
        const historyPopup = TVHistoryWindow.view({
            popupName: "file-open-history-popup",
            listAttrs: { "data-tv-file-open-history-list": true },
        });
        const fileOpenMain = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([nameLabel])).setDrawOptions({ presentation: "file-open-name-label" }),
                (new TVGroup(new TVRect()).insertAll([nameInput])).setDrawOptions({ presentation: "file-open-name-input" }),
                historyButton,
                (new TVGroup(new TVRect()).insertAll([filesLabel])).setDrawOptions({ presentation: "file-open-files-label" }),
                fileListHost,
                (new TVGroup(new TVRect()).insertAll([
                        scrollLeftButton,
                        scrollTrack,
                        scrollRightButton,
                    ])).setDrawOptions({ presentation: "file-open-hscroll", viewName: "file-open-hscroll", ariaHidden: true }),
                (new TVGroup(new TVRect()).insertAll([openButton])).setDrawOptions({ presentation: "file-open-open-button" }),
                (new TVGroup(new TVRect()).insertAll([cancelButton])).setDrawOptions({ presentation: "file-open-cancel-button" }),
                (new TVGroup(new TVRect()).insertAll([
                        pathLabel,
                        detailLabel,
                    ])).setDrawOptions({ presentation: "file-open-info" }),
                historyPopup,
            ])).setDrawOptions({ presentation: "file-open-main" });

        super(new TVRect(0, 0, 49, 19), "Open a File", {
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
        this.nameInput = nameInput;
        this.pathLabel = pathLabel;
        this.detailLabel = detailLabel;
        this.openButton = openButton;
        this.cancelButton = cancelButton;
        this.historyButton = historyButton;
        this.historyPopup = historyPopup;
        this.scrollLeftButton = scrollLeftButton;
        this.scrollRightButton = scrollRightButton;
        this.scrollTrack = scrollTrack;
        this.fileList = (new TVFileList(new TVRect(), 2)).setDrawOptions({
            itemClassName: "tv-file-open-list-item",
            itemAttrName: "data-tv-file-open-file-index",
            renderItemContent: (item) => escapeHtml(item.label),
        }).bindRoot(fileListHost.root);
        this.fileList.onViewportChange = () => this.updateHorizontalScrollbar();
        this.historyList = (new TVHistoryViewer(new TVRect())).setDrawOptions({
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
        // Browser input is translated by TVDialog and handled in handleEvent.
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "file-open-confirm") { this.openSelected(); }
            else if (event.command === "file-open-cancel") { this.close(); }
            else if (event.command === "file-open-scroll-left") { this.fileList.scrollColumns(-1); }
            else if (event.command === "file-open-scroll-right") { this.fileList.scrollColumns(1); }
            else { return; }
            this.clearEvent(event);
            return;
        }
        if (event.what === evBroadcast && event.infoPtr === this.nameInput) {
            this.selectNameMatch();
            this.clearEvent(event);
            return;
        }
        const keyEvent = event.nativeEvent;
        if (event.what !== evKeyDown || !keyEvent?.altKey || keyEvent.ctrlKey || keyEvent.metaKey) { return; }
        const key = keyEvent.key.toLowerCase();
        if (key === "n") {
            keyEvent.preventDefault();
            this.nameInput.focus();
            this.nameInput.selectAll();
        } else if (key === "f") {
            keyEvent.preventDefault();
            this.fileList.selectedElement()?.focus();
        } else if (key === "o") {
            keyEvent.preventDefault();
            this.openSelected();
        } else {
            return;
        }
        this.clearEvent(event);
    }

    open() {
        this.historyWindow.hide();
        this.refresh();
        super.open();
        window.requestAnimationFrame(() => {
            this.updateHorizontalScrollbar();
            this.nameInput.focus();
            this.nameInput.selectAll();
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
        this.nameInput.setData("*.*");
        this.updateInfo(this.currentItems[0] || null);
        this.updateHistoryState();
        this.updateHorizontalScrollbar();
    }

    currentMaskPath() {
        const directory = this.currentDirectory ? `${this.currentDirectory}\\` : "";
        return `THelpViewer:\\${directory}*.*`;
    }

    selectItem(item) {
        if (!item || item.type === "status") { return; }
        this.nameInput.setData(item.type === "file" ? item.entry.fileName : `${item.label}*.*`);
        this.updateInfo(item);
    }

    updateInfo(item) {
        this.pathLabel.setText(` ${this.currentMaskPath()}`);
        if (!item) {
            this.detailLabel.setText("");
        } else if (item.type === "status") {
            this.detailLabel.setText(` ${item.label}`);
        } else if (item.type === "file") {
            const format = String(item.entry.format || (item.entry.kind === "doc" ? "Markdown" : "Help")).toUpperCase();
            const topics = Number.isInteger(item.entry.topics) ? `  ${item.entry.topics} topics` : "";
            this.detailLabel.setText(` ${item.entry.fileName}  ${format}${topics}`);
        } else {
            this.detailLabel.setText(` ${item.label}  Directory`);
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
        const query = this.nameInput.getData().trim().toLocaleLowerCase();
        if (!query || query.includes("*")) { return; }
        const index = this.currentItems.findIndex((item) => item.label.toLocaleLowerCase().startsWith(query));
        if (index >= 0) {
            this.fileList.select(index);
            this.updateInfo(this.currentItems[index]);
        }
    }

    openSelected() {
        const query = this.nameInput.getData().trim().toLocaleLowerCase();
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
        const trackLength = 29;
        const columns = Math.max(1, Math.ceil(this.currentItems.length / this.fileList.rows));
        const maxColumn = Math.max(0, columns - 2);
        const position = maxColumn
            ? Math.round((this.fileList.firstColumn() / maxColumn) * (trackLength - 1))
            : -1;
        const cells = Array.from({ length: trackLength }, () => displayCp437Char(177));
        if (position >= 0) { cells[position] = displayCp437Char(254); }
        this.scrollTrack.setText(cells.join(""));
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
            this.nameInput.focus();
        }
    }
}

class TVChangeDirectoryDialog extends TVDialog {
    constructor() {
        const directoryLabel = (new TVLabel(new TVRect(), "~D~irectory")).setDrawOptions({ hotkey: true });
        const directoryInput = (new TVInputLine(new TVRect(), 255).setData("")).setDrawOptions({ autocomplete: "off", spellcheck: "false", viewName: 'change-dir-path' });
        directoryLabel.link = directoryInput;
        const treeLabel = (new TVLabel(new TVRect(), "Directory ~t~ree")).setDrawOptions({ hotkey: true });
        const changeButton = new TVButton(new TVRect(), "~C~hdir", "change-dir-confirm", bfDefault);
        const revertButton = new TVButton(new TVRect(), "~R~evert", "change-dir-revert", bfNormal);
        const cancelButton = new TVButton(new TVRect(), "Cancel", "change-dir-cancel", bfNormal);
        const historyButton = TVHistoryWindow.triggerView({
            name: "change-dir-history",
            ariaLabel: "Directory history",
        });
        const directoryListHost = new TVMarkupView([TVVerticalListViewer.renderMarkup({
            rootClass: "tv-change-dir-listviewer",
            rootAttrs: { "data-tv-change-dir-list": true },
            viewportClass: "tv-change-dir-list",
        })]);
        const detailView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "change-dir-detail", presentation: "change-dir-detail" });
        const historyPopup = TVHistoryWindow.view({
            popupRole: "change-dir-history-popup",
            popupName: "change-dir-history-popup",
            listAttrs: { "data-tv-change-dir-history-list": true },
        });
        const changeDirectoryMain = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([directoryLabel])).setDrawOptions({ presentation: "change-dir-path-label" }),
                (new TVGroup(new TVRect()).insertAll([directoryInput])).setDrawOptions({ presentation: "change-dir-path-input" }),
                historyButton,
                (new TVGroup(new TVRect()).insertAll([treeLabel])).setDrawOptions({ presentation: "change-dir-tree-label" }),
                directoryListHost,
                (new TVGroup(new TVRect()).insertAll([changeButton])).setDrawOptions({ presentation: "change-dir-confirm-button" }),
                (new TVGroup(new TVRect()).insertAll([revertButton])).setDrawOptions({ presentation: "change-dir-revert-button" }),
                (new TVGroup(new TVRect()).insertAll([cancelButton])).setDrawOptions({ presentation: "change-dir-cancel-button" }),
                detailView,
                historyPopup,
            ])).setDrawOptions({ presentation: "change-dir-main" });

        super(new TVRect(0, 0, 46, 18), "Change Directory", {
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
        this.pathInput = directoryInput;
        this.detailView = detailView;
        this.changeButton = changeButton;
        this.revertButton = revertButton;
        this.cancelButton = cancelButton;
        this.historyButton = historyButton;
        this.historyPopup = historyPopup;
        this.directoryList = TVVerticalListViewer.bindRendered((new TVOutline(new TVRect())).setDrawOptions({
            itemClassName: "tv-change-dir-item",
            itemAttrName: "data-tv-change-dir-index",
            getKey: (item) => item.path,
            getLabel: (item) => item.label,
        }), directoryListHost);
        this.historyList = (new TVHistoryViewer(new TVRect())).setDrawOptions({
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
                else { this.pathInput.focus(); }
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
        // Browser input is translated by TVDialog and handled in handleEvent.
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "change-dir-confirm") { this.commit(); }
            else if (event.command === "change-dir-revert") { this.setDirectory(this.initialDirectory); }
            else if (event.command === "change-dir-cancel") { this.close(); }
            else { return; }
            this.clearEvent(event);
            return;
        }
        if (
            event.infoPtr === this.pathInput
            && event.what === evBroadcast
            && event.nativeEvent?.type === "change"
        ) {
            this.selectInputPath();
            this.clearEvent(event);
            return;
        }
        const keyEvent = event.nativeEvent;
        if (event.what !== evKeyDown || !keyEvent) { return; }
        if (event.infoPtr === this.pathInput && keyEvent.key === "Enter") {
            keyEvent.preventDefault();
            this.selectInputPath();
            this.commit();
            this.clearEvent(event);
            return;
        }
        if (!keyEvent.altKey || keyEvent.ctrlKey || keyEvent.metaKey) { return; }
        const key = keyEvent.key.toLowerCase();
        if (key === "d") {
            keyEvent.preventDefault();
            this.pathInput.focus();
            this.pathInput.selectAll();
        } else if (key === "t") {
            keyEvent.preventDefault();
            this.directoryList.selectedElement()?.focus();
        } else if (key === "c") {
            keyEvent.preventDefault();
            this.commit();
        } else if (key === "r") {
            keyEvent.preventDefault();
            this.setDirectory(this.initialDirectory);
        } else {
            return;
        }
        this.clearEvent(event);
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
        const item = this.findDirectory(this.pathInput.getData());
        if (!item) {
            this.detailView.setText("Directory does not exist");
            return false;
        }
        return this.selectDirectory(item.path);
    }

    updatePath() {
        this.pathInput.setData(this.displayPath(this.currentDirectory));
        this.detailView.setText(`${this.entries.filter((entry) => entry.directory === this.currentDirectory).length} files`);
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
            this.pathInput.focus();
            this.pathInput.selectAll();
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
    constructor() {
        const chart = new TVMarkupView([], { className: "tv-ascii-chart", attributes: { "data-tv-ascii-chart": true } });
        const report = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "ascii-report", presentation: "ascii-report" });
        super(new TVRect(0, 0, 34, 12), "ASCII Chart", {
            viewName: "ascii",
            helpCtx: hcAsciiTable,
            palette: "ascii",
            content: [chart, report],
        });
        this.selectedCode = 0;
        this.chartView = chart;
        this.reportView = report;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        if (this.chartView.root) {
            this.chartView.root.addEventListener("focusin", (event) => this.onCellEvent(event));
            this.chartView.root.addEventListener("mousemove", (event) => {
                if (event.buttons & 1) {
                    this.onCellEvent(event);
                }
            });
        }
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
        this.renderChart();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evMouseDown && event.infoPtr === this.chartView) {
            this.onCellEvent(event.nativeEvent);
            this.clearEvent(event);
        }
    }

    open() {
        super.open();
        this.renderChart();
    }

    renderChart() {
        const items = [];
        for (let code = 0; code < 256; code += 1) {
            const selected = code === this.selectedCode ? " is-selected" : "";
            items.push((new TVButton(new TVRect(), "", "ascii-code", bfNormal).setValue(code).setCommandData({ selected: Boolean(selected) })).setDrawOptions({ labelMarkup: escapeHtml(displayCp437Char(code)), ariaLabel: `ASCII ${code}` }).renderMarkup());
        }
        this.chartView.setHTML(items.join(""));
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
        this.chartView.queryAll("[data-tv-ascii-code]").forEach((element) => {
            const cellCode = Number.parseInt(element.getAttribute("data-tv-ascii-code"), 10);
            element.classList.toggle("is-selected", cellCode === code);
        });
        this.updateReport(code);
    }

    updateReport(code) {
        const char = code === 0 ? " " : displayCp437Char(code);
        const decimal = String(code).padStart(3, " ");
        const hex = code.toString(16).toUpperCase().padStart(2, "0");
        this.reportView.setText(`  Char: ${char} Decimal: ${decimal} Hex ${hex}`.padEnd(32, " "));
    }
}

class TVCalculatorDialog extends TVDialog {
    constructor() {
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
            (new TVButton(new TVRect(), "", "calc-key", bfNormal).setValue(key)).setDrawOptions({ labelMarkup: escapeHtml(label), ariaLabel: `Calculator key ${aria}` })
        );
        const displayView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "calc-display", presentation: "calc-display" });
        const calcMain = (new TVGroup(new TVRect()).insertAll([
                displayView,
                (new TVGroup(new TVRect()).insertAll(buttons)).setDrawOptions({ presentation: "calc-keypad" }),
            ])).setDrawOptions({ presentation: "calc-main" });

        super(new TVRect(0, 0, 24, 15), "Calculator", {
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
        this.displayView = displayView;
        this.buttons = buttons;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.updateDisplay();
    }

    bind() {
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
        document.addEventListener("keyup", (event) => this.onKeyUp(event));
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "calc-key") {
            const token = String(event.infoPtr.value || "");
            this.calcKey(this.buttonValueMap[token] || token);
            this.clearEvent(event);
        }
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
        const width = 18;
        const lead = Math.max(0, width - this.number.length - 2);
        const text = `${" ".repeat(lead)}${this.sign}${this.number} `;
        this.displayView.setText(text.slice(-width).padEnd(width, " "));
    }
}

class TVCalendarDialog extends TVDialog {
    constructor() {
        const now = new Date();
        const captionView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "calendar-caption" });
        const prevButton = (new TVButton(new TVRect(), "", "calendar-prev", bfNormal)).setDrawOptions({ labelMarkup: escapeHtml(displayCp437Char(30)), ariaLabel: "Previous month" });
        const nextButton = (new TVButton(new TVRect(), "", "calendar-next", bfNormal)).setDrawOptions({ labelMarkup: escapeHtml(displayCp437Char(31)), ariaLabel: "Next month" });
        const gridView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "calendar-grid", presentation: "calendar-grid" });
        const calendarMain = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([
                        captionView,
                        prevButton,
                        new TVStaticText(new TVRect(), "  "),
                        nextButton,
                    ])).setDrawOptions({ presentation: "calendar-header" }),
                new TVStaticText(new TVRect(), "Su Mo Tu We Th Fr Sa"),
                gridView,
            ])).setDrawOptions({ presentation: "calendar-main" });
        super(new TVRect(0, 0, 27, 11), "Calendar", {
            viewName: "calendar",
            helpCtx: hcCalendar,
            palette: "calendar",
            content: calendarMain,
        });
        this.captionView = captionView;
        this.gridView = gridView;
        this.prevButton = prevButton;
        this.nextButton = nextButton;
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
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "calendar-prev") { this.changeMonth(-1); }
        else if (event.command === "calendar-next") { this.changeMonth(1); }
        else { return; }
        this.clearEvent(event);
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
        this.captionView.setText(`${MONTH_NAMES[this.month].padStart(9, " ")} ${String(this.year).padStart(4, " ")}`);
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
                cells.push((new TVStaticText(new TVRect(), inMonth ? String(current).padStart(2, " ") : "  ")).setDrawOptions({ presentation: `calendar-cell${isToday ? " is-current" : ""}${!inMonth ? " is-empty" : ""}` }).renderMarkup());
                current += 1;
            }
        }
        this.gridView.setHTML(cells.join(""));
    }
}

class TVColorsDialog extends TVDialog {
    constructor() {
        const okButton = new TVButton(new TVRect(), 'O~K~', "colors-ok", bfDefault);
        const cancelButton = new TVButton(new TVRect(), '~C~ancel', "colors-cancel", bfNormal);
        const resetAllButton = new TVButton(new TVRect(), '~R~eset All', "colors-reset-all", bfNormal);
        const defaultButton = new TVButton(new TVRect(), '~D~efault', "colors-default", bfNormal);
        const buttonStrip = (new TVGroup(new TVRect()).insertAll([defaultButton, resetAllButton, okButton, cancelButton])).setDrawOptions({ presentation: "colors-dialog-buttons" });
        const groupTitle = (new TVLabel(new TVRect(), "~G~roup")).setDrawOptions({ presentation: "colors-group-label", hotkey: true });
        const itemTitle = (new TVLabel(new TVRect(), "~I~tem")).setDrawOptions({ presentation: "colors-item-label", hotkey: true });
        const fgTitle = (new TVLabel(new TVRect(), "~F~oreground")).setDrawOptions({ presentation: "colors-foreground-label", hotkey: true });
        const bgTitle = (new TVLabel(new TVRect(), "~B~ackground")).setDrawOptions({ presentation: "colors-background-label", hotkey: true });
        const groupListHost = new TVMarkupView([TVVerticalListViewer.renderMarkup({
            rootClass: "tv-colors-listviewer tv-colors-groups-listviewer",
            rootAttrs: { "data-tv-colors-groups": true },
            viewportClass: "tv-colors-list-viewport",
        })]);
        const itemListHost = new TVMarkupView([TVVerticalListViewer.renderMarkup({
            rootClass: "tv-colors-listviewer tv-colors-items-listviewer",
            rootAttrs: { "data-tv-colors-items": true },
            viewportClass: "tv-colors-list-viewport",
        })]);
        const foregroundView = (new TVGroup(new TVRect()).insertAll([])).setDrawOptions({ presentation: "colors-selector colors-foreground", viewName: "colors-foreground" });
        const backgroundView = (new TVGroup(new TVRect()).insertAll([])).setDrawOptions({ presentation: "colors-selector colors-background is-background", viewName: "colors-background" });
        const displayView = (new TVGroup(new TVRect()).insertAll([])).setDrawOptions({ presentation: "colors-display", viewName: "colors-display" });
        const colorsMain = (new TVGroup(new TVRect()).insertAll([
                groupTitle,
                groupListHost,
                itemTitle,
                itemListHost,
                fgTitle,
                foregroundView,
                bgTitle,
                backgroundView,
                displayView,
                buttonStrip,
            ])).setDrawOptions({ presentation: "colors-main" });
        super(new TVRect(0, 0, 61, 18), "Colors", {
            viewName: "colors",
            helpCtx: hcColors,
            content: colorsMain,
        });
        this.foregroundView = foregroundView;
        this.backgroundView = backgroundView;
        this.displayView = displayView;
        this.okButton = okButton;
        this.cancelButton = cancelButton;
        this.defaultButton = defaultButton;
        this.resetAllButton = resetAllButton;
        this.groupBox = TVVerticalListViewer.bindRendered((new TVVerticalListViewer(new TVRect())).setDrawOptions({
            itemClassName: "tv-colors-list-item",
            itemAttrName: "data-tv-colors-group",
            renderItemContent: (group) => escapeHtml(group.name),
        }), groupListHost);
        this.itemBox = TVVerticalListViewer.bindRendered((new TVVerticalListViewer(new TVRect())).setDrawOptions({
            itemClassName: "tv-colors-list-item",
            itemAttrName: "data-tv-colors-item",
            renderItemContent: (item) => escapeHtml(item.name),
        }), itemListHost);
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
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "colors-ok") { this.confirm(); }
            else if (event.command === "colors-cancel") { this.cancel(); }
            else if (event.command === "colors-default") { this.restoreSelectedDefault(); }
            else if (event.command === "colors-reset-all") { this.resetAllColors(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evMouseDown && (event.infoPtr === this.foregroundView || event.infoPtr === this.backgroundView)) {
            this.onSelectorClick(event.nativeEvent, event.infoPtr === this.foregroundView ? "fg" : "bg");
            this.clearEvent(event);
        } else if (event.what === evKeyDown && (event.infoPtr === this.foregroundView || event.infoPtr === this.backgroundView)) {
            this.onSelectorKeyDown(event.nativeEvent, event.infoPtr === this.foregroundView ? "fg" : "bg");
            if (event.nativeEvent.defaultPrevented) { this.clearEvent(event); }
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
            const selector = type === "fg" ? this.foregroundView : this.backgroundView;
            window.requestAnimationFrame(() => {
                selector.query(`[data-tv-color-index="${colorIndex}"]`)?.focus();
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
        const selector = type === "fg" ? this.foregroundView : this.backgroundView;
        selector.query(`[data-tv-color-index="${color}"]`)?.click();
        selector.query(`[data-tv-color-index="${color}"]`)?.focus();
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
        this.foregroundView.setHTML(this.renderSelectorCells(16, fg));
        this.backgroundView.setHTML(this.renderSelectorCells(8, bg));
    }

    renderSelectorCells(count, selected) {
        const marker = displayCp437Char(8);
        const icon = displayCp437Char(219).repeat(3);
        const cells = [];
        for (let index = 0; index < count; index += 1) {
            const isSelected = index === selected;
            const content = isSelected
                ? escapeHtml(displayCp437Char(219))
                    + new TVMarkupView([escapeHtml(marker)], { element: "span", className: "tv-color-cell-marker" }).renderMarkup()
                    + escapeHtml(displayCp437Char(219))
                : escapeHtml(icon);
            cells.push((new TVButton(new TVRect(), "", "color-index", bfNormal).setValue(index).setCommandData({ selected: isSelected, color: DOS_COLORS[index] })).setDrawOptions({ labelMarkup: content, ariaLabel: `Color ${index}`, ariaPressed: isSelected, tabIndex: isSelected ? 0 : -1 }).renderMarkup());
        }
        return cells.join("");
    }

    renderDisplay() {
        const item = this.selectedItem();
        if (!item) {
            return;
        }
        const fg = dosColor(item.attr, 0);
        const bg = dosColor(item.attr, 4);
        this.displayView.setHTML((new TVStaticText(new TVRect(), "Text Text Text \nText Text Text ")).setDrawOptions({ presentation: "colors-display-sample" }).renderMarkup());
        this.displayView.root?.style.setProperty("--tv-colors-sample-fg", fg);
        this.displayView.root?.style.setProperty("--tv-colors-sample-bg", bg);
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
    constructor() {
        const previousButton = (new TVButton(new TVRect(), "◄◄", "midi-previous", bfNormal)).setDrawOptions({ tooltip: "Previous track" });
        const playButton = new TVButton(new TVRect(), "►", "midi-play", bfDefault);
        const pauseButton = (new TVButton(new TVRect(), "▌▌", "midi-pause", bfNormal)).setDrawOptions({ tooltip: "Pause" });
        const stopButton = new TVButton(new TVRect(), "■", "midi-stop", bfNormal);
        const nextButton = (new TVButton(new TVRect(), "►►", "midi-next", bfNormal)).setDrawOptions({ tooltip: "Next track" });
        const moreButton = (new TVButton(new TVRect(), "More", "midi-more", bfNormal)).setDrawOptions({ ariaExpanded: false });
        const closeButton = new TVButton(new TVRect(), "Close", "midi-close-button", bfNormal);
        const buttons = (new TVGroup(new TVRect()).insertAll([
                previousButton, playButton, pauseButton, stopButton, nextButton, moreButton, closeButton,
            ])).setDrawOptions({ presentation: "midi-buttons" });
        const sourceButtons = TV_MIDI_EXTERNAL_SOURCES.map((source, index) => (new TVButton(new TVRect(), "", "midi-source", bfNormal).setValue(index)).setDrawOptions({ labelMarkup: escapeHtml(source.label), tooltip: `${source.title} (${source.credit})` }));
        const midiUrlInput = (new TVInputLine(new TVRect(), 255)).setDrawOptions({
                presentation: "midi-url-input",
                placeholder: "https://example.com/song.mid",
                spellcheck: "false",
                viewName: "midi-url",
            });
        const midiUrlLabel = (new TVLabel(new TVRect(), "URL", midiUrlInput)).setDrawOptions({ presentation: "midi-url-label" });
        const trackNumberView = (new TVStaticText(new TVRect(), "01")).setDrawOptions({ viewName: "midi-track-number", presentation: "midi-track-number" });
        const timeView = (new TVStaticText(new TVRect(), "0:00 / 0:00")).setDrawOptions({ viewName: "midi-time", presentation: "midi-display-time" });
        const titleView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "midi-display-title", presentation: "midi-display-title" });
        const statusView = (new TVStaticText(new TVRect(), "Ready.")).setDrawOptions({ viewName: "midi-status", presentation: "midi-status" });
        const display = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([
                        (new TVStaticText(new TVRect(), "Track")).setDrawOptions({ presentation: "midi-display-label" }),
                        trackNumberView,
                        timeView,
                    ])).setDrawOptions({ presentation: "midi-display-line" }),
                titleView,
                statusView,
            ])).setDrawOptions({ presentation: "midi-display" });
        const meterView = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "midi-meter", presentation: "midi-meter-fill" });
        const meter = (new TVGroup(new TVRect()).insertAll([
                meterView,
            ])).setDrawOptions({ presentation: "midi-meter" });
        const loadUrlButton = new TVButton(new TVRect(), "Load", "midi-load-url", bfNormal);
        const externalSource = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([
                        midiUrlLabel,
                        midiUrlInput,
                        loadUrlButton,
                    ])).setDrawOptions({ presentation: "midi-url-row" }),
                (new TVGroup(new TVRect()).insertAll(sourceButtons)).setDrawOptions({ presentation: "midi-source-presets" }),
            ])).setDrawOptions({ presentation: "midi-external", viewName: "midi-advanced", hidden: true });
        const trackList = new TVMarkupView([TVVerticalListViewer.renderMarkup({
            rootClass: "tv-midi-track-list",
            rootAttrs: { "data-tv-midi-track-list": true },
            viewportClass: "tv-midi-track-viewport",
            scrollbarClass: "tv-midi-list-scrollbar",
            arrowClass: "tv-midi-list-arrow",
            trackClass: "tv-midi-list-track",
            cellsClass: "tv-midi-list-cells",
            thumbClass: "tv-midi-list-thumb",
        })]);
        const main = (new TVGroup(new TVRect()).insertAll([display, meter, buttons, trackList, externalSource])).setDrawOptions({ presentation: "midi-main", viewName: "midi-main" });
        super(new TVRect(0, 0, 58, 23), "CD/MIDI Player", {
            viewName: "midi",
            helpCtx: hcMidiPlayer,
            content: main,
        });
        this.selectedIndex = 0;
        this.cache = new Map();
        this.loadSerial = 0;
        this.isPlaying = false;
        this.synth = new TVMidiSynth();
        this.trackNumberView = trackNumberView;
        this.titleView = titleView;
        this.timeView = timeView;
        this.statusView = statusView;
        this.meterView = meterView;
        this.previousButton = previousButton;
        this.playButton = playButton;
        this.pauseButton = pauseButton;
        this.stopButton = stopButton;
        this.nextButton = nextButton;
        this.moreButton = moreButton;
        this.closeActionButton = closeButton;
        this.mainView = main;
        this.advancedView = externalSource;
        this.urlInput = midiUrlInput;
        this.loadUrlButton = loadUrlButton;
        this.sourceButtons = sourceButtons;
        this.trackListBox = TVVerticalListViewer.bindRendered((new TVVerticalListViewer(new TVRect())).setDrawOptions({
            itemClassName: "tv-midi-track",
            itemAttrName: "data-tv-midi-track",
            renderItemMarkup: (track, index, selected) => (new TVButton(new TVRect(), "", "midi-track", bfNormal).setValue(index).setCommandData({ selected })).setDrawOptions({ labelMarkup: [
                    new TVMarkupView([escapeHtml(String(index + 1).padStart(2, "0"))], { element: "span", className: "tv-midi-track-index" }),
                    new TVMarkupView([escapeHtml(track.title)], { element: "span", className: "tv-midi-track-title" }),
                    new TVMarkupView([escapeHtml(track.credit)], { element: "span", className: "tv-midi-track-credit" }),
                ].map((widget) => widget.renderMarkup()).join("") }).renderMarkup(),
        }), trackList);
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
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "midi-previous") { this.previousTrack(); }
            else if (event.command === "midi-play") { void this.playSelected(); }
            else if (event.command === "midi-pause") { this.pausePlayback(); }
            else if (event.command === "midi-stop") { this.stopPlayback(); }
            else if (event.command === "midi-next") { this.nextTrack(); }
            else if (event.command === "midi-more") { this.toggleAdvanced(); }
            else if (event.command === "midi-close-button") { this.close(); }
            else if (event.command === "midi-load-url") { this.playExternalUrl(); }
            else if (event.command === "midi-source") { this.playExternalPreset(Number(event.infoPtr.value)); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown && event.infoPtr === this.urlInput && event.nativeEvent.key === "Enter") {
            event.nativeEvent.preventDefault();
            this.playExternalUrl();
            this.clearEvent(event);
        }
    }

    close() {
        this.stopPlayback();
        super.close();
    }

    toggleAdvanced() {
        const expanded = this.advancedView.root.hidden;
        this.advancedView.setState("visible", expanded);
        this.mainView.root?.classList.toggle("is-advanced", expanded);
        this.moreButton.setState("expanded", expanded);
        this.moreButton.setTitle(expanded ? "Less" : "More");
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
        this.trackNumberView.setText(number);
        this.titleView.setText(track.title);
        this.timeView.setText("0:00 / 0:00");
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
            file = normalizeMidiUrl(this.urlInput.getData());
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
        this.urlInput.setData(source.file);
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
        this.playButton.setState("disabled", true);
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
            this.playButton.setState("disabled", false);
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
        const ratio = duration > 0 ? Math.max(0, Math.min(1, elapsed / duration)) : 0;
        if (this.meterView.root) { this.meterView.root.style.width = `${Math.round(ratio * 100)}%`; }
        this.timeView.setText(`${formatMidiTime(elapsed)} / ${formatMidiTime(duration)}`);
        if (status && duration > 0) {
            this.setStatus(`Playing ${formatMidiTime(elapsed)} / ${formatMidiTime(duration)}.`);
        }
    }

    setStatus(message) {
        this.statusView.setText(message);
    }
}

class TVFindDialog extends TVDialog {
    constructor() {
        const findLabel = (new TVLabel(new TVRect(), "~T~ext to find")).setDrawOptions({ hotkey: true });
        const findInput = (new TVInputLine(new TVRect(), 255).setData("")).setDrawOptions({ autocomplete: "off", spellcheck: "false", viewName: 'find-input' });
        findLabel.link = findInput;
        const findButton = new TVButton(new TVRect(), "~F~ind", "find-confirm", bfDefault);
        const cancelButton = new TVButton(new TVRect(), "Cancel", "find-cancel", bfNormal);
        const findStatus = (new TVStaticText(new TVRect(), "")).setDrawOptions({ viewName: "find-status", presentation: "find-status" });
        const historyButton = TVHistoryWindow.triggerView({
            name: "find-history",
            ariaLabel: "Find history",
        });
        const historyPopup = TVHistoryWindow.view({
            popupRole: "find-history-popup",
            popupName: "find-history-popup",
            listAttrs: { "data-tv-find-history-list": true },
        });
        const findMain = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([findLabel])).setDrawOptions({ presentation: "find-label" }),
                (new TVGroup(new TVRect()).insertAll([findInput])).setDrawOptions({ presentation: "find-input" }),
                historyButton,
                (new TVGroup(new TVRect()).insertAll([findButton])).setDrawOptions({ presentation: "find-confirm" }),
                (new TVGroup(new TVRect()).insertAll([cancelButton])).setDrawOptions({ presentation: "find-cancel" }),
                findStatus,
                historyPopup,
            ])).setDrawOptions({ presentation: "find-main" });
        super(new TVRect(0, 0, 49, 10), "Find", {
            viewName: "find",
            helpCtx: hcFind,
            content: findMain,
            modal: true,
        });
        this.history = new TVHistory("thelp:find-history");
        this.findHandler = null;
        this.findAgainHandler = null;
        this.targetLabel = "active window";
        this.input = findInput;
        this.statusView = findStatus;
        this.findButton = findButton;
        this.cancelButton = cancelButton;
        this.historyButton = historyButton;
        this.historyPopup = historyPopup;
        this.historyList = (new TVHistoryViewer(new TVRect())).setDrawOptions({
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
                this.input.setData(item.value);
                this.historyWindow.hide();
                if (activate) { this.performFind(); }
                else { this.input.focus(); }
            },
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "find-confirm") {
            this.performFind();
            this.clearEvent(event);
        } else if (event.what === evCommand && event.command === "find-cancel") {
            this.close();
            this.clearEvent(event);
        } else if (
            event.what === evKeyDown
            && event.infoPtr === this.input
            && event.nativeEvent?.key === "Enter"
        ) {
            event.nativeEvent.preventDefault();
            this.performFind();
            this.clearEvent(event);
        }
    }

    configure({ find = null, findAgain = null, targetLabel = "active window" } = {}) {
        this.findHandler = typeof find === "function" ? find : null;
        this.findAgainHandler = typeof findAgain === "function" ? findAgain : null;
        this.targetLabel = String(targetLabel || "active window");
        this.historyWindow.refresh();
    }

    open(initialQuery = "") {
        this.historyWindow.hide();
        if (initialQuery) { this.input.setData(initialQuery); }
        this.statusView.setText(`Find in ${this.targetLabel}`);
        this.historyWindow.refresh();
        super.open();
        this.input.focus();
        this.input.selectAll();
    }

    performFind() {
        const query = this.input.getData().trim();
        if (!query || !this.findHandler) {
            this.statusView.setText("Enter text to find.");
            return false;
        }
        this.history.remember(query);
        this.historyWindow.refresh();
        const found = Boolean(this.findHandler(query));
        this.statusView.setText(found ? `Found in ${this.targetLabel}` : `Text not found in ${this.targetLabel}`);
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
    constructor() {
        const okButton = new TVButton(new TVRect(), '~O~K', "search-ok", bfDefault);
        const cancelButton = new TVButton(new TVRect(), '~C~ancel', "search-cancel", bfNormal);
        const buttonStrip = (new TVGroup(new TVRect()).insertAll([okButton, cancelButton])).setDrawOptions({ presentation: "search-buttons" });
        const searchInput = (new TVInputLine(new TVRect(), 255)).setDrawOptions({ autocomplete: "off", spellcheck: "false", viewName: "search-input" });
        const searchLabel = new TVLabel(new TVRect(), "Find:", searchInput);
        const resultsHost = new TVMarkupView([TVVerticalListViewer.renderMarkup({
            rootClass: "tv-search-results-scroll",
            rootAttrs: { "data-tv-search-results": true },
            viewportClass: "tv-search-results",
        })]);
        const searchMain = (new TVGroup(new TVRect()).insertAll([
                (new TVGroup(new TVRect()).insertAll([
                        searchLabel,
                        searchInput,
                    ])).setDrawOptions({ columns: "auto minmax(0,1fr)", gap: "1ch", align: "center" }),
                new TVStaticText(new TVRect(), "Enter text and choose a topic."),
                (new TVGroup(new TVRect()).insertAll([
                        resultsHost,
                    ])).setDrawOptions({ presentation: "search-results-panel" }),
            ])).setDrawOptions({ presentation: "search-main" });

        super(new TVRect(0, 0, 76, 26), "Find", {
            viewName: "search",
            helpCtx: hcSearch,
            content: new TVGroup(new TVRect()).insertAll([searchMain, buttonStrip]),
        });
        this.searchData = window.TV_SEARCH_INDEX && Array.isArray(window.TV_SEARCH_INDEX.topics)
            ? window.TV_SEARCH_INDEX
            : { topics: [] };
        this.input = searchInput;
        this.okButton = okButton;
        this.cancelButton = cancelButton;
        this.resultsBox = TVVerticalListViewer.bindRendered((new TVVerticalListViewer(new TVRect())).setDrawOptions({
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
                ].map(([className, value]) => new TVMarkupView([escapeHtml(value)], { element: "span", className: className }).renderMarkup()).join("");
                return (new TVButton(new TVRect(), "", "search-index", bfNormal).setValue(index).setCommandData({ selected })).setDrawOptions({ labelMarkup: parts }).renderMarkup();
            },
        }), resultsHost);
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

        this.resultsBox.bind({
            onSelect: (_entry, index) => {
                this.selectIndex(index);
            },
            onActivate: (_entry, index) => {
                this.selectIndex(index);
                this.openSelected();
            },
        });
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evBroadcast && event.infoPtr === this.input) {
            this.renderResults(this.input.getData());
            this.clearEvent(event);
        } else if (event.what === evCommand) {
            if (event.command === "search-ok") { this.openSelected(); }
            else if (event.command === "search-cancel") { this.close(); }
            else { return; }
            this.clearEvent(event);
        }
    }

    onKeyDown(event) {
        if (event.key === "F3") {
            event.preventDefault();
            if (this.isOpen()) {
                this.input.focus();
                this.input.selectAll();
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
            this.input.setData(initialQuery);
        }
        this.renderResults(this.input.getData());
        window.requestAnimationFrame(() => this.resultsBox.updateScrollbar());
        this.input.focus();
        this.input.selectAll();
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
        this.okButton.setState("active", this.selectedIndex >= 0);
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
        this.okButton.setState("active", false);
        if (!this.searchData.topics.length) {
            this.results.innerHTML = (new TVStaticText(new TVRect(), "Search index is not available for this help file.")).setDrawOptions({ presentation: "search-empty" }).renderMarkup();
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const trimmed = query.trim();
        if (!trimmed) {
            this.results.innerHTML = (new TVStaticText(new TVRect(), "Type text to search across all generated topics.")).setDrawOptions({ presentation: "search-empty" }).renderMarkup();
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const matches = this.search(trimmed);
        if (!matches.length) {
            this.results.innerHTML = (new TVStaticText(new TVRect(), `No matches for "${trimmed}".`)).setDrawOptions({ presentation: "search-empty" }).renderMarkup();
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
    TVViewGalleryDialog,
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
