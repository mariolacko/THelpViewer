"""Package-owned DOS search paths and the managed AUTOEXEC PATH line."""

import re

from .paths import c_path


_SET_PATH = re.compile(r'^\s*@?SET\s+(?:"PATH=(.*)"|PATH=(.*))\s*$', re.IGNORECASE)


def package_paths(config: dict, installed: dict) -> list[str]:
    return list(dict.fromkeys(c_path(source["path"]) for source in config["sources"]
                             if "path" in source and installed.get(source["id"])))


def dos_search_path(directories: list[str], baseline: str = "Z:\\") -> str:
    paths = ["C:\\" + name.replace("/", "\\") for name in directories]
    paths.extend(part.strip().replace("/", "\\") for part in baseline.split(";") if part.strip())
    unique = {}
    for path in paths:
        unique.setdefault(path.upper(), path)
    return ";".join(unique.values())


def autoexec_with_path(current: bytes, configured: bytes, directories: list[str]) -> bytes:
    """Manage SET PATH from the manifest; leave other existing BAT lines intact."""
    baseline = "Z:\\"
    for line in configured.decode("cp437").splitlines():
        match = _SET_PATH.fullmatch(line)
        if match:
            baseline = match[1] if match[1] is not None else match[2]
    command = "SET PATH=" + dos_search_path(directories, baseline)
    lines = current.decode("cp437").splitlines()
    positions = [index for index, line in enumerate(lines) if _SET_PATH.fullmatch(line)]
    position = positions[0] if positions else int(bool(lines) and lines[0].strip().upper() == "@ECHO OFF")
    lines = [line for line in lines if not _SET_PATH.fullmatch(line)]
    lines.insert(position, command)
    return ("\r\n".join(lines) + "\r\n").encode("cp437")
