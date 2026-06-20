# THelp Viewer — Bundle Transport

> Updated: 2026-04-08

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

## 2. Loading Flow

1. The viewer loads `helps/catalog.json`.
2. When the user opens a help file, the viewer fetches the matching
   `.json.gz` bundle.
3. The downloaded bytes are decompressed in the browser with
   `DecompressionStream("gzip")`.
4. The resulting UTF-8 text is parsed as JSON.
5. The UHF 2.0 payload is rendered into the TurboVision-style window UI.

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
