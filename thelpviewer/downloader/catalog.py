"""Central manifest of what help products to fetch from which sources."""

from __future__ import annotations

from dataclasses import dataclass


SOURCE_ORDER = ("winworld", "archiveorg", "olddos", "github", "davep_ng", "cheater_cz", "slunecnice")

SOURCE_DESCRIPTIONS: dict[str, str] = {
    "winworld": "WinWorldPC (product/version pages)",
    "archiveorg": "Archive.org (search query + metadata files)",
    "olddos": "old-dos.ru (category listing + detail page)",
    "github": "GitHub (repo tree / contents API)",
    "davep_ng": "Dave Pearson Norton Guides mirror",
    "cheater_cz": "Cheater.cz (Scorpions Cheater DOS archives)",
    "slunecnice": "Slunečnice.cz (Game-Cheater 9.02 archive)",
}


@dataclass(frozen=True, slots=True)
class SourceQuery:
    """How one logical product is discovered on one concrete website."""

    search_text: str
    slug: str | None = None
    query: str | None = None
    keywords: tuple[str, ...] = ()
    category_ids: tuple[int, ...] = ()
    base_url: str | None = None
    api_url: str | None = None
    raw_base_url: str | None = None
    direct_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductSpec:
    """One logical downloadable help/product group."""

    key: str
    label: str
    sources: dict[str, SourceQuery]


@dataclass(frozen=True, slots=True)
class BuildGroupSpec:
    """One logical build group consumed by the build shell wrapper."""

    key: str
    label: str
    source_root_prefixes: tuple[str, ...]
    help_dir_prefixes: tuple[str, ...]
    include_by_default: bool = True


PRODUCTS: dict[str, ProductSpec] = {
    "tp": ProductSpec(
        key="tp",
        label="Borland Turbo Pascal",
        sources={
            "winworld": SourceQuery(
                search_text="Turbo Pascal",
                slug="turbo-pascal",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland Turbo Pascal",
                query='creator:Borland AND (title:"Turbo Pascal" OR subject:"Turbo Pascal") AND mediatype:software',
                keywords=("borland", "turbo pascal"),
            ),
            "olddos": SourceQuery(
                search_text="Turbo Pascal",
                keywords=("turbo pascal",),
                category_ids=(51,),
            ),
        },
    ),
    "tc": ProductSpec(
        key="tc",
        label="Borland Turbo C",
        sources={
            "winworld": SourceQuery(
                search_text="Turbo C / Turbo C++",
                slug="turbo-c",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland Turbo C / Turbo C++",
                query='creator:Borland AND (title:"Turbo C" OR title:"Turbo C++") AND mediatype:software',
                keywords=("borland", "turbo c", "turbo c++"),
            ),
            "olddos": SourceQuery(
                search_text="Turbo C / Turbo C++",
                keywords=("turbo c", "turbo c++", "turbo cpp"),
                category_ids=(52,),
            ),
        },
    ),
    "tasm": ProductSpec(
        key="tasm",
        label="Borland Turbo Assembler",
        sources={
            "winworld": SourceQuery(
                search_text="Turbo Assembler",
                slug="turbo-assembler",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland Turbo Assembler",
                query='creator:Borland AND (title:"Turbo Assembler" OR title:"TASM") AND mediatype:software',
                keywords=("borland", "turbo assembler", "tasm"),
            ),
            "olddos": SourceQuery(
                search_text="Turbo Assembler",
                keywords=("turbo assembler", "tasm"),
                category_ids=(50,),
            ),
        },
    ),
    "td": ProductSpec(
        key="td",
        label="Borland Turbo Debugger",
        sources={
            "archiveorg": SourceQuery(
                search_text="Borland Turbo Debugger",
                query='creator:Borland AND title:"Turbo Debugger" AND mediatype:software',
                keywords=("borland", "turbo debugger"),
            ),
            "olddos": SourceQuery(
                search_text="Turbo Debugger",
                keywords=("turbo debugger",),
                category_ids=(229,),
            ),
        },
    ),
    "tbasic": ProductSpec(
        key="tbasic",
        label="Borland Turbo Basic",
        sources={
            "winworld": SourceQuery(
                search_text="Turbo Basic",
                slug="turbo-basic",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland Turbo Basic / PowerBASIC",
                query='(creator:Borland OR creator:"Power Basic") AND (title:"Turbo Basic" OR title:"PowerBASIC") AND mediatype:software',
                keywords=("borland", "turbo basic", "powerbasic"),
            ),
            "olddos": SourceQuery(
                search_text="Turbo Basic",
                keywords=("turbo basic",),
                category_ids=(58,),
            ),
        },
    ),
    "tprolog": ProductSpec(
        key="tprolog",
        label="Borland Turbo Prolog",
        sources={
            "winworld": SourceQuery(
                search_text="Turbo Prolog",
                slug="turbo-prolog",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland Turbo Prolog",
                query='creator:Borland AND title:"Turbo Prolog" AND mediatype:software',
                keywords=("borland", "turbo prolog"),
            ),
            "olddos": SourceQuery(
                search_text="Turbo Prolog",
                keywords=("turbo prolog",),
                category_ids=(126,),
            ),
        },
    ),
    "bc": ProductSpec(
        key="bc",
        label="Borland C++",
        sources={
            "winworld": SourceQuery(
                search_text="Borland C++",
                slug="borland-c",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland C++",
                query='creator:Borland AND title:"Borland C++" AND mediatype:software NOT title:"Builder"',
                keywords=("borland", "borland c++", "borland c"),
            ),
            "olddos": SourceQuery(
                search_text="Borland C++",
                keywords=("borland c++", "borland c"),
                category_ids=(52,),
            ),
        },
    ),
    "bp": ProductSpec(
        key="bp",
        label="Borland Pascal",
        sources={
            "winworld": SourceQuery(
                search_text="Borland Pascal",
                slug="borland-pascal",
            ),
            "archiveorg": SourceQuery(
                search_text="Borland Pascal",
                query='creator:Borland AND title:"Borland Pascal" AND mediatype:software',
                keywords=("borland", "borland pascal"),
            ),
            "olddos": SourceQuery(
                search_text="Borland Pascal",
                keywords=("borland pascal",),
                category_ids=(51,),
            ),
        },
    ),
    "sk": ProductSpec(
        key="sk",
        label="Borland Sidekick",
        sources={
            "winworld": SourceQuery(
                search_text="Sidekick",
                slug="sidekick",
            ),
        },
    ),
    "ng": ProductSpec(
        key="ng",
        label="Norton Guides",
        sources={
            "archiveorg": SourceQuery(
                search_text="Peter Norton Computing Norton Guides",
                query='creator:"Peter Norton Computing" AND subject:"Norton Guides"',
                keywords=("norton guides", "peter norton", "ng"),
            ),
            "github": SourceQuery(
                search_text="Norton Guides on GitHub",
                base_url="https://github.com/davep/norton-guides/tree/main/guides",
                api_url="https://api.github.com/repos/davep/norton-guides/contents/guides",
                raw_base_url="https://raw.githubusercontent.com/davep/norton-guides/main/guides/",
                direct_urls=("https://github.com/davep/norton-guides/tree/main/guides",),
            ),
            "davep_ng": SourceQuery(
                search_text="Norton Guides mirror",
                base_url="https://norton-guides.davep.dev/",
            ),
        },
    ),
    "qbx": ProductSpec(
        key="qbx",
        label="Microsoft QuickBASIC Extended 7.1",
        sources={
            "archiveorg": SourceQuery(
                search_text="Microsoft QuickBASIC Extended 7.1 / BASIC PDS 7.1",
                query='(identifier:qb71zip OR title:"Quickbasic Extended 7.1" OR title:"BASIC Professional Development System 7.1") AND mediatype:software',
                keywords=("quickbasic extended", "basic professional development system", "qbx", "quickbasic"),
                direct_urls=(
                    "https://archive.org/details/qb71zip",
                    "https://archive.org/details/microsoft-basic-professional-development-system-7.1-5.25",
                ),
            ),
        },
    ),
    "quickc": ProductSpec(
        key="quickc",
        label="Microsoft QuickC, C, and C++",
        sources={
            "archiveorg": SourceQuery(
                search_text="Microsoft QuickC / Microsoft C / PDS",
                query=(
                    "(identifier:microsoft-quick-c-2.50 "
                    "OR identifier:ms_c_pro_dev_sys_ver6.0 "
                    'OR identifier:"microsoft-c-cpp-7.0-3-20-1992-3.5-1.44mb.-7z") '
                    "AND mediatype:software"
                ),
                keywords=("quickc", "microsoft c", "microsoft c/c++", "professional development system"),
                direct_urls=(
                    "https://archive.org/details/microsoft-quick-c-2.50",
                    "https://archive.org/details/ms_c_pro_dev_sys_ver6.0",
                    "https://archive.org/details/microsoft-c-cpp-7.0-3-20-1992-3.5-1.44mb.-7z",
                ),
            ),
        },
    ),
    "masm": ProductSpec(
        key="masm",
        label="Microsoft MASM and CodeView",
        sources={
            "archiveorg": SourceQuery(
                search_text="Microsoft MASM / Macro Assembler / CodeView",
                query=(
                    "(identifier:en-masm-611 "
                    "OR identifier:microsoftmacroassembler_v51 "
                    'OR identifier:"microsoft-macro-assembler-v5.0") '
                    "AND mediatype:software"
                ),
                keywords=("masm", "microsoft macro assembler", "macro assembler", "codeview"),
                direct_urls=(
                    "https://archive.org/details/en-masm-611",
                    "https://archive.org/details/microsoftmacroassembler_v51",
                    "https://archive.org/details/microsoft-macro-assembler-v5.0",
                ),
            ),
        },
    ),
    "scorpion": ProductSpec(
        key="scorpion",
        label="Scorpions Cheater DOS",
        sources={
            "cheater_cz": SourceQuery(
                search_text="Scorpions Cheater DOS versions",
                base_url="https://www.cheater.cz/wincheater2/historie-cheater-pro-dos/",
                direct_urls=("https://www.cheater.cz/wincheater2/historie-cheater-pro-dos/",),
            ),
        },
    ),
    "game-cheater": ProductSpec(
        key="game-cheater",
        label="Game-Cheater 9.02",
        sources={
            "slunecnice": SourceQuery(
                search_text="Game-Cheater 9.02",
                base_url="https://www.slunecnice.cz/sw/game-cheater/",
                direct_urls=("https://www.slunecnice.cz/sw/game-cheater/",),
            ),
        },
    ),
}

PRODUCT_ORDER = tuple(PRODUCTS.keys())

BUILD_GROUPS: dict[str, BuildGroupSpec] = {
    "borland": BuildGroupSpec(
        key="borland",
        label="Borland",
        source_root_prefixes=("Borland ",),
        help_dir_prefixes=("Borland ",),
    ),
    "microsoft": BuildGroupSpec(
        key="microsoft",
        label="Microsoft",
        source_root_prefixes=("Microsoft ",),
        help_dir_prefixes=("Microsoft ",),
    ),
    "norton-guides": BuildGroupSpec(
        key="norton-guides",
        label="Norton Guides",
        source_root_prefixes=(PRODUCTS["ng"].label,),
        help_dir_prefixes=(PRODUCTS["ng"].label,),
    ),
    "software602": BuildGroupSpec(
        key="software602",
        label="Software 602",
        source_root_prefixes=("Software 602",),
        help_dir_prefixes=("Software 602",),
    ),
    "scorpion": BuildGroupSpec(
        key="scorpion",
        label="Scorpions Cheater DOS",
        source_root_prefixes=(PRODUCTS["scorpion"].label,),
        help_dir_prefixes=("Scorpions Cheater",),
        include_by_default=False,
    ),
    "game-cheater": BuildGroupSpec(
        key="game-cheater",
        label="Game-Cheater 9.02",
        source_root_prefixes=("Game-Cheater",),
        help_dir_prefixes=(PRODUCTS["game-cheater"].label,),
    ),
}

BUILD_GROUP_ORDER = tuple(BUILD_GROUPS.keys())


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


def build_source_root_prefixes_for_groups(selected_keys: list[str] | None = None) -> list[str]:
    """Return source-root prefixes for the selected build groups."""
    wanted = set(selected_keys or all_build_groups(default_only=True))
    roots: list[str] = []
    seen: set[str] = set()
    for key in BUILD_GROUP_ORDER:
        if key not in wanted:
            continue
        for root in BUILD_GROUPS[key].source_root_prefixes:
            if root in seen:
                continue
            seen.add(root)
            roots.append(root)
    return roots


def build_help_prefixes_for_groups(selected_keys: list[str] | None = None) -> list[str]:
    """Return top-level help-dir prefixes for the selected build groups."""
    wanted = set(selected_keys or all_build_groups(default_only=True))
    prefixes: list[str] = []
    seen: set[str] = set()
    for key in BUILD_GROUP_ORDER:
        if key not in wanted:
            continue
        for prefix in BUILD_GROUPS[key].help_dir_prefixes:
            if prefix in seen:
                continue
            seen.add(prefix)
            prefixes.append(prefix)
    return prefixes


def product_spec(key: str) -> ProductSpec:
    """Return one product spec or raise ``KeyError``."""
    return PRODUCTS[key]


def products_for_source(source: str, selected_keys: list[str] | None = None) -> list[ProductSpec]:
    """Return product specs supported by one source."""
    wanted = set(selected_keys or PRODUCT_ORDER)
    specs: list[ProductSpec] = []
    for key in PRODUCT_ORDER:
        if key not in wanted:
            continue
        spec = PRODUCTS[key]
        if source in spec.sources:
            specs.append(spec)
    return specs


def supported_product_keys(source: str) -> list[str]:
    """Return product keys supported by one source."""
    return [spec.key for spec in products_for_source(source)]
