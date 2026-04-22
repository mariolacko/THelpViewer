"""Compatibility wrapper: downloader extraction now uses ``unar`` directly."""

from __future__ import annotations

from pathlib import Path

from .extractor import ExtractorTools, extract_file, find_unar, require_extractor_tools


def find_unrar() -> str | None:
    """Backward-compatible alias returning the ``unar`` executable."""
    return find_unar()


def require_unrar(dry_run: bool = False) -> str | None:
    """Backward-compatible alias returning the ``unar`` executable."""
    return require_extractor_tools(dry_run=dry_run).unar


def run_unrar(archive: Path, dest: Path, unrar: str) -> bool:
    """Backward-compatible wrapper around the new ``unar`` extractor."""
    return extract_file(archive, dest, ExtractorTools(unar=unrar, lsar=None))
