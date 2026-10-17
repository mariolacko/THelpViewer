"""Ordered source attempts, with domain-owned validation and site-limit scope."""

from urllib.error import HTTPError, URLError

from .errors import SourceUnavailable
from ..processing import UnsafeContentError
from .transport import defer_limited_sources

SOURCE_ERRORS = (HTTPError, URLError, TimeoutError, ConnectionError, SourceUnavailable)


def try_sources(candidates, attempt, *, complete=lambda _value: True,
                on_attempt=None, on_failure=None, limited_sources=None, errors=SOURCE_ERRORS):
    """Return the first accepted result, or None after exhausting candidates.

    Callers decide when a result is complete (e.g. CRC-verified HELP components).
    Retries/countdowns belong to transport; this loop never repeats a request or
    bypasses security failures. A supplied set shares exhausted sites across jobs.
    """
    with defer_limited_sources(limited_sources if limited_sources is not None else set()):
        for index, candidate in enumerate(candidates):
            if on_attempt:
                on_attempt(index, candidate)
            try:
                value = attempt(candidate)
            except UnsafeContentError:
                raise
            except errors as error:
                try:
                    if on_failure:
                        on_failure(candidate, error)
                finally:
                    if isinstance(error, HTTPError):
                        error.close()
                continue
            if complete(value):
                return value
    return None
