"""HELP source selection and ingestion; archive mechanics live in server.archives."""

from dataclasses import dataclass
import filecmp
from fnmatch import fnmatch
from pathlib import Path
import tempfile

from ..archives.core import ExtractorTools, extract_file
from ..archives.containers import expand_single_file_payloads
from ..archives.nested import extract_nested
from ..processing import report_progress
from .sources import collect_help_files, copy_help_files, is_help_file_path


@dataclass(frozen=True, slots=True)
class HelpInput:
    path: Path
    collection: str
    members: tuple[str, ...] = ()
    language: str | None = None
    direct: bool = False
    product: object | None = None
    inner_member: str = ""
    allow_partial: bool = False


def ingest_help(source, sources_dir, tools):
    """Apply a provider-independent extraction/selection plan to a cached input."""
    if source.direct:
        if source.members and not any(fnmatch(source.path.name.casefold(), Path(name.replace("\\", "/")).name.casefold())
                                      for name in source.members):
            return []
        return copy_help_files([source.path], sources_dir / source.collection, sources_dir)
    if source.members and not source.inner_member:
        return collect_archive_members(source.path, source.members, source.collection, sources_dir, tools,
                                       allow_partial=source.allow_partial)
    if source.product is None and not source.inner_member:
        return collect_from_archive(source.path, source.collection, sources_dir, tools, lang_code=source.language)
    with tempfile.TemporaryDirectory(prefix="thelp-ingest-") as directory:
        root = Path(directory)
        work = root / "contents"
        extract_file(source.path, work, tools)
        if source.inner_member:
            matches = [path for path in work.rglob("*") if path.name.casefold() == source.inner_member.casefold() and path.is_file()]
            if len(matches) != 1:
                raise ValueError(f"Missing/ambiguous inner archive: {source.inner_member}")
            unpacked = root / "inner"
            extract_file(matches[0], unpacked, tools)
            work = unpacked
        else:
            extract_nested(work, tools, skip=is_help_file_path)
            expand_single_file_payloads(work, tools)
        files = sorted(path for path in work.rglob("*") if path.is_file())
        if source.product is not None:
            primary = [path for path in files if source.product.conversion.matches(path)]
            files = primary or [path for path in files if source.product.conversion.matches(path, secondary=True)]
        if source.members:
            selected = []
            for name in source.members:
                matches = [path for path in files if path.name.casefold() == name.casefold()]
                preferred = [path for path in matches if "GCDATA" in {part.upper() for part in path.parts}]
                matches = preferred or matches
                if len(matches) != 1:
                    raise ValueError(f"Missing/ambiguous source member: {name}")
                selected.extend(matches)
            files = selected
        return copy_help_files(files, sources_dir / source.collection, sources_dir)


def collect_from_archive(
    archive: Path,
    label: str,
    sources_dir: Path,
    tools: ExtractorTools,
    *,
    lang_code: str | None = None,
) -> list[Path]:
    """Extract one downloaded container, recurse, collect help files, copy them."""
    lang_suffix = f" ({lang_code})" if lang_code else ""
    target_dir = sources_dir / f"{label}{lang_suffix}".strip()

    with tempfile.TemporaryDirectory(prefix="dlhelp_") as tmp:
        tmp_path = Path(tmp)
        extract_file(archive, tmp_path, tools)
        extract_nested(tmp_path, tools, skip=is_help_file_path)
        expand_single_file_payloads(tmp_path, tools)
        report_progress("Collecting HELP files", archive.name)
        files = collect_help_files(tmp_path)
        if not files:
            return []
        return copy_help_files(files, target_dir, sources_dir)


def collect_archive_members(
    archive: Path,
    members: tuple[str, ...],
    label: str,
    sources_dir: Path,
    tools: ExtractorTools,
    *,
    allow_partial: bool = False,
) -> list[Path]:
    """Collect only configured files from an archive, including disk images."""
    if not members:
        raise ValueError("No archive members configured")

    with tempfile.TemporaryDirectory(prefix="dlmembers_") as tmp:
        work_dir = Path(tmp)
        extract_file(archive, work_dir, tools)

        def find_members() -> tuple[list[Path], list[str]]:
            files = sorted(path for path in work_dir.rglob("*") if path.is_file())
            # Index component-aligned suffixes once, not once per requested
            # member. CD images contain thousands of unrelated source files.
            names, suffixes = {}, {}
            for path in files:
                names.setdefault(path.name.casefold(), []).append(path)
                parts = path.relative_to(work_dir).as_posix().casefold().split("/")
                for index in range(len(parts)):
                    suffixes.setdefault("/".join(parts[index:]), []).append(path)
            selected: list[Path] = []
            missing: list[str] = []
            for pattern in members:
                needle = pattern.casefold().replace("\\", "/")
                candidates = suffixes if "/" in needle else names
                if any(char in needle for char in "*?["):
                    matches = sorted({path for name, paths in candidates.items()
                                      if fnmatch(name, needle) for path in paths})
                else:
                    matches = candidates.get(needle, [])
                if len(matches) > 1:
                    first = matches[0]
                    if any(path.name.casefold() != first.name.casefold() or not filecmp.cmp(path, first, shallow=False)
                           for path in matches[1:]):
                        raise ValueError(f"Missing archive members: {pattern} (ambiguous)")
                    # Split-media assembly can expose an identical file both
                    # inside its disk and at the common root. It is one source.
                    matches = matches[:1]
                if not matches:
                    missing.append(pattern)
                elif matches[0] not in selected:
                    selected.append(matches[0])
            return selected, missing

        selected, missing = find_members()
        if missing:
            stems = {Path(name.replace("\\", "/")).stem.casefold() for name in members}
            extract_nested(work_dir, tools, skip=is_help_file_path,
                           complete=lambda: not find_members()[1],
                           prefer=lambda path: path.stem.casefold() in stems)
            selected, missing = find_members()
        if missing:
            expand_single_file_payloads(work_dir, tools)
            selected, missing = find_members()
        if missing and not allow_partial:
            raise ValueError(f"Missing archive members: {', '.join(missing)}")
        report_progress("Collecting HELP files", archive.name)
        return copy_help_files(selected, sources_dir / label, sources_dir)
