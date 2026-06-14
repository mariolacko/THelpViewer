"""Compatibility facade over the shared JSON product manifest."""

from __future__ import annotations

from thelpviewer.help_database import (
    BuildGroupSpec,
    ProductSpec,
    SourceQuery,
    load_help_manifest,
)


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


def product_spec(key: str) -> ProductSpec:
    """Return one product spec or raise ``KeyError``."""
    return PRODUCTS[key]


def products_for_source(source: str, selected_keys: list[str] | None = None) -> list[ProductSpec]:
    """Return product specs supported by one source."""
    wanted = set(selected_keys or PRODUCT_ORDER)
    return [
        product
        for product in _MANIFEST.products
        if product.key in wanted and source in product.sources
    ]


def supported_product_keys(source: str) -> list[str]:
    """Return product keys supported by one source."""
    return [spec.key for spec in products_for_source(source)]


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
    "build_help_prefixes_for_groups",
    "build_source_root_prefixes_for_groups",
    "normalize_build_group",
    "product_spec",
    "products_for_source",
    "supported_product_keys",
]
