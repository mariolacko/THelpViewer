# Software602 T6HLP Help Format

> Created: 2026-06-20 · Last updated: 2026-10-11

Used by: Text602 3.00. File extension: `.HLP`.
The inspected 102,013-byte file has CRC32 `CCC3E5FB`.
This specifies the uncompressed, unencrypted `T6HLP86278` layout verified
against the matching native reader and graphics printer. It is not the newer
`Text602 - help` / `Calc602 - help` THelpTopic paragraph format.

## 1. Header and directory

All multibyte integers are unsigned little-endian. File offsets are absolute.

| Offset | Size | Type | Meaning |
|--------|------|------|---------|
| `0000h` | 1 | BYTE | Length 10 of the following Pascal signature |
| `0001h` | 10 | ASCII | `T6HLP86278` |
| `000Bh` | 4 | DWORD LE | Declared total file size |
| `000Fh` | 1,536 | 256 descriptors | Fixed six-byte topic directory |
| `060Fh` | Variable | Topic blocks | Located by directory offsets |

For the inspected file, the header is:

```text
0A 54 36 48 4C 50 38 36 32 37 38 7D 8E 01 00
   T  6  H  L  P  8  6  2  7  8
file_size = 00018E7Dh = 102013
```

The original loader reads `060Fh` header bytes, compares the Pascal stamp and
checks the stored file size. The `86278` suffix is part of that stamp; no
version/date semantics are established for its digits. There is no stored
directory count or charset field.

For byte-sized application context `C` in `0..255`:

```text
entry_position = 0Fh + 6 * C
```

| Descriptor-relative offset | Size | Type | Meaning |
|----------------------------|------|------|---------|
| `+0` | 4 | DWORD LE | Absolute payload offset `P`; zero means unavailable |
| `+4` | 2 | WORD LE | Stored payload size `S`, including row-length bytes |

The context is the slot number itself, **not slot + 1** or a populated-topic
ordinal. Sparse slots retain their identities. The final slot, context 255,
starts at `0609h`.

The native reader tests only `P` for availability. An unused slot's size WORD
is irrelevant. A nonzero offset and zero size describe an empty block.
Offsets need not follow slot order; contexts can share payloads. Read exactly
`[P, P+S)`, not up to the next descriptor. Require `P >= 060Fh` and
`P+S <= file_size`, calculating in a wider integer.

Observed properties of the inspected directory:

- 191 populated contexts and 65 unavailable slots.
- Context 0 is present, at offset `D32Bh`, size `0159h` (345 bytes).
- The first physical block, at `060Fh`, belongs to context 34, “Otevření”.
- All title names are text in the payload, not separately stored directory fields.

## 2. Stored rows and block boundaries

Each topic is a sequence of Pascal byte strings:

```text
length uint8
bytes  length bytes
```

The next row starts exactly `1 + length` bytes after the current row start.
`00h` in the length position is a **blank row**, not a separator between
larger records. `00h` inside a row is a glyph byte and must not split its
payload. There is no NUL or DOS-EOF termination between rows or at block end.

A minimal example:

```text
03 41 42 43 00 01 58
```

This is three rows: `ABC`, blank, `X`. It consumes seven bytes.
Length includes selectors and literal font cells; it is not visible width.

The native reader allocates `S+1` bytes and appends a `05h` guard in memory.
That guard is not part of the HLP payload. Its row-copy loop increments the
length in an eight-bit register; an independent decoder should use a wider
integer for `length+1` so `FFh` cannot wrap to zero and stall parsing.

The inspected blocks contain 3,360 stored rows: 631 with zero byte length
and four additional selector-only rows with no visible cells. Blank rows
between paragraphs and diagrams are authored spacing.

## 3. Graphics-font character encoding

Glyph bytes are used directly: no XOR and no `-1` transform. `20h..7Eh`
are ASCII, and `7Fh` is the house glyph `⌂`. The built-in graphics fonts have
their own arrangement, not a Kamenický/CP437 fallback.

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


The compound low glyphs `00h`, `01h`, `03h`, `0Eh`, `10h` have no
established single-character Unicode transcription here. They are not string
terminators or invisible attributes. Their bitmap/key semantics are not
inferred from those of another executable revision.

Every non-selector byte is sent to the glyph writer. In particular `0Dh`
draws `↵` in Enter-key labels, `17h/18h/19h` draw `↨/↑/↓`, and `0Ah`
is a corner glyph, not a newline. The `96h/97h/98h` blocks remain visible
even at the end of a styled row. `8Dh` is a blank cell and `FEh` is a dash.

### Font bitmap layout

The fonts are in the application, not the HLP. The inspected native executable
has 256 8×15 glyphs at file offset `10C5Ah` (3,840 bytes) and 256 8×11 glyphs
at `11B5Ah` (2,816 bytes). For character byte `B`, height `H`, row `Y`
and column `X`:

```text
row_bits = font[H * B + Y]       # 0 <= Y < H
pixel(X) = (row_bits >> (7-X)) & 1
```

Bitmap rows run top-to-bottom and high bits are leftmost. These executable
offsets are sample-specific, not HLP addressing constants. Other installed
fonts or revisions can alter appearance.

## 4. Inline style selectors

Each stored row starts in ordinary category zero:

| Byte | Selected category | Native effect |
|------|-------------------|---------------|
| `02h` | `02h` | Bold |
| `04h` | `01h` | Italic |
| `0Fh` | `04h` | Double-cell-width font |
| `13h` | `20h` | Underlined ordinary font |
| `14h` | `06h` | Raised five-row glyph |
| `16h` | `07h` | Lowered five-row glyph |

A selector occupies no glyph cell. If its selected category equals the current
category, it toggles back to zero; otherwise it replaces the category. These
are not independently cumulative bold/italic flags. For example:

```text
02 41 04 42 04 43  →  bold A, italic B, ordinary C
```

The inspected HLP uses only `02h` and `04h`. The remaining selectors are
confirmed by the original printer's switch, not claimed present in that file.
The native font kernels thicken strokes for bold, shift upper glyph rows for
italic and add a filled penultimate scanline for underline. Runtime colors and
inversion are separate from these font category numbers.

Neither selector is an inline hyperlink delimiter in this format. No stored
topic-target operands or hyperlink table have been established.

## 5. Title, underline and viewport

Title/underline graphics are authored rows, for example:

```text
00
0E 20 20 02 4F 74 65 76 D2 65 6E C9 20 02 97
0C 20 20 20 98 98 98 98 98 98 98 98 98
00
```

The title row is “Otevření” with leading spaces, bold selectors and its
terminal lower-half block. The next row uses upper-half blocks. They are
visible cells, not a separate hidden title/attribute structure.

The native help viewer clamps a measured text-width hint to 50–70 cells and
starts with a 14-row body viewport. Those are runtime display rules, not
fields in the HLP. Long stored rows remain single rows; a decoder must not
invent paragraph boundaries from literal font bytes.

## 6. Decoder procedure

1. Validate the Pascal stamp, file-size DWORD and complete `060Fh` header.
2. Read all 256 descriptors, retaining their byte contexts.
3. Ignore zero-offset entries regardless of their unused size WORD.
4. Validate every populated payload range, including zero-sized blocks,
   without assuming sorted/unique offsets.
5. Read length-prefixed rows until exactly that payload size is consumed.
   Reject a row crossing its own block end, even if later file bytes exist.
6. Preserve zero-length rows and every non-selector glyph cell.
7. Reset category on each row and apply the selector state machine.
8. Transcribe glyph bytes through the known font, keeping authored block art,
   title cells and whitespace separate from presentation/navigation choices.

There is no stored checksum. Structural validation cannot detect every byte
change that still produces valid descriptors/rows. Unspecified details include
other stamps/revisions, custom fonts, the compound low-glyph transcription
and exact clipping behavior for unusual row widths. No field defines
Previous/Next topic navigation.
