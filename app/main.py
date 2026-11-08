import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from app import db
from app.config import get_settings

logger = logging.getLogger("app")

# Flipped on shutdown so /readyz fails while uvicorn drains in-flight requests.
_shutting_down = threading.Event()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # Runs after SIGTERM once uvicorn has drained connections.
    _shutting_down.set()
    try:
        db.get_engine().dispose()
    except Exception:  # noqa: BLE001 - best effort during shutdown
        logger.exception("engine dispose failed")


app = FastAPI(title="multi-env-api", lifespan=lifespan)


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Liveness: process is up. Never touches dependencies."""
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz(response: Response) -> dict[str, str]:
    """Readiness: ready to take traffic only if the database is reachable."""
    if _shutting_down.is_set():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "shutting_down"}
    try:
        db.check_database()
    except Exception:  # noqa: BLE001
        logger.exception("readiness check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "database_unavailable"}
    return {"status": "ready"}


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": "multi-env-api", "environment": get_settings().environment}
