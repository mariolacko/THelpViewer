# Format Conversion RE Notes

Internal implementation/mapping excerpts removed from the format datasheets.
These are historical notes, not source-format fields. Some examples refer to
obsolete tools or behavior; current decoder code and CHANGELOG take precedence.

## QuickC 2.50 split-media closure (2026-10-14)

The Archive.org `microsoft-quick-c-2.50` distribution is complete: its
2,808,328-byte `Microsoft QuickC 2.50.zip` has SHA-1
`329db59baf4d10c4ab8c5da38ea2afaa1fa8408a`. `PACKING.LST` names the Advisor
disk's QC.HLP as part 1 and the Learning disk's QC.HL2 as part 2. Physical
QC.HL$ contains an SZ/D1 header and the beginning of the stream; QC.HL2's
eight-byte SZ/02 header precedes its continuation. The old extractor treated
only the first part as a standalone compressed file and silently skipped its
EOF error. This was not a missing source distribution or a QuickHelp parser
failure.

The shared downloader now validates and joins uniquely named media parts,
preserving one LZSS dictionary/control/token state. It bounds declared output,
rejects bad headers, missing/gapped/duplicate parts and symbolic links, and
surfaces recognized compression errors before copying originals. Unit cases
split inside both literals and overlapping dictionary tokens; original media
checks use the normal unar+7-Zip fallback and the 7-Zip-only path. `unar`
alone does not recognize these FAT images and is not claimed to support them.

The restored QC.HLP is 504,694 bytes, CRC32 `0143767A`, SHA-256
`5c256559a80df21a8040f440c6e1726bb8c56fa10a02866ad0cea0306c88fd43`.
It has one case-sensitive `qc.hlp` database, 876 topics and 414 index entries.
Its CRC entry supplies both an exact-member direct job and Archive.org
release/search provenance; the actual fallback query returns the verified
distribution. `download_products(..., source_keys=["direct"])` installs it
without warnings. Existing originals are preserved.

Staged `build_help_groups(..., product_keys=["quickc"])` publishes 255 bundles
and 173,307 topics while preserving unrelated content byte-for-byte and
retaining the previous generation as a recoverable backup. The SHA-256 checks
cover all 496 originals and 242 unrelated published files; the final build's
backup is `data/.helps-previous-d33c082a896c455ea28490dc63df98eb`.
Contents/Index in
ERRORS.HLP now open their original QC.HLP destinations; isolated tests also
retain the no-advisor fallback. No link was removed. The shared JS link audit
reduces the 1,390 absent-QC occurrences to two appearances of the same native
control-bearing composite alias at GRAPHICS topic 168 (inline and Up).
That alias still needs original-consumer evidence. Across the full catalog,
94 unresolved occurrences remain, with no out-of-range emitted row targets,
missing TextScreens or invalid UHF link syntax. Windows/SC 2000/SCX deferrals
are unchanged.

The downloader/QuickHelp/server-build/docs regression set reports 258 passes;
the final SZ/reader/Markdown repetition reports 36 passes. Repository test
caches are absent. No commits or production deployment are included.

## Complete source/publication check (2026-10-14)

The four additional SC 2000 prose records in Cheater 21 TEXTY.DAT are explicitly
deferred at the user's request. No consumer search, guessed text/font/page
conversion, Windows graphics or SCX palette work is included in this pass.

Isolated `export_bundle_tree(..., layout="helps")` regeneration selects 355
inputs from the 495 retained source files, producing 272 outputs in 22 output
format families with no conversion errors. The installed 254 bundles match
fresh logical JSON in every field except the converter date. Catalog entries
also match their bundle metadata. The 18 additional Turbo Basic/Prolog outputs
belong to products absent from the saved server selection and are not activated.
All 495 original and 256 published-file hashes stay unchanged. The isolated
generation is retained at `/tmp/thelp-audit-closure.cvEYak/helps`; it is not
another product/staging directory under permanent HELP storage.

The published-link check uses the actual shared JS catalog/alias/cursor
resolvers, not a second heuristic filename matcher. Across 254 bundles and
172,431 topics it resolves 836,830 internal and 34,547 external references,
checks 11,206 navigation actions and all 608 screen references. No emitted
line target is out of range and no referenced TextScreen is missing. It
separately counts 3,539 reader-declared unavailable source-context references
and 47 deferred Windows macros, without deleting them or manufacturing text.
The remaining 1,482 unresolved reference occurrences are not all parser faults:
1,390 point to the absent matching QuickC 2.50 QC.HLP; the others include
unprovided PWB API libraries, Windows external names/hashes and three v6
shareware references to unavailable PROGRAM markers. Existing-file targets
without a verified native context require their own source evidence. The
check does not claim all cross-file destinations are available.

The complete test run reports 2,229 passes, five failures and one opt-in Safari
skip in 728.75 seconds, with the existing Starlette/httpx deprecation warning.
Three BW03 failures come solely from newly added empty `fonts`/`text_screens`
model fields. Explicit empty-resource assertions restore comparison against
the same original independent digests; no golden hashes or decoder output are
changed. The generated entry-page template had older JS/CSS cache revisions
than www/index.html and is now synchronized, protecting static exports from
cached pre-TextScreen code. The fifth failure is an intermittent direct DOS
backend Zoom geometry check. Both backends pass on isolated repetition and
an additional direct-backend run passes, but no runtime cause/fix is claimed;
the test now includes actual before/after/desktop rectangles on failure.
The focused repetitions report 65 passes, then 25 passes, then one direct
backend pass. A final metadata/BW03/docs/export/widget check reports another
109 passes. The broad pre-fix run is not reported as a fully green run.
Repository bytecode/test caches are absent; no commits or production deployment
are part of this check.

## Regression closure (2026-10-13)

The DOS converter/downloader suite reports 1,531 passes. The complete suite
reports 2,014 passes, one opt-in Safari skip and two failures that were then
isolated: the browser's timed UI script waited only 20 seconds for an empty
full-corpus index, and copying the cached 4.52 CD archive timed out while it
was a macOS cloud placeholder. The browser fixture now waits for an available,
ready index before starting its timed UI assertions, with a bounded deadline
and immediate database-error reporting. Its readiness/error/timeout regressions
and the repeated browser/download checks report 10 passes. No Windows decoder
or graphics support was changed.

The final Game-Cheater/BW03 checks report 81 passes, including ten boundary
cases for the database fixture writer: the first terminal memo page holds
510 payload bytes, subsequent terminal pages 512, and only continued pages
reserve a pointer. The original BW03 digests remain unchanged as described
below. `git diff --check` passes; repository bytecode/test caches are absent.

macOS marked the local index, account/statistics databases, generated bundles
and CD download as `dataless`. Reading them through the host restored their
content without deleting/replacing databases or originals; Docker could then
serve the complete Game-Cheater bundle and return real global-search results.
Cloud materialization also changes source fingerprints and can trigger an
index refresh. This is local filesystem evidence, not a source-format defect
or a claim about the public server.

## Windows Help companion decoding (2026-10-12)

The installed 20 Borland Windows HLX trees match the original 4.52 CD,
not an assumed generic 4.5 release. Matching HLPs are now retained and
CRC/provenance-registered, with distinct BCW/OWL 4.5 pairs kept separately.
The shared Windows Help container/B+ tree and native topic backend verifies
every decompressed packet and resolves all native keyword addresses. HC31
paragraph/table/font/inline-link text projection is now registered; bitmap
pixels, image-region links and full Windows macro behavior remain limitations.
The inspected corpus now contains 495 originals: 354 selected conversion
inputs (including 22 text HC31 HLPs), 22 retained same-stem HLX indexes, and
119 other companion/non-conversion files. Public bundles total 253, including
two additional 4.5 editions, now built from HLP rather than their HLX indexes.
Shared alias destinations now retain native cursor rows, including external
file navigation and public URL resolution. Numeric and symbolic aliases use
the viewer's direct-ID priority and native context-case rules; alias rows do
not become extra articles. Windows graphics remain explicitly deferred.
See [Windows Help RE Notes](../Formats/Windows%20Help%20RE%20Notes.md) and
[HLX RE Notes](../Formats/Borland%20HLX%20RE%20Notes.md) for current evidence.

## THELP consumer defaults and page navigation (2026-10-12)

The Pascal 4 original compiler disk supplies a format 2/1 consumer, not a
reconstructed implementation. Distribution:
[Borland Turbo Pascal 4.0](https://archive.org/details/BorlandTurboPascal4.0),
`https://archive.org/download/BorlandTurboPascal4.0/disk1_compiler.img`.
The disk image is 368,640 bytes, archive-metadata SHA-1
`d5a65adc300a310fcbe3497f3fd153ca65db5c69`, SHA-256
`1b933069e4f96529dc52cfeaa77fbd9464dd23cdb9c61f780bf47c4e567bbf6c`.
Its `TURBO.HLP` is byte-identical to the installed CRC `58AB33C3` edition:
85,344 bytes, SHA-256
`0bf6ed99bb45ff65823e8d309da897af31082b7417af133b1a4a4813a4060a34`.
No duplicate edition is added. The manifest retains the verified release
page, portable search text/fallback query and a pinned disk URL; extraction
selects only `TURBO.HLP`, not the runtime/compiler companions used for research.
The actual fallback Archive.org query returns eight results including this
verified item; downloader regression extracts the same CRC and no companions.

Original `TURBO.EXE`: 115,272 bytes, CRC `8BA16332`, SHA-256
`c7877cc1f42eaeb4df9da4bfb6bfb9e109675a2de39c7bce3cb5eea0b40dbb34`.
The lookup routine at file `4EADh..4F18h` checks the context range and reads
the addressed three-byte entry. If the number is invalid or the offset is
`FFFFFFh`, file `4EF1h` adds `012Ch` (100*3) to the table base and reads slot
100. It does not use a referring label or keyword range. The actual default
record starts at file offset 4,985. A caller at `5190h` also explicitly
requests context 100. An injected `FFFFFEh` slot remains -2, not slot 100.
This is a verified consumer binding for profile 2/1, not an extra short-header
field or a universal rule for other legacy profiles. The converter continues
to diagnose unavailable out-of-namespace targets rather than emulating unsafe
native input behavior.

Research harness `/tmp/thelp-thelp-defaults.H10FS4/native.py` executes the
original lookup and three-byte offset helper. Host shims supply only bounded
file seek/read, never the default-selection logic; interrupts are forbidden,
with a 10,000-instruction limit. All 509 original context slots and four
invalid-number probes return the expected offsets. The 129 `FFFFFFh` slots
resolve to the same index record. Compact ASCII JSON+LF tuples
`(context, stored_offset_or_null, native_resolved_offset)` in table/probe order
have SHA-256:

```text
a7edd6b9bf3522d473260378c77a37c2d78776edd3e2d044476f59e863ead52a
```

The converter retains all 129 default aliases, including genuine context
zero. Unverified legacy/short-header bindings are unknown instead of the
previous assumed zero. Both positioned and sequential layouts consistently
mark the actual stored/default Contents record. The shared primary-selection
rule does not require a negative alias slot. No missing default body is
replaced with an arbitrary visible topic; No Help stays a distinct condition.
Pascal 7's slot-4 failure behavior remains consumer-specific, not transplanted
to all files by extension or filename.

THELP page Up/Down WORDs now normalize terminal zero to no link. Their actual
nonzero contexts provide Prev/Next as well; legacy hotspot direction bytes
remain one-based keyword-selection indices, not topic IDs. Raw parser fields
and the normalized positioned-keyword navigation tuples stay intact. For
example Pascal 4 index pages form `100 -> 101 -> 102`, and Sidekick 2's
`128 -> 327` pair exposes Next on the first page and Prev on the last, never
a fake page-zero link. This changes shared-model navigation, not source data.

`verify.py` compares the preceding reader with every one of the 66 original
copies: all 93,032 topic IDs, source rows, code attributes, 85,484 index entries,
41,537 positioned and 369,218 sequential targets remain intact. It verifies
each normalized page destination independently from raw Up/Down fields. The
three copies of Pascal 4 add 387 aliases in total; 19 Contents flags change.
There are 179,088 raw terminal-zero page words and 93,029 changed navigation
projections. The previous model had 19,484 Prev/Next items derived from
positioned keyword indices; they are not encoded page-context references.
Source-hash aggregate remains
`a954f9228d530acfae475c91590247e4554c818a3873e26843aa578aaab0a0b0`.
Complete model aggregate after these corrections:

```text
b6b98d250813484b76e3a7bf311e5567b6802c59baa400ece8f4cb00e729942e
```

Focused default/alias/word-flow/control/product/navigation/download regressions
report 194 passes. Initial synthetic positioned-link fixtures used the wrong
one-based row/column range; native margin-inclusive coordinates fix the tests
without changing rendering code. A separate shared-browser defect dropped
numeric alias zero through `value || ""`; `value ?? ""` preserves it without
overriding a real topic-zero entry. Regression checks cover numeric/string
zero, null/empty references, ordinary aliases and direct-topic precedence.
An invalid Contents WORD equal to the parser's unassigned-screen marker must
not mark synthetic orphan topics as Contents either.

Publication stages 62 canonical `bc`/`bp`/`sk`/`tasm`/`tc`/`tp` bundles,
keeping every manifest product. Thirty-nine THELP payloads change 59,195
navigation projections, six Contents flags and the 129 Pascal 4 aliases.
All source text, rendered content, keyword/record/topic IDs, index labels,
other-format payloads, 191 unselected files including the catalog, and all
251 catalog entries remain intact. The complete prepublication library is
recoverable at `data/.helps-previous-3d8ffd2f6bac43ea9e29e82012ddbc5d/`.
Native-source and public Docs/bundle HTTP byte checks pass. The publication
checker initially applied THELP navigation invariants to unchanged HLX/
Sidekick payloads and then confused reader name `borland` with transport
format `thelp`; correcting the checker validates the same publication without
rebuilding or changing those formats. One HTTP verification ran during the
local container restart; repeating it after health checks passes.

Real headless Chrome mouse input opens Pascal 4 alias 140 at canonical
index 100, Next at 101/102, Previous at 101, and Help Contents at 100 in the
same window. The first/last page does not expose a bogus previous/next item.
A direct URL with `topic=0` also resolves to index 100. Sidekick 2's `<more>`
opens 327 and Previous returns to 128. Screenshot
`/tmp/thelp-defaults-browser.cOlwa8/pascal4-index.png` has been inspected.
Initial clicks occurred underneath the correctly modal global-index progress
dialog; waiting for the intended control to be the hit-test target fixes the
harness, without bypassing modal handling or altering application event code.
All browser profiles are isolated temporary profiles, not the user's session.
The local Docker health check passes; global index is ready at 100% with
146,906 topics, 35 documents and no warnings. No commit or production
deployment is performed.
Docker Python 3.12 also verifies native default/alias-zero resolution,
terminal page directions and the published first/last index pages. The
public topic-zero URL redirects to its genuine canonical topic, not a 404.

The final complete suite reports 1,667 passes, one skipped Safari test and
the existing Starlette/httpx deprecation warning (308.91 seconds). Separate
final default/browser-alias regressions report 21 passes; native-edition
download/browser-navigation regressions report 14 passes. Mirrored assets
are byte-identical, both `node --check` invocations and `git diff --check`
pass. Repository bytecode/test caches are absent after every test run.

The follow-up Sidekick 2 investigation below corrects this pass's assumption
about its header: the original has a nine-byte long 4/2 header storing zero,
not an unknown short-header binding. Its consumer roots are application-owned.

## Sidekick 2 application-owned Contents roots (2026-10-12)

The original
[2.0 January 1991 distribution](https://winworldpc.com/download/2d20744e-7356-11c3-a7c2-9d25525400ef)
is retained at `var/downloads/help/ww_sidekick2_19910111.7z`. The package
is 1,576,234 bytes; SHA-256
`efe04e87e9e32e89b3033993d055b56592198e816d7f34b8f9c567f3fecfd88e`.
Its SHA-512 matches the download page:

```text
6dc7b297f082641241a6e6d4b251cc21349e45af21369566b60182b4026c7a3511cb811350c84b7d2f5db1022ba89b973a6dcfa1f94f832d3429784644097083
```

Disk 3's `SK2-5.ZIP` contains `SK2.HLP`: 231,761 bytes, CRC `58D27871`,
SHA-256 `d74837a0b2bf06bf8663ba63755831557a6722de1bab9b6da690519d9efbc82f`.
It is byte-identical to both installed Sidekick 2 originals, so no additional
edition or source directory is created. The CRC entry retains the release and
download-selector pages, portable search text, fallback query and exact
`SK2.HLP` extraction member. No EXE/overlay/lexicon/font companions are retained
by downloader jobs. The fallback query is a discovery hint, not proof that
Archive.org currently holds this particular DOS edition.

For executable research only, concatenate the original `SK2.EX1` (300,000),
`SK2.EX2` (390,000) and `SK2.EX3` (37,360) from disk 1/2's ZIP members.
`SK2.EXE` has 727,360 bytes, CRC `8ACB3348`, SHA-256
`ce3ff65f70a206f6b9df259e81bd482ccb8426594ad66530545507b279bb6416`.
No installed user software or HELP bytes are modified.

The HLP's record at offset 32 is `00 09 00 00 00 00 00 D3 01 11 32 00`:
a **long nine-byte** 4/2 header, stored Contents 0, max screen payload 467,
17 rows, 50 columns and no margin. Its Context table has 1,145 slots,
370 `FFFFFFh`, seven `FFFFFEh` (including slot 0), and 768 actual Text
records. Its native Index Count is zero. The intermediate model intentionally
generates 768 index entries; the viewer previously opened that generated index,
not the first physical `No Carrier` record. Earlier progress claims based only
on physical parser order are corrected here; no invented short-header binding
or global Contents offset is introduced.

Original file `8C9D8h..8CA6Eh` reads a signed three-byte context address.
For invalid context numbers, `FFFFFFh` **or** `FFFFFEh`, `8CA3Bh` reads table
slot 100. That context is Address Book, not global Contents. This is native
failure policy, not proof that all failed slots are source aliases.
Original `8CDE8h..8CE31h` instead selects an eight-byte application root
record from DS:`009Eh`; original table bytes are at file `3A81Eh..3A88Dh`.
The table's first record is `(FFFFh,101,101,0)`. A current-desktop application
offset of `FFFFh` selects that record, so no-application Contents and General
both use 101. Other records select Contents 800 (Notepad), 900 (Time Planner),
100 (Address Book), 200 (Communications) or 700 (Calculator); General is 101
throughout. The fourth WORD is another contextual root, not a header field.
The original event handler uses the returned record's +2/+4 WORDs for Contents/
General and keeps page Up/Down and keyword-selection bytes separate.

`/tmp/thelp-sidekick2-defaults.nSIDXz/native.py` executes these original
routines in bounded 16-bit Unicorn. Host shims supply only seek/read and the
current-desktop pointer; no lookup/root-selection logic is reimplemented in
the host. Interrupts are forbidden and each call has a 10,000-instruction
budget. All 1,145 original context slots, followed by invalid-number probes
`-1`, `-2`, `1145`, `32767`, and all 14 table records match. Compact ASCII
JSON+LF fingerprints (native code receives the low unsigned WORD of a context):

```text
lookup tuples (context, stored_offset_or_null, native_resolved_offset):
4f69906fca468a7b3a012e9f185e1e7bd3f79c22aa971476bb3cf0e08d098152
root tuples (application, contents, general, contextual_root), table order:
4bb705f87b0bb90ecc901124ab52d5c1629f13004137873d8a010763ba170d29
```

The catalog supplies the verified no-application root 101 through the existing
CRC-backed `help_contents_topic_id` override, with release 2.0. The lossless
parser retains stored zero; all topics, source links, page chains and failed
slot identities stay intact. No `KATO` filename switch, guessed label map,
new renderer or fake global aliases are added. The universal viewer's empty-
index fallback now prefers a reader-supplied Contents tree before its first
topic, and delegated opens add only one history entry. Sidekick itself keeps
its generated index in addition to the verified start page.

The WinWorld provider had ignored pinned editions' collection directories,
constructing a new label/release path. It now passes the configured collection
to shared version processing, while ordinary family discovery is unchanged.
Real archive extraction regressions cover Sidekick's `Borland Sidekick 2/`
despite release 2.0, existing TASM collection paths, exact member selection,
CRC equality and absence of runtime companions. Existing sources are not moved.

Validated staged publication selects the four existing Sidekick bundles and
changes only Sidekick 2's default-root/release metadata (and its catalog release).
All 768 topics, their content/links/aliases/page chains, the generated index,
all 66 THELP originals, unselected bundle bytes and all 251 catalog entries
remain intact. The previous complete HELP tree is recoverable from
`data/.helps-previous-9332b74d8c744c57b12c9b94822f28b7/`.

Actual headless Chrome mouse input verifies the file-only default 101,
General's authored Address Book target 102, Help Contents returning to 101,
the 768-entry Index, and `<more>` 128 -> 327 / Previous -> 128 in one window.
The first layout probe exposed an unrelated shared-screen defect: a long
SSR fallback enlarged the min-height application grid, so the new window
centered at y=6069 before removal of the fallback shrank the desktop. A fixed
viewport height on the existing root grid resolves this for all HELP, document
and restored windows; no Sidekick-specific repositioning service is added.
The final browser captures show the complete frame at y=238..574 inside the
desktop y=16..797. Browser regressions now check HELP/topic/document bounds
and status-line placement, not merely existence of a window node.
The focused suite reports 45 passes with the existing Starlette/httpx warning;
repository bytecode and temporary test caches remain absent.

A narrower-viewport follow-up reproduced offscreen locally saved positions,
independently of SSR: a wide-screen x=424 or stale y=6069 remained unchanged
on a 390-pixel desktop. Shared `restoreState()` now constrains positions after
size/minimum restoration and captures the bounded normal geometry before
maximizing. Valid positions and original size variables are retained; no
per-file local-storage reset or alias is introduced. Fake-widget regressions
cover valid/stale/oversized states and maximize/restore. Actual Chrome input
also verifies public README loading, explicit `#tv=` geometry 100/80, a fresh
390-pixel screen and seeded stale saved geometry (final frame x=12..390,
y=492..786, desktop y=14..786). Geometry/lifecycle/browser/metadata regressions
report 13 passes.

The first post-layout full-suite run reported 1,671 passes and one metadata
test failure: an asset-version bump was made while that process held the old
imported HTML template. The fresh-process template regression passes; the
checked-in and generated templates carry identical current versions.

The final fresh-process complete suite reports **1,672 passes**, one skipped
Safari test and the existing Starlette/httpx deprecation warning (309.12 seconds).
Docker's Python 3.12 independently verifies stored header 0 versus catalog/
published root 101, release 2.0 and all 768 topics/index entries. The live index
is ready with 146,906 topics, 35 documents and no warnings. All changed public
documents and mirrored browser assets match their served HTTP bytes. Final
syntax/mirror/diff checks pass; no repository bytecode or test caches remain.

One mirror request stalled on its connection and was interrupted; the alternate
distribution URL downloaded successfully and its publisher checksum matches.
The transient failure is not hidden by a per-host network/security bypass.
The emulator harness initially shadowed Python's `inspect` with a research
filename; renaming that script fixes the harness without application changes.

## Borland Sidekick 1 Help

The second original is now retained in `data/sources/Borland Sidekick 1.56b/`
and registered independently with its release/download page and fallback
search query, rather than replacing the differently sized first original.

## Evidence

The 1.56b distribution's original `SK.COM` supplies the runtime evidence.
Addresses below are COM load addresses (file offset + `100h`):

- `2F2Fh` and `2F39h` compare the first two input bytes with the executable's
  tag at `2E6Bh`; a mismatch produces “Wrong version of file”.
- The executable's offset table begins at `2E7Dh`: `0002h`, `0012h`,
  `1623h`, `2F7Bh`, etc. These equal the independently parsed context starts
  in its HLP. The HLP itself contains no offset/index table.
- `30DCh`/`30E3h` read the context's two size bytes before its display text.
- `1842h` dispatches attribute selectors `01`, `02`, `04`, returns at `03`
  or `00`, and otherwise calls the character printer.
- `31A7h` distinguishes `03` (another page) from `00` (end of context),
  retaining offsets for previous-page navigation.

This describes observed original structures and runtime behavior, not a
published universal specification of every Sidekick release.

---

## Converter mapping and limits

`readers/sidekick1.py` checks the English context-zero signature, validates
every record and preserves all pages. First pages retain their original
numeric context IDs. Continuation pages receive IDs after the context range,
with generated Prev/Next navigation only within that same context. Index and
Contents are generated from first-page text; context zero remains available
but is omitted from the generated menus. These trees and continuation IDs
are converter presentation, not stored source fields.

Normal/emphasis/key-label categories map to ordinary/bold/underlined UHF text.
This preserves category changes but is not a claim to reproduce an arbitrary
user-configured native palette. OEM arrows and box glyphs use CP437, literal
UHF brackets are escaped, and authored spacing is preserved. A terminal
“More..” cue on the last nonempty line links to the next page only when the
source's `03` separator proves that continuation exists. It retains its text,
spacing and attribute; this clickable UHF presentation is not a native source
hotspot. Other occurrences and filename mentions stay plain text. Pages without
the cue still expose their structural Prev/Next navigation. In the 42,240-byte
original, 80 of the 81 continuation boundaries have this terminal cue.
`metadata.sidekick_contexts` records offsets, dimensions and each context's
page IDs; `sidekick_version_tag` records the opaque header word.

The supported grammar is bounded to 64 KiB, 1–23 rows and 1–78 columns.
The importer requires CRLF line layout that fits those dimensions. Bare cursor
CR/LF, backspaces, wider auto-wrapping/scrolling streams and other-language
placeholder signatures are not yet covered; it rejects them instead of
silently removing controls or clipping text. Missing NULs, invalid sizes and
unrecognized tails fail conversion. EOF padding must fit the final 128-byte
record. The printer's `FF` raw-character escape depends on register state;
it is not present in the verified bodies and is rejected rather than guessed.
Sidekick Plus uses a [separate reader and directory format](../Formats/Borland%20Sidekick%20Plus%20Help.md).

## Borland Sidekick Plus Help

## Evidence and scope

The local original is `data/sources/Borland Sidekick Plus/SKPLUS.HLP`.
[The 1.00A disk listing](https://www.pcjs.org/software/pcx86/util/borland/skplus/1.00a/)
independently identifies a file of this size dated 1988-03-10. Borland's
[owner's handbook](https://www.bitsavers.org/pdf/borland/sidekick/Sidekick_Plus_Owners_Handbook_1988.pdf),
page 18, describes per-application help and highlighted lookup words.
Those references establish the product and user-facing navigation, not the
binary field layouts below: these were derived from the actual HLP tables.

All 18 group directories and 1,087 text descriptors are accounted for.
Two descriptors in the Vogon Poetry group share exactly the same text record;
there are 1,086 distinct records and 1,165 distinct display pages. Each of the
2,051 hotspot entries matches a displayed hotspot on its declared page.
All displayed rows fit their descriptor's width and height. Further runtime
verification uses the original `SKPLUS.EXE` from the 3.5-inch 1.00A distribution
and the byte-identical HLP from the independent 5.25-inch set. Addresses below
are **file offsets**, not MZ entry-point-relative addresses:

- The Help module begins at `52FC0h`. `5305Ch`/`53062h` compare the HLP's
  initial word with the running application's configured tag.
- `53093h`–`530B7h` read six bytes at `paragraph * 16 + slot * 6`.
- `530BEh` tests the dimension word against `FFFFh`; missing text reaches the
  “Sorry, no help screen available” path at `530C4h`.
- `530EAh`–`530F8h` test the high offset byte for `FF`, reload the default
  paragraph from `DS:002Dh`, and use the low byte as another context slot.
- `5335Eh`–`53371h` select that same default paragraph for a zero hotspot
  scope byte; every nonzero scope retains the current paragraph.
- `53399h`–`533F8h` isolate each display row and call API `4014h` separately.
  The kernel's printer at `A024h`–`A0BEh` handles raw glyphs and categories.

Executing the original descriptor-reader branch with HLP-backed reads confirms
all three redirects and all six missing descriptors. Varying the injected
default paragraph confirms that redirection is runtime-bound, not an intrinsic
group number. Original printer execution matches all 11,554 source rows across
1,166 pages, including the shared record twice, for both text and category
cells before the VGA handoff. Test attributes distinguish categories, not
actual screen colors. This is not a claim of support for every revision.

---

## Converter mapping and limits

`readers/sidekick_plus.py` detects the header, validates paragraph/relative
offsets, dimensions, record boundaries, hotspot counts/scopes and page numbers.
Malformed structures fail conversion instead of importing a partial stream.
The supported display bounds are 1–25 rows and 1–80 columns; truncated escapes,
unexpected NULs and unresolved runtime-string insertions fail conversion.

The first page receives `(native_group << 8) | context_slot` as its UHF ID.
Continuation IDs start at `1000000h`, outside the complete 24-bit source ID
range. Prev/Next navigation stays within a source context; Contents groups
contexts and lists their continuation pages. Index uses authored captions.
The first available context is the generated entry point, not a claimed
native global Contents screen. Shared records and proven redirects use UHF
`aliases.ids`; alias IDs remain available without fabricated text topics.

Standalone conversion binds the common help group to the first directory
entry, matching the inspected distribution and the previous zero-scope link
mapping. `SidekickPlusReader(..., common_group=<native ID>)` permits a known
runtime binding to another group. This is explicit converter configuration,
not a new source field or a claim that every custom application uses the first
group. No caption or particular product/group ID is hard-coded. Invalid group
bindings fail; missing destinations stay unresolved and cyclic redirects fail.

Ordinary/emphasis/key-label/selected categories map to plain/bold/underlined/
reverse UHF spans. Row boundaries reset the category as in native Help;
tags are balanced on every output row. Hotspots retain all original
targets, including unresolved ones. Fixed-width UHF display metadata supplies
the shared help window's layout; no format-specific JS, CSS or window is added.

Six source links remain unresolved: group/slot `0003h:90`, `0017h:4`,
`0104h:86`, `0114h:166`, `0020h:3`, `0020h:50`. They point to unused
descriptors and the original reader reports missing help, not a neighboring
context. They remain real links rather than being deleted, moved to adjacent
context numbers or given fabricated text. The former seventh target,
`0104h:146`, now resolves through its native alias to Services slot 129.

Optional transport metadata `sidekick_plus_groups` retains directory order;
`sidekick_plus_contexts` records distinct text context IDs, group/slot,
offset, size, dimensions and page IDs; `sidekick_plus_redirects` records each
native `context_id`, `target_context` and the descriptor bytes as a little-endian
integer. `sidekick_plus_common_group` records the selected binding and
`sidekick_plus_version_tag` retains the opaque pairing word.
`unresolved_contexts.links` lists the unresolved numeric destinations.

## HelpPC 2.10

## Verified runtime layout

The distribution's original `HELPPC.COM` is 10,603 bytes with CRC32 `8D6D7C24`.
Its display routine begins at COM address `129Ch` (load address, not file offset):

- `12BBh` distinguishes the `^` control; the TAB and `%` branches select margins
  of 8 and 1. Ordinary text also starts at column 1.
- `12DCh`–`12F0h` computes `floor((80 - strlen(source + 1)) / 2)` for `^`.
  It uses the original byte length after the control character, **before**
  expanding TAB or consuming tilde controls; it does not center the eventual
  visible or UHF-marked-up string.
- `135Eh`–`139Ah` expands TAB according to the current output column modulo 8.
- `13A0h`–`13F6h` handles tilde/link state, including literal `~~` both inside
  and outside a link. An unmatched opening tilde is consumed as a control.
- `1426h` hands the prepared character/attribute row to the screen writer.

Executing this original routine up to the screen handoff confirmed the visible
columns of all **17,742 nonempty display rows** in the six source files,
including **1,075 centered rows** and their **20 TAB-bearing headings**.
This establishes the character layout, not a pixel-exact recreation of its
runtime palette or the separate HelpTSR popup interface.

---

## THelpViewer mapping and limits

`helppc.py` recognizes an `@` title followed by `:` topic lines. Each key
becomes an index entry; database titles become Contents sections. A
single `.TXT` is exported as its own UHF bundle (`ASM.TXT` to `asm.json.gz`,
and likewise for the other five files). Each bundle assigns topic IDs in
source order. The reader indexes sibling HelpPC databases before rendering,
so a cross-database `~key~` becomes a `file=...` link to the correct bundle;
the six original files contain 1,006 topics in total.

Link lookup ignores letter case and compresses repeated spaces in both topic
keys and link labels, matching the original HelpPC key rule; the displayed
spelling and spacing are preserved.

Display lines retain CP437 text and native column positions. `%` and `^` become
UHF highlighted spans after their margin; `^` receives the runtime-verified
80-column centering above. `metadata.display.cols = 80` selects the viewer's
existing fixed-width layout, without format-specific JS/CSS. This display
width is a converter/runtime mapping, not a numeric field stored in the TXT.
The normalized raw lines are also expanded display text, so Markdown and UHF
agree on the same spacing. All **1,786 resolvable inline references** remain
real topic links. References to keys absent from the six available files remain
text rather than being given invented destinations. The original DOS
`HELPPC.NDX` binary is not parsed or regenerated.

Centered source text over 80 bytes is rejected rather than reproducing the
native unsigned-margin underflow. Ordinary text is never silently clipped:
eight verified rows expand to 81–82 columns, and the importer retains that text
for horizontal scrolling even though the original screen renderer clips it.
Native attributes are represented by the existing UHF bold/link categories,
not a claimed reconstruction of configurable native colors.

The downloader selects only the six `.TXT` conversion inputs into
`data/sources/HelpPC 2.10/`. `HELPPC.DOC` and `HELPPC.NDX` remain in the original
downloaded archive; the converter does not use them. These sources are
excluded from the default public build pending a redistribution-rights review.

## DOS BACKUP Source Container

The converter validates the ASCII absolute DOS path, its NUL/length and zero
padding. It supports complete single-volume files: flag `FF`, sequence 1.
Recognized continued/later-volume parts fail instead of being imported as if
they were a whole file. Joining multi-volume backups is not implemented.

---

`converter/readers/source_containers.py` removes a validated header in memory before
format detection and reader loading. This works for any registered inner format,
not only Prolog or these CRCs. Original files and their manifest CRCs stay
unchanged. Transport metadata records `source_container` with format, original
pathname and disk number. No files are written using the embedded pathname.

## DOS Text Help

## Converter behavior

`readers/dos_text.py` / DosTextHelpReader is the final `.HLP` text handler,
after the structural/binary readers. It requires meaningful multiline text
and allows only TAB, CR and LF below byte 32 before the optional EOF marker.
NUL and unexplained binary/control bytes are rejected. It does not scan a
binary for printable strings or declare every unknown `.HLP` readable.

Each physical file becomes one topic with ID 1, a generated Index/Contents,
literal escaped UHF text and CP437 decoding. Blank lines and spaces are kept;
tabs expand to standard eight-column stops. The default display width is 80
columns. Topic ID, title derived from visible text, tab expansion and navigation
are converter presentation choices, not stored format fields.

Files beginning like the separate Prolog `h("…")` database or MicroCalc page
format are not silently downgraded to plain text if their own parsing fails.

---

## Limits

This handler is for uncompiled DOS display text with the stated byte grammar.
It is not a general Prolog interpreter, a colored terminal emulator, an RTF
decoder or a fallback for Sidekick/TDH binaries. Other encodings or control
grammars need evidence and the appropriate reader.

## MicroCalc Text Help

## Converter behavior and limits

`readers/dos_text.py` / MicroCalcReader detects the page directives and permitted
text/control bytes. It emits one topic per page, ordinal IDs starting at 1,
synthetic Contents/Index and previous/next page navigation. Those IDs and trees
are converter presentation, not fields stored in the original file.
UHF color spans preserve the runtime's state transitions and five-space margin.
The default display width is 80 columns. Binary/NUL data and other unsupported
controls are rejected; they are not stripped to manufacture readable text.

## Turbo Prolog Help Database

The converter also accepts an optional final period on a clause and the simple
string escapes `\r`, `\t`, `\"` and `\\`. Only newline escapes occur in the
current original; these additional escape cases are covered by synthetic tests,
not evidence that every historical Prolog string grammar is implemented.
Unescaped text uses CP437; the present example is ASCII-only.

---

## Conversion and limits

`readers/dos_text.py` / PrologHelpReader validates the entire sequence, expands
supported escapes without executing code, and emits one topic per record.
IDs start at 1 in record order; first visible lines supply Index labels and
generated Contents entries. These are presentation choices, not original fields.
Literal UHF brackets are escaped. TAB is expanded to eight-column stops.

Unknown escapes, malformed strings, other predicates and trailing executable
source are rejected instead of being omitted or evaluated. A malformed `h(`
database does not fall through to the plain-text HELP handler. This is a small
help-database grammar, not a general Turbo Prolog parser.

## FreeDOS HTML Help

The current importer emits
a replacement character there; no alternate encoding or intended character
has been verified, so it must not silently guess or rewrite the original.

---

## THelpViewer mapping

`freedos_html.py` recognizes a ZIP named `HHSTNDRD.ZIP` with a ZIP
signature and a `help/index.htm` member. It reads entries in memory
without extracting files. Each HTML page becomes one UHF topic. Page
`<title>` text becomes its index label, parent directories become
Contents groups, and sorted member paths determine stable numeric topic
IDs. `help/index.htm` is marked as the help-contents topic.

Relative page links are normalized against the current page and become
UHF links when the destination member exists. The observed English
archive yields **4,132 actual links** to existing topic IDs. The prior count
of 4,286 included all 154 named destinations as spurious self-links.
Its 22 links to
the absent root `index.htm` remain plain text rather than being pointed
at an invented topic.

The importer first records bookmark positions for every page, then renders
the links. `#fragment` becomes the existing UHF `topic=…,line=…` target,
including forward links, same-page jumps and links to another page. All 112
fragment references whose destination member exists resolve to bookmark
lines; the other four refer to the absent root page. No new JS/CSS navigation
is needed. For example, `base/debug.htm#progexec` targets its emitted line 117,
which begins the Program Execution section.

Paths are normalized case-insensitively for the DOS archive; fragment names
are percent-decoded once and matched exactly. The importer also accepts HTML
`id` destinations, though this corpus uses `a name`. Duplicate definitions use
the first matching destination; IDs take precedence over same-named anchors.
Bookmarks between blocks target the next text row after blank-line compaction,
and terminal bookmarks use the last emitted row. A missing fragment retains
the real page link without inventing a line; an empty page has no line target.
Head/script/style attributes are not display destinations.

The importer preserves preformatted text, headings, paragraphs, basic
bold emphasis and table-cell text. Inline bold/link state persists across
source line breaks and blocks, but each emitted UHF display row closes and
reopens its active tags so `[/b]`/`[/link]` do not become visible text.
Markup-only rows are not treated as article text. It is not a full browser: CSS,
images and scripts are not rendered. The reader rejects case-colliding HTML
member paths rather than silently merging topics, and enforces page-count and
uncompressed-size limits as a safety measure;
those are THelpViewer limits, not properties of the FreeDOS format.

### Flowing text word boundaries (2026-10-12)

The importer previously normalized each HTML text callback independently and
discarded its trailing space. Inline tags then joined separate words, including
the original `help/memman.htm` heading `DOS <a name="ext">Extenders</a>:`.
The shared page parser now defers a separator at its original markup position
until more visible text arrives. Block/preformatted transitions reset that
pending separator; no new JS/CSS or page-specific replacement is involved.
Only ordinary text spaces/tabs/source line breaks collapse. NBSP, other
Unicode space separators and noncollapsible controls remain literal text.

The original archive's conversion changes one row: topic 185, row 99 now reads
`DOS Extenders:`. All 354 article IDs/titles, index/Contents, 4,132 outgoing
links and 112 fragment destinations retain their identity. The malformed byte
in `authors/ack.htm` remains an explicit replacement glyph, not a guessed
character. Synthetic tests cover empty anchors/comments, crossed style/link
boundaries, pending-space reset, non-breaking/Unicode spaces and one-character
parser input chunks. A separate headless Chrome comparison checks actual
flowing text without relying on our formatter. Its initial form-feed case
showed that HTML lexical whitespace is not the same as text-flow whitespace;
the decoder preserves that control rather than collapsing it. This is text
projection verification, not emulation of every native DOS HTMLHELP feature.

The final reference/download/catalog/export regression run reports 67 passes,
including the real Chrome comparison. Docker Python 3.12.15 independently
loads the original archive and confirms the corrected row. Staged publication
keeps all 253 bundle paths, all 495 source hashes and the 252 unselected bundles
byte-identical, including every Windows HLP. Full selected payload equality
holds after removing the converter timestamp and restoring that one heading
for comparison. The previous publication is recoverable at
`data/.helps-previous-072cf68784d346cba0b02b03e39b1f51/`. Live bundle/public Docs
bytes match the updated files. No commit or production deployment was made.

---

The known archive has CRC32 `3F1A2C97` in
`thelpviewer/config/help-database.json`. `FDL.TXT` and `COPYING` are kept
with the downloaded package as license materials, not imported as help
topics. The selected FreeDOS package lists an
[Express + GNU Free Documentation License copying policy](https://ibiblio.org/pub/micro/pc-stuff/freedos/files/repositories/latest/html/en/base/htmlhelp/20251203.4/index.html).
This product remains outside the default public build until its
redistribution obligations and included notices are reviewed.

## TurboVision FBHF

### TVHC source grammar verification (2026-10-11)

The source-reader pass checks the original Pascal `TVHC.PAS` functions
`GetLine`, `GetWord`, `TopicHeader`, `TopicDefinitionList`, `ReadParagraph`,
`ScanForCrossRefs`, `RecordReference` and `ResolveReference`, plus
`THelpIndex.Add` in `HELPFILE.PAS`. The native `.TOPIC` command is uppercased
independently of the predefined APP-name table; token whitespace is 20h/08h.
Symbol keys use ASCII uppercase, not Unicode folding. Duplicate symbols
are errors, whereas distinct symbols reusing a number update the context's
indexed position. The importer now keeps surviving aliases of an old object
and transfers earlier symbolic names to that number's current owner.

The compiler's mutable brace scanner differs from a fresh input/output scan
for consecutive opening braces. Removing the second brace then advancing
the cursor leaves `{{{A}` as literal `{{A}`, but `{{{{A}` becomes two literal
braces followed by an `A` reference at column 3. The closing brace is located
on the same physical line; absence is a fatal source error. The source-reader
limits protect the 253-byte GetLine input, 4096-byte paragraph buffer and
signed count/reference-position fields instead of reproducing unsafe native
truncation, misalignment or overflow. A standalone 1Ah is a sentinel; the
native `IsEndParagraph` checks `Line = #26`, not its first byte. Literal
arrows at the start of longer lines must survive.

Unresolved symbol fixups leave FFFFh in the native stream and print one
warning per case-folded symbol. The importer retains that positioned target
and exports `unresolved_topic_names`, preserving first spelling; a real FFFFh
topic remains the numeric destination if present. Writers do not guess a
different topic from visible label text. Malformed sources abort the staged
server build, keeping published HELP/catalog; corrected sources can retry.

The complete source/reference pair is:

- `TVisionJS/references/turbovision-delphi/Demos/Demohelp.txt`: 18,780 bytes,
  SHA-256 `62cbe3bab97c16cf3f28a51dc489cb487dfd104d86d9cd5ba8d01e741192c99b`.
- `HelpTools/samples/DEMOHELP_BP7.HLP`: 18,749 bytes,
  SHA-256 `2cb9bc120644d7b83b2a6b1efd146c4ee35d8cf437d2b77dde779e933feadd35`.

All 55 source objects, paragraph bytes, 47 references, physical object
positions, sorted context IDs, the 60-slot index and full header reproduce
the existing binary **byte for byte**, without running a native compiler or
changing that original. UHF content from source and binary is identical.
The comparison script is `/tmp/thelp-tvhc.X7B7jC/compare.py`. A permanent
optional reference-pair test pins both inputs and exact reconstruction;
small grammar/bounds/replacement/rollback fixtures run without external files.

Automatic source selection checks the first nonblank/noncomment line, not
an arbitrary later occurrence of `.topic`. A synthetic HelpPC file starting
with `@Example`, then a key and a `.topic` code example, formerly selected
the FBHF reader and is now correctly routed to HelpPC. This is a grammar
boundary check shared by all source callers, not a filename/catalog exception.
An explicitly selected TVHC reader can still parse empty/comment-only native
source without requiring a decompiler banner.

The Magiblot C++ demo source is a related but different text revision:
15,577 bytes, SHA-256
`5bb2621a2adffda9e32b3d8d7225fc298589aa75ca7ca44ebe6974c8193cca33`.
Its 39 topics and all 40 reference fields agree with the TP6 demo, but five
texts use different capitalization of Puzzle/Calendar/Calculator and
`TVDEMO.DST` rather than `TVDEMO.DSK`. Those are real source differences,
not decoder failures. Neither reference source was added as a new installed
product or given invented release/provenance metadata.

### Native paragraph layout verification (2026-10-11)

The earlier structural-validation pass below deliberately retained the old
flattening output. A separate layout audit now checks `THelpTopic.WrapText`,
`GetCrossRef`, `THelpViewer.Init/ChangeBounds` and `THelpWindow.Init` in
`HelpTools/pascal/compiler/HELPFILE.PAS` (Borland 1992).
The 50×18 window shrinks its viewer by `(2,1)` on each side, giving an initial
46×16 client. Wrapping at 78, treating stored physical paragraphs as one line
or normalizing FF before selecting breaks does not reproduce that viewer.

The same byte-based WrapText/GetCrossRef logic already established in the
Text602 executable was invoked with the **unencoded** FBHF paragraph bytes
and width 46, without starting the application or using DOS/system I/O. The
existing bounded Unicorn harness in `/tmp/thelp-text602.McOLPF/layout.py`
supplies the proof; the comparison script is `/tmp/thelp-fbhf.sFC3hO/verify.py`.
The following SHA-256 values pin the inputs and native results:

| Sample | Input SHA-256 | Native rows / cells / references |
|---|---|---|
| `DEMOHELP.HLP` | `84eb6628aa9b8967156989c5bf0dfbe78a1aefee4531acd98c25bbcff3f254e1` | 483 / 13,725 / 40 |
| `DEMOHELP_BP7.HLP` | `2cb9bc120644d7b83b2a6b1efd146c4ee35d8cf437d2b77dde779e933feadd35` | 592 / 16,981 / 47 |

Compact JSON `[context, [[global_start, consumed_end, raw_row_hex], ...]]`
digests, before FF normalization:

- TP6: `6eb9254f87b17a99a8fc4f52621b62b6070b07e284f9865ab3097d908b9f8095`.
- BP7: `4e133acc15fb16ce354840bfad28db3967be62185469147622646c3273928c7d`.

Native reference-location `[context, [[target, x, y, length], ...]]` digests:

- TP6: `eb60191e449bb92d1e992004800b54961cae072eb74c63793ce0c20511ed44f8`.
- BP7: `b76aed3cd5bc0872a13e97cbd67c4409404d3627570da1f850043f0231ddac12`.

The former raw export had only 405/479 rows, including fabricated terminal
blanks and single wrapped rows of 394/404 bytes. The corrected export matches
every native visible row after readable FF-to-space normalization and all
87 stored reference locations/labels. Existing shared PositionedKeyword
ranges retain links even for exceptional spans crossing rows; that splitting
is deliberate converter behavior, not native GetCrossRef semantics. Native
draw colors only the row containing a reference start. UHF remains a frozen
46-column projection and does not rewrap native paragraphs when resized.

### Earlier structural validation

Validation evidence: local `HelpTools/samples/DEMOHELP.HLP` is the dense-index
sample (15,014 bytes, 39 contexts, 40 hotspots) and `DEMOHELP_BP7.HLP` the
sorted-index sample (18,749 bytes, 55 contexts, 47 hotspots). Their complete
normalized models are unchanged by strict record validation. They are not
installed products in the current public catalog. Additional malformed/alias
fixtures are generated from the serialization layout, not copied into the
original HELP library.

The 1992 Borland `HELPFILE.PAS` and `TVHC.PAS` in the local HelpTools compiler
and OldTurboVision reference tree establish signed counts, five-byte
references, shared positions and predefined APP contexts. A source `.topic`
line assigns a separate numeric context to each name; the converter emits one
owning topic and retains other contexts as aliases. Source references resolve
to the primary context, while genuine binary shared-position contexts remain
readable. A global reference split by paragraph/CR flattening becomes separate
balanced UHF links with the same destination, without discarding its text.

#### Converter cross-reference reconstruction

The binary and textual readers resolve every cross-reference target through
the complete case-insensitive topic-name map before rendering. The stored
1-based global byte range is projected into native-layout rows and preserved
as real UHF links; it must not be discarded while converting paragraphs into
display lines.

Inside the linked range, `$FF` is rendered as a normal space. This preserves
the visible label; native word-wrap protection is applied before that
normalization. The resulting UHF rows are fixed, not dynamically reflowed.

## Microsoft BW03 Help

### Original-reader evidence

The Microsoft C 5.10 DOS/OS2 distribution at PCjs provides `CV.EXE` (232,896
bytes, MD5 `e95601011699466f65de9f1a4c4aa5d9`) on
`https://miscdisks.pcjs.org/pcx86/lang/microsoft/c/5.10-os2/MSC510-DISK10-CVDOS.json`.
Sector reconstruction and FAT-chain extraction were read-only/in-memory and
verified against the distribution's file hash. The resident EXEPACK wrapper
was run with a bounded Unicorn instruction count only until its final jump;
the application itself was not launched. Unicorn/Capstone are research tools,
not converter dependencies.

The following are disassembly observations, not a claim of a full native
screen-rendering comparison. Resident addresses are offsets in the unpacked
load module; overlay addresses are offsets in the original executable:

- Resident `15D9Bh`–`15E88h` reads the header counts, 22-byte menu records,
  exactly 48 style bytes and `ScreenCount * 12` descriptor bytes. It does not
  require all 40 allocated slots to be stored before seeking a payload.
- Resident `13D0Dh`–`13D29h` selects navigation from descriptor words at
  `+0`/`+2` (`DS:76A2h`/`76A4h`), proving Next/Prev rather than screen number.
- Overlay 4 `3054Ch` starts color attribute 07h; `30666h`–`306E9h` expands
  each FF repeat by calling the direct character-cell writer, without parsing
  its operand as a control. `305D7h`/`30662h` ends at standalone NUL.
- Overlay 4 `30701h`–`30729h` searches 16 style triplets and selects the first
  or second attribute using the display-mode flag. This also establishes that
  physical triplet order is not the identifier.
- Overlay 4 `30497h`–`304DFh` seeks to the final active descriptor's
  offset+length; `30501h`–`3053Bh` prints the separate short-help block until
  NUL, skips CR and pauses at form-feed. It does not invoke screen RLE/styles.

### Validation and conversion

Three installed originals contain 68 indexed screens. Full normalized-model
baselines for those indexed screens, metadata, original index and original
Contents remain unchanged by the validation/control fixes. The only content
addition is each source's native command summary (1806 / 1706 / 1706 bytes,
including its terminator). The public library deduplicates identical 5.1
CV.HLP/CVP.HLP, so it gains two summary topics, not three duplicate bundles.

The 2026-10-13 regression run confirms all three historical model digests
still match exactly. The shared `TopicRecord.alias_lines` field introduced
for native article cursors is empty on every BW03 topic, including the
summary; the baseline test asserts that before comparing the original
fields. It does not replace expected digests or change decoded content.

Summary titles and IDs after the indexed-screen range are converter choices.
Form-feed pages reuse shared Prev/Next navigation and appear in Contents/Index;
no BW03-specific JS/window/control is needed. Other unverified summary console
controls fail explicitly rather than being flattened into guessed glyphs.
Without a stored file size/checksum, removing an entire unindexed suffix is
indistinguishable from a file containing only indexed screens. Inactive slots
and data after the first NUL are not invented as another screen or summary.
Corruption fixtures include all descriptor ranges, incomplete repeat operands,
compact/native circular tables, unordered/shared menu entries and staged
publication rollback/retry using a damaged copy of a real CV.HLP.

The converter exports inline BW03 styles to UHF using the first attribute byte,
split into DOS `fg/bg` nibbles and resolved through the standard UHF `cga`
palette. The second byte is preserved as additional palette metadata under a
`bw03-mono` palette.

---

For richer UHF export the converter may instead keep the inline style runs and
emit them as UHF `[color:fg:bg]...[/color]` spans using the decoded DOS
attributes.

---

The converter reader uses this footer to derive:

- `topic.names[]`
- page numbering for multi-screen categories
- category-local `Up` / `Down` navigation
- UHF `contents[]` entries reconstructed from the BW03 menu table
- optional viewer app-bar menu items reconstructed from the same BW03 menu table

## Microsoft QuickHelp

Strict-decoding verification covers all 28 installed LN originals, comprising
35 logical databases and 10,190 topics. The complete normalized models before
and after validation/demand-driven decoding have identical hashes, not merely
equal topic counts. The original format specification and every inspected
topic agree that TextBlockLen/AttrBlockLen are positive and OUTLEN ends the
binary stream; the former datasheet's NUL-termination statement and synthetic
container fixture were incorrect. No original bytes were changed. Corruption
fixtures test each section/index/compression/record layer and staged build
rollback/retry against a damaged copy of the real QA.HLP placeholder.

All 65,224 parsed visible-line link records have valid direct topic indices.
Seven original CLANG.HLP ranges end one byte beyond their line: topic 750 rows
64/86 (`_COM_RECEIVE`, `ctime`), 754 row 56 (`_grstatus`), 760 rows 47/49
(`modf`, `modfl`), 766 row 51 (`_setvieworg`), 1029 row 20 (`isalnum`). Their
targets are retained; the shared UHF renderer bounds spans to the visible
text. Do not reject this whole original or apply a global coordinate shift.

Converter behavior: one physical file remains one UHF bundle at its existing
path. IDs of the first database stay unchanged; later IDs add the topic counts
of preceding databases. Local links, category navigation and index targets use
the same mapping. Additional Contents sections expose every database.
`quickhelp_databases` metadata records names, byte offsets/sizes, topic ranges
and case-sensitivity. Qualified `DatabaseName!context` aliases keep namespaces
distinct, and catalog `source_files` includes verified logical database names.
The former first-database-only reader omitted 378 topics in these four files.

A truncated header, invalid size or non-database trailing data now fails
conversion instead of silently discarding the remainder.

---

**Implementation note:** the reader extracts `:n`, `:l`, `:c`, `:i`, and `:g`
into topic names, frozen-row count, category navigation, list state, and popup
state respectively. Other command lines remain invisible and are filtered from
`raw_lines`.

---

If an explicit filename is absent but its context exists in exactly one
sibling database, the converter uses that database. This repairs the original
`QB45QCK.HLP` reference to `AB45ADVR.HLP!.erasex`: the actual file on the
Advisor disk is `QB45ADVR.HLP`. Ambiguous contexts retain their original
external target rather than guessing. A duplicated qualifier such as
`qb45advr.hlp!qb45advr.hlp!.vupri` is reduced to its actual context only
when both filenames agree.
When the named database exists but lacks that context, the reader does not
substitute a context from another database. It preserves a qualified unresolved
alias so a merged container cannot accidentally resolve it in another namespace.
Context indices are cached by path, modification time and size, not just path.

---

over the **raw text bytes including these markers**.  Our reader:

1. Keeps the markers visible in UHF output as `◄` / `►`.
2. Strips them only from stored `raw_lines`, so title/index heuristics do not
   see decorative tab markers.
3. Leaves link column positions in raw-byte coordinates, because the visible
   UHF line still contains one character per marker.

---

Topic titles come from `:n` command lines, stored in `topic.names[]`.

When no `:n` command is present, the first non-empty `raw_line` (stripped of
leading/trailing whitespace) is used as the human-readable index label.
Context strings (e.g. `h.pg1`, `.cccp`) are internal identifiers used only
as a last resort.

---

UHF exposes the combined index of the physical file containing that database.

---

The converter preserves this as a UHF link containing the source filename and
alias. If the physical or logical sibling database is present, it also stores
the resolved topic id:

```text
[link:file=CV.HLP,topic=90,alias=cv.contents]...[/link]
```

If the explicitly named file is absent, the link remains real and keeps
`file=CV.HLP,alias=cv.contents`; it is not downgraded to plain text. It starts
working automatically when a matching bundle is later added to the catalog.

A bare unresolved alias is searched across sibling `.HLP` files and becomes an
external link only when exactly one file matches. Ambiguous bare aliases stay
plain because the source format does not identify which database was intended.

The QuickBASIC 4.5 distribution has `QB45QCK.HLP` on the Program disk,
`QB45ADVR.HLP` on the Advisor disk, and `QB45ENER.HLP` on a Utilities disk.
Converting only the first leaves hundreds of valid cross-file links without
their targets. The tiny QuickC 2.50 `QA.HLP` (445 bytes, two contexts,
including `taw080554`) explicitly says it is a null search-order context;
it is an original placeholder, not a damaged help database.

At display time, duplicate filenames such as `CV.HLP`, `PWB.HLP`, `LINK.HLP`,
or `UTILERR.HLP` are resolved in this order:

1. same catalog collection/group as the current help file;
2. same product and version;
3. if still ambiguous, fail instead of selecting another product/version.

A unique verified filename match works without a preferred collection. Bundle
paths and verified source/database names must match exactly (ignoring DOS
filename case); no stem-only names or obsolete-URL aliases are accepted.

Original filename extensions are significant: `MISC.HLP` cannot match HelpPC's
`MISC.TXT` merely because both export to `misc.json.gz`. Logical names such as
`NMAKE.HLP` resolve through the verified `source_files` aliases of `UTILS.HLP`.
An explicit missing file/context returns failure; the viewer does not replace
it with an arbitrary first topic or infer Contents from a similar alias name.
The defined `!HV`/`!VX` and `-9996`/`-9997` navigation commands remain valid.
The reader and viewer honor case-sensitive context strings while DOS database
name qualifiers remain case-insensitive.

## Borland THELP

### Bounded records and long format-4 headers (2026-10-11)

Re-read the primary Borland BOA binary chapter and `DEHELP.C` in archived
`BC4BOA.ZIP`, obtained from
[this preserved package](https://dose.0wnz.at/Shareware/Pegasus-5.0/TEXTE/BC4BOA.ZIP).
Its record length excludes the three-byte record header, Context count
requires `2 + 3*N` bytes, compression defines only type 2, Index carryover
counts prefix bytes and Text is loaded by its own declared size. Source
code confirms that text is buffered per record, not read from the following
Keyword record. Treating physical truncation as arbitrary trailing bytes
is not a binary grammar rule. The public datasheet now describes boundaries
and the verified all-space terminal extension separately.

Research artifact SHA256: package
`d52ec11e82a4d46b099fdbfe6d592ab360070b5f390408c0eb88177ab91e0594`,
`BOA.TXT` `8e235e83d1477b62dd369cde72da747021a55bdbc764f2158b09ca8a46d4971d`,
`DEHELP.C` `74879b627a93f46e79b7658b7b6b60f9ac834b9780c0cb6c791aea4e75ccc88d`.
The archived source/executables were not installed as HELP or run on the host.

All 66 installed THELP originals were independently snapshotted before the
changes. Physical records: 66 FileHeader, 63 separate Compression (the three
format-2 headers have inline tables), 66 Context, 66 Index, 21 IndexTags,
93,142 Text and 93,139 Keyword. Normalized output has 93,032 topics,
85,484 index entries, 41,537 positioned and 369,218 sequential keyword targets.
All 5,408 tag length bytes equal the number of bytes before their bounded NUL.
Context table sizes equal `2 + 3*N` in all originals. Three German Pascal 6
copies have complete space tails of 93,187/96,388/96,388 bytes. No installed
record needs to read beyond its own declared boundary.

The tables contain 98,459 ordinary in-file addresses and 18,500 native
`FFFFFFh`/`FFFFFEh` sentinels, with no zero or out-of-file offsets. A context
offset outside the file now fails even when truncation ends neatly on a
record boundary; no extra negative/sentinel aliases are assumed.

Six copies of two format-4/1 TCHELP editions have nine-byte FileHeaders.
Their bytes are `04 00 64 00 97 01 0F 32 02` or
`04 00 64 00 99 01 0F 32 02`. The old five-byte interpretation mistook
context 100 for height, width zero and maximum-size low byte 151/153 for
left margin, then guessed width 80 and margin 2. The actual fields are
Contents 100, maximum compressed screen 407/409, height 15, width 50 and
margin 2. The corrected field selection also interprets context-zero's
`FFFFFFh` as its genuine source Contents alias. This is not an alias retained
for a former export ID.

Hash each source and compact sorted-key UTF-8 `document.to_dict()` model
(`ensure_ascii=False`); then hash the sorted filename-to-SHA256 dictionaries:

```text
sources aggregate:
a954f9228d530acfae475c91590247e4554c818a3873e26843aa578aaab0a0b0
models before bounded/header pass:
b2f49226ab02f19c170413930d1dd70b0ffdc22b6c990e8498f94d6491ffb762
models after corrected long headers:
d37286aca4bbc76832cdd46069a8cd307f80ed16594bdd7d8026ea029491ea44
```

For the six changed copies, compare every topic/row/keyword/index field
against the unedited reader: only header metadata and context-100's `[0]`
alias change. Substitute only those six new fingerprints into the old
dictionary; its aggregate equals the all-originals new aggregate above,
proving that the other 60 complete models are identical. Source bytes,
context IDs, raw text, code projection and all keyword/index target identities
remain unchanged. Malformed fixtures cover record-local tables/strings,
incomplete nibble operands, bad prefix/tag lengths and explicit unknown codes;
staged failures preserve all published bytes and retry after input repair.

This was a structural/header audit, not a claim that every THELP rendering
rule is runtime-verified. It identified last high-nibble handling for the
separate text pass below: the old loop tracked fetched bytes rather than
consumption of both halves of the last byte. A direct stream census found
17,394 no-EOT and 75,257 explicit-EOT records in the earlier reference corpus;
do not assume an EOT exists in every historical Text record or silently
borrow bytes from its neighbor. Inline marker semantics, code heuristics,
flat-table restoration and orphan target inference also require their own
original-runtime comparisons. None was rewritten in this bounded pass.

Selective publication rebuilds the five TC product bundles while preserving
all unselected bytes and every catalog path/group/order. Two outputs correct
format-4 geometry/Contents/alias metadata. Two others refresh edition titles
already recorded in the CRC database (`Turbo C++ 1.01 Help` and
`Turbo C++ 3.0 Help`); their old published generic names were stale. All five
now identify the current converter version instead of the old `1.0.0`;
generation timestamp/version changes are separate from content comparisons.
Every published topic ID and visible content row stays identical. The prior
complete library is retained in the normal recoverable backup.

### Complete final byte and bounded nibble grammar (2026-10-11)

`DEHELP.C`'s `getNibble()` leaves `pCurr` on the current byte after its low
half and advances it only after the high half. Its loop therefore processes
both halves of the last physical byte. Our old decoder decremented its byte
counter when fetching the low half, then stopped before a pending upper
opcode. No filename, release or topic-specific exception is involved in the
fix: continue while either an unread byte or a pending high half exists.

Compile the archived `getNibble()`/`getByte()` functions into a small host C
capture harness, retaining their bit-fetch logic. The harness bounds operands
to the supplied Text payload, captures literal-byte events separately from
table-zero newline events, rejects undefined repeat-character `Eh`, and
stops at the first non-repeated raw `01h` for comparison with our logical
EOT projection. This is not execution of a downloaded DOS program, a full
DEHELP source-formatting run or a native viewer screen capture. DEHELP's
original `__put` suppresses SOH and continues its physical buffer; do not
claim that its complete formatted output was compared.

All 66 installed originals contain 93,142 physical Text records: 75,748 have
an explicit logical EOT and 17,394 do not. Captured event prefixes contain
66,307,522 events including the 75,748 EOT events. No literal NUL or repeated
raw SOH occurs in these originals; their viewer meaning is not established
by this corpus. Every current decoded row matches the C capture projection.

Compared with the previous text method under the already-corrected header
parser, 3,001 records in 24 original copies differ: 2,998 regain their last
character and three have an additional row. The latter are terminal Text
records in the German Pascal 6 copies with valid compressed `20h` bytes
(newline, table entry 2), not bytes outside a record's declared extent.
Do not hide them using a padding heuristic. Administrative metadata,
context IDs/aliases, page links, positioned/sequential keyword records,
index and tags stay identical.

Pascal 4 context 34 ends with `Compile  Options`, context 5 with `version
screen`, context 10 with `Quit`, and context 183 with `SPtr`. That final
word occupies columns 1–4 of line 13 and still targets native context 466;
the exported link now includes all four characters.

Fingerprint each physical Text record as compact ASCII JSON plus LF, in
sorted source-relative path and physical record order. Hash tuples
`(name, record_offset, events)` after removing the logical EOT; newline is
event 256, literal bytes are 0–255. For rows use tuples
`(name, record_offset, [row.hex(), ...])`. Independent reference hashes:

```text
compression-event prefixes:
bf77958629b2d74f330da7f0431d4ef55efb48e897581ea700e19d0ce9782800
decoded rows:
93677d27d3455b126291dc711aab7bdb33d29598e68becc0e17887cc4de7057e
complete models after the text fix (same algorithm as above):
b9d9e5dca21d6a674324d4f780fc8f2b2f1f90a3e399b8ec8c17b56274b97a6e
```

Fixtures cover final low/high codes without an EOT, all non-EOT raw byte
values in both alignments, every lookup/repeat-count combination, NUL table
entries, malformed final opcodes with a complete neighboring record, early
EOT/physical boundary separation, page completion, full positioned link
labels and staged publication failure/retry. The corpus fingerprints are
reference results, not an alternative decoder embedded into production.
Inline marker/style semantics, code heuristics, table reconstruction and
hidden-anchor inference were not changed or claimed runtime-verified here.

Selective publication rebuilds 26 bundles of products `tp`, `tc` and `sk`.
Nine canonical bundles change visible text in 1,006 topics after existing
CRC duplicate selection; 24 source copies do not mean 24 different menu
entries. Every original THELP source, all unselected library files and the
complete 251-entry catalog (paths, names, counts, product/release grouping
and order) remain unchanged. Published topic IDs, aliases, navigation,
Contents/index entries and inline link target order are identical.
The preceding library remains in the normal recoverable backup.

### Native Turbo Example controls and literal OEM arrows (2026-10-11)

BOA's Borland Help chapter, Wordwrap/Turbo Example section, explicitly
defines `^E` (`05h`) around example text and permits an example to span
contexts joined through native Up/Down links. It does not define `03h` or
`10h` as example delimiters. The old projection treated all three as
interchangeable start-of-row toggles, collapsed a run of multiple markers
to one toggle, removed whole marker-only rows, stripped indentation before
an opening marker, and left inline closing markers as visible `♣` glyphs.

The full decompressed corpus contains 17,223 `05h` occurrences in 31
original copies: 15,428 marker-only rows, 1,744 prefix rows and 38 inline
rows; 13 rows contain two markers. There are no `03h` bytes. Its 236 `10h`
bytes occur in 22 originals, mainly as drawn scrollbar triangles paired
with `11h` left triangles. Czech Pascal context 434 begins a menu-table
row with `20 20 20 20 10 20 20 20 20 B3`; the old projection removed its
arrow/indentation and incorrectly marked all following rows as code.
Context 1327's `10 05` ending alone is not evidence of a composite end
opcode; retain the triangle and independently process its `05h`.

For example, C++ 2.0 `puts` context 1388 opens with
`20 05 23 69 6E 63 6C 75 64 65 ...` and ends with `20 7D 20 05`.
Both spaces around the closing brace are source text. Preserve all
decompressed row boundaries while removing each `05h` byte; the closing
brace is still inside the example. `05 05` changes state twice, not once.
No file/topic-specific rendering exception is used.

An independent C reference implements the documented byte-toggle rule,
emitting every other byte and recording whether a row contains example
text (or is blank with the exit state active). It is a new reference
derived from BOA, not original compiled Borland viewer code or a DOS GUI
capture. Every one of 2,212,161 rows in 93,142 Text records matches its
visible bytes and whole-row projection, including 201,770 native code
rows. The installed corpus has no actual example spanning page links;
out-of-order continuations, aliases, ending state, zero/missing/conflicting
links, cycles and a 2,000-page chain are tested using synthetic records.
Only reciprocal, nonzero native page links supply an entering state;
ambiguous cycles do not acquire a guessed state. The byte rule itself is
not a claim that mixed normal/code spans in one row are represented with
per-cell attributes: the shared model remains whole-row code metadata.

Compare with the exact preceding normalization methods while retaining
the already-corrected nibble/header parser. All original hashes and native
topic/alias/page/positioned/sequential/index identities remain unchanged.
31 source copies change 8,281 topics' visible rows/rendered content and
6,626 topics' code-row sets. Lossless raw Text decoding still has the
previous nibble reference fingerprint. Use the earlier model hashing
algorithm; the preceding aggregate equals the recorded nibble-pass
aggregate, not a newly invented baseline:

```text
models before example projection:
b9d9e5dca21d6a674324d4f780fc8f2b2f1f90a3e399b8ec8c17b56274b97a6e
models after example projection:
b8a0254286ffee86a91a24a2e97a45cfe9482fa67cbd05b69d601f9aa1c1656b
independent visible-row/code reference:
743ec4c968003e0f25c55d6784032fe72a6dcbbd79f22cffc471f8e7e6c51228
```

For the last fingerprint, hash compact ASCII JSON plus LF tuples
`(source_relative_name, physical_Text_ordinal, [visible_row.hex(), ...],
sorted_native_code_row_indices)` in sorted path/physical order. The
ordinal and code-row indices are zero-based. Independent source field
targets retain their identity even when derived fallback line positions
move to the restored visible rows. Explicit markers supersede display
heuristics; unmarked legacy examples keep the existing optional heuristic.
Paired `14h` stripping, reflow/table restoration and hidden-anchor inference
were not rewritten or claimed original-runtime-verified by this pass.

Publication rebuilt 55 canonical bundles belonging to `bc`, `bp`, `tc`
and `tp`, retaining every other manifest product. Twenty bundles change
rendered content in 6,044 topics after source deduplication; five existing
C++ CRC manifest titles also replace stale generic catalog names, including
one title-only bundle. Thus 21 payloads differ beyond converter timestamp/
version. All 66 THELP source copies and 197 unselected library files remain
byte-identical. The 251 catalog path/product/release/source identities and
topic IDs, aliases, page/navigation, Contents, index and inline link target
order are unchanged; no index row adjustment was necessary. Title updates
match the existing CRC entries, with sorting following the current catalog
rule. The complete previous library is recoverable at
`data/.helps-previous-745a40b52d42477499f291f82b6c652c/`.

The complete test suite reports 1,579 passing tests and one skipped Safari
test; this is not a native DOS display verification. Repository bytecode
and test caches were absent after the test run. Public documentation and
representative bundle downloads match the published files byte for byte.
The restarted local Docker server also passes native-source/bundle/HTTP
checks under Python 3.12.15. Its rebuilt global index is ready at 100%,
with 146,906 topics, 35 documents and no warnings. These checks do not
exercise Safari rendering or deploy the change to the public server.

### Native Pascal 7 product-name substitution (2026-10-11)

The original TP7 decode routine at file offsets `468FDh..469C9h` in
`TURBO.EXE` (`0951BC69`, 403,655 bytes) tests `AL == 14h` before
`STOSB`/`REP STOSB`. It toggles a record-local suppression bit and on
opening copies the Pascal short string at `DS:2116h`, whose normal value
is `Turbo`. The BP7 routine at `403A7h..4046Fh` in `BP.EXE`
(`E635651A`, 498,961 bytes) has the same logic with string `Borland`
at `DS:2A5Eh`. It uses a near call/return and an ENTER frame rather than
the Turbo routine's far call, but the nibble/substitution body agrees.

Artifacts and provenance:

- [TP7 archive](https://archive.org/details/tp_20240418), download
  `TP.zip`, exact members `BIN/TURBO.EXE`, `BIN/TURBO.TPH` and
  `BIN/TVISION.TPH`. Its two HELP CRCs `CBC21976`/`CBB75BF0` match
  already-installed originals; no duplicate edition is added.
- [Borland Pascal installation disks](https://archive.org/details/borland-pascal-with-objects-7.0-and-bonus-disk),
  download `Borland Pascal with Objects 7.0.zip`, member
  `Borland Pascal with Objects 7.0 Disk 8 WinImage9.IMA`, then
  `BP.ZIP/BP.EXE` and `TURBO.ZIP/TURBO.EXE`. Its Turbo executable
  is identical to the TP7 archive's executable.

```text
TURBO.EXE SHA256:
818e01a4cee4df09abe34562629bcfa99e63656c02bb46214bb63c8eae6ffb75
BP.EXE SHA256:
438f04b782a92b2b162f7af363df87a76f1b99534ea94537905450e0c5060ed4
TP.zip SHA256:
b9e71fcdb0cb5c2932e20e8eed254c643fe4de71fa5118868e61e8448743fc45
Borland Pascal with Objects 7.0.zip SHA256:
01966c0bb1b923d798edf37180a7266459107c708bf4d8e39c90cc5272e22786
```

These two downloadable archives are cached under `var/downloads/help/`
using the standard `ao_<identifier>_<filename>` names. Extracted research
executables are not published or copied into permanent HELP storage.

Bounded Unicorn execution enters only those decode routines with mapped
input, compression table, product short string, output and stack. Their
return sink is captured and interrupts are forbidden; this is not a full
DOS/BIOS or screen capture. Both original routines verify the literal
placeholder grammar and six RLE combinations, including a repeated `14h`
token toggling once and a repeat count surviving suppressed text/NULs.
No host executable, installer or arbitrary DOS entry point is run.
The separately archived reconstructed TP6 source and Free Pascal's
`WOAHelp` reader do not contain this substitution branch; neither was used
as proof of the original Pascal 7 behavior.

All eight installed placeholder-bearing originals use `(52, 2)` and
contain 2,306 markers (1,153 pairs) in 791 physical Text records:
193 use the Borland profile selected from their native IndexTags
description and 598 use the Turbo default. Their 20,584 projected rows
match the corresponding original routine on the actual compressed
payload, including its real table/RLE. Stored bodies are `Turbo`,
` Turbo ` or `Turbo `; deleting only markers incorrectly retained their
padding and always displayed Turbo even in tagged Borland HELP.

The projection runs before example/hotspot handling and resets at each
physical Text record. Compression token runs are retained privately only
for records containing the placeholder; parser rows still retain all
original decompressed bytes. Other profiles keep unverified `14h` glyphs.
An untagged file cannot establish which alternate consumer opened it:
the chosen default is explicitly the verified Turbo viewer, not a guess
from its path or manifest title. All 66 source hashes and native topic,
alias, page, positioned/sequential/index target identities are unchanged.
Eight source copies change 395 topics' visible/rendered text, with no
code-row change. Use the preceding complete-model hashing algorithm:

```text
models before product substitution:
b8a0254286ffee86a91a24a2e97a45cfe9482fa67cbd05b69d601f9aa1c1656b
models after product substitution:
3bfa17ecf20d113edfcb98c32a14fec244cead5ce5b6388c07870f7657c4cf2a
original decoder placeholder-row capture:
d268765ddd4113309a232cfcf0ed48afdad59d6278c6b0252c1a0ad0eac98d3e
```

The capture fingerprint hashes compact ASCII JSON plus LF tuples
`(source_relative_name, physical_Text_ordinal, product_name.hex(),
[visible_row.hex(), ...])` in sorted path/physical order. The ordinal is
zero-based. Pure binary/event decoding and the earlier `05h` reference
remain unchanged; the product projection deliberately differs from
lossless raw text. No new runtime verification of table/reflow or hidden
anchor inference is claimed.

Publication rebuilt the 23 canonical `bp`/`tp` bundles while preserving
all other manifest products. Five payloads change 294 rendered topics
after deduplication. All 66 originals, 230 unselected library files
including the catalog, and all 251 catalog entries remain byte-identical.
Native topic/alias/page/navigation/Contents/index/inline target identities
are unchanged, including derived line targets. The full previous library
is recoverable at
`data/.helps-previous-cde32631f2f14d2bb05a657d7178df9f/`.
The complete test suite reports 1,612 passing tests, one skipped Safari
test and the existing Starlette/httpx deprecation warning. Repository
bytecode/test caches are absent after the run. The public datasheet and
Converter document, plus both representative product bundle downloads,
match the published files byte for byte.
The restarted local Docker server passes product/RLE/source/bundle/HTTP
checks under Python 3.12.15; its index is ready at 100% with 146,906 topics,
35 documents and no warnings. No public production deployment is performed.

### Native sequential word flow (2026-10-11)

The preceding table helper inferred a column count from `╤ ... ╕` in
already-rendered UHF and joined that many one-link cells. BOA chapter 6
instead defines ordinary word flow, atomic keywords and soft returns.
No border-derived table opcode is described. The actual Pascal 7 routine
confirms that the table is merely a sequence of wrappable words.

Primary runtime evidence is the same archived original `TURBO.EXE`
(`0951BC69`, SHA-256
`818e01a4cee4df09abe34562629bcfa99e63656c02bb46214bb63c8eae6ffb75`),
obtained from `https://archive.org/details/tp_20240418` / `TP.zip`.
The formatter is at file offsets `3B294h..3B4A7h`, with a far Pascal
return and 12 bytes of arguments. Its internal word reader starts at
`3B411h`, word copy at `3B463h`, and row terminator at `3B3DDh`.
BOA's independently archived chapter and package hashes are recorded in
the preceding sections. The reconstructed `HELPSCRN.PAS` helps locate the
routine but is not treated as proof of original behavior.

The bounded 16-bit Unicorn harness executes those original instructions,
not a reassembled formatter. It maps code, input/output, Self and stack;
forbids DOS/BIOS interrupts and enforces an instruction budget. Three
object-service call boundaries are supplied by the host: SortPos is a
no-op only for the explicitly empty position array; GetBuffer returns
the mapped 4096-byte buffer; Reset changes walking cursors, not formatted
text. The actual byte copying, keyword toggles, cell arithmetic and row
decisions execute natively. No full DOS GUI or cursor/selection adjustment
is claimed. A deterministic set of 1,000 bounded word/control/space vectors
matches the Python implementation exactly.

Literal leading `20h` or NUL selects a fixed row. Other rows, including
ones beginning with `02h`/`05h`/TAB, flow. Spaces inside a keyword are
atomic; ordinary runs of spaces remain at the end of their word. A
source return supplies one space unless an existing suffix run already
does. Word-fit excludes its suffix spaces, but they still contribute to
the output row width. The native formatter counts bytes below `07h` as
zero cells; this is not a general glyph/attribute definition. Oversized
words/fixed rows remain in the buffer for separate viewport clipping.

The shared projection runs after product substitution but before example
marker removal and sequential link rendering. It chooses the smaller of
76 flowing DOS cells and positive FileHeader Width minus LeftMargin,
retaining stored geometry separately. Legacy positioned profiles do not
flow. Native topic IDs, aliases, page links and keyword/index context IDs
remain stable; derived display-line coordinates are recomputed from the
laid-out rows. Source/parser rows are not mutated. Every table uses the
same byte-word algorithm, including one without a border. No table-specific
Unicode/UHF-string guessing remains. This is fixed-row conversion, not
browser-resize reflow or a merge of published continuation-page IDs.
Safe Python buffers retain large words/records rather than reproducing
the native 80-byte word temporary or 4096-byte object-buffer overflow.
Hidden-anchor destination inference remains unverified.

Corpus comparison verifies 74,211 physical records / 1,651,766 output rows,
using 38,815 distinct native calls after exact input/width deduplication.
The other 1,421 of 75,632 nonempty sequential records exceed the native
buffer/word harness bounds; they are not reported as native captures.
Large-word/large-record regressions verify safe preservation instead.
The capture hashes compact ASCII JSON plus LF tuples
`(source_relative_name, physical_Text_ordinal, width, [row.hex(), ...])`
in sorted path/zero-based physical order:

```text
native word-flow capture:
48daad19e051802eec5eb4e3dc5c7292be0c62adcd0bdfce8d4f841ce7728f9e
complete models before word flow:
3bfa17ecf20d113edfcb98c32a14fec244cead5ce5b6388c07870f7657c4cf2a
complete models after word flow:
6eebf2cf0565ecf30a2d99cab5dfb717707326c78fb14a47b6aa4ba95b9f0900
```

All 66 source hashes remain the preceding aggregate
`a954f9228d530acfae475c91590247e4554c818a3873e26843aa578aaab0a0b0`.
The corpus still has 93,032 topics, 85,484 index entries, 41,537 positioned
and 369,218 sequential targets. Forty-five original copies change 68,622
normalized/display topics; 3,800 code-row index sets move with their layout.
All native target IDs, aliases and page/navigation identities are unchanged.
Derived index/fallback display coordinates may change, not native contexts.

Publication rebuilt 58 canonical `bc`/`bp`/`tasm`/`tc`/`tp` bundles while
preserving all other products. Thirty-two payloads change 47,256 topics;
12 index entries move their display-line coordinate. The originals,
195 unselected library files including the catalog, all 251 catalog
entries and the selected bundles' topic/alias/page/navigation/Contents/
index/inline target identities remain unchanged. The complete previous
library is recoverable at
`data/.helps-previous-3eaecbc02f94445ea1951f7221620c14/`.
Published public datasheet/Converter files and the representative C++
table bundle match their local HTTP downloads byte for byte. Private
RE notes remain excluded from public Docs. No production deployment
or commit is performed.

The fresh full suite reports 1,636 passes, one skipped Safari test and
one DOSBox browser failure (`DOS close failed` after native EXIT). Both
DOSBox variants pass on isolated repetition (2 passes); the cause of
that intermittent failure is not established and no unrelated DOS code
or test assertion is weakened. All converter/corpus regressions pass,
including the new full-model fingerprint. The existing Starlette/httpx
deprecation warning remains. Repository bytecode/test caches are absent
after every run, including failures, and `git diff --check` is clean.

The restarted local Docker server passes native vectors/source/bundle/
target/HTTP document checks under Python 3.12.15. Its index is ready at
100%, with 146,906 topics, 35 documents and no warnings. The unavailable
integrated browser/native Safari surface is not reported as a visual pass.
A separate headless Chrome capture of C++ 3.0 context 2088 verifies six
aligned seven-cell rows and their dividers, with all 50 topic links (42
table cells plus eight other links) retained. The screenshot is at
`/tmp/thelp-reflow-browser.fyta6t/table.png`.

### Native context addresses and missing destinations (2026-10-11)

The original TP7 `TURBO.EXE` (CRC `0951BC69`, SHA-256
`818e01a4cee4df09abe34562629bcfa99e63656c02bb46214bb63c8eae6ffb75`)
contains SearchTopic at file offsets `46A25h..46B08h`, ReadCode at
`46B09h..46B95h`, ReadRecHeader at `46816h..4682Ch`, and the signed
24-bit offset conversion at `46744h`. Source archive/provenance and
hashes are recorded in the preceding native sections. The bounded
Unicorn harness executes the original selection/record-reader instructions
with in-memory FRead/FSeek and memory-copy services, forbidding interrupts
and enforcing an instruction budget. No DOS GUI/full I/O error emulation
or modification of the original executable is involved.

Across all 66 originals, 5,109 nonzero contexts sharing positive Text
addresses select the exact original offset. Every one of the 947 positive
padding-context offsets selects that same offset and then fails ReadCode:
the header bytes `20 20 20` imply a length of `2020h` (8,224), exceeding
the routine's 4096-byte output buffer. Only the three-byte header is read;
no compressed text is decoded. The capture hashes compact ASCII JSON+LF
tuples `(source_relative_name, context, classification, original_offset)`
in sorted path/table order, skipping context zero and untested sentinels:

```text
native context-address/record-bound capture:
909d8ff8553950fb71b968ad5136f5aaeab8cf909074f7c0bbad59d316e1c65e
complete models before context correction:
6eebf2cf0565ecf30a2d99cab5dfb717707326c78fb14a47b6aa4ba95b9f0900
complete models after context correction:
912011798c136a65073b206fe38a9d1097b1583eec0bedfff79bf4a0250019d2
```

These captures do not establish every consumer's sentinel policy. The
TP7 lookup rejects context zero, admits its count boundary without a safe
table bound, and sends negative stored offsets to slot 4, not a source
hotspot. Those application behaviors are not universal wire rules and
unsafe reads are not reproduced. The converter's header-bound `FFFFFFh`
Contents projection remains BOA's documented model. Implicit bindings in
short-header consumers require separate executable-specific verification.

The removed inference produced 767 guessed context mappings: 116 genuine
aliases, 599 padding targets, 49 out-of-namespace IDs and three unbound
Contents IDs. Native addresses do not encode that inference. The reader
now uses one primary/alias offset map (including a consistent shared
Contents primary); recognizes valid alias IDs when rendering/classifying
references; retains unavailable native IDs as link/index targets; and
exports classified offsets through the existing `unresolved_contexts`
transport metadata. Duplicate reader-local renderer/label heuristics are
gone. Native labels, rows, code attributes, context/index/keyword/page/
alias identities and all 66 source hashes remain unchanged.

The corpus keeps 93,032 topics, 85,484 index entries, 41,537 positioned
and 369,218 sequential keyword targets. Its 410,995 rendered numeric
links include those 410,755 native keywords plus 240 structural `<more>`
continuations. Twenty-two source copies change 1,191 rendered topics.
Per-copy missing-reference diagnostics contain 333 index IDs, 958 link IDs,
908 referenced padding IDs, three unbound Contents IDs and 320 out-of-range
IDs. The 947 padding count above includes unreferenced context slots too.
No missing text is manufactured, and no verified input source is rewritten.

The generic JSON writer retains reader-declared missing index IDs, without
guessing another topic from a similarly named alias. Browser links retain
their actual numeric/string URL target even when it is unavailable/unloaded.
An unsuccessful open invokes the application's existing Help Error MessageBox,
records one broken-link result and leaves the active help page/history alone.
Native aliases still resolve through the ordinary shared bundle alias map.

Publication rebuilt 55 canonical `bc`/`bp`/`tc`/`tp` bundles while keeping
all other manifest products. Fourteen payloads change 937 topic link bodies
and restore 661 previously suppressed native index entries. Topic text,
titles, aliases, page/Contents/navigation identities remain unchanged; index
labels are preserved or restored and every emitted target is either real
or explicitly declared missing. All 66 originals, 198 unselected library
files including the catalog and all 251 catalog entries are unchanged.
The complete prepublication library is recoverable at
`data/.helps-previous-747f8507440341bab8b3a70e43f14740/`.
The representative C++ alias bundle and public datasheet/Converter/UHF2
documents match their local HTTP downloads byte for byte. Private RE notes
remain excluded from public Docs. JavaScript/context-help mirror pairs and
`node --check` pass. No commit or production deployment is performed.

The complete suite reports 1,650 passes, one skipped Safari test and the
existing Starlette/httpx deprecation warning. The Docker Python 3.12.15
alias/source/bundle/HTTP smoke checks pass. Its global index is ready at
100%, with 146,906 topics, 35 documents and no warnings. Repository
bytecode/test caches are absent after every test run and `git diff --check`
is clean.

Real headless Chrome mouse input opens C++ 3.0 alias 543 at canonical
topic 542 in the existing window. Clicking the German Pascal 6.0 source
topic 1801's unavailable target 281 shows Help Error while preserving
the same window and source topic. The screenshot is
`/tmp/thelp-contexts-browser.gQ92It/missing-topic.png`. Initial browser
harness failures used a wrong dialog selector and a stale debugging-port
file; fresh profiles and the actual shared dialog root fix the harness,
without weakening an application assertion or changing application code.

Confirmed Turbo Assembler sample: `data/sources/Borland Turbo Assembler/TASM.TAH`
is a normal THELP-family file. The current loader detects it via the standard
THELP signature and reads it with `format_version = 52` / `text_version = 1`;
no separate `TAH` decoder is needed.
The independently collected Turbo Assembler 2.01 `TASM.TAH` (`C517BD6D`,
167,927 bytes) instead uses `format_version = 5`, `text_version = 1` and
contains 491 text topics in a 492-slot context namespace. The same THELP
reader handles it. Its installer README confirms the 2.01 edition; the CRC
manifest retains the enclosing WinWorld release/download and fallback query.
The original 2.0 disks contain the already retained `TASM.TAH` (`07E89446`,
166,816 bytes); no duplicate source copy is required. Its manifest record now
identifies release 2.0 and a distinct bundle stem, avoiding the previous output
collision with `9AC3E64A`. Both editions retain their genuine context IDs.

---

Turbo Debugger 1.0 `TDHELP.TDH` is a product-specific exception, not a
THELP record stream. It has no `$*$* &&&&$*$` signature, starts with
`02 06 00 01 ...`, and appears compressed/encoded from offset 0. The downloader
collects it and the help database records its CRC32, but it must be decoded by
a separate TDH reader rather than by the THELP parser.

---

The current parser treats `0xFFFFFF` entries as aliases to the header's
Help Contents context when the file header defines one. In the original
viewers this is the help contents screen, not the alphabetical index.

Physical text screens which are not assigned a context-table id arrive at the
reader with the sentinel context `0xFFFF`. Non-empty orphan screens are still
real content and receive stable synthetic export contexts beginning at
`0x10000`; only completely empty orphan records are omitted. The assigned ids
and empty-orphan count are retained in parser metadata.

---

For HTML export this means `0x05` / `0x10 0x05` should not be rendered as CP437
glyphs such as `♣` or `►♣`; they behave as structural delimiters for a code
example block.

Some files contain no explicit example delimiter and use a visible heading such
as `Example:`. In that fallback mode, headings such as `See Also:`, `Notes:`,
`Remarks:`, `Syntax:`, `Description:`, `Parameters:`, `Returns:`, and `Errors:`
terminate the inferred code block even when indentation would otherwise keep it
open.

---

### 1.11 Suggested Decompiler Source Mapping

A recompilable textual representation that preserves exact binary data can
use the following directives:

```
;CONTEXTCOUNT 1334
;UNUSEDCTX 42 FFFFFE
;SCREEN 424
;COMMENT ALIASCTX 658
...
;KEYWORD4 146 AT (3,22-43) NAV (1,2,0,0)
;INDEXORDER 424 Runtime errors
;TAGORDER 17 Errors
;TEXTCOMPLETE
```

Recommended meanings:

- `;CONTEXTCOUNT`: exact context table size
- `;UNUSEDCTX`: exact special context-table sentinel as emitted in source form
- `;COMMENT ALIASCTX`: additional context numbers sharing the same text offset
- `;INDEXORDER`: raw `RT_Index` order
- `;TAGORDER`: raw `RT_IndexTags` order
- `;TEXTCOMPLETE`: exact v5+ text-record ending state

---

### Earlier missing-context inference (unverified)

The former reader redirected a missing context to a unique referring
Keyword row, sometimes matching an Index label too. This was an export
heuristic, not a decoded destination. The native context audit rejects
that inference: record offsets are authoritative, and even one source
occurrence cannot supply a missing destination. The presently installed
C++ 2.x originals have no unresolved context targets; earlier claims of
their exact hidden-anchor reconstruction were not runtime proof.
DEHELP's hard-coded `HC_INDEXTABLE=401` skips a generated index screen
for recompilation; it does not recover absent context destinations.


For decompilation, a practical textual source format is:

```
;KEYWORD4 146 AT (3,22-43) NAV (1,2,0,0)
;KEYWORD 432
```

## Software602 M602

### Native directory and hotspot evidence

The 396,413-byte ZIP downloaded from the version 2.0 page at
`https://softmania.sk/operacne-systemy/m602/download/31920` contains a
byte-identical `M602.HLP` (139,965 bytes, CRC32 E851C195, SHA256
`68400f18501288affa7cf7138e111cf70a67aacd0ba8fad8b64d7407f2676e99`).
Its 801,695-byte `M602X.EXE` has SHA256
`d4ab0fc6fbd9fe655eb42f141fa17fed8bd9b7db4a44591a16a8f17a9c75224f`.
All following addresses are executable file offsets, not load addresses.

- `89040h`–`890C1h` reads the final DWORD and the WORD at EOF-6.
  `890C4h`–`8910Ah` locates EOF-6-count*8 and reads count*8 bytes.
- `89121h`–`891AFh` scans the first WORD of each eight-byte entry, returning
  the first matching slot. If absent, it scans for WORD 270Fh (9999).
- `891F7h`–`89235h` takes the selected entry's DWORD at +2 as the seek
  position and its WORD at +6 as the read size. The WORD is not a delta.
- `89291h`–`892B9h` XOR-decrypts the allocated topic bytes with FAh.
- `8971Ah`–`8976Dh` copies a Pascal record, advances by length+1, then
  decrements its display length. All 3,363 inspected records end in one CR.
- `8959Dh`–`89717h` removes the opening hotspot delimiter and closing
  delimiter/operand bytes, replaces label underscores with spaces, and keeps
  their full padding. `896A2h`–`896CCh` assembles the inline operand high byte
  first: this is a native big-endian context, unlike the directory WORD.
- `8980Dh`–`89819h` replaces a leading 01h with a space; `89A30h` onward
  joins soft records and wraps them at the runtime width, with 01h hard rows.

Bounded Unicorn execution of only `89121h`–`891AFh`, with an injected
directory/object/stack and no DOS calls, confirms all 201 context lookups and
the absent-context fallback to native 9999 at slot 1. The native
`(context WORD, absolute offset, size)` trace SHA256 is
`e6caa3c3b96b36f5b3df75634ebf95af2257a5e69d8158118826a2a28caab836`.
The remaining claims above are instruction/byte inspection, not a full
application run or pixel/native-wrap comparison. Research files are outside
the repository at `/tmp/thelp-m602.QJjapZ/`; Capstone/Unicorn are not runtime
dependencies.

### Converter mapping and limits

`m602.py` retains physical-topic UHF ordinals and the raw inline LE-code
convention used by source-HLX dumps. Each indexed range is decoded separately;
identical ranges share one physical topic. The directory maps raw targets back
to those UHF IDs, including the previously omitted error context. No title
similarity is used for binaries. An unknown target takes the original 9999
fallback, retained in `missing_raw_link_targets`; absent fallback fails
explicitly. Malformed footers, ranges, records and links cannot publish a
partial HELP. Padded labels now retain their native widths in 15 topics;
all 201 titles, 201 index labels and 406 link destinations remain unchanged.

The earlier display projection removed title decorations/leading row prefixes
and kept stored rows instead of the native soft-wrap routine. The native
display follow-up below replaces that projection; those earlier converter
choices are not source-format fields.
Source-only HLX uses its separate label/title recovery when no binary companion
exists; a companion must pass the same binary structural validation.

The OS-DOS.NET 3.0 installer was downloaded for comparison, but its DATA602
installer containers have not been decoded/verified. No unverified 3.0 HELP
or new edition/CRC was added, and the 2.0 duplicate was not copied as an edition.

### Native M602 display assembly (2026-10-12)

Research `/tmp/thelp-m602-layout.wMCGn8/native_layout.py` uses the same
byte-verified original M602X.EXE. It maps the resident image after its 4E60h
MZ header and the HELP overlay at file 88FE3h. Enter `89A2Bh` after the
already independently verified source loader, injecting its complete decoded
payload and width. Execute original record-copy `8971Ah`, row assembly/
wrapping `89A2Bh..89B44h`, split finder `894E3h`, hotspot decoder `8959Dh`
and emitted-row storage `89770h`. Original Pascal Copy/Delete/Concat/Move
and NewStr routines execute too. The only host shim is RTL GetMem; there
is no Python implementation of HELP wrapping/decoding in the harness.
Stop before scrollbar/video updates at `89B44h`, forbid interrupts and
bound each call to 1,000,000 instructions. Read original stored row strings
and six-byte `(native_context, row, first_column, last_column)` descriptors.

All 201 indexed payloads match at width 78: 3,012 literal rows and 406
hotspots. Serialize compact JSON+LF, physical-topic ordinal and row order:

```text
(topic_ordinal, one_based_row, native_row.hex()):
2cc0dc638d5f302b3708d2ec4bb8ade522d1badf9e1dae3c0d756bde69b2fd2d
(topic_ordinal, native_context, one_based_row, first_column, last_column):
55d216d03aeb878eed01eb81141b54a01c7ec4c3f28ff9b9f7fe482452f66699
```

The critical order is raw short-string assembly, then hotspot removal,
then leading-01h replacement and row storage. Hard rows never wrap; a last
unjoined soft record is not separately wrapped. Soft joins insert one space,
include the cut's space and count encoded link bytes. Label underscores
stay protected until decoding. Literal internal CR/NUL/TAB remain cells;
only one final suffix is removed. A leading 01h created by a wrap or hotspot
removal is also replaced by a space. Synthetic native vectors at widths
10/40/78 confirm these rules, including long terminal labels and source art.

The reader uses raw-byte-to-cell mapping and common positioned keywords/UHF
rendering. This preserves all cells, padding and original targets, including
adjacent identical links. Only label fragments get a carried source target
when a rare cut crosses the label; no native out-of-string search or guessed
destination is reproduced. Wider buffers preserve text beyond Pascal's 255-
byte concatenation limit. Zero-length records would underflow native length;
missing CR suffixes and incomplete operands are rejected, while zero-byte
topics and genuine empty display strings remain valid. The 78-cell published
width is a DOS projection choice, not an invented file header field, and
browser-resize reflow remains separate work.

All 3,012 original rows survive shared UHF escaping and link rendering without
cell loss. The 201 topic IDs/titles, native destination order and index remain
unchanged. Focused reader/layout/HLX/export/catalog regressions report 106
passes. An initial synthetic fragment fixture wrongly placed the cut's space
on the following row; the corrected fixture retains it on the prefix according
to the raw-byte cut rule. No original input or expected native corpus trace
was changed to accommodate the implementation. Bytecode/test caches are absent.

The complete suite reports 1,694 passes, one skipped Safari regression and the
existing Starlette/httpx deprecation warning (315.87 seconds). Staged publication
rebuilt the five Software602 outputs, with normalized changes only in M602:
all 201 bodies gain the verified projection. Original checksums, every topic
ID/title and per-topic destination order, Contents/Index, the 251-entry catalog
and all other products remain unchanged. The prior complete tree is recoverable
at `data/.helps-previous-6bbaf91c66b64a379ffa3ca992675abe/`.

Local Docker was restarted to load the new reader. Its Python 3.12 independently
confirms 201 topics, 3,012 rows, 406 positioned links and display width 78.
Public datasheet/converter docs and the current bundle match their HTTP bytes.
Headless Chrome renders the full shared frame and restored art, then actual
mouse input on “panely” opens topic 14 in the same window. An initial click
probe was blocked while the modal index-progress dialog was open; repeating
after completion passes. The index is ready with 146,906 topics, 35 documents
and no warnings. No per-file UI/CSS, compatibility links, commits or production
deployment were added. Final diff checks pass and repository test caches are absent.

## Software602 K602

### Native directory evidence

The 151,236-byte self-extracting archive at
`https://www.osdos.net/download/k602/k602.exe` contains a byte-identical
`K602.HLP` and a 289,947-byte original `K602.EXE` (SHA256
`14a8a2926524f509fa05f754b70094cc16766bf2d105f89b364bbd889bbd2bac`).
The archive was extracted as data, never executed on the host. These are
EXE file offsets, not MZ-relative instruction addresses:

- `2ECEDh..2ED15h`: read exactly `060Fh` header bytes and compare the
  Pascal signature against the executable's `K6HLP86278` stamp.
- `2ED17h..2ED2Bh`: compare physical file size with the DWORD at header +11.
- `2EFA4h..2EFBCh`: zero-extend the input context byte, multiply by six and
  add `1DE7h`, i.e. header buffer `1DD8h` +15. The initial 17 zero descriptors
  belong to the 256-slot directory, not a 117-byte header. Bounded execution
  of this original address calculation agrees for every context `0..255`.
- `2EFBDh..2F07Eh`: an offset DWORD of zero means unavailable; otherwise
  allocate size +1, append an in-memory `05h` guard, seek to the absolute
  DWORD offset and read exactly the size WORD. Shared/unsorted and zero-byte
  descriptors need no invented ordering or positive-size constraint.
- `2EE27h..2EEBBh`: copy a complete one-byte-length-prefixed row only when
  length +1 fits the remaining topic. Its byte increment can overflow at
  length 255; the independent decoder uses wider arithmetic.
- `800Ah..80C9h`: distinct selectors choose/reset categories 1, 2, 4, 20h,
  6 and 7. The ordinary inline printer resets category at each stored row.
  The 1,773 observed stored rows only contain selector bytes 02h and 04h.

### Native font and printer verification

The follow-up inspection identified the built-in regular fonts at EXE file
offsets `B3F9h` (256 ×15 rows) and `C2F9h` (256 ×11 rows). Init at `89A2h`
sets the near pointers within code segment 071Ah, not within DGROUP; the
graphics kernels read glyph bytes with a CS override. The optional font
loader at `8892h..897Fh` accepts a 7,168-byte file containing these two fonts
followed by two 256-byte tables. No external font or executable is required
by the converter; Unicode transcription uses the inspected built-in font.

The original EXE is loaded as data in a bounded 16-bit CPU emulator with its
resident MZ relocations. Only printer `071Ah:02BDh` and the original Pascal
string/set helpers execute, stopping at the screen handoff before pixels.
All 1,773 stored rows match literal font-byte/category cells, including 49,016
cells: 44,489 ordinary, 3,677 bold and 850 italic. The immutable trace digest is
`6759d69ef558e294b532267bd4a1f64a630aab2ebadfbab6016e03ffd95699ee`.
Columns also match the handoff; no controls or glyph operands are borrowed
from another row. This is a complete logical-row comparison, not execution of
the full application, native viewport clipping or a pixel-exact browser font.

`9712h` writes ordinary glyph rows, `9896h` thickens bits with OR/right-shift
for bold, and `9ACEh` slants upper rows for italic. `8D46h..8D6Dh` confirms
underline; other kernels show double-width and raised/lowered five-row fonts.
The viewport clamp is `max(width, 50)` then `min(width, 70)` at `2F0C8h..2F0E1h`,
with helpers at `20F63h`/`20F51h`; its body loop displays 14 rows. These are
executable rules, not HLP header fields.

96h/97h/98h are full/lower/upper blocks in both fonts, including chart entries,
row-ending shadows and title/underline decoration. FEh is a shortcut dash;
the entire high-byte charset differs from Kamenicky, not just those four bytes.
8Dh is blank and 0Ah is a curved corner. The exceptional 135-byte row therefore
remains one row containing two `SP ╯` pairs, not three invented rows. Compound
boxed-key glyphs are absent in the HLP and have no adopted one-character
Unicode mapping. Custom font table roles remain partially unspecified.

### Mapping and validation

The 115 topics use native IDs +16 relative to the erroneous original exported
ordinals, without compatibility aliases. Titles and all 92 authored index
captions remain unchanged; topic bodies now retain literal block/shadow glyphs,
native characters and italic instead of the former wrong codepage/attribute
guesses. Generated fallback captions follow corrected IDs. `02h`, `04h`, `13h`
map to shared UHF bold, italic and underline respectively, preserving the
native row-local category switch/reset, not accumulating separate flags.
Literal UHF-like source strings are escaped by the shared renderer; stub/index
selection operates on decoded source cells, not by stripping markup tags.

`display_width=70` selects the existing fixed-cell HELP viewer and horizontal
overflow, using the native maximum instead of recreating dynamic per-topic
50–70 sizing. Original long rows are retained rather than clipped. There is
no format-specific JS/CSS, new renderer or bundled native executable/font.
Untranscribed compound key glyphs are visible U+FFFD cells, not silent deletions;
unrepresented double-width/super/subscript selectors raise explicit errors.
Neither case occurs in this original. Pixel-exact glyph colors, custom fonts
and those size variants remain outside this conversion profile.

The reader validates all 256 directory entries and bounded complete rows,
accepts zero-offset unused size WORDs and empty/shared payloads, and rejects
malformed descriptors instead of returning a shorter successful HELP. The
native byte-length-overflow bug is not reproduced at 255: independent decoding
uses wider arithmetic. Tests include a real failed staged publication and retry,
native-cell digest, all high-byte mappings and style/glyph/cursor edge cases.

## Software602 T6HLP

### Original reader/printer evidence

The 3,107,571-byte SFX at `https://www.osdos.net/download/t602/t602.exe`
contains `T602/D_2/T602.EX@`, a 207,087-byte raw LZSS payload. Research-only
expansion uses a 4,096-byte space-filled window at FEEh, low-to-high flag bits,
literal bits set, and two-byte offset/length matches. The expanded original
`T602.EXE` has 367,854 bytes and SHA256
`244b5cd591fe552476d00f79ec7b0d69dea3541bfa9f81e934dd1d435f72ce41`.
The installed T6HLP input has 102,013 bytes, CRC32 CCC3E5FB and SHA256
`f258a874876cc3f01c620e50eabff6d46f054412679067a4855ca16613684b66`.
No duplicate HELP edition or unverified installer container was published.

Executable addresses below are file offsets:

- `5012Eh`–`5016Ch` loads exactly 060Fh header bytes, compares its Pascal
  stamp with `T6HLP86278`, and verifies the DWORD at header+0Bh.
- `503EAh`–`50403h` widens the byte context, computes 6*C and adds DS:3CC9h,
  which is header DS:3CBAh + 15. `50403h`–`5040Dh` tests only offset DWORD.
- `50438h`–`50488h` appends memory guard 05h, seeks the descriptor DWORD and
  reads exactly its size WORD. Empty/unused slots are distinct native cases.
- `50271h`–`50302h` copies one Pascal row and advances length+1; NUL in the
  length position is a blank row, not a split-record separator.
- `504CDh`–`50523h` measures row widths and clamps the help viewport to 50–70
  cells. The help caller starts with 14 rows at `5059Dh`.
- Graphics printer `0C44:0272` starts at file D7E2h; category switch at D6FFh
  gives 02h bold, 04h italic, 13h underline and 0Fh/14h/16h size changes.
  Every other byte reaches the glyph writer, including 96h/97h blocks.
- Its built-in 8×15/8×11 tables begin at 10C5Ah/11B5Ah. They match the
  verified K602 tables for every observed visible HLP glyph (all high bytes);
  unobserved compound low slots 00h/0Fh/10h have differing bitmaps. The shared
  Unicode decoder does not invent a transcription for compound cells.

Bounded Unicorn execution of directory arithmetic verifies all 256 slots.
Original row-printer execution stops before D570h's glyph/pixel handoff and
matches all 3,360 stored rows, including 631 zero-byte and four selector-only
rows. It emits 95,759 cells: 88,908 ordinary, 5,444 bold, 1,407 italic.
Native `(context, row font-byte/category cells)` trace SHA256:
`754d12e69eca07a27eb968898cec4cbab4c15aec94af1dfaf34f0db8fc596428`.
This is logical-cell/style verification, not a full application, pixel or
clipping comparison. Capstone/Unicorn are research dependencies only.
Reproduction artifacts are outside the repository at `/tmp/thelp-t602.a4bieR/`.

### Converter mapping and limits

T6HLP topics now retain native slots rather than IDs shifted by one, without
compatibility aliases. All 191 title strings and index labels are retained;
their corrected `(ID, title)` and `(ID, index label)` SHA256 values are
`30619d2164371653adf67ce9084188ada94cd34850de3d1c97905fde88d35abb` and
`baa45ef5d5354bd0a5e5840a4496b87388bc7bde85d7e303f990cb9a761a17db`.
Authored header/block rows and internal empty rows stay in the UHF body;
only outer blank rows/trailing spaces are trimmed. Prev/Next over populated
contexts is converter convenience, not a source field or invented hyperlink.
Shared `readers/software602_graphics.py` handles the verified font/category behavior
for K602 and T6HLP; K602's native-cell/name/index baselines remain unchanged.
The later 3.10/Calc602 chunk parser is not affected by that sharing.
Special cell-size selectors fail explicitly rather than becoming false glyphs;
compound key bitmaps have visible replacement cells. No per-format JS/CSS.

## Norton Guide

The public [Norton Guide datasheet](../Formats/Norton%20Guide.md) describes
the binary fields and decoding algorithm. Implementation/corpus evidence
belongs here rather than among source-format fields.

### Physical corpus and structural-validation baseline

All 58 installed originals were read without rewriting their bytes. Their
decrypted physical layout is:

| Record class | Count |
|---|---:|
| MENU | 120 |
| SHORT | 832 |
| LONG | 20,357 |
| Total topics | 21,309 |

Reading all records sequentially produces the same 21,309 topic offsets and
resolves every internal text link, positioned hotspot, and non-terminal
directional navigation target. The converter deliberately does not strip
unresolved link markup as a repair strategy; a missing target is treated as a
parser or source-data error to investigate.

Baseline was captured before tightening validation. For each source, hash
the original bytes; for each parsed document hash compact, sorted-key UTF-8
JSON from `document.to_dict()` with `ensure_ascii=False`. Hash each resulting
sorted filename-to-digest dictionary as compact UTF-8 JSON:

```text
sources aggregate SHA256:
6d37d26a096bc96eec58ac9e4363429a1a63afa10d6250eb8157391990b85a1b
models aggregate SHA256:
31d401038dcecfa939a02178d2a96a6548b56a2f45431e17ec2fd6ccc5ff001d
```

Both aggregates remained identical after the structural parser/API changes,
covering all raw rows, UHF text/styles/links, names, positioned keywords and navigation,
not merely record counts. That validation-only pass required no bundle
regeneration. The native text pass below intentionally changes the models
and requires rebuilding those bundles. No title/CRC-specific workaround
was added.

### Structural validation and input API

The old reader accepted several malformed inputs by scanning for a plausible
root, skipping bad SHORT offsets and stopping early on incomplete LONG/
see-also data. It could also omit zero-line physical records, leaving valid
incoming pointers without a destination. The bounded reader consumes all
records from offset 378, validates their complete tables/strings and retains
empty records. A separate post-pass checks every raw pointer, even when its
label is empty or has no visible hotspot span. Only LONG `Next` accepts EOF;
no nearby-offset recovery or link deletion is used.

All real SHORT strings lie beyond their complete descriptor table and end
within their record. All MENU records contain `StoredCount - 1` pointers,
the `(PromptCount + 1)*8` auxiliary bytes, title/prompts and a trailing `00`.
The trailer's meaning/value is not promoted to a format invariant. LONG
records demonstrate why logical content must not consume the whole physical
payload: 15,258 have no remainder, 4,943 have one `00`, 28 have two `00`,
and other remainders include literal fragments such as `6F 77 00 00` and
`6E 64 6F 77 00 00`. Remaining bytes are opaque, not additional lines.
Synthetic fixtures also cover shared/unsorted strings, full-width header
fields, empty guides, arbitrary nonzero see-also flags and self/cyclic links.

`NGReader` now follows `HelpReaderBase`: standard source-name/encoding/path
constructor, `read_bytes()` and inherited `read_path()`. Header/title/credits
are decoded from the supplied buffer on every call; no constructor IO or
cached header survives across reads. Removed the manifest/exporter's old
path-initialization mode rather than retaining a compatibility branch.
Previously that mode reopened an already-unwrapped DOS BACKUP source and
rejected its transport magic. A factory-level wrapped-NG regression verifies
in-memory decoding and preservation of the original transport bytes.

Four staged server tests corrupt the root, SHORT descriptor, record target
or line count. Each failed job preserves all published bytes/catalog and
cleans only its disposable stage; a repaired input can be retried and the
previous generation is verified in the normal backup.

### Independent references and remaining work

Compared with Dave Pearson's
[format notes](https://www.davep.org/norton-guides/file-format/) and his
[ngdb.py source](https://github.com/davep/ngdb.py/tree/cb685aec5b1ed2c6153d823915c640258f6c30b7),
especially `menu.py`, `entry.py`, `seealso.py` and `reader.py`. The pinned
MENU implementation independently confirms count-minus-one, auxiliary-table
size and the trailer. Its string reader finds NUL before expanding spaces;
there is no basis for letting an RLE operand consume a following record.
External research guides were not installed or registered as new products.

The structural pass intentionally left rendering unchanged. An attempted
removal of zero-width positioned keywords changed four real fingerprints and
was reverted at that stage. The native verification below establishes the
whole-row ranges, including previously invisible leading-padding links.
Structural checks are not a replacement for a trusted source checksum.

### Native body text and SHORT selection

Original programs were obtained as research artifacts from
[Norton Guides](https://archive.org/details/norton-guides-peter-norton), archive
`Norton Guides.zip` (SHA1 `c0ac6b5f77b165c73737fcc24178be1da4423d19`). They were
not executed on the host or installed as server DOS packages. Bounded 16-bit
emulation loads the MZ code/data and calls only the original row loop; DOS/BIOS
interrupts are forbidden. Its actual video sink writes character/attribute
WORDs to mapped memory. Skip only final blank-fill and stop at an explicit
return address; no host filesystem/network calls are emulated.

| NG edition | Original EXE SHA256 | Row loop / video sink (MZ image-relative) |
|---|---|---|
| 1.00 | `68d924b7fb2b008195d4a4d9b68be1217921fad48c9313b91156e5a12e0a7eee` | `6810h` / `71F5h` |
| 1.02 | `3a2f4336b5164bcd8747a9e36437cb9551a6a88b723d1fb9df9dfc3af490a2f0` | `6718h` / `7135h` |
| 1.04 | `36c9d83477f5ac6f5b61fbe202eb5dddde9ea1d4f07f3afe799d81a49fb83c71` | `6734h` / `7015h` |

All three produce identical test-vector cells/categories. In 1.04,
`6734h–681Ah` decodes a row, `72C2h–72EBh` implements ASCII/OEM uppercase,
and the data table at DS:`100Ah` supplies the eight non-ASCII substitutions.
Row entry attribute is saved in DH, current attribute in DS:`07C8h`, and
the standard normal/reverse/bold/underline bytes are in DS:`08C4h/08C6h/
08C8h/08CAh`. An attribute request compares byte equality, then either
resets to normal or replaces the current value; entry-reverse suppresses
changes for selected rows. End restores the entry attribute, proving that
style state does not leak between lines. Hex operand arithmetic and low-byte
glyphs were checked with literal, non-hex, zero and incomplete operands.

All 509,785 SHORT/LONG body rows (24,159/485,626) match original 1.04 output
at its 78-column viewport. For the 888 longer logical lines, capture the
original loop's emitted DL/current-attribute before its video sink, using
a wider loop argument; keep those logical tails without pretending the
original 78-cell window showed them. This verifies all 17,967,220 expanded
character/attribute cells. Two thousand seeded arbitrary bounded strings
also match the native decoder, including OEM escape folding.

The corpus hash serializes each `(filename, record_offset, zero_based_row,
cells.hex(), attributes.hex())` as compact JSON followed by LF, in sorted
file/physical-record/row order:

```text
native logical-cell SHA256:
63124b7e9e4cdf9fdfe70a55ee05cedc30c4fd449912bec7ff42ff05bd31f3a8
corrected complete-model aggregate SHA256:
681be2281acc543956dd346d0212f8ef3285ecea4709856c2db79bcc310e1183
```

SHORT selection is a whole-row operation: `1708h` selects a descriptor and
`1916h` calls the row renderer with normal/reverse and width 78. There is
no first-FF label-width boundary. The old heuristic incorrectly truncated
multiword/inter-column captions and could produce a zero-width hotspot
after an opening style marker. The corrected ranges cover the full decoded
row and labels retain the whole visible source caption, including descriptions.

Comparison with the pre-rendering model changes 51 documents, 7,847 topics,
409 raw rows and 6,856 derived names; every original record ID, Parent/Prev/
Next target and all 36,265 positioned target identities remain identical.
The old source aggregate remains unchanged. Current regression hashes lock
the corrected cells/models rather than requiring the erroneous old output.

The one shared byte decoder supplies both raw cells and UHF spans. Normal,
bold, reverse and underline categories reuse the existing themed viewer
styles; other attribute bytes retain explicit colors. This is an intentional
presentation projection, not native theme/hardware-blink emulation. NUL,
TAB/CR/LF and DEL literal cells have explicit visible glyphs. Incomplete
numeric escapes are NUL-bounded and cannot pull in another line; native
adjacent-memory continuation is not reproduced. Original body text, not
menu/see-also prompt grammar, is the verified scope. Expert Help-only
rendering extensions remain unverified; no viewer-specific JS/CSS was added.

### Native MENU descriptor addressing and plain captions

The same 1.04 image relocates MENU descriptors in `0FF0h–1030h`. It takes
the table at payload base plus the fixed-header WORD at `+06h`, adds the
payload base to the first WORD of each eight-byte descriptor, and places
the title pointer immediately after `StoredCount` descriptors. The first
`StoredCount - 1` descriptors identify prompts; the last points to an empty
string. This is not two opaque arrays followed by implicitly sequential
labels. Generic popup drawing at `63A8h` reads the same descriptor: `+02h`
is its check state, `+04h` its separator/disabled state and `+06h` its DOS
key code. The end descriptor's other WORDs are unused; BEATLES demonstrates
why they must not be required to be zero.

Bounded emulation of the original relocation routine verifies the title
address and all 553 caption offsets in the 120 installed menus. Here the
table-offset WORD is always `4*PromptCount`, and caption offsets agree with
sequential compiler output, but the original routine addresses through
each WORD rather than deriving that agreement. Synthetic shared, unsorted,
title-sharing and gap-separated table fixtures exercise that distinction;
invalid offsets/overlaps/nonempty terminators fail bounded conversion.

MENU rows call plain output (`7738h` wrapper / `7133h` loop in 1.04), not
the body decoder. See-also popup captions also use plain output. Equivalent
loops in 1.00/1.02 begin at `730Ah`/`7254h`. Direct execution confirms that
`^B...^N`, `^^`, leading/trailing padding and FFh are emitted unchanged.
FFh is an OEM blank cell, not a run operand or an instruction to swallow
the next character. TAB expands to absolute eight-column stops, BEL is a
no-op, CR/LF move the DOS cursor; body literal-glyph semantics are distinct.
The installed captions contain none of those four terminal controls, so
every native-emitted byte can be compared directly with the source caption.

The complete native caption baseline contains 120 titles, 553 MENU prompts
and 13,878 See Also labels, totalling 111,967 cells. Serialize compact JSON
`(filename, record_offset, kind, zero_based_caption_index, cells.hex())`
plus LF, in sorted file/physical record order; MENU title is first, then
its prompts, and See Also labels are in pointer-table order:

```text
native plain-caption SHA256:
b49a803f880c9bc5e891c4899cb4fdb9b12fa8666ba67616a1afffcf5fb8e984
complete model aggregate after caption preservation:
ff848d86fce1c3eab9a101d820b42135ee626b9c240241aeffca21f7564e3e10
```

UHF caption rows now retain source bytes/cells rather than applying name
cleanup to their displayed content. MENU blank/symbol-only captions no
longer become child titles or invented `Context` labels. See Also keeps
captions without targets and positioned targets without visible captions,
preserving slot order and duplicates. Friendly search/topic names may still
use the separate name-cleanup path; it does not mutate visible captions.
The archival UHF projection uses normal topic rows, not the native popup
chrome or terminal cursor movement; those rare control-bearing captions and
Expert Help-only extensions remain separate presentation work.

Compared to Git's pre-native decoder, the complete NG pass now changes 53
documents/7,861 topics and 446 raw rows. All 21,309 record IDs, Parent/Prev/
Next identities and 36,265 positioned target identities remain identical;
the original-source aggregate is unchanged. Staged regressions also corrupt
the MENU table location and caption offset, verify that failed conversion
preserves publication, and retry after restoring the valid original input.
Compared specifically with the already-published native-body generation,
caption preservation changes visible content in 105 topics across 12 NG
bundles, without changing topic titles. For example, GT_LIBNG at 1511 has
the authored `GT_S2ARR()` See Also caption with no stored target: retain
the caption as text instead of either dropping it or inventing a link.

## Game Cheater PC-Fand Format

### 2026-10-13 — native name lookup and embedded help

Inspected Pc-Fand revision
`fdd28085095886f39e493486752fc112ac103336`:
[WWMENU.PAS `GetHlpText`](https://github.com/alisoss/pcfand/blob/fdd28085095886f39e493486752fc112ac103336/pas/WWMENU.PAS#L630),
[COMMON.PAS `EqualsMask`](https://github.com/alisoss/pcfand/blob/fdd28085095886f39e493486752fc112ac103336/pas/COMMON.PAS#L67),
[KEYBD.PAS `TabLtN`](https://github.com/alisoss/pcfand/blob/fdd28085095886f39e493486752fc112ac103336/pas/KEYBD.PAS#L62)
and `EDITOR.PAS`'s Help viewer. This is source-code evidence, not a claim
that the original Game-Cheater executable was run for this comparison.

Native lookup scans physical records from the beginning. It applies the
Latin2 byte-fold and character-order table, then uses each stored name as
the mask. It does not collapse whitespace, expand sharp-s or choose the
nearest duplicate. A matching empty memo advances to the next physical
nonempty memo without comparing the intervening names again. Nonfinal `*`
consumes its next mask byte literally, even another `*` or `?`; this is not
ordinary filename globbing. The display hides a leading `{` description
through the first CR and at most one following LF. The help Contents name
is `root`.

The 531 GCHLP slots contain 486 names, 383 nonempty texts and 103 named
empty aliases. The marker-delimited Pc-Fand range belongs to the same
lookup namespace. The user chose to preserve it in the existing Nápověda
bundle rather than split it into another file. Its removal had left real
links without their original destinations. Root's `Int_help` now reaches
the first embedded record (context 3649), rather than a later duplicate;
`Hledání cheatu` reaches `hledání cheatů` (3606) by the actual byte fold.
The two installation links in contexts 3538 and 3542 both select the first
`instalační program` (3505). Empty `navigace`, `rámečky` and `clipboard`
names forward to 3517, 3522 and 3524 respectively.

The complete model has 3,991 records. Suppressing the 103 genuine alias
stubs leaves 3,888 published articles: Cheaty 3,301, Firmy 142, Internetové
adresy 56, Nápověda 383 and Informace 6. Nápověda retains all 486 named
Index/Contents entries, with empty aliases pointing to their actual text.
No former generated topic IDs are retained as compatibility aliases.
Only the real empty-record identities are attached to their destinations.

An independent byte-regex implementation of the native mask grammar and
a physical record scan verify all 669 converted help links. Regression
vectors also cover duplicate ordering, diacritics, exact whitespace,
literal escaped markup, masks, empty memo aliases, Contents, page navigation
and hidden description boundaries. The targeted reader, validation, link,
bundle, navigation and downloader run passes all 120 tests.

Staged publication rebuilt all five Game-Cheater section bundles. The 253
catalog entries retain their paths, product/release grouping and source-file
mapping; only Nápověda's article count changes from 167 to 383. All 495
original files and 248 unselected bundles retain their SHA-256 hashes. The
other four Game-Cheater sections retain their article titles and text;
Informace's generated IDs move with the expanded preceding source section.
Every published link, Index/Contents destination and the 103 native aliases
resolves inside the Nápověda bundle. Its Contents ID is 3501 (`Root`). The
previous generation remains recoverable in
`data/.helps-previous-0075a180981d458f88883c74f15cd4e0`.

Chrome verification against the local Docker server uses the published
bundle in the shared TVWindow with one vertical scrollbar. Actual mouse
clicks reach embedded context 3649, the diacritic-fold target 3606 and both
first-duplicate targets 3505. Back restores Root; the empty-record public
URL and Index entry both open 3517, and the help Contents command opens
3501. No browser exceptions are reported. The refreshed global index is
ready without warnings: 172,326 articles and 36 documents, an increase of
216 articles from retaining the previously omitted source text.

### 2026-10-12 — literal frames and bounded storage

The original Pc-Fand [FILEACC.PAS](https://github.com/alisoss/pcfand/blob/master/pas/FILEACC.PAS)
confirms the signed header count: `RdPrefix` takes its absolute value and
`WrPrefix` uses a negative value for type X. All six local table headers
match their physical active records: CHEATDBS -3301/111, FIRMY -142/55,
GCNETADR -56/143, GCHLP 531/39, DBSNFO 1/42 and GCPRM 1/100.
There is no evidence for treating CHEATDBS's count as an unrelated counter.
The reader no longer derives/clamps counts or imports spare slots at count zero.

`TFile.Read` excludes offsets below the 512-byte header; `RdWr` follows
raw pointer DWORDs only when the logical remainder exceeds the whole physical
page remainder. The terminal continuation can contain 512 bytes, not only 508.
Tests exercise 506..511/1014..1019 boundaries, noncontiguous and backward
acyclic chains, assigned empty fields and exact logical NUL bytes. Invalid
header/payload/pointer reads, a cycle to the first page, incomplete records
and present-but-incomplete pairs now raise rather than producing empty text.
Invalid memo/table source jobs preserve every published byte, discard only
their stage and allow a successful retry with a backup after input repair.

[COMMON.PAS](https://github.com/alisoss/pcfand/blob/master/pas/COMMON.PAS)
`WrStyleChar` changes attributes for styles and writes ordinary characters
unchanged. Removed the converter's double-table glyph translation. Comparing
the old/new complete documents permits only the inverse of that former
translation: authored frame cells change in contexts 3038 (Ultima 7 - Serpent
Isle), 3501 (Root) and 3667 (Upozornění). All 3,672 topic IDs/titles/tags,
aliases, navigation, Contents/index and the exact 252 link targets stay intact.
All 7,061 assigned memo references decode, including the internal help that
was still excluded from publication in this earlier pass. The
datasheet's reference payload algorithm is independently executed on the
same memo fields. The 250-line standalone export example was replaced with
structural validation and byte examples; it is not part of a source format.

Publication verification on 2026-10-13 rebuilt the five Game-Cheater bundles
through the staged server API. All 253 catalog entries and all 248 unselected
bundles remain unchanged, as do all 495 source files. Only the three identified
topics change content; the other export difference is the generator's existing
version/date metadata (`1.0.0` to `2.1.0.dev0`), not a source-format change.
The preceding generation is retained in
`data/.helps-previous-72665a3944234abaabc96c850080da62`. The public datasheet and
converter documentation were published through the managed document copier.

## 2. Source / Download

The analyzed database files come from **Game-Cheater 9.02**.

Download / catalog page:

```text
https://www.slunecnice.cz/sw/game-cheater/
```

Known information about the program:

```text
Name:      Game-Cheater
Version:   9.02
Author:    Jiří Kalous
License:   Freeware
Language:  Czech
Platform:  MS-DOS / Windows
Archive:   instgc.zip
```

---

Historical behavior: THelpViewer normalized every table starting with a
double top border to double borders throughout. The literal-frame audit
above removes that conversion; both source and published glyphs are preserved.

---

Historical heuristic, superseded by the native lookup audit above:
in user-facing `GCHLP` topics, Ctrl-S underlining is also used for hypertext
targets. After all retained help records have topic ids, compare the visible
text of each underlined span with the decoded topic titles, case-insensitively
and with whitespace collapsed. A match should be exported as a link to that
topic while preserving the underline.

```text
Viz.: Ctrl-S "O programu" Ctrl-S
    -> [link:topic=<id>][u]O programu[/u][/link]
```

Not every underlined span is a link. If no help title matches, retain it as
ordinary underline formatting. If a title occurs more than once, the nearest
matching record in topic order is the best reconstruction of PC-Fand's local
help navigation.

---

THelpViewer exports the user-facing groups as separate UHF bundles:

```text
cheaty.json.gz               CHEATDBS
firmy.json.gz                FIRMY
internetove-adresy.json.gz   GCNETADR
napoveda.json.gz             complete GCHLP, with native empty-record aliases
informace.json.gz            DBSNFO and GCPRM metadata
```

---

## 16. Recommended Export Model

For practical use, the extracted Game-Cheater database can be represented as JSON.

## 16.1 Cheat Entry

```json
{
  "title": "04X - Alien Eliminator",
  "publisher": "",
  "source": "WWW.CHEATY.SK",
  "version": "9.02",
  "text": "Uvedená písmena stiskněte najednou pro daný efekt..."
}
```

## 16.2 Company Entry

```json
{
  "company": "3D Realms",
  "text": "E-mail: help@3drealms.com\nWWW: http://www.3drealms.com/..."
}
```

## 16.3 Internet Address Entry

```json
{
  "name": "Alis",
  "url": "http://www.alis.cz",
  "description": "Stránka autorů PC-Fandu -> zajímavosti, demo verze atd."
}
```

## 16.4 Help Entry

```json
{
  "topic": "Root",
  "text": "Všeobecné informace o Game-Cheateru ver. 9.00..."
}
```

## 17. Implementation Notes

A robust extractor should:

```text
validate all offsets before reading
treat offset 0 as missing text
reject malformed or truncated referenced text blocks
decode text with CP852, not UTF-8 or Windows-1250
keep original offsets in exported metadata for debugging
preserve Czech and Slovak text in UTF-8 output
handle negative record counts by using abs()
validate stored counts against complete physical slots
retain the marker-delimited internal PC-Fand help range in the same namespace
resolve Ctrl-S captions by the first native name/mask match
forward matching empty memos to the following text without another name comparison
preserve source single/double box characters
export CHEATDBS source and publisher fields as structured topic tags/facets
```

Recommended output encoding:

```text
UTF-8
```

Recommended interchange formats:

```text
JSON
CSV
Markdown
SQLite
```

---

Do not classify a repeated sequence such as `0xB5 0xB5 0xB5` as box drawing
only because the bytes are adjacent. Interpret a contiguous run of conflicting
bytes as box drawing only when that same run also contains an unambiguous box
byte; otherwise decode it normally as CP852. This preserves strings such as
`DDDLLLOOOUUUHHHÁÁÁ` without damaging actual PC-Fand tables.

## Help Source Text Format

**Historical consumers:** FBHF compiler (`TVHC.PAS`) and independent Python compiler/decompiler experiments.
**Not used by:** Pascal HLDC decompiler (uses `;SCREEN` only for THELP/S602).

---

Earlier Python THELP experiments recorded exact round-trip metadata beyond
the minimal Borland source syntax. Those compiler/decompiler scripts are not
part of this repository's current converter. The comparison below is historical
research, not a supported decompile/recompile API or a current byte-identical
rebuild guarantee. Current exports are HTML, UHF JSON bundles and Markdown;
see [Converter](Converter.md).

---

## 6. Format Differences: Python vs Pascal Decompiler

The two decompilers produce slightly different output for the same input:

| Feature             | Python (`hldc.py`)              | Pascal (`HLDC.PAS`)              |
|---------------------|---------------------------------|----------------------------------|
| Line endings        | LF or CRLF output               | CR+LF                           |
| FBHF support        | Yes (full)                      | No                               |
| Screen numbering    | 0-based (S602)                  | 1-based (S602)                   |
| `.topic` directive  | Yes (FBHF)                      | No                               |
| Title underline     | No (S602)                       | Yes, `▀▀▀` line (S602)          |
| S602 blank lines    | Collapsed with text             | Preserved with blank lines       |
| Trailing spaces     | Stripped                        | Preserved (padded to line length)|
| THELP exact round-trip metadata | Yes                  | Partially preserved              |
| S602 `{}` links     | Identical format                | Identical format                 |
| Rebuild capability  | FBHF: yes, THELP: yes, S602: no | THELP text output for HL.EXE, S602: no |

Both decompilers produce the same `{link text:target}` syntax for S602
inline links and the same `;KEYWORD` syntax for THELP keyword records.

---

## 7. Historical compilation workflow

### 7.1 Creating an FBHF Help File with the original compiler

1. Write a `.txt` source file with `.topic` directives and `{xref}` markup
2. Run the separately obtained native compiler: `TVHC source.txt output.hlp [output.pas]`
3. The optional `.pas` file contains `hcXXX` context constants

The native compiler is not a server dependency or a current converter command.

### 7.2 Round-trip research limits

The independent FBHF/THELP experiments used scripts named `hldc.py`,
`tvhc.py` and `thelp_compile.py`; none is shipped here. Exact-rebuild claims
require those tools and the original sample evidence, not just accepting a
source file. If you want a THELP source file intended primarily for
Borland `HL.EXE`, stick to the documented subset and avoid relying on
` ;TEXTCOMPLETE`.

Software602 compilation is not currently supported by any tool in this
project.

---

*Part of the THelp Viewer project. See [format index](../FORMATS.md) for binary format documentation.*
