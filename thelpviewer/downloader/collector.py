"""Help-file discovery, language detection, and final copy helpers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


HELP_EXTENSIONS = {".hlp", ".tph", ".tch", ".hlx", ".hl6", ".ng"}
WINHELP_MAGIC = b"\x3f\x5f\x03\x00"

SKIP_HELP_NAMES = {
    "CALC.HLP",
    "TUTOR.HLP",
    "INSTALL.HLP",
    "UTILS.HLP",
    "DEMOHELP.HLP",
    "DEMOHELP_BP7.HLP",
}

LANG_CODES: dict[str, str] = {
    "german": "DE",
    "deutsch": "DE",
    "french": "FR",
    "français": "FR",
    "francais": "FR",
    "spanish": "ES",
    "español": "ES",
    "espanol": "ES",
    "italian": "IT",
    "italiano": "IT",
    "dutch": "NL",
    "netherlands": "NL",
    "portuguese": "PT",
    "czech": "CZ",
    "polish": "PL",
    "russian": "RU",
    "swedish": "SE",
    "norwegian": "NO",
    "danish": "DK",
    "finnish": "FI",
    "hungarian": "HU",
}


def detect_language(text: str) -> str | None:
    """Guess a language code from one archive title or filename."""
    lowered = text.lower()
    for keyword, code in LANG_CODES.items():
        if re.search(r"[\[\(\s_]" + re.escape(keyword) + r"[\]\)\s_\.]", lowered):
            return code
    return None


def is_winhelp(path: Path) -> bool:
    """Return ``True`` for Windows help files that should be ignored here."""
    try:
        return path.read_bytes()[:4] == WINHELP_MAGIC
    except OSError:
        return False


def collect_help_files(work_dir: Path) -> list[Path]:
    """Find all supported help files under one extracted work tree."""
    found: list[Path] = []
    for path in sorted(work_dir.rglob("*")):
        if not (path.is_file() and path.suffix.lower() in HELP_EXTENSIONS):
            continue
        if path.name.upper() in SKIP_HELP_NAMES:
            print(f"    [skipped] {path.name} (accessory)")
            continue
        if path.suffix.lower() == ".hlp" and is_winhelp(path):
            print(f"    [skipped] {path.name} (Windows HLP)")
            continue
        found.append(path)
    return found


def copy_help_files(files: list[Path], target_dir: Path, sources_dir: Path) -> list[Path]:
    """Copy found help files into the final product directory."""
    copied: list[Path] = []
    for src in files:
        dest = target_dir / src.name.upper()
        if dest.exists():
            print(f"    [skipped] {dest.name} (exists)")
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"    ✓ {dest.relative_to(sources_dir)}")
        copied.append(dest)
    return copied
