"""Checkpoint serializer configured to (de)serialize our state models.

LangGraph will block deserializing unregistered custom types in a future
version, so we explicitly allowlist the Pydantic models embedded in
``ResearchState``. Use ``make_serde()`` when constructing any checkpointer.
"""

from __future__ import annotations

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.graph import state

# Pydantic models that appear inside the graph state / checkpoints.
STATE_MODELS = [
    state.Caps,
    state.CostUsed,
    state.QuestionItem,
    state.PaperItem,
    state.MethodologyItem,
    state.PlanItem,
    state.CriterionScore,
    state.RankedPlanItem,
]


def make_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=STATE_MODELS)
