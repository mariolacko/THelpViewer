"""Statistics and Hall of Fame HTTP routes for the viewer server."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..statistics import (
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
    normalize_midi_play,
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
    level: int = 0


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


def create_statistics_router(
    store: StatisticsStore, help_display_names: dict[str, str],
) -> APIRouter:
    """Expose aggregate statistics and scores without owning app setup."""
    router = APIRouter()

    @router.post("/api/statistics/events", status_code=204)
    def statistics_event(event: StatisticsEvent, request: Request) -> Response:
        match event.event:
            case "visit":
                operating_system, browser, device = parse_user_agent(request.headers.get("user-agent", ""))
                store.add(
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
            case "session_end":
                bucket = bucket_duration(event.duration_ms)
                if not bucket:
                    raise HTTPException(status_code=422, detail="Invalid active duration")
                store.add({"active_duration": bucket})
            case "dialog_open":
                dialog = normalize_dialog(event.name)
                if not dialog:
                    raise HTTPException(status_code=422, detail="Invalid dialog")
                store.add({"dialog": dialog})
            case "tool_open":
                tool = normalize_tool(event.name)
                if not tool:
                    raise HTTPException(status_code=422, detail="Invalid tool")
                store.add({"tool": tool})
            case "search":
                search = normalize_search(event.scope, event.result)
                if not search:
                    raise HTTPException(status_code=422, detail="Invalid search result")
                store.add({"search": search})
            case "link":
                link = normalize_link(event.result)
                if not link:
                    raise HTTPException(status_code=422, detail="Invalid link result")
                store.add({"link": link})
            case "open" | "help_open":
                help_file = normalize_help_file(event.help_file)
                if not help_file:
                    raise HTTPException(status_code=422, detail="Invalid help file")
                store.add({"help_file": normalize_help_name(event.help_name) or help_file})
            case "doc_open":
                document = normalize_path(event.document)
                if not document:
                    raise HTTPException(status_code=422, detail="Invalid document")
                store.add({"document": document})
            case "topic_open":
                topic = normalize_topic(event.help_file, event.topic)
                if not topic:
                    raise HTTPException(status_code=422, detail="Invalid topic")
                store.add({"topic": topic})
            case "game_open":
                game = normalize_game(event.game)
                if not game:
                    raise HTTPException(status_code=422, detail="Invalid game")
                store.add({"game": game})
            case "view_duration":
                values = normalize_view_duration(
                    event.scope, event.name, event.result, event.duration_ms
                )
                if not values:
                    raise HTTPException(status_code=422, detail="Invalid view duration")
                store.add(values)
            case "game_complete":
                values = normalize_view_duration(
                    "game", event.game, event.result, event.duration_ms
                )
                if not values:
                    raise HTTPException(status_code=422, detail="Invalid game completion")
                store.add(values)
            case "midi_play":
                values = normalize_midi_play(
                    event.scope, event.topic, event.game, event.name, event.duration_ms
                )
                if values is None:
                    raise HTTPException(status_code=422, detail="Invalid MIDI playback")
                store.add_midi_play(*values)
            case "performance":
                metric = normalize_choice(
                    event.metric, {"page_ttfb", "page_load", "lcp", "cls", "inp"}, ""
                )
                bucket = bucket_layout_shift(event.value) if metric == "cls" else bucket_timing(event.value)
                if not metric or not bucket:
                    raise HTTPException(status_code=422, detail="Invalid performance metric")
                store.add({metric: bucket})
            case "help_performance":
                phase = normalize_choice(event.metric, {"load", "decompress", "render"}, "")
                bucket = bucket_timing(event.duration_ms)
                if not phase or not bucket:
                    raise HTTPException(status_code=422, detail="Invalid HELP performance metric")
                store.add({f"help_{phase}": bucket})
            case "client_error":
                store.add({"client_error": normalize_error(event.error)})
            case _:
                raise HTTPException(status_code=422, detail="Unsupported statistics event")
        return Response(status_code=204)

    @router.get("/api/statistics/summary")
    def statistics_summary() -> JSONResponse:
        summary = store.summary()
        _apply_help_display_names(summary, help_display_names)
        return JSONResponse(summary)

    @router.get("/api/hall-of-fame/{game}")
    def hall_of_fame(game: str) -> JSONResponse:
        try:
            return JSONResponse({"game": game, "entries": store.hall_of_fame(game)})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @router.post("/api/hall-of-fame/{game}")
    def add_hall_of_fame_score(game: str, score: HallOfFameScore) -> JSONResponse:
        try:
            entries, accepted = store.add_hall_of_fame(
                game, score.name, score.score, score.note, score.level
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return JSONResponse({"game": game, "accepted": accepted, "entries": entries})

    return router
