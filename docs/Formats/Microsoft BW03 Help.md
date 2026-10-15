# Microsoft BW03 Help Format

## Overview

`BW03` is an older **DOS / OS/2 text-mode** Microsoft help format used by
pre-QuickHelp toolchains:

- `CV.HLP` for CodeView DOS / DOS mode
- `CVP.HLP` for CodeView protected-mode / OS/2 mode

This is **not** the later QuickHelp `LN` format.  Files with the same `.HLP`
extension must therefore be detected by signature, not by suffix.

Status of this document:

- header, menu/style/descriptor tables and payload boundaries are confirmed
  from the files below and original CodeView reader instructions
- original CodeView selects the first or second triplet attribute using a
  display-mode flag; color/monochrome meanings also match Microsoft documentation

Sample files used:

- `Microsoft MASM and CodeView 5.0/CV.HLP`
- `Microsoft MASM and CodeView 5.1/CV.HLP`
- `Microsoft MASM and CodeView 5.1/CVP.HLP`

External product context:

- [IBM CodeView/C documentation](https://www.bitsavers.org/pdf/ibm/pc/languages/15F0377_C2_1.10_Debug_1988.pdf)
  distinguishes DOS `CV.HLP` and OS/2 `CVP.HLP`.
- [Original Microsoft C 5.10 distribution at PCjs](https://www.pcjs.org/software/pcx86/lang/microsoft/c/5.10-os2/)
  contains the original `CV.EXE`; its help routines confirm the layouts and
  controls below. The indexed-screen renderer and plain-text short-help reader
  are distinct routines, not two encodings inferred from filename extensions.

---

## File Header

All WORD/DWORD fields are little-endian; payload offsets are absolute file offsets.

Offset `0x00`:

| Offset | Size | Type | Meaning |
|--------|------|------|---------|
| `00` | 4 | ASCII | Signature, always `BW03` |
| `04` | 2 | `WORD` | Screen count actually used |
| `06` | 2 | `WORD` | Menu category count |

Immediately after the 8-byte header:

1. menu table, `MenuCount * 22` bytes
2. control / style dictionary, always `48` bytes in the sampled files
3. active screen descriptors, `ScreenCount * 12` bytes
4. optional reserved descriptor slots, then indexed screen payloads
5. optional plain-text command summary after the final indexed screen

The sampled files reserve space for **40 screen descriptors**, even when the
actual `ScreenCount` is smaller. This allocation is not another count field:
the native loader reads only the active descriptors and seeks to their absolute
payload positions. A compact file need not contain the unused 40-slot padding.

Exact starts:

```text
MenuTable       = 8
StyleTable      = 8 + 22 * MenuCount
DescriptorTable = StyleTable + 48
ActiveTableEnd  = DescriptorTable + 12 * ScreenCount
```

No byte-scanning heuristic is needed to locate a table. Payload offsets must
not point into the header or active tables; each positive-length range must
fit inside the file. There is no stored file size or checksum.

---

## Menu Table

Each menu entry is 22 bytes:

| Offset | Size | Type | Meaning |
|--------|------|------|---------|
| `+00` | 1 | `BYTE` | Zero-based screen index of the first screen in this category |
| `+01` | 1 | `BYTE` | Hotkey character |
| `+02` | 20 | bytes | CP437 / ASCII title, NUL-padded |

Example from `CV.HLP`:

| First screen | Hotkey | Title |
|--------------|--------|-------|
| `0` | `I` | `Introducing Help` |
| `1` | `K` | `Keyboard/Mouse` |
| `2` | `R` | `Run Commands` |
| `3` | `D` | `Display Commands` |
| `6` | `E` | `Expressions` |
| `10` | `W` | `Watch/Break` |
| `12` | `M` | `Memory Operations` |
| `15` | `S` | `System Commands` |
| `18` | `X` | `Regular Xpressions` |

`CVP.HLP` adds one more category:

- `21` / `T` / `Thread Command`

Every first-screen index is below `ScreenCount`. Menu order need not be physical
screen order; different titles can also address the same screen. A menu click
selects this index directly. The title is at most 20 bytes and may occupy all
20 without a terminating NUL; padding after the first NUL is not visible text.

For grouped display, the distinct first-screen indices define ranges:

- current category starts at its own `first screen`
- it ends before the next **larger** distinct first-screen index, or at
  `ScreenCount` for the final range; retain the authored order of menu labels

---

## Control / Style Table

After the menu table there is a `48`-byte control table. In all sampled files it
is byte-for-byte identical and consists of `16` consecutive 3-byte entries:

| Bytes | Meaning |
|-------|---------|
| `attr_lo attr_hi style_id` | one formatting dictionary entry |

The `style_id` bytes run in order from `0xE1` to `0xF0` in the examples. IDs
identify entries, so lookup does not require this physical ordering. All 16
IDs are distinct. Example from all three sampled files:

| Entry bytes |
|-------------|
| `17 07 E1` |
| `12 07 E2` |
| `13 70 E3` |
| `1F 0F E4` |
| `...` |
| `74 70 EF` |
| `0F 0F F0` |

This is a palette / attribute dictionary for the inline style markers used in
the payload stream. The meaning of the two attribute bytes is:

- first byte = color-display DOS text attribute
- second byte = monochrome-display attribute / fallback variant

A DOS color attribute uses bits 0–3 for foreground, bits 4–6 for background
and bit 7 for blink/background intensity depending on adapter mode.

External support for the second byte interpretation:

- Microsoft CodeView documentation states that black-and-white mode uses
  `normal text`, `high-intensity text`, and `reverse-video text`.
- Microsoft KB Q44412 documents standard monochrome adapter attributes:
  `07 = normal`, `0F = high intensity`, `70 = reverse video`, `87 = blinking`.

These values match the second bytes in the triplets. Original CodeView searches
the entries for the received style ID and selects the attribute at offset
`+0` or `+1` using its display-mode flag. The screen routine starts at DOS
attribute `07h`; an `E1h` control explicitly selects the body-text attribute,
it is not implicitly selected at screen entry.

The reader tries dictionary lookup for standalone bytes with their high bit
set, after handling `FFh` as RLE. Thus a custom selector can use `80h`–`FEh`;
`E1h`–`F0h` is the example dictionary, not a hardwired source-byte class.
A high byte absent from the dictionary is an ordinary OEM glyph. Low bytes
cannot select a style, and `FFh` cannot select one because it is the RLE prefix.

---

## Screen Descriptor Table

After the control table come `ScreenCount` active descriptors. The observed
40-slot allocation contains additional unused records; these are not screens.

Descriptor layout:

| Offset | Size | Type | Meaning |
|--------|------|------|---------|
| `+00` | 2 | `WORD` | Next screen index, zero-based |
| `+02` | 2 | `WORD` | Previous screen index, zero-based; first screen wraps to the last one |
| `+04` | 4 | `DWORD` | Payload offset |
| `+08` | 4 | `DWORD` | Payload length |

Both navigation indices must be below `ScreenCount`. In the supplied originals
they describe a circular sequence, but they are stored pointers, not display
numbers to regenerate from descriptor order. Absolute payload positions also
need not increase with descriptor order. Reserved slots in the examples are
zero-filled; a decoder must not use inactive bytes as another descriptor.

Example, `CV.HLP` first screens:

| Next | Prev | Offset | Length |
|--------|------|--------|--------|
| `1` | `19` | `0x02DE` | `0x0362` |
| `2` | `0` | `0x0640` | `0x048D` |
| `3` | `1` | `0x0ACD` | `0x02E4` |

In the circular example, descriptor `i` has:

- `next = current + 1` for non-final descriptors
- the last screen wraps to `0`

For `ScreenCount = 20`, its final pair is `0000h, 0012h` (Next=0, Prev=18).
The visible `#20` label lives in the payload and is not this first WORD.

---

## Screen Payload Encoding

The payload stream is stored as CP437 text with inline formatting control bytes.

Observed byte classes:

- `0x0D 0x0A`: normal line break
- `0x00`: end of indexed screen; later bytes are not another row
- `0xFF <count> <byte>`: simple run-length encoding, expand `<byte>` repeated
  `<count>` times
- high bytes matching a style ID: select its dictionary attribute; the
  inspected dictionary uses `0xE1` .. `0xF0`
- CP437 printable text and box-drawing characters; other literal video bytes
  use IBM PC glyphs rather than Unicode control characters

`FFh count byte` writes **literal cells**: do not recursively interpret the
repeated byte as a style selector, NUL terminator, newline or another RLE
prefix. Count zero is a complete, zero-output operation. A trailing `FFh` or
`FFh count` is incomplete and must not borrow its operand from the next screen.

Example, starting at attribute `07h`:

```text
E4 41 FF 02 E1 FF 01 0A 00
```

`E4h` selects attribute `1Fh` in the example dictionary. The visible cells are
`Aßß◙`: `E1h` repeated twice is CP437 sharp-s, and the repeated `0Ah` is the
video glyph `◙`, not a line break. The final standalone `00h` ends the screen.

Important distinction from the raw byte stream:

- low bytes such as `0x04`, `0x08`, `0x1B` visible in the compressed payload are
  only the `<count>` part of `0xFF <count> <byte>` sequences in the sampled
  files; they do **not** survive RLE expansion as standalone inline controls

In the currently sampled screen payloads, the actual inline style markers that
appear are limited to `0xE1`, `0xE2`, `0xE3`, `0xE4`, and `0xEF`.

Working semantic interpretation from visible screens:

- `0xE1`: default body text
- `0xE2`: headings / command labels
- `0xE3`: placeholders and user-supplied metavariables
- `0xE4`: literal keys, commands, punctuation, and bracket markers
- `0xEF`: reset / structural text used around screen markers and footers

Example attribute decoding from the shared 48-byte dictionary:

| Style | Color attr | Mono attr | Working meaning |
|-------|------------|-----------|-----------------|
| `E1` | `0x17` | `0x07` | body text |
| `E2` | `0x12` | `0x07` | headings / command names |
| `E3` | `0x13` | `0x70` | placeholders |
| `E4` | `0x1F` | `0x0F` | literals / hotkeys |
| `EF` | `0x74` | `0x70` | screen markers / footer band |

For readable plain-text extraction the following is sufficient:

1. parse within the descriptor's byte range; stop at standalone `00h`
2. expand complete `FFh count byte` triples to literal display cells
3. apply standalone style selectors without emitting a character
4. discard standalone CR and start a new row at standalone LF
5. decode literal cells as the IBM PC CP437 video glyphs

That produces legible screens with their line-drawing layout preserved.
The native renderer wraps at 78 cells and uses a fixed text viewport; these
are display rules, not stored paragraph or topic-length fields.

---

## Visible Screen Structure

Decoded screens typically contain:

1. a screen number marker such as `# 4`
2. the main visible content
3. a footer line like `SCREEN 2 OF 3 (Display Commands)`

The footer is useful metadata:

- `SCREEN X OF Y` gives page position inside a category
- `(Category Name)` matches the menu grouping

---

## Notes For Reader Implementation

- Detect by signature `b"BW03"`, never by file suffix alone.
- Use menu entries as the canonical category/index source.
- Use descriptor order as topic order.
- Parse RLE operands as literal cells, independently of standalone controls.
- Preserve box-drawing characters.
- Generate category-local navigation from menu ranges.
- Read global `Prev` / `Next` from their stored descriptor WORDs.

## Plain-Text Command Summary

CodeView's short-help routine seeks to:

```text
SummaryStart = Descriptor[ScreenCount-1].PayloadOffset
             + Descriptor[ScreenCount-1].PayloadLength
```

In the inspected files this is the unindexed suffix after all screen payloads.
It is not a 41st descriptor, compressed screen, or an extra menu record.
The two routines use different control grammars:

| Byte | Plain-text summary meaning |
|---|---|
| `00h` | End of summary |
| `0Dh` | Ignored |
| `0Ah` | Console newline |
| `0Ch` | Pause between pages; a key continues, Escape stops |
| Other bytes | Console text; neither RLE nor style-table lookup |

In particular, `FFh` and `E1h` are text here, not the indexed-screen controls.
The supplied suffixes contain printable ASCII, CR/LF and the final NUL; other
console controls can depend on the active DOS console and are not established
by these examples. If the final screen is also EOF, no summary bytes exist.
No checksum can establish that a wholly absent unindexed summary was present
before truncation.

| Example | SummaryStart | Total suffix bytes, including NUL |
|---|---:|---:|
| CodeView 5.0 `CV.HLP` | `409Eh` | 1806 |
| CodeView 5.1 `CV.HLP` / `CVP.HLP` | `4D86h` | 1706 |

The summaries begin with headings for executing code and examining data. The
summary has no stored context number, title, page count or length WORD;
`0Ch` boundaries and final `00h` delimit it.

---

## Related Formats

- Later Microsoft QuickHelp databases use `LN`, documented separately in
  [Microsoft QuickHelp.md](Microsoft%20QuickHelp.md)
