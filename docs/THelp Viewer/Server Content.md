# Server Content

> Updated: 2026-10-17 — 2.1 development

HELP, DOS and MIDI share queued HTTP transfer, staged cache publication,
`processing.py` progress events, `file_storage.py` atomic writes and
`archives/` ZIP/tool/image/split-container handling. Providers discover source
plans; domain processors still own HELP conversion, DOS extraction recipes and
MIDI/cover validation. No generic converter pretends these outputs are the same.
Safety failures stop fallback; missing/corrupt content retains a concrete
diagnostic. New raw archives publish to cache only after processing accepts them.

Server Configuration also offers **Clear cache**. After explicit confirmation,
the administrator-only `POST /api/admin/cache/clear` removes the raw HELP/DOS/MIDI
download scope contents, including abandoned transfer staging, **and all HELP
originals/licence files in the configured sources directory** (default
`var/sources/`). It reports the combined file count and logical bytes removed.
The confirmation warns that manually supplied/unavailable originals may not
be downloadable again; the action makes no new recovery copy. Running/queued downloads, processing or
retries return HTTP 409; maintenance holds the shared downloader lock so new
writers cannot start during deletion. Linked/special files and directory
overlaps with permanent or installed content are rejected before deleting any
scope. This does not change package selections or remove installed software,
UHF, indexes, music/covers, private files, settings or backups. Source/download
scope roots remain as empty directories. The next operation fetches removed
archives/originals again only if it needs them and their sources remain available.
**Cache lifetime (days)** in Server Configuration also enables automatic
expiry: `download_cache_days` is an integer from 1 to 3650, default **30**.
It is persisted with other server settings in `data/server-settings.json`.
The server sweeps at startup and hourly; running/queued transfers, extraction,
conversion and retries defer that sweep. The boundary is the last successful
download or cache reuse, recorded in file mtime rather than filesystem atime.
Expiry removes raw-cache files/metadata and HELP originals/licences under
`var/sources/`, plus empty folders. Successful ingestion/reuse and server
conversion refresh HELP input mtime; scans and failed conversion do not.
Old file mtimes are not reset automatically when upgrading. Archive any manual
or unavailable originals before enabling this policy. Shortening the lifetime applies at the next idle sweep, not while
saving settings. This is deletion, not backup; needed inputs are downloaded
again if available. Published HELP, installed DOS/MIDI, accounts, settings, private
files and recovery copies remain outside the expiration scopes.
MIDI raw inputs use `var/downloads/midi/`; playable tracks and covers stay in
`var/midi/`. Extracted/manual HELP originals and licence notices are retained in
`var/sources/`; private user data and published HELP/Docs stay in `data/`.
HELP validates every generated bundle and stages a catalog for each completed
edition before activating it. A failed edition never replaces live content or
undoes successful siblings; published editions appear immediately in Help Files.

Admin → Configuration → HELP Packages, DOS Packages and MIDI Sources are
three independent windows (`TVHelpPackagesDialog`, `TVDosPackagesDialog`,
`TVMidiSourcesDialog`) derived from `TVPackagesDialog`. There is no mode
selector. The shared base builds each window's TVListBox of groups/sources on
the left and TVCheckBoxes of editions/packages/albums on the right.
HELP groups use the same product names as Help Files, including a single
Microsoft QuickBASIC group containing 4.5 and 7.1. Versions come from verified
manifest CRC entries, explicit product `versions` for non-CRC databases, and
published catalog metadata. A version without a suffix is still a concrete
edition, not a wildcard for all product releases.
Non-CRC version IDs must match their actual source/publication metadata,
including edition qualifiers. For example, Scorpions Cheater 6–8 use their
existing `6 _shareware_`, `7 _shareware_`, `8 _shareware_` identities; separate
plain-number choices would describe nonexistent additional editions.

The description box follows the highlighted row. HELP product descriptions come
from `products[].description` in help-database.json, with optional exact-version
overrides in `products[].version_descriptions` (a version-to-text mapping).
Unknown editions use the product description. DOS descriptions come from
the package's `description` in dos-prompt.json. MIDI additionally has Enable
source and Load albums. The three introductory text rows are omitted; all
HELP/DOS dialogs are 82×24 / 90×24 cells and MIDI is 94×24. Description starts at row
14, one row below the group checkbox, and contains only the explanatory text,
not a duplicate title/installation label. The HELP/DOS Groups pane extends to
the checkbox's bottom row. Restoring geometry calls `changeBounds`, resizing
owned controls through `growMode`/`calcBounds` rather than only stretching the
DOM frame. All layouts use owned TVision
views and TVEvent commands/broadcasts, with no dialog-specific HTML or CSS.
DOS Groups is one column wider; category icons use TVListBox's shared fixed
icon column, also used by Server Statistics, rather than spaces or per-dialog
markup to compensate for emoji widths.
Checkbox colors fill the whole pane; arrows, wheel and standard scrollbars
move through it. An asterisk marks actually published installations, not merely
requested downloads. DOS rows are plain checkbox labels: JS pads names and
installed markers with spaces before a common language-flag column. The flag
scrolls with its text; no annotation markup, sticky positioning or special CSS
is used. Short manifest titles fit the default pane in full. Hidden
clusters remain hidden after redraw and cannot cover a neighbouring list.
Reopening reads the current catalog and DOS receipt. Saved selections alone
never replay old work; explicit queued/interrupted jobs resume from the journal,
while terminal failures require Retry or Apply.
HELP/DOS IDs removed from the manifest are omitted from saved intent; they cannot
break lazy DOS startup or unrelated HELP changes. Explicit requests containing
unknown IDs still fail validation. Reading settings deletes no installed files.
DOS sources marked `"required": true` are always selected and their checkboxes
are disabled. Currently these are UTILS and Volkov Commander. Category/global
Deselect All clears optional packages only; a required-only group has no
editable group toggle. API requests omitting required IDs are normalized to
include them, as are saved intent, direct disk configuration and rebuilds.
The installed asterisk requires a matching live recipe receipt and owned files,
not merely the required flag or a temporary staging receipt.
Required DOS packages have queue priority 0 ahead of ordinary priority 10 work;
urgent MIDI playback retains its reserved negative-priority lane. On opening
DOS, a missing required receipt or owned file triggers required-only preparation,
not installation of every optional saved selection. The DOS session and boot
bundle remain unavailable until that preparation succeeds; failures cannot launch
jsDOS with an incomplete required environment.

Switching group or active window preserves each dialog's unsaved draft. The
Select / Deselect All checkbox below the right pane affects only that group or
MIDI provider. It follows the visible selection and is disabled for an empty
HELP/DOS group. The bottom Select All / Deselect All buttons affect **every
group of that dialog**, including hidden groups, and remain available in an
empty category when other packages exist. MIDI global selection also
enables/disables every provider; selecting all albums includes future ones.
Apply submits **all groups of the current type** directly, without an additional
selection-confirmation dialog, including hidden groups, but changes no other
type. Closing the choices before Apply writes nothing. Refresh explicitly discards the current type's
draft and reloads server choices. A successful background job refreshes real
installation flags while retaining subsequent edits. The window is modeless.
Separate rebuild/delete confirmations remain modal. There is no bottom
status row: descriptions belong above the common action row, progress belongs
to Downloads, and errors/warnings use shared MessageBoxes. DOS changes save and
close the current DOS Prompt first; other browser sessions need restart.
A missing/invalid category or package API response disables Apply rather than
interpreting missing data as an intentional uninstall. Pure uninstallation
requires no upstream archive requests. HTTP 429 retries expose the bounded wait
and package name. HELP uses one queue row per edition, trying the configured
providers as alternatives. An exhausted rate-limited site is deferred for that
job, including its mirrors/subdomains, while other sites remain eligible.
Complete canonical originals are CRC-verified before stopping fallback;
incomplete registered sets prevent publication. Source diagnostics remain
warnings after successful fallback, not a falsely failed installed package.
HELP rows remain active while staged conversion and publication run; downloading
originals does not move them to Completed downloads. Their conversion phase uses
35–95% and only successful publication marks 100%. A conversion failure is
attached to the same edition. A later DOS failure does not retroactively mark
already published HELP as failed. Whole-library checking/publication events
do not start or advance each edition's conversion. If one edition aborts a
HELP batch, only the actual failed edition is Failed; other unfinished
editions are blocked/Not published, not failed downloads. An unattributed
transaction failure has one Operation error. Previously published HELP stays
live until that edition's generation succeeds. Progress records are separate
components of the shared downloader; HELP/DOS/MIDI keep domain validation.
Explicit Retry rechecks that edition's alternatives without changing other
products/selections. Do not interrupt running jobs to update the server without
approval. Explicit queued/interrupted jobs and progress survive restart in the
job journal; terminal failures still require Retry/Apply.

Downloads stays compact initially: at most 64 columns, with no reserved filename
row when none is shown and no empty footer below the button shadows.
Apply and the download menu's Show Downloads
command reuse one nonmodal `TVProgressDialog` managed by `TVDownloadProgress`.
More/Less expands/collapses its green TVListBox, fed by the same `/api/downloads`
snapshot as the menu: HELP products, DOS packages and MIDI albums. Rows show
stage symbols (`↓` transfer, `▣` extraction, `⚙` processing), known phase-local
percentages and `!` for failure. Unknown totals show only the symbol; changing
phase never retains the preceding transfer's percentage. The caption can show
concurrent stages together and becomes `✓` only after full success.
The main gauge retains the separate overall batch/operation percentage.
Completed rows immediately leave this list and
remain accessible in the menu's Completed downloads submenu. The selection
follows its item when earlier rows finish. Hide is on the left and More/Less on
the right; when no unfinished rows remain, the details pane collapses and Hide
is centered. Download completion
is not proof that conversion/publication finished: a followed content job supplies
its own overall phase/percent through `setOperation`, without losing the shared
queue. Archive counters distinguish newly downloaded files from cache reuse and
actual transferred bytes. The dialog remains available after completion; Hide
or `[ ]` hides it without cancelling server work.

Apply is disabled only while loading/validating configuration or submitting a
change, not throughout background download retries. While its own content type
is installing or queued, clicking Apply reopens Downloads without submitting
another job. HELP and DOS requests of the other type are accepted during a run;
their rows appear immediately in the shared queue. Disjoint HELP and DOS jobs
start independently, including after restart; a combined request also runs
its HELP and DOS parts concurrently. Each job owns its progress, journal ID
and checkpoints, so neither task can overwrite the other's state or receipt.
Requests touching the same content type retain their order; new overlapping
requests are rejected. HELP publication stays single-writer, as do shared-DOS
disk transactions, without serializing these unrelated destinations. An error
in one type does not cancel the other. Edited drafts of the busy type
can be applied after the job finishes. Switching categories and
the completion refresh keep that draft. Server/network errors release the monitor
and restore Apply for valid configuration. Invalid/unavailable configuration still
requires a successful Refresh. Rebuild/delete confirmations enter the same desktop
dialog stack as package windows, rather than relying on a fixed CSS z-index.

Within an installation, up to three package inputs are prepared concurrently.
Bounded preparation drivers are separate from both the global HTTP workers and
the three shared local-processing workers. Waiting for a busy remote site must
not occupy the extraction pool or prevent another content type submitting work.
HELP looks ahead through the selected input plans for another initial source,
using edition URLs/provider identity as advisory hints; real requests still
enforce the actual site's limit, including redirects and fallback. DOS can
prepare later independent inputs ahead but always installs in manifest order.
Local extraction does not occupy an HTTP worker
or hold a site's download lane, so the next archive can transfer immediately.
HELP sends ready edition IDs to one converter while other inputs continue.
Each edition gets an independently validated/staged publication, preserving
already published siblings. A later download/conversion failure discards only
that disposable stage, not successful editions or private data. Unchecked
editions are removed after requested additions succeed. DOS consumes prepared packages and runs post-install scripts in manifest
order, retaining dependencies such as UTILS. MIDI albums use the same bounded
queue with a separate urgent lane for playback. Failure/shutdown joins active
writers and cancels pending owned steps rather than leaving orphan installers.

The live Downloads menu beside the account/clock uses one shared online queue
for HELP, DOS and MIDI. It groups MIDI by source/album and replaces the player's
separate automatic download dialog. Its normal TVMenuBox supports scrolling
and live percentage/retry updates. Closing it does not cancel work. Anonymous
users see MIDI only; administrator sessions also see package work. Queue progress
is a runtime snapshot, not proof of HELP conversion/publication. ZIP member
counts can grow after extraction. See Downloader for the common pipeline/API.
Missing music requested in the player gets a per-track row at the front and uses
the shared downloader's one urgent lane, even during an active package transfer.
Waiting requests for the same track are promoted, not duplicated. Regular packages
share at most three regular source lanes; each source permits one transfer,
including urgent playback. Completed playback rows move to Completed downloads.

## HTTP response compression

`compression.py` applies one ASGI policy across the viewer, API and static
mounts. Starlette performs streaming gzip (level 5, minimum 1024 bytes), with
large chunks compressed off the event loop. HTML, JSON/catalogs, JS, CSS, XML,
Markdown, WebAssembly, raw MIDI and DOS chunks all use this policy; individual
routes do not compress their own responses. Clients decode HTTP gzip normally,
without application changes. The direct Starlette dependency is at least 1.8
for its MIME exclusions, partial-response protection and off-thread compression.

Negotiation follows [Accept-Encoding](https://www.rfc-editor.org/rfc/rfc9110.html#section-12.5.3):
coding names are case-insensitive; an explicit `gzip;q=0` overrides `*`.
Absent/empty headers conservatively select identity; unsupported encodings and
malformed/zero gzip weights do not enable gzip. `Vary: Accept-Encoding` separates
eligible compressed/identity cache variants, retaining existing Vary values.
Compression updates/removes Content-Length as appropriate and weakens strong
ETags when gzip changes the bytes. FileResponse uses chunks rather than
zero-copy pathsend when gzip is negotiated; files are not read wholly into RAM.

HEAD, byte-range/206 responses, SSE, existing Content-Encoding, compressed
archives/UHF `.json.gz`, SF3, compressed audio/video, WOFF and compressed images
are not recompressed. Raw UHF remains gzip *file data*, not HTTP Content-Encoding,
because its decoder explicitly expands it. The precompressed SoundFont keeps
its Brotli sidecar, cache policy and shared encoding negotiation. Response
`Cache-Control: no-transform` is respected. Account/registration-token APIs,
administrator user/invitation responses and any Set-Cookie response are excluded
to avoid compressing secrets with caller-controlled text. This does not add
compressed request-body support or change stored files/download-cache formats.

## Server module boundaries

`app.py` constructs services, connects their shared dependencies and registers
HTTP routers. `routes/` remains the HTTP layer: request validation, authentication,
response status and serialization.

The session/role/same-origin guard for administrator HTTP endpoints lives in
`routes/authorization.py`, shared by content, downloads, settings and rebuild
routes. Account persistence and role data remain in `accounts/`.

Feature logic is grouped by responsibility:

`content_config.read_source_manifest()` is shared by DOS and MIDI: it reads the
versioned JSON and validates the object, source list and unique bounded IDs.
DOS-specific category/boot rules live in `dos/config.py`, used equally by
package choices, installation and rebuild. MIDI keeps its provider/album/HTML
rules; HELP keeps its existing typed manifest/CRC loader. These are not folded
into an inheritance chain. `json_storage.write_json()` handles atomic settings
and migration-metadata publication with flush/fsync, replacement, symlink
rejection and temporary-file cleanup on failure. HELP/DOS intent, MIDI selection
and quota settings share this writer but retain their separate data files.

- `accounts/`: account/schema management (`store.py`), registration tokens and
  invitations (`registration.py`), named WebAuthn credentials (`passkeys.py`),
  optional password validation/hash/throttling (`passwords.py`) and sessions
  (`sessions.py`). See [Accounts](Accounts.md) for authentication and migration rules.
- `dos/`: shared disk/boot coordination (`store.py`), bounded package extraction
  (`packages.py`), isolated BAT execution (`post_install.py`), private snapshots
  (`overlay.py`), removable media (`media.py`) and shared path guards (`paths.py`).
- `midi/`: selection/background playback-download coordination (`library.py`),
  manifest/HTML extraction (`sources.py`), SQLite catalog and covers (`catalog.py`),
  and bounded Standard MIDI/container decoding (`format.py`).
- `downloader/` and `converter/`: the existing shared transport/queue and HELP
  conversion modules, not separate copies inside each feature.

The main stores are explicit coordinating APIs, not dynamic method forwarding or
mixin chains. Small configuration, storage, search and statistics modules remain
at the server root. Moving Python code does not move permanent data, change API
URLs or rebuild installed content. All consumers use the new module paths;
the removed flat modules have no compatibility shims.

## First run and permissions

On a fresh server HELP Packages opens after an administrator signs in, including
the opt-in localhost development admin. Registration/bootstrap Passkey setup
comes first. Anonymous users and members cannot read or change these settings.
No HELP/DOS package is downloaded just by visiting or opening configuration.
Initial HELP selection is empty; DOS starts with its manifest-required packages
checked. Applying empty HELP selection completes fresh setup without installing DOS.
Applying empty DOS selection installs/retains required packages and removes optional
ones. Other types stay unchanged. Opening settings alone starts no download.
First-run setup uses the same per-type Apply flow.

Existing HELP/DOS installations do not trigger first-run setup. Their installed
products/packages initially appear selected. An interrupted job does not turn
existing installed content into a fresh server. Later reconfiguration retains
the completed setup flag while running and on failure; job status, not that
flag, reports whether the requested installation succeeded. HELP requests contain
edition IDs, not vendor/build-group aliases.
Preferences are saved atomically in
`data/content-settings.json`, separately from server quota settings. This file
is intent, not proof of installation or a durable work queue. The job journal
below distinguishes interrupted work from terminal failures. One Uvicorn worker
is required; a second process is refused by the journal's OS ownership lock.

### Durable jobs and restart recovery

`data/jobs.sqlite3` is permanent operational state, separate from accounts,
statistics, generated MIDI catalogs and the rebuildable full-text index. It uses
short FULL-synchronous SQLite transactions, foreign keys and a single application
owner (`jobs.lock`, automatically released by the OS after process death).
Do not open a live production database through a network share. Back it up using
SQLite's backup API or with the server stopped, retaining journal sidecars.

- `jobs`: ordered IDs, domain/payload (manifest selections, never Python
  callables), queued/running/interrupted/done/error state, attempt count,
  last progress/error and timestamps.
- `job_steps`: completed/failed source checkpoints and publication recovery
  details. Published HELP checkpoints contain relative paths and SHA-256 values.
- `queue_jobs`/`queue_items`: latest HELP/DOS/MIDI queue states, phases, known
  phase percentages and errors. Progress updates persist at changed integer
  percentages/phases, not for every received byte. Remove really removes the
  stored queue row; it does not delete content or retry it on the next startup.

Startup claims journal ownership, changes abandoned running jobs to interrupted,
recovers any journaled HELP rename gap, then queues unfinished explicit content
requests, retaining original order for overlapping content types while starting
independent HELP/DOS jobs together. Removed/unknown manifest IDs fail visibly;
the server never broadens the saved request. Reserve work before cache expiry
and before starting the index. A saved selection predating this journal is not
automatically replayed: its previous attempt may have intentionally failed.

Failed or blocked ("Not started") queue rows remain actionable through Retry
and Remove, even if the original failure was removed. Explicit DOS Retry
preserves the live installation and continues all saved selected additions:
one failed disk transaction can leave many later packages uninstalled. Its full
target is journaled before starting; pending removals still require Apply.
Obsolete unselected DOS queue rows are discarded and successful installs clear
their stale errors. No terminal failure is retried merely by restarting.

DOS packages stay visible as Awaiting publication until both the new common C
generation and its receipt are published. If the transaction rolls back,
unpublished packages become Not completed rather than entering Completed downloads;
the actual failure remains visible. Startup reconciles persisted completion rows
against live receipts and regular owned files, without retrying terminal failures.
The common software library has no aggregate capacity/file-count quota. Private
overlay capacity and file limits, archive safety bounds and host disk errors
remain independent of the common library size.

HELP rechecks published catalog/files plus checkpoint hashes; missing/changed
outputs are rebuilt, not trusted as installed. Each verified edition is converted
and published independently; browsers observe the public catalog revision in
`GET /api/downloads` and refresh Help Files while the job is still running.
Completed units are skipped after restart, including a crash after publication
but before its job was marked done. A journaled crash between the live-to-backup
and stage-to-live renames restores the previous generation before recovery.
Only the exact owned staging path recorded in that checkpoint is discarded;
unrelated/pre-journal staging trees are not adopted or removed automatically.

Restarting a download means reusing a checksum/domain-validated cached archive
or canonical originals, **not arbitrary HTTP byte-range continuation**. An
unfinished transfer/extraction/current edition is repeated from its last safe
artifact boundary. Partial files and saved percentages are never marked complete.
DOS replays its selected disk transaction using validated caches/receipts;
private overlays are outside it. MIDI already resumes missing, non-failed tracks
from its own catalog and now uses the same durable processing progress store.
Explicit terminal content/MIDI failures are not automatically retried forever.

Global index jobs use the same journal for intent/progress and per-source
fingerprint checkpoints. Indexed rows and their fingerprints commit together in
`var/global-search.sqlite3`; this database remains the authoritative incremental
checkpoint even if a process dies before recording its journal step. Restart
skips already committed, unchanged inputs and rolls back incomplete SQLite
transactions. Unchanged corrupt-file failures survive restart; a changed input
becomes eligible again. HELP suspension/shutdown yields at a source boundary,
and the index starts only after recovered HELP writers release the guard.

On graceful shutdown the server stops the index, signals/drains content work,
then stops MIDI/shared transfers before releasing ownership. Interrupted work
keeps its durable job, rather than being converted into a terminal failure.
Forced process termination needs no shutdown hook: SQLite and artifact validation
provide the same safe-unit recovery on the next startup.

## Data locations

| Location | Content | Retention |
| --- | --- | --- |
| `var/sources/<Product>/` | Extracted/manual original HELP and required licence files | Expires after the cache lifetime (default 30 days since use); Clear cache deletes all inputs; uninstall/rebuild retain them |
| `data/helps/<Product>/` | Published gzip UHF bundles and catalog | Permanent publication |
| `data/docs/` | Published documentation and additional/edited documents | Permanent |
| `var/downloads/help/` | Downloaded HELP archives | Reusable cache, not a user disk |
| `var/downloads/midi/` | Validated raw MIDI tracks/album archives | Reusable cache; decoded music/covers remain in `var/midi/` |
| `var/downloads/dos/<package-id>/` | Readable DOS archives and source/checksum sidecars | Reusable cache with configurable idle expiry, not removed by a base rebuild |
| `var/dos/c/` | Shared generated DOS C | Recoverable rebuild; not private data |
| `data/dos/users/<account-id>/` | Overlay revisions, deletion records and media | Permanent; back up independently |
| `var/midi/` | Tracks, covers and catalog | Recoverable MIDI rebuild |
| `data/accounts.sqlite3`, `data/statistics.sqlite3` | Accounts/sessions and aggregate statistics/Hall of Fame | Permanent; include in backups |
| `var/global-search.sqlite3` | Full-text HELP/Docs and public-index metadata | Rebuildable index |
| `data/server-settings.json`, `data/content-settings.json`, `data/midi-settings.json` | Quotas, installation selections and MIDI providers | Permanent configuration |

URLs remain `/helps/...`, `/?file=...&topic=...` and `/?doc=...` despite the
physical move. `THELP_DATA_DIR` selects the permanent root; `THELP_STATE_DIR`
selects generated/runtime state. `THELP_HELPS_DIR`, `THELP_SOURCES_DIR`,
`THELP_DOCS_DIR` and `THELP_DOWNLOADS_DIR` still permit explicit overrides.
The default originals directory is `THELP_STATE_DIR/sources`, independent of
`THELP_DATA_DIR`. Uninstall and rebuild keep originals. Automatic cache expiry
removes unused inputs after the configured lifetime; explicit administrator
Clear cache removes all of them after confirmation.
When using a custom legacy state location, set THELP_DATA_DIR explicitly.
Docker configures `/app/data` and `/app/var`; both survive container replacement.
DOS cache migration verifies known old flat entries against readable
destinations, retains their mtime, and removes old paths only after every copy
is verified. Entries no longer identifiable from the manifest are retained for
expiry, not assigned guessed software names or used through legacy aliases.

### Docker runtime dependencies

HELP archive extraction requires `unar` with `lsar`, or `7zz`/`7z`; DOS package
post-install BAT scripts require `dosbox`. The Dockerfile installs these tools
and checks their executable availability during the build. Updating bind-mounted
Python files or restarting/recreating a container does not replace an old image.
After Dockerfile/dependency changes, build the image explicitly and recreate the
service with `docker compose build viewer` followed by
`docker compose up -d --force-recreate viewer` from the deployment directory.
Verify tools in the resulting container with
`docker compose exec -T viewer sh -c '(command -v 7zz || command -v 7z) && command -v unar && command -v lsar && command -v dosbox'`
and run an actual extraction before declaring the installation ready. A GUI's
successful container start alone is not evidence that the image was rebuilt.

### macOS cloud-backed storage

An iCloud-backed Documents checkout may contain `dataless` placeholders:
their filenames and sizes exist, but bytes are not physically on the Mac.
Docker Desktop's Linux bind mount cannot trigger the host's cloud download.
Consequently local auto-login can fail with SQLite `disk I/O error`, while
DOS preparation fails with `[Errno 5] Input/output error` even though both
files appear in Finder. A MIDI cover can likewise be listed in the catalog and
return HTTP 200 headers, then fail during the image body read with the same
I/O error. The browser receives an incomplete image, not a missing catalog
entry. None of these errors proves damaged data or calls for rebuilding it.

`./thelp.sh docker start` / `./thelp.sh docker restart` first read the current
HELP tree, permanent root metadata (including accounts/settings and SQLite
sidecars), the separate development account store, private DOS overlays/media
and `var/dos/` plus `var/midi/` (tracks, covers, catalog and SQLite sidecars)
through the host filesystem. This materializes existing bytes
at their original paths; it does not copy/reset databases, rebuild C, change
account IDs, pin folders or remove caches. A read failure stops before Docker
Compose changes the container. Empty first-run HELP storage does not bypass
the account/DOS/MIDI checks. Downloads and migration/rebuild backups are excluded.

Plain `docker compose start/restart/up` does not run this preflight. If a
running checkout has been offloaded, stop its container before materializing
database files and restarting. Keep database WAL/journal sidecars with their
database; do not delete them to resolve an I/O error. Individual generated
cover files can be read on the host while the server stays running; database
recovery requires stopping its writer. Reload the web page after recovery so
session/DOS startup and image requests run again. Without
Finder's optional Keep Downloaded setting, macOS can offload the files again;
the preflight restores availability but is not a permanent pinning policy.

## Upgrade migration

Stop the old server/container before upgrading. Startup (and the existing
build adapter) migrates legacy root helps/sources, accounts including Passkey
credentials/sessions and the registration-token encryption key, statistics,
configuration and private DOS files/media. It separately relocates the
generated disk to `var/dos/c`, its receipt to `var/dos/installed.json`, and old
DOS downloads to `var/downloads/dos`. MIDI tracks remain in `var/midi`.
Original HELP in the former `data/sources/` directory moves to `var/sources/`,
as do legacy root originals. Preflight checks all incoming trees together before
publishing any, merging only identical collisions and retaining extra files and
empty directories. Explicit `THELP_SOURCES_DIR` overrides are not relocated.

Migration verifies SHA-256 before and after publishing each copied tree.
Conflicting destination files abort before source changes; symlinks are
rejected. Identical destinations can be merged. Originals move to a unique
`data/migration-backups/<id>/` directory, not the trash. The relative-path
`data/storage-migration.json` journal makes completed transfers repeat-safe
and portable between native paths and Docker bind mounts. Account IDs and
shared disk hashes do not change. Keep the backup until the upgraded server's
login, private disks and HELP links are verified. Do not downgrade 2.1 storage
to 2.0 without restoring that snapshot and its matching configuration.

`docs/` remains version-controlled source documentation. Startup publishes
public Markdown into `data/docs` and records managed hashes; later code
updates replace only unchanged managed documents. Administrator edits and
additional documents remain untouched. RE/Audit files are not published.
The obsolete root `downloads/` is not runtime storage; it may be removed during
explicit maintenance after the original HELP sources and current cache are
verified. Active downloads remain under `var/downloads/help/` and
`var/downloads/dos/`.
Completed `data/migration-backups/`, managed generations under `var/backups/` and
duplicate `helps 2`/`helps 3` directories are recovery copies, not live content.
Remove them only after checking the active catalog/files, completed migration
and absence of running content jobs. Prefer moving them to Trash for recovery;
disk space is reclaimed only when those trashed files are permanently removed.
Retain `storage-migration.json`, `.storage-migration.lock`, databases, source
HELP, published content and private DOS storage. Temporary-looking operational
metadata is not a disposable cache.
Never clean all of `var/` blindly; rebuild scopes and private data are separate.

## Module and API flow

Versioned application configuration lives together in `thelpviewer/config/`:
`help-database.json`, `dos-prompt.json` and `midi-sources.json`. Environment
overrides (`THELP_HELP_DATABASE_PATH`, `THELP_DOS_CONFIG_PATH` and
`THELP_MIDI_SOURCES_PATH`) still select explicit files. Update any override
that pointed at a removed old default. `.env` and Docker Compose remain at
the project root; settings edited in the browser remain under `data/`.

### MIDI source and album selection

Server shutdown first sets the MIDI library's terminal stop state, waits for
its current catalog writer and urgent playback transfers, then closes the
shared downloader. MIDI transfers still waiting for a lane are cancelled, so
shutdown need not wait for an unrelated HELP/DOS transfer to release that lane;
other consumers' tasks are not cancelled. Pending rebuild/source/index
operations cannot restart a writer or archive its files after that stop.
This preserves the current
transfer's atomic file publication; shutdown may wait for its bounded network
operation to finish. Cached tracks and persistent selections are not deleted.

Startup resumes missing MIDI downloads that have no recorded failure. The catalog
checks all local members of each selected album before registering a transfer.
Already indexed pages and complete albums do not reset the shared progress batch
or enter "Downloading"; existing completed history is retained. Verified published
files also complete interrupted queue rows without repeating a transfer. Only
missing tracks, files failing the lightweight availability check or incomplete
albums enter the background pipeline.
Deselected queue rows are discarded without deleting their cached files.
The catalog persists download errors (including network errors), in addition to rejected ZIP
member diagnostics. Known failures remain visible in the library's partial/error
count but are not automatically downloaded or reinserted into the queue on restart.
Remove therefore stays removed without deleting tracks, covers or selections.
Explicit Retry, requesting a missing track for playback or applying source
selection can try again; successful processing clears the recorded download error.

Newly processed music is normalized to Standard MIDI before atomic publication.
Existing-file availability (`_is_downloaded`) only checks a regular non-linked
file of 22 bytes to 2 MiB whose first four bytes are `MThd`. It does not run the
complete decoder again. Consequently older cache entries can remain available
despite malformed headers/chunk lengths or source trailers; catalog availability
is not proof of full SMF validity or normalization. Retrospective validation and
normalization are still required; startup currently does not rewrite those files.
The payload decoder accepts raw `MThd`, RIFF/RMID `data` chunks and a counted
DOS record with a two-byte little-endian payload length followed immediately by
`MThd`. RIFF lengths are little-endian and odd-size chunks have word padding;
the declared container and every chunk must fit, with exactly one MIDI data
chunk. SMF header/track lengths are big-endian; the header, declared number of
tracks and chunk bounds are checked. Counted payload lengths must agree with
the complete SMF boundaries. Source trailers after the declared SMF are excluded
from the playable copy, not interpreted as events; source URLs/IDs do not change.
The decoder does not search arbitrary bytes for an embedded MIDI signature.
Archives allow up to 4,096 entries, 2 MiB per music file and 128 MiB of expanded
MIDI in total. Invalid payloads are rejected before replacing a cached file and
ZIP failures identify the specific member. RIFF details follow the
[Microsoft RIFF specification](https://learn.microsoft.com/en-us/windows/win32/xaudio2/resource-interchange-file-format--riff-).

ZIP members are checked independently. Rejected members retain their filename,
title and diagnostic in the catalog, but their bytes are not published as music;
valid siblings and cover art remain available, including after a restart or an
urgent playback download. Album failures summarize the rejected count and up to
three member diagnostics. A partial album stays failed rather than being counted
as cached success merely because its valid tracks exist. Retry re-fetches that
album and clears member errors only when the replacement passes validation.

Opening a partially downloaded library shows the ready-track count and number
of download errors. Detailed source/member errors belong in the shared Downloads
queue; a failed album does not make already available music unplayable. Text
files merely renamed `.mid` get an explicit plain-text source diagnostic; they
are not silently accepted or synthesized as music.

MIDI Sources has a shared TVListBox of providers on
the left and a TVCheckBoxes album selection on the right. Source arrows/clicks
only select which provider is being edited; Enable source changes its inclusion.
The unsaved draft for every source is retained while switching between them.
The checkbox below Albums selects/clears only the current provider's albums
(including future albums when selecting all), without changing provider flags.
The bottom Select All / Deselect All buttons affect every provider and its
albums, including enabling/disabling sources. Toggling a specific
album switches to an explicit set. Both lists have standard scrolling and full
normal-palette backgrounds. An album groups entries by their source-provided
game name; a missing game name falls back to the entry title. Each provider is
one row even when its manifest has multiple alphabet pages. IDs are the first
24 hexadecimal SHA-256 digits of the UTF-8 game/title, scoped to the provider.

GET `/api/admin/midi-sources` returns provider IDs/names, enabled flags,
`all_albums`, the cached album IDs/names/selected flags, whether the pages have
been indexed, and downloader status. It does not fetch remote pages or scan
every cached MIDI file. PUT requires a `sources` array of unique enabled
manifest IDs and an `albums` mapping from provider IDs to null (all albums,
including future ones) or an explicit array of album IDs. An omitted mapping
entry also means all; an empty array means none. The stored album mapping is
optional, with the same all-albums default. Unknown/duplicate IDs are rejected.
The selection is saved atomically in `data/midi-settings.json`; provider URLs,
extraction rules and file paths cannot be supplied through this API. GET status
and all writes require an administrator session; writes require exact Origin.

Load albums posts to `/api/admin/midi-sources/<provider-id>/index`. A single
background worker stops the existing downloader after its in-flight write,
indexes missing provider pages, then resumes the previously selected music.
It neither enables the provider nor downloads its unselected albums. The shared
TVProgressDialog reports this operation through the small
`/api/admin/midi-sources/status` response; polling does not retransmit the whole
album catalog. Hide hides the view, not the server operation. Cached page
identities live in the generated library.sqlite3 midi_pages table. Existing
nonempty catalogs can be reused; a page with no matching MIDI/ZIP links is an
error and is not marked complete, so it can be retried after correction.

Before a saved selection exists, the manifest's enabled flags apply; a saved
empty array means no sources. Apply saves directly and stops playback
in the current browser. Closing before Apply does not save. The old downloader stops
at a safe boundary after an in-flight request/write, then resumes using the
new selection. Cached tracks/covers/index rows remain in `var/midi`; disabled
providers and unselected albums are excluded from downloading, priority requests,
the public playlist and file/cover endpoints.
Re-enabling a source resumes from its cache. MIDI rebuild uses this same saved
source/album selection and does not reset it. Concurrent selection, indexing
and rebuild starts return 409 while a handover/index/rebuild is running.

### HELP and DOS jobs

`thelpviewer/server/content.py` schedules one background installation at a time:

1. Validate stable manifest product/package IDs, persist the explicit selection.
   This is remembered request intent for explicit Retry, not an installation
   receipt. While a job runs the chooser shows its target; reopening after a
   failure or server restart selects only products in the published HELP catalog
   and packages in the shared DOS installation receipt. Failed additions are not
   checked as installed, and failed removals leave the old content checked.
2. `server/downloader/service.py` invokes the existing HELP providers; transport
   reports byte progress per task without redirecting process-wide stdout.
3. `server/converter/build.py` converts missing selected product paths through the existing
   readers/writers, retaining product paths, metadata and CRC behavior.
   Verified CRC ownership takes priority, then manifest conversion filenames and
   known filename owners, then the product/release folder. A shared filename in
   an unrelated archive is not guessed. Thus a package containing other products'
   HELP cannot silently install those companions as the selected product.
4. For each ready edition validate its bundles, rebuild the full staged catalog
   and rename that edition's completed generation into place immediately. Keep a transient `.helps-previous-<id>`
   beside the live directory for same-filesystem rename/rollback, then move it
   to `var/backups/help/help-<id>/` after publication succeeds. A move across
   filesystems verifies SHA-256 and directories before removing the original;
   if archival fails, the sibling recovery copy is retained and logged.
   Successful archival rotates older HELP backups using the retention limit.
5. Refresh catalog display names and the browser's Help Files menu after each
   successful edition. Resume the incremental search/SEO index only
   after HELP processing and publication (or failed-job writer cleanup) finish.
6. Stage the shared DOS disk, remove exact files owned only by unchecked
   packages, install newly selected packages, and publish disk/receipt together
   with rollback on publication failure. Root configured files, files owned by
   a remaining package, untracked administrator files and private overlays/media
   stay intact. Disabled manifest entries can be explicitly selected.

Unchecked installed products/packages **are uninstalled when Apply is pressed**.
Original HELP files and cached archives are not removed. DOS records ownership
under `_files` in its installed.json receipt. Older receipt-only installations
need their cached archives to recover exact ownership; missing archives or
ambiguous modified files abort without deleting live content. Software from
unknown, removed manifest IDs is retained rather than guessed/deleted.
Previous shared DOS generations and receipts live in `var/backups/dos/dos-packages-*`.
Successful DOS package changes and base rebuilds share the DOS backup limit.

### Backup retention

Admin → Configuration → Server Configuration exposes **Retained backups per
type** (`backup_count`, integer 1–100, default **2**) alongside the private C
quota. It is persisted in `data/server-settings.json` and returned/updated by
`GET`/`PUT /api/admin/settings`; writes require an administrator and a valid
same-origin request. Existing settings files receive the new default without
changing the saved disk quota.

The limit is independent for each family: HELP (`var/backups/help/help-<id>`),
DOS (`var/backups/dos/dos-base-<id>` and `dos-packages-<id>` together), and MIDI
(`var/backups/midi/midi-<id>`). After a successful publication/rebuild, keep its
recovery copy plus the newest siblings up to the limit, deleting older copies
permanently. Lowering the setting takes effect at the next successful operation
for that family, not on saving settings. The direct HELP build API also defaults
to two and accepts explicit `backup_count` and `backup_dir` arguments. Server
calls supply `state_dir/backups/help`; a standalone build defaults to
`<helps-parent>/backups/help` unless an explicit backup directory is passed.

Startup moves old HELP sibling generations and flat DOS/MIDI backups into the
grouped tree. It rejects links/conflicts before moving anything, accepts an
identical already-copied destination and preserves empty directories. Migration
does not prune recovery copies or touch live content/private data. Exact managed
UUID names are migrated; unrelated directories remain unchanged. Atomic renames
are used on one filesystem; copied moves are verified before source removal.

Failed or partial rebuilds do not rotate backups, so their recovery copies can
temporarily exceed the limit. Cleanup failures are logged and do not undo a
successful publication. Only exact managed UUID-named directories are eligible;
symbolic links, other names, active content, private user data and caches are
not pruned. Migration uses one journal-owned archive rather than producing a
new backup on each start; it stays under explicit maintenance control. Private
DOS disk revisions retain their separate transactional recovery generation.

HELP activation and DOS configuration
are separate operations, not one transaction: a DOS failure does not undo a
successful HELP publication. Save/close the current browser DOS
window first; DOS sessions in other tabs need restart after shared C changes.

GET `/api/admin/content` returns `help_categories`, `help_packages`,
`dos_categories`, `dos_packages`, installed markers, current selection,
first-run flags and job status. HELP rows have `id`, `product`, `version`,
`category`, `label`, `group`, `description`, `installed`; categories use the
same menu product names and may combine products (QuickBASIC 4.5/7.1). HELP
IDs are `product:version`, for example `tp:5.5`, `qbx:7.1` or `helppc:`
for an unversioned manifest entry. Identifiers are opaque client values, not
paths. POST accepts `help_packages` and/or `dos_packages` arrays and returns
202. DOS rows also expose `language` and boolean `required`; the server unions
every DOS selection with the required manifest IDs before saving/applying it.
Product/vendor selections and the former `help_groups` field are not
accepted. Edition IDs are checked against manifest/catalog choices before
saving or starting work. GET `/api/admin/content/status` reports state, phase,
percent, processed/total, file, received bytes, errors, warnings and the retained
HELP backup, plus `scopes`: the active and waiting content types (`help`, `dos`).
A request for a type already active/queued returns 409; a request for the other
type returns 202 and enters the installation queue. Waiting package rows use
the same provider/edition plan as execution, not a second list inferred by the
browser. A failed job does not discard the next type's request, and final status
retains earlier errors. MIDI retains its separate server
API, called by its own dialog; the shared base does not merge persistence or
backend responsibilities.

All endpoints require an admin session, host/same-origin checks and, for
writes, the configured Origin. Omitted types retain their saved request and
are not installed/uninstalled/retried by that job. Empty arrays explicitly
uninstall the indicated type's optional managed content; required DOS packages
remain selected. Both missing/null is rejected.
The saved request is not an installation receipt; choices use published bundles
and the canonical DOS receipt, including during staged DOS changes. URLs,
executable commands and filesystem paths cannot be supplied through this API.

Percentages measure phases and checked/converted units, with byte progress
when Content-Length is known; they are not an estimated completion time.
The global HELP/Docs/SEO index yields to server HELP processing. The index's
`suspend()` context finishes the current source transaction and closes its
SQLite writer before HELP download/extraction/conversion/publication begins.
It checks pause requests between indexed files, retaining already committed
rows and their search/public-page/sitemap availability. While suspended,
`ensure_current()` and HTTP status/search/sitemap requests cannot start another
writer or rescan a changing library. Nested/concurrent suspensions release only
after their last holder exits. HELP Retry and removal use the same guard;
failure cleanup drains HELP input writers before releasing it. DOS/MIDI-only
processing does not pause the index.

When HELP work ends (success or failure), the guard automatically takes a fresh
snapshot of the published HELP/Docs and updates only changed inputs. It does not
continue an obsolete pre-publication snapshot or require a browser poll to
restart. Staged/failed generations are never indexed. The API reports
`state: "paused"`, `phase: "Waiting for HELP processing"` and retains the last
committed availability/progress. The menu shows `▤ ‖`; clicking it opens the
existing index progress dialog. The monitor polls paused work at one-second
intervals and returns to percentage progress on resume. Public pages without
an indexed entry return temporary 503 with Retry-After while paused, so delaying
indexing does not falsely declare a newly published article missing.
Public topic URLs resolve genuine numeric and symbolic source aliases using
the same context-case rules as the viewer. A `topic` request checks a real
article ID first; an explicit `alias` request checks only declared aliases,
including aliases whose spelling collides with an article ID. The two
parameters are mutually exclusive. An alias
with a destination row redirects to `/?file=...&topic=...&line=...`; an
explicit `line` remains in control. Canonical tags and sitemaps use the article
URL without a row, so aliases do not create duplicate indexed articles.
The alias lookup is part of the rebuildable search database. Its schema/index
revision upgrade rebuilds alias rows from published UHF without modifying
HELP originals, account databases or private user files.
Setup and progress use the existing managed-view statistics lifecycle: only
aggregate opens and bucketed active durations are recorded, not selections or
account details.
The bounded dialog-name list includes current account, registration, user
management, server configuration, download actions and rebuild windows.
Automatically registered `tv-view-<n>` dialogs are aggregated as `progress`,
`messagebox` or `dialog` from their shared view type. The same normalized name
is used for open and duration events; generated IDs, titles and input values
are not sent as statistics labels. Unknown arbitrary names remain rejected.

HELP provider modules and the DOS `downloader/packages.py` module share atomic
cache writes, public-network HTTP transport, chunk/size limits, redirect
validation and actual-peer private-address rejection. Legacy HELP providers
may use public HTTP; DOS sources and their POST/redirect chain require HTTPS.
The shared archive extractor still uses installed unar/lsar or 7zz binaries:
this is archive extraction, not a server terminal or an arbitrary command API.
Existing downloader/converter CLI adapters remain for maintenance and tests.

## CRC database maintenance

`python3 tools/rebuild_help_database.py` scans original HELP and merges CRC
records into `thelpviewer/config/help-database.json`. It preserves the manifest
version, providers, converters, products, build groups and unknown metadata.
Existing verified titles, paths, product/release overrides and records whose
originals are currently absent are retained; discovered filename aliases are
merged case-insensitively. New CRC records remain separated for manual review.

Malformed JSON, invalid records, duplicate CRCs or a missing sources directory
abort without changing the existing file. A complete UTF-8 JSON file is flushed
and atomically renamed into place, preserving its permissions; publication
failure leaves the old manifest intact and removes the temporary file.
Using `--output` with a nonexistent file starts from the configured complete
version-2 manifest, retaining its definitions and known CRC records. The tool
does not create or accept old version-1 CRC-only snapshots, `filename` records
or `project`-to-collection translations.
