# Changelog

## [Unreleased]

## [2.0.0] — 2026-10-10

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
