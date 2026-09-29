# TODO

## v1.0 (current)

- [x] Compressed `.json.gz` bundles with `DecompressionStream`
- [x] TurboVision UI (menus, windows, scrollbars, dialogs, resize, zoom)
- [x] Full-text search across topics
- [x] A–Z index navigation
- [x] Theme support (light, dark, auto)
- [x] Color customization (TurboVision Colors dialog)
- [x] Pascal, C, ASM syntax highlighting (client-side)
- [x] Code block heuristic for TC 2.0/2.01
- [x] Downloader (WinWorldPC, archive.org, old-dos.ru)
- [x] Docker support
- [x] CP852 box-drawing disambiguation
- [x] Built-in apps (Calculator, ASCII table, Calendar, Tetris, Minesweeper, Puzzle)
- [ ] License — switch to GPL 3

## v2.0

- [ ] Extract CLI-independent downloader/converter job services with progress callbacks, cancellation, bounded working directories, and atomic publish; keep CLI commands as thin adapters
- [ ] Web-triggered downloader from an authenticated menu/API (SSE progress, DOS Navigator-style dual progress bar)
- [ ] Web-triggered converter/rebuild from an authenticated menu/API (SSE progress)
- [ ] Python data model classes (THelpTopic, TParagraph, TCrossRef, THelpIndex)
- [ ] Refactor readers/writers to use data model classes
- [ ] Web API for help file browsing and editing
