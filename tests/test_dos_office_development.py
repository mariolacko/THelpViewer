"""Optional office/development recipes and bounded Microsoft file expansion."""

import io
import json
import struct
import zipfile

import pytest

from thelpviewer.config import CONFIG_DIR
from thelpviewer.server.dos.packages import DosPackageExtractor, configured_files
from thelpviewer.server.dos.paths import DosError


NEW_PACKAGES = {
    "freedos-watcom-c": ("BINW/WCL.EXE", "BINW/WCC.EXE", "LICENSE.TXT"),
    "freedos-watcom-fortran": ("BINW/WFL.EXE", "BINW/WFC.EXE", "LICENSE.TXT"),
    "freepascal-1010": ("BIN/GO32V2/FPC.EXE", "BIN/GO32V2/FP.EXE", "UNITS/GO32V2/RTL/SYSTEM.PPU"),
    "freedos-freebasic": ("DEVEL/FBC/FBC.EXE", "SOURCE/FBC/SOURCES.ZIP"),
    "freedos-nasm": ("DEVEL/NASM/NASM.EXE", "DEVEL/NASM/NDISASM.EXE", "SOURCE/NASM/SOURCES.ZIP"),
    "freedos-jwasm": ("DEVEL/JWASM/JWASMR.EXE", "SOURCE/JWASM/SOURCES.ZIP"),
    "freedos-djgpp-rhide": ("BIN/GCC.EXE", "BIN/GPP.EXE", "BIN/RHIDE.EXE"),
    "microsoft-word-55": ("WORD.EXE", "WORD.OVL", "MW.HLP", "SCREEN.VID"),
    "trius-as-easy-as-57": ("ASEASY.EXE", "ASEASY.HLP", "VENDOR.DOC", "NOTICE.TXT"),
    "ability-plus-30": ("AB30.EXE", "AB3.BAT", "ABILITY.HLP"),
    "visicalc-1981": ("VC.COM",),
}


def zipped(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def kwaj(name="PROGRAM", extension="EXE", payload=b"MZ DOS program"):
    names = name.encode() + b"\0" + extension.encode() + b"\0"
    return b"KWAJ\x88\xf0\x27\xd1" + struct.pack("<HHHI", 0, 18 + len(names), 25, len(payload)) + names + payload


def test_office_and_development_catalog_uses_optional_original_packages():
    manifest = json.loads((CONFIG_DIR / "dos-prompt.json").read_text())
    sources = {source["id"]: source for source in manifest["sources"]}
    assert NEW_PACKAGES.keys() <= sources.keys()
    assert manifest["memory_mb"] == 64
    for ident in NEW_PACKAGES:
        source = sources[ident]
        assert source["enabled"] is False and not source.get("required", False)
        assert source["category"] == ("development" if ident.startswith(("freedos-", "freepascal-")) else "office")
        assert source["language"] and len(source["title"]) <= 32
        assert source["description"] and source["license"] and source["launch"]
        assert isinstance(source["post_install"], list)
        configured_files(source, 256 * 1024 * 1024)
    assert sources["microsoft-word-55"]["expand"] == "microsoft"
    assert sources["trius-as-easy-as-57"]["extract"][0]["archive"] == "ASEASY.570"
    assert len(sources["freedos-djgpp-rhide"]["archives"]) == 7
    # DJGPP's libc treats /dev as devices, not an ordinary software directory.
    assert sources["freedos-djgpp-rhide"]["target"] == "DJGPP"
    assert b"C:\\DJGPP\\DJGPP.ENV" in configured_files(sources["freedos-djgpp-rhide"], 10000)["START.BAT"]


def test_kwaj_expansion_uses_original_header_names_and_preserves_parent_directory():
    source = {"format": "zip", "expand": "microsoft"}
    data = zipped({"BIN/PROG.EX$": kwaj(), "LICENSE.TXT": b"original licence"})
    assert DosPackageExtractor(10000).extract(data, source) == {
        "BIN/PROGRAM.EXE": b"MZ DOS program", "LICENSE.TXT": b"original licence"}
    assert "BIN/PROG.EX$" in DosPackageExtractor(10000).extract(data, {"format": "zip"})


def test_szdd_expansion_restores_the_missing_extension_character():
    payload = b"DOS data"
    data = b"SZDD\x88\xf0\x27\x33A" + b"T" + struct.pack("<I", len(payload)) + b"\xff" + payload
    assert DosPackageExtractor(10000).extract(zipped({"FILE.TX_": data}), {
        "format": "zip", "expand": "microsoft"}) == {"FILE.TXT": payload}


@pytest.mark.parametrize("name", ["../escape", "/outside", "SUB/DIR", "SUB\\DIR"])
def test_kwaj_header_cannot_write_outside_its_original_directory(name):
    with pytest.raises(DosError, match="path|directories|expand"):
        DosPackageExtractor(10000).extract(zipped({"PROG.EX$": kwaj(name)}), {"format": "zip", "expand": "microsoft"})


def test_microsoft_expansion_rejects_conflicts_corrupt_files_and_expanded_quota():
    extractor = DosPackageExtractor(10000)
    with pytest.raises(DosError, match="Duplicate expanded"):
        extractor.extract(zipped({"PROG.EX$": kwaj(), "PROGRAM.EXE": b"existing"}), {"format": "zip", "expand": "microsoft"})
    with pytest.raises(DosError, match="Cannot expand"):
        extractor.extract(zipped({"PROG.EX$": b"KWAJ\x88\xf0\x27\xd1"}), {"format": "zip", "expand": "microsoft"})
    with pytest.raises(DosError, match="quota|expand"):
        DosPackageExtractor(250).extract(zipped({"PROG.EX$": kwaj(payload=b"A" * 200), "PROG2.EX$": kwaj("SECOND", payload=b"B" * 200)}),
            {"format": "zip", "expand": "microsoft"})
    with pytest.raises(DosError, match="Unknown software"):
        extractor.extract(b"", {"expand": "other"})


def test_collection_obeys_expanded_disk_quota_not_download_size_limit():
    # A compiler collection can exceed 64 MiB expanded; the configured disk
    # quota still bounds output, just as for a standalone software ZIP.
    data = zipped({"0.archive": zipped({"ONE.DAT": b"a" * 512}), "1.archive": zipped({"TWO.DAT": b"b" * 512})})
    source = {"format": "collection", "archives": [{"format": "zip"}, {"format": "zip"}]}
    with pytest.raises(DosError, match="quota"):
        DosPackageExtractor(1000).extract(data, source)
    assert sum(map(len, DosPackageExtractor(2000).extract(data, source).values())) == 1024


def test_member_exclusions_remove_other_platform_trees_before_stripping():
    data = zipped({"DIST/H/STDIO.H": b"DOS header", "DIST/H/NT/WINDOWS.H": b"Windows header",
                   "DIST/LICENSE.TXT": b"licence"})
    assert DosPackageExtractor(10000).extract(data, {"format": "zip", "members": ["DIST/*"],
        "exclude_members": ["DIST/H/NT/*"], "strip_components": 1}) == {
            "H/STDIO.H": b"DOS header", "LICENSE.TXT": b"licence"}
    with pytest.raises(DosError, match="member exclusions"):
        DosPackageExtractor(10000).extract(data, {"format": "zip", "exclude_members": "*"})
