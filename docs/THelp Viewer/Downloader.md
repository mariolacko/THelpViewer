# Downloader

> Updated: 2026-04-05

Automated downloader for Borland/Turbo DOS help files from multiple online sources.
Fetches original product archives, extracts them, and collects `.HLP`/`.TPH`/`.TCH`
files into the `sources/` directory organized by product group.

Requires Python 3.10+ and `7z` (p7zip) for archive and disk image extraction.

## Usage

```bash
# Download from all sources, all products
python3 -m downloader

# Specific sources
python3 -m downloader --source winworld archiveorg

# Specific products
python3 -m downloader --products tp tc tasm

# Preview what would be downloaded
python3 -m downloader --dry-run

# Custom output directories
python3 -m downloader --out-dir sources/ --dl-dir downloads/
```

## Options

| Option | Description |
|--------|-------------|
| `--source` | Sources to use: `winworld`, `archiveorg`, `olddos` (default: all) |
| `--products` | Products to download: `tp`, `tc`, `tasm`, etc. (default: all for given source) |
| `--out-dir` | Target directory for extracted help files (default: `sources/`) |
| `--dl-dir` | Directory for downloaded archives (default: `downloads/`) |
| `--dry-run` | Only print what would happen, don't download or extract |

## Sources

| Source | URL | Notes |
|--------|-----|-------|
| `winworld` | WinWorldPC | 25 downloads/day limit. Downloads disk images (`.img`, `.zip`), extracts with `7z`. |
| `archiveorg` | Archive.org | No rate limit. Downloads direct file archives (`.zip`, `.7z`). |
| `olddos` | old-dos.ru | Category 102 programming tools. Downloads `.zip`/`.rar` archives. |

Each source has its own set of supported products (not all products are
available on all sources):

| Product | `winworld` | `archiveorg` | `olddos` |
|---------|:----------:|:------------:|:--------:|
| `tp` — Turbo Pascal | ✓ | ✓ | ✓ |
| `tc` — Turbo C / C++ | ✓ | ✓ | ✓ |
| `tasm` — Turbo Assembler | ✓ | ✓ | ✓ |
| `td` — Turbo Debugger | — | ✓ | ✓ |
| `tbasic` — Turbo Basic | ✓ | ✓ | ✓ |
| `tprolog` — Turbo Prolog | ✓ | ✓ | ✓ |
| `bc` — Borland C++ | ✓ | ✓ | ✓ |
| `bp` — Borland Pascal | ✓ | ✓ | ✓ |
| `sk` — Sidekick | ✓ | — | — |

## Extraction Pipeline

1. **Download** — fetch archive from the source into `downloads/`
2. **Extract** — use `7z` to unpack the archive (handles `.zip`, `.7z`, `.rar`,
   `.img`, `.ima`, `.dsk` disk images, and nested archives)
3. **Collect** — scan extracted files for help file extensions
   (`.HLP`, `.TPH`, `.TCH`) using case-insensitive matching
4. **Organize** — copy found help files into `sources/<Product Group>/`
   (e.g. `sources/Borland Turbo Pascal 7/TURBO.TPH`)

The extraction automatically handles nested archives (e.g. a `.zip` containing
a floppy disk image containing another `.zip` with the actual help files).

## Architecture

| Module | Purpose |
|--------|---------|
| `__main__.py` | Unified CLI entry point, source routing, product filtering |
| `common.py` | Shared utilities: HTTP download, `7z` detection, archive extraction, help file collection |
| `winworld.py` | WinWorldPC scraper — version page parsing, download link extraction, disk image handling |
| `archiveorg.py` | Archive.org downloader — direct file downloads with metadata parsing |
| `olddos.py` | old-dos.ru downloader — category page parsing, `.rar`/`.zip` extraction |

### `common.py` Utilities

| Function | Description |
|----------|-------------|
| `require_7z()` | Find `7z` or `7zz` binary, raise error if not installed |
| `download_file(url, dest)` | HTTP download with progress tracking and retry |
| `extract_archive(archive, dest, sevenz)` | Extract using `7z x` with auto-detection |
| `collect_help_files(source_dir, target_dir)` | Recursively find `.HLP`/`.TPH`/`.TCH` and copy to target |

## Requirements

- **Python 3.10+** — no external Python packages needed
- **7z** (p7zip or 7-Zip) — must be on PATH. Install via:
  - macOS: `brew install p7zip` or `brew install sevenzip`
  - Linux: `apt install p7zip-full` or `dnf install p7zip-plugins`
  - Windows: install [7-Zip](https://www.7-zip.org/) and add to PATH

## Output

Downloaded help files are organized into `sources/` by product group:

```
sources/
├── Borland Turbo Pascal 4/
│   └── TURBO4.HLP
├── Borland Turbo Pascal 7/
│   ├── TURBO.TPH
│   ├── TVISION.TPH
│   └── OWL.TPH
├── Borland Turbo C 2.01/
│   └── TCHELP.TCH
├── Software602 M602/
│   └── M602_200.HLP
└── ...
```

These directories map directly to catalog groups when
the converter builds JSON bundles (`python -m converter sources/ www/ --bundle`).
