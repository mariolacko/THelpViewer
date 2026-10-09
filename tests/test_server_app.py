import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from thelpviewer import __version__
from thelpviewer.server.app import create_app
from thelpviewer.server.config import AppConfig
from thelpviewer.server.statistics import StatisticsStore
from thelpviewer.server.routes.statistics import create_statistics_router


def test_statistics_event_dispatch_keeps_help_alias_and_rejects_unknown(tmp_path):
    app = FastAPI()
    app.include_router(create_statistics_router(StatisticsStore(tmp_path / "statistics.sqlite3"), {}))
    client = TestClient(app)

    assert client.post(
        "/api/statistics/events", json={"event": "help_open", "help_file": "VISTA.NG"}
    ).status_code == 204
    assert client.post(
        "/api/statistics/events", json={"event": "help_open", "help_file": ""}
    ).status_code == 422
    assert client.post(
        "/api/statistics/events", json={"event": "unknown"}
    ).status_code == 422
    assert client.get("/api/statistics/summary").json()["help_file"] == [
        {"value": "VISTA.NG", "count": 1}
    ]


def test_statistics_store_uses_bind_mount_safe_journal_mode(tmp_path):
    database = tmp_path / "var" / "statistics.sqlite3"
    store = StatisticsStore(database)

    store.add({"visit": "1"})

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)


def test_dos_tool_open_and_duration_are_available_in_server_statistics(tmp_path):
    app = FastAPI()
    app.include_router(create_statistics_router(StatisticsStore(tmp_path / "statistics.sqlite3"), {}))
    client = TestClient(app)
    assert client.post("/api/statistics/events", json={
        "event": "tool_open", "name": "dos-prompt",
    }).status_code == 204
    assert client.post("/api/statistics/events", json={
        "event": "view_duration", "scope": "tool", "name": "dos-prompt", "duration_ms": 90_000,
    }).status_code == 204
    assert client.post("/api/statistics/events", json={
        "event": "view_duration", "scope": "tool", "name": "unknown-tool", "duration_ms": 90_000,
    }).status_code == 422
    summary = client.get("/api/statistics/summary").json()
    assert summary["tool_opens"] == 1
    assert summary["tool"] == [{"value": "dos-prompt", "count": 1}]
    assert summary["tool_duration"] == [{"value": "dos-prompt · 1–2 min", "count": 1}]


def test_midi_playback_statistics_count_plays_and_actual_minutes(tmp_path):
    app = FastAPI()
    app.include_router(create_statistics_router(StatisticsStore(tmp_path / "statistics.sqlite3"), {}))
    client = TestClient(app)
    for track_id, duration in (("a" * 16, 90_000), ("a" * 16, 30_000), ("b" * 16, 60_000)):
        response = client.post("/api/statistics/events", json={
            "event": "midi_play", "scope": "karlsitretro-dos-d", "topic": track_id,
            "game": "Doom", "name": "At Doom's Gate" if track_id[0] == "a" else "E1M2",
            "duration_ms": duration,
        })
        assert response.status_code == 204
    assert client.post("/api/statistics/events", json={
        "event": "midi_play", "scope": "invalid source", "topic": "a" * 16,
        "game": "Doom", "name": "At Doom's Gate", "duration_ms": 90_000,
    }).status_code == 422
    summary = client.get("/api/statistics/summary").json()
    assert summary["midi_plays"] == 3
    assert summary["midi_minutes"] == 3.0
    assert summary["midi_tracks"] == [
        {"value": "Doom — At Doom's Gate", "count": 2, "minutes": 2.0},
        {"value": "Doom — E1M2", "count": 1, "minutes": 1.0},
    ]


def test_sokoban_hall_of_fame_adds_levels_to_existing_database(tmp_path):
    database = tmp_path / "statistics.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE hall_of_fame (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT NOT NULL,
                name TEXT NOT NULL, score REAL NOT NULL, note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "INSERT INTO hall_of_fame(game, name, score, note, created_at) VALUES (?, ?, ?, ?, ?)",
            ("sokoban", "Existing", 77, "5 levels", "2026-01-01"),
        )

    entries = StatisticsStore(database).hall_of_fame("sokoban")
    assert [(entry["name"], entry["level"], entry["score"]) for entry in entries] == [
        ("Existing", 10, 77),
    ]


def test_sokoban_higher_level_outranks_a_full_table_of_lower_levels(tmp_path):
    store = StatisticsStore(tmp_path / "statistics.sqlite3")
    for score in range(10, 20):
        _, accepted = store.add_hall_of_fame("sokoban", "Level two", score, level=2)
        assert accepted

    entries, accepted = store.add_hall_of_fame("sokoban", "Level three", 100, level=3)
    assert accepted
    assert len(entries) == 10
    assert (entries[0]["level"], entries[0]["score"]) == (3, 100)
    assert [(entry["level"], entry["score"]) for entry in entries[1:]] == [
        (2, score) for score in range(10, 19)
    ]


def test_docs_route_rejects_encoded_parent_traversal(tmp_path):
    web_dir = tmp_path / "www"
    docs_dir = tmp_path / "docs"
    assets_dir = web_dir / "assets"
    helps_dir = tmp_path / "helps"
    for directory in (web_dir, docs_dir, assets_dir, helps_dir):
        directory.mkdir(parents=True, exist_ok=True)
    index_path = web_dir / "index.html"
    index_path.write_text("index", encoding="utf-8")
    (docs_dir / "inside.md").write_text("inside", encoding="utf-8")
    (docs_dir / "Runtime Audit.md").write_text("private audit", encoding="utf-8")
    (docs_dir / "Format RE Notes.md").write_text("private notes", encoding="utf-8")
    (docs_dir / "Audit.md").write_text("private audit", encoding="utf-8")
    (docs_dir / "RE.md").write_text("private notes", encoding="utf-8")
    (docs_dir / "private.txt").write_text("private", encoding="utf-8")
    (tmp_path / "docs-secret.md").write_text("secret", encoding="utf-8")

    config = AppConfig(
        host="127.0.0.1",
        port=5448,
        web_dir=web_dir,
        index_path=index_path,
        assets_dir=assets_dir,
        helps_dir=helps_dir,
        docs_dir=docs_dir,
        readme_path=tmp_path / "README.md",
        changelog_path=tmp_path / "CHANGELOG.md",
        state_dir=tmp_path / "var",
        virtual_docs=(),
    )
    client = TestClient(create_app(config))

    assert client.get("/docs/inside.md").status_code == 200
    assert client.get("/docs/Runtime%20Audit.md").status_code == 404
    assert client.get("/docs/Format%20RE%20Notes.md").status_code == 404
    assert client.get("/docs/Audit.md").status_code == 404
    assert client.get("/docs/RE.md").status_code == 404
    assert client.get("/docs/private.txt").status_code == 404
    assert client.get("/docs/%2e%2e/docs-secret.md").status_code == 404

    runtime_config = client.get("/config.json")
    assert runtime_config.status_code == 200
    assert runtime_config.json() == {
        "index_url": "/",
        "assets_url": "/assets/",
        "helps_url": "/helps/",
        "docs_url": "/docs/",
        "virtual_docs": [],
    }
    assert str(tmp_path) not in runtime_config.text

    catalog = client.get("/docs/catalog.json")
    assert catalog.status_code == 200
    assert catalog.json() == [{"file": "inside.md", "name": "inside"}]


def test_soundfont_uses_brotli_and_versioned_cache_with_raw_fallback(tmp_path):
    web_dir = tmp_path / "www"
    assets_dir = web_dir / "assets"
    soundfont_dir = assets_dir / "midi" / "synth"
    soundfont_dir.mkdir(parents=True)
    soundfont_dir.joinpath("FluidR3Mono_GM.sf3").write_bytes(b"font-data")
    soundfont_dir.joinpath("FluidR3Mono_GM.sf3.br").write_bytes(bytes.fromhex("0f0480666f6e742d6461746103"))
    config = AppConfig(
        host="127.0.0.1", port=5448, web_dir=web_dir, index_path=web_dir / "index.html",
        assets_dir=assets_dir, helps_dir=tmp_path / "helps", docs_dir=tmp_path / "docs",
        readme_path=tmp_path / "README.md", changelog_path=tmp_path / "CHANGELOG.md",
        state_dir=tmp_path / "var", virtual_docs=(),
    )
    client = TestClient(create_app(config))
    url = "/assets/midi/synth/FluidR3Mono_GM.sf3?v=test-version"

    compressed = client.get(url, headers={"accept-encoding": "gzip, br;q=0.5"})
    assert compressed.status_code == 200
    assert compressed.headers["content-encoding"] == "br"
    assert compressed.headers["vary"] == "Accept-Encoding"
    assert compressed.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert compressed.headers["content-type"] == "application/octet-stream"
    assert int(compressed.headers["content-length"]) == 13
    assert client.get(url.split("?", 1)[0], headers={
        "accept-encoding": "br",
    }).headers["cache-control"] == "no-cache"

    uncompressed = client.get(url, headers={"accept-encoding": "br;q=0"})
    assert uncompressed.status_code == 200
    assert uncompressed.content == b"font-data"
    assert "content-encoding" not in uncompressed.headers
    assert uncompressed.headers["vary"] == "Accept-Encoding"
    assert uncompressed.headers["etag"] != compressed.headers["etag"]
    assert client.get(url, headers={
        "accept-encoding": "br", "if-none-match": compressed.headers["etag"],
    }).status_code == 304

    soundfont_dir.joinpath("FluidR3Mono_GM.sf3.br").unlink()
    fallback = client.get(url, headers={"accept-encoding": "br"})
    assert fallback.status_code == 200
    assert fallback.content == b"font-data"
    assert "content-encoding" not in fallback.headers


def test_browser_404_redirects_to_viewer_message_while_api_keeps_json(tmp_path):
    web_dir = tmp_path / "www"
    docs_dir = tmp_path / "docs"
    assets_dir = web_dir / "assets"
    helps_dir = tmp_path / "helps"
    for directory in (web_dir, docs_dir, assets_dir, helps_dir):
        directory.mkdir(parents=True, exist_ok=True)
    index_path = web_dir / "index.html"
    index_path.write_text("index", encoding="utf-8")
    config = AppConfig(
        host="127.0.0.1",
        port=5448,
        web_dir=web_dir,
        index_path=index_path,
        assets_dir=assets_dir,
        helps_dir=helps_dir,
        docs_dir=docs_dir,
        readme_path=tmp_path / "README.md",
        changelog_path=tmp_path / "CHANGELOG.md",
        state_dir=tmp_path / "var",
        virtual_docs=(),
    )
    client = TestClient(create_app(config))

    assert client.get("/healthz").json() == {"status": "ok", "version": __version__}

    browser = client.get("/missing", headers={"accept": "text/html"}, follow_redirects=False)
    assert browser.status_code == 303
    assert browser.headers["location"] == "/?server_error=404&server_path=%2Fmissing"
    api = client.get("/api/missing", headers={"accept": "application/json"})
    assert api.status_code == 404
    assert api.json() == {"detail": "Not Found"}


def test_statistics_are_aggregate_and_do_not_store_private_request_data(tmp_path):
    web_dir = tmp_path / "www"
    docs_dir = tmp_path / "docs"
    assets_dir = web_dir / "assets"
    helps_dir = tmp_path / "helps"
    for directory in (web_dir, docs_dir, assets_dir, helps_dir):
        directory.mkdir(parents=True, exist_ok=True)
    index_path = web_dir / "index.html"
    index_path.write_text("index", encoding="utf-8")
    (helps_dir / "catalog.json").write_text(
        '[{"file":"Norton Guides/vista.json.gz","source_file":"VISTA.NG",'
        '"name":"db_VISTA III Database Programming Guide"}]',
        encoding="utf-8",
    )
    statistics_path = tmp_path / "state" / "stats.sqlite3"
    config = AppConfig(
        host="127.0.0.1",
        port=5448,
        web_dir=web_dir,
        index_path=index_path,
        assets_dir=assets_dir,
        helps_dir=helps_dir,
        docs_dir=docs_dir,
        readme_path=tmp_path / "README.md",
        changelog_path=tmp_path / "CHANGELOG.md",
        state_dir=tmp_path / "state",
        virtual_docs=(),
        statistics_path=statistics_path,
    )
    client = TestClient(create_app(config))
    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Version/18 Safari/605.1.15",
        "cf-ipcountry": "sk",
        "x-forwarded-for": "203.0.113.42",
    }

    visit = client.post(
        "/api/statistics/events",
        headers=headers,
        json={
            "event": "visit",
            "referrer": "https://example.test/private/path?secret=yes",
            "screen_width": 1920,
            "screen_height": 1080,
            "viewport_width": 1512,
            "viewport_height": 982,
            "pixel_ratio": 2,
            "color_depth": 24,
            "language": "sk-SK",
            "timezone": "Europe/Bratislava",
            "theme": "dark",
            "orientation": "landscape",
            "pointer": "fine",
            "reduced_motion": "reduce",
        },
    )
    opened = client.post(
        "/api/statistics/events",
        json={
            "event": "open",
            "help_file": "Norton Guides/VISTA.NG",
            "help_name": "db_VISTA III Database Programming Guide",
        },
    )
    legacy_opened = client.post(
        "/api/statistics/events",
        json={"event": "open", "help_file": "VISTA.NG"},
    )
    document = client.post(
        "/api/statistics/events",
        json={"event": "doc_open", "document": "README.md"},
    )
    game = client.post(
        "/api/statistics/events",
        json={"event": "game_open", "game": "tetris"},
    )
    client_error = client.post(
        "/api/statistics/events",
        json={"event": "client_error", "error": "javascript:TypeError"},
    )
    detail_events = [
        {"event": "session_end", "duration_ms": 95_000},
        {"event": "dialog_open", "name": "systeminfo"},
        {"event": "tool_open", "name": "screen-saver-stars"},
        {"event": "search", "scope": "topic", "result": "found"},
        {"event": "search", "scope": "find", "result": "no-results"},
        {"event": "link", "result": "internal"},
        {"event": "link", "result": "external"},
        {"event": "link", "result": "broken"},
        {
            "event": "view_duration", "scope": "help",
            "name": "db_VISTA III Database Programming Guide", "duration_ms": 95_000,
        },
        {
            "event": "view_duration", "scope": "document",
            "name": "README.md", "duration_ms": 15_000,
        },
        {
            "event": "view_duration", "scope": "dialog",
            "name": "systeminfo", "duration_ms": 45_000,
        },
        {
            "event": "view_duration", "scope": "game", "name": "tetris", "result": "lost",
            "duration_ms": 245_000,
        },
        {
            "event": "game_complete", "game": "snake", "result": "abandoned",
            "duration_ms": 4_000,
        },
        {"event": "performance", "metric": "page_ttfb", "value": 83},
        {"event": "performance", "metric": "page_load", "value": 870},
        {"event": "performance", "metric": "lcp", "value": 1800},
        {"event": "performance", "metric": "cls", "value": 0.18},
        {"event": "performance", "metric": "inp", "value": 275},
        {"event": "help_performance", "metric": "load", "duration_ms": 620},
        {"event": "help_performance", "metric": "decompress", "duration_ms": 42},
        {"event": "help_performance", "metric": "render", "duration_ms": 130},
    ]
    detail_responses = [
        client.post("/api/statistics/events", json=event) for event in detail_events
    ]
    assert visit.status_code == 204
    assert opened.status_code == 204
    assert legacy_opened.status_code == 204
    assert document.status_code == 204
    assert game.status_code == 204
    assert client_error.status_code == 204
    assert all(response.status_code == 204 for response in detail_responses)

    summary = client.get("/api/statistics/summary").json()
    assert summary["visits"] == 1
    assert summary["country"] == [{"value": "SK", "count": 1}]
    assert summary["referrer"] == [{"value": "example.test", "count": 1}]
    assert summary["resolution"] == [{"value": "1920×1080", "count": 1}]
    assert summary["viewport"] == [{"value": "1512×982", "count": 1}]
    assert summary["pixel_ratio"] == [{"value": "2×", "count": 1}]
    assert summary["color_depth"] == [{"value": "24 bit", "count": 1}]
    assert summary["os"] == [{"value": "macOS", "count": 1}]
    assert summary["browser"] == [{"value": "Safari", "count": 1}]
    assert summary["device"] == [{"value": "Desktop", "count": 1}]
    assert summary["language"] == [{"value": "sk-SK", "count": 1}]
    assert summary["timezone"] == [{"value": "Europe/Bratislava", "count": 1}]
    assert summary["theme"] == [{"value": "dark", "count": 1}]
    assert summary["orientation"] == [{"value": "landscape", "count": 1}]
    assert summary["pointer"] == [{"value": "fine", "count": 1}]
    assert summary["reduced_motion"] == [{"value": "reduce", "count": 1}]
    assert summary["active_duration"] == [{"value": "1–2 min", "count": 1}]
    assert summary["dialog"] == [{"value": "systeminfo", "count": 1}]
    assert summary["tool"] == [{"value": "screen-saver-stars", "count": 1}]
    assert summary["search"] == [
        {"value": "find · no-results", "count": 1},
        {"value": "topic · found", "count": 1},
    ]
    assert summary["link"] == [
        {"value": "broken", "count": 1},
        {"value": "external", "count": 1},
        {"value": "internal", "count": 1},
    ]
    assert summary["help_file"] == [
        {"value": "db_VISTA III Database Programming Guide", "count": 2}
    ]
    assert summary["document_opens"] == 1
    assert summary["game_launches"] == 1
    assert summary["dialog_opens"] == 1
    assert summary["tool_opens"] == 1
    assert summary["searches"] == 2
    assert summary["link_opens"] == 3
    assert summary["client_errors"] == 1
    assert summary["document"] == [{"value": "README.md", "count": 1}]
    assert summary["game"] == [{"value": "tetris", "count": 1}]
    assert summary["help_duration"] == [
        {"value": "db_VISTA III Database Programming Guide · 1–2 min", "count": 1}
    ]
    assert summary["document_duration"] == [
        {"value": "README.md · 10–29 s", "count": 1}
    ]
    assert summary["dialog_duration"] == [
        {"value": "systeminfo · 30–59 s", "count": 1}
    ]
    assert summary["game_completions"] == 1
    assert summary["game_outcome"] == [
        {"value": "snake · abandoned", "count": 1},
        {"value": "tetris · lost", "count": 1},
    ]
    assert summary["game_duration"] == [
        {"value": "snake · <10 s", "count": 1},
        {"value": "tetris · 3–9 min", "count": 1},
    ]
    assert summary["page_ttfb"] == [{"value": "<100 ms", "count": 1}]
    assert summary["page_load"] == [{"value": "0.5–0.9 s", "count": 1}]
    assert summary["lcp"] == [{"value": "1–2.4 s", "count": 1}]
    assert summary["cls"] == [{"value": "0.1–0.25", "count": 1}]
    assert summary["inp"] == [{"value": "250–499 ms", "count": 1}]
    assert summary["help_load"] == [{"value": "0.5–0.9 s", "count": 1}]
    assert summary["help_decompress"] == [{"value": "<100 ms", "count": 1}]
    assert summary["help_render"] == [{"value": "100–249 ms", "count": 1}]
    assert summary["client_error"] == [{"value": "javascript:TypeError", "count": 1}]
    database_bytes = statistics_path.read_bytes()
    assert b"203.0.113.42" not in database_bytes
    assert b"private/path" not in database_bytes
    assert b"secret=yes" not in database_bytes


def test_hall_of_fame_is_shared_ranked_and_limited(tmp_path):
    web_dir = tmp_path / "www"
    docs_dir = tmp_path / "docs"
    assets_dir = web_dir / "assets"
    helps_dir = tmp_path / "helps"
    for directory in (web_dir, docs_dir, assets_dir, helps_dir):
        directory.mkdir(parents=True, exist_ok=True)
    index_path = web_dir / "index.html"
    index_path.write_text("index", encoding="utf-8")
    config = AppConfig(
        host="127.0.0.1", port=5448, web_dir=web_dir, index_path=index_path,
        assets_dir=assets_dir, helps_dir=helps_dir, docs_dir=docs_dir,
        readme_path=tmp_path / "README.md", changelog_path=tmp_path / "CHANGELOG.md",
        state_dir=tmp_path / "state", virtual_docs=(),
        statistics_path=tmp_path / "state" / "stats.sqlite3",
    )
    client = TestClient(create_app(config))

    for score in range(5, 17):
        response = client.post(
            "/api/hall-of-fame/tetris",
            json={"name": f"Player {score}", "score": score, "note": "L1"},
        )
        assert response.status_code == 200
        assert response.json()["accepted"] is True
    tetris = client.get("/api/hall-of-fame/tetris").json()["entries"]
    assert len(tetris) == 10
    assert [entry["score"] for entry in tetris] == list(range(16, 6, -1))
    rejected = client.post(
        "/api/hall-of-fame/tetris", json={"name": "Too low", "score": 1}
    )
    assert rejected.status_code == 200
    assert rejected.json()["accepted"] is False

    for score in (25, 18, 31):
        assert client.post(
            "/api/hall-of-fame/hanoi", json={"name": "Mario", "score": score}
        ).status_code == 200
    hanoi = client.get("/api/hall-of-fame/hanoi").json()["entries"]
    assert [entry["score"] for entry in hanoi] == [18, 25, 31]
    assert client.post(
        "/api/hall-of-fame/sokoban", json={"name": "Old", "score": 77, "note": "5 levels"}
    ).status_code == 200
    assert client.post(
        "/api/hall-of-fame/sokoban", json={"name": "New", "score": 170, "note": "10 levels"}
    ).status_code == 200
    assert client.post(
        "/api/hall-of-fame/sokoban", json={"name": "Partial", "score": 1, "level": 3}
    ).status_code == 200
    sokoban = client.get("/api/hall-of-fame/sokoban").json()["entries"]
    assert [(entry["level"], entry["score"]) for entry in sokoban] == [(10, 77), (10, 170), (3, 1)]
    assert client.post(
        "/api/hall-of-fame/sokoban", json={"name": "Invalid", "score": 3, "level": 11}
    ).status_code == 422
    assert client.get("/api/hall-of-fame/unknown").status_code == 404
    assert client.post(
        "/api/hall-of-fame/tetris", json={"name": "Bad", "score": -1}
    ).status_code == 422
