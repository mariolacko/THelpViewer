# Microsoft BW03 Help Format

## Overview

`BW03` is an older **DOS / OS/2 text-mode** Microsoft help format used by
pre-QuickHelp toolchains.  In the current source set it appears in:

- `CV.HLP` for CodeView DOS / DOS mode
- `CVP.HLP` for CodeView protected-mode / OS/2 mode

This is **not** the later QuickHelp `LN` format.  Files with the same `.HLP`
extension must therefore be detected by signature, not by suffix.

Status of this document:

- header, menu table, style table, descriptor table and text stream layout are
  confirmed from local sample files
- the second attribute byte in each style triplet is strongly supported as a
  monochrome DOS attribute by external Microsoft documentation, although no
  external source has yet been found that states the BW03 triplet semantics at
  byte-level explicitly

Sample files used:

- `Microsoft MASM and CodeView 5.0/CV.HLP`
- `Microsoft MASM and CodeView 5.1/CV.HLP`
- `Microsoft MASM and CodeView 5.1/CVP.HLP`

External product context:

- IBM CodeView/C documentation describes `CV.HLP` for DOS / DOS mode and
  `CVP.HLP` for OS/2 mode:
  https://www.bitsavers.org/pdf/ibm/pc/languages/15F0377_C2_1.10_Debug_1988.pdf
- PCjs file listings also show `CV.HLP` and `CVP.HLP` alongside `CV.EXE` and
  `CVP.EXE`:
  https://www.pcjs.org/software/pcx86/lang/microsoft/c/5.10-os2/

---

## File Header

Offset `0x00`:

| Offset | Size | Type | Meaning |
|--------|------|------|---------|
| `00` | 4 | ASCII | Signature, always `BW03` |
| `04` | 2 | `WORD` | Screen count actually used |
| `06` | 2 | `WORD` | Menu category count |

Immediately after the 8-byte header:

1. menu table, `MenuCount * 22` bytes
2. control / style dictionary, always `48` bytes in the sampled files
3. 40 fixed screen descriptors, `40 * 12` bytes
4. first screen payload begins immediately after the 40-slot descriptor array

The sampled files reserve space for **40 screen descriptors**, even when the
actual `ScreenCount` is smaller.

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

The first-screen index is enough to reconstruct category ranges:

- current category starts at its own `first screen`
- it ends before the next category's `first screen`

---

## Control / Style Table

After the menu table there is a `48`-byte control table. In all sampled files it
is byte-for-byte identical and consists of `16` consecutive 3-byte entries:

| Bytes | Meaning |
|-------|---------|
| `attr_lo attr_hi style_id` | one formatting dictionary entry |

The `style_id` bytes run in order from `0xE1` to `0xF0`. Example from all three
sampled files:

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
the payload stream. The current working meaning of the two attribute bytes is:

- first byte = color-display DOS text attribute
- second byte = monochrome-display attribute / fallback variant

The converter exports inline BW03 styles to UHF using the first attribute byte,
split into DOS `fg/bg` nibbles and resolved through the standard UHF `cga`
palette. The second byte is preserved as additional palette metadata under a
`bw03-mono` palette.

External support for the second byte interpretation:

- Microsoft CodeView documentation states that black-and-white mode uses
  `normal text`, `high-intensity text`, and `reverse-video text`.
- Microsoft KB Q44412 documents standard monochrome adapter attributes:
  `07 = normal`, `0F = high intensity`, `70 = reverse video`, `87 = blinking`.

These external descriptions match the second-byte values seen in BW03 triplets
exactly, but they still stop short of an explicit byte-level statement about the
BW03 file format itself.

---

## Screen Descriptor Table

After the control table comes a fixed array of **40 descriptors**.

Descriptor layout:

| Offset | Size | Type | Meaning |
|--------|------|------|---------|
| `+00` | 2 | `WORD` | 1-based screen number |
| `+02` | 2 | `WORD` | Previous screen index, zero-based; first screen wraps to the last one |
| `+04` | 4 | `DWORD` | Payload offset |
| `+08` | 4 | `DWORD` | Payload length |

Only the first `ScreenCount` descriptors are active; the remaining reserved
slots are zero-filled.

Example, `CV.HLP` first screens:

| Screen | Prev | Offset | Length |
|--------|------|--------|--------|
| `1` | `19` | `0x02DE` | `0x0362` |
| `2` | `0` | `0x0640` | `0x048D` |
| `3` | `1` | `0x0ACD` | `0x02E4` |

The next screen can be inferred from descriptor order:

- `next = current + 1`
- the last screen wraps to `0`

---

## Screen Payload Encoding

The payload stream is stored as CP437 text with inline formatting control bytes.

Observed byte classes:

- `0x0D 0x0A`: normal line break
- `0x00`: logical line separator / block separator; treating it as a newline
  yields readable output
- `0xFF <count> <byte>`: simple run-length encoding, expand `<byte>` repeated
  `<count>` times
- `0xE1` .. `0xF0`: inline style / emphasis control bytes whose attribute pairs
  are defined in the 48-byte dictionary described above
- CP437 printable text and box-drawing characters

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

1. expand `0xFF count byte`
2. treat `0x00` as a line break
3. strip `0xE1 .. 0xF0`
4. decode the result as `CP437`

That produces legible screens with their line-drawing layout preserved.

For richer UHF export the converter may instead keep the inline style runs and
emit them as UHF `[color:fg:bg]...[/color]` spans using the decoded DOS
attributes.

---

## Visible Screen Structure

Decoded screens typically contain:

1. a screen number marker such as `# 4`
2. the main visible content
3. a footer line like `SCREEN 2 OF 3 (Display Commands)`

The footer is useful metadata:

- `SCREEN X OF Y` gives page position inside a category
- `(Category Name)` matches the menu grouping

The converter reader uses this footer to derive:

- `topic.names[]`
- page numbering for multi-screen categories
- category-local `Up` / `Down` navigation
- UHF `contents[]` entries reconstructed from the BW03 menu table
- optional viewer app-bar menu items reconstructed from the same BW03 menu table

---

## Notes For Reader Implementation

- Detect by signature `b"BW03"`, never by file suffix alone.
- Use menu entries as the canonical category/index source.
- Use descriptor order as topic order.
- Decode payloads as CP437 after RLE expansion and control-byte stripping.
- Preserve box-drawing characters.
- Generate category-local navigation from menu ranges.
- Generate global `Prev` / `Next` from descriptor order and wrap-around.

---

## Related Formats

- Later Microsoft QuickHelp databases use `LN`, documented separately in
  [Microsoft QuickHelp.md](Microsoft%20QuickHelp.md)
