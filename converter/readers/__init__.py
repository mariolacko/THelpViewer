"""Format-specific help file readers."""

from __future__ import annotations

from .thelp import ThelpHelpReader, ThelpHlxSourceParser, ThelpBinaryParser, is_thelp_binary
from .fbhf import (
    FBHFHelpReader,
    FBHFSourceReader,
    FBHFSourceParser,
    FBHFBinaryParser,
    is_fbhf_binary,
    is_fbhf_source,
)
from .m602 import M602Reader, M602BinaryParser, is_m602_binary, decode_m602_bytes
from .hlx import HlxHelpReader, HlxSourceParser, detect_hlx_source_format, is_hlx_source

__all__ = [
    "ThelpHelpReader",
    "ThelpHlxSourceParser",
    "ThelpBinaryParser",
    "is_thelp_binary",
    "FBHFHelpReader",
    "FBHFSourceReader",
    "FBHFSourceParser",
    "FBHFBinaryParser",
    "is_fbhf_binary",
    "is_fbhf_source",
    "M602Reader",
    "M602BinaryParser",
    "is_m602_binary",
    "decode_m602_bytes",
    "HlxHelpReader",
    "HlxSourceParser",
    "detect_hlx_source_format",
    "is_hlx_source",
]
