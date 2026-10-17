"""Static-asset behavior specific to the MIDI SoundFont."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.responses import Response

from .compression import accepts_encoding


class ViewerAssets(StaticFiles):
    """Serve the versioned MIDI SoundFont with its precompressed variant."""

    async def get_response(self, path: str, scope: dict) -> Response:
        if path != "midi/synth/FluidR3Mono_GM.sf3":
            return await super().get_response(path, scope)

        accepted = ",".join(Headers(scope=scope).getlist("accept-encoding"))
        brotli = accepts_encoding(accepted, "br")
        compressed = Path(self.directory) / f"{path}.br" if self.directory else None
        use_brotli = bool(brotli and compressed and compressed.is_file())
        response = await super().get_response(f"{path}.br" if use_brotli else path, scope)
        versioned = bool(parse_qs(scope.get("query_string", b"").decode("ascii", "ignore")).get("v"))
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable" if versioned else "no-cache"
        )
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["Content-Type"] = "application/octet-stream"
        if use_brotli:
            response.headers["Content-Encoding"] = "br"
        return response
