# Downloader

> Updated: 2026-10-10

Automated downloader for DOS help-file sources.

The downloader is split into three layers:

1. `thelpviewer/config/help-database.json` defines **what** logical product families
   we want, how each provider should find them, and which archive files to
   collect. The converter separately detects supported inputs.
2. `winworld.py`, `archiveorg.py`, `direct.py`, `olddos.py`, `github.py`, `davep_ng.py`, `cheater_cz.py`, `slunecnice.py` define **how**
   each concrete website is scraped and downloaded.
3. `service.py` orchestrates callable provider jobs; `transport.py` supplies
   shared bounded public-network downloads for HELP and DOS. `catalog.py`
   exposes typed manifest objects and `extractor.py` handles
   unpacking through `unar`/`lsar`, including
   nested archives and disk images.

## Usage

The server's **Server Configuration → HELP / DOS packages** dialog selects
HELP build groups and calls `download_products()` directly. API progress uses
the job's callback and `observe_downloads()`, not captured terminal output.
Empty server selections download nothing. Provider failures are surfaced as
warnings; absence of usable input fails the build without publishing it.
See [Server Content](Server%20Content.md) for storage, setup and API behavior.

```bash
# Download from all sources, all configured products
python3 -m thelpviewer.server.downloader

# Only specific sites
python3 -m thelpviewer.server.downloader --source winworld archiveorg cheater_cz slunecnice

# Positional selectors also work
python3 -m thelpviewer.server.downloader tp olddos

# Only specific logical products
python3 -m thelpviewer.server.downloader --products tp tc ng qbx quickc masm scorpion game-cheater

# Game-Cheater 9.02 only
./thelp.sh download game-cheater slunecnice

# Four pinned DOS-era reference products
python3 -m thelpviewer.server.downloader --source direct --products msdos622 qb45 helppc freedos-help

# Convert the default groups and DOS reference products together for local Help Files
./thelp.sh build --with-dos-reference

# Preview only
python3 -m thelpviewer.server.downloader --dry-run
```

With no selectors, the downloader runs every configured provider for every
configured product and skips anything already present in `var/downloads/help/` or
`data/sources/`.
The legacy `downloads/` directory is not migrated or removed automatically;
use `--dl-dir downloads` to reuse it explicitly.

## Options

| Option | Description |
|--------|-------------|
| `--source` | Sources to use: `winworld`, `archiveorg`, `direct`, `olddos`, `github`, `davep_ng`, `cheater_cz`, `slunecnice` |
| `--products` | Logical product families from `thelpviewer/config/help-database.json` |
| positional selectors | Short form for sources/products, e.g. `python3 -m thelpviewer.server.downloader tp olddos` |
| `--out-dir` | Target directory for extracted help files |
| `--dl-dir` | Directory for downloaded archives/files |
| `--dry-run` | Print planned actions only |

## Manifest

`thelpviewer/config/help-database.json` is the single source of truth for:

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
The `direct` provider uses `direct_urls` plus exact `archive_members` paths or
names. This is the download selection, not the converter's input list: include
the files needed for conversion and any required licence notices, but do not
select unused companion files. It extracts nested disk images where needed and
rejects missing or ambiguous matches instead of collecting unrelated files.
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
| `direct.py` | Pinned archive URLs | Exact member selection from known archives |
| `olddos.py` | old-dos.ru | Category pagination, detail-page download link lookup |
| `github.py` | GitHub | Public repo directory listing via Contents API or direct repo path |
| `davep_ng.py` | DaveP NG mirror | Plain `.ng` mirror download |
| `cheater_cz.py` | Cheater.cz | DOS Scorpions Cheater version discovery, gated download resolution, versioned corpus collection |
| `slunecnice.py` | Slunečnice.cz | Signed Game-Cheater URL discovery and extraction of `instgc.zip` plus embedded `INSTGC.EXE` |

Each provider reads only its own source-specific config from the parsed JSON
manifest. `catalog.py` contains no concrete product list.
Archive.org release detection appends a version to a product's source
directory only if its `label` does not already end in that version (for
example, `Microsoft QuickBASIC Extended 7.1` stays a single `7.1`).

`cheater_cz.py` is intentionally provider-specific: it keeps every DOS release in a
separate version folder under `data/sources/Scorpions Cheater DOS/` and copies the raw
Scorpion corpus artifacts selected by the manifest. For the earliest
releases where the corpus is embedded directly in executables, it falls back to
preserving the `.exe` files so no DOS version is silently dropped.

The same manifest also drives build-group selection and aliases in `thelp.sh`,
so adding a group does not require another shell `case` branch.

`slunecnice.py` copies the eleven Game-Cheater database files into
`data/sources/Game-Cheater/Game-Cheater 9.02/`. Build them with
`./thelp.sh build --group=game-cheater`.

The four pinned products are downloaded into `data/sources/<Product>/`, alongside
the existing product directories.
MS-DOS 6.22 and QuickBASIC 4.5 also have Archive.org `search_text` and
verified, exact-identifier `query` entries, following the other Microsoft
products. That provider extracts only the configured HELP member into the same
product directory; the direct provider skips files already
collected by search. HelpPC 2.10 and FreeDOS HTML Help keep their pinned direct
sources: Archive.org search did not locate those exact releases (the HelpPC
result is 2.0), while the FreeDOS package is indexed by its official ibiblio
repository.
The opt-in `dos-reference` build group converts them to eleven UHF bundles under
their respective `data/helps/<Product>/` directories and updates `data/helps/catalog.json`,
which supplies the Help Files menu. Use `./thelp.sh build --with-dos-reference` to include them in
the same build as the default groups while preserving unrelated opt-in bundles.
A normal default build does not select this group; rerun with the flag after a
default rebuild if these local bundles
are wanted. `./thelp.sh build --group dos-reference` still rebuilds only this
group:

| Product | Selected source | Current conversion status |
|---------|-----------------|---------------------------|
| `msdos622` | `HELP.HLP` expanded from MS-DOS 6.22 Disk 2 `HELP.HL_` | QuickHelp reader exports 428 topics; topic/link validation remains |
| `qb45` | `QB45QCK.HLP`, `QB45ADVR.HLP`, `QB45ENER.HLP` from the Program, Advisor, and Utilities disks | Three UHF bundles, 990 topics total; QuickHelp cross-file links resolve |
| `helppc` | Six `.TXT` databases | Six UHF bundles (`asm.json.gz` etc.), 1,006 topics total, with cross-file links |
| `freedos-help` | English `HHSTNDRD.ZIP` plus license files | 354 HTML pages convert into one UHF bundle |

The four Microsoft `.HLP` files, six HelpPC topic databases, and FreeDOS help
ZIP are recorded by CRC32 and assigned to their products in
`thelpviewer/config/help-database.json`. HelpPC's `HELPPC.DOC` and `.NDX` are not
selected by the downloader because they are not conversion inputs. FreeDOS
licence texts are retained as required companion files, not topic databases.
These products are still outside the default public
build; conversion support does not change redistribution rights.

HelpPC's original documentation describes the distribution as shareware;
Microsoft's files are proprietary. Downloading them for local inspection does
not establish permission to publish converted content. The selected FreeDOS
package states `Express+GNU Free Documentation License`; review its included
`COPYING` and `FDL.TXT` before publication.

## Extraction

`thelpviewer/server/downloader/extractor.py` uses:

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

Microsoft setup-disk `KWAJ` single-file compression (including LZH) is also
expanded to final filenames such as `HELP.HLP` using `pylibmspack`.

This replaces the old mix of `7z`, `zipfile`, and special-case RAR handling.

## Shared Helpers

| Module | Purpose |
|--------|---------|
| `http.py` | HTTP fetch/download helpers and anchor parsing |
| `collector.py` | language detection, help-file scanning, final copy to `data/sources/` |
| `extractor.py` | archive probing and extraction through `unar` / `lsar` |

## Requirements

- Python 3.10+
- `unar` and `lsar`, or `7zz`, on PATH
- Python dependencies from `requirements.txt` (including `pylibmspack` for KWAJ)

Install:

- macOS: `brew install unar`
- Linux: `sudo apt install unar`

## Output

Collected help files are copied into `data/sources/<Product Label ...>/`.
Those directories are then consumed by `python -m thelpviewer.server.converter` / `./thelp.sh build`.
