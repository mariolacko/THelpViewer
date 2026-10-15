"""Shared source-aware download queue and one urgent playback lane."""

from concurrent.futures import Future
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from itertools import count
from urllib.parse import urlsplit
import threading
import time


_current = ContextVar("online_downloader", default=None)


def source_key(url):
    """Conservatively share a lane across a site's mirrors and subdomains."""
    host = (urlsplit(url).hostname or "").rstrip(".").lower()
    return ".".join(host.split(".")[-2:])


class OnlineDownloader:
    def __init__(self):
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self._queue = []
        self._urgent_queue = []
        self._sources = set()
        self._transfers = set()
        self._cooldowns = {}
        self._tasks = {}
        self._sequence = count()
        self._workers = []
        self._urgent_worker = None
        self._closed = False
        self._jobs = {}
        self._batch = 0
        self._retry_handlers = {}
        self._retrying = set()

    def register_retry(self, kind, prepare):
        """A consumer validates a known failed group and returns its retry pipeline."""
        with self._lock:
            self._retry_handlers[kind] = prepare

    def retry_in_progress(self, kind):
        with self._lock:
            return kind in self._retrying

    def act(self, ident, action):
        kind, separator, group = ident.partition(":")
        with self._lock:
            job = self._jobs.get(kind)
            items = [item for item in job["items"].values() if item["group"] == group] if job else []
            failed = [item["id"] for item in items if item["state"] == "error"]
            if not separator or not failed or any(item["state"] == "running" for item in items):
                raise ValueError("This download is no longer failed; refresh the queue")
            if kind in self._retrying:
                raise ValueError("A retry is already running; wait for it to finish")
            if action == "remove":
                # Forget the runtime row, never its cached/installed files or selection.
                for item in items:
                    del job["items"][item["id"]]
                return
            if action != "retry" or kind not in self._retry_handlers or group == "operation":
                raise ValueError("This operation cannot be retried from the download menu")
            if job["state"] == "running" or self._closed:
                raise ValueError("Wait for the current download operation to finish")
            self._retrying.add(kind)
        try:
            operation = self._retry_handlers[kind](group, failed)
            with self._lock:
                if self._jobs.get(kind) is not job or self._closed:
                    raise ValueError("The download operation changed; refresh the queue")
                self._start_batch(kind)
                for key in failed:
                    job["items"][key].update(state="pending", phase="Retrying", percent=0,
                        received=0, bytes_total=0, error="", batch=self._batch)
                job["state"] = "running"
                job["retrying"] = True
            def retry():
                try:
                    operation()
                except Exception as error:
                    with self._lock:
                        if self._jobs.get(kind) is job:
                            for key in failed:
                                self.update(kind, key, state="error", phase="Failed", error=str(error))
                finally:
                    with self._lock:
                        self._retrying.discard(kind)
                        if self._jobs.get(kind) is job:
                            job.pop("retrying", None)
                            self.finish(kind)
            threading.Thread(target=retry, name=f"thelp-{kind}-retry", daemon=True).start()
        except Exception:
            with self._lock:
                self._retrying.discard(kind)
            raise

    def call(self, operation, *, priority=10, identity=None, source=""):
        """Queue a transfer/pipeline; nested pipeline steps use the same worker."""
        if threading.current_thread() in (*self._workers, self._urgent_worker):
            return operation()
        future = self.enqueue(operation, priority=priority, identity=identity, source=source)
        return future.result()

    def enqueue(self, operation, *, priority=10, identity=None, source=""):
        with self._lock:
            if self._closed:
                raise RuntimeError("Downloader is stopping")
            task = self._tasks.get(identity) if identity is not None else None
            if task and not task["future"].done():
                if task["claimed"] or priority >= task["priority"]:
                    return task["future"]
                task.update(priority=priority, context=copy_context())
                if not source and not task["source"] and priority < 0:
                    task["source"] = None
            else:
                task = {"future": Future(), "context": copy_context(), "operation": operation,
                    "priority": priority, "claimed": False, "identity": identity,
                    "source": source_key(source) if source else (None if priority < 0 else "")}
                if identity is not None:
                    self._tasks[identity] = task
            urgent = priority < 0
            queue = self._urgent_queue if urgent else self._queue
            sequence = next(self._sequence)
            queue.append((priority, -sequence if urgent else sequence, task))
            if urgent and self._urgent_worker is None:
                self._urgent_worker = threading.Thread(target=self._run, args=(queue,),
                    name="thelp-urgent-downloader", daemon=True)
                self._urgent_worker.start()
            elif not urgent and not self._workers:
                for index in range(3):
                    worker = threading.Thread(target=self._run, args=(queue,),
                        name=f"thelp-online-downloader-{index + 1}", daemon=True)
                    self._workers.append(worker)
                    worker.start()
            self._changed.notify_all()
        return task["future"]

    def submit(self, source, limit, *, kind, key, label, destination=None, process=None, priority=10):
        """Submit a URL/form definition with an optional extraction/install step."""
        with self._lock:
            self._start_batch(kind)
            job = self._jobs.setdefault(kind, {"state": "running", "items": {}})
            job["state"] = "running"
            job["items"][str(key)] = {"id": str(key), "label": label, "group": str(key),
                "state": "pending", "phase": "Waiting", "percent": 0, "received": 0, "bytes_total": 0, "error": "", "batch": self._batch}
            self.update(kind, key, priority=priority)
        def operation():
            from .transport import fetch_source
            from .cache import atomic_download
            self.update(kind, key, state="running", phase="Downloading")
            try:
                if destination is not None and (destination.is_symlink() or destination.parent.is_symlink()):
                    raise ValueError("Download cache must not contain symbolic links")
                if destination is not None and destination.exists():
                    if destination.is_symlink() or not destination.is_file() or destination.stat().st_size > limit:
                        raise ValueError("Invalid download cache entry")
                    data = destination.read_bytes()
                    self.update(kind, key, phase="Cached")
                else:
                    data = fetch_source(source, limit,
                        lambda received, total: self.update(kind, key, received=received, bytes_total=total),
                        on_status=lambda phase: self.update(kind, key, phase=phase))
                    if destination is not None:
                        with atomic_download(destination) as output:
                            output.write(data)
                if process:
                    self.update(kind, key, phase="Processing")
                    data = process(data)
                self.update(kind, key, state="done", percent=100, phase="Finished")
                return data
            except Exception as error:
                self.update(kind, key, state="error", error=str(error), phase="Failed")
                raise
            finally:
                with self._lock:
                    if all(item["state"] in {"done", "error"} for item in self._jobs[kind]["items"].values()):
                        self.finish(kind)
        with self.context(kind, key, priority=priority):
            return self.enqueue(operation, priority=priority, source=source["url"])

    def defer_source(self, url, delay):
        with self._changed:
            key = source_key(url)
            self._cooldowns[key] = max(self._cooldowns.get(key, 0), time.monotonic() + delay)
            self._changed.notify_all()

    @contextmanager
    def transfer_slot(self, url):
        # Redirects/form actions can use a different server than the queued URL.
        key = source_key(url)
        with self._changed:
            while key in self._transfers:
                self._changed.wait()
            self._transfers.add(key)
        try:
            yield
        finally:
            with self._changed:
                self._transfers.discard(key)
                self._changed.notify_all()

    def _next(self, queue):
        with self._changed:
            while not self._closed:
                now = time.monotonic()
                queue[:] = [entry for entry in queue if not entry[2]["claimed"] and not entry[2]["future"].cancelled()]
                available = [entry for entry in queue if entry[2]["source"] not in self._sources
                    and self._cooldowns.get(entry[2]["source"], 0) <= now
                    and (queue is self._urgent_queue or not any(not urgent[2]["claimed"]
                        and not urgent[2]["future"].cancelled() and urgent[2]["source"] == entry[2]["source"]
                        for urgent in self._urgent_queue))]
                if available:
                    entry = min(available, key=lambda value: value[:2])
                    queue.remove(entry)
                    task = entry[2]
                    task["claimed"] = True
                    self._sources.add(task["source"])
                    return task
                delays = [self._cooldowns[entry[2]["source"]] - now for entry in queue
                    if self._cooldowns.get(entry[2]["source"], 0) > now]
                self._changed.wait(min(delays) if delays else None)
            return None

    def _run(self, queue):
        while True:
            task = self._next(queue)
            if task is None:
                return
            try:
                future = task["future"]
                if future.set_running_or_notify_cancel():
                    try:
                        future.set_result(task["context"].run(task["operation"]))
                    except Exception as error:
                        future.set_exception(error)
            finally:
                with self._changed:
                    self._sources.discard(task["source"])
                    identity = task["identity"]
                    if identity is not None and self._tasks.get(identity) is task:
                        del self._tasks[identity]
                    self._changed.notify_all()

    def close(self):
        with self._lock:
            self._closed = True
            for queue in (self._queue, self._urgent_queue):
                for _priority, _sequence, task in queue:
                    task["future"].cancel()
                queue.clear()
            self._tasks = {key: task for key, task in self._tasks.items() if not task["future"].done()}
            self._changed.notify_all()

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
                    "percent": 0, "phase": "Waiting", "received": 0, "bytes_total": 0, "error": "", "batch": self._batch}
                if (key in previous and previous[key].get("batch") == self._batch
                        and (not replace or previous[key].get("priority", 10) < 0)):
                    unit = previous[key]
                job["items"][key] = unit

    def update(self, kind, key, **values):
        with self._lock:
            item = self._jobs.get(kind, {}).get("items", {}).get(str(key))
            if item is None:
                return
            if values.get("bytes_total"):
                values["percent"] = min(99, int(100 * values.get("received", 0) / values["bytes_total"]))
            if "percent" in values:
                values["percent"] = max(0, min(100, int(values["percent"])))
            if values.get("priority", 10) < 0:
                values["order"] = next(self._sequence)
            item.update(values)

    def finish_if_idle(self, kind):
        with self._lock:
            job = self._jobs.get(kind)
            if job and all(item["state"] not in {"pending", "running"} for item in job["items"].values()):
                self.finish(kind)

    def finish(self, kind, *, error=""):
        with self._lock:
            job = self._jobs.get(kind)
            if job is None:
                return
            job["state"] = "error" if error or any(item["state"] == "error" for item in job["items"].values()) else "ready"
            for item in job["items"].values():
                if item["state"] == "running":
                    item.update(state="error" if error else "done", error=error, percent=item["percent"] if error else 100)
                elif error and item["state"] == "pending":
                    item.update(state="blocked", phase="Not started")
            if error and not any(item["state"] == "error" for item in job["items"].values()):
                job["items"]["operation"] = {"id": "operation", "group": "operation", "label": "Operation",
                    "state": "error", "percent": 0, "phase": "Failed", "received": 0, "bytes_total": 0, "error": error, "batch": self._batch}
            if job.get("retrying"):
                job["state"] = "running"

    @contextmanager
    def activate(self):
        current = _current.get()
        token = _current.set(current if current and current[0] is self else (self, "", "", 10))
        try:
            yield
        finally:
            _current.reset(token)

    @contextmanager
    def context(self, kind, key, *, priority=10):
        token = _current.set((self, kind, str(key), priority))
        try:
            yield
        finally:
            _current.reset(token)

    def snapshot(self, *, private=False):
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
            for group in groups.values():
                items = group.pop("items")
                states = {item["state"] for item in items}
                state = ("running" if "running" in states else "error" if "error" in states
                         else "pending" if "pending" in states else "blocked" if "blocked" in states else "done")
                current = next((item for item in items if item["state"] == "running"), items[-1])
                rows.append({**group, "state": state, "percent": int(sum(item["percent"] for item in items) / len(items)),
                    "priority": min(item.get("priority", 10) for item in items),
                    "order": max(item.get("order", 0) for item in items),
                    "retryable": state == "error" and jobs[group["kind"]]["state"] != "running"
                        and group["kind"] in self._retry_handlers and group["id"] != f"{group['kind']}:operation",
                    "phase": current["phase"], "error": next((item["error"] for item in items if item["error"]), ""),
                    "processed": sum(item["state"] in {"done", "error"} for item in items), "total": len(items)})
            rows.sort(key=lambda row: (row["priority"], -row["order"]))
            completed = not active_items and all(item["state"] == "done" for item in progress_items)
            return {"active": bool(active_items),
                "percent": min(99 if active_items else 100, int(sum(item["percent"] for item in progress_items) / len(progress_items))) if progress_items and not completed else 0,
                "errors": sum(row["state"] == "error" for row in rows), "items": rows}


_default = OnlineDownloader()


def run_download(operation, *, source=""):
    current = _current.get()
    return (current[0] if current else _default).call(operation, priority=current[3] if current else 10, source=source)


def defer_source(url, delay):
    current = _current.get()
    (current[0] if current else _default).defer_source(url, delay)


@contextmanager
def transfer_slot(url):
    current = _current.get()
    with (current[0] if current else _default).transfer_slot(url):
        yield


def report_transfer(phase, received=0, bytes_total=0):
    current = _current.get()
    if current:
        current[0].update(current[1], current[2], state="running", phase=phase,
            received=received, bytes_total=bytes_total)
