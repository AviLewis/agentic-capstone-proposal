"""Typed shared state for the coResearcher LangGraph pipeline.

The graph state is a ``TypedDict`` (LangGraph's channel schema) whose values are
Pydantic models for structured, validated sub-objects. Lists that should
accumulate across nodes (``logs``) use an ``operator.add`` reducer; everything
else is replaced by the returning node.
"""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field

from app.enums import RunStatus

# ---------------------------------------------------------------------------
# Budget / caps
# ---------------------------------------------------------------------------


class Caps(BaseModel):
    """Hard limits enforced before each node runs."""

    max_questions: int = 6
    max_papers_per_question: int = 8
    max_tool_calls: int = 40
    token_ceiling: int = 400_000
    cost_ceiling_usd: float = 5.0
    wall_clock_seconds: int = 900


class CostUsed(BaseModel):
    """Running tally of resource usage for a run."""

    tokens_used: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    started_at: float = Field(default_factory=time.time)

    def bump(
        self, *, tokens: int = 0, cost: float = 0.0, tool_calls: int = 0
    ) -> CostUsed:
        """Return a new CostUsed with the given increments applied."""
        return self.model_copy(
            update={
                "tokens_used": self.tokens_used + tokens,
                "cost_usd": self.cost_usd + cost,
                "tool_calls": self.tool_calls + tool_calls,
            }
        )

    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at


DEFAULT_CAPS = Caps()

# Weighted feasibility rubric applied by the Judge (weights sum to 1.0).
FEASIBILITY_RUBRIC: dict[str, float] = {
    "data_availability": 0.25,
    "methodological_soundness": 0.25,
    "scope_time_realism": 0.20,
    "novelty": 0.15,
    "resource_skill_fit": 0.15,
}


# ---------------------------------------------------------------------------
# Structured items carried in state (decoupled from DB rows / UUIDs)
# ---------------------------------------------------------------------------


class QuestionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    rationale: str = ""
    tag: str = ""
    selected: bool = False


class PaperItem(BaseModel):
    source: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    relevance: str | None = None


class MethodologyItem(BaseModel):
    methods: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class PlanItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    question_id: str
    content: dict[str, Any] = Field(default_factory=dict)


class CriterionScore(BaseModel):
    criterion: str
    score: float
    weight: float
    justification: str = ""


class RankedPlanItem(BaseModel):
    plan: PlanItem
    scores: list[CriterionScore] = Field(default_factory=list)
    total: float = 0.0
    rank: int = 0


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


class ResearchState(TypedDict, total=False):
    # identity / persistence
    run_id: str | None
    thread_id: str | None

    # inputs
    brief: str
    researcher_context: str
    own_data: str

    # config
    sources: list[str] | None  # literature sources to query (None = defaults)

    # guardrails
    caps: Caps
    cost: CostUsed

    # pipeline artifacts
    questions: list[QuestionItem]
    papers_by_question: dict[str, list[PaperItem]]
    methodologies: dict[str, MethodologyItem]
    plans: list[PlanItem]
    ranked_plans: list[RankedPlanItem]
    approved_plan_id: str | None

    # control
    status: RunStatus
    capped_reason: str | None
    source_health: dict[str, str]  # literature source -> failure reason (if any)
    logs: Annotated[list[str], operator.add]


TerminalStatus = Literal["completed", "capped", "error"]


def initial_state(
    brief: str,
    researcher_context: str = "",
    own_data: str = "",
    caps: Caps | None = None,
    run_id: str | None = None,
    thread_id: str | None = None,
    sources: list[str] | None = None,
) -> ResearchState:
    """Build a fresh ResearchState for a new run."""
    return ResearchState(
        run_id=run_id,
        thread_id=thread_id,
        brief=brief,
        researcher_context=researcher_context,
        own_data=own_data,
        sources=sources,
        caps=caps or Caps(),
        cost=CostUsed(),
        questions=[],
        papers_by_question={},
        methodologies={},
        plans=[],
        ranked_plans=[],
        approved_plan_id=None,
        status="pending",
        capped_reason=None,
        source_health={},
        logs=[],
    )
