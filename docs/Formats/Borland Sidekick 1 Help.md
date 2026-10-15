# Borland Sidekick 1 Help

> Updated: 2026-10-11

Sidekick 1's `SK.HLP` is an uncompressed screen/page stream, not THELP,
FBHF, Windows WinHelp or the later Sidekick Plus format. The local original
has CRC32 `6AE04030`, 42,240 bytes, 67 contexts and 148 display pages.
A second original from the Sidekick 1.56b disk image has CRC32 `0EA517F6`,
53,632 bytes, 72 contexts and 179 pages. The different version tags and
context counts must not be treated as fixed format signatures.
## File and context structure

```text
WORD version_tag           little-endian, opaque executable/HLP pairing tag
context 0
context 1
...
optional 1A + DOS record padding
```

Each context is:

| Field | Bytes | Meaning |
| --- | ---: | --- |
| rows | 1 | Display-height parameter |
| columns | 1 | Display-width parameter |
| text/pages | variable | Attribute selectors, OEM characters and CRLF |
| terminator | 1 | `00`: end of this context |

The first context in both verified English originals is
`01 0C 02 "Help text #0" 00`. It is a placeholder, not a file title or a
topic-count field. Main general help is context 1. Context IDs are ordinal
record numbers starting at zero. An executable's category/command tables
choose these contexts; those tables are outside the HLP file.

The two version-tag words are `5DEBh` and `2BE4h`. Their numeric relationship
to a release number or checksum algorithm has not been established. The
executable/HLP pairing cannot be validated without the corresponding executable.

## Display controls

| Byte | Native meaning |
| --- | --- |
| `01` | Select the window's emphasis attribute (descriptor offset `+7`). |
| `02` | Select the normal attribute (`+6`). |
| `04` | Select the key-label attribute (`+8`). |
| `03` | Page boundary inside the current context, not a new context. |
| `00` | Context terminator, not a displayed NUL. |
| `0D 0A` | Return to the left column and advance one display row. |
| `11`, `18`, `19`, `1A`, `1B` | Ordinary VGA/OEM glyphs, including arrows. |

Attribute selections persist across lines and page boundaries. They replace
one another; they are not independently nested styles. Native window clearing
retains the current attribute. Both current originals start each page with `02`.
Colors come from the executable/window configuration, not the HLP, so there is
no intrinsic HLP RGB/CGA palette to infer. The printer handles `08` as cursor
backspace; other non-structural low bytes are VGA glyphs, not ANSI controls.
In particular, `09` is the circle glyph, not an eight-column TAB stop.

`1A` inside a context is the right-arrow glyph. It marks EOF only at a context
boundary. Both originals are rounded to 128-byte DOS records: bytes after the
EOF marker are stale buffer padding, including fragments of prior text. They
must not be imported as another article.

## Boundaries and unspecified operations

The two size bytes are display dimensions, not a text-record length.
Scan page/control bytes until the context's NUL terminator; only then read
another context's dimensions. Keep `03` page boundaries in the same context.
Final `1A` and padding belong to the last 128-byte DOS record.

The printer's `FF` raw-character operation depends on application register
state; its complete byte grammar is not established here. Cursor backspace
and bare CR/LF behavior also require the application's display rules.

Synthetic two-page context:

```text
02 14 02 "First page" 03 01 "Second page" 02 00
```

Here `02 14` are dimensions (2 rows, 20 columns); the next `02` selects
normal text. The two pages belong to one context.
