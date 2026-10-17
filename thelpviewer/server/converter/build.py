"""Stage and publish selected HELP groups without a shell or partial catalog."""

import json
import logging
import os
import re
from contextlib import nullcontext
from pathlib import Path
import shutil
import tempfile
import uuid

from .planning import BUILD_GROUPS, build_group_for_help_root, build_group_for_source_root
from ..rebuild import prune_backups
from ..file_storage import relocate_directory
from ..settings import DEFAULT_BACKUP_COUNT, validate_backup_count
from ...help_database import load_help_manifest, lookup_help_database_entry
from ...help_packages import help_package_id
from .catalog import _catalog_entry, rebuild_catalog
from .exporter import iter_help_files
from .planning import build_pending_bundle_export
from .metadata import product_metadata_for_group, product_metadata_for_source
from .writers.bundle import export_bundle_tree
from .results import ConversionError
from ..processing import observe_progress, report_progress


def recover_help_publication(helps_dir: Path, detail: dict) -> None:
    """Roll back an interrupted directory swap recorded before either rename.

    Only the exact owned staging/rollback names in the durable job are touched;
    unrelated or pre-journal build trees are not guessed or adopted.
    """
    stage_name, previous_name = detail.get("stage", ""), detail.get("previous", "")
    if (not re.fullmatch(re.escape(f".{helps_dir.name}-build-") + r"[a-z0-9_]+", stage_name)
            or not re.fullmatch(re.escape(f".{helps_dir.name}-previous-") + r"[0-9a-f]{32}", previous_name)):
        raise ValueError("Invalid HELP publication checkpoint")
    stage, previous = helps_dir.parent / stage_name, helps_dir.parent / previous_name
    if any(path.is_symlink() for root in (helps_dir, stage, previous) for path in (root, *root.parents)):
        raise ValueError("HELP recovery refuses symbolic links")
    if not helps_dir.exists() and previous.is_dir():
        previous.rename(helps_dir)
    if stage.exists():
        shutil.rmtree(stage)  # Exact disposable tree recorded by this job; never live content.


def _select_source_paths(groups, sources_dir, helps_dir, product_keys, package_ids):
    manifest = load_help_manifest()
    paths = []
    found_groups = set()
    found_products = set()
    found_packages = set()
    database = manifest.entry_map
    registered_collections = {}
    for entry in manifest.entries:
        product = manifest.product_map.get(entry.product_key)
        if product and entry.collection:
            package = help_package_id(entry.product_key, entry.version or product.default_version)
            registered_collections.setdefault(package, set()).add(entry.collection)
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
                        pending = build_pending_bundle_export(path, source_root=sources_dir,
                            helps_dir=helps_dir, database_entry=entry)
                        product, _name, version = product_metadata_for_source(path, pending.group_name, entry)
                        package = help_package_id(product, version)
                        if (package_ids is not None and entry is None and package in registered_collections
                                and path.parent.relative_to(sources_dir).as_posix() not in registered_collections[package]):
                            # A shared filename in another product's distribution
                            # does not identify a registered edition. Unknown CRCs
                            # in its own collection still reach decoder validation.
                            continue
                        if (product_keys is None or product in product_keys) and (package_ids is None or package in package_ids):
                            paths.append(path)
                            found_products.add(product)
                            found_packages.add(package)
    missing = (set(package_ids) - found_packages if package_ids is not None else
               set(product_keys) - found_products if product_keys is not None else set(groups) - found_groups)
    if missing:
        raise ValueError("No convertible source files for: " + ", ".join(sorted(missing)))
    return paths


def build_help_groups(groups: list[str], sources_dir: Path, helps_dir: Path, *, on_progress=None,
                      product_keys: list[str] | None = None, keep_products: list[str] | None = None,
                      package_ids: list[str] | None = None, keep_packages: list[str] | None = None,
                      backup_count: int = DEFAULT_BACKUP_COUNT, source_batches=None,
                      backup_dir: Path | None = None, on_publication=None) -> dict:
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
    if source_batches is not None and package_ids is None:
        raise ValueError("Pipelined HELP builds need explicit edition IDs")
    paths = _select_source_paths(groups, sources_dir, helps_dir, product_keys, package_ids) if source_batches is None else []
    helps_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{helps_dir.name}-build-", dir=helps_dir.parent))
    generation = uuid.uuid4().hex
    previous = helps_dir.parent / f".{helps_dir.name}-previous-{generation}"
    backup = (backup_dir or helps_dir.parent / "backups" / "help") / f"help-{generation}"
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
                product = entry.get("product") or product_metadata_for_group(entry["group"])[0]
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
        batches = [(None, paths)] if source_batches is None else (
            (edition, None)
            for edition in source_batches)
        converted, destinations = set(), set()
        for edition, paths in batches:
            if edition is not None:
                if edition not in package_ids or edition in converted:
                    raise ValueError("Unknown/duplicate ready HELP edition")
                converted.add(edition)
            def progress(status):
                if on_progress:
                    on_progress({**status, **({"product": edition} if edition is not None else {})})
            try:
                if paths is None:
                    paths = _select_source_paths(groups, sources_dir, helps_dir, product_keys, [edition])
                results = export_bundle_tree(sources_dir, stage, layout="helps", source_paths=paths,
                                             on_progress=progress, include_catalog=False) if paths else []
                failed = [f"{result.input_path}: {result.error}" for result in results if result.error]
                if failed or (paths and not results):
                    raise ConversionError("HELP conversion failed: " + ", ".join(failed))
            except Exception as error:
                if edition is None:
                    raise
                raise ConversionError(str(error), package_id=edition) from error
            # Refresh only successful conversion inputs, never passive CRC scans
            # or failed decodes. Read-only input metadata must not undo a build.
            for path in paths:
                try:
                    os.utime(path, None)
                except OSError:
                    logging.getLogger(__name__).warning("Cannot refresh HELP input retention: %s", path, exc_info=True)
            for result in results:
                if result.json_path in destinations:
                    raise ConversionError("Conflicting HELP edition output: " + str(result.json_path))
                destinations.add(result.json_path)
            if edition is not None and on_progress:
                on_progress({"product": edition, "phase": "Awaiting publication", "stage": "publish",
                             "stage_percent": None, "processed": 1, "total": 1})
        if source_batches is not None and converted != set(package_ids):
            raise ConversionError("Not all HELP editions became ready for conversion")
        with observe_progress(on_progress) if on_progress else nullcontext():
            count = rebuild_catalog(stage, stage / "catalog.json")
        # Validate the completed catalog before activating it.
        catalog = json.loads((stage / "catalog.json").read_text(encoding="utf-8"))
        if (not catalog and keep_products is None and keep_packages is None) or any(not (stage / entry["file"]).is_file() for entry in catalog):
            raise ValueError("Generated HELP catalog is incomplete")
        progress = report_progress("Publishing HELP", stage="publish")
        if on_progress:
            on_progress(progress)
        if on_publication:
            on_publication({"stage": stage.name, "previous": previous.name})
        if helps_dir.exists():
            helps_dir.rename(previous)
        try:
            stage.rename(helps_dir)
        except OSError:
            if previous.exists():
                previous.rename(helps_dir)
            raise
        if previous.exists():
            try:
                relocate_directory(previous, backup)
            except (OSError, ValueError):
                logging.getLogger(__name__).warning("HELP published; recovery copy remains at %s", previous, exc_info=True)
                backup = previous
            else:
                prune_backups(backup, ("help-",), backup_count)
        return {"bundles": count, "backup": str(backup) if backup.exists() else ""}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
