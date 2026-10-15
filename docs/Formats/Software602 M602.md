# Software602 M602 HelpSystem Format

> Created: 2026-04-03 · Last updated: 2026-10-12

Used by: Manažer 602, classic HelpSystem variant. File extension: `.HLP`.
All offsets below are absolute byte offsets unless explicitly stated otherwise.
The described directory and record grammar are verified for the 2.00 file.
Other releases may have different layouts; a matching stamp alone does not
establish compatibility.

## 1. File layout and signature

| Region | Offset | Size | Encoding |
|--------|--------|------|----------|
| Signature | `0000h` | 27 bytes | Unencrypted |
| Topic records | `001Bh` onward | Ranges stored in the directory | Every byte XOR `FAh` |
| Topic directory | `D` | `8 * N` bytes | Unencrypted |
| Footer | `file_size - 6` | 6 bytes | Unencrypted |

The signature is exactly:

```text
1A 28 63 29 20 53 6F 66 74 77 61 72 65 36 30 32
20 48 65 6C 70 53 79 73 74 65 6D
   (c) Software602 HelpSystem
```

No topic count, charset or record count occurs in this signature. `1Ah`
is part of the stamp, not the end of the binary file.

## 2. Footer and directory addressing

The footer occupies the final six bytes:

| Footer-relative offset | Size | Type | Meaning |
|------------------------|------|------|---------|
| `+0` | 2 | WORD, little-endian | `N`: number of topic-directory entries |
| `+2` | 4 | DWORD, little-endian | Declared complete file size, including footer |

Compute the directory start:

```text
D = file_size - 6 - 8 * N
```

Validate the declared size against the actual input size and require
`D >= 27`. Do not decrypt the footer or directory. There is no separate
six-byte directory header and no eight-byte sentinel entry.

For the 139,965-byte 2.00 file:

```text
footer = C9 00 BD 22 02 00
N      = 00C9h = 201
size   = 000222BDh = 139965
D      = 222BDh - 6 - 8 * 00C9h = 21C6Fh = 138351
```

The directory has 201 entries (1,608 bytes) and the footer has six bytes.
Neither `N` nor the first directory byte is a text-record count or pivot count.

## 3. Eight-byte topic-directory entry

Entry `i` starts at `D + 8 * i`, for `0 <= i < N`.

| Entry-relative offset | Size | Type | Meaning |
|-----------------------|------|------|---------|
| `+0` | 2 | WORD, little-endian | Native application help context |
| `+2` | 4 | DWORD, little-endian | Absolute topic-record offset `P` |
| `+6` | 2 | WORD, little-endian | Encrypted topic size `S`, including record-length bytes |

The payload is exactly `[P, P + S)`. Require `P >= 27` and
`P + S <= D`, using wider arithmetic for validation. Parse every record
inside that range; a length byte cannot borrow bytes from the next range or
from the directory.

The stored size is **not** a delta to another directory entry. Entry order
need not match physical payload order. The original lookup scans the
directory forward; the first matching context wins. Multiple contexts can
refer to the same payload. Gaps outside indexed ranges are not topic text.
A zero count produces no lookup entries; a zero size has no payload bytes.
The inspected native reader caps the read size at 6,000 bytes after issuing
its damaged-file warning. That is a runtime buffer limit, not a smaller
on-disk integer field; it must not change the directory/footer addressing.

Examples from the 2.00 directory:

| Entry bytes | Native context | Offset | Size |
|-------------|----------------|--------|------|
| `0F 27 1B 00 00 00 35 00` | `270Fh` = 9999 | `001Bh` | `0035h` = 53 |
| `00 00 50 00 00 00 A2 01` | `0000h` | `0050h` | `01A2h` = 418 |
| `0A 00 F2 01 00 00 B9 02` | `000Ah` | `01F2h` | `02B9h` = 697 |
| `0D EB D1 1B 02 00 9E 00` | `EB0Dh` | `00021BD1h` | `009Eh` = 158 |

The first entry is the real error topic “Chyba”, not a directory header.
The last topic ends at `21BD1h + 009Eh = 21C6Fh`, before the directory.
Its trailing size WORD `9E 00` is immediately followed by the footer
`C9 00 BD 22 02 00`; interpreting all eight bytes as one sentinel obscures
the last topic's actual size.

## 4. Record encryption and boundaries

A topic contains concatenated Pascal-style byte strings. Both the length
byte and the payload bytes are XOR-encrypted with `FAh`:

```text
L = input[position] XOR FAh
payload[j] = input[position + 1 + j] XOR FAh, 0 <= j < L
next_position = position + 1 + L
```

`L` is an unsigned byte, 0–255. The one-byte prefix counts payload bytes,
not visible character cells. Hyperlink delimiters and operands count toward
`L`. There is no escaping for the XOR key: an encrypted zero byte may decode
to a perfectly valid `FAh` glyph, and its frequency does not delimit the index.

Each observed 2.00 record ends with one `0Dh` carriage-return terminator,
included in `L`. The original string-copy routine copies `L + 1` bytes
(prefix and payload), advances the source by that amount and decrements the
copied length **once**. It does not strip a run of CRs. A second CR immediately
before the suffix is a literal screen cell. A target operand equal to `0Dh`
is still binary data: identify the actual suffix and parse complete operands
before it, rather than stripping arbitrary bytes from a target.

Observed examples:

```text
plain title:     09 01 43 68 79 62 61 20 DC 0D
encrypted:      F3 FB B9 92 83 98 9B DA 26 F7
visible title:  Chyba  (the final DC is a block decoration)

plain blank:    02 01 0D
encrypted:      F8 FB F7
```

The 2.00 file has 3,363 records inside its indexed ranges, with no zero-length
records. No standalone text-record-count field is established.
The native decrement is unconditional. A zero `L` underflows the copied
byte length to `FFh`, making subsequent reads depend on unrelated memory;
it is not an empty row. A safe decoder must not follow those reads. A non-CR
last byte would also be removed, but no such terminator variant is established
by the sample. Require a complete suffix for this grammar and never use
malformed strings to read outside the topic. A genuine empty displayed string
has `L = 1`, with CR as its only payload byte; a hard blank row has `01 0D`.

## 5. Row markers, titles and separators

A leading `01h` distinguishes a hard row from ordinary wrapping text.
The original reader replaces this leading byte with a space in the display
string. Ordinary records can be concatenated with a space and wrapped to the
current viewport width; a following hard row terminates that concatenation.
The stored record length is not a fixed viewport width. `01h` is special only
at the start of the emitted row; the same byte elsewhere is a literal cell.

Typical first rows are:

```text
01 <title bytes> DC 0D
01 DF DF DF ... DF 0D
```

`DCh` and `DFh` are lower-half and upper-half block glyphs. These authored
title/underline patterns do not define topic boundaries: only the directory's
offset and size do. The same glyphs in body text, or inside two-byte link
operands, must not start or end a topic.

### Raw-byte row assembly and wrapping

Let `R[i]` be the complete decoded payload of record `i` after removing its
single suffix. Let `W` be the view's current horizontal size (the verified
split routine uses its low unsigned byte). No `W` field occurs in the file.
The following sequence precedes hotspot removal and character decoding:

1. Take the next record as `current`.
2. If its first byte is `01h`, emit it immediately without wrapping.
3. Otherwise, while another record is available and that next record does
   not begin with `01h`, append **one ASCII space**, then that whole record.
4. After each such append, while the encoded length exceeds `W`, find a cut:

   - inspect one-based position `W`; search backward for `20h`, down to 1;
   - if no space is found there, search forward from `W` to the first `20h`;
   - if no forward space exists, use the complete current length;
   - emit the prefix **including** the space at the cut, then remove exactly
     that prefix from `current` and repeat if needed.
5. When the next record is hard or there is no next record, emit the remainder
   and resume at step 1. An unjoined final soft record is not separately wrapped.
6. For each emitted row, remove complete hotspots as described below and
   replace a leading `01h` with `20h`. Do not trim other spaces or title art.

This is byte-length wrapping, not visible-cell wrapping: link delimiters and
the two context bytes count before removal. Label underscores remain `5Fh`
during the split search and become spaces only during hotspot decoding.
Only ASCII `20h` is a split point; internal CR, TAB and NBSP are not split
instructions. Spaces already present at record ends remain, in addition to
the inserted separator. There is no whitespace collapsing or forced split
inside an unbroken word. Hard rows and long words can exceed the viewport.

The original concatenation uses 255-byte Pascal short strings: a sum beyond
255 retains only the prefix that fits. It must not be mistaken for a smaller
on-disk row/topic field or an end-of-topic marker. Wider safe buffers can
retain the complete source but must explicitly distinguish that behavior
from native short-string truncation.

For `W = 10`, source soft rows `one two three 0D` and `four five six 0D`
produce `one two `, `three `, `four five `, `six`. Both trailing cut spaces
and the inserted record separator are actual display bytes. A following
hard row `01 0D` is a separate single-space row.

## 6. Inline hyperlinks

Within a decoded display record:

```text
02 <label bytes> 02 context_hi context_lo
```

| Component | Size | Meaning |
|-----------|------|---------|
| First `02h` | 1 | Start of hotspot |
| Label | Variable | Visible bytes, ending at the next `02h` |
| Second `02h` | 1 | End of hotspot label |
| `context_hi` | 1 | High byte of the native context |
| `context_lo` | 1 | Low byte of the native context |

The native target is `(context_hi << 8) | context_lo`: **big-endian** in the
inline record, but little-endian in the directory WORD. Alternatively, a
decoder may read inline operands as an LE raw code and compare it with each
directory context after swapping its bytes. Those two numeric conventions
must not be mixed.

In a label, `5Fh` (underscore) becomes `20h` (space). Keep all label
cells, including final padding. Outside a label, underscores remain literal.
The two delimiters and the two target bytes do not occupy display cells.
After consuming a target, resume at the following byte. Require a closing
delimiter and both operand bytes before the record suffix. Neither the suffix
nor bytes from a following Pascal string complete a truncated operand.

Hotspot rows and columns are one-based. After removing the opening delimiter,
the native start column is the current string position; after removing the
closing delimiter/operand, the end column is the preceding visible label
cell. The row is assigned when the emitted string is stored. Adjacent links
with equal contexts are still separate hotspots. An empty label has end less
than start and contributes no clickable cell.

Because wrapping precedes decoding, unusual padding/space-containing labels
can be cut inside a hotspot. The original label scan then runs beyond the
emitted string length looking for its closing delimiter; that adjacent-memory
behavior is not a valid bounded file grammar. An independent safe decoder
can lex complete hotspots within their original records first, retain a
raw-byte-to-cell map, apply the same cut positions and carry the target to
each visible label fragment. Do not invent a target or erase text at a cut.

For native context `7919h`:

```text
inline operands:    79 19
directory WORD:     19 79
native numeric ID:  7919h
LE raw-inline ID:   1979h
```

A full example targeting native context `000Ah`:

```text
02 50 72 A0 63 65 02 00 0A
   P  r  á  c  e
```

This is the visible link “Práce”; look up WORD `000Ah` in the directory.
The operands are not physical topic ordinals and are not payload offsets.

### Lookup and unavailable contexts

1. Scan entries in stored order for the requested native context.
2. Read exactly the matching entry's payload at its stored absolute offset.
3. If absent, scan for native context `270Fh` (decimal 9999), the error page.
4. If neither exists, lookup has no topic.

This fallback is an application-defined context, not a title-matching
algorithm or an assumption that the first topic is always the error screen.
Duplicate captions do not affect destination lookup.

## 7. Character encoding

The verified Czech file uses Kamenický (KEYBCS2); the stamp has no encoding
selector. `20h`–`7Eh` are ASCII. Decode character cells only after separating
record/row markers, hyperlink delimiters and their operands.

High-byte map, in order from column `0` to `F`:

| High nibble | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
|-------------|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | Č | ü | é | ď | ä | Ď | Ť | č | ě | Ě | Ĺ | Í | ľ | ĺ | Ä | Á |
| 9 | É | ž | Ž | ô | ö | Ó | ů | Ú | ý | Ö | Ü | Š | Ľ | Ý | Ř | ť |
| A | á | í | ó | ú | ň | Ň | Ů | Ô | š | ř | ŕ | Ŕ | ¼ | § | « | » |
| B | ░ | ▒ | ▓ | │ | ┤ | ╡ | ╢ | ╖ | ╕ | ╣ | ║ | ╗ | ╝ | ╜ | ╛ | ┐ |
| C | └ | ┴ | ┬ | ├ | ─ | ┼ | ╞ | ╟ | ╚ | ╔ | ╩ | ╦ | ╠ | ═ | ╬ | ╧ |
| D | ╨ | ╤ | ╥ | ╙ | ╘ | ╒ | ╓ | ╫ | ╪ | ┘ | ┌ | █ | ▄ | ▌ | ▐ | ▀ |
| E | α | ß | Γ | π | Σ | σ | µ | τ | Φ | Θ | Ω | δ | ∞ | φ | ε | ∩ |
| F | ≡ | ± | ≥ | ≤ | ⌠ | ⌡ | ÷ | ≈ | ° | ∙ | · | √ | ⁿ | ² | ■ | NBSP |

Low OEM glyphs occur in visible body text: `12h` = ↕, `1Eh` = ▲,
`1Fh` = ▼. They are not extra link/format controls. After record and hotspot
processing, bytes are literal screen cells: an internal CR does not start a
new row, TAB does not expand and NUL does not terminate a Pascal string.
The ordinary OEM transcription has `00h` = blank, `09h` = ○, `0Ah` = ◙,
`0Dh` = ♪ and `7Fh` = ⌂. An alternate application-loaded font can change
their pixel appearance; there is no font selection field in this stamp.

## 8. Decoder procedure and validation

1. Match the entire 27-byte stamp.
2. Read the unencrypted footer, validate its file size and locate the directory.
3. Read all `N` eight-byte entries, retaining native context, offset and size.
4. Validate each indexed byte range independently. Do not infer size from the
   next entry or require sorted offsets.
5. XOR-decode length-prefixed records within each indexed range. Reject a
   record that would cross its range end.
6. Identify the record terminator separately from binary operands; extract
   complete hotspots, substitute underscores only inside labels and preserve
   their cell widths.
7. Assemble hard/soft rows using the raw-byte procedure above and project
   complete source hotspots onto emitted cells. Decode visible cells using
   the known charset, keeping layout separate from storage addressing.
8. Resolve native contexts through the directory, including its first entry
   and the defined 9999 fallback. Do not guess destinations from visible text.

Unknowns include charset selection in other releases, other HelpSystem
variants, non-CR terminator variants and alternate screen-font appearance.
The verified footer/directory
layout has no unexplained header/pivot bytes.
