"""ARM API server - FastAPI."""
import functools
import inspect
import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import arm.config.config as cfg
from arm.database import db

log = logging.getLogger(__name__)


def _cleanup_session():
    """Roll back and release the current thread's scoped session.

    Safe to call when no engine is initialised or no session has been
    bound on this thread - both paths short-circuit without acquiring
    a pool connection.
    """
    if db._engine is None:
        return
    try:
        db.session.rollback()
    except Exception as exc:
        # rollback() can raise if the session is already invalid; we still
        # want remove() to drop any held connection. Log at debug so a
        # pattern of repeated failures is visible if someone goes looking.
        log.debug("db session rollback during cleanup failed: %s", exc)
    db.session.remove()


def _wrap_sync_endpoint(endpoint: Callable) -> Callable:
    """Wrap a sync endpoint so its scoped_session is cleaned on the same thread.

    FastAPI runs sync def endpoints in the AnyIO threadpool. A handler that
    queries the DB checks out a connection bound to its thread's scoped
    session, but nothing returns it: scoped_session keys by thread id, so
    only code running on that same thread can call session.remove() to
    release the pool connection. AnyIO reuses threads, so each unique
    worker thread leaks one connection on the first DB-touching request,
    permanently. Once enough distinct workers have served requests the
    pool is exhausted and every later request blocks 30s on bind.connect()
    before timing out.

    Wrapping each sync endpoint with cleanup-in-finally guarantees the
    cleanup runs on the same thread that ran the endpoint, so the
    scoped_session is the right one and the connection actually returns
    to the pool.

    Contract: the wrapper itself MUST stay sync. FastAPI's APIRoute snapshots
    `dependant.is_coroutine_callable` at construction time and dispatches
    via either ``await call`` (async) or ``await run_in_threadpool(call)``
    (sync) based on that flag. Returning a coroutine from this wrapper
    would silently break the sync dispatch path. Async endpoints are not
    wrapped at all - see _install_session_cleanup.
    """
    @functools.wraps(endpoint)
    def wrapper(*args, **kwargs):
        try:
            return endpoint(*args, **kwargs)
        finally:
            _cleanup_session()
    # Mark so we don't double-wrap if this function is called twice.
    wrapper.__arm_session_wrapped__ = True  # type: ignore[attr-defined]
    return wrapper


def _install_session_cleanup(app: FastAPI) -> None:
    """Wrap every registered sync endpoint with per-request DB cleanup.

    Walks app.routes once at startup. Async endpoints are left untouched -
    they run on the event loop, where scoped_session would yield a
    session keyed to the loop thread (shared across all async handlers).
    Async handlers must manage their own DB lifecycle if they query the DB.

    Both `route.endpoint` and the captured `dependant.call` need to be
    rebound: FastAPI snapshots the dependant at route construction, and
    that's what actually runs. Reassigning only `route.endpoint` would
    leave the captured callable in place.
    """
    from fastapi.routing import APIRoute as _APIRoute  # local to avoid top-level cost

    for route in app.routes:
        if not isinstance(route, _APIRoute):
            continue
        endpoint = route.endpoint
        if inspect.iscoroutinefunction(endpoint):
            continue
        if getattr(endpoint, "__arm_session_wrapped__", False):
            continue
        wrapped = _wrap_sync_endpoint(endpoint)
        route.endpoint = wrapped
        # FastAPI builds dependant.call at route construction. Replace it
        # too, otherwise the wrapper is never invoked.
        if route.dependant is not None and route.dependant.call is endpoint:
            route.dependant.call = wrapped


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    db.init_engine(cfg.get_db_uri())

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

    # Notification dispatcher (drains outbox, runs forever).
    import asyncio
    from arm.notifications.dispatcher import run_dispatcher_loop
    dispatcher_stop = asyncio.Event()
    dispatcher_task = asyncio.create_task(
        run_dispatcher_loop(stop_event=dispatcher_stop),
        name="notification-dispatcher",
    )

    log.info("ARM API server starting up.")
    try:
        yield
    finally:
        log.info("ARM API server shutting down.")
        dispatcher_stop.set()
        try:
            await asyncio.wait_for(dispatcher_task, timeout=10.0)
        except asyncio.TimeoutError:
            log.warning("dispatcher did not stop within 10s; cancelling")
            dispatcher_task.cancel()


app = FastAPI(title="ARM API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from arm.api.v1 import jobs, logs, metadata, notifications, settings, system, drives, files, setup, folder, iso, maintenance  # noqa: E402

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
app.include_router(iso.router)
app.include_router(maintenance.router)

# Wrap every sync endpoint with per-request DB cleanup. Must run after all
# routers are included; sees a fixed set of routes (we don't register routes
# at runtime).
_install_session_cleanup(app)
