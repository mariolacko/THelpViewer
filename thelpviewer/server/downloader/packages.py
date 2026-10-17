"""Cached archive downloads for manifest-defined software packages."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import zipfile
from urllib.parse import urlsplit

from .cache import cached_identity_data, cache_metadata_path, download_cached, download_filename, write_cache_identity
from ..file_storage import atomic_file, file_digest, locked_path
from .transport import fetch_source, public_url
from .attempts import try_sources
from .errors import SourceUnavailable
from .online import run_processing
from ..processing import UnsafeContentError


def package_cache_key(source: dict) -> str:
    digest = source.get("sha256", "")
    if digest and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError("Invalid package SHA-256")
    identity = {"url": source.get("url"), "download_forms": source.get("download_forms", [])}
    if "archives" in source:
        identity["archives"] = source["archives"]
    if "file" in source:
        identity["file"] = source["file"]
    if "alternatives" in source:
        identity["alternatives"] = source["alternatives"]
    return digest or hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def package_cache_path(source: dict) -> Path:
    """Readable location; the source fingerprint lives in a sidecar, not the name."""
    ident = source.get("id")
    if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", ident):
        raise ValueError("Invalid package cache ID")
    name = download_filename(str(source.get("file") or urlsplit(source.get("url", "")).path.rsplit("/", 1)[-1]))
    suffix = Path(name).suffix.lower()
    if "archives" in source:
        name = ident + ".zip"
    elif suffix not in {".zip", ".7z", ".rar", ".arj", ".arc", ".lzh", ".lha", ".exe",
                        ".img", ".ima", ".iso", ".gz", ".bz2", ".xz", ".tgz", ".tar"}:
        name = ident + {"zip": ".zip", "img": ".img"}.get(source.get("format"), ".archive")
    if len(name.encode("utf-8")) > 180:
        name = Path(name).stem.encode("utf-8")[:160].decode("utf-8", errors="ignore") + Path(name).suffix
    return Path(ident) / name


def _source_recipes(source):
    yield {key: value for key, value in source.items() if key != "alternatives"}
    for alternative in source.get("alternatives", []):
        yield {"id": source["id"], "title": source.get("title", source["id"]), **alternative}


def read_package_cache(source, downloads_dir: Path, limit: int, *, process):
    """Process an existing matching source cache; never fetch ownership guesses."""
    def missing(_path):
        raise SourceUnavailable("Matching package cache is unavailable")
    for recipe in _source_recipes(source):
        path = downloads_dir / package_cache_path(recipe)
        if not path.exists() and not path.is_symlink():
            continue
        try:
            return download_cached(path, limit, missing, identity=package_cache_key(recipe),
                process=lambda path: process(path.read_bytes(), recipe))
        except SourceUnavailable:
            continue
    return None


def migrate_package_cache(sources, downloads_dir: Path) -> dict:
    """Move recognized flat cache files once; keep unmapped inputs for expiry.

    The caller holds idle maintenance. No runtime lookup of old hash paths is
    retained. Preflight all collisions and verify copied bytes before removal.
    """
    plans, destinations = [], {}
    def plan(recipe):
        key = package_cache_key(recipe)
        old, target = downloads_dir / key, downloads_dir / package_cache_path(recipe)
        if not old.exists() and not old.is_symlink():
            return
        metadata = cache_metadata_path(target)
        if any(path.is_symlink() for root in (old, target, metadata) for path in (root, *root.parents)):
            raise UnsafeContentError("Package cache migration refuses symbolic links")
        if not old.is_file():
            raise ValueError("Package cache migration needs regular files")
        digest = file_digest(old)
        if recipe.get("sha256") and recipe["sha256"] != digest:
            raise ValueError("Package cache migration SHA-256 mismatch")
        if target in destinations:
            return  # One readable slot can hold only one source recipe.
        if target.is_file() and metadata.is_file() and metadata.stat().st_size <= 16384:
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            if (isinstance(saved, dict) and saved.get("key") != key
                    and saved.get("sha256") == file_digest(target)):
                return  # A different managed source already owns this same-name slot.
        if (target.exists() and (not target.is_file() or file_digest(target) != digest)
                or metadata.exists() and not metadata.is_file()):
            raise ValueError(f"Package cache migration conflict (nothing overwritten): {target}")
        plans.append((old, target, key, digest, old.stat()))
        destinations[target] = key

    def visit(source):
        for recipe in _source_recipes(source):
            plan(recipe)
            for index, entry in enumerate(recipe.get("archives", [])):
                visit({"id": f"{recipe['id']}-{index}", **entry})
    for source in sources:
        visit(source)
    for old, target, key, digest, info in plans:
        modified = max(info.st_mtime_ns, target.stat().st_mtime_ns) if target.exists() else info.st_mtime_ns
        if not target.exists():
            with old.open("rb") as stream, atomic_file(target) as output:
                shutil.copyfileobj(stream, output)
        if file_digest(target) != digest or file_digest(old) != digest:
            raise ValueError(f"Package cache migration verification failed: {old}")
        write_cache_identity(target, key, digest=digest)
        os.utime(target, ns=(info.st_atime_ns, modified))
    for old in {plan[0] for plan in plans}:
        old.unlink()
    return {"moved": len({plan[0] for plan in plans}),
            "unmapped": sum(path.is_file() and bool(re.fullmatch(r"[0-9a-f]{64}", path.name))
                            for path in downloads_dir.iterdir()) if downloads_dir.is_dir() else 0}


def download_package(source: dict, downloads_dir: Path, limit: int, *, on_progress=None,
                     on_status=None, local_dir: Path | None = None, process=None):
    """Try complete source recipes; validate/process before publishing their cache.

    Alternatives describe the same product/edition/language with their own
    archive layout. They cannot override installation identity or destination.
    The optional processor receives (bytes, recipe); otherwise return raw bytes.
    """
    alternatives = source.get("alternatives", [])
    allowed = {"url", "download_forms", "format", "image_member", "extract", "members",
               "exclude_members", "strip_components", "expand", "sha256", "file", "archives"}
    if (not isinstance(alternatives, list) or len(alternatives) > 8
            or any(not isinstance(item, dict) or not item or set(item) - allowed for item in alternatives)):
        raise ValueError("Package alternatives need up to eight complete download/extraction recipes")
    candidates = list(_source_recipes(source))
    primary = candidates[0]
    for candidate in candidates:
        if "url" in candidate:
            public_url(candidate["url"])
        if isinstance(candidate.get("archives"), list) and any(
                isinstance(item, dict) and "alternatives" in item for item in candidate["archives"]):
            raise ValueError("Collection components cannot override their extraction recipe with alternatives")
    options = dict(on_progress=on_progress, on_status=on_status,
                   local_dir=local_dir, process=process)
    if not alternatives:
        return _download_package(primary, downloads_dir, limit, **options)
    failures = []
    def starting(index, _candidate):
        if index and on_status:
            on_status(f"Trying alternative source {index + 1}/{len(candidates)}")
    result = try_sources(candidates,
        lambda candidate: _download_package(candidate, downloads_dir, limit, **options), on_attempt=starting,
        on_failure=lambda candidate, error: failures.append(
            f"{urlsplit(candidate.get('url', '')).hostname or 'package'}: {error}"))
    if result is not None:
        return result
    raise ValueError(f"All sources failed for {source.get('title', source['id'])}: " + "; ".join(failures))


def _download_package(source, downloads_dir, limit, *, on_progress, on_status, local_dir, process):
    key = package_cache_key(source)
    cached = downloads_dir / package_cache_path(source)
    def fetch(staged):
        data = cached_identity_data(downloads_dir, key, limit)
        if data is not None:
            pass  # The same input may already belong to another package/component.
        elif "archives" in source:
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
        with atomic_file(staged) as output:
            output.write(data)

    def validate(path):
        data = path.read_bytes()
        if source.get("sha256") and hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise SourceUnavailable(f"SHA-256 mismatch for {source['id']}")
        if process is None:
            return data
        try:
            return run_processing(lambda: process(data, source))
        except UnsafeContentError:
            raise
        except (ValueError, zipfile.BadZipFile) as error:
            raise SourceUnavailable(str(error)) from error

    try:
        # Preserve the old cache's one-transfer-per-source property even when
        # multiple package IDs now give the same archive different readable paths.
        with locked_path(downloads_dir / (".source-" + key)):
            return download_cached(cached, limit, fetch, process=validate, identity=key), key
    finally:
        if not cached.parent.is_symlink():
            try:
                cached.parent.rmdir()  # Only an empty failed attempt's own package directory.
            except OSError:
                pass
