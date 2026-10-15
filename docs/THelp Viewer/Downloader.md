# Downloader

> Updated: 2026-10-15

## Shared online queue

The server creates one `OnlineDownloader` in `app.state.downloads` and gives it
to HELP orchestration, DOS packages and the MIDI library. Network transfers use
the same bounded `read_request` transport. It handles GET/POST, streaming byte
counts, atomic file writes, transient network/5xx retries and three bounded
HTTP 429 attempts with countdowns. HTTPS host restrictions for MIDI remain in
force; all connections also reject private resolved peers. Source discovery,
archive layout and format conversion remain provider/consumer modules.

Before sending a request, the transport converts HTML Unicode URLs to ASCII
wire addresses: path/query Unicode and spaces use UTF-8 percent encoding; Unicode
host names use IDNA. Existing percent escapes, query separators and literal `+`
remain intact. GET, POST, form actions and redirects share this behavior; request
headers, methods and form bodies are retained. Source/catalog URLs and IDs do not
change. URL validation runs before and after encoding, rejecting controls,
credentials and private/local addresses; redirect HTTPS/host checks still apply.

`submit(source, limit, kind=..., key=..., label=..., destination=..., process=...)`
accepts a URL/form definition, optional reusable cache path and Python processor.
It returns a Future. The processor receives downloaded/cached bytes and may
unpack, validate or prepare installation, returning its result to the caller.
`enqueue` and blocking `call` compose existing module pipelines without CLI
subprocesses. Three regular workers select the highest-priority eligible job
from different sources, skipping busy sources rather than blocking unrelated
downloads behind them. A source permits one job/response-body transfer at a
time, shared by HELP, DOS and MIDI. Negative priority uses one reserved urgent
playback worker: it may run beside unrelated package work, but cannot bypass
the source limit. Newer waiting urgent requests go first and take precedence
over waiting regular work for the same source. At most four jobs execute at
once, never ten transfers from one site. Running transfers are not aborted.
Unkeyed local pipelines remain serial. Response-body guards also apply to the
final redirect/form destination. Site keys conservatively group the final two
DNS labels, so archive.org and its storage mirrors share a lane; sites under
multi-label public suffixes may share a stricter-than-necessary lane.
HTTP 429 Retry-After cooldowns apply to later jobs from the same source,
including after the last failed attempt, without pausing unrelated sites.
An active job's own bounded retries still show the existing countdown.
This is an in-process scheduler; multiple server processes are not supported.
Nested transfers run inline on their current worker rather than requeueing into
a blocked worker. An optional `identity` deduplicates an in-flight unit and lets
an urgent request promote its waiting Future without cancelling the caller or
starting another copy of the same request. Context follows a promoted job too.
MIDI playback requests retain selection and album checks, skip cached files,
and enqueue the catalog item directly rather than using a private priority stack.

Task context follows the queued operation, so progress does not leak between
HELP, DOS and MIDI threads. Planned rows use `begin`, `update` and `finish`;
known file byte counts contribute partial progress, completed/cache items count
as complete. Unknown source/archive counts are not invented; discovery can change
the denominator. Background MIDI rows are aggregated by provider/album; requested
playback tracks get named priority rows at the front. Completed tracks move to
Completed downloads. Changing MIDI selections/indexes or rebuilding waits for
active playback writes and cancels waiting ones before changing generated data.
Queue state is held
in memory for the latest operation per kind, not stored as permanent history.
Stopping/restarting the server does not remove caches or private user data.

The counter measures the current batch, separately from retained queue rows.
After successful completion its API percentage resets to zero. Adding more
work or retrying after idle starts from zero; old successful rows are not part
of that denominator. Concurrent tasks join the current batch, and completed
work stays counted until that batch ends. A new MIDI operation also starts
fresh for public viewers while private package work continues. Preparation/
publication remains active until its owner finishes; it cannot show 100% merely
because its files finished transferring. Failed work retains partial progress.

GET `/api/downloads` is a read-only, no-store snapshot. Administrators with the
existing same-origin session guard see HELP/DOS and MIDI; others see MIDI only.
It cannot submit arbitrary URLs or host commands. Configuration/installation
APIs keep their existing administrator checks and confirmation workflow.
The live `TVDownloadProgress` caption between account and clock contains only
the Unicode down arrow and, while progress is shown, a percentage. Its first submenu, Completed downloads,
holds successful rows; waiting, active and failed rows stay in the main popup.
Rows include state markers and rate-limit countdowns. It uses the
normal TVMenuView event flow, TVMenuBox framing and scrollbar. Updating progress
keeps an open popup/submenu, focus and scroll position; closing it does not cancel
work. Successful completion leaves only the down arrow, with no `100%` in the
caption; completed rows remain accessible at 100% in the history submenu. Only
an empty queue hides the indicator. Failed queues retain actual partial progress. The next operation of
the same kind replaces its runtime rows; this is not permanent download history.
Existing detailed installation dialogs still report conversion/publication;
download/source-check completion alone is not proof of a published HELP bundle.

Show Downloads in the menu and Apply in HELP/DOS configuration reuse one Downloads
dialog. It is an ordinary nonmodal `TVProgressDialog`, owned/registered by the
desktop, not a source-specific HTML window. More/Less reveals a green TVListBox
fed by the shared snapshot for all visible HELP/DOS/MIDI groups. Live changes
preserve selection/scroll. A followed installation can supply its phase, overall
percentage and archive/cache counters via `setOperation`; downloader updates do
not overwrite conversion/publication progress. Successful rows leave the details
list and remain in the menu's Completed downloads submenu. With no unfinished
rows, the details pane collapses; the dialog may stay open with its finished
gauge at 100% even after the menu counter resets. Hiding it does not cancel the
transfer or installation.

Clicking a failed row opens a Turbo Vision dialog composed from shared views:
Retry, Remove and Cancel. Its complete source label, error and notice wrap using
the MessageBox text helper; character-cell bounds follow the text and buttons
wrap into rows when the viewport is narrow. Closing with `[ ]` or Escape is Cancel. Remove forgets
that grouped runtime row; it does not uninstall content, delete downloaded files
or change the configured selection. A later explicit operation can show it again.

POST `/api/downloads/action` accepts only `{ "id": "kind:group", "action":
"retry" | "remove" }` for an existing failed row, not a URL. HELP/DOS actions and
MIDI source-index retries require the existing same-origin administrator session.
Public MIDI album actions require a same-origin request; retry revalidates current
provider/album selection. Invalid/stale rows, unselected content and duplicate or
busy retries return 409 without silently changing selection. Retry is disabled in
the dialog while that content kind is still running or for generic preparation
errors that have no retryable package/source identity.

Consumer modules register a `register_retry(kind, prepare)` callback on the shared
downloader. It validates the group and returns a pipeline for just its failed unit
IDs. A retry keeps unrelated runtime rows and successful units. MIDI retries only
failed tracks of the clicked album, not the whole library. HELP rechecks the failed
providers and stages conversion/publication of that edition, retaining other
published versions and products. DOS stages the clicked package on top of all installed packages,
without applying other pending installs/removals from the failed configuration.
Existing quotas, validation, backups and private-overlay protections still apply.
A repeated failure remains failed with its current error; retry is not a bypass
for source rate limits, invalid archives or unavailable files.

Automated downloader for DOS and Windows help-file sources.

The downloader is split into three layers:

1. `thelpviewer/config/help-database.json` defines **what** logical product families
   we want, how each provider should find them, and which archive files to
   collect. The converter separately detects supported inputs.
2. `winworld.py`, `archiveorg.py`, `direct.py`, `olddos.py`, `github.py`, `davep_ng.py`, `cheater_cz.py`, `slunecnice.py` define **how**
   each concrete website is scraped and downloaded.
3. `service.py` orchestrates callable provider jobs; `transport.py` supplies
   shared queued public-network downloads for HELP, DOS and MIDI. `catalog.py`
   exposes typed manifest objects and `extractor.py` handles
   unpacking through `unar`/`lsar`, including
   nested archives and disk images.

## Usage

The server's **HELP Packages** dialog selects HELP editions by product and version
and calls `download_products(..., package_ids=...)` directly. A request-local
provider context restricts CRC-edition queries and filters discovered WinWorld,
Archive.org, old-dos and Cheater release pages before archive downloads. The
conversion stage independently checks authoritative CRC/source metadata before
publication. Family-level maintenance calls omit `package_ids`; an empty list
selects no editions. DOS Packages and MIDI Sources derive from the same dialog base;
applying one type leaves the others unchanged. API progress uses
the job's callback and `observe_downloads()`, not captured terminal output.
Empty server selections download nothing. Provider failures are surfaced as
warnings; absence of usable input fails the build without publishing it.
See [Server Content](Server%20Content.md) for storage, setup and API behavior.

Progress reports the destination archive name, not the last component of a
mirror URL. WinWorld pinned selectors read the download page's title and mirrors
together to produce readable cache names; unknown archive extensions use
`.archive` and extraction still probes the actual bytes. URL-escaped direct
archive names are decoded and sanitized within `var/downloads/help/`.
Discovery, reuse of cached archives, extraction and rate-limit waits are explicit
phases. Per-transfer bytes reset when the phase changes. The callable service
also reports source/product task snapshots and new/cached file and byte counts;
unvisited sources are pending, not assumed downloaded. Provider warnings stay
visible in the API even when other archives can still be converted.

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
  prefixes, provider queries, conversion rules, and optional verified `versions`
  for databases without CRC edition entries
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
Paths match at directory-component boundaries, including a nested archive's
enclosing extraction directories. A basename selects exactly one matching
file anywhere in that tree; it does not resolve ambiguity by taking the first
match. Existing originals are skipped only if their bytes are identical;
a different payload at the same destination fails without overwriting it.
Products with many releases keep these values once at family level. Known files
remain independent `entries`; their family and release are derived from the
configured `collection_prefixes`, or can be stated explicitly with `product`
and `release`.

Individual CRC entries can also retain `sources`, using the same typed
provider/query fields as product sources: `search_text`, `query`,
`direct_urls` and `archive_members`. The shared provider catalog expands
these into edition download jobs in addition to the family discovery query,
deduplicating identical queries and keeping the same stable product key.
Exact-member jobs use the edition's collection, not the family's first root,
so pinned disk images do not get extracted into another product/release.
WinWorld's pinned selectors and explicit edition pages also use that configured
collection verbatim: the display release does not manufacture another source
directory. Ordinary family version discovery retains its product/version layout.
Keep a verified release page and its download-selector page (not an expiring
mirror URL), the enclosing package name and exact member in the search text,
and a portable fallback query. WinWorld can consume the retained download
selector directly even if product-page scraping fails, and extracts only
the configured members. Archive.org executes edition fallback queries too,
without processing the same item twice after a successful collection.
Server/CLI orchestration invokes each provider/product once, not once per
edition; each provider consumes its complete family/edition job list.
Database rebuild preserves these entry fields; a CRC identifies the extracted
original, not its containing archive. A fallback query is a discovery hint,
not proof that another site currently holds the same bytes.

Borland C++ 4.52's registered Windows HLP/HLX pairs are pinned to its CD
download selector: the 20 existing `Borland C++ 4.x` indexes match those HLPs.
The distinct BCW/OWL 4.5 pairs use the separate `Borland C++ 4.5` collection;
the other 18 identical indexes are not installed again. Windows HLP files
are retained as originals even when their visual conversion is unfinished;
downloader collection and converter detection are separate decisions.
Archive.org's 4.5 discovery can find floppy media rather than the CD, so its
exact basename selection does not require the CD's `BC45/BIN` prefix.
That fallback query has been checked for discovery, not for byte-identical
payloads. The pinned WinWorld CD source supplies the verified CRC entries.
Archive.org can also select an ISO when a package has no ZIP/7z/RAR;
raw flux captures are not chosen as ordinary disk images.

Turbo Debugger now also discovers its DOS/Windows/32-bit HELP through the
Turbo Assembler WinWorld product; the Archive.org fallback searches Debugger,
Profiler and Assembler distributions. The registered Debugger 1.5/4.0/5.0,
TASM 2.0/2.01, Profiler 1.01 and Sidekick 1.56b/2.0 originals keep edition-specific
provenance. Debugger 1.5 also has executable `direct` jobs for the separate
English Utilities and German Hilfe disk images. Exact duplicates from the 2.0
disks need no additional source copy or CRC row; the existing record gets the verified release and retrieval
information. Language describes the HELP text, not merely the installer.

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
- `7zz` as an alternative/fallback, including FAT floppy images that `unar`
  does not recognize

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
SZDD and the Microsoft `SZ ... D1` profile use the shared bounded LZSS
decoder. When a D1 stream spans disks, the extractor locates uniquely named
`NAME.HL2`, `NAME.HL3`, ... parts throughout the extracted archive, validates
their sequence/header numbers, and removes only their eight-byte headers.
It decodes the combined stream once, preserving dictionary and control-bit
state across media. Recognized damaged or ambiguous compressed payloads fail
before original files are copied; they no longer silently disappear.
Unrelated filenames and other releases are never guessed as continuations.
Decoded Microsoft payloads are bounded to 64 MiB.
See [Microsoft SZ Compression](../Formats/Microsoft%20SZ%20Compression.md)
for byte layouts and the algorithm.

QuickC 2.50's original ZIP contains `QC.HL$` on `Advisor.img` and `QC.HL2`
on `Learning.img`; together they restore the 876-topic `QC.HLP` (CRC32
`0143767A`). Its CRC entry retains the verified Archive.org distribution,
portable fallback query and an executable exact-member job for `QC.HLP`.
The normal family collector also retains the four companion HLPs.

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

- macOS: `brew install unar sevenzip` (7-Zip is needed for FAT disk images)
- Linux: `sudo apt install unar`

## Output

Collected help files are copied into `data/sources/<Product Label ...>/`.
Those directories are then consumed by `python -m thelpviewer.server.converter` / `./thelp.sh build`.
