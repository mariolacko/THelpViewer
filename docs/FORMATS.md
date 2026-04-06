# Help File Format Documentation

> Created: 2026-03-29 · Last updated: 2026-04-05

Index of supported help file binary and source formats.

## Binary Format Specifications

- Borland THELP: [Formats/Borland THELP.md](Formats/Borland%20THELP.md) — TP4–7, Turbo C, TASM, Sidekick, Sprint
- TurboVision FBHF: [Formats/TurboVision FBHF.md](Formats/TurboVision%20FBHF.md) — TP6, BP7 THelpFile (TVHC)
- Software602 family index: [Formats/Software602.md](Formats/Software602.md) — M602, Text602, Calc602
- Software602 M602 HelpSystem: [Formats/Software602 M602.md](Formats/Software602%20M602.md) — XOR $FA encrypted
- Software602 Text602 help: [Formats/Software602 Text602.md](Formats/Software602%20Text602.md) — chunk-based +1 encoding

## Source Text Format

- Help Source Text Format: [Formats/Help Source Text Format.md](Formats/Help%20Source%20Text%20Format.md) — HLX/TXT directive-based source for compilers and decompilers

## Format Comparison

| Feature              | Borland THELP        | TurboVision FBHF      | Software602                          |
|----------------------|----------------------|-----------------------|--------------------------------------|
| Magic/Signature      | `$*$* &&&&$*$`       | `FBHF` ($46484246)    | `$1A(c) Software602 HelpSystem`      |
| Encryption           | None                 | None                  | XOR $FA                              |
| Text compression     | Nibble (4-bit codes) | None (raw text)       | None                                 |
| Character encoding   | CP437                | CP437 / Latin-1       | Kamenicky (KEYBCS2)                  |
| Topic identification | Context array + offset | Stream position + index | Sequential records                 |
| Hyperlinks           | Keyword records      | Cross-reference array | Inline $02 markers                   |
| Word wrap            | Fixed width display  | Per-paragraph flag    | Display-side only                    |
| Index structure      | Prefix-compressed    | Sorted array or simple array | None (sequential)              |
| Max topics           | 65535 (24-bit offset)| 65535 (Word context)  | ~255 (practical)                     |
| Created by           | Various Borland tools| TVHC compiler         | Unknown (proprietary)                |
| Era                  | 1987-1992            | 1990-1993             | ~1990-1995                           |

## Tools

| Tool | Language | Purpose |
|------|----------|---------|
| `python -m converter` | Python | Universal reader (all 4 formats) → HTML / JSON bundle / Markdown |
| `python -m converter --bundle` | Python | Gzip-compressed JSON bundles for the SPA viewer |
| `python -m downloader` | Python | Automated help file downloader (WinWorldPC, archive.org, old-dos.ru) |

---

*Part of the [THelpViewer](https://github.com/) project.*
