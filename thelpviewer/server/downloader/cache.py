"""Atomic file publication shared by all download providers."""

from contextlib import contextmanager
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote


def download_filename(name: str) -> str:
    """Keep a readable, decoded archive name within its download directory."""
    return re.sub(r"[^\w\-. ]", "_", unquote(name)).strip(" .") or "archive"


@contextmanager
def atomic_download(destination: Path):
    if destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("Download cache must not contain symbolic links")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".download-", delete=False) as stream:
            temporary = Path(stream.name)
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
