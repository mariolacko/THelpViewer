"""Recoverable, exact-directory replacement for local development rebuilds."""

from pathlib import Path
import uuid


def archive_rebuild_directory(directory: Path, backup_root: Path, label: str) -> str:
    if (directory.is_symlink() or directory.parent.is_symlink()
            or backup_root.is_symlink() or backup_root.parent.is_symlink()):
        raise ValueError("Rebuild directories must not be symbolic links")
    if not directory.exists():
        return ""
    if not directory.is_dir() or directory.name not in {"base", "c", "midi"}:
        raise ValueError("Invalid rebuild directory")
    backup_root.mkdir(parents=True, exist_ok=True)
    destination = backup_root / f"{label}-{uuid.uuid4().hex}"
    directory.rename(destination)
    return str(destination.relative_to(backup_root.parent))
