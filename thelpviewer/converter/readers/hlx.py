"""Reader for textual HLX source files across supported help dialects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from ..base import (
    CommentRecord,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    PositionedKeyword,
    TopicRecord,
    build_directional_nav_items,
    ensure_document_index,
)


SCREEN_RE = re.compile(r"^;(?:SCREEN|PAGE)\s+(.+)$")
KEYWORD4_RE = re.compile(
    r"^;KEYWORD4\s+(\d+)\s+AT\s+\((\d+),(\d+)-(\d+)\)(?:\s+NAV\s+\((\d+),(\d+),(\d+),(\d+)\))?$"
)
LINK_RE = re.compile(r"^;LINK\s+UP\s+(\d+)\s+DOWN\s+(\d+)$")
INDEXORDER_RE = re.compile(r"^;INDEXORDER\s+(\d+)\s+(.+)$")
UNUSEDCTX_RE = re.compile(r"^;UNUSEDCTX\s+(\d+)\s+((?:0x)?[0-9A-Fa-f]+)$")


@dataclass(slots=True)
class PendingInlineLink:
    """One brace-delimited HLX link waiting for post-parse target resolution."""

    label: bytes
    target_text: str | None = None
    raw_target: int | None = None


def detect_hlx_source_format(data: bytes) -> str:
    """Return the most likely source dialect for one textual HLX buffer."""
    header = data[:4096]
    if b";STAMP (c) Software602 HelpSystem" in header or b"Software602 helpfile" in header:
        return "m602"
    if b";STAMP Text602 - help" in header or b";STAMP Calc602 - help" in header or b";S602" in header:
        return "software602"
    if b";STAMP TURBO PASCAL HELP FILE." in header or b";SIGNATURE $*$* &&&&$*$" in header:
        return "borland"
    return "hlx"


def is_hlx_source(data: bytes) -> bool:
    """Return ``True`` when the buffer looks like line-oriented HLX text."""
    return any(marker in data[:4096] for marker in (b";SCREEN", b";PAGE", b";STAMP", b";COMMENT"))


class HlxSourceParser:
    """Parse textual HLX source directly into the shared document model."""

    def __init__(
        self,
        data: bytes,
        source_name: str = "input.hlx",
        source_path: str | Path | None = None,
        from_cp: str | None = None,
    ):
        from ..codepages import guess_display_encoding
        self.data = data
        self.source_name = source_name
        self.source_path = Path(source_path) if source_path is not None else None
        self.lines = data.splitlines()
        self.comments: list[CommentRecord] = []
        self.topics: list[TopicRecord] = []
        self.index_entries: list[IndexEntry] = []
        self.pending_inline_links: dict[int, list[tuple[int, PendingInlineLink]]] = {}
        self.metadata: dict[str, object] = {
            "stamp": None,
            "signature": None,
            "format_version": None,
            "text_version": None,
            "height": None,
            "width": None,
            "left_margin": 0,
            "description": None,
            "help_contents_topic_id": None,
            "casesense": False,
            "context_count": None,
            "text_encoding": None,
            "unused_contexts": {},
            "index_order": [],
            "tag_order": [],
            "s602_anchor_table_hex": None,
        }
        self.in_comment_block = False
        self.current_topic: TopicRecord | None = None
        self.format_name = detect_hlx_source_format(data)
        # autodetect encoding if not given
        if from_cp:
            self.metadata["text_encoding"] = from_cp
        else:
            # Use first 32 lines or 8 KB for detection
            sample = self.lines[:32] if len(self.lines) > 32 else self.lines[:]
            hint = source_name or ""
            encoding = guess_display_encoding(sample, hint)
            self.metadata["text_encoding"] = encoding

    def parse(self) -> HelpDocument:
        """Parse the whole HLX text buffer into the normalized document model."""
        for raw_line in self.lines:
            self._handle_line(raw_line)
        self._flush_topic()
        self._resolve_pending_inline_links()
        self._synthesize_missing_index_entries()
        self._dedupe_index_entries()
        for topic in self.topics:
            topic.nav_items = build_directional_nav_items(topic)
        return ensure_document_index(HelpDocument(
            format_name=self.format_name,
            source_name=self.source_name,
            topics=self.topics,
            index_entries=self.index_entries,
            comments=self.comments,
            metadata=self.metadata,
            binary_data=None,
        ))

    def _handle_line(self, raw_line: bytes) -> None:
        line_str = raw_line.decode("latin-1")

        if line_str == ";CBEGIN":
            self.in_comment_block = True
            return
        if line_str == ";CEND":
            self.in_comment_block = False
            return
        if self.in_comment_block:
            return

        if line_str.startswith(";STAMP "):
            self.metadata["stamp"] = line_str[7:]
            self.format_name = self._normalize_format_name(self.format_name, line_str[7:])
            if self.format_name in {"m602", "software602"} and self.metadata["text_encoding"] is None:
                self.metadata["text_encoding"] = "kamenicky"
            return
        if line_str.startswith(";SIGNATURE "):
            self.metadata["signature"] = line_str[11:]
            return
        if line_str.startswith(";VERSION "):
            self.metadata["text_version"] = int(line_str[9:].strip())
            return
        if line_str.startswith(";S602ANCHORTABLE "):
            self.metadata["s602_anchor_table_hex"] = line_str[17:].strip()
            self.comments.append(CommentRecord(text=line_str[1:], topic_context=None))
            return
        if line_str.startswith(";HEIGHT "):
            self.metadata["height"] = int(line_str[8:].strip())
            return
        if line_str.startswith(";WIDTH "):
            self.metadata["width"] = int(line_str[7:].strip())
            return
        if line_str.startswith(";LMARGIN "):
            self.metadata["left_margin"] = int(line_str[9:].strip())
            return
        if line_str == ";CASESENSE":
            self.metadata["casesense"] = True
            return
        if line_str.startswith(";DESCRIPTION "):
            self.metadata["description"] = line_str[13:]
            return
        if line_str.startswith(";CONTEXTCOUNT "):
            self.metadata["context_count"] = int(line_str[14:].strip())
            return

        match = UNUSEDCTX_RE.match(line_str)
        if match:
            self.metadata["unused_contexts"][int(match.group(1))] = int(match.group(2), 16)
            return

        match = INDEXORDER_RE.match(line_str)
        if match:
            context_id = int(match.group(1))
            label = match.group(2).encode("latin-1")
            self.metadata["index_order"].append((match.group(2), context_id))
            self.index_entries.append(IndexEntry(label=label, context_id=context_id))
            return

        if line_str.startswith(";TAGORDER "):
            self.metadata["tag_order"].append(line_str[10:])
            self.comments.append(CommentRecord(text=line_str[1:], topic_context=self._current_context()))
            return

        if line_str.startswith(";COMMENT "):
            self.comments.append(CommentRecord(text=line_str[9:], topic_context=self._current_context()))
            alias_match = re.match(r"^;COMMENT\s+ALIASCTX\s+(\d+)$", line_str)
            if alias_match and self.current_topic is not None:
                self.current_topic.alias_contexts.append(int(alias_match.group(1)))
                return
            version_match = re.search(r"FormatVersion\s+(\d+)", line_str)
            if version_match:
                self.metadata["format_version"] = int(version_match.group(1))
            return

        match = SCREEN_RE.match(line_str)
        if match:
            self._start_topic(match.group(1))
            return

        if line_str == ";ENDSCREEN":
            self._flush_topic()
            return

        match = KEYWORD4_RE.match(line_str)
        if match and self.current_topic is not None:
            navigation = (
                tuple(int(match.group(index)) for index in range(5, 9))
                if match.group(5)
                else (None, None, None, None)
            )
            self.current_topic.positional_keywords.append(
                PositionedKeyword(
                    target_context=int(match.group(1)),
                    line=int(match.group(2)),
                    first_column=int(match.group(3)),
                    last_column=int(match.group(4)),
                    navigation=navigation,
                )
            )
            return

        if line_str.startswith(";KEYWORD ") and self.current_topic is not None:
            self.current_topic.sequential_keywords.append(int(line_str[9:].strip()))
            return

        if line_str.startswith(";INDEX ") and self.current_topic is not None:
            label = line_str[7:].encode("latin-1")
            self.current_topic.index_terms.append(label)
            self.index_entries.append(IndexEntry(label=label, context_id=self.current_topic.context_id))
            return

        if line_str.startswith(";ALIASCTX ") and self.current_topic is not None:
            self.current_topic.alias_contexts.append(int(line_str[10:].strip()))
            return

        if line_str.startswith(";HELP_CONTENTS") and self.current_topic is not None:
            self.current_topic.is_help_contents = True
            self.metadata["help_contents_topic_id"] = self.current_topic.context_id
            return

        match = LINK_RE.match(line_str)
        if match and self.current_topic is not None:
            self.current_topic.up_context = int(match.group(1))
            self.current_topic.down_context = int(match.group(2))
            return

        if line_str.startswith(";SCREENTAG ") or line_str.startswith(";TEXTCOMPLETE"):
            self.comments.append(CommentRecord(text=line_str[1:], topic_context=self._current_context()))
            return

        if line_str.startswith(";S602"):
            self.comments.append(CommentRecord(text=line_str[1:], topic_context=self._current_context()))
            return

        if line_str.startswith(";") and not self.current_topic:
            self.comments.append(CommentRecord(text=line_str[1:], topic_context=None))
            return

        if self.current_topic is None:
            return

        line_bytes, link_refs = self._rewrite_brace_links(raw_line)
        self.current_topic.raw_lines.append(line_bytes)
        if not link_refs:
            return
        pending = self.pending_inline_links.setdefault(self.current_topic.context_id, [])
        for link_ref in link_refs:
            sequence_index = len(self.current_topic.sequential_keywords)
            self.current_topic.sequential_keywords.append(-1)
            pending.append((sequence_index, link_ref))

    def _start_topic(self, context_token: str) -> None:
        self._flush_topic()
        context_id = self._parse_context_token(context_token)
        self.current_topic = TopicRecord(context_id=context_id, raw_lines=[])

    def _flush_topic(self) -> None:
        if self.current_topic is None:
            return
        title = self._topic_title(self.current_topic.raw_lines)
        if title:
            self.current_topic.names = [self._decode_source_text(title)]
            if not self.current_topic.index_terms:
                self.current_topic.index_terms.append(title)
        self.topics.append(self.current_topic)
        self.current_topic = None

    def _synthesize_missing_index_entries(self) -> None:
        if self.index_entries:
            return
        for topic in self.topics:
            title = self._topic_title(topic.raw_lines)
            if title:
                self.index_entries.append(IndexEntry(label=title, context_id=topic.context_id))

    def _dedupe_index_entries(self) -> None:
        seen: set[tuple[bytes, int]] = set()
        unique_entries: list[IndexEntry] = []
        for entry in self.index_entries:
            key = (entry.label, entry.context_id)
            if key in seen:
                continue
            seen.add(key)
            unique_entries.append(entry)
        self.index_entries = unique_entries

    @staticmethod
    def _parse_context_token(token: str) -> int:
        token = token.strip()
        if token.startswith("noscreen"):
            suffix = token[8:]
            return int(suffix) if suffix.isdigit() else 0xFFFF
        return int(token)

    def _rewrite_brace_links(self, raw_line: bytes) -> tuple[bytes, list[PendingInlineLink]]:
        """Translate brace-delimited HLX links to the renderer's `0x02` format."""
        output = bytearray()
        link_refs: list[PendingInlineLink] = []
        index = 0

        while index < len(raw_line):
            if raw_line[index:index + 2] == b"{{":
                output.append(ord("{"))
                index += 2
                continue
            if raw_line[index:index + 1] != b"{":
                output.append(raw_line[index])
                index += 1
                continue

            end = raw_line.find(b"}", index + 1)
            if end < 0:
                output.append(raw_line[index])
                index += 1
                continue

            inner = raw_line[index + 1:end]
            if b":" not in inner:
                output.extend(raw_line[index:end + 1])
                index = end + 1
                continue

            parts = inner.split(b":")
            label_bytes = parts[0]
            target_text = None
            raw_target = None

            if not label_bytes:
                output.extend(raw_line[index:end + 1])
                index = end + 1
                continue

            if len(parts) >= 3 and self._is_ascii_int(parts[-1]):
                raw_target = int(parts[-1].decode("ascii").strip())
                target_blob = b":".join(parts[1:-1]).strip()
                if target_blob:
                    target_text = self._decode_source_text(target_blob)
            elif len(parts) == 2 and self._is_ascii_int(parts[1]):
                raw_target = int(parts[1].decode("ascii").strip())
            else:
                target_blob = b":".join(parts[1:]).strip()
                if not target_blob:
                    output.extend(raw_line[index:end + 1])
                    index = end + 1
                    continue
                target_text = self._decode_source_text(target_blob)

            output.append(0x02)
            output.extend(label_bytes)
            output.append(0x02)
            link_refs.append(PendingInlineLink(label=label_bytes, target_text=target_text, raw_target=raw_target))
            index = end + 1

        return bytes(output), link_refs

    @staticmethod
    def _topic_title(raw_lines: list[bytes]) -> bytes | None:
        for raw_line in raw_lines:
            title = raw_line.replace(b"\x02", b"").strip()
            if title:
                return title
        return None

    @staticmethod
    def _normalize_format_name(current: str, stamp: str) -> str:
        if "Software602 HelpSystem" in stamp:
            return "m602"
        if "Text602 - help" in stamp or "Calc602 - help" in stamp:
            return "software602"
        if "TURBO PASCAL HELP FILE." in stamp:
            return "borland"
        return current

    def _current_context(self) -> int | None:
        return self.current_topic.context_id if self.current_topic is not None else None

    def _resolve_pending_inline_links(self) -> None:
        """Resolve post-parse brace links once all topic titles are known."""
        if not self.pending_inline_links:
            return

        title_aliases = self._build_title_aliases()
        known_dest_ids = self._build_software602_known_destinations(title_aliases)
        m602_target_map = self._build_m602_source_target_map()

        for topic in self.topics:
            pending = self.pending_inline_links.get(topic.context_id, [])
            if not pending:
                continue
            for sequence_index, link_ref in pending:
                topic.sequential_keywords[sequence_index] = self._resolve_inline_link(
                    topic.context_id,
                    link_ref,
                    title_aliases,
                    known_dest_ids,
                    m602_target_map,
                )

    def _resolve_inline_link(
        self,
        topic_context: int,
        link_ref: PendingInlineLink,
        title_aliases: dict[str, set[int]],
        known_dest_ids: dict[int, int],
        m602_target_map: dict[int, int],
    ) -> int:
        """Resolve one inline source link to a final topic context or ``-1``."""
        if link_ref.target_text:
            target_context = self._resolve_title_context(link_ref.target_text, title_aliases, topic_context)
            if target_context is not None:
                return target_context

        if self.format_name == "software602" and link_ref.raw_target is not None:
            if link_ref.raw_target in known_dest_ids:
                return known_dest_ids[link_ref.raw_target]
            target_context = self._resolve_title_context(self._decode_source_text(link_ref.label), title_aliases, topic_context)
            if target_context is not None:
                return target_context
            return -1

        if self.format_name == "m602" and link_ref.raw_target is not None:
            return m602_target_map.get(link_ref.raw_target, -1)

        if link_ref.raw_target is not None:
            return link_ref.raw_target

        return -1

    def _build_m602_source_target_map(self) -> dict[int, int]:
        """Resolve M602 raw source targets from labels and titles inside the same HLX file."""
        if self.format_name != "m602":
            return {}
        from .m602 import build_m602_binary_target_context_map, build_m602_target_context_map, is_m602_binary, M602BinaryParser

        exact_map = self._load_m602_companion_target_map(
            build_m602_binary_target_context_map=build_m602_binary_target_context_map,
            is_m602_binary=is_m602_binary,
            parser_type=M602BinaryParser,
        )
        if exact_map:
            self.metadata["link_target_resolution"] = "binary_tail_exact_companion"
            return exact_map

        occurrences: list[tuple[int, int, str]] = []
        for topic in self.topics:
            pending = self.pending_inline_links.get(topic.context_id, [])
            for _sequence_index, link_ref in pending:
                if link_ref.raw_target is None:
                    continue
                occurrences.append(
                    (
                        topic.context_id,
                        link_ref.raw_target,
                        self._decode_source_text(link_ref.label),
                    )
                )

        resolved = build_m602_target_context_map(
            self.topics,
            occurrences,
            text_encoding=str(self.metadata.get("text_encoding") or "latin1"),
        )
        if resolved:
            self.metadata["link_target_resolution"] = "label_title_matching"
        return resolved

    def _load_m602_companion_target_map(
        self,
        *,
        build_m602_binary_target_context_map,
        is_m602_binary,
        parser_type,
    ) -> dict[int, int]:
        """Load exact M602 raw target mapping from a nearby companion binary if present."""
        if self.source_path is None:
            return {}

        candidate_names: list[str] = []
        stem = self.source_path.stem
        candidate_names.append(stem)
        if stem.lower().endswith(".utf8"):
            candidate_names.append(stem[:-5])

        source_context_ids = {topic.context_id for topic in self.topics}
        for candidate_name in dict.fromkeys(candidate_names):
            for suffix in (".HLP", ".hlp"):
                candidate_path = self.source_path.with_name(f"{candidate_name}{suffix}")
                if not candidate_path.exists():
                    continue
                binary_data = candidate_path.read_bytes()
                if not is_m602_binary(binary_data):
                    continue
                parser = parser_type(binary_data)
                parsed_topics = parser.parse()
                exact_map = build_m602_binary_target_context_map(
                    binary_data,
                    parsed_topics,
                    tail_offset=getattr(parser, "binary_index_offset", None),
                )
                if not exact_map:
                    continue
                filtered_map = {
                    raw_target: context_id
                    for raw_target, context_id in exact_map.items()
                    if context_id in source_context_ids
                }
                if filtered_map:
                    return filtered_map

        return {}

    def _build_title_aliases(self) -> dict[str, set[int]]:
        """Build a normalized title/alias map for source-level target resolution."""
        alias_map: dict[str, set[int]] = {}
        for topic in self.topics:
            title_bytes = self._topic_title(topic.raw_lines)
            if title_bytes is None:
                continue
            title = self._decode_source_text(title_bytes.replace(b"\x02", b""))
            if not title:
                continue
            title_no_hotkey = re.sub(r"\s*<[^>]+>$", "", title).rstrip()
            self._register_title_alias(alias_map, title, topic.context_id)
            self._register_title_alias(alias_map, title_no_hotkey, topic.context_id)

            if title_no_hotkey.startswith("Menu "):
                self._register_title_alias(alias_map, title_no_hotkey[5:].strip(), topic.context_id)

            if "|" not in title_no_hotkey:
                continue

            segments = [segment.strip() for segment in title_no_hotkey.split("|") if segment.strip()]
            if not segments:
                continue

            last = segments[-1]
            self._register_title_alias(alias_map, last, topic.context_id)

            if last == "Otevření":
                self._register_title_alias(alias_map, "Otevřít", topic.context_id)
            if segments[0] == "Klávesnice" and "klávesnice" not in last.casefold():
                self._register_title_alias(alias_map, f"{last} klávesnice", topic.context_id)
            if segments[0] == "Soubor":
                if last == "Nový":
                    self._register_title_alias(alias_map, "Nový soubor", topic.context_id)
                if last == "Otevření":
                    self._register_title_alias(alias_map, "Otevřít soubor", topic.context_id)
                    self._register_title_alias(alias_map, "Otevřít databázový soubor", topic.context_id)
                if last == "Uložit":
                    self._register_title_alias(alias_map, "Uložit soubor", topic.context_id)
                    self._register_title_alias(alias_map, "Uložit databázový soubor", topic.context_id)
                if last == "Zapsat jako":
                    self._register_title_alias(alias_map, "Zapsat soubor pod jménem", topic.context_id)
                    self._register_title_alias(alias_map, "Zapsat databázový soubor pod jménem", topic.context_id)
                if last == "Import":
                    self._register_title_alias(alias_map, "Import textu", topic.context_id)
                if last == "Export":
                    self._register_title_alias(alias_map, "Export textu", topic.context_id)
            if segments[0] == "Blok":
                self._register_title_alias(alias_map, f"{last} bloku", topic.context_id)
            if segments[0] == "Makra":
                if last == "Načtení":
                    self._register_title_alias(alias_map, "Načtení makra", topic.context_id)
                if last == "Uložení":
                    self._register_title_alias(alias_map, "Uložení makra", topic.context_id)
                if last == "Editace":
                    self._register_title_alias(alias_map, "Editace Makra", topic.context_id)
            if segments[0] == "Formulář":
                if last == "Vybrat":
                    self._register_title_alias(alias_map, "Vybrat formulář", topic.context_id)
                if last == "Navrhnout":
                    self._register_title_alias(alias_map, "Navrhnout formulář", topic.context_id)
            if segments[0] == "Text602" and last == "Obsah":
                self._register_title_alias(alias_map, "Obsah nápovědy", topic.context_id)
            if segments[0] in {"Text602", "Help"} and "Abecední rejstřík nápovědy" in last:
                self._register_title_alias(alias_map, "Rejstřík", topic.context_id)
                self._register_title_alias(alias_map, "Rejstřík nápovědy", topic.context_id)
                self._register_title_alias(alias_map, "Abecední rejstřík nápovědy", topic.context_id)
            if segments[0] == "Help" and last == "Obsah":
                self._register_title_alias(alias_map, "Obsah nápovědy", topic.context_id)

        return alias_map

    @staticmethod
    def _normalize_title_key(text: str) -> str:
        """Normalize titles so source target strings can be matched robustly."""
        text = re.sub(r"\s+", " ", text.strip())
        text = re.sub(r"\s*<[^>]+>$", "", text).rstrip()
        return text.rstrip(".").casefold()

    @classmethod
    def _register_title_alias(cls, alias_map: dict[str, set[int]], alias: str, context_id: int) -> None:
        """Register one source-level title alias."""
        key = cls._normalize_title_key(alias)
        if not key:
            return
        alias_map.setdefault(key, set()).add(context_id)

    def _resolve_title_context(
        self,
        target_text: str,
        alias_map: dict[str, set[int]],
        topic_context: int,
    ) -> int | None:
        """Resolve one textual target name to a topic context."""
        key = self._normalize_title_key(target_text)
        contexts = sorted(alias_map.get(key, ()))
        if not contexts:
            return None
        if len(contexts) == 1:
            return contexts[0]
        for context_id in contexts:
            if context_id != topic_context:
                return context_id
        return contexts[0]

    def _build_software602_known_destinations(self, alias_map: dict[str, set[int]]) -> dict[int, int]:
        """Resolve special Text602/Calc602 destination ids that are not topic ids."""
        if self.format_name != "software602":
            return {}

        known_aliases: dict[int, str] = {
            3: "Zavřít",
            77: "Zavřít",
            78: "Zavřít",
            91: "Stránku",
            92: "Řádku",
            93: "Začátek bloku",
            94: "Konec bloku",
            95: "Začátek souboru",
            96: "Konec souboru",
            102: "Klávesnice",
            104: "Konfigurace",
            105: "Makra",
            106: "Rámečky",
            107: "Kalkulačka",
            108: "Kartotéka",
            109: "Kontrola pravopisu",
            110: "Překladové slovníky",
            111: "Obsah nápovědy",
            112: "Rejstřík nápovědy",
            113: "Informace",
            117: "Výběr makra",
            118: "Načtení makra",
            119: "Uložení makra",
            120: "Editace Makra",
            133: "Obsah nápovědy",
            134: "Rejstřík nápovědy",
            315: "Začátek souboru",
            316: "Konec souboru",
            317: "Předchozí záznam",
            318: "Další záznam",
            321: "Přeskočit",
            322: "První položku",
            323: "Poslední položku",
            328: "Vyhledat",
            330: "Navrhnout formulář",
            331: "Vybrat formulář",
            348: "Záznam číslo",
            349: "Najít",
            350: "Další",
        }
        resolved: dict[int, int] = {}
        for dest_id, alias in known_aliases.items():
            context_id = self._resolve_title_context(alias, alias_map, topic_context=-1)
            if context_id is not None:
                resolved[dest_id] = context_id
        return resolved

    @staticmethod
    def _is_ascii_int(value: bytes) -> bool:
        """Return `True` when the byte slice contains a plain ASCII integer."""
        try:
            return value.decode("ascii").strip().isdigit()
        except UnicodeDecodeError:
            return False

    @staticmethod
    def _detect_source_text_encoding(data: bytes) -> str | None:
        """Detect UTF-8 HLX sources; otherwise keep legacy byte interpretation."""
        if not any(value >= 0x80 for value in data):
            return None
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return "utf-8"

    def _decode_source_text(self, data: bytes) -> str:
        encoding = self.metadata.get("text_encoding")
        if encoding == "utf-8":
            return data.decode("utf-8", errors="replace")
        if isinstance(encoding, str) and encoding:
            from .codepages import decode_bytes

            return decode_bytes(data, encoding)
        return data.decode("latin-1", errors="ignore")

def parse_hlx_data(
    data: bytes,
    source_name: str = "input.hlx",
    source_path: str | Path | None = None,
    from_cp: str | None = None,
) -> HelpDocument:
    """Compatibility wrapper around ``HlxSourceParser``."""
    return HlxSourceParser(
        data,
        source_name=source_name,
        source_path=source_path,
        from_cp=from_cp,
    ).parse()


class HlxHelpReader(HelpReaderBase):
    """Read textual HLX source and normalize it into the shared document model."""

    def read_bytes(self, data: bytes) -> HelpDocument:
        """Parse one HLX text buffer into ``HelpDocument``."""
        return HlxSourceParser(
            data,
            source_name=self.source_name,
            source_path=self.source_path,
        ).parse()
