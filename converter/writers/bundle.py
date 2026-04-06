"""JS bundle writer — exports a whole help file as one compressed .json.gz bundle."""

from __future__ import annotations

import gzip
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .html import (
    GENERATOR_VERSION,
    HelpHtmlRenderer,
    PACKAGE_ASSET_DIR,
    SITE_ASSET_DIR_NAME,
    copy_site_assets,
)
from ..exporter import (
    _clean_dir,
    fix_metadata_encoding,
    iter_help_files,
    load_document,
    select_display_encoding,
)


HELPS_DIR_NAME = "helps"
DOCS_DIR_NAME = "docs"
CATALOG_FILENAME = "catalog.json"

# Mapping of source file stems (uppercase) to human-friendly bundle names.
BUNDLE_DISPLAY_NAMES: dict[str, str] = {
    # Turbo Pascal variants
    "TURBO4": "Turbo Pascal 4",
    "TURBO": "Turbo Pascal 6",
    "TURBO5": "Turbo Pascal 5",
    "TURBO5DE": "Turbo Pascal 5 DE",
    "TURBO6": "Turbo Pascal 6",
    "TURBO7": "Turbo Pascal 7",
    "TURBO7CZ": "Turbo Pascal 7 CZ",
    "TURBODE": "Turbo Pascal DE",
    "DEMOHELP": "Demo Help TP6",
    "DEMOHELP_BP7": "Demo Help BP7",
    # TVISION/OWL/WINDOWS
    "TVISION": "Turbo Vision",
    "OWL": "ObjectWindows Library",
    "WINDOWS": "Windows API",
    # Turbo C
    "TCHELP": "Turbo C Help",
    "TCWHELP": "Turbo C for Windows",
    # Others
    "SHED": "Resource Workshop",
    "SK2": "Sidekick 2",
    "C602_152": "Calc 602",
    "K602_10": "Kalk 602",
    "M602_200": "Manager 602",
    "T602_301": "Text 602",
    "MCISTRWH": "MCI String Help",
    "PENAPIWH": "Pen API Help",
}

def bundle_display_name(source_stem: str, source_path: Path | None = None, document: object | None = None) -> str:
    """Return a human-friendly name for a help bundle.

    Uses description from document metadata if available and ASCII-safe,
    then infers Turbo Pascal version from format_version, falls back to
    BUNDLE_DISPLAY_NAMES mapping, then to source_stem.
    """
    if document is not None:
        meta = getattr(document, "metadata", None) or {}
        desc = meta.get("description")
        if desc and isinstance(desc, str):
            return desc

        # For TURBO stem without usable description, infer from format_version
        stem = source_stem.upper()
        if stem == "TURBO":
            fv = meta.get("format_version")
            if fv is not None:
                if fv <= 3:
                    return "Turbo Pascal 4"
                if fv == 4:
                    return "Turbo Pascal 5"
                if fv == 51:
                    return "Turbo Pascal 6"
                if fv >= 52:
                    return "Borland Pascal 7"

    stem = source_stem.upper()

    if stem in BUNDLE_DISPLAY_NAMES:
        return BUNDLE_DISPLAY_NAMES[stem]

    return source_stem


@dataclass(slots=True)
class BundleResult:
    """Summary of one help file exported as a JSON bundle."""

    input_path: Path
    json_path: Path
    format_name: str
    topic_count: int
    display_name: str = ""


def export_bundle(
    input_path: str | Path,
    output_dir: str | Path,
    encoding: str = "auto",
    bundle_name: str | None = None,
) -> BundleResult:
    """Export one help file as a gzipped JSON bundle for the single-page viewer."""
    source_path = Path(input_path)
    print(f"[bundle] Spracovávam: {source_path.name}")
    try:
        document = load_document(source_path)
        chosen_encoding = select_display_encoding(
            document, encoding=encoding, source_hint=str(source_path)
        )
        fix_metadata_encoding(document, chosen_encoding)
        renderer = HelpHtmlRenderer(document, display_encoding=chosen_encoding)
        bundle = renderer.render_json_bundle()

        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        display_name = bundle_display_name(source_path.stem, document=document)
        file_stem = source_path.stem.lower() if bundle_name is None else bundle_name
        gz_path = target_dir / (file_stem + ".json.gz")
        json_payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
        json_bytes = json_payload.encode("utf-8")
        compressed = gzip.compress(json_bytes, compresslevel=9)
        gz_path.write_bytes(compressed)
        print(f"[bundle] OK: {source_path.name} → {gz_path.name} ({getattr(document, 'format_name', '?')})")
        return BundleResult(
            input_path=source_path,
            json_path=gz_path,
            format_name=document.format_name,
            topic_count=len(document.topics),
            display_name=display_name,
        )
    except Exception as e:
        print(f"[bundle] CHYBA: {source_path.name} — {e}")
        file_stem = source_path.stem.lower() if bundle_name is None else bundle_name
        return BundleResult(
            input_path=source_path,
            json_path=Path(output_dir) / (file_stem + ".json.gz"),
            format_name="ERROR",
            topic_count=0,
            display_name=bundle_display_name(source_path.stem),
        )


def export_bundle_tree(
    input_root: str | Path,
    output_dir: str | Path,
    encoding: str = "auto",
    clean: bool = False,
) -> list[BundleResult]:
    """Export all help files under *input_root* as JSON bundles plus a viewer."""
    source_root = Path(input_root)
    target_dir = Path(output_dir)

    if clean and target_dir.exists():
        _clean_dir(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    helps_dir = target_dir / HELPS_DIR_NAME
    helps_dir.mkdir(parents=True, exist_ok=True)

    results: list[BundleResult] = []
    for path in iter_help_files(source_root):
        relative = path.relative_to(source_root)
        group_parts = relative.parent.parts
        bundle_dir = helps_dir.joinpath(*group_parts) if group_parts else helps_dir
        result = export_bundle(
            path, bundle_dir, encoding=encoding,
        )
        results.append(result)

    # Build catalog.json in the helps/ directory.
    catalog = []
    for result in results:
        rel_path = result.json_path.relative_to(helps_dir)
        group = str(rel_path.parent) if rel_path.parent != Path(".") else ""
        catalog.append(
            {
                "group": group,
                "file": str(rel_path).replace("\\", "/"),
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

    # Copy shared assets and write the SPA index page.
    copy_site_assets(target_dir)
    _write_bundle_index(target_dir)

    # Copy documentation Markdown files if a docs/ sibling exists.
    docs_source = source_root.parent / "docs"
    if docs_source.is_dir():
        _copy_docs(docs_source, target_dir / DOCS_DIR_NAME,
                    readme=source_root.parent / "README.md")

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
<meta name="description" content="TurboVision-style web viewer for Borland and Software602 help files. Browse Turbo Pascal, Borland C++ and Text602/M602 help in a retro DOS-like interface.">
<meta name="keywords" content="THelp, TurboVision, Borland, Software602, help file viewer, Turbo Pascal, retro DOS">
<meta name="author" content="THelpViewer">
<meta property="og:title" content="THelpViewer — TurboVision-style Help File Viewer">
<meta property="og:description" content="TurboVision-style web viewer for Borland and Software602 help files. Browse Turbo Pascal, Borland C++ and Text602/M602 help in a retro DOS-like interface.">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE_ASSET_DIR_NAME}/Thelp.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="THelpViewer — TurboVision-style Help File Viewer">
<meta name="twitter:description" content="TurboVision-style web viewer for Borland and Software602 help files.">
<meta name="twitter:image" content="{SITE_ASSET_DIR_NAME}/Thelp.png">
<meta name="theme-color" content="#000080">
<meta name="GENERATOR" content="THelp Viewer Converter {GENERATOR_VERSION}">
<link rel="stylesheet" href="{SITE_ASSET_DIR_NAME}/turbovision.css">
<script defer src="{SITE_ASSET_DIR_NAME}/tv-core.js"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-highlight.js"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-dialogs.js"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-screensaver.js"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-games.js"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-shell.js"></script>
<script defer src="{SITE_ASSET_DIR_NAME}/tv-bundle-app.js"></script>
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
