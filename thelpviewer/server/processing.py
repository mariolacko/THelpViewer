"""Operation progress and policy errors shared by transfers and local processing."""

from contextlib import contextmanager
from contextvars import ContextVar


class UnsafeContentError(ValueError):
    """Content violates a safety boundary; a fallback must not bypass it."""


_observer = ContextVar("processing_progress", default=None)


@contextmanager
def observe_progress(callback):
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def stage_progress(stage, *, received=0, bytes_total=0, processed=0, total=0):
    """A phase-local percentage, never an estimate of the complete operation."""
    numerator, denominator = (received, bytes_total) if stage == "download" else (processed, total)
    percent = max(0, min(100, int(100 * numerator / denominator))) if denominator > 0 else None
    return {"stage": stage, "stage_percent": percent}


def report_progress(phase, filename="", *, stage="prepare", **values):
    event = {"phase": phase, "file": filename, "received": 0, "bytes_total": 0,
             **stage_progress(stage, **{key: values[key] for key in ("received", "bytes_total", "processed", "total")
                                       if key in values}), **values}
    callback = _observer.get()
    if callback:
        callback(event)
    return event
