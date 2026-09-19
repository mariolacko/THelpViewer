# Help Format Comparison

> Created: 2026-04-08

Compares the six source formats supported by THelpViewer across every data
element the viewer can display or navigate.  
Readers: THELP (Borland), Norton Guide (.NG), Microsoft QuickHelp (.HLP),
Turbo Vision FBHF, Software602 M602, textual HLX source.

---

## 1. Feature Matrix

✅ supported · ⚠️ partial / heuristic · ❌ not available

| Data element | THELP | Norton Guide | QuickHelp | FBHF | M602 | HLX source |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Topic identifier** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Topic title (explicit)** | ❌¹ | ❌¹ | ✅ | ✅ | ✅ | ✅ |
| **Plain text lines** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Searchable index entry** | ✅ | ❌² | ✅ | ✅ | ✅ | ✅ |
| **Alias / alternate context ids** | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Hyperlink — local topic** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Hyperlink — navigation action** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Inline hotspot delimiters (0x02)** | ✅ v5 only | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Navigation: Up** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Navigation: Down / Next** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Navigation: Left / Right (nav tuple)** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Is-main-index flag** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Code block (explicitly marked)** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Code block (heuristic detection)** | ⚠️ TC 2.x | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Text style: Bold** | ❌ | ✅³ | ✅ | ❌ | ❌ | ❌ |
| **Text style: Italic** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Text style: Underline** | ❌ | ✅³ | ✅ | ❌ | ❌ | ❌ |
| **Text style: Reverse video** | ❌ | ✅³ | ❌ | ❌ | ❌ | ❌ |
| **Color: foreground / background** | ❌ | ✅³ | ❌ | ❌ | ❌ | ❌ |
| **Metadata: file title / stamp** | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Metadata: author / copyright** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Metadata: display width** | ✅ | ❌⁴ | ✅ | ✅⁴ | ❌ | ✅ |
| **Metadata: display height** | ✅ | ❌ | ❌ | ✅⁴ | ❌ | ✅ |
| **Frozen rows (scroll-lock header)** | ❌ | ❌ | ✅⁵ | ❌ | ❌ | ❌ |
| **Preserved source comments** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |

**Notes:**
1. THELP topics carry no separate title field. NG `SHORT`/`LONG` records also have no dedicated title field, but NG labels can usually be derived from the referring `MENU`/`SHORT` entry via `Parent` + `Parent Line`; the first visible `LONG` line is only a fallback.
2. NG has no dedicated global alphabetical index table; a converter can synthesise one from menu prompts, short-entry labels, and parent-derived `LONG` labels.
3. Norton Guide encodes these as inline escape sequences (`^B`, `^U`, `^N`, `^R`, `^Ann`). The current reader surfaces them as UHF style spans even though the plain `raw_lines` view is de-styled.
4. Implied / fixed values: NG is always 76 chars wide; FBHF is always 50 × 18.
5. QuickHelp `:l N` command (`.freeze` directive) freezes the first N lines so they remain visible while the user scrolls. The reader stores this as `frozen_rows`.

---

## 2. Per-Element Detail

### Topic identifier

| Format | Storage |
|---|---|
| **THELP** | Sequential zero-based integer; matches the order of `RT_CONTEXT` records in the binary. |
| **Norton Guide** | Absolute byte offset of the block inside the `.NG` file (32-bit). Records are enumerated sequentially using `next = offset + 26 + payload_size`; links then resolve those physical offsets. |
| **QuickHelp** | Sequential zero-based integer; index into the `TopicIndex` array in the file header. Context strings in `ContextMap` are resolved to these integers at load time. |
| **FBHF** | Sequential integer starting at 2; derived from the `.topic name[=N]` declarations in the textual source. |
| **M602** | Sequential integer derived from the tail index at the end of the binary file. |
| **HLX source** | `;SCREEN N` / `;PAGE N` header gives the exact integer directly. |

---

### Topic title

| Format | Storage |
|---|---|
| **THELP** | No explicit title field. Viewer uses the first non-empty decoded text line. |
| **Norton Guide** | No explicit title field on `SHORT`/`LONG` records. `MENU` prompts and `SHORT` lines carry visible labels, while `LONG` records carry `Parent` + `Parent Line` so the label can often be recovered from the referring entry. First visible `LONG` line is only a fallback. |
| **QuickHelp** | Command line `:n <text>` inside the topic binary stream. Stored in `topic.names[]`. May be absent — then the viewer falls back to the first visible raw line. |
| **FBHF** | First name in the `.topic name1,name2` directive. All names are stored in `topic.names[]`. |
| **M602** | First text line up to the `0xDC` title-end byte; decoded as Latin. |
| **HLX source** | `;SCREEN label` comment above the screen body text. |

---

### Searchable index entries

| Format | Storage |
|---|---|
| **THELP** | `RT_INDEX` records: each is a label byte-string paired with a context id. Separate from the topic text. |
| **Norton Guide** | No dedicated global index block. A converter can synthesise index entries from `MENU` prompts, `SHORT` lines, and parent-derived labels for `LONG` records. |
| **QuickHelp** | `ContextStrings` section: NUL-terminated ASCII strings mapped to topic indices via `ContextMap`. Human-readable names come from `:n` command lines; context strings (e.g. `h.pg1`) are used as last resort. |
| **FBHF** | All `.topic` names become index entries. |
| **M602** | All topic title strings (up to `0xDC` per topic) become index entries. |
| **HLX source** | `;INDEXORDER N label` directives define the ordered index. |

---

### Hyperlinks (local topic)

| Format | Storage |
|---|---|
| **THELP v4 (old)** | `RT_KEYWORD` records: each gives `(context_id, line, col_start, col_end)` — a positional range in one display line plus an optional navigation 4-tuple. |
| **THELP v5 (new)** | `0x02` delimiter bytes inline in `raw_lines`. `sequential_keywords` list gives context ids in order of occurrence. |
| **Norton Guide** | `MENU` prompts and `SHORT` lines each point to child entries by absolute file offset. `LONG` entries have a separate "see also" section with labeled pointers. |
| **QuickHelp** | Attribute block (after `0xFF` separator): list of `(start_byte, end_byte, context_string)` records per display line. Inline `0x11`/`0x10` markers visually bracket the link text in the raw stream. |
| **FBHF** | Inline `0x02` marker bytes delimit link text; a separate cross-reference list gives `(name, byte_offset, length)` tuples per topic. |
| **M602** | `0x02` marker bytes inline; the linked topic is identified by its title string resolved at load time. |
| **HLX source** | `{link text:target_name}` brace syntax inline in the text; resolved to context ids after all topics are parsed. |

---

### Navigation action links (Back / Contents / Index)

| Format | Storage |
|---|---|
| **QuickHelp only** | Context string in the attribute block: `!B` = Back, `*!HV` = Contents, `*!VX` = Index. Supplementary QBX databases additionally use the literal strings `"-9996"` (Contents) and `"-9997"` (Index). These are translated to shared pseudo-context ids `NAV_BACK_CONTEXT (-1)`, `NAV_CONTENTS_CONTEXT (-2)`, `NAV_INDEX_CONTEXT (-3)` at parse time and rendered as `data-tv-nav` anchor attributes. |
| **All other formats** | Not present. |

---

### Navigation: Up / Down / Prev / Next

| Format | Storage |
|---|---|
| **THELP** | Binary file: `up_context` and `down_context` DWORDs inside each `RT_CONTEXT` record. HLX source: `;LINK UP N DOWN N` comment lines. THELP v4 positional keywords also carry a `navigation=(left, right, up, down)` 4-tuple per hotspot. |
| **Norton Guide** | `SHORT` and `LONG` headers contain `Parent` (Up). `LONG` headers additionally contain `Previous` and `Next` sibling offsets. `Parent Line` identifies which label in the parent entry points to the child. |
| **QuickHelp** | Not present in the binary format. |
| **FBHF / M602 / HLX** | Not present. |

---

### Code blocks

| Format | Storage |
|---|---|
| **THELP (TC 1.x, BP ≥ 3)** | Standalone lines containing only the bytes `0x03`, `0x05`, or `0x10` toggle code-example mode on/off. Lines between two such markers are displayed as code. The marker lines themselves are not displayed. |
| **THELP TC 2.0/2.01** | No explicit marker. A line matching `Examples?:` (case-insensitive) starts a code block; the block ends when a non-empty, non-indented line appears. The reader resolves this into `code_line_indices`. |
| **HLX source** | Same control-byte conventions as binary THELP. |
| **All other formats** | No code block concept. |

---

### Text styles: Bold, Italic, Underline, Reverse, Color

| Format | Storage |
|---|---|
| **Norton Guide** | Inline escape sequences in raw text: `^B` toggles bold, `^U` toggles underline, `^N` resets to normal, `^R` toggles reverse video. Color is `^Ann` where `nn` is a two-hex-digit CP437 attribute byte (high nibble = background color index 0–15, low nibble = foreground color index 0–15). The current reader converts these to UHF style spans. |
| **QuickHelp** | Attribute block styles section (before `0xFF`): alternating `(ChunkLen, StyleByte)` pairs. Style byte bit 0 = Bold, bit 1 = Italic, bit 2 = Underline. No color. The reader converts these to UHF style spans; marker-heavy tab rows are normalized separately. |
| **THELP / FBHF / M602 / HLX** | No character-level style or color information in the format. |

---

### File metadata

| Field | THELP | Norton Guide | QuickHelp | FBHF | M602 | HLX |
|---|---|---|---|---|---|---|
| **Title / stamp** | `$*$* &&&&$*$` block contains a human-readable stamp string (e.g. `TURBO PASCAL HELP FILE.`) | 40-byte title field in the unencrypted header at offset 8 | 14-byte `DatabaseName` field at offset `0x10` | No header title | `(c) Software602 HelpSystem` prefix only | `;STAMP` comment line |
| **Author / copyright** | First lines of stamp string (product-specific) | Five 66-byte credit lines starting at offset 48 | Not present | Not present | Not present | Not present |
| **Display width (chars)** | `width` field in file header | Implied 76 (fixed) | `DisplayWidth` WORD at offset `0x0C` | Implied 50 (fixed) | Not present | `;WIDTH N` |
| **Display height (rows)** | `height` field in file header | Not present | Not present | Implied 18 (fixed) | Not present | `;HEIGHT N` |
| **Frozen rows (scroll-lock)** | Not present | Not present | `:l N` command (`.freeze` directive) per topic — parsed into `frozen_rows`, so the first N lines stay fixed during scroll. | Not present | Not present | Not present |
| **Encoding** | CP437 implied by format | CP437 fixed | CP437 fixed | Latin-1 (source) | Latin-1 / CP852 guessed | Guessed from content |
| **Format / text version** | Two bytes at start of binary: `format_version`, `text_version`; determines binary layout variant | Not versioned | Version `0x0002` fixed | Not versioned | Not versioned | Derived from `;STAMP` |

---

## 3. What the Current `TopicRecord` Carries

```python
@dataclass
class TopicRecord:
    context_id: int                          # numeric topic id
    raw_lines: list[bytes]                   # raw CP437/Latin bytes (may contain control codes)
    index_terms: list[bytes]                 # searchable labels (THELP only)
    alias_contexts: list[int]                # alternative context ids for the same topic
    sequential_keywords: list[int]           # THELP v5 / FBHF / M602 inline hotspot targets
    positional_keywords: list[PositionedKeyword]  # line+col link ranges (THELP v4, NG, QuickHelp)
    is_help_contents: bool
    up_context: int | None
    down_context: int | None
    names: list[str]                         # explicit titles (QuickHelp :n, FBHF .topic)
```

**Remaining format-specific cleanup opportunities:**

| What | Where today | Should move to |
|---|---|---|
| Norton Guide dual text decode paths | `_expand_text()` in ng.py de-styles `raw_lines`, while `_expand_text_to_uhf_parts()` preserves styles/colors for UHF | Unify around one decode path so raw/plain and styled output cannot drift |
| Exporter format registry | Format detection is duplicated in `load_document()` and `iter_help_files()` | One shared registry with suffixes + detectors + reader factory |

---

## 4. Proposed `code_line_indices` field (lowest-effort improvement)

Add `code_line_indices: set[int]` to `TopicRecord` (zero-based line indices that should be rendered as code). This removes all code-block detection from the renderer without changing `raw_lines` or the bundle JSON schema.

**THELP reader change:**
```python
marker_bytes = {0x03, 0x05, 0x10}
code_lines: set[int] = set()
in_code = False
cleaned: list[bytes] = []
for line in raw_lines:
    stripped = line.strip(b" \t")
    if stripped and all(b in marker_bytes for b in stripped):
        in_code = not in_code   # toggle
        continue                # drop marker line from raw_lines
    if in_code:
        code_lines.add(len(cleaned))
    cleaned.append(line)
```

**TC 2.0/2.01 heuristic (same field, applied when `format_version==4, text_version==1`):**
```python
_EXAMPLE_RE = re.compile(rb"^Examples?\s*:", re.IGNORECASE)
in_code = False
for i, line in enumerate(raw_lines):
    decoded = line.decode("cp437", errors="replace")
    if _EXAMPLE_RE.match(decoded):
        in_code = True
    elif in_code and decoded.strip() and not decoded.startswith(" "):
        in_code = False
    if in_code:
        code_lines.add(i)
```

*Part of the [THelpViewer](https://github.com/) project.*
