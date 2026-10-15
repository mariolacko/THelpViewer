# FreeDOS HTML Help (HHSTNDRD) Format

> Created: 2026-09-29 · Last updated: 2026-10-12

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
<h2><a name="syntax">Syntax:</a></h2>
<pre>  EXAMPLE [options]</pre>
<a href="#syntax">Back to syntax</a>
<a href="../help/help.htm">HTMLHELP</a>
</body>
</html>
```

The file path is part of link resolution. For example, a relative link
from `base/append.htm` to `../command/environm.htm` targets the
`command/` directory. Some links include `#fragment` identifiers for
a location within the destination page. These are HTML links, not numeric
topic offsets or an external link table.

The original `authors/tags.htm` documents the viewer's `HREF` and `NAME`
attributes. The inspected archive has 154 `<a name="…">` destinations and
116 fragment-bearing hrefs. A named anchor without `href` is a bookmark,
not an extra clickable link. These definitions can precede visible text,
occur inside headings or sit within a preformatted line.

## Character encoding and navigation

The sampled English files use UTF-8 text and HTML entities. Their
preformatted blocks rely on preserved spaces and line breaks, while text
outside `<pre>` follows ordinary HTML whitespace rules. The DOS
`HTMLHELP` viewer uses a help path and opens `index.htm` by default;
the viewer's `/L` option opens another page relative to that path.
The format is therefore a directory tree of pages rather than one fixed
binary record stream.

One original page, `authors/ack.htm`, contains a standalone byte `81` despite
declaring UTF-8. This is not a valid UTF-8 sequence. The intended character and any alternative source encoding are not established.

## Link resolution

Resolve `href` relative to the containing page's directory, then apply any
fragment. A fragment names a destination, not a numeric context or line number.
Named anchors declare `name`; standard HTML elements may also declare `id`.
An anchor without `href` does not create an outgoing link.

The member paths follow DOS case-insensitive lookup. Percent-escaped references
must be decoded before matching; path case rules do not merge distinct fragment
names. Missing pages and missing fragments are different cases. The absent
root `index.htm` is not the real `help/index.htm` member.

Inline elements may span physical source lines. Inside `<pre>`, spaces and
line endings affect display; outside it they follow HTML whitespace rules.
Tables, emphasis and anchors are HTML markup, not binary HELP records.

For ordinary English flowing text, display whitespace processing collapses
U+0020 spaces, U+0009 tabs and source line breaks (U+000A/U+000D) into a
single separator. This continues across inline element boundaries, comments
and empty named anchors; a block boundary does not carry a pending separator
into the next block. Leading/trailing collapsible separators do not create
display cells. For example, `DOS <a name="ext">Extenders</a>:` displays
`DOS Extenders:`, while `one<b>two</b>` has no authored word separator.

`&nbsp;` decodes to U+00A0 (UTF-8 `C2 A0`) and is not a collapsible U+0020
space. Other Unicode space separators must not be erased by a general Unicode
whitespace split. Text-flow whitespace is distinct from HTML lexical
whitespace; in particular U+000C is not one of the collapsible text characters
above. Its exact DOS viewer glyph/control behavior is not established here.
See the [standard text whitespace processing rules](https://www.w3.org/TR/css-text-3/#white-space-rules).

## Distribution and source identification

The inspected English archive has CRC32 `3F1A2C97`. `FDL.TXT` and
`COPYING` are licence documents, not an index or compression table.
