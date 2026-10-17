# Borland HLX RE Notes

Private analysis and converter evidence, not the public source-format datasheet.

## Verified keyword trees (2026-10-12)

All 20 originals in `var/sources/Borland C++ 4.x/` conform to the
standalone Windows Help B+ tree descriptor `i24`. Together they contain
18,975 exact keyword records and 29,064 referenced keyword-data positions.
The format contains no compressed article stream. Its native leaf count
matches its global header count in every file.

The previous extraction was structurally wrong: it treated PageSize at
header offset 4 as a string-pool start, grouped live and dead printable
strings as articles, inferred pointer arrays from header/page bytes and
invented local hotspots from small bytes followed by plausible integers.
The purported RTF/map families were largely classifications of unused
memory containing RTF paths. Scanned branch separator copies and free-space
remnants also produced duplicate or suffix “records”. Old topic counts,
families, pointer maps and hotspot statistics are superseded, not format
evidence.

The replacement parser reads bounded branch and leaf records, checks
header/file geometry, root/child depth, cycles, page used-area boundaries,
reciprocal leaf order and global keyword count. It preserves every live
keyword byte string, native occurrence count and KWDATA offset. No filename
or specimen-specific parsing branch is used.

Standalone output is explicitly `compiled-index`, one keyword per
projection page. Those sequential page IDs are converter-owned keyword
ordinals, not native article contexts. Native addresses survive in
`hlx_keyword_records` transport metadata. There are no guessed
positioned hotspots, article bodies or source Prev/Next links; standard
viewer Contents/Index/history controls remain available.
Full article navigation comes from the companion Windows HLP reader, now
registered for HC31 fixed-cell text. Normal builds prefer HLP over its
same-stem HLX; converting HLX alone still cannot manufacture a manual.
No existing source-format target is deleted
or redirected to a nearby keyword.

### Independent record comparison

Research directory: `/tmp/thelp-hlx-btree.eIU9So/`.
HelpDeco source revision:
`785273788af17fde4fba7df7162d547f8645d7d8`, fetched from
[the upstream repository](https://github.com/pmachapman/helpdeco).
A small harness calls its unmodified `GetFirstPage()` /
`GetNextPage()`, `my_gets()`, `my_getw()` and `getdw()`
routines on each original standalone tree. No application parser is used
to produce the reference enumeration. The C traversal matches every
Python record in offset, raw keyword bytes, count and KWDATA offset.

`tests/golden/hlx/keyword_trees.json` pins each original CRC32/SHA-256,
the independent record digest, page/depth counts, total keyword/reference
counts and first/last keywords. Record digests are SHA-256 over compact
JSON plus LF of ordered arrays:
`[file_offset, label.hex(), reference_count, kwdata_offset]`.
No external code is executed by the application or normal regression suite.

| Original | Keywords | Reference positions |
| --- | ---: | ---: |
| BCDOS.HLX | 163 | 237 |
| BCW.HLX | 2322 | 4135 |
| BWCC.HLX | 44 | 162 |
| CLASSLIB.HLX | 791 | 3084 |
| CWH.HLX | 254 | 686 |
| HELPREF.HLX | 189 | 189 |
| OCF.HLX | 1405 | 2492 |
| OLE.HLX | 1984 | 2445 |
| OPENGL.HLX | 936 | 1212 |
| OPENHELP.HLX | 36 | 62 |
| OWL.HLX | 3208 | 4901 |
| RPC.HLX | 563 | 750 |
| RSL.HLX | 117 | 301 |
| SOC.HLX | 181 | 205 |
| VFW.HLX | 763 | 785 |
| WIN31WH.HLX | 3013 | 3038 |
| WIN32.HLX | 2600 | 2640 |
| WINSIGHT.HLX | 64 | 150 |
| WINSPCTR.HLX | 75 | 116 |
| WORKHELP.HLX | 267 | 1474 |

Only OLE contains non-ASCII/control keyword bytes: one A0h nonbreaking
space and two 15h Word field separators. Windows ANSI metadata now uses
cp1252 for these Windows keyword trees; the shared cp125x decode table
retains C0 controls instead of substituting DOS glyphs. OEM formats retain
their existing screen alphabet.

### Remaining work

Windows Help paragraph/table/font/inline-link text now projects to real articles
with resolved keywords. Picture pixels and full Windows macro/UI behavior remain
limitations. HLX itself is no longer a guessed topic decoder. Charset bindings outside the English corpus
and the extra 2000h tree flag remain unverified.

### Matching companion revisions (2026-10-12)

WinWorld's original 4.52 CD contains all 20 installed HLX byte for byte.
Eighteen also match 4.5, but BCW and OWL differ. Binding the installed 4.52
BCW index to 4.5 KWDATA would misdirect 2,232 shared keywords; filenames and
mostly-equal labels are not proof of a matching edition. The 20 matching
HLP originals are retained in the existing 4.x source collection. Only the
four distinct BCW/OWL 4.5 files are copied into a separate 4.5 collection.
Their CRCs, native SYSTEM titles, release and provider/member provenance are
recorded in the manifest. No original HLX bytes are modified.

Shared B+ tree/container/topic validation and independent packet comparison
are documented in [Windows Help RE Notes](Windows%20Help%20RE%20Notes.md).

### Verification and local publication

The final targeted parser/corpus/bundle/code-page run covers 95 cases.
Independent Docker Python 3.12 parsing also verifies all 18,975 keyword
records and 29,064 reference counts. Actual headless Chrome opens BCW's
standard 2,322-entry index inside the desktop; an actual mouse click opens
keyword projection 1 in the same window, with no JavaScript exceptions.

The existing staged builder republished product `bc` (27 bundles, including
20 changed HLX projections). Source SHA-256s, all 251 catalog paths/titles,
seven other C++ normalized payloads and all unselected bundle bytes are
unchanged. Only the actual HLX keyword counts change in the catalog.
Recoverable publication backup:
`data/.helps-previous-55797616ce5b4e9da394c9a2f0b7c0e5/`.
Public datasheet/converter/format-index copies match the local HTTP catalog;
private RE notes are not exposed. Local Docker was restarted and its global
index is ready with 152,050 topic rows, 35 documents and no warnings.

The initial full regression run had 1,759 passes, one Safari skip and one
DOS browser close failure. The same DOS case initially failed in isolation,
then passed twice in an instrumented copy: at close, the shared frame button
was hit directly, the window was active/not busy and no modal/menu covered
it. This is not evidence of a format defect; no DOS or frame implementation
has been changed to hide the failure. Keep the intermittent close test under
observation and report its verification separately from HLX.
The final uninstrumented retry of both DOS browser variants together with
the complete targeted HLX/code-page set passed all 97 cases (56.15 seconds).
This does not establish that the earlier close failure is permanently fixed;
no production change was made for it. Repository bytecode/test-cache scans
were empty after every run, including failures.
No commit, push or production deployment was performed.
