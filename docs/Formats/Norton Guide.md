# Norton Guide (NG) File Format

> Created: 2026-04-07 · Last updated: 2026-09-19

_This page summarizes the Norton Guide / Expert Help binary layout as used by
THelpViewer. It combines Dave Pearson's reverse-engineered documentation with
byte-level validation against every `.NG` file in the repository._

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

| Field | Size | Notes |
|---|---:|---|
| Magic Value | `short` | `0x474E` = Norton Guide (`"NG"`), `0x4845` = Expert Help (`"EH"`). |
| Unknown | `short` | Undocumented. |
| Unknown | `short` | Undocumented. |
| Menu count | `short` | Number of main menus. |
| Title | `char[40]` | CP437, NUL-terminated if shorter than 40 bytes. |
| Credit line 1 | `char[66]` | CP437, NUL-terminated if shorter than 66 bytes. |
| Credit line 2 | `char[66]` | Same layout. |
| Credit line 3 | `char[66]` | Same layout. |
| Credit line 4 | `char[66]` | Same layout. |
| Credit line 5 | `char[66]` | Same layout. |

The header does **not** contain an explicit root-topic offset. The first record
starts immediately after the 378-byte header. `Menu count` is the exact number
of consecutive `MENU` records at the start of the encrypted record stream.

## Physical Record Sequence and Size

Every record begins with the following six bytes, followed by a type-specific
20-byte fixed header:

| Field | Size | Notes |
|---|---:|---|
| ID | `short` | `0` = SHORT, `1` = LONG, `2` = MENU. |
| Payload Size | `short` | Number of bytes after the 26-byte fixed header. |
| Type field | `short` | Line count for SHORT/LONG; stored menu count for MENU. |

The next record begins at:

```text
next_offset = current_offset + 26 + payload_size
```

`Payload Size` is **not** the complete record length. Valid compact LONG
entries can have `payload_size = 2`; rejecting values below 8 loses real topics
and their incoming links.

The reader must first consume exactly `Header.MenuCount` MENU records and then
continue sequentially through SHORT/LONG records until EOF. Pointer traversal
alone is insufficient because secondary menus and some entries are not
reachable from the first menu.

## Encryption and Text Encoding

- Record bodies are XOR-encrypted with `0x1A`.
- Text is stored in CP437.
- Byte sequence `0xFF nn` means “insert `nn` spaces”.
- Formatting escapes are inline in the text stream:
  - `^B` toggle bold
  - `^U` toggle underline
  - `^R` toggle reverse video
  - `^N` reset styles/colors to normal
  - `^Ann` set CP437 attribute byte (`bg << 4 | fg`)
  - `^Cnn` emit literal byte with hex value `nn`
  - `^^` emit a literal caret

## Short Entry

Short entries usually act as menu-like lists of labeled jumps to other entries.

| Field | Size | Notes |
|---|---:|---|
| ID | `short` | Always `0`. |
| Payload Size | `short` | Bytes after the fixed header; total size is `26 + Payload Size`. |
| Line Count | `short` | Number of lines in this entry. |
| Unknown | `short` | Undocumented. |
| Parent Line | `short` | 1-based line number in the parent entry that points here. |
| Parent | `long` | File offset of the parent entry. |
| Menu | `short` | Menu number that points here. |
| Menu Prompt | `short` | Prompt number inside that menu. |
| Unknown | `char[8]` | Undocumented. |
| Line descriptors | `6 × Line Count` | Each line uses `WORD text_offset + DWORD target_offset`. The text offset is relative to the fixed 26-byte SHORT header. |
| Lines | variable | `Line Count` NUL-terminated text lines contained inside the physical record. |

In practice, the human-readable label for many child topics is stored here, not
inside the child `LONG` record itself.

## Long Entry

Long entries contain the main body text for a topic.

| Field | Size | Notes |
|---|---:|---|
| ID | `short` | Always `1`. |
| Payload Size | `short` | Bytes after the fixed header; total size is `26 + Payload Size`. |
| Line Count | `short` | Number of visible text lines. |
| See Also Flag | `short` | Non-zero if a see-also section follows the lines. |
| Parent Line | `short` | 1-based line number in the parent entry that points here. |
| Parent | `long` | File offset of the parent entry. |
| Menu | `short` | Menu number that points here. |
| Menu Prompt | `short` | Prompt number inside that menu. |
| Previous | `long` | File offset of the previous sibling entry. |
| Next | `long` | File offset of the next sibling entry. |
| Lines | variable | `Line Count` NUL-terminated text lines. |

If `See Also Flag != 0`, the text lines are followed by:

| Field | Size | Notes |
|---|---:|---|
| See Also Count | `short` | Number of see-also entries. |
| Pointers | `long[See Also Count]` | Target file offset for each see-also label. |
| See Also Labels | variable | `See Also Count` NUL-terminated strings. |

The first visible line of a `LONG` entry is often a section heading such as
`DESCRIPTION` or `SYNTAX`; it is not a reliable authoritative topic title.

## Menu Entry

Menu entries provide top-level or intermediate navigation nodes.

| Field | Size | Notes |
|---|---:|---|
| ID | `short` | Always `2`. |
| Payload Size | `short` | Bytes after the fixed header; total size is `26 + Payload Size`. |
| Stored Count | `short` | Actual prompt count plus one. `Prompt Count = Stored Count - 1`. |
| Unknown | `char[20]` | Undocumented. |
| Pointers | `long[Prompt Count]` | Target entry for each menu prompt. |
| Unknown tables | `char[8 × (Prompt Count + 1)]` | Two undocumented arrays which must be skipped before reading text. |
| Title | variable | Menu title, NUL-terminated string when present. |
| Prompts | variable | Exactly `Prompt Count` NUL-terminated menu labels. |
| Unknown | `char` | One trailing byte after the prompt strings. |

The root screen of a guide is often a `MENU` record rather than a `SHORT` or
`LONG` topic.

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

For a faithful converter, parent-derived labels should take precedence over the
first visible line of a `LONG` topic whenever both are available.

Practical notes from the sample corpus in this repository:

- `SHORT` entries are more reliably parsed from their per-line text offsets than
  by assuming the text lines begin immediately after a flat pointer table.
- The stored MENU count includes one non-prompt slot. Reading it directly as
  `Prompt Count` consumes the first unknown-table value as a phantom pointer.
- Two final LONG entries use the exact file size as their terminal `Next`
  value. This is equivalent to no next page, not a topic offset.

## Repository Validation

The current repository corpus contains 58 NG files with this physical layout:

| Record class | Count |
|---|---:|
| MENU | 120 |
| SHORT + LONG | 21,189 |
| Total topics | 21,309 |

Reading all records sequentially produces the same 21,309 topic offsets and
resolves every internal text link, positioned hotspot, and non-terminal
directional navigation target. The converter deliberately does not strip
unresolved link markup as a repair strategy; a missing target is treated as a
parser or source-data error to investigate.

## External References

- Dave Pearson: [The Norton Guide database file format](https://www.davep.org/norton-guides/file-format/)
- Archiveteam / Just Solve: [Norton Guides help file](https://fileformats.archiveteam.org/wiki/Norton_Guides_help_file)

_This documentation is part of the THelpViewer project. For the full index of
format notes, see [Formats.md](../Formats.md)._
