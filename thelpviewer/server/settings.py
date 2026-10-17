"""Small, persisted administrator settings, separate from disk source manifests."""

from __future__ import annotations

import json
from pathlib import Path
import threading

from .json_storage import write_json

DEFAULT_BACKUP_COUNT = 2
MAX_BACKUP_COUNT = 100
DEFAULT_DOWNLOAD_CACHE_DAYS = 30
MAX_DOWNLOAD_CACHE_DAYS = 3650
DEFAULT_SETTINGS = {"dos_user_disk_mb": 64, "backup_count": DEFAULT_BACKUP_COUNT,
                    "download_cache_days": DEFAULT_DOWNLOAD_CACHE_DAYS}


def validate_backup_count(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_BACKUP_COUNT:
        raise ValueError(f"Backup count must be 1–{MAX_BACKUP_COUNT}")
    return value


class ServerSettings:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def validate(values: dict) -> dict:
        if not isinstance(values, dict) or set(values) != DEFAULT_SETTINGS.keys():
            raise ValueError("Expected DOS user disk capacity, backup count and download cache days")
        capacity = values["dos_user_disk_mb"]
        if type(capacity) is not int or not 1 <= capacity <= 256:
            raise ValueError("DOS user disk capacity must be 1–256 MiB")
        days = values["download_cache_days"]
        if type(days) is not int or not 1 <= days <= MAX_DOWNLOAD_CACHE_DAYS:
            raise ValueError(f"Download cache lifetime must be 1–{MAX_DOWNLOAD_CACHE_DAYS} days")
        return {"dos_user_disk_mb": capacity, "backup_count": validate_backup_count(values["backup_count"]),
                "download_cache_days": days}

    def get(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return dict(DEFAULT_SETTINGS)
            return self.validate({**DEFAULT_SETTINGS, **json.loads(self.path.read_text(encoding="utf-8"))})

    def update(self, values: dict) -> dict:
        if not isinstance(values, dict):
            raise ValueError("Expected server settings")
        with self._lock:
            values = self.validate({**self.get(), **values})
            write_json(self.path, values)
        return values
