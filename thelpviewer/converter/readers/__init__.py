"""Format-specific help file readers."""

from __future__ import annotations

from .thelp import ThelpHelpReader, ThelpBinaryParser, is_thelp_binary
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
from .hlx_binary import HlxBinaryReader, is_hlx_binary
from .ng import NGReader, is_ng_binary
from .bw03 import BW03HelpReader, is_bw03_binary
from .quickhelp import QuickHelpReader, is_quickhelp_binary
from .scorpion_dat import ScorpionDatReader, is_scorpion_dat_binary
from .software602 import Text602Reader, is_text602_binary
from .tdh import TdhHelpReader, is_tdh_binary, is_tfh_binary, probe_tdh_binary, probe_tfh_binary

__all__ = [
    "ThelpHelpReader",
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
    "HlxBinaryReader",
    "is_hlx_binary",
    "NGReader",
    "is_ng_binary",
    "BW03HelpReader",
    "is_bw03_binary",
    "QuickHelpReader",
    "is_quickhelp_binary",
    "ScorpionDatReader",
    "is_scorpion_dat_binary",
    "Text602Reader",
    "is_text602_binary",
    "TdhHelpReader",
    "is_tdh_binary",
    "is_tfh_binary",
    "probe_tdh_binary",
    "probe_tfh_binary",
]
