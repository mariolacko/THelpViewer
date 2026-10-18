# AGENTS.md

Repository rules for coding agents. Prefer the smallest change that fixes the
user's problem; these rules exist to prevent regressions, not to add process.

## Before and after a change

- Read the target file, its direct callers and exports, and nearby shared
  utilities before editing. Reuse existing components, patterns, design tokens
  and naming; explain conflicting patterns instead of inventing a hybrid.
- State assumptions when behavior is ambiguous and ask when a choice would
  materially change the result. Define what "done" means for complex work.
- Make surgical edits. Do not reformat or refactor unrelated code, add a
  framework for a one-off need, or overwrite existing user changes.
- Prefer the current design over backward compatibility. When an intentional
  fix/refactor changes APIs, configuration, paths or URLs, update callers,
  tests, catalogs and documentation together; do not retain old aliases,
  redirect routes or compatibility branches. Keep genuine source-format
  identities/cross-file links and protect permanent user data. Do not change
  a correct path merely to make it different.
- Test the intended behavior, not just implementation details. Verify the
  result before reporting success; explicitly report failed or unverified work.
- Run Python tests with `PYTHONDONTWRITEBYTECODE=1` and pytest's
  `-p no:cacheprovider`. After every test run (including failures), remove and
  verify the absence of repository `__pycache__`, `.pyc`/`.pyo`, `.pytest_cache`
  and other temporary test caches. Never clean `.venv`, dependencies, source
  HELP files, generated bundles or persistent `data/` as test cache. Never
  recursively clean all of `var/`; its generated DOS/MIDI data and downloads
  have explicit, recoverable rebuild operations. Isolate mutable test paths:
  replacing `AppConfig.state_dir` must also redirect `downloads_dir` and
  `sources_dir`; startup expiry must never reach the repository's real inputs.
- Record every user-visible feature or behavior fix under `CHANGELOG.md`'s
  `[Unreleased]` section and update affected technical documentation.
- Restart the local THelp Docker service when needed to activate or test changes;
  no separate confirmation is required. Check active jobs first and preserve
  persistent data and download caches. This does not authorize production
  deployment or restarts.

## Adding HELP files

1. Inspect the existing product, source and bundle layout first. Put original
   files in `var/sources/<Product>/` and generated UHF bundles in
   `data/helps/<Product>/`; retain an existing release subdirectory when that
   product already uses one. Never add a staging/build-group directory such as
   `Candidates/` to these paths or to the Help Files menu.
2. Register the product in `thelpviewer/config/help-database.json`: stable product
   key, label, `build_group`, `collection_prefixes`, and downloader
   `search_text`/`query`/URLs following comparable products. Add CRC32
   `entries` for known source files with the correct product, title, encoding
   and language. Do not invent metadata that has not been verified.
   Register additional verified revisions too; compare CRCs before copying so
   exact duplicates do not create another edition. Each new CRC entry keeps
   `sources` provenance in the same provider/query shape as product sources:
   verified release/download pages, portable `search_text`, fallback `query`
   and exact `archive_members`. Downloader jobs consume both family and
   edition queries; do not add retrieval metadata that providers ignore.
3. Use `archive_members` as the single list of files to extract and process;
   do not add parallel include/exclude configuration. Keep edition-specific
   lists with the edition's sources so older releases retain their own names.
   Retain required licence notices (not converted) and explain them in the
   downloader documentation. Ignore stale unselected originals during batch
   conversion without deleting them or adding filename hacks to readers.
4. Reuse an existing reader when the format matches. For a new format, add a
   reader and register it in the manifest. Every `docs/Formats/<Format>.md`
   datasheet must be a self-contained technical specification from which an
   independent decoder can be written: byte offsets, field sizes/types,
   endianness, addressing, encoding/compression, controls, links, boundaries,
   algorithms and byte examples. Mark unknown fields and unverified rules
   explicitly; retain technical variant differences, not a history of changes.
   Do not put our release/fix history, support status, test counts, module paths
   or UHF mapping in datasheets. Keep these in `CHANGELOG.md`, converter
   documentation or private `* RE Notes.md`, not among source-format fields.
5. Build the affected group, rebuild `data/helps/catalog.json`, and verify the
   source-to-bundle mapping, titles, topic counts, cross-file links and Help
   Files menu. Test downloader selection and conversion with representative
   files. Build groups select product roots; opt-in groups need explicit roots
   so broad groups such as `microsoft` do not select or remove them.

Keep source-format decoders and their font/layout/container helpers in
`converter/readers/`, output orchestration in `converter/writers/`, and shared
document/UHF models and cross-layer contracts at the converter root.

The Help Files menu groups catalog entries by `product_name`, then `version`.
Releases of one product use the same version-free `menu_label`, with the
release in `default_version` or inferred from `collection_prefixes`. Do not
repeat the release in both menu levels. A single-file edition opens directly
from its version item; a product with only one file opens directly as product
plus version, without redundant submenus. Use one canonical bundle layout in CLI
and server builds. Correct paths when needed; do not maintain old HELP URLs as
aliases. Reader-verified logical database names are real link identities, not
backward-compatibility aliases.

## Server content storage

- Group server feature logic in `server/accounts/`, `server/dos/` and
  `server/midi/`; keep HTTP adapters in `server/routes/` and common transfers in
  `server/downloader/`. Stores coordinate explicit modules/components, not mixin
  chains or dynamic forwarding. Keep small shared modules at the server root.
- Share archive mechanics through server/archives/ (no HELP or network
  dependencies), operation events through processing.py and atomic publication
  through file_storage.py. Keep HELP ingestion/edition selection in converter/;
  providers discover source plans, while HELP/DOS/MIDI retain domain validation.
- Versioned application JSON belongs in `thelpviewer/config/`; converter and
  downloader modules belong in `thelpviewer/server/`. Server jobs call their
  Python APIs directly. `.env` and Docker Compose stay at the project root;
  web-edited settings remain permanent data, not versioned configuration.
- Permanent storage is `data/`: published UHF in `data/helps/`, documents in
  `data/docs/`, accounts/statistics/settings
  databases and private DOS overlays/media in `data/dos/users/<id>/`.
  HTTP URLs and product/release-relative paths follow the current canonical
  layout; rebuild catalogs/indexes after an intentional layout change.
- Cache new HELP/DOS/MIDI raw downloads under `var/downloads/help/`,
  `var/downloads/dos/` and `var/downloads/midi/`. Extracted/manual HELP originals
  and licence notices belong in `var/sources/`; retain them across uninstall
  and rebuild, but expire unused inputs with the same cache lifetime as raw
  downloads. Explicit administrator Clear cache empties both locations after
  warning that manual/unavailable inputs may be impossible to download again.
  Shared generated
  DOS C is `var/dos/c/`; downloaded
  tracks/covers/catalog are `var/midi/`. Never include `data/` in a rebuild or
  cache cleanup target. Upgrade with the old server stopped; migration verifies
  copies, refuses conflicts and archives originals in `data/migration-backups/`.
- Raw downloads and HELP inputs expire by `download_cache_days` (default 30) since their
  last successful download/use, at startup and hourly under idle downloader
  maintenance. Successful HELP ingestion/reuse and server conversion refresh
  input mtime; passive scans and failed conversion do not. Never expire installed
  content or permanent data. DOS archive paths are
  `<package-id>/<readable-archive-name>` with source/checksum sidecars; preserve
  source identity across same-name alternatives, and migrate recognized old
  cache entries rather than adding runtime hash-path fallback aliases.
- Group recoverable content generations under `var/backups/help/`,
  `var/backups/dos/` and `var/backups/midi/`, respecting `backup_count` per
  family. A HELP sibling rollback directory is transient until publication
  succeeds; then move it to the backup tree, verifying cross-filesystem copies.
  Preserve migration archives and private overlay revisions separately.
- Server download/build jobs call Python modules, not CLI subprocesses.
  Selections use manifest IDs; an empty selection means none except DOS
  sources explicitly marked `required` in the manifest. Publish staged
  HELP only after validation, preserving unselected content and a backup.
- DOS boot verifies required recipe receipts and owned-file presence, not only
  configured selection or `_complete`. Missing required tools install before
  jsDOS starts; opening DOS does not apply saved optional selections. Required
  work leads the shared queue using the manifest flag, never hardcoded IDs.
- Shared DOS C has no aggregate byte/file quota. Capacity quotas apply to private
  user data; archive safety bounds stay separate. DOS queue completion requires
  publication of the live disk and receipt, not preparation in a staging tree.
- Persist operation intent and processing progress in `data/jobs.sqlite3`.
  Recover only queued/interrupted jobs, not terminal failures or old saved
  selections. Validate output checkpoints against real files before skipping
  work; percentages are not completion receipts. Publish each successful HELP
  edition immediately and preserve it if another edition fails. Reserve recovered
  HELP work before starting the index or expiring its inputs. One server process
  owns the journal; stop/join its writers before releasing ownership.
- HELP Packages, DOS Packages and MIDI Sources are separate dialogs derived
  from TVPackagesDialog, sharing layout/workflow, not a mode-switching window.
  Keep product/package descriptions in their configuration manifests. HELP
  installation IDs are product:version, using the same metadata as Help Files; do not fall back
  to installing/removing an entire product when one edition was selected.
- In package dialogs the checkbox below the right pane selects only its
  category/source; bottom Select All/Deselect All buttons span every group of
  that dialog. Keep domain pipelines separate; reuse source-manifest validation
  and atomic JSON storage rather than copying configuration I/O into stores.

## Turbo Vision JS

- Version 3 application modules have a JavaScript client and an optional Python
  server component under one stable identity. Client-only modules may use shared
  server services; do not add empty Python backends (e.g. MOD Player) or duplicate
  download queues. Keep existing applications directly registered until their
  migration is explicitly requested. Follow the planned module contract in
  docs/THelp Viewer/TurboVision JS.md; distinguish planned APIs from implemented
  behavior. New module windows still use the TVision hierarchy and owner flow.
- Match the original Turbo Vision hierarchy, constructor order, method names,
  state masks, owner flow and `TVEvent` handling wherever the browser permits.
  Concrete dialogs and games retain references to owned `TVView` children and
  handle commands/input in `handleEvent()`. Do not rediscover owned controls
  with dialog-wide `data-tv-*` selectors or parallel DOM click handlers.
  Private DOM queries inside shared drawing primitives are permitted.
- Compose dialog client areas from shared views (`TVGroup`, `TVStaticText`,
  `TVLabel`, `TVInputLine`, `TVListViewer`, `TVOutline`, `TVCluster`, `TVButton`).
  Keep handwritten HTML/CSS in shared frame/window/dialog/scrollbar drawing,
  not in each dialog. Game chrome uses shared views; only the changing
  playfield may stay specialised. Do not add a one-off dialog control when an
  existing shared view fits.
- Public constructors describe TVision objects, not browser nodes. Use
  positional forms such as `TVView(bounds)`, `TVGroup(bounds)`,
  `TVStaticText(bounds, text)`, `TVLabel(bounds, text, link)`,
  `TVInputLine(bounds, maxLen)`, `TVButton(bounds, title, command, flags)`,
  `TVListViewer(bounds, numCols)`, `TVEditor(bounds, hScrollBar, vScrollBar,
  indicator, bufSize)`, `TVScrollBar(bounds, options)`,
  `TVWindow(bounds, title, number)`, `TVDialog(bounds, title)` and
  `TVDesktop(bounds)`. Bind browser roots later with `bindRoot()`; insert
  children with `insert()` / `insertAll()` and managed dialogs through
  `TVDesktop.insert()` / `TVDialogManager.register()`.
- Do not add public CSS class, HTML tag, arbitrary attribute, DOM selector or
  renderer-option arguments. Classes, IDs, accessibility/data attributes and
  markup belong in the owning shared view's drawing code. Link `TVLabel` to
  its target object, not a caller-chosen DOM ID. Do not restore `TVWidget`,
  `TVButtonStrip`, `TVMarkupList`, object-literal compatibility constructors
  or a separate renderer service.
- When adding or changing user-facing tools, update `tv-context-help.json`
  (Contents, Index, topics and links) and its mirrored converter asset. New
  views own their `hc...` context; do not add a separate dialog-context map.
