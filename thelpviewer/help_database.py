"""Shared product, download, build, and help-file manifest loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from functools import lru_cache
import json
import os
from pathlib import Path
import zlib

from .config import CONFIG_DIR

DEFAULT_HELP_DATABASE_PATH = CONFIG_DIR / "help-database.json"


@dataclass(frozen=True, slots=True)
class DownloadSourceSpec:
    """One downloader provider registered in the manifest."""

    key: str
    description: str
    runner: str


@dataclass(frozen=True, slots=True)
class ConverterSpec:
    """One format detector and reader registered in the manifest."""

    name: str
    source_kind: str
    reader: str
    reader_init: str = "source"
    loader: str = ""
    matcher: str = ""
    matcher_args: str = "data"
    reject_matcher: str = ""
    reject_matcher_args: str = "data"
    detector: str = ""
    detector_args: str = "path_data"
    detector_equals: str = ""
    extensions: tuple[str, ...] = ()
    match_mode: str = "all"


@dataclass(frozen=True, slots=True)
class SourceQuery:
    """How one logical product is discovered on one provider."""

    search_text: str
    slug: str | None = None
    query: str | None = None
    keywords: tuple[str, ...] = ()
    category_ids: tuple[int, ...] = ()
    base_url: str | None = None
    api_url: str | None = None
    raw_base_url: str | None = None
    direct_urls: tuple[str, ...] = ()
    archive_members: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversionFileSpec:
    """One exact or pattern-based source file selected for conversion."""

    filename: str = ""
    pattern: str = ""
    crc32: int | None = None
    required: bool = False

    def matches(self, path: str | Path) -> bool:
        name = Path(path).name
        if self.filename and name.casefold() == self.filename.casefold():
            return True
        return bool(self.pattern and fnmatch(name.casefold(), self.pattern.casefold()))


@dataclass(frozen=True, slots=True)
class ConversionBundleSpec:
    """One output bundle assembled from related product files."""

    label: str
    bundle_stem: str
    filenames: tuple[str, ...]
    required: bool = True
    show_topic_titles: bool | None = None


@dataclass(frozen=True, slots=True)
class ConversionSpec:
    """Product-level conversion input selection."""

    use_database_entries: bool = True
    files: tuple[ConversionFileSpec, ...] = ()
    secondary_files: tuple[ConversionFileSpec, ...] = ()
    bundles: tuple[ConversionBundleSpec, ...] = ()

    @property
    def filenames(self) -> tuple[str, ...]:
        return tuple(item.filename for item in self.files if item.filename)

    @property
    def required_filenames(self) -> tuple[str, ...]:
        return tuple(item.filename for item in self.files if item.filename and item.required)

    def matches(self, path: str | Path, *, secondary: bool = False) -> bool:
        candidates = self.secondary_files if secondary else self.files
        return any(item.matches(path) for item in candidates)


@dataclass(frozen=True, slots=True)
class ProductSpec:
    """One product family shared by downloader and converter."""

    key: str
    label: str
    sources: dict[str, SourceQuery]
    menu_label: str = ""
    default_version: str = ""
    build_group: str = ""
    collection_prefixes: tuple[str, ...] = ()
    conversion: ConversionSpec = field(default_factory=ConversionSpec)


@dataclass(frozen=True, slots=True)
class BuildGroupSpec:
    """One logical build group consumed by the shell wrapper."""

    key: str
    label: str
    source_root_prefixes: tuple[str, ...]
    help_dir_prefixes: tuple[str, ...]
    include_by_default: bool = True
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HelpDatabaseEntry:
    """One canonical help-file record keyed by CRC32."""

    crc32: int
    filenames: tuple[str, ...]
    title: str
    collection: str
    bundle_stem: str = ""
    text_encoding: str = ""
    language: str = ""
    help_contents_topic_id: int | None = None
    product_key: str = ""
    version: str = ""


@dataclass(frozen=True, slots=True)
class HelpManifest:
    """Fully parsed contents of ``help-database.json``."""

    version: int
    sources: tuple[DownloadSourceSpec, ...]
    converters: tuple[ConverterSpec, ...]
    products: tuple[ProductSpec, ...]
    build_groups: tuple[BuildGroupSpec, ...]
    entries: tuple[HelpDatabaseEntry, ...]

    @property
    def source_map(self) -> dict[str, DownloadSourceSpec]:
        return {item.key: item for item in self.sources}

    @property
    def converter_map(self) -> dict[str, ConverterSpec]:
        return {item.name: item for item in self.converters}

    @property
    def product_map(self) -> dict[str, ProductSpec]:
        return {item.key: item for item in self.products}

    @property
    def build_group_map(self) -> dict[str, BuildGroupSpec]:
        return {item.key: item for item in self.build_groups}

    @property
    def entry_map(self) -> dict[int, HelpDatabaseEntry]:
        return {item.crc32: item for item in self.entries}


def crc32_file(path: str | Path) -> int:
    """Return the unsigned CRC32 of one source help file."""
    return zlib.crc32(Path(path).read_bytes()) & 0xFFFFFFFF


def help_database_path(path: str | Path | None = None) -> Path:
    """Resolve the configured manifest path."""
    if path is not None:
        return Path(path)
    configured = os.environ.get("THELP_HELP_DATABASE_PATH")
    return Path(configured) if configured else DEFAULT_HELP_DATABASE_PATH


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _integer_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(result)


def _parse_crc32(value: object) -> int | None:
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return int(value.strip(), 16) & 0xFFFFFFFF
    except ValueError:
        return None


def _parse_source_query(value: object) -> SourceQuery:
    item = value if isinstance(value, dict) else {}
    search_text = item.get("search_text") if isinstance(item.get("search_text"), str) else ""
    return SourceQuery(
        search_text=search_text.strip(),
        slug=item.get("slug") if isinstance(item.get("slug"), str) else None,
        query=item.get("query") if isinstance(item.get("query"), str) else None,
        keywords=_string_tuple(item.get("keywords")),
        category_ids=_integer_tuple(item.get("category_ids")),
        base_url=item.get("base_url") if isinstance(item.get("base_url"), str) else None,
        api_url=item.get("api_url") if isinstance(item.get("api_url"), str) else None,
        raw_base_url=item.get("raw_base_url") if isinstance(item.get("raw_base_url"), str) else None,
        direct_urls=_string_tuple(item.get("direct_urls")),
        archive_members=_string_tuple(item.get("archive_members")),
    )


def _parse_converter(value: object) -> ConverterSpec | None:
    if not isinstance(value, dict):
        return None
    name = value.get("name") if isinstance(value.get("name"), str) else ""
    source_kind = value.get("source_kind") if isinstance(value.get("source_kind"), str) else ""
    reader = value.get("reader") if isinstance(value.get("reader"), str) else ""
    loader = value.get("loader") if isinstance(value.get("loader"), str) else ""
    if not name.strip() or source_kind.strip() not in {"compiled", "source"}:
        return None
    if not reader.strip() and not loader.strip():
        return None
    reader_init = value.get("reader_init") if isinstance(value.get("reader_init"), str) else "source"
    match_mode = value.get("match_mode") if isinstance(value.get("match_mode"), str) else "all"
    matcher_args = value.get("matcher_args") if isinstance(value.get("matcher_args"), str) else "data"
    reject_args = value.get("reject_matcher_args") if isinstance(value.get("reject_matcher_args"), str) else "data"
    detector_args = value.get("detector_args") if isinstance(value.get("detector_args"), str) else "path_data"
    return ConverterSpec(
        name=name.strip(),
        source_kind=source_kind.strip(),
        reader=reader.strip(),
        reader_init=reader_init.strip() or "source",
        loader=loader.strip(),
        matcher=str(value.get("matcher") or "").strip(),
        matcher_args=matcher_args.strip() or "data",
        reject_matcher=str(value.get("reject_matcher") or "").strip(),
        reject_matcher_args=reject_args.strip() or "data",
        detector=str(value.get("detector") or "").strip(),
        detector_args=detector_args.strip() or "path_data",
        detector_equals=str(value.get("detector_equals") or "").strip(),
        extensions=tuple(item.lower() for item in _string_tuple(value.get("extensions"))),
        match_mode=match_mode.strip() or "all",
    )


def _parse_conversion_file(value: object) -> ConversionFileSpec | None:
    if isinstance(value, str) and value.strip():
        return ConversionFileSpec(filename=value.strip())
    if not isinstance(value, dict):
        return None
    filename = value.get("filename") if isinstance(value.get("filename"), str) else ""
    pattern = value.get("pattern") if isinstance(value.get("pattern"), str) else ""
    if not filename.strip() and not pattern.strip():
        return None
    return ConversionFileSpec(
        filename=filename.strip(),
        pattern=pattern.strip(),
        crc32=_parse_crc32(value.get("crc32")),
        required=bool(value.get("required", False)),
    )


def _parse_conversion(value: object) -> ConversionSpec:
    item = value if isinstance(value, dict) else {}

    def parse_files(key: str) -> tuple[ConversionFileSpec, ...]:
        raw = item.get(key)
        if not isinstance(raw, list):
            return ()
        parsed = (_parse_conversion_file(entry) for entry in raw)
        return tuple(entry for entry in parsed if entry is not None)

    bundles: list[ConversionBundleSpec] = []
    raw_bundles = item.get("bundles")
    if isinstance(raw_bundles, list):
        for raw_bundle in raw_bundles:
            if not isinstance(raw_bundle, dict):
                continue
            label = raw_bundle.get("label") if isinstance(raw_bundle.get("label"), str) else ""
            bundle_stem = (
                raw_bundle.get("bundle_stem")
                if isinstance(raw_bundle.get("bundle_stem"), str)
                else ""
            )
            filenames = _string_tuple(raw_bundle.get("filenames"))
            if not label.strip() or not bundle_stem.strip() or not filenames:
                continue
            show_topic_titles = raw_bundle.get("show_topic_titles")
            if not isinstance(show_topic_titles, bool):
                show_topic_titles = None
            bundles.append(
                ConversionBundleSpec(
                    label=label.strip(),
                    bundle_stem=bundle_stem.strip(),
                    filenames=filenames,
                    required=bool(raw_bundle.get("required", True)),
                    show_topic_titles=show_topic_titles,
                )
            )

    files = parse_files("files")
    if not files and bundles:
        files = tuple(
            ConversionFileSpec(filename=filename, required=bundle.required)
            for bundle in bundles
            for filename in bundle.filenames
        )
    return ConversionSpec(
        use_database_entries=bool(item.get("use_database_entries", True)),
        files=files,
        secondary_files=parse_files("secondary_files"),
        bundles=tuple(bundles),
    )


def _infer_product_and_version(
    collection: str,
    products: tuple[ProductSpec, ...],
) -> tuple[str, str]:
    matches: list[tuple[int, str, str]] = []
    for product in products:
        for prefix in product.collection_prefixes:
            if collection.casefold().startswith(prefix.casefold()):
                version = collection[len(prefix) :].strip(" -")
                matches.append((len(prefix), product.key, version))
    if not matches:
        return "", ""
    _length, product_key, version = max(matches)
    return product_key, version


def _require_unique_keys(kind: str, values: list[str]) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise ValueError(f"duplicate {kind} keys: {', '.join(duplicates)}")


def _parse_manifest(payload: object) -> HelpManifest:
    if not isinstance(payload, dict):
        raise ValueError("help database root must be a JSON object")

    raw_sources = payload.get("sources", [])
    sources: list[DownloadSourceSpec] = []
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if not isinstance(item, dict):
                continue
            key = item.get("key") if isinstance(item.get("key"), str) else ""
            runner = item.get("runner") if isinstance(item.get("runner"), str) else ""
            if not key.strip() or not runner.strip():
                continue
            description = item.get("description") if isinstance(item.get("description"), str) else key
            sources.append(DownloadSourceSpec(key.strip(), description.strip(), runner.strip()))

    raw_converters = payload.get("converters", [])
    converters: list[ConverterSpec] = []
    if isinstance(raw_converters, list):
        for item in raw_converters:
            converter = _parse_converter(item)
            if converter is not None:
                converters.append(converter)

    raw_products = payload.get("products", [])
    products: list[ProductSpec] = []
    if isinstance(raw_products, list):
        for item in raw_products:
            if not isinstance(item, dict):
                continue
            key = item.get("key") if isinstance(item.get("key"), str) else ""
            label = item.get("label") if isinstance(item.get("label"), str) else ""
            if not key.strip() or not label.strip():
                continue
            raw_queries = item.get("sources")
            queries = {
                source_key: _parse_source_query(query)
                for source_key, query in raw_queries.items()
                if isinstance(source_key, str)
            } if isinstance(raw_queries, dict) else {}
            build_group = item.get("build_group") if isinstance(item.get("build_group"), str) else ""
            products.append(
                ProductSpec(
                    key=key.strip(),
                    label=label.strip(),
                    sources=queries,
                    menu_label=str(item.get("menu_label") or "").strip(),
                    default_version=str(item.get("default_version") or "").strip(),
                    build_group=build_group.strip(),
                    collection_prefixes=_string_tuple(item.get("collection_prefixes")),
                    conversion=_parse_conversion(item.get("conversion")),
                )
            )
    product_tuple = tuple(products)

    raw_groups = payload.get("build_groups", [])
    build_groups: list[BuildGroupSpec] = []
    if isinstance(raw_groups, list):
        for item in raw_groups:
            if not isinstance(item, dict):
                continue
            key = item.get("key") if isinstance(item.get("key"), str) else ""
            label = item.get("label") if isinstance(item.get("label"), str) else ""
            if not key.strip() or not label.strip():
                continue
            build_groups.append(
                BuildGroupSpec(
                    key=key.strip(),
                    label=label.strip(),
                    source_root_prefixes=_string_tuple(item.get("source_root_prefixes")),
                    help_dir_prefixes=_string_tuple(item.get("help_dir_prefixes")),
                    include_by_default=bool(item.get("include_by_default", True)),
                    aliases=_string_tuple(item.get("aliases")),
                )
            )

    raw_entries = payload.get("entries", [])
    entries: list[HelpDatabaseEntry] = []
    if isinstance(raw_entries, list):
        for item in raw_entries:
            if not isinstance(item, dict) or item.get("kind") == "separator":
                continue
            filenames = _string_tuple(item.get("filenames"))
            filename = item.get("filename")
            if not filenames and isinstance(filename, str) and filename.strip():
                filenames = (filename.strip(),)
            crc32 = _parse_crc32(item.get("crc32"))
            if not filenames or crc32 is None:
                continue
            title = item.get("title") if isinstance(item.get("title"), str) else ""
            collection = item.get("collection") if isinstance(item.get("collection"), str) else ""
            if not collection and isinstance(item.get("project"), str):
                collection = item["project"]
            inferred_product, inferred_version = _infer_product_and_version(collection.strip(), product_tuple)
            product_key = item.get("product") if isinstance(item.get("product"), str) else inferred_product
            version = item.get("release") if isinstance(item.get("release"), str) else inferred_version
            topic_id = item.get("help_contents_topic_id")
            try:
                topic_id = int(topic_id) if topic_id is not None else None
            except (TypeError, ValueError):
                topic_id = None
            entries.append(
                HelpDatabaseEntry(
                    crc32=crc32,
                    filenames=filenames,
                    title=title.strip(),
                    collection=collection.strip(),
                    bundle_stem=str(item.get("bundle_stem") or "").strip(),
                    text_encoding=str(item.get("text_encoding") or "").strip(),
                    language=str(item.get("language") or "").strip(),
                    help_contents_topic_id=topic_id,
                    product_key=product_key.strip(),
                    version=version.strip(),
                )
            )

    _require_unique_keys("source", [item.key for item in sources])
    _require_unique_keys("product", [item.key for item in products])
    _require_unique_keys("build group", [item.key for item in build_groups])
    source_keys = {item.key for item in sources}
    build_group_keys = {item.key for item in build_groups}
    product_keys = {item.key for item in products}
    for product in products:
        unknown_sources = sorted(set(product.sources) - source_keys)
        if unknown_sources:
            raise ValueError(
                f"product {product.key} uses unknown sources: {', '.join(unknown_sources)}"
            )
        if product.build_group and product.build_group not in build_group_keys:
            raise ValueError(
                f"product {product.key} uses unknown build group: {product.build_group}"
            )
    for entry in entries:
        if entry.product_key and entry.product_key not in product_keys:
            raise ValueError(
                f"entry {entry.crc32:08X} uses unknown product: {entry.product_key}"
            )
    for converter in converters:
        if converter.match_mode not in {"all", "any"}:
            raise ValueError(f"converter {converter.name} has invalid match_mode: {converter.match_mode}")
        if converter.reader_init not in {"source", "path", "none"}:
            raise ValueError(f"converter {converter.name} has invalid reader_init: {converter.reader_init}")
        has_matcher = bool(converter.matcher or converter.detector or converter.extensions)
        if not has_matcher:
            raise ValueError(f"converter {converter.name} has no matcher, detector, or extension rule")

    try:
        version = int(payload.get("version", 1))
    except (TypeError, ValueError):
        version = 1
    return HelpManifest(
        version=version,
        sources=tuple(sources),
        converters=tuple(converters),
        products=product_tuple,
        build_groups=tuple(build_groups),
        entries=tuple(entries),
    )


@lru_cache(maxsize=4)
def _load_manifest(database_path: str) -> HelpManifest:
    path = Path(database_path)
    if not path.is_file():
        return HelpManifest(version=1, sources=(), converters=(), products=(), build_groups=(), entries=())
    return _parse_manifest(json.loads(path.read_text(encoding="utf-8")))


def load_help_manifest(path: str | Path | None = None) -> HelpManifest:
    """Load the complete shared manifest."""
    return _load_manifest(str(help_database_path(path).resolve()))


def load_help_database(path: str | Path | None = None) -> dict[int, HelpDatabaseEntry]:
    """Load canonical help-file entries indexed by CRC32."""
    return load_help_manifest(path).entry_map


def lookup_help_database_entry(
    source_path: str | Path,
    database: dict[int, HelpDatabaseEntry] | None = None,
) -> HelpDatabaseEntry | None:
    """Return the canonical metadata entry for one source help file."""
    key = crc32_file(source_path)
    return (database if database is not None else load_help_database()).get(key)


def product_entries(product_key: str, path: str | Path | None = None) -> tuple[HelpDatabaseEntry, ...]:
    """Return all CRC-backed conversion entries assigned to a product family."""
    return tuple(entry for entry in load_help_manifest(path).entries if entry.product_key == product_key)


__all__ = [
    "BuildGroupSpec",
    "ConverterSpec",
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
