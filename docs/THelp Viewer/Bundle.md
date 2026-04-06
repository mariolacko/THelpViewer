# THelp Viewer — JSON Bundle Format

> Updated: 2026-04-04

Transport format for the THelpViewer single-page application.
Each help file is compiled into a single `.json.gz` file — a native
gzip-compressed JSON payload served directly over HTTP.

## 1. File Structure

A bundle file is a gzip-compressed UTF-8 JSON document:

```
<stem>.json.gz   →   gzip(JSON payload)
```

| Part | Description |
|------|-------------|
| `<stem>` | Lowercase stem of the source file (e.g. `turbo`, `tchelp`, `sk2`) |
| Compression | gzip level 9, served as a binary `.json.gz` file |

### Decompression (browser side)

```
fetch(url) → ReadableStream → DecompressionStream("gzip") → Response.text() → JSON.parse
```

Uses the Web Streams API (`DecompressionStream`), supported in all modern browsers.
The browser fetches the raw `.json.gz` binary and decompresses it client-side.

## 2. JSON Payload

The decompressed JSON object has this structure:

```json
{
  "name":              "Turbo Pascal Help",
  "source_name":       "TURBO7CZ.TPH",
  "format_name":       "borland",
  "encoding":          "kamenicky",
  "header_label":      "Turbo Pascal Help",
  "index_label":       "Index",
  "window": {
    "cols":     78,
    "rows":     21,
    "min_cols": 40,
    "min_rows": 10
  },
  "help_context":      "0001",
  "topic_count":       1334,
  "index_entry_count": 1280,
  "index_entries":     [ ... ],
  "topics":            [ ... ],
  "search_index":      [ ... ]
}
```

### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable name from the help file header |
| `source_name` | string | Original source file name (e.g. `TURBO7CZ.TPH`) |
| `format_name` | string | One of: `borland`, `fbhf`, `m602`, `software602` |
| `encoding` | string | Display encoding used: `cp437`, `cp852`, `kamenicky`, `utf-8`, etc. |
| `header_label` | string | Label for the window title bar |
| `index_label` | string | Label for the index page heading |
| `window` | object | Default window geometry in character cells |
| `window.cols` | int | Default width in columns |
| `window.rows` | int | Default height in rows |
| `window.min_cols` | int | Minimum width |
| `window.min_rows` | int | Minimum height |
| `help_context` | string\|null | 4-digit hex context ID of the main help topic |
| `topic_count` | int | Number of topics |
| `index_entry_count` | int | Number of index entries |
| `index_entries` | array | Index entries for the A–Z navigation page |
| `topics` | array | All topics with pre-rendered HTML |
| `search_index` | array | Search-optimized topic list |

### `index_entries[]`

```json
{
  "label":        "TApplication.Run",
  "context_id":   42,
  "context_hex":  "002A"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Display text for the index entry |
| `context_id` | int | Numeric context identifier |
| `context_hex` | string | 4-digit uppercase hex, used for cross-references |

### `topics[]`

```json
{
  "context_id":    42,
  "context_hex":   "002A",
  "title":         "TApplication.Run",
  "html":          "<pre class=\"tv-pre tv-topic-pre\">...</pre>",
  "is_main_index": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `context_id` | int | Numeric context identifier |
| `context_hex` | string | 4-digit hex used in cross-reference links |
| `title` | string | Topic heading text |
| `html` | string | Pre-rendered HTML fragment (complete `<pre>` block) |
| `is_main_index` | bool | `true` if this is the default index topic |

Cross-reference links in the HTML use `<a href="XXXX.html">` with 4-digit hex.
The viewer rewrites these to `data-tv-bundle-topic="XXXX"` at runtime.

### `search_index[]`

```json
{
  "context_hex":  "002A",
  "title":        "TApplication.Run",
  "text":         "tapplication run method runs the application..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `context_hex` | string | 4-digit hex context ID |
| `title` | string | Topic title for display in search results |
| `text` | string | Normalized plain text for substring matching |

## 3. Catalog

The catalog is a separate `helps/catalog.json` file loaded at startup:

```json
[
  {
    "group":   "Borland Turbo Pascal 7",
    "file":    "Borland Turbo Pascal 7/turbo.json.gz",
    "name":    "Borland Pascal 7",
    "format":  "borland",
    "topics":  1340
  },
  ...
]
```

| Field | Type | Description |
|-------|------|-------------|
| `group` | string | Product group name (used for submenu grouping) |
| `file` | string | Relative path to the `.json.gz` bundle under `helps/` |
| `name` | string | Human-readable display name |
| `format` | string | Format identifier |
| `topics` | int | Number of topics |

The viewer uses this catalog to populate the Help Files menu and trigger
on-demand loading of `.json.gz` bundles.

## 4. Compression Ratios

Typical compression (gzip level 9):

| Source | Uncompressed JSON | Compressed `.json.gz` | Ratio |
|--------|-------------------|------------------------|-------|
| DEMOHELP.HLP | ~40 KB | ~8 KB | ~80% |
| TURBO.TPH | ~3.5 MB | ~580 KB | ~83% |
| WINDOWS.TPH | ~8.4 MB | ~1.7 MB | ~80% |

Note: `.json.gz` is ~25% smaller than the previous base64-wrapped `.js` format
because base64 encoding adds ~33% overhead.

## 5. Loading Flow

1. User selects a file from the Help Files menu
2. Viewer shows a Loading dialog with progress bar
3. `fetch()` downloads the `.json.gz` file with `ReadableStream` progress tracking
4. Response bytes are piped through `DecompressionStream("gzip")`
5. Decompressed text is parsed as JSON
6. Bundle is cached in memory; Loading dialog closes
7. Index page renders with A–Z letter navigation
