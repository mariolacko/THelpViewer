# TurboVision JS — API Documentation

The current behavioural audit and implementation order are tracked in
[TurboVision JS Audit](TurboVision%20JS%20Audit.md).

THelpViewer uses a modular JavaScript framework inspired by Borland's TurboVision TUI toolkit. The runtime assets are served from `www/assets/`:

| File | Purpose |
|------|---------|
| `tv-core.js` | Core widget classes, dialog manager, theme engine, utility functions |
| `tv-dialogs.js` | Standard dialogs (About, Search, Calculator, Calendar, Colors, ASCII Table, MIDI Player) |
| `tv-games.js` | Game dialogs and rules (Puzzle, Tetris, Minesweeper, BreakOut, Sokoban, Lines, Reversi, Ludo, Snake) |
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
- **TVStaticText** — Renders text or HTML. `constructor({tag, text, html, className, attrs})`.
- **TVLabel** — Text label with hotkey markup. With `forId` it emits a native
  `<label for="…">`; otherwise it emits a presentational `<span>`.
- **TVInputLine** — `<input>` element. `constructor({className, attrs})`.
- **TVGroup** — Container with children. `constructor({tag, className, attrs, children, html})`.
- **TVListViewer** — Static list. `constructor({tag, className, attrs, items})`.
- **TVListBox** — Interactive selectable list. `setItems(items, index)`,
  `select(index)`, `bind({onSelect, onActivate})`; click selects and
  double-click/Enter activates.
- **TVVerticalListViewer** — List with scrollbar integration, roving tab focus,
  Arrow, Home/End and Page Up/Down keyboard navigation, and a passive
  scrollbar while its dialog is inactive.
- **TVVerticalScrollArea** — Generic scroll container.
- **TVMenuBox** — Menu popup with items.
- **TVCheckBoxes** — Native checkbox group rendered with DOS `[ ]` / `[X]`
  marks; supports click, Space, focus and disabled state.
- **TVRadioButtons** — Native mutually exclusive radio group rendered with DOS
  `( )` / `(·)` marks. An explicit `name` may be supplied.
- **TVButtonStrip** — Row of buttons.
- **TVButton** — Button with optional dialog shadow. `constructor({labelMarkup, dialog, className, ...})`.
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

### TVFrame & TVDialog

- **TVFrame** — Generates dialog window markup (titlebar, body, footer, borders).
- **TVDialog** — Managed dialog/window with overlay; it may be modal or non-modal.
  - `open()`, `close()`, `destroy()`, `center()`, `isOpen()`, `isActive()`
  - `close()` hides a reusable dialog; `destroy()` permanently removes a
    dynamic dialog, its drag listeners and its manager registration.
  - `bindCommonClose(callback)` — Bind the common close action
  - `bindDrag()` — Enable title bar drag
  - `setManager(manager, name)` — Register with TVDialogManager
  - `focusableElements()` — Return the current keyboard focus cycle
  - `onDialogKeyDown(event)` — Shared Escape, default Enter and Tab handling
  - `query(selector)` — Shortcut for `this.dialog.querySelector()`
  - Constructor options `modal`, `keyboard`, `escapeCloses` and
    `defaultButtonSelector` customize shared interaction without duplicating
    document-level key handlers.

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

### TurboVisionScrollbar

Custom scrollbar for `[data-tv-scroll-frame]` containers. Handles thumb drag, track clicks, arrow buttons, wheel events.

- `refresh()` — Re-observe replaced viewport content and redraw both axes.
- `setActive(active)` — Enable input for the active window or switch both axes
  to passive, non-interactive rendering.
- `destroy()` — Stop repeat/drag state and detach element/global listeners and
  the `ResizeObserver`.

### Theme Engine

- `applyThemePreset(preset)` — Apply "light", "dark", or "auto" theme
- `applyColorPalette(palette)` — Apply custom color palette from `DOS_COLORS`
- `readStoredThemePreset()` / `readStoredColorPalette()` — Read from localStorage

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

### Dialogs

| Class | Purpose |
|-------|---------|
| `TVAboutDialog` | About / splash screen |
| `TVSearchDialog` | Full-text search across topics |
| `TVAsciiTableDialog` | CP437 character table (0–255) |
| `TVCalculatorDialog` | DOS-style calculator |
| `TVCalendarDialog` | Month calendar with navigation and Gregorian leap-year handling |
| `TVColorsDialog` | Color palette customization editor |

### TVSearchDialog

- `search(query)` — Filter topics by query
- `renderResults(query)` — Update result list UI
- `moveSelection(delta)` — Navigate result list
- `openSelected()` — Open the highlighted result (override for custom navigation)

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
| `TVSnakeDialog` | Snake | 28×18 | ←→↑↓ move, Enter restart |

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
| `TVMenuBar` | Renders menu bar items and hotkeys |
| `TVStatusLine` | Renders status line items |
| `TurboVisionWindowResizer` | Window drag-move and resize, double-click maximize |
| `TurboVisionMenus` | Generated-page adapter for the shared `TVMenuController` |
| `TVApplication` | Main application coordinator |

### TVApplication

Entry point. Called via `TV.initTurboVision()`.

- `start()` — Calls `initTheme()`, `initChrome()`, `initLayout()`, `initShellWidgets()`
- `initTheme()` — Reads stored theme from localStorage, applies it
- `initChrome()` — Initializes menu bar and status line
- `initLayout()` — Calls `fillBorders()`, `fillDesktopPatterns()`, starts clock timer, binds resize
- `initShellWidgets()` — Initializes scrollbars, resizers, dialog manager, registers all dialogs, sets up screen saver with 5-minute idle auto-start

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
- Registered dialogs: about, puzzle, calendar, ascii, calc, colors, tetris, mines, breakout, sokoban, lines, reversi, search

The Help Files menu uses `product_name`, `version`, and `menu_name` from
`helps/catalog.json` to render product → version → file. Entries without
`product_name` are shown as direct Help Files items.

### BundleWindowManager

- `showIndex()` — Display bundle index (topic list)
- `showTopic(bundle, contextHex)` — Display a specific topic
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
