"""Small, persisted administrator settings, separate from disk source manifests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading


class ServerSettings:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def validate(values: dict) -> dict:
        if not isinstance(values, dict) or set(values) != {"dos_user_disk_mb"}:
            raise ValueError("Expected DOS user disk capacity")
        capacity = values["dos_user_disk_mb"]
        if type(capacity) is not int or not 1 <= capacity <= 256:
            raise ValueError("DOS user disk capacity must be 1–256 MiB")
        return {"dos_user_disk_mb": capacity}

    def get(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return {"dos_user_disk_mb": 64}
            return self.validate(json.loads(self.path.read_text(encoding="utf-8")))

    def update(self, values: dict) -> dict:
        values = self.validate(values)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as output:
                output.write(json.dumps(values).encode("utf-8"))
                temporary = Path(output.name)
            os.replace(temporary, self.path)
        return values
