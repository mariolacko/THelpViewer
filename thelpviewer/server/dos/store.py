"""Coordinate shared DOS installation, boot bundles and private storage."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
import threading
import uuid
import zipfile

from ..accounts.store import AccountStore
from ..downloader.online import OnlineDownloader
from ..downloader.packages import download_package, package_cache_key
from ..rebuild import archive_rebuild_directory, prune_backups
from ..settings import ServerSettings
from .config import load_dos_config, select_dos_packages
from .media import DosMediaStore
from .overlay import DosOverlayStore
from .packages import DosPackageExtractor, configured_files
from .paths import DosError, ID_RE, MAX_FILES, MAX_SOURCE_BYTES, atomic_file, c_path
from .post_install import run_post_install


class DosPromptStore:
    def __init__(self, root: Path, config_path: Path | None, settings: ServerSettings | None = None,
                 accounts: AccountStore | None = None, downloads_dir: Path | None = None,
                 *, users_dir: Path | None = None, disk_dir: Path | None = None, downloads=None):
        self.root, self.config_path = root, config_path
        self.settings = settings or ServerSettings(root.parent / "server-settings.json")
        self.accounts = accounts
        self.config: dict = {}
        self.files: dict[str, bytes] = {}
        self.file_hashes: dict[str, str] = {}
        self.base_id = ""
        self.state = "idle"
        self.error = ""
        self.current = ""
        self.initializing = False
        self.processed = self.total = self.percent = 0
        self.phase = "Checking disk"
        self.received = 0
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self.backup = ""
        self.rebuilding = False
        self.configuring = False
        self.downloads_dir = downloads_dir or root / "downloads"
        self.source_selection = None
        self.on_progress = None
        self.downloads = downloads or OnlineDownloader()
        self._download_id = ""
        self.users_dir = users_dir or root / "users"
        self.disk_dir = disk_dir or root / "base" / "c"
        self.base_root = disk_dir or root / "base"
        self.installed_path = root / "installed.json" if disk_dir else root / "base" / "installed.json"

        self.overlays = DosOverlayStore(self.users_dir, self.settings, self.accounts)
        self.media = DosMediaStore(self.users_dir)

    def install(self, source_ids: list[str], *, on_progress=None) -> None:
        """Install explicitly selected packages; keep the shared disk and private overlays."""
        with self._lock:
            if self.state == "building" or (self._worker and self._worker.is_alive()):
                raise DosError("DOS C drive is already being prepared")
            self.state, self.error = "building", ""
            self.on_progress = on_progress
            self.processed = self.percent = self.received = 0
            self.total = len(source_ids)
            self.phase, self.current = "Preparing DOS package changes", ""
        try:
            self.prepare(install_sources=True, source_ids=source_ids)
        finally:
            self.on_progress = None

    def configure(self, source_ids: list[str], *, on_progress=None, preserve_downloads=False) -> None:
        """Publish a selected shared disk generation; never touch private overlays."""
        with self._lock:
            if self.state == "building" or self.configuring or (self._worker and self._worker.is_alive()):
                raise DosError("DOS C drive is already being prepared")
            self.configuring = True
            previous = (self.files, self.file_hashes, self.base_id, self.state)
            self.state, self.error = "building", ""
            self.on_progress = on_progress
            self.processed = self.percent = self.received = 0
            self.total = len(source_ids)
            self.phase, self.current = "Preparing DOS package changes", ""
        disk, marker = self.disk_dir, self.installed_path
        temporary = None
        backup = None
        published = False
        try:
            backup_count = self.settings.get()["backup_count"]
            config = load_dos_config(self.config_path)
            sources = {source["id"]: source for source in config["sources"]}
            source_ids = select_dos_packages(config, source_ids)
            self.downloads.begin("dos", [], replace=not preserve_downloads)
            if disk.is_symlink() or disk.parent.is_symlink() or marker.is_symlink():
                raise DosError("Shared DOS storage must not contain symbolic links")
            if disk.exists() and (not disk.is_dir() or any(p.is_symlink() for p in disk.rglob("*"))):
                raise DosError("Shared DOS storage must be a regular directory")
            original_receipt = marker.read_bytes() if marker.exists() else None
            installed = json.loads(original_receipt) if original_receipt is not None else {}
            self.config = config
            owned = self._package_inventory(installed, sources, disk)
            removed = (set(installed) & sources.keys()) - set(source_ids)
            protected = set(configured_files(config, int(config.get("max_c_bytes", MAX_SOURCE_BYTES))))
            protected.update(name for ident, names in owned.items() if ident not in removed for name in names)
            disk.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".dos-packages-", dir=disk.parent))
            staged = temporary / "c"
            if disk.exists():
                shutil.copytree(disk, staged)
            self.disk_dir, self.installed_path = staged, temporary / "installed.json"
            installed["_files"] = owned
            for ident in removed:
                for name in owned.pop(ident):
                    path = staged / name
                    if name not in protected and path.is_file():
                        path.unlink()
                del installed[ident]
            if staged.exists():
                for directory in sorted((p for p in staged.rglob("*") if p.is_dir()),
                                        key=lambda p: len(p.parts), reverse=True):
                    if not any(directory.iterdir()):
                        directory.rmdir()
            if original_receipt is not None:
                atomic_file(self.installed_path, json.dumps(installed).encode())
            self._progress("Applying DOS packages", 0)
            self.prepare(install_sources=True, source_ids=source_ids, preserve_downloads=preserve_downloads)
            if self.state != "ready":
                raise DosError(self.error or "DOS package configuration failed")
            self.state = "building"
            backup = self.root.parent / "backups" / f"dos-packages-{uuid.uuid4().hex}"
            backup.mkdir(parents=True)
            if original_receipt is not None:
                atomic_file(backup / "installed.json", original_receipt)
            if disk.exists():
                disk.rename(backup / "c")
            try:
                staged.rename(disk)
                published = True
                atomic_file(marker, self.installed_path.read_bytes())
            except Exception:
                if published:
                    disk.rename(temporary / "unpublished-c")
                if (backup / "c").exists():
                    (backup / "c").rename(disk)
                raise
            self.backup = str(backup.relative_to(self.root.parent))
            prune_backups(backup, ("dos-base-", "dos-packages-"), backup_count)
            self.state = "ready"
            self.downloads.finish("dos")
        except Exception as error:
            self.files, self.file_hashes, self.base_id, self.state = previous
            self.error = str(error)
            self.downloads.finish("dos", error=str(error))
            raise DosError(str(error)) from error
        finally:
            self.disk_dir, self.installed_path = disk, marker
            self.configuring = False
            self.on_progress = None
            if temporary is not None:
                shutil.rmtree(temporary)

    def _package_inventory(self, installed: dict, sources: dict, disk: Path) -> dict[str, list[str]]:
        owned = installed.get("_files", {})
        if not isinstance(owned, dict):
            raise DosError("Invalid DOS installation file inventory")
        result = {}
        for ident, names in owned.items():
            if not isinstance(names, list):
                raise DosError("Invalid DOS installation file inventory")
            result[ident] = [c_path(name) for name in names]
        root_files = configured_files(self.config, int(self.config.get("max_c_bytes", MAX_SOURCE_BYTES)))
        for ident in set(installed) & sources.keys():
            if ident in result:
                continue
            key = installed[ident]
            if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
                raise DosError("Invalid DOS installation cache key")
            cached = next((directory / key for directory in (self.downloads_dir, self.root / "downloads")
                           if (directory / key).is_file() and not (directory / key).is_symlink()), None)
            if cached is None:
                raise DosError(f"Cannot safely change {ident}: its legacy installation needs the cached archive")
            if cached.stat().st_size > MAX_SOURCE_BYTES:
                raise DosError("Cached software archive exceeds its quota")
            source = sources[ident]
            incoming = self._source_files(cached.read_bytes(), source)
            incoming.update(configured_files(source, MAX_SOURCE_BYTES))
            prefix = c_path(source["target"]) + "/" if source.get("target") else ""
            names = []
            for name, contents in incoming.items():
                name = prefix + name
                if name in root_files:
                    continue
                path = disk / name
                if path.exists() and (not path.is_file() or path.read_bytes() != contents):
                    raise DosError(f"Cannot safely recover legacy ownership of modified C file: {name}")
                names.append(name)
            result[ident] = names
        return result

    def rebuild(self) -> None:
        """Replace only the shared base; retain downloads and every private overlay."""
        with self._lock:
            if self.state == "building" or (self._worker and self._worker.is_alive()):
                raise DosError("DOS C drive is already being prepared")
            if self.installed_path.is_symlink():
                raise DosError("DOS installation metadata must not be a symbolic link")
            self.settings.get()  # Validate retention before archiving the live C drive.
            self.backup = archive_rebuild_directory(self.base_root, self.root.parent / "backups", "dos-base")
            if not self.installed_path.is_relative_to(self.base_root) and self.installed_path.exists():
                if not self.backup:
                    backup = self.root.parent / "backups" / f"dos-base-{uuid.uuid4().hex}"
                    backup.mkdir(parents=True)
                    self.backup = str(backup.relative_to(self.root.parent))
                self.installed_path.rename(self.root.parent / self.backup / "installed.json")
            self.files, self.file_hashes, self.base_id = {}, {}, ""
            self.state, self.error, self.current = "idle", "", ""
            self.processed = self.total = self.percent = self.received = 0
            self.initializing = True
            self.rebuilding = True
            self.phase = "Preparing new C drive"
            self.start()

    def start(self) -> None:
        with self._lock:
            if self.state != "idle":
                return
            self.state = "building"
            self._worker = threading.Thread(target=self.prepare, name="thelp-dos-first-run", daemon=True)
            self._worker.start()

    def prepare(self, *, install_sources: bool = False, source_ids: list[str] | None = None,
                preserve_downloads=False) -> None:
        download_queue = False
        try:
            backup_count = self.settings.get()["backup_count"]
            config = load_dos_config(self.config_path)
            self.config = config
            limit = int(config.get("max_c_bytes", MAX_SOURCE_BYTES))
            if not 1024 <= limit <= 256 * 1024 * 1024:
                raise DosError("Invalid C drive size limit")
            media_limit = int(config.get("max_media_bytes", 128 * 1024 * 1024))
            if not 512 <= media_limit <= 256 * 1024 * 1024:
                raise DosError("Invalid media size limit")
            root_files = configured_files(config, limit)
            self.root.mkdir(parents=True, exist_ok=True)
            base = self.disk_dir
            marker = self.installed_path
            installed = json.loads(marker.read_text()) if marker.exists() else {}
            if not isinstance(installed, dict):
                raise DosError("Invalid DOS disk installation marker")
            initializing = installed.get("_complete") is not True
            self.initializing = initializing or install_sources
            if initializing:
                base.mkdir(parents=True, exist_ok=True)
            elif not base.is_dir():
                raise DosError("The initialised C drive is missing; restore the server disk backup")
            seen = set()
            if source_ids is None and self.source_selection:
                source_ids = self.source_selection()
            if source_ids is None:
                source_ids = [source["id"] for source in config["sources"] if source.get("enabled") is not False]
            source_ids = select_dos_packages(config, source_ids)
            sources = [source for source in config["sources"] if self.initializing and source["id"] in source_ids]
            self.total = len(sources)
            if self.total:
                self.downloads.begin("dos", [{"id": source["id"], "label": source.get("title", source["id"])}
                    for source in sources],
                    replace=not preserve_downloads)
                download_queue = True
            self.processed = 0
            for source in sources:
                if not isinstance(source, dict):
                    raise DosError("Each software source must be an object")
                ident = source.get("id", "")
                digest = source.get("sha256", "")
                if not ID_RE.fullmatch(ident) or ident in seen or (digest and not re.fullmatch(r"[0-9a-f]{64}", digest)):
                    raise DosError("Software sources need unique IDs and valid optional SHA-256 hashes")
                cache_key = package_cache_key(source)
                seen.add(ident)
                self._download_id = ident
                additions = configured_files(source, limit)
                target = c_path(source["target"]) + "/" if source.get("target") else ""
                additions = {name: root_files.get(target + name, contents) for name, contents in additions.items()}
                if installed.get(ident) == cache_key:
                    # Resume/explicit install may fill missing configured files,
                    # but never overwrite the administrator's existing C files.
                    for name, contents in additions.items():
                        destination = base / (target + name)
                        if not destination.exists():
                            atomic_file(destination, contents)
                        elif not destination.is_file() or destination.read_bytes() != contents:
                            raise DosError(f"Configured software file conflicts with existing C file: {target + name}")
                    self.processed += 1
                    self.downloads.update("dos", ident, state="done", percent=100, phase="Installed")
                    continue
                self.current = str(source.get("title", ident))
                self._progress("Downloading", 0)
                with self.downloads.context("dos", ident):
                    incoming = self.downloads.call(lambda: self._prepare_package(source, base, additions, root_files, target, limit),
                        source=source.get("url", ""))
                if len(incoming) > MAX_FILES or sum(len(value) for value in incoming.values()) > limit:
                    raise DosError("Software exceeds C drive quota")
                for index, (name, contents) in enumerate(incoming.items(), 1):
                    destination = base / (target + name)
                    if destination.exists():
                        if not destination.is_file() or destination.read_bytes() != contents:
                            raise DosError(f"Initial software conflicts with existing C file: {target + name}")
                    else:
                        atomic_file(destination, contents)
                    self._progress("Installing", 0.75 + 0.25 * index / max(1, len(incoming)))
                installed[ident] = cache_key
                installed.setdefault("_files", {})[ident] = [target + name for name in incoming
                                                            if target + name not in root_files]
                atomic_file(marker, json.dumps(installed).encode())
                self.processed += 1
                self.downloads.update("dos", ident, state="done", percent=100, phase="Installed")
            for filename, contents in root_files.items():
                destination = base / filename
                if initializing or (install_sources and not destination.exists()):
                    if destination.exists() and not destination.is_file():
                        raise DosError(f"Configured DOS file is not a regular file: {filename}")
                    atomic_file(destination, contents)
            files = {}
            self.phase = "Checking installed files"
            if (initializing or install_sources) and config.get("software_catalog"):
                guide = list(config["software_catalog"])
                if not all(isinstance(line, str) and "\n" not in line and "\r" not in line for line in guide):
                    raise DosError("DOS software_catalog must contain individual header lines")
                for source in config["sources"]:
                    if source.get("launch") and installed.get(source.get("id")):
                        guide.extend([str(source.get("title", source["id"])), "  " + source["launch"], ""])
                atomic_file(base / "SOFTWARE.TXT", ("\r\n".join(guide) + "\r\n").encode("cp437", errors="replace"))
            for path in base.rglob("*"):
                if path.is_symlink():
                    raise DosError("Shared C drive must not contain symbolic links")
                if path.is_file():
                    files[c_path(path.relative_to(base).as_posix())] = path.read_bytes()
            if len(files) > MAX_FILES or sum(map(len, files.values())) > limit:
                raise DosError("Shared C drive exceeds configured limits")
            hasher = hashlib.sha256()
            hashes = {}
            for name, contents in sorted(files.items()):
                digest = hashlib.sha256(contents)
                hashes[name] = digest.hexdigest()
                hasher.update(name.encode() + b"\0" + digest.digest())
            if initializing:
                installed["_complete"] = True
                atomic_file(marker, json.dumps(installed).encode())
            with self._lock:
                self.files, self.base_id, self.state = files, hasher.hexdigest(), "ready"
                self.file_hashes = hashes
                self.percent = 100
                if self.rebuilding and self.backup:
                    prune_backups(self.root.parent / self.backup, ("dos-base-", "dos-packages-"), backup_count)
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            self.error, self.state = str(error), "error"
            self.downloads.update("dos", self._download_id, state="error", phase="Failed", error=str(error))
        finally:
            if download_queue and not self.configuring:
                self.downloads.finish("dos", error=self.error if self.state == "error" else "")
            self._download_id = ""
            self.current = ""
            self.rebuilding = False

    def _progress(self, phase: str, fraction: float) -> None:
        self.phase = phase
        self.percent = min(99, int(100 * (self.processed + fraction) / max(1, self.total)))
        self.downloads.update("dos", self._download_id, state="running", phase=phase, percent=int(100 * fraction))
        if self.on_progress:
            self.on_progress(self.status(start=False))

    def _download_progress(self, received: int, total: int) -> None:
        self.received = received
        self._progress("Downloading", min(1, received / total) * 0.75 if total > 0 else 0)

    def _prepare_package(self, source, base, additions, root_files, target, limit):
        data, _key = download_package(source, self.downloads_dir, MAX_SOURCE_BYTES,
            on_progress=self._download_progress, legacy_dirs=(self.root / "downloads",),
            on_status=lambda phase: self._progress(phase, 0), local_dir=Path(__file__).parent.parent / "assets" / "dos")
        self._progress("Extracting", 0.75)
        incoming = self._source_files(data, source)
        incoming.update(additions)
        incoming = {name: root_files.get(target + name, contents) for name, contents in incoming.items()}
        if source.get("post_install"):
            self._progress("Post-install script", 0.85)
            tools_dir = base / "UTILS" / "BIN"
            tools = ({"UTILS/BIN/" + path.name: path.read_bytes() for path in tools_dir.iterdir() if path.is_file()}
                     if tools_dir.is_dir() else {})
            incoming = run_post_install(incoming, source, tools, limit)
        return incoming

    def status(self, *, start: bool = True) -> dict:
        if start:
            self.start()
        return {"state": "building" if self.configuring else self.state, "current": self.current, "error": self.error,
                "initializing": self.initializing, "processed": self.processed, "total": self.total,
                "percent": self.percent, "phase": self.phase, "received": self.received,
                "backup": self.backup, "rebuilding": self.rebuilding}

    def c_limit(self, account_id: str | None) -> int:
        return (sum(map(len, self.files.values())) + self.overlay_limit(account_id) if account_id
                else int(self.config.get("max_c_bytes", MAX_SOURCE_BYTES)))

    def bundle(self, account_id: str | None, media_id: str = "", *, lazy: bool = False, account_name: str = "") -> tuple[bytes, dict]:
        revision, overlay, deleted, directories = self.overlay(account_id)
        files = {name: data for name, data in self.files.items() if name not in deleted}
        files.update(overlay)
        remote_files = {name: {"size": len(data), "sha256": (self.file_hashes.get(name) if name not in overlay else None)
                              or hashlib.sha256(data).hexdigest(), "base": name not in overlay}
                        for name, data in files.items()} if lazy else {}
        commands = ["@echo off", "mount c drive_c"]
        media = self.media_path(account_id, media_id) if media_id and account_id else None
        if media_id and media is None:
            raise DosError("Media not found for this account")
        if media:
            kind = "floppy" if media.suffix == ".img" else "iso"
            drive = "a" if kind == "floppy" else "d"
            commands.append(f"imgmount {drive} media/{media.name} -t {kind}")
        commands += ["config -securemode", "c:", "set PATH=C:\\FREEDOS\\BIN;Z:\\", "cls",
                     "echo THelpViewer DOS Prompt - use the DOS Prompt menu for media.",
                     "if exist C:\\AUTOEXEC.BAT call C:\\AUTOEXEC.BAT",
                     "Z:\\COMMAND.COM", "echo THelpViewer DOS session ended.", "pause >nul"]
        cycles = str(self.config.get("cycles", "auto"))
        if not re.fullmatch(r"auto|max|[0-9]{1,6}", cycles):
            raise DosError("Invalid DOS cycles setting")
        memory = int(self.config.get("memory_mb", 16))
        if not 4 <= memory <= 64:
            raise DosError("Invalid DOS memory setting")
        conf = f"[dosbox]\nmemsize={memory}\n[sdl]\nautolock=false\n[cpu]\ncycles={cycles}\n[autoexec]\n" + "\n".join(commands) + "\n"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(".jsdos/", b"")
            archive.writestr(".jsdos/dosbox.conf", conf)
            if lazy:
                archive.writestr(".jsdos/disk.json", json.dumps({"base_id": self.base_id, "account": account_name, "files": remote_files}))
            archive.writestr("drive_c/", b"")
            folders = set(directories)
            for name in [*files, *directories]:
                parts = name.split("/")
                folders.update("/".join(parts[:index]) for index in range(1, len(parts)))
            # libzip in DOSBox does not synthesise missing parent directories.
            for directory in sorted(folders, key=lambda name: (name.count("/"), name)):
                archive.writestr("drive_c/" + directory + "/", b"")
            if not lazy:
                for name, contents in sorted(files.items()):
                    archive.writestr("drive_c/" + name, contents)
        metadata = {
            "base_id": self.base_id, "revision": revision,
            "files": {name: self.file_hashes.get(name) or hashlib.sha256(data).hexdigest() for name, data in self.files.items()},
            "media": media.name if media else "", "max_c_bytes": self.c_limit(account_id),
            "max_overlay_bytes": self.overlay_limit(account_id) if account_id else 0,
            "overlay_files": list(overlay), "remote_files": remote_files,
            "allow_full_disk_fallback": self.config.get("allow_full_disk_fallback") is True,
            "max_media_bytes": self.config.get("max_media_bytes", 128 * 1024 * 1024),
        }
        return buffer.getvalue(), metadata

    def read_chunk(self, account_id: str | None, name: str, digest: str, base_file: bool, offset: int, size: int) -> bytes:
        name = c_path(name)
        if offset < 0 or not 1 <= size <= 65536:
            raise DosError("Invalid DOS file chunk")
        if base_file:
            data = self.files.get(name)
            if data is None or (self.file_hashes.get(name) or hashlib.sha256(data).hexdigest()) != digest:
                raise DosError("DOS file changed; reload the disk")
            return data[offset:offset + size]
        return self.overlays.read_chunk(account_id, name, digest, offset, size)

    def _source_files(self, data: bytes, source: dict) -> dict[str, bytes]:
        return DosPackageExtractor(int(self.config.get("max_c_bytes", MAX_SOURCE_BYTES))).extract(data, source)

    def overlay(self, account_id: str | None) -> tuple[int, dict[str, bytes], list[str], list[str]]:
        return self.overlays.overlay(account_id)

    def save(self, account_id: str, payload: dict) -> int:
        return self.overlays.save(account_id, payload, self.base_id, self.files)

    def overlay_limit(self, account_id: str | None = None) -> int:
        return self.overlays.overlay_limit(account_id)

    def disk_usage(self, account_id: str) -> dict:
        return self.overlays.disk_usage(account_id)

    def add_media(self, account_id: str, kind: str, data: bytes) -> str:
        return self.media.add_media(account_id, kind, data, int(self.config.get("max_media_bytes", 128 * 1024 * 1024)))

    def media_path(self, account_id: str, ident: str) -> Path | None:
        return self.media.media_path(account_id, ident)
