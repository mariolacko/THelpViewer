"""Compatibility re-exports for the refactored downloader package."""

from __future__ import annotations

from .collector import (
    HELP_EXTENSIONS,
    SKIP_HELP_NAMES,
    WINHELP_MAGIC,
    collect_help_files,
    copy_help_files,
    detect_language,
    is_help_file_path,
    is_winhelp,
)
from .extractor import (
    ExtractorTools,
    collect_from_archive,
    extract_file,
    extract_nested,
    find_lsar,
    find_unar,
    probe_extractable,
    require_extractor_tools,
)
from .http import (
    DOWNLOAD_DELAY,
    REQUEST_DELAY,
    download_file,
    fetch_html,
    fetch_json,
    fetch_polite,
    get_opener,
    parse_anchors,
)

__all__ = [
    "DOWNLOAD_DELAY",
    "ExtractorTools",
    "HELP_EXTENSIONS",
    "REQUEST_DELAY",
    "SKIP_HELP_NAMES",
    "WINHELP_MAGIC",
    "collect_from_archive",
    "collect_help_files",
    "copy_help_files",
    "detect_language",
    "download_file",
    "extract_file",
    "extract_nested",
    "fetch_html",
    "fetch_json",
    "fetch_polite",
    "find_lsar",
    "find_unar",
    "get_opener",
    "is_help_file_path",
    "is_winhelp",
    "parse_anchors",
    "probe_extractable",
    "require_extractor_tools",
]
