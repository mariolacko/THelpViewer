"""Atomic binary publication shared by downloads, conversion and server storage."""

from contextlib import contextmanager
import errno
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import threading
from weakref import WeakValueDictionary

from .processing import UnsafeContentError


_path_locks = WeakValueDictionary()
_path_locks_guard = threading.Lock()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_files(root: Path) -> dict[Path, Path]:
    """Inventory regular storage without following links or special files."""
    if root.is_symlink():
        raise UnsafeContentError(f"Storage refuses symbolic links: {root}")
    if root.is_file():
        return {Path("."): root}
    if root.exists() and not root.is_dir():
        raise UnsafeContentError(f"Storage refuses special files: {root}")
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise UnsafeContentError(f"Storage refuses symbolic links: {path}")
        if path.is_file():
            files[path.relative_to(root)] = path
        elif not path.is_dir():
            raise UnsafeContentError(f"Storage refuses special files: {path}")
    return files


def directory_signature(root: Path) -> dict[Path, str | None]:
    files = {relative: file_digest(path) for relative, path in directory_files(root).items()}
    return files | {path.relative_to(root): None for path in root.rglob("*") if path.is_dir()}


def relocate_directory(source: Path, destination: Path) -> None:
    """Rename an owned tree, or verify a cross-filesystem copy before removal."""
    if any(path.is_symlink() for root in (source, destination) for path in (root, *root.parents)):
        raise UnsafeContentError("Storage relocation refuses symbolic links")
    origin, target = source.resolve(), destination.resolve()
    if (origin in {Path(origin.anchor), Path.home().resolve(), Path.cwd().resolve()}
            or target.is_relative_to(origin) or origin.is_relative_to(target)
            or not source.is_dir()):
        raise UnsafeContentError("Storage relocation needs separate, specific directories")
    files = directory_signature(source)
    if destination.exists():
        if not destination.is_dir() or directory_signature(destination) != files:
            raise ValueError(f"Storage relocation conflict (nothing overwritten): {destination}")
        if directory_signature(source) != files:
            raise ValueError(f"Storage relocation source changed: {source}")
        shutil.rmtree(source)  # The exact verified tree already exists at its destination.
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        source.rename(destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        with tempfile.TemporaryDirectory(prefix=".backup-copy-", dir=destination.parent) as directory:
            staged = Path(directory) / "content"
            shutil.copytree(source, staged)
            if directory_signature(staged) != files or directory_signature(source) != files:
                raise ValueError(f"Storage relocation verification failed: {source}")
            if destination.exists():
                raise ValueError(f"Storage relocation destination appeared: {destination}")
            staged.rename(destination)
            shutil.rmtree(source)


@contextmanager
def locked_path(path: Path):
    """Serialize writers of one path without retaining every historical key."""
    key = str(path.absolute())
    with _path_locks_guard:
        lock = _path_locks.setdefault(key, threading.RLock())
    with lock:
        yield


@contextmanager
def atomic_file(destination: Path):
    if destination.is_symlink() or destination.parent.is_symlink():
        raise UnsafeContentError("File storage must not contain symbolic links")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".write-", delete=False) as stream:
            temporary = Path(stream.name)
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
