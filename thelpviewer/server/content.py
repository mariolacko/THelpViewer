"""Administrator-selected server content installation and API progress."""

import json
import threading

from .converter.build import build_help_groups
from .converter.writers.bundle import _product_metadata_for_group
from .downloader.service import download_products
from ..help_database import load_help_manifest
from ..help_packages import help_package_id, help_packages
from .dos.config import load_dos_config, select_dos_packages
from .json_storage import write_json


class ContentService:
    def __init__(self, config, dos, on_help_publish=None):
        self.config, self.dos = config, dos
        self._dos_receipt = dos.installed_path
        self.on_help_publish = on_help_publish
        self.path = config.persistent_dir / "content-settings.json"
        self.sources_dir = config.sources_dir or config.helps_dir.parent / "sources"
        self.downloads_dir = config.downloads_dir or config.state_dir / "downloads"
        self._lock = threading.RLock()
        self._worker = None
        self._status = {"state": "idle", "phase": "", "percent": 0, "processed": 0,
                        "total": 0, "file": "", "error": "", "warnings": [], "backup": ""}
        dos.source_selection = self.selected_dos
        for kind in ("help", "dos"):
            dos.downloads.register_retry(kind,
                lambda group, failed, kind=kind: self._prepare_retry(kind, group, failed))

    def _prepare_retry(self, kind, group, failed):
        with self._lock:
            if self._worker and self._worker.is_alive():
                raise ValueError("Content installation is already running")
            if self.dos.status(start=False)["state"] == "building":
                raise ValueError("Wait for the current DOS operation to finish")
            selection = self._saved_selection() or self.choices()["selection"]
            if group not in selection.get("help_packages" if kind == "help" else "dos_packages", []):
                raise ValueError("This package is no longer selected")
            if kind == "help" and any(not key.endswith(":" + group) for key in failed):
                raise ValueError("Unknown failed HELP source")
            if kind == "dos" and failed != [group]:
                raise ValueError("Unknown failed DOS package")
        return lambda: self._retry_package(kind, group, failed)

    def _retry_package(self, kind, group, failed):
        with self._lock:
            # Configuration might have changed while the retry was being queued.
            self._prepare_retry(kind, group, failed)
            self._worker = threading.current_thread()
            self._status = {"state": "building", "phase": "Retrying", "percent": 0,
                "processed": 0, "total": 0, "file": group, "error": "", "warnings": [], "backup": ""}
        try:
            if kind == "help":
                product_key = group.split(":", 1)[0]
                result = download_products([product_key], self.sources_dir, self.downloads_dir / "help", package_ids=[group],
                    source_keys=[key.split(":", 1)[0] for key in failed],
                    downloads=self.dos.downloads, preserve_downloads=True,
                    on_progress=lambda status: self._phase_progress(status, 0, 35))
                self._update(warnings=result.warnings)
                product = load_help_manifest().product_map[product_key]
                built = build_help_groups([product.build_group], self.sources_dir, self.config.helps_dir,
                    backup_count=self.dos.settings.get()["backup_count"],
                    package_ids=[group], keep_packages=sorted(self._installed_help_packages() | {group}),
                    on_progress=lambda status: self._phase_progress(status, 35, 95))
                self._update(backup=built["backup"])
                if self.on_help_publish:
                    self.on_help_publish()
            else:
                marker = self.dos.installed_path
                installed = json.loads(marker.read_text()) if marker.exists() else {}
                known = {source["id"] for source in self._dos_manifest()["sources"]}
                # Retry one package, retaining the published disk, not applying other
                # pending installs or removals from a previous failed configuration.
                self.dos.configure(sorted((set(installed) & known) | {group}), preserve_downloads=True,
                    on_progress=lambda status: self._update(phase=status["phase"], file=status["current"],
                        percent=status["percent"], processed=status["processed"], total=status["total"]))
            self._update(state="ready", phase="Finished", percent=100, file="")
        except Exception as error:
            self._update(state="error", phase="Failed", error=str(error))
            raise

    def _dos_manifest(self):
        return load_dos_config(self.config.dos_config_path)

    def _catalog(self):
        path = self.config.helps_dir / "catalog.json"
        if not path.exists():
            return []
        entries = json.loads(path.read_text(encoding="utf-8"))
        return [{**entry, "product": entry.get("product") or _product_metadata_for_group(entry.get("group", ""))[0]}
                for entry in entries if (self.config.helps_dir / entry["file"]).is_file()]

    def _installed_help_packages(self):
        return {help_package_id(entry["product"], entry.get("version", "")) for entry in self._catalog()
                if entry["product"] in load_help_manifest().product_map}

    def choices(self):
        dos_manifest = self._dos_manifest()
        saved = self._saved_selection()
        installed = self._dos_receipt
        dos_installed = json.loads(installed.read_text()) if installed.exists() else {}
        catalog = self._catalog()
        help_installed = self._installed_help_packages()
        packages = help_packages(catalog)
        configured = bool(saved and saved.get("configured"))
        status = self.status()
        selection = {"help_packages": sorted(help_installed), "dos_packages": [
            source["id"] for source in dos_manifest["sources"] if source["id"] in dos_installed]}
        # Saved requests support explicit retries, but are not installation receipts.
        # Show a running job's target; after success/failure/restart show live content.
        if saved and status["state"] == "building":
            selection = {"help_packages": saved.get("help_packages", sorted(help_installed)),
                         "dos_packages": saved.get("dos_packages", [])}
        selection["dos_packages"] = select_dos_packages(dos_manifest, selection["dos_packages"])
        return {
            "configured": configured,
            "needs_setup": not configured and not help_installed and not any(
                not key.startswith("_") for key in dos_installed),
            "help_categories": [{"id": name, "label": name} for name in dict.fromkeys(item["category"] for item in packages)],
            "help_packages": [{**item, "installed": item["id"] in help_installed} for item in packages],
            "dos_categories": dos_manifest["categories"],
            "dos_packages": [{"id": source["id"], "label": source.get("title", source["id"]),
                              "category": source.get("category", "other"),
                              "description": source.get("description", ""),
                              "language": source.get("language", "und"),
                              "required": source.get("required", False),
                              "installed": source["id"] in dos_installed} for source in dos_manifest["sources"]],
            "selection": selection,
            "status": status,
        }

    def _saved_selection(self):
        if not self.path.exists():
            return None
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        manifest = self._dos_manifest()
        known = {source["id"] for source in manifest["sources"]}
        saved["dos_packages"] = select_dos_packages(manifest,
            [ident for ident in saved.get("dos_packages", []) if ident in known])
        return saved

    def selected_dos(self):
        saved = self._saved_selection()
        if saved:
            return saved["dos_packages"]
        # New deployments wait for explicit setup. Existing installations retain their policy.
        return None if self.dos.installed_path.exists() else select_dos_packages(self._dos_manifest(), [])

    def status(self):
        with self._lock:
            return {**self._status, "warnings": list(self._status["warnings"])}

    def _update(self, **values):
        with self._lock:
            self._status.update(values)

    def start(self, help_packages=None, dos_packages=None):
        if help_packages is None and dos_packages is None:
            raise ValueError("Select HELP editions or DOS packages")
        with self._lock:
            if self._worker and self._worker.is_alive():
                raise ValueError("Content installation is already running")
            if any(self.dos.downloads.retry_in_progress(kind) for kind in ("help", "dos")):
                raise ValueError("Wait for the current package retry to finish")
            choices = self.choices()
            requested = self._saved_selection() or choices["selection"]
            editions = list(dict.fromkeys(help_packages if help_packages is not None else
                requested.get("help_packages", choices["selection"]["help_packages"])))
            if set(editions) - {item["id"] for item in choices["help_packages"]}:
                raise ValueError("Unknown HELP edition")
            packages = dos_packages if dos_packages is not None else requested["dos_packages"]
            if set(packages) - {item["id"] for item in choices["dos_packages"]}:
                raise ValueError("Unknown HELP group or DOS package")
            packages = select_dos_packages(self._dos_manifest(), packages)
            if self.dos.status(start=False)["state"] == "building":
                raise ValueError("Wait for the current DOS operation to finish")
            values = {"configured": choices["configured"], "help_packages": editions,
                      "dos_packages": list(dict.fromkeys(packages))}
            self._save_selection(values)
            self._status = {"state": "building", "phase": "Preparing", "percent": 0,
                            "processed": 0, "total": 0, "file": "", "error": "",
                            "warnings": [], "backup": ""}
            scope = {key for key, value in (("help", help_packages), ("dos", dos_packages)) if value is not None}
            self._worker = threading.Thread(target=self._run, args=(values, scope, choices["configured"]), daemon=True,
                                            name="thelp-content-install")
            self._worker.start()
        return self.status()

    def _save_selection(self, values):
        write_json(self.path, values)

    def _run(self, values, scope, already_configured):
        try:
            desired, packages = values["help_packages"], values["dos_packages"]
            marker = self.dos.installed_path
            receipt = json.loads(marker.read_text()) if marker.exists() else {}
            manifest = self._dos_manifest()
            known = {source["id"] for source in manifest["sources"]}
            required = {source["id"] for source in manifest["sources"] if source.get("required", False)}
            dos_changes = "dos" in scope and set(packages) != (set(receipt) & known)
            installed = self._installed_help_packages()
            editions = [key for key in desired if key not in installed]
            products = list(dict.fromkeys(ident.split(":", 1)[0] for ident in editions))
            help_changes = "help" in scope and bool(editions or installed - set(desired))
            if help_changes:
                downloads = download_products(products, self.sources_dir, self.downloads_dir / "help", package_ids=editions,
                    downloads=self.dos.downloads,
                    on_progress=lambda status: self._phase_progress(status, 0, 35))
                self._update(warnings=downloads.warnings)
                groups = list(dict.fromkeys(load_help_manifest().product_map[key].build_group for key in products))
                built = build_help_groups(groups, self.sources_dir, self.config.helps_dir,
                    backup_count=self.dos.settings.get()["backup_count"],
                    package_ids=editions, keep_packages=desired,
                    on_progress=lambda status: self._phase_progress(status, 35, 70 if dos_changes else 95))
                self._update(backup=built["backup"])
                if self.on_help_publish:
                    self.on_help_publish()
            if dos_changes:
                self.dos.configure(packages, on_progress=lambda status: self._update(
                    phase=f"DOS: {status['phase']}", file=status["current"],
                    percent=(70 if help_changes else 0) + int(status["percent"] * (0.25 if help_changes else 0.95)),
                    processed=status["processed"], total=status["total"], received=status["received"]))
                if self.dos.state != "ready":
                    raise ValueError(self.dos.error or "DOS installation failed")
            current = json.loads(marker.read_text()) if marker.exists() else {}
            complete = already_configured or (("help" in scope or set(desired) == self._installed_help_packages())
                and ("dos" in scope or set(packages) - required == (set(current) & known) - required))
            self._save_selection({**values, "configured": complete})
            self._update(state="ready", phase="Finished", percent=100, file="")
        except Exception as error:
            self._update(state="error", error=str(error), phase="Failed")

    def _phase_progress(self, status, start, end):
        total = max(1, status.get("total", 0))
        fraction = status.get("processed", 0) / total
        if status.get("bytes_total"):
            fraction += min(1, status.get("received", 0) / status["bytes_total"]) / total
        self._update(**status, percent=max(self.status()["percent"], min(end, start + int((end - start) * fraction))))
