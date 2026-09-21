# Changelog

## [Unreleased]

### Formats
- Preserved Microsoft Advisor's qualified QuickHelp links such as
  `OS2.h.overview`, `WIN.h.contents`, and `LAN.h.contents` as real external
  HELP links; optional databases that are not installed are no longer rendered
  as non-interactive bold text
- Promoted **Borland Turbo Debugger TDH / Turbo Profiler TFH** from a
  diagnostic-only path to a decoded reader path for the known sample families,
  including runtime-aligned topics, hotspots, contents/index export, and UHF
  bundle output
- Added end-to-end bundle export regression coverage for the current TDH/TFH
  sample families, so legacy TDH, later 2.x TDH, and TFH are now checked
  through actual UHF bundle output instead of reader-local decode assertions
  only
- Hardened the TDH runtime decoder to rely on in-stream topic termination plus
  the confirmed 15-line page limit instead of a synthetic next-page upper bound
- Narrowed TDH alias fallback so text matching now runs only for unresolved
  out-of-range alias contexts after structural embedded-start detection
- Extended TDH decode metadata so alias-heavy high contexts now expose exact
  out-of-range, embedded, text-fallback, remaining-unresolved, and empty-
  placeholder context-id lists instead of counts only
- Hardened the TDH reader failure path so structurally matched but truncated
  payloads now raise a clean unsupported/truncated error instead of failing in
  intermediate decode bookkeeping
- Switched TFH format-handler detection to content-based probing in the shared
  exporter registry, so renamed TFH inputs no longer depend on a `.tfh`
  suffix to route into the TFH reader
- Recovered a direct resident TD 2.0 loader/seek anchor: `TD.EXE` opens
  `tdhelp.tdh`, reads the header into `0xA248`, buffers `0x258` words at
  `0x9D94`, and computes topic starts as `2 * header + 2 + sum(sign16(deltas))`
  instead of relying only on file-side inference

### Viewer & UI
- Fixed Calculator's display palette so its digits are white in every theme;
  the shared static-text color no longer overrides the display foreground.
- Restored the status-line hint for the active dialog, HELP topic/index,
  contents/tag view or Docs editor instead of resetting it to the generic
  application name whenever window focus changes.
- Removed `role` and `name` from the public `TVButton` constructor without a
  compatibility branch. Callers now provide the Turbo Vision-style `command`,
  while the shared renderer privately maps commands and button kinds to the
  browser DOM. Removed raw `className` and `style` from `TVStaticText` and
  `TVLabel`; palette colors and text kinds are rendered centrally.
- Removed raw `className` and `attrs` constructor options from `TVButton` and
  `TVGroup` without a compatibility path; dialogs, games, menus, status bars
  and application overlays now declare semantic commands, values, states,
  accessibility and bounds, while the shared renderer owns their DOM/CSS
  translation
- Completed the standard-dialog object-composition pass: About, Context Help,
  Widget Gallery, Open a File, Change Directory, ASCII Table, Calculator,
  Calendar, Colors, MIDI Player, Find and Search now assemble their client
  controls from the existing TVision JS groups, labels, inputs, lists,
  clusters, buttons and static text instead of dialog-specific HTML templates
- Let the shared `TVFrame` render a `TVWidget` or an array of widget sections
  directly, so concrete dialogs no longer need to flatten their object tree
  before passing it to `TVDialog`
- Rebuilt dynamic ASCII cells, calendar cells, Colors selectors/sample and
  Search result/empty rows with the same shared TV objects used for their
  initial dialog content
- Fixed the dynamic top `Contents` menu: nested submenu separators are no
  longer mistaken for separators of the parent `TVMenuBox`, which previously
  removed complete context-Help menu branches and left the popup empty
- Made HELP `Contents` reuse its enclosing `TVWindow` viewport and right-edge
  `TVScrollBar`; the embedded `TVOutline` no longer creates a second scrollbar
- Moved standard-dialog and per-game `helpCtx` ownership into each
  `TVDialog` constructor and removed the duplicate name-to-context maps from
  both application registration paths
- Began the object-composition migration for dialog clients: Context Help,
  Open a File, Change Directory and Find now assemble their content from
  `TVGroup`, `TVStaticText`, `TVLabel`, `TVInputLine`, `TVButton`,
  `TVVerticalListViewer`/`TVOutline` and the shared `TVHistoryWindow` trigger
  instead of dialog-specific HTML templates
- Added a distinct `hc...` context and UHF topic for every game, so F1 from
  Puzzle, Tetris, Mines, BreakOut, Sokoban, Lines, Reversi, Ludo, Mastermind,
  Snake, Tower of Hanoi or Tron opens that game's own help instead of the
  generic Games page
- Made shared dialog, HELP and Docs close controls act on the original Turbo
  Vision mouse-down event while retaining native button clicks for keyboard
  input, avoiding Safari's intermittently lost click activation
- Kept the shared History trigger active when its list is empty; Open a File,
  Change Directory and Find can now open and close an empty History window in
  Safari instead of presenting a disabled arrow
- Made the shared History trigger reproduce Turbo Vision's CP437 half-cell
  icon with palette-driven CSS halves, preventing Safari from exposing the
  blue InputLine behind the green sides next to the down arrow in Open,
  Change Directory and Find
- Routed THelpViewer's UHF context help through the same `BundleWindowManager`,
  `TVWindow`, topic renderer, edge scrollbars and global status line as every
  converted HELP file; the bundle application no longer opens a parallel
  context-help dialog with its own Back/Contents controls
- Unified game Hall of Fame `[H]` with the shared `TVFrame` title-control
  renderer, so its brackets use the title color and its glyph uses the same
  green icon color as standard frame controls
- Restored `THistoryWindow` ownership for File Open, Change Directory and Find:
  the framed History popup now covers the trigger, has its own close control,
  and preserves the original separate arrow/side palette roles
- Rebuilt context-sensitive F1 Help as a native UHF 2.0 `THELPVIEWER.HLP`
  bundle with internal topic links, fixed-width tables, long-topic scrolling
  and URL-state restoration of the selected topic
- Added Turbo Vision-style `hc...` help-context constants, inheritance through
  widgets/groups, menu/dialog/window resolution, F1 dispatch, and an in-app
  context Help dialog for menus, HELP/Docs windows, standard dialogs, tools,
  and games
- Matched the original `THistory` interaction more closely: its exact
  three-cell `0x72 / 0x20 / 0x72` icon reacts on mouse-down, toggles reliably,
  closes on Escape or an outside click, and uses the original arrow/side
  palette roles
- Replaced standard-window close and zoom anchors with semantic buttons so the
  shared frame controls activate consistently in Safari and Chromium
- Restored Turbo Vision 2.0's single-line `─┘` grow icon and passive-window
  coloring instead of deriving a double-line resize corner from the frame

### Tooling
- Added built-in ZIP member listing support to `tools/zip_implode.py`, so old
  PKZIP method-6 archives can be inspected with a repo-local tool instead of
  depending on external `unzip` / `7z` output
- Verified repo-local extraction of bundled TD/TPROF method-6 DOC members via
  `tools/zip_implode.py`

## [1.1.0] — 2026-04-09

### Features
- Introduced **UHF 2.0** as the normalized internal document format with structured
  `contents`, `index`, `topics`, topic aliases, exact-label navigation items,
  frozen rows, and line-addressable links
- Added **Microsoft QuickHelp (LN)** reader support for QuickBASIC, QuickC, PWB,
  LINK and related toolchain help files
- Added **Microsoft BW03** reader support for older CodeView DOS / OS/2 help
  files (`CV.HLP`, `CVP.HLP`)
- Added separate **Borland Turbo Debugger TDH / TFH** reader support with
  decoded text/topic-addressing for the current real TDH 1.0, later TDH 2.x,
  and TFH sample families
- Added **Norton Guide / Expert Help** reader support with parent-derived topic
  titles, real MENU traversal, see-also links, and generated contents/index data
- Added standalone **UHF JSON writer** and made the web bundle transport
  consistently use compressed `.json.gz`
- Added bundle-level **table of contents trees** and viewer support for
  Contents windows and menu-driven navigation from `contents[]`
- Added cross-file and symbolic link targets in UHF:
  `file=`, `topic_id`, `alias=`, `line=`
- Added topic alias export so symbolic contexts such as QuickHelp
  `file!context` links can resolve across bundles
- Added generated fallback index creation in readers for source formats that do
  not carry a usable native index
- Added standalone `rebuild_catalog.py` to rebuild `helps/catalog.json`
  directly from existing `.json.gz` bundles
- Added FastAPI runtime server with static `www/` frontend serving, root
  `helps/` bundle output, and direct docs sharing

### Viewer & UI
- Viewer now accepts only **UHF 2.0** bundles; old pre-rendered legacy bundles
  are no longer supported
- Added status-line buttons for **Index** and **Content** when the opened help
  file provides them
- Added dynamic app-bar help menus derived from document contents; BW03 menu
  categories now appear in the top bar after `Windows`, separated by `|`
- Fixed index/content click handling regressions in the SPA viewer
- Improved QuickHelp top navigation rendering including external sibling-file
  tabs and preserved CP437 arrow markers
- Improved syntax highlighting and color palettes to better match
  **Borland C++ 3.1** and **Borland Pascal 7**

### Converter & Refactoring
- Refactored exporter format detection into a shared handler registry used by
  both loading and directory traversal
- Moved format-specific logic back into the appropriate readers, including
  QuickHelp display-name derivation and THELP/QuickHelp/NG navigation handling
- Split HLX source parsing out of `thelp.py` into its own `hlx.py` reader path
- Added shared markup helpers for UHF link generation/parsing and shared
  navigation helpers in the base model
- Extended the document model with structured contents nodes, nav items,
  aliases, comments, and richer metadata

### Downloader
- Refactored the downloader into a product/source manifest plus provider-specific
  downloaders for **WinWorld**, **archive.org**, **old-dos.ru**, **GitHub**, and
  the **Dave Pearson Norton Guides** mirror
- Added default “download everything” behavior when no selectors are given,
  while skipping already downloaded content
- Added recursive extraction through `lsar` / `unar`, including nested archives,
  disk images, and fallback handling for Microsoft compressed help payloads such
  as `HL$` / `SZDD`
- Added Borland installer split-archive assembly for `*.CA1`, `*.CA2`, ...
  files so WinWorld floppy images yield complete `TCHELP.TCH` / `TCHELPW.TCH`
  help files instead of truncated first-part payloads
- Expanded downloadable Microsoft source sets for QuickBASIC, QuickC, MASM,
  CodeView, and related tools

### Tooling & Docs
- `thelp.sh` now auto-bootstraps missing prerequisites: it triggers `download`
  if `downloads/` is empty and `build` if `helps/` is missing
- `thelp.sh` command layout was cleaned up into explicit subcommands:
  `docker start|stop|restart` for container runtime and
  `serve start|stop|status|restart` for the local FastAPI server
- Expanded documentation with new format specs for **UHF 2.0**, **Microsoft
  QuickHelp**, **Microsoft BW03**, **Norton Guide**, bundle transport, downloader
  architecture, and cross-format comparisons
- Updated README, format index, and bundle/downloader docs to describe the new
  converter architecture and `.json.gz` transport

## [1.0.0] — 2026-04-06

### Features
- TurboVision-style single-page viewer with menus, windows, dialogs
- **Help file formats**: Borland THELP (TP4–7, TC, TASM, Sidekick, Sprint),
  TurboVision FBHF (THelpFile), Software602 (M602/Text602), `.TCH` (Turbo C Help)
- **Bundle format**: `.json.gz` bundles with native `DecompressionStream` decompression
- **Converter**: Python package with `readers/` and `writers/` subpackages
- Loading progress dialog with Cancel and abort support
- Full-text search across topics
- A–Z index navigation with letter jump links
- URL routing: `?file=`, `?topic=`, `?docs=` parameters for deep linking
- Documentation Markdown viewer with in-app window
- Theme support (light, dark, auto)
- Color customization dialog
- Syntax highlighting for **Pascal**, **C**, and **x86 ASM** (`tv-highlight.js`)
  - Borland-accurate color scheme (text=yellow, keyword=white, comment=gray, preproc=green, asm=green)
- Automatic encoding detection for Czech help files (CP852, Kamenický, CP437)
- Code block heuristic for TC 2.0/2.01 (`fv=4, tv=1`)
- Box-drawing character stripping from topic headings
- **TVInfoBox** widget with `resolve()` instance API and `updateRow()` for formatted rows
- **TVMessageBox** widget — modal message box extending TVDialog with promise-based `show()`
- Built-in apps: Calculator, ASCII table, Calendar
- Built-in games: Tetris, Minesweeper, BreakOut, Sokoban, Lines, Snake, Reversi, Puzzle
- High Score dialog with name input
- Open Graph / Twitter Card meta tags
- Docker support with docker-compose
- Format documentation: Borland THELP, TurboVision FBHF, Software602 M602/Text602
- JS bundle format specification
