"""Local development administrator rebuilds; never enabled on production."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..accounts import AccountStore
from ..config import AppConfig
from ..dos_prompt import DosPromptStore
from ..midi_library import MidiLibrary


def create_rebuild_router(config: AppConfig, accounts: AccountStore,
                          dos: DosPromptStore, midi: MidiLibrary) -> APIRouter:
    router = APIRouter(prefix="/api/admin/rebuild")

    def authorize(request: Request, *, write: bool = False) -> None:
        if not config.dev_auto_login:
            raise HTTPException(status_code=404, detail="Local rebuild is disabled")
        user = accounts.session_user(request.cookies.get("thelp_session", ""))
        if not user or user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator sign-in required")
        if (str(request.base_url).rstrip("/") != config.auth_origin
                or any(name == "forwarded" or name.startswith("x-forwarded-") for name in request.headers)
                or request.headers.get("sec-fetch-site", "same-origin") != "same-origin"
                or (write and request.headers.get("origin") != config.auth_origin)):
            raise HTTPException(status_code=403, detail="Invalid local rebuild origin")

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
