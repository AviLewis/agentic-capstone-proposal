"""Background execution + event pub/sub for graph runs.

The ``RunManager`` drives the compiled LangGraph in a background asyncio task,
publishing progress events (node updates, cost, interrupts, completion) to any
subscribers (the SSE endpoint). It enforces one active execution per run and an
optional wall-clock timeout, and best-effort persists run status/cost.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from langgraph.types import Command

from app.db import repository
from app.graph.state import CostUsed, ResearchState
from app.logging import get_logger

log = get_logger(__name__)

# Events after which an SSE stream leg should close.
TERMINAL_EVENTS = {"interrupt", "completed", "error"}

_GATE_TO_STATUS = {
    "question_selection": "awaiting_question_selection",
    "plan_approval": "awaiting_plan_approval",
}


@dataclass
class RunEvent:
    event: str
    data: dict[str, Any]


class RunAlreadyActiveError(RuntimeError):
    """Raised when starting/resuming a run that is already executing."""


class RunManager:
    def __init__(self, graph):
        self._graph = graph
        self._subscribers: dict[str, set[asyncio.Queue[RunEvent]]] = {}
        self._active: set[str] = set()
        self._lock = asyncio.Lock()

    # --- config -----------------------------------------------------------
    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    # --- subscriptions ----------------------------------------------------
    def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent]:
        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._subscribers.setdefault(run_id, set()).add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        subs = self._subscribers.get(run_id)
        if subs:
            subs.discard(queue)
            if not subs:
                self._subscribers.pop(run_id, None)

    def _publish(self, run_id: str, event: str, data: dict[str, Any]) -> None:
        for queue in self._subscribers.get(run_id, set()):
            queue.put_nowait(RunEvent(event=event, data=data))

    def is_active(self, run_id: str) -> bool:
        return run_id in self._active

    async def snapshot(self, thread_id: str) -> dict[str, Any]:
        """Current state summary for a run (status + pending interrupt)."""
        state = await self._graph.aget_state(self._config(thread_id))
        interrupts = [i for t in state.tasks for i in (t.interrupts or [])]
        values = state.values or {}
        # A run is only "done" once it has produced state *and* has no next step.
        # A freshly-created run whose graph task hasn't checkpointed yet returns an
        # empty state with no `next`; treating that as done would make clients show
        # an empty "completed" view while the pipeline is actually still starting.
        done = bool(values) and not state.next
        return {
            "status": values.get("status", "pending"),
            "done": done,
            "interrupt": interrupts[0].value if interrupts else None,
        }

    # --- execution --------------------------------------------------------
    async def start(
        self, run_id: str, thread_id: str, state: ResearchState, *, timeout: float | None = None
    ) -> None:
        await self._launch(run_id, thread_id, state, timeout)

    async def resume(
        self, run_id: str, thread_id: str, resume_value: Any, *, timeout: float | None = None
    ) -> None:
        await self._launch(run_id, thread_id, Command(resume=resume_value), timeout)

    async def _launch(
        self, run_id: str, thread_id: str, graph_input: Any, timeout: float | None
    ) -> None:
        async with self._lock:
            if run_id in self._active:
                raise RunAlreadyActiveError(run_id)
            self._active.add(run_id)
        asyncio.create_task(self._run(run_id, thread_id, graph_input, timeout))

    async def _run(
        self, run_id: str, thread_id: str, graph_input: Any, timeout: float | None
    ) -> None:
        try:
            self._publish(run_id, "status", {"status": "running"})
            coro = self._drive(run_id, thread_id, graph_input)
            if timeout:
                await asyncio.wait_for(coro, timeout=timeout)
            else:
                await coro
        except TimeoutError:
            log.error("run_timeout", run_id=run_id)
            await self._persist_status(run_id, "error", "run timed out")
            self._publish(run_id, "error", {"message": "run timed out"})
        except Exception as exc:  # noqa: BLE001
            log.error("run_failed", run_id=run_id, exc_info=True)
            await self._persist_status(run_id, "error", str(exc))
            self._publish(run_id, "error", {"message": str(exc)})
        finally:
            async with self._lock:
                self._active.discard(run_id)

    async def _drive(self, run_id: str, thread_id: str, graph_input: Any) -> None:
        config = self._config(thread_id)
        async for chunk in self._graph.astream(
            graph_input, config, stream_mode="updates"
        ):
            for node, delta in chunk.items():
                if node == "__interrupt__" or not isinstance(delta, dict):
                    continue
                self._publish(
                    run_id,
                    "node",
                    {
                        "node": node,
                        "status": delta.get("status"),
                        "logs": delta.get("logs", []),
                        "source_health": delta.get("source_health") or {},
                    },
                )
                cost = delta.get("cost")
                if isinstance(cost, CostUsed):
                    self._publish(
                        run_id,
                        "cost",
                        {
                            "tokens": cost.tokens_used,
                            "cost_usd": round(cost.cost_usd, 6),
                            "tool_calls": cost.tool_calls,
                        },
                    )

        state = await self._graph.aget_state(config)
        values = state.values or {}
        interrupts = [i for t in state.tasks for i in (t.interrupts or [])]

        if interrupts:
            payload = interrupts[0].value
            gate = payload.get("gate") if isinstance(payload, dict) else None
            status = _GATE_TO_STATUS.get(gate, "awaiting_question_selection")
            await self._persist_status(run_id, status)
            await self._persist_cost(run_id, values.get("cost"))
            self._publish(run_id, "interrupt", {"value": payload})
        else:
            status = values.get("status", "completed")
            await self._persist_status(run_id, status)
            await self._persist_cost(run_id, values.get("cost"))
            self._publish(
                run_id,
                "completed",
                {
                    "status": status,
                    "approved_plan_id": values.get("approved_plan_id"),
                },
            )

    # --- persistence (best-effort) ---------------------------------------
    async def _persist_status(
        self, run_id: str, status: str, error: str | None = None
    ) -> None:
        try:
            await repository.update_run_status(UUID(run_id), status, error)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            log.warning("persist_status_failed", run_id=run_id, exc_info=True)

    async def _persist_cost(self, run_id: str, cost: Any) -> None:
        if not isinstance(cost, CostUsed):
            return
        try:
            await repository.update_run_cost(UUID(run_id), cost.model_dump())
        except Exception:  # noqa: BLE001
            log.warning("persist_cost_failed", run_id=run_id, exc_info=True)
