# Borland Turbo Debugger/Profiler Runtime Help

> Created: 2026-05-14 · Last updated: 2026-09-19

Used by: Borland Turbo Debugger 1.0/2.x and Borland Turbo Profiler.
File extensions: `.TDH`, `.TFH`.

These files are not Borland THELP/TPH/TCH streams. They do not contain the
THELP signature `$*$* &&&&$*$` and must be detected and parsed separately.

Detailed reverse-engineering history, runtime traces, and unresolved questions
are kept in internal project notes rather than the public format reference.

All visible multi-byte integers in the on-disk outer structures are
big-endian unless stated otherwise. In the TDH runtime map, each word is later
interpreted as a signed 16-bit delta.

For the known TDH/TFH sample families, the runtime text layer and topic
addressing are now decoded rather than merely sketched. The formerly suspicious
later-2.x context `537` is now confirmed as a literal three-byte empty
placeholder block (`00 00 0D`), not as hidden undecoded text. The old
loader/service blocker has also narrowed sharply: the widened 2.x path is now
anchored directly in resident `TD.EXE`, while `TDH386.SYS` turns out to be a
separate `TDHDEBUG` DOS device driver rather than the TDH text loader itself.
That status is now also covered by end-to-end bundle export regression checks
for the current legacy TDH, later 2.x TDH, and TFH samples rather than only by
reader-local decode assertions.
The exact proof addresses, helper entrypoints, and byte-level runtime traces
stay in those internal notes; this document only keeps the stable format-level
conclusions.

## 1. Family Overview

The TDH/TFH family shares one higher text layer:

- nibble-packed text, read low nibble first then high nibble
- `^` hotspot markers with a big-endian target word
- fixed-width runtime line layout (`49` columns)

The outer container differs by product family:

| Variant | Used by | Word 0 | Outer layout |
|---------|---------|--------|--------------|
| TDH | Turbo Debugger | byte size of each visible pre-separator half | `header -> half A -> half B -> separator -> payload` |
| TFH | Turbo Profiler | context count | `count -> size table -> separator -> cumulative blocks` |

## 2. Detection

There is no fixed ASCII magic string. Detection is structural.

### 2.1 TDH Detection

Known TDH samples satisfy all of the following:

- word `0x0000` is an even byte count in the observed range `0x0200..0x0800`
- two visible halves of that byte size follow immediately after the header word
- the separator word at `2 + header_word + header_word` is `0x0001`
- the first payload byte after the separator is in the observed range `0x80..0xBF`
- the payload begins with a short run of `0xCC` bytes after that lead byte

### 2.2 TFH Detection

Known TFH samples satisfy all of the following:

- word `0x0000` is the big-endian context count
- `context_count` big-endian words follow as a size table
- the separator word at `2 + context_count * 2` is `0x0000`
- the first byte after the separator follows the same observed payload lead pattern

## 3. TDH Outer Layout

```text
┌──────────────────────────────────────────┐  +0x0000
│ HeaderWord (WORD)                        │  byte size of each visible half
├──────────────────────────────────────────┤  +0x0002
│ VisibleHalfA (HeaderWord bytes)          │
├──────────────────────────────────────────┤
│ VisibleHalfB (HeaderWord bytes)          │
├──────────────────────────────────────────┤  +SeparatorOffset
│ SeparatorWord = 0x0001                   │
├──────────────────────────────────────────┤  +EncodedPayloadOffset
│ Encoded payload                          │
└──────────────────────────────────────────┘
```

Known header values:

- TD 1.0 sample: `0x0206` (`518` bytes per half)
- later TD 2.x sample: `0x0254` (`596` bytes per half)

The first word is a byte-size field, not a fixed TDH version signature.

Current sample-specific probe offsets, payload-prefix comparisons, and other
byte-level evidence stay in the internal reverse-engineering notes.

### 3.1 Runtime Context Map

The runtime uses the separator offset as the context-map base.

Known sample families currently use these active map widths:

- TD 1.0: fixed legacy width `0x212` (`530`) words
- later TD 2.x sample: full pre-separator prefix width (`596`) words

That split is also visible directly in the file layout. In TD 1.0, the visible
pre-separator area contains only `259 + 259 = 518` words, so the live legacy
`530`-word runtime load necessarily overruns by `12` words into the separator
and payload prefix. In the later 2.x sample, the widened `298 + 298 = 596`
visible words already fill the whole active runtime map, so the `596`-word
model stops cleanly before the separator instead of spilling into the payload.

On the later TD 2.x sample, decoding that full `596`-word runtime map exposes a
coherent late-topic region through contexts `530..595`. So the `596`-word
model is an observed property of the known 2.x sample family, not just a
reader-side overrun heuristic.

For the known TDH sample families, that is now enough for practical end-to-end
support rather than only partial reverse-engineering:

- the legacy TDH 1.0 sample decodes through the full user-visible namespace,
  with the old high-tail `519..529` now resolving as alias continuations rather
  than as unnamed hidden pages
- the later TDH 2.x sample decodes through the full real `596`-context map,
  including the confirmed late tail `530..595`
- the resident TD 2.x runtime agrees with the same cumulative signed-delta
  addressing model used by the file-side reader
- context `537` is a genuine empty placeholder block, so any future collapse to
  nearby context `539` would be viewer/export policy rather than missing format
  decode

That does not erase every historical caution. The end of the legacy TDH 1.0
high-context range is alias-heavy rather than a clean run of standalone pages:
current tooling reconstructs redirects such as `520 -> 425`, `521 -> 380`,
`522 -> 314`, `527 -> 393`, and `528 -> 328`, so the overlap window near
`530..543` cannot be resolved by naive title-for-title comparison alone. But
that is now a namespace-reconstruction nuance, not a missing decoder.

In other words, for the known TDH sample families the current reader status is
already `decoded` at the text/topic-addressing layer. The remaining uncertainty
is limited to exact 1.0-to-2.x namespace reconstruction near the front edge of
the late 2.x tail plus a few runtime implementation details already tracked in
the internal reverse-engineering notes. Exact `TD.EXE` helper addresses,
runtime buffers, the `600` vs. `596` preload nuance, and the detailed anchor
list for the observed high-context drift stay there.

Each map entry is interpreted as `sign16(word)`, not as an unsigned block size.

Context starts are computed cumulatively:

```text
start(0) = separator_offset
start(n) = separator_offset + sum(sign16(map[i]) for i = 0 .. n-1)
```

Runtime slot `0` is effectively a separator-aligned artifact rather than a
user-visible help topic. Real help content starts at context `1`.

### 3.2 TDH Topic Block

At each computed TDH topic start:

- the first big-endian word is a per-page control / next-context field
- visible text begins immediately after that word
- there is no explicit per-topic byte length, so the next distinct computed
  topic start is the hard upper boundary for visible decoding
- text terminators inside that bounded range still end the rendered topic
- the runtime page parser renders at most `15` visible lines per TDH page

When the leading control word is a valid in-range context id, it behaves as the
runtime next-page target.

Alias discovery is intentionally separate from visible decoding. Some legacy
alias markers sit beyond a topic's visible boundary, so the reader performs a
second unbounded runtime-stream scan only for alias positions. Bytes found by
that scan must not leak into the rendered text of the preceding topic.

## 4. TFH Outer Layout

```text
┌──────────────────────────────────────────┐  +0x0000
│ ContextCount (WORD)                      │
├──────────────────────────────────────────┤  +0x0002
│ SizeTable[ContextCount] (WORD each)      │  big-endian block sizes
├──────────────────────────────────────────┤  +SeparatorOffset
│ SeparatorWord = 0x0000                   │
├──────────────────────────────────────────┤
│ Runtime blocks                           │  cumulative variable-size blocks
└──────────────────────────────────────────┘
```

For the known TFH sample, `ContextCount = 0x016B` (`363`).

### 4.1 TFH Block Addressing

The runtime block base is the separator offset itself:

```text
block_start(0) = separator_offset
block_start(n) = separator_offset + sum(size[i] for i = 0 .. n-1)
```

Known sample detail:

- context `0` is a one-byte sentinel block
- context `1` therefore starts one byte after the separator word

### 4.2 TFH Topic Block

Each TFH block consists of:

1. one leading big-endian control word
2. visible text stream starting at block byte `+2`

When that control word is a valid in-range context id, it behaves as the
runtime next-page target.

## 5. Shared Text And Hotspot Layer

### 5.1 Nibble Packing

Text is decoded low nibble first, then high nibble.

Known nibble values:

| Nibble | Meaning |
|--------|---------|
| `0x0` | skip / no output |
| `0x1` | `e` |
| `0x2` | `t` |
| `0x3` | `r` |
| `0x4` | `o` |
| `0x5` | `i` |
| `0x6` | `n` |
| `0x7` | `a` |
| `0x8` | `s` |
| `0x9` | `l` |
| `0xA` | `c` |
| `0xB` | `h` |
| `0xC` | space |
| `0xD` | `^` hotspot/control marker |
| `0xE` | special marker class (`<E>` in the current reader) |
| `0xF` | literal byte from the next two raw nibbles as `low + high * 16` |

### 5.2 Hotspots

In the decoded stream, `^` starts a hotspot block:

1. align to the next byte boundary
2. read one big-endian target context word
3. decode visible hotspot label text until the next `^`

### 5.3 Line Layout

The runtime renders one screen line at a time with a width of `0x31` (`49`)
columns.

- CR/LF sequences terminate the current line
- ordinary text wraps at spaces before column `49`
- hotspot labels are kept intact; if a label does not fit near the right edge,
  it moves to the next line instead of being split

## 6. Relationship To THELP

TDH and TFH are separate Borland runtime-help containers, not THELP variants.
They should not be decoded by the THELP record parser even though they are used
by Borland DOS tools and also carry topic text, links, and next-page behavior.
