"""One-time recovery of SHA-pinned installation receipts, never runtime aliases."""

import json
import os
import re

from ..downloader.cache import cache_metadata_path, write_cache_identity
from ..downloader.packages import package_cache_key, package_cache_path
from ..file_storage import file_digest
from .packages import DosPackageExtractor, configured_files
from .paths import DosError, MAX_SOURCE_BYTES, atomic_file, c_path


def migrate_legacy_packages(config, receipt_path, disk, downloads_dir):
    """Recover ownership only from a checksum-proven archive matching live C.

    Removing a manifest's pinned SHA changes its recipe key. The old receipt
    still proves the payload checksum, but ordinary cache migration cannot map
    it. Validate all candidates before publishing any receipt/cache changes.
    Do not guess missing inputs or overwrite modified shared/private files.
    """
    def checked(path):
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise DosError("DOS installation migration refuses symbolic links")
        if path.exists() and not path.is_file():
            raise DosError("DOS installation migration needs regular files")
        return path

    checked(receipt_path)
    if not receipt_path.exists():
        return 0
    installed = json.loads(receipt_path.read_text())
    if not isinstance(installed, dict) or not isinstance(installed.get("_files", {}), dict):
        raise DosError("Invalid DOS installation file inventory")
    owned = dict(installed.get("_files", {}))
    limit = int(config.get("max_c_bytes", MAX_SOURCE_BYTES))
    root_files = configured_files(config, limit)
    plans = []
    for source in config["sources"]:
        ident = source["id"]
        key = installed.get(ident)
        if ident in owned or key is None or key == package_cache_key(source):
            continue
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise DosError("Invalid DOS installation cache key")
        old = checked(downloads_dir / key)
        if not old.exists():
            continue
        if old.stat().st_size > MAX_SOURCE_BYTES:
            raise DosError("Legacy DOS archive exceeds its size limit")
        if file_digest(old) != key:
            continue  # A recipe fingerprint is not proof of this archive's bytes.
        if source.get("sha256") or source.get("post_install"):
            continue  # A different pinned revision/generated BAT output needs its own provenance.
        incoming = DosPackageExtractor(limit).extract(old.read_bytes(), source)
        if not incoming:
            raise DosError(f"Cannot recover legacy DOS installation: {ident}")
        prefix = c_path(source["target"]) + "/" if source.get("target") else ""
        names = []
        for name, contents in incoming.items():
            name = prefix + name
            if name in root_files:
                continue
            path = checked(disk / name)
            if not path.is_file() or path.read_bytes() != contents:
                raise DosError(f"Cannot safely recover legacy ownership of modified/missing C file: {name}")
            names.append(name)
        for name, contents in configured_files(source, limit).items():
            name = prefix + name
            if name in root_files or name in names:
                continue
            path = checked(disk / name)
            if not path.exists():
                continue  # New configured additions are installed by Apply, not this migration.
            if path.read_bytes() != contents:
                raise DosError(f"Cannot safely recover legacy ownership of modified C file: {name}")
            names.append(name)
        target = checked(downloads_dir / package_cache_path(source))
        checked(cache_metadata_path(target))
        if target.exists() and file_digest(target) != key:
            raise DosError(f"DOS cache migration conflict (nothing overwritten): {target}")
        plans.append((ident, source, old, target, key, names, old.stat()))

    for ident, source, old, target, key, names, info in plans:
        if file_digest(old) != key:
            raise DosError("Legacy DOS archive changed during migration")
        if not target.exists():
            atomic_file(target, old.read_bytes())
        if file_digest(target) != key:
            raise DosError("Legacy DOS cache copy verification failed")
        primary = {name: value for name, value in source.items() if name != "alternatives"}
        write_cache_identity(target, package_cache_key(primary), digest=key)
        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))
        installed[ident] = package_cache_key(source)
        owned[ident] = names
    if plans:
        installed["_files"] = owned
        atomic_file(receipt_path, json.dumps(installed).encode())
        # The receipt and checksum-verified readable copies are durable first.
        for old in {plan[2] for plan in plans}:
            if file_digest(old) == old.name:
                old.unlink()
    return len(plans)
