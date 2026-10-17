"""Recursive container discovery with caller-owned leaf selection."""

from .core import DEFAULT_LIMITS, ExtractionError, extract_file, probe_extractable, validate_tree
from .containers import assemble_borland_split_archives, _is_borland_split_part


def _should_probe(path):
    return not _is_borland_split_part(path)


def extract_nested(work_dir, tools, *, skip=None, complete=None, prefer=None, limits=DEFAULT_LIMITS):
    seen = set()
    def ordered(paths):
        # Completed split streams can contain every requested HELP component.
        # Try them before unrelated example/source ZIPs from the same installer.
        return sorted(paths, key=lambda path: (path.parent.name != "__assembled_split_archives",
                                               not prefer(path) if prefer else False, path))
    def visit(root, depth):
        # A member-selecting consumer can stop descending once the enclosing
        # archive yielded its requested inputs; sibling containers still run.
        if complete and complete():
            return
        assemble_borland_split_archives(root, limits=limits)
        paths = ordered(path for path in root.rglob("*") if path.is_file())
        for path in paths:
            if complete and complete():
                return
            if path in seen or not _should_probe(path) or (skip and skip(path)):
                continue
            seen.add(path)
            probe = probe_extractable(path, tools, limits)
            if probe is None:
                continue
            if depth >= limits.max_depth:
                raise ExtractionError("Nested archive depth limit exceeded")
            dest = path.parent / (path.name.replace(".", "_") + "__extracted")
            if dest.exists():
                raise ExtractionError("Nested archive extraction directory already exists")
            extract_file(path, dest, tools, limits=limits)
            validate_tree(work_dir, limits)
            visit(dest, depth + 1)
        # Split media may become complete only after the sibling images above.
        if complete and complete():
            return
        assembled = assemble_borland_split_archives(root, limits=limits)
        for path in ordered(assembled):
            if complete and complete():
                return
            if path not in seen:
                if depth >= limits.max_depth:
                    raise ExtractionError("Nested archive depth limit exceeded")
                seen.add(path)
                dest = path.with_name(path.name.replace(".", "_") + "__extracted")
                extract_file(path, dest, tools, limits=limits)
                validate_tree(work_dir, limits)
                visit(dest, depth + 1)
    visit(work_dir, 0)
