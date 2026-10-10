"""Stage and publish selected HELP groups without a shell or partial catalog."""

import json
from pathlib import Path
import shutil
import tempfile
import uuid

from ..downloader.catalog import BUILD_GROUPS, build_group_for_help_root, build_group_for_source_root
from .catalog import rebuild_catalog
from .exporter import iter_help_files
from .writers.bundle import export_bundle_tree


def build_help_groups(groups: list[str], sources_dir: Path, helps_dir: Path, *, on_progress=None) -> dict:
    if set(groups) - BUILD_GROUPS.keys():
        raise ValueError("Unknown HELP build group")
    if not groups:
        return {"bundles": 0, "backup": ""}
    if helps_dir.is_symlink() or sources_dir.is_symlink():
        raise ValueError("HELP roots must not be symbolic links")
    paths = []
    found_groups = set()
    if sources_dir.exists():
        for root in sorted(sources_dir.iterdir()):
            group = build_group_for_source_root(root.name)
            if root.is_dir() and group in groups:
                candidates = iter_help_files(root)
                if any(path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
                       for path in candidates):
                    raise ValueError("HELP sources must not contain symbolic links")
                if candidates:
                    found_groups.add(group)
                    paths.extend(candidates)
    missing = set(groups) - found_groups
    if missing:
        raise ValueError("No convertible source files for: " + ", ".join(sorted(missing)))
    helps_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{helps_dir.name}-build-", dir=helps_dir.parent))
    backup = helps_dir.parent / f".{helps_dir.name}-previous-{uuid.uuid4().hex}"
    try:
        if helps_dir.exists():
            if any(path.is_symlink() for path in helps_dir.rglob("*")):
                raise ValueError("Published HELP files must not contain symbolic links")
            shutil.copytree(helps_dir, stage, dirs_exist_ok=True)
        # Delete only disposable staged output, never original sources or live bundles.
        for root in stage.iterdir():
            if root.is_dir() and build_group_for_help_root(root.name) in groups:
                shutil.rmtree(root)
        results = export_bundle_tree(sources_dir, stage, layout="helps", source_paths=paths,
                                     on_progress=on_progress)
        failed = [str(result.input_path) for result in results if result.format_name == "ERROR"]
        if failed or not results:
            raise ValueError("HELP conversion failed: " + ", ".join(failed))
        count = rebuild_catalog(stage, stage / "catalog.json")
        # Validate the completed catalog before activating it.
        catalog = json.loads((stage / "catalog.json").read_text(encoding="utf-8"))
        if not catalog or any(not (stage / entry["file"]).is_file() for entry in catalog):
            raise ValueError("Generated HELP catalog is incomplete")
        if helps_dir.exists():
            helps_dir.rename(backup)
        try:
            stage.rename(helps_dir)
        except OSError:
            if backup.exists():
                backup.rename(helps_dir)
            raise
        return {"bundles": count, "backup": str(backup) if backup.exists() else ""}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
