"""Source/output planning; independent of renderers, transfers and publication."""

from dataclasses import dataclass
from pathlib import Path
from thelpviewer.help_database import HelpDatabaseEntry, BuildGroupSpec, load_help_manifest
from .exporter import load_document

BUILD_GROUPS = load_help_manifest().build_group_map
BUILD_GROUP_ORDER = tuple(BUILD_GROUPS)


def all_build_groups(*, default_only: bool = False) -> list[str]:
    """Return stable build group keys used by the shell wrapper."""
    if not default_only:
        return list(BUILD_GROUP_ORDER)
    return [key for key in BUILD_GROUP_ORDER if BUILD_GROUPS[key].include_by_default]


def build_group_spec(key: str) -> BuildGroupSpec:
    """Return one build-group spec or raise ``KeyError``."""
    return BUILD_GROUPS[key]


def normalize_build_group(value: str) -> str | None:
    """Resolve a manifest build-group key or alias."""
    token = value.strip().casefold().replace("_", "-")
    if token == "all":
        return "all"
    for group in load_help_manifest().build_groups:
        names = (group.key, *group.aliases)
        if token in {name.casefold().replace("_", "-") for name in names}:
            return group.key
    return None


def build_source_root_prefixes_for_groups(selected_keys: list[str] | None = None) -> list[str]:
    """Return source-root prefixes for the selected build groups."""
    wanted = set(selected_keys or all_build_groups(default_only=True))
    roots: list[str] = []
    for key in BUILD_GROUP_ORDER:
        if key not in wanted:
            continue
        for root in BUILD_GROUPS[key].source_root_prefixes:
            if root not in roots:
                roots.append(root)
    return roots


def build_help_prefixes_for_groups(selected_keys: list[str] | None = None) -> list[str]:
    """Return top-level help-dir prefixes for the selected build groups."""
    wanted = set(selected_keys or all_build_groups(default_only=True))
    prefixes: list[str] = []
    for key in BUILD_GROUP_ORDER:
        if key not in wanted:
            continue
        for prefix in BUILD_GROUPS[key].help_dir_prefixes:
            if prefix not in prefixes:
                prefixes.append(prefix)
    return prefixes


def _build_group_for_root(name: str, prefix_field: str) -> str | None:
    """Use the most specific manifest prefix when build groups overlap."""
    owner: str | None = None
    longest = 0
    for group in load_help_manifest().build_groups:
        for prefix in getattr(group, prefix_field):
            if name.startswith(prefix) and len(prefix) > longest:
                owner = group.key
                longest = len(prefix)
    return owner


def build_group_for_source_root(name: str) -> str | None:
    return _build_group_for_root(name, "source_root_prefixes")


def build_group_for_help_root(name: str) -> str | None:
    return _build_group_for_root(name, "help_dir_prefixes")


@dataclass(frozen=True, slots=True)
class BundlePlan:
    source_path: Path
    bundle_dir: Path
    bundle_path: Path
    bundle_stem: str
    group_name: str = ""
    database_entry: HelpDatabaseEntry | None = None


def bundle_stem_for_entry(source_path: Path, database_entry: object | None) -> str:
    if database_entry is not None:
        bundle_stem = getattr(database_entry, "bundle_stem", "")
        if isinstance(bundle_stem, str) and bundle_stem.strip():
            return bundle_stem.strip().lower()
        filenames = getattr(database_entry, "filenames", ())
        if filenames:
            return Path(filenames[0]).stem.lower()
    return source_path.stem.lower()


def build_pending_bundle_export(
    path: Path,
    *,
    source_root: Path,
    helps_dir: Path,
    database_entry: HelpDatabaseEntry | None,
) -> BundlePlan:
    relative = path.relative_to(source_root)
    group_name = (
        database_entry.collection
        if database_entry is not None and getattr(database_entry, "collection", "")
        else str(relative.parent).replace("\\", "/")
    )
    if (database_entry is None or not database_entry.collection) and len(relative.parent.parts) > 1:
        # A declared source container can hold publication roots. The result
        # must not depend on whether the caller exports that container or its
        # parent (CLI product roots versus the server's complete source tree).
        container, publication_root, *rest = relative.parent.parts
        for group in load_help_manifest().build_groups:
            if (any(container.startswith(prefix) for prefix in group.source_root_prefixes)
                    and any(publication_root.startswith(prefix) for prefix in group.help_dir_prefixes)):
                group_name = Path(publication_root, *rest).as_posix()
                break
    group_parts = tuple(part for part in Path(group_name).parts if part not in {"", "."})
    bundle_dir = helps_dir.joinpath(*group_parts) if group_parts else helps_dir
    bundle_stem = bundle_stem_for_entry(path, database_entry)
    return BundlePlan(
        source_path=path,
        bundle_dir=bundle_dir,
        bundle_path=bundle_dir / f"{bundle_stem}.json.gz",
        bundle_stem=bundle_stem,
        group_name=group_name,
        database_entry=database_entry,
    )


def pending_bundle_topic_count(
    candidate: BundlePlan,
    *,
    cache: dict[Path, int],
) -> int:
    cached = cache.get(candidate.source_path)
    if cached is not None:
        return cached
    try:
        cached = len(load_document(candidate.source_path).topics)
    except Exception:
        cached = -1
    cache[candidate.source_path] = cached
    return cached


def prefer_pending_bundle_export(
    current: BundlePlan,
    candidate: BundlePlan,
    *,
    topic_count_cache: dict[Path, int],
) -> bool:
    current_count = pending_bundle_topic_count(current, cache=topic_count_cache)
    candidate_count = pending_bundle_topic_count(candidate, cache=topic_count_cache)
    if candidate_count != current_count:
        return candidate_count > current_count
    return str(candidate.source_path).casefold() < str(current.source_path).casefold()
