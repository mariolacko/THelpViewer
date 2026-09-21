# TurboVision JS — API Documentation

The behavioural audit and implementation order are maintained as internal
project documents and are not part of the public Docs catalog.

THelpViewer uses a modular JavaScript framework inspired by Borland's TurboVision TUI toolkit. The runtime assets are served from `www/assets/`:

| File | Purpose |
|------|---------|
| `tv-core.js` | Core widget classes, dialog manager, theme engine, utility functions |
| `tv-dialogs.js` | Standard dialogs (Context Help, About, File Open, Change Directory, Find/Search, Calculator, Calendar, Colors, ASCII Table, MIDI Player) |
| `tv-games.js` | Game dialogs and rules (Puzzle, Tetris, Minesweeper, BreakOut, Sokoban, Lines, Reversi, Ludo, Mastermind, Snake, Tron, Tower of Hanoi) |
| `tv-screensaver.js` | Screen saver base class and animated modes |
| `tv-highlight.js` | Pascal, C and ASM syntax highlighting |
| `tv-shell.js` | Menu bar, status line, window resizer, application bootstrap |
| `tv-bundle-app.js` | Single-page bundle viewer (catalog, window manager, Markdown renderer) |

All modules share a single namespace: `window.THelpViewerTV` (aliased as `TV`).
The syntax highlighter detects Pascal, C and ASM independently for each
contiguous code block, so one topic can safely contain examples in several
languages.

---

## tv-core.js

Core widget hierarchy and infrastructure.

### Widget Base Classes

- **TVWidget** — Base for all UI components. `constructor(root=null)`.
  `setHelpCtx()` and `getHelpCtx()` attach or resolve a Turbo Vision-style
  context identifier.
- **TVRect** — Character-cell bounds used by windows and dialogs. It mirrors
  Turbo Vision's `(x1, y1, x2, y2)` rectangle convention.
- **TVStaticText** — Renders static text with character-cell bounds. It accepts
  text, semantic formatting and bounds, but no HTML tag or arbitrary DOM
  attributes. `getText()`, `setText()` and `draw()` mirror the basic
  `TStaticText` contract.
- **TVLabel** — Text label with hotkey markup. With `forId` it emits a native
  `<label for="…">`; otherwise it emits a presentational `<span>`.
- **TVInputLine** — `<input>` element. `constructor({className, attrs})`.
- **TVGroup** — Container with children.
  `constructor({tag, role, name, children, html, x, y, w, h, helpCtx})`.
  Concrete views supply a semantic renderer role/name rather than raw DOM
  classes or attributes.
  `setCurrent(child)` makes `getHelpCtx()` inherit from the current child,
  matching the relevant part of `TGroup::getHelpCtx()`.
- **TVListViewer** — Static list. `constructor({tag, className, attrs, items})`.
- **TVListBox** — Interactive selectable list. `setItems(items, index)`,
  `select(index)`, `bind({onSelect, onActivate})`; click selects and
  double-click/Enter activates.
- **TVVerticalListViewer** — `TVListBox` subclass with scrollbar integration,
  shared row rendering and palette, roving tab focus,
  pointer-coordinate row selection, Arrow, Home/End and Page Up/Down keyboard
  navigation. Visibility is measured against the real viewport rectangle, so
  focus changes cannot introduce an offset between a drawn and clicked row.
  While its dialog is inactive, the scrollbar keeps its Turbo Vision palette
  but ignores input.
- **TVOutline** — Tree-oriented `TVVerticalListViewer` with shared selection,
  scrolling and activation plus expand/collapse state and Left/Right keyboard
  navigation. HELP Contents and Change Directory both use it.
- **TVVerticalScrollArea** — Generic scroll container.
- **TVMenuView** — Shared menu rendering base.
- **TVMenuBox** — `TVMenuView` popup subclass.
- **TVCheckBoxes** — Native checkbox group rendered with DOS `[ ]` / `[X]`
  marks; supports click, Space, focus and disabled state.
- **TVRadioButtons** — Native mutually exclusive radio group rendered with DOS
  `( )` / `(·)` marks. An explicit `name` may be supplied.
- **TVMultiCheckBoxes** — `TVCluster` subclass with configurable three-state
  DOS marks, keyboard-focusable buttons, disabled state and `aria-checked`.
- **TVTerminal** — Bounded append-only line buffer. `append(text)`, `clear()`
  and `bind(root)` update a fixed set of framed terminal rows.
- **TVEditor** and **TVIndicator** — Read-only document control with selection,
  `find()`, `findNext()`, cursor position reporting and explicit lifecycle.
  Markdown Docs windows instantiate this pair instead of using a styled
  viewport alone.
- **TVButtonStrip** — Row of buttons.
- **TVButton** — Dialog command button. Like Turbo Vision's `TButton`, it is
  identified by its title, command and `bfNormal`/`bfDefault`/`bfLeftJust`/
  `bfBroadcast` flags; `draw()`, `press()`,
  `makeDefault()` and `setState()` provide the basic control operations. It no
  longer represents menus or status-line items and has no `buttonKind`.
- **TVMenuItem** / **TVStatusItem** — Command descriptors drawn by
  `TVMenuView`/`TVMenuBox` and the status line, matching Turbo Vision's
  separation between `TButton`, `TMenuItem` and `TStatusItem`.
- **TVMessageBox** — Modal Promise-based message box with OK/Cancel and
  Yes/No/Cancel flag combinations, mnemonics and default-button keyboard
  handling.

### TVInfoBox

Reusable framed info-box borders (used for game info panels).

Static methods:
- `TVInfoBox.header(width, title)` → `"┌── Title ──┐"`
- `TVInfoBox.footer(width)` → `"└───────────┘"`
- `TVInfoBox.separator(width, title)` → `"├── Title ──┤"`
- `TVInfoBox.rowHtml(width, content, borderClass)` → `"│ content    │"` (as HTML with styled border span)
- `TVInfoBox.applyBorders(width, specs)` — Batch apply header/footer/separator to DOM elements.

Header, footer and both row-side glyphs inherit the same current frame color.

### TVFrame, TVWindow & TVDialog

- **TVFrame** — Generates dialog window markup (titlebar, body, footer, borders).
  Its active frame uses the Turbo Vision 2.0 double-line glyphs; the passive
  frame uses single-line glyphs and omits the close control. The close control
  is overlaid at columns 2–4 and the title is centered over one continuous
  frame line, matching `TFrame` rather than participating in the layout.
  `titleControlMarkup()` / `createTitleControl()` are the single renderer for
  bracketed title controls: brackets inherit the title color while the inner
  glyph uses the owner's frame-icon color. Dialog close, History close and the
  games' Hall of Fame `[H]` use this path.
- **TVWindow** — Shared `TVGroup` base and standard window-frame composition
  used by HELP, Docs and dialogs. On a passive standard window, the close and
  zoom cells remain in the title-row grid but become non-interactive
  single-line frame segments. This preserves the centered caption and both
  frame corners while matching the inactive `TFrame` drawing.
  Standard close/zoom controls are semantic buttons. Close additionally acts
  on the original Turbo Vision mouse-down event, with propagation stopped
  before window activation can consume it; native click activation remains for
  keyboard input. The grow control always draws Turbo Vision 2.0's source-
  defined single-line `─┘` icon.
- **TVDialog** — `TVWindow` subclass constructed from `TVRect` bounds, a title
  and semantic options/content; it may be modal or non-modal. Callers do not
  provide CSS class names, close attributes or handwritten frame footers.
  - `open()`, `close()`, `destroy()`, `center()`, `isOpen()`, `isActive()`
  - `setSize({width, height})` — Change CSS dimensions and immediately redraw
    the affected character frame. Dynamic dialogs must use this instead of
    setting `--tv-dialog-width` or `--tv-dialog-height` directly.
  - `close()` hides a reusable dialog; `destroy()` permanently removes a
    dynamic dialog, its drag listeners and its manager registration.
  - `bindCommonClose(callback)` — Bind the common close action
  - `bindDrag()` — Enable title bar drag. While moving, the shared frame uses
    the single-line Turbo Vision drag glyphs and restores its active/passive
    frame after mouse release.
  - `setManager(manager, name)` — Register with TVDialogManager
  - `focusableElements()` — Return the current keyboard focus cycle
  - `onDialogKeyDown(event)` — Shared Escape, default Enter and Tab handling
  - `query(selector)` — Shortcut for `this.dialog.querySelector()`
  - Constructor options `modal`, `keyboard`, `escapeCloses` and
    `defaultButtonSelector` customize shared interaction without duplicating
    document-level key handlers. The `palette` option selects the owner palette
    (`dialog`, `viewer`, `calendar` or `ascii`) while the shared frame renderer
    keeps identical active/passive/drag semantics.
  - The `helpCtx` constructor option belongs to the dialog itself and is
    written to both its window and overlay roots. Application registration no
    longer maps dialog names to contexts.

### TVDialogManager

Manages dialog lifecycle, z-ordering, and active state.

- `register(name, dialog)` — Register a named dialog
- `unregister(name, dialog)` — Remove a dynamic dialog registration safely
- `registerWindow(name, element, commands)` — Register a managed window and
  its command handlers
- `setHostWindow(element, commands)` — Register the generated page's host
  window and its command handlers
- `open(name, {exclusive})` — Open a dialog (optionally closing others)
- `close(name)` — Close a dialog
- `bringToFront(name)` — Activate and focus a dialog
- `activateHostWindow()` — Deactivate all dialogs, activate host window
- `dispatchCommand(command)` — Send a command to the active dialog, viewer,
  document or host window
- `cycleTarget(delta)` — Activate the next or previous managed window/dialog
- `openTargets()` / `openWindowCount()` — Report currently usable managed targets
- `canDispatchCommand(command)` — Report whether the active target accepts a command
- `applyAllZIndices()` — Recalculate z-index stack
- `applyActiveStates()` — Update `is-window-active` / `is-window-inactive` classes
- `getHelpCtx()` — Return the active dialog/window/host context

URL-state restoration keeps every open modal dialog above ordinary windows
and makes the top modal active, even when an older serialized stack recorded
an invalid background position for it.

### Context Help

`TV_HELP_CONTEXTS` exports the application's `hc...` constants, including
`hcApplication`, menu contexts, HELP/Docs viewer contexts, individual
standard-dialog contexts and one context for each game. The constants are also
exposed directly on `THelpViewerTV` for Turbo Vision-style use.

- `elementHelpContext(element)` resolves `data-tv-help-ctx` through DOM owners.
- `TVMenuController.getHelpCtx()` returns the selected menu/root context.
- `resolveHelpContext()` prioritizes an open menu, focused view, active managed
  target and finally `hcApplication`.
- `TVHelpController` captures plain F1 and sends the resolved context to the
  application callback.
- Every concrete standard/game dialog passes its own `hc...` value to
  `TVDialog`; registration is deliberately context-agnostic.
- The bundle application loads `assets/tv-context-help.json`, a native UHF 2.0
  `THELPVIEWER.HLP` bundle, and passes the resolved `hc...` value directly to
  `BundleWindowManager.showTopic()`.
- THelpViewer Help therefore uses the same `TVWindow`, UHF renderer, right-edge
  `TVScrollBar`, frame controls and URL-state path as every converted HELP
  file. Back, Help Contents, Content, Search and Close stay in the global
  status line; no second navigation strip is rendered inside the window.
- Internal topic links, fixed-width tables and long text are handled by the
  existing UHF renderer. Restoring URL state reloads the same context bundle
  and selected topic.

The Help menu and `F1 Help` status command use the same context-resolution path
as the keyboard.

### TVDesktop

Small `TVGroup` owner shared by the generated-page and bundle applications.
It owns the desktop root, one `TVDialogManager`, border/background layout,
clock updates and the global load/resize lifecycle. Product-specific startup
and navigation remain in `TVApplication` and `TVBundleApp`.

### TVMenuController

Shared mouse and keyboard state machine used by both the generated-page shell
and the bundle viewer.

- `refresh()` — Discover and bind a newly rendered menu tree
- `openMenu(root)` / `closeMenus()` — Open or close the active top-level menu
- `openSubmenu(toggle)` / `closeSubmenu(popup)` — Manage nested menu levels
- `moveSelection(delta)` — Move the roving selection through enabled items
- `destroy()` — Remove the controller's document-level listeners
- Supports `F10`, Alt mnemonics, popup mnemonics, arrows, `Home`, `End`,
  `Enter`, Space, Tab/Shift+Tab and `Esc`, including remembered selection and
  focus restoration. Disabled commands are skipped by mouse, keyboard and
  mnemonic navigation.

The bundle desktop keeps one managed window per opened HELP bundle and one per
Markdown document. `F6`/`Shift-F6`, Window List, Tile and Cascade all operate
on the same `TVDialogManager` stack. Dynamic windows use distinct persisted
geometry keys, so moving or maximizing one does not overwrite another.
Markdown documentation uses a dedicated Editor palette: blue background with
yellow base text. These two colors stay fixed across themes and Viewer palette
customization; headings, links and syntax accents may use their own colors.

### TurboVisionScrollbar

Custom scrollbar for `[data-tv-scroll-frame]` containers. Handles thumb drag, track clicks, arrow buttons, wheel events.

- `refresh()` — Re-observe replaced viewport content and redraw both axes.
- `setActive(active)` — Enable input for the active window or make both axes
  non-interactive without changing their Turbo Vision scrollbar palette.
- `destroy()` — Stop repeat/drag state and detach element/global listeners and
  the `ResizeObserver`.

### Theme Engine

- `initializeTVTheme()` — Shared shell/bundle startup, including stored theme
  and palette restoration
- `applyThemePreset(preset)` — Apply "light", "dark", or "auto" theme
- `applyColorPalette(palette)` — Apply custom color palette from `DOS_COLORS`
- `setColorPaletteAttribute(palette, index, attr)` — Update every Color-dialog
  view that references the same 1-based `cpAppColor` index
- `readStoredThemePreset()` / `readStoredColorPalette()` — Read from localStorage

The default color source is the exact 135-entry Turbo Vision 2.0
`cpAppColor`. `COLOR_GROUPS` does not own duplicate colors: Viewer and Puzzle,
for example, both reference indexes 8–14. CSS first resolves an owner palette
for a window/dialog and then derives its current active, passive or dragging
frame state. Common list and scrollbar controls inherit from that owner.

### Utility Functions

- `measureCells()` — Returns `{width, height}` of a monospace character cell
- `fillBorders()` — Measures cells and fills `data-tv-border-fill` / `data-tv-border-side` elements
- `fillDesktopPatterns()` — Fill desktop background pattern elements
- `escapeHtml(text)` — HTML entity escaping
- `renderHotkeyMarkup(text)` — Convert `~X~` to `<span class="tv-hotkey">X</span>`
- `displayCp437Char(code)` — Convert a CP437 byte to a display character
- `updateClocks()` — Update all `[data-tv-clock]` elements with current time
- `dosColor(index)` — Get CSS color string for DOS color index (0-15)

### Key Constants

- `DOS_COLORS` — 16 standard DOS color strings
- `THEME_PRESETS` — 5 predefined theme configurations
- `TV_COMMANDS` — Shared `menu`, `close`, `zoom`, `resize`, `next`,
  `previous`, `ok`, `cancel` and `default` command identifiers
- `PUZZLE_START`, `PUZZLE_HIGHLIGHT_MAP` — 15-puzzle initial state

---

## tv-dialogs.js

Standard application dialogs.

Dialog client areas are composed from shared TVision JS widgets. About,
Context Help, Widget Gallery, Open a File, Change Directory, ASCII Table,
Calculator, Calendar, Colors, MIDI Player, Find and Search assemble labels,
inputs, buttons, status text, lists/outlines, clusters and History controls as
`TVGroup` children or shared widget renderers rather than handwritten
dialog-specific HTML. Their dynamic cells and result rows use the same
`TVButton`, `TVStaticText` and list objects. `TVFrame.dialogMarkup()` accepts a
single widget or an array of widget sections and renders that tree at the
shared dialog boundary. CSS remains responsible for character-cell geometry
and palette presentation, not control identity or behaviour.

### Dialogs

| Class | Purpose |
|-------|---------|
| `TVAboutDialog` | About / splash screen |
| `TVWidgetGalleryDialog` | Interactive gallery for shared labels, inputs, choices, list focus/activation and scrolling, static/framed information, buttons and message boxes |
| `TVFileOpenDialog` | Keyboard-accessible virtual file picker for generated HELP bundles and Markdown documentation, with persistent history |
| `TVChangeDirectoryDialog` | Turbo Vision-style virtual directory tree with Chdir, Revert and shared persistent History |
| `TVFindDialog` | Active-window Find dialog with persistent shared History |
| `TVSearchDialog` | Full-text search across topics |
| `TVAsciiTableDialog` | CP437 character table (0–255) |
| `TVCalculatorDialog` | DOS-style calculator |
| `TVCalendarDialog` | Month calendar with navigation and Gregorian leap-year handling |
| `TVColorsDialog` | Color palette customization editor |

`TVColorsDialog` follows the Turbo Vision 2.0 `TColorDialog` 61×18 cell
geometry from `colorsel.cpp`: Group and Item lists, 4×4 foreground and 4×2
background selectors, a two-line sample, and the original OK/Cancel controls.
THelpViewer additionally provides Default, which restores only the selected
item's original `cpAppColor` attribute, and Reset All, which previews the full
default palette. OK persists the preview; Cancel/Escape restores the palette
that was active when the dialog opened.
Its list states use the original color attributes (`0x30`, `0x2F`, `0x3E`),
and only the list that owns keyboard focus uses the focused-row attribute.
The selectors support arrow-key navigation.

### TVSearchDialog

- `search(query)` — Filter topics by query
- `renderResults(query)` — Update result list UI
- `moveSelection(delta)` — Navigate result list
- `openSelected()` — Open the highlighted result (override for custom navigation)

### TVFindDialog

- `configure({find, findAgain, targetLabel})` — Bind the dialog to the active
  read-only Editor or HELP viewport.
- `open(initialQuery)` — Open with an optional query and refresh History.
- `performFind()` / `findAgain()` — Execute the supplied target callbacks.
- The bundle Search menu exposes Find (`Ctrl+F`), Find Again (`Ctrl+L`) and
  topic-index Search (`F3`) as distinct commands.
- Find is disabled without an active HELP/Docs window. Find Again remains
  disabled until the active target has a previous query.

### TVFileOpenDialog

- `configure(entries, onOpen)` — Populate the browser-safe virtual filesystem and install its open callback
- `setDirectory(path)` — Select the virtual directory shared with Change Directory.
- `TVFileList`, `TVHistory`, `TVHistoryViewer` and `TVHistoryWindow` provide the
  reusable file-list, persistent model, list and popup roles. The old
  `TVFileListBox` export remains a compatibility alias.
- `TVHistoryWindow` renders the source-compatible framed popup shared by File
  Open, Change Directory and Find. Its default geometry is 32×8 character
  cells, covering the 28-cell File Open input and its three-cell History
  trigger without padding outside the frame. Like original `THistoryWindow`
  with `wfClose`, it owns a bracketed close control in its top frame. It also
  owns popup visibility, `aria-expanded` state, Escape handling,
  outside-click dismissal and focus return to the History button. Pointer
  activation happens on mouse-down like the original `THistory::handleEvent`;
  keyboard activation remains a native button click. An empty history remains
  an active control and opens the same closable empty window; it is not
  disabled based on its current item count.
- `TVHistoryWindow.triggerMarkup()` is the single three-cell History-button
  composition used by File Open, Change Directory and Find.
- The source `THistory::icon` value `\xDE~\x19~\xDD` is rendered as two
  explicit half-cell CSS fills around the arrow. This preserves the original
  History sides/button palette mapping without relying on browser rendering of
  Unicode `▐`/`▌` glyphs, which can expose the blue InputLine in Safari.
- The layout follows Turbo Vision 2.0 `TFileDialog`: one unframed, two-column
  `TFileList`, a horizontal scrollbar, Name input with a three-cell History
  control, Open/Cancel buttons and the two-line `TFileInfoPane` at the bottom.
- HELP and DOCS roots and their catalog groups appear in the same list as
  directory entries ending in `\`; `..\` navigates to the parent directory.
- Arrow keys move within a column, Left/Right move by one eight-row column,
  Page Up/Down move by two columns, and double-click/Enter activates an entry.
- `Alt+N`, `Alt+F` and `Alt+O` focus Name, the file list and Open respectively.
- The ten most recently opened catalog entries are stored in local storage;
  missing catalog entries are ignored.
- Open is available during asynchronous HELP/DOCS catalog loading. It opens
  immediately with a visible loading row, refreshes itself when the catalogs
  arrive, and shows an explicit empty-state row if neither catalog has files.

### TVChangeDirectoryDialog

- Uses the same normalized HELP/DOCS virtual tree and History implementation as
  File Open.
- Chdir updates File Open's current directory; Revert restores the directory
  that was active when the dialog opened.
- Directory input, `TVOutline` tree, history popup, keyboard mnemonics and the
  shared list scrollbar are available without browser filesystem privileges.

## tv-screensaver.js

### TVScreenSaver

Fullscreen overlay with animated modes.

- `start()` — Start the selected saver instance and preserve current focus
- `stop()` — Dismiss, detach resize handling and restore focus (also triggered by click or keypress)
- `TVScreenSaver.installIdleStart()` — Install the shared five-minute idle trigger once per page

Both the generated-page shell and bundle application install the same idle
trigger. Active modes remeasure and reinitialize after a browser resize.

Mode descriptions:
- **stars** — Falling star characters with random colors
- **bounce** — Bouncing "THelpViewer" text, color changes on wall bounce
- **clock** — Big ASCII-art clock with date
- **matrix** — Matrix-style falling green character streams

Constants: `SAVER_FPS = 15`, `SAVER_STAR_COUNT = 60`

---

## tv-games.js

Game dialog implementations. All extend `TVDialog`.

Game timers and CPU turns run only while their dialog is active. The dynamic
high-score name prompt is registered as a managed modal dialog, so opening it
also suspends the owning game until the prompt is destroyed.

### Common Patterns

- Each game has `open()` → `super.open()` → `newGame()` → `fillBorders(this.dialog)`
- Info panels use `TVInfoBox` for framed borders
- Best score stored in localStorage as JSON `{score, name}` via `loadBest(key)` / `saveBest(key, score, name)`
- `showBestNamePrompt(ownerDialog, score, callback)` — Shows a managed modal name input dialog on new high score

### Games

| Class | Game | Grid | Key Controls |
|-------|------|------|-------------|
| `TVPuzzleDialog` | 15-puzzle | 4×4 | Click tiles |
| `TVTetrisDialog` | Tetris / Pentix | 12×18 | ←→ move, ↑ rotate, ↓/Space drop, P pause, X pentix |
| `TVMinesDialog` | Minesweeper | 9×9 (10 mines) | Click or Space/Enter reveal, Right-click or F flag, arrows/Home/End move cursor; first reveal is safe |
| `TVBreakOutDialog` | BreakOut | 14×20 | ←→ paddle, Space launch |
| `TVSokobanDialog` | Sokoban | Variable (5 levels) | ←→↑↓ move, R restart, U undo |
| `TVLinesDialog` | Color Lines | 9×9 | Click select + click destination |
| `TVReversiDialog` | Reversi vs AI | 8×8 | Click to place, N new game |
| `TVLudoDialog` | Ludo | 11×11 path map | Roll, click legal piece |
| `TVMastermindDialog` | Mastermind | 4 pegs, 6 colors, 10 turns | 1–6 choose color, ←→ select peg, Enter/G guess, N new |
| `TVTronDialog` | Tron Light Cycles | 30×18 | P1 W/A/S/D, P2 arrows, P pause, N new round |
| `TVHanoiDialog` | Tower of Hanoi | 3 towers, 5 disks | ←→/1–3 focus, Enter/Space select or move, drag, U undo, N new |
| `TVSnakeDialog` | Snake | 28×18 | ←→↑↓ move, Enter restart |

All twelve games use the same persistent, sorted ten-entry Hall of Fame. The
dialog root of every game owns a distinct `hcPuzzle` … `hcTron` context, and
`THELPVIEWER.HLP` contains the corresponding UHF topics, so F1 always describes
the active game rather than falling back to the generic Games topic. The
pure `MastermindGame` rule class correctly handles repeated colors when
calculating exact and misplaced pegs. Its 64-column dialog reserves an inset around the
board and keeps all color, action and status controls inside the client area.
`TronGame` applies both queued directions before resolving a tick, including
same-cell collisions, while `TVTronDialog` pauses its timer whenever another
window is active. `HanoiGame` owns legal moves and reversible move history;
`TVHanoiDialog` exposes the same actions through focus, keyboard, click and
drag-and-drop.

### Tetris Specifics

- 28 figures: 7 standard tetris (indices 0–6) + 21 pentix (7–27)
- `TETRIS_FIGURES` — Array of `[row, col]` coordinate pairs
- `TETRIS_CROT` — Rotation center per figure
- `TETRIS_COLORS` — 7 colors
- `TETRIS_DELAYS` — Level-based drop speeds (1600ms → 80ms)
- The `Next` preview uses a 7×7 grid, keeping at least one empty cell
  between every Tetris/Pentix figure and its frame.
- Ghost piece rendering (transparent preview where piece will land)

---

## tv-shell.js

Application shell: menus, status bar, window management, initialization.

### Classes

| Class | Purpose |
|-------|---------|
| `TVMenuBar` | `TVMenuView` subclass that renders menu bar items and hotkeys |
| `TVStatusLine` | Renders status line items |
| `TurboVisionWindowResizer` | Window drag-move and resize, double-click maximize |
| `TurboVisionMenus` | Generated-page adapter for the shared `TVMenuController` |
| `TVApplication` | Main application coordinator |

### TVApplication

Entry point. Called via `TV.initTurboVision()`.

- `start()` — Initializes theme, chrome, shared desktop/widgets and layout
- `initTheme()` — Reads stored theme from localStorage, applies it
- `initChrome()` — Initializes menu bar and status line
- `initLayout()` — Delegates border/background, clock and resize ownership to
  `TVDesktop.startLayout()`.
- `initShellWidgets()` — Creates `TVDesktop`, initializes scrollbars and
  resizers, registers dialogs and sets up the five-minute idle screen saver.

### TurboVisionWindowResizer

- Draggable title bar (move), resize handle (bottom-right corner)
- `maximize()`, `restore()`, `toggleMaximize()`
- Persists geometry to localStorage per optional `data-tv-window-storage-key`
- `destroy()` persists the final geometry and detaches drag, handle and
  `beforeunload` listeners.

### TVAppContext

Reads configuration from `data-tv-*` body attributes:
- `helpHref`, `indexHref`, `pageKind`, `statusHint`, `topicContext`, `topicHref`

---

## tv-bundle-app.js

Single-page application for browsing help file bundles.

### Classes

| Class | Purpose |
|-------|---------|
| `TVLoadingDialog` | Progress bar during bundle download |
| `BundleWindowManager` | Multi-window help file viewer with cascade/tile |
| `TVBundleApp` | Main bundle application |

### TVBundleApp

- `start()` — Loads catalog, handles URL params, shows welcome
- `_loadCatalog()` — Fetches `helps/catalog.json` and `docs/catalog.json`
- `_openDocWindow(filename, markdown)` — Opens rendered Markdown in a doc window (z-index 5, above help windows but below menu bar)
- `_registerDialog(name, factory)` — Creates and registers a dialog with the dialog manager
- Registered dialogs include About, File Open, Change Directory, Find, topic
  Search, the utility dialogs and all twelve games including Tron and Hanoi.
- Find targets the currently active HELP or Docs window through `TVEditor`;
  HELP viewports receive a lifecycle-managed read-only adapter only when first
  searched.

The Help Files menu uses `product_name`, `version`, and `menu_name` from
`helps/catalog.json` to render product → version → file. Entries without
`product_name` are shown as direct Help Files items.

The public Docs catalog and static site export omit internal files named
`* Audit.md` or `* RE Notes.md`. Markdown links are resolved inside the viewer;
repository-relative `docs/...` links in the root README are translated to the
public Docs root instead of opening a broken `docs/docs/...` URL.

### BundleWindowManager

- `showIndex()` — Display bundle index (topic list)
- `showTopic(bundle, contextHex)` — Display a specific topic
- `showContents(bundle)` — Display hierarchical contents through `TVOutline`
- `goBack()` — Navigate history
- `tile()`, `cascade()` — Arrange open windows
- `closeAll()` — Close all open help windows

### renderMarkdown(md)

Minimal Markdown-to-HTML converter.

Supported syntax: headings (`# H1` through `###### H6`), bold (`**text**`), italic (`*text*`), inline code, links, unordered/ordered lists, horizontal rules, fenced code blocks, tables (`| col | col |`).

### URL Parameters

- `?file=<name>` — Auto-load a help bundle by catalog name
- `?topic=<hex>` — Navigate directly to a topic (requires `?file=`)
- `?search=<query>` — Open search dialog with pre-filled query
- `?docs=<file.md>` — Open a documentation Markdown file

### Z-Index Hierarchy

The viewer uses a fixed z-index stack for layering:

| Layer | z-index | Element |
|-------|---------|---------|
| Desktop pattern | 0 | Background |
| Help windows | 1 | `tv-window` |
| Doc windows | 5 | Markdown document viewer |
| Dialog overlays | 10 | `TVDialog` overlays |
| Menu bar | 10 | `.tv-menu-bar` (position: relative) |
| Menu popups | 20 | Dropdown menu panels |
| Submenus | 25 | Nested submenu panels |
| Modal overlay | 9999 | Loading dialog |

### Data Format

Bundle JSON structure:
```json
{
  "window": { "cols": 80, "rows": 24, ... },
  "header_label": "...",
  "index_label": "...",
  "index_entries": [{ "context_hex": "0001", "title": "..." }, ...],
  "topics": [{ "context_hex": "0001", "title": "...", "html": "...", "text": "..." }, ...],
  "search_index": ["term1", "term2", ...],
  "source_name": "TURBO.TPH"
}
```
