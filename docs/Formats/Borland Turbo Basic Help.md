# Borland Turbo Basic Help

`TBHELP.TBH` is a CP437 screen database with little-endian WORD record types
and lengths. It is not the three-byte-record, nibble-compressed THELP grammar,
despite sharing its `$*$* &&&&$*$` signature and version bytes `01 01`.

## File prefix

| File offset | Bytes | Meaning |
| --- | --- | --- |
| `0000h` | 23 | ASCII `TURBO BASIC HELP FILE.` followed by NUL |
| `0017h` | 1 | Separator `1Ah` |
| `0018h` | 13 | ASCII `$*$* &&&&$*$` followed by NUL |
| `0025h` | 1 | Format version `01h` |
| `0026h` | 1 | Text version `01h` |

The authoritative prefix is the following byte sequence; do not derive
offsets by counting the printable signature as twelve characters:

```text
54 55 52 42 4F 20 42 41 53 49 43 20 48 45 4C 50
20 46 49 4C 45 2E 00 1A 24 2A 24 2A 20 26 26 26
26 24 2A 24 00 01 01
```

It occupies `27h` bytes: the stamp including NUL is 23 bytes, the separator
is at `17h`, the signature including NUL is 13 bytes at `18h`, and the
format/text versions are at `25h` and `26h`. Both versions are `01h` in the
described profile. No other version pair is established here.

## Records

Records start at `27h`. Each header is `LE16 Kind, LE16 Length`. Advance by
`4 + Length`, **except Kind 4**, whose count WORD is outside Length: advance
by `6 + Length`. Reject any header or payload crossing EOF. There is no
terminating record: the record stream ends exactly at EOF.

| Kind | Payload | Length |
| --- | --- | --- |
| 0 | File parameters | 10 |
| 2 | Context directory | `2 + 6 * Count` |
| 3 | Encoded screen text | Stored byte count |
| 4 | Hotspots for preceding screen | `12 * Count`, excluding Count WORD |

The file has one Kind 0 followed by one Kind 2, then pairs of Kind 3 and
Kind 4. Other kinds/orderings are not established. A screen without links
still has `04 00 00 00 00 00` as its empty Kind 4 record.

## File parameters (Kind 0)

| Payload offset | Type | Meaning |
| --- | --- | --- |
| `+0` | LE16 | Opaque word, observed zero |
| `+2` | LE16 | Opaque word, observed zero |
| `+4` | LE16 | Screen height, observed 15 |
| `+6` | LE16 | Screen width, observed 48 |
| `+8` | LE16 | Space packing: 0 = literal; 1 = FE runs |

Example: `00 00 00 00 0F 00 30 00 01 00`. The last word is not a margin
or a nibble-compression selector. No character lookup table follows it.

## Context directory (Kind 2)

The first WORD is Count; exactly Count six-byte entries follow:

| Entry offset | Type | Meaning |
| --- | --- | --- |
| `+0` | LE16 | Stored ID; equals slot number in populated observed slots |
| `+2` | LE32 | Absolute file offset of a Kind 3 **header**, or `FFFFFFFFh` |

The context number is the zero-based slot, not a byte offset. The original
lookup selects `directory_entries + 6 * context` and uses the DWORD, without
testing the stored ID. Empty observed slots are `FF FF FF FF FF FF`.
Reject a non-sentinel offset that does not identify an actual Kind 3 header;
do not reinterpret it as an offset into a text payload. Multiple slots can
refer to one screen. Screens not referenced by any slot are still reachable
through hotspot offsets and must not be discarded.

The native F1 entry point requests slot 100 (`64h`). Invalid/missing context
lookups fall back to slot 100. This is a consumer binding, not an extra
directory flag. The observed directory has 164 slots, Length `03DAh`.

## Text (Kind 3)

Decode only the declared payload bytes, with these rules:

1. With packing 1, `FEh N` consumes two stored bytes and produces N spaces.
   `N=0` produces nothing; `N=255` produces 255 spaces. A final `FEh` without
   a count is truncated. With packing 0, `FEh` is a literal CP437 glyph.
2. `00h` flushes the current line, increments the row and resets the column.
   Consecutive NULs produce empty rows.
3. `01h` is ignored, without advancing the cursor.
4. Other bytes are literal CP437 cells. In particular `FFh` is literal;
   it does not consume a following displacement byte in this consumer.
5. Controls apply to the space-expanded stream; spaces themselves never act
   as control bytes. CR/LF/TAB are not established line-layout controls here.

Example: packed `41 FE 03 42 00 00 43 00` displays rows `A   B`, empty,
`C`. In literal mode `41 FE 00 42 00` displays `41 FE`, then `42`.

Every observed row terminates with NUL. Behavior of a nonempty final fragment
without NUL is not a reliable alternate grammar: the native final flush uses
a different buffer than normal newline flushing. Such a fragment should be
reported as unverified/malformed, not silently guessed. Bound expanded lines
and row counts when reading untrusted data; packing can enlarge stored text.

## Hotspots (Kind 4)

After its four-byte record header, read a LE16 Count and exactly Count
twelve-byte entries. Require header Length `= 12 * Count`.

| Entry offset | Type | Meaning |
| --- | --- | --- |
| `+0` | BYTE | One-based row |
| `+1` | BYTE | One-based first column |
| `+2` | BYTE | One-based last column, inclusive |
| `+3` | BYTE | Reserved/opaque; observed zero |
| `+4` | BYTE | Left navigation field |
| `+5` | BYTE | Right navigation field |
| `+6` | BYTE | Up navigation field |
| `+7` | BYTE | Down navigation field |
| `+8` | LE32 | Absolute offset of destination Kind 3 header |

The display highlights the original cells; there are no link delimiters in
the text. Validate row and inclusive columns against decoded text, and the
destination against record boundaries. Navigation bytes describe movement
among the screen's hotspot entries; their sentinel/edge behavior is not
fully established. They are not destination contexts. Preserve them as bytes
without substituting guessed links.

Example: `01 01 05 00 00 00 00 00 13 04 00 00` highlights the first five
cells on row 1 and targets the record at `0413h`. Context directory entries
and hotspots both use absolute byte offsets, not paragraphs, relative deltas
or later THELP context-number fields.
