# MicroCalc Text Help

> Updated: 2026-10-11

Used by Borland Turbo Basic's MicroCalc example. Original file: `MC.HLP`.
This is a paginated display-text format, not THELP, FBHF or QuickHelp.

## Evidence and structure

The original `MC4.INC`, `SUB HELP`, on Disk02.img in
`Borland Turbo Basic 1.0 (1987) (5.25-360k)` reads MC.HLP with `LINE INPUT`.
`MC0.INC` defines LowColor=7 and NormColor=14; `MC1.INC` implements the
LowVideo/NormVideo calls. These are runtime-source evidence, not guessed colors.
Current originals: English CRC32 `559E061B` (5,326 bytes) and German
`CEA5FAE6` (6,277 bytes; present in two source collections).

There is no binary header or stored topic/context table. Lines use CRLF and
OEM text; the verified German characters decode in CP437. A trailing DOS
text EOF byte `1A` is not displayed. A line starting with the exact uppercase
three bytes `.PA` ends a page; that directive itself is not displayed.

| Byte | Original behavior |
| --- | --- |
| `02` | Toggle the Bold flag. On selects foreground 14/background 0; off selects 7/0. |
| `09` | Toggle the Revers flag. On selects 0/7; off selects 7/0. This is not a tab stop. |
| CRLF | End a display line, without resetting flags. |

Both flags and the current colors reset at each page. They are independent
flags but each control sets the current colors directly: toggling Bold can
replace an active reverse color, without clearing the Revers flag. Treating
them as independently nested bold/reverse styles would be inaccurate.
The routine prints five leading spaces on every line. It advances pages by
a key press; no hyperlink target records are present.

Minimal synthetic example (escapes denote bytes):

```text
\x09Introduction\x09\r\n
Text with \x02highlight\x02.\r\n
.PA\r\n
Next page.\r\n\x1A
```

## Fields not stored

There are no numeric topic IDs, index offsets, display-width fields or RGB
palettes. Page order follows `.PA` boundaries; screen size and key handling
belong to the application.
