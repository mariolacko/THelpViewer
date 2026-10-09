"""Administrator-only server configuration."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..accounts import AccountStore
from ..config import AppConfig
from ..settings import ServerSettings


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dos_user_disk_mb: int = Field(strict=True, ge=1, le=256)


def create_settings_router(config: AppConfig, accounts: AccountStore, settings: ServerSettings) -> APIRouter:
    router = APIRouter(prefix="/api/admin")

    def administrator(request: Request) -> None:
        user = accounts.session_user(request.cookies.get("thelp_session", ""))
        if not user or user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator sign-in required")

    @router.get("/settings")
    def read_settings(request: Request) -> JSONResponse:
        administrator(request)
        return JSONResponse(settings.get(), headers={"Cache-Control": "no-store"})

    @router.put("/settings")
    def write_settings(data: SettingsUpdate, request: Request) -> JSONResponse:
        administrator(request)
        if request.headers.get("origin") != config.auth_origin:
            raise HTTPException(status_code=403, detail="Invalid request origin")
        return JSONResponse(settings.update(data.model_dump()), headers={"Cache-Control": "no-store"})

    return router
