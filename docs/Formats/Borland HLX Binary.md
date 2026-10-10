# Borland HLX (compiled) — best-effort analysis

> Created: 2026-04-19 · Last updated: 2026-05-05

Used by: Borland C++ 3.x–4.x compiled help (extension: `.HLX`).

This document summarises a pragmatic analysis of compiled `.HLX` files
found in the Borland C++ 4.x sample tree and documents the project's
best-effort reader. It collects observed patterns, parsing heuristics,
hotspot extraction notes, measured corpus behaviour and practical test
guidance. It is still not a formal binary specification.

### 1 Overview

Compiled `.HLX` files are binary. A printable NUL-terminated string pool
coexists with pointer-like tables and binary control streams that encode
cross-topic navigation. Some variants behave like full manuals with many
topic starts; others are closer to compiled search/index databases.

### 2 Observations

- Files often begin with a short signature-like area. Many samples start
  with `3B 29 02 00 00 08 69 32 34 00`.
- Numerous NUL-terminated printable strings are present: topic titles,
  index labels, API names and occasional fragments of layout/control
  text.
- Multiple arrays of little-endian offsets (16-bit or 32-bit) typically
  point into the string pool, but their exact position and quality vary.
- Textual HLX directives such as `;SCREEN` or `;STAMP` are absent in
  compiled `.HLX` files.
- In the current Borland C++ 4.x corpus, bytes `4..5` consistently hold
  `0x0800`, which is also a valid inferred pool base.

### 3 Corpus snapshot (current project state)

Measured with the current reader on `data/sources/Borland C++ 4.x/`:

- 20 compiled `.HLX` files total.
- 9 files currently export as `compiled-topics`.
- 11 files currently export as `compiled-index`.

Representative samples:

| File | Size | Reader result | Topics | Pointer map | Positional hotspots | Notes |
|------|-----:|---------------|-------:|------------:|--------------------:|-------|
| `BCW.HLX` | 45,094 B | `compiled-topics` | 425 | 5 | 14,461 | Still rich enough to keep grouped topics |
| `BCDOS.HLX` | 6,182 B | `compiled-topics` | 94 | 0 | 1,082 | Topic-rich even without a usable pointer map |
| `OLE.HLX` | 61,478 B | `compiled-index` | 1,984 | 13 | 0 | Pointer map exists, but payload is still too shallow to present as article topics |
| `OWL.HLX` | 69,670 B | `compiled-topics` | 712 | 14 | 20,680 | Large corpus with stable hotspot extraction |
| `OPENHELP.HLX` | 2,086 B | `compiled-index` | 36 | 0 | 0 | Low-diversity/search-like payload; deterministic parse is too weak |

Current `compiled-index` files in the sample corpus:

- `BWCC.HLX`
- `HELPREF.HLX`
- `OLE.HLX`
- `OPENGL.HLX`
- `OPENHELP.HLX`
- `RSL.HLX`
- `VFW.HLX`
- `WIN31WH.HLX`
- `WIN32.HLX`
- `WINSIGHT.HLX`
- `WINSPCTR.HLX`

### 4 Payload families (current typology)

The current reverse-engineering work distinguishes several recurring HLX
payload families. These are not official Borland format names; they are
working labels derived from the observed binary content.

| Family | Typical signals | Current examples | Interpretation |
|--------|-----------------|------------------|----------------|
| `rtf-keyword-map` | many `.rtf` strings, especially `lkeyword.rtf`, plus many strings starting with 8 hex digits | `BCW.HLX` | keyword/index map that still groups labels richly enough to expose clustered topics |
| `rtf-overview-map` | many `overview.rtf` references | `WIN31WH.HLX` | external overview/topic map rather than article storage |
| `rtf-reference-map` | many generic `.rtf` references without a strong `lkeyword` or `overview` bias | `BWCC.HLX`, `CWH.HLX`, `OCF.HLX`, `OPENGL.HLX`, `RPC.HLX`, `SOC.HLX`, `WIN32.HLX` | external reference map with labels and anchors, but not self-contained full text |
| `heading-catalog` | very high topic count, average lines per topic around 1 to 2, high single-line ratio, many long headings | `OLE.HLX`, `HELPREF.HLX` | heading catalog or navigational title store, not article bodies |
| `topic-clusters` | average lines per topic around 3 or more, lower single-line ratio, meaningful grouped lexical neighborhoods | `BCDOS.HLX`, `CLASSLIB.HLX`, `OWL.HLX` | best current candidate for genuine internal topic clustering |
| `compact-index` | low-diversity compact payload, few long strings, usually small file size | `OPENHELP.HLX` | small search/index database |
| `mixed-catalog` | none of the above dominates clearly | rare / transitional | requires case-by-case inspection |

The parser now writes this classification to metadata as `hlx_family`.

Additional current corpus result from export validation:

- `BCW.HLX` is still the strongest confirmed case of a functional HLX → UHF 2.0 topic bundle.
- `OLE.HLX`, `RSL.HLX`, `WINSPCTR.HLX`, `VFW.HLX`, `WIN32.HLX`, and `WIN31WH.HLX` currently remain `compiled-index` exports: they produce many one-line labels or headings, but no stable multi-line article stream.

### 4.1 Index-record structure signals

The current `hlx_probe.py` can also summarize the compiled index records themselves. This turned out to be useful for distinguishing between several catalog-like variants that all remain `compiled-index` at export time.

Observed patterns:

- `OLE.HLX`: 2005 scanned index records, 1984 unique target offsets, only 15 repeated targets. Dominant flag is `1`, but target deltas are still mostly `+4`, with smaller tails at `+8`, `+12`, and `+16`. This looks like a dense heading/address catalog rather than a plain sequential slot table.
- `RSL.HLX`: 117 records, 117 unique targets, no repeated targets. Target deltas are predominantly `+4`, then `+8`, `+16`, `+12`, `+24`. This is a compact linear catalog with no obvious target reuse.
- `WINSPCTR.HLX`: 75 records, 75 unique targets, no repeated targets. Again, `+4` dominates strongly, with a short sparse tail of larger jumps. This is structurally closer to `RSL.HLX` than to `OLE.HLX`.

The strongest current reverse-engineering result for these index records is:

- in the sorted target stream, `flags` behave almost like a span or step code where `target_stride ~= flags * 4`
- `OLE.HLX` fits this very strongly (`flag 1 -> +4` in 1730/1753 cases, `flag 2 -> +8` in 153/153, `flag 3 -> +12` in 55/55, `flag 4 -> +16` in 23/23)
- `RSL.HLX` and `WINSPCTR.HLX` fit it even more cleanly, with no target reuse and exact `flag * 4` stride matches for all dominant flags currently observed

This does not yet prove the semantic meaning of each flag, but it strongly suggests that the low flag values encode how many 4-byte target slots the current record spans in the compiled index table.

So far, these signals reinforce the current routing choice: some HLX variants do expose rich lexical neighborhoods or external reference maps, but they still serialize to one-line catalog entries rather than to stable internal article bodies.

### 5 Tentative file layout (observed)

```
┌──────────────────────────────┐
│  Small signature / sync area │  (often starts 0x3B 0x29)
├──────────────────────────────┤
│  Small header fields         │  (pool base candidate often at data[4:6])
├──────────────────────────────┤
│  Pointer table(s)            │  (16-bit or 32-bit arrays)
├──────────────────────────────┤
│  Binary blobs / controls     │  (hotspots, layout, variant-specific data)
├──────────────────────────────┤
│  String pool (ASCIIZ)        │  (NUL-terminated printable runs)
└──────────────────────────────┘
```

This is an observed layout, not a guaranteed one. Tables and pools may
interleave differently by variant.

### 6 Header field candidates

The following fields are commonly observed (tentative):

| Offset | Size | Field | Observed notes |
|--------|------|-------|----------------|
| 0..3 | var | Signature | often `3B 29 ...` sync area |
| 4..5 | 2 | PoolBase? | candidate 16-bit pool base; validate before use |
| 6..? | var | Header flags | sample-dependent metadata |

Treat these values as heuristics. Only trust a pool base when it is at
least `0x100` and still inside the file.

### 7 Pointer table shapes

| Type | Entry size | Notes |
|------|-----------:|-------|
| 16-bit | 2 bytes | Common; often monotonic offsets into the pool |
| 32-bit | 4 bytes | Present in some larger variants |

Measured pointer-map counts for selected files:

- `BCW.HLX`: 5
- `OCF.HLX`: 7
- `OLE.HLX`: 13
- `OWL.HLX`: 14
- `WIN31WH.HLX`: 19

### 8 Header scanning and pointer-table scoring

When the deterministic detector is not immediately confident, it scans
the header region in both 2-byte and 4-byte strides and scores candidate
tables using three main signals:

- fraction of entries that resolve into the pool range
- monotonicity of adjacent entries
- uniqueness of values

The current implementation also adds a strong signal for title matches
against the naive topic set. In practical terms, it uses this shape:

```python
score = (
    frac_into_pool * 100.0
    + monotonicity * 40.0
    + uniqueness * 10.0
    + title_fraction * 80.0
    + (2.0 if step == 2 else 0.0)
)
```

Candidates with `frac_into_pool < 0.25` are discarded.

### 9 Naive topic grouping

- Extract all printable ASCIIZ strings, preferring CP437 and falling
  back to Latin-1.
- Group strings into naive topics using title heuristics: all-caps
  labels, short headings or strings starting with words like `About`,
  `Help`, `Contents` or `Menu`.
- If no good title-like sequence is found, still return a usable fallback
  topic list instead of aborting the parse.

### 10 Reader decision rule

The current wrapper in `hlx_binary.py` does not trust compiled index
records blindly. The effective rule is:

1. Always attempt deterministic topic extraction.
2. Scan compiled search/index records in parallel.
3. Prefer `compiled-topics` only when the deterministic parse looks both
  substantial and non-shallow:
  - `topic_count >= 50`, and
  - average `raw_lines` per topic is at least `3.0` or the share of
    single-line topics is at most `0.75`
4. Within that richer topic set, pointer-map evidence still helps confirm
  that the grouped topics are useful:
  - `pointer_map >= 3`, or
  - `topic_count >= 50`
5. Otherwise, if there are at least 10 compiled index records, fall back
   to `compiled-index`.

This is why files like `BCW.HLX` and `OWL.HLX` remain topic-based, while
`OLE.HLX`, `WIN31WH.HLX` and similarly shallow corpora now downgrade to
`compiled-index` instead of pretending to be article trees.

### 11 Pointer-to-topic mapping

- When a reliable pointer table is found, the deterministic detector
  returns `pointer_map` directly.
- Otherwise the wrapper maps control-stream targets to the nearest topic
  start found in the file.
- When no topic tree is reliable enough but many compiled index records
  exist, the reader emits an index-only document.

### 12 Hotspot scanning algorithm (effective behavior)

The wrapper scans the full binary for small control bytes followed by a
2-byte or 4-byte address candidate:

```python
for i in range(file_size):
    if data[i] in range(0x00, 0x08):
        try_16bit_target(i + 1)
        try_32bit_target(i + 1)
```

For each candidate target address:

- prefer an explicit `pointer_map` hit
- otherwise map to the nearest topic start at or before that address
- attach a `PositionedKeyword` to the source topic using a simple column
  estimate derived from printable bytes before the control sequence

This produces useful navigation even in files where `pointer_count == 0`
but the binary still contains many target-like control sequences.

### 13 Control bytes (observed)

- `0x00`–`0x07`: common hotspot prefixes followed by 2-byte or 4-byte
  pointer payloads
- other values: variant-specific; no general meaning is assigned yet

### 14 Concrete sample bytes

Representative first 32 bytes from current samples:

| File | First 32 bytes (hex) |
|------|----------------------|
| `BCW.HLX` | `3b29020000086932340061725f457831206c6b657977000014001500ffff1600` |
| `BCDOS.HLX` | `3b29020000086932340075727265640a0006002a2f0a000001000200ffff0300` |
| `OLE.HLX` | `3b290200000869323400fff01dff810f4bff840000ff00001c001d00ffff1e00` |
| `OWL.HLX` | `3b290200000869323400000000000000000000000000000020002100ffff2200` |
| `OPENHELP.HLX` | `3b290200000869323400010101010101010101010101000000000000ffff0100` |

These values are useful mostly as family markers. The prefix is stable,
but the header diverges quickly after it.

### 15 First printable pool strings (examples)

Representative early strings after the inferred `0x0800` pool base:

- `BCW.HLX`: `-wmsg`, `-wnsf`, `-wobs`, `page size`, `parameter types`
- `BCDOS.HLX`: `pieslice`, `polygon`, `program segment prefix`
- `OLE.HLX`: `APIs to initialize OLE`, `APIs to manage compound documents`
- `OWL.HLX`: `BITMAPINFO`, `BITMAPINFOHEADER`, `BitmapOrigin`
- `OPENHELP.HLX`: only two weak printable fragments near the pool start

This is a useful discriminator between topic-rich manuals and the more
index-heavy low-diversity variants.

### 16 Tests and fixtures

Existing regression coverage:

- `tests/test_hlx_reader.py`
- `tests/test_hlx_hotspots.py`
- `tests/test_hlx_small_files.py`
- `tests/test_hlx_golden_ole.py`

Recommended next fixture work:

- create a `tests/golden/hlx/` directory with small hand-verified slices
- add at least one strong pointer-map case (`OLE` or `OWL`)
- add at least one low-diversity/index-heavy case (`OPENHELP`)

### 17 Reverse-engineering workflow in this repo

Use the dedicated probe helper:

```bash
python tools/hlx_probe.py "data/sources/Borland C++ 4.x"
python tools/hlx_probe.py "data/sources/Borland C++ 4.x/OLE.HLX" --details
```

The script reports:

- final reader classification (`compiled-topics` vs `compiled-index`)
- payload family (`hlx_family`)
- topic count
- pointer-map count
- hotspot count
- index-record count
- average lines per topic
- RTF reference count
- first printable strings after the inferred pool base
- sample pointer-to-context mappings

This makes it easier to compare future heuristic changes against a
stable baseline.

### 18 Generating UHF bundles for HLX samples

To generate only the Borland C++ 4.x HLX corpus into a safe staging
directory without overwriting the main `data/helps/` catalog:

```bash
python -m thelpviewer.server.converter \
  "data/sources/Borland C++ 4.x" \
  var/hlx-uhf \
  --bundle \
  --bundle-layout helps \
  --clean
```

This writes `.json.gz` UHF bundles plus a local `catalog.json` under
`var/hlx-uhf/`.

### 19 Next steps

- investigate the five current `compiled-index` variants to decide
  whether they are truly search databases or still hide a topic stream
- add golden fixtures for one strong and one weak variant
- refine hotspot scanning for variants with `pointer_count == 0` but a
  large hotspot count (`BCDOS`, `CLASSLIB`, `OPENGL`)

### Implementation references

- Heuristic wrapper: `thelpviewer/server/converter/readers/hlx_binary.py`
- Deterministic detector: `thelpviewer/server/converter/readers/hlx_deterministic.py`
- Data models: `thelpviewer/server/converter/base.py`
- Probe helper: `tools/hlx_probe.py`
- Tests: `tests/test_hlx_reader.py`, `tests/test_hlx_hotspots.py`, `tests/test_hlx_small_files.py`, `tests/test_hlx_golden_ole.py`
