# TurboVision JS Audit

Audit date: 2026-09-21

## Goal

The JavaScript UI should reproduce Borland Turbo Vision for MS-DOS as closely
as practical, both visually and behaviourally. Character-cell geometry,
CP437-style frames, active/passive window states, shadows, menus, dialogs and
keyboard interaction are part of the compatibility target.

The behavioural reference is Borland Turbo Vision 2.0 and the minimally
altered `magiblot/tvision` port, which retains DOS builds and source-level
compatibility with old Turbo Vision applications.

## Verification baseline

- All eight JavaScript assets pass `node --check`.
- The source assets and their checked-in `www/assets` mirrors are identical.
- The complete automated suite passes: 222 tests.
- Real-Chrome coverage exercises focus, modal behaviour, keyboard menus,
  dynamic dialog resizing and exact reported multi-window URLs in addition to
  converter-level regressions.

## Findings

### Critical behavioural gaps

1. **Menus are primarily mouse-driven.** They do not implement the complete
   Turbo Vision interaction model: `F10`, Alt shortcuts, arrow navigation,
   `Home`, `End`, `Enter`, submenu return with `Esc`/Left, remembered selection
   and dynamically enabled or disabled commands.
   **Resolved in Phases 2.1 and 2.4:** shell and bundle menus share one state
   machine with `F10`, Alt and popup mnemonics, arrows, Home/End, Enter, Space,
   Tab, nested Escape return, remembered selection and focus restoration.
   Window commands now derive their enabled state from the active managed
   target and the number of open windows.
2. **Dialog keyboard behaviour is duplicated and inconsistent.** `Esc`,
   default-button `Enter`, Tab order and focus restoration are not provided by
   `TVDialog`. In the bundle viewer, `Esc` closes Search and most games but not
   About, Calendar, ASCII, Colors, MIDI, Puzzle or Welcome.
   **Resolved in Phase 1.1:** the shared dialog now owns Escape, default Enter,
   Tab cycling and focus restoration, with explicit per-dialog exceptions.
3. **Window commands do not target the active view.** `F5` chooses the first
   help window, while `Alt-F3` and the Windows/Close command call `closeAll()`.
   An active document or dialog can therefore be ignored while unrelated help
   windows are closed.
   **Resolved in Phases 1.2–1.3:** the central command dispatcher now routes
   Close and Zoom to the active dialog, help viewer, document or host window.
4. **The advertised multi-window model is restricted.** Opening another help
   file removes the previous help window; opening another Markdown document
   removes the previous document window. This limits Window List, Tile and
   Cascade compared with Turbo Vision's overlapping desktop.
   **Resolved in Phase 2.2:** HELP bundles and Markdown documents now remain as
   independently managed windows. Window List, Tile, Cascade, `F6` Next and
   `Shift-F6` Previous use the shared z-order stack and URL state preserves the
   individual windows.
5. **Several shared controls are incomplete.** `TVCheckBoxes` and
   `TVRadioButtons` only render their initial marks. `TVLabel` renders a `for`
   attribute on a `span`, so it cannot focus an associated control.
   `TVVerticalListViewer` lacks arrow/Page/Home/End navigation and gives every
   row its own tab stop.
   **Resolved in Phases 3.1–3.2:** labels with `forId` now render a native
   `<label>`, and list controls provide keyboard navigation, selection
   semantics and one roving tab stop. Checkbox and radio groups now use native
   inputs beneath their DOS-style marks, including focus and disabled state.

### Dialog, accessibility and lifecycle issues

6. Every `TVDialog` is marked `aria-modal="true"`, although most dialogs are
   non-modal and the rest of the desktop remains interactive.
   **Resolved in Phase 1.1:** modal state is explicit in both behaviour and
   accessibility markup.
7. Closing a dialog does not restore the previously focused element, and Tab
   can leave the active dialog.
   **Resolved in Phase 1.1.**
8. The high-score name prompt is not registered with the dialog manager. A
   game remains active underneath it, so typing game keys can still control the
   game.
   **Resolved in Phase 4.1:** every high-score prompt is registered as a unique
   managed modal dialog and destroys its registration exactly once.
9. Dynamic windows have no common `destroy()` lifecycle. Scrollbars,
   resizers, `ResizeObserver` instances and global listeners may remain after
   their DOM windows are removed.
   **Resolved in Phase 2.3:** scrollbars, resizers and dynamic dialogs now have
   explicit, idempotent `destroy()` methods. HELP and Markdown window close
   paths destroy their widgets before removing the DOM and release manager
   references; replaced HELP content refreshes its observer targets.
10. `updateWindowFrameState()` calls a full-document `fillBorders()` for every
    managed window/dialog during an active-state update, causing repeated work.
    **Resolved in Phase 3.3:** frame updates refill only the affected window.
    The same active-state pass now disables its standard and list scrollbars;
    an inactive scrollbar's first click activates the window without also
    scrolling it. A later source comparison corrected their colors: Turbo
    Vision 2.0 keeps the scrollbar's own palette when its window is inactive.

### Component-specific defects

11. Search opens a result on a single selection click; selection and activation
    are not separate as in a Turbo Vision list box.
    **Resolved in Phase 3.1:** click changes selection; double-click or Enter
    activates the selected result.
12. `TVMessageBox` is currently unused and lightly tested. Its Cancel mnemonic
    is incomplete and a click on empty button-strip space can consume its
    one-shot click listener.
    **Hardened in Phase 3.2:** button-strip delegation ignores empty space,
    Cancel has a declared mnemonic, the first button is explicitly default,
    empty flag sets fall back to OK, and destruction resolves a pending call.
    Adoption by application dialogs remains future work.
13. Reversi leaves the computer-move timeout unmanaged. BreakOut does not clear
    held-key state on close. Snake and some CPU games continue while inactive,
    whereas Tetris and BreakOut pause their update loops.
    **Resolved in Phase 4.1:** Reversi owns and cancels its CPU timer, Reversi
    and Ludo defer CPU turns while inactive, Snake and Mines pause their clocks,
    and BreakOut clears held keys on blur, inactivity and close.
14. Mines has no keyboard board navigation and can place a mine on the first
    clicked cell.
    **Resolved in Phase 4.2:** mines are placed only after the first reveal and
    exclude that cell. A roving board cursor supports arrows, Home/End,
    Space/Enter to reveal and F to toggle a flag; mouse actions preserve the
    cursor for continued keyboard play.
15. Syntax highlighting chooses one language for all code blocks in a
    container, so mixed Pascal/C/ASM documents are highlighted incorrectly.
    **Resolved in Phase 4.3:** contiguous code blocks are identified separately
    in both generated pages and bundle windows. Language detection and
    multiline comment/preprocessor state are now scoped to each block.
16. The calendar leap-year helper treats every year divisible by four as a leap
    year, including 2100.
    **Resolved in Phase 4.4:** the shared helper now applies the full Gregorian
    rule, including the 100-year exclusion and 400-year exception.
17. Screen savers do not restore focus or remeasure while active after a resize;
    automatic idle start is present in the generated-page shell but not in the
    bundle application.
    **Resolved in Phase 4.5:** the saver restores its previous connected focus,
    remeasures and reinitializes the active mode on resize, detaches its resize
    listener on stop, and provides one shared idempotent idle-start mechanism
    used by both applications.
18. The first File Open implementation used separate framed Files and
    Directories controls, although Turbo Vision 2.0 `TFileDialog` uses one
    unframed, two-column `TFileList`. The shared dialog title frame also laid
    out its close control as a grid column, shifting the title away from the
    true window center, and drew that control while the dialog was inactive.
    **Resolved in Phase 5.3:** File Open now follows the original 49×19 cell
    geometry with one list, directory entries ending in `\`, a horizontal
    scrollbar and a two-line information pane. `TVFrame` now draws one
    continuous title line, overlays the close control at its DOS coordinates,
    centers the title over the whole frame and hides the control on passive
    frames.
19. **The color model did not represent the Turbo Vision application palette.**
    Color groups owned independent copies of attributes, even when the
    original `TColorItem`s referenced the same 1-based `cpAppColor` entry.
    Thus Viewer and Puzzle could disagree about indexes 8–14, later groups
    overwrote earlier CSS variables, and a broad descendant rule replaced
    passive frame colors with active colors.
    **Resolved in Phase 6.1:** `tv-core.js` now contains the exact 135-entry
    Turbo Vision 2.0 `cpAppColor` table. Color groups are views over shared
    palette indexes, edits propagate to every view of an index, and CSS uses
    owner-scoped semantic tokens for Help, Viewer/Puzzle, Calendar, ASCII and
    gray Dialog palettes. Passive dialogs now use app entry 32 (`0x70`) and
    passive HELP windows use entry 128 (`0x37`).
20. **Frame and theme state had multiple competing implementations.** Standard
    windows and dialogs used different `--tv-current-*` variables, dragging
    used hard-coded colors, and shell/bundle startup duplicated theme loading.
    **Resolved in Phase 6.2:** both window types share one owner/current frame
    contract and one active/passive/drag glyph table; `TVDialog` selects its
    owner palette through `palette`, controls inherit scrollbar/list colors
    from that owner, and both applications call `initializeTVTheme()`.
21. **Per-format HELP themes stopped at legacy CSS aliases.** UHF themes such
    as Norton Guides supplied different frame, title, title-text and icon
    colors, but the shared window frame only read the newer owner-frame
    variables. The Norton title, `[■]` and `[↑]` controls therefore inherited
    the frame color. **Resolved in Phase 7.1:** the shared window contract now
    has separate active/passive title and icon roles, and UHF themes populate
    both the compatibility aliases and the owner-scoped roles. Norton Guides
    is covered in real Chrome, including frame, title, icons and scrollbar.
22. **Disabled choice controls used the disabled-button palette entry.** The
    original `TCluster` maps disabled choices through dialog entry 31, which
    is application palette index 62 (`0x38`) in the gray dialog. CheckBoxes and
    RadioButtons instead used button-disabled index 44 (`0x78`). **Resolved in
    Phase 7.1:** index 62 is now editable as `Cluster disabled` in Colors and
    shared by both choice controls.
23. **Docker Open needed an end-to-end deployment check.** The routes and both
    catalogs were valid, but the browser test only started its own server.
    **Resolved in Phase 7.1:** the same physical-click smoke test can target a
    supplied deployment URL. Against `http://127.0.0.1:5448/`, Help Files/Open
    displays its loading state and then the populated HELP/DOCS tree. Asset
    versions were advanced so an already open browser can fetch the fixes.
24. **Several regressions shared one missing ownership boundary.** Norton
    Guides used the icon background for the title while moving, File Open did
    not explicitly own its row foreground and input-history arrow color, and
    wide Markdown tables were forced into fixed columns with mid-word breaks.
    **Resolved in Phase 7.2:** moving windows retain their source title roles,
    File Open explicitly uses the dialog input/list palette, and Docs tables
    size their columns from content and use the window's horizontal scrollbar.
    The exact reported VISTA/DEBUG/TCHELP/README URL is a real-Chrome fixture.
25. **The hierarchy and scrollbar duplication matched the audit warning.**
    HELP and Docs hand-built the same frame, `TVDialog` bypassed a window base,
    list behaviour lived in `TVListBox`, and lists, menus and windows each
    implemented scroll repetition and thumb movement. **Resolved in Phase
    7.3:** `TVWindow : TVGroup` owns standard window markup, `TVDialog :
    TVWindow`, `TVListBox : TVListViewer`, and CheckBoxes/RadioButtons inherit
    `TVCluster`. `TVScrollBar` is the only scroll engine; the old exported
    names remain compatibility aliases or delegating facades.
26. **Games only retained one best score and the MIDI dialog exposed every
    advanced source control at once.** **Resolved in Phase 7.4:** all nine games
    use one persistent, sorted ten-entry Hall of Fame component, with lower
    scores preferred for timed/move-count games. MIDI now opens as a compact
    transport and track list; URL and preset sources remain available through
    `More`.
27. **Dialogs that changed their CSS size directly left a stale character
    frame.** MIDI's `More` expanded the body but did not refill its side
    glyphs, so the frame ended at the old height. **Resolved in Phase 7.5:**
    `TVDialog.setSize()` is the shared size mutation path and redraws the
    affected frame; MIDI uses it for both compact and expanded sizes.
28. **Some THELP hotspot tables remained flattened into one cell per line.**
    The normalizer recognized `│` only after `[/link]`, while Borland
    `TVCHELP.TCH` stores it inside the hotspot and permits an incomplete final
    row. **Resolved in Phase 7.5:** both encodings and partial rows are restored
    generically. A 64-file THELP corpus audit found 53 tables and no remaining
    malformed first rows; all ten affected bundles already present in `helps/`
    were regenerated.
29. **File Open still owned private History/FileList behaviour and several
    useful TV 2.0 controls were absent.** **Resolved in Phase 7.6:**
    `TVFileList`, `TVHistory`, `TVHistoryViewer` and `TVHistoryWindow` are
    reusable roles used by File Open and the new Change Directory dialog.
    `TVMultiCheckBoxes`, bounded `TVTerminal`, read-only `TVEditor` and
    `TVIndicator` are shared controls; Widget Gallery and Docs exercise them in
    real Chrome.
30. **Rendered File Open rows and the MIDI display contained text that was
    present in the DOM but clipped or painted black-on-black.** The shared
    `TVListViewer` template inserted formatting whitespace before its text
    span; in the one-cell-high, `white-space: pre` file rows that moved the
    visible label outside the clipped row. The generic static-text rule also
    overrode MIDI's earlier one-class color rules. **Resolved in Phase 7.7:**
    list rows now render without structural whitespace, MIDI declares its
    static-text palette through the shared control token, and browser coverage
    checks the text rectangles and computed foreground/background pairs.
31. **History used InputLine colors and public Docs exposed internal working
    papers.** **Resolved in Phase 7.7:** the three-cell History icon now uses
    the original `THistory` arrow/sides palette mapping, runtime and static
    exports omit `* Audit.md` and `* RE Notes.md`, and public documentation no
    longer links to those private files. Repository-relative `docs/...` links
    in the public README are normalized by the viewer and exercised in Chrome.
32. **Menu/desktop ownership, active-window Find and hierarchical views were
    the next remaining structural gaps.** **Resolved in Phase 7.8:**
    `TVMenuBar` and `TVMenuBox` now share `TVMenuView`; both applications use a
    small `TVDesktop` owner for the dialog manager and global layout lifecycle;
    a History-backed Find dialog routes `Ctrl+F`/`Ctrl+L` to the active Docs or
    HELP editor; and `TVOutline : TVVerticalListViewer` drives HELP Contents and
    Change Directory. Mastermind is the tenth game and uses the shared Hall of
    Fame.
33. **The History control still differed from Turbo Vision at the glyph and
    popup levels, Search commands were always enabled, and Mastermind inherited
    an incompatible button minimum width.** **Resolved in Phase 7.9:** the
    source-defined `THistory::icon` sequence (`\xDE~\x19~\xDD`) is shared by
    all History consumers in one compact framed
    `TVHistoryWindow` without gray padding. Find is enabled only for an active
    HELP/Docs target and Find Again only after that target has a query.
    Mastermind has centered, inset content and its five-column color controls
    explicitly override the generic eleven-column button minimum.
34. **A component `display` rule could override the HTML `hidden` state.** This
    made all three shared History popups visible on dialog open and visually
    immune to closing even though their DOM `hidden` property was true.
    **Resolved in Phase 7.10:** the presentation layer now enforces semantic
    hidden state globally; `TVHistoryWindow` owns show/hide/toggle, ARIA state,
    Escape handling and focus restoration; File Open, Change Directory and
    Find reset it on every open. Mastermind was widened to 64 columns with a
    60-column inset client layout.
35. **The two next planned games were absent.** **Resolved in Phase 7.11:**
    `TronGame` resolves both riders from one tick snapshot and its dialog
    pauses on inactive windows; `HanoiGame` owns legal moves, completion and
    undo history while its dialog supports roving focus, keyboard, click and
    drag-and-drop. Both use the shared managed Hall of Fame and are registered
    in bundle and standalone applications.
36. **The global semantic `hidden` rule exposed a standard-window frame
    regression.** `updateWindowFrameState()` hid the close and zoom elements
    on passive HELP and Docs windows. Because those elements are columns in
    `TVWindow`'s title-row grid, removing them shifted the caption and the
    top-right corner and left gaps in the top line. **Resolved in Phase 7.12:**
    passive standard-window controls retain their grid cells, become
    non-interactive and paint single-line frame segments; dialog controls keep
    their overlay-specific hidden behaviour. The exact reported README/TCHELP
    URL is exercised in both active-window orders in real Chrome.
37. **The History icon palette pair was decoded in reverse and its popup could
    overlap the trigger.** Turbo Vision's `getColor(0x0102)` uses the low byte
    first, so `\xDE`/`\xDD` use History sides and the toggled `\x19` arrow uses
    History button. **Resolved in Phase 7.13:** the CSS roles now match that
    order and the complete three-cell trigger stays above the popup. The
    follow-up implementation now mirrors the original `evMouseDown` path,
    closes on outside mouse-down like `THistoryWindow::handleEvent()`, and
    renders the three character cells explicitly. Physical Chrome clicks test
    arrow close/reopen, outside close and Escape.
38. **There was no equivalent of Turbo Vision's `helpCtx` propagation.** Views,
    groups, menu selections and managed windows could not identify the correct
    F1 topic. **Resolved in Phase 7.14:** `TVWidget` owns `helpCtx`, `TVGroup`
    inherits it from its current child, menu/dialog managers expose the active
    context, `TVHelpController` resolves priority and dispatches F1, and the
    application supplies its own context Help dialog and `hc...` constants.
39. **Standard-window frame controls were anchors and the grow icon was derived
    from the active double-line frame.** The anchors were fragile in Safari and
    the resulting `═╝` did not match `TFrame::dragIcon`. **Resolved in Phase
    7.14:** close/zoom are real buttons and the resize glyph is the source-
    defined single-line `─┘`, with passive coloring when its window is inactive.

## Component assessment

| Area | Assessment |
|---|---|
| Desktop, CP437 frames and shadows | Good |
| Active/passive/drag window drawing | Shared state and source-accurate palette/glyph mapping |
| Mouse move, resize and scrollbars | One shared `TVScrollBar`, including explicit cleanup lifecycle |
| Menus and status line | Shared `TVMenuView`, keyboard model and dynamic window-command state complete |
| Windows, dialogs and buttons | `TVWindow : TVGroup`, `TVDialog : TVWindow`; shared keyboard, modal, focus and frame model |
| InputLine | Usable native input, limited Turbo Vision semantics |
| ListBox/ListViewer | Correct inheritance; selection, activation, keyboard and roving focus complete |
| CheckBoxes/RadioButtons/MultiCheckBoxes | Shared `TVCluster` hierarchy with native or multistate behaviour and DOS-style rendering |
| MessageBox | Hardened and tested; application adoption remains |
| Editor/Terminal/Outline | Active-window Find, read-only editor with indicator, bounded terminal and reusable hierarchical outline are present |
| Games | Twelve playable games with shared top-ten Hall of Fame, focus, timer and keyboard policy |
| Screen savers | Shared idle start, resize lifecycle and focus restoration complete |
| Syntax highlighter | Pascal, C and ASM detection is scoped per code block |

## Phase 7 structural comparison with Turbo Vision 2.0

The source comparison uses `magiblot/tvision` commit
`b4831e2ca16652db327fb7cc964f1c8c2d512524`, especially `views.h`,
`dialogs.h`, `menus.h`, `stddlg.h`, `editors.h`, `help.h`, `colorsel.h`,
`outline.h` and `textview.h`. That project is a minimally altered port of the
Borland code and preserves the relevant Turbo Vision 2.0 class hierarchy.

### Core hierarchy

| Turbo Vision 2.0 | Current JavaScript | Result and required change |
|---|---|---|
| `TView` | `TVWidget` | Present as the basic DOM helper. Add a no-op `destroy()` contract before more dynamic widgets are introduced. |
| `TGroup : TView` | `TVGroup : TVWidget` | Owns child references, a current child and `helpCtx` inheritance; full child lifecycle, focus order and event propagation remain incomplete. |
| `TWindow : TGroup` | `TVWindow : TVGroup` | Implemented; HELP and Docs use its common frame, title controls, client and scrollbar composition. |
| `TDialog : TWindow` | `TVDialog : TVWindow` | Correct hierarchy while preserving modal, keyboard, focus, move and destroy behaviour. |
| `TFrame : TView` | `TVFrame : TVWidget` | Present and shared by dialogs; `TVWindow` owns the separate standard-window composition. |
| `TScrollBar : TView` | `TVScrollBar` | One axis-aware renderer and interaction engine for windows, lists and menus. `TurboVisionScrollbar` remains an API alias. |
| `TScroller : TView` | `TVVerticalScrollArea` compatibility facade and window composition | Partial class parity, but both delegate to `TVScrollBar`; no second scroll algorithm remains. |
| `TListViewer : TView` | `TVListViewer : TVWidget` | Functional selection, activation, keyboard and roving-focus base. |
| `TListBox : TListViewer` | `TVListBox : TVListViewer` | Correct hierarchy; specialised vertical lists add shared scroll composition. |
| `TStaticText : TView` | `TVStaticText : TVWidget` | Present. |
| `TLabel : TStaticText` | `TVLabel : TVStaticText` | Correct hierarchy and native label association. |
| `TInputLine : TView` | `TVInputLine : TVWidget` | Present through native input; selection, validation and horizontal indicator semantics are incomplete. |
| `TButton : TView` | `TVButton : TVWidget` | Present with default, selected, disabled and mnemonic states. |
| `TCluster : TView` | `TVCluster : TVWidget` | Implemented with common native-input, option and DOS-mark rendering. |
| `TRadioButtons`, `TCheckBoxes : TCluster` | Both extend `TVCluster` | Correct shared hierarchy and cluster palette. |
| `TMultiCheckBoxes : TCluster` | `TVMultiCheckBoxes : TVCluster` | Implemented with configurable states, disabled/focus rendering and Widget Gallery coverage. |

### Menus, application and standard dialogs

| Turbo Vision 2.0 | Current JavaScript | Result and required change |
|---|---|---|
| `TMenuView`, `TMenuBar`, `TMenuBox` | `TVMenuBar`, `TVMenuBox : TVMenuView` | Shared rendering hierarchy plus one `TVMenuController` interaction model. Unlike the original, menus are still mostly HTML/config records rather than `TVMenu`/`TVMenuItem`/`TVSubMenu` objects with commands and per-item contexts. |
| `TStatusLine` | `TVStatusLine` | Present and functional; context-specific status definitions and hints remain to be modeled. |
| `TBackground`, `TDeskTop`, `TProgram`, `TApplication` | CSS background, `TVDesktop : TVGroup`, `TVApplication`/`TVBundleApp` | Shared desktop owns layout, clocks and the dialog manager; product-specific applications retain navigation and content composition. |
| `THistory`, `THistoryViewer`, `THistoryWindow` | `TVHistory`, `TVHistoryViewer`, `TVHistoryWindow` | Shared by File Open and Change Directory; storage, list interaction and popup lifecycle are separate roles. |
| `TFileInputLine`, `TSortedListBox`, `TFileList`, `TFileInfoPane` | Native input, `TVFileList`, and inline info markup | File list behaviour is reusable and the old name is an alias; specialised InputLine and InfoPane classes remain optional. |
| `TFileDialog : TDialog` | `TVFileOpenDialog : TVDialog` | Present and catalog-backed. The browser verifies both startup loading and populated states. |
| `TDirListBox`, `TChDirDialog` | `TVOutline` and `TVChangeDirectoryDialog` | Present as a browser-safe HELP/DOCS directory tree with Chdir, Revert and History. |
| `TColorSelector`, `TColorDisplay`, `TColorGroupList`, `TColorItemList` | Logic embedded in `TVColorsDialog` | Visually and behaviourally covered, but the selectors and lists should become reusable widgets after the list-base refactor. |

### Viewer, editor and specialised controls

| Turbo Vision 2.0 | Current JavaScript | Result and required change |
|---|---|---|
| `THelpViewer : TScroller`, `THelpWindow : TWindow` | Bundle rendering and `BundleWindowManager` | Feature-rich, but not represented by reusable classes. Migrate after `TVWindow`/`TVScroller`; do not rewrite the parser or UHF renderer. |
| `TEditor`, `TMemo`, `TFileEditor`, `TEditWindow`, `TIndicator` | `TVEditor` and `TVIndicator` used by Docs | Read-only subset supports selection, Find/Find Again and position reporting; mutation, clipboard commands and file saving remain out of scope. |
| `TOutlineViewer`, `TOutline` | `TVOutline : TVVerticalListViewer` | Implemented for HELP Contents and Change Directory with shared scrolling, selection, activation and expand/collapse keys. |
| `TTextDevice`, `TTerminal` | `TVTerminal` | Bounded append/clear control now drives Widget Gallery's framed Event Log. |
| `TParamText` | Missing | Low-cost addition once `TVStaticText` is stable. |
| Validators | Native HTML constraints only | Optional. Add range/filter validators when editable dialogs need them, not as unused infrastructure. |
| Collections, streams, resources and draw buffers | Not implemented | Intentionally out of scope for the browser. JavaScript, DOM and UHF JSON already provide these low-level services. |

The answer to “do we have every Turbo Vision element?” is therefore **no**.
All important visible primitives have either a working implementation or a
close functional equivalent, but several are composites rather than correctly
layered classes. Low-level DOS object streaming and draw-buffer classes should
not be copied merely for name parity.

### Confirmed duplication and maintenance risks

1. HELP and Docs previously contained separate frame copies; both now use
   `TVWindow.renderMarkup()`.
2. Scrollbar algorithms were consolidated into `TVScrollBar`; compatibility
   facades delegate to it and menu/list renderers use its markup.
3. CheckBoxes and RadioButtons now share `TVCluster` option rendering.
4. File Open and Change Directory share History/FileList roles; their virtual
   filesystem adaptation remains intentionally application-specific.
5. `TVApplication` and `TVBundleApp` retain product-specific bootstrap, while
   `TVDesktop` now owns their shared dialog manager and global layout lifecycle.
6. Shared scrollbar listeners are stored and removed by `destroy()`.

### Next implementation order

1. Replace menu HTML/config records with reusable `TVMenu`, `TVMenuItem` and
   `TVSubMenu` objects that own command, disabled state, mnemonic and `helpCtx`;
   keep `TVMenuController` as the single interaction engine.
2. Add context-dependent `TVStatusDef`/`TVStatusItem`-style hints so the status
   line changes with the resolved help context instead of only the active
   window type.
3. Extract HELP viewing into explicit `TVHelpViewer`/`TVHelpWindow` classes
   without changing converter or UHF rendering semantics.
4. Add Find options (case sensitivity and whole words) through shared cluster
   controls, then add Replace only when editable documents exist.
5. Add reusable `TVParamText` and validators when a real editable dialog needs
   them; avoid unused name-parity infrastructure.

### Proposed new dialogs and games

Completed additions:

1. **Change Directory (`TChDirDialog`)** — virtual directory tree, Revert,
   Chdir and shared History.
2. **History Viewer roles** — reusable model, viewer and popup window used by
   File Open and Change Directory.
3. **Read-only Editor/Indicator** — Docs selection, Find/Find Again and cursor
   position reporting.
4. **Terminal/Event Log** — bounded append/clear log replacing the gallery's
   static row.
5. **Find dialog** — shared History and active HELP/Docs target routing.
6. **Outline/Contents** — reusable tree used by HELP Contents and Change
   Directory.
7. **Mastermind** — compact keyboard/pointer game with duplicate-color scoring
   and the shared Hall of Fame.
8. **Tron Light Cycles** — simultaneous two-player tick resolution, explicit
   and inactive-window pause, keyboard controls and Hall of Fame.
9. **Tower of Hanoi** — focused towers, click/drag/keyboard moves, visible move
   history, undo and Hall of Fame.

Recommended dialogs, in order:

1. **Find options / later Replace** — case/word options now; Replace only after
   editable document support exists.
2. **Go To Line** — a small validator-backed Editor dialog.

No previously recommended game remains unimplemented.

## Resolution order

### Phase 1 — shared interaction foundation

1. Give `TVDialog` universal `Esc`, default-button `Enter`, Tab/Shift+Tab focus
   cycling, modal event isolation and focus restoration. Preserve explicit
   exceptions such as Calculator's use of Escape as a calculator key.
2. Add a central command model for `cmMenu`, `cmClose`, `cmZoom`, `cmResize`,
   `cmNext`, `cmPrev`, `cmOK`, `cmCancel` and `cmDefault`.
3. Route status-line shortcuts and Window-menu commands to the active managed
   target.

### Phase 2 — menus and window desktop

4. Implement the complete keyboard menu state machine and mnemonic handling.
5. Allow multiple help and document windows, then make Window List, Tile,
   Cascade, Next and Previous operate on the same managed stack.
6. Add explicit `destroy()` methods for dynamic windows and widgets.

### Phase 3 — reusable controls

7. Complete Label, CheckBoxes, RadioButtons, ListBox/ListViewer and MessageBox.
8. Separate list selection from activation and implement roving focus.
9. Hide or deactivate scrollbars consistently for inactive views where the
   original control does so.

### Phase 4 — dialogs, games and utilities

10. Migrate every standard dialog to shared commands and mnemonics.
11. Fix game modal prompts, timers, inactive-state policy and keyboard grids.
12. Fix mixed-language highlighting, Gregorian leap years and screen-saver
    lifecycle.

### Phase 5 — regression coverage and additions

13. Add browser-level keyboard/focus tests and visual snapshots for every
    shared widget and menu state.
14. Add a Turbo Vision Widget Gallery/Test dialog.
15. Add an authentic File Open dialog with one two-column file/directory list
    and input history, followed by History Viewer and a source/text viewer.
16. Candidate games, in order: Mastermind, Tron Light Cycles, Tower of Hanoi.

## Progress

- [x] Audit recorded and work order defined.
- [x] Phase 1.1: shared dialog keyboard, modal and focus behaviour.
- [x] Phase 1.2: central command model.
- [x] Phase 1.3: active-target status and window commands.
- [x] Phase 2.1: complete keyboard menu state machine and mnemonics.
- [x] Phase 2.2: multi-window desktop, Window List, Tile, Cascade, Next and Previous.
- [x] Phase 2.3: explicit destroy lifecycle for dynamic windows and widgets.
- [x] Phase 2.4: dynamic Windows-menu command state.
- [x] Phase 3.1: native Label association and list keyboard/activation model.
- [x] Phase 3.2: functional CheckBoxes, RadioButtons and MessageBox hardening.
- [x] Phase 3.3: non-interactive inactive scrollbar with its original palette,
  and window-scoped frame redraw.
- [x] Phase 4.1: managed game modals, timers and inactive-state policy.
- [x] Phase 4.2: safe first Mines reveal and keyboard board navigation.
- [x] Phase 4.3: independent language detection for contiguous code blocks.
- [x] Phase 4.4: Gregorian leap-year handling in Calendar.
- [x] Phase 4.5: shared screen-saver idle start, resize and focus lifecycle.
- [x] Phase 5.1: dependency-free real-Chrome menu/focus smoke-test foundation.
- [x] Phase 5.2: interactive Turbo Vision Widget Gallery/Test dialog.
- [x] Phase 5.3: catalog-backed File Open dialog with HELP/DOCS directories,
  a single two-column list, horizontal scrolling, persistent input history and
  Turbo Vision 2.0 cell geometry. Shared `TVFrame` title drawing was corrected
  and is covered by unit and real-Chrome geometry tests.
- [x] Phase 5.4: preserved single-line drag frames for windows and dialogs,
  modal-first URL-state restoration, and functional THELP `<more>` continuation
  links. The reported Sidekick 2 topic 128/File Open URL is a browser regression
  fixture.
- [x] Phase 5.5: kept inactive scrollbars on their original Turbo Vision palette
  while disabling their input, and restored continuous Widget Gallery dialog
  sides by moving content padding inside the shared frame.
- [x] Phase 5.6: rebuilt the Colors dialog on the Turbo Vision 2.0
  `TColorDialog` 61×18 cell geometry, restored its original list attributes,
  controls and two-line sample, and added selector keyboard navigation plus
  cancel/restore coverage.
- [x] Phase 6.1: replaced duplicated group colors with the exact shared,
  1-based `cpAppColor` model and owner-scoped Help, Viewer/Puzzle, Calendar,
  ASCII and Dialog CSS palettes.
- [x] Phase 6.2: unified `TWindow`/`TDialog` active, passive and dragging frame
  state, removed the global passive-color override, made common controls use
  their owner's palette, and centralized theme initialization.
- [x] Phase 6.3: added real-Chrome regressions for shared Viewer/Puzzle indexes,
  inactive Colors list state, passive frame color/glyph and hidden frame icons.
- [x] Phase 6.4: made `TVVerticalListViewer` retain roving focus after click
  handlers redraw their rows, restored distinct current/selected Colors-list
  states, added a non-persistent Reset preview, and widened Widget Gallery so
  the complete 30-column Event Log frame remains visible. Real-Chrome coverage
  verifies click selection, focus, event text and the right-hand frame edge.
- [x] Phase 6.5: restored the explicit blue/yellow Editor palette for Markdown
  documents, unified all four `TVInfoBox` frame sides, and corrected physical
  list clicks by resolving the pointer against current row rectangles. The
  browser regression now uses a real DevTools mouse event instead of DOM
  `.click()`, which had hidden the one-row targeting defect.
- [x] Phase 6.6: separated the Markdown Editor content colors from the
  customizable Viewer palette. A browser regression deliberately changes the
  Viewer text background to green and verifies that Docs remains blue/yellow.
- [x] Phase 6.7: made `TVVerticalListViewer` a real `TVListBox` subclass and
  centralized list row geometry, focus/selection colors and viewport layout.
  Colors, Widget Gallery, File Open and history now use the same Turbo Vision
  dialog-list palette. Checkbox/radio groups use the original cluster normal,
  selected, shortcut and disabled colors across the whole row. File Open is
  bound before catalog loading completes and waits for HELP/DOCS data instead
  of exposing an empty dialog. Widget Gallery now also exercises an enabled
  scrollbar, static text, hotkeys, disabled states and `TVMessageBox`.
- [x] Phase 6.8: made Help Files/Open available before catalog loading finishes
  and open synchronously with explicit loading and empty states; a physical
  real-Chrome menu click now covers this startup path. Split the Colors reset
  action into per-item Default and full-palette Reset All, with scope-specific
  browser regression coverage.
- [x] Phase 7.1: restored per-format title/frame/icon/scrollbar roles for Norton
  Guides and every other UHF theme, added the original Cluster Disabled palette
  entry, verified File Open against the running Docker service, and recorded the
  complete hierarchy, duplication and missing-component comparison.
- [x] Phase 7.2: fixed the Norton moving-title palette, File Open text/arrow
  colors and content-sized Markdown tables; the exact reported multi-window
  URL is covered in real Chrome.
- [x] Phase 7.3: introduced `TVWindow`, corrected `TVDialog`, `TVListViewer`,
  `TVListBox` and `TVCluster` inheritance, migrated HELP/Docs frame markup and
  consolidated windows, lists and menus on one `TVScrollBar` engine.
- [x] Phase 7.4: added one ten-entry Hall of Fame implementation to all nine
  games and made MIDI compact by default with advanced sources behind `More`.
- [x] Phase 7.5: added shared `TVDialog.setSize()` frame redraw, fixed MIDI
  expansion, restored both Borland THELP sequential-table encodings including
  incomplete final rows, regenerated the ten affected installed bundles and
  covered the exact reported TVCHELP URL in real Chrome.
- [x] Phase 7.6: extracted FileList and all three History roles, added Change
  Directory, MultiCheckBoxes, Terminal/Event Log and a read-only
  Editor/Indicator pair for Docs, with shared-control and browser regressions.
- [x] Phase 7.7: fixed shared list-row text clipping, restored the original
  History and visible MIDI-display colors, validated public Markdown links and
  excluded Audit/RE working papers from runtime and exported Docs trees.
- [x] Phase 7.8: added shared `TVMenuView` and `TVDesktop` ownership, a
  History-backed active-window Find/Find Again flow, reusable `TVOutline` for
  HELP Contents and Change Directory, and Mastermind as the tenth Hall of Fame
  game. Unit and Docker-backed real-Chrome coverage exercise the new paths.
- [x] Phase 7.9: matched the original segmented History icon attributes and
  compact framed popup, made Find/Find Again availability follow the active
  target and query, and corrected Mastermind geometry plus its inherited
  button-width conflict. Docker-backed Chrome checks dimensions, palettes,
  command states and clipping.
- [x] Phase 7.10: made semantic hidden state authoritative across TVision,
  consolidated the complete History popup lifecycle in `TVHistoryWindow`, and
  widened Mastermind. Browser coverage now checks computed visibility and both
  directions of the History toggle for File Open, Change Directory and Find.
- [x] Phase 7.11: added pure Tron and Hanoi rule models, their Turbo
  Vision-style dialogs, all input/lifecycle policies and shared Hall of Fame
  integration. Unit tests cover simultaneous collision and reversible Hanoi
  rules; Docker Chrome covers rendering, focus, keyboard, drag and inactive
  pause/resume.
- [x] Phase 7.12: preserved passive `TVWindow` title-grid geometry while
  replacing inactive close/zoom controls with non-interactive frame segments.
  The reported README/TCHELP state is a real-Chrome regression fixture.
- [x] Phase 7.13: corrected the source-defined `THistory` arrow/sides palette
  order and kept the complete trigger above its popup. Real pointer clicks
  verify open/close in File Open and Change Directory.
- [x] Phase 7.14: added the shared `helpCtx` model, `hc...` constants, F1
  controller and THelpViewer context Help; restored the original `─┘` grow icon
  and semantic close/zoom buttons, and completed History mouse-down/outside-
  close behavior.
- [x] Phase 7.15: preserved Microsoft Advisor's qualified cross-file QuickHelp
  targets and regenerated both installed PWB bundles.
