"""Bundle writer — exports a whole help file as a UHF 2.0 JSON bundle."""

from __future__ import annotations

import gzip
import json
import shutil
import os
from dataclasses import dataclass
from pathlib import Path

from ..help_database import load_help_database, lookup_help_database_entry
from ..exporter import iter_help_files, load_document, select_display_encoding, fix_metadata_encoding, _clean_dir
from .json import HelpJsonRenderer
from .html import (
    GENERATOR_VERSION,
    PACKAGE_ASSET_DIR,
    SITE_ASSET_DIR_NAME,
    copy_site_assets,
)


HELPS_DIR_NAME = "helps"
CATALOG_FILENAME = "catalog.json"
DOCS_DIR_NAME = "docs"


@dataclass(frozen=True, slots=True)
class BundleResult:
    input_path: Path
    json_path: Path
    format_name: str
    topic_count: int
    display_name: str
    source_files: tuple[str, ...] = ()


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
        if isinstance(collection_name, str) and collection_name.strip():
            document.metadata["collection"] = collection_name.strip()
        if isinstance(title_override, str) and title_override.strip():
            document.metadata["title"] = title_override.strip()
        if database_entry is not None and getattr(database_entry, "help_contents_topic_id", None) is not None:
            document.metadata.setdefault("help_contents_topic_id", database_entry.help_contents_topic_id)
        if database_entry is not None and getattr(database_entry, "language", ""):
            document.metadata.setdefault("language", database_entry.language)
        renderer = HelpJsonRenderer(document, display_encoding=chosen_encoding)

        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        display_name = document.display_name
        canonical_name = database_entry.filenames[0] if database_entry and database_entry.filenames else source_path.name
        file_stem = Path(canonical_name).stem.lower() if bundle_name is None else bundle_name
        json_path = renderer.write_json_gz(target_dir / (file_stem + ".json.gz"))
        print(f"[bundle] OK: {source_path.name} → {json_path.name} ({getattr(document, 'format_name', '?')})")
        return BundleResult(
            input_path=source_path,
            json_path=json_path,
            format_name=document.format_name,
            topic_count=len(document.topics),
            display_name=display_name,
            source_files=tuple(
                getattr(database_entry, "filenames", ()) or (source_path.name,)
            ),
        )
    except Exception as e:
        import traceback
        print(f"[bundle] CHYBA: {source_path.name} — {e}")
        traceback.print_exc()
        file_stem = Path(source_path).stem.lower() if bundle_name is None else bundle_name
        return BundleResult(
            input_path=source_path,
            json_path=Path(output_dir) / (file_stem + ".json.gz"),
            format_name="ERROR",
            topic_count=0,
            display_name=source_path.stem,
            source_files=(source_path.name,),
        )


def export_bundle_tree(
    input_root: str | Path,
    output_dir: str | Path,
    encoding: str = "auto",
    clean: bool = False,
    layout: str = "site",
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
    seen_outputs: set[Path] = set()
    for path in iter_help_files(source_root):
        relative = path.relative_to(source_root)
        db_entry = lookup_help_database_entry(path, help_database)
        group_name = db_entry.collection if db_entry and db_entry.collection else str(relative.parent).replace("\\", "/")
        group_parts = tuple(part for part in Path(group_name).parts if part not in {"", "."})
        bundle_dir = helps_dir.joinpath(*group_parts) if group_parts else helps_dir
        bundle_stem = Path(db_entry.filenames[0]).stem.lower() if db_entry and db_entry.filenames else path.stem.lower()
        bundle_path = bundle_dir / f"{bundle_stem}.json.gz"
        if db_entry is not None:
            if db_entry.crc32 in seen_crc32:
                rel_bundle = bundle_path.relative_to(helps_dir)
                print(f"[bundle] SKIP DUPLIKÁT CRC32: {path.name} → {rel_bundle}")
                continue
            seen_crc32.add(db_entry.crc32)
        elif bundle_path in seen_outputs:
            rel_bundle = bundle_path.relative_to(helps_dir)
            print(f"[bundle] SKIP DUPLIKÁT: {path.name} → {rel_bundle}")
            continue
        else:
            seen_outputs.add(bundle_path)
        result = export_bundle(
            path,
            bundle_dir,
            encoding=encoding,
            bundle_name=bundle_stem,
            collection_name=db_entry.collection if db_entry else None,
            title_override=db_entry.title if db_entry else None,
            database_entry=db_entry,
        )
        results.append(result)

    # Build catalog.json in the helps/ directory.
    catalog = []
    for result in results:
        rel_path = result.json_path.relative_to(helps_dir)
        group = str(rel_path.parent) if rel_path.parent != Path(".") else ""
        source_files = list(result.source_files) if result.source_files else [result.input_path.name]
        catalog.append(
            {
                "group": group,
                "file": str(rel_path).replace("\\", "/"),
                "source_file": source_files[0],
                "source_files": source_files,
                "name": result.display_name,
                "format": result.format_name,
                "topics": result.topic_count,
            }
        )

    catalog_path = helps_dir / CATALOG_FILENAME
    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

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

    print(f"[bundle] Katalóg aktualizovaný: {catalog_path} ({len(catalog)} položiek)")
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
<link rel="stylesheet" href="{SITE_ASSET_DIR_NAME}/turbovision.css?v=20260511b">
<script defer src="{SITE_ASSET_DIR_NAME}/tv-core.js?v=20260511b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-highlight.js?v=20260506a"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-dialogs.js?v=20260506a"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-screensaver.js?v=20260506a"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-games.js?v=20260506a"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-shell.js?v=20260507b"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-bundle-app.js?v=20260511c"></script>
</head>
<body class="tv-page tv-bundle-page"
  data-tv-site-name="THelpViewer"
  data-tv-generator="THelp Viewer Converter"
  data-tv-generator-version="{GENERATOR_VERSION}"
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
