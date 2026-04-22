"""Converter package — reads legacy help files and exports HTML, JSON bundles, or Markdown."""

from __future__ import annotations

__version__ = "1.0.0"

from pathlib import Path

from .base import CommentRecord, HelpDocument, HelpReaderBase, IndexEntry, TopicRecord
from .readers.bw03 import BW03HelpReader, is_bw03_binary
from .readers.hlx import HlxHelpReader, HlxSourceParser, detect_hlx_source_format, is_hlx_source
from .readers.m602 import M602HelpReader, is_m602_binary
from .readers.thelp import ThelpHelpReader, is_thelp_binary
from .readers.scorpion_dat import ScorpionDatReader, is_scorpion_dat_binary
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
from .writers.json import HelpJsonRenderer
from .writers.bundle import BundleResult, export_bundle, export_bundle_tree
from .writers.md import HelpMarkdownRenderer


__all__ = [
    "BundleResult",
    "CommentRecord",
    "ExportResult",
    "BW03HelpReader",
    "FBHFHelpReader",
    "FBHFSourceParser",
    "FBHFSourceReader",
    "HelpDocument",
    "HelpHtmlRenderer",
    "HelpJsonRenderer",
    "HelpMarkdownRenderer",
    "HelpReaderBase",
    "HlxHelpReader",
    "HlxSourceParser",
    "IndexEntry",
    "M602HelpReader",
    "ScorpionDatReader",
    "ThelpHelpReader",
    "TopicRecord",
    "detect_hlx_source_format",
    "export_bundle",
    "export_bundle_tree",
    "export_file",
    "export_tree",
    "guess_display_encoding",
    "is_bw03_binary",
    "is_fbhf_binary",
    "is_fbhf_source",
    "is_hlx_source",
    "is_m602_binary",
    "is_scorpion_dat_binary",
    "is_thelp_binary",
    "load_binary_document",
    "load_document",
]
