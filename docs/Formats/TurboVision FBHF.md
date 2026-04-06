# TurboVision FBHF Format

> Created: 2026-03-29 · Last updated: 2026-03-29

Used by: Turbo Vision applications (TP6, TP7, BP7). Created by TVHC compiler.
File extension: `.HLP`.

Implementation: `HELPFILE.PAS` unit (THelpFile, THelpTopic, THelpIndex).  
Uses Turbo Vision TStream object persistence (TStream.Put/Get with StreamRec).

All multi-byte integers are little-endian.

### 2.1 File Layout

```
┌──────────────────────────────────────┐  Offset 0
│  Magic: "FBHF" ($46 $48 $42 $46)    │  4 bytes
├──────────────────────────────────────┤  Offset 4
│  FileSize − 8 (LongInt)             │  4 bytes
├──────────────────────────────────────┤  Offset 8
│  IndexPos (LongInt)                  │  4 bytes → points to Index
├──────────────────────────────────────┤  Offset 12
│  Topic 0: ObjType(Word) + Store()   │  variable
│  Topic 1: ObjType(Word) + Store()   │
│  ...                                 │
│  Topic N: ObjType(Word) + Store()   │
├──────────────────────────────────────┤  Offset = IndexPos
│  Index: ObjType(Word) + Store()     │  THelpIndex
└──────────────────────────────────────┘
```

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

```
┌──────────────────────────────────────────┐
│  NumParagraphs (Integer = 2 bytes)       │
├──────────────────────────────────────────┤
│  Paragraph 0:                            │
│    Size (Integer = 2 bytes)              │  text byte count
│    Wrap (Boolean = 1 byte)               │  0=non-wrapping, 1=wrapping
│    Text (Size bytes)                     │  raw paragraph content
│  Paragraph 1: ...                        │
│  ...                                     │
├──────────────────────────────────────────┤
│  NumCrossRefs (Integer = 2 bytes)        │
├──────────────────────────────────────────┤
│  CrossRef 0:                             │
│    Ref (Word = 2 bytes)                  │  target context number
│    Offset (Integer = 2 bytes, signed)    │  1-based byte offset in topic
│    Length (Byte = 1 byte)                │  highlighted text length
│  CrossRef 1: ...                         │
│  ...                                     │
└──────────────────────────────────────────┘
```

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

```
┌──────────────────────────────────────┐
│  Size (Word = 2 bytes)               │  allocated array size
├──────────────────────────────────────┤
│  Index[0] (LongInt = 4 bytes)        │  file position of topic 0
│  Index[1] ...                        │  ...or -1 ($FFFFFFFF) if unused
│  ...                                 │
│  Index[Size-1]                       │
└──────────────────────────────────────┘
```

Context number = array index. `Index[ctx]` = file offset of topic,
or `-1` if context not defined.

**Detection:** `idx_pos + 2 + 2 + Size*4 == FileSize`

#### BP7 Variant (sorted contexts)

Written by BP7's `THelpIndex.Store`:

```
┌──────────────────────────────────────┐
│  Used (Word = 2 bytes)               │  number of active entries
├──────────────────────────────────────┤
│  Size (Word = 2 bytes)               │  allocated array size (≥ Used)
├──────────────────────────────────────┤
│  Contexts[0] (Word = 2 bytes)        │  sorted context numbers
│  Contexts[1] ...                     │  unused slots = $FFFF
│  ...                                 │
│  Contexts[Size-1]                    │
├──────────────────────────────────────┤
│  Positions[0] (LongInt = 4 bytes)    │  file position for Contexts[0]
│  Positions[1] ...                    │  unused slots = -1
│  ...                                 │
│  Positions[Size-1]                   │
└──────────────────────────────────────┘
```

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
