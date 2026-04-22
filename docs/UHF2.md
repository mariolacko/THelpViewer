# Universal Help Format 2.0 (UHF)

> Created: 2026-04-08

UHF is the internal exchange format used by THelpViewer readers and writers.
Every source format (THELP, Norton Guide, QuickHelp, BW03, FBHF, M602, HLX,
Scorpion DAT) is read
into a UHF document; every output target (HTML bundle, plain text, future
formats) is written from a UHF document.

Bundle JSON files without `"uhf_version"` are old pre-rendered bundles and
are no longer accepted by the current viewer.

For web transport, the UHF 2.0 JSON payload is typically gzip-compressed and
stored as `.json.gz`. Compression is a transport detail; the logical format
described here is still plain JSON.

---

## 1. Root Object

```json
{
  "uhf_version":  "2.0",
  "metadata":     { ... },
  "converter":    { ... },
  "contents":     [ ... ],
  "index":        [ ... ],
  "topics":       { ... }
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `uhf_version` | string | ✅ | Always `"2.0"` for this spec. |
| `metadata` | object | ✅ | File-level metadata. See §2. |
| `converter` | object | ✅ | Tool that produced this file. See §3. |
| `contents` | array | ✅ | Table of contents tree (may be empty `[]`). See §4. |
| `index` | array | ✅ | Alphabetical index (may be empty `[]`). See §5. |
| `topics` | object | ✅ | Map of topic-id → Topic Object. See §6. |

---

## 2. Metadata Object

```json
{
  "name":          "QuickBasic 7.1 Advanced Reference",
  "author":        "Microsoft Corporation",
  "copyright":     "Copyright © 1990 Microsoft",
  "display":       { "cols": 76, "rows": 24 },
  "frozen_rows":   0,
  "encoding":      "utf-8",
  "source": {
    "filename":   "BAS7ADVR.HLP",
    "format":     "quickhelp",
    "encoding":   "cp437",
    "date":       "1990-01-01"
  }
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `name` | string | ✅ | Human-readable name of the help file. |
| `author` | string | ❌ | Author or organization. Omit if unknown. |
| `copyright` | string | ❌ | Copyright notice. Omit if unknown. |
| `display` | object | ❌ | Default display size. Omit if the source format does not define it. |
| `display.cols` | integer | ❌ | Default display width in character columns. |
| `display.rows` | integer | ❌ | Default display height in character rows. |
| `frozen_rows` | integer | ❌ | Number of lines from the top of each topic that stay fixed during scrolling (file-level default). Default `0`. |
| `encoding` | string | ✅ | Encoding of the text in this UHF file. Always `"utf-8"` for new conversions. |
| `source` | object | ✅ | Information about the original source file. |
| `source.filename` | string | ✅ | Original file name without path (e.g. `"BAS7ADVR.HLP"`). |
| `source.format` | string | ✅ | Source format: `"thelp"`, `"norton-guide"`, `"quickhelp"`, `"bw03"`, `"fbhf"`, `"m602"`, `"hlx"`, `"scorpion-dat"`. |
| `source.encoding` | string | ✅ | Encoding of the original source file (e.g. `"cp437"`, `"cp852"`, `"latin-1"`). |
| `source.date` | string | ❌ | File creation or modification date in ISO 8601 (`"YYYY-MM-DD"`). Omit if unknown. |

---

## 3. Converter Object

```json
{
  "name":    "THelpViewer",
  "version": "2.0.0",
  "date":    "2026-04-08T14:30:00Z"
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `name` | string | ✅ | Name of the software that produced this UHF file. |
| `version` | string | ❌ | Version of the converter. |
| `date` | string | ✅ | ISO 8601 datetime when the conversion was performed. |

---

## 4. Contents (Table of Contents)

A tree of TOC nodes. Each node has an optional topic reference and an optional
list of child nodes. May be empty (`[]`) if the source format provides no
hierarchical structure.

When present, `contents[]` is the canonical document-level table of contents.
A viewer may present it as a dedicated Contents window, as a top menu, or both.

```json
[
  {
    "label":    "Language Reference",
    "topic_id": 1,
    "children": [
      { "label": "Statements", "topic_id": 5, "children": [] },
      { "label": "Functions",  "topic_id": 6, "children": [] }
    ]
  },
  {
    "label":    "Error Messages",
    "topic_id": 100,
    "children": []
  }
]
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `label` | string | ✅ | Display label for this TOC entry. |
| `hotkey` | string | ❌ | Preferred menu accelerator character when the source format provides one. |
| `topic_id` | integer | ❌ | Topic id (see §6). |
| `source_file` | string | ❌ | Open a topic from another bundle/source file. |
| `alias` | string | ❌ | Open a topic by string alias, optionally together with `source_file`. |
| `line` | integer | ❌ | Optional 1-based target line inside the destination topic. |
| `children` | array | ✅ | Child TOC nodes. Empty array `[]` for leaf nodes. |

Each TOC node may target the current bundle via `topic_id`, or another bundle
via any combination of `source_file`, `alias`, `topic_id`, and `line`. Omit
all target fields for pure section headings.

---

## 5. Index

A two-level alphabetical list. The outer array groups entries by initial letter.
The inner `entries` array lists individual topics.

```json
[
  {
    "group": "A",
    "entries": [
      { "label": "ABSOLUTE function", "topic_id": 23 },
      { "label": "ARRAY statement",   "topic_id": 41 }
    ]
  },
  {
    "group": "B",
    "entries": [
      { "label": "BEGIN block",       "topic_id": 55 }
    ]
  }
]
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `group` | string | ✅ | Letter or label: `"A"`, `"#"`, `"0–9"`. |
| `entries[].label` | string | ✅ | Human-readable index label. |
| `entries[].topic_id` | integer | ✅ | Topic id (see §6). |

---

## 6. Topics

An **object** whose keys are topic ids and whose values are **Topic Objects**
(see §7). Topic ids are integers, but JSON requires object keys to be strings —
so the key is `str(id)`. The integer value is stored inside the topic as `id`.

```json
{
  "0":   { "id": 0,   ... },
  "1":   { "id": 1,   ... },
  "378": { "id": 378, ... }
}
```

When reading the file, consumers may normalize the object key `"0"` to the
integer topic id `0`, but the canonical numeric value is always `topic.id`.

---

## 7. Topic Object

```json
{
  "id":          42,
  "title":       "CHDRIVE Statement Details",
  "aliases":     { "ids": [10, 11], "strings": ["chdrive", "chdrive.details"] },
  "is_main":     false,
  "nav": {
    "Up":   { "topic_id": 1 },
    "Next": { "topic_id": 43, "alias": "chdir.details" },
    "Back": { "action": "back" }
  },
  "frozen_rows": 2,
  "content":     [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `id` | integer | ✅ | Topic id. Same as the key in `topics` (as integer). |
| `title` | string | ❌ | Explicit topic title if the source provides one. Omit if absent. |
| `aliases` | object | ❌ | Optional alternative identifiers that also resolve to this topic. |
| `aliases.ids` | array\<integer\> | ❌ | Alternative numeric topic ids. |
| `aliases.strings` | array\<string\> | ❌ | Alternative symbolic aliases such as QuickHelp context strings. |
| `is_main` | boolean | ❌ | `true` for the main / home topic. Default `false`. |
| `nav` | object | ❌ | Map of display label → Nav Item. Keys are the exact labels to show in the viewer menu. |
| `nav.<label>.file` | string | ❌ | Original source filename of another bundle to open first (for example `BAS7EX.HLP`). |
| `nav.<label>.topic_id` | integer | ❌ | Navigate to this topic id. |
| `nav.<label>.alias` | string | ❌ | Navigate to this topic alias inside the current or target bundle. |
| `nav.<label>.line` | integer | ❌ | 1-based visible display line inside the target topic. |
| `nav.<label>.action` | string | ❌ | Built-in action name such as `"back"`, `"contents"`, or `"index"`. |
| `frozen_rows` | integer | ❌ | Per-topic freeze override. Overrides `metadata.frozen_rows`. Default `0`. |
| `content` | array\<string\> | ✅ | Ordered list of display lines. See §8. |

Each nav item should contain either `action` or a link target composed from any
combination of `file`, `topic_id`, `alias`, and `line`.

---

## 8. Content — Array of Lines

`content` is a **flat array of strings**. Each string is exactly one display
line, mirroring the line-oriented nature of all original formats (fixed-width
terminal display — no text wrapping).

```json
"content": [
  "  [nav:contents]Contents[/nav]  [nav:index]Index[/nav]",
  "",
  "[b]CHDRIVE Statement Details[/b]",
  "",
  "Syntax",
  "[code:basic]",
  "  ChDrive drive$",
  "[/code]",
  "",
  "See also: [link:topic=2]ChDir[/link]  [link:topic=3]CurDir$[/link]"
]
```

### Line rendering rules

| Line content | Rendered as |
|---|---|
| `""` (empty string) | Blank display line |
| `"[rule]"` (exactly) | Horizontal separator (box-drawing or dash line) |
| `"[code]"` or `"[code:lang]"` (exactly) | Start of a code block — all following lines until `"[/code]"` are code lines |
| `"[/code]"` (exactly) | End of the current code block |
| Anything else | Text line — parsed for inline markup (see §9) |

### Code blocks

Lines between `"[code]"` / `"[code:lang]"` and `"[/code]"` are **code lines**.
Code lines are plain text — inline markup tags inside them are **not parsed**
and are displayed as literal characters. The renderer applies syntax
highlighting based on `lang` (see §9.2).

```json
"content": [
  "Example:",
  "[code:pascal]",
  "  x := Abs(y) + 1;   { comment }",
  "  WriteLn(x);",
  "[/code]",
  "After the code block."
]
```

Supported `lang` values: `"pascal"`, `"c"`, `"basic"`, `"asm"`, `"python"`.
Omit `lang` (use just `"[code]"`) for generic / unknown language.

---

## 9. Inline Markup

Text content inside `"text"` lines uses a **bracket-tag** markup language.
Tags are `[tag]...[/tag]` pairs. Tags may be nested. The text outside any tag
is treated as plain Unicode.

### 9.1 Style tags

| Tag | Description |
|---|---|
| `[b]...[/b]` | **Bold** |
| `[i]...[/i]` | *Italic* |
| `[u]...[/u]` | Underline |
| `[r]...[/r]` | Reverse video (swap foreground and background) |

### 9.2 Color tags

`fg` = foreground, `bg` = background. Color values are CGA palette indices
0–15 (see §9.4). Either attribute may be omitted.

| Tag | Description |
|---|---|
| `[fg:N]...[/fg]` | Foreground color index N (0–15) |
| `[bg:N]...[/bg]` | Background color index N (0–15) |
| `[color:N]...[/color]` | Foreground color N, background unchanged |
| `[color:N:M]...[/color]` | Foreground N, background M |

Examples:
```
[color:4]red text[/color]
[color:14:1]yellow on blue[/color]
[fg:12]light red[/fg]
```

### 9.3 Link tags

| Tag | Description |
|---|---|
| `[link:file=...,topic=...,alias=...,line=...]...[/link]` | Canonical combinable link target. Any subset of `file`, `topic`, `alias`, `line` may be present. |
| `[nav:back]...[/nav]` | Built-in Back action |
| `[nav:contents]...[/nav]` | Built-in Contents action |
| `[nav:index]...[/nav]` | Built-in Index action |

`line` is a 1-based visible display line inside the rendered topic. It counts
only lines that the viewer actually shows; UHF control lines such as
`"[code]"` / `"[/code]"` are not counted.

`alias` is a symbolic topic identifier. It is primarily used for formats such
as QuickHelp where links are stored as `file!context` names instead of direct
numeric topic ids.

When both `topic` and `alias` are present, `topic` is the canonical direct
target and `alias` acts as an additional stable resolver or preservation of
the original source context string.

Examples:
```
[link:topic=42]CHDRIVE Statement[/link]
[link:file=BAS7EX.HLP,topic=1]Example[/link]
[link:file=HELPMAKE.HLP,alias=helpmake.contents]Up[/link]
[link:topic=42,alias=chdrive.details,line=12]Jump to declaration[/link]
[link:topic=42,line=12]Jump to declaration[/link]
[link:file=BAS7QCK.HLP,line=3]Open other file and jump to line 3 of its main topic[/link]
[nav:back]Back[/nav]
[nav:contents]Contents[/nav]
```

### 9.4 Literal bracket

To include a literal `[` in text, write `[[`.

### 9.5 Nesting

Tags may be nested freely:

```
[b][link:topic=42]Bold link[/link][/b]
[color:4][u]red underline[/u][/color]
```

### 9.6 CGA Color Index

| 0 Black | 1 Blue | 2 Green | 3 Cyan |
|---|---|---|---|
| **4 Red** | **5 Magenta** | **6 Brown** | **7 Light Gray** |
| **8 Dark Gray** | **9 Light Blue** | **10 Light Green** | **11 Light Cyan** |
| **12 Light Red** | **13 Light Magenta** | **14 Yellow** | **15 White** |

---

## 10. Source Format Mapping

How each source format maps onto UHF fields:

| UHF field | THELP | Norton Guide | QuickHelp | FBHF | M602 |
|---|---|---|---|---|---|
| `metadata.name` | stamp string | NG title field | `DatabaseName` or first meaningful topic heading | — | header string |
| `metadata.author` | stamp line 0 | credit line 0 | — | — | — |
| `metadata.copyright` | stamp line 1 | credit line 1 | — | — | — |
| `metadata.display` | `width`/`height` header fields | omitted (76 implied) | `DisplayWidth` / omitted | omitted (50×18 fixed) | omitted |
| `metadata.frozen_rows` | — | — | file-level default 0 | — | — |
| `source.format` | `"thelp"` | `"norton-guide"` | `"quickhelp"` | `"fbhf"` | `"m602"` |
| `source.encoding` | `"cp437"` | `"cp437"` | `"cp437"` | `"latin-1"` | `"latin-1"` / `"cp852"` |
| `topic.id` | context id → hex | file offset → 8-digit hex | sequential 0-N → hex | sequential → hex | sequential → hex |
| `topic.title` | first visible line | parent `MENU`/`SHORT` label when available, otherwise first visible line | `:n` command | `.topic` name | heading up to `0xDC` |
| `topic.frozen_rows` | — | — | `:l N` command | — | — |
| `topic.nav` | synthesized labels from `up/down/prev/next` plus explicit top-menu links | synthesized labels from `Parent` / `Previous` / `Next` and from `MENU`/`SHORT` pointer labels | exact top-menu labels and `!B` / `!HV` / `!VX` actions | — | — |
| `[b]` | — | `^B` toggle | style bit 0 | — | — |
| `[i]` | — | — | style bit 1 | — | — |
| `[u]` | — | `^U` toggle | style bit 2 | — | — |
| `[r]` | — | `^R` toggle | — | — | — |
| `[color:N:M]` | — | `^Ann` (CP437 attr) | — | — | — |
| `[link:topic=.../alias=...]` | positional kw / 0x02 inline | SHORT offset / see-also | attr-block link / `file!context` | 0x02 inline | 0x02 inline |
| `[nav:*]` | — | — | `!B` / `!HV` / `!VX` / `-9996` / `-9997` | — | — |
| `"code"` block | `0x03`/`0x05`/`0x10` toggle | — | — | — | — |
| `"code"` heuristic | TC 2.x `"Example:"` regex | — | — | — | — |

---

## 11. Full Example

```json
{
  "uhf_version": "2.0",
  "metadata": {
    "name":        "QuickBasic 7.1 Advanced Reference",
    "author":      "Microsoft Corporation",
    "copyright":   "Copyright © 1990 Microsoft",
    "display":     { "cols": 76, "rows": 24 },
    "frozen_rows": 0,
    "encoding":    "utf-8",
    "source": {
      "filename": "BAS7ADVR.HLP",
      "format":   "quickhelp",
      "encoding": "cp437",
      "date":     "1990-01-01"
    }
  },
  "converter": {
    "name":    "THelpViewer",
    "version": "2.0.0",
    "date":    "2026-04-08T14:30:00Z"
  },
  "contents": [
    {
      "label": "QuickBasic Reference",
      "topic_id": 0,
      "children": [
        { "label": "CHDRIVE Statement", "topic_id": 1, "children": [] }
      ]
    }
  ],
  "index": [
    {
      "group": "C",
      "entries": [
        { "label": "CHDRIVE Statement Details", "topic_id": 1 }
      ]
    }
  ],
  "topics": {
    "0": {
      "id":      0,
      "title":   "QuickBasic 7.1 Reference",
      "is_main": true,
      "nav": {
        "CHDRIVE Statement": { "topic_id": 1 },
        "Index": { "action": "index" }
      },
      "content": [
        "QuickBasic 7.1 Reference",
        "",
        "[nav:contents]Contents[/nav]  [nav:index]Index[/nav]"
      ]
    },
    "1": {
      "id":          1,
      "title":       "CHDRIVE Statement Details",
      "frozen_rows": 2,
      "nav": {
        "Contents": { "action": "contents" },
        "Index": { "action": "index" },
        "Back": { "action": "back" },
        "Up": { "topic_id": 0 }
      },
      "content": [
        "[b]CHDRIVE Statement Details[/b]",
        "",
        "Syntax",
        "[code:basic]",
        "  ChDrive drive$",
        "[/code]",
        "",
        "Description",
        "  Changes the current drive to [b]drive$[/b].",
        "",
        "See also: [link:topic=2]ChDir[/link]  [link:topic=3]CurDir$[/link]",
        "",
        "[nav:contents]Contents[/nav]  [nav:index]Index[/nav]  [nav:back]Back[/nav]"
      ]
    }
  }
}
```

**Reading the example:**

- Each string in `content` is exactly one display line.
- `""` is a blank line — same as pressing Enter in the original viewer.
- `"[b]CHDRIVE Statement Details[/b]"` — the title rendered bold.
- `"[code:basic]"` and `"[/code]"` are sentinel lines that toggle code mode — they are not displayed themselves.
- Lines inside the code block (`"  ChDrive drive$"`) are plain text; inline tags would not be parsed there.
- `"See also: [link:topic=2]ChDir[/link]  [link:topic=3]CurDir$[/link]"` — `ChDir` and `CurDir$` are clickable links to topics `2` and `3`.
- `"[nav:contents]Contents[/nav]  [nav:index]Index[/nav]  [nav:back]Back[/nav]"` — three navigation actions on one line, separated by spaces.

---

## 12. Versioning

| `uhf_version` | Status | Notes |
|---|---|---|
| absent | Legacy (v1) | Original bundle JSON. Topics are pre-rendered HTML. No block model. |
| `"2.0"` | Current | This spec. Structured topic lines with inline markup. |

Writers generating UHF 2.0 MUST include `"uhf_version": "2.0"`.  
Readers encountering an unknown version SHOULD reject the file with a clear error.

*Part of the [THelpViewer](https://github.com/) project.*
