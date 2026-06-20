"""Converter package — reads legacy help files and exports HTML, JSON bundles, or Markdown."""

from __future__ import annotations

__version__ = "1.0.0"

from pathlib import Path

from .base import (
    CommentRecord,
    HelpDocument,
    HelpReaderBase,
    IndexEntry,
    TopicRecord,
    TopicTag,
)
from .readers.bw03 import BW03HelpReader, is_bw03_binary
from .readers.hlx import HlxHelpReader, HlxSourceParser, detect_hlx_source_format, is_hlx_source
from .readers.m602 import M602HelpReader, is_m602_binary
from .readers.thelp import ThelpHelpReader, is_thelp_binary
from .readers.tdh import TdhHelpReader, is_tdh_binary, is_tfh_binary
from .readers.scorpion_dat_reader import ScorpionDatReader, is_scorpion_dat_binary
from .readers.scorpion_reader import ScorpionReader, scorpion_version_hint_from_path
from .codepages import guess_display_encoding
from .exporter import (
    ExportResult,
    export_file,
    export_tree,
    load_document,
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
    "ScorpionReader",
    "ScorpionDatReader",
    "TdhHelpReader",
    "ThelpHelpReader",
    "TopicRecord",
    "TopicTag",
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
    "scorpion_version_hint_from_path",
    "is_thelp_binary",
    "is_tdh_binary",
    "is_tfh_binary",
    "load_document",
]
