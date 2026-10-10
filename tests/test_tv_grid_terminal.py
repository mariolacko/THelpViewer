"""Checks for the grid primitive and removal of the server terminal."""

from pathlib import Path

def test_grid_is_exported_and_uses_list_scrollbars():
    source = Path("thelpviewer/server/converter/assets/tv-core.js").read_text(encoding="utf-8")
    assert "class TVGridView extends TVListBox" in source
    assert "setHeadersVisible(visible)" in source
    assert "selectCell(row, column, options = {})" in source
    assert "    TVGridView," in source
    assert source == Path("www/assets/tv-core.js").read_text(encoding="utf-8")


def test_server_terminal_is_removed():
    for file in ("tv-dialogs.js", "tv-shell.js", "tv-bundle-app.js"):
        source = Path("www/assets", file).read_text(encoding="utf-8")
        assert "TVServerTerminalDialog" not in source
        assert "/api/terminal/" not in source
    assert not Path("thelpviewer/server/terminal.py").exists()
