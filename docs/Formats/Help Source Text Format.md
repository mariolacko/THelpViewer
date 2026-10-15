# Help Source Text Format (HLX/TXT)

> Created: 2026-03-29 · Last updated: 2026-10-11

Text format used as input for help file compilers and as output from
decompilers. Based on the original Borland TVHC source format, extended
for Borland THELP and Software602 decompilation, and further extended
with a small set of round-trip directives needed for byte-identical
THELP rebuilds.

---

## 1. Overview

A help source file is a plain-text file with special directives (lines
starting with `;` or `.`) and inline cross-reference markup (`{text:target}`).

Two main use cases:

| Use case | Flow |
| --- | --- |
| Compilation | Source directives → binary HELP records |
| Decompilation | Binary HELP records → a textual representation |

File extensions are conventional: `.txt` for source, `.hlx` for decompiled
output, `.hlp` / `.tph` for compiled binary.

---

## 2. File Structure

```
;CBEGIN
; comment block (metadata, rebuild hints)
;CEND

; header directives (;STAMP, ;VERSION, etc.)

; topic 1
; topic 2
; ...

;COMMENT thats all, folks
```

---

## 3. Directives

All directives start with `;` or `.` at the beginning of a line.

### 3.1 Comment Block

```
;CBEGIN
; any text (typically tool name, version, rebuild hints)
;CEND
```

Ignored by compilers. Used to store metadata about the decompilation.

### 3.2 Header Directives

| Directive        | Example                          | Description                                  |
|------------------|----------------------------------|----------------------------------------------|
| `;STAMP`         | `;STAMP TURBO PASCAL HELP FILE.` | File stamp string                            |
| `;SIGNATURE`     | `;SIGNATURE $*$* &&&&$*$`        | THELP signature                              |
| `;VERSION`       | `;VERSION 1`                     | Text version number                          |
| `;HEIGHT`        | `;HEIGHT 15`                     | Screen height in rows                        |
| `;WIDTH`         | `;WIDTH 48`                      | Screen width in columns                      |
| `;LMARGIN`       | `;LMARGIN 2`                     | Left margin                                  |
| `;DESCRIPTION`   | `;DESCRIPTION Help text`         | Help file description / `RT_IndexTags[$FFFF]`|
| `;FORMAT`        | `;FORMAT Software602 (...)`      | Format identifier (Python)                   |
| `;CONTEXTCOUNT`  | `;CONTEXTCOUNT 1334`             | Exact THELP context table size               |
| `;UNUSEDCTX`     | `;UNUSEDCTX 42 FFFFFE`           | Exact special context-table sentinel         |
| `;INDEXORDER`    | `;INDEXORDER 424 Runtime errors` | Preserve raw THELP index entry order         |
| `;TAGORDER`      | `;TAGORDER 17 Errors`            | Preserve raw THELP tag record order          |
| `;COMMENT`       | `;COMMENT FormatVersion 52`      | Informational comment                        |

Not all directives are present in every file. FBHF files have mainly
`.topic` and comment lines. Software602 files have `;STAMP` and `;FORMAT`.
THELP round-trip files may additionally contain `;CONTEXTCOUNT`,
`;UNUSEDCTX`, `;INDEXORDER`, `;TAGORDER`, `;COMMENT ALIASCTX` and
`;TEXTCOMPLETE`.

### 3.3 Topic Directive

```
.topic TopicName=ContextNumber[, AliasName[, AliasName2...]]
```

Defines a new topic with a symbolic name and numeric context ID.
Multiple aliases can share the same topic, with auto-incrementing numbers:

```
.topic FileOpen=3, OpenFile, FFileOpen
```

This assigns: `FileOpen=3`, `OpenFile=4`, `FFileOpen=5`.

In native TVHC, the `TOPIC` command is case-insensitive; predefined APP
names use their fixed contexts without consuming the automatic counter.
Symbol lookup folds ASCII letters only and rejects a second definition of
the same name. Distinct names may reuse a numeric context: the latest
indexed position owns that number, while other aliases of an earlier object
remain live. See the full [TVHC source grammar](TurboVision%20FBHF.md#24-tvhc-source-text-format)
for tokenization, numbering and byte limits.

### 3.4 Screen Delimiters

```
;SCREEN 100
  ... screen content ...
;ENDSCREEN
```

`;SCREEN N` marks the start of a topic (N = context number).
`;ENDSCREEN` marks the end. Used by the THELP and S602 decompilers
(both Python and Pascal).

FBHF topics use `.topic` instead of `;SCREEN`/`;ENDSCREEN`.

### 3.4.1 Page and Auxiliary THELP Directives

```
;PAGE 471
;INDEX Runtime errors
;SCREENTAG Errors
;HELP_CONTENTS
;LINK UP 12 DOWN 13
;COMMENT ALIASCTX 658
;TEXTCOMPLETE
```

Meaning:

| Directive               | Meaning |
|-------------------------|---------|
| `;PAGE N`               | THELP continuation page within a multi-page topic |
| `;INDEX text`           | Index entry attached to current screen |
| `;SCREENTAG tag`        | Tag emitted before the following `;INDEX` |
| `;HELP_CONTENTS`        | Marks the source Help Contents / table-of-contents topic |
| `;LINK UP a DOWN b`     | Explicit old-format page links (format < 5) |
| `;COMMENT ALIASCTX n`   | Additional context number pointing to the same text record |
| `;TEXTCOMPLETE`         | Exact THELP v5+ text-record ending hint for byte-identical rebuild |

` ;COMMENT ALIASCTX` is deliberately stored in comment namespace so the
file does not invent a new pseudo-directive in the original HL.EXE syntax.

` ;TEXTCOMPLETE` belongs to the extended round-trip dialect; it is not
part of Borland's documented source syntax.

### 3.5 Keyword / Cross-Reference Directives (THELP only)

```
;KEYWORD4 146 AT (3,22-43) NAV (1,2,0,0)
;KEYWORD 432
```

THELP keyword records contain either explicit screen coordinates (older
variants) or ordered target WORDs paired with inline delimiters (newer
variants). The source directives represent those binary fields:

| Field       | Meaning                                          |
|-------------|--------------------------------------------------|
| Context ID  | Target topic number (e.g. `146`)                 |
| Row, Col    | Position on screen where the link appears        |
| Length      | Length of the highlighted text (implicit from range) |

The number after `;KEYWORD` is the format-specific variant:
- `;KEYWORD` — simple keyword (format ≥ 5), just a context ID
- `;KEYWORD4` — positional keyword (format < 5), with `AT (row,col-col)`
  and optional `NAV (left,right,up,down)` button indices for exact rebuild

**Binary distinction:** old THELP keyword records store clickable coordinates.
THELP format 5 and later also pair ordered target WORDs with `02h` inline
text delimiters. The `;KEYWORD` source directive represents those target WORDs,
not an assertion that every binary variant lacks delimiters.

### 3.6 Inline Cross-References (FBHF and S602)

```
{highlighted text:TargetTopic}
```

The text in braces is displayed highlighted (clickable). The part after
`:` identifies the target:

| Format   | Target syntax     | Example                            |
|----------|-------------------|------------------------------------|
| FBHF     | Topic name        | `{File Open:FileOpen_F3}`          |
| S602     | Decimal context ID| `{Nastavení konfigurace:3328}`     |

For FBHF, the compiler resolves the topic name to a context number.
For S602, the context ID is an opaque 16-bit M602 application identifier
(not a sequential index).

If text and target are the same, the `:alias` part can be omitted in FBHF:
```
{Calculator}     → same as {Calculator:Calculator}
```

Spaces in cross-reference text are stored as `$FF` bytes in the FBHF
binary format. The decompiler converts them back to spaces.

TVHC escapes a literal opening brace with `{{`; its mutable scan cursor
governs longer brace runs. An unterminated reference is a compiler error.
Unresolved forward references retain the WORD `FFFFh` and cause a warning;
their target must not be inferred from the displayed label. Target bytes,
including whitespace, are preserved before ASCII-only case-insensitive
symbol lookup.

---

## 4. Topic Content

### 4.1 Title Line

The first non-blank line after `.topic` or `;SCREEN` is the topic title.
Conventions vary by format:

| Format | Title style                         | Example                     |
|--------|-------------------------------------|-----------------------------|
| FBHF   | ` Title ◄` + underline `  ═══`     | ` File viewer ◄`            |
| THELP   | Raw text (first line of screen)    | `                Index`     |
| S602   | ` Title` (Python) or `Title` + `▀▀▀` (Pascal) | ` Základní obrazovka` |

### 4.2 Paragraph Rules (FBHF compiler)

The TVHC compiler groups consecutive lines into paragraphs:

- **Wrapping lines** — no leading space → joined and word-wrapped
- **Non-wrapping lines** — start with a space → output verbatim
- **Empty lines** — produce CR (`$0D`) bytes prepended to the next paragraph
- Trailing empty lines at end of topic → discarded

Lines of the same wrap type are merged into a single paragraph.
A change in wrap type starts a new paragraph.

The DOS TVHC compiler reads CRLF physical lines of at most 253 text bytes
and uses a 4096-byte paragraph buffer, counting prepended CRs and appended
line separators. A standalone `1Ah` line terminates source; `1Ah` followed
by more text is a character cell. These native TVHC limits do not define
the separate extended `;SCREEN` dialect's source-line or buffer limits.

### 4.3 Special Characters

| Character | Meaning                                           |
|-----------|---------------------------------------------------|
| `█`       | Button highlight (S602) — purely decorative       |
| `◄`       | Title end marker (FBHF)                           |
| `▀`       | Title line (S602 decompiler)                      |
| `▀`       | Title underline (S602 Pascal decompiler)          |
| `═`, `─`  | Separator/underline characters                    |
| Box chars | `┌┐└┘│─` etc. — decorative frames (CP437)        |

### 4.4 Character Encoding

Source files can be in:
- **CP437** — standard DOS (Borland THELP, FBHF)
- **Kamenický (KEYBCS2)** — Czech/Slovak DOS (Software602)
- **UTF-8** — when decompiled with `--from ENC --to utf-8`

The source dialect has no universal byte-order mark or encoding field.
The parser needs an explicit character-set agreement with its producer.

---

## 5. THELP Round-Trip Notes

The extended source dialect can retain binary fields not represented in
minimal Borland source syntax:

| Data preserved             | Directive / encoding |
|---------------------------|----------------------|
| Exact context table size  | `;CONTEXTCOUNT`      |
| Non-default unused slots  | `;UNUSEDCTX`         |
| Exact index order         | `;INDEXORDER`        |
| Exact tag order           | `;TAGORDER`          |
| Alias contexts            | `;COMMENT ALIASCTX`  |
| Exact v5+ text ending     | `;TEXTCOMPLETE`      |
| Old keyword nav buttons   | `;KEYWORD4 ... NAV`  |

Without these details a semantic rebuild is possible, but a byte-for-byte
rebuild is not guaranteed.

## 6. Dialect boundaries

The `.topic`/brace-cross-reference dialect is based on TVHC. Semicolon
screen/keyword directives represent THELP or Software602 records. Extended
round-trip directives preserve original binary fields but are not universally
accepted by the historical compilers. Do not confuse these text files with
[compiled binary HLX](Borland%20HLX%20Binary.md).
