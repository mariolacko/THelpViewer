# Game-Cheater 9.02 Database File Format Specification

## 1. Overview

Game-Cheater 9.02 is a Czech freeware cheat database for MS-DOS and Windows.
Its data is stored in several database files that appear to originate from a Pc-Fand / FAND database application.

The main database and supporting tables are stored mostly as pairs of files:

```text
NAME.000
NAME.T00
```

The `.000` file usually contains fixed-size records.
The `.T00` file contains variable-length text blocks referenced by offsets stored in the `.000` records.

The analyzed files belong to Game-Cheater 9.02.

## 2. Source / Download

The analyzed database files come from **Game-Cheater 9.02**.

Download / catalog page:

```text
https://www.slunecnice.cz/sw/game-cheater/
```

Known information about the program:

```text
Name:      Game-Cheater
Version:   9.02
Author:    Jiří Kalous
License:   Freeware
Language:  Czech
Platform:  MS-DOS / Windows
Archive:   instgc.zip
```

## 3. Analyzed File Set

This specification describes the observed format of the following files:

```text
CHEATDBS.000
CHEATDBS.T00

FIRMY.000
FIRMY.T00

GCNETADR.000
GCNETADR.T00

GCHLP.000
GCHLP.T00

DBSNFO.000
DBSNFO.T00

GCPRM.000
```

## 4. Common Format Concepts

## 4.1 `.000` Fixed Record Files

Most `.000` files contain a small header followed by fixed-size records.

Common structure:

```text
Offset  Size  Description
------  ----  ---------------------------------------
0x0000  6     Table header
0x0006  ...   Fixed-size records
```

The usual `.000` header format is:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------
0x00    4     int32LE    Record count or internal table counter
0x04    2     uint16LE   Record size
```

In some files the record count is stored as a negative integer.
In that case, the real number of records can be obtained using:

```python
record_count = abs(record_count_raw)
```

The record size at offset `0x04` is reliable and should be used when iterating over records.

## 4.2 `.T00` Variable-Length Text Files

The `.T00` files store variable-length text blocks.

Text offsets stored in `.000` files are absolute offsets into the corresponding `.T00` file.

A short text block that fits in the current 512-byte memo page has the following
logical structure:

```text
Offset  Size      Type       Description
------  --------  ---------  ---------------------------------------
+0x00   2         uint16LE   Length of encoded text data
+0x02   length    bytes      Encoded text data
```

A zero offset usually means that no text block is assigned.

The length is the logical text length. It does not include page-chain pointers.
Texts longer than the remaining payload space of a page are not contiguous.
PC-Fand reserves the final four bytes of each continued 512-byte page for a
little-endian absolute pointer to the next page:

```text
Memo page size: 512 bytes
First page:     uint16LE length + up to 506 payload bytes + uint32LE next_page
Next pages:     up to 508 payload bytes + uint32LE next_page
Final page:     remaining payload bytes; no pointer is consumed
```

The payload bytes are XOR-encoded, but the four-byte page pointers are raw
PC-Fand file offsets and must not be XOR-decoded. A naive contiguous read works
only for texts of at most 510 bytes and exposes the pointer bytes as visible
garbage in longer articles.

This behavior is confirmed by PC-Fand's open-source `TFile.RdWr` implementation
in [`FILEACC.PAS`](https://github.com/alisoss/pcfand/blob/master/pas/FILEACC.PAS).

## 4.3 Text Encoding

Most fixed text fields and `.T00` text blocks are encoded using:

```text
XOR key:     0xAA
Code page:   CP852
```

To decode text:

```python
decoded_bytes = bytes(byte ^ 0xAA for byte in encoded_bytes)
text = decoded_bytes.decode("cp852", errors="replace")
```

CP852 is the DOS Central European code page. It is required for correct Czech and Slovak characters.

Do not decode the data as UTF-8 or Windows-1250 directly.

CP852 byte `0xB5` is `Á`, while the same byte is the CP437 box character `╡`.
Do not classify a repeated sequence such as `0xB5 0xB5 0xB5` as box drawing
only because the bytes are adjacent. Interpret a contiguous run of conflicting
bytes as box drawing only when that same run also contains an unambiguous box
byte; otherwise decode it normally as CP852. This preserves strings such as
`DDDLLLOOOUUUHHHÁÁÁ` without damaging actual PC-Fand tables.

### 4.3.1 Inline Style Controls

After page-chain reconstruction and XOR decoding, text can contain PC-Fand
toggle controls. The same byte opens and closes a style:

```text
Byte  Pascal name  Meaning                UHF mapping
----  -----------  ---------------------  -----------
0x01  Ctrl-A       elite typeface         omitted
0x02  Ctrl-B       emphasized             [b]...[/b]
0x04  Ctrl-D       double strike          omitted
0x05  Ctrl-E       compressed typeface    omitted
0x11  Ctrl-Q       double width           omitted
0x13  Ctrl-S       underline              [u]...[/u]
0x17  Ctrl-W       italic                 [i]...[/i]
```

`CR` starts a new line and a following `LF` is consumed. Other low DOS bytes,
such as `0x18`/`0x19` for up/down arrows, are visible CP437 glyphs rather than
format controls. The control meanings are confirmed by PC-Fand's
[`SetStyleAttr`](https://github.com/alisoss/pcfand/blob/master/pas/COMMON.PAS)
implementation.

### 4.3.2 Mixed Box Tables

Some long `DBSNFO` texts store a double-line heading followed by single-line
body borders in the same table. The "Historie vývoje databáze Game-Cheateru"
table is a confirmed example: its heading starts with `╔═...═╗`, but its body
uses bytes for `├─...─┤` and `│`.

This mixture exists in the source data; it is not a code-page decoding error.
THelpViewer normalizes every table that starts with a double top border to
double borders throughout (`╠═...═╣`, `║`, `╚═...═╝`) for consistent display.
An archival extractor may instead preserve the original mixed glyphs.

## 4.4 Fixed XOR Strings

Many `.000` records contain fixed-length string fields.

These fields are:

```text
XOR 0xAA encoded
CP852 text
fixed length
usually padded with null bytes or spaces after decoding
```

A typical decoder should:

```text
1. XOR every byte with 0xAA.
2. Decode the result as CP852.
3. Strip trailing null bytes and spaces.
```

Example function:

```python
def decode_xor_string(data: bytes) -> str:
    decoded = bytes(byte ^ 0xAA for byte in data)
    decoded = decoded.rstrip(b"\x00 ")
    return decoded.decode("cp852", errors="replace").strip()
```

## 5. `CHEATDBS` Main Cheat Database

## 5.1 Files

```text
CHEATDBS.000
CHEATDBS.T00
```

`CHEATDBS.000` contains the main index of games and cheat articles.

`CHEATDBS.T00` contains:

```text
cheat texts
source strings
author / credit strings
redirect texts
```

## 5.2 Observed File Properties

```text
CHEATDBS.000 size: 366,417 bytes
CHEATDBS.T00 size: 2,779,136 bytes
Index header size: 6 bytes
Record size: 111 bytes
Record count: 3,301
```

The record size is stored in `CHEATDBS.000` at offset `0x04`:

```text
0x006F = 111 bytes
```

## 5.3 `CHEATDBS.000` Header

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------
0x00    4     unknown    Unknown / internal Pc-Fand value
0x04    2     uint16LE   Record size
```

For Game-Cheater 9.02:

```text
Record size = 111 bytes
```

## 5.4 `CHEATDBS.000` Record

Each record is 111 bytes long.

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------------
0x00    1     uint8      Record status / deleted flag
0x01    50    xorstr     Game title, XOR 0xAA, CP852
0x33    4     uint32LE   Offset of source text block in CHEATDBS.T00
0x37    4     uint32LE   Offset of cheat text block in CHEATDBS.T00
0x3B    2     uint16BE   Game-Cheater version code
0x3D    50    xorstr     Publisher / company, XOR 0xAA, CP852
```

## 5.4.1 Record Status

```text
Offset: 0x00
Size:   1 byte
Type:   uint8
```

Observed value:

```text
0x00
```

In the analyzed database this value is always zero. It may be a deleted-record flag or another internal Pc-Fand status byte.

This field is not required for extraction of user-facing data.

## 5.4.2 Game Title

```text
Offset: 0x01
Size:   50 bytes
Type:   XOR string
```

Contains the game or article title.

Examples:

```text
04X - Alien Eliminator
11th Hour
3D Pulsoid
Abomination: The Nemesis Project
```

The field is decoded using XOR `0xAA` and CP852.

## 5.4.3 Source Text Offset

```text
Offset: 0x33
Size:   4 bytes
Type:   uint32LE
```

This field points to a short text block in `CHEATDBS.T00`.

The source block usually contains the origin, credit, author, or database source of the article.

Examples:

```text
WWW.CHEATY.SK
Scorpion's Cheater
PC Games Cheat & Scorpion's Cheater
```

A value of `0` means that no source text is assigned.

## 5.4.4 Cheat Text Offset

```text
Offset: 0x37
Size:   4 bytes
Type:   uint32LE
```

This field points to the main cheat article text in `CHEATDBS.T00`.

The referenced text block contains:

```text
cheat codes
walkthrough notes
tips
password lists
key combinations
redirect messages
```

A value of `0` means that no cheat text is assigned.

## 5.4.5 Version Code

```text
Offset: 0x3B
Size:   2 bytes
Type:   uint16BE
```

This field stores a Game-Cheater version code.

It is stored as big-endian:

```python
version_code = record[0x3B] * 256 + record[0x3C]
```

Observed values:

```text
0
100
150
200
205
300
305
400
405
500
505
600
605
700
701
702
703
800
801
802
803
804
805
806
807
808
809
900
901
902
```

These correspond to Game-Cheater versions:

```text
100 -> 1.00
150 -> 1.50
200 -> 2.00
205 -> 2.05
300 -> 3.00
305 -> 3.05
400 -> 4.00
405 -> 4.05
500 -> 5.00
505 -> 5.05
600 -> 6.00
605 -> 6.05
700 -> 7.00
701 -> 7.01
702 -> 7.02
703 -> 7.03
800 -> 8.00
801 -> 8.01
802 -> 8.02
803 -> 8.03
804 -> 8.04
805 -> 8.05
806 -> 8.06
807 -> 8.07
808 -> 8.08
809 -> 8.09
900 -> 9.00
901 -> 9.01
902 -> 9.02
```

Helper function:

```python
def decode_version_code(code: int) -> str:
    if code == 0:
        return "alias / redirect"

    major = code // 100
    minor = code % 100
    return f"{major}.{minor:02d}"
```

The exact semantic meaning is likely one of the following:

```text
version in which the entry was added
version in which the entry was last updated
```

The field is definitely a Game-Cheater version code, not two independent flags.

## 5.4.6 Publisher / Company

```text
Offset: 0x3D
Size:   50 bytes
Type:   XOR string
```

Contains the publisher, developer, or company name.

Examples:

```text
Trilobyte
Eidos Interactive & HotHouse Creations
```

The field may be empty.

## 5.5 `CHEATDBS.T00`

`CHEATDBS.T00` stores variable-length source and cheat text blocks.

The first observed text block begins at offset:

```text
0x0200 = 512
```

The first 512 bytes appear to be a Pc-Fand memo-file header or internal structure.

A text block uses the common chained `.T00` structure from section 4.2:

```text
Offset  Size      Type       Description
------  --------  ---------  ---------------------------------------
+0x00   2         uint16LE   Length of encoded text data
+0x02   length    logical payload, XOR 0xAA, CP852; may cross chained pages
```

## 5.6 Example `CHEATDBS` Entry

First decoded entry:

```text
Title:         04X - Alien Eliminator
Publisher:
Source offset: 729
Cheat offset:  512
Version code:  902
Version:       9.02
```

Source text at offset `729`:

```text
WWW.CHEATY.SK
```

Cheat text at offset `512`:

```text
Uvedená písmena stiskněte najednou pro daný efekt:

TUO   - zapne cheat mód
WRY   - vypne cheat mód
I     - nepřemožitelnost on
U     - nepřemožitelnost off
asdfg - výběr zbraně
N     - skok do dalšího levelu
```

## 5.7 Alias / Redirect Entries

Some entries with version code `0` appear to be aliases or redirects.

Their cheat text may contain a message such as:

```text
!!! ČTĚTE CHEATY NA "PACIFIC AIR WAR (1942)" !!!
```

These records likely point the user to another title under which the real cheat article is stored.

## 6. `FIRMY` Company Database

## 6.1 Files

```text
FIRMY.000
FIRMY.T00
```

`FIRMY` appears to contain company, publisher, developer, and contact information.

## 6.2 Purpose

This database stores company names and longer text descriptions or contact information.

Typical text content includes:

```text
E-mail addresses
WWW addresses
lists of games
company notes
```

## 6.3 `FIRMY.000` Header

The file uses the common `.000` header:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------
0x00    4     int32LE    Record count or internal table counter
0x04    2     uint16LE   Record size
```

The observed record count may be negative. Use the absolute value.

Observed record count:

```text
-142 -> 142 records
```

## 6.4 `FIRMY.000` Record

Observed record size:

```text
55 bytes
```

Record structure:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------------
0x00    1     uint8      Record status / internal flag
0x01    50    xorstr     Company name, XOR 0xAA, CP852
0x33    4     uint32LE   Offset of company text block in FIRMY.T00
```

## 6.4.1 Company Name

```text
Offset: 0x01
Size:   50 bytes
Type:   XOR string
```

Contains a company, publisher, or developer name.

Example:

```text
3D Realms
```

## 6.4.2 Company Text Offset

```text
Offset: 0x33
Size:   4 bytes
Type:   uint32LE
```

Points to a variable-length text block in `FIRMY.T00`.

The text block may contain contact details, website addresses, and games associated with the company.

## 6.5 `FIRMY.T00`

Uses the common chained `.T00` text block structure:

```text
uint16LE length
logical byte[length] text, XOR 0xAA, CP852, with page pointers skipped
```

## 6.6 Example `FIRMY` Entry

```text
Company: 3D Realms
Offset:  789
Text:    E-mail: help@3drealms.com
         WWW: http://www.3drealms.com/
         Hry: Duke Nukem 3D ...
```

## 7. `GCNETADR` Internet Address Database

## 7.1 Files

```text
GCNETADR.000
GCNETADR.T00
```

`GCNETADR` contains a list of internet addresses, probably shown from inside Game-Cheater as useful web links.

## 7.2 Purpose

This database stores:

```text
website names
URL addresses
short descriptions
```

## 7.3 `GCNETADR.000` Header

Uses the common `.000` header:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------
0x00    4     int32LE    Record count or internal table counter
0x04    2     uint16LE   Record size
```

Observed count:

```text
-56 -> 56 records
```

## 7.4 `GCNETADR.000` Record

Observed record size:

```text
143 bytes
```

Record structure:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------------
0x00    1     uint8      Record status / internal flag
0x01    60    xorstr     Website name, XOR 0xAA, CP852
0x3D    78    xorstr     URL address, XOR 0xAA, CP852
0x8B    4     uint32LE   Offset of description text in GCNETADR.T00
```

## 7.4.1 Website Name

```text
Offset: 0x01
Size:   60 bytes
Type:   XOR string
```

Contains a website or resource name.

Example:

```text
Alis
```

## 7.4.2 URL Address

```text
Offset: 0x3D
Size:   78 bytes
Type:   XOR string
```

Contains the website URL.

Example:

```text
http://www.alis.cz
```

## 7.4.3 Description Offset

```text
Offset: 0x8B
Size:   4 bytes
Type:   uint32LE
```

Points to a variable-length description text block in `GCNETADR.T00`.

## 7.5 `GCNETADR.T00`

Uses the common chained `.T00` block structure:

```text
uint16LE length
logical byte[length] text, XOR 0xAA, CP852, with page pointers skipped
```

## 7.6 Example `GCNETADR` Entry

```text
Name:        Alis
URL:         http://www.alis.cz
Description: Stránka autorů PC-Fandu -> zajímavosti, demo verze atd.
```

## 8. `GCHLP` Help Database

## 8.1 Files

```text
GCHLP.000
GCHLP.T00
```

`GCHLP` contains the built-in Game-Cheater help system and an embedded copy of
PC-Fand's internal runtime help. Only the Game-Cheater topics belong in a
Game-Cheater export.

## 8.2 Purpose

This database stores help topics and help article texts.

## 8.3 `GCHLP.000` Header

Uses the common `.000` header:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------
0x00    4     int32LE    Record count or internal table counter
0x04    2     uint16LE   Record size
```

## 8.4 `GCHLP.000` Record

Unlike most other `.000` records, `GCHLP` does not appear to start with a status byte.

The topic title begins directly at offset `0x00`.

Observed record size:

```text
39 bytes
```

Record structure:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------------
0x00    35    xorstr     Help topic name, XOR 0xAA, CP852
0x23    4     uint32LE   Offset of help text in GCHLP.T00
```

## 8.4.1 Help Topic Name

```text
Offset: 0x00
Size:   35 bytes
Type:   XOR string
```

Contains the help topic title.

Example:

```text
Root
```

## 8.4.2 Help Text Offset

```text
Offset: 0x23
Size:   4 bytes
Type:   uint32LE
```

Points to a text block in `GCHLP.T00`.

## 8.4.3 Embedded PC-Fand Help Range

The topic list contains explicit boundary records:

```text
!! ZDE ZAČÍNÁ INTERNÍ HELP FANDU !!
!! ZDE KONČÍ INTERNÍ HELP FANDU !!
```

An extractor should skip both boundary records and every record between them.
The analyzed `GCHLP.000` has 531 physical records. The embedded PC-Fand range
starts at record 149 and ends at record 508 (zero-based); valid Game-Cheater
help continues after the end marker. Filtering by marker text is preferred to
hard-coded record numbers.

After blank titles and the embedded range are removed, Game-Cheater 9.02 has
167 user-facing help topics. Names such as `FMEdit`, one-letter entries and
other generic database-runtime commands come from PC-Fand and must not appear
in the Game-Cheater Contents tree.

## 8.4.4 Hypertext Links

In user-facing `GCHLP` topics, Ctrl-S underlining is also used for hypertext
targets. After all retained help records have topic ids, compare the visible
text of each underlined span with the decoded topic titles, case-insensitively
and with whitespace collapsed. A match should be exported as a link to that
topic while preserving the underline.

```text
Viz.: Ctrl-S "O programu" Ctrl-S
    -> [link:topic=<id>][u]O programu[/u][/link]
```

Not every underlined span is a link. If no help title matches, retain it as
ordinary underline formatting. If a title occurs more than once, the nearest
matching record in topic order is the best reconstruction of PC-Fand's local
help navigation.

## 8.5 `GCHLP.T00`

Uses the common chained `.T00` structure:

```text
uint16LE length
logical byte[length] text, XOR 0xAA, CP852, with page pointers skipped
```

## 8.6 Example `GCHLP` Entry

```text
Topic:  Root
Offset: 3584
Text:   Všeobecné informace o Game-Cheateru ver. 9.00...
```

## 9. `DBSNFO` Database Information Table

## 9.1 Files

```text
DBSNFO.000
DBSNFO.T00
```

`DBSNFO` appears to contain database information, notices, credits, and system text references.

It is not a normal list table like `CHEATDBS`, `FIRMY`, or `GCNETADR`.

## 9.2 Observed Purpose

`DBSNFO.000` contains one main fixed-size record with several numeric values and text offsets.

`DBSNFO.T00` contains long informational texts, warnings, credits, and notices.

## 9.3 `DBSNFO.000` Structure

Observed record size:

```text
42 bytes
```

Observed record count:

```text
1
```

Partially decoded layout:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------------
0x00    ?     unknown    Internal values
0x0C    2     uint16BE   Game-Cheater version code
0x0E    4     uint32LE   Text offset 1
0x12    4     uint32LE   Text offset 2
0x16    4     uint32LE   Text offset 3
0x1A    4     uint32LE   Text offset 4
0x1E    4     uint32LE   Text offset 5
0x22    4     unknown    Unknown numeric field
0x26    4     uint32LE   Text offset 6
```

The version code at offset `0x0C` is:

```text
03 86 = 902 = 9.02
```

## 9.4 Known `DBSNFO` Text Offsets

Observed text offsets:

```text
Offset in record  Value   Meaning
----------------  ------  --------------------------------------------
0x0E              71680   Warning / attention text
0x12              64512   Financial contributors / supporters
0x16              58368   Final notice / closing text
0x1A              56320   Blacklist text
0x1E              19968   Short advice / tips
0x26              1024    Long informational text / essays
```

Examples of decoded text headings:

```text
!!! P O Z O R !!!
finanční přispěvovatelé
ČERNÁ LISTINA
```

## 9.5 `DBSNFO.T00`

Uses the common chained `.T00` block structure:

```text
uint16LE length
logical byte[length] text, XOR 0xAA, CP852, with page pointers skipped
```

## 9.6 Unknowns

The complete meaning of all numeric fields in `DBSNFO.000` is not yet known.

However, the version code and several text offsets are confirmed.

## 10. `GCPRM` Program Parameters Table

## 10.1 File

```text
GCPRM.000
```

No matching `GCPRM.T00` file was provided.

`GCPRM` appears to be a program parameter or configuration table.

## 10.2 Observed Structure

Observed:

```text
Record count: 1
Record size:  100 bytes
```

Partially decoded layout:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------------
0x00    7     bytes      Numeric parameters / internal flags
0x07    80    xorstr     Text parameter, empty in analyzed file
0x57    13    bytes      Additional numeric parameters / flags
```

The 80-byte field at offset `0x07` follows the common XOR `0xAA` + CP852 string pattern, but it is empty in the analyzed file.

## 10.3 Unknowns

The exact meaning of the numeric fields is not yet known.

This file is not required for extracting cheat articles, company descriptions, internet addresses, or help texts.

## 11. Common Parser Strategy

A parser for Game-Cheater databases should implement the following primitive functions:

```text
read_i32le()
read_u16le()
read_u16be()
read_u32le()
decode_xor_string()
read_t00_text_block()
decode_version_code()
```

## 11.1 Reading `.000` Files

General algorithm:

```text
1. Open NAME.000.
2. Read int32LE at offset 0x00.
3. Read uint16LE at offset 0x04 as record_size.
4. Use abs(record_count_raw) when the record count is meaningful.
5. Start reading records at offset 0x06.
6. Read records using record_size.
7. Decode fields according to the table-specific layout.
```

For `CHEATDBS.000`, record count may also be derived from file size:

```python
record_count = (len(data) - 6) // record_size
```

## 11.2 Reading `.T00` Files

General algorithm:

```text
1. Open NAME.T00.
2. For each non-zero text offset:
   1. Read `uint16LE length` at the absolute offset.
   2. Start at `offset + 2` with `remaining = length`.
   3. Copy payload bytes up to the final four bytes of the current 512-byte page.
   4. If more logical bytes remain, read the raw `uint32LE next_page` pointer.
   5. Continue at `next_page` and repeat with up to 508 payload bytes per page.
   6. XOR only the collected logical payload bytes with `0xAA`.
   7. Interpret style controls and decode ordinary bytes as DOS CP852.
```

Python implementation:

```python
def read_text_block(t00_data: bytes, offset: int) -> str | None:
    if offset == 0:
        return None

    if offset < 0 or offset + 2 > len(t00_data):
        return None

    remaining = struct.unpack_from("<H", t00_data, offset)[0]
    position = offset + 2
    encoded = bytearray()
    visited = set()

    while remaining:
        page_rest = 512 - (position % 512)
        if remaining <= page_rest:
            if position + remaining > len(t00_data):
                return None
            encoded.extend(t00_data[position:position + remaining])
            break

        payload_size = page_rest - 4
        pointer_offset = position + payload_size
        if payload_size < 0 or pointer_offset + 4 > len(t00_data):
            return None
        encoded.extend(t00_data[position:pointer_offset])
        remaining -= payload_size
        position = struct.unpack_from("<I", t00_data, pointer_offset)[0]
        if position < 512 or position % 512 or position + 512 > len(t00_data):
            return None
        if position in visited:
            return None
        visited.add(position)

    decoded = bytes(byte ^ 0xAA for byte in encoded).rstrip(b"\x00")
    decoded = bytes(byte for byte in decoded if byte not in {1, 2, 4, 5, 17, 19, 23})
    return decoded.decode("cp852", errors="replace")
```

## 12. Reference Python Extractor

```python
#!/usr/bin/env python3
# File: game_cheater_full_extract.py
# Description: Reference extractor for Game-Cheater 9.02 database files.
# Author: Mario Lacko / ChatGPT
# Created: 2026-06-03
# Version: 1.0
# License: GPL v3

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Optional


XOR_KEY = 0xAA
ENCODING = "cp852"


def xor_decode(data: bytes) -> bytes:
    return bytes(byte ^ XOR_KEY for byte in data)


def decode_xor_string(data: bytes) -> str:
    decoded = xor_decode(data)
    decoded = decoded.rstrip(b"\x00 ")
    return decoded.decode(ENCODING, errors="replace").strip()


def read_i32le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def read_u16le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def read_u16be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def read_u32le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def decode_version_code(code: int) -> str:
    if code == 0:
        return "alias / redirect"

    major = code // 100
    minor = code % 100
    return f"{major}.{minor:02d}"


def read_text_block(t00_data: bytes, offset: int) -> Optional[str]:
    if offset == 0:
        return None

    if offset < 0 or offset + 2 > len(t00_data):
        return None

    remaining = read_u16le(t00_data, offset)
    position = offset + 2
    encoded = bytearray()
    visited = set()

    while remaining:
        page_rest = 512 - (position % 512)
        if remaining <= page_rest:
            if position + remaining > len(t00_data):
                return None
            encoded.extend(t00_data[position:position + remaining])
            break

        payload_size = page_rest - 4
        pointer_offset = position + payload_size
        if payload_size < 0 or pointer_offset + 4 > len(t00_data):
            return None
        encoded.extend(t00_data[position:pointer_offset])
        remaining -= payload_size
        position = read_u32le(t00_data, pointer_offset)
        if position < 512 or position % 512 or position + 512 > len(t00_data):
            return None
        if position in visited:
            return None
        visited.add(position)

    decoded = xor_decode(bytes(encoded)).rstrip(b"\x00")
    decoded = bytes(byte for byte in decoded if byte not in {1, 2, 4, 5, 17, 19, 23})
    return decoded.decode(ENCODING, errors="replace")


def parse_cheatdbs(index_path: Path, text_path: Path) -> list[dict]:
    index_data = index_path.read_bytes()
    text_data = text_path.read_bytes()

    record_size = read_u16le(index_data, 0x04)
    records_start = 0x06

    entries = []

    for record_offset in range(records_start, len(index_data), record_size):
        record = index_data[record_offset:record_offset + record_size]

        if len(record) < record_size:
            break

        source_offset = read_u32le(record, 0x33)
        cheat_offset = read_u32le(record, 0x37)
        version_code = read_u16be(record, 0x3B)

        entries.append({
            "record_offset": record_offset,
            "status": record[0x00],
            "title": decode_xor_string(record[0x01:0x33]),
            "publisher": decode_xor_string(record[0x3D:0x6F]),
            "source_offset": source_offset,
            "cheat_offset": cheat_offset,
            "version_code": version_code,
            "version": decode_version_code(version_code),
            "source": read_text_block(text_data, source_offset),
            "text": read_text_block(text_data, cheat_offset),
        })

    return entries


def parse_firmy(index_path: Path, text_path: Path) -> list[dict]:
    index_data = index_path.read_bytes()
    text_data = text_path.read_bytes()

    record_count = abs(read_i32le(index_data, 0x00))
    record_size = read_u16le(index_data, 0x04)
    records_start = 0x06

    entries = []

    for i in range(record_count):
        record_offset = records_start + i * record_size
        record = index_data[record_offset:record_offset + record_size]

        if len(record) < record_size:
            break

        text_offset = read_u32le(record, 0x33)

        entries.append({
            "record_offset": record_offset,
            "status": record[0x00],
            "company": decode_xor_string(record[0x01:0x33]),
            "text_offset": text_offset,
            "text": read_text_block(text_data, text_offset),
        })

    return entries


def parse_gcnetadr(index_path: Path, text_path: Path) -> list[dict]:
    index_data = index_path.read_bytes()
    text_data = text_path.read_bytes()

    record_count = abs(read_i32le(index_data, 0x00))
    record_size = read_u16le(index_data, 0x04)
    records_start = 0x06

    entries = []

    for i in range(record_count):
        record_offset = records_start + i * record_size
        record = index_data[record_offset:record_offset + record_size]

        if len(record) < record_size:
            break

        description_offset = read_u32le(record, 0x8B)

        entries.append({
            "record_offset": record_offset,
            "status": record[0x00],
            "name": decode_xor_string(record[0x01:0x3D]),
            "url": decode_xor_string(record[0x3D:0x8B]),
            "description_offset": description_offset,
            "description": read_text_block(text_data, description_offset),
        })

    return entries


def parse_gchlp(index_path: Path, text_path: Path) -> list[dict]:
    index_data = index_path.read_bytes()
    text_data = text_path.read_bytes()

    record_count = abs(read_i32le(index_data, 0x00))
    record_size = read_u16le(index_data, 0x04)
    records_start = 0x06

    entries = []

    for i in range(record_count):
        record_offset = records_start + i * record_size
        record = index_data[record_offset:record_offset + record_size]

        if len(record) < record_size:
            break

        text_offset = read_u32le(record, 0x23)

        entries.append({
            "record_offset": record_offset,
            "topic": decode_xor_string(record[0x00:0x23]),
            "text_offset": text_offset,
            "text": read_text_block(text_data, text_offset),
        })

    return entries


def main() -> None:
    exports = {}

    if Path("CHEATDBS.000").exists() and Path("CHEATDBS.T00").exists():
        exports["cheats"] = parse_cheatdbs(Path("CHEATDBS.000"), Path("CHEATDBS.T00"))

    if Path("FIRMY.000").exists() and Path("FIRMY.T00").exists():
        exports["companies"] = parse_firmy(Path("FIRMY.000"), Path("FIRMY.T00"))

    if Path("GCNETADR.000").exists() and Path("GCNETADR.T00").exists():
        exports["internet_addresses"] = parse_gcnetadr(Path("GCNETADR.000"), Path("GCNETADR.T00"))

    if Path("GCHLP.000").exists() and Path("GCHLP.T00").exists():
        exports["help"] = parse_gchlp(Path("GCHLP.000"), Path("GCHLP.T00"))

    output_path = Path("game_cheater_full_export.json")
    output_path.write_text(
        json.dumps(exports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Export written to {output_path}")


if __name__ == "__main__":
    main()
```

## 13. Confirmed Constants

```text
XOR key:               0xAA
Text encoding:         CP852
Common .000 header:    6 bytes
Common .T00 block:     uint16LE logical length + chained 512-byte pages
Text offsets:          absolute offsets into corresponding .T00 file
```

## 14. Known Table Summary

```text
Table      Index file     Text file       Purpose
---------  -------------  --------------  -----------------------------------
CHEATDBS   CHEATDBS.000   CHEATDBS.T00    Main cheat article database
FIRMY      FIRMY.000      FIRMY.T00       Company / publisher database
GCNETADR   GCNETADR.000   GCNETADR.T00    Internet address database
GCHLP      GCHLP.000      GCHLP.T00       Help system database
DBSNFO     DBSNFO.000     DBSNFO.T00      Database information / notices
GCPRM      GCPRM.000      -               Program parameters / configuration
```

THelpViewer exports the user-facing groups as separate UHF bundles:

```text
cheaty.json.gz               CHEATDBS
firmy.json.gz                FIRMY
internetove-adresy.json.gz   GCNETADR
napoveda.json.gz             filtered GCHLP
informace.json.gz            DBSNFO and GCPRM metadata
```

## 15. Unknown or Partially Confirmed Fields

The following fields are still not fully identified:

```text
first 4 bytes of some .000 headers
exact meaning of the status byte in most records
remaining administrative fields in the first 512-byte .T00 header page
whether CHEATDBS version_code means "added in version" or "last updated in version"
all numeric fields in DBSNFO.000
all numeric fields in GCPRM.000
```

These unknowns do not prevent reliable extraction of the main textual content.

## 16. Recommended Export Model

For practical use, the extracted Game-Cheater database can be represented as JSON.

## 16.1 Cheat Entry

```json
{
  "title": "04X - Alien Eliminator",
  "publisher": "",
  "source": "WWW.CHEATY.SK",
  "version": "9.02",
  "text": "Uvedená písmena stiskněte najednou pro daný efekt..."
}
```

## 16.2 Company Entry

```json
{
  "company": "3D Realms",
  "text": "E-mail: help@3drealms.com\nWWW: http://www.3drealms.com/..."
}
```

## 16.3 Internet Address Entry

```json
{
  "name": "Alis",
  "url": "http://www.alis.cz",
  "description": "Stránka autorů PC-Fandu -> zajímavosti, demo verze atd."
}
```

## 16.4 Help Entry

```json
{
  "topic": "Root",
  "text": "Všeobecné informace o Game-Cheateru ver. 9.00..."
}
```

## 17. Implementation Notes

A robust extractor should:

```text
validate all offsets before reading
treat offset 0 as missing text
tolerate malformed or truncated text blocks
decode text with CP852, not UTF-8 or Windows-1250
keep original offsets in exported metadata for debugging
preserve Czech and Slovak text in UTF-8 output
handle negative record counts by using abs()
derive record count from file size when the header count is unreliable
exclude the marker-delimited internal PC-Fand help range from GCHLP
resolve matching underlined GCHLP titles as topic links
normalize mixed box tables only if the target renderer requires consistent borders
export CHEATDBS source and publisher fields as structured topic tags/facets
```

Recommended output encoding:

```text
UTF-8
```

Recommended interchange formats:

```text
JSON
CSV
Markdown
SQLite
```

## 18. Minimal Extraction Checklist

To extract all useful user-facing content:

```text
CHEATDBS:
  title
  publisher
  source
  version
  cheat text

FIRMY:
  company name
  company text

GCNETADR:
  website name
  URL
  description

GCHLP:
  help topic
  help text

DBSNFO:
  version
  informational text blocks

GCPRM:
  optional configuration values
```

## 19. Final Notes

The Game-Cheater 9.02 database format is simple enough to extract reliably.

The most important discoveries are:

```text
1. Fixed-size records are stored in .000 files.
2. Variable-length text blocks are stored in .T00 files.
3. Text is XOR-encoded using key 0xAA.
4. Decoded text uses DOS CP852 encoding.
5. Text offsets are absolute offsets into .T00 files.
6. CHEATDBS stores a version code as uint16BE.
7. The version code maps cleanly to Game-Cheater versions such as 9.02.
```

This is sufficient to implement a complete extractor and convert the original Game-Cheater data into modern formats.
