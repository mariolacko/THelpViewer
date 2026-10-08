"""Configurable HTML indexes and resumable local MIDI downloads."""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import os
import re
import sqlite3
import tempfile
import threading
import time
import zipfile
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup


MAX_HTML_BYTES = 4 * 1024 * 1024
MAX_MIDI_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXTRACTED_BYTES = 128 * 1024 * 1024
USER_AGENT = "THelpViewer MIDI indexer (+https://thelp.zdrojak.dev/)"
SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _safe_filename(value: str) -> str:
    name = re.sub(r"[^\w. -]", "_", unquote(value), flags=re.UNICODE).strip(" .")
    return name[:100] or "track.mid"


class MidiIndexParser(HTMLParser):
    """Extract tracks using one of the declarative HTML layouts."""

    def __init__(self, rules: dict[str, object]):
        super().__init__(convert_charrefs=True)
        self.rules = rules
        self.pattern = re.compile(str(rules.get("href_pattern", r"\.(?:mid|midi|zip)$")), re.I)
        self.mode = str(rules.get("mode", "anchors"))
        if self.mode not in ("table_rows", "anchors", "download_then_heading", "selectors"):
            raise ValueError(f"Unsupported MIDI HTML extraction mode: {self.mode}")
        self._html_parts: list[str] = []
        self.items: list[dict[str, str]] = []
        self.game = ""
        self.row_class = ""
        self.cells: list[str] | None = None
        self.row_links: list[tuple[str, str]] = []
        self.anchor_href: str | None = None
        self.anchor_text: list[str] = []
        self.heading_text: list[str] | None = None
        self.pending: tuple[str, str] | None = None

    def feed(self, data: str) -> None:
        if self.mode == "selectors":
            self._html_parts.append(data)
        else:
            super().feed(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "tr" and self.mode == "table_rows":
            self._finish_row()
            self.row_class = values.get("class") or ""
            self.cells, self.row_links = [], []
        elif tag == "td" and self.cells is not None:
            self.cells.append("")
        elif tag == "a":
            self.anchor_href = values.get("href")
            self.anchor_text = []
        elif tag == self.rules.get("game_heading_tag") and self.mode == "download_then_heading":
            self.heading_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.anchor_href is not None:
            text = _clean_text("".join(self.anchor_text))
            href = self.anchor_href
            if self.pattern.search(urlsplit(href).path):
                if self.mode == "table_rows":
                    self.row_links.append((href, text))
                elif self.mode == "anchors":
                    self.items.append({"href": href, "game": "", "title": text, "sequencer": ""})
                elif text.casefold() == str(self.rules.get("download_link_text", "Download")).casefold():
                    self.pending = (href, text)
            self.anchor_href = None
            self.anchor_text = []
        elif tag == "tr" and self.mode == "table_rows":
            self._finish_row()
        elif tag == self.rules.get("game_heading_tag") and self.heading_text is not None:
            text = _clean_text("".join(self.heading_text))
            prefix = str(self.rules.get("game_prefix", "Game:"))
            if self.pending and text.casefold().startswith(prefix.casefold()):
                href, _label = self.pending
                game = _clean_text(text[len(prefix):])
                self.items.append({"href": href, "game": game, "title": game, "sequencer": ""})
                self.pending = None
            self.heading_text = None

    def handle_data(self, data: str) -> None:
        if self.cells:
            self.cells[-1] += data
        if self.anchor_href is not None:
            self.anchor_text.append(data)
        if self.heading_text is not None:
            self.heading_text.append(data)

    def _finish_row(self) -> None:
        if self.cells is None:
            return
        cells = [_clean_text(value) for value in self.cells]
        group_class = str(self.rules.get("group_row_class", ""))
        if group_class and group_class in self.row_class.split():
            index = int(self.rules.get("group_cell", 0))
            if index < len(cells):
                self.game = cells[index]
        elif self.row_links:
            href, title = self.row_links[0]
            author_index = int(self.rules.get("author_cell", -1))
            author = cells[author_index] if 0 <= author_index < len(cells) else ""
            self.items.append({"href": href, "game": self.game, "title": title, "sequencer": author})
        self.cells, self.row_links, self.row_class = None, [], ""

    def finish(self) -> list[dict[str, str]]:
        if self.mode == "selectors":
            return self._selector_items()
        self._finish_row()
        return self.items

    def _selector_items(self) -> list[dict[str, str]]:
        item_selector = str(self.rules.get("item_selector", ""))
        link_selector = str(self.rules.get("link_selector", "a[href]"))
        if not item_selector:
            raise ValueError("MIDI selector extraction needs item_selector")
        page = BeautifulSoup("".join(self._html_parts), "html.parser")
        for item in page.select(item_selector):
            link = item.select_one(link_selector)
            if link is None:
                continue
            href = str(link.get(str(self.rules.get("link_attr", "href")), ""))
            if not self.pattern.search(urlsplit(href).path):
                continue

            def field(name: str, fallback: str = "") -> str:
                selector = str(self.rules.get(f"{name}_selector", ""))
                element = item.select_one(selector) if selector else None
                if element is None:
                    return fallback
                attribute = str(self.rules.get(f"{name}_attr", ""))
                return _clean_text(str(element.get(attribute, "")) if attribute
                                   else element.get_text(" ", strip=True))

            self.items.append({
                "href": href,
                "game": field("game", str(self.rules.get("game", ""))),
                "title": field("title", _clean_text(link.get_text(" ", strip=True))),
                "sequencer": field("sequencer"),
            })
        return self.items


class _SameHostRedirect(HTTPRedirectHandler):
    def __init__(self, hosts: set[str]):
        self.hosts = hosts

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in self.hosts:
            raise ValueError("MIDI source redirected outside its configured HTTPS hosts")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class MidiLibrary:
    def __init__(self, root: Path, sources_path: Path | None):
        self.root = root
        self.sources_path = sources_path
        self._lock = threading.Lock()
        self._items: list[dict[str, object]] = []
        self._covers: dict[tuple[str, str], str] = {}
        self._state = "idle"
        self._current = ""
        self._errors: list[str] = []
        self._worker: threading.Thread | None = None
        self._priority: deque[tuple[str, str]] = deque()
        self._priority_set: set[tuple[str, str]] = set()
        self._load_catalog()

    def _load_catalog(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.root / "library.sqlite3") as database:
            database.execute("""CREATE TABLE IF NOT EXISTS midi_index (
                id TEXT PRIMARY KEY, source_id TEXT NOT NULL, game TEXT NOT NULL,
                title TEXT NOT NULL, url TEXT NOT NULL, payload TEXT NOT NULL
            )""")
            database.execute("""CREATE TABLE IF NOT EXISTS midi_covers (
                source_id TEXT NOT NULL, game TEXT NOT NULL, filename TEXT NOT NULL,
                source_url TEXT NOT NULL, rights_note TEXT NOT NULL,
                PRIMARY KEY (source_id, game)
            )""")
            database.execute("""CREATE TABLE IF NOT EXISTS midi_tracks (
                source_id TEXT NOT NULL, filename TEXT NOT NULL, game TEXT NOT NULL,
                title TEXT NOT NULL, sequencer TEXT NOT NULL, source_url TEXT NOT NULL,
                cover_filename TEXT NOT NULL,
                PRIMARY KEY (source_id, filename)
            )""")
            self._items = [json.loads(row[0]) for row in database.execute(
                "SELECT payload FROM midi_index ORDER BY source_id, game, title, id"
            )]
            self._covers = {(row[0], row[1]): row[2] for row in database.execute(
                "SELECT source_id, game, filename FROM midi_covers"
            )}
        self._sync_tracks()

    def _sync_tracks(self) -> None:
        """Keep one SQLite row per valid local MIDI, including ZIP members."""
        rows = []
        for item in self._items:
            source_id = str(item["source_id"])
            game = str(item["game"])
            members = item.get("members") or []
            for member in members if item.get("kind") == "zip" else [item]:
                filename = str(member["filename"])
                if self._is_downloaded(source_id, filename):
                    rows.append((
                        source_id, filename, game,
                        str(member.get("title") if item.get("kind") == "zip" else item["title"]),
                        str(item["sequencer"]), str(item["url"]),
                        self._covers.get((source_id, game), ""),
                    ))
        with sqlite3.connect(self.root / "library.sqlite3") as database:
            database.execute("DELETE FROM midi_tracks")
            database.executemany("""INSERT INTO midi_tracks
                (source_id, filename, game, title, sequencer, source_url, cover_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", rows)

    def _save_catalog(self) -> None:
        with sqlite3.connect(self.root / "library.sqlite3") as database:
            database.executemany("""INSERT OR REPLACE INTO midi_index
                (id, source_id, game, title, url, payload) VALUES (?, ?, ?, ?, ?, ?)""", [
                (item["id"], item["source_id"], item["game"], item["title"],
                 item["url"], json.dumps(item, ensure_ascii=False)) for item in self._items
            ])

    def _save_cover(self, source: dict[str, object], game: str, data: bytes, suffix: str, url: str) -> None:
        if len(data) > 5 * 1024 * 1024 or not (
            (suffix in (".jpg", ".jpeg") and data.startswith(b"\xff\xd8\xff"))
            or (suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        ):
            raise ValueError("ZIP cover image has an unsupported format or size")
        source_id = str(source["id"])
        filename = hashlib.sha256(f"{source_id}:{game}".encode()).hexdigest()[:24] + suffix
        directory = self.root / "covers"
        directory.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", dir=directory, delete=False) as stream:
            stream.write(data)
            temporary = Path(stream.name)
        os.replace(temporary, directory / filename)
        with sqlite3.connect(self.root / "library.sqlite3") as database:
            database.execute("""INSERT OR REPLACE INTO midi_covers
                (source_id, game, filename, source_url, rights_note) VALUES (?, ?, ?, ?, ?)""",
                (source_id, game, filename, url, str(source.get("rights_note", ""))))
        self._covers[(source_id, game)] = filename

    def _sources(self) -> list[dict[str, object]]:
        if self.sources_path is None:
            return []
        data = json.loads(self.sources_path.read_text(encoding="utf-8"))
        configured = data.get("sources")
        if not isinstance(configured, list):
            raise ValueError("MIDI sources JSON must contain a sources list")
        sources: list[dict[str, object]] = []
        for source in configured:
            if not isinstance(source, dict):
                raise ValueError("Invalid MIDI source")
            if not SOURCE_ID_RE.fullmatch(str(source.get("id", ""))) or not source.get("name"):
                raise ValueError("Invalid MIDI source ID or name")
            if source.get("enabled") is False:
                continue
            pages = source.get("pages")
            if not isinstance(pages, list) or not pages or not all(isinstance(page, str) for page in pages):
                raise ValueError(f"MIDI source {source.get('id')} needs a nonempty pages list")
            page_tokens = []
            for page in pages:
                url = urlsplit(page)
                last_path = url.path.rstrip("/").rsplit("/", 1)[-1]
                page_name = f"{last_path}-{url.query}" if url.query else last_path
                slug = re.sub(r"[^a-z0-9]+", "-", unquote(page_name).casefold()).strip("-")
                page_tokens.append(slug.split("-"))
            common_count = 0
            if len(pages) > 1:
                for tokens in zip(*page_tokens):
                    if len(set(tokens)) != 1:
                        break
                    common_count += 1
            for page, tokens in zip(pages, page_tokens):
                suffix = "-".join(tokens[common_count:]) or "0"
                sources.append({
                    **{key: value for key, value in source.items() if key != "pages"},
                    "id": f"{source['id']}-{suffix}" if len(pages) > 1 else source["id"],
                    "name": f"{source['name']} {'#' if suffix == '0' else suffix.upper()}"
                    if len(pages) > 1 else source["name"],
                    "index_url": page,
                    "source_page": page if len(pages) > 1 else source.get("source_page", page),
                })
        seen_ids: set[str] = set()
        for source in sources:
            if not isinstance(source, dict) or not SOURCE_ID_RE.fullmatch(str(source.get("id", ""))):
                raise ValueError("Invalid MIDI source ID")
            if source["id"] in seen_ids:
                raise ValueError(f"Duplicate MIDI source ID: {source['id']}")
            seen_ids.add(str(source["id"]))
            if not isinstance(source.get("extract"), dict):
                raise ValueError(f"MIDI source {source['id']} has no extraction rules")
            hosts = source.get("allowed_hosts")
            parsed = urlsplit(str(source.get("index_url", "")))
            if parsed.scheme != "https" or not isinstance(hosts, list) or parsed.hostname not in hosts:
                raise ValueError(f"MIDI source {source['id']} needs an HTTPS URL and matching allowed_hosts")
        return sources

    @staticmethod
    def _fetch(url: str, hosts: set[str], limit: int) -> bytes:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in hosts:
            raise ValueError("MIDI URL is outside its configured HTTPS hosts")
        opener = build_opener(_SameHostRedirect(hosts))
        with opener.open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("MIDI source exceeds the configured size limit")
        return data

    def _index_source(self, source: dict[str, object]) -> list[dict[str, object]]:
        hosts = set(source["allowed_hosts"])
        page = str(source["index_url"])
        html = self._fetch(page, hosts, MAX_HTML_BYTES).decode("utf-8", errors="replace")
        parser = MidiIndexParser(source["extract"])
        parser.feed(html)
        results: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in parser.finish():
            url = urljoin(page, item["href"])
            parts = urlsplit(url)
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
            if parts.scheme != "https" or parts.hostname not in hosts or url in seen:
                continue
            seen.add(url)
            kind = "zip" if parts.path.lower().endswith(".zip") else "midi"
            ident = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            basename = _safe_filename(Path(unquote(parts.path)).name)
            if kind == "midi":
                filename = f"{ident}-{basename}"
            else:
                filename = ""
            results.append({
                "id": ident, "source_id": source["id"], "url": url, "kind": kind,
                "game": item["game"], "title": item["title"] or basename,
                "sequencer": item["sequencer"], "filename": filename, "members": [],
            })
        if not results:
            raise ValueError(f"No MIDI/ZIP links found for {source['id']}")
        return results

    def _is_downloaded(self, source_id: str, filename: str) -> bool:
        if not filename:
            return False
        path = self.root / source_id / filename
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_MIDI_BYTES:
            return False
        with path.open("rb") as stream:
            return stream.read(4) == b"MThd"

    def _write_midi(self, source_id: str, filename: str, data: bytes) -> None:
        if not data.startswith(b"MThd") or len(data) > MAX_MIDI_BYTES:
            raise ValueError("Downloaded data is not a valid-size MIDI file")
        directory = self.root / source_id
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", dir=directory, delete=False) as stream:
            stream.write(data)
            temporary = Path(stream.name)
        os.replace(temporary, directory / filename)

    def _download_item(self, source: dict[str, object], item: dict[str, object]) -> bool:
        source_id = str(source["id"])
        if item["kind"] == "midi":
            if not self._is_downloaded(source_id, str(item["filename"])):
                data = self._fetch(str(item["url"]), set(source["allowed_hosts"]), MAX_MIDI_BYTES)
                self._write_midi(source_id, str(item["filename"]), data)
                return True
            return False
        members = item.get("members") or []
        if members and all(self._is_downloaded(source_id, str(member["filename"])) for member in members):
            return False
        data = self._fetch(str(item["url"]), set(source["allowed_hosts"]), MAX_ARCHIVE_BYTES)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            midi_files = [info for info in archive.infolist() if not info.is_dir()
                          and info.filename.lower().endswith((".mid", ".midi"))]
            if not midi_files or len(midi_files) > 300:
                raise ValueError("ZIP contains no MIDI files or too many entries")
            if sum(info.file_size for info in midi_files) > MAX_EXTRACTED_BYTES:
                raise ValueError("ZIP has too much expanded MIDI data")
            extracted: list[dict[str, str]] = []
            for info in midi_files:
                if info.file_size > MAX_MIDI_BYTES:
                    raise ValueError(f"ZIP MIDI is too large: {info.filename}")
                name = _safe_filename(Path(info.filename).name)
                ident = hashlib.sha256((str(item["url"]) + "!" + info.filename).encode()).hexdigest()[:16]
                filename = f"{ident}-{name}"
                with archive.open(info) as stream:
                    midi_data = stream.read(MAX_MIDI_BYTES + 1)
                self._write_midi(source_id, filename, midi_data)
                extracted.append({"filename": filename, "title": Path(name).stem})
            cover_rules = source.get("cover") or {}
            if cover_rules.get("mode") == "zip_image" and (source_id, str(item["game"])) not in self._covers:
                extensions = set(cover_rules.get("extensions") or (".jpg", ".jpeg", ".png"))
                images = [info for info in archive.infolist() if not info.is_dir()
                          and Path(info.filename).suffix.lower() in extensions and info.file_size <= 5 * 1024 * 1024]
                if images:
                    image = images[0]
                    with archive.open(image) as stream:
                        image_data = stream.read(5 * 1024 * 1024 + 1)
                    self._save_cover(source, str(item["game"]), image_data,
                                     Path(image.filename).suffix.lower(), str(item["url"]))
            item["members"] = extracted
            self._save_catalog()
            return True

    def _download_pair(self, source: dict[str, object], item: dict[str, object], sleep: bool) -> None:
        self._current = f"{source['name']}: {item['game'] or item['title']}"
        try:
            downloaded = self._download_item(source, item)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            if len(self._errors) < 20:
                self._errors.append(f"{item['title']}: {exc}")
        else:
            if sleep and downloaded:
                time.sleep(max(0.0, min(float(source.get("request_delay_seconds", 1.5)), 10.0)))

    def prioritize(self, source_id: str, item_id: str) -> bool:
        """Move a catalog item ahead of the normal download order."""
        if not SOURCE_ID_RE.fullmatch(source_id) or not re.fullmatch(r"[0-9a-f]{16}", item_id):
            return False
        if source_id not in {str(source["id"]) for source in self._sources()}:
            return False
        if not any(item.get("source_id") == source_id and item.get("id") == item_id
                   for item in self._items):
            return False
        key = (source_id, item_id)
        with self._lock:
            if key not in self._priority_set:
                self._priority.append(key)
                self._priority_set.add(key)
        self.start()
        return True

    def _next_priority(self) -> tuple[str, str] | None:
        with self._lock:
            if not self._priority:
                return None
            key = self._priority.popleft()
            self._priority_set.discard(key)
            return key

    def run_once(self, *, sleep: bool = True) -> None:
        """Refresh missing source indexes and download missing tracks; safe to resume."""
        try:
            sources = self._sources()
            self.root.mkdir(parents=True, exist_ok=True)
            self._errors = []
            self._state = "downloading"
            for source in sources:
                source_id = str(source["id"])
                if not any(item.get("source_id") == source_id for item in self._items):
                    self._current = f"Indexing {source['name']}"
                    self._items.extend(self._index_source(source))
                    self._save_catalog()
            grouped = [
                [(source, item) for item in self._items if item.get("source_id") == source["id"]]
                for source in sources
            ]
            indexed = {(str(source["id"]), str(item["id"])): (source, item)
                       for group in grouped for source, item in group}
            processed: set[tuple[str, str]] = set()

            def drain_priority() -> None:
                while key := self._next_priority():
                    pair = indexed.get(key)
                    if pair is None:
                        continue
                    self._download_pair(*pair, sleep)
                    processed.add(key)

            for batch in itertools.zip_longest(*grouped):
                for pair in batch:
                    drain_priority()
                    if pair is None:
                        continue
                    source, item = pair
                    key = (str(source["id"]), str(item["id"]))
                    if key not in processed:
                        self._download_pair(source, item, sleep)
                        processed.add(key)
            drain_priority()
            self._state = "partial" if self._errors else "ready"
        except (OSError, ValueError, KeyError, TypeError, re.error) as exc:
            self._state = "error"
            self._errors.append(str(exc))
        finally:
            self._sync_tracks()
            self._current = ""

    def start(self) -> None:
        if self.sources_path is None or (self._worker and self._worker.is_alive()):
            return
        self._worker = threading.Thread(target=self.run_once, name="thelp-midi-download", daemon=True)
        self._worker.start()

    def catalog(self) -> dict[str, object]:
        sources = self._sources()
        active_ids = {str(source["id"]) for source in sources}
        tracks: list[dict[str, object]] = []
        for item in self._items:
            source_id = str(item["source_id"])
            if source_id not in active_ids:
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
        if not SOURCE_ID_RE.fullmatch(source_id) or filename != Path(filename).name:
            return None
        if source_id not in {str(source["id"]) for source in self._sources()}:
            return None
        if not any(item.get("source_id") == source_id and (
            item.get("filename") == filename or any(
                member.get("filename") == filename for member in item.get("members", [])
            )
        ) for item in self._items):
            return None
        return self.root / source_id / filename if self._is_downloaded(source_id, filename) else None

    def cover_path(self, source_id: str, filename: str) -> Path | None:
        if not SOURCE_ID_RE.fullmatch(source_id) or filename != Path(filename).name:
            return None
        if source_id not in {str(source["id"]) for source in self._sources()}:
            return None
        if not any(key[0] == source_id and stored == filename for key, stored in self._covers.items()):
            return None
        path = self.root / "covers" / filename
        return path if path.is_file() and not path.is_symlink() else None
