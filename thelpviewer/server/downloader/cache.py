"""Atomic raw-download caching and idle-only cleanup shared by providers."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from urllib.parse import unquote

from ..processing import UnsafeContentError, report_progress
from ..file_storage import file_digest, locked_path
from ..json_storage import write_json


def download_filename(name: str) -> str:
    """Keep a readable, decoded archive name within its download directory."""
    return re.sub(r"[^\w\-. ]", "_", unquote(name)).strip(" .") or "archive"


def cache_metadata_path(destination: Path) -> Path:
    return destination.with_name(destination.name + ".source.json")


def write_cache_identity(destination: Path, identity: str, *, digest: str | None = None) -> None:
    write_json(cache_metadata_path(destination), {"key": identity, "sha256": digest or file_digest(destination)})


def cached_identity_data(root: Path, identity: str, limit: int) -> bytes | None:
    """Reuse identical sources across readable package paths without a network request.

    Atomic publication and the checksum validate the snapshot even if a
    same-name slot changes source concurrently. Do not nest another path lock
    while a caller is already downloading into its own cache slot.
    """
    for metadata in root.glob("*/*.source.json"):
        if any(path.is_symlink() for path in (metadata, *metadata.parents)):
            raise UnsafeContentError("Download cache metadata must not contain symbolic links")
        try:
            if not metadata.is_file() or metadata.stat().st_size > 16384:
                continue
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            if not isinstance(saved, dict) or saved.get("key") != identity:
                continue
            payload = metadata.with_name(metadata.name[:-len(".source.json")])
            if payload.is_symlink():
                raise UnsafeContentError("Download cache must not contain symbolic links")
            if not payload.is_file() or payload.stat().st_size > limit:
                continue
            with payload.open("rb") as stream:
                data = stream.read(limit + 1)
            if len(data) <= limit and hashlib.sha256(data).hexdigest() == saved.get("sha256"):
                return data
        except (OSError, ValueError) as error:
            if isinstance(error, UnsafeContentError):
                raise
    return None


def download_cached(destination: Path, limit: int, fetch, *, process=None, on_cached=None, identity=None):
    """Fetch to staging, validate/process, then publish; never replace a failed cache.

    Fetch and process receive a Path, so streamed HELP/ISO transfers do not need
    to be loaded into RAM. A processor is also run when reusing an existing file.
    The caller owns format-specific validation; without a processor return the
    published destination, not a temporary path.
    """
    with locked_path(destination):
        return _download_cached(destination, limit, fetch, process=process, on_cached=on_cached, identity=identity)


def _download_cached(destination, limit, fetch, *, process, on_cached, identity):
    def check(path):
        if path.is_symlink() or not path.is_file():
            raise UnsafeContentError("Download cache entry must be a regular file, not a symbolic link")
        if path.stat().st_size > limit:
            raise ValueError("Cached download exceeds its size limit")

    if any(path.is_symlink() for path in (destination, *destination.parents)):
        raise UnsafeContentError("Download cache must not contain symbolic links")
    metadata = cache_metadata_path(destination)
    if identity is not None and (metadata.is_symlink() or (metadata.exists() and not metadata.is_file())):
        raise UnsafeContentError("Download cache metadata must be a regular file")
    def matches_identity():
        if identity is None:
            return True
        try:
            if metadata.stat().st_size > 16384:
                return False
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            return isinstance(saved, dict) and saved.get("key") == identity and saved.get("sha256") == file_digest(destination)
        except (OSError, ValueError):
            return False

    if destination.exists():
        check(destination)
        try:
            # A cloud placeholder can have a size and pass is_file(), but fail
            # on its first read inside Docker. Do not send it to an extractor.
            with destination.open("rb") as stream:
                stream.read(1)
        except OSError:
            report_progress("Cached download unreadable; fetching again", destination.name)
        else:
            if matches_identity():
                if on_cached:
                    on_cached()
                result = process(destination) if process else destination
                # Retention measures successful reuse, never filesystem atime
                # (which can be disabled, delayed or changed by antivirus scans).
                os.utime(destination, None)
                if identity is not None:
                    os.utime(metadata, None)
                return result
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".download-", dir=destination.parent) as directory:
        staged = Path(directory) / destination.name
        fetch(staged)
        check(staged)
        result = process(staged) if process else destination
        digest = file_digest(staged) if identity is not None else None
        os.replace(staged, destination)
        if identity is not None:
            # The content hash makes a crash between these two atomic writes a
            # cache miss, never a different source's payload with stale identity.
            write_cache_identity(destination, identity, digest=digest)
        os.utime(destination, None)
        return result


def clear_download_cache(downloads_dir: Path, *, protected_paths: tuple[Path, ...],
                         older_than: float | None = None, sources_dir: Path | None = None) -> dict:
    """Clear raw downloads and optional manual HELP inputs after one preflight.

    The caller must hold the shared downloader's idle maintenance lock. Never
    follow links, read payloads or clean unrelated files in var/data. A cutoff
    expires both raw downloads and supplied HELP inputs by their last-use mtime.
    """
    def cleanup_root(path):
        path = path.absolute()
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise UnsafeContentError("Download cache must not contain symbolic links")
        path = path.resolve()
        if path in (Path(path.anchor), Path.home().resolve(), Path.cwd().resolve()):
            raise ValueError("Download cache must have its own directory")
        return path
    root = cleanup_root(downloads_dir)
    targets = [root / kind for kind in ("help", "dos", "midi")]
    if sources_dir is not None:
        sources = cleanup_root(sources_dir)
        if sources.is_relative_to(root) or root.is_relative_to(sources):
            raise UnsafeContentError("Download cache and HELP inputs must be separate directories")
        targets.append(sources)
    protected = [path.resolve() for path in protected_paths]
    for target in targets:
        resolved = target.resolve()
        if any(resolved.is_relative_to(path) or path.is_relative_to(resolved) for path in protected):
            raise UnsafeContentError("Download cache overlaps permanent or installed content")
    files, directories = {}, []
    def inspect(path):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            for child in path.iterdir():
                inspect(child)
            directories.append(path)
        elif stat.S_ISREG(info.st_mode):
            files[path] = info
        else:
            raise UnsafeContentError("Download cache contains a link or special file")
    # Validate every scope before deleting the first file. stat() is enough:
    # unreadable/cloud placeholders are precisely one reason to clear cache.
    for target in targets:
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not target.is_dir():
                raise UnsafeContentError("Download cache scopes must be regular directories")
            inspect(target)
    selected = {path for path, info in files.items() if older_than is None or info.st_mtime <= older_than}
    for path in files:
        if path.name.endswith(".source.json"):
            payload = path.with_name(path.name[:-len(".source.json")])
            if payload in files:
                if payload in selected:
                    selected.add(path)
                else:
                    selected.discard(path)
    counts = {"files": len(selected), "bytes": sum(files[path].st_size for path in selected)}
    for path in selected:
        path.unlink()
    for path in directories:
        if path not in targets and not any(path.iterdir()):
            path.rmdir()
    return counts
