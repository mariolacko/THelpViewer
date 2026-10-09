"""DOS boot bundles and session-owned C-drive overlays (never host mounts)."""

from __future__ import annotations

import json
import gzip

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from ..accounts import AccountStore
from ..config import AppConfig
from ..dos_prompt import DosError, DosPromptStore


def _accepts_gzip(value: str) -> bool:
    for part in value.split(","):
        encoding, *parameters = part.split(";")
        if encoding.strip().lower() != "gzip":
            continue
        quality = 1.0
        for parameter in parameters:
            name, _, number = parameter.strip().partition("=")
            if name.lower() == "q":
                try:
                    quality = float(number)
                except ValueError:
                    quality = 0.0
        return quality > 0
    return False


def create_dos_router(config: AppConfig, accounts: AccountStore, store: DosPromptStore) -> APIRouter:
    router = APIRouter(prefix="/api/dos")

    def identity(request: Request, required: bool = False) -> tuple[str | None, str]:
        token = request.cookies.get("thelp_session", "")
        account_id = accounts.session_account_id(token)
        user = accounts.session_user(token) if account_id else None
        if required and not account_id:
            raise HTTPException(status_code=401, detail="Sign in to save your C drive or mount media")
        return account_id, user["username"] if user else ""

    def ready() -> None:
        if store.status()["state"] != "ready":
            raise HTTPException(status_code=503, detail=store.error or "DOS C drive is being prepared")

    def write_origin(request: Request) -> None:
        if request.headers.get("origin") != config.auth_origin:
            raise HTTPException(status_code=403, detail="Invalid DOS request origin")

    async def body(request: Request, limit: int) -> bytes:
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > limit:
                raise HTTPException(status_code=413, detail="DOS upload exceeds its quota")
            data.extend(chunk)
        return bytes(data)

    @router.get("/status")
    def status() -> Response:
        return JSONResponse(store.status(), headers={"Cache-Control": "no-store"})

    @router.get("/session")
    def session(request: Request, media: str = "") -> Response:
        ready()
        account_id, username = identity(request)
        try:
            _bundle, metadata = store.bundle(account_id, media, lazy=True, account_name=username)
        except DosError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        metadata["account"] = username
        return JSONResponse(metadata, headers={"Cache-Control": "no-store"})

    @router.get("/bundle")
    def bundle(request: Request, media: str = "", full: bool = False) -> Response:
        ready()
        account_id, username = identity(request)
        try:
            data, metadata = store.bundle(account_id, media, lazy=not full, account_name=username)
        except DosError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return Response(data, media_type="application/zip", headers={
            "Cache-Control": "no-store", "X-DOS-Revision": str(metadata["revision"]),
            "X-DOS-Base": metadata["base_id"],
        })

    @router.get("/file")
    def file_chunk(request: Request, name: str, sha256: str, base_id: str, account: str = "",
                   base_file: bool = True, offset: int = 0, size: int = 65536) -> Response:
        ready()
        account_id, username = identity(request)
        if account != username or base_id != store.base_id:
            raise HTTPException(status_code=409, detail="DOS disk or signed-in account changed")
        try:
            data = store.read_chunk(account_id, name, sha256, base_file, offset, size)
        except (DosError, OSError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        headers = {"Cache-Control": "no-store", "Vary": "Accept-Encoding, Cookie"}
        if _accepts_gzip(request.headers.get("accept-encoding", "")) and len(data) >= 1024:
            data = gzip.compress(data, compresslevel=2)
            headers["Content-Encoding"] = "gzip"
        return Response(data, media_type="application/octet-stream", headers=headers)

    @router.put("/overlay")
    async def overlay(request: Request) -> Response:
        ready()
        write_origin(request)
        account_id, username = identity(request, required=True)
        data = await body(request, store.overlay_limit() * 2 + 1024 * 1024)
        try:
            payload = json.loads(data)
            if not isinstance(payload, dict) or payload.get("account") != username:
                raise DosError("The signed-in account changed; this drive was not saved")
            revision = store.save(account_id, payload)
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return JSONResponse({"revision": revision}, headers={"Cache-Control": "no-store"})

    @router.post("/media")
    async def upload_media(request: Request, kind: str = "") -> Response:
        ready()
        write_origin(request)
        account_id, username = identity(request, required=True)
        if request.headers.get("x-dos-account") != username:
            raise HTTPException(status_code=409, detail="The signed-in account changed; this image was not uploaded")
        data = await body(request, int(store.config.get("max_media_bytes", 128 * 1024 * 1024)))
        try:
            ident = store.add_media(account_id, kind, data)
        except DosError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        return JSONResponse({"id": ident}, headers={"Cache-Control": "no-store"})

    @router.get("/media/{ident}")
    def media_file(ident: str, request: Request) -> Response:
        account_id, _username = identity(request, required=True)
        path = store.media_path(account_id, ident)
        if path is None:
            raise HTTPException(status_code=404, detail="Media not found for this account")
        return FileResponse(path, media_type="application/octet-stream", headers={"Cache-Control": "no-store"})

    return router
