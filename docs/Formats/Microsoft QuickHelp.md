# Microsoft QuickHelp LN Format

> Created: 2026-04-07 · Last updated: 2026-10-14

Used by: Microsoft QuickBasic 4.5, QuickC 2.0/2.50, MASM 6, PWB, LINK, later CodeView bundles, and compatible products.
File extension: `.HLP` (LN binary database).

Installer media may wrap or split the file using
[Microsoft SZ compression](Microsoft%20SZ%20Compression.md). The LN offsets
below apply to the complete expanded database, not to individual compressed
disk parts.

**Authoritative format specification:**
[fancidev/DosHelp — Format.txt](https://raw.githubusercontent.com/fancidev/DosHelp/master/QuickHelp/Serialization/Format.txt)
(MIT licence; layouts below also describe observations from original LN databases.)

All multi-byte integers are little-endian.

---

## 1. File Signature

Bytes 0–3: `4C 4E 02 00` (`LN` + version word `0x0002`).

Detection:

```python
data[:2] == b"LN" and data[2:4] == b"\x02\x00"
```

---

## 2. File Header (offset 0x00)

```
00-02  WORD  Signature ("LN")
02-04  WORD  Version           = 2
04-06  WORD  Attributes        bit 0 = CaseSensitive context strings;
                              bit 1 = prevent HELPMAKE decoding;
                              bits 2-15 reserved (zero)
06-07  BYTE  ControlCharacter  command-line prefix (typically 0x3A = ':')
07-08  BYTE  (padding)
08-0A  WORD  TopicCount        number of topics
0A-0C  WORD  ContextCount      number of context strings
0C-0E  WORD  DisplayWidth      default display width (characters)
0E-10  WORD  PredefinedCtxCount
10-1E  BYTE[14] DatabaseName   NUL-padded ASCII database name
1E-22  DWORD (reserved)
22-26  DWORD TopicIndexOffset  → TopicIndex section
26-2A  DWORD ContextStringsOffset → ContextStrings section
2A-2E  DWORD ContextMapOffset  → ContextMap section
2E-32  DWORD KeywordsOffset    → Keywords section (0 = absent)
32-36  DWORD HuffmanTreeOffset → HuffmanTree section (0 = absent)
36-3A  DWORD TopicTextOffset   → TopicText section (compressed topic data)
3A-3E  DWORD (reserved)
3E-42  DWORD (reserved)
42-46  DWORD DatabaseSize      size of this database, not necessarily the file
```

### 2.1 Concatenated databases

The format permits consecutive complete LN databases in one physical `.HLP`.
Each has its own header, context namespace and compression tables. Section and
topic offsets are relative to that database's beginning. Advance by its
`DatabaseSize` to find the next header; never scan arbitrary compressed bytes
for `LN`. `DatabaseName` identifies the logical database for external links,
and need not match the physical filename.

Original-file examples:

| Product / physical file | Logical databases in order | Topic counts |
| --- | --- | --- |
| QuickBASIC Extended 7.1 / `BC.HLP` | `bc.hlp`, `pwbbc.hlp` | 20 + 22 = 42 |
| QuickBASIC Extended 7.1 / `LINK.HLP` | `linkx.hlp`, `ilink.hlp` | 155 + 51 = 206 |
| QuickBASIC Extended 7.1 / `UTILS.HLP` | `lib.hlp`, `nmake.hlp`, `helpmake.hlp`, `bind.hlp`, `misc.hlp` | 59 + 102 + 73 + 43 + 36 = 313 |
| QuickC, C, and C++ 6.0 / `LINK.HLP` | `linkx.hlp`, `ilink.hlp` | 155 + 51 = 206 |

Each concatenated database must fit within the physical file, including its
header, sections and indexed topic ranges. Advance by the declared size, not
by scanning compressed data for another signature.

---

## 3. Sections

### 3.1 TopicIndex

`TopicCount + 1` DWORDs at `TopicIndexOffset`.
Each entry is an offset into `TopicText` (relative to database start).
Topic *i* occupies bytes `TopicIndex[i]` through `TopicIndex[i+1] - 1`.
The first entry equals `TopicTextOffset`; the final entry equals `DatabaseSize`.
Entries are increasing and every interval contains at least its two-byte
`OUTLEN`. An empty topic can have `OUTLEN = 0`, but is not a zero-byte interval.

### 3.2 ContextStrings

`ContextCount` NUL-terminated ASCII strings packed consecutively.
These are the human-visible or internal context names used for linking.

### 3.3 ContextMap

`ContextCount` WORDs at `ContextMapOffset`.
`ContextMap[i]` = topic index for `ContextStrings[i]`.
Each index must be below `TopicCount`; it is local to this logical database.

Context lookup is case-insensitive unless `Attributes & 0x01` is set.

### 3.4 Keywords (optional)

Length-prefixed byte strings packed consecutively.
Each entry: `BYTE length` followed by `length` bytes of keyword text.
Absent when `KeywordsOffset == 0`; in that case treat as empty dictionary.

Used by Step 2 decompression (keyword substitution).
There are at most 1024 entries because a reference has ten index bits. Every
length-prefixed entry fits entirely before the Huffman section, or before
`TopicTextOffset` when Huffman compression is absent.

### 3.5 HuffmanTree (optional)

Sequence of signed `INT16` values at `HuffmanTreeOffset`, terminated by `0`.
Absent when `HuffmanTreeOffset == 0`; in that case skip Huffman decoding.

Tree encoding (per Format.txt):

- Root node is at index 0.
- Node at index *i* with value *V*:
  - `V > 0` → internal node: 0-bit (left) child at `tree[V // 2]`, 1-bit (right) child at `tree[i + 1]`.
  - `V < 0` → leaf: emit symbol `V & 0xFF`.
  - `V == 0` → terminator (end of tree array).

Bits are read **MSB-first** from each byte.

The section contains at most 511 nodes plus its final zero WORD (1024 bytes).
Its length is even and the terminator is the final WORD, not an internal node.
For an internal node, `V` is an even byte offset. The serialized post-order
numbering puts both child indices strictly after the parent and within the
node array; this prevents cycles and out-of-array traversal. A tree with one
leaf encodes a single repeated symbol without consuming bits: expansion still
stops at the declared `OUTLEN`.

### 3.6 TopicText

Compressed topic data.  Each topic begins at `TopicIndex[i]` and is decoded
through a three-stage pipeline (see §4).

---

## 4. Three-Stage Decompression Pipeline

Each raw topic blob is decompressed in three stages in reverse order.

### Stage 3 → Huffman decode

Input: raw compressed bytes from `TopicText`.
Output: "compact" intermediate bytes.

The first 2 bytes of the topic blob are `OUTLEN` (WORD), the number of bytes
expected after Stage 2 decoding.  The remaining bytes are Huffman-encoded
using the tree from §3.5.

If no HuffmanTree section is present, the bytes after `OUTLEN` are already
compact and no decoding is needed.

Read symbols on demand for Stage 2. The final encoded byte can contain unused
padding bits; decoding every bit as another output symbol is not an end rule.
Exhausting the bit stream before Stage 2 produces `OUTLEN` is truncated data.

### Stage 2 → Keyword expand + RLE

Input: compact bytes from Stage 3.
Output: binary topic data of exactly `OUTLEN` bytes.

Control byte values:

| Range | Meaning |
|-------|---------|
| `0x00–0x0F`, `0x1B–0xFF` | Literal byte — copy as-is |
| `0x10–0x17` | Dictionary reference: `idx = ((byte & 3) << 8) \| next_byte`; emit `Keywords[idx]`; if `byte & 4` also emit space `0x20` |
| `0x18` | Space run: emit `next_byte` × `0x20` |
| `0x19` | Repeat: emit `next_byte₁` × `next_byte₂` times |
| `0x1A` | Escape: next byte is literal |

Every control's argument must be present, and each dictionary index must refer
to an existing entry. Do not skip an invalid reference or an incomplete escape.
An expansion must produce exactly `OUTLEN`: neither too few bytes nor an
overshooting dictionary/run is a complete topic. Stop requesting Huffman
symbols as soon as that count is reached.

### Stage 1 → Binary topic decompile

Input: binary topic data from Stage 2.
Output: display lines + attribute records.

The binary stream is a sequence of `(TextBlock, AttrBlock)` pairs:

```
BYTE  TextLen        length of text data + 1; at least 1
BYTE  text[TextLen-1]
BYTE  AttrLen        length of attribute data + 1; at least 1
BYTE  attr[AttrLen-1]
```

The stream ends after exactly `OUTLEN` bytes, at a complete pair boundary.
Neither block length may be zero; there is no additional NUL topic terminator.
`TextLen = 1` represents an empty text block and `AttrLen = 1` empty attributes.
Bounds apply to command lines as well as visible lines.

Uncompressed byte example for the visible line `Hello` in normal style:

```text
08 00  06 48 65 6C 6C 6F  02 05
^^^^^  ^^^^^^^^^^^^^^^^  ^^^^^
OUTLEN text block        attributes: five characters in default style
```

The two-byte `OUTLEN` is not included in its value. `01 01` is a complete
two-byte binary pair for a blank line; `01 00` is not, because the attribute
block length is zero.

---

## 5. Command Lines

A text block whose first byte equals `ControlCharacter` is a **command line**.
It is not displayed; instead the second byte selects the command.
Parameters follow immediately (no separator between command byte and parameter).

### Known commands (observed across QB 4.5 / QBX / MASM / CV / PWB / LINK)

| Cmd | Parameter | Source directive | Meaning |
|-----|-----------|-----------------|---------|
| `n` | topic title | `.topic` | Human-readable topic title |
| `c` | `string [linenum]` | `.category` | Category name + optional line number for Table of Contents placement |
| `l` | `N` (decimal) | `.freeze` | Freeze first *N* lines — they stay visible when the user scrolls |
| `z` | `N` (decimal) | — | Numeric display parameter (observed alongside `:l`; exact meaning unclear) |
| `i` | — | `.list` | Mark topic as a selectable list |
| `p` | paste-name | `.paste` | Begin a named pasteable section |
| `e` | — | `.end` | End the pasteable section started by `:p` |
| `r` | — | `.ref` | References declaration (parameter lists related context strings; empty = none) |
| `g` | — | `.popup` | Mark topic for popup display in a temporary window |
| `x` | comment text | — | Author/editor annotation; never displayed (compiler metadata) |
| `u` | — | — | Observed in QBX; meaning unknown |

---

## 6. Attribute Block

The attribute block has two sections separated by `0xFF`:

```
[style bytes ...] 0xFF [link records ...]
```

**Style bytes** (before `0xFF`) encode character attributes using an alternating
list of `(ChunkLen, Style)` pairs. Each Style byte:

```
bits 7–3: reserved (0)
bit  2:   Underline
bit  1:   Italic
bit  0:   Bold
```

The first byte is always a ChunkLen (no leading Style; defaults to Normal).

**Link records** (after `0xFF`) each describe one hyperlink:

```
BYTE  StartIndex  1-based index of first link character (inclusive)
BYTE  EndIndex    1-based index of last link character (inclusive)
                  = 0-based exclusive byte-slice end
NUL-terminated context string  (empty string → use inline WORD index instead)
[WORD TopicIndex]              present only when context string is empty;
                               high bit may be set as a marker — mask with 0x7FFF
```

If the context string is non-empty it is looked up in the `ContextMap`.
If the context string is empty, the following `WORD` gives the topic index
directly.
After masking its marker bit, the direct index must be below this database's
`TopicCount`; it is not an external context number.

Links whose context strings are built-in commands are handled as navigation
actions (§9). Cross-database references are resolved against every logical
database in the current file and sibling QuickHelp `.HLP` files in the same
source directory, regardless of extension case. Explicit `FILE.HLP!context` links
and the Microsoft Advisor variant `DATABASE.context` (for example
`OS2.h.overview`) are preserved as external links even if that optional file
or context is not currently available.
The explicit qualifier identifies a database namespace. A destination absent
from that namespace is unresolved; it is not an instruction to substitute a
similar title or a same-named context from another database. Original files
can contain erroneous qualifiers: `QB45QCK.HLP` refers to
`AB45ADVR.HLP!.erasex`, while its distribution contains `QB45ADVR.HLP`.
This mismatch is source data, not a different qualifier grammar.

Parse every link record within its attribute block. A lone range byte,
unterminated context string or missing inline target WORD is an incomplete
record, not a plain-text/no-link alternative.

Observed source anomaly: in QuickC/C 6.0 `CLANG.HLP`, seven link records have
`EndIndex = text byte count + 1` (topics 750, 754, 760, 766 and 1029, with some
containing multiple such records). This does not encode an extra display
character. A defensive renderer can bound the highlighted range to existing
text while retaining the stored destination; it must not read into attributes.
This is not evidence for shifting every LN link's coordinates by one.

---

## 7. Highlight Markers (0x11 / 0x10)

QuickHelp stores `0x11` **before** and `0x10` **after**
link text as visual selection markers visible in the original QuickHelp viewer.

The link `StartIndex`/`EndIndex` values in the attribute block are measured
over the **raw text bytes including these markers**. Bytes `11h` and
`10h` display as CP437 left/right pointer glyphs (`◄` / `►`). Removing
them changes coordinate positions; any transformed display must explicitly
map raw byte ranges to its displayed columns.

---

## 8. Index and Topic Titles

A `:n` command stores the title independently of display lines. Context
strings are link identifiers, not a guaranteed human-readable title. If no
`:n` is present, the file has no separate authoritative title field.

---

## 9. Navigation Contexts

QuickHelp defines several **built-in navigation context strings** that are not
topics in the local database but trigger viewer-level actions.  They appear as
link targets in many QBX / Microsoft help files.

### 9.1 !B — Go Back

Context string `!B` (case-insensitive) means "navigate back in history".

### 9.2 !hv — Contents (Home View)

Context string `*!HV` (suffix, case-insensitive, e.g. `pwb.hlp!hv`) means
"go to the home topic of the named database". Bare `!HV` and `-9996` use the
current database; in a concatenated file, this is not always the first database.

### 9.3 !vx — Index

Context string `*!VX` (suffix, case-insensitive, e.g. `pwb.hlp!vx`) means
"open the index of the named database". Bare `!VX` uses the current database.

### 9.4 Numeric predefined contexts (-9996, -9997)

Some Microsoft QBX supplementary databases (e.g. `BAS7ADVR.HLP`) use the
literal strings `"-9996"` and `"-9997"` as link targets for Contents and
Index respectively.  These are treated the same as `!HV` and `!VX`.

| Context string pattern | Viewer action |
|------------------------|---------------|
| `!B` | Back (history) |
| `*!HV` | Contents — go to help contents topic |
| `*!VX` | Index — open index page |
| `-9996` | Contents (numeric predefined context) |
| `-9997` | Index (numeric predefined context) |

### 9.5 Cross-file help links

QuickHelp references can name another database explicitly, for example:

```text
CV.HLP!cv.contents
```

The name can identify a physical file or a logical `DatabaseName` in a
concatenated container. Resolve context names using that database's case rule;
DOS filename qualifiers remain case-insensitive. Original filename extensions
are significant: `MISC.HLP` and `MISC.TXT` are not the same namespace.

Duplicate names in different product/release collections need the application's
search path or another explicit binding. That selection is not stored in a
link record. A missing file or context remains a missing destination.

The tiny QuickC 2.50 `QA.HLP` (445 bytes, two contexts including
`taw080554`) is an original null search-order placeholder. Small file size
alone does not establish corruption.

---

## 10. File Layout Diagram

```text
┌────────────────────────────────┐  0x00
│  Header (0x46 bytes)           │
├────────────────────────────────┤  TopicIndexOffset
│  TopicIndex (TopicCount+1 × 4) │  DWORD offsets into TopicText
├────────────────────────────────┤  ContextStringsOffset
│  ContextStrings                │  NUL-terminated packed strings
├────────────────────────────────┤  ContextMapOffset
│  ContextMap (ContextCount × 2) │  WORD topic indices
├────────────────────────────────┤  KeywordsOffset (optional)
│  Keywords                      │  length-prefixed strings
├────────────────────────────────┤  HuffmanTreeOffset (optional)
│  HuffmanTree                   │  signed INT16 array, 0-terminated
├────────────────────────────────┤  TopicTextOffset
│  TopicText                     │  compressed topic blobs
└────────────────────────────────┘  DatabaseSize
```

### Structural boundaries

The non-absent sections follow the order above. `TopicIndex` must contain all
`TopicCount + 1` DWORDs before context strings, context strings must contain
their NUL terminators before the map, and all map WORDs precede compression
tables/text. No offset can point into the 70-byte header or beyond the declared
database. An absent compression table has a zero header pointer, not a fake
pointer into another section. These are database-local bounds; a following
concatenated database cannot supply missing bytes to the previous one.

---

## 11. Format examples

| Product | HLP file | Notes |
|---------|----------|-------|
| QuickBasic 4.5 / QBX 7.1 | `QB.HLP`, `BAS7*.HLP` | LN database |
| QuickC 2.x | `QC.HLP` | Full format |
| MASM 6.x | `MASM.HLP` | Full format |
| Microsoft PWB | `PWB.HLP` | Full format |
| MS LINK | `LINK.HLP` | Full format |
| MS-DOS QH utility | `QH.HLP`, `UTILS.HLP` | Minimal, no Huffman |

Older `CV.HLP` / `CVP.HLP` files from the DOS / OS/2 CodeView line can use the
separate `BW03` format documented in [Microsoft BW03 Help.md](Microsoft%20BW03%20Help.md).
