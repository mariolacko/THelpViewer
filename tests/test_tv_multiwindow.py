from pathlib import Path


def test_bundle_desktop_keeps_multiple_help_and_document_windows():
    paths = (
        Path("www/assets/tv-bundle-app.js"),
        Path("thelpviewer/server/converter/assets/tv-bundle-app.js"),
    )
    assert paths[0].read_bytes() == paths[1].read_bytes()
    source = paths[0].read_text(encoding="utf-8")

    open_window = source[source.index("    _openWindow(bundle"):source.index("    _initWindowWidgets(windowEl)")]
    open_doc = source[source.index("    _openDocWindow(filename"):source.index("    _showWelcome()")]

    assert "this.openWindows.clear()" not in open_window
    assert "el.remove()" not in open_window
    assert 'helpWindow.currentView = this.currentView || "index"' in open_window
    assert "this.docWindows.get(docKey)" in open_doc
    assert 'const managerName = "doc:" + docKey' in open_doc
    assert "querySelectorAll(\".tv-doc-window\").forEach" not in open_doc
    assert "this.docWindows.delete(docKey)" in open_doc
    assert 'targets.push("doc:" + entry.file)' in source


def test_window_commands_include_cycle_and_layout_for_all_managed_windows():
    bundle = Path("www/assets/tv-bundle-app.js").read_text(encoding="utf-8")
    core = Path("www/assets/tv-core.js").read_text(encoding="utf-8")
    shell = Path("www/assets/tv-shell.js").read_text(encoding="utf-8")

    assert '{ cmd: "next", label: "~N~ext", hotkey: "F6" }' in bundle
    assert '{ cmd: "previous", label: "~P~revious", hotkey: "Shift-F6" }' in bundle
    assert "[...this.dialogManager.windows.values()]" in bundle
    assert "kbF6" in bundle
    assert "kbShiftF6" in bundle
    assert "this.activateKeyCode(getKeyCode(key), key)" in core
    assert "this.menuView?.handleEvent(event)" in core
    assert "cycleTarget(delta = 1)" in core
    assert "command === TV_COMMANDS.NEXT" in core
    assert "command === TV_COMMANDS.PREVIOUS" in core
    assert "this.identity" in shell
