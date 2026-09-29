# Converter

> Updated: 2026-09-29

Help file converter — reads binary and source help formats, exports to HTML, JSON bundles or Markdown.

The converter has no external dependencies beyond Python 3.10+.

## Usage

```bash
# Single file → HTML
python -m thelpviewer.converter TURBO.TPH output/

# Directory tree → HTML (with clean target)
python -m thelpviewer.converter sources/ output/ --clean

# JSON bundle for SPA viewer
python -m thelpviewer.converter sources/ www/ --bundle

# Specify encoding
python -m thelpviewer.converter TURBO7CZ.TPH output/ --encoding cp852

# Dump normalized HelpDocument as JSON
python -m thelpviewer.converter TURBO.TPH output/ --dump-json
```

## Options

| Option | Description |
|--------|-------------|
| `input` | Supported help file or directory tree, including HelpPC `.TXT` and FreeDOS `HHSTNDRD.ZIP` |
| `output_dir` | Target directory for exported files |
| `--encoding` | Display encoding: `auto`, `cp437`, `cp852`, `latin1`, `latin2`, `kamenicky` (default: `auto`) |
| `--clean` | Delete target directory before exporting a directory tree |
| `--dump-json` | Write `document.json` with the normalized HelpDocument model next to the exported files |
| `--bundle` | Export as gzip-compressed `.json.gz` bundles for the SPA viewer instead of individual HTML files |
| `--bundle-layout` | Bundle layout: `site` writes SPA assets + catalog, `helps` writes only bundle data |

## Architecture

The converter uses a pipeline architecture with automatic format detection:

```
Binary/Source Files → Format Detection → Reader → HelpDocument → Writer → Output
```

Before format detection, `thelpviewer/help-database.json` supplies shared
product and source metadata. Its product families group releases, define build
roots and conversion inputs, and map known CRC32 files to canonical collection,
title, encoding, and bundle metadata. It also defines converter handlers in
deterministic order, including the matcher/detector function and reader class.
`thelpviewer/help_database.py` validates and exposes the schema.

### 1. Format Detection

When the converter loads a file, `exporter.py` builds its ordered format
registry from the manifest. Handlers combine extension, magic-byte and/or
structural checks. Representative checks are:

| Check | Format |
|-------|--------|
| `.txt` with `.topic` directives | FBHF source text |
| `.hl6` or recognized `.hlx` structure | HLX source or binary |
| `.txt` with `@` title and `:` topic keys | HelpPC text database |
| `HHSTNDRD.ZIP` containing `help/index.htm` | FreeDOS HTML Help |
| `LN` + version word `0x0002` | Microsoft QuickHelp |
| `NG`/`EH` header or `.ng` | Norton Guide |
| `FBHF` magic | TurboVision FBHF binary |
| THELP signature | Borland THELP binary |
| `\x1a(c) Software602 HelpSystem` | M602 binary |

Detection is deterministic — each file triggers exactly one reader.
Unknown formats raise `ValueError`.

The HelpPC matcher requires an `@` title followed by `:` topic keys, so
unrelated `.TXT` files are not treated as HelpPC. The FreeDOS matcher requires
the `HHSTNDRD.ZIP` filename and `help/index.htm` archive member. See the
[HelpPC](../Formats/HelpPC%202.10.md) and
[FreeDOS HTML Help](../Formats/FreeDOS%20HTML%20Help.md) format notes.

### 2. Data Model (`base.py`)

All readers produce a single shared **HelpDocument** object:

```
HelpDocument
├── format_name: str         ("borland", "fbhf", "m602", "software602", "scorpion-dat", "scorpion-legacy", "game-cheater")
├── source_name: str         ("TURBO.TPH")
├── topics: list[TopicRecord]
│   ├── context_id: int
│   ├── raw_lines: list[bytes]
│   ├── index_terms: list[bytes]
│   ├── alias_contexts: list[int]
│   ├── sequential_keywords: list[int]     (THELP format ≥5)
│   ├── positional_keywords: list[PositionedKeyword]  (THELP format <5)
│   ├── names: list[str]                   (FBHF topic names)
│   ├── is_help_contents: bool
│   ├── up_context / down_context: int     (page navigation)
│   └── ...
├── index_entries: list[IndexEntry]
│   ├── label: bytes
│   └── context_id: int
├── comments: list[CommentRecord]
├── metadata: dict
│   ├── format_version, text_version
│   ├── height, width, left_margin
│   ├── stamp, signature, description
│   └── text_encoding
└── binary_data: bytes | None
```

The `raw_lines` in each topic are stored as raw bytes in the file's native
encoding (CP437, Kamenický, CP852, etc.). Display encoding is applied by
writers at export time, not by readers.

### 3. Encoding Detection (`codepages.py`)

When `--encoding auto` is used (the default), the converter uses a scoring
heuristic to choose the correct display encoding:

1. **Filename hint**: if the source name contains `CZ` or `602`,
   the file is flagged as a potential Czech/Slovak encoding candidate.
2. **Candidate list**: `kamenicky`, `cp852`, `latin2`, `cp437`, `latin1`
3. **Scoring**: each candidate decodes a sample of topic bytes and scores
   based on the frequency of Czech diacritical characters
   (á, č, ď, ě, í, ň, ...) and common Czech word stems
   (`nápově`, `příkaz`, `řádk`, ...).
   Mojibake characters (Polish/Romanian letters that shouldn't appear
   in Czech text) receive negative scores.
4. The candidate with the highest score wins.

For non-Czech files (no `CZ`/`602` in name), the default is `cp437`.

**Box-drawing ambiguity**: in CP852, bytes `0xB5`–`0xD8` overlap between
Czech letters and CP437 box-drawing characters. The `decode_bytes_box_aware()`
function resolves these ambiguities by checking adjacent bytes — if a
conflicting byte is next to an unambiguous box-drawing character, it is decoded
as box-drawing rather than a Czech letter.

### 4. Supported Encoding Tables

| Encoding | Range | Description |
|----------|-------|-------------|
| `cp437` | `0x80`–`0xFF` | Standard DOS / IBM PC (Western European + box-drawing) |
| `kamenicky` | `0x80`–`0xFF` | Kamenický (KEYBCS2), Czech/Slovak DOS encoding used by Software602 |
| `cp852` | `0x80`–`0xFF` | Central European DOS (Czech, Slovak, Polish, Hungarian) |
| `latin1` | `0x80`–`0xFF` | ISO 8859-1 (Western European) |
| `latin2` | `0x80`–`0xFF` | ISO 8859-2 (Central European) |

All encodings share CP437's low-byte mapping (`0x01`–`0x1F` → PC special
characters like ☺, ♥, ♦, ♣, ♠, •, ◘, etc.).

### Core Modules

| Module | Purpose |
|--------|---------|
| `base.py` | Shared in-memory model (`HelpDocument`, `TopicRecord`, `IndexEntry`, `HelpReaderBase`) |
| `exporter.py` | Format detection, reader dispatch, single-file and tree export coordination |
| `codepages.py` | Character encoding tables (CP437, Kamenický, CP852, Latin-1, Latin-2) and auto-detection |
| `../help_database.py` | Shared JSON manifest loader, product grouping, CRC lookup, and validation |

### Readers (`thelpviewer/converter/readers/`)

| Reader | Format | Signature | Binary/Text |
|--------|--------|-----------|-------------|
| `thelp.py` | Borland THELP (TP4–7, TC, TASM, Sidekick) | `$*$* &&&&$*$` | Binary |
| `fbhf.py` | TurboVision FBHF (TP6, TP7, BP7) | `FBHF` magic | Binary |
| `m602.py` | Software602 M602 HelpSystem | `\x1a(c) Software602 HelpSystem` | Binary (XOR $FA encrypted) |
| `hlx.py` | HLX/HL6 decompiled source text | `;SCREEN`/`;PAGE` directives | Text |
| `fbhf.py` | TVHC-compatible `.txt` source | `.topic` directives | Text |
| `helppc.py` | HelpPC 2.10 text databases | `@` title and `:` topic keys | Text |
| `freedos_html.py` | FreeDOS HTML Help | `HHSTNDRD.ZIP` with `help/index.htm` | ZIP of HTML text |
| `game_cheater.py` + `game_cheater_bundle.py` | Game-Cheater 9.02 Pc-Fand database, split into cheats, companies, internet addresses, help and information bundles | `CHEATDBS.000`, 111-byte records | Binary |
| `scorpion_dat_reader.py` | Scorpion's Cheater DAT 15-23 | Allegro DAT signature | Binary |
| `scorpion_legacy_reader.py` + `_v1x/_v3x/_v4x` | Scorpion's Cheater legacy families 1-14 | version-aware path + extension hints | Binary |

Each reader implements `read_bytes(data: bytes) → HelpDocument`.

### Writers (`thelpviewer/converter/writers/`)

| Writer | Output | Description |
|--------|--------|-------------|
| `html.py` | Multi-page HTML | One `.html` per topic + index + CSS/JS assets. TurboVision-style theme. |
| `bundle.py` | `.json.gz` bundle | Single gzip-compressed JSON with pre-rendered HTML. See [Bundle](Bundle.md). |
| `md.py` | Markdown | One `.md` per topic. Useful for further processing. |

### Export Orchestration (`exporter.py`)

| Function | Description |
|----------|-------------|
| `load_document(path)` | Load any supported file into a `HelpDocument` |
| `export_file(path, output_dir, ...)` | Single file → one output directory |
| `export_tree(input_dir, output_dir, ...)` | Recurse directory with subfolders |
| `export_bundle(path, output_dir, ...)` | Single file → `.json.gz` bundle |
| `export_bundle_tree(input_dir, output_dir, ...)` | Directory → bundles + `catalog.json` |

Tree exports preserve subdirectory structure from `sources/`. Bundle tree
exports also generate a `helps/catalog.json` that the SPA viewer loads at
startup.

The Help Files menu uses `product_name` as its family level and `version` as
the release level. A product's version-free `menu_label` in
`help-database.json` can be shared across releases even when their download
labels and physical source directories differ. For example, QuickBASIC 4.5
and QuickBASIC Extended 7.1 both appear under `Microsoft QuickBASIC`, then
under separate `4.5` and `7.1` entries. The catalog `file` path stays tied to
the existing bundle location, not to the menu labels.

Known files are deduplicated by CRC32. Product-level conversion rules cover
corpora where a release consists of several related files without stable CRCs.
For example, Game-Cheater's manifest bundles pair `.000` indexes with `.T00`
texts, while Scorpion's manifest selects its version-dependent data files and
lets the version readers assemble related sections.

## Supported Formats

See Formats for detailed binary format documentation:

- [Borland THELP](../Formats/Borland%20THELP.md) — TP4–5.5, Turbo C, TASM, Sidekick, Sprint
- [Microsoft BW03 Help](../Formats/Microsoft%20BW03%20Help.md) — older CodeView DOS / OS2 help
- [Microsoft QuickHelp](../Formats/Microsoft%20QuickHelp.md) — QuickBASIC, QuickC, MASM 6, PWB, LINK
- [Norton Guide](../Formats/Norton%20Guide.md) — Norton Guides and Expert Help
- [TurboVision FBHF](../Formats/TurboVision%20FBHF.md) — TP6, TP7, BP7 THelpFile
- [Software602 M602](../Formats/Software602%20M602.md) — M602 Manager HelpSystem
- [Software602 Text602](../Formats/Software602%20Text602.md) — Text602, Calc602
- [Scorpion's Cheater DAT](../Formats/Scorpion%20Cheater%20DAT.md) — modern DAT 15-23 plus notes about legacy branches
- [Game-Cheater Pc-Fand](../Formats/Game%20Cheater%20PC-Fand%20Format.md) — paired `.000`/`.T00` tables used by Game-Cheater 9.02
- [Help Source Text Format](../Formats/Help%20Source%20Text%20Format.md) — HLX/TXT decompiled source format
- [JSON Bundle](Bundle.md) — Transport format for SPA viewer
