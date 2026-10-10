"""Helpers for loading help files and exporting them to HTML trees."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib
from pathlib import Path
import shutil
from typing import Callable

from .base import HelpDocument
from .codepages import decode_bytes, guess_display_encoding, is_czech_encoding_hint
from thelpviewer.help_database import ConverterSpec, load_help_manifest, lookup_help_database_entry
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


@lru_cache(maxsize=None)
def _resolve_dotted_path(dotted: str):
    module_name, separator, attr_name = dotted.partition(":")
    if not separator:
        module_name, attr_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def _call_manifest_target(dotted: str, args: str, path: Path, data: bytes):
    target = _resolve_dotted_path(dotted)
    if args == "path_data":
        return target(path, data)
    if args == "path":
        return target(path)
    return target(data)


def _converter_spec_matches(spec: ConverterSpec, path: Path, data: bytes) -> bool:
    extension_ok = not spec.extensions or path.suffix.lower() in spec.extensions

    has_predicate = bool(spec.matcher or spec.detector)
    predicate_ok = True
    if spec.matcher:
        predicate_ok = bool(_call_manifest_target(spec.matcher, spec.matcher_args, path, data))
    if predicate_ok and spec.detector:
        detected = _call_manifest_target(spec.detector, spec.detector_args, path, data)
        predicate_ok = detected == spec.detector_equals if spec.detector_equals else bool(detected)
    if predicate_ok and spec.reject_matcher:
        if _call_manifest_target(spec.reject_matcher, spec.reject_matcher_args, path, data):
            predicate_ok = False

    if spec.match_mode == "any":
        return (bool(spec.extensions) and extension_ok) or (has_predicate and predicate_ok)
    return extension_ok and predicate_ok


def _load_converter_spec_document(spec: ConverterSpec, path: Path, data: bytes) -> HelpDocument:
    if spec.loader:
        return _call_manifest_target(spec.loader, "path_data", path, data)

    reader_cls = _resolve_dotted_path(spec.reader)
    match spec.reader_init:
        case "path":
            reader = reader_cls(path)
        case "none":
            reader = reader_cls()
        case _:
            reader = reader_cls(source_name=path.name, source_path=path)
    return reader.read_bytes(data)


def _build_format_handlers() -> tuple[FormatHandler, ...]:
    handlers: list[FormatHandler] = []
    for spec in load_help_manifest().converters:
        handlers.append(
            FormatHandler(
                name=spec.name,
                source_kind=spec.source_kind,
                matches=lambda path, data, converter_spec=spec: _converter_spec_matches(converter_spec, path, data),
                load=lambda path, data, converter_spec=spec: _load_converter_spec_document(converter_spec, path, data),
            )
        )
    return tuple(handlers)


FORMAT_HANDLERS: tuple[FormatHandler, ...] = _build_format_handlers()


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
