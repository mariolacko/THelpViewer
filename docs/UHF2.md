# Universal Help Format 2.0 (UHF)

> Created: 2026-04-08

UHF is the internal exchange format used by THelpViewer readers and writers.
Every source format (THELP, Norton Guide, QuickHelp, BW03, FBHF, M602, HLX,
Scorpion DAT) is read
into a UHF document; every output target (HTML bundle, plain text, future
formats) is written from a UHF document.

Bundle JSON files without `"uhf_version": "2.0"` are not UHF2 and are rejected
by the current viewer.

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
| `default_palette` | string | ❌ | Default palette used by inline color tags. Default `"cga"` when omitted. See §3. |
| `palettes` | object | ❌ | Document palette definitions and overrides. See §3. |
| `converter` | object | ✅ | Tool that produced this file. See §4. |
| `contents` | array | ✅ | Table of contents tree (may be empty `[]`). See §5. |
| `index` | array | ✅ | Alphabetical index (may be empty `[]`). See §6. |
| `topics` | object | ✅ | Map of topic-id → Topic Object. See §7. |

---

## 2. Metadata Object

```json
{
  "name":          "QuickBasic 7.1 Advanced Reference",
  "author":        "Microsoft Corporation",
  "copyright":     "Copyright © 1990 Microsoft",
  "display":       { "cols": 76, "rows": 24 },
  "help_contents_topic_id": 3,
  "frozen_rows":   0,
  "language":      "en",
  "ui": {
    "window": "cga:1",
    "text": "cga:7",
    "link": "cga:14"
  },
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
| `help_contents_topic_id` | integer | ❌ | Source Help Contents / table-of-contents topic for the whole help file. This is distinct from the alphabetical help index. A viewer may expose this as a Help Contents button. |
| `frozen_rows` | integer | ❌ | Number of lines from the top of each topic that stay fixed during scrolling (file-level default). Default `0`. |
| `language` | string | ❌ | BCP 47 language tag for the help content, e.g. `"en"`, `"cs"`, `"de"`. Omit if unknown. |
| `ui` | object | ❌ | Semantic viewer colors for this help file. Values are UHF2 color references resolved through `default_palette` / `palettes`. |
| `ui.window` | string | ❌ | Help window background. |
| `ui.text` | string | ❌ | Default help text color. |
| `ui.link` | string | ❌ | Link color. |
| `ui.title` | string | ❌ | Active title/frame background. |
| `ui.title_text` | string | ❌ | Active title text. |
| `ui.frame` | string | ❌ | Frame line color. |
| `ui.icon` | string | ❌ | Frame icon color. |
| `ui.page_area` | string | ❌ | Secondary page/code background. |
| `ui.hover_bg` | string | ❌ | Hover/focus background. |
| `ui.hover_fg` | string | ❌ | Hover/focus foreground. |
| `ui.arrow_bg` | string | ❌ | Scrollbar arrow cell background. |
| `ui.arrow_fg` | string | ❌ | Scrollbar arrow glyph color. |
| `ui.scroll_glyph` | string | ❌ | Scrollbar track glyph color. |
| `ui.thumb_bg` | string | ❌ | Scrollbar thumb background. May be `"transparent"`. |
| `ui.thumb_fg` | string | ❌ | Scrollbar thumb glyph color. |
| `ui.code_bg` | string | ❌ | Code block background. |
| `ui.code_text` | string | ❌ | Code block text. |
| `encoding` | string | ✅ | Encoding of the text in this UHF file. Always `"utf-8"` for new conversions. |
| `source` | object | ✅ | Information about the original source file. |
| `source.filename` | string | ✅ | Original file name without path (e.g. `"BAS7ADVR.HLP"`). |
| `source.format` | string | ✅ | Source format: `"thelp"`, `"tdh"`, `"tfh"`, `"norton-guide"`, `"quickhelp"`, `"bw03"`, `"fbhf"`, `"m602"`, `"text602"`, `"hlx"`, `"scorpion-dat"`. |
| `source.encoding` | string | ✅ | Encoding of the original source file (e.g. `"cp437"`, `"cp852"`, `"latin-1"`). |
| `source.date` | string | ❌ | File creation or modification date in ISO 8601 (`"YYYY-MM-DD"`). Omit if unknown. |

---

## 3. Palettes

UHF2 color tags resolve color values through a document palette. The viewer has
a built-in `cga` palette, but a UHF2 file may redefine any built-in palette or
add new palettes. Document-defined values override built-in values with the same
palette name.

Converters should omit `default_palette` and `palettes` when they only need the
built-in CGA defaults. Store only source-specific palette overrides or custom
palettes in the UHF file.

```json
{
  "default_palette": "cga",
  "palettes": {
    "cga": {
      "type": "indexed",
      "colors": {
        "0": "#000000",
        "1": "#0000aa",
        "4": "#aa0000",
        "14": "#ffff55",
        "15": "#ffffff"
      },
      "aliases": {
        "black": 0,
        "blue": 1,
        "red": 4,
        "yellow": 14,
        "white": 15,
        "warning": "yellow"
      }
    },
    "ng": {
      "type": "indexed",
      "colors": {
        "0": "#000000",
        "1": "#00aaaa"
      },
      "aliases": {
        "link": 1
      }
    }
  }
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `default_palette` | string | ❌ | Palette used when a color reference does not specify a palette. Default `"cga"`. |
| `palettes` | object | ❌ | Map of palette name → palette definition. |
| `palettes.*.type` | string | ❌ | Palette kind. Currently `"indexed"` is defined. |
| `palettes.*.colors` | object or array | ❌ | Palette entries. Object keys are string indices or names; array positions are numeric indices. Values are color references. |
| `palettes.*.aliases` | object | ❌ | Human-readable aliases. Values may point to numeric indices, other aliases, `palette:value`, or direct RGB values. |

Color references accepted by UHF2:

| Form | Meaning |
|---|---|
| `4` | Index `4` in `default_palette`. |
| `red` | Alias or named color in `default_palette`. |
| `cga:4` | Index `4` in the `cga` palette. |
| `cga:red` | Alias `red` in the `cga` palette. |
| `#ff5555` | Direct RGB hex color. |
| `#f55` | Short RGB hex color. |
| `rgb(255,85,85)` | Direct RGB color. |
| `transparent` | Transparent CSS color, useful for scrollbar/thumb backgrounds. |

Aliases may chain, but consumers must reject cycles.

`metadata.ui` uses the same color-reference syntax. This lets a converter
keep source-family colors without hard-coding them in the viewer. For example,
Borland THELP may use a cyan window with black text, Microsoft QuickHelp may use
a blue window with gray text, and Norton Guides may use a black window with
cyan links.

### 3.1 Built-in CGA Palette

The built-in `cga` palette is available even when `palettes.cga` is omitted.
If `palettes.cga` is present, its `colors` and `aliases` override or extend the
built-in values.

| 0 Black | 1 Blue | 2 Green | 3 Cyan |
|---|---|---|---|
| **4 Red** | **5 Magenta** | **6 Brown** | **7 Light Gray** |
| **8 Dark Gray** | **9 Light Blue** | **10 Light Green** | **11 Light Cyan** |
| **12 Light Red** | **13 Light Magenta** | **14 Yellow** | **15 White** |

---

## 4. Converter Object

```json
{
  "name":    "THelpViewer",
  "version": "0.0.0",
  "date":    "2026-04-08T14:30:00Z"
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `name` | string | ✅ | Name of the software that produced this UHF file. |
| `version` | string | ❌ | Version of the converter. This is not the UHF format version; the UHF version is stored only in root `uhf_version`. |
| `date` | string | ✅ | ISO 8601 datetime when the conversion was performed. |

---

## 5. Contents (Table of Contents)

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
| `topic_id` | integer | ❌ | Topic id (see §7). |
| `file` | string | ❌ | Open a topic from another bundle/source file. |
| `alias` | string | ❌ | Open a topic by string alias, optionally together with `file`. |
| `line` | integer | ❌ | Optional 1-based target line inside the destination topic. |
| `children` | array | ✅ | Child TOC nodes. Empty array `[]` for leaf nodes. |

Each TOC node may target the current bundle via `topic_id`, or another bundle
via any combination of `file`, `alias`, `topic_id`, and `line`. Omit
all target fields for pure section headings.

---

## 6. Index

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
| `entries[].topic_id` | integer | ❌ | Topic id (see §7). |
| `entries[].file` | string | ❌ | Open a topic from another bundle/source file. |
| `entries[].alias` | string | ❌ | Open a topic by string alias. |
| `entries[].line` | integer | ❌ | Optional 1-based target line inside the destination topic. |

Each index entry must contain at least one target field: `topic_id`, `file`,
`alias`, or `line`.

---

## 7. Topics

An **object** whose keys are topic ids and whose values are **Topic Objects**
(see §8). Topic ids are integers, but JSON requires object keys to be strings —
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

## 8. Topic Object

```json
{
  "id":          42,
  "title":       "CHDRIVE Statement Details",
  "aliases":     { "ids": [10, 11], "strings": ["chdrive", "chdrive.details"] },
  "is_help_contents": false,
  "nav": {
    "Obsah": { "action": "contents" },
    "Rejstřík": { "action": "index" },
    "Zpět": { "action": "back" },
    "Další téma": { "topic_id": 43, "alias": "chdir.details" }
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
| `is_help_contents` | boolean | ❌ | `true` for the source Help Contents / table-of-contents topic. This is distinct from the alphabetical help index. Default `false`. |
| `nav` | object | ❌ | Map of display label → Nav Item. Keys are source-provided labels to show in the viewer menu. Labels such as `Up`, `Next`, or `Back` are not reserved; use them only when the source help file uses them. |
| `nav.<label>.file` | string | ❌ | Original source filename of another bundle to open first (for example `BAS7EX.HLP`). |
| `nav.<label>.topic_id` | integer | ❌ | Navigate to this topic id. |
| `nav.<label>.alias` | string | ❌ | Navigate to this topic alias inside the current or target bundle. |
| `nav.<label>.line` | integer | ❌ | 1-based visible display line inside the target topic. |
| `nav.<label>.action` | string | ❌ | Built-in action name such as `"back"`, `"contents"`, or `"index"`. |
| `frozen_rows` | integer | ❌ | Per-topic freeze override. Overrides `metadata.frozen_rows`. Default `0`. |
| `content` | array\<string\> | ✅ | Ordered list of display lines. See §9. |

Each nav item should contain either `action` or a link target composed from any
combination of `file`, `topic_id`, `alias`, and `line`.
The viewer must not synthesize localized labels from `action`; the object key is
the visible label.

---

## 9. Content — Array of Lines

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
| Anything else | Text line — parsed for inline markup (see §10) |

### Code blocks

Lines between `"[code]"` / `"[code:lang]"` and `"[/code]"` are **code lines**.
Code lines are plain text — inline markup tags inside them are **not parsed**
and are displayed as literal characters. The renderer applies syntax
highlighting based on `lang`.

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

## 10. Inline Markup

Text content inside `"text"` lines uses a **bracket-tag** markup language.
Tags are `[tag]...[/tag]` pairs. Tags may be nested. The text outside any tag
is treated as plain Unicode.

### 10.1 Style tags

| Tag | Description |
|---|---|
| `[b]...[/b]` | **Bold** |
| `[i]...[/i]` | *Italic* |
| `[u]...[/u]` | Underline |
| `[r]...[/r]` | Reverse video (swap foreground and background) |

### 10.2 Color tags

`fg` = foreground, `bg` = background. Color values are palette references
or direct RGB values (see §3). Numeric values and aliases resolve through
`default_palette`; `palette:value` resolves through the named palette.

| Tag | Description |
|---|---|
| `[fg:VALUE]...[/fg]` | Foreground color. |
| `[fg=VALUE]...[/fg]` | Foreground color. |
| `[bg:VALUE]...[/bg]` | Background color. |
| `[bg=VALUE]...[/bg]` | Background color. |
| `[color:FG]...[/color]` | Foreground color, background unchanged. |
| `[color:FG:BG]...[/color]` | Legacy shorthand: foreground and background. Intended for simple values such as `14:1`. |
| `[color=FG]...[/color]` | Foreground color, including palette-qualified values such as `cga:red`. |

Examples:
```
[color:red]red text[/color]
[color:14:1]yellow on blue[/color]
[color=#ff5555]RGB red text[/color]
[fg=cga:12]light red from CGA[/fg]
[fg=yellow][bg=blue]yellow on blue[/bg][/fg]
[fg=ng:link]Norton Guides link color[/fg]
```

`[color:FG:BG]` is kept for compact DOS attribute output. Prefer
nesting `[fg]` and `[bg]` when either color value contains `:`, for example
`[fg=cga:yellow][bg=cga:blue]...[/bg][/fg]`.

### 10.3 Link tags

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
[link:file=BAS7QCK.HLP,line=3]Open other file and jump to line 3 of its default topic[/link]
[nav:back]Back[/nav]
[nav:contents]Contents[/nav]
```

### 10.4 Literal bracket

To include a literal `[` in text, write `[[`.

### 10.5 Nesting

Tags may be nested freely:

```
[b][link:topic=42]Bold link[/link][/b]
[color=red][u]red underline[/u][/color]
```

---

## 11. Source Format Mapping

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

## 12. Full Example

```json
{
  "uhf_version": "2.0",
  "metadata": {
    "name":        "QuickBasic 7.1 Advanced Reference",
    "author":      "Microsoft Corporation",
    "copyright":   "Copyright © 1990 Microsoft",
    "display":     { "cols": 76, "rows": 24 },
    "language":    "en",
    "ui": {
      "window": "cga:1",
      "text": "cga:7",
      "link": "cga:14",
      "title": "cga:1",
      "title_text": "cga:15"
    },
    "frozen_rows": 0,
    "encoding":    "utf-8",
    "source": {
      "filename": "BAS7ADVR.HLP",
      "format":   "quickhelp",
      "encoding": "cp437",
      "date":     "1990-01-01"
    }
  },
  "default_palette": "cga",
  "palettes": {
    "cga": {
      "type": "indexed",
      "colors": {
        "14": "#ffff55"
      },
      "aliases": {
        "heading": 14
      }
    }
  },
  "converter": {
    "name":    "THelpViewer",
    "version": "0.0.0",
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
      "is_help_contents": true,
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
        "[fg:heading][b]CHDRIVE Statement Details[/b][/fg]",
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
- `"[fg:heading][b]CHDRIVE Statement Details[/b][/fg]"` — the title rendered bold and colored through the document palette.
- `"[code:basic]"` and `"[/code]"` are sentinel lines that toggle code mode — they are not displayed themselves.
- Lines inside the code block (`"  ChDrive drive$"`) are plain text; inline tags would not be parsed there.
- `"See also: [link:topic=2]ChDir[/link]  [link:topic=3]CurDir$[/link]"` — `ChDir` and `CurDir$` are clickable links to topics `2` and `3`.
- `"[nav:contents]Contents[/nav]  [nav:index]Index[/nav]  [nav:back]Back[/nav]"` — three navigation actions on one line, separated by spaces.

---

## 13. Versioning

| `uhf_version` | Status | Notes |
|---|---|---|
| `"2.0"` | Current | This spec. Structured topic lines with inline markup. |

Writers generating UHF 2.0 MUST include `"uhf_version": "2.0"`.  
Readers encountering an unknown version SHOULD reject the file with a clear error.

*Part of the [THelpViewer](https://github.com/) project.*
