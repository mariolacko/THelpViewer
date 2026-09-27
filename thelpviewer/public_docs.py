"""Rules for documentation that may be published by the web viewer."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


_PRIVATE_DOC_SUFFIXES = (" audit.md", " re.md", " re notes.md")
_PRIVATE_DOC_NAMES = {"audit.md", "re.md", "re notes.md"}


def is_public_doc_path(path: str | PurePosixPath) -> bool:
    """Return whether a Markdown path belongs in the public Docs tree."""
    normalized = str(path).replace("\\", "/").strip("/")
    if not normalized:
        return False
    name = PurePosixPath(normalized).name.casefold()
    return (name.endswith(".md") and name not in _PRIVATE_DOC_NAMES
            and not name.endswith(_PRIVATE_DOC_SUFFIXES))


def public_doc_sources(docs_dir: Path,
                       virtual_docs: tuple[tuple[str, Path], ...] = ()) -> dict[str, Path]:
    """Resolve only Markdown documents exposed by the public Docs route."""
    sources = {
        request_path: disk_path
        for request_path, disk_path in virtual_docs
        if is_public_doc_path(request_path) and disk_path.is_file()
    }
    if docs_dir.is_dir():
        root = docs_dir.resolve()
        for path in sorted(docs_dir.rglob("*.md")):
            relative = path.relative_to(docs_dir).as_posix()
            if (relative not in sources and is_public_doc_path(relative)
                    and path.resolve().is_relative_to(root) and path.is_file()):
                sources[relative] = path
    return sources
