# TurboVision JS — API Documentation

THelpViewer uses a modular JavaScript framework inspired by Borland's TurboVision TUI toolkit. The runtime assets are served from `www/assets/`:

| File | Purpose |
|------|---------|
| `tv-core.js` | Core widget classes, dialog manager, theme engine, utility functions |
| `tv-dialogs.js` | Standard dialogs (About, Search, Calculator, Calendar, Colors, ASCII Table) and Screen Saver |
| `tv-games.js` | Game dialogs (Puzzle, Tetris, Minesweeper, BreakOut, Sokoban, Lines, Reversi) |
| `tv-shell.js` | Menu bar, status line, window resizer, application bootstrap |
| `tv-bundle-app.js` | Single-page bundle viewer (catalog, window manager, Markdown renderer) |

All modules share a single namespace: `window.THelpViewerTV` (aliased as `TV`).

---

## tv-core.js

Core widget hierarchy and infrastructure.

### Widget Base Classes

- **TVWidget** — Base for all UI components. `constructor(root=null)`.
- **TVStaticText** — Renders text or HTML. `constructor({tag, text, html, className, attrs})`.
- **TVLabel** — Text label with hotkey markup. `constructor({text, forId, hotkey, ...})`.
- **TVInputLine** — `<input>` element. `constructor({className, attrs})`.
- **TVGroup** — Container with children. `constructor({tag, className, attrs, children, html})`.
- **TVListViewer** — Static list. `constructor({tag, className, attrs, items})`.
- **TVListBox** — Interactive selectable list. `setItems(items, index)`, `select(index)`, `bind({onSelect, onActivate})`.
- **TVVerticalListViewer** — List with scrollbar integration.
- **TVVerticalScrollArea** — Generic scroll container.
- **TVMenuBox** — Menu popup with items.
- **TVCheckBoxes** — Checkbox group.
- **TVButtonStrip** — Row of buttons.
- **TVButton** — Button with optional dialog shadow. `constructor({labelMarkup, dialog, className, ...})`.

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
- **TVDialog** — Modal dialog with overlay.
  - `open()`, `close()`, `center()`, `isOpen()`, `isActive()`
  - `bindCommonClose(callback)` — Bind close button + Escape key
  - `bindDrag()` — Enable title bar drag
  - `setManager(manager, name)` — Register with TVDialogManager
  - `query(selector)` — Shortcut for `this.dialog.querySelector()`

### TVDialogManager

Manages dialog lifecycle, z-ordering, and active state.

- `register(name, dialog)` — Register a named dialog
- `open(name, {exclusive})` — Open a dialog (optionally closing others)
- `close(name)` — Close a dialog
- `bringToFront(name)` — Activate and focus a dialog
- `activateHostWindow()` — Deactivate all dialogs, activate host window
- `applyZIndices()` — Recalculate z-index stack
- `applyActiveStates()` — Update `is-window-active` / `is-window-inactive` classes

### TurboVisionScrollbar

Custom scrollbar for `[data-tv-scroll-frame]` containers. Handles thumb drag, track clicks, arrow buttons, wheel events.

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
- `PUZZLE_START`, `PUZZLE_HIGHLIGHT_MAP` — 15-puzzle initial state

---

## tv-dialogs.js

Standard application dialogs and screen saver.

### Dialogs

| Class | Purpose |
|-------|---------|
| `TVAboutDialog` | About / splash screen |
| `TVSearchDialog` | Full-text search across topics |
| `TVAsciiTableDialog` | CP437 character table (0–255) |
| `TVCalculatorDialog` | DOS-style calculator |
| `TVCalendarDialog` | Month calendar with navigation |
| `TVColorsDialog` | Color palette customization editor |

### TVSearchDialog

- `search(query)` — Filter topics by query
- `renderResults(query)` — Update result list UI
- `moveSelection(delta)` — Navigate result list
- `openSelected()` — Open the highlighted result (override for custom navigation)

### TVScreenSaver

Fullscreen overlay with animated modes.

- `start(mode)` — Start saver: `"stars"`, `"bounce"`, `"clock"`, `"matrix"`
- `stop()` — Dismiss (also triggered by click or keypress)

Mode descriptions:
- **stars** — Falling star characters with random colors
- **bounce** — Bouncing "THelpViewer" text, color changes on wall bounce
- **clock** — Big ASCII-art clock with date
- **matrix** — Matrix-style falling green character streams

Constants: `SAVER_FPS = 15`, `SAVER_STAR_COUNT = 60`

---

## tv-games.js

Seven game dialog implementations. All extend `TVDialog`.

### Common Patterns

- Each game has `open()` → `super.open()` → `newGame()` → `fillBorders(this.dialog)`
- Info panels use `TVInfoBox` for framed borders
- Best score stored in localStorage as JSON `{score, name}` via `loadBest(key)` / `saveBest(key, score, name)`
- `showBestNamePrompt(desktop, score, callback)` — Shows name input dialog on new high score

### Games

| Class | Game | Grid | Key Controls |
|-------|------|------|-------------|
| `TVPuzzleDialog` | 15-puzzle | 4×4 | Click tiles |
| `TVTetrisDialog` | Tetris / Pentix | 12×20 | ←→ move, ↑ rotate, ↓/Space drop, P pause, X pentix |
| `TVMinesDialog` | Minesweeper | 9×9 (10 mines) | Click reveal, Right-click flag |
| `TVBreakOutDialog` | BreakOut | 14×20 | ←→ paddle, Space launch |
| `TVSokobanDialog` | Sokoban | Variable (5 levels) | ←→↑↓ move, R restart, U undo |
| `TVLinesDialog` | Color Lines | 9×9 | Click select + click destination |
| `TVReversiDialog` | Reversi vs AI | 8×8 | Click to place, N new game |

### Tetris Specifics

- 28 figures: 7 standard tetris (indices 0–6) + 21 pentix (7–27)
- `TETRIS_FIGURES` — Array of `[row, col]` coordinate pairs
- `TETRIS_CROT` — Rotation center per figure
- `TETRIS_COLORS` — 7 colors
- `TETRIS_DELAYS` — Level-based drop speeds (1600ms → 80ms)
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
| `TurboVisionMenus` | Menu popup interaction (open with mouse/keyboard, navigate) |
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
- Persists geometry to localStorage per `data-tv-window-id`

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
