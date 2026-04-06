"""Converter package — reads legacy help files and exports HTML, JS bundles, or Markdown."""

from __future__ import annotations

__version__ = "1.0.0"

from pathlib import Path

from .base import CommentRecord, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from .readers.hlx import HlxHelpReader, HlxSourceParser, detect_hlx_source_format, is_hlx_source
from .readers.m602 import M602HelpReader, is_m602_binary
from .readers.thelp import ThelpHelpReader, ThelpHlxSourceParser, is_thelp_binary
from .codepages import guess_display_encoding
from .exporter import (
    ExportResult,
    export_file,
    export_tree,
    load_document,
    load_binary_document,
)
from .readers.fbhf import FBHFHelpReader, FBHFSourceParser, FBHFSourceReader, is_fbhf_binary, is_fbhf_source
from .writers.html import HelpHtmlRenderer
from .writers.bundle import BundleResult, export_bundle, export_bundle_tree
from .writers.md import HelpMarkdownRenderer


__all__ = [
    "BundleResult",
    "CommentRecord",
    "ExportResult",
    "FBHFHelpReader",
    "FBHFSourceParser",
    "FBHFSourceReader",
    "HelpDocument",
    "HelpHtmlRenderer",
    "HelpMarkdownRenderer",
    "HelpReaderBase",
    "HlxHelpReader",
    "HlxSourceParser",
    "IndexEntry",
    "M602HelpReader",
    "ThelpHelpReader",
    "ThelpHlxSourceParser",
    "TopicRecord",
    "detect_hlx_source_format",
    "export_bundle",
    "export_bundle_tree",
    "export_file",
    "export_tree",
    "guess_display_encoding",
    "is_fbhf_binary",
    "is_fbhf_source",
    "is_hlx_source",
    "is_m602_binary",
    "is_thelp_binary",
    "load_binary_document",
    "load_document",
]
