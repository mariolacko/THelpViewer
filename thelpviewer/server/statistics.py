"""Aggregate usage statistics and shared game scores for the viewer server."""

from __future__ import annotations

from datetime import UTC, datetime
import math
from pathlib import Path, PurePosixPath
import re
import sqlite3
from urllib.parse import urlsplit


KINDS = (
    "visit", "country", "referrer", "resolution", "viewport", "pixel_ratio",
    "color_depth", "os", "browser", "device", "language", "timezone", "theme",
    "orientation", "pointer", "reduced_motion", "active_duration", "dialog", "dialog_duration",
    "tool", "tool_duration", "search", "link", "game", "game_outcome", "game_completion", "game_duration",
    "help_duration", "document_duration", "page_ttfb",
    "page_load", "lcp", "cls", "inp", "help_load", "help_decompress",
    "help_render", "help_file", "document", "topic", "client_error",
)
EVENT_TOTALS = {
    "help_opens": "help_file",
    "document_opens": "document",
    "topic_views": "topic",
    "game_launches": "game",
    "dialog_opens": "dialog",
    "tool_opens": "tool",
    "searches": "search",
    "link_opens": "link",
    "game_completions": "game_completion",
    "client_errors": "client_error",
}
COUNTRY_HEADERS = (
    "cf-ipcountry", "x-vercel-ip-country", "cloudfront-viewer-country", "x-country-code",
)
HALL_OF_FAME_GAMES = {
    "puzzle": True, "tetris": False, "pentix": False, "mines": True,
    "breakout": False, "sokoban": True, "lines": False, "reversi": False,
    "ludo": True, "mastermind": True, "hanoi": True, "snake": False, "tron": False,
}
HALL_OF_FAME_LIMIT = 10
DIALOG_NAMES = {
    "account", "add-user", "dialog", "download-action", "download-error", "grid", "login",
    "messagebox", "progress", "rebuild-dos", "rebuild-midi", "registration",
    "registration-token", "server-configuration", "users",
    "about", "ascii", "breakout", "calc", "calendar", "chdir", "colors",
    "contexthelp", "help-packages", "dos-packages", "downloads", "fileopen", "find", "hall-of-fame", "hanoi", "highscore",
    "lines", "ludo", "mastermind", "midi", "midi-sources", "midi-source-progress", "mines", "puzzle", "reversi",
    "search", "server-error", "snake", "sokoban", "statistics", "systeminfo",
    "tetris", "tetris-setup", "tron", "welcome", "widgets", "windowlist",
}
TOOL_NAMES = {
    "context-help", "dos-prompt", "screen-saver-bounce", "screen-saver-clock",
    "screen-saver-matrix", "screen-saver-stars", "theme-auto", "theme-dark",
    "theme-default", "theme-light",
}


def _day() -> str:
    return datetime.now(UTC).date().isoformat()


def _limited(value: object, maximum: int = 160) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value or "")).strip()[:maximum]


def normalize_referrer(value: object) -> str:
    """Keep only the referrer's host; never store full paths or query strings."""
    text = _limited(value, 500)
    if not text:
        return "Direct"
    try:
        parsed = urlsplit(text)
    except ValueError:
        return "Other"
    return _limited(parsed.hostname or "Other", 120) or "Other"


def normalize_dimensions(width: object, height: object) -> str:
    try:
        w = min(16384, max(1, int(width)))
        h = min(16384, max(1, int(height)))
    except (TypeError, ValueError):
        return "Unknown"
    return f"{w}×{h}"


def normalize_resolution(width: object, height: object) -> str:
    """Compatibility name used by older callers."""
    return normalize_dimensions(width, height)


def normalize_number(value: object, minimum: float, maximum: float, suffix: str = "") -> str:
    try:
        number = min(maximum, max(minimum, float(value)))
    except (TypeError, ValueError):
        return "Unknown"
    rendered = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{rendered}{suffix}"


def normalize_choice(value: object, choices: set[str], default: str = "Unknown") -> str:
    candidate = _limited(value, 80)
    return candidate if candidate in choices else default


def normalize_locale(value: object) -> str:
    candidate = _limited(value, 35).replace("_", "-")
    return candidate if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,2}", candidate) else "Unknown"


def normalize_timezone(value: object) -> str:
    candidate = _limited(value, 80)
    return candidate if re.fullmatch(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*", candidate) else "Unknown"


def normalize_path(value: object, maximum: int = 240) -> str:
    text = _limited(value, maximum).replace("\\", "/").lstrip("/")
    path = PurePosixPath(text)
    if not text or ".." in path.parts:
        return ""
    return str(path)


def normalize_help_file(value: object) -> str:
    return normalize_path(value)


def normalize_help_name(value: object) -> str:
    return _limited(value, 160)


def normalize_topic(help_file: object, topic: object) -> str:
    source = normalize_path(help_file, 160)
    context = _limited(topic, 80)
    return f"{source} · {context}" if source and context else ""


def normalize_game(value: object) -> str:
    game = _limited(value, 32).casefold()
    return game if game in HALL_OF_FAME_GAMES else ""


def normalize_dialog(value: object) -> str:
    dialog = _limited(value, 40).casefold()
    return dialog if dialog in DIALOG_NAMES else ""


def normalize_tool(value: object) -> str:
    tool = _limited(value, 40).casefold()
    return tool if tool in TOOL_NAMES else ""


def normalize_search(scope: object, result: object) -> str:
    search_scope = normalize_choice(scope, {"find", "find-again", "topic"}, "")
    search_result = normalize_choice(result, {"found", "no-results", "unavailable"}, "")
    if not search_scope or not search_result:
        return ""
    return f"{search_scope} · {search_result}"


def normalize_link(result: object) -> str:
    return normalize_choice(result, {"internal", "external", "broken"}, "")


def normalize_game_completion(game: object, result: object) -> str:
    normalized_game = normalize_game(game)
    outcome = normalize_choice(result, {"won", "lost", "draw", "finished", "abandoned"}, "")
    if not normalized_game or not outcome:
        return ""
    return f"{normalized_game} · {outcome}"


def bucket_duration(value: object) -> str:
    try:
        milliseconds = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(milliseconds):
        return ""
    milliseconds = max(0.0, min(milliseconds, 86_400_000.0))
    seconds = milliseconds / 1000
    if seconds < 10:
        return "<10 s"
    if seconds < 30:
        return "10–29 s"
    if seconds < 60:
        return "30–59 s"
    if seconds < 180:
        return "1–2 min"
    if seconds < 600:
        return "3–9 min"
    if seconds < 1800:
        return "10–29 min"
    if seconds < 3600:
        return "30–59 min"
    return "1 h+"


def bucket_timing(value: object) -> str:
    try:
        milliseconds = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(milliseconds):
        return ""
    milliseconds = max(0.0, min(milliseconds, 600_000.0))
    if milliseconds < 100:
        return "<100 ms"
    if milliseconds < 250:
        return "100–249 ms"
    if milliseconds < 500:
        return "250–499 ms"
    if milliseconds < 1000:
        return "0.5–0.9 s"
    if milliseconds < 2500:
        return "1–2.4 s"
    if milliseconds < 4000:
        return "2.5–3.9 s"
    if milliseconds < 10_000:
        return "4–9.9 s"
    return "10 s+"


def bucket_layout_shift(value: object) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(score):
        return ""
    score = max(0.0, min(score, 100.0))
    if score <= 0.1:
        return "≤0.1"
    if score <= 0.25:
        return "0.1–0.25"
    return ">0.25"


def normalize_view_duration(
    scope: object,
    name: object,
    result: object,
    duration_ms: object,
) -> dict[str, str]:
    """Return aggregate rows for one active managed-view interval."""
    normalized_scope = normalize_choice(scope, {"help", "document", "dialog", "game", "tool"}, "")
    duration = bucket_duration(duration_ms)
    if not normalized_scope or not duration:
        return {}
    if normalized_scope == "help":
        label = normalize_help_name(name)
        return {"help_duration": f"{label} · {duration}"} if label else {}
    if normalized_scope == "document":
        document = normalize_path(name)
        return {"document_duration": f"{document} · {duration}"} if document else {}
    if normalized_scope == "dialog":
        dialog = normalize_dialog(name)
        return {"dialog_duration": f"{dialog} · {duration}"} if dialog else {}
    if normalized_scope == "tool":
        tool = normalize_tool(name)
        return {"tool_duration": f"{tool} · {duration}"} if tool else {}

    game = normalize_game(name)
    completion = normalize_game_completion(game, result)
    if not game or not completion:
        return {}
    values = {
        "game_outcome": completion,
        "game_duration": f"{game} · {duration}",
    }
    if result != "abandoned":
        values["game_completion"] = game
    return values


def normalize_error(value: object) -> str:
    candidate = _limited(value, 80)
    return candidate if re.fullmatch(r"[A-Za-z0-9_.: -]+", candidate) else "Other"


def normalize_midi_play(
    source: object, track: object, game: object, title: object, duration_ms: object,
) -> tuple[str, str, str, str, int] | None:
    source_id = _limited(source, 64)
    track_id = _limited(track, 180)
    game_name = _limited(game, 100)
    track_title = _limited(title, 100)
    try:
        milliseconds = float(duration_ms)
    except (TypeError, ValueError):
        return None
    if (not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", source_id)
            or not re.fullmatch(r"[0-9a-f]{16}(?::.{1,163})?", track_id)
            or not game_name or not track_title or not math.isfinite(milliseconds)
            or not 0 <= milliseconds <= 86_400_000):
        return None
    return source_id, track_id, game_name, track_title, round(milliseconds)


def parse_user_agent(value: object) -> tuple[str, str, str]:
    user_agent = _limited(value, 500).casefold()
    if "android" in user_agent:
        operating_system = "Android"
    elif "iphone" in user_agent or "ipad" in user_agent:
        operating_system = "iOS"
    elif "windows" in user_agent:
        operating_system = "Windows"
    elif "mac os" in user_agent or "macintosh" in user_agent:
        operating_system = "macOS"
    elif "linux" in user_agent:
        operating_system = "Linux"
    else:
        operating_system = "Other"

    if "edg/" in user_agent:
        browser = "Edge"
    elif "opr/" in user_agent or "opera" in user_agent:
        browser = "Opera"
    elif "firefox/" in user_agent:
        browser = "Firefox"
    elif "chrome/" in user_agent or "crios/" in user_agent:
        browser = "Chrome"
    elif "safari/" in user_agent:
        browser = "Safari"
    else:
        browser = "Other"

    if "ipad" in user_agent or "tablet" in user_agent:
        device = "Tablet"
    elif "mobile" in user_agent or "iphone" in user_agent or "android" in user_agent:
        device = "Mobile"
    else:
        device = "Desktop"
    return operating_system, browser, device


def country_from_headers(headers: object) -> str:
    for name in COUNTRY_HEADERS:
        value = _limited(getattr(headers, "get", lambda _name, _default=None: None)(name), 2).upper()
        if re.fullmatch(r"[A-Z]{2}", value):
            return value
    return "Unknown"


class StatisticsStore:
    """SQLite aggregates plus a public top-ten table; private request data is not stored."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        # The state directory is commonly bind-mounted by Docker Desktop.
        # SQLite WAL shared-memory files are not reliable on every host-backed
        # filesystem, while this small aggregate store does not need WAL-level
        # write concurrency.
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS statistics (
                day TEXT NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, kind, value)
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS hall_of_fame (
                id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT NOT NULL,
                name TEXT NOT NULL, score REAL NOT NULL, note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 0
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS hall_of_fame_game_score ON hall_of_fame(game, score)"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS midi_playback (
                day TEXT NOT NULL, source_id TEXT NOT NULL, track_id TEXT NOT NULL,
                game TEXT NOT NULL, title TEXT NOT NULL,
                plays INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (day, source_id, track_id)
            )"""
        )
        if "level" not in {column[1] for column in connection.execute("PRAGMA table_info(hall_of_fame)")}:
            try:
                connection.execute("ALTER TABLE hall_of_fame ADD COLUMN level INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError as error:
                if "duplicate column name" not in str(error).lower():
                    raise
        return connection

    def add(self, values: dict[str, str]) -> None:
        rows = [(_day(), kind, value) for kind, value in values.items() if kind in KINDS and value]
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """INSERT INTO statistics(day, kind, value, count) VALUES (?, ?, ?, 1)
                ON CONFLICT(day, kind, value) DO UPDATE SET count = count + 1""",
                rows,
            )

    def add_midi_play(self, source_id: str, track_id: str, game: str, title: str, duration_ms: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO midi_playback
                (day, source_id, track_id, game, title, plays, duration_ms)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(day, source_id, track_id) DO UPDATE SET
                    plays = plays + 1, duration_ms = duration_ms + excluded.duration_ms,
                    game = excluded.game, title = excluded.title""",
                (_day(), source_id, track_id, game, title, duration_ms),
            )

    def summary(self, limit: int = 10) -> dict[str, object]:
        safe_limit = min(25, max(1, int(limit)))
        result: dict[str, object] = {"visits": 0}
        with self._connect() as connection:
            totals = dict(connection.execute(
                "SELECT kind, COALESCE(SUM(count), 0) FROM statistics GROUP BY kind"
            ).fetchall())
            result["visits"] = int(totals.get("visit", 0))
            for name, kind in EVENT_TOTALS.items():
                result[name] = int(totals.get(kind, 0))
            result["hall_of_fame_scores"] = int(
                connection.execute("SELECT COUNT(*) FROM hall_of_fame").fetchone()[0]
            )
            midi_plays, midi_duration = connection.execute(
                "SELECT COALESCE(SUM(plays), 0), COALESCE(SUM(duration_ms), 0) FROM midi_playback"
            ).fetchone()
            result["midi_plays"] = int(midi_plays)
            result["midi_minutes"] = round(midi_duration / 60_000, 1)
            result["midi_tracks"] = [
                {"value": f"{game} — {title}", "count": int(plays),
                 "minutes": round(duration / 60_000, 1)}
                for game, title, plays, duration in connection.execute(
                    """SELECT game, title, SUM(plays), SUM(duration_ms) FROM midi_playback
                    GROUP BY source_id, track_id ORDER BY SUM(plays) DESC,
                    SUM(duration_ms) DESC, game, title LIMIT ?""",
                    (safe_limit,),
                ).fetchall()
            ]
            result["daily"] = [
                {"value": day, "count": int(count)}
                for day, count in connection.execute(
                    """SELECT day, SUM(count) FROM statistics WHERE kind = 'visit'
                    GROUP BY day ORDER BY day DESC LIMIT 30"""
                ).fetchall()
            ]
            for kind in KINDS:
                if kind == "visit":
                    continue
                rows = connection.execute(
                    """SELECT value, SUM(count) AS total FROM statistics WHERE kind = ?
                    GROUP BY value ORDER BY total DESC, value ASC LIMIT ?""",
                    (kind, safe_limit),
                ).fetchall()
                result[kind] = [{"value": value, "count": int(count)} for value, count in rows]
        return result

    def hall_of_fame(self, game: str) -> list[dict[str, object]]:
        normalized = normalize_game(game)
        if not normalized:
            raise ValueError("Unsupported game")
        direction = "ASC" if HALL_OF_FAME_GAMES[normalized] else "DESC"
        order = (
            "CASE WHEN level = 0 THEN 10 ELSE level END DESC, score ASC"
            if normalized == "sokoban" else f"score {direction}"
        )
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT name, score, note, level FROM hall_of_fame WHERE game = ?
                ORDER BY {order}, id ASC LIMIT ?""",
                (normalized, HALL_OF_FAME_LIMIT),
            ).fetchall()
        return [
            {
                "name": name,
                "score": int(score) if float(score).is_integer() else score,
                "note": note,
                "level": (level or 10) if normalized == "sokoban" else level,
            }
            for name, score, note, level in rows
        ]

    def add_hall_of_fame(
        self, game: str, name: object, score: object, note: object = "", level: object = 0
    ) -> tuple[list[dict[str, object]], bool]:
        normalized = normalize_game(game)
        if not normalized:
            raise ValueError("Unsupported game")
        player = _limited(name, 15) or "Player"
        annotation = _limited(note, 12)
        try:
            numeric_score = float(score)
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid score") from error
        if not 0 < numeric_score <= 1_000_000_000:
            raise ValueError("Invalid score")
        try:
            numeric_level = int(level)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Invalid level") from error
        if numeric_level != level or not 0 <= numeric_level <= 10:
            raise ValueError("Invalid level")
        if normalized != "sokoban":
            numeric_level = 0
        direction = "ASC" if HALL_OF_FAME_GAMES[normalized] else "DESC"
        order = (
            "CASE WHEN level = 0 THEN 10 ELSE level END DESC, score ASC"
            if normalized == "sokoban" else f"score {direction}"
        )
        with self._connect() as connection:
            inserted = connection.execute(
                "INSERT INTO hall_of_fame(game, name, score, note, created_at, level) VALUES (?, ?, ?, ?, ?, ?)",
                (normalized, player, numeric_score, annotation, datetime.now(UTC).isoformat(), numeric_level),
            )
            connection.execute(
                f"""DELETE FROM hall_of_fame WHERE game = ? AND id NOT IN (
                    SELECT id FROM hall_of_fame WHERE game = ?
                    ORDER BY {order}, id ASC LIMIT ?
                )""",
                (normalized, normalized, HALL_OF_FAME_LIMIT),
            )
            accepted = connection.execute(
                "SELECT 1 FROM hall_of_fame WHERE id = ?", (inserted.lastrowid,)
            ).fetchone() is not None
        return self.hall_of_fame(normalized), accepted
