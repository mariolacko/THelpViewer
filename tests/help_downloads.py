"""Exercise source providers through the current shared ingestion boundary."""

from functools import partial

from thelpviewer.server.archives.core import require_extractor_tools
from thelpviewer.server.downloader.service import process_help_input


def help_processor(sources, tools=None):
    return partial(process_help_input, sources_dir=sources, extractor=tools or require_extractor_tools())
