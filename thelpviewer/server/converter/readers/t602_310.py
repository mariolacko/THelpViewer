"""Reader for Software602 Text-family help files (Text602 and Calc602).

Ported from Text602HelpDecompiler in HelpTools/python/decompiler/hldc.py.
Visible bytes are stored with a +1 offset; body is 0x0E-delimited chunks.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import struct
from difflib import SequenceMatcher

from ..base import HelpDocument, IndexEntry, TopicRecord
from ..codepages import KAMENICKY
from ..uhf_markup import escape_uhf_text, format_uhf_link

# ─── Format detection ────────────────────────────────────────────────────────

_TEXT602_HDR = b'Text602 - help'
_CALC602_HDR = b'Calc602 - help'

_TEXT602_UI_THEME: dict[str, str] = {
    "window": "#005454",
    "text": "#a8fcfc",
    "link": "#a8a800",
    "title": "#a8a800",
    "title_passive": "#005454",
    "title_text": "#005454",
    "title_text_passive": "#a8a800",
    "frame": "#a8a800",
    "frame_passive": "#a8a800",
    "icon": "#005454",
    "icon_passive": "#a8a800",
    "page_area": "#005454",
    "hover_bg": "#a8a800",
    "hover_fg": "#005454",
    "arrow_bg": "#a8a800",
    "arrow_fg": "#005454",
    "scroll_glyph": "#a8a800",
    "thumb_bg": "#a8a800",
    "thumb_fg": "#005454",
    "code_bg": "#005454",
    "code_text": "#a8fcfc",
}


def is_t602_310_binary(data: bytes) -> bool:
    """Return True when *data* looks like a Text602 or Calc602 help file."""
    return data.startswith(_TEXT602_HDR) or data.startswith(_CALC602_HDR)


# ─── Character decode maps ───────────────────────────────────────────────────
# After subtracting 1 from stored byte, high bytes use these overrides.

_T602_TEXT: dict[int, str] = {
    0x98: '\u25A0',  # ■
    0xC4: '\u010F',  # ď
    0xCE: '\u0148',  # ň
    0xD4: '\u0165',  # ť
    0xD5: '\u00FA',  # ú
    0xE1: '\u00C1',  # Á
    0xE7: '|',
    0xF2: '\u0158',  # Ř
    0xF3: '\u0160',  # Š
    0xF5: '\u00DA',  # Ú
    0xF7: '\u00C9',  # É
    0xC1: '\u00E1',  # á
    0xC3: '\u010D',  # č
    0xC5: '\u011B',  # ě
    0xC9: '\u00ED',  # í
    0xCA: '\u016F',  # ů
    0xCF: '\u00F3',  # ó
    0xD2: '\u0159',  # ř
    0xD3: '\u0161',  # š
    0xD7: '\u00E9',  # é
    0xD9: '\u00FD',  # ý
    0xDA: '\u017E',  # ž
    0xE3: '\u010C',  # Č
    0xE9: '\u00CD',  # Í
    0xFA: '\u017D',  # Ž
}

_T602_BOX: dict[int, str] = {
    0xC0: '\u250c',  # ┌
    0xC2: '\u2514',  # └
    0xC7: '\u2500',  # ─
    0xD6: '\u251c',  # ├
    0xDB: '\u252c',  # ┬
    0xDF: '\u253c',  # ┼
    0xE0: '\u2510',  # ┐
    0xE2: '\u2518',  # ┘
    0xE7: '\u2502',  # │
    0xF6: '\u2524',  # ┤
    0xFB: '\u2534',  # ┴
}

# Internal link markup produced by the parser: {label:target_title} or {label:target_title:dest_id}
_LINK_RE = re.compile(r'\{([^{}:]+):([^{}]*?)(?::(\d+))?\}')
_UNRESOLVED_LINK_RE = re.compile(r'\{([^{}:]+)::(\d+)\}')
_NAV_TITLE_ALIAS_BY_TITLE = {
    'Graf | Nadpis': ('Nadpis grafu',),
}
_NAV_GRAPH_TITLE_RE = re.compile(r'([23]D)\s+(?:rovinný|prostorový)\s+graf', re.IGNORECASE)
_TARGET_OCCURRENCE_SEPARATOR = '\x1f'


def _target_ref(title: str, occurrence: int = 1) -> str:
    if occurrence == 1:
        return title
    return f'{_TARGET_OCCURRENCE_SEPARATOR}{occurrence}{_TARGET_OCCURRENCE_SEPARATOR}{title}'


# Application-owned HelpCtx ids are not present in the HLP anchor table. These
# targets were verified against the HelpCtx resource in the original T602.EXE.
_TEXT602_FIXED_DESTINATIONS: dict[int, tuple[str, int]] = {
    89: ('Písmo | Výběr fontu               <Ctrl-P>', 1),
    90: ('Menu Jdi na                       <Alt-J>', 1),
    91: ('Jdi na | Stránku', 1),
    92: ('Jdi na | Řádku', 1),
    93: ('Jdi na | Začátek bloku            <Ctrl-QB>', 1),
    94: ('Jdi na | Konec bloku              <Ctrl-QK>', 1),
    95: ('Jdi na | Začátek souboru          <Ctrl-PgUp>', 1),
    96: ('Jdi na | Konec souboru            <Ctrl-PgDn>', 1),
    97: ('Jdi na | Najít                    <Ctrl-QF>', 1),
    98: ('Jdi na | Zaměnit                  <Ctrl-QA>', 1),
    99: ('Vzorce | Další                    <Ctrl-L>', 1),
    100: ('Menu okna                         <Alt-O>', 1),
    101: ('Soubor | Nový', 1),
    102: ('Menu Klávesnice', 1),
    103: ('Konfigurace | Myš', 1),
    104: ('Text602 | Konfigurace', 1),
    105: ('Text602 | Makra', 1),
    106: ('Text602 | Rámečky                 <Alt-G>', 1),
    107: ('Text602 | Kalkulačka              <Alt-Q>', 1),
    108: ('Text602 | Kartotéka', 1),
    109: ('Text602 | Kontrola pravopisu      <Alt-L>', 1),
    110: ('Text602 | Překladové slovníky     <Alt-H>', 1),
    111: ('Text602 | Obsah', 1),
    112: ('Text602 | Abecední rejstřík nápovědy.', 1),
    113: ('Text602 | Informace', 1),
    114: ('Okna | Výběr', 1),
    116: ('Makra | Definice                  <Alt-0>', 1),
    117: ('Makra | Výběr makra               <Alt-=>', 1),
    118: ('Makra | Načtení', 1),
    119: ('Makra | Uložení', 1),
    120: ('Makra | Editace', 1),
    121: ('Klávesnice | Ruština              <Alt-7>', 1),
    122: ('Klávesnice | Český psací stroj    <Alt-2>', 1),
    123: ('Klávesnice | Slovenský psací stroj       <Alt-3>', 1),
    124: ('Klávesnice | Speciální znaky      <Alt-4>', 1),
    125: ('Klávesnice | Německá klávesnice   <Alt-6>', 1),
    126: ('Klávesnice | Uživatelská klávesnice KL8        <Alt-8>', 1),
    127: ('Klávesnice | Uživatelská klávesnice KL9        <Alt-9>', 1),
    128: ('Klávesnice | Počítačová klávesnice       <Alt-5>', 1),
    129: ('Klávesnice | Česká amatérská      <Alt-1>', 1),
    132: ('Klávesnice | Prohození Z za Y', 1),
    133: ('Klávesnice | Zobrazení vybrané klávesnice      <Alt-X>', 1),
    136: ('Dokument | Výběr stylu odstavce   <Alt-Y>', 1),
    137: ('Řádka | Políčko', 1),
    139: ('Preview                           <Ctrl+PrtScr>', 1),
    140: ('Čas odeslání zásilky', 1),
    141: ('Seznamy adresátů', 1),
    142: ('Konfigurace | Pravopis', 1),
    144: ('Text602 | Kalkulačka              <Alt-Q>', 3),
    146: ('Dělení slov', 1),
    147: ('Přihlášení uživatele', 1),
    148: ('Konfigurace  | Styl odstavce STANDARD', 1),
    149: ('Konfigurace | Pošta&Fax', 1),
    301: ('Soubor | Otevření                 <F3>', 2),
    302: ('Soubor | Uložit                   <F2>', 2),
    303: ('Soubor | Zapsat jako', 2),
    305: ('Edit | Smazat položku             <Ctrl-Y>', 1),
    306: ('Soubor | Zhustit', 1),
    307: ('Soubor | Vyprázdnit', 1),
    310: ('Záznam | Pro tisk                 <Alt-=>', 1),
    312: ('Zobrazit | Filtr', 1),
    313: ('Zobrazit | Zrušené', 1),
    314: ('Zobrazit | Století', 1),
    315: ('Jdi na | Začátek souboru', 1),
    316: ('Jdi na | Konec souboru', 1),
    317: ('Jdi na | Předchozí záznam         <F7>', 1),
    318: ('Jdi na | Další záznam             <F8>', 1),
    321: ('Jdi na | Přeskočit', 1),
    322: ('Jdi na | První položku', 1),
    323: ('Jdi na | Poslední položku', 1),
    324: ('Záznam | Obnovit', 1),
    326: ('Záznam | Smazat obsah', 1),
    327: ('Záznam | Zrušený                  <Alt-Mezerník>', 1),
    328: ('Jdi na | Vyhledat', 1),
    330: ('Formulář | Navrhnout', 1),
    331: ('Formulář | Vybrat', 1),
    332: ('Soubor | Připojit', 1),
    333: ('Záznam | Nový                     <Ctrl-Enter>', 1),
    334: ('Zobrazit | Definice filtru', 1),
    335: ('Soubor | Struktura dat', 1),
    337: ('Zobrazit | Prohlížeč              <Alt-P>', 1),
    339: ('Menu Soubor                       <Alt-S>', 1),
    340: ('Menu Edit                         <Alt-E>', 2),
    341: ('Menu Zobrazit                     <Alt-Z>', 1),
    342: ('Menu Formulář                     <Alt-F>', 1),
    343: ('Menu Záznam                       <Alt-M>', 1),
    344: ('Text602 | Editor', 1),
    345: ('Menu Jdi na                       <Alt-J>', 2),
    348: ('Jdi na | Záznam číslo', 1),
    349: ('Jdi na | Najít                    <Ctrl-QF>', 2),
    350: ('Jdi na | Další                    <Ctrl-L>', 1),
    351: ('Text602 | Statistika', 1),
    352: ('Menu Text602                      <Alt-T>', 2),
    353: ('Základní pohyb v nápovědě', 2),
    354: ('Seznam funkcí kartotéky', 1),
    355: ('Soubor | Tisk', 2),
}

_CALC602_FIXED_DESTINATIONS: dict[int, tuple[str, int]] = {
    133: ('Help | Obsah', 1),
    134: ('Help | Rejstřík', 1),
}


@dataclass(frozen=True, slots=True)
class _NavCandidate:
    ctx_id: int
    title: str
    text: str
    score: int
    key: str
    tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _NavigationIndex:
    by_key: dict[str, list[_NavCandidate]]
    by_token: dict[str, tuple[_NavCandidate, ...]]
    candidates: tuple[_NavCandidate, ...]


# ─── Core parser ─────────────────────────────────────────────────────────────

class _T602Parser:
    """Parse one Text602/Calc602 file into a list of screen records.

    Each screen dict has keys:
      title (str), flag (int|None), items (list[dict])
    Items are dicts with 'kind' in ('visible', 'separator', 'comment', 'ctrl')
    and 'text' (str). Title items are not included in items (stored in 'title').
    """

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.header_end = data.index(b'\x0e')
        crlf_pos = data.index(b'\r\n', 0, self.header_end)
        self.file_header_str = data[:crlf_pos].decode('ascii', errors='replace')
        self.is_text602 = data.startswith(_TEXT602_HDR)
        self.header_binary = data[crlf_pos + 2: self.header_end]
        self._current_title: str | None = None
        self._current_flag: int | None = None
        self._title_aliases: dict[str, set[str]] = {}
        self._dest_targets: dict[int, str] = {}
        self._dest_hints: dict[int, tuple[str, ...]] = {}

    # ── public ──

    def parse(self) -> list[dict]:
        """Return parsed screens."""
        payload = self.data[self.header_end:]
        parts = payload.split(b'\x0e')
        self._title_aliases = self._build_title_aliases(parts)
        self._dest_targets = self._build_destination_id_targets(parts)
        screens: list[dict] = []
        pos = self._find_next_title(parts, 0)
        while pos is not None:
            screen, pos = self._process_screen(parts, pos)
            if screen is not None:
                screens.append(screen)
        return screens

    # ── chunk detection ──

    @staticmethod
    def _is_title_chunk(part: bytes, next_part: bytes) -> bool:
        return (
            len(part) > 5
            and part.endswith(b'\x00\x00')
            and len(next_part) == 77
            and set(next_part) == {0x99}
        )

    @classmethod
    def _is_marked_title_at(cls, parts: list[bytes], idx: int) -> bool:
        if idx + 3 >= len(parts):
            return False
        if parts[idx + 1] != b'\x4f\x00\x00':
            return False
        if not cls._is_separator_chunk(parts[idx + 2]) or not cls._is_context_chunk(parts[idx + 3]):
            return False
        if cls._looks_binary(parts[idx]):
            return False
        title = cls._decode_preview(parts[idx]).strip()
        return '|' in title

    @classmethod
    def _is_title_at(cls, parts: list[bytes], idx: int) -> bool:
        return (
            idx + 1 < len(parts)
            and cls._is_title_chunk(parts[idx], parts[idx + 1])
        ) or cls._is_marked_title_at(parts, idx)

    @staticmethod
    def _is_separator_chunk(chunk: bytes) -> bool:
        return len(chunk) == 77 and set(chunk) == {0x99}

    @staticmethod
    def _is_context_chunk(chunk: bytes) -> bool:
        return len(chunk) == 3

    @classmethod
    def _is_footer_chunk(cls, chunk: bytes) -> bool:
        core = cls._footer_core(cls._decode_preview(chunk))
        return core in {
            'Obsah nápovědy',
            'Rejstřík  Obsah',
            'Rejstřík',
            'Obsah',
            'Rejstřík nápovědy',
        }

    @staticmethod
    def _footer_core(text: str) -> str:
        core = text.strip()
        if core.startswith('\u25a0'):
            core = core[1:].strip()
        return core

    @staticmethod
    def _looks_binary(chunk: bytes) -> bool:
        if not chunk:
            return False
        return sum(1 for b in chunk if b >= 0x20) * 2 < len(chunk)

    @classmethod
    def _looks_box_chunk(cls, chunk: bytes) -> bool:
        vals = [((b - 1) & 0xFF) for b in chunk if b >= 0x80]
        if not vals:
            return False
        box_bytes = sum(1 for v in vals if v in _T602_BOX)
        if box_bytes == len(vals) and box_bytes >= 2:
            return True
        if len(chunk) < 20:
            return False
        verticals = sum(1 for v in vals if v == 0xE7)
        horizontals = sum(1 for v in vals if v == 0xC7)
        return box_bytes >= 6 or verticals >= 2 or horizontals >= 8

    # ── text decoding ──

    @classmethod
    def _decode_byte(cls, b: int, box_mode: bool = False) -> str:
        if b == 0x00:
            return ' '
        if b in (0x06, 0x07):
            return '\n'
        if b < 0x20:
            return ''
        val = (b - 1) & 0xFF
        if val < 0x80:
            return chr(val)
        if box_mode:
            return _T602_BOX.get(val, _T602_TEXT.get(val, KAMENICKY.get(val, f'[{val:02X}]')))
        return _T602_TEXT.get(val, KAMENICKY.get(val, f'[{val:02X}]'))

    @classmethod
    def _decode_preview(cls, chunk: bytes) -> str:
        return ''.join(cls._decode_byte(b) for b in chunk)

    @classmethod
    def _extract_edge_controls(cls, chunk: bytes) -> tuple[list, bytes, list]:
        prefix: list = []
        suffix: list = []
        while len(chunk) >= 3 and chunk[1] < 0x20 and chunk[2] < 0x20:
            prefix.append(chunk[:3])
            chunk = chunk[3:]
        while len(chunk) >= 3 and chunk[-2] < 0x20 and chunk[-1] < 0x20:
            suffix.insert(0, chunk[-3:])
            chunk = chunk[:-3]
        return prefix, chunk, suffix

    def _decode_chunk(self, chunk: bytes, title: bool = False) -> str:
        _, chunk, _ = self._extract_edge_controls(chunk)
        had_trailing = False
        while chunk and chunk[-1] == 0x00:
            chunk = chunk[:-1]
            had_trailing = True
        while chunk and chunk[-1] < 0x20:
            chunk = chunk[:-1]
            had_trailing = True
        while chunk and chunk[-1] == 0x00:
            chunk = chunk[:-1]
            had_trailing = True
        if len(chunk) > 3 and chunk[1] <= 0x03 and chunk[2] == 0x01:
            chunk = chunk[3:]
        if self._is_separator_chunk(chunk):
            return '\u2580' * len(chunk)
        box_mode = self._looks_box_chunk(chunk)
        text = ''.join(self._decode_byte(b, box_mode=box_mode) for b in chunk).rstrip()
        if title and text.endswith(' N'):
            text = text[:-2].rstrip()
        text = re.sub(r'([.!?;:)\]"\']) [^\s]$', r'\1', text)
        if had_trailing and chunk and chunk[-1] >= 0x80:
            text = re.sub(r' (.)$', '', text)
        return text

    # ── title alias system (text-based link resolution) ──

    @staticmethod
    def _normalize_title_key(text: str) -> str:
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\s*<[^>]+>$', '', text).rstrip()
        return text.rstrip('.').casefold()

    def _register_alias(self, alias_map: dict, alias: str, target: str) -> None:
        key = self._normalize_title_key(alias)
        if key:
            alias_map.setdefault(key, set()).add(target)

    def _build_title_aliases(self, parts: list[bytes]) -> dict[str, set[str]]:
        alias_map: dict[str, set[str]] = {}
        for idx in range(len(parts) - 2):
            if not self._is_title_at(parts, idx):
                continue
            title = self._decode_chunk(parts[idx], title=True)
            if not title:
                continue
            title_no_hk = re.sub(r'\s*<[^>]+>$', '', title).rstrip()
            self._register_alias(alias_map, title, title)
            self._register_alias(alias_map, title_no_hk, title)
            if title_no_hk.startswith('Menu '):
                self._register_alias(alias_map, title_no_hk[5:].strip(), title)
            if '|' in title_no_hk:
                segments = [s.strip() for s in title_no_hk.split('|') if s.strip()]
                if segments:
                    last = segments[-1]
                    self._register_alias(alias_map, last, title)
                    if last == 'Otevření':
                        self._register_alias(alias_map, 'Otevřít', title)
                    if segments[0] == 'Klávesnice' and 'klávesnice' not in last.casefold():
                        self._register_alias(alias_map, f'{last} klávesnice', title)
                    if segments[0] == 'Klávesnice':
                        if last == 'Uživatelská klávesnice KL8':
                            self._register_alias(alias_map, 'Uživatelská klávesnice 1', title)
                            self._register_alias(alias_map, 'Uživatelská 1', title)
                        if last == 'Uživatelská klávesnice KL9':
                            self._register_alias(alias_map, 'Uživatelská klávesnice 2', title)
                            self._register_alias(alias_map, 'Uživatelská 2', title)
                    if segments[0] == 'Soubor':
                        if last == 'Nový':
                            self._register_alias(alias_map, 'Nový soubor', title)
                        if last == 'Otevření':
                            self._register_alias(alias_map, 'Otevřít soubor', title)
                            self._register_alias(alias_map, 'Otevřít databázový soubor', title)
                        if last == 'Uložit':
                            self._register_alias(alias_map, 'Uložit soubor', title)
                            self._register_alias(alias_map, 'Uložit databázový soubor', title)
                        if last == 'Zapsat jako':
                            self._register_alias(alias_map, 'Zapsat soubor pod jménem', title)
                            self._register_alias(alias_map, 'Zapsat databázový soubor pod jménem', title)
                        if last == 'Import':
                            self._register_alias(alias_map, 'Import textu', title)
                        if last == 'Export':
                            self._register_alias(alias_map, 'Export textu', title)
                    if segments[0] == 'Blok':
                        self._register_alias(alias_map, f'{last} bloku', title)
                    if segments[0] == 'Makra':
                        if last == 'Načtení':
                            self._register_alias(alias_map, 'Načtení makra', title)
                        if last == 'Uložení':
                            self._register_alias(alias_map, 'Uložení makra', title)
                        if last == 'Editace':
                            self._register_alias(alias_map, 'Editace Makra', title)
                    if segments[0] == 'Formulář':
                        if last == 'Vybrat':
                            self._register_alias(alias_map, 'Vybrat formulář', title)
                        if last == 'Navrhnout':
                            self._register_alias(alias_map, 'Navrhnout formulář', title)
                    if segments[0] == 'Text602' and last == 'Obsah':
                        self._register_alias(alias_map, 'Obsah nápovědy', title)
                    if segments[0] == 'Text602' and 'Abecední rejstřík nápovědy' in last:
                        self._register_alias(alias_map, 'Rejstřík', title)
                        self._register_alias(alias_map, 'Rejstřík nápovědy', title)
                        self._register_alias(alias_map, 'Abecední rejstřík nápovědy', title)
        return alias_map

    def _candidate_targets(self, text: str) -> set[str]:
        return self._title_aliases.get(self._normalize_title_key(text), set())

    def _remember_dest_hint(self, dest_id: int, *hints: str) -> None:
        current = list(self._dest_hints.get(dest_id, ()))
        known = {self._normalize_title_key(hint) for hint in current}
        changed = False
        for hint in hints:
            key = self._normalize_title_key(hint)
            if not key or key in known:
                continue
            current.append(hint)
            known.add(key)
            changed = True
        if changed:
            self._dest_hints[dest_id] = tuple(current)

    @staticmethod
    def _title_section(title: str) -> str | None:
        title = re.sub(r'\s*<[^>]+>$', '', title).strip()
        if '|' in title:
            return title.split('|', 1)[0].strip().title()
        if title.lower().startswith('menu '):
            return title[5:].strip().title()
        return None

    @staticmethod
    def _title_last_segment(title: str) -> str:
        title = re.sub(r'\s*<[^>]+>$', '', title).strip()
        if '|' in title:
            return title.split('|')[-1].strip()
        return title

    def _resolve_link_target(self, text: str) -> str | None:
        targets = self._candidate_targets(text)
        if len(targets) == 1:
            return next(iter(targets))
        if len(targets) > 1 and self._current_title:
            section = self._title_section(self._current_title)
            if section:
                scoped = sorted(t for t in targets if t.startswith(f'{section} | '))
                if len(scoped) == 1:
                    return scoped[0]
        return None

    def _resolve_hint_target(self, dest_id: int, hints: tuple[str, ...]) -> str | None:
        ranked: dict[str, int] = {}
        hint_keys = tuple(self._normalize_title_key(hint) for hint in hints if hint)
        for hint in hints:
            hint_key = self._normalize_title_key(hint)
            for target in self._candidate_targets(hint):
                score = 0
                last_key = self._normalize_title_key(self._title_last_segment(target))
                if last_key == hint_key:
                    score += 30
                section = self._title_section(target)
                if section and any(self._normalize_title_key(section) in key for key in hint_keys):
                    score += 20
                if '<' in target and dest_id < 256:
                    score += 6
                if '<' not in target and dest_id >= 256:
                    score += 6
                if target.startswith('Menu '):
                    score -= 10
                ranked[target] = max(ranked.get(target, -10_000), score)

        if not ranked:
            return None
        ordered = sorted(ranked.items(), key=lambda item: (-item[1], item[0]))
        if len(ordered) == 1:
            return ordered[0][0]
        if ordered[0][1] > ordered[1][1]:
            return ordered[0][0]
        return None

    # ── text linkification ──

    @staticmethod
    def _raw_display_len(text: str) -> int:
        return len(re.sub(r'\{([^{}:]+):[^{}]*\}', r'\1', text))

    def _linkify_text_line(self, text: str) -> str:
        if not text or '{' in text or '}' in text:
            return text
        prefix = ''
        core = text
        if text.startswith('\u25a0 '):
            rest = text[2:]
            core = rest.lstrip(' ')
            prefix = text[:len(text) - len(core)]
        else:
            stripped = text.lstrip(' ')
            prefix = text[:len(text) - len(stripped)]
            core = stripped
        if not core:
            return text
        if core == 'Rejstřík  Obsah':
            index_target = (
                self._resolve_link_target('Rejstřík nápovědy')
                or self._resolve_link_target('Rejstřík')
            )
            contents_target = (
                self._resolve_link_target('Obsah nápovědy')
                or self._resolve_link_target('Obsah')
            )
            if self.is_text602:
                index_target = index_target or _TEXT602_INDEX_TITLE
                contents_target = contents_target or _TEXT602_CONTENTS_TITLE
            if index_target and contents_target:
                return (f'{prefix}{{Rejstřík:{index_target}}}  '
                        f'{{Obsah:{contents_target}}}')
            return text
        target = self._resolve_link_target(core)
        if target and self._normalize_title_key(target) != self._normalize_title_key(self._current_title or ''):
            return f'{prefix}{{{core}:{target}}}'
        return text

    # ── binary link chunks ──

    @staticmethod
    def _parse_link_chunk(chunk: bytes):
        if len(chunk) < 7:
            return None, None
        count = int.from_bytes(chunk[:2], 'little')
        if count <= 0 or count > 4096:
            return None, None
        body_len = 2 + count * 5
        remainder = len(chunk) - body_len
        if body_len > len(chunk) or remainder not in (0, 7):
            return None, None
        records = []
        for i in range(count):
            off = 2 + i * 5
            records.append((
                int.from_bytes(chunk[off:off + 2], 'little'),
                int.from_bytes(chunk[off + 2:off + 4], 'little'),
                chunk[off + 4],
            ))
        return records, (bytes(chunk[body_len:]) if remainder == 7 else None)

    def _parse_link_chunk_sequence(self, parts: list[bytes], start_idx: int):
        part = parts[start_idx]
        if not self._looks_binary(part) or len(part) < 2:
            return None, 0

        record_count = int.from_bytes(part[:2], 'little')
        if record_count <= 0 or record_count > 4096:
            return None, 1
        body_len = 2 + record_count * 5
        max_len = body_len + 7
        raw = part
        consumed = 1
        while len(raw) <= max_len:
            records, _trailer = self._parse_link_chunk(raw)
            if records:
                return records, consumed

            # A delimiter can also be the final byte of a binary record. It is
            # absent from `split(0x0E)`, so restore it only when the declared
            # record count makes the resulting length exact.
            if len(raw) + 1 in (body_len, max_len):
                records, _trailer = self._parse_link_chunk(raw + b'\x0e')
                if records:
                    return records, consumed

            next_idx = start_idx + consumed
            if next_idx >= len(parts):
                break
            candidate = raw + b'\x0e' + parts[next_idx]
            if len(candidate) > max_len:
                break
            raw = candidate
            consumed += 1
        return None, 1

    # ── anchor table / destination IDs ──

    def _build_destination_id_targets(self, parts: list[bytes]) -> dict[int, str]:
        targets: dict[int, str] = {}
        payload_pos = 0
        offsets: list[int] = []
        for part in parts:
            offsets.append(payload_pos)
            payload_pos += len(part) + 1

        if len(self.header_binary) >= 7:
            anchor_off = (
                self.header_binary[4]
                | (self.header_binary[5] << 8)
                | (self.header_binary[6] << 16)
            )
            if anchor_off + 4 <= len(self.data):
                magic = struct.unpack_from('<H', self.data, anchor_off)[0]
                if magic == 0x2711:
                    anchor_data = self.data[anchor_off:]
                    if len(anchor_data) >= 4:
                        nbytes = struct.unpack_from('<H', anchor_data, 2)[0]
                        for idx in range(nbytes // 4):
                            val = struct.unpack_from('<I', anchor_data, 4 + idx * 4)[0]
                            if val == 0xFFFFFFFF or val < 33:
                                continue
                            target_pos = val - 33
                            chunk_idx = max(j for j, off in enumerate(offsets) if off <= target_pos)
                            is_title = (
                                chunk_idx + 1 < len(parts)
                                and self._is_title_at(parts, chunk_idx)
                            )
                            title = self._decode_chunk(parts[chunk_idx], title=is_title)
                            if title:
                                targets[idx] = title

        fixed_destinations = (
            _TEXT602_FIXED_DESTINATIONS
            if self.is_text602
            else _CALC602_FIXED_DESTINATIONS
        )
        for dest_id, (title, occurrence) in fixed_destinations.items():
            targets[dest_id] = _target_ref(title, occurrence)
        return targets

    def _resolve_dest_id_target(self, dest_id: int, text: str | None = None) -> str | None:
        target = self._dest_targets.get(dest_id)
        if target:
            return target
        if text:
            self._remember_dest_hint(dest_id, text)
            hints = tuple(self._dest_hints.get(dest_id, ()))
            return self._resolve_hint_target(dest_id, hints)
        return None

    # ── link application ──

    def _apply_link_chunks(self, items: list[dict], link_chunks: list[list]) -> None:
        # Build list of (item_idx, line_start_pos, line_end_pos, text) for visible items
        visible_positions = []
        pos = 0
        for idx, item in enumerate(items):
            if item['kind'] == '_title_pos':
                pos += item.get('buffer_len', self._raw_display_len(item['text']))
                continue
            if item['kind'] == 'separator':
                pos += 77
                continue
            if item['kind'] != 'visible':
                continue
            text = item['text']
            raw_len = self._raw_display_len(text)
            if raw_len > 0:
                visible_positions.append((idx, pos, pos + raw_len - 1, text))
            pos += raw_len

        edits: dict[int, list] = {}
        for records in link_chunks:
            for dest_id, end_pos, text_len in records:
                if text_len <= 0:
                    continue
                start_pos = end_pos - text_len + 1
                hints = self._dest_hints.get(dest_id, ())
                resolved = False
                TOL = 3
                for item_idx, line_start, line_end, line_text in visible_positions:
                    raw_line = re.sub(r'\{([^{}:]+):[^{}]*\}', r'\1', line_text)
                    raw_len = len(raw_line)
                    end_col = None
                    if line_start <= end_pos <= line_end + TOL:
                        end_col = min(raw_len - 1, end_pos - line_start)
                    elif abs(start_pos - line_start) <= TOL and text_len <= raw_len:
                        core_start = len(raw_line) - len(raw_line.lstrip(' '))
                        if raw_line.startswith('\u25a0'):
                            core_start = next((i for i, c in enumerate(raw_line) if c not in '\u25a0 '), 0)
                        end_col = core_start + text_len - 1
                        if end_col >= raw_len:
                            continue
                    if end_col is None:
                        continue
                    start_col = end_col - text_len + 1
                    if start_col < 0:
                        continue
                    if start_col > 0 and raw_line[start_col - 1].isalnum():
                        continue
                    if end_col + 1 < raw_len and raw_line[end_col + 1].isalnum():
                        continue
                    label = raw_line[start_col:end_col + 1].strip()
                    if not label:
                        continue
                    self._remember_dest_hint(dest_id, label)
                    if hints and not any(
                        self._normalize_title_key(label) == self._normalize_title_key(h) for h in hints
                    ):
                        continue
                    target = self._resolve_dest_id_target(dest_id, label) or ''
                    if target and self._normalize_title_key(target) == self._normalize_title_key(self._current_title or ''):
                        continue
                    edits.setdefault(item_idx, []).append((start_col, end_col, label, target, dest_id))
                    resolved = True
                    break

                if resolved or not hints:
                    continue

                # Hint-based fallback: find line containing hint text
                best_match = None
                best_score = None
                for item_idx, line_start, line_end, line_text in visible_positions:
                    raw_line = re.sub(r'\{([^{}:]+):[^{}]*\}', r'\1', line_text)
                    for hint in sorted(hints, key=len, reverse=True):
                        hit = raw_line.find(hint)
                        if hit < 0:
                            continue
                        start_col = hit
                        end_col = hit + len(hint) - 1
                        label = hint
                        self._remember_dest_hint(dest_id, label)
                        target = self._resolve_dest_id_target(dest_id, label)
                        if not target:
                            continue
                        if self._normalize_title_key(target) == self._normalize_title_key(self._current_title or ''):
                            continue
                        score = abs(end_pos - line_end)
                        if best_score is None or score < best_score:
                            best_match = (item_idx, start_col, end_col, label, target)
                            best_score = score
                        break
                if best_match:
                    item_idx, start_col, end_col, label, target = best_match
                    edits.setdefault(item_idx, []).append((start_col, end_col, label, target, dest_id))

        for item_idx, line_edits in edits.items():
            line_text = items[item_idx]['text']
            raw_line = re.sub(r'\{([^{}:]+):[^{}]*\}', r'\1', line_text)
            for start_col, end_col, label, target, dest_id in sorted(line_edits, key=lambda x: x[0], reverse=True):
                if raw_line[start_col:end_col + 1].strip() != label:
                    continue
                # Since we apply edits right-to-left, earlier edits (to the right)
                # don't shift the current coordinates. Check if raw text is still
                # at these coordinates (direct insert), otherwise try upgrade of
                # an existing 2-field link added by _linkify_text_line.
                if line_text[start_col:end_col + 1].strip() == label:
                    line_text = (
                        line_text[:start_col]
                        + '{' + label + ':' + target + ':' + str(dest_id) + '}'
                        + line_text[end_col + 1:]
                    )
                else:
                    upgraded = re.sub(
                        r'\{' + re.escape(label) + r':([^{}:]+)\}',
                        '{' + label + ':' + r'\1' + ':' + str(dest_id) + '}',
                        line_text, count=1,
                    )
                    if upgraded != line_text:
                        line_text = upgraded
            items[item_idx]['text'] = line_text

    def _apply_navigation_link_chunks(self, items: list[dict], link_chunks: list[list]) -> None:
        records = [record for chunk in link_chunks for record in chunk]
        if not records:
            return

        candidates: list[tuple[int, int, int, str]] = []
        for item_idx, item in enumerate(items):
            if item['kind'] != 'visible':
                continue
            plain = _plain_internal_text(item['text'])
            item['text'] = plain
            label_start = len(plain) - len(plain.lstrip(' '))
            if plain[label_start:].startswith('\u25a0'):
                label_start += 1
                while label_start < len(plain) and plain[label_start] == ' ':
                    label_start += 1
            label_end = len(plain.rstrip())
            if label_end > label_start:
                candidates.append((item_idx, label_start, label_end, plain[label_start:label_end]))

        assignments: list[tuple[int, int, int, str, str, int]] = []
        candidate_idx = 0
        for dest_id, _position, text_len in records:
            while candidate_idx < len(candidates) and len(candidates[candidate_idx][3]) != text_len:
                candidate_idx += 1
            if candidate_idx >= len(candidates):
                return
            item_idx, label_start, label_end, label = candidates[candidate_idx]
            target = self._resolve_dest_id_target(dest_id, label) or ''
            assignments.append((item_idx, label_start, label_end, label, target, dest_id))
            candidate_idx += 1

        for item_idx, label_start, label_end, label, target, dest_id in assignments:
            plain = items[item_idx]['text']
            items[item_idx]['text'] = (
                plain[:label_start]
                + '{' + label + ':' + target + ':' + str(dest_id) + '}'
                + plain[label_end:]
            )

    # ── screen processing ──

    def _find_next_title(self, parts: list[bytes], start: int) -> int | None:
        for idx in range(start, len(parts)):
            if self._is_title_at(parts, idx):
                return idx
        return None

    def _emit_title_block(self, items: list[dict], parts: list[bytes], idx: int) -> int:
        title = self._decode_chunk(parts[idx], title=True)
        self._current_title = title
        if self._is_marked_title_at(parts, idx):
            underline_idx = idx + 2
            meta_idx = idx + 3
            next_idx = idx + 4
        else:
            underline_idx = idx + 1
            meta_idx = idx + 2
            next_idx = idx + 2
        underline_len = len(self._decode_chunk(parts[underline_idx])) if underline_idx < len(parts) else 0
        items.append({
            'kind': '_title_pos',
            'text': title,
            'buffer_len': self._raw_display_len(title) + underline_len,
        })
        idx = next_idx
        if meta_idx < len(parts) and self._is_context_chunk(parts[meta_idx]):
            self._current_flag = parts[meta_idx][2]
            idx = meta_idx + 1
        elif meta_idx + 2 < len(parts) and not parts[meta_idx] and len(parts[meta_idx + 1]) == 2:
            split_meta = b'\x0e' + parts[meta_idx + 1]
            first_body_len = len(parts[meta_idx + 2]) - 2
            if int.from_bytes(split_meta[:2], 'little') == first_body_len and split_meta[2] in (0, 1):
                self._current_flag = split_meta[2]
                idx = meta_idx + 2
            else:
                self._current_flag = None
        else:
            self._current_flag = None
        return idx

    def _process_screen(self, parts: list[bytes], start_idx: int) -> tuple[dict | None, int | None]:
        items: list[dict] = []
        link_chunks: list[list] = []
        idx = self._emit_title_block(items, parts, start_idx)
        title = self._current_title or ''
        summary_expected = self._current_flag == 1
        summary_seen = False
        summary_gap_pending = False

        while idx < len(parts):
            # Next title starts a new screen
            if self._is_title_at(parts, idx):
                if self._current_flag == 0:
                    # FLAG=0: standalone screen, emit and return
                    if title in _NAV_SCREEN_TITLES:
                        self._apply_navigation_link_chunks(items, link_chunks)
                    else:
                        self._apply_link_chunks(items, link_chunks)
                    return _make_screen(title, self._current_flag, items), idx
                # FLAG!=0 (sub-screen): absorb as blank+sub-title
                items.append({'kind': 'visible', 'text': ''})
                idx = self._emit_title_block(items, parts, idx)
                summary_expected = self._current_flag == 1
                summary_seen = False
                summary_gap_pending = False
                continue

            part = parts[idx]

            if self._is_footer_chunk(part):
                footer = self._decode_chunk(part)
                items.append({'kind': 'visible', 'text': ''})
                summary_gap_pending = False
                items.append({'kind': 'visible', 'text': self._linkify_text_line(footer)})
                idx += 1
                # Skip trailing context/empty chunks after footer
                while idx < len(parts) and (self._is_context_chunk(parts[idx]) or len(parts[idx]) == 0):
                    idx += 1
                if idx < len(parts) and self._is_separator_chunk(parts[idx]):
                    items.append({'kind': 'separator', 'text': ''})
                    idx += 1
                # Collect everything up to the next title. Most screens use local
                # count-prefixed link chunks here. Some Calc602 navigation screens
                # instead store raw late-file 5-byte records without the count field.
                post_footer_parts: list[bytes] = []
                while idx < len(parts):
                    if self._is_title_at(parts, idx):
                        break
                    p = parts[idx]
                    if not self._is_context_chunk(p) and len(p) != 0:
                        post_footer_parts.append(p)
                    idx += 1

                local_idx = 0
                while local_idx < len(post_footer_parts):
                    records, consumed = self._parse_link_chunk_sequence(post_footer_parts, local_idx)
                    if records:
                        link_chunks.append(records)
                        local_idx += consumed
                        continue
                    local_idx += 1

                if title in _NAV_SCREEN_TITLES:
                    self._apply_navigation_link_chunks(items, link_chunks)
                else:
                    self._apply_link_chunks(items, link_chunks)
                return _make_screen(title, self._current_flag, items), (
                    idx if idx < len(parts) else None
                )
                break

            if self._is_context_chunk(part):
                idx += 1
                continue

            if self._is_separator_chunk(part):
                if summary_gap_pending:
                    items.append({'kind': 'visible', 'text': ''})
                    summary_gap_pending = False
                items.append({'kind': 'separator', 'text': ''})
                idx += 1
                continue

            if len(part) == 0:
                items.append({'kind': 'visible', 'text': ''})
                summary_gap_pending = False
                idx += 1
                continue

            if self._looks_binary(part):
                records, consumed = self._parse_link_chunk_sequence(parts, idx)
                if records:
                    link_chunks.append(records)
                    idx += consumed
                else:
                    idx += 1
                continue

            text = self._decode_chunk(part)
            if text:
                if summary_gap_pending:
                    items.append({'kind': 'visible', 'text': ''})
                    summary_gap_pending = False
                for line in text.split('\n'):
                    items.append({'kind': 'visible', 'text': self._linkify_text_line(line.rstrip())})
                if summary_expected and not summary_seen:
                    summary_seen = True
                    summary_gap_pending = True
            else:
                items.append({'kind': 'visible', 'text': ''})
                summary_gap_pending = False
            idx += 1

        if title in _NAV_SCREEN_TITLES:
            self._apply_navigation_link_chunks(items, link_chunks)
        else:
            self._apply_link_chunks(items, link_chunks)
        return _make_screen(title, self._current_flag, items), None


def _make_screen(title: str, flag: int | None, items: list[dict]) -> dict:
    return {'title': title, 'flag': flag, 'items': items}


# ─── UHF 2.0 conversion ──────────────────────────────────────────────────────

_TEXT602_CONTENTS_TITLE = 'Text602 | Obsah'
_TEXT602_INDEX_TITLE = 'Text602 | Abecední rejstřík nápovědy.'
_NAV_SCREEN_TITLES = {
    'Help | Obsah',
    'Help | Rejstřík',
    _TEXT602_CONTENTS_TITLE,
    _TEXT602_INDEX_TITLE,
}


@lru_cache(maxsize=8192)
def _plain_internal_text(text: str) -> str:
    return re.sub(r'\{([^{}:]+):[^{}]*?(?::\d+)?\}', r'\1', text)


@lru_cache(maxsize=8192)
def _normalize_lookup_text(text: str) -> str:
    text = _plain_internal_text(text)
    text = text.strip()
    if text.startswith('\u25a0'):
        text = text[1:].strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^0-9A-Za-zÁČĎÉĚÍĹĽŇÓŘŠŤÚŮÝŽáčďéěíĺľňóřšťúůýž]+$', '', text)
    return text.rstrip('.').strip().casefold()


@lru_cache(maxsize=8192)
def _lookup_tokens(text: str) -> tuple[str, ...]:
    normalized = _normalize_lookup_text(text)
    if not normalized:
        return ()
    return tuple(
        token
        for token in re.split(r'[^0-9A-Za-zÁČĎÉĚÍĹĽŇÓŘŠŤÚŮÝŽáčďéěíĺľňóřšťúůýž]+', normalized)
        if token
    )


def _navigation_lookup_aliases(text: str) -> tuple[str, ...]:
    plain = _plain_internal_text(text).strip()
    if not plain:
        return ()

    aliases: list[str] = [plain]
    seen = {_normalize_lookup_text(plain)}

    def add(candidate: str) -> None:
        candidate = candidate.strip()
        key = _normalize_lookup_text(candidate)
        if not key or key in seen:
            return
        seen.add(key)
        aliases.append(candidate)

    for delimiter in (' - ', ' – ', ' — ', ': '):
        if delimiter in plain:
            add(plain.split(delimiter, 1)[0])

    for delimiter in ('.', ',', ';'):
        if delimiter in plain:
            head, tail = plain.split(delimiter, 1)
            add(head)
            add(tail)

    tokens = plain.split()
    for count in (2, 3, 4):
        if len(tokens) > count:
            add(' '.join(tokens[:count]))

    return tuple(aliases)


def _title_navigation_aliases(title: str) -> tuple[str, ...]:
    aliases: list[str] = []
    configured = _NAV_TITLE_ALIAS_BY_TITLE.get(title)
    if configured:
        aliases.extend(configured)

    title_no_hotkey = re.sub(r'\s*<[^>]+>$', '', title).strip()
    if '|' in title_no_hotkey:
        section, last = (part.strip() for part in title_no_hotkey.split('|', 1))
        if section and last:
            aliases.append(f'{section} {last}')
        if section == 'Klávesnice':
            keyboard_aliases = {
                'Ruština': ('Ruská',),
                'Český psací stroj': ('Česká profesionální',),
                'Slovenský psací stroj': ('Slovenská profesionální',),
                'Speciální znaky': ('Speciální',),
                'Německá klávesnice': ('Německá',),
                'Uživatelská klávesnice KL8': ('Uživatelská 1', 'Uživatelská klávesnice 1'),
                'Uživatelská klávesnice KL9': ('Uživatelská 2', 'Uživatelská klávesnice 2'),
                'Počítačová klávesnice': ('Anglická podle IBM',),
                'Prohození Z za Y': ('Prohození Z a Y',),
            }
            aliases.extend(keyboard_aliases.get(last, ()))

    match = _NAV_GRAPH_TITLE_RE.fullmatch(_T602Parser._title_last_segment(title))
    if match:
        dimension = match.group(1).upper()
        aliases.extend((f'{dimension} graf', f'Výběr {dimension} grafu'))

    return tuple(dict.fromkeys(aliases))


def _is_candidate_text_line(text: str) -> bool:
    plain = _plain_internal_text(text).strip()
    if not plain:
        return False
    if plain.startswith(('┌', '├', '└', '│', '─')):
        return False
    if plain in {'■ Rejstřík  Obsah', '■ Obsah', '■ Rejstřík', 'Rejstřík', 'Obsah'}:
        return False
    return sum(char.isalnum() for char in plain) >= 4


def _build_navigation_target_index(screens: list[dict]) -> _NavigationIndex:
    by_key: dict[str, list[_NavCandidate]] = {}
    token_buckets: dict[str, set[_NavCandidate]] = {}
    candidates: list[_NavCandidate] = []

    def add_candidate(ctx_id: int, title: str, text: str, score: int) -> None:
        key = _normalize_lookup_text(text)
        if not key:
            return
        candidate = _NavCandidate(
            ctx_id=ctx_id,
            title=title,
            text=text,
            score=score,
            key=key,
            tokens=_lookup_tokens(text),
        )
        candidates.append(candidate)
        by_key.setdefault(key, []).append(candidate)
        for token in candidate.tokens:
            token_buckets.setdefault(token, set()).add(candidate)

    for ctx_id, screen in enumerate(screens, 1):
        title = screen['title']
        if title in _NAV_SCREEN_TITLES:
            continue

        for title_alias in {title, _T602Parser._title_last_segment(title)}:
            add_candidate(ctx_id, title, title_alias, 120)

        for title_alias in _title_navigation_aliases(title):
            add_candidate(ctx_id, title, title_alias, 118)

        plain_seen = 0
        for item in screen['items']:
            if item['kind'] != 'visible':
                continue
            item_text = item['text']
            if not _is_candidate_text_line(item_text):
                continue
            plain_seen += 1
            key = _normalize_lookup_text(item_text)
            if not key:
                continue
            score = 88 if plain_seen == 1 else max(60, 82 - plain_seen * 4)
            plain = _plain_internal_text(item_text).strip()
            if plain.endswith('.'):
                score += 8
            if plain.startswith('\u25a0'):
                score -= 15
            for alias in _navigation_lookup_aliases(item_text):
                add_candidate(ctx_id, title, alias, score)

    by_token = {token: tuple(values) for token, values in token_buckets.items()}
    return _NavigationIndex(by_key=by_key, by_token=by_token, candidates=tuple(candidates))


def _resolve_navigation_target(
    label: str,
    current_title: str,
    target_index: _NavigationIndex,
    *,
    allow_fuzzy: bool = True,
) -> str | None:
    key = _normalize_lookup_text(label)
    if not key:
        return None

    candidates = [
        candidate
        for candidate in target_index.by_key.get(key, [])
        if candidate.title != current_title
    ]
    if len(candidates) == 1:
        return candidates[0].title
    if candidates:
        ranked = sorted(candidates, key=lambda item: (-item.score, item.ctx_id, item.title, item.text))
        top_score = ranked[0].score
        top = [candidate for candidate in ranked if candidate.score == top_score]
        if len(top) == 1:
            return top[0].title
        filtered = [
            candidate
            for candidate in top
            if not candidate.title.startswith(('Help | ', 'Menu '))
            and candidate.title != 'Makrofunkce odpovídající příkazům na menu'
        ]
        if filtered:
            top = filtered
        titles = {candidate.title for candidate in top}
        if titles:
            return sorted(top, key=lambda item: (item.ctx_id, item.title, item.text))[0].title

    if not allow_fuzzy:
        return None

    fuzzy_candidates: list[tuple[_NavCandidate, int]] = []
    for candidate in target_index.candidates:
        if candidate.title == current_title:
            continue
        if key not in candidate.key and candidate.key not in key:
            continue
        score = candidate.score - abs(len(candidate.key) - len(key))
        if candidate.title.startswith('Menu '):
            score -= 35
        if candidate.title == 'Makrofunkce odpovídající příkazům na menu':
            score -= 25
        if candidate.title.startswith('Help | '):
            score -= 60
        fuzzy_candidates.append((candidate, score))

    if fuzzy_candidates:
        ranked = sorted(fuzzy_candidates, key=lambda item: (-item[1], item[0].ctx_id, item[0].title, item[0].text))
        top_score = ranked[0][1]
        top = [candidate for candidate in ranked if candidate[1] == top_score]
        if len(top) == 1 and top_score >= 55:
            return top[0][0].title
        filtered = [
            candidate
            for candidate in top
            if not candidate[0].title.startswith(('Help | ', 'Menu '))
            and candidate[0].title != 'Makrofunkce odpovídající příkazům na menu'
        ]
        if len(filtered) == 1 and top_score >= 55:
            return filtered[0][0].title

    query_tokens = set(_lookup_tokens(label))
    if len(query_tokens) <= 1:
        return None
    ranked_by_title: dict[str, tuple[float, int]] = {}
    candidate_pool: set[_NavCandidate] = set()
    for token in query_tokens:
        candidate_pool.update(target_index.by_token.get(token, ()))
    ordered_query = _lookup_tokens(label)
    for candidate in candidate_pool:
        if candidate.title == current_title or not candidate.key:
            continue
        candidate_tokens = set(candidate.tokens)
        overlap = (
            len(query_tokens & candidate_tokens) / max(len(query_tokens), len(candidate_tokens))
            if query_tokens and candidate_tokens
            else 0.0
        )
        ratio = SequenceMatcher(None, key, candidate.key).ratio()
        common_prefix = 0
        for left, right in zip(ordered_query, candidate.tokens):
            if left != right:
                break
            common_prefix += 1
        score = ratio * 100 + overlap * 60 + candidate.score * 0.2 + common_prefix * 18
        if candidate.title.startswith('Help | '):
            score -= 30
        if candidate.title.startswith('Menu '):
            score -= 20
        previous = ranked_by_title.get(candidate.title)
        if previous is None or score > previous[0] or (score == previous[0] and candidate.ctx_id < previous[1]):
            ranked_by_title[candidate.title] = (score, candidate.ctx_id)

    if not ranked_by_title:
        return None

    ranked = sorted(
        ranked_by_title.items(),
        key=lambda item: (
            -item[1][0],
            0 if '|' in item[0] else 1,
            item[1][1],
            item[0],
        ),
    )
    if len(ranked) == 1 and ranked[0][1][0] >= 92:
        return ranked[0][0]
    if ranked[0][1][0] >= 92 and ranked[0][1][0] - ranked[1][1][0] >= 10:
        return ranked[0][0]
    near_top = [item for item in ranked if ranked[0][1][0] - item[1][0] <= 2]
    if ranked[0][1][0] >= 118 and len(near_top) >= 1:
        preferred = [item for item in near_top if '|' in item[0]]
        if len(preferred) == 1:
            return preferred[0][0]
    return None


def _navigation_line_span(text: str) -> tuple[int, int, str] | None:
    stripped_start = len(text) - len(text.lstrip(' '))
    stripped = text[stripped_start:]
    if stripped.startswith('\u25a0'):
        label_start = stripped_start + 1
        while label_start < len(text) and text[label_start] == ' ':
            label_start += 1
    elif stripped_start >= 2:
        label_start = stripped_start
    else:
        return None

    label_end = len(text.rstrip())
    label = text[label_start:label_end]
    if not label:
        return None
    if len(label) > 50 or label[-1] in '.:,;':
        return None
    if sum(char.isalnum() for char in label) < 4:
        return None
    return label_start, label_end, label


def _is_footer_navigation_line(text: str) -> bool:
    plain = _plain_internal_text(text).strip()
    return plain == '\u25a0 Rejstřík  Obsah'


def _contextual_navigation_indexes(items: list[dict]) -> list[int]:
    footer_idx = next(
        (
            idx
            for idx, item in enumerate(items)
            if item['kind'] == 'visible' and _is_footer_navigation_line(item['text'])
        ),
        None,
    )
    if footer_idx is None:
        return []

    idx = footer_idx - 1
    while idx >= 0 and items[idx]['kind'] == 'visible' and not items[idx]['text'].strip():
        idx -= 1

    indexes: list[int] = []
    while idx >= 0:
        item = items[idx]
        if item['kind'] != 'visible':
            break
        if '{' in item['text'] or '}' in item['text']:
            if _navigation_line_span(_plain_internal_text(item['text'])) is None:
                break
            idx -= 1
            continue
        if _navigation_line_span(item['text']) is None:
            break
        indexes.append(idx)
        idx -= 1
    return list(reversed(indexes))


def _linkify_contextual_navigation_lines(screens: list[dict], target_index: _NavigationIndex) -> None:
    for screen in screens:
        if screen['title'] in _NAV_SCREEN_TITLES:
            continue
        for item_idx in _contextual_navigation_indexes(screen['items']):
            item = screen['items'][item_idx]
            if item['kind'] != 'visible' or '{' in item['text'] or '}' in item['text']:
                continue
            span = _navigation_line_span(item['text'])
            if span is None:
                continue
            label_start, label_end, label = span
            target = _resolve_navigation_target(label, screen['title'], target_index)
            if not target:
                continue
            item['text'] = (
                item['text'][:label_start]
                + '{'
                + label
                + ':'
                + target
                + '}'
                + item['text'][label_end:]
            )


def _learn_dest_targets_from_screens(screens: list[dict]) -> dict[int, str]:
    seen: dict[int, set[str]] = {}
    for screen in screens:
        for item in screen['items']:
            if item['kind'] != 'visible':
                continue
            for _label, target, dest_id_text in _LINK_RE.findall(item['text']):
                if not dest_id_text or not target:
                    continue
                seen.setdefault(int(dest_id_text), set()).add(target)
    return {
        dest_id: next(iter(targets))
        for dest_id, targets in seen.items()
        if len(targets) == 1
    }


def _resolve_inline_placeholders(screens: list[dict], target_index: _NavigationIndex) -> None:
    learned_targets = _learn_dest_targets_from_screens(screens)

    for screen in screens:
        current_title = screen['title']
        for item in screen['items']:
            if item['kind'] != 'visible' or '::' not in item['text']:
                continue

            def replace(match: re.Match[str]) -> str:
                label = match.group(1)
                dest_id = int(match.group(2))
                target = learned_targets.get(dest_id)
                if target is None:
                    target = _resolve_navigation_target(label, current_title, target_index)
                if target is None:
                    return match.group(0)
                return '{' + label + ':' + target + ':' + str(dest_id) + '}'

            item['text'] = _UNRESOLVED_LINK_RE.sub(replace, item['text'])


def _items_to_uhf(items: list[dict], title_to_ctx: dict[str, int]) -> list[str]:
    """Convert screen items to a flat UHF 2.0 content list."""
    content: list[str] = []
    for item in items:
        if item['kind'] in ('_title_pos', 'comment', 'ctrl'):
            continue
        if item['kind'] == 'separator':
            content.append('[rule]')
            continue
        # kind == 'visible'
        text = item['text']
        if not text:
            content.append('')
            continue
        content.append(_convert_links(text, title_to_ctx))
    while content and content[-1] == '[rule]':
        content.pop()
    return content


def _convert_links(text: str, title_to_ctx: dict[str, int]) -> str:
    """Replace {label:title} internal markup with UHF [link:...] markup."""
    parts: list[str] = []
    last_end = 0
    for m in _LINK_RE.finditer(text):
        # Escape plain text before this link
        parts.append(escape_uhf_text(text[last_end:m.start()]))
        label = m.group(1)
        target_title = m.group(2)
        ctx_id = title_to_ctx.get(target_title)
        escaped_label = escape_uhf_text(label)
        if ctx_id is not None:
            parts.append(format_uhf_link(escaped_label, topic_id=ctx_id))
        else:
            parts.append(escaped_label)
        last_end = m.end()
    parts.append(escape_uhf_text(text[last_end:]))
    return ''.join(parts)


# ─── Public reader ───────────────────────────────────────────────────────────

class T602310Reader:
    """Reader for Software602 Text602 and Calc602 help files."""

    def __init__(self, source_name: str = "", source_path=None) -> None:
        self.source_name = source_name
        self.source_path = source_path

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_t602_310_binary(data):
            raise ValueError("Input is not a Software602 Text602/Calc602 help file.")

        # Detect product name from header
        crlf = data.index(b'\r\n')
        header_str = data[:crlf].decode('ascii', errors='replace')
        if data.startswith(_CALC602_HDR):
            format_name = "calc602"
        else:
            format_name = "text602"

        parser = _T602Parser(data)
        screens = parser.parse()
        navigation_index = _build_navigation_target_index(screens)
        _resolve_inline_placeholders(screens, navigation_index)
        _linkify_contextual_navigation_lines(screens, navigation_index)

        # Assign sequential context IDs (1-based). Occurrence-qualified keys
        # keep links to duplicate original titles unambiguous.
        title_to_ctx: dict[str, int] = {}
        title_occurrences: dict[str, int] = {}
        for idx, screen in enumerate(screens, 1):
            title = screen['title']
            if not title:
                continue
            occurrence = title_occurrences.get(title, 0) + 1
            title_occurrences[title] = occurrence
            title_to_ctx.setdefault(title, idx)
            title_to_ctx[_target_ref(title, occurrence)] = idx

        if parser.is_text602:
            missing_targets = sorted({
                _target_ref(title, occurrence)
                for title, occurrence in _TEXT602_FIXED_DESTINATIONS.values()
                if _target_ref(title, occurrence) not in title_to_ctx
            })
            if missing_targets:
                raise ValueError(
                    'Text602 HelpCtx targets are missing from the HLP file: '
                    + ', '.join(repr(target) for target in missing_targets)
                )

        topics: list[TopicRecord] = []
        index_entries: list[IndexEntry] = []

        for idx, screen in enumerate(screens, 1):
            title = screen['title']
            uhf_content = _items_to_uhf(screen['items'], title_to_ctx)
            topic = TopicRecord(
                context_id=idx,
                raw_lines=[],
                names=[title] if title else [],
                uhf_content=uhf_content,
            )
            topics.append(topic)
            if title:
                index_entries.append(IndexEntry(
                    label=title.encode('utf-8'),
                    context_id=idx,
                ))

        return HelpDocument(
            format_name=format_name,
            source_name=self.source_name,
            topics=topics,
            index_entries=index_entries,
            metadata={
                'text_encoding': 'utf-8',      # labels stored as utf-8 (already decoded)
                'source_encoding': 'kamenicky', # original file encoding
                'stamp': header_str.strip(),
                'ui': dict(_TEXT602_UI_THEME),
            },
        )
