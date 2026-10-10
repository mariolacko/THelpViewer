"""DOS sources use the shared downloader's HTTPS transport."""

from ..downloader.transport import fetch_source as fetch_dos_source

__all__ = ["fetch_dos_source"]
