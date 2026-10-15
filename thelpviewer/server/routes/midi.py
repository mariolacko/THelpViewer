"""MIDI catalog and locally cached track endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..midi.library import MidiLibrary


def create_midi_router(library: MidiLibrary) -> APIRouter:
    router = APIRouter(prefix="/api/midi")

    @router.get("/catalog")
    def catalog() -> dict[str, object]:
        return library.catalog()

    @router.post("/priority/{source_id}/{item_id}")
    def prioritize(source_id: str, item_id: str) -> dict[str, bool]:
        if not library.prioritize(source_id, item_id):
            raise HTTPException(status_code=404, detail="MIDI catalog item not found")
        return {"queued": True}

    @router.get("/files/{source_id}/{filename}")
    def track(source_id: str, filename: str) -> FileResponse:
        path = library.file_path(source_id, filename)
        if path is None:
            raise HTTPException(status_code=404, detail="MIDI track not found")
        return FileResponse(path, media_type="audio/midi")

    @router.get("/covers/{source_id}/{filename}")
    def cover(source_id: str, filename: str) -> FileResponse:
        path = library.cover_path(source_id, filename)
        if path is None:
            raise HTTPException(status_code=404, detail="MIDI cover not found")
        return FileResponse(path, media_type="image/png" if path.suffix == ".png" else "image/jpeg")

    return router
