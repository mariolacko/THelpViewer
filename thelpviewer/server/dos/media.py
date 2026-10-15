"""Owner-scoped floppy and CD images; never arbitrary host mounts."""

import hashlib
from pathlib import Path
import re

from .paths import DosError, atomic_file, user_dir


class DosMediaStore:
    def __init__(self, users_dir: Path):
        self.users_dir = users_dir

    def add_media(self, account_id: str, kind: str, data: bytes, limit: int) -> str:
        if kind not in ("floppy", "cd"):
            raise DosError("Only floppy and CD images may be mounted")
        if kind == "floppy":
            if len(data) % 512 or len(data) < 512 or len(data) > 16 * 1024 * 1024 or data[510:512] != b"\x55\xaa":
                raise DosError("Invalid raw floppy image")
        elif len(data) < 32774 or data[32769:32774] != b"CD001":
            raise DosError("CD media must be an ISO9660 image")
        if len(data) > limit:
            raise DosError("Media exceeds its configured quota")
        directory = user_dir(self.users_dir, account_id) / "media"
        directory.mkdir(exist_ok=True)
        ident = hashlib.sha256(data).hexdigest()[:32] + (".img" if kind == "floppy" else ".iso")
        if (directory / ident).is_file():
            return ident
        if len(list(directory.iterdir())) >= 8:
            raise DosError("Media library is full (8 images)")
        atomic_file(directory / ident, data)
        return ident

    def media_path(self, account_id: str, ident: str) -> Path | None:
        if not re.fullmatch(r"[a-f0-9]{32}\.(img|iso)", ident):
            return None
        path = user_dir(self.users_dir, account_id) / "media" / ident
        return path if path.is_file() and not path.is_symlink() else None
