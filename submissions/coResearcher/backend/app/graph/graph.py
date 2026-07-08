"""LangGraph orchestrator: wires the five agent nodes and two HITL gates.

Flow:
    START -> ideator -> [gate: pick questions] -> literature_review
          -> methodology -> research_plan -> judge -> [gate: approve plan] -> END

Every processing node runs a budget check first; on breach it returns a terminal
``capped`` status and a conditional edge routes the run straight to END.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.state import ResearchState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph


def _capped_router(state: ResearchState) -> str:
    """Route to END when a node short-circuited the run to ``capped``."""
    return "capped" if state.get("status") == "capped" else "continue"


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construct and compile the research pipeline graph.

    A checkpointer is required for the ``interrupt()`` HITL gates to persist and
    resume; pass an ``AsyncPostgresSaver`` in production or an in-memory saver in
    tests.
    """
    builder = StateGraph(ResearchState)

    builder.add_node("ideator", nodes.ideator)
    builder.add_node("gate_questions", nodes.gate_questions)
    builder.add_node("literature_review", nodes.literature_review)
    builder.add_node("methodology", nodes.methodology)
    builder.add_node("research_plan", nodes.research_plan)
    builder.add_node("judge", nodes.judge)
    builder.add_node("gate_plan_approval", nodes.gate_plan_approval)

    builder.add_edge(START, "ideator")
    builder.add_conditional_edges(
        "ideator", _capped_router, {"continue": "gate_questions", "capped": END}
    )
    builder.add_edge("gate_questions", "literature_review")
    builder.add_conditional_edges(
        "literature_review", _capped_router, {"continue": "methodology", "capped": END}
    )
    builder.add_conditional_edges(
        "methodology", _capped_router, {"continue": "research_plan", "capped": END}
    )
    builder.add_conditional_edges(
        "research_plan", _capped_router, {"continue": "judge", "capped": END}
    )
    builder.add_conditional_edges(
        "judge", _capped_router, {"continue": "gate_plan_approval", "capped": END}
    )
    builder.add_edge("gate_plan_approval", END)

    return builder.compile(checkpointer=checkpointer)
