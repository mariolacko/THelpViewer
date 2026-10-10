"""Generic extension types for bundle export planning."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .base import HelpDocument


@dataclass(frozen=True, slots=True)
class BundleDocumentVariant:
    bundle_stem: str
    document: HelpDocument
    source_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BundleSourceGroup:
    source_paths: tuple[Path, ...]
    bundle_stem: str
    build_document: Callable[[tuple[Path, ...], tuple[HelpDocument, ...]], HelpDocument]
    description: str = ""
