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
`var/content-settings.json`, separately from server quota settings. A failed
or interrupted initial job keeps its selection and requires explicit retry;
restart does not silently resume network work. Progress itself is in memory,
so one Uvicorn worker is required. Do not enable multiple processes until
cross-process job scheduling and publication locks are implemented.

## Data locations

| Location | Content | Retention |
| --- | --- | --- |
| `sources/<Product>/` | Original HELP and required licence files | Keep; may not be available upstream later |
| `helps/<Product>/` | Published gzip UHF bundles and catalog | Keep; rebuildable from original sources |
| `var/downloads/help/` | Downloaded HELP archives | Reusable cache, not a user disk |
| `var/downloads/dos/` | Downloaded DOS packages | Reusable cache, never cleared by a base rebuild |
| `var/dos/base/` | Shared installed DOS C | Recoverable rebuild; not private data |
| `var/dos/users/<account-id>/` | Overlay revisions, deletion records and media | Permanent; back up independently |
| `var/midi/` | Tracks, covers and catalog | Recoverable MIDI rebuild |
| `var/accounts.sqlite3`, `var/statistics.sqlite3` | Accounts/sessions and aggregate statistics/Hall of Fame | Permanent; include in backups |
| `var/global-search.sqlite3` | Full-text HELP/Docs and public-index metadata | Rebuildable index |
| `var/server-settings.json`, `var/content-settings.json` | Quotas and installation selections | Permanent configuration |

Published HELP stays outside `var/`; moving it gives no benefit here and risks
existing installations. URLs remain `/helps/...` and `/?file=...&topic=...`.
`THELP_HELPS_DIR`, `THELP_SOURCES_DIR`, `THELP_DOWNLOADS_DIR` and
`THELP_STATE_DIR` permit explicit storage overrides. Docker mounts the project
with these defaults. `var/` must survive image/container replacement.

Old `downloads/` and `var/dos/downloads/` are not moved/deleted. DOS reads its
old cache before fetching a missing new-cache entry. Original HELP and private
user storage are never temporary downloads, even though generated files and
state are excluded from Git. Do not clean all of `var/` as cache.

## Module and API flow

`server/content.py` schedules one background installation at a time:

1. Validate stable manifest group/package IDs, persist the explicit selection.
2. `downloader/service.py` invokes the existing HELP providers; transport
   reports byte progress per task without redirecting process-wide stdout.
3. `converter/build.py` converts selected source paths through the existing
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
