"""Scorpion PROGRAM text screens: native cells, attributes and bitmap fonts."""

from __future__ import annotations

from pathlib import Path

from ..text_screen import BitmapFont, TextScreen
from ..codepages import KAMENICKY
from .scorpion_dat_parser import ScorpionDatRecord
from .scorpion_lzhuf import ScorpionLzhufDecoder

_SCREEN_NAMES = frozenset({"_main", "egg", "obr1", "obr2", "obr3", "obr4",
                           "obrview", "pirat", "scroll", "xicht"})
# The complete v15 font table and screens are byte-identical to v16's objects.
_V15_NAMES = frozenset({"obr1", "obr3", "obr15", "obr16", "obr17", "obr18",
                        "obr19", "obr21", "obr24"})


def inline_text_screen(cells: tuple[tuple[int, int, int], ...], text: str, font_id: str) -> TextScreen | None:
    """One authored artwork row, in place; never associate a separate picture."""
    if (not cells or len(cells) > 80
            or not any(0xB0 <= glyph <= 0xDF or glyph == 0x99 for glyph, _, _ in cells)):
        return None
    return TextScreen(80, 1, cells + ((32, 7, 0),) * (80 - len(cells)), font_id,
                      text=(text,), cell_format="dos-text")


def decode_text_screen(cells: bytes, font_id: str, *, cell_format: str = "dos-text") -> TextScreen:
    if len(cells) != 4000:
        raise ValueError("Scorpion screens require exactly 80×25 character/attribute cells")
    if cell_format not in {"dos-text", "dos-text-blink", "dos-text-bright"}:
        raise ValueError("Invalid Scorpion text attribute mode")
    if cell_format == "dos-text" and any(attr & 0x80 for attr in cells[1::2]):
        raise ValueError("Scorpion screen blink/bright-background binding is unverified")
    text = []
    for row in range(25):
        codes = cells[row * 160:(row + 1) * 160:2]
        text.append("".join(KAMENICKY.get(code, chr(code)) if code >= 32 else " "
                            for code in codes).rstrip())
    return TextScreen(80, 25, tuple((code, attr & 15, (attr >> 4) & (15 if cell_format == "dos-text-bright" else 7))
                                  for code, attr in zip(cells[::2], cells[1::2])),
                      font_id, text=tuple(text), cell_format=cell_format,
                      blink=tuple(bool(attr & 128) for attr in cells[1::2]) if cell_format == "dos-text-blink" else ())


def modern_screens(records: list[ScorpionDatRecord]) -> tuple[BitmapFont | None, list[tuple[ScorpionDatRecord, TextScreen]]]:
    by_name = {record.name.lower(): record for record in records}
    font = by_name.get("font1")
    names = _SCREEN_NAMES
    if font is None:
        # Establish the older table before interpreting its positional obr* names.
        if not all(name in by_name and len(by_name[name].payload) == 4096
                   for name in (f"obr{i}" for i in range(4, 13))):
            return None, []
        font = by_name["obr4"]
        names = _V15_NAMES
    screens = [record for record in records if record.name.lower() in names]
    if not screens:
        return None, []
    bitmap_font = BitmapFont(8, 16, font.payload)
    return bitmap_font, [(record, decode_text_screen(record.payload, "program-font")) for record in screens]


def decode_resource_bank(data: bytes, marker: bytes, size: int) -> list[bytes]:
    """Decode native FNT/SCR records, bounded by their next complete frame."""
    signature = marker + size.to_bytes(4, "little")
    if not data.startswith(signature):
        raise ValueError("Invalid Scorpion resource bank header")
    offsets = [0]
    while (offset := data.find(signature, offsets[-1] + len(signature))) >= 0:
        offsets.append(offset)
    result = []
    for start, end in zip(offsets, offsets[1:] + [len(data)]):
        block = data[start + len(marker):end]
        decoded, position, _ = ScorpionLzhufDecoder(block, 0).decode()
        if position != len(block):
            raise ValueError("Unconsumed Scorpion resource payload")
        result.append(decoded)
    return result


def legacy_default_font(directory: Path, version: float) -> BitmapFont | None:
    names = {path.name.upper(): path for path in directory.iterdir()} if directory.is_dir() else {}
    path = names.get("FA.SCO" if version < 9 else "FONT.SCO")
    if path is None:
        return None
    if path.is_symlink():
        raise ValueError("Scorpion companion fonts must not be symbolic links")
    raw = path.read_bytes()
    if version < 9:
        if len(raw) != 4223:
            raise ValueError("Invalid Scorpion FA.SCO font length")
        return BitmapFont(8, 16, raw[127:])
    fonts = decode_resource_bank(raw, b"FNT", 4096)
    if len(fonts) != 7:
        raise ValueError("Scorpion FONT.SCO requires seven fonts")
    return BitmapFont(8, 16, fonts[1])


def legacy_screens(directory: Path, version: float) -> tuple[dict[str, BitmapFont], list[tuple[str, TextScreen]], list[str]]:
    """Read companions; v6 retains the standard blink-enabled DOS text mode."""
    by_name = {path.name.upper(): path for path in directory.iterdir() if path.is_file()}
    fonts = {}
    resources = []
    if 6 <= version < 9:
        paths = sorted((path for name, path in by_name.items()
                        if name.startswith("SCR") and name[3:-4].isdigit() and name.endswith(".SCD")),
                       key=lambda path: int(path.stem[3:]))
        if not paths:
            return {}, [], []
        for name, path in by_name.items():
            if name in {"FOK.SCO", *(f"F{letter}.SCO" for letter in "ABCDEF")}:
                if path.is_symlink():
                    raise ValueError("Scorpion companion fonts must not be symbolic links")
                raw = path.read_bytes()
                if len(raw) != 4223:
                    raise ValueError(f"Invalid Scorpion font length: {path.name}")
                fonts["program-font" if name == "FA.SCO" else path.stem.lower()] = BitmapFont(8, 16, raw[127:])
        if "program-font" not in fonts:
            raise ValueError("Scorpion screen default FA.SCO font is missing")
        font_id = "program-font"
        for path in paths:
            if path.is_symlink():
                raise ValueError("Scorpion companion screens must not be symbolic links")
            raw = path.read_bytes()
            if raw[:4] != (4000).to_bytes(4, "little"):
                raise ValueError(f"Invalid Scorpion screen header: {path.name}")
            decoded, position, _ = ScorpionLzhufDecoder(raw, 0).decode()
            if position != len(raw):
                raise ValueError(f"Unconsumed Scorpion screen payload: {path.name}")
            resources.append((path.name, decoded))
    elif 10 <= version <= 14:
        path = by_name.get("SCREENS.SCO")
        if path is None:
            return {}, [], []
        font_path = by_name.get("FONT.SCO")
        if font_path is None:
            raise ValueError("Scorpion screen FONT.SCO bank is missing")
        if path.is_symlink() or font_path.is_symlink():
            raise ValueError("Scorpion companion resources must not be symbolic links")
        fonts = {"program-font" if i == 1 else f"font-{i}": BitmapFont(8, 16, raw)
                 for i, raw in enumerate(decode_resource_bank(font_path.read_bytes(), b"FNT", 4096))}
        if len(fonts) != 7:
            raise ValueError("Scorpion FONT.SCO requires seven fonts")
        font_id = "program-font"
        resources = [(f"SCREENS.SCO/{i}", raw)
                     for i, raw in enumerate(decode_resource_bank(path.read_bytes(), b"SCR", 4000))]
    else:
        return {}, [], []
    has_blink = lambda raw: any(attr & 128 for attr in raw[1::2])
    deferred = [name for name, raw in resources if has_blink(raw) and version != 6]
    # Animated templates follow static ones, keeping existing resource topics
    # and aliases stable when previously unsupported bit-7 screens are added.
    resources.sort(key=lambda item: has_blink(item[1]))
    return fonts, [(name, decode_text_screen(raw, font_id,
                   cell_format="dos-text-blink" if has_blink(raw) else "dos-text"))
                   for name, raw in resources if name not in deferred], deferred
