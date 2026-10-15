"""Session-authenticated administrator rebuilds with recoverable backups."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..accounts.store import AccountStore
from ..config import AppConfig
from ..dos.store import DosPromptStore
from ..midi.library import MidiLibrary
from .authorization import require_administrator


def create_rebuild_router(config: AppConfig, accounts: AccountStore,
                          dos: DosPromptStore, midi: MidiLibrary) -> APIRouter:
    router = APIRouter(prefix="/api/admin/rebuild")

    def authorize(request: Request, *, write: bool = False) -> None:
        require_administrator(config, accounts, request, write=write)

    def status(resource: str) -> dict:
        match resource:
            case "dos":
                result = dos.status(start=False)
                return {**result, "file": result["current"]}
            case "midi":
                return midi.rebuild_status()
            case _:
                raise HTTPException(status_code=404, detail="Unknown rebuild resource")

    @router.get("/{resource}")
    def read_status(resource: str, request: Request) -> JSONResponse:
        authorize(request)
        return JSONResponse(status(resource), headers={"Cache-Control": "no-store"})

    @router.post("/{resource}", status_code=202)
    def rebuild(resource: str, request: Request) -> JSONResponse:
        authorize(request, write=True)
        try:
            match resource:
                case "dos": dos.rebuild()
                case "midi": midi.rebuild()
                case _: raise HTTPException(status_code=404, detail="Unknown rebuild resource")
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return JSONResponse(status(resource), status_code=202, headers={"Cache-Control": "no-store"})

    return router
