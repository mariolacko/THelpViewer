# Changelog

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
