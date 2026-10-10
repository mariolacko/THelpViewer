"""Verified, resumable storage migration. Never overwrite conflicting data."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from ..public_docs import is_public_doc_path
from .config import PROJECT_ROOT


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> dict[Path, Path]:
    if root.is_symlink():
        raise ValueError(f"Storage migration refuses symbolic links: {root}")
    if root.is_file():
        return {Path("."): root}
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Storage migration refuses symbolic links: {path}")
        if path.is_file():
            files[path.relative_to(root)] = path
        elif not path.is_dir():
            raise ValueError(f"Storage migration refuses special files: {path}")
    return files


def _atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            output.write(json.dumps(value, indent=2).encode())
            output.flush(); os.fsync(output.fileno())
            temporary = Path(output.name)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@contextmanager
def _migration_lock(path: Path):
    # Startup is one process today, but concurrent startups must not both move data.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if handle.tell() == 0:
                handle.write(b"0"); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def migration_plan(config, project_root: Path = PROJECT_ROOT) -> list[tuple[Path, Path]]:
    data, state = config.persistent_dir, config.state_dir
    plan = []
    if config.helps_dir == data / "helps":
        plan.append((project_root / "helps", config.helps_dir))
    if config.sources_dir == data / "sources":
        plan.append((project_root / "sources", config.sources_dir))
    if data != state:
        plan.extend((state / name, data / name) for name in (
            "accounts.sqlite3", "accounts.sqlite3-wal", "accounts.sqlite3-shm",
            "registration-tokens.key", "statistics.sqlite3", "statistics.sqlite3-wal",
            "statistics.sqlite3-shm", "server-settings.json", "content-settings.json", "development",
        ))
        plan.append((state / "dos" / "users", data / "dos" / "users"))
    plan.extend([
        (state / "dos" / "base" / "c", state / "dos" / "c"),
        (state / "dos" / "base" / "installed.json", state / "dos" / "installed.json"),
        (state / "dos" / "downloads", (config.downloads_dir or state / "downloads") / "dos"),
    ])
    return [(source, target) for source, target in plan if source != target]


def migrate_storage(config, *, project_root: Path = PROJECT_ROOT) -> dict:
    """Copy, verify SHA-256, then archive exact legacy paths; old server must be stopped."""
    data = config.persistent_dir
    if data.is_symlink():
        raise ValueError("Persistent data directory must not be a symbolic link")
    journal_path = data / "storage-migration.json"
    def key(source):
        if source.is_relative_to(config.state_dir):
            return "var/" + source.relative_to(config.state_dir).as_posix()
        return source.relative_to(project_root).as_posix()
    with _migration_lock(data / ".storage-migration.lock"):
        journal = json.loads(journal_path.read_text()) if journal_path.exists() else {
            "version": 1, "backup": "migration-backups/" + uuid.uuid4().hex, "completed": [],
        }
        normalized = False
        if Path(journal["backup"]).is_absolute() and Path(journal["backup"]).is_relative_to(data):
            # Normalize the just-created local migration record before the same disk is bind-mounted.
            journal["backup"] = Path(journal["backup"]).relative_to(data).as_posix()
            journal["completed"] = [key(Path(item)) if Path(item).is_absolute() else item
                                    for item in journal["completed"]]
            normalized = True
        if (journal.get("version") != 1 or not isinstance(journal.get("completed"), list)
                or Path(journal["backup"]).is_absolute() or ".." in Path(journal["backup"]).parts
                or not Path(journal["backup"]).is_relative_to(Path("migration-backups"))):
            raise ValueError("Invalid storage migration journal")
        if normalized:
            _atomic_json(journal_path, journal)
        pending = [(source, target) for source, target in migration_plan(config, project_root)
                   if key(source) not in journal["completed"] and (source.exists() or source.is_symlink())]
        snapshots = {}
        # Preflight every target before changing any source or active destination.
        for source, target in pending:
            if target.is_symlink() or target.parent.is_symlink() or source.parent.is_symlink():
                raise ValueError(f"Storage migration refuses symbolic links: {source} -> {target}")
            files = _files(source)
            if target.exists() and source.is_dir() != target.is_dir():
                raise ValueError(f"Storage migration target type conflicts: {target}")
            if target.exists():
                _files(target)  # Reject symlinked descendants before any collision reads/writes.
            for relative, path in files.items():
                destination = target if relative == Path(".") else target / relative
                if destination.exists() and (not destination.is_file() or _digest(path) != _digest(destination)):
                    raise ValueError(f"Storage migration conflict (nothing overwritten): {destination}")
            snapshots[source] = {relative: _digest(path) for relative, path in files.items()}
        if not pending:
            return journal
        _atomic_json(journal_path, journal)
        for source, target in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".storage-copy-", dir=target.parent))
            try:
                staged = staging / "content"
                if source.is_dir():
                    shutil.copytree(source, staged)
                else:
                    shutil.copy2(source, staged)
                if {relative: _digest(path) for relative, path in _files(staged).items()} != snapshots[source]:
                    raise ValueError(f"Storage copy verification failed: {source}")
                if target.exists():
                    if staged.is_dir():
                        for directory in staged.rglob("*"):
                            if directory.is_dir():
                                (target / directory.relative_to(staged)).mkdir(parents=True, exist_ok=True)
                    # All collisions were checked above. Copy only missing entries, with atomic files.
                    for relative, path in _files(staged).items():
                        destination = target if relative == Path(".") else target / relative
                        if not destination.exists():
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            os.replace(path, destination)
                else:
                    os.replace(staged, target)
                if {relative: _digest(path) for relative, path in _files(source).items()} != snapshots[source]:
                    raise ValueError(f"Source changed during migration; stop the old server: {source}")
                for relative, digest in snapshots[source].items():
                    destination = target if relative == Path(".") else target / relative
                    if _digest(destination) != digest:
                        raise ValueError(f"Published storage verification failed: {destination}")
                backup = data / journal["backup"] / f"{len(journal['completed']):02d}-{source.name}"
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), backup)
                journal["completed"].append(key(source))
                _atomic_json(journal_path, journal)
            finally:
                shutil.rmtree(staging)
        return journal


def publish_docs(source: Path | None, destination: Path) -> None:
    """Publish versioned documentation; preserve edits and extra permanent documents."""
    if source is None or source == destination or not source.is_dir():
        return
    if destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("Published Docs must not be symbolic links")
    destination.mkdir(parents=True, exist_ok=True)
    _files(destination)
    marker = destination / ".managed-docs.json"
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    hashes = dict(previous)
    for relative, path in _files(source).items():
        if not is_public_doc_path(relative.as_posix()):
            continue
        target = destination / relative
        new_hash = _digest(path)
        if target.is_symlink():
            raise ValueError("Published Docs must not be symbolic links")
        if target.exists() and _digest(target) not in {previous.get(relative.as_posix()), new_hash}:
            continue  # Administrator edit / pre-existing document; not managed by the publisher.
        if not target.exists() or _digest(target) != new_hash:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                temporary = Path(output.name)
            try:
                shutil.copy2(path, temporary)
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
        hashes[relative.as_posix()] = new_hash
    _atomic_json(marker, hashes)


def prepare_storage(config) -> None:
    migrate_storage(config)
    if config.docs_dir == config.persistent_dir / "docs":
        publish_docs(config.docs_source_dir, config.docs_dir)
