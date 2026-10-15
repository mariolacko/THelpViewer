"""SQLite MIDI indexes, local-track inventory and source-provided covers."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


def load_catalog(root: Path) -> tuple[list[dict], dict[tuple[str, str], str], dict[str, str]]:
    root.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(root / "library.sqlite3") as database:
        database.execute("CREATE TABLE IF NOT EXISTS midi_pages (source_id TEXT PRIMARY KEY, url TEXT NOT NULL)")
        indexed_pages = dict(database.execute("SELECT source_id,url FROM midi_pages"))
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
        items = [json.loads(row[0]) for row in database.execute(
            "SELECT payload FROM midi_index ORDER BY source_id, game, title, id"
        )]
        covers = {(row[0], row[1]): row[2] for row in database.execute(
            "SELECT source_id, game, filename FROM midi_covers"
        )}
    return items, covers, indexed_pages


def sync_tracks(root: Path, items, covers, is_downloaded) -> None:
    """Keep one SQLite row per valid local MIDI, including ZIP members."""
    rows = []
    for item in items:
        source_id = str(item["source_id"])
        game = str(item["game"])
        members = item.get("members") or []
        for member in members if item.get("kind") == "zip" else [item]:
            filename = str(member["filename"])
            if is_downloaded(source_id, filename):
                rows.append((
                    source_id, filename, game,
                    str(member.get("title") if item.get("kind") == "zip" else item["title"]),
                    str(item["sequencer"]), str(item["url"]),
                    covers.get((source_id, game), ""),
                ))
    with sqlite3.connect(root / "library.sqlite3") as database:
        database.execute("DELETE FROM midi_tracks")
        database.executemany("""INSERT INTO midi_tracks
            (source_id, filename, game, title, sequencer, source_url, cover_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", rows)


def save_catalog(root: Path, items) -> None:
    with sqlite3.connect(root / "library.sqlite3") as database:
        database.executemany("""INSERT OR REPLACE INTO midi_index
            (id, source_id, game, title, url, payload) VALUES (?, ?, ?, ?, ?, ?)""", [
            (item["id"], item["source_id"], item["game"], item["title"],
             item["url"], json.dumps(item, ensure_ascii=False)) for item in items
        ])


def save_cover(root: Path, source: dict[str, object], game: str, data: bytes, suffix: str, url: str) -> str:
    if len(data) > 5 * 1024 * 1024 or not (
        (suffix in (".jpg", ".jpeg") and data.startswith(b"\xff\xd8\xff"))
        or (suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
    ):
        raise ValueError("ZIP cover image has an unsupported format or size")
    source_id = str(source["id"])
    filename = hashlib.sha256(f"{source_id}:{game}".encode()).hexdigest()[:24] + suffix
    directory = root / "covers"
    directory.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=directory, delete=False) as stream:
        stream.write(data)
        temporary = Path(stream.name)
    os.replace(temporary, directory / filename)
    with sqlite3.connect(root / "library.sqlite3") as database:
        database.execute("""INSERT OR REPLACE INTO midi_covers
            (source_id, game, filename, source_url, rights_note) VALUES (?, ?, ?, ?, ?)""",
            (source_id, game, filename, url, str(source.get("rights_note", ""))))
    return filename
