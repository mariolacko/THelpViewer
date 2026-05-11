# Borland Turbo Debugger/Profiler Runtime Help

Status: detected, not decoded.

`TDHELP.TDH` from Turbo Debugger and `TFHELP.TFH` from Turbo Profiler are not
Borland THELP/TPH/TCH files. They do not contain the THELP signature
`$*$* &&&&$*$`, and the existing THELP record parser must not handle them.

## Confirmed Sample

Current samples:

| File | Size | CRC32 | SHA256 |
|------|------|-------|--------|
| `TDHELP.TDH` | 112,669 | `A9C668A7` | `0c23e564e60f3ec97b98eb71adab052eae2f8b19d5202faa7c43d93271da5f07` |
| `TDHELP.TDH` | 125,805 | `A6E139F2` | `fabad0cc8f53cc5ad3134c3c41baf384f12fa72581b00a1012bf6553fc25f04d` |
| `TFHELP.TFH` | 67,415 | `EDCB6DAB` | `a00fcaee3c1ee94a8801cdbae9dd75d602ed91d9df4063fd1bc27676dc075630` |

The same file appears in:

| Collection | Path |
|------------|------|
| Borland Turbo Debugger 1.0 | `sources/Borland Turbo Debugger 1.0/TDHELP.TDH` |
| Borland Turbo Assembler 1.0 with Turbo Debugger | `sources/Borland Turbo Assembler 1.0 with Turbo Debugger/TDHELP.TDH` |
| Borland Turbo Profiler | `sources/Borland Turbo Profiler/TFHELP.TFH` |
| Borland Turbo Debugger/Profiler/Assembler 2.x | `downloads/.../TDUTIL.ZIP/TDHELP.TDH` |
| Borland Turbo Debugger/Profiler/Assembler 2.x | `downloads/.../TFHELP.ZIP/TFHELP.TFH` |

## Observed Header

The file starts with big-endian words:

```text
0206 0001 0124 01B7 0072 0096 008B 00AF
006C 00A7 0086 00C3 00BB 00B4 00BE 0060
```

Confirmed structural observations in the Turbo Debugger 1.0 sample:

| Offset | Value | Meaning |
|--------|-------|---------|
| `0x0000` | `0x0206` | Header word; in this sample it is also the byte size of each decode table. |
| `0x0002` | 259 big-endian words | First decode table, 518 bytes. |
| `0x0208` | 259 big-endian words | Second decode table, 518 bytes. |
| `0x040E` | `00 01` | Separator word before payload. |
| `0x0410` | starts `A0 CC CC ...` | Encoded payload. |

The two 259-entry tables look like a compact decoder table pair, but the exact
meaning of entries and root/index handling is not confirmed yet. Treating them
as a simple left/right Huffman tree does not produce readable text.

The payload lead also has a stable short preamble in the current real samples:
the first payload byte is followed by 9 consecutive `0xCC` bytes, and both TDH
and TFH then continue with the same visible prefix bytes starting at
`FC 48 5F F4 4C 0F ...`.

The later 125,805-byte sample has the same structure but starts with `0x0254`,
which gives two 596-byte tables with 298 big-endian words each. Its payload
starts at `0x04AC` with `AE CC CC ...`. This confirms that the first word is a
table byte size, not a fixed TDH version signature.

`TFHELP.TFH` follows the same broad runtime-help structure but with a smaller,
odd first table byte size:

| Offset | Value | Meaning |
|--------|-------|---------|
| `0x0000` | `0x016B` | Header word; byte size of each decode table. |
| `0x0002` | 363 bytes | First decode table. |
| `0x016D` | 363 bytes | Second decode table. |
| `0x02D8` | `00 00` | Separator word before payload. |
| `0x02DA` | starts `96 CC CC ...` | Encoded payload. |

`file(1)` reports this as `ALAN game data version 2.60`, but that is a false
positive caused by the first big-endian word `0x0206`. The system magic rule for
ALAN only checks this word and does not validate a Borland TDH structure.

Brute-force checks against nearby decoder families have not matched yet. The
currently tested simple left/right prefix-tree variants and small standard LZW
bitstream variants both produce only repetitive synthetic output, not readable
help text.

## Relation To Turbo Debugger / Profiler

`TD.EXE` contains:

```text
tdhelp.tdh
No help for this context
Help file %s not found
Index
Previous page
First page
```

This confirms that TDH is the external runtime help payload used by Turbo
Debugger. The decompressor and context resolver are likely in `TD.EXE` and/or
`TD.OVL`.

`TPROF.EXE` contains the same UI strings plus:

```text
tfhelp.tfh
No help for this context
Help file %s not found
Index
Previous page
First page
```

This confirms that TFH is the matching external runtime help payload used by
Turbo Profiler and strongly suggests a shared or closely related help decoder.

`DEHELP.DOC` from the BOA/DEHELP tools explicitly lists Turbo Debugger,
Turbo Debugger for Windows, Turbo C++ for Windows, and Resource Workshop as
unsupported formats. That matches the observed separate TDH/TFH container
instead of the standard THELP layout.

## Current Reader Behavior

`thelpviewer/converter/readers/tdh.py` contains strict TDH and TFH detectors and
a diagnostic reader. It intentionally emits a single status topic instead of
inventing topics from unknown data.

The reader metadata contains:

```json
{
  "format": "tdh",
  "format_status": "undecoded",
  "tdh_probe": {
    "header_word": "0x0206",
    "table_byte_size": 518,
    "table_word_count": 259,
    "encoded_payload_offset": 1040,
    "payload_lead_byte": "0xA0",
    "payload_lead_cc_run": 9
  }
}
```

## Work Needed For Full Reader Support

To produce normal UHF2 topics, we still need to reverse:

| Area | Needed result |
|------|---------------|
| Encoded table | Exact role of the two 259-word big-endian tables. |
| Payload codec | Bit/byte-level decompression algorithm. |
| Topic boundaries | Mapping from TD help contexts to decoded text blocks. |
| Index/menu data | Runtime help index labels and navigation actions. |
| Text attributes | Link, color, and selection markers if stored in TDH. |

Until these are known, TDH/TFH support must remain separate from THELP and
marked as undecoded.
