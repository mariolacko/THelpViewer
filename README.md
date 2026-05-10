# THelpViewer

![THelpViewer](Thelp.png)


A web-based viewer for Borland/Turbo Pascal and Software602 help files,
rendered as a TurboVision-style single-page application.

Homepage: [https://thelp.zdrojak.dev](https://thelp.zdrojak.dev)

Reads multiple legacy DOS help formats including Borland THELP, Microsoft
QuickHelp / BW03, Norton Guide, FBHF, Software602, and text `.hlx` / `.hl6`
sources, then serves them as an interactive web application with authentic DOS
look and feel.

## Supported Formats

| Format | Products | Extension |
|--------|----------|-----------|
| **Borland THELP** | Turbo Pascal 4–7, Turbo C, TASM, Sidekick, Sprint | `.HLP`, `.TPH`, `.TCH`, `*.T?H` with THELP signature |
| **Microsoft BW03** | Older CodeView DOS / OS2 help (`CV.HLP`, `CVP.HLP`) | `.HLP` |
| **Microsoft QuickHelp (LN)** | QuickBASIC, QuickC, MASM 6, PWB, LINK | `.HLP` |
| **Norton Guide** | Norton Guides and Expert Help databases | `.NG` |
| **TurboVision FBHF** | Turbo Vision apps (TP6, BP7), TVHC compiler | `.HLP` |
| **Software602 M602** | M602 Manager (XOR $FA encrypted) | `.HLP` |
| **Software602 Text602** | Text602, Calc602 word processors | `.HLP` |
| **HLX/HL6 text** | Decompiled text format (round-trip capable) | `.hlx`, `.hl6` |
| **Scorpion DAT (experimental)** | Scorpion's Cheater 23.0 content databases | `.dat` |

## Quick Start

### Local

```bash
# 1. Download help files from the internet (requires unar)
./thelp.sh download

# 2. Build UHF 2.0 `.json.gz` bundles from source help files
./thelp.sh build

# Optional: rebuild only the help catalog from already generated bundles
./thelp.sh catalog

# 3. Serve locally through FastAPI
./thelp.sh serve start
```

Useful local server commands:

```bash
./thelp.sh serve status
./thelp.sh serve restart
./thelp.sh serve stop
```

Or do everything at once (download + build + Docker start):

```bash
./thelp.sh all
```

Open http://localhost:5448 in your browser.
Port 5448 = `0x5448` = ASCII "TH" (THelp).

### Docker

```bash
./thelp.sh all
```

That downloads missing source archives, builds `helps/`, and starts the
FastAPI server in Docker on http://localhost:5448.

If bundles already exist, plain Docker startup is enough:

```bash
./thelp.sh docker start
```

Useful Docker commands:

```bash
./thelp.sh docker stop
./thelp.sh docker restart
```

The container image is intentionally minimal: it installs Python deps only and
docker-compose bind-mounts the whole repository into `/app`, so JS/CSS/docs/help
data are never copied into the image.

## Project Structure

```
THelpViewer/
├── www/                    ← Static frontend shell served by FastAPI
│   ├── index.html          ←   SPA entry document
│   └── assets/             ←   JS, CSS, fonts, images
├── thelpviewer/            ← Unified Python package root
│   ├── converter/          ←   help converter package
│   │   ├── readers/        ←     format readers (thelp, bw03, quickhelp, ng, fbhf, hlx, m602, scorpion_dat)
│   │   ├── writers/        ←     output writers (html, uhf json, bundle, md)
│   │   ├── base.py         ←     shared data model (HelpDocument, TopicRecord, …)
│   │   ├── codepages.py    ←     encoding tables (CP437, CP852, Kamenický)
│   │   └── exporter.py     ←     high-level export orchestration
│   ├── downloader/         ←   help file downloader
│   │   ├── catalog.py      ←     logical product/source manifest
│   │   ├── http.py         ←     shared HTTP + HTML helpers
│   │   ├── extractor.py    ←     recursive unar/lsar extraction
│   │   └── *.py            ←     one provider per website
│   ├── server/             ←   FastAPI app
│       ├── app.py          ←     routes and static mounts
│       ├── config.py       ←     env-based runtime configuration
│       └── __init__.py
│   └── help-database.json  ←   canonical help-file metadata
├── downloads/              ← Cached downloaded archives and disk images
├── sources/                ← Source help files organized by product group
│   ├── Borland Turbo Pascal 7/   ← e.g. TURBO.TPH, TVISION.TPH, OWL.TPH
│   ├── Borland Turbo C 2.01/     ← e.g. TCHELP.TCH
│   └── …
├── helps/                  ← Generated UHF 2.0 `.json.gz` bundles + catalog.json
├── var/                    ← Future mutable server-side state
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
├── docker-compose.yml
└── tools/
    ├── rebuild_help_database.py ← Rebuild the canonical help database from sources
    └── rebuild_catalog.py       ← Rebuild helps/catalog.json from existing bundles
```

## Features

- **Authentic TurboVision UI** — menus, windows, scrollbars, dialogs, resize, maximize
- **Compressed structured bundles** — UHF 2.0 payload stored as `.json.gz`
- **Loading progress** — DOS Navigator-style dialog with progress bar and Cancel
- **Full-text search** — search across all topics within a help file
- **A–Z index navigation** — letter jump links in the index view
- **Window management** — zoom (F5), close (Alt-F3), drag, resize
- **Theme support** — light, dark, auto (system preference)
- **Color customization** — TurboVision Colors dialog with live preview
- **Syntax highlighting** — Pascal, C, and ASM highlighting (client-side)
- **Code block heuristic** — automatic detection for older formats without markers (TC 2.0/2.01)
- **Built-in apps** — Calculator, ASCII table, Calendar, Tetris, Minesweeper, Puzzle

## Bundle Size

Measured on the current generated UHF 2.0 payloads:

| Source | Original help | Raw UHF JSON | Compressed `.json.gz` | Reduction (orig→gz) | Reduction (UHF→gz) |
|--------|---------------:|--------------:|----------------------:|-------------------:|-------------------:|
| `Borland Pascal 4.0/TURBO.HLP` | 85,344 B | 326,369 B | 47,130 B | 44.7% | 85.6% |
| `Microsoft QuickBASIC Extended 7.1/BAS7QCK.HLP` | 230,419 B | 858,630 B | 115,323 B | 50.0% | 86.6% |
| `Norton Guides/DOS.NG` | 58,664 B | 125,313 B | 22,072 B | 62.4% | 82.4% |
| `Borland C++ 3.1/TCHELP.TCH` | 1,544,843 B | 4,513,532 B | 626,963 B | 59.4% | 86.1% |

## How It Works

1. The **downloader** (`python3 -m thelpviewer.downloader`) reads one shared manifest of
   logical products and fetches them via provider-specific downloaders
   (WinWorldPC, archive.org, old-dos.ru, GitHub, DaveP NG mirror) into `sources/`
   When called without selectors it downloads everything it knows about and skips
   files already present in `downloads/` or `sources/`
2. `thelp.sh build` runs the converter over all files in `sources/`
3. Each help file is parsed and rendered into a UHF 2.0 JSON payload containing
   structured topics, index entries, and metadata
4. The JSON payload is gzip-compressed into a `.json.gz` bundle for web transport
5. A `catalog.json` is generated in `helps/`
6. FastAPI serves `www/`, `helps/`, and `docs/` directly
7. The browser fetches `.json.gz` bundles on demand, decompresses them, and renders them in a TurboVision window

The canonical [help-database.json](thelpviewer/help-database.json) stores source-level
metadata keyed by `crc32`, including the canonical `filenames` list, the target
`collection` name, the help-file title, and the preferred
`text_encoding`. Encoding resolution now uses this precedence: explicit
parameter, database entry, then payload autodetection. Bundle export also uses
the database for CRC-based deduplication and falls back to the current
directory-based grouping when no match exists.

See [Bundle format](docs/THelp%20Viewer/Bundle.md) for the JSON bundle specification.

To build and serve in one step:

```bash
./thelp.sh build serve start
```

To serve only (if bundles are already built):

```bash
./thelp.sh serve start
```

After regeneration, restart the local server or Docker and hard-refresh the browser (Ctrl+F5).

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

The FastAPI docs catalog also exposes `README.md` and `CHANGELOG.md`
virtually under `docs/THelp Viewer/`, so they appear in the viewer without
duplicating files on disk.

## Requirements

- Python 3.10+
- `fastapi` and `uvicorn` for local serving (`pip install -r requirements.txt`)
- Modern browser with DecompressionStream API support
- Docker (optional, for containerized deployment)

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

### Bundled Fonts

The bitmap fonts in `www/assets/fonts/` are from
[The Ultimate Oldschool PC Font Pack](https://int10h.org/oldschool-pc-fonts/)
by VileR, licensed under [CC BY-SA 4.0](www/assets/fonts/LICENSE.TXT).
