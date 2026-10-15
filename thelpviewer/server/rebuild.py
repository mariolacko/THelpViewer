"""Recoverable directory replacement and bounded, post-publication backups."""

import logging
from pathlib import Path
import re
import shutil
import threading
import uuid

from .settings import validate_backup_count

_backup_lock = threading.RLock()
_logger = logging.getLogger(__name__)


def prune_backups(newest: Path, prefixes: tuple[str, ...], keep: int) -> list[Path]:
    """Keep the just-published recovery copy and newest siblings of its family.

    Call only after successful publication/rebuild. Cleanup errors must not turn
    a committed replacement into a failed transaction. Foreign names and links
    are never cleanup targets; failed rebuilds do not call this function.
    """
    validate_backup_count(keep)
    pattern = re.compile("(?:" + "|".join(re.escape(prefix) for prefix in prefixes) + ")[0-9a-f]{32}")
    removed = []
    with _backup_lock:
        try:
            root = newest.parent
            if root.is_symlink() or root.parent.is_symlink() or newest.is_symlink():
                raise ValueError("Backup directories must not be symbolic links")
            if not pattern.fullmatch(newest.name) or not newest.is_dir():
                raise ValueError("Invalid completed backup directory")
            candidates = [path for path in root.iterdir()
                          if pattern.fullmatch(path.name) and not path.is_symlink() and path.is_dir()]
            candidates.sort(key=lambda path: (path == newest, path.stat().st_ctime_ns, path.name), reverse=True)
            for path in candidates[keep:]:
                if path.is_symlink() or any(child.is_symlink() for child in path.rglob("*")):
                    _logger.warning("Skipping linked backup directory: %s", path)
                    continue
                try:
                    shutil.rmtree(path)
                    removed.append(path)
                except OSError:
                    _logger.warning("Could not remove old backup %s", path, exc_info=True)
        except (OSError, ValueError):
            _logger.warning("Could not apply backup retention for %s", newest, exc_info=True)
    return removed


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
