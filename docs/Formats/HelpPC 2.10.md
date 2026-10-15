# HelpPC 2.10 Text Database Format

> Created: 2026-09-29 · Last updated: 2026-10-11

HelpPC is a DOS quick-reference system. Its readable source consists of
independent `.TXT` databases; `INDEXHLP` / `BUILD` creates `HELPPC.NDX`
from them. This document describes the text database format, not the
undocumented binary layout of `.NDX`.

The primary specification is **Creating your own Help Files** in the
original `HELPPC.DOC` shipped with HelpPC 2.10. The same format is also
described by the [HelpPC format reference](https://stanislavs.org/helppc/helppc_format.html).
The local 2.10 manual says source lines should not exceed **79 characters**;
the online reference says 70. These are source-size recommendations, not a
field stored in the TXT.

## File structure

Each database begins with one `@` title line. The remainder is a sequence
of topics. A `:` key line starts a topic; all subsequent display lines
belong to it until the next key line or end of file.

```text
@Example database title
:first key:alternate key
^First topic heading
 Normal text with a ~second key~ link.

:second key
%Highlighted line
 Text containing a literal ~~ tilde.
```

The `@` title appears in HelpPC's main menu. The first key of each topic
appears in its subtopic menu; additional colon-separated keys point to the
same topic. Keys may contain single spaces. HelpPC compresses consecutive
spaces in a key to one space for lookup.

The original manual specifies DOS CR/LF line endings and eight-column tab
stops. It calls the files ASCII, but the distributed data also contains
DOS box-drawing bytes; the English sample is decoded as CP437.

## Column-one controls

| First character | Meaning |
|-----------------|---------|
| `@` | Database title; required on the first line. |
| `:` | New topic and one or more lookup keys. |
| `%` | Highlight the entire display line. |
| `^` | Center and highlight the display line. |
| Space | Display ordinary text. |
| Tab | Begin display text at column 9. |
| Other | Not displayed by the original HelpPC viewer. |

The control character occupies column one and is not part of the displayed
text. The native renderer starts ordinary and `%` text at zero-based column 1
(the second screen column), and a leading TAB at column 8. A blank line remains
a blank display line. Tabs within display text advance to the next eight-column
stop using the **actual output column**, not the byte position in the source.

## Centering and tab expansion

For a `^` line, the zero-based start column is:

```text
column = floor((80 - byte_length(source_after_control)) / 2)
```

Measure source bytes before expanding TAB or consuming tilde controls.
Centering the eventual displayed text gives a different position. Internal
TAB advances to the next multiple of eight from the actual output column.
Ordinary and `%` rows start at column 1; a leading TAB starts at 8.

For example, `^PORTS<TAB>Common I/O Port Addresses` has 31 source bytes after
`^`, so starts at column 24. After `PORTS`, TAB advances from column 29 to 32;
centering the expanded heading instead would give a different result.

## Inline links

A phrase between two tildes is a link to a topic key, even when that key is
in a different `.TXT` database:

```text
 See ~FLAGS~ and ~Instruction Timing~.
```

Two consecutive tildes (`~~`) produce a literal `~` character. Link labels
serve as lookup keys; there is no separate numeric destination in the text
file. An index built from the complete set of databases is therefore needed
for cross-file navigation.

The original renderer also consumes an unclosed `~` marker through the end
of the current row. One such row occurs in the `int 2a,81` article of the
original `INTERRUP.TXT`. The marker is not displayed; subsequent characters
remain visible through the row end.

## Original HelpPC limits

These are limits of the DOS application stated in `HELPPC.DOC`:

| Item | Limit |
|------|------:|
| Main-menu databases | 16 |
| Subtopic-menu items | 512 |
| Indexed topics | 1,800 |
| Topic text | 16,384 bytes |
| Lines per topic | 512 |
| Topic key | 20 bytes |
| Database title | 40 bytes |
| Database file size | No stated limit |

## Distributed HelpPC 2.10 sample

The inspected distribution contains these six topic databases. CRC32 values
identify the exact source examples:

| File | CRC32 | Topics |
|------|-------|-------:|
| `ASM.TXT` | `6B1B3FB7` | 161 |
| `C.TXT` | `0E21B5FB` | 410 |
| `HARDWARE.TXT` | `4AA25C65` | 20 |
| `INTERRUP.TXT` | `0E038E1B` | 358 |
| `MISC.TXT` | `F7B1BD0B` | 14 |
| `TABLES.TXT` | `96D09BA1` | 43 |

This totals **1,006 topics**. `HELPPC.DOC` also names `DOS.TXT`, but that
file is absent from the selected distribution. `HELPPC.NDX` is the index
generated for the original HelpPC executable, not another topic source.

## Lookup and absent fields

Lookup ignores letter case and compresses repeated spaces in keys and link
labels. Their displayed spelling and spacing remain significant source text.
Cross-database keys use all databases participating in the index.

Numeric context IDs, topic-offset tables, RGB palettes and display-width fields
are not stored in TXT. The native renderer uses an 80-column screen. Some
ordinary rows expand to 81–82 cells after TAB; the screen clips the overrun.
Centered source text longer than 80 bytes causes unsigned-margin underflow,
not a defined alternative centering rule.
