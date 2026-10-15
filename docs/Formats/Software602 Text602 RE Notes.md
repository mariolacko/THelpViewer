# Software602 Text602 RE Notes

Internal historical analysis and converter behavior, not the source-format
specification. Some statements describe earlier implementations; use the
corresponding datasheet for current byte-field definitions.

## Native HELP screen-font proof (2026-10-11)

This supersedes the partial glyph/mode assumptions below, not the already
verified paragraph fields or cross-reference positions. Text602 3.1's matched
package has T602.DRV SHA-256
`b85fc83e6e2dd7318fef29b5c8e79530da835eb0bcc3040566bac7385718cbb7`.
Its plain screen font is 256 8×15 glyphs at byte 11668 (2D94h), SHA-256
`9cd78ebc40327cef1a6e05aa834bb6b3247b71e4c10662d229f0dbf0696c14aa`.
The internal graphics-editor font at T602.EXE 01372Fh is not the low-code
screen font. SCRR602.FON is a replaceable editor font resource; external
CZECHVGA/CZECHEGA NRM/SMC keyboard fonts are not HELP glyph assignments.

The previously rejected OS-DOS `c602.exe` SFX can be read as
data despite its inconsistent ZIP headers. Its local ZIP member C602.IMA
uses raw deflate, expands to exactly 1,474,560 bytes and matches the stored
CRC32 89F9D8B9. The FAT12 disk contains CALC_D1.PAK: consecutive LE32
compressed-member byte counts, each followed by its own LZSS stream. The
first member is C602.DRV, second C602.EXE, third C602.HLP. Window size
4096, initial spaces/cursor FEEh, LSB-first flag groups, literal bit=1;
two-byte matches use offset=lo|((hi&F0h)<<4), length=(hi&0Fh)+3. Overlapping
copies feed the same ring. Bounded decoding consumes all 162 members and
905,461 packed bytes; no native installer or DOS executable is launched.

The recovered HLP is exactly the installed 211,493-byte CRC 667F1E22 source,
SHA-256 `6f730a0b3a55881bc4736d6070ee030843db3012d6b39db4f164834320008920`.
There is no additional HELP revision to register. Recovered C602.EXE has
732,089 bytes, SHA-256
`67a51509901137aef80a96964b886a7f957508a5f27b4447643b2c47ef323bb8`;
C602.DRV has 68,306 bytes, SHA-256
`6d585d7ae257ae17d649ae519353d8b498d9ba0ddb1719335c01724f2c8f84b7`.
Its screen font at 5F41h has SHA-256
`44a12c6b3ba4273c5514e21df1234207c7ac787d9678888b628c54eb728bd090`.

All bitmap bytes for 20h..FFh match between both drivers and the earlier
K602/T6HLP built-in fonts. Text602/Calc602 differ only in low slots
02h/11h/12h/15h/16h. The only low glyph actually retained in these HLP
corpora is Calc602's final 1Ah, identical in both fonts and drawing `→`.
The normal high-font shape of 98h is `▀`, not `■`; ADh is the square.
E7h is always `│`, including title separators and isolated cells. Calc602
context 87 is an independent authored Czech/Slovak/math/Greek keyboard
chart consistent with every high-byte mapping. Low rounded corners are
07h/08h/09h/0Ah = ╭/╮/╰/╯; 0Bh is vertical. The two K602 0Ah body cells
retain their established lower-right corner. 99h..9Fh and FFh
share the tiny mid-line stroke of 8Ch, not blank glyphs (8Dh is blank).

NE relocation chains confirm HELP drawing calls:
- 24:3783 HelpViewer.Draw calls GetLine 24:2C74 and builds a cell buffer;
- 21:330B MoveStr copies every row byte literally with an attribute;
- 3:1994 TView.WriteBuf receives that same character/attribute row;
- UI kernels in segments 32/33 select glyph rows by the literal byte;
- 2:02E3 derives the thirteen-row mode by omitting scanlines 2 and 12.

A bounded Unicorn harness loads only segments 3/21/24/36/37, stubs palette
lookup and captures WriteBuf before owner/device I/O. It enters the original
Draw method on synthetic paragraphs, returning at a sentinel. All 255
non-CR byte values retain their cells, including graphics style selectors
02h/04h/13h: in this HELP format those are not text-mode switches. All
12,207 real source rows also retain identical literal bytes. This proves
font-byte identity, not the full application's palette/device pixel output.

After Unicode transcription and the deliberate readable-space projection
of FFh's non-breaking separator, there are no unknown glyphs in either
installed corpus. Each native glyph byte still corresponds to one output
character, preserving link coordinates. Pure 76/77-cell authored rule rows
retain the existing UHF rule representation; other 98h cells draw `▀`.
Rare unused low boxed-key/revision-dependent symbols remain explicit
unknown cells, not CP437 faces or silently discarded selectors.

Native-draw/font corpus fixtures serialize
`[object_offset, [[global_start, consumed_end, unicode_row], ...]]` as compact
UTF-8 JSON, ensure_ascii=False:
- Text602: 5,802 rows / 187,010 cells, SHA-256
  `c3913e81f8a55d2553b166787d93f64f5317e3a9e901b233c0ecdddf82921a5c`;
- Calc602: 6,405 rows / 192,409 cells, SHA-256
  `098c78336e9247b6aef0b70a71f7f79e68b18ff682376a91e3f19f11aebdf1a2`.
Research artifacts stay outside the repository; only specifications, shared
transcription, tests and release notes are published. The title transcription
uses real `│` glyphs now; native contexts and references are unchanged.

## Native paragraph and cross-reference proof (2026-10-11)

This section supersedes the chunk/control interpretation, including the
seven-byte "screen prefix" explanation in the earlier audit below. The body
is TStream object persistence: 2710h, paragraph count, repeated Size/Wrap/Text,
reference count and five-byte references. Only text is encoded byte+1.
The native T602.EXE is the matching OS-DOS 3.1 artifact identified below.
It has an NE protected-mode image; segment 24 starts at file 08E300h.
NE relocation records identify these routines and their internal calls:

| Segment:offset | Function/evidence |
| --- | --- |
| 24:28E6 | Load paragraphs: signed count, WORD Size, BYTE Wrap, exact Text bytes |
| 24:288A | Decode: decrement every text byte modulo 256 |
| 24:2859 | Encode for Store: increment every text byte |
| 24:29CA | Load reference count and count*5 bytes |
| 24:3081 | GetLine: CR scan, Wrap, whitespace backtracking and Pascal row copy |
| 24:2B58 | GetCrossRef: START offset; column = Offset - previous consumed offset - 1 |
| 24:322C | Index Load: read slot count and allocate/read count*4 bytes |
| 24:32D7 | Index lookup: context*4; invalid context returns FFFFFFFFh |
| 24:336A | Header: expected 41-byte stamp, size/index DWORDs, first object at 49 |
| 24:355F | GetTopic: exact index lookup, then TStream.Get |
| 24:35CD | Missing-topic response constructed by the application |

The standalone trace harness loads only code segments 24/36 and data segment
37 into bounded Unicorn 16-bit memory. It patches NE internal relocations,
enters the decoder/GetLine/GetCrossRef routines directly, stops at a sentinel
return and never starts the application, DOS I/O or DPMI. Pascal short-string
copy is the original 36:4162 code. Native byte decoding matches all 256 values.

With width 78, every paragraph's consumed byte intervals and displayed row
bytes match native execution. Every stored cross-reference's context,
column, one-based row and length matches native GetCrossRef too:

| File | Physical objects | Paragraphs | Rows | References |
| --- | ---: | ---: | ---: | ---: |
| t602_310.hlp | 188 | 1992 | 5802 | 1170 |
| C602.HLP | 275 | 2088 | 6405 | 1065 |

Compact-JSON SHA-256 proof fixtures:
- Text602 rows: `a50705aac6ecd025d1ad5ed94fc586a32096661b5a98a9d8ba70c096686fd420`
- Text602 refs: `e1a41a237da3b951362f5b3132e59c3009794e3bc489d042c94e3db0d86485cd`
- Calc602 rows: `ed0fc9494bc77285a9b29b32bf7aaee6cf9148467eebee5eb3e1c850640b28ff`
- Calc602 refs: `2b15d865ac198148283e3d77d1fccb66eebf385bbd4998451e48450a0737ca7f`

Rows serialize as `[object_offset, [[global_start, consumed_end, row_hex], ...]]`.
References serialize as `[object_offset, [[context, column, row, length], ...]]`.
The proof is byte layout and reference positioning, not Unicode/pixel output.
All 4,080 paragraphs additionally match native GetLine at widths 20, 50 and
100, confirming Wrap and FF behavior independently of the export width.
External CZECHVGA.NRM/SMC files are Kamenicky terminal fonts, not proof of the
graphics-mode font used for these internal paragraph bytes. Prior Unicode
assignments remain partial; do not substitute the K602 graphics table blindly.

There are no stored 06h/07h line-break controls or unknown three-byte edge
attributes in these corpora. The supposed controls were Size/Wrap headers.
For example, `4F 00 00` means a 79-byte non-wrapping paragraph, not a title
suffix/marker; `0E 00 01` means Size=14, Wrap=1. Rules, titles, footer text
and embedded keyboard headings are normal authored paragraph text.

The real 188 Text602 objects include one unindexed object at 55003, retained
in UHF as 120539. Shared native indices are 64/150, 107/143, 120/151 and
Calc602 52/53. Use native primary contexts and these genuine aliases; old
physical sequential IDs and invented keyboard subtopics have no compatibility
aliases. All text of those keyboard sections remains in its true parent.
The final Calc602 paragraph contains stored 1Bh (decoded 1Ah) before its
trailing space. Native GetLine retains it; conversion must not strip it as
a guessed source-EOF control. Text602 context 99 contains a genuine stored
reference labeled `Zaměnit` targeting 99 itself; retain the source target
rather than replacing it by caption similarity to context 98.

Both families now use one bounded THelpTopic field reader with FBHF. A
corrupt paragraph/count/reference cannot publish partial text. Shared UHF
spans preserve punctuation, brackets and labels crossing row boundaries.
All 1170/1065 original references render, without extra guessed links.
The fixed 78-column UHF projection matches this native layout; dynamic
paragraph reflow and complete font mapping remain separate follow-up work.

## 2026-10-11: complete EOF anchor arrays

The historical sections below are superseded on anchor addressing. The WORD
at table `+2` is a slot count, not an array byte length: Text602 has 360 slots
and Calc602 280. The table ends exactly at EOF after `4 + 4*count` bytes.
Text602 has 190 populated slots / 187 distinct addresses; Calc602 has 276
populated slots / 275 distinct addresses. Reading only one quarter caused
the false conclusion that higher IDs were absent from the HLP. All of the
former fixed mappings, including card-file contexts 301–355 and Contents /
Index, are present at ordinary native addresses. The executable's HelpCtx
status descriptions are corroborating UI information, not a second lookup
required for decoding those destinations.

Every populated address begins `10 27`, with a seven-byte control prefix and
`0E` at `+7`; text begins at `+8`. Exact lookup replaces `offset-33` and
nearest-part rounding. Both header address/size fields are DWORDs; header
CRLF plus 15 bytes locates the body even if a field contains `0E`. The first
DWORD counts bytes following itself through EOF. The seven-byte sequence
after a local link array can be the next screen's prefix, not a per-table
destination namespace.

The independently downloaded OS-DOS Text602 3.1 package
(`https://www.osdos.net/download/t602/t602_31.exe`, linked from
`https://www.osdos.net/download.htm`) contains `T602/T602.HLP` identical to
the installed source: SHA-256
`908972ae2d9a8663586aaadeecd06dc7d229d4723dbfe59cbf628c6866acfc14`.
Its T602.EXE SHA-256 is
`a7ece581e214e5e2ff6f7c88f0d859df716154cc5d7a93a687514b731da20d0c`.
No additional source revision was added for that duplicate. The fetched
OS-DOS C602 SFX has malformed ZIP headers; no extracted edition was accepted
or registered from it. Installed C602.HLP SHA-256:
`6f730a0b3a55881bc4736d6070ee030843db3012d6b39db4f164834320008920`.

Parsed source-anchor pairs `(context, prefix_offset)` SHA-256 digests
(compact JSON, ordered native slots):
- Text602: `fbf10e5fb8c2dfef81cdd32a88b24c2a26fdf55851961126bb42e398313559f1`
- Calc602: `5b2847bb359c2ea1c0a1eec44976605045a9370657438ab8a575681c45546fff`

Text602 keeps all 196 titles/physical topic IDs. Calc602 now has 275 physical
topics, retaining all 149 previous titles and adding 126: 122 error screens,
two printing screens, the terminal-functions screen and one separate section.
Error screens lack underline/footer patterns; printing rules have 76 cells.
Anchors determine their boundaries and prevent speculative binary reassembly
from swallowing following errors. The table starts within Calc602's final
apparent chunk, so decoding must stop at its absolute offset rather than
printing its DWORDs as body text.

Removed fixed caption/occurrence maps and unknown-ID caption guessing.
Known native ID resolution is exact by source address; incomplete populated
anchors fail conversion and staged server publication leaves existing bundles
intact. Existing hotspot-position/edge-control and unannotated navigation-line
heuristics remain separate follow-up work. This pass verifies source structure
and mappings, not native pixel output or the complete original printer.

# Software602 Text-Family Help Format

> Created: 2026-04-03 · Last updated: 2026-09-19

Used by: Software602 word-processor and spreadsheet products.

Known header variants:
- `Text602 - help  v.3.1   (c) Software602` — Text602 word processor
- `Calc602 - help  v.1.00  (c) Software602` — Calc602 spreadsheet

This document describes the currently reverse-engineered chunk-based format
shared by both products.  It is structurally different from the classic
`M602 HelpSystem` format and does not use XOR `$FA` encryption.

Current repository validation samples:
- `t602_310.hlp`
- `C602.HLP`

Earlier reverse-engineering notes in this document may still reference older
but equivalent sample names such as `T602_301.HLP` or `C602_152.HLP`.

## Current Status

Confirmed so far:

- visible text bytes are stored with a `+1` offset before decoding
- the body is a stream of `0x0E`-delimited chunks
- titles are followed by a 77-byte underline chunk filled with `0x99`
- most titles are followed by a 3-byte `S602SCREENMETA` record
- bytes `0x06` and `0x07` inside text chunks are in-chunk line separators
- visible menu/link text is paired with separate binary metadata chunks

## File Header

The file starts with a printable ASCII header string terminated by the first
`0x0E` byte:

```text
Text602 - help  v.3.1   (c) Software602\r\n<15 binary bytes>0x0E
```

The 15-byte binary section immediately after the `\r\n`
contains:

| Offset | Size | Interpretation |
|--------|------|----------------|
| 0      | 3    | LE24 ≈ file_size − 45 (unknown exact meaning) |
| 3      | 1    | Unknown (observed: `00`) |
| 4      | 3    | **LE24 — absolute file offset of the anchor table** (magic `0x2711`) |
| 7      | 2    | LE16 — always `0x2710` (10000) in observed samples |
| 9      | 2    | Unknown |
| 11     | 3    | **File-level S602SCREENMETA** (same 3-byte format as per-screen record) |

The file-level S602SCREENMETA at bytes 11–13 follows the same rule as the
per-screen variant: byte 2 (flag) = `0x01`, and bytes 0–1 as LE16 equal the
raw length of the very first chunk minus 2.

Confirmed on current samples:
- `t602_310.hlp`: file-level screen meta `1b 00 01` → LE16=27, first chunk len=29=27+2
- `C602.HLP`: file-level screen meta `09 00 01` → LE16=9, first chunk len=11=9+2

## Chunk Model

The outer structure is:

```text
chunk 0 | 0x0E | chunk 1 | 0x0E | chunk 2 | ...
```

The primary storage unit is an `0x0E`-delimited chunk. The `0x0E` byte is
the definitive record separator — it can never appear in encoded text because
the `+1` offset encoding means that any text byte with visible value `0x0E`
would be stored as `0x0F`. Raw `0x0E` is therefore unambiguous as a delimiter.

Observed chunk families:

- title chunk
- 77-byte underline chunk (`0x99` × 77)
- 3-byte `S602SCREENMETA` control chunk (after title+underline)
- visible text chunk (may contain in-chunk line separators)
- binary link/menu metadata chunk
- 3-byte or 2-byte `S602MARK` in-body control chunks

## Text Encoding

Visible bytes are stored with a `+1` offset:

```text
visible_value = stored_byte - 1
```

ASCII bytes below `0x80` mostly decode after subtracting `1`. High bytes use
Text602-specific mappings layered over Kamenický plus separate handling for
box-drawing characters.

### In-chunk line separators

Bytes `0x06` and `0x07` inside text chunks act as **in-chunk line
separators**. They are raw control bytes (no `+1` offset applied) and mark a
line break within a single `0x0E`-delimited chunk.

The separator byte is immediately followed by one or more `0x00` bytes (which
decode as spaces) and then the next visible line content. The full pattern
observed in `T602_301.HLP`:

```text
...text... 07 00 00 21 2F 21 ...next line...
                              ^  ^  ^
                              |  |  next visible char
                              |  space (0x21 → val=0x20)
                       two leading spaces (0x00 → ' ')
```

Concrete examples from chunks 470–472 (dialog button descriptions):

```text
chunk 470: "Tlačítka v rámečku mají následující výstřihem: [07]   . Ano"
chunk 471: "Cílový soubor se přepíše zdrojovým... [06]   . Ne"
chunk 472: "Aktuální soubor se nebude kopírovat... [07]   . Vše"
```

Each yields two separate output lines. When a `0x06`/`0x07` byte appears at
the very end of a chunk (followed only by `0x00` bytes), it is stripped by the
trailing-control cleanup and produces no newline.

## Screen Structure

Each screen consists of:

1. **Title chunk** — text ending with `0x00 0x00`
2. **Underline chunk** — 77 × `0x99`
3. **S602SCREENMETA chunk** (3 bytes, optional) — screen metadata
4. **Body chunks** — visible text, binary link data, S602MARK records
5. **Footer chunk** — text containing `Rejstřík` / `Obsah` or similar
6. **Footer separator** — 77 × `0x99` (same underline format)
7. **Post-footer link chunks** (optional) — binary navigation metadata

## S602SCREENMETA Record

The 3-byte record immediately after the title+underline pair. Emitted in HLX as:

```text
;COMMENT S602SCREENMETA <hex6>
```

Example: `;COMMENT S602SCREENMETA f30001`

### Byte layout

All three bytes are emitted as raw hex. Known interpretation:

```text
byte 0–1  (LE16): value related to screen content length (see below)
byte 2:           screen access type (0 or 1 in observed data)
```

**Important:** this field split is our reverse-engineering interpretation,
not a confirmed format definition. The raw hex is what matters for round-trip
reconstruction.

### Byte 2 — screen access type

| Value | Observed meaning |
|-------|-----------------|
| `0x01` | **Context-sensitive help screen.** Directly accessible via F1 key while the corresponding command or dialog is active in the application. |
| `0x00` | **Reference / navigation screen.** Keyboard shortcut tables, table of contents, alphabetical index, application menu overviews. Not reachable via F1 context help. |

Distribution:
- T602_301.HLP: 180 × `0x01`, 14 × `0x00`
- C602_152.HLP: 146 × `0x01`, 1 × `0x00`

### Bytes 0–1 — content length hint

**When byte 2 = `0x01`:** LE16 value equals the **raw byte length of the
first body chunk minus 2** (the `−2` subtracts the two trailing `0x00` bytes
that close every chunk):

```text
LE16(byte0, byte1) = len(first_body_chunk_raw) - 2
```

The first body chunk contains the one-line summary sentence of the topic. Its
raw length is stored here so that the help viewer can calculate where the
remaining body content and link hotspots start in the rendered screen buffer.
The viewer renders this summary as a lead line followed by one blank line.

Verification against `T602_301.HLP` (byte-2=`0x01` topics):

| Topic | LE16 | first_raw−2 |
|-------|------|-------------|
| Soubor \| Nový | 33 | 35−2 = 33 |
| Soubor \| Otevření \<F3\> | 30 | 32−2 = 30 |
| Soubor \| Uložit \<F2\> | 38 | 40−2 = 38 |
| Soubor \| Tisk | 16 | 18−2 = 16 |
| Edit \| Smazat slovo | 88 | 90−2 = 88 |
| Blok \| Sloupcové bloky \<Ctrl-KN\> | 37 | 39−2 = 37 |

Confirmed for all 180 byte-2=`0x01` screens in T602_301.HLP.

**When byte 2 = `0x00`:** LE16 meaning is **not yet determined**.

Earlier analysis suggested LE16 ≈ total rendered visible character count. This
holds approximately for some keyboard-reference screens, but breaks completely
for large navigation screens:

| Topic | LE16 | approx body vis |
|-------|------|-----------------|
| Základní klávesové povely | 939 | 924 |
| Klávesové povely pro přesun v textu | 2145 | 2112 |
| **Text602 \| Obsah** (TOC) | **38** | ~3200 |
| **Text602 \| Abecední rejstřík** (index) | **3153** | ~4700 |

The TOC screen (LE16=38, ~215 output lines) disproves "total visible character
count" as a general rule. The true meaning is unknown.

### Note on uniqueness

The 3-byte raw value is **not** a unique screen identifier. The same bytes can
occur on unrelated screens (e.g. `d6 01 01` appears on multiple screens).

### S602SCREENMETA split by the chunk delimiter

In `T602_301.HLP`, two screens (`Řádka | Vložení času <Alt-C>` and
`Řádka | Políčko`) appear after splitting as an empty chunk followed by
`00 01`. Their complete metadata record is `0e 00 01`: its first byte equals
the outer `0x0E` chunk delimiter and is therefore consumed by the split. The
LE16 value `0x000e` matches the following first body chunk length minus two.
An extractor must reconstruct this record instead of emitting the empty chunk
as a visible blank line.

## S602MARK Records

In addition to the S602SCREENMETA record after the title+underline pair,
the file contains 3-byte and 2-byte chunks scattered throughout screen bodies.
These are **display or navigation attribute markers** for the help viewer.

The decompiler preserves them as `;S602MARK <hexbytes>` at their exact
position in the HLX stream, so a future compiler can reconstruct the original
binary exactly:

```text
;S602MARK 130000

■ {Rejstřík:Text602 | Abecední rejstřík nápovědy.}  {Obsah:Text602 | Obsah}
;S602MARK 4f0000
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
```

Known sub-types:

| Raw bytes | Count (T602) | Position |
|-----------|--------------|----------|
| `4f 00 00` | 186 | between footer text and footer separator |
| `13 00 00` | 128 | immediately before the footer text chunk |
| various 3-byte | ~117 | intra-body: section markers in keyboard-table and TOC screens |
| `00 00` | 7 | before section heading (`■ ...`) in body text |
| `00 01` | 4 | 2 are anomalous variant S602SCREENMETA; 2 are inline body markers |

The `13 00 00` / `4f 00 00` pair brackets the standard footer on almost every
screen. They are likely **display-attribute or link-bank markers** that tell the
viewer to render the footer in a different color or handle the Rejstřík/Obsah
link targets specially. The exact meaning of the value bytes is not confirmed.

The 2-byte `00 00` / `00 01` chunks that appear between text chunks (not
adjacent to binary link data) are section-boundary markers. They are
preserved as `;S602MARK 0000` / `;S602MARK 0001` in the HLX.

Note: some 2-byte chunks adjacent to binary link data (`03 00`, `04 00`,
`00 01` after a binary block) are **split link records** caused by the outer
`0x0E` delimiter cutting through a binary link chunk. These are correctly
joined by `_parse_link_chunk_sequence` and do not appear as `;S602MARK` markers.

### Title chunks must not be linkified

The `_apply_link_chunks` position-mapping algorithm must exclude title and
separator items from the `visible_positions` list. If title items are included,
link records whose hotspot position falls within the title's character range
will incorrectly insert link markup into the title text, corrupting it and
making it unmatchable as a link target from other screens.

## Binary Link And Menu Metadata

Text602 links are not stored as inline text markers. Instead, many
navigation/menu areas have separate binary chunks nearby.

Partially reverse-engineered structure:

- many binary navigation chunks begin with a 16-bit little-endian `count`
- that is followed by `count` records of 5 bytes

Current working interpretation of one 5-byte record:

| Offset | Size | Meaning                       |
|--------|------|-------------------------------|
| +0     | 2    | destination id                |
| +2     | 2    | rendered-buffer hotspot position |
| +4     | 1    | highlighted text length       |

Example from the `Soubor | Nový` topic:

- first link chunk contains:
  - `(id=9, pos=400, len=7)`
  - `(id=3, pos=411, len=6)`
  - `(id=18, pos=421, len=7)`
  - `(id=20, pos=432, len=3)`
  - `(id=21, pos=439, len=5)`
  - `(id=112, pos=448, len=8)`
  - `(id=111, pos=458, len=5)`

The first field is the destination id. For normal topic/menu links this often
matches an entry index in the late anchor table. In the same example:

- `9` -> `Soubor | Otevření`
- `3` -> `Okna | Zavřít`
- `18` -> `Soubor | Manažer`
- `20` -> `Soubor | DOS`
- `21` -> `Soubor | Konec`

The repeated footer ids are special:

- `112` behaves as the global `Rejstřík` link
- `111` behaves as the global `Obsah` link

In `T602_301.HLP`, each of those ids appears in `157` link records.

Observed footer text forms in the sample:

- the common in-topic footer is `■ Rejstřík  Obsah`
- the final tail footer before the late lookup tables is `■ Obsah nápovědy`

The second field is not the destination. It is a position in the viewer's
rendered buffer. The exact coordinate origin differs between ordinary screens
and the large navigation screens, so it must not be treated unconditionally as
the hotspot end. The third field is the exact clickable label length.

Important notes:

- the destination id namespace is wider than the anchor table
- ids above the anchor table range (e.g. T602 `91..120`, C602 `70..154`) are
  special fixed IDs resolved internally by the viewer
- some IDs appear hardcoded in the viewer (e.g. `111/112` for Rejstřík/Obsah)
- link hotspot positions are in the **viewer's rendered buffer**,
  which includes title+underline as the first content

### Application-owned `HelpCtx` IDs

High T602 destination IDs must not be resolved by fuzzy title matching. They
are application context IDs and are not present in the HLP anchor table. The
matching original `T602.EXE` contains a named `HelpCtx` resource with 39
records. Each record is three little-endian words:

```text
first_context_id, context_count, first_status_string_offset
```

For example, `(339, 14, 5901)` describes IDs `339..352`. Its consecutive
length-prefixed status strings identify the card-file commands and menus. They
confirm, among others:

| ID | Status text / meaning | HLP target |
|----|-----------------------|------------|
| 339 | file operations | second `Menu Soubor` family |
| 340 | data editing | second `Menu Edit` topic |
| 341 | display options | `Menu Zobrazit` |
| 342 | form selection/design | `Menu Formulář` |
| 343 | record operations | `Menu Záznam` |
| 344 | open the editor window | `Text602 \| Editor` |
| 345 | go to start/end of the database, etc. | second `Menu Jdi na` topic |
| 349 | find a database record | second `Jdi na \| Najít` topic |
| 350 | find the next database record | card-file `Jdi na \| Další` topic |

Several editor and card-file screens deliberately have identical titles. A
converter must therefore preserve the title occurrence as part of its internal
target key; a plain `title -> topic` dictionary incorrectly sends card-file
links to the first editor topic. The original title shown to the user remains
unchanged.

An extractor processing another executable/HLP pair must read that
executable's `HelpCtx` resource or provide an exact version-specific context
map. The HLP file alone cannot derive application-owned destination IDs.

### Buffer position model

The viewer counts bytes sequentially (no `+1` per chunk boundary):

```text
buffer_pos = sum(len(chunk_N) for chunk in [title, underline, body...])
```

S602SCREENMETA (3-byte context chunk) is a control code and does NOT
contribute to the buffer position. The 0x0E delimiter bytes are not counted.

Both local and large navigation link tables use the same count-prefixed
container. The difference is only their size and how often an embedded `0x0E`
splits them into outer chunks:

- `Text602 | Obsah`: count `178`, followed by `178 × 5` bytes and a 7-byte trailer
- `Text602 | Abecední rejstřík`: count `168`, followed by `168 × 5` bytes

For navigation tables, records and visible labels are stored in the same order.
The stored label length identifies the next linked visible label; visible rows
without a corresponding record remain plain text. This reconstructs all 178
Contents links without title matching.

Another important consequence of the outer `0x0E` chunk delimiter:

- local binary link chunks may themselves contain byte value `0x0E`
- when that happens, the outer splitter breaks one logical binary record into
  two or more adjacent chunks
- reconstructing the original local link chunk requires joining those adjacent
  binary chunks with literal `0x0E` bytes inserted between them

Confirmed examples from `T602_301.HLP`:

- chunks `1734 + 1735` reconstruct one valid local link chunk for
  `Makra | Definice`
- chunks `1769 + 1770` reconstruct one valid local link chunk for
  `Makra | Načtení`
- chunks `1787 + 1788` reconstruct one valid local link chunk for
  `Makra | Uložení`
- chunks `1805 + 1806` reconstruct one valid local link chunk for
  `Makra | Editace`
- chunks `2550 + 2551 + 2552` reconstruct one valid local link chunk before
  `Soubor | Otevření`

Concrete byte example:

```text
1734: 07 00 74 00 2C 03
1735: 75 00 3D 03 0B ...
```

These do not parse separately. But after reinserting the lost delimiter byte:

```text
07 00 74 00 2C 03 0E 75 00 3D 03 0B ...
```

the combined payload parses correctly as a 7-record local link chunk.

For screen-local navigation, one more rule is now strongly supported by the
sample:

- a parseable local link chunk placed after a footer separator and immediately
  before the next title belongs to the previous screen, not to the following
  title

Concrete evidence from `T602_301.HLP`:

- chunk `1503`, placed before title `Jdi na | Začátek souboru`, contains ids
  `91,92,93,95,96`
- that set matches the visible submenu of the previous topic
  `Jdi na | Konec bloku`
- it does not match the following topic, which would need `94` instead of `95`

Likewise:

- chunk `1519`, placed before title `Jdi na | Konec souboru`, omits `95`
- that matches the previous topic `Jdi na | Začátek souboru`
- and not the following one

## Link Chunk 7-Byte Trailer

All 157 link chunks in `T602_301.HLP` have a 7-byte trailer appended after
the 5-byte record array. The current decompiler discards it silently.

Observed structure:

```text
10 27 BB 00 GG 00 01
```

| Bytes | Field | Observed values |
|-------|-------|-----------------|
| `10 27` | Magic constant `0x2710` | Always `10 27` |
| `BB 00` | Link bank / namespace id (LE16) | Varies per chunk |
| `GG 00` | Unknown LE16 | Varies, often multiples of 0x0100 |
| `01` | Always `0x01` | Constant |

Examples:

- `10 27 0C 00 28 00 01` on `Soubor | Nový`
- `10 27 08 00 12 00 01` on `Blok | Řádkování`
- `10 27 0B 00 28 00 01` on `Menu Blok`

The effective link key appears to be `(trailer, raw_target)` rather than just
the 16-bit raw target, because the same end-position values appear in multiple
trailers with different bank ids.

For decompiler output, edge control triplets attached directly to text chunks
are currently preserved as:

```text
;COMMENT S602EDGEMARK PREFIX <hextriplet>[,...] SUFFIX <hextriplet>[,...]
```

This is used for cases where the last visible byte of the chunk would
otherwise leak into text as a bogus character, but the bytes may still carry
useful UI or navigation metadata.

Observed example: on `Text602 | Kalkulačka`, command lines such as:

- `C    vymaže displej`
- `N    změní znaménko čísla na displeji`
- `MC   vymaže obsah paměti`

carry edge markers like `380001`, `310001`, `250001`, `290001`. These do not
look like normal text terminators; they are likely action, hotspot, or other
UI metadata. At the current stage they should be preserved, not discarded.

## Anchor Table

The anchor table maps `dest_id → absolute file offset` of the target screen.
It is located via the file header binary section (bytes 4–6 as LE24):

```text
header_binary[4..6] LE24 = absolute file offset of anchor table in .HLP file
```

This pointer works for both T602 and C602. The file data at that offset must
begin with the magic `0x2711 LE16`.

### Anchor table format

```text
[11 27]         magic   LE16 = 0x2711
[NN NN]         nbytes  LE16 — total byte count of entry array
[entry0][...]   nbytes/4 entries, each a 32-bit LE file offset
```

Each 32-bit entry is an absolute file offset to the screen it represents.
Entry index N corresponds to `dest_id = N`. Invalid entries (pointing nowhere)
are stored as `0xFFFFFFFF`.

To resolve an entry:

```text
target_pos = entry_value - (header_end + 1 + 32)
             ≈ entry_value - 33   (approximately, see note)
```

### Location in file

| File | Location | Notes |
|------|----------|-------|
| T602_301.HLP | Standalone chunk 3738 | Aligned to a 0x0E chunk boundary |
| C602_152.HLP | 54 bytes inside chunk 4892 | Embedded mid-chunk; not chunk-aligned |

The hardcoded chunk-index approach only works for T602. The header pointer
approach works for both. The decompiler always uses the header pointer.

### Anchor table vs links

The anchor table is a **lookup table only** — it does NOT contain links.
Links (clickable hotspots) are stored in binary link chunks within each screen.
The anchor table is needed only to resolve `dest_id → screen title`.

### Anchor table size

| File | Entries | dest_id range |
|------|---------|---------------|
| t602_310.hlp | 90 entries (0–89) | 0x0168 bytes |
| C602.HLP | 70 entries (0–69) | 0x0118 bytes |

Dest_ids above the anchor table range (e.g. C602 dest_ids 70–154) are
**special fixed IDs** that the viewer resolves internally without consulting
the table. Common ones:

| dest_id | T602 meaning | C602 meaning |
|---------|-------------|-------------|
| 111 | Obsah nápovědy | Help \| Obsah |
| 112 | Rejstřík nápovědy | Help \| Rejstřík |
| 133 | — | Help \| Obsah (alternate) |
| 134 | — | Help \| Rejstřík (alternate) |
| 91–96 | Jdi na submenu items | — |

### Anchor table examples (T602)

- entry 9 → `Soubor | Otevření <F3>` (file offset 7244)
- entry 3 → `Okna | Zavřít <F9>` (file offset 7211)
- some entries point to non-title heading chunks that still behave as
  navigation destinations (e.g. `Blok | Začátek`, `Blok | Konec`)

## Calc602 Help File

`C602.HLP` uses the identical chunk format with a different header string:

```text
Calc602 - help  v.1.00  (c) Software602\r\n<15 binary bytes>0x0E
```

Binary header section (bytes after `\r\n`, 15 bytes):
`f8 39 03 00 c1 35 03 00 10 27 06 00 09 00 01`

| Offset | Bytes | Value | Meaning |
|--------|-------|-------|---------|
| 0      | 3     | `f8 39 03 00` (LE24) | ≈ file_size − 45 |
| 4      | 3     | `c1 35 03` (LE24) | 0x0335c1 = anchor table file offset |
| 6      | 2     | `10 27` | Always 0x2710 = 10000 |
| 8      | 3     | `06 00 09` | Unknown |
| 11     | 3     | `00 01` → `09 00 01` | File-level S602SCREENMETA |

- Anchor table at `0x0335c1`: magic `11 27`, 70 entries (`0x0118` bytes), **mid-chunk** (C602 differs from T602 where the anchor table is standalone)
- File-level S602SCREENMETA: `09 00 01` → LE16=9, first chunk len=11=9+2 ✓

Current observed parser totals on repo sample:
- `t602_310.hlp`: 196 screens
- `C602.HLP`: 149 screens

## Viewer UI Theme

Text602/Calc602 bundles carry a Software602-specific `metadata.ui` theme based
on the T602 3.00 screenshot colors:

| UI role | Color |
|---------|-------|
| Window/page background | `#005454` |
| Main text | `#a8fcfc` |
| Links | `#a8a800` |
| Frame, caption bar, scrollbar | `#a8a800` |
| Active title/close/zoom glyphs | `#005454` |

These values are stored as direct RGB colors, not CGA palette indices.

### C602 special dest_ids

C602 uses different dest_ids from T602 for its standard footer/navigation:

| dest_id | Usage | Appears on N screens |
|---------|-------|---------------------|
| 133 | Help \| Obsah (Contents) | 147 (every screen) |
| 134 | Help \| Rejstřík (Index) | 147 (every screen) |
| 78 | Soubor \| Zavřít or similar | 12 screens |
| 77 | Edit-related | 17 screens |

These IDs are above the 70-entry anchor table range and are resolved by the
viewer internally.

## What Is Still Unknown

The link-table container is decoded. What remains unresolved by the HLP alone
is the destination mapping for application-owned context IDs above the anchor
table range. Those IDs must not be mapped by fuzzy title matching; they require
an explicit mapping structure from the original input set or must remain
non-clickable.

## HLX Round-Trip Markers

The decompiler emits extra markers to enable lossless reconstruction of the
binary HLP file from HLX. These all begin with `;S602` and appear in specific
positions:

### File header (once per file)

```text
;S602ANCHORTABLE <hex>
```

The full raw anchor table bytes (magic `11 27` + `nbytes` + entry array),
extracted from the file at the offset stored in `header_binary[4..6]`.

### Per-screen link markers

#### Link format: `{label:target:dest_id}`

Links in HLX are stored as three-field syntax:

```text
{Rejstřík:Help | Rejstřík:134}
{Obsah:Help | Obsah:133}
{Zavřít:Okna | Zavřít <F9>:3}
```

Fields: `label` = clickable text shown to user, `target` = title of destination
screen (used for readable navigation and for anchor reverse-lookup), `dest_id` =
numeric ID from the binary link record (used directly during recompilation).

If `target` is empty (`{label::dest_id}`), the dest_id is used directly; the
target screen title is unknown but the link still compiles correctly.

If `dest_id` is absent (`{label:target}`), the recompiler must reverse-look up
`target` in the anchor table to find the dest_id.

#### Fallback: `;S602LINKIDS`

For dest_ids that could not be placed inline (position matching failed and no
pre-linkified text was found to upgrade), the decompiler emits:

```text
;S602LINKIDS 78 4 134 133
```

This preserves the raw dest_ids so the compiler can reconstruct the complete
link chunk even when the text hotspots are not annotated.

#### Trailer: `;S602LINKTRAILER`

When a link chunk contains the optional 7-byte trailer:

```text
;S602LINKTRAILER 10270c00280001
```

Format of the 7 bytes:
```text
[10 27]  magic 0x2710
[BB BB]  bank / link-namespace id (LE16)
[GG GG]  unknown LE16 (often multiples of 0x0100)
[01]     constant
```

---

## Known Decompiler Bugs Fixed (v2.6)

### 9. Link dest_id not preserved in HLX

Previously `{label:target}` (2-field). Now `{label:target:dest_id}` (3-field).
The dest_id from the binary link record is preserved inline. For unresolvable
dest_ids a fallback `;S602LINKIDS` comment is emitted. The 7-byte trailer is
preserved as `;S602LINKTRAILER`. The full anchor table is emitted as
`;S602ANCHORTABLE` in the file header. Together these enable lossless
round-trip recompilation.

### 10. Buffer position counting wrong

`_apply_link_chunks` did not include `kind='title'` items (title + underline)
when computing text buffer positions. The viewer includes title+underline in its
buffer, so all positions were offset by ~86 chars (42 title + 77 underline -
some overlap). Fixed: title items now contribute to `pos` accounting even though
they are not matchable targets.

Also fixed: `_raw_display_len` strips `{label:target:dest_id}` markup before
computing text length, so pre-linkified items don't inflate position offsets.

### 11. Separator chunk outside footer block added as visible

In some C602 screens (no footer text, just S602MARK + separator + links),
the separator chunk was not detected inside the footer block and fell through
to the main loop. `_decode_chunk` returns 77 × `▀` for separators, so it was
added as `kind='visible'`. This caused `_apply_link_chunks` to match link
hotspots inside the `▀▀▀...` separator line.

Fix: main processing loop now checks `_is_separator_chunk` explicitly and
adds it as `kind='separator'` (excluded from position accounting).

### 12. C602 character encoding overrides missing

Several characters were wrong in C602 output. The stored byte is still decoded
by subtracting `1` first; the values below are the post-subtraction byte values.

Confirmed Software602-specific remaps:
- `Ž` (e.g. `Ženatý`, `ŽENA`, `Životnost`): KEYBCS2 maps byte `0xFB` to `·`. Fixed by overriding `0xFA → Ž` (`\u017D`) in `TEXT602_TEXT_CHARS`.
- `Í` (e.g. `POUŽÍVAT`): KEYBCS2 maps byte `0xEA` to `Θ`. Fixed by overriding `0xE9 → Í` (`\u00CD`).
- `ď` in `buď`: `0xC4 → ď`.
- `ť` in `zvlášť`, `paměť`: `0xD4 → ť`.
- `Á` in `ZÁPORNÉ`, `TERMINÁL`: `0xE1 → Á`.
- `Ú` in `Úvod`, `Úrok`: `0xF5 → Ú`.
- `É` in `KLADNÉ`, `ZÁPORNÉ`: `0xF7 → É`.

These are Software602-specific remappings that differ from standard KEYBCS2.

Two symbols are intentionally left as decoded glyphs until the original
Software602 font/screen rendering is verified:
- `0xE0 → α` in a chart axis drawing.
- `0xF4 → ⌠` in a `Postup:` step line.

### 13. Box drawing detection failed for short chunks

`_looks_box_chunk` returned `False` for chunks < 20 bytes even when all
high-byte values decoded to box-drawing characters. Fixed: if every high byte
in the chunk decodes to a box-drawing character and there are at least 2 of
them, the chunk is classified as box mode regardless of length.

---

## Known Decompiler Bugs Fixed (v2.5)

### 7. Rename: TEXT602CTRL → S602SCREENMETA, CTRL → S602MARK, TEXT602EDGE → S602EDGEMARK

All marker names in the HLX output were our own invented labels. Renamed to the
`S602` namespace for clarity and consistency:

| Old name | New name | Output format |
|----------|----------|---------------|
| `;COMMENT TEXT602CTRL {val} FLAG {flag}` | `;COMMENT S602SCREENMETA {hex6}` | raw 3-byte hex |
| `;CTRL {hex}` | `;S602MARK {hex}` | raw hex |
| `;COMMENT TEXT602EDGE ...` | `;COMMENT S602EDGEMARK ...` | unchanged |

The S602SCREENMETA output format changed from parsed `{val} FLAG {flag}` to raw
hex — consistent with S602MARK. The internal FLAG byte is still read for screen
processing logic (FLAG=0 screens terminate on next title), but the HLX output
records the raw bytes without asserting a field interpretation.

### 8. C602 (Calc602) help format support

The decompiler previously only accepted headers starting with `b'Text602 - help'`.
`C602_152.HLP` starts with `b'Calc602 - help'` and was rejected with "Unknown
help file format!".

Fix: added `S602_CALC602_HDR = b'Calc602 - help'` detection. The `decompile()`
method now auto-detects the header length by finding the first `0x0E` byte,
instead of relying on the hardcoded `S602_TEXT602_FILE_HDR` constant. This
makes the decompiler work for any Software602 product using this chunk format.

---

## Known Decompiler Bugs Fixed (v2.4)

### 5. In-body control records silently dropped

All 3-byte chunks in screen bodies were silently skipped by `_is_context_chunk`
(which returns `True` for any chunk with `len == 3`). Short 2-byte control
records (`00 00`, `00 01`) that failed binary link parsing were also silently
dropped via `idx += 1`.

These records are required for faithful HLP reconstruction. The decompiler now
emits them as `;S602MARK <hexbytes>` markers at their exact position in the HLX
stream:

```text
;S602MARK 130000
■ {Rejstřík:...}  {Obsah:...}
;S602MARK 4f0000
▀▀▀▀▀▀▀▀▀▀▀▀...
```

Known sub-types preserved (434 total in `T602_301.HLP`):

| Bytes | Count | Position |
|-------|-------|----------|
| `4f 00 00` | 186 | between footer text and footer separator |
| `13 00 00` | 128 | before footer text chunk |
| `14 00 00` | 9 | inside screen body sections |
| `00 00` | 7 | before section heading (`■ ...`) in body |
| various 3-byte | ~100 | intra-body section / keyboard-table markers |
| `00 01` | 4 | in body (2 are anomalous variant S602SCREENMETA) |

### 6. Footer separator linkified

The `▀▀▀...` separator chunk at the end of the footer area was stored with
`kind='visible'` and therefore included in the `_apply_link_chunks`
position-mapping calculation. Link records whose hotspot end position fell
within the separator's 77-character range incorrectly inserted link markup into
the separator text:

```text
▀{▀▀▀▀▀▀:Soubor | Import}▀▀▀▀▀▀▀▀▀▀▀...
```

Fix: the footer separator is now stored with `kind='separator'`, which is
excluded from `visible_positions` in `_apply_link_chunks`, exactly like
`kind='title'`.

---

## Known Decompiler Bugs Fixed (v2.3)

### 4. FLAG=0 screens merged with following screen

When a byte-2=`0x00` (reference/navigation) screen contained no footer, the
next title chunk encountered during body processing was treated as a secondary
heading of the same screen rather than the start of a new screen. This caused
two pairs of screens to be merged:

- `Menu Text602 <Alt-T>` merged with `Text602 | Makra`
- `Text602 | Obsah` merged with `Text602 | Abecední rejstřík nápovědy.`

The two merged targets were referenced by 199 links that all resolved as broken.

Fix: `_process_screen` now checks the internal flag byte from S602SCREENMETA.
When a new title chunk is encountered in the body of a byte-2=`0x00` screen,
the current screen is closed and the new title starts a separate screen.

Result after fix: 194 screens, 0 broken links.

---

## Known Decompiler Bugs Fixed (v2.2)

### 1. In-chunk line separators stripped instead of emitted

Bytes `0x06` and `0x07` were treated as generic control bytes (decoded as
empty string). This caused text that the help viewer displays on separate lines
to be concatenated into a single output line. Fixed `_decode_byte` to return
`'\n'` for these bytes.

### 2. Incorrect `<Ctrl-KN>` → `<Ctrl-MD>` substitution

The decompiler contained a hardcoded string replacement that changed the
correctly-decoded keyboard shortcut `<Ctrl-KN>` to `<Ctrl-MD>`. Removed.

### 3. Title items linkified by `_apply_link_chunks`

The link-chunk position mapping algorithm included title and separator items
in its `visible_positions` list. When a link record's hotspot position fell
within the character range of a title item, the algorithm inserted link markup
into the title text. This corrupted three screen titles and caused 18 broken
links. Fix: title and separator items are now marked `kind='title'` and
excluded from `visible_positions`.
