"""Canonical product/release/menu metadata, shared by conversion and publication."""

from pathlib import Path
from thelpviewer.help_database import HelpDatabaseEntry, ProductSpec, load_help_manifest


def product_menu_label(product: ProductSpec | None) -> str:
    if product is None:
        return ""
    return product.menu_label or product.label


def product_metadata_for_database_entry(
    database_entry: HelpDatabaseEntry | None,
) -> tuple[str, str, str]:
    if database_entry is None or not database_entry.product_key:
        return "", "", ""
    product = load_help_manifest().product_map.get(database_entry.product_key)
    version = database_entry.version or (product.default_version if product else "")
    return database_entry.product_key, product_menu_label(product), version


def product_metadata_for_group(group_name: str) -> tuple[str, str, str]:
    normalized = group_name.replace("\\", "/").strip("/")
    if not normalized:
        return "", "", ""
    manifest = load_help_manifest()
    matches: list[tuple[int, int, ProductSpec, str]] = []
    for product in manifest.products:
        prefixes = (
            [(prefix, 2) for prefix in product.collection_prefixes]
            + [(product.label, 1)]
            + ([(product.menu_label, 0)] if product.menu_label else [])
        )
        for prefix, priority in prefixes:
            clean_prefix = prefix.strip()
            if not clean_prefix:
                continue
            if normalized.casefold().startswith(clean_prefix.casefold()):
                remainder = normalized[len(clean_prefix) :]
                if remainder and remainder[0] not in " -/":
                    continue
                matches.append((len(clean_prefix), priority, product, remainder.strip(" -/")))
    if matches:
        _, _, product, version = max(matches, key=lambda match: (match[0], match[1]))
        return product.key, product_menu_label(product), version or product.default_version
    return "", "", ""


def product_metadata_for_source(
    source_path: Path, group_name: str, database_entry: HelpDatabaseEntry | None,
) -> tuple[str, str, str]:
    """Prefer verified CRC/file ownership over the containing archive's label."""
    if database_entry is not None and database_entry.product_key:
        return product_metadata_for_database_entry(database_entry)
    manifest = load_help_manifest()
    owners = {product.key for product in manifest.products if product.conversion.matches(source_path)}
    owners.update(entry.product_key for entry in manifest.entries
                  if entry.product_key and any(name.casefold() == source_path.name.casefold()
                                               for name in entry.filenames))
    inferred = product_metadata_for_group(group_name)
    if not owners or inferred[0] in owners:
        return inferred
    if len(owners) == 1:
        product = manifest.product_map[next(iter(owners))]
        return product.key, product_menu_label(product), product.default_version
    return "", "", ""  # A mixed archive cannot disambiguate a shared filename.


def catalog_menu_name(
    display_name: str,
    *,
    group_name: str,
    product_name: str,
    version: str,
) -> str:
    label = display_name.strip()
    prefixes = [
        f"{group_name} - ",
        f"{product_name} {version} - " if product_name and version else "",
        f"{product_name} - " if product_name else "",
    ]
    for prefix in prefixes:
        if prefix and label.casefold().startswith(prefix.casefold()):
            return label[len(prefix) :].strip() or label
    return label
