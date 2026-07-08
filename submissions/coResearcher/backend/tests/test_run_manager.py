"""Tests for the RunManager background execution + event stream."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.db import repository
from app.graph.graph import build_graph
from app.graph.serde import make_serde
from app.graph.state import Caps, initial_state
from app.run_manager import RunAlreadyActiveError, RunManager


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    async def _noop_status(*args, **kwargs):
        return None

    async def _noop_cost(*args, **kwargs):
        return None

    monkeypatch.setattr(repository, "update_run_status", _noop_status)
    monkeypatch.setattr(repository, "update_run_cost", _noop_cost)


async def _drain_until(queue, target, timeout=5.0):
    events = []
    while True:
        event = await asyncio.wait_for(queue.get(), timeout=timeout)
        events.append(event)
        if event.event == target:
            return events


async def _wait_idle(manager, run_id, timeout=5.0):
    async with asyncio.timeout(timeout):
        while manager.is_active(run_id):
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_run_streams_nodes_then_interrupt_then_completes(stub_deps):
    graph = build_graph(checkpointer=InMemorySaver(serde=make_serde()))
    manager = RunManager(graph)
    run_id, thread_id = str(uuid4()), str(uuid4())

    queue = manager.subscribe(run_id)
    await manager.start(
        run_id, thread_id, initial_state("A research brief", caps=Caps(max_questions=2))
    )

    events = await _drain_until(queue, "interrupt")
    assert any(e.event == "node" for e in events)
    assert any(e.event == "cost" for e in events)
    assert events[-1].data["value"]["gate"] == "question_selection"

    await _wait_idle(manager, run_id)

    queue2 = manager.subscribe(run_id)
    await manager.resume(run_id, thread_id, {"select_all": True})
    events2 = await _drain_until(queue2, "interrupt")  # plan approval gate
    assert events2[-1].data["value"]["gate"] == "plan_approval"

    await _wait_idle(manager, run_id)

    queue3 = manager.subscribe(run_id)
    await manager.resume(run_id, thread_id, {"approved_index": 0})
    events3 = await _drain_until(queue3, "completed")
    assert events3[-1].data["status"] == "completed"
    assert events3[-1].data["approved_plan_id"]


@pytest.mark.asyncio
async def test_snapshot_reports_pending_interrupt(stub_deps):
    graph = build_graph(checkpointer=InMemorySaver(serde=make_serde()))
    manager = RunManager(graph)
    run_id, thread_id = str(uuid4()), str(uuid4())

    queue = manager.subscribe(run_id)
    await manager.start(run_id, thread_id, initial_state("brief", caps=Caps(max_questions=1)))
    await _drain_until(queue, "interrupt")
    await _wait_idle(manager, run_id)

    snap = await manager.snapshot(thread_id)
    assert snap["interrupt"]["gate"] == "question_selection"
    assert snap["done"] is False


@pytest.mark.asyncio
async def test_concurrent_start_rejected(stub_deps):
    graph = build_graph(checkpointer=InMemorySaver(serde=make_serde()))
    manager = RunManager(graph)
    run_id, thread_id = str(uuid4()), str(uuid4())

    await manager.start(run_id, thread_id, initial_state("brief", caps=Caps(max_questions=1)))
    with pytest.raises(RunAlreadyActiveError):
        await manager.resume(run_id, thread_id, {"select_all": True})

    await _wait_idle(manager, run_id)
