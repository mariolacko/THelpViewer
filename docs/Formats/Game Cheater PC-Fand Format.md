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
0x00    4     int32LE    Signed record count; its absolute value is the active count
0x04    2     uint16LE   Record size
```

In some files the record count is stored as a negative integer.
In that case, the real number of records can be obtained using:

```python
record_count = abs(record_count_raw)
```

The sign distinguishes the native table kind; it is not a deletion count.
`RdPrefix` uses the absolute value for the record count, and `WrPrefix` writes
negative counts for type X tables. Zero denotes zero active records even if
unused physical slots remain. The record size at `0x04` determines each
record boundary. Record `i` starts at `6 + i*record_size` for
`0 <= i < abs(record_count_raw)`.
See PC-Fand's [`RdPrefix` / `WrPrefix`](https://github.com/alisoss/pcfand/blob/master/pas/FILEACC.PAS).

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
There is no required NUL terminator. A NUL inside the logical payload is
still a byte in that field and does not shorten the declared length.
Texts longer than the remaining payload space of a page are not contiguous.
PC-Fand reserves the final four bytes of each continued 512-byte page for a
little-endian absolute pointer to the next page:

```text
Memo page size: 512 bytes
Continued first page at a page boundary:
               uint16LE length + 506 payload bytes + uint32LE next_page
Continued next page:
               508 payload bytes + uint32LE next_page
Final first page:
               uint16LE length + up to 510 payload bytes
Final continuation page:
               up to 512 payload bytes; no pointer is consumed
```

The payload bytes are XOR-encoded, but the four-byte page pointers are raw
PC-Fand file offsets and must not be XOR-decoded. A naive contiguous read works
only for texts that fit after their two-byte header in the current page, and
exposes the pointer bytes as visible
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
A repeated `B5h` sequence therefore need not be box drawing. Some text
tables mix glyph assignments from different display fonts. Character identity
cannot be established by byte repetition alone; preserve the byte/font context
where the encoding assignment is ambiguous.

### 4.3.1 Inline Style Controls

After page-chain reconstruction and XOR decoding, text can contain PC-Fand
toggle controls. The same byte opens and closes a style:

```text
Byte  Pascal name  Meaning
----  -----------  ---------------------
0x01  Ctrl-A       elite typeface
0x02  Ctrl-B       emphasized
0x04  Ctrl-D       double strike
0x05  Ctrl-E       compressed typeface
0x11  Ctrl-Q       double width
0x13  Ctrl-S       underline
0x17  Ctrl-W       italic
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
Single and double border characters remain distinct source glyphs; the mixed
borders are not an instruction to replace them. `WrStyleChar` changes the
attribute for style controls and writes ordinary characters unchanged; it
does not infer table geometry or substitute border glyphs. See
[`COMMON.PAS`](https://github.com/alisoss/pcfand/blob/master/pas/COMMON.PAS).

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
0x00    4     int32LE    Signed record count; absolute value gives the record count
0x04    2     uint16LE   Record size
```

For Game-Cheater 9.02:

```text
Record count = -3301 (3,301 records)
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

The first 512 bytes are the Pc-Fand memo-file header; they are not article
payload. Native `TFile.Read` rejects nonzero text offsets in that header.
The full administrative/encryption field layout is not specified here.

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
0x00    4     int32LE    Signed record count
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
0x00    4     int32LE    Signed record count
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
PC-Fand's internal runtime help, separated by marker records.

## 8.2 Purpose

This database stores help topics and help article texts.

## 8.3 `GCHLP.000` Header

Uses the common `.000` header:

```text
Offset  Size  Type       Description
------  ----  ---------  ---------------------------------------
0x00    4     int32LE    Signed record count
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

The markers delimit the embedded PC-Fand help range; they are stored records.
The analyzed `GCHLP.000` has 531 physical records. The embedded PC-Fand range
starts at record 149 and ends at record 508 (zero-based); valid Game-Cheater
help continues after the end marker. The range uses the same name/text fields
and participates in the same physical-order name lookup; its boundaries do
not create another lookup namespace. For example, `Int_help` first resolves
inside this range, even though another similarly named record occurs later.
There are 486 nonblank stored names, 383 nonempty memo texts and 103 named
empty records in this specimen. Empty named records can forward lookup to
the next physical record with nonempty text, as described below.

## 8.4.4 Hypertext Links

In help mode, paired Ctrl-S bytes (`13h`) delimit selectable words. The
selected delimiters are temporarily changed to Ctrl-Q (`11h`) in the editor
buffer; this selection state is not a separate stored numeric destination.
The selected word supplies the lookup text. Other style controls inside the
word are bytes of that lookup text, not instructions to remove them. Example:

```text
Viz.: Ctrl-S "O programu" Ctrl-S
```

Name lookup scans records from physical record 1 through the declared count:

1. Remove trailing padding spaces from the stored 35-byte name.
2. Convert the clicked name and stored name to non-diacritic bytes using
   the current video-font profile, then compare using the runtime's
   configured character-order table.
3. The stored name is a mask; the clicked word is its input. Stop at the
   first matching record, not the nearest record or the best-looking title.
4. Read its memo. If its logical length is zero, advance through subsequent
   physical records until a nonempty memo or the final record is reached.
   Do not repeat the name comparison while advancing. Both offset zero and
   an assigned zero-length memo have this forwarding behavior.
5. If no name matches, the consumer can continue through parent application
   help files. That parent chain belongs to runtime configuration, not to
   the `.000` record or an inferred same-caption destination.

The default Latin2 profile uses the following non-diacritic byte table.
ASCII bytes below `80h` are unchanged; the first row below maps input
`80h..8Fh`, and subsequent rows advance by `10h`:

```text
43 75 65 61 61 75 63 63 6C 65 4F 6F 69 5A 41 43
45 4C 6C 6F 6F 4C 6C 53 73 4F 55 54 74 4C 9E 63
61 69 6F 75 41 61 5A 7A 45 65 61 7A 43 73 AE AF
B0 B1 B2 B3 B4 41 41 45 53 B9 BA BB BC 5A 7A BF
C0 C1 C2 C3 C4 C5 41 61 C8 C9 CA CB CC CD CE CF
64 44 44 45 64 4E 49 49 65 D9 DA DB DC 54 55 DF
4F E1 4F 4E 6E 6E 53 73 52 55 72 55 79 59 74 EF
F0 F1 F2 F3 F4 F5 F6 F7 F8 F9 FA 75 52 72 FE FF
```

The default character-order table compares ASCII letters without case after
this conversion. Comparison is byte-based: spaces are not collapsed, `ß`
does not expand to `ss`, and literal brackets are not markup. Custom
character-order tables and other video-font profiles require their external
configuration; they cannot be reconstructed from `GCHLP.000` alone.

Mask syntax is the native `EqualsMask` grammar, not regular DOS filename
matching. An ordinary byte compares one folded byte. `?` consumes exactly
one input byte. A final `*` accepts the remaining input, including none.
Otherwise `*` consumes the next mask byte as a **literal** and searches for
that byte in the input; after each occurrence it tries the remaining mask
against the remaining input. Thus `*?` matches an input ending in a literal
question mark, and `**` needs a literal asterisk; neither means two generic
wildcards. The complete mask must match the complete clicked name.

Examples for the Latin2/default profile:

```text
clicked "Hledání cheatu"  matches stored "hledání cheatů"
clicked "root "          does not match stored "root"
clicked "ABC?"           matches stored "*?"
clicked "ABC"            does not match stored "*?"
```

If record 6 has name `Alias` and zero text offset, record 7 has an assigned
zero-length memo, and record 8 contains text, lookup of `Alias` returns record
8. Its name need not be `Alias`. A later duplicate `Alias` does not override
the first match.

The native Help command requests the name `root` for F1. This is a consumer
convention, not a numeric Contents field in the table header.

## 8.4.5 Hidden Description Line

If a selected memo begins with byte `7Bh` (`{`), the help display omits its
first line. It locates the first `0Dh`, advances over it and one immediately
following `0Ah`, then displays the remaining bytes. A following blank line
is preserved. No closing `}` is required by this test. If no `0Dh` occurs,
the entire memo is hidden, even if it contains standalone `0Ah` bytes.
The stored length and memo bytes remain unchanged; name lookup tests that
original length before this display-only removal.

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
4. Use abs(record_count_raw); zero denotes an empty table.
5. Start reading records at offset 0x06.
6. Read records using record_size.
7. Decode fields according to the table-specific layout.
```

File size supplies a validation bound, not a replacement count:

```python
assert (len(data) - 6) % record_size == 0
available_slots = (len(data) - 6) // record_size
assert abs(record_count_raw) <= available_slots
```

## 11.2 Reading `.T00` Files

General algorithm:

```text
1. Open NAME.T00.
2. For each non-zero text offset:
   1. Read `uint16LE length` at the absolute offset.
   2. Start at `offset + 2` with `remaining = length`.
   3. Let `rest = 512 - (position % 512)`.
   4. If `remaining <= rest`, copy exactly `remaining` bytes and finish.
      Otherwise, copy `rest - 4` bytes and read the raw `uint32LE next_page`.
   5. Continue at `next_page` and repeat with up to 508 payload bytes per page.
   6. XOR only the collected logical payload bytes with `0xAA`.
   7. Interpret style controls and decode ordinary bytes as DOS CP852.
```

Boundary-checked payload algorithm (the returned bytes still contain styles):

```python
import struct

def read_text_block(t00_data: bytes, offset: int) -> bytes | None:
    if offset == 0:
        return None

    if offset < 512 or offset + 2 > len(t00_data):
        raise ValueError("Invalid memo header")

    remaining = struct.unpack_from("<H", t00_data, offset)[0]
    position = offset + 2
    encoded = bytearray()
    visited = {offset - offset % 512}

    while remaining:
        page_rest = 512 - (position % 512)
        if remaining <= page_rest:
            if position + remaining > len(t00_data):
                raise ValueError("Incomplete memo text")
            encoded.extend(t00_data[position:position + remaining])
            break

        payload_size = page_rest - 4
        pointer_offset = position + payload_size
        if payload_size < 0 or pointer_offset + 4 > len(t00_data):
            raise ValueError("Incomplete memo continuation pointer")
        encoded.extend(t00_data[position:pointer_offset])
        remaining -= payload_size
        position = struct.unpack_from("<I", t00_data, pointer_offset)[0]
        if position < 512 or position % 512 or position + 512 > len(t00_data):
            raise ValueError("Invalid memo continuation page")
        if position in visited:
            raise ValueError("Cyclic memo chain")
        visited.add(position)

    return bytes(byte ^ 0xAA for byte in encoded)
```

## 12. Structural validation

A table header must contain all six bytes and the declared record size must
match its table layout. Compute `count = abs(i32le(0))`; zero is an empty
table, not a request to scan every allocated slot. For file size `S` and
record size `R`, require `(S-6) mod R = 0` and `count <= (S-6)/R`.
Whole slots after the declared count are not additional active records.
Do not replace a declared count with the physical slot count or silently
stop after an incomplete record.

Memo offset zero denotes an unassigned field. A nonzero offset must be at
least 512 and leave both length bytes inside the memo file. A valid length
of zero denotes assigned empty text, distinct from an absent field. Read
exactly the declared logical payload; physical EOF is not an implicit text
terminator.

Check every payload read and raw continuation DWORD before using it.
Continuation addresses identify complete, 512-aligned pages at or beyond
byte 512. Include the initial containing page in the visited set; returning
to it is a cycle even when the remaining length could fit in that page.
A backward pointer to a different, unvisited page is not itself a cycle.
A missing member of a present index/memo pair cannot supply empty article
text; the referenced memo must be available.

The length/count fields do not store a complete-file checksum. Removing
unreferenced memo pages or unused whole record slots cannot always be detected
from the referenced content alone. Arbitrary file-integrity verification
requires a trusted external length or digest.

## 13. Confirmed Constants

```text
XOR key:               0xAA
Text encoding:         CP852
Common .000 header:    6 bytes
Common .T00 block:     uint16LE logical length + chained 512-byte pages
Text offsets:          absolute offsets into corresponding .T00 file
```

### 13.1 Byte examples

`FD FF FF FF 6F 00` is a six-byte table header with signed count -3 and
record size 111; the three active records occupy bytes 6 through 338.
The count's sign does not reverse their order.

At memo offset 512, `03 00 EB E8 E9` declares three logical bytes.
XOR `AAh` gives `41 42 43` (ABC). No NUL terminator is required.

For a 511-byte memo beginning at 512, the length WORD is `FF 01`.
The first 506 encoded bytes occupy 514..1019; the raw pointer at 1020
can be `00 06 00 00`, selecting page 1536. Its first five bytes finish the
logical text. The physical gap at page 1024 is not part of the text.

For a 1,018-byte memo, the length WORD is `FA 03`. After the same first
506 bytes and pointer, all 512 bytes at 1536..2047 are final-page payload.
Bytes 2044..2047 are then encoded text, not another pointer. The comparison
is against the whole page remainder, not a permanent 508-byte capacity.

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

## 15. Unknown or Partially Confirmed Fields

The following fields are still not fully identified:

```text
exact meaning of the status byte in most records
remaining administrative fields in the first 512-byte .T00 header page
whether CHEATDBS version_code means "added in version" or "last updated in version"
remaining numeric fields in DBSNFO.000
all numeric fields in GCPRM.000
```

These unknowns do not prevent reliable extraction of the main textual content.

## 16. Minimal Extraction Checklist

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

## 17. Storage Summary

Core storage rules:

```text
1. Fixed-size records are stored in .000 files.
2. Variable-length text blocks are stored in .T00 files.
3. Text is XOR-encoded using key 0xAA.
4. Decoded text uses DOS CP852 encoding.
5. Text offsets are absolute offsets into .T00 files.
6. CHEATDBS stores a version code as uint16BE.
7. The version code maps cleanly to Game-Cheater versions such as 9.02.
```
