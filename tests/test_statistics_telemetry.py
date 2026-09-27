from pathlib import Path


ASSET_PATHS = (
    Path("www/assets/tv-bundle-app.js"),
    Path("thelpviewer/converter/assets/tv-bundle-app.js"),
)


def test_bundle_statistics_cover_requested_aggregate_signals():
    source = ASSET_PATHS[1].read_text(encoding="utf-8")

    assert 'event: "session_end"' in source
    assert 'event: "dialog_open"' in source
    assert 'event: "tool_open"' in source
    assert 'event: "search"' in source
    assert 'event: "link"' in source
    assert 'event: "view_duration"' in source
    assert 'dialog instanceof TVGameDialog' in source
    assert 'session.view.getGameResult()' in source
    assert 'scope: "help"' in source
    assert 'scope: "document"' in source
    assert 'scope: "dialog"' in source
    assert 'scope: "game"' in source
    assert "GAME_DIALOG_NAMES" not in source
    assert "recordHelpOpen" not in source
    assert "this.dialogManager.windows.forEach" in source
    assert 'document.visibilityState === "visible"' in source
    assert 'metric: "page_ttfb"' in source
    assert 'metric: "page_load"' in source
    assert 'metric: "lcp"' in source
    assert 'metric: "cls"' in source
    assert 'metric: "inp"' in source
    assert 'event: "help_performance"' in source
    assert 'recordHelpPerformance("load"' in source
    assert 'recordHelpPerformance("decompress"' in source
    assert 'recordHelpPerformance("render"' in source
    assert "statisticsOrientation()" in source
    assert "statisticsPointer()" in source
    assert '"(prefers-reduced-motion: reduce)"' in source


def test_search_telemetry_never_sends_the_query_text():
    source = ASSET_PATHS[1].read_text(encoding="utf-8")
    search_calls = [
        line.strip()
        for line in source.splitlines()
        if 'event: "search"' in line
    ]

    assert search_calls
    assert all("query" not in line for line in search_calls)


def test_statistics_asset_mirror_is_current():
    assert ASSET_PATHS[0].read_bytes() == ASSET_PATHS[1].read_bytes()
