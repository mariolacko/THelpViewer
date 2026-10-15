"""Bounded HC31 paragraph and character-command streams.

Text strings and format commands advance independently. Preserve native
metrics, table columns, font selections and hotspot operands before layout.
"""

from dataclasses import dataclass
import struct

from .winhelp_binary import WinHelpTopicLink, _bounded


class _Cursor:
    def __init__(self, data: bytes, description: str):
        self.data, self.description, self.pos = data, description, 0

    def take(self, size: int) -> bytes:
        result = _bounded(self.data, self.pos, size, self.description)
        self.pos += size
        return result

    def integer(self, size: int, *, signed: bool = False) -> int:
        return int.from_bytes(self.take(size), "little", signed=signed)

    def short(self, *, signed: bool = False) -> int:
        first = self.integer(1)
        return ((first >> 1) + (128 * self.integer(1) if first & 1 else 0)
                - ((16384 if first & 1 else 64) if signed else 0))

    def long(self, *, signed: bool = False) -> int:
        first = self.integer(2)
        return ((first >> 1) + (32768 * self.integer(2) if first & 1 else 0)
                - ((1073741824 if first & 1 else 16384) if signed else 0))

    def string(self) -> bytes:
        end = self.data.find(b"\0", self.pos)
        if end < 0:
            raise ValueError(f"Unterminated WinHelp {self.description} string at {self.pos:#x}")
        return self.take(end + 1 - self.pos)[:-1]


@dataclass(frozen=True, slots=True)
class WinHelpCommand:
    text: bytes
    text_offset: int
    opcode: int
    operand: bytes
    value: int = 0
    hotspots: int = 0


@dataclass(frozen=True, slots=True)
class WinHelpParagraph:
    column: int | None
    prefix: bytes
    flags: int
    unknown: int | None
    metrics: tuple[int | None, ...]
    border: tuple[int, int] | None
    tabs: tuple[tuple[int, int], ...]
    commands: tuple[WinHelpCommand, ...]


@dataclass(frozen=True, slots=True)
class WinHelpDisplay:
    size: int
    length: int
    table_type: int | None
    minimum_width: int | None
    columns: tuple[tuple[int, int], ...]
    paragraphs: tuple[WinHelpParagraph, ...]

    @classmethod
    def read(cls, record: WinHelpTopicLink):
        if record.record_type not in {0x20, 0x23}:
            raise ValueError(f"Unsupported WinHelp display type {record.record_type:#x}")
        fmt = _Cursor(record.data1, f"format record {record.position:#x}")
        text = _Cursor(record.data2, f"text record {record.position:#x}")
        size, length = fmt.long(signed=True), fmt.short()
        table_type = minimum_width = None
        columns = ()
        if record.record_type == 0x23:
            count, table_type = fmt.integer(1), fmt.integer(1)
            if not count or table_type not in {0, 1, 2, 3}:
                raise ValueError("Invalid WinHelp table geometry/type")
            if table_type in {0, 2}:
                minimum_width = fmt.integer(2, signed=True)
            columns = tuple((fmt.integer(2, signed=True), fmt.integer(2, signed=True)) for _ in range(count))
        paragraphs = []
        while True:
            column = None
            prefix = b""
            if table_type is not None:
                column = fmt.integer(2, signed=True)
                if column == -1:
                    break
                if not 0 <= column < len(columns):
                    raise ValueError("WinHelp cell column outside the table")
                prefix = fmt.take(3)
            prefix += fmt.take(4)
            flags = fmt.integer(2)
            unknown = fmt.long(signed=True) if flags & 1 else None
            metrics = tuple(fmt.short(signed=True) if flags & bit else None
                            for bit in (2, 4, 8, 16, 32, 64))
            border = (fmt.integer(1), fmt.integer(2, signed=True)) if flags & 0x100 else None
            tabs = []
            if flags & 0x200:
                count = fmt.short(signed=True)
                if count < 0:
                    raise ValueError("Negative WinHelp tab-stop count")
                for _ in range(count):
                    stop = fmt.short()
                    kind = fmt.short() if stop & 0x4000 else 0
                    if kind not in {0, 1, 2}:
                        raise ValueError("Unsupported WinHelp tab alignment")
                    tabs.append((stop & 0x3FFF, kind))
            commands = []
            while True:
                text_offset = text.pos
                string = text.string()
                opcode = fmt.integer(1)
                start = fmt.pos
                value = hotspots = 0
                if opcode in {0x20, 0xE0, 0xE1, 0xE2, 0xE3, 0xE6, 0xE7}:
                    value = fmt.integer(4)
                elif opcode in {0x21, 0x80}:
                    value = fmt.integer(2)
                elif opcode in {0x86, 0x87, 0x88}:
                    value = fmt.integer(1)
                    picture_size = fmt.long(signed=True)
                    if value not in {3, 5, 0x22} or picture_size < 0:
                        raise ValueError("Unsupported WinHelp picture command/type")
                    if value == 0x22:
                        hotspots = fmt.short()
                    fmt.take(picture_size)
                elif opcode in {0xC8, 0xCC, 0xEA, 0xEB, 0xEE, 0xEF}:
                    value = fmt.integer(2)
                    fmt.take(value)
                elif opcode not in {0x81, 0x82, 0x83, 0x89, 0x8B, 0x8C, 0xFF}:
                    raise ValueError(f"Unknown WinHelp format opcode {opcode:#x} at {record.position:#x}")
                commands.append(WinHelpCommand(string, text_offset, opcode, fmt.data[start:fmt.pos], value, hotspots))
                if opcode == 0xFF:
                    break
            paragraphs.append(WinHelpParagraph(column, prefix, flags, unknown, metrics,
                                               border, tuple(tabs), tuple(commands)))
            if table_type is None:
                break
        if fmt.pos != len(fmt.data):
            raise ValueError(f"Unconsumed WinHelp format bytes at {record.position:#x}: {len(fmt.data) - fmt.pos}")
        if any(text.data[text.pos:]):
            raise ValueError(f"Unconsumed WinHelp text bytes at {record.position:#x}")
        return cls(size, length, table_type, minimum_width, columns, tuple(paragraphs))


@dataclass(frozen=True, slots=True)
class WinHelpFont:
    attributes: int
    half_points: int
    family: int
    face: bytes
    foreground: bytes
    background: bytes


def read_fonts(data: bytes) -> tuple[WinHelpFont, ...]:
    names, count, name_start, descriptor_start = struct.unpack("<HHHH", _bounded(data, 0, 8, "FONT header"))
    if name_start != 8:
        raise ValueError("Extended WinHelp FONT descriptors are not implemented")
    if not names or not count or descriptor_start < name_start or (descriptor_start - name_start) % names:
        raise ValueError("Invalid WinHelp FONT face/descriptor geometry")
    name_size = (descriptor_start - name_start) // names
    if not name_size or descriptor_start + 11 * count != len(data):
        raise ValueError("WinHelp FONT descriptor count/length mismatch")
    faces = [_bounded(data, name_start + i * name_size, name_size, "font face").split(b"\0", 1)[0]
             for i in range(names)]
    fonts = []
    for index in range(count):
        raw = _bounded(data, descriptor_start + index * 11, 11, "font descriptor")
        face = int.from_bytes(raw[3:5], "little")
        if face >= names:
            raise ValueError("WinHelp font face index outside the face table")
        fonts.append(WinHelpFont(raw[0], raw[1], raw[2], faces[face], raw[5:8], raw[8:11]))
    return tuple(fonts)


@dataclass(frozen=True, slots=True)
class WinHelpLink:
    kind: str
    value: int | bytes
    file: bytes | None = None
    window: int | bytes | None = None


def read_link(command: WinHelpCommand) -> WinHelpLink:
    if command.opcode in {0xE0, 0xE1}:
        return WinHelpLink("topic-number", command.value)
    if command.opcode in {0xE2, 0xE3, 0xE6, 0xE7}:
        return WinHelpLink("context-hash", command.value)
    if command.opcode in {0xC8, 0xCC}:
        payload = command.operand[2:]
        if b"\0" in payload.rstrip(b"\0"):
            raise ValueError("WinHelp macro contains an internal NUL")
        return WinHelpLink("macro", payload.rstrip(b"\0"))
    if command.opcode not in {0xEA, 0xEB, 0xEE, 0xEF}:
        raise ValueError("Not a WinHelp link command")
    cur = _Cursor(command.operand[2:], "external hotspot")
    kind, value = cur.integer(1), cur.integer(4)
    file = window = None
    if kind == 1:
        window = cur.integer(1)
    elif kind == 4:
        file = cur.string()
    elif kind == 6:
        # Native HC31 layout: secondary window name precedes the filename.
        window, file = cur.string(), cur.string()
    elif kind != 0:
        raise ValueError(f"Unsupported WinHelp external-link subtype {kind}")
    if cur.pos != len(cur.data):
        raise ValueError("Unconsumed WinHelp external-link payload")
    return WinHelpLink("context-hash", value, file, window)


def context_hash(name: bytes) -> int:
    result = 0
    for byte in name:
        if 65 <= byte <= 90:
            value = byte - 65 + 17
        elif 97 <= byte <= 122:
            value = byte - 97 + 17
        elif 49 <= byte <= 57:
            value = byte - 48
        elif byte in {48, 46, 95}:
            value = {48: 10, 46: 12, 95: 13}[byte]
        else:
            raise ValueError("Invalid HC31 context-name byte")
        result = (result * 43 + value) & 0xFFFFFFFF
    return result if name else 1


class _Macro:
    """Read native quoted calls, never evaluate a host-language expression."""

    def __init__(self, raw):
        self.raw, self.pos = raw, 0

    def space(self):
        while self.pos < len(self.raw) and self.raw[self.pos] in b" \t\r\n":
            self.pos += 1

    def value(self, depth=0):
        if depth > 32:
            raise ValueError("WinHelp macro nesting limit")
        self.space()
        start = self.pos
        if self.pos == len(self.raw):
            raise ValueError("Incomplete WinHelp macro")
        if self.raw[self.pos] in {34, 96}:
            quote = self.raw[self.pos]
            self.pos += 1
            start = self.pos
            nesting = 1
            while self.pos < len(self.raw):
                char = self.raw[self.pos]
                if quote == 96 and char == 96:
                    nesting += 1
                if char == (34 if quote == 34 else 39):
                    nesting -= 1
                    if not nesting:
                        result = self.raw[start:self.pos]
                        self.pos += 1
                        return result
                self.pos += 1
            raise ValueError("Unterminated WinHelp macro string")
        while self.pos < len(self.raw) and (self.raw[self.pos:self.pos + 1].isalnum() or self.raw[self.pos] == 95):
            self.pos += 1
        name = self.raw[start:self.pos]
        self.space()
        if not name or self.raw[self.pos:self.pos + 1] != b"(":
            raise ValueError("Unsupported WinHelp macro expression")
        self.pos += 1
        args = []
        self.space()
        if self.raw[self.pos:self.pos + 1] != b")":
            while True:
                args.append(self.value(depth + 1))
                self.space()
                if self.raw[self.pos:self.pos + 1] != b",":
                    break
                self.pos += 1
        if self.raw[self.pos:self.pos + 1] != b")":
            raise ValueError("Unterminated WinHelp macro call")
        self.pos += 1
        return name.lower(), tuple(args)


def macro_navigation(raw: bytes, depth: int = 0) -> WinHelpLink | None:
    """Only deterministic navigation with no native marks or host side effects."""
    if depth > 32:
        return None
    try:
        parser = _Macro(raw)
        node = parser.value()
        parser.space()
        if parser.pos != len(raw) or not isinstance(node, tuple):
            return None
        name, args = node
        if name in {b"jumpid", b"ji"} and len(args) == 2 and all(isinstance(a, bytes) for a in args):
            return WinHelpLink("context-hash", context_hash(args[1]), args[0] or None)
        if name == b"jumpcontents" and len(args) == 1 and isinstance(args[0], bytes):
            return WinHelpLink("contents", 0, args[0] or None)
        if (name == b"ifthenelse" and len(args) == 3 and isinstance(args[0], tuple)
                and args[0][0] == b"ismark" and len(args[0][1]) == 1 and isinstance(args[2], bytes)):
            # Native Mark/GotoMark state is not created in this viewer, so the
            # source-authored no-mark branch is the applicable navigation.
            return macro_navigation(args[2], depth + 1)
    except ValueError:
        pass
    return None


# Standard Symbol encoding: AFM character identities plus Unicode glyph names
# (URW StandardSymbolsPS / Adobe Glyph List). Construction pieces use their
# standard Unicode equivalents rather than font-specific private-use cells.
_SYMBOL = {byte: chr(byte) for byte in range(32, 64)}
_SYMBOL.update(zip(range(65, 91), "ΑΒΧ∆ΕΦΓΗΙϑΚΛΜΝΟΠΘΡΣΤΥςΩΞΨΖ"))
_SYMBOL.update(zip(range(97, 123), "αβχδεφγηιϕκλµνοπθρστυϖωξψζ"))
_SYMBOL.update({34: "∀", 36: "∃", 39: "∋", 42: "∗", 45: "−", 64: "≅",
                91: "[", 92: "∴", 93: "]", 94: "⊥", 95: "_", 96: "⎷",
                123: "{", 124: "|", 125: "}", 126: "∼"})
_SYMBOL.update(zip(range(160, 192), "€ϒ′≤⁄∞ƒ♣♦♥♠↔←↑→↓°±″≥×∝∂•÷≠≡≈…⏐⎯↵"))
_SYMBOL.update(zip(range(192, 240), "ℵℑℜ℘⊗⊕∅∩∪⊃⊇⊄⊂⊆∈∉∠∇®©™∏√⋅¬∧∨⇔⇐⇑⇒⇓◊〈®©™∑⎛⎜⎝⎡⎢⎣⎧⎨⎩⎪"))
_SYMBOL.update(zip(range(241, 255), "〉∫⌠⎮⌡⎞⎟⎠⎤⎥⎦⎫⎬⎭"))


def decode_font_text(raw: bytes, font: WinHelpFont, encoding: str) -> tuple[str, tuple[int, ...]]:
    if font.face.lower() == b"symbol":
        return "".join(_SYMBOL.get(byte, "\ufffd") for byte in raw), tuple(byte for byte in raw if byte not in _SYMBOL)
    return raw.decode(encoding, errors="replace"), ()
