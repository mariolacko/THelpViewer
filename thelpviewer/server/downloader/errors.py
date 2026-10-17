"""Distinguish unavailable source content from non-recoverable policy failures."""

from urllib.error import HTTPError
from ..processing import UnsafeContentError


class SourceUnavailable(ValueError):
    """A source response/payload is unusable; another source may work."""


class DownloadSecurityError(UnsafeContentError):
    """A URL/peer/redirect violates policy; never bypass it through fallback."""


class SourceRateLimited(HTTPError):
    """A source exhausted this operation's bounded HTTP 429 attempts."""

    def __init__(self, url):
        super().__init__(url, 429, "Source deferred for this operation; trying alternative sources", {}, None)
