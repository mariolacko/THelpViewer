# TurboVision FBHF Format

> Created: 2026-03-29 · Last updated: 2026-10-11

Used by: Turbo Vision applications (TP6, TP7, BP7). Created by TVHC compiler.
File extension: `.HLP`.

Implementation: `HELPFILE.PAS` unit (THelpFile, THelpTopic, THelpIndex).  
Uses Turbo Vision TStream object persistence (TStream.Put/Get with StreamRec).

All multi-byte integers are little-endian.

### 2.1 File Layout

| Offset | Field | Size / meaning |
|---:|---|---|
| `0` | Magic `FBHF` (`$46 $42 $48 $46`) | 4 bytes |
| `4` | `FileSize - 8` | `LongInt`, 4 bytes |
| `8` | `IndexPos` | `LongInt`, 4 bytes; points to the index object |
| `12` | Topic objects: `ObjType(Word) + Store()` | Variable; indexed by file offset, not necessarily by context order |
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
| 1 | `NumParagraphs` | 2 bytes, signed `Integer` | Nonnegative number of paragraph records |
| 2 | `Size` | 2 bytes | Text byte count for each paragraph |
| 3 | `Wrap` | 1 byte | `0` = non-wrapping, `1` = wrapping |
| 4 | `Text` | `Size` bytes | Raw paragraph content; steps 2–4 repeat for every paragraph |
| 5 | `NumCrossRefs` | 2 bytes, signed `Integer` | Nonnegative number of cross-reference records |
| 6 | `Ref` | 2 bytes | Target context number for each cross-reference |
| 7 | `Offset` | 2 bytes, signed | 1-based byte offset in the topic |
| 8 | `Length` | 1 byte | Highlighted text length; steps 6–8 repeat for every cross-reference |

**Important details:**

- **Cross-ref offsets are 1-based starts**, not end positions. The viewer
  calculates screen position with `Loc.X := Offset - OldOffset - 1`, so
  offset 1 maps to the first byte of the topic.
- **Cross-ref offsets are global** across all paragraphs in a topic. Paragraph
  texts are conceptually concatenated — offset counts from beginning of
  first paragraph's text through all paragraphs.
- **Spaces in cross-ref text are stored as `$FF`** (not `$20`). The
  `ReplaceSpacesWithFF` routine converts spaces to `$FF` so the word-wrap
  algorithm doesn't break inside hyperlink text.
- **Cross-ref target resolution is case-insensitive.** TVHC compares names
  by `UpStr`, not by exact case.

#### Cross-reference positions

The range is `[Offset - 1, Offset - 1 + Length)` in the concatenated paragraph
texts. All bytes count, including `0Dh`, `FFh` and spaces consumed at a wrap
boundary. Paragraph headers do not count. Paragraph boundaries do not restart
the stored offset; byte offsets and screen columns are different coordinates.

For native `GetCrossRef`, traverse rows with the algorithm below until their
global **consumed end** is at least `Offset`. Let `OldOffset` be that row's
global byte start. Return `X = Offset - OldOffset - 1`, its one-based row
number as `Y`, and the stored `Length` and `Ref` unchanged. The native drawing
routine changes `Length` cell attributes on the row containing the start;
it does not turn an exceptional cross-row range into several references.
The compiler's non-breaking label bytes normally prevent a split inside
a link. A decoder must not infer the target from the label or change a
target simply because that context is absent from the index.

#### Paragraph Text Encoding

FBHF Text bytes are stored directly. The related Software602 Text602/Calc602
stream uses the same paragraph/reference object fields but stores every Text
byte plus one modulo 256; that transformation does not apply to FBHF fields
or text. See [Software602 Text602](Software602%20Text602.md) for its distinct
ASCII stamp/header and encoded-byte examples.

**Non-wrapping paragraphs** (Wrap=0):
- Lines separated by `$0D` (CR)
- Source lines begin with a space character
- Leading CRs represent blank lines inherited from source

**Wrapping paragraphs** (Wrap=1):
- Words separated by `$20` (space)
- Viewer performs word-wrap at display width
- Source lines do NOT begin with a space

#### Native byte-based row layout

Width is a viewer property, not a file-header field. The standard Pascal
`THelpWindow` has outer bounds `(0,0,50,18)` and the `THelpViewer` bounds are
shrunk by two columns and one row on each side: its initial text width is
**46**, height **16**. `ChangeBounds` supplies the viewer's new width to the
topic; wrapped paragraphs can therefore have different rows after resizing.
The horizontal scroll limit is initialized to 78 independently of wrap width.

For a paragraph of `N` bytes, use cursor `C = 0`. Repeat while `C < N`:

1. Scan at most `min(N-C, 256)` bytes for the first `0Dh`. Candidate length
   includes that CR if found; otherwise it is the scanned byte count.
2. If `Wrap=1` and candidate length is **at least** width `W`, propose
   `E = min(C+W, N)`. For an in-buffer proposed boundary, inspect `Text[E]`
   (the byte after the first `W` proposed cells), walking backwards until a
   blank byte or `C`. Blank means **only** `20h`, `0Dh` or `0Ah`; `FFh` is
   never a blank. If a blank is found strictly after `C`, consume it too,
   setting `E = blank_position+1`. Otherwise split at `C+W`. A width proposal
   beyond the paragraph end stops at `N`.
3. For `Wrap=0`, use the candidate end without word wrapping. A paragraph
   ending in CR does not produce another empty row; an actual leading or
   repeated CR does produce an empty row.
4. The row is the byte interval `[C,E)`. Remove **only** a final CR from its
   visible text, not from the consumed count. Preserve leading/trailing
   spaces, internal LF and all other character bytes. Advance `C = E`.

The selected blank is part of the consumed row; an ordinary space remains
in the native string. Do not use `split(CR)` with a terminal empty element,
trim text, add an indentation byte or substitute `FFh` before word wrapping.
In DOS OEM fonts `FFh` is a blank/non-breaking cell. Other low bytes are
character cells, not inline bold or hyperlink delimiters.

The native Pascal string has a one-byte length. A 256-byte copy wraps that
length to zero even though the byte cursor advances; it is not a valid
255-character string. Readers should detect this boundary rather than
silently turning an overlong non-wrapping line into an empty successful row.
The Pascal routine may inspect `Text[N]` when a width proposal equals `N`;
that byte lies outside the stored paragraph and its value is not specified
by FBHF. A bounded decoder must not read a following serialized field as
text. This edge has no defined byte-independent native layout.

Example at width 6, `Wrap=1`:

```text
Text: 61 62 63 20 64 65 66 20 67 68 69 0D   "abc def ghi\r"
Row 1: bytes [0,4)   "abc "
Row 2: bytes [4,8)   "def "
Row 3: bytes [8,12)  "ghi"; CR consumes byte 11, no column
Ref=7, Offset=5, Length=3 -> row 2, X=0, highlighted "def"
```

If the first separating space is `FFh`, the first row instead consumes
six bytes (`abc`, non-breaking blank, `de`): `FFh` cannot be a wrap point.

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
`Size = 0` is a valid empty index: only its object type and size WORD exist.

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
Only its first `Used` entries are active; `Used <= Size`. Active contexts are
strictly increasing. Unused allocated slots do not create topics.
Size is rounded up: `Size = ((Used + Delta) div Delta) * Delta` where `Delta = 10`.

**Detection:** `idx_pos + 2 + 4 + Size*6 == FileSize`

#### Aliases and object bounds

Different context numbers can store exactly the same topic position. TVHC
records every name on a `.topic` line at the current position before writing
one topic object. This is an alias, not two overlapping serializations or a
reason to discard one context number. Topic positions must address a
`10000` object after the 12-byte header and before the index object. They are
not required to be increasing in context order.

Read the header before either index variant; check its length field and
`IndexPos`, then the index object's type and complete arrays. While reading
an indexed topic, bound paragraph headers/text, reference count and all
five-byte reference records before the next distinct indexed topic position,
or `IndexPos` for the final indexed object. Shared positions use the same
bound. Do not require an object to consume the entire interval: unindexed
older objects can remain between live positions after an update.

For a reference, `Offset >= 1` and
`Offset - 1 + Length <= sum(paragraph.Size)`. The range counts text bytes,
not paragraph headers or object fields. A missing destination context does
not invalidate a correctly stored range: the native viewer supplies its
no-help placeholder rather than binding a different topic.

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

- Lines starting with `;` have no visible comment text; native `GetLine`
  returns an empty line, so a mid-topic comment creates a paragraph boundary
- `.topic` defines a new topic with name and context number; command spelling
  is case-insensitive (`.TOPIC` is the same command)
- Multiple names receive context numbers but map to the same topic object
- Empty lines create paragraph boundaries
- `{text:target}` creates a cross-reference hyperlink
- Source is byte text with CRLF line endings; the DOS application's character
  set determines interpretation of high bytes. No encoding identifier is stored.
- A line containing **only** DOS EOF `1Ah` ends input. A `1Ah` byte followed
  by text, or inside a line, is a literal character cell, not an EOF sentinel.

#### Physical lines, tokens and limits

The DOS `GetLine` reads bytes through CR and reads one additional byte to
skip LF. Standard physical lines are therefore `text + 0Dh 0Ah`. It reads
at most 254 bytes before decrementing its byte counter to remove the CR:
a well-formed physical line has at most **253 text bytes**, excluding CRLF.
Longer input can desynchronize native line reading; do not silently split or
truncate it. These are byte counts, not Unicode character counts. Neither
vertical tab `0Bh`, form feed `0Ch` nor other low character bytes separate
physical lines.

`GetWord` skips only space `20h` and backspace `08h` between header tokens.
It returns the maximal run of `[A-Za-z0-9_]`, or one other byte as a token.
Common topic names use that ASCII word alphabet. Tabs are not header-token
whitespace. The command has a separate `.` token followed by case-insensitive
`TOPIC`; `. topic` is also recognized. Commas separate definitions and `=`
introduces a numeric value. After a definition, a token other than comma ends
the list; the native parser ignores the rest of that header line. A period
in column 1 ends the preceding paragraph and starts command parsing; text
requiring a literal initial period can use a non-wrapping leading space.

Symbol names and reference names are compared using ASCII uppercase:
subtract `20h` from bytes `61h..7Ah`, leaving all other bytes unchanged.
Do not apply Unicode case folding: a high DOS byte is not the two-byte name
`ss`, for example. A second definition of the same folded name is a fatal
`Redefinition` error, including two names on the same header. Malformed
numeric definitions and unterminated brace references are also fatal.

`ReadParagraph` uses a **4096-byte** buffer. Its stored text size includes
leading blank/comment CRs and the space/CR appended to every processed line.
Each append must fit, including that final byte. This is a compiler-buffer
limit, not a new bound on the WORD `Size` in arbitrary FBHF binary records.
Paragraph and reference counts are signed nonnegative 16-bit integers;
reference starts must fit `1..32767`. A larger source cannot be represented
by those fields without native overflow.

#### Brace-reference scanner

Process a mutable physical byte line, with search cursor initially zero:

1. Find `{` at or after the cursor. If its following byte is also `{`,
   remove that **second** brace and resume one byte after its former index.
   This cursor advance matters for runs of three or more braces.
2. Otherwise find the first following `}` on the same physical line.
   Its absence is an unterminated-reference error; there is no continuation
   onto another source line.
3. Split the inside bytes at the first `:` if present. The prefix is the
   visible label, the suffix the target name. Without `:`, the unmodified
   label bytes are also the target name. Target whitespace is not trimmed.
4. Record one-based start `topic_bytes_before_line + opening_brace_index + 1`
   and the label's byte length. The topic count includes every previously
   stored paragraph byte, not its record headers.
5. Replace label spaces `20h` by `FFh`, replace the whole brace expression
   with that label, and resume immediately after the inserted label.

Bare closing braces are literal text. An empty label has length zero. The
unresolved forward-reference WORD initially contains `FFFFh`; resolving a
symbol patches that WORD to its numeric context. A name still unresolved
at compilation end produces a warning and leaves `FFFFh` in the file. That
value can address a real context `FFFFh` if one exists; otherwise it has the
same missing-context behavior as a binary reference. It is not a label-based
guess at another destination.

```text
Input:  See {A B:Target}.
Text:   53 65 65 20 41 FF 42 2E 20   "See A(nonbreaking)B. "
Ref:    Offset=5, Length=3, target context supplied by symbol Target

Input       Stored line before its appended paragraph separator
{{A}        {A}       (literal; no reference)
{{{A}       {{A}      (literal; no reference)
{{{{A}      {{A       (A is a reference starting at column 3)
```

#### Context-number assignment

The counter begins at 2. An explicit `Name=number` sets both that name's
context and the counter. An ordinary name without `=` increments the counter
and receives its new value; this also applies to further names on the same
line. The counter is a 16-bit `Word` and wraps after `FFFFh`.

The BP7 TVHC source contains predefined APP contexts. A name spelled exactly
as below, without an explicit number, uses its fixed context and does **not**
change the counter. Explicit numbers override this lookup. Cross-reference
name matching remains case-insensitive.

| Name | Context | Name | Context |
|---|---:|---|---:|
| Dragging | `0001h` | New | `FF01h` |
| Open | `FF02h` | Save | `FF03h` |
| SaveAs | `FF04h` | SaveAll | `FF05h` |
| ChangeDir | `FF06h` | DosShell | `FF07h` |
| Exit | `FF08h` | Undo | `FF10h` |
| Cut | `FF11h` | Copy | `FF12h` |
| Paste | `FF13h` | Clear | `FF14h` |
| Tile | `FF20h` | Cascade | `FF21h` |
| CloseAll | `FF22h` | Resize | `FF23h` |
| Zoom | `FF24h` | Next | `FF25h` |
| Prev | `FF26h` | Close | `FF27h` |

Example: `.topic Open, OpenFile` assigns `FF02h` and `0003h` to one object;
the next ordinary name receives `0004h`.

#### Reusing a numeric context

Distinct symbol names may explicitly use the same numeric context. The
later `THelpIndex.Add` replaces that context's file position while leaving
its earlier name-to-number resolution intact. It does **not** redefine the
symbol name. Other numeric aliases of the earlier object remain indexed;
an object whose last live context was replaced becomes unindexed.

For example, after `.topic First=2, Alias=20` followed by
`.topic Replacement=2`, context 20 still addresses the first object's text,
while both symbolic references `First` and `Replacement` have value 2 and
address the replacement object. Do not publish two different texts under
the same context, discard the surviving alias, or bind `First` back to the
obsolete file position. Several names using the same number at the same
file position do not create duplicate index slots.

### 2.5 Decompiler Reconstruction Rules

To build a compatible FBHF decompiler:

1. Read the 12-byte file header and seek to `IndexPos`.
2. Detect which `THelpIndex` variant is stored:
   TP6 dense array or BP7 sorted contexts array.
3. Build a map from topic file offset to all of its context numbers.
4. Parse each topic object:
   paragraph count, paragraph records, cross-reference array.
5. Reconstruct source:
   use `.topic Name=Number` or synthetic topic names,
   restore wrapping vs non-wrapping lines from paragraph `Wrap`,
   and convert cross-reference ranges back into `{text:target}` markup.
6. Convert `$FF` back to spaces inside hyperlink text.

Arbitrary binary paragraphs need not have a lossless TVHC textual form:
for example, `Wrap=0` text without a leading space cannot be represented by
an ordinary non-wrapping source line without adding a byte. Keep binary
paragraph bytes and `Wrap` separate from an optional source reconstruction.

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
- comment lines beginning with `;` supply an empty line, not visible text

### 2.8 Minimal Binary Example

An empty TP6 database is 16 bytes, including its index object:

```text
46 42 48 46  08 00 00 00  0C 00 00 00  11 27  00 00
FBHF         length-8    IndexPos=12  type   Size=0
```

There are no topic objects. For an empty BP7 index replace the final `00 00`
with `00 00 00 00` (`Used=0`, `Size=0`) and set the length field to `0Ah`;
the file becomes 18 bytes. Never read a BP7 `Size` WORD from beyond an empty
TP6 index merely to attempt variant detection.

---
