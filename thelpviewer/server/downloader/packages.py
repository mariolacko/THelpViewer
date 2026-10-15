"""Cached archive downloads for manifest-defined software packages."""

import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from .cache import atomic_download
from .transport import fetch_source


def package_cache_key(source: dict) -> str:
    digest = source.get("sha256", "")
    if digest and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError("Invalid package SHA-256")
    identity = {"url": source.get("url"), "download_forms": source.get("download_forms", [])}
    if "archives" in source:
        identity["archives"] = source["archives"]
    if "file" in source:
        identity["file"] = source["file"]
    return digest or hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def download_package(source: dict, downloads_dir: Path, limit: int, *, on_progress=None,
                     legacy_dirs=(), on_status=None, local_dir: Path | None = None) -> tuple[bytes, str]:
    key = package_cache_key(source)
    cached = downloads_dir / key
    data = None
    for path in (cached, *(directory / key for directory in legacy_dirs)):
        if path.is_symlink():
            raise ValueError("Download cache must not contain symbolic links")
        if path.is_file():
            if path.stat().st_size > limit:
                raise ValueError("Cached download exceeds its size limit")
            data = path.read_bytes()
            break
    if data is None:
        if "archives" in source:
            entries = source["archives"]
            if (source.get("format") != "collection" or not isinstance(entries, list) or not 1 <= len(entries) <= 32
                    or any(not isinstance(entry, dict) or "archives" in entry for entry in entries)):
                raise ValueError("Package collection needs 1–32 archive definitions")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
                for index, entry in enumerate(entries):
                    component = {"id": f"{source['id']}-{index}", **entry}
                    contents, _ = download_package(component, downloads_dir, limit, on_progress=on_progress,
                        on_status=on_status, local_dir=local_dir)
                    archive.writestr(f"{index}.archive", contents)
                    if buffer.tell() > limit:
                        raise ValueError("Package collection exceeds its size limit")
            data = buffer.getvalue()
        elif "file" in source:
            name = source["file"]
            if local_dir is None or not isinstance(name, str) or Path(name).name != name or name in ("", ".", ".."):
                raise ValueError("Invalid bundled package filename")
            path = local_dir / name
            if path.is_symlink() or not path.resolve().is_relative_to(local_dir.resolve()) or path.stat().st_size > limit:
                raise ValueError("Invalid bundled package file")
            data = path.read_bytes()
        else:
            data = fetch_source(source, limit, on_progress, **({"on_status": on_status} if on_status else {}))
    if len(data) > limit:
        raise ValueError("Download exceeds its size limit")
    if source.get("sha256") and hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {source['id']}")
    if not cached.is_file():
        with atomic_download(cached) as output:
            output.write(data)
    return data, key
