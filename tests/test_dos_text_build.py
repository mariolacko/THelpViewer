"""The distributed bridge recipe matches its pinned sources and paired assets."""
from pathlib import Path
import runpy
import sys


def test_text_backend_recipe_and_published_asset_mirrors(tmp_path, monkeypatch):
    assets = Path("www/assets/dos")
    build_script = assets / "native/build.py"
    recipe = runpy.run_path(str(build_script))
    work, output = tmp_path / "work", tmp_path / "output"
    commands = []

    def compiled(command, check):
        assert check
        commands.append(command)
        if "--build" in command:
            build = work / "build"
            build.mkdir()
            (build / "wdosbox.js").write_text("// compiled fixture\n")
            (build / "wdosbox.wasm").write_bytes(b"compiled fixture")

    monkeypatch.setattr(sys, "argv", [str(build_script), "--work-dir", str(work), "--output-dir", str(output)])
    monkeypatch.setattr(recipe["subprocess"], "run", compiled)
    recipe["main"]()
    assert len(commands) == 2
    source = work / "source"
    native = (source / "native/jsdos/dosbox/jsdos-main.cpp").read_text()
    assert native.count("thelp_video_frame();") == 2  # declaration and frame call
    assert 'fireMessage("thelp-screen", message)' in (source / "src/protocol/protocol.ts").read_text()
    assert (output / "emulators.js").read_bytes() == (assets / "emulators/emulators.js").read_bytes()
    assert "WDOSBOX" in (output / "wdosbox.js").read_text()
    for relative in ("native/build.py", "native/text-screen.cpp", "emulators/emulators.js",
                     "emulators/wdosbox.js", "emulators/wdosbox.wasm", "emulators/README.md", "tv-dos-worker.js"):
        assert (assets / relative).read_bytes() == (Path("thelpviewer/server/converter/assets/dos") / relative).read_bytes()
