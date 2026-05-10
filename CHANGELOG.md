# Changelog

## [1.1.0] — 2026-04-09

### Features
- Introduced **UHF 2.0** as the normalized internal document format with structured
  `contents`, `index`, `topics`, topic aliases, exact-label navigation items,
  frozen rows, and line-addressable links
- Added **Microsoft QuickHelp (LN)** reader support for QuickBASIC, QuickC, PWB,
  LINK and related toolchain help files
- Added **Microsoft BW03** reader support for older CodeView DOS / OS/2 help
  files (`CV.HLP`, `CVP.HLP`)
- Added separate **Borland Turbo Debugger TDH** detection and diagnostic reader
  for `TDHELP.TDH`; its encoded payload is documented but not decoded yet
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
