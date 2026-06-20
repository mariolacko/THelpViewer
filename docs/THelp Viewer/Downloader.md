# Downloader

> Updated: 2026-06-14

Automated downloader for DOS help-file sources.

The downloader is split into three layers:

1. `thelpviewer/help-database.json` defines **what** logical product families
   we want, how each provider should find them, and which files are conversion
   inputs.
2. `winworld.py`, `archiveorg.py`, `olddos.py`, `github.py`, `davep_ng.py`, `cheater_cz.py`, `slunecnice.py` define **how**
   each concrete website is scraped and downloaded.
3. `catalog.py` exposes typed manifest objects and `extractor.py` handles
   unpacking through `unar`/`lsar`, including
   nested archives and disk images.

## Usage

```bash
# Download from all sources, all configured products
python3 -m thelpviewer.downloader

# Only specific sites
python3 -m thelpviewer.downloader --source winworld archiveorg cheater_cz slunecnice

# Positional selectors also work
python3 -m thelpviewer.downloader tp olddos

# Only specific logical products
python3 -m thelpviewer.downloader --products tp tc ng qbx quickc masm scorpion game-cheater

# Game-Cheater 9.02 only
./thelp.sh download game-cheater slunecnice

# Preview only
python3 -m thelpviewer.downloader --dry-run
```

With no selectors, the downloader runs every configured provider for every
configured product and skips anything already present in `downloads/` or
`sources/`.

## Options

| Option | Description |
|--------|-------------|
| `--source` | Sources to use: `winworld`, `archiveorg`, `olddos`, `github`, `davep_ng`, `cheater_cz`, `slunecnice` |
| `--products` | Logical product families from `thelpviewer/help-database.json` |
| positional selectors | Short form for sources/products, e.g. `python3 -m thelpviewer.downloader tp olddos` |
| `--out-dir` | Target directory for extracted help files |
| `--dl-dir` | Directory for downloaded archives/files |
| `--dry-run` | Print planned actions only |

## Manifest

`thelpviewer/help-database.json` is the single source of truth for:

- `sources`: provider key, description, and Python runner module
- `converters`: format handler order, matcher/detector function, reader class,
  and reader construction mode
- `products`: stable family key, display label, build group, collection
  prefixes, provider queries, and conversion rules
- `build_groups`: source/output prefixes, default inclusion, and CLI aliases
- `entries`: known individual files with filenames, optional bundle name,
  encoding, language, and CRC32

A product source may use a direct URL, provider-specific search query, slug,
keywords, category ids, API URL, or any combination required by that provider.
Products with many releases keep these values once at family level. Known files
remain independent `entries`; their family and release are derived from the
configured `collection_prefixes`, or can be stated explicitly with `product`
and `release`.

Conversion rules support exact `filename` values, glob `pattern` values,
optional `crc32`, required inputs, secondary inputs, and named output `bundles`.
Game-Cheater uses bundle rules for its five sections. Scorpion uses `*.DAT`,
`*.SCO`, `*.SCX`, and `*.SCD`, with `*.EXE` only as a secondary embedded-data
input when a release has no standalone data files.

For Scorpions Cheater this now also includes the stable public DOS history page
in `direct_urls`, while the provider still resolves each per-version gated file
URL dynamically through `get-name.php` / `get-link.php`.

This keeps “what we want” separate from provider code.

Adding a downloader does not require changing the central CLI: create a provider
module with `run(...)`, add it to `sources`, and reference that source from one
or more products. Adding a converter follows the same pattern: create a reader
module with a matcher/detector and reader class, then add a `converters` entry.

## Providers

| Module | Site | Responsibility |
|--------|------|----------------|
| `winworld.py` | WinWorldPC | Product/version scraping, mirror selection |
| `archiveorg.py` | Archive.org | Search API, metadata files, candidate file picking |
| `olddos.py` | old-dos.ru | Category pagination, detail-page download link lookup |
| `github.py` | GitHub | Public repo directory listing via Contents API or direct repo path |
| `davep_ng.py` | DaveP NG mirror | Plain `.ng` mirror download |
| `cheater_cz.py` | Cheater.cz | DOS Scorpions Cheater version discovery, gated download resolution, versioned corpus collection |
| `slunecnice.py` | Slunečnice.cz | Signed Game-Cheater URL discovery and extraction of `instgc.zip` plus embedded `INSTGC.EXE` |

Each provider reads only its own source-specific config from the parsed JSON
manifest. `catalog.py` contains no concrete product list.

`cheater_cz.py` is intentionally provider-specific: it keeps every DOS release in a
separate version folder under `sources/Scorpions Cheater DOS/` and copies the raw
Scorpion corpus artifacts selected by the manifest. For the earliest
releases where the corpus is embedded directly in executables, it falls back to
preserving the `.exe` files so no DOS version is silently dropped.

The same manifest also drives build-group selection and aliases in `thelp.sh`,
so adding a group does not require another shell `case` branch.

`slunecnice.py` copies the eleven Game-Cheater database files into
`sources/Game-Cheater/Game-Cheater 9.02/`. Build them with
`./thelp.sh build --group=game-cheater`.

## Extraction

`thelpviewer/downloader/extractor.py` uses:

- `lsar -json` to detect whether a file is an extractable container and what
  format it is
- `unar` to unpack it

The extraction is recursive:

```text
outer.7z
  -> disk1.img
    -> install.zip
      -> TURBO.HLP
```

The extractor will:

1. unpack the downloaded file
2. scan the extracted tree for any nested extractable files
3. unpack those too
4. repeat up to a safe maximum depth
5. collect final help files from the fully expanded tree

This replaces the old mix of `7z`, `zipfile`, and special-case RAR handling.

## Shared Helpers

| Module | Purpose |
|--------|---------|
| `http.py` | HTTP fetch/download helpers and anchor parsing |
| `collector.py` | language detection, help-file scanning, final copy to `sources/` |
| `extractor.py` | archive probing and extraction through `unar` / `lsar` |

## Requirements

- Python 3.10+
- `unar` and `lsar` on PATH

Install:

- macOS: `brew install unar`
- Linux: `sudo apt install unar`

## Output

Collected help files are copied into `sources/<Product Label ...>/`.
Those directories are then consumed by `python -m thelpviewer.converter` / `./thelp.sh build`.
