"""FastAPI application for ARM UI."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.common.path_safety import safe_join

from backend.routers import (
    arm_actions,
    config,
    dashboard,
    drives,
    files,
    folder,
    images,
    iso,
    jobs,
    logs,
    maintenance,
    notifications,
    patterns,
    settings,
    setup,
    system,
    themes,
    transcoder,
)
from backend.services import arm_client, transcoder_client
from backend.services import image_cache, system_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    await system_cache.refresh()
    image_cache.startup_scan()
    yield
    await arm_client.close_client()
    await transcoder_client.close_client()


app = FastAPI(title="ARM UI", version="1.0.0", lifespan=lifespan)

# CORS for dev (SvelteKit on :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(dashboard.router)
app.include_router(config.router)
app.include_router(jobs.router)
app.include_router(arm_actions.router)
app.include_router(arm_actions.naming_router)
app.include_router(arm_actions.system_router)
app.include_router(transcoder.router)
app.include_router(drives.router)
app.include_router(logs.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(themes.router)
app.include_router(files.router)
app.include_router(folder.router)
app.include_router(iso.router)
app.include_router(setup.router)
app.include_router(system.router)
app.include_router(images.router)
app.include_router(maintenance.router)
app.include_router(patterns.router)

# Serve static frontend build if it exists
static_dir = Path(__file__).parent.parent / "frontend" / "build"
if static_dir.is_dir():
    # Serve _app assets directly
    app.mount("/_app", StaticFiles(directory=str(static_dir / "_app")), name="static")

    # Serve /img assets directly
    img_dir = static_dir / "img"
    if img_dir.is_dir():
        app.mount("/img", StaticFiles(directory=str(img_dir)), name="images")

    # Serve root-level static files (favicon, apple-touch-icon, etc.)

    @app.get("/{filename:path}")
    async def root_static_or_spa(request: Request, filename: str):
        if filename:
            try:
                file_path = safe_join(static_dir, filename)
            except ValueError:
                pass
            else:
                if Path(file_path).is_file():
                    return FileResponse(file_path)
        return FileResponse(
            static_dir / "index.html",
            headers={"Cache-Control": "no-cache"},
        )


if __name__ == "__main__":
    import uvicorn

    from backend.config import settings as cfg

    uvicorn.run("backend.main:app", host="0.0.0.0", port=cfg.port, reload=True)
