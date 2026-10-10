# Borland Turbo Debugger/Profiler Runtime Help RE Notes

This file keeps the full reverse-engineering notes, runtime observations, and
open questions for the TDH/TFH family. The format-only summary lives in
`Borland TDH.md`.

Status: TDH runtime-aligned text layer decoded for the current 1.0 and 2.x
samples; TFH decoded for the current real sample family.

`TDHELP.TDH` from Turbo Debugger and `TFHELP.TFH` from Turbo Profiler are not
Borland THELP/TPH/TCH files. They do not contain the THELP signature
`$*$* &&&&$*$`, and the existing THELP record parser must not handle them.

## Confirmed Sample

Current samples:

| File | Size | CRC32 | SHA256 |
|------|------|-------|--------|
| `TDHELP.TDH` | 112,669 | `A9C668A7` | `0c23e564e60f3ec97b98eb71adab052eae2f8b19d5202faa7c43d93271da5f07` |
| `TDHELP.TDH` | 125,805 | `A6E139F2` | `fabad0cc8f53cc5ad3134c3c41baf384f12fa72581b00a1012bf6553fc25f04d` |
| `TFHELP.TFH` | 67,415 | `EDCB6DAB` | `a00fcaee3c1ee94a8801cdbae9dd75d602ed91d9df4063fd1bc27676dc075630` |

The same file appears in:

| Collection | Path |
|------------|------|
| Borland Turbo Debugger 1.0 | `Borland Turbo Debugger 1.0/TDHELP.TDH` |
| Borland Turbo Assembler 1.0 with Turbo Debugger | `Borland Turbo Assembler 1.0 with Turbo Debugger/TDHELP.TDH` |
| Borland Turbo Profiler | `Borland Turbo Profiler/TFHELP.TFH` |
| Borland Turbo Debugger/Profiler/Assembler 2.x | `TDUTIL.ZIP/TDHELP.TDH` |
| Borland Turbo Debugger/Profiler/Assembler 2.x | `TFHELP.ZIP/TFHELP.TFH` |

For the current 2.x loader hunt, the extracted executables still split into two
different RE targets, but the picture is now less one-sided than it first
looked. `TD286.EXE` is the large one (`502,177` bytes) and parses as an
ordinary MZ with `header_paragraphs = 0x80`, so its loaded image starts at file
offset `0x0800`. `TD386.EXE` is much smaller (`24,536` bytes) with
`header_paragraphs = 0x20` (image base `0x0200`), and its visible entry path is
still dominated by switch/bootstrap/file-handling code rather than by obvious
help-runtime structures. However, a focused analog check against the TD 1.0
help anchors was negative inside `TD286.EXE`: the translated neighborhoods for
the 1.0 lazy-loader and page-seek routines did not show recognizable TDH
loader/page logic, and no obvious resident `TDHELP.TDH` string anchor surfaced
in that quick pass. Direct central-directory reads of the local archive copies
now settle that packaging split. `TD286.ZIP` has exactly two members
(`TD286.EXE`, `TD286INS.EXE`), while `TDUTIL.ZIP` has fourteen members:
`TD386.EXE`, `TDCONVRT.EXE`, `TDH386.SYS`, `TDMAP.EXE`, `TDNMI.COM`,
`TDPACK.EXE`, `TDREMOTE.EXE`, `TDRF.EXE`, `TDSTRIP.EXE`, `TDUMP.EXE`,
`TDINST.EXE`, `TDHELP.TDH`, `TDMEM.EXE`, and `TDDEV.EXE`. So the later TDH
sample is physically packaged with the TD386/utility set, not with the plain
TD286 package. The strongest next static anchors are therefore the TD386 handoff
path and the companion `TDH386.SYS` service/driver image, not a simple resident
TD286 clone of the TD 1.0 loader.

A narrower code-level result now exists inside `TD386.EXE` itself. In the loaded
image around `0x083A..0x08AA` (raw file `0x0A3A..0x0AAA`), TD386 contains a
helper that copies one semicolon-delimited path entry into a buffer, tracks the
last `/`, `\`, or `:` separator, normalizes a trailing backslash when needed,
appends a fixed `7`-byte suffix, NUL-terminates the candidate path, and probes
it via DOS `INT 21h` with `AX = 3D02`, immediately closing the handle again on
success with `AH = 3E`. That is direct proof that the 386-side bootstrap
expects at least one external companion file/service image and searches for it
through a path list rather than treating the later TDH support as purely
resident inside the main EXE. The raw anchor for that claim is now explicit:
near raw `0x0A7D` the helper executes `B0 5C AA`, then `BE A2 09 B9 07 00 F3
A4`, then `32 C0 AA`, and finally the DOS probe pair `B8 02 3D CD 21` /
`B4 3E CD 21`. So the path candidate is built in memory, copied with a fixed
7-byte tail, terminated, opened read/write, and closed immediately on success.

The TD386 tail strings now make that companion identity much less ambiguous.
Near raw file `0x481B` the image contains the signature `TDHDEBUG`, followed by
error/reporting strings such as `TD386 error: couldn't execute '...'`,
`TD386 error: '...' is corrupt or wrong version`, `Enter pathname for modified
program file [$]:`, `TD386 error: 80386 device driver missing or wrong version`,
and `TD386 error: environment too long; use -e#### switch with TDH386.SYS`.
So `TD386.EXE` is not just a generic wrapper around `TDHELP.TDH`; it is a
program-modification / launch-side utility that explicitly depends on the
external `TDH386.SYS` device driver. That is the first direct in-binary proof
linking the TD386 side to `TDH386.SYS`. The remaining unknown is no longer the
general companion identity, but the exact handoff from that TD386/`TDH386.SYS`
pair into the later TDH runtime map / service path.

That service-side identity is now confirmed from the extracted driver payload
itself as well, not only from the TD386 launcher strings. Running the local
ZIP method-6 decoder on `TDUTIL.ZIP:TDH386.SYS` yields a 6,591-byte driver
image whose plain ASCII strings include `TDHDEBUG`, `Turbo Debugger 80386
Device Driver Version 2.0`, `Wrong CPU type - TDH80386 driver not installed.`,
and `Invalid command line - TDH80386 driver not installed.`. Parsing its raw
header shows the standard DOS character-device layout directly:
`next=FFFF:FFFF`, `attr=0x8000`, strategy entry `0x1140`, interrupt entry
`0x114B`, name `TDHDEBUG`. The request dispatcher at `0x114B` loads command
code `req+2`, indexes the handler table at `0x0FC9`, and later handlers touch
`dr7`, `int 0xFF`, and ordinary DOS init/command-line plumbing. No `tdhelp.tdh`
string, no nibble char table, and no visible TDH text-buffer logic appear in
this driver image. So `TDH386.SYS` is a concrete debugger-side service driver,
but it is no longer the strongest candidate for the TDH file loader itself.

The direct later-2.x TDH loader proof now comes from resident `TD.EXE` instead.
In the current extracted TD 2.0 image, a help-init block around loaded image
`0x477C4` pushes data-segment offset `0x5489`, which resolves under resident
data segment `0x191D` exactly to the `tdhelp.tdh` string. That block then calls
an external/protected-mode helper via far selector-style entry `0340:0048`,
stores the returned handle in `0x9D90`, calls companion entry `0340:0034` once
to read the header word into `0xA248`, then loops `0x258` times calling the
same read helper and storing each returned word into the buffer at `0x9D94`.
On success it sets status byte `0x5A5E = 1`; on failure it sets `0x5A5E = FF`.

Those helper roles are now tighter than a generic "protected-mode service"
label. In the current `TD.EXE` image, `0340:0048` appears only once and only in
that `tdhelp.tdh` init path, so its practical role is now constrained to TDH
stream open/init rather than generic arithmetic or UI work. Entry `0340:0034`
appears four times: once for the initial header read at `0x477D9`, once in the
`0x258`-word loader loop at `0x477E9`, once in the text decoder path at
`0x55409`, and once after a reposition helper at `0x558BE`. The `0x55409`
call site is especially informative because the surrounding code treats the
returned word as decoded text/control data, checking for `0x000D`, `0x000A`,
and `0x005E` (`'^'`) while wrapping visible text at width `0x31`. So
`0340:0034` is no longer just "some companion helper": it behaves like the TD
2.0 TDH word reader used by both loader and text/parser paths.

Entry `0340:0061` is likewise better constrained now. It has multiple call
sites, including `0x558B5`, where the caller first computes a 32-bit target
offset, pushes that offset plus a zero mode word, calls `0340:0061`, and only
then calls `0340:0034` on the same handle. That usage matches the already known
TFH-side pattern where `0x430:0061` behaves as a seek/reposition helper and
`0x430:0034` as the next-word reader. The far-target normalization
`0340:0034 -> 0x3434` / `0340:0048 -> 0x3448` lands inside resident arithmetic
code that does not match the observed TDH loader behavior, and some other
normalized targets such as `0x3452`, `0x3457`, `0x4325`, and `0x4352` even land
in the middle of decoded instructions. That rules out the simpler explanation
that these are ordinary internal MZ far entry points whose behavior we just
misread.

That selector-style interpretation is now stronger than before. A brute-force
scan of far calls to segment `0340` in the extracted `TD.EXE` finds `23`
call sites spread across `8` unique offsets: `0x25`, `0x2A`, `0x34`, `0x3E`,
`0x48`, `0x52`, `0x57`, and `0x61`. So `0340` does not behave like a tiny
TDH-private code segment with only one or two help routines in it; it behaves
more like a shared runtime service selector/API block that the TDH path happens
to use for open/read/seek-style work. A relocation-table check makes the same
point from the loader side: in both `TD.EXE` and `TPROF.EXE`, the segment-word
immediates in all observed `lcall ... 0x340:*` / `lcall ... 0x430:*` sites are
absent from the MZ relocation table. So these calls are not ordinary relocated
in-image far calls; they are best modeled as non-relocated absolute far entries
into a runtime-installed service block. The same selector values also appear in
another embedded-constant form: both executables have non-help paths that
explicitly build far pointers such as `0340:0020` / `0340:0043` and `0430:0020`
on the stack before passing them to a different helper layer. So the current
evidence is not that the XMS bootstrap computes `0340` / `0430`, but that the
executables reuse those selector values directly as fixed service-entry
constants.

That neighboring helper layer now looks selector-style as well. In `TD.EXE`,
far calls to segment `0090` appear `282` times across `16` offsets; in
`TPROF.EXE`, far calls to segment `00C8` appear `202` times across `15`
offsets. The specific bridge entries used around the explicit `0340:*` /
`0430:*` pointers are `0090:0135` / `0090:01A0` and `00C8:013F` / `00C8:01AA`.
That pairing is not random: `14` of the currently observed `0090:*` offsets have
direct `00C8:*` mates under a stable `+0x0A` shift (`0x001 -> 0x00B`,
`0x02C -> 0x036`, `0x05D -> 0x067`, `0x078 -> 0x082`, `0x08F -> 0x099`,
`0x0BD -> 0x0C7`, `0x104 -> 0x10E`, `0x135 -> 0x13F`, `0x173 -> 0x17D`,
`0x1A0 -> 0x1AA`, `0x1DD -> 0x1E7`, `0x1F3 -> 0x1FD`, `0x2C6 -> 0x2D0`,
`0x38E -> 0x398`). The currently unmatched tails are small (`TD: 0x26F, 0x40A`;
`TPROF: 0x3C5`).
But their segment-word immediates are also absent from the MZ relocation table,
so the naive linear targets `0x00A35` / `0x00AA0` / `0x00DBF` / `0x00E2A`
should not be overread as trustworthy in-image helper bodies either. The model
therefore widens slightly: these binaries appear to rely on at least two nearby
families of non-relocated selector-style runtime API blocks, not on one lone
`0340:*` / `0430:*` quirk. The exact concrete provider behind those selectors
still remains unidentified.

Raw far-call scans now show that this `+0x0A` pairing is behavioral, not just
numeric. In `TD.EXE`, `0090:0078` appears `39` times and is typically called
with `0` or another small mode word, returning a handle/id that is stored into
globals or per-structure slots before follow-up calls such as `0090:0135` or
`0090:0001`. `TPROF.EXE` shows the same shape for `00C8:0082` across `25`
calls, with the matching follow-ups `00C8:013F` and `00C8:000B`. The paired
entries `0090:01DD` (`56` calls) and `00C8:01E7` (`29` calls) then behave like
the next query/count-like layer over those returned handles: callers compare
the result with `0` or `1`, use it as a loop bound or ordinal limit, and feed
it into the paired fetch/dispatch entries `0090:008F` / `00C8:0099` and
`0090:01F3` / `00C8:01FD`. So the current evidence supports a shared runtime
API family with executable-specific selector values and mostly shifted entry
numbers, even though the provider/runtime name is still unknown.

The next bridge pair now looks narrower too. Stored callsite dumps show
`0090:008F` / `00C8:0099` in the classic "handle + ordinal" shape: callers
first obtain or query a handle through `0078/0082` and `01DD/01E7`, then push
that handle together with a loop index, ordinal, or per-item field and use the
returned value immediately as an item-like payload. In the strongest examples,
the return is either dereferenced right away (`mov ax, es:[bx+4]` after local
materialization) or masked with `0x7FFF` and compared against another id,
which fits an ordinal fetch/getter much better than a pure predicate. By
contrast, `0090:0135` / `00C8:013F` behave like the next two-argument bridge or
dispatch layer over a handle and a second selector/value: some callsites test
the return for zero/non-zero before continuing, while others use the call only
for its side effects and ignore the return. So the current safe classification
is: `008F/0099` are fetch-like handle+ordinal entries, while `0135/013F` are
follow-up handle+arg bridge calls whose exact side effect still needs a tighter
name.

The non-help offsets now make that API shape more specific. In a broader TD 2.0
file-processing path around `0x45DF0`, the program first opens a file through a
different helper, then passes the returned handle by address to `0340:0052`,
uses `0340:0061` to seek to absolute offset `0`, and then calls `0340:0057`
with `(handle, 0x80, buffer)` to read a `0x80`-byte block. In another path,
`0340:0025` is used as a byte reader from that same stream-style handle, while
the TDH path uses `0340:0034` as the matching word reader. So the current best
behavioral model is no longer just "shared protected-mode service block" but
"shared stream/file service API exposed through a non-relocated absolute
selector value that differs by executable". That is already enough to explain why TD 2.0 uses
`0340:*` while the analogous TFH path in `TPROF.EXE` uses `0430:*` for the same
kind of read/seek primitives.

That cross-executable comparison is now backed by direct counts rather than by
name matching alone. A brute-force scan of far calls to selector `0430` in the
extracted `TPROF.EXE` finds `33` call sites across `10` offsets:
`0x25`, `0x2A`, `0x2F`, `0x34`, `0x39`, `0x3E`, `0x48`, `0x52`, `0x5C`, and
`0x61`. The shared core with TD 2.0 is the important part: both executables use
the same small offset family for byte read, word read, open/init, stream/object
acquire, seek/reposition, and neighboring non-help file-processing work. That
is much stronger evidence for a per-process selector assignment over one common
runtime service API than for two unrelated local helper implementations that
happen to share offset numbers.

What still does *not* follow from the current evidence is the vendor or runtime
name behind that API block. A direct string scan of the extracted `TD.EXE` for
common extender/provider anchors (`DPMI`, `VCPI`, `Phar Lap`, `Rational`,
`RTM`, `CauseWay`, `DOS/16`, `DOS4`, `extender`) does not surface a strong
positive match. The extracted ZIP member lists (`TD.ZIP`, `TD286.ZIP`,
`TDUTIL.ZIP`, `TPROF.ZIP`) also do not expose an obvious companion runtime file
with one of those names. The nearest explicit local naming stays on Borland's
own side instead: the 386-side helper payload is a `TDHDEBUG` DOS device
driver, and the surrounding binaries/utilities are all Borland-branded rather
than third-party extender payloads. So the current best local conclusion is no
longer "unknown external extender" but "Borland-internal selector-style
runtime/service layer with no recovered public product name". The remaining
question is therefore narrower: not what the `0340:*` entries do, and probably
not which common third-party extender they belong to, but which exact Borland
component installs that selector family in TD and TPROF.

One more environmental clue is now visible, and it argues *against* the more
common late-DOS protected-mode suspects. In both extracted executables, direct
pattern scans find no `int 31h`, no `AX=1687h / int 2Fh` DPMI handshake, and
no `AX=DE0Ch / int 67h` VCPI handshake. Instead, both images contain the same
older memory-manager support patterns:

- `int 2Fh` with `AX=4300h` and `AX=4310h`, which is the XMS presence/query +
  entry-point handshake
- `int 67h` with `AH=47h`, `AH=48h`, and `AX=4400h`, used in shared EMS page-
  frame transfer helpers

The TD 2.0 and TPROF code slices around those calls are structurally parallel,
including the same `0x4000`-byte transfer chunking and the same XMS entry-point
indirect far call after `AX=4310h`. More specifically, the XMS side is no
longer just a generic handshake guess: both executables call XMS function `0`
to check the reported version (`AH >= 2`), then `AH=8` (query free extended
memory), `AH=9` (allocate an extended-memory block), `AH=0Ch` (lock that
block), and finally `AH=0Dh` / `AH=0Ah` (unlock + free). That pattern looks
like XMS-backed memory-pool probing/allocation support, not selector material
for `0340` / `0430` themselves. So the current evidence fits an older Borland
runtime that relies on XMS/EMS services and separately exposes the selector-
based stream/file API used by `0340:*` / `0430:*`; it does *not* fit a plain
DPMI- or VCPI-signature story.

The matching seek logic is now visible too. Helper `0x557D3` initializes a
32-bit accumulator, sums signed words from `0x9D94[0 .. current_context-1]`
where current context lives in `0x5A5C`, then adds `2 * 0xA248 + 2` before
returning the final stream position. In code terms, that is the same runtime
addressing formula already recovered from the older TD family:

$$
\\text{start} = 2 \\cdot \\text{header} + 2 + \\sum_{i=0}^{context-1} \\operatorname{sign16}(\\Delta_i)
$$

So the widened later-sample path is no longer just a file-side inference. There
is now direct resident 2.0 evidence for the TDH open/read/seek model itself.
The `600` vs. `596` nuance is now narrower too. In the real later file, header
word `0` is `0x0254 = 596`. Dumping the words immediately after that header
shows that indices `1..596` are the live runtime map, index `597` is the
separator word `0x0001`, and indices `598..600` are already payload prefix
words (`0xAECC`, `0xCCCC`, `0xCCCC`). So the resident `0x258 = 600` bootstrap
loop is not evidence for a 600-context on-disk format; it is a fixed preload
window that covers the whole live `596`-word map plus the separator and the
first three payload words.

## Observed Header

The file starts with big-endian words:

```text
0206 0001 0124 01B7 0072 0096 008B 00AF
006C 00A7 0086 00C3 00BB 00B4 00BE 0060
```

Confirmed structural observations in the Turbo Debugger 1.0 sample:

| Offset | Value | Meaning |
|--------|-------|---------|
| `0x0000` | `0x0206` | Header word; in this sample it is also the byte size of each visible pre-separator half. |
| `0x0002` | 259 big-endian words | First visible half of the TDH runtime-map prefix, 518 bytes. |
| `0x0208` | 259 big-endian words | Second visible half of the TDH runtime-map prefix, 518 bytes. |
| `0x040E` | `00 01` | Observed TDH-family flag/separator word before payload. |
| `0x0410` | starts `A0 CC CC ...` | Encoded payload. |

Runtime evidence no longer supports treating those visible halves as standalone
decoder tables. In TDH 1.0, the live signed-delta map still uses a legacy fixed
`530`-word load and therefore extends `12` words past the separator into the
payload prefix. In the later 2.x sample, the live signed-delta map instead uses
the whole `596`-word pre-separator prefix and cleanly unlocks readable contexts
`530..595` (for example Object Inspector / Hierarchy help topics). The
two-byte field before payload still does not look like an entry-state index: in
the currently observed TDH-family samples it is always `0x0001`, while TFH
uses `0x0000`.

The payload lead also has a stable short preamble in the current real samples:
the first payload byte is followed by 9 consecutive `0xCC` bytes, and both TDH
and TFH then continue with the same visible prefix bytes starting at
`FC 48 5F F4 4C 0F ...`.

Comparing the two real TDH samples adds one more useful invariant: after
skipping the first payload byte (`0xA0` in TD 1.0, `0xAE` in TD/Profiler/
Assembler 2.x), the payloads share a 54-byte common prefix before diverging at
offset `0x0037`. Several early differences are a clean `+0x0E`
(`0x83 -> 0x91`, `0xD1 -> 0xDF`, `0xCF -> 0xDD`), then the streams diverge more
heavily after about `0x00C7`.

The later 125,805-byte sample has the same structure but starts with `0x0254`,
which gives two 596-byte tables with 298 big-endian words each. Its payload
starts at `0x04AC` with `AE CC CC ...`. This confirms that the first word is a
table byte size, not a fixed TDH version signature. One caution matters here:
the later resident `TD.EXE` build does contain call sites that push `0x0254`,
but the currently inspected one is only a local far-pointer thunk that writes
entries into a low-memory/vector table, not the help loader itself. So the
`596`-slot TDH 2.x interpretation is currently grounded in file-side decoding
and readable extra contexts, not yet in a resident-code loader proof.

`TFHELP.TFH` shares some runtime behavior with TDH, but the file-side layout is
now much less speculative and should no longer be described as "two decode
tables".

| Offset | Value | Meaning |
|--------|-------|---------|
| `0x0000` | `0x016B` | Big-endian context count (`363`). |
| `0x0002` | 363 big-endian words | Per-context block sizes. |
| `0x02D8` | `00 00` | Separator word and runtime block base used by the loader. |
| `0x02DA` | starts `96 CC CC ...` | First bytes after the separator; not yet the visible text start of context 1. |

Using runtime block base `0x02D8` together with the `363` big-endian size words
at `0x0002` matches the seek helper at `0x3C9FD` exactly and produces the same
topic boundaries seen by the program. The first few sizes are:

```text
0001 00A4 0170 0003 0091 0089 00A3 0003
```

and the cumulative byte sum of all `363` sizes lands almost exactly on the end
of the file. The current real sample leaves only a small trailing tail of `157`
bytes after the last sized block, which strongly supports the model:

1. big-endian context count
2. big-endian per-context byte sizes
3. one zero separator word at `0x02D8`
4. cumulative variable-size runtime blocks starting at `0x02D8`

This resolves the earlier `0x02D8` vs `0x02DA` contradiction. `0x02D8` is the
true block base, while `0x02DA` is only the first byte after the separator. In
the current sample the first size is `0x0001`, so context `0` is a one-byte
sentinel block and context `1` starts at `0x02D9`. Its separately consumed
control word is therefore `0x0096` (`00 96`), and the first visible text word
for `HELP INDEX` begins one byte later at `0x02DB` as `0xCCCC`.

The text layer inside those TFH blocks is also now independently confirmed
offline from file bytes alone. Once the block-leading control word is skipped,
decoding the visible stream from block byte `+2`, low nibble first, yields
readable English if the nibble alphabet is interpreted as:

| Nibble | Meaning |
|--------|---------|
| `0x0` | skip |
| `0x1..0xC` | `e t r o i n a s l c h <space>` |
| `0xD` | `^` |
| `0xE` | not needed in the current structured TFH parse; earlier apparent `E` output came from mis-decoding raw target words as text |
| `0xF` | literal byte from next two raw nibbles as `low + high * 16` |

Under that model, TFH already decodes real topic text. For example:

```text
context 1: HELP INDEX
context 2: Welcome to Turbo Profiler's help facility. Use the following keys to move around:
context 51: The File command has a number of options ...
```

The next layer is now concrete too. In the outer nibble-decoded stream, control
character `'^'` is a hotspot start marker. After that marker, the runtime aligns
to the next byte, reads one big-endian target word, then decodes the visible
label until the next `'^'`. Under that model, topic text like:

```text
^crOpen^           ^hmGet Info^
```

turns into clean structured records such as:

```text
Open -> 58
Get Info -> 235
```

and inline text references like `^iltext pane^` / `^toModule Window^` likewise
become normal hotspot spans (`text pane -> 149`, `Module Window -> 66`). So TFH
is no longer blocked on the earlier TDH-style two-table hypothesis. At this
point the known TFH sample family is structurally decoded above this raw
text-plus-hotspot layer.

The runtime line parser above that symbol stream is now mostly concrete too.
Helper `0x3C5A0` does not return free-form paragraphs; it emits one screen line
at a time with a fixed width of `0x31` (`49`) columns. Its control-symbol table
is segment-relative and resolves to the five special first-symbol cases:

1. `0xFFFF` = end of topic / stream exhaustion
2. `0x0000` = explicit end-of-topic marker
3. `0x000A` = line break
4. `0x000D` = line break
5. `0x005E` = hotspot block

Ordinary text is wrapped to the previous space before column `49`, with the tail
carried to the next line through a one-line pushback buffer. CR/LF sequences end
the current line and push back the first non-CR/LF symbol for the next call.
When a hotspot begins too close to the right edge, the runtime moves the whole
hotspot label to the next line rather than splitting part of it on the current
line. On the current sample there are no hotspot labels longer than the runtime
line width, but ordinary prose wrapping is pervasive. The reader now
matches that runtime line layout while still trimming the synthetic leading blank
line produced by the common `0xDFF0` text prefix.

One more file-side clue is now stable across the known sample: the first raw
big-endian word at each runtime-aligned TFH block start is a separately consumed
control word, not visible text. In the current real sample, `308` in-block
control words are `0x0000`; the only short block is the one-byte sentinel
context `0`; and all `54` non-zero in-block control words already lie inside
the valid context range `1..362`. The most common non-zero values are
`0x009D` (`22` topics), `0x014E` (`5` topics), and `0x0013` (`3` topics).

The recurring values `0xDFF0`, `0x4FB5`, `0x5F85`, and `0x7F15` are therefore
not block headers at all. They are the first two bytes of the visible text
stream at block byte `+2` when present: `0x7F15 -> Welc`, `0x4FB5 -> This`,
`0x5F85 -> Use `, and `0xDFF0 -> CR/LF` followed by `Th...`. In the current
sample, `0xDFF0` appears on `329` visible text streams and yields one synthetic
leading blank line before the first visible text. The reader now handles that as
plain text-layer normalization: decode from byte `+2`, low nibble first, then
trim exactly one leading blank line for the `0xDFF0` class. The earlier
`cThe...` / `cThis...` artifact disappeared once parsing stopped at the true
control-word boundary.

This also removes the earlier file-vs-runtime mismatch around `0x9832`. Topic
loader `0x3CA9B` seeks to the runtime block start, reads the block-leading word
into memory location `0x9832`, and only then enters the nibble/text parser in
`0x3C5A0`. The file control word and runtime word are therefore the same field;
the earlier contradiction only came from treating the visible text prefix as the
block start.

Combined with the earlier zero/nonzero check in `0x3CA71` and the recovered key
dispatch table, the runtime model is now sharper than before: `0x9832` is the
actual per-topic next-page field. It is usually zero, and when non-zero the
value is already a direct big-endian target context consumed by the `PgDn` /
next-page path. The repeated values such as `0x009D`, `0x014E`, or `0x0013`
therefore do not imply a second decoding layer; they are simply reused follow-up
targets shared by multiple related topics.

That interpretation is now strong enough for the reader to expose the
in-range non-zero control word as `next_context` in the normalized topic model.
Representative chains in the current sample include `20/21/22 -> 19 -> 334`
and `339 -> 340`, which fit the runtime `PgDn` / next-screen semantics much
better than any flag-only explanation.

That UI/event role is now much narrower than before. The help event handler at
`0x3CD6C` dispatches through a 13-entry local key table. Recovered key codes map
`0x001B -> exit`, `0x0149 -> previous-page branch`, `0x0151 -> branch 0x3CE18`,
and `0x1C0D -> Enter/follow selected hotspot`, with the `0x0147..0x0151` range
matching standard extended navigation keys (`Home`, `Up`, `PgUp`, `Left`,
`Right`, `End`, `Down`, `PgDn`). This means the `0x3CE18` path that consumes
`0x9832` is strongly tied to `PgDn`/next-page navigation, not to ordinary topic
rendering.

The symmetry with previous-page handling is also now clear. `0x3CA71` builds a
small availability bitmask: bit `0` is set when the runtime history stack depth
`0x9373` is non-zero, and bit `1` is set when `0x9832 != 0`. In the dispatcher,
the previous-page branch at `0x3CE07` calls `0x3C3F2` to pop the history stack
and then reloads the topic, while the next-page branch at `0x3CE18` simply
pushes `[0x9832]` and falls into `0x3CC08 -> 0x3C390`. That helper does not
transform the value: it compares the argument directly against current context
`0x544C`, pushes the old context onto the history stack, and writes the new one
straight back to `0x544C`.

One file-vs-runtime reconciliation is now concrete. The stable parse for the
current real sample is:

1. seek to `0x02D8 + sum(sizes[:ctx])`
2. read one big-endian control word into the runtime state
3. decode visible text from block byte `+2`, low nibble first
4. treat `0xDFF0` at that text-layer start as a synthetic leading CR/LF prefix

That model preserves the current `363` topics, `321` hotspots, and the visible
topic text now recovered by the reader, while finally matching the runtime
seek/load sequence seen in the executable.

`file(1)` reports this as `ALAN game data version 2.60`, but that is a false
positive caused by the first big-endian word `0x0206`. The system magic rule for
ALAN only checks this word and does not validate a Borland TDH structure.

Brute-force checks against nearby decoder families have not matched yet. The
currently tested simple left/right prefix-tree variants and small standard LZW
bitstream variants both produce only repetitive synthetic output, not readable
help text.

One table-walk family is now more interesting than the others. If the decoder
starts from a fixed state `2`, consumes payload bits LSB-first, uses bit `0`
for the first table and bit `1` for the second table, and resets back to state
`2` after each leaf, then the derived branch-vs-leaf event stream is no longer
random across samples. Under that tentative model, TDH 2.x and TFH share the
same first `236` event decisions, while TDH 1.0 shares the same first `84`.
The candidate root also has the same local shape in all three files: state `2`
maps `0 -> leaf`, `1 -> internal state`, and that next state maps `1 -> leaf`.
Looking at emitted codeword paths instead of numeric leaf IDs refines that
clue. If decoding starts at payload byte `1`, the early emitted paths are
identical across all three files (`0`, `0`, `11`, repeating at the start), but
that alignment is dominated by the shared `0xCC` preamble bytes. Starting from
payload byte `0` collapses the common path prefix to only `1..2` symbols, which
strongly suggests that the first payload byte is a separate seed/flag rather
than ordinary codeword data. Starting after the `0xCC` run (for example at
payload byte `10`) also weakens the earlier cross-family result: TDH 1.0 then
matches TDH 2.x / TFH for only about `8` codewords, and brute-force checks over
fixed roots `0..255` do not recover a stronger TDH 1.0 alignment. The emitted
leaf IDs still differ per file, so either leaf numbering is local to each table
set or an additional symbol-expansion layer is still missing. The current
evidence therefore supports state `2` more as a tentative TDH 2.x / TFH anchor
than as a confirmed universal TDH root.

Allowing file-specific entry states changes that picture again. Under one richer
non-degenerate model found so far (MSB-first bit order, bit `0 -> first table`,
bit `1 -> second table`), TDH 1.0 root states `217` or `105`, TDH 2.x root
state `147`, and TFH root states `142` or `124` all produce the same first
`106` emitted codeword paths when decoding begins at payload byte `10`. That is
stronger than the fixed-root result and suggests that TDH 1.0 may still belong
to the same broad table-walk family, but with a different entry state selected
somewhere outside the simple shared `root=2` preamble model. These candidate
entry states are not arbitrary: their unlabeled subtree shape matches exactly
across all three files (`0(0(0L1L)1L)1L`, i.e. `0 -> internal`, `1 -> leaf`,
`00 -> internal`, `01 -> leaf`, `000/001 -> leaf`), which also explains why
multiple equivalent root states appear in TDH 1.0 and TFH. In the current real
samples, that exact subtree signature occurs at exactly two states in TDH 1.0
(`105`, `217`), one state in TDH 2.x (`147`), and two states in TFH (`124`,
`142`).

That `byte 10` alignment is now better understood as a later resynchronization
point inside a longer shared stream, not as the true post-preamble start.
Before the first raw family divergence at payload byte `30`, the three files
are byte-identical from payload bytes `1..29`; only payload byte `0` differs
(`A0` in TDH 1.0, `AE` in TDH 2.x, `96` in TFH). With the same candidate entry
states, decoding the real symbol stream shows a short file-specific prologue
contained in payload byte `0` plus one crossing codeword that ends at payload
byte `1`, bit `7`. After that, all three samples converge on the same emitted
path stream starting at payload byte `1`, bit `6`, and stay identical there for
`141` real symbols up to payload byte `30`, bit `6`. Measured from that real
shared start, TDH 1.0 and TDH 2.x continue together for `258` codeword paths up
to payload byte `55`, bit `7`; the earlier `106` / `223` counts are the same
divergence points remeasured from the later byte-`10` resynchronization anchor.

The file-specific prologues are short but not identical. For one representative
root choice, TDH 1.0 emits `1, 01, 000, 001` before that common start, TDH 2.x
emits `1, 01, 01, 1, 1, 01`, and TFH emits `1, 001, 01, 1, 01`; in each case
the last listed codeword is the one that crosses from payload byte `0` into
payload byte `1`. The repeated `0xCC` run in payload bytes `1..9` then decodes
as a regular shared rhythm rather than opaque out-of-band metadata: before
payload byte `10`, it emits `36` symbols total (`19` times path `1`, `17`
times path `001`), and one of those symbols crosses from payload byte `9` into
payload byte `10`. So payload byte `10` is a useful comparison anchor, but not
an actual symbol boundary.

The shared `106`-symbol prefix stays entirely inside that four-leaf local
subtree. Only four codeword paths occur there, with the same counts in all
three files: `1` (`70` times), `01` (`16`), `000` (`13`), and `001` (`7`).
Each path maps to exactly one leaf ID per file, and those IDs form a clean
bijective renumbering across samples rather than a noisy many-to-many relation.
For one representative root choice, the mapping is:

| Path | TDH 1.0 | TDH 2.x | TFH |
|------|---------|---------|-----|
| `1` | `129` | `7` | `74` |
| `01` | `33` | `27` | `275` |
| `000` | `75` | `6` | `102` |
| `001` | `6` | `49` | `316` |

That local four-leaf picture is not just an early-prefix coincidence. For the
representative good roots `217` / `147` / `142`, decoding the full observed
payload never leaves the same tiny subtree: from the real shared start at
payload byte `1`, bit `6`, every emitted symbol in all three samples is still
one of `1`, `01`, `000`, or `001`, and the full payload ends cleanly on a
symbol boundary with the decoder back at the same entry root. In other words,
the active decoder visits only three internal states per file for the entire
stream (`217 -> 111 -> 108` in TDH 1.0, `147 -> 244 -> 130` in TDH 2.x,
`142 -> 77 -> 88` in TFH). The alternate equivalent roots (`105` in TDH 1.0,
`124` in TFH) show the same three-state shape with different local leaf labels.
In the current real samples, the large decode tables therefore behave less like
fully exercised runtime trees and more like sparse family-specific encodings of
one tiny effective four-symbol prefix code.

This stronger whole-payload criterion also isolates exactly the same entry-root
family as the earlier prefix-only search. If a candidate root is required to
decode the entire payload with no leftover tail bits, to end back at the same
root, to visit exactly three internal states, and to emit exactly the path set
`1` / `01` / `000` / `001`, then the only matching states in the current real
samples are TDH 1.0 `105` and `217`, TDH 2.x `147`, and TFH `124` and `142`.
So the `2 / 1 / 2` multiplicity is not just a local prefix artifact; it
survives an end-to-end check over the full compressed payload.

One simple second-stage hypothesis has also become weaker. Treating those four
path classes as direct `2`-bit values and packing them into bytes under all
`24` path-to-value permutations, both MSB-first and LSB-first packing orders,
and several basic byte transforms (bit-reverse, nibble-swap, `xor 0xFF`) does
not reveal any obvious help-like ASCII words in the TDH 1.0 stream. That does
not rule out a quaternary intermediate representation, but it argues against a
trivial plain-byte mapping immediately after this first four-symbol stage. The
full emitted-symbol counts also do not line up to a consistent byte boundary
under that model across the current samples: TDH 1.0 emits `548111` symbols,
TDH 2.x emits `610792`, and TFH emits `324671`, giving `mod 4` remainders of
`3 / 0 / 3` rather than one stable family-wide alignment.

Widening that same family of cheap second-stage checks has not improved the
picture. Allowing small front/back symbol skips before direct `2`-bit packing
still does not reveal useful plaintext. A simple bitplane interpretation of the
same four-symbol stream (splitting each symbol into two derived bitstreams and
packing those into bytes) likewise produces only short pseudo-printable noise,
not recognizable help text. Grouping the stream into `3`-symbol chunks as a
direct `6`-bit text alphabet also fails: the only detected English-looking hit
in the tested TDH 1.0 output is a trivial accidental `file` substring, while
the surrounding text remains clearly synthetic (`iiii...`, `erer...`, etc.).

The raw symbol stream itself also does not show a strong fixed-size periodicity
that would rescue those simple chunking models. For candidate group sizes
`2..12`, the per-position modulo-`N` symbol distributions stay extremely close
to the global distribution; no standout period appears for the obvious byte-like
or text-like chunk sizes such as `3` or `4`. That weakens the idea that the
second stage is just a hidden fixed-width regrouping of the four emitted symbol
classes.

One tempting end-of-stream clue also turned out to be weaker than it first
looked. TDH 2.x and TFH share a `22`-symbol suffix at the end of the decoded
path stream, but that same `22`-symbol motif recurs many times inside all three
files (for example about `206` times in TDH 1.0, `243` in TDH 2.x, `144` in
TFH). So it is not a unique EOF marker; at best it is one common token pattern
that happens to appear at the end of the later two files.

The duplicate candidate roots inside TDH 1.0 and TFH are therefore only
unlabeled-structure equivalents, not exact cloned subtrees with the same leaf
labels. For example, TDH 1.0 state `105` has the same four-path shape as state
`217`, but a different path-to-leaf assignment (`000 -> 37`, `001 -> 15`,
`01 -> 78`, `1 -> 105`). The exact rule that selects one entry state rather
than another is still unresolved.

One nearby alternative has now been falsified: the matching entry states do not
look like an artifact of starting a few bits too late inside a larger shared
outer subtree. The nearest zero-indegree ancestors of the good states are short
prefixes away (`TDH 1.0: 64 -> 00 -> 105`, `46 -> 11 -> 217`; `TDH 2.x:
18 -> 001 -> 147`; `TFH: 37 -> 1 -> 124`, while `142` already has zero
indegree), but decoding from those ancestors collapses the shared three-way
prefix immediately. The strongest match still begins only when decoding starts
directly from the interior four-leaf states themselves.

This table-walk model also lines up with the verified raw payload boundaries.
Measured from the real shared start at payload byte `1`, bit `6`, the three-way
TDH 1.0 / TDH 2.x / TFH stream stays identical for `141` symbols and then
diverges inside payload byte `30`; TDH and TFH still share the last common
symbol ending at payload byte `30`, bit `6`, and the next symbol differs at the
very next bits (`TDH: path `000`, TFH: path `1``). This matches the already
observed raw payload split where TFH first differs from both TDH samples at
payload byte `30` (`TDH: ... 0D AF C0 CC FC`, `TFH: ... 0D AF F0 5E 00`).
Likewise, under the same model TDH 1.0 and TDH 2.x continue together for `258`
symbols from that same real start and then diverge at payload byte `55`, where
their raw payloads first split (`0x83` vs. `0x91`). The earlier `106` / `223`
counts are the same boundaries remeasured from the later byte-`10`
resynchronization anchor. That byte-accurate boundary match strongly suggests
that the current path model is following the real compressed stream rather than
an accidental table correlation.

One newer clue from the real TDH samples is that the two big-endian word tables
do not look like simple permutations. For TD 1.0 (`259` entries), most values
still fall back into the entry range itself (`188` left, `157` right), but most
out-of-range values stay close to `entry_count + 0..255`; only the right table
has two larger outliers (`delta 293`, `delta 977`). The 2.x sample shows the
same broad split (`251/224` in-range, `47/74` out-of-range, one right-table
outlier with `delta 920`). That shape fits a table-driven state/token decoder
better than a naive left/right Huffman tree, but the exact state-reset and
token-expansion rules are still unresolved.

## Relation To Turbo Debugger / Profiler

`TD.EXE` contains:

```text
tdhelp.tdh
No help for this context
Help file %s not found
Index
Previous page
First page
```

This confirms that TDH is the external runtime help payload used by Turbo
Debugger. The decompressor and context resolver are likely in `TD.EXE` and/or
`TD.OVL`.

`TPROF.EXE` contains the same UI strings plus:

```text
tfhelp.tfh
No help for this context
Help file %s not found
Index
Previous page
First page
```

This confirms that TFH is the matching external runtime help payload used by
Turbo Profiler and strongly suggests a shared or closely related help decoder.

TPROF also now exposes the first concrete per-context runtime structure on the
TFH side. In the resident image, near offset `0x1870` resolves to the string
`tfhelp.tfh`. A routine at image `0x3D144` uses that offset to initialize a TFH
stream handle (`0x937E`), reads one leading word into `0x9836`, then reads
`0x258` more words into the table at `0x9382`. Another routine at `0x3C9FD`
uses the current runtime help index in `0x544C` to sum `0x9382[0..index-1]` and
then adds `2 * 0x9836 + 2` before seeking the same stream. That is not a vague
correlation: on the real TFH sample, `0x9836` matches the file header word
(`0x016B`), so the runtime is explicitly using the file's leading table-size
word as part of the address calculation into later TFH data.

The immediate consequence is important: TFH is not treated only as one opaque
bitstream. Turbo Profiler first materializes a fixed `600`-entry workspace and
then addresses per-context blocks cumulatively from it. The current context
selector is `0x544C`, and the runtime rejects contexts whose corresponding
`0x9382[index]` entry is zero before trying to render a topic. After the seek,
the next fetched word is stored in `0x9832` and drives a further branch between
the "no help" path and follow-up topic handling. With the file-side decode now
confirmed, that runtime `600`-entry table should no longer be read as a literal
on-disk header table. It is more likely a fixed in-memory context map or
expanded workspace derived from the real `363`-entry file size list. So even
though the low-level decode primitive behind the stream handle is still not
fully mapped, the higher-level TFH layout now looks much more like:

1. file header word
2. runtime-decoded fixed context table (`600` words)
3. variable-size per-context blocks addressed by cumulative sums over that table

That is the strongest current evidence that TDH/TFH contain a real context map
above the first table-walk stage rather than only raw free-form text.

The next runtime layer above that table is also no longer opaque. In TPROF,
far entry `0x430:0025` behaves as a byte reader from the TFH stream,
`0x430:0034` behaves as a word reader that is only referenced by the help
decoder path, and `0x430:0061` is used as a general seek/reposition helper.
On top of that, helper `0x3C50C` splits each fetched byte into two nibbles by
returning the low nibble first and the high nibble second. Helper `0x3C54B`
then turns those nibbles into visible characters:

1. nibble `0x0` is skipped recursively
2. nibbles `0x1..0xE` index a small resident character table
3. nibble `0xF` introduces one literal byte assembled from the next two
  nibbles as `low + high * 16`

That is a direct runtime confirmation of the low-nibble-first packing rule. It
also shows that the second stage is not simple fixed-width ASCII packing: it is
a nibble-coded text alphabet with an explicit literal escape.

The per-context block parser above that decoder is visible at `0x3C645`. It
reads one word from the TFH stream, then builds a line by consuming decoded
characters until terminator byte `0x5E` (`'^'`) or a hard visible-width limit
of `0x31` characters is reached. The parser trims trailing spaces, handles
special control cases through a jump table, and emits auxiliary metadata via
`0x3C471` when a line overruns the simple inline case. In other words, the
runtime TFH topics are already organized as structured records with control
words plus `'^'`-terminated text fragments, not as one flat plain-text stream.

One concrete runtime anchor now exists on the TD side: `TD.EXE` contains a real
overlay/export dispatcher layer rather than only flat resident code. At image
offset `0x1EA60`, `tools/dos_mz_disasm.py` decodes a valid 22-entry
overlay/resource table. Entries `1..21` target `TD.OVL`; entry `22` targets
`TD.EXE` itself and carries flag `0x4000`. Immediately after the `TD.OVL`
string, image range `0x1EBD6..0x1F66E` is a contiguous block of 226 export
stubs. Every stub follows the same shape: `call far 1F67:02BC`, embed an
overlay index `1..21`, then `jmp far` to the patched target entry point.

That overlay discovery explains an earlier negative result: the help UI strings
(`tdhelp.tdh`, `No help for this context`, `Index`, `Previous page`, `First
page`) live in EXE data/resource blobs, but they do not have useful direct
immediate xrefs because substantial runtime functionality is reached indirectly
through the overlay dispatcher and resource tables. The remaining runtime hunt
should therefore focus on the overlay-dispatched code paths and their resource
loaders, not on naive literal string references alone.

The dispatcher itself is now partially decoded. Stub `call far 1F67:02BC`
returns to an inline word inside the stub; `02BC` reads that word as the 1-based
overlay index, increments the saved return IP by two so execution resumes after
the inline index, and then calls resolver `1F67:0262 -> 1F67:0267`. The
resolver treats the table at `1EA6:0000` as 16-byte entries, uses bit `15` of
`entry+6` as a loaded/visited flag, follows low `13`-bit chain links stored in
that same word, opens the file name pointer from `entry+0x0E`, seeks using the
32-bit file-base field at `entry+0x10`, loads the body into the segment window
from `entry+0x0A..0x0C`, and then applies 4-byte relocation records from the
overlay header. By contrast, `TPROF.EXE` currently shows no comparable long run
of TD-style 12-byte export stubs and no `.OVL` file string, so Turbo Profiler
may be the simpler resident binary to attack next when hunting the real TDH/TFH
decoder.

One more runtime ambiguity is now gone: many frequently seen `1EA6:*` call
targets are not real helper bodies but export stubs back into `TD.OVL`. Parsing
the `1EBD6..1F66E` stub block as `226` contiguous 12-byte records shows that
addresses such as `1EA6:03F2`, `1EA6:040A`, `1EA6:0416`, `1EA6:042E`, `1EA6:06DA`,
and `1EA6:07BE` are only overlay trampolines. For example, the `1EA6:040A`
target reached from several overlay entries is the stub for overlay entry `6`,
not an EXE-local helper. Resolving those stubs turns the current overlay graph
into a much cleaner shape: entries `2`, `3`, `4`, `5`, `8`, `12`, `13`, and `20`
all dispatch repeatedly into overlay entry `6`, while entry `8` also reaches a
small layer in entry `5`.

That changes the current best runtime interpretation. Overlay entry `8` no
longer looks like the TDH decoder itself; it behaves more like a thin controller
that toggles mode/state bits, then delegates almost all substantial work to
entry `6` and a few startup/reset exports in entry `5`. The entry-5 export at
loaded linear `0x21157` is now a concrete anchor: it seeds globals `1F68 = -1`,
`6A7F = 6A84`, clears several `734x` state bytes, and then hands off through
the stub `1EA6:0266`, which resolves to overlay entry `6` target `270B:0109`
(linear `0x271B9`). Inside entry `6`, the low exports at `21E0:0000..0218`
mostly look like generic search/select wrappers around the shared service at
`1725:0019`, so entry `6` itself is probably still a common engine layer rather
than the final TDH bitstream loop.

The concrete TD-side decoder path finally appears one hop away from that shared
engine. Overlay entry `10` contains a line parser whose shape is directly
homologous to the already-decoded TFH runtime path in `TPROF.EXE`.

At `272B0`, entry `10` updates global `0x5820` as the current TD help context
index and pushes the previous value plus one byte of parser state onto a small
history stack at `0x7613`; helper `27311` pops that stack back into `0x5820`.
The actual per-context seek calculation is at `2784F`: it sums the word table
`0x765A[0..0x5820-1]`, then adds `2 * 0x7658 + 2`, returning a 32-bit offset.
That is the same cumulative-addressing pattern already seen on the TFH side.

The table behind that seek comes from overlay entry `1`, target `20FA5`, which
is also the lazy-loader reached through stub `1EA6:097A`. That loader opens the
help stream through `1A38:00B1`, stores the handle in `0x7654`, reads one word
into `0x7658`, then reads `0x212` more words into `0x765A`, and marks status in
`0x5822`. Entry `10` checks `0x5822` before rendering and re-enters the loader
if the table is still uninitialized.

Below that context layer, entry `10` contains direct TD equivalents of the TFH
nibble/text helpers:

1. `273CF` is a low-nibble-first stream reader. It toggles flag `0x5823`; on
  one half-cycle it fetches a fresh byte from `1A38:03DA` using handle `0x7654`,
  returns `byte & 0x0F`, and on the next half-cycle returns `(byte >> 4) & 0x0F`.
2. `2740B` is the nibble-to-character decoder. It mirrors the TFH runtime logic:
  escape nibble `0xF` reads two more nibbles into one literal byte, nibble `0x0`
  recurses/skips, and other nibbles index a resident character table using base
  `0x5824`.
3. `274B8..275E3` is the TD line parser. It repeatedly calls `2740B`, stops on
  terminator `0x5E`, enforces visible width `0x31`, trims trailing spaces, and
  emits overflow metadata through helper `2738A`, just like the TFH parser.

Entry `10` target `2789D` ties those pieces together for one help page. It
rejects contexts whose `0x765A[index]` entry is zero, seeks to the per-context
block via `1A38:032D` using the offset from `2784F`, reads one follow-up word
through `1A38:0418` into `0x7656`, and then parses up to `0x0F` lines via
`27461`. That makes the current best TDH runtime model much more specific:

1. lazy-load help stream and a fixed runtime table into `0x7658/0x765A`
2. select context through `0x5820`
3. seek to `sum(table[0..index-1]) + 2 * header_word + 2`
4. read one page-control word (`0x7656`)
5. decode `'^'`-terminated lines through the same nibble-coded alphabet shape as TFH

This still does not explain the TDH on-disk first-stage table walk by itself,
but it finally proves that the higher text layer above that stage is no longer
opaque: TDH ultimately feeds the same low-nibble-first text alphabet and the
same `0x5E`/`0x31` line discipline already confirmed on the TFH side.

The stream layer below that parser is now much clearer. The TD help loader at
`20FA:1295` opens the file through `1A38:00B1`, stores the returned handle in
`0x7654`, reads one big-endian word through `1A38:0418` into `0x7658`, then
loops exactly `0x212` times calling `1A38:0418` again and storing each result in
`0x765A[si]`. So the runtime table is not an inferred bulk-read myth; the code
really does populate `0x765A` from `530` successive big-endian words delivered
by the stream object.

The remaining open question used to be whether that stream object was itself a
hidden TDH decoder. The new answer is: probably not. The `1A38:00B1` wrapper is
still the only currently observed TD help caller, but the special `0x71FC = 1`
branch now looks like a path-search/open variant rather than a decode filter.
At `1A38:0453`, the normal branch calls `1E4A:0033`, while the help branch calls
`0AE9:00FF`; that helper first tries the direct open, then retries through path
search logic using the string at `0x381B`, and finally still returns an ordinary
handle stored in `[si]`. Refill helper `1A38:038D` then seeks via `1A38:032D`,
reads bytes into the buffer at `[si+9]` through `1DD9:0005`, and `1A38:0418`
assembles big-endian words from two `1A38:03DA` byte reads. So the current best
reading is that TD is consuming raw file bytes, not a hidden expanded stream.

The actual missing detail was not “hidden decoded bytes”, but one signed add.
Entry `10` target `2784F` does not sum `0x765A` as unsigned block sizes. For
each entry it executes `cwd` before the add, so every table word is treated as a
signed 16-bit delta. The routine returns:

`2 * 0x7658 + 2 + sum(sign16(0x765A[0 .. context-1]))`

and `2789D` then only checks whether the current table word is zero before it
seeks to that start offset, reads one per-page control word into `0x7656`, and
hands the rest of the byte stream to the nibble/line parser. In other words,
TDH runtime entries are not block lengths. They are cumulative signed start
deltas, and the parser itself finds the end of each topic in-stream.

That resolves the earlier high-context contradiction directly. Under the real
runtime formula, TDH 1.0 context `1` starts at `0x040F`, not `0x0410`, and
already decodes as centered `HELP INDEX`; context `2` starts at `0x0533` and
decodes as the welcome page; high direct hotlink targets such as `371`, `384`,
`387`, `396`, `405`, `422`, `463`, `465`, `467`, `468`, and `469` all land in
range and decode as the expected breakpoint / C / assembler topics. The same is
true on TDH 2.x for the corresponding targets up to `483`.

This does not fully settle the family rule yet, but it changes the
interpretation a lot. The runtime does not load “left table only” or “left
table plus some guessed extra sizes”; it uses a signed runtime map whose active
width depends on the sample family. On TDH 1.0 the active map is the legacy
fixed `530` words, spanning the whole `259+259` visible pair, the separator
word, and `11` more words from the payload prefix. On the later TDH 2.x sample,
the active map is the whole `596`-word pre-separator prefix, which yields
readable extra contexts `530..595`. The important runtime facts are now:

The raw file layout now gives that split a stronger physical explanation. In
the TDH 1.0 sample, the two visible halves after the header contribute only
`259+259 = 518` words before the separator, so the fixed post-header `530`-word
runtime load necessarily overruns by `12` words: it consumes the separator word
`0x0001` plus the first `11` words of the nibble-coded payload stream. The byte
window around the boundary shows exactly that shape: the separator is followed
immediately by the live payload prefix (`A0 CC CC CC ... FC 48 5F F4 ...`). In
the later TDH 2.x sample, the widened `298+298 = 596` visible words already fill
the whole runtime map width, so the `596`-word model stops cleanly just before
the separator instead of spilling into the payload. That still is not a direct
resident-code proof for 2.x, but it does show that the 1.0-vs-2.x split is a
real on-disk family difference, not just a reader-side heuristic.

1. TDH 1.0 has a live signed-delta context map with `530` slots (`0..529`)
2. the later 2.x sample has a live signed-delta context map with `596` slots (`0..595`)
3. slot `0` is effectively a separator-aligned artifact; real help starts at context `1`
4. context starts come from signed cumulative deltas, not unsigned block sizes
5. per-topic termination is in the text stream itself, so runtime never needs an explicit current-block length

For TDH 1.0, that legacy `530`-slot side is already supported by code-level
runtime evidence: the documented overlay loader reads one word into `0x7658`
and then a fixed `0x212` words into `0x765A`. For TDH 2.x, the `596`-slot side
is not yet backed by an equally direct resident-code loader trace; the current
proof is that the full pre-separator prefix decodes cleanly, yields zero
out-of-range page words, and exposes readable continuation topics beyond
context `529`.

That late-context region is not just a formally in-bounds tail. The first
confirmed exposed cluster in the later TDH 2.x sample is already thematically
coherent and plainly readable: context `530` starts with the Ctrl-function-key
help page (`In some cases, a Ctrl function key duplicates ...`), `531` is the
Object Instance Inspector list-pane help, `532` is the `Methods` toggle page,
`533` opens `Object Hierarchy`, `534` is `Show inherited`, `535` is the first
object-type Inspector entry, `536` is the `Tree` pane switch, `538` is the
`Parents` toggle, and `540` is the Hierarchy-window alphabetical-list pane
help. The one unusual front-edge slot is context `537`, but it is no longer a
decode mystery: on the current 2.x sample its raw partition is exactly the
three-byte block `00 00 0D`, i.e. page word zero plus one low-nibble `^`
terminator byte that immediately stops at the next block's zero page word. So
the 596-width model is already exposing a real late help cluster, not random
residue after the legacy 530-slot range. The remaining question around `537`
is only presentation policy, because nearby context `539` still carries an
otherwise unreferenced second object-type Inspector page that may represent the
tree-pane local-menu `Inspect` text.

That late cluster now extends cleanly through the whole exposed tail
`541..595`. Thematically, `541..550` continue the Object Hierarchy / Object
Type Inspector help set; `551..553` and `561..562` are dialog/help-picker
pages that repeatedly chain into shared dialog help context `576`; `554..560`
cover Execution History / reverse-debugging help; `565..570` cover symbol-load
and relocation prompts and errors; `571..575` describe follow-pointer modes in
the code/data panes; `576..579` cover dialog navigation and Execution History
list panes; `580..581` document hardware-breakpoint match modes; `582..587`
cover language and display options; and `588..595` cover breakpoint actions,
conditions, and an inspector local-menu recap. Inline hotspots remain common in
this range, and the observed `next_context` links are consistent with shared UI
help pages rather than with dead padding. So the current later TDH 2.x sample
now has a fully confirmed coherent late-topic region `530..595`, not just one
small readable island near `530`.

One more cross-sample fact now sharpens that runtime picture. In the raw
`HELP INDEX` block, all currently verified high TDH 1.0 targets shift by a
uniform `+14` in the TDH 2.x sample, while `Help on Help` remains at context
`2`. For example: `Assembler 387 -> 401`, `Breakpoints 371 -> 385`,
`Byte lists 384 -> 398`, `C Debugging tips 405 -> 419`, and the whole
assembler subcluster `463/465/467/468/469 -> 477/479/481/482/483`. The same
`+14` shift also appears on the next clean help page (`Examining Data 374 ->
388`, `Windows 375 -> 389`, `Local Menus 376 -> 390`, `Expressions 377 -> 391`,
`Function Keys 382 -> 396`, `Command line 407 -> 421`). So the offset is a real
property of the runtime namespace, not a parser accident.

That same shift pattern is not confined to the index page. In the next clean TD
help page (`Help on Help` / context `2` under the current raw low-context
approximation), the readable high-target subset also shifts by `+14` between the
two samples: `Examining Data 374 -> 388`, `Windows 375 -> 389`,
`Local Menus 376 -> 390`, `Expressions 377 -> 391`, `Function Keys 382 -> 396`,
and `Command line 407 -> 421`. So the observed offset is a broader runtime
context-space property, not just one quirk of `HELP INDEX`.

That uniform shift also suggests one useful working hypothesis for the exposed
2.x tail. If the same `+14` offset continues through the whole old high-context
tail, then legacy TDH 1.0 context `529` would land at TDH 2.x context `543`.
Under that model, the first `14` contexts of the confirmed late 2.x region
(`530..543`) would be shifted legacy tail topics, and the clearly extra 2.x-only
tail would begin at `544`. This is still only a hypothesis, not a proved family
rule, but it sharply narrows what the remaining `+14` explanation needs to
account for.

That arithmetic implication is itself already useful: under the current uniform
shift model, the unresolved overlap window is no longer the whole late 2.x tail
but only the front edge `530..543`. Everything from `544` onward already lies
beyond the shifted TDH 1.0 ceiling (`529 + 14 = 543`), so the later sample's
far tail `544..595` is the minimum guaranteed extra 2.x namespace region if the
observed `+14` rule really does continue through the end of the legacy high
tail. In other words, the remaining content-side ambiguity is now concentrated
on a `14`-context boundary problem, not on the full `66`-context exposed tail.

One caveat matters on that front edge: the end of the TDH 1.0 high namespace is
already alias-heavy, not a clean run of standalone pages. The current reader's
alias reconstruction marks embedded out-of-range starts as redirects, and the
tests already pin several late legacy contexts that way: `520 -> 425`,
`521 -> 380`, `522 -> 314`, `527 -> 393`, and `528 -> 328`. So a naive
title-for-title comparison inside the candidate overlap window does not yet
falsify the `+14` model. Some of `530..543` may correspond to shifted legacy
redirect contexts rather than to shifted standalone page bodies.

The old front-edge blind spot is now much narrower than before. Runtime metadata
from the current TDH 1.0 reader no longer leaves any unresolved out-of-range
alias contexts: `519..529` are all observed alias continuations, resolving to
owner contexts `516`, `424`, `380`, `314`, `220`, `156`, `152`, `294`, `392`,
`328`, and `306` respectively, with only context `528` still needing the text
fallback rather than structural embedded-start detection. So legacy
`523..526` and `529` are no longer unnamed blind spots; they are directly
witnessed alias continuations into lower help pages.

That changes the remaining content-side question materially. The later 2.x
sample still exposes a coherent readable front edge through `530..543`, but the
legacy side of that boundary no longer hides an unknown run of standalone high
pages. The main unresolved family-level question is therefore no longer the
existence of missing legacy anchors in `523..529`, but the direct 2.x
loader/service proof that explains how the widened `596`-slot runtime map is
reached at runtime.

One newly confirmed local source for those missing anchors is the original ZIP
packaging itself. Direct central-directory reads now give the exact archive
split: `TD.ZIP` contains `TD.EXE`, `HELPME!.DOC`, and `MANUAL.DOC`;
`TPROF.ZIP` contains `TPROF.EXE`, `TFINST.EXE`, and `HELPME!.DOC`;
`TD286.ZIP` contains only `TD286.EXE` and `TD286INS.EXE`; and `TDUTIL.ZIP`
contains the whole later 386-side utility set, including `TD386.EXE`,
`TDH386.SYS`, and `TDHELP.TDH`. That makes the packaging claim itself direct,
not inferred. Those bundled DOC files are no longer just hypothetical anchors:
the repo-local `tools/zip_implode.py` helper now successfully extracts all
three known method-6 text members (`TD.ZIP:HELPME!.DOC`, `TD.ZIP:MANUAL.DOC`,
`TPROF.ZIP:HELPME!.DOC`) into plain text. They turned out to be product Q&A /
manual material rather than a direct dump of the internal Object Hierarchy help
cluster, so they do not by themselves explain the UI intent behind nearby
unreferenced tree-pane `Inspect` text at context `539`, but they do remove the
old archive-execution blocker around bundled TD/TPROF documentation. The raw
file itself already settles that context `537` is intentionally empty at the
format level.

Archive details are now precise enough to guide that follow-up. All three DOC
members (`TD.ZIP:HELPME!.DOC`, `TD.ZIP:MANUAL.DOC`, `TPROF.ZIP:HELPME!.DOC`)
use PKZIP method `6` with general-purpose flags `0x0006`, i.e. the old
`implode` variant rather than `stored` or `deflate`. In these samples that also
means the same local-header shape and no extra fields, with local member
offsets `0x38841` (`TD` helpme), `0x3A544` (`TD` manual), and `0x3A0A7`
(`TPROF` helpme). The relevant `TDUTIL.ZIP` members follow the same archive
method family: the central directory shows method `6` for `TD386.EXE`,
`TDH386.SYS`, and `TDHELP.TDH`, with local-header offsets `0x000000`,
`0x00779A`, and `0x02D740` respectively. So the blocker is now narrower and
explicit: extracting either those texts or the 386-side companion/service files
from the original archives requires an `implode`-capable unpacker or a small
dedicated decoder, not just standard-library ZIP handling. The repo now carries
that decoder path directly in `tools/zip_implode.py`, including central-
directory member listing and ZIP-aware method-6 decode for named members. With
the DOC payloads now extracted successfully, the remaining practical blocker is
interpreting any still-needed 386-side service payloads rather than getting the
text documents out of the ZIPs at all.

That decoder path is now much less speculative. Cross-checking against the
official ZIP APPNOTE and Info-ZIP's `explode.c` narrows these members to the
standard ZIP method-6 stream, not some Borland-specific subformat. For ZIP
method `6`, bits `1` and `2` of the general-purpose flag live outside the
compressed stream and define the mode directly; on these samples `0x0006`
means `8K` dictionary plus coded literals, so minimum match length is `3` and
the raw low-distance field is `7` bits. The stream itself therefore begins
immediately with three Shannon-Fano trees in order `literal(256) -> length(64)
-> distance(64)`, each parsed by the usual `count_byte + 1` wrapper followed by
`count/bitlen` nibbles (`high+1`, `low+1`).

This also explains why Adler's small `blast.c` probe was close but not a drop-
in reader for these archive members. `blast` expects a DCL-style two-byte
prologue that carries the literal/dictionary mode inside the compressed data,
whereas ZIP method `6` carries that mode in the outer ZIP flags and starts the
member data directly with the tree blocks. So the practical next step is no
longer "find any unpacker" in the abstract; it is specifically to reuse or port
an Info-ZIP-style `explode.c` path (or an equivalent ZIP-aware method-6
decoder) for those three bundled DOC entries.

A broad smoke test now supports that signed-runtime interpretation almost
end-to-end. Using the real runtime start formula and then feeding bytes from
that start onward into the already-validated TFH nibble/line parser yields
plainly readable topic text across essentially the whole live TDH namespace on
both known samples. On both TDH 1.0 and TDH 2.x, all `530` runtime starts land
inside the file, and a simple readability check marks `528` of the `529`
user-visible contexts (`1..529`) as clearly readable; the only low-score page is
a formatting-heavy table topic rather than obvious garbage. So the old “sparse
high contexts are unexplained” blocker is gone. The current remaining TDH work
is mostly descriptive: naming the exact physical role of the visible header
regions and polishing any residual formatting edge cases, not recovering an
unknown second decoder.

`DEHELP.DOC` from the BOA/DEHELP tools explicitly lists Turbo Debugger,
Turbo Debugger for Windows, Turbo C++ for Windows, and Resource Workshop as
unsupported formats. That matches the observed separate TDH/TFH container
instead of the standard THELP layout.

## Current Reader Behavior

`thelpviewer/server/converter/readers/tdh.py` contains strict TDH and TFH detectors.
TFH uses the confirmed file-side size table, the low-nibble-first text
alphabet, and the `'^' + target word + label + '^'` control pattern above to
emit decoded topics with positioned hotspot metadata. TDH now uses the same
runtime-aligned nibble/text parser above a signed-delta context map, choosing
the larger of the legacy `0x212` load and the full pre-separator prefix width
for the known sample families.

The TDH reader metadata contains:

```json
{
  "format": "tdh",
  "format_status": "decoded",
  "tdh_probe": {
    "header_word": "0x0206",
    "table_byte_size": 518,
    "table_word_count": 259,
    "encoded_payload_offset": 1040,
    "payload_lead_byte": "0xA0",
    "payload_lead_cc_run": 9
  },
  "tdh_decode": {
    "runtime_context_count": 530,
    "runtime_table_word_count": 530
  }
}
```

That concrete JSON example is the TDH 1.0 sample shape. On the later 2.x
sample, the same metadata now reports `runtime_context_count = 596` and
`runtime_table_word_count = 596`. The alias-resolution counters now live in
that same `tdh_decode` block as
`out_of_range_page_word_context_count`,
`out_of_range_page_word_contexts`,
`embedded_alias_context_count`,
`embedded_alias_contexts`,
`text_alias_context_count`, and
`text_alias_contexts`, plus
`remaining_unresolved_alias_context_count` and
`remaining_unresolved_alias_contexts`, so the remaining heuristic surface is
measured explicitly instead of being inferred only from redirect behavior.

For the current TFH sample, the reader now recovers all `363` context blocks,
exposes real strings such as `HELP INDEX` and `Welcome to Turbo Profiler's help
facility...`, extracts hundreds of hotspot spans from menu and inline-reference
topics, emits runtime-style `49`-column wrapped screen lines, and exposes the
block control word as `next_context` / `Next` navigation when non-zero.

The archive-inspection side is also less speculative than before. The repo now
has a local method-6 ZIP helper in `tools/zip_implode.py` that can list central
directory members and decode named implode entries without depending on an
external `unzip`/`7z` toolchain. That path has now been exercised successfully
for the three bundled DOC members, so the remaining archive blocker is no
longer text extraction; it is whether any extra signal still needs to be mined
from the 386-side service payloads.

## Remaining Cleanup

Known-sample reader/converter support is already in place for the current TDH
1.0, later TDH 2.x, and TFH real samples. The remaining work is cleanup or
out-of-sample validation rather than missing core decode:

| Area | Remaining result |
|------|---------------|
| TDH family rule | Optional cleanup only: identify the exact Borland component/install path behind the shared selector-style TD 2.0 service families `0340:*` / `0430:*` and the neighboring `0090:*` / `00C8:*` bridge layer. The behavioral map is already fairly tight: stream open/read/seek are visible at `0048`, `0034`, and `0061`, while the neighboring bridge entries now look allocator/query/fetch/dispatch-like (`0078/0082`, `01DD/01E7`, `008F/0099`, `0135/013F`). Current local evidence argues against a standard named DPMI/VCPI extender and instead points to a Borland-internal service layer whose public/runtime name is still unrecovered. |
| TDH 2.x late contexts | Optional viewer/export policy only: decide whether the genuine blank placeholder context `537` should remain exported as-is or be presentation-collapsed to the otherwise unreferenced tree-pane `Inspect` text at context `539`. |
| TFH out-of-sample edge cases | Validate rare paths not exercised by current real samples (for example oversized hotspot-label continuation across screen lines). |
| Text attributes | Any link, color, selection, or layout markers beyond those already observed in the current TFH sample set. |

TDH/TFH should still remain separate from THELP. The practical open items are
now narrowed to the exact Borland-side owner of the shared selector-style
service families, the optional export policy for blank placeholder context
`537`, and validation of TFH edge cases that are not covered by the current
real sample family.
