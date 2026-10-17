"""Bundle writer — exports a whole help file as a UHF 2.0 JSON bundle."""

from __future__ import annotations

import json
import shutil
import os
from pathlib import Path

from ..results import BundleResult
from ..selection import archive_member_selected
from ..metadata import (product_metadata_for_database_entry, product_metadata_for_group,
    product_metadata_for_source, catalog_menu_name)
from ..planning import BundlePlan, bundle_stem_for_entry, build_pending_bundle_export, prefer_pending_bundle_export
from ..catalog import rebuild_catalog
from ...processing import report_progress
from ..base import HelpDocument
from .bundle_extensions import discover_bundle_source_groups, document_bundle_variants
from ..bundle_types import BundleDocumentVariant, BundleSourceGroup
from ..exporter import iter_help_files, load_document, select_display_encoding, fix_metadata_encoding, _clean_dir
from .json import HelpJsonRenderer, TRANSPORT_METADATA_KEY_LIST
from thelpviewer.help_database import (
    load_help_database,
    lookup_help_database_entry,
)
from thelpviewer.public_docs import is_public_doc_path
from thelpviewer.config import PROJECT_ROOT
from .html import (
    GENERATOR_AUTHORS,
    GENERATOR_VERSION,
    PACKAGE_ASSET_DIR,
    SITE_ASSET_DIR_NAME,
    copy_site_assets,
)


HELPS_DIR_NAME = "helps"
CATALOG_FILENAME = "catalog.json"
DOCS_DIR_NAME = "docs"


def _add_transport_metadata_keys(document: HelpDocument, keys: tuple[str, ...]) -> None:
    raw_keys = document.metadata.get(TRANSPORT_METADATA_KEY_LIST)
    transport_keys = (
        [item for item in raw_keys if isinstance(item, str)]
        if isinstance(raw_keys, (list, tuple))
        else []
    )
    for key in keys:
        if key not in transport_keys:
            transport_keys.append(key)
    document.metadata[TRANSPORT_METADATA_KEY_LIST] = transport_keys


def _source_files_with_aliases(document: HelpDocument, source_files: tuple[str, ...]) -> tuple[str, ...]:
    """Retain physical filenames and reader-verified logical database names."""
    aliases = document.metadata.get("source_file_aliases")
    values = list(source_files) + (aliases if isinstance(aliases, list) else [])
    files: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str) and value.strip() and value.strip().casefold() not in seen:
            files.append(value.strip())
            seen.add(value.strip().casefold())
    return tuple(files)


def _apply_catalog_metadata(
    document: HelpDocument,
    *,
    product: str,
    product_name: str,
    version: str,
    menu_name: str,
    source_files: tuple[str, ...],
) -> None:
    transported: list[str] = []
    for key, value in (
        ("product", product),
        ("product_name", product_name),
        ("version", version),
        ("menu_name", menu_name),
    ):
        cleaned = value.strip()
        if cleaned:
            document.metadata[key] = cleaned
            transported.append(key)

    files = [item for item in source_files if isinstance(item, str) and item.strip()]
    if files:
        document.metadata["catalog_source_files"] = files
        transported.append("catalog_source_files")

    if transported:
        _add_transport_metadata_keys(document, tuple(transported))


def export_bundle(
    source_path: str | Path,
    output_dir: str | Path,
    encoding: str = "auto",
    bundle_name: str | None = None,
    collection_name: str | None = None,
    title_override: str | None = None,
    database_entry=None,
) -> BundleResult:
    """Export one help source file into a JSON bundle file.

    Returns a :class:`BundleResult` summary.
    """
    source_path = Path(source_path)
    print(f"[bundle] Spracovávam: {source_path.name}")
    try:
        if database_entry is None:
            database_entry = lookup_help_database_entry(source_path, load_help_database())
        document = load_document(source_path)
        chosen_encoding = select_display_encoding(
            document,
            encoding=encoding,
            source_hint=str(source_path),
            source_path=source_path,
            help_database=load_help_database(),
            database_entry=database_entry,
        )
        fix_metadata_encoding(document, chosen_encoding)
        _apply_bundle_metadata(document, collection_name=collection_name,
                               title_override=title_override, database_entry=database_entry)
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        display_name = document.display_name
        file_stem = bundle_stem_for_entry(source_path, database_entry) if bundle_name is None else bundle_name
        source_files = tuple(
            getattr(database_entry, "filenames", ()) or (source_path.name,)
        )
        source_files = _source_files_with_aliases(document, source_files)
        product_key, product_name, version = product_metadata_for_database_entry(database_entry)
        menu_name = catalog_menu_name(
            display_name,
            group_name=getattr(database_entry, "collection", "") if database_entry is not None else "",
            product_name=product_name,
            version=version,
        )
        _apply_catalog_metadata(
            document,
            product=product_key,
            product_name=product_name,
            version=version,
            menu_name=menu_name if menu_name != display_name else "",
            source_files=source_files,
        )
        json_path, topic_count = _write_document_bundle(document, target_dir / (file_stem + ".json.gz"), chosen_encoding)
        print(f"[bundle] OK: {source_path.name} → {json_path.name} ({getattr(document, 'format_name', '?')})")
        return BundleResult(
            input_path=source_path,
            json_path=json_path,
            format_name=document.format_name,
            topic_count=topic_count,
            display_name=display_name,
            source_files=source_files,
            product=product_key,
            product_name=product_name,
            version=version,
        )
    except Exception as e:
        import traceback
        print(f"[bundle] CHYBA: {source_path.name} — {e}")
        traceback.print_exc()
        file_stem = Path(source_path).stem.lower() if bundle_name is None else bundle_name
        return BundleResult(
            input_path=source_path,
            json_path=Path(output_dir) / (file_stem + ".json.gz"),
            format_name="",
            error=str(e) or type(e).__name__,
            topic_count=0,
            display_name=source_path.stem,
            source_files=(source_path.name,),
        )


def _write_document_bundle(document: HelpDocument, json_path: Path, display_encoding: str) -> tuple[Path, int]:
    renderer = HelpJsonRenderer(document, display_encoding=display_encoding)
    return renderer.write_json_gz(json_path), len(renderer.topic_ids)


def _export_bundle_source_group(
    group: BundleSourceGroup,
    *,
    bundle_dir: Path,
    group_name: str,
    encoding: str,
) -> BundleResult:
    source_names = ", ".join(path.name for path in group.source_paths)
    print(f"[bundle] Spracovávam: {source_names}")
    documents = tuple(load_document(path) for path in group.source_paths)
    chosen_encoding = select_display_encoding(
        documents[0],
        encoding=encoding,
        source_hint=str(group.source_paths[0]),
        source_path=group.source_paths[0],
        help_database=load_help_database(),
        database_entry=None,
    )
    for document in documents:
        fix_metadata_encoding(document, chosen_encoding)

    document = group.build_document(group.source_paths, documents)
    product_key, product_name, version = product_metadata_for_group(group_name)
    source_files = _source_files_with_aliases(document, tuple(path.name for path in group.source_paths))
    menu_name = catalog_menu_name(
        document.display_name,
        group_name=group_name,
        product_name=product_name,
        version=version,
    )
    _apply_catalog_metadata(
        document,
        product=product_key,
        product_name=product_name,
        version=version,
        menu_name=menu_name if menu_name != document.display_name else "",
        source_files=source_files,
    )
    json_path, topic_count = _write_document_bundle(document, bundle_dir / f"{group.bundle_stem}.json.gz", chosen_encoding)
    print(f"[bundle] OK: {source_names} → {json_path.name} ({getattr(document, 'format_name', '?')})")
    return BundleResult(
        input_path=group.source_paths[0],
        json_path=json_path,
        format_name=document.format_name,
        topic_count=topic_count,
        display_name=document.display_name,
        source_files=source_files,
        product=product_key,
        product_name=product_name,
        version=version,
    )


def _apply_bundle_metadata(
    document: HelpDocument,
    *,
    collection_name: str | None,
    title_override: str | None,
    database_entry,
) -> None:
    if isinstance(collection_name, str) and collection_name.strip():
        document.metadata["collection"] = collection_name.strip()
    if isinstance(title_override, str) and title_override.strip():
        document.metadata["title"] = title_override.strip()
    if database_entry is not None and getattr(database_entry, "help_contents_topic_id", None) is not None:
        document.metadata["help_contents_topic_id"] = database_entry.help_contents_topic_id
    if database_entry is not None and getattr(database_entry, "language", ""):
        document.metadata["language"] = database_entry.language


def _export_pending_bundle_variants(
    pending: BundlePlan,
    *,
    encoding: str,
) -> list[BundleResult]:
    source_path = pending.source_path
    print(f"[bundle] Spracovávam: {source_path.name}")
    try:
        document = load_document(source_path)
        chosen_encoding = select_display_encoding(
            document,
            encoding=encoding,
            source_hint=str(source_path),
            source_path=source_path,
            help_database=load_help_database(),
            database_entry=pending.database_entry,
        )
        fix_metadata_encoding(document, chosen_encoding)
        db_entry = pending.database_entry
        _apply_bundle_metadata(
            document,
            collection_name=db_entry.collection if db_entry else None,
            title_override=db_entry.title if db_entry else None,
            database_entry=db_entry,
        )

        variants = document_bundle_variants(document) or [
            BundleDocumentVariant(bundle_stem=pending.bundle_stem, document=document)
        ]
        results: list[BundleResult] = []
        product_key, product_name, version = product_metadata_for_source(
            source_path, pending.group_name, db_entry,
        )
        for variant in variants:
            variant_document = variant.document
            source_files = variant.source_files or tuple(getattr(db_entry, "filenames", ()) or (source_path.name,))
            source_files = _source_files_with_aliases(variant_document, source_files)
            menu_name = catalog_menu_name(
                variant_document.display_name,
                group_name=pending.group_name,
                product_name=product_name,
                version=version,
            )
            _apply_catalog_metadata(
                variant_document,
                product=product_key,
                product_name=product_name,
                version=version,
                menu_name=menu_name if menu_name != variant_document.display_name else "",
                source_files=source_files,
            )
            json_path, topic_count = _write_document_bundle(
                variant_document,
                pending.bundle_dir / f"{variant.bundle_stem}.json.gz",
                chosen_encoding,
            )
            print(
                f"[bundle] OK: {source_path.name} → {json_path.name} "
                f"({getattr(variant_document, 'format_name', '?')})"
            )
            results.append(
                BundleResult(
                    input_path=source_path,
                    json_path=json_path,
                    format_name=variant_document.format_name,
                    topic_count=topic_count,
                    display_name=variant_document.display_name,
                    source_files=source_files,
                    product=product_key,
                    product_name=product_name,
                    version=version,
                )
            )
        return results
    except Exception as e:
        import traceback
        print(f"[bundle] CHYBA: {source_path.name} — {e}")
        traceback.print_exc()
        return [
            BundleResult(
                input_path=source_path,
                json_path=pending.bundle_path,
                format_name="",
                error=str(e) or type(e).__name__,
                topic_count=0,
                display_name=source_path.stem,
                source_files=(source_path.name,),
                product=product_metadata_for_group(pending.group_name)[0],
                product_name=product_metadata_for_group(pending.group_name)[1],
                version=product_metadata_for_group(pending.group_name)[2],
            )
        ]


def export_bundle_tree(
    input_root: str | Path,
    output_dir: str | Path,
    encoding: str = "auto",
    clean: bool = False,
    layout: str = "site",
    *,
    source_paths: list[Path] | None = None,
    on_progress=None,
    include_catalog=True,
) -> list[BundleResult]:
    """Export all help files under *input_root* as JSON bundles."""
    source_root = Path(input_root)
    target_dir = Path(output_dir)
    if layout not in {"site", "helps"}:
        raise ValueError("layout must be 'site' or 'helps'")

    if clean and target_dir.exists():
        _clean_dir(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    helps_dir = target_dir / HELPS_DIR_NAME if layout == "site" else target_dir
    helps_dir.mkdir(parents=True, exist_ok=True)

    help_database = load_help_database()
    results: list[BundleResult] = []
    seen_crc32: set[int] = set()
    topic_count_cache: dict[Path, int] = {}
    pending_exports: dict[Path, BundlePlan] = {}
    help_paths = iter_help_files(source_root) if source_paths is None else source_paths
    if any(not path.is_relative_to(source_root) for path in help_paths):
        raise ValueError("Selected HELP paths must be inside the source root")
    help_paths = [path for path in help_paths
                  if archive_member_selected(path, lookup_help_database_entry(path, help_database))]
    source_groups = discover_bundle_source_groups(help_paths)
    grouped_source_members = {
        path
        for group in source_groups
        for path in group.source_paths
    }

    for path in help_paths:
        if path in grouped_source_members:
            continue
        db_entry = lookup_help_database_entry(path, help_database)
        pending = build_pending_bundle_export(
            path,
            source_root=source_root,
            helps_dir=helps_dir,
            database_entry=db_entry,
        )
        if db_entry is not None:
            if db_entry.crc32 in seen_crc32:
                rel_bundle = pending.bundle_path.relative_to(helps_dir)
                print(f"[bundle] SKIP DUPLIKÁT CRC32: {path.name} → {rel_bundle}")
                continue
            seen_crc32.add(db_entry.crc32)
        existing = pending_exports.get(pending.bundle_path)
        if existing is not None and not prefer_pending_bundle_export(
            existing,
            pending,
            topic_count_cache=topic_count_cache,
        ):
            rel_bundle = pending.bundle_path.relative_to(helps_dir)
            print(f"[bundle] SKIP KOLÍZIU: {path.name} → {rel_bundle}")
            continue
        pending_exports[pending.bundle_path] = pending

    total_exports = len(pending_exports) + len(source_groups)
    processed = 0
    for pending in pending_exports.values():
        progress = report_progress("Converting", pending.source_path.name,
                                   stage="convert", processed=processed, total=total_exports)
        if on_progress:
            on_progress(progress)
        results.extend(_export_pending_bundle_variants(pending, encoding=encoding))
        processed += 1
    for group in source_groups:
        progress = report_progress("Converting", group.source_paths[0].name,
                                   stage="convert", processed=processed, total=total_exports)
        if on_progress:
            on_progress(progress)
        processed += 1
        try:
            first_pending = build_pending_bundle_export(
                group.source_paths[0],
                source_root=source_root,
                helps_dir=helps_dir,
                database_entry=lookup_help_database_entry(group.source_paths[0], help_database),
            )
            results.append(
                _export_bundle_source_group(
                    group,
                    bundle_dir=first_pending.bundle_dir,
                    group_name=first_pending.group_name,
                    encoding=encoding,
                )
            )
        except Exception as e:
            import traceback
            description = group.description or group.bundle_stem
            print(f"[bundle] CHYBA: {description} — {e}")
            traceback.print_exc()
            results.append(
                BundleResult(
                    input_path=group.source_paths[0],
                    json_path=helps_dir
                    / group.source_paths[0].parent.relative_to(source_root)
                    / f"{group.bundle_stem}.json.gz",
                    format_name="",
                    error=str(e) or type(e).__name__,
                    topic_count=0,
                    display_name=description,
                    source_files=tuple(path.name for path in group.source_paths),
                    product=product_metadata_for_group(str(group.source_paths[0].parent.relative_to(source_root)))[0],
                    product_name=product_metadata_for_group(str(group.source_paths[0].parent.relative_to(source_root)))[1],
                    version=product_metadata_for_group(str(group.source_paths[0].parent.relative_to(source_root)))[2],
                )
            )

    progress = report_progress("Converting", stage="convert", processed=processed, total=total_exports)
    if on_progress:
        on_progress(progress)
    catalog_path = helps_dir / CATALOG_FILENAME
    count = rebuild_catalog(helps_dir, catalog_path) if include_catalog else len(results)

    # No cross-bundle index annotation: do not add `source_file` to
    # index entries and do not attempt to invent external links here.
    # Leave index entries exactly as produced by the reader/renderer.

    if layout == "site":
        # Copy shared assets and write the SPA index page.
        copy_site_assets(target_dir)
        _write_bundle_index(target_dir)

        # Copy documentation Markdown files if a docs/ sibling exists.
        docs_source = source_root.parent / "docs"
        if docs_source.is_dir():
            _copy_docs(docs_source, target_dir / DOCS_DIR_NAME,
                        readme=source_root.parent / "README.md")

    print(f"[bundle] Katalóg aktualizovaný: {catalog_path} ({count} položiek)")
    return results


def _copy_docs(docs_source: Path, docs_target: Path, *,
               readme: Path | None = None) -> None:
    """Copy Markdown documentation files and build a docs catalog."""
    if docs_target.exists():
        _clean_dir(docs_target)
    docs_target.mkdir(parents=True, exist_ok=True)

    catalog = []

    # Copy root README.md first (if provided and exists).
    if readme and readme.is_file():
        dest = docs_target / readme.name
        shutil.copy2(readme, dest)
        catalog.append({"file": readme.name, "name": readme.stem})

    for md_path in sorted(docs_source.rglob("*.md")):
        rel = md_path.relative_to(docs_source)
        if not is_public_doc_path(rel):
            continue
        dest = docs_target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md_path, dest)
        entry: dict = {
            "file": str(rel).replace("\\", "/"),
            "name": md_path.stem,
        }
        group_parts = list(rel.parent.parts)
        if group_parts:
            entry["group"] = " / ".join(group_parts)
        catalog.append(entry)

    catalog_path = docs_target / CATALOG_FILENAME
    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_bundle_index(target_dir: Path) -> None:
    """Write the single-page viewer ``index.html`` into *target_dir*."""
    bundle_app_js = PACKAGE_ASSET_DIR / "tv-bundle-app.js"
    if bundle_app_js.is_file():
        dest = Path(target_dir) / SITE_ASSET_DIR_NAME / "tv-bundle-app.js"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundle_app_js, dest)
    site_image = PROJECT_ROOT / "Thelp.png"
    if site_image.is_file():
        dest = Path(target_dir) / SITE_ASSET_DIR_NAME / "Thelp.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(site_image, dest)

    index_html = _render_bundle_index_html()
    (target_dir / "index.html").write_text(index_html, encoding="utf-8")


def _render_bundle_index_html() -> str:
    """Return the full HTML for the single-page bundle viewer."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>THelpViewer — TurboVision-style Help File Viewer</title>
<meta name="description" content="TurboVision-style web viewer for UHF2 help bundles. Browse converted help files in a retro DOS-like interface.">
<meta name="keywords" content="THelp, TurboVision, UHF2, help file viewer, retro DOS">
<meta name="author" content="THelpViewer">
<meta property="og:title" content="THelpViewer — TurboVision-style Help File Viewer">
<meta property="og:description" content="TurboVision-style web viewer for UHF2 help bundles. Browse converted help files in a retro DOS-like interface.">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE_ASSET_DIR_NAME}/Thelp.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="THelpViewer — TurboVision-style Help File Viewer">
<meta name="twitter:description" content="TurboVision-style web viewer for UHF2 help bundles.">
<meta name="twitter:image" content="{SITE_ASSET_DIR_NAME}/Thelp.png">
<meta name="theme-color" content="#000080">
<meta name="GENERATOR" content="THelp Viewer Converter {GENERATOR_VERSION}">
<link rel="icon" type="image/svg+xml" href="{SITE_ASSET_DIR_NAME}/thelp-icon.svg">
<link rel="stylesheet" href="{SITE_ASSET_DIR_NAME}/turbovision.css?v=20261015c">
<script defer src="{SITE_ASSET_DIR_NAME}/tv-core.js?v=20261015e"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-context-help.js?v=20261017b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-highlight.js?v=20261010b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-dialogs.js?v=20261016t"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-content.js?v=20261016g"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-screensaver.js?v=20261010b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-games.js?v=20261010b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-shell.js?v=20261017b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-dos.js?v=20261017a"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-bundle-app.js?v=20261016w"></script>
</head>
<body class="tv-page tv-bundle-page"
  data-tv-site-name="THelpViewer"
  data-tv-generator="THelp Viewer Converter"
  data-tv-generator-version="{GENERATOR_VERSION}"
  data-tv-authors="{GENERATOR_AUTHORS}"
  data-tv-page-kind="bundle-index">
<div class="tv-app">
<header class="tv-menu-bar" data-tv-menu-bar></header>
<div class="tv-desktop" data-tv-bundle-desktop>
<pre class="tv-desktop-pattern" data-tv-desktop-pattern="░" aria-hidden="true"></pre>
</div>
<footer class="tv-status-line" data-tv-status-line></footer>
</div>
</body>
</html>
"""
