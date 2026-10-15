"""Verified Software602 graphics-font cells and inline style categories."""

from itertools import groupby
import re

from ..uhf_markup import UhfStyleSpan, render_uhf_line


GRAPHICS_STYLE_CATEGORIES = {0x02: 2, 0x04: 1, 0x13: 0x20}
# These native selectors change cell dimensions, not merely emphasis.
GRAPHICS_SIZE_SELECTORS = {0x0F, 0x14, 0x16}

# The common high glyphs also match Text602/Calc602's HELP screen drivers.
# They are not a Kamenicky/CP437 character table.
# A row supplies the high nibble, a position supplies the low nibble. Blank
# glyph slots are spaces; standalone accents are spacing Unicode characters.
_GRAPHICS_HIGH = (
    "Çùè§ß£ÆØÅæøå· ¤ò"
    "ìÞ¡Ñ¿ñ█▄▀·······"
    "≡±≥≤⌠⌡÷≈°√²½¼■«»"
    "αβΓπΣσµτΦΘΩδ∞φε∩"
    "┌á└čďěŕ─üíůĺľöňó"
    "ôäřšťú├éàýž┬ˇ´˚┼"
    "┐Á┘ČĎĚŔ│ÜÍŮĹĽÖŇÓ"
    "ÔÄŘŠŤÚ┤ÉÀÝŽ┴¨^-·"
)
_GRAPHICS_LOW = {
    0x05: "┓", 0x06: "━", 0x07: "╭", 0x08: "╮", 0x09: "╰",
    0x0A: "╯", 0x0B: "│", 0x0C: "─", 0x0D: "↵",
    0x11: "“", 0x12: "„", 0x15: "│", 0x17: "↨", 0x18: "↑",
    0x19: "↓", 0x1A: "→", 0x1B: "←", 0x1C: "└", 0x1D: "↔",
    0x1E: "√", 0x1F: "±",
}

# Low HELP glyphs shared by both drivers. The remaining low slots include
# boxed keys and revision-dependent icons; do not assign CP437 smileys to them.
_HELP_LOW = {value: glyph for value, glyph in _GRAPHICS_LOW.items()
             if value not in (0x11, 0x12, 0x15)}
_HELP_LOW.update({0x04: "┏", 0x13: "┳"})


def decode_graphics_cells(raw_line: bytes) -> list[tuple[int, int]]:
    """Return literal font-byte/category cells for one native stored row."""
    cells: list[tuple[int, int]] = []
    category = 0
    for value in raw_line:
        if value in GRAPHICS_SIZE_SELECTORS:
            raise ValueError(f"Unsupported Software602 font-size selector {value:02X}h.")
        if value in GRAPHICS_STYLE_CATEGORIES:
            selected = GRAPHICS_STYLE_CATEGORIES[value]
            category = 0 if category == selected else selected
            continue
        cells.append((value, category))
    return cells


def render_graphics_line(raw_line: bytes) -> str:
    cells = decode_graphics_cells(raw_line)
    text = "".join(decode_graphics_byte(value) for value, _category in cells)
    styles: list[UhfStyleSpan] = []
    position = 0
    for category, group in groupby(cells, key=lambda cell: cell[1]):
        end = position + sum(1 for _ in group)
        if category:
            styles.append(UhfStyleSpan(position, end, bold=category == 2,
                                       italic=category == 1, underline=category == 0x20))
        position = end
    return render_uhf_line(text, style_spans=styles)


def plain_graphics_line(raw_line: bytes) -> str:
    text = "".join(decode_graphics_byte(value) for value, _category in decode_graphics_cells(raw_line))
    return re.sub(r"\s+", " ", text).strip()


def decode_graphics_byte(value: int) -> str:
    if value < 0x20:
        # Untranscribed boxed-key/compound glyphs occupy a cell, never vanish.
        return _GRAPHICS_LOW.get(value, "\uFFFD")
    if value < 0x80:
        return "⌂" if value == 0x7F else chr(value)
    return _GRAPHICS_HIGH[value - 0x80]


def decode_help_byte(value: int) -> str:
    """Transcribe one literal THelpTopic screen cell, without style selectors."""
    if value < 0x20:
        return _HELP_LOW.get(value, "\uFFFD")
    # FF is the paragraph format's non-breaking separator. Normalize it only
    # after native wrapping/range positioning, not to the driver's marker stroke.
    return " " if value == 0xFF else decode_graphics_byte(value)
