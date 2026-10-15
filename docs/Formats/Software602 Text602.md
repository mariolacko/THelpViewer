# Software602 Text602 / Calc602 Help Format

> Created: 2026-04-03 · Last updated: 2026-10-11

This format stores Turbo Vision THelpTopic and THelpIndex objects. Paragraph
text bytes are encoded by adding one modulo 256. It is distinct from
T6HLP/K6HLP directories and the XOR-FA M602 HelpSystem.

All multi-byte fields are little-endian. Object types and paragraph sizes
are unsigned WORDs. Paragraph/reference counts and reference offsets use
signed 16-bit Integer fields and must be nonnegative (offsets positive).
File addresses are absolute byte positions from the beginning of the file.

## 1. File header and layout

Known ASCII stamps, including their terminating CRLF:

- Text602: `Text602 - help  v.3.1   (c) Software602\r\n`
- Calc602: `Calc602 - help  v.1.00  (c) Software602\r\n`

Let H be the absolute position immediately after CRLF.

| Position | Size | Type | Meaning |
| --- | ---: | --- | --- |
| 0 | H | ASCII | Product/version stamp, including CRLF |
| H | 4 | LE32 | File size minus H+4 |
| H+4 | 4 | LE32 | Absolute address A of the index object |
| H+8 | variable | object stream | First topic object; further topic objects follow |
| A | variable | object stream | Index object, ending at EOF |

There is no fixed fifteen-byte binary header or delimiter terminating it:
the seven bytes after the two DWORDs belong to the first topic object.
In the two stamps above H=41, so the first object is at 49.

Size validation:

`file_size = H + 4 + LE32(H)`

The two inspected files have:

| Stamp family | Size DWORD | Index A | Total file bytes |
| --- | ---: | ---: | ---: |
| Text602 | 205086 (`03211Eh`) | 203687 (`031BA7h`) | 205131 |
| Calc602 | 211448 (`0339F8h`) | 210369 (`0335C1h`) | 211493 |

The topic area occupies [H+8, A). Decode records by their lengths/counts,
not by searching for byte 0Eh. It can occur in binary fields and is an
ordinary encoded CR inside paragraph text.

## 2. Topic object: type 2710h

Each object is written by a Turbo Vision stream as its registered type
WORD followed by the object's Store fields.

| Topic-relative position | Size | Type | Meaning |
| --- | ---: | --- | --- |
| +0 | 2 | LE16 | Object type 10000 (`2710h`, bytes `10 27`) |
| +2 | 2 | signed LE16 | Number P of paragraphs |
| +4 | variable | paragraph records | Exactly P records described below |
| after paragraphs | 2 | signed LE16 | Number R of cross references |
| after reference count | 5*R | reference array | Exactly R five-byte records |

The next object begins immediately after the final reference. There is no
seven-byte link-table trailer or link bank: a following `10 27` introduces
the next topic, with its paragraph count and first paragraph header.

An object can have no paragraphs, no references, or both. Its minimum size
is six bytes: `10 27 00 00 00 00`. Titles, footer text and horizontal rules
are authored text, not required record boundaries.

### 2.1 Paragraph record

| Paragraph-relative position | Size | Type | Meaning |
| --- | ---: | --- | --- |
| +0 | 2 | LE16 | Size S, number of stored text bytes |
| +2 | 1 | Boolean | Wrap: 00h fixed lines, 01h word wrapping |
| +3 | S | encoded bytes | Paragraph text |

Advance by 3+S bytes to the next paragraph. Size can be zero. A paragraph
can contain many CRs; those do not create additional binary records.

Text602's first object begins:

`10 27 14 00 1B 00 01 0E 5B C2 ...`

Interpretation:

- `10 27`: topic object type;
- `14 00`: twenty paragraphs;
- `1B 00`: first paragraph has 27 stored bytes;
- `01`: wrapping enabled;
- `0E`: first text byte, decoding to CR;
- `5B C2 ...`: encoded caption characters.

The next paragraph header follows those 27 bytes:

`4F 00 00 0E [99 repeated 77 times] 0E`

It has 79 text bytes, Wrap=0, and encodes CR + 77 glyph bytes + CR.
The 4Fh size byte is not a letter at the end of the previous title.

### 2.2 Text transform and controls

Decode every text byte, including control characters:

`decoded_byte = (stored_byte - 1) & FFh`

Encode with `(decoded_byte + 1) & FFh`.

| Stored | Decoded | Meaning |
| --- | --- | --- |
| 21h | 20h | Ordinary breakable space |
| 0Eh | 0Dh | CR, explicit line break |
| 0Bh | 0Ah | LF; considered whitespace by the wrapping search |
| 00h | FFh | Non-breaking separator; occupies one screen cell |
| 42h | 41h | Letter A |
| 99h | 98h | Application-font glyph, often used for rules/bullets |

The transform preserves paragraph byte count and therefore reference
positions. It applies only to Text fields: never subtract one from sizes,
counts, Wrap flags, context numbers or reference positions.

A low byte in a length/count can resemble a printable letter or a control.
Do not strip a three-byte prefix/suffix based on its numerical appearance,
remove trailing letters after punctuation, or infer paragraph boundaries
from text. Source-file binary metadata is outside the declared text range.

The stored text corpora contain no standalone 06h/07h line-break opcodes:
such apparent controls arise when binary fields are interpreted as text.
Only decoded CR is the explicit terminator used by GetLine.

### 2.3 Paragraph layout

Each paragraph has its own byte cursor, initially zero. Global text offsets
continue across paragraph boundaries. A paragraph ending without CR still
finishes its last visible row; the next paragraph begins a new row.

For a display width W (positive, normally less than 256):

1. Starting at cursor C, scan through the first CR, including it in the
   consumed range. Search at most 256 bytes and never pass paragraph Size.
   If no CR is found, the candidate range ends at that limit.
2. If Wrap=0, consume that entire candidate.
3. If Wrap=1 and candidate length is at least W, propose end C+W, bounded
   by Size. Search backwards from this position for an ordinary space,
   CR or LF. FFh is not a search delimiter.
4. If a delimiter is found strictly after C, consume through it, including
   that delimiter. If none is found, hard-split at the proposed end.
5. Copy the consumed bytes. Remove one terminal CR from the visible row,
   but keep other bytes and spacing. Advance C by the consumed count.

Leading and repeated CRs create genuine blank rows. Trailing spaces can be
part of a native row; do not globally trim them when mapping references.

The native routine copies into a Pascal short string. A consumed length
of 256 wraps its byte length to zero; this is a native rendering limitation,
not a different on-disk Size field. A decoder must not silently discard
such source text. The inspected paragraphs do not require such rows.

Wrap is a layout flag, not a context-sensitive/reference-screen type.
Titles can wrap; reference tables can contain many fixed lines. Error
screens do not require an underline or footer.

## 3. Cross-reference record

References follow all paragraphs of their own topic:

| Record-relative position | Size | Type | Meaning |
| --- | ---: | --- | --- |
| +0 | 2 | LE16 | Destination context |
| +2 | 2 | signed LE16 | One-based START byte position |
| +4 | 1 | unsigned byte | Highlighted range length L |

For a stored position O, the zero-based range is [O-1, O-1+L).
Positions count every decoded paragraph text byte, including CR and FFh,
but none of the topic/paragraph headers or reference records.

Text fields are conceptually concatenated in paragraph order. The +1
encoding changes values, not lengths. Thus stored and decoded text have
the same reference offsets. Require O>=1 and O-1+L<=total paragraph bytes.

A reference is not located by matching its label length to nearby rows,
searching for a caption, or treating O as an end coordinate. Several
unrelated references may have identical labels and lengths.

### 3.1 Mapping to screen coordinates

Retain each rendered row's starting global text offset B and the count of
bytes it consumes. Locate the row containing position O. Then:

- zero-based screen column = O-B-1;
- one-based screen row = that row's ordinal over all paragraphs;
- highlighted length = the stored L.

CR consumes a source byte but no visible column. If a range spans CR,
paragraph or wrapped-row boundaries, intersect it with every visible row
fragment while retaining its original destination.

FFh occupies a cell but is not a word-break opportunity. Source compilers
commonly use it inside multi-word link labels. It can be normalized to a
space for plain-text transcription; the default screen driver has a small
mid-line marker in that font slot (see section 6).

Example in Text602's `Menu soubor`: the first three paragraph sizes are
43, 79 and 52, totaling 174. The following fixed paragraph begins:

`0E 99 21 21 4F 70 77 DA ...`

These decode to CR, bullet, two spaces, then `Nový`.
Reference (101, 179, 4) starts at global zero-based byte 178, four bytes
into that paragraph. It selects `Nový` at column 3 of the displayed row.

A footer record (112, 448, 8) selects the eight bytes of `Rejstřík`;
the neighboring (111, 458, 5) selects `Obsah`. The same rule applies
to large Contents/Index topics; there is no separate hotspot namespace.

## 4. Index object: type 2711h

| Index-relative position | Size | Type | Meaning |
| --- | ---: | --- | --- |
| +0 | 2 | LE16 | Object type 10001 (`2711h`, bytes `11 27`) |
| +2 | 2 | unsigned LE16 | Number N of context slots |
| +4 | 4*N | LE32 array | Absolute topic-object positions, indexed by context |

The WORD is a slot count, not a byte count. The complete index ends at EOF:

`file_size = A + 4 + 4*N`

For context C within [0,N), read `LE32(A+4+4*C)`. FFFFFFFFh means no
topic assigned. A populated slot addresses the `10 27` type WORD at the
start of its topic object, not a title byte. Titles need not begin with CR.

Text602's N is 360 (`0168h`) and its array occupies `05A0h` bytes.
Calc602's N is 280 (`0118h`) and its array occupies `0460h` bytes.

Shared positions are legitimate: Text602 contexts 64/150, 107/143 and
120/151 share their respective objects. Calc602 contexts 52/53 share
the `Graf │ Zobrazit` object. Conversely, equal captions do not imply
shared positions: Text602 9 and 301 address different `Soubor │ Otevření`
objects at 7244 and 155418.

Contexts 111/112 (Text602 Contents/Index), 133/134 (Calc602 Contents/Index)
and 301–355 (Text602 card-file commands) all use the same index. They do
not require an executable-owned caption lookup.

The original viewer creates a generic “no help for this command” object
when lookup fails; it does not derive a destination from a similar title.
An independent decoder should retain or report an unavailable context,
never erase its label or silently invent a target.

The topic stream may contain an unindexed object. It still has ordinary
paragraph/reference fields. Sequential decoding must not fold it into the
preceding indexed topic or discard its bytes.

## 5. Boundary validation

- Locate CRLF, then require the two complete DWORDs.
- Validate declared file size and index address before reading arrays.
- Decode topic objects by P, Size and R, stopping before the index.
- No paragraph or reference array may borrow bytes from the following
  indexed object. Require every populated slot to address an exact decoded
  object start; a nearby `10 27` inside text is not a fallback boundary.
- Validate object types, nonnegative counts and supported Boolean values.
- Reject truncated records and out-of-text reference ranges.
- Distinguish a malformed populated position from the FFFFFFFFh sentinel.
- Object positions need not follow context order and need not be unique.

## 6. Application-font characters

Decoding the +1 transform gives original one-byte font codes, not Unicode.
The HELP viewer copies these bytes literally into character/attribute cells.
It does not choose a codepage from a row's length, letter/box density or
neighboring characters. `20h..7Eh` follow ASCII; `7Fh` draws the house `⌂`.
The graphics-editor inline font selectors are **not** selectors in this
THelpTopic text. After line layout, even low bytes are literal screen cells.

### 6.1 High-byte screen-font table

The Text602 and Calc602 screen-driver fonts have identical bitmap assignments
for `20h..FFh`, also shared by the older K602/T6HLP default fonts. The
screen font is not Kamenický/CP437, despite familiar Czech letters and frames.
External CZECHVGA/CZECHEGA keyboard fonts and printer fonts are different
resources and must not be used as this table's fallback.

A row supplies the high nibble and a column the low nibble. `SP` is a blank
one-cell glyph. Small placeholder strokes are transcribed as `·`; `FEh`
is a single-pixel dash. The `FFh` font marker is distinct from its logical
use as a non-breaking separator in paragraph text.

| High | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | Ç | ù | è | § | ß | £ | Æ | Ø | Å | æ | ø | å | · | SP | ¤ | ò |
| 9 | ì | Þ | ¡ | Ñ | ¿ | ñ | █ | ▄ | ▀ | · | · | · | · | · | · | · |
| A | ≡ | ± | ≥ | ≤ | ⌠ | ⌡ | ÷ | ≈ | ° | √ | ² | ½ | ¼ | ■ | « | » |
| B | α | β | Γ | π | Σ | σ | µ | τ | Φ | Θ | Ω | δ | ∞ | φ | ε | ∩ |
| C | ┌ | á | └ | č | ď | ě | ŕ | ─ | ü | í | ů | ĺ | ľ | ö | ň | ó |
| D | ô | ä | ř | š | ť | ú | ├ | é | à | ý | ž | ┬ | ˇ | ´ | ˚ | ┼ |
| E | ┐ | Á | ┘ | Č | Ď | Ě | Ŕ | │ | Ü | Í | Ů | Ĺ | Ľ | Ö | Ň | Ó |
| F | Ô | Ä | Ř | Š | Ť | Ú | ┤ | É | À | Ý | Ž | ┴ | ¨ | ^ | - | · |

Standalone accents are spacing characters: DCh=U+02C7, DDh=U+00B4,
DEh=U+02DA, FCh=U+00A8. The actual filled-square glyph is ADh, not 98h.
96h fills all bitmap rows, 97h the lower portion, 98h the upper portion.
Rules, keyboard-title underlines, shadow ends and menu bullets may all use
these same glyphs. A lone C0h still means `┌`, a lone C7h `─`, and a lone
E7h `│`; they do not turn into codepage letters or ASCII `|` in prose.

### 6.2 Low-byte cells and genuine font variants

Common low glyphs in the inspected Text602/Calc602 screen drivers:

| Bytes | Glyph transcription |
| --- | --- |
| `04 05 06` | `┏ ┓ ━` |
| `07 08 09 0A` | `╭ ╮ ╰ ╯` |
| `0B 0C 0D` | `│ ─ ↵` |
| `13` | `┳` |
| `17 18 19 1A 1B` | `↨ ↑ ↓ → ←` |
| `1C 1D 1E 1F` | `└ ↔ √ ±` |

CR (`0Dh`) is consumed by paragraph line layout before font drawing. LF
(`0Ah`) is wrapping whitespace but, when retained in a fixed row, is the
`╯` glyph, not an additional line break. 1Ah draws a right arrow if present
in the declared Text range; it is not an implicit DOS-EOF terminator.

The fonts differ in low slots 02h, 11h, 12h, 15h and 16h. Text602's 02h
and 16h have a check-mark shape; Calc602 uses a diagonal stroke and a
right-side vertical stroke. Text602 11h/12h/15h duplicate 06h/04h/05h;
Calc602's 11h/12h are quote-like corner pairs and 15h a left vertical line.
Those are font-resource variants, not HELP style opcodes. Boxed keys,
compound symbols and small letter forms in 00h/01h/03h/0Eh/0Fh/10h/14h
have no complete semantic Unicode transcription here. Keep their byte/cell
identity or use a visible unknown glyph, never silently erase them.

### 6.3 Screen-driver bitmap layout

The HLP contains no font bitmap or font selector. Pixel-faithful decoding
requires the matching application's screen-driver resource, not a printer
font guessed from the HELP extension. Inspected default 8×15 resources:

| Driver stamp | Stamp length | Font byte position | Font bytes |
| --- | ---: | ---: | ---: |
| `T602-DRIVERS-v.3.10` followed by NUL | 19 | `2D94h` (11668) | 3840 |
| `C602-DRIVERS-v.1.51` | 18 | `5F41h` (24385) | 3840 |

These positions locate a sample's resource, not an address in HLP. They
follow the preceding driver/resource blobs; do not assume all releases have
the same position. Each font consists of 256 glyphs × 15 bitmap bytes,
with glyphs in decoded-byte order. For byte B, scanline Y and column X:

```text
row_bits = font_start[15 * B + Y]       # 0 <= Y < 15
pixel(X) = (row_bits >> (7-X)) & 1      # 0 <= X < 8
```

Rows run top-to-bottom; the high bit is leftmost. A thirteen-row mode
derives its font by omitting zero-based scanlines 2 and 12 of each 15-row
glyph. This is scanline removal, not a character-code translation.
The original screen writer selects a glyph using the literal character byte;
palette attributes can alter color/stroke appearance, not its text identity.
Font changes are runtime application configuration, not a per-paragraph flag.
