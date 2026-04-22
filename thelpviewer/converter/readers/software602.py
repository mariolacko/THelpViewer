"""Reader for Software602 Text-family help files (Text602 and Calc602).

Ported from Text602HelpDecompiler in HelpTools/python/decompiler/hldc.py.
Visible bytes are stored with a +1 offset; body is 0x0E-delimited chunks.
"""

from __future__ import annotations

import re
import struct
from difflib import SequenceMatcher

from ..base import HelpDocument, IndexEntry, TopicRecord
from ..codepages import KAMENICKY
from ..uhf_markup import escape_uhf_text, format_uhf_link

# ─── Format detection ────────────────────────────────────────────────────────

_TEXT602_HDR = b'Text602 - help'
_CALC602_HDR = b'Calc602 - help'


def is_text602_binary(data: bytes) -> bool:
    """Return True when *data* looks like a Text602 or Calc602 help file."""
    return data.startswith(_TEXT602_HDR) or data.startswith(_CALC602_HDR)


# ─── Character decode maps ───────────────────────────────────────────────────
# After subtracting 1 from stored byte, high bytes use these overrides.

_T602_TEXT: dict[int, str] = {
    0x98: '\u25A0',  # ■
    0xCE: '\u0148',  # ň
    0xD5: '\u00FA',  # ú
    0xE7: '|',
    0xF2: '\u0158',  # Ř
    0xF3: '\u0160',  # Š
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
        self.header_binary = data[crlf_pos + 2: self.header_end]
        self._current_title: str | None = None
        self._current_flag: int | None = None
        self._title_aliases: dict[str, set[str]] = {}
        self._dest_targets: dict[int, str] = {}
        self._dest_hints: dict[int, tuple[str, ...]] = {}
        self._screen_num = 0

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
            if not self._is_title_chunk(parts[idx], parts[idx + 1]):
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

    def _resolve_scoped_link_target(self, text: str, prefix: str) -> str | None:
        targets = sorted(t for t in self._candidate_targets(text) if t.startswith(prefix))
        if len(targets) == 1:
            return targets[0]
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
        if len(chunk) < 14:
            return None, None
        count = int.from_bytes(chunk[:2], 'little')
        if count <= 0 or count >= 40:
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
        if not self._looks_binary(part):
            return None, 0
        records, _trailer = self._parse_link_chunk(part)
        if records:
            return records, 1
        raw = part
        for count in range(2, 5):
            next_idx = start_idx + count - 1
            if next_idx >= len(parts):
                break
            next_part = parts[next_idx]
            if self._is_context_chunk(next_part) or not self._looks_binary(next_part):
                break
            raw += b'\x0e' + next_part
            records, _trailer = self._parse_link_chunk(raw)
            if records:
                return records, count
        return None, 1

    def _parse_late_lookup_records(self, parts: list[bytes]) -> list[tuple[int, int, int]]:
        """Decode late-file raw 5-byte records used by some Text602/Calc602 screens.

        Unlike local link chunks, these records are packed without an initial
        count field and may be split by the outer 0x0E delimiter.  The best
        observed alignment is chosen by scoring plausible `(dest_id, end_pos,
        text_len)` tuples against known destination ids and monotonically
        increasing end positions.
        """
        if not parts:
            return []
        raw = b''.join(part + b'\x0e' for part in parts)
        best_records: list[tuple[int, int, int]] = []
        best_score = -1
        for offset in range(5):
            usable = len(raw) - offset
            if usable < 10:
                continue
            records: list[tuple[int, int, int]] = []
            plausible = 0
            resolved = 0
            monotonic = 0
            previous_end = -1
            for index in range(offset, len(raw) - ((len(raw) - offset) % 5), 5):
                chunk = raw[index:index + 5]
                dest_id = chunk[0] | (chunk[1] << 8)
                end_pos = chunk[2] | (chunk[3] << 8)
                text_len = chunk[4]
                records.append((dest_id, end_pos, text_len))
                if 0 < text_len <= 80 and end_pos < 20000:
                    plausible += 1
                if end_pos >= previous_end:
                    monotonic += 1
                    previous_end = end_pos
                if self._resolve_dest_id_target(dest_id):
                    resolved += 1
            score = (resolved * 10) + (plausible * 2) + monotonic
            if score > best_score:
                best_score = score
                best_records = records

        if best_score < 0:
            return []
        return [
            (dest_id, end_pos, text_len)
            for dest_id, end_pos, text_len in best_records
            if 0 < text_len <= 80 and end_pos < 20000
        ]

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
                                and self._is_title_chunk(parts[chunk_idx], parts[chunk_idx + 1])
                            )
                            title = self._decode_chunk(parts[chunk_idx], title=is_title)
                            if title:
                                targets[idx] = title

        # Minimal fallback layer for viewer-internal fixed ids that are not
        # described by the anchor table. Only label hints are stored here; the
        # target title is still resolved from titles extracted from the file.
        known_ids: dict[int, tuple[str, ...]] = {
            3: ('Zavřít', 'Zavření okna'),
            91: ('Stránku',),
            92: ('Řádku',),
            93: ('Začátek bloku',),
            94: ('Konec bloku',),
            95: ('Začátek souboru',),
            96: ('Konec souboru',),
            102: ('Klávesnice',),
            104: ('Konfigurace',),
            105: ('Makra',),
            106: ('Rámečky',),
            107: ('Kalkulátor', 'Kalkulačka'),
            108: ('Kartotéka',),
            109: ('Kontrola pravopisu',),
            110: ('Překladové slovníky',),
            111: ('Obsah', 'Obsah nápovědy'),
            112: ('Rejstřík', 'Rejstřík nápovědy', 'Abecední rejstřík nápovědy'),
            113: ('Informace',),
            117: ('Výběr', 'Výběr makra'),
            118: ('Načtení', 'Načtení makra'),
            119: ('Uložení', 'Uložení makra'),
            120: ('Editace', 'Editace Makra'),
            133: ('Obsah', 'Obsah nápovědy'),
            134: ('Rejstřík', 'Rejstřík nápovědy', 'Abecední rejstřík nápovědy'),
            315: ('Začátek souboru',),
            316: ('Konec souboru',),
            317: ('Předchozí záznam',),
            318: ('Další záznam', 'Další'),
            321: ('Přeskočit',),
            322: ('První položku',),
            323: ('Poslední položku',),
            328: ('Vyhledat',),
            330: ('Navrhnout', 'Navrhnout formulář'),
            331: ('Vybrat', 'Vybrat formulář'),
            348: ('Záznam číslo',),
            349: ('Najít',),
            350: ('Další',),
        }
        for dest_id, label_hints in known_ids.items():
            self._remember_dest_hint(dest_id, *label_hints)
            if dest_id in targets:
                continue
            target = self._resolve_hint_target(dest_id, label_hints)
            if target:
                targets[dest_id] = target
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

    # ── screen processing ──

    def _find_next_title(self, parts: list[bytes], start: int) -> int | None:
        for idx in range(start, len(parts) - 1):
            if self._is_title_chunk(parts[idx], parts[idx + 1]):
                return idx
        return None

    def _emit_title_block(self, items: list[dict], parts: list[bytes], idx: int) -> int:
        title = self._decode_chunk(parts[idx], title=True)
        self._current_title = title
        underline_len = len(self._decode_chunk(parts[idx + 1])) if idx + 1 < len(parts) else 0
        items.append({
            'kind': '_title_pos',
            'text': title,
            'buffer_len': self._raw_display_len(title) + underline_len,
        })
        idx += 2  # skip title + underline chunks
        if idx < len(parts) and self._is_context_chunk(parts[idx]):
            self._current_flag = parts[idx][2]
            idx += 1
        else:
            self._current_flag = None
        return idx

    def _process_screen(self, parts: list[bytes], start_idx: int) -> tuple[dict | None, int | None]:
        self._screen_num += 1
        items: list[dict] = []
        link_chunks: list[list] = []
        idx = self._emit_title_block(items, parts, start_idx)
        title = self._current_title or ''

        while idx < len(parts):
            # Next title starts a new screen
            if idx + 1 < len(parts) and self._is_title_chunk(parts[idx], parts[idx + 1]):
                if self._current_flag == 0:
                    # FLAG=0: standalone screen, emit and return
                    self._apply_link_chunks(items, link_chunks)
                    return _make_screen(title, self._current_flag, items), idx
                # FLAG!=0 (sub-screen): absorb as blank+sub-title
                items.append({'kind': 'visible', 'text': ''})
                idx = self._emit_title_block(items, parts, idx)
                continue

            part = parts[idx]

            if self._is_footer_chunk(part):
                footer = self._decode_chunk(part)
                items.append({'kind': 'visible', 'text': ''})
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
                    if idx + 1 < len(parts) and self._is_title_chunk(parts[idx], parts[idx + 1]):
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

                late_records = self._parse_late_lookup_records(post_footer_parts)
                if late_records:
                    link_chunks.append(late_records)

                self._apply_link_chunks(items, link_chunks)
                return _make_screen(title, self._current_flag, items), (
                    idx if idx < len(parts) else None
                )
                break

            if self._is_context_chunk(part):
                idx += 1
                continue

            if self._is_separator_chunk(part):
                items.append({'kind': 'separator', 'text': ''})
                idx += 1
                continue

            if len(part) == 0:
                items.append({'kind': 'visible', 'text': ''})
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
                for line in text.split('\n'):
                    items.append({'kind': 'visible', 'text': self._linkify_text_line(line.rstrip())})
            else:
                items.append({'kind': 'visible', 'text': ''})
            idx += 1

        self._apply_link_chunks(items, link_chunks)
        return _make_screen(title, self._current_flag, items), None


def _make_screen(title: str, flag: int | None, items: list[dict]) -> dict:
    return {'title': title, 'flag': flag, 'items': items}


# ─── UHF 2.0 conversion ──────────────────────────────────────────────────────

_NAV_SCREEN_TITLES = {'Help | Obsah', 'Help | Rejstřík'}


def _plain_internal_text(text: str) -> str:
    return re.sub(r'\{([^{}:]+):[^{}]*?(?::\d+)?\}', r'\1', text)


def _normalize_lookup_text(text: str) -> str:
    text = _plain_internal_text(text)
    text = text.strip()
    if text.startswith('\u25a0'):
        text = text[1:].strip()
    text = text.replace('⌡', 'Ú')
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^0-9A-Za-zÁČĎÉĚÍĹĽŇÓŘŠŤÚŮÝŽáčďéěíĺľňóřšťúůýž]+$', '', text)
    return text.rstrip('.').strip().casefold()


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


def _is_candidate_text_line(text: str) -> bool:
    plain = _plain_internal_text(text).strip()
    if not plain:
        return False
    if plain.startswith(('┌', '├', '└', '│', '─')):
        return False
    if plain in {'■ Rejstřík  Obsah', '■ Obsah', '■ Rejstřík', 'Rejstřík', 'Obsah'}:
        return False
    return sum(char.isalnum() for char in plain) >= 4


def _build_navigation_target_index(screens: list[dict]) -> dict[str, list[tuple[int, str, str, int]]]:
    index: dict[str, list[tuple[int, str, str, int]]] = {}
    for ctx_id, screen in enumerate(screens, 1):
        title = screen['title']
        if title in _NAV_SCREEN_TITLES:
            continue

        for title_alias in {title, _T602Parser._title_last_segment(title)}:
            title_key = _normalize_lookup_text(title_alias)
            if title_key:
                index.setdefault(title_key, []).append((ctx_id, title, title_alias, 120))

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
                alias_key = _normalize_lookup_text(alias)
                if alias_key:
                    index.setdefault(alias_key, []).append((ctx_id, title, alias, score))
    return index


def _resolve_navigation_target(
    label: str,
    current_title: str,
    target_index: dict[str, list[tuple[int, str, str, int]]],
) -> str | None:
    key = _normalize_lookup_text(label)
    if not key:
        return None

    candidates = [
        candidate
        for candidate in target_index.get(key, [])
        if candidate[1] != current_title
    ]
    if len(candidates) == 1:
        return candidates[0][1]
    if candidates:
        ranked = sorted(candidates, key=lambda item: (-item[3], item[0], item[1], item[2]))
        top_score = ranked[0][3]
        top = [candidate for candidate in ranked if candidate[3] == top_score]
        if len(top) == 1:
            return top[0][1]
        filtered = [
            candidate
            for candidate in top
            if not candidate[1].startswith(('Help | ', 'Menu '))
            and candidate[1] != 'Makrofunkce odpovídající příkazům na menu'
        ]
        if filtered:
            top = filtered
        titles = {candidate[1] for candidate in top}
        if titles:
            return sorted(top, key=lambda item: (item[0], item[1], item[2]))[0][1]

    fuzzy_candidates: list[tuple[int, str, str, int]] = []
    for values in target_index.values():
        for candidate in values:
            if candidate[1] == current_title:
                continue
            candidate_key = _normalize_lookup_text(candidate[2])
            if not candidate_key or (key not in candidate_key and candidate_key not in key):
                continue
            score = candidate[3] - abs(len(candidate_key) - len(key))
            if candidate[1].startswith('Menu '):
                score -= 35
            if candidate[1] == 'Makrofunkce odpovídající příkazům na menu':
                score -= 25
            if candidate[1].startswith('Help | '):
                score -= 60
            fuzzy_candidates.append((candidate[0], candidate[1], candidate[2], score))

    if fuzzy_candidates:
        ranked = sorted(fuzzy_candidates, key=lambda item: (-item[3], item[0], item[1], item[2]))
        top_score = ranked[0][3]
        top = [candidate for candidate in ranked if candidate[3] == top_score]
        if len(top) == 1 and top_score >= 55:
            return top[0][1]
        filtered = [
            candidate
            for candidate in top
            if not candidate[1].startswith(('Help | ', 'Menu '))
            and candidate[1] != 'Makrofunkce odpovídající příkazům na menu'
        ]
        if len(filtered) == 1 and top_score >= 55:
            return filtered[0][1]

    query_tokens = set(_lookup_tokens(label))
    if len(query_tokens) <= 1:
        return None
    ranked_by_title: dict[str, tuple[float, int]] = {}
    for values in target_index.values():
        for ctx_id, title, candidate_text, base_score in values:
            if title == current_title:
                continue
            candidate_key = _normalize_lookup_text(candidate_text)
            if not candidate_key:
                continue
            candidate_tokens = set(_lookup_tokens(candidate_text))
            overlap = (
                len(query_tokens & candidate_tokens) / max(len(query_tokens), len(candidate_tokens))
                if query_tokens and candidate_tokens
                else 0.0
            )
            ratio = SequenceMatcher(None, key, candidate_key).ratio()
            prefix_bonus = 0.0
            if candidate_tokens and query_tokens:
                ordered_query = list(_lookup_tokens(label))
                ordered_candidate = list(_lookup_tokens(candidate_text))
                common_prefix = 0
                for left, right in zip(ordered_query, ordered_candidate):
                    if left != right:
                        break
                    common_prefix += 1
                prefix_bonus = common_prefix * 18
            score = ratio * 100 + overlap * 60 + base_score * 0.2 + prefix_bonus
            if title.startswith('Help | '):
                score -= 30
            if title.startswith('Menu '):
                score -= 20
            previous = ranked_by_title.get(title)
            if previous is None or score > previous[0] or (score == previous[0] and ctx_id < previous[1]):
                ranked_by_title[title] = (score, ctx_id)

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


def _linkify_navigation_screens(screens: list[dict]) -> None:
    target_index = _build_navigation_target_index(screens)
    for screen in screens:
        if screen['title'] not in _NAV_SCREEN_TITLES:
            continue
        for item in screen['items']:
            if item['kind'] != 'visible':
                continue
            text = item['text']
            stripped = text.strip()
            if not stripped or '{' in text:
                continue
            if stripped in {'\u25a0 Rejstřík', '\u25a0 Obsah', 'Rejstřík', 'Obsah'}:
                continue
            if stripped.startswith('\u25a0'):
                continue
            target = _resolve_navigation_target(stripped, screen['title'], target_index)
            if not target:
                continue
            leading = text[:len(text) - len(text.lstrip(' '))]
            item['text'] = leading + '{' + stripped + ':' + target + '}'

        for item in screen['items']:
            if item['kind'] != 'visible' or '::' not in item['text'] or '[link:' in item['text']:
                continue
            plain = _plain_internal_text(item['text']).strip()
            if not plain or plain.startswith('\u25a0'):
                continue
            target = _resolve_navigation_target(plain, screen['title'], target_index)
            if not target:
                continue
            leading = item['text'][:len(item['text']) - len(item['text'].lstrip(' '))]
            item['text'] = leading + '{' + plain + ':' + target + '}'


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


def _resolve_inline_placeholders(screens: list[dict]) -> None:
    target_index = _build_navigation_target_index(screens)
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

class Text602Reader:
    """Reader for Software602 Text602 and Calc602 help files."""

    def __init__(self, source_name: str = "", source_path=None) -> None:
        self.source_name = source_name
        self.source_path = source_path

    def read_bytes(self, data: bytes) -> HelpDocument:
        if not is_text602_binary(data):
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
        _resolve_inline_placeholders(screens)
        _linkify_navigation_screens(screens)

        # Assign sequential context IDs (1-based); map title → context_id
        title_to_ctx: dict[str, int] = {}
        for idx, screen in enumerate(screens, 1):
            if screen['title'] and screen['title'] not in title_to_ctx:
                title_to_ctx[screen['title']] = idx

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
            },
        )
