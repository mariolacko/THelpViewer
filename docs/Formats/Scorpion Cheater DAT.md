# Scorpion's Cheater DAT Format

## Status

Preliminary reverse-engineering notes for the DOS-era `Scorpion's Cheater 23.0`
database files.

This format is **experimentally supported** by THelpViewer at the container
level. The current reader can enumerate records, build an index, and expose
text-bearing records as topics with best-effort decoded text.

The current reader also splits some records into multiple topics when the
payload contains internal page markers such as `[R010]`, `[R201]`, `[N001]`,
or bare line-start variants like `R204`.

For `program.dat`, the reader also reconstructs a best-effort main menu topic
(`Seznam položek`) and now derives the top-level program menu directly from the
`seznam` payload, not only from hardcoded labels. It exports those program-level
menu items as `contents[]` entries and also stores their current target hints in
metadata for research purposes. The current implementation also builds grouped
cross-file TOC sections for sibling databases such as `cheaty.dat`,
`navody.dat`, `vtipy.dat`, and `easter.dat`, using UHF cross-file targets.

The text payload still uses a custom token/formatting codec that has not been
fully decoded, so the visible text is only approximate.

Screenshot-derived text samples are useful as reverse-engineering references,
but they should be treated as temporary ground truth for codec work, not as
authoritative runtime replacements in exported content.

Sample files analysed:

- `cheat23/cheaty.dat`
- `cheat23/navody.dat`
- `cheat23/program.dat`
- `cheat23/vtipy.dat`
- `cheat23/easter.dat`

`icona.dat` is unrelated; it is a standard Windows icon resource.

## High-Level Structure

All content databases start with the same container header:

```text
12 1E 03 2D 41 4C 4C 2E ...
         -ALL.
```

The exact meaning of the first three bytes is still unknown, but the root
marker `-ALL.` is stable across the examined databases.

Immediately after the root header, the file contains a flat sequence of records.
Each record has four named fields:

1. `propDATE`
2. `propNAME`
3. `propORIG`
4. `DATA`

`propDATE`, `propNAME`, and `propORIG` are straightforward:

```text
ASCII field name
big-endian 32-bit length
raw field bytes
```

`DATA` is similar, but appears to store an extra trailing 4 bytes beyond the
declared length. For parsing purposes the safe rule is:

```text
"DATA"
big-endian 32-bit length
payload[length]
payload_tail[4]
```

The 4-byte tail is not a simple checksum. In short metadata records it clearly
contains meaningful payload bytes such as year/version suffixes.

## Observed Record Counts

From the current sample set:

| File | Parsed records | Notes |
|---|---:|---|
| `cheaty.dat` | 32 | Main cheat text database |
| `navody.dat` | 35 | Walkthroughs / guides |
| `program.dat` | 25 | UI resources, fonts, editorial text, misc data |
| `vtipy.dat` | 8 | Jokes |
| `easter.dat` | 9 | Easter-egg / misc content |

Representative record names:

| File | Record names |
|---|---|
| `cheaty.dat` | `ch01`, `ch02`, `ch03`, ... |
| `navody.dat` | `datumN`, `libraryN`, `nav01`, `nav02`, ... |
| `program.dat` | `_main`, `datum`, `egg`, `FONT1`, ..., `kecy`, `kecy2`, `pirat` |
| `vtipy.dat` | `datumJ`, `jok01`, `jok02`, ... |
| `easter.dat` | `datumE`, `east01`, `libraryE`, `rokE`, `seznamE`, `verzeE` |

`propORIG` stores the original build-time source path, for example:

```text
c:\djgpp\ja\!cheater\navody\navody.001
c:\prace2\thedraw\cheater\_main.bin
```

This suggests the files were built from a custom editor pipeline rather than
from a known third-party help compiler.

## Payload Characteristics

The large `DATA` blocks are not plain CP437/CP852 text. They contain:

- visible text fragments
- inline record tags such as `[0101]`, `[N001]`, `[R010]`
- many bytes in the `0x00-0x1F` range
- many bytes in the `0x80-0xFF` range
- formatting / navigation-like structures in records such as `seznamE`

Examples:

- `kecy` begins with something that clearly corresponds to an editorial page:
  `"[R010]"`, then a styled title similar to `EDITORIAL`, then body text
- `kecy2` contains multiple internal pages in one record, including markers
  for `R201`, `R204`, `R222`, and `R223`
- `nav01` begins with `"[N001]"` and a title matching `The Kymera`
- `seznamE` begins with `Seznam Polozek,[23.0]...`, suggesting an encoded table
  of contents or menu/index structure

Straight decoding as CP437 / CP850 / CP852 / CP1250 does **not** reconstruct
the original text cleanly. The payload is therefore best described as a custom
formatted/tokenized text stream, likely produced by the historical
Scorpion editor.

## Compression / Codec Notes

`cheater.exe` contains embedded strings from the **LZO 1.04** library, so the
application certainly uses LZO somewhere internally. However, the current `.dat`
payloads do not look like raw standalone LZO streams:

- they contain too much directly visible structure and text
- they are already wrapped in their own record container
- no standard LZO file framing is present in the `.dat` files themselves

Current working hypothesis:

- outer layer: custom Scorpion DAT record container
- inner text layer: custom text/formatting/token codec
- LZO may be used by the application at runtime, in editor/export tooling, or
  on selected resource blocks, but this has not yet been proven for the text
  records themselves

## Research Tooling

For byte-level inspection there is now a local helper script:

```bash
python3 tools/scorpion_probe.py "/path/to/program.dat" kecy --marker "[R010]"
```

It prints:

- a hex dump of the selected payload slice
- a raw CP852-ish one-byte-per-char view
- the current best-effort filtered display view used for reader experiments

For layout-heavy slices there is also a research-only aggressive mode:

```bash
python3 tools/scorpion_probe.py "/path/to/program.dat" kecy2 --byte-offset 13318 --length 2200 --drop-profile generic-layout --text-islands
```

This keeps the runtime decoder untouched, but prints:

- `DISPLAY WITH EXTRA DROP`
- `TEXT ISLANDS`

The current `generic-layout` profile is based on the repeatedly suspicious byte
set:

- `0x40`
- `0x60`
- `0x80`
- `0x90`
- `0xA0`
- `0xA1`
- `0xB0`
- `0xC0`
- `0xD0`
- `0xE0`
- `0xF0`
- `0xF1`

On `R222 / O programu` this already exposes more stable text islands such as
`SC ORPION CHEA`, `Index`, `Edic1al`, `DJGP`, `SCX`, `The Draw`, `Windows`,
and `K O N T K T`, even though the result is still far from a clean decode.

There is also a stricter profile derived from multi-sample affinity analysis:

```bash
python3 tools/scorpion_probe.py "/path/to/program.dat" kecy2 --byte-offset 13318 --length 900 --drop-profile text-only-strong --text-islands
```

This profile focuses on the strongest layout-only byte candidates and keeps
more of the uncertain extended bytes in place. On `R222` it currently exposes
slightly cleaner islands such as `ESC ORPION`, `Honz`, `jPdex`, `Edic1al`,
and `DOďSov`.

For aggregate byte classification across the current known ground-truth slices
there is now also:

```bash
python3 tools/scorpion_affinity.py
```

It compares the known `R010`, tutorial, and `R222` references and prints:

- per-case compact coverage
- `STRONG LAYOUT BYTES`
- `TOP LAYOUT CANDIDATES`

At the moment the strongest layout-only group includes mainly:

- `0x40`
- `0x60`
- `0x9E`
- `0xB0`
- `0xB1`
- `0xB2`
- `0xB3`
- `0xB4`
- `0xC0`
- `0xC1`
- `0xC2`
- `0xC3`
- `0xDB`
- `0xF0`
- `0xF1`
- `0xF2`
- `0xF4`
- `0xF5`
- `0xF6`

For broad start-offset scans against a stitched reference there is now also:

```bash
python3 tools/scorpion_locate.py "/path/to/program.dat" kecy2 reference.txt --start 22000 --stop 23800
```

It scans candidate slice starts and prints the best offsets ordered by a
combined score:

- compact-reference coverage
- penalty when the first matched byte appears too late in the slice
- small bonus for exact compact prefix matches near the start

This is especially useful for pages that do not have a clean `[Rxxx]` marker
and are therefore invisible to the current structural splitter.

For side-by-side comparison against a screenshot-derived reference block:

```bash
python3 tools/scorpion_compare.py "/path/to/program.dat" kecy reference.txt --marker "[R010]"
```

If the screenshot starts later inside the topic, you can shift the compared
slice with `--byte-offset`, for example:

```bash
python3 tools/scorpion_compare.py "/path/to/program.dat" kecy reference.txt --marker "[R010]" --byte-offset 350
```

It prints:

- the reference text
- the current display decode of the same payload slice
- compact alignment stats against the reference text
- candidate control / drop bytes inferred from unmatched payload regions
- frequency counts of suspicious bytes in that slice

## Ground Truth Samples

The following excerpts are kept only as reverse-engineering references. They
must not be injected into exported runtime content unless the underlying codec
is actually decoded.

### `program.dat` / `kecy` / `R010`

Source: screenshot `Scorpion's Cheater 23.0 2026-04-09 at 5.27.39 PM.png`

```text
Sledujte naše WWW stránky, už brzo se na nich objeví nová, revoluční verze
Scorpions Cheatra pro Windows, a tak se jistě nebudete zlobit, když ji v
dnešním editorialu věnujeme trochu víc místa, abyste věděli, na co se můžete
těšit. Tedy především - je to nový a skvělý program, který odbourá všechny
problémy, se kterými se potýkala "stará" DOSovská verze. Samozřejmě, že bude
obsahovat všechny doprovodné texty a funkce, na které jste zvyklí i když
některé texty možná zjednodušíme. Také vyhovíme nátlaku některých z Vás a
upustíme od heslování Jokera. Mysleli jsme si, že je to takový bonbónek,
zábava navíc, aby to nebylo tak fádní a jednoduché, ale jsou mezi Vámi
zřejmě jedinci, pro které je luštění i takto jednoduchých hříček příliš
náročná myslitelská činnost. Další vymožeností nového programu bude
takříkajíc modulové řešení celého projektu. V čem spočívá ? Jde o to, že si
budete moci sami vybrat, které části programu vás zajímají - a proto si je
stáhnete - a které nikoliv. Nejdříve si samozřejmě budete muset stáhnout
základní programový modul, bez toho to nejde, ale potom už to bude jenom na
Vás. Cheaty, eggy, vtipy, návody budou v samostatných knihovnách, které si
budete moci stahovat dle Vašeho vlastního výběru. Navíc připravujeme jednu
speciální knihovnu, ve které budou verze některých návodů s obrázky a také
```

There is now also a fuller stitched reference transcript for the current 23.0
editorial in:

`tools/scorpion_ground_truth/r010-editorial-23.0.txt`

For the beginning of the embedded archive section there is also:

`tools/scorpion_ground_truth/r010-dopisy-z-verze-22.0-opening.txt`

For the menu item `Jak používat cheaty` there is now a stitched screenshot
transcript in:

`tools/scorpion_ground_truth/kecy2-jak-pouzivat-cheaty.txt`

There is now also a dedicated menu dumper for the top-level `program.dat /
seznam` block:

`tools/scorpion_menu_dump.py`

That tool confirms that `seznam` is not just a plain rendered list. It contains
the visible menu labels plus short per-item target blobs. On the current
`program.dat` sample the reconstructed order is:

- `O programu`
- `Editorial a korespondence`
- `Spolupracovali`
- `Kontakt`
- `Historie`
- `Dotazník`
- `Nejčastější otázky & odpovědi`
- `Jak používat cheaty ??`
- `WWW adresy`
- `Minislovník + zkratky`
- `Cheater 2000`
- `Herní servery`

The most important result is that multiple menu entries expose partial or full
target identifiers inside those blobs:

- `O programu` includes clear `R222`
- `Historie` includes clear `204`
- `Dotazník` includes noisy but still recognizable `R00?6`
- `Nejčastější otázky & odpovědi` includes noisy `2?01`
- `Minislovník + zkratky` includes clear `005`

So `seznam` already carries internal navigation metadata, even when the
corresponding page in `kecy` / `kecy2` is too noisy to split safely from its
own payload. The unresolved menu items (`Jak používat cheaty`, `WWW adresy`,
`Cheater 2000`, `Herní servery`) also carry short numeric/control blobs, but
their exact mapping is not yet decoded.

Current lightweight blob hints from `tools/scorpion_menu_dump.py`:

- `Jak používat cheaty ??` -> `3C`
- `WWW adresy` -> `EC7`
- `Herní servery` -> `S99`

These are not trustworthy enough to use as runtime aliases yet, but they are
the first stable per-item signatures for those unresolved menu targets.

The reader also derives a cleaner research-oriented `hint` from the whole menu
slice and exposes it in `metadata.program_menu_hints`. On the current sample
that produces:

- `O programu` -> `R222`
- `Historie` -> `204`
- `Dotazník` -> `R006`
- `Nejčastější otázky & odpovědi` -> `201`
- `WWW adresy` -> `07`
- `Minislovník + zkratky` -> `005`
- `Cheater 2000` -> `2000`
- `Herní servery` -> `99`

Those normalized hints are still only reverse-engineering aids, not verified
runtime targets.

Another important constraint: raw tag inventory inside `program.dat` is much
smaller than the visible program menu suggests. The currently detectable
page-like tags are only:

- `kecy` -> `R010`
- `kecy2` -> `R201`
- `kecy2` -> `R223`
- `seznam` -> `V050`

So pages such as `O programu`, `Historie`, `Dotazník`, `Minislovník + zkratky`,
and `Jak používat cheaty` are not simply recoverable from explicit `[Rxxx]`
markers in the raw payload. At least part of the navigation is routed through
the menu blobs in `seznam`, not through standalone page tags.

There is also a strong cross-file reuse clue: `program.dat / seznam` and
`easter.dat / seznamE` differ in the first 4 bytes, but after that they share
an identical 302-byte prefix. That strongly suggests a common program-wide menu
scaffold with a short per-file variant header.

This block appears to live inside `program.dat` record `kecy2`. The title
itself is still not cleanly recoverable from the payload, but several raw
ASCII anchors are stable inside the same block:

- `Workshop` at byte offset `23590`
- `bpsoft` at byte offset `23636`
- `AITD3` at byte offset `26102`
- `SAVE0` at byte offset `26405`
- `openGL` at byte offset `28434`

A locator scan over `program.dat / kecy2` currently shows two offset clusters:

- high-coverage windows around `22592` / `22656`
- the first clearly tutorial-like windows around `22912` / `22960`

The earlier cluster still looks like preceding noise when inspected directly,
while the `22912..22960` cluster is where the first paragraph starts to become
recognizable (`minule uveřejněný ... qHEX ...`). So the current best practical
candidate start is around byte offset `22912`, but this is not yet reliable
enough to promote to a runtime split.

An additional experiment with the stricter `text-only-strong` drop profile on
the same `22912..22960` cluster still leaves too much carry-over noise from the
preceding block in the first visible lines. In other words, the anchor is good
enough for research, but not yet good enough to ship as a clean runtime topic.

The old synthetic `WWW adresy` topic was removed from the reader because its
search term landed at byte offset `6159` inside the same record and produced a
false-positive garbage page, not a real standalone article.

### `program.dat` / `kecy2` / `R222`

The `O programu` page is already structurally visible as `R222`, but the raw
decode is still very noisy. A screenshot-backed structural reference now lives
in:

`tools/scorpion_ground_truth/r222-o-programu-structure.txt`

This page is especially important because it shows that the payload can carry
more than paragraphs:

- box-drawing / frame-like structures
- a large centered title plaque inside a blue raster field
- colored headings and underlines
- index-style menu formatting
- a large right-side red sprite in the `Několik pozdravů` section

Current profiler run against that structural reference:

- slice start: `program.dat / kecy2` byte offset `13318`
- slice length used for comparison: `7800`
- compact reference coverage: only about `12.7%`

A broad locator scan around this region currently clusters very tightly around:

- `13412`
- `13428`
- `13444`
- `13460`

That is currently the strongest candidate group for the practical beginning of
the `R222 / O programu` slice, even though the payload is still heavily mixed
with layout and art opcodes.

That is much worse than the tutorial-like `Jak používat cheaty` block in the
same record, which reaches about `21.3%` coverage against its stitched text
reference. In practice this strongly suggests that `R222` carries much more
layout / art data inline with the text, not just extra prose with a few opcodes.

The same profiler run repeatedly surfaces these bytes as the strongest
control/layout candidates inside `R222`:

- `0x40` (`@`)
- `0x60` (<code>`</code>)
- `0x80`
- `0x90`
- `0xA0`
- `0xA1`
- `0xB0`
- `0xC0`
- `0xD0`
- `0xE0`
- `0xF0`
- `0xF1`

A smaller subset of these also appears in `Jak používat cheaty`, especially
`0x40`, `0x60`, `0x80`, `0x90`, `0xC0`, `0xE0`, and `0xF0`, which makes them
good candidates for generic formatting/layout bytes rather than page-specific
text corruption.

That strongly suggests the Scorpion codec includes layout and graphic commands,
not just tokenized text. In other words, a future proper reader will likely
need two layers:

1. text decode
2. art / layout decode

From the larger screenshot batch:

- `6.42.43 PM` through `6.42.48 PM` continue the current `R010` editorial
- `6.42.51 PM` already switches into the embedded archive section
  `DOPISY z verze 22.0`
- the repeated top header/footer is window chrome, not duplicated payload text
- in the raw `kecy` payload the ASCII anchor `DOPISY` appears at byte offset
  `33477`, which makes it a good candidate for future structural splitting

The current experimental reader already uses that anchor to split the `kecy`
record into:

- `R010` / `Editorial a korespondence`
- synthetic `D220` / `DOPISY z verze 22.0`

## What Would Be Needed For Reader Support

To improve this from experimental support to a proper reader, the remaining work is:

1. fully decode the `DATA` text stream
2. identify control codes for line breaks, styles, links, and menus
3. improve `seznam` / `seznamE` decoding so menu targets are derived from the
   original payload instead of the current best-effort reconstructed TOC
4. improve title extraction and de-noising for cheat / joke / guide pages
5. map the result into UHF topics, index entries, and contents

The record container itself is already simple enough to parse.

## Related Context

Background on the application family:

- Scorpion's WinCheater / DOS Cheater overview:
  https://encyklopedia.sk/encyklopedia/index.php?pojem=Scorpion%E2%80%99s_WinCheater&veda=5403

Notable clue from that article:

- the DOS application had a companion tool called **Scorpion's RTF Editor**
  that edited text into the exact format later used by the program

That strongly suggests the text stream is not a standard help format, but a
project-specific editorial format.
