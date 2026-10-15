# Norton Guide (NG) File Format

> Created: 2026-04-07 · Last updated: 2026-10-11

All WORD/DWORD fields are unsigned little-endian integers (16/32 bits).
File offsets are absolute and zero-based; record-relative offsets are
explicitly identified below. Field offsets describe decrypted records.

## Overview

Norton Guide databases are DOS help files built from a small unencrypted header
followed by a series of encrypted records. Records reference each other by
absolute file offsets, so navigation is based on direct pointer chasing rather
than a separate global index table.

Record types:

- `0` = Short Entry
- `1` = Long Entry
- `2` = Menu Entry

Important properties:

- The file header is unencrypted and is always 378 bytes long.
- All records after the header are XOR-encrypted with `0x1A`.
- Text is CP437 and may contain both style escapes and simple space-run
  compression.
- There is no dedicated global alphabetical index structure in the format.
- All `MENU` records occur first, followed by all `SHORT` and `LONG` entries.
- Links contain absolute file offsets, but records themselves must be read
  sequentially so that unreferenced entries and secondary menus are preserved.

## Header

The header layout is:

| Offset | Field | Size | Meaning |
| --- | --- | ---: | --- |
| `000h` | Magic | 2 | `474Eh` (NG) or `4845h` (EH) |
| `002h` | Unknown | 2 | Undocumented WORD |
| `004h` | Unknown | 2 | Undocumented WORD |
| `006h` | Menu count | 2 | Number of leading MENU records |
| `008h` | Title | 40 | Fixed-width CP437 field; first NUL ends text, if present |
| `030h` | Credit 1 | 66 | Same string rule |
| `072h` | Credit 2 | 66 | Same string rule |
| `0B4h` | Credit 3 | 66 | Same string rule |
| `0F6h` | Credit 4 | 66 | Same string rule |
| `138h` | Credit 5 | 66 | Same string rule |

The header does **not** contain an explicit root-topic offset. The first record
starts immediately after the 378-byte header. `Menu count` is the exact number
of consecutive `MENU` records at the start of the encrypted record stream.
The title and credits can fill their entire field without a NUL. Do not
search beyond a field's fixed width for its terminator. There is no verified
version discriminator in either undocumented header WORD.

## Physical Record Sequence and Size

Every record begins with the following six bytes, followed by a type-specific
20-byte fixed header:

| Field | Size | Notes |
|---|---:|---|
| ID | `WORD` | `0` = SHORT, `1` = LONG, `2` = MENU. |
| Payload Size | `WORD` | Number of bytes after the 26-byte fixed header. |
| Type field | `WORD` | Line count for SHORT/LONG; stored menu count for MENU. |

The next record begins at:

```text
next_offset = current_offset + 26 + payload_size
```

`Payload Size` is **not** the complete record length. A LONG with one line
`A 00` needs just two payload bytes. A SHORT or LONG with zero lines can have
zero payload bytes; its 26-byte record still has a valid address.

The reader must first consume exactly `Header.MenuCount` MENU records and then
continue sequentially through SHORT/LONG records until EOF. Pointer traversal
alone is insufficient because secondary menus and some entries are not
reachable from the first menu.
There is no alignment gap between the file header and the first record, nor
between consecutive physical records. EOF must coincide with a record end.
An empty database consists of the complete file header with `MenuCount = 0`.

## Encryption and Text Encoding

- Every byte after the 378-byte file header, including fixed record headers,
  is XOR-encrypted with `0x1A`.
- Text is stored in CP437.
- In SHORT/LONG body strings, `FF nn` emits `nn` cells containing byte `20`.
  The count is unsigned: `FF FF` is 255 spaces, not a literal `FF` or a
  one-space special case. A bare final `FF` encounters the string's NUL
  and emits nothing. Raw `00` terminates the string before text decoding;
  it is not a count operand permitting continuation into another string.
  MENU/see-also captions use the separate plain-string rules below, not this
  space-run decoder.

For example, decrypted `41 FF 03 42 00` is a five-cell line `A   B`;
the encrypted bytes are `5B E5 19 58 1A`. The terminating raw `00`
(encrypted `1A`) is not a display cell. `^C41` is an encoded literal `A`;
it is distinct from an on-disk text delimiter.

### Body-line controls and attributes

The following rendering rules describe Norton Guides 1.00, 1.02 and 1.04.
Expert Help-specific rendering extensions are not independently verified.
Each line starts with one current attribute byte, not a stack of independent
bold/underline/reverse flags. Attributes are viewer configuration, not fields
in the NG header; the standard color palette is:

| Name | Default attribute | Meaning on a color text display |
|---|---:|---|
| Normal | `07` | Light gray on black |
| Reverse / selected row | `70` | Black on light gray |
| Bold | `0F` | Bright white on black |
| Underline category | `7F` | Bright white on light gray; not a literal underline bitmap |

Decode an escape by consuming `5E` (`^`) and uppercasing the following byte.
ASCII `61`–`7A` become `41`–`5A`. The OEM uppercase substitutions are:

```text
81→9A  82→90  84→8E  86→8F  87→80  91→92  94→99  A4→A5
```

All other bytes remain unchanged. This fold applies only to escape dispatch
and numeric operands, not ordinary text cells.

| Escape | Operation |
|---|---|
| `^B`, `^U`, `^R`, `^N` | Request the configured bold, underline, reverse or normal attribute |
| `^Ann` | Request the literal attribute formed from the next two operand bytes |
| `^Cnn` | Emit the literal character byte formed from the next two operand bytes |
| `^^` | Emit one `5E` cell; a special instance of the fallback below |
| `^x` with any other folded `x` | Emit folded `x` as one literal cell; do not discard it and do not emit the caret |
| Final bare `^` | Encounter NUL and end without emitting a cell |

For any attribute request `requested`, assign normal if it equals the current
attribute, otherwise assign `requested`. Equality is byte equality: `^A0F`
while bold is active returns to normal, just as a second `^B` would. A new
different attribute replaces the old one. Restore the entry attribute at the
end of each displayed line. If the line's entry attribute equals the configured
reverse attribute (a selected SHORT row), suppress all attribute requests so
its entire row stays selected; character escapes still take effect.

Example using the standard palette:

```text
^Bx^Uy^A1Fz^A1Fw^A0Fv^Bu
cells:       x  y  z  w  v  u
attributes: 0F 7F 1F 07 0F 07
```

### Numeric operands and literal glyphs

For a valid two-digit hexadecimal operand, the resulting byte is the usual
`16*first + second`. The original routine does not validate hexadecimal
syntax: after the uppercase fold, it calculates each byte as follows:

```text
nibble(c) = (c - 30h) & FFh  if c <= 39h
            (c - 37h) & FFh  otherwise
value = ((nibble(first) << 4) | nibble(second)) & FFh
```

Thus `^Cgg` emits `10h`, and `^C/0` emits `F0h`; neither is an instruction
to silently remove four bytes. A NUL encountered before the first operand
returns zero; after one operand it returns that first computed nibble without
shifting. In a bounded string, incomplete `^C1` therefore emits `01h`, and
incomplete `^C` emits one `00h` cell. End that string after such an incomplete
operand. The original pointer routine may advance past that NUL and continue
reading adjacent memory; this behavior must not be used to infer additional
text or a permission to cross record/string boundaries.

Literal `^C` results are video cells, not recursively decoded escapes or
terminal controls. `^C5E` is a caret, `^CFF` the font's `FFh` cell, and `^C00`
a blank glyph occupying one cell, not an end-of-string instruction. Ordinary
non-control bytes use the same video-cell semantics. In particular, low CP437
cells do not create TAB stops, line breaks or terminal actions:

```text
00 blank   01 ☺   02 ☻   03 ♥   04 ♦   05 ♣   06 ♠   07 •
08 ◘       09 ○   0A ◙   0B ♂   0C ♀   0D ♪   0E ♫   0F ☼
10 ►       11 ◄   12 ↕   13 ‼   14 ¶   15 §   16 ▬   17 ↨
18 ↑       19 ↓   1A →   1B ←   1C ∟   1D ↔   1E ▲   1F ▼
7F ⌂
```

Cells `20h`–`7Eh` and `80h`–`FFh` use ordinary IBM CP437 glyphs. Hardware font
replacement can alter their appearance; the file does not embed a font.
The standard renderer accepts 78 visible cells per body row and then stops
processing that row; shorter rows are padded for screen clearing. This is a
viewport limit, not a field stored in the string. An archival decoder can keep
the full expanded logical line separately from this clipped screen projection.
DOS attribute bits 0–3 select foreground, 4–6 background, and bit 7 blink
on the usual blink-enabled adapter; adapter blink/intensity mode is external
configuration rather than part of the NG file.

## Short Entry

Short entries usually act as menu-like lists of labeled jumps to other entries.

| Relative offset | Field | Size | Notes |
| --- | --- | ---: | --- |
| `+00h` | ID | `WORD` | Always `0`. |
| `+02h` | Payload Size | `WORD` | Bytes after the fixed header; total size is `26 + Payload Size`. |
| `+04h` | Line Count | `WORD` | Number of lines in this entry. |
| `+06h` | Unknown | `WORD` | Undocumented. |
| `+08h` | Parent Line | `WORD` | 1-based line number in the parent entry that points here. |
| `+0Ah` | Parent | `DWORD` | File offset of the parent entry. |
| `+0Eh` | Menu | `WORD` | Menu number that points here; ordinal base unverified. |
| `+10h` | Menu Prompt | `WORD` | Prompt number inside that menu; ordinal base unverified. |
| `+12h` | Unknown | `char[8]` | Undocumented. |
| `+1Ah` | Line descriptors | `6 × Line Count` | Each line uses `WORD text_offset + DWORD target_offset`. Text begins at `record_start + 26 + text_offset`; target is an absolute record offset. |
| variable | Lines | variable | NUL-terminated text addressed by each descriptor, contained inside the physical record. |

For descriptor `i` (zero-based), read its WORD and DWORD at `26 + 6*i`.
If its text offset is `T`, the string begins at relative offset `26 + T`,
not at `T` and not at the target record address. Require:

```text
descriptor_end = 26 + 6 * LineCount
descriptor_end <= 26 + T < 26 + PayloadSize
```

The first NUL at or after that position must occur before the physical
record end. Descriptor order is display-line order. Text positions need not
be sorted or unique; shared positions produce shared strings, not missing
lines. Padding between strings or after the last string is opaque.

Example: a SHORT at `017Ah` with `LineCount = 2`, `PayloadSize = 16`
can have this decrypted payload:

```text
0C 00 7A 01 00 00  0E 00 FF FF FF FF  41 00 42 00
```

The descriptors occupy 12 bytes. They select `A` at `017Ah + 26 + 12`
and `B` at `017Ah + 26 + 14`. The first line links to `017Ah` itself;
the second has no target. The next physical record is at `01A4h`.

In practice, the human-readable label for many child topics is stored here, not
inside the child `LONG` record itself.
The target belongs to the entire selectable SHORT row, including leading
spaces, inter-column padding and any description after the first `FF` run.
No first-padding delimiter or character-range field limits the jump to the
first word/column. An empty row can still have a stored destination.

## Long Entry

Long entries contain the main body text for a topic.

| Relative offset | Field | Size | Notes |
| --- | --- | ---: | --- |
| `+00h` | ID | `WORD` | Always `1`. |
| `+02h` | Payload Size | `WORD` | Bytes after the fixed header; total size is `26 + Payload Size`. |
| `+04h` | Line Count | `WORD` | Number of visible text lines. |
| `+06h` | See Also Flag | `WORD` | Any non-zero value means a see-also section follows the lines. |
| `+08h` | Parent Line | `WORD` | 1-based line number in the parent entry that points here. |
| `+0Ah` | Parent | `DWORD` | File offset of the parent entry. |
| `+0Eh` | Menu | `WORD` | Menu number that points here; ordinal base unverified. |
| `+10h` | Menu Prompt | `WORD` | Prompt number inside that menu; ordinal base unverified. |
| `+12h` | Previous | `DWORD` | File offset of the previous sibling entry. |
| `+16h` | Next | `DWORD` | File offset of the next sibling entry. |
| `+1Ah` | Lines | variable | `Line Count` NUL-terminated text lines. |

If `See Also Flag != 0`, the text lines are followed by:

| Field | Size | Notes |
|---|---:|---|
| See Also Count | `WORD` | Number of see-also entries. |
| Pointers | `DWORD[See Also Count]` | Target file offset for each see-also label. |
| See Also Labels | variable | `See Also Count` NUL-terminated strings. |

Read exactly `LineCount` raw NUL-terminated strings from `+1Ah`, advancing
past each NUL, even for an empty string. If the flag is nonzero, read the
complete count, then the entire pointer table, then exactly that many labels.
A zero see-also count is valid. All these fields remain inside this record;
the next record cannot provide a missing terminator or table byte. Bytes
remaining after the declared content are opaque padding, which need not
be zero. Do not interpret them as extra lines or records.

The first visible line of a `LONG` entry is often a section heading such as
`DESCRIPTION` or `SYNTAX`; it is not a reliable authoritative topic title.

## Menu Entry

Menu entries provide top-level or intermediate navigation nodes.

| Relative offset | Field | Size | Notes |
| --- | --- | ---: | --- |
| `+00h` | ID | `WORD` | Always `2`. |
| `+02h` | Payload Size | `WORD` | Bytes after the fixed header; total size is `26 + Payload Size`. |
| `+04h` | Stored Count | `WORD` | Must be at least one. `Prompt Count = Stored Count - 1`. |
| `+06h` | Descriptor offset | `WORD` | Offset of the prompt descriptors relative to `+1Ah`; normally `4 × Prompt Count`. |
| `+08h` | Unknown | `char[18]` | Undocumented. |
| `+1Ah` | Pointers | `DWORD[Prompt Count]` | Target entry for each menu prompt. |
| `+1Ah + DescriptorOffset` | Descriptors | `8 × (Prompt Count + 1)` | One descriptor per prompt, then an end descriptor. Layout below. |
| variable | Title | variable | Exactly one NUL-terminated title string; may be empty. |
| addressed | Prompts | variable | NUL-terminated labels selected by descriptor offsets, not by scanning title-adjacent strings. |
| addressed | Terminator | `char` | The last descriptor points to an empty NUL string. |

For `P = StoredCount - 1` and `D = WORD(+06h)`, descriptors begin at
`26 + D` and the title begins immediately after them, at
`26 + D + 8*(P+1)`. `D >= 4*P` keeps them beyond the target DWORDs;
any intervening bytes are opaque padding. Each descriptor is:

| Descriptor offset | Size | Meaning |
|---|---:|---|
| `+00h` | `WORD` | Caption offset relative to record `+1Ah`; add 26 to address it. |
| `+02h` | `WORD` | Check marker state; nonzero draws the native `FBh` check glyph. |
| `+04h` | `WORD` | Separator/disabled state; nonzero draws a horizontal rule instead of the caption and is skipped in item selection. |
| `+06h` | `WORD` | Keyboard shortcut code, displayed at the right of a menu row; zero means none. Ordinary byte codes and `100h + scan code` represent DOS keys. |

The remaining three WORDs of the end descriptor are not interpreted: its
first WORD points to the terminating empty string. These unused bytes may
contain nonzero material and are not a zero-padding invariant.

Read the title at its fixed computed position, but read prompt `i` at
`26 + WORD(26 + D + 8*i)`. Pair it with DWORD `i` in the target table.
Descriptor order is item order. Text offsets may be shared, unsorted, or
point to a substring/the title; do not substitute the next sequential string.
Every addressed string begins at or beyond the end of the complete table,
and its NUL must remain inside the physical record. Neither title nor prompt
has a separately stored length. Native popup sizing has implementation limits;
they do not establish an on-disk 40/50-byte string boundary. Unaddressed text
and bytes remaining before the record end are opaque, not extra prompts.

Example: `P=2`, `D=8`, descriptor positions `34, 42, 50`, title at `58`.
Payload-relative caption offsets `26h`, `26h`, `2Bh` address two shared
copies of `Item` at record `64` and its empty terminator at `69`. The title
can be `Title 00` at `58`; target DWORDs still independently identify each
item's destination. XOR the complete record by `1Ah` for storage.

The root screen of a guide is often a `MENU` record rather than a `SHORT` or
`LONG` topic.

### MENU and See Also caption rendering

These strings use the original plain-string routine, not the body-line
decoder. Carets are literal: `^BName^N` displays the entire eight-character
string unchanged, and `^^` displays two carets. `FFh` is the
CP437 blank/non-breaking-space glyph, not a run prefix. `41 FF FF 42 00`
therefore displays four cells `A`, blank, blank, `B`. Leading, trailing and
repeated spaces are cells too. Preserve symbols and source slot order; an
empty caption does not erase its separately stored target.

The generic DOS output routine handles `07h` as a no-op, `09h` as spaces to
the next eight-column absolute screen tab stop, `0Dh` as carriage return and
`0Ah` as cursor movement to the next screen row. Other nonzero bytes write
literal font cells. Unlike `^C` body results, these four bytes are terminal
controls in plain captions. Screen origin, clipping, scroll-at-bottom and
caption check/rule/shortcut chrome are viewer state, not bytes embedded in
the string. The same plain captions are used by the See Also selection
popup; it does not apply body formatting merely because a label contains `^`.

## Titles, Labels, and Navigation

Norton Guide does not have a single dedicated “topic title” field for `SHORT`
and `LONG` records.

Instead:

- `MENU` prompts provide human-readable labels for the entries they open.
- `SHORT` lines likewise provide labels for their child targets.
- `LONG` records point back to their parent and carry `Parent Line`, so a reader
  can recover the display label from the referring `MENU`/`SHORT` entry.
- `Previous` and `Next` in `LONG` records provide sibling navigation.
- `See Also` cross-references are stored separately from the main text.

Parent-derived labels identify destinations more directly than the
first visible line of a `LONG` topic whenever both are available.

### Pointer rules

`0` and `FFFFFFFFh` mean no record target. Every other MENU prompt,
SHORT target/parent or LONG see-also/parent/previous/next pointer must equal
an exact physical record start. A pointer inside a record is not an alias
for that record. Shared destinations, self-links and cycles are possible;
do not reject them merely for revisiting an address.

One terminal convention uses the exact file size for LONG `Next`; it means
no next page. This exception does not make EOF a target for any other pointer
field. No independently verified cross-file pointer structure is described
here: these DWORDs address this database, not another `.NG` file.

## Bounded decoding algorithm

1. Require the full 378-byte header and either magic. Read `MenuCount` and
   fixed-width strings without stepping into the encrypted record stream.
2. Start at `378`. Require a full 26-byte fixed record header, decrypt it,
   and compute `end = start + 26 + PayloadSize` with non-wrapping arithmetic.
   Require `end <= file_size`; decrypt exactly this record.
3. The first `MenuCount` records must be MENU; subsequent records must be
   SHORT or LONG. Validate type-specific tables, counts and NUL strings
   within `[start, end)`. Retain even zero-line records. Advance to `end`
   rather than searching for a plausible header in the payload.
4. Stop only at exact EOF. Require at least `MenuCount` records; a truncated
   header, missing declared MENU or leftover partial record is invalid.
5. Validate all raw record pointers against the set of record starts,
   applying only the explicit no-target and LONG-next EOF conventions.
   Build navigation after this pass so forward and unreferenced records work.

There is no verified whole-file checksum field. These structural checks
cannot detect arbitrary damage that leaves valid counts, addresses and text.

## External References

- Dave Pearson: [The Norton Guide database file format](https://www.davep.org/norton-guides/file-format/)
- Dave Pearson: [MENU decoding](https://github.com/davep/ngdb.py/blob/cb685aec5b1ed2c6153d823915c640258f6c30b7/src/ngdb/menu.py), including the count adjustment, auxiliary tables and trailer
