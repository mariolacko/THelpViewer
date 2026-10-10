# Server Content

> Updated: 2026-10-10 — 2.1 development

Server Configuration → HELP / DOS packages selects content from the existing
HELP and DOS manifests. Click or Space toggles a row; arrows only move focus.
An asterisk marks installed content. Install requires confirmation. Closing
setup changes nothing; Hide on progress leaves the server job running.

## First run and permissions

On a fresh server the dialog opens after an administrator signs in, including
the opt-in localhost development admin. Registration/bootstrap Passkey setup
comes first. Anonymous users and members cannot read or change these settings.
Nothing is downloaded just by visiting the page or opening configuration.
Initial selections are empty. An intentionally empty confirmed selection
completes setup without installing anything.

Existing HELP/DOS installations do not trigger first-run setup. Their installed
groups/packages initially appear selected. Preferences are saved atomically in
`data/content-settings.json`, separately from server quota settings. A failed
or interrupted initial job keeps its selection and requires explicit retry;
restart does not silently resume network work. Progress itself is in memory,
so one Uvicorn worker is required. Do not enable multiple processes until
cross-process job scheduling and publication locks are implemented.

## Data locations

| Location | Content | Retention |
| --- | --- | --- |
| `data/sources/<Product>/` | Original HELP and required licence files | Permanent; may not be available upstream later |
| `data/helps/<Product>/` | Published gzip UHF bundles and catalog | Permanent publication |
| `data/docs/` | Published documentation and additional/edited documents | Permanent |
| `var/downloads/help/` | Downloaded HELP archives | Reusable cache, not a user disk |
| `var/downloads/dos/` | Downloaded DOS packages | Reusable cache, never cleared by a base rebuild |
| `var/dos/c/` | Shared generated DOS C | Recoverable rebuild; not private data |
| `data/dos/users/<account-id>/` | Overlay revisions, deletion records and media | Permanent; back up independently |
| `var/midi/` | Tracks, covers and catalog | Recoverable MIDI rebuild |
| `data/accounts.sqlite3`, `data/statistics.sqlite3` | Accounts/sessions and aggregate statistics/Hall of Fame | Permanent; include in backups |
| `var/global-search.sqlite3` | Full-text HELP/Docs and public-index metadata | Rebuildable index |
| `data/server-settings.json`, `data/content-settings.json` | Quotas and installation selections | Permanent configuration |

URLs remain `/helps/...`, `/?file=...&topic=...` and `/?doc=...` despite the
physical move. `THELP_DATA_DIR` selects the permanent root; `THELP_STATE_DIR`
selects generated/runtime state. `THELP_HELPS_DIR`, `THELP_SOURCES_DIR`,
`THELP_DOCS_DIR` and `THELP_DOWNLOADS_DIR` still permit explicit overrides.
When using a custom legacy state location, set THELP_DATA_DIR explicitly.
Docker configures `/app/data` and `/app/var`; both survive container replacement.

## Upgrade migration

Stop the old server/container before upgrading. Startup (and the existing
build adapter) migrates legacy root helps/sources, accounts including Passkey
credentials/sessions and the registration-token encryption key, statistics,
configuration and private DOS files/media. It separately relocates the
generated disk to `var/dos/c`, its receipt to `var/dos/installed.json`, and old
DOS downloads to `var/downloads/dos`. MIDI tracks remain in `var/midi`.

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
Old root `downloads/` is left as a legacy cache for explicit maintenance use.
Never clean all of `var/` blindly; rebuild scopes and private data are separate.

## Module and API flow

Versioned application configuration lives together in `thelpviewer/config/`:
`help-database.json`, `dos-prompt.json` and `midi-sources.json`. Environment
overrides (`THELP_HELP_DATABASE_PATH`, `THELP_DOS_CONFIG_PATH` and
`THELP_MIDI_SOURCES_PATH`) still select explicit files. Update any override
that pointed at a removed old default. `.env` and Docker Compose remain at
the project root; settings edited in the browser remain under `data/`.

`thelpviewer/server/content.py` schedules one background installation at a time:

1. Validate stable manifest group/package IDs, persist the explicit selection.
2. `server/downloader/service.py` invokes the existing HELP providers; transport
   reports byte progress per task without redirecting process-wide stdout.
3. `server/converter/build.py` converts selected source paths through the existing
   readers/writers, retaining product paths, metadata and CRC behavior.
4. Validate every produced bundle, rebuild the full staged catalog, rename
   the completed generation into place and retain the prior generation as
   `.helps-previous-<id>` beside the published directory. The backup is kept
   on the same filesystem for rename/rollback; repeated builds consume space.
5. Refresh catalog display names and trigger the incremental search/SEO index.
6. Install selected DOS packages without overwriting existing shared files
   or private overlays. Newly selected disabled manifest entries are explicit
   opt-ins. An existing shared file conflict fails rather than replacing it.

Unselected content is **not uninstalled**. HELP activation and DOS installation
are separate operations, not one transaction: a DOS failure does not undo a
successful HELP publication. DOS installation retains per-package markers for
retry, but is not a whole-disk transaction. Save/close the current browser DOS
window first; DOS sessions in other tabs need restart after shared C changes.

GET `/api/admin/content` returns choices, installed markers, saved selection,
first-run flags and job status. POST takes only `help_groups` and
`dos_packages` arrays and returns HTTP 202. GET `/api/admin/content/status`
reports state, phase, percent, processed/total, file, received bytes, errors,
warnings and the retained HELP backup. Concurrent starts return 409.
All endpoints require an admin session, host/same-origin checks and, for
writes, the configured Origin. URLs, executable commands and filesystem paths
cannot be supplied through this API.

Percentages measure phases and checked/converted units, with byte progress
when Content-Length is known; they are not an estimated completion time.
Search indexing continues independently and exposes its own progress API.

HELP and DOS share public-network HTTP transport, chunk/size limits, redirect
validation and actual-peer private-address rejection. Legacy HELP providers
may use public HTTP; DOS sources and their POST/redirect chain require HTTPS.
The shared archive extractor still uses installed unar/lsar or 7zz binaries:
this is archive extraction, not a server terminal or an arbitrary command API.
Existing downloader/converter CLI adapters remain for maintenance and tests.
