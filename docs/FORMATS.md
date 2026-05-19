# Help File Format Documentation

> Created: 2026-03-29 · Last updated: 2026-05-17

Index of supported help file binary and source formats.

## Binary Format Specifications

- Borland THELP: [Formats/Borland THELP.md](Formats/Borland%20THELP.md) — TP4–7, Turbo C, TASM, Sidekick, Sprint
- Borland Turbo Debugger/Profiler runtime help: [Formats/Borland TDH.md](Formats/Borland%20TDH.md) — separate TDH/TFH runtime-help family, decoded for the known sample families
- TurboVision FBHF: [Formats/TurboVision FBHF.md](Formats/TurboVision%20FBHF.md) — TP6, BP7 THelpFile (TVHC)
- Software602 family index: [Formats/Software602.md](Formats/Software602.md) — M602, Text602, Calc602
- Software602 M602 HelpSystem: [Formats/Software602 M602.md](Formats/Software602%20M602.md) — XOR $FA encrypted
- Software602 Text602 help: [Formats/Software602 Text602.md](Formats/Software602%20Text602.md) — chunk-based +1 encoding
- Norton Guide (NG): [Formats/Norton Guide.md](Formats/Norton%20Guide.md) — DOS binary help, menu tree, cross-references
- Microsoft BW03 Help: [Formats/Microsoft BW03 Help.md](Formats/Microsoft%20BW03%20Help.md) — older DOS/OS2 CodeView help (`CV.HLP`, `CVP.HLP`)
- Microsoft QuickHelp (LN): [Formats/Microsoft QuickHelp.md](Formats/Microsoft%20QuickHelp.md) — QB 4.5, QuickC 2.0, MASM 6, PWB, LINK

## Source Text Format

- Help Source Text Format: [Formats/Help Source Text Format.md](Formats/Help%20Source%20Text%20Format.md) — HLX/TXT directive-based source for compilers and decompilers

## Experimental

- Scorpion Cheater DAT: [Formats/Scorpion Cheater DAT.md](Formats/Scorpion%20Cheater%20DAT.md) — proprietary DOS content database used by Scorpion's Cheater 23.0, with experimental container/index/topic support

## Format Comparison

| Feature              | Borland THELP        | TurboVision FBHF      | Software602                          | MS QuickHelp                         |
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
| `python -m thelpviewer.converter` | Python | Universal reader (all supported formats) → HTML / JSON bundle / Markdown |
| `python -m thelpviewer.converter --bundle` | Python | Gzip-compressed JSON bundles for the SPA viewer |
| `python -m downloader` | Python | Automated help file downloader (WinWorldPC, archive.org, old-dos.ru, GitHub, DaveP NG mirror) |

---

*Part of the [THelpViewer](https://github.com/) project.*
