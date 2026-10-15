"""Shared DOS path validation and atomic file publication."""

import os
from pathlib import Path
import re
import tempfile

MAX_FILES = 4096
MAX_SOURCE_BYTES = 64 * 1024 * 1024
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ACCOUNT_RE = re.compile(r"^[a-f0-9]{32}$")


class DosError(ValueError):
    pass


def c_path(value: str) -> str:
    """Canonical DOS names, never a host path or an archive escape."""
    if not isinstance(value, str) or not value or len(value) > 260 or value.startswith(("/", "\\")):
        raise DosError("Invalid C drive path")
    parts = value.replace("\\", "/").split("/")
    for part in parts:
        if (part in ("", ".", "..") or len(part) > 64
                or not re.fullmatch(r"[a-zA-Z0-9_. !#$%&'()@^{}~-]+", part)
                or part.rstrip(" .") != part):
            raise DosError("Invalid C drive path")
    return "/".join(parts).upper()


def atomic_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        output.write(data)
        temporary = Path(output.name)
    os.replace(temporary, path)


def user_dir(users_dir: Path, account_id: str) -> Path:
    if not ACCOUNT_RE.fullmatch(account_id):
        raise DosError("Invalid account storage ID")
    directory = users_dir / account_id
    if directory.is_symlink() or directory.parent.is_symlink():
        raise DosError("Private user storage must not be a symbolic link")
    directory.mkdir(parents=True, exist_ok=True)
    return directory
