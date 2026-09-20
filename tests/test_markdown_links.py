from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote

from thelpviewer.public_docs import is_public_doc_path


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def test_public_markdown_links_resolve_to_public_files():
    repo_root = Path(__file__).resolve().parents[1]
    sources = [repo_root / "README.md", repo_root / "CHANGELOG.md"]
    sources.extend(
        path
        for path in (repo_root / "docs").rglob("*.md")
        if is_public_doc_path(path.relative_to(repo_root / "docs"))
    )
    failures: list[str] = []

    for source in sources:
        markdown = source.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(markdown):
            href = match.group(1).strip()
            if href.startswith("<") and href.endswith(">"):
                href = href[1:-1]
            href = href.split(maxsplit=1)[0]
            if not href or href.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
                continue
            relative = unquote(href.split("#", 1)[0].split("?", 1)[0])
            target = (source.parent / relative).resolve()
            if not target.is_file():
                failures.append(f"{source.relative_to(repo_root)} -> missing {href}")
                continue
            if target.suffix.casefold() == ".md" and not is_public_doc_path(target.name):
                failures.append(f"{source.relative_to(repo_root)} -> private {href}")

    assert failures == []
