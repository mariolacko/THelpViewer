"""Universal recursive extractor built around ``unar`` / ``lsar``."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from .collector import collect_help_files, copy_help_files, is_help_file_path
from .http import report_progress


MAX_EXTRACTION_DEPTH = 6


@dataclass(frozen=True, slots=True)
class ExtractorTools:
    """Resolved external tools used by the downloader extraction pipeline."""

    unar: str | None
    lsar: str | None
    sevenzip: str | None

    @property
    def available(self) -> bool:
        return bool((self.unar and self.lsar) or self.sevenzip)


@dataclass(frozen=True, slots=True)
class ArchiveProbe:
    """Basic format information reported by ``lsar``."""

    format_name: str
    entry_count: int


SZDD_SIGNATURE = b"SZDD\x88\xF0\x27\x33"
SZ_SIGNATURE = b"SZ \x88\xF0\x27\x33"
QBASIC_SZ_SIGNATURE = SZ_SIGNATURE + b"\xD1"
KWAJ_SIGNATURE = b"KWAJ\x88\xF0\x27\xD1"
MAX_EXPANDED_PAYLOAD = 64 * 1024 * 1024
ZIP_LOCAL_FILE_HEADER = b"PK\x03\x04"
BORLAND_SPLIT_PART_RE = re.compile(r"^(?P<stem>.+)\.C(?P<series>[A-Z])(?P<part>\d+)$", re.I)


def find_unar() -> str | None:
    """Return the ``unar`` binary on PATH when available."""
    return shutil.which("unar")


def find_lsar() -> str | None:
    """Return the companion ``lsar`` binary on PATH when available."""
    return shutil.which("lsar")


def find_sevenzip() -> str | None:
    """Return a working 7-Zip compatible binary when available."""
    return shutil.which("7zz") or shutil.which("7z")


def require_extractor_tools(dry_run: bool = False) -> ExtractorTools:
    """Resolve required extraction tools or exit with a clear install hint."""
    tools = ExtractorTools(
        unar=find_unar(),
        lsar=find_lsar(),
        sevenzip=find_sevenzip(),
    )
    if tools.available:
        return tools

    msg = (
        "No archive/image extractor found – downloader needs unar/lsar or 7zz.\n"
        "  macOS:  brew install unar\n"
        "  alt:    brew install sevenzip\n"
        "  Linux:  sudo apt install unar\n"
    )
    if dry_run:
        print(f"WARNING: {msg}")
        return tools
    sys.exit(f"ERROR: {msg}")


def probe_extractable(path: Path, tools: ExtractorTools) -> ArchiveProbe | None:
    """Return archive/image format metadata for one file or ``None``."""
    if not path.is_file():
        return None

    if tools.lsar:
        result = subprocess.run(
            [tools.lsar, "-json", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout or "{}")
            except json.JSONDecodeError:
                payload = {}
            format_name = str(payload.get("lsarFormatName") or "").strip()
            contents = payload.get("lsarContents") or []
            if format_name:
                return ArchiveProbe(format_name=format_name, entry_count=len(contents))

    if tools.sevenzip:
        result = subprocess.run(
            [tools.sevenzip, "l", str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            match = re.search(r"^Type = (.+)$", result.stdout or "", flags=re.MULTILINE)
            if match:
                return ArchiveProbe(format_name=match.group(1).strip(), entry_count=0)

    return None


def _extract_with_unar(path: Path, dest: Path, tools: ExtractorTools) -> tuple[bool, str | None]:
    if not tools.unar:
        return False, None
    result = subprocess.run(
        [
            tools.unar,
            "-quiet",
            "-force-overwrite",
            "-no-directory",
            "-no-recursion",
            "-output-directory",
            str(dest),
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, None
    stderr = (result.stderr or result.stdout or "").strip()
    return False, stderr[:300] or None


def _extract_with_7zz(path: Path, dest: Path, tools: ExtractorTools) -> tuple[bool, str | None]:
    if not tools.sevenzip:
        return False, None
    result = subprocess.run(
        [
            tools.sevenzip,
            "x",
            "-y",
            f"-o{dest}",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, None
    stderr = (result.stderr or result.stdout or "").strip()
    return False, stderr[:300] or None


def _extraction_tree_is_safe(dest: Path) -> bool:
    """Reject symlinks and paths resolving outside an extraction directory."""
    root = dest.resolve()
    for item in dest.rglob("*"):
        if item.is_symlink():
            return False
        try:
            item.resolve().relative_to(root)
        except (OSError, ValueError):
            return False
    return True


def _discard_unsafe_extraction(dest: Path) -> None:
    shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)


def _read_head(path: Path, size: int = 16) -> bytes:
    with path.open("rb") as handle:
        return handle.read(size)


def extract_file(path: Path, dest: Path, tools: ExtractorTools) -> bool:
    """Extract one archive/image/container into ``dest`` using ``unar``."""
    report_progress("Extracting", path.name)
    if not tools.available:
        print(f"    [error] Cannot extract {path.name}: no extractor available")
        return False

    if dest.is_symlink():
        print(f"    [extract error] {path.name}: extraction directory is a symbolic link")
        return False
    dest.mkdir(parents=True, exist_ok=True)
    ok, unar_error = _extract_with_unar(path, dest, tools)
    if ok:
        if _extraction_tree_is_safe(dest):
            return True
        _discard_unsafe_extraction(dest)
        print(f"    [extract error] {path.name}: archive contains an unsafe symbolic link")
        return False
    if tools.unar:
        _discard_unsafe_extraction(dest)
    ok, sevenzip_error = _extract_with_7zz(path, dest, tools)
    if ok:
        if _extraction_tree_is_safe(dest):
            return True
        _discard_unsafe_extraction(dest)
        print(f"    [extract error] {path.name}: archive contains an unsafe symbolic link")
        return False
    error = sevenzip_error or unar_error
    _discard_unsafe_extraction(dest)
    if error:
        print(f"    [extract error] {path.name}: {error}")
    return False


def _unique_extract_dir(path: Path) -> Path:
    """Return a stable sibling extraction directory for one file."""
    stem = path.name.replace(".", "_")
    candidate = path.parent / f"{stem}__extracted"
    index = 2
    while candidate.exists():
        candidate = path.parent / f"{stem}__extracted_{index}"
        index += 1
    return candidate


def _borland_split_part(path: Path) -> tuple[str, str, int] | None:
    """Return Borland installer split-archive identity for ``*.CA1``-style parts."""
    match = BORLAND_SPLIT_PART_RE.match(path.name)
    if not match:
        return None
    return (
        match.group("stem"),
        match.group("series").upper(),
        int(match.group("part")),
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


def assemble_borland_split_archives(work_dir: Path) -> list[Path]:
    """Combine Borland installer split archives like ``HELP.CA1`` + ``HELP.CA2``.

    The floppy installer stores split ZIP streams as ``*.CA1``, ``*.CA2`` ...
    and prefixes every part with a four-byte part header.  Extracting ``*.CA1``
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

        try:
            first_data = ordered[0].read_bytes()
        except OSError:
            continue
        if len(first_data) <= 4:
            continue

        first_payload = first_data[4:]
        if not first_payload.startswith(ZIP_LOCAL_FILE_HEADER):
            continue

        out_path = _assembled_split_archive_path(work_dir, ordered[0], first_payload)
        if out_path.exists():
            continue

        combined = bytearray(first_payload)
        try:
            for path in ordered[1:]:
                data = path.read_bytes()
                if len(data) <= 4:
                    raise ValueError("split part is too short")
                combined.extend(data[4:])
        except (OSError, ValueError):
            continue

        if first_payload.startswith(ZIP_LOCAL_FILE_HEADER) and not _zip_has_end_record(combined):
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(bytes(combined))
        print(f"    [assemble] {' + '.join(path.name for path in ordered)} -> {out_path.name}")
        assembled.append(out_path)

    return assembled


def _should_probe(path: Path) -> bool:
    """Skip known final artifacts that should not be treated as containers."""
    if is_help_file_path(path):
        return False
    if _is_borland_split_part(path):
        return False
    return True


def extract_nested(work_dir: Path, tools: ExtractorTools, depth: int = 0) -> None:
    """Recursively unpack nested archives and disk images via ``unar``."""
    if not tools.available or depth >= MAX_EXTRACTION_DEPTH:
        return

    assemble_borland_split_archives(work_dir)

    for path in sorted(work_dir.rglob("*")):
        if not (path.is_file() and _should_probe(path)):
            continue
        probe = probe_extractable(path, tools)
        if probe is None:
            continue
        dest = _unique_extract_dir(path)
        indent = "  " * depth
        print(f"    {indent}[extract] {path.name} ({probe.format_name}, {probe.entry_count} entries)")
        if extract_file(path, dest, tools):
            extract_nested(dest, tools, depth + 1)

    for path in assemble_borland_split_archives(work_dir):
        probe = probe_extractable(path, tools)
        if probe is None:
            continue
        dest = _unique_extract_dir(path)
        indent = "  " * depth
        print(f"    {indent}[extract] {path.name} ({probe.format_name}, {probe.entry_count} entries)")
        if extract_file(path, dest, tools):
            extract_nested(dest, tools, depth + 1)


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
        if marker in "$_" and _read_head(candidate).startswith(QBASIC_SZ_SIGNATURE):
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
    print(f"    [assemble] {' + '.join(part.name for part in ordered)} -> {_single_file_output_path(path).name}")
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
        extracted = [candidate for candidate in out_dir.rglob("*") if candidate.is_file()]
        if len(extracted) != 1:
            return None
        return extracted[0].read_bytes()


def expand_single_file_payloads(work_dir: Path, tools: ExtractorTools) -> None:
    """Expand Microsoft payloads, including files split across floppy images."""
    if work_dir.is_symlink() or not _extraction_tree_is_safe(work_dir):
        raise ValueError("Microsoft payload tree contains an unsafe symbolic link")
    files = sorted(path for path in work_dir.rglob("*") if path.is_file())
    for path in files:
        head = _read_head(path)
        if not _looks_like_single_file_payload(path, head):
            continue
        dest = _single_file_output_path(path)
        if dest.exists():
            continue
        try:
            if head.startswith(KWAJ_SIGNATURE):
                from pylibmspack import KwajFile

                data = KwajFile(str(path)).read(max_size=MAX_EXPANDED_PAYLOAD)
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


def collect_from_archive(
    archive: Path,
    label: str,
    sources_dir: Path,
    tools: ExtractorTools,
    *,
    lang_code: str | None = None,
) -> list[Path]:
    """Extract one downloaded container, recurse, collect help files, copy them."""
    lang_suffix = f" ({lang_code})" if lang_code else ""
    target_dir = sources_dir / f"{label}{lang_suffix}".strip()

    with tempfile.TemporaryDirectory(prefix="dlhelp_") as tmp:
        tmp_path = Path(tmp)
        if not extract_file(archive, tmp_path, tools):
            return []
        extract_nested(tmp_path, tools)
        expand_single_file_payloads(tmp_path, tools)
        report_progress("Collecting HELP files", archive.name)
        files = collect_help_files(tmp_path)
        if not files:
            return []
        return copy_help_files(files, target_dir, sources_dir)


def collect_archive_members(
    archive: Path,
    members: tuple[str, ...],
    label: str,
    sources_dir: Path,
    tools: ExtractorTools,
) -> list[Path]:
    """Collect only configured files from an archive, including disk images."""
    if not members:
        raise ValueError("No archive members configured")

    with tempfile.TemporaryDirectory(prefix="dlmembers_") as tmp:
        work_dir = Path(tmp)
        if not extract_file(archive, work_dir, tools):
            raise ValueError(f"Cannot extract {archive.name}")

        def matches_member(path: Path, needle: str) -> bool:
            if "/" not in needle:
                return fnmatch(path.name.casefold(), needle)
            parts = path.relative_to(work_dir).as_posix().casefold().split("/")
            # Nested archives add enclosing extraction directories. Match
            # configured member paths at component boundaries, never substrings.
            return any(fnmatch("/".join(parts[index:]), needle) for index in range(len(parts)))

        def find_members() -> tuple[list[Path], list[str]]:
            files = sorted(path for path in work_dir.rglob("*") if path.is_file())
            selected: list[Path] = []
            missing: list[str] = []
            for pattern in members:
                needle = pattern.casefold().replace("\\", "/")
                matches = [
                    path for path in files
                    if matches_member(path, needle)
                ]
                if len(matches) != 1:
                    missing.append(pattern if not matches else f"{pattern} (ambiguous)")
                elif matches[0] not in selected:
                    selected.append(matches[0])
            return selected, missing

        selected, missing = find_members()
        if missing:
            extract_nested(work_dir, tools)
            expand_single_file_payloads(work_dir, tools)
            selected, missing = find_members()
        if missing:
            raise ValueError(f"Missing archive members: {', '.join(missing)}")
        report_progress("Collecting HELP files", archive.name)
        return copy_help_files(selected, sources_dir / label, sources_dir)
