"""FastAPI application for serving viewer assets, help bundles, and docs."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
import aiofiles
from fastapi.staticfiles import StaticFiles

from .config import AppConfig, load_config


def _virtual_docs_map(config: AppConfig) -> dict[str, Path]:
    virtual_docs: dict[str, Path] = {}
    for request_path, disk_path in config.virtual_docs:
        if disk_path.is_file():
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
    app = FastAPI(title="THelpViewer", version="2.0")
    app.state.config = config

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
        async with aiofiles.open(config.index_path, mode="rb") as f:
            content = await f.read()
        return Response(content, media_type="text/html")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/docs/catalog.json")
    def docs_catalog() -> JSONResponse:
        return JSONResponse(_docs_catalog(config))

    @app.get("/docs/{doc_path:path}")
    async def docs_file(doc_path: str) -> Response:
        if doc_path == "catalog.json":
            raise HTTPException(status_code=404)
        virtual_docs = _virtual_docs_map(config)
        if doc_path in virtual_docs:
            path = virtual_docs[doc_path]
        else:
            resolved = (config.docs_dir / doc_path).resolve()
            docs_root = config.docs_dir.resolve()
            if not str(resolved).startswith(str(docs_root)):
                raise HTTPException(status_code=404)
            if not resolved.is_file():
                raise HTTPException(status_code=404)
            path = resolved
        async with aiofiles.open(path, mode="rb") as f:
            content = await f.read()
        # Volitelně: určete media_type podle přípony
        return Response(content, media_type="text/markdown")

    @app.get("/config.json")
    def runtime_config() -> JSONResponse:
        payload = {
            "web_dir": str(config.web_dir),
            "index_path": str(config.index_path),
            "helps_dir": str(config.helps_dir),
            "docs_dir": str(config.docs_dir),
            "assets_dir": str(config.assets_dir),
            "readme_path": str(config.readme_path),
            "changelog_path": str(config.changelog_path),
            "state_dir": str(config.state_dir),
            "virtual_docs": [
                {
                    "file": request_path,
                    "disk_path": str(disk_path),
                }
                for request_path, disk_path in config.virtual_docs
            ],
        }
        return JSONResponse(json.loads(json.dumps(payload)))

    return app


app = create_app()
