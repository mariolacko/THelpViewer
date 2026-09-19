# TurboVision FBHF Format

> Created: 2026-03-29 · Last updated: 2026-09-19

Used by: Turbo Vision applications (TP6, TP7, BP7). Created by TVHC compiler.
File extension: `.HLP`.

Implementation: `HELPFILE.PAS` unit (THelpFile, THelpTopic, THelpIndex).  
Uses Turbo Vision TStream object persistence (TStream.Put/Get with StreamRec).

All multi-byte integers are little-endian.

### 2.1 File Layout

| Offset | Field | Size / meaning |
|---:|---|---|
| `0` | Magic `FBHF` (`$46 $48 $42 $46`) | 4 bytes |
| `4` | `FileSize - 8` | `LongInt`, 4 bytes |
| `8` | `IndexPos` | `LongInt`, 4 bytes; points to the index object |
| `12` | Topic objects: `ObjType(Word) + Store()` | Variable; topics 0 through N are consecutive |
| `IndexPos` | Index object: `ObjType(Word) + Store()` | Variable `THelpIndex` object |

Each object is written by `TStream.Put`:
1. ObjType (Word) from StreamRec registration
2. Object's `Store()` method writes the rest

**StreamRec registrations:**
- THelpTopic: ObjType = `10000` (`$2710`)
- THelpIndex: ObjType = `10001` (`$2711`)

### 2.1.1 Minimal Compiler Recipe

To build a compatible FBHF compiler:

1. Parse `.topic` source into topics, aliases and paragraph text.
2. Convert each topic into one `THelpTopic` object:
   paragraph list + cross-reference array.
3. Write all topics preceded by `ObjType = 10000`.
4. Build `THelpIndex` from context number → topic file offset.
5. Write the index object preceded by `ObjType = 10001`.
6. Patch the 12-byte file header with `FBHF`, `FileSize-8` and `IndexPos`.

### 2.2 THelpTopic Store Format

Written by `THelpTopic.Store(var S: TStream)`:

| Order | Field | Size | Meaning |
|---:|---|---:|---|
| 1 | `NumParagraphs` | 2 bytes | Number of paragraph records |
| 2 | `Size` | 2 bytes | Text byte count for each paragraph |
| 3 | `Wrap` | 1 byte | `0` = non-wrapping, `1` = wrapping |
| 4 | `Text` | `Size` bytes | Raw paragraph content; steps 2–4 repeat for every paragraph |
| 5 | `NumCrossRefs` | 2 bytes | Number of cross-reference records |
| 6 | `Ref` | 2 bytes | Target context number for each cross-reference |
| 7 | `Offset` | 2 bytes, signed | 1-based byte offset in the topic |
| 8 | `Length` | 1 byte | Highlighted text length; steps 6–8 repeat for every cross-reference |

**Important details:**

- **Cross-ref offsets are 1-based.** The viewer calculates screen position with
  `Loc.X := Offset - OldOffset - 1` (HELPFILE.PAS line ~282), so offset 1
  maps to the first byte of the topic.
- **Cross-ref offsets are global** across all paragraphs in a topic. Paragraph
  texts are conceptually concatenated — offset counts from beginning of
  first paragraph's text through all paragraphs.
- **Spaces in cross-ref text are stored as `$FF`** (not `$20`). The
  `ReplaceSpacesWithFF` routine converts spaces to `$FF` so the word-wrap
  algorithm doesn't break inside hyperlink text.
- **Cross-ref target resolution is case-insensitive.** TVHC compares names
  by `UpStr`, not by exact case.

#### Converter cross-reference reconstruction

The binary and textual readers resolve every cross-reference target through
the complete case-insensitive topic-name map before rendering. The stored
1-based global byte range is then projected back into its paragraph and
preserved as a real UHF link; it must not be discarded while flattening
paragraphs into display lines.

Inside the linked range, `$FF` is rendered as a normal space. This preserves
both the visible label and the original word-wrap protection used by
Turbo Vision.

#### Paragraph Text Encoding

**Non-wrapping paragraphs** (Wrap=0):
- Lines separated by `$0D` (CR)
- Source lines begin with a space character
- Leading CRs represent blank lines inherited from source

**Wrapping paragraphs** (Wrap=1):
- Words separated by `$20` (space)
- Viewer performs word-wrap at display width
- Source lines do NOT begin with a space

**Paragraph grouping rules** (TVHC compiler):
1. Empty source lines → `$0D` bytes prepended to the next paragraph
2. Consecutive source lines of the same type → merged into one paragraph
3. Type determined by first character: space = non-wrapping, other = wrapping
4. Trailing empty lines at end of topic → discarded

### 2.3 THelpIndex Store Format

Two variants exist depending on HELPFILE.PAS version:

#### TP6 Variant (simpler)

Written by TP6's `THelpIndex.Store`:

| Order | Field | Size | Meaning |
|---:|---|---:|---|
| 1 | `Size` | 2 bytes | Allocated array size |
| 2 | `Index[0..Size-1]` | 4 bytes each | Topic file position, or `-1` (`$FFFFFFFF`) when unused |

Context number = array index. `Index[ctx]` = file offset of topic,
or `-1` if context not defined.

**Detection:** `idx_pos + 2 + 2 + Size*4 == FileSize`

#### BP7 Variant (sorted contexts)

Written by BP7's `THelpIndex.Store`:

| Order | Field | Size | Meaning |
|---:|---|---:|---|
| 1 | `Used` | 2 bytes | Number of active entries |
| 2 | `Size` | 2 bytes | Allocated array size; at least `Used` |
| 3 | `Contexts[0..Size-1]` | 2 bytes each | Sorted context numbers; unused slots are `$FFFF` |
| 4 | `Positions[0..Size-1]` | 4 bytes each | File positions corresponding to `Contexts`; unused slots are `-1` |

Contexts array is sorted for binary search.
Size is rounded up: `Size = ((Used + Delta) div Delta) * Delta` where `Delta = 10`.

**Detection:** `idx_pos + 2 + 4 + Size*6 == FileSize`

### 2.4 TVHC Source Text Format

The TVHC compiler reads `.TXT` files with this syntax:

```
.topic TopicName=ContextNumber[, AnotherName]
 Non-wrapping line (starts with space)
 Another non-wrapping line

Wrapping paragraph line (no leading space)
Another wrapping line

{Highlighted text:TargetTopicName}
```

- Lines starting with `;` are comments (ignored)
- `.topic` defines a new topic with name and context number
- Multiple names can map to the same topic (comma-separated)
- Empty lines create paragraph boundaries
- `{text:target}` creates a cross-reference hyperlink
- File encoding: Latin-1 / CP437 with CRLF line endings

### 2.5 Decompiler Reconstruction Rules

To build a compatible FBHF decompiler:

1. Read the 12-byte file header and seek to `IndexPos`.
2. Detect which `THelpIndex` variant is stored:
   TP6 dense array or BP7 sorted contexts array.
3. Build a map from topic file offset to context number.
4. Parse each topic object:
   paragraph count, paragraph records, cross-reference array.
5. Reconstruct source:
   use `.topic Name=Number` or synthetic topic names,
   restore wrapping vs non-wrapping lines from paragraph `Wrap`,
   and convert cross-reference ranges back into `{text:target}` markup.
6. Convert `$FF` back to spaces inside hyperlink text.

### 2.6 Source-to-Binary Rules That Matter

These rules are required for byte-identical recompilation:

- Wrapping paragraphs append a trailing space byte (`$20`) after every
  physical source line, including the last line of the paragraph.
- Non-wrapping paragraphs append a trailing carriage return (`$0D`) after
  every physical source line.
- Empty source lines do not form standalone paragraphs; instead they emit
  leading `$0D` bytes that are prepended to the next paragraph.
- Trailing blank lines at end of topic are discarded.
- Cross-reference offsets are measured in the concatenated paragraph byte
  stream, starting at 1.
- BP7 index `Size` is not simple ceiling-to-10; when `Used` is already a
  multiple of 10, TVHC still allocates the next multiple of 10.

### 2.7 Recommended Textual Source Mapping

The standard textual form used by TVHC-compatible compilers is:

```text
.topic FileOpen=3, OpenFile
 File menu
 Open an existing file

Use {Open:FileOpen} to load a file.
```

Recommended conventions:

- first alias with explicit `=number` is the primary context
- following names on the same `.topic` line are aliases
- leading space means non-wrapping paragraph text
- no leading space means wrapping paragraph text
- `{text:target}` stores a cross-reference
- comment lines beginning with `;` are ignored by the compiler

---
