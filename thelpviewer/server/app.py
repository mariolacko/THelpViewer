"""FastAPI application for serving viewer assets, help bundles, and docs."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..public_docs import is_public_doc_path, public_doc_sources
from .accounts import AccountError, AccountStore, SESSION_LIFETIME
from .config import AppConfig, load_config
from .public_pages import create_public_router
from .search_index import GlobalSearchIndex
from .terminal import authorize_job, read_job, send_input
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
    level: int = 0


class PasskeyEnrollment(BaseModel):
    username: str
    token: str


class PasskeyRegistration(BaseModel):
    name: str
    email: str
    token: str


class PasskeyLogin(BaseModel):
    username: str


class PasskeyAnswer(BaseModel):
    ceremony_id: str
    credential: dict


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


def _docs_catalog(config: AppConfig) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    for file_name in public_doc_sources(config.docs_dir, config.virtual_docs):
        request = Path(file_name)
        entry: dict[str, str] = {"file": file_name, "name": request.stem}
        if request.parent != Path("."):
            entry["group"] = " / ".join(request.parent.parts)
        catalog.append(entry)
    return catalog


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or load_config()

    @asynccontextmanager
    async def lifespan(running_app: FastAPI):
        running_app.state.global_search.ensure_current()
        bootstrap_token = running_app.state.accounts.bootstrap_token()
        if bootstrap_token:
            print(f"THelpViewer first administrator registration token (valid 1 hour): {bootstrap_token}", flush=True)
        yield

    app = FastAPI(title="THelpViewer", version=__version__, lifespan=lifespan)
    app.state.config = config
    statistics_path = config.statistics_path or config.state_dir / "statistics.sqlite3"
    app.state.statistics = StatisticsStore(statistics_path)
    app.state.global_search = GlobalSearchIndex(
        config.helps_dir, config.state_dir, config.docs_dir, config.virtual_docs
    )
    app.state.accounts = AccountStore(config.state_dir)
    app.state.help_display_names = _help_display_names(config)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        accepts_html = "text/html" in request.headers.get("accept", "")
        if (exc.status_code == 404 and request.method == "GET" and accepts_html
                and not (request.url.path == "/" and any(
                    key in request.query_params for key in ("file", "topic", "doc")
                ))
                and not request.url.path.startswith(("/api/", "/topics/", "/documents/", "/sitemap"))):
            query = urlencode({"server_error": "404", "server_path": request.url.path})
            return RedirectResponse(url=f"/?{query}", status_code=303)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(ImportError)
    async def missing_dependency(request: Request, exc: ImportError) -> Response:
        if request.url.path.startswith("/api/auth/passkey/"):
            return JSONResponse(
                {"detail": "Passkey server dependency is unavailable; rebuild the viewer Docker image."},
                status_code=503,
            )
        raise exc

    @app.get("/assets/Thelp.png")
    def site_image() -> FileResponse:
        image = config.readme_path.parent / "Thelp.png"
        if not image.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(image, media_type="image/png")

    @app.get("/favicon.ico")
    def favicon() -> RedirectResponse:
        return RedirectResponse("/assets/thelp-icon.svg", status_code=307)

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

    app.include_router(create_public_router(
        config, app.state.global_search, app.state.help_display_names,
    ))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/search/status")
    def search_index_status() -> dict[str, object]:
        return app.state.global_search.status()

    @app.get("/api/search/global")
    def global_search(q: str = "", limit: int = 60) -> Response:
        if len(q) > 255:
            raise HTTPException(status_code=422, detail="Search text is too long")
        status, results = app.state.global_search.search(q, limit)
        if status["state"] != "ready":
            return JSONResponse(status, status_code=503 if status["state"] == "error" else 202)
        return JSONResponse({"status": status, "results": results}, headers={"Cache-Control": "no-store"})

    def auth_origin(request: Request, *, require_post: bool = False) -> tuple[str, str]:
        origin = config.auth_origin
        parsed = urlparse(origin)
        secure_context = parsed.scheme == "https" or (
            parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        )
        if not secure_context or request.headers.get("host", "").lower() != parsed.netloc.lower():
            raise HTTPException(status_code=503, detail="Passkey login is not configured for this host")
        if require_post and request.headers.get("origin") != origin:
            raise HTTPException(status_code=403, detail="Invalid request origin")
        return origin, parsed.hostname or ""

    def auth_response(token: str, origin: str) -> JSONResponse:
        response = JSONResponse({"authenticated": True})
        response.set_cookie(
            "thelp_session", token, max_age=SESSION_LIFETIME, httponly=True,
            secure=origin.startswith("https://"), samesite="strict", path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/auth/session")
    def auth_session(request: Request) -> JSONResponse:
        try:
            auth_origin(request)
        except HTTPException:
            return JSONResponse({"enabled": False, "authenticated": False}, headers={"Cache-Control": "no-store"})
        user = app.state.accounts.session_user(request.cookies.get("thelp_session", ""))
        return JSONResponse(
            {"enabled": True, "authenticated": bool(user), "user": user},
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/api/auth/passkey/enroll/options")
    def passkey_enroll_options(data: PasskeyEnrollment, request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        try:
            return app.state.accounts.registration_options(data.username, data.token, rp_id, "THelpViewer")
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @app.post("/api/auth/passkey/enroll/verify")
    def passkey_enroll_verify(data: PasskeyAnswer, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        try:
            token = app.state.accounts.verify_registration(data.ceremony_id, data.credential, rp_id, origin)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @app.post("/api/auth/passkey/register/options")
    def passkey_register_options(data: PasskeyRegistration, request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        try:
            return app.state.accounts.new_registration_options(
                data.name, data.email, data.token, rp_id, "THelpViewer",
            )
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @app.post("/api/auth/passkey/register/verify")
    def passkey_register_verify(data: PasskeyAnswer, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        try:
            token = app.state.accounts.verify_new_registration(data.ceremony_id, data.credential, rp_id, origin)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @app.get("/api/auth/registration-tokens")
    def registration_tokens(request: Request) -> JSONResponse:
        auth_origin(request)
        try:
            tokens = app.state.accounts.list_registration_tokens(request.cookies.get("thelp_session", ""))
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return JSONResponse({"tokens": tokens}, headers={"Cache-Control": "no-store"})

    @app.post("/api/auth/registration-tokens")
    def registration_token(request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        try:
            token = app.state.accounts.issue_registration_token(request.cookies.get("thelp_session", ""))
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return JSONResponse({"token": token, "expires_in": 3600}, headers={"Cache-Control": "no-store"})

    @app.delete("/api/auth/registration-tokens/{token_hash}", status_code=204)
    def delete_registration_token(token_hash: str, request: Request) -> Response:
        auth_origin(request, require_post=True)
        try:
            app.state.accounts.delete_registration_token(request.cookies.get("thelp_session", ""), token_hash)
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return Response(status_code=204)

    @app.post("/api/auth/passkey/login/options")
    def passkey_login_options(data: PasskeyLogin, request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        try:
            return app.state.accounts.authentication_options(data.username, rp_id)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @app.post("/api/auth/passkey/login/verify")
    def passkey_login_verify(data: PasskeyAnswer, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        try:
            token = app.state.accounts.verify_authentication(data.ceremony_id, data.credential, rp_id, origin)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @app.post("/api/auth/logout")
    def auth_logout(request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        app.state.accounts.logout(request.cookies.get("thelp_session", ""))
        response = JSONResponse({"authenticated": False}, headers={"Cache-Control": "no-store"})
        response.delete_cookie("thelp_session", path="/")
        return response

    @app.get("/api/terminal/jobs/{job_id}")
    def terminal_output(job_id: str, request: Request, offset: int = 0) -> dict[str, object]:
        return read_job(config.state_dir, job_id, request.headers.get("x-thelp-terminal-key", ""), offset)

    @app.post("/api/terminal/jobs/{job_id}/input", status_code=204)
    async def terminal_input(job_id: str, request: Request) -> Response:
        key = request.headers.get("x-thelp-terminal-key", "")
        authorize_job(config.state_dir, job_id, key)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                raise HTTPException(status_code=413, detail="Terminal input is too large")
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, ValueError):
            raise HTTPException(status_code=422, detail="Invalid terminal input") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise HTTPException(status_code=422, detail="Terminal input must contain text")
        send_input(config.state_dir, job_id, key, payload["text"])
        return Response(status_code=204)

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
                game, score.name, score.score, score.note, score.level
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
        path = public_doc_sources(config.docs_dir, config.virtual_docs).get(doc_path)
        if path is None:
            raise HTTPException(status_code=404)
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
