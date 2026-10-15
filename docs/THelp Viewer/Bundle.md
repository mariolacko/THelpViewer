# THelp Viewer — Bundle Transport

> Updated: 2026-10-14

THelpViewer stores each converted help file as a gzip-compressed UHF 2.0
payload:

```text
<stem>.json.gz  →  gzip(UHF 2.0 JSON)
```

The logical payload format is defined in [../UHF2.md](../UHF2.md). This
document describes only the web transport used by the single-page viewer.

## 1. Files

- Bundle file: `helps/<group>/<stem>.json.gz`
- Help catalog: `helps/catalog.json`
- Docs catalog: `docs/catalog.json`

Example catalog entry:

```json
{
  "group": "Microsoft QuickBASIC Extended 7.1",
  "file": "Microsoft QuickBASIC Extended 7.1/bas7qck.json.gz",
  "name": "Microsoft BASIC Help",
  "product": "qbx",
  "product_name": "Microsoft QuickBASIC Extended",
  "version": "7.1",
  "menu_name": "Microsoft BASIC Help",
  "format": "quickhelp",
  "topics": 428
}
```

`product`, `product_name`, `version`, and `menu_name` are emitted by the bundle
writer and used by the TurboVision menu. Help Files is rendered as product →
version → bundle file from these explicit catalog fields.
Verified CRC editions retain their explicit `release` in `version`, even when
their shared publication directory has no release in its name. Missing versions
are not guessed from bundle filenames. If sibling files have equal menu titles,
the viewer adds each bundle stem (or its path if stems coincide), keeping every
file selectable; it does not deduplicate by title.

`topics` counts the topic objects actually emitted in UHF, excluding
redirect-only source contexts represented as aliases. The same count is used
by direct exports, grouped/variant exports and catalog rebuilds. For example,
TDH 1.0 has 530 runtime contexts but 519 emitted topics and 11 alias continuations.

`source_file` is the physical/canonical original filename. `source_files`
additionally contains reader-verified aliases, including logical QuickHelp
database names contained in one physical `.HLP`. A concatenated file still
publishes at the same bundle path, with first-database topic IDs unchanged.
These identities also live in `metadata.catalog_source_files` so a catalog rebuilt
from gzip bundles retains them. Matching an original name with an extension
does not fall back to unrelated extensions or an arbitrary bundle stem. Only
current bundle paths and verified source/database names are accepted. Ambiguous
filename matches without a matching collection/product/version fail; old URL
aliases and basename-only compatibility lookups are not retained.

## 2. Loading Flow

Standalone site exports copy the current package assets and generate their
entry page with the same JS/CSS cache revisions as `www/index.html`. Changing
an asset revision requires updating the generated template too; the metadata
regression checks that the two entry pages match, so an export cannot keep
requesting cached pre-TextScreen viewer code.

1. The viewer loads `helps/catalog.json`.
2. When the user opens a help file, the viewer fetches the matching
   `.json.gz` bundle.
3. The downloaded bytes are decompressed in the browser with
   `DecompressionStream("gzip")`.
4. The resulting UTF-8 text is parsed as JSON.
5. The UHF 2.0 payload is rendered into the TurboVision-style window UI.

Native text screens use root `text_screens` and shared `fonts` resources.
Each cell retains its glyph byte and foreground/background palette indexes;
font bits are carried once as Base64 inside the gzip bundle. The HELP adapter
resolves the existing UHF palette and creates owned `TVTextScreen` views in
the standard HELP client area. No PNG or separate image download is involved.
Screen rows retain visible line addresses and searchable literal text.
Cells can be readable triples or Base64: `dos-text` preserves the original
two-byte DOS cells, while `glyph-fg-bg` stores three independent byte indexes.
The explicit `dos-text-blink` and `dos-text-bright` variants keep the same
native two bytes while recording whether bit 7 means blinking foreground or
bright background. Readable and `glyph-fg-bg` cells can carry a separate
boolean `blink` mask. The viewer decodes all forms into the same shared
TextScreen object, slicing the flags with each row and retaining background
colors during hidden phases. Reduced motion keeps glyphs visible; navigation
and window destruction release the owned animation resources.

## 3. Compression

Measured on the current generated payloads:

| Source | Raw UHF JSON | Compressed `.json.gz` | Reduction |
|--------|--------------:|----------------------:|----------:|
| `Borland Pascal 4.0/TURBO.HLP` | 326,369 B | 47,130 B | 85.6% |
| `Microsoft QuickBASIC Extended 7.1/BAS7QCK.HLP` | 858,630 B | 115,323 B | 86.6% |
| `Norton Guides/DOS.NG` | 125,313 B | 22,072 B | 82.4% |
| `Borland C++ 3.1/TCHELP.TCH` | 4,513,532 B | 626,963 B | 86.1% |

## 4. Notes

- Compression is a transport detail. After decompression, the payload is plain
  UHF 2.0 JSON.
- `catalog.json` stays uncompressed so the viewer can build menus immediately.
- Topic ids inside the payload remain numeric fields; only JSON object keys are
  strings, as documented in [../UHF2.md](../UHF2.md).

## 5. Public navigation URLs

Menu entries for HELP files and Docs expose `?file=<bundle-path>` and
`?doc=<document-path>` URLs. Index entries, Contents nodes and inline UHF links
expose `?file=<bundle-path>&topic=<id>`; an optional `line=<n>` restores the
target text line. Values are encoded with `URLSearchParams`, including literal
`+` characters in product names. The current viewer pathname is retained, so
exported `index.html` bundles also support these links.

These are browser fallbacks for existing TVision commands, not a second
navigation system: ordinary clicks still pass through `TVEvent`. The menu's
shared drawing primitive emits anchors for navigation entries and buttons for
application actions, keeping the original positional constructors. Modified
clicks retain the browser's new-tab/window behavior.

Topic aliases in loaded bundles resolve to their real IDs. The server index
also stores numeric UHF `aliases.ids` as file-scoped mappings, not duplicate
full-text topics. An unresolved explicit alias uses
`?file=...&alias=<native-alias>`; its spelling and namespace survive until
the target is loaded. The server resolves the alias and redirects to the
real article ID/cursor, retaining an explicit `line` and viewer options.
`topic=<id>` uses article-ID priority; `alias=<name>` uses only declared
aliases even if its name is numeric or collides with an article ID.
Only real topic IDs enter search results and sitemaps. Updating/removing a
bundle also replaces/removes its alias mappings; the index revision refreshes
older caches automatically without modifying source HELP files.
External original
filenames resolve through the existing catalog, with preference for the current
product collection. If a target bundle is not loaded, the public alias URL
still opens the exact source target, not the file overview. The TVEvent
target retains the same explicit namespace. Missing source files and application-only
context help do not receive invented public URLs. The initial server text is
replaced by the corresponding viewer content; catalog links remain available
in the rendered menus rather than as duplicate hidden HTML.

An explicit missing target reports a broken link without opening the first
unrelated topic. File-only requests may open Contents; defined QuickHelp
navigation commands may open Contents/Index. Ordinary context strings must
resolve to a real topic. Qualified aliases distinguish concatenated databases;
their case-sensitive context flags are retained in `quickhelp_databases`.

## 6. Multi-page topics

The shared status line exposes Previous/Next when the active topic has a real
link target under `nav.Prev`/`nav.Next`. These TVStatusItem commands pass through
`TVEvent` and the normal UHF target resolver; they do not guess adjacent numeric
IDs. They follow the active HELP window, disappear in Index/Contents and other
windows, and stop at the reader-defined boundaries. Other source-provided nav
labels retain their existing menu behavior.

Contents also permits direct selection of a continuation page. Sidekick 1
groups `Page 2`, `Page 3`, etc. under each original context; its terminal
`More..` cue is clickable when backed by the source page separator.
