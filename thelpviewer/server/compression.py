"""Shared HTTP compression policy; Starlette owns the streaming compressor."""

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES, GZipMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def accepts_encoding(value: str, coding: str) -> bool:
    """Honor explicit exclusions before wildcards, including malformed qvalues."""
    qualities: dict[str, float] = {}
    for part in value.split(","):
        name, *parameters = part.lower().split(";")
        name = name.strip()
        quality = 1.0
        for parameter in parameters:
            key, _, number = parameter.strip().partition("=")
            if key.strip() == "q":
                try:
                    quality = float(number)
                except ValueError:
                    quality = 0.0
                if not 0 <= quality <= 1:
                    quality = 0.0
        qualities[name] = min(qualities.get(name, 1.0), quality)
    return qualities.get(coding.lower(), qualities.get("*", 0.0)) > 0


class ResponseCompressionMiddleware:
    """Negotiate gzip once for API, documents and static files, not per route."""

    # These file formats are already compressed, even when served as octet-stream
    # or application/json (UHF .json.gz must reach the JS decoder unchanged).
    compressed_suffixes = (".gz", ".br", ".sf3", ".zip", ".rar", ".7z", ".bz2", ".xz", ".zst")
    excluded_types = tuple(
        content_type for content_type in DEFAULT_EXCLUDED_CONTENT_TYPES if content_type != "audio/*"
    ) + ("audio/mpeg", "audio/ogg", "audio/aac", "audio/mp4", "audio/webm")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        if (path == "/api/auth" or path.startswith("/api/auth/")
                or path == "/api/admin/users" or path.startswith("/api/admin/users/")
                or path.lower().endswith(self.compressed_suffixes)):
            # Account/token responses can mix secrets and user-controlled text.
            await self.app(scope, receive, send)
            return

        request_headers = Headers(scope=scope)
        use_gzip = (accepts_encoding(
            ",".join(request_headers.getlist("accept-encoding")), "gzip",
        ) and scope["method"] != "HEAD" and "range" not in request_headers)
        application_scope = scope
        if use_gzip:
            # FileResponse must emit chunks rather than bypassing compression via
            # a server's zero-copy pathsend extension. Keep client headers intact.
            application_scope = {**scope, "extensions": {
                key: value for key, value in scope.get("extensions", {}).items()
                if key != "http.response.pathsend"
            }}

        async def send_response(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                if headers.get("content-encoding") == "gzip" or (use_gzip and message["status"] == 304):
                    # A strong validator cannot identify both identity and gzip
                    # bytes. StaticFiles accepts this weak ETag on revalidation.
                    etag = headers.get("etag")
                    if etag and not etag.startswith("W/"):
                        headers["ETag"] = "W/" + etag
                if message["status"] == 304 or scope["method"] == "HEAD" or "range" in request_headers:
                    headers.add_vary_header("Accept-Encoding")
            await send(message)

        async def application(_scope: Scope, receive: Receive, compressed_send: Send) -> None:
            bypass = False

            async def policy_send(message: Message) -> None:
                nonlocal bypass
                if message["type"] == "http.response.start":
                    headers = Headers(raw=message["headers"])
                    bypass = ("set-cookie" in headers or "no-transform" in {
                        directive.strip().lower() for directive in headers.get("cache-control", "").split(",")
                    })
                await (send(message) if bypass else compressed_send(message))

            await self.app(application_scope, receive, policy_send)

        # Starlette's gzip switch is substring-based. Give only its selector a
        # normalized value so gzip;q=0 is never mistaken for support. The routed
        # application still sees the original Accept-Encoding (including br).
        negotiated_scope = {**application_scope, "headers": [
            (key, value) for key, value in scope["headers"] if key.lower() != b"accept-encoding"
        ] + [(b"accept-encoding", b"gzip" if use_gzip else b"identity")]}
        await GZipMiddleware(
            application, minimum_size=1024, compresslevel=5, exclude_content_types=self.excluded_types,
        )(negotiated_scope, receive, send_response)
