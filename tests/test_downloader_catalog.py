from thelpviewer.downloader.catalog import (
    all_build_groups,
    build_help_prefixes_for_groups,
    build_source_root_prefixes_for_groups,
    product_spec,
)


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
