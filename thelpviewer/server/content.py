"""Administrator-selected server content installation and API progress."""

import json
import logging
import threading
from dataclasses import dataclass, field
from contextlib import closing, nullcontext
from queue import Queue
from concurrent.futures import CancelledError, ThreadPoolExecutor

from .converter.build import build_help_groups, recover_help_publication
from .converter.metadata import product_metadata_for_group
from .converter.results import ConversionError
from .downloader.service import DownloadResult, download_products, plan_help_downloads
from ..help_database import load_help_manifest
from ..help_packages import help_package_id, help_packages
from .dos.config import load_dos_config, select_dos_packages
from .json_storage import write_json
from .jobs import JobStore


class JobInterrupted(RuntimeError):
    """Stop at a safe pipeline boundary without recording a terminal failure."""


def _initial_status(phase="Queued"):
    return {"state": "building", "phase": phase, "percent": 0, "processed": 0,
            "total": 0, "file": "", "error": "", "warnings": [], "backup": ""}


def _combined_status(states):
    states = list(states)
    if not states:
        return {**_initial_status(""), "state": "idle"}
    active = [status for status in states if status["state"] == "building"]
    errors = list(dict.fromkeys(status["error"] for status in states if status.get("error")))
    state = "building" if active else "error" if errors else (
        "interrupted" if any(status["state"] == "interrupted" for status in states) else "ready")
    return {**(active[0] if active else states[-1]), "state": state,
            "phase": active[0]["phase"] if active else "Failed" if errors else "Finished",
            "percent": sum(status["percent"] for status in states) // len(states),
            "error": "; ".join(errors),
            "warnings": list(dict.fromkeys(warning for status in states for warning in status["warnings"]))}


@dataclass
class ContentJob:
    ident: str
    values: dict
    scope: set
    configured: bool
    progress: dict = field(init=False)
    worker: threading.Thread | None = None
    queued: bool = False

    def __post_init__(self):
        self.progress = {kind: _initial_status() for kind in sorted(self.scope)}

    def status(self):
        return {**_combined_status(self.progress.values()),
                "operations": {kind: dict(status) for kind, status in self.progress.items()}}


class ContentService:
    def __init__(self, config, dos, on_help_publish=None, *, help_processing=None, journal=None):
        self.config, self.dos = config, dos
        self._dos_receipt = dos.installed_path
        self.on_help_publish = on_help_publish
        self.help_processing = help_processing or nullcontext
        self.path = config.persistent_dir / "content-settings.json"
        self.sources_dir = config.sources_dir or config.state_dir / "sources"
        self.downloads_dir = config.downloads_dir or config.state_dir / "downloads"
        self._lock = threading.RLock()
        self._jobs = []
        self._pending = []
        self._active = {}
        self.journal = journal or JobStore(config.persistent_dir / "jobs.sqlite3")
        self._stop = threading.Event()
        self._repair_editions = set()
        dos.source_selection = self.selected_dos
        for kind in ("help", "dos"):
            dos.downloads.register_retry(kind,
                lambda group, failed, kind=kind: self._prepare_retry(kind, group, failed))

    def _prepare_retry(self, kind, group, failed):
        with self._lock:
            self._validate_retry(kind, group, failed)
            if any(kind in job["payload"]["scope"] for job in self.journal.pending("content")):
                raise ValueError("An unfinished content job is already queued")
            values = self.choices()["selection"]
            field = "help_packages" if kind == "help" else "dos_packages"
            # DOS publication is one disk transaction. Continue the requested
            # additions that its failure blocked, without uninstalling live C files.
            requested = (self._saved_selection() or {}).get(field, []) if kind == "dos" else []
            values[field] = sorted(set(values[field]) | set(requested) | {group})
            configured = bool((self._saved_selection() or {}).get("configured"))
            ident = self.journal.create("content", {"values": values, "scope": [kind], "configured": configured})
        return lambda: self._retry_package(kind, group, failed, ident, values, configured)

    def _validate_retry(self, kind, group, failed):
        with self._lock:
            self._check_stop()
            if kind in self._busy_scopes():
                raise ValueError("Content installation is already running")
            if kind == "dos" and self.dos.status(start=False)["state"] == "building":
                raise ValueError("Wait for the current DOS operation to finish")
            selection = self._saved_selection() or self.choices()["selection"]
            if group not in selection.get("help_packages" if kind == "help" else "dos_packages", []):
                raise ValueError("This package is no longer selected")
            if kind == "help" and failed != [group]:
                raise ValueError("Unknown failed HELP source")
            if kind == "dos" and failed != [group]:
                raise ValueError("Unknown failed DOS package")

    def _retry_package(self, kind, group, failed, ident, values, configured):
        with self._lock:
            # Configuration might have changed while the retry was being queued.
            try:
                self._validate_retry(kind, group, failed)
            except Exception as error:
                self.journal.update(ident, "interrupted" if self._stop.is_set() else "error",
                                    error="" if self._stop.is_set() else str(error))
                raise
            if not self._busy_scopes():
                self._jobs.clear()
            if kind == "dos":
                self.dos.downloads.reconcile(kind, values["dos_packages"])
                self._queue_progress(values, {kind}, self.choices(), replace=False)
            job = ContentJob(ident, values, {kind}, configured, worker=threading.current_thread(), queued=True)
            job.progress[kind].update(phase="Retrying", file=group)
            self._jobs.append(job)
            self._active[ident] = job
            pause = self.help_processing() if kind == "help" else nullcontext()
            pause.__enter__()
        self._execute_job(job, pause)
        if job.status()["state"] == "error":
            raise ValueError(job.status()["error"])

    def _dos_manifest(self):
        return load_dos_config(self.config.dos_config_path)

    def _catalog(self):
        path = self.config.helps_dir / "catalog.json"
        if not path.exists():
            return []
        entries = json.loads(path.read_text(encoding="utf-8"))
        return [{**entry, "product": entry.get("product") or product_metadata_for_group(entry.get("group", ""))[0]}
                for entry in entries if (self.config.helps_dir / entry["file"]).is_file()]

    def _installed_help_packages(self):
        return {help_package_id(entry["product"], entry.get("version", "")) for entry in self._catalog()
                if entry["product"] in load_help_manifest().product_map} - self._repair_editions

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
        if saved:
            for kind in status["scopes"]:
                field = kind + "_packages"
                selection[field] = saved.get(field, selection[field])
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
        known_help = {item["id"] for item in help_packages(self._catalog())}
        saved["help_packages"] = [ident for ident in saved.get("help_packages", []) if ident in known_help]
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
            latest = {kind: progress for job in self._jobs for kind, progress in job.progress.items()}
            for job in self._active.values():
                latest.update({kind: progress for kind, progress in job.progress.items()
                               if progress["state"] == "building"})
            status = _combined_status(latest.values())
            scopes = self._busy_scopes()
            if self._stop.is_set():
                status["state"] = "error" if status["error"] else "interrupted"
            elif scopes:
                status["state"] = "building"
            return {**status, "scopes": sorted(scopes)}

    def _busy_scopes(self):
        return {kind for job in (*self._active.values(), *self._pending) for kind in job.scope}

    def _update(self, job, kind, **values):
        with self._lock:
            job.progress[kind].update(values)
            if not self._stop.is_set():
                self.journal.update(job.ident, "running", job.status())

    def _check_stop(self):
        if self._stop.is_set():
            raise JobInterrupted("Interrupted; will resume after server restart")

    def resume(self):
        """Recover explicit unfinished requests only, never retry terminal failures."""
        with self._lock:
            if self._busy_scopes():
                return
            self._check_stop()
            choices = self.choices()
            known_help = {item["id"] for item in choices["help_packages"]}
            known_dos = {item["id"] for item in choices["dos_packages"]}
            for job in self.journal.pending("content"):
                payload = job["payload"]
                values, scope = payload["values"], set(payload["scope"])
                if (not scope or scope - {"help", "dos"}
                        or ("help" in scope and set(values["help_packages"]) - known_help)
                        or ("dos" in scope and set(values["dos_packages"]) - known_dos)):
                    self.journal.update(job["id"], "error", error="Saved job references removed manifest packages")
                    continue
                for step, record in self.journal.steps(job["id"]).items():
                    if step.startswith("help:") and not self.journal.files_valid(self.config.helps_dir, record):
                        self._repair_editions.add(step.removeprefix("help:"))
                operation = ContentJob(job["id"], values, scope, payload["configured"])
                if not scope & self._busy_scopes():
                    self._queue_progress(values, scope, choices)
                    operation.queued = True
                self._jobs.append(operation)
                self._pending.append(operation)
            if self._pending:
                self._schedule()

    def recover_publications(self):
        for job in self.journal.pending("content"):
            publication = self.journal.steps(job["id"]).get("help-publication")
            if publication:
                recover_help_publication(self.config.helps_dir, publication["detail"])

    def close(self):
        with self._lock:
            self._stop.set()
            workers = [job.worker for job in self._jobs if job.worker]
        for worker in workers:
            if worker is not threading.current_thread():
                worker.join()

    def _queue_progress(self, values, scope, choices, *, replace=True):
        if "help" in scope:
            missing = [item for item in values["help_packages"] if item not in self._installed_help_packages()]
            products = list(dict.fromkeys(item.split(":", 1)[0] for item in missing))
            self.dos.downloads.begin("help", plan_help_downloads(products, package_ids=missing), replace=replace)
        if "dos" in scope:
            packages = {item["id"]: item for item in choices["dos_packages"]}
            self.dos.downloads.begin("dos", [{"id": ident, "label": packages[ident]["label"], "byte_progress": False,
                "priority": 0 if packages[ident]["required"] else 10}
                for ident in select_dos_packages(self._dos_manifest(), values["dos_packages"])
                if not packages[ident]["installed"]],
                replace=replace)

    def _schedule(self):
        # Preserve order within a content type, not across independent disks.
        # Reserve HELP's index pause before startup can schedule its first scan.
        busy = {kind for job in self._active.values() for kind in job.scope}
        for job in list(self._pending):
            if self._stop.is_set():
                return
            blocked = bool(job.scope & busy)
            busy.update(job.scope)
            if blocked:
                continue
            if not job.queued:
                self._queue_progress(job.values, job.scope, self.choices())
                job.queued = True
            pause = self.help_processing() if "help" in job.scope else nullcontext()
            pause.__enter__()
            job.worker = threading.Thread(target=self._execute_job, args=(job, pause),
                daemon=True, name="thelp-content-" + "-".join(sorted(job.scope)))
            self._pending.remove(job)
            self._active[job.ident] = job
            job.worker.start()

    def _finish_job(self, job):
        status = job.status()
        state = "interrupted" if self._stop.is_set() else "error" if status["state"] == "error" else "done"
        self.journal.update(job.ident, state, status, status.get("error", "") if state == "error" else "")

    def start(self, help_packages=None, dos_packages=None):
        if help_packages is None and dos_packages is None:
            raise ValueError("Select HELP editions or DOS packages")
        with self._lock:
            if self._stop.is_set():
                raise ValueError("The content executor is stopped; restart the server to recover its jobs")
            scope = {key for key, value in (("help", help_packages), ("dos", dos_packages)) if value is not None}
            busy = self._busy_scopes()
            if scope & busy:
                raise ValueError("This content type is already queued or installing")
            if any(self.dos.downloads.retry_in_progress(kind) for kind in scope):
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
            if "dos" in scope and self.dos.status(start=False)["state"] == "building":
                raise ValueError("Wait for the current DOS operation to finish")
            values = {"configured": choices["configured"], "help_packages": editions,
                      "dos_packages": list(dict.fromkeys(packages))}
            self._save_selection(values)
            ident = self.journal.create("content", {"values": values, "scope": sorted(scope), "configured": choices["configured"]})
            self._queue_progress(values, scope, choices)
            if not busy:
                self._jobs.clear()
            job = ContentJob(ident, values, scope, choices["configured"], queued=True)
            self._jobs.append(job)
            self._pending.append(job)
            self._schedule()
        return self.status()

    def _execute_job(self, job, pause):
        pause_closed = threading.Event()
        def release_pause():
            if not pause_closed.is_set():
                pause_closed.set()
                pause.__exit__(None, None, None)
        def install(kind):
            try:
                self._run(job, kind)
            finally:
                if kind == "help" and len(job.scope) > 1:
                    with self._lock:
                        if not any("help" in waiting.scope for waiting in self._pending):
                            release_pause()
        try:
            self.journal.claim(job.ident)
            with self._lock:
                for progress in job.progress.values():
                    progress["phase"] = "Preparing"
                self.journal.update(job.ident, "running", job.status())
            if len(job.scope) == 1:
                install(next(iter(job.scope)))
            else:
                with ThreadPoolExecutor(max_workers=len(job.scope), thread_name_prefix="thelp-content") as executor:
                    tasks = [executor.submit(install, kind) for kind in sorted(job.scope)]
                    for task in tasks:
                        task.result()
            self._finish_job(job)
        except Exception as error:
            # A journal/storage failure must stop the executor, not silently
            # leave a dead worker advertised as running. Durable intent remains
            # queued/interrupted for recovery once storage is available again.
            logging.getLogger(__name__).exception("Content job executor stopped")
            self._stop.set()
            with self._lock:
                for status in job.progress.values():
                    status.update(state="error", phase="Job executor stopped", error=str(error))
            for kind in job.scope:
                try:
                    self.dos.downloads.interrupt(kind)
                except Exception:
                    logging.getLogger(__name__).exception("Cannot persist interrupted queue")
        finally:
            with self._lock:
                self._active.pop(job.ident, None)
                try:
                    self._schedule()
                finally:
                    release_pause()

    def _save_selection(self, values):
        write_json(self.path, values)

    def _run(self, job, kind):
        values = job.values
        unfinished = {kind}
        editions = []
        try:
            self._check_stop()
            desired, packages = values["help_packages"], values["dos_packages"]
            marker = self._dos_receipt
            receipt = json.loads(marker.read_text()) if marker.exists() else {}
            manifest = self._dos_manifest()
            known = {source["id"] for source in manifest["sources"]}
            required = {source["id"] for source in manifest["sources"] if source.get("required", False)}
            dos_changes = kind == "dos" and set(packages) != (set(receipt) & known)
            installed = self._installed_help_packages()
            editions = [key for key in desired if key not in installed] if kind == "help" else []
            products = list(dict.fromkeys(ident.split(":", 1)[0] for ident in editions))
            help_changes = kind == "help" and bool(editions or installed - set(desired))
            if help_changes:
                with self.help_processing():
                    completed = set()
                    with closing(self._help_source_batches(job, products, editions)) as batches:
                        for edition in batches:
                            self._check_stop()
                            if edition not in editions or edition in completed:
                                raise ValueError("Unknown/duplicate ready HELP edition")
                            self._publish_help(job, [edition], sorted(self._installed_help_packages() | {edition}), 95)
                            completed.add(edition)
                    self._check_stop()
                    if completed != set(editions):
                        raise ValueError("Not all requested HELP editions became ready")
                    # Uninstall unchecked editions only after all requested additions succeed.
                    if self._installed_help_packages() - set(desired):
                        self._publish_help(job, [], desired, 95)
                    self.dos.downloads.finish("help")
                    unfinished.discard("help")
            if dos_changes:
                self._check_stop()
                self.dos.configure(packages, preserve_downloads=True, on_progress=lambda status: self._update(job, kind,
                    phase=f"DOS: {status['phase']}", file=status["current"],
                    percent=int(status["percent"] * 0.95),
                    processed=status["processed"], total=status["total"], received=status["received"]))
                if self.dos.state != "ready":
                    raise ValueError(self.dos.error or "DOS installation failed")
            current = json.loads(marker.read_text()) if marker.exists() else {}
            with self._lock:
                latest = self._saved_selection() or values
                complete = job.configured or latest.get("configured", False) or (
                    set(latest["help_packages"]) == self._installed_help_packages()
                    and set(latest["dos_packages"]) - required == (set(current) & known) - required)
                self._save_selection({**latest, "configured": complete})
            for remaining in unfinished:
                self.dos.downloads.finish(remaining)
            self._update(job, kind, state="ready", phase="Finished", percent=100, file="")
        except Exception as error:
            if self._stop.is_set():
                self._update(job, kind, state="interrupted", phase="Interrupted; will resume after restart", error="")
                return
            failed_edition = getattr(error, "package_id", None)
            if failed_edition:
                self.dos.downloads.update("help", failed_edition, state="error", phase="Failed", error=str(error))
            elif "help" in unfinished and len(editions) == 1:
                self.dos.downloads.update("help", editions[0], state="error", phase="Failed", error=str(error))
            for remaining in unfinished:
                self.dos.downloads.finish(remaining, error=str(error), block_unfinished=remaining == "help")
            self._update(job, kind, state="error", error=str(error), phase="Failed")

    def _publish_help(self, job, editions, keep, end):
        groups = list(dict.fromkeys(load_help_manifest().product_map[key.split(":", 1)[0]].build_group for key in editions))
        try:
            built = build_help_groups(groups, self.sources_dir, self.config.helps_dir,
                backup_count=self.dos.settings.get()["backup_count"],
                backup_dir=self.config.state_dir / "backups" / "help", package_ids=editions, keep_packages=keep,
                on_publication=lambda detail: self._publication_checkpoint(job, detail),
                on_progress=lambda status: self._help_build_progress(job, status, editions, end))
        except Exception as error:
            if len(editions) == 1:
                raise ConversionError(str(error), package_id=editions[0]) from error
            raise
        self._update(job, "help", backup=built["backup"])
        for edition in editions:
            self._repair_editions.discard(edition)
            files = [self.config.helps_dir / row["file"] for row in self._catalog()
                     if help_package_id(row["product"], row.get("version", "")) == edition]
            self.journal.checkpoint_files(job.ident, "help:" + edition, self.config.helps_dir, files)
            self.dos.downloads.update("help", edition, state="done", percent=100, phase="Published", error="")
        if self.on_help_publish:
            self.on_help_publish()

    def _publication_checkpoint(self, job, detail):
        self.journal.checkpoint(job.ident, "help-publication", state="running", detail=detail)

    def _help_source_batches(self, job, products, editions):
        """Feed verified editions to atomic per-edition publication while inputs continue."""
        messages, stopped = Queue(), threading.Event()
        def ready(edition):
            self._check_stop()
            if stopped.is_set():
                raise CancelledError("HELP conversion stopped")
            messages.put(edition)
        def prepare():
            try:
                result = download_products(products, self.sources_dir, self.downloads_dir / "help", package_ids=editions,
                    downloads=self.dos.downloads, preserve_downloads=True, finalize=False, on_ready=ready,
                    on_progress=lambda status: self._phase_progress(job, status, 0, 35))
                messages.put(result)
            except Exception as error:
                messages.put(error)
        worker = threading.Thread(target=prepare, daemon=True, name="thelp-help-inputs")
        worker.start()
        try:
            while True:
                self._check_stop()
                message = messages.get()
                if isinstance(message, str):
                    yield message
                elif isinstance(message, Exception):
                    raise message
                else:
                    self._update(job, "help", warnings=message.warnings)
                    if message.errors:
                        raise ValueError("HELP sources unavailable: " + "; ".join(message.errors))
                    return
        finally:
            stopped.set()
            worker.join()
            # Conversion can fail before the final source message is consumed.
            # Retain provider diagnostics already collected by the producer.
            while not messages.empty():
                message = messages.get_nowait()
                if isinstance(message, DownloadResult):
                    self._update(job, "help", warnings=message.warnings)

    def _help_build_progress(self, job, status, editions, end=95):
        self._check_stop()
        self._phase_progress(job, status, 35, end)
        # Selection/catalog/publication events describe the whole transaction,
        # not a conversion happening simultaneously in every edition.
        targets = [status["product"]] if status.get("product") in editions else editions if len(editions) == 1 else []
        fraction = min(1, max(0, status.get("processed", 0)) / max(1, status.get("total", 0)))
        for edition in targets:
            self.dos.downloads.update("help", edition, state="running",
                phase=status.get("phase", "Converting"), percent=35 + int(60 * fraction),
                received=0, bytes_total=0, stage=status.get("stage", "prepare"),
                stage_percent=status.get("stage_percent"))

    def _phase_progress(self, job, status, start, end):
        self._check_stop()
        total = max(1, status.get("total", 0))
        fraction = status.get("processed", 0) / total
        if status.get("bytes_total"):
            fraction += min(1, status.get("received", 0) / status["bytes_total"]) / total
        with self._lock:
            self._update(job, "help", **status,
                percent=max(job.progress["help"]["percent"], min(end, start + int((end - start) * fraction))))
