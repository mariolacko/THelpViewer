# Software602 M602 HelpSystem Format

> Created: 2026-04-03 · Last updated: 2026-04-03

Used by: Software602 products (primarily M602 Manager).  
File extension: `.HLP`.

This document describes the classic `M602 HelpSystem` variant only.

## 3.1 File Layout

```
┌──────────────────────────────────┐  Offset 0
│  Header (27 bytes, unencrypted)  │
├──────────────────────────────────┤  Offset 27
│  Encrypted body (XOR $FA)        │
│    Record 0                      │
│    Record 1                      │
│    ...                           │
│    Record N                      │
│    [Binary index / padding]      │
└──────────────────────────────────┘
```

## 3.2 Header (27 bytes)

```
$1A  "(c) Software602 HelpSystem"
```

| Offset | Size | Content                           |
|--------|------|-----------------------------------|
| 0      | 1    | `$1A` (DOS end-of-file marker)    |
| 1      | 26   | `(c) Software602 HelpSystem`      |

Detection: first bytes match `$1A(c) Software602 HelpSystem`.

### 3.2.1 Integer Endianness

Unless stated otherwise, multi-byte numeric values in the classic M602 format
are stored as little-endian integers, matching DOS/x86 conventions.

This document still spells some values out byte-by-byte where that is more
useful for reverse-engineering, for example hyperlink targets stored as
`ctx_lo, ctx_hi`.

No confirmed big-endian numeric fields have been observed in `M602_200.HLP`.

## 3.3 Body Encryption

All bytes after the 27-byte header are XOR-encrypted with constant key `$FA`:

```text
plaintext_byte = encrypted_byte XOR $FA
```

XOR is symmetric, so decryption = encryption.

## 3.4 Record Format

```
┌────────────────────────────┐
│  Length (1 byte)           │  0–255
├────────────────────────────┤
│  Content (Length bytes)    │
└────────────────────────────┘
```

Records are concatenated sequentially. Trailing `$0D` bytes in content are
stripped.

Record types are determined by content pattern, not by a dedicated type field.

| Pattern                                   | Type      |
|-------------------------------------------|-----------|
| `$01` + text + `$DC`, no `$DF`, [1]≠`$02` | Title     |
| `$01` + bytes containing `$DF`            | Separator |
| Anything else                             | Body text |

Body records may also start with `$01`. In observed `M602_200.HLP` this is an
internal line prefix, not a visible CP437 smiley. Strip one leading `$01` from
body records before parsing visible text and links. A body record containing
only `$01` is a blank line. Do not treat `$01` bytes inside the two raw target
bytes after a link as text or markup.

## 3.5 Title Records

Mark the beginning of a new help topic.

```
┌─────┬──────────────────────┬──────┐
│ $01 │  Title text bytes    │ $DC  │
└─────┴──────────────────────┴──────┘
```

- First byte: `$01` marker
- Last byte: `$DC` title terminator
- Must not contain `$DF`
- Second byte must not be `$02`
- Title text is in Kamenický encoding

## 3.6 Separator Records

Visual dividers between topics or sections.

```
┌─────┬─────┬─────┬─────┬───┐
│ $01 │ $DF │ $DF │ $DF │...│
└─────┴─────┴─────┴─────┴───┘
```

`$DF` renders as `▀` in CP437/Kamenický.

## 3.7 Hyperlink Encoding

Links can appear inside any body record:

```
┌─────┬──────────────────┬─────┬────────┬────────┐
│ $02 │  Link text bytes │ $02 │ ctx_lo │ ctx_hi │
└─────┴──────────────────┴─────┴────────┴────────┘
```

| Field     | Size | Description                     |
|-----------|------|---------------------------------|
| `$02`     | 1    | Link start marker               |
| Link text | var  | Display text                    |
| `$02`     | 1    | Link end marker                 |
| ctx_lo    | 1    | Context ID low byte             |
| ctx_hi    | 1    | Context ID high byte            |

Raw target = `ctx_lo + (ctx_hi * 256)`.

Equivalently, this is one 16-bit little-endian value assembled from the two
bytes `ctx_lo, ctx_hi`.

### 3.7.1 Link Target Semantics

Despite the field names above, the two bytes after the closing `$02` are not a
topic number. They are also **not** reliably decodable as a direct offset into
the decrypted record stream; that earlier hypothesis produces wrong topic
destinations for multiple real links.

Observed behavior in `M602_200.HLP`:

- raw targets form a small number of numeric families (for example low bytes
  `00`, `07`, `0B`, `13`, `79`, `9C`)
- the same visible hotspot label can appear with different raw target values
  when the help contains duplicate topic titles
- the exact destination is stored in the unencrypted binary tail at the end of
  the file

### 3.7.2 Binary Tail Link Index

After the XOR `$FA` record stream ends, classic M602 appends an unencrypted
binary tail. In `M602_200.HLP` the tail starts at file offset `$21C4F`
(`138351` decimal).

Observed size in `M602_200.HLP`:

- total tail size: `$064E` (`1614`) bytes
- tail header size: `6` bytes
- tail entry size: `8` bytes
- total tail entries: `201`

The tail begins with a 6-byte header:

```text
0F 27 1B 00 00 00
```

Observed interpretation:

- byte `0` = root/pivot count candidate (`15` in `M602_200.HLP`)
- bytes `1..5` = still not fully decoded

Immediately after the 6-byte header follows a flat array of 8-byte entries.

```text
┌──────────────┬────────────────────┬───────────────────────┐
│ delta        │ raw_target_swapped │ target_offset         │
│ uint16 LE    │ uint16 LE          │ uint32 LE             │
└──────────────┴────────────────────┴───────────────────────┘
```

Equivalent split of the same `target_offset` field:

```text
┌──────────────┬────────────────────┬──────────────────┬──────────────────┐
│ delta        │ raw_target_swapped │ target_offset_lo │ target_offset_hi │
│ uint16 LE    │ uint16 LE          │ uint16 LE        │ uint16 LE        │
└──────────────┴────────────────────┴──────────────────┴──────────────────┘
```

Observed entry count in `M602_200.HLP`:

- `201` total 8-byte entries in the tail
- entries `0..199` resolve real help link targets
- entry `200` is a final sentinel row, not a normal topic lookup row
- the first real row points to topic `2`, so topic `1` ("Chyba") has no tail
  lookup row

### 3.7.3 Finding The Tail Start

For `M602_200.HLP` the start of the binary tail does not need to be found
heuristically. The file ends with an 8-byte sentinel:

```text
9E 00 C9 00 BD 22 02 00
```

Interpretation:

- bytes `2..3` = total count of 8-byte tail entries, little-endian
  (`$00C9` = `201`)
- bytes `4..7` = absolute EOF offset, little-endian
  (`$000222BD` = `139965`, exactly the file size)

So the tail start can be computed backwards from EOF:

```text
tail_start = file_size - 6 - (entry_count * 8)
```

For `M602_200.HLP`:

```text
tail_start = $222BD - 6 - ($00C9 * 8) = $21C4F
```

which matches the observed binary tail start.

This means `hlx2html` no longer needs the old FA-density heuristic as the
primary detector for compiled M602 `.HLP`; it can derive the tail start exactly
from the final sentinel and the fixed 6-byte tail header size.

### 3.7.4 Text Record Count

The number of XOR text records before the binary tail is still not known as an
explicit header field.

For `M602_200.HLP`, sequential parsing yields:

- `3363` text records before the first binary-tail record candidate
- `3364` total parsed records if the first binary-tail candidate record is also counted
- `201` title records
- `201` separator records
- `2961` body-text records
- `0` zero-length records observed in this sample

No explicit 16-bit or 32-bit field equal to `3363` or `3364` has been found in
the file so far. Current evidence suggests that the compiled file stores enough
information to derive the tail start exactly, but not an obvious standalone
`text_record_count` field.

### 3.7.5 Decoding Tail Entries

For regular lookup rows, decoding works as follows:

1. `raw_target_swapped` stores the same two target bytes as the inline body
   link, but in reversed order.
   Example: inline target `$1979` is stored in body bytes as `79 19`
   (`ctx_lo, ctx_hi`), while the tail index stores the same target bytes as
   `19 79`. If those tail bytes are read as a normal little-endian `uint16`,
   the temporary numeric value is `$7919`, so the decoder must swap the bytes
   back before comparing it with the inline raw target.
2. `target_offset = target_offset_lo + (target_offset_hi << 16)`.
3. `target_offset` is an absolute file offset of the destination topic title
   record.
4. Map that absolute file offset back to the parsed topic/context.

For regular lookup rows, `delta` is also meaningful:

```text
delta = current_target_offset - previous_target_offset
```

with the implicit initial `previous_target_offset` equal to the first byte after
the 27-byte file header (`$001B`).

Examples:

- first lookup row: `A2 01 0A 00 F2 01 00 00`
  `target_offset = $01F2`, previous offset = `$001B`, so
  `delta = $01F2 - $001B = $01A2`
- row for topic `120`: `47 0D 1E 79 8C AA 01 00`
  previous topic offset = `$019D45`, current target offset = `$01AA8C`, so
  `delta = $0D47`

Examples from `M602_200.HLP`:

| Stored entry bytes              | Raw target | Target file offset | Target context |
|---------------------------------|------------|--------------------|----------------|
| `A2 01 0A 00 F2 01 00 00`       | `$0A00`    | `$01F2`            | `3`            |
| `44 08 29 A0 00 A4 00 00`       | `$29A0`    | `$A400`            | `45`           |
| `47 0D 1E 79 8C AA 01 00`       | `$1E79`    | `$01AA8C`          | `120`          |
| `DC 10 F7 07 68 BB 01 00`       | `$F707`    | `$01BB68`          | `121`          |

The final tail row is special:

| Stored entry bytes              | Meaning                        |
|---------------------------------|--------------------------------|
| `9E 00 C9 00 BD 22 02 00`       | sentinel: count + EOF pointer  |

Observed interpretation of the final row:

- `delta = $009E`
- `raw_target_swapped = $00C9` -> reused here as total tail-entry count
- `target_offset = $000222BD` -> exact EOF offset

This exact tail index resolves all `119` unique inline raw targets observed in
`samples/602/M602_200.HLP`, without needing label/title heuristics.

If the binary tail is unavailable, `hlx2html` can still fall back to visible
label/title matching, but that is only a compatibility heuristic for source-only
HLX dumps, not the canonical decoder for compiled M602 `.HLP`.

## 3.8 Character Encoding

Bytes `$20`–`$7E` are standard ASCII. Bytes `$80`–`$FF` use Kamenický
(KEYBCS2), a Czech/Slovak DOS encoding.

Selected mappings:

| Byte | Char | Byte | Char | Byte | Char | Byte | Char |
|------|------|------|------|------|------|------|------|
| $80  | Č    | $88  | ě    | $90  | É    | $98  | ý    |
| $81  | ü    | $89  | Ě    | $91  | ž    | $99  | Ö    |
| $82  | é    | $8A  | ó    | $92  | Ž    | $9A  | Ü    |
| $84  | ä    | $8B  | ö    | $97  | Š    | $9B  | Ř    |
| $85  | ů    | $8E  | Ä    | $9C  | ř    | $9D  | Ý    |
| $87  | č    | $8F  | Ć    | $9F  | ť    | $A0  | á    |
| $A1  | í    | $A2  | ó    | $A3  | ú    | $A4  | ň    |
| $A5  | Ň    | $A8  | š    | $A9  | ř    | $B5  | Á    |

Low CP437 graphic bytes can appear as visible text after record/link parsing.
Observed examples in body text are `$12` = `↕`, `$1E` = `▲`, and `$1F` = `▼`.
They are display glyphs, not additional formatting controls.

## 3.9 Topic Structure

Topics are implicit; there is no separate topic table in the XOR text stream.

Observed parsing rule:

1. A title record starts a new topic.
2. The following separator record belongs to the same topic and acts as the
   visible underline below the title.
3. All subsequent body records belong to that topic until the next title record
   or the binary tail start.

In `M602_200.HLP` this yields:

- `201` topics
- 1-based topic numbering in parse order
- `context_id = 1` for the first topic, `context_id = 201` for the last topic
- every observed topic begins with exactly two visible lines:
  title text, then a separator line made of `$DF`

Practical consequences for parsers:

- `context_id` can be assigned sequentially in parse order
- a topic's `start_offset` is the body-stream offset of its title record
- a topic's `end_offset` is the next topic's `start_offset`, or the start of
  the binary tail for the last topic
- inline hyperlink targets are not topic numbers; they must be resolved through
  the binary tail index described above

Observed special case in `M602_200.HLP`:

- topic `1` is the error/help-fallback screen `Chyba`
- the first normal tail lookup row points to topic `2`, not topic `1`

This suggests that the first error screen is handled slightly differently from
the rest of the help topics in the compiled tail index.

## 3.10 What We Still Do Not Know

The following points are still open:

- the exact meaning of tail-header bytes `1..5` in
  `0F 27 1B 00 00 00`
- whether header byte `0F` is definitely a root/pivot count used by the
  original M602 viewer, or whether it has a slightly different role
- whether the number of XOR text records is stored anywhere explicitly in the
  `.HLP`, or only derivable by sequential parsing
- the exact semantic role of the final 8-byte sentinel row beyond the confirmed
  `entry_count + EOF` information
- whether all classic M602 `.HLP` files use the same tail layout, or whether
  there are older/newer sub-variants with a different header or sentinel shape
- whether `M602X.EXE` uses this tail strictly as a flat lookup table, or as a
  remnant of a higher-level search structure that is only partly visible in the
  compiled `.HLP`
