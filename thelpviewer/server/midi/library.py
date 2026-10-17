"""Coordinate catalog refresh, source selection and shared queued MIDI downloads."""

from __future__ import annotations

import hashlib
import io
import itertools
import re
import sqlite3
import threading
import zipfile
from concurrent.futures import CancelledError
from contextlib import closing
from pathlib import Path

from ..rebuild import archive_rebuild_directory, prune_backups
from ..settings import ServerSettings
from ..json_storage import write_json
from ..downloader.online import OnlineDownloader
from ..downloader.transport import fetch_bytes
from ..downloader.cache import download_cached
from ..file_storage import atomic_file
from ..archives.core import ExtractionLimits, open_zip, read_zip_member
from ..processing import report_progress
from . import catalog as catalog_storage
from .format import standard_midi
from .sources import (
    SOURCE_ID_RE, safe_filename, configured_sources, source_selection,
    album_selection, album_id, album_enabled, expand_sources, index_source,
)

MAX_MIDI_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXTRACTED_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 4096
USER_AGENT = "THelpViewer MIDI indexer (+https://thelp.zdrojak.dev/)"


class MidiLibrary:
    def __init__(self, root: Path, sources_path: Path | None, *, selection_path: Path | None = None,
                 downloads=None, settings: ServerSettings | None = None):
        self.root = root
        self.sources_path = sources_path
        self.selection_path = selection_path
        self.settings = settings or ServerSettings(root.parent / "server-settings.json")
        self.downloads = downloads or OnlineDownloader()
        self._lock = threading.RLock()
        self._items: list[dict[str, object]] = []
        self._covers: dict[tuple[str, str], str] = {}
        self._state = "idle"
        self._current = ""
        self._errors: list[str] = []
        self._worker: threading.Thread | None = None
        self._play_tasks = {}
        self._download_tasks = set()
        self._stop = threading.Event()
        self._closed = False
        self._resetting = self._rebuilding = False
        self._indexing = False
        self._indexed_pages: dict[str, str] = {}
        self._processed = self._total = 0
        self._phase = ""
        self._backup = ""
        self._load_catalog()
        self.downloads.register_retry("midi", self._prepare_retry)

    def _prepare_retry(self, group, failed):
        with self._lock:
            if self._closed:
                raise ValueError("MIDI library is stopping")
            if self._resetting or self._rebuilding or self._indexing or (self._worker and self._worker.is_alive()):
                raise ValueError("Wait for the current MIDI operation to finish")
            if ":" not in group:
                sources = self._sources([source["id"] for source in self._configured_sources()])
                pairs = [(source, None) for source in sources if source["id"] == group]
                if failed != [group] or not pairs:
                    raise ValueError("Unknown MIDI source index")
            else:
                sources = {source["id"]: source for source in self._sources()}
                albums = self._album_selection()
                pairs = [(sources[item["source_id"]], item) for item in self._items
                    if item["source_id"] in sources and f"{item['source_id']}:{item['id']}" in failed
                    and (f"{sources[item['source_id']]['provider_id']}:{album_id(item)}" == group
                         or group == f"track:{item['source_id']}:{item['id']}")
                    and album_enabled(item, sources[item["source_id"]], albums)]
                if len(pairs) != len(failed):
                    raise ValueError("This MIDI album is no longer selected or available")
        return lambda: self._retry_pairs(group, failed, pairs)

    def _retry_pairs(self, group, failed, pairs):
        # Claim the library writer before retrying, without starting run_once over
        # all albums or downloading disabled sources as a side effect.
        with self._lock:
            self._prepare_retry(group, failed)
            self._worker = threading.current_thread()
            self._state, self._phase = "downloading", "Retrying MIDI"
            self._processed, self._total = 0, len(pairs)
            self._stop.clear()
        try:
            for source, item in pairs:
                if self._stop.is_set():
                    raise ValueError("MIDI selection changed; retry stopped")
                if item is None:
                    with self.downloads.context("midi", source["id"], priority=0):
                        self.downloads.update("midi", source["id"], state="running", phase="Indexing source", stage="index")
                        self._ensure_index(source)
                        self.downloads.update("midi", source["id"], state="done", percent=100, phase="Indexed")
                else:
                    self._download_pair(source, item, False, priority=-10 if group.startswith("track:") else 0)
                self._processed += 1
        except Exception as error:
            for key in failed:
                self.downloads.update("midi", key, state="error", phase="Failed", error=str(error))
            raise
        finally:
            self._sync_tracks()
            self._current = ""
            self._errors = self._catalog_errors()
            for row in self.downloads.snapshot()["items"]:
                if (row["kind"] == "midi" and row["error"]
                        and not any(row["error"] in error for error in self._errors)):
                    self._errors.append(row["error"])
            self._errors = self._errors[:20]
            self._state = "partial" if self._errors else "ready"

    def rebuild(self) -> None:
        """Stop the old writer before replacing catalog, tracks and covers."""
        with self._lock:
            if self._closed:
                raise ValueError("MIDI library is stopping")
            if self._rebuilding or self._resetting or self._indexing:
                raise ValueError("MIDI rebuild or source change is already running")
            old_worker = self._worker
            self._resetting = self._rebuilding = True
            self._stop.set()
            self._phase = "Stopping downloader"
            self._backup = ""
            self._worker = threading.Thread(target=self._run_rebuild, args=(old_worker,),
                                            name="thelp-midi-rebuild", daemon=True)
            self._worker.start()

    def _run_rebuild(self, old_worker: threading.Thread | None) -> None:
        try:
            backup_count = self.settings.get()["backup_count"]
            self._stop_downloads()
            if old_worker and old_worker.is_alive():
                old_worker.join()
            with self._lock:
                if self._closed:
                    return
                archived = archive_rebuild_directory(self.root, self.root.parent / "backups" / "midi", "midi")
                self._backup = str(archived.relative_to(self.root.parent)) if archived else ""
                self._items, self._covers, self._errors = [], {}, []
                self._processed = self._total = 0
                self._load_catalog()
                self._stop.clear()
                self._resetting = False
            self.run_once()
            if self._state == "ready" and not self._stop.is_set() and self._backup:
                prune_backups(self.root.parent / self._backup, ("midi-",), backup_count)
        except (OSError, ValueError, sqlite3.Error) as error:
            self._state = "error"
            self._errors = [str(error)]
        finally:
            self._resetting = self._rebuilding = False

    def rebuild_status(self) -> dict[str, object]:
        state = "building" if self._rebuilding or self._resetting or self._indexing else self._state
        if state == "downloading":
            state = "building"
        percent = 100 if state == "ready" else min(99, int(100 * self._processed / max(1, self._total)))
        if self._resetting:
            percent = 0
        return {"state": state, "phase": self._phase,
                "processed": self._processed, "total": self._total, "percent": percent,
                "file": self._current, "error": self._errors[0] if self._errors and state in {"error", "partial"} else "",
                "backup": self._backup, "rebuilding": self._rebuilding, "indexing": self._indexing}

    def _page_indexed(self, source) -> bool:
        previous = self._indexed_pages.get(source["id"])
        return previous == source["index_url"] or (previous is None
            and any(item.get("source_id") == source["id"] for item in self._items))

    def _ensure_index(self, source) -> None:
        if self._indexed_pages.get(source["id"]) == source["index_url"]:
            return
        if not self._page_indexed(source):
            self._current = f"Indexing {source['name']}"
            self._items.extend(self._index_source(source))
            self._save_catalog()
        with sqlite3.connect(self.root / "library.sqlite3") as database:
            database.execute("INSERT OR REPLACE INTO midi_pages (source_id,url) VALUES (?,?)",
                             (source["id"], source["index_url"]))
        self._indexed_pages[source["id"]] = source["index_url"]

    def source_choices(self) -> dict[str, object]:
        configured = self._configured_sources()
        selected = self._source_selection()
        album_selection = self._album_selection()
        pages = self._sources([source["id"] for source in configured])
        page_map = {source["id"]: source for source in pages}
        grouped = {source["id"]: {} for source in configured}
        for item in self._items:
            source = page_map.get(item["source_id"])
            if source is None:
                continue
            provider = source["provider_id"]
            ident = album_id(item)
            grouped[provider].setdefault(ident, {"id": ident,
                "name": str(item.get("game") or item["title"]),
                "selected": album_selection.get(provider) is None or ident in album_selection[provider]})
        return {"sources": [{"id": source["id"], "name": source["name"],
                "selected": source["id"] in selected if selected is not None else source.get("enabled") is not False,
                "all_albums": album_selection.get(source["id"]) is None,
                "albums": sorted(grouped[source["id"]].values(), key=lambda album: (album["name"].casefold(), album["id"])),
                "indexed": all(self._page_indexed(page) for page in pages if page["provider_id"] == source["id"])}
                for source in configured], "status": self.rebuild_status()}

    def select_sources(self, selected: list[str], albums: dict[str, list[str] | None]) -> None:
        """Persist manifest IDs and resume with cached files after the old writer stops."""
        configured_ids = {source["id"] for source in self._configured_sources()}
        if len(selected) != len(set(selected)) or any(item not in configured_ids for item in selected):
            raise ValueError("Unknown or duplicate MIDI source ID")
        if set(albums) - configured_ids:
            raise ValueError("Unknown MIDI album provider")
        choices = {source["id"]: {album["id"] for album in source["albums"]}
                   for source in self.source_choices()["sources"]}
        for provider, ids in albums.items():
            if ids is not None and (len(ids) > 10000 or len(ids) != len(set(ids)) or set(ids) - choices[provider]):
                raise ValueError("Unknown or duplicate MIDI album ID")
        self._sources(selected)  # Validate selected providers before committing the selection.
        if self.selection_path is None:
            raise ValueError("MIDI source selection storage is not configured")
        with self._lock:
            if self._closed:
                raise ValueError("MIDI library is stopping")
            if self._resetting or self._rebuilding or self._indexing:
                raise ValueError("MIDI rebuild or source change is already running")
            write_json(self.selection_path, {"sources": selected, "albums": albums})
            old_worker = self._worker
            self._resetting = True
            self._stop.set()
            self._phase = "Changing MIDI sources"
            self._worker = threading.Thread(target=self._run_source_selection, args=(old_worker,),
                                            name="thelp-midi-selection", daemon=True)
            self._worker.start()

    def _run_source_selection(self, old_worker: threading.Thread | None) -> None:
        self._stop_downloads()
        if old_worker and old_worker.is_alive():
            old_worker.join()
        with self._lock:
            if self._closed:
                return
            self._stop.clear()
            self._resetting = False
        try:
            self.run_once()
        except (OSError, ValueError, sqlite3.Error) as error:
            self._state = "error"
            self._errors = [str(error)]

    def index_source(self, provider: str) -> None:
        if provider not in {source["id"] for source in self._configured_sources()}:
            raise ValueError("Unknown MIDI source ID")
        pages = self._sources([provider])
        with self._lock:
            if self._closed:
                raise ValueError("MIDI library is stopping")
            if self._resetting or self._rebuilding or self._indexing:
                raise ValueError("MIDI rebuild or source change is already running")
            old_worker = self._worker
            self._indexing = self._resetting = True
            self._stop.set()
            self._phase = "Preparing MIDI album index"
            self._worker = threading.Thread(target=self._run_album_index, args=(old_worker, pages),
                                            name="thelp-midi-albums", daemon=True)
            self._worker.start()

    def _run_album_index(self, old_worker, pages) -> None:
        try:
            self._stop_downloads()
            if old_worker and old_worker.is_alive():
                old_worker.join()
            with self._lock:
                if self._closed:
                    return
                self._stop.clear()
                self._resetting = False
            self._errors = []
            self._state = "indexing"
            self._phase = "Indexing MIDI albums"
            self._processed, self._total = 0, len(pages)
            self.downloads.begin("midi", [{"id": page["id"], "label": page["name"], "byte_progress": False} for page in pages])
            for page in pages:
                if self._stop.is_set():
                    return
                with self.downloads.context("midi", page["id"]):
                    self.downloads.update("midi", page["id"], state="running", phase="Indexing albums", stage="index")
                    self._ensure_index(page)
                    self.downloads.update("midi", page["id"], state="done", percent=100, phase="Indexed")
                self._processed += 1
        except (OSError, ValueError, sqlite3.Error, KeyError, TypeError, re.error) as error:
            self._errors = [str(error)]
            self._state = "error"
            self.downloads.finish("midi", error=str(error))
            with self._lock:
                self._indexing = self._resetting = False
            return
        with self._lock:
            self._indexing = False
        self.downloads.finish("midi")
        self.run_once()

    def _fetch(self, url: str, hosts: set[str], limit: int) -> bytes:
        with self.downloads.activate():
            return fetch_bytes(url, hosts, limit, user_agent=USER_AGENT)

    def _is_downloaded(self, source_id: str, filename: str) -> bool:
        if not filename:
            return False
        path = self.root / source_id / filename
        try:
            if not path.is_file() or path.is_symlink() or not 22 <= path.stat().st_size <= MAX_MIDI_BYTES:
                return False
            with path.open("rb") as stream:
                return stream.read(4) == b"MThd"
        except OSError:
            return False

    def _write_midi(self, source_id: str, filename: str, data: bytes) -> None:
        data = standard_midi(data, limit=MAX_MIDI_BYTES)
        with atomic_file(self.root / source_id / filename) as stream:
            stream.write(data)

    def _item_downloaded(self, source_id, item) -> bool:
        if item["kind"] == "midi":
            return self._is_downloaded(source_id, str(item["filename"]))
        members = item.get("members") or []
        return bool(members) and all(not member.get("error")
            and self._is_downloaded(source_id, str(member["filename"])) for member in members)

    def _download_item(self, source: dict[str, object], item: dict[str, object]) -> bool:
        source_id = str(source["id"])
        if self._item_downloaded(source_id, item):
            return False
        limit = MAX_MIDI_BYTES if item["kind"] == "midi" else MAX_ARCHIVE_BYTES
        cache = self.root.parent / "downloads" / "midi" / (
            hashlib.sha256(str(item["url"]).encode()).hexdigest() + "-" + safe_filename(str(item["url"]).rsplit("/", 1)[-1]))
        def fetch(path):
            data = self._fetch(str(item["url"]), set(source["allowed_hosts"]), limit)
            with atomic_file(path) as stream:
                stream.write(data)
        return download_cached(cache, limit, fetch,
            process=lambda path: self._process_item(source, item, path.read_bytes()))

    def _process_item(self, source, item, data):
        source_id = str(source["id"])
        if item["kind"] == "midi":
            report_progress("Converting MIDI", str(item["filename"]), stage="convert")
            self._write_midi(source_id, str(item["filename"]), data)
            return True
        report_progress("Extracting MIDI album", str(item["game"]), stage="extract")
        with open_zip(data, ExtractionLimits(max_files=MAX_ARCHIVE_ENTRIES, max_bytes=MAX_EXTRACTED_BYTES)) as archive:
            midi_files = [info for info in archive.infolist() if not info.is_dir()
                          and info.filename.lower().endswith((".mid", ".midi"))]
            if not midi_files:
                raise ValueError("ZIP contains no MIDI files")
            if sum(info.file_size for info in midi_files) > MAX_EXTRACTED_BYTES:
                raise ValueError("ZIP has too much expanded MIDI data")
            extracted: list[dict[str, str]] = []
            errors = []
            for index, info in enumerate(midi_files):
                name = safe_filename(Path(info.filename).name)
                ident = hashlib.sha256((str(item["url"]) + "!" + info.filename).encode()).hexdigest()[:16]
                filename = f"{ident}-{name}"
                member = {"filename": filename, "title": Path(name).stem}
                extracted.append(member)
                try:
                    if info.file_size > MAX_MIDI_BYTES:
                        raise ValueError("ZIP MIDI exceeds its size limit")
                    midi_data = read_zip_member(archive, info, MAX_MIDI_BYTES)
                    report_progress("Converting MIDI", info.filename, stage="convert",
                                    processed=index, total=len(midi_files))
                    self._write_midi(source_id, filename, midi_data)
                    report_progress("Converting MIDI", info.filename, stage="convert",
                                    processed=index + 1, total=len(midi_files))
                except (ValueError, zipfile.BadZipFile) as error:
                    member["error"] = str(error)
                    errors.append(f"{info.filename}: {error}")
            cover_rules = source.get("cover") or {}
            if cover_rules.get("mode") == "zip_image" and (source_id, str(item["game"])) not in self._covers:
                extensions = set(cover_rules.get("extensions") or (".jpg", ".jpeg", ".png"))
                images = [info for info in archive.infolist() if not info.is_dir()
                          and Path(info.filename).suffix.lower() in extensions and info.file_size <= 5 * 1024 * 1024]
                if images:
                    image = images[0]
                    image_data = read_zip_member(archive, image, 5 * 1024 * 1024)
                    self._save_cover(source, str(item["game"]), image_data,
                                     Path(image.filename).suffix.lower(), str(item["url"]))
            report_progress("Publishing MIDI album", str(item["game"]), stage="publish")
            item["members"] = extracted
            self._save_catalog()
            if errors:
                details = "; ".join(errors[:3])
                if len(errors) > 3:
                    details += f"; and {len(errors) - 3} more rejected files"
                raise ValueError(f"{len(errors)}/{len(midi_files)} MIDI files rejected: {details}")
            return True

    def _queue_download(self, source, item, *, priority=10):
        key = f"{source['id']}:{item['id']}"
        label = f"{source['name']}: {item['game'] or item['title']}"
        with self._lock:
            if self._closed or self._resetting:
                raise ValueError("MIDI configuration is changing")
            self.downloads.begin("midi", [{"id": key, "label": label,
                "group": f"{source['provider_id']}:{album_id(item)}"}], replace=False)
            if priority < 0:
                self.downloads.update("midi", key, group=f"track:{key}", priority=priority,
                    label=f"{source['name']}: {item['game']} — {item['title']}" if item['game'] else f"{source['name']}: {item['title']}")

            def operation():
                if self._stop.is_set():
                    self.downloads.update("midi", key, state="blocked", phase="Selection changed")
                    self.downloads.finish_if_idle("midi")
                    return False
                self.downloads.update("midi", key, state="running", phase="Downloading", stage="download")
                try:
                    try:
                        downloaded = self._download_item(source, item)
                    finally:
                        if priority < 0:
                            self._sync_tracks()
                    with self._lock:
                        if item.pop("download_error", None) is not None:
                            self._save_catalog()
                    self.downloads.update("midi", key, state="done", percent=100,
                        phase="Downloaded" if downloaded else "Cached", error="")
                    return downloaded
                except CancelledError:
                    self.downloads.update("midi", key, state="blocked", phase="Selection changed")
                    raise
                except Exception as error:
                    with self._lock:
                        item["download_error"] = str(error)
                        self._save_catalog()
                    self.downloads.update("midi", key, state="error", phase="Failed", error=str(error))
                    raise
                finally:
                    self.downloads.finish_if_idle("midi")

            with self.downloads.context("midi", key, priority=priority,
                    delay=source.get("request_delay_seconds", 1.5), cancel=self._stop):
                task = self.downloads.enqueue_processing(operation, priority=priority, identity=("midi", key))
            self._download_tasks = {pending for pending in self._download_tasks if not pending.done()}
            self._download_tasks.add(task)
            return task

    def _download_pair(self, source: dict[str, object], item: dict[str, object], sleep: bool, *, priority=10) -> None:
        self._current = f"{source['name']}: {item['game'] or item['title']}"
        self._complete_download(source, item, self._queue_download(source, item, priority=priority), sleep)

    def _complete_download(self, source, item, task, sleep):
        try:
            downloaded = task.result()
        except CancelledError:
            if not self._stop.is_set():
                raise
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            if len(self._errors) < 20:
                self._errors.append(f"{item['title']}: {exc}")
        else:
            if sleep and downloaded:
                self._stop.wait(max(0.0, min(float(source.get("request_delay_seconds", 1.5)), 10.0)))

    def prioritize(self, source_id: str, item_id: str) -> bool:
        """Submit an allowed catalog item to the shared urgent playback lane."""
        if self._closed or self._resetting or not SOURCE_ID_RE.fullmatch(source_id) or not re.fullmatch(r"[0-9a-f]{16}", item_id):
            return False
        sources = {str(source["id"]): source for source in self._sources()}
        if source_id not in sources:
            return False
        albums = self._album_selection()
        item = next((item for item in self._items if item.get("source_id") == source_id and item.get("id") == item_id
                     and album_enabled(item, sources[source_id], albums)), None)
        if item is None:
            return False
        if self._item_downloaded(source_id, item):
            return True
        with self._lock:
            if self._closed or self._resetting:
                return False
            self._play_tasks = {key: task for key, task in self._play_tasks.items() if not task.done()}
            self._play_tasks[(source_id, item_id)] = self._queue_download(sources[source_id], item, priority=-10)
        return True

    def _stop_downloads(self):
        with self._lock:
            tasks = list(self._download_tasks)
        for task in tasks:
            task.cancel()
        self.downloads.cancel_pending("midi")
        for task in tasks:
            try:
                task.result()
            except Exception:
                pass
        with self._lock:
            self._play_tasks.clear()
            self._download_tasks.clear()

    @staticmethod
    def _item_error(item):
        if item.get("download_error"):
            return str(item["download_error"])
        # ZIP member diagnostics also describe failures recorded before a whole
        # download finished; they must not turn into automatic startup retries.
        return "; ".join(f"{member['title']}: {member['error']}"
                         for member in item.get("members", []) if member.get("error"))

    def _catalog_errors(self):
        sources = {source["id"]: source for source in self._sources()}
        albums = self._album_selection()
        return [f"{item['title']}: {error}" for item in self._items
                if item["source_id"] in sources and album_enabled(item, sources[item["source_id"]], albums)
                and (error := self._item_error(item))][:20]

    def run_once(self, *, sleep: bool = True, retry_failed: bool = True) -> None:
        """Refresh missing source indexes and download missing tracks; safe to resume."""
        if self._closed:
            return
        try:
            sources = self._sources()
            albums = self._album_selection()
            self.root.mkdir(parents=True, exist_ok=True)
            self._errors = []
            self._state = "downloading"
            self._phase = "Indexing sources"
            unindexed = [source for source in sources
                         if self._indexed_pages.get(source["id"]) != source["index_url"]]
            self._processed, self._total = 0, len(unindexed)
            if unindexed:
                self.downloads.begin("midi", [{"id": source["id"], "label": source["name"], "byte_progress": False}
                    for source in unindexed], replace=False)
            for index, source in enumerate(unindexed):
                if self._stop.is_set():
                    return
                with self.downloads.context("midi", source["id"], cancel=self._stop):
                    self.downloads.update("midi", source["id"], state="running", phase="Indexing source", stage="index")
                    self._ensure_index(source)
                    self.downloads.update("midi", source["id"], state="done", percent=100, phase="Indexed")
                self._processed = index + 1
            selected = [
                [(source, item) for item in self._items if item.get("source_id") == source["id"]
                 and album_enabled(item, source, albums)]
                for source in sources
            ]
            completed = {f"{source['id']}:{item['id']}" for group in selected for source, item in group
                         if not self._item_error(item) and self._item_downloaded(str(source["id"]), item)}
            self.downloads.reconcile("midi", {
                group for pairs in selected for source, item in pairs for group in (
                    f"{source['provider_id']}:{album_id(item)}", f"track:{source['id']}:{item['id']}")},
                completed=completed)
            grouped = [[(source, item) for source, item in group
                        if f"{source['id']}:{item['id']}" not in completed
                        and (retry_failed or not self._item_error(item))] for group in selected]
            indexed = {(str(source["id"]), str(item["id"])): (source, item)
                       for group in grouped for source, item in group}
            if indexed:
                self.downloads.begin("midi", [{"id": f"{source['id']}:{item['id']}",
                    "label": f"{source['name']}: {item['game'] or item['title']}",
                    "group": f"{source['provider_id']}:{album_id(item)}"}
                    for source, item in indexed.values()], replace=False)
            processed: set[tuple[str, str]] = set()
            self._phase = "Downloading MIDI"
            self._processed, self._total = 0, len(indexed)

            pairs = []
            for batch in itertools.zip_longest(*grouped):
                for pair in batch:
                    if pair is not None:
                        source, item = pair
                        key = (str(source["id"]), str(item["id"]))
                        if key not in processed:
                            pairs.append(pair)
                            processed.add(key)
            def submit(pair):
                if self._stop.is_set():
                    raise CancelledError("MIDI selection changed")
                return self._queue_download(*pair)
            with closing(self.downloads.pipeline(pairs, submit)) as pending:
                for (source, item), task in pending:
                    if self._stop.is_set():
                        return
                    self._current = f"{source['name']}: {item['game'] or item['title']}"
                    self._complete_download(source, item, task, sleep)
                    self._processed += 1
            self._errors = self._catalog_errors()
            self._state = "partial" if self._errors else "ready"
        except CancelledError:
            if not self._stop.is_set():
                self._state = "error"
                self._errors.append("MIDI download was cancelled")
        except (OSError, ValueError, KeyError, TypeError, re.error) as exc:
            self._state = "error"
            self._errors.append(str(exc))
        finally:
            self.downloads.finish("midi", error=self._errors[0] if self._state == "error" and self._errors else "")
            self._sync_tracks()
            self._current = ""

    def start(self) -> None:
        with self._lock:
            if (self._closed or self.sources_path is None or self._resetting or self.downloads.retry_in_progress("midi")
                    or (self._worker and self._worker.is_alive())):
                return
            self._stop.clear()
            self._worker = threading.Thread(target=self.run_once, kwargs={"retry_failed": False},
                                            name="thelp-midi-download", daemon=True)
            self._worker.start()

    def close(self) -> None:
        """Quiesce every MIDI writer before its shared downloader is closed."""
        with self._lock:
            self._closed = True
            self._stop.set()
            worker = self._worker
        self._stop_downloads()
        if worker and worker is not threading.current_thread():
            worker.join()

    def catalog(self) -> dict[str, object]:
        if self._resetting:
            return {"state": "rebuilding", "current": self._phase, "downloaded": 0,
                    "total": 0, "errors": [], "tracks": [], "sources": []}
        sources = self._sources()
        active = {str(source["id"]): source for source in sources}
        albums = self._album_selection()
        with self._lock:
            pending = {key for key, task in self._play_tasks.items() if not task.done()}
        tracks: list[dict[str, object]] = []
        for item in self._items:
            source_id = str(item["source_id"])
            if source_id not in active or not album_enabled(item, active[source_id], albums):
                continue
            members = item.get("members") or []
            candidates = members if item.get("kind") == "zip" and members else [item]
            for member in candidates:
                filename = str(member.get("filename") or "")
                available = self._is_downloaded(source_id, filename)
                tracks.append({
                    "id": str(item["id"]) if member is item else f"{item['id']}:{filename}",
                    "item_id": str(item["id"]), "source_id": source_id,
                    "title": str(member.get("title") if item.get("kind") == "zip" else item["title"]),
                    "game": str(item["game"]), "credit": str(item["game"] or source_id),
                    "sequencer": str(item["sequencer"]),
                    "available": available,
                    "download_error": "" if available or (source_id, str(item["id"])) in pending else str(
                        member.get("error") or item.get("download_error") or ""),
                    "file": f"/api/midi/files/{source_id}/{filename}" if available else "",
                    "source_url": str(item["url"]),
                    "cover": (
                        f"/api/midi/covers/{source_id}/{self._covers[(source_id, str(item['game']))]}"
                        if (source_id, str(item["game"])) in self._covers else ""
                    ),
                })
        return {
            "state": self._state, "current": self._current,
            "downloaded": sum(bool(track["available"]) for track in tracks),
            "total": len(tracks), "errors": list(self._errors), "tracks": tracks,
            "sources": [
                {key: str(source.get(key, "")) for key in ("id", "name", "source_page", "rights_note")}
                for source in sources
            ],
        }

    def file_path(self, source_id: str, filename: str) -> Path | None:
        if self._resetting or not SOURCE_ID_RE.fullmatch(source_id) or filename != Path(filename).name:
            return None
        sources = {str(source["id"]): source for source in self._sources()}
        if source_id not in sources:
            return None
        albums = self._album_selection()
        if not any(item.get("source_id") == source_id and album_enabled(item, sources[source_id], albums) and (
            item.get("filename") == filename or any(
                member.get("filename") == filename for member in item.get("members", [])
            )
        ) for item in self._items):
            return None
        return self.root / source_id / filename if self._is_downloaded(source_id, filename) else None

    def cover_path(self, source_id: str, filename: str) -> Path | None:
        if self._resetting or not SOURCE_ID_RE.fullmatch(source_id) or filename != Path(filename).name:
            return None
        sources = {str(source["id"]): source for source in self._sources()}
        if source_id not in sources:
            return None
        albums = self._album_selection()
        if not any(item.get("source_id") == source_id and album_enabled(item, sources[source_id], albums)
                   and self._covers.get((source_id, str(item["game"]))) == filename for item in self._items):
            return None
        path = self.root / "covers" / filename
        return path if path.is_file() and not path.is_symlink() else None

    def _load_catalog(self) -> None:
        self._items, self._covers, self._indexed_pages = catalog_storage.load_catalog(self.root)
        self._sync_tracks()

    def _sync_tracks(self) -> None:
        with self._lock:
            catalog_storage.sync_tracks(self.root, self._items, self._covers, self._is_downloaded)

    def _save_catalog(self) -> None:
        with self._lock:
            catalog_storage.save_catalog(self.root, self._items)

    def _save_cover(self, source: dict[str, object], game: str, data: bytes, suffix: str, url: str) -> None:
        with self._lock:
            self._covers[(str(source["id"]), game)] = catalog_storage.save_cover(self.root, source, game, data, suffix, url)

    def _configured_sources(self) -> list[dict[str, object]]:
        return configured_sources(self.sources_path)

    def _source_selection(self) -> list[str] | None:
        return source_selection(self.selection_path)

    def _album_selection(self) -> dict[str, list[str] | None]:
        return album_selection(self.selection_path)

    def _sources(self, selected: list[str] | None = None) -> list[dict[str, object]]:
        return expand_sources(self.sources_path, self.selection_path, selected)

    def _index_source(self, source: dict[str, object]) -> list[dict[str, object]]:
        return index_source(source, self._fetch)
