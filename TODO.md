# TODO

## Pre-commit verification — 2026-10-15

The complete 2,539-test run reported 2,530 passes, eight failures and one skip.
Two failures were stale test setup after the account change: an unqualified
six-column credential INSERT and a profile-browser mock missing the security
endpoint. Those fixtures were corrected; all six tests in the affected
migration/public-browser modules then passed. The remaining six failures are
not a clean full-suite result:

- [ ] Verify the newly downloaded Turbo Basic `TBHELP.TBH` header/compression
  profile using its original consumer. The current parser reports unsupported
  compression type 15; that interpretation itself needs verification. Three
  THELP corpus checks and the combined Turbo Basic/Prolog server-build check
  fail on these inputs. Keep the bounded rejection/atomic publication behavior;
  do not silently omit the inputs or guess a decoder to satisfy a snapshot.
- [ ] Isolate the browser workspace-restore and installed-Scorpion corpus
  fixtures from administrator-selected live content. The current local
  `data/helps/catalog.json` contains only Norton Guides; Sidekick 2 and Scorpion
  are absent, so those two tests cannot perform their intended assertions.
  Do not reinstall packages into permanent data as an implicit test setup step.

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
- [ ] Stop/join MIDI background writers before closing the shared downloader
  during application shutdown. Short-lived TestClient lifespans can currently
  report an unhandled `RuntimeError: Downloader is stopping` in the MIDI thread;
  the worker/queue shutdown ordering is separate from the module-layout refactor.
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
