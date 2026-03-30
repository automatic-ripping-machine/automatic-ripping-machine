"""ARM API server — FastAPI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import arm.config.config as cfg
from arm.database import db

log = logging.getLogger(__name__)


class SessionCleanupMiddleware(BaseHTTPMiddleware):
    """Remove scoped DB sessions after each request.

    FastAPI runs sync def handlers in a threadpool.  AnyIO reuses threads,
    so scoped_session (keyed by thread ID) can leak uncommitted state from
    one request to the next on the same thread.  Calling db.session.remove()
    returns the connection to the pool and resets the session.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if db._engine is not None:
            db.session.remove()
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    db.init_engine('sqlite:///' + cfg.arm_config['DBFILE'])

    # Start cached disk usage - never blocks on NFS stalls
    from arm.services.disk_usage_cache import register_paths, start_background_refresh
    register_paths([
        cfg.arm_config.get("RAW_PATH", ""),
        cfg.arm_config.get("TRANSCODE_PATH", ""),
        cfg.arm_config.get("COMPLETED_PATH", ""),
        cfg.arm_config.get("LOGPATH", ""),
        cfg.arm_config.get("DBFILE", ""),
        cfg.arm_config.get("INSTALLPATH", ""),
    ])
    start_background_refresh()

    log.info("ARM API server starting up.")
    yield
    log.info("ARM API server shutting down.")


app = FastAPI(title="ARM API", lifespan=lifespan)

app.add_middleware(SessionCleanupMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from arm.api.v1 import jobs, logs, metadata, notifications, settings, system, drives, files, setup, folder, maintenance  # noqa: E402

app.include_router(jobs.router)
app.include_router(logs.router)
app.include_router(metadata.router)
app.include_router(notifications.router)
app.include_router(settings.router)
app.include_router(system.router)
app.include_router(drives.router)
app.include_router(files.router)
app.include_router(setup.router)
app.include_router(folder.router)
app.include_router(maintenance.router)
