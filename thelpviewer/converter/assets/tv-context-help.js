// THelpViewer's native UHF context-help bundle and fallback window.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    TVRect,
    TVScroller,
    TVWindow,
    TVPoint,
    TVEvent,
    evMouseDown,
    evCommand,
    wnNoNumber,
    normalizeHelpContext,
    TV_HELP_CONTEXTS,
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
    hcHelpViewer,
    hcAbout,
    hcFileOpen,
    hcChangeDirectory,
    hcFind,
    hcColors,
    hcWidgetGallery,
    hcMidiPlayer,
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
    hcStatistics,
    hcSystemInformation,
} = TV_HELP_CONTEXTS;

const TV_CONTEXT_HELP_TOPICS = Object.freeze({
    [hcApplication]: { title: "THelpViewer", text: "Use the menu bar to open HELP files, documentation, tools and games.\n\nF10 activates the menu bar. F1 opens help for the current view. F6 and Shift-F6 cycle windows." },
    [hcSystemMenu]: { title: "System menu", text: "The system menu contains utilities, Colors, Widget Gallery, System Information, screen savers and theme selection. About is available from the Help menu." },
    [hcHelpFiles]: { title: "Help Files", text: "Open installs a HELP or Docs file. Catalog submenus open a source directly. The viewer preserves links between related files when the target exists." },
    [hcDocuments]: { title: "Documents", text: "Documentation opens in a read-only Editor-style window. Use Ctrl-F to find text and Ctrl-L to find the next occurrence." },
    [hcSearch]: { title: "Search", text: "Find searches the active HELP or Docs window. Find Again repeats its query. Search Topics searches the current help bundle index." },
    [hcGames]: { title: "Games", text: "Games share Turbo Vision dialogs, keyboard focus, inactive-window pause policies and a server-wide ten-entry Hall of Fame with local fallback." },
    [hcWindows]: { title: "Windows", text: "Tile, Cascade and Window List arrange managed windows. F5 zooms, F6 selects the next window and Alt-F3 closes the active target." },
    [hcContextHelp]: { title: "Context Help", text: "This is THelpViewer's own context-sensitive help. Each view and menu item carries an hc... identifier, following Turbo Vision's helpCtx model." },
    [hcAbout]: { title: "About", text: "Shows the application version and authors. The version is read from the running package metadata." },
    [hcFileOpen]: { title: "Open a File", text: "Choose a HELP or Docs file from the two-column list. The down-arrow opens recent files; press it again or Escape to close the history." },
    [hcChangeDirectory]: { title: "Change Directory", text: "Select a virtual HELP/DOCS directory. Chdir applies it to Open a File, Revert restores the initial path and the arrow opens directory history." },
    [hcFind]: { title: "Find", text: "Enter text to search in the active HELP or Docs window. The arrow opens previous queries." },
    [hcColors]: { title: "Colors", text: "Choose a group and item, then edit its DOS foreground/background attribute. Default restores one item; Reset All restores the complete palette." },
    [hcWidgetGallery]: { title: "Widget Gallery", text: "Exercises shared labels, inputs, lists, clusters, scrollbars, buttons, static text, terminal and message-box components." },
    [hcMidiPlayer]: { title: "CD/MIDI Player", text: "The compact view contains the display and transport controls. More reveals the track list and external sources inside the resized dialog frame." },
    [hcHelpViewer]: { title: "HELP viewer", text: "Links open topics or external companion HELP files. Use Back, Index, Contents and Search from the status line or menus." },
    [hcDocumentViewer]: { title: "Document viewer", text: "Markdown is displayed with the read-only Editor palette. The lower-left indicator reports the current line and column." },
    [hcDialog]: { title: "Dialog", text: "Tab and Shift-Tab move focus. Enter activates the default button and Escape closes the dialog unless the control uses Escape itself." },
    [hcCalendar]: { title: "Calendar", text: "Browse months and years with the arrow controls. Date calculations use Gregorian leap-year rules." },
    [hcAsciiTable]: { title: "ASCII Table", text: "Shows character codes and glyphs using the configured DOS code page presentation." },
    [hcCalculator]: { title: "Calculator", text: "Use number and operation buttons or the keyboard. Escape is reserved by the calculator and does not close it." },
    [hcScreenSaver]: { title: "Screen saver", text: "Choose a mode, including DOS Navigator's Projector, from the system menu. Mouse or keyboard input stops the saver and restores the previously focused control." },
    [hcPuzzle]: { title: "Puzzle", text: "Move a tile next to the blank square with the mouse or arrow keys. Solve the shuffled 4 x 4 board in as few moves as possible." },
    [hcTetris]: { title: "Tetris", text: "New starts a game. Use Left/Right to move, Up to rotate, Down to drop faster and P to pause. Pentix toggles the extended pieces." },
    [hcMines]: { title: "Mines", text: "Reveal safe squares and mark suspected mines. The game pauses while its window is inactive." },
    [hcBreakOut]: { title: "BreakOut", text: "Move the paddle, keep the ball in play and clear the bricks. The game timer pauses while another window is active." },
    [hcSokoban]: { title: "Sokoban", text: "Push every crate onto a goal. Arrow keys move the player; crates can be pushed but not pulled. Enter advances after a solved level. Hall of Fame ranks the level reached first, then total moves." },
    [hcLines]: { title: "Lines", text: "Move coloured balls to form scoring lines. Selecting and moving a ball consumes a turn unless a line is completed." },
    [hcReversi]: { title: "Reversi", text: "Place a disc that brackets one or more opposing discs. The player with the most discs when no move remains wins." },
    [hcLudo]: { title: "Ludo", text: "Roll the die and move a legal piece around the board. Bring all of your pieces home before the other players." },
    [hcMastermind]: { title: "Mastermind", text: "Build a colour guess and submit it. Feedback reports correct colours in the correct and incorrect positions." },
    [hcSnake]: { title: "Snake", text: "Use the arrow keys to steer. Eat food to grow without hitting the wall or your own body." },
    [hcHanoi]: { title: "Tower of Hanoi", text: "Move the stack to another peg without placing a larger disc on a smaller one. Use mouse, keyboard and the move history." },
    [hcTron]: { title: "Tron Light Cycles", text: "Steer both cycles simultaneously and avoid every trail. The timer pauses while the game window is inactive." },
    [hcStatistics]: { title: "Server Statistics", text: "Browses aggregate visits, active viewing intervals for HELP files, documents, dialogs and games, search and link outcomes, environment and coarse performance intervals. Target time pauses when another window or browser tab becomes active. No search text, exact timing, IP address, cookie, visitor ID, full referrer or raw user agent is stored." },
    [hcSystemInformation]: { title: "System Information", text: "Shows local application, browser, display, locale, storage and capability information plus server status and catalog counts. Opening it does not submit these details to statistics." },
});

const TV_CONTEXT_HELP_BUNDLE_URL = "assets/tv-context-help.json?v=20260927e";
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
    const lines = content.map((line) => {
        const raw = String(line || "");
        if (raw === "[rule]") {
            return '<div class="tv-context-help-line tv-context-help-rule" aria-hidden="true"></div>';
        }
        return `<div class="tv-context-help-line">${raw ? renderContextHelpInline(raw) : "&nbsp;"}</div>`;
    }).join("");
    return [
        '<div class="tv-document tv-context-help-document">',
        `<div class="tv-topic-heading">${escapeHtml(topic?.title || "Help")}</div>`,
        lines,
        "</div>",
    ].join("");
}

class TVHelpViewer extends TVScroller {
    constructor(bounds, bundle, content = "") {
        super(bounds);
        this.bundle = bundle;
        this.content = String(content || "");
        this.onContentClick = (nativeEvent) => {
            this.dispatchEvent(new TVEvent(evMouseDown, { infoPtr: this, nativeEvent }));
        };
        this.setHelpCtx(hcHelpViewer);
    }

    bindRoot(root) {
        this.root?.removeEventListener("click", this.onContentClick);
        super.bindRoot(root);
        this.root?.addEventListener("click", this.onContentClick);
        return this;
    }

    handleEvent(event) {
        if (event.what !== evMouseDown || event.nativeEvent?.type !== "click") { return; }
        const link = event.nativeEvent.target?.closest?.(
            "[data-tv-nav], a[data-letter], [data-tv-topic-tag-key], "
            + "[data-tv-uhf-link], [data-tv-bundle-topic], [data-tv-topic-alias], "
            + "[data-tv-source-file], [data-tv-context-help-topic]"
        );
        if (!link || !this.root?.contains(link)) { return; }
        if (link.tagName === "A" && !String(link.getAttribute("href") || "").startsWith("#")
            && (event.nativeEvent.ctrlKey || event.nativeEvent.metaKey || event.nativeEvent.shiftKey)) { return; }
        event.nativeEvent.preventDefault();
        event.what = evCommand;
        event.command = "help-link";
        event.infoPtr = link;
    }

    draw() {
        const attrs = Object.entries(this._drawAttrs({ "data-tv-help-viewer": true }))
            .map(([name, value]) => `${name}="${escapeHtml(String(value))}"`)
            .join(" ");
        return `<div class="tv-help-viewer" ${attrs}>${this.content}</div>`;
    }

    setContent(content) {
        this.content = String(content || "");
        if (!this.root) { return; }
        this.root.innerHTML = this.content;
        const viewport = this.root.closest("[data-tv-viewport]");
        if (viewport) {
            viewport.scrollTop = 0;
            viewport.scrollLeft = 0;
        }
        window.requestAnimationFrame(() => {
            const frame = this.root?.closest("[data-tv-scroll-frame]");
            frame?.querySelector(".tv-scrollbar")?._tvScrollbar?.refresh();
        });
    }

    destroy() {
        this.root?.removeEventListener("click", this.onContentClick);
        super.destroy();
        this.viewport = null;
        this.bindRoot(null);
    }
}

class TVHelpWindow extends TVWindow {
    constructor(bounds, bundle, title, number = wnNoNumber) {
        super(bounds, title, number);
        this.bundle = bundle;
        this.sourceFile = bundle?._catalogFile || "";
        this.currentView = "index";
        this.currentTopic = null;
        this.currentLine = null;
        this.currentTag = null;
        this.outline = null;
        this.onLink = null;
        this.viewer = this.initViewer(this.getExtent(), bundle);
        this.insert(this.viewer);
        this.setHelpCtx(hcHelpViewer);
    }

    initViewer(bounds, bundle) {
        return new TVHelpViewer(bounds, bundle);
    }

    setContent(content) {
        this.viewer.setContent(content);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "help-link" && this.onLink) {
            this.onLink(event.infoPtr, event.nativeEvent);
            this.clearEvent(event);
        }
    }

    destroy() {
        this.viewer.destroy();
        this.bindRoot(null);
    }
}

class TVContextHelpViewer extends TVHelpViewer {}

class TVContextHelpWindow extends TVHelpWindow {
    static viewName = "context-help";
    static palette = "help";

    constructor() {
        super(new TVRect(0, 0, 72, 24), null, "THelpViewer Help");
        this.minSize = new TVPoint(40, 10);
        this.setHelpCtx(hcContextHelp);
        this.context = hcApplication;
        this.bundle = null;
        this.topicHistory = [];
        this.openAction = null;
    }

    initViewer(bounds, bundle) {
        return new TVContextHelpViewer(bounds, bundle);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "help-link"
            && event.infoPtr?.hasAttribute("data-tv-context-help-topic")) {
            this.showTopic(event.infoPtr.dataset.tvContextHelpTopic, { remember: true });
            this.clearEvent(event);
        }
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
        this.setContent(renderContextHelpTopic(topic));
    }

    goBack() {
        const previous = this.topicHistory.pop();
        if (previous == null) { return; }
        this.showTopic(previous);
    }

    open() {
        this.topicHistory = [];
        this.showTopic(this.context);
        this.show();
        this.openAction?.();
        void loadContextHelpBundle()
            .then((bundle) => {
                this.bundle = bundle;
                this.viewer.bundle = bundle;
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
}

Object.assign(TV, {
    TV_CONTEXT_HELP_TOPICS,
    TV_CONTEXT_HELP_BUNDLE_URL,
    loadContextHelpBundle,
    TVHelpViewer,
    TVHelpWindow,
    TVContextHelpViewer,
    TVContextHelpWindow,
});
})();
