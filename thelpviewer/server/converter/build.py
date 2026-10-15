"""Stage and publish selected HELP groups without a shell or partial catalog."""

import json
from pathlib import Path
import shutil
import tempfile
import uuid

from ..downloader.catalog import BUILD_GROUPS, build_group_for_help_root, build_group_for_source_root
from ..rebuild import prune_backups
from ..settings import DEFAULT_BACKUP_COUNT, validate_backup_count
from ...help_database import load_help_manifest, lookup_help_database_entry
from ...help_packages import help_package_id
from .catalog import _catalog_entry, rebuild_catalog
from .exporter import iter_help_files
from .writers.bundle import _build_pending_bundle_export, _product_metadata_for_group, _product_metadata_for_source, export_bundle_tree


def build_help_groups(groups: list[str], sources_dir: Path, helps_dir: Path, *, on_progress=None,
                      product_keys: list[str] | None = None, keep_products: list[str] | None = None,
                      package_ids: list[str] | None = None, keep_packages: list[str] | None = None,
                      backup_count: int = DEFAULT_BACKUP_COUNT) -> dict:
    validate_backup_count(backup_count)
    if set(groups) - BUILD_GROUPS.keys():
        raise ValueError("Unknown HELP build group")
    manifest = load_help_manifest()
    if (product_keys is not None and set(product_keys) - manifest.product_map.keys()
            or keep_products is not None and set(keep_products) - manifest.product_map.keys()):
        raise ValueError("Unknown HELP product")
    if not groups and keep_products is None and keep_packages is None:
        return {"bundles": 0, "backup": ""}
    if helps_dir.is_symlink() or sources_dir.is_symlink():
        raise ValueError("HELP roots must not be symbolic links")
    paths = []
    found_groups = set()
    found_products = set()
    found_packages = set()
    database = manifest.entry_map
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
                    for path in candidates:
                        entry = lookup_help_database_entry(path, database) if product_keys is not None or package_ids is not None else None
                        pending = _build_pending_bundle_export(path, source_root=sources_dir,
                            helps_dir=helps_dir, database_entry=entry)
                        product, _name, version = _product_metadata_for_source(path, pending.group_name, entry)
                        package = help_package_id(product, version)
                        if (product_keys is None or product in product_keys) and (package_ids is None or package in package_ids):
                            paths.append(path)
                            found_products.add(product)
                            found_packages.add(package)
    missing = (set(package_ids) - found_packages if package_ids is not None else
               set(product_keys) - found_products if product_keys is not None else set(groups) - found_groups)
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
        if keep_products is not None or keep_packages is not None:
            catalog_path = stage / "catalog.json"
            previous_catalog = {entry["file"]: entry for entry in json.loads(catalog_path.read_text())} if catalog_path.exists() else {}
            bundles = list(stage.rglob("*.json.gz"))
            for index, path in enumerate(bundles):
                entry = previous_catalog.get(path.relative_to(stage).as_posix()) or _catalog_entry(path, stage)
                product = entry.get("product") or _product_metadata_for_group(entry["group"])[0]
                package = help_package_id(product, entry.get("version", ""))
                remove = (package not in keep_packages or package in (package_ids or [])) if keep_packages is not None else (
                    product not in keep_products or product in (product_keys or []))
                if product in manifest.product_map and remove:
                    path.unlink()
                if on_progress:
                    on_progress({"phase": "Checking HELP selection", "processed": index + 1,
                                 "total": len(bundles), "file": path.name})
            for directory in sorted((p for p in stage.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                if not any(directory.iterdir()):
                    directory.rmdir()
        else:
            for root in stage.iterdir():
                if root.is_dir() and build_group_for_help_root(root.name) in groups:
                    shutil.rmtree(root)
        results = export_bundle_tree(sources_dir, stage, layout="helps", source_paths=paths,
                                     on_progress=on_progress) if paths else []
        failed = [str(result.input_path) for result in results if result.format_name == "ERROR"]
        if failed or (paths and not results):
            raise ValueError("HELP conversion failed: " + ", ".join(failed))
        count = rebuild_catalog(stage, stage / "catalog.json")
        # Validate the completed catalog before activating it.
        catalog = json.loads((stage / "catalog.json").read_text(encoding="utf-8"))
        if (not catalog and keep_products is None and keep_packages is None) or any(not (stage / entry["file"]).is_file() for entry in catalog):
            raise ValueError("Generated HELP catalog is incomplete")
        if helps_dir.exists():
            helps_dir.rename(backup)
        try:
            stage.rename(helps_dir)
        except OSError:
            if backup.exists():
                backup.rename(helps_dir)
            raise
        if backup.exists():
            prune_backups(backup, (f".{helps_dir.name}-previous-",), backup_count)
        return {"bundles": count, "backup": str(backup) if backup.exists() else ""}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
