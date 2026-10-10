# DOS Prompt

DOS runs in the browser through the locally bundled `emulators` 8.5.2 DOSBox
WASM backend, not as a process or shell on the server. `TVDosWindow` inherits
the shared `TVWindow` frame, movement, resize and title controls. Its specialised
`TVDosView` owns only the DOS canvas, audio and native input bridge into
`TVEvent.handleEvent()`. There is no second js-dos player UI or player CSS.
Both text-mode software and graphical DOS programs are supported. The canvas
follows DOSBox's video-mode size; a BIOS VGA 320x200 test verifies real graphics
and the transition back to text mode. Individual games still depend on DOSBox
compatibility, configured memory/cycles and the browser's performance.

The worker backend is required by the default configuration. If a browser
denies workers, DOS reports an unsupported mode instead of downloading the
entire C drive. Browser audio permission is optional: denied AudioContext
creation/resume cannot prevent DOS from running silently. The explicit
`allow_full_disk_fallback` setting defaults to false; only enabling it allows
the legacy direct backend and its full ZIP download.

Open **≡ → DOS Prompt**. While the window is active, a **DOS Prompt** menu is
added to the main menu bar. It contains Pause/Resume, Restart, Save C to cloud,
Mount CD, Mount Floppy, Eject media, Zoom 2×, Fullscreen and Close. Ctrl+Alt+M opens this
menu from the DOS keyboard. F1 and other DOS keys go to the emulator instead
of opening THelpViewer help. Operating-system/browser-reserved shortcuts may
still be intercepted by the browser. Clicking outside the window or hiding
the page pauses DOS and clears held keyboard/mouse buttons.
With the DOS canvas focused, **Alt+Enter** toggles native fullscreen and
**Alt+Pause** toggles pause/resume (also **Alt+F16** for the classic Mac mapping).
These match the [classic DOSBox bindings](https://www.dosbox.com/wiki/Special_Keys).
Classic DOSBox has no standard restart binding; **Ctrl+Alt+R** is a THelpViewer
extension. Restart confirmation leaves fullscreen so the standard TVision
message box is visible; cancelling preserves the running session. Shortcut
repeats/key releases are consumed, not forwarded as extra DOS keystrokes.

**Zoom 2×** enlarges the window's DOS client area up to twice its current size,
limited uniformly by the available desktop. **Zoom back** restores the prior
window position and dimensions. This uses the shared window resizer/frame,
not browser fullscreen or extra CSS scaling; the DOS image retains its aspect
ratio. The frame's Zoom button uses the same operation. A successful cloud
save is silent, including periodic autosaves, so it does not cover the DOS
image. Save failures still display an error.

DOS uses both sides of the shared TVWindow frame, including its single-line
inactive state when another window covers it. The shared window mover caches
drag limits at mouse-down, coalesces position updates per browser animation
frame and commits the final mouse-up position before saving workspace geometry.

DOS Prompt participates in the existing `#tv=1.…` workspace state, including
window geometry, stacking/active window and Pause state. Restoring the URL
starts a fresh emulator session with the currently signed-in user's saved
overlay; it is not a CPU/RAM save-state. Commands, account identifiers and
private media IDs are not placed in the URL. Fullscreen requires a new user
gesture and is not restored automatically from a link.

Server Statistics lists opens under **Tools → dos-prompt** and duration buckets
under **Tool time**. The shared managed-window lifecycle excludes startup,
explicit Pause, inactive windows and hidden tabs. It does not inspect DOS
commands or identify which DOS game/program is running. Durations are sent on
close/page exit; abrupt crashes or failed exit delivery can lose an interval.

## Native fullscreen

**DOS Prompt → Fullscreen** requests the browser's native Fullscreen API for
the DOS canvas itself. Only DOS is visible: there is no TVision menu/frame,
desktop or browser toolbar. The image keeps its aspect ratio, with black
letterboxing where needed, and the canvas retains keyboard/mouse input.
The original TVWindow position, dimensions and maximized state do not change.

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
`var/backups/`, keeps `data/dos/users/` overlays/media and cached source archives,
then runs the normal initial preparation again. Other browser tabs must restart
DOS after the base changes. Ordinary members cannot rebuild; the action is
rejected while preparation is already running. See
[local rebuild actions](Accounts.md#local-rebuild-actions) for API/progress and
manual backup recovery. The built-in HELP now has a DOS Prompt topic (hc2320),
including these operations, keyboard bindings, streaming and private storage.

`THELP_DOS_CONFIG_PATH` selects the manifest, defaulting to
`thelpviewer/dos-prompt.json`; Docker Compose already passes it through.
On fresh 2.1 servers, an administrator first selects packages in
Server Configuration → HELP / DOS packages; confirmation starts preparation.
Before selection, opening DOS does not download the whole source manifest.
Existing completed C disks are still loaded lazily on the first DOS request.
The DOS window reports
preparation status through a shared `TVLoadingDialog` with a solid-cell gauge,
source name and download/extraction phase. Cancel closes the wait, not the
server installer; Restart reconnects to its progress. FreeDOS EDIT (`EDIT`),
BlockDrop, Sudoku86, Zmiy and Volkov Commander 4.05 (`VC`) retain their licence
notices and source archives. `TYPE C:\SOFTWARE.TXT` lists installed software
and launch commands.

The manifest also configures Prince of Persia, Wolfenstein 3D, DOOM,
Battle Chess, Commander Keen, Color Lines, Lemmings, The Lost Vikings,
Quadrax, Supaplex, Tetris, The Incredible Machine 1/2, Formula One Grand Prix,
Grand Prix 2, Ironman Super Off Road, Lamborghini and Dungeon Master 1/2.
Lost Vikings 2 is deliberately excluded. Packages come from BestOldGames,
except Lemmings: that site's ZIP contained a Windows executable, so the
manifest uses the DOS release from Internet Archive instead. The stable
`bog-lemmings` source ID is retained. DOOM, Wolfenstein and Keen packages are
shareware; The Incredible Machine 1 package is an interactive demo. Permission
to distribute full games does not turn a source's demo into a full release.
The Lost Vikings requires its original `SETUP` before `VIKINGS`; the unconfigured
game reports a copy-protection error. Dungeon Master asks for a display mode;
the current Chrome/WASM smoke test stalls at that selector, even with a held
selection key. It reproduces both with worker/file-on-demand and with the
explicitly enabled direct/full-disk test configuration, so it is not specific
to chunk delivery. The cause and gameplay compatibility remain unresolved.
Norton Commander 4.0
has a pinned disk-image source but is disabled pending redistribution permission.
Subsequent messages distinguish C-drive loading, runtime loading, backend
startup and the command shell. Network/backend waits have 30-second deadlines,
script loading 20 seconds and shell startup 15 seconds, rather than leaving
the initial preparation message displayed indefinitely.
The original licence and source archive are retained alongside the program.

The manifest contains `cycles` (`auto`, `max` or a numeric DOSBox cycle count),
`memory_mb` (4–64), `max_c_bytes` (manifest 256 MiB), `max_media_bytes` (default
128 MiB) and a `sources` list. Each source has:

- `id`: unique lowercase identifier;
- `url`: HTTPS archive URL or HTML download page;
- `format`: `zip`, `img` or `archive` (7-Zip-supported archives);
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
- `files`: optional list of generated text or binary files, relative to
  `target`, in addition to the selected archive files. Each entry has `path`
  and exactly one of `text` (individual CP437 lines with CRLF) or `base64`
  (strict Base64 bytes, without whitespace or a data-URL prefix);
- `license`: a human-readable provenance/licence note, not a permission check.

ZIP extraction rejects traversal, symbolic links, duplicate DOS names and
excessive file count/expanded size. Trusted configured IMG sources reuse the
downloader's existing unar/7-Zip image extraction; Docker includes 7-Zip.
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
starts still leave completed base disks frozen; use administrator Rebuild DOS C to
apply a changed recipe from scratch. User overlays are not rewritten. Paths,
case-insensitive duplicates, file counts and combined byte sizes are checked.
The default Volkov Commander entry demonstrates `files` with `START.BAT`.

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

Trusted startup enables secure mode first, then calls `C:\AUTOEXEC.BAT`.
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

New downloads are cached by hash in `var/downloads/dos/`; upgrade migrates the
legacy `var/dos/downloads/` cache there and archives its original. Verified files are
installed under `var/dos/c/`; `var/dos/installed.json` records installed
source hashes. After successful initialisation its `_complete` flag freezes
automatic installation: later starts only read the existing disk, even if the
manifest's source list changes. They do not redownload, restore deleted files
or overwrite administrator edits. An interrupted initial installation without
this flag resumes from verified package receipts. The earlier receipt-only
prototype is completed once, retaining existing files and adding these games.
Runtime memory/cycle/quota settings still reload on server restart. Later
software additions use Server Configuration → HELP / DOS packages → Install.
The existing maintenance adapter `python -m thelpviewer.tools.install_dos_sources`
also remains available. Installation adds selected packages without overwriting different existing
files and refreshes SOFTWARE.TXT. Removals remain an administrator disk change;
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
files are retained server-side by name; only changed/new contents are uploaded.
The server replaces the private overlay transactionally and validates paths,
file count, private capacity and file/directory collisions. Revision checks reject stale saves
from another tab; a base hash check rejects saves after the common disk changes.
Reload the page to load the new server state after a conflict; this discards
the old tab's unsaved changes instead of overwriting the newer server snapshot.
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

Authenticated sessions save every 60 seconds while active, on **Save C to
cloud**, before normal Close/Restart and when the DOS `EXIT` command returns
from the interactive `COMMAND.COM` to the trusted boot script. The parent
shell remains alive for the filesystem save; only then does the adapter stop
DOSBox using its public `exit()` API. A normal window-close save failure leaves the window
open rather than silently discarding changes. Use manual Save before closing
the browser/tab: unload, crashes or loss of network cannot guarantee upload.
Signing out or switching accounts closes the old DOS window without writing
it under the new identity. Unsynced changes are then discarded. Guests have
a temporary C drive without server persistence or media upload.

This is file persistence, not an emulator save-state: restart resumes saved
configuration/savegames but not the running program, CPU state or RAM.

## CD/floppy mounting and isolation

The menu chooses a local ISO/raw floppy image and uploads it under the current
account. A content-derived opaque ID deduplicates repeat uploads. At most
eight images per account are retained; the first UI does not yet manage/delete
that library. CD images must have an ISO9660 signature and fit the configured
media limit; raw floppies must have a boot signature, sector-aligned size and
be at most 16 MiB. These are preliminary format checks, not malware scanning.

The first version mounts one image at a time: floppy as A or CD as D.
Mount/eject confirms a DOS restart and saves C first. ISO images are read-only;
modifications inside mounted floppy images are not uploaded back. Copy their
configuration/save files onto C if persistence is required. Large 650/700 MB
CDs exceed the default 128 MiB limit; streamed images and writable-media
overlays remain future work.

The server generates a fixed boot configuration: mount the prepared C,
optionally mount only a validated image owned by that account, then execute
`config -securemode` before presenting the interactive prompt. The DOSBox
engine itself blocks MOUNT, IMGMOUNT, BOOT and protected configuration changes;
this is not a JavaScript command-string blacklist. The browser filesystem
contains only the bundle and approved media, not host disks. The server has
no endpoint for mounting an arbitrary host path or executing DOS commands.

Uploads/saves require an authenticated session and the exact configured
`THELP_AUTH_ORIGIN`. All DOS API responses are `no-store`. Media reads check
ownership; knowing another account's image ID does not grant access. Keep the
state directory private, back it up together with the accounts database, and
apply deployment-level rate limits to uploads. Secure mode is not a reason to
run untrusted software with trusted server privileges: emulation stays in WASM.

## Modules and API

`server/dos_prompt.py` owns software preparation, bundles, overlays and media;
`server/routes/dos.py` owns the HTTP/session/origin boundary; `dos_sources.py`
handles configured downloads. `settings.py` and `routes/settings.py` own
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
The emulator assets load only
on demand. Media uploads also send `X-DOS-Account` matching the loaded session
to prevent an account switch during a file picker from misrouting the upload.
Fullscreen displays only the DOS canvas and leaves the TVWindow geometry
unchanged; see the native-fullscreen section above for input and restrictions.

Regression tests exercise a real WASM DOSBox: TVEvent keyboard input creates
a C file, secure-mode commands are rejected, saved files/deletions survive
restart, approved FAT12 floppy/ISO9660 CD files can be copied to C, and
native fullscreen targets only the canvas, fills the viewport and supports
returning to the DOS menu with Ctrl+Alt+M. Backend tests
cover source hashes, private accounts, origins, traversal, revisions and media
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
