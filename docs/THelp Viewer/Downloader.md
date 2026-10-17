# Downloader

> Updated: 2026-10-17

## Shared online queue

The server creates one `OnlineDownloader` in `app.state.downloads` and gives it
to HELP orchestration, DOS packages and the MIDI library. Network transfers use
the same bounded `read_request` transport. It handles GET/POST, streaming byte
counts, atomic file writes, transient network/5xx retries and three bounded
HTTP 429 attempts with countdowns. HTTPS host restrictions for MIDI remain in
force; all connections also reject private resolved peers. Source discovery,
archive layout and format conversion remain provider/consumer modules.

`online.py` owns scheduling, source lanes, urgent priorities and retry dispatch.
Its explicit `DownloadProgress` component in `progress.py` owns thread-safe
rows, batches, percentages and snapshots, sharing the coordinator's lock.
There is no inheritance/mixin chain or dynamic method forwarding.
`attempts.py` runs ordered alternative attempts for HELP and DOS; their callers
still decide when the result is complete. HELP verifies edition CRC components,
DOS extracts its own recipe, and MIDI validates tracks/partial ZIP members.
`errors.py` distinguishes unavailable content (including missing forms and
incomplete responses), exhausted HTTP 429 and fatal URL/peer/redirect policy
failures. Policy failures propagate through providers and never trigger fallback.

`cache.download_cached(destination, limit, fetch, process=..., on_cached=..., identity=...)`
uses a staged Path on the destination filesystem. Fetch writes that path;
size/regular-file checks and an optional domain processor run before atomic
publication. Existing cache entries are checked and processed again without a
network request; a failed processor preserves the old cache and removes only
new staging. HELP's streaming wrapper and DOS package downloads share it.
An existing cache file must also permit an actual read before it counts as a
cache hit. A filesystem I/O error (including an unavailable cloud placeholder
visible through a Docker bind mount) triggers a fresh fetch to staging, not
archive extraction. Publish the replacement only after its processor succeeds;
on fetch/processing failure preserve the old file. Safety/size violations do not
use this recovery path. This recovers a download, not permanent original HELP
or private user data, and does not change the host's cloud-storage settings.
Raw HELP cache validates the bounded transport/file, not converter semantics;
source selection, CRC completeness and conversion remain separate checks.
MIDI validates decoded tracks before the same atomic file-write primitive.
Successful downloads and reuses update cache mtime for retention. Failed
processors do not refresh it. Server Configuration's **Cache lifetime (days)**
sets `download_cache_days` (1–3650, default 30), measured since successful use.
An idle-only sweep runs at startup and hourly over `help/`, `dos/` and `midi/`
and the configured HELP inputs directory (default `var/sources/`). New/identical
accepted source copies and successful server conversion refresh input mtime;
passive CRC/catalog scans and failed conversion do not. Existing input mtimes
are used as-is; review/archive old manual inputs before enabling expiration.
It removes expired payloads with their source metadata and empty directories,
preserving recent siblings and refusing linked/special files or protected-path
overlaps before deleting anything. HELP originals and licences expire too,
including manual files; unavailable originals may not be downloadable again.
It does not remove published HELP, installed content, music/covers, backups or
private data. Shorter retention
takes effect on the next idle sweep. Expired archives are fetched again on demand.

Administrators can use **Server Configuration > Clear cache** to remove raw
source downloads under the configured downloads directory's `help/`, `dos/`
and `midi/` scopes, including abandoned `.download-*`/transfer staging inside
those trees, **plus all extracted/manual HELP originals and licence files**
under the configured sources directory (default `var/sources/`), regardless of
age. `POST /api/admin/cache/clear` requires the administrator's session
and same-origin write protection, and returns `files` and logical source
`bytes` removed. The dialog requires explicit OK (Cancel, Escape and title
close do nothing) and reports the result. This is deletion, not a backup:
archives and registered originals are fetched again if needed, not immediately
after clearing. The confirmation warns that manually supplied or unavailable
originals may be impossible to retrieve again; save an independent copy first.
The shared downloader's idle maintenance lock rejects running/queued transfers,
active processing and retries; new queue work waits until deletion completes.
All scopes are preflighted before deletion, rejecting symbolic links, special
files and overlap with permanent/installed content. Only scope contents are
deleted; cache directories and unrelated files in the downloads root remain.
Generated UHF/catalogs/search indexes, shared DOS C, decoded MIDI
tracks/covers/catalogs, backups, account settings and private data are retained.
No global `var/`, `data/`, host temporary-directory or Python-cache cleanup runs.

Software package definitions can add `alternatives`, a list of up to eight
complete download/extraction recipes. Each uses its own `url`/`download_forms`,
`format`, optional `image_member` and `extract` rules; it does not inherit an
incompatible primary layout. Identity, title, language, installation target,
configured files and post-install behavior remain the package's, not an
alternative's. Nested collection components cannot change their recipe using
alternatives; make the whole collection an alternative instead.
`download_package(..., process=...)` passes downloaded/cached bytes and their
recipe to a validator/extractor before publishing a new cache file. It returns
that processor's result and the actual archive cache key (raw bytes without a
processor). Failed extraction/checksum or exhausted network retries move to the
next configured recipe; source limits still apply across subdomains, and unsafe
URLs/credentials/private peers remain errors, not a reason to bypass guards.
DOS raw archives use `<package-id>/<readable-archive-name>`, retaining an original
archive suffix where available; opaque endpoints use the package ID plus a
format-appropriate suffix. Collections have a generated `.zip` wrapper.
A sibling `<archive-name>.source.json` stores the source key and payload
SHA-256. Cache hits require both to match. Same-name alternatives may share a
readable slot but never reuse one another's bytes: mismatched identity triggers
staged download/validation before replacement. The content hash also prevents
a crash between atomic payload/metadata writes from accepting stale identity.
Package IDs sharing the same input retain source-level serialization: reuse a
verified cached copy before fetching, including simultaneous requests from
different packages. Readable names do not cause duplicate network transfers.
On upgrade, recognized flat hash entries move to readable paths after verified
copying, preserving mtime. Unmapped inputs remain until expiry; no runtime
fallback to old hash filenames is retained.
Old SHA-pinned DOS receipts without ownership inventories require a separate
one-time installation migration before cache expiry. It accepts only an archive
whose SHA-256 equals that receipt's former hash and whose selected files match
the live shared disk byte for byte. After all candidates pass preflight it
publishes checksum-verified readable caches, updates receipt keys/inventories,
then removes the redundant flat copies. A receipt-write failure retains the
original cache and can be retried. Missing/corrupt archives, modified disk files,
different pinned revisions and post-install-generated output are not guessed.
No network request or shared/private C write is needed for this migration.
Package intent/installation
identity includes the alternative definitions; normal installed-file ownership
continues protecting safe updates/removals. Downloading does not itself install
or change an administrator's selection. Failed recipes are reported together
if none succeeds, preserving old caches and the staged/live disk.

Before sending a request, the transport converts HTML Unicode URLs to ASCII
wire addresses: path/query Unicode and spaces use UTF-8 percent encoding; Unicode
host names use IDNA. Existing percent escapes, query separators and literal `+`
remain intact. GET, POST, form actions and redirects share this behavior; request
headers, methods and form bodies are retained. Source/catalog URLs and IDs do not
change. URL validation runs before and after encoding, rejecting controls,
credentials and private/local addresses; redirect HTTPS/host checks still apply.

`enqueue` and blocking `call` schedule HTTP steps without CLI subprocesses;
there is no second URL-submit/cache implementation in the queue.
Three regular HTTP workers select the highest-priority eligible transfer
from different sources, skipping busy sources rather than blocking unrelated
downloads behind them. A source permits one job/response-body transfer at a
time, shared by HELP, DOS and MIDI. Negative priority uses one reserved urgent
playback worker: it may run beside unrelated package work, but cannot bypass
the source limit. Newer waiting urgent requests go first and take precedence
over waiting regular work for the same source. At most four HTTP steps execute
at once, never ten transfers from one site. Running transfers are not aborted.
Response-body guards also apply to the
final redirect/form destination. Site keys conservatively group the final two
DNS labels, so archive.org and its storage mirrors share a lane; sites under
multi-label public suffixes may share a stricter-than-necessary lane.
HTTP 429 Retry-After cooldowns apply to later jobs from the same source,
including after the last failed attempt, without pausing unrelated sites.
An active job's own bounded retries still show the existing countdown.
This is an in-process scheduler; multiple server processes are not supported.
Nested transfers run inline only on an HTTP worker. `enqueue_processing` and
blocking `process`/`run_processing` use three separate local-processing workers
and one reserved urgent worker. HELP ingestion and DOS extraction run there,
after their HTTP step has released its site slot. `prepare(items, operation)`
uses three bounded orchestration drivers per installation, not extraction slots
while waiting for network. HELP and DOS installations therefore submit transfers
independently, even while the other type is converting or waiting on a site.
All of these drivers still share the same three regular HTTP lanes and the same
local extraction pool; this does not grant three connections per installation.

`pipeline(items, submit)` bounds each consumer to three in-flight units and
drains active writers on exit/failure. Its optional source hint selects a later
independent origin before filling slots with another waiting origin; HELP derives
it from edition query URLs/provider identity. Hints are advisory, not permissions
or locks: actual transport limits and fallback security remain authoritative.
Ordered consumption always preserves DOS installation and post-install BAT
dependencies in manifest order even when later inputs prepare first. HELP feeds
ready editions to one staged converter and publishes each validated edition
immediately. MIDI source delays apply to subsequent HTTP transfers too.
Cancelling pending MIDI work cancels its queued HTTP steps, not unrelated jobs;
active writes finish before selection changes, rebuilds or shutdown continue.

An optional `identity` deduplicates an in-flight unit and lets
an urgent request promote its waiting Future without cancelling the caller or
starting another copy of the same request. Context follows a promoted job too.
MIDI playback requests retain selection and album checks, skip cached files,
and enqueue the catalog item directly rather than using a private priority stack.

Task context follows the queued operation, so progress does not leak between
HELP, DOS and MIDI threads. Planned rows use `begin`, `update` and `finish`;
single-file byte counts contribute partial progress, completed/cache items count
as complete. Compound units use `byte_progress=False`: their owner's explicit
stage percentage (DOS download/extract/install) takes precedence. Server HELP
uses `download_products(..., finalize=False)`: verified sources leave the row
running at 35%, conversion advances it up to 95%, and only successful publication
marks it done/100%. Conversion failure remains on that edition, not a previously
completed row. Standalone download jobs finalize when source collection ends.
MIDI source indexes advance when the planned check finishes.
A discovery HTML response or one archive is not the size of the whole compound
unit. Raw byte counters remain available to its detailed operation dialog.
Unknown source/archive counts are not invented; discovery can change
the denominator. Background MIDI rows are aggregated by provider/album; requested
playback tracks get named priority rows at the front. Completed tracks move to
Completed downloads. Changing MIDI selections/indexes or rebuilding waits for
active playback writes and cancels waiting ones before changing generated data.
Queue state for the latest operation per kind is mirrored in
`data/jobs.sqlite3`. Explicit queued/interrupted HELP/DOS operations resume
after restart; terminal failures require Retry/Apply. Completed HELP editions
publish immediately and are verified/skipped during recovery. Global indexing
shares the job journal but keeps its own per-file transactional search database.
See [Durable jobs and restart recovery](Server%20Content.md#durable-jobs-and-restart-recovery).
Stopping/restarting the server does not remove caches or private user data.

The counter measures the current batch, separately from retained queue rows.
After successful completion its API percentage resets to zero. Adding more
work or retrying after idle starts from zero; old successful rows are not part
of that denominator. Concurrent tasks join the current batch, and completed
work stays counted until that batch ends. A new MIDI operation also starts
fresh for public viewers while private package work continues. Preparation/
publication remains active until its owner finishes; it cannot show 100% merely
because its files finished transferring. Failed work retains partial progress.

Within a batch each visible package/album has equal weight. HELP has one unit
per edition, not one per provider; MIDI track units contribute their album's
partial percentage. Adding fallback providers does not change a HELP edition's
weight or create spurious failed packages after a successful fallback.
Only units from the current batch contribute to its counter. Already installed
DOS packages are checked on disk without being requeued as new completed work.
Only successful units count as 100%; failed editions retain their actual partial
progress, capped below completion. These are package/work percentages,
not a byte-weighted estimate of unknown future archives or a time estimate.
HELP percentages can therefore pause during a multi-request source check or an
HTTP 429 cooldown; they do not jump up/down with each HTML page's Content-Length.

Discovered WinWorld release pages are not exact archive identities: their
archive titles are filtered against the requested edition before transfer.
After extraction, a known source CRC selects the manifest's canonical collection
and exact product/version selection. An unselected verified sibling is not
copied into the requested edition's directory. Unknown conflicting originals
remain an error and are never overwritten. Loose HELP downloads from Archive.org
and GitHub pass through this same collector, not directly into published sources.

`plan_help_downloads` returns one `id`/`group` per exact selected edition, with
its ordered `sources` from the manifest. A product with no applicable provider
retains a visible failed row instead of disappearing from the plan. Providers
are tried for one edition before the next edition. No new catalog schema or
product-specific fallback rule is needed: family and matching CRC-entry sources
in `help-database.json` supply the existing provider queries/URLs.
For an explicitly selected edition, providers with matching CRC-entry recipes
precede family-only providers; within each provider matching entry recipes
precede the family scan. The family remains available for missing components.
The operation processor remembers each attempted URL/source plan (including
empty results and failures) for that edition, so overlapping discovery queries
do not repeat the same extraction or failed transfer. Different member plans,
collections and mirror URLs remain distinct; an explicit Retry starts fresh.
Archive.org also remembers empty/failed item/member selections for its run,
without suppressing a later query's search fallback.

After three exhausted HTTP 429 attempts, a request-scoped set defers the site
(the same conservative site key used by the shared scheduler) for the remainder
of that HELP operation. Subsequent requests and redirects to that site fail
before queueing/network access, avoiding another cooldown for each mirror or
edition. Other sites remain eligible, including URLs from a mixed-host direct
provider. The first site's bounded Retry-After countdown and shared cooldown
still apply; limits are not bypassed. A later explicit installation/Retry starts
with a fresh set. DOS/MIDI keep their existing bounded retries and cooldowns.

Fallback stops early only when each registered collection/bundle component of
the selected edition has an original with a matching registered CRC in its
canonical collection. CRC revisions of the same component are alternatives.
Filenames or a provider returning a nonempty list alone are insufficient;
verified sibling editions do not satisfy the request. Existing complete verified
sources can be reused without network access. Products without registered CRCs
continue discovery and require the existing conversion/publication validation.
The processor rechecks completeness after every ingested archive/file; each
provider's optional `complete` predicate stops before the next candidate, not
only after the entire provider has run. Discovery of multi-file Archive.org or
Old-DOS sets uses partial member collection: collect uniquely matching requested
files from each candidate, without requiring every disk to contain them all.
Ambiguity, unsafe archives and extraction failures remain errors; strict pinned
archive recipes still reject missing members. Only the full CRC-verified set
can satisfy the registered edition and stop discovery.
`DownloadResult.warnings` retains failed-source diagnostics even after recovery;
`errors` identifies incomplete registered sets or unavailable provider plans,
which prevent server publication. A non-CRC edition's source warnings remain
diagnostic while staged conversion validates its active queue row; failed
conversion keeps the existing HELP untouched. Registered CRC entries are not
discarded by the generic accessory-name filter (for example QuickBASIC's
`UTILS.HLP`); unregistered accessories are still excluded.
Successful fallback completes the edition, not the failed network transfer.

Registered editions with different bytes and the same original filename use
separate canonical collections in the JSON manifest. Turbo Debugger 1.0, 2.x,
4.0 and 5.0 use `Borland Turbo Debugger/<release>/`; Profiler 1.01 uses its own
`1.01/` collection. This does not rename TDHELP/TDWHELP/TD32HELP/TFHELP internally.
The release-unknown Profiler retains its existing collection. If a corrected
manifest moves an original formerly occupying another edition's slot, ingestion
may relocate it only after its CRC identifies the new canonical destination;
an unknown original, link or different existing destination still fails safely.
Shared-path locks and atomic original publication prevent concurrent editions
from fetching the same missing archive twice or observing a partial copy.

Old-DOS `dl.php?id=...` links are distinct archives despite sharing a basename.
Their cache names contain the readable entry title and stable entry ID rather
than reusing one `od_dl.php`. The registered TASM CRC `9AC3E64A` uses collection
`Borland Turbo Assembler`; `07E89446` retains its existing collection and source
path. These different originals cannot overwrite each other. Normal selected
rebuilds regenerate their UHF/catalog entries without keeping old URL aliases.
All five registered TASM inputs have explicit edition metadata; the two formerly
unregistered copies from C++ 3.0/3.x share CRC `91D5F0DE` (TASM 3.0), while German
Pascal 7's `C74EE5C6` belongs to the bundled TASM 3.2. Their exact WinWorld
selectors, member lists and fallback queries are executable CRC-entry recipes.
`9AC3E64A` is TASM 3.1 from BCPP31.ZIP. Containing compiler versions and old
version mentions within a topic are not sufficient evidence of a tool release.
Member selection prioritizes matching nested-container stems before unrelated
archives, including after split-media assembly, and checks completion before
each sibling. Identical same-name member copies are compared byte-for-byte and
collected once; different bytes or different names remain ambiguous. Thus the
German TASM recipe does not unpack a corrupt, unrelated BPWHLP.ZIP payload.

Tool stdout/stderr uses UTF-8
diagnostic decoding with replacement for legacy display bytes; this does not
recode extracted filenames, contents or archive-member selectors. Old-DOS's
public categories use its working `http://old-dos.ru` origin explicitly; its
HTTPS endpoint redirects back to HTTP. Other HTTPS requests still cannot
downgrade through redirects, and public-peer/credential checks remain.

GET `/api/downloads` is a read-only, no-store snapshot. Administrators with the
existing same-origin session guard see HELP/DOS and MIDI; others see MIDI only.
It cannot submit arbitrary URLs or host commands. Configuration/installation
APIs keep their existing administrator checks. Apply submits package/source
selection directly; separate rebuild/delete actions retain their confirmations.
The live `TVDownloadProgress` caption between account and clock uses
`↓` for transfers, `▣` for extraction and `⚙` for conversion, installation,
validation and publication. Simultaneous stages appear together. A phase shows
a percentage only when its own byte or work count is known; otherwise only
the symbol is shown. Discovery/waiting shows `…`; failure shows `!`.
The API exposes `stage` and nullable `stage_percent` on each row. A new phase
clears the previous phase's percentage; these values are separate from the
owner-weighted overall `percent` used by the dialog's batch gauge.
For example, transferring an archive may reach `↓ 100%`, followed by `▣`
without a known extraction total, then `⚙ 25%` during conversion.
Python ZIP extraction counts extracted entries. External unar extraction uses
the successfully completed entry lines and lsar's total entry count; 7-Zip uses
its native percentage output (`-bsp1`). Output is consumed in bounded chunks
from a spool without changing the child process's write offset. Extraction
still enforces timeout, path and expanded-size limits, and validates the final
tree before reporting successful completion. Totals are local to the current
archive, including nested archives, not the complete package's future work.
HELP conversion percentages count completed source files/source groups in the
edition; a decoder without an internal work counter does not estimate its own
remaining time. Unknown totals remain indeterminate. A phase reaching 100% is
not installation/publication success: only the domain owner marks the row done.
ZIP detection requires a readable central directory, not only an end marker:
FAT images can contain ZIP files whose end records make `is_zipfile` return true
for the enclosing image. Such containers continue through external inspection.
Readable ZIP metadata still rejects traversal, links, encryption and exceeded
quotas before extraction; those failures are not reinterpreted as disk images.
Its first submenu, Completed downloads,
holds successful rows; waiting, active and failed rows stay in the main popup.
Rows include state markers and rate-limit countdowns. It uses the
normal TVMenuView event flow, TVMenuBox framing and scrollbar. Updating progress
keeps an open popup/submenu, focus and scroll position; closing it does not cancel
work. Only successful completion of the full processing pipeline shows `✓`, with no `100%` in the
caption; completed rows remain accessible at 100% in the history submenu. Only
an empty queue hides the indicator. Failed queues show `!`, not a success tick.
An explicit HELP/DOS selection replaces its current queue rows. MIDI startup
checks local tracks and every member of a ZIP album before queueing work; cached
pages and complete albums do not create a new batch, flash "Downloading" or alter
another content type's counter. Existing completed/failed album rows remain in
history, while deselected entries are removed. If publication finished before a
crash, the verified output completes its interrupted row without a transfer.
Retained operational jobs are not an unlimited list of completed menu rows.
The existing-file check tests size and the `MThd` prefix, not the complete SMF.
New transfers/extractions are validated and normalized before publication;
older cached payloads are not retroactively revalidated or rewritten by startup.
Existing detailed installation dialogs still report conversion/publication;
download/source-check completion alone is not proof of a published HELP bundle.

Show Downloads in the menu and Apply in HELP/DOS configuration reuse one Downloads
dialog. It is an ordinary nonmodal `TVProgressDialog`, owned/registered by the
desktop, not a source-specific HTML window. More/Less reveals a green TVListBox
fed by the shared snapshot for all visible HELP/DOS/MIDI groups. Live changes
preserve selection/scroll. Its shared-view layout uses up to 64 columns, wraps
the complete phase/counters and filename, and allocates separate rows for the
gauges, buttons and list, without an unused filename row or empty bottom padding.
Long package names remain complete in the TVListBox
and can be read with its standard horizontal scrollbar.
A followed installation can supply its phase, overall
percentage and archive/cache counters via `setOperation`; downloader updates do
not overwrite conversion/publication progress. Successful rows leave the details
list and remain in the menu's Completed downloads submenu. With no unfinished
rows, the details pane collapses; the dialog may stay open with its finished
gauge at 100% even after the menu counter resets. Hiding it does not cancel the
transfer or installation.

Clicking a failed or blocked ("Not started") row opens a Turbo Vision dialog composed from shared views:
Retry, Remove and Cancel. Its complete source label, error and notice wrap using
the MessageBox text helper; character-cell bounds follow the text and buttons
wrap into rows when the viewport is narrow. Closing with `[ ]` or Escape is Cancel. Remove forgets
that grouped runtime row; it does not uninstall content, delete downloaded files
or change the configured selection. A later explicit operation can show it again.
MIDI startup skips downloads with recorded failures instead of silently retrying
them and recreating removed rows. Diagnostics stay in the MIDI catalog; explicit
Retry, a missing-track playback request or applying source selection can retry.

POST `/api/downloads/action` accepts only `{ "id": "kind:group", "action":
"retry" | "remove" }` for an existing failed/blocked row, not a URL. HELP/DOS actions and
MIDI source-index retries require the existing same-origin administrator session.
Public MIDI album actions require a same-origin request; retry revalidates current
provider/album selection. Invalid/stale rows, unselected content and duplicate or
busy retries return 409 without silently changing selection. Retry is disabled in
the dialog while that content kind is still running or for generic preparation
errors that have no retryable package/source identity.

Consumer modules register a `register_retry(kind, prepare)` callback on the shared
downloader. It validates the group and returns a pipeline for just its failed unit
IDs. A retry keeps successful units. MIDI retries only
failed tracks of the clicked album, not the whole library. HELP rechecks the clicked
edition's configured providers with fresh rate-limit deferral and stages
conversion/publication of that edition, retaining other
published versions and products. DOS resumes the saved selected additions, not
only the clicked package: a disk transaction failure may have prevented later
packages from being installed. It also retains all currently installed packages;
pending removals require Apply. Unselected stale failure/blocked rows are removed,
successful cached installs clear their earlier errors, and the complete target is
journaled before Retry starts, so restart resumes the same request. A blocked row
remains actionable even if the original failing row was removed. No terminal
failure is automatically retried on startup.
Existing quotas, validation, backups and private-overlay protections still apply.
A repeated failure remains failed with its current error; retry is not a bypass
for source rate limits, invalid archives or unavailable files.

Automated downloader for DOS and Windows help-file sources.

The downloader is split into three layers:

1. `thelpviewer/config/help-database.json` defines **what** logical product families
   we want, how each provider should find them, and which archive files to
   collect. The converter separately detects supported inputs.
2. `winworld.py`, `archiveorg.py`, `direct.py`, `olddos.py`, `github.py`, `davep_ng.py`, `cheater_cz.py`, `slunecnice.py` define **how**
   each concrete website is scraped. Their shared contract is
   `run(product_keys, dl_dir, dry_run, process)`: discovery supplies a
   `converter.ingest.HelpInput` and URL/headers to the processor. Providers
   never choose extraction tools or write original HELP files themselves.
3. `service.py` orchestrates callable provider jobs; `transport.py` supplies
   shared queued public-network downloads for HELP, DOS and MIDI. `catalog.py`
   exposes typed manifest objects. `server/archives/` handles bounded
   unpacking independently of downloads or HELP selection; the HELP processor
   lives in `converter/ingest.py`.

## Usage

The server's **HELP Packages** dialog selects HELP editions by product and version
and calls `download_products(..., package_ids=...)` directly. A request-local
provider context restricts CRC-edition queries and filters discovered WinWorld,
Archive.org, old-dos and Cheater release pages before archive downloads. The
conversion stage independently checks authoritative CRC/source metadata before
publication. Family-level maintenance calls omit `package_ids`; an empty list
selects no editions. DOS Packages and MIDI Sources derive from the same dialog base;
applying one type leaves the others unchanged. API progress uses
the job's callback and `processing.observe_progress()`, not captured terminal
output. Transfers and local processing share context-local operation events.
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
`var/sources/`.
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
names. This is the shared extraction/processing selection: include
the files needed for conversion and any required licence notices, but do not
select unused companion files. It extracts nested disk images where needed and
rejects missing or ambiguous matches instead of collecting unrelated files.
Paths match at directory-component boundaries, including a nested archive's
enclosing extraction directories. A basename selects exactly one matching
file anywhere in that tree; it does not resolve ambiguity by taking the first
match. Existing originals are skipped only if their bytes are identical;
a different payload at the same destination fails without overwriting it.
The same complete product/edition lists filter batch conversion of originals
already on disk. No separate include/exclude list is required and originals are
not deleted. CRC completeness still requires the selected components; missing
or ambiguous requested members do not become a successful partial extraction.
See [Conversion input selection](Converter.md#conversion-input-selection).
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
without repeating a successfully collected item with the same member selection.
Server installation scopes provider calls to each selected edition and stops
when its registered components are complete. Product-wide discovery (including
the CLI without edition selectors) lets each provider consume the product's
complete family/edition query list.
Database rebuild preserves these entry fields; a CRC identifies the extracted
original, not its containing archive. A fallback query is a discovery hint,
not proof that another site currently holds the same bytes.

### Alternatives to WinWorld

Every WinWorld-backed HELP product family has concrete Archive.org item URLs
in addition to portable discovery queries. The metadata endpoints were checked
for downloadable software media, not just search-engine snippets:

| HELP family | Pinned alternative examples |
| --- | --- |
| Turbo Pascal | 4.0 compiler disk, 5.0 distribution, publisher's 5.5 archive, 7.0 |
| Turbo C/C++ | Turbo C++ 1.00's Internet Archive full floppy-set ZIP and exact WinWorld selector, Turbo C 2.01 and original Turbo C++ media |
| Turbo Assembler | Assembler installation media and combined Debugger/Profiler/Assembler disks |
| Turbo Debugger/Profiler | Debugger installation media and the combined tool disks |
| Turbo Basic | English ZIP and German original disks |
| Turbo Prolog | 1.0 extracted originals and 2.0 disks |
| Borland C++ | 3.0 disks, 3.1 ZIP and 4.52 CD |
| Borland Pascal | 7.0 original disks and German 7.00/7.01 archives |
| Sidekick | Plus original disks; independent ACRPC archives for 1.56b and 2.0 |

CRC-matching originals were extracted from representative English Basic,
Prolog 1.0, Sidekick Plus, Assembler 2.0, Debugger 2.x/Profiler, Pascal 5.5,
Turbo C 2.01, Borland C++ 3.1 and Borland Pascal 7 distributions. Their CRC
entries retain the concrete item URLs, search text/query and exact HELP members.
Turbo C++ 1.00 uses Internet Archive's format-based ZIP of all eight original
disk images so HELP.CA1 and HELP.CA2 can be assembled together. Both that ZIP
and the WinWorld archive yield TCHELP.TCH with CRC32 DBBB570E. Exact direct
archive recipes are attempted before edition release-page discovery; fallback
still observes site limits and verifies the same edition components.
Borland C++ 2.0 selects TCHELP.TCH/TCHELPW.TCH, 3.0 selects TCHELP.TCH,
3.1 selects TCHELP.TCH/WINHELP.TCH, and the framework edition selects
TVCHELP.TCH/OWLHELP.TCH. Member lists also filter stale unselected originals at
conversion. The 3.1 framework installer yields CRC32 1387BD2A and 280DB274;
registered revisions of one component are alternatives, not extra required
files. A valid existing revision is retained rather than overwritten merely
to fill another missing component. Unknown/conflicting originals still fail.

### Borland installer split ZIP containers

Parts have a common basename and suffix CA1, CA2, ... CA9, CAA, CAB, ...;
other series letters use the same ordering. Lettered parts require their first
volume; a real `MSCF` cabinet remains a cabinet even when its suffix is CAB.
The prefix before each ZIP payload is either four or five bytes:

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 1 or 2 | Little-endian volume bitmap; observed bits describe the other volumes |
| 1 or 2 | 3 | Little-endian payload offset in the assembled ZIP stream |
| 4 or 5 | remaining | This volume's ZIP payload bytes |

Determine prefix size from `PK 03 04` at offset 4 or 5 of the first volume.
Its stream offset is zero. Sort the complete contiguous part sequence, strip
the same prefix from every part and require each part's offset to equal the
assembled payload length so far. A missing/gapped/ambiguous or offset-mismatched
set is not assembled. The completed stream needs its ZIP end record and normal
archive validation. For example, WHELP1.CA1 begins `0E 00 00 00 00 50 4B 03 04`;
WHELP1.CA2 begins `0D 00 FB 83 05`, declaring offset 0583FBh (361467).
The bitmap is observed metadata, not a substitute for offset/ZIP validation.
Complete assembled streams are inspected before unrelated sample/source ZIPs.
Sidekick 1.56b/2.0 also have executable `direct` recipes from
`https://www.acrpc.net/utils/DOS-Misc/`; their extracted `SK.HLP` and `SK2.HLP`
match CRC32 `0EA517F6` and `58D27871`, respectively. They are not replaced by
similarly named Windows releases or the 1.56A edition.
This is not a claim that every language/revision is present at every provider;
metadata-only candidates still have to satisfy edition selection, extraction,
registered CRC completeness and conversion before publication.
Pinned Archive.org items use `/metadata/<identifier>` and are processed before
advanced search, so a working pin does not depend on that search API. Different
exact member selections are not deduplicated as if they were identical jobs.
Safe nested metadata paths such as `BP700/All.zip` are supported; `_jp2.zip`
manual scans and KryoFlux captures are not software input. Downloads keep
readable flattened archive names, without allowing path traversal.

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

Slunečnice's download page can expose the signed URL as an anchor or as the
JSON-compatible `softwareUrl` string in its partner-offer script. The provider
decodes that string, never executes JavaScript and never follows `partnerUrl`.
It accepts only an HTTPS URL on the same source host beneath the download page,
with nonempty `md5` and `expires` query fields. Missing/invalid links are
recoverable source unavailability, not a reason to execute site scripts.

Each provider reads only its own source-specific config from the parsed JSON
manifest. `catalog.py` contains no concrete product list.
Archive.org release detection appends a version to a product's source
directory only if its `label` does not already end in that version (for
example, `Microsoft QuickBASIC Extended 7.1` stays a single `7.1`).

`cheater_cz.py` is intentionally provider-specific: it keeps every DOS release in a
separate version folder under `var/sources/Scorpions Cheater DOS/` and copies the raw
Scorpion corpus artifacts selected by the manifest. For the earliest
releases where the corpus is embedded directly in executables, it falls back to
preserving the `.exe` files so no DOS version is silently dropped.

The same manifest also drives build-group selection and aliases in `thelp.sh`,
so adding a group does not require another shell `case` branch.

`slunecnice.py` copies the eleven Game-Cheater database files into
`var/sources/Game-Cheater/Game-Cheater 9.02/`. Build them with
`./thelp.sh build --group=game-cheater`.

The four pinned products are downloaded into `var/sources/<Product>/`, alongside
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

`thelpviewer/server/archives/core.py` is used by HELP, DOS and MIDI. It uses:

- Python ZIP decoding with full member-metadata validation and bounded reads
- `lsar -json` to detect whether a file is an extractable container and what
  format it is
- `unar` to unpack it
- `7zz` as an alternative/fallback, including FAT floppy images that `unar`
  does not recognize

Debian's `7zip` package lists RAR headers but omits the RAR decoding module.
The Docker image also installs `7zip-rar` from Debian's `non-free` component;
without it, fallback reports `Unsupported Method` on compressed RAR members.
This matters when Linux `unar` cannot finish an older solid/SFX RAR even though
its initial entries extract correctly. Existing deployments must rebuild the
Docker image to install the decoder; restarting an old image is insufficient.
The shared fallback applies to HELP, DOS and MIDI, not a filename-specific rule.
Tool failures retain a bounded trailing diagnostic without terminal control
characters, so a long successful-entry listing cannot hide the actual error.

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
5. return files and byte counts to the domain consumer; HELP ingestion
   separately selects and collects final source files

The archive API raises `ExtractionError` with a decoding/tool diagnostic;
`UnsafeArchiveError` is a fatal policy failure, never a reason to bypass
checks through another source. All ZIP members are checked, including
unselected ones. Absolute/parent paths, symbolic links, duplicate ZIP file
names, expanded-size/file quotas and encrypted entries are rejected.
External extraction has a timeout and monitored output-size quota. Recursive
extraction has an explicit depth budget. Program-section listings (PE/ELF)
are not nested archives; self-extracting ZIPs remain archive inputs.
OLE/CFBF compound documents are identified by the eight-byte signature
`D0 CF 11 E0 A1 B1 1A E1` before any archive-member listing, regardless of their
filename/extension. They remain unchanged leaf files during recursion; OLE
streams such as `\x01CompObj` are document internals, not filesystem members
([Microsoft's CompObjStream specification](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-oleds/142e0420-2f74-4ed9-829b-0b3d5a684d01)).
Passing a compound document as the archive itself raises `ExtractionError`,
allowing a provider to try another archive. Control characters remain forbidden
in real archive member paths, including unselected entries.
Extraction destinations must be empty, disposable staging directories.

`archives/containers.py` owns split streams and Microsoft compression;
`archives/nested.py` owns recursion and accepts caller-defined leaf selection.
The common archive layer has no reader, manifest or HTTP dependencies.
Exact-member ingestion indexes component-aligned paths once and stops
descending into a container after its requested members are available. It still
checks sibling containers for ambiguity. Existing requested members do not cause
unrelated compressed programs on a CD to be expanded.

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

HELP ingestion, DOS recipes and MIDI album processing use the shared primitives,
retaining distinct output validation and quotas. New cache files publish only
after processing accepts them; cached inputs are processed again on reuse.
Failure preserves an existing cache and published content. Atomic writes use
`server/file_storage.py`, also used for UHF, server JSON and decoded MIDI.

## Shared Helpers

| Module | Purpose |
|--------|---------|
| `http.py` | HTTP fetch/download helpers and anchor parsing |
| `converter/sources.py` | language detection, CRC-aware HELP collection into `var/sources/` |
| `converter/ingest.py` | source-plan member selection and HELP ingestion |
| `archives/core.py` | bounded ZIP reads and archive/image extraction |
| `archives/containers.py`, `archives/nested.py` | split/compressed payloads and recursion |
| `processing.py`, `file_storage.py` | operation events/policy errors and atomic publication |
| `jobs.py` | durable job intent, processing progress and verified restart checkpoints |

## Requirements

- Python 3.10+
- `unar` and `lsar`, or `7zz`, on PATH
- Python dependencies from `requirements.txt` (including `pylibmspack` for KWAJ)

Install:

- macOS: `brew install unar sevenzip` (7-Zip is needed for FAT disk images)
- Linux: `sudo apt install unar`

## Output

Collected help files are copied into `var/sources/<Product Label ...>/`.
Those directories are then consumed by `python -m thelpviewer.server.converter` / `./thelp.sh build`.
