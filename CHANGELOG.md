# Changelog

## [Unreleased]

### 2.1 development

- Align restart/Retry and MIDI availability documentation with the current
  implementation. Record the production inventory audit and the outstanding
  legacy MIDI-cache validation/normalization work in TODO; no repair of those
  cached payloads or new complete-suite result is claimed.
- Queue only missing MIDI tracks/albums after restart, checking every ZIP member
  before creating work. Preserve completed/failed history without resetting the
  progress batch or replaying cached source indexes. Reconcile interrupted rows
  whose output was already published, and remove deselected MIDI queue entries.
  DOS Retry continues the saved requested additions as one disk transaction,
  preserves installed packages/private data, and removes obsolete unselected
  queue rows. Allow Retry/Remove for blocked "Not started" rows and clear stale
  errors when installation succeeds; terminal failures still need explicit action.
- Install Debian's separate `7zip-rar` decoder in Docker so the shared extractor
  can fall back when `unar` fails on historical solid/SFX RAR packages such as
  Text602 3.1. Keep archive validation and failed-output cleanup unchanged.
  Report the actual trailing extraction error without terminal control codes,
  rather than truncating the preceding successful-file list. Existing Docker
  deployments need an image rebuild, not only a container restart.
- Run independent HELP and DOS installation jobs concurrently, including
  recovery and combined requests. Give every job/type its own progress and
  journal/checkpoint context, preserve same-type ordering and stable live DOS
  receipts, and release the global-index pause when HELP finishes. Separate
  bounded preparation drivers from HTTP/extraction workers and look ahead for
  independent HELP/DOS sources without increasing per-site connection limits
  or changing DOS installation order. Keep failures, retries and shutdown
  isolated, and update Downloads/package HELP and technical documentation.
- Connect every application HELP topic to its parent category and Help Contents
  through footer links. Expand relevant cross-links between viewers, tools,
  accounts, packages and Downloads, remove a duplicate MIDI Sources link, and
  complete the Contents tree. Verify category/topic navigation in both bundle
  mirrors and in the existing shared HELP window; no new renderer or CSS.
- Review all 47 application HELP topics, expanding short tool descriptions and
  the rules, controls, scoring and tips for all twelve games. Reformat prose
  into paragraphs within the 72-column UHF text area, retaining topic IDs,
  links and tables; align the DOS Prompt shortcut table. Correct Tetris's
  Down/Space hard-drop description and Hanoi's right-tower goal. Verify every
  topic in the shared help window, without changes to player/game code or CSS.
- Write Downloads HELP as continuous paragraphs, word-wrapped to its 72-column
  UHF text area rather than one sentence per source row. Separate titled
  sections with real blank lines, retaining the shared HELP renderer. Correct
  the obsolete claim that restart clears the queue; add source-layout and
  browser coverage when restoring the application's own help from a URL.
- Persist explicit HELP/DOS installation jobs, processing phases and queue rows
  in `data/jobs.sqlite3`. Recover queued/interrupted work after restart, verify
  checkpointed HELP outputs by SHA-256, reuse validated sources/download caches,
  and repeat only unfinished safe units. Terminal failures require explicit
  retry; removing a failed queue row persists across restarts. One process owns
  the journal; shutdown drains content writers before releasing it.
- Publish each validated HELP edition immediately instead of waiting for an
  entire batch. Refresh Help Files in open browsers as the live catalog changes;
  later failures keep successful editions. Defer unchecked-edition removal until
  requested additions succeed. Recover an interrupted HELP directory swap from
  its exact journaled rollback path before rotating backups.
- Connect incremental global indexing to the same job journal. Retain committed
  per-file SQLite checkpoints, recover interrupted work, persist unchanged-file
  failures, and stop at source boundaries. Recovered HELP work holds the index
  before its first startup scan; cache expiry/clearing cannot consume inputs
  reserved by unfinished content jobs.
- Distinguish FAT images containing embedded ZIP end records from real ZIP
  containers by requiring a readable central directory before ZIP selection.
  Retain strict ZIP metadata/quota/path validation. Decode Borland installer
  split ZIPs with four/five-byte headers, checked 24-bit offsets and lettered
  volumes after 9, without misclassifying Microsoft cabinets. Prioritize
  complete assembled streams before unrelated installer examples.
- Give Borland C++ 2.0, 3.0, 3.1 and the framework guides precise edition source
  recipes/member lists. Register the CRC-verified ObjectWindows guide from the
  same 3.1 installer as Turbo Vision; treat registered revisions of a component
  as alternatives, retaining valid existing originals. Exclude unselected stale
  companions from conversion without deleting them or adding reader hacks.
  Consumer cancellation no longer marks another successful source as Failed.
- Accept aggregate telemetry for current account/configuration/download dialogs.
  Classify automatically registered progress/message windows with bounded stable
  names, not generated view IDs or window text, preventing repeated HTTP 422s.
- Restore Game-Cheater download discovery when Slunečnice puts the signed
  program URL in a JavaScript string instead of an anchor. Decode only the
  literal, verify the source/path/signature fields and ignore partner downloads;
  report missing links as recoverable source failures. Pin Turbo C++ 1.00's
  original floppy archives at Internet Archive and WinWorld, retaining the
  exact TCHELP.TCH selection and CRC edition. Prefer exact direct archives
  before release-page crawls, retaining other sources as fallbacks.
- Report external archive extraction percentages through the shared queue:
  unar counts successfully extracted entries against lsar's listing, while
  7-Zip supplies native progress. Stream output without moving the child's
  write position, retain timeout/quota/path checks and validate before completing
  extraction. HELP conversion reports completed files/source groups; unknown
  phase totals retain an icon rather than an invented percentage.
- Suspend the global HELP/Docs/SEO index while server HELP sources are being
  downloaded, extracted, converted and published, including Retry/removal and
  failure cleanup. Finish the current indexed file before yielding, release
  SQLite, retain committed search data, and rescan the final live library once
  HELP work ends, even on failure. DOS/MIDI-only jobs do not hold the index.
  Show a paused `▤ ‖` indicator and waiting progress status; keep polling and
  return temporary 503/Retry-After for not-yet-indexed public pages, not false 404s.
  Refresh pending search results when indexing finishes even if the build was
  too quick to create a progress window; idle polling does not reset selections.
- Remove nonexistent plain Scorpions Cheater 6/7/8 installation choices; use
  the actual shareware edition IDs already present in source collections and
  published HELP. Ignore removed HELP IDs in saved requests, not explicit new
  API requests. Attribute a failed pipelined conversion to its edition and mark
  other unpublished editions blocked rather than claiming each download failed.
  Whole-library checks no longer start/change the progress of every edition.
- Recover old SHA-pinned DOS installations once when manifests no longer pin
  those hashes: verify the retained archive checksum and its files against the
  shared C drive, persist ownership, and migrate to readable cache paths and
  current receipt keys. Preflight conflicts, preserve unknown packages/private
  data, never overwrite changed C files, and retain original cache bytes until
  verified copies and the updated receipt are published. This prevents unrelated
  package changes from failing despite the original archives still being present.
- Apply the configured cache lifetime (default 30 days) to unused HELP originals
  and licence files in `var/sources/` too. Refresh their age after accepted
  ingestion/reuse and successful server conversion, not passive scans or failed
  decodes. Check startup/hourly only while idle and protect published HELP,
  installed DOS/MIDI, user data and backups. Existing file dates are used as-is;
  unavailable/manual originals need an independent backup if they must be kept.
- Include extracted/manual HELP originals and licence files in `var/sources/`
  in confirmed administrator Clear cache, together with raw HELP/DOS/MIDI
  downloads. Warn that unavailable originals may not be downloadable again;
  count both locations in the result and preflight every scope before deletion.
  Apply automatic expiry by age, while manual cleanup clears all inputs. Preserve published HELP,
  installed DOS/MIDI, private data, settings, indexes and backups.
- Give DOS raw-download cache readable package/archive paths with separate
  source-identity and content-checksum metadata. Migrate recognized flat cache
  files without redownloading or losing timestamps; preserve unknown inputs
  for normal expiry rather than guessing their package. Never reuse another
  source's same-name archive or publish invalid downloads over a valid cache.
  Preserve one-transfer-per-source reuse across different package IDs.
- Add Download cache lifetime to Server Configuration, default 30 days since
  successful download/reuse, configurable from 1 to 3650 days. Sweep HELP, DOS
  and MIDI raw downloads plus HELP inputs at startup and hourly while idle. Defer active jobs,
  remove matching metadata/empty folders, reject unsafe paths before deletion,
  and preserve installed content, backups and private user data.
- Move extracted and manually supplied HELP originals to `var/sources/` for
  server jobs, downloader, builds and database tools. Migrate existing originals
  with SHA-256 verification and conflict checks, retaining a recovery copy.
  Keep published HELP/Docs and private data in `data/`; no URL aliases or changes
  to product/release paths. Uninstallation and rebuilds preserve originals;
  expiry and explicit Clear cache remove these cached inputs.
- Group recovery generations under `var/backups/help/`, `dos/` and `midi/`
  instead of leaving HELP snapshots in `data/` or mixing DOS/MIDI generations
  in one flat directory. Migrate existing managed backups without pruning or
  overwriting conflicts. Keep atomic HELP rollback beside the live library
  until publication succeeds, then relocate it; verify cross-filesystem copies
  before removing the original. Retain the configured per-family backup limit.
- Overlap package downloads, archive extraction and conversion through bounded
  processing workers separate from HTTP workers. HELP converts ready editions
  while later inputs continue, then atomically publishes each validated edition.
  DOS prefetches packages but installs/post-processes in manifest order; MIDI
  uses the same processing queue and retains its urgent playback lane. Preserve
  per-site transfer limits/cooldowns, serialize shared cache/original writers,
  cancel queued MIDI transfers on shutdown, and drain active writers on failure.
  Report conversion progress per edition rather than borrowing another
  edition's percentage.
- Separate colliding Turbo Debugger/Profiler original collections by their
  registered releases in the HELP manifest. Retain original filenames and
  CRC ownership; relocate a misplaced known original to its declared collection
  before filling its former slot, refusing unknown/different destination data.
  Prevent an installation of one release from blocking other registered releases
  with a false original-file conflict. Explicit registered-edition builds ignore
  unknown same-name originals from unrelated distribution collections rather
  than labelling them as that edition; no old URL aliases are added.
- Recognize OLE/CFBF document signatures before recursive archive inspection.
  Leave documents such as the TASM media's INSTALAR.DOC intact instead of
  interpreting internal CompObj/property streams as filesystem paths and
  aborting HELP discovery. Explicit document-as-archive inputs fail with a
  recoverable format diagnostic; real archives still reject control-character
  paths, traversal and links for all consumers.
- Show a temporary global-index indicator (▤ and percentage) beside Downloads
  and the clock. Clicking it reopens the existing Building Global Index dialog,
  including after Hide; remove the indicator when indexing finishes. Reuse the
  search status monitor for both displays, detect later background rebuilds,
  preserve progress across menu refreshes and stop polling on view destruction.
- Simplify Help Files menus using the JSON catalog's product/version metadata:
  a product with only one HELP opens directly with its version in the label;
  single-file editions open directly from their version item. Keep submenus
  for editions with multiple files, natural release ordering and real targets.
- Give every published Turbo Assembler HELP a verified edition: 2.0, 2.01,
  3.0, 3.1 and German 3.2. Register the two previously unlisted CRCs, retain
  executable/archive provenance and exact downloader recipes, and deduplicate
  the identical C++ 3.0/3.x copy through the normal CRC publication path.
  Sort release submenus numerically for all HELP products. Keep real source
  collections/cross-file identities rather than inferring an assembler version
  from the host C++/Pascal release. Prefer requested nested containers, stop
  after selection completes, and accept only byte-identical same-name copies
  created by split-media assembly; distinct ambiguous members remain errors.
- Align Server Configuration actions in a two-row, three-column grid with equal
  button widths and spacing. Keep Save/Cancel together at the bottom right and
  status above them; narrow the dialog to 82 columns without increasing its
  27-row height. Use shared TVision bounds, controls and shadows, not new CSS.
- Add Clear cache in Server Configuration, with explicit confirmation and a
  removed-file/source-byte summary. Administrators clear raw HELP, DOS and MIDI
  download caches (including abandoned transfer staging) and extracted/manual
  originals, never published bundles, installed DOS/MIDI, backups or private data.
  Refuse active downloads/processing, linked/special files and unsafe directory
  overlaps; serialize maintenance with new shared-downloader work.
- Prefer exact HELP-edition recipes before family-wide discovery and stop each
  provider between archives as soon as every required CRC component is present.
  Deduplicate failed/empty source attempts within a job as well as successful
  ones. Discovery may collect selected members across separate disks; pinned
  single-archive recipes and final edition completeness remain strict. Recover
  unreadable download-cache placeholders by fetching/validating a staged copy,
  retaining the old cache if recovery fails. Give Old-DOS download endpoints
  distinct readable cache names and separate the two colliding TASM originals'
  collections without overwriting existing source files.
- Apply in HELP Packages, DOS Packages and MIDI Sources submits the selected
  changes directly, without a second selection-confirmation dialog. Keep duplicate
  submission guards, DOS save/close handling and separate rebuild/delete prompts.
  Compact the shared progress dialog to at most 64 columns, remove unused file
  rows and excess bottom/gauge spacing, retaining full wrapped text, button
  shadows and the expandable Downloads list.
- Reuse `archive_members` for HELP extraction and batch input selection rather
  than separate include/exclude rules. Complete edition source lists also filter
  stale unselected originals already on disk; preserve originals, licence files,
  CRC checks and missing/ambiguous-member failures. Turbo Pascal 7 selects
  TURBO.TPH, OWL.TPH and TVISION.TPH, not the deferred HC30 examples.
- Keep known failed MIDI downloads out of automatic startup work. Removing a
  failed album no longer makes it reappear after a server restart. Persist
  download diagnostics in the MIDI catalog, preserving valid tracks and covers;
  explicit Retry, playback requests and source Apply can still retry failures.
- Show real processing stages in the shared Downloads menu and detail list:
  ↓ transfer, ▣ extraction and ⚙ conversion/installation/validation/publication.
  Display phase-local percentages only when bytes or work counts are known;
  clear stale percentages on stage changes. Concurrent stages remain visible
  together. Show ✓ only after successful processing/publication, never merely
  after transfer reaches 100%; failed work retains ! and waiting work has no
  invented percentage.
- Unify HELP, DOS and MIDI processing boundaries: one bounded archive layer
  for ZIP, external tools, disk images, nested/split containers and Microsoft
  single-file compression; one progress observer and atomic file publisher.
  HELP providers now pass source plans to common transfer/ingestion instead
  of unpacking/copying independently. MIDI caches validated original downloads
  in var/downloads/midi; rejected new inputs are not cached. Reject unsafe
  archive paths/links and enforce extraction quotas/timeouts. Separate converter
  selection, planning, metadata, results and validation from UHF writing;
  propagate actual conversion errors and use one validated catalog builder for
  server and CLI. Preserve published content/private data on processing failure.
  Index exact archive member paths once and avoid expanding unrelated software
  after the requested HELP files are available. Close standalone download
  workers on success/failure without stopping the server's shared downloader.
- Refactor the shared downloader with a separate progress/lifecycle registry,
  one staged cache helper and common source-attempt handling. Remove the unused
  second URL submission pipeline. Preserve source lanes, urgent MIDI playback,
  private/public snapshots and retry isolation. Missing download forms and
  incomplete responses can use alternatives; URL/peer/redirect policy failures
  abort instead of being hidden by provider fallback.
- Keep HELP queue rows active through conversion and publication, not just
  source transfer. Report conversion failures on the affected edition; mark
  Published only after activation. Retain successfully published HELP when a
  subsequent DOS installation fails. Cache processors validate fresh/reused
  files before new publication, without loading streamed HELP/ISO into memory.
- Add concrete Archive.org alternatives for all nine WinWorld-backed Borland
  HELP families and retain exact-member provenance for CRC-matching originals.
  Process pinned items before advanced search, using metadata directly; keep
  separate member selections, allow safe nested archive paths and skip scanned
  manual/KryoFlux ZIPs. Version/language and CRC selection still apply.
- Replace Norton Commander's mislabeled MFF image with original English DOS
  4.0 media and a second distribution. Extract its ARJ payloads on the server
  without running INSTALL. Shared package downloading supports complete
  alternative extraction recipes, bounded source retries and validation before
  cache publication; private disks, installed selection and other packages stay
  unchanged on failure.
- Treat HELP providers as edition-scoped fallbacks in one queue row. After
  bounded HTTP 429 retries, defer that site and its subdomains for the current
  HELP job instead of repeating the same quota across mirrors/products. Try
  other configured providers, stopping only at complete CRC-verified originals;
  retain source warnings without marking a recovered edition Failed. Explicit
  Retry starts fresh for that edition; incomplete verified sets do not publish.
  Route loose Archive.org/GitHub HELP through the same CRC/selection collector
  as archives, preserving cached originals and unrelated installed content.
  Retain CRC-registered utility references instead of skipping them as unknown
  accessories; non-CRC formats still require successful staged conversion.
- Redraw the shared TVButton bottom-shadow glyphs after changeBounds/locate,
  including buttons constructed before their final layout. Restore Downloads
  Hide/More/Less shadows without replacing button roots, focus or pressed state.
- Do not use one HTML response or archive's Content-Length as completion of a
  multi-request HELP source check/MIDI index. Count completed planned checks;
  retain byte-based single-track progress and owner-weighted DOS installation
  stages. Expand Downloads with wrapped full status/filename text, nonoverlapping
  shared views and complete package names accessible by horizontal scrolling.
- Bind each scrollbar to its own frame controls, not nested menus/lists; restore
  Download menu arrows, track clicks and thumb dragging without moving its
  Completed downloads submenu. Weight batch percentages by package/album rather
  than provider-attempt count, exclude already installed DOS packages from new
  work, and never show rejected source checks as 100% successful downloads.
  Refresh shell/export asset URLs so cached browser/CDN copies do not mask fixes.
- Filter WinWorld archive releases before transfer and place known HELP originals
  using their verified CRC edition/collection, skipping unselected editions while
  retaining conflict protection for unknown originals. Decode archive-tool
  diagnostics safely when legacy filenames emit non-UTF-8 bytes. Use Old-DOS's
  verified public HTTP catalog directly; keep generic HTTPS downgrade/private-peer
  checks unchanged. Plan only providers applicable to the requested edition.
- Diagnose plain-text files mislabeled `.mid` without pretending to convert
  them into music. Process every MIDI ZIP member, retain valid tracks and
  cover art when other members fail, and keep rejected-member diagnostics
  across catalog reloads. Partial albums stay failed/retryable until all
  members validate; urgent playback also publishes the usable track inventory.
- Accept DOS changes while HELP installation runs (and vice versa), show
  waiting packages immediately in Downloads and process installations in order.
  Keep each selection and earlier failures when the next job starts; Apply
  follows only its own content type instead of dropping another type's request.
- Share MIDI's normal/focused/selected row colors with the standard TVListBox
  palette used by Downloads. Preserve list focus during live row updates so
  the focused color does not disappear at every progress refresh.
  Align Statistics and package category icons with
  the shared list icon column; widen DOS Groups by one character to avoid an
  unnecessary horizontal scrollbar.
- Decode Turbo Basic TBHELP.TBH with its native WORD records, FE-space runs,
  context slots and absolute-offset hyperlinks instead of misreading it as
  nibble THELP. Preserve all 108 screens per original, including continuations;
  verify display bytes against TB.EXE and document the binary profile/CRCs.
- Build browser/Scorpion regression HELP libraries in temporary output, so
  administrator package selections no longer break those checks or get changed.
- Stop and join MIDI catalog/playback writers before closing the shared
  downloader; cancel only pending MIDI tasks and prevent pending rebuilds/source
  changes from restarting at exit, without waiting behind unrelated downloads.
- Reconcile Account/Login, shared package dialogs and Downloads documentation
  with the current APIs and controls. Correct the format index/Sidekick link;
  distinguish historical compiler experiments from current converter commands.
  Update account migration/browser fixtures for credential metadata and the
  security API. Record the initial full-suite result and subsequent repairs
  in TODO, keeping graphics and external-link verification explicitly scoped.
- Add Account's New password mnemonic (Alt+P) through the linked TVLabel.
- Add account-owned named Passkeys: list, add another authenticator and rename
  existing keys without changing their cryptographic identity. Suggest an
  editable OS/browser label at registration; preserve old unnamed credentials.
  Add optional password creation/change and Login's password alternative:
  validate matching entries, 15–128-character passphrases and basic weak values;
  store only salted scrypt hashes and throttle online guessing. Credential
  changes require a recent verified Passkey session; changing a password
  revokes other sessions. Keep account IDs, roles and private DOS files intact.
  Compose the expanded Account/Login from shared TVision controls, with masked
  inputs and no new layout CSS. Existing accounts remain passwordless until opt-in.
- Add eleven optional DOS development/office packages: Open Watcom C/C++ and
  Fortran, Free Pascal 1.0.10, FreeBASIC, NASM, JWasm, DJGPP with RHIDE,
  Microsoft Word 5.5, As-Easy-As 5.7, Ability Plus 3.0 and VisiCalc.
  Prepare compiler environments/examples and Word's VGA driver without
  interactive installation. Retain licence notices and leave existing package
  selections/private disks unchanged. Use 64 MiB DOS memory for development.
  Share bounded KWAJ/SZDD expansion for Microsoft's original software archives
  and case-insensitive archive member exclusions; expanded collections obey
  the configured shared-disk quota rather than the compressed download limit.
- Mark UTILS and Volkov Commander as required in the DOS manifest. Keep them
  checked and non-editable through individual/category/global selection;
  enforce the same rule in API requests, disk configuration and rebuilds.
  Align language flags with plain-text space padding, removing the special
  annotation markup/CSS. Shorten package titles and widen DOS Packages to
  90 columns so names, installed markers and flags fit without scrolling.
- Restore package dialog geometry through changeBounds and the shared
  growMode/calcBounds rules so its controls follow the window size. Respect
  hidden cluster state during redraw; the MIDI-only control no longer covers
  lower DOS categories such as Antivirus.
- Mark Quadrax as Slovak and remove the separate Volkov Commander source
  package. Keep the runnable Volkov Commander and its original BSD licence
  notice without installing assembly source files. Prune removed manifest IDs
  from saved DOS intent, without deleting files or accepting unknown API IDs.
- Size HELP/DOS Packages to 82/90 columns, move Description one row lower and
  align the Groups pane bottom with its Select/Deselect checkbox. Keep MIDI
  at 94 columns. Show useful descriptions without repeated name/status text;
  distinguish verified HELP editions through manifest-owned version descriptions.
- Schedule downloads across three regular source lanes plus urgent playback,
  limiting each site and its subdomains to one transfer. Skip busy sources,
  guard redirected response bodies and retain HTTP 429 cooldowns between jobs.
  Existing failed source-conflict, encoding and invalid-file errors are not
  silently treated as successful downloads.
- Add optional original DOS Vlak 2.01, DOS Manažer 2.20, Text602 3.1,
  Manager602 2.0 and operator-supplied Calc602 packages with prepared runtime
  layouts. Calc602 excludes saved settings and working/test documents. Add language metadata
  and Unicode flags at the end of DOS package names; mixed/unknown languages
  use a globe. Package selection and private disks remain unchanged.
- Compact all package dialogs by removing the three heading rows. Add a
  shared Select / Deselect All checkbox below the right pane for its current
  category/source; the bottom Select All / Deselect All buttons now span every
  group of that dialog. MIDI global selection also enables/disables providers;
  selecting all albums includes future albums. Keep selection, confirmation
  and per-type Apply semantics independent between the three windows.
- Share DOS/MIDI source-manifest structure/ID validation and reuse one DOS
  configuration loader for choices, installation and rebuild. Share atomic
  JSON settings publication across HELP/DOS selection, MIDI, server settings
  and migration metadata, cleaning temporary files on failure and retaining
  live settings. Keep domain-specific installation pipelines separate.
- Expand DOS Packages to 14 populated categories and 55 packages. Add Winter
  Challenge, Summer Challenge, Lotus: The Ultimate Challenge and the shareware
  first episodes of Duke Nukum, Duke Nukem II, Crystal Caves and Bio Menace.
  Add DOS Navigator 2, DOSZip, TDE, BIEW, GrafX2 and DOSMid from the FreeDOS
  repository, keeping documentation, licences and supplied source archives.
  All new entries are opt-in; no installed or private files are moved.
- Add optional DOS packages for Cannon Fodder 1/2, Commander Keen episodes
  2–6 and Keen Dreams alongside the existing episode 1, and Catacomb, Catacomb
  II, Catacomb 3-D and The Catacomb Abyss. Verify archive members and launch
  commands; extract DOS game data/manuals, not portable Windows emulators.
  Existing installations and private disks are unchanged until Apply.
  Shared archive recipes validate selected DOS paths after member filtering;
  irrelevant host-only filenames do not block a safe game-only selection.
  Nested-archive input is materialized only for rules that actually need it;
  host extraction traversal/symlink guards remain in place.
- Share TVPackagesDialog layout/workflow between three separate HELP Packages,
  DOS Packages and MIDI Sources windows, without a mode selector. Each menu
  entry opens its own dialog; switching windows retains independent drafts;
  keep shared selection controls, descriptions, confirmations and
  shared download progress. HELP groups follow Help Files menu product names;
  edition IDs select exact versions through download, staged conversion and
  removal. Keep published siblings, originals and private data; failed requests
  are not installation receipts. Update API clients without old selection aliases.
  Add manifest-owned HELP product descriptions beside DOS descriptions.
  Keep dynamic TVLabel mnemonic markup when its text changes;
  use standard horizontal scrolling for long group names.
- Reopening HELP/DOS Packages now checks the published HELP catalog and DOS
  installation receipt instead of treating a failed saved request as installed.
  Running targets and explicit Retry remain separate from installed state.
- Verify 7zz/7z, unar, lsar and DOSBox during Docker image construction. Document
  verifying the actual runtime image, not only updated bind-mounted source files.
- Bound retained HELP, DOS and MIDI backups to two per type by default.
  Administrators can set 1–100 in Server Configuration; successful publication
  or rebuild rotates only that type (DOS package changes and base rebuilds share
  a limit). Failed/partial rebuilds keep recovery copies; migration archives,
  private disk revisions and download caches are not automatic cleanup targets.
- Clarify maintenance cleanup boundaries: active download caches live in
  `var/downloads/`, not the obsolete root directory. Distinguish removable,
  verified migration/HELP recovery copies from permanent sources, published
  content, databases, private disks and operational migration metadata.
- Place source-format helpers under converter readers: Software602 graphics,
  Turbo Vision topics, DOS BACKUP containers, and Windows Help binary/text
  decoding. Keep bundle dispatch with writers and administrator HTTP guards
  with routes. Update manifest targets, imports and documentation without old
  module aliases; conversion algorithms, source data and published URLs are unchanged.
- Split server account, DOS and MIDI responsibilities into dedicated packages:
  account profiles/registration/Passkeys/sessions; shared DOS installation,
  archive recipes/private overlays/media; and MIDI source discovery/catalog/
  container decoding. Keep explicit coordinating stores and one shared downloader,
  update all consumers and tests, and remove the former flat modules without
  compatibility shims. API URLs, disk quotas and persistent data paths are unchanged.
- Reset the shared download counter after a successful batch and remove the
  percentage from the menu caption, retaining the down-arrow/history menu.
  Start later work and retries at zero without counting completed history;
  keep concurrent work and public/private progress scoped correctly. Finished
  rows retain 100% in Completed downloads and the finished dialog gauge.
- Normalize RIFF/RMID and counted DOS MIDI containers to bounded Standard MIDI
  payloads before publishing music. Validate MIDI headers/track boundaries,
  exclude source trailers, and name an invalid ZIP member in the download error.
  Accept albums up to 4,096 ZIP entries while retaining 2 MiB/file and 128 MiB
  expanded MIDI limits. Show ready-track counts and a download-error count when
  opening a partially downloaded library, not another album's raw error.
- Encode Unicode/space-containing download URLs as UTF-8 HTTP addresses in the
  shared HELP/DOS/MIDI transport, including form actions and redirects. Preserve
  existing percent escapes, query separators and POST fields; retain public-peer,
  HTTPS and configured-host checks. Do not rename source titles or catalog IDs.
- Wrap the complete failed-download label, error and notice with the same text
  wrapping as MessageBox. Size the dialog from its rows and wrap buttons on narrow
  screens instead of truncating album names or cutting error messages at three rows.
- Submit on-demand MIDI playback directly to the shared downloader, ahead of
  waiting work, with a named per-track queue row. One reserved urgent worker can
  fetch the selected song while the serial HELP/DOS/background queue is busy;
  newer waiting playback requests go first. Promote existing queued transfers
  without duplicating requests or cancelling their callers. Keep selection,
  album and cache validation; MIDI rebuild/source changes wait for active playback
  downloads before moving generated data. Refresh the shared download menu as
  soon as playback enqueues missing music.
- Wrap all MessageBox text within the visible character-cell width, including
  long HTTP 429 messages, unbroken words and embedded newlines. Resize the window
  from the wrapped rows, wrap buttons on narrow screens and center dialogs in the
  visible desktop area; do not truncate download errors in a single text row.
- Add shared system-clipboard commands `cmCut`, `cmCopy`, `cmPaste` and
  `clipCut`/`clipCopy`/`clipPaste` to input lines and editors. Support Turbo Pascal
  Ctrl+Insert, Shift+Delete and Shift+Insert alongside native OS Ctrl/Cmd+C/X/V.
  Keep native editable clipboard events in the TVEvent flow without replacing
  browser undo or paste-permission handling. Validate pasted input, respect length
  limits, reject stale asynchronous edits, and never cut text before copying
  succeeds. HELP/Docs remain read-only. Use the common clipboard writer for tokens;
  do not poll, persist or send clipboard contents to the server.
- Remove the bottom status row from HELP Packages, DOS Packages, Initial Content
  Setup and MIDI Sources, shortening their windows by two rows. Show download and
  installation progress only in shared Downloads/index progress windows; report
  configuration failures and source warnings with standard MessageBoxes.
- Add Copy to Clipboard as the Registration Token dialog's fourth action,
  using a shared TVButton command. Copy the generated or selected token and
  report success; if browser clipboard access is unavailable/denied, select
  the input for manual Ctrl+C/Cmd+C instead. Disable Copy when no token is shown.
- Remove completed rows from the Downloads dialog immediately, retaining only
  waiting, running and failed work. Keep successful rows in the menu's Completed
  downloads submenu, preserve the selected item during live removal, and swap
  Hide with More/Less. Collapse the details pane when no pending rows remain.
- Keep HELP Packages and DOS Packages modeless, like MIDI Sources, so switching
  configuration windows preserves their open state and draft selections. Remove
  backdrop-click closing from the shared TVDialog; modal confirmations still
  block background input without treating it as Cancel or Close.
- Replace the content-specific Applying Server Content window with one shared
  Downloads dialog for HELP, DOS and MIDI, also opened through Show Downloads in
  the download menu. Generalize TVIndexProgressDialog to TVProgressDialog; reuse
  its gauges, More/Less and green TVListBox without extra HTML/CSS. Preserve
  conversion/publication progress and archive/cache counters while showing the
  common queue. Downloads is nonmodal and remains available after completion.
- Restore usable Apply state after accepting a background installation and after
  failures (including HTTP 429). While a job runs, Apply reopens its progress rather
  than submitting a duplicate. Preserve draft selections across categories and
  completion refreshes. Keep Apply disabled only during configuration loading,
  submission or when configuration is invalid. Bound the DOS confirmation preview
  for large selections. Register temporary dialogs through their TVDesktop owner
  before opening so confirmations cannot remain beneath managed package windows;
  do not serialize their runtime view IDs into workspace URLs.
- Clicking a failed download opens a shared-view dialog with Retry, Remove and
  Cancel. Retry repeats only failed parts of that HELP product, DOS package or
  MIDI album, retaining successful work and unrelated selections/installations.
  Remove forgets only the runtime queue entry, never caches or installed/private
  files. Closing with [ ] or Escape changes nothing. Reject duplicate/busy or
  deselected retries, preserve same-origin/admin boundaries and keep failures
  visible when a source still cannot be downloaded or validated.
- Keep the download menu caption strictly as a Unicode down arrow and percent,
  including stopped/failed queues. Move successful rows into the first Completed
  downloads submenu; leave waiting, running and failed rows in the main popup.
  Retain access to completed queues after downloading ends. Preserve an open
  nested menu, focus and scroll while rows move between lists. Report partial
  stopped queues using their actual known progress, not an unconditional 100%.
- Route HELP, DOS and MIDI transfers through one queued online downloader with
  FIFO/priority execution, propagated task context, common bounded HTTP retries,
  byte limits, redirect/public-peer validation and atomic cache writes. URL tasks
  can include a cache destination and an extraction/install processor; nested
  processing stays on the same worker. Retain format/provider-specific modules.
  Add a live TVDownloadProgress menu between the account and clock, using the
  shared TVMenuBox and scrollbar. Show pending/active/completed/failed packages,
  grouped MIDI albums and retry countdowns without closing the open menu during
  updates. Replace the player's separate automatic MIDI download dialog.
  Hide private HELP/DOS entries from non-administrators. Closing the
  menu does not cancel jobs; installation publication still uses existing staging.
- Add an opt-in UTILS collection assembled through the shared downloader from
  FreeDOS/DJGPP ZIP packages and the original UnARJ 2.41 archive recovered
  from the administrator's DOSBox collection. Retain licences, available
  sources and the unchanged UnARJ envelope; do not bundle registered keys or
  assume RAR/ARCE are unrestricted freeware. Add configurable extraction
  rules and assembled Borland split archives so Turbo Pascal 5.5, Turbo C 2.01
  and Turbo C++ 1.01 are published as ready program/header/library/help trees,
  not interactive installers. Run optional CP437 post-install BAT lines once
  in a temporary DOSBox filesystem before publishing, with secure mode,
  timeout, output validation and package-scoped writes. Include DOSBox and
  unar in Docker for this workflow and classic ARC extraction.
- DOS Packages now displays category icons and a shared Description box
  following mouse/keyboard selection; Select All, Deselect All, Apply,
  Refresh and Close share one row. Bulk marking affects only the current
  category. Name pending new installs in the confirmation so a retained
  package in another category cannot look like a download caused by removal.
  Rename MIDI Sources and label its per-source Select All / Deselect All.
  Retry package HTTP 429 responses with bounded Retry-After waits and progress;
  repeated rate limits name the affected package. Verify pure DOS removal
  never downloads or runs post-install scripts. Update native context help.
- Reject an outdated DOS configuration API before enabling Apply: missing
  category metadata now shows a server-restart explanation instead of an
  applicable empty package selection. Keep HELP Packages unchanged. Verify
  recovery after the matching API becomes available.
  Do not reopen the combined first-run chooser on an existing HELP/DOS
  installation after an interrupted job; retain completed setup state during
  later installation attempts, including failures.
- Keep HELP Packages and DOS Packages as separate dialogs. Give DOS Packages
  a category TVListBox (Games, Programming, Antivirus, Utilities), a package
  TVCheckBoxes pane and Select All for only the current category. Preserve
  unsaved selections across category switches and submit the complete DOS
  draft, without changing HELP choices. Add opt-in original Borland Museum
  Turbo Pascal 3.02/5.5, Turbo C 2.01 and Turbo C++ 1.01 packages, and complete
  ThunderBYTE 8.03 evaluation/Norton Michelangelo antivirus distributions.
  Identify installer/evaluation editions explicitly and retain licence files;
  do not classify NOD-iCE or restricted F-PROT preinstallation as abandonware.
  Support generic validated `strip_components` for multi-disk distribution
  layouts, rejecting traversal, short paths and resulting filename collisions.
  Interpret ZIP Unix symlink mode bits only for Unix-created entries, avoiding
  false rejection of ordinary legacy DOS ZIP files while retaining link checks.
  Update native context help and server/DOS documentation.
- Restore local MIDI cover availability after macOS/iCloud offloads image
  files that Docker cannot hydrate. Include existing MIDI tracks, covers and
  SQLite catalog/sidecars in the management script's host-side Docker
  availability preflight, without deleting/rebuilding media or pinning paths.
  Document incomplete HTTP image bodies caused by host placeholder I/O errors.
- Identify the older Turbo Debugger CRC editions by release in their bundles
  and catalog; disambiguate equal sibling HELP menu labels with bundle names
  without dropping real files or guessing unknown versions. Use readable
  archive names, rather than mirror UUIDs, in HELP download progress and pinned
  WinWorld cache names; decode/sanitize direct-download filenames. Report
  discovery, cache reuse, extraction, byte progress and rate-limit waits instead
  of leaving a completed transfer on screen. Applying Server Content and MIDI
  download progress share More/Less and a green TVListBox below the compact
  view: HELP products show waiting/active/checked/warning markers and archive
  counters; MIDI albums show ready/total percentages and completion ticks.
- Preserve source-provider warnings in the HELP job API and details instead
  of reporting unsuccessful provider checks as unqualified completions.
- Split normal HELP and DOS package configuration into independent TVDialogs
  backed by the same installer/progress views; changing one category preserves
  the other and does not retry its failed jobs. Keep the combined first-run
  chooser. MIDI configuration now has a source TVListBox on the left and game
  soundtrack TVCheckBoxes on the right, with Enable, All/None and future-album
  selection. Index unselected sources with progress without downloading their
  music. Persist/filter album choices in downloads, playlist, priority requests
  and file/cover serving, retaining caches and respecting choices on rebuild.
  Paint the whole shared scrollable cluster, including blank rows, with its
  normal palette instead of coloring only populated rows. Update context help.
- Group all administrator configuration under the user menu's Configuration:
  server settings, HELP/DOS installation, MIDI providers, users/tokens and
  DOS/MIDI rebuilds. Keep personal Colors/Theme available to members and
  remove their duplicate system-menu entries while signed in. Rebuild actions
  open confirmation/progress directly, without opening Server Configuration,
  and report standalone completion/errors in a shared MessageBox.
  Add a TVCheckBoxes MIDI source selector with an admin/same-origin API,
  permanent data/midi-settings.json selection and safe downloader handover.
  Empty selection disables all sources; deselection retains cached MIDI/covers,
  and rebuild respects the selection. Update native context help.
- Extend the Docker host-side file-availability preflight beyond HELP to
  accounts/settings metadata and shared/private DOS storage, including empty
  first-run HELP installs. Abort before Compose on unreadable data. Document
  iCloud placeholder recovery for local Admin and DOS Prompt without deleting,
  rebuilding, moving or pinning their existing files.
- Restore Microsoft SZ payloads split across installer disks through the
  shared downloader extractor, preserving LZSS state between numbered parts.
  Reject missing, damaged or ambiguous parts and bound decompression instead
  of silently omitting recognized compressed files. Recover QuickC 2.50's
  876-topic QC.HLP, register its CRC and executable retrieval provenance,
  and rebuild its HELP collection without replacing unrelated content.
  Document SZ/SZDD headers and continuation/compression rules.
- Keep generated bundle sites' JS/CSS cache revisions synchronized with the
  current viewer, including native TextScreen/font/blink and context-help
  assets. Full source regeneration verifies the installed published content;
  defer Cheater 21's four SC 2000 companion texts explicitly.
- Keep SC 2000 angle-bracket prose separate from DOS article detection even
  when it contains apparent `[Rnnn]` markers; do not publish guessed DOS
  topics. Verify preservation of the four complete source payloads, including
  an in-word `FEh`, and clarify text-end/encoding uncertainties and literal
  spaced tag examples in the datasheet. Refresh the roadmap's implemented
  server download/build features without claiming cancellation or SSE.
- Preserve explicit DOS blink and bright-background modes in UHF TextScreen,
  including byte-exact Base64 attribute bits and readable blink masks. Shared
  TVTextScreen animates only flagged glyphs, respects reduced motion, and
  releases timers/listeners on topic changes and window destruction. Add the
  three v6 blink templates after existing resource topics, retaining their
  aliases/IDs; use the standard blink-enabled DOS presentation profile.
  Verify and apply original FA.SCO fonts to v4/v5 PROGRAM inline artwork.
  Extend source-format/UHF documentation and native-byte/pixel regressions.
- Correct Scorpion's shared LZHUF adaptive-tree update for NUL literals;
  verify output against the original DOS decoder and reject payloads that
  require synthetic EOF bits. Convert 53 legacy v6–v14 text screens and all
  seven native FONT.SCO fonts into the existing PROGRAM bundle. Render
  embedded PROGRAM block/box artwork in place with native glyph bytes and
  the original default font, preserving article IDs, row cursors and links.
  Keep three v6 blink-mode screens and indexed SCX palettes explicitly
  deferred. Expand the technical compression/font specification.
- Add UHF `TextScreen` character-cell resources and reusable Base64 bitmap
  fonts. Cells retain native glyph bytes and indexes into existing UHF
  palettes, not PNGs/RGB snapshots. Support readable cell triples and Base64
  blocks: byte-exact DOS character/attribute pairs or independent glyph/FG/BG
  bytes. Shared `TVTextScreen` renders the bits in
  the standard HELP window with addressable rows, search text and managed
  view ownership. Convert 48 modern Scorpion PROGRAM screens from versions
  15, 16 and 21–23, grouping them in Contents without changing native article
  IDs or inventing text/image associations. Validate font lengths, cells,
  palette references and dimensions; document the native v15 resource names.
- Keep explicit UHF source aliases separate from numeric article IDs during
  inline/Contents/menu navigation, including external files and alias cursors.
  `alias=0070` must not open article 70; a declared alias `70` can also differ
  from article 70. Unloaded targets expose `?file=...&alias=...` and the server
  resolves that namespace before redirecting to the canonical article/line.
  Rebuild the search alias cache without dropping aliases that collide with
  IDs. Added browser-helper/event, public-URL and cache-upgrade regressions.
- Convert the SC 2000 `txt` catalog retained in v21 `TEXTY.DAT` through the
  existing Allegro reader and HELP window. Index/Contents entries retain the
  original row cursors, including duplicate captions. Preserve all native
  descriptor fields and ambiguous comma rows; link the 1,800 cheat references
  specifically to CHEATY and six exact title references within the catalog.
  Do not invent links to missing LIB attachments or treat the four unverified
  SC 2000 prose objects as DOS marker articles. Report their names separately
  from actual resources. Added source-scoped link/cursor regressions.
- Document SC 2000 companion text/catalog token boundaries, short title
  references and ambiguous comma-bearing rows without inventing link or
  encoding semantics. Track the remaining HELP audit scope separately from
  the historical application roadmap and deferred graphics work.
- Reject incomplete Scorpion/Allegro LZSS chunks and mismatched uncompressed
  lengths instead of publishing partial articles or reading compressed bytes
  as plain text. Validate objects before resource filtering, remove the
  lenient placeholder option, and propagate errors for recognized DATs through
  source selection so damaged files cannot silently disappear in a rebuild.
  Added malformed-chunk/container, native-corpus and safe publication/retry
  regressions; clarified length/boundary rules in the technical datasheet.
- Retain Game-Cheater's embedded Pc-Fand help in its existing Nápověda bundle
  so original links into that range can open their actual text. Resolve the
  first physical name/mask match with native Latin2 byte folding, not the
  nearest duplicate title or collapsed whitespace. Forward empty named
  records to their following text through real source aliases, preserving
  Index/Contents labels and skipping empty slots in page navigation. Hide
  native leading description lines and open `root` as help Contents. Added
  mask, literal-markup, alias/bundle and complete-source link regressions;
  documented the byte lookup and display rules.
- Preserve Game-Cheater's authored single/double frame glyphs instead of
  rewriting every table below a double header. Follow Pc-Fand's signed
  record count, including empty tables and unused slots; reject partial or
  count-truncated records rather than clamping/deriving counts. Memo reads
  distinguish absent/empty fields from invalid offsets, incomplete payloads,
  pointers and cycles back to the first page. Incomplete index/memo pairs
  fail conversion. Added page-edge, noncontiguous-chain, corpus and staged
  publication/retry regressions; expanded the technical datasheet and removed
  its obsolete standalone export script. Native topic/link identities remain.
- Resolve older TDH overlapping contexts by complete consumed source-byte
  ranges, including page headers, raw target WORDs and split literal nibbles.
  Remove caption/substring-based alias ownership and its diagnostic fields;
  all 11 TD 1.0 aliases retain their verified targets. Identical text on an
  unrelated earlier page cannot steal a link, and unconsumed contexts remain
  readable independently instead of receiving a guessed redirect. Added
  duplicate-text, byte-boundary and unresolved-overlap regressions; native
  text, hotspots and existing navigation are unchanged.
- Correct runtime HELP hotspot boundaries against the original Profiler and
  TD 4/5 line routines. Profiler allows a label to end at column 48 even
  before NUL or CR/LF; newer TD retains its own lookahead reservation. A NUL
  inside a label ends the visible C string, not the encoded label: consume
  through its closing caret, preserve subsequent hard breaks and reject a
  missing caret. Project links only onto displayed cells. Added native edge
  vectors and full-reader regressions; existing TDH/TFH corpus output stays
  intact and the byte-level datasheet now distinguishes the runtime profiles.
- Preserve word separators across inline tags in flowing FreeDOS HTML text.
  Defer collapsible whitespace at its original style/link boundary until the
  next visible text, discard it at block boundaries, and retain non-breaking
  and other Unicode spaces. The original memory-management heading now reads
  `DOS Extenders:` rather than `DOSExtenders:`. Preformatted text, topic IDs,
  index/Contents and all real link/fragment destinations stay intact. Added
  parser-chunk, boundary/Unicode, corpus and real Chrome whitespace checks.
- Preserve the destination line of genuine source context aliases in shared
  UHF export, inline/index navigation and cross-file links. Alias jumps now
  reach the native cursor inside the article instead of losing it at the
  article heading; explicit line targets still override the alias. The public
  server resolves symbolic as well as numeric aliases, retains QuickHelp's
  context-case rules, and redirects to the canonical article with its line
  without creating duplicate search/sitemap topics. Rebuild the old alias
  search cache automatically; source HELP files and user data are unchanged.
- Explicitly defer Windows HLP graphics and image-region links in `TODO.md`.
  Keep the completed HC31 text reader and retained picture payloads unchanged;
  remove the unfinished image/hotspot implementation rather than shipping it
  as supported conversion.
- Convert verified HC31 Windows HLP articles rather than showing only their
  HLX keyword labels. Decode bounded paragraph metrics, tab stops, table
  cells, font/style changes and native inline links through shared UHF.
  Keywords now open actual native article IDs/cursor lines, including the
  complete `\fonttbl` description, parameters and See Also links. Preserve
  real context-hash/external identities, browse navigation and non-scrolling
  headings; never redirect old keyword ordinals into unrelated articles.
  Prefer a same-stem HLP over its index-only HLX in tree/server builds.
  Safely interpret deterministic navigation macros without host execution.
  This is an 80-cell text projection, not Windows pixel emulation: pictures
  are explicit placeholders with retained payloads, and unsupported native
  macros/undefined Symbol glyphs remain reported limitations. Added malformed
  field/control, native-corpus, article/bundle/publication regressions and
  expanded the byte-level Windows Help datasheet.
- Retain Windows HLP originals instead of silently discarding them during
  download. Pin Borland C++ 4.52's matching HLP/HLX pairs and register the
  distinct 4.5 revisions with CRCs and retrieval provenance. Shared exact
  archive-member selection also handles paths inside nested ISO images,
  rejecting ambiguity and conflicting original-file copies. Added bounded
  Windows Help container/B+ tree, LZ77/phrase and native article-record
  decoding, shared with HLX. Independently verified all packet payloads and
  real keyword destinations, including uncompressed HC31's 16-KiB logical
  address stride. Document the binary structures and remaining pixel grammar.
- Replaced compiled-HLX string/pointer guesses with its real Windows Help
  keyword B+ tree. Read all declared branch/leaf records and ignore unused
  header/page memory; validate bounds, counts, depth, cycles and leaf links.
  Keep exact labels, occurrence counts and companion KWDATA addresses in
  index-only bundles instead of fabricated articles, hotspots or Prev/Next.
  Correct Windows ANSI/NBSP decoding without changing DOS glyphs. Added
  independently enumerated corpus, malformed-tree and bundle regressions;
  replaced the partial datasheet with the byte-level index specification.
  Standalone indexes cannot supply article text without their companion HLP.
- Corrected M602 display assembly against the original runtime instructions.
  Preserve hard-row indentation and title/block art; join and wrap soft
  records using raw-byte lengths and native cut spaces before decoding links.
  Use shared positioned hotspots/UHF rendering, retaining all native targets
  and adjacent equal links. Consume one CR suffix, keep literal OEM controls
  and reject incomplete operands/zero-length or unterminated records. Safe
  buffers preserve oversized text and wrapped label fragments instead of
  reproducing native memory overreads or short-string loss. All 201 original
  topics match 3,012 native rows and 406 hotspot coordinates at 78 cells;
  titles, index and source bytes remain intact. Added native-vector, corpus,
  control/bounds/overflow and publication regressions and expanded the datasheet.
- Keep the shared application screen at viewport height while crawlable HTML
  is still present. Long public HELP indexes or documents no longer enlarge
  the desktop during startup and leave newly centered windows offscreen after
  the HTML fallback is removed. Preserve the complete server-rendered text
  and the existing window geometry/restoration flow; no file-specific fix.
  Shared geometry restoration also bounds saved positions to the current
  desktop, including a maximized window's normal restore position. Valid
  positions and saved sizes stay intact on smaller screens or after a stale
  offscreen layout; no local-storage reset is needed.
- Verified Sidekick 2's native help roots: its nine-byte THELP header stores
  context 0 with no text, while the original application's no-app Contents
  and General commands select topic 101. Register that verified start through
  the existing CRC-backed catalog metadata, keep the raw header, topics and
  sentinel identities intact, and retain the generated index. Correct its
  menu release to 2.0 and pin the byte-identical original download/member.
  Pinned WinWorld editions now use the catalog's collection directory instead
  of manufacturing another product/version path; family discovery is unchanged.
  The shared viewer now prefers an available Contents tree over an arbitrary
  first topic when a bundle has no index. Added native-header, source/bundle,
  downloader and default/index/history regressions; expanded the datasheet.
- Corrected THELP default Contents and page navigation. Pascal 4 format 2/1
  uses its verified native context 100 and retains all 129 default aliases;
  short headers with an unknown consumer binding no longer claim context 0.
  Mark stored Contents consistently for legacy and sequential Text records.
  Zero Up/Down words terminate page chains, while genuine topic-zero links
  remain valid. Previous/Next now follow page contexts, not positioned
  keyword-button indices. Preserve those indices in the lossless model and
  all original text/targets. The shared browser alias normalizer also retains
  numeric zero instead of treating it as an empty value; an actual topic 0
  still takes precedence over an alias. Added default/alias/page/bundle regressions,
  technical documentation and executable source provenance for Pascal 4.
- Corrected THELP native context/alias resolution. Genuine aliases now open
  their addressed Text record instead of disappearing or jumping to a
  referring menu row. Use one primary/alias offset map for shared Contents.
  Removed guessed hidden anchors and their duplicate renderer; retain missing
  native links/index entries with explicit offset/failure diagnostics. Generic
  index export and public link URLs keep reader-declared missing targets.
  The existing Help Error MessageBox reports an unavailable destination while
  preserving the current page and recording one broken-link event. Added
  native alias/padding, source/bundle/index/navigation regressions and updated
  the technical datasheet and application help.
- Replaced THELP's border-derived table reconstruction with native sequential
  byte-word flow. Join soft returns, keep authored spaces, treat each hotspot
  as an indivisible word and preserve fixed rows/oversized text. Lay out before
  example projection, using the source width/margin within the standard DOS
  viewport; retain legacy positioned rows, native target/page identities and
  lossless originals. Tables now use the same rule as other flowing text,
  including cells without borders. Updated display-line index/fallback
  coordinates, native vectors, source/bundle regressions and the technical
  datasheet. Dynamic browser-resize and whole-stream page reflow are not added.
- Corrected Pascal 7 THELP `14h` product-name substitution using the original
  Turbo/Borland decoder routines instead of deleting supposed style markers.
  Replace the complete placeholder, including its padding; use the native
  description's Borland profile or the Turbo viewer default. Apply the rule
  before example/hotspot interpretation, reset at each Text record and retain
  the original RLE/token order. Keep lossless source bytes and native targets,
  and preserve unverified control glyphs in other text variants. Added native
  compression, source/bundle and corpus regressions and a byte-level datasheet.
- Corrected THELP Turbo Example handling to use only native `05h` toggles,
  process every inline/repeated delimiter and preserve indentation, blank
  rows and positioned-link row numbers. Keep OEM hearts/triangles instead
  of interpreting them as code markers; restore the Czech Pascal menu arrow
  and remove leaked club glyphs from inline closing delimiters. Carry code
  state through native linked pages rather than physical record order, and
  let explicit markers override filename/heading heuristics. Added control,
  continuation, link/bundle regressions and a byte-level technical description.
  Rebuilt C++ bundles also use their already-verified manifest titles instead
  of generic names or filename stems in the Help Files catalog.
- Corrected THELP text decoding to consume the upper half of the last byte
  instead of dropping final characters or line breaks when a record has no
  end marker. Restore complete positioned link labels; all 93,142 physical
  text records match an independent bounded C nibble reference. Preserve
  native records/targets, treat zero-valued lookup entries as line breaks
  and reject invalid repeat codes/tables and incomplete final operands.
  Added grammar, corpus, link/bundle and staged failure/retry regressions
  and expanded the technical format specification.
- Bound THELP fields, NUL strings, counts and used compression operands to
  their own records. Incomplete records/headers no longer return partial
  HELP as opaque trailing data; retain verified all-space terminal padding.
  Validate the administrative signature, known format/compression values,
  prefix-compressed index lengths, IndexTags byte lengths and context offsets.
  Cuts at a complete record boundary still fail if declared text lies beyond
  EOF. Correct the
  long format-4 FileHeader instead of reading it as five bytes and applying
  invented geometry: Turbo C 2.x retains its stored 50×15 screen, Contents
  context 100 and genuine context-zero alias. Added malformed/variant/
  staged failure-retry/bundle regressions and expanded the technical datasheet.
  Rebuilt TC bundles also pick up their already-registered edition titles.
- Corrected NG MENU addressing using the original descriptor-offset field
  and per-caption WORDs, with bounded shared/unsorted strings and an explicit
  empty end descriptor. Preserve authored caption cells, padding, NBSPs,
  duplicate/blank/symbol-only slots and See Also order instead of replacing
  captions with child titles or removing labels without targets. Caption
  carets and FFh stay literal, distinct from body escapes/RLE. Original NG
  relocation/plain-output routines verify all 120 menus and 14,551 captions;
  retain every source record/target. Added addressing, bounds, caption,
  source-order, bundle and corpus regressions; documented the native table
  and plain-caption grammar without format-specific viewer code.
- Corrected NG text and SHORT link ranges against original Norton Guides
  1.00/1.02/1.04 instructions. Use one byte-cell decoder rather than separate
  raw/styled parsers: attributes replace each other and equal values toggle
  back to normal, unknown escapes keep their folded character, and literal
  OEM controls become glyphs instead of disappearing or breaking rows.
  Preserve bounded numeric-operand results and all unsigned space runs.
  SHORT links cover the entire row, including leading/inter-column padding
  and descriptions; derived labels retain those words too. All 509,785 body
  rows and 17,967,220 logical character/attribute cells are verified, with
  original viewport and longer-tail captures. Keep every one of the 21,309
  records and 36,265 positioned targets; no old IDs/paths or file-specific
  fixes. Added native vectors, whole-row/glyph/bundle/corpus regressions and
  expanded the pure technical datasheet. Shared viewer styling remains;
  native hardware blink/theme and separate prompt grammars are not claimed.
- Hardened Norton Guide/Expert Help records, MENU/SHORT/see-also tables,
  declared strings and exact record-target pointers. Damaged guides now fail
  staged conversion rather than publishing partial topics or guessing a new
  root; existing HELP/catalog survive and retry works after repair. Preserve
  valid empty records, shared/unsorted SHORT text, cycles, opaque padding and
  LONG-next EOF terminals without removing source links. Standardized the NG
  reader on supplied bytes and shared `read_path()`, fixing stale headers on
  reuse and DOS BACKUP NG inputs that previously reopened the raw container.
  All 58 originals and their 21,309 normalized topics remain unchanged.
  Added malformed/empty/pointer/transport/staged regressions and a byte-level
  datasheet with bounded decoding and explicit unknown fields.
- Corrected TVHC source parsing: recognize case-insensitive topic commands
  and native token spacing, reject symbol redefinitions/malformed headers
  with source-line diagnostics, and honor numeric context replacement without
  losing surviving aliases or old symbolic names. Match the original mutable
  brace-escape cursor; unfinished references and source buffer/field overflows
  now fail instead of publishing partial text. Keep unresolved FFFFh targets
  with explicit diagnostics rather than silently dropping the references.
  Only a standalone 1Ah ends input, not a literal arrow starting a text row.
  Detect the first real command rather than quoted/embedded examples in other
  help formats, including after long comment preambles. Full reconstruction
  of the BP7 demo matches all 18,749 original bytes, 55 topics and 47 links.
  Added source grammar, limits, replacement, exact-reference and staged
  failure/retry regressions; expanded both source
  datasheets with pure technical rules.
- Corrected FBHF/TVHC paragraph rendering against the original HELPFILE.PAS
  row algorithm and bounded native execution. Apply Wrap at the standard
  viewer's 46-column width before normalizing non-breaking FFh cells;
  preserve authored spacing and CR gaps without invented indentation or
  terminal blank rows. Reuse the shared Turbo Vision paragraph layout and
  positioned hotspots instead of inserting 02h controls into literal text.
  Both reference samples match all 1,075 native rows and retain all 87 links.
  Added wrapping/non-breaking/fixed/empty/range/literal-byte and corpus
  regressions and staged-server failure/retry coverage; documented the byte
  algorithm and its native Pascal boundary limits. Adaptive UHF reflow
  remains separate work.
- Verified Text602/Calc602's native HELP screen-font resources and literal
  HelpViewer.Draw cells. Replace row-density glyph guessing and Kamenicky
  fallback with the common Software602 font table: Czech/Slovak keyboard
  charts, Greek/math symbols, blocks, shadows and even isolated frame pieces
  now retain their proper glyphs. 98h is the upper half block, E7h is always
  vertical; low bytes are not graphics-editor style selectors. Keep FFh's
  non-breaking layout and exact link columns. Also correct the shared rounded
  corner positions and small placeholder marks in K602/T6HLP. Added complete
  high-table, context-independence, low-cell/link and real-chart tests; expanded
  the technical font specification with verified resource layout and explicit
  unknown/revision-dependent low pictograms.
- Decoded Text602/Calc602's real native THelpTopic persistence: count-prefixed
  Size/Wrap/Text paragraphs, not an 0Eh-delimited chunk grammar. Reuse one
  bounded topic-field reader with FBHF. Remove numerical edge-control guesses,
  punctuation/tail deletion, invented keyboard subtopics, caption link recovery
  and ±3-column corrections. Native execution verifies all 12,207 rows and
  2,235 one-based START-position links at 78 columns. Preserve authored titles,
  rules, paragraph gaps, fixed/wrapped rows, non-breaking spaces and all links.
  Text602 has 188 real objects (including one unindexed object); Calc602 275.
  Use native contexts and genuine shared-slot aliases, with no old sequential
  ID compatibility. Retain unindexed objects in a disjoint source-address
  namespace. Added native-corpus/layout/range/label tests; rewrote the technical
  datasheet and kept executable research separate. The font verification above
  completes observed glyph mapping; adaptive UHF paragraph reflow and rare
  untranscribed compound pictograms remain separate follow-up work.
- Corrected Text602 3.10/Calc602's EOF lookup: its WORD counts anchor slots,
  not bytes (360/280 slots, rather than only the first 90/70). Resolve links
  through exact absolute topic-object addresses; removed fixed caption
  maps, approximate `offset-33` addressing and unknown-context title guessing.
  Validate full DWORDs, file/table sizes and every populated anchor. Keep the
  index array out of text and restore omitted Calc602 errors, printing and
  terminal screens. Added malformed/shared/duplicate/late-context and staged
  rollback/retry tests; isolated superseded research assumptions in private
  notes. The native paragraph decoding above completes the topic boundaries
  and hotspot-position correction.
- Corrected T602 3.00 T6HLP against the original reader/printer: contexts are
  byte slots 0–255, not slots plus one, and zero-length Pascal rows preserve
  authored paragraph gaps instead of acting as disposable NUL separators.
  Restored title/underline/shadow blocks, keyboard glyphs, mathematical
  characters and FEh shortcut dashes. 04h is italic, not bold; category changes
  reset per row. Native execution matches all 3,360 stored rows and 95,759
  font-byte/category cells, retaining 191 titles/index labels with corrected
  IDs and no old-ID aliases. Validate empty/shared/unsorted directories and
  exact topic/row bounds. K602 and T6HLP now share the verified graphics-font
  decoder without changing K602 output or touching the separate 3.10/C602
  THelpTopic format. Added native-corpus, malformed/empty/style and staged-server
  rollback/retry tests; expanded the technical datasheet and converter notes.
- Corrected M602's native directory against the original M602X.EXE reader:
  entries are context/absolute offset/byte size, followed by a six-byte EOF
  footer, not a six-byte header and delta/sentinel rows. The first error
  context is indexed too, and the last topic ends before the directory.
  Parse each stored range independently; reject incomplete records and links
  instead of publishing partial text or guessing destinations from captions.
  Native lookup keeps directory order, shared payloads and its 9999 error
  fallback. Retained all 201 physical topics and 406 source links, restoring
  padded hotspot cells in 15 topics. Removed FA-density scanning and false
  root-count metadata. Added boundary/shared/order/fallback and staged-server
  rollback/retry tests; rewrote the technical datasheet's fields, endianness,
  examples and Kamenicky table, with research/mapping details kept separately.
- Corrected K602's directory and context identities against the original
  executable: 256 six-byte slots start at 000Fh, not 239 slots at 0075h.
  The first 17 empty slots are not reserved header bytes; populated topics
  now use their real byte-context IDs instead of IDs shifted down by 16.
  No aliases retain the incorrect IDs. Replaced scan-until-invalid parsing
  with exact directory/range checks, including unused size WORDs, empty and
  shared topics. Damaged inputs cannot publish a shorter successful HELP.
- Corrected K602's actual built-in graphics-font table rather than falling
  back to Kamenicky: mathematical/Greek keyboard charts, native block/shadow
  glyphs and FEh shortcut dashes now survive intact. Removed invisible-attribute
  guesses for 96h/97h and invented 8D 0A newlines. Original printer execution
  matches all 1,773 stored rows and 49,016 font-byte/category cells. 02h is bold,
  04h is italic, and 13h is underline; shared UHF spans preserve those states.
  Retained native IDs, all 115 titles and 92 index labels. The shared fixed-cell
  viewer uses the native maximum width of 70 cells with horizontal overflow.
  Unrepresented double-width/super/subscript selectors fail explicitly, and
  untranscribed compound key glyphs remain visible replacement cells.
  Added font/style/native-corpus and existing staged rollback/retry regressions;
  expanded the datasheet with byte tables, font layout, controls and viewport
  rules, keeping conversion/research notes separate. No per-format JS/CSS.
- Corrected Microsoft BW03 against original CodeView reader instructions:
  descriptor WORDs are stored Next/Prev indices, not a screen number and an
  inferred next page; NUL ends the screen and RLE operands are literal video
  cells. High-byte style selectors follow the stored dictionary rather than
  hardwired E1h–F0h values. Native attribute 07h initializes each screen, with
  standard OEM glyph decoding. Removed table-scanning guesses and unused duplicate decoders;
  validate active tables, all navigation/payload ranges and complete repeats
  without requiring 40 reserved slots or sorted/unique menu destinations.
- Export BW03's formerly omitted plain-text command summary to standard
  Contents/Index topics, preserving its separate NUL/form-feed grammar and
  common page navigation. All 68 original indexed screens remain unchanged;
  each inspected source gains its native summary. Added corpus, controls,
  compact/shared/menu-order fixtures and real staged rollback/retry tests.
  Expanded the datasheet with corrected fields, byte examples and summary
  boundaries; implementation/research details remain in private RE notes.
- Hardened QuickHelp LN section/topic/context bounds, Huffman trees,
  dictionary/RLE expansion and text/attribute/link records. Corrupt topics now
  fail with database/topic diagnostics instead of becoming empty HELP pages.
  Huffman decoding is demand-driven and stops at exact OUTLEN, preserving
  final-byte padding and handling a single-symbol tree without an infinite
  loop. Corrected the datasheet's former NUL-termination rule: binary topics
  end at OUTLEN and both block lengths must be positive. All 10,190 topics in
  28 installed originals retain identical normalized output. Added malformed
  data, valid compression and staged rollback/retry regressions.
- Validated FBHF file lengths, stream-object types, TP6/BP7 index arrays,
  topic/paragraph/reference bounds and native empty/sparse/shared indexes.
  TVHC source aliases now retain their numeric identities and resolve to the
  shared topic; predefined APP contexts and Word counter behavior follow the
  original compiler. Name scanning respects DOS EOF. Global hotspot ranges
  retain balanced clickable fragments across paragraph/CR boundaries.
  Added field/truncation/alias tests and expanded the technical datasheet;
  both available TP6/BP7 samples remain unchanged.
- Made TDH/TFH block decoding uniformly strict: incomplete page headers,
  literal escapes, hotspot target WORDs, labels/trailers and missing text
  termination now fail instead of producing partial HELP. Removed the lax
  TDH path and bypassed opaque context zero explicitly; valid native row
  limits, EOF slots and unavailable tails remain intact. Added twelve-edition
  truncation/control tests and real staged-server rollback/retry coverage;
  published HELP/catalog are preserved when an input fails. Documented the
  limits of structural validation without an external file digest. Corrected
  TFH 1.0's unused-tail example to 159 total bytes: a two-byte page WORD plus
  157 encoded bytes.
- Fixed TDH/TFH hotspot reflow in the shared decoder: ordinary word wrapping
  moves/splits the label ranges with their cells and retains each source
  target, without title/CRC/file-specific rules. All six older TDH stale
  spans now render complete clickable labels, including multiline byte list
  and Breakpoint window links; native text remains unchanged. Oversized
  pending labels obey the screen-row limit and do not emit phantom hotspots
  below it. Added native/corrected-range, synthetic wrap and real-bundle
  regressions, and documented the character-range algorithm separately from
  the original runtime's stale coordinates.
- Corrected older TDH 1.0/1.5/2.x decoding: 48 visible columns, dictionary
  D/E NUL controls and the older hotspot fit rule. Bounded original TD
  1.0/1.5 execution matches all 19,027 decoded rows and native hotspot spans
  across four originals. Added the three real cumulative-end pages, restoring
  2.x's Hardware breakpoint link. Zero-target carets consume their WORD and
  display Pascal operators instead of truncating German help. Correct stream
  boundaries also fix legacy alias owners. Added native-baseline, control and
  bundle tests; documented six original stale hotspot spans as a remaining
  UHF-reflow limitation, not a falsely passing bounds check.
- Audited all 23 public format documents and separated source-format
  specifications from converter mapping, support status and repair history.
  Preserved implementation/research material in private RE notes and recorded
  the datasheet rule in AGENTS.md. Added TDH/TFH byte layouts and decoder steps,
  exact NG offsets and Allegro old-crypt/LZSS rules. Corrected Text602 binary
  header offsets and anchor-prefix addressing, plus M602's tail offset and
  first-row delta example against the original bytes. Undecoded HLX fields
  remain explicitly unspecified, not presented as extraction heuristics.
- Completed Profiler 1.01 TFH support: the overlapping base WORD enables its
  genuine final page, yielding 367 contexts and all 325 intact hotspots.
  Both TFH revisions now use 48-cell/NUL decoding verified against original
  Profiler execution for all 5,622 native rows and hotspot spans. Malformed
  maps and truncated text fail explicitly; context zero stays blank. Added
  corpus/native-baseline/export tests and corrected the format specification.
- Added six newer Turbo Debugger DOS/Windows/32-bit TDH editions: corrected
  odd context-map counts, overlapping base WORDs, absent zero slots, real final
  pages and native 48-cell hotspot wrapping. All 4,423 links resolve across
  4,602 emitted topics, including TDW's genuine payload-overlap alias. Matching
  original 4.0/5.0 DOS parser execution verifies text and hotspot cells;
  existing older TDH/TFH layout baselines remain intact.
- Registered distinct TASM 2.01, Profiler 1.01 and Sidekick 1.56b originals
  without replacing existing editions or copying exact 2.0 duplicates.
  CRC entries retain verified release/download pages, extraction members,
  search texts and fallback queries through shared `SourceQuery` metadata.
  Providers consume edition queries directly; pinned WinWorld selectors work
  when family-page discovery fails and select only the specified archive
  members. Successful Archive.org item downloads are not repeated per query.
  Added bundled-TASM discovery for Debugger and Archive.org fallback for
  Sidekick; database rebuild preserves provenance. Profiler 1.01 was retained
  for runtime analysis before publication of its complete conversion.
- Registered the English and German Debugger 1.5 HELP from separate images in
  the German disk set with exact downloadable images and fallback search.
  Pinned edition jobs retain their own collection root. Verified TASM 2.0's original CRC, added
  retrieval metadata to the existing row and fixed its bundle-stem collision
  so it no longer disappears behind another Assembler edition.
- TDH Contents follows the native F1 context, not an English title. Verified
  CRC language/home metadata override reader defaults, including German HELP.
  Probe diagnostics report actual map WORD/byte sizes without fictitious
  left/right tables. Server download orchestration invokes each provider/product
  once while the provider handles all retained edition queries.
- Public topic URLs now resolve genuine numeric UHF aliases through the shared
  search index and canonicalize to the real topic, retaining target-line and
  viewer options. This fixes source-context links for all HELP formats, not
  only Sidekick Plus. Alias mappings are file-scoped, rebuilt/removed with
  their bundle and do not duplicate search or sitemap entries; existing index
  caches refresh automatically to populate them.
- Sidekick Plus now resolves its three native common-group redirects through
  standard UHF aliases. Corrected hotspot scopes (zero selects common help,
  nonzero retains the current group), opaque pairing-tag detection and
  row-local style resets; added native category toggles and OEM glyph handling.
  Original reader execution confirms six remaining targets are absent in the
  source, not parser-created failures; all 2,051 authored links remain intact.
  All 11,554 source rows match original printer execution for text/category
  cells. Runtime common-group binding is configurable, with no product/title
  target heuristics; embedded application-string insertions fail explicitly.
- Added a separate, structurally validated Sidekick Plus reader for paragraph
  directories, group-relative screens, scoped hotspot tables and explicit
  pages. The inspected original yields 1,165 distinct UHF topics, preserving
  all 2,051 links and its shared-record alias. Contents/Index and local page
  navigation reuse the common help viewer, without per-format JS/CSS. Six
  source link targets remain absent; native redirects are resolved without
  caption guessing. Added its datasheet,
  CRC metadata and malformed-file/corpus regression tests.
  Published the new Plus bundle through the selected Sidekick staged build;
  all 233 other bundles and every Sidekick original remain byte-identical.
- HelpPC now preserves native 80-column `^` heading centering, `%`/ordinary
  margins and TAB stops after link controls are consumed. Verified all 17,742
  nonempty source rows against execution of the original COM renderer,
  including 1,075 headings. All 1,006 topics and 1,786 links are retained;
  shared UHF spans and display metadata need no format-specific JS/CSS.
  Handles escaped/unclosed tilde controls without rewriting originals,
  rejects unsafe centered margins and retains ordinary text overruns.
  Added runtime evidence, format limits and regression fixtures.
- FreeDOS HTML HELP now resolves same-page, forward and cross-page fragments
  to existing UHF topic/line targets through a two-pass bookmark map. All 112
  available fragment targets resolve; 354 topics and all 4,132 real internal
  links are retained. Named destinations no longer become 154 empty self-links.
  Multiline preformatted bold/link markup is balanced on each UHF row,
  preserving inline state without showing stray closing tags as text.
  Added strict case-collision handling, corpus/edge-case regression tests and
  updated the format specification; original bytes remain untouched.
- Multi-page HELP now exposes Previous/Next in the shared status line through
  TVEvent and real UHF navigation targets, following only the active topic.
  Sidekick 1's terminal `More..` cue becomes a link only when its native page
  separator proves a continuation; text/styles/spacing and context boundaries
  stay intact. Contents still offers direct Page 2, Page 3, etc. selection.
- Added a structurally detected Sidekick 1 `SK.HLP` reader: original contexts,
  explicit intra-context pages, persistent attribute categories, OEM arrows and
  bounded DOS EOF padding. The inspected local file now yields 67 contexts /
  148 pages; the independent 1.56b runtime sample yields 72 / 179. Generated
  continuation navigation has no invented cross-file links. Added its original
  format/runtime-evidence datasheet and strict malformed-layout regression tests.
  Sidekick Plus uses a separate reader; native palette choices live in the
  executable, not the HLP.
- Refreshed the selected local Sidekick library through the staged builder:
  added its newly supported first-generation help and regenerated Sidekick 2
  so its source-defined `<more>` continuation links use the current reader.
  Other published products remain unchanged and the prior library is backed up.
- Added MicroCalc paginated text HELP with runtime-verified highlight/reverse
  colors, page-state resets and margins; added strictly validated DOS text HELP
  and Turbo Prolog `h("…")` records without executing source code. The current
  corpus gains 26 readable originals, including two validated DOS BACKUP
  wrappers decoded in memory. Unknown binary HELP still fails detection.
  Added original-format specifications and positive/negative conversion tests.
- Bundle results/catalogs now count emitted UHF topics, not redirect-only
  source contexts. TDH 1.0 consistently reports 519 topics while retaining
  all 11 alias continuations; single-file, grouped and variant exports agree.
- Removed compatibility-only CRC v1 snapshots and legacy filename/project
  translations from database rebuild. New outputs copy the complete current v2
  manifest. External links require verified source/database identities or exact
  bundle paths; no stem-only or arbitrary-first-version compatibility fallback.
- Repository rules now permit intentional URL/layout/API breaks and require
  updating current callers/docs instead of retaining compatibility layers;
  genuine original-format links and permanent user data remain protected.
- QuickHelp now reads all concatenated LN databases using database-relative
  offsets, recovering 378 omitted topics in four verified originals. Physical
  bundle URLs and first-database IDs remain stable; catalogs include logical
  database names, scoped aliases and context case-sensitivity. Invalid container
  boundaries fail conversion rather than discarding the tail.
- Whole-tree/server export retains the same publication paths and menu versions
  as product-root exports for manifest-declared containers, fixing 78 moved
  Scorpions/Game-Cheater bundles without special product-name exceptions.
- External HELP links no longer confuse original filename extensions or report
  success by opening an arbitrary first topic when the requested file/context
  is absent. Real source links remain intact; defined navigation commands work.
- CRC database rebuild preserves the complete shared manifest, including product
  and release overrides and unknown metadata. Invalid/duplicate records abort
  without overwriting; atomic publication retains the prior file on failure.
- Corrected FBHF signature bytes, THELP signature length/raw-nibble order and
  compiled-HLX corpus/fixture notes. The format index now distinguishes M602
  from other Software602 encodings and documents unsupported original families.
- Product-specific HELP installation now resolves verified CRC/file ownership
  before archive-folder labels, so companion HELP cannot become the requested
  product. Corrected the two verified TASM.TAH records to Turbo Assembler while
  retaining their published paths.
- Accept aggregate opens/active durations for content setup and progress in
  statistics, without collecting selections or account data.
- HELP / DOS Packages is directly available in the administrator menu. HELP
  choices are individual manifest products (Pascal, C/C++, Assembler, etc.),
  not entire vendors. Both selections use shared TVCheckBoxes with TVEvent
  keyboard input, wheel/shared scrollbars and independent masks beyond 32 items.
- Confirmed Apply installs checked missing products and uninstalls unchecked
  installed HELP/DOS packages. HELP publishes a validated staged catalog;
  DOS stages its shared disk and tracks exact package-owned files, retaining
  shared ownership, original HELP, downloads and every private overlay/media.
  Previous HELP/DOS generations remain recoverable; failed DOS publication
  restores the prior shared disk and receipt. Legacy DOS ownership is recovered
  only from available cached archives; unknown ownership fails without deleting.
- DOS archive downloads are a downloader module, sharing public-network
  transport, archive tools and atomic cache publication with HELP providers.
  Removed the separate dos_sources adapter; HTTP(S)/HTTPS policies remain intact.
- Consolidated versioned HELP/DOS/MIDI JSON configuration in thelpviewer/config/.
  Converter and downloader are server submodules; Python imports, manifest
  plugin names, shell adapters, Docker paths and documentation use that layout.
  Existing environment overrides and public HELP/Docs URLs remain unchanged.
- Split permanent storage into data/ (HELP, original sources, Docs, accounts,
  statistics/Hall of Fame, settings and data/dos/users) and rebuildable state
  into var/ (downloads, var/dos/c, MIDI and full-text index). Upgrade migration
  checks SHA-256, refuses conflicting destinations, preserves originals in
  data/migration-backups and keeps public URLs/account IDs/Passkeys unchanged.
- Publish versioned documentation into data/docs while preserving administrator
  edits and added documents; private RE/Audit files stay excluded.
- Fresh server startup no longer downloads/builds all HELP automatically through
  the shell wrapper; administrators confirm the initial content selection.
- Removed old bundled MIDI demo files and playlist documentation from both asset
  trees. Synthesizer/SoundFont assets and server MIDI tracks remain unchanged;
  browser playback tests use their own small SMF fixture.
- Added administrator server-content configuration with selectable HELP build
  groups and DOS packages. A fresh server opens setup after admin sign-in;
  confirmed selections launch background Python module jobs through the API.
  Shared TVCheckBoxes/TVButton views and a TVBarGauge progress dialog need no
  per-dialog HTML/CSS. Hide does not cancel the server operation.
- HELP conversion stages output, validates and rebuilds the shared catalog,
  retains a previous-generation backup and activates only after success.
  Original HELP sources and private DOS disks are retained.
  The server refreshes display names and its full-text/SEO index afterwards.
- Unified bounded public-network transport for HELP and DOS downloads,
  including HTML POST forms, redirects, actual-peer/private-address rejection
  and per-task byte progress. DOS retains its HTTPS-only policy.
- New server archives use var/downloads/help and var/downloads/dos; legacy
  DOS cache migrates without redownloading. Content choices persist in
  data/content-settings.json.
- Extracted callable downloader orchestration, staged HELP builder and catalog
  builder; existing CLI entry points remain adapters, not server subprocesses.

## [2.0.0] — 2026-10-10

- Fixed TVProgram keyboard owner-flow recursion; child input is not sent
  back into the active dialog, restoring Escape and normal key handling.
- Rechecking an already-open Find dialog refreshes global-search availability;
  reactivating the window no longer leaves that option disabled.
- Moved Users' Add User / Save row down one character row, leaving a blank
  row below the profile details; Refresh / Close and the list stay unchanged.
- Arranged Users' four buttons into a 2×2 matrix and extended the user list
  by five character rows, aligned with the bottom of the button block.
- Add User now opens the shared registration-profile form (first/last name,
  nickname, email). An administrator creates a member without a Passkey and
  receives a copyable, account-bound one-hour invitation; the admin session
  stays unchanged. The user enrolls their own Passkey through Login → Register.
- Registration now persists first/last name and nickname with its ceremony;
  invitations for existing managed users reuse the existing enrollment API.
- All email inputs, including Login, use TVEmailValidator. Login also accepts
  valid legacy usernames; email and server validation reject control characters.
- Renamed the default local-development account label to Admin, including
  existing default profiles and active sessions; custom names and DOS data stay unchanged.
- Removed the separate Display name field from Account/Users and profile-edit
  requests. The server derives the account label from nickname, then first/last
  name, retaining the existing label if those fields are empty.
- Fixed TVButton shadows to cover the actual button width, including the lower
  right corner of wide Rebuild DOS C / Rebuild MIDI / Users buttons.
- Connected both application desktops to their TVProgram owner so dialog button
  commands reach the application through TVEvent. Server Configuration Users works.
- Added Add user below the Users list, opening the existing registration-token
  workflow; the new user registers their own Passkey with a one-hour token.
- Added first name, last name and nickname to Account and administrator Users,
  retaining display names, usernames, Passkeys and private DOS storage. Existing
  profiles migrate with blank optional fields, without guessing name splits.
- Email inputs in Account, Users and Registration now use a shared TVEmailValidator
  through TVInputLine; invalid completed addresses are blocked before submission.
- Moved the Server Configuration Rebuild DOS C / Rebuild MIDI / Users row down
  one character row, leaving a gap below the runtime-settings list.
- Made Users one column narrower and its user list two rows taller.
  Private C capacity now rejects non-digit typing/pastes through the shared
  TVFilterValidator; blank still inherits the server default.
- Fixed shared TVInputLine input-broadcast delivery so attached validators
  run during typing and paste, not only when validating a completed field.
- Added administrator Users management with name/email, role, enabled state,
  per-account DOS overlay capacity and protection of the last administrator.
  The founding administrator is permanently protected against deactivation
  and demotion, even when additional administrators exist.
- Account now shows private C usage/capacity; the default overlay is 64 MiB.
  Server Configuration centralizes the default, runtime information and rebuilds.
- Shared root menu placement now keeps right-aligned popups within the viewport.
- Removed Server Terminal, its API and launcher. The shared TVTerminal view remains.
- DOS sources no longer require manifest sha256/archive_bytes; HTTPS and archive
  extraction limits remain enforced. Existing prepared C disks are not rebuilt.


- Separated Login from Account profile settings. Signed-in users can update
  their display name/email through owned TVision controls; role is read-only.
  The API restricts edits to the session owner and preserves username, account
  ID, Passkeys, sessions and private DOS storage. Updated emails work for login.
- Enabled recoverable DOS/MIDI rebuilds for signed-in administrators on the
  public server, retaining host/origin/session/role checks and stricter local
  development proxy rejection. Members cannot rebuild; confirmation is required.

- Refreshed viewer JS/CSS cache-version URLs for the complete frontend update,
  including the right-aligned Login/account menu. Documented coherent asset
  deployment to avoid mixing current HTML with an older set of scripts/styles.

### Server
- Isolated gzip/JSON/UHF/Docs read failures to their own sources, preserving
  healthy full-text search, public pages and sitemaps. Warnings name the failed
  source in the API/log; repaired or removed sources recover automatically.
  Completed per-file data stays available during indexing; only initial
  unavailability and failed individual files return retryable 503 responses.
  Database errors remain fatal. Original HELP/Docs files are never deleted.
- Public HELP previews now identify original diagnostic messages as reference
  documentation, rather than presenting them like website errors. All
  non-empty topics use the same indexing rules; removed the text-specific
  "no help available" exclusion. No filename, topic ID, language or diagnostic
  wording determines indexing. Original HELP bundles and links are unchanged.
- Public HELP/Docs URL encoding/order variants now permanently redirect to
  sitemap-compatible URLs, preserving viewer options and browser fragments.
  Missing content is still 404. Browser error pages now return HTTP 404 with
  `noindex` instead of an indexable 200, while keeping the TVision MessageBox.
  Public page rendering runs in FastAPI's thread pool rather than blocking
  the event loop with synchronous index/file reads.
- DOS source entries now support a `files` list with CP437/CRLF text lines or
  strict Base64 bytes, relative to `target`, with path/count/size validation.
  On a fresh install, configured content overrides its archive counterpart;
  existing shared disks stay frozen until explicit rebuild/installation.
  Removed DOS `allowed_hosts`; direct/form/redirect downloads accept public
  HTTPS hosts with private-peer rejection, size limits and SHA-256 pinning.
- Unified root and package `files` definitions, both supporting text/Base64.
  AUTOEXEC.BAT is a normal root entry; legacy initial_files/boot-file keys
  are rejected with a migration message. Existing C disks remain untouched.
- Removed the unused `page` field from the Norton Commander DOS source;
  its download URL and inner disk-image selection are unchanged.
- Added local-development-admin DOS/MIDI rebuild endpoints with exact scope,
  origin/session guards and recoverable backups. DOS keeps user overlays and
  cached archives; MIDI stops its old downloader before replacing tracks,
  covers and SQLite catalog and re-reading the configured sources.
- Added opt-in local Docker auto-login without WebAuthn, with a loopback-only
  port override, separate development accounts/sessions and rejection of
  public auth origins, public base URLs and proxied/cross-origin login requests.
- Kept Docker's Python bytecode cache enabled for imports/startup, relocating
  it to `/tmp/thelp-python-cache` outside the bind-mounted project. Agent test
  instructions require no-cache runs and cleanup after success or failure.
- Removed the ineffective default CONFIG.SYS from the DOS manifest. Documented
  DOOM's disabled source sound settings and its Sound Blaster setup, without
  overwriting users' or the shared disk's existing game configuration.
- Added DOS Prompt opens and active-duration buckets to tool statistics,
  excluding startup, explicit pause, inactive windows and hidden tabs.
  Page-exit lifecycle notifications no longer double-count window opens.
- DOS now boots from a metadata-only ZIP and reads C files on demand in
  gzip-capable 64 KiB chunks, with hash/account guards and private-file isolation.
  Unread shared files are no longer transferred merely to save an overlay.
- Private DOS files now live under each account's regular filesystem revision
  directory; SQLite retains metadata/deletions. Legacy BLOB overlays migrate
  automatically, and failed saves preserve the prior snapshot.
- Added admin-only Server Configuration for a persisted private-overlay quota,
  default 128 MiB excluding shared software. Added configured DOS game sources,
  Volkov Commander and an optional disabled Norton Commander source.
- Added a generated software guide and an explicit non-overwriting DOS source
  installer. CONFIG.SYS may be stored as a normal file but is not interpreted
  by DOSBox's internal shell.
- The prepared DOS C drive is now initialised only once, with a completion
  marker preventing later startups/configuration changes from rewriting it.
  Added BlockDrop, Sudoku86 and Zmiy under `C:\GAMES`, preserving their
  source archives/licence notices from the FreeDOS repository.
- Fixed DOS boot ZIPs omitting parent directories for installed software and
  overlays. DOSBox's extractor now receives directories before their files,
  preventing the FreeDOS `APPINFO` extraction failure and startup timeouts.
- Added DOS Prompt software preparation from a hash-pinned ZIP/IMG source JSON,
  a shared C drive and private file overlays tied to Passkey sessions.
  Overlay saves retain deletions, enforce quotas and reject concurrent stale
  writes. Approved ISO/floppy uploads are private to their account; DOSBox
  enters native secure mode before accepting commands.
- Renamed the MIDI source manifest's URL list to `pages`, updating source
  loading, validation and documentation. Source IDs, download paths and
  previously downloaded tracks remain unchanged.
- Serve the MIDI SoundFont as precompressed Brotli when supported, with an
  uncompressed fallback and immutable caching for its versioned URL.
- Temporarily disabled VGMusic in the MIDI source manifest and removed its
  local tracks and catalog rows; disabled sources are hidden from MIDI APIs.
- Added aggregate per-track MIDI play counts and listened minutes to server
  statistics, excluding time spent paused.
- Expanded Karl's DOS MIDI source from its D page to every available numbered
  and lettered catalog page. All MIDI sources now configure `pages` as a
  plain URL list, and redundant extraction defaults were removed. Existing D
  downloads retain their source ID.
- Added configurable HTML MIDI sources, background/resumable MIDI and ZIP
  downloads into `var/midi`, per-track SQLite metadata and cover references,
  and local MIDI APIs. New HTML sources can use JSON-configured CSS selectors
  when the table/link/heading extraction layouts do not fit.
- Added pending MIDI entries to the catalog and a priority endpoint, so playing
  an undownloaded track moves its source ahead of the normal download order.
- Switched statistics event dispatch to Python `match/case` while keeping
  legacy HELP-open aliases and invalid-event responses unchanged.
- Moved Passkey login, registration, token and session endpoints into an auth
  router and grouped HTTP routers under `server/routes/`, preserving their URLs
  and cookie/origin rules.
- Moved statistics event validation, summary and Hall of Fame API routes out
  of `app.py` into a dedicated router without changing endpoints or storage.

### TVision
- Search and index progress show skipped-file counts and refresh results after
  a background index update. Updated the native Search HELP instructions.
- Added local-only Rebuild DOS C / Rebuild MIDI account-menu actions with
  confirmation and shared progress views. DOS saves/closes its current window
  first; MIDI playback stops before reset. Hiding progress does not cancel jobs.
- Renamed Account / Passkey to Account. Colors remains available to ordinary
  users; menu tests now guard this independently of administrator permissions.
- Updated the native HELP bundle, Contents/Index and view-owned hc contexts
  for accounts, registration, configuration/rebuild, DOS, terminal and grid;
  refreshed outdated MIDI, global search and statistics instructions.
- Fixed passive frames of shared windows without scrollbars updating only
  their left side, including DOS Prompt. Window dragging now caches bounds
  and coalesces position writes per animation frame, retaining the final
  mouse-release position and cancelling pending work on destruction.
  The mover now reuses shared frame-state drawing instead of leaving a
  single-line bottom border behind after moving a window.
- Added DOS Prompt Zoom 2× / Zoom back through shared window geometry, limited
  by the available desktop. Successful C-drive autosaves no longer overlay
  the DOS display with a cloud-save notice; save errors remain visible.
- Added a shared right-aligned account menu: Login for guests, display name
  with Account/Passkey, color configuration and Sign Out for signed-in users;
  admin server settings/tokens moved there from system/Help menus.
- Added DOSBox-style Alt-Enter fullscreen and Alt-Pause (Alt-F16 on Mac)
  pause/resume shortcuts, plus THelpViewer's Ctrl-Alt-R restart confirmation.
  Commands use TVEvent and are not also forwarded to DOS as keystrokes.
- Fixed DOS `EXIT` or an unexpected emulator stop leaving a stopped canvas in
  native fullscreen. The control
  menu shortcut now remains available after the emulator stops; restarting
  a running DOS session retains fullscreen. Rapid fullscreen re-entry no longer
  gets blocked by a delayed fullscreen-change notification.
- DOS Fullscreen now uses native browser fullscreen for the DOS canvas alone,
  without the TVision menu/frame and without changing window geometry.
  Ctrl+Alt+M leaves fullscreen before opening the DOS control menu.
- DOS Prompt now participates in `#tv=` workspace links, restoring geometry,
  stacking/active window and Pause state without exposing commands or private
  media/account IDs. Restoring starts a new emulator, not a CPU/RAM snapshot.
- First-time DOS downloads/extraction now show a shared initialization dialog
  with progress. Worker-denied browsers report unsupported mode by default,
  without silently downloading the full C drive.
- Made the entire DOS Prompt background black using the shared window palette,
  and fixed shared growable-window bottom-frame fill without a scrollbar.
- DOS startup now reports disk loading, runtime loading and emulator startup
  separately, with bounded request/script/backend waits. Denied Web Audio
  no longer aborts DOS startup. The full-disk direct backend is available only
  when explicitly enabled in the server's DOS configuration.
- Added DOS Prompt using the shared `TVWindow` frame and an embedded WASM
  DOSBox view, with TVEvent keyboard/mouse input and a contextual menu for
  pause, restart, cloud save, CD/floppy mounting, eject and fullscreen.
  Inactive/hidden sessions pause automatically. C is saved every minute and
  before normal close/restart and DOS `EXIT`; guests have an unsaved temporary
  disk. The shared close control waits for mouse release before closing DOS.
- HELP Files and Docs menu entries now retain real public URLs after the
  server-rendered catalog is replaced. HELP indexes, Contents outlines, inline
  links and `<more>` links also expose file/topic URLs while ordinary clicks
  continue through `TVEvent` without reloading the viewer. Browser-modified
  clicks can open those links in another tab, and public topic URLs preserve
  their optional target line.
- Removed the Downloads button from the CD/MIDI Player's More panel, widened
  its Filter input, and made Random next track span the full panel width.
  Background downloads and their automatic progress dialog remain unchanged.
- Version the SoundFont URL and record MIDI script, download, SoundFont-load
  and Play-to-ready timings so first-play delays can be diagnosed.
- Reduced the first MIDI playlist click's work: shared list selection now
  updates only changed rows after the initial render, and the player avoids
  reselecting the same row. `TVListBox` now resolves the clicked row from the
  event target before falling back to per-row geometry checks. The player
  starts loading its SoundFont when opened instead of waiting for first Play.
- Fixed clicks on the shared vertical and horizontal scrollbar tracks: the
  position calculation now reads the track from `axisMetrics().axis`, so lists
  and document windows can jump to the clicked position again.
- A single click on a different MIDI playlist row now starts that track, rather
  than changing only its title and cover. Choosing a pending download stops the
  old audio while it waits; arrow-key navigation still only changes selection.
- Added the shared `TVHistory` dropdown to the MIDI Filter and a MIDI playback
  category to Server Statistics.
- Retry the MIDI catalog automatically after a temporary server/API failure,
  so an open player recovers after the server restarts.
- Fixed MIDI Pause/Play to resume the current position without resetting the
  progress gauge, and separated adjacent transport buttons by one character.
- Fixed the MIDI playback gauge jumping to 100% when FluidSynth initially
  reports zero total ticks; it now uses the parsed MIDI file's final tick.
- Removed the legacy Commons/ToBeFree MIDI preset buttons, replaced oscillator
  tones with FluidSynth and a General MIDI SoundFont, and added automatic
  next-track playback with a Random next track checkbox under More. Large MIDI
  files now play through the synthesizer rather than scheduling every note as
  a separate browser oscillator; audio is resumed on the Play gesture for Safari.
- Made the MIDI playback gauge seek to the clicked position, moved the
  pending-download cloud to the end of each playlist row, and fixed `TVImage`
  binding so available game covers actually appear.
- Replaced the MIDI Player's hardcoded demo playlist with the server catalog
  and added a shared `TVImage` view for source-provided cover art.
- Widened the MIDI transport controls, aligned game names in the playlist, and
  marked pending tracks with a cloud. Added a hideable Download progress dialog
  using shared gauges and replaced the URL field with a game/track filter.
- Moved the Building Global Index dialog's Hide button down one text row.
- Kept the completed global-index gauge visible briefly at `100%`, so fast
  rebuilds show a solid `█` bar instead of only the initial shaded track.
- Changed the shared `TVBarGauge` to fill a shaded `░` track with solid `█`
  cells, including the global-index and HELP-loading dialogs. MIDI playback
  now uses the same TVision gauge instead of a separate CSS progress meter.

### Downloader
- Limited HelpPC archive extraction to the six converted `.TXT` databases;
  its original `.DOC` and `.NDX` are no longer copied into `sources/`.
- Removed the invented `Candidates/` layer: DOS reference sources and HELP
  bundles now live directly under their product names. Renamed the opt-in
  build group to `dos-reference` and kept group selection separate from paths.
- Collected the QuickBASIC 4.5 Advisor and runtime-error `.HLP` files from
  their original floppies, restoring the targets of 519 cross-file links in
  `QB45QCK.HLP`; registered both files by CRC32.
- Added verified Archive.org search queries for the MS-DOS 6.22 and
  QuickBASIC 4.5 products. Search results use the same exact HELP-member
  selection and product directory as pinned downloads, avoiding
  duplicate or unintended default-build output.
- Added `./thelp.sh build --with-dos-reference` to build the default HELP groups
  and the four opt-in DOS reference products in one pass without discarding
  unrelated opt-in bundles.
- Added an opt-in `dos-reference` build group that converts the four downloaded
  DOS reference products to UHF bundles and registers them in Help Files.
  Corrected their CRC database product associations; the default public build
  still excludes this group.
- Added pinned downloads for MS-DOS 6.22 command help, QuickBASIC 4.5,
  HelpPC 2.10, and English FreeDOS HTML Help. The downloader selects the exact
  original files from archives under `sources/<Product>/`, outside the default
  public build pending format and redistribution review.
- Expanded Microsoft KWAJ/LZH single-file payloads from DOS installation disks,
  so `HELP.HL_` is collected as a readable `HELP.HLP`.

### Formats
- Replaced value and type dispatch chains in HELP readers and bundle export
  with Python `match/case`; conditional range and parser-state checks remain
  `if/elif` where that form expresses their behavior more clearly.
- Matched HelpPC topic keys and `~key~` links after collapsing repeated
  spaces, as specified by the original `HELPPC.DOC`, without changing their
  displayed text.
- Exported HelpPC's six original `.TXT` databases as six individually named
  bundles, preserving links between them. Recovered QuickHelp links with a
  misspelled source filename only when a sibling context matches uniquely.
- Identified QuickC 2.50 `QA.HLP`/`taw080554` as an intact two-context
  search-order stub and gave its catalog entry a descriptive title.
- Added HelpPC 2.10 source conversion: six CP437 text databases export
  1,006 topics with cross-database links, index and Contents.
- Added a FreeDOS HTML Help importer for `HHSTNDRD.ZIP`, converting its 354
  pages and relative links into one UHF bundle. Registered both formats and
  the downloaded products in the CRC32 help database, while retaining their
  exclusion from the default public build pending license review.
- Preserved Microsoft Advisor's qualified QuickHelp links such as
  `OS2.h.overview`, `WIN.h.contents`, and `LAN.h.contents` as real external
  HELP links; optional databases that are not installed are no longer rendered
  as non-interactive bold text
- Promoted **Borland Turbo Debugger TDH / Turbo Profiler TFH** from a
  diagnostic-only path to a decoded reader path for the known sample families,
  including runtime-aligned topics, hotspots, contents/index export, and UHF
  bundle output
- Added end-to-end bundle export regression coverage for the current TDH/TFH
  sample families, so legacy TDH, later 2.x TDH, and TFH are now checked
  through actual UHF bundle output instead of reader-local decode assertions
  only
- Hardened the TDH runtime decoder to rely on in-stream topic termination plus
  the confirmed 15-line page limit instead of a synthetic next-page upper bound
- Narrowed TDH alias fallback so text matching now runs only for unresolved
  out-of-range alias contexts after structural embedded-start detection
- Extended TDH decode metadata so alias-heavy high contexts now expose exact
  out-of-range, embedded, text-fallback, remaining-unresolved, and empty-
  placeholder context-id lists instead of counts only
- Hardened the TDH reader failure path so structurally matched but truncated
  payloads now raise a clean unsupported/truncated error instead of failing in
  intermediate decode bookkeeping
- Switched TFH format-handler detection to content-based probing in the shared
  exporter registry, so renamed TFH inputs no longer depend on a `.tfh`
  suffix to route into the TFH reader
- Recovered a direct resident TD 2.0 loader/seek anchor: `TD.EXE` opens
  `tdhelp.tdh`, reads the header into `0xA248`, buffers `0x258` words at
  `0x9D94`, and computes topic starts as `2 * header + 2 + sum(sign16(deltas))`
  instead of relying only on file-side inference

### Viewer & UI
- Kept the HELP viewer and generated TVision pages running when the optional
  screen-saver script fails to load; its menu actions then become harmless no-ops.
- Grouped QuickBASIC 4.5 and Extended 7.1 under one Microsoft QuickBASIC
  Help Files menu, with separate version branches and unchanged bundle URLs.
  Archive.org downloads no longer append a release number already present in
  the product directory name.
- Opened Markdown Docs windows wide enough for 80 text/code columns after
  their frame and padding, and rendered soft-wrapped source lines as one paragraph
  instead of orphaning the last word on a separate line.
- Added crawlable HELP/Docs links and a canonical URL to the server-rendered
  homepage, included it in the sitemap index, and restored the public preview
  image and favicon URLs used by search crawlers.
- Closing a Yes/No `TVMessageBox` with [ ] or Escape now returns No, never the
  default Yes action; dismissing the registration-token deletion prompt keeps
  the token valid.
- Register Passkey now shows an Information MessageBox after the server
  confirms the signed-in session, then closes both registration and Login.
  Administrators can list still-valid registration tokens with their expiry,
  select one for copying, and revoke it after confirmation. New token values
  are encrypted in server state; older hash-only tokens remain revocable but
  cannot be displayed again.
- Docker start now rebuilds changed Python dependencies, and Passkey endpoints
  report a missing server dependency as JSON HTTP 503 instead of a generic 500.
- Made Google Search Console verification configurable through
  `THELP_GOOGLE_SITE_VERIFICATION`; the server injects it into public viewer
  pages without baking the token into generated HTML.
- Made `TVLabel` mnemonics focus their linked controls via Alt+letter in dialogs,
  including Search Topics' `~F~ind:` label; the selected search result now shows
  its HELP catalog name below the list, and radio choices use the larger DOS dot.
- Added picture-validated, auto-hyphenated registration token input and
  five-group, one-hour registration tokens; older token formats are rejected
  even when unexpired. Registration errors now identify the failing Passkey
  stage.
- Used the configured HTTPS Passkey origin for public sitemap/robots links
  when no separate public base URL is set, avoiding an HTTP sitemap hint
  behind a TLS proxy.
- Made shared window/dialog Close resilient to Safari omitting a click after
  mouse release on an inactive title control; the normal click still takes
  precedence and Close is dispatched only once.
- Server Statistics retries one transient API failure and reports the actual
  HTTP/network or display error instead of always claiming the API is unreachable.
- Public Docs and HELP search URLs now open their content directly in TVision
  while keeping server-rendered text in the initial HTML for search crawlers.
- Made `/?doc=<path>` the canonical and sitemap URL for public Docs; removed
  the unused `/documents/<path>` and `/topics/<path>` aliases while keeping
  `/docs/<path>` as raw Markdown for the TVision viewer.
- Indexed public Markdown Docs alongside HELP topics in the existing SQLite
  global search. Search results open Docs in the standard TVision document
  window; server-rendered Docs pages and a Docs sitemap make them discoverable
  to search engines without exposing private RE/audit documents.
- Added an HTML overview for each HELP file, linking to all of its non-empty
  topics. The sitemap index now groups overview and topic URLs into a separate
  sitemap for each HELP file; the older numbered sitemap URLs remain available.
- Find and Search Topics now use exclusive, availability-aware radio scopes
  for server-wide and active-window/HELP searching; topic results show their
  source filename on a second line. Shared `TVCluster` now visibly dims
  dynamically disabled choices.
- Added first-admin Passkey bootstrap from a one-hour token logged at server
  startup, name/email/token registration, and one-hour registration tokens
  issued only by a signed-in administrator from a conditional menu item.
- Added server-rendered `/?file=...&topic=...` HELP pages and made these readable
  query URLs the sitemap/canonical targets, while retaining a link into the
  interactive viewer.
- Added administrator-created accounts with one-time Passkey enrollment,
  WebAuthn sign-in, server-side sessions and a shared TVision Login dialog;
  public registration remains closed and Server Terminal credentials are
  unchanged.
- Added crawlable, server-rendered HELP topic pages plus `robots.txt` and
  paginated sitemaps so search engines can discover topics without `#tv`
  fragment or JavaScript execution.
- Fixed inactive window/dialog close controls so they can be clicked directly;
  shortened Find and aligned its history scrollbar with the popup frame.
- Kept `TVButton` drawing generic; ASCII, calendar, color, MIDI, search-result
  and game buttons now render their special faces in their owning controls.
- Added an incremental SQLite FTS5 index of every generated HELP bundle under
  `var/`. Search Topics and Find now offer local/global scope; global queries
  use the server API, open the result's actual HELP file and topic, and show a
  Turbo Vision percentage dialog while indexing is still in progress.
- Added a read-only `TVGridView` with visible/toggleable column headers,
  keyboard/mouse cell selection and shared horizontal/vertical scrollbars;
  Grid Viewer in the system menu demonstrates it.
- Added Server Terminal: a command deliberately started on the server CLI
  streams its output to a Turbo Vision dialog, accepts line input while
  running, and locks input after exit. Each job requires a random access key;
  browser requests cannot launch commands.
- Server Statistics now reveals a shared horizontal list scrollbar when a
  topic or other ranked value is wider than the detail viewport.
- Expanded Sokoban to ten solver-verified levels, retaining its existing
  Hall of Fame. It now also records the reached level when a run ends and
  ranks a higher level ahead of fewer moves at a lower level.
- Replaced unsolvable Sokoban boards with five solver-verified levels and made
  Hall of Fame rank a completed five-level run by total moves. Finishing the
  last level now offers a new game instead of a dead-end Next action.
- Standard windows now zoom on a double-click of the title row, matching
  Turbo Vision's `TFrame` command path.
- Fixed Calendar's Today control to occupy one row, kept inactive dialog
  close controls visible in passive colors, and tightened the Tower of Hanoi
  and Mastermind windows while giving Tron one more row.
- Sokoban now allows Enter to advance after a solved intermediate level
  without an intervening Hall of Fame name prompt.
- Window and dialog close controls now show the pressed asterisk while the
  mouse button is held and close only on release over the control.
- Unified dialog Close/Cancel from Escape and `TVDialogManager` with the
  existing `TVDialog.handleEvent()` command path. Pressing a default
  `TVButton` now sends its command through `TVEvent` instead of synthesizing a
  browser click. HELP Find adapters and Docs editors are retained and cleaned
  up by their `TVWindow` instances, not by DOM element properties.
- Contents Outline now activates its target directly from the selected
  `TVOutline` node instead of synthesizing an anchor click. HELP outlines and
  window scrollbars are retained by their `TVWindow` instances and cleaned up
  with the window, not stored on browser elements. Generated-page Close routes
  through `TVWindow.handleEvent()` while preserving its `index.html` destination.
  Added an opt-in Safari/WebDriver regression for File Open history and HELP
  window closing.
- Routed Markdown Docs links through one `TVEditor` click-to-`TVEvent` bridge
  and dialog backdrop closing through `TVDialog.handleEvent()`; Tile/Cascade
  now places windows through the shared resizer so geometry and zoom restore
  stay in sync. File Open's two-column keyboard navigation again follows its
  `TVListViewer` event path, with its row count defined in JS. MIDI display
  colors now follow named child views rather than CSS child positions.
- Routed list selection, activation and outline expansion through the shared
  `TVListViewer.handleEvent()` path. HELP topic links now travel through
  `TVHelpViewer` and their owning `TVHelpWindow`, including Contents and Index
  links; the link target metadata remains intact. Removed unused page Back/Search
  DOM hooks and menu key-code markup, read MIDI expansion and History visibility
  from `TVView` state,
  and kept History's outside-click listener active only while its popup is open.
  The three-cell History icon is drawn by `TVHistory`, not by command-name
  branches in the generic `TVButton`.
- Shared `TVWindow.zoom()` now uses the existing resizer for HELP and Docs
  windows, preserving one zoom/restore path for geometry, glyphs and stored
  state instead of separate window-manager DOM mutations.
- Cached each menu's rendered toggles, popups and selectable items when
  `TVMenuView` binds them. Keyboard and mouse navigation now uses those retained
  references instead of repeatedly querying its own DOM structure.
- Added DOS Navigator-inspired Projector screen saver to both viewer menus.
  Screen savers now inherit `TVView`, receive mouse/keyboard input through
  `TVEvent`, and restore focus when dismissed; the browser implementation
  reveals the live page through the moving aperture.
- Moved menu/submenu, status-line and cluster decisions from `data-tv-*`
  attributes into retained `TVMenuItem`, `TVStatusItem` and `TVCluster`
  objects. HELP window navigation and URL state now live on `TVHelpWindow`
  instead of HTML datasets; binding flags stay in JS. DOM attributes remain
  for view binding, browser hit testing, generated-page metadata and dynamic
  content links, but no longer own these commands or window/cluster states.
  `TVFrame` now owns its title-control commands, including game Hall of Fame,
  so `TVWindow` and `TVDialog` no longer read commands back from HTML.
- Routed menu mouse movement, clicks and keyboard navigation through
  `TVMenuView.handleEvent()`. The browser menu controller now only translates
  DOM input to `TVEvent`; selected commands propagate through the view owner.
- Docker startup now reads HELP bundles at their original paths before the
  direct bind mount, making offloaded macOS files locally available without a
  second copy.
- Fixed menu commands losing their `TVMenuItem` on click after the linked-menu
  refactor. HELP, Docs, dialog and game entries again deliver their file or
  action to the application instead of trying to load an empty filename.
- Rebuilt menu composition around the original Turbo Vision model: `TVMenu`
  now owns a linked `TVMenuItem.next` list and default item, `TVSubMenu` owns a
  nested menu, and `NewItem`/`NewMenu`/`NewLine`/`NewSubMenu` provide
  source-like construction. Both viewer modes now use the shared `TVMenuBar`;
  callers pass raw `~hotkey~` labels and accelerator text instead of generated
  HTML, command payloads no longer leak through `TMenuItem.param`, and dynamic
  enabled state is updated through retained menu objects rather than DOM
  selector scans.
- Unified active-time statistics through the existing `TVDialogManager` for
  HELP windows, Markdown documents, dialogs and games. Time now accumulates
  only while the managed target and browser tab are active, pauses across
  window/tab switches, resumes on return and is stored only as a coarse
  interval. Game discovery now uses `TVGameDialog` instead of a duplicated
  hard-coded game-name list.
- Fixed Server Statistics returning HTTP 500 from Docker Desktop bind mounts:
  the small aggregate SQLite store now uses the portable rollback journal
  instead of WAL shared-memory sidecar files.
- Expanded anonymous Server Statistics with active-visit duration intervals,
  dialog/tool opens, search outcomes without query text, link outcomes, game
  results and duration intervals, Navigation Timing, coarse LCP/CLS/INP and
  HELP download/decompression/render timing. Visit environment counters now
  include coarse orientation, pointer type and reduced-motion preference; no
  exact timing or persistent visitor identifier is stored.
- Added a source-shaped System Information utility to both viewer modes. The
  standard `TVDialog` uses category/detail `TVListBox` controls and OK/Refresh
  buttons to show local application, browser, display, locale, storage and web
  capabilities plus live server version and HELP/Docs catalog sizes. Merely
  opening the dialog does not add those details to visitor statistics.
- Corrected Puzzle's Turbo Vision `0x71` highlight so it applies both the
  light-gray background and blue foreground instead of drawing blue letters
  on the blue board. Restored Tetris's shared `[H]` Hall of Fame title
  control. Dynamic `TVWindow.drawContent()` updates now redraw the shared
  frame, so asynchronously loaded Hall of Fame rows retain both side borders.
  `TVInfoBox` side cells now keep the owner palette background during row
  hover, preventing Ludo's Players highlight from painting beneath its frame.
  Positioned views now use `TVWindow`'s client viewport as their coordinate
  origin, fixing Find history's one-cell list/scrollbar offset; the taller Find
  client also leaves room for the popup shadow. ASCII Chart again uses two
  native `TVDialog` sections with a `╟──╢` separator above its character info.
  Internal dialog separators now use the active/passive frame palette instead
  of inheriting the client text color. The single shared `TVScrollBar` now
  handles mouse wheels over both list contents and scrollbar chrome.
  Repaired
  Tetris's Info box by returning its Preview to the normal `TVInfoBox` flow,
  widening the Preview to the full 23-column frame and giving the complete
  header/rows/separators/Preview/footer stack its required height.
- Reduced the stylesheet's responsibility for layout: ASCII Chart, Colors,
  Calculator and History now receive their child sizes from `TVRect`; Tetris,
  Ludo and Window List no longer repeat their outer dimensions in CSS; and
  MIDI/Window List reuse the shared `TVListBox` layout without private copies.
  Ludo's player controls also use explicit TVision bounds. CSS remains only
  for shared browser primitives, palettes and the internal drawing of game
  boards. Renaming Snake's internal body segment removed a collision with the
  generated dialog-body class, so the gray window no longer needs a masking
  selector. Calculator keys now inherit the standard `TVButton` face, focus,
  pressed and shadow rules instead of maintaining a second copy.
- Unified both UHF display paths on `TVHelpWindow : TVWindow` with an owned
  `TVHelpViewer : TVScroller`. Generated-page F1 Help is no longer a bespoke
  `TVDialog`: Close, Zoom, moving, resizing, outer horizontal/vertical
  scrollbars, frame colors and inactive state now come from the same shared
  `TVWindow` chrome as every loaded HELP file; only UHF topic content remains
  format-specific.
- Moved THelpViewer's own UHF loader and fallback context-help window out of
  `tv-dialogs.js` into `tv-context-help.js`. Both generated-page and SPA
  bootstraps load the focused module before dialogs, while the SPA continues
  to show the native UHF through the same `TVHelpWindow` used by other HELP
  files.
- Removed About from the system menu and kept it under Help. The Help menu now
  also exposes Index, backed by a populated alphabetical index in
  `tv-context-help.json`; F1, topic links, Contents and Index all reuse the
  existing bundle window manager.
- Made Search Topics use the shared `TVListBox` normal/focused palette instead
  of its private blue result pane. The stylesheet audit removed that obsolete
  theme token and merged the remaining duplicate Ludo state rules; dynamic
  `viewName`, palette and game-state selectors were retained deliberately.
- Repaired the shared `TVListBox` layout used by Open a File: its two-column
  viewport no longer replaces the right `TVScrollBar` grid, so both arrows,
  page track and thumb area keep their proper vertical positions. Change
  Directory now leaves its `TVOutline` viewport wheel-scrollable.
- Made untitled `TVWindow` frames draw a continuous top border instead of an
  empty two-cell caption gap. File Open, Change Directory and Find History
  popups all inherit the fix from the shared window renderer.
- Matched Calendar more closely to DOS Navigator's 28x8 `TCalendarView`, with
  Monday-first columns, selected/current-day states, `<`, `>`, `=` controls
  and day/week/month/year keyboard navigation. Tetris now uses the original
  DOS Navigator `TGameWindow.Init` geometry; Mastermind was tightened and
  Snake/Tetris explicitly retain the dialog palette outside their playfields.
- Expanded privacy-preserving Server Statistics into a `TVDialog`
  with summary counters and browsable category/detail lists. Daily visits now
  include aggregate device, viewport, pixel ratio, color depth, language,
  time-zone and theme data; HELP/Docs/topic opens, individual game launches
  and coarse client-error categories are counted as well. No IP address,
  cookie, persistent visitor ID, full referrer URL, raw user agent or
  per-visit record is stored.
- Returned Server Statistics to a classic gray `TVDialog`, composed from two
  standard green/cyan `TVListBox` controls and explicit OK/Refresh buttons.
  HELP usage now records the catalog's long display name instead of exposing
  the source filename in the statistics list. Legacy ambiguous counters are
  left unchanged instead of guessing which catalog title they represented.
- Simplified `TVMessageBox` to the shared dialog implementation: message rows
  are ordinary `TVStaticText`, title refresh uses `TVFrame.drawTitle()`, and
  Enter/Escape/Tab use `TVDialog.onDialogKeyDown()`. Removed its private title
  element, duplicate DOM propagation listeners and complete CSS override.
- Added server-wide SQLite Hall of Fame tables and `GET/POST
  /api/hall-of-fame/{game}` endpoints. Games fetch and save the global top ten,
  fall back to the existing browser-local table when the server API is absent,
  and never upload pre-existing local names automatically.
- Reduced the shared stylesheet by consolidating identical menu, window,
  scrollbar, list-cell and game-overlay rules. Static selector analysis found
  no safely removable control selectors; all dynamically generated dialog and
  game roles remain covered.
- Removed another layer of Search, File Open and Change Directory list CSS
  that duplicated the geometry and overflow already supplied by
  `TVListBox`/`TVListViewer`. Search result rows now rely on normal grid-item
  stretching instead of a redundant `width: 100%`. Menu command cleanup also
  preserves focus moved by the command, so Find and Open a File open with
  their first `TVInputLine` selected and ready for typing.
- Browser requests for missing server paths now return to the viewer with a
  Turbo Vision `TVMessageBox`; failed HELP and Markdown loads also surface an
  error dialog instead of only writing to the developer console. JSON API
  clients retain normal structured HTTP errors.
- Local links clicked inside the running viewer are now checked by the current
  `TVBundleApp`. A 404 opens its existing `TVMessageBox` without navigating,
  reloading the desktop or opening another THelpViewer tab; direct invalid URLs
  still use the server-side fallback.
- Added DOS Navigator-compatible `TVPercentGauge` and `TVBarGauge` views from
  the `GAUGE.PAS` design, including `cmUpdateGauge`, `cmResetGauge` and
  `cmAddGauge` broadcast commands. Bundle loading is now a real
  `TVLoadingDialog` composed from those gauges, filename text and a
  `TVButton`, rather than a dialog-specific progress-bar implementation.
- Routed shell and bundle menu/status commands, History navigation, Hall of
  Fame, shared window Close/Zoom controls and Loading Cancel through
  `handleEvent()`. Native DOM listeners remain only at shared browser input
  adapters, global lifecycle boundaries, scrolling/dragging and specialised
  game playfields.
- Fixed `TVScrollBar.bindRoot()` overwriting the logical `TVView` stored on a
  list/scroller frame. Keyboard events now continue through the real owner
  chain, so Escape closes an open History window before its parent dialog;
  shared window Close also preserves the previously active target on Safari.
- Removed the remaining presentation-only dialog/game subclasses that existed
  solely to emit a CSS role. Their owners now compose the corresponding
  `TVGroup`, `TVStaticText`, `TVInputLine`, `TVListBox` or `TVOutline`
  directly. Colors arrow navigation now belongs to
  `TVColorSelector.handleEvent()` and reaches `TVColorsDialog` as the normal
  `evCommand` owner flow instead of a dialog-specific key-down method.
- Fixed `TVTerminal` framed-row width accounting so Widget Gallery's Event
  Log draws its right border inside the bounded 62-column `TVInfoBox` instead
  of clipping it. Removed the role-only Search/Find status subclasses and
  their stale CSS hooks; both dialogs now use ordinary bounded
  `TVStaticText`, while Search keeps result styling scoped to its owned list.
- Removed unused bundle-diagnostic, list-text, game-info and menu-scroll CSS
  selectors left behind by the TVision object refactor. Consolidated input
  sizing in the shared `TVInputLine` rule and removed redundant per-dialog
  clipping, repeated `[hidden]` rules and unused compatibility variables.
- Removed MIDI subclasses that existed only to inject a CSS `role`.
  The external-source area is now an ordinary `TVGroup`; `TVMidiDisplay`
  owns and updates its text children, `TVMidiMeter` owns progress state, and
  `TVMidiTrackList` keeps only its real list-item behaviour.
- Removed the separate `TVRenderer` adapter, its hidden `WeakMap` state and
  the replacement `setDrawOptions`/`drawOptions` API. Each concrete view now
  draws from its Turbo Vision state and fields; there is no generic public
  class/attribute/tag renderer. Dialog and game constructors no longer accept or find
  a desktop DOM element; `TVDesktop.insert()` establishes ownership and mounts
  the view, while `TVDialogManager.register()` performs that insertion for
  managed dialogs. Game frames, labels, buttons, status/info panels and Hall
  of Fame remain composed from shared TVision objects; only the changing game
  board markup remains game-specific.
- Removed the generic `TVMarkupView` escape hatch. Shared dialog content is now
  made from concrete TVision objects; only specialised drawing code emits the
  browser markup required to display a control or a changing game board.
- Added the original `sf...`, `of...`, `gf...` and `dm...` masks plus useful
  Turbo Vision operations including `getBounds`, `getExtent`, `locate`,
  `moveTo`, cursor state, `focus`, `select`, `makeFirst`, group traversal,
  `focusNext`, `newList`, `focusItem`, `selectItem`, and scrollbar
  `setParams`/`setRange`/`setStep`/`setValue`.
- Replaced the public scrollbar markup/options renderer with
  `TVScrollBar(bounds, options).draw()`; `sbHorizontal`/`sbVertical` now select
  the axis and windows, menus, lists and scrollers use the same control and
  generic palette path.
- Folded the former `TVVerticalListViewer` into `TVListBox : TVListViewer` and
  replaced `TVVerticalScrollArea` with the source-like
  `TVScroller(bounds, hScrollBar, vScrollBar)`. Lists no longer have a second
  browser-specific inheritance branch.
- Made `TVMenuItem` and `TVStatusItem` plain command descriptors instead of
  views. Their owning `TVMenuView` and `TVStatusLine` now draw them, matching
  the original separation between menu/status records and visible views.
- Added the source-like `TVMenu` record and changed `TVMenuView`/`TVMenuBox`
  constructors to receive it. Menu item parameters now carry command values
  and payload instead of a second browser-specific attribute object.
- Restored the Turbo Vision `TVMenuItem(name, command, keyCode, helpCtx,
  param, next)` constructor order. Ctrl-F, Ctrl-L, F3, F5, F6, Shift-F6,
  Alt-F3 and Alt-0 now activate their owning menu records through the shared
  `TVMenuController`; the bundle application no longer duplicates those
  shortcuts in an application-specific key switch.
- Replaced caller-built submenu and separator HTML with source-like
  `NewSubMenu()` and `NewLine()` records. Nested menu markup is now emitted
  only by `TVMenuView`/`TVMenuBox`.
- Added `TVStatusDef`, `NewStatusDef()` and `NewStatusKey()` and changed
  `TVStatusLine` to own context ranges and status records instead of receiving
  an untyped array of rendered buttons.
- Internalized list rendering hooks. `TVListBox` no longer exposes caller-set
  item classes, data-attribute names, markup callbacks or root/viewport CSS
  classes; File, History, Directory, Colors, MIDI, Search, Widget Gallery and
  Contents lists now encapsulate their own drawing. `TVOutline` uses normal
  overridable `getChildren`, `getKey`, `getLabel` and `renderNodeContent`
  methods.
- Added explicit `TVHelpViewer : TVScroller` and `TVHelpWindow : TVWindow`
  objects for every converted HELP bundle. Topic/Contents/Back updates now
  replace the owned viewer content instead of overwriting the window viewport,
  and closing the window destroys that object lifecycle cleanly.
- Added `TVProgram : TVGroup` and made both `TVApplication` and `TVBundleApp`
  derive from it, restoring the original program/application ownership level
  without adding DOM parameters to either constructor.
- Made `TVStatusLine` emit its `TVStatusItem.keyCode` records. F1, F3 and
  Alt-F3 status actions now share the same key-code dispatcher as menu items,
  and the clickable F1 item reaches the same `TVHelpController` path.
- Rebuilt Calculator geometry from `TVRect` bounds: an owned `TVStaticText`
  displays the value and all twenty `TVButton` keys have fixed Turbo Vision
  coordinates. The former `calc-main`/`calc-keypad` CSS layout wrappers and
  generic group grid-option fields are gone.
- Migrated Calendar and Find to bounds-first client composition. Calendar's
  caption, arrows, weekday heading and grid, plus Find's label, input,
  History trigger, buttons and status, now carry their own `TVRect` geometry
  instead of dialog-specific positioning wrappers. `TVHistory` also derives
  its command from its semantic history id rather than an input's browser
  `viewName`.
- Migrated Open a File's labels, input/history pair, two-column file list and
  Open/Cancel buttons to their original 47×17 client `TVRect` coordinates.
  Dialog CSS now handles only the controls' intrinsic appearance and list
  flow; it no longer positions those objects through wrapper groups.
- Migrated Change Directory's path input/history pair, outline, status and
  three command buttons to direct `TVRect` geometry, matching the same
  bounds-first construction now used by Open a File and Find.
- Removed browser presentation names from the Open, Change Directory and Find
  `TVInputLine` objects. Their History links and tests now follow owned
  controls and dialog types instead of caller-assigned `data-tv-*`
  identities; no empty input subclass is kept without source behaviour.
- Made `TVListViewer`, `TVListBox`, `TVCluster` and `TVTerminal` honor their
  `TVRect` bounds. Widget Gallery is now assembled at fixed character-cell
  coordinates without its former CSS grid/flex layout or caller-assigned DOM
  identities; `TVMultiCheckBoxes` reports changes through the owner event
  chain instead of a parallel click listener.
- Rebuilt the Colors dialog at its original 59×16 client geometry with direct
  `TVRect` bounds for labels, both lists, selectors, sample and four buttons.
  CSS now styles those controls but no longer positions the dialog.
- Rebuilt full-text Search from bounded TVision controls and removed its CSS
  row/panel/button layout plus input DOM identity. Empty-result messages are
  now drawn by a concrete `TVStaticText` descendant inside the owned list.
- Rebuilt MIDI Player's display, transport controls, track list and optional
  external-source area with direct `TVRect` coordinates. More/Less now resizes
  the client group and dialog through source-like `changeBounds()`/`locate()`;
  the browser-only `TVDialog.setSize()` API and MIDI layout wrappers are gone.
- Fixed the shared dialog client coordinate system: bounded `TVGroup` objects
  now keep absolute Turbo Vision positioning, dialog content is clipped inside
  the framed client area, and MIDI Player's More/Less expansion keeps its
  controls and both frame sides inside the resized window.
- Reflowed Widget Gallery to a 68-column dialog so every action button stays
  inside the frame, and moved Event log into a full-width 62-column
  `TVInfoBox` whose bounded terminal now preserves both frame rows.
- Matched DOS Navigator's Pascal `MessageBox` geometry: a minimum 42×7 dialog,
  standard close control, ten-column buttons separated by two columns, and
  message/button-driven growth without a broken top-right frame.
- Removed the stale four-column Search body override so the shared
  `TVDialog` client and right frame side reach the actual dialog edge.
- Restored Window List rows to the shared `TVListViewer` cyan/green palette
  instead of overriding text-bearing rows with a gray application-bar color.
- Fixed MIDI Player's progress meter ownership (`TVGroup.insert()` had
  returned the fill child), removed that zero-bounds child entirely, and draw
  the fill inside the bounded `TVMidiMeter`. Display, meter, two-row controls
  and track list now follow the coordinate sequence from DOS Navigator
  `CDPLAYER.PAS`.
- Reworked MIDI Player's geometry after direct comparison with DOS Navigator
  `CDPLAYER.PAS` and its original HELP illustration. It now opens as a compact
  44×10 window with one empty character row between the three-row display,
  meter and real two-line `TVButton` controls; the track list and external
  sources stay hidden until `More`. The expanded URL/Load row and its source
  buttons are also separated by one row.
  Removed the duplicate client-area Close button, and made bounded `TVButton`
  widths honor their `TVRect` instead of a browser-only ten-column minimum.
  URL state now records `More/Less`, so old saved 58×21 geometry is normalized
  to the new compact size rather than reopening with empty space.
- Moved Calculator's bounded keypad one character row upward while retaining
  its original twenty two-row command buttons and white-on-blue display.
- Removed `TVHistoryWindow`'s duplicate handwritten frame. The original-style
  `wfClose` window now inherits `TVWindow.draw()`; the shared window renderer
  honors fixed windows without zoom, grow handle or outer scrollbars while
  preserving the History viewer's own list scrollbar.
- Restored Tower of Hanoi focus synchronously after board redraws, preventing
  a rapid Arrow key immediately after Enter from being lost between animation
  frames.
- Removed the remaining dialog-layer `Object.assign(new TV...)` construction.
  Open a File's horizontal controls/info panes, ASCII report, Find status and
  the standalone Context Help dialog now use concrete bounded TVision views.
- Replaced the bundle application's handwritten Window List buttons, DOM
  selection and parallel keyboard/click handlers with `TVWindowList :
  TVListBox`. Loading progress text uses concrete views and Cancel now travels
  through `TVLoadingDialog.handleEvent()`.
- Completed the bounds/event cleanup across shared dialogs and games. Removed
  zero-height `TVRect` controls, rebuilt `TVMessageBox` from owned
  `TVGroup`/`TVStaticText`/`TVButton` children, moved History toggling and all
  dialog/game keyboard input to `handleEvent()`, and kept browser key-up only
  as a shared `TVDialog` bridge for BreakOut's held-key state.
- Removed caller-assigned `presentation`, `viewName`, `_presentation` and
  `_viewName` state. Concrete view classes now declare their drawing role and
  stable browser identity themselves; the original positional constructors
  remain free of CSS classes, DOM attributes and selector options.
- Made `TVInfoRow` derive its frame palette from its owning `TVInfoBox`, fixed
  all game info-panel bounds, and moved Tetris/Pentix title refresh into the
  shared `TVFrame.drawTitle()` path.
- Removed the dialog default-button CSS selector. Enter now finds the nested
  `TVButton` with `bfDefault` through recursive `TVGroup.firstThat()`, so
  object ownership—not generated markup—controls command dispatch.
- Removed browser-only state such as `ariaLabel`, `ariaExpanded`, `tabIndex`,
  `tooltip`, `labelMarkup` and CSS width from `TVButton`. Its private drawing
  path now derives markup and accessibility from the command, value, flags and
  semantic command data; dynamic controls redraw through `drawView()`.
- Fixed bounds propagation in `TVStaticText`, `TVInputLine`, `TVInfoBox`,
  `TVTerminal`, `TVCluster` and `TVButton`; their `origin` and `size` now come
  from the same `TVView(bounds)` initialization path as the original objects.
- Reworked Tetris/Pentix against DOS Navigator's `tetris.pas`: the dialog now
  owns a separate `TVTetrisGameView` and `TVTetrisGameInfo`, exposes New,
  Setup, Top 10 and Pause commands, pauses on inactive/focus state, and keeps
  separate Tetris/Pentix score tables with starting and ending levels.
- Promoted ASCII table, calendar and Colors internals to reusable
  `TVAsciiTable`, `TVCalendarView`, `TVColorSelector` and `TVColorDisplay`
  views. Their dialogs retain object references and route interaction through
  `handleEvent` instead of rediscovering generated elements with selectors.
- Rebuilt History as `TVHistory : TVButton`, `TVHistoryViewer` and an owned
  `TVHistoryWindow : TVWindow`. File Open, Change Directory and Find share the
  same closable popup and empty History remains usable.
- Made the dynamically redrawn status line use one persistent command
  dispatcher, fixing lost Content/Back/Index/Search/Close actions after a
  HELP window changed the available status items.
- Added the Turbo Vision event path (`TVEvent`, `evMouseDown`, `evKeyDown`,
  `evCommand`, `evBroadcast`, `handleEvent()` and `clearEvent()`). Concrete
  dialogs and games now retain their child `TVView` objects and receive button,
  input and board actions through owner-chain propagation instead of querying
  their own generated DOM by `data-tv-*` selectors and wiring parallel click
  handlers. Browser drawing no longer participates in application control
  flow.
- Replaced the browser-shaped TVision object API with positional,
  Turbo Vision-style construction for the shared base view, groups, static
  text, labels, input lines, buttons, clusters, info boxes, terminals and menu
  boxes, as well as lists, outlines, editors, scroll areas, scrollbars, windows
  and the desktop. `TVGroup` now accepts only `TVRect` and inserted `TVView` children;
  `TVInputLine` no longer accepts caller-provided DOM ids or attributes, and
  `TVLabel` links directly to its input object. Constructors no longer accept
  browser roots; explicit `bindRoot()` is the browser boundary. DOM classes,
  generated ids, ARIA and data hooks are produced by each shared view's own
  drawing implementation.
- Renamed the common `TVWidget` base to `TVView`, removed the redundant
  `TVButtonStrip` and public `TVMarkupList`, and made raw shared markup an
  explicit renderer concern. Invalid non-view children now fail loudly rather
  than disappearing from a group.
- Changed the lower status-line text from the active window/dialog caption to
  the first concise sentence of its `helpCtx` topic, restoring an actual
  context-sensitive mini-help hint. HELP navigation can no longer override it
  by passing the current topic title through a second status-text channel.
- Replaced the overloaded `TVButton.buttonKind` path with real
  `TVMenuItem`/`TVStatusItem` objects; `TVButton` is again reserved for command
  buttons, uses Turbo Vision `bf...` flags and derives its browser presentation
  internally from the command.
- Added `TVRect` and changed `TVDialog` construction to start with bounds and
  title. Dialog callers now pass TVision object content and a semantic view
  name; the shared frame renderer owns DOM classes, close attributes and the
  footer.
- Removed `tag` and arbitrary `attrs` from `TVStaticText`. Named dynamic text
  views now expose renderer hooks internally, while labels own their native
  label/span rendering.
- Rebuilt Hall of Fame rows and headings from `TVGroup` and `TVStaticText`
  objects instead of handwritten HTML.
- Fixed Calculator's display palette so its digits are white in every theme;
  the shared static-text color no longer overrides the display foreground.
- Restored the status-line hint for the active dialog, HELP topic/index,
  contents/tag view or Docs editor instead of resetting it to the generic
  application name whenever window focus changes.
- Removed `role` and `name` from the public `TVButton` constructor without a
  compatibility branch. Callers now provide the Turbo Vision-style `command`,
  while the shared renderer privately maps commands and button kinds to the
  browser DOM. Removed raw `className` and `style` from `TVStaticText` and
  `TVLabel`; palette colors and text kinds are rendered centrally.
- Removed raw `className` and `attrs` constructor options from `TVButton` and
  `TVGroup` without a compatibility path; dialogs, games, menus, status bars
  and application overlays now declare semantic commands, values, states,
  accessibility and bounds, while the shared renderer owns their DOM/CSS
  translation
- Completed the standard-dialog object-composition pass: About, Context Help,
  Widget Gallery, Open a File, Change Directory, ASCII Table, Calculator,
  Calendar, Colors, MIDI Player, Find and Search now assemble their client
  controls from the existing TVision JS groups, labels, inputs, lists,
  clusters, buttons and static text instead of dialog-specific HTML templates
- Let the shared `TVFrame` render a `TVView` or an array of view sections
  directly, so concrete dialogs no longer need to flatten their object tree
  before passing it to `TVDialog`
- Rebuilt dynamic ASCII cells, calendar cells, Colors selectors/sample and
  Search result/empty rows with the same shared TV objects used for their
  initial dialog content
- Fixed the dynamic top `Contents` menu: nested submenu separators are no
  longer mistaken for separators of the parent `TVMenuBox`, which previously
  removed complete context-Help menu branches and left the popup empty
- Made HELP `Contents` reuse its enclosing `TVWindow` viewport and right-edge
  `TVScrollBar`; the embedded `TVOutline` no longer creates a second scrollbar
- Moved standard-dialog and per-game `helpCtx` ownership into each
  `TVDialog` constructor and removed the duplicate name-to-context maps from
  both application registration paths
- Began the object-composition migration for dialog clients: Context Help,
  Open a File, Change Directory and Find now assemble their content from
  `TVGroup`, `TVStaticText`, `TVLabel`, `TVInputLine`, `TVButton`,
  `TVListBox`/`TVOutline` and the shared `TVHistoryWindow` trigger
  instead of dialog-specific HTML templates
- Added a distinct `hc...` context and UHF topic for every game, so F1 from
  Puzzle, Tetris, Mines, BreakOut, Sokoban, Lines, Reversi, Ludo, Mastermind,
  Snake, Tower of Hanoi or Tron opens that game's own help instead of the
  generic Games page
- Made shared dialog, HELP and Docs close controls act on the original Turbo
  Vision mouse-down event while retaining native button clicks for keyboard
  input, avoiding Safari's intermittently lost click activation
- Kept the shared History trigger active when its list is empty; Open a File,
  Change Directory and Find can now open and close an empty History window in
  Safari instead of presenting a disabled arrow
- Made the shared History trigger reproduce Turbo Vision's CP437 half-cell
  icon with palette-driven CSS halves, preventing Safari from exposing the
  blue InputLine behind the green sides next to the down arrow in Open,
  Change Directory and Find
- Routed THelpViewer's UHF context help through the same `BundleWindowManager`,
  `TVWindow`, topic renderer, edge scrollbars and global status line as every
  converted HELP file; the bundle application no longer opens a parallel
  context-help dialog with its own Back/Contents controls
- Unified game Hall of Fame `[H]` with the shared `TVFrame` title-control
  renderer, so its brackets use the title color and its glyph uses the same
  green icon color as standard frame controls
- Restored `THistoryWindow` ownership for File Open, Change Directory and Find:
  the framed History popup now covers the trigger, has its own close control,
  and preserves the original separate arrow/side palette roles
- Rebuilt context-sensitive F1 Help as a native UHF 2.0 `THELPVIEWER.HLP`
  bundle with internal topic links, fixed-width tables, long-topic scrolling
  and URL-state restoration of the selected topic
- Added Turbo Vision-style `hc...` help-context constants, inheritance through
  widgets/groups, menu/dialog/window resolution, F1 dispatch, and an in-app
  context Help dialog for menus, HELP/Docs windows, standard dialogs, tools,
  and games
- Matched the original `THistory` interaction more closely: its exact
  three-cell `0x72 / 0x20 / 0x72` icon reacts on mouse-down, toggles reliably,
  closes on Escape or an outside click, and uses the original arrow/side
  palette roles
- Replaced standard-window close and zoom anchors with semantic buttons so the
  shared frame controls activate consistently in Safari and Chromium
- Restored Turbo Vision 2.0's single-line `─┘` grow icon and passive-window
  coloring instead of deriving a double-line resize corner from the frame

### Tooling
- Removed the obsolete internal `TurboVision JS Audit` document. The current
  API and module layout remain documented in `TurboVision JS.md`, while
  implementation history and user-visible changes are tracked in this
  changelog.
- Added built-in ZIP member listing support to `tools/zip_implode.py`, so old
  PKZIP method-6 archives can be inspected with a repo-local tool instead of
  depending on external `unzip` / `7z` output
- Verified repo-local extraction of bundled TD/TPROF method-6 DOC members via
  `tools/zip_implode.py`

## [1.1.0] — 2026-04-09

### Features
- Introduced **UHF 2.0** as the normalized internal document format with structured
  `contents`, `index`, `topics`, topic aliases, exact-label navigation items,
  frozen rows, and line-addressable links
- Added **Microsoft QuickHelp (LN)** reader support for QuickBASIC, QuickC, PWB,
  LINK and related toolchain help files
- Added **Microsoft BW03** reader support for older CodeView DOS / OS/2 help
  files (`CV.HLP`, `CVP.HLP`)
- Added separate **Borland Turbo Debugger TDH / TFH** reader support with
  decoded text/topic-addressing for the current real TDH 1.0, later TDH 2.x,
  and TFH sample families
- Added **Norton Guide / Expert Help** reader support with parent-derived topic
  titles, real MENU traversal, see-also links, and generated contents/index data
- Added standalone **UHF JSON writer** and made the web bundle transport
  consistently use compressed `.json.gz`
- Added bundle-level **table of contents trees** and viewer support for
  Contents windows and menu-driven navigation from `contents[]`
- Added cross-file and symbolic link targets in UHF:
  `file=`, `topic_id`, `alias=`, `line=`
- Added topic alias export so symbolic contexts such as QuickHelp
  `file!context` links can resolve across bundles
- Added generated fallback index creation in readers for source formats that do
  not carry a usable native index
- Added standalone `rebuild_catalog.py` to rebuild `helps/catalog.json`
  directly from existing `.json.gz` bundles
- Added FastAPI runtime server with static `www/` frontend serving, root
  `helps/` bundle output, and direct docs sharing

### Viewer & UI
- Viewer now accepts only **UHF 2.0** bundles; old pre-rendered legacy bundles
  are no longer supported
- Added status-line buttons for **Index** and **Content** when the opened help
  file provides them
- Added dynamic app-bar help menus derived from document contents; BW03 menu
  categories now appear in the top bar after `Windows`, separated by `|`
- Fixed index/content click handling regressions in the SPA viewer
- Improved QuickHelp top navigation rendering including external sibling-file
  tabs and preserved CP437 arrow markers
- Improved syntax highlighting and color palettes to better match
  **Borland C++ 3.1** and **Borland Pascal 7**

### Converter & Refactoring
- Refactored exporter format detection into a shared handler registry used by
  both loading and directory traversal
- Moved format-specific logic back into the appropriate readers, including
  QuickHelp display-name derivation and THELP/QuickHelp/NG navigation handling
- Split HLX source parsing out of `thelp.py` into its own `hlx.py` reader path
- Added shared markup helpers for UHF link generation/parsing and shared
  navigation helpers in the base model
- Extended the document model with structured contents nodes, nav items,
  aliases, comments, and richer metadata

### Downloader
- Refactored the downloader into a product/source manifest plus provider-specific
  downloaders for **WinWorld**, **archive.org**, **old-dos.ru**, **GitHub**, and
  the **Dave Pearson Norton Guides** mirror
- Added default “download everything” behavior when no selectors are given,
  while skipping already downloaded content
- Added recursive extraction through `lsar` / `unar`, including nested archives,
  disk images, and fallback handling for Microsoft compressed help payloads such
  as `HL$` / `SZDD`
- Added Borland installer split-archive assembly for `*.CA1`, `*.CA2`, ...
  files so WinWorld floppy images yield complete `TCHELP.TCH` / `TCHELPW.TCH`
  help files instead of truncated first-part payloads
- Expanded downloadable Microsoft source sets for QuickBASIC, QuickC, MASM,
  CodeView, and related tools

### Tooling & Docs
- `thelp.sh` now auto-bootstraps missing prerequisites: it triggers `download`
  if `downloads/` is empty and `build` if `helps/` is missing
- `thelp.sh` command layout was cleaned up into explicit subcommands:
  `docker start|stop|restart` for container runtime and
  `serve start|stop|status|restart` for the local FastAPI server
- Expanded documentation with new format specs for **UHF 2.0**, **Microsoft
  QuickHelp**, **Microsoft BW03**, **Norton Guide**, bundle transport, downloader
  architecture, and cross-format comparisons
- Updated README, format index, and bundle/downloader docs to describe the new
  converter architecture and `.json.gz` transport

## [1.0.0] — 2026-04-06

### Features
- TurboVision-style single-page viewer with menus, windows, dialogs
- **Help file formats**: Borland THELP (TP4–7, TC, TASM, Sidekick, Sprint),
  TurboVision FBHF (THelpFile), Software602 (M602/Text602), `.TCH` (Turbo C Help)
- **Bundle format**: `.json.gz` bundles with native `DecompressionStream` decompression
- **Converter**: Python package with `readers/` and `writers/` subpackages
- Loading progress dialog with Cancel and abort support
- Full-text search across topics
- A–Z index navigation with letter jump links
- URL routing: `?file=`, `?topic=`, `?docs=` parameters for deep linking
- Documentation Markdown viewer with in-app window
- Theme support (light, dark, auto)
- Color customization dialog
- Syntax highlighting for **Pascal**, **C**, and **x86 ASM** (`tv-highlight.js`)
  - Borland-accurate color scheme (text=yellow, keyword=white, comment=gray, preproc=green, asm=green)
- Automatic encoding detection for Czech help files (CP852, Kamenický, CP437)
- Code block heuristic for TC 2.0/2.01 (`fv=4, tv=1`)
- Box-drawing character stripping from topic headings
- **TVInfoBox** widget with `resolve()` instance API and `updateRow()` for formatted rows
- **TVMessageBox** widget — modal message box extending TVDialog with promise-based `show()`
- Built-in apps: Calculator, ASCII table, Calendar
- Built-in games: Tetris, Minesweeper, BreakOut, Sokoban, Lines, Snake, Reversi, Puzzle
- High Score dialog with name input
- Open Graph / Twitter Card meta tags
- Docker support with docker-compose
- Format documentation: Borland THELP, TurboVision FBHF, Software602 M602/Text602
- JS bundle format specification
