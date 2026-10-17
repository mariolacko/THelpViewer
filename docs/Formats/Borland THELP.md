# Borland THELP Format

> Created: 2026-03-29 · Last updated: 2026-10-12

Used by: Turbo Pascal 4–7, Borland Pascal 7, Turbo C, Turbo Assembler, Borland Sprint,
Sidekick 2, Eureka. File extensions: `.HLP`, `.TPH`, `.TCH`, `.TAH`, and other
Borland `*.T?H` variants when the THELP signature matches.

Sidekick 1 `SK.HLP` is a separate uncompressed context/page stream; see
[Sidekick 1 Help](Borland%20Sidekick%201%20Help.md). Sidekick Plus uses separate
[paragraph directories and scoped hotspots](Borland%20Sidekick%20Plus%20Help.md),
not THELP records; accepting a `.HLP` suffix does not decode that format.

Turbo Basic's `TBHELP.TBH` shares the signature and version pair `1/1`, but
uses WORD record kinds/lengths, absolute-offset hotspots and space packing,
not the grammar below. Its exact stamp selects the separate
[Turbo Basic Help profile](Borland%20Turbo%20Basic%20Help.md). Version bytes
alone do not distinguish it from Eureka.

Assembler TAH files use the same record grammar when their THELP signature
matches. Examples include `formatVersion=5,textVersion=1` and
`formatVersion=52,textVersion=1`; the extension does not select the grammar.

Original implementation: THELP unit in Turbo Pascal runtime.  
Reference decompiler: HLDC 1.03 by Volker Pohlers (1994/2010).  
Borland references:
- Open Architecture Handbook 4.0, chapter `Borland Help System` (`BOA.TXT`)
- `DEHELP.C` / `DEHELP.DOC` from `BOA.BC3/DECOMP.ZIP`

`DEHELP` explicitly states support for BC++ 3.0 and Turbo Pascal help
systems only; Borland's Windows and some product-specific variants are
outside its supported set.

Turbo Debugger TDH has a separate big-endian runtime map and nibble stream;
see [TDH/TFH](Borland%20TDH.md). It does not have the THELP signature.

All multi-byte integers are little-endian.

BOA documents the core Borland Help binary model with record types `0..5`
and `formatVersion = 52` as the current baseline. Real files seen in the
wild extend this baseline, most notably with `RT_IndexTags = 6` in newer
`TPH/TCH` variants.

Observed divergence from the BOA baseline:
- some `formatVersion = 51` TCH files end with large trailing `0x20` padding
  after the last valid BOA-style record
- these tails are not a continuation of the normal record stream and should
  not be interpreted as additional records
- some `formatVersion = 51` TCH files also use context ids that have no
  standalone `RT_Text` record; their runtime destination is not established
  merely by finding an inline keyword that references the same ID

Some `formatVersion=51` contexts have offsets in trailing space padding,
rather than at a Text record. The documented Context/Index/Keyword structures
do not contain an additional explicit destination for those entries.
A Keyword occurrence supplies a source hotspot's position and target ID; it
does not by itself prove that the missing target is that source position.

The same padding limitation also occurs in the German Turbo Pascal 6.0/6.01
originals. A context pointing to padding has no directly addressed text record;
its runtime destination cannot be established from a similar-looking title.

### 1.1 File Layout

```
┌──────────────────────────────┐
│  Stamp (null-terminated)     │  e.g. "TURBO PASCAL HELP FILE"
├──────────────────────────────┤
│  $1A separator               │  1 byte
├──────────────────────────────┤
│  Signature (null-terminated) │  "$*$* &&&&$*$" (12 bytes + NUL)
├──────────────────────────────┤
│  Version Record              │  2 bytes
├──────────────────────────────┤
│  Record 0                    │  3-byte header + data
│  Record 1                    │
│  ...                         │
│  Record N                    │
└──────────────────────────────┘
```

### 1.2 Version Record (2 bytes)

| Offset | Size | Field           | Description                          |
|--------|------|-----------------|--------------------------------------|
| +0     | 1    | FormatVersion   | Binary format version                |
| +1     | 1    | TextVersion     | Content/text version                 |

**Known FormatVersion values:**

| Stored FormatVersion | Product / technical variant |
| --- | --- |
| 1 | Eureka |
| 2 | Turbo Pascal 4.0 |
| 3 | Borland Sprint |
| 4 | Turbo Pascal 5.0/5.5, Turbo C++ 3.0 |
| 4 with TextVersion 2 | Sidekick KATO; positional keyword variant |
| 5 | Turbo Assembler 2 |
| 51 | Turbo Pascal 6.0 |
| 52 | Turbo Pascal 7.0, Borland Pascal 7 |

The KATO variant is referred to as 4/2 below. Value 41 is not stored as
FormatVersion in that variant.

### 1.3 Record Header (3 bytes)

Every record begins with:

| Offset | Size | Field     | Description         |
|--------|------|-----------|---------------------|
| +0     | 1    | RecType   | Record type (0–6)   |
| +1     | 2    | RecLength | Payload size (Word) |

**Record types:**

| Value | Name          | Description                           |
|-------|---------------|---------------------------------------|
| 0     | FileHeader    | Global file parameters                |
| 1     | Context       | Screen number → file offset mapping   |
| 2     | Text          | Compressed screen text                |
| 3     | Keyword       | Hyperlink/keyword definitions         |
| 4     | Index         | Alphabetical index entries            |
| 5     | Compression   | Nibble compression character table    |
| 6     | IndexTags     | Named tags for index entries (≥v5)    |

BOA 4.0 explicitly lists only record types `0..5`. `RT_IndexTags = 6` is an
observed extension present in some Borland help files.

Record order is format-dependent:

- Format 2/3: `FileHeader(with embedded compression) → Context → Index → [Text → Keyword]*`
- Format 4 or 4/2: `FileHeader → Compression → Context → Index → [Text → Keyword]*`
- Format 5/51/52: `FileHeader → Compression → Context → Index → [IndexTags] → [Text → Keyword]*`

For exact rebuild, preserve the original order of index entries and tag
entries as they appear in `RT_Index` and `RT_IndexTags`.

The physical next record begins at `record_start + 3 + RecLength`, using
non-wrapping arithmetic. A known record whose declared end exceeds EOF is
truncated, not an opaque tail. Likewise, a partial three-byte header or a
non-defined record type does not complete a valid stream.
One verified terminal extension consists exclusively of `20h` bytes after
the final complete record. Check the entire remainder before classifying it
as this padding; an arbitrary damaged record must not become padding merely
because its first byte cannot be a record type.

Counts, operands and NUL strings are bounded by their containing record,
not by EOF. For example, a Context count cannot consume offsets from the
following Index record, nor can an IndexTags string use the following Text
record's `00h` length byte as its terminator. Uninterpreted bytes remaining
inside a complete known record may be skipped to its declared end; they do
not supply missing declared fields of another record.

### 1.4 FileHeader Record (RecType=0)

**Format ≤ 3 (20 bytes):**

| Offset | Size | Field      | Description                        |
|--------|------|------------|------------------------------------|
| +0     | 2    | Options    | Flags (bit 2 = case-sensitive)     |
| +2     | 1    | Height     | Screen height in lines             |
| +3     | 1    | Width      | Screen width in columns            |
| +4     | 1    | LeftMargin | Left margin offset                 |
| +5     | 1    | CompType   | Compression type (2 = nibble)      |
| +6     | 14   | CharTable  | Nibble compression lookup table    |

This header has no stored Help Contents context. The Turbo Pascal 4
consumer of profile `FormatVersion=2, TextVersion=1` uses context-table
slot `0064h` (100) as its default index screen. An entry `FF FF FF` in
that consumer resolves to the offset in slot 100. This is an application
binding, not an extra WORD after the compression table; other legacy
profiles' implicit binding is not established here.

**Short Format 4 or 4/2 header (5 bytes):**

| Offset | Size | Field      | Description                        |
|--------|------|------------|------------------------------------|
| +0     | 2    | Options    | Flags                              |
| +2     | 1    | Height     | Screen height                      |
| +3     | 1    | Width      | Screen width                       |
| +4     | 1    | LeftMargin | Left margin                        |

The short form has no stored Help Contents context. Its implicit binding
belongs to the consumer, not to a field at these offsets.
Format 4 and 4/2 can also use the following long form. Select the field
layout by the actual header payload size, not solely by FormatVersion.
Payloads of 6–8 bytes do not contain a complete long header.

**Long Format 4, 4/2, 5, 51 or 52 header (9 bytes):**

| Offset | Size | Field           | Description                   |
|--------|------|-----------------|-------------------------------|
| +0     | 2    | Options         | Flags                         |
| +2     | 2    | HelpContentsScreen | Context number of the source Help Contents screen |
| +4     | 2    | MaxScreenSize   | Maximum compressed `RT_Text` payload size |
| +6     | 1    | Height          | Screen height                 |
| +7     | 1    | Width           | Screen width                  |
| +8     | 1    | LeftMargin      | Left margin                   |

Example complete record:

```text
00 09 00  04 00  64 00  97 01  0F 32 02
```

Type is `0`, payload size `9`, Options `0004h`, Help Contents context
`0064h` (100), MaxScreenSize `0197h` (407), Height 15, Width 50, and
LeftMargin 2. Interpreting its first five payload bytes as a short header
would mistake context 100 for height and a size byte for the margin;
there is no format rule that substitutes width 80 for those misplaced fields.

The `KATO HELP FILE.` Sidekick 2 variant also has a **long**, not short,
FileHeader. Example:

```text
00 09 00  00 00  00 00  D3 01  11 32 00
```

Options and HelpContentsScreen are zero; MaxScreenSize is 467, Height 17,
Width 50, LeftMargin zero. Context-table slot 0 contains `FE FF FF`, not
the address of a Contents Text record, and the Index record's Count is zero.
There is no global Contents body encoded by this header. That consumer
selects Contents from its current application state, not from the first
physical Text record or a matching caption. Its application-owned roots are:

| Application scope | Contents context | General context |
|---|---:|---:|
| No current application | 101 | 101 |
| Notepad | 800 | 101 |
| Time Planner | 900 | 101 |
| Address Book | 100 | 101 |
| Communications | 200 | 101 |
| Calculator | 700 | 101 |

These are consumer bindings outside the HLP, not extra FileHeader fields.
Context 101's text is `GENERAL SIDEKICK TOPICS`; context 100 is the Address
Book, not the global Contents. A different consumer may select another scope.

### 1.5 Context Record (RecType=1)

| Offset | Size   | Field        | Description                      |
|--------|--------|--------------|----------------------------------|
| +0     | 2      | ContextNum   | Number of context entries (Word) |
| +2     | N × 3  | Entries      | Array of 3-byte file offsets     |

Each 3-byte entry encodes a 24-bit file offset:
`FileOffset = byte[0] + (byte[1] << 8) + (byte[2] << 16)`

The array index = screen/context number. The file offset points to
the Text record for that screen.

Special values seen in BOA and in real files:

- `0xFFFFFF` encoded as `FF FF FF` = use the source Help Contents screen text
- `0xFFFFFE` encoded as `FE FF FF` = no help available for this context
- Multiple context entries may point to the same text offset; these are
  alias contexts and must be preserved for byte-identical rebuilds

A `FFFFFFh` entry selects the header-defined Help Contents screen. It does
not select the alphabetical index. Physical Text records can exist without a
context-table assignment; no numeric source context is encoded for such an
orphan merely because it has visible content.
Require all `2 + 3*ContextNum` declared payload bytes before reading offsets.
A complete table can contain unresolved/padding offsets as described above;
checking table boundaries does not invent a text destination for them.
Apart from `FFFFFFh`/`FFFFFEh`, an offset must be smaller than the file size.
EOF is not a Text record. Other negative 24-bit sentinel values have no
defined meaning in this grammar.

Resolve references by the addressed record, not by the location or wording
of a referring hotspot. Several context IDs addressing the same Text record
are genuine aliases; a context ID whose offset addresses padding is not.
A unique Keyword occurrence supplies only a source label/range and target
WORD. It does not supply a replacement destination or prove a hidden anchor.
The same applies to a matching Index label. Keep the target identity even
when its destination is unavailable.

An offset is a record address, not an offset into the Text payload. Confirm
that it is an actual record boundary with RecType `02h`. For example, three
padding bytes `20 20 20` would give RecType `20h` and RecLength `2020h`
(8,224), not a Text record or an anchor. A positive context number outside
`0..ContextNum-1` also has no table entry; it must not be confused with a
stored offset sentinel merely because its WORD is `FFFEh` or `FFFFh`.

The special-value meanings above are BOA's file model. Individual consumers
can supply a different failure/default policy. The Pascal 4 lookup routine
substitutes slot 100 only for `FFFFFFh` or an invalid context number; it
does not use a referring hotspot's label or position. Sidekick 2's lookup
also substitutes slot 100 for `FFFFFEh`, but that failure behavior must not
be confused with its application-selected Contents roots above or encoded
as a genuine positive-offset alias. The Pascal 7 lookup routine
maps negative stored offsets to context-table slot 4 rather than deriving
that slot from a referring label. That application default is not another
wire field or a universal rule for all THELP consumers. A short FileHeader
does not store the long form's HelpContentsScreen binding; do not invent
a native destination when its consumer-specific binding is unknown.

### 1.6 Compression Record (RecType=5)

| Offset | Size | Field     | Description                      |
|--------|------|-----------|----------------------------------|
| +0     | 1    | CompType  | Compression type (2 = nibble)    |
| +1     | 14   | CharTable | Lookup table for nibble codes    |

The table requires all 15 bytes; a partial table must not continue into
another record. `CompType=2` selects the nibble grammar below. Meanings of
other values are not established here and must not be assumed equivalent.
`CharTable[0]` is the reserved NUL/newline entry; a nonzero value there
does not satisfy this grammar. Entries 1–13 contain byte values, not Unicode
characters. A NUL in any of those entries also denotes a newline.

### 1.7 Text Record (RecType=2) — Nibble Compression

Text content is nibble-compressed. Each byte contains two 4-bit nibbles:
**lower nibble first**, then upper nibble.
The upper half of the last payload byte is still part of the stream after
its lower half has been read. Reaching the last byte is not the same as
consuming both of its nibbles.

**Nibble codes:**

| Code      | Meaning                                           |
|-----------|---------------------------------------------------|
| `$0`      | Newline (end of current line)                     |
| `$1`–`$D` | Byte from `CharTable[code]`; NUL means newline   |
| `$E`      | Repeat: next nibble = count−2, then char nibble   |
| `$F`      | Raw byte: next two nibbles = low, high → 1 byte  |

**Repeat (`$E`) details:**

- Count nibble: actual repeat = nibble + 2 (range 2–17)
- Character nibble: same codes as above (`$0`=newlines, `$1`–`$D`=table,
  `$F`=raw byte in next 2 nibbles)
- `$E` is not a valid repeated-character code: there is no nested repeat
  production or lookup entry 14 in the 14-byte table.
- A zero-valued table entry repeats the line break, not a visible NUL.

**Raw byte (`$F`) details:**

- Two nibbles follow in nibble-stream order: `low_nibble + high_nibble * 16`
- Special case: value = `$01` → end-of-text marker
- These two operands may straddle physical bytes. If `$F` occupies the
  lower half, its low operand is the same byte's upper half and its high
  operand is the next byte's lower half. If `$F` occupies the upper half,
  the following byte contains both operands in low/high order.
- A literal byte is not recursively decoded as another nibble command:
  raw `00h`, for example, is not the table-coded line break. Repeated raw
  control bytes are equally distinct from table lookups; original viewer
  treatment of repeated `00h`/`01h` is not established here.

Every used repeat/literal operand stays within the Text payload. An operand
that requires a new byte beyond `RecLength` is incomplete even when a
following Keyword record happens to contain suitable nibble values. Physical
record size remains authoritative after an earlier end marker; unused
remaining payload bytes are not the next record header.
An explicit end marker is not mandatory for all historical Text records.
Without one, consume the entire bounded nibble stream and keep the final
nonempty line; do not discard its last character or invent an extra operand.

A bounded nibble reader can use a half-byte position `i`, initially zero:

```text
require i < 2 * RecLength
b = payload[i // 2]
result = (b >> (4 * (i % 2))) & 0Fh
i = i + 1
```

Fetch repeat and literal operands with the same reader. A newline appends
the current line, even if empty, and clears its byte buffer. At physical end
or a logical end marker, append a remaining nonempty buffer. Preserve the
number of preceding newline events separately from the number of empty
lines if the consumer needs the page-completion state below.

Examples using `CharTable = 00 41 42 ... 4D` (NUL, `A`–`M`):

| Payload bytes | Nibbles, low first | Decoded result |
|---------------|--------------------|----------------|
| `21` | `1 2` | `AB`, including the last upper nibble |
| `00` | `0 0` | Two empty lines |
| `1F 04` | `F 1 4 0` | Raw `41h` (`A`), then newline |
| `F1 41` | `1 F 1 4` | Table `A`, then raw `41h`: `AA` |
| `0E 11` | `E 0 1 1` | Two repeated `A`s, then `A`: `AAA` |
| `EE 1F 04` | `E E F 1 4 0` | Sixteen raw `41h` bytes (`A`s), then newline |
| `F1` | `1 F` | `A`, then a raw opcode without operands; reject |

Implementation notes for a faithful compiler:

- Build the nibble stream first, then pack low nibble first into bytes.
- Page-oriented formats commonly store an explicit end-of-text marker
  (`$F 1 0`); its absence alone does not make a complete payload invalid.
- The exact choice between `... $0 $F 1 0` and `... $F 1 0` affects whether
  the decompiler reconstructs one extra blank line at the end of a topic.
  A round-trip decompiler therefore needs to preserve this state explicitly.

### 1.7.1 In-Band Text Control Bytes

After nibble decompression, topic text may still contain non-printing control
bytes embedded directly in the text lines. These are part of the THELP topic
content and should be preserved by a decompiler/compiler pipeline.

Defined text controls:

| Byte sequence | Meaning | Notes |
|---------------|---------|-------|
| `0x02` | Inline hotspot delimiter | Text between two `0x02` bytes is a clickable hotspot. In newer formats the matching targets come from the sequential context IDs stored in `RT_Keyword`; in older formats the click ranges are given explicitly by `KEYWORD4` coordinates. |
| `0x05` | Turbo Example delimiter (`^E`) | Each occurrence toggles the example state and consumes no visible cell. It can appear anywhere in a row, not only as the first byte. |
| `0x14` | Pascal 7 product-name placeholder (`^T`) | Consumer-specific substitution before RLE emission; see section 1.7.2. |

The example state initially is off at the beginning of a logical topic.
Process the decompressed text bytes in order:

```text
if byte == 05h:
    example = not example
else:
    emit byte with the current example attribute
```

Preserve every other byte, including indentation before a delimiter,
whitespace after it, and row boundaries. Removing a delimiter does not
remove its entire row: `05h, newline` still contains a newline. Two adjacent
`05h` bytes toggle twice and leave the entering state unchanged. A closing
delimiter after source text belongs after that text; it does not make the
preceding text normal or become a visible `♣` glyph.

Example content can span contexts linked through `UpContext`/`DownContext`.
Carry the state through that logical page sequence, not through neighboring
physical Text records: file order does not establish a continuation.
Zero in a page-link field is an end sentinel even when context zero exists.
A linked page without a new delimiter may still be inside an example.
Cycles or contradictory page links do not establish a unique entry state.

The documented authoring constraint is one Turbo Example per logical topic,
without nesting examples inside hotspots or hotspots inside examples.
This does not permit collapsing repeated delimiter bytes: decode each
occurrence, including malformed/unbalanced authored text. A visible heading
such as `Example:` or a filename ending in `.PAS` is plain text, not a
stored example opcode.

Examples, where `↵` denotes a decoded line break:

| Bytes/text | Meaning |
|------------|---------|
| `20 05 41 05 20` | Normal space, example `A`, normal space |
| `05 05 41` | Two toggles; `A` retains the entering attribute |
| `05 ↵ 20 41 ↵ 05 ↵` | Empty opening row, example ` A`, empty closing row |
| `20 7D 20 05` | If entered inside an example, ` } ` is example text before the closing toggle |

`03h` and `10h` are not Turbo Example delimiters. In OEM display text,
they can be the heart (`♥`) and right-pointing triangle (`►`) glyphs.
In particular, `10h` occurs as a menu arrow and as the right end of drawn
scrollbars. There is no established two-byte example-end opcode `10h 05h`;
those bytes alone do not justify discarding `10h`.

### 1.7.2 Pascal 7 Product-Name Substitution

Pascal 7 consumers interpret `14h` (`^T`) as a product-name placeholder,
not an emphasis attribute or a Turbo Example delimiter. The corresponding
text profile occurs with FormatVersion `34h` (decimal 52), TextVersion `02h`.
Do not assume that every other consumer gives `14h` the same meaning;
retain unknown byte/glyph semantics rather than silently deleting it.

The replacement is an application-owned Pascal short string: one BYTE
length followed by that many bytes, not a string stored in the placeholder.
The Turbo Pascal consumer uses `05 54 75 72 62 6F` (`Turbo`); the Borland
Pascal consumer uses `07 42 6F 72 6C 61 6E 64` (`Borland`). The ordinary
`IndexTags` description can identify the intended product, but there is
no dedicated replacement-string field in FileHeader or RT_Text. A decoder
must therefore select a consumer profile separately for ambiguous files.

At the start of each physical RT_Text record, suppression is off and the
pending repeat count is zero. Apply the following algorithm to decoded
character tokens **before expanding the nibble codec's repeat count**:

```text
on a repeat token:
    pending_repeat = stored_count + 2
on its character, or an ordinary character token:
    if character == 01h:
        end the text
    else if character == 14h:
        suppressed = not suppressed
        if suppressed: emit the replacement string once
    else if not suppressed:
        emit character (pending_repeat or 1) times
        pending_repeat = 0
```

The opening `14h` inserts the replacement and suppresses every following
character through the closing `14h`, including spaces, NUL row boundaries,
hotspot and example delimiters. The closing marker emits nothing. A pending
repeat count is **not** cleared by either marker or a suppressed character;
a new repeat token can overwrite it. Thus an RLE-encoded `14h` toggles once
per character token, not once per expanded repetition. A missing closing
marker suppresses the rest of that physical record; state does not carry
through UpContext/DownContext links. Inserted replacement bytes do not pass
back through this substitution loop.

Examples with replacement `Turbo`:

| Input | Emitted bytes/text |
|-------|--------------------|
| `14 20 54 75 72 62 6F 20 14 20 50 61 73 63 61 6C` | `Turbo Pascal`, not ` Turbo  Pascal` |
| `pre 14 ignored 14 post` | `preTurbopost` |
| `14 14 14 14` | `TurboTurbo` |
| `14 ignored 00 second 14 after` | `Turboafter`; the suppressed NUL makes no row |
| repeat count 4 + `14`, ordinary `A`, `14`, `B` | `TurboBBBB`; the count survives suppression |

Keep the original compressed stream or lossless decoded tokens for
reconstruction: the displayed replacement is not the stored placeholder
body and cannot be used to recover its original bytes.

### 1.7.3 Sequential Text Word Flow

The newer sequential text stream is laid out at a consumer-selected width
`W` in byte cells. FileHeader supplies preferred dimensions and LeftMargin,
not a table schema. Apply the left margin to the right wrapping boundary;
horizontal scrolling does not change that boundary. A change of viewport
width requires laying out the original text again, not rewrapping rows that
have already been formatted. Fixed text can be clipped by the viewport, but
the formatter does not delete its tail.

BOA describes wrapping at whitespace. The Pascal 7 formatter's precise
branch uses a **literal `20h` or NUL at the start of the source row**:

- A row starting with `20h`, or an empty row, is fixed. End any preceding
  flowing row and copy the fixed row unchanged, including its hard return.
- Every other row flows, including one starting with `02h`, `05h` or TAB
  (`09h`). A control followed by a space is not a leading literal space.
- Decode product-name placeholders before this stage, but retain hotspot
  and example delimiters until after it. A raw-escaped NUL still becomes a
  return in the consumer's uncompressed buffer.

For a flowing row, read words using this algorithm:

```text
word = empty; word_cells = 0; in_keyword = false
while not at NUL and not (byte == 20h and not in_keyword):
    copy byte into word
    if byte >= 07h: word_cells += 1
    else if byte == 02h: in_keyword = not in_keyword
append the complete following run of ordinary 20h spaces to word
if the word ended at NUL without such a run: append one 20h
if the output row has cells and row_cells + word_cells > W:
    end the output row before this word
append word; count its bytes >= 07h toward row_cells
```

The suffix spaces contribute to the output row's cell count but not to the
word's fit test. Retain them: a row is not wrapped merely because its trailing
spaces extend past `W`. A word/hotspot wider than `W` remains indivisible;
clipping or horizontal scrolling is a separate display operation. Bytes
below `07h` occupy no cells in this formatter's arithmetic; that rule does
not define their glyph/attribute behavior in every consumer. An unmatched
hotspot delimiter does not give a word access beyond its source return.

An unindented source return contributes a separating space and allows the
next flowing row to continue the same output row. A following fixed/empty
row terminates the flow. Process logical page continuations according to
their UpContext/DownContext stream, not physical record order.

Examples, with each array element denoting a source or output row:

| Source bytes/text | Width | Output |
|-------------------|-------|--------|
| `[Hello, world]` | 10 | `[Hello␠, world␠]` |
| `[Hello, world]` | 76 | `[Hello␠world␠]` |
| `[one␠␠two␠␠␠three]` | 10 | `[one␠␠two␠␠␠, three␠]` |
| `[␠Fixed, row]` | 76 | `[␠Fixed, row␠]`; the first return stays hard |
| `[02 alpha 02 B3, 02 beta 02 B3]` | 76 | One row, both atomic labels, a space after each `B3` |

Tables are an application of these same rules, not an additional binary
record: a fixed border may precede one linked cell per source row. The `│`
separator can be inside or immediately after its hotspot. Fit successive
cells at `W` while preserving keyword order; **do not infer a column count
from `╤`/`╕` or require a border to enable flow**. Resizing can change the
number of cells per display row. The sequential Keyword target array stays
in physical hotspot order regardless of the resulting row breaks.

### 1.8 Keyword Record (RecType=3)

**Format < 5 and the 4/2 variant:**

| Offset | Size | Field       | Type | Description            |
|--------|------|-------------|------|------------------------|
| +0     | 2    | UpContext   | Word | Previous screen link   |
| +2     | 2    | DownContext | Word | Next screen link       |
| +4     | 1    | KeyWordCnt  | Byte | Number of keywords     |

Followed by `KeyWordCnt` keyword entries (9 bytes each):

| Offset | Size | Field       | Type | Description               |
|--------|------|-------------|------|---------------------------|
| +0     | 1    | Line        | Byte | Line position on screen   |
| +1     | 1    | FirstColumn | Byte | Start column (+ margin)   |
| +2     | 1    | LastColumn  | Byte | End column (+ margin)     |
| +3     | 1    | LeftBtn     | Byte | Left navigation target    |
| +4     | 1    | RightBtn    | Byte | Right navigation target   |
| +5     | 1    | UpBtn       | Byte | Up navigation target      |
| +6     | 1    | DownBtn     | Byte | Down navigation target    |
| +7     | 2    | Context     | Word | Target screen context ID  |

`UpContext` and `DownContext` address previous/next Text screens. Zero
means there is no screen in that direction: `UpContext=0` begins a page
chain and `DownContext=0` ends it. Zero here is a control value, not an
instruction to open context-table slot 0. A Keyword's target Context WORD
and the long FileHeader's HelpContentsScreen use their own field semantics;
an actual topic-zero target in those fields must not be discarded.

Sidekick 2 displays the literal final-line marker `<more>` on screens that
continue through a non-zero `DownContext`. This marker is navigation, not
ordinary text. Its destination is the stored `DownContext`, not a new
context encoded in the marker.

`LeftBtn/RightBtn/UpBtn/DownBtn` are 1-based keyword-navigation button
indices used by old-format viewers: `01h` selects the first keyword entry,
`02h` the second, and so on; zero does not select a keyword. They move the
highlight within the current screen, not to context-table slots 1, 2, etc.
Only the selected keyword's separate Context WORD supplies its destination
when activated. These indices are not derivable from position alone and
must be preserved if exact rebuild is required.

**Format ≥ 5 (excluding 4/2):**

| Offset | Size | Field       | Type | Description            |
|--------|------|-------------|------|------------------------|
| +0     | 2    | UpContext   | Word | Previous screen link   |
| +2     | 2    | DownContext | Word | Next screen link       |
| +4     | 2    | KeyWordCnt  | Word | Number of keywords     |

Followed by `KeyWordCnt` × Word values (target context IDs).

The UpContext/DownContext zero-sentinel and page-chain rules above apply
to this layout too; the keyword target array does not contain the legacy
four direction-button indices.

In page-oriented files, the word values are best treated as target context
ids. They often equal index-context values, but the binary does not store a
separate text label here; the visible label comes from the matching inline
`0x02...0x02` hotspot in the `RT_Text` stream.

### 1.9 Index Record (RecType=4)

| Offset | Size | Field | Type | Description             |
|--------|------|-------|------|-------------------------|
| +0     | 2    | Count | Word | Number of index entries |

Followed by `Count` entries with prefix compression:

Each entry:
- 1 byte: `(keep << 5) | new_len`
  - `keep` (bits 7–5): characters to reuse from previous entry (0–7)
- `new_len` (bits 4–0): new characters to read (0–31)
- `new_len` bytes: new character data
- 2 bytes: ContextNumber (Word) — target screen

Start with an empty previous token. Require `keep <= previous_token_length`,
then form `previous_token[0:keep] + unique_bytes`. Count and all descriptor
fields remain inside this record. For previous `addition`, lengthCode `46h`
means keep two bytes and append six; suffix `vanced` yields `advanced`.

The entry number in this record is important because `RT_IndexTags`
references index entries by ordinal, not by string value.

Use each raw ContextNumber to look up its context-table entry. Repeated text
offsets are aliases. Sentinel values have their defined semantics; a padding
offset has no directly addressed Text record. Its destination is not determined
by the index label or by a similarly named topic.

### 1.10 IndexTags Record (RecType=6, Format ≥ 5)

Repeated until end of record:

| Offset | Size | Field        | Type   | Description              |
|--------|------|--------------|--------|--------------------------|
| +0     | 2    | IndexNumber  | Word   | Index entry number       |
| +2     | 1    | TextLength   | Byte   | Tag string length        |
| +3     | var  | TagString    | ASCIIZ | Null-terminated tag name |

Special case: `IndexNumber = $FFFF` → file description tag.

Multiple tags may reference the same index entry. Preserve record order.
TextLength counts the bytes before the terminating `00h`, not including
that terminator. Both the declared text bytes and its NUL remain within the
record; an earlier NUL or a mismatched length is not another valid tag form.

### 1.12 Compiler Recipe

To build a compatible THELP compiler:

1. Write administrative header: stamp, `0x1A`, signature, version.
2. Emit `RT_FileHeader`, optional `RT_Compression`, `RT_Context`, `RT_Index`
   and `RT_IndexTags` in the format-specific order above.
3. Build the 14-byte character table from text frequency.
4. Encode each screen's text using nibble compression.
5. Emit matching `RT_Keyword` for every `RT_Text`.
6. Fill the context table with 24-bit offsets to each `RT_Text`.
7. Preserve alias contexts, index order, tag order, unused sentinels and
   v5+ end-of-text behaviour if byte-identical rebuild matters.

### 1.13 Decompiler Recipe

To build a compatible THELP decompiler:

1. Parse the administrative header and version record.
2. Parse records sequentially and remember compression, context table,
   index entries and index tags.
3. Resolve text-record file offsets back to context numbers through the
   context table. If several context numbers share one offset, emit alias
   information for all but the first one.
4. Decode nibble-compressed text, preserving whether the record ended with
   an extra trailing newline before the v5+ end marker, and preserve in-band
   text control bytes such as `0x02`, `0x05` and `0x10 0x05`.
5. Decode keyword records:
   old format stores coordinates/navigation-button indices, new format stores
   ordered target WORDs paired with the inline hotspot delimiters.
6. Re-emit `RT_Index` and `RT_IndexTags` information in a stable textual
   form that preserves their stored entry order.

### 1.14 Bounded structural decoding

1. Read both administrative NUL strings within the file. Require `1Ah`
   immediately after the stamp and the two complete version bytes after
   the signature. For the standard family described here, the signature
   is exactly `$*$* &&&&$*$` at that position, not an occurrence found in
   body text. Borland's generic protocol permits negotiated signatures,
   but a different signature is not identified by an incidental body match.
2. Use the explicitly defined version/record grammar. Other version numbers
   have unverified layouts; do not presume that every value above 52 means
   the same extension. TextVersion is ordinarily an author-assigned content
   version; the independently identified 4/2 branch retains legacy keywords.
3. For each record, require its complete header and declared physical extent.
   Give field readers that record's end as their limit, including nibble
   operand reads and string terminator searches.
4. Decode all counted Context, Keyword and Index entries, and every complete
   IndexTags descriptor. A field does not become optional when the payload
   ends early. Require at least the FileHeader record; an administrative
   preamble alone does not define a complete help database.
5. Advance only to the declared physical end. At EOF finish; otherwise
   continue with the next record or the verified all-space terminal extension.
   Structural validity alone does not prove that an unresolved context or
   a source-specific text control has a known runtime meaning.

### References

- Borland, Open Architecture Handbook, chapter 6, binary Help records and
  nibble grammar, and `BOA.BC3/DECOMP.ZIP` containing `DEHELP.C`:
  [archived BC4BOA package](https://dose.0wnz.at/Shareware/Pegasus-5.0/TEXTE/BC4BOA.ZIP).

---
