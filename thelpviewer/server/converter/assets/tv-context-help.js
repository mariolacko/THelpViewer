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
    hcAccount,
    hcRegistration,
    hcRegistrationTokens,
    hcServerConfiguration,
    hcHelpPackages,
    hcDosPackages,
    hcMidiSources,
    hcDownloads,
    hcDosPrompt,
    hcUsers,
    hcGridDemo,
} = TV_HELP_CONTEXTS;

const TV_CONTEXT_HELP_TOPICS = Object.freeze({
    [hcApplication]: { title: "THelpViewer", text: "Use the menu bar to open HELP files, documentation, tools and games.\n\nF10 activates the menu bar. F1 opens help for the current view. F6 and Shift-F6 cycle windows." },
    [hcSystemMenu]: { title: "System menu", text: "The system menu contains utilities, Widget Gallery, System Information and screen savers. Signed-in users find Colors/Theme in their Configuration menu; guests use the system menu. About is available from Help." },
    [hcHelpFiles]: { title: "Help Files", text: "Open installs a HELP or Docs file. Catalog submenus open a source directly. The viewer preserves links between related files when the target exists." },
    [hcDocuments]: { title: "Documents", text: "Documentation opens in a read-only Editor-style window. Use Ctrl-F to find text and Ctrl-L to find the next occurrence." },
    [hcSearch]: { title: "Search", text: "Choose server-wide Search all HELP/Docs or Find in active window. Search Topics shows topics and their source; Find Again repeats the active window's query. The server builds a persistent global index." },
    [hcGames]: { title: "Games", text: "Games share Turbo Vision dialogs, keyboard focus, inactive-window pause policies and a server-wide ten-entry Hall of Fame with local fallback." },
    [hcWindows]: { title: "Windows", text: "Tile, Cascade and Window List arrange managed windows. F5 zooms, F6 selects the next window and Alt-F3 closes the active target." },
    [hcContextHelp]: { title: "Context Help", text: "This is THelpViewer's own context-sensitive help. Each view and menu item carries an hc... identifier, following Turbo Vision's helpCtx model." },
    [hcAbout]: { title: "About", text: "Shows the application version and authors. The version is read from the running package metadata." },
    [hcFileOpen]: { title: "Open a File", text: "Choose a HELP or Docs file from the two-column list. The down-arrow opens recent files; press it again or Escape to close the history." },
    [hcChangeDirectory]: { title: "Change Directory", text: "Select a virtual HELP/DOCS directory. Chdir applies it to Open a File, Revert restores the initial path and the arrow opens directory history." },
    [hcFind]: { title: "Find", text: "Choose Search all HELP/Docs or Find in active window. Alt-F focuses the input through its label. The arrow opens previous queries; Escape or its close control dismisses history." },
    [hcColors]: { title: "Colors", text: "All users can edit colors. Default restores one item; Reset All restores the complete palette. Colors are saved in this browser, not synchronized between accounts/devices." },
    [hcWidgetGallery]: { title: "Widget Gallery", text: "Exercises shared labels, inputs, lists, clusters, scrollbars, buttons, static text, terminal and message-box components." },
    [hcMidiPlayer]: { title: "CD/MIDI Player", text: "Play game MIDI with a SoundFont synthesizer and available cover art. RIFF/RMID and counted DOS MIDI are decoded to Standard MIDI. Click the progress bar to seek. More reveals tracks, Filter/history and Random next track. A cloud marks missing downloads; playing prioritizes them. A partial library shows ready tracks and the download-error count; Downloads contains album/member errors while other music remains usable. Downloads beside the account/clock shows the shared queue and album percentages without a separate automatic window. Closing the menu does not stop downloading. Local admins can rebuild the MIDI library." },
    [hcHelpViewer]: { title: "HELP viewer", text: "Links open topics or external companion HELP files. Use Back, Index, Contents and Search from the status line or menus. Native TextScreens keep original glyphs and palette colors with embedded fonts in the same window." },
    [hcDocumentViewer]: { title: "Document viewer", text: "Markdown is displayed with the read-only Editor palette. The lower-left indicator reports the current line and column." },
    [hcDialog]: { title: "Dialog and Clipboard", text: "Tab and Shift-Tab move focus. Enter activates the default button and Escape closes the dialog unless the control uses Escape itself. Clicking outside never closes a dialog; a modal dialog blocks background mouse input. System clipboard: Ctrl+Ins copies, Shift+Del cuts, Shift+Ins pastes. Native Cmd+C/X/V on macOS and Ctrl+C/X/V on Windows/Linux also work. Input Paste respects validators and length. HELP/Docs permit Copy only. Clipboard contents are never sent to the server." },
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
    [hcAccount]: { title: "Account and Login", text: "Login accepts an email/username with a Passkey or optional password. Account edits names/email, lists named Passkeys and can add/rename keys or set a 15-128-character password. New credentials require Passkey confirmation; password changes sign out other sessions. Security actions save separately from profile Save/Cancel. Role is read-only; private C usage/capacity is shown. User IDs, keys and private DOS files are preserved." },
    [hcRegistration]: { title: "Registration", text: "Enter first/last name, nickname, validated email and a single-use one-hour token, then approve your own Passkey creation. Administrator-created accounts retain their prepared profile and use a bound invitation. On success a MessageBox confirms registration; OK closes Register and Login. The first-admin token is printed in the server log." },
    [hcRegistrationTokens]: { title: "Registration Token", text: "Administrators generate one-hour tokens and select them from the valid-token list. Copy to Clipboard copies the generated or selected token value; it is disabled without a token. The status confirms success or selects the input for manual Ctrl+C/Cmd+C if browser clipboard access fails. Delete requires confirmation to revoke a token. Cancel, Escape or closing the confirmation keeps it valid." },
    [hcServerConfiguration]: { title: "Server Configuration and Rebuild", text: "Admin > Configuration groups settings, separate HELP/DOS/MIDI dialogs, users and rebuilds. Package Apply confirms every group of the edited content type and keeps originals, caches and private DOS data. The right-pane checkbox affects its current group; bottom Select All/Deselect All span that dialog. Rebuild opens confirmation/progress directly. Permanent data is under data/; generated shared C is var/dos/c." },
    [hcMidiSources]: { title: "MIDI Sources", text: "Choose a provider on the left and soundtrack albums on the right. The checkbox below Albums selects/clears that provider's albums; selecting all includes future albums. Bottom Select All/Deselect All affect every source and album, including enabling/disabling providers. Load albums indexes a provider without downloading music. Drafts survive window/source changes. Apply confirms changes; Close or cancelling confirmation saves nothing. Caches are retained; progress/errors use shared dialogs." },
    [hcHelpPackages]: { title: "HELP Packages", text: "Choose HELP versions by product group. The checkbox below the right pane selects/clears this group; bottom Select All/Deselect All span every HELP group. Description explains the highlighted edition. Apply confirms installation/removal of all groups; Close or cancelling confirmation changes nothing. Other dialogs keep independent drafts. Only HELP changes; originals, caches, published siblings and private DOS data are kept. Progress is in Downloads; errors use MessageBox." },
    [hcDosPackages]: { title: "DOS Packages", text: "Choose DOS categories on the left and packages on the right. The checkbox below Packages selects/clears this category; bottom Select All/Deselect All span all DOS categories. Required packages (UTILS and Volkov Commander) remain checked and cannot be uninstalled. Description follows the highlighted package; spaces align language flags after short names, scrolling with the text. Apply confirms all changes without modifying HELP/MIDI settings; while a job runs it shows Downloads, without a duplicate submission. Drafts survive window/category changes and completion. Private disks, caches and backups are kept. Close changes nothing." },
    [hcDownloads]: { title: "Downloads", text: "The Unicode down arrow and current percentage beside the account/clock opens the shared queue. Successful completion resets the counter and leaves only the arrow. New batches and retries start at 0%, excluding finished history. Completed downloads is the first submenu; its rows keep 100%. Show Downloads opens the same nonmodal progress dialog as Package Apply. More/Less shows waiting, running and failed HELP/DOS/MIDI groups; completed rows disappear from the list. Hide is on the left and More/Less on the right; Hide does not cancel work. Click a failed menu row for Retry, Remove or Cancel. The full name, error and notice wrap without truncation; buttons wrap on narrow screens. Retry repeats failed parts only; Remove clears only the queue entry, keeping files and selections. Closing [ ] or Escape changes nothing. Busy/deselected operations cannot be retried. Three regular lanes use different sources; each source permits one transfer, also for urgent playback. HTTP 429 waits affect that source only. Only administrators see HELP/DOS entries." },
    [hcDosPrompt]: { title: "DOS Prompt", text: "Run text/graphics DOS programs in a shared TVWindow using Worker DOSBox. C files load on demand; signed-in users save private overlays. Alt-Enter is native fullscreen, Alt-Pause pauses, Ctrl-Alt-R confirms restart and Ctrl-Alt-M opens the DOS menu. Zoom 2x enlarges the window. Host mounts are blocked. F1 goes to DOS; request this help from its menu." },
    [hcUsers]: { title: "Users and Add User", text: "Administrators manage profiles, validated emails, roles, enabled accounts and DOS capacity. Four buttons form a 2x2 block beside the extended list. Add User shares the registration-profile form: Create makes a member and a copyable one-hour, account-bound invitation without changing the admin session. The user opens Login > Register in their own browser to enroll a Passkey. Blank capacity inherits 64 MiB. Founding/last administrators remain protected; no Passkeys or DOS files are deleted." },
    [hcGridDemo]: { title: "Grid Viewer", text: "TVGridView displays rows and columns with optional headers and shared horizontal/vertical scrollbars. Arrow keys select cells; Hide headers toggles titles." },
});

const TV_CONTEXT_HELP_BUNDLE_URL = "assets/tv-context-help.json?v=20261015k";
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
        this.textScreens = [];
        this.onContentClick = (nativeEvent) => {
            this.dispatchEvent(new TVEvent(evMouseDown, { infoPtr: this, nativeEvent }));
        };
        this.setHelpCtx(hcHelpViewer);
    }

    bindRoot(root) {
        this.root?.removeEventListener("click", this.onContentClick);
        super.bindRoot(root);
        this.root?.addEventListener("click", this.onContentClick);
        this.textScreens.forEach(view => view.resolve(this.root));
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

    setContent(content, textScreens = []) {
        this.textScreens.forEach(view => { view.bindRoot(null); view.owner = null; });
        this.textScreens = textScreens;
        this.textScreens.forEach(view => { view.owner = this; });
        this.content = String(content || "");
        if (!this.root) { return; }
        this.root.innerHTML = this.content;
        this.textScreens.forEach(view => view.resolve(this.root));
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
        this.textScreens.forEach(view => { view.bindRoot(null); view.owner = null; });
        this.textScreens = [];
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

    setContent(content, textScreens = []) {
        this.viewer.setContent(content, textScreens);
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
