# Software602 K602 Help Format

> Created: 2026-06-20 · Last updated: 2026-06-20

Used by: Kartoteka 602 / K602.  
Observed sample: `K602.HLP`, CRC32 `17ADD07D`.

## Detection

The file starts with a Pascal-style 10-byte ASCII signature:

```text
0A "K6HLP86278"
```

At offset `$0B` follows a little-endian 32-bit file size. In the observed
sample this is `$0000CF7B`, exactly `53115` bytes.

## File Layout

```text
Offset  Size  Description
------  ----  -----------
0000    11    signature: 0A + "K6HLP86278"
000B    4     declared file size, uint32 LE
000F    ...   reserved/zero header area
0075    ...   fixed-width topic table
060F    ...   length-prefixed topic text records
```

The topic table begins at offset `$75`. It contains 6-byte entries:

```text
offset uint32 LE
size   uint16 LE
```

An entry with `offset = 0` and `size = 0` is unused. The table ends at the
first entry that cannot point to a valid text block. In `K602.HLP` this yields:

- `239` table entries
- `115` non-empty topic entries
- first text block offset `$060F`
- topic text blocks cover the rest of the file without gaps or overlaps

The logical context ID is the table index plus one. Empty table entries simply
leave unused context IDs.

## Topic Text

Each topic block is a sequence of one-byte length-prefixed lines:

```text
length uint8
text   length bytes
```

`length = 0` is a blank line. Lines continue until the topic entry's `size`
bytes are consumed.

## Text Encoding

K602 uses the Software602 direct character table. Unlike Text602/Calc602 help,
stored text bytes are not decremented before decoding. The same high-byte
overrides used by Text602 apply directly:

- `$C3` = `č`
- `$C5` = `ě`
- `$C9` = `í`
- `$CA` = `ů`
- `$D2` = `ř`
- `$D3` = `š`
- `$D7` = `é`
- `$D9` = `ý`
- `$DA` = `ž`
- `$E3` = `Č`

Software602 box drawing bytes also apply directly:

- `$C0` = `┌`
- `$C2` = `└`
- `$C7` = `─`
- `$E0` = `┐`
- `$E2` = `┘`
- `$E7` = `│`

Bytes not covered by the Software602 overrides fall back to Kamenicky/KEYBCS2.

## Inline Attributes

Observed inline formatting markers:

| Byte | Meaning in converter |
|------|----------------------|
| `$02` | highlighted text toggle |
| `$04` | highlighted text toggle |
| `$97` | title/attribute byte when adjacent to `$02`/`$04`, or trailing line attribute |
| `$96` | trailing line attribute/shadow byte |

The converter emits `$02` and `$04` spans as UHF `[b]...[/b]`. `$97` is removed
only when it is adjacent to a highlight marker or at the end of a line. `$96` is
removed only at the end of a line. This preserves literal byte values in the
K602 keyboard/character tables while dropping title artifacts such as a bogus
trailing `Ú`.

Low CP437 glyph bytes can appear in text, for example arrow symbols in key
descriptions. `$0D` inside `<...>` key descriptions is rendered as `↵`.
