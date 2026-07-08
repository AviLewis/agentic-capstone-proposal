"""Integration tests for the graph skeleton: HITL gates + capped routing."""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.graph import build_graph
from app.graph.serde import make_serde
from app.graph.state import Caps, CostUsed, initial_state


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _graph():
    return build_graph(checkpointer=InMemorySaver(serde=make_serde()))


@pytest.mark.asyncio
async def test_full_run_pauses_at_both_gates_then_completes(stub_deps):
    graph = _graph()
    config = _config("run-1")

    state = initial_state("Study X in domain Y", caps=Caps(max_questions=3))

    # First interrupt: question selection gate.
    out = await graph.ainvoke(state, config)
    assert "__interrupt__" in out
    payload = out["__interrupt__"][0].value
    assert payload["gate"] == "question_selection"
    assert len(payload["questions"]) == 3

    # Resume by selecting the first two questions.
    out = await graph.ainvoke(
        Command(resume={"selected_indexes": [0, 1]}), config
    )
    assert "__interrupt__" in out
    payload = out["__interrupt__"][0].value
    assert payload["gate"] == "plan_approval"
    # Only selected questions produce plans.
    assert len(payload["ranked_plans"]) == 2

    # Resume by approving the top-ranked plan.
    out = await graph.ainvoke(Command(resume={"approved_index": 0}), config)
    assert out["status"] == "completed"
    assert out["approved_plan_id"]
    assert len(out["ranked_plans"]) == 2
    assert all(r.rank >= 1 for r in out["ranked_plans"])
    assert {r.rank for r in out["ranked_plans"]} == {1, 2}


@pytest.mark.asyncio
async def test_defaults_to_all_questions_when_no_selection(stub_deps):
    graph = _graph()
    config = _config("run-2")
    state = initial_state("brief", caps=Caps(max_questions=2))

    await graph.ainvoke(state, config)
    # A dict without selection keys means "keep all selected".
    out = await graph.ainvoke(Command(resume={"select_all": True}), config)
    assert out["__interrupt__"][0].value["gate"] == "plan_approval"
    assert len(out["__interrupt__"][0].value["ranked_plans"]) == 2


@pytest.mark.asyncio
async def test_budget_breach_short_circuits_to_capped():
    graph = _graph()
    config = _config("run-3")
    state = initial_state("brief")
    # Pre-load usage that already exceeds a tiny cap so ideator caps immediately.
    state["caps"] = Caps(max_tool_calls=0)
    state["cost"] = CostUsed(tool_calls=10)

    out = await graph.ainvoke(state, config)
    assert "__interrupt__" not in out
    assert out["status"] == "capped"
    assert out["capped_reason"]
    assert out["questions"] == []
