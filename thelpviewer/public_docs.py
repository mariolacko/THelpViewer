"""Rules for documentation that may be published by the web viewer."""

from __future__ import annotations

from pathlib import PurePosixPath


_PRIVATE_DOC_SUFFIXES = (" audit.md", " re notes.md")


def is_public_doc_path(path: str | PurePosixPath) -> bool:
    """Return whether a Markdown path belongs in the public Docs tree."""
    normalized = str(path).replace("\\", "/").strip("/")
    if not normalized:
        return False
    name = PurePosixPath(normalized).name.casefold()
    return name.endswith(".md") and not name.endswith(_PRIVATE_DOC_SUFFIXES)
