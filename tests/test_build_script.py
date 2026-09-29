"""End-to-end build-group selection through the management script."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_with_dos_reference_builds_default_and_reference_sources_together(tmp_path):
    sources = tmp_path / "sources"
    default_source = sources / "Microsoft Demo" / "ASM.TXT"
    reference_source = sources / "HelpPC 2.10" / "C.TXT"
    default_source.parent.mkdir(parents=True)
    reference_source.parent.mkdir(parents=True)
    default_source.write_bytes(b"@Default\r\n:DefaultTopic\r\n%Default help\r\n")
    reference_source.write_bytes(b"@Reference\r\n:ReferenceTopic\r\n%Reference help\r\n")

    script = Path(__file__).resolve().parents[1] / "thelp.sh"
    env = os.environ.copy()
    env.update({
        "THELP_PYTHON": sys.executable,
        "THELP_SOURCES_DIR": str(sources),
        "THELP_STATE_DIR": str(tmp_path / "var"),
    })

    def build(*options, name):
        helps = tmp_path / name
        result = subprocess.run(
            [str(script), "build", *options],
            env={**env, "THELP_HELPS_DIR": str(helps)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads((helps / "catalog.json").read_text(encoding="utf-8"))

    default_catalog = build(name="helps")
    helps = tmp_path / "helps"
    unrelated_bundle = helps / "Scorpions Cheater Demo" / "legacy.json.gz"
    unrelated_bundle.parent.mkdir()
    shutil.copy2(helps / default_catalog[0]["file"], unrelated_bundle)

    combined_catalog = build("--with-dos-reference", name="helps")

    assert {entry["name"] for entry in default_catalog} == {"Default"}
    assert {entry["name"] for entry in combined_catalog} == {"Default", "Reference"}
    assert len(combined_catalog) == 3
    assert unrelated_bundle.is_file()
    assert (helps / "c.json.gz").is_file()

    overlapping_source = sources / "Microsoft MS-DOS 6.22" / "TABLES.TXT"
    overlapping_source.parent.mkdir()
    overlapping_source.write_bytes(b"@DOS\r\n:dos\r\n%DOS help\r\n")
    microsoft_catalog = build("--group", "microsoft", name="helps")
    assert {entry["name"] for entry in microsoft_catalog} == {
        "Default", "Reference",
    }
    assert not (helps / "tables.json.gz").exists()
    assert unrelated_bundle.is_file()
