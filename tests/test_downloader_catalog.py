import json

from thelpviewer.server.downloader.catalog import (
    SOURCE_RUNNERS,
    all_build_groups,
    all_products,
    build_help_prefixes_for_groups,
    build_group_for_help_root,
    build_group_for_source_root,
    build_source_root_prefixes_for_groups,
    normalize_build_group,
    product_spec,
)
from thelpviewer.help_database import load_help_manifest, product_entries


def test_build_groups_and_scorpion_direct_url():
    assert all_build_groups(default_only=True) == [
        "borland",
        "microsoft",
        "norton-guides",
        "software602",
        "game-cheater",
    ]
    assert all_build_groups() == [
        "borland",
        "microsoft",
        "norton-guides",
        "software602",
        "scorpion",
        "game-cheater",
        "dos-reference",
    ]
    assert build_source_root_prefixes_for_groups(["scorpion"]) == ["Scorpions Cheater DOS"]
    assert build_help_prefixes_for_groups(["scorpion"]) == ["Scorpions Cheater"]
    assert product_spec("scorpion").sources["cheater_cz"].direct_urls == (
        "https://www.cheater.cz/wincheater2/historie-cheater-pro-dos/",
    )
    assert build_source_root_prefixes_for_groups(["game-cheater"]) == ["Game-Cheater"]
    assert build_help_prefixes_for_groups(["game-cheater"]) == ["Game-Cheater 9.02"]
    reference_roots = [
        "Microsoft MS-DOS 6.22", "Microsoft QuickBASIC 4.5",
        "HelpPC 2.10", "FreeDOS HTML Help 1.1.1a",
    ]
    assert build_source_root_prefixes_for_groups(["dos-reference"]) == reference_roots
    assert build_help_prefixes_for_groups(["dos-reference"]) == reference_roots
    assert normalize_build_group("dos-reference") == "dos-reference"
    assert build_group_for_source_root("Microsoft MS-DOS 6.22") == "dos-reference"
    assert build_group_for_help_root("Microsoft MS-DOS 6.22") == "dos-reference"
    assert build_group_for_source_root("Microsoft QuickBASIC Extended 7.1") == "microsoft"
    assert build_group_for_help_root("Microsoft QuickBASIC Extended 7.1") == "microsoft"
    assert product_spec("game-cheater").sources["slunecnice"].direct_urls == (
        "https://www.slunecnice.cz/sw/game-cheater/",
    )


def test_manifest_drives_sources_products_and_conversion_files():
    manifest = load_help_manifest()

    assert manifest.version == 2
    assert [converter.name for converter in manifest.converters[:6]] == [
        "fbhf-source",
        "hlx",
        "hlx",
        "winhelp",
        "hlx",
        "norton-guide",
    ]
    assert manifest.converters[2].source_kind == "index"
    assert manifest.converters[3].source_kind == "compiled"
    assert manifest.converters[3].reader == "thelpviewer.server.converter.readers.winhelp:WinHelpReader"
    assert manifest.converters[0].reader == "thelpviewer.server.converter.readers.fbhf:FBHFSourceReader"
    assert SOURCE_RUNNERS["cheater_cz"] == "thelpviewer.server.downloader.cheater_cz"
    assert SOURCE_RUNNERS["direct"] == "thelpviewer.server.downloader.direct"
    assert "software602" in all_products()
    assert normalize_build_group("ms") == "microsoft"
    assert normalize_build_group("gamecheater") == "game-cheater"
    assert normalize_build_group("missing") is None

    game_cheater = product_spec("game-cheater")
    assert game_cheater.menu_label == "Game-Cheater"
    assert game_cheater.default_version == "9.02"
    assert game_cheater.conversion.required_filenames == (
        "CHEATDBS.000",
        "CHEATDBS.T00",
        "FIRMY.000",
        "FIRMY.T00",
        "GCNETADR.000",
        "GCNETADR.T00",
        "GCHLP.000",
        "GCHLP.T00",
        "DBSNFO.000",
        "DBSNFO.T00",
        "GCPRM.000",
    )
    assert [bundle.bundle_stem for bundle in game_cheater.conversion.bundles] == [
        "cheaty",
        "firmy",
        "internetove-adresy",
        "napoveda",
        "informace",
    ]
    assert product_spec("scorpion").conversion.matches("DATA1.SCO")
    assert product_spec("scorpion").conversion.matches("CHEATER.EXE", secondary=True)

    turbo_pascal_entries = product_entries("tp")
    assert turbo_pascal_entries
    assert {entry.product_key for entry in turbo_pascal_entries} == {"tp"}
    assert any(entry.version == "7.1" for entry in turbo_pascal_entries)
    assembler_entries = product_entries("tasm")
    assert {entry.crc32 for entry in assembler_entries} == {0x07E89446, 0x9AC3E64A, 0xC517BD6D}
    assert all(entry.filenames == ("TASM.TAH",) for entry in assembler_entries)


def test_discovered_revisions_retain_retrieval_pages_and_fallback_queries():
    manifest = load_help_manifest()
    for crc in (0x07E89446, 0xC517BD6D, 0xC7CCE043, 0x0EA517F6, 0xBBF9DEFB, 0x7C2A5934,
                0x77B4692D, 0x1A84ACE2, 0x7D23BEE7, 0x86079353):
        entry = manifest.entry_map[crc]
        assert entry.version and entry.product_key
        origin = entry.sources["winworld"]
        assert origin.search_text and entry.filenames == origin.archive_members
        assert any("/product/" in url for url in origin.direct_urls)
        assert any("/download/" in url for url in origin.direct_urls)
        fallback = entry.sources["archiveorg"]
        assert fallback.search_text and "mediatype:software" in fallback.query
    assert product_spec("td").sources["winworld"].slug == "turbo-assembler"
    assert "Turbo Assembler" in product_spec("td").sources["archiveorg"].query
    assert product_spec("sk").sources["archiveorg"].query
    debugger15 = manifest.entry_map[0xF126AD2C]
    assert debugger15.version == "1.5" and debugger15.language == "en"
    assert debugger15.sources["direct"].archive_members == ("TDHELP.TDH",)
    assert debugger15.sources["archiveorg"].direct_urls
    assert debugger15.sources["direct"].direct_urls[0].endswith("/Disk2-Utilities.img")
    german15 = manifest.entry_map[0x4B5D33CE]
    assert german15.version == "1.5" and german15.language == "de"
    assert german15.sources["direct"].direct_urls[0].endswith("/Disk4-Hilfe.img")


def test_source_product_metadata_uses_crc_then_filename_before_folder():
    from pathlib import Path
    from thelpviewer.server.converter.writers.bundle import _product_metadata_for_source
    manifest = load_help_manifest()
    folder = "Borland Turbo Assembler 4.x"
    assert _product_metadata_for_source(Path("TDHELP.TDH"), folder, None)[0] == "td"
    assert _product_metadata_for_source(Path("TD32HELP.TDH"), folder, None)[0] == "td"
    assert _product_metadata_for_source(Path("TASM.TAH"), folder, None) == (
        "tasm", "Borland Turbo Assembler", "4.x")
    # TCHELP is shared by C and C++; an unrelated archive name proves neither.
    assert _product_metadata_for_source(Path("TCHELP.TCH"), folder, None)[0] == ""
    crc_entry = manifest.entry_map[0x9AC3E64A]
    assert _product_metadata_for_source(Path("RENAMED.HLP"), "Borland C++ 3.0", crc_entry)[0] == "tasm"


def test_pinned_dos_sources_select_only_the_intended_files():
    assert product_spec("msdos622").sources["direct"].archive_members == ("HELP.HLP",)
    assert product_spec("qb45").sources["direct"].archive_members == (
        "QB45QCK.HLP", "QB45ADVR.HLP", "QB45ENER.HLP",
    )
    assert product_spec("msdos622").sources["archiveorg"].query == (
        "identifier:en_msdos622.zip AND mediatype:software"
    )
    assert product_spec("qb45").sources["archiveorg"].query == (
        "identifier:003495-MicrosoftQuickbasic45 AND mediatype:software"
    )
    for key in ("msdos622", "qb45"):
        product = product_spec(key)
        assert product.sources["archiveorg"].archive_members == product.sources["direct"].archive_members
        assert product.collection_prefixes[0] == product.label
    assert product_spec("helppc").sources["direct"].archive_members == (
        "ASM.TXT", "C.TXT", "HARDWARE.TXT", "INTERRUP.TXT",
        "MISC.TXT", "TABLES.TXT",
    )
    assert product_spec("freedos-help").sources["direct"].archive_members == (
        "HELP/EN/HHSTNDRD/HHSTNDRD.ZIP",
        "HELP/FDL.TXT",
        "DOC/HELP/COPYING",
    )
    for key in ("msdos622", "qb45", "helppc", "freedos-help"):
        assert product_spec(key).build_group == "dos-reference"
    assert "archiveorg" not in product_spec("helppc").sources
    assert "archiveorg" not in product_spec("freedos-help").sources


def test_manifest_parses_optional_conversion_crc32(tmp_path):
    database_path = tmp_path / "help-database.json"
    database_path.write_text(
        json.dumps(
            {
                "version": 2,
                "sources": [],
                "products": [
                    {
                        "key": "sample",
                        "label": "Sample",
                        "sources": {},
                        "conversion": {
                            "use_database_entries": False,
                            "files": [
                                {
                                    "filename": "SAMPLE.DAT",
                                    "crc32": "1234ABCD",
                                    "required": True,
                                }
                            ],
                        },
                    }
                ],
                "build_groups": [],
                "entries": [],
            }
        ),
        encoding="utf-8",
    )

    conversion_file = load_help_manifest(database_path).product_map["sample"].conversion.files[0]

    assert conversion_file.filename == "SAMPLE.DAT"
    assert conversion_file.crc32 == 0x1234ABCD
    assert conversion_file.required is True
