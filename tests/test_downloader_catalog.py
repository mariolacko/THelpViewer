import json

from thelpviewer.downloader.catalog import (
    SOURCE_RUNNERS,
    all_build_groups,
    all_products,
    build_help_prefixes_for_groups,
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
    ]
    assert build_source_root_prefixes_for_groups(["scorpion"]) == ["Scorpions Cheater DOS"]
    assert build_help_prefixes_for_groups(["scorpion"]) == ["Scorpions Cheater"]
    assert product_spec("scorpion").sources["cheater_cz"].direct_urls == (
        "https://www.cheater.cz/wincheater2/historie-cheater-pro-dos/",
    )
    assert build_source_root_prefixes_for_groups(["game-cheater"]) == ["Game-Cheater"]
    assert build_help_prefixes_for_groups(["game-cheater"]) == ["Game-Cheater 9.02"]
    assert product_spec("game-cheater").sources["slunecnice"].direct_urls == (
        "https://www.slunecnice.cz/sw/game-cheater/",
    )


def test_manifest_drives_sources_products_and_conversion_files():
    manifest = load_help_manifest()

    assert manifest.version == 2
    assert [converter.name for converter in manifest.converters[:5]] == [
        "fbhf-source",
        "hlx",
        "hlx",
        "hlx",
        "norton-guide",
    ]
    assert manifest.converters[0].reader == "thelpviewer.converter.readers.fbhf:FBHFSourceReader"
    assert SOURCE_RUNNERS["cheater_cz"] == "thelpviewer.downloader.cheater_cz"
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
