"""HTTP application. The app reads only files on this machine."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from chorus.api import admin, annotations, auth, home, media, partitions
from chorus.config import settings
from chorus.db.migrate import has_pending

STATIC = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    missing = [project for project in settings().projects if has_pending(project)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Pending migrations for {joined}. Run: python -m chorus migrate --project <name>"
        )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Chorus", lifespan=lifespan)
    prefix = "/api/p/{project}"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(home.router, prefix=prefix)
    app.include_router(partitions.router, prefix=prefix)
    app.include_router(annotations.router, prefix=prefix)
    app.include_router(media.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)

    @app.get("/")
    def root():
        return RedirectResponse("/p/voices")

    if STATIC.is_dir():
        assets = STATIC / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            if path.startswith("api"):
                raise HTTPException(status_code=404, detail="Not found")
            index = STATIC / "index.html"
            if not index.is_file():
                raise HTTPException(status_code=404, detail="Frontend is not built")
            return FileResponse(index)

    return app


app = create_app()
