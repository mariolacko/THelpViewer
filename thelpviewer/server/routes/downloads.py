"""Shared queue and actions on known failed rows, never arbitrary URLs."""

from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .authorization import require_administrator


class DownloadAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=3, max_length=256)
    action: Literal["retry", "remove"]


def create_downloads_router(config, accounts, downloads):
    router = APIRouter(prefix="/api/downloads")

    @router.get("")
    def status(request: Request):
        private = False
        try:
            require_administrator(config, accounts, request)
            private = True
        except HTTPException:
            pass
        catalog = config.helps_dir / "catalog.json"
        try:
            stat = catalog.stat()
            revision = f"{stat.st_mtime_ns}:{stat.st_size}"
        except FileNotFoundError:
            revision = "missing"
        return JSONResponse({**downloads.snapshot(private=private), "content_revision": revision},
                            headers={"Cache-Control": "no-store"})

    @router.post("/action", status_code=202)
    def act(values: DownloadAction, request: Request):
        kind, _, group = values.id.partition(":")
        if kind != "midi" or ":" not in group:
            # Source indexing and HELP/DOS installation remain administrator actions.
            require_administrator(config, accounts, request, write=True)
        else:
            origin = request.headers.get("origin", "")
            # The configured public origin also covers TLS termination at the proxy.
            if (origin not in {config.auth_origin, str(request.base_url).rstrip("/")}
                    or urlsplit(origin).netloc.lower() != request.headers.get("host", "").lower()
                    or request.headers.get("sec-fetch-site", "same-origin") != "same-origin"):
                raise HTTPException(status_code=403, detail="Invalid download request origin")
        try:
            downloads.act(values.id, values.action)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return JSONResponse({"accepted": True}, status_code=202, headers={"Cache-Control": "no-store"})

    return router
