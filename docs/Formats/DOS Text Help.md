# DOS Text Help

> Updated: 2026-10-11

An uncompiled `.HLP` can be a display-text document rather than a binary help
database. The current examples are Turbo Prolog's main and example-program
helps: PROLOG, GEOBASE, DIFF, GENI, SCRDEF, SANAL/SEN_AN, PIE and REGISTER.
The extension alone is not a format signature.

## Verified original structure

These originals contain ordinary CRLF-separated OEM text, spaces, horizontal
tabs and CP437 box/block glyphs. Some end with DOS text EOF (`1A`); others do
not. They do not store a topic index, numeric help contexts or hyperlink records.
Program names in their paragraphs are plain references, not encoded links.
No `.PA` commands or MicroCalc highlight controls occur in these Prolog samples.

Two Prolog 1.0 copies, GEOBASE.HLP (`2B446AAB`) and PROLOG.HLP (`5C5EE722`),
have a separate [DOS BACKUP container](DOS%20BACKUP%20Source%20Container.md).
Removing that validated 128-byte header exposes the same bytes as the plain
GEOBASE (`E71708C8`) and PROLOG (`FB92DEEC`) copies. The wrapper is not part
of the Prolog display-text format.

## Byte interpretation

Read CRLF as a physical line boundary; preserve spaces and blank lines.
TAB uses conventional eight-column DOS stops. Optional final `1A` is DOS
text EOF, not display text. Ordinary bytes use the application's OEM code page;
these examples use CP437.

There are no stored numeric contexts, title fields or navigation records.
A first line resembling a heading is ordinary source text.

Example:

```text
Screen layout\r\n
\tF1: Help\r\n
\tF10: Finish\r\n\x1A
```

## Format boundaries

This description covers uncompiled DOS display text. It does not assign meanings
to NUL, terminal color controls, Prolog predicates or binary HELP headers.
The filename extension does not identify a control grammar or encoding.
