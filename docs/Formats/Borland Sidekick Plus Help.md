# Borland Sidekick Plus Help

> Updated: 2026-10-11

Sidekick Plus `SKPLUS.HLP` is an uncompressed, paragraph-addressed collection
of screen groups. It is neither THELP nor the Sidekick 1 context stream.
The inspected original has 328,740 bytes and CRC32 `418860F6`.

## Header and group directory

The observed 16-byte header is:

```text
00 9B "Borland Help" 00 01
```

The initial word (`9B00h` here) is an opaque executable/HLP pairing tag, not
universal magic. The structural stamp is `"Borland Help" 00 01`; `01`
distinguishes this observed layout. Neither field is interpreted as a topic
count or a product release. Compatibility requires the matching executable's
pairing tag.
The signature is followed by a reserved 1,024-byte directory at `10h`.
Each directory entry is four bytes, little-endian:

| Field | Bytes | Meaning |
| --- | ---: | --- |
| paragraph | 2 | Absolute group address divided by 16 |
| group | 2 | Native group identifier; `FFFFh` can be a real group |

A paragraph of `FFFFh` ends the directory; the remaining reserved bytes are
not more entries. For example, `41 00 03 00` points to group `0003h` at `410h`,
and `89 06 1E 00` points to group `001Eh` at `6890h`.
Directory ordinal numbers and native group identifiers are different values.

## Group context directory

Each group begins with 256 six-byte descriptors. The context slot is its
ordinal byte index; no title matching is needed to identify a context.

| Field | Bytes | Meaning for a text descriptor |
| --- | ---: | --- |
| rows | 1 | Display-height bound |
| columns | 1 | Display-width bound |
| offset | 2 | Text record offset relative to this group's start |
| size | 2 | Complete text record length, including tables/title |

An `FFFFh` dimension word marks an unused slot, even if its remaining bytes
are not all `FF`; the observed unused descriptors are six `FF` bytes.
Text records start after the 1,536-byte
context directory. The first group/slot zero descriptor is
`11 3A 00 06 2A 02`: 17 rows, 58 columns, offset `600h`, length `22Ah`.
Its actual record starts at `A10h`, not at absolute `600h`.

Records need not follow context-slot order. Identical `(offset, size)` pairs
are real shared-record contexts, not two copies of the text. Native paragraph
alignment leaves up to 15 opaque bytes between groups; observed padding can
contain stale text fragments and is not an article.

Three zero-height descriptors in group `0104h` are special, not text offsets:
slots 23, 146, 149 contain respectively `00 FF 80 FF FF FF`,
`00 FF 81 FF FF FF`, `00 FF 82 FF FF FF`. They are redirects: an offset whose
high byte is `FF` selects the runtime's default paragraph and the low-byte
context slot. Their observed targets are Services slots 128, 129, 130. Height
zero is incidental; the native branch tests the offset byte after the unused
dimension check. Do not treat `FF80h` as a text offset or use titles to choose
a replacement. Cyclic redirects would loop in the native reader.

## Text record, pages and hotspots

```text
hotspot triples...
FF FF FF                       end of hotspot table
display bytes [FF FF display bytes]...
00                             end of display bytes
caption
00                             end of record
```

Each three-byte hotspot table entry contains:

| Byte | Meaning |
| --- | --- |
| 0 | One-based page containing the hotspot |
| 1 | Zero: runtime's common/default group; any nonzero value: current group |
| 2 | Target context slot in that group |

Entries match `05` runs in display order on the indicated page. For example,
the first Services screen starts with `01 FF 83`: its first page's first
hotspot points to current group `0003h`, slot 131, “Edit Clipboard”. In the
Notepad index, `03 00 81` refers from page 3 to the common group (Services in
this distribution), slot 129, “Options File Defaults”. It is not a group
directory ordinal. The corpus has 46 zero-scope and 2,005 `FF`-scope links.
The common-group paragraph is runtime state, not an explicit HLP header field.

The corpus has 79 additional pages in distinct records. `FF FF` is their
boundary; `03` is a style selector here, unlike Sidekick 1's page separator.
The native executable supplies PgUp/PgDn controls outside this text stream.

## Display stream

| Bytes | Observed category/operation |
| --- | --- |
| `01` | Ordinary text category |
| `02` | Emphasis category |
| `03` | Key-label category |
| `04` | Selected-keyword category; the Help runtime substitutes this for the focused `05` |
| `05` | Begin the next hotspot from the table |
| `06` | Toggle `01`/`02` or `03`/`04`; leave `05` unchanged |
| `0D` | New display row, from the left column |
| `FF xx` | Literal OEM/VGA character `xx`, except structural `FF FF` |

Category selectors replace each other. The generic native string printer
can retain them across a CR, but the **Help module calls it separately for
every row**, starting with the help window's ordinary category. There is no
implicit style carry into the next help row or page. Hotspot labels end at
the next category selector or the row/string boundary.
A caption is separate metadata, not a final
display row. Raw escapes include low-byte arrows and bullets; escaped TAB is
the circle glyph, not eight-column indentation. CP437 box-drawing characters
and authored spaces supply the in-text diagrams; there is no HTML table.

One bare `0F` occurs before `.. *****...` in group `012Dh`, slot 29. The native
printer emits it as a VGA glyph, as it does other unescaped low bytes apart
from category controls, NUL and CR. It is not a comment instruction. Raw TAB
and LF likewise display OEM glyphs rather than performing cursor movement.
Unescaped `FE` is different: it reads a two-byte runtime-string reference and
recursively prints text from the application. No such reference occurs in this
HLP's display pages. Its destination text requires the application's string
table; the two reference bytes are not character data.
Exact attribute colors and the initial attribute come from the executable,
not an embedded HLP palette. There is no stored RGB palette.

## Decoding boundaries and external state

Locate a descriptor at `group_start + slot*6`. Test the `FFFFh` dimension
sentinel before interpreting offsets. Resolve `FFxxh` redirects through the
runtime's default paragraph, not as text offsets; detect redirect cycles.

For text descriptors, `offset + size` bounds the complete record, including
hotspots, display bytes and caption. The hotspot page number and display order
determine its label. Truncated escapes and missing terminators are malformed
records, not ordinary shorter text.

Default paragraph, runtime-string table, category colors and executable/HLP
pairing are application state, not additional HLP header fields.

In the inspected original, targets `0003h:90`, `0017h:4`, `0104h:86`,
`0114h:166`, `0020h:3` and `0020h:50` have unused descriptors. These are
missing help, not neighboring contexts. Redirect `0104h:146` selects slot
129 in the runtime's default paragraph.
