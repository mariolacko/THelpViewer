"""FastAPI application for serving viewer assets, help bundles, and docs."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..public_docs import is_public_doc_path
from .config import AppConfig, load_config
from .statistics import (
    StatisticsStore,
    bucket_duration,
    bucket_layout_shift,
    bucket_timing,
    country_from_headers,
    normalize_choice,
    normalize_dialog,
    normalize_dimensions,
    normalize_error,
    normalize_game,
    normalize_help_file,
    normalize_help_name,
    normalize_link,
    normalize_locale,
    normalize_number,
    normalize_path,
    normalize_referrer,
    normalize_resolution,
    normalize_search,
    normalize_timezone,
    normalize_tool,
    normalize_topic,
    normalize_view_duration,
    parse_user_agent,
)


class StatisticsEvent(BaseModel):
    event: str
    referrer: str = ""
    screen_width: int | None = None
    screen_height: int | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    pixel_ratio: float | None = None
    color_depth: int | None = None
    language: str = ""
    timezone: str = ""
    theme: str = ""
    help_file: str = ""
    help_name: str = ""
    document: str = ""
    topic: str = ""
    game: str = ""
    error: str = ""
    name: str = ""
    scope: str = ""
    result: str = ""
    metric: str = ""
    duration_ms: float | None = None
    value: float | None = None
    orientation: str = ""
    pointer: str = ""
    reduced_motion: str = ""


class HallOfFameScore(BaseModel):
    name: str = "Player"
    score: float
    note: str = ""


def _help_display_names(config: AppConfig) -> dict[str, str]:
    """Return only exact, unambiguous catalog filename-to-title mappings."""
    catalog_path = config.helps_dir / "catalog.json"
    try:
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    candidates: dict[str, set[str]] = {}
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        display_name = str(entry.get("name") or "").strip()
        if not display_name:
            continue
        values = [entry.get("file"), entry.get("source_file")]
        values.extend(entry.get("source_files") if isinstance(entry.get("source_files"), list) else [])
        for value in values:
            normalized = str(value or "").strip().replace("\\", "/").casefold()
            if not normalized:
                continue
            candidates.setdefault(normalized, set()).add(display_name)
            candidates.setdefault(normalized.rsplit("/", 1)[-1], set()).add(display_name)
    return {key: next(iter(names)) for key, names in candidates.items() if len(names) == 1}


def _apply_help_display_names(summary: dict[str, object], names: dict[str, str]) -> None:
    combined: dict[str, int] = {}
    for row in summary.get("help_file", []):
        if not isinstance(row, dict):
            continue
        value = str(row.get("value") or "")
        key = value.replace("\\", "/").casefold()
        label = names.get(key, names.get(key.rsplit("/", 1)[-1], value))
        combined[label] = combined.get(label, 0) + int(row.get("count") or 0)
    summary["help_file"] = [
        {"value": value, "count": count}
        for value, count in sorted(combined.items(), key=lambda item: (-item[1], item[0]))
    ]


def _virtual_docs_map(config: AppConfig) -> dict[str, Path]:
    virtual_docs: dict[str, Path] = {}
    for request_path, disk_path in config.virtual_docs:
        if is_public_doc_path(request_path) and disk_path.is_file():
            virtual_docs[request_path] = disk_path
    return virtual_docs


def _docs_catalog(config: AppConfig) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    virtual_docs = _virtual_docs_map(config)
    for request_path, _disk_path in config.virtual_docs:
        if request_path not in virtual_docs:
            continue
        request = Path(request_path)
        entry: dict[str, str] = {"file": request_path, "name": request.stem}
        if request.parent != Path("."):
            entry["group"] = " / ".join(request.parent.parts)
        catalog.append(entry)

    if config.docs_dir.is_dir():
        for md_path in sorted(config.docs_dir.rglob("*.md")):
            rel = md_path.relative_to(config.docs_dir)
            file_name = str(rel).replace("\\", "/")
            if not is_public_doc_path(file_name):
                continue
            if file_name in virtual_docs:
                continue
            entry: dict[str, str] = {
                "file": file_name,
                "name": md_path.stem,
            }
            if rel.parent != Path("."):
                entry["group"] = " / ".join(rel.parent.parts)
            catalog.append(entry)
    return catalog


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or load_config()
    app = FastAPI(title="THelpViewer", version=__version__)
    app.state.config = config
    statistics_path = config.statistics_path or config.state_dir / "statistics.sqlite3"
    app.state.statistics = StatisticsStore(statistics_path)
    app.state.help_display_names = _help_display_names(config)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        accepts_html = "text/html" in request.headers.get("accept", "")
        if exc.status_code == 404 and request.method == "GET" and accepts_html and not request.url.path.startswith("/api/"):
            query = urlencode({"server_error": "404", "server_path": request.url.path})
            return RedirectResponse(url=f"/?{query}", status_code=303)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    app.mount(
        "/assets",
        StaticFiles(directory=config.assets_dir, check_dir=False),
        name="assets",
    )
    app.mount(
        "/helps",
        StaticFiles(directory=config.helps_dir, check_dir=False),
        name="helps",
    )

    @app.get("/")
    async def index() -> Response:
        if not config.index_path.is_file():
            raise HTTPException(status_code=404)
        return Response(config.index_path.read_bytes(), media_type="text/html")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/api/statistics/events", status_code=204)
    def statistics_event(event: StatisticsEvent, request: Request) -> Response:
        if event.event == "visit":
            operating_system, browser, device = parse_user_agent(request.headers.get("user-agent", ""))
            app.state.statistics.add(
                {
                    "visit": "all",
                    "country": country_from_headers(request.headers),
                    "referrer": normalize_referrer(event.referrer),
                    "resolution": normalize_resolution(event.screen_width, event.screen_height),
                    "viewport": normalize_dimensions(event.viewport_width, event.viewport_height),
                    "pixel_ratio": normalize_number(event.pixel_ratio, 0.25, 10, "×"),
                    "color_depth": normalize_number(event.color_depth, 1, 64, " bit"),
                    "os": operating_system,
                    "browser": browser,
                    "device": device,
                    "language": normalize_locale(event.language),
                    "timezone": normalize_timezone(event.timezone),
                    "theme": normalize_choice(event.theme, {"default", "light", "dark", "auto"}, "default"),
                    "orientation": normalize_choice(
                        event.orientation, {"portrait", "landscape", "unknown"}, "unknown"
                    ),
                    "pointer": normalize_choice(
                        event.pointer, {"fine", "coarse", "none", "unknown"}, "unknown"
                    ),
                    "reduced_motion": normalize_choice(
                        event.reduced_motion, {"reduce", "no-preference"}, "no-preference"
                    ),
                }
            )
        elif event.event == "session_end":
            bucket = bucket_duration(event.duration_ms)
            if not bucket:
                raise HTTPException(status_code=422, detail="Invalid active duration")
            app.state.statistics.add({"active_duration": bucket})
        elif event.event == "dialog_open":
            dialog = normalize_dialog(event.name)
            if not dialog:
                raise HTTPException(status_code=422, detail="Invalid dialog")
            app.state.statistics.add({"dialog": dialog})
        elif event.event == "tool_open":
            tool = normalize_tool(event.name)
            if not tool:
                raise HTTPException(status_code=422, detail="Invalid tool")
            app.state.statistics.add({"tool": tool})
        elif event.event == "search":
            search = normalize_search(event.scope, event.result)
            if not search:
                raise HTTPException(status_code=422, detail="Invalid search result")
            app.state.statistics.add({"search": search})
        elif event.event == "link":
            link = normalize_link(event.result)
            if not link:
                raise HTTPException(status_code=422, detail="Invalid link result")
            app.state.statistics.add({"link": link})
        elif event.event in {"open", "help_open"}:
            help_file = normalize_help_file(event.help_file)
            if not help_file:
                raise HTTPException(status_code=422, detail="Invalid help file")
            app.state.statistics.add({"help_file": normalize_help_name(event.help_name) or help_file})
        elif event.event == "doc_open":
            document = normalize_path(event.document)
            if not document:
                raise HTTPException(status_code=422, detail="Invalid document")
            app.state.statistics.add({"document": document})
        elif event.event == "topic_open":
            topic = normalize_topic(event.help_file, event.topic)
            if not topic:
                raise HTTPException(status_code=422, detail="Invalid topic")
            app.state.statistics.add({"topic": topic})
        elif event.event == "game_open":
            game = normalize_game(event.game)
            if not game:
                raise HTTPException(status_code=422, detail="Invalid game")
            app.state.statistics.add({"game": game})
        elif event.event == "view_duration":
            values = normalize_view_duration(
                event.scope, event.name, event.result, event.duration_ms
            )
            if not values:
                raise HTTPException(status_code=422, detail="Invalid view duration")
            app.state.statistics.add(values)
        elif event.event == "game_complete":
            values = normalize_view_duration(
                "game", event.game, event.result, event.duration_ms
            )
            if not values:
                raise HTTPException(status_code=422, detail="Invalid game completion")
            app.state.statistics.add(values)
        elif event.event == "performance":
            metric = normalize_choice(
                event.metric, {"page_ttfb", "page_load", "lcp", "cls", "inp"}, ""
            )
            bucket = bucket_layout_shift(event.value) if metric == "cls" else bucket_timing(event.value)
            if not metric or not bucket:
                raise HTTPException(status_code=422, detail="Invalid performance metric")
            app.state.statistics.add({metric: bucket})
        elif event.event == "help_performance":
            phase = normalize_choice(event.metric, {"load", "decompress", "render"}, "")
            bucket = bucket_timing(event.duration_ms)
            if not phase or not bucket:
                raise HTTPException(status_code=422, detail="Invalid HELP performance metric")
            app.state.statistics.add({f"help_{phase}": bucket})
        elif event.event == "client_error":
            app.state.statistics.add({"client_error": normalize_error(event.error)})
        else:
            raise HTTPException(status_code=422, detail="Unsupported statistics event")
        return Response(status_code=204)

    @app.get("/api/statistics/summary")
    def statistics_summary() -> JSONResponse:
        summary = app.state.statistics.summary()
        _apply_help_display_names(summary, app.state.help_display_names)
        return JSONResponse(summary)

    @app.get("/api/hall-of-fame/{game}")
    def hall_of_fame(game: str) -> JSONResponse:
        try:
            return JSONResponse({"game": game, "entries": app.state.statistics.hall_of_fame(game)})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/hall-of-fame/{game}")
    def add_hall_of_fame_score(game: str, score: HallOfFameScore) -> JSONResponse:
        try:
            entries, accepted = app.state.statistics.add_hall_of_fame(
                game, score.name, score.score, score.note
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return JSONResponse({"game": game, "accepted": accepted, "entries": entries})

    @app.get("/docs/catalog.json")
    def docs_catalog() -> JSONResponse:
        return JSONResponse(_docs_catalog(config))

    @app.get("/docs/{doc_path:path}")
    async def docs_file(doc_path: str) -> Response:
        if doc_path == "catalog.json" or not is_public_doc_path(doc_path):
            raise HTTPException(status_code=404)
        virtual_docs = _virtual_docs_map(config)
        if doc_path in virtual_docs:
            path = virtual_docs[doc_path]
        else:
            resolved = (config.docs_dir / doc_path).resolve()
            docs_root = config.docs_dir.resolve()
            if not resolved.is_relative_to(docs_root):
                raise HTTPException(status_code=404)
            if resolved.suffix.casefold() != ".md":
                raise HTTPException(status_code=404)
            if not resolved.is_file():
                raise HTTPException(status_code=404)
            path = resolved
        return Response(path.read_bytes(), media_type="text/markdown")

    @app.get("/config.json")
    def runtime_config() -> JSONResponse:
        return JSONResponse(
            {
                "index_url": "/",
                "assets_url": "/assets/",
                "helps_url": "/helps/",
                "docs_url": "/docs/",
                "virtual_docs": [request_path for request_path, _disk_path in config.virtual_docs],
            }
        )

    return app


app = create_app()
