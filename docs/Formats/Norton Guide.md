# Norton Guide (NG) File Format

_Note: This page summarizes the Norton Guide / Expert Help binary layout as
used by THelpViewer, based primarily on Dave Pearson's reverse-engineered
documentation and verified against sample `.NG` files in this repository._

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

The header does **not** contain an explicit root-topic offset. Readers normally
start with the first record immediately after the header and then traverse the
pointer graph.

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
| Length | `short` | Record length in bytes. |
| Line Count | `short` | Number of lines in this entry. |
| Unknown | `short` | Undocumented. |
| Parent Line | `short` | 1-based line number in the parent entry that points here. |
| Parent | `long` | File offset of the parent entry. |
| Menu | `short` | Menu number that points here. |
| Menu Prompt | `short` | Prompt number inside that menu. |
| Unknown | `char[8]` | Undocumented. |
| Line descriptors | variable | In the sampled guides used by THelpViewer, each line uses `WORD text_offset + DWORD target_offset`. The text offset is relative to the fixed 26-byte SHORT header. |
| Lines | variable | `Line Count` NUL-terminated text lines. Some sampled guides store the last few line strings slightly beyond the nominal record length, so a reader may need a small lookahead past `Length`. |

In practice, the human-readable label for many child topics is stored here, not
inside the child `LONG` record itself.

## Long Entry

Long entries contain the main body text for a topic.

| Field | Size | Notes |
|---|---:|---|
| ID | `short` | Always `1`. |
| Length | `short` | Record length in bytes. |
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
| Length | `short` | Record length in bytes. |
| Prompt Count | `short` | Number of prompts in the menu. |
| Unknown | `char[20]` | Undocumented. |
| Pointers | `long[Prompt Count]` | Target entry for each menu prompt. |
| Unknown | variable | Sample guides appear to contain additional per-prompt offset data here; the exact structure is not fully documented. |
| Title | variable | Menu title, NUL-terminated string when present. |
| Prompts | variable | `Prompt Count` menu labels. In sampled guides the prompt-string tail may also extend slightly past the nominal record length. |

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

Two practical notes from the sample corpus in this repository:

- `SHORT` entries are more reliably parsed from their per-line text offsets than
  by assuming the text lines begin immediately after a flat pointer table.
- `MENU` and `SHORT` string tails may continue a little beyond the formal
  `Length` field, so strict truncation at `Length` can lose the last labels.

## External References

- Dave Pearson: [The Norton Guide database file format](https://www.davep.org/norton-guides/file-format/)
- Archiveteam / Just Solve: [Norton Guides help file](https://fileformats.archiveteam.org/wiki/Norton_Guides_help_file)

_This documentation is part of the THelpViewer project. For the full index of
format notes, see [FORMATS.md](FORMATS.md)._
