# Microsoft BW03 Help Format

## Overview

`BW03` is an older **DOS / OS/2 text-mode** Microsoft help format used by
pre-QuickHelp toolchains.  In the current source set it appears in:

- `CV.HLP` for CodeView DOS / DOS mode
- `CVP.HLP` for CodeView protected-mode / OS/2 mode

This is **not** the later QuickHelp `LN` format.  Files with the same `.HLP`
extension must therefore be detected by signature, not by suffix.

Status of this document:

- header, menu table, screen table and text stream layout are confirmed from
  local sample files
- some attribute bytes are still only partially reverse-engineered

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
2. small control / style table, observed as `46-48` bytes in local samples
3. 24 fixed screen descriptors, `24 * 12` bytes
4. zero padding until the first screen payload

The sample files always reserve space for **24 screen descriptors**, even when
the actual `ScreenCount` is smaller.

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

After the menu table there is a small control table.  In the sampled files it
contains non-zero bytes and is stable in shape, but not perfectly constant in
length across all variants, so the reader locates the descriptor table by
validating the first screen records instead of relying on one hard-coded offset.

The reader currently treats it as an opaque formatting dictionary.

---

## Screen Descriptor Table

After the control table comes a fixed array of **24 descriptors**.

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
- `0xE1` .. `0xF0`: inline style / emphasis control bytes
- CP437 printable text and box-drawing characters

For readable plain-text extraction the following is sufficient:

1. expand `0xFF count byte`
2. treat `0x00` as a line break
3. strip `0xE1 .. 0xF0`
4. decode the result as `CP437`

That produces legible screens with their line-drawing layout preserved.

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
