"""Native character-cell screens and bitmap fonts carried by UHF."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import re

SCREEN_LINE = re.compile(r"^\[screen:([A-Za-z0-9_-]{1,64})\]$")


@dataclass(frozen=True, slots=True)
class BitmapFont:
    """256 byte-addressed glyphs, scanlines top-down and bits left-to-right."""

    width: int
    height: int
    data: bytes

    def __post_init__(self) -> None:
        if (type(self.width) is not int or not 1 <= self.width <= 32
                or type(self.height) is not int or not 1 <= self.height <= 64
                or not isinstance(self.data, bytes)
                or len(self.data) != 256 * self.height * ((self.width + 7) // 8)):
            raise ValueError("Invalid bitmap font dimensions/length")

    def to_dict(self) -> dict[str, object]:
        return {"width": self.width, "height": self.height,
                "data": base64.b64encode(self.data).decode("ascii")}


@dataclass(frozen=True, slots=True)
class TextScreen:
    """Row-major (glyph byte, foreground index, background index) cells."""

    cols: int
    rows: int
    cells: tuple[tuple[int, int, int], ...]
    font: str
    palette: str = "cga"
    text: tuple[str, ...] = ()
    cell_format: str | None = None
    blink: tuple[bool, ...] = ()

    def __post_init__(self) -> None:
        if (type(self.cols) is not int or not 1 <= self.cols <= 512
                or type(self.rows) is not int or not 1 <= self.rows <= 512
                or len(self.cells) != self.cols * self.rows):
            raise ValueError("Invalid text screen dimensions/cell count")
        if any(len(cell) != 3 or any(type(value) is not int or not 0 <= value <= 255 for value in cell)
               for cell in self.cells):
            raise ValueError("Text screen cells require glyph/foreground/background byte indexes")
        if (not isinstance(self.font, str) or not SCREEN_LINE.fullmatch(f"[screen:{self.font}]")
                or not isinstance(self.palette, str)
                or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", self.palette)):
            raise ValueError("Invalid text screen font/palette reference")
        if self.text and (len(self.text) != self.rows
                          or any(not isinstance(line, str) or "\n" in line or "\r" in line for line in self.text)):
            raise ValueError("Text screen transcription must have one literal string per row")
        if self.cell_format not in (None, "glyph-fg-bg", "dos-text", "dos-text-blink", "dos-text-bright"):
            raise ValueError("Invalid text screen packed-cell format")
        if self.blink and (len(self.blink) != len(self.cells) or any(type(flag) is not bool for flag in self.blink)):
            raise ValueError("Text screen blink mask requires one boolean per cell")
        if self.cell_format and self.cell_format.startswith("dos-text"):
            limit = 15 if self.cell_format == "dos-text-bright" else 7
            if any(fg > 15 or bg > limit for _, fg, bg in self.cells):
                raise ValueError("DOS text attributes have invalid foreground/background indexes")
            if any(self.blink) and self.cell_format != "dos-text-blink":
                raise ValueError("DOS blink bits require the explicit dos-text-blink format")

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"cols": self.cols, "rows": self.rows, "font": self.font,
                                     "palette": self.palette}
        if self.cell_format is None:
            result["cells"] = [list(cell) for cell in self.cells]
        else:
            dos = self.cell_format.startswith("dos-text")
            data = bytes(value for index, (glyph, fg, bg) in enumerate(self.cells)
                         for value in ((glyph, fg | bg << 4 | (128 if self.blink and self.blink[index] else 0))
                                       if dos else (glyph, fg, bg)))
            result.update(cell_format=self.cell_format, data=base64.b64encode(data).decode("ascii"))
        if any(self.blink) and (self.cell_format is None or self.cell_format == "glyph-fg-bg"):
            result["blink"] = list(self.blink)
        if self.text:
            result["text"] = list(self.text)
        return result


def screen_text_lines(bundle: dict, line: str) -> list[str] | None:
    """Literal transcription for search; glyph/color data is never indexed."""
    match = SCREEN_LINE.fullmatch(line)
    screens = bundle.get("text_screens")
    screen = screens.get(match[1]) if match and isinstance(screens, dict) else None
    if not isinstance(screen, dict):
        return None
    text = screen.get("text")
    if (not isinstance(text, list) or len(text) != screen.get("rows")
            or any(not isinstance(row, str) for row in text)):
        return None
    return text
