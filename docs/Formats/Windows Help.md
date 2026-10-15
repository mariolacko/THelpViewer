# Windows Help Container and HC31 Topic Records

Windows Help `.HLP` uses a compound internal-file container beginning with
`3F 5F 03 00`. It is not Microsoft DOS QuickHelp (`LN`), CodeView (`BW03`),
Borland THELP or a standalone Borland `.HLX` keyword tree.

This specification describes the container, page trees, HC31 old-style
compression, native articles, paragraph/character commands and addressing. The verified
topic profile has `SYSTEM.Minor = 21`, with compression flags `0` or `4`.
The documented flag-`8` geometry has not been verified against an original
here. HC30 topic links, Hall phrase tables, MediaView extensions and the
extended FONT and bitmap/metafile pixel grammar are outside the verified profile;
do not apply HC31 rules to them silently.

All integers are little-endian. Offsets have several distinct bases, stated
below. `LE16` and `LE32` denote unsigned two- and four-byte fields. Bytes in
strings are not UTF-8. English Windows ANSI text uses Windows-1252; other
languages and font-selected character sets need their own binding.

## 1. Outer container

The file begins with a 16-byte header:

| File offset | Size | Field | Meaning |
| --- | ---: | --- | --- |
| `00h` | 4 | Magic | LE32 `00035F3Fh` |
| `04h` | 4 | DirectoryStart | Absolute offset of the directory's internal-file header |
| `08h` | 4 | FirstFreeBlock | Absolute offset of the free list, or `FFFFFFFFh` |
| `0Ch` | 4 | EntireFileSize | Complete file length, including this header |

Each internal file, including the directory, starts with a nine-byte header:

| Relative offset | Size | Field | Meaning |
| --- | ---: | --- | --- |
| `00h` | 4 | ReservedSpace | Allocation length, **including** this nine-byte header |
| `04h` | 4 | UsedSpace | Payload length, **excluding** the header |
| `08h` | 1 | FileFlags | Allocation flags; normally `04h`, other bits not specified here |
| `09h` | UsedSpace | Payload | Only these bytes belong to the internal file |
| `09h + UsedSpace` | remainder | Unused allocation | Not another stream or live record |

Require `ReservedSpace >= 9 + UsedSpace` and the complete allocation to fit
inside `EntireFileSize`. Stream allocations, the outer header, directory
allocation and free-list allocations must not overlap.

A free block contains LE32 `FreeSpace` at offset 0 and LE32
`NextFreeBlock` at offset 4. `FreeSpace` includes this eight-byte header;
`NextFreeBlock = FFFFFFFFh` terminates the list. Bound every block and reject
cycles. Free bytes can contain old strings or records; they are not live data.

## 2. Internal directory and shared B+ trees

The directory payload is a B+ tree. Its leaf keys are NUL-terminated internal
filenames such as `|SYSTEM`, `|TOPIC`, `|Phrases`, `|KWBTREE` and `|KWDATA`.
Its LE32 values address the **nine-byte headers**, relative to the outer
file's beginning. The pipe is a literal filename byte, not a separator.

Every tree payload starts with the following 38-byte header:

| Payload offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | Magic: `293Bh` |
| `02h` | 2 | Flags: `0002h` set; `0400h` denotes a directory |
| `04h` | 2 | PageSize in bytes |
| `06h` | 16 | NUL-terminated Structure descriptor; bytes after NUL are unused |
| `16h` | 2 | ReservedZero: `0000h` |
| `18h` | 2 | PageSplits |
| `1Ah` | 2 | RootPage, zero-based |
| `1Ch` | 2 | ReservedMinusOne: `FFFFh` |
| `1Eh` | 2 | TotalPages |
| `20h` | 2 | Levels, including the leaf level |
| `22h` | 4 | TotalEntries, counting leaf records only |
| `26h` | variable | Fixed-size pages |

Payload size is `38 + TotalPages * PageSize`; page `p` starts at
`38 + p * PageSize`. Typical directory pages are 1,024 bytes; keyword trees
commonly use 2,048. Page size is not a string-pool address. Other flags,
including `2000h`, have no established meaning in this specification.

The descriptor concatenates key and leaf-value types:

| Descriptor | Leaf record |
| --- | --- |
| `z4` / `F4` | NUL string filename, LE32 outer file offset |
| `i24` | NUL string keyword, LE16 occurrence count, LE32 keyword-data offset |
| `L4` | LE32 context hash, LE32 TOPICOFFSET |
| `Lz` | LE32 TOPICOFFSET, NUL string title |

`F` and `i` are indexed strings; `L` is an indexed four-byte key. The exact
locale comparison for every string variant is not specified here. Enumeration
can use stored routing order without inventing a character comparator.

All pages begin with LE16 `Unused` at offset 0 and LE16 `Entries` at offset 2.
The used-area end is `page_start + PageSize - Unused`. Read exactly `Entries`
records and finish at that end. Never read a NUL string past it. Unused tails
and unreachable allocated pages may contain plausible but obsolete records.

A branch header is six bytes: `Unused`, `Entries`, then LE16 `LeftChild`.
Each branch record contains the descriptor's **key only**, followed by LE16
`ChildPage`. There are `Entries + 1` children. Descend into the left child,
then the separator children in stored order, decreasing remaining depth.
Branch separators are routing copies, not extra leaf entries.

A leaf header is eight bytes: `Unused`, `Entries`, LE16 `PreviousLeaf`,
LE16 `NextLeaf`. `FFFFh` denotes a leaf-chain endpoint. Leaf records contain
all fields in the descriptor. Check that the chain agrees with tree order,
child/page references are bounded, no page is reused or cyclic, and the
reachable leaf-record total equals `TotalEntries`.

Standalone [Borland HLX](Borland%20HLX%20Binary.md) starts with this same
tree header but has no container or nine-byte allocation wrapper.

## 3. SYSTEM and version selection

The `|SYSTEM` payload begins with 12 bytes:

| Payload offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | Magic: `036Ch` |
| `02h` | 2 | Minor version: `21` for the verified HC31 profile |
| `04h` | 2 | Major version: `1` |
| `06h` | 4 | Generation timestamp; epoch/convention not established here |
| `0Ah` | 2 | Compression flags |

For `Minor > 16`, the remainder is a sequence of records: LE16 `RecordType`,
LE16 `DataSize`, then exactly `DataSize` bytes. Advance by `4 + DataSize`;
there is no inferred alignment. Keep unknown types bounded by their size.

Common records are type 1 (NUL title), 2 (NUL copyright), 3 (LE32 Contents
TOPICOFFSET), 4 (NUL startup macro), 5 (icon bytes) and 6 (window definition).
Icon/window substructures and other types are not specified here. Macros are
data for the native consumer, not instructions to execute on the host.

For `Minor <= 16`, the older header is followed directly by a NUL title;
do not parse it as the newer record sequence. Its topic addressing differs.

For HC31, flags select physical `|TOPIC` block geometry:

| Flags | Physical block size | Block payload |
| ---: | ---: | --- |
| `0` | 4,096 | Uncompressed |
| `4` | 4,096 | LZ77 |
| `8` | 2,048 | LZ77; documented but unverified here |

These are observed flag values, not permission to combine arbitrary bits.
Phrase compression is a separate layer, indicated by the phrase streams.

## 4. LZ77 and old-style phrases

LZ77 consists of mask groups. Read one mask byte, then process bits 0 through
7. A zero bit consumes one literal byte. A one bit consumes a LE16 token:

`distance = (token & 0FFFh) + 1`

`length = (token >> 12) + 3`

Copy `length` bytes from `output_cursor - distance`, one byte at a time.
Overlap is intentional: later copied bytes may refer to bytes just emitted.
There is no prefilled rotating SZDD dictionary. Reject a reference preceding
the output buffer or a used token missing an operand. A final mask need not
use all eight bits if the input has ended.

For topic blocks, cap expansion at 16,384 bytes. After reaching that limit,
remaining packed physical-block bytes are padding, not more topic content.
Phrase-table expansion instead must produce its exact declared length.

The HC31 `|Phrases` payload has this layout:

| Payload offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | NumPhrases |
| `02h` | 2 | Marker: `0100h` |
| `04h` | 4 | DecompressedSize |
| `08h` | `2 * (NumPhrases + 1)` | LE16 phrase offsets |
| following | remainder | LZ77 phrase bytes |

Offsets are relative to the **start of the offset table**, not the stream
or compressed bytes. Let `table_size = 2 * (NumPhrases + 1)`;
`phrase_start[i] = stored_offset[i] - table_size`. The first start is 0,
the final start equals `DecompressedSize`, and starts are nondecreasing.
Phrase `i` comprises decoded bytes `[start[i], start[i+1])`; it is not a
NUL-terminated string. Verify offsets and the final size before allocation.

The older `Minor <= 16` form omits `DecompressedSize`: offsets begin at 4,
and the following phrase bytes are plain. MediaView's additional-prefix
variant and Hall `|PhrIndex` / `|PhrImage` are not described by this layout.

To expand an old-style phrase-compressed text buffer, read its next byte `b`:

- `b = 0` or `b >= 16`: emit it literally.
- `1 <= b <= 15`: consume another byte `c`, compute
  `token = (b - 1) * 256 + c`, emit phrase `token // 2`, and append one
  ASCII space if `token` is odd.

Bound phrase indices and output length. The native HC31 consumer zero-fills
any remaining declared text-buffer space after expansion; these NULs are
not bytes to read from a neighboring record. For example `01 02` denotes
phrase 1, whereas `01 03` denotes phrase 1 followed by a space.

## 5. TOPIC physical blocks and TOPICPOS

Each physical `|TOPIC` block starts with 12 uncompressed bytes:

| Block offset | Size | Field |
| --- | ---: | --- |
| `00h` | 4 | LastTopicLink: TOPICPOS of the prior block's last link, or `FFFFFFFFh` |
| `04h` | 4 | FirstTopicLink: TOPICPOS of the first link starting in this block |
| `08h` | 4 | LastTopicHeader: TOPICPOS of the last article header, or `0` / `FFFFFFFFh` |
| `0Ch` | remainder | Plain or LZ77 bytes selected by SYSTEM |

The final physical block may be shorter. Bound it by the used `|TOPIC`
payload length, not the surrounding allocation. Decompress each block
independently, without carrying LZ history from another block.

For the verified HC31 profile, the logical TOPICPOS stride is **16,384**
even when flag 0 stores only a plain 4,084-byte block payload:

`block = (TOPICPOS - 12) // 16384`

`decoded_offset = (TOPICPOS - 12) % 16384`

Physical block start is `block * physical_block_size` in `|TOPIC`.
`TOPICPOS < 12` is invalid. Decoded offsets in a block's unused logical gap
are not valid pointers. Do not substitute 4,084 as HC31's logical stride.

A linked record can span blocks. After exhausting actual decoded bytes,
continue at byte 0 of the next decoded payload, skipping its physical
12-byte header and any logical gap. A read cursor exactly at the decoded
end normalizes to that next block; a pointer beyond the decoded end does not.
Keep the record's start address distinct from the continued read cursor.

HC30 uses a different address stride and relative link movement; the above
formulas are not a complete HC30 specification.

## 6. TOPICLINK and native article headers

At the first TOPICPOS (12), and subsequently at each absolute NextBlock,
read the 21-byte TOPICLINK:

| Record offset | Size | Field |
| --- | ---: | --- |
| `00h` | 4 | BlockSize: header + Data1 + packed Data2, excluding intervening physical headers |
| `04h` | 4 | DataLen2: decoded Data2 length |
| `08h` | 4 | PrevBlock: previous TOPICPOS; initially `FFFFFFFFh` |
| `0Ch` | 4 | NextBlock: next TOPICPOS |
| `10h` | 4 | DataLen1: **includes** the 21-byte TOPICLINK |
| `14h` | 1 | RecordType |
| `15h` | `DataLen1 - 21` | Data1: control/header bytes |
| following | `BlockSize - DataLen1` | Packed Data2 |

Require `21 <= DataLen1 <= BlockSize`. The formula is `DataLen1 - 21`,
not `DataLen1 - 11`. Check reciprocal PrevBlock and reject cycles. Following
links are absolute HC31 TOPICPOS values, not byte deltas or article numbers.
The final sentinel has NextBlock `0` or `FFFFFFFFh` and no usable content.

If `DataLen2 > packed_data2_size`, expand Data2 through old-style phrases.
Otherwise its first `DataLen2` bytes are plain; any remaining packed bytes
are unused but still included in the record's BlockSize.

RecordType `02h` begins an article. Its HC31 Data1 is exactly 28 bytes:

| Data1 offset | Size | Field |
| --- | ---: | --- |
| `00h` | 4 | ArticleBlockSize: native aggregate article size |
| `04h` | 4 | BrowseBack: TOPICOFFSET of previous browse destination, or `FFFFFFFFh` |
| `08h` | 4 | BrowseForward: TOPICOFFSET of next browse destination, or `FFFFFFFFh` |
| `0Ch` | 4 | TopicNum: native article number, independent of context hash |
| `10h` | 4 | NonScroll: TOPICPOS of non-scrolling region, or `FFFFFFFFh` |
| `14h` | 4 | Scroll: TOPICPOS of scrolling region |
| `18h` | 4 | NextTopic: TOPICPOS of the following article header |

The exact accounting rules for ArticleBlockSize are not established here;
it is not a substitute for following TOPICLINK. NextTopic agrees with the
next type-2 header in link traversal. Data2 contains the article title and
then optional macro strings, separated by NUL. An empty title is valid.
The declared buffer end also terminates the last string: a stored final
NUL is not mandatory. Do not consume a byte from the following record.

RecordType `20h` is a display record and `23h` is a table record. The common
Data1 prefix is a compressed signed TopicSize, followed by a compressed
unsigned TopicLength. For the addressing operation, TopicSize's value is
not needed, but its encoded width must be consumed correctly:

- Read LE16 `w`. If bit 0 is zero, width is two bytes and signed value is
  `(w >> 1) - 16384`.
- Otherwise consume LE16 `v`: width is four bytes and signed value is
  `(w >> 1) + 32768 * v - 1073741824`.
- Read TopicLength byte `b`. If bit 0 is zero, length is `b >> 1` and width
  is one byte. Otherwise consume byte `c`; length is `(b >> 1) + 128 * c`
  and width is two bytes.

The remaining Data1 follows the conditional grammar in section 8. Data2 is
its text/string data, **not** a ready-to-display article. NULs and picture
hotspot counts participate in native cursor addressing; stripping NULs or
scanning printable runs cannot preserve table cells or links. Other record
types must not silently be treated as these two types.

## 7. TOPICOFFSET, keyword and context lookup

TOPICOFFSET is a character/hotspot cursor address, not TOPICPOS:

`block = TOPICOFFSET // 32768`

`character = TOPICOFFSET % 32768`

For each block, follow records beginning with its FirstTopicLink. Accumulate
TopicLength for every `20h` / `23h` record starting there. A record occupies
`[accumulated, accumulated + TopicLength)` in that block's cursor space.
The owning article is the last preceding type-2 header, which may be in an
earlier physical block; LastTopicHeader helps locate it. A record crossing
a physical block boundary remains addressed in its **starting** block.

Resolution succeeds only inside a declared interval. Gaps, macro sentinels
and offsets at an interval's exclusive end are not nearest-article links.
Cursor positions count text including NULs and hotspots in pictures, so
TopicLength is not necessarily `len(decoded_Data2)` or visible string length.
Locating the exact displayed cursor within a record additionally requires
the visual instruction grammar, not just the interval lookup.

`|KWBTREE` uses `i24`. Each leaf's Count and KWDataOffset select Count LE32
TOPICOFFSETs in the **payload** of `|KWDATA`:

`KWDataOffset + 4 * Count <= KWDATA.UsedSpace`

The allocation header is not part of that base. These are not HLX file
offsets, keyword ordinals or context numbers. `FFFFFFFFh` can denote a
macro keyword in later variants; macro storage is outside this profile.
When binding a standalone HLX, compare its live key/count/offset tuples to
the containing HLP's KWBTREE. Equal filenames or similar keyword sets are
not enough to establish a matching revision.

`|CONTEXT` uses `L4`: LE32 context hash to TOPICOFFSET. `|TTLBTREE` uses
`Lz`: TOPICOFFSET to NUL title. Neither tree converts TOPICOFFSET into an
article number by itself. Native TopicNum, context hash, physical record
position and keyword ordinal are different identities.
Different hashes may address different cursor positions inside the same
article. Preserve the selected record and its within-record cursor after the
hash lookup, including for an external-file jump; the article's first record
is not a substitute for that cursor.

For the HC31 legal ASCII context alphabet, initialize a 32-bit hash to 0
and for each byte compute `hash = (hash * 43 + value) mod 2^32`. Values are
1–9 for digits `1`–`9`, 10 for `0`, 12 for `.`, 13 for `_`, and 17–42 for
`A`–`Z` or `a`–`z`. Empty-name hash is the special value 1. Later compilers'
extended alphabet and locale behavior are not specified here.

## 8. Paragraph, table and character grammar

### 8.1 Packed integers

The low bit selects encoded width; all multi-byte operands are little-endian.
Read only the selected width, then apply the signed bias if applicable:

| Type | Low bit clear | Low bit set |
| --- | --- | --- |
| Unsigned short | byte `b`: `b >> 1` | LE16 `w`: `w >> 1` |
| Signed short | `(b >> 1) - 64` | `(w >> 1) - 16384` |
| Unsigned long | LE16 `w`: `w >> 1` | LE32 `d`: `d >> 1` |
| Signed long | `(w >> 1) - 16384` | `(d >> 1) - 1073741824` |

Thus `80` is signed short 0; `01 80` is wide signed short 0; `00 80` is
signed long 0; `01 80 00 80` is wide signed long 16,384. The four-byte
long bias is `40000000h`, **not** `04000000h` in some older descriptions.
The unsigned forms do not subtract a bias.

### 8.2 Table prefix and paragraphs

After TopicSize and TopicLength, a type-`20h` record immediately contains one
ParagraphInfo followed by its character stream. Its character stream may
contain several `82h` paragraph endings using that same ParagraphInfo.

For type `23h`, first read this table prefix:

| Relative to table prefix | Size | Field |
| --- | ---: | --- |
| `00h` | 1 | NumberOfColumns; nonzero |
| `01h` | 1 | TableType: `0` or `2` variable width; `1` or `3` ordinary |
| following, only type `0`/`2` | 2 | Signed MinTableWidth |
| following | `4 * NumberOfColumns` | Column descriptors |

Each descriptor is signed LE16 **ColWidth, then GapWidth**. The executable
native consumers use this order despite reversed fields in older prose:
a one-column table's first word is its right cell boundary and the second
its left margin. In variable-width tables these are relative values, with
their total documented as 32,767. Scale the boundary metrics by
`MinTableWidth / 32767`; ordinary tables use factor 1. Exact pixel rounding
and every special table subtype's behavior are not specified here. Metrics depend on the
FONT variant (old half-points versus later twips); do not apply one pixel or
character scale to all variants.

One table record supplies a row, with one or more paragraphs in each cell.
Then repeat cell paragraphs in stored order:

1. Read a signed LE16 column index. `FFFFh` ends the table and has **no**
   following fields. Otherwise require `0 <= column < NumberOfColumns`.
2. Read two opaque bytes and one biased byte, normally `80h`. Their semantic
   purpose is unknown; they belong to the cell header, not its text.
3. Read ParagraphInfo and its complete character stream, including `FFh`.
4. Return to step 1. A column may have several stored paragraphs; do not
   infer a new row from a repeated column, caption, rule or printable label.

ParagraphInfo starts with four opaque bytes: one byte, one biased byte
(normally `80h`), then LE16 identifier. Their full semantics are unknown.
Next read LE16 Flags and its operands **in this order**:

| Flag | Conditional operand / meaning |
| --- | --- |
| `0001h` | Packed signed long; meaning unknown |
| `0002h` | Packed signed short SpacingAbove |
| `0004h` | Packed signed short SpacingBelow |
| `0008h` | Packed signed short SpacingLines |
| `0010h` | Packed signed short LeftIndent |
| `0020h` | Packed signed short RightIndent |
| `0040h` | Packed signed short FirstLineIndent, relative to LeftIndent |
| `0080h` | Unknown flag; no established extra operand |
| `0100h` | Border flags byte, then signed LE16 BorderWidth |
| `0200h` | Tab-stop structure below |
| `0400h` | Right-aligned paragraph; no extra operand |
| `0800h` | Center-aligned paragraph; no extra operand |
| `1000h` | Keep paragraph lines together; no extra operand |
| `2000h`, `4000h`, `8000h` | Unknown flags; no established extra operands |

Border bits are `01h` box, `02h` top, `04h` left, `08h` bottom, `10h` right,
`20h` thick and `40h` double. Bit `80h` is unknown. BorderWidth's unit and
exact rendering behavior are not independently specified here.

For tabs, read packed **signed** short NumberOfTabStops and require it to be
nonnegative. Each stop is a packed unsigned short: the lower 14 bits give
the position. If bit `4000h` is set, a packed unsigned short modifier follows:
`1` right-aligned or `2` centered. An unflagged stop is left-aligned.
Bits without a stated meaning must not be used to infer more operands.

### 8.3 Interleaved character commands

Maintain independent cursors into decoded Data1 and Data2. For every command:
first consume the next **NUL-terminated Data2 string**, even if empty, and
display it with the current font/hotspot state; then consume the next Data1
opcode and its complete operand. The opcode changes state for the following
string. Empty strings are necessary for adjacent font/link/picture changes.
The `FFh` opcode also consumes a preceding string.

| Opcode | Following Data1 bytes | Operation |
| --- | --- | --- |
| `20h` | LE32 field number | Native `vfld` field |
| `21h` | LE16 field type | Native `dtype` field |
| `80h` | LE16 descriptor index | Select a `\|FONT` descriptor |
| `81h` | none | Hard line break; do not reapply first-line indent |
| `82h` | none | End paragraph; next paragraph reuses ParagraphInfo |
| `83h` | none | Move to next tab stop |
| `86h`, `87h`, `88h` | Object structure below | Inline, left or right object respectively |
| `89h` | none | End hotspot |
| `8Bh` | none | Nonbreaking space, absent from Data2 itself |
| `8Ch` | none | Nonbreaking hyphen; the actual hyphen is already in Data2 |
| `C8h`, `CCh` | LE16 Length, then Length bytes | Macro hotspot; normal / without font change |
| `E2h`, `E3h` | LE32 **context hash** | Popup / jump in HC31 |
| `E6h`, `E7h` | LE32 **context hash** | Popup / jump without font change |
| `EAh`, `EBh` | External hotspot below | Popup / jump |
| `EEh`, `EFh` | External hotspot below | Popup / jump without font change |
| `FFh` | none | End character stream; next cell for type `23h`, otherwise end record |

The macro Length counts **all following payload bytes**, not `Length - 3`.
Payloads can include a terminal NUL; a NUL inside a macro string is not a
separator to another opcode. Native macros use quoted strings such as
`JumpID("OWL.HLP","context")` or backtick/apostrophe quoting
``JI(`OWL.HLP',`context')``; nested quoted macro strings may appear as
arguments. Multiple calls and OS/UI commands belong to the native macro
language, not a host-language expression or JavaScript.

HC30 also has `E0h`/`E1h` with a four-byte native destination, but its complete
addressing is not covered by this HC31 profile. Do not treat an HC31 hash
as a TOPICOFFSET, TOPICPOS or article number. Resolve it through `|CONTEXT`,
then use the bounded TOPICOFFSET resolution in section 7.

External hotspots start with LE16 Size, then exactly Size payload bytes:

| Payload offset | Size | Field |
| --- | ---: | --- |
| `00h` | 1 | Subtype: `0`, `1`, `4` or `6` |
| `01h` | 4 | Context hash |
| `05h`, subtype `1` | 1 | Window number |
| `05h`, subtype `4` | variable | NUL external filename |
| `05h`, subtype `6` | variable | NUL secondary **window name**, then NUL external filename |

Subtype `0` has no further bytes. Subtype `1` uses the current file; types
`4`/`6` name the external file. The subtype-6 string order is window first,
file second. Keep filenames as native identities; do not guess another
destination from a similar name or erase a missing-file link.

### 8.4 Object boundaries

Opcodes `86h`/`87h`/`88h` are followed by an ObjectType byte and a packed
signed long PictureSize. Reject a negative size. If ObjectType is `22h`,
read a packed unsigned short NumberOfHotspots next. Then read **exactly
PictureSize bytes** of object payload; the hotspot-count operand is outside
that size. Hotspots add cursor positions even without visible text bytes.

For picture types `03h` and `22h`, the payload begins with LE16 Embedded:

- `0`: the next LE16 is PictureNumber, selecting an internal bitmap resource.
- `1`: embedded SHG/MRB picture bytes immediately follow the two-byte flag;
  there is **no** extra PictureNumber before the embedded picture header.

For object type `05h`, six initial opaque bytes precede a NUL string. Known
string families are `DLLName,WindowClass,Param`, `!Label,Macro` for a native
button, and an MCI media specification. Their Windows execution and pixel
formats are not implied by the outer PictureSize grammar.

All strings and operands must end inside their own record/payload. After a
display stream, or the `FFFFh` cell sentinel, Data1 must be exhausted.
Trailing decoded Data2 bytes may be zero padding from phrase expansion;
nonzero unconsumed bytes require another proven grammar, not a guessed text
fragment. Unknown opcodes cannot be skipped without a verified operand size.

## 9. Old FONT descriptors and text encoding

The old `|FONT` stream starts with this eight-byte header:

| Payload offset | Size | Field |
| --- | ---: | --- |
| `00h` | 2 | NumFaces |
| `02h` | 2 | NumDescriptors |
| `04h` | 2 | FacenamesOffset; `8` in this profile |
| `06h` | 2 | DescriptorsOffset, relative to payload start |

Face slots are fixed width:
`(DescriptorsOffset - FacenamesOffset) / NumFaces`, which must be a positive
integer. A slot is a byte string ending at its first NUL or its slot boundary.
Do not read a face name into the next slot. Extended headers with another
FacenamesOffset have different descriptor/charset structures.

Every old descriptor is exactly **11 bytes**:

| Descriptor offset | Size | Field |
| --- | ---: | --- |
| `00h` | 1 | Attributes: `01h` bold, `02h` italic, `04h` underline, `08h` strikeout, `10h` double underline, `20h` small capitals |
| `01h` | 1 | FontSize in half-points |
| `02h` | 1 | Family: `1` modern, `2` roman, `3` swiss, `4` script, `5` decorative |
| `03h` | 2 | Zero-based face-slot index |
| `05h` | 3 | Foreground red, green, blue bytes |
| `08h` | 3 | Background red, green, blue bytes; original consumers may ignore them |

Require the face index to be below NumFaces. Do not assume an 8-bit index,
replace RGB triples with a DOS palette index or read a charset byte from an
old descriptor that has none. The descriptor end is
`DescriptorsOffset + 11 * NumDescriptors`.

Ordinary text uses its Windows ANSI code page. The `Symbol` face instead
selects Standard Symbol encoding: for example `41h` = Greek alpha capital,
`62h` = Greek beta small, `B7h` = bullet, `BEh` = horizontal arrow extender,
and `E6h` = left-parenthesis top piece. The byte `94h` has no assigned
Standard Symbol glyph; it must not silently become Windows-1252's quote.
Font selection changes glyph interpretation without changing byte-based
TOPICOFFSET counts. A full encoding table is available in the primary
[StandardSymbolsPS AFM](https://github.com/ArtifexSoftware/urw-base35-fonts/blob/master/fonts/StandardSymbolsPS.afm),
with Unicode names in the [Adobe Glyph List](https://github.com/adobe-type-tools/agl-aglfn/blob/master/glyphlist.txt).
Some construction glyphs have font-specific private-use names; Unicode
assembly-piece equivalents require an explicit transcription policy.

## 10. Concrete byte examples

One 44,393-byte `OPENHELP.HLP` has this outer header:

```text
3F 5F 03 00 35 08 00 00 FF FF FF FF 69 AD 00 00
```

DirectoryStart is `0835h`, there is no free list, and EntireFileSize is
`AD69h`. Its SYSTEM header is:

```text
6C 03 15 00 01 00 06 E5 B6 2E 04 00
```

It selects Minor 21, Major 1 and flag 4 (4,096-byte physical LZ77 blocks).
The first TOPIC block header is:

```text
FF FF FF FF 0C 00 00 00 00 00 00 00
```

The first type-2 record at TOPICPOS 12 has this decoded Data1:

```text
DC 03 00 00 FF FF FF FF 89 03 00 00 00 00 00 00
48 00 00 00 87 00 00 00 32 04 00 00
```

Its native TopicNum is 0, NonScroll is 72, Scroll is 135 and NextTopic is
1,074. The stored title bytes spell `Using Help in Borland C++` and end at
the declared Data2 length, without a final stored NUL.

The following type-20 record starts at TOPICPOS 72. Its Data1 begins
`30 80 3C`: TopicSize consumes two bytes, and TopicLength is 30 because
`3Ch >> 1 = 30`. The next type-20 record at TOPICPOS 135 begins
`20 80 74`: TopicLength is 58. Their cursor intervals in block 0 are
`[0, 30)` and `[30, 88)`. A TOPICOFFSET of 31 selects the second record,
character 1 within it; it is not TOPICPOS 31 or native article 31.

## 11. References and remaining unknown structures

The wider family is described in the primary
[HelpDeco format description](https://github.com/pmachapman/helpdeco/blob/master/helpfile.txt)
and its [decoder sources](https://github.com/pmachapman/helpdeco/tree/master/src).
The independently implemented [Wine WinHelp reader](https://github.com/wine-mirror/wine/blob/master/programs/winhlp32/hlpfile.c)
also defines native context-hash hotspots and external window/file order.
The HC31 plain-block logical stride and 21-byte TOPICLINK accounting above
must not be replaced by inconsistent formulas in older prose descriptions.

The following require separate field-by-field specifications before complete
visual decoding: extended FONT/charset records, proportional glyph/pixel
metrics, SHG/MRB bitmap/metafile internals and image-region hotspots, complete
Windows macro/UI semantics, Hall phrases and HC30 topic movement.
Unspecified fields must remain bounded opaque bytes rather than inferred
from printable strings, nearby pointer values or one specimen's filename.
