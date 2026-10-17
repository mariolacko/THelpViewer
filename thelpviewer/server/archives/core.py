"""Archive tools, bounded ZIP access and safe external extraction; no consumers."""

from contextlib import contextmanager
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile

from ..processing import UnsafeContentError, report_progress


class ExtractionError(ValueError):
    """An archive cannot be decoded completely."""


class UnsafeArchiveError(UnsafeContentError):
    """An archive contains unsafe paths, entries or exceeds its resource budget."""


@dataclass(frozen=True, slots=True)
class ExtractionLimits:
    max_files: int = 100000
    max_bytes: int = 2 * 1024 * 1024 * 1024
    max_depth: int = 6
    timeout: float = 120


DEFAULT_LIMITS = ExtractionLimits()
OLE_COMPOUND_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


@dataclass(frozen=True, slots=True)
class ExtractorTools:
    unar: str | None
    lsar: str | None
    sevenzip: str | None

    @property
    def available(self):
        return bool((self.unar and self.lsar) or self.sevenzip)


@dataclass(frozen=True, slots=True)
class ArchiveProbe:
    format_name: str
    entry_count: int


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    files: tuple[Path, ...]
    total_bytes: int


def find_unar():
    return shutil.which("unar")


def find_lsar():
    return shutil.which("lsar")


def find_sevenzip():
    return shutil.which("7zz") or shutil.which("7z")


def read_head(path, size=16):
    with path.open("rb") as stream:
        return stream.read(size)


def require_extractor_tools(dry_run=False):
    tools = ExtractorTools(find_unar(), find_lsar(), find_sevenzip())
    if not tools.available and not dry_run:
        raise ExtractionError("Archive extraction requires unar/lsar or 7zz; rebuild the Docker image")
    return tools


def member_path(name):
    normalized = name.replace("\\", "/").rstrip("/")
    path = PurePosixPath(normalized)
    if (not normalized or path.is_absolute() or re.match(r"^[A-Za-z]:", normalized)
            or any(part in ("", "..") for part in normalized.split("/"))
            or any(ord(char) < 32 or ord(char) == 127 for char in normalized)):
        raise UnsafeArchiveError(f"Unsafe archive member path: {name!r}")
    return path.as_posix()


def validate_tree(root, limits=DEFAULT_LIMITS):
    if root.is_symlink():
        raise UnsafeArchiveError("Extraction directory must not be a symbolic link")
    resolved = root.resolve()
    files, total = [], 0
    for path in root.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(resolved):
            raise UnsafeArchiveError("Archive contains an unsafe symbolic link")
        if path.is_dir():
            continue
        if not path.is_file():
            raise UnsafeArchiveError("Archive contains a special file")
        files.append(path)
        total += path.stat().st_size
        if len(files) > limits.max_files or total > limits.max_bytes:
            raise UnsafeArchiveError("Archive extraction exceeds its file/size quota")
    return ExtractionResult(tuple(sorted(files)), total)


@contextmanager
def open_zip(source, limits=DEFAULT_LIMITS, *, probe=False):
    """Check all metadata before reading any ZIP member, including unselected ones."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(source) if isinstance(source, bytes) else source)
    except (zipfile.BadZipFile, OSError) as error:
        if probe and isinstance(error, zipfile.BadZipFile):
            # An embedded ZIP end record can fool is_zipfile() on a FAT disk
            # image. Only a readable central directory identifies a ZIP here.
            yield None
            return
        raise ExtractionError(f"Cannot open ZIP: {error}") from error
    with archive:
        entries = archive.infolist()
        if len(entries) > limits.max_files or sum(entry.file_size for entry in entries) > limits.max_bytes:
            raise UnsafeArchiveError("ZIP exceeds its entry/expanded-size quota")
        names, directories = set(), set()
        for entry in entries:
            name = member_path(entry.filename)
            if name == "." and not entry.is_dir():
                raise UnsafeArchiveError("ZIP file member must have a basename")
            parents = {parent.as_posix() for parent in PurePosixPath(name).parents if parent.as_posix() != "."}
            if parents & names or (entry.is_dir() and name in names) or (not entry.is_dir() and name in directories):
                raise UnsafeArchiveError("ZIP has conflicting file/directory paths")
            directories.update(parents)
            if entry.is_dir():
                directories.add(name)
            if entry.create_system == 3 and stat.S_ISLNK(entry.external_attr >> 16):
                raise UnsafeArchiveError("ZIP contains a symbolic link")
            if not entry.is_dir():
                if name in names:
                    raise UnsafeArchiveError("ZIP contains duplicate member paths")
                names.add(name)
            if entry.flag_bits & 1:
                raise ExtractionError("Encrypted ZIP members are not supported")
        yield archive


def read_zip_member(archive, entry, limit):
    if entry.file_size > limit:
        raise ExtractionError(f"ZIP member exceeds its size limit: {entry.filename}")
    try:
        with archive.open(entry) as stream:
            data = stream.read(limit + 1)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        raise ExtractionError(f"Cannot decode {entry.filename}: {error}") from error
    if len(data) > limit or len(data) != entry.file_size:
        raise ExtractionError(f"Incomplete/oversized ZIP member: {entry.filename}")
    return data


def probe_extractable(path, tools, limits=DEFAULT_LIMITS):
    if not path.is_file():
        return None
    # OLE streams are document internals, not filesystem archive members.
    # Inspect the signature, not a suffix: documents can use arbitrary names.
    if read_head(path, 8) == OLE_COMPOUND_SIGNATURE:
        return None
    with open_zip(path, limits, probe=True) as archive:
        if archive is not None:
            return ArchiveProbe("Zip", len(archive.infolist()))
    commands = ([tools.lsar, "-json", str(path)] if tools.lsar else None,
                [tools.sevenzip, "l", "-slt", str(path)] if tools.sevenzip else None)
    for index, command in enumerate(commands):
        if command is None:
            continue
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=limits.timeout)
        except subprocess.TimeoutExpired as error:
            raise ExtractionError(f"Archive inspection timed out: {path.name}") from error
        if result.returncode:
            continue
        if index == 0:
            try:
                payload = json.loads(result.stdout or "{}")
            except json.JSONDecodeError:
                continue
            name = str(payload.get("lsarFormatName") or "").strip()
            entries = payload.get("lsarContents") or []
            for entry in entries:
                if entry.get("XADFileName"):
                    member_path(entry["XADFileName"])
                if entry.get("XADIsLink") or entry.get("XADIsSymbolicLink"):
                    raise UnsafeArchiveError("Archive contains a symbolic link")
            if len(entries) > limits.max_files or sum(int(entry.get("XADFileSize") or 0) for entry in entries) > limits.max_bytes:
                raise UnsafeArchiveError("Archive metadata exceeds its extraction quota")
            if name:
                return ArchiveProbe(name, len(entries))
        else:
            match = re.search(r"^Type = (.+)$", result.stdout or "", re.M)
            if match:
                # 7-Zip can list program sections too. They are not nested
                # archives (SFX containers still report their archive type).
                if match.group(1).strip().casefold() in {"pe", "elf", "macho", "te"}:
                    return None
                listing = (result.stdout or "").split("----------", 1)
                if len(listing) == 2:
                    if re.search(r"^(?:Symbolic Link|Hard Link) = .+", listing[1], re.M):
                        raise UnsafeArchiveError("Archive contains a link")
                    names = re.findall(r"^Path = (.+)$", listing[1], re.M)
                    for name in names:
                        member_path(name)
                    sizes = re.findall(r"^Size = (\d+)$", listing[1], re.M)
                    if len(names) > limits.max_files or sum(map(int, sizes)) > limits.max_bytes:
                        raise UnsafeArchiveError("Archive metadata exceeds its extraction quota")
                return ArchiveProbe(match.group(1).strip(), 0)
    return None


def _run_tool(command, destination, limits, *, progress=None):
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + limits.timeout
        offset = 0
        def read_progress():
            nonlocal offset
            # pread does not move the descriptor offset shared with the child.
            # Read bounded chunks, retaining diagnostics in the spool file.
            data = os.pread(output.fileno(), 65536, offset)
            offset += len(data)
            if data and progress:
                progress(data)
            return bool(data)
        try:
            while process.poll() is None:
                read_progress()
                validate_tree(destination, limits)
                if time.monotonic() >= deadline:
                    raise ExtractionError("Archive extraction timed out")
                time.sleep(.05)
            while read_progress():
                pass
            # A long successful-file listing must not hide the later failure.
            output.seek(max(0, output.seek(0, os.SEEK_END) - 4096))
            message = output.read().decode("utf-8", errors="replace")
            message = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", message)
            message = "".join(char for char in message if char.isprintable() or char in "\n\r\t")
            lines = [line.strip() for line in message.splitlines() if line.strip()]
            failures = [line for line in lines if re.search(r"\b(?:error|failed|unsupported)\b", line, re.I)]
            return process.returncode == 0, "\n".join(failures or lines)[-300:]
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()


def _extract_with_unar(path, dest, tools, limits=DEFAULT_LIMITS, *, entries=0):
    if not tools.unar:
        return False, ""
    if entries:
        report_progress("Extracting", path.name, stage="extract", processed=0, total=entries)
    pending, completed = b"", 0
    def progress(data):
        nonlocal pending, completed
        lines = (pending + data).split(b"\n")
        pending = lines.pop()[-4096:]
        count = sum(line.rstrip(b"\r").endswith(b"... OK.") for line in lines)
        if count and entries:
            completed += count
            report_progress("Extracting", path.name, stage="extract",
                            processed=min(completed, entries), total=entries)
    return _run_tool([tools.unar, "-force-overwrite", "-no-directory", "-no-recursion",
                      "-output-directory", str(dest), str(path)], dest, limits, progress=progress)


def _extract_with_7zz(path, dest, tools, limits=DEFAULT_LIMITS):
    if not tools.sevenzip:
        return False, ""
    report_progress("Extracting", path.name, stage="extract", processed=0, total=100)
    pending, previous = b"", None
    def progress(data):
        nonlocal pending, previous
        text = pending + data
        pending = text[-8:]
        matches = re.findall(rb"(?:^|[\x08\r\n ])(\d{1,3})%", text)
        if matches:
            percent = min(100, int(matches[-1]))
            if percent != previous:
                previous = percent
                report_progress("Extracting", path.name, stage="extract", processed=percent, total=100)
    return _run_tool([tools.sevenzip, "x", "-y", "-bsp1", "-bso0", f"-o{dest}", str(path)],
                     dest, limits, progress=progress)


def extract_file(path, dest, tools=None, *, limits=DEFAULT_LIMITS):
    """Extract into an empty disposable directory or raise with the actual cause."""
    if dest.is_symlink() or (dest.exists() and any(dest.iterdir())):
        raise UnsafeArchiveError("Extraction needs an empty, non-symlink staging directory")
    dest.mkdir(parents=True, exist_ok=True)
    report_progress("Extracting", path.name, stage="extract")
    try:
        if read_head(path, 8) == OLE_COMPOUND_SIGNATURE:
            raise ExtractionError(f"{path.name} is an OLE compound document, not an archive")
        with open_zip(path, limits, probe=True) as archive:
            if archive is not None:
                if all(entry.compress_type in (0, 8, 12, 14) for entry in archive.infolist()):
                    entries = archive.infolist()
                    for index, entry in enumerate(entries):
                        target = dest / member_path(entry.filename)
                        if entry.is_dir():
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(read_zip_member(archive, entry, limits.max_bytes))
                        report_progress("Extracting", path.name, stage="extract",
                                        processed=index + 1, total=len(entries))
                    return validate_tree(dest, limits)
        tools = tools or require_extractor_tools()
        if not tools.available:
            raise ExtractionError("Archive extraction requires unar/lsar or 7zz")
        probe = probe_extractable(path, tools, limits)
        failures = []
        for extractor in (_extract_with_unar, _extract_with_7zz):
            report_progress("Extracting", path.name, stage="extract")
            ok, error = (extractor(path, dest, tools, limits, entries=probe.entry_count if probe else 0)
                         if extractor is _extract_with_unar else extractor(path, dest, tools, limits))
            if ok:
                result = validate_tree(dest, limits)
                report_progress("Extracting", path.name, stage="extract", processed=1, total=1)
                return result
            failures.append(error)
            shutil.rmtree(dest)
            dest.mkdir()
        raise ExtractionError(f"Cannot extract {path.name}: " + "; ".join(filter(None, failures)))
    except BaseException:
        shutil.rmtree(dest)
        dest.mkdir()
        raise
