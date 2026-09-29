# HelpPC 2.10 Text Database Format

> Created: 2026-09-29 · Last updated: 2026-09-29

HelpPC is a DOS quick-reference system. Its readable source consists of
independent `.TXT` databases; `INDEXHLP` / `BUILD` creates `HELPPC.NDX`
from them. This document describes the text database format, not the
undocumented binary layout of `.NDX`.

The primary specification is **Creating your own Help Files** in the
original `HELPPC.DOC` shipped with HelpPC 2.10. The same format is also
described by the [HelpPC format reference](https://stanislavs.org/helppc/helppc_format.html).
The local 2.10 manual says source lines should not exceed **79 characters**;
the online reference says 70. We follow the manual bundled with the
sample being converted.

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
text. A blank line remains a blank display line. Tabs within display text
advance to the next eight-column stop.

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

## Original HelpPC limits

These are limits of the DOS application stated in `HELPPC.DOC`, not limits
of the THelpViewer UHF output:

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

The downloaded archive contains these six topic databases. CRC32 values
identify the exact source files registered in
`thelpviewer/help-database.json`:

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

## THelpViewer mapping and known gaps

`helppc.py` recognizes an `@` title followed by `:` topic lines. Each key
becomes an index entry; database titles become Contents sections. A
single `.TXT` is exported as its own UHF bundle (`ASM.TXT` to `asm.json.gz`,
and likewise for the other five files). Each bundle assigns topic IDs in
source order. The reader indexes sibling HelpPC databases before rendering,
so a cross-database `~key~` becomes a `file=...` link to the correct bundle;
the six original files contain 1,006 topics in total.

Link lookup ignores letter case and compresses repeated spaces in both topic
keys and link labels, matching the original HelpPC key rule; the displayed
spelling and spacing are preserved.

Display lines retain their spacing and CP437 text. `%` and `^` become UHF
highlighted lines, and resolvable `~key~` references become topic links.
The current converter does **not** reproduce the original centering of
`^` lines. References to keys absent from the six available files remain
text rather than being given invented destinations. The original DOS
`HELPPC.NDX` binary is not parsed or regenerated.

The downloader selects only the six `.TXT` conversion inputs into
`sources/HelpPC 2.10/`. `HELPPC.DOC` and `HELPPC.NDX` remain in the original
downloaded archive; the converter does not use them. These sources are
excluded from the default public build pending a redistribution-rights review.
