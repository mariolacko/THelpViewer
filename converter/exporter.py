"""Helpers for loading help files and exporting them to HTML trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .base import HelpDocument
from .readers.hlx import HlxHelpReader, is_hlx_source
from .readers.m602 import M602HelpReader, is_m602_binary
from .readers.thelp import ThelpHelpReader, is_thelp_binary
from .codepages import decode_bytes, guess_display_encoding
from .readers.fbhf import FBHFHelpReader, FBHFSourceReader, is_fbhf_binary, is_fbhf_source
from .writers.html import HelpHtmlRenderer


HELP_FILE_SUFFIXES = {".hlp", ".tph", ".tch"}
HLX_FILE_SUFFIXES = {".hlx"}
HL6_FILE_SUFFIXES = {".hl6"}
FBHF_SOURCE_SUFFIXES = {".txt"}


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


def load_document(path: str | Path) -> HelpDocument:
    """Load one supported help file into the shared document model."""
    source_path = Path(path)
    data = source_path.read_bytes()
    suffix = source_path.suffix.lower()

    if suffix in FBHF_SOURCE_SUFFIXES and is_fbhf_source(data):
        return FBHFSourceReader(source_name=source_path.name, source_path=source_path).read_bytes(data)

    if suffix in HL6_FILE_SUFFIXES:
        return HlxHelpReader(source_name=source_path.name, source_path=source_path).read_bytes(data)

    if suffix in HLX_FILE_SUFFIXES:
        if is_fbhf_source(data):
            return FBHFSourceReader(source_name=source_path.name, source_path=source_path).read_bytes(data)
        return HlxHelpReader(source_name=source_path.name, source_path=source_path).read_bytes(data)

    if suffix in HELP_FILE_SUFFIXES or is_thelp_binary(data):
        return ThelpHelpReader(source_name=source_path.name).read_bytes(data)
    if is_fbhf_binary(data):
        return FBHFHelpReader(source_name=source_path.name).read_bytes(data)
    if is_m602_binary(data):
        return M602HelpReader(source_name=source_path.name).read_bytes(data)
    raise ValueError(f"Unsupported help format for {source_path}")


def load_binary_document(path: str | Path) -> HelpDocument:
    """Backward-compatible alias for ``load_document``."""
    return load_document(path)


def select_display_encoding(
    document: HelpDocument,
    encoding: str = "auto",
    source_hint: str = "",
) -> str:
    """Resolve ``auto`` to a concrete display encoding for HTML export."""
    if encoding != "auto":
        return encoding
    source_encoding = document.metadata.get("text_encoding")
    if isinstance(source_encoding, str) and source_encoding:
        return source_encoding
    return guess_display_encoding(iter_encoding_chunks(document), hint=source_hint)


def fix_metadata_encoding(document: HelpDocument, encoding: str) -> None:
    """Re-decode latin-1 metadata strings with the correct display encoding.

    Binary readers store ``description`` (and others) via
    ``bytes.decode("latin-1")`` which is a 1:1 byte mapping.  When the
    actual content uses CP852 or Kamenický, the stored string contains
    raw high-byte chars (U+0080..U+00FF).  This function converts them
    to proper Unicode using the detected *encoding*.
    """
    if encoding in ("utf-8", "latin-1", "latin1"):
        return
    for key in ("description",):
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
        chosen_encoding = select_display_encoding(document, encoding=encoding, source_hint=str(source_path))
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
    paths: list[Path] = []
    compiled_stems: set[Path] = set()

    for path in all_paths:
        suffix = path.suffix.lower()
        if suffix in HELP_FILE_SUFFIXES:
            data = path.read_bytes()
            if is_thelp_binary(data) or is_fbhf_binary(data) or is_m602_binary(data):
                paths.append(path)
                compiled_stems.add(path.with_suffix(""))

    for path in all_paths:
        if path.suffix.lower() not in HLX_FILE_SUFFIXES | HL6_FILE_SUFFIXES | FBHF_SOURCE_SUFFIXES or path.with_suffix("") in compiled_stems:
            continue
        data = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix in FBHF_SOURCE_SUFFIXES and is_fbhf_source(data):
            paths.append(path)
            continue
        if suffix in HL6_FILE_SUFFIXES and is_hlx_source(data):
            paths.append(path)
            continue
        if suffix in HLX_FILE_SUFFIXES and (is_fbhf_source(data) or is_hlx_source(data)):
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
