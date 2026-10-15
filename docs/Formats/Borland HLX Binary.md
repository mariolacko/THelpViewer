# Borland Compiled HLX Keyword Index

Compiled Borland Windows Help `.HLX` files with structure `i24` are
standalone keyword B+ trees. They contain keywords, occurrence counts and
addresses into a companion Windows Help keyword-data stream. They do not
contain the article text addressed by that stream.

This is unrelated to semicolon-directive `.hlx` source text. A complete
Windows `.HLP` container also has a different outer signature, `3F 5F 03 00`.
An HLX tree starts directly with its B+ tree header; there is no preceding
nine-byte internal-file wrapper.

All numeric fields below are little-endian. Page numbers are zero-based;
`FFFFh` means no page where a chain endpoint permits it.

## 1. File header

The fixed header is 38 bytes. It is followed by `TotalPages` fixed-size
pages. A standalone file's length is exactly:

`38 + TotalPages * PageSize`

| Absolute offset | Size | Field | Interpretation |
| --- | ---: | --- | --- |
| `00h` | 2 | Magic | LE16 `293Bh` |
| `02h` | 2 | Flags | Bit `0002h` is set; retain other bits |
| `04h` | 2 | PageSize | Page size in bytes, not a string-pool offset |
| `06h` | 16 | Structure | NUL-terminated descriptor `i24`; bytes after its NUL are unused |
| `16h` | 2 | ReservedZero | `0000h` |
| `18h` | 2 | PageSplits | Page-split count |
| `1Ah` | 2 | RootPage | Page containing the root of the tree |
| `1Ch` | 2 | ReservedMinusOne | `FFFFh` |
| `1Eh` | 2 | TotalPages | Number of allocated pages |
| `20h` | 2 | Levels | Root-to-leaf depth, counting the leaf level |
| `22h` | 4 | TotalEntries | Total number of keyword records in the leaves |
| `26h` | variable | Pages | `TotalPages` pages of `PageSize` bytes |

The `i24` descriptor denotes a NUL-terminated indexed string, a two-byte
value and a four-byte value. It describes leaf records, not branch records.

The inspected trees use `PageSize = 0800h` (2,048 bytes) and one or two
levels. Other page sizes are not ruled out by the addressing scheme.
`Levels = 1` means the root itself is a leaf. Page type is determined by
its depth; no separate page-type byte is stored.

The precise meaning of additional flags is not established here.
`WIN31WH.HLX` has `2002h` instead of `0002h` while retaining the same
record grammar. Header descriptor padding is not guaranteed to be zero:
it can contain old RTF paths, labels or arbitrary bytes. Such padding is
not a table or an external resource declaration.

## 2. Page addressing and used area

For page number `p`:

`page_start = 38 + p * PageSize`

Every page starts with:

| Page-relative offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | Unused: number of free bytes at the end of the page |
| `02h` | 2 | Entries: number of records on this page |

The used area ends at `page_start + PageSize - Unused`. Read exactly
`Entries` records, and verify that the cursor reaches this boundary.
The unused tail can contain remnants of older records and is not necessarily
zero-filled. A string found there is not an additional keyword or article.

Records do not cross page boundaries. A missing NUL or operand before the
used-area end is malformed; do not continue searching in free bytes or the
following page.

## 3. Branch pages

A branch page has a six-byte header:

| Page-relative offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | Unused |
| `02h` | 2 | Entries |
| `04h` | 2 | LeftChild: child preceding the first separator |

Starting at `06h`, each separator record is:

| Field | Size | Meaning |
| --- | ---: | --- |
| Separator | variable | NUL-terminated keyword |
| Child | 2 | Page number for this separator's subtree |

There are `Entries + 1` child pointers. The left child handles keys
before the first separator; each remaining child handles keys from its
separator up to the next. Each descent reduces the remaining level count
by one. Separators are routing copies, not additional keyword entries.

Enumeration visits the left child, then separator children in stored order.
Do not reconstruct this order using file offsets or sorting the numeric
keyword-data addresses. Character-set and locale collation are not encoded
fully in this header; portable enumeration needs no guessed comparator.

## 4. Leaf pages

A leaf has an eight-byte header:

| Page-relative offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | Unused |
| `02h` | 2 | Entries |
| `04h` | 2 | PreviousLeaf, or `FFFFh` for the first leaf |
| `06h` | 2 | NextLeaf, or `FFFFh` for the last leaf |

Starting at `08h`, every keyword record is:

| Field | Size | Meaning |
| --- | ---: | --- |
| Keyword | variable | NUL-terminated byte string |
| Count | 2 | Number of referenced positions for this keyword |
| KWDataOffset | 4 | Byte offset in the companion keyword-data stream |

`Count` is not a style flag or a navigation opcode.
`KWDataOffset` is not an offset into the HLX tree and is not a topic ID.
Do not clamp it to the HLX file size or add `PageSize` to it.

The double-linked leaf chain follows the same order as branch traversal.
Its endpoints are `FFFFh`; check reciprocity, valid page numbers and
absence of loops. The sum of leaf record counts must equal `TotalEntries`.
The same count/address tuple can occur under multiple keywords. A shorter
keyword which happens to be a suffix of another is not a damaged fragment.

An alternate enumeration descends through left children to the first leaf
and follows `NextLeaf`. Validate the branch structure as well if
corruption detection is required. Never interpret unreachable allocated
pages as live records merely because they contain printable strings.

## 5. Resolving keyword addresses

The layout matches the Windows Help `|KWBTREE` keyword tree. Its associated
`|KWDATA` stream is an array of four-byte TOPICOFFSET cursor addresses.
To resolve one record, read:

`Count` LE32 values from `KWDataOffset` in the keyword-data payload.

Offsets are relative to the payload, excluding its nine-byte internal-file
header in the containing Windows Help file. Require
`KWDataOffset + 4 * Count <= keyword_data_payload_size`.
Adjacent records often satisfy
`next.KWDataOffset = current.KWDataOffset + 4 * current.Count`, because
their lists are stored consecutively. Shared/reused lists are not ruled out;
this relationship is not a required HLX record-boundary rule.

These values address the Windows Help topic system, whose interpretation
depends on the parent help version. They are not the ordinal numbers of
HLX keywords. In Windows Help variants with macro keywords, `FFFFFFFFh`
is a macro reference rather than an article address.
For HC31, TOPICOFFSET's high 17 bits select a physical topic block and its
low 15 bits select a character/hotspot position accumulated from native
display-record lengths. It is distinct from the 16-KiB-stride TOPICPOS
record address. See [Windows Help](Windows%20Help.md) for the container,
compression and bounded record-span resolution; do not interpret either
address as a raw HLP file byte offset.

Without that companion data, the destination list cannot be recovered.
The tree header stores no companion filename. Binding a particular tree
to a particular help file must be verified separately. RTF filenames in
unused bytes do not supply this binding or the missing article text.

## 6. Strings, encoding and controls

Keywords are byte strings, not compressed paragraphs. No article codec,
screen layout or inline hotspot opcode stream is present in this grammar.
Preserve complete strings, including punctuation, one-character keywords,
spaces, numeric terms and control bytes; there is no 128-byte label limit.

The tree has no explicit character-set field. English Borland Windows
keywords use Windows ANSI; `A0h` in the OLE keyword
`Windows A0 NT?` is a nonbreaking space under Windows-1252, not the
DOS CP437 letter á. Other language/code-page bindings require separate
evidence from the companion help or its environment. C0 bytes are not
automatically DOS display glyphs or hyperlinks. For example, OLE keys
containing a Word field-code fragment have a literal `15h` inside
the NUL-terminated keyword; the rest of that key remains in the same record.

## 7. Byte examples

`OPENHELP.HLX` is 2,086 bytes: a 38-byte header and one 2,048-byte leaf.
Its root is page 0, depth 1, with 36 keywords.

At file offset `26h` its leaf header is:

```text
8E 04 24 00 FF FF FF FF
```

This means 1,166 unused bytes, 36 records, no previous leaf and no next leaf.
Records occupy file offsets `2Eh..397h`; the used-area end is `398h`.

The first keyword starts at `2Eh`:

```text
61 64 64 69 6E 67 20 68 65 6C 70 20 66 69 6C 65 73
20 74 6F 20 4F 70 65 6E 48 65 6C 70 00 01 00 00 00 00 00
```

It spells `adding help files to OpenHelp`, has Count 1 and KWDataOffset 0.
The following record begins at `52h`, spells
`adding help files to search ranges`, has Count 1 and KWDataOffset 4.
The four-byte values 0 and 4 select keyword-data cells, not local topics.

For larger examples, `BCW.HLX` declares 22 pages, root page 21,
depth 2 and 2,322 keyword records; the root contains only separator keys.
Its first leaf record is at `2Eh`, far before file offset `0800h`.

## 8. Reference implementations

The B+ tree layout and companion keyword-data interpretation can also be
checked against the independently maintained
[HelpDeco format description](https://github.com/pmachapman/helpdeco/blob/master/helpfile.txt)
and Wine's
[B+ tree traversal](https://github.com/wine-mirror/wine/blob/master/programs/winhlp32/hlpfile.c)
and [keyword lookup](https://github.com/wine-mirror/wine/blob/master/programs/winhlp32/winhelp.c).
Other tree descriptors and undocumented flag meanings are outside this
index specification. Container/article addressing and compression are
described separately in [Windows Help](Windows%20Help.md).
