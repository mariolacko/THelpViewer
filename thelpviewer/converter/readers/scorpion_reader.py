"""Shared helpers and dispatch for Scorpions Cheater readers."""

from __future__ import annotations

from pathlib import Path
import re

from ..base import HelpDocument, HelpReaderBase
from ..codepages import KAMENICKY


SCORPION_TEXT_ENCODING = "kamenicky"
SCORPION_VERSION_DIR_RE = re.compile(r"^Scorpions Cheater (?P<version>\d+(?:\.\d+)?)(?:\s.*)?$")
SCORPION_LEGACY_CONTAINER_STEMS = frozenset({"DATA", "CHEATER", "MAIN"})
SCORPION_DISPLAY_COLUMNS = 80
SCORPION_RENDER_TAB_TEXT = "        "
SCORPION_RESET_CONTROL = 0xED
SCORPION_LINE_BREAK_CONTROL = 0xFA
SCORPION_SOFT_BREAK_BYTE = 0xFB
SCORPION_BACKGROUND_RESET_CONTROL = 0xF6
SCORPION_BACKGROUND_CONTROLS = {
    0xE5: 7,  # gray background in block artwork
    0xF7: 1,  # blue background/highlight
}
SCORPION_STYLE_CONTROLS = {
    0xE7: 1,   # blue
    0xE8: 2,   # green emphasis/secondary value
    0xE9: 3,   # cyan label/value
    0xEA: 4,   # red
    0xEB: 5,   # magenta emphasis/code in early releases
    0xEC: 6,   # orange/brown
    0xEE: 8,   # dark gray
    0xEF: 9,   # bright blue
    0xF0: 10,  # bright green/code
    0xF1: 11,  # bright cyan/section
    0xF2: 12,  # bright red/warning
    0xF3: 13,  # bright magenta
    0xF4: 14,  # yellow/value
    0xF5: 15,  # white/meta/key
}
SCORPION_ATTRIBUTE_CONTROLS = (
    frozenset(range(0xE1, 0xF0)) | frozenset(range(0xF0, 0xF9))
) - {0xF8}
SCORPION_UI_THEME = {
    "window": "cga:0",
    "text": "cga:7",
    "link": "cga:14",
    "title": "cga:0",
    "title_passive": "cga:0",
    "title_text": "cga:15",
    "frame": "cga:7",
    "icon": "cga:10",
    "page_area": "cga:0",
    "hover_bg": "cga:1",
    "hover_fg": "cga:14",
    "arrow_bg": "cga:0",
    "arrow_fg": "cga:7",
    "scroll_glyph": "cga:10",
    "thumb_bg": "transparent",
    "thumb_fg": "cga:15",
    "code_bg": "cga:0",
    "code_text": "cga:7",
}

_SCORPION_ENCODE_TABLE = {chr(index): index for index in range(32, 127)}
_SCORPION_ENCODE_TABLE.update({char: byte for byte, char in KAMENICKY.items()})


def scorpion_version_hint_from_path(path: str | Path) -> str | None:
    source_path = Path(path)
    for candidate in (source_path, *source_path.parents):
        match = SCORPION_VERSION_DIR_RE.match(candidate.name.strip())
        if match:
            return match.group("version")
    return None


def encode_scorpion_text(text: str) -> bytes:
    encoded = bytearray()
    for char in text:
        if char == "\n":
            encoded.append(0x0A)
            continue
        if char == "\r":
            encoded.append(0x0D)
            continue
        value = _SCORPION_ENCODE_TABLE.get(char)
        if value is not None:
            encoded.append(value)
            continue
        encoded.extend(char.encode("cp852", errors="replace"))
    return bytes(encoded)


def scorpion_raw_lines(lines: list[str]) -> list[bytes]:
    return [encode_scorpion_text(line) for line in lines]


def strip_legacy_container_suffix(title: str, source_name: str) -> str:
    source_path = Path(source_name)
    if (
        source_path.suffix.upper() not in {".DAT", ".EXE"}
        or source_path.stem.upper() not in SCORPION_LEGACY_CONTAINER_STEMS
    ):
        return title
    suffix = f" - {source_path.name}"
    if title.upper().endswith(suffix.upper()):
        return title[: -len(suffix)].strip()
    return title


def detect_scorpion_reader_family(path: str | Path, data: bytes | None = None) -> str | None:
    source_path = Path(path)
    if data is not None and source_path.suffix.lower() == ".dat":
        from .scorpion_dat_reader import is_scorpion_dat_help_binary

        if is_scorpion_dat_help_binary(data):
            return "dat"

    from .scorpion_legacy_reader import is_scorpion_legacy_binary

    if is_scorpion_legacy_binary(source_path, data):
        return "legacy"
    return None


def scorpion_reader_class_for_path(path: str | Path, data: bytes | None = None) -> type[HelpReaderBase] | None:
    family = detect_scorpion_reader_family(path, data)
    if family == "dat":
        from .scorpion_dat_reader import ScorpionDatReader

        return ScorpionDatReader
    if family == "legacy":
        from .scorpion_legacy_reader import ScorpionLegacyReader

        return ScorpionLegacyReader
    return None


class ScorpionReader(HelpReaderBase):
    """Dispatch Scorpions Cheater files to the matching legacy or DAT reader."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        source_path = self.source_path or Path(self.source_name)
        reader_class = scorpion_reader_class_for_path(source_path, data)
        if reader_class is None:
            raise ValueError("Not a supported Scorpions Cheater file.")
        reader = reader_class(source_name=self.source_name, source_path=source_path)
        return reader.read_bytes(data)
