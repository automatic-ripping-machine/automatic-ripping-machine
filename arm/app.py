"""ARM API server — FastAPI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import arm.config.config as cfg
from arm.database import db

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    db.init_engine('sqlite:///' + cfg.arm_config['DBFILE'])
    log.info("ARM API server starting up.")
    yield
    log.info("ARM API server shutting down.")


app = FastAPI(title="ARM API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from arm.api.v1 import jobs, logs, metadata, notifications, settings, system, drives  # noqa: E402

app.include_router(jobs.router)
app.include_router(logs.router)
app.include_router(metadata.router)
app.include_router(notifications.router)
app.include_router(settings.router)
app.include_router(system.router)
app.include_router(drives.router)
