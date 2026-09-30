"""Serve a manifest file to a logged-in user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response

from chorus.api.deps import current_user
from chorus.media import file_response, resolve_file

router = APIRouter()


@router.get("/media/{file_id:path}")
def get_media(
    project: str,
    file_id: str,
    request: Request,
    user: dict = Depends(current_user),
) -> Response:
    del user
    path = resolve_file(project, file_id)
    if path is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file_response(path, request)
