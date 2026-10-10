# FreeDOS HTML Help (HHSTNDRD) Format

> Created: 2026-09-29 · Last updated: 2026-09-29

FreeDOS `HELP` / `HTMLHELP` displays a collection of linked HTML pages.
The help texts are ordinary `.htm` files distributed inside
`HHSTNDRD.ZIP`; this is not Microsoft CHM or another compiled help
database. The [FreeDOS help documentation](https://help.fdos.org/en/hhstndrd/help/help.htm)
describes the DOS viewer, the collection name and language selection.

## Package and page layout

The English 1.1.1a archive contains **354 HTML pages**. Members are stored
under topic directories such as `base/`, `batch/`, `command/`,
`network/`, `util/` and `help/`. Directories may include their own
`index.htm`. The archive has `help/index.htm`, but no root
`index.htm`; links to the latter occur in some pages.

Each page is a normal HTML document with a `<head>`, a `<title>` and a
`<body>`. The sampled pages declare UTF-8 using a content-type meta tag.
They use `<h1>` / `<h2>` headings, `<pre>` blocks for fixed-width DOS
syntax and examples, and `<a href="...">` for navigation. Some pages
also use ordinary paragraphs, lists and tables.

Representative structure, simplified from the observed pages:

```html
<!DOCTYPE html>
<html lang="en">
<head><title>FreeDOS command: example</title></head>
<body>
<h1>Command: example</h1>
<h2>Syntax:</h2>
<pre>  EXAMPLE [options]</pre>
<a href="../help/help.htm">HTMLHELP</a>
</body>
</html>
```

The file path is part of link resolution. For example, a relative link
from `base/append.htm` to `../command/environm.htm` targets the
`command/` directory. Some links include `#fragment` identifiers for
a location within the destination page. These are HTML links, not numeric
topic offsets or an external link table.

## Character encoding and navigation

The sampled English files use UTF-8 text and HTML entities. Their
preformatted blocks rely on preserved spaces and line breaks, while text
outside `<pre>` follows ordinary HTML whitespace rules. The DOS
`HTMLHELP` viewer uses a help path and opens `index.htm` by default;
the viewer's `/L` option opens another page relative to that path.
The format is therefore a directory tree of pages rather than one fixed
binary record stream.

## THelpViewer mapping

`freedos_html.py` recognizes a ZIP named `HHSTNDRD.ZIP` with a ZIP
signature and a `help/index.htm` member. It reads entries in memory
without extracting files. Each HTML page becomes one UHF topic. Page
`<title>` text becomes its index label, parent directories become
Contents groups, and sorted member paths determine stable numeric topic
IDs. `help/index.htm` is marked as the help-contents topic.

Relative page links are normalized against the current page and become
UHF links when the destination member exists. The observed English
archive yields **4,286 links** to existing topic IDs. Its 22 links to
the absent root `index.htm` remain plain text rather than being pointed
at an invented topic.

The importer preserves preformatted text, headings, paragraphs, basic
bold emphasis and table-cell text. It is not a full browser: CSS,
images and scripts are not rendered, and links with `#fragment` currently
open the destination page rather than its exact anchor line. The reader
also enforces page-count and uncompressed-size limits as a safety measure;
those are THelpViewer limits, not properties of the FreeDOS format.

## Distribution and source identification

The known archive has CRC32 `3F1A2C97` in
`thelpviewer/config/help-database.json`. `FDL.TXT` and `COPYING` are kept
with the downloaded package as license materials, not imported as help
topics. The selected FreeDOS package lists an
[Express + GNU Free Documentation License copying policy](https://ibiblio.org/pub/micro/pc-stuff/freedos/files/repositories/latest/html/en/base/htmlhelp/20251203.4/index.html).
This product remains outside the default public build until its
redistribution obligations and included notices are reviewed.
