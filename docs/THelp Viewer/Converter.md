# Converter

> Updated: 2026-04-05

Help file converter — reads binary and source help formats, exports to HTML, JSON bundles or Markdown.

The converter has no external dependencies beyond Python 3.10+.

## Usage

```bash
# Single file → HTML
python -m converter TURBO.TPH output/

# Directory tree → HTML (with clean target)
python -m converter sources/ output/ --clean

# JSON bundle for SPA viewer
python -m converter sources/ www/ --bundle

# Specify encoding
python -m converter TURBO7CZ.TPH output/ --encoding cp852

# Dump normalized HelpDocument as JSON
python -m converter TURBO.TPH output/ --dump-json
```

## Options

| Option | Description |
|--------|-------------|
| `input` | Input `.hlp`/`.tph`/`.tch`/`.hlx`/`.hl6`/`.txt` file or directory tree |
| `output_dir` | Target directory for exported files |
| `--encoding` | Display encoding: `auto`, `cp437`, `cp852`, `latin1`, `latin2`, `kamenicky` (default: `auto`) |
| `--clean` | Delete target directory before exporting a directory tree |
| `--dump-json` | Write `document.json` with the normalized HelpDocument model next to the exported files |
| `--bundle` | Export as gzip-compressed `.json.gz` bundles for the SPA viewer instead of individual HTML files |

## Architecture

The converter uses a pipeline architecture with automatic format detection:

```
Binary/Source Files → Format Detection → Reader → HelpDocument → Writer → Output
```

### 1. Format Detection

When the converter loads a file, `exporter.py` determines the format using
file extension and magic-byte detection:

| Priority | Check | Format |
|----------|-------|--------|
| 1 | Extension `.txt` + contains `.topic` | FBHF source text |
| 2 | Extension `.hl6` | HLX source text (HL6 dialect) |
| 3 | Extension `.hlx` + contains `.topic` | FBHF source text |
| 4 | Extension `.hlx` | HLX source text |
| 5 | First bytes = `$*$* &&&&$*$` (in first 200 bytes) | Borland THELP binary |
| 6 | First 4 bytes = `FBHF` | TurboVision FBHF binary |
| 7 | First bytes = `\x1a(c) Software602 HelpSystem` | M602 binary |
| 8 | Extension `.hlp`/`.tph`/`.tch` → falls through to THELP | Borland THELP binary |

Detection is deterministic — each file triggers exactly one reader.
Unknown formats raise `ValueError`.

### 2. Data Model (`base.py`)

All readers produce a single shared **HelpDocument** object:

```
HelpDocument
├── format_name: str         ("borland", "fbhf", "m602", "software602")
├── source_name: str         ("TURBO.TPH")
├── topics: list[TopicRecord]
│   ├── context_id: int
│   ├── raw_lines: list[bytes]
│   ├── index_terms: list[bytes]
│   ├── alias_contexts: list[int]
│   ├── sequential_keywords: list[int]     (THELP format ≥5)
│   ├── positional_keywords: list[PositionedKeyword]  (THELP format <5)
│   ├── names: list[str]                   (FBHF topic names)
│   ├── is_main_index: bool
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

### Readers (`converter/readers/`)

| Reader | Format | Signature | Binary/Text |
|--------|--------|-----------|-------------|
| `thelp.py` | Borland THELP (TP4–7, TC, TASM, Sidekick) | `$*$* &&&&$*$` | Binary |
| `fbhf.py` | TurboVision FBHF (TP6, TP7, BP7) | `FBHF` magic | Binary |
| `m602.py` | Software602 M602 HelpSystem | `\x1a(c) Software602 HelpSystem` | Binary (XOR $FA encrypted) |
| `hlx.py` | HLX/HL6 decompiled source text | `;SCREEN`/`;PAGE` directives | Text |
| `fbhf.py` | TVHC-compatible `.txt` source | `.topic` directives | Text |

Each reader implements `read_bytes(data: bytes) → HelpDocument`.

### Writers (`converter/writers/`)

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

## Supported Formats

See Formats for detailed binary format documentation:

- [Borland THELP](../Formats/Borland%20THELP.md) — TP4–5.5, Turbo C, TASM, Sidekick, Sprint
- [TurboVision FBHF](../Formats/TurboVision%20FBHF.md) — TP6, TP7, BP7 THelpFile
- [Software602 M602](../Formats/Software602%20M602.md) — M602 Manager HelpSystem
- [Software602 Text602](../Formats/Software602%20Text602.md) — Text602, Calc602
- [Help Source Text Format](../Formats/Help%20Source%20Text%20Format.md) — HLX/TXT decompiled source format
- [JSON Bundle](Bundle.md) — Transport format for SPA viewer
