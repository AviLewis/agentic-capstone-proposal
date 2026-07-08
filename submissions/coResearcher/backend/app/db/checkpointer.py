"""LangGraph PostgresSaver wiring.

The checkpointer stores graph state on the same Postgres database as the domain
tables, which enables HITL resume and fault tolerance. It reuses the shared
async connection pool. ``setup_checkpointer`` creates the checkpoint tables and
is idempotent, so it is safe to call on every startup.
"""

from __future__ import annotations

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.db.pool import get_pool
from app.graph.serde import make_serde
from app.logging import get_logger

log = get_logger(__name__)

_checkpointer: AsyncPostgresSaver | None = None


def get_checkpointer() -> AsyncPostgresSaver:
    """Return a checkpointer bound to the shared pool (open the pool first)."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = AsyncPostgresSaver(get_pool(), serde=make_serde())
    return _checkpointer


async def setup_checkpointer() -> AsyncPostgresSaver:
    """Create/upgrade checkpoint tables. Idempotent."""
    checkpointer = get_checkpointer()
    await checkpointer.setup()
    log.info("checkpointer_ready")
    return checkpointer


def reset_checkpointer() -> None:
    """Drop the cached checkpointer (used when the pool is recycled)."""
    global _checkpointer
    _checkpointer = None
