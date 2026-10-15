# Turbo Prolog Help Database

> Updated: 2026-10-11

Original example: Turbo Prolog 1.0 `XHELP.HLP`, CRC32 `F361F5DA`, 265 bytes.
Unlike the ordinary Prolog display-text helps, this is a textual database of
`h` clauses. The verified original has two records, not one long source-code
page. It is not THELP or a compiled binary database.

## Record grammar and encoding

The observed grammar is a sequence of `h("text")` records separated by
whitespace/CRLF. The string contains escaped `\n` characters that are display
newlines, not literal backslash-n text. There are no stored numeric context IDs,
topic names, byte offsets or hyperlink records.

Synthetic example:

```prolog
h("First page\nSecond line")
h("Another page\n")
```

Only `\\n` escapes occur in the inspected original. General Prolog escapes,
optional clause punctuation and other predicates are not established by this
sample. Its ordinary text is ASCII; no character-set tag is stored.

## Record boundaries

Opening `h("` starts a record; closing `")` ends it. Whitespace between
records is not display text. Decode `\\n` inside the string as a display
line break, not a record separator. No count, topic index or executable
instruction stream is stored in this grammar.
