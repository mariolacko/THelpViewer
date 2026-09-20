# TurboVision JS Audit

Audit date: 2026-09-20

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
- The complete automated suite passes: 216 tests.
- Existing automated coverage is strong for converters and selected rendering
  regressions, but it does not yet exercise browser focus, modal behaviour or
  complete keyboard menu navigation.

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
    The same active-state pass now disables and passively colors its standard
    and list scrollbars; an inactive scrollbar's first click activates the
    window without also scrolling it.

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

## Component assessment

| Area | Assessment |
|---|---|
| Desktop, CP437 frames and shadows | Good |
| Active/passive window drawing | Good |
| Mouse move, resize and scrollbars | Good, including explicit cleanup lifecycle |
| Menus and status line | Shared keyboard model and dynamic window-command state complete |
| Dialogs and buttons | Shared keyboard, modal and focus model complete; `TFrame` title geometry matches TV 2.0 |
| InputLine | Usable native input, limited Turbo Vision semantics |
| ListBox/ListViewer | Selection, activation, keyboard and roving focus complete |
| CheckBoxes/RadioButtons | Native behaviour with DOS-style rendering |
| MessageBox | Hardened and tested; application adoption remains |
| Games | Playable; focus, timers and keyboard consistency need work |
| Screen savers | Shared idle start, resize lifecycle and focus restoration complete |
| Syntax highlighter | Pascal, C and ASM detection is scoped per code block |

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
- [x] Phase 3.3: inactive scrollbar state and window-scoped frame redraw.
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
