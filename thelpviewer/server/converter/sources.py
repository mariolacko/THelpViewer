"""Help-file discovery, language detection, and final copy helpers."""

from __future__ import annotations

import re
import shutil
import os
from pathlib import Path

from ...help_database import lookup_help_database_entry
from .selection import archive_member_selected, source_entry_selected
from ..file_storage import atomic_file, locked_path

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
        if path.name.upper() in SKIP_HELP_NAMES and lookup_help_database_entry(path) is None:
            print(f"    [skipped] {path.name} (accessory)")
            continue
        found.append(path)
    return found


def copy_help_files(files: list[Path], target_dir: Path, sources_dir: Path) -> list[Path]:
    """Copy found help files into the final product directory."""
    copied: list[Path] = []
    for src in files:
        entry = lookup_help_database_entry(src)
        if entry and not source_entry_selected(entry):
            print(f"    [skipped] {src.name} (different verified HELP edition)")
            continue
        if not archive_member_selected(target_dir / src.name, entry):
            print(f"    [skipped] {src.name} (not in archive_members)")
            continue
        directory = sources_dir / entry.collection if entry and entry.collection else target_dir
        dest = directory / src.name.upper()
        with locked_path(dest):
            if dest.is_file() and not dest.is_symlink() and dest.read_bytes() != src.read_bytes():
                previous = lookup_help_database_entry(dest)
                if previous and entry and entry.product_key and (
                        previous.product_key, previous.version, previous.collection, previous.bundle_stem) == (
                        entry.product_key, entry.version, entry.collection, entry.bundle_stem):
                    # Registered revisions of the same edition/component are
                    # alternatives. Retain a verified original rather than
                    # overwriting it merely to fill another missing component.
                    os.utime(dest, None)
                    print(f"    [skipped] {dest.name} (verified component revision exists)")
                    continue
                canonical = sources_dir / previous.collection / dest.name if previous and previous.collection else dest
                if canonical != dest:
                    # A corrected manifest may separate editions formerly stored
                    # together. Move only a CRC-verified original to its declared
                    # collection; never replace a different or unknown payload.
                    with locked_path(canonical):
                        if canonical.is_symlink() or canonical.exists() and (
                                not canonical.is_file() or canonical.read_bytes() != dest.read_bytes()):
                            raise ValueError(f"Conflicting original HELP source: {canonical.relative_to(sources_dir)}")
                        canonical.parent.mkdir(parents=True, exist_ok=True)
                        dest.replace(canonical)
            if dest.exists() or dest.is_symlink():
                if not dest.is_file() or dest.is_symlink() or dest.read_bytes() != src.read_bytes():
                    raise ValueError(f"Conflicting original HELP source: {dest.relative_to(sources_dir)}")
                os.utime(dest, None)
                print(f"    [skipped] {dest.name} (exists)")
                continue
            directory.mkdir(parents=True, exist_ok=True)
            with src.open("rb") as input_file, atomic_file(dest) as output_file:
                shutil.copyfileobj(input_file, output_file)
        print(f"    ✓ {dest.relative_to(sources_dir)}")
        copied.append(dest)
    return copied
