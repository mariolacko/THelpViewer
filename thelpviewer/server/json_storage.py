"""Atomic JSON publication for persistent server settings and migration metadata."""

import json
import os
from pathlib import Path
import tempfile


def write_json(path: Path, value) -> None:
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("JSON storage must not contain symbolic links")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(json.dumps(value, indent=2, allow_nan=False).encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
