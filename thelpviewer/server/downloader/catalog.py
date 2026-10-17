"""Shared HELP manifest catalog and request-scoped edition discovery."""

from __future__ import annotations

from dataclasses import replace
from ..converter.selection import _selected_packages

from thelpviewer.help_database import (
    ProductSpec,
    SourceQuery,
    load_help_manifest,
)
from ...help_packages import help_package_id


_MANIFEST = load_help_manifest()
SOURCE_ORDER = tuple(item.key for item in _MANIFEST.sources)
SOURCE_DESCRIPTIONS = {item.key: item.description for item in _MANIFEST.sources}
SOURCE_RUNNERS = {item.key: item.runner for item in _MANIFEST.sources}
PRODUCTS = _MANIFEST.product_map
PRODUCT_ORDER = tuple(item.key for item in _MANIFEST.products)


def all_sources() -> list[str]:
    """Return supported downloader sources in stable CLI order."""
    return list(SOURCE_ORDER)


def all_products() -> list[str]:
    """Return supported logical product keys in stable CLI order."""
    return list(PRODUCT_ORDER)


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
        family = product if source in product.sources else None
        if source in product.sources:
            queries.add(product.sources[source])
            if selected is None:
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
        if selected is not None and family:
            # Pinned edition recipes must not wait behind an entire family's
            # release scan. Keep the family as fallback for missing components.
            jobs.append(family)
    return jobs


def supported_product_keys(source: str) -> list[str]:
    """Return product keys supported by one source."""
    return list(dict.fromkeys(spec.key for spec in products_for_source(source)))


__all__ = [
    "PRODUCTS",
    "PRODUCT_ORDER",
    "ProductSpec",
    "SOURCE_DESCRIPTIONS",
    "SOURCE_ORDER",
    "SOURCE_RUNNERS",
    "SourceQuery",
    "all_products",
    "all_sources",
    "product_spec",
    "products_for_source",
    "supported_product_keys",
]
