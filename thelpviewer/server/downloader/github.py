"""GitHub provider for public repository file trees."""

from __future__ import annotations

from pathlib import Path

from ..processing import UnsafeContentError
from .errors import SourceRateLimited
from .catalog import products_for_source
from ..converter.sources import is_help_file_path
from ..converter.ingest import HelpInput
from .http import fetch_json
from ..processing import report_progress


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
    dl_dir: Path,
    dry_run: bool,
    process,
    *,
    complete=None,
) -> list[Path]:
    """Run the GitHub provider for selected logical products."""
    all_collected: list[Path] = []

    for product in products_for_source(SOURCE_NAME, product_keys):
        if complete and complete():
            break
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
        except SourceRateLimited:
            raise
        except UnsafeContentError:
            raise
        except Exception as exc:
            print(f"  [error] {exc}")
            report_progress("Source warning", warning=str(exc))
            continue

        if not files:
            print("  [error] No files found.")
            report_progress("Source warning", warning=f"No files found for {product.label}")
            continue


        for entry in files:
            if complete and complete():
                break
            name = entry["name"]
            url = entry["download_url"]
            print(f"  File: {name}")
            if dry_run:
                print(f"    [dry-run] {url}")
                continue

            path = dl_dir / name
            try:
                all_collected.extend(process(HelpInput(path, product.label,
                    direct=is_help_file_path(Path(name))), url=url))
            except (SourceRateLimited, UnsafeContentError):
                raise
            except Exception as exc:
                report_progress("Source warning", warning=str(exc))

    return all_collected
