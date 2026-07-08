"""FastAPI application entrypoint.

Boots the app with structured logging, CORS, a Postgres connection pool, the
LangGraph checkpointer, the compiled graph, and the run manager, then mounts the
runs API (create / SSE stream / resume / results).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.runs import router as runs_router
from app.config import get_settings
from app.db import (
    close_pool,
    get_checkpointer,
    open_pool,
    reset_checkpointer,
    setup_checkpointer,
)
from app.graph import build_graph
from app.logging import configure_logging, get_logger
from app.run_manager import RunManager

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_logs=settings.APP_ENV != "development")
    log.info("startup", env=settings.APP_ENV, version=__version__)

    db_ready = False
    app.state.run_manager = None
    try:
        await open_pool()
        await setup_checkpointer()
        graph = build_graph(checkpointer=get_checkpointer())
        app.state.graph = graph
        app.state.run_manager = RunManager(graph)
        db_ready = True
    except Exception:  # noqa: BLE001 - degrade gracefully if DB is unreachable
        log.error("db_init_failed", exc_info=True)

    app.state.db_ready = db_ready

    try:
        yield
    finally:
        reset_checkpointer()
        await close_pool()
        log.info("shutdown")


def _error_response(status_code: int, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": status_code, "message": message}}
    if details is not None:
        body["error"]["details"] = jsonable_encoder(details)
    return JSONResponse(status_code=status_code, content=body)


def create_app() -> FastAPI:
    app = FastAPI(
        title="coResearcher API",
        version=__version__,
        description="Multi-agent research planning pipeline.",
        lifespan=lifespan,
    )

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(request: Request, exc: StarletteHTTPException):
        return _error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_exc_handler(request: Request, exc: RequestValidationError):
        return _error_response(422, "Request validation failed", exc.errors())

    @app.exception_handler(Exception)
    async def _unhandled_exc_handler(request: Request, exc: Exception):
        log.error("unhandled_error", exc_info=True)
        return _error_response(500, "Internal server error")

    app.include_router(runs_router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/ready", tags=["meta"])
    async def ready(request: Request) -> dict[str, object]:
        return {
            "status": "ok",
            "db_ready": bool(getattr(request.app.state, "db_ready", False)),
        }

    return app


app = create_app()
