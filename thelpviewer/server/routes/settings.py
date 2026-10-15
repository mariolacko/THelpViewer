"""Administrator-only server configuration."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from typing import Literal

from ..accounts.common import AccountError
from ..accounts.store import AccountStore
from ..config import AppConfig
from ..settings import MAX_BACKUP_COUNT, ServerSettings
from ..dos.store import DosPromptStore
from ..midi.library import MidiLibrary
from .authorization import require_administrator


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dos_user_disk_mb: int = Field(strict=True, ge=1, le=256)
    backup_count: int = Field(strict=True, ge=1, le=MAX_BACKUP_COUNT)


class MidiSourcesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[str] = Field(max_length=100)
    albums: dict[str, list[str] | None] = Field(max_length=100)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(strict=True, max_length=254)
    first_name: str | None = Field(default=None, strict=True, max_length=100)
    last_name: str | None = Field(default=None, strict=True, max_length=100)
    nickname: str | None = Field(default=None, strict=True, max_length=100)
    role: Literal["admin", "member"]
    active: bool = Field(strict=True)
    disk_capacity_mb: int | None = Field(default=None, strict=True, ge=1, le=256)


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(strict=True, min_length=3, max_length=254)
    first_name: str = Field(default="", strict=True, max_length=100)
    last_name: str = Field(default="", strict=True, max_length=100)
    nickname: str = Field(default="", strict=True, max_length=100)


def create_settings_router(config: AppConfig, accounts: AccountStore, settings: ServerSettings,
                           dos: DosPromptStore, midi: MidiLibrary) -> APIRouter:
    router = APIRouter(prefix="/api/admin")

    def administrator(request: Request, *, write: bool = False) -> str:
        return require_administrator(config, accounts, request, write=write)

    @router.get("/settings")
    def read_settings(request: Request) -> JSONResponse:
        administrator(request)
        return JSONResponse({**settings.get(), "runtime": {
            "host": config.host, "port": config.port,
            "public_base_url": config.public_base_url, "auth_origin": config.auth_origin,
            "state_dir": str(config.state_dir), "helps_dir": str(config.helps_dir),
            "data_dir": str(config.persistent_dir), "sources_dir": str(config.sources_dir or ""),
            "downloads_dir": str(config.downloads_dir or config.state_dir / "downloads"),
            "docs_dir": str(config.docs_dir), "web_dir": str(config.web_dir),
            "assets_dir": str(config.assets_dir), "index_path": str(config.index_path),
            "readme_path": str(config.readme_path), "changelog_path": str(config.changelog_path),
            "statistics_path": str(config.statistics_path or config.persistent_dir / "statistics.sqlite3"),
            "google_site_verification_configured": bool(config.google_site_verification),
            "virtual_docs": [name for name, _path in config.virtual_docs],
            "midi_sources_path": str(config.midi_sources_path or ""),
            "dos_config_path": str(config.dos_config_path or ""),
            "dev_auto_login": config.dev_auto_login,
        }}, headers={"Cache-Control": "no-store"})

    @router.put("/settings")
    def write_settings(data: SettingsUpdate, request: Request) -> JSONResponse:
        administrator(request, write=True)
        return JSONResponse(settings.update(data.model_dump()), headers={"Cache-Control": "no-store"})

    @router.get("/midi-sources")
    def midi_sources(request: Request) -> JSONResponse:
        administrator(request)
        try:
            return JSONResponse(midi.source_choices(), headers={"Cache-Control": "no-store"})
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from None

    @router.put("/midi-sources", status_code=202)
    def update_midi_sources(data: MidiSourcesUpdate, request: Request) -> JSONResponse:
        administrator(request, write=True)
        try:
            midi.select_sources(data.sources, data.albums)
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return JSONResponse(midi.source_choices(), status_code=202, headers={"Cache-Control": "no-store"})

    @router.get("/midi-sources/status")
    def midi_source_status(request: Request) -> JSONResponse:
        administrator(request)
        return JSONResponse(midi.rebuild_status(), headers={"Cache-Control": "no-store"})

    @router.post("/midi-sources/{source_id}/index", status_code=202)
    def index_midi_source(source_id: str, request: Request) -> JSONResponse:
        administrator(request, write=True)
        try:
            midi.index_source(source_id)
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return JSONResponse(midi.rebuild_status(), status_code=202, headers={"Cache-Control": "no-store"})

    @router.get("/users")
    def read_users(request: Request) -> JSONResponse:
        token = administrator(request)
        users = accounts.list_users(token)
        for user in users:
            user["disk"] = dos.disk_usage(user["id"])
        return JSONResponse({"users": users, "dos_user_disk_mb": settings.get()["dos_user_disk_mb"]},
                            headers={"Cache-Control": "no-store"})

    @router.put("/users/{account_id}")
    def write_user(account_id: str, data: UserUpdate, request: Request) -> JSONResponse:
        token = administrator(request, write=True)
        try:
            user = accounts.update_user(token, account_id, **data.model_dump())
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        user["disk"] = dos.disk_usage(account_id)
        return JSONResponse({"user": user}, headers={"Cache-Control": "no-store"})

    @router.post("/users")
    def create_user(data: UserCreate, request: Request) -> JSONResponse:
        token = administrator(request, write=True)
        try:
            result = accounts.create_managed_user(token, **data.model_dump())
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        result["user"]["disk"] = dos.disk_usage(result["user"]["id"])
        return JSONResponse(result, status_code=201, headers={"Cache-Control": "no-store"})

    return router
