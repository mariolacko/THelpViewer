"""Stable installable HELP editions, shared by selection, downloads and builds."""

import re

from .help_database import load_help_manifest


def help_package_id(product: str, version: str = "") -> str:
    return product + ":" + version


def help_packages(catalog=()):
    manifest = load_help_manifest()
    versions = {product.key: set(product.versions) for product in manifest.products}
    for entry in manifest.entries:
        if entry.product_key in versions:
            product = manifest.product_map[entry.product_key]
            versions[product.key].add(entry.version or product.default_version)
    for entry in catalog:
        if entry.get("product") in versions:
            versions[entry["product"]].add(entry.get("version", ""))
    result = []
    for product in manifest.products:
        name = product.menu_label or product.label
        for version in sorted(versions[product.key] or {product.default_version},
                              key=lambda value: [(0, int(part)) if part.isdigit() else (1, part.casefold())
                                                 for part in re.split(r"(\d+)", value)]):
            label = name if not version or name.casefold().endswith(version.casefold()) else name + " " + version
            result.append({"id": help_package_id(product.key, version), "product": product.key,
                "version": version, "category": name, "label": label, "group": product.build_group,
                "description": product.version_descriptions.get(version, product.description)})
    return result
