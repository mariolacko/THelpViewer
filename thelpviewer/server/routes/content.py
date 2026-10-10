"""Administrator-only content choices and long-running installation progress."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..admin import require_administrator


class ContentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    help_groups: list[str] = Field(max_length=100)
    dos_packages: list[str] = Field(max_length=100)


def create_content_router(config, accounts, content):
    router = APIRouter(prefix="/api/admin/content")

    @router.get("")
    def choices(request: Request):
        require_administrator(config, accounts, request)
        try:
            return JSONResponse(content.choices(), headers={"Cache-Control": "no-store"})
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=503, detail=f"Server content configuration is unavailable: {error}") from None

    @router.get("/status")
    def status(request: Request):
        require_administrator(config, accounts, request)
        return JSONResponse(content.status(), headers={"Cache-Control": "no-store"})

    @router.post("", status_code=202)
    def install(data: ContentSelection, request: Request):
        require_administrator(config, accounts, request, write=True)
        try:
            status = content.start(data.help_groups, data.dos_packages)
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return JSONResponse(status, status_code=202, headers={"Cache-Control": "no-store"})

    return router
