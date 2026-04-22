# Borland HLX (compiled) — best-effort analysis

> Created: 2026-04-19 · Last updated: 2026-04-20

Used by: Borland C++ 3.x–4.x compiled help (extension: `.HLX`).

This document summarises a pragmatic analysis of compiled `.HLX` files
found in the Borland C++ 4.x sample tree and documents the project's
best-effort reader (heuristic + deterministic approaches). It collects
observed patterns, parsing heuristics, hotspot extraction notes and
practical test suggestions — it is not a formal binary specification.

### 1 Overview

Compiled `.HLX` files are binary: a printable NUL‑terminated string pool
coexists with pointer tables (16‑bit or 32‑bit little-endian) that
reference pool entries. Many variants store short offsets relative to a
pool base rather than absolute file offsets.

### 2 Observations

- Files often begin with a short signature-like area (many samples start
  `0x3B 0x29 ...`).
- Numerous NUL-terminated printable strings are present: topic titles,
  index labels, tokens and occasional RTF references.
- Multiple arrays of little-endian offsets (16‑bit or 32‑bit) typically
  point into the string pool; their position varies between samples.
- Textual HLX directives (e.g. `;SCREEN`, `;STAMP`) are absent in
  compiled `.HLX` files.

### 3 Tentative file layout (observed)

```
┌──────────────────────────────┐
│  Small signature / sync area │  (often starts 0x3B 0x29)
├──────────────────────────────┤
│  Small header fields         │  (pool base candidate often at data[4:6])
├──────────────────────────────┤
│  Pointer table(s)            │  (16‑bit or 32‑bit arrays)
├──────────────────────────────┤
│  Binary blobs (hotspots, code)│
├──────────────────────────────┤
│  String pool (ASCIIZ)        │  (NUL-terminated printable runs)
└──────────────────────────────┘
```

Note: the above is an observed, not guaranteed layout. Many files mix
the tables and pools in different orders.

### 4 Header field candidates

The following fields are commonly observed (tentative):

| Offset | Size | Field         | Observed notes |
|--------|------|---------------|----------------|
| 0..3   | var  | Signature     | often `3B 29 ...` sync area |
| 4..5   | 2    | PoolBase?     | candidate 16-bit pool base; if invalid we fallback |
| 6..?   | var  | Header flags  | sample-dependent metadata |

Treat these values as heuristics — use validation (>=0x100 & < file_size)
before trusting a pool base.

### 5 Pointer table shapes

| Type   | Entry size | Notes |
|--------|------------:|-------|
| 16-bit | 2 bytes     | Common; often monotonic increasing offsets into pool |
| 32-bit | 4 bytes     | Present in some samples; used for larger pools |

### 6 Header scanning & pointer-table scoring

When a deterministic detector is not confident the reader scans the
header region in both 2‑ and 4‑byte strides and scores candidate
tables. A practical scoring heuristic uses three signals:

- frac_into_pool: fraction of entries that resolve into the pool range
- monotonicity: fraction of adjacent entries that are non-decreasing
- uniqueness: fraction of unique values in the table

A simple score (illustrative) is:

```
score = 0.6*frac_into_pool + 0.2*monotonicity + 0.2*uniqueness
# add small bias for 16-bit tables when sizes are similar
```

The implementation uses a similar weighted scoring and discards
candidates with very low `frac_into_pool`.

### 7 Naive topic grouping

- Extract all printable ASCIIZ strings (prefer CP437, fallback latin‑1).
- Group strings into naive topics using `is_title()` heuristics: lines
  that look like a heading (ALL CAPS, short, or starting with
  `About/Help/Contents/Menu`).

### 8 Pointer→topic mapping

- Deterministic detector (if confident) supplies `pointer_map` used
  directly.
- Otherwise the reader builds a global `addr_counter` of referenced
  addresses discovered while scanning blobs and header tables. High-
  frequency addresses that decode to short printable strings are
  candidate topic starts and are mapped to the nearest naive topic
  offset or to a title match, producing the `final_pointer_map`.

### 9 Hotspot scanning algorithm (pseudocode)

```python
def scan_blob(blob, pool_base, file_size, topics_map):
    CONTROL_RANGE = range(0x00, 0x08)
    for i in range(len(blob)):
        ctrl = blob[i]
        if ctrl in CONTROL_RANGE:
            for size in (2, 4):
                if i+1+size <= len(blob):
                    raw = le_int(blob[i+1:i+1+size])
                    addr = resolve_addr_for_scan(raw, pool_base)
                    if pool_base <= addr < file_size:
                        s = decode_printable_at(addr)
                        if len(s) >= 3:
                            target = topics_map.find_target(addr)
                            if target:
                                line, col = map_blob_offset_to_linecol(blob, i)
                                emit_positioned_keyword(source_topic, target, line, col)
```

`resolve_addr_for_scan()` prefers absolute pool addresses (>= pool_base)
but accepts short raw values interpreted as `raw + pool_base` when
that resolves into the pool.

### 10 Control bytes (observed)

- `0x00`–`0x07`: common hotspot prefixes followed by 2/4-byte pointer
  (interpretation varies across variants).
- other values: file/variant specific; watch for patterns and add
  special-cases as new variants are analysed.

### 11 Hex examples (annotated)

Example: small pointer table (16-bit words) referencing pool at 0x100

```
... header ...
02 00 04 00 08 00 0C 00 10 00  # pointer table: 0x0002,0x0004,... (little-endian words)
... blob ...
04 1A 00                       # control=0x04, pointer=0x001A -> resolves to pool address 0x11A
...
```

Interpretation: the reader will test whether `0x001A` + pool_base
(if needed) points into the string pool and decode the target string.

### 12 Testing & golden fixtures

- Recommended fixture path: `tests/golden/hlx/` with small hand-
  verified extracts. Each fixture should include expected `pointer_map`
  and a small set of `PositionedKeyword` assertions.
- Add a `tests/test_hlx_golden.py` that loads fixtures and asserts
  deterministic mapping + hotspot targets.

### 13 Next steps (recommended)

- Add concrete hex snippets from representative HLX samples to
  illustrate header/pointer patterns (expand section 11).
- Create golden fixtures for 2–4 representative files and add tests.
- Iterate on control-byte rules for low-diversity variants (BCW,
  OPENHELP etc.).

### Implementation references

- Heuristic reader: `thelpviewer/converter/readers/hlx_binary.py`
- Deterministic detector: `thelpviewer/converter/readers/hlx_deterministic.py`
- Data models: `thelpviewer/converter/base.py` (`TopicRecord`, `PositionedKeyword`)
- Tests: `tests/test_hlx_reader.py`, `tests/test_hlx_hotspots.py`, `tests/test_hlx_small_files.py`

---

If you want, I can now add concrete hex excerpts and create the first
golden fixture (small sample + expected `PositionedKeyword` set). Shall
I proceed with that? 
