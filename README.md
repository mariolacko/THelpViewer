# THelpViewer

![THelpViewer](Thelp.png)


A web-based viewer for legacy DOS help files, rendered as a TurboVision-style
single-page application.

Homepage: [https://thelp.zdrojak.dev](https://thelp.zdrojak.dev)

Reads multiple legacy DOS help formats including Borland THELP, Microsoft
QuickHelp / BW03, Borland TDH/TFH runtime help, Norton Guide, FBHF,
Software602, and text `.hlx` / `.hl6` sources, then serves them as an
interactive web application with authentic DOS look and feel.

## Supported Formats

| Format | Products | Extension |
|--------|----------|-----------|
| **Borland THELP** | Turbo Pascal 4–7, Turbo C, TASM, Sidekick, Sprint | `.HLP`, `.TPH`, `.TCH`, `*.T?H` with THELP signature |
| **Borland TDH/TFH runtime help** | Turbo Debugger 1.0/2.x, Turbo Profiler | `.TDH`, `.TFH` |
| **Microsoft BW03** | Older CodeView DOS / OS2 help (`CV.HLP`, `CVP.HLP`) | `.HLP` |
| **Microsoft QuickHelp (LN)** | QuickBASIC, QuickC, MASM 6, PWB, LINK | `.HLP` |
| **Norton Guide** | Norton Guides and Expert Help databases | `.NG` |
| **TurboVision FBHF** | Turbo Vision apps (TP6, BP7), TVHC compiler | `.HLP` |
| **Software602 M602** | M602 Manager (XOR $FA encrypted) | `.HLP` |
| **Software602 Text602** | Text602, Calc602 word processors | `.HLP` |
| **HLX/HL6 text** | Decompiled text format (round-trip capable) | `.hlx`, `.hl6` |
| **Scorpion's Cheater legacy / DAT (experimental)** | Scorpion's Cheater 1-23 (`legacy` 1-14, modern DAT 15-23) | `.exe`, `.dat`, `.sco`, `.scd`, `.scx` |
| **Game-Cheater Pc-Fand** | Game-Cheater 9.02 cheat, company, URL, help and database tables | paired `.000`, `.T00` files |

Borland TDH/TFH runtime help is decoded for the current known TDH 1.0, later
TDH 2.x, and TFH sample families.

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
│   │   ├── readers/        ←     format readers (thelp, tdh, bw03, quickhelp, ng, fbhf, hlx, m602, scorpion)
│   │   ├── writers/        ←     output writers (html, uhf json, bundle, md)
│   │   ├── base.py         ←     shared data model (HelpDocument, TopicRecord, …)
│   │   ├── codepages.py    ←     encoding tables (CP437, CP852, Kamenický)
│   │   └── exporter.py     ←     high-level export orchestration
│   ├── downloader/         ←   help file downloader
│   │   ├── catalog.py      ←     typed facade over help-database.json
│   │   ├── http.py         ←     shared HTTP + HTML helpers
│   │   ├── extractor.py    ←     recursive unar/lsar extraction
│   │   └── *.py            ←     one provider per website
│   ├── help_database.py    ←   shared manifest loader and validation
│   ├── server/             ←   FastAPI app
│       ├── app.py          ←     routes and static mounts
│       ├── config.py       ←     env-based runtime configuration
│       └── __init__.py
│   └── help-database.json  ←   products, download sources, build groups, conversion files, CRC metadata
├── downloads/              ← Cached downloaded archives and disk images
├── sources/                ← Source help files organized by product group
│   ├── Borland Turbo Pascal 7/   ← e.g. TURBO.TPH, TVISION.TPH, OWL.TPH
│   ├── Borland Turbo C 2.01/     ← e.g. TCHELP.TCH
│   └── …
├── helps/                  ← Generated UHF 2.0 `.json.gz` bundles + catalog.json
├── var/                    ← Future mutable server-side state
├── docs/                   ← Documentation
│   ├── Formats.md          ←   binary format index
│   ├── Formats/            ←   detailed format specifications
│   │   ├── Borland THELP.md
│   │   ├── Borland TDH.md
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
- **Server statistics** — privacy-preserving aggregate SQLite counters shown in a Turbo Vision window
- **System information** — local application, browser, display, locale, storage and capability details with live server/catalog status
- **Shared Hall of Fame** — server-wide top-ten tables with automatic local-browser fallback
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
   (WinWorldPC, archive.org, old-dos.ru, GitHub, DaveP NG mirror, Cheater.cz) into `sources/`
   When called without selectors it downloads everything it knows about and skips
   files already present in `downloads/` or `sources/`

The downloader now also manages the full published DOS Scorpions Cheater corpus.
Those releases are stored under `sources/Scorpions Cheater DOS/` in per-version
subdirectories so DAT-era and pre-DAT-era builds can coexist without overwriting
each other.
2. `thelp.sh build` runs the converter over manifest-backed build groups resolved
   from `thelpviewer/help-database.json`. The default build still covers
   `borland`, `microsoft`, `norton-guides`, and `software602`, while the
   Scorpions Cheater group remains opt-in and can be generated later with
   `./thelp.sh build group=scorpion`. The same grouped build path also works for
   other families such as `group=borland`, `group=microsoft`,
   `group=norton-guides`, or `group=all`.
3. Each help file is parsed and rendered into a UHF 2.0 JSON payload containing
   structured topics, index entries, and metadata
4. The JSON payload is gzip-compressed into a `.json.gz` bundle for web transport
5. A `catalog.json` is generated in `helps/`
6. FastAPI serves `www/`, `helps/`, and `docs/` directly
7. The browser fetches `.json.gz` bundles on demand, decompresses them, and renders them in a TurboVision window

The canonical [help-database.json](thelpviewer/help-database.json) is shared by
the downloader and converter. Schema version 2 contains downloader providers,
converter handlers, product families, build groups, conversion file rules,
output bundle groups, and the existing source metadata keyed by `crc32`. Product families group
multiple releases without duplicating provider configuration. CRC entries are
assigned to a family through `collection_prefixes` and expose the remaining
collection suffix as the release version.

Encoding resolution uses this precedence: explicit parameter, CRC database
entry, then payload autodetection. Bundle export also uses the database for
CRC-based deduplication; files without CRC metadata keep their directory-based
grouping.

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

### Server statistics and errors

The System menu's **System Information** dialog reports the current application
version, page mode, browser/OS, display and Turbo Vision cell geometry, locale,
storage availability and browser capabilities. Its Server category checks the
running version and HELP/Docs catalog sizes. These details remain local to the
dialog and are not submitted as statistics merely by opening it.

The System menu's **Statistics** window reads aggregate counters from
`var/statistics.sqlite3`. The location can be changed with
`THELP_STATISTICS_PATH`; `THELP_STATE_DIR` changes the default state directory.
SQLite uses its rollback journal so the database also works when `var/` is a
Docker Desktop bind mount.
The server records daily visits, referrer hosts, proxy-supplied country codes,
screen/viewport sizes, pixel ratio, color depth, coarse device/OS/browser
families, language, time zone, theme and orientation/pointer/accessibility
preferences. Usage counters cover HELP/Docs/topic and dialog opens, searches
as found/no-results without the entered text, internal/external/broken links,
game outcomes with duration intervals and coarse client-error categories.
The viewer also measures active time for each HELP file, Markdown document,
dialog and game: switching to another window or hiding the browser tab pauses
that target, and returning resumes it.
Performance counters group TTFB, page load, LCP, CLS, INP and HELP
download/decompression/render times into intervals. Active visit time is also
stored only as an interval. The server deliberately does not store IP
addresses, cookies, persistent visitor identifiers, full referrer URLs, raw
user-agent strings, search text, exact timings or individual visit rows. HELP
statistics show the catalog's long display name rather than its source
filename.

Game scores use `GET/POST /api/hall-of-fame/{game}` and are shared by all
visitors of the server. A public score consists only of the entered player
name, score and short game note. When the API is unavailable (for example when
the generated viewer runs directly from disk), the existing per-browser
`localStorage` Hall of Fame remains active; local entries are not uploaded
automatically.

Unknown browser URLs are redirected into the application and shown through a
Turbo Vision error MessageBox. `/api/...` callers continue to receive JSON HTTP
errors.

## Documentation

### Format Specifications

- [Format index](docs/Formats.md) — overview and comparison of all binary formats
- [Borland THELP](docs/Formats/Borland%20THELP.md) — TP4–7, Turbo C, TASM, Sidekick, Sprint
- [Borland TDH/TFH runtime help](docs/Formats/Borland%20TDH.md) — Turbo Debugger 1.0/2.x, Turbo Profiler
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
