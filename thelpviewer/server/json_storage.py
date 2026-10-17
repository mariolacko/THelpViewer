"""Atomic JSON publication for persistent server settings and migration metadata."""

import json
from pathlib import Path

from .file_storage import atomic_file


def write_json(path: Path, value) -> None:
    with atomic_file(path) as output:
        output.write(json.dumps(value, indent=2, allow_nan=False).encode("utf-8"))
