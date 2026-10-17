"""Configured DOS files and bounded software archive extraction."""

import base64
from fnmatch import fnmatch
from pathlib import Path
import tempfile

from ..archives.core import (ExtractorTools, ExtractionLimits, extract_file, find_lsar, find_sevenzip,
    find_unar, open_zip, read_zip_member)
from ..archives.containers import assemble_borland_split_archives, expand_microsoft
from ..processing import report_progress
from .paths import DosError, MAX_FILES, MAX_SOURCE_BYTES, c_path

def configured_files(config: dict, limit: int) -> dict[str, bytes]:
    entries = config.get("files", [])
    if not isinstance(entries, list) or len(entries) > MAX_FILES:
        raise DosError("DOS files must be a list of file definitions")
    files = {}
    total = 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) not in ({"path", "text"}, {"path", "base64"}):
            raise DosError("Each DOS file needs path and exactly one of text/base64")
        name = c_path(entry["path"])
        if name in files:
            raise DosError("Duplicate configured DOS filename")
        if "text" in entry:
            lines = entry["text"]
            if not isinstance(lines, list) or not all(isinstance(line, str) and "\n" not in line and "\r" not in line for line in lines):
                raise DosError("DOS text files must contain lists of individual lines")
            contents = ("\r\n".join(lines) + "\r\n").encode("cp437", errors="replace")
        else:
            encoded = entry["base64"]
            if not isinstance(encoded, str) or len(encoded) > 4 * ((limit + 2) // 3):
                raise DosError("Configured binary DOS file exceeds its quota")
            try:
                contents = base64.b64decode(encoded, validate=True)
            except ValueError as error:
                raise DosError("Invalid base64 in configured DOS file") from error
        total += len(contents)
        if total > limit:
            raise DosError("Configured DOS files exceed the C drive quota")
        files[name] = contents
    return files


class DosPackageExtractor:
    def __init__(self, limit: int):
        self.limit = limit

    def extract(self, data: bytes, source: dict) -> dict[str, bytes]:
        if "expand" in source:
            if source["expand"] != "microsoft":
                raise DosError("Unknown software file expansion")
            files = self.extract(data, {key: value for key, value in source.items() if key != "expand"})
            expanded = {}
            total = 0
            for name, contents in files.items():
                name, contents = expand_microsoft(contents, name, min(self.limit, MAX_SOURCE_BYTES))
                name = c_path(name)
                if name in expanded:
                    raise DosError("Duplicate expanded DOS filename")
                total += len(contents)
                if total > self.limit:
                    raise DosError("Expanded software files exceed their quota")
                expanded[name] = contents
            return expanded
        if source.get("format") == "collection":
            files = {}
            with open_zip(data, ExtractionLimits(max_files=MAX_FILES, max_bytes=MAX_SOURCE_BYTES)) as archive:
                for index, component in enumerate(source["archives"]):
                    payload = read_zip_member(archive, archive.getinfo(f"{index}.archive"), MAX_SOURCE_BYTES)
                    incoming = self.extract(payload, component)
                    prefix = c_path(component["target"]) + "/" if component.get("target") else ""
                    for name, contents in incoming.items():
                        name = prefix + name
                        if name in files and files[name] != contents:
                            raise DosError("Conflicting package collection files")
                        files[name] = contents
                    if component.get("retain_archive"):
                        name = c_path(component["retain_archive"])
                        if name in files and files[name] != payload:
                            raise DosError("Conflicting retained package archive")
                        files[name] = payload
                    if len(files) > MAX_FILES or sum(map(len, files.values())) > self.limit:
                        raise DosError("Package collection expands beyond its quota")
            return files
        if "extract" in source:
            rules = source["extract"]
            if not isinstance(rules, list) or not 1 <= len(rules) <= 64 or not all(isinstance(rule, dict) for rule in rules):
                raise DosError("Package extract must contain 1–64 extraction rules")
            original = self.extract(data, {key: value for key, value in source.items()
                if key not in ("extract", "members", "strip_components")}) if any("archive" in rule for rule in rules) else {}
            files = {}
            for rule in rules:
                if "archive" in rule:
                    names = rule["archive"] if isinstance(rule["archive"], list) else [rule["archive"]]
                    if not 1 <= len(names) <= 16:
                        raise DosError("Invalid nested archive parts")
                    try:
                        nested = b"".join(original[c_path(name)] for name in names)
                    except KeyError:
                        raise DosError("Configured nested archive is missing") from None
                    format_name = rule.get("format", "archive")
                    if format_name == "borland-split":
                        with tempfile.TemporaryDirectory(prefix="thelp-dos-split-") as temporary:
                            for name in names:
                                path = Path(temporary) / c_path(name)
                                path.parent.mkdir(parents=True, exist_ok=True)
                                path.write_bytes(original[c_path(name)])
                            assembled = assemble_borland_split_archives(Path(temporary))
                            if len(assembled) != 1:
                                raise DosError("Cannot assemble configured Borland archive parts")
                            nested = assembled[0].read_bytes()
                        format_name = "zip"
                    incoming = self.extract(nested, {"format": format_name,
                        "members": rule.get("members", ["*"]), "strip_components": rule.get("strip_components", 0)})
                else:
                    incoming = self.extract(data, {
                        **{key: value for key, value in source.items() if key != "extract"}, **rule})
                prefix = c_path(rule["target"]) + "/" if rule.get("target") else ""
                for name, contents in incoming.items():
                    name = prefix + name
                    if name in files and files[name] != contents:
                        raise DosError("Conflicting package extraction rules")
                    files[name] = contents
                if len(files) > MAX_FILES or sum(map(len, files.values())) > self.limit:
                    raise DosError("Package extraction expands beyond its quota")
            return files
        patterns = source.get("members", ["*"])
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise DosError("Invalid software member selection")
        excluded = source.get("exclude_members", [])
        if not isinstance(excluded, list) or not all(isinstance(p, str) for p in excluded):
            raise DosError("Invalid software member exclusions")
        strip = source.get("strip_components", 0)
        if not isinstance(strip, int) or isinstance(strip, bool) or not 0 <= strip <= 16:
            raise DosError("Invalid software path component count")

        def selected_name(name):
            normalized = name.replace("\\", "/").upper()
            if (not any(fnmatch(normalized, pattern.upper()) for pattern in patterns)
                    or any(fnmatch(normalized, pattern.upper()) for pattern in excluded)):
                return None
            name = c_path(name)
            parts = name.split("/")
            if len(parts) <= strip:
                raise DosError("Selected software path has too few components")
            return "/".join(parts[strip:])

        limits = ExtractionLimits(max_files=MAX_FILES, max_bytes=self.limit)
        if source.get("format") == "zip":
            files = {}
            with open_zip(data, limits) as archive:
                if any(entry.compress_type not in (0, 8, 12, 14) for entry in archive.infolist()):
                    return self.extract(data, {**source, "format": "archive"})
                entries = archive.infolist()
                for index, entry in enumerate(entries):
                    report_progress("Extracting DOS package", entry.filename, stage="extract",
                                    processed=index, total=len(entries))
                    if entry.is_dir():
                        continue
                    c_path(entry.filename)
                    name = selected_name(entry.filename)
                    if name is not None:
                        if name in files:
                            raise DosError("Duplicate DOS filename in software archive")
                        files[name] = read_zip_member(archive, entry, self.limit)
            return files
        if source.get("format") not in ("img", "archive"):
            raise DosError("Software sources must be zip, img or archive")
        tools = ExtractorTools(find_unar(), find_lsar(), find_sevenzip())
        if not tools.available:
            raise DosError("IMG extraction needs unar/lsar or 7zz; rebuild the Docker image")
        # Reuse the common image extractor for administrator-configured
        # sources, never untrusted media uploaded by a player.
        with tempfile.TemporaryDirectory(prefix="thelp-dos-image-") as temporary:
            image = Path(temporary) / ("software.img" if source.get("format") == "img" else "software.archive")
            image.write_bytes(data)
            directory = Path(temporary) / "contents"
            extract_file(image, directory, tools, limits=limits)
            if source.get("image_member"):
                wanted = c_path(source["image_member"])
                candidates = [path for path in directory.rglob("*") if path.is_file()
                              and c_path(path.relative_to(directory).as_posix()) == wanted]
                if len(candidates) != 1:
                    raise DosError("Configured disk image is missing from the software archive")
                contents = Path(temporary) / "disk-contents"
                extract_file(candidates[0], contents, tools, limits=limits)
                directory = contents
            files = {}
            for path in directory.rglob("*"):
                if path.is_symlink():
                    raise DosError("Unsafe software image")
                if path.is_file():
                    name = selected_name(path.relative_to(directory).as_posix())
                    if name is not None:
                        if name in files:
                            raise DosError("Duplicate DOS filename in software archive")
                        files[name] = path.read_bytes()
                    if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_SOURCE_BYTES:
                        raise DosError("Software image expands beyond its quota")
            return files
