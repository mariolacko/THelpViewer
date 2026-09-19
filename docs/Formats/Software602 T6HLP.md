# Software602 T6HLP Help Format

> Created: 2026-06-20 · Last updated: 2026-09-19

Used by: Text602 3.00.
Observed sample: `t602_300.hlp`, CRC32 `CCC3E5FB`.

This is a legacy Text602 format. It is not compatible with the later
`Text602 - help` / `Calc602 - help` chunk format used by Text602 3.10 and
Calc602.

## Detection

The file starts with an 11-byte ASCII signature:

```text
0A "T6HLP86278"
```

At offset `$0B` follows a little-endian 32-bit file size. In the observed
sample this is `$00018E7D`, exactly `102013` bytes.

## File Layout

```text
Offset  Size  Description
------  ----  -----------
0000    11    signature: 0A + "T6HLP86278"
000B    4     declared file size, uint32 LE
000F    1536  fixed 256-entry topic table
060F    ...   topic text blocks
```

The topic table starts immediately after the declared file size. It contains
exactly 256 entries. Each entry is 6 bytes:

```text
offset uint32 LE
size   uint16 LE
```

An entry with `offset = 0` and `size = 0` is unused. The logical context ID is
the table index plus one, so empty entries leave gaps in the context ID range.

For `t602_300.hlp` this yields:

- 256 table entries
- 191 non-empty topic entries
- first text block offset `$060F`

## Topic Text

Each topic table entry points to one topic block. A topic block is split into
records by byte `$00`. Each non-empty record then contains one or more
physical screen rows encoded as:

```text
length uint8
text   length bytes
```

The length byte is part of the format, not visible text. It must be used to
split the record into rows. Do not treat punctuation-looking bytes between
sentences as text: they are often row length bytes for the next physical row.

Example from `Otevření`:

```text
2A "     Příkaz je určen pro otevření (načtení"
2E "z disku) pracovního textového souboru. Není-li"
2F "stávající (dosud editovaný) soubor uložen, bude"
2C "zobrazen dotaz, zda má být zapsán na disk či"
08 "nikoliv."
```

If the parser ignores the length model and decodes the bytes linearly, it will
produce bogus characters such as dots, slashes, commas, or digits inside words.

## Text Encoding

T6HLP uses the Software602 direct character table. Stored bytes are decoded
directly; unlike the newer `Text602 - help` format, there is no `-1` visible
byte transform.

The same high-byte overrides used by the repository's Text602/K602 decoders
apply here:

- `$C1` = `á`
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
| `$96` | display attribute byte, removed |
| `$97` | display/title attribute byte, removed |

The converter emits `$02` and `$04` spans as UHF `[b]...[/b]`. Attribute bytes
`$96` and `$97` are not visible text and are dropped.

Most topics start with a rendered help-window title and a short block-rule
line. The converter uses that title as the topic name and omits the decorative
header from the exported topic body.
