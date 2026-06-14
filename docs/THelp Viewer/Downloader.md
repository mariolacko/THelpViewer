# Downloader

> Updated: 2026-06-14

Automated downloader for DOS help-file sources.

The downloader is now split into three layers:

1. `catalog.py` defines **what** logical product groups we want to fetch and
   how each source should search for them.
2. `winworld.py`, `archiveorg.py`, `olddos.py`, `github.py`, `davep_ng.py`, `cheater_cz.py`, `slunecnice.py` define **how**
   each concrete website is scraped and downloaded.
3. `extractor.py` handles **all unpacking** through `unar`/`lsar`, including
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
| `--products` | Logical product groups from `thelpviewer/downloader/catalog.py` |
| positional selectors | Short form for sources/products, e.g. `python3 -m thelpviewer.downloader tp olddos` |
| `--out-dir` | Target directory for extracted help files |
| `--dl-dir` | Directory for downloaded archives/files |
| `--dry-run` | Print planned actions only |

## Manifest

`thelpviewer/downloader/catalog.py` is the single source of truth for:

- logical product keys such as `tp`, `tc`, `bc`, `ng`, `qbx`, `quickc`, `masm`, `scorpion`, `game-cheater`
- user-facing labels such as `Borland Turbo Pascal`
- per-site search text
- per-site machine parameters such as:
  - WinWorld slug
  - Archive.org advanced-search query
  - old-dos category ids + filter keywords
  - direct base URL for mirrors
  - direct item/repository URLs when the exact source is known

For Scorpions Cheater this now also includes the stable public DOS history page
in `direct_urls`, while the provider still resolves each per-version gated file
URL dynamically through `get-name.php` / `get-link.php`.

This keeps “what we want” separate from provider code.

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

Each provider reads only its own source-specific config from `catalog.py`.

`cheater_cz.py` is intentionally provider-specific: it keeps every DOS release in a
separate version folder under `sources/Scorpions Cheater DOS/` and copies the raw
Scorpion corpus artifacts (`.dat`, `.sco`, `.scx`, `.scd`). For the earliest
releases where the corpus is embedded directly in executables, it falls back to
preserving the `.exe` files so no DOS version is silently dropped.

The same manifest also drives build-group selection in `thelp.sh`, so Scorpion's
opt-in build behavior is no longer hardcoded only in the shell wrapper.

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
| `common.py` | compatibility re-export shim for older entry points |

## Requirements

- Python 3.10+
- `unar` and `lsar` on PATH

Install:

- macOS: `brew install unar`
- Linux: `sudo apt install unar`

## Output

Collected help files are copied into `sources/<Product Label ...>/`.
Those directories are then consumed by `python -m thelpviewer.converter` / `./thelp.sh build`.
