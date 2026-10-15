# Scorpion's Cheater DAT

Main format: the latest verified DOS DAT branch, Scorpion's Cheater v23.
The same modern Allegro-backed DAT family is used by v15, v16, v21, and v22.

Files: `CHEATY.DAT`, `NAVODY.DAT`, `PROGRAM.DAT`, `VTIPY.DAT`,
`EASTER.DAT`, and v21 `TEXTY.DAT`.

## Container identity

The Allegro-backed DOS DAT family uses password-protected Allegro datafiles
with per-object LZSS compression and Kamenický/KEYBCS2 article text.
`ICONA.DAT` is a Windows icon resource, not an article container.

## Corpus

All Allegro-backed DAT files in the local corpus use the same old-crypt
password:

- raw on-disk magic: `12 1E 03 2D`
- old-crypt password: `akrab`
- decoded Allegro packfile magic: `slh.`
- top-level compression: none
- object compression: all 579 `DATA` entries are Allegro LZSS streams

No alternative old-crypt password was observed in the lower modern DAT branch
(`v15` / `v16`) or anywhere else in the current local DAT corpus. Pre-DAT
Scorpion releases are legacy container families rather than differently
passworded Allegro files.

### v23

`Objects` is the Allegro object count. `DATA` is the count of Allegro `DATA`
objects before article/resource filtering.

| File | Objects | DATA | Contains |
|---|---:|---:|---|
| `CHEATY.DAT` | 33 | 32 | Cheat/code articles |
| `EASTER.DAT` | 10 | 9 | Easter eggs and bonus/misc articles |
| `NAVODY.DAT` | 47 | 46 | Walkthroughs and guides |
| `PROGRAM.DAT` | 26 | 25 | Program/editorial/help text plus non-topic resources such as fonts and screens |
| `VTIPY.DAT` | 17 | 16 | Jokes |
| `ICONA.DAT` | - | - | Windows icon resource, not an Allegro article container |

## Allegro Container

Scorpion uses old-crypt password `akrab` and restarts the password cursor
at each compressed object payload.

The root layout after the first four old-crypt bytes is standard Allegro:

```text
12 1E 03 2D 41 4C 4C 2E ...
            A  L  L  .
```

After old-crypt decoding, the first four bytes are Allegro `slh.`. `ALL.` is
followed by a big-endian object count and Allegro objects.

Normal text-bearing objects have this shape:

```text
prop DATE <len> <timestamp>
prop NAME <len> <record name>
prop ORIG <len> <source path>
DATA
big-endian 32-bit packed_length
big-endian signed 32-bit unpacked_size
payload[packed_length]
```

`unpacked_size < 0` means that `payload` is Allegro LZSS-compressed and should
decompress to `-unpacked_size` bytes. In the modern corpus all `DATA` objects
use this path. With a nonnegative `unpacked_size`, both lengths must be equal;
zero denotes an empty object only when `packed_length` is also zero. It is
not an unspecified-size flag for a populated object.

The last object is usually Allegro grabber metadata named `GrabberInfo`.

## Old-crypt and object decompression

For password bytes `p = 61 6B 72 61 62` (ASCII `akrab`):

```text
mask = XOR(p[i] << (8*(i mod 4)), for each password byte)
decoded_magic = u32be(raw_magic) XOR mask
```

Here `mask = 61726B03h`, so raw `12 1E 03 2D` becomes `slh.`.
The uncompressed root contains `ALL.` at offset 4 and a big-endian object
count at offset 8. Property and object headers are not encrypted.

Before an object type, zero or more properties have this layout:

| Relative offset | Size | Meaning |
| --- | ---: | --- |
| `+0` | 4 | ASCII `prop` |
| `+4` | 4 | Property ID: `NAME`, `DATE`, `ORIG`, etc. |
| `+8` | 4 | Big-endian property byte length |
| `+12` | length | Raw property value |

The following object header is:

| Relative offset | Size | Meaning |
| --- | ---: | --- |
| `+0` | 4 | ASCII type, for example `DATA` |
| `+4` | 4 | Big-endian nonnegative packed byte length |
| `+8` | 4 | Big-endian signed unpacked length; negative selects LZSS |
| `+12` | packed length | Object payload |

For Scorpion old-crypt LZSS, initialize a zero-filled 4096-byte circular
dictionary, write cursor 4078, and password cursor zero per object.
Read flag bytes LSB-first, eight tokens per flag. XOR **only flag bytes**
with the next repeating password byte; literal and match bytes are not XORed.

- Flag bit 1: read one literal; append it and write it to the dictionary.
- Flag bit 0: read `a,b`; source index is `a | ((b & F0h) << 4)`,
  length is `(b & 0Fh)+3`. Copy that many dictionary bytes to output
  and dictionary.
- Dictionary cursors wrap with `& 0FFFh`. Update after each copied byte
  so overlapping matches can consume newly written bytes.
- Stop at the absolute declared unpacked length; input exhaustion before that
  many output bytes is truncation.

### Container boundaries and validation

The object count includes actual objects, not the preceding `prop` entries.
Every property header, property value, object header and packed payload must
fit in its containing object-list byte range. `packed_length` is nonnegative
and is the physical distance to the next object's property/type header; never
extend a short LZSS stream into that following object to satisfy its logical
length. All declared root objects must exist, and the completed list must end
at the container's end.

An Allegro `FILE` object contains a big-endian 32-bit child count followed by
child objects with the same grammar. Parse that list inside the decoded FILE
payload, not in the parent's remaining bytes. Its property/payload bounds and
final position are relative to this decoded range. A parent's compressed or
uncompressed length is validated before parsing its children.

With a known logical length, a final match token can be limited to the bytes
still requested. Unread packed bytes inside that object's declared physical
range are skipped at chunk close; they are not an extra article or another
object. Conversely, a partial flag/literal or two-byte match that cannot
supply the remaining decoded bytes is incomplete. A zero-length resource is
valid; a nonzero-length resource containing no packed data is not.

Example without password encryption:

```text
44 41 54 41  00 00 00 04  FF FF FF FD  07 41 42 43
DATA         packed=4    unpacked=-3  flags, A B C
```

This object expands to three bytes. Replacing `FF FF FF FD` by
`FF FF FF FC` declares four decoded bytes but still supplies only three:
the physical header/payload fits, yet the LZSS object is truncated. Returning
the three-byte prefix as a complete object would lose source data.

## Article Stream

After old-crypt + LZSS, article payloads are direct Scorpion text streams.
They contain literal article markers, CR/LF line breaks, Czech DOS text, and
inline formatting bytes.

Examples of article markers:

- `CHEATY.DAT`: `[3001]`, `[L002]`, `[9001]`
- `NAVODY.DAT`: `[N001]`
- `PROGRAM.DAT`: `[R010]`, `[R201]`, `[R222]`

The text encoding is Kamenicky / KEYBCS2, not CP852. For example, bytes in
v23 `CHEATY.DAT / ch05` decode as:

```text
[3001]
A F T E R L I F E
Následující kódy napište v průběhu hry:
   ≡$@! φ    - přidá deset miliónů (funguje jen 4x - po páté jste mrtví!)
```

The words `napište`, `přidá`, and `průběhu` are correct under Kamenicky. CP852
renders the same bytes as mojibake such as `napiĘte`, `pęidá`, and `prľbłhu`.

## Inline Formatting

Formatting bytes are not printable text even though a raw Kamenicky decode maps
them to glyphs such as `≡`, `φ`, `⌠`, and `⌡`. In the original DOS renderer
they switch text-attribute or layout state.

| Byte | Meaning |
|---:|---|
| `0x09` | fixed eight-space tab/spacer |
| `0x0D 0x0A` | line break |
| `0xE5` | gray background; context-sensitive literal `ň` in two v15/v16 text records |
| `0xE6` | modern DAT background reset |
| `0xE7` | dark-blue foreground |
| `0xE8` | green emphasis / secondary value |
| `0xE9` | cyan label / value |
| `0xEA` | dark-red foreground |
| `0xEB` | dark-magenta foreground |
| `0xEC` | orange foreground |
| `0xED` | reset current foreground attribute |
| `0xEE` | dark-gray foreground |
| `0xEF` | bright-blue foreground |
| `0xF0` | green code / emphasis span |
| `0xF1` | cyan section span |
| `0xF2` | red warning / emphasis span |
| `0xF3` | magenta foreground |
| `0xF4` | yellow value / highlight span |
| `0xF5` | white key / meta span |
| `0xF6` | end blue-background span |
| `0xF7` | begin blue-background span |
| `0xF8` | literal degree sign `°` |
| `0xFA` | visible line/page separator |

In the modern DAT family only, `0xE6` is also a background reset. It replaces
the legacy `0xF6` terminator in otherwise identical inherited table rows.

The foreground controls form a continuous DOS/CGA palette sequence. `0xE7`
through `0xEC` select colors 1 through 6, `0xED` resets to the default color,
and `0xEE` through `0xF5` select colors 8 through 15. `0xF7` temporarily sets
the background to blue / CGA 1 and `0xF6` restores the black background.

### Attribute state and ambiguous character values

Foreground controls `E7..EC` map to CGA 1..6, and `EE..F5` to CGA 8..15.
`ED` restores the default foreground. Background controls are independent:
`F7` selects CGA 1, `E5` selects CGA 7, and legacy `F6` restores black.
The Allegro-backed DAT text also uses `E6` as background reset.

For example, `F7 F0 NANCY F6 ED` displays bright-green text on dark blue.
A block-art sequence `F5 DC E5 DC DB DB F6` changes the background to gray
while retaining white foreground.

Some byte values collide with text characters. Two v15/v16 TOPGUN records
store `kampa E5 ,`, where the intended word appears to be `kampaň,`.
Whether this is an escaped literal or malformed inherited text is not fully
established. Do not derive a universal grammar from an alphanumeric-neighbor
heuristic. Likewise, v3-family `EE` can occur inside words such as
`D EE F EE N D EE R`; this case needs to be distinguished from a color control.

### Other text bytes

Additional byte interpretations:

| Byte | Meaning |
|---:|---|
| `0xE0` | literal `ŕ` |
| `0xFB` | context-sensitive: invisible pre-CR/LF terminator, otherwise literal `ü` |
| `0xFC` | literal `ü` |
| `0xFD` | literal `ř` |
| `0xFE` | hard space separator |
| `0xFF` | non-breaking / layout space, not an ordinary breakable space |

## Non-text Resources

### Inline text-mode artwork

Pictures visible inside articles such as v10/v14 `PROGRAM / R010` are not
bitmaps. They are part of the article text stream and use the original DOS
80-column character grid:

- spaces position each cell horizontally
- CP437/Kamenicky block and box characters such as `▄`, `▀`, `█`, `▌`, and
  `▐` provide the visible pixels
- inline attribute controls select the foreground and background CGA colors
- every source line is one row of the picture

The source is character cells plus attributes, not a raster image. Bytes such
as `D2` and `99` can be redefined by the selected bitmap font; ordinary
CP437 Unicode names do not establish their visible glyph shape.

This applies only to artwork embedded in readable article streams. It does not
automatically decode the separate resource records and files described below.

### Bitmap font resources

The DOS releases use real 8 x 16 monochrome bitmap fonts. A decoded font is
exactly 4096 bytes:

```text
256 character codes x 16 scanlines x 1 byte = 4096 bytes
```

Glyph `code` starts at `code * 16`. Its 16 bytes are the scanlines from top to
bottom; bit 7 is the leftmost pixel and bit 0 is the rightmost pixel. A set bit
uses the cell foreground color and a clear bit uses the background color. This
is sufficient to export the resource as a raw DOS font, a PSF/BDF font, or a
16 x 16 PNG glyph atlas. A minimal PSF1 export consists of header bytes
`36 04 00 10` followed by the 4096 decoded font bytes. The byte-to-Unicode map
must still follow the Cheater/Kamenicky character assignment when the font is
used for normal text.

#### v4-v8: uncompressed `FA.SCO`..`FF.SCO` and `FOK.SCO`

Each file is 4223 bytes. The final 4096 bytes are the complete raw 8 x 16 font;
the preceding 127 bytes form a DOS COM font installer and metadata. In the
verified v4–v8 files:

| File offset | Size | Meaning |
|---:|---:|---|
| `00` | 2 | `EB 67`: jump to installer at file offset `69` |
| `02` | 1 | `90`: NOP |
| `03..68` | 102 | Metadata/padding; glyph height at `0C` is 16; other fields unverified |
| `69..7E` | 22 | BIOS font installer and DOS return |
| `7F` | 4096 | 256 consecutive 16-byte glyphs |

Loaded as a COM at segment offset `0100`, the installer sets AX=`1110`,
BH=`byte[010C]` (16 scanlines), BL=0 (font block), CX=`0100` (256 glyphs),
DX=0 (first glyph) and BP=`017F` (bitmap address). `INT 10h` loads this
ES:BP font, followed by `INT 20h` to return. This is an executable font
installer, not a file with a 127-byte bitmap header to pass to the BIOS.
Extraction therefore needs no decompressor:

```text
font = file_bytes[len(file_bytes) - 4096 :]
assert len(font) == 4096
```

This framing is verified for the 4223-byte files only: the bitmap begins at
offset `0x7F`. A different length/header requires its own profile; do not
silently treat an arbitrary file's last 4096 bytes as a font.

#### v10-v14: compressed `FONT.SCO`

Versions 10 through 14 contain the same byte-identical `FONT.SCO` (SHA-256
`785a87b1d019705d208b70f82f629832dd1ac8fc06e9c6b81fe006548654f65d`).
It contains seven consecutive records. Each record has this observed frame:

```text
"FNT"                         3-byte marker
unpacked_size                 little-endian uint32; always 4096
compressed font payload       continues up to the next "FNT" marker or EOF
```

The record offsets in the shared file are `0`, `1451`, `2940`, `4348`, `5850`,
`7573`, and `9070`. The corresponding compressed payload lengths are `1444`,
`1482`, `1401`, `1495`, `1716`, `1490`, and `1461` bytes.

Each payload uses the same adaptive-Huffman/LZSS decoder as the text and
text-screen blocks, specified below. There is no font-specific transform.
NUL bytes are ordinary Huffman literals: their leaf at initial tree index
zero must be updated too. Skipping that update desynchronizes the tree and
produces plausible but incorrect glyph bytes very early in a font.

Records are numbered `0` through `6`: `0` is the standard/restoration font,
then `1` through `6` are the selectable A through F fonts. The program
installs index `1` before its initial text screen. For v4–v8 the corresponding
default font is `FA.SCO`, not `FOK.SCO`. Screen templates and article artwork
inherit the selected font; their names do not independently select fonts.

#### v16 and v21-v23: Allegro DAT font records

`PROGRAM.DAT` stores `FONT1`..`FONT7`, `FONTKRUH`, and `FONTOK` as Allegro
`DATA` objects. First apply the normal modern DAT recipe: old-crypt password
`akrab`, then Allegro object LZSS decompression using the negative unpacked
size. The resulting payload of every font record is already the complete raw
4096-byte 8 x 16 font described above; no additional font codec is applied.
Version 15 uses positional names instead: `obr4`..`obr10` are `FONT1`..`FONT7`,
`obr11` is `FONTKRUH`, and `obr12` is `FONTOK`. All nine decoded resources
are byte-identical to the corresponding version-16 resources. These `obr*`
records are fonts, not 80×25 screens.

The modern records also confirm why a normal CP437 Unicode conversion cannot
reconstruct every inline picture. For example, glyph byte `0xD2` is a curved
tail fragment in the program font although CP437 names that code `╥`; glyph
`0x99` varies by selected font and can be a filled picture cell although CP437
names it `Ö`.

Legacy releases also store complete presentation screens outside the article
streams. The current corpus confirms two distinct decoded layouts:

- `SCREENS.SCO` and `SCR*.SCD` use the same LZHUF compression as the v6-v14
  text libraries. Their payload is exactly 4000 bytes: 80 columns x 25 rows x
  two bytes per cell. Each cell contains a CP437/Kamenicky character followed
  by its VGA text attribute. These resources include complete title/menu
  screens with the CHEATER logo, version, authors, menu labels, and controls.
  `SCR*.SCD` starts at offset zero with the LE uint32 unpacked size `4000`.
  `SCREENS.SCO` contains eight consecutive records, each with a three-byte
  `SCR` marker followed by that size and one compressed payload. There is no
  count field or per-record compressed length. Glyph and attribute layout is
  the same as the modern text-screen cells below. The v6 `SCR1`, `SCR2` and
  `SCR6` attributes include bit 7. The file has no flag selecting its meaning;
  the active VGA attribute-controller mode determines blink versus background
  intensity, as described below. Never discard the bit.
- `SCR*.SCX`, `SP.SCX`, and `XMAS.SCX` use LZHUF too, but decode to a four-byte
  little-endian `width, height` header followed by one indexed pixel byte per
  pixel. Observed files decode to `640 x 480` plus 307200 pixel indexes. They
  are raster screens, not ASCII art. Their original VGA palette still needs to
  be identified to assign original colors to the pixel indexes.

Besides article streams, modern DAT files also ship non-text resource records.
They are not article records merely because their object type is `DATA`.

#### Modern text-screen cells

A complete text screen is exactly 4000 decoded bytes. There is no header:

```text
offset = (y * 80 + x) * 2
byte[offset]     = glyph index in the selected 256-glyph bitmap font
byte[offset+1]   = VGA text attribute
foreground      = attribute & 0x0F
background      = (attribute >> 4) & 0x07
```

Coordinates start at `(0,0)` and rows run top-to-bottom. Spaces and zero
glyphs are cells too; do not trim the native margins or parse text-style
bytes such as `F0` as commands. A cell `F0 1E` draws font glyph 240 with
yellow foreground (CGA index 14) and blue background (index 1).

Attribute bit 7 depends on the native VGA blink/bright-background mode.
With blink enabled, background is `(attribute >> 4) & 7`; bit 7 marks a
blinking foreground. During the hidden phase, keep the background and omit
only the glyph's foreground pixels. With blink disabled, background is
`(attribute >> 4) & 15`, and bit 7 supplies its intensity bit. For example
`44 87` is blinking gray `D` on black in the first mode, but static gray `D`
on dark-gray background in the second. No bit in the stored screen itself
chooses between these meanings. Standard DOS text mode uses blinking;
an inherited alternative VGA mode must be recorded separately by a decoder.
All observed modern screen cells have bit 7 clear; v6 templates retain it
on DEMO/registration captions. The other colors use the ordinary 16-color
CGA palette (black/blue/green/cyan/red/magenta/brown/light-gray followed by
the bright variants).

`PROGRAM.DAT` resource bindings differ by layout:

| Screen role/name (v16, v21–v23) | Positional name in v15 |
|---|---|
| `_main` | `obr1` |
| `egg` | `obr3` |
| `obr1`..`obr4` | `obr15`..`obr18` |
| `obrview` | `obr19` |
| `scroll` | `obr21` |
| `xicht` | `obr24` |
| `pirat` (v21–v23) | absent |

The native font selection values are `1`..`7` for `FONT1`..`FONT7`,
`8` for `FONTKRUH`, and `0` for `FONTOK`. The program initializes the
selected value to `1`. Screen backgrounds inherit the selected font;
the default resource view therefore uses `FONT1`, not a Unicode/font
guess based on its caption. These objects include background templates:
version/date fields and live menus can be filled by the program afterward,
and are not missing bytes in the stored screen.

Observed resource families in the current corpus:

- `_main`, selected `obr*`, `obrview`, `xicht`, `pirat`, `egg`, `scroll` —
  the complete text-cell screens identified above; a name prefix alone does
  not distinguish screens, fonts, text indexes and version/date metadata
- `FONT1..FONT7`, `FONTKRUH`, `FONTOK` — Allegro-compressed objects whose
  decoded payloads are raw 4096-byte 8 x 16 bitmap fonts
- `datum*`, `rok*`, `seznam*`, `verze*`, `library*`, `Librar`, `update_ini` — metadata / library helper records

## Index And Marker IDs

Square-bracket strings such as `[N001]`, `[L002]`, `[R222]`, or `[3001]` are
link target IDs, not display titles. Their meaning depends on the source
library and index that references them.

Observed index row grammar in readable branches:

```text
LABEL,[TARGET]FLAG
```

The same target syntax is used by modern DAT `seznam*` resources, v3/v3.5
`SCC.SC`, and v4/v5 `DATAA.SCO` / `DATAB.SCO`. `FLAG` is a status marker in
the index row; it is not part of the target ID.

Target prefix rules observed in the local corpus:

| Target form | Meaning |
|---|---|
| `Rnnn` | Program/editorial/help page target. These appear in `PROGRAM.DAT`, all modern `seznam*` menus, v4/v5 `DATAHELP.SCO`, and v4/v5 `DATATEXT.SCO`. |
| `Nnnn` | Manual/walkthrough target when used by guide libraries such as `NAVODY.DAT`, v3 `NAVODY.1`, or v4/v5 `DATAN1.SCO`. In modern `CHEATY.DAT` v21+ the same prefix is also reused as a cheat overflow block, so `N` alone is not enough to classify a topic. |
| `Mnnn` | Extra/multi cheat block. v3.5 stores this in `MULTI.1`; v4/v5 stores the same family in `DATA5.SCO`; modern DAT keeps it as one cheat block inside `CHEATY.DAT`. |
| `0000`..`9999` | Numeric targets. Used for older cheat blocks, jokes, Easter eggs, and many index rows. The containing file/section decides the content type. |
| `Annn`, `Bnnn`, ... | Cheat namespace blocks used after the numeric ranges are exhausted or split into later import batches. The letter is not the first letter of the game title. |
| `fórů` | Header target in joke indexes; not a topic target. |

There are version-specific exceptions. In v4/v5 `DATAA.SCO`, `P001` and
`P002` are save-editor entries and `O001` is `Dungeon Master 2 - kouzla`;
in modern DAT, `O...` and `P...` are ordinary cheat namespace blocks. This is
another reason to keep the source file role in the classifier.

Modern DAT `seznam*` resources confirm the split:

- `PROGRAM.DAT / seznam` lists program pages (`R...`) plus cheat targets.
- `NAVODY.DAT / seznamN` lists program pages (`R...`) plus guide targets
  (`N...`).
- `VTIPY.DAT / seznamJ` lists program pages (`R...`) plus numeric joke
  targets.
- `EASTER.DAT / seznamE` lists program pages (`R...`) plus numeric Easter-egg
  targets.

The first target character alone does not identify the content section.
Its namespace is scoped by the source library and parsed index role.

## Modern DAT Extractor Recipe

This is the primary format documented by this file. It covers the verified
Allegro-backed branch used by v15, v16, v21, v22, and v23.

Detection:

- accept article DAT names such as `CHEATY.DAT`, `NAVODY.DAT`, `PROGRAM.DAT`,
  `VTIPY.DAT`, `EASTER.DAT`, and v21 `TEXTY.DAT`
- require raw bytes to start with `12 1E 03 2D`
- reject known non-article resources such as v23 `ICONA.DAT`

Container extraction:

1. Enable Allegro old-crypt with password `akrab`.
2. Decode the packfile header. The encrypted on-disk bytes become Allegro
   `slh.` and the following container starts with `ALL.`.
3. Parse the big-endian object count after `ALL.`.
4. For each object, read Allegro properties. The useful properties are
   `DATE`, `NAME`, and `ORIG`.
5. Read the `DATA` object payload as:
   `packed_length:u32be`, `unpacked_size:i32be`, `payload[packed_length]`.
6. If `unpacked_size < 0`, decompress the payload with Allegro LZSS to
   `-unpacked_size` bytes. In the verified corpus every article `DATA` record
   uses this compressed path.
7. Treat `GrabberInfo` and known resource names as metadata or resources, not
   article text.

Article extraction:

- decode article bytes as Kamenicky / KEYBCS2
- normalize CR/LF to lines, preserving source blank lines inside articles
- split articles at marker lines in square brackets, for example `[3001]`,
  `[L002]`, `[N001]`, `[R201]`
- do not split on formatting/control tokens that are not real markers
- the first non-empty content line after a marker is the topic title
- retain the marker as the source's local article ID
- interpret foreground/background state according to the inline-format table
  before decoding remaining character bytes

Resource handling:

- `obr*`, `obrview`, `xicht`, `pirat`, `egg`, and `scroll` are compressed
  text-mode screens or presentation assets
- `FONT1..FONT7`, `FONTKRUH`, and `FONTOK` decode to raw 4096-byte 8 x 16
  bitmap fonts as described in the resource section above
- `datum*`, `rok*`, `seznam*`, `verze*`, `library*`, `Librar`, and
  `update_ini` are metadata/helper records
- these records must not become normal help topics

## Legacy Formats

Legacy here means every branch below the main v23 corpus: the older modern DAT
releases v15-v22 and the pre-DAT container families v1-v14.

### Modern DAT Legacy Branch v15-v22

These releases use the same Allegro old-crypt DAT container and the same
extractor recipe as v23. Their tables are kept here because v23 is the primary
documented DAT version.

#### v15

| File | Objects | DATA | Contains |
|---|---:|---:|---|
| `CHEATY.DAT` | 22 | 22 | Cheat/code articles |
| `EASTER.DAT` | 9 | 9 | Easter eggs and bonus/misc articles |
| `NAVODY.DAT` | 25 | 25 | Walkthroughs and guides |
| `PROGRAM.DAT` | 24 | 24 | Program/editorial/help text |
| `VTIPY.DAT` | 16 | 16 | Jokes |

#### v16

| File | Objects | DATA | Contains |
|---|---:|---:|---|
| `CHEATY.DAT` | 22 | 22 | Cheat/code articles |
| `EASTER.DAT` | 9 | 9 | Easter eggs and bonus/misc articles |
| `NAVODY.DAT` | 25 | 25 | Walkthroughs and guides |
| `PROGRAM.DAT` | 24 | 24 | Program/editorial/help text |
| `VTIPY.DAT` | 16 | 16 | Jokes |

#### v21

| File | Objects | DATA | Contains |
|---|---:|---:|---|
| `CHEATY.DAT` | 32 | 31 | Cheat/code articles |
| `EASTER.DAT` | 10 | 9 | Easter eggs and bonus/misc articles |
| `NAVODY.DAT` | 47 | 46 | Walkthroughs and guides |
| `PROGRAM.DAT` | 26 | 25 | Program/editorial/help text |
| `TEXTY.DAT` | 6 | 5 | SC 2000 text/catalog records, without DOS article markers |
| `VTIPY.DAT` | 17 | 16 | Jokes |

The v21 `TEXTY.DAT` has five DATA names: `kontakt`, `novezpra`, `oprogramu`,
`spoluaut` and `txt`. The first four begin with angle-bracket controls such
as `<!K=1><!M=1>Kontakt<!M!>`; they are not ordinary DOS `[Rnnn]` articles.
The `txt` record starts with an SC 2000 catalog heading and uses `#` title
lines followed by comma-separated resource descriptors. This is a different
text grammar inside the same Allegro container. Its control operands,
links and catalog-field meanings are not established here. Container
decompression alone does not determine how those records should be displayed.

##### SC 2000 companion text: observed byte syntax

The four prose objects are CR/LF byte text with inline ASCII tokens bounded
by adjacent `3C 21` (`<!`) and `3E` (`>`). A space between `<` and `!`
changes the byte sequence: the explanatory examples spelled `< !J=1>` in
`novezpra` are ordinary source text, not active `<!J=1>` tokens. An apparent
DOS marker such as `[R010]` inside this angle-bracket grammar does not switch
the object to the separate DOS article grammar. Observed token forms are:

| Token prefix | Observed forms | Established meaning |
| --- | --- | --- |
| `K` | `<!K=1>`, `<!K=3>` | Integer operand; display semantics unknown |
| `M` | `<!M=1>`, `<!M=2>`, `<!M=4>`, `<!M!>` | Font macro; end form restores the previous font; exact macro table unknown |
| `F` | `<!F=9>`, `<!F=10>`, `<!F=13>` | Font selector, not the DOS foreground-color alphabet; selector 20 is described as Wingdings; exact font resources unknown |
| `L` | `<!L=40,63,665,63,1>`, `<!L=40,64,665,64,1>` | Five comma-separated integers; coordinate/attribute semantics unverified |
| `U` | `<!U>`, `<!U!>` | Underline start/end; must be ended before the physical row ends |
| `J` | `<!J=1>`, `<!J!>` | Justified text start/end; exact wrapping/font metrics unknown |
| `B` | `<!B=4>` | Integer operand; behavior unverified |
| `X` | `<!X=1,2>`, `<!X!1>` through `<!X=11,5>`, `<!X!11>` | Relative text link: zone number, destination page; end form repeats the zone number; native page-to-text binding unknown |
| `?` | `<!?>` | REM: skip its physical row; not a page-break command |

These meanings are explicitly described in the embedded `novezpra` text.
The `!` forms are not XML closing tags, and `<!?>` is not an ordinary
letter-named command. A scanner must preserve unknown tokens and bytes;
recognizing an `X` token alone does not establish a text-row destination.
The graphical consumer uses an 800 x 600 pixel display; pagination depends
on its chosen font and wrapping, not a fixed count of DOS text rows. Related
documented controls (not present in these four prose objects) are:

- `<!A=zone,file,page>` / `<!A!zone>`: text link to a page in another file.
- `<!Z=zone,x1,y1,x2,y2,page>`: absolute rectangular link zone.
- `<!O=...>`: absolute picture placement; its complete operand order is
  not established here. An X coordinate of `999` centers the picture.
- `<!W=filename,x>`: picture at the current text row; `999` centers it.
- `<!PP=directory>` and `<!PT=directory>`: picture/text default directory.
- `<!H=x1,x2,color>`: relative horizontal separator.
- `C`: centering; the embedded description requires the tag at the
  beginning of the physical row, but does not specify its complete operand
  syntax. Exact horizontal bounds/font metrics are also unknown.
- `<!S>`: text/picture shadow; the description places it before a row, word
  or picture. The description also mentions using `<!S>` to end text
  shadowing; its exact toggle/state behavior is unverified.
- `<!BB=color>`: persistent color according to the embedded description;
  the numeric color table and its interaction with `B` are unknown.
- `<!DT=zone>` / `<!DT!zone>`: text Back zone; the end form repeats the
  zone number.
- `<!DP=zone,x1,y1,x2,y2>`: absolute rectangular Back zone. Coordinate
  bounds and history behavior require the consumer.

The embedded description calls byte `FEh` a text terminator, but its complete
recognition rule is unverified. In the retained `spoluaut` object, relative
decoded offset 665 (0299h) contains `FE 73 70 B0 9A 6E B0` inside a physical
prose row; more rows follow, and offset 1592 (0638h), the final byte, is also
`FE`. This could involve source defects or an encoding/font-specific rule;
the bytes alone do not establish which. Do not use the first `FE` to truncate
an Allegro DATA object: container extraction uses the declared decoded size.
The separate catalog's observed tail rule is specified below.

The documented `M!` behavior is to restore the preceding font, not always
the default font. Do not map `F` numerals directly to VGA palette colors.
The DOS control-byte alphabet above does not establish this grammar's font
or character assignment. For example, `spoluaut` uses `F8h` inside the word
`Spoluato<F8h>i` at decoded offset 20 (0014h), where interpreting it as the
DOS degree-sign glyph would not recover the intended prose. Its prefix is
`<!K=3>`, whereas the other three objects begin `<!K=1>`. The numeric `K`
mapping has not been established. The title bytes fit Windows-1250, but
the later paragraph also has `ADh`, `B0h`, `B1h`, `D8h` and `FEh` in words
where one Windows-1250 pass does not recover ordinary Czech text. The font,
encoding and possible source-defect boundaries remain unknown. Do not infer
the prose encoding from the catalog's Windows-1250 text.

The `txt` catalog uses physical CR/LF lines and Windows-1250 text. Stop at
the first `FEh`; the observed tail contains two `FEh` bytes followed by CR/LF.
`#` (`23h`) introduces a title;
commas inside such a title are literal text, not descriptor separators.
Following item lines have observed forms such as:

```text
#1000 Miglia
--,1,4,0005-01,1000MIGL.COM,Trainer +8
#101st Airbone in Normandy
--,0,1,*,[B007],
```

Trailing empty fields are significant syntactically; they must not be
discarded by a field splitter. The first field is a two-byte form such as
`--`, `-*`, `-!` or `-b`. The next fields contain `0`/`1` and an alphanumeric
one-byte value. Remaining operands can include an archive-like identifier,
a literal filename, a bracketed DOS article ID or a description. Their
complete type/flag/lookup rules are not established by these examples.
The native cheat-export routine writes `#title` followed by
`-*,0,1,*,[marker],` from the CHEATY library. Thus six-field rows with type
`1`, resource address `*` and a bracketed four-byte marker use the CHEATY
namespace. The same marker in a joke or Easter library is not that target.
Rows naming `LIB`-style archive/member locations do not by themselves
establish a filesystem path to an attachment.

Short lines such as `-!,US Navy Fighters` have a different shape from the
six-field item rows; do not pad them with invented fields or interpret the
title after the comma as a DOS numeric context. The short form names another
catalog title verbatim. Repeated title captions must retain distinct physical
rows; resolving a caption without the original consumer's duplicate-selection
rule can be ambiguous. Other observed rows contain
seven fields, for example `-*,1,4,0029-05,trainer,zip,`. Whether the comma
between `trainer` and `zip` is malformed source or meaningful to the native
consumer is unknown; do not silently replace it with a period.

#### v22

| File | Objects | DATA | Contains |
|---|---:|---:|---|
| `CHEATY.DAT` | 32 | 31 | Cheat/code articles |
| `EASTER.DAT` | 10 | 9 | Easter eggs and bonus/misc articles |
| `NAVODY.DAT` | 47 | 46 | Walkthroughs and guides |
| `PROGRAM.DAT` | 26 | 25 | Program/editorial/help text |
| `VTIPY.DAT` | 17 | 16 | Jokes |

### Legacy v1.x

Observed files:

| Version | File | Contains / status |
|---|---|---|
| v1.0 | `DATA.DAT` | DOS MZ/RAR SFX wrapper; `MENU2.EXE` inside the archive contains menu/help text and cheat topics |
| v1.5 | `CHEATER.EXE` | PKLITE-packed DOS executable with embedded menu/help text, author names, and cheat topics |
| v1.5 | `CS.EXE` | Helper executable/resource; skipped, not a help corpus |

#### v1.0 `DAT` wrapper

Detection:

- accepted suffix is `.DAT`
- file starts as a DOS MZ executable or otherwise contains an embedded RAR4
  signature `52 61 72 21 1A 07 00`

Container extraction:

1. Parse the DOS MZ image size from header fields at `0x02`, `0x04`, and
   `0x08`.
2. If bytes after the computed MZ image start with RAR4 signature, treat them
   as the overlay. Otherwise scan the file for the RAR4 signature and use the
   first embedded archive.
3. Parse RAR4 file headers (`0x74`) and directory attributes (`0x10`). A
   full extractor can either implement RAR decompression or delegate the overlay
   to a RAR-capable tool.
4. Extract `MENU2.EXE`; it contains the useful help/menu string table.

Text extraction:

- split the extracted executable region on `NUL`
- decode each string as Kamenicky / KEYBCS2
- normalize CR/LF sequences to `\n`
- find the intro by prefix `SCORPIONS CHEATER V.1.00`
- find controls by prefix `Pro pohyb:`
- find the cheat topic stream starting at exact title `QUARANTINE`
- topic titles are all-uppercase rows; spaced titles are compacted, for
  example `B A T T L E` becomes `BATTLE`
- uppercase multi-column code-table rows remain in the previous topic body
- repeated title blocks mark the start of the directory/footer area and stop
  topic scanning
- internal blank lines are preserved; only leading/trailing empty rows are
  trimmed from a topic or section

#### v1.5 `CHEATER.EXE`

Detection:

- accepted suffix is `.EXE`
- `CS.EXE` is skipped; it is not a help corpus file for this branch
- the useful corpus is in `CHEATER.EXE`, typically PKLITE-packed

Container extraction:

1. Detect DOS MZ and PKLITE in the executable header.
2. Unpack the PKLITE stream to recover the original executable image.
3. Use the unpacked EXE payload as the string-table source.

Text extraction:

- split the unpacked payload on `NUL`
- decode strings as Kamenicky / KEYBCS2
- required anchors are `SCORPIONS  CHEATER V1.50`, `MENU PRO TISK`,
  `Pro pohyb:`, and footer prefix `Scorpions Cheater V1.5 -`
- scan any cheat topic stream before the main title using the same uppercase
  topic-title rules as v1.0
- the repeated-title directory may contain status prefixes:
  `Ř ` or `ⁿ ` means new, `! ` means renovated, and no prefix means plain
- the cheat stream stops before the footer/logo art immediately preceding the
  repeated-title directory; that art is not part of the last cheat topic
- directory titles are matched back to topic titles with spelling/roman numeral
  normalization and a small override table for known corpus typos
- internal blank lines are preserved by the section normalizer

### Legacy v3.x

Observed files:

| Version | File | Contains / status |
|---|---|---|
| v3.0 | `CHEATER.DAT` | RAR-overlay corpus; `NAVODY.1` manuals, `TEXTY.*` cheats, `VTIP*.SC` jokes, `SCC.SC` cheat index/order |
| v3.0 | `BLCK.DAT` | DOS COM-style binary/resource; skipped, not a help corpus |
| v3.5 | `CHEATER.DAT` | RAR-overlay corpus; same roles as v3.0 plus `MULTI.*` cheat/code streams |
| v3.5 | `MAIN.DAT` | Program/main-shell data/resource; skipped, not a help corpus |
| v3.5 | `BLCK.DAT` | DOS COM-style binary/resource; skipped, not a help corpus |

Versions 3 and 3.5 use a pre-SCO `.DAT` branch with an embedded RAR4 archive,
not the Allegro old-crypt DAT container. Text-bearing members are classified by
name:

- `NAVODY.1` is exported as manuals
- `TEXTY.*` members are exported as cheats
- v3.5 `MULTI.*` members are exported into the cheat bundle as the same kind
  of code/hack topic stream
- `VTIP*.SC` members are exported as jokes
- `SCC.SC` is used only as the cheat-section index and ordering source
- `BLCK.DAT` is skipped as a non-help resource/executable payload

Detection and archive extraction:

- accepted suffix is `.DAT`
- find a RAR4 overlay either after the computed MZ payload or by scanning for
  `52 61 72 21 1A 07 00`
- parse RAR4 file headers, normalize archive member paths, and extract members
  with a RAR-capable extractor

Topic parsing:

- decode member payloads as Kamenicky / KEYBCS2
- marker lines match `[A-Z0-9]{4}` in square brackets, for example `[0001]`
  or `[N001]`
- `END` closes the current topic
- the first normalized content line is the topic title unless `SCC.SC`
  supplies an override for cheat topics
- `SCC.SC` lines have the shape `LABEL,[MARK]flag`; only `TEXTY.*` and
  `MULTI.*` cheat topics receive these title/order overrides
- `SCC.SC` order is applied first for cheat topics; manuals, remaining cheats,
  jokes, and other parsed topics follow in source order

The marker string is the source article identifier. It does not contain a
numeric section-offset scheme or a JSON/bundle filename.

The `MULTI.*` classification is also supported by web copies of individual
entries. `ALONE IN THE DARK II` and `CHAOS ENGINE` both resolve to Cheater.cz
`cheat` articles, and `CLOCKWISER` appears as a cheat/password list rather than
as a walkthrough.

The v3 text contains formatting attribute bytes that would otherwise decode
as visible Kamenický glyphs. Web copies of the same texts show normal prose and
code lists without these symbols; for example `THE LEGεND OF KYRANDIA` is the
plain title `Legend of Kyrandia`, and the cave map embedded after `Plánek
jeskyně` is an image in the web article rather than printable `Φ` / `≡`
characters.

Observed v3/v3.5 glyph artifacts:

| Glyph | Byte | Meaning in v3 text |
|---|---:|---|
| `ε` | `0xEE` | context-sensitive: highlighted letter `E` inside English words such as `LEGEND`, `END`, `DEFENDER`; standalone line-prefix use is a formatting attribute |
| `φ` | `0xED` | reset / end of the current highlighted span |
| `≡` | `0xF0` | start of highlighted cheat-code or map text |
| `Φ` | `0xE8` | line / map / heading attribute; not printable text |

Other nearby high bytes in this branch, such as `±`, `≥`, `≤`, `⌠`, and `⌡`,
follow the same attribute-control pattern around codes and labels.

### Legacy v4.x / v5.x SCO

Versions 4 and 5 are the verified external `.SCO` library branch. Text
libraries begin with:

```text
53 43 4F 52 50 49 4F 4E 00 01
S  C  O  R  P  I  O  N  \0  \1
```

SCO Huffman layout:

| Offset | Size | Meaning |
|---:|---:|---|
| `0x000` | 10 | signature `SCORPION 00 01` |
| `0x00A` | 512 | 256 little-endian unsigned 16-bit code starts |
| `0x20A` | 256 | reserved/header gap before the stream |
| `0x30A` | rest | MSB-first Huffman bitstream |

Huffman decoding:

1. Read the 256 16-bit values at `0x00A`. Symbol `n` owns table value
   `table[n]`.
2. Sort pairs as `(start, symbol)`.
3. The interval end is the next sorted start, or `0x10000` for the last entry.
4. Each interval width must be a positive power of two.
5. Symbol bit length is `16 - log2(width)`.
6. Decode from bit offset 0 at stream offset `0x30A`, reading bits
   most-significant first.
7. At each step, peek the next 16 bits, choose the interval where
   `start <= value < end`, append that symbol byte, then advance by the
   selected symbol bit length.
8. Stop when fewer than 16 bits remain, no interval matches, or a chosen
   interval is inconsistent.
9. Decode output bytes as Kamenicky / KEYBCS2 and normalize CR/LF line breaks.

Readable decoded streams use two shapes:

- marker topic streams with lines such as `[0101]`, `[3001]`, `[M001]`,
  `[N001]`; each marker starts one topic, and the first content line is the
  title
- single-topic index streams with lines matching `LABEL,[target]flag`

SCO index entries:

| Flag | Status | Original list color |
|---|---|---|
| `-` | plain | white, CGA 15 |
| `*` | new | yellow, CGA 14 |
| `+` | updated | bright green, CGA 10 |
| `!` | supplement: editor, guide, map, or spell reference | white, CGA 15 |

Versions 8 and later store a second trailing flag of unknown purpose, producing values
such as `--`, `*-`, `+-`, and `!-`. The first character is the status shown by
the list color; the second character is not the status. A DOSBox capture of the
v14 list confirms `3D ULTRA RACE,[E089]*-` in yellow,
`FALCON 3.0,[4077]+-` in bright green, and ordinary `--` entries in white.
A DOSBox capture of v7 confirms that `!` is not a renovated-item status:
all seven such rows are auxiliary content (`save editor`, `návod`, `mapa`, or
`kouzla`) and are displayed in white. The selected row uses the normal blue
selection background and yellow selection text, independently of its flag.

The original v14 browser is a combined list, not a literal rendering of only
the `CHEATS.SCO` index. A DOSBox capture shows three adjacent variants:
`WARCRAFT II`, `WARCRAFT II (průvodce)`, and `WARCRAFT 2 (kouzla)`. The
parenthesized qualifier is white like an ordinary entry; it is a content-kind
disambiguator, not a status color. The external v14 `CHEATS.SCO` index contains
only `WARCRAFT II`, while `NAVODY2.SCO` contains no Warcraft row at all. The
two qualified Warcraft entries therefore appear to be synthesized from data
owned by `CHEAT14.EXE` or another runtime-only table. Their article payloads
are not present in the currently extracted SCO/SCD libraries.

The external manual index independently establishes the qualifier vocabulary
used from v12 through v14:

| Example target | Display label | Content kind |
|---|---|---|
| `N051` | `Diablo (průvodce)` | walkthrough/guide |
| `O001` | `Dungeon Master II (kouzla)` | spell reference |
| `O003` | `Ishar I (mapa)` | map supplement |
| `P001` | `Settlers II (save editor)` | save editor |

Do not classify these solely by the first target letter. `N` is mostly a
walkthrough namespace in this library, but `O` contains both spells and maps,
and later DAT releases reuse `N`, `O`, and `P` for ordinary cheat blocks. Keep
the explicit parenthesized label and the source-library role.

Index stream roles:

- `DATAA.SCO` contains the cheat index.
- `DATAB.SCO` or a header containing `[FÓRŮ]` identifies a joke index.
- Rows whose label starts with `SEZNAM` are headers, not game entries.

Verified v4 file roles:

| File(s) | Contains |
|---|---|
| `DATAA.SCO`, `DATA1.SCO`..`DATA6.SCO` | Cheat index plus cheat topic streams |
| `DATAB.SCO`, `DATAV1.SCO` | Joke index plus jokes |
| `DATAN1.SCO` | Manuals/walkthroughs |
| `DATAHELP.SCO`, `DATATEXT.SCO` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | Font/resource files; headers contain strings such as `SCORPIONS CHEATER 4.0 font A` |
| `SLEEPER.SCO` | DOS executable/helper |
| `SPELDATA.SCO` | Binary resource, not a `SCORPION 00 01` text library |

Verified v5 file roles:

| File(s) | Contains |
|---|---|
| `DATAA.SCO`, `DATA1.SCO`..`DATA7.SCO` | Cheat index plus cheat topic streams |
| `DATAB.SCO`, `DATAV1.SCO` | Joke index plus jokes |
| `DATAN1.SCO` | Manuals/walkthroughs |
| `DATAHELP.SCO`, `DATATEXT.SCO` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | Font/resource files |
| `SLEEPER.SCO` | DOS executable/helper |
| `SPELDATA.SCO` | Binary resource, not a `SCORPION 00 01` text library |

Non-text/resource filtering for this branch:

- `FA.SCO`..`FF.SCO`, `FOK.SCO`, and `FONT.SCO` are font/resource files; v4/v5
  font stubs contain strings like `SCORPIONS CHEATER 4.0 font B`
- `DRIVER.SCO`, `SCREENS.SCO`, `SLEEPER.SCO`, and `SPELDATA.SCO` are not help
  text
- `SLEEPER.SCO` starts with DOS `MZ`
- `SPELDATA.SCO` does not start with the `SCORPION 00 01` text signature
- `SP.SCX`, `XMAS.SCX`, and `SCR*.SCD` / `SCR*.SCX` screen banks are skipped
  as resources
- any `.SCO` that starts with DOS `MZ` or has a font header within the first
  128 bytes is skipped

### Legacy v6.x-v14.x SCO/SCD/SCX Profiles

These releases keep the broader SCO family but change the library naming and
introduce `.SCD` / `.SCX` split resources.

Text compression is the classic Okumura `lzhuf` stream:

- 4-byte little-endian unpacked size
- adaptive Huffman symbols over an LZSS 4096-byte ring buffer
- lookahead length `F=60`
- match threshold `2`
- the ring buffer is initialized with ASCII spaces
- matches are encoded as symbol `256..313` plus a position code whose upper
  6 bits use the fixed `p_len` / `p_code` table from `lzhuf.c`

#### Adaptive tree and position decoding

All compressed bits are read MSB first. Initialize 314 literal/match leaves
and 313 internal nodes; arrays are `freq[628]`, `child[627]` and
`parent[941]`. For `i=0..313`, set `freq[i]=1`, `child[i]=627+i` and
`parent[627+i]=i`. Then, with `j=0`, for `i=314..626`, set
`freq[i]=freq[j]+freq[j+1]`, `child[i]=j`, `parent[j]=parent[j+1]=i`,
and advance `j` by 2. Root is 626; set `parent[626]=0` and the frequency
sentinel `freq[627]=65535`.

Decode a symbol by starting at `child[626]`. While this value is below 627,
read one bit `b` and replace the value with `child[value+b]`. Subtract 627
to obtain a symbol `0..313`, then update the adaptive tree:

1. If root frequency is 32768, reconstruct the tree as described below.
2. Set `node=parent[627+symbol]`. Execute the body at least once, **including
   when this initial node is zero**.
3. Increment `freq[node]`. If it exceeds `freq[node+1]`, find the last later
   node with strictly smaller frequency, exchange frequencies and `child`
   values, and update parent pointers for both exchanged children (and their
   right siblings when an exchanged child is an internal-node pair). Continue
   from the later exchanged node.
4. Replace `node` with `parent[node]`; repeat until this new value is zero.

Reconstruction retains the leaves in their current order, replacing each
frequency with `(frequency+1)//2`. Rebuild internal nodes in ascending
frequency order from consecutive pairs, inserting a new sum after equal
frequencies and before larger ones. Move corresponding `child` entries
with frequencies. Finally rebuild every parent pointer from the child array.
The 65535 sentinel and root-parent zero remain unchanged.

Symbols below 256 are literal bytes. Other symbols encode a match length
`symbol-253`, ranging from 3 to 60. The ring has 4096 positions and starts
writing at 4036; initialize preceding positions `0..4035` to byte `20`.
Read the match position using this fixed prefix table:

| Upper position value | Prefix length | Left-aligned prefix byte |
|---|---:|---|
| `0` | 3 | `00` |
| `1..3` | 4 | `20,30,40` |
| `4..11` | 5 | `50..88`, step `08` |
| `12..23` | 6 | `90..BC`, step `04` |
| `24..47` | 7 | `C0..EE`, step `02` |
| `48..63` | 8 | `F0..FF`, step `01` |

Read an eight-bit value `v`. Select the row/prefix whose interval contains
`v` (interval width `2^(8-prefix_length)`). For this upper value `u`, read
`prefix_length-2` more bits, shifting each into `v`. The decoded position is
`(u<<6)|(v&63)`. Copy the match from
`(write_position-position-1)&4095`, advancing both source and write positions
with wraparound. Copy byte by byte so overlapping matches work.

The LE uint32 header is the logical output length. Stop at that length, even
if the last match describes more bytes; its symbol and position have already
been consumed. The native routine may physically finish that match, but those
additional bytes are not part of the declared resource. Unused low bits of
the last compressed byte are padding. A bit-reader may fetch an extra byte
for lookahead, including zero at EOF; it must not consume invented EOF bits
to produce missing output. NUL literals in binary resources are data, not
terminators.

For `.SCD` libraries the file starts directly with one LZHUF block. For
v10-v14 `.SCO` text libraries, blocks are concatenated and each block is
prefixed before the LZHUF size:

| Prefix | Meaning |
|---|---|
| `CHT` | Cheat index or cheat article block |
| `JOK` | Joke index or joke article block |
| `HLP` | Help/manual index block |
| `HLPnnn` | One numbered manual/walkthrough block, e.g. `HLP030` |

The LZHUF bit reader keeps one byte of lookahead in many blocks. After a block
is decoded, continue at `input_position - floor(unread_bits / 8)` when that
offset starts with the next known prefix; otherwise continue at
`input_position`. Single-block `.SCD` files usually consume the physical EOF.

The decoded v6-v14 text streams still contain the same inline attribute bytes
as the v3/v4 SCO family. In Kamenicky text these appear as glyphs such as `φ`,
`≡`, `⌠`, `⌡`, `±`, `Θ`, `≥`, `√`, and `ε`; v10 `DATATEXT.SCD` also uses
them around box-drawing tables. The foreground map is shared with modern DAT: `0xE7` through `0xEC` as CGA 1 through 6 and `0xEE` through
`0xF5` as CGA 8 through 15. `0xED` / `φ` closes the current foreground span.
`0xF7` begins a blue-background span and `0xF6` ends it. Modern DAT streams
also use `0xE6` as the background reset. `0xF8` is preserved as a literal
degree sign. `0xE5` begins a gray-background span, except for the conservative
literal-`ň` text case documented above.

A literal-E interpretation of `EE` inside words is an extraction hypothesis,
not an established escape instruction. Standalone `EE` follows the dark-gray
foreground rule.

Observed v6 shareware files:

| File(s) | Contains |
|---|---|
| `DATAA.SCD`, `DATA1.SCD`..`DATA7.SCD` | Cheat index plus cheat topic streams |
| `DATAB.SCD`, `DATAV1.SCD` | Joke index plus jokes |
| `DATAN1.SCD` | Manuals/walkthroughs |
| `DATATEXT.SCD` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | Font/resource files |
| `SCR1.SCD`..`SCR6.SCD` | Screen/resource banks |
| `SLEEPER.SCO` | DOS executable/helper |

Observed v7 shareware files:

| File(s) | Contains |
|---|---|
| `DATAA.SCD`, `DATA1.SCD`..`DATA8.SCD` | Cheat index plus cheat topic streams |
| `DATAB.SCD`, `DATAV1.SCD` | Joke index plus jokes |
| `DATAN1.SCD` | Manuals/walkthroughs |
| `DATATEXT.SCD` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | Font/resource files |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCR1.SCD`, `SCR2.SCD`, `SCR4.SCD`..`SCR6.SCD`, `SP.SCX` | Screen/resource banks |

Observed v8 shareware files:

| File(s) | Contains |
|---|---|
| `DATAA.SCD`, `DATA1.SCD`..`DATA9.SCD` | Cheat index plus cheat topic streams |
| `DATAB.SCD`, `DATAV1.SCD` | Joke index plus jokes |
| `DATAN1.SCD` | Manuals/walkthroughs |
| `DATATEXT.SCD` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | Font/resource files |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCR1.SCD`, `SCR2.SCD`, `SCR4.SCD`..`SCR6.SCD`, `SP.SCX` | Screen/resource banks |

Observed v10 files:

| File(s) | Contains |
|---|---|
| `CHEATS.SCO` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `HELPS.SCO` | Concatenated `HLP` blocks: manual/help index followed by manuals |
| `JOKES.SCO` | Concatenated `JOK` blocks: joke index followed by jokes |
| `DATATEXT.SCD` | Program/help text |
| `FONT.SCO` | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX`, `XMAS.SCX` | Screen/resource banks |

Observed v11 files:

| File(s) | Contains |
|---|---|
| `CHEATS.SCO` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | Program/help text |
| `FONT.SCO` | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX`, `XMAS.SCX` | Screen/resource banks |

Observed v12 files:

| File(s) | Contains |
|---|---|
| `CHEATS.SCO` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO`, `NAVODY4.SCO` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | Program/help text |
| `FONT.SCO` | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX` | Screen/resource banks |

Observed v13 files:

| File(s) | Contains |
|---|---|
| `CHEATS.SCO` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO`, `NAVODY4.SCO` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | Program/help text |
| `FONT.SCO` | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX` | Screen/resource banks |

Observed v14 files:

| File(s) | Contains |
|---|---|
| `CHEATS.SCO` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO`, `NAVODY4.SCO` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | Program/help text |
| `FONT.SCO` | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX` | Screen/resource banks |

Extractor guidance:

- first apply the same non-text resource filter as v4/v5
- if a candidate file starts with `SCORPION 00 01`, try the v4/v5 Huffman
  decoder
- otherwise try LZHUF:
  - `.SCD`: one direct LZHUF block at file offset `0`
  - `.SCO`: one or more prefixed LZHUF blocks as described above
- index target IDs can address articles in other libraries of the same
  release; for example `NAVODY2.SCO` also indexes articles in `NAVODY3.SCO`
  and `NAVODY4.SCO`

## References

- Allegro datafiles: <https://liballeg.org/stabledocs/en/datafile.html>
- Allegro packfiles and old password API: <https://liballeg.org/stabledocs/en/packfile.html>
- Allegro `packfile_password`: <https://www.allegro.cc/manual/4/api/file-and-compression-routines/packfile_password>
- Cheater DOS history: <https://www.cheater.cz/wincheater2/historie-cheater-pro-dos/>
- Cheater.cz Legend of Kyrandia 1 walkthrough: <https://www.cheater.cz/pc-hry/legend-of-kyrandia-1/navod/1895/>
- Cheater.cz Legend of Kyrandia 2 walkthrough: <https://www.cheater.cz/pc-hry/legend-of-kyrandia-2/navod/1894/>
- Cheater.cz Alone In The Dark 2 cheat: <https://www.cheater.cz/pc-hry/alone-in-the-dark-2/cheat/2198/>
- Cheater.cz Chaos Engine cheat: <https://www.cheater.cz/pc-hry/chaos-engine/>
- Cheater.cz Starfighter 3000 cheat: <https://www.cheater.cz/pc-hry/starfighter-3000/>
- Cheater.cz Sword of Sodan cheat: <https://www.cheater.cz/pc-hry/sword-of-sodan/>
- Cheater.cz legacy article CSS: <https://www.cheater.cz/css-clanek-old.css>
- Clockwiser cheats/passwords: <https://www.absolutcheats.com/pc/clockwiser-cheats>
- Kamenicky encoding: <https://en.wikipedia.org/wiki/Kamenick%C3%BD_encoding>
