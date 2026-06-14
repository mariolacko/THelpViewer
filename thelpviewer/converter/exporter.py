"""Helpers for loading help files and exporting them to HTML trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Callable

from .base import HelpDocument
from .readers.bw03 import BW03HelpReader, is_bw03_binary
from .readers.hlx import HlxHelpReader, is_hlx_source
from .readers.hlx_binary import HlxBinaryReader, is_hlx_binary
from .readers.m602 import M602HelpReader, is_m602_binary
from .readers.thelp import ThelpHelpReader, is_thelp_binary
from .readers.ng import NGReader, is_ng_binary
from .readers.quickhelp import QuickHelpReader, is_quickhelp_binary
from .readers.game_cheater import GameCheaterReader, is_game_cheater_database
from .readers.scorpion_reader import ScorpionReader, detect_scorpion_reader_family
from .readers.software602 import Text602Reader, is_text602_binary
from .readers.tdh import TdhHelpReader, is_tdh_binary, is_tfh_binary
from .codepages import decode_bytes, guess_display_encoding, is_czech_encoding_hint
from .help_database import lookup_help_database_entry
from .readers.fbhf import FBHFHelpReader, FBHFSourceReader, is_fbhf_binary, is_fbhf_source
from .writers.html import HelpHtmlRenderer


def _clean_dir(path: Path) -> None:
    """Remove all contents of *path* without removing the directory itself."""
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


@dataclass(slots=True)
class ExportResult:
    """Summary of one exported help file."""

    input_path: Path
    output_dir: Path
    format_name: str
    encoding: str
    html_count: int
    json_path: Path | None = None


@dataclass(frozen=True, slots=True)
class FormatHandler:
    """One format matcher plus the corresponding document loader."""

    name: str
    source_kind: str
    matches: Callable[[Path, bytes], bool]
    load: Callable[[Path, bytes], HelpDocument]


def _build_reader_document(reader_cls, path: Path, data: bytes) -> HelpDocument:
    """Instantiate one standard reader and parse already loaded bytes."""
    return reader_cls(source_name=path.name, source_path=path).read_bytes(data)


def _load_fbhf_source(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(FBHFSourceReader, path, data)


def _load_hlx(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(HlxHelpReader, path, data)


def _load_hlx_binary(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(HlxBinaryReader, path, data)


def _load_ng(path: Path, data: bytes) -> HelpDocument:
    return NGReader(path).read_bytes(data)


def _load_bw03(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(BW03HelpReader, path, data)


def _load_quickhelp(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(QuickHelpReader, path, data)


def _load_game_cheater(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(GameCheaterReader, path, data)


def _load_thelp(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(ThelpHelpReader, path, data)


def _load_tdh(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(TdhHelpReader, path, data)


def _load_scorpion(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(ScorpionReader, path, data)


def _load_fbhf_binary(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(FBHFHelpReader, path, data)


def _load_m602(path: Path, data: bytes) -> HelpDocument:
    return _build_reader_document(M602HelpReader, path, data)


def _load_text602(path: Path, data: bytes) -> HelpDocument:
    return Text602Reader(source_name=path.name, source_path=path).read_bytes(data)


FORMAT_HANDLERS: tuple[FormatHandler, ...] = (
    FormatHandler(
        name="fbhf-source",
        source_kind="source",
        matches=lambda path, data: path.suffix.lower() in {".txt", ".hlx"} and is_fbhf_source(data),
        load=_load_fbhf_source,
    ),
    FormatHandler(
        name="hlx",
        source_kind="source",
        matches=lambda path, data: path.suffix.lower() == ".hl6",
        load=_load_hlx,
    ),
    FormatHandler(
        name="hlx",
        source_kind="compiled",
        matches=lambda path, data: path.suffix.lower() == ".hlx" and not is_hlx_source(data) and is_hlx_binary(data),
        load=_load_hlx_binary,
    ),
    FormatHandler(
        name="hlx",
        source_kind="source",
        matches=lambda path, data: path.suffix.lower() == ".hlx" and is_hlx_source(data),
        load=_load_hlx,
    ),
    FormatHandler(
        name="norton-guide",
        source_kind="compiled",
        matches=lambda path, data: path.suffix.lower() == ".ng" or is_ng_binary(data),
        load=_load_ng,
    ),
    FormatHandler(
        name="bw03",
        source_kind="compiled",
        matches=lambda _path, data: is_bw03_binary(data),
        load=_load_bw03,
    ),
    FormatHandler(
        name="quickhelp",
        source_kind="compiled",
        matches=lambda _path, data: is_quickhelp_binary(data),
        load=_load_quickhelp,
    ),
    FormatHandler(
        name="game-cheater",
        source_kind="compiled",
        matches=is_game_cheater_database,
        load=_load_game_cheater,
    ),
    FormatHandler(
        name="scorpion-legacy",
        source_kind="compiled",
        matches=lambda path, data: detect_scorpion_reader_family(path, data) == "legacy",
        load=_load_scorpion,
    ),
    FormatHandler(
        name="scorpion-dat",
        source_kind="compiled",
        matches=lambda path, data: detect_scorpion_reader_family(path, data) == "dat",
        load=_load_scorpion,
    ),
    FormatHandler(
        name="tdh",
        source_kind="compiled",
        matches=lambda _path, data: is_tdh_binary(data),
        load=_load_tdh,
    ),
    FormatHandler(
        name="tfh",
        source_kind="compiled",
        matches=lambda _path, data: is_tfh_binary(data),
        load=_load_tdh,
    ),
    FormatHandler(
        name="thelp",
        source_kind="compiled",
        matches=lambda _path, data: is_thelp_binary(data),
        load=_load_thelp,
    ),
    FormatHandler(
        name="fbhf",
        source_kind="compiled",
        matches=lambda _path, data: is_fbhf_binary(data),
        load=_load_fbhf_binary,
    ),
    FormatHandler(
        name="m602",
        source_kind="compiled",
        matches=lambda _path, data: is_m602_binary(data),
        load=_load_m602,
    ),
    FormatHandler(
        name="text602",
        source_kind="compiled",
        matches=lambda _path, data: is_text602_binary(data),
        load=_load_text602,
    ),
)


def detect_format_handler(path: str | Path, data: bytes | None = None) -> FormatHandler | None:
    """Return the first registered format handler that matches this file."""
    source_path = Path(path)
    payload = data if data is not None else source_path.read_bytes()
    for handler in FORMAT_HANDLERS:
        if handler.matches(source_path, payload):
            return handler
    return None


def load_document(path: str | Path) -> HelpDocument:
    """Load one supported help file into the shared document model."""
    source_path = Path(path)
    data = source_path.read_bytes()
    handler = detect_format_handler(source_path, data)
    if handler is None:
        raise ValueError(f"Unsupported help format for {source_path}")
    return handler.load(source_path, data)


def load_binary_document(path: str | Path) -> HelpDocument:
    """Backward-compatible alias for ``load_document``."""
    return load_document(path)


def autodetect_display_encoding(
    document: HelpDocument,
    source_hint: str = "",
) -> str:
    """Pick the most plausible display encoding from document content."""
    source_encoding = document.metadata.get("text_encoding")
    if isinstance(source_encoding, str) and source_encoding:
        # Many DOS readers use cp437 as a safe default. For Czech/Slovak files
        # we still want payload-based detection so CP852/Kamenický can win.
        if source_encoding == "cp437" and is_czech_encoding_hint(source_hint):
            return guess_display_encoding(iter_encoding_chunks(document), hint=source_hint)
        return source_encoding
    return guess_display_encoding(iter_encoding_chunks(document), hint=source_hint)


def select_display_encoding(
    document: HelpDocument,
    encoding: str = "auto",
    source_hint: str = "",
    source_path: str | Path | None = None,
    help_database=None,
    database_entry=None,
) -> str:
    """Resolve the final display encoding.

    Precedence:
    1. explicit parameter
    2. canonical help database
    3. payload autodetection / reader hint
    """
    if encoding != "auto":
        return encoding
    entry = database_entry
    if entry is None and source_path is not None:
        entry = lookup_help_database_entry(source_path, help_database)
    if entry is not None and isinstance(entry.text_encoding, str) and entry.text_encoding.strip():
        return entry.text_encoding.strip()
    effective_hint = source_hint or (str(source_path) if source_path is not None else "")
    return autodetect_display_encoding(document, source_hint=effective_hint)


def fix_metadata_encoding(document: HelpDocument, encoding: str) -> None:
    """Re-decode latin-1 metadata strings with the correct display encoding.

    Binary readers store ``description`` (and others) via
    ``bytes.decode("latin-1")`` which is a 1:1 byte mapping.  When the
    actual content uses CP852 or Kamenický, the stored string contains
    raw high-byte chars (U+0080..U+00FF).  This function converts them
    to proper Unicode using the detected *encoding*.
    """
    document.metadata["text_encoding"] = encoding
    if document.format_name == "borland":
        from .readers.thelp import ThelpHelpReader

        ThelpHelpReader.refresh_rendered_uhf_content(document, encoding=encoding)
    if document.metadata.get("metadata_already_decoded"):
        return
    if encoding in ("utf-8", "latin-1", "latin1"):
        return
    for key in ("title", "display_name", "description"):
        value = document.metadata.get(key)
        if not value or not isinstance(value, str):
            continue
        # Pure ASCII — nothing to re-decode.
        if all(ord(c) < 128 for c in value):
            continue
        try:
            raw = value.encode("latin-1")
            document.metadata[key] = decode_bytes(raw, encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass


def export_file(
    input_path: str | Path,
    output_dir: str | Path,
    encoding: str = "auto",
    dump_json: bool = False,
) -> ExportResult:
    """Export one supported help file to a directory containing HTML pages."""
    source_path = Path(input_path)
    print(f"[converter] Spracovávam: {source_path.name}")
    try:
        document = load_document(source_path)
        chosen_encoding = select_display_encoding(
            document,
            encoding=encoding,
            source_hint=str(source_path),
            source_path=source_path,
        )
        fix_metadata_encoding(document, chosen_encoding)
        target_dir = Path(output_dir)
        HelpHtmlRenderer(document, display_encoding=chosen_encoding).write_site(target_dir)
        json_path = None
        if dump_json:
            json_path = document.write_json(target_dir / "document.json", text_encoding=chosen_encoding)
        print(f"[converter] OK: {source_path} → {target_dir} ({getattr(document, 'format_name', '?')})")
        return ExportResult(
            input_path=source_path,
            output_dir=target_dir,
            format_name=document.format_name,
            encoding=chosen_encoding,
            html_count=len(document.topics) + 1,
            json_path=json_path,
        )
    except Exception as e:
        print(f"[converter] CHYBA: {source_path.name} — {e}")
        return ExportResult(
            input_path=source_path,
            output_dir=Path(output_dir),
            format_name="ERROR",
            encoding="?",
            html_count=0,
            json_path=None,
        )


def export_tree(
    input_root: str | Path,
    output_root: str | Path,
    encoding: str = "auto",
    clean: bool = False,
    dump_json: bool = False,
) -> list[ExportResult]:
    """Export every supported help file found under ``input_root``."""
    source_root = Path(input_root)
    target_root = Path(output_root)

    if clean and target_root.exists():
        _clean_dir(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    results: list[ExportResult] = []
    for path in iter_help_files(source_root):
        relative_path = path.relative_to(source_root)
        result = export_file(
            path,
            target_root / relative_path.with_suffix(""),
            encoding=encoding,
            dump_json=dump_json,
        )
        results.append(result)
    return results


def iter_help_files(root: str | Path) -> list[Path]:
    """Return supported help files in a stable traversal order."""
    source_root = Path(root)
    all_paths = [path for path in sorted(source_root.rglob("*")) if path.is_file()]
    detected: list[tuple[Path, FormatHandler]] = []
    compiled_stems: set[Path] = set()

    for path in all_paths:
        data = path.read_bytes()
        handler = detect_format_handler(path, data)
        if handler is None:
            continue
        detected.append((path, handler))
        if handler.source_kind == "compiled":
            compiled_stems.add(path.with_suffix(""))

    paths: list[Path] = []
    for path, handler in detected:
        if handler.source_kind == "source" and path.with_suffix("") in compiled_stems:
            continue
        paths.append(path)

    return paths


def iter_encoding_chunks(document: HelpDocument, limit: int = 512) -> list[bytes]:
    """Collect representative text chunks for display-encoding detection."""
    chunks: list[bytes] = []

    def append(chunk: bytes) -> bool:
        normalized = chunk.replace(b"\x02", b"").strip()
        if not normalized:
            return False
        # Pure ASCII lines do not help to distinguish DOS encodings.
        if not any(value >= 0x80 for value in normalized):
            return False
        # Keep only chunks that look like real text, not box drawing only.
        if not any(
            48 <= value <= 57 or 65 <= value <= 90 or 97 <= value <= 122
            for value in normalized
        ):
            return False
        chunks.append(normalized)
        return len(chunks) >= limit

    for entry in document.index_entries:
        if append(entry.label):
            return chunks

    for topic in document.topics:
        for term in topic.index_terms:
            if append(term):
                return chunks
        for raw_line in topic.raw_lines:
            if append(raw_line):
                return chunks

    return chunks
