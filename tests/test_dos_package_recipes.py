"""Composed archives, prepared layouts and isolated DOS post-install scripts."""

import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from thelpviewer.server.downloader.packages import download_package
from thelpviewer.server.dos.post_install import run_post_install
from thelpviewer.server.dos.paths import DosError
from thelpviewer.server.dos.packages import DosPackageExtractor, configured_files
from thelpviewer.config import CONFIG_DIR
from test_dos_prompt import store_at


def zipped(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return stream.getvalue()


def test_dos_install_falls_back_with_its_recipe_then_preserves_private_data(tmp_path, monkeypatch):
    from urllib.error import HTTPError
    from test_dos_prompt import payload

    store = store_at(tmp_path)
    account = "a" * 32
    store.save(account, payload(store, files={"SAVE.DAT": b"private save"}))
    source = {"id": "app", "url": "https://first.test/app.img", "format": "img", "target": "TOOLS/APP",
        "alternatives": [{"url": "https://second.test/app.zip", "format": "zip", "strip_components": 1}]}
    config = json.loads(store.config_path.read_text())
    config["sources"] = [source]
    store.config_path.write_text(json.dumps(config))
    calls = []
    def fetch(recipe, *_args, **_kwargs):
        calls.append(recipe["url"])
        if "first.test" in recipe["url"]:
            raise HTTPError(recipe["url"], 404, "unavailable", {}, None)
        return zipped({"APP/PROGRAM.EXE": b"MZ program", "APP/LICENSE.TXT": b"original licence"})
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    try:
        store.configure(["app"])
        assert store.state == "ready", store.error
        assert store.files["TOOLS/APP/PROGRAM.EXE"] == b"MZ program"
        assert store.overlay(account)[1] == {"SAVE.DAT": b"private save"}
        assert len(calls) == 2
        receipt = json.loads(store.installed_path.read_text())
        assert set(receipt["_files"]["app"]) == {"TOOLS/APP/PROGRAM.EXE", "TOOLS/APP/LICENSE.TXT"}
        store.configure([])
        assert "TOOLS/APP/PROGRAM.EXE" not in store.files
        assert store.overlay(account)[1] == {"SAVE.DAT": b"private save"}
        assert len(calls) == 2  # Removing the fallback install does not download.
    finally:
        store.downloads.close()


@pytest.mark.parametrize("ident,root,executable", [
    ("ia-cannon-fodder", "Cannon Fodder/_dosbox/_gamefiles/", "CF_ENG.EXE"),
    ("ia-cannon-fodder-2", "Cannon Fodder 2/_dosbox/_gamefiles/", "CANNON.EXE"),
    ("ia-commander-keen-2", "CKeen2/", "KEEN2.EXE"),
    ("ia-commander-keen-3", "CKeen3/", "KEEN3.EXE"),
    ("ia-commander-keen-4", "CKeen4/", "KEEN4E.EXE"),
    ("ia-commander-keen-5", "Keen5E/KEEN5E/", "KEEN5E.EXE"),
    ("ia-commander-keen-6", "CKeen6/", "KEEN6C.EXE"),
    ("ia-commander-keen-dreams", "", "KDREAMS.EXE"),
    ("ia-catacomb", "Catacomb/", "CATACOMB.EXE"),
    ("ia-catacomb-2", "Cataco2/", "CATACOMB.EXE"),
    ("ia-catacomb-3d", "Cataco3D/", "CAT3D.EXE"),
    ("ia-catacomb-abyss", "TheCatac/", "CATABYSS.EXE"),
    ("ia-winter-challenge", "TGameWnC/WINTER/", "WINTER.EXE"),
    ("ia-summer-challenge", "", "SUMMER.EXE"),
    ("ia-lotus-ultimate-challenge", "LotusThe/", "LOTUS.EXE"),
    ("ia-duke-nukum-shareware", "", "DN1.EXE"),
    ("ia-duke-nukem-2-shareware", "", "NUKEM2.EXE"),
    ("ia-crystal-caves-shareware", "", "CC1.EXE"),
    ("ia-bio-menace-shareware", "", "BMENACE1.EXE"),
])
def test_optional_game_recipes_flatten_the_verified_archive_roots(ident, root, executable):
    manifest = json.loads((CONFIG_DIR / "dos-prompt.json").read_text())
    source = next(item for item in manifest["sources"] if item["id"] == ident)
    assert source["enabled"] is False and source["description"] and source["license"]
    assert source["category"].startswith("games-") and source["target"].startswith("GAMES/")
    entries = {root + executable: b"MZ game", root + "README.TXT": b"original manual"}
    if "extract" in source:
        prefix = root.split("/")[0]
        entries.update({prefix + "/docs/manual.pdf": b"PDF manual",
                        prefix + "/_dosbox/DOSBOX.EXE": b"Windows host, not DOS game"})
    files = DosPackageExtractor(10000).extract(zipped(entries), {**source, "format": "zip"})
    files.update(configured_files(source, 10000))
    assert files[executable] == b"MZ game"
    if ident != "ia-summer-challenge":
        assert files["README.TXT"] == b"original manual"
    else:
        assert "SUMCRACK.EXE" not in source["members"] and "RUN.BAT" not in source["members"]
    assert not any("DOSBOX" in name or name.endswith(".DLL") for name in files)
    if ident == "ia-cannon-fodder":
        assert b"CF_ENG.EXE /F\r\n" in files["START.BAT"]
    if "extract" in source:
        assert files["DOC/MANUAL.PDF"] == b"PDF manual"


@pytest.mark.parametrize("ident,executable", [
    ("freedos-dos-navigator-2", "APPS/DN2/DN.COM"), ("freedos-doszip", "BIN/DZ.EXE"),
    ("freedos-tde", "BIN/TDER.EXE"), ("freedos-biew", "BIN/BIEW.EXE"),
    ("freedos-grafx2", "APPS/GRAFX2/BIN/GRAFX2.EXE"),
    ("freedos-dosmid", "SOUND/DOSMID/DOSMID.EXE"),
])
def test_freedos_tools_keep_their_runtime_documentation_and_source_package(ident, executable):
    source = next(item for item in json.loads((CONFIG_DIR / "dos-prompt.json").read_text())["sources"] if item["id"] == ident)
    original = {executable: b"MZ program", "DOC/LICENCE.TXT": b"licence", "SOURCE/ORIGINAL.ZIP": b"source archive"}
    assert DosPackageExtractor(10000).extract(zipped(original), source) == original
    assert source["enabled"] is False and source["description"] and source["license"]
    assert "INSTALL" not in source["launch"] and not source["post_install"]


def test_czech_package_recipes_keep_runtime_files_instead_of_an_installer(tmp_path, monkeypatch):
    sources = {item["id"]: item for item in json.loads((CONFIG_DIR / "dos-prompt.json").read_text())["sources"]}
    for ident, original in (("panda-vlak-201", {"VLAK.BAT": b"@vlak$.com vlak$.exe", "VLAK$.COM": b"loader",
            "VLAK$.EXE": b"MZ game", "VLAK$.SCN": b"scenes", "VLAK$COL.PCX": b"graphics", "VLAK.TXT": b"manual"}),
            ("software602-m602-20", {"M602.EXE": b"MZ program", "M602.HLP": b"manual", "M602C.STM": b"Czech resources"})):
        assert DosPackageExtractor(10000).extract(zipped(original), sources[ident]) == original
    source = sources["software602-t602-31"]
    files = DosPackageExtractor(10000).extract(zipped({"T602/T602.EXE": b"MZ program", "T602/T602.HLP": b"manual"}),
        {**source, "format": "zip"})
    assert files == {"T602.EXE": b"MZ program", "T602.HLP": b"manual"}
    source = sources["panda-dosman-220"]
    nested = zipped({"DOSMAN.EXE": b"MZ manager", "DOSMAN.HLP": b"manual", "LICENCE.TXT": b"licence",
                     "INSTALL.EXE": b"not published", "SHAREWARE/OTHER.EXE": b"not published"})
    source = {**source, "format": "zip", "extract": [{**source["extract"][0], "format": "zip"}]}
    assert DosPackageExtractor(10000).extract(zipped({"DOSMAN/DOSMAN.RAR": nested}), source) == {
        "DOSMAN.EXE": b"MZ manager", "DOSMAN.HLP": b"manual", "LICENCE.TXT": b"licence"}


def test_bundled_calc602_contains_only_the_approved_original_runtime(tmp_path):
    source = next(item for item in json.loads((CONFIG_DIR / "dos-prompt.json").read_text())["sources"]
                  if item["id"] == "software602-c602")
    payload, _ = download_package(source, tmp_path / "cache", 2 * 1024 * 1024,
        local_dir=Path(__file__).resolve().parents[1] / "thelpviewer/server/assets/dos")
    files = DosPackageExtractor(2 * 1024 * 1024).extract(payload, source)
    assert files["C602.EXE"].startswith(b"MZ") and files["C602.HLP"] and files["C602.DRV"]
    assert all(name in {"C602.EXE", "C602.DRV", "C602.HLP"} or name.endswith((".FON", ".DST")) for name in files)
    assert "C602.CFG" not in files and not source["enabled"] and source["language"] == "cs"


def test_archive_filter_ignores_host_only_names_but_validates_selected_dos_names(tmp_path, monkeypatch):
    monkeypatch.setattr("thelpviewer.server.dos.packages.find_sevenzip", lambda: "/usr/bin/7zz")
    def extract(_archive, output, _tools, **_options):
        (output / "GAME").mkdir(parents=True)
        (output / "GAME/PLAY.EXE").write_bytes(b"MZ game")
        (output / "HOST[windows].txt").write_bytes(b"not DOS content")
        return True
    monkeypatch.setattr("thelpviewer.server.dos.packages.extract_file", extract)
    extractor = DosPackageExtractor(10000)
    assert extractor.extract(b"archive", {"format": "archive", "members": ["GAME/*"],
        "strip_components": 1}) == {"PLAY.EXE": b"MZ game"}
    with pytest.raises(DosError, match="Invalid C drive path"):
        extractor.extract(b"archive", {"format": "archive", "members": ["*"]})


def test_collection_uses_shared_cache_and_keeps_licences_and_original_local_archive(tmp_path, monkeypatch):
    local = tmp_path / "bundled"
    local.mkdir()
    local_data = zipped({"UNARJ.EXE": b"DOS program", "LICENSE.TXT": b"licence"})
    (local / "unarj.zip").write_bytes(local_data)
    calls = []
    def fetch(source, _limit, _progress, **_kwargs):
        calls.append(source["url"])
        return zipped({"ZIP.EXE": b"zip", "COPYING": b"copyright"})
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source", fetch)
    source = {"id": "utils", "format": "collection", "archives": [
        {"url": "https://packages.test/zip.zip", "format": "zip", "target": "ZIP"},
        {"file": "unarj.zip", "format": "zip", "target": "UNARJ", "retain_archive": "SOURCE/unarj.zip"},
    ]}
    data, key = download_package(source, tmp_path / "downloads", 10000, local_dir=local)
    files = store_at(tmp_path)._source_files(data, source)
    assert files == {"ZIP/ZIP.EXE": b"zip", "ZIP/COPYING": b"copyright",
                     "UNARJ/UNARJ.EXE": b"DOS program", "UNARJ/LICENSE.TXT": b"licence",
                     "SOURCE/UNARJ.ZIP": local_data}
    assert download_package(source, tmp_path / "downloads", 10000, local_dir=local) == (data, key)
    assert calls == ["https://packages.test/zip.zip"]


@pytest.mark.parametrize("name", ["../outside.zip", "/etc/passwd", "", "."])
def test_local_package_files_cannot_escape_the_bundled_directory(tmp_path, name):
    with pytest.raises(ValueError, match="bundled package"):
        download_package({"id": "local", "file": name}, tmp_path / "downloads", 1000, local_dir=tmp_path)


def test_extract_rules_publish_prepared_files_not_an_installer(tmp_path):
    inner = zipped({"TC.EXE": b"compiler", "TCHELP.TCH": b"help"})
    outer = zipped({"Disk1/INSTALL.EXE": b"not published", "Disk2/HEAD.H": b"header", "BIN.ZIP": inner})
    files = store_at(tmp_path)._source_files(outer, {"format": "zip", "extract": [
        {"archive": "BIN.ZIP", "format": "zip", "target": "BIN"},
        {"members": ["Disk2/*.H"], "strip_components": 1, "target": "INCLUDE"},
    ]})
    assert files == {"BIN/TC.EXE": b"compiler", "BIN/TCHELP.TCH": b"help", "INCLUDE/HEAD.H": b"header"}


def fake_dosbox(monkeypatch, action):
    monkeypatch.setattr("thelpviewer.server.dos.post_install.shutil.which", lambda _: "/usr/bin/dosbox")
    def run(command, **kwargs):
        root = Path(kwargs["cwd"])
        assert command[:2] == ["/usr/bin/dosbox", "-conf"] and kwargs["timeout"] == 120
        config = Path(command[2]).read_text()
        assert "config -securemode" in config and kwargs["env"]["SDL_VIDEODRIVER"] == "dummy"
        action(root / "c")
        wrapper = next((root / "c").glob("*.BAT"))
        wrapper.with_suffix(".OK").write_bytes(b"OK\r\n")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr("thelpviewer.server.dos.post_install.subprocess.run", run)


def test_post_install_keeps_bat_and_generated_files_without_changing_tools(tmp_path, monkeypatch):
    fake_dosbox(monkeypatch, lambda disk: (disk / "TOOLS/TEST/READY.TXT").write_bytes(b"ready"))
    source = {"target": "TOOLS/TEST", "post_install": ["@ECHO OFF", "ECHO ready>READY.TXT"]}
    result = run_post_install({"FILE.TXT": b"source"}, source, {"UTILS/BIN/UNZIP.EXE": b"tool"}, 10000)
    assert result == {"FILE.TXT": b"source", "READY.TXT": b"ready",
                      "POSTINST.BAT": b"@ECHO OFF\r\nECHO ready>READY.TXT\r\n"}


@pytest.mark.parametrize("path,message", [("OUTSIDE.TXT", "outside"), ("UTILS/BIN/UNZIP.EXE", "utility")])
def test_post_install_rejects_writes_outside_its_package(tmp_path, monkeypatch, path, message):
    fake_dosbox(monkeypatch, lambda disk: (disk / path).write_bytes(b"changed"))
    with pytest.raises(DosError, match=message):
        run_post_install({"FILE.TXT": b"source"}, {"target": "TOOLS/TEST", "post_install": ["REM test"]},
                         {"UTILS/BIN/UNZIP.EXE": b"tool"}, 10000)


@pytest.mark.parametrize("lines", ["echo wrong", [42], ["a\nb"], ["a\0b"], ["🙂"]])
def test_post_install_requires_real_dos_lines(lines):
    with pytest.raises(DosError, match="post_install"):
        run_post_install({}, {"post_install": lines}, {}, 10000)


def test_pure_dos_uninstall_never_uses_network_or_post_install(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    config = json.loads(store.config_path.read_text())
    config["sources"] = [{"id": "installed", "url": "https://packages.test/game.zip", "format": "zip", "target": "GAMES"}]
    store.config_path.write_text(json.dumps(config))
    receipt = json.loads(store.installed_path.read_text())
    receipt.update({"installed": "a" * 64, "_files": {"installed": ["GAMES/OWNED.TXT"]}})
    store.installed_path.write_text(json.dumps(receipt))
    (store.disk_dir / "GAMES/OWNED.TXT").write_bytes(b"package")
    def forbidden(*_args, **_kwargs):
        pytest.fail("Pure uninstallation must not download or run scripts")
    monkeypatch.setattr("thelpviewer.server.dos.store.download_package", forbidden)
    monkeypatch.setattr("thelpviewer.server.dos.store.run_post_install", forbidden)
    store.configure([])
    assert "GAMES/OWNED.TXT" not in store.files and store.state == "ready"
