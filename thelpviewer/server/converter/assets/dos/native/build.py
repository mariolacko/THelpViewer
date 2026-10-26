"""Rebuild the pinned classic DOSBox canvas backend.

Run inside the official emscripten/emsdk:4.0.8 image; see the bundled README.
Only generated wdosbox.js/wasm are published. Source archives remain untouched.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tarfile


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"Pinned source no longer matches: {path.name}: {old!r}")
    path.write_text(text.replace(old, new))


def extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as source:
        # These are versioned upstream source archives, not user DOS packages.
        for member in source.getmembers():
            original = Path(member.name)
            if original.is_absolute() or ".." in original.parts:
                raise RuntimeError(f"Unsafe source archive member: {member.name}")
            relative = Path(*original.parts[1:])
            if not relative.parts:
                continue
            if relative.is_absolute() or ".." in relative.parts or member.issym() or member.islnk():
                raise RuntimeError(f"Unsafe source archive member: {member.name}")
            member.name = relative.as_posix()
            source.extract(member, destination, filter="data")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    options = parser.parse_args()
    assets = Path(__file__).resolve().parents[1]
    source = options.work_dir.resolve() / "source"
    build = options.work_dir.resolve() / "build"
    if source.exists():
        raise RuntimeError("Use a fresh work directory; existing build sources are not overwritten")
    extract(assets / "emulators/sources/emulators.tar.gz", source)
    extract(assets / "emulators/sources/dosbox.tar.gz", source / "native/dosbox")
    cmake = source / "CMakeLists.txt"
    replace_once(cmake, "set(GL4ES true)", "set(GL4ES false)")
    for target in ("dhry2", "sokol", "dosbox-sdl", "dosbox-x-sdl2"):
        replace_once(cmake, f'include("${{TARGETS_DIR}}/{target}.cmake")', "")
    subprocess.run(["emcmake", "cmake", "-GUnix Makefiles", "-DCMAKE_BUILD_TYPE=Release", "-DDOSBOX_DEBUG=OFF",
                    "-S", str(source), "-B", str(build)], check=True)
    subprocess.run(["cmake", "--build", str(build), "--target", "wdosbox", "-j4"], check=True)
    options.output_dir.mkdir(parents=True, exist_ok=True)
    worker = (source / "src/dos/dosbox/ts/worker-server.js").read_text().replace("@MODULE_NAME@", "WDOSBOX").replace("@SOCKDRIVE@", "")
    (options.output_dir / "wdosbox.js").write_text((build / "wdosbox.js").read_text() + "\n" + worker)
    shutil.copyfile(build / "wdosbox.wasm", options.output_dir / "wdosbox.wasm")
    shutil.copyfile(assets / "emulators/emulators.js", options.output_dir / "emulators.js")


if __name__ == "__main__":
    main()
