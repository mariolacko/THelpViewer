"""GitHub provider for public repository file trees."""

from __future__ import annotations

from pathlib import Path

from .catalog import products_for_source
from .collector import HELP_EXTENSIONS
from .extractor import ExtractorTools, collect_from_archive
from .http import download_file, fetch_json


SOURCE_NAME = "github"


def list_repo_files(api_url: str) -> list[dict[str, str]]:
    """Return GitHub Contents API file entries for one directory."""
    payload = fetch_json(api_url)
    if not isinstance(payload, list):
        return []
    files: list[dict[str, str]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "file":
            continue
        name = str(entry.get("name") or "").strip()
        download_url = str(entry.get("download_url") or "").strip()
        html_url = str(entry.get("html_url") or "").strip()
        if not name or not download_url:
            continue
        files.append(
            {
                "name": name,
                "download_url": download_url,
                "html_url": html_url,
            }
        )
    return files


def run(
    product_keys: list[str],
    sources_dir: Path,
    dl_dir: Path,
    dry_run: bool,
    extractor: ExtractorTools,
) -> list[Path]:
    """Run the GitHub provider for selected logical products."""
    all_collected: list[Path] = []

    for product in products_for_source(SOURCE_NAME, product_keys):
        source_query = product.sources[SOURCE_NAME]
        if not source_query.api_url:
            continue

        print(f"\n{'=' * 60}")
        print(f"[github] {product.label}")
        print(f"Search: {source_query.search_text}")
        if source_query.direct_urls:
            print(f"Repo:   {source_query.direct_urls[0]}")
        print("=" * 60)

        try:
            files = list_repo_files(source_query.api_url)
        except Exception as exc:
            print(f"  [error] {exc}")
            continue

        if not files:
            print("  [error] No files found.")
            continue

        target_dir = sources_dir / product.label
        target_dir.mkdir(parents=True, exist_ok=True)

        for entry in files:
            name = entry["name"]
            url = entry["download_url"]
            ext = Path(name).suffix.lower()
            print(f"  File: {name}")
            if dry_run:
                print(f"    [dry-run] {url}")
                continue

            if ext in HELP_EXTENSIONS:
                final_dest = target_dir / name.upper()
                temp_dest = dl_dir / name
                if final_dest.exists():
                    print(f"    [skipped] {final_dest.name} (exists)")
                    continue
                try:
                    download_file(url, temp_dest)
                    final_dest.parent.mkdir(parents=True, exist_ok=True)
                    temp_dest.replace(final_dest)
                    print(f"    ✓ {final_dest.relative_to(sources_dir)}")
                    all_collected.append(final_dest)
                except Exception as exc:
                    print(f"    [error] {exc}")
                continue

            archive_path = dl_dir / name
            try:
                download_file(url, archive_path)
            except Exception as exc:
                print(f"    [error] {exc}")
                continue

            result = collect_from_archive(archive_path, product.label, sources_dir, extractor)
            all_collected.extend(result)
            if not result:
                print("    No help files found.")

    return all_collected
