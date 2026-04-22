"""Runtime configuration for the FastAPI viewer."""

from __future__ import annotations

import os
from pathlib import Path


from dataclasses import dataclass


DEFAULT_VIRTUAL_DOCS: tuple[tuple[str, str], ...] = (
    ("README.md", "README.md"),
    ("THelp Viewer/README.md", "README.md"),
    ("CHANGELOG.md", "CHANGELOG.md"),
    ("THelp Viewer/CHANGELOG.md", "CHANGELOG.md"),
)


@dataclass(slots=True)
class AppConfig:
    """Filesystem and network settings for the web app."""

    host: str
    port: int
    web_dir: Path
    index_path: Path
    assets_dir: Path
    helps_dir: Path
    docs_dir: Path
    readme_path: Path
    changelog_path: Path
    state_dir: Path
    virtual_docs: tuple[tuple[str, Path], ...]


def _resolve_virtual_doc_disk_path(disk_path: str, root: Path, readme_path: Path, changelog_path: Path) -> Path:
    normalized = disk_path.strip().replace("\\", "/")
    if normalized == "README.md":
        return readme_path
    if normalized == "CHANGELOG.md":
        return changelog_path
    path = Path(normalized)
    if path.is_absolute():
        return path
    return root / path


def _resolve_virtual_docs(root: Path, readme_path: Path, changelog_path: Path) -> tuple[tuple[str, Path], ...]:
    virtual_docs: list[tuple[str, Path]] = []
    for request_path, disk_path in DEFAULT_VIRTUAL_DOCS:
        virtual_docs.append(
            (
                request_path.strip().replace("\\", "/"),
                _resolve_virtual_doc_disk_path(disk_path, root, readme_path, changelog_path),
            )
        )
    return tuple(virtual_docs)


def load_config() -> AppConfig:
    root = Path(__file__).resolve().parents[2]
    web_dir = Path(os.environ.get("THELP_WEB_DIR", root / "www"))
    readme_path = Path(os.environ.get("THELP_README_PATH", root / "README.md"))
    changelog_path = Path(os.environ.get("THELP_CHANGELOG_PATH", root / "CHANGELOG.md"))
    return AppConfig(
        host=os.environ.get("THELP_HOST", "0.0.0.0"),
        port=int(os.environ.get("THELP_PORT", "5448")),
        web_dir=web_dir,
        index_path=Path(os.environ.get("THELP_INDEX_PATH", web_dir / "index.html")),
        assets_dir=Path(os.environ.get("THELP_ASSETS_DIR", web_dir / "assets")),
        helps_dir=Path(os.environ.get("THELP_HELPS_DIR", root / "helps")),
        docs_dir=Path(os.environ.get("THELP_DOCS_DIR", root / "docs")),
        readme_path=readme_path,
        changelog_path=changelog_path,
        state_dir=Path(os.environ.get("THELP_STATE_DIR", root / "var")),
        virtual_docs=_resolve_virtual_docs(root, readme_path, changelog_path),
    )
