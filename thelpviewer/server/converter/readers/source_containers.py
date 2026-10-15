"""Decode and validate source transport containers before HELP topic parsing."""

from __future__ import annotations


def unpack_dos_backup(data: bytes) -> tuple[bytes, dict[str, object]]:
    """Restore one complete DOS 2.x–3.2 BACKUP file in memory, never on disk."""
    if len(data) < 128 or data[0] not in (0, 0xFF) or data[2:5] != b"\x00\x00\x00":
        return data, {}
    length = data[0x53]
    if not 2 <= length <= 78 or data[0x54:0x80] != bytes(44):
        return data, {}
    end = 5 + length
    raw_path = data[5:end - 1]
    if data[end - 1] != 0 or any(data[end:0x53]):
        return data, {}
    if not raw_path.startswith(b"\\") or any(value < 32 or value >= 127 for value in raw_path):
        return data, {}
    pathname = raw_path.decode("ascii")
    parts = pathname.split("\\")[1:]
    if any(not part or part in {".", ".."} or any(char in '<>:"/|?*' for char in part) for part in parts):
        return data, {}
    if data[0] != 0xFF or data[1] != 1:
        raise ValueError("Incomplete/multi-volume DOS BACKUP source is not supported.")
    if len(data) == 128:
        raise ValueError("DOS BACKUP source has no file payload.")
    return data[128:], {"format": "dos-backup", "pathname": pathname, "disk_number": data[1]}
