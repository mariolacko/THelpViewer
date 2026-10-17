# Windows Help RE Notes

Private decoding and source-acquisition evidence, not the public binary
datasheet. HC31 fixed-cell text projection is registered; it is not full
Windows proportional-font/picture emulation.

## Original media and revision matching (2026-10-12)

Downloaded three WinWorld distributions into `var/downloads/help/`, using
the existing downloader transport. Their archive SHA-512s agree with the
provider's published checksums:

| Distribution | Cached archive bytes | WinWorld selector |
| --- | ---: | --- |
| Borland C++ 4.0 (CD) | 77,936,029 | `445f58c3-ba4f-6c11-c3a5-c28fc2a3c388` |
| Borland C++ 4.5 (CD) | 88,306,034 | `c2a44ac3-a459-4f66-11c3-a5c28fc2a3ef` |
| Borland C++ 4.52 | 99,042,845 | `45c2b512-c382-18c3-9a11-c3a4e284a2ef` |

The first is a research input, not another installed catalog edition.
The 4.52 ISO reproduces all 20 existing 4.x HLX files exactly. Eighteen
indexes also match 4.5; BCW/OWL do not. Permanent source acquisition keeps
20 matching HLPs under `var/sources/Borland C++ 4.x/`, and the four distinct
4.5 BCW/OWL HLP/HLX files under `var/sources/Borland C++ 4.5/`. The original
20 indexes remain byte-identical. Manifest release metadata now identifies
them as 4.52; this does not rename their physical collection or bundle URLs.

Every new CRC entry retains shared edition/provider provenance so the
downloader deduplicates jobs, not sources. WinWorld uses pinned selectors
and exact CD member paths. Archive.org's discovery query returns a 4.52
ISO and a separate 4.5 floppy set; those alternative payloads have **not**
been independently downloaded/compared. Its 4.5 members therefore use exact
basenames rather than assuming a CD directory prefix. Discovery is not
checksum proof. Wrong source revisions cannot be bound merely by filename:
compare the live external and embedded keyword key/count/offset tuples.

The acquisition pipeline previously discarded any HLP beginning with
`3F 5F 03 00`. That filter is removed from archive collection and direct
Archive.org downloads. Collection no longer asserts converter support.
Copying a distinct original over an existing destination now fails, while
an exact duplicate is skipped. Shared configured member selection matches
complete directory components through nested extraction prefixes and still
rejects ambiguous matches. A test runs the actual cached 4.52 CD through
the WinWorld provider/extractor and verifies all 40 selected files against
the retained originals and their embedded keyword trees.

## Independent decoded record evidence

Research directory: `/tmp/thelp-winhelp.UHDcOY/`.
Reference implementation: HelpDeco revision
`785273788af17fde4fba7df7162d547f8645d7d8` from
[the upstream source](https://github.com/pmachapman/helpdeco).
A temporary C harness invokes its existing `SysLoad`, `PhraseLoad`,
`SearchFile`, `TopicRead` and `TopicPhraseRead` routines. It does not invoke
the Python parser or generated UHF. No upstream implementation is copied
into the application or executed by the ordinary regression suite.

The shared Python backend matches the C output on **every record** in the
20 matching HLPs: 279,497 records, 29,756 article headers and 36,358,369
decoded Data1/Data2 bytes. It separately groups native type-2 articles,
checks their NextTopic chain and resolves all 29,064 references from 18,975
keyword records inside declared native display spans. Two distinct 4.5
HLPs have the same independent verification. This establishes payload and
address decoding, not native visual rendering or macro execution.

`tests/golden/winhelp/borland452.json` and `borland45.json` pin original
SHA-256/CRC32, native titles, media members, SYSTEM flags and record counts.
Their independent record digest is SHA-256 over ordered records, each:

```text
LE32 position, LE32 previous, LE32 following, byte type,
LE32 Data1 length, LE32 Data2 length, Data1 bytes, Data2 bytes
```

The HC31 reference uses a 16-KiB logical TOPICPOS stride even for flag-0
plain physical blocks. Using the plain payload size as stride decodes some
first-block samples but fails later pointers. Records can cross physical
blocks; continuing skips the block header and the unused logical gap.
The record header is 21 bytes, despite an inconsistent `DataLen1 - 11`
formula in old prose. Native HC31 zero-fill explains underfilled phrase
buffers in WIN31WH; a title's declared buffer end can replace a stored NUL.
These are general structural rules, not specimen-name branches.

## HC31 text projection

`converter/readers/winhelp_text.py` parses complete bounded Data1/Data2 command streams:
conditional paragraph fields, tabs, table cells, old 11-byte FONT descriptors,
hotspots and size-delimited object/macro operands. Every one of the 295,218
display/table records across both editions consumes its formatting bytes
exactly; remaining phrase-expanded text may contain only zero padding.
The native HelpDeco `-d '|TOPIC'` output independently matches TopicSize,
TopicLength, table type/minimum and every column pair for all 22 originals.
`tests/golden/winhelp/display_fields.json` freezes count/SHA-256 over compact
JSON arrays `[unsigned TopicSize, TopicLength, TableType-or-null,
MinWidth-or-null, [[ColWidth, GapWidth], ...]]` in native record order.
The native dumper/RTF writer and Wine's single-cell boundaries establish
width-then-gap order, despite reversed fields in older prose. A table record
emits one row; a repeated column is another paragraph in that cell, not an
inferred row. Examples include WIN32's Style/Meaning row with `(265, 0)`
and `(431, 0)`, and WIN31WH's three columns `(278, 18)`, `(286, 18)`, `(287, 18)`.

Signed wide packed longs subtract `40000000h`, not the old prose's
`04000000h`. The former is independently implemented by HelpDeco scanlong
and Wine and required by OWL embedded pictures. Macro payload Length includes
all following bytes. HC31 E2/E3/E6/E7 operands are context hashes; external
subtype 6 stores window name before filename. These structural corrections
are not source-name hacks.

The registered reader uses actual native TopicNum IDs and real hash aliases.
It projects native metrics/tabs/table ratios to 80 fixed cells through the
standard UHF markup, keeping font style/Symbol text, native browse links,
non-scrolling headings and exact external filenames. Two layout passes retain
only requested cursor anchors between articles, not every character origin
for the whole manual. Deterministic JumpID/JumpContents navigation is parsed
without executing host code; unknown native actions retain their source and
unavailable aliases, not fabricated destinations.

WIN31WH keyword ordinal 52 previously showed only `\fonttbl RTF statement`.
The actual KWDATA value 19,303,714 selects native article 2,559 at record
9,654,734, character 0. Its complete text now includes RTF syntax, native
parameter/value tabs, Comments and links to articles 2552/2556/2561/2572.
No keyword-ordinal-to-article compatibility alias is retained: numeric article
52 is a different real article. HLP takes precedence over same-stem HLX in
normal tree/server builds; standalone HLX conversion remains explicitly index-only.

## Remaining work

- Bitmap/metafile pixels, SHG/MRB image-region links and native embedded controls
  are not rendered. Picture payloads/placement remain transport metadata with
  a visible `▧` placeholder, not guessed OCR or discarded source bytes.
- Exact proportional font/RGB/vertical metrics and thick/double/vertical borders
  are not reproduced. Old FONT descriptors are retained as metadata.
- Complete Windows macro/UI, secondary-window and popup presentation are not
  implemented. Source CWH contains 40 distinct unsupported macros; WIN31WH has
  one CloseWindow macro and two uses of unassigned Symbol byte 94h.
- Independently verify Hall compression, HC30 and other observed variants
  before registering them as supported conversions.

The public [Windows Help datasheet](Windows%20Help.md) contains byte fields,
algorithms, boundaries and explicitly unknown grammar, not these work notes.

## Initial packet/index-only verification and publication

The real-CD targeted run passed 169 cases; after adding destination-symlink
protection and the two 4.5 bundle cases, the parser/downloader/export set
passes all 172 cases. The actual Docker Python 3.12 decoder independently
matches the frozen record digests for all 22 retained HLPs: 334,253 records
and 39,035 native article headers across both editions.

The staged product-`bc` build retains all 251 existing bundle paths and adds
only `Borland C++ 4.5/bcw.json.gz` and `owl.json.gz`. All unselected bundle
bytes remain identical. Existing C++ normalized payloads are unchanged,
apart from converter timestamps and the 20 verified release metadata values
moving from `4.x` to `4.52`; keyword content/index/native fields are intact.
Recoverable publication backup:
`data/.helps-previous-3f3468360d444a2c814cc5e47553806a/`.
The standard documentation publisher preserves local edits and excludes RE
notes. Actual local HTTP serves the new datasheet and both 4.5 indexes.
Local Docker's global index is ready with 157,563 topic rows, 36 indexed
documents and no warnings; its public Docs catalog has 38 entries.

The initial full regression run has 1,824 passes, one Safari skip and two
failures in DOS Prompt's real-browser close test, not the format tests.
Temporary capture of actual mouse targets proves that all three mouse
events hit `tv-index-progress-overlay is-modal`, not the close button.
Each DOS test had been rebuilding the whole developer HELP library and
then programmatically interacting through that modal progress overlay.
This explains the earlier timing-dependent retries without inventing a
frame/close implementation defect.

The DOS fixture now has its own empty HELP/Docs tree and an explicitly
configured test server. First-run setup and global indexing retain their
separate tests; no modal is disabled in application code and no close
assertion is removed. Both uninstrumented real-WASM browser variants pass
after isolation (53.55 seconds). The complete suite had not yet been rerun
at this packet-only checkpoint. All 172 targeted format/downloader/export
cases passed independently. Repository bytecode/test-cache scans were empty
after each run, including failures. No commit, push or production deployment
was performed.

## Text conversion verification and local publication

The focused parser/reader/downloader/export run passed 222 cases. The first
complete run had 1,920 passes, one Safari skip and one stale manifest-order
assertion after registering the HLP reader. Updating that assertion keeps
the source/index/compiled precedence checks; no application failure was
suppressed. The repeated complete suite passes **1,922 cases**, with one
unavailable-Safari skip and one upstream Starlette/httpx deprecation warning
(607.96 seconds). This includes both isolated real-WASM DOS tests and the
new real-Chrome HLP rendering/link/Back regression.

The staged product-`bc` build retains all 253 existing bundle paths. Its 22
Windows bundles now contain 39,035 native articles instead of keyword-only
pages. All 224 unselected bundles remain byte-identical; the seven older
C++ normalized payloads are also unchanged, apart from converter timestamps.
All 495 retained originals have the same pre/post-publication SHA-256s.
Recoverable publication backup:
`data/.helps-previous-0d1246b0e5014dcb8770570149e98881/`.
The standard documentation publisher again preserves local edits and excludes
RE notes. Public Windows Help/Converter/format-index copies match their sources.

Actual Docker Python 3.12.15 runs the registered HC31 reader. Live HTTP serves
WIN31WH's 3,623 native articles and the 54-row fonttbl article 2559; its public
query URL contains the complete article text. The rebuilt global index is
ready with 172,110 topics, 36 documents and no warnings. Both keyword and
phrase full-text queries find fonttbl at its native ID. A local screenshot
also confirms title/frame, syntax, parameter tabs and scrolling in the shared
help window. Integrated-browser/Chrome UI surfaces are unavailable to the
computer-use connector here; the real headless Chrome runtime was used instead.

Published link fragments include 118,543 direct internal targets and 1,797
external targets. Every direct internal destination exists. One native HLP
hash remains missing: article 1023 (`MS Windows`) links `Copyright` through
E2 payload `4A F1 D4 37` at record `2AC2D0h`, but hash `37D4F14Ah` has no
entry in the original `|CONTEXT` tree. Its source identity is retained as an
unavailable link, not erased or redirected. Unsupported Windows macros and
picture placeholders remain separate declared limitations.

Repository bytecode/test-cache scans and `git diff --check` are empty/clean.
No commit, push or production deployment was performed.

## Deferred graphics research

Graphics and everything tied to image rendering/active regions are deferred
at the user's request. The experimental `winhelp_pictures.py` and its reader
integration were removed; no image-link labels, picture descriptors or other
graphics behavior from that experiment were published. The working text/UHF
reader remains unchanged. The follow-up checklist is in root `TODO.md`.

Read-only inspection found 1,429 referenced picture containers, 2,256 variants
and 2,547 image-region hotspot descriptors across the 22 retained HLPs.
617 variants have hotspot data. Most are DIB type 6 with 4-bit palettes/LZ77;
359 variants are type-8 metafiles. A temporary C harness in
`/tmp/thelp-winhelp-hotspots.IMjDEE/` calls the original HelpDeco `SearchFile`,
`GetCWord`, `GetCDWord`, `GetWord`, `GetDWord` and `StringRead` functions.
Every descriptor field and hotspot rectangle/name/reference agrees with the
experimental Python interpretation. This proves outer fields, not decoded
pixels, macro execution or browser graphics support.

Important observations for a future implementation:

- Hotspot extra data is not merely a list of macro strings. External regions
  use a size-bounded native subtype/hash/window/filename packet, and the
  four-byte hotspot value is its offset into that extra-data block. Observed
  CC macro regions also use offset 0, not a constant field value of 1 as old
  prose suggests. Never replace authoritative binary operands with a guessed
  target from a display label; retain names/reference strings separately.
- Bitmap regions may differ between resolution variants. One retained inline
  OWL picture has two regions in its first variant and three in its second;
  its native cursor increment is four. A first-variant-only implementation
  would miss an authored region. This is a structural issue, not an OWL-name
  parsing rule.
- Unknown pixel structures and unsafe Windows commands remain unsupported.
  Source originals and published `winhelp_objects` payloads were not changed.

## Context cursor preservation (2026-10-12)

Native `|CONTEXT` entries can select a later display record or a nonzero
cursor within one article. The first HC31 reader preserved those rows for
direct/local links and keywords, but exported symbolic hashes only as article
aliases. An external hash jump therefore lost the row after alias resolution;
uncached public alias URLs also failed because the server indexed only numeric
aliases. This was a shared destination-model/lookup defect, not missing HLP
article records.

`TopicRecord.alias_lines` now exports optional shared `aliases.lines` entries.
The viewer resolves article and row together; explicit rows and real topic IDs
take precedence. The public search cache stores both numeric/symbolic aliases,
native case comparison and destination rows. Public alias URLs normalize to
the article plus row without producing another searchable/sitemap topic.
Synthetic source records verify a context cursor at 130 in a wrapped article
and a real two-file external jump. Chrome checks that line 2 is highlighted,
Back returns to the source and the public alias URL opens the same destination.
No picture decoding or image-region links are implemented by this correction.

Publication verifies all 495 source hashes, all 253 bundle paths and the
byte-identical 224 unselected bundles. The selected 29 C++ bundles preserve
their entire prior payload after excluding converter timestamps and the new
alias-line map; native articles still total 39,035. There are 1,496 aliases
with non-start destination rows. For example CLASSLIB hash `0017986Fh` opens
native article 14 at row 69. Actual local Docker HTTP redirects to that row,
honors an explicit row override, and serves the updated mirrored JS. Its
rebuilt index is ready with 172,110 topics, 36 documents and no warnings.
Regression runs cover 118 native/navigation/server/browser checks (including
the unchanged NG and THELP model hashes) and 176 converter/corpus/export
checks, including every retained HLP. A first live index wait
expired after 90 seconds during the normal rebuild; a later readiness check
and native URL checks completed successfully. No source/data correction was
needed for that wait timeout. Old HELP generation is retained in
`data/.helps-previous-51f7aef6d5b8433ebc9d78bcddc70c2b/`.
