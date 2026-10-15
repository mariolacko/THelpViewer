# Borland Turbo Debugger/Profiler Runtime Help

File extensions: `.TDH`, `.TFH`. These are separate from Borland THELP,
TPH/TCH and Turbo Vision FBHF. There is no ASCII magic or stored product,
language, character-set or decoder-profile identifier.

## 1. Integer and offset conventions

- `u16be(p) = (file[p] << 8) | file[p+1]`.
- A signed map value is `s16(x) = x` for `x < 8000h`, otherwise `x - 10000h`.
- File offsets are zero-based absolute byte offsets.
- Context numbers are zero-based map indices, not byte offsets.
- Cumulative offsets require at least a signed 32-bit accumulator; do not
  wrap them modulo 65536.

## 2. File header and stored map

| Absolute offset | Size | Field | Meaning |
| --- | ---: | --- | --- |
| `0000h` | 2 | `N: u16be` | Number of stored delta WORDs |
| `0002h + 2*i` | 2 | `map[i]: s16be` | Delta used in cumulative addressing, for `0 <= i < N` |
| `B = 2 + 2*N` | 1 | slot-zero byte | Opaque byte; context 0 is not normal topic text |
| `B+1` | 2 | page 1 next-context | Context 1 begins here when `map[0] = 1` |
| `B+3` | variable | page 1 text | Nibble-coded text after its next-context WORD |

The WORD at `B` overlaps the slot-zero byte and the first byte of page 1's
next-context field. It is **not a separator signature**. Values such as
`0000h`, `0001h`, `2C00h`, `C101h` and `0901h` occur.

In the inspected files, `map[0] = 1` and page 1 contains the help index.
Its nonzero next-context WORD is followed by a run of `CCh` bytes, which
decode to spaces. These are structural recognition clues, not universal magic.
Odd `N` values are valid. Observed TFH maps have 363/366 stored WORDs;
TDH examples have 518, 537, 538, 596 and 728–817. A range chosen for detection
is not a stored field or a proof of the format.

## 3. Runtime map and context addressing

The original applications preload more map WORDs than the file header declares.
Those additional WORDs are read directly from the payload beginning at `B`;
there is no second table or decompression step.

| Application profile | Preloaded map WORDs | Stored-map example |
| --- | ---: | ---: |
| Turbo Debugger 1.0 | 530 | 518 |
| Turbo Debugger DOS 2.0 | 600 | 596 |
| Turbo Debugger DOS 4.0 | 790 | 728 |
| Turbo Debugger DOS 5.0 | 850 | 776 |
| Turbo Profiler 1.0 | 600 | 363 |

These counts belong to the application profile, not the file header. The
exact preload count for other application profiles is not established here.

For any addressed context `c`, including an overlapping map slot:

```text
delta(i) = s16(u16be(2 + 2*i))
start(0) = B
start(c) = B + sum(delta(i), i = 0 .. c-1)

available(c) = (delta(c) != 0)
```

A zero map WORD means no help for that context. It does not identify an empty
page at the next context's offset. A negative delta can move backward into an
earlier page; context starts need not be monotonic or unique.

The header's `N` is not a maximum context ID. Context `N` starts at
`B + sum(delta(0)..delta(N-1))`; its availability WORD is `u16be(B)`.
Thus remaining bytes at that cumulative end can be a real final page.

The namespace of application-selected contexts is external to the file.
To reconstruct it, use the matching application's map profile and contexts,
together with authored hotspot/next-page targets. Do not interpret every
preloaded text WORD as proof of an independent article.

## 4. Page record

At a valid addressed page start `P`:

| Page-relative offset | Size | Meaning |
| --- | ---: | --- |
| `+0` | 2 | Big-endian next-page context; zero means no next page |
| `+2` | variable | Nibble-coded text/control stream |

There is no stored title, paragraph count, text-byte length or per-page palette.
The native help index is context 1; an English caption is not its identifier.
Previous-page navigation uses application history, not another page field.

A context can point inside another page's bytes. For example, TDW 5.0 context
776 begins at `start(775)+1`; both streams display the same Imports page.
That is a genuine overlapping context, not a second physical article or a
title-based redirect. Keep the source context identity.

A page's native termination comes from its control stream and screen-row limit,
not from a size WORD. For bounded extraction, the next distinct ordinary page
start or EOF supplies a byte boundary; overlapping alias starts are not new
ordinary-page boundaries. An EOF offset alone contains no page WORD.

### 4.1 Overlapping context addresses

An overlapping address can lie in either header byte or in the middle of
a literal escape. It is not necessarily the final byte/nibble cursor of a
decoded character. To associate a context address with a containing stream,
track the complete byte ranges actually consumed while reading that stream:

- The page WORD consumes `[P, P+2)`.
- A symbol starting at byte cursor `O` and ending at cursor `(O2, half2)`
  consumes `[O, O2 + half2)`, where `half2 = 1` means that the low nibble
  of byte `O2` has been read and its high nibble remains unread. The range
  can overlap the preceding symbol's range because they share a byte.
- An aligned hotspot target WORD consumes its two raw bytes, separately
  from the nibble-coded symbols. Returning a pushed-back symbol does not
  consume additional bytes.
- The byte at the exclusive end of a range is not owned merely because
  the cursor reached it. Stop tracing at the page terminator or row cap;
  do not assign unused trailing bytes by proximity or text similarity.

For TDH CRC32 `A9C668A7`, context 519 starts at 112,639, one byte into
context 518's header at 112,638. Context 528 starts at 63,973, byte `+68`
of context 328 at 63,905. That byte belongs to a literal `62h` (b) whose
nibbles span relative bytes 67 and 68; its final cursor is byte 69. Looking
only at final cursors misses both overlaps. A context starts its own
next-context WORD at its addressed byte and resets nibble decoding at
`start+2`, so overlapping streams need not display identical first rows.
Equal captions or normalized prose are not evidence of an address relation.

## 5. Nibble decoding

Reset the nibble cursor at `P+2`. Read the low nibble of a byte first, then
the high nibble. The verified TD 1.0/1.5, Profiler and TD DOS 4/5 alphabet is:

| Nibble | Decoded byte |
| --- | --- |
| `0` | no output; read another nibble |
| `1` | `65h` — e |
| `2` | `74h` — t |
| `3` | `72h` — r |
| `4` | `6Fh` — o |
| `5` | `69h` — i |
| `6` | `6Eh` — n |
| `7` | `61h` — a |
| `8` | `73h` — s |
| `9` | `6Ch` — l |
| `A` | `63h` — c |
| `B` | `68h` — h |
| `C` | `20h` — space |
| `D`, `E` | `00h` — NUL control |
| `F` | literal byte: read two raw nibbles `lo, hi`, emit `lo | (hi << 4)` |

Literal nibbles are raw values: zero inside an escape is not skipped. An escape
can cross a byte boundary. A caret control is the literal byte `5Eh`, encoded
by nibble sequence `F E 5`, not by compressed nibble D.

```text
next_symbol():
    n = next_raw_nibble()
    while n == 0:
        n = next_raw_nibble()
    if n == F:
        lo = next_raw_nibble()
        hi = next_raw_nibble()
        return lo | (hi << 4)
    return alphabet[n]
```

Decoded text uses the application's DOS character set; inspected English
files use CP437. NUL, CR/LF and caret must be interpreted as controls before
translating ordinary character bytes. The file has no encoding declaration.

## 6. Text controls and hotspots

| Decoded byte | Operation outside a hotspot |
| --- | --- |
| `00h` | End page |
| `0Ah`, `0Dh` | End display row; consume an adjacent complementary CR/LF |
| `09h` | One space, not a tab stop |
| `5Eh` | Begin hotspot control |
| other | Append a DOS character |

For a hotspot:

1. Decode the opening caret through the nibble stream.
2. Discard any unread high nibble of that byte and align to the next byte.
3. Read an uncompressed **big-endian target context WORD**.
4. Resume nibble decoding on the following byte, low nibble first.
5. Read label text to its closing decoded caret. The closing caret is a
   control, not visible label text; subsequent text resumes at the current
   nibble cursor, without another target WORD.

The target WORD must not pass through the nibble alphabet. It is a context
index in this same file, not a character pair or an absolute file address.
A zero target is a literal-caret control: consume the target WORD, append
`5Eh` as visible text and resume normal decoding. It does not end the page,
create a clickable destination or rewind the WORD into the nibble stream.
This represents, for example, the Pascal pointer operator `^`.

Inside a nonzero-target label, only a decoded caret ends the field. NUL,
CR/LF and TAB are raw label bytes, not the outer text controls. Continue
decoding through an embedded NUL or line break until the closing caret;
EOF is not an alternative delimiter. All decoded label bytes count toward
the native fit test, including bytes after NUL.

The native display and carried-prefix buffers are C strings. An embedded
NUL therefore ends the visible string without ending the encoded label.
If the label fits, the row's visible text stops at that NUL; subsequent
bytes appended on the same row remain invisible. If the label must be
carried, the prefix copy retains only its bytes before NUL. Text following
the closing caret resumes normal decoding and can then follow that copied
prefix visibly. A CR/LF after the closing caret remains a hard row break.
Within a label, CR/LF and TAB before NUL are retained bytes rather than
row breaks or tab expansion. Oversized labels can exceed native buffers;
their memory-overflow behavior is not a portable display rule.

## 7. Screen layout

The verified TD 1.0/1.5, Profiler and TD DOS 4/5 line buffer has a `31h` limit including
one leading margin cell: **48 visible columns**. The native page loop requests
at most **15 rows**, including blank rows.

- Ordinary text exceeding the width wraps at the last preceding space;
  carry the following word to the next row.
- A hotspot that does not fit moves as a whole to the next row.
- TD 1.0/1.5 and Profiler let a hotspot finish at visible column 48 without
  inspecting the symbol after its closing caret.
- TD DOS 4/5 let a hotspot finish at visible column 48 when the
  symbol following its closing caret is SPACE; otherwise it reserves another
  cell and ends by 47. This lookahead remains in the normal text stream.
- Trailing row spaces are not displayed.
- A leading encoded CR/LF is a real blank native row and counts toward 15.

The text prefix WORD `DFF0h` is not a page header: low-first nibble decoding
of bytes `DF F0` produces literal CR (`F D 0`) and then literal LF from
the following nibble/byte sequence. Do not universally strip a leading row.

Older line routines can leave hotspot coordinates on their previous row
when subsequent ordinary text causes a word wrap. Thus native hotspot spans
need not fit the final trimmed row: a multiword label can appear across two
rows while its stored-in-memory span still refers to the first. These spans
are runtime products, not additional coordinate fields in the file. Their
reflow must be distinguished from decoding an incorrect target WORD.

The label's decoded characters still identify the link across a word wrap.
To retain their positions, use zero-based, half-open character ranges
`[a, b)` on the row buffer before wrapping. Let `h` be the retained head
length and `q` the start of the carried text. For a space break at position
`k`, `h = k` and `q = k+1`; for a hard 48-cell break, `h = q = 48`.

- The current-row fragment is `[a, min(b, h))`, if nonempty.
- The next-row fragment is `[max(a, q)-q, b-q)`, if nonempty.
- Both fragments retain the same uncompressed target WORD.
- The discarded wrap space has no output cell. Suffixes/punctuation outside
  `[a, b)` do not become part of the link.
- Repeat the range intersections if the carried text wraps again. Only
  ranges intersecting displayed rows/cells belong to the visible screen.

For example, a label at one-based columns 40–48 containing `byte list`
splits at the space in column 44 into current-row columns 40–43 (`byte`)
and next-row columns 1–4 (`list`). A following period remains ordinary text.
These coordinates are derived display state, not bytes stored in a page.
An embedded label NUL can likewise leave native coordinates beyond the
visible C string. Intersect such spans with its displayed cells; neither
hidden bytes nor cells below the screen-row limit have visible positions.

## 8. Byte examples

### 8.1 A short text page

```text
00 00 1F 14 0D
^^^^  ^^^^^^^^
Next  text
```

`Next = 0`. Text nibbles are `F,1,4,1,D,0`: literal `41h` (A),
dictionary `65h` (e), NUL, then unused padding. Visible text is `Ae`.

### 8.2 Stored map and final-page availability

| Original | N | B | WORD at B | Cumulative end of stored deltas |
| --- | ---: | ---: | --- | ---: |
| TFH, CRC32 `EDCB6DAB` | 363 | 728 (`02D8h`) | `0000h` | 67,256 |
| TFH, CRC32 `C7CCE043` | 366 | 734 (`02DEh`) | `2C00h` | 68,980 |

In the first file, context 363 is unavailable even though 159 bytes remain
(a two-byte page WORD plus 157 encoded bytes).
In the second, context 366 is available; its 258-byte record reaches EOF at
69,238. Those residual lengths are sample properties, not fixed trailer sizes.

The same overlapping slot enables genuine final pages in older TDH:

| CRC32 | N | B | WORD at B | Final page start | File size |
| --- | ---: | ---: | --- | ---: | ---: |
| `A6E139F2` | 596 | 1,194 | `0001h` | 125,593 | 125,805 |
| `F126AD2C` | 538 | 1,078 | `0001h` | 114,591 | 114,748 |
| `4B5D33CE` | 537 | 1,076 | `0001h` | 142,333 | 142,478 |

For `A6E139F2`, a hotspot in context 55 contains target WORD `0254h`
(596), addressing the final Hardware breakpoint page by the same signed
cumulative formula. These are not fixed trailer records.

### 8.3 NUL inside a closed hotspot label

```text
00 00 EF 05 00 0B 1F F4 00 2F F4 5E 0F 00
```

The page WORD is zero. `EF 05` decodes the opening caret and leaves a
padding high nibble, discarded before reading target `000Bh` (11).
The remaining nibble stream decodes `41h 00h 42h 5Eh 00h`: label bytes
`A NUL B`, closing caret, then the outer page terminator. The visible row
is `A`; `B` is still part of the encoded label, not another page or prose.
The three raw label bytes affect the fit test, but only column 1 is visible.

## 9. Validation and unspecified fields

Check header/map reads, signed cumulative starts, page WORDs and literal
escapes against file bounds. Distinguish absent contexts, empty text pages,
overlapping contexts and offsets that contain no data. A missing target must
not be replaced by a neighboring context or a similar title.

For an addressed page, require both bytes of its next-context WORD. A literal
escape requires its two raw data nibbles; a caret requires a complete aligned
target WORD. A nonzero hotspot label must reach its closing caret, including
when it contains NUL or CR/LF. Those bytes do not replace the delimiter.
EOF before a valid terminal control or the requested
screen-row limit is an incomplete text stream, not an implicit page end.
Slot zero is opaque data and must not be checked as an encoded text page.

No complete-file length or checksum is stored in these fields. Unaddressed
tail bytes can exist when the overlapping map slot is unavailable. Removing
such bytes does not prove a text-page truncation. Likewise, removing an entire
unreferenced last record can be indistinguishable from an unused runtime EOF
slot; an offset at EOF contains no page header. Detecting arbitrary whole-file
damage requires a trusted external length/digest, not a fabricated terminator
or guessed page. The screen-row cap is a valid decode stop even if later
bytes contain additional text.

Unknown application profiles, their complete context namespaces,
unsafe oversized-label buffer behavior and additional attribute controls are not
specified by this document. There is no basis for inferring them from a
filename extension alone.
