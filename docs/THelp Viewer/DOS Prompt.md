# DOS Prompt

DOS runs in the browser through the locally bundled `emulators` 8.5.2 DOSBox
WASM backend, not as a process or shell on the server. `TVDosWindow` inherits
the shared `TVWindow` frame, movement, resize and title controls. Its specialised
`TVDosView` owns the text/graphics screens, embedded pause dialog and native input bridge into
`TVEvent.handleEvent()`. There is no second js-dos player UI or player CSS.
Both text-mode software and graphical DOS programs are supported. The screen
follows DOSBox's video-mode size; BIOS VGA 320x200 and 640x480 tests verify real
graphics and the transition back to text mode. Individual games still depend on DOSBox
compatibility, configured memory/cycles and the browser's performance.

The worker backend is required by the default configuration. If a browser
denies workers, DOS reports an unsupported mode instead of downloading the
entire C drive. Browser audio permission is optional: denied AudioContext
creation/resume cannot prevent DOS from running silently. The explicit
`allow_full_disk_fallback` setting defaults to false; only enabling it allows
the legacy direct backend and its full ZIP download.

Open **≡ → DOS Prompt**. While the window is active, a **DOS Prompt** menu is
added to the main menu bar. It contains Pause/Resume, Restart, Save C to cloud,
Mount local folder, Disconnect local D, Mount CD, Mount Floppy,
Eject media, Zoom 2×, Fullscreen and Close. Ctrl+Alt+M opens this
menu from the DOS keyboard. F1 and other DOS keys go to the emulator instead
of opening THelpViewer help. Operating-system/browser-reserved shortcuts may
still be intercepted by the browser. Clicking outside the window or hiding
the page pauses DOS and clears held keyboard/mouse buttons. Moving/resizing
the frame also pauses DOS through `sfDragging`; mouse events belong exclusively
to the shared frame mover, including mouse-up over the canvas. Releasing the
mouse or losing browser focus clears dragging and preserves manual Pause.
The DOS contents are gray during move/resize, for both text and graphics;
releasing or cancelling the gesture restores colors unless manually paused.
Dragging does not open the embedded Resume panel.
The numeric keypad forwards physical keys separately from the main keyboard:
0–9, decimal/comma, divide, multiply, subtract, add and Enter use jsDOS keypad
codes 320–335. NumLock is forwarded too, leaving number/navigation behavior to
DOS. Keypad equals uses ordinary `=` (61), because the bundled backend exposes
no distinct keypad-equals code. Browser/OS-reserved combinations can still be
intercepted before the page receives them.
With the DOS screen focused, **Alt+Enter** toggles native fullscreen and
**Alt+Pause** toggles pause/resume (also **Alt+F16** for the classic Mac mapping).
These match the [classic DOSBox bindings](https://www.dosbox.com/wiki/Special_Keys).
Classic DOSBox has no standard restart binding; **Ctrl+Alt+R** is a THelpViewer
extension. Restart confirmation leaves fullscreen so the standard TVision
message box is visible; cancelling preserves the running session. Shortcut
repeats/key releases are consumed, not forwarded as extra DOS keystrokes.

Manual **Pause** grays the DOS contents and opens an immovable `TVDialog`
inside the DOS client area, with a **Resume** button. Resume (or Alt+Pause)
continues the same running program. The panel has no Close control and does
not block the rest of the desktop. Automatic inactive-window, hidden-page,
snapshot and frame-drag pauses do not display it.

## Text and graphics screens

The pinned classic DOSBox has a small native bridge at its completed-video-
frame boundary. It reads the active VGA text buffer, not DOS stdout, so direct
B800 writes by file managers and editors are visible too. Standard CP437 text
uses the existing `TVTextScreen` without a bitmap font: real DOM character
cells with foreground/background palette indexes. Geometry and cell scaling
follow the native mode; 80x25 and 80x50 are covered by browser tests. The shared
IBM VGA web font is fitted to the mode's character grid, not replaced with a
pixel screenshot. Native cursor scanlines and blink phase are supplied by
DOSBox; there is no independent browser blink clock for the live screen.
Background cells form an untransformed display-sized grid with device-pixel-
snapped outer bounds. Only glyphs are scaled; their individual edges are
snapped to the font's whole-CSS-pixel raster grid, not uniformly centered in
fractional cells (half-CSS-pixel heights can lose a font row even on Retina).
Neighboring backgrounds and single/double box lines therefore meet even at
fractional zoom or high-DPI resolutions.

Graphics modes continue using the existing canvas. Custom/dual hardware fonts,
underline effects, panning/split-screen and unsupported machines/layouts also
retain DOSBox's pixel renderer rather than showing incorrect characters.
Switching presentations never restarts the emulator or changes mounted drives,
memory or the input target. UHF bitmap-font TextScreens remain unchanged.

The top-level `text_rendering` boolean in `thelpviewer/config/dos-prompt.json`
selects the presentation. The default, `true`, uses character cells where the
native font/mode is supported and canvas otherwise. Set it to `false` to use
DOSBox's canvas for everything, including ordinary text. Restart the server
and reopen DOS Prompt to apply it; neither rebuilding C nor modifying user
data is required. A program that uploads its own font always uses its exact
native pixels, even with `text_rendering: true`; restoring the ROM font
returns to character cells automatically.

The bridge protocol uses the existing CI message transport. `thelp-screen`
carries a copied Uint8Array, not a RAM dump: 16 header bytes, sixteen RGB
palette entries and interleaved character/attribute bytes. Header offsets:
0 text/fallback flag; 1 columns; 2 rows; 3 glyph height; 4 glyph width;
5 attribute-blink enabled; 6 blink phase; 7 cursor visible; 8/9 cursor column/row
(255 if absent); 10/11 cursor first/last scanline; 12–15 reserved zero.
Palette RGB starts at 16; cells start at 64. A fallback packet is 16 zero bytes.
Changed state is emitted at native frame boundaries, with a periodic refresh
for late listeners. The API preserves this one typed message instead of
converting it to a log string. Source, reproducible build steps and license are
in [the bundled emulator README](../../www/assets/dos/emulators/README.md).

**Zoom 2×** enlarges the window's DOS client area up to twice its current size,
limited uniformly by the available desktop. **Zoom back** restores the prior
window position and dimensions. This uses the shared window resizer/frame,
not browser fullscreen or extra CSS scaling; the DOS image retains its aspect
ratio. The frame's Zoom button and title-bar double-click use the same
`TVWindow` command, without a separate mover maximize action. A successful cloud
save is silent, including periodic autosaves, so it does not cover the DOS
image. Save failures still display an error.
Size limits include the window frame but never reserve space for its shadow;
at the desktop edge the shadow is simply clipped.

**Windows → Default Size** restores the declared default width (82 columns for
the standard DOS Prompt) and derives its height from the current video mode,
fitting both dimensions to the desktop. It clears maximization/2× zoom without
restarting DOS or changing the running program, mounted media or private disk.

When DOSBox changes video mode, the window keeps its client width and adjusts
its height to the new screen ratio, rounded up to TVision character rows with
the shared frame included. For example, switching from 640x400 to 640x480
adds five rows with 8x16 cells and a 640-pixel-wide client. If the taller window
cannot fit the desktop, its width is reduced too; its position is kept where
possible, otherwise moved back inside the desktop. Normal frames at the same
resolution do not resize the window or undo manual adjustments. Zoom back's
stored geometry adapts to the new mode as well. Fullscreen and maximized
windows stay in their mode; pending video-size changes apply on returning to
the normal window. There are no per-program resolution exceptions.

Dragging the resize corner horizontally or vertically scales both client
dimensions to the current DOSBox pixel width/height ratio. The shared resizer
sends a `TVEvent` Resize command to the owned window before drawing; only DOS
constrains its proposal, so HELP/document windows still resize freely. The
two frame columns/rows are excluded from the ratio. Dimensions stay on the
TVision character grid, with less than one row of rounding, and respect the
desktop space available from the fixed top-left corner. The initial frame and
Zoom use the same sizing calculation. Fullscreen/maximized clients may still
have black letterboxes to fit the display without stretching the DOS image.

DOS uses both sides of the shared TVWindow frame, including its single-line
inactive state when another window covers it. The shared window mover caches
drag limits at mouse-down, coalesces position updates per browser animation
frame and commits the final mouse-up position before saving workspace geometry.

DOS Prompt participates in the existing `#tv=1.…` workspace state, including
window geometry, stacking/active window and Pause state. Restoring the URL
starts a fresh emulator session with the currently signed-in user's saved
overlay; it is not a CPU/RAM save-state. Commands, account identifiers and
private media IDs are not placed in the URL. Fullscreen requires a new user
gesture and is not restored automatically from a link. A local folder and its
permission handle are also excluded; select the folder again after a page reload.

Server Statistics lists opens under **Tools → dos-prompt** and duration buckets
under **Tool time**. The shared managed-window lifecycle excludes startup,
explicit Pause, inactive windows and hidden tabs. It does not inspect DOS
commands or identify which DOS game/program is running. Durations are sent on
close/page exit; abrupt crashes or failed exit delivery can lose an interval.

## Native fullscreen

**DOS Prompt → Fullscreen** requests the browser's native Fullscreen API for
the DOS screen container. Only DOS is visible: there is no TVision menu/frame,
desktop or browser toolbar. The image keeps its aspect ratio, with black
letterboxing where needed, and either text or graphics retains keyboard/mouse
input. Manual Pause and its embedded Resume button remain visible in fullscreen.
Entering/leaving fullscreen alone does not change the TVWindow geometry or
maximized state. A video-mode change while fullscreen defers the normal-window
height adjustment until fullscreen exits.

Press **Alt+Enter** again to exit (main or numeric-keypad Enter). Fullscreen
control shortcuts are captured by the owning DOS input view even if browser
focus moves off the canvas; they still pass through `TVEvent.handleEvent()`.
Use the browser's **Esc** fullscreen exit, or **Ctrl+Alt+M** to leave fullscreen
and open the DOS Prompt menu. Restarting DOS keeps fullscreen; closing its
window exits only its own fullscreen, not an unrelated fullscreen element.
The DOS `EXIT` command leaves fullscreen before saving/stopping so the stopped
window and its status remain visible. Ctrl+Alt+M also works after DOS stops.
An unexpected emulator stop also exits its own native fullscreen. A late
fullscreen-change notification cannot block the next fullscreen request.
The browser must allow Fullscreen API and the request must follow a user
gesture. Embedded browsers/iframes may deny it; denial displays an error,
not a simulated CSS fullscreen. Safari/device-specific behavior still needs
manual verification.

## Software sources and first use

On the server or in local development, a signed-in administrator can use **User name →
Configuration → Rebuild DOS C** to recreate this shared disk from the current
manifest. Confirmation is required; the current browser saves/closes DOS first.
The server moves only `var/dos/c/` to a unique recoverable backup under
`var/backups/dos/`, keeps `data/dos/users/` overlays/media and cached source archives,
then runs the normal initial preparation again. Other browser tabs must restart
DOS after the base changes. A successful rebuild rotates older DOS backups:
default two, shared with package-change snapshots, configurable via Server
Configuration's Retained backups per type. Failed rebuilds keep recovery copies.
Ordinary members cannot rebuild; the action is
rejected while preparation is already running. See
[local rebuild actions](Accounts.md#local-rebuild-actions) for API/progress and
manual backup recovery. The built-in HELP now has a DOS Prompt topic (hc2320),
including these operations, keyboard bindings, streaming and private storage.

For Docker Desktop on an iCloud-backed macOS checkout, the installed receipt,
shared C files and private overlays must exist physically on the host.
`[Errno 5] Input/output error` during Checking disk can mean an offloaded
placeholder, not a failed software install. Restore file availability rather
than rebuilding the disk or deleting private data; the management script's
Docker preflight covers these paths. See
[cloud-backed storage recovery](Server%20Content.md#macos-cloud-backed-storage).

`THELP_DOS_CONFIG_PATH` selects the manifest, defaulting to
`thelpviewer/config/dos-prompt.json`; Docker Compose already passes it through.
On fresh 2.1 servers HELP Packages opens after administrator sign-in; DOS
Packages is a separate menu entry using the same dialog base. Confirmation
starts preparation. Later changes
use **Admin → Configuration → DOS Packages…**, independently of HELP products.
Categories cover platform/action/racing/sports/puzzle/strategy/RPG
games, programming, editors, file managers, archive tools, graphics, sound and
antivirus and office software. They appear on the left; the selected category's package checkboxes
are on the right. The checkbox below the right pane selects/clears only that
category; the bottom Select All / Deselect All buttons affect all categories.
Required packages remain checked and disabled in both cases. COMPRESS and Volkov
Commander are required by the manifest and cannot be uninstalled through the
dialog, API or direct disk reconfiguration; rebuild retains this selection rule.
Changing categories retains the complete draft;
Apply confirms installation/uninstallation across all DOS categories. Close
discards the draft. HELP Packages remains a separate dialog.
Before selection, opening DOS does not download the whole source manifest.
It bootstraps only sources already marked `required: true`, not optional saved
choices. Required packages lead the queue and preparation order. Before the
disk becomes ready, the server checks each required source's recipe key and
nonempty owned-file inventory against regular files on C. A receipt with missing
files is not a completed installation: the normal installer/cache repairs the
package, preserving other installed programs, administrator files and overlays.
This also applies to an empty disk whose old receipt says `_complete: true`.
While mandatory preparation runs, `/api/dos/session` and `/api/dos/bundle` return
503 and the window shows progress without starting jsDOS. A mandatory-source
failure keeps those endpoints blocked and displays the error; readiness is never
inferred from the configured selection alone.
Existing completed C disks are still loaded lazily on the first DOS request.
Package updates report `configuring: true`, independently of `initializing`.
The browser labels this wait **Updating DOS C**, not **Initializing DOS C**.
The latter is reserved for creating/rebuilding a disk, not adding software to
an already initialized disk. Emulator startup waits until publication finishes.
The DOS window reports
preparation status through a shared `TVLoadingDialog` with a solid-cell gauge,
source name and download/extraction phase. Cancel closes the wait, not the
server installer; Restart reconnects to its progress. FreeDOS EDIT (`EDIT`),
BlockDrop, Sudoku86, Zmiy and Volkov Commander 4.05 (`VC`) retain their licence
notices. Volkov Commander has no separate source-code package; its original
BSD copyright/conditions/disclaimer are included as LICENSE.TXT through the
existing `files` mechanism. The same package seeds `TOOLS/VC/VC.INI` with the
prepared Volkov Commander preferences. VC.INI is a 511-byte binary file, so its
exact contents are stored as Base64 in the package's `files`, not converted to
text or generated by a BAT. Private overlay settings remain independent.
Quadrax's primary language is Slovak. Its package
also creates `GAMES/QUADRAX/QUADRAX.CFG` through `files`, with Sound Blaster 16
at port 220, IRQ 7, DMA 1, music/effects enabled and the game's keyboard
settings. It is plain CP437/CRLF text, not a post-install BAT or server-side
special case. Private overlay configuration files continue to override these
shared defaults and are not rewritten by package installation.
`TYPE C:\SOFTWARE.TXT` lists installed software
and launch commands.

The manifest also configures Prince of Persia, Wolfenstein 3D, DOOM,
Battle Chess, Commander Keen, Cannon Fodder 1/2, Catacomb, Color Lines, Lemmings, The Lost Vikings,
Quadrax, Supaplex, Tetris, The Incredible Machine 1/2, Formula One Grand Prix,
Grand Prix 2, Ironman Super Off Road, Lamborghini and Dungeon Master 1/2.
Lost Vikings 2 is deliberately excluded. Most earlier packages come from
BestOldGames; Lemmings uses Internet Archive because the site's ZIP contained
a Windows executable. The stable `bog-lemmings` source ID is retained. The new
optional games use verified Internet Archive packages:

- Cannon Fodder 1/2 select only `_dosbox/_gamefiles/*` and `docs/*` from the
  portable 7z packages. Windows DOSBox, DLLs, launchers and shaders are not
  installed. C:\GAMES\CANNON\START.BAT runs `CF_ENG.EXE /F`; the sequel uses
  C:\GAMES\CANNON2\CANNON.EXE. No host launcher or interactive installer runs.
- Commander Keen 1 remains the existing shareware package. Episodes 2–6 are
  independent selections under GAMES/KEEN2 through KEEN6; episode 5 strips two
  archive directories. Executables are KEEN2, KEEN3, KEEN4E, KEEN5E and KEEN6C.
  Keen Dreams is the original DOS 1.13 EGA shareware, not a modern remake and
  not a new numbered seventh episode; run GAMES/KDREAMS/KDREAMS.EXE.
- Catacomb, Catacomb II, Catacomb 3-D and The Catacomb Abyss have independent
  targets CATACOMB, CATACOM2, CAT3D and CATABYSS under GAMES. The first two use
  CATACOMB.EXE, 3-D uses CAT3D.EXE and Abyss uses CATABYSS.EXE.

These entries default to unchecked; adding them to configuration never changes
an already prepared shared C or private overlays. Select them in DOS Packages
and confirm Apply. Archive URLs, exact member roots, path stripping, launch
commands and descriptions live in dos-prompt.json, not Python/UI conditionals.
Commercial entries require the operator's redistribution permission.

Vlak 2.01 and DOS Manažer 2.20 use the original author's distributions at
[breatharian.eu](https://www.breatharian.eu/sw/index.html), not a Windows port.
Vlak launches its original VLAK.BAT, keeping the compressed executable,
loader, scenes and graphics together. DOS Manažer extracts the ready runtime
from DOSMAN/DOSMAN.RAR, including its manual and LICENCE.TXT; it does not run
INSTALL or install the distribution's third-party shareware collection.
Text602 3.1 uses OS-DOS.NET's ready T602 tree, not its separate 3.0 installer;
Manager602 2.0 uses the portable M602.zip distribution from Sosej. Both retain
their original help/resources. New entries remain unchecked until Apply.
Calc602 uses the operator-supplied `assets/dos/c602-runtime.zip`: original
C602.EXE, C602.DRV, C602.HLP, fonts and printer drivers from the approved DOS
reference installation. It excludes saved C602.CFG settings, spreadsheets,
macros and test documents. The program creates settings in the user's overlay;
launch C:\OFFICE\C602\C602.EXE. It is a bundled package, not an external
download and not an interactive installer. Original copyright notices remain.
Additional optional packages include Winter Challenge, Summer Challenge,
Lotus: The Ultimate Challenge, and the original shareware first episodes of
Duke Nukum, Duke Nukem II, Crystal Caves and Bio Menace. Winter is flattened
from `TGameWnC/WINTER/`, Lotus from `LotusThe/`; the other game archives have
flat DOS roots. Launch WINTER, SUMMER, LOTUS, DN1, NUKEM2, CC1 or BMENACE1 in
their configured GAMES directories. Summer selects only original game/data
files, excluding its archive's patch launcher and Windows shortcuts; this does
not remove any protection the original executable may require.

The additional FreeDOS 1.4 packages retain their complete ZIP distribution,
licences, documentation and supplied source archives, without an installer:

| Package | C: directory and command |
| --- | --- |
| DOS Navigator 2.14 beta | `TOOLS/DN2/APPS/DN2`, `DN` |
| DOSZip 2.68 | `TOOLS/DOSZIP/BIN`, `DZ` |
| TDE 5.1w | `TOOLS/TDE/BIN`, `TDER` (real mode), `TDEP` (protected mode) |
| BIEW/Beye 6.10a | `TOOLS/BIEW/BIN`, `BIEW` (i686 required) |
| GrafX2 2.2 | `TOOLS/GRAFX2/APPS/GRAFX2/BIN`, `GRAFX2` |
| DOSMid 0.9.8 | `TOOLS/DOSMID/SOUND/DOSMID`, `DOSMID` |

DOOM, Wolfenstein, Keen 1/4 and Keen Dreams are shareware;
The Incredible Machine 1 package is an interactive demo. Permission
to distribute full games does not turn a source's demo into a full release.
The Lost Vikings requires its original `SETUP` before `VIKINGS`; the unconfigured
game reports a copy-protection error. Dungeon Master asks for a display mode;
the current Chrome/WASM smoke test stalls at that selector, even with a held
selection key. It reproduces both with worker/file-on-demand and with the
explicitly enabled direct/full-disk test configuration, so it is not specific
to chunk delivery. The cause and gameplay compatibility remain unresolved.
Norton Commander 4.0 is opt-in and uses original English media from
`archive.org/details/003492-NortonCommander40`, with a second distribution at
`archive.org/details/norton-commander-4.0-for-dos`. The first recipe opens the
7z's `003492_norton_commander/disk1.img`, then extracts `NC_ARC.EXE` and
`NC_ARCV1.EXE` as ARJ archives and retains `README.TXT`. The alternative ZIP
has a single `NC_ARC.EXE`; its Symantec ARJ variant is supported by unar (7-Zip
reports an invalid archive length for that variant). Neither executes INSTALL.
Both actual program binaries identify as Norton Commander 4.0; the old WinWorld
image identified as modified "MFF" and is not retained as an alternative.
The recipes were checked by extraction, not by a gameplay/runtime smoke test.
Commercial redistribution still requires the administrator's permission;
the package remains unchecked by default. Alternative recipes are handled by
the shared package downloader, not Norton-specific code.
Subsequent messages distinguish C-drive loading, runtime loading, backend
startup and the command shell. Network/backend waits have 30-second deadlines,
script loading 20 seconds and shell startup 15 seconds, rather than leaving
the initial preparation message displayed indefinitely.
The original licence and source archive are retained alongside the program.

### Programming and historical antivirus packages

The optional programming entries use original Embarcadero Museum archives:
Turbo Pascal 3.02, Turbo Pascal 5.5, Turbo C 2.01 and Turbo C++ 1.01.
They are prepared on the server, not offered as interactive INSTALL programs.
Turbo Pascal 3.02 starts with TURBO from C:\DEV\TP302. The other compilers
start from their BIN directories under C:\DEV\TP55, C:\DEV\TC201 and
C:\DEV\TCPP101. Extraction rules place help beside the compiler and create
INCLUDE, LIB, BGI, DOC and example/source directories as applicable. The
original 5.5/2.01 ARC containers are decoded by unar; 1.01 Borland split ZIPs
are assembled by the existing shared extractor before decoding. Post-install
BAT creates the C compilers' TURBOC.CFG include/library paths. No original
installer needs user interaction or writes an installation into the private
overlay. Editor-directory preferences may still be adjusted in the IDE.
These are historical publisher downloads, not a blanket public-domain
designation for every Borland release. Original download archives stay cached.

### Additional development and office software

The following packages are optional and initially unchecked. Installing the
application update does not select them, rebuild C or change private overlays.
Use DOS Packages and Apply; launch commands are also in C:\SOFTWARE.TXT.
Run each package's START first when present: compiler environments are local
to the current DOS shell, not competing global AUTOEXEC settings.

| Package | C: directory | Start / example |
| --- | --- | --- |
| Open Watcom C/C++ 1.9 | `DEV/WATCOMC` | `START`, `WCL HELLO.C` |
| Open Watcom Fortran 1.9 | `DEV/WATCOMF` | `START`, `WFL HELLO.FOR` |
| Free Pascal 1.0.10 | `DEV/FPC` | `START`, `FPC HELLO.PAS`; `FP` opens the IDE |
| FreeBASIC 1.10.1 | `DEV/FBC/DEVEL/FBC` | `START`, `FBC HELLO.BAS` |
| NASM 3.02 | `DEV/NASM` | `START`, `NASM -f bin HELLO.ASM -o HELLO.COM` |
| JWasm 2.18 | `DEV/JWASM` | `START`, `JWASMR` (real mode), `JWASMD` (DPMI) |
| DJGPP GCC 4.7.1 / RHIDE 1.5 | `DJGPP` | `START`, `GCC HELLO.C -o HELLO.EXE`; `RHIDE` |
| Microsoft Word 5.5 | `OFFICE/WORD55` | `START` or `WORD` |
| As-Easy-As 5.7 | `OFFICE/ASEASY` | `ASEASY` |
| Ability Plus 3.0 | `OFFICE/ABILITY` | `AB3` |
| VisiCalc, IBM PC 1981 | `OFFICE/VISICALC` | `VC`; `/SQY` quits |
| HIEW 6.50 | `TOOLS/HIEW` | `HIEW <file>` |

HIEW uses the author's free DOS 6.50 rebuild from
[hiew.ru](https://www.hiew.ru/), not the modern Windows demo. The shared
extractor opens the nested HIEW_650.ZIP and installs the executable, original
HIEW.HLP, HIEW.INI and HIEWE.650 manual. The detached archive signature is
retained under DOC. It is optional and unchecked until selected in Editors.

Watcom retains DOS tools/headers/libraries, not Windows/OS2 executables and
headers. Free Pascal uses the original project's nested DOS ZIP distribution.
FreeBASIC and DJGPP include the official CWSDPMI runtime. DJGPP uses C:\DJGPP,
not C:\DEV: its libc reserves the /dev namespace for devices. FreeDOS distributions retain original
licences, documentation and supplied source archives. The manifest uses
64 MiB DOS memory. The shared software library has no aggregate byte or file-count
quota; only private user data has a capacity quota.

Word is Microsoft's original British-English self-extracting ZIP. Its KWAJ
files are expanded to header-provided original names; MAKEVID builds the VGA
SCREEN.VID once during preparation. Neither Setup nor a Windows host runs.
As-Easy-As expands its embedded ARC; NOTICE.TXT records TRIUS's original free
licence announcement and public serial. Ability is the publisher's complete
DOS office-suite ZIP, not a Windows installer. VisiCalc is Dan Bricklin's
original IBM PC executable under the Lotus personal, non-commercial licence,
not public domain or an unrestricted redistribution grant. Its notice links
to those terms; operators must check their intended use. It only sees its
current directory. Excel has no standalone DOS release; these spreadsheets
are DOS alternatives, not Excel binaries. Archived original download URLs
are used where the publisher's old server is unavailable.

COMPRESS is the required archive toolkit (`id: "utils"`, target `COMPRESS`).
It combines original FreeDOS/DJGPP packages for ZIP/UnZip, UnRAR, ARJ,
P7ZIP, 7-Zip 24.09, LHA, CAB, GZIP, BZIP2, TAR, ZOO, LZIP, LZMA, LZOP,
LPQ1 and the CWSDPMI runtime, plus LZEXE 0.91e, UnLZEXE 0.91a, UPX 5.2.1,
DIET 1.45f, PKLITE 2.01, ARC 6.02/ARCE 3.1c, UC2 revision 3 and the
operator's original UNARJ241.EXE
from DOS Universum's DOSBox disk. That immutable local source envelope
remains in `thelpviewer/server/assets/dos/`.

Every component explicitly selects program/runtime paths with `members` and
uses the shared `extract` rules to put original manuals, readmes and licence
notices in **C:\COMPRESS\DOC\<tool>**. Thus unrelated README/LICENSE files do
not overwrite each other. Some FreeDOS packages keep their licence only in a
nested source archive: the recipe extracts the licence, not the program source.
UnLZEXE 0.91a's original manual and terms are in DOC\UNLZEXE\UNLZEXE.DOC.
Raw downloads stay unchanged under
`var/downloads/dos/`.

All programs remain directly in C:\COMPRESS, without BIN, ARCHIVER or UNARJ
subdirectories. `strip_components` removes each verified archive prefix;
filenames remain the original names from their archives:

| Command | Implementation |
| --- | --- |
| `P7ZIP`, `P7ZIPR` | Existing P7ZIP DOS tools |
| `7ZA`, `7ZR`, `7ZM`, `7ZDEC` | DOS 7-Zip 24.09 aggregate, reduced, minimal and decoder builds |
| `LZIP`, `LZIP-REC` | Lzip compressor and recovery tool |
| `LZMA`, `LZMADEC`, `LZMAINFO` | LZMA compressor, decoder and stream information |
| `LZOP`, `LPQ1` | Additional LZO and LPQ archive tools |
| `LZEXE`, `UNLZEXE` | Compress DOS MZ executables and unpack LZEXE 0.90/0.91 files |
| `COMTOEXE`, `INFOEXE`, `UPACKEXE` | LZEXE's COM converter, executable information and EXEPACK unpacker |
| `UPX` | UPX 5.2.1 executable packer, DOS build |
| `DIET`, `PKLITE`, `CHK4LITE` | Period executable/data packers and PKLITE recognition utility |
| `ARC`, `ARCE`, `MKSARC` | ARC 6.02 archive creation/extraction, its matching ARCE 3.1c and self-extractor builder |
| `UC`, `VU` | UltraCompressor II revision 3 command line and graphical shell |

The original [LZEXE author archive](https://bellard.org/lzexe/) and
[UPX release](https://github.com/upx/upx/releases/tag/v5.2.1) supply those
tools. Other period originals are retrieved from SAC and the Metropoli archive,
with exact release URLs in the manifest. UC2's original self-extractor is not
supported by host archive tools: the existing isolated server DOSBox runs it
once, moves its documentation into DOC\UC2 and removes UC2R3.EXE. Neither it
nor POSTINST.BAT is published on the shared disk.
To browse UC2's native manual after relocating documentation, change to
`C:\COMPRESS\DOC\UC2` and run `UC -??`; UC remains reachable through PATH.

UnLZEXE, DIET, PKLITE, ARC/ARCE and UC2 retain their original personal/commercial-use,
evaluation and redistribution restrictions. Keeping documentation does not
grant additional permission, and the collection is not wholly open source.
No registration keys are included. Read each tool's original documents before
using or redistributing it.

The DOS 7-Zip build comes from [retro7zip](https://github.com/dajhorn/retro7zip)
via the FreeDOS repository. Its reduced/minimal variants use less memory;
they do not support every format handled by the aggregate build.

RAR is a separate, optional `rar-dos-393` package from the
[original RARLAB archive](https://www.rarlab.com/rar/rarx393.exe).
The publisher identifies 3.93 as the
[last DOS/OS2 release](https://winrar.es/descargas/39/descargar-rar-393-para-dos-32bits-os2-en-ingles).
RAR32.EXE, EMX/RSX runtime files, DEFAULT.SFX and RARFILES.LST are installed
directly in C:\COMPRESS too; manuals and licence notices go to DOC\RAR.
Run `RAR32`. It can create and
extract older RAR archives, not RAR5. It remains proprietary shareware with a
40-day evaluation, not freeware. The operator confirmed redistribution
permission; no registration key is included. Both archive packages declare
`"path": "COMPRESS"`; the installer adds C:\COMPRESS to the shared PATH once.

Antivirus includes the complete ThunderBYTE 8.03 evaluation package (TBAV)
and the free, limited Norton AntiVirus Michelangelo Edition (NAV).
ThunderBYTE's original LICENSE.TXT permits unchanged complete evaluation
redistribution, not unlimited registered use; no registration key is provided.
All antivirus files and licence documents are retained. These obsolete tools
run inside DOSBox and are not protection for the host or current malware.
New entries default to disabled until an administrator explicitly selects them.

NOD-iCE 7.24 was located at the Slovak Antivirus Center, but its original
NOD.DOC expressly says it is not free/public-domain/shareware and limits
evaluation to 15 days, excluding organizational use. It is not offered as
abandonware here. F-PROT 3.16f's DISTRIB.TXT separately requires permission
for bundling/preinstallation, so it is not included either. No verified Avast
DOS program archive with suitable distribution terms was found; a freeware
mention or old registration key alone is not enough to add a package.

The manifest contains `cycles` (`auto`, `max` or a numeric DOSBox cycle count),
`memory_mb` (4–64), `text_rendering` (boolean, default true), `max_media_bytes` (default
128 MiB), a `categories` list of unique `{id, label, icon}` entries and a `sources`
list. Each source has:

- `id`: unique lowercase identifier;
- `title`: readable name displayed in DOS Packages;
- `required`: optional boolean, default `false`. `true` forces inclusion in
  every explicit selection and disables its checkbox. It overrides `enabled`
  and empty selections; it is an installation policy, not an installed receipt;
- `language`: primary interface language, e.g. `cs`, `sk`, `en`, `en-US`;
  optional region suffixes use uppercase ISO country codes. The UI appends a
  Unicode flag after the name/installed marker, aligned by JS space padding.
  Names and flags are one text label and scroll together. DOS Packages is
  90 columns; shortened titles fit its standard pane without horizontal scrolling.
  `und` (unverified) and `mul`
  (mixed-language collection) use a globe rather than an invented flag;
- `description`: plain text displayed in the shared Description box;
- `category`: ID from `categories`; omitted values use the neutral Other group.
  Unknown IDs are rejected by the configuration API;
- `url`: HTTPS archive URL or HTML download page; archives must produce a ready
  program tree, not require an interactive installer;
- `file`: instead of URL, an immutable bundled archive filename under the
  server's assets/dos directory; absolute paths, traversal and links are refused;
- `format`: `zip`, `img`, `archive` (unar/7-Zip-supported archives), or
  `collection` with 1–32 `archives` entries. Each component uses the same
  download/cache/extraction definition and optional target relative to the
  package. `retain_archive` optionally stores its unchanged envelope at a
  validated package-relative path. Components cannot nest collections;
- `image_member`: optional exact inner disk-image path in an archive;
- `download_forms`: optional ordered POST form selectors; the downloader
  submits fresh hidden fields and the named submit button, retaining cookies;
- `target`: optional directory on C, such as `FREEDOS`;
- `members`: optional case-insensitive glob patterns selecting paths **inside
  the archive**, before adding `target`. For example `["PRINCE/*"]` keeps the
  Prince game directory and skips other archive content. The default `["*"]`
  extracts all files; selective FreeDOS entries retain the needed program,
  licence documentation and source archive. This is not a DOS drive mount
  list and does not control user uploads;
- `strip_components`: optional integer 0–16 removing that many leading path
  components from selected archive files before adding `target`. Member globs
  and traversal checks use the original path. Paths too short to strip and
  resulting case-insensitive filename collisions are errors, not silent
  overwrites. This merges multi-disk compiler distributions without modifying
  the original file contents;
- `exclude_members`: optional case-insensitive glob exclusions applied to the
  original archive paths before stripping, after `members` selection;
- `expand`: optional `"microsoft"` expands selected KWAJ/SZDD files with the
  shared libmspack decoder. Other files are unchanged. Original header names
  replace compressed names in the same directory; embedded directories,
  invalid paths, collisions, corrupt streams and quota overruns are rejected;
- `extract`: optional 1–64 output rules combining selected original files
  (`members`, `strip_components`, `target`) and extracted inner `archive`
  files (`format`, `members`, `strip_components`, `target`). An archive can be
  a list of raw ordered parts; `format: "borland-split"` delegates CA1/CA2
  header removal and ZIP completeness checking to the shared assembler.
  Conflicting output bytes, missing parts and unsafe paths fail publication;
  each package's expanded output remains bounded by 256 MiB and 4096 files,
  while downloaded envelopes have a separate 64 MiB safety bound. These are
  archive-processing safeguards, not a quota on the installed common library;
- `files`: optional list of generated text or binary files, relative to
  `target`, in addition to the selected archive files. Each entry has `path`
  and exactly one of `text` (individual CP437 lines with CRLF) or `base64`
  (strict Base64 bytes, without whitespace or a data-URL prefix);
- `license`: a human-readable provenance/licence note, not a permission check.
- `path`: optional single directory relative to C, independent of `target`.
  For example, `"path": "COMPRESS"` adds `C:\COMPRESS` and
  `"path": "TOOLS/VC"` adds `C:\TOOLS\VC`. Absolute paths, traversal and
  command separators are rejected. Only installed packages contribute entries;
  equal directories are deduplicated, and uninstallation removes an entry
  only when no remaining package declares it. This also provides tools to
  isolated post-install DOSBox runs.
- `post_install`: optional individual CP437 BAT lines, including optional
  `@ECHO OFF`. The server writes POSTINST.BAT and calls it once after extraction
  in native DOSBox with only a temporary C mounted, secure mode enabled and a
  120-second timeout. The package sees its final C:\target path and an unchanged
  copy of commands from installed packages' declared `path` directories.
  Output outside the package, altered
  utility files, links, invalid names, excessive size/count and unsuccessful
  completion are rejected. The generated POSTINST.BAT is discarded before
  publication; ordinary runtime BAT files are retained. It is never called on
  normal browser boots; existing completed installations are not
  rerun. Apply a changed recipe by removing/reinstalling it or Rebuild DOS.
  This is for administrator-trusted software, not a general security sandbox
  for arbitrary DOS executables. Scripts are never executed in the host shell.

ZIP extraction rejects traversal, symbolic links, duplicate DOS names and
excessive file count/expanded size. Trusted configured IMG sources reuse the
downloader's existing unar/7-Zip image extraction; Docker includes both and
native DOSBox for post-install. Native, non-Docker servers need these tools
installed before preparing recipes that use them.
Player-uploaded images are **not** extracted on the server. Only configure
software you may redistribute, and include required licence/source notices.
This deployment's administrator confirmed permission for the commercial games;
other deployments must obtain their own redistribution rights.

DOS sources no longer use `allowed_hosts`. Initial URLs, POST form actions
and redirects must use HTTPS without embedded credentials. Downloads may
follow a public CDN/other host automatically. Literal private/loopback URLs
are rejected, and the TLS connection's actual peer must be globally routable
before HTTP request headers/body are sent. Private HTTPS proxy peers are also
rejected. TLS certificate validation, byte limits and extraction/path checks remain.
The standard manifest does not pin archive hashes or sizes. Download cache keys
are derived from source URLs/forms; progress uses HTTP Content-Length when available.
Individual lazy C-file hashes and overlay integrity checks are still generated.
This is specific to DOS sources; the MIDI manifest is unchanged.

For example, inside a source with `target: "GAMES/EXAMPLE"`:

```json
"files": [
  {"path": "RUN.BAT", "text": ["@ECHO OFF", "GAME"]},
  {"path": "DATA/EXAMPLE.BIN", "base64": "AAECAw=="}
]
```

This creates `C:\GAMES\EXAMPLE\RUN.BAT` and a four-byte file (00 01 02 03).
Configured content overrides the same selected archive path in the incoming
fresh installation. It does not overwrite an existing on-disk file with
different bytes during resume/explicit installation: that reports a conflict.
New missing files can be added during explicit installation. Ordinary server
starts leave optional packages on completed base disks frozen; required-package
receipts/files are checked before boot and missing tools are repaired. Use Rebuild DOS C to
apply a changed recipe from scratch. User overlays are not rewritten. Paths,
case-insensitive duplicates, file counts and combined byte sizes are checked.
When any source declares `path`, the installer manages the shared
AUTOEXEC.BAT's SET PATH line during initialization and explicit package
changes. Paths come first in manifest order, followed by the baseline from
the root AUTOEXEC.BAT definition (Z:\ in the default manifest). Put additional
permanent search directories in that configured baseline; manually editing
the generated SET PATH line is not persistent. Other existing boot lines are
preserved. If no SET PATH exists, it is inserted before the first program
launch, following a leading @ECHO OFF if present. Normal starts of a completed
disk do not rewrite this line. Private AUTOEXEC.BAT overlays remain independent
and can override the shared file, including its PATH.

The default Volkov Commander entry demonstrates `files` with `START.BAT`
and the binary `VC.INI` encoded as Base64.

For a targeted forced reinstall, the server-side Python API accepts
`store.configure(selected_ids, reinstall=[...])`. Include every package to
retain in `selected_ids`; `reinstall` must be a subset after mandatory packages
are included. Only those packages' recorded owned files are removed from the
staged generation, and their receipts are cleared so the normal installer
extracts them again. Root files, files owned by surviving packages, unowned
manual files and private overlays remain protected. Old files no longer in the
recipe disappear only if owned exclusively by a replaced package. Downloads
are reused; this does not force another network transfer. Publication and
backups use the same atomic workflow as other package changes. When invoking
this directly for maintenance, stop the web server first to exclude concurrent
writers. This is not an HTTP endpoint or a change to ordinary Apply behavior.
DOS Apply prepares up to three inputs while publishing each completed package
in its own staged transaction. Earlier published packages survive a later
download, post-install or publication failure; restart/retry checks receipts and
owned files before skipping them. The required boot tools publish as one group,
and unchecked packages are removed only after requested additions succeed.
Unchanged files can share hard-linked storage across staging/backups, with a
copy fallback on unsupported filesystems; changed files are always replaced
atomically, never edited through those links.
`Awaiting installation` means extracted input is ready;
`Awaiting publication` means installation into staging has finished. Such rows
remain unfinished until that package's live disk generation and receipt are
published successfully, not until every selected download finishes. Existing
published queue rows do not revert to waiting during later package transactions.

Root-level `files` uses exactly the same list of `path` + `text` or `base64`
definitions as package `sources[].files`. Root paths start at C, while package
paths start under `target`. `AUTOEXEC.BAT` is an ordinary root text entry;
binary root files are also supported. During fresh initialisation/rebuild,
root recipes take precedence over archive/package paths. Ordinary starts do
not rewrite the disk, and explicit installation only fills missing root files,
preserving administrator edits. The old `initial_files`, `autoexec.bat` and
`config.sys` root keys are rejected with a migration message; no compatibility
constructor/reader is retained. For example:

```json
"files": [
  {"path": "AUTOEXEC.BAT", "text": ["@ECHO OFF", "SET PATH=C:\\TOOLS;Z:\\"]},
  {"path": "DATA/EXAMPLE.BIN", "base64": "AAECAw=="}
]
```

Trusted browser startup mounts the virtual drives, then calls `C:\AUTOEXEC.BAT`.
There is no default CONFIG.SYS entry in `files` because
DOSBox's internal DOS does not interpret it. Existing shared disks are not
rewritten by a configuration/schema change; an older CONFIG.SYS can remain inert.
Engine settings use `memory_mb` and `cycles`. `software_catalog` supplies
header lines for generated SOFTWARE.TXT.

## Game sound setup

The supplied DOOM archive has `snd_musicdevice=0` and `snd_sfxdevice=0` in
DEFAULT.CFG: both music and effects are disabled. In `C:\GAMES\DOOM`, run
`SETUP`, select **Sound Blaster** for music and effects, and configure effects
for **port 220, IRQ 7, DMA 1**. Save the configuration and launch DOOM.
For signed-in users the changed DEFAULT.CFG is stored in their private overlay,
not another user's settings or the common disk. Remember **Save C to cloud**.

DOSBox creates the BLASTER environment variable for its emulated card
automatically; `SET BLASTER` displays it. The default Sound Blaster 16 uses
`A220 I7 D1 H5 T6`. Setting BLASTER alone does not enable sound in a game's
disabled configuration. Use each game's setup utility and choose an emulated
device it supports. Web Audio also requires browser permission/user activation;
click the DOS canvas after restoring a URL if audio has not been unlocked.
See the [DOSBox sound documentation](https://www.dosbox.com/wiki/Sound).

New downloads use readable `<package-id>/<archive-name>` paths with identity
and checksum sidecars in `var/downloads/dos/`; upgrade migrates the
legacy `var/dos/downloads/` cache there and archives its original. Verified files are
installed under `var/dos/c/`; `var/dos/installed.json` records installed
source-recipe keys and per-package `_files` ownership. Old SHA-pinned receipts
are recovered once from retained checksum-proven archives whose contents match
the shared disk, before migrating those caches to readable names. No C files or
private overlays are changed; missing/modified/ambiguous data is not guessed.
After successful initialisation its `_complete` flag freezes optional
automatic installation. Before boot, required recipe keys and their owned files
are still checked; missing required tools use the normal installer/cache before
the disk becomes ready. Other optional source-list changes and deleted optional
files do not trigger downloads or repairs. Different administrator-edited bytes
are never overwritten by automatic repair: conflicts remain errors. Interrupted
initial preparation resumes from installed required-package receipts/files.
Runtime memory/cycle/quota settings still reload on server restart. Later
software changes use the administrator menu → Configuration → DOS Packages → Apply.
The existing maintenance adapter `python -m thelpviewer.tools.install_dos_sources`
also remains available. Installation adds selected packages without overwriting different existing
files and refreshes SOFTWARE.TXT. Confirmed checkbox deselection uninstalls
package-owned shared files, with a staged disk, receipt and recoverable backup.
Other packages' shared files, root configured files and private overlays/media
are retained. Legacy ownership needs the cached archive; missing or ambiguous
ownership fails before live changes. Unknown removed manifest IDs are preserved.
editing source JSON alone does not install new packages on a completed disk.
See [Server Content](Server%20Content.md) for API, selections and progress.

Boot ZIPs include all parent-directory entries, ordered before files. This is
required by the emulator's libzip extractor; a ZIP that desktop unzip accepts
can otherwise fail with `No such file or directory` on a nested path.

## Private C-drive overlays

The shared C drive is never written by a user's DOS session. The boot ZIP
contains only directory entries, trusted DOSBox configuration and a file
manifest, not the C file contents. A worker adapter creates virtual files and
fetches their data only when DOS reads them, in chunks of at most 64 KiB.
HTTP uses gzip when accepted; the browser decodes it automatically. A 16 MiB
LRU chunk cache bounds read caching. Writes materialise the affected file into
the browser's in-memory filesystem, not the whole disk. Large mounted media
are still transferred as a complete image; they are not streamed yet.

New/changed files and empty directories are ordinary filesystem entries in
`data/dos/users/<internal-account-id>/c/<revision>/`. The adjacent
`overlay.sqlite3` holds names, sizes, hashes, deletion markers and the current
revision, not file BLOBs. Existing SQLite-BLOB overlays migrate automatically
without losing deletions. Current and previous generations are retained for
recovery; older generations are removed after successful saves. The internal
ID comes from the session cookie, never a caller-supplied username/path.
In the standard Compose deployment these are ordinary host files inside the
project's `data/`, mounted as `/app/data` in the container. `THELP_DATA_DIR` can
change that root in other deployments. Savegames and game configuration are
stored only after a successful overlay save; guests have no persisted account
directory. Uploaded CD/floppy images live in the account's `media/` directory.
Back up `data/dos/users/` together with `data/accounts.sqlite3`, which maps the
stable internal IDs to accounts; a username change does not rename the disk.

Saving briefly pauses DOS and scans C. The worker tracks changed files so
unread shared files are not downloaded just to compare them. Unchanged private
files are retained server-side by name and their expected SHA-256 hash; only
changed/new contents are uploaded. The server verifies those hashes under the
same lock as publication. Identical saves do not advance the revision or rotate
snapshots. Implicit parent directories are not counted as new private edits.
The server replaces the private overlay transactionally and validates paths,
file count, private capacity and file/directory collisions. An older revision
is accepted only if the complete proposed overlay (file hashes, deletion markers
and empty directories) already equals the current saved state, for example a
retry after losing the successful response. Other stale saves are rejected;
a base hash check rejects saves after the common disk changes. No automatic
overwrite or merge of conflicting disks is attempted. Close/reopen DOS to load
the latest cloud disk; this loses the old window's unsaved C changes and RAM.
No user's files or deleted-file markers affect another account.

The default private quota is **64 MiB**, excluding all shared software.
An authenticated admin can change the default or set individual overrides in Users;
the Account dialog shows committed overlay usage and capacity. Change the default in **User name → Configuration → Server
Configuration** (1–256 MiB).
It is stored in `data/server-settings.json` and enforced on each server save.
Changing it does not delete existing data or stop DOS writes immediately;
an over-limit save fails and leaves the last good overlay intact. Restart DOS
to refresh its advertised client-side allowance. Backup generations are not
included in the logical quota, so physical storage may be larger.

Authenticated sessions save every 60 seconds while active and the page is visible, on **Save C to
cloud**, before normal Close/Restart and when the DOS `EXIT` command returns
from the interactive `COMMAND.COM` to the trusted boot script. The parent
shell remains alive for the filesystem save; only then does the adapter stop
DOSBox using its public `exit()` API. If cloud saving fails during normal Close,
a standard message box offers **OK** to close without saving this window's C
changes, or **Cancel**, Escape/[] to keep DOS and its changes open. This never
overwrites the other window's saved disk. Local D is flushed before cloud C;
a local-folder save failure still blocks closing rather than discarding local
edits. Use manual Save before closing
the browser/tab: unload, crashes or loss of network cannot guarantee upload.
Signing out, expiry or switching accounts closes the old DOS window without
uploading C under the new identity; local D is saved separately first. Unsynced
C changes are then discarded. A failed local flush retains the paused window.
Guests have
a temporary C drive without server persistence or media upload.

This is file persistence, not an emulator save-state: restart resumes saved
configuration/savegames but not the running program, CPU state or RAM.

## Local folder (D)

**DOS Prompt → Mount local folder (D:)…** opens the browser directory picker
with `mode: "readwrite"`. The browser must support `showDirectoryPicker` and
the page must be a secure context (HTTPS or localhost). Chromium-based desktop
browsers such as Chrome and Edge support this; detect the API rather than a
browser name. Other browsers show an explanation, not a file-upload fallback.
This feature requires the worker backend even if full-disk fallback is enabled.

Choose a dedicated folder: DOS programs can read, create, overwrite, rename and
delete its files. A confirmation warns about these rights without restarting DOS.
Selecting/cancelling a picker or cancelling confirmation does not modify the
folder. Connecting/replacing/disconnecting local D saves pending local changes
first and keeps the same DOS session, running program and C memory. Close files
and programs using D first: the worker rejects replacement while D has open
filesystem streams. Changing CD/floppy media still requires the ordinary restart.
**Disconnect local D** releases the folder, leaving an empty D slot; it does not
delete the host folder. CD always uses E; floppy uses A.

`DosLocalDrive` in `tv-dos-local.js` keeps the directory capability in the page.
A fresh, random, browser-local BroadcastChannel gives the DOS worker immutable
`File` snapshots, not the directory handle. The worker uses FileReaderSync to
read file slices on demand and keeps DOS modifications in its own memory.
No local files are read eagerly in bulk or uploaded to initialize D. Neither
the handle, folder name nor local file bytes are sent to the server; no server
local-folder flag is needed. Startup mounts `drive_d` as a reserved, initially
empty D slot. `DosLocalConnection` owns one browser-local channel per emulator;
the worker stages and swaps its contents only after rejecting open D streams.
Errors before publication preserve the old tree; mount identities in the local
state prevent a lost acknowledgement from writing a different folder's files.
The pinned backend's native `_rescanFilesystem` export invalidates DOS directory
caches before acknowledgement, without injecting commands or keyboard input.
Its classic mapper is a no-op, so Ctrl-F4/mapper events are not used. Host directory capabilities
stay in the page; the worker receives only immutable File snapshots. A restart
re-enumerates the selected folder, but normal connecting/disconnecting needs none.
If you manually unmount/remap D using DOS commands, restore the managed slot with
`MOUNT D drive_d` to use the local-folder menu again.

Local D changes are automatically written back through File System Access every
**two seconds**, including while another TVision window is active, and checked
when page visibility changes. The timer only reads a small revision record;
unchanged D does not pause DOS or scan/read its files. A changed revision is
saved with emulation briefly paused. This is separate from C's 60-second cloud
autosave: local flushes do not scan/upload C or require a THelp account/quota.
Close, Restart, DOS EXIT and Save C also flush D; saves are serialized so a
concurrent local flush cannot skip a requested cloud save.

There is no routine Save local D command. On failure DOS pauses, the error is
shown once and **DOS Prompt → Retry local D save** becomes available. Changes
remain in the DOS window; resolve the conflict/permission/storage problem and
retry, then Resume. Close/restart cannot silently discard a failed local save.
Forced browser close, reload, crashes and suspended/background-tab timers cannot
guarantee completion of an asynchronous write: the last unsaved changes may be
lost. This is buffered continuous saving, not synchronous host filesystem access.
Do not reload while saving or while an unresolved write error is displayed.

This is a session view, not a live filesystem watcher. Reselect the folder
(without restarting), or restart DOS, to see external changes. Before overwriting/deleting an existing
file, saving checks its identity, metadata and original bytes; a stale snapshot
or conflicting edit aborts the save. Do not edit the same files concurrently:
these checks are not an OS-level lock against a change racing the write itself.
Multi-file saves are not one atomic transaction; a filesystem/permission error
can occur after earlier entries were saved. Retain the window and resolve the
error before retrying. Directory removals are never recursive, so files added
outside DOS cannot be silently removed with an old directory snapshot.

DOS names use deterministic 8.3 aliases (for example `LONG_N~1.TXT`), retaining
the original host names for existing entries. New entries use their DOS names.
Bounds are 4096 entries, a 240-character DOS path and 64 MiB per file/per save;
choose a smaller folder for larger collections. A file/directory type change
at the same path requires reconnecting the folder instead of a destructive
replacement. These safety bounds are separate from the private C quota.

D is not automatically cloud-saved. However, a DOS program can copy any file
it can read on D to C; those copies follow the ordinary C cloud-save rules.
Only grant folder access to DOS software you trust.

## CD/floppy mounting and isolation

The menu chooses a local ISO/raw floppy image and uploads it under the current
account. A content-derived opaque ID deduplicates repeat uploads. At most
eight images per account are retained; the first UI does not yet manage/delete
that library. CD images must have an ISO9660 signature and fit the configured
media limit; raw floppies must have a boot signature, sector-aligned size and
be at most 16 MiB. These are preliminary format checks, not malware scanning.

One image is mounted at a time: floppy as A or CD as E (D is the local-folder slot).
Mount/eject confirms a DOS restart and saves C first. ISO images are read-only;
modifications inside mounted floppy images are not uploaded back. Copy their
configuration/save files onto C if persistence is required. Large 650/700 MB
CDs exceed the default 128 MiB limit; streamed images and writable-media
overlays remain future work.

The server generates a fixed boot configuration: mount the prepared virtual C,
the empty D slot and optionally a validated image owned by that account. Browser
DOSBox does not enable `config -securemode`: MOUNT, IMGMOUNT and BOOT work on its
in-memory Emscripten filesystem. Paths such as `/` refer to that virtual tree,
not the browser machine's disk or the NAS. The virtual filesystem contains only
this session's bundle, approved media, runtime files and the selected folder's
snapshot. A DOS command cannot invoke a browser picker or grant itself another
directory capability. Private server APIs still enforce session ownership,
origins, revisions and paths; there is no arbitrary host-mount/command endpoint.
The separate server-side DOSBox used for package post-installation retains
secure mode: that process, unlike browser WASM, runs on the server OS.

Uploads/saves require an authenticated session and the exact configured
`THELP_AUTH_ORIGIN`. All DOS API responses are `no-store`. Media reads check
ownership; knowing another account's image ID does not grant access. Keep the
state directory private, back it up together with the accounts database, and
apply deployment-level rate limits to uploads. Never run untrusted DOS software
with trusted server privileges; interactive emulation stays in browser WASM.

## Modules and API

`server/dos/store.py` coordinates software preparation and boot bundles.
`dos/packages.py` validates configured file recipes and extracts bounded
archives; `dos/post_install.py` runs administrator-authored DOS BAT scripts.
`dos/overlay.py` owns private revision snapshots, tombstones and quota accounting;
`dos/media.py` owns floppy/CD images. Both use the path guards in `dos/paths.py`.
The store composes private storage and media components rather than inheriting
unrelated responsibilities. These modules keep the same disk locations, SQLite
transactions and ownership checks. `server/routes/dos.py` owns the
HTTP/session/origin boundary. The shared
`server/downloader/packages.py` module handles cached software downloads and
uses the same transport and atomic cache writer as HELP providers.
DOS recipes use `server/archives/` just like HELP ingestion and MIDI albums:
bounded ZIP members, external image/archive extraction, split-stream assembly
and Microsoft SZDD/KWAJ expansion. The DOS layer alone owns installation paths,
recipe/member selection, C-drive quotas and post-install commands.
`settings.py` and `routes/settings.py` own
persisted admin settings. `app.py` constructs stores and registers routers.

- `GET /api/dos/status`: starts/reports lazy preparation;
- `GET /api/dos/session`: base hashes, revision, account and quotas;
- `GET /api/dos/bundle`: tiny ZIP with merged file metadata and configuration;
- `GET /api/dos/file`: bounded, hash/identity-checked common or private chunks;
- `PUT /api/dos/overlay`: revision-checked file delta save;
- `POST /api/dos/media?kind=cd|floppy`: private raw image upload;
- `GET /api/dos/media/<id>`: authenticated, owner-only image download.
- `GET/PUT /api/admin/settings`: admin-only private disk quota.

Session/bundle accept an optional `media=<id>`; revision/base response headers
detect changes between their separate requests. File requests carry base/hash
and account guards and cannot read another account's overlay. An explicit
`bundle?full=true` is reserved for the disabled-by-default legacy fallback.
The overlay JSON carries `base_id`, integer `revision`, `account`, `files`
(DOS path → Base64 contents), `unchanged` (DOS path → expected SHA-256),
`deleted` (shared-file paths) and `directories` (directory paths). Retained
hashes refer to the private files loaded for this session, not current data
silently substituted from another window. A successful identical retry returns
the current revision without publishing a new generation.
The emulator assets load only
on demand. Media uploads also send `X-DOS-Account` matching the loaded session
to prevent an account switch during a file picker from misrouting the upload.
Fullscreen displays only the DOS canvas; the underlying frame adapts to pending
video-mode changes after exit. See the native-fullscreen section above for input
and restrictions.

Regression tests exercise a real WASM DOSBox: TVEvent keyboard input creates
a C file, MOUNT maps virtual paths, saved files/deletions survive
restart, approved FAT12 floppy/ISO9660 CD files can be copied to C, and
native fullscreen targets only the canvas, fills the viewport and supports
Alt+Enter toggling and returning to the DOS menu with Ctrl+Alt+M. A concurrent
cloud update exercises Cancel/[] versus explicit close-without-saving and
checks that the newer server disk is untouched. Browser tests
also exercise keypad digits/operators/Enter through a real DOS command and
check horizontal, vertical, minimum and desktop-bounded resizing in VGA
640x480. Deterministic input tests cover key-up, repeat and focus release.
Backend tests cover source hashes, private accounts, origins, traversal, revisions and media
ownership. Safari-specific fullscreen/audio behavior is not covered by that
Chrome integration test.
The same browser test explicitly enables the legacy fallback with workers and
Web Audio deliberately blocked. Startup tests separately verify that the
default worker-denied mode reports an error without requesting a full disk,
and that initialization progress/cancellation clean up the shared dialog.
Chunk API tests cover gzip negotiation, limits and private-file isolation.
The real-worker test confirms an unused 3 MiB file is never transferred,
including during saves, and that renamed private files survive further saves.
An optional `THELP_DOS_TEST_GAME=DOOM THELP_DOS_TEST_AUDIO=1` smoke test uses an
isolated copy configured for Sound Blaster. It verifies the automatic BLASTER
environment, nonzero emulator audio samples and a running browser AudioContext,
without modifying the shared disk or any real user's settings.

Upstream references: [command interface](https://js-dos.com/command-interface.html),
[DOSBox secure mode](https://www.dosbox.com/wiki/Usage),
[emulators source](https://github.com/js-dos/emulators).
Bundled runtime licence/provenance is in `assets/dos/emulators/README.md` and
`LICENSE.txt`; software licences remain in the configured source packages.
