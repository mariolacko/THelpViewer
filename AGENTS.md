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
- Preserve APIs, configuration, environment variables and file paths unless
  the user explicitly requests a break. Check callers before changing them.
- Test the intended behavior, not just implementation details. Verify the
  result before reporting success; explicitly report failed or unverified work.
- Run Python tests with `PYTHONDONTWRITEBYTECODE=1` and pytest's
  `-p no:cacheprovider`. After every test run (including failures), remove and
  verify the absence of repository `__pycache__`, `.pyc`/`.pyo`, `.pytest_cache`
  and other temporary test caches. Never clean `.venv`, dependencies, source
  HELP files, generated bundles or persistent `data/` as test cache. Never
  recursively clean all of `var/`; its generated DOS/MIDI data and downloads
  have explicit, recoverable rebuild operations.
- Record every user-visible feature or behavior fix under `CHANGELOG.md`'s
  `[Unreleased]` section and update affected technical documentation.

## Adding HELP files

1. Inspect the existing product, source and bundle layout first. Put original
   files in `data/sources/<Product>/` and generated UHF bundles in
   `data/helps/<Product>/`; retain an existing release subdirectory when that
   product already uses one. Never add a staging/build-group directory such as
   `Candidates/` to these paths or to the Help Files menu.
2. Register the product in `thelpviewer/config/help-database.json`: stable product
   key, label, `build_group`, `collection_prefixes`, and downloader
   `search_text`/`query`/URLs following comparable products. Add CRC32
   `entries` for known source files with the correct product, title, encoding
   and language. Do not invent metadata that has not been verified.
3. `archive_members` is the downloader's exact extraction list, **not** the
   converter's input list. Select the files needed for conversion and any
   required licence notices; do not extract unused companion files. Explain
   retained non-converted files in the downloader or format documentation.
4. Reuse an existing reader when the format matches. For a new format, add a
   reader and register it in the manifest. Write `docs/Formats/<Format>.md` as
   a specification of the original format first: evidence, structure,
   encoding, controls, links, limits and a small example. Separate confirmed
   facts from converter behavior and unresolved observations.
5. Build the affected group, rebuild `data/helps/catalog.json`, and verify the
   source-to-bundle mapping, titles, topic counts, cross-file links and Help
   Files menu. Test downloader selection and conversion with representative
   files. Build groups select product roots; opt-in groups need explicit roots
   so broad groups such as `microsoft` do not select or remove them.

The Help Files menu groups catalog entries by `product_name`, then `version`.
Releases of one product use the same version-free `menu_label`, with the
release in `default_version` or inferred from `collection_prefixes`. Do not
repeat the release in both menu levels. Keep existing bundle paths stable
when only changing menu metadata, so saved HELP links keep working.

## Server content storage

- Versioned application JSON belongs in `thelpviewer/config/`; converter and
  downloader modules belong in `thelpviewer/server/`. Server jobs call their
  Python APIs directly. `.env` and Docker Compose stay at the project root;
  web-edited settings remain permanent data, not versioned configuration.
- Permanent storage is `data/`: original HELP in `data/sources/`, published
  UHF in `data/helps/`, documents in `data/docs/`, accounts/statistics/settings
  databases and private DOS overlays/media in `data/dos/users/<id>/`.
  HTTP URLs and product/release-relative paths stay stable.
- Cache new HELP/DOS downloads under `var/downloads/help/` and
  `var/downloads/dos/`. Shared generated DOS C is `var/dos/c/`; downloaded
  tracks/covers/catalog are `var/midi/`. Never include `data/` in a rebuild or
  cache cleanup target. Upgrade with the old server stopped; migration verifies
  copies, refuses conflicts and archives originals in `data/migration-backups/`.
- Server download/build jobs call Python modules, not CLI subprocesses.
  Selections use manifest IDs; an empty selection means none. Publish staged
  HELP only after validation, preserving unselected content and a backup.

## Turbo Vision JS

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
