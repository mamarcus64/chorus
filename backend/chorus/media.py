"""Manifest lookup and byte-range video responses. Paths come from the manifest only."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, Request
from starlette.responses import FileResponse, Response, StreamingResponse

from chorus.config import settings

CHUNK = 1024 * 1024

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".json": "application/json",
    ".txt": "text/plain",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
}

_VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}


def empty_manifest(project: str) -> dict:
    return {"schema": 1, "project": project, "files": {}}


def load_manifest(project: str) -> dict:
    path = settings().manifest_path(project)
    if not path.exists():
        return empty_manifest(project)
    return json.loads(path.read_text())


def save_manifest(project: str, manifest: dict) -> None:
    path = settings().manifest_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def upsert_manifest_file(project: str, file_id: str, record: dict) -> None:
    manifest = load_manifest(project)
    manifest["files"][file_id] = record
    save_manifest(project, manifest)


def resolve_file(project: str, file_id: str) -> Path | None:
    manifest = load_manifest(project)
    record = manifest.get("files", {}).get(file_id)
    if not record:
        return None
    rel = record.get("path")
    if not isinstance(rel, str) or rel.startswith("/") or ".." in Path(rel).parts:
        return None
    root = settings().data_dir(project).resolve()
    full = (root / rel).resolve()
    if full != root and root not in full.parents:
        return None
    if not full.is_file():
        return None
    return full


def media_type(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


def is_video(path: Path) -> bool:
    return path.suffix.lower() in _VIDEO_SUFFIXES


def open_range_response(path: Path, request: Request) -> Response:
    """200 or 206 with Range support, ported from VoiceOver's video stream."""
    file_size = path.stat().st_size
    content_type = media_type(path)
    range_header = request.headers.get("range")

    if range_header is None:

        def _iter_full():
            with path.open("rb") as handle:
                while chunk := handle.read(CHUNK):
                    yield chunk

        return StreamingResponse(
            _iter_full(),
            status_code=200,
            media_type=content_type,
            headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"},
        )

    try:
        units, rng = range_header.split("=", 1)
        if units.strip().lower() != "bytes":
            raise ValueError
        start_str, end_str = rng.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except Exception as exc:
        raise HTTPException(status_code=416, detail="Invalid Range header") from exc

    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(
            status_code=416,
            detail="Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    length = end - start + 1

    def _iter_range():
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                data = handle.read(min(CHUNK, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        _iter_range(),
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
            "Accept-Ranges": "bytes",
        },
    )


def file_response(path: Path, request: Request) -> Response:
    if is_video(path):
        return open_range_response(path, request)
    return FileResponse(path, media_type=media_type(path))
