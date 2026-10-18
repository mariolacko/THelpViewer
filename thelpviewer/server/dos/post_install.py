"""Run administrator-authored package BAT scripts in an isolated DOS filesystem."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid


from .paths import DosError, c_path, MAX_FILES
from .environment import dos_search_path


def run_post_install(files, source, tools, limit):
    lines = source.get("post_install", [])
    if (not isinstance(lines, list) or len(lines) > 1024
            or any(not isinstance(line, str) or any(char in line for char in "\r\n\0") for line in lines)):
        raise DosError("post_install must be a list of individual DOS BAT lines")
    try:
        script = ("\r\n".join(lines) + "\r\n").encode("cp437")
    except UnicodeEncodeError:
        raise DosError("post_install must use DOS CP437 characters") from None
    if len(script) > 65536:
        raise DosError("Post-install script is too large")
    emulator = shutil.which("dosbox")
    if not emulator:
        raise DosError("DOS post-install requires DOSBox on the server; rebuild the Docker image")
    prefix = c_path(source["target"]) + "/" if source.get("target") else ""
    package_names = {prefix + c_path(name) for name in files}
    script_path = prefix + "POSTINST.BAT"
    if "POSTINST.BAT" in files and files["POSTINST.BAT"] != script:
        raise DosError("Post-install script conflicts with an archive file")
    tag = uuid.uuid4().hex[:8].upper()
    wrapper, marker = tag + ".BAT", tag + ".OK"
    directories = list(dict.fromkeys(c_path(name).rsplit("/", 1)[0] for name in tools if "/" in c_path(name)))
    search_path = dos_search_path(directories)
    with tempfile.TemporaryDirectory(prefix="thelp-dos-post-") as temporary:
        root = Path(temporary)
        disk = root / "c"
        originals = {**tools, **{prefix + c_path(name): data for name, data in files.items()}, script_path: script}
        for name, data in originals.items():
            path = disk / c_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        directory = "\\" + prefix.replace("/", "\\").rstrip("\\")
        dos_script = script_path.replace("/", "\\")
        (disk / wrapper).write_bytes((f"@ECHO OFF\r\nCD {directory}\r\n"
            f"CALL C:\\{dos_script}\r\nIF ERRORLEVEL 1 GOTO FAIL\r\n"
            f"ECHO OK>C:\\{marker}\r\nEXIT\r\n:FAIL\r\nECHO FAILED>C:\\{marker}\r\nEXIT\r\n").encode("ascii"))
        config = root / "dosbox.conf"
        config.write_text("[sdl]\noutput=surface\nfullscreen=false\n[dosbox]\nmemsize=64\n[cpu]\ncycles=max\n"
            "[mixer]\nnosound=true\n[midi]\nmididevice=none\n[serial]\nserial1=disabled\nserial2=disabled\n"
            "[ipx]\nipx=false\n[autoexec]\n"
            f'mount c "{disk}"\nconfig -securemode\nc:\nset PATH={search_path}\n{wrapper}\n', encoding="ascii")
        try:
            result = subprocess.run([emulator, "-conf", str(config)], cwd=root,
                env={**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        except subprocess.TimeoutExpired:
            raise DosError("DOS post-install script timed out; shared C was not changed") from None
        if result.returncode or not (disk / marker).is_file() or (disk / marker).read_bytes().strip() != b"OK":
            raise DosError("DOS post-install script failed; shared C was not changed")
        output = {}
        total = 0
        for path in disk.rglob("*"):
            if path.is_symlink():
                raise DosError("Post-install created a symbolic link")
            if not path.is_file():
                continue
            name = c_path(path.relative_to(disk).as_posix())
            if name in (wrapper, marker, script_path):
                continue
            data = path.read_bytes()
            if name in tools and name not in package_names:
                if data != tools[name]:
                    raise DosError("Post-install changed utility files")
                continue
            if not name.startswith(prefix):
                raise DosError("Post-install wrote outside its package directory")
            name = name[len(prefix):]
            total += len(data)
            if len(output) >= MAX_FILES or total > limit:
                raise DosError("Post-install output exceeds its quota")
            if name in output:
                raise DosError("Duplicate DOS post-install filename")
            output[name] = data
        return output
