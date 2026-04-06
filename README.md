# THelpViewer

![THelpViewer](Thelp.png)


A web-based viewer for Borland/Turbo Pascal and Software602 help files,
rendered as a TurboVision-style single-page application.

Homepage: [https://thelp.zdrojak.dev](https://thelp.zdrojak.dev)

Reads binary `.HLP`, `.TPH`, `.TCH` and text `.hlx` help files and serves them
as an interactive web application with authentic DOS look and feel.

## Supported Formats

| Format | Products | Extension |
|--------|----------|-----------|
| **Borland THELP** | Turbo Pascal 4–7, Turbo C, TASM, Sidekick, Sprint | `.HLP`, `.TPH`, `.TCH` |
| **TurboVision FBHF** | Turbo Vision apps (TP6, BP7), TVHC compiler | `.HLP` |
| **Software602 M602** | M602 Manager (XOR $FA encrypted) | `.HLP` |
| **Software602 Text602** | Text602, Calc602 word processors | `.HLP` |
| **HLX/HL6 text** | Decompiled text format (round-trip capable) | `.hlx`, `.hl6` |

## Quick Start

### Local

```bash
# 1. Download help files from the internet (requires 7z)
./thelp.sh download

# 2. Build compressed .json.gz bundles from source help files
./thelp.sh build

# 3. Serve locally
./thelp.sh serve
```

Or do everything at once (download + build + Docker):

```bash
./thelp.sh all
```

Open http://localhost:5448 in your browser.
Port 5448 = `0x5448` = ASCII "TH" (THelp).

### Docker

```bash
docker compose up --build
```

This builds all help files and starts a web server on http://localhost:8080.

## Project Structure

```
THelpViewer/
├── converter/              ← Python converter package
│   ├── readers/            ←   format readers (thelp, fbhf, hlx, m602)
│   ├── writers/            ←   output writers (html, js/json.gz, md)
│   ├── assets/             ←   TurboVision CSS, JS (core, highlight, dialogs, shell, app)
│   ├── base.py             ←   shared data model (HelpDocument, TopicRecord, …)
│   ├── codepages.py        ←   encoding tables (CP437, CP852, Kamenický)
│   └── exporter.py         ←   high-level export orchestration
├── downloader/             ← Help file downloader (WinWorldPC, archive.org, old-dos.ru)
├── sources/                ← Source help files organized by product group
│   ├── Borland Turbo Pascal 7/   ← e.g. TURBO.TPH, TVISION.TPH, OWL.TPH
│   ├── Borland Turbo C 2.01/     ← e.g. TCHELP.TCH
│   └── …
├── www/                    ← Generated output
│   ├── index.html          ←   SPA viewer entry point
│   ├── helps/              ←   compressed .json.gz bundles + catalog.json
│   ├── docs/               ←   Markdown docs served in-viewer
│   └── assets/             ←   CSS + JS assets
├── docs/                   ← Documentation
│   ├── FORMATS.md          ←   binary format index
│   ├── Formats/            ←   detailed format specifications
│   │   ├── Borland THELP.md
│   │   ├── TurboVision FBHF.md
│   │   ├── Software602.md
│   │   ├── Software602 M602.md
│   │   ├── Software602 Text602.md
│   │   └── Help Source Text Format.md
│   └── THelp Viewer/       ←   viewer and tool docs
│       ├── Bundle.md       ←   JSON bundle transport format
│       ├── Converter.md    ←   converter usage & architecture
│       ├── Downloader.md   ←   help file downloader
│       └── TurboVision JS.md ← JS UI framework API
├── thelp.sh                ← Build, serve & manage script
├── Dockerfile
└── docker-compose.yml
```

## Features

- **Authentic TurboVision UI** — menus, windows, scrollbars, dialogs, resize, maximize
- **Compressed bundles** — native gzip `.json.gz` bundles (70–80% size reduction)
- **Loading progress** — DOS Navigator-style dialog with progress bar and Cancel
- **Full-text search** — search across all topics within a help file
- **A–Z index navigation** — letter jump links in the index view
- **Window management** — zoom (F5), close (Alt-F3), drag, resize
- **Theme support** — light, dark, auto (system preference)
- **Color customization** — TurboVision Colors dialog with live preview
- **Syntax highlighting** — Pascal, C, and ASM highlighting (client-side)
- **Code block heuristic** — automatic detection for older formats without markers (TC 2.0/2.01)
- **Built-in apps** — Calculator, ASCII table, Calendar, Tetris, Minesweeper, Puzzle

## How It Works

1. The **downloader** (`python3 -m downloader`) fetches original help files
   from WinWorldPC, archive.org, and old-dos.ru into `sources/`
2. `thelp.sh build` runs the converter over all files in `sources/`
3. Each help file is parsed and rendered into a JSON bundle containing
   pre-rendered HTML for every topic, index entries, and search data
4. The JSON is gzip-compressed into a `.json.gz` file
5. A `catalog.json` and `index.html` are generated for the SPA viewer
6. The browser fetches bundles on demand, decompresses via `DecompressionStream`,
   and renders them in a TurboVision window

See [Bundle format](docs/THelp%20Viewer/Bundle.md) for the JSON bundle specification.

To build and serve in one step:

```bash
./thelp.sh build serve
```

To serve only (if bundles are already built):

```bash
./thelp.sh serve
```

After regeneration, restart the server/Docker and hard-refresh the browser (Ctrl+F5).

## Documentation

### Format Specifications

- [Format index](docs/FORMATS.md) — overview and comparison of all binary formats
- [Borland THELP](docs/Formats/Borland%20THELP.md) — TP4–7, Turbo C, TASM, Sidekick, Sprint
- [TurboVision FBHF](docs/Formats/TurboVision%20FBHF.md) — TP6, BP7 THelpFile (TVHC compiler)
- [Software602](docs/Formats/Software602.md) — M602, Text602, Calc602 help families
- [Help source text format](docs/Formats/Help%20Source%20Text%20Format.md) — HLX/TXT decompiled-source specification

### Viewer & Tools

- [Converter](docs/THelp%20Viewer/Converter.md) — help file converter (binary → HTML / JSON / Markdown)
- [JSON Bundle format](docs/THelp%20Viewer/Bundle.md) — transport format for the SPA viewer
- [Downloader](docs/THelp%20Viewer/Downloader.md) — automated help file downloader
- [TurboVision JS](docs/THelp%20Viewer/TurboVision%20JS.md) — JavaScript UI framework API reference

## Requirements

- Python 3.10+ (no external dependencies)
- Modern browser with DecompressionStream API support
- Docker (optional, for containerized deployment)

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

### Bundled Fonts

The bitmap fonts in `converter/assets/fonts/` are from
[The Ultimate Oldschool PC Font Pack](https://int10h.org/oldschool-pc-fonts/)
by VileR, licensed under [CC BY-SA 4.0](converter/assets/fonts/LICENSE.TXT).
