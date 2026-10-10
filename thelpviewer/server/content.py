"""Administrator-selected server content installation and API progress."""

import json
import os
from pathlib import Path
import tempfile
import threading

from ..converter.build import build_help_groups
from ..downloader.service import download_products
from ..help_database import load_help_manifest
from .dos_prompt import ID_RE


class ContentService:
    def __init__(self, config, dos, on_help_publish=None):
        self.config, self.dos = config, dos
        self.on_help_publish = on_help_publish
        self.path = config.state_dir / "content-settings.json"
        self.sources_dir = config.sources_dir or config.helps_dir.parent / "sources"
        self.downloads_dir = config.downloads_dir or config.state_dir / "downloads"
        self._lock = threading.RLock()
        self._worker = None
        self._status = {"state": "idle", "phase": "", "percent": 0, "processed": 0,
                        "total": 0, "file": "", "error": "", "warnings": [], "backup": ""}
        dos.source_selection = self.selected_dos

    def _dos_sources(self):
        path = self.config.dos_config_path
        data = json.loads(path.read_text(encoding="utf-8")) if path else {"sources": []}
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            raise ValueError("DOS configuration needs a sources list")
        sources = data["sources"]
        ids = [source.get("id") if isinstance(source, dict) else None for source in sources]
        if any(not isinstance(ident, str) or not ID_RE.fullmatch(ident) for ident in ids) or len(set(ids)) != len(ids):
            raise ValueError("DOS packages need unique valid IDs")
        return sources

    def choices(self):
        manifest = load_help_manifest()
        saved = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else None
        installed = self.dos.root / "base" / "installed.json"
        dos_installed = json.loads(installed.read_text()) if installed.exists() else {}
        from ..downloader.catalog import build_group_for_help_root
        help_installed = {build_group_for_help_root(path.name) for path in self.config.helps_dir.iterdir()
                          if path.is_dir() and any(path.rglob("*.json.gz"))} if self.config.helps_dir.exists() else set()
        return {
            "configured": bool(saved and saved.get("configured")),
            "needs_setup": (not saved.get("configured") if saved else
                            not help_installed and not any(key != "_complete" for key in dos_installed)),
            "help_groups": [{"id": group.key, "label": group.label,
                             "installed": group.key in help_installed} for group in manifest.build_groups],
            "dos_packages": [{"id": source["id"], "label": source.get("title", source["id"]),
                              "installed": source["id"] in dos_installed} for source in self._dos_sources()],
            "selection": {"help_groups": saved.get("help_groups", []) if saved else sorted(help_installed - {None}),
                          "dos_packages": saved.get("dos_packages", []) if saved else [
                              source["id"] for source in self._dos_sources() if source["id"] in dos_installed]},
            "status": self.status(),
        }

    def selected_dos(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))["dos_packages"]
        # New deployments wait for explicit setup. Existing installations retain their policy.
        return None if (self.dos.root / "base" / "installed.json").exists() else []

    def status(self):
        with self._lock:
            return {**self._status, "warnings": list(self._status["warnings"])}

    def _update(self, **values):
        with self._lock:
            self._status.update(values)

    def start(self, help_groups, dos_packages):
        choices = self.choices()
        if (set(help_groups) - {item["id"] for item in choices["help_groups"]}
                or set(dos_packages) - {item["id"] for item in choices["dos_packages"]}):
            raise ValueError("Unknown HELP group or DOS package")
        with self._lock:
            if self._worker and self._worker.is_alive():
                raise ValueError("Content installation is already running")
            if self.dos.status(start=False)["state"] == "building":
                raise ValueError("Wait for the current DOS operation to finish")
            values = {"configured": False, "help_groups": list(dict.fromkeys(help_groups)),
                      "dos_packages": list(dict.fromkeys(dos_packages))}
            self._save_selection(values)
            self._status = {"state": "building", "phase": "Preparing", "percent": 0,
                            "processed": 0, "total": 0, "file": "", "error": "",
                            "warnings": [], "backup": ""}
            self._worker = threading.Thread(target=self._run, args=(values,), daemon=True,
                                            name="thelp-content-install")
            self._worker.start()
        return self.status()

    def _save_selection(self, values):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as output:
            output.write(json.dumps(values).encode())
            pending = Path(output.name)
        os.replace(pending, self.path)

    def _run(self, values):
        try:
            groups, packages = values["help_groups"], values["dos_packages"]
            if groups:
                products = [item.key for item in load_help_manifest().products if item.build_group in groups]
                downloads = download_products(products, self.sources_dir, self.downloads_dir / "help",
                    on_progress=lambda status: self._phase_progress(status, 0, 35))
                self._update(warnings=downloads.warnings)
                built = build_help_groups(groups, self.sources_dir, self.config.helps_dir,
                    on_progress=lambda status: self._phase_progress(status, 35, 70 if packages else 95))
                self._update(backup=built["backup"])
                if self.on_help_publish:
                    self.on_help_publish()
            if packages:
                self.dos.install(packages, on_progress=lambda status: self._update(
                    phase=f"DOS: {status['phase']}", file=status["current"],
                    percent=(70 if groups else 0) + int(status["percent"] * (0.25 if groups else 0.95)),
                    processed=status["processed"], total=status["total"], received=status["received"]))
                if self.dos.state != "ready":
                    raise ValueError(self.dos.error or "DOS installation failed")
            self._save_selection({**values, "configured": True})
            self._update(state="ready", phase="Finished", percent=100, file="")
        except Exception as error:
            self._update(state="error", error=str(error), phase="Failed")

    def _phase_progress(self, status, start, end):
        total = max(1, status.get("total", 0))
        fraction = status.get("processed", 0) / total
        if status.get("bytes_total"):
            fraction += min(1, status.get("received", 0) / status["bytes_total"]) / total
        self._update(**status, percent=min(end, start + int((end - start) * fraction)))
