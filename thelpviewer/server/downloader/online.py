"""Shared source-aware download queue and one urgent playback lane."""

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from itertools import count
from urllib.parse import urlsplit
import threading
import time

from .progress import DownloadProgress
from ..processing import observe_progress, stage_progress


_current = ContextVar("online_downloader", default=None)


def source_key(url):
    """Conservatively share a lane across a site's mirrors and subdomains."""
    host = (urlsplit(url).hostname or "").rstrip(".").lower()
    return ".".join(host.split(".")[-2:])


class OnlineDownloader:
    def __init__(self, journal=None):
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self._queue = []
        self._urgent_queue = []
        self._processing_queue = []
        self._urgent_processing_queue = []
        self._sources = set()
        self._transfers = set()
        self._cooldowns = {}
        self._tasks = {}
        self._sequence = count()
        self._workers = []
        self._urgent_worker = None
        self._processing_workers = []
        self._urgent_processing_worker = None
        self._closed = False
        self.progress = DownloadProgress(self._lock, journal)
        self._retry_handlers = {}
        self._retrying = set()
        self._retry_workers = set()

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
            if not separator:
                raise ValueError("This download is no longer failed; refresh the queue")
            job, failed = self.progress.failed_group(kind, group)
            if kind in self._retrying:
                raise ValueError("A retry is already running; wait for it to finish")
            if action == "remove":
                self.progress.remove_group(kind, group)
                return
            if action != "retry" or kind not in self._retry_handlers or group == "operation":
                raise ValueError("This operation cannot be retried from the download menu")
            if job["state"] == "running" or self._closed:
                raise ValueError("Wait for the current download operation to finish")
            self._retrying.add(kind)
        try:
            operation = self._retry_handlers[kind](group, failed)
            with self._lock:
                if self._closed:
                    raise ValueError("The download operation changed; refresh the queue")
                self.progress.start_retry(kind, job, failed)
            def retry():
                error = None
                try:
                    operation()
                except Exception as failure:
                    error = str(failure)
                finally:
                    with self._lock:
                        self._retrying.discard(kind)
                        try:
                            self.progress.end_retry(kind, job, failed, error)
                        finally:
                            self._retry_workers.discard(threading.current_thread())
            with self._lock:
                worker = threading.Thread(target=retry, name=f"thelp-{kind}-retry", daemon=True)
                worker.start()
                self._retry_workers.add(worker)
        except Exception:
            with self._lock:
                self._retrying.discard(kind)
            raise

    def call(self, operation, *, priority=10, identity=None, source="", check=None):
        """Queue a transfer/pipeline; nested pipeline steps use the same worker."""
        if threading.current_thread() in (*self._workers, self._urgent_worker):
            return operation()
        future = self.enqueue(operation, priority=priority, identity=identity, source=source, check=check)
        return future.result()

    def enqueue(self, operation, *, priority=10, identity=None, source="", check=None):
        return self._enqueue(operation, priority, identity, source, check, processing=False)

    def enqueue_processing(self, operation, *, priority=10, identity=None):
        """Keep local extraction/validation out of the HTTP worker/source slots."""
        return self._enqueue(operation, priority, identity, "", None, processing=True)

    def prepare(self, items, operation, *, ordered=False, source=None, priority=None):
        """Bound orchestration separately from shared HTTP and local processing.

        Waiting for a remote site must not occupy an extraction worker or keep
        another content type from submitting its independent HTTP requests.
        """
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="thelp-prepare") as executor:
            yield from self.pipeline(items,
                lambda item: executor.submit(copy_context().run, operation, item),
                ordered=ordered, source=source, priority=priority)

    def process(self, operation):
        if threading.current_thread() in (*self._processing_workers, self._urgent_processing_worker):
            return operation()
        current = _current.get()
        return self.enqueue_processing(operation, priority=current[3] if current else 10).result()

    def pipeline(self, items, submit, *, ordered=False, source=None, priority=None):
        """Bound in-flight package work; drain writers before leaving on failure."""
        pending = {}
        inputs = list(enumerate(items))
        next_order = 0
        origins = {}
        for index, item in inputs:
            value = (source(item) or "") if source else ""
            origins[index] = source_key(value) or value
        def fill():
            while len(pending) < 3 and inputs:
                active = Counter(origins[index] for index, _item in pending.values())
                with self._lock:
                    def preference(entry):
                        index, item = entry
                        origin = origins[index]
                        busy = origin in self._sources or self._cooldowns.get(origin, 0) > time.monotonic()
                        return (int(not (ordered and index == next_order)),
                                priority(item) if priority else 0, int(busy), active[origin], index)
                    entry = min(inputs, key=preference) if source or priority else inputs[0]
                inputs.remove(entry)
                pending[submit(entry[1])] = entry
        try:
            fill()
            while pending:
                ready = ([next(future for future, (index, _item) in pending.items() if index == next_order)]
                    if ordered else wait(pending, return_when=FIRST_COMPLETED).done)
                for future in ready:
                    yield pending[future][1], future
                    pending.pop(future)
                    next_order += 1
                    fill()
        finally:
            running = [future for future in pending if not future.cancel()]
            if running:
                wait(running)

    def _enqueue(self, operation, priority, identity, source, check, *, processing):
        with self._lock:
            if self._closed:
                raise RuntimeError("Downloader is stopping")
            current = _current.get()
            if current and current[5] is not None and current[5].is_set():
                future = Future()
                future.cancel()
                future.set_running_or_notify_cancel()
                return future
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
                    "source": object() if processing else source_key(source) if source else (None if priority < 0 else ""),
                    "check": check}
                if identity is not None:
                    self._tasks[identity] = task
            urgent = priority < 0
            queue = ((self._urgent_processing_queue if urgent else self._processing_queue) if processing
                     else self._urgent_queue if urgent else self._queue)
            sequence = next(self._sequence)
            queue.append((priority, -sequence if urgent else sequence, task))
            urgent_name = "_urgent_processing_worker" if processing else "_urgent_worker"
            workers = self._processing_workers if processing else self._workers
            if urgent and getattr(self, urgent_name) is None:
                worker = threading.Thread(target=self._run, args=(queue,),
                    name="thelp-urgent-processor" if processing else "thelp-urgent-downloader", daemon=True)
                setattr(self, urgent_name, worker)
                worker.start()
            elif not urgent and not workers:
                for index in range(3):
                    worker = threading.Thread(target=self._run, args=(queue,),
                        name=f"thelp-{'processor' if processing else 'online-downloader'}-{index + 1}", daemon=True)
                    workers.append(worker)
                    worker.start()
            self._changed.notify_all()
        return task["future"]

    def _cancel_task(self, task):
        if not task["claimed"] and task["future"].cancel():
            task["claimed"] = True
            task["future"].set_running_or_notify_cancel()
            identity = task["identity"]
            if identity is not None and self._tasks.get(identity) is task:
                del self._tasks[identity]

    def cancel_pending(self, kind):
        """Stop one consumer's queued steps, leaving active writers to finish."""
        with self._changed:
            for queue in (self._queue, self._urgent_queue, self._processing_queue, self._urgent_processing_queue):
                for _priority, _sequence, task in queue:
                    context = task["context"].get(_current)
                    if context and context[0] is self and context[1] == kind:
                        self._cancel_task(task)
            self._changed.notify_all()

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
                for _priority, _sequence, task in queue:
                    if task["future"].cancelled():
                        self._cancel_task(task)
                queue[:] = [entry for entry in queue if not entry[2]["claimed"] and not entry[2]["future"].cancelled()]
                for entry in list(queue):
                    task = entry[2]
                    if task["check"]:
                        try:
                            task["context"].run(task["check"])
                        except Exception as error:
                            queue.remove(entry)
                            if task["future"].set_running_or_notify_cancel():
                                task["future"].set_exception(error)
                            if task["identity"] is not None and self._tasks.get(task["identity"]) is task:
                                del self._tasks[task["identity"]]
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
            for queue in (self._queue, self._urgent_queue, self._processing_queue, self._urgent_processing_queue):
                for _priority, _sequence, task in queue:
                    self._cancel_task(task)
                queue.clear()
            self._tasks = {key: task for key, task in self._tasks.items() if not task["future"].done()}
            self._changed.notify_all()
            retries = list(self._retry_workers)
        for worker in retries:
            if worker is not threading.current_thread():
                worker.join()

    def begin(self, kind, items, *, replace=True):
        self.progress.begin(kind, items, replace=replace)

    def reconcile(self, kind, groups, *, completed=(), phase="Cached"):
        self.progress.reconcile(kind, groups, completed=completed, phase=phase)

    def update(self, kind, key, **values):
        self.progress.update(kind, key, **values)

    def finish_if_idle(self, kind):
        self.progress.finish_if_idle(kind)

    def interrupt(self, kind):
        self.progress.interrupt(kind)

    def finish(self, kind, *, error="", block_unfinished=False):
        self.progress.finish(kind, error=error, block_unfinished=block_unfinished)

    def snapshot(self, *, private=False):
        with self._lock:
            return self.progress.snapshot(private=private, retry_kinds=self._retry_handlers)

    @contextmanager
    def maintenance(self):
        """Keep new work out while idle-only download-cache maintenance runs."""
        with self._lock:
            if (self.snapshot(private=True)["active"] or self._sources or self._transfers
                    or self._retrying or any(not task["claimed"] and not task["future"].cancelled()
                        for queue in (self._queue, self._urgent_queue, self._processing_queue, self._urgent_processing_queue)
                        for _priority, _sequence, task in queue)):
                raise ValueError("Wait for downloads and processing to finish before clearing the cache")
            yield

    @contextmanager
    def activate(self):
        current = _current.get()
        token = _current.set(current if current and current[0] is self else (self, "", "", 10, 0, None))
        try:
            yield
        finally:
            _current.reset(token)

    @contextmanager
    def context(self, kind, key, *, priority=10, delay=0, cancel=None):
        token = _current.set((self, kind, str(key), priority, max(0, min(10, float(delay))), cancel))
        try:
            with observe_progress(lambda values: self.update(kind, key, state="running", **values)):
                yield
        finally:
            _current.reset(token)



_default = OnlineDownloader()


def run_download(operation, *, source="", check=None):
    current = _current.get()
    return (current[0] if current else _default).call(operation, priority=current[3] if current else 10, source=source, check=check)


def run_processing(operation):
    current = _current.get()
    return (current[0] if current else _default).process(operation)


def defer_source(url, delay):
    current = _current.get()
    (current[0] if current else _default).defer_source(url, delay)


@contextmanager
def transfer_slot(url):
    current = _current.get()
    with (current[0] if current else _default).transfer_slot(url):
        try:
            yield
        finally:
            if current and current[4]:
                current[0].defer_source(url, current[4])


def report_transfer(phase, received=0, bytes_total=0):
    current = _current.get()
    if current:
        current[0].update(current[1], current[2], state="running", phase=phase,
            received=received, bytes_total=bytes_total,
            **stage_progress("download" if phase == "Downloading" else "prepare",
                             received=received, bytes_total=bytes_total))
