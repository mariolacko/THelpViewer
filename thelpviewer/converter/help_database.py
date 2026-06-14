"""Backward-compatible imports for the shared help manifest."""

from thelpviewer.help_database import (
    DEFAULT_HELP_DATABASE_PATH,
    BuildGroupSpec,
    ConversionBundleSpec,
    ConversionFileSpec,
    ConversionSpec,
    DownloadSourceSpec,
    HelpDatabaseEntry,
    HelpManifest,
    ProductSpec,
    SourceQuery,
    crc32_file,
    help_database_path,
    load_help_database,
    load_help_manifest,
    lookup_help_database_entry,
    product_entries,
)


__all__ = [
    "BuildGroupSpec",
    "ConversionBundleSpec",
    "ConversionFileSpec",
    "ConversionSpec",
    "DEFAULT_HELP_DATABASE_PATH",
    "DownloadSourceSpec",
    "HelpDatabaseEntry",
    "HelpManifest",
    "ProductSpec",
    "SourceQuery",
    "crc32_file",
    "help_database_path",
    "load_help_database",
    "load_help_manifest",
    "lookup_help_database_entry",
    "product_entries",
]
