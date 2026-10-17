"""Installer split streams and single-file compression, independent of consumers."""

from pathlib import Path
import re
import tempfile

from .core import (DEFAULT_LIMITS, ExtractionError, ExtractorTools, UnsafeArchiveError,
                   _extract_with_unar, member_path, validate_tree, read_head)
from ..processing import report_progress

SZDD_SIGNATURE = b"SZDD\x88\xF0\x27\x33"
SZ_SIGNATURE = b"SZ \x88\xF0\x27\x33"
QBASIC_SZ_SIGNATURE = SZ_SIGNATURE + b"\xD1"
KWAJ_SIGNATURE = b"KWAJ\x88\xF0\x27\xD1"
MAX_EXPANDED_PAYLOAD = 64 * 1024 * 1024
ZIP_LOCAL_FILE_HEADER = b"PK\x03\x04"
BORLAND_SPLIT_PART_RE = re.compile(r"^(?P<stem>.+)\.C(?P<series>[A-Z])(?P<part>\d+|[A-Z])$", re.I)


def _borland_split_part(path: Path) -> tuple[str, str, int] | None:
    """Return Borland installer split-archive identity for ``*.CA1``-style parts."""
    match = BORLAND_SPLIT_PART_RE.match(path.name)
    if not match:
        return None
    part = match.group("part")
    if not part.isdigit():
        # .CAB is also Microsoft's cabinet suffix. A lettered split part needs
        # its matching first volume; a real MSCF cabinet is never a split part.
        first_name = f"{match.group('stem')}.C{match.group('series')}1".casefold()
        if (path.is_file() and read_head(path, 4) == b"MSCF") or not any(
                sibling.name.casefold() == first_name and sibling.is_file() for sibling in path.parent.iterdir()):
            return None
    return (
        match.group("stem"),
        match.group("series").upper(),
        int(part) if part.isdigit() else int(part, 36),
    )


def _is_borland_split_part(path: Path) -> bool:
    return _borland_split_part(path) is not None


def _zip_has_end_record(data: bytes) -> bool:
    """Return True when a ZIP stream has its end-of-central-directory record."""
    return data.rfind(b"PK\x05\x06", max(0, len(data) - 65557)) >= 0


def _assembled_split_archive_path(work_dir: Path, first_part: Path, payload_head: bytes) -> Path:
    """Choose the generated path for a combined split archive."""
    part_info = _borland_split_part(first_part)
    if part_info is None:
        return work_dir / "__assembled_split_archives" / f"{first_part.name}.assembled"

    stem, _series, _part = part_info
    suffix = ".ZIP" if payload_head.startswith(ZIP_LOCAL_FILE_HEADER) else ".assembled"
    return work_dir / "__assembled_split_archives" / f"{stem}{suffix}"


def assemble_borland_split_archives(work_dir: Path, *, limits=DEFAULT_LIMITS) -> list[Path]:
    """Combine Borland installer split archives like ``HELP.CA1`` + ``HELP.CA2``.

    The floppy installer stores split ZIP streams as ``*.CA1``, ``*.CA2`` ...
    and prefixes every part with a four- or five-byte header. Part numbers can
    continue with A, B, ... after 9. Extracting ``*.CA1``
    alone can produce a truncated payload, so generate a synthetic archive first
    and let the normal recursive extractor process that archive instead.
    """
    groups: dict[tuple[str, str], dict[int, list[Path]]] = {}
    for path in sorted(work_dir.rglob("*")):
        if not path.is_file():
            continue
        part_info = _borland_split_part(path)
        if part_info is None:
            continue
        stem, series, part = part_info
        groups.setdefault((stem, series), {}).setdefault(part, []).append(path)

    assembled: list[Path] = []
    for (_stem, _series), parts in sorted(groups.items(), key=lambda item: str(item[0])):
        if 1 not in parts or len(parts) < 2:
            continue

        ordered: list[Path] = []
        part_num = 1
        while part_num in parts:
            candidates = parts[part_num]
            if len(candidates) != 1:
                ordered = []
                break
            ordered.append(candidates[0])
            part_num += 1
        if len(ordered) != len(parts):
            continue
        if sum(path.stat().st_size for path in ordered) > limits.max_bytes:
            raise UnsafeArchiveError("Split archive exceeds its size quota")

        try:
            first_data = ordered[0].read_bytes()
        except OSError:
            continue
        header_size = next((size for size in (4, 5) if first_data[size:].startswith(ZIP_LOCAL_FILE_HEADER)), None)
        if header_size is None:
            continue
        if int.from_bytes(first_data[header_size - 3:header_size], "little") != 0:
            continue
        first_payload = first_data[header_size:]

        out_path = _assembled_split_archive_path(work_dir, ordered[0], first_payload)
        if out_path.exists():
            continue

        combined = bytearray(first_payload)
        try:
            for path in ordered[1:]:
                data = path.read_bytes()
                if len(data) <= header_size:
                    raise ValueError("split part is too short")
                if int.from_bytes(data[header_size - 3:header_size], "little") != len(combined):
                    raise ValueError("split part offset does not follow the previous part")
                combined.extend(data[header_size:])
        except (OSError, ValueError):
            continue

        if first_payload.startswith(ZIP_LOCAL_FILE_HEADER) and not _zip_has_end_record(combined):
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(bytes(combined))
        report_progress("Assembling split archive", path.name, stage="extract")
        assembled.append(out_path)

    return assembled


def _looks_like_single_file_payload(path: Path, head: bytes) -> bool:
    """Return True for known single-file compressed payloads."""
    upper = path.name.upper()
    return (
        head.startswith(SZDD_SIGNATURE)
        or head.startswith(QBASIC_SZ_SIGNATURE)
        or head.startswith(KWAJ_SIGNATURE)
        or upper.endswith(".HL$")
        or upper.endswith(".HL_")
        or upper.endswith("_")
        or upper.endswith("$")
    )


def _single_file_output_path(path: Path) -> Path:
    """Choose a reasonable destination path for one expanded payload."""
    upper = path.name.upper()
    if upper.endswith(".HL$") or upper.endswith(".HL_"):
        return path.with_suffix(".HLP")
    if path.name.endswith("_") or path.name.endswith("$"):
        return path.with_name(path.name[:-1])
    return path.with_name(f"{path.name}.expanded")


class _IncompleteSzPayload(ValueError):
    """The declared output requires more compressed bytes."""


def _decompress_sz_payload(data: bytes) -> bytes:
    """Decompress an SZDD-style single-file payload."""
    if data.startswith(SZDD_SIGNATURE):
        if len(data) < 14:
            raise ValueError("Truncated SZDD header")
        if data[8] != 0x41:
            raise ValueError("Unsupported SZDD compression method")
        out_len = int.from_bytes(data[10:14], "little")
        payload = memoryview(data)[14:]
        pos = 4096 - 16
    elif data.startswith(QBASIC_SZ_SIGNATURE):
        if len(data) < 12:
            raise ValueError("Truncated Microsoft SZ header")
        out_len = int.from_bytes(data[8:12], "little")
        payload = memoryview(data)[12:]
        pos = 4096 - 18
    else:
        raise ValueError("Not an SZDD-style single-file payload")
    if out_len > MAX_EXPANDED_PAYLOAD:
        raise ValueError("Expanded Microsoft payload exceeds 64 MiB")

    window = bytearray(b"\x20" * 4096)
    output = bytearray()
    index = 0

    while len(output) < out_len:
        if index >= len(payload):
            raise _IncompleteSzPayload("Unexpected end of compressed stream")
        control = payload[index]
        index += 1
        bit = 1
        while bit <= 0x80 and len(output) < out_len:
            if control & bit:
                if index >= len(payload):
                    raise _IncompleteSzPayload("Missing literal byte")
                value = payload[index]
                index += 1
                window[pos] = value
                output.append(value)
                pos = (pos + 1) & 0x0FFF
            else:
                if index + 1 >= len(payload):
                    raise _IncompleteSzPayload("Missing match bytes")
                match_pos = payload[index]
                match_len = payload[index + 1]
                index += 2
                match_pos |= (match_len & 0xF0) << 4
                match_len = (match_len & 0x0F) + 3
                for _ in range(match_len):
                    value = window[match_pos]
                    window[pos] = value
                    output.append(value)
                    pos = (pos + 1) & 0x0FFF
                    match_pos = (match_pos + 1) & 0x0FFF
                    if len(output) >= out_len:
                        break
            bit <<= 1

    return bytes(output)


def _expand_sz_file(path: Path, files: list[Path]) -> bytes:
    """Decode SZ, joining numbered media parts only when the first is incomplete.

    Microsoft floppies use NAME.HL$ followed by NAME.HL2, NAME.HL3, ... .
    The first SZ/D1 header includes the complete output length; continuation
    headers are the seven-byte SZ signature and the one-byte part number.
    They interrupt one LZSS stream, not independent compressed files.
    """
    if path.stat().st_size > 2 * MAX_EXPANDED_PAYLOAD:
        raise ValueError("Compressed Microsoft payload exceeds 128 MiB")
    first = path.read_bytes()
    try:
        return _decompress_sz_payload(first)
    except _IncompleteSzPayload:
        if (not first.startswith(QBASIC_SZ_SIGNATURE) or len(path.suffix) != 4
                or path.name[-1] not in "$_"):
            raise

    prefix = path.name[:-1].casefold()
    parts: dict[int, list[Path]] = {1: [path]}
    for candidate in files:
        if candidate == path or candidate.name[:-1].casefold() != prefix:
            continue
        marker = candidate.name[-1]
        if marker in "$_" and read_head(candidate).startswith(QBASIC_SZ_SIGNATURE):
            parts[1].append(candidate)
        elif marker in "23456789":
            parts.setdefault(int(marker), []).append(candidate)
    if any(len(candidates) != 1 for candidates in parts.values()):
        raise ValueError(f"Ambiguous Microsoft SZ parts for {path.name}")
    if len(parts) == 1:
        raise ValueError(f"Missing Microsoft SZ continuation part 2 for {path.name}")

    combined = bytearray(first)
    ordered = [path]
    for number in range(2, max(parts) + 1):
        if number not in parts:
            raise ValueError(f"Missing Microsoft SZ continuation part {number} for {path.name}")
        continuation = parts[number][0]
        if continuation.stat().st_size + len(combined) > 2 * MAX_EXPANDED_PAYLOAD:
            raise ValueError("Compressed Microsoft payload exceeds 128 MiB")
        data = continuation.read_bytes()
        if len(data) <= 8 or data[:8] != SZ_SIGNATURE + bytes([number]):
            raise ValueError(f"Invalid Microsoft SZ continuation header: {continuation.name}")
        combined.extend(data[8:])
        ordered.append(continuation)
    result = _decompress_sz_payload(bytes(combined))
    report_progress("Assembling split archive", path.name, stage="extract")
    return result


def _extract_single_file_payload_with_unar(path: Path, tools: ExtractorTools) -> bytes | None:
    """Try to expand one single-file payload via ``unar`` first."""
    if not tools.unar:
        return None
    with tempfile.TemporaryDirectory(prefix="dlsingle_") as tmp:
        out_dir = Path(tmp)
        ok, _error = _extract_with_unar(path, out_dir, tools)
        if not ok:
            return None
        extracted = validate_tree(out_dir).files
        if len(extracted) != 1:
            return None
        return extracted[0].read_bytes()


def expand_microsoft(data: bytes, name: str, limit=MAX_EXPANDED_PAYLOAD) -> tuple[str, bytes]:
    """Decode one SZDD/KWAJ file, preserving the encoded basename only."""
    from pylibmspack import KwajFile, SzddFile
    from pylibmspack.errors import MspackError

    reader = (KwajFile.from_bytes(data, name=Path(name).name) if data.startswith(KWAJ_SIGNATURE)
              else SzddFile.from_bytes(data, name=Path(name).name) if data.startswith(SZDD_SIGNATURE) else None)
    if reader is None:
        return name, data
    try:
        basename = member_path(reader.suggested_name())
        if "/" in basename:
            raise UnsafeArchiveError("Compressed filename must not contain directories")
        target = str(Path(name).with_name(basename))
        return target, reader.read(max_size=limit)
    except MspackError as error:
        raise ExtractionError(f"Cannot expand {name}: {error}") from error


def expand_single_file_payloads(work_dir: Path, tools: ExtractorTools) -> None:
    """Expand Microsoft payloads, including files split across floppy images."""
    validate_tree(work_dir)
    files = sorted(path for path in work_dir.rglob("*") if path.is_file())
    for path in files:
        head = read_head(path)
        if not _looks_like_single_file_payload(path, head):
            continue
        dest = _single_file_output_path(path)
        if dest.exists():
            continue
        report_progress("Expanding compressed file", path.name, stage="extract")
        try:
            if head.startswith(KWAJ_SIGNATURE):
                _name, data = expand_microsoft(path.read_bytes(), path.name)
            elif head.startswith(SZDD_SIGNATURE) or head.startswith(QBASIC_SZ_SIGNATURE):
                data = _expand_sz_file(path, files)
            else:
                data = _extract_single_file_payload_with_unar(path, tools)
                if data is None:
                    data = _decompress_sz_payload(path.read_bytes())
        except Exception as exc:
            if head.startswith((KWAJ_SIGNATURE, SZDD_SIGNATURE, QBASIC_SZ_SIGNATURE)):
                raise ValueError(f"Cannot expand {path.relative_to(work_dir)}: {exc}") from exc
            continue
        dest.write_bytes(data)
        validate_tree(work_dir)
