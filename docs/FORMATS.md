# Help File Format Documentation

> Created: 2026-03-29 · Last updated: 2026-10-14

Index of supported help file binary and source formats.

## Binary Format Specifications

- Borland THELP: [Formats/Borland THELP.md](Formats/Borland%20THELP.md) — TP4–7, Turbo C, TASM, Sidekick 2, Sprint
- Borland Sidekick 1: [Formats/Borland Sidekick 1 Help.md](Formats/Borland%20Sidekick%201%20Help.md) — uncompressed screen contexts and intra-context pages; not Sidekick Plus
- Borland Sidekick Plus: [Formats/Borland Sidekick Plus Help.md](Formats/Borland%20Sidekick%20Plus%20Help.md) — paragraph-addressed screen groups, native redirects, scoped hotspots and pages
- Borland Turbo Debugger/Profiler runtime help: [Formats/Borland TDH.md](Formats/Borland%20TDH.md) — separate TDH/TFH runtime-help family, decoded for the known sample families
- TurboVision FBHF: [Formats/TurboVision FBHF.md](Formats/TurboVision%20FBHF.md) — TP6, BP7 THelpFile (TVHC)
- Software602 family index: [Formats/Software602.md](Formats/Software602.md) — M602, Text602, Calc602
- Software602 M602 HelpSystem: [Formats/Software602 M602.md](Formats/Software602%20M602.md) — XOR $FA encrypted
- Software602 Text602 help: [Formats/Software602 Text602.md](Formats/Software602%20Text602.md) — encoded Turbo Vision paragraphs and context index
- Norton Guide (NG): [Formats/Norton Guide.md](Formats/Norton%20Guide.md) — DOS binary help, menu tree, cross-references
- Microsoft BW03 Help: [Formats/Microsoft BW03 Help.md](Formats/Microsoft%20BW03%20Help.md) — older DOS/OS2 CodeView help (`CV.HLP`, `CVP.HLP`)
- Microsoft QuickHelp (LN): [Formats/Microsoft QuickHelp.md](Formats/Microsoft%20QuickHelp.md) — QB 4.5, QuickC 2.0, MASM 6, PWB, LINK
- Borland compiled HLX: [Formats/Borland HLX Binary.md](Formats/Borland%20HLX%20Binary.md) — standalone Windows Help keyword B+ tree; article data belongs to the companion HLP
- Windows Help HC31: [Formats/Windows Help.md](Formats/Windows%20Help.md) — container, compression, native articles, paragraph/table/font commands and context-hash links; fixed-cell text conversion
- Game-Cheater 9.02 / PC-Fand: [Formats/Game Cheater PC-Fand Format.md](Formats/Game%20Cheater%20PC-Fand%20Format.md) — paired `.000` records and `.T00` text blocks

## Source Text Format

- Help Source Text Format: [Formats/Help Source Text Format.md](Formats/Help%20Source%20Text%20Format.md) — HLX/TXT directive-based source for compilers and decompilers
- HelpPC 2.10: [Formats/HelpPC 2.10.md](Formats/HelpPC%202.10.md) — keyed CP437 text databases and tilde links
- FreeDOS HTML Help: [Formats/FreeDOS HTML Help.md](Formats/FreeDOS%20HTML%20Help.md) — HTML pages in `HHSTNDRD.ZIP`
- MicroCalc text help: [Formats/MicroCalc Text Help.md](Formats/MicroCalc%20Text%20Help.md) — Turbo Basic example, `.PA` pages and inline display controls
- DOS text help: [Formats/DOS Text Help.md](Formats/DOS%20Text%20Help.md) — uncompiled CP437 `.HLP`, including Turbo Prolog main/example helps
- Turbo Prolog help database: [Formats/Turbo Prolog Help Database.md](Formats/Turbo%20Prolog%20Help%20Database.md) — validated `h("…")` display records

## Source Containers

- DOS BACKUP: [Formats/DOS BACKUP Source Container.md](Formats/DOS%20BACKUP%20Source%20Container.md) — validated 128-byte single-volume wrapper, decoded before the inner HELP format
- Microsoft SZ/SZDD: [Formats/Microsoft SZ Compression.md](Formats/Microsoft%20SZ%20Compression.md) — LZSS installer wrapper and numbered split-media continuation headers

## Experimental

- Scorpion Cheater DOS: [Formats/Scorpion Cheater DAT.md](Formats/Scorpion%20Cheater%20DAT.md) — modern DAT articles and native TextScreen/font resources; earlier DOS containers and unresolved legacy graphics

## Coverage limits (2026-10-14 corpus)

M602's original row assembly verifies all 201 topics, 3,012 display rows and
406 hotspot coordinates at 78 cells, including authored title/block art and
raw-byte soft wrapping. The published view remains a fixed-width projection.

Game-Cheater's Nápověda retains the embedded Pc-Fand help: 383 text articles,
103 native empty-record aliases and 486 named Index/Contents entries. All
669 Ctrl-S links match an independent physical-record lookup using the
native byte fold and mask grammar. This verifies the installed 9.02 database;
other fonts, character-order tables and parent-database lookup require their
external runtime configuration.

Scorpion's modern DAT container validation covers 26 originals and all 579
DATA objects. Their 15,144 supported DOS articles retain their complete text,
Index and Contents; malformed compressed lengths fail instead of publishing
partial data. v21 TEXTY's SC 2000 catalog now retains title/row navigation and
verified CHEATY links. Its four prose objects' fonts and native pixel-based
page targets remain unresolved in TODO, alongside the separate graphics work.
Modern PROGRAM exports also retain 48 native 80×25 text screens as byte-exact
Base64 character/attribute blocks, shared bitmap fonts and UHF palette indexes,
without changing the existing article IDs/text. Legacy v6–v14 adds 56 native
text screens and verified LZHUF fonts; v4/v5 inline artwork also uses its
original default font. The three v6 bit-7 templates use an explicit standard
DOS blink profile. Indexed raster palettes remain unresolved; they are not
PNG substitutions. SC 2000 prose extraction retains complete DATA bytes;
its in-word `FEh`, encoding/font bindings and native page targets still need
consumer evidence.

All 20 compiled HLX originals now expose their declared keyword records, not
guessed articles or hotspots from unused memory. Their matching 4.52 HLPs
now supply verified native article records and keyword destinations, with
two distinct 4.5 HLP/HLX pairs retained separately. All 22 HC31 HLPs now have
text article conversion, authored paragraph/tab/table layout, styled text
and native keyword/inline targets. Their 39,035 native article headers are
not the earlier keyword ordinals. Paired HLX files are source companions,
not duplicate text conversions; a standalone HLX is not a full-text manual.
Bitmap/metafile pixels, image-region links and special Windows macro/UI
behavior remain outside the fixed-cell text projection.

The 496 inspected originals have 356 selected conversion inputs, now including
22 Windows HLPs instead of their same-stem index-only HLX companions. The 22
paired indexes remain retained originals but are not built a second time.
The remaining
118 are companion tables, fonts, screens, licences or other non-conversion
inputs. Profiler 1.01 TFH now includes its real cumulative-end page: 367
contexts and 325 intact hotspots. Both TFH revisions use runtime-verified
48-column text; original decoder execution confirms every row and span.
Older TDH now uses the same 48-cell/NUL alphabet, with its own native hotspot
fit rule. Both 1.5 editions and 2.x retain their final cumulative-end page;
literal-caret controls no longer truncate Pascal operator help. Older native
word-wrap hotspot-coordinate quirks remain documented separately; the decoder
reflows all six affected link labels onto their displayed cells, retaining
targets and native text.
Six newer TDH/TD32/TDW originals now decode into 4,602
topics with all 4,423 hotspots resolving. Sidekick 1.56b and TASM 2.01 add
distinct supported editions, as does the newly retained German Debugger 1.5
HELP; its English counterpart was already present. Exact 2.0 duplicates are
not copied again, and the 2.0 bundle no longer collides with another edition.
Sidekick Plus now imports all distinct text pages and preserves
its 2,051 hotspots and resolves the three native redirects. Six targets have
unused source descriptors and also fail in the original reader. Besides
Sidekick 1/Plus, the newly covered 26
originals are three
MicroCalc files, 22 DOS-text Prolog helps (two in DOS BACKUP wrappers), and one
two-record Prolog help database, including duplicate editions. A catalog CRC
or product choice is not proof of decoder support. Unverified binary inputs
need structural/runtime evidence; do not treat an unknown `.HLP` as an existing
binary format or generic text. These counts describe the inspected local corpus,
not every historical revision of the formats.

## Format Comparison

| Feature              | Borland THELP        | TurboVision FBHF      | Software602 M602                     | MS QuickHelp                         |
|----------------------|----------------------|-----------------------|--------------------------------------|--------------------------------------|
| Magic/Signature      | `$*$* &&&&$*$`       | `FBHF` ($46484246)    | `$1A(c) Software602 HelpSystem`      | `LN` + `\x02\x00`                    |
| Encryption           | None                 | None                  | XOR $FA                              | None                                 |
| Text compression     | Nibble (4-bit codes) | None (raw text)       | None                                 | Huffman + keyword dict + RLE         |
| Character encoding   | CP437                | CP437 / Latin-1       | Kamenicky (KEYBCS2)                  | CP437 / Latin-1                      |
| Topic identification | Context array + offset | Stream position + index | Sequential records                 | Context string → topic index map     |
| Hyperlinks           | Keyword records      | Cross-reference array | Inline $02 markers                   | Attr block link records              |
| Word wrap            | Fixed width display  | Per-paragraph flag    | Display-side only                    | Display-side only                    |
| Index structure      | Prefix-compressed    | Sorted array or simple array | None (sequential)              | Context string array                 |
| Max topics           | 65535 (24-bit offset)| 65535 (Word context)  | ~255 (practical)                     | 65535 (Word topic index)             |
| Created by           | Various Borland tools| TVHC compiler         | Unknown (proprietary)                | HELPMAKE.EXE (Microsoft)             |
| Era                  | 1987-1992            | 1990-1993             | ~1990-1995                           | 1989-1994                            |

## Tools

| Tool | Language | Purpose |
|------|----------|---------|
| `python -m thelpviewer.server.converter` | Python | Universal reader (all supported formats) → HTML / JSON bundle / Markdown |
| `python -m thelpviewer.server.converter --bundle` | Python | Gzip-compressed JSON bundles for the SPA viewer |
| `python -m thelpviewer.server.downloader` | Python | Automated help file downloader (WinWorldPC, archive.org, old-dos.ru, GitHub, DaveP NG mirror) |

---

*Part of the [THelpViewer](https://github.com/mariolacko/THelpViewer) project.*
