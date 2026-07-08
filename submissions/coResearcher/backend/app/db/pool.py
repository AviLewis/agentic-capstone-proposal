"""Async Postgres connection pool (psycopg 3).

A single lazily-initialized pool is shared across the app and by the LangGraph
checkpointer. Connections are autocommit with ``dict_row`` so query results come
back as dictionaries that map cleanly onto Pydantic models.
"""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)

_pool: AsyncConnectionPool | None = None


def _build_pool() -> AsyncConnectionPool:
    settings = get_settings()
    return AsyncConnectionPool(
        conninfo=settings.SUPABASE_DB_URL,
        open=False,
        min_size=1,
        max_size=10,
        # LangGraph's PostgresSaver requires autocommit for CREATE INDEX
        # CONCURRENTLY during setup; autocommit also keeps simple writes simple.
        kwargs={"autocommit": True, "row_factory": dict_row},
    )


async def open_pool() -> AsyncConnectionPool:
    """Open (and cache) the global connection pool."""
    global _pool
    if _pool is None:
        _pool = _build_pool()
    if _pool.closed:
        await _pool.open()
    await _pool.wait()
    log.info("db_pool_opened", min_size=_pool.min_size, max_size=_pool.max_size)
    return _pool


def get_pool() -> AsyncConnectionPool:
    """Return the open pool, raising if it has not been initialized yet."""
    if _pool is None or _pool.closed:
        raise RuntimeError("Connection pool is not open. Call open_pool() at startup.")
    return _pool


async def close_pool() -> None:
    """Close the global connection pool (call on shutdown)."""
    global _pool
    if _pool is not None and not _pool.closed:
        await _pool.close()
        log.info("db_pool_closed")
    _pool = None
