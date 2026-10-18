# TODO

## Version 3 application modules

- [x] Release/tag 2.1.0 and open a separate 3.0.0.dev0 development branch.
- [x] Define the client-plus-optional-Python contract in TurboVision JS docs.
- [ ] Add a trusted application manifest and registry with unique stable IDs;
  reject duplicate commands/help contexts and invalid entry points.
- [ ] Connect new modules to both viewer shells' menus and TVEvent dispatch,
  retaining existing direct registrations and shared TVWindow/TVDialog views.
- [ ] Register optional Python routers and lifespan resources using the existing
  FastAPI host/services. Test client-only modules and a server-equipped fixture,
  including cleanup after failures; do not create dummy MOD Player server code.
- [ ] Connect module help to Contents/Index and view-owned contexts, then add
  public workspace state and isolated per-user settings without moving DOS data.
- [ ] Implement MOD/XM/S3M Player as the first real client module using the shared
  downloader. Select/verify a browser engine before implementing playback.
- [ ] Consider shared/private per-application disks separately, after the module
  lifecycle and ownership tests are stable. Do not migrate existing applications
  or private overlays as part of the initial module infrastructure.

## Production inventory and restart/retry verification — 2026-10-17

- [x] Deploy the MIDI restart/DOS Retry fixes and verify public assets, context
  HELP, managed Docs and a healthy restarted service. No private data or content
  selection was changed by deployment. A blocked row opens Retry/Remove through
  the regular menu event flow; Cancel does not start installation.
- [x] Check all 273 published HELP bundles (76 editions, 173,741 topics): valid
  gzip/UHF, matching catalog counts and matching published checkpoint SHA-256s.
- [x] Check all 23 current-manifest DOS packages marked installed: all 1,221
  owned files exist, source recipe keys and launch targets match. Compare 1,215
  files with checksum-identified cached archive outputs and six UTILS generated
  files with the configured post-install copy/script bytes. HC602.EXE is a COM
  executable with an EXE filename, not corruption; original archive CRC agrees.
- [ ] Continue the outstanding DOS selection by explicit Retry/Apply: only 23
  of the 70 originally selected current-manifest packages were installed at this
  snapshot. Deployment/audit did not start another installation automatically.
- [ ] Validate/normalize legacy MIDI cache without unnecessary redownloads.
  All 7,236 catalogued files and 207 covers exist, but only 7,150 tracks already
  match the current normalized SMF decoder output. Fifty tracks retain removable
  source trailers. Thirty-five Amy's Fantasies tracks declare SMF format 0 with
  two tracks (rejected by the current validator); Duke Nukem 3D Atomic Edition's
  WAREHAUS.MID has a chunk extending beyond the file. Check original payloads
  before deciding whether to repair a nonconforming source or retain a failure.
  The lightweight size/MThd cache check currently still reports these files as
  available. No retrospective cache repair or playback verification is claimed.
- [ ] Verify the seven absent tracked originals formerly under `data/sources/`
  against canonical `var/sources/` or migration backups before committing their
  deletion. Code/documentation commits do not authorize discarding original bytes.

Targeted verification: 447 tests passed; three corpus-dependent tests were
deselected because their TASM.TAH / Turbo Debugger 1.0 TDHELP.TDH inputs are
absent. This includes browser menu/action tests and restart/job recovery, not a
new complete-suite run. Earlier complete-suite results below are historical.

An additional six-module converter check reported 214 passes, four skips and
20 failures: 19 cannot read absent original THELP/Scorpions inputs; the remaining
case finds an unreferenced `Borland C++ 3.x/OWLHELP.TCH` payload (SHA-256
`9dcf2d3e64de62e3fc0a964a89fc7f494e1b4c4881164483053440be85919180`).
Restore/verify the missing corpus and independently verify that ObjectWindows
revision before extending the frozen references. Do not regenerate expected
decoder hashes from the implementation merely to make this test pass.

## Browser regression — 2026-10-16

- [x] Refresh pending global Search results when a response reports `building`
  or `paused` but the first index-status poll already says `ready`, without a
  progress dialog having been created. Track pending search refresh separately
  from the dialog, and keep idle polling from resetting a completed selection.
  Use canonical temporary paths in browser tests because storage migration
  deliberately rejects symlink ancestors.

## Live HELP download diagnostics — 2026-10-15

- [x] WinWorld's broad release pages collect distinct HELP versions
  into the same `Borland Turbo Pascal 5.x` directory. The existing original is
  CRC32 `8BB44D4B` (Turbo Pascal 5.0); a different original correctly triggers
  conflict protection. Archive titles now filter releases before download;
  verified CRCs control canonical placement and exact edition selection,
  without overwriting originals or adding aliases. Unknown collisions still fail.
- [x] Archive-tool stdout/stderr can contain non-UTF-8 filename bytes. In the
  running Docker HELP job this produces a decoding failure at byte EB in TP6
  extraction; decode diagnostic output safely, keeping actual file paths,
  member matching and source bytes intact. These are not HTTP 429s.
  Neither failure was retried/removed and the running job was not interrupted.
- [x] Old-DOS requests failed the URL transport guard: HTTPS redirects to HTTP.
  Its actual HTTP catalogs (categories 51/52) return 200; use that provider's
  explicit HTTP origin. Public-peer, credential and generic HTTPS-downgrade
  checks are unchanged.
- [x] Replace Norton Commander 4.0's rate-limited WinWorld source with two
  verified English-media alternatives at Internet Archive. Retain bounded
  retries/cooldowns; a failed job still requires explicit Retry/Apply, and an
  alternative recipe is not proof that the package has already been installed.
- [x] The run ended with 11 failed source groups. Publication then rejected
  `Borland Turbo Pascal 7/COMMDLGS.HLP` and `HELPEX.HLP`: both report
  "Windows Help 3.0 topic addressing is not implemented". Turbo Pascal 7's
  `archive_members` selects TURBO.TPH, OWL.TPH and TVISION.TPH for extraction
  and processing; the two example originals are retained. Selected malformed inputs still
  fail staging rather than replacing existing publication.
- [ ] Implement/verify Windows Help 3.0 (HC30, SYSTEM.Minor 15) topic addressing
  before selecting those example files for conversion. This is deferred format work,
  not proof of damaged originals or a completed HC30 implementation.

## MIDI source data — 2026-10-15

- [ ] Obtain actual playable MIDI for Karl's IT Retro's `Bad Blood (1990).zip`.
  All four `.mid` members contain short plain-text parameter lists ending in
  DOS EOF, not Standard MIDI payloads. The original `01 - Title.mid` is 46 bytes
  (`(2/60)`, then `(2/4,3/104,4/110,5/114,10/1,10/1)`). Do not invent notes or
  disable validation. The server now reports the source error, examines every
  member and preserves the cover/any valid siblings; the upstream music itself
  remains unavailable.

## Regression repair — 2026-10-15

The complete 2,539-test run reported 2,530 passes, eight failures and one skip.
Two failures were stale test setup after the account change: an unqualified
six-column credential INSERT and a profile-browser mock missing the security
endpoint. Those fixtures were corrected; all six tests in the affected
migration/public-browser modules then passed. This is the historical starting
result, not the result after the following repairs:

- [x] Verify Turbo Basic `TBHELP.TBH` using its original consumer. It uses
  WORD records and literal/FE-space text, not compression type 15. A dedicated
  reader matches TB.EXE's display bytes for all 324 physical screens; preserve
  native context/offset links, malformed-input rejection and atomic builds.
  Register both distinct CRCs and document the separate binary grammar.
- [x] Isolate browser workspace-restore and Scorpion publication checks from
  administrator-selected content. Build the eight browser HELP sources and
  Scorpion DAT corpus only in temporary output. Update stale MIDI assertions
  for the shared Downloads control instead of restoring removed APIs.
- [x] Freeze the original 66-file THELP reference cohort with source hashes,
  preserving its independent golden digests. Verify 13 additional source copies
  separately: nine are prior byte-identical inputs; the other four contain
  three distinct inputs matching the existing DEHELP.C/BOA C references.

Verification: the complete 2,570-case run reported 2,567 passes, two failures
and one skipped Safari automation test. Both failures were reference-fixture
ordering (string sorting versus the original Path component sorting), not
changed decoder output. After restoring Path order, both unchanged independent
golden tests passed (58.02 s). The final pending-download shutdown case adds
one regression: all 34 MIDI/configuration/rebuild tests passed (2.51 s), and
the main browser/catalog repetition passed seven tests (37.20 s).
Across the complete run and targeted repetitions, all 2,570 distinct current
non-Safari cases have passing results. This is not a claim of a fresh clean
single full-suite run after the last fixture/shutdown edits. Safari remains
unverified here; the known Starlette/httpx deprecation warning remains too.

## HELP conversion audit — remaining scope (2026-10-14)

All main currently registered reader families have had their installed
corpus and technical datasheets reviewed. This does not establish every
historical variant, every reserved byte or pixel-exact native presentation.
Do not count the earlier general application roadmap below as unfinished
HELP decoders.

- [x] Run the combined regression/integration pass after the latest
  Game-Cheater and Scorpion changes; check published catalogs, actual links,
  search and documentation together (305 tests; modern/legacy screens,
  custom fonts and explicit blink profiles included, SCX/Windows graphics
  remain explicitly deferred).
- [x] Regenerate every selected source in isolated output and compare all
  published content/catalog metadata: 355 inputs, 272 outputs, all 254
  installed bundles unchanged apart from converter timestamps; the 18
  Turbo Basic/Prolog outputs remain uninstalled according to server selection.
- [x] Restore QuickC 2.50's QC.HLP from the original Advisor/Learning disks
  through the shared Microsoft SZ splitter/decoder; register its CRC and
  retrieval jobs, publish the 876-topic bundle and recover 1,388 of the
  1,390 GRAPHICS reference occurrences previously lacking a target file.
- [ ] Complete the remaining external HELP corpus and source/runtime context
  verification. The link audit retains 94 unresolved occurrences; two are
  one control-bearing composite GRAPHICS context (topic 168's inline/Up link).
  Do not substitute a different release, guess aliases or remove the links.
- [ ] Keep consumer-specific unknowns explicit: legacy/short-header THELP
  Contents bindings, Expert Help-only rendering extensions and undocumented
  variant controls need their own original consumer evidence. They are not
  confirmed faults in the already verified source profiles.

Deferred scope also includes four companion texts in Cheater 21's
`TEXTY.DAT` (SC 2000 grammar), explicitly postponed by the user on 2026-10-14.
They are not a separate installed Cheater release or a fault in the normal
Cheater 21 article decoder. Windows HLP graphics/native UI behavior and
Scorpion's indexed graphics palettes remain deferred too. Modern and v4–v14
PROGRAM text screens/artwork use native
TextScreen/font resources; the unresolved presentation variants below are separate work.
Do not include them in a claim of complete text conversion or silently turn
them into guessed text/links. Their detailed evidence is in the corresponding
format RE notes; the Windows graphics checklist follows.

## Scorpion native screens and fonts

- [x] Preserve the modern v15/v16/v21–v23 PROGRAM text screens as native
  glyph/foreground/background cells and shared Base64 bitmap fonts, with
  existing UHF palette indexes and shared TVTextScreen/HELP chrome.
- [x] Recover v10–v14 FONT.SCO and legacy SCD/SCO text screens using the
  original DOS LZHUF routine as an independent reference. Preserve 53
  non-blinking templates and their default fonts in the PROGRAM bundles.
- [x] Bind native default fonts to PROGRAM inline block/box artwork in its
  original article rows. Retain surrounding text, links and row cursors;
  never associate a separate template with prose by caption/position guesses.
- [x] Preserve v6 SCR1/SCR2/SCR6 bit-7 attributes with explicit DOS blink
  semantics, the standard blink-enabled presentation profile, reduced-motion
  handling and shared-view animation cleanup. Do not infer a video mode from
  attribute bytes; UHF also supports an explicit bright-background profile.
- [ ] Recover original SCX indexed graphics palettes. Windows graphics stay
  deferred; do not substitute guessed colors or publish PNG approximations.
- [x] Verify v4/v5 default FA.SCO selection and project PROGRAM inline artwork
  using its actual bitmap font, retaining text, links and original row positions.

## Deferred Windows Help graphics

The HC31 text/article reader remains in use. Graphics and related behavior
are deliberately unresolved for now; `▧` placeholders and original object
payloads remain intact. Do not present descriptor parsing as complete image
support or replace native links with guessed destinations.

- [ ] Decode and render external `|bmN` and embedded SHG/MRB images: DIB/DDB
  bitmaps, Windows metafiles, palettes, transparency and packing methods.
- [ ] Handle multiple resolutions, native dimensions/DPI and image placement
  inside the existing shared HELP window; do not introduce another window type.
- [ ] Restore image-region links, coordinates, local/external context targets
  and navigation macros, preserving every source variant and original identity.
- [ ] Document verified byte fields in the Windows Help datasheet and add
  independent native-corpus, malformed-data and browser regressions before
  advertising graphics support. Research evidence is in
  `docs/Formats/Windows Help RE Notes.md`.

## Deferred Cheater 21 TEXTY.DAT companion text (SC 2000)

Keep the source bytes and already converted catalog intact. Do not continue
native prose/font/page-layout research without a new request or new original
consumer evidence.

- [ ] Establish the angle-bracket text-control grammar in v21 `TEXTY.DAT`
  (`kontakt`, `novezpra`, `oprogramu`, `spoluaut`), including its real link
  targets, font/encoding rules and display layout. These are valid Allegro
  text objects, not damaged compression or DOS `[Rnnn]` article streams.
- [x] Keep this grammar out of DOS article detection even when prose quotes
  `[Rnnn]` markers. Retain complete decoded objects, including the in-word
  `FEh` in `spoluaut`; text-end/font/encoding rules still need verification.
- [x] Preserve the `txt` catalog's rows and fields, title Index/Contents
  cursors, CHEATY-scoped marker references and exact short title references.
  Duplicate captions and ambiguous seven-field descriptors remain intact.
- [ ] Establish remaining catalog flag/type/attachment bindings when an
  actual CH2000 consumer and its LIB archives become available. No paths to
  absent LIB members are guessed. The retained author's 2001 CH2000 web page
  advertises a beta but supplies no program download; the original v22/v23
  PROGRAM article says the graphical DOS project was postponed in favor of
  a Windows rewrite. No authenticated CH2000 consumer was found in the
  checked author/archive catalogs. Do not repeat the same unsuccessful
  searches as converter fixes; resume native layout/link work when a new
  executable, font bank or source-code lead becomes available. Search
  evidence and verified prose controls are in the Scorpion RE notes/datasheet.

## Implemented application foundation

- [x] Compressed `.json.gz` bundles with `DecompressionStream`
- [x] TurboVision UI (menus, windows, scrollbars, dialogs, resize, zoom)
- [x] Full-text search across topics
- [x] A–Z index navigation
- [x] Theme support (light, dark, auto)
- [x] Color customization (TurboVision Colors dialog)
- [x] Pascal, C, ASM syntax highlighting (client-side)
- [x] Code block heuristic for TC 2.0/2.01
- [x] Downloader (WinWorldPC, archive.org, old-dos.ru)
- [x] Docker support
- [x] CP852 box-drawing disambiguation
- [x] Built-in apps (Calculator, ASCII table, Calendar, Tetris, Minesweeper, Puzzle)
- [x] GNU GPL v3 license

## Server integration — 2.1

- [x] Account-owned named Passkey list/add/rename and opt-in password setup/login,
  with recent Passkey confirmation, salted hashes, throttling and browser tests.
- [x] Separate accounts, DOS and MIDI into feature packages, retaining explicit
  coordinating stores, the shared downloader, HTTP adapters and data paths.
- [x] Stop/join MIDI background writers and urgent playback transfers before
  closing the shared downloader during application shutdown. A terminal stop
  state prevents pending rebuild/source/index operations from restarting the
  writer. Cancel only pending MIDI tasks, without waiting behind unrelated
  HELP/DOS work; Event-gated regressions verify ordering and file preservation.
- [x] Callable downloader/converter services with progress callbacks, bounded
  staging and validated atomic HELP publication; server jobs call Python APIs.
- [x] Administrator HELP / DOS Packages menu/dialog with shared TVCheckBoxes,
  installation/deinstallation, first-run setup and API progress polling.
- [x] Server-triggered conversion of selected missing HELP products, catalog
  publication and incremental search/SEO index refresh.
- [x] Shared reader/writer model: HelpDocument, TopicRecord, IndexEntry,
  ContentNode and structured links/font/TextScreen resources.
- [ ] Cooperative cancellation of server download/build jobs before publication.
  Closing a progress dialog does not currently cancel the server job.
- [ ] Push progress via SSE if needed; current content dialogs poll status.
  A DOS Navigator-style dual total/current-file progress display remains open.
- [ ] Explicit rebuild of already installed HELP products from the web API.
- [ ] HELP content editing API; read-only bundles/catalogs already serve browsing.
- [ ] Investigate the intermittent DOS Zoom browser regression under the
  combined suite: one direct-backend failure, then both backends and another
  direct-backend run passed. Geometry diagnostics were added; no runtime fix
  is claimed yet.
