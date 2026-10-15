"""Help-file discovery, language detection, and final copy helpers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


HELP_EXTENSIONS = {".hlp", ".tph", ".tch", ".tah", ".tdh", ".tfh", ".hlx", ".hl6", ".ng"}

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


def is_help_file_path(path: Path) -> bool:
    """Return True for file names that can contain supported help payloads."""
    suffix = path.suffix.lower()
    return suffix in HELP_EXTENSIONS or (
        len(suffix) == 4
        and suffix.startswith(".t")
        and suffix.endswith("h")
    )


def collect_help_files(work_dir: Path) -> list[Path]:
    """Find original HELP candidates; converter support is a separate check."""
    found: list[Path] = []
    for path in sorted(work_dir.rglob("*")):
        if not (path.is_file() and is_help_file_path(path)):
            continue
        if path.name.upper() in SKIP_HELP_NAMES:
            print(f"    [skipped] {path.name} (accessory)")
            continue
        found.append(path)
    return found


def copy_help_files(files: list[Path], target_dir: Path, sources_dir: Path) -> list[Path]:
    """Copy found help files into the final product directory."""
    copied: list[Path] = []
    for src in files:
        dest = target_dir / src.name.upper()
        if dest.exists() or dest.is_symlink():
            if not dest.is_file() or dest.is_symlink() or dest.read_bytes() != src.read_bytes():
                raise ValueError(f"Conflicting original HELP source: {dest.relative_to(sources_dir)}")
            print(f"    [skipped] {dest.name} (exists)")
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"    ✓ {dest.relative_to(sources_dir)}")
        copied.append(dest)
    return copied
