"""Verified, resumable storage migration. Never overwrite conflicting data."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from ..public_docs import is_public_doc_path
from .config import PROJECT_ROOT
from .json_storage import write_json
from .file_storage import directory_files, directory_signature, file_digest, relocate_directory


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
    sources = config.sources_dir or state / "sources"
    if sources == state / "sources":
        plan.extend((old, sources) for old in (project_root / "sources", data / "sources"))
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
        if source.is_relative_to(data):
            return "data/" + source.relative_to(data).as_posix()
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
            write_json(journal_path, journal)
        pending = [(source, target) for source, target in migration_plan(config, project_root)
                   if key(source) not in journal["completed"] and (source.exists() or source.is_symlink())]
        snapshots = {}
        planned = {}
        # Preflight every target before changing any source or active destination.
        for source, target in pending:
            if any(path.is_symlink() for root in (source, target) for path in (root, *root.parents)):
                raise ValueError(f"Storage migration refuses symbolic links: {source} -> {target}")
            if target.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(target.resolve()):
                raise ValueError(f"Storage migration needs separate source and target: {source} -> {target}")
            signature = directory_signature(source)
            if target.exists() and source.is_dir() != target.is_dir():
                raise ValueError(f"Storage migration target type conflicts: {target}")
            if target.exists():
                directory_files(target)  # Reject linked descendants before collision reads/writes.
            entries = {Path("."): None, **signature} if source.is_dir() else signature
            for relative, digest in entries.items():
                destination = target if relative == Path(".") else target / relative
                if destination in planned and planned[destination] != digest:
                    raise ValueError(f"Storage migration conflict (nothing overwritten): {destination}")
                if destination.exists() and (
                        (not destination.is_dir() if digest is None
                         else not destination.is_file() or digest != file_digest(destination))):
                    raise ValueError(f"Storage migration conflict (nothing overwritten): {destination}")
                planned[destination] = digest
            snapshots[source] = {relative: digest for relative, digest in signature.items() if digest is not None}
        if not pending:
            return journal
        write_json(journal_path, journal)
        for source, target in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".storage-copy-", dir=target.parent))
            try:
                staged = staging / "content"
                if source.is_dir():
                    shutil.copytree(source, staged)
                else:
                    shutil.copy2(source, staged)
                if {relative: file_digest(path) for relative, path in directory_files(staged).items()} != snapshots[source]:
                    raise ValueError(f"Storage copy verification failed: {source}")
                if target.exists():
                    if staged.is_dir():
                        for directory in staged.rglob("*"):
                            if directory.is_dir():
                                (target / directory.relative_to(staged)).mkdir(parents=True, exist_ok=True)
                    # All collisions were checked above. Copy only missing entries, with atomic files.
                    for relative, path in directory_files(staged).items():
                        destination = target if relative == Path(".") else target / relative
                        if not destination.exists():
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            os.replace(path, destination)
                else:
                    os.replace(staged, target)
                if {relative: file_digest(path) for relative, path in directory_files(source).items()} != snapshots[source]:
                    raise ValueError(f"Source changed during migration; stop the old server: {source}")
                for relative, digest in snapshots[source].items():
                    destination = target if relative == Path(".") else target / relative
                    if file_digest(destination) != digest:
                        raise ValueError(f"Published storage verification failed: {destination}")
                backup = data / journal["backup"] / f"{len(journal['completed']):02d}-{source.name}"
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), backup)
                journal["completed"].append(key(source))
                write_json(journal_path, journal)
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
    directory_files(destination)
    marker = destination / ".managed-docs.json"
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    hashes = dict(previous)
    for relative, path in directory_files(source).items():
        if not is_public_doc_path(relative.as_posix()):
            continue
        target = destination / relative
        new_hash = file_digest(path)
        if target.is_symlink():
            raise ValueError("Published Docs must not be symbolic links")
        if target.exists() and file_digest(target) not in {previous.get(relative.as_posix()), new_hash}:
            continue  # Administrator edit / pre-existing document; not managed by the publisher.
        if not target.exists() or file_digest(target) != new_hash:
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
    write_json(marker, hashes)


def migrate_backups(config) -> list[tuple[Path, Path]]:
    """Group existing managed recovery generations; never prune during migration."""
    root = config.state_dir / "backups"
    groups = [root / kind for kind in ("help", "dos", "midi")]
    moved = []
    with _migration_lock(config.persistent_dir / ".storage-migration.lock"):
        for directory in [root, *groups]:
            if any(path.is_symlink() for path in (directory, *directory.parents)):
                raise ValueError("Backup migration refuses symbolic links")
            if directory.exists() and not directory.is_dir():
                raise ValueError(f"Backup storage must be a directory: {directory}")
        plan = []
        old_help = config.helps_dir.parent
        help_pattern = re.compile(re.escape(f".{config.helps_dir.name}-previous-") + r"([0-9a-f]{32})")
        for path in old_help.iterdir() if old_help.is_dir() else ():
            match = help_pattern.fullmatch(path.name)
            if match:
                plan.append((path, root / "help" / f"help-{match[1]}"))
        for path in root.iterdir() if root.is_dir() else ():
            match = re.fullmatch(r"(dos-(?:base|packages)|midi)-[0-9a-f]{32}", path.name)
            if match:
                plan.append((path, root / ("midi" if match[1] == "midi" else "dos") / path.name))
        # Refuse every conflict before moving the first backup. Identical
        # destinations make an interrupted cross-filesystem move repeat-safe.
        for source, target in plan:
            if any(path.is_symlink() for parent in (source, target) for path in (parent, *parent.parents)):
                raise ValueError("Backup migration refuses symbolic links")
            if not source.is_dir():
                raise ValueError(f"Backup migration needs a directory: {source}")
            files = directory_signature(source)
            if target.exists() and (not target.is_dir() or directory_signature(target) != files):
                raise ValueError(f"Backup migration conflict (nothing overwritten): {target}")
        plan.sort(key=lambda pair: (pair[0].stat().st_ctime_ns, pair[0].name))
        for source, target in plan:
            relocate_directory(source, target)
            moved.append((source, target))
        for directory in groups:
            directory.mkdir(parents=True, exist_ok=True)
    return moved


def prepare_storage(config) -> None:
    migrate_storage(config)
    if config.docs_dir == config.persistent_dir / "docs":
        publish_docs(config.docs_source_dir, config.docs_dir)
