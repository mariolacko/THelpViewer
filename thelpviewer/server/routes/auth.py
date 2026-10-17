"""Account, Passkey, optional password and registration-token HTTP routes."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from ..accounts.common import AccountError
from ..accounts.passwords import PasswordRateLimit
from ..accounts.store import AccountStore
from ..accounts.sessions import SESSION_LIFETIME
from ..config import AppConfig


class PasskeyEnrollment(BaseModel):
    username: str
    token: str


class PasskeyRegistration(BaseModel):
    name: str
    email: str
    token: str
    first_name: str | None = Field(default=None, strict=True, max_length=100)
    last_name: str | None = Field(default=None, strict=True, max_length=100)
    nickname: str | None = Field(default=None, strict=True, max_length=100)


class PasskeyLogin(BaseModel):
    username: str


class PasskeyAnswer(BaseModel):
    ceremony_id: str
    credential: dict


class PasskeyCreation(PasskeyAnswer):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="Passkey", strict=True, min_length=1, max_length=80)


class PasskeyName(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(strict=True, min_length=1, max_length=80)


class PasswordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(strict=True, min_length=15, max_length=128, repr=False)


class PasswordLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(strict=True, min_length=1, max_length=254)
    password: str = Field(strict=True, min_length=1, max_length=128, repr=False)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(strict=True, min_length=3, max_length=254)
    first_name: str | None = Field(default=None, strict=True, max_length=100)
    last_name: str | None = Field(default=None, strict=True, max_length=100)
    nickname: str | None = Field(default=None, strict=True, max_length=100)


def create_auth_router(config: AppConfig, accounts: AccountStore) -> APIRouter:
    """Expose account endpoints while keeping their origin and cookie policy together."""
    router = APIRouter()

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
        if config.dev_auto_login and (
            request.url.scheme != "http"
            or any(name == "forwarded" or name.startswith("x-forwarded-") for name in request.headers)
            or request.headers.get("sec-fetch-site", "same-origin") != "same-origin"
            or request.headers.get("origin", origin) != origin
        ):
            raise HTTPException(status_code=403, detail="Local development login does not accept proxied or cross-origin requests")
        return origin, parsed.hostname or ""

    def auth_response(token: str, origin: str, payload: dict | None = None) -> JSONResponse:
        response = JSONResponse(payload if payload is not None else {"authenticated": True})
        response.set_cookie(
            "thelp_session", token, max_age=SESSION_LIFETIME, httponly=True,
            secure=origin.startswith("https://"), samesite="strict", path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    def owner_token(request: Request) -> str:
        token = request.cookies.get("thelp_session", "")
        if not accounts.session_user(token):
            raise HTTPException(status_code=403, detail="Sign-in required")
        return token

    @router.get("/api/auth/session")
    def auth_session(request: Request) -> JSONResponse:
        try:
            origin, _rp_id = auth_origin(request)
        except HTTPException:
            return JSONResponse({"enabled": False, "authenticated": False}, headers={"Cache-Control": "no-store"})
        user = accounts.session_user(request.cookies.get("thelp_session", ""))
        if config.dev_auto_login and not user:
            try:
                token = accounts.development_session()
            except AccountError as error:
                raise HTTPException(status_code=403, detail=str(error)) from None
            return auth_response(token, origin, {
                "enabled": True, "authenticated": True, "user": accounts.session_user(token),
                "development": True,
            })
        return JSONResponse(
            {"enabled": True, "authenticated": bool(user), "user": user,
             **({"development": True} if config.dev_auto_login else {})},
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/api/auth/activity")
    def session_activity(request: Request) -> JSONResponse:
        origin, _rp_id = auth_origin(request, require_post=True)
        token = request.cookies.get("thelp_session", "")
        if accounts.session_activity(token):
            return auth_response(token, origin, {
                "enabled": True, "authenticated": True, "user": accounts.session_user(token),
                **({"development": True} if config.dev_auto_login else {}),
            })
        response = JSONResponse({"enabled": True, "authenticated": False, "user": None},
                                headers={"Cache-Control": "no-store"})
        response.delete_cookie("thelp_session", path="/", secure=origin.startswith("https://"),
                               httponly=True, samesite="strict")
        return response

    @router.put("/api/auth/profile")
    def update_profile(data: ProfileUpdate, request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        token = request.cookies.get("thelp_session", "")
        if not accounts.session_user(token):
            raise HTTPException(status_code=403, detail="Sign-in required")
        try:
            user = accounts.update_profile(token, **data.model_dump())
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return JSONResponse({"user": user}, headers={"Cache-Control": "no-store"})

    @router.post("/api/auth/passkey/enroll/options")
    def passkey_enroll_options(data: PasskeyEnrollment, request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        try:
            return accounts.registration_options(data.username, data.token, rp_id, "THelpViewer")
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @router.post("/api/auth/passkey/enroll/verify")
    def passkey_enroll_verify(data: PasskeyCreation, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        try:
            token = accounts.verify_registration(data.ceremony_id, data.credential, rp_id, origin, data.name)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @router.post("/api/auth/passkey/register/options")
    def passkey_register_options(data: PasskeyRegistration, request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        try:
            return accounts.new_registration_options(
                data.name, data.email, data.token, rp_id, "THelpViewer",
                first_name=data.first_name, last_name=data.last_name, nickname=data.nickname,
            )
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @router.post("/api/auth/passkey/register/verify")
    def passkey_register_verify(data: PasskeyCreation, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        try:
            token = accounts.verify_new_registration(data.ceremony_id, data.credential, rp_id, origin, data.name)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @router.get("/api/auth/registration-tokens")
    def registration_tokens(request: Request) -> JSONResponse:
        auth_origin(request)
        try:
            tokens = accounts.list_registration_tokens(request.cookies.get("thelp_session", ""))
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return JSONResponse({"tokens": tokens}, headers={"Cache-Control": "no-store"})

    @router.post("/api/auth/registration-tokens")
    def registration_token(request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        try:
            token = accounts.issue_registration_token(request.cookies.get("thelp_session", ""))
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return JSONResponse({"token": token, "expires_in": 3600}, headers={"Cache-Control": "no-store"})

    @router.delete("/api/auth/registration-tokens/{token_hash}", status_code=204)
    def delete_registration_token(token_hash: str, request: Request) -> Response:
        auth_origin(request, require_post=True)
        try:
            accounts.delete_registration_token(request.cookies.get("thelp_session", ""), token_hash)
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return Response(status_code=204)

    @router.post("/api/auth/passkey/login/options")
    def passkey_login_options(data: PasskeyLogin, request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        try:
            return accounts.authentication_options(data.username, rp_id)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @router.post("/api/auth/passkey/login/verify")
    def passkey_login_verify(data: PasskeyAnswer, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        try:
            token = accounts.verify_authentication(data.ceremony_id, data.credential, rp_id, origin)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @router.post("/api/auth/logout")
    def auth_logout(request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        accounts.logout(request.cookies.get("thelp_session", ""))
        response = JSONResponse({"authenticated": False}, headers={"Cache-Control": "no-store"})
        response.delete_cookie("thelp_session", path="/")
        return response

    @router.get("/api/auth/security")
    def account_security(request: Request) -> JSONResponse:
        auth_origin(request)
        token = owner_token(request)
        try:
            data = accounts.security(token)
        except AccountError as error:
            raise HTTPException(status_code=403, detail=str(error)) from None
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    @router.put("/api/auth/password")
    def set_password(data: PasswordUpdate, request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        token = owner_token(request)
        try:
            accounts.set_password(token, data.password)
        except PasswordRateLimit as error:
            raise HTTPException(status_code=429, detail=str(error), headers={"Retry-After": "30"}) from None
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return JSONResponse({"password_set": True}, headers={"Cache-Control": "no-store"})

    @router.post("/api/auth/password/login")
    def password_login(data: PasswordLogin, request: Request) -> JSONResponse:
        origin, _rp_id = auth_origin(request, require_post=True)
        try:
            token = accounts.password_login(data.username, data.password, request.client.host if request.client else "")
        except PasswordRateLimit as error:
            raise HTTPException(status_code=429, detail=str(error), headers={"Retry-After": "900"}) from None
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return auth_response(token, origin)

    @router.post("/api/auth/passkeys/options")
    def add_passkey_options(request: Request) -> dict:
        _origin, rp_id = auth_origin(request, require_post=True)
        token = owner_token(request)
        try:
            return accounts.add_passkey_options(token, rp_id, "THelpViewer")
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    @router.post("/api/auth/passkeys/verify")
    def add_passkey_verify(data: PasskeyCreation, request: Request) -> JSONResponse:
        origin, rp_id = auth_origin(request, require_post=True)
        token = owner_token(request)
        try:
            accounts.verify_added_passkey(token, data.ceremony_id, data.credential, rp_id, origin, data.name)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return JSONResponse({"created": True}, headers={"Cache-Control": "no-store"})

    @router.put("/api/auth/passkeys/{credential_id}")
    def rename_passkey(credential_id: str, data: PasskeyName, request: Request) -> JSONResponse:
        auth_origin(request, require_post=True)
        token = owner_token(request)
        try:
            accounts.rename_passkey(token, credential_id, data.name)
        except AccountError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return JSONResponse({"renamed": True}, headers={"Cache-Control": "no-store"})

    return router
