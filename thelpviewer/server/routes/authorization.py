"""Shared HTTP session, role and same-origin guards for administrator APIs."""

from urllib.parse import urlparse
from fastapi import HTTPException


def require_administrator(config, accounts, request, *, write=False):
    origin = urlparse(config.auth_origin)
    if (origin.scheme not in {"http", "https"}
            or (origin.scheme == "http" and origin.hostname not in {"localhost", "127.0.0.1", "::1"})
            or request.headers.get("host", "").lower() != origin.netloc.lower()
            or request.headers.get("sec-fetch-site", "same-origin") != "same-origin"
            or (write and request.headers.get("origin") != config.auth_origin)
            or (config.dev_auto_login and (str(request.base_url).rstrip("/") != config.auth_origin
                or any(name == "forwarded" or name.startswith("x-forwarded-") for name in request.headers)))):
        raise HTTPException(status_code=403, detail="Invalid administrator request origin")
    token = request.cookies.get("thelp_session", "")
    user = accounts.session_user(token)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator sign-in required")
    return token
