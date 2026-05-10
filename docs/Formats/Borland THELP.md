# Borland THELP Format

> Created: 2026-03-29 · Last updated: 2026-05-05

Used by: Turbo Pascal 4–5.5, Turbo C, Turbo Assembler, Borland Sprint,
Sidekick, Eureka. File extensions: `.HLP`, `.TPH`, `.TCH`, and other
Borland `*.T?H` variants when the THELP signature matches.

Original implementation: THELP unit in Turbo Pascal runtime.  
Reference decompiler: HLDC 1.03 by Volker Pohlers (1994/2010).  
Borland references:
- Open Architecture Handbook 4.0, chapter `Borland Help System` (`BOA.TXT`)
- `DEHELP.C` / `DEHELP.DOC` from `BOA.BC3/DECOMP.ZIP`

`DEHELP` explicitly states support for BC++ 3.0 and Turbo Pascal help
systems only; Borland's Windows and some product-specific variants are
outside its supported set.

Turbo Debugger 1.0 `TDHELP.TDH` is a product-specific exception, not a
THELP record stream. It has no `$*$* &&&&$*$` signature, starts with
`02 06 00 01 ...`, and appears compressed/encoded from offset 0. The downloader
collects it and the help database records its CRC32, but it must be decoded by
a separate TDH reader rather than by the THELP parser.

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
  standalone `RT_Text` record; in practice these behave like hidden anchors
  into existing topics and can often be resolved from inline keyword usage

Observed BC++ 2.x hidden-anchor behavior:
- `RT_Index.ContextNumber` is still the authoritative raw target. In some
  BC++ 2.x `formatVersion = 51` files that target's context-table offset
  points into trailing space padding instead of an `RT_Text` record.
- BOA 4.0 and `DEHELP.C` do not document an additional record that resolves
  these targets. They only read the context table, the index table and the
  keyword target list.
- A hidden context can be reconstructed exactly only when the same context id
  is referenced by `RT_Keyword` from visible text. If that context id appears
  at one unique `(topic, line)` location, the parser treats that location as
  the hidden anchor.
- If the same hidden context is referenced from multiple different locations,
  or is never referenced by `RT_Keyword`, the parser must leave the index item
  unresolved instead of guessing from visible text.
- Known generated index-table contexts such as `HC_INDEXTABLE = 401` may also
  point to padding. `DEHELP.C` uses the hard-coded `401` only to skip the
  generated index screen and let `HL.EXE` recreate it; it does not provide
  per-entry targets for missing contexts.

### 1.1 File Layout

```
┌──────────────────────────────┐
│  Stamp (null-terminated)     │  e.g. "TURBO PASCAL HELP FILE"
├──────────────────────────────┤
│  $1A separator               │  1 byte
├──────────────────────────────┤
│  Signature (null-terminated) │  "$*$* &&&&$*$" (13 bytes + NUL)
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

| Value | Internal | Product                              |
|-------|----------|--------------------------------------|
| 1     | 1        | Eureka                               |
| 2     | 2        | Turbo Pascal 4.0                     |
| 3     | 3        | Borland Sprint                       |
| 4     | 4        | Turbo Pascal 5.0/5.5, Turbo C++ 3.0 |
| 4*    | 41       | Sidekick (KATO) — TextVersion=2      |
| 5     | 5        | Turbo Assembler 2                    |
| 51    | 51       | Turbo Pascal 6.0                     |
| 52    | 52       | Turbo Pascal 7.0, Borland Pascal 7   |

\* Sidekick KATO: FormatVersion=4, TextVersion=2 → treated as format 41 internally
(uses old keyword format like format ≤3).

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
observed extension present in newer Borland help files and supported by the
current parser.

Record order is format-dependent:

- Format 2/3: `FileHeader(with embedded compression) → Context → Index → [Text → Keyword]*`
- Format 4/41: `FileHeader → Compression → Context → Index → [Text → Keyword]*`
- Format 5/51/52: `FileHeader → Compression → Context → Index → IndexTags → [Text → Keyword]*`

For exact rebuild, preserve the original order of index entries and tag
entries as they appear in `RT_Index` and `RT_IndexTags`.

Parser note:
- stop record parsing at the first invalid record header or record extending
  past EOF; any remaining bytes should be treated as opaque trailing data or
  padding, not as more help records

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

**Format 4/41 (5 bytes):**

| Offset | Size | Field      | Description                        |
|--------|------|------------|------------------------------------|
| +0     | 2    | Options    | Flags                              |
| +2     | 1    | Height     | Screen height                      |
| +3     | 1    | Width      | Screen width                       |
| +4     | 1    | LeftMargin | Left margin                        |

**Format ≥ 5 (9 bytes):**

| Offset | Size | Field           | Description                   |
|--------|------|-----------------|-------------------------------|
| +0     | 2    | Options         | Flags                         |
| +2     | 2    | HelpContentsScreen | Context number of the source Help Contents screen |
| +4     | 2    | MaxScreenSize   | Maximum compressed `RT_Text` payload size |
| +6     | 1    | Height          | Screen height                 |
| +7     | 1    | Width           | Screen width                  |
| +8     | 1    | LeftMargin      | Left margin                   |

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

The current parser treats `0xFFFFFF` entries as aliases to the header's
Help Contents context when the file header defines one. In the original
viewers this is the help contents screen, not the alphabetical index.

### 1.6 Compression Record (RecType=5)

| Offset | Size | Field     | Description                      |
|--------|------|-----------|----------------------------------|
| +0     | 1    | CompType  | Compression type (2 = nibble)    |
| +1     | 14   | CharTable | Lookup table for nibble codes    |

### 1.7 Text Record (RecType=2) — Nibble Compression

Text content is nibble-compressed. Each byte contains two 4-bit nibbles:
**lower nibble first**, then upper nibble.

**Nibble codes:**

| Code      | Meaning                                           |
|-----------|---------------------------------------------------|
| `$0`      | Newline (end of current line)                     |
| `$1`–`$D` | Character from `CharTable[code]`                  |
| `$E`      | Repeat: next nibble = count−2, then char nibble   |
| `$F`      | Raw byte: next two nibbles = high, low → 1 byte  |

**Repeat (`$E`) details:**
- Count nibble: actual repeat = nibble + 2 (range 2–17)
- Character nibble: same codes as above (`$0`=newlines, `$1`–`$D`=table,
  `$F`=raw byte in next 2 nibbles)

**Raw byte (`$F`) details:**
- Two nibbles follow in nibble-stream order: `low_nibble + high_nibble * 16`
- Special case: value = `$01` → end-of-text marker

Implementation notes for a faithful compiler:

- Build the nibble stream first, then pack low nibble first into bytes.
- In format ≥ 5, Borland stores an explicit end-of-text marker (`$F 1 0`).
- The exact choice between `... $0 $F 1 0` and `... $F 1 0` affects whether
  the decompiler reconstructs one extra blank line at the end of a topic.
  A round-trip decompiler therefore needs to preserve this state explicitly.

### 1.7.1 In-Band Text Control Bytes

After nibble decompression, topic text may still contain non-printing control
bytes embedded directly in the text lines. These are part of the THELP topic
content and should be preserved by a decompiler/compiler pipeline.

Observed control bytes:

| Byte sequence | Meaning | Notes |
|---------------|---------|-------|
| `0x02` | Inline hotspot delimiter | Text between two `0x02` bytes is a clickable hotspot. In newer formats the matching targets come from the sequential context IDs stored in `RT_Keyword`; in older formats the click ranges are given explicitly by `KEYWORD4` coordinates. |
| `0x05` | Code-example block toggle | Observed as a standalone line marker before and after Pascal source examples. |
| `0x10 0x05` | Code-example block end variant | Observed as an alternate closing marker in some topics. |

Observed in sample files:

- `TURBO7CZ.TPH`: `0x05` used in hundreds of topics around source examples
- `BTP7CZ/TURBO.TPH`: same pattern as `TURBO7CZ.TPH`
- `BTP7CZ/TVISION.TPH`: same marker in a smaller subset of topics
- `BTP7CZ/OWL.TPH`, `BTP7CZ/WINDOWS.TPH`, `TURBO4.HLP`: no such marker observed in current samples

For HTML export this means `0x05` / `0x10 0x05` should not be rendered as CP437
glyphs such as `♣` or `►♣`; they behave as structural delimiters for a code
example block.

### 1.8 Keyword Record (RecType=3)

**Format < 5 and Format 41:**

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

When `DownContext = 0`, this is the last page of a multi-page screen.

`LeftBtn/RightBtn/UpBtn/DownBtn` are 1-based keyword-navigation button
indices used by old-format viewers. They are not derivable from position
alone and must be preserved if exact rebuild is required.

**Format ≥ 5 (excluding 41):**

| Offset | Size | Field       | Type | Description            |
|--------|------|-------------|------|------------------------|
| +0     | 2    | UpContext   | Word | Previous screen link   |
| +2     | 2    | DownContext | Word | Next screen link       |
| +4     | 2    | KeyWordCnt  | Word | Number of keywords     |

Followed by `KeyWordCnt` × Word values (target context IDs).

In page-oriented files, the word values are best treated as target context
ids. They often equal index-context values, but the binary does not store a
separate text label here; the visible label comes from the matching inline
`0x02...0x02` hotspot in the `RT_Text` stream.

For decompilation, a practical textual source format is:

```
;KEYWORD4 146 AT (3,22-43) NAV (1,2,0,0)
;KEYWORD 432
```

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

The entry number in this record is important because `RT_IndexTags`
references index entries by ordinal, not by string value.

For exact link reconstruction:
- if `ContextNumber` exists as an `RT_Text` topic, link directly to that topic
- if it is a hidden context with one unique `RT_Keyword` occurrence, link to
  that `(topic, line)` anchor
- if it has several possible keyword occurrences, keep it unresolved and
  expose the alternatives in parser metadata
- if it has no keyword occurrence and its context-table offset points into
  padding, there is not enough information in the known BOA/DEHELP structures
  to reconstruct the destination

### 1.10 IndexTags Record (RecType=6, Format ≥ 5)

Repeated until end of record:

| Offset | Size | Field        | Type   | Description              |
|--------|------|--------------|--------|--------------------------|
| +0     | 2    | IndexNumber  | Word   | Index entry number       |
| +2     | 1    | TextLength   | Byte   | Tag string length        |
| +3     | var  | TagString    | ASCIIZ | Null-terminated tag name |

Special case: `IndexNumber = $FFFF` → file description tag.

Multiple tags may reference the same index entry. Preserve record order.

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
   old format emits positional `;KEYWORD4 ... NAV (...)`, new format emits
   `;KEYWORD ...`.
6. Re-emit `RT_Index` and `RT_IndexTags` information in a stable textual
   form such as `;INDEXORDER` and `;TAGORDER`.

---
