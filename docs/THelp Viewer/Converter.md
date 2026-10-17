# Converter

> Updated: 2026-10-16

Help file converter — reads binary and source help formats, exports to HTML, JSON bundles or Markdown.

Use Python 3.10+ and the repository requirements. Container ingestion may also
need unar/lsar or 7zz; decoding format-specific compression uses the reader's
declared dependencies.

## Usage

```bash
# Single file → HTML
python -m thelpviewer.server.converter TURBO.TPH output/

# Directory tree → HTML (with clean target)
python -m thelpviewer.server.converter var/sources/ output/ --clean

# JSON bundle for SPA viewer
python -m thelpviewer.server.converter var/sources/ www/ --bundle

# Specify encoding
python -m thelpviewer.server.converter TURBO7CZ.TPH output/ --encoding cp852

# Dump normalized HelpDocument as JSON
python -m thelpviewer.server.converter TURBO.TPH output/ --dump-json
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

The converter's public processing responsibilities are separate:

- `ingest.py` consumes `HelpInput` source plans, calls the shared
  `server/archives/` layer, selects required members and retains originals.
- `sources.py` owns CRC-aware source collection; `selection.py` owns the
  request-local edition filter used by discovery and ingestion.
- `planning.py` owns build groups, canonical bundle destinations and collision
  selection; `metadata.py` owns product/version/menu metadata.
- Readers return `HelpDocument`; writers serialize it without fetching URLs.
- `results.py` defines conversion results with an explicit `error` string.
  Failed conversions retain their actual diagnostic, not an ERROR format ID.
- `validation.py` validates gzip/JSON, UHF version, required structures and
  topic IDs/content before `catalog.py` builds the catalog. External links are
  not rejected just because their target belongs to a different bundle.

`export_bundle_tree(include_catalog=False)` lets the staged server build own
the one final catalog pass; standalone exports include the catalog by default.
Both paths use the same catalog builder. UHF and catalogs are atomically
written, so a failed write does not replace an existing file.

Server builds call `converter.build.build_help_groups()` directly. It converts
only the selected manifest groups, stages bundles next to `data/helps/`, rebuilds
the catalog through `converter.catalog.rebuild_catalog()`, and keeps live
output untouched until validation succeeds. The previous generation remains
as a recoverable sibling backup. `tools/rebuild_catalog.py` is a CLI adapter.
Package installation passes `package_ids` and `keep_packages` to select exact
`product:version` editions. Source identity uses verified CRC metadata and the
same canonical collection calculation as the exporter, not an archive folder's
name alone. Removing/rebuilding one edition keeps other versions byte-for-byte;
missing selected inputs or failed conversion leave live publication untouched.
`export_bundle_tree()` accepts optional `source_paths` and an `on_progress`
callback. CRC collections remain authoritative. For files without CRC metadata,
declared source containers are omitted only when their child directory matches
a publication prefix in the same manifest build group. Exporting the complete
source tree or that product container therefore retains the same public paths
and menu versions (including Scorpions/Game-Cheater); unknown directories are
not stripped. Existing CLI
exports remain available; the server does not run them as commands.
See [Server Content](Server%20Content.md).

Recognition is not a promise that every historical profile can be decoded.
Turbo Basic `TBHELP.TBH` uses a separate WORD-record/space-packing reader,
verified against the original `TB.EXE`, rather than the later nibble THELP
decoder. It retains continuation screens addressed only by native offsets;
generated IDs at `65536 + physical screen ordinal` identify screens without
context slots. MicroCalc's `.HLP` text grammar remains separate. Malformed
inputs fail a selected staged build without replacing the published library.
Remaining verification is tracked in the repository's
`TODO.md`, which is not part of the public Docs catalog.

The converter uses a pipeline architecture with automatic format detection:

```
Binary/Source Files → Format Detection → Reader → HelpDocument → Writer → Output
```

Before format detection, `thelpviewer/config/help-database.json` supplies shared
product and source metadata. Its product families group releases, define build
roots and conversion inputs, and map known CRC32 files to canonical collection,
title, encoding, and bundle metadata. It also defines converter handlers in
deterministic order, including the matcher/detector function and reader class.
`thelpviewer/help_database.py` validates and exposes the schema.
An auxiliary tool's release is its own version, not the release of the C++ or
Pascal distribution containing it. CRC entries for all current TASM originals
declare explicit releases (2.0, 2.01, 3.0, 3.1, 3.2 (DE)); byte-identical copies
share one registered output. Their verified distribution collections remain
unchanged where needed for real cross-file lookup. Catalog product/version
metadata, not physical folder nesting, controls the Help Files hierarchy.

### Conversion input selection

`archive_members` in `help-database.json` is the shared list of files to extract
and process. Turbo Pascal 7 uses `"archive_members": ["TURBO.TPH"]` for its
compiler archive and `"archive_members": ["OWL.TPH", "TVISION.TPH"]` for the
library archive. Their combined selection is those three HELP files.

The server and CLI use the same lists for HTML/UHF batch builds, including
explicit batches and already-extracted originals. Source queries retain full
archive paths; published originals use their canonical basenames. Matching is
case-insensitive. An explicit archive plan still requires every listed member
and rejects ambiguous matches. Broad discovery reuses the complete edition list
instead of copying unrelated HELP files from the archive.

Edition lists stay with edition sources: Turbo Pascal 5.5 still uses TURBO.HLP,
not the 7.0 list. A retrieval recipe for only one component is not treated as a
complete edition list while other registered components have no member lists.
Products without a complete declared selection retain normal format discovery.
CRC ownership takes precedence over a mixed archive's directory label.
For an explicitly selected registered edition, an unknown CRC in a different
collection is not identified by filename alone. Unknown/corrupt inputs in the
edition's canonical collection still undergo decoder validation and can fail
the build; unregistered formats retain their usual discovery rules.

Originals sharing a filename but belonging to distinct registered releases need
distinct `collection` paths in the manifest. Debugger originals use release
subdirectories, keeping their physical DOS filenames intact. A corrected
collection can relocate an existing CRC-verified source without overwriting
different data; source and output planning both use the same manifest.

The server may pass `source_batches`, an iterator of ready edition IDs, with
explicit `package_ids` to `build_help_groups`. Each edition is selected and
converted when ready while downloading/extraction continues. Duplicate/unknown
IDs or an incomplete iterator fail the build. Every result remains in one
staging tree until all requested editions, bundle validation and catalog
generation succeed; an exception cannot publish the earlier partial results.
Without `source_batches`, CLI and direct API builds retain full-batch discovery.
`backup_dir` selects the recovery destination: the server uses
`var/backups/help/`; standalone calls default to `<helps-parent>/backups/help/`.
The previous live directory stays beside HELP only during atomic publication
and is moved to a managed `help-<id>` generation after success. Backup transfer
failure keeps that original recovery tree and logs its path rather than
rolling back an already published valid library.

Unselected originals are retained but do not enter that edition's batch. Thus
COMMDLGS.HLP and HELPEX.HLP can remain on disk without blocking Turbo Pascal 7.
Required licence notices may also be selected; format detection does not turn
them into HELP bundles. Selected malformed/unsupported inputs still fail staging,
without replacing published HELP. Low-level single-file readers remain usable
for diagnostics. Special multi-file reader/bundle assembly rules remain separate
from this download selection; no parallel include/exclude list is needed.

### 1. Format Detection

When the converter loads a file, `exporter.py` builds its ordered format
registry from the manifest. Handlers combine extension, magic-byte and/or
structural checks. Representative checks are:

| Check | Format |
|-------|--------|
| `.txt` with `.topic` directives | FBHF source text |
| `.hl6` or recognized `.hlx` structure | HLX source or binary |
| `3F 5F 03 00` compound header | Windows HLP; article reader validates the HC31 SYSTEM/FONT profile |
| `.txt` with `@` title and `:` topic keys | HelpPC text database |
| `HHSTNDRD.ZIP` containing `help/index.htm` | FreeDOS HTML Help |
| `LN` + version word `0x0002` | Microsoft QuickHelp |
| `NG`/`EH` header or `.ng` | Norton Guide |
| `FBHF` magic | TurboVision FBHF binary |
| Exact `TURBO BASIC HELP FILE.` stamp and signature | Turbo Basic WORD-record binary |
| Other THELP signatures | Borland THELP binary |
| Opaque word followed by the validated English `Help text #0` screen record | Sidekick 1 screen stream |
| Opaque pairing word followed by `"Borland Help" 00 01` | Sidekick Plus paragraph directory |
| Big-endian delta map, sentinel and first-page padding structure | TDH/TFH runtime help (not THELP) |
| `\x1a(c) Software602 HelpSystem` | M602 binary |
| `\x0aK6HLP` with a complete 256-slot directory | Kartotéka 602 binary |
| `.hlp`, permitted text/control grammar and exact `.PA` page directives | MicroCalc text help |
| `.hlp` containing only validated `h("…")` clauses | Turbo Prolog help database |
| `.hlp`, meaningful multiline OEM text with TAB/CR/LF only | Uncompiled DOS text help |

Detection is deterministic — each file triggers exactly one reader.
Unknown formats raise `ValueError`.

Before these checks, `readers/source_containers.py` validates an optional DOS BACKUP
header and unwraps a complete single-volume payload in memory. Partial or
multi-volume backups fail rather than silently importing a fragment. The
embedded pathname is metadata, never a filesystem destination; original
bytes and manifest CRCs stay unchanged. See
[DOS BACKUP](../Formats/DOS%20BACKUP%20Source%20Container.md).

The final `.HLP` text checks reject NUL/unexplained control bytes, not merely
an unknown signature. MicroCalc retains its original `.PA` pages, five-space
margin and control-driven colors (byte `09` is reverse, not TAB). Ordinary
Prolog text is one topic per file; the separate `h("…")` grammar emits one
topic per record without evaluating code. A malformed clause database does
not fall back to plain text. Generated ordinal IDs/Contents/Index are
presentation choices, not claimed original format fields.

Sidekick 1 uses a distinct uncompressed screen stream: NUL ends a context,
while byte `03` advances pages within it. The reader retains source context
IDs and adds continuation-page IDs with local Prev/Next navigation. The
header's opaque pairing word is not a topic count or a version whitelist.
EOF is recognized only between contexts; an in-text `1A` remains an OEM
arrow. Native colors are executable/window settings, not HLP metadata. See
[Sidekick 1](../Formats/Borland%20Sidekick%201%20Help.md) for evidence and limits.

Sidekick Plus uses a different reader: paragraph-addressed group tables,
group-relative text offsets, separate caption strings and hotspot triples
scoped by page/group/context. It imports 1,165 distinct pages from the local
original, preserving 2,051 hotspots, a shared-record alias and three native
common-group redirects. Runtime verification confirms row-local category
resets, style toggles and that six missing source contexts also fail in native
Help. Original target identities remain intact; pairing tags are not detector
whitelists. A known runtime common-group binding can be supplied explicitly. See
[Sidekick Plus](../Formats/Borland%20Sidekick%20Plus%20Help.md) for the verified
structures and remaining runtime limits.

Game-Cheater's Pc-Fand tables use their signed header count, not a physical
slot-count fallback. Zero counts stay empty and partial/count-truncated
tables fail. Memo offset zero is absent; a nonzero invalid, truncated or
cyclic chain is an error, including a return to its first page. Present
index/memo sections require both members. Final memo pages can use all 512
bytes, while only continued pages reserve their pointer DWORD. Original
single/double frame glyphs remain unchanged; there is no table-appearance
rewrite. Failed staged jobs preserve published bundles and allow a retry.
The Nápověda bundle retains the embedded Pc-Fand records too: real links
cross their boundary, so excluding them loses destinations. Native name
lookup chooses the first physical mask match using Latin2 byte folding,
without nearest-title guesses or whitespace/Unicode-case expansion. Named
empty records become real source aliases to the following nonempty text in
links, Index and Contents; navigation skips those empty slots. The native
leading description line is hidden and F1's `root` is the Contents target.
See [Game-Cheater](../Formats/Game%20Cheater%20PC-Fand%20Format.md).

The TDH reader supports newer DOS/Windows/32-bit maps too: odd stored counts,
variable overlapping base WORDs, absent zero entries and a real cumulative-end
page. Authored references into the native preload's payload overlap retain
their identities; exactly equivalent overlapping pages become UHF aliases.
Older overlap ownership is tracked through complete consumed byte ranges,
including header bytes and literals crossing nibble/byte boundaries, not
through caption or substring matching. All 11 TD 1.0 aliases retain their
source owners. A context outside the consumed stream keeps its independent
text and is reported unresolved rather than redirected to similar prose.
All inspected TDH uses 48 visible cells and dictionary D/E NUL controls.
Original TD 1.0/1.5 routine execution verifies 19,027 rows across the older
corpus; those profiles fit hotspots without the later lookahead reservation.
Both 1.5 editions and 2.x include their real cumulative-end pages, including
2.x context 596 referenced by Hardware breakpoint. Zero-target carets retain
literal Pascal operators and consume their raw WORD. Older native hotspot
metadata has six stale spans after ordinary word wrapping. The shared decoder
now moves/splits label ranges with the wrapped cells, preserving the original
target on every visible fragment without caption/CRC heuristics. Native cells
remain unchanged; original stale spans are retained only as regression
evidence. Carried labels also obey the screen-row limit and never create
hotspots on undisplayed rows. The six 4.0/5.0 originals
yield 4,602 topics and 4,423 intact links. TFH 1.0/1.01 uses the separately
verified 48-cell runtime codec without TD 4/5's post-hotspot lookahead cell.
Labels can finish at column 48 before a page terminator or hard break.
Inside a label, NUL truncates the visible C string but not its encoded field;
the closing caret is mandatory even after hidden NUL/CR/LF bytes. Carried
labels retain subsequent hard breaks and links are clipped to visible cells.
The nonzero overlapping map slot enables
Profiler 1.01's real final page (367 contexts, 325 hotspots); a zero slot in
1.0 correctly disables that trailing page. Both TDH and TFH use one strict
block decoder: incomplete page headers, literal escapes, hotspot targets,
labels/trailers and unterminated displayed text fail conversion. Opaque slot
zero is not sent through text decoding. The native row cap, legitimate EOF
slots and unavailable tail bytes remain valid; there is no lax TDH fallback.
Real damaged-source tests exercise the staged server build: failure preserves
all published bundles/catalog, cleans only the disposable stage and permits
a successful retry after replacing the bad input. A stored-file checksum is
not part of this format, so arbitrary whole-file integrity needs a trusted
external digest. See
[TDH/TFH](../Formats/Borland%20TDH.md) for verified coverage and limits.

QuickHelp LN files can contain several concatenated databases. The reader
follows each database's size and relative offsets, includes all topics in the
existing physical-file bundle, retains first-database IDs and records logical
database names as catalog aliases. Single-file and tree exports both include
the appended content. See [Microsoft QuickHelp](../Formats/Microsoft%20QuickHelp.md).

The HelpPC matcher requires an `@` title followed by `:` topic keys, so
unrelated `.TXT` files are not treated as HelpPC. Its display rows now retain
the original 80-column centering, ordinary/highlight margins and output-column
TAB stops, verified by executing the original COM renderer. Shared UHF spans
preserve links and escaping; the existing fixed-width viewer needs no special
JS/CSS. Overlong centered sources fail, while ordinary text is not clipped.
The FreeDOS matcher requires
the `HHSTNDRD.ZIP` filename and `help/index.htm` archive member. FreeDOS HTML
flowing text preserves word boundaries across inline elements and empty
bookmarks. Collapsible spaces are deferred at their source style/link boundary
and discarded at a block boundary; NBSP/other Unicode spaces remain literal.
Preformatted rows remain intact. The importer uses two passes to map named/ID
bookmarks after display-line compaction, then
emit existing UHF topic/line targets for same-page, forward and cross-page
fragments. A bookmark without `href` is not a link. Topic IDs remain tied to
sorted member paths; originals are not extracted or rewritten. See the
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
| `uhf_markup.py` | Shared inline UHF text, link and style encoding |
| `text_screen.py` | Shared UHF bitmap font/TextScreen models and text projection |
| `bundle_types.py` | Reader/writer contracts for source groups and document variants |
| `../../help_database.py` | Shared JSON manifest loader, product grouping, CRC lookup, and validation |

Format-specific decoding belongs in `readers/`, including helpers shared by
multiple readers. The generic document, UHF/font models and encoding tools stay
at the converter root because readers, writers and server indexing use them.
Bundle provider dispatch belongs in `writers/bundle_extensions.py`; the shared
`bundle_types.py` contracts do not depend on that writer implementation.

### Readers (`thelpviewer/server/converter/readers/`)

| Helper module | Purpose |
| --- | --- |
| `software602_graphics.py` | Software602 native font cells and style selectors, shared by K602 and T602 readers |
| `tvision_help.py` | Bounded native THelpTopic fields and byte-based paragraph layout |
| `source_containers.py` | In-memory DOS BACKUP transport-header validation/unwrapping |
| `winhelp_binary.py` | Windows Help containers/B+ trees, LZ77/phrases and native article/target records; B+ trees are also used by HLX |
| `winhelp_text.py` | Bounded HC31 paragraph/table/font/hotspot commands and navigation macros |

`winhelp.py` is the reader adapter that projects these native structures into
the shared document model. `winhelp_binary.py` decodes their source bytes;
the separate names distinguish those responsibilities. Moving these modules
does not implement the deferred Windows graphics or alter source decoding.

THELP field readers use the current record's declared end, including counted
tables, NUL tag strings and used nibble operands. Incomplete known records,
unknown record headers and arbitrary nonpadding tails fail conversion rather
than returning partial HELP; verified all-space terminal padding remains
valid. Standard signature/version and compression selection are explicit;
unsupported codes do not silently use the latest known grammar. Validate
prefix-compressed index carryover, IndexTags byte lengths and context offsets
within the file (or the two native sentinels). A staged failure
preserves the published library/catalog and can be retried after source repair.

Format 4 uses the actual FileHeader payload size to select its five-byte or
nine-byte layout, just as 4/2 does. Turbo C 2.x's long header retains its
native 50×15 dimensions, Contents context 100 and genuine context-zero alias,
not an invented 80×100 geometry. All 66 installed THELP originals retain
93,032 topics, 85,484 index entries and 410,755 keyword targets. The bounded
header pass left source rows and keyword/index target identities unchanged.
Only six copies of those two long-header editions change metadata/aliases;
the other 60 complete models were identical before the separate text fix.

The nibble decoder now consumes both halves of the final Text byte, even
without an EOT. Its 93,142 physical text records match an independent C
reference using the archived `DEHELP.C` bit-fetch routines and a bounded
compression-event capture, projected to rows up to the logical EOT. This
restores endings in 3,001 records across 24 original copies, including the
last letter of positioned link labels. Treat zero-valued lookup entries as
line breaks, reserve lookup entry zero for NUL and reject undefined nested
repeat codes; operands still cannot cross the physical record boundary.
Context/page/keyword/index/tag identities and original files are unchanged.
This comparison does not emulate DEHELP's source formatter or the DOS GUI.

Native Turbo Example projection follows BOA's `05h` toggle rule byte by
byte, including inline and repeated delimiters. Preserve all source rows
and indentation instead of dropping marker-only rows or stripping leading
spaces. `03h`/`10h` are not code toggles: retain their OEM glyphs, including
the Czech Pascal menu arrow. Carry example state along reciprocal native
page links and aliases, independently of physical record order; do not
guess an entry state for cycles or unrelated/missing links. Explicit markers
take precedence over the existing optional Example/Pascal-filename display
heuristics. The shared model currently marks code at whole-row granularity,
so mixed normal/example text within one row is not a per-cell attribute
emulation.

For the verified Pascal 7 `(52, 2)` text profile, `14h` substitutes the
consumer's product name rather than marking emphasis. Use `Borland` when
the native IndexTags description identifies Borland Pascal; otherwise use
the verified Turbo viewer default. Do not infer a different name from a
directory, filename or heuristic title. Remove the entire placeholder body,
including padding and any embedded controls/row boundaries, before computing
example state or rendering hotspots. Reset suppression at each physical
Text record. Private token runs retain the original compression order where
substitution precedes RLE emission and preserves a suppressed repeat count;
they do not replace the lossless parser's source rows. Other text profiles
retain unverified `14h` glyphs. The shared projection matches both original
Turbo/Borland routines on all 791 installed placeholder records; untagged
files cannot identify which alternate application originally opened them.

Sequential THELP profiles (5/51/52) use one native byte-word formatter before
example projection and UHF link rendering. Fixed rows start with a literal
space or are empty; other rows can join across source returns. Keep complete
space runs, make each `02h` label atomic and leave oversized words/fixed rows
available for horizontal scrolling. Table cells follow this same algorithm:
there is no border-derived column count or UHF-string table reconstruction.
Retain every sequential target and keep display coordinates separate from
source context identities. Legacy positioned profiles keep their authored
rows and coordinates unchanged.

UHF output is a fixed-row projection: use the smaller of the ordinary DOS
76-cell flowing viewport and the positive FileHeader Width minus LeftMargin.
Keep the original FileHeader geometry as source metadata; this projection
does not implement browser-resize reflow or combine published page IDs into
one topic. Native page identities/navigation and example state still remain
separate from physical file order. The binary parser retains lossless source
rows and bytes so subsequent layouts can start from the source. The formatter
matches bounded original Pascal 7 instructions; safe Python buffers preserve
longer text rather than reproducing native temporary-buffer overflow.

THELP context resolution uses actual Text-record addresses and genuine aliases,
including header-bound Contents aliases under the BOA model. Primary IDs and
aliases come from the same offset map; a shared Contents record no longer
loses its binding when an earlier context also addresses it. Preserve original
Keyword/index IDs. Do not turn a unique referring row or a matching human
label into a destination: the previous guessed fallback/hidden-anchor code
has been removed along with its duplicate UHF renderer.

For Pascal 4 profile 2/1, the native consumer's default index context is 100:
all `FFFFFFh` slots address that record when it actually exists. Retain these
aliases, including context 0, without changing original table bytes.
The browser's shared alias lookup retains numeric zero as a real alias;
an actual topic 0 takes precedence when both are declared. Other
legacy/short headers with no verified consumer binding use an unknown value,
not an invented context-zero Contents. Long headers keep their stored context,
and both keyword layouts mark its Text record consistently. A missing default
body is not replaced with the first visible topic.

Sidekick 2's `KATO HELP FILE.` uses a long 4/2 header with stored context
0, a No Help slot and an empty native index; it is not a short-header variant.
The original application chooses different Contents roots for its tools.
For the standalone viewer, its no-application Contents/General root 101 is
registered through the existing CRC-backed catalog override. The parser
retains the actual header value, sentinel offsets and all source records;
neither its failure-default Address Book context 100 nor its invalid slots
are turned into global Contents aliases. Keep the generated alphabetical
index and ordinary source links. A verified byte-identical distribution
adds retrieval provenance without creating a duplicate edition; its canonical
path stays `Borland Sidekick 2/`, while the catalog release is 2.0.

The shared viewer's default order is a verified Contents topic, an available
alphabetical index, a reader-supplied Contents tree, then the first available
topic. An explicit Index request on a file without index entries also prefers
that existing tree over an arbitrary topic. Delegated opens add one history
entry, not a second entry or an empty index window. This is a generic UHF
view-selection rule, not a Sidekick-only renderer or filename switch.

Map native UpContext/DownContext page words to previous/next navigation.
Normalize their terminal zero to no link; expose only existing directions in
Up/Down and Prev/Next items. Preserve genuine target/context-zero identities
in other fields. Positioned keyword direction bytes remain lossless hotspot
selection indices, not topic-level navigation; no Prev/Next destinations are
derived from them. Physical record order is not a page-chain substitute.

Missing native references remain clickable UHF links and index entries,
declared through the shared `unresolved_contexts` metadata. Classify referenced
padding, explicit no-help offsets, unbound Contents and out-of-namespace IDs;
retain their original offsets where available. Genuine aliases are not missing.
Terminal padding is the parser-validated suffix, not any 64-space body fragment.
The generic JSON writer preserves reader-declared missing index targets instead
of redirecting them by label. Opening an unavailable topic uses the existing
MessageBox, records a broken link and leaves the current help page unchanged;
its public URL still retains the actual numeric/string target. Native aliases
continue to resolve to their canonical topic. This does not reconstruct missing
source text or emulate every consumer's sentinel/default policy.

K602 and legacy T602 3.00 T6HLP use `readers/software602_graphics.py` for their
verified common glyph/category semantics. T6HLP keeps native byte-context IDs
0–255, authored title/block art and blank rows; no aliases retain the former
one-based IDs. Both use a fixed 70-cell shared viewer with horizontal overflow.
Unrepresented font-size selectors fail explicitly and untranscribed compound
glyphs occupy visible replacement cells. The later Text602/Calc602 encoded
THelpTopic format uses the same high screen glyphs, but does not interpret
graphics-editor style/size selectors in paragraph text.

Text602 3.10/Calc602 store standard Turbo Vision THelpTopic fields with
paragraph text encoded byte+1. `0Eh` is encoded CR, not a binary delimiter;
three-byte length/Wrap fields are not inline display controls. The same
bounded field reader now serves FBHF and Software602. Native GetLine/GetCrossRef
execution verifies all 12,207 rows and 2,235 references at 78 columns. Links
use one-based START positions across the concatenated text and balanced
shared UHF spans, not caption matching, tolerance or label-length guesses.
Preserve titles, authored rules/gaps, fixed rows, wrapping and non-breaking
spaces. Counts, sizes, flags, references and exact object starts are checked
before publication; absent link contexts fail explicitly without erasing links.

Read all physical objects through the index: Text602 has 188, Calc602 275
(including 122 errors). Embedded keyboard sections remain inside their true
owner instead of becoming invented topics. The EOF arrays have 360/280
slots. UHF topic IDs use the first native context for each indexed object;
genuine shared slots become aliases (64/150, 107/143, 120/151 in Text602 and
52/53 in Calc602). No aliases preserve old sequential IDs. Unindexed objects
use `65536 + source_offset`, a namespace disjoint from native WORD contexts;
Text602's unindexed `Blok │ Řádkování` at 55003 is retained as topic 120539.
UHF stores the verified 78-column projection with the shared window/scrollbars;
adaptive paragraph reflow is not yet represented in UHF. The original HELP
screen-driver fonts verify all observed glyphs, including Calc602's complete
Czech/Slovak/Greek/math keyboard charts. Reuse the common high-byte font table
without row-content mode guessing or Kamenicky fallback. Low cells are literal,
not inline style selectors; untranscribed compound/revision-dependent icons
occupy replacement cells. FFh is normalized to a readable space only after
wrapping and reference positioning, not to its native driver's marker stroke.
Pure 76/77-cell 98h authored rules retain the existing UHF rule projection;
other 98h/97h/96h cells keep their upper/lower/full block shapes. Metadata
identifies this encoding as `software602-plus1`, not `kamenicky`.

M602 binary conversion reads its native context/offset/size directory and
six-byte EOF footer. Every topic range and inline link is bounded; damaged
data fails staged publication rather than falling back to caption matching.
Physical ranges retain the existing sequential UHF topic IDs; genuine inline
targets are resolved through the directory, including the first error context
and the original native 9999 fallback. Hotspot padding retains its cell width.
Source-only M602 HLX still has a separate label-based recovery path when no
companion binary exists; that is not the binary-format decoding algorithm.
M602 display projection now uses its native raw-byte row assembly at a
standard 78-cell DOS client width. Restore the leading hard-row space and
authored title/underline blocks; join soft records with one space and keep
the native cut spaces. Wrapping counts original delimiters/operand bytes
before their removal, so label underscores do not become premature breaks.
Use common positioned hotspots and UHF rendering after layout; adjacent
equal targets remain separate. If an unusual cut crosses a source label,
carry its verified target to each visible fragment without reproducing the
native out-of-string scan. Wider buffers retain source beyond the original
255-byte concatenation limit. Empty topics remain valid; zero-length records,
missing CR suffixes and incomplete operands fail rather than reading adjacent
memory. Consume exactly one CR suffix; internal CR/NUL/TAB remain literal
OEM cells. All indexed topic IDs, labels and directory destinations are
unchanged. The published projection is fixed-width, not browser-resize reflow.

Compiled Borland Windows `.HLX` is a separate keyword B+ tree, not an article
stream or semicolon-directive source. The reader traverses declared pages,
validates used-space/record boundaries and preserves all keyword labels,
counts and offsets into the companion HLP keyword-data stream. UHF exports
are explicitly `compiled-index` when converted on their own: one keyword per projection page and the
complete native fields under `hlx_keyword_records` / `hlx_header` metadata.
Projection page IDs are keyword ordinals, not native article contexts.
No printable-string grouping, guessed pointer table, free-space RTF path,
nearest-address hotspot or numeric-offset Prev/Next chain is retained.
The English Windows trees use cp1252; shared cp125x decoding keeps C0 bytes
as controls instead of OEM glyphs. Matching original HLPs are now retained
and CRC-registered: the 20 indexes are from 4.52, not an assumed 4.5 revision.
BCW and OWL's distinct 4.5 pairs are retained separately.
`tools/hlx_probe.py <file-or-directory> --details` lists the native tree records.

The shared `winhelp.py` backend reads bounded internal allocations, directory
trees, SYSTEM records, LZ77 blocks, old-style phrases and linked article
headers. Native TOPICPOS uses the verified HC31 16-KiB logical stride even
for plain blocks; TOPICOFFSET uses a separate 32-KiB character/hotspot space.
Resolve keyword addresses only inside declared display-record spans, and
verify an external HLX against the HLP's embedded keyword tuples before
binding it. All 279,497 records of the 20 4.52 HLPs match an independent
HelpDeco C decoder byte for byte; all 29,064 keyword references resolve to
native articles. Two distinct 4.5 HLPs have independent fixtures too.
The registered `readers/winhelp.py` reader converts the verified HC31 profile
(Minor 21, flags 0/4 and old FONT descriptors) into shared UHF articles. It
consumes each conditional operand and each interleaved NUL text string inside
its record boundary, not printable runs. Native TopicNum is the article ID;
context hashes have their own `winhelp-hash:xxxxxxxx` identity. Keywords,
Contents and browse links resolve through actual bounded record/cursor spans.
The old keyword-ordinal projection is not an article-ID compatibility layer.

Text layout uses an 80-cell viewport and 12 old half-points per character:
authored indent/tab positions, left/right/center tabs, hard line breaks,
table column ratios and horizontal paragraph rules. Preserve bold, italic,
underline and Standard Symbol glyph transcription through common markup;
native non-scrolling headings use the existing frozen-row support. A paired
HLP is `compiled`, its HLX is `index`: tree and server builds select the HLP
instead of generating two competing same-stem bundles. A standalone HLX
still exports only its proven index data.

This is **fixed-cell text projection**, not Windows pixel/font emulation.
Proportional typeface sizing, native RGB colors, vertical spacing units,
vertical/double/thick borders and bitmap/metafile pixels are not reproduced.
Font fields remain in `winhelp_fonts`; picture operands and placement remain
in `winhelp_objects`, with visible `▧` placeholders. Undefined Symbol bytes
are explicit replacement glyphs listed in `winhelp_unmapped_glyphs`.
`JumpID`/`JI`, `JumpContents` and the source-authored no-mark branch of
`IfThenElse(IsMark(...),...)` provide navigation, without native mark state.
Other macros retain unavailable `winhelp-macro:<hex>` link targets and their
source in `winhelp_macros`; no Windows command or host-language code executes.
Graphics, image-region links and related image behavior are deferred work;
the picture placeholder is not a claim of rendered bitmap/metafile support.
Secondary-window/popup presentation also remains a limitation,
while native external filenames/hashes are retained. A target at a NUL or an
unrendered hotspot maps to that record's start line, not a guessed article.
Source context aliases retain an optional destination row through shared
`aliases.lines`. Local, external and public-URL jumps resolve both the article
and that row; an explicitly supplied line takes precedence. Alias destinations
do not become duplicate articles or search/sitemap entries.
HC30 addressing, Hall phrases and extended FONT profiles fail explicitly.
See [Windows Help](../Formats/Windows%20Help.md) for source-format byte fields.

| Reader | Format | Signature | Binary/Text |
|--------|--------|-----------|-------------|
| `thelp.py` | Borland THELP (TP4–7, TC, TASM, Sidekick 2) | `$*$* &&&&$*$` | Binary |
| `turbo_basic.py` | Turbo Basic compiler/editor screens | Exact TBH stamp, WORD records and FE-space packing | Binary |
| `fbhf.py` | TurboVision FBHF (TP6, TP7, BP7) | `FBHF` magic | Binary |
| `ng.py` | Norton Guide / Expert Help | `NG` / `EH` | Binary, XOR `1Ah` records |
| `m602.py` | Software602 M602 HelpSystem | `\x1a(c) Software602 HelpSystem` | Binary (XOR $FA encrypted) |
| `k602.py` | Kartotéka 602 | `\x0aK6HLP` | Binary, fixed 256-slot directory |
| `hlx.py` | HLX/HL6 decompiled source text | `;SCREEN`/`;PAGE` directives | Text |
| `winhelp.py` | Windows HC31 articles, tables, fonts and links | `3F 5F 03 00` container, verified SYSTEM/FONT profile | Binary |
| `hlx_binary.py` | Borland Windows keyword B+ tree | `3B 29` and `i24` descriptor | Binary index, not article text |
| `fbhf.py` | TVHC-compatible `.txt` source | `.topic` directives | Text |
| `helppc.py` | HelpPC 2.10 text databases | `@` title and `:` topic keys | Text |
| `freedos_html.py` | FreeDOS HTML Help | `HHSTNDRD.ZIP` with `help/index.htm` | ZIP of HTML text |
| `dos_text.py` | MicroCalc, uncompiled DOS `.HLP`, Prolog help clauses | Strict byte/record grammar, `.PA` or `h("…")` where applicable | Text |
| `sidekick1.py` | Sidekick 1 screen contexts/pages | Context-zero structure after opaque pairing word | Binary/text stream |
| `sidekick_plus.py` | Sidekick Plus screen groups/pages | Pairing word + `"Borland Help" 00 01` | Binary/text stream |
| `game_cheater.py` + `game_cheater_bundle.py` | Game-Cheater 9.02 Pc-Fand database, split into cheats, companies, internet addresses, help and information bundles | `CHEATDBS.000`, 111-byte records | Binary |
| `scorpion_dat_reader.py` | Scorpion's Cheater DAT 15-23 | Allegro DAT signature | Binary |
| `scorpion_legacy_reader.py` + `_v1x/_v3x/_v4x` | Scorpion's Cheater legacy families 1-14 | version-aware path + extension hints | Binary |

Each reader implements `read_bytes(data: bytes) → HelpDocument`.

Modern Scorpion DAT conversion validates every Allegro object before article
filtering. A compressed chunk must supply its declared decoded length, and
uncompressed stored/decoded sizes must agree, including empty objects.
The shared Allegro parser has no lenient placeholder mode or compressed-byte
fallback. A recognized but damaged DAT raises during source selection rather
than disappearing from the selected product; a failed server build preserves
the live bundles and catalog. The v21 TEXTY `txt` catalog is converted by
`scorpion_sc2000.py` inside this reader: one catalog article, title Index and
Contents entries with original row cursors, CHEATY-scoped marker links and
exact local title references. Duplicate labels retain distinct cursors;
library/member descriptors stay literal without invented attachment paths.
Its four angle-bracket prose objects still need the original SC 2000 font
and pixel-pagination bindings. Their names appear in
`scorpion_unconverted_record_names`, not the font/screen resource inventory.
Their grammar takes precedence over apparent DOS `[Rnnn]` markers in the
prose, so quoted markers cannot accidentally publish guessed DOS articles.
Allegro extraction retains their complete declared bytes, including an
in-word `FEh` in `spoluaut`; its text-end and encoding rules are not guessed
from the catalog or ordinary DOS articles.
Resource-only containers remain excluded. The installed 26 modern containers
and all 579 DATA objects satisfy the length rules; the 15,144 DOS article
projections are unchanged.

Modern `PROGRAM.DAT` also exports its 48 verified 80×25 screens using
`scorpion_screens.py`: native glyph/attribute cells, shared Base64 `FONT1`
and CGA palette indexes in UHF `TextScreen` resources, never PNGs. Version 15
has the same font/screen data under positional `obr*` names. Resource topics
are appended after native articles, preserving existing IDs and text, and
Contents groups them under `Obrazovky programu`. The literal row transcription
is searchable; it does not replace the source font during drawing. These are
stored screen templates with source text, not reconstructed live menus or
guessed links to nearby articles. Per-topic legacy HTML retains the literal
transcription; native-font rendering is provided by the UHF bundle viewer.
Legacy v6–v14 PROGRAM bundles also carry 56 verified text
screens, seven native fonts per release, and in-place inline block/box-art
rows. The default is FA.SCO for v6–v8 and FONT.SCO record 1 for v10–v14.
The shared `scorpion_lzhuf.py` decoder handles both text and binary resources;
it updates Huffman leaf zero and bounds consumed bits by real input bytes.
Seven FONT.SCO outputs and all 56 legacy stored screen outputs match hashes
obtained independently from the original DOS decoder. Three v6 templates
with attribute bit 7 use explicit `dos-text-blink` under the standard
blink-enabled DOS presentation profile. They follow existing static templates
without shifting published article/resource IDs. Their source files carry
no video-mode flag: the selected UHF packed format records the interpretation,
not a bit-masking or caption-based guess. UHF separately supports
`dos-text-bright` for source profiles with blinking disabled. Indexed SCX
palettes remain deferred.
Inline PROGRAM rows containing native block/box/custom artwork use the same
embedded default font, retain their original article position, and keep a
literal search transcription. Ordinary prose and links remain ordinary UHF
lines. There is no invented association between an article and a separate
screen resource, no external image and no new HELP window type. v4/v5 PROGRAM
also uses its verified default FA.SCO font for eight inline-art rows each.
The shared text-screen view owns blink animation, leaves cell backgrounds
unchanged, honors reduced motion and releases animation/listeners when its
topic or window is removed. Readable and independent three-byte packed cells
may carry an explicit boolean blink mask; DOS packed forms retain the
original flags directly in their two-byte character/attribute cells.
The modern screen converter emits byte-exact Base64 `dos-text` blocks;
the general UHF model also supports readable triples and Base64
`glyph-fg-bg` cells. Original attributes are not converted to RGB or stripped.

Norton Guide uses the same source-name/encoding/source-path constructor and
inherited `read_path()` as other binary readers. Construction does not open
the source; `read_bytes()` parses the supplied header and records on every
call. The manifest no longer uses path initialization that reopened the file
and bypassed DOS BACKUP unwrapping. NG/EH validation bounds every physical
record, MENU/SHORT/see-also table and declared NUL string, then checks all
raw pointers against exact record starts. Only LONG `Next` may use exact EOF
as a terminal value. Do not scan for a replacement root or drop bad links.
Empty records, shared/unsorted SHORT strings, cycles and opaque record padding
remain valid. Staged failure preserves published bundles/catalog and permits
retry after source repair. Structural validation alone preserved the complete
normalized models of all 58 originals; subsequent native rendering validation
corrects their text/categories and SHORT ranges without changing record IDs
or target identities.

NG body text now uses one byte-cell decoder for raw rows and shared UHF
spans. Bounded execution of original NG 1.00/1.02/1.04 verifies category
replacement and attribute-equality toggling, unknown-escape/OEM uppercase
behavior, literal video glyphs and unsigned space runs. All 509,785 installed
body rows match the 78-cell native viewport; original-loop captures before
the video sink also verify longer logical tails. UHF retains those tails
instead of silently clipping source text. Low CP437 bytes are glyphs, not
browser controls. Incomplete numeric escapes cannot read another string;
their bounded terminator result retains its cell rather than losing text.
One SHORT destination covers its entire row, including padding/descriptions;
the former first-padding boundary and zero-width visible-label guess are gone.
The 21,309 records and all 36,265 positioned target identities remain intact.
Normal/bold/reverse/underline categories continue using shared viewer styles,
while other attribute bytes retain explicit UHF colors; this is not an exact
emulation of native theme settings, hardware blink or monochrome underline.
MENU caption offsets now use the original payload-relative eight-byte
descriptor table and its header offset rather than assumed sequential text.
Keep shared/unsorted captions, blank/symbol-only slots and every stored target;
do not invent child-based labels. MENU/see-also captions preserve raw OEM
cells, whitespace and literal carets; FFh is not body RLE in these strings.
Native relocation/plain-output routines verify all 120 menus and 14,551
captions (111,967 cells). See-also captions without a target remain visible
and empty target captions retain positioned metadata. Shared UHF renders
captions inside ordinary topics, not the native popup/check/rule/shortcut
chrome. Rare plain-caption terminal cursor controls are not projected as
original screen movement; none occur in the installed caption corpus.
Expert Help-only extensions still need independent native verification. See the
[NG datasheet](../Formats/Norton%20Guide.md).

K602 reads its complete native 256-slot directory at `000Fh`, with application
context `C` selecting the descriptor at `0Fh + 6*C`. Zero-offset slots are
unavailable regardless of their unused size WORD. Empty/shared topics and
unsorted physical offsets remain valid; incomplete tables, out-of-file ranges
and rows extending beyond their own topic fail before publication. Its former
IDs were incorrectly 16 lower than the original context; no compatibility
aliases are emitted. The native IDs, including zero if populated, remain the
published UHF topic IDs. K602 uses its built-in graphics-font transcription,
not Kamenicky: 96h/97h/98h remain visible `█`/`▄`/`▀`, and FEh renders a shortcut
dash. Each stored row remains one UHF row; 8Dh is blank and 0Ah is the corner
glyph `╯`, not a newline. Native bold/italic/underline categories use the shared
UHF style renderer, with row-local switch/reset behavior. `display_width=70`
selects the common fixed-cell viewer and horizontal scrolling for longer rows.
It represents the native maximum viewport, not per-topic dynamic sizing or a
width field stored in the HLP. Compound boxed-key glyphs without a chosen
Unicode form become one visible replacement cell; they do not disappear.
Double-width and five-row super/subscript selectors fail explicitly until
those font-size effects can be represented. Neither limitation occurs in the
inspected HLP. No custom fonts, extra JS/CSS or specialised viewer is added.
See the [K602 datasheet](../Formats/Software602%20K602.md) for stored structures,
the built-in character table and source/runtime rules.

QuickHelp validates database-local sections, indexes and every decompression
stage. A malformed topic raises `ValueError` identifying its logical database
and local topic number; it is not exported as an empty page. Huffman symbols
are read on demand until expansion reaches exactly OUTLEN, so unused padding
does not become binary data. FBHF validates stream-object types and bounded
paragraph/reference records, including empty, sparse and shared-position
indexes. TVHC numeric aliases use shared `TopicRecord.alias_contexts`; names
resolve to the owning topic and multiline fragments retain their target.
FBHF binary and TVHC source share the native byte-based `paragraph_lines`
layout at the standard Pascal viewer's initial width of 46 columns. Empty
paragraphs produce no rows; actual CRs preserve blank lines without an extra
terminal row. Fixed rows retain their spacing and are not synthetically
indented. Word wrapping precedes FF-to-space normalization. Global references
become `PositionedKeyword` ranges on those rows, including separate clickable
fragments if an exceptional range crosses a wrap/CR/paragraph boundary; no
02h markers are inserted into source text. The exported display width is 46.
UHF currently freezes this projection: native adaptive paragraph reflow on
window resizing is not represented. The two external DEMOHELP reference
files are validation inputs, not newly installed catalog products.
TVHC source detection requires the first nonblank/noncomment physical line
to be a case-insensitive `.topic` command, respects the standalone DOS EOF
line and scans past long comment preambles. Embedded command examples do
not override another source format. An explicit reader can also read empty
comment-only sources; automatic empty-source detection uses the decompiler
banner. Header tokenization, predefined contexts and
ASCII-only name matching follow TVHC; duplicate names fail with a source
line diagnostic. Reused numeric contexts follow the native last-position
index rule without losing surviving aliases or redirecting symbolic names
to obsolete objects. The brace scanner preserves literal escaped braces
and rejects unfinished references rather than converting partial source to
plain text. Native line/paragraph/signed-field limits are checked before
publication. Unresolved symbols retain positioned `FFFFh` targets and the
exported `unresolved_topic_names` diagnostics, once per folded name. Standard
writers retain their text and emit a link only when the resulting numeric
context exists; no destination is guessed. Staged builds preserve published
HELP/catalog when source validation fails and can be retried after repair.
BW03 reads the fixed menu/style-table starts and only the active descriptors,
following their stored Next/Prev indices. NUL termination and literal RLE cells
follow the original CodeView screen routine. The separately encoded unindexed
command summary is exported as additional Contents/Index topics; form-feed
pages receive generated IDs after the indexed screens and shared page
navigation. These IDs/titles are converter presentation, not stored fields.
Staged server builds refuse failed conversions and keep the published library
and catalog intact; the same job can be retried after correcting its input.

### Writers (`thelpviewer/server/converter/writers/`)

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

Tree exports preserve subdirectory structure from `var/sources/`. Bundle tree
exports also generate `catalog.json` in the selected output directory. Server
builds publish it at `data/helps/catalog.json`, served as `/helps/catalog.json`.

The Help Files menu uses `product_name` as its family level and `version` as
the release level. A product's version-free `menu_label` in
`help-database.json` can be shared across releases even when their download
labels and physical source directories differ. For example, QuickBASIC 4.5
and QuickBASIC Extended 7.1 both appear under `Microsoft QuickBASIC`, then
under separate `4.5` and `7.1` entries. The catalog `file` path stays tied to
the existing bundle location, not to the menu labels.
Single-file editions open directly from their version item instead of adding
a one-file submenu. If the whole product contains only one file, its Help
Files item opens that file directly and shows the product plus its version.
Versions still come from the manifest/catalog, not product-specific JS rules;
an unknown version is not invented.

Known files are deduplicated by CRC32. Product-level conversion rules cover
corpora where a release consists of several related files without stable CRCs.
For example, Game-Cheater's manifest bundles pair `.000` indexes with `.T00`
texts, while Scorpion's manifest selects its version-dependent data files and
lets the version readers assemble related sections.

## Supported Formats

See Formats for detailed binary format documentation:

- [Borland THELP](../Formats/Borland%20THELP.md) — TP4–7, BP7, Turbo C, TASM, Sidekick 2, Sprint
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
