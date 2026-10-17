"""Thread-safe download lifecycle, batch percentages and public/private snapshots."""

from itertools import count


class DownloadProgress:
    def __init__(self, lock, journal=None):
        self._lock = lock
        self.journal = journal
        self._jobs = journal.load_queue() if journal else {}
        self._batch = max((job.pop("batch", 0) for job in self._jobs.values()), default=0)
        self._sequence = count(1 + max((item.get("order", 0) for job in self._jobs.values()
                                      for item in job["items"].values()), default=0))
        for job in self._jobs.values():
            if job["state"] == "running":
                job["state"] = "interrupted"
                for item in job["items"].values():
                    if item["state"] in {"pending", "running"}:
                        item.update(state="pending", phase="Interrupted; awaiting recovery")

    def _persist(self, kind):
        if self.journal:
            job = self._jobs[kind]
            self.journal.save_queue(kind, job["state"], self._batch, job["items"].values())

    def failed_group(self, kind, group):
        with self._lock:
            job = self._jobs.get(kind)
            items = [item for item in job["items"].values() if item["group"] == group] if job else []
            failed = [item["id"] for item in items if item["state"] in {"error", "blocked"}]
            if not failed or any(item["state"] == "running" for item in items):
                raise ValueError("This download is no longer failed; refresh the queue")
            return job, failed

    def remove_group(self, kind, group):
        with self._lock:
            job, _failed = self.failed_group(kind, group)
            job["items"] = {key: item for key, item in job["items"].items() if item["group"] != group}
            self._persist(kind)

    def start_retry(self, kind, job, failed):
        with self._lock:
            if self._jobs.get(kind) is not job:
                raise ValueError("The download operation changed; refresh the queue")
            self._start_batch(kind)
            for key in failed:
                job["items"][key].update(state="pending", phase="Retrying", percent=0,
                    stage="prepare", stage_percent=None, received=0, bytes_total=0, error="", batch=self._batch)
            job.update(state="running", retrying=True)
            self._persist(kind)

    def end_retry(self, kind, job, failed, error=None):
        with self._lock:
            if self._jobs.get(kind) is not job:
                return
            if error is not None:
                for key in failed:
                    self.update(kind, key, state="error", phase="Failed", error=error)
            job.pop("retrying", None)
            self.finish(kind)

    def _start_batch(self, kind):
        """Keep completed rows out of the next counter, not out of history."""
        if not any(job["state"] == "running" for job in self._jobs.values()):
            self._batch += 1
        elif self._jobs.get(kind, {}).get("state") != "running":
            # Public MIDI progress must restart even while private work continues.
            for item in self._jobs.get(kind, {}).get("items", {}).values():
                item.pop("batch", None)

    def begin(self, kind, items, *, replace=True):
        with self._lock:
            self._start_batch(kind)
            previous = self._jobs.get(kind, {}).get("items", {})
            if replace or kind not in self._jobs:
                self._jobs[kind] = {"state": "running", "items": {}}
            job = self._jobs[kind]
            job["state"] = "running"
            for item in items:
                key = str(item["id"])
                unit = {"id": key, "label": str(item["label"]),
                    "group": str(item.get("group", item["id"])), "state": "pending",
                    "byte_progress": item.get("byte_progress", True),
                    "stage": "prepare", "stage_percent": None,
                    "percent": 0, "phase": "Waiting", "received": 0, "bytes_total": 0, "error": "", "batch": self._batch}
                if (key in previous and previous[key].get("batch") == self._batch
                        and (not replace or previous[key].get("priority", 10) < 0)):
                    unit = previous[key]
                job["items"][key] = unit
            self._persist(kind)

    def reconcile(self, kind, groups, *, completed=(), phase="Cached"):
        """Check existing rows against domain selection/receipts without starting work."""
        with self._lock:
            job = self._jobs.get(kind)
            if job is None:
                return
            groups = set(groups)
            items = {key: item for key, item in job["items"].items() if item["group"] in groups}
            changed = len(items) != len(job["items"])
            for key in completed:
                item = items.get(key)
                if item is not None and item["state"] != "done":
                    item.update(state="done", percent=100, phase=phase, stage="prepare",
                                stage_percent=None, error="")
                    changed = True
            if changed:
                job["items"] = items
                if job["state"] != "running" and not any(
                        item["state"] == "pending" for item in items.values()):
                    job["state"] = "error" if any(item["state"] == "error" for item in items.values()) else "ready"
                self._persist(kind)

    def update(self, kind, key, **values):
        with self._lock:
            item = self._jobs.get(kind, {}).get("items", {}).get(str(key))
            if item is None:
                return
            if "phase" in values or "stage" in values:
                values.setdefault("stage", "prepare")
                values.setdefault("stage_percent", None)
            # A compound unit can perform many HTTP requests (HTML discovery,
            # archives, covers). One response's size is not that unit's total.
            # Its owner reports explicit stage progress or completes the unit.
            if item.get("byte_progress", True) and values.get("bytes_total") and "percent" not in values:
                values["percent"] = min(99, int(100 * values.get("received", 0) / values["bytes_total"]))
            if "percent" in values:
                values["percent"] = max(0, min(100, int(values["percent"])))
            if values.get("priority", 10) < 0:
                values["order"] = next(self._sequence)
            before = tuple(item.get(key) for key in ("state", "phase", "stage", "stage_percent", "percent", "error"))
            item.update(values)
            after = tuple(item.get(key) for key in ("state", "phase", "stage", "stage_percent", "percent", "error"))
            if self.journal and before != after:
                self.journal.save_queue_item(kind, item)

    def finish_if_idle(self, kind):
        with self._lock:
            job = self._jobs.get(kind)
            if job and all(item["state"] not in {"pending", "running"} for item in job["items"].values()):
                self.finish(kind)

    def interrupt(self, kind):
        with self._lock:
            job = self._jobs.get(kind)
            if not job or job["state"] != "running":
                return
            job["state"] = "interrupted"
            for item in job["items"].values():
                if item["state"] in {"pending", "running"}:
                    item.update(state="pending", phase="Interrupted; awaiting recovery")
            self._persist(kind)

    def finish(self, kind, *, error="", block_unfinished=False):
        with self._lock:
            job = self._jobs.get(kind)
            if job is None:
                return
            job["state"] = "error" if error or any(item["state"] == "error" for item in job["items"].values()) else "ready"
            for item in job["items"].values():
                if error and block_unfinished and item["state"] in {"running", "pending"}:
                    item.update(state="blocked", phase="Not published", error="")
                elif item["state"] == "running":
                    item.update(state="error" if error else "done", error=error, percent=item["percent"] if error else 100)
                elif error and item["state"] == "pending":
                    item.update(state="blocked", phase="Not started")
            if error and not any(item["state"] == "error" for item in job["items"].values()):
                job["items"]["operation"] = {"id": "operation", "group": "operation", "label": "Operation",
                    "state": "error", "percent": 0, "phase": "Failed", "received": 0, "bytes_total": 0, "error": error, "batch": self._batch}
            if job.get("retrying"):
                job["state"] = "running"
            self._persist(kind)

    def snapshot(self, *, private=False, retry_kinds=()):
        def percent(units):
            return sum(100 if item["state"] == "done" else min(99, item["percent"])
                       for item in units) / len(units)

        with self._lock:
            jobs = {kind: job for kind, job in self._jobs.items() if private or kind == "midi"}
            progress_items = [item for job in jobs.values() for item in job["items"].values()
                              if item.get("batch") == self._batch]
            active_items = [item for job in jobs.values() if job["state"] == "running"
                            for item in job["items"].values() if item.get("batch") == self._batch]
            groups = {}
            for kind, job in jobs.items():
                for item in job["items"].values():
                    group = groups.setdefault((kind, item["group"]), {"id": f"{kind}:{item['group']}",
                        "kind": kind, "label": item["label"], "items": []})
                    group["items"].append(item)
            rows = []
            progress_groups = []
            for group in groups.values():
                items = group.pop("items")
                current_batch = [item for item in items if item.get("batch") == self._batch]
                if current_batch:
                    progress_groups.append(percent(current_batch))
                states = {item["state"] for item in items}
                state = ("running" if "running" in states else "error" if "error" in states
                         else "pending" if "pending" in states else "blocked" if "blocked" in states else "done")
                current = next((item for item in items if item["state"] == "running"), items[-1])
                rows.append({**group, "state": state, "percent": int(percent(items)),
                    "priority": min(item.get("priority", 10) for item in items),
                    "order": max(item.get("order", 0) for item in items),
                    "retryable": state in {"error", "blocked"} and jobs[group["kind"]]["state"] != "running"
                        and group["kind"] in retry_kinds and group["id"] != f"{group['kind']}:operation",
                    "phase": current["phase"], "error": next((item["error"] for item in items if item["error"]), ""),
                    "stage": current.get("stage", "prepare"),
                    "stage_percent": current.get("stage_percent"),
                    "processed": sum(item["state"] in {"done", "error"} for item in items), "total": len(items)})
            rows.sort(key=lambda row: (row["priority"], -row["order"]))
            completed = not active_items and all(item["state"] == "done" for item in progress_items)
            return {"active": bool(active_items),
                "percent": min(99 if active_items else 100, int(sum(progress_groups) / len(progress_groups))) if progress_groups and not completed else 0,
                "errors": sum(row["state"] == "error" for row in rows), "items": rows}
