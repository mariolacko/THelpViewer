# DOS BACKUP Source Container

> Updated: 2026-10-11

DOS 2.x–3.2 BACKUP adds a 128-byte file header before the original file bytes.
It is a source wrapper, independent of the HELP format inside.

Primary evidence: David Jurgens' original HelpPC `TABLES.TXT`, topic
`backup headers`, and the two wrapped Turbo Prolog 1.0 samples. An independent
contemporary account is [Inside DOS BACKUP, IBM PC Information Exchange,
Jan/Feb 1986, printed p. 39](https://www.bitsavers.org/pdf/ibm/pc/IBM_PC_Information_Exchange/G320-0848-0_198601.pdf).

## Header layout

| Offset | Size | Meaning / validation |
| --- | --- | --- |
| `00` | 1 | Continuation flag: `00` means more parts, `FF` means final part. |
| `01` | 1 | Disk sequence number in the HelpPC-described layout. |
| `02..04` | 3 | Unused; zero in inspected samples. |
| `05..52` | 78 | DOS pathname storage/padding region. HelpPC describes 64 pathname bytes followed by 14 unused bytes; the IBM article describes the region together. |
| `53` | 1 | Path string length including its terminating NUL. |
| `54..7F` | 44 | Unused, zero. |
| `80` onward | variable | Original file bytes. |

The pathname is ASCII, NUL-terminated and padded. Complete final single-volume
examples have flag `FF` and sequence 1. Continuation flag `00` or a later
disk number describes a part, not a complete original file. The inner HELP
format is independent of this header.

## Verified samples

| Wrapped original | Bytes | CRC32 | Path | Unwrapped bytes / CRC32 |
| --- | ---: | --- | --- | --- |
| Prolog 1.0 GEOBASE.HLP | 3,556 | `2B446AAB` | `\PROLOG\GEOBASE.HLP` | 3,428 / `E71708C8` |
| Prolog 1.0 PROLOG.HLP | 10,090 | `5C5EE722` | `\PROLOG\PROLOG.HLP` | 9,962 / `FB92DEEC` |
