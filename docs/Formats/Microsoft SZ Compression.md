# Microsoft SZ and SZDD Compression

> Updated: 2026-10-14

These installer wrappers contain one compressed file. Their bytes are
independent of the embedded file format. An expanded QuickHelp database, for
example, begins `4C 4E 02 00`; that is not an SZ header.

Primary evidence for the split profile is Microsoft QuickC 2.50's original
`PACKING.LST`, `Advisor.img/QC.HL$` and `Learning.img/QC.HL2` in the
[distribution archive](https://archive.org/details/microsoft-quick-c-2.50).
The standalone header profiles are also described by
[libmspack's SZDD header reader](https://github.com/kyz/libmspack/blob/master/libmspack/mspack/szddd.c).
All lengths below are unsigned little-endian integers. Offsets are hexadecimal.

## SZDD header

| Offset | Size | Meaning |
| --- | --- | --- |
| `00` | 8 | Signature `53 5A 44 44 88 F0 27 33`. |
| `08` | 1 | Compression method `41` (`A`). Other methods are not specified here. |
| `09` | 1 | Original filename's missing final character, or zero. It is not a data byte. |
| `0A` | 4 | Expanded byte count. |
| `0E` | variable | LZSS token stream. |

## Microsoft SZ/D1 header

| Offset | Size | Meaning |
| --- | --- | --- |
| `00` | 7 | Signature `53 5A 20 88 F0 27 33`. |
| `07` | 1 | Initial-stream marker `D1`. Other initial marker values are unverified. |
| `08` | 4 | Expanded byte count for the complete file, not just this media part. |
| `0C` | variable | First bytes of the LZSS token stream. |

This profile is also known as the QBasic SZDD variant. There is no missing
filename-character field in its header.

## LZSS token stream

Allocate a circular 4,096-byte dictionary filled with `20` (space). Its
initial write cursor is `FF0` for SZDD and `FEE` for SZ/D1. Every cursor wraps
modulo 4,096. Read a control byte and consume its eight bits **least
significant first**. For each bit:

- `1`: consume one literal byte. Emit it, store it at the write cursor and
  advance the cursor.
- `0`: consume two bytes `a`, `b`. The absolute dictionary read position is
  `a | ((b & F0) << 4)`; the match length is `(b & 0F) + 3`. For each match
  byte, read the current dictionary cell, emit it, store it at the write
  cursor, and advance both cursors. Copy one byte at a time: overlapping
  matches may read bytes just written by the same match.

Stop when the declared expanded count has been emitted. A final control
byte need not use all eight bits. A match reaching that count emits only
the remaining required bytes. EOF before that count is an incomplete stream,
not implicit zero padding or a complete first-volume file.

For an SZ/D1 dictionary, `07 41 42 43 EE F3` emits `ABCABCABC`: three literal
bits precede a six-byte overlapping match from `FEE`. No Huffman or secondary
keyword expansion belongs to this wrapper.

## Split-media continuation

The QuickC packing list identifies `qc.hlp` on the Advisor disk as part 1
and `qc.hl2` on the Learning disk as part 2. The physical compressed names
are `QC.HL$` and `QC.HL2`. The second file has this header:

| Offset | Size | Meaning |
| --- | --- | --- |
| `00` | 7 | Same signature `53 5A 20 88 F0 27 33`. |
| `07` | 1 | Part sequence number; `02` in the verified second part. |
| `08` | variable | Continuation of the preceding compressed token stream. |

There is **no expanded-length DWORD** in the continuation. Remove its eight
header bytes, concatenate the remaining bytes after the first part's stream,
then decode with the first header's length and profile. Do not reset the
dictionary, control-bit position, or a partly consumed literal/match token at
a disk boundary. Decoding continuation files independently is invalid.

Numbered third and later parts should be treated as a sequence whose filename
and header number agree; no original part beyond number 2 has yet been
verified. Other naming conventions and sequence-marker variants are unknown.
Missing numbers, duplicate candidate parts or invalid headers do not identify
a unique complete stream and must not be repaired by filename guessing.

## Original split example

```text
QC.HL$ (360,000 bytes):
53 5A 20 88 F0 27 33 D1 76 B3 07 00 FF 4C 4E 02 ...

QC.HL2 (81,961 bytes):
53 5A 20 88 F0 27 33 02 45 DA 4E FF B8 B0 D4 B2 ...
```

The declared output is `0007B376` = 504,694 bytes. Excluding the first
12-byte and second eight-byte headers leaves 441,941 compressed bytes.
Expanded CRC32 is `0143767A`; SHA-256 is
`5c256559a80df21a8040f440c6e1726bb8c56fa10a02866ad0cea0306c88fd43`.
