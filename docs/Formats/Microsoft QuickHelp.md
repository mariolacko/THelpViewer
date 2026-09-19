# Microsoft QuickHelp LN Format

> Created: 2026-04-07 · Last updated: 2026-09-19

Used by: Microsoft QuickBasic 4.5, QuickC 2.0, MASM 6, PWB, LINK, later CodeView bundles, and compatible products.
File extension: `.HLP` (LN binary database).

**Authoritative format specification:**
[fancidev/DosHelp — Format.txt](https://raw.githubusercontent.com/fancidev/DosHelp/master/QuickHelp/Serialization/Format.txt)
(MIT licence; this document summarises the most relevant parts with implementation notes.)

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
04-06  WORD  Attributes        bit 0 = CaseSensitive context strings
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
42-46  DWORD DatabaseSize      total file size
```

---

## 3. Sections

### 3.1 TopicIndex

`TopicCount + 1` DWORDs at `TopicIndexOffset`.
Each entry is an offset into `TopicText` (relative to file start).
Topic *i* occupies bytes `TopicIndex[i]` through `TopicIndex[i+1] - 1`.

### 3.2 ContextStrings

`ContextCount` NUL-terminated ASCII strings packed consecutively.
These are the human-visible or internal context names used for linking.

### 3.3 ContextMap

`ContextCount` WORDs at `ContextMapOffset`.
`ContextMap[i]` = topic index for `ContextStrings[i]`.

Context lookup is case-insensitive unless `Attributes & 0x01` is set.

### 3.4 Keywords (optional)

Length-prefixed byte strings packed consecutively.
Each entry: `BYTE length` followed by `length` bytes of keyword text.
Absent when `KeywordsOffset == 0`; in that case treat as empty dictionary.

Used by Step 2 decompression (keyword substitution).

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

### Stage 1 → Binary topic decompile

Input: binary topic data from Stage 2.
Output: display lines + attribute records.

The binary stream is a sequence of `(TextBlock, AttrBlock)` pairs:

```
BYTE  TextLen        length of text data + 1 (0 = end of topic)
BYTE  text[TextLen-1]
BYTE  AttrLen        length of attribute data + 1 (0 = end of topic)
BYTE  attr[AttrLen-1]
```

A `TextLen == 0` or `AttrLen == 0` terminates the topic.

---

## 5. Command Lines

A text block whose first byte equals `ControlCharacter` is a **command line**.
It is not displayed; instead the second byte selects the command.
Parameters follow immediately (no separator between command byte and parameter).

### Known commands (observed across QB 4.5 / QBX / MASM / CV / PWB / LINK)

| Cmd | Parameter | Source directive | Meaning |
|-----|-----------|-----------------|---------|
| `n` | topic title | `.topic` | Human-readable topic title stored in `topic.names[]` |
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

**Implementation note:** the reader extracts `:n`, `:l`, `:c`, `:i`, and `:g`
into topic names, frozen-row count, category navigation, list state, and popup
state respectively. Other command lines remain invisible and are filtered from
`raw_lines`.

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
                  = 0-based exclusive slice end when used with raw_lines
NUL-terminated context string  (empty string → use inline WORD index instead)
[WORD TopicIndex]              present only when context string is empty;
                               high bit may be set as a marker — mask with 0x7FFF
```

If the context string is non-empty it is looked up in the `ContextMap`.
If the context string is empty, the following `WORD` gives the topic index
directly.

Links whose context strings are built-in commands are handled as navigation
actions (§9). Cross-file references are resolved against sibling QuickHelp
`.HLP` files in the same source directory. An explicit `FILE.HLP!context`
reference is preserved as an external link even if that file or context is not
currently available.

---

## 7. Highlight Markers (0x11 / 0x10)

QuickHelp stores `0x11` **before** and `0x10` **after**
link text as visual selection markers visible in the original QuickHelp viewer.

The link `StartIndex`/`EndIndex` values in the attribute block are measured
over the **raw text bytes including these markers**.  Our reader:

1. Keeps the markers visible in UHF output as `◄` / `►`.
2. Strips them only from stored `raw_lines`, so title/index heuristics do not
   see decorative tab markers.
3. Leaves link column positions in raw-byte coordinates, because the visible
   UHF line still contains one character per marker.

---

## 8. Index and Topic Titles

Topic titles come from `:n` command lines, stored in `topic.names[]`.

When no `:n` command is present, the first non-empty `raw_line` (stripped of
leading/trailing whitespace) is used as the human-readable index label.
Context strings (e.g. `h.pg1`, `.cccp`) are internal identifiers used only
as a last resort.

---

## 9. Navigation Contexts

QuickHelp defines several **built-in navigation context strings** that are not
topics in the local database but trigger viewer-level actions.  They appear as
link targets in many QBX / Microsoft help files.

### 9.1 !B — Go Back

Context string `!B` (case-insensitive) means "navigate back in history".

### 9.2 !hv — Contents (Home View)

Context string `*!HV` (suffix, case-insensitive, e.g. `pwb.hlp!hv`) means
"go to the main/first topic of the current database" (Contents view).

### 9.3 !vx — Index

Context string `*!VX` (suffix, case-insensitive, e.g. `pwb.hlp!vx`) means
"open the topic index of the current database".

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

The converter preserves this as a UHF link containing the source filename and
alias. If the sibling file is present, it also stores the resolved topic id:

```text
[link:file=CV.HLP,topic=90,alias=cv.contents]...[/link]
```

If the explicitly named file is absent, the link remains real and keeps
`file=CV.HLP,alias=cv.contents`; it is not downgraded to plain text. It starts
working automatically when a matching bundle is later added to the catalog.

A bare unresolved alias is searched across sibling `.HLP` files and becomes an
external link only when exactly one file matches. Ambiguous bare aliases stay
plain because the source format does not identify which database was intended.

At display time, duplicate filenames such as `CV.HLP`, `PWB.HLP`, `LINK.HLP`,
or `UTILERR.HLP` are resolved in this order:

1. same catalog collection/group as the current help file;
2. same product and version;
3. first remaining filename match as a compatibility fallback.

---

## 10. File Layout Diagram

```
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

---

## 11. Supported Products

| Product | HLP file | Notes |
|---------|----------|-------|
| QuickBasic 4.5 / QBX 7.1 | `QB.HLP`, `BAS7*.HLP` | Full format |
| QuickC 2.x | `QC.HLP` | Full format |
| MASM 6.x | `MASM.HLP` | Full format |
| Microsoft PWB | `PWB.HLP` | Full format |
| MS LINK | `LINK.HLP` | Full format |
| MS-DOS QH utility | `QH.HLP`, `UTILS.HLP` | Minimal, no Huffman |

Older `CV.HLP` / `CVP.HLP` files from the DOS / OS/2 CodeView line can use the
separate `BW03` format documented in [Microsoft BW03 Help.md](Microsoft%20BW03%20Help.md).

---

*Part of the [THelpViewer](https://github.com/) project.*
