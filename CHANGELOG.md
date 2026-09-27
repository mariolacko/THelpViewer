# Changelog

## [Unreleased]

### Formats
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
