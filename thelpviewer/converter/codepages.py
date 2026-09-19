"""Codepage helpers used by readers and the HTML renderer."""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

CP437_LOW = {
    0x01: "\u263A", 0x02: "\u263B", 0x03: "\u2665", 0x04: "\u2666",
    0x05: "\u2663", 0x06: "\u2660", 0x07: "\u2022", 0x08: "\u25D8",
    0x0B: "\u2642", 0x0C: "\u2640", 0x0E: "\u266B", 0x0F: "\u263C",
    0x10: "\u25BA", 0x11: "\u25C4", 0x12: "\u2195", 0x13: "\u203C",
    0x14: "\u00B6", 0x15: "\u00A7", 0x16: "\u25AC", 0x17: "\u21A8",
    0x18: "\u2191", 0x19: "\u2193", 0x1A: "\u2192", 0x1B: "\u2190",
    0x1C: "\u221F", 0x1D: "\u2194", 0x1E: "\u25B2", 0x1F: "\u25BC",
}

KAMENICKY = {
    0x80: "\u010C", 0x81: "\u00FC", 0x82: "\u00E9", 0x83: "\u010F",
    0x84: "\u00E4", 0x85: "\u010E", 0x86: "\u0164", 0x87: "\u010D",
    0x88: "\u011B", 0x89: "\u011A", 0x8A: "\u0139", 0x8B: "\u00CD",
    0x8C: "\u013E", 0x8D: "\u013A", 0x8E: "\u00C4", 0x8F: "\u00C1",
    0x90: "\u00C9", 0x91: "\u017E", 0x92: "\u017D", 0x93: "\u00F4",
    0x94: "\u00F6", 0x95: "\u00D3", 0x96: "\u016F", 0x97: "\u00DA",
    0x98: "\u00FD", 0x99: "\u00D6", 0x9A: "\u00DC", 0x9B: "\u0160",
    0x9C: "\u013D", 0x9D: "\u00DD", 0x9E: "\u0158", 0x9F: "\u0165",
    0xA0: "\u00E1", 0xA1: "\u00ED", 0xA2: "\u00F3", 0xA3: "\u00FA",
    0xA4: "\u0148", 0xA5: "\u0147", 0xA6: "\u016E", 0xA7: "\u00D4",
    0xA8: "\u0161", 0xA9: "\u0159", 0xAA: "\u0155", 0xAB: "\u0154",
    0xAC: "\u00BC", 0xAD: "\u00A7", 0xAE: "\u00AB", 0xAF: "\u00BB",
    0xB0: "\u2591", 0xB1: "\u2592", 0xB2: "\u2593", 0xB3: "\u2502",
    0xB4: "\u2524", 0xB5: "\u2561", 0xB6: "\u2562", 0xB7: "\u2556",
    0xB8: "\u2555", 0xB9: "\u2563", 0xBA: "\u2551", 0xBB: "\u2557",
    0xBC: "\u255D", 0xBD: "\u255C", 0xBE: "\u255B", 0xBF: "\u2510",
    0xC0: "\u2514", 0xC1: "\u2534", 0xC2: "\u252C", 0xC3: "\u251C",
    0xC4: "\u2500", 0xC5: "\u253C", 0xC6: "\u255E", 0xC7: "\u255F",
    0xC8: "\u255A", 0xC9: "\u2554", 0xCA: "\u2569", 0xCB: "\u2566",
    0xCC: "\u2560", 0xCD: "\u2550", 0xCE: "\u256C", 0xCF: "\u2567",
    0xD0: "\u2568", 0xD1: "\u2564", 0xD2: "\u2565", 0xD3: "\u2559",
    0xD4: "\u2558", 0xD5: "\u2552", 0xD6: "\u2553", 0xD7: "\u256B",
    0xD8: "\u256A", 0xD9: "\u2518", 0xDA: "\u250C", 0xDB: "\u2588",
    0xDC: "\u2584", 0xDD: "\u258C", 0xDE: "\u2590", 0xDF: "\u2580",
    0xE0: "\u03B1", 0xE1: "\u00DF", 0xE2: "\u0393", 0xE3: "\u03C0",
    0xE4: "\u03A3", 0xE5: "\u03C3", 0xE6: "\u00B5", 0xE7: "\u03C4",
    0xE8: "\u03A6", 0xE9: "\u0398", 0xEA: "\u03A9", 0xEB: "\u03B4",
    0xEC: "\u221E", 0xED: "\u03C6", 0xEE: "\u03B5", 0xEF: "\u2229",
    0xF0: "\u2261", 0xF1: "\u00B1", 0xF2: "\u2265", 0xF3: "\u2264",
    0xF4: "\u2320", 0xF5: "\u2321", 0xF6: "\u00F7", 0xF7: "\u2248",
    0xF8: "\u00B0", 0xF9: "\u2219", 0xFA: "\u00B7", 0xFB: "\u221A",
    0xFC: "\u207F", 0xFD: "\u00B2", 0xFE: "\u25A0", 0xFF: "\u00A0",
}

DEFAULT_DISPLAY_ENCODING = "cp437"

# Bytes that are box-drawing in CP437 but Czech/Slovak letters in CP852.
# When these bytes appear adjacent to unambiguous box-drawing bytes in a
# CP852-encoded file, they were almost certainly intended as box-drawing.
CP852_BOX_CONFLICTS: dict[int, str] = {
    0xB5: "\u2561",  # ╡   CP852=Á
    0xB6: "\u2562",  # ╢   CP852=Â
    0xB7: "\u2556",  # ╖   CP852=Ě
    0xB8: "\u2555",  # ╕   CP852=Ş
    0xBD: "\u255C",  # ╜   CP852=Ż
    0xBE: "\u255B",  # ╛   CP852=ż
    0xC6: "\u255E",  # ╞   CP852=Ă
    0xC7: "\u255F",  # ╟   CP852=ă
    0xCF: "\u2567",  # ╧   CP852=¤
    0xD0: "\u2568",  # ╨   CP852=đ
    0xD1: "\u2564",  # ╤   CP852=Đ
    0xD2: "\u2565",  # ╥   CP852=Ď
    0xD3: "\u2559",  # ╙   CP852=Ë
    0xD4: "\u2558",  # ╘   CP852=ď
    0xD5: "\u2552",  # ╒   CP852=Ň
    0xD6: "\u2553",  # ╓   CP852=Í
    0xD7: "\u256B",  # ╫   CP852=Î
    0xD8: "\u256A",  # ╪   CP852=ě
    0xDD: "\u258C",  # ▌   CP852=Ţ (Romanian, not Czech)
    0xDE: "\u2590",  # ▐   CP852=Ů (Czech, but only box-drawing when adjacent)
}

# Bytes that are unambiguously box-drawing in both CP852 and CP437.
_SAFE_BOX_BYTES = frozenset(
    {0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB9, 0xBA, 0xBB, 0xBC, 0xBF,
     0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC8, 0xC9, 0xCA, 0xCB,
     0xCC, 0xCD, 0xCE, 0xD9, 0xDA, 0xDB, 0xDC, 0xDF}
)

_BOX_CONTEXT_BYTES = _SAFE_BOX_BYTES | CP852_BOX_CONFLICTS.keys()
CZECH_HINT_ENCODINGS = ("kamenicky", "cp852", "latin2", "cp437", "latin1")
CZECH_SCORE_CHARS = set(
    "áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
    "ľĺäôĽĹÄÔ"
)
CZECH_SCORE_WORDS = (
    "nápově",
    "vyhrazen",
    "příkaz",
    "řádk",
    "hlášen",
    "chybov",
    "uživatel",
    "proměnn",
    "spoušt",
    "správ",
    "jednotk",
    "obecn",
    "pomocn",
    "vstup",
    "výstup",
    "nástroj",
    "kód",
)
SUSPICIOUS_MOJIBAKE = set("ąćęłńśźżĄĆĘŁŃŚŹŻŢţ¤×çÇëËƒÿŸ")


@lru_cache(maxsize=None)
def _cached_decode_table(from_enc: str, to_enc: str | None) -> tuple[str, ...]:
    """Return an immutable cached byte-to-text lookup table."""
    if to_enc is None:
        return tuple(chr(i) for i in range(256))
    table: list[str] = []
    for i in range(32):
        table.append(CP437_LOW.get(i, chr(i)))
    for i in range(32, 128):
        table.append(chr(i))
    if from_enc == "kamenicky":
        for i in range(128, 256):
            table.append(KAMENICKY.get(i, chr(i)))
    else:
        encoding = "latin-1" if from_enc == "latin1" else from_enc
        for i in range(128, 256):
            table.append(bytes([i]).decode(encoding, errors="replace"))
    return tuple(table)


def build_decode_table(from_enc: str, to_enc: str | None) -> list[str]:
    """Build a mutable byte-to-text lookup table for the requested encoding."""
    return list(_cached_decode_table(from_enc, to_enc))


def decode_bytes(data: bytes, encoding: str) -> str:
    """Decode a raw byte string with the project-specific lookup rules."""
    table = _cached_decode_table(encoding, "unicode")
    return "".join(table[value] for value in data if value != 0x00)


def decode_bytes_box_aware(data: bytes, encoding: str) -> str:
    """Like *decode_bytes* but fix CP852 box-drawing ambiguities.

    In CP852, bytes 0xB5-0xD8 overlap between Czech letters and CP437
    box-drawing characters.  When such a byte is adjacent to an
    unambiguous box-drawing byte, it is decoded as a box-drawing glyph
    instead of a Czech letter.
    """
    if encoding != "cp852":
        return decode_bytes(data, encoding)
    table = _cached_decode_table(encoding, "unicode")
    has_left_block = 0xDD in data
    has_right_block = 0xDE in data
    out: list[str] = []
    length = len(data)
    for i, value in enumerate(data):
        if value == 0x00 or value == 0x0D:
            continue
        if value in CP852_BOX_CONFLICTS:
            prev = data[i - 1] if i > 0 else 0
            nxt = data[i + 1] if i + 1 < length else 0
            # Czech CP852 help files often use CP437 block glyphs as
            # title decorations. 0xDD is Romanian in CP852, not Czech,
            # and 0xDE is the matching right block when the line also
            # contains 0xDD.
            if (
                value == 0xDD
                or (value == 0xDE and has_left_block and has_right_block)
                or prev in _BOX_CONTEXT_BYTES
                or nxt in _BOX_CONTEXT_BYTES
            ):
                out.append(CP852_BOX_CONFLICTS[value])
                continue
        out.append(table[value])
    return "".join(out)


def guess_display_encoding(chunks: Iterable[bytes], hint: str = "") -> str:
    """Pick the most plausible display encoding for a set of text chunks."""
    sample = [chunk for chunk in chunks if chunk]
    is_czech_hint = _looks_czech_hint(hint)
    if not is_czech_hint:
        return DEFAULT_DISPLAY_ENCODING
    if not sample:
        return "kamenicky"

    candidates = CZECH_HINT_ENCODINGS
    scores = {encoding: _score_chunks(sample, encoding) for encoding in candidates}
    best_score = max(scores.values())
    if best_score <= 0:
        return "kamenicky"

    for encoding in candidates:
        if scores[encoding] == best_score:
            return encoding
    return DEFAULT_DISPLAY_ENCODING


def is_czech_encoding_hint(hint: str) -> bool:
    """Public helper used by export code when Czech DOS code pages are plausible."""
    return _looks_czech_hint(hint)


def _looks_czech_hint(hint: str) -> bool:
    """Treat CZ/602 file names as candidates for Czech DOS code pages."""
    upper_hint = hint.upper()
    return "CZ" in upper_hint or "602" in upper_hint


def _score_chunks(chunks: list[bytes], encoding: str) -> int:
    """Prefer decodings that produce Czech words and penalize mojibake."""
    score = 0
    for chunk in chunks:
        text = decode_bytes(chunk, encoding)
        lowered = text.lower()
        score += sum(lowered.count(word) for word in CZECH_SCORE_WORDS) * 24
        score += sum(character in CZECH_SCORE_CHARS for character in text) * 4
        score -= sum(character in SUSPICIOUS_MOJIBAKE for character in text) * 8
        score -= sum(0x80 <= ord(character) <= 0x9F for character in text) * 32
        score -= text.count("\ufffd") * 32
    return score
