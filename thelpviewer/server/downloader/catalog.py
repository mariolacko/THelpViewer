"""Shared HELP manifest catalog and request-scoped edition discovery."""

from __future__ import annotations

from dataclasses import replace
from contextlib import contextmanager
from contextvars import ContextVar
import re

from thelpviewer.help_database import (
    BuildGroupSpec,
    ProductSpec,
    SourceQuery,
    load_help_manifest,
)
from ...help_packages import help_package_id


_selected_packages = ContextVar("help_download_packages", default=None)


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


_MANIFEST = load_help_manifest()
SOURCE_ORDER = tuple(item.key for item in _MANIFEST.sources)
SOURCE_DESCRIPTIONS = {item.key: item.description for item in _MANIFEST.sources}
SOURCE_RUNNERS = {item.key: item.runner for item in _MANIFEST.sources}
PRODUCTS = _MANIFEST.product_map
PRODUCT_ORDER = tuple(item.key for item in _MANIFEST.products)
BUILD_GROUPS = _MANIFEST.build_group_map
BUILD_GROUP_ORDER = tuple(item.key for item in _MANIFEST.build_groups)


def all_sources() -> list[str]:
    """Return supported downloader sources in stable CLI order."""
    return list(SOURCE_ORDER)


def all_products() -> list[str]:
    """Return supported logical product keys in stable CLI order."""
    return list(PRODUCT_ORDER)


def all_build_groups(*, default_only: bool = False) -> list[str]:
    """Return stable build group keys used by the shell wrapper."""
    if not default_only:
        return list(BUILD_GROUP_ORDER)
    return [key for key in BUILD_GROUP_ORDER if BUILD_GROUPS[key].include_by_default]


def build_group_spec(key: str) -> BuildGroupSpec:
    """Return one build-group spec or raise ``KeyError``."""
    return BUILD_GROUPS[key]


def normalize_build_group(value: str) -> str | None:
    """Resolve a manifest build-group key or alias."""
    token = value.strip().casefold().replace("_", "-")
    if token == "all":
        return "all"
    for group in _MANIFEST.build_groups:
        names = (group.key, *group.aliases)
        if token in {name.casefold().replace("_", "-") for name in names}:
            return group.key
    return None


def build_source_root_prefixes_for_groups(selected_keys: list[str] | None = None) -> list[str]:
    """Return source-root prefixes for the selected build groups."""
    wanted = set(selected_keys or all_build_groups(default_only=True))
    roots: list[str] = []
    for key in BUILD_GROUP_ORDER:
        if key not in wanted:
            continue
        for root in BUILD_GROUPS[key].source_root_prefixes:
            if root not in roots:
                roots.append(root)
    return roots


def build_help_prefixes_for_groups(selected_keys: list[str] | None = None) -> list[str]:
    """Return top-level help-dir prefixes for the selected build groups."""
    wanted = set(selected_keys or all_build_groups(default_only=True))
    prefixes: list[str] = []
    for key in BUILD_GROUP_ORDER:
        if key not in wanted:
            continue
        for prefix in BUILD_GROUPS[key].help_dir_prefixes:
            if prefix not in prefixes:
                prefixes.append(prefix)
    return prefixes


def _build_group_for_root(name: str, prefix_field: str) -> str | None:
    """Use the most specific manifest prefix when build groups overlap."""
    owner: str | None = None
    longest = 0
    for group in _MANIFEST.build_groups:
        for prefix in getattr(group, prefix_field):
            if name.startswith(prefix) and len(prefix) > longest:
                owner = group.key
                longest = len(prefix)
    return owner


def build_group_for_source_root(name: str) -> str | None:
    return _build_group_for_root(name, "source_root_prefixes")


def build_group_for_help_root(name: str) -> str | None:
    return _build_group_for_root(name, "help_dir_prefixes")


def product_spec(key: str) -> ProductSpec:
    """Return one product spec or raise ``KeyError``."""
    return PRODUCTS[key]


def products_for_source(source: str, selected_keys: list[str] | None = None) -> list[ProductSpec]:
    """Return family and CRC-edition discovery jobs for one provider."""
    wanted = set(PRODUCT_ORDER if selected_keys is None else selected_keys)
    selected = _selected_packages.get()
    jobs: list[ProductSpec] = []
    for product in _MANIFEST.products:
        if product.key not in wanted:
            continue
        if selected is not None and not any(ident.split(":", 1)[0] == product.key for ident in selected):
            continue
        queries: set[SourceQuery] = set()
        if source in product.sources:
            queries.add(product.sources[source])
            jobs.append(product)
        for entry in _MANIFEST.entries:
            query = entry.sources.get(source) if entry.product_key == product.key and (
                selected is None or help_package_id(product.key, entry.version or product.default_version) in selected) else None
            if query is None or query in queries:
                continue
            queries.add(query)
            jobs.append(replace(
                product, sources={source: query}, default_version=entry.version,
                collection_prefixes=(entry.collection,) if entry.collection else product.collection_prefixes,
            ))
    return jobs


def supported_product_keys(source: str) -> list[str]:
    """Return product keys supported by one source."""
    return list(dict.fromkeys(spec.key for spec in products_for_source(source)))


__all__ = [
    "BUILD_GROUPS",
    "BUILD_GROUP_ORDER",
    "BuildGroupSpec",
    "PRODUCTS",
    "PRODUCT_ORDER",
    "ProductSpec",
    "SOURCE_DESCRIPTIONS",
    "SOURCE_ORDER",
    "SOURCE_RUNNERS",
    "SourceQuery",
    "all_build_groups",
    "all_products",
    "all_sources",
    "build_group_spec",
    "build_group_for_help_root",
    "build_group_for_source_root",
    "build_help_prefixes_for_groups",
    "build_source_root_prefixes_for_groups",
    "normalize_build_group",
    "product_spec",
    "products_for_source",
    "select_help_packages",
    "supported_product_keys",
    "version_selected",
]
