"""Runtime configuration for the FastAPI viewer."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


from dataclasses import dataclass


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    statistics_path: Path | None = None
    public_base_url: str = ""
    auth_origin: str = ""
    google_site_verification: str = ""
    midi_sources_path: Path | None = None
    dos_config_path: Path | None = None
    dev_auto_login: bool = False
    sources_dir: Path | None = None
    downloads_dir: Path | None = None
    data_dir: Path | None = None
    docs_source_dir: Path | None = None

    @property
    def persistent_dir(self) -> Path:
        # An explicitly assembled/custom-state config remains isolated (e.g. tests).
        return self.data_dir or (PROJECT_ROOT / "data" if self.state_dir == PROJECT_ROOT / "var" else self.state_dir)

    def validate_development_login(self) -> None:
        if not self.dev_auto_login:
            return
        origin = urlparse(self.auth_origin)
        if (self.public_base_url or origin.scheme != "http"
                or origin.hostname not in {"localhost", "127.0.0.1", "::1"}
                or origin.username or origin.password or origin.path or origin.query or origin.fragment):
            raise ValueError("THELP_DEV_AUTO_LOGIN requires a local HTTP auth origin and no public base URL")


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
    root = PROJECT_ROOT
    web_dir = Path(os.environ.get("THELP_WEB_DIR", root / "www"))
    readme_path = Path(os.environ.get("THELP_README_PATH", root / "README.md"))
    changelog_path = Path(os.environ.get("THELP_CHANGELOG_PATH", root / "CHANGELOG.md"))
    state_dir = Path(os.environ.get("THELP_STATE_DIR", root / "var"))
    data_dir = Path(os.environ["THELP_DATA_DIR"]) if os.environ.get("THELP_DATA_DIR") else None
    persistent = data_dir or (root / "data" if state_dir == root / "var" else state_dir)
    content_root = data_dir or root / "data"
    docs_dir = Path(os.environ.get("THELP_DOCS_DIR", content_root / "docs"))
    return AppConfig(
        host=os.environ.get("THELP_HOST", "0.0.0.0"),
        port=int(os.environ.get("THELP_PORT", "5448")),
        web_dir=web_dir,
        index_path=Path(os.environ.get("THELP_INDEX_PATH", web_dir / "index.html")),
        assets_dir=Path(os.environ.get("THELP_ASSETS_DIR", web_dir / "assets")),
        helps_dir=Path(os.environ.get("THELP_HELPS_DIR", content_root / "helps")),
        docs_dir=docs_dir,
        readme_path=readme_path,
        changelog_path=changelog_path,
        state_dir=state_dir,
        virtual_docs=_resolve_virtual_docs(root, readme_path, changelog_path),
        statistics_path=Path(os.environ.get("THELP_STATISTICS_PATH", persistent / "statistics.sqlite3")),
        public_base_url=os.environ.get("THELP_PUBLIC_BASE_URL", "").rstrip("/"),
        auth_origin=os.environ.get("THELP_AUTH_ORIGIN", f"http://localhost:{os.environ.get('THELP_PORT', '5448')}").rstrip("/"),
        google_site_verification=os.environ.get("THELP_GOOGLE_SITE_VERIFICATION", "").strip(),
        midi_sources_path=Path(os.environ.get(
            "THELP_MIDI_SOURCES_PATH", root / "thelpviewer" / "midi-sources.json"
        )),
        dos_config_path=Path(os.environ.get("THELP_DOS_CONFIG_PATH", root / "thelpviewer" / "dos-prompt.json")),
        dev_auto_login=os.environ.get("THELP_DEV_AUTO_LOGIN", "0") == "1",
        sources_dir=Path(os.environ.get("THELP_SOURCES_DIR", content_root / "sources")),
        downloads_dir=Path(os.environ.get("THELP_DOWNLOADS_DIR", state_dir / "downloads")),
        data_dir=data_dir,
        docs_source_dir=root / "docs" if docs_dir == content_root / "docs" else None,
    )
