# Scorpion's Cheater DAT

Main format: the latest verified DOS DAT branch, Scorpion's Cheater v23.
The same modern Allegro-backed DAT family is used by v15, v16, v21, and v22.

Files: `CHEATY.DAT`, `NAVODY.DAT`, `PROGRAM.DAT`, `VTIPY.DAT`,
`EASTER.DAT`, and v21 `TEXTY.DAT`.

## Status

Modern DOS Scorpion DAT files are password-protected Allegro datafiles. The
reader implements the container, old-crypt header handling, Allegro LZSS
decompression, Kamenicky / KEYBCS2 article decoding, inline text attributes, and
source line breaks. `ICONA.DAT` in v23 is a Windows icon resource, not an
article DAT.

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
| `ICONA.DAT` | - | - | Windows icon resource, excluded from article export |

## Allegro Container

The generic Allegro parser is intentionally independent from Scorpion's
Cheater. Scorpion-specific code passes the password `akrab` and enables
per-object old-crypt password reset.

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
use this path.

The last object is usually Allegro grabber metadata named `GrabberInfo`.

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

### Attribute Audit

The current corpus audit counts only decoded article streams. Fonts, executable
helpers, screen banks, and other filtered resources are excluded. An occurrence
is counted again when the same historical article is included in another
version, so the totals measure the amount of source data affected rather than
the number of distinct articles.

After the corpus, web, and DOSBox comparison described below, no unresolved
inline attribute bytes remain in any supported version family:

| Version family | Releases | Unresolved bytes | Distinct | Occurrences |
|---|---|---|---:|---:|
| v3.x | 3, 3.5 | none | 0 | 0 |
| v4-v5 | 4, 5 | none | 0 | 0 |
| v6-v8 | 6, 7, 8 shareware | none | 0 | 0 |
| v10-v14 | 10, 11, 12, 13, 14 | none | 0 | 0 |
| modern DAT | 15, 16, 21, 22, 23 | none | 0 | 0 |

The unresolved union is empty. The final audited control was `0xE5`, with 11
raw occurrences: nine in inherited `R010` block artwork and two in the same
v15/v16 `TOPGUN / 9011` text.

The v4/v5 `Starfighter 3000` article contains a self-describing color legend.
It is stronger evidence than the migrated website because the byte and its
written color name occur in the same original DOS record:

| Sequence | Written legend | Mapping |
|---|---|---|
| `F0 G ED` | `G = zelený` | green |
| `F4 Y ED` | `Y = žlutý` | yellow |
| `F2 R ED` | `R = červený` | red |
| `EF B ED` | `B = modrý` | blue |
| `F3 M ED` | `M = fialový` | magenta |
| `F1 C ED` | `C = světle modrý` | light blue / cyan |
| `EC O ED` | `O = oranžový` | orange |

Modern `Alone in the Dark 2` independently agrees with Cheater.cz for `F0`
green (`SAVE0.ITD`), `F5` white (offsets), and `F4` yellow (replacement
bytes). Modern `Chaos Engine` agrees for `F1` light blue, `F5` white, and `F0`
green.

A direct DOSBox Staging run of Scorpions Cheater 14 resolves `0xE8` and
`0xE9`, and also fixes the palette indexes previously assigned to `0xF0` and
`0xF1`. Topic `[4078]`, `FIFA Soccer '96`, stores
`E9 VANCOUVER E8 (USA) ED` and displays `VANCOUVER` in cyan and `(USA)` in
green. The same screen shows `F0 XPLAY ED` in bright green and `F1 1) ED` in
bright cyan. The captured VGA colors are `#00AA00`, `#00AAAA`, `#55FF55`, and
`#55FFFF`, corresponding to CGA foreground indexes 2, 3, 10, and 11. The
`O programu` screen also shows `F2 >> ED` as `#FF5555`, confirming CGA 12.

A direct DOSBox run of v5 resolves `0xEB`. In `Battle Beast` topic `[0101]`,
the source stores `EB YOYOYO` and displays `YOYOYO` as `#AA00AA`, dark
magenta / CGA 5. Later releases reformat the same cheat: v10 stores `F0
YOYOYO`, so its bright-green rendering does not describe the v5 byte. The
same v5 capture set independently shows `EB world 6/4 =103546` in `Super
Frog` as dark magenta while the preceding password rows remain white. The
`0xEB -> CGA 5` mapping removes all unresolved controls from the v3.x family.

A direct DOSBox run of v10 resolves the remaining foreground controls used by
the legacy families. In `DATATEXT.SCD / R001`, `EF` draws the grid in
`#5555FF` / CGA 9, `EE` draws the inset frame in `#555555` / CGA 8, and `E7`
draws its shadow lines in `#0000AA` / CGA 1. The same topic stores its large
scorpion picture between `EA` transitions and displays it as `#AA0000` / CGA
4. Together with the earlier observations, this confirms the continuous
foreground sequence from `E7` through `F5`, with `ED` reserved as reset.

The v5 `Sword of Sodan` sequence is `F7 F0 NANCY F6 ED`. Its screenshot shows
`NANCY` in bright green on a dark-blue rectangular background. V10
`DATATEXT.SCD / R002` independently stores both hex-table rows as
`F7 F1 ... F6` and displays bright-cyan text on the same dark-blue background.
Therefore `F7` begins a CGA 1 background span and `F6` ends it; the foreground
control inside the pair remains independent.

Modern `PROGRAM.DAT / R201` contains the same two inherited hex-table rows,
but stores `E6` where v10 stores the closing `F6`. Modern `R010` also ends its
colored block-art row with `E6`. The modern reader therefore treats `E6` as
the version-specific blue-background reset.

A direct DOSBox run of v14 resolves `E5`. The relevant `R010` source sequence
is `F5 DC E5 DC DB DB F6`: `F5` selects white foreground, then `E5` changes
the upper half of the following `DC` cell to `#AAAAAA` / CGA 7 while its lower
half remains white. Thus `E5` starts a gray-background span and `F6` ends it.
The two non-art occurrences are `kampa E5 ,` in identical v15/v16 `TOPGUN`
records. Since the surrounding text requires `kampaň,` and the preceding byte
is a letter rather than block art, the reader conservatively restores literal
`ň` only when `E5` follows an alphanumeric character and precedes punctuation.

`0xF8` is not a formatting control in the decoded article corpus. All 36 text
occurrences are literal degree signs in v21-v23 `NAVODY.DAT`, in phrases such
as `otočila se o 180°`. The reader preserves these as literal text.

Web comparison limitations:

- Cheater.cz preserves useful named spans such as `zelena`, `modra`, `bila`,
  and `zluta`. These validate the modern foreground controls when the local and
  web article versions have the same byte-level formatting.
- The same article can be reformatted between DOS releases. For example,
  `SAVE0.ITD` uses `F5` in v3.5-v7 but `F0` from v10 onward; the current web
  page matches the later `F0` version. A textual match alone is therefore not
  enough to infer an older byte meaning.
- Cheater.cz exports some styles as classes such as `c2`, `c3`, `c5`,
  and `c6`. These classes are absent from both the current stylesheet and the
  archived 2018 `css-clanek-old.css`, so their actual colors cannot be
  recovered from the public CSS.
- `0xE9` demonstrates that the generated `cN` class is not a stable byte map:
  it becomes `c2` in `Colonization`, `c3` in `Chaos Engine`, and `c5` in
  `Eye of the Beholder 3`.
- ASCII-art colors and frame attributes are generally lost on the website;
  direct DOSBox captures were required to finish their mapping.

Additional byte-level fixes that are now handled in the reader:

| Byte | Meaning |
|---:|---|
| `0xE0` | literal `ŕ` |
| `0xFB` | context-sensitive: invisible pre-CR/LF terminator, otherwise literal `ü` |
| `0xFC` | literal `ü` |
| `0xFD` | literal `ř` |
| `0xFE` | hard space separator |
| `0xFF` | non-breaking / layout space, normalized to plain space in UHF output |

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

The converter transfers this artwork directly to standard UHF2. It preserves
the leading spaces on block/box-art rows, emits the characters as Unicode,
converts the attributes to `[fg]`, `[bg]`, or `[color:fg:bg]` spans, and exports
`metadata.display.cols = 80`. The viewer therefore uses fixed, non-wrapping
topic layout and reconstructs the picture without embedding a raster image.

This Unicode reconstruction is not yet pixel-exact for glyphs redefined by the
program's external `FONT.SCO`. For example, the v10/v14 `PROGRAM / R001`
scorpion artwork stores bytes `0xD2` and `0x99`. A normal CP437 mapping displays
them as `╥` and `Ö`, but the original custom DOS font draws a curved tail
fragment and a filled picture fragment instead. These are unresolved custom
font glyph mappings, not inline formatting controls.

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
the preceding 127-byte program-specific header includes the font description.
Extraction therefore needs no decompressor:

```text
font = file_bytes[len(file_bytes) - 4096 :]
assert len(font) == 4096
```

Using the final 4096 bytes instead of a hard-coded `0x7F` offset also makes the
extractor fail less dangerously if another release adds header metadata.

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

Do not decode these payloads with the v6-v14 text-library LZHUF routine. The
framing resembles the `SCR`/`CHT`/`HLP` resources, but that decoder reaches a
4096-byte output before consuming the complete record and produces invalid
glyphs. Zero-filled or space-filled LZSS dictionaries and the common `F=18`
and `F=60` LZHUF variants have all been rejected. The exact font-specific
decompressor or post-processing stage is still unresolved. A converter must
therefore either preserve these seven compressed records losslessly or use a
verified font recovered from the running DOS program; it must not publish the
current text-LZHUF probe output as a bitmap font.

#### v16 and v21-v23: Allegro DAT font records

`PROGRAM.DAT` stores `FONT1`..`FONT7`, `FONTKRUH`, and `FONTOK` as Allegro
`DATA` objects. First apply the normal modern DAT recipe: old-crypt password
`akrab`, then Allegro object LZSS decompression using the negative unpacked
size. The resulting payload of every font record is already the complete raw
4096-byte 8 x 16 font described above; no additional font codec is applied.
Version 15 does not contain these font records in the current corpus.

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
  They can be represented in UHF as fixed 80-column text plus foreground and
  background spans.
- `SCR*.SCX`, `SP.SCX`, and `XMAS.SCX` use LZHUF too, but decode to a four-byte
  little-endian `width, height` header followed by one indexed pixel byte per
  pixel. Observed files decode to `640 x 480` plus 307200 pixel indexes. They
  are raster screens, not ASCII art. Their original VGA palette still needs to
  be identified before a faithful image export can be added to a future UHF
  asset/attachment layer.

Besides article streams, modern DAT files also ship non-text resource records.
These are excluded from the topic list and surfaced separately in bundle
metadata. Simple convenience fields still expose
`scorpion_resource_record_count` and `scorpion_resource_record_names`.

Observed families in the current corpus:

- `obr*`, `obrview`, `xicht`, `pirat`, `egg`, `scroll` — compressed 80x25 text-mode screens, ASCII-art, and TheDraw-like presentation assets
- `FONT1..FONT7`, `FONTKRUH`, `FONTOK` — Allegro-compressed objects whose
  decoded payloads are raw 4096-byte 8 x 16 bitmap fonts
- `datum*`, `rok*`, `seznam*`, `verze*`, `library*`, `Librar`, `update_ini` — metadata / library helper records

The richest modern bundle for this purpose is `v23 PROGRAM.DAT`, which still
contains 23 non-topic resource records including fonts and `obr*` assets. These
records are the obvious candidates for a future UHF2 asset/attachment layer.

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

This means a converter must not infer the content section from the first
character alone. Use the current source file or parsed index role first, then
use the bracketed target only as a stable local ID.

## UHF2 Export Metadata

Yes, but only through existing UHF2 fields.

Modern Scorpion DAT exports keep the usual UHF metadata such as
`metadata.source.filename`, `metadata.source.format`, `metadata.source.encoding`,
the black DOS-like `metadata.ui` theme, and the lightweight non-topic resource
summary fields `scorpion_resource_record_count` and
`scorpion_resource_record_names`.

The writer no longer emits extra Scorpion-only UHF keys for record inventories,
Allegro object lists, or per-topic byte boundaries. When a source bundle has one
clear source-wide date, it belongs in the existing `metadata.source.date` field
instead of a new custom export key.

## Viewer Defaults

All supported Scorpions Cheater families, from v1 through the modern DAT
releases, export the same black DOS-like UI theme through UHF `metadata.ui`.
The help window therefore opens with a black background instead of the default
cyan TurboVision pane. Inline Scorpion spans still use the DOS CGA color
palette.

## Reader Model

The reader implementation is split by responsibility:

- `thelpviewer/server/converter/readers/scorpion_reader.py`: Scorpion version/path
  helpers, shared Scorpion text encoding/theme constants, and top-level
  dispatch between modern DAT and legacy readers
- `thelpviewer/server/converter/readers/scorpion_bundle.py`: Scorpion-only bundle
  grouping and document variants; this is where v3 sections and v4-v14
  multi-file category merges are assembled
- `thelpviewer/server/converter/readers/allegro_dat.py`: generic Allegro DAT parser,
  old-crypt support, and Allegro LZSS decompression
- `thelpviewer/server/converter/readers/scorpion_dat_parser.py`: Scorpion password,
  decoded `DATA` entries, records, and article slices
- `thelpviewer/server/converter/readers/scorpion_dat_reader.py`: Kamenicky text rendering,
  inline styles, Scorpion-specific byte fixes, topics, index entries, contents,
  black-window UI metadata, and resource-record inventory
- `thelpviewer/server/converter/readers/scorpion_legacy_reader.py`: shared legacy
  primitives, RAR4 overlay parsing, PKLITE unpack handoff, text normalization,
  SCO topic parsing, shared SCO text rendering, and non-text resource filtering
- `thelpviewer/server/converter/readers/scorpion_legacy_v1x.py`: version-specific
  v1.0 and v1.5 readers
- `thelpviewer/server/converter/readers/scorpion_legacy_v3x.py`: version-specific
  v3 and v3.5 readers
- `thelpviewer/server/converter/readers/scorpion_legacy_v4x.py`: version-specific
  v4-v5 SCO readers using the `SCORPION 00 01` Huffman text libraries
- `thelpviewer/server/converter/readers/scorpion_legacy_v6x.py`: version-specific
  v6-v14 SCO/SCD/SCX readers using LZHUF text libraries

The Scorpion reader selects `decoded_payload` for compressed Allegro `DATA`
objects. `stored_payload` is kept only as source metadata; it is not the article
text stream.

Generic writers do not contain Scorpion-specific logic. `bundle.py` asks the
extension layer for optional source groups and document variants, and `json.py`
only emits custom metadata named in `transport_metadata_keys`.

Merged legacy SCO category bundles retain the source-validation counters in
that allowlist, including `scorpion_sco_marker_topic_count`,
`scorpion_sco_index_entry_count`, `scorpion_sco_index_header_count`,
`scorpion_sco_index_status_counts`, and `scorpion_sco_index_flag_counts`.
These fields must survive the merge so generated bundles can still be audited
against the individual SCO index structures.

## Modern DAT Extractor Recipe

This is the primary format documented by this file. It covers the verified
Allegro-backed branch used by v15, v16, v21, v22, and v23.

Detection:

- match the source path to a modern Scorpions Cheater version directory
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
- keep the marker as an alias / source ID
- render attribute bytes as UHF spans or strip them from plain text according
  to the inline-format table above

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
| `TEXTY.DAT` | 6 | 5 | Additional program/text articles |
| `VTIPY.DAT` | 17 | 16 | Jokes |

#### v22

| File | Objects | DATA | Contains |
|---|---:|---:|---|
| `CHEATY.DAT` | 32 | 31 | Cheat/code articles |
| `EASTER.DAT` | 10 | 9 | Easter eggs and bonus/misc articles |
| `NAVODY.DAT` | 47 | 46 | Walkthroughs and guides |
| `PROGRAM.DAT` | 26 | 25 | Program/editorial/help text |
| `VTIPY.DAT` | 17 | 16 | Jokes |

### Legacy v1.x

Source modules: `scorpion_legacy_reader.py` and `scorpion_legacy_v1x.py`.

Observed files:

| Version | File | Contains / status |
|---|---|---|
| v1.0 | `DATA.DAT` | DOS MZ/RAR SFX wrapper; `MENU2.EXE` inside the archive contains menu/help text and cheat topics |
| v1.5 | `CHEATER.EXE` | PKLITE-packed DOS executable with embedded menu/help text, author names, and cheat topics |
| v1.5 | `CS.EXE` | Helper executable/resource; skipped, not a help corpus |

#### v1.0 `DAT` wrapper

Detection:

- version directory resolves to `Scorpions Cheater 1`
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

Export:

- create overview, `O programu`, `Ovládání`, and parsed sample cheat topics
- use the parsed topic order from the string stream
- keep RAR member names, overlay offset, and parsed member name as source
  metadata

#### v1.5 `CHEATER.EXE`

Detection:

- version directory resolves to `Scorpions Cheater 1.5`
- accepted suffix is `.EXE`
- `CS.EXE` is skipped; it is not a help corpus file for this branch
- the useful corpus is in `CHEATER.EXE`, typically PKLITE-packed

Container extraction:

1. Detect DOS MZ and PKLITE in the executable header.
2. Unpack PKLITE. The current implementation delegates this step to `deark`
   with module `pklite`.
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

Export:

- create overview, `O programu`, `Menu pro tisk`, `Ovládání`, optional
  `Seznam her`, and parsed cheat topics
- store directory counts for `new`, `renovated`, and `plain`
- add resolved directory aliases to matching cheat topics

### Legacy v3.x

Source modules: `scorpion_legacy_reader.py`, `scorpion_legacy_v3x.py`, and
`scorpion_bundle.py`.

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

- version directories resolve to `Scorpions Cheater 3` or `Scorpions Cheater
  3.5`
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

Context IDs:

- digit-only cheat markers use their numeric value directly
- other sections add a section offset to the marker value
- manuals use base `0x100000`
- jokes use base `0x200000`
- index/other use base `0x300000`
- non-digit cheat markers use base `0x400000`

Export:

- one parsed document initially contains all sections under `Návody`, `Cheaty`,
  `Vtipy`, and `Další`
- bundle variants split that document into three UHF files:
  `navody.json.gz`, `cheaty.json.gz`, and `vtipy.json.gz`
- `SCC.SC` is not exported as its own final article file

The `MULTI.*` classification is also supported by web copies of individual
entries. `ALONE IN THE DARK II` and `CHAOS ENGINE` both resolve to Cheater.cz
`cheat` articles, and `CLOCKWISER` appears as a cheat/password list rather than
as a walkthrough.

The v3 reader also handles legacy formatting attribute bytes that would decode
as visible Kamenicky glyphs. Web copies of the same texts show normal prose and
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

Source modules: `scorpion_legacy_reader.py`, `scorpion_legacy_v4x.py`, and
`scorpion_bundle.py`.

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

Index stream handling:

- `DATAA.SCO` with index entries is the cheat index and exports as
  `Index cheatů`
- `DATAB.SCO` with index entries, or any index whose first line contains
  `[FÓRŮ]`, is the joke index and exports as `Index vtipů`
- index rows whose label starts with `SEZNAM` are headers, not game entries
- all parsed index rows are kept in metadata as `scorpion_sco_index_entries`

Verified v4 file roles:

| File(s) | Export/status | Contains |
|---|---|---|
| `DATAA.SCO`, `DATA1.SCO`..`DATA6.SCO` | merged to `cheaty.json.gz` | Cheat index plus cheat topic streams |
| `DATAB.SCO`, `DATAV1.SCO` | merged to `vtipy.json.gz` | Joke index plus jokes |
| `DATAN1.SCO` | `navody.json.gz` | Manuals/walkthroughs |
| `DATAHELP.SCO`, `DATATEXT.SCO` | merged to `program.json.gz` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | skipped | Font/resource files; headers contain strings such as `SCORPIONS CHEATER 4.0 font A` |
| `SLEEPER.SCO` | skipped | DOS executable/helper |
| `SPELDATA.SCO` | skipped | Binary resource, not a `SCORPION 00 01` text library |

Verified v5 file roles:

| File(s) | Export/status | Contains |
|---|---|---|
| `DATAA.SCO`, `DATA1.SCO`..`DATA7.SCO` | merged to `cheaty.json.gz` | Cheat index plus cheat topic streams |
| `DATAB.SCO`, `DATAV1.SCO` | merged to `vtipy.json.gz` | Joke index plus jokes |
| `DATAN1.SCO` | `navody.json.gz` | Manuals/walkthroughs |
| `DATAHELP.SCO`, `DATATEXT.SCO` | merged to `program.json.gz` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | skipped | Font/resource files |
| `SLEEPER.SCO` | skipped | DOS executable/helper |
| `SPELDATA.SCO` | skipped | Binary resource, not a `SCORPION 00 01` text library |

Export:

- legacy SCO/SCD exports are category bundles: `cheaty`, `vtipy`, `navody`,
  and `program`
- index files such as `DATAA` and `DATAB` are source members of the category
  bundle, not standalone final bundles
- topic titles are retitled from parsed index entries by matching the index
  `target_id` to the article marker, e.g. `0002`, `N030`, or `R001`
- the category merge is implemented in `scorpion_bundle.py`, not in generic
  bundle or JSON writers

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

Source module: `scorpion_legacy_v6x.py`, sharing the same SCO/SCD base reader
as v4/v5.

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
them around box-drawing tables. For v10-v14 the extractor renders the resolved
attribute controls as UHF inline spans using the same foreground map as the
modern DAT reader: `0xE7` through `0xEC` as CGA 1 through 6 and `0xEE` through
`0xF5` as CGA 8 through 15. `0xED` / `φ` closes the current foreground span.
`0xF7` begins a blue-background span and `0xF6` ends it. Modern DAT streams
also use `0xE6` as the background reset. `0xF8` is preserved as a literal
degree sign. `0xE5` begins a gray-background span, except for the conservative
literal-`ň` text case documented above.

`0xEE` / `ε` is restored to literal `E` only when it is embedded between two
alphanumeric characters, for example `DεFεNDεR` -> `DEFENDER`. If `ε` appears
next to a box border or as a line/list attribute, it is treated as a formatting
control instead.

Observed v6 shareware files:

| File(s) | Export/status | Contains |
|---|---|---|
| `DATAA.SCD`, `DATA1.SCD`..`DATA7.SCD` | decoded and merged to `cheaty.json.gz` | Cheat index plus cheat topic streams |
| `DATAB.SCD`, `DATAV1.SCD` | decoded and merged to `vtipy.json.gz` | Joke index plus jokes |
| `DATAN1.SCD` | `navody.json.gz` | Manuals/walkthroughs |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | skipped | Font/resource files |
| `SCR1.SCD`..`SCR6.SCD` | skipped | Screen/resource banks |
| `SLEEPER.SCO` | skipped | DOS executable/helper |

Observed v7 shareware files:

| File(s) | Export/status | Contains |
|---|---|---|
| `DATAA.SCD`, `DATA1.SCD`..`DATA8.SCD` | decoded and merged to `cheaty.json.gz` | Cheat index plus cheat topic streams |
| `DATAB.SCD`, `DATAV1.SCD` | decoded and merged to `vtipy.json.gz` | Joke index plus jokes |
| `DATAN1.SCD` | `navody.json.gz` | Manuals/walkthroughs |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | skipped | Font/resource files |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCR1.SCD`, `SCR2.SCD`, `SCR4.SCD`..`SCR6.SCD`, `SP.SCX` | skipped | Screen/resource banks |

Observed v8 shareware files:

| File(s) | Export/status | Contains |
|---|---|---|
| `DATAA.SCD`, `DATA1.SCD`..`DATA9.SCD` | decoded and merged to `cheaty.json.gz` | Cheat index plus cheat topic streams |
| `DATAB.SCD`, `DATAV1.SCD` | decoded and merged to `vtipy.json.gz` | Joke index plus jokes |
| `DATAN1.SCD` | `navody.json.gz` | Manuals/walkthroughs |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FA.SCO`..`FF.SCO`, `FOK.SCO` | skipped | Font/resource files |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCR1.SCD`, `SCR2.SCD`, `SCR4.SCD`..`SCR6.SCD`, `SP.SCX` | skipped | Screen/resource banks |

Observed v10 files:

| File(s) | Export/status | Contains |
|---|---|---|
| `CHEATS.SCO` | `cheaty.json.gz` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `HELPS.SCO` | `navody.json.gz` | Concatenated `HLP` blocks: manual/help index followed by manuals |
| `JOKES.SCO` | `vtipy.json.gz` | Concatenated `JOK` blocks: joke index followed by jokes |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FONT.SCO` | skipped | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX`, `XMAS.SCX` | skipped | Screen/resource banks |

Observed v11 files:

| File(s) | Export/status | Contains |
|---|---|---|
| `CHEATS.SCO` | `cheaty.json.gz` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | `vtipy.json.gz` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO` | merged to `navody.json.gz` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FONT.SCO` | skipped | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX`, `XMAS.SCX` | skipped | Screen/resource banks |

Observed v12 files:

| File(s) | Export/status | Contains |
|---|---|---|
| `CHEATS.SCO` | `cheaty.json.gz` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | `vtipy.json.gz` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO`, `NAVODY4.SCO` | merged to `navody.json.gz` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FONT.SCO` | skipped | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX` | skipped | Screen/resource banks |

Observed v13 files:

| File(s) | Export/status | Contains |
|---|---|---|
| `CHEATS.SCO` | `cheaty.json.gz` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | `vtipy.json.gz` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO`, `NAVODY4.SCO` | merged to `navody.json.gz` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FONT.SCO` | skipped | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX` | skipped | Screen/resource banks |

Observed v14 files:

| File(s) | Export/status | Contains |
|---|---|---|
| `CHEATS.SCO` | `cheaty.json.gz` | Concatenated `CHT` blocks: cheat index followed by cheat topics |
| `JOKES.SCO` | `vtipy.json.gz` | Concatenated `JOK` blocks: joke index followed by jokes |
| `NAVODY2.SCO`, `NAVODY3.SCO`, `NAVODY4.SCO` | merged to `navody.json.gz` | Concatenated `HLP` / `HLPnnn` manual blocks |
| `DATATEXT.SCD` | `program.json.gz` | Program/help text |
| `FONT.SCO` | skipped | Font resource |
| `DRIVER.SCO`, `SLEEPER.SCO` | skipped | DOS executable/helper files |
| `SCREENS.SCO`, `SCR001.SCX`..`SCR003.SCX` | skipped | Screen/resource banks |

Extractor guidance:

- first apply the same non-text resource filter as v4/v5
- if a candidate file starts with `SCORPION 00 01`, try the v4/v5 Huffman
  decoder
- otherwise try LZHUF:
  - `.SCD`: one direct LZHUF block at file offset `0`
  - `.SCO`: one or more prefixed LZHUF blocks as described above
- accept the decoded output only if it contains marker topics, at least five
  index entries, or enough Scorpion/help vocabulary to be readable
- merge related decoded files by category after they produce real text:
  - `DATAA` + numeric `DATA*` -> `cheaty`
  - `DATAB` + `DATAV*` -> `vtipy`
  - `DATAN*`, `HELPS`, and `NAVODY*` -> `navody`
  - `DATAHELP` + `DATATEXT` -> `program`
- use index `target_id` values to retitle matching marker topics across all
  merged source files; for example the index in `NAVODY2.SCO` also names
  topics stored in `NAVODY3.SCO` and `NAVODY4.SCO`

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
