"""FastAPI application for serving viewer assets, help bundles, and docs."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..public_docs import is_public_doc_path, public_doc_sources
from .accounts import AccountStore
from .config import AppConfig, load_config
from .routes.auth import create_auth_router
from .routes.midi import create_midi_router
from .routes.public_pages import create_public_router
from .routes.statistics import create_statistics_router
from .search_index import GlobalSearchIndex
from .midi_library import MidiLibrary
from .terminal import authorize_job, read_job, send_input
from .statistics import StatisticsStore
from .static_assets import ViewerAssets


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
        running_app.state.midi_library.start()
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
    app.state.midi_library = MidiLibrary(config.state_dir / "midi", config.midi_sources_path)
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
        ViewerAssets(directory=config.assets_dir, check_dir=False),
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
    app.include_router(create_statistics_router(
        app.state.statistics, app.state.help_display_names,
    ))
    app.include_router(create_auth_router(config, app.state.accounts))
    app.include_router(create_midi_router(app.state.midi_library))

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
