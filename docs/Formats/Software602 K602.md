# Software602 K602 Help Format

> Created: 2026-06-20 · Last updated: 2026-10-11

Used by: Kartotéka 602 / K602. File extension: `.HLP`.

## Evidence and scope

The inspected `K602.HLP` has 53,115 bytes and CRC32 `17ADD07D`. The
[K602 1.0 distribution](https://www.osdos.net/download.htm#k602-v1-0)
contains a byte-identical file and the original `K602.EXE` in a
[self-extracting archive](https://www.osdos.net/download/k602/k602.exe).
The original reader and built-in graphics fonts confirm the directory,
byte-sized context addressing, absolute offsets, topic sizes, stored rows,
character identities and ordinary/bold/italic drawing below.
This specifies that `K6HLP` layout, not every Software602 help family.
It is neither encrypted nor compressed.

## Detection

The file starts with a Pascal-style 10-byte ASCII signature:

```text
0A "K6HLP86278"
```

At offset `$0B` follows a little-endian 32-bit file size. In the observed
sample this is `$0000CF7B`, exactly `53115` bytes.

## File Layout

```text
Offset  Size  Description
------  ----  -----------
0000    11    signature: 0A + "K6HLP86278"
000B    4     declared file size, uint32 LE
000F    1536  topic directory: 256 entries of 6 bytes
060F    ...   topic blocks addressed by directory entries
```

All multibyte integers are unsigned little-endian. Offsets are relative to
the **beginning of the file**, not to a segment or the text area. There is no
stored directory count: the original reader loads `060Fh` bytes at once.

The directory begins at `$0F`. Each of its 256 entries is:

| Relative offset | Size | Type | Meaning |
| --- | ---: | --- | --- |
| `+00` | 4 | LE32 | Absolute topic-block offset; zero means unavailable |
| `+04` | 2 | LE16 | Block length in bytes, including each row's length byte |

For an application context `C` in `0..255`:

```text
entry_position = 0Fh + 6 * C
offset         = LE32(file[entry_position : entry_position + 4])
size           = LE16(file[entry_position + 4 : entry_position + 6])
```

The slot is the context itself; it is **not** a one-based ordinal of populated
topics. In this sample contexts `0..16` are unused, so their 102 zero bytes
occupy `000Fh..0074h`. They are not reserved header space. The first populated
slot at `0075h` is context `17`; the final slot is context `255` at `0609h`.

Native lookup tests the offset DWORD only. When it is zero, the size WORD is
irrelevant; the original's unused slots happen to have zero sizes too. A
nonzero offset with size zero describes an empty block. This differs from an
unavailable slot. Slots can be sparse and offsets need not be sorted. Read
each block through its own descriptor; never infer its end from the next slot.
Shared descriptors address the same stored block.

Observed directory properties:

- 256 total slots, 115 populated slots and 141 unavailable contexts
- first stored block at `060Fh`, owned by context `125`
- populated contexts occur between `17` and `140`
- physical blocks cover `060Fh..CF7Ah` without gaps or overlaps

The contiguous packing is a sample property, not a mandatory sorting or
uniqueness rule. A decoder must not use invalid-looking text bytes as a
directory terminator: the boundary is always `060Fh`.

## Topic Text

Each topic block is a sequence of one-byte length-prefixed lines:

```text
length uint8
text   length bytes
```

`length = 0` is a blank row. The length is the **stored byte count**, including
format controls; it is not the visible column count. The next row starts
exactly `1 + length` bytes after the current row start. A block ends at
`offset + size`, without a NUL or DOS-EOF terminator. A NUL inside a row does
not end the topic. No hyperlink target table or in-band topic-target operand
has been identified in this layout.

The original allocates `size + 1` bytes and appends byte `05h` in memory. That
guard byte is not stored in the HLP and must not be consumed as another row.
Likewise the original uses an 8-bit increment for the row length; an independent
decoder should calculate `1 + length` in a wider integer to avoid overflow at
`FFh`.

## Bounded decoding

1. Require the signature, file-size DWORD and all `060Fh` header bytes.
2. Check the stored file size against the actual byte length.
3. Read exactly 256 descriptors beginning at `000Fh`, retaining slot numbers.
4. Skip zero-offset slots, without interpreting their unused size WORDs.
5. For each populated slot require `offset >= 060Fh` and
   `offset + size <= file_size`, using overflow-safe arithmetic.
6. Starting at `offset`, read a length byte only while before `offset + size`.
   Require its complete payload to fit that same block. A row cannot borrow
   bytes from another topic or from trailing unindexed bytes.
7. Decode all rows until exactly the descriptor's size has been consumed.

Zero-byte blocks and zero-length rows are distinct valid cases. Bytes after
all referenced blocks need not be interpreted as another topic. There is no
stored checksum; a changed descriptor that still points to valid bytes cannot
always be distinguished from an intentional edit.

## Text Encoding

Stored glyph bytes are used directly, without XOR or Text602/Calc602's `-1`
transform. `20h..7Eh` follow ASCII; `7Fh` is the house glyph `⌂`. The default
graphics font has its own character arrangement. It is **not** Kamenický or
CP437, even though many Czech letter and box forms are familiar.

The following Unicode transcription follows the built-in 8×15/8×11 fonts.
A column number supplies the low nibble; a row label supplies the high nibble.
`SP` means a completely blank glyph occupying one cell. Standalone accents
are spacing characters: `DCh=ˇ` (U+02C7), `DDh=´` (U+00B4), `DEh=˚` (U+02DA),
`FCh=¨` (U+00A8), `FDh=^`. Small bitmap dot/stroke shapes are transcribed as
`8Ch=·`, `99h..9Fh=·`, `FEh=-`, `FFh=·` rather than as codepage letters
or blocks. The small mid-line placeholders have identical 8×15 bitmap rows;
only 8Dh is a blank slot in the high half.

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

Low-byte glyphs, distinct from the selector bytes in the next section:

| Bytes | Default-font transcription |
| --- | --- |
| `05 06` | `┓ ━` |
| `07 08 09 0A 0B` | `╭ ╮ ╰ ╯ │` |
| `0C 0D` | `─ ↵` |
| `11 12 15` | raised/lowered quote marks `“ „`, vertical stroke `│` |
| `17 18 19 1A 1B` | `↨ ↑ ↓ → ←` |
| `1C 1D 1E 1F` | `└ ↔ √ ±` |

`00h` is a compound quote-like bitmap, and `01h`, `03h`, `0Eh`, `10h` are
boxed E/C/P/U key glyphs. A one-character Unicode transcription has not been
established for these compound forms; their application/key semantics are
also not inferred from their letters. They are absent from the inspected
HLP's row payloads. They are not NUL termination or implicit string operands.

The original printer passes every non-selector byte to its glyph writer. In
particular `0Ah` draws `╯`, not a newline. `0Dh` inside `<...>` Enter labels
draws `↵`, not a cursor return. `8Dh` is a blank cell; an `8D 0A` pair draws
`SP ╯` on the **same stored row**. It is not an established newline escape.

### Font bitmap layout

The glyph font is not embedded in the HLP. The inspected `K602.EXE` contains
256 consecutive 8×15 glyphs at file offset `B3F9h` (3,840 bytes) and 256
8×11 glyphs at `C2F9h` (2,816 bytes). For byte `B`, height `H` and row `Y`:

```text
row_bits = font[H * B + Y]     # 0 <= Y < H
pixel(X) = (row_bits >> (7 - X)) & 1
```

Rows are top-to-bottom and bits are left-to-right. These offsets apply to
the verified original executable, not to arbitrary revisions. Native startup
can load an optional `1C00h`-byte font file: first `0F00h` bytes for the 8×15
font, then `0B00h` for 8×11, followed by two 256-byte tables whose complete
role is not established here. Custom fonts can therefore change a glyph's
appearance; the Unicode table above specifies the built-in font.

The block glyphs make the absence of hidden attributes especially clear:
`96h` is `FFh` in every bitmap row (`█`); `97h` has a zero upper half and
filled lower half (`▄`); `98h` has a filled upper half and zero lower half
(`▀`). Retain them at row ends and alongside selectors too, including source
window shadows and title/underline decoration.

## Inline Attributes

The original inline printer starts each stored row in category zero. These
selector bytes change its category without occupying a text cell:

| Byte | Category | Native effect | Present in inspected HLP |
| --- | ---: | --- | --- |
| `02h` | `02h` | bold | yes |
| `04h` | `01h` | italic | yes |
| `0Fh` | `04h` | double-cell-width font | no |
| `13h` | `20h` | underlined ordinary font | no |
| `14h` | `06h` | raised five-row glyph (superscript) | no |
| `16h` | `07h` | lowered five-row glyph (subscript) | no |

For a selector's category `S`, use `category = 0` if the current category
already equals `S`, otherwise `category = S`. Different selectors switch
categories; they do not cancel each other as a single Boolean toggle would.
The native graphics kernels confirm the effects: ordinary rows use stored
font bits, bold uses `bits OR (bits >> 1)`, italic shifts the upper glyph rows
to the right, and underline adds a filled penultimate scanline. Category zero
is ordinary text; categories replace the previous style rather than combining
independent bold/italic bits. The caller's color/inversion flags and graphics
palette determine colors; category numbers are not DOS foreground/background
attribute bytes.

### Native viewport

The original help window calculates a width hint from the stored rows and
clamps its text width to 50–70 cells, with a 14-row body viewport. This is an
executable display rule, not a dimension field in the HLP. Long rows remain
single stored rows; native display may clip them to the chosen viewport. A
decoder can retain all row bytes without inventing additional topic records
or treating cursor-like glyph bytes as newlines.

## Byte examples

First populated descriptor, **context 17**, at `0075h`:

```text
A1 8C 00 00  6C 02
^^^^^^^^^^^  ^^^^^
offset 8CA1h size 026Ch = 620 bytes
```

Context `125` is stored at `0Fh + 6*125 = 02FDh`:

```text
0F 06 00 00  82 07
offset 060Fh size 0782h = 1922 bytes
```

Its first row at `060Fh` is blank (`00h`). The title row begins at `0610h`:

```text
13 20 20 02 4E 6F 76 C1 20 64 61 74 61 62 C1 7A 65 20 02 97
^^
19 payload bytes; the next length byte is at 0610h + 1 + 19 = 0624h
```

The readable title is “Nová databáze” with its authored spaces and category
selectors. Terminal `97h` is a visible lower block `▄`, not a hidden attribute.
An independent minimal row example is `03 41 42 43 00 01 58`: three rows,
respectively `ABC`, blank and `X`, occupying seven block bytes in total.
