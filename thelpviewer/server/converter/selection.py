"""Request-scoped HELP edition selection shared by discovery and ingestion."""

from contextlib import contextmanager
from contextvars import ContextVar
from fnmatch import fnmatch
from pathlib import Path
import re

from ...help_database import load_help_manifest
from ...help_packages import help_package_id
from .metadata import product_metadata_for_group


_selected_packages = ContextVar("help_download_packages", default=None)


def archive_members_for(product_key, version) -> tuple[str, ...]:
    """Reuse configured source members as the edition's input list."""
    manifest = load_help_manifest()
    product = manifest.product_map.get(product_key)
    if product is None:
        return ()
    queries = list(product.sources.values())
    entries = [entry for entry in manifest.entries if entry.product_key == product_key
               and (entry.version or product.default_version) == version]
    components = {}
    for entry in entries:
        component = (entry.collection, entry.bundle_stem or (entry.filenames[0].casefold() if entry.filenames else ""))
        components[component] = components.get(component, False) or any(
            query.archive_members for query in entry.sources.values())
    if not any(query.archive_members for query in queries) and not all(components.values()):
        # A retrieval recipe for only one component is not a complete edition
        # allowlist. Revisions of one component are alternatives, not additional
        # required files. Do not discard other components without a list.
        return ()
    queries.extend(query for entry in entries for query in entry.sources.values())
    # Archive paths describe provider-specific containers; publication keeps
    # canonical basenames. Explicit source plans retain their full member paths.
    return tuple(dict.fromkeys(Path(name.replace("\\", "/")).name
                               for query in queries for name in query.archive_members))


def _source_identity(path, entry=None):
    if entry and entry.product_key:
        product = load_help_manifest().product_map[entry.product_key]
        return entry.product_key, entry.version or product.default_version
    product_key, version = "", ""
    parts = Path(path).parent.parts
    for index in range(len(parts) - 1, -1, -1):
        product_key, _name, version = product_metadata_for_group(Path(*parts[index:]).as_posix())
        if product_key:
            break
    if product_key and _selected_packages.get():
        versions = [ident.partition(":")[2] for ident in _selected_packages.get()
                    if ident.partition(":")[0] == product_key]
        if len(versions) == 1 and (not version or version_selected(product_key, version)):
            version = versions[0]
    return product_key, version


def archive_member_selected(path, entry=None) -> bool:
    """Apply the same source list to already-extracted batch inputs."""
    product_key, version = _source_identity(path, entry)
    product = load_help_manifest().product_map.get(product_key)
    if entry and not entry.sources and product and not any(
            query.archive_members for query in product.sources.values()):
        return True
    members = archive_members_for(product_key, version)
    return not members or any(fnmatch(Path(path).name.casefold(), member.casefold()) for member in members)


@contextmanager
def select_help_packages(package_ids):
    token = _selected_packages.set(None if package_ids is None else frozenset(package_ids))
    try:
        yield
    finally:
        _selected_packages.reset(token)


def version_selected(product_key: str, label: str, *, match_language=True) -> bool:
    """Filter discovered release pages before requesting their archives."""
    selected = _selected_packages.get()
    if selected is None:
        return True
    versions = [ident.split(":", 1)[1] for ident in selected if ident.split(":", 1)[0] == product_key]
    for version in versions:
        if not version:
            return True
        number = re.search(r"\d+(?:\.(?:\d+|x))*", version, re.I)
        if number:
            wanted = number.group().lower().split(".")
            for candidate in re.findall(r"\d+(?:\.\d+)*", label):
                parts = candidate.split(".")
                if all(part == "x" or int(part) == int(parts[index])
                       for index, part in enumerate(wanted) if index < len(parts)) and (
                       len(parts) >= len(wanted) or all(part in ("0", "x") for part in wanted[len(parts):])) and (
                       "x" in wanted or all(int(part) == 0 for part in parts[len(wanted):])):
                    language = re.search(r"\(([A-Z]{2})\)", version)
                    if not match_language or not language or re.search(r"\b" + language.group(1) + r"\b", label, re.I) or (
                            language.group(1) == "DE" and re.search(r"german|deutsch", label, re.I)):
                        return True
        elif version.casefold() in label.casefold():
            return True
    return False


def source_entry_selected(entry) -> bool:
    """Use verified source identity, not an archive's broad release-page name."""
    selected = _selected_packages.get()
    if selected is None or not entry.product_key:
        return True
    product = load_help_manifest().product_map.get(entry.product_key)
    return help_package_id(entry.product_key, entry.version or (product.default_version if product else "")) in selected
